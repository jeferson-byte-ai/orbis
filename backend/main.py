"""
Orbis Backend v2.0 - Main Application
Real-time multilingual video conferencing with voice cloning
"""
import asyncio
import time
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.db.base import Base
from backend.db.session import engine
from backend.api import auth, users, voices, rooms, chat
from backend.api import profile, billing
from backend.api.websocket import router as websocket_router
from backend.core.exceptions import OrbisException
from backend.core.cache import cache_service
from backend.core.security_middleware import (
    SecurityHeadersMiddleware,
    CSRFProtectionMiddleware,
    RequestIDMiddleware,
    RequestValidationMiddleware,
    SQLInjectionProtectionMiddleware,
    BruteForceProtectionMiddleware
)
from backend.core.monitoring import (
    MetricsMiddleware,
    metrics_endpoint,
    health_check_detailed
)
from backend.core.rate_limiter import RateLimitMiddleware
from backend.services.backup_service import backup_service
from backend.services.advanced_voice_cloning import advanced_voice_cloning_service
from backend.services.ultra_fast_translation import ultra_fast_translation_service
from backend.services.ultra_low_latency_webrtc import ultra_low_latency_webrtc_service
from backend.services.ai_meeting_assistant import ai_meeting_assistant
from backend.services.voice_marketplace import voice_marketplace_service
from backend.services.advanced_analytics import advanced_analytics_service
from backend.core.enterprise_features import enterprise_service, sso_service, compliance_service
from backend.services.gamification_system import gamification_system
from backend.services.advanced_ai_features import advanced_ai_features_service
from backend.services.social_networking import social_networking_service
# from backend.db.enterprise_database import enterprise_database  # Requires asyncpg
# from backend.db.sharding_manager import sharding_manager  # Requires asyncpg
# from backend.services.disaster_recovery import disaster_recovery_service  # Requires psycopg2
from ml.asr.whisper_service import whisper_service
from ml.mt.nllb_service import nllb_service
from ml.tts.coqui_service import coqui_service

# NEW: Import lazy loading and hardware detection services
from backend.services.lazy_loader import lazy_loader, ModelType
from backend.services.hardware_detection import hardware_detector

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce SQLAlchemy logging verbosity (only show warnings and errors)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('faster_whisper').setLevel(logging.WARNING)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Real Time Multilingual Meeting AI",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.debug
)

# ========== Security Middlewares ==========
# (Order matters! Applied in reverse order)

# CORS middleware (must be first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request ID for tracing
app.add_middleware(RequestIDMiddleware)

# Request validation (size limits)
app.add_middleware(RequestValidationMiddleware, max_body_size=50 * 1024 * 1024)  # 50MB

# SQL injection protection
app.add_middleware(SQLInjectionProtectionMiddleware)

# Brute force protection (DISABLED - requires Redis)
# app.add_middleware(BruteForceProtectionMiddleware)

# Rate limiting (requires Redis)
if settings.is_production:
    app.add_middleware(RateLimitMiddleware, default_limit=100, default_window=60)

# CSRF protection (disable in dev for easier testing)
if settings.is_production:
    app.add_middleware(CSRFProtectionMiddleware)

# Metrics collection
if settings.metrics_enabled:
    app.add_middleware(MetricsMiddleware)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(OrbisException)
