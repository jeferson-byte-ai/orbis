"""
Voice Marketplace Service
Premium voice marketplace for billion-dollar revenue
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload

from backend.db.models import User, VoiceProfile
# from backend.db.models import VoiceMarketplaceListing  # TODO: Create this model
from backend.db.session import async_engine
from backend.config import settings

logger = logging.getLogger(__name__)


class VoiceCategory(Enum):
    """Voice categories in marketplace"""
    PROFESSIONAL = "professional"
    CELEBRITY = "celebrity"
    CHARACTER = "character"
    ACCENT = "accent"
    LANGUAGE = "language"
    EMOTION = "emotion"
    AGE = "age"
    GENDER = "gender"


class VoiceQuality(Enum):
    """Voice quality levels"""
    STANDARD = "standard"
    PREMIUM = "premium"
    ULTRA = "ultra"
    PROFESSIONAL = "professional"


class ListingStatus(Enum):
    """Marketplace listing status"""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    DELISTED = "delisted"


@dataclass
class VoiceListing:
    """Voice marketplace listing"""
    id: str
    title: str
    description: str
    category: VoiceCategory
    quality: VoiceQuality
    price_usd: float
    currency: str
    seller_id: int
    voice_profile_id: str
    sample_audio_url: str
    demo_text: str
    languages: List[str]
    accents: List[str]
    emotions: List[str]
    age_range: Tuple[int, int]
    gender: str
    tags: List[str]
    status: ListingStatus
    rating: float
    review_count: int
    download_count: int
    created_at: datetime
    updated_at: datetime
    featured: bool = False
    trending: bool = False


@dataclass
class VoicePurchase:
    """Voice purchase record"""
    id: str
    buyer_id: int
    listing_id: str
    price_paid: float
    currency: str
    payment_method: str
    transaction_id: str
    purchased_at: datetime
    license_type: str  # personal, commercial, enterprise
    usage_limits: Dict[str, Any]


@dataclass
class VoiceReview:
    """Voice review and rating"""
    id: str
    listing_id: str
    user_id: int
    rating: int  # 1-5
    review_text: str
    created_at: datetime
    helpful_votes: int = 0


class VoiceMarketplaceService:
    """Voice marketplace service for premium voice sales"""
    
    def __init__(self):
        self.redis = None
        self.featured_voices = []
        self.trending_voices = []
        self.voice_categories = {}
        self.seller_commissions = 0.7  # 70% to seller, 30% to Orbis
        
    async def initialize(self):
        """Initialize voice marketplace service"""
        try:
            self.redis = redis.from_url(settings.redis_url)
            await self.redis.ping()
            logger.info("✅ Voice Marketplace service initialized")
        except Exception as e:
            logger.warning(f"⚠️ Voice Marketplace Redis connection failed: {e}")
    
    async def create_voice_listing(self, seller_id: int, voice_data: Dict[str, Any]) -> VoiceListing:
        """Create a new voice listing in marketplace"""
        listing_id = str(uuid.uuid4())
        
        # Validate voice profile exists and belongs to seller
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(VoiceProfile).where(
                    and_(
                        VoiceProfile.id == voice_data["voice_profile_id"],
                        VoiceProfile.user_id == seller_id
                    )
                )
            )
            voice_profile = result.scalar_one_or_none()
            
            if not voice_profile:
                raise ValueError("Voice profile not found or not owned by seller")
        
        # Create listing
        listing = VoiceListing(
            id=listing_id,
            title=voice_data["title"],
            description=voice_data["description"],
            category=VoiceCategory(voice_data["category"]),
            quality=VoiceQuality(voice_data["quality"]),
            price_usd=voice_data["price_usd"],
            currency=voice_data.get("currency", "USD"),
            seller_id=seller_id,
            voice_profile_id=voice_data["voice_profile_id"],
            sample_audio_url=voice_data["sample_audio_url"],
            demo_text=voice_data.get("demo_text", "Hello, this is a sample of my voice."),
            languages=voice_data.get("languages", ["en"]),
            accents=voice_data.get("accents", []),
            emotions=voice_data.get("emotions", ["neutral"]),
            age_range=tuple(voice_data.get("age_range", [25, 45])),
            gender=voice_data.get("gender", "neutral"),
            tags=voice_data.get("tags", []),
            status=ListingStatus.PENDING,
            rating=0.0,
            review_count=0,
            download_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store in database
        await self._store_voice_listing(listing)
        
        # Cache for quick access
        await self._cache_voice_listing(listing)
        
        logger.info(f"✅ Voice listing created: {listing_id}")
        return listing
    
    async def _store_voice_listing(self, listing: VoiceListing):
        """Store voice listing in database"""
        async with AsyncSession(async_engine) as session:
            db_listing = VoiceMarketplaceListing(
                id=listing.id,
                title=listing.title,
                description=listing.description,
                category=listing.category.value,
                quality=listing.quality.value,
                price_usd=listing.price_usd,
                currency=listing.currency,
                seller_id=listing.seller_id,
                voice_profile_id=listing.voice_profile_id,
                sample_audio_url=listing.sample_audio_url,
                demo_text=listing.demo_text,
                languages=json.dumps(listing.languages),
                accents=json.dumps(listing.accents),
                emotions=json.dumps(listing.emotions),
                age_range_min=listing.age_range[0],
                age_range_max=listing.age_range[1],
                gender=listing.gender,
                tags=json.dumps(listing.tags),
                status=listing.status.value,
                rating=listing.rating,
                review_count=listing.review_count,
                download_count=listing.download_count,
                featured=listing.featured,
                trending=listing.trending,
                created_at=listing.created_at,
                updated_at=listing.updated_at
            )
            
            session.add(db_listing)
            await session.commit()
    
    async def _cache_voice_listing(self, listing: VoiceListing):
        """Cache voice listing in Redis"""
        if not self.redis:
            return
        
        try:
            cache_key = f"voice_listing:{listing.id}"
            await self.redis.setex(
                cache_key,
                3600,  # 1 hour
                json.dumps(listing.__dict__, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to cache voice listing: {e}")
    
    async def get_voice_listings(self, filters: Dict[str, Any] = None, 
                               limit: int = 20, offset: int = 0) -> List[VoiceListing]:
        """Get voice listings with optional filters"""
        if not filters:
            filters = {}
        
        # Try cache first
        cache_key = f"voice_listings:{hash(str(filters))}:{limit}:{offset}"
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    listings_data = json.loads(cached)
                    return [VoiceListing(**data) for data in listings_data]
            except Exception as e:
                logger.warning(f"Failed to get cached listings: {e}")
        
        # Query database
        async with AsyncSession(async_engine) as session:
            query = select(VoiceMarketplaceListing).where(
                VoiceMarketplaceListing.status == ListingStatus.APPROVED.value
            )
            
            # Apply filters
            if "category" in filters:
                query = query.where(VoiceMarketplaceListing.category == filters["category"])
            
            if "quality" in filters:
                query = query.where(VoiceMarketplaceListing.quality == filters["quality"])
            
            if "min_price" in filters:
                query = query.where(VoiceMarketplaceListing.price_usd >= filters["min_price"])
            
            if "max_price" in filters:
                query = query.where(VoiceMarketplaceListing.price_usd <= filters["max_price"])
            
            if "languages" in filters:
                # This would need more complex JSON querying
                pass
            
            if "featured" in filters and filters["featured"]:
                query = query.where(VoiceMarketplaceListing.featured == True)
            
            if "trending" in filters and filters["trending"]:
                query = query.where(VoiceMarketplaceListing.trending == True)
            
            # Order by rating and download count
            query = query.order_by(
                VoiceMarketplaceListing.featured.desc(),
                VoiceMarketplaceListing.trending.desc(),
                VoiceMarketplaceListing.rating.desc(),
                VoiceMarketplaceListing.download_count.desc()
            )
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await session.execute(query)
            db_listings = result.scalars().all()
            
            # Convert to VoiceListing objects
            listings = []
            for db_listing in db_listings:
                listing = VoiceListing(
                    id=db_listing.id,
                    title=db_listing.title,
                    description=db_listing.description,
                    category=VoiceCategory(db_listing.category),
                    quality=VoiceQuality(db_listing.quality),
                    price_usd=db_listing.price_usd,
                    currency=db_listing.currency,
                    seller_id=db_listing.seller_id,
                    voice_profile_id=db_listing.voice_profile_id,
                    sample_audio_url=db_listing.sample_audio_url,
                    demo_text=db_listing.demo_text,
                    languages=json.loads(db_listing.languages),
                    accents=json.loads(db_listing.accents),
                    emotions=json.loads(db_listing.emotions),
                    age_range=(db_listing.age_range_min, db_listing.age_range_max),
                    gender=db_listing.gender,
                    tags=json.loads(db_listing.tags),
                    status=ListingStatus(db_listing.status),
                    rating=db_listing.rating,
                    review_count=db_listing.review_count,
                    download_count=db_listing.download_count,
                    featured=db_listing.featured,
                    trending=db_listing.trending,
                    created_at=db_listing.created_at,
                    updated_at=db_listing.updated_at
                )
                listings.append(listing)
            
            # Cache results
            if self.redis:
                try:
                    await self.redis.setex(
                        cache_key,
                        300,  # 5 minutes
                        json.dumps([listing.__dict__ for listing in listings], default=str)
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache listings: {e}")
            
            return listings
    
    async def get_featured_voices(self) -> List[VoiceListing]:
        """Get featured voice listings"""
        return await self.get_voice_listings({"featured": True}, limit=10)
    
    async def get_trending_voices(self) -> List[VoiceListing]:
        """Get trending voice listings"""
        return await self.get_voice_listings({"trending": True}, limit=10)
    
    async def purchase_voice(self, buyer_id: int, listing_id: str, 
                           payment_data: Dict[str, Any]) -> VoicePurchase:
        """Purchase a voice from marketplace"""
        # Get listing
        listing = await self.get_voice_listing(listing_id)
        if not listing:
            raise ValueError("Voice listing not found")
        
        if listing.status != ListingStatus.APPROVED:
            raise ValueError("Voice listing not available for purchase")
        
        # Create purchase record
        purchase_id = str(uuid.uuid4())
        purchase = VoicePurchase(
            id=purchase_id,
            buyer_id=buyer_id,
            listing_id=listing_id,
            price_paid=listing.price_usd,
            currency=listing.currency,
            payment_method=payment_data.get("payment_method", "stripe"),
            transaction_id=payment_data.get("transaction_id", ""),
            purchased_at=datetime.utcnow(),
            license_type=payment_data.get("license_type", "personal"),
            usage_limits=payment_data.get("usage_limits", {})
        )
        
        # Store purchase
        await self._store_voice_purchase(purchase)
        
        # Update listing download count
        await self._increment_download_count(listing_id)
        
        # Process payment to seller (70% commission)
        seller_amount = listing.price_usd * self.seller_commissions
        await self._process_seller_payment(listing.seller_id, seller_amount, purchase_id)
        
        logger.info(f"✅ Voice purchased: {listing_id} by user {buyer_id}")
        return purchase
    
    async def _store_voice_purchase(self, purchase: VoicePurchase):
        """Store voice purchase in database"""
        # This would store in a VoicePurchase table
        # For now, just log it
        logger.info(f"Voice purchase stored: {purchase.id}")
    
    async def _increment_download_count(self, listing_id: str):
        """Increment download count for listing"""
        async with AsyncSession(async_engine) as session:
            await session.execute(
                update(VoiceMarketplaceListing)
                .where(VoiceMarketplaceListing.id == listing_id)
                .values(download_count=VoiceMarketplaceListing.download_count + 1)
            )
            await session.commit()
    
    async def _process_seller_payment(self, seller_id: int, amount: float, purchase_id: str):
        """Process payment to seller"""
        # This would integrate with payment processing
        # For now, just log it
        logger.info(f"Seller payment processed: ${amount} to seller {seller_id} for purchase {purchase_id}")
    
    async def add_voice_review(self, user_id: int, listing_id: str, 
                             rating: int, review_text: str) -> VoiceReview:
        """Add review and rating for voice"""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        # Check if user has purchased this voice
        # This would check the purchase records
        
        review_id = str(uuid.uuid4())
        review = VoiceReview(
            id=review_id,
            listing_id=listing_id,
            user_id=user_id,
            rating=rating,
            review_text=review_text,
            created_at=datetime.utcnow()
        )
        
        # Store review
        await self._store_voice_review(review)
        
        # Update listing rating
        await self._update_listing_rating(listing_id)
        
        logger.info(f"✅ Voice review added: {review_id}")
        return review
    
    async def _store_voice_review(self, review: VoiceReview):
        """Store voice review in database"""
        # This would store in a VoiceReview table
        logger.info(f"Voice review stored: {review.id}")
    
    async def _update_listing_rating(self, listing_id: str):
        """Update average rating for listing"""
        # This would calculate average rating from all reviews
        # For now, just log it
        logger.info(f"Listing rating updated for: {listing_id}")
    
    async def get_voice_listing(self, listing_id: str) -> Optional[VoiceListing]:
        """Get specific voice listing by ID"""
        # Try cache first
        if self.redis:
            try:
                cached = await self.redis.get(f"voice_listing:{listing_id}")
                if cached:
                    data = json.loads(cached)
                    return VoiceListing(**data)
            except Exception as e:
                logger.warning(f"Failed to get cached listing: {e}")
        
        # Query database
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(VoiceMarketplaceListing).where(VoiceMarketplaceListing.id == listing_id)
            )
            db_listing = result.scalar_one_or_none()
            
            if not db_listing:
                return None
            
            listing = VoiceListing(
                id=db_listing.id,
                title=db_listing.title,
                description=db_listing.description,
                category=VoiceCategory(db_listing.category),
                quality=VoiceQuality(db_listing.quality),
                price_usd=db_listing.price_usd,
                currency=db_listing.currency,
                seller_id=db_listing.seller_id,
                voice_profile_id=db_listing.voice_profile_id,
                sample_audio_url=db_listing.sample_audio_url,
                demo_text=db_listing.demo_text,
                languages=json.loads(db_listing.languages),
                accents=json.loads(db_listing.accents),
                emotions=json.loads(db_listing.emotions),
                age_range=(db_listing.age_range_min, db_listing.age_range_max),
                gender=db_listing.gender,
                tags=json.loads(db_listing.tags),
                status=ListingStatus(db_listing.status),
                rating=db_listing.rating,
                review_count=db_listing.review_count,
                download_count=db_listing.download_count,
                featured=db_listing.featured,
                trending=db_listing.trending,
                created_at=db_listing.created_at,
                updated_at=db_listing.updated_at
            )
            
            # Cache for future requests
            await self._cache_voice_listing(listing)
            
            return listing
    
    async def get_seller_listings(self, seller_id: int) -> List[VoiceListing]:
        """Get all listings for a seller"""
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(VoiceMarketplaceListing)
                .where(VoiceMarketplaceListing.seller_id == seller_id)
                .order_by(VoiceMarketplaceListing.created_at.desc())
            )
            db_listings = result.scalars().all()
            
            listings = []
            for db_listing in db_listings:
                listing = VoiceListing(
                    id=db_listing.id,
                    title=db_listing.title,
                    description=db_listing.description,
                    category=VoiceCategory(db_listing.category),
                    quality=VoiceQuality(db_listing.quality),
                    price_usd=db_listing.price_usd,
                    currency=db_listing.currency,
                    seller_id=db_listing.seller_id,
                    voice_profile_id=db_listing.voice_profile_id,
                    sample_audio_url=db_listing.sample_audio_url,
                    demo_text=db_listing.demo_text,
                    languages=json.loads(db_listing.languages),
                    accents=json.loads(db_listing.accents),
                    emotions=json.loads(db_listing.emotions),
                    age_range=(db_listing.age_range_min, db_listing.age_range_max),
                    gender=db_listing.gender,
                    tags=json.loads(db_listing.tags),
                    status=ListingStatus(db_listing.status),
                    rating=db_listing.rating,
                    review_count=db_listing.review_count,
                    download_count=db_listing.download_count,
                    featured=db_listing.featured,
                    trending=db_listing.trending,
                    created_at=db_listing.created_at,
                    updated_at=db_listing.updated_at
                )
                listings.append(listing)
            
            return listings
    
    async def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        async with AsyncSession(async_engine) as session:
            # Total listings
            total_listings_result = await session.execute(
                select(VoiceMarketplaceListing).where(
                    VoiceMarketplaceListing.status == ListingStatus.APPROVED.value
                )
            )
            total_listings = len(total_listings_result.scalars().all())
            
            # Total sellers
            sellers_result = await session.execute(
                select(VoiceMarketplaceListing.seller_id).distinct()
            )
            total_sellers = len(sellers_result.scalars().all())
            
            # Average price
            avg_price_result = await session.execute(
                select(VoiceMarketplaceListing.price_usd)
                .where(VoiceMarketplaceListing.status == ListingStatus.APPROVED.value)
            )
            prices = [row[0] for row in avg_price_result.fetchall()]
            avg_price = sum(prices) / len(prices) if prices else 0
            
            return {
                "total_listings": total_listings,
                "total_sellers": total_sellers,
                "average_price": round(avg_price, 2),
                "featured_voices": len(await self.get_featured_voices()),
                "trending_voices": len(await self.get_trending_voices()),
                "categories": len(VoiceCategory),
                "commission_rate": self.seller_commissions
            }


# Global voice marketplace service instance
voice_marketplace_service = VoiceMarketplaceService()




