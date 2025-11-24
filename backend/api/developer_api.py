"""
Developer API Platform
Public API for third-party developers and integrations
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend.db.models import User, APIKey
# from backend.db.models import APIPlan  # TODO: Create this model
# from backend.db.models import APICall  # TODO: Create this model
from backend.db.session import get_db, async_engine
from backend.core.security import verify_api_key
from backend.services.ultra_fast_translation import ultra_fast_translation_service, TranslationRequest, TranslationQuality, TranslationMode
from backend.services.advanced_voice_cloning import advanced_voice_cloning_service, VoiceSynthesisRequest, VoiceQuality, EmotionType
from backend.services.voice_marketplace import voice_marketplace_service, VoiceCategory, VoiceQuality as MarketplaceVoiceQuality
from backend.core.rate_limiter import rate_limit
from backend.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["Developer API"])

# Security
security = HTTPBearer()


class APIResponse(BaseModel):
    """Standard API response format"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TranslationRequestModel(BaseModel):
    """Translation request model"""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to translate")
    source_language: str = Field(..., description="Source language code (e.g., 'en', 'pt')")
    target_language: str = Field(..., description="Target language code (e.g., 'en', 'pt')")
    quality: str = Field(default="balanced", description="Translation quality: fast, balanced, high, ultra")
    mode: str = Field(default="standard", description="Translation mode: real_time, batch, contextual")
    context: Optional[str] = Field(None, description="Context for better translation")
    
    @validator('quality')
    def validate_quality(cls, v):
        if v not in ['fast', 'balanced', 'high', 'ultra']:
            raise ValueError('Quality must be one of: fast, balanced, high, ultra')
        return v
    
    @validator('mode')
    def validate_mode(cls, v):
        if v not in ['real_time', 'batch', 'contextual', 'standard']:
            raise ValueError('Mode must be one of: real_time, batch, contextual, standard')
        return v


class VoiceSynthesisRequestModel(BaseModel):
    """Voice synthesis request model"""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    voice_profile_id: str = Field(..., description="Voice profile ID")
    target_language: str = Field(..., description="Target language code")
    emotion: str = Field(default="neutral", description="Emotion: neutral, happy, sad, angry, excited, calm, confident, worried")
    quality: str = Field(default="balanced", description="Voice quality: fast, balanced, high, ultra")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")
    pitch_shift: float = Field(default=0.0, ge=-1.0, le=1.0, description="Pitch shift in semitones")
    volume: float = Field(default=1.0, ge=0.1, le=2.0, description="Volume multiplier")
    
    @validator('emotion')
    def validate_emotion(cls, v):
        if v not in ['neutral', 'happy', 'sad', 'angry', 'excited', 'calm', 'confident', 'worried']:
            raise ValueError('Emotion must be one of: neutral, happy, sad, angry, excited, calm, confident, worried')
        return v
    
    @validator('quality')
    def validate_quality(cls, v):
        if v not in ['fast', 'balanced', 'high', 'ultra']:
            raise ValueError('Quality must be one of: fast, balanced, high, ultra')
        return v


class VoiceMarketplaceRequestModel(BaseModel):
    """Voice marketplace request model"""
    category: str = Field(..., description="Voice category")
    quality: str = Field(default="premium", description="Voice quality")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    languages: Optional[List[str]] = Field(None, description="Supported languages filter")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    
    @validator('category')
    def validate_category(cls, v):
        if v not in ['professional', 'celebrity', 'character', 'accent', 'language', 'emotion', 'age', 'gender']:
            raise ValueError('Category must be one of: professional, celebrity, character, accent, language, emotion, age, gender')
        return v
    
    @validator('quality')
    def validate_quality(cls, v):
        if v not in ['standard', 'premium', 'ultra', 'professional']:
            raise ValueError('Quality must be one of: standard, premium, ultra, professional')
        return v


class APIPlanModel(BaseModel):
    """API plan model"""
    name: str
    description: str
    monthly_calls: int
    price_per_month: float
    features: List[str]


