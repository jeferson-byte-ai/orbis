"""
AI Meeting Assistant Service
Advanced AI features for billion-dollar scale meetings
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import openai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.db.models import User, Room
# from backend.db.models import MeetingTranscript  # TODO: Create this model
from backend.db.session import async_engine
from backend.config import settings

logger = logging.getLogger(__name__)


class MeetingActionType(Enum):
    """Types of meeting actions"""
    ACTION_ITEM = "action_item"
    DECISION = "decision"
    QUESTION = "question"
    CONCERN = "concern"
    IDEA = "idea"
    FOLLOW_UP = "follow_up"
    DEADLINE = "deadline"


@dataclass
class MeetingAction:
    """Meeting action item"""
    id: str
    type: MeetingActionType
    description: str
    assignee: Optional[str]
    due_date: Optional[datetime]
    priority: str  # low, medium, high, critical
    status: str  # pending, in_progress, completed, cancelled
    created_at: datetime
    updated_at: datetime


@dataclass
class MeetingSummary:
    """AI-generated meeting summary"""
    id: str
    room_id: str
    title: str
    summary: str
    key_points: List[str]
    action_items: List[MeetingAction]
    decisions: List[str]
    participants: List[str]
    duration_minutes: int
    created_at: datetime


@dataclass
class RealTimeInsight:
    """Real-time meeting insight"""
    type: str  # sentiment, engagement, topic, language
    value: Any
    confidence: float
    timestamp: datetime
    participant_id: Optional[str] = None


class AIMeetingAssistant:
    """AI-powered meeting assistant with advanced features"""
    
    def __init__(self):
        self.openai_client = None
        self.active_meetings = {}
        self.real_time_insights = {}
        self.meeting_summaries = {}
        
    async def initialize(self):
        """Initialize AI meeting assistant"""
        try:
            if settings.openai_api_key:
                self.openai_client = openai.AsyncOpenAI(
                    api_key=settings.openai_api_key
                )
                logger.info("✅ AI Meeting Assistant initialized with OpenAI")
            else:
                logger.warning("⚠️ OpenAI API key not configured - AI features disabled")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI Meeting Assistant: {e}")
    
    async def start_meeting_analysis(self, room_id: str, participants: List[str]):
        """Start real-time meeting analysis"""
        self.active_meetings[room_id] = {
            "participants": participants,
            "start_time": datetime.utcnow(),
            "transcript": [],
            "insights": [],
            "action_items": [],
            "decisions": [],
            "sentiment_history": [],
            "engagement_scores": {}
        }
        
        logger.info(f"🎯 Started AI analysis for meeting {room_id}")
    
    async def process_audio_chunk(self, room_id: str, participant_id: str, 
                                audio_data: bytes, language: str = "en") -> Dict[str, Any]:
        """Process audio chunk and generate real-time insights"""
        if room_id not in self.active_meetings:
            return {"error": "Meeting not found"}
        
        meeting_data = self.active_meetings[room_id]
        
        # Simulate ASR processing (would integrate with actual ASR)
        transcript_text = await self._transcribe_audio(audio_data, language)
        
        # Add to meeting transcript
        transcript_entry = {
            "participant_id": participant_id,
            "text": transcript_text,
            "timestamp": datetime.utcnow(),
            "language": language
        }
        meeting_data["transcript"].append(transcript_entry)
        
        # Generate real-time insights
        insights = await self._generate_real_time_insights(
            room_id, transcript_text, participant_id
        )
        
        # Update engagement scores
        await self._update_engagement_scores(room_id, participant_id, transcript_text)
        
        return {
            "transcript": transcript_text,
            "insights": insights,
            "engagement_score": meeting_data["engagement_scores"].get(participant_id, 0.5)
        }
    
    async def _transcribe_audio(self, audio_data: bytes, language: str) -> str:
        """Transcribe audio using ASR service"""
        # This would integrate with the actual ASR service
        # For now, return a mock transcription
        return f"Mock transcription in {language}: This is a sample transcript."
    
    async def _generate_real_time_insights(self, room_id: str, text: str, 
                                         participant_id: str) -> List[RealTimeInsight]:
        """Generate real-time insights from transcript text"""
        insights = []
        
        # Sentiment analysis
        sentiment = await self._analyze_sentiment(text)
        insights.append(RealTimeInsight(
            type="sentiment",
            value=sentiment,
            confidence=0.85,
            timestamp=datetime.utcnow(),
            participant_id=participant_id
        ))
        
        # Topic detection
        topics = await self._detect_topics(text)
        for topic in topics:
            insights.append(RealTimeInsight(
                type="topic",
                value=topic,
                confidence=0.75,
                timestamp=datetime.utcnow(),
                participant_id=participant_id
            ))
        
        # Action item detection
        action_items = await self._detect_action_items(text)
        for action in action_items:
            insights.append(RealTimeInsight(
                type="action_item",
                value=action,
                confidence=0.8,
                timestamp=datetime.utcnow(),
                participant_id=participant_id
            ))
        
        # Store insights
        if room_id not in self.real_time_insights:
            self.real_time_insights[room_id] = []
        self.real_time_insights[room_id].extend(insights)
        
        return insights
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        if not self.openai_client:
            return {"sentiment": "neutral", "score": 0.0}
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of the following text. Return a JSON object with 'sentiment' (positive/negative/neutral) and 'score' (-1 to 1)."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.warning(f"Failed to analyze sentiment: {e}")
            return {"sentiment": "neutral", "score": 0.0}
    
    async def _detect_topics(self, text: str) -> List[str]:
        """Detect topics in text"""
        if not self.openai_client:
            return ["general"]
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract the main topics from the following text. Return a JSON array of topic strings."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.1
            )
            
            topics = json.loads(response.choices[0].message.content)
            return topics if isinstance(topics, list) else [topics]
        except Exception as e:
            logger.warning(f"Failed to detect topics: {e}")
            return ["general"]
    
    async def _detect_action_items(self, text: str) -> List[Dict[str, Any]]:
        """Detect action items in text"""
        if not self.openai_client:
            return []
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract action items from the following text. Return a JSON array of objects with 'description', 'assignee' (if mentioned), and 'priority' (low/medium/high)."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.1
            )
            
            action_items = json.loads(response.choices[0].message.content)
            return action_items if isinstance(action_items, list) else []
        except Exception as e:
            logger.warning(f"Failed to detect action items: {e}")
            return []
    
    async def _update_engagement_scores(self, room_id: str, participant_id: str, text: str):
        """Update engagement scores for participants"""
        if room_id not in self.active_meetings:
            return
        
        meeting_data = self.active_meetings[room_id]
        
        # Simple engagement scoring based on text length and frequency
        text_length = len(text.split())
        current_score = meeting_data["engagement_scores"].get(participant_id, 0.5)
        
        # Update score based on contribution
        if text_length > 10:  # Substantial contribution
            new_score = min(1.0, current_score + 0.1)
        elif text_length > 5:  # Moderate contribution
            new_score = min(1.0, current_score + 0.05)
        else:  # Minimal contribution
            new_score = max(0.0, current_score - 0.02)
        
        meeting_data["engagement_scores"][participant_id] = new_score
    
    async def generate_meeting_summary(self, room_id: str) -> MeetingSummary:
        """Generate comprehensive meeting summary"""
        if room_id not in self.active_meetings:
            raise ValueError(f"Meeting {room_id} not found")
        
        meeting_data = self.active_meetings[room_id]
        
        # Combine all transcript text
        full_transcript = " ".join([
            entry["text"] for entry in meeting_data["transcript"]
        ])
        
        # Generate summary using AI
        summary_data = await self._generate_ai_summary(
            full_transcript, 
            meeting_data["participants"]
        )
        
        # Create meeting summary
        meeting_summary = MeetingSummary(
            id=f"summary_{room_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            room_id=room_id,
            title=summary_data.get("title", "Meeting Summary"),
            summary=summary_data.get("summary", ""),
            key_points=summary_data.get("key_points", []),
            action_items=summary_data.get("action_items", []),
            decisions=summary_data.get("decisions", []),
            participants=meeting_data["participants"],
            duration_minutes=int((datetime.utcnow() - meeting_data["start_time"]).total_seconds() / 60),
            created_at=datetime.utcnow()
        )
        
        # Store summary
        self.meeting_summaries[room_id] = meeting_summary
        
        # Store in database
        await self._store_meeting_summary(meeting_summary)
        
        return meeting_summary
    
    async def _generate_ai_summary(self, transcript: str, participants: List[str]) -> Dict[str, Any]:
        """Generate AI-powered meeting summary"""
        if not self.openai_client:
            return {
                "title": "Meeting Summary",
                "summary": "AI summary generation not available",
                "key_points": ["Meeting completed"],
                "action_items": [],
                "decisions": []
            }
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Generate a comprehensive meeting summary from the following transcript.
                        Participants: {', '.join(participants)}
                        
                        Return a JSON object with:
                        - title: Brief meeting title
                        - summary: 2-3 paragraph summary
                        - key_points: Array of 3-5 key discussion points
                        - action_items: Array of action items with description, assignee, and priority
                        - decisions: Array of decisions made
                        
                        Focus on actionable items and important decisions."""
                    },
                    {
                        "role": "user",
                        "content": transcript
                    }
                ],
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.warning(f"Failed to generate AI summary: {e}")
            return {
                "title": "Meeting Summary",
                "summary": "Failed to generate AI summary",
                "key_points": ["Meeting completed"],
                "action_items": [],
                "decisions": []
            }
    
    async def _store_meeting_summary(self, summary: MeetingSummary):
        """Store meeting summary in database"""
        try:
            async with AsyncSession(async_engine) as session:
                # Create meeting transcript record
                transcript = MeetingTranscript(
                    room_id=summary.room_id,
                    summary=summary.summary,
                    key_points=json.dumps(summary.key_points),
                    action_items=json.dumps([item.__dict__ for item in summary.action_items]),
                    decisions=json.dumps(summary.decisions),
                    participants=json.dumps(summary.participants),
                    duration_minutes=summary.duration_minutes,
                    created_at=summary.created_at
                )
                
                session.add(transcript)
                await session.commit()
                
                logger.info(f"✅ Meeting summary stored for room {summary.room_id}")
        except Exception as e:
            logger.error(f"❌ Failed to store meeting summary: {e}")
    
    async def get_meeting_insights(self, room_id: str) -> Dict[str, Any]:
        """Get real-time meeting insights"""
        if room_id not in self.active_meetings:
            return {"error": "Meeting not found"}
        
        meeting_data = self.active_meetings[room_id]
        insights = self.real_time_insights.get(room_id, [])
        
        # Aggregate insights
        sentiment_scores = [i.value["score"] for i in insights if i.type == "sentiment"]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        topics = [i.value for i in insights if i.type == "topic"]
        topic_counts = {}
        for topic in topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        return {
            "meeting_id": room_id,
            "duration_minutes": int((datetime.utcnow() - meeting_data["start_time"]).total_seconds() / 60),
            "participant_count": len(meeting_data["participants"]),
            "transcript_length": len(meeting_data["transcript"]),
            "average_sentiment": avg_sentiment,
            "top_topics": sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "engagement_scores": meeting_data["engagement_scores"],
            "action_items_detected": len([i for i in insights if i.type == "action_item"]),
            "insights_count": len(insights)
        }
    
    async def end_meeting_analysis(self, room_id: str) -> MeetingSummary:
        """End meeting analysis and generate final summary"""
        if room_id not in self.active_meetings:
            raise ValueError(f"Meeting {room_id} not found")
        
        # Generate final summary
        summary = await self.generate_meeting_summary(room_id)
        
        # Clean up active meeting data
        del self.active_meetings[room_id]
        if room_id in self.real_time_insights:
            del self.real_time_insights[room_id]
        
        logger.info(f"🎯 Ended AI analysis for meeting {room_id}")
        return summary
    
    async def get_meeting_history(self, user_id: int, limit: int = 10) -> List[MeetingSummary]:
        """Get meeting history for a user"""
        try:
            async with AsyncSession(async_engine) as session:
                result = await session.execute(
                    select(MeetingTranscript)
                    .where(MeetingTranscript.room_id.in_(
                        select(Room.id).where(Room.created_by == user_id)
                    ))
                    .order_by(MeetingTranscript.created_at.desc())
                    .limit(limit)
                )
                
                transcripts = result.scalars().all()
                
                summaries = []
                for transcript in transcripts:
                    summary = MeetingSummary(
                        id=transcript.id,
                        room_id=transcript.room_id,
                        title=f"Meeting {transcript.room_id}",
                        summary=transcript.summary,
                        key_points=json.loads(transcript.key_points),
                        action_items=json.loads(transcript.action_items),
                        decisions=json.loads(transcript.decisions),
                        participants=json.loads(transcript.participants),
                        duration_minutes=transcript.duration_minutes,
                        created_at=transcript.created_at
                    )
                    summaries.append(summary)
                
                return summaries
        except Exception as e:
            logger.error(f"❌ Failed to get meeting history: {e}")
            return []


# Global AI meeting assistant instance
ai_meeting_assistant = AIMeetingAssistant()




