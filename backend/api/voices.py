import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from pathlib import Path
from sqlalchemy.orm import Session

from backend.api.deps import get_current_active_user, get_db
from backend.db.models import User, VoiceProfile, VoiceType
from backend.config import settings
from backend.services.voice_training_service import train_voice_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voices", tags=["Voices"])


class PresetVoiceRequest(BaseModel):
    voice_type: str  # "male" or "female"

@router.post("/upload-profile-voice", status_code=status.HTTP_201_CREATED)
async def upload_profile_voice(
    file: Annotated[UploadFile, File(description="Audio file for voice cloning profile")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Uploads an audio file to create or update a user's voice cloning profile.
    The file will be stored in the `data/voices` directory with the user's ID as the filename.
    """
    if not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only audio files are allowed."
        )

    user_id = current_user.id
    voice_profile_path = Path(settings.voices_path) / f"{user_id}.wav"

    try:
        # Ensure the directory exists
        voice_profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the uploaded file
        contents = await file.read()
        with open(voice_profile_path, "wb") as f:
            f.write(contents)
        
        # Upsert voice profile metadata so we can track training progress
        voice_profile = (
            db.query(VoiceProfile)
            .filter(VoiceProfile.user_id == user_id, VoiceProfile.type == VoiceType.CLONED)
            .order_by(VoiceProfile.created_at.desc())
            .first()
        )

        primary_language = (current_user.speaks_languages or ["en"])[0]
        voice_name = current_user.full_name or current_user.username or "Minha Voz"

        if voice_profile is None:
            voice_profile = VoiceProfile(
                user_id=user_id,
                type=VoiceType.CLONED,
                name=f"{voice_name} (Cloned)",
                language=primary_language,
                is_default=True
            )
            db.add(voice_profile)
        else:
            voice_profile.language = primary_language

        voice_profile.is_ready = False
        voice_profile.training_progress = 0.0
        voice_profile.model_path = None

        db.commit()
        db.refresh(voice_profile)

        # Launch training asynchronously so the request returns quickly
        asyncio.create_task(train_voice_profile(voice_profile.id, str(voice_profile_path)))

        logger.info(f"Voice profile for user {user_id} uploaded successfully to {voice_profile_path}")
        return {
            "message": "Voice profile uploaded successfully",
            "file_path": str(voice_profile_path),
            "voice_profile_id": str(voice_profile.id)
        }
    except Exception as e:
        logger.error(f"Error uploading voice profile for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload voice profile."
        )

@router.get("/profile-voice-status", status_code=status.HTTP_200_OK)
async def get_profile_voice_status(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Checks if a voice profile exists for the current user.
    """
    user_id = current_user.id
    voice_profile_path = Path(settings.voices_path) / f"{user_id}.wav"

    if voice_profile_path.exists():
        return {"exists": True, "message": "Voice profile exists."}
    else:
        return {"exists": False, "message": "No voice profile found."}


@router.get("/profile")
async def get_voice_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Get current user's voice profile information
    """
    user_id = current_user.id
    voice_profile_path = Path(settings.voices_path) / f"{user_id}.wav"
    
    if not voice_profile_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found"
        )
    
    import os
    from datetime import datetime
    
    file_stats = os.stat(voice_profile_path)
    
    return {
        "exists": True,
        "file_path": f"/api/voices/profile/audio",
        "file_size": file_stats.st_size,
        "created_at": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
    }


@router.get("/profile/audio")
async def get_voice_profile_audio(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Stream the voice profile audio file
    """
    from fastapi.responses import FileResponse
    
    user_id = current_user.id
    voice_profile_path = Path(settings.voices_path) / f"{user_id}.wav"
    
    if not voice_profile_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile audio not found"
        )
    
    return FileResponse(
        path=str(voice_profile_path),
        media_type="audio/wav",
        filename=f"voice_profile_{user_id}.wav"
    )


@router.delete("/profile")
async def delete_voice_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Delete the current user's voice profile
    """
    user_id = current_user.id
    voice_profile_path = Path(settings.voices_path) / f"{user_id}.wav"
    
    if not voice_profile_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice profile not found"
        )
    
    try:
        voice_profile_path.unlink()
        logger.info(f"Voice profile for user {user_id} deleted successfully")
        return {"message": "Voice profile deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting voice profile for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete voice profile"
        )


# ENDPOINT REMOVIDO: select-preset
# Orbis agora usa apenas clonagem de voz (voice cloning)
# Para criar perfil de voz, use POST /api/voices/upload-profile-voice