async def orbis_exception_handler(request: Request, exc: OrbisException):
    """Handle custom Orbis exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("🚀 Starting Orbis Backend v2.0...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Create data directories
    import os
    os.makedirs(settings.storage_path, exist_ok=True)
    os.makedirs(settings.voices_path, exist_ok=True)
    os.makedirs(settings.uploads_path, exist_ok=True)
    os.makedirs(settings.models_path, exist_ok=True)
    os.makedirs("./backups", exist_ok=True)
    logger.info("✅ Storage directories created/verified")
    
    # Connect to Redis
    try:
        await cache_service.connect()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed (some features will be disabled): {e}")

    # === NEW: Lazy Loading System ===
    logger.info("🔍 Initializing Lazy Loading System...")
    
    # Detect hardware capabilities
    if settings.ml_auto_detect_hardware:
        hardware_caps = hardware_detector.detect()
        
        # Update ML service configurations based on hardware
        if settings.ml_force_device:
            device = settings.ml_force_device
        else:
            device = hardware_caps.recommended_device
        
        if settings.ml_force_whisper_model:
            whisper_model = settings.ml_force_whisper_model
        else:
            whisper_model = hardware_caps.recommended_whisper_model
        
        if settings.ml_force_nllb_model:
            nllb_model = settings.ml_force_nllb_model
        else:
            nllb_model = hardware_caps.recommended_nllb_model
        
        # Apply hardware recommendations to services
        whisper_service.model_size = whisper_model
        whisper_service.device = device
        whisper_service.compute_type = hardware_caps.recommended_compute_type
        
        nllb_service.model_name = nllb_model
        nllb_service.device = device
        
        coqui_service.device = device
        
        logger.info(f"✅ Hardware auto-configuration applied:")
        logger.info(f"   Device: {device}")
        logger.info(f"   Whisper: {whisper_model}")
        logger.info(f"   NLLB: {nllb_model}")
    
    # Register ML services with lazy loader
    if settings.enable_transcription:
        lazy_loader.register_model(ModelType.WHISPER, whisper_service)
        logger.info("📝 Registered Whisper for lazy loading")
    
    if settings.enable_translation:
        lazy_loader.register_model(ModelType.NLLB, nllb_service)
        logger.info("📝 Registered NLLB for lazy loading")
    
    if settings.enable_voice_cloning:
        lazy_loader.register_model(ModelType.COQUI, coqui_service)
        logger.info("📝 Registered Coqui TTS for lazy loading")
    
    # Start auto-unload task if enabled
    if settings.ml_auto_unload_enabled:
        lazy_loader.idle_timeout_seconds = settings.ml_unload_after_idle_seconds
        lazy_loader.check_interval_seconds = settings.ml_check_idle_interval_seconds
        await lazy_loader.start_auto_unload_task()
        logger.info(f"✅ Auto-unload enabled (idle: {settings.ml_unload_after_idle_seconds}s)")
    
    # If lazy loading is DISABLED, load all models immediately (old behavior)
    if not settings.ml_lazy_load:
        logger.info("⏳ Lazy loading disabled - loading all ML models now...")
        await _initialize_ml_services_immediately()
    else:
        logger.info("✅ Lazy loading enabled - models will load on first use")
    
    # Initialize advanced services (if enabled)
    if settings.enable_advanced_analytics or settings.enable_ai_assistant:
        await _initialize_advanced_services()
    else:
        logger.info("ℹ️ Advanced services disabled via feature flags")
    
    logger.info(f"🌍 Environment: {settings.environment}")
    logger.info(f"🔧 Debug mode: {settings.debug}")
    logger.info(f"🎯 Target latency: <{settings.target_latency_ms}ms")
    logger.info(f"🔐 Security features enabled: {settings.is_production}")
    logger.info(f"📊 Metrics enabled: {settings.metrics_enabled}")
    logger.info("✨ Orbis Backend ready!")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("👋 Shutting down Orbis Backend...")
    
    # Stop auto-unload task
    await lazy_loader.stop_auto_unload_task()
    
    # Unload all ML models
    await lazy_loader.unload_all()
    
    # Disconnect from Redis
    await cache_service.disconnect()


# Health check endpoints
@app.get("/health", tags=["Health"])
def health_check():
    """
    Basic health check endpoint
    Returns service status and version
    """
    return {
        "status": "healthy",
        "version": settings.api_version,
        "environment": settings.environment
    }


@app.get("/health/detailed", tags=["Health"])
async def health_check_detail():
    """
    Detailed health check
    Checks all system components (database, Redis, system resources)
    """
    return await health_check_detailed()


# Metrics endpoint (Prometheus)
if settings.metrics_enabled:
    @app.get("/metrics", tags=["Monitoring"])
    async def metrics(request: Request):
        """Prometheus metrics endpoint"""
        return await metrics_endpoint(request)


# Root endpoint
@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint
    """
    return {
        "message": "🌍 Welcome to Orbis - Real-time Multilingual Communication",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "websockets": {
            "audio": "/ws/audio/{room_id}",
            "status": "/ws/status/{room_id}"
        }
    }


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(voices.router)
app.include_router(rooms.router)
app.include_router(profile.router)
app.include_router(billing.router)
app.include_router(chat.router)  # Chat endpoints
app.include_router(websocket_router, prefix="/api")  # WebSocket endpoints

# Include admin API
from backend.api.admin import router as admin_router
app.include_router(admin_router)

# Include developer API
from backend.api.developer_api import router as developer_api_router
app.include_router(developer_api_router)

