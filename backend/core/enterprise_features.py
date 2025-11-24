"""
Enterprise-Grade Features for Orbis
Advanced features for billion-dollar scale
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from backend.db.models import User, Room, VoiceProfile, Subscription
from backend.db.session import async_engine
from backend.core.cache import cache_service
from backend.config import settings

logger = logging.getLogger(__name__)


class EnterpriseTier(Enum):
    """Enterprise subscription tiers"""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class EnterpriseLimits:
    """Enterprise feature limits per tier"""
    max_participants: int
    max_room_duration: int  # minutes
    max_concurrent_rooms: int
    max_voice_profiles: int
    max_storage_gb: int
    max_api_calls_per_month: int
    priority_support: bool
    sso_enabled: bool
    custom_branding: bool
    on_premise_deployment: bool
    dedicated_support: bool
    sla_uptime: float  # percentage


ENTERPRISE_LIMITS = {
    EnterpriseTier.STARTER: EnterpriseLimits(
        max_participants=10,
        max_room_duration=60,
        max_concurrent_rooms=5,
        max_voice_profiles=3,
        max_storage_gb=1,
        max_api_calls_per_month=1000,
        priority_support=False,
        sso_enabled=False,
        custom_branding=False,
        on_premise_deployment=False,
        dedicated_support=False,
        sla_uptime=99.0
    ),
    EnterpriseTier.PROFESSIONAL: EnterpriseLimits(
        max_participants=25,
        max_room_duration=240,
        max_concurrent_rooms=20,
        max_voice_profiles=10,
        max_storage_gb=10,
        max_api_calls_per_month=10000,
        priority_support=True,
        sso_enabled=False,
        custom_branding=False,
        on_premise_deployment=False,
        dedicated_support=False,
        sla_uptime=99.5
    ),
    EnterpriseTier.BUSINESS: EnterpriseLimits(
        max_participants=100,
        max_room_duration=480,
        max_concurrent_rooms=100,
        max_voice_profiles=50,
        max_storage_gb=100,
        max_api_calls_per_month=100000,
        priority_support=True,
        sso_enabled=True,
        custom_branding=True,
        on_premise_deployment=False,
        dedicated_support=True,
        sla_uptime=99.9
    ),
    EnterpriseTier.ENTERPRISE: EnterpriseLimits(
        max_participants=500,
        max_room_duration=1440,  # 24 hours
        max_concurrent_rooms=500,
        max_voice_profiles=200,
        max_storage_gb=1000,
        max_api_calls_per_month=1000000,
        priority_support=True,
        sso_enabled=True,
        custom_branding=True,
        on_premise_deployment=True,
        dedicated_support=True,
        sla_uptime=99.95
    ),
    EnterpriseTier.UNLIMITED: EnterpriseLimits(
        max_participants=-1,  # unlimited
        max_room_duration=-1,  # unlimited
        max_concurrent_rooms=-1,  # unlimited
        max_voice_profiles=-1,  # unlimited
        max_storage_gb=-1,  # unlimited
        max_api_calls_per_month=-1,  # unlimited
        priority_support=True,
        sso_enabled=True,
        custom_branding=True,
        on_premise_deployment=True,
        dedicated_support=True,
        sla_uptime=99.99
    )
}


class EnterpriseService:
    """Enterprise-grade service for advanced features"""
    
    def __init__(self):
        self.redis = None
        self.analytics_cache = {}
        
    async def initialize(self):
        """Initialize enterprise service"""
        try:
            self.redis = redis.from_url(settings.redis_url)
            await self.redis.ping()
            logger.info("✅ Enterprise service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Enterprise service Redis connection failed: {e}")
    
    async def get_user_limits(self, user_id: int) -> EnterpriseLimits:
        """Get enterprise limits for a user"""
        # Get user subscription tier
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription or not subscription.is_active:
                return ENTERPRISE_LIMITS[EnterpriseTier.STARTER]
            
            tier = EnterpriseTier(subscription.tier)
            return ENTERPRISE_LIMITS[tier]
    
    async def check_room_limits(self, user_id: int, room_id: str) -> Dict[str, Any]:
        """Check if user can create/join room based on limits"""
        limits = await self.get_user_limits(user_id)
        
        # Check concurrent rooms
        active_rooms = await self.get_user_active_rooms(user_id)
        if limits.max_concurrent_rooms != -1 and len(active_rooms) >= limits.max_concurrent_rooms:
            return {
                "allowed": False,
                "reason": "max_concurrent_rooms_exceeded",
                "current": len(active_rooms),
                "limit": limits.max_concurrent_rooms
            }
        
        return {"allowed": True, "limits": limits}
    
    async def get_user_active_rooms(self, user_id: int) -> List[str]:
        """Get list of active rooms for a user"""
        cache_key = f"user_active_rooms:{user_id}"
        
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Failed to get cached active rooms: {e}")
        
        # Query database for active rooms
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(Room).where(
                    Room.created_by == user_id,
                    Room.status == "active",
                    Room.created_at > datetime.utcnow() - timedelta(hours=24)
                )
            )
            rooms = result.scalars().all()
            room_ids = [room.id for room in rooms]
        
        # Cache for 5 minutes
        if self.redis:
            try:
                await self.redis.setex(
                    cache_key, 
                    300, 
                    json.dumps(room_ids)
                )
            except Exception as e:
                logger.warning(f"Failed to cache active rooms: {e}")
        
        return room_ids
    
    async def track_usage(self, user_id: int, event_type: str, metadata: Dict[str, Any]):
        """Track enterprise usage metrics"""
        usage_data = {
            "user_id": user_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata
        }
        
        # Store in Redis for real-time analytics
        if self.redis:
            try:
                await self.redis.lpush(
                    f"usage_events:{user_id}",
                    json.dumps(usage_data)
                )
                await self.redis.expire(f"usage_events:{user_id}", 86400 * 30)  # 30 days
            except Exception as e:
                logger.warning(f"Failed to track usage: {e}")
        
        # Store in analytics cache for immediate access
        if user_id not in self.analytics_cache:
            self.analytics_cache[user_id] = []
        
        self.analytics_cache[user_id].append(usage_data)
        
        # Keep only last 1000 events in memory
        if len(self.analytics_cache[user_id]) > 1000:
            self.analytics_cache[user_id] = self.analytics_cache[user_id][-1000:]
    
    async def get_usage_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage analytics for a user"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        analytics = {
            "period": f"{start_date.date()} to {end_date.date()}",
            "total_meetings": 0,
            "total_minutes": 0,
            "total_participants": 0,
            "voice_clones_created": 0,
            "api_calls": 0,
            "storage_used_gb": 0,
            "daily_breakdown": {}
        }
        
        # Get from Redis if available
        if self.redis:
            try:
                events = await self.redis.lrange(
                    f"usage_events:{user_id}",
                    0, -1
                )
                
                for event_json in events:
                    event = json.loads(event_json)
                    event_date = datetime.fromisoformat(event["timestamp"])
                    
                    if start_date <= event_date <= end_date:
                        event_type = event["event_type"]
                        metadata = event.get("metadata", {})
                        
                        # Aggregate metrics
                        if event_type == "meeting_started":
                            analytics["total_meetings"] += 1
                            analytics["total_participants"] += metadata.get("participant_count", 1)
                        elif event_type == "meeting_ended":
                            analytics["total_minutes"] += metadata.get("duration_minutes", 0)
                        elif event_type == "voice_clone_created":
                            analytics["voice_clones_created"] += 1
                        elif event_type == "api_call":
                            analytics["api_calls"] += 1
                        elif event_type == "storage_used":
                            analytics["storage_used_gb"] += metadata.get("size_gb", 0)
                        
                        # Daily breakdown
                        day_key = event_date.date().isoformat()
                        if day_key not in analytics["daily_breakdown"]:
                            analytics["daily_breakdown"][day_key] = {
                                "meetings": 0,
                                "minutes": 0,
                                "participants": 0
                            }
                        
                        if event_type == "meeting_started":
                            analytics["daily_breakdown"][day_key]["meetings"] += 1
                            analytics["daily_breakdown"][day_key]["participants"] += metadata.get("participant_count", 1)
                        elif event_type == "meeting_ended":
                            analytics["daily_breakdown"][day_key]["minutes"] += metadata.get("duration_minutes", 0)
                            
            except Exception as e:
                logger.warning(f"Failed to get usage analytics from Redis: {e}")
        
        return analytics
    
    async def enforce_limits(self, user_id: int, action: str, **kwargs) -> Dict[str, Any]:
        """Enforce enterprise limits for user actions"""
        limits = await self.get_user_limits(user_id)
        
        if action == "create_room":
            # Check concurrent rooms
            active_rooms = await self.get_user_active_rooms(user_id)
            if limits.max_concurrent_rooms != -1 and len(active_rooms) >= limits.max_concurrent_rooms:
                return {
                    "allowed": False,
                    "reason": "max_concurrent_rooms_exceeded",
                    "current": len(active_rooms),
                    "limit": limits.max_concurrent_rooms
                }
        
        elif action == "join_room":
            # Check room participant limit
            room_id = kwargs.get("room_id")
            if room_id:
                room_participants = await self.get_room_participant_count(room_id)
                if limits.max_participants != -1 and room_participants >= limits.max_participants:
                    return {
                        "allowed": False,
                        "reason": "max_participants_exceeded",
                        "current": room_participants,
                        "limit": limits.max_participants
                    }
        
        elif action == "create_voice_clone":
            # Check voice profile limit
            voice_count = await self.get_user_voice_count(user_id)
            if limits.max_voice_profiles != -1 and voice_count >= limits.max_voice_profiles:
                return {
                    "allowed": False,
                    "reason": "max_voice_profiles_exceeded",
                    "current": voice_count,
                    "limit": limits.max_voice_profiles
                }
        
        elif action == "api_call":
            # Check API call limit
            monthly_calls = await self.get_monthly_api_calls(user_id)
            if limits.max_api_calls_per_month != -1 and monthly_calls >= limits.max_api_calls_per_month:
                return {
                    "allowed": False,
                    "reason": "max_api_calls_exceeded",
                    "current": monthly_calls,
                    "limit": limits.max_api_calls_per_month
                }
        
        return {"allowed": True, "limits": limits}
    
    async def get_room_participant_count(self, room_id: str) -> int:
        """Get current participant count for a room"""
        cache_key = f"room_participants:{room_id}"
        
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return int(cached)
            except Exception as e:
                logger.warning(f"Failed to get cached participant count: {e}")
        
        # This would typically come from WebSocket connections
        # For now, return a placeholder
        return 0
    
    async def get_user_voice_count(self, user_id: int) -> int:
        """Get voice profile count for a user"""
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(VoiceProfile).where(VoiceProfile.user_id == user_id)
            )
            return len(result.scalars().all())
    
    async def get_monthly_api_calls(self, user_id: int) -> int:
        """Get monthly API call count for a user"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if self.redis:
            try:
                events = await self.redis.lrange(
                    f"usage_events:{user_id}",
                    0, -1
                )
                
                count = 0
                for event_json in events:
                    event = json.loads(event_json)
                    event_date = datetime.fromisoformat(event["timestamp"])
                    
                    if (event_date >= start_of_month and 
                        event.get("event_type") == "api_call"):
                        count += 1
                
                return count
            except Exception as e:
                logger.warning(f"Failed to get monthly API calls: {e}")
        
        return 0


