"""
Real-time Audio Stream Processor
Handles ASR → MT → TTS pipeline with latency optimization
"""
import asyncio
import base64
import logging
import time
from pathlib import Path
from typing import Dict
from uuid import UUID

import numpy as np

from ml.asr.whisper_service import whisper_service
from ml.mt.nllb_service import nllb_service
from ml.tts.coqui_service import coqui_service
from backend.config import settings
from backend.services.audio_pipeline.websocket_manager import connection_manager, audio_chunk_manager
from backend.services.lazy_loader import lazy_loader, ModelType

logger = logging.getLogger(__name__)


class AudioStreamProcessor:
    """Processes audio streams in real-time with translation"""
    
    def __init__(self):
        self.user_languages: Dict[UUID, Dict[str, str]] = {}  # {user_id: {'input': 'pt', 'output': 'en'}}
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

    async def start_processing(self, user_id: UUID, room_id: str, input_lang: str = 'auto', output_lang: str = 'en'):
        """Start processing audio for a user"""
        self.user_languages[user_id] = {
            'input': input_lang,
            'output': output_lang,
            'room_id': room_id
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
            user_config = self.user_languages[user_id]
            room_id = user_config['room_id']
            input_lang = user_config['input']
            output_lang = user_config['output']

            if output_lang in (None, 'auto'):
                output_lang = input_lang if input_lang not in (None, 'auto') else 'en'
            
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
            
            # Step 3: Machine Translation (Lazy Load)
            mt_start_time = time.time()
            
            # Ensure NLLB is loaded
            if not await lazy_loader.ensure_loaded(ModelType.NLLB):
                await self._notify_translation_error(user_id, "mt", "Translation model unavailable")
                return

            if getattr(nllb_service, "model", None) is None:
                await self._notify_translation_error(user_id, "mt", "NLLB model failed to load")
                return
            
            translated_text = await self._translate_text(transcribed_text, input_lang or detected_lang, output_lang)
            mt_latency = (time.time() - mt_start_time) * 1000
            
            # Step 4: Text-to-Speech with Voice Cloning (Lazy Load)
            tts_start_time = time.time()
            
            # Ensure Coqui TTS is loaded
            if not await lazy_loader.ensure_loaded(ModelType.COQUI):
                await self._notify_translation_error(user_id, "tts", "Voice synthesis model unavailable")
                return

            if getattr(coqui_service, "tts", None) is None:
                await self._notify_translation_error(user_id, "tts", "Coqui TTS model failed to load")
                return
            
            translated_audio = await self._text_to_speech(translated_text, output_lang, user_id)
            tts_latency = (time.time() - tts_start_time) * 1000
            if not translated_audio:
                logger.debug(f"No translated audio generated for user {user_id}")
                return
            
            # Step 5: Send translated audio to room
            send_start_time = time.time()
            await self._send_translated_audio(room_id, user_id, translated_audio, translated_text)
            send_latency = (time.time() - send_start_time) * 1000
            
            # Calculate and log latency
            total_processing_time = (time.time() - start_time) * 1000
            logger.info(
                f"User {user_id} processed in {total_processing_time:.1f}ms "
                f"(ASR: {asr_latency:.1f}ms, MT: {mt_latency:.1f}ms, TTS: {tts_latency:.1f}ms, Send: {send_latency:.1f}ms): "
                f"'{transcribed_text}' → '{translated_text}'"
            )
            
            if total_processing_time > self.latency_target_ms:
                logger.warning(f"Latency exceeded target: {total_processing_time:.1f}ms > {self.latency_target_ms}ms")
                
        except Exception as e:
            logger.error(f"Error processing audio chunk for user {user_id}: {e}", exc_info=True)
    
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
    
    async def _text_to_speech(self, text: str, language: str, user_id: UUID) -> bytes:
        """Convert text to speech with voice cloning"""
        try:
            # Get user's voice profile path if available
            voice_profile_path = Path(settings.voices_path) / f"{user_id}.wav"
            speaker_wav = str(voice_profile_path) if voice_profile_path.exists() else None

            audio_array = await coqui_service.synthesize(
                text=text,
                language=language,
                speaker_wav=speaker_wav,
                sample_rate=self.output_sample_rate
            )

            if audio_array.size == 0:
                return b""

            audio_array = np.clip(audio_array, -1.0, 1.0)
            pcm_audio = (audio_array * 32767).astype(np.int16)
            return pcm_audio.tobytes()

        except Exception as e:
            logger.error(f"TTS service error: {e}")
            # Fallback to mock audio
            return b""
    
    async def _send_translated_audio(self, room_id: str, source_user_id: UUID, audio_data: bytes, text: str):
        """Send translated audio to all room participants except source"""
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
            'timestamp': time.time()
        }
        
        await connection_manager.send_audio_to_room(room_id, audio_message, exclude_user=source_user_id)
    
    def update_user_language(self, user_id: UUID, input_lang: str, output_lang: str):
        """Update user's language preferences"""
        if user_id in self.user_languages:
            self.user_languages[user_id]['input'] = input_lang
            self.user_languages[user_id]['output'] = output_lang
            logger.info(f"Updated languages for user {user_id}: {input_lang}→{output_lang}")


# Global instance
audio_stream_processor = AudioStreamProcessor()
