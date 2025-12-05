"""
Real-time Audio Stream Processor
Handles ASR → MT → TTS pipeline with latency optimization
"""
import asyncio
import base64
import json
import logging
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
            'understands_pref': list(understands_pref or [])
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
        
        audio_chunk_manager.clear_audio_buffer(user_id)
        logger.info(f"Stopped audio processing for user {user_id}")
    
    async def _process_audio_loop(self, user_id: UUID):
        """Background loop to process audio chunks"""
        try:
            while True:
                await asyncio.sleep(0.1)  # Process every 100ms
                
                if user_id not in self.user_languages:
                    break
                
                audio_chunks = audio_chunk_manager.consume_audio_chunks(user_id)
                if not audio_chunks:
                    continue
                
                # Process the latest chunk
                combined_chunk = b"".join(audio_chunks)
                if not combined_chunk:
                    continue

                await self._process_audio_chunk(user_id, combined_chunk)
                
        except asyncio.CancelledError:
            logger.info(f"Audio processing stopped for user {user_id}")
        except Exception as e:
            logger.error(f"Audio processing error for user {user_id}: {e}")
    
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
            
            # Step 2: ASR - Speech to Text (Lazy Load)
            asr_start_time = time.time()
            
            # Ensure Whisper is loaded
            if not await lazy_loader.ensure_loaded(ModelType.WHISPER):
                await self._notify_translation_error(user_id, "asr", "Speech recognition model unavailable")
                return

            if not getattr(whisper_service, "model_loaded", False):
                await self._notify_translation_error(user_id, "asr", "Whisper model failed to load")
                return
            
            transcribed_text, detected_lang, _ = await whisper_service.transcribe(
                audio_array,
                language=input_lang if input_lang != 'auto' else None,
                sample_rate=self.input_sample_rate
            )
            asr_latency = (time.time() - asr_start_time) * 1000
            
            if not transcribed_text.strip():
                logger.debug(f"No speech detected for user {user_id}")
                return  # No speech detected
            
            # Update detected language if auto mode
            if input_lang == 'auto' and detected_lang:
                self.user_languages[user_id]['input'] = detected_lang
                input_lang = detected_lang
            
            speaker_language = self._determine_speaker_language(user_id, input_lang, detected_lang)

            logger.info(f"🎤 User {user_id} spoke in {speaker_language}: '{transcribed_text}'")
            
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
            if not listeners:
                logger.debug(f"No listeners in room {room_id}")
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

                # Check if we already processed this language
                target_text = translations_cache.get(target_language)

                if not target_text:
                    translation_start = time.time()
                    
                    # Translate text from speaker's language to listener's language
                    target_text = await self._translate_text(
                        transcribed_text,
                        speaker_language,
                        target_language
                    )
                    translation_latency = (time.time() - translation_start) * 1000
                    mt_latency += translation_latency

                    logger.info(f"🌐 Translated to {target_language}: '{target_text}'")

                    translations_cache[target_language] = target_text

                # Synthesize audio for this listener (use listener voice, fallback to speaker voice)
                tts_start_time = time.time()
                target_audio, used_fallback_voice = await self._text_to_speech(
                    target_text,
                    target_language,
                    voice_user_id=target_user_id,
                    fallback_user_id=user_id
                )
                tts_latency = (time.time() - tts_start_time) * 1000
                tts_total_latency += tts_latency

                if not target_audio:
                    logger.warning(
                        f"⚠️ No translated audio generated for {input_lang} → {target_language}"
                    )
                    continue

                # Send translated audio to listener
                send_start_time = time.time()
                await self._send_translated_audio(
                    room_id=room_id,
                    source_user_id=user_id,
                    target_user_id=target_user_id,
                    audio_data=target_audio,
                    text=target_text,
                    target_language=target_language,
                    voice_fallback=used_fallback_voice
                )
                send_latency += (time.time() - send_start_time) * 1000
                processed_count += 1
            
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
            # Use NLLB service for translation
            translated_text = await nllb_service.translate(
                text, 
                source,
                target
            )
            return translated_text
        except Exception as e:
            logger.error(f"Translation service error: {e}")
            # Fallback to mock translation
            return f"[{(target or 'en').upper()}] {text}"
    
    async def _text_to_speech(
        self,
        text: str,
        language: str,
        voice_user_id: UUID,
        fallback_user_id: UUID
    ) -> Tuple[bytes, bool]:
        """Convert text to speech with listener voice, falling back as needed"""
        try:
            speaker_wav = self._get_speaker_reference(voice_user_id)
            used_fallback = False

            if not speaker_wav and fallback_user_id != voice_user_id:
                speaker_wav = self._get_speaker_reference(fallback_user_id)
                used_fallback = bool(speaker_wav)

            audio_array = await coqui_service.synthesize(
                text=text,
                language=language,
                speaker_wav=speaker_wav,
                sample_rate=self.output_sample_rate
            )

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
        """Send translated audio to a specific participant"""
        if not audio_data:
            return

        encoded_audio = base64.b64encode(audio_data).decode("ascii")
        audio_message = {
            'type': 'translated_audio',
            'user_id': str(source_user_id),
            'audio': {
                'data': encoded_audio,
                'encoding': 'pcm_s16le',
                'sample_rate': self.output_sample_rate
            },
            'audio_data': encoded_audio,
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
        if input_lang:
            config['input'] = input_lang
        if output_lang:
            config['output'] = output_lang
        if speaks_pref is not None:
            config['speaks_pref'] = list(speaks_pref)
        if understands_pref is not None:
            config['understands_pref'] = list(understands_pref)

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
        detected_lang: Optional[str]
    ) -> str:
        if configured_input and configured_input != 'auto':
            return configured_input
        if detected_lang:
            return detected_lang

        user_prefs = self.user_languages.get(user_id, {})
        speaks_pref = user_prefs.get('speaks_pref', []) or []
        fallback = self._first_valid_language(speaks_pref)
        return fallback or 'en'

    def _resolve_target_language(
        self,
        listener_prefs: Dict[str, Any],
        speaker_language: str
    ) -> str:
        understands_pref = listener_prefs.get('understands_pref') or []
        preferred_output = listener_prefs.get('output')

        if speaker_language:
            match = self._first_matching_language(understands_pref, speaker_language)
            if match:
                return match

        if preferred_output and preferred_output != 'auto':
            return preferred_output

        fallback_understands = self._first_valid_language(understands_pref)
        if fallback_understands:
            return fallback_understands

        fallback_input = listener_prefs.get('input')
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

            if not profile or not profile.model_path:
                return fallback_path

            model_file = Path(profile.model_path)
            if not model_file.exists():
                return fallback_path

            try:
                metadata = json.loads(model_file.read_text())
                speaker_wav = metadata.get("speaker_wav")
                if speaker_wav and Path(speaker_wav).exists():
                    return speaker_wav
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to parse voice profile metadata for %s: %s", user_id, exc)

            return fallback_path
        finally:
            session.close()


# Global instance
audio_stream_processor = AudioStreamProcessor()