# Global enterprise service instance
enterprise_service = EnterpriseService()


class SSOProvider(Enum):
    """SSO provider types"""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    OKTA = "okta"
    AUTH0 = "auth0"
    SAML = "saml"
    LDAP = "ldap"


class SSOService:
    """Single Sign-On service for enterprise customers"""
    
    def __init__(self):
        self.providers = {}
    
    async def configure_provider(self, provider: SSOProvider, config: Dict[str, Any]):
        """Configure SSO provider"""
        self.providers[provider.value] = config
        logger.info(f"✅ SSO provider {provider.value} configured")
    
    async def authenticate_user(self, provider: SSOProvider, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user via SSO"""
        if provider.value not in self.providers:
            raise ValueError(f"SSO provider {provider.value} not configured")
        
        config = self.providers[provider.value]
        
        # This would integrate with actual SSO providers
        # For now, return a mock response
        return {
            "user_id": "sso_user_123",
            "email": "user@company.com",
            "name": "Enterprise User",
            "groups": ["employees", "managers"],
            "attributes": {
                "department": "Engineering",
                "role": "Senior Developer"
            }
        }


# Global SSO service instance
sso_service = SSOService()


class ComplianceService:
    """Compliance and audit service for enterprise customers"""
    
    def __init__(self):
        self.audit_logs = []
    
    async def log_audit_event(self, user_id: int, action: str, resource: str, metadata: Dict[str, Any]):
        """Log audit event for compliance"""
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "metadata": metadata,
            "ip_address": metadata.get("ip_address"),
            "user_agent": metadata.get("user_agent")
        }
        
        self.audit_logs.append(audit_event)
        
        # Store in database for long-term retention
        # This would typically go to a dedicated audit database
        
        logger.info(f"Audit event logged: {action} on {resource} by user {user_id}")
    
    async def get_audit_logs(self, user_id: Optional[int] = None, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get audit logs with optional filtering"""
        logs = self.audit_logs
        
        if user_id:
            logs = [log for log in logs if log["user_id"] == user_id]
        
        if start_date:
            logs = [log for log in logs if datetime.fromisoformat(log["timestamp"]) >= start_date]
        
        if end_date:
            logs = [log for log in logs if datetime.fromisoformat(log["timestamp"]) <= end_date]
        
        return logs


# Global compliance service instance
compliance_service = ComplianceService()




