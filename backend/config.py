"""
Configuration management using Pydantic Settings
Loads from environment variables and .env file
"""
from functools import lru_cache
from typing import List, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "Orbis API"
    api_version: str = "2.0.0"
    
    # Database
    database_url: str = Field(
        default="sqlite:///./data/orbis.db",
        description="Database connection URL"
    )
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "orbis"
    database_user: str = "orbis"
    database_password: str = ""
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Security
    secret_key: str = Field(
        min_length=32,
        description="Secret key for encryption"
    )
    jwt_secret: str = Field(
        min_length=32,
        description="JWT secret key"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 10080  # 7 days (7 * 24 * 60)
    jwt_refresh_token_expire_days: int = 30
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_allow_credentials: bool = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins if isinstance(self.cors_origins, list) else ["http://localhost:3000", "http://localhost:5173"]
    
    # ML Services
    ml_worker_url: str = "http://localhost:8001"
    
    asr_model: str = "openai/whisper-large-v3-turbo"
    asr_device: Literal["cuda", "cpu"] = "cuda"
    
    mt_model: str = "facebook/nllb-200-distilled-600M"
    mt_device: Literal["cuda", "cpu"] = "cuda"
    
    tts_model: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    tts_device: Literal["cuda", "cpu"] = "cuda"
    
    # Voice Cloning
    voice_clone_min_duration: int = 180  # 3 minutes
    voice_clone_max_duration: int = 300  # 5 minutes
    voice_clone_sample_rate: int = 22050
    
    # Storage
    storage_path: str = "./data"
    voices_path: str = "./data/voices"
    uploads_path: str = "./data/uploads"
    models_path: str = "./data/models"
    
    # Features
    max_room_participants: int = 100
    max_room_duration: int = 240  # minutes
    target_latency_ms: int = 250  # Target <250ms
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_auth_per_minute: int = 10
    rate_limit_voice_clone_per_hour: int = 1
    
    # Monitoring
    metrics_enabled: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    # Email (SMTP)
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    from_email: str = Field(default="noreply@orbis.app")
    from_name: str = Field(default="Orbis")
    
    # Frontend
    frontend_url: str = Field(default="http://localhost:3000")
    
    # OAuth
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    github_client_id: str = Field(default="")
    github_client_secret: str = Field(default="")
    
    # OpenAI
    openai_api_key: str = Field(default="")
    
    # Stripe (Payments)
    stripe_api_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    stripe_price_pro_monthly: str = Field(default="")
    stripe_price_pro_yearly: str = Field(default="")
    stripe_price_enterprise: str = Field(default="")
    
    # S3 Storage (Optional)
    s3_bucket: str = Field(default="")
    s3_region: str = Field(default="us-east-1")
    s3_access_key: str = Field(default="")
    s3_secret_key: str = Field(default="")
    
    # Analytics
    google_analytics_id: str = Field(default="")
    mixpanel_token: str = Field(default="")
    
    # === FEATURE FLAGS ===
    
    # Core Features (Always Active)
    enable_auth: bool = Field(default=True, description="Enable authentication system")
    enable_rooms: bool = Field(default=True, description="Enable video rooms")
    enable_websocket: bool = Field(default=True, description="Enable WebSocket for real-time")
    
    # ML Features (Lazy Loaded)
    enable_voice_cloning: bool = Field(default=True, description="Enable Coqui TTS voice cloning")
    enable_translation: bool = Field(default=True, description="Enable NLLB translation")
    enable_transcription: bool = Field(default=True, description="Enable Whisper transcription")
    
    # Advanced Features (Optional)
    enable_ai_assistant: bool = Field(default=False, description="Enable AI meeting assistant")
    enable_advanced_analytics: bool = Field(default=True, description="Enable advanced analytics")
    enable_gamification: bool = Field(default=True, description="Enable gamification system")
    enable_voice_marketplace: bool = Field(default=False, description="Enable voice marketplace")
    enable_social_networking: bool = Field(default=False, description="Enable social features")
    
    # Enterprise Features (Optional)
    enable_enterprise_features: bool = Field(default=False, description="Enable LDAP/SAML/SSO")
    enable_disaster_recovery: bool = Field(default=False, description="Enable disaster recovery")
    enable_database_sharding: bool = Field(default=False, description="Enable database sharding")
    
    # Legacy/Other Features
    enable_recordings: bool = Field(default=True, description="Enable room recordings")
    enable_oauth: bool = Field(default=True, description="Enable OAuth (Google/GitHub)")
    enable_payments: bool = Field(default=False, description="Enable Stripe payments")
    
    # === PERFORMANCE & OPTIMIZATION ===
    
    # Lazy Loading Configuration
    ml_lazy_load: bool = Field(default=True, description="Enable lazy loading for ML models")
    ml_auto_detect_hardware: bool = Field(default=True, description="Auto-detect hardware and choose models")
    ml_unload_after_idle_seconds: int = Field(default=3600, description="Unload models after idle time (seconds)")
    ml_auto_unload_enabled: bool = Field(default=True, description="Enable automatic model unloading")
    ml_check_idle_interval_seconds: int = Field(default=300, description="Check idle models every N seconds")
    
    # Hardware Override (Leave empty for auto-detection)
    ml_force_device: str = Field(default="", description="Force device: 'cuda', 'cpu', or '' for auto")
    ml_force_whisper_model: str = Field(default="", description="Force Whisper model or '' for auto")
    ml_force_nllb_model: str = Field(default="", description="Force NLLB model or '' for auto")
    

    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    # Helper methods for feature checking
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        attr_name = f"enable_{feature_name}"
        return getattr(self, attr_name, False)
    
    def get_ml_config(self) -> dict:
        """Get ML configuration summary"""
        return {
            "lazy_load": self.ml_lazy_load,
            "auto_detect_hardware": self.ml_auto_detect_hardware,
            "auto_unload_enabled": self.ml_auto_unload_enabled,
            "idle_timeout_seconds": self.ml_unload_after_idle_seconds,
            "check_interval_seconds": self.ml_check_idle_interval_seconds,
            "force_device": self.ml_force_device or "auto",
            "force_whisper_model": self.ml_force_whisper_model or "auto",
            "force_nllb_model": self.ml_force_nllb_model or "auto"
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
