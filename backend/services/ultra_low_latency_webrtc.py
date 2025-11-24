"""
Ultra-Low Latency WebRTC Service
Custom WebRTC implementation for <250ms latency
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import uuid

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.config import settings
from backend.db.models import Room, User
# # from backend.db.models import WebRTCSession  # TODO: Create this model
from backend.db.session import async_engine

logger = logging.getLogger(__name__)


class ConnectionQuality(Enum):
    """Connection quality levels"""
    EXCELLENT = "excellent"  # <100ms latency
    GOOD = "good"  # <250ms latency
    FAIR = "fair"  # <500ms latency
    POOR = "poor"  # >500ms latency


class MediaType(Enum):
    """Media types"""
    AUDIO = "audio"
    VIDEO = "video"
    SCREEN = "screen"
    DATA = "data"


@dataclass
class WebRTCStats:
    """WebRTC connection statistics"""
    connection_id: str
    user_id: int
    room_id: str
    latency: float
    jitter: float
    packet_loss: float
    bandwidth: float
    quality: ConnectionQuality
    timestamp: datetime


@dataclass
class MediaStream:
    """Media stream information"""
    stream_id: str
    user_id: int
    media_type: MediaType
    codec: str
    bitrate: int
    resolution: Tuple[int, int]
    framerate: int
    quality: ConnectionQuality


@dataclass
class ICEConfiguration:
    """ICE server configuration"""
    servers: List[Dict[str, Any]]
    ice_candidate_pool_size: int
    bundle_policy: str
    rtcp_mux_policy: str


class UltraLowLatencyWebRTCService:
    """Ultra-low latency WebRTC service"""
    
    def __init__(self):
        self.redis = None
        self.active_connections = {}
        self.room_sessions = {}
        self.media_streams = {}
        self.connection_stats = {}
        self.ice_configurations = {}
        
        # Performance optimization settings
        self.optimization_settings = {
            "audio_codec": "opus",
            "video_codec": "VP8",
            "audio_bitrate": 64000,  # 64kbps for low latency
            "video_bitrate": 500000,  # 500kbps for low latency
            "audio_sample_rate": 48000,
            "audio_channels": 1,
            "video_width": 640,
            "video_height": 480,
            "video_framerate": 15,  # Lower framerate for lower latency
            "keyframe_interval": 30,  # 2 seconds at 15fps
            "buffer_size": 100,  # ms
            "jitter_buffer": 50,  # ms
            "packet_loss_threshold": 0.05,  # 5%
            "latency_threshold": 250  # ms
        }
        
        # ICE server configurations
        self.ice_servers = [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
            {"urls": "stun:stun2.l.google.com:19302"},
            {"urls": "stun:stun3.l.google.com:19302"},
            {"urls": "stun:stun4.l.google.com:19302"}
        ]
    
    async def initialize(self):
        """Initialize ultra-low latency WebRTC service"""
        try:
            # Connect to Redis
            self.redis = redis.from_url(settings.redis_url)
            await self.redis.ping()
            
            # Start background tasks
            asyncio.create_task(self._connection_monitor())
            asyncio.create_task(self._stats_collector())
            asyncio.create_task(self._quality_optimizer())
            
            logger.info("✅ Ultra-Low Latency WebRTC Service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Ultra-Low Latency WebRTC Service: {e}")
    
    async def create_room_session(self, room_id: str, creator_id: int) -> Dict[str, Any]:
        """Create a new room session with optimized settings"""
        session_id = str(uuid.uuid4())
        
        # Create room session
        session = {
            "id": session_id,
            "room_id": room_id,
            "creator_id": creator_id,
            "participants": {},
            "media_streams": {},
            "ice_configuration": self._get_ice_configuration(),
            "created_at": datetime.utcnow(),
            "settings": self.optimization_settings.copy()
        }
        
        # Store session
        self.room_sessions[room_id] = session
        
        # Store in Redis for persistence
        await self._store_room_session(session)
        
        logger.info(f"✅ Room session created: {room_id}")
        return {
            "session_id": session_id,
            "room_id": room_id,
            "ice_configuration": session["ice_configuration"],
            "settings": session["settings"]
        }
    
    def _get_ice_configuration(self) -> ICEConfiguration:
        """Get optimized ICE configuration"""
        return ICEConfiguration(
            servers=self.ice_servers,
            ice_candidate_pool_size=10,
            bundle_policy="max-bundle",
            rtcp_mux_policy="require"
        )
    
    async def _store_room_session(self, session: Dict[str, Any]):
        """Store room session in Redis"""
        if not self.redis:
            return
        
        try:
            await self.redis.setex(
                f"webrtc_session:{session['room_id']}",
                3600,  # 1 hour
                json.dumps(session, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to store room session: {e}")
    
    async def join_room(self, room_id: str, user_id: int, 
                       media_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Join a room with optimized media constraints"""
        if room_id not in self.room_sessions:
            raise ValueError(f"Room {room_id} not found")
        
        session = self.room_sessions[room_id]
        
        # Create connection ID
        connection_id = str(uuid.uuid4())
        
        # Add participant to session
        session["participants"][user_id] = {
            "connection_id": connection_id,
            "joined_at": datetime.utcnow(),
            "media_constraints": media_constraints,
            "connection_quality": ConnectionQuality.GOOD,
            "stats": {
                "latency": 0.0,
                "jitter": 0.0,
                "packet_loss": 0.0,
                "bandwidth": 0.0
            }
        }
        
        # Create media streams
        media_streams = await self._create_media_streams(user_id, media_constraints)
        session["media_streams"][user_id] = media_streams
        
        # Store active connection
        self.active_connections[connection_id] = {
            "user_id": user_id,
            "room_id": room_id,
            "session_id": session["id"],
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        
        # Update session in Redis
        await self._store_room_session(session)
        
        logger.info(f"✅ User {user_id} joined room {room_id}")
        return {
            "connection_id": connection_id,
            "ice_configuration": session["ice_configuration"],
            "media_streams": media_streams,
            "participants": list(session["participants"].keys())
        }
    
    async def _create_media_streams(self, user_id: int, 
                                  media_constraints: Dict[str, Any]) -> List[MediaStream]:
        """Create optimized media streams"""
        streams = []
        
        # Audio stream
        if media_constraints.get("audio", True):
            audio_stream = MediaStream(
                stream_id=f"audio_{user_id}_{uuid.uuid4()}",
                user_id=user_id,
                media_type=MediaType.AUDIO,
                codec=self.optimization_settings["audio_codec"],
                bitrate=self.optimization_settings["audio_bitrate"],
                resolution=(0, 0),  # Not applicable for audio
                framerate=0,  # Not applicable for audio
                quality=ConnectionQuality.GOOD
            )
            streams.append(audio_stream)
        
        # Video stream
        if media_constraints.get("video", True):
            video_stream = MediaStream(
                stream_id=f"video_{user_id}_{uuid.uuid4()}",
                user_id=user_id,
                media_type=MediaType.VIDEO,
                codec=self.optimization_settings["video_codec"],
                bitrate=self.optimization_settings["video_bitrate"],
                resolution=(
                    self.optimization_settings["video_width"],
                    self.optimization_settings["video_height"]
                ),
                framerate=self.optimization_settings["video_framerate"],
                quality=ConnectionQuality.GOOD
            )
            streams.append(video_stream)
        
        return streams
    
    async def handle_ice_candidate(self, connection_id: str, 
                                 candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ICE candidate exchange"""
        if connection_id not in self.active_connections:
            raise ValueError(f"Connection {connection_id} not found")
        
        connection = self.active_connections[connection_id]
        room_id = connection["room_id"]
        
        # Store ICE candidate
        candidate_id = str(uuid.uuid4())
        
        # Broadcast to other participants
        await self._broadcast_ice_candidate(room_id, connection_id, candidate)
        
        return {
            "candidate_id": candidate_id,
            "status": "processed"
        }
    
    async def _broadcast_ice_candidate(self, room_id: str, sender_connection_id: str, 
                                     candidate: Dict[str, Any]):
        """Broadcast ICE candidate to other participants"""
        if room_id not in self.room_sessions:
            return
        
        session = self.room_sessions[room_id]
        sender_user_id = self.active_connections[sender_connection_id]["user_id"]
        
        # Send to all other participants
        for user_id, participant in session["participants"].items():
            if user_id != sender_user_id:
                # This would send via WebSocket
                await self._send_ice_candidate(
                    participant["connection_id"],
                    sender_user_id,
                    candidate
                )
    
    async def _send_ice_candidate(self, connection_id: str, sender_user_id: int, 
                                candidate: Dict[str, Any]):
        """Send ICE candidate to specific connection"""
        # This would integrate with WebSocket service
        # For now, just log it
        logger.info(f"Sending ICE candidate from {sender_user_id} to {connection_id}")
    
    async def handle_offer(self, connection_id: str, offer: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WebRTC offer"""
        if connection_id not in self.active_connections:
            raise ValueError(f"Connection {connection_id} not found")
        
        connection = self.active_connections[connection_id]
        room_id = connection["room_id"]
        
        # Process offer and create answer
        answer = await self._create_answer(offer, connection_id)
        
        # Store offer/answer
        await self._store_offer_answer(connection_id, offer, answer)
        
        return {
            "answer": answer,
            "status": "processed"
        }
    
    async def _create_answer(self, offer: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
        """Create WebRTC answer with optimized settings"""
        # This would use WebRTC library to create answer
        # For now, return mock answer
        return {
            "type": "answer",
            "sdp": "mock_sdp_answer",
            "connection_id": connection_id
        }
    
    async def _store_offer_answer(self, connection_id: str, offer: Dict[str, Any], 
                                answer: Dict[str, Any]):
        """Store offer/answer for debugging"""
        if not self.redis:
            return
        
        try:
            data = {
                "connection_id": connection_id,
                "offer": offer,
                "answer": answer,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis.setex(
                f"webrtc_offer_answer:{connection_id}",
                3600,  # 1 hour
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Failed to store offer/answer: {e}")
    
    async def update_connection_stats(self, connection_id: str, stats: Dict[str, Any]):
        """Update connection statistics"""
        if connection_id not in self.active_connections:
            return
        
        connection = self.active_connections[connection_id]
        user_id = connection["user_id"]
        room_id = connection["room_id"]
        
        # Update stats
        self.connection_stats[connection_id] = WebRTCStats(
            connection_id=connection_id,
            user_id=user_id,
            room_id=room_id,
            latency=stats.get("latency", 0.0),
            jitter=stats.get("jitter", 0.0),
            packet_loss=stats.get("packetLoss", 0.0),
            bandwidth=stats.get("bandwidth", 0.0),
            quality=self._calculate_quality(stats),
            timestamp=datetime.utcnow()
        )
        
        # Update participant stats in session
        if room_id in self.room_sessions:
            session = self.room_sessions[room_id]
            if user_id in session["participants"]:
                session["participants"][user_id]["stats"] = stats
                session["participants"][user_id]["connection_quality"] = self._calculate_quality(stats)
    
    def _calculate_quality(self, stats: Dict[str, Any]) -> ConnectionQuality:
        """Calculate connection quality based on stats"""
        latency = stats.get("latency", 0.0)
        packet_loss = stats.get("packetLoss", 0.0)
        
        if latency < 100 and packet_loss < 0.01:
            return ConnectionQuality.EXCELLENT
        elif latency < 250 and packet_loss < 0.05:
            return ConnectionQuality.GOOD
        elif latency < 500 and packet_loss < 0.1:
            return ConnectionQuality.FAIR
        else:
            return ConnectionQuality.POOR
    
    async def _connection_monitor(self):
        """Monitor connections for health and performance"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.utcnow()
                disconnected_connections = []
                
                for connection_id, connection in self.active_connections.items():
                    # Check for inactive connections
                    if (current_time - connection["last_activity"]).total_seconds() > 300:  # 5 minutes
                        disconnected_connections.append(connection_id)
                
                # Remove disconnected connections
                for connection_id in disconnected_connections:
                    await self._remove_connection(connection_id)
                
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
    
    async def _stats_collector(self):
        """Collect and store connection statistics"""
        while True:
            try:
                await asyncio.sleep(60)  # Collect every minute
                
                # Store stats in database
                await self._store_connection_stats()
                
            except Exception as e:
                logger.error(f"Error in stats collector: {e}")
    
    async def _quality_optimizer(self):
        """Optimize connection quality based on stats"""
        while True:
            try:
                await asyncio.sleep(120)  # Optimize every 2 minutes
                
                # Analyze connection quality and suggest optimizations
                await self._analyze_and_optimize()
                
            except Exception as e:
                logger.error(f"Error in quality optimizer: {e}")
    
    async def _remove_connection(self, connection_id: str):
        """Remove connection and clean up resources"""
        if connection_id not in self.active_connections:
            return
        
        connection = self.active_connections[connection_id]
        user_id = connection["user_id"]
        room_id = connection["room_id"]
        
        # Remove from room session
        if room_id in self.room_sessions:
            session = self.room_sessions[room_id]
            if user_id in session["participants"]:
                del session["participants"][user_id]
            if user_id in session["media_streams"]:
                del session["media_streams"][user_id]
        
        # Remove from active connections
        del self.active_connections[connection_id]
        
        # Remove stats
        if connection_id in self.connection_stats:
            del self.connection_stats[connection_id]
        
        logger.info(f"✅ Connection {connection_id} removed")
    
    async def _store_connection_stats(self):
        """Store connection statistics in database"""
        try:
            async with AsyncSession(async_engine) as session:
                for connection_id, stats in self.connection_stats.items():
                    # This would store in WebRTCSession table
                    # For now, just log it
                    pass
        except Exception as e:
            logger.warning(f"Failed to store connection stats: {e}")
    
    async def _analyze_and_optimize(self):
        """Analyze connection quality and suggest optimizations"""
        for connection_id, stats in self.connection_stats.items():
            if stats.quality == ConnectionQuality.POOR:
                # Suggest optimizations for poor quality connections
                await self._suggest_optimizations(connection_id, stats)
    
    async def _suggest_optimizations(self, connection_id: str, stats: WebRTCStats):
        """Suggest optimizations for poor quality connections"""
        optimizations = []
        
        if stats.latency > 250:
            optimizations.append("Consider using a closer server")
        
        if stats.packet_loss > 0.05:
            optimizations.append("Check network stability")
        
        if stats.bandwidth < 1000000:  # 1Mbps
            optimizations.append("Reduce video quality or disable video")
        
        # Send optimizations to client
        logger.info(f"Optimizations for {connection_id}: {optimizations}")
    
    async def get_room_stats(self, room_id: str) -> Dict[str, Any]:
        """Get room statistics"""
        if room_id not in self.room_sessions:
            return {"error": "Room not found"}
        
        session = self.room_sessions[room_id]
        
        # Calculate room statistics
        total_participants = len(session["participants"])
        avg_latency = 0.0
        avg_quality = 0.0
        
        if total_participants > 0:
            latencies = []
            qualities = []
            
            for user_id, participant in session["participants"].items():
                stats = participant["stats"]
                latencies.append(stats["latency"])
                qualities.append(participant["connection_quality"].value)
            
            avg_latency = sum(latencies) / len(latencies)
            avg_quality = sum(qualities) / len(qualities)
        
        return {
            "room_id": room_id,
            "total_participants": total_participants,
            "average_latency": avg_latency,
            "average_quality": avg_quality,
            "session_duration": (datetime.utcnow() - session["created_at"]).total_seconds(),
            "participants": list(session["participants"].keys())
        }
    
    async def get_connection_stats(self, connection_id: str) -> Optional[WebRTCStats]:
        """Get connection statistics"""
        return self.connection_stats.get(connection_id)
    
    async def leave_room(self, connection_id: str) -> Dict[str, Any]:
        """Leave room and clean up resources"""
        if connection_id not in self.active_connections:
            return {"error": "Connection not found"}
        
        connection = self.active_connections[connection_id]
        room_id = connection["room_id"]
        
        # Remove connection
        await self._remove_connection(connection_id)
        
        # Update room session
        if room_id in self.room_sessions:
            await self._store_room_session(self.room_sessions[room_id])
        
        return {
            "status": "left",
            "room_id": room_id,
            "connection_id": connection_id
        }


# Global ultra-low latency WebRTC service instance
ultra_low_latency_webrtc_service = UltraLowLatencyWebRTCService()




