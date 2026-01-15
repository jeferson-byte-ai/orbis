"""
Coqui TTS Service with Voice Cloning
Text-to-Speech with natural voice cloning using XTTS
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch

try:
    from torch.serialization import add_safe_globals
except (ImportError, AttributeError):  # pragma: no cover - older torch versions
    add_safe_globals = None

logger = logging.getLogger(__name__)


class CoquiTTSService:
    """Coqui XTTS service for voice cloning and text-to-speech"""
    
    def __init__(
        self, 
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        device: str = "cuda"
    ):
        """
        Initialize Coqui TTS service
        
        Args:
            model_name: TTS model to use
            device: Device to run on (cuda or cpu)
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.tts = None
        logger.info(f"Initializing Coqui TTS: {model_name} on {self.device}")
    
    def load(self):
        """Load TTS model"""
        try:
            from TTS.api import TTS

            # PyTorch 2.6+ loads checkpoints with weights_only=True by default.
            # Register XTTS config class as safe so torch.load can reconstruct it.
            if add_safe_globals is not None:
                try:
                    from TTS.tts.configs.xtts_config import XttsConfig
                    safe_globals = [XttsConfig]
                    try:
                        from TTS.tts.models.xtts import XttsAudioConfig
                        safe_globals.append(XttsAudioConfig)
                    except Exception:  # noqa: BLE001
                        pass
                    try:
                        from TTS.tts.models.xtts import XttsArgs
                        safe_globals.append(XttsArgs)
                    except Exception:  # noqa: BLE001
                        pass
                    try:
                        from TTS.config.shared_configs import BaseDatasetConfig
                        safe_globals.append(BaseDatasetConfig)
                    except Exception:  # noqa: BLE001
                        pass
                    add_safe_globals(safe_globals)
                    logger.info(
                        "✅ Registered XTTS safe globals for deserialization: %s",
                        ", ".join(cls.__name__ for cls in safe_globals)
                    )
                except Exception as safe_err:  # noqa: BLE001
                    logger.warning("⚠️ Could not register XTTS safe globals: %s", safe_err)

            self.tts = TTS(self.model_name, gpu=(self.device == "cuda"))
            logger.info("✅ Coqui TTS model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Coqui TTS: {e}")
            logger.info("Install with: pip install TTS")
            raise
    
    async def synthesize(
        self,
        text: str,
        language: str,
        speaker_wav: Optional[str] = None,
        sample_rate: int = 22050
    ) -> np.ndarray:
        """
        Synthesize speech from text with optional voice cloning
        Coqui XTTS v2 supports high-quality voice cloning with just 5+ seconds of audio
        
        Args:
            text: Text to synthesize
            language: Language code (e.g., 'en', 'pt', 'es')
            speaker_wav: Path to speaker's voice sample for cloning (5+ seconds)
            sample_rate: Output sample rate
        
        Returns:
            Audio array (numpy)
        """

        def _synthesize_blocking() -> np.ndarray:
            try:
                if self.tts is None:
                    logger.warning("TTS model not loaded, attempting to load...")
                    self.load()
                    if self.tts is None:
                        logger.error("Failed to load TTS model, returning mock audio")
                        return np.zeros(sample_rate, dtype=np.float32)

                if speaker_wav:
                    logger.info("Synthesizing with cloned voice from: %s", speaker_wav)
                    audio = self.tts.tts(
                        text=text,
                        speaker_wav=speaker_wav,
                        language=language
                    )
                else:
                    logger.info("Synthesizing with default voice")
                    audio = self.tts.tts(
                        text=text,
                        language=language
                    )

                audio_array = np.array(audio, dtype=np.float32)
                logger.info(
                    "✅ Synthesized speech: '%s...' in %s (%s samples)",
                    text[:50],
                    language,
                    len(audio_array)
                )
                return audio_array

            except Exception as exc:  # noqa: BLE001
                logger.error("❌ TTS synthesis error: %s", exc)
                return np.zeros(sample_rate, dtype=np.float32)

        return await asyncio.to_thread(_synthesize_blocking)
    
    async def clone_voice(
        self,
        audio_samples: list,
        output_path: str
    ) -> bool:
        """
        Clone voice from audio samples using Coqui XTTS
        Supports short audio samples (5+ seconds)
        
        Args:
            audio_samples: List of paths to audio samples
            output_path: Where to save the cloned voice model
        
        Returns:
            Success status
        """
        try:
            if not audio_samples:
                logger.error("No audio samples provided for voice cloning")
                return False
            
            logger.info(f"Cloning voice from {len(audio_samples)} samples")
            
            # XTTS v2 works great with short samples (5+ seconds)
            # No need for 3 minutes of audio anymore
            if self.tts is None:
                logger.warning("TTS model not loaded, attempting to load...")
                self.load()
            
            output_file = Path(output_path)
            if not output_file.suffix:
                output_file = output_file.with_suffix(".json")
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Store voice profile with reference to audio samples
            # XTTS will use the audio file directly for cloning
            metadata = {
                "created_at": time.time(),
                "sample_count": len(audio_samples),
                "samples": [str(Path(sample).resolve()) for sample in audio_samples],
                "model": self.model_name,
                "device": self.device,
                "speaker_wav": str(Path(audio_samples[0]).resolve()),
                "notes": "Coqui XTTS v2 voice profile - works with short audio samples (5+ seconds)",
            }

            output_file.write_text(json.dumps(metadata, indent=2))
            logger.info(f"✅ Voice profile created successfully: {output_file}")
            logger.info(f"Using speaker reference: {metadata['speaker_wav']}")
            return True
            
        except Exception as e:
            logger.error(f"Voice cloning error: {e}")
            return False
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages for TTS"""
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 
            'ru', 'nl', 'cs', 'ar', 'zh-cn', 'ja', 'hu', 'ko'
        ]


# Singleton instance
coqui_service = CoquiTTSService()