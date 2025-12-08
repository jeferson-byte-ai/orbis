import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from pathlib import Path
from sqlalchemy.orm import Session
import json

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


@router.post("/preload")
async def preload_voice_for_meeting(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Preload user's cloned voice into memory for real-time translation.
    This should be called before joining a meeting to ensure fast voice synthesis.
    
    Steps:
    1. Check if user has a voice profile (WAV file)
    2. Create/verify Coqui voice profile (JSON metadata)
    3. Load TTS model with the voice
    4. Return ready status
    """
    user_id = current_user.id
    voice_wav_path = Path(settings.voices_path) / f"{user_id}.wav"
    voice_json_path = Path(settings.voices_path) / f"{user_id}.json"
    
    try:
        logger.info(f"🎤 Preloading voice for user {user_id}")
        logger.info(f"📁 Voice WAV: {voice_wav_path}")
        logger.info(f"📁 Voice JSON: {voice_json_path}")
        
        # Get or create voice profile from database
        voice_profile = (
            db.query(VoiceProfile)
            .filter(VoiceProfile.user_id == user_id, VoiceProfile.type == VoiceType.CLONED)
            .order_by(VoiceProfile.created_at.desc())
            .first()
        )
        
        if not voice_profile:
            # Create voice profile entry
            primary_language = (current_user.speaks_languages or ["en"])[0]
            voice_name = current_user.full_name or current_user.username or "My Voice"
            
            voice_profile = VoiceProfile(
                user_id=user_id,
                type=VoiceType.CLONED,
                name=f"{voice_name} (Cloned)",
                language=primary_language,
                is_default=True,
                is_ready=False,  # Will be set to True after cloning
                model_path=str(voice_json_path)  # JSON metadata file
            )
            db.add(voice_profile)
            db.commit()
            db.refresh(voice_profile)
            logger.info(f"✅ Created voice profile in database")
        
        # Load TTS service
        from ml.tts.coqui_service import coqui_service
        
        # Initialize TTS if not already loaded
        if coqui_service.tts is None:
            logger.info("🔄 Loading Coqui TTS model...")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, coqui_service.load)
            logger.info("✅ Coqui TTS model loaded")
        
        # Resolve best speaker WAV (prefer fresh upload; fallback to existing profile metadata)
        speaker_wav_path: Path | None = None
        if voice_wav_path.exists():
            speaker_wav_path = voice_wav_path
        else:
            # Try existing profile metadata
            metadata_path = Path(voice_profile.model_path) if voice_profile.model_path else None
            if metadata_path and metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text())
                    candidate_wav = metadata.get("speaker_wav")
                    if candidate_wav and Path(candidate_wav).exists():
                        speaker_wav_path = Path(candidate_wav)
                        logger.warning(
                            "⚠️ Using speaker WAV from existing profile metadata because user WAV was missing: %s",
                            speaker_wav_path,
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("⚠️ Could not read profile metadata for fallback WAV: %s", exc)

        if not speaker_wav_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voice profile not found. Please upload a voice sample first."
            )

        # Choose target JSON (reuse existing ready profile if possible)
        target_json_path = voice_json_path
        if voice_profile.model_path and Path(voice_profile.model_path).exists():
            target_json_path = Path(voice_profile.model_path)

        need_clone = (not target_json_path.exists()) or (not voice_profile.is_ready)
        if need_clone:
            logger.info("🎨 Creating/refreshing Coqui voice profile at %s", target_json_path)
            success = await coqui_service.clone_voice(
                audio_samples=[str(speaker_wav_path)],
                output_path=str(target_json_path)
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to clone voice. Please try uploading again."
                )

            voice_profile.is_ready = True
            voice_profile.model_path = str(target_json_path)
            db.commit()
            logger.info(f"✅ Voice cloned successfully: {target_json_path}")
        else:
            logger.info(f"✅ Voice profile already ready: {target_json_path}")
        
        # Verify voice file can be read (if present)
        if voice_wav_path.exists():
            voice_file_size = voice_wav_path.stat().st_size
            logger.info(f"📊 Voice WAV file: {voice_file_size} bytes")
        else:
            logger.warning("⚠️ Voice WAV file missing after preload attempt: %s", voice_wav_path)
        
        # Verify JSON metadata
        if target_json_path.exists():
            metadata = json.loads(target_json_path.read_text())
            logger.info(f"📊 Voice profile metadata: {metadata.get('notes', 'N/A')}")
            speaker_wav = metadata.get('speaker_wav')
            if speaker_wav and Path(speaker_wav).exists():
                logger.info(f"✅ Speaker WAV verified: {speaker_wav}")
            else:
                logger.warning(f"⚠️ Speaker WAV not found: {speaker_wav}")
        
        # Store voice profile ID in Redis for fast lookup during meeting
        try:
            from backend.core.redis import redis_client
            if redis_client:
                await redis_client.setex(
                    f"voice_preload:{user_id}",
                    3600,  # 1 hour TTL
                    str(voice_profile.id)
                )
                logger.info(f"✅ Voice preloaded and cached for user {user_id}")
        except Exception as redis_error:
            logger.warning(f"⚠️ Redis cache warning: {redis_error}")
        
        return {
            "success": True,
            "message": "Voice preloaded successfully",
            "voice_profile_id": str(voice_profile.id),
            "voice_name": voice_profile.name,
            "language": voice_profile.language,
            "ready": voice_profile.is_ready,
            "file_size": voice_file_size,
            "tts_loaded": coqui_service.tts is not None,
            "voice_wav": str(voice_wav_path),
            "voice_json": str(voice_json_path),
            "json_exists": voice_json_path.exists()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error preloading voice for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preload voice: {str(e)}"
        )


# ENDPOINT REMOVIDO: select-preset
# Orbis agora usa apenas clonagem de voz (voice cloning)
# Para criar perfil de voz, use POST /api/voices/upload-profile-voice
