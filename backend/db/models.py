"""Database models"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, DateTime, ForeignKey, Text, JSON, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.db.base import Base
import enum


class VoiceType(str, enum.Enum):
    """Voice profile type"""
    CLONED = "cloned"  # User's cloned voice
    # PRESET removido - apenas clonagem de voz agora


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    
    # Profile
    full_name = Column(String(255))
    avatar_url = Column(String(500))
    bio = Column(Text)
    company = Column(String(255))
    job_title = Column(String(255))
    
    # Authentication
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    email_verification_token = Column(String(500), unique=True, nullable=True)
    
    # OAuth
    google_id = Column(String(255), unique=True, nullable=True)
    github_id = Column(String(255), unique=True, nullable=True)
    
    # Language settings - what user speaks and understands
    speaks_languages = Column(JSON, default=["en"])  # Languages user can speak
    understands_languages = Column(JSON, default=["en"])  # Languages user can understand
    
    # User preferences (JSON)
    preferences = Column(JSON, default={
        "primary_language": "en",
        "output_language": "en",
        "auto_detect_input": True,
        "auto_detect_output": True,
        "theme": "dark",
        "notifications_enabled": True,
        "email_notifications": True
    })
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Relationships
    voice_profiles = relationship("VoiceProfile", back_populates="user", cascade="all, delete-orphan")
    created_rooms = relationship("Room", back_populates="creator", cascade="all, delete-orphan")
    room_participations = relationship("RoomParticipant", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    oauth_providers = relationship("OAuthProvider", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username}>"


class OAuthProvider(Base):
    """OAuth provider linking table"""
    __tablename__ = "oauth_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Provider details
    provider = Column(String(50), nullable=False)  # "google", "github", etc.
    provider_user_id = Column(String(255), nullable=False)  # ID from provider
    
    # Tokens (encrypted or not stored for security)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="oauth_providers")
    
    # Unique constraint: one provider account per user
    __table_args__ = (
        {"schema": None},
    )
    
    def __repr__(self):
        return f"<OAuthProvider {self.provider} for user {self.user_id}>"


class VoiceProfile(Base):
    """Voice profile model - supports both cloned and preset voices"""
    __tablename__ = "voice_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Voice type
    type = Column(Enum(VoiceType), nullable=False, default=VoiceType.CLONED)
    
    # Voice details
    name = Column(String(255), nullable=False)  # e.g., "Minha voz", "Voz Feminina Suave"
    language = Column(String(10), nullable=False)  # e.g., "pt", "en"
    
    # Model path (null for presets, they use global models)
    model_path = Column(String(500), nullable=True)
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)  # 0-100 score
    sample_duration_seconds = Column(Integer, nullable=True)  # For cloned voices
    
    # Status
    is_default = Column(Boolean, default=False)
    is_ready = Column(Boolean, default=False)  # False while training
    training_progress = Column(Float, default=0.0)  # 0-100
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="voice_profiles")
    room_usages = relationship("RoomParticipant", back_populates="voice_profile")
    
    def __repr__(self):
        return f"<VoiceProfile {self.name} ({self.type})>"


class Room(Base):
    """Meeting room model"""
    __tablename__ = "rooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Room details
    name = Column(String(255), nullable=True)  # Optional room name
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Room settings
    max_participants = Column(Integer, default=100)
    pin = Column(String(100), nullable=True)  # Optional PIN protection
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Auto-cleanup after expiry
    
    # Relationships
    creator = relationship("User", back_populates="created_rooms")
    participants = relationship("RoomParticipant", back_populates="room", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Room {self.id} - {self.name or 'Unnamed'}>"


class RoomParticipant(Base):
    """Room participant model - tracks who's in which room with what settings"""
    __tablename__ = "room_participants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Links
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    voice_profile_id = Column(UUID(as_uuid=True), ForeignKey("voice_profiles.id", ondelete="SET NULL"), nullable=True)
    
    # Language settings for this session
    input_language = Column(String(10), default="auto")  # "pt", "en", or "auto"
    output_language = Column(String(10), default="auto")  # "pt", "en", or "auto"
    
    # Session tracking
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)
    
    # Metrics
    total_speak_time_seconds = Column(Integer, default=0)
    total_translated_words = Column(Integer, default=0)
    average_latency_ms = Column(Float, nullable=True)
    
    # Relationships
    room = relationship("Room", back_populates="participants")
    user = relationship("User", back_populates="room_participations")
    voice_profile = relationship("VoiceProfile", back_populates="room_usages")
    
    def __repr__(self):
        return f"<RoomParticipant user={self.user_id} room={self.room_id}>"


