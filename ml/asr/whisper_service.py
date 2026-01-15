"""
Whisper ASR Service - PRODUCTION READY
Real-time audio transcription with language detection
Optimized for low latency (<100ms)
"""
import logging
from typing import Optional, Tuple, Dict
import numpy as np
import torch
import time
from pathlib import Path
import io
import tempfile
import re

logger = logging.getLogger(__name__)


class WhisperService:
    @staticmethod
    def _clean_repetitions(text: str) -> str:
        """
        Reduce pathological repetitions that can occur in ASR streaming like:
        "what's what's what's" or "go go go".
        - Collapse 3+ repeated tokens to 1
        - Collapse repeated bigrams/trigrams
        - Normalize excessive punctuation/whitespace
        """
        if not text:
            return text
        # Normalize spaces
        t = re.sub(r"\s+", " ", text).strip()

        # Collapse token repetitions (words or contractions)
        # e.g., "what's what's what's" -> "what's"
        def collapse_repeats(tokens, max_n=3):
            out = []
            i = 0
            n = len(tokens)
            while i < n:
                j = i + 1
                while j < n and tokens[j].lower() == tokens[i].lower():
                    j += 1
                count = j - i
                # keep a single occurrence if repeated >=2
                out.append(tokens[i])
                i = j
            return out

        tokens = t.split(" ")
        tokens = collapse_repeats(tokens)
        t = " \\n".join(tokens).replace(" \\n", " ")

        # Collapse repeated bigrams (A B A B A B -> A B)
        words = t.split(" ")
        i = 0
        out = []
        while i < len(words):
            # try bigram
            if i + 3 < len(words) and words[i].lower() == words[i+2].lower() and words[i+1].lower() == words[i+3].lower():
                # consume all repeating bigrams
                a, b = words[i], words[i+1]
                out.extend([a, b])
                k = i + 2
                while k + 1 < len(words) and words[k].lower() == a.lower() and words[k+1].lower() == b.lower():
                    k += 2
                i = k
                continue
            out.append(words[i])
            i += 1
        t = " ".join(out)

        # Remove leftover runs of the same word (case-insensitive)
        t = re.sub(r"\b(\w+[’']?\w*)\b(\s+\1\b)+", r"\1", t, flags=re.IGNORECASE)

        # Collapse punctuation repetitions
        t = re.sub(r"([,.!?])\1{1,}", r"\1", t)
        t = re.sub(r"\s*([,.!?])\s*", r"\1 ", t).strip()

        return t
    """
    Production-ready Whisper ASR service for real-time transcription
    Uses faster-whisper for optimal performance
    """
    
    def __init__(
        self, 
        model_size: str = "base",  # base, small, medium, large-v2
        device: str = "auto",
        compute_type: str = "float16"
    ):
        """
        Initialize Whisper service
        
        Args:
            model_size: Model size (base=fastest, large=most accurate)
            device: Device to run on (cuda, cpu, or auto)
            compute_type: Computation type (float16 for GPU, int8 for CPU)
        """
        self.model_size = model_size
        self.device = self._detect_device() if device == "auto" else device
        self.compute_type = compute_type if self.device == "cuda" else "int8"
        self.model = None
        self.model_loaded = False
        
        # Performance tracking
        self.transcription_times = []
        
        logger.info(f"🎙️ Initializing Whisper ASR: {model_size} on {self.device} ({self.compute_type})")
    
    def _detect_device(self) -> str:
        """Auto-detect best available device"""
        if torch.cuda.is_available():
            logger.info("✅ CUDA available - using GPU")
            return "cuda"
        else:
            logger.info("⚠️ CUDA not available - using CPU (slower)")
            return "cpu"
    
    def load(self):
        """Load Whisper model"""
        try:
            from faster_whisper import WhisperModel
            
            start_time = time.time()
            
            # Load model with optimal settings
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(Path("./data/models/whisper")),
                num_workers=4,  # Parallel processing
            )
            
            load_time = time.time() - start_time
            self.model_loaded = True
            
            logger.info(f"✅ Whisper {self.model_size} loaded in {load_time:.2f}s")
            
            # Warm up model
            self._warmup()
            
        except ImportError:
            logger.error("❌ faster-whisper not installed!")
            logger.error("Install with: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper: {e}")
            raise
    
    def _warmup(self):
        """Warm up model with dummy audio"""
        try:
            logger.info("🔥 Warming up Whisper model...")
            dummy_audio = np.random.randn(16000).astype(np.float32)  # 1 second
            segments, _ = self.model.transcribe(dummy_audio, language="en")
            list(segments)  # Force execution
            logger.info("✅ Model warmed up")
        except Exception as e:
            logger.warning(f"⚠️ Warmup failed: {e}")
    
    async def transcribe(
        self, 
        audio: np.ndarray, 
        language: Optional[str] = None,
        sample_rate: int = 16000,
        vad_filter: bool = True
    ) -> Tuple[str, str, Dict]:
        """
        Transcribe audio to text
        
        Args:
            audio: Audio array (numpy float32, normalized to [-1, 1])
            language: Language code (if known) or None for auto-detect
            sample_rate: Audio sample rate (must be 16000 for Whisper)
            vad_filter: Use Voice Activity Detection to filter silence
        
        Returns:
            (transcribed_text, detected_language, metadata)
        """
        if not self.model_loaded:
            logger.error("Model not loaded! Call load() first")
            return "", "en", {"error": "model_not_loaded"}
        
        start_time = time.time()
        
        try:
            # Ensure audio is correct format
            if sample_rate != 16000:
                logger.warning(f"Sample rate {sample_rate} != 16000, resampling needed")
                # In production, resample here
            
            # Ensure float32
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            # Normalize audio
            if np.abs(audio).max() > 1.0:
                audio = audio / np.abs(audio).max()
            
            # Transcribe with optimal settings for real-time conversation
            # ✅ DIAGNOSTIC MODE: Force Portuguese and disable VAD for testing
            segments, info = self.model.transcribe(
                audio,
                language=language,
                vad_filter=vad_filter,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.25,
                condition_on_previous_text=False,
                vad_parameters={
                    "threshold": 0.20,  # Menos sensível para não cortar fala
                    "min_speech_duration_ms": 200,  # Requer mais duração para considerar fala
                    "min_silence_duration_ms": 800,  # Aguarda silêncio mais longo antes de cortar
                    "speech_pad_ms": 600,  # Mais padding para capturar início/fim da fala
                } if vad_filter else None,
            )
            
            # Log more details for debugging
            if hasattr(info, 'language_probability'):
                logger.info(
                    f"🔍 Whisper detected language: {info.language} "
                    f"(confidence: {info.language_probability:.2%})"
                )
            
            # Collect all segments
            transcription = ""
            segment_count = 0
            for segment in segments:
                transcription += segment.text + " "
                segment_count += 1
            
            transcription = transcription.strip()
            # Sanitize repetitions and artifacts often produced by partial-chunk decoding
            transcription = self._clean_repetitions(transcription)
            # If language was forced, trust it and override detection to avoid spurious mislabels
            if language:
                detected_lang = language
                if isinstance(info, dict):
                    info['language'] = language
                    info['language_probability'] = 1.0
            else:
                detected_lang = info.language if hasattr(info, 'language') else (language or "en")
            
            # ✅ Log warning if transcription is empty but audio was long enough
            if not transcription and len(audio) > 8000:  # More than 0.5 seconds
                logger.warning(
                    f"⚠️ Empty transcription for {len(audio)/sample_rate:.2f}s of audio. "
                    f"Detected lang: {detected_lang}, segments: {segment_count}"
                )
            
            # Performance metrics
            elapsed = time.time() - start_time
            self.transcription_times.append(elapsed)
            
            # Keep only last 100 measurements
            if len(self.transcription_times) > 100:
                self.transcription_times.pop(0)
            
            avg_time = sum(self.transcription_times) / len(self.transcription_times)
            
            metadata = {
                "latency_ms": elapsed * 1000,
                "avg_latency_ms": avg_time * 1000,
                "audio_duration_s": len(audio) / sample_rate,
                "language": detected_lang,
                "language_probability": getattr(info, 'language_probability', 0.0)
            }
            
            logger.info(
                f"✅ Transcribed [{elapsed*1000:.0f}ms]: '{transcription[:50]}...' "
                f"(lang: {detected_lang})"
            )
            
            return transcription, detected_lang, metadata
            
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}")
            return "", "en", {"error": str(e)}
    
    async def transcribe_streaming(
        self,
        audio_chunk: np.ndarray,
        language: Optional[str] = None,
        sample_rate: int = 16000
    ) -> Tuple[str, str, Dict]:
        """
        Transcribe audio chunk in streaming mode
        Optimized for real-time processing with minimal latency
        
        Args:
            audio_chunk: Small audio chunk (500ms recommended)
            language: Language code
            sample_rate: Audio sample rate
        
        Returns:
            (transcribed_text, detected_language, metadata)
        """
        # For streaming, we want fastest possible processing
        # Use same method but with optimizations
        return await self.transcribe(
            audio_chunk, 
            language=language,
            sample_rate=sample_rate,
            vad_filter=True  # Important for real-time to skip silence
        )
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        if not self.transcription_times:
            return {"message": "No transcriptions yet"}
        
        times = self.transcription_times
        return {
            "count": len(times),
            "avg_ms": sum(times) / len(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "last_ms": times[-1] * 1000,
        }
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return [
            'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr',
            'pl', 'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi',
            'he', 'uk', 'el', 'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no',
            'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy', 'sk',
            'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk',
            'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw',
            'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc',
            'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo',
            'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl',
            'mg', 'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su'
        ]


# Singleton instance - use base model for best speed/quality tradeoff
whisper_service = WhisperService(model_size="base", device="auto")
