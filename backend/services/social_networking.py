"""
Social Networking Service
Advanced social features for community building and networking
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from backend.config import settings
from backend.db.models import User
from backend.db.session import async_engine

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Types of social connections"""
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    MENTOR = "mentor"
    MENTEE = "mentee"
    BUSINESS_PARTNER = "business_partner"
    LANGUAGE_PARTNER = "language_partner"


class PostType(Enum):
    """Types of social posts"""
    MEETING_SUMMARY = "meeting_summary"
    ACHIEVEMENT = "achievement"
    LANGUAGE_LEARNING = "language_learning"
    BUSINESS_UPDATE = "business_update"
    THOUGHT_LEADERSHIP = "thought_leadership"
    COMMUNITY_EVENT = "community_event"


class EventType(Enum):
    """Types of social events"""
    NETWORKING = "networking"
    LANGUAGE_EXCHANGE = "language_exchange"
    WORKSHOP = "workshop"
    CONFERENCE = "conference"
    MEETUP = "meetup"
    VIRTUAL_HANGOUT = "virtual_hangout"


@dataclass
class SocialConnection:
    """Social connection between users"""
    id: str
    user_id: int
    connected_user_id: int
    connection_type: ConnectionType
    status: str  # pending, accepted, blocked
    created_at: datetime
    accepted_at: Optional[datetime]
    mutual_connections: int
    shared_interests: List[str]
    interaction_score: float


@dataclass
class SocialPost:
    """Social media style post"""
    id: str
    user_id: int
    type: PostType
    title: str
    content: str
    media_urls: List[str]
    hashtags: List[str]
    mentions: List[int]
    likes: int
    comments: int
    shares: int
    views: int
    created_at: datetime
    updated_at: datetime
    is_public: bool
    language: str


@dataclass
class SocialEvent:
    """Social event or meetup"""
    id: str
    organizer_id: int
    title: str
    description: str
    event_type: EventType
    start_time: datetime
    end_time: datetime
    max_participants: int
    current_participants: int
    languages: List[str]
    topics: List[str]
    location: str
    is_virtual: bool
    meeting_room_id: Optional[str]
    registration_required: bool
    created_at: datetime
    status: str  # upcoming, ongoing, completed, cancelled


@dataclass
class UserProfile:
    """Extended user profile for social features"""
    user_id: int
    bio: str
    location: str
    timezone: str
    languages: List[str]
    interests: List[str]
    skills: List[str]
    company: str
    job_title: str
    industry: str
    experience_level: str
    availability: Dict[str, Any]
    social_links: Dict[str, str]
    profile_visibility: str  # public, connections, private
    last_active: datetime
    total_connections: int
    total_posts: int
    total_events_attended: int
    reputation_score: float


