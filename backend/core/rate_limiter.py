"""
Advanced Rate Limiting Middleware
Implements sliding window rate limiting with Redis
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Callable
import time
from functools import wraps
from backend.core.cache import cache_service
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-backed rate limiter with sliding window"""
    
    def __init__(
        self,
        requests: int,
        window: int,
        key_prefix: str = "rate_limit"
    ):
        """
        Initialize rate limiter
        
        Args:
            requests: Max requests allowed
            window: Time window in seconds
            key_prefix: Redis key prefix
        """
        self.requests = requests
        self.window = window
        self.key_prefix = key_prefix
    
    def _get_key(self, identifier: str) -> str:
        """Generate Redis key for identifier"""
        return f"{self.key_prefix}:{identifier}"
    
    async def check_limit(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if request is within rate limit
        
        Returns: (is_allowed, headers_dict)
        """
        key = self._get_key(identifier)
        
        is_allowed, remaining = await cache_service.check_rate_limit(
            key=key,
            max_requests=self.requests,
            window_seconds=self.window
        )
        
        headers = {
            "X-RateLimit-Limit": str(self.requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Window": str(self.window)
        }
        
        if not is_allowed:
            # Get TTL for retry-after header
            ttl = await cache_service.redis.ttl(key) if cache_service.redis else self.window
            headers["Retry-After"] = str(max(1, ttl))
        
        return is_allowed, headers
    
    async def reset(self, identifier: str) -> bool:
        """Reset rate limit for identifier"""
        key = self._get_key(identifier)
        return await cache_service.reset_rate_limit(key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware"""
    
    def __init__(self, app, default_limit: int = 100, default_window: int = 60):
        super().__init__(app)
        self.default_limiter = RateLimiter(
            requests=default_limit,
            window=default_window,
            key_prefix="global_rate_limit"
        )
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get identifier (IP or user ID)
        identifier = self._get_identifier(request)
        
        # Check rate limit
        is_allowed, headers = await self.default_limiter.check_limit(identifier)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {identifier} on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": headers.get("Retry-After", "60")
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier from request"""
        # Try to get user ID from auth
        user_id = request.state.__dict__.get("user_id")
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host
        
        return f"ip:{ip}"


def rate_limit(requests: int = 60, window: int = 60, key_func: Optional[Callable] = None):
    """
    Decorator for endpoint-specific rate limiting
    
    Usage:
        @router.get("/expensive-endpoint")
        @rate_limit(requests=10, window=60)
        async def expensive_operation():
            pass
    """
    def decorator(func):
        limiter = RateLimiter(
            requests=requests,
            window=window,
            key_prefix=f"endpoint_limit:{func.__name__}"
        )
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get("request")
            
            if not request:
                # No request object found, skip rate limiting
                return await func(*args, **kwargs)
            
            # Get identifier
            if key_func:
                identifier = key_func(request)
            else:
                # Default: use IP or user ID
                user_id = request.state.__dict__.get("user_id")
                if user_id:
                    identifier = f"user:{user_id}"
                else:
                    identifier = f"ip:{request.client.host}"
            
            # Check rate limit
            is_allowed, headers = await limiter.check_limit(identifier)
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers=headers
                )
            
            # Execute function
            response = await func(*args, **kwargs)
            
            return response
        
        return wrapper
    return decorator


# Pre-configured rate limiters for common use cases
auth_rate_limiter = RateLimiter(
    requests=settings.rate_limit_auth_per_minute,
    window=60,
    key_prefix="auth_rate_limit"
)

voice_clone_rate_limiter = RateLimiter(
    requests=settings.rate_limit_voice_clone_per_hour,
    window=3600,
    key_prefix="voice_clone_rate_limit"
)

api_rate_limiter = RateLimiter(
    requests=settings.rate_limit_per_minute,
    window=60,
    key_prefix="api_rate_limit"
)