class APIKeyModel(BaseModel):
    """API key model"""
    key: str
    name: str
    plan: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from API key"""
    api_key = credentials.credentials
    
    # Verify API key
    user = await verify_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user


async def track_api_call(user: User, endpoint: str, request_data: Dict[str, Any], 
                        response_data: Dict[str, Any], processing_time: float):
    """Track API call for billing and analytics"""
    try:
        async with AsyncSession(async_engine) as session:
            # Get user's API key
            result = await session.execute(
                select(APIKey).where(APIKey.user_id == user.id, APIKey.is_active == True)
            )
            api_key = result.scalar_one_or_none()
            
            if api_key:
                # Create API call record
                api_call = APICall(
                    api_key_id=api_key.id,
                    user_id=user.id,
                    endpoint=endpoint,
                    request_data=json.dumps(request_data),
                    response_data=json.dumps(response_data),
                    processing_time=processing_time,
                    timestamp=datetime.utcnow()
                )
                
                session.add(api_call)
                await session.commit()
                
                # Update API key usage
                api_key.calls_this_month += 1
                await session.commit()
                
    except Exception as e:
        logger.error(f"Failed to track API call: {e}")


@router.get("/", response_model=APIResponse)
async def api_info():
    """Get API information and status"""
    return APIResponse(
        success=True,
        data={
            "name": "Orbis Developer API",
            "version": "1.0.0",
            "description": "Real-time multilingual communication API",
            "features": [
                "Real-time translation",
                "Voice synthesis with cloning",
                "Voice marketplace",
                "WebRTC integration",
                "Enterprise features"
            ],
            "documentation": "/docs",
            "status": "operational"
        }
    )


@router.get("/languages", response_model=APIResponse)
async def get_supported_languages():
    """Get list of supported languages"""
    try:
        languages = await ultra_fast_translation_service.get_supported_languages()
        
        return APIResponse(
            success=True,
            data={
                "languages": languages,
                "total": len(languages)
            }
        )
    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported languages")


@router.post("/translate", response_model=APIResponse)
@rate_limit(requests=100, window=60)  # 100 calls per minute
async def translate_text(
    request: TranslationRequestModel,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Translate text with ultra-fast processing"""
    start_time = datetime.utcnow()
    
    try:
        # Convert request to service format
        translation_request = TranslationRequest(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            quality=TranslationQuality(request.quality),
            mode=TranslationMode(request.mode),
            context=request.context,
            user_id=current_user.id
        )
        
        # Translate
        result = await ultra_fast_translation_service.translate(translation_request)
        
        # Prepare response
        response_data = {
            "translated_text": result.translated_text,
            "source_language": result.source_language,
            "target_language": result.target_language,
            "confidence": result.confidence,
            "processing_time": result.processing_time,
            "quality_score": result.quality_score,
            "alternatives": result.alternatives
        }
        
        # Track API call
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        background_tasks.add_task(
            track_api_call,
            current_user,
            "/translate",
            request.dict(),
            response_data,
            processing_time
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            metadata={
                "processing_time": processing_time,
                "quality": request.quality,
                "mode": request.mode
            }
        )
        
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/voice/synthesize", response_model=APIResponse)
@rate_limit(requests=50, window=60)  # 50 calls per minute
async def synthesize_voice(
    request: VoiceSynthesisRequestModel,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Synthesize voice with advanced cloning"""
    start_time = datetime.utcnow()
    
    try:
        # Convert request to service format
        synthesis_request = VoiceSynthesisRequest(
            text=request.text,
            voice_profile_id=request.voice_profile_id,
            target_language=request.target_language,
            emotion=EmotionType(request.emotion),
            quality=VoiceQuality(request.quality),
            speed=request.speed,
            pitch_shift=request.pitch_shift,
            volume=request.volume
        )
        
        # Synthesize voice
        result = await advanced_voice_cloning_service.synthesize_voice(synthesis_request)
        
        # Prepare response
        response_data = {
            "audio_data": result.audio_data.tolist(),  # Convert numpy array to list
            "sample_rate": result.sample_rate,
            "duration": result.duration,
            "quality_score": result.quality_score,
            "processing_time": result.processing_time,
            "metadata": result.metadata
        }
        
        # Track API call
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        background_tasks.add_task(
            track_api_call,
            current_user,
            "/voice/synthesize",
            request.dict(),
            response_data,
            processing_time
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            metadata={
                "processing_time": processing_time,
                "quality": request.quality,
                "emotion": request.emotion
            }
        )
        
    except Exception as e:
        logger.error(f"Voice synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {str(e)}")


@router.get("/voice/marketplace", response_model=APIResponse)
@rate_limit(requests=200, window=60)  # 200 calls per minute
async def get_voice_marketplace(
    request: VoiceMarketplaceRequestModel = Depends(),
    current_user: User = Depends(get_current_user)
):
    """Get voice marketplace listings"""
    try:
        # Convert request to service format
        filters = {
            "category": request.category,
            "quality": request.quality,
            "min_price": request.min_price,
            "max_price": request.max_price,
            "languages": request.languages
        }
        
        # Get listings
        listings = await voice_marketplace_service.get_voice_listings(
            filters=filters,
            limit=request.limit,
            offset=request.offset
        )
        
        # Convert listings to response format
        response_data = []
        for listing in listings:
            response_data.append({
                "id": listing.id,
                "title": listing.title,
                "description": listing.description,
                "category": listing.category.value,
                "quality": listing.quality.value,
                "price_usd": listing.price_usd,
                "currency": listing.currency,
                "sample_audio_url": listing.sample_audio_url,
                "demo_text": listing.demo_text,
                "languages": listing.languages,
                "accents": listing.accents,
                "emotions": listing.emotions,
                "age_range": listing.age_range,
                "gender": listing.gender,
                "tags": listing.tags,
                "rating": listing.rating,
                "review_count": listing.review_count,
                "download_count": listing.download_count,
                "featured": listing.featured,
                "trending": listing.trending
            })
        
        return APIResponse(
            success=True,
            data={
                "listings": response_data,
                "total": len(response_data),
                "limit": request.limit,
                "offset": request.offset
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get voice marketplace: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get voice marketplace: {str(e)}")


@router.get("/voice/marketplace/featured", response_model=APIResponse)
@rate_limit(requests=100, window=60)  # 100 calls per minute
async def get_featured_voices(current_user: User = Depends(get_current_user)):
    """Get featured voice listings"""
    try:
        listings = await voice_marketplace_service.get_featured_voices()
        
        # Convert to response format
        response_data = []
        for listing in listings:
            response_data.append({
                "id": listing.id,
                "title": listing.title,
                "description": listing.description,
                "category": listing.category.value,
                "quality": listing.quality.value,
                "price_usd": listing.price_usd,
                "sample_audio_url": listing.sample_audio_url,
                "rating": listing.rating,
                "download_count": listing.download_count
            })
        
        return APIResponse(
            success=True,
            data={
                "featured_voices": response_data,
                "total": len(response_data)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get featured voices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get featured voices: {str(e)}")


@router.get("/voice/marketplace/trending", response_model=APIResponse)
@rate_limit(requests=100, window=60)  # 100 calls per minute
async def get_trending_voices(current_user: User = Depends(get_current_user)):
    """Get trending voice listings"""
    try:
        listings = await voice_marketplace_service.get_trending_voices()
        
        # Convert to response format
        response_data = []
        for listing in listings:
            response_data.append({
                "id": listing.id,
                "title": listing.title,
                "description": listing.description,
                "category": listing.category.value,
                "quality": listing.quality.value,
                "price_usd": listing.price_usd,
                "sample_audio_url": listing.sample_audio_url,
                "rating": listing.rating,
                "download_count": listing.download_count
            })
        
        return APIResponse(
            success=True,
            data={
                "trending_voices": response_data,
                "total": len(response_data)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get trending voices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trending voices: {str(e)}")


@router.get("/voice/marketplace/stats", response_model=APIResponse)
@rate_limit(requests=50, window=60)  # 50 calls per minute
async def get_marketplace_stats(current_user: User = Depends(get_current_user)):
    """Get marketplace statistics"""
    try:
        stats = await voice_marketplace_service.get_marketplace_stats()
        
        return APIResponse(
            success=True,
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get marketplace stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get marketplace stats: {str(e)}")


@router.get("/translation/stats", response_model=APIResponse)
@rate_limit(requests=50, window=60)  # 50 calls per minute
async def get_translation_stats(current_user: User = Depends(get_current_user)):
    """Get translation statistics"""
    try:
        stats = await ultra_fast_translation_service.get_translation_stats()
        
        return APIResponse(
            success=True,
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get translation stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get translation stats: {str(e)}")


@router.get("/plans", response_model=APIResponse)
async def get_api_plans():
    """Get available API plans"""
    try:
        # This would come from database
        plans = [
            {
                "name": "Starter",
                "description": "Perfect for developers and small projects",
                "monthly_calls": 1000,
                "price_per_month": 9.99,
                "features": [
                    "Basic translation",
                    "Standard voice synthesis",
                    "API access",
                    "Email support"
                ]
            },
            {
                "name": "Professional",
                "description": "For growing applications and businesses",
                "monthly_calls": 10000,
                "price_per_month": 49.99,
                "features": [
                    "Advanced translation",
                    "Premium voice synthesis",
                    "Voice marketplace access",
                    "Priority support",
                    "Analytics dashboard"
                ]
            },
            {
                "name": "Enterprise",
                "description": "For large-scale applications and enterprises",
                "monthly_calls": 100000,
                "price_per_month": 199.99,
                "features": [
                    "Ultra-fast translation",
                    "Custom voice cloning",
                    "White-label options",
                    "Dedicated support",
                    "Custom integrations",
                    "SLA guarantee"
                ]
            }
        ]
        
        return APIResponse(
            success=True,
            data={
                "plans": plans,
                "total": len(plans)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get API plans: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get API plans: {str(e)}")


@router.get("/usage", response_model=APIResponse)
async def get_api_usage(current_user: User = Depends(get_current_user)):
    """Get API usage statistics for current user"""
    try:
        async with AsyncSession(async_engine) as session:
            # Get user's API key
            result = await session.execute(
                select(APIKey).where(APIKey.user_id == current_user.id, APIKey.is_active == True)
            )
            api_key = result.scalar_one_or_none()
            
            if not api_key:
                raise HTTPException(status_code=404, detail="No active API key found")
            
            # Get API plan
            plan_result = await session.execute(
                select(APIPlan).where(APIPlan.name == api_key.plan)
            )
            plan = plan_result.scalar_one_or_none()
            
            # Get usage statistics
            usage_data = {
                "api_key": {
                    "name": api_key.name,
                    "plan": api_key.plan,
                    "created_at": api_key.created_at,
                    "expires_at": api_key.expires_at,
                    "is_active": api_key.is_active
                },
                "plan": {
                    "name": plan.name if plan else api_key.plan,
                    "monthly_calls": plan.monthly_calls if plan else 0,
                    "price_per_month": plan.price_per_month if plan else 0
                },
                "usage": {
                    "calls_this_month": api_key.calls_this_month,
                    "calls_remaining": max(0, (plan.monthly_calls if plan else 0) - api_key.calls_this_month),
                    "usage_percentage": (api_key.calls_this_month / (plan.monthly_calls if plan else 1)) * 100
                }
            }
            
            return APIResponse(
                success=True,
                data=usage_data
            )
        
    except Exception as e:
        logger.error(f"Failed to get API usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get API usage: {str(e)}")


@router.post("/keys", response_model=APIResponse)
async def create_api_key(
    name: str,
    plan: str,
    current_user: User = Depends(get_current_user)
):
    """Create a new API key"""
    try:
        async with AsyncSession(async_engine) as session:
            # Check if user already has an active API key
            result = await session.execute(
                select(APIKey).where(APIKey.user_id == current_user.id, APIKey.is_active == True)
            )
            existing_key = result.scalar_one_or_none()
            
            if existing_key:
                raise HTTPException(status_code=400, detail="User already has an active API key")
            
            # Generate new API key
            import secrets
            api_key_value = f"orbis_{secrets.token_urlsafe(32)}"
            
            # Create API key
            api_key = APIKey(
                user_id=current_user.id,
                key=api_key_value,
                name=name,
                plan=plan,
                is_active=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year
            )
            
            session.add(api_key)
            await session.commit()
            
            return APIResponse(
                success=True,
                data={
                    "api_key": api_key_value,
                    "name": name,
                    "plan": plan,
                    "created_at": api_key.created_at,
                    "expires_at": api_key.expires_at
                }
            )
        
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create API key: {str(e)}")


@router.delete("/keys/{key_id}", response_model=APIResponse)
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user)
):
    """Revoke an API key"""
    try:
        async with AsyncSession(async_engine) as session:
            # Get API key
            result = await session.execute(
                select(APIKey).where(
                    APIKey.id == key_id,
                    APIKey.user_id == current_user.id
                )
            )
            api_key = result.scalar_one_or_none()
            
            if not api_key:
                raise HTTPException(status_code=404, detail="API key not found")
            
            # Revoke API key
            api_key.is_active = False
            await session.commit()
            
            return APIResponse(
                success=True,
                data={
                    "message": "API key revoked successfully",
                    "key_id": key_id
                }
            )
        
    except Exception as e:
        logger.error(f"Failed to revoke API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to revoke API key: {str(e)}")


@router.get("/health", response_model=APIResponse)
async def api_health_check():
    """API health check endpoint"""
    try:
        # Check service health
        translation_healthy = True  # Would check actual service
        voice_healthy = True  # Would check actual service
        marketplace_healthy = True  # Would check actual service
        
        overall_healthy = translation_healthy and voice_healthy and marketplace_healthy
        
        return APIResponse(
            success=overall_healthy,
            data={
                "status": "healthy" if overall_healthy else "degraded",
                "services": {
                    "translation": "healthy" if translation_healthy else "unhealthy",
                    "voice_synthesis": "healthy" if voice_healthy else "unhealthy",
                    "marketplace": "healthy" if marketplace_healthy else "unhealthy"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return APIResponse(
            success=False,
            error="Health check failed",
            data={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat()
            }
        )




