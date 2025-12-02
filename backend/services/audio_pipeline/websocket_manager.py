"""
WebSocket Manager for real-time audio streaming
Handles audio chunks, participant connections, and low-latency delivery
"""
import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time audio"""
    
    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.room_connections: Dict[str, List[UUID]] = {}
        self.user_rooms: Dict[UUID, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: UUID, room_id: str):
        """Connect user to room"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
        
        self.room_connections[room_id].append(user_id)
        self.user_rooms[user_id] = room_id
        
        logger.info(f"User {user_id} connected to room {room_id}")
    
    def disconnect(self, user_id: UUID):
        """Disconnect user from room"""
        if user_id in self.user_rooms:
            room_id = self.user_rooms[user_id]
            if room_id in self.room_connections:
                self.room_connections[room_id].remove(user_id)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]
            
            del self.user_rooms[user_id]
        
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        logger.info(f"User {user_id} disconnected")
    
    async def send_audio_to_room(self, room_id: str, audio_data: dict, exclude_user: Optional[UUID] = None):
        """Send audio data to all users in room except excluded user"""
        if room_id not in self.room_connections:
            return
        
        tasks = []
        for user_id in self.room_connections[room_id]:
            if user_id == exclude_user:
                continue
            
            if user_id in self.active_connections:
                tasks.append(
                    self.active_connections[user_id].send_json(audio_data)
                )
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_room(self, room_id: str, message: dict, exclude_user: Optional[UUID] = None):
        """Broadcast message to all users in room (optionally excluding a user)"""
        if room_id not in self.room_connections:
            logger.warning(f"Cannot broadcast to room {room_id}: room not found")
            return
        
        tasks = []
        for user_id in self.room_connections[room_id]:
            if user_id == exclude_user:
                continue
            
            if user_id in self.active_connections:
                try:
                    tasks.append(
                        self.active_connections[user_id].send_json(message)
                    )
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Log any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to send message: {result}")
    
    async def send_personal_message(self, user_id: UUID, message: dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
    
    def get_room_users(self, room_id: str) -> List[UUID]:
        """Get all users in a room"""
        return self.room_connections.get(room_id, [])
    
    def get_user_room(self, user_id: UUID) -> Optional[str]:
        """Get room ID for user"""
        return self.user_rooms.get(user_id)


class AudioChunkManager:
    """Manages audio chunks for real-time processing"""
    
    def __init__(self, chunk_duration_ms: int = 500):
        self.chunk_duration_ms = chunk_duration_ms
        self.audio_buffers: Dict[UUID, List[bytes]] = {}
    
    def add_audio_chunk(self, user_id: UUID, audio_data: bytes):
        """Add audio chunk to user's buffer"""
        if user_id not in self.audio_buffers:
            self.audio_buffers[user_id] = []
        
        self.audio_buffers[user_id].append(audio_data)
        
        # Keep only recent chunks (last 2 seconds)
        max_chunks = 2000 // self.chunk_duration_ms
        if len(self.audio_buffers[user_id]) > max_chunks:
            self.audio_buffers[user_id] = self.audio_buffers[user_id][-max_chunks:]
    
    def get_audio_chunks(self, user_id: UUID) -> List[bytes]:
        """Get all audio chunks for user"""
        return self.audio_buffers.get(user_id, [])

    def consume_audio_chunks(self, user_id: UUID) -> List[bytes]:
        """Retrieve and clear buffered audio chunks for a user"""
        if user_id not in self.audio_buffers:
            return []

        chunks = self.audio_buffers[user_id]
        self.audio_buffers[user_id] = []
        return chunks
    
    def clear_audio_buffer(self, user_id: UUID):
        """Clear user's audio buffer"""
        if user_id in self.audio_buffers:
            del self.audio_buffers[user_id]


# Global instances
connection_manager = ConnectionManager()
audio_chunk_manager = AudioChunkManager()