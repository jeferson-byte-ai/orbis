"""
Coqui TTS Streaming Service with Voice Cloning
Ultra-low latency TTS using XTTS v2 streaming inference
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional, AsyncGenerator, Tuple
import threading

import numpy as np
import torch

try:
    from torch.serialization import add_safe_globals
except (ImportError, AttributeError):
    add_safe_globals = None

logger = logging.getLogger(__name__)


class CoquiStreamingTTSService:
    """
    Coqui XTTS v2 service with streaming support for ultra-low latency voice cloning.
    
    Key optimizations:
    1. Streaming inference - generates audio in chunks as it processes
    2. Pre-computed speaker embeddings - caches voice profile for faster synthesis
    3. Smaller chunk processing - processes text in smaller pieces
    4. Async-friendly design - non-blocking synthesis
    """
    
    def __init__(
        self, 
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        device: str = "cuda"
    ):
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.tts = None
        self.model = None  # Direct XTTS model reference for streaming
        self._speaker_embeddings_cache: dict = {}  # Cache speaker embeddings
        self._gpt_cond_latent_cache: dict = {}  # Cache GPT conditioning
        self._lock = threading.Lock()
        logger.info(f"Initializing Coqui Streaming TTS: {model_name} on {self.device}")
    
    def load(self):
        """Load TTS model with streaming support"""
        try:
            from TTS.api import TTS
            from TTS.tts.configs.xtts_config import XttsConfig

            if add_safe_globals is not None:
                try:
                    safe_globals = [XttsConfig]
                    try:
                        from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
                        safe_globals.extend([XttsAudioConfig, XttsArgs])
                    except Exception:
                        pass
                    try:
                        from TTS.config.shared_configs import BaseDatasetConfig
                        safe_globals.append(BaseDatasetConfig)
                    except Exception:
                        pass
                    add_safe_globals(safe_globals)
                    logger.info("✅ Registered XTTS safe globals for streaming service")
                except Exception as e:
                    logger.warning(f"⚠️ Could not register safe globals: {e}")

            self.tts = TTS(self.model_name, gpu=(self.device == "cuda"))
            
            # Get direct model reference for streaming
            if hasattr(self.tts, 'synthesizer') and hasattr(self.tts.synthesizer, 'tts_model'):
                self.model = self.tts.synthesizer.tts_model
                logger.info("✅ Got direct XTTS model reference for streaming")
            
            logger.info("✅ Coqui Streaming TTS loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Coqui Streaming TTS: {e}")
            raise
    
    def _get_or_compute_speaker_embedding(
        self, 
        speaker_wav: str
    ) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Get cached speaker embedding or compute it.
        Returns (gpt_cond_latent, speaker_embedding)
        """
        if not speaker_wav or not Path(speaker_wav).exists():
            return None, None
        
        cache_key = str(Path(speaker_wav).resolve())
        
        # Check cache
        if cache_key in self._gpt_cond_latent_cache:
            logger.debug(f"🎯 Using cached speaker embedding for {cache_key}")
            return (
                self._gpt_cond_latent_cache[cache_key],
                self._speaker_embeddings_cache.get(cache_key)
            )
        
        # Compute embedding
        try:
            if self.model is None:
                logger.warning("Model not available for embedding computation")
                return None, None
            
            logger.info(f"🔄 Computing speaker embedding for {speaker_wav}...")
            start = time.time()
            
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=speaker_wav
            )
            
            # Cache it
            with self._lock:
                self._gpt_cond_latent_cache[cache_key] = gpt_cond_latent
                self._speaker_embeddings_cache[cache_key] = speaker_embedding
            
            elapsed = (time.time() - start) * 1000
            logger.info(f"✅ Speaker embedding computed in {elapsed:.0f}ms")
            
            return gpt_cond_latent, speaker_embedding
            
        except Exception as e:
            logger.error(f"❌ Failed to compute speaker embedding: {e}")
            return None, None
    
    async def preload_speaker(self, speaker_wav: str) -> bool:
        """
        Pre-compute and cache speaker embedding for faster synthesis later.
        Call this when user joins a room.
        """
        def _preload():
            return self._get_or_compute_speaker_embedding(speaker_wav)
        
        gpt_cond, speaker_emb = await asyncio.to_thread(_preload)
        return gpt_cond is not None
    
    async def synthesize_streaming(
        self,
        text: str,
        language: str,
        speaker_wav: Optional[str] = None,
        sample_rate: int = 24000
    ) -> AsyncGenerator[np.ndarray, None]:
        """
        Stream audio chunks as they are generated.
        Yields numpy arrays of audio data.
        
        This is much faster for real-time applications because:
        1. First audio chunk arrives quickly
        2. Audio plays while rest is being generated
        """
        if not text.strip():
            return
        
        def _stream_blocking():
            """Blocking generator that yields audio chunks"""
            try:
                if self.model is None:
                    if self.tts is None:
                        self.load()
                    if self.model is None:
                        logger.error("Cannot stream: model not available")
                        return
                
                # Get cached or compute speaker embedding
                gpt_cond_latent = None
                speaker_embedding = None
                
                if speaker_wav:
                    gpt_cond_latent, speaker_embedding = self._get_or_compute_speaker_embedding(speaker_wav)
                
                if gpt_cond_latent is None or speaker_embedding is None:
                    # Fallback to non-streaming if no speaker embedding
                    logger.warning("⚠️ No speaker embedding, using standard synthesis")
                    if self.tts:
                        audio = self.tts.tts(text=text, language=language)
                        yield np.array(audio, dtype=np.float32)
                    return
                
                # Use streaming inference
                logger.info(f"🎵 Starting streaming synthesis: '{text[:30]}...'")
                start = time.time()
                
                chunks = self.model.inference_stream(
                    text=text,
                    language=language,
                    gpt_cond_latent=gpt_cond_latent,
                    speaker_embedding=speaker_embedding,
                    stream_chunk_size=20,  # Smaller chunks = lower latency
                    enable_text_splitting=True
                )
                
                chunk_count = 0
                total_samples = 0
                first_chunk_time = None
                
                for chunk in chunks:
                    if chunk is not None:
                        if first_chunk_time is None:
                            first_chunk_time = (time.time() - start) * 1000
                            logger.info(f"⚡ First audio chunk in {first_chunk_time:.0f}ms")
                        
                        audio_chunk = chunk.cpu().numpy().squeeze()
                        if audio_chunk.size > 0:
                            chunk_count += 1
                            total_samples += len(audio_chunk)
                            yield audio_chunk
                
                elapsed = (time.time() - start) * 1000
                logger.info(
                    f"✅ Streaming complete: {chunk_count} chunks, "
                    f"{total_samples} samples in {elapsed:.0f}ms"
                )
                
            except Exception as e:
                logger.error(f"❌ Streaming synthesis error: {e}")
                # Fallback to standard synthesis
                if self.tts:
                    try:
                        audio = self.tts.tts(text=text, language=language, speaker_wav=speaker_wav)
                        yield np.array(audio, dtype=np.float32)
                    except Exception as e2:
                        logger.error(f"❌ Fallback synthesis also failed: {e2}")
        
        # Run blocking generator in thread and yield results
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        done = asyncio.Event()
        
        def _producer():
            try:
                for chunk in _stream_blocking():
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            finally:
                loop.call_soon_threadsafe(done.set)
        
        thread = threading.Thread(target=_producer, daemon=True)
        thread.start()
        
        while not done.is_set() or not queue.empty():
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield chunk
            except asyncio.TimeoutError:
                continue
    
    async def synthesize(
        self,
        text: str,
        language: str,
        speaker_wav: Optional[str] = None,
        sample_rate: int = 24000
    ) -> np.ndarray:
        """
        Standard synthesis (non-streaming) with optimizations.
        Uses cached speaker embeddings for faster processing.
        """
        chunks = []
        async for chunk in self.synthesize_streaming(text, language, speaker_wav, sample_rate):
            chunks.append(chunk)
        
        if not chunks:
            return np.zeros(sample_rate, dtype=np.float32)
        
        return np.concatenate(chunks)
    
    def clear_cache(self, speaker_wav: Optional[str] = None):
        """Clear speaker embedding cache"""
        with self._lock:
            if speaker_wav:
                cache_key = str(Path(speaker_wav).resolve())
                self._gpt_cond_latent_cache.pop(cache_key, None)
                self._speaker_embeddings_cache.pop(cache_key, None)
            else:
                self._gpt_cond_latent_cache.clear()
                self._speaker_embeddings_cache.clear()
        logger.info("🧹 Speaker embedding cache cleared")
    
    def get_supported_languages(self) -> list:
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 
            'ru', 'nl', 'cs', 'ar', 'zh-cn', 'ja', 'hu', 'ko'
        ]


# Singleton instance
coqui_streaming_service = CoquiStreamingTTSService()
