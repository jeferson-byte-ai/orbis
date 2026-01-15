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
from collections import Counter

import numpy as np

from ml.asr.whisper_service import whisper_service
from ml.mt.nllb_service import nllb_service
from ml.mt.fast_marian_service import fast_marian_service
from ml.tts.coqui_service import coqui_service
from ml.tts.coqui_streaming_service import coqui_streaming_service
from backend.config import settings
from backend.db.session import SessionLocal
# Note: avoid importing backend.api.profile here to prevent circular import during app startup
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
        self.output_sample_rate = 24000  # XTTS native sample rate
        self.max_tts_chars = 120  # Smaller chunks for faster streaming
        self.use_streaming_tts = True  # Enable streaming TTS for lower latency
        # Prevent ASR hallucination/repetition: track last transcript per user
        self._last_transcript: Dict[UUID, Tuple[str, float]] = {}
        # Simple energy gate to drop near-silence chunks (tuned)
        # Lower threshold reduces false skips on soft speech
        self._silence_rms_threshold: float = 0.0018
        # Rolling buffers for streaming context and voice activity
        self._rolling_buffers: Dict[UUID, bytes] = {}
        self._last_activity_ts: Dict[UUID, float] = {}
        self._last_process_ts: Dict[UUID, float] = {}
        self._speaking_flags: Dict[UUID, bool] = {}
        self._had_first_transcript: Dict[UUID, bool] = {}
        # Track what translation content has already been sent per (speaker -> listener, language)
        self._last_sent_translations: Dict[Tuple[UUID, UUID, str], str] = {}
        # Per (speaker->listener) sequence counters for audio chunks
        self._seq_counters: Dict[Tuple[UUID, UUID], int] = {}
        # Mute flags per speaker
        self._muted: Dict[UUID, bool] = {}
        # Diagnostics counters per user
        self._diag_counters: Dict[UUID, int] = {}
        # Silence tracking to proactively reset stale rolling contexts on noise
        self._silence_acc_ms: Dict[UUID, float] = {}
        # Consecutive empty-ASR streak guard
        self._empty_asr_streak: Dict[UUID, int] = {}
        # Tail window to preserve minimal context after each processed chunk
        self._context_tail_ms: float = 200.0
        # Track background translation tasks per speaker
        self._translation_tasks: Dict[UUID, List[asyncio.Task]] = {}
        self._translation_semaphores: Dict[UUID, asyncio.Semaphore] = {}
        # Pending transcript aggregation per speaker
        self._pending_transcripts: Dict[UUID, str] = {}
        self._pending_started_at: Dict[UUID, float] = {}
        # Buffer thresholds for when to flush aggregated transcripts into MT/TTS
        # Balanced for complete sentences while maintaining reasonable latency
        self._pending_timeout_ms: float = 3500.0  # Wait up to 3.5s for complete sentence
        self._pending_min_chars: int = 40  # Minimum chars before considering flush
        self._pending_max_chars: int = 150  # Force flush if buffer gets too large
        # Track last language decision to flush buffered text
        # Tuple = (speaker_language, detected_lang, detected_conf, updated_at_ts)
        self._last_detected_state: Dict[UUID, Tuple[str, Optional[str], float, float]] = {}
    
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
        self._translation_tasks[user_id] = []
        self._translation_semaphores[user_id] = asyncio.Semaphore(1)
        self._pending_transcripts.pop(user_id, None)
        self._pending_started_at.pop(user_id, None)
        self._last_detected_state.pop(user_id, None)
        
        # Pre-load speaker embedding for faster TTS (non-blocking)
        asyncio.create_task(self._preload_speaker_embedding(user_id))
        
        logger.info(f"Started audio processing for user {user_id} ({input_lang}→{output_lang})")
    
    async def _preload_speaker_embedding(self, user_id: UUID):
        """Pre-compute speaker embedding for faster TTS synthesis"""
        try:
            speaker_wav = self._get_speaker_reference(user_id)
            if speaker_wav:
                logger.info(f"🔄 Pre-loading speaker embedding for user {user_id}...")
                success = await coqui_streaming_service.preload_speaker(speaker_wav)
                if success:
                    logger.info(f"✅ Speaker embedding pre-loaded for user {user_id}")
                else:
                    logger.warning(f"⚠️ Failed to pre-load speaker embedding for user {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Error pre-loading speaker embedding: {e}")
    
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
        self._had_first_transcript.pop(user_id, None)
        self._rolling_buffers.pop(user_id, None)
        self._last_activity_ts.pop(user_id, None)
        self._last_process_ts.pop(user_id, None)
        self._speaking_flags.pop(user_id, None)
        self._silence_acc_ms.pop(user_id, None)
        self._empty_asr_streak.pop(user_id, None)
        audio_chunk_manager.clear_audio_buffer(user_id)
        logger.info(f"Stopped audio processing for user {user_id}")
        # Clear mute flag
        self._muted.pop(user_id, None)
        # Cancel translation tasks
        tasks = self._translation_tasks.pop(user_id, [])
        for task in tasks:
            task.cancel()
        self._translation_semaphores.pop(user_id, None)
        self._pending_transcripts.pop(user_id, None)
        self._pending_started_at.pop(user_id, None)
        self._last_detected_state.pop(user_id, None)
    
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
                max_seconds = 3.0
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
                # Use a higher threshold for the first utterance after silence, then reduce for continuity
                first_utterance = user_id not in self._had_first_transcript or not self._had_first_transcript.get(user_id)
                min_ms = 450 if first_utterance else 100
                min_bytes = int(self.input_sample_rate * (min_ms/1000.0) * 2)
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
        # Wait for longer silence before considering end of speech
        # This prevents cutting off sentences during natural pauses
        silence_duration = time.time() - last_ts
        if silence_duration > 2.0:  # 2 seconds of silence = end of speech
            self._flush_pending_translation(user_id, "end-of-speech")
            # Reset rolling context and per-listener delta trackers
            self._rolling_buffers.pop(user_id, None)
            self._speaking_flags[user_id] = False
            self._had_first_transcript.pop(user_id, None)
            # Clear last transcript window older than 2s to allow new phrases
            last_text, last_time = self._last_transcript.get(user_id, ("", 0.0))
            if last_text and (time.time() - last_time) > 2.0:
                self._last_transcript.pop(user_id, None)
            # Clear last-sent trackers for this speaker so next utterance starts fresh
            keys_to_clear = [k for k in self._last_sent_translations.keys() if k[0] == user_id]
            for k in keys_to_clear:
                self._last_sent_translations.pop(k, None)
            logger.debug(f"🛑 End-of-speech detected for {user_id}, resetting rolling buffer and last-sent deltas")
    
    def set_muted(self, user_id: UUID, muted: bool):
        self._muted[user_id] = muted
        logger.info(f"🎚️ Set muted={muted} for user {user_id}")

    @staticmethod
    def _looks_repetitive(tokens: List[str]) -> Tuple[bool, Optional[str], float]:
        """Heuristic to flag hallucinated repetitions."""
        if not tokens:
            return False, None, 0.0
        uniq_ratio = len(set(tokens)) / max(1, len(tokens))
        freq = Counter(tokens)
        top_word, top_count = freq.most_common(1)[0]
        top_frac = top_count / max(1, len(tokens))

        # Bigram repetition signal
        bigrams = list(zip(tokens, tokens[1:]))
        top_bigram_frac = 0.0
        if bigrams:
            bfreq = Counter(bigrams)
            top_bigram_frac = bfreq.most_common(1)[0][1] / max(1, len(bigrams))

        repetitive = (
            (len(tokens) >= 30 and top_frac >= 0.30)
            or (len(tokens) >= 40 and uniq_ratio <= 0.45)
            or (len(tokens) >= 24 and top_bigram_frac >= 0.40)
        )
        return repetitive, top_word, top_frac

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
            
            # Convert bytes to numpy array
            audio_array = self._bytes_to_audio_array(audio_data)
            if audio_array.size == 0:
                return

            chunk_ms = len(audio_array) / self.input_sample_rate * 1000.0
            self._silence_acc_ms[user_id] = self._silence_acc_ms.get(user_id, 0.0)

            # Diagnostics: per-user counter and periodic logs
            self._diag_counters[user_id] = self._diag_counters.get(user_id, 0) + 1

            # Drop near-silence chunks to avoid Whisper hallucinations (e.g., repeated 'what is')
            rms = float(np.sqrt(np.mean(np.square(audio_array)))) if audio_array.size > 0 else 0.0

            # Adaptive Gain Control (AGC): if speech is too soft, scale up to target RMS
            try:
                target_rms = 0.010  # target energy for comfortable ASR
                if 0.0002 < rms < 0.0045:
                    gain = min(4.0, target_rms / max(rms, 1e-8))
                    audio_array = np.clip(audio_array * gain, -1.0, 1.0)
                    rms = float(np.sqrt(np.mean(np.square(audio_array)))) if audio_array.size > 0 else rms
            except Exception:
                pass

            if rms < self._silence_rms_threshold:
                self._silence_acc_ms[user_id] += chunk_ms
                if self._silence_acc_ms[user_id] >= 1200.0:
                    self._reset_context_for_silence(user_id, "prolonged near-silence")
                if (self._diag_counters.get(user_id, 0) % 20) == 0 and logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"⏭️ Skipping near-silence after AGC (RMS={rms:.5f}, thr={self._silence_rms_threshold:.5f}) for user {user_id}"
                    )
                return
            else:
                # Reset silence accumulator once we detect speech energy
                self._silence_acc_ms[user_id] = 0.0

            # Periodic diagnostics
            if (self._diag_counters.get(user_id, 0) % 20) == 0 and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[AudioDiag] user={user_id} RMS={rms:.5f} buf_ms={len(audio_array)/self.input_sample_rate*1000:.1f}")

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
                self._empty_asr_streak[user_id] = self._empty_asr_streak.get(user_id, 0) + 1
                if self._empty_asr_streak[user_id] >= 3:
                    self._reset_context_for_silence(user_id, "repeated empty ASR")
                logger.debug(f"⏭️ Skipping empty/noise transcription for user {user_id}")
                return  # No meaningful speech detected
            self._empty_asr_streak[user_id] = 0
            # Detect pathological repetition (hallucination) and trim to protect latency
            tokens = re.findall(r"\w+", transcribed_text.lower())
            if tokens:
                repetitive, top_word, top_frac = self._looks_repetitive(tokens)
                if repetitive:
                    logger.warning(
                        "🧹 Dropping repetitive transcript (top '%s' = %.0f%% of %s tokens); resetting context",
                        top_word or "",
                        top_frac * 100,
                        len(tokens),
                    )
                    self._reset_context_for_silence(user_id, "hallucinated repetition")
                    return

            # Hard cap transcript length to keep MT/TTS responsive even on hallucinations
            max_transcript_chars = self.max_tts_chars * 2  # keep under ~480 chars
            if len(transcribed_text) > max_transcript_chars:
                logger.warning(
                    "✂️ Truncating long transcript from %s to %s chars to protect latency",
                    len(transcribed_text),
                    max_transcript_chars,
                )
                transcribed_text = transcribed_text[:max_transcript_chars]
            # Suppress repeated identical transcriptions within 1.5s window (tuned)
            now = time.time()
            last_text, last_ts = self._last_transcript.get(user_id, ("", 0.0))
            if transcribed_text.lower() == last_text.lower() and (now - last_ts) < 1.5:
                logger.debug(f"⏭️ Suppressing duplicate transcript within window for user {user_id}: '{transcribed_text}'")
                return
            self._last_transcript[user_id] = (transcribed_text, now)
            self._trim_rolling_buffer(user_id)
            if not self._had_first_transcript.get(user_id):
                self._had_first_transcript[user_id] = True
            
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

            # If user is muted, do not emit or translate
            if self._muted.get(user_id):
                logger.debug(f"🔇 User {user_id} is muted — skipping transcript/translation send")
                return
            
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

            if not self._buffer_and_maybe_translate(
                user_id=user_id,
                room_id=room_id,
                speaker_language=speaker_language,
                transcribed_text=transcribed_text,
                detected_lang=detected_lang,
                detected_conf=detected_conf
            ):
                return
            return
                
        except Exception as e:
            logger.error(f"❌ Error processing audio chunk for user {user_id}: {e}", exc_info=True)
    
    def _buffer_and_maybe_translate(
        self,
        user_id: UUID,
        room_id: str,
        speaker_language: str,
        transcribed_text: str,
        detected_lang: Optional[str],
        detected_conf: float,
    ) -> bool:
        """
        Aggregate very short transcripts to avoid firing MT/TTS per syllable.
        Returns True when processing should continue, False to short-circuit.
        """
        now = time.time()

        # Flush buffered text if language decision changed
        last_state = self._last_detected_state.get(user_id)
        if last_state:
            last_speaker_lang, last_detected_lang, *_ = last_state
            if (
                last_speaker_lang != speaker_language
                or (last_detected_lang or None) != (detected_lang or None)
            ):
                self._flush_pending_translation(user_id, "language-change")

        # Track current detection state
        self._last_detected_state[user_id] = (
            speaker_language,
            detected_lang,
            detected_conf,
            now,
        )

        pending = self._pending_transcripts.get(user_id, "")
        if not pending:
            self._pending_started_at[user_id] = now
        sep = " " if pending else ""
        pending = f"{pending}{sep}{transcribed_text}".strip()
        self._pending_transcripts[user_id] = pending

        start_ts = self._pending_started_at.get(user_id, now)
        elapsed_ms = (now - start_ts) * 1000
        
        # Check for sentence-ending punctuation in the NEW text (not just at the end)
        has_sentence_end = any(p in transcribed_text for p in (".", "!", "?", "…"))
        
        # More intelligent flush logic:
        # 1. If we have a complete sentence (punctuation) AND enough chars, flush
        # 2. If timeout reached, flush whatever we have
        # 3. If buffer is getting too large, flush to avoid memory issues
        # 4. Don't flush tiny fragments - wait for more content
        
        buffer_len = len(pending)
        max_chars = getattr(self, '_pending_max_chars', 150)
        
        should_flush = (
            # Complete sentence with good amount of text
            (buffer_len >= self._pending_min_chars and has_sentence_end)
            # Timeout - flush whatever we have if it's meaningful
            or (elapsed_ms >= self._pending_timeout_ms and buffer_len >= 15)
            # Buffer getting too large - must flush
            or buffer_len >= max_chars
        )

        if should_flush:
            return self._flush_pending_translation(user_id, "buffer-ready")
        return True

        if should_flush:
            return self._flush_pending_translation(user_id, "buffer-ready")
        return True

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
    
    async def _fetch_user_language_prefs(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Fetch latest user language preferences directly from DB to avoid circular imports."""
        try:
            session = SessionLocal()
            try:
                from backend.db.models import User  # local import to avoid cycles
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    return None
                speaks = (user.speaks_languages or []) if hasattr(user, 'speaks_languages') else []
                understands = (user.understands_languages or []) if hasattr(user, 'understands_languages') else []
                # Normalize to short codes
                def _norm(code: Optional[str]) -> Optional[str]:
                    if not code:
                        return code
                    return (code.split('-')[0] or code).lower()
                speaks = [(_norm(x) or 'en') for x in speaks if x]
                understands = [(_norm(x) or 'en') for x in understands if x]
                return {
                    'speaks_languages': speaks,
                    'understands_languages': understands,
                }
            finally:
                session.close()
        except Exception:
            return None

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
            use_fast = fast_marian_service.can_translate(source, target)
            fast_failed = False
            for chunk in chunks:
                translated: Optional[str] = None
                if use_fast and not fast_failed:
                    try:
                        translated = await fast_marian_service.translate(chunk, source, target)
                    except Exception as fast_err:  # noqa: BLE001
                        fast_failed = True
                        logger.warning(
                            "⚠️ Fast Marian translation failed for %s→%s: %s. Falling back to NLLB.",
                            source,
                            target,
                            fast_err,
                        )

                if not translated:
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
        """Convert text to speech with speaker's cloned voice using streaming for lower latency"""
        try:
            speaker_wav = self._get_speaker_reference(voice_user_id)
            used_fallback = not bool(speaker_wav)

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

            text_chunks = self._chunk_text_for_tts(text, self.max_tts_chars)
            if not text_chunks:
                return b"", used_fallback

            audio_segments: List[np.ndarray] = []
            
            # Use streaming TTS for lower latency when speaker_wav is available
            if self.use_streaming_tts and speaker_wav:
                try:
                    for chunk in text_chunks:
                        async for audio_chunk in coqui_streaming_service.synthesize_streaming(
                            text=chunk,
                            language=language,
                            speaker_wav=speaker_wav,
                            sample_rate=self.output_sample_rate
                        ):
                            if audio_chunk.size > 0:
                                audio_segments.append(audio_chunk)
                except Exception as stream_err:
                    logger.warning(f"⚠️ Streaming TTS failed, falling back to standard: {stream_err}")
                    audio_segments = []  # Reset and try standard
            
            # Fallback to standard TTS if streaming failed or not available
            if not audio_segments:
                for chunk in text_chunks:
                    audio_array = await coqui_service.synthesize(
                        text=chunk,
                        language=language,
                        speaker_wav=speaker_wav,
                        sample_rate=self.output_sample_rate
                    )
                    if audio_array.size > 0:
                        audio_segments.append(audio_array)

            if not audio_segments:
                return b"", used_fallback

            audio_array = np.concatenate(audio_segments)
            if audio_array.size == 0:
                return b"", used_fallback

            audio_array = np.clip(audio_array, -1.0, 1.0)
            pcm_audio = (audio_array * 32767).astype(np.int16)
            return pcm_audio.tobytes(), used_fallback

        except Exception as e:
            logger.error(f"TTS service error: {e}")
            return b"", True

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
        voice_fallback: bool,
        original_text: str
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
            'original_text': original_text,
            'detected_language': self.user_languages.get(source_user_id, {}).get('last_detected_language')
            or self.user_languages.get(source_user_id, {}).get('input'),
            'text': text,
            'language': target_language,
            'voice_fallback': voice_fallback,
            'timestamp': time.time()
        }
        
        await connection_manager.send_personal_message(target_user_id, audio_message)

    def _schedule_translation_job(
        self,
        user_id: UUID,
        room_id: str,
        speaker_language: str,
        transcribed_text: str,
        detected_lang: Optional[str],
        detected_conf: float,
    ):
        tasks = self._translation_tasks.setdefault(user_id, [])
        task = asyncio.create_task(
            self._translation_delivery(
                user_id,
                room_id,
                speaker_language,
                transcribed_text,
                detected_lang,
                detected_conf,
            )
        )
        tasks.append(task)

        def _cleanup(fut: asyncio.Task, uid: UUID = user_id):
            task_list = self._translation_tasks.get(uid)
            if task_list and fut in task_list:
                task_list.remove(fut)

        task.add_done_callback(_cleanup)

    async def _translation_delivery(
        self,
        user_id: UUID,
        room_id: str,
        speaker_language: str,
        transcribed_text: str,
        detected_lang: Optional[str],
        detected_conf: float,
    ):
        semaphore = self._translation_semaphores.setdefault(user_id, asyncio.Semaphore(1))
        async with semaphore:
            try:
                user_config = self.user_languages.get(user_id)
                if not user_config or self._muted.get(user_id):
                    return

                start_time = time.time()
                input_lang = user_config.get('input')

                if not await lazy_loader.ensure_loaded(ModelType.NLLB):
                    await self._notify_translation_error(user_id, "mt", "Translation model unavailable")
                    return

                if getattr(nllb_service, "model", None) is None:
                    await self._notify_translation_error(user_id, "mt", "NLLB model failed to load")
                    return

                if not await lazy_loader.ensure_loaded(ModelType.COQUI):
                    await self._notify_translation_error(user_id, "tts", "Voice synthesis model unavailable")
                    return

                if getattr(coqui_service, "tts", None) is None:
                    await self._notify_translation_error(user_id, "tts", "Coqui TTS model failed to load")
                    return

                listeners = connection_manager.get_room_users(room_id)
                logger.info(
                    "🔊 Found %s listeners in room %s: %s",
                    len(listeners) if listeners else 0,
                    room_id,
                    listeners,
                )
                if not listeners:
                    logger.warning("⚠️ No listeners in room %s - cannot send translation!", room_id)
                    return

                translations_cache: Dict[str, str] = {}
                mt_latency = 0.0
                tts_total_latency = 0.0
                send_latency = 0.0
                processed_count = 0

                for target_user_id in listeners:
                    if target_user_id == user_id:
                        continue

                    listener_prefs = self.user_languages.get(target_user_id, {})
                    target_language = self._resolve_target_language(listener_prefs, speaker_language)
                    logger.debug(
                        "📢 Processing for listener %s: %s → %s",
                        target_user_id,
                        input_lang,
                        target_language,
                    )

                    effective_source = speaker_language
                    try:
                        if target_language == speaker_language and detected_lang and detected_conf >= 0.40:
                            det_norm = (detected_lang.split('-')[0] or detected_lang).lower()
                            if det_norm != target_language:
                                effective_source = det_norm
                                logger.warning(
                                    "🛡️ Forcing MT source from '%s' to detected '%s' for target '%s'",
                                    speaker_language,
                                    effective_source,
                                    target_language,
                                )
                    except Exception:
                        pass

                    full_translation = translations_cache.get(target_language)

                    if not full_translation:
                        translation_start = time.time()
                        full_translation = await self._translate_text(
                            transcribed_text,
                            effective_source,
                            target_language,
                        )
                        translation_latency = (time.time() - translation_start) * 1000
                        mt_latency += translation_latency
                        logger.info("🌐 Translated to %s: '%s'", target_language, full_translation)
                        translations_cache[target_language] = full_translation

                    try:
                        await connection_manager.send_personal_message(target_user_id, {
                            'type': 'partial_translation',
                            'from_user_id': str(user_id),
                            'text': full_translation,
                            'language': target_language,
                            'timestamp': time.time()
                        })
                    except Exception as _e:
                        logger.debug("Partial translation send failed: %s", _e)

                    key = (user_id, target_user_id, target_language)
                    last_sent = self._last_sent_translations.get(key, "")
                    delta_text = full_translation[len(last_sent):] if full_translation.startswith(last_sent) else full_translation

                    if not delta_text.strip():
                        continue

                    tts_start_time = time.time()
                    target_audio, used_fallback_voice = await self._text_to_speech(
                        delta_text,
                        target_language,
                        voice_user_id=user_id,
                        fallback_user_id=None,
                    )
                    tts_latency = (time.time() - tts_start_time) * 1000
                    tts_total_latency += tts_latency

                    if not target_audio:
                        logger.warning(
                            "⚠️ No translated audio generated for %s → %s",
                            input_lang,
                            target_language,
                        )
                        continue

                    send_start_time = time.time()
                    await self._send_translated_audio(
                        room_id=room_id,
                        source_user_id=user_id,
                        target_user_id=target_user_id,
                        audio_data=target_audio,
                        text=delta_text,
                        target_language=target_language,
                        voice_fallback=used_fallback_voice,
                        original_text=transcribed_text,
                    )
                    send_latency += (time.time() - send_start_time) * 1000
                    processed_count += 1
                    self._last_sent_translations[key] = full_translation

                total_processing_time = (time.time() - start_time) * 1000
                target_languages = list(translations_cache.keys())

                if processed_count > 0:
                    logger.info(
                        "✅ User %s translation job in %.1fms (MT: %.1fms, TTS: %.1fms, Send: %.1fms) | '%s' → %s",
                        user_id,
                        total_processing_time,
                        mt_latency,
                        tts_total_latency,
                        send_latency,
                        transcribed_text,
                        target_languages,
                    )
                else:
                    logger.debug("⚠️ No listeners needed translation for '%s'", transcribed_text)

                if total_processing_time > self.latency_target_ms:
                    logger.warning(
                        "⚠️ Translation latency exceeded target: %.1fms > %sms",
                        total_processing_time,
                        self.latency_target_ms,
                    )

            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("❌ Translation delivery error for user %s: %s", user_id, exc, exc_info=True)
    
    def _reset_context_for_silence(self, user_id: UUID, reason: str):
        """
        Reset rolling context and counters when we accumulate silence/empty ASR.
        This prevents hallucinated mega-chunks after long noisy gaps.
        """
        self._flush_pending_translation(user_id, reason)
        logger.debug("🧹 Resetting context for user %s due to %s", user_id, reason)
        self._rolling_buffers.pop(user_id, None)
        self._last_transcript.pop(user_id, None)
        self._had_first_transcript.pop(user_id, None)
        self._speaking_flags[user_id] = False
        self._silence_acc_ms[user_id] = 0.0
        self._empty_asr_streak[user_id] = 0
        # Clear last-sent trackers for this speaker so next utterance starts fresh
        keys_to_clear = [k for k in self._last_sent_translations.keys() if k[0] == user_id]
        for k in keys_to_clear:
            self._last_sent_translations.pop(k, None)
        self._trim_rolling_buffer(user_id)

    def _flush_pending_translation(self, user_id: UUID, reason: str) -> bool:
        """Flush buffered transcript into the translation pipeline."""
        text = (self._pending_transcripts.pop(user_id, "") or "").strip()
        self._pending_started_at.pop(user_id, None)

        if not text:
            return True  # nothing to do, not a failure

        state = self._last_detected_state.get(user_id)
        cfg = self.user_languages.get(user_id, {})
        room_id = cfg.get("room_id")

        if not state or not room_id:
            logger.debug("⚠️ Cannot flush pending text: missing state/room (reason=%s)", reason)
            return False

        speaker_language, detected_lang, detected_conf, _ts = state
        logger.info(
            "🧾 Flushing buffered transcript (%d chars) for user %s due to %s",
            len(text),
            user_id,
            reason,
        )

        self._schedule_translation_job(
            user_id=user_id,
            room_id=room_id,
            speaker_language=speaker_language,
            transcribed_text=text,
            detected_lang=detected_lang,
            detected_conf=detected_conf,
        )
        return True

    def _trim_rolling_buffer(self, user_id: UUID):
        """Keep only the last ~context_tail_ms of audio after successful processing."""
        buf = self._rolling_buffers.get(user_id)
        if not buf:
            return
        tail_ms = max(self._context_tail_ms, 0.0)
        tail_bytes = int(self.input_sample_rate * (tail_ms / 1000.0) * 2)
        if tail_bytes <= 0:
            self._rolling_buffers.pop(user_id, None)
            return
        if len(buf) > tail_bytes:
            self._rolling_buffers[user_id] = buf[-tail_bytes:]
    
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
