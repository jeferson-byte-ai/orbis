"""
Real-time Audio Stream Processor
Handles ASR → MT → TTS pipeline with latency optimization
"""
import asyncio
import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

import numpy as np

from ml.asr.whisper_service import whisper_service
from ml.mt.nllb_service import nllb_service
from ml.tts.coqui_service import coqui_service
from backend.config import settings
from backend.db.session import SessionLocal
from backend.db.models import VoiceProfile, VoiceType
from backend.services.audio_pipeline.websocket_manager import connection_manager, audio_chunk_manager
from backend.services.lazy_loader import lazy_loader, ModelType

logger = logging.getLogger(__name__)


class AudioStreamProcessor:
    """Processes audio streams in real-time with translation"""
    
    def __init__(self):
        self.user_languages: Dict[UUID, Dict[str, Any]] = {}  # {user_id: {'input': 'pt', 'output': 'en'}}
        self.processing_tasks: Dict[UUID, asyncio.Task] = {}
        self.latency_target_ms = 200
        self.input_sample_rate = 16000
        self.output_sample_rate = 22050
        self.max_tts_chars = 240  # Keep text under XTTS 400 token limit
        # Prevent ASR hallucination/repetition: track last transcript per user
        self._last_transcript: Dict[UUID, Tuple[str, float]] = {}
        # Simple energy gate to drop near-silence chunks (tuned)
        # Lower threshold reduces false skips on soft speech
        self._silence_rms_threshold: float = 0.0025
        # Rolling buffers for streaming context and voice activity
        self._rolling_buffers: Dict[UUID, bytes] = {}
        self._last_activity_ts: Dict[UUID, float] = {}
        self._last_process_ts: Dict[UUID, float] = {}
        self._speaking_flags: Dict[UUID, bool] = {}
        # Track what translation content has already been sent per (speaker -> listener, language)
        self._last_sent_translations: Dict[Tuple[UUID, UUID, str], str] = {}
        # Per (speaker->listener) sequence counters for audio chunks
        self._seq_counters: Dict[Tuple[UUID, UUID], int] = {}
    
    async def _notify_translation_error(self, user_id: UUID, stage: str, detail: str):
        """Send translation error information back to the user"""
        logger.error("Translation pipeline error (%s) for user %s: %s", stage, user_id, detail)
        try:
            await connection_manager.send_personal_message(user_id, {
                "type": "translation_error",
                "stage": stage,
                "message": detail
            })
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to notify user %s about translation error: %s", user_id, exc)

    async def start_processing(
        self,
        user_id: UUID,
        room_id: str,
        input_lang: str = 'auto',
        output_lang: str = 'en',
        speaks_pref: Optional[List[str]] = None,
        understands_pref: Optional[List[str]] = None
    ):
        """Start processing audio for a user"""
        self.user_languages[user_id] = {
            'input': input_lang,
            'output': output_lang,
            'room_id': room_id,
            'speaks_pref': list(speaks_pref or []),
            'understands_pref': list(understands_pref or []),
            'last_good_input': (input_lang if input_lang and input_lang != 'auto' else None)
        }
        
        # Start background processing task
        self.processing_tasks[user_id] = asyncio.create_task(
            self._process_audio_loop(user_id)
        )
        
        logger.info(f"Started audio processing for user {user_id} ({input_lang}→{output_lang})")
    
    async def stop_processing(self, user_id: UUID):
        """Stop processing audio for a user"""
        if user_id in self.processing_tasks:
            self.processing_tasks[user_id].cancel()
            try:
                await self.processing_tasks[user_id]
            except asyncio.CancelledError:
                pass
            del self.processing_tasks[user_id]
        
        if user_id in self.user_languages:
            del self.user_languages[user_id]
        
        # Clear per-user state
        self._last_transcript.pop(user_id, None)
        self._rolling_buffers.pop(user_id, None)
        self._last_activity_ts.pop(user_id, None)
        self._last_process_ts.pop(user_id, None)
        self._speaking_flags.pop(user_id, None)
        audio_chunk_manager.clear_audio_buffer(user_id)
        logger.info(f"Stopped audio processing for user {user_id}")
    
    async def _process_audio_loop(self, user_id: UUID):
        """Background loop to process audio chunks with rolling buffer and VAD-like gating"""
        try:
            while True:
                # Throttle processing loop to ~100ms for ultra-low latency
                await asyncio.sleep(0.10)
                
                if user_id not in self.user_languages:
                    break
                
                # Get new chunks from the socket buffer
                new_chunks = audio_chunk_manager.consume_audio_chunks(user_id)
                if not new_chunks:
                    # On silence, check if we should end the speaking session
                    self._check_end_of_speech(user_id)
                    continue
                
                combined_new = b"".join(new_chunks)
                if not combined_new:
                    continue
                
                # Append to rolling buffer with a maximum of 2.5s to limit Whisper context size
                buf = self._rolling_buffers.get(user_id, b"") + combined_new
                max_seconds = 6.0
                max_bytes = int(self.input_sample_rate * max_seconds * 2)
                if len(buf) > max_bytes:
                    buf = buf[-max_bytes:]
                self._rolling_buffers[user_id] = buf
                
                # Update last activity timestamp based on energy in the new audio
                # This helps us know when the user stopped speaking
                audio_array = self._bytes_to_audio_array(combined_new)
                rms = float(np.sqrt(np.mean(np.square(audio_array)))) if audio_array.size > 0 else 0.0
                if rms >= self._silence_rms_threshold:
                    self._last_activity_ts[user_id] = time.time()
                    self._speaking_flags[user_id] = True
                
                # Only process if enough time passed since last process to avoid duplicate work
                now = time.time()
                last_proc = self._last_process_ts.get(user_id, 0.0)
                if now - last_proc < 0.10:  # 100ms minimum interval
                    continue
                self._last_process_ts[user_id] = now
                
                # If we still have very little audio in the rolling buffer, wait for more to reduce first-word cut
                min_bytes = int(self.input_sample_rate * 0.10 * 2)  # ~100ms (start even earlier)
                if len(buf) < min_bytes:
                    continue
                
                # Process the rolling buffer, which provides some context
                await self._process_audio_chunk(user_id, buf)
                
        except asyncio.CancelledError:
            logger.info(f"Audio processing stopped for user {user_id}")
        except Exception as e:
            logger.error(f"Audio processing error for user {user_id}: {e}")
    
    def _check_end_of_speech(self, user_id: UUID):
        """End-of-speech detection based on silence duration to reset rolling context"""
        last_ts = self._last_activity_ts.get(user_id)
        speaking = self._speaking_flags.get(user_id, False)
        if not last_ts or not speaking:
            return
        # If we've had >500ms without activity, finalize and reset state to avoid repeats
        if time.time() - last_ts > 0.8:  # wait longer to avoid premature end-of-speech reset
            # Reset rolling context and per-listener delta trackers
            self._rolling_buffers.pop(user_id, None)
            self._speaking_flags[user_id] = False
            # Clear last transcript window older than 1.5s to allow new phrases
            last_text, last_time = self._last_transcript.get(user_id, ("", 0.0))
            if last_text and (time.time() - last_time) > 1.5:
                self._last_transcript.pop(user_id, None)
            # Clear last-sent trackers for this speaker so next utterance starts fresh
            keys_to_clear = [k for k in self._last_sent_translations.keys() if k[0] == user_id]
            for k in keys_to_clear:
                self._last_sent_translations.pop(k, None)
            logger.debug(f"🛑 End-of-speech detected for {user_id}, resetting rolling buffer and last-sent deltas")
    
    async def _process_audio_chunk(self, user_id: UUID, audio_data: bytes):
        """Process a single audio chunk through ASR → MT → TTS pipeline"""
        start_time = time.time()
        
        try:
            user_config = self.user_languages.get(user_id)
            if not user_config:
                logger.warning(f"No language config for user {user_id}, skipping audio processing")
                return
                
            room_id = user_config['room_id']
            input_lang = user_config['input']
            output_lang = user_config['output']

            # Note: output_lang is what the SPEAKER wants to HEAR from others
            # input_lang is what the SPEAKER is SPEAKING
            
            # Step 1: Convert bytes to numpy array
            audio_array = self._bytes_to_audio_array(audio_data)
            if audio_array.size == 0:
                return
            
            # Drop near-silence chunks to avoid Whisper hallucinations (e.g., repeated 'what is')
            rms = float(np.sqrt(np.mean(np.square(audio_array)))) if audio_array.size > 0 else 0.0
            if rms < self._silence_rms_threshold:
                logger.debug(f"⏭️ Skipping near-silence chunk (RMS={rms:.4f}) for user {user_id}")
                return

            # Step 2: ASR - Speech to Text (Lazy Load)
            asr_start_time = time.time()
            
            # Ensure Whisper is loaded
            if not await lazy_loader.ensure_loaded(ModelType.WHISPER):
                await self._notify_translation_error(user_id, "asr", "Speech recognition model unavailable")
                return

            if not getattr(whisper_service, "model_loaded", False):
                await self._notify_translation_error(user_id, "asr", "Whisper model failed to load")
                return
            
            # Use Whisper VAD to reduce repetitions on noisy audio
            # Normalize possible region-specific codes (e.g., pt-BR -> pt)
            forced_lang = None
            if input_lang and input_lang != 'auto':
                forced_lang = (input_lang.split('-')[0] or input_lang).lower()
            else:
                # If auto, bias ASR with last good input if we have one
                forced_lang = (self.user_languages.get(user_id, {}).get('last_good_input') or None)
            transcribed_text, detected_lang, asr_meta = await whisper_service.transcribe(
                audio_array,
                language=forced_lang if forced_lang else None,
                sample_rate=self.input_sample_rate,
                vad_filter=True
            )
            asr_latency = (time.time() - asr_start_time) * 1000

            # If input is auto and we have speaks_pref, bias chosen language to speaks_pref[0]
            if (not input_lang or input_lang == 'auto'):
                prefs = self.user_languages.get(user_id, {})
                sp0 = self._first_valid_language(prefs.get('speaks_pref', []) or [])
                if sp0 and sp0 != (forced_lang or detected_lang):
                    detected_lang = sp0
                    if isinstance(asr_meta, dict):
                        asr_meta['language'] = sp0
                        asr_meta['language_probability'] = max(asr_meta.get('language_probability', 0.0), 0.75)
            
            # ✅ Filter out empty/meaningless transcriptions
            transcribed_text = transcribed_text.strip()
            if not transcribed_text or transcribed_text in ['...', '.', ',', '?', '!', '  ']:
                logger.debug(f"⏭️ Skipping empty/noise transcription for user {user_id}")
                return  # No meaningful speech detected
            # If detection confidence is very low and we're in auto with no last_good, wait for more audio
            if (input_lang == 'auto' or not input_lang) and not self.user_languages.get(user_id, {}).get('last_good_input'):
                if 'detected_conf' in locals() and detected_conf < 0.50:
                    logger.debug(f"⏭️ Low-confidence ({detected_conf:.2f}) detection with no prior hint; waiting for more audio for user {user_id}")
                    return

            # Suppress repeated identical transcriptions within 1.5s window (tuned)
            now = time.time()
            last_text, last_ts = self._last_transcript.get(user_id, ("", 0.0))
            if transcribed_text.lower() == last_text.lower() and (now - last_ts) < 1.5:
                logger.debug(f"⏭️ Suppressing duplicate transcript within window for user {user_id}: '{transcribed_text}'")
                return
            self._last_transcript[user_id] = (transcribed_text, now)
            
            detected_conf = 0.0
            try:
                detected_conf = float(asr_meta.get('language_probability', 0.0)) if isinstance(asr_meta, dict) else 0.0
            except Exception:
                detected_conf = 0.0
            # Recompute detection confidence after possible biasing
            detected_conf = 0.0
            try:
                detected_conf = float(asr_meta.get('language_probability', 0.0)) if isinstance(asr_meta, dict) else 0.0
            except Exception:
                detected_conf = 0.0

            speaker_language = self._determine_speaker_language(
                user_id,
                (input_lang.split('-')[0].lower() if input_lang and input_lang != 'auto' else 'auto'),
                (detected_lang.split('-')[0].lower() if detected_lang else None),
                detected_confidence=detected_conf
            )

            # Post-decision guard: never trust auto-detected language under low confidence
            if (input_lang == 'auto' or not input_lang) and detected_lang and detected_conf < 0.70:
                prefs = self.user_languages.get(user_id, {})
                fallback = (
                    prefs.get('last_good_input')
                    or self._first_valid_language(prefs.get('speaks_pref', []) or [])
                    or 'en'
                )
                if speaker_language != fallback:
                    logger.warning(
                        "🛡️ Overriding low-confidence detection (%s @ %.2f) → %s",
                        detected_lang,
                        detected_conf,
                        fallback,
                    )
                    speaker_language = (fallback.split('-')[0] or fallback).lower()

            try:
                self.user_languages[user_id]['last_detected_language'] = speaker_language
                # Update last-good input if we chose confidently detected or configured
                if input_lang and input_lang != 'auto':
                    self.user_languages[user_id]['last_good_input'] = (input_lang.split('-')[0] or input_lang).lower()
                elif detected_conf >= 0.70 and detected_lang:
                    self.user_languages[user_id]['last_good_input'] = (detected_lang.split('-')[0] or detected_lang).lower()
            except Exception:
                pass

            try:
                logger.info(
                    "🧭 Language decision | configured_input=%s detected=%s conf=%.2f → chosen=%s",
                    input_lang,
                    detected_lang,
                    detected_conf,
                    speaker_language,
                )
            except Exception:
                pass

            logger.info(f"🎤 User {user_id} spoke in {speaker_language}: '{transcribed_text}'")
            
            # Emit partial transcript immediately to room (low-latency UI)
            try:
                await connection_manager.broadcast_to_room(room_id, {
                    'type': 'partial_transcript',
                    'user_id': str(user_id),
                    'text': transcribed_text,
                    'language': speaker_language,
                    'timestamp': time.time()
                })
            except Exception as _e:
                logger.debug(f"Partial transcript broadcast failed: {_e}")
            
            # Step 3: Machine Translation (Lazy Load)
            # Ensure NLLB is loaded
            if not await lazy_loader.ensure_loaded(ModelType.NLLB):
                await self._notify_translation_error(user_id, "mt", "Translation model unavailable")
                return

            if getattr(nllb_service, "model", None) is None:
                await self._notify_translation_error(user_id, "mt", "NLLB model failed to load")
                return
            
            mt_latency = 0.0
            
            # Step 4: Text-to-Speech with Voice Cloning (Lazy Load)
            if not await lazy_loader.ensure_loaded(ModelType.COQUI):
                await self._notify_translation_error(user_id, "tts", "Voice synthesis model unavailable")
                return

            if getattr(coqui_service, "tts", None) is None:
                await self._notify_translation_error(user_id, "tts", "Coqui TTS model failed to load")
                return
            
            listeners = connection_manager.get_room_users(room_id)
            logger.info(f"🔊 Found {len(listeners) if listeners else 0} listeners in room {room_id}: {listeners}")
            if not listeners:
                logger.warning(f"⚠️ No listeners in room {room_id} - cannot send translation!")
                return

            translations_cache: Dict[str, str] = {}
            tts_total_latency = 0.0
            send_latency = 0.0
            processed_count = 0

            for target_user_id in listeners:
                # Skip sending to self
                if target_user_id == user_id:
                    continue

                # Get listener's preferred language (what they want to HEAR)
                listener_prefs = self.user_languages.get(target_user_id, {})
                target_language = self._resolve_target_language(listener_prefs, speaker_language)
                
                logger.debug(f"📢 Processing for listener {target_user_id}: {input_lang} → {target_language}")

                # Decide effective source language for MT to avoid 'no-op' when source==target due to misdetection
                effective_source = speaker_language
                try:
                    # If we would skip MT because source==target, but detected differs from target and has some confidence,
                    # use detected as source to force translation
                    if target_language == speaker_language and detected_lang and detected_conf >= 0.40:
                        det_norm = (detected_lang.split('-')[0] or detected_lang).lower()
                        if det_norm != target_language:
                            effective_source = det_norm
                            logger.warning(f"🛡️ Forcing MT source from misdetected '{speaker_language}' to detected '{effective_source}' for target '{target_language}'")
                except Exception:
                    pass

                # Check if we already processed this language
                full_translation = translations_cache.get(target_language)

                if not full_translation:
                    translation_start = time.time()
                    
                    # Translate text from effective source to listener's language
                    full_translation = await self._translate_text(
                        transcribed_text,
                        effective_source,
                        target_language
                    )
                    translation_latency = (time.time() - translation_start) * 1000
                    mt_latency += translation_latency

                    logger.info(f"🌐 Translated to {target_language}: '{full_translation}'")

                    translations_cache[target_language] = full_translation
                
                # Also broadcast partial translation for UI immediacy
                try:
                    await connection_manager.send_personal_message(target_user_id, {
                        'type': 'partial_translation',
                        'from_user_id': str(user_id),
                        'text': full_translation,
                        'language': target_language,
                        'timestamp': time.time()
                    })
                except Exception as _e:
                    logger.debug(f"Partial translation send failed: {_e}")

                # Compute delta: only speak what hasn't been sent yet to this listener for this language
                key = (user_id, target_user_id, target_language)
                last_sent = self._last_sent_translations.get(key, "")
                delta_text = full_translation[len(last_sent):] if full_translation.startswith(last_sent) else full_translation
                
                # If delta is too small, skip to avoid micro TTS calls
                min_delta_chars = 1  # allow tiny deltas to capture short words like 'a', 'é'
                if len(delta_text.strip()) < min_delta_chars:
                    continue
                
                # TTS only the delta
                tts_start_time = time.time()
                target_audio, used_fallback_voice = await self._text_to_speech(
                    delta_text,
                    target_language,
                    voice_user_id=user_id,
                    fallback_user_id=None
                )
                tts_latency = (time.time() - tts_start_time) * 1000
                tts_total_latency += tts_latency

                if not target_audio:
                    logger.warning(
                        f"⚠️ No translated audio generated for {input_lang} → {target_language} (delta)"
                    )
                    continue

                # Send translated audio delta to listener
                send_start_time = time.time()
                await self._send_translated_audio(
                    room_id=room_id,
                    source_user_id=user_id,
                    target_user_id=target_user_id,
                    audio_data=target_audio,
                    text=delta_text,
                    target_language=target_language,
                    voice_fallback=used_fallback_voice
                )
                send_latency += (time.time() - send_start_time) * 1000
                processed_count += 1
                # Update last-sent marker for incremental streaming
                self._last_sent_translations[key] = full_translation
            
            # Calculate and log latency
            total_processing_time = (time.time() - start_time) * 1000
            target_languages = list(translations_cache.keys())
            
            if processed_count > 0:
                logger.info(
                    f"✅ User {user_id} audio processed in {total_processing_time:.1f}ms "
                    f"(ASR: {asr_latency:.1f}ms, MT: {mt_latency:.1f}ms, TTS: {tts_total_latency:.1f}ms, Send: {send_latency:.1f}ms) | "
                    f"Sent to {processed_count} listener(s) | "
                    f"'{transcribed_text}' → languages {target_languages}"
                )
            else:
                logger.debug(
                    f"⚠️ User {user_id} spoke but no listeners needed translation: '{transcribed_text}'"
                )
            
            if total_processing_time > self.latency_target_ms:
                logger.warning(f"⚠️ Latency exceeded target: {total_processing_time:.1f}ms > {self.latency_target_ms}ms")
                
        except Exception as e:
            logger.error(f"❌ Error processing audio chunk for user {user_id}: {e}", exc_info=True)
    
    def _bytes_to_audio_array(self, audio_data: bytes) -> np.ndarray:
        """Convert raw PCM bytes to normalized float32 numpy array"""
        if not audio_data:
            return np.array([], dtype=np.float32)

        # Ensure even number of bytes for int16 conversion
        if len(audio_data) % 2 != 0:
            audio_data = audio_data[:-1]

        if not audio_data:
            return np.array([], dtype=np.float32)

        audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
        if audio_int16.size == 0:
            return np.array([], dtype=np.float32)

        audio_float = audio_int16.astype(np.float32) / 32768.0
        return audio_float
    
    async def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text using NLLB"""
        source = source_lang or target_lang or "en"
        target = target_lang or source

        if source == target:
            return text

        try:
            cleaned = text.strip()
            if not cleaned:
                return ""

            max_total_chars = self.max_tts_chars * 3
            if len(cleaned) > max_total_chars:
                logger.warning(
                    "Truncating long transcription from %s to %s chars for translation",
                    len(cleaned),
                    max_total_chars,
                )
                cleaned = cleaned[-max_total_chars:]

            chunks = self._chunk_text_for_tts(cleaned, self.max_tts_chars)
            if not chunks:
                return ""

            translated_chunks: List[str] = []
            for chunk in chunks:
                translated = await nllb_service.translate(
                    chunk,
                    source,
                    target,
                )
                translated_chunks.append(translated)

            return " ".join(translated_chunks)
        except Exception as e:
            logger.error(f"Translation service error: {e}")
            return f"[{(target or 'en').upper()}] {text}"
    
    async def _text_to_speech(
        self,
        text: str,
        language: str,
        voice_user_id: UUID,
        fallback_user_id: Optional[UUID] = None
    ) -> Tuple[bytes, bool]:
        """Convert text to speech with speaker's cloned voice"""
        try:
            speaker_wav = self._get_speaker_reference(voice_user_id)
            # Consider it a fallback whenever we don't have a speaker-specific WAV
            used_fallback = not bool(speaker_wav)

            # Log voice profile status
            if not speaker_wav:
                logger.warning(
                    f"⚠️ No voice profile found for user {voice_user_id}. "
                    f"Using default TTS voice without cloning."
                )
            else:
                logger.info(f"✅ Using cloned voice for user {voice_user_id}: {speaker_wav}")

            if not speaker_wav and fallback_user_id and fallback_user_id != voice_user_id:
                logger.info(f"🔄 Trying fallback voice profile for user {fallback_user_id}")
                speaker_wav = self._get_speaker_reference(fallback_user_id)
                used_fallback = bool(speaker_wav)
                if speaker_wav:
                    logger.info(f"✅ Using fallback cloned voice: {speaker_wav}")
                else:
                    logger.warning(f"⚠️ No fallback voice profile found either")

            text_chunks = self._chunk_text_for_tts(text, max(60, self.max_tts_chars // 3))
            if not text_chunks:
                return b"", used_fallback

            # Stream TTS progressively: synthesize small chunks and yield concatenated bytes
            audio_segments: List[np.ndarray] = []
            for idx, chunk in enumerate(text_chunks):
                audio_array = await coqui_service.synthesize(
                    text=chunk,
                    language=language,
                    speaker_wav=speaker_wav,
                    sample_rate=self.output_sample_rate
                )

                if audio_array.size == 0:
                    logger.warning("⚠️ Empty audio chunk from TTS, skipping segment")
                    continue

                # Append to segments
                audio_segments.append(audio_array)

            if not audio_segments:
                return b"", used_fallback

            # Concatenate and return bytes
            audio_array = np.concatenate(audio_segments)
            if audio_array.size == 0:
                return b"", used_fallback

            audio_array = np.clip(audio_array, -1.0, 1.0)
            pcm_audio = (audio_array * 32767).astype(np.int16)
            return pcm_audio.tobytes(), used_fallback

        except Exception as e:
            logger.error(f"TTS service error: {e}")
            # Fallback to mock audio
            return b"", True
    
    async def _send_translated_audio(
        self,
        room_id: str,
        source_user_id: UUID,
        target_user_id: UUID,
        audio_data: bytes,
        text: str,
        target_language: str,
        voice_fallback: bool
    ):
        """Send translated audio to a specific participant (with sequence for jitter buffer)"""
        if not audio_data:
            return

        # Sequence per (speaker->listener)
        seq_key = (source_user_id, target_user_id)
        seq = self._seq_counters.get(seq_key, 0) + 1
        self._seq_counters[seq_key] = seq

        encoded_audio = base64.b64encode(audio_data).decode("ascii")
        audio_message = {
            'type': 'translated_audio',
            'user_id': str(source_user_id),
            'seq': seq,
            'audio': {
                'data': encoded_audio,
                'encoding': 'pcm_s16le',
                'sample_rate': self.output_sample_rate
            },
            'audio_data': encoded_audio,
            'original_text': self._last_transcript.get(source_user_id, ("", 0.0))[0],
            'detected_language': self.user_languages.get(source_user_id, {}).get('last_detected_language')
            or self.user_languages.get(source_user_id, {}).get('input'),
            'text': text,
            'language': target_language,
            'voice_fallback': voice_fallback,
            'timestamp': time.time()
        }
        
        await connection_manager.send_personal_message(target_user_id, audio_message)
    
    def update_user_language(
        self,
        user_id: UUID,
        input_lang: Optional[str] = None,
        output_lang: Optional[str] = None,
        speaks_pref: Optional[List[str]] = None,
        understands_pref: Optional[List[str]] = None
    ):
        """Update user's language preferences"""
        if user_id not in self.user_languages:
            logger.debug(
                f"Cannot update languages for user {user_id}: user not in processing queue"
            )
            return

        config = self.user_languages[user_id]
        # Normalize short language codes (e.g., pt-BR -> pt)
        def _norm(code: Optional[str]) -> Optional[str]:
            if not code:
                return code
            return (code.split('-')[0] or code).lower()
        def _norm_list(codes: Optional[List[str]]) -> Optional[List[str]]:
            if codes is None:
                return None
            return [(_norm(c) or 'en') for c in codes if c]

        if input_lang:
            config['input'] = _norm(input_lang)
            if config['input'] != 'auto':
                config['last_good_input'] = config['input']
        if output_lang:
            config['output'] = _norm(output_lang)
        if speaks_pref is not None:
            config['speaks_pref'] = _norm_list(speaks_pref) or []
        if understands_pref is not None:
            config['understands_pref'] = _norm_list(understands_pref) or []

        logger.info(
            "🔄 Updated languages for user %s: speaks=%s, wants_to_hear=%s",
            user_id,
            config.get('input'),
            config.get('output')
        )

    def _determine_speaker_language(
        self,
        user_id: UUID,
        configured_input: str,
        detected_lang: Optional[str],
        detected_confidence: float = 0.0
    ) -> str:
        # Normalize
        configured = (configured_input or '').split('-')[0].lower() if configured_input else ''
        detected = (detected_lang or '').split('-')[0].lower() if detected_lang else ''

        # If user explicitly configured their input language, always respect it
        if configured and configured != 'auto':
            return configured

        # If we have a confident detection, use it
        if detected and detected_confidence >= 0.70:
            return detected

        # If low confidence, prefer last good input if available
        user_prefs = self.user_languages.get(user_id, {})
        last_good = (user_prefs.get('last_good_input') or '')
        if last_good:
            return (last_good.split('-')[0] or last_good).lower()

        # Otherwise, prefer user's speaks preferences
        speaks_pref = user_prefs.get('speaks_pref', []) or []
        fallback = self._first_valid_language(speaks_pref)
        if fallback:
            return fallback.split('-')[0].lower()

        # Last resort, do not trust low-confidence random detection; return English default
        return 'en'

    def _resolve_target_language(
        self,
        listener_prefs: Dict[str, Any],
        speaker_language: str
    ) -> str:
        # Normalize
        def _norm(code: Optional[str]) -> Optional[str]:
            if not code:
                return code
            return (code.split('-')[0] or code).lower()
        understands_pref = [c for c in (listener_prefs.get('understands_pref') or [])]
        understands_pref = [_norm(c) for c in understands_pref if c]
        preferred_output = _norm(listener_prefs.get('output'))
        speaker_language = _norm(speaker_language)

        if preferred_output and preferred_output != 'auto':
            return preferred_output

        if speaker_language:
            match = self._first_matching_language(understands_pref, speaker_language)
            if match:
                return match

        fallback_understands = self._first_valid_language(understands_pref)
        if fallback_understands:
            return fallback_understands

        fallback_input = _norm(listener_prefs.get('input'))
        if fallback_input and fallback_input != 'auto':
            return fallback_input

        return 'en'

    @staticmethod
    def _first_valid_language(languages: List[str]) -> Optional[str]:
        for lang in languages:
            if lang and lang != 'auto':
                return lang
        return None

    @staticmethod
    def _first_matching_language(languages: List[str], target: str) -> Optional[str]:
        for lang in languages:
            if lang == target:
                return lang
        return None

    def _get_speaker_reference(self, user_id: UUID) -> Optional[str]:
        """Resolve the best speaker reference wav for the user"""
        fallback_wav = Path(settings.voices_path) / f"{user_id}.wav"
        fallback_path = str(fallback_wav) if fallback_wav.exists() else None

        session = SessionLocal()
        try:
            profile = (
                session.query(VoiceProfile)
                .filter(VoiceProfile.user_id == user_id, VoiceProfile.type == VoiceType.CLONED)
                .order_by(VoiceProfile.is_default.desc(), VoiceProfile.created_at.desc())
                .first()
            )

            if not profile:
                logger.debug(f"🔍 No voice profile found in DB for user {user_id}")
                if fallback_path:
                    logger.debug(f"✅ Found fallback WAV file: {fallback_path}")
                else:
                    logger.debug(f"❌ No fallback WAV file found for user {user_id}")
                return fallback_path

            if not profile.model_path:
                logger.warning(f"⚠️ Voice profile exists but has no model_path for user {user_id}")
                return fallback_path

            model_file = Path(profile.model_path)
            if not model_file.exists():
                logger.warning(
                    f"⚠️ Voice profile model_path does not exist: {profile.model_path} for user {user_id}"
                )
                return fallback_path

            try:
                metadata = json.loads(model_file.read_text())
                speaker_wav = metadata.get("speaker_wav")
                
                if not speaker_wav:
                    logger.warning(
                        f"⚠️ Voice profile metadata missing 'speaker_wav' field for user {user_id}"
                    )
                    return fallback_path
                
                if not Path(speaker_wav).exists():
                    logger.warning(
                        f"⚠️ Speaker WAV file does not exist: {speaker_wav} for user {user_id}"
                    )
                    return fallback_path
                
                logger.debug(f"✅ Found speaker WAV from profile: {speaker_wav} for user {user_id}")
                return speaker_wav
                
            except json.JSONDecodeError as exc:
                logger.warning(
                    f"⚠️ Failed to parse voice profile metadata JSON for user {user_id}: {exc}"
                )
                return fallback_path
            except Exception as exc:
                logger.warning(
                    f"⚠️ Unexpected error reading voice profile metadata for user {user_id}: {exc}"
                )
                return fallback_path

        finally:
            session.close()

    @staticmethod
    def _chunk_text_for_tts(text: str, max_chars: int) -> List[str]:
        """Split long sentences so XTTS stays within its 400-token limit (~250 chars)"""
        cleaned = text.strip()
        if not cleaned:
            return []
        if len(cleaned) <= max_chars:
            return [cleaned]

        sentences = re.split(r'(?<=[\.\?\!\n])\s+', cleaned)
        chunks: List[str] = []
        buffer = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(sentence) > max_chars:
                # Flush existing buffer before hard splitting the long sentence
                if buffer:
                    chunks.append(buffer.strip())
                    buffer = ""
                for idx in range(0, len(sentence), max_chars):
                    part = sentence[idx:idx + max_chars].strip()
                    if part:
                        chunks.append(part)
                continue

            prospective = f"{buffer} {sentence}".strip() if buffer else sentence
            if len(prospective) <= max_chars:
                buffer = prospective
            else:
                if buffer:
                    chunks.append(buffer)
                buffer = sentence

        if buffer:
            chunks.append(buffer.strip())

        return chunks


# Global instance
audio_stream_processor = AudioStreamProcessor()
