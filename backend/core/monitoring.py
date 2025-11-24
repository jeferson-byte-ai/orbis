"""
Monitoring & Observability
Prometheus metrics, structured logging, and health checks
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import structlog
from datetime import datetime
import psutil
import os

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# ========== Prometheus Metrics ==========

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

# WebSocket metrics
websocket_connections_total = Gauge(
    "websocket_connections_total",
    "Current WebSocket connections",
    ["room_id"]
)

websocket_messages_total = Counter(
    "websocket_messages_total",
    "Total WebSocket messages",
    ["type", "room_id"]
)

# Audio processing metrics
audio_processing_duration_seconds = Histogram(
    "audio_processing_duration_seconds",
    "Audio processing latency",
    ["stage"]  # asr, mt, tts
)

audio_chunks_processed_total = Counter(
    "audio_chunks_processed_total",
    "Total audio chunks processed",
    ["language"]
)

# Translation metrics
translations_total = Counter(
    "translations_total",
    "Total translations",
    ["source_lang", "target_lang"]
)

translation_quality_score = Histogram(
    "translation_quality_score",
    "Translation quality scores",
    ["source_lang", "target_lang"]
)

# Room metrics
active_rooms_total = Gauge(
    "active_rooms_total",
    "Number of active rooms"
)

room_participants_total = Gauge(
    "room_participants_total",
    "Total participants across all rooms"
)

room_duration_seconds = Histogram(
    "room_duration_seconds",
    "Room session duration"
)

# Voice cloning metrics
voice_cloning_requests_total = Counter(
    "voice_cloning_requests_total",
    "Total voice cloning requests",
    ["status"]  # success, failed
)

voice_cloning_duration_seconds = Histogram(
    "voice_cloning_duration_seconds",
    "Voice cloning processing time"
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation"]  # select, insert, update, delete
)

db_connections_total = Gauge(
    "db_connections_total",
    "Active database connections"
)

# Cache metrics
cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["key_prefix"]
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["key_prefix"]
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors",
    ["type", "endpoint"]
)

# System metrics
system_cpu_usage = Gauge(
    "system_cpu_usage_percent",
    "System CPU usage percentage"
)

system_memory_usage = Gauge(
    "system_memory_usage_bytes",
    "System memory usage in bytes"
)

system_disk_usage = Gauge(
    "system_disk_usage_percent",
    "System disk usage percentage"
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic metrics collection"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Collect metrics for each request"""
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Record metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status_code
            ).inc()
            
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            # Add timing header
            response.headers["X-Process-Time"] = f"{duration:.4f}"
            
            return response
            
        except Exception as e:
            # Record error
            errors_total.labels(
                type=type(e).__name__,
                endpoint=request.url.path
            ).inc()
            
            # Log error
            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=time.time() - start_time
            )
            
            raise


def update_system_metrics():
    """Update system resource metrics"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu_percent)
        
        # Memory
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.used)
        
        # Disk
        disk = psutil.disk_usage('/')
        system_disk_usage.set(disk.percent)
        
    except Exception as e:
        logger.error("system_metrics_error", error=str(e))


async def metrics_endpoint(request: Request):
    """Endpoint to expose Prometheus metrics"""
    # Update system metrics before serving
    update_system_metrics()
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ========== Structured Logging Helpers ==========

def log_request(request: Request, duration: float, status_code: int):
    """Log HTTP request with structured data"""
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        duration=duration,
        client_ip=request.client.host,
        user_agent=request.headers.get("user-agent", "unknown")
    )


def log_audio_processing(
    stage: str,
    duration: float,
    language: str,
    success: bool,
    metadata: dict = None
):
    """Log audio processing event"""
    logger.info(
        "audio_processing",
        stage=stage,
        duration=duration,
        language=language,
        success=success,
        metadata=metadata or {}
    )
    
    # Update metrics
    audio_processing_duration_seconds.labels(stage=stage).observe(duration)
    if success:
        audio_chunks_processed_total.labels(language=language).inc()


def log_translation(
    source_lang: str,
    target_lang: str,
    duration: float,
    quality_score: float = None,
    word_count: int = None
):
    """Log translation event"""
    logger.info(
        "translation",
        source_lang=source_lang,
        target_lang=target_lang,
        duration=duration,
        quality_score=quality_score,
        word_count=word_count
    )
    
    # Update metrics
    translations_total.labels(
        source_lang=source_lang,
        target_lang=target_lang
    ).inc()
    
    if quality_score is not None:
        translation_quality_score.labels(
            source_lang=source_lang,
            target_lang=target_lang
        ).observe(quality_score)


def log_room_event(
    event_type: str,
    room_id: str,
    participant_count: int = None,
    metadata: dict = None
):
    """Log room event"""
    logger.info(
        "room_event",
        event_type=event_type,
        room_id=room_id,
        participant_count=participant_count,
        metadata=metadata or {}
    )


def log_error(
    error_type: str,
    message: str,
    context: dict = None,
    exc_info: Exception = None
):
    """Log error with context"""
    logger.error(
        "error",
        error_type=error_type,
        message=message,
        context=context or {},
        exc_info=exc_info
    )


# ========== Health Check ==========

async def health_check_detailed() -> dict:
    """Comprehensive health check"""
    from backend.core.cache import cache_service
    from backend.db.session import engine, async_engine
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check database
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health["components"]["database"] = {
            "status": "healthy",
            "type": "postgresql" if "postgresql" in str(engine.url) else "sqlite"
        }
    except Exception as e:
        health["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
    
    # Check Redis
    redis_health = await cache_service.health_check()
    health["components"]["redis"] = redis_health
    if redis_health["status"] != "healthy":
        health["status"] = "degraded"
    
    # System resources
    health["components"]["system"] = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent
    }
    
    # Check if system is under heavy load
    if (psutil.cpu_percent() > 90 or 
        psutil.virtual_memory().percent > 90 or 
        psutil.disk_usage('/').percent > 90):
        health["status"] = "degraded"
        health["warnings"] = ["System under heavy load"]
    
    return health


# ========== Performance Monitoring ==========

class PerformanceMonitor:
    """Context manager for monitoring code performance"""
    
    def __init__(self, operation: str, metadata: dict = None):
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            # Error occurred
            logger.error(
                "operation_failed",
                operation=self.operation,
                duration=duration,
                error=str(exc_val),
                **self.metadata
            )
        else:
            # Success
            logger.info(
                "operation_completed",
                operation=self.operation,
                duration=duration,
                **self.metadata
            )
        
        return False  # Don't suppress exceptions


def monitor_performance(operation: str):
    """Decorator for monitoring function performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with PerformanceMonitor(operation):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
