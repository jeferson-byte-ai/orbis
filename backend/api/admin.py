"""Admin endpoints for user management"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.db.session import get_db
from backend.db.models import User
from backend.api.deps import get_current_active_user
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class UserListResponse(BaseModel):
    """User list response"""
    id: UUID
    email: str
    username: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None
    
    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """Detailed user response"""
    id: UUID
    email: str
    username: str
    full_name: str | None
    company: str | None
    job_title: str | None
    bio: str | None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    google_id: str | None
    github_id: str | None
    speaks_languages: List[str]
    understands_languages: List[str]
    created_at: datetime
    updated_at: datetime | None
    last_login_at: datetime | None
    
    # Counts
    voice_profiles_count: int = 0
    rooms_count: int = 0
    participations_count: int = 0
    
    class Config:
        from_attributes = True


@router.get("/users", response_model=List[UserListResponse])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only)
    
    **Note:** In a production environment, you should add proper admin authorization here.
    For now, any authenticated user can access this endpoint.
    """
    # TODO: Add admin check
    # if not current_user.is_superuser:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not enough permissions"
    #     )
    
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific user (admin only)
    """
    # TODO: Add admin check
    # if not current_user.is_superuser:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not enough permissions"
    #     )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Add counts
    response = UserDetailResponse.from_orm(user)
    response.voice_profiles_count = len(user.voice_profiles)
    response.rooms_count = len(user.created_rooms)
    response.participations_count = len(user.room_participations)
    
    return response


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user (admin only)
    
    **WARNING:** This action is irreversible and will cascade delete all related data.
    """
    # TODO: Add admin check
    # if not current_user.is_superuser:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not enough permissions"
    #     )
    
    # Prevent self-deletion
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account via admin endpoint"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        db.delete(user)
        db.commit()
        
        return {
            "message": f"User {user.email} deleted successfully",
            "deleted_user_id": str(user_id)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Toggle user active status (admin only)
    """
    # TODO: Add admin check
    # if not current_user.is_superuser:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not enough permissions"
    #     )
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"User {user.email} is now {'active' if user.is_active else 'inactive'}",
        "user_id": str(user_id),
        "is_active": user.is_active
    }


@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get system statistics (admin only)
    """
    # TODO: Add admin check
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    oauth_users = db.query(User).filter(
        (User.google_id.isnot(None)) | (User.github_id.isnot(None))
    ).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "oauth_users": oauth_users,
        "inactive_users": total_users - active_users,
        "unverified_users": total_users - verified_users
    }
