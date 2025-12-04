"""
User Profile endpoints
Complete profile management, stats, settings
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import logging

from backend.db.session import get_db
from backend.db.models import User, Subscription, Room, VoiceProfile
from backend.models.user import (
    UserResponse, 
    UpdateProfileRequest, 
    UpdatePreferencesRequest,
    UpdateLanguagesRequest,
    UserStats
)
from backend.core.languages import validate_language_code, get_languages_for_api
from backend.models.subscription import SubscriptionResponse, UsageStats
from backend.api.deps import get_current_user
from backend.services.audio_pipeline.stream_processor import audio_stream_processor
from backend.services.audio_pipeline.websocket_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        company=current_user.company,
        job_title=current_user.job_title,
        is_verified=current_user.is_verified,
        speaks_languages=current_user.speaks_languages or ["en"],
        understands_languages=current_user.understands_languages or ["en"],
        preferences=current_user.preferences,
        created_at=current_user.created_at
    )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.bio is not None:
        current_user.bio = request.bio
    if request.company is not None:
        current_user.company = request.company
    if request.job_title is not None:
        current_user.job_title = request.job_title
    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        company=current_user.company,
        job_title=current_user.job_title,
        is_verified=current_user.is_verified,
        speaks_languages=current_user.speaks_languages or ["en"],
        understands_languages=current_user.understands_languages or ["en"],
        preferences=current_user.preferences,
        created_at=current_user.created_at
    )


@router.put("/preferences", response_model=UserResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    preferences = current_user.preferences or {}
    
    if request.primary_language is not None:
        preferences["primary_language"] = request.primary_language
    if request.output_language is not None:
        preferences["output_language"] = request.output_language
    if request.auto_detect_input is not None:
        preferences["auto_detect_input"] = request.auto_detect_input
    if request.auto_detect_output is not None:
        preferences["auto_detect_output"] = request.auto_detect_output
    if request.theme is not None:
        preferences["theme"] = request.theme
    if request.notifications_enabled is not None:
        preferences["notifications_enabled"] = request.notifications_enabled
    if request.email_notifications is not None:
        preferences["email_notifications"] = request.email_notifications
    
    current_user.preferences = preferences
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        company=current_user.company,
        job_title=current_user.job_title,
        is_verified=current_user.is_verified,
        speaks_languages=current_user.speaks_languages or ["en"],
        understands_languages=current_user.understands_languages or ["en"],
        preferences=current_user.preferences,
        created_at=current_user.created_at
    )


@router.put("/languages", response_model=UserResponse)
async def update_languages(
    request: UpdateLanguagesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user languages (what they speak and understand)"""
    
    # Validate language codes
    if request.speaks_languages:
        for lang in request.speaks_languages:
            if not validate_language_code(lang):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid language code: {lang}"
                )
        current_user.speaks_languages = request.speaks_languages
    
    if request.understands_languages:
        for lang in request.understands_languages:
            if not validate_language_code(lang):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid language code: {lang}"
                )
        current_user.understands_languages = request.understands_languages
    
    db.commit()
    db.refresh(current_user)

    # Determine active languages for runtime services
    speaks = current_user.speaks_languages[0] if current_user.speaks_languages else "auto"
    understands = current_user.understands_languages[0] if current_user.understands_languages else "en"

    # Propagate to active audio sessions so translations switch immediately
    audio_stream_processor.update_user_language(current_user.id, speaks, understands)

    if current_user.id in connection_manager.active_connections:
        await connection_manager.send_personal_message(current_user.id, {
            "type": "language_updated",
            "input_language": speaks,
            "output_language": understands,
            "message": "Language preferences updated"
        })

    # Log with clear explanation
    logger.info(
        f"🌐 User {current_user.id} language settings updated: "
        f"speaks={speaks}, wants_to_hear={understands}"
    )
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        company=current_user.company,
        job_title=current_user.job_title,
        is_verified=current_user.is_verified,
        speaks_languages=current_user.speaks_languages or ["en"],
        understands_languages=current_user.understands_languages or ["en"],
        preferences=current_user.preferences,
        created_at=current_user.created_at
    )


@router.get("/languages/supported")
async def get_supported_languages():
    """Get list of all supported languages - PUBLIC endpoint"""
    try:
        languages = get_languages_for_api()
        return {
            "languages": languages,
            "total": len(languages)
        }
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        # Retornar lista básica como fallback
        return {
            "languages": [
                {"code": "en", "name": "English", "native_name": "English", "flag": "🇬🇧"},
                {"code": "pt", "name": "Portuguese", "native_name": "Português", "flag": "🇧🇷"},
                {"code": "es", "name": "Spanish", "native_name": "Español", "flag": "🇪🇸"},
                {"code": "fr", "name": "French", "native_name": "Français", "flag": "🇫🇷"},
                {"code": "de", "name": "German", "native_name": "Deutsch", "flag": "🇩🇪"},
            ],
            "total": 5
        }


@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user statistics"""
    # Count meetings
    total_meetings = db.query(Room).filter(
        Room.creator_id == current_user.id
    ).count()
    
    # Count voice profiles
    voice_profiles_count = db.query(VoiceProfile).filter(
        VoiceProfile.user_id == current_user.id
    ).count()
    
    # Get subscription for usage stats
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    total_minutes = subscription.total_minutes if subscription else 0
    
    return UserStats(
        total_meetings=total_meetings,
        total_minutes=total_minutes,
        languages_used=5,  # Mock - would track this in production
        voice_profiles=voice_profiles_count,
        recordings=0  # Mock
    )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user subscription details"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    from backend.models.subscription import TIER_FEATURES
    from backend.models.subscription import SubscriptionTier
    
    tier = SubscriptionTier(subscription.tier)
    features = TIER_FEATURES[tier]
    
    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        tier=tier,
        status=subscription.status,
        features=features,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        stripe_customer_id=subscription.stripe_customer_id,
        stripe_subscription_id=subscription.stripe_subscription_id
    )


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current period usage statistics"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        return UsageStats(
            meetings_count=0,
            total_minutes=0,
            recordings_count=0,
            storage_used_gb=0.0,
            api_calls=0
        )
    
    return UsageStats(
        meetings_count=subscription.meetings_count,
        total_minutes=subscription.total_minutes,
        recordings_count=subscription.recordings_count,
        storage_used_gb=subscription.storage_used_gb,
        api_calls=subscription.api_calls
    )


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload user avatar
    
    Accepts: image/jpeg, image/png, image/webp
    Max size: 5MB
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file size (5MB max)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to start
    
    if file_size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Max size: 5MB"
        )
    
    # TODO: Upload to S3 or local storage
    # For now, return mock URL
    avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={current_user.username}"
    
    current_user.avatar_url = avatar_url
    db.commit()
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url
    }


@router.delete("/me")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account
    
    WARNING: This action is irreversible!
    """
    # TODO: Add confirmation requirement
    # TODO: Cancel subscriptions
    # TODO: Delete all user data (GDPR compliance)
    
    db.delete(current_user)
    db.commit()
    
    return {"message": "Account deleted successfully"}