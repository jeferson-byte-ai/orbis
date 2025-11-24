"""
Ultra-Fast Translation Pipeline
Optimized for <250ms latency with advanced caching and streaming
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import hashlib

import redis.asyncio as redis
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.config import settings
# # from backend.db.models import LanguagePair  # TODO: Create this model
# from backend.db.models import TranslationCache  # TODO: Create this model
from backend.db.session import async_engine

logger = logging.getLogger(__name__)


class TranslationQuality(Enum):
    """Translation quality levels"""
    FAST = "fast"  # <100ms, basic quality
    BALANCED = "balanced"  # <250ms, good quality
    HIGH = "high"  # <500ms, high quality
    ULTRA = "ultra"  # <1000ms, ultra quality


class TranslationMode(Enum):
    """Translation modes"""
    REAL_TIME = "real_time"  # Streaming translation
    BATCH = "batch"  # Batch translation
    CONTEXTUAL = "contextual"  # Context-aware translation


@dataclass
class TranslationRequest:
    """Translation request"""
    text: str
    source_language: str
    target_language: str
    quality: TranslationQuality
    mode: TranslationMode
    context: Optional[str] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class TranslationResult:
    """Translation result"""
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    processing_time: float
    quality_score: float
    alternatives: List[str]
    metadata: Dict[str, Any]


@dataclass
class LanguagePairStats:
    """Language pair statistics"""
    pair: str
    total_translations: int
    average_latency: float
    cache_hit_rate: float
    quality_score: float
    last_updated: datetime


class UltraFastTranslationService:
    """Ultra-fast translation service with advanced optimization"""
    
    def __init__(self):
        self.redis = None
        self.models = {}
        self.tokenizers = {}
        self.translation_cache = {}
        self.language_pairs = {}
        self.stats = {}
        self.streaming_sessions = {}
        
        # Model configurations for different quality levels
        self.model_configs = {
            TranslationQuality.FAST: {
                "model_name": "facebook/nllb-200-distilled-600M",
                "max_length": 128,
                "batch_size": 32,
                "use_cache": True,
                "streaming": True
            },
            TranslationQuality.BALANCED: {
                "model_name": "facebook/nllb-200-distilled-600M",
                "max_length": 256,
                "batch_size": 16,
                "use_cache": True,
                "streaming": True
            },
            TranslationQuality.HIGH: {
                "model_name": "facebook/nllb-200-3.3B",
                "max_length": 512,
                "batch_size": 8,
                "use_cache": True,
                "streaming": False
            },
            TranslationQuality.ULTRA: {
                "model_name": "facebook/nllb-200-3.3B",
                "max_length": 1024,
                "batch_size": 4,
                "use_cache": True,
                "streaming": False
            }
        }
        
        # Language code mappings
        self.language_codes = {
            "en": "eng_Latn",
            "pt": "por_Latn",
            "es": "spa_Latn",
            "fr": "fra_Latn",
            "de": "deu_Latn",
            "it": "ita_Latn",
            "ru": "rus_Cyrl",
            "zh": "zho_Hans",
            "ja": "jpn_Jpan",
            "ko": "kor_Hang",
            "ar": "arb_Arab",
            "hi": "hin_Deva",
            "th": "tha_Thai",
            "vi": "vie_Latn",
            "tr": "tur_Latn",
            "pl": "pol_Latn",
            "nl": "nld_Latn",
            "sv": "swe_Latn",
            "da": "dan_Latn",
            "no": "nor_Latn"
        }
    
    async def initialize(self):
        """Initialize ultra-fast translation service"""
        try:
            # Connect to Redis
            self.redis = redis.from_url(settings.redis_url)
            await self.redis.ping()
            
            # Load models for different quality levels
            for quality, config in self.model_configs.items():
                await self._load_translation_model(quality, config)
            
            # Load language pair statistics
            await self._load_language_pair_stats()
            
            # Start background tasks
            asyncio.create_task(self._cache_cleanup_worker())
            asyncio.create_task(self._stats_update_worker())
            
            logger.info("✅ Ultra-Fast Translation Service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Ultra-Fast Translation Service: {e}")
    
    async def _load_translation_model(self, quality: TranslationQuality, config: Dict[str, Any]):
        """Load translation model for specific quality level"""
        try:
            model_name = config["model_name"]
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.tokenizers[quality] = tokenizer
            
            # Load model
            model = AutoModel.from_pretrained(model_name)
            model.eval()
            self.models[quality] = model
            
            logger.info(f"✅ Translation model loaded for quality: {quality.value}")
        except Exception as e:
            logger.error(f"❌ Failed to load translation model for {quality.value}: {e}")
    
    async def translate(self, request: TranslationRequest) -> TranslationResult:
        """Translate text with ultra-fast processing"""
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check cache first
        cached_result = await self._get_cached_translation(cache_key)
        if cached_result:
            logger.info(f"Cache hit for translation: {cache_key}")
            return cached_result
        
        # Get model configuration
        model_config = self.model_configs[request.quality]
        
        # Preprocess text
        processed_text = await self._preprocess_text(request.text, request.source_language)
        
        # Translate based on mode
        if request.mode == TranslationMode.REAL_TIME:
            result = await self._translate_real_time(processed_text, request, model_config)
        elif request.mode == TranslationMode.BATCH:
            result = await self._translate_batch(processed_text, request, model_config)
        elif request.mode == TranslationMode.CONTEXTUAL:
            result = await self._translate_contextual(processed_text, request, model_config)
        else:
            result = await self._translate_standard(processed_text, request, model_config)
        
        # Post-process translation
        result.translated_text = await self._postprocess_text(
            result.translated_text, 
            request.target_language
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        result.processing_time = processing_time
        
        # Cache result
        await self._cache_translation(cache_key, result)
        
        # Update statistics
        await self._update_translation_stats(request, processing_time, result.quality_score)
        
        logger.info(f"Translation completed in {processing_time:.3f}s")
        return result
    
    def _generate_cache_key(self, request: TranslationRequest) -> str:
        """Generate cache key for translation request"""
        # Create hash of request parameters
        key_data = {
            "text": request.text,
            "source": request.source_language,
            "target": request.target_language,
            "quality": request.quality.value,
            "mode": request.mode.value
        }
        
        if request.context:
            key_data["context"] = request.context
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def _get_cached_translation(self, cache_key: str) -> Optional[TranslationResult]:
        """Get cached translation result"""
        if not self.redis:
            return None
        
        try:
            cached_data = await self.redis.get(f"translation:{cache_key}")
            if cached_data:
                data = json.loads(cached_data)
                return TranslationResult(**data)
        except Exception as e:
            logger.warning(f"Failed to get cached translation: {e}")
        
        return None
    
    async def _cache_translation(self, cache_key: str, result: TranslationResult):
        """Cache translation result"""
        if not self.redis:
            return
        
        try:
            # Cache for 24 hours
            await self.redis.setex(
                f"translation:{cache_key}",
                86400,
                json.dumps(result.__dict__, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to cache translation: {e}")
    
    async def _preprocess_text(self, text: str, source_language: str) -> str:
        """Preprocess text for translation"""
        # Clean and normalize text
        text = text.strip()
        
        # Handle special characters
        text = text.replace('\n', ' ')
        text = text.replace('\t', ' ')
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Language-specific preprocessing
        if source_language == "zh":
            # Chinese text preprocessing
            pass
        elif source_language == "ar":
            # Arabic text preprocessing
            pass
        
        return text
    
    async def _translate_standard(self, text: str, request: TranslationRequest, 
                                model_config: Dict[str, Any]) -> TranslationResult:
        """Standard translation"""
        model = self.models[request.quality]
        tokenizer = self.tokenizers[request.quality]
        
        # Get language codes
        source_code = self.language_codes.get(request.source_language, request.source_language)
        target_code = self.language_codes.get(request.target_language, request.target_language)
        
        # Tokenize input
        inputs = tokenizer(
            text,
            return_tensors="pt",
            max_length=model_config["max_length"],
            truncation=True,
            padding=True
        )
        
        # Translate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=model_config["max_length"],
                num_beams=4,
                early_stopping=True
            )
        
        # Decode output
        translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Calculate confidence (mock for now)
        confidence = 0.85
        
        # Generate alternatives (mock for now)
        alternatives = [translated_text + " (alt1)", translated_text + " (alt2)"]
        
        return TranslationResult(
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence=confidence,
            processing_time=0.0,  # Will be set later
            quality_score=0.85,
            alternatives=alternatives,
            metadata={"method": "standard", "model": model_config["model_name"]}
        )
    
    async def _translate_real_time(self, text: str, request: TranslationRequest, 
                                 model_config: Dict[str, Any]) -> TranslationResult:
        """Real-time streaming translation"""
        # For real-time, we use smaller chunks and streaming
        chunk_size = 50  # characters
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        translated_chunks = []
        total_confidence = 0
        
        for chunk in chunks:
            # Translate chunk
            chunk_result = await self._translate_standard(chunk, request, model_config)
            translated_chunks.append(chunk_result.translated_text)
            total_confidence += chunk_result.confidence
        
        # Combine chunks
        translated_text = " ".join(translated_chunks)
        avg_confidence = total_confidence / len(chunks)
        
        return TranslationResult(
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence=avg_confidence,
            processing_time=0.0,  # Will be set later
            quality_score=0.8,
            alternatives=[],
            metadata={"method": "real_time", "chunks": len(chunks)}
        )
    
    async def _translate_batch(self, text: str, request: TranslationRequest, 
                             model_config: Dict[str, Any]) -> TranslationResult:
        """Batch translation for multiple texts"""
        # For batch translation, we can process multiple texts together
        # For now, just use standard translation
        return await self._translate_standard(text, request, model_config)
    
    async def _translate_contextual(self, text: str, request: TranslationRequest, 
                                  model_config: Dict[str, Any]) -> TranslationResult:
        """Context-aware translation"""
        # Use context to improve translation quality
        if request.context:
            # Combine context and text
            combined_text = f"{request.context} {text}"
            
            # Translate with context
            result = await self._translate_standard(combined_text, request, model_config)
            
            # Remove context from result (this is simplified)
            result.translated_text = result.translated_text.replace(
                request.context, ""
            ).strip()
            
            # Higher quality score for contextual translation
            result.quality_score = 0.9
            
            return result
        else:
            # Fall back to standard translation
            return await self._translate_standard(text, request, model_config)
    
    async def _postprocess_text(self, text: str, target_language: str) -> str:
        """Post-process translated text"""
        # Clean up translation
        text = text.strip()
        
        # Language-specific post-processing
        if target_language == "zh":
            # Chinese post-processing
            pass
        elif target_language == "ar":
            # Arabic post-processing
            pass
        
        return text
    
    async def _update_translation_stats(self, request: TranslationRequest, 
                                      processing_time: float, quality_score: float):
        """Update translation statistics"""
        pair = f"{request.source_language}-{request.target_language}"
        
        if pair not in self.stats:
            self.stats[pair] = LanguagePairStats(
                pair=pair,
                total_translations=0,
                average_latency=0.0,
                cache_hit_rate=0.0,
                quality_score=0.0,
                last_updated=datetime.utcnow()
            )
        
        stats = self.stats[pair]
        stats.total_translations += 1
        
        # Update average latency
        stats.average_latency = (
            (stats.average_latency * (stats.total_translations - 1) + processing_time) 
            / stats.total_translations
        )
        
        # Update quality score
        stats.quality_score = (
            (stats.quality_score * (stats.total_translations - 1) + quality_score) 
            / stats.total_translations
        )
        
        stats.last_updated = datetime.utcnow()
    
    async def _load_language_pair_stats(self):
        """Load language pair statistics from database"""
        try:
            async with AsyncSession(async_engine) as session:
                result = await session.execute(select(LanguagePair))
                language_pairs = result.scalars().all()
                
                for pair in language_pairs:
                    self.stats[pair.pair] = LanguagePairStats(
                        pair=pair.pair,
                        total_translations=pair.total_translations,
                        average_latency=pair.average_latency,
                        cache_hit_rate=pair.cache_hit_rate,
                        quality_score=pair.quality_score,
                        last_updated=pair.last_updated
                    )
        except Exception as e:
            logger.warning(f"Failed to load language pair stats: {e}")
    
    async def _cache_cleanup_worker(self):
        """Background worker for cache cleanup"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                if self.redis:
                    # Clean up expired cache entries
                    # This would be handled by Redis TTL, but we can add custom cleanup
                    pass
                
            except Exception as e:
                logger.error(f"Error in cache cleanup worker: {e}")
    
    async def _stats_update_worker(self):
        """Background worker for updating statistics"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Update database with current stats
                await self._update_database_stats()
                
            except Exception as e:
                logger.error(f"Error in stats update worker: {e}")
    
    async def _update_database_stats(self):
        """Update database with current statistics"""
        try:
            async with AsyncSession(async_engine) as session:
                for pair, stats in self.stats.items():
                    await session.execute(
                        update(LanguagePair)
                        .where(LanguagePair.pair == pair)
                        .values(
                            total_translations=stats.total_translations,
                            average_latency=stats.average_latency,
                            cache_hit_rate=stats.cache_hit_rate,
                            quality_score=stats.quality_score,
                            last_updated=stats.last_updated
                        )
                    )
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to update database stats: {e}")
    
    async def get_translation_stats(self) -> Dict[str, Any]:
        """Get translation statistics"""
        total_translations = sum(stats.total_translations for stats in self.stats.values())
        avg_latency = np.mean([stats.average_latency for stats in self.stats.values()])
        avg_quality = np.mean([stats.quality_score for stats in self.stats.values()])
        
        return {
            "total_translations": total_translations,
            "average_latency": avg_latency,
            "average_quality": avg_quality,
            "language_pairs": len(self.stats),
            "cache_size": await self._get_cache_size(),
            "top_pairs": sorted(
                self.stats.items(),
                key=lambda x: x[1].total_translations,
                reverse=True
            )[:10]
        }
    
    async def _get_cache_size(self) -> int:
        """Get current cache size"""
        if not self.redis:
            return 0
        
        try:
            keys = await self.redis.keys("translation:*")
            return len(keys)
        except Exception as e:
            logger.warning(f"Failed to get cache size: {e}")
            return 0
    
    async def clear_cache(self, language_pair: Optional[str] = None):
        """Clear translation cache"""
        if not self.redis:
            return
        
        try:
            if language_pair:
                # Clear cache for specific language pair
                pattern = f"translation:*{language_pair}*"
            else:
                # Clear all translation cache
                pattern = "translation:*"
            
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            
            logger.info(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    async def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.language_codes.keys())
    
    async def get_language_pair_stats(self, pair: str) -> Optional[LanguagePairStats]:
        """Get statistics for specific language pair"""
        return self.stats.get(pair)


# Global ultra-fast translation service instance
ultra_fast_translation_service = UltraFastTranslationService()