class SocialNetworkingService:
    """Advanced social networking service for community building"""
    
    def __init__(self):
        self.redis = None
        self.connections = {}
        self.posts = {}
        self.events = {}
        self.user_profiles = {}
        self.feed_cache = {}
        
        # Social algorithms
        self.connection_algorithm = ConnectionRecommendationAlgorithm()
        self.feed_algorithm = FeedAlgorithm()
        self.event_matching_algorithm = EventMatchingAlgorithm()
    
    async def initialize(self):
        """Initialize social networking service"""
        try:
            # Connect to Redis
            self.redis = redis.from_url(settings.redis_url)
            await self.redis.ping()
            
            # Load social data
            await self._load_social_data()
            
            # Start background tasks
            asyncio.create_task(self._feed_updater())
            asyncio.create_task(self._connection_suggester())
            asyncio.create_task(self._event_matcher())
            
            logger.info("✅ Social Networking Service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Social Networking Service: {e}")
    
    async def _load_social_data(self):
        """Load social networking data"""
        try:
            # This would load from database when models are properly defined
            pass
        except Exception as e:
            logger.warning(f"Failed to load social data: {e}")
    
    async def create_user_profile(self, user_id: int, profile_data: Dict[str, Any]) -> UserProfile:
        """Create or update user profile"""
        try:
            profile = UserProfile(
                user_id=user_id,
                bio=profile_data.get("bio", ""),
                location=profile_data.get("location", ""),
                timezone=profile_data.get("timezone", "UTC"),
                languages=profile_data.get("languages", []),
                interests=profile_data.get("interests", []),
                skills=profile_data.get("skills", []),
                company=profile_data.get("company", ""),
                job_title=profile_data.get("job_title", ""),
                industry=profile_data.get("industry", ""),
                experience_level=profile_data.get("experience_level", "beginner"),
                availability=profile_data.get("availability", {}),
                social_links=profile_data.get("social_links", {}),
                profile_visibility=profile_data.get("profile_visibility", "public"),
                last_active=datetime.utcnow(),
                total_connections=0,
                total_posts=0,
                total_events_attended=0,
                reputation_score=0.0
            )
            
            # Store profile
            self.user_profiles[user_id] = profile
            await self._store_user_profile(profile)
            
            # Update recommendations
            await self._update_connection_recommendations(user_id)
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to create user profile: {e}")
            raise
    
    async def send_connection_request(self, user_id: int, target_user_id: int, 
                                    connection_type: ConnectionType, message: str = "") -> str:
        """Send connection request"""
        try:
            connection_id = str(uuid.uuid4())
            
            connection = SocialConnection(
                id=connection_id,
                user_id=user_id,
                connected_user_id=target_user_id,
                connection_type=connection_type,
                status="pending",
                created_at=datetime.utcnow(),
                accepted_at=None,
                mutual_connections=0,
                shared_interests=[],
                interaction_score=0.0
            )
            
            # Store connection
            self.connections[connection_id] = connection
            await self._store_connection(connection)
            
            # Send notification
            await self._send_connection_notification(target_user_id, user_id, connection_type, message)
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to send connection request: {e}")
            raise
    
    async def accept_connection_request(self, connection_id: str, user_id: int) -> bool:
        """Accept connection request"""
        try:
            connection = self.connections.get(connection_id)
            if not connection or connection.connected_user_id != user_id:
                return False
            
            # Update connection status
            connection.status = "accepted"
            connection.accepted_at = datetime.utcnow()
            
            # Calculate mutual connections and shared interests
            await self._update_connection_metadata(connection)
            
            # Update user profiles
            await self._update_connection_counts(connection.user_id, connection.connected_user_id)
            
            # Store updated connection
            await self._store_connection(connection)
            
            # Send acceptance notification
            await self._send_connection_accepted_notification(connection.user_id, connection.connected_user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to accept connection request: {e}")
            return False
    
    async def create_social_post(self, user_id: int, post_data: Dict[str, Any]) -> str:
        """Create social media style post"""
        try:
            post_id = str(uuid.uuid4())
            
            post = SocialPost(
                id=post_id,
                user_id=user_id,
                type=PostType(post_data.get("type", "meeting_summary")),
                title=post_data.get("title", ""),
                content=post_data.get("content", ""),
                media_urls=post_data.get("media_urls", []),
                hashtags=post_data.get("hashtags", []),
                mentions=post_data.get("mentions", []),
                likes=0,
                comments=0,
                shares=0,
                views=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_public=post_data.get("is_public", True),
                language=post_data.get("language", "en")
            )
            
            # Store post
            self.posts[post_id] = post
            await self._store_post(post)
            
            # Update user profile
            if user_id in self.user_profiles:
                self.user_profiles[user_id].total_posts += 1
            
            # Update feed cache
            await self._update_feed_cache(user_id, post)
            
            # Send notifications to mentioned users
            for mentioned_user in post.mentions:
                await self._send_mention_notification(mentioned_user, user_id, post)
            
            return post_id
            
        except Exception as e:
            logger.error(f"Failed to create social post: {e}")
            raise
    
    async def like_post(self, post_id: str, user_id: int) -> bool:
        """Like a social post"""
        try:
            post = self.posts.get(post_id)
            if not post:
                return False
            
            # Check if already liked
            like_key = f"post_like:{post_id}:{user_id}"
            if self.redis and await self.redis.exists(like_key):
                return False
            
            # Add like
            post.likes += 1
            
            # Store like
            if self.redis:
                await self.redis.setex(like_key, 86400 * 365, "1")  # 1 year
            
            # Update post
            await self._store_post(post)
            
            # Send notification to post author
            if post.user_id != user_id:
                await self._send_like_notification(post.user_id, user_id, post)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to like post: {e}")
            return False
    
    async def comment_on_post(self, post_id: str, user_id: int, comment: str) -> str:
        """Comment on a social post"""
        try:
            post = self.posts.get(post_id)
            if not post:
                return ""
            
            comment_id = str(uuid.uuid4())
            
            # Store comment
            comment_data = {
                "id": comment_id,
                "post_id": post_id,
                "user_id": user_id,
                "comment": comment,
                "created_at": datetime.utcnow().isoformat()
            }
            
            if self.redis:
                await self.redis.lpush(f"post_comments:{post_id}", json.dumps(comment_data))
            
            # Update post
            post.comments += 1
            await self._store_post(post)
            
            # Send notification to post author
            if post.user_id != user_id:
                await self._send_comment_notification(post.user_id, user_id, post, comment)
            
            return comment_id
            
        except Exception as e:
            logger.error(f"Failed to comment on post: {e}")
            return ""
    
    async def create_social_event(self, organizer_id: int, event_data: Dict[str, Any]) -> str:
        """Create social event"""
        try:
            event_id = str(uuid.uuid4())
            
            event = SocialEvent(
                id=event_id,
                organizer_id=organizer_id,
                title=event_data.get("title", ""),
                description=event_data.get("description", ""),
                event_type=EventType(event_data.get("type", "networking")),
                start_time=datetime.fromisoformat(event_data.get("start_time")),
                end_time=datetime.fromisoformat(event_data.get("end_time")),
                max_participants=event_data.get("max_participants", 50),
                current_participants=0,
                languages=event_data.get("languages", []),
                topics=event_data.get("topics", []),
                location=event_data.get("location", ""),
                is_virtual=event_data.get("is_virtual", True),
                meeting_room_id=event_data.get("meeting_room_id"),
                registration_required=event_data.get("registration_required", True),
                created_at=datetime.utcnow(),
                status="upcoming"
            )
            
            # Store event
            self.events[event_id] = event
            await self._store_event(event)
            
            # Create social post for event
            await self.create_social_post(organizer_id, {
                "type": "community_event",
                "title": f"New Event: {event.title}",
                "content": event.description,
                "hashtags": event.topics + ["event", "networking"],
                "is_public": True
            })
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to create social event: {e}")
            raise
    
    async def join_event(self, event_id: str, user_id: int) -> bool:
        """Join a social event"""
        try:
            event = self.events.get(event_id)
            if not event:
                return False
            
            # Check if event is full
            if event.current_participants >= event.max_participants:
                return False
            
            # Check if already joined
            join_key = f"event_join:{event_id}:{user_id}"
            if self.redis and await self.redis.exists(join_key):
                return False
            
            # Add participant
            event.current_participants += 1
            
            # Store join
            if self.redis:
                await self.redis.setex(join_key, 86400 * 30, "1")  # 30 days
            
            # Update event
            await self._store_event(event)
            
            # Update user profile
            if user_id in self.user_profiles:
                self.user_profiles[user_id].total_events_attended += 1
            
            # Send notification to organizer
            if event.organizer_id != user_id:
                await self._send_event_join_notification(event.organizer_id, user_id, event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to join event: {e}")
            return False
    
    async def get_user_feed(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get personalized user feed"""
        try:
            # Check cache first
            cache_key = f"user_feed:{user_id}:{limit}:{offset}"
            if self.redis:
                cached_feed = await self.redis.get(cache_key)
                if cached_feed:
                    return json.loads(cached_feed)
            
            # Generate feed using algorithm
            feed = await self.feed_algorithm.generate_feed(user_id, limit, offset)
            
            # Cache feed
            if self.redis:
                await self.redis.setex(cache_key, 300, json.dumps(feed, default=str))  # 5 minutes
            
            return feed
            
        except Exception as e:
            logger.error(f"Failed to get user feed: {e}")
            return []
    
    async def get_connection_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get connection recommendations"""
        try:
            # Check cache first
            cache_key = f"connection_recommendations:{user_id}:{limit}"
            if self.redis:
                cached_recommendations = await self.redis.get(cache_key)
                if cached_recommendations:
                    return json.loads(cached_recommendations)
            
            # Generate recommendations using algorithm
            recommendations = await self.connection_algorithm.generate_recommendations(user_id, limit)
            
            # Cache recommendations
            if self.redis:
                await self.redis.setex(cache_key, 3600, json.dumps(recommendations, default=str))  # 1 hour
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get connection recommendations: {e}")
            return []
    
    async def get_event_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get event recommendations"""
        try:
            # Check cache first
            cache_key = f"event_recommendations:{user_id}:{limit}"
            if self.redis and await self.redis.exists(cache_key):
                cached_recommendations = await self.redis.get(cache_key)
                if cached_recommendations:
                    return json.loads(cached_recommendations)
            
            # Generate recommendations using algorithm
            recommendations = await self.event_matching_algorithm.generate_recommendations(user_id, limit)
            
            # Cache recommendations
            if self.redis:
                await self.redis.setex(cache_key, 1800, json.dumps(recommendations, default=str))  # 30 minutes
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get event recommendations: {e}")
            return []
    
    async def search_users(self, query: str, filters: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
        """Search for users"""
        try:
            results = []
            
            for user_id, profile in self.user_profiles.items():
                # Check if profile matches search criteria
                if self._matches_search_criteria(profile, query, filters):
                    results.append({
                        "user_id": user_id,
                        "bio": profile.bio,
                        "location": profile.location,
                        "languages": profile.languages,
                        "interests": profile.interests,
                        "skills": profile.skills,
                        "company": profile.company,
                        "job_title": profile.job_title,
                        "reputation_score": profile.reputation_score
                    })
            
            # Sort by relevance
            results.sort(key=lambda x: x["reputation_score"], reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search users: {e}")
            return []
    
    def _matches_search_criteria(self, profile: UserProfile, query: str, filters: Dict[str, Any]) -> bool:
        """Check if profile matches search criteria"""
        query_lower = query.lower()
        
        # Text search
        if query:
            searchable_text = f"{profile.bio} {profile.company} {profile.job_title} {' '.join(profile.skills)} {' '.join(profile.interests)}"
            if query_lower not in searchable_text.lower():
                return False
        
        # Filter by location
        if "location" in filters and profile.location != filters["location"]:
            return False
        
        # Filter by languages
        if "languages" in filters:
            if not any(lang in profile.languages for lang in filters["languages"]):
                return False
        
        # Filter by skills
        if "skills" in filters:
            if not any(skill in profile.skills for skill in filters["skills"]):
                return False
        
        # Filter by industry
        if "industry" in filters and profile.industry != filters["industry"]:
            return False
        
        return True
    
    async def _update_connection_metadata(self, connection: SocialConnection):
        """Update connection metadata"""
        try:
            # Calculate mutual connections
            user_connections = [c for c in self.connections.values() 
                              if c.user_id == connection.user_id and c.status == "accepted"]
            target_connections = [c for c in self.connections.values() 
                                if c.user_id == connection.connected_user_id and c.status == "accepted"]
            
            mutual_connections = len(set(c.connected_user_id for c in user_connections) & 
                                   set(c.connected_user_id for c in target_connections))
            connection.mutual_connections = mutual_connections
            
            # Calculate shared interests
            user_profile = self.user_profiles.get(connection.user_id)
            target_profile = self.user_profiles.get(connection.connected_user_id)
            
            if user_profile and target_profile:
                shared_interests = list(set(user_profile.interests) & set(target_profile.interests))
                connection.shared_interests = shared_interests
            
        except Exception as e:
            logger.error(f"Failed to update connection metadata: {e}")
    
    async def _update_connection_counts(self, user_id: int, connected_user_id: int):
        """Update connection counts in user profiles"""
        try:
            if user_id in self.user_profiles:
                self.user_profiles[user_id].total_connections += 1
            
            if connected_user_id in self.user_profiles:
                self.user_profiles[connected_user_id].total_connections += 1
            
        except Exception as e:
            logger.error(f"Failed to update connection counts: {e}")
    
    async def _update_feed_cache(self, user_id: int, post: SocialPost):
        """Update feed cache for user's connections"""
        try:
            # Get user's connections
            user_connections = [c for c in self.connections.values() 
                              if c.connected_user_id == user_id and c.status == "accepted"]
            
            # Update feed cache for each connection
            for connection in user_connections:
                cache_key = f"user_feed:{connection.user_id}"
                if self.redis:
                    # Add post to feed cache
                    await self.redis.lpush(cache_key, json.dumps({
                        "post_id": post.id,
                        "user_id": post.user_id,
                        "type": post.type.value,
                        "title": post.title,
                        "content": post.content,
                        "created_at": post.created_at.isoformat(),
                        "likes": post.likes,
                        "comments": post.comments
                    }))
                    
                    # Keep only recent posts
                    await self.redis.ltrim(cache_key, 0, 99)
        
        except Exception as e:
            logger.error(f"Failed to update feed cache: {e}")
    
    async def _update_connection_recommendations(self, user_id: int):
        """Update connection recommendations for user"""
        try:
            # Clear existing recommendations cache
            cache_key = f"connection_recommendations:{user_id}"
            if self.redis:
                await self.redis.delete(cache_key)
            
            # Generate new recommendations
            await self.connection_algorithm.generate_recommendations(user_id, 10)
            
        except Exception as e:
            logger.error(f"Failed to update connection recommendations: {e}")
    
    async def _store_user_profile(self, profile: UserProfile):
        """Store user profile in database"""
        try:
            async with AsyncSession(async_engine) as session:
                # This would store in UserProfile table
                pass
        except Exception as e:
            logger.error(f"Failed to store user profile: {e}")
    
    async def _store_connection(self, connection: SocialConnection):
        """Store connection in database"""
        try:
            async with AsyncSession(async_engine) as session:
                # This would store in SocialConnection table
                pass
        except Exception as e:
            logger.error(f"Failed to store connection: {e}")
    
    async def _store_post(self, post: SocialPost):
        """Store post in database"""
        try:
            async with AsyncSession(async_engine) as session:
                # This would store in SocialPost table
                pass
        except Exception as e:
            logger.error(f"Failed to store post: {e}")
    
    async def _store_event(self, event: SocialEvent):
        """Store event in database"""
        try:
            async with AsyncSession(async_engine) as session:
                # This would store in SocialEvent table
                pass
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
    
    async def _send_connection_notification(self, target_user_id: int, user_id: int, 
                                          connection_type: ConnectionType, message: str):
        """Send connection request notification"""
        # This would integrate with notification system
        pass
    
    async def _send_connection_accepted_notification(self, user_id: int, connected_user_id: int):
        """Send connection accepted notification"""
        # This would integrate with notification system
        pass
    
    async def _send_mention_notification(self, mentioned_user: int, user_id: int, post: SocialPost):
        """Send mention notification"""
        # This would integrate with notification system
        pass
    
    async def _send_like_notification(self, post_author: int, user_id: int, post: SocialPost):
        """Send like notification"""
        # This would integrate with notification system
        pass
    
    async def _send_comment_notification(self, post_author: int, user_id: int, post: SocialPost, comment: str):
        """Send comment notification"""
        # This would integrate with notification system
        pass
    
    async def _send_event_join_notification(self, organizer_id: int, user_id: int, event: SocialEvent):
        """Send event join notification"""
        # This would integrate with notification system
        pass
    
    async def _feed_updater(self):
        """Background task to update feeds"""
        while True:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                # This would update feed caches
                pass
            except Exception as e:
                logger.error(f"Error in feed updater: {e}")
    
    async def _connection_suggester(self):
        """Background task to suggest connections"""
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                # This would update connection recommendations
                pass
            except Exception as e:
                logger.error(f"Error in connection suggester: {e}")
    
    async def _event_matcher(self):
        """Background task to match events"""
        while True:
            try:
                await asyncio.sleep(1800)  # Update every 30 minutes
                # This would update event recommendations
                pass
            except Exception as e:
                logger.error(f"Error in event matcher: {e}")


class ConnectionRecommendationAlgorithm:
    """Algorithm for recommending connections"""
    
    async def generate_recommendations(self, user_id: int, limit: int) -> List[Dict[str, Any]]:
        """Generate connection recommendations"""
        # This would implement sophisticated recommendation algorithm
        # For now, return mock recommendations
        return []


class FeedAlgorithm:
    """Algorithm for generating personalized feeds"""
    
    async def generate_feed(self, user_id: int, limit: int, offset: int) -> List[Dict[str, Any]]:
        """Generate personalized feed"""
        # This would implement sophisticated feed algorithm
        # For now, return mock feed
        return []


class EventMatchingAlgorithm:
    """Algorithm for matching events to users"""
    
    async def generate_recommendations(self, user_id: int, limit: int) -> List[Dict[str, Any]]:
        """Generate event recommendations"""
        # This would implement sophisticated event matching algorithm
        # For now, return mock recommendations
        return []


# Global social networking service instance
social_networking_service = SocialNetworkingService()
