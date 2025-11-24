"""
Security-Enhanced Database Models
BigTech-level security features
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.db.base import Base


class TwoFactorAuth(Base):
    """Two-Factor Authentication model"""
    __tablename__ = "two_factor_auth"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # TOTP secret (encrypted)
    totp_secret_encrypted = Column(String(500), nullable=False)
    totp_secret_nonce = Column(String(24), nullable=False)
    
    # Backup codes (hashed)
    backup_codes = Column(Text)  # JSON array of hashed codes
    
    # Status
    is_enabled = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Metadata
    method = Column(String(20), default="totp")  # totp, sms, email
    phone_number_encrypted = Column(String(500), nullable=True)
    phone_number_nonce = Column(String(24), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    last_used_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", backref="two_factor_auth")


class APIKeySecure(Base):
    """Secure API Key storage (hashed keys)"""
    __tablename__ = "api_keys_secure"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Key hash (SHA-256) - actual key never stored!
    key_hash = Column(String(64), unique=True, index=True, nullable=False)
    key_prefix = Column(String(10))  # First 8 chars for identification (e.g., "sk_live_")
    
    name = Column(String(255))
    description = Column(Text)
    
    # Permissions
    scopes = Column(Text)  # JSON array of allowed scopes
    rate_limit_override = Column(Integer)  # Custom rate limit
    
    # Security
    allowed_ips = Column(Text)  # JSON array of whitelisted IPs
    allowed_domains = Column(Text)  # JSON array of whitelisted domains
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    
    # Usage tracking
    last_used_at = Column(DateTime)
    total_requests = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", backref="api_keys_secure")


class OAuthTokenSecure(Base):
    """Secure OAuth token storage (encrypted)"""
    __tablename__ = "oauth_tokens_secure"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    provider = Column(String(50), nullable=False)  # google, github, etc
    
    # Tokens (encrypted with AES-256-GCM)
    access_token_encrypted = Column(Text, nullable=False)
    access_token_nonce = Column(String(24), nullable=False)
    
    refresh_token_encrypted = Column(Text)
    refresh_token_nonce = Column(String(24))
    
    # Token metadata (not encrypted)
    expires_at = Column(DateTime)
    scopes = Column(Text)  # JSON array of granted scopes
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="oauth_tokens_secure")


class EncryptionKeyRotation(Base):
    """Track encryption key rotations for compliance"""
    __tablename__ = "encryption_key_rotations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    key_type = Column(String(50), nullable=False)  # master, room, user
    key_version = Column(Integer, nullable=False)
    
    # Old key info (for decrypting old data)
    old_key_hash = Column(String(64))
    
    # New key info
    new_key_hash = Column(String(64))
    
    # Rotation status
    status = Column(String(20), default="pending")  # pending, in_progress, completed, failed
    records_to_rotate = Column(Integer, default=0)
    records_rotated = Column(Integer, default=0)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Metadata
    triggered_by = Column(String(50))  # auto, manual, policy
    notes = Column(Text)


class SecurityEvent(Base):
    """Security events and alerts"""
    __tablename__ = "security_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    event_type = Column(String(50), nullable=False)  # login_failed, suspicious_ip, 2fa_disabled, etc
    severity = Column(String(20), default="low")  # low, medium, high, critical
    
    # Event details
    description = Column(Text)
    event_metadata = Column(Text)  # JSON with additional context
    
    # Request context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    location = Column(String(255))  # Geolocation if available
    
    # Resolution
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(255))
    resolution_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="security_events")


class PasswordHistory(Base):
    """Track password history to prevent reuse"""
    __tablename__ = "password_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    password_hash = Column(String(255), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="password_history")


class DataEncryptionAudit(Base):
    """Audit trail for data encryption/decryption operations"""
    __tablename__ = "data_encryption_audit"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    operation = Column(String(20), nullable=False)  # encrypt, decrypt, rotate
    resource_type = Column(String(50))  # api_key, oauth_token, room_key, etc
    resource_id = Column(UUID(as_uuid=True))
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Encryption details
    algorithm = Column(String(50))  # AES-256-GCM, SHA-256, etc
    key_version = Column(Integer)
    
    # Success/failure
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Context
    ip_address = Column(String(45))
    performed_at = Column(DateTime, default=datetime.utcnow)