# Include system status API
from backend.api.system_status import router as system_status_router
app.include_router(system_status_router, prefix="/api")


# Development info
if settings.is_development:
    @app.get("/dev/info", tags=["Development"])
    def dev_info():
        """Development information (only available in dev mode)"""
        return {
            "environment": settings.environment,
            "debug": settings.debug,
            "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "sqlite",
            "cors_origins": settings.cors_origins_list,
            "ml_worker_url": settings.ml_worker_url,
            "target_latency_ms": settings.target_latency_ms,
            "websocket_endpoints": [
                "/api/ws/audio/{room_id}",
                "/api/ws/status/{room_id}"
            ],
            "backups": {
                "available": len(backup_service.list_backups()),
                "endpoint": "/dev/backups"
            }
        }
    
    @app.get("/dev/backups", tags=["Development"])
    def dev_list_backups():
        """List available backups (dev only)"""
        return backup_service.list_backups()
    
    @app.post("/dev/backup", tags=["Development"])
    async def dev_create_backup():
        """Create manual backup (dev only)"""
        result = await backup_service.create_full_backup()
        return result


def _load_service(loader, name: str):
    """Helper to load ML services with safe logging."""
    try:
        loader()
        logger.info("✅ %s ready", name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("⚠️ %s unavailable: %s", name, exc)


async def _initialize_ml_services_immediately():
    """
    Load all ML models immediately (when lazy loading is disabled)
    Uses the new lazy_loader system for consistency
    """
    logger.info("⏳ Loading all ML models immediately...")
    
    tasks = []
    
    if settings.enable_transcription:
        tasks.append(lazy_loader.load_model(ModelType.WHISPER))
    
    if settings.enable_translation:
        tasks.append(lazy_loader.load_model(ModelType.NLLB))
    
    if settings.enable_voice_cloning:
        tasks.append(lazy_loader.load_model(ModelType.COQUI))
    
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        model_names = []
        if settings.enable_transcription:
            model_names.append("Whisper")
        if settings.enable_translation:
            model_names.append("NLLB")
        if settings.enable_voice_cloning:
            model_names.append("Coqui TTS")
        
        for name, success in zip(model_names, results):
            if success:
                logger.info(f"✅ {name} loaded")
            else:
                logger.warning(f"⚠️ {name} failed to load")
    
    logger.info("✅ ML models initialization complete")


async def _initialize_advanced_services():
    """Initialize advanced services for billion-dollar scale."""
    logger.info("🚀 Initializing advanced services...")
    
    # Initialize enterprise services
    await enterprise_service.initialize()
    logger.info("✅ Enterprise service initialized")
    
    # Initialize advanced voice cloning
    await advanced_voice_cloning_service.initialize()
    logger.info("✅ Advanced voice cloning service initialized")
    
    # Initialize ultra-fast translation (DISABLED - high memory usage)
    # await ultra_fast_translation_service.initialize()
    # logger.info("✅ Ultra-fast translation service initialized")
    
    # Initialize ultra-low latency WebRTC
    await ultra_low_latency_webrtc_service.initialize()
    logger.info("✅ Ultra-low latency WebRTC service initialized")
    
    # Initialize AI meeting assistant
    await ai_meeting_assistant.initialize()
    logger.info("✅ AI meeting assistant initialized")
    
    # Initialize voice marketplace
    await voice_marketplace_service.initialize()
    logger.info("✅ Voice marketplace service initialized")
    
    # Initialize advanced analytics
    await advanced_analytics_service.initialize()
    logger.info("✅ Advanced analytics service initialized")
    
    # Initialize gamification system
    await gamification_system.initialize()
    logger.info("✅ Gamification system initialized")
    
    # Initialize advanced AI features
    await advanced_ai_features_service.initialize()
    logger.info("✅ Advanced AI features service initialized")
    
    # Initialize social networking
    await social_networking_service.initialize()
    logger.info("✅ Social networking service initialized")
    
    # Initialize enterprise database system
    # await enterprise_database.initialize()  # Disabled - requires asyncpg
    # logger.info("✅ Enterprise database system initialized")
    
    # Initialize sharding manager
    # await sharding_manager.initialize()  # Disabled - requires asyncpg
    # logger.info("✅ Sharding manager initialized")
    
    # Initialize disaster recovery service
    # await disaster_recovery_service.initialize()  # Disabled - requires psycopg2
    # logger.info("✅ Disaster recovery service initialized")
    
    logger.info("🎯 All advanced services initialized successfully!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
