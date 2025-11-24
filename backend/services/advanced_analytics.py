"""
Advanced Analytics Service
Comprehensive analytics and insights for billion-dollar scale
"""
import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import uuid

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.db.models import User, Room, VoiceProfile, Subscription
# from backend.db.models import APICall  # TODO: Create this model
# from backend.db.models import MeetingTranscript  # TODO: Create this model
from backend.db.session import async_engine

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    USER_ENGAGEMENT = "user_engagement"
    REVENUE = "revenue"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    USAGE = "usage"
    GROWTH = "growth"
    RETENTION = "retention"
    CONVERSION = "conversion"


class TimeGranularity(Enum):
    """Time granularity for analytics"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class AnalyticsMetric:
    """Analytics metric"""
    id: str
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    dimensions: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class UserSegment:
    """User segment for analytics"""
    id: str
    name: str
    criteria: Dict[str, Any]
    user_count: int
    created_at: datetime


@dataclass
class CohortAnalysis:
    """Cohort analysis result"""
    cohort_period: str
    cohort_size: int
    retention_rates: Dict[str, float]
    revenue_per_user: Dict[str, float]
    engagement_scores: Dict[str, float]


@dataclass
class FunnelAnalysis:
    """Funnel analysis result"""
    funnel_name: str
    steps: List[str]
    conversion_rates: Dict[str, float]
    drop_off_points: List[str]
    total_conversions: int


class AdvancedAnalyticsService:
    """Advanced analytics service for comprehensive insights"""
    
    def __init__(self):
        self.redis = None
        self.metrics_cache = {}
        self.user_segments = {}
        self.cohort_data = {}
        self.funnel_data = {}
        
        # Analytics configurations
        self.metric_configs = {
            MetricType.USER_ENGAGEMENT: {
                "retention_window": 30,  # days
                "engagement_threshold": 0.5,
                "session_duration_threshold": 300  # seconds
            },
            MetricType.REVENUE: {
                "currency": "USD",
                "conversion_window": 7,  # days
                "lifetime_value_window": 365  # days
            },
            MetricType.PERFORMANCE: {
                "latency_threshold": 250,  # ms
                "quality_threshold": 0.8,
                "uptime_threshold": 0.99
            }
        }
        
        # Real-time metrics
        self.real_time_metrics = {
            "active_users": 0,
            "active_rooms": 0,
            "translation_requests": 0,
            "voice_synthesis_requests": 0,
            "api_calls": 0,
            "revenue_today": 0.0
        }
    
    async def initialize(self):
        """Initialize advanced analytics service"""
        try:
            # Connect to Redis
            self.redis = redis.from_url(settings.redis_url)
            await self.redis.ping()
            
            # Load existing data
            await self._load_analytics_data()
            
            # Start background tasks
            asyncio.create_task(self._metrics_collector())
            asyncio.create_task(self._real_time_updater())
            asyncio.create_task(self._cohort_analyzer())
            asyncio.create_task(self._funnel_analyzer())
            
            logger.info("✅ Advanced Analytics Service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Advanced Analytics Service: {e}")
    
    async def _load_analytics_data(self):
        """Load existing analytics data"""
        try:
            # Load user segments
            await self._load_user_segments()
            
            # Load cohort data
            await self._load_cohort_data()
            
            # Load funnel data
            await self._load_funnel_data()
            
        except Exception as e:
            logger.warning(f"Failed to load analytics data: {e}")
    
    async def _load_user_segments(self):
        """Load user segments from database"""
        try:
            async with AsyncSession(async_engine) as session:
                # This would load from a UserSegment table
                # For now, create default segments
                self.user_segments = {
                    "new_users": UserSegment(
                        id="new_users",
                        name="New Users",
                        criteria={"days_since_signup": {"$lte": 7}},
                        user_count=0,
                        created_at=datetime.utcnow()
                    ),
                    "active_users": UserSegment(
                        id="active_users",
                        name="Active Users",
                        criteria={"last_activity": {"$gte": datetime.utcnow() - timedelta(days=7)}},
                        user_count=0,
                        created_at=datetime.utcnow()
                    ),
                    "premium_users": UserSegment(
                        id="premium_users",
                        name="Premium Users",
                        criteria={"subscription_tier": {"$in": ["pro", "business", "enterprise"]}},
                        user_count=0,
                        created_at=datetime.utcnow()
                    )
                }
        except Exception as e:
            logger.warning(f"Failed to load user segments: {e}")
    
    async def _load_cohort_data(self):
        """Load cohort analysis data"""
        # This would load from database
        pass
    
    async def _load_funnel_data(self):
        """Load funnel analysis data"""
        # This would load from database
        pass
    
    async def track_event(self, event_type: str, user_id: int, 
                         properties: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Track analytics event"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "properties": properties,
            "timestamp": timestamp.isoformat()
        }
        
        # Store in Redis for real-time processing
        if self.redis:
            try:
                await self.redis.lpush(
                    f"analytics_events:{event_type}",
                    json.dumps(event)
                )
                await self.redis.expire(f"analytics_events:{event_type}", 86400 * 30)  # 30 days
            except Exception as e:
                logger.warning(f"Failed to store analytics event: {e}")
        
        # Update real-time metrics
        await self._update_real_time_metrics(event_type, properties)
    
    async def _update_real_time_metrics(self, event_type: str, properties: Dict[str, Any]):
        """Update real-time metrics based on event"""
        if event_type == "user_login":
            self.real_time_metrics["active_users"] += 1
        elif event_type == "room_created":
            self.real_time_metrics["active_rooms"] += 1
        elif event_type == "translation_request":
            self.real_time_metrics["translation_requests"] += 1
        elif event_type == "voice_synthesis_request":
            self.real_time_metrics["voice_synthesis_requests"] += 1
        elif event_type == "api_call":
            self.real_time_metrics["api_calls"] += 1
        elif event_type == "payment_completed":
            amount = properties.get("amount", 0)
            self.real_time_metrics["revenue_today"] += amount
    
    async def get_user_engagement_metrics(self, user_id: int, 
                                        days: int = 30) -> Dict[str, Any]:
        """Get user engagement metrics"""
        try:
            async with AsyncSession(async_engine) as session:
                # Get user data
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {"error": "User not found"}
                
                # Calculate engagement metrics
                engagement_metrics = {
                    "user_id": user_id,
                    "period_days": days,
                    "total_sessions": 0,
                    "average_session_duration": 0.0,
                    "total_meetings": 0,
                    "total_translations": 0,
                    "total_voice_synthesis": 0,
                    "engagement_score": 0.0,
                    "retention_rate": 0.0,
                    "last_activity": user.last_login_at
                }
                
                # Get meeting data
                meetings_result = await session.execute(
                    select(Room).where(
                        and_(
                            Room.created_by == user_id,
                            Room.created_at >= datetime.utcnow() - timedelta(days=days)
                        )
                    )
                )
                meetings = meetings_result.scalars().all()
                engagement_metrics["total_meetings"] = len(meetings)
                
                # Get API call data
                api_calls_result = await session.execute(
                    select(APICall).where(
                        and_(
                            APICall.user_id == user_id,
                            APICall.timestamp >= datetime.utcnow() - timedelta(days=days)
                        )
                    )
                )
                api_calls = api_calls_result.scalars().all()
                engagement_metrics["total_translations"] = len([call for call in api_calls if "translate" in call.endpoint])
                engagement_metrics["total_voice_synthesis"] = len([call for call in api_calls if "voice" in call.endpoint])
                
                # Calculate engagement score
                engagement_metrics["engagement_score"] = self._calculate_engagement_score(engagement_metrics)
                
                return engagement_metrics
                
        except Exception as e:
            logger.error(f"Failed to get user engagement metrics: {e}")
            return {"error": "Failed to get engagement metrics"}
    
    def _calculate_engagement_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate user engagement score"""
        # Weighted scoring based on different activities
        weights = {
            "meetings": 0.3,
            "translations": 0.2,
            "voice_synthesis": 0.2,
            "session_duration": 0.2,
            "frequency": 0.1
        }
        
        score = 0.0
        
        # Meeting score (0-1)
        meeting_score = min(1.0, metrics["total_meetings"] / 10)  # 10 meetings = max score
        score += meeting_score * weights["meetings"]
        
        # Translation score (0-1)
        translation_score = min(1.0, metrics["total_translations"] / 100)  # 100 translations = max score
        score += translation_score * weights["translations"]
        
        # Voice synthesis score (0-1)
        voice_score = min(1.0, metrics["total_voice_synthesis"] / 50)  # 50 voice synthesis = max score
        score += voice_score * weights["voice_synthesis"]
        
        # Session duration score (0-1)
        duration_score = min(1.0, metrics["average_session_duration"] / 3600)  # 1 hour = max score
        score += duration_score * weights["session_duration"]
        
        return min(1.0, score)
    
    async def get_revenue_metrics(self, start_date: datetime, 
                                end_date: datetime) -> Dict[str, Any]:
        """Get revenue metrics for date range"""
        try:
            async with AsyncSession(async_engine) as session:
                # Get subscription data
                subscriptions_result = await session.execute(
                    select(Subscription).where(
                        and_(
                            Subscription.created_at >= start_date,
                            Subscription.created_at <= end_date,
                            Subscription.is_active == True
                        )
                    )
                )
                subscriptions = subscriptions_result.scalars().all()
                
                # Calculate revenue metrics
                revenue_metrics = {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "total_revenue": 0.0,
                    "recurring_revenue": 0.0,
                    "new_subscriptions": 0,
                    "churned_subscriptions": 0,
                    "average_revenue_per_user": 0.0,
                    "revenue_by_tier": {},
                    "monthly_recurring_revenue": 0.0
                }
                
                # Calculate revenue by tier
                tier_revenue = {}
                for subscription in subscriptions:
                    tier = subscription.tier
                    if tier not in tier_revenue:
                        tier_revenue[tier] = 0.0
                    tier_revenue[tier] += subscription.price_per_month
                
                revenue_metrics["revenue_by_tier"] = tier_revenue
                revenue_metrics["total_revenue"] = sum(tier_revenue.values())
                revenue_metrics["new_subscriptions"] = len(subscriptions)
                
                # Calculate MRR
                revenue_metrics["monthly_recurring_revenue"] = sum(tier_revenue.values())
                
                # Calculate ARPU
                if len(subscriptions) > 0:
                    revenue_metrics["average_revenue_per_user"] = revenue_metrics["total_revenue"] / len(subscriptions)
                
                return revenue_metrics
                
        except Exception as e:
            logger.error(f"Failed to get revenue metrics: {e}")
            return {"error": "Failed to get revenue metrics"}
    
    async def get_performance_metrics(self, start_date: datetime, 
                                    end_date: datetime) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            # Get API call data for performance analysis
            async with AsyncSession(async_engine) as session:
                api_calls_result = await session.execute(
                    select(APICall).where(
                        and_(
                            APICall.timestamp >= start_date,
                            APICall.timestamp <= end_date
                        )
                    )
                )
                api_calls = api_calls_result.scalars().all()
                
                # Calculate performance metrics
                performance_metrics = {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    },
                    "total_requests": len(api_calls),
                    "average_latency": 0.0,
                    "p95_latency": 0.0,
                    "p99_latency": 0.0,
                    "error_rate": 0.0,
                    "uptime": 0.0,
                    "throughput": 0.0,
                    "latency_by_endpoint": {},
                    "error_by_endpoint": {}
                }
                
                if api_calls:
                    # Calculate latency metrics
                    latencies = [call.processing_time for call in api_calls if call.processing_time]
                    if latencies:
                        performance_metrics["average_latency"] = np.mean(latencies)
                        performance_metrics["p95_latency"] = np.percentile(latencies, 95)
                        performance_metrics["p99_latency"] = np.percentile(latencies, 99)
                    
                    # Calculate error rate
                    error_count = len([call for call in api_calls if call.response_data and "error" in call.response_data])
                    performance_metrics["error_rate"] = error_count / len(api_calls)
                    
                    # Calculate throughput (requests per second)
                    duration_seconds = (end_date - start_date).total_seconds()
                    performance_metrics["throughput"] = len(api_calls) / duration_seconds
                    
                    # Calculate uptime (assuming 99.9% target)
                    performance_metrics["uptime"] = 1.0 - performance_metrics["error_rate"]
                    
                    # Group by endpoint
                    endpoint_stats = {}
                    for call in api_calls:
                        endpoint = call.endpoint
                        if endpoint not in endpoint_stats:
                            endpoint_stats[endpoint] = {
                                "count": 0,
                                "total_latency": 0.0,
                                "errors": 0
                            }
                        
                        endpoint_stats[endpoint]["count"] += 1
                        if call.processing_time:
                            endpoint_stats[endpoint]["total_latency"] += call.processing_time
                        if call.response_data and "error" in call.response_data:
                            endpoint_stats[endpoint]["errors"] += 1
                    
                    # Calculate latency by endpoint
                    for endpoint, stats in endpoint_stats.items():
                        if stats["count"] > 0:
                            performance_metrics["latency_by_endpoint"][endpoint] = stats["total_latency"] / stats["count"]
                            performance_metrics["error_by_endpoint"][endpoint] = stats["errors"] / stats["count"]
                
                return performance_metrics
                
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": "Failed to get performance metrics"}
    
    async def get_cohort_analysis(self, cohort_period: str = "month") -> Dict[str, Any]:
        """Get cohort analysis"""
        try:
            # This would analyze user cohorts based on signup date
            # For now, return mock data
            cohort_analysis = {
                "cohort_period": cohort_period,
                "cohorts": {
                    "2024-01": {
                        "cohort_size": 1000,
                        "retention_rates": {
                            "month_1": 0.8,
                            "month_2": 0.6,
                            "month_3": 0.5,
                            "month_6": 0.4,
                            "month_12": 0.3
                        },
                        "revenue_per_user": {
                            "month_1": 25.0,
                            "month_2": 45.0,
                            "month_3": 60.0,
                            "month_6": 85.0,
                            "month_12": 120.0
                        }
                    },
                    "2024-02": {
                        "cohort_size": 1200,
                        "retention_rates": {
                            "month_1": 0.85,
                            "month_2": 0.65,
                            "month_3": 0.55
                        },
                        "revenue_per_user": {
                            "month_1": 28.0,
                            "month_2": 48.0,
                            "month_3": 65.0
                        }
                    }
                }
            }
            
            return cohort_analysis
            
        except Exception as e:
            logger.error(f"Failed to get cohort analysis: {e}")
            return {"error": "Failed to get cohort analysis"}
    
    async def get_funnel_analysis(self, funnel_name: str) -> Dict[str, Any]:
        """Get funnel analysis"""
        try:
            # This would analyze conversion funnels
            # For now, return mock data
            funnel_analysis = {
                "funnel_name": funnel_name,
                "steps": [
                    "signup",
                    "email_verification",
                    "voice_clone_creation",
                    "first_meeting",
                    "subscription"
                ],
                "conversion_rates": {
                    "signup_to_verification": 0.95,
                    "verification_to_voice_clone": 0.80,
                    "voice_clone_to_meeting": 0.70,
                    "meeting_to_subscription": 0.15
                },
                "drop_off_points": [
                    "voice_clone_to_meeting",
                    "meeting_to_subscription"
                ],
                "total_conversions": 1000,
                "overall_conversion_rate": 0.08
            }
            
            return funnel_analysis
            
        except Exception as e:
            logger.error(f"Failed to get funnel analysis: {e}")
            return {"error": "Failed to get funnel analysis"}
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.real_time_metrics.copy(),
            "user_segments": {
                segment_id: segment.user_count 
                for segment_id, segment in self.user_segments.items()
            }
        }
    
    async def _metrics_collector(self):
        """Background task to collect and process metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Collect and process metrics
                await self._process_metrics()
                
            except Exception as e:
                logger.error(f"Error in metrics collector: {e}")
    
    async def _real_time_updater(self):
        """Background task to update real-time metrics"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Update real-time metrics
                await self._update_real_time_metrics_from_db()
                
            except Exception as e:
                logger.error(f"Error in real-time updater: {e}")
    
    async def _cohort_analyzer(self):
        """Background task to analyze cohorts"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Analyze cohorts
                await self._analyze_cohorts()
                
            except Exception as e:
                logger.error(f"Error in cohort analyzer: {e}")
    
    async def _funnel_analyzer(self):
        """Background task to analyze funnels"""
        while True:
            try:
                await asyncio.sleep(1800)  # Run every 30 minutes
                
                # Analyze funnels
                await self._analyze_funnels()
                
            except Exception as e:
                logger.error(f"Error in funnel analyzer: {e}")
    
    async def _process_metrics(self):
        """Process and store metrics"""
        # This would process events and calculate metrics
        pass
    
    async def _update_real_time_metrics_from_db(self):
        """Update real-time metrics from database"""
        try:
            async with AsyncSession(async_engine) as session:
                # Update active users count
                active_users_result = await session.execute(
                    select(func.count(User.id)).where(
                        User.last_login_at >= datetime.utcnow() - timedelta(hours=1)
                    )
                )
                self.real_time_metrics["active_users"] = active_users_result.scalar()
                
                # Update active rooms count
                active_rooms_result = await session.execute(
                    select(func.count(Room.id)).where(
                        Room.is_active == True
                    )
                )
                self.real_time_metrics["active_rooms"] = active_rooms_result.scalar()
                
        except Exception as e:
            logger.warning(f"Failed to update real-time metrics: {e}")
    
    async def _analyze_cohorts(self):
        """Analyze user cohorts"""
        # This would perform cohort analysis
        pass
    
    async def _analyze_funnels(self):
        """Analyze conversion funnels"""
        # This would perform funnel analysis
        pass
    
    async def create_custom_dashboard(self, user_id: int, 
                                    dashboard_config: Dict[str, Any]) -> str:
        """Create custom analytics dashboard"""
        dashboard_id = str(uuid.uuid4())
        
        # Store dashboard configuration
        if self.redis:
            try:
                await self.redis.setex(
                    f"dashboard:{dashboard_id}",
                    86400 * 30,  # 30 days
                    json.dumps({
                        "id": dashboard_id,
                        "user_id": user_id,
                        "config": dashboard_config,
                        "created_at": datetime.utcnow().isoformat()
                    })
                )
            except Exception as e:
                logger.warning(f"Failed to store dashboard config: {e}")
        
        return dashboard_id
    
    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get dashboard data"""
        if not self.redis:
            return {"error": "Redis not available"}
        
        try:
            dashboard_data = await self.redis.get(f"dashboard:{dashboard_id}")
            if dashboard_data:
                return json.loads(dashboard_data)
            else:
                return {"error": "Dashboard not found"}
        except Exception as e:
            logger.warning(f"Failed to get dashboard data: {e}")
            return {"error": "Failed to get dashboard data"}


# Global advanced analytics service instance
advanced_analytics_service = AdvancedAnalyticsService()




