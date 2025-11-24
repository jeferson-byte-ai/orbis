"""
Gamification System
Advanced gamification features to increase user engagement and retention
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
from sqlalchemy import select, update, and_

from backend.config import settings
from backend.db.models import User
from backend.db.session import async_engine

logger = logging.getLogger(__name__)


class AchievementType(Enum):
    """Types of achievements"""
    FIRST_MEETING = "first_meeting"
    MEETING_STREAK = "meeting_streak"
    TRANSLATION_MASTER = "translation_master"
    VOICE_CLONER = "voice_cloner"
    SOCIAL_BUTTERFLY = "social_butterfly"
    LANGUAGE_LEARNER = "language_learner"
    EARLY_ADOPTER = "early_adopter"
    POWER_USER = "power_user"
    GLOBAL_CITIZEN = "global_citizen"
    TECH_SAVVY = "tech_savvy"


class BadgeRarity(Enum):
    """Badge rarity levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Achievement:
    """Achievement definition"""
    id: str
    name: str
    description: str
    type: AchievementType
    rarity: BadgeRarity
    icon: str
    points: int
    requirements: Dict[str, Any]
    rewards: Dict[str, Any]
    is_hidden: bool = False
    category: str = "general"


@dataclass
class UserAchievement:
    """User's achievement progress"""
    user_id: int
    achievement_id: str
    progress: Dict[str, Any]
    completed: bool
    completed_at: Optional[datetime]
    points_earned: int


@dataclass
class UserLevel:
    """User level system"""
    user_id: int
    level: int
    experience: int
    experience_to_next: int
    total_points: int
    badges_earned: int
    achievements_unlocked: int


@dataclass
class UserStreak:
    """User streak tracking"""
    user_id: int
    type: str  # daily_login, meeting_streak, etc.
    current_streak: int
    longest_streak: int
    last_activity: datetime
    streak_bonus: float