class UsageMetric(Base):
    """Usage metrics for monitoring and billing"""
    __tablename__ = "usage_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=True)
    
    # Metric details
    event_type = Column(String(50), nullable=False)  # "translation", "voice_clone", "meeting_minute"
    duration_seconds = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<UsageMetric {self.event_type} user={self.user_id}>"


class Subscription(Base):
    """User subscription model"""
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    tier = Column(String(20), default="free")  # free, pro, enterprise
    status = Column(String(20), default="active")  # active, cancelled, past_due, trialing
    
    # Billing
    stripe_customer_id = Column(String(255), unique=True)
    stripe_subscription_id = Column(String(255), unique=True)
    stripe_price_id = Column(String(255))
    
    # Period
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime)
    
    # Trial
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    
    # Usage tracking
    meetings_count = Column(Integer, default=0)
    total_minutes = Column(Integer, default=0)
    recordings_count = Column(Integer, default=0)
    storage_used_gb = Column(Float, default=0.0)
    api_calls = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")


class UserSession(Base):
    """User session tracking for security and analytics"""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    refresh_token = Column(String(500), unique=True, index=True)
    access_token_jti = Column(String(255), unique=True)  # JWT ID for revocation
    
    device_info = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class PasswordReset(Base):
    """Password reset tokens"""
    __tablename__ = "password_resets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    token = Column(String(500), unique=True, index=True, nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Recording(Base):
    """Meeting recording model"""
    __tablename__ = "recordings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(255))
    file_path = Column(String(500))
    file_size_mb = Column(Float)
    duration_seconds = Column(Integer)
    
    status = Column(String(20), default="processing")  # processing, ready, failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    room = relationship("Room", backref="recordings")


class Transcript(Base):
    """Meeting transcript model"""
    __tablename__ = "transcripts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    
    content = Column(JSON)  # Array of transcript segments
    languages = Column(JSON)  # Languages detected in transcript
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    room = relationship("Room", backref="transcripts")


class APIKey(Base):
    """API Key for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Key details
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # Hashed key
    prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    
    # Permissions
    scopes = Column(JSON, default=["read"])  # Permissions list
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<APIKey {self.name} - {self.prefix}***>"


class AuditLog(Base):
    """Audit log for security and compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Event details
    action = Column(String(100), nullable=False, index=True)  # "user.login", "room.create", etc
    resource_type = Column(String(50), nullable=True)  # "user", "room", "voice_profile"
    resource_id = Column(String(255), nullable=True)
    
    # Request context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    method = Column(String(10))  # HTTP method
    endpoint = Column(String(255))
    
    # Result
    status_code = Column(Integer)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"


class RoomEncryptionKey(Base):
    """End-to-end encryption keys for rooms"""
    __tablename__ = "room_encryption_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Encrypted key (encrypted with master key)
    encrypted_key = Column(Text, nullable=False)
    nonce = Column(String(255), nullable=False)
    
    # Key rotation
    version = Column(Integer, default=1)
    rotated_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    room = relationship("Room", backref="encryption_key")
    
    def __repr__(self):
        return f"<RoomEncryptionKey room={self.room_id} v{self.version}>"


class ChatMessage(Base):
    """Chat message model for in-meeting chat"""
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=True)  # Auto-detected language
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    edited_at = Column(DateTime, nullable=True)
    
    # Relationships
    room = relationship("Room", backref="chat_messages")
    user = relationship("User", backref="chat_messages")
    
    def __repr__(self):
        return f"<ChatMessage room={self.room_id} user={self.user_id}>"