class GamificationSystem:
    """Advanced gamification system for user engagement"""
    
    def __init__(self):
        self.redis = None
        self.achievements = {}
        self.user_levels = {}
        self.user_streaks = {}
        self.leaderboards = {}
        
        # Achievement definitions
        self.achievement_definitions = {
            AchievementType.FIRST_MEETING: Achievement(
                id="first_meeting",
                name="First Connection",
                description="Join your first multilingual meeting",
                type=AchievementType.FIRST_MEETING,
                rarity=BadgeRarity.COMMON,
                icon="🎯",
                points=100,
                requirements={"meetings_joined": 1},
                rewards={"experience": 100, "badge": "first_meeting"}
            ),
            AchievementType.MEETING_STREAK: Achievement(
                id="meeting_streak_7",
                name="Consistent Communicator",
                description="Join meetings for 7 consecutive days",
                type=AchievementType.MEETING_STREAK,
                rarity=BadgeRarity.UNCOMMON,
                icon="🔥",
                points=500,
                requirements={"meeting_streak": 7},
                rewards={"experience": 500, "badge": "streak_7", "multiplier": 1.1}
            ),
            AchievementType.TRANSLATION_MASTER: Achievement(
                id="translation_master",
                name="Translation Master",
                description="Use translation in 100 different conversations",
                type=AchievementType.TRANSLATION_MASTER,
                rarity=BadgeRarity.RARE,
                icon="🌐",
                points=1000,
                requirements={"translations_used": 100},
                rewards={"experience": 1000, "badge": "translation_master", "unlock": "premium_voices"}
            ),
            AchievementType.VOICE_CLONER: Achievement(
                id="voice_cloner",
                name="Voice Artist",
                description="Create your first voice clone",
                type=AchievementType.VOICE_CLONER,
                rarity=BadgeRarity.UNCOMMON,
                icon="🎙️",
                points=300,
                requirements={"voice_clones_created": 1},
                rewards={"experience": 300, "badge": "voice_cloner", "credits": 50}
            ),
            AchievementType.SOCIAL_BUTTERFLY: Achievement(
                id="social_butterfly",
                name="Social Butterfly",
                description="Meet people from 10 different countries",
                type=AchievementType.SOCIAL_BUTTERFLY,
                rarity=BadgeRarity.EPIC,
                icon="🦋",
                points=2000,
                requirements={"countries_met": 10},
                rewards={"experience": 2000, "badge": "social_butterfly", "title": "Global Connector"}
            ),
            AchievementType.LANGUAGE_LEARNER: Achievement(
                id="language_learner",
                name="Polyglot",
                description="Use translation between 5 different language pairs",
                type=AchievementType.LANGUAGE_LEARNER,
                rarity=BadgeRarity.RARE,
                icon="📚",
                points=800,
                requirements={"language_pairs_used": 5},
                rewards={"experience": 800, "badge": "polyglot", "unlock": "advanced_translation"}
            ),
            AchievementType.EARLY_ADOPTER: Achievement(
                id="early_adopter",
                name="Early Adopter",
                description="Join Orbis in the first month",
                type=AchievementType.EARLY_ADOPTER,
                rarity=BadgeRarity.LEGENDARY,
                icon="⭐",
                points=5000,
                requirements={"join_date": "first_month"},
                rewards={"experience": 5000, "badge": "early_adopter", "title": "Pioneer", "lifetime_discount": 0.2}
            ),
            AchievementType.POWER_USER: Achievement(
                id="power_user",
                name="Power User",
                description="Spend 100 hours in meetings",
                type=AchievementType.POWER_USER,
                rarity=BadgeRarity.EPIC,
                icon="⚡",
                points=3000,
                requirements={"total_meeting_hours": 100},
                rewards={"experience": 3000, "badge": "power_user", "unlock": "priority_support"}
            ),
            AchievementType.GLOBAL_CITIZEN: Achievement(
                id="global_citizen",
                name="Global Citizen",
                description="Host meetings in 5 different time zones",
                type=AchievementType.GLOBAL_CITIZEN,
                rarity=BadgeRarity.RARE,
                icon="🌍",
                points=1500,
                requirements={"timezones_hosted": 5},
                rewards={"experience": 1500, "badge": "global_citizen", "unlock": "timezone_insights"}
            ),
            AchievementType.TECH_SAVVY: Achievement(
                id="tech_savvy",
                name="Tech Savvy",
                description="Use all advanced features (voice cloning, AI assistant, marketplace)",
                type=AchievementType.TECH_SAVVY,
                rarity=BadgeRarity.EPIC,
                icon="🤖",
                points=2500,
                requirements={"features_used": ["voice_cloning", "ai_assistant", "marketplace"]},
                rewards={"experience": 2500, "badge": "tech_savvy", "unlock": "beta_features"}
            )
        }
    
    async def initialize(self):
        """Initialize gamification system"""
        try:
            # Connect to Redis
            self.redis = redis.from_url(settings.redis_url)
            await self.redis.ping()
            
            # Load user data
            await self._load_user_data()
            
            # Start background tasks
            asyncio.create_task(self._achievement_checker())
            asyncio.create_task(self._leaderboard_updater())
            asyncio.create_task(self._streak_maintainer())
            
            logger.info("✅ Gamification System initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gamification System: {e}")
    
    async def _load_user_data(self):
        """Load user gamification data"""
        try:
            # This would load from database when models are properly defined
            pass
        except Exception as e:
            logger.warning(f"Failed to load user data: {e}")
    
    async def track_user_action(self, user_id: int, action: str, metadata: Dict[str, Any]):
        """Track user action for achievement progress"""
        try:
            # Update user statistics
            await self._update_user_stats(user_id, action, metadata)
            
            # Check for achievement progress
            await self._check_achievements(user_id, action, metadata)
            
            # Update streaks
            await self._update_streaks(user_id, action, metadata)
            
            # Update experience
            await self._update_experience(user_id, action, metadata)
            
        except Exception as e:
            logger.error(f"Failed to track user action: {e}")
    
    async def _update_user_stats(self, user_id: int, action: str, metadata: Dict[str, Any]):
        """Update user statistics"""
        stats_key = f"user_stats:{user_id}"
        
        if self.redis:
            try:
                # Get current stats
                current_stats = await self.redis.hgetall(stats_key)
                if not current_stats:
                    current_stats = {}
                
                # Update stats based on action
                if action == "meeting_joined":
                    current_stats["meetings_joined"] = str(int(current_stats.get("meetings_joined", 0)) + 1)
                    current_stats["last_meeting"] = datetime.utcnow().isoformat()
                
                elif action == "translation_used":
                    current_stats["translations_used"] = str(int(current_stats.get("translations_used", 0)) + 1)
                    language_pair = f"{metadata.get('source')}-{metadata.get('target')}"
                    current_stats[f"lang_pair_{language_pair}"] = str(int(current_stats.get(f"lang_pair_{language_pair}", 0)) + 1)
                
                elif action == "voice_clone_created":
                    current_stats["voice_clones_created"] = str(int(current_stats.get("voice_clones_created", 0)) + 1)
                
                elif action == "meeting_hosted":
                    current_stats["meetings_hosted"] = str(int(current_stats.get("meetings_hosted", 0)) + 1)
                    timezone = metadata.get("timezone", "unknown")
                    current_stats[f"timezone_{timezone}"] = str(int(current_stats.get(f"timezone_{timezone}", 0)) + 1)
                
                # Save updated stats
                await self.redis.hset(stats_key, current_stats)
                await self.redis.expire(stats_key, 86400 * 365)  # 1 year
                
            except Exception as e:
                logger.warning(f"Failed to update user stats: {e}")
    
    async def _check_achievements(self, user_id: int, action: str, metadata: Dict[str, Any]):
        """Check if user has earned any achievements"""
        try:
            # Get user stats
            stats_key = f"user_stats:{user_id}"
            user_stats = {}
            
            if self.redis:
                user_stats = await self.redis.hgetall(stats_key)
            
            # Check each achievement
            for achievement_id, achievement in self.achievement_definitions.items():
                if await self._is_achievement_earned(user_id, achievement, user_stats):
                    await self._award_achievement(user_id, achievement)
        
        except Exception as e:
            logger.error(f"Failed to check achievements: {e}")
    
    async def _is_achievement_earned(self, user_id: int, achievement: Achievement, user_stats: Dict[str, str]) -> bool:
        """Check if user has earned a specific achievement"""
        try:
            # Check if already earned
            earned_key = f"achievement_earned:{user_id}:{achievement.id}"
            if self.redis and await self.redis.exists(earned_key):
                return False
            
            # Check requirements
            requirements = achievement.requirements
            
            if achievement.type == AchievementType.FIRST_MEETING:
                return int(user_stats.get("meetings_joined", 0)) >= 1
            
            elif achievement.type == AchievementType.MEETING_STREAK:
                streak_key = f"{user_id}_meeting_streak"
                streak = self.user_streaks.get(streak_key)
                return streak and streak.current_streak >= 7
            
            elif achievement.type == AchievementType.TRANSLATION_MASTER:
                return int(user_stats.get("translations_used", 0)) >= 100
            
            elif achievement.type == AchievementType.VOICE_CLONER:
                return int(user_stats.get("voice_clones_created", 0)) >= 1
            
            elif achievement.type == AchievementType.SOCIAL_BUTTERFLY:
                # Count unique countries from meetings
                countries = set()
                for key, value in user_stats.items():
                    if key.startswith("country_"):
                        countries.add(key.replace("country_", ""))
                return len(countries) >= 10
            
            elif achievement.type == AchievementType.LANGUAGE_LEARNER:
                # Count unique language pairs
                pairs = set()
                for key, value in user_stats.items():
                    if key.startswith("lang_pair_"):
                        pairs.add(key.replace("lang_pair_", ""))
                return len(pairs) >= 5
            
            elif achievement.type == AchievementType.POWER_USER:
                total_hours = float(user_stats.get("total_meeting_hours", 0))
                return total_hours >= 100
            
            elif achievement.type == AchievementType.GLOBAL_CITIZEN:
                # Count unique timezones
                timezones = set()
                for key, value in user_stats.items():
                    if key.startswith("timezone_"):
                        timezones.add(key.replace("timezone_", ""))
                return len(timezones) >= 5
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check achievement {achievement.id}: {e}")
            return False
    
    async def _award_achievement(self, user_id: int, achievement: Achievement):
        """Award achievement to user"""
        try:
            # Mark as earned
            earned_key = f"achievement_earned:{user_id}:{achievement.id}"
            if self.redis:
                await self.redis.setex(earned_key, 86400 * 365, "1")
            
            # Award experience and rewards
            await self._award_experience(user_id, achievement.points)
            
            # Process rewards
            await self._process_rewards(user_id, achievement.rewards)
            
            # Send notification
            await self._send_achievement_notification(user_id, achievement)
            
            # Update leaderboards
            await self._update_leaderboards(user_id)
            
            logger.info(f"✅ Achievement awarded: {achievement.name} to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to award achievement: {e}")
    
    async def _award_experience(self, user_id: int, points: int):
        """Award experience points to user"""
        try:
            # Get current level
            level = self.user_levels.get(user_id)
            if not level:
                level = UserLevel(
                    user_id=user_id,
                    level=1,
                    experience=0,
                    experience_to_next=1000,
                    total_points=0,
                    badges_earned=0,
                    achievements_unlocked=0
                )
                self.user_levels[user_id] = level
            
            # Add experience
            level.experience += points
            level.total_points += points
            
            # Check for level up
            while level.experience >= level.experience_to_next:
                level.experience -= level.experience_to_next
                level.level += 1
                level.experience_to_next = int(level.experience_to_next * 1.2)  # Exponential growth
                
                # Send level up notification
                await self._send_level_up_notification(user_id, level.level)
            
            # Save to database
            await self._save_user_level(level)
            
        except Exception as e:
            logger.error(f"Failed to award experience: {e}")
    
    async def _process_rewards(self, user_id: int, rewards: Dict[str, Any]):
        """Process achievement rewards"""
        try:
            # Process different types of rewards
            if "credits" in rewards:
                await self._award_credits(user_id, rewards["credits"])
            
            if "unlock" in rewards:
                await self._unlock_feature(user_id, rewards["unlock"])
            
            if "title" in rewards:
                await self._award_title(user_id, rewards["title"])
            
            if "multiplier" in rewards:
                await self._apply_multiplier(user_id, rewards["multiplier"])
            
        except Exception as e:
            logger.error(f"Failed to process rewards: {e}")
    
    async def _send_achievement_notification(self, user_id: int, achievement: Achievement):
        """Send achievement notification to user"""
        try:
            # This would integrate with the notification system
            notification = {
                "type": "achievement",
                "title": f"Achievement Unlocked! 🏆",
                "message": f"You earned '{achievement.name}' - {achievement.description}",
                "icon": achievement.icon,
                "points": achievement.points,
                "rarity": achievement.rarity.value
            }
            
            # Send via WebSocket or push notification
            logger.info(f"Achievement notification sent to user {user_id}: {achievement.name}")
            
        except Exception as e:
            logger.error(f"Failed to send achievement notification: {e}")
    
    async def _send_level_up_notification(self, user_id: int, new_level: int):
        """Send level up notification to user"""
        try:
            notification = {
                "type": "level_up",
                "title": f"Level Up! 🎉",
                "message": f"Congratulations! You've reached level {new_level}!",
                "level": new_level
            }
            
            logger.info(f"Level up notification sent to user {user_id}: Level {new_level}")
            
        except Exception as e:
            logger.error(f"Failed to send level up notification: {e}")
    
    async def _update_streaks(self, user_id: int, action: str, metadata: Dict[str, Any]):
        """Update user streaks"""
        try:
            current_time = datetime.utcnow()
            
            if action == "meeting_joined":
                streak_key = f"{user_id}_meeting_streak"
                streak = self.user_streaks.get(streak_key)
                
                if not streak:
                    streak = UserStreak(
                        user_id=user_id,
                        type="meeting_streak",
                        current_streak=0,
                        longest_streak=0,
                        last_activity=current_time,
                        streak_bonus=1.0
                    )
                    self.user_streaks[streak_key] = streak
                
                # Check if streak should continue
                time_diff = current_time - streak.last_activity
                if time_diff.days <= 1:  # Within 24 hours
                    streak.current_streak += 1
                else:
                    streak.current_streak = 1
                
                # Update longest streak
                if streak.current_streak > streak.longest_streak:
                    streak.longest_streak = streak.current_streak
                
                streak.last_activity = current_time
                
                # Calculate streak bonus
                if streak.current_streak >= 7:
                    streak.streak_bonus = 1.5
                elif streak.current_streak >= 3:
                    streak.streak_bonus = 1.2
                else:
                    streak.streak_bonus = 1.0
                
                # Save streak
                await self._save_user_streak(streak)
        
        except Exception as e:
            logger.error(f"Failed to update streaks: {e}")
    
    async def _update_experience(self, user_id: int, action: str, metadata: Dict[str, Any]):
        """Update user experience based on action"""
        try:
            # Base experience for different actions
            experience_map = {
                "meeting_joined": 50,
                "meeting_hosted": 100,
                "translation_used": 10,
                "voice_clone_created": 200,
                "achievement_earned": 0,  # Handled separately
                "daily_login": 25
            }
            
            base_experience = experience_map.get(action, 10)
            
            # Apply streak bonus
            streak_key = f"{user_id}_meeting_streak"
            streak = self.user_streaks.get(streak_key)
            if streak:
                base_experience = int(base_experience * streak.streak_bonus)
            
            # Award experience
            await self._award_experience(user_id, base_experience)
            
        except Exception as e:
            logger.error(f"Failed to update experience: {e}")
    
    async def _update_leaderboards(self, user_id: int):
        """Update leaderboards"""
        try:
            if not self.redis:
                return
            
            level = self.user_levels.get(user_id)
            if not level:
                return
            
            # Update various leaderboards
            await self.redis.zadd("leaderboard:experience", {str(user_id): level.total_points})
            await self.redis.zadd("leaderboard:level", {str(user_id): level.level})
            await self.redis.zadd("leaderboard:achievements", {str(user_id): level.achievements_unlocked})
            
        except Exception as e:
            logger.error(f"Failed to update leaderboards: {e}")
    
    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user gamification profile"""
        try:
            level = self.user_levels.get(user_id)
            if not level:
                level = UserLevel(
                    user_id=user_id,
                    level=1,
                    experience=0,
                    experience_to_next=1000,
                    total_points=0,
                    badges_earned=0,
                    achievements_unlocked=0
                )
            
            # Get user stats
            stats_key = f"user_stats:{user_id}"
            user_stats = {}
            if self.redis:
                user_stats = await self.redis.hgetall(stats_key)
            
            # Get earned achievements
            earned_achievements = []
            for achievement_id, achievement in self.achievement_definitions.items():
                earned_key = f"achievement_earned:{user_id}:{achievement.id}"
                if self.redis and await self.redis.exists(earned_key):
                    earned_achievements.append({
                        "id": achievement.id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "icon": achievement.icon,
                        "rarity": achievement.rarity.value,
                        "points": achievement.points
                    })
            
            # Get streaks
            streaks = {}
            for key, streak in self.user_streaks.items():
                if key.startswith(f"{user_id}_"):
                    streak_type = key.replace(f"{user_id}_", "")
                    streaks[streak_type] = {
                        "current": streak.current_streak,
                        "longest": streak.longest_streak,
                        "bonus": streak.streak_bonus
                    }
            
            return {
                "user_id": user_id,
                "level": level.level,
                "experience": level.experience,
                "experience_to_next": level.experience_to_next,
                "total_points": level.total_points,
                "badges_earned": level.badges_earned,
                "achievements_unlocked": level.achievements_unlocked,
                "stats": user_stats,
                "achievements": earned_achievements,
                "streaks": streaks,
                "rank": await self._get_user_rank(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return {}
    
    async def _get_user_rank(self, user_id: int) -> Dict[str, int]:
        """Get user's rank in various leaderboards"""
        try:
            if not self.redis:
                return {}
            
            ranks = {}
            
            # Experience rank
            exp_rank = await self.redis.zrevrank("leaderboard:experience", str(user_id))
            ranks["experience"] = exp_rank + 1 if exp_rank is not None else 0
            
            # Level rank
            level_rank = await self.redis.zrevrank("leaderboard:level", str(user_id))
            ranks["level"] = level_rank + 1 if level_rank is not None else 0
            
            # Achievement rank
            ach_rank = await self.redis.zrevrank("leaderboard:achievements", str(user_id))
            ranks["achievements"] = ach_rank + 1 if ach_rank is not None else 0
            
            return ranks
            
        except Exception as e:
            logger.error(f"Failed to get user rank: {e}")
            return {}
    
    async def _save_user_level(self, level: UserLevel):
        """Save user level to database"""
        try:
            async with AsyncSession(async_engine) as session:
                # This would save to UserLevel table
                # For now, just update in memory
                self.user_levels[level.user_id] = level
        except Exception as e:
            logger.error(f"Failed to save user level: {e}")
    
    async def _save_user_streak(self, streak: UserStreak):
        """Save user streak to database"""
        try:
            async with AsyncSession(async_engine) as session:
                # This would save to UserStreak table
                # For now, just update in memory
                key = f"{streak.user_id}_{streak.type}"
                self.user_streaks[key] = streak
        except Exception as e:
            logger.error(f"Failed to save user streak: {e}")
    
    async def _achievement_checker(self):
        """Background task to check for achievements"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                # This would check for time-based achievements
                pass
            except Exception as e:
                logger.error(f"Error in achievement checker: {e}")
    
    async def _leaderboard_updater(self):
        """Background task to update leaderboards"""
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                # This would update leaderboards
                pass
            except Exception as e:
                logger.error(f"Error in leaderboard updater: {e}")
    
    async def _streak_maintainer(self):
        """Background task to maintain streaks"""
        while True:
            try:
                await asyncio.sleep(86400)  # Check daily
                # This would check and reset expired streaks
                pass
            except Exception as e:
                logger.error(f"Error in streak maintainer: {e}")


# Global gamification system instance
gamification_system = GamificationSystem()
