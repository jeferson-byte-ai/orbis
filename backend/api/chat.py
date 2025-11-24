"""Chat API endpoints"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.session import get_db
from backend.db.models import ChatMessage, User, Room
from backend.api.deps import get_current_user
from backend.services.lazy_loader import lazy_loader, ModelType
from ml.mt.nllb_service import nllb_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessageCreate(BaseModel):
    """Create chat message request"""
    room_id: str
    content: str
    language: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    id: str
    room_id: str
    user_id: str
    user_name: str  # full_name or username
    user_avatar: Optional[str]
    content: str
    language: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TranslateMessageRequest(BaseModel):
    """Translate chat message request"""
    text: str
    target_language: str
    source_language: Optional[str] = None


class TranslateMessageResponse(BaseModel):
    """Translate chat message response"""
    translated_text: str
    source_language: str
    target_language: str


class ConnectionManager:
    """WebSocket connection manager for chat rooms"""
    def __init__(self):
        # room_id -> List[WebSocket]
        self.active_connections: dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str):
        """Connect a client to a room"""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info(f"Client connected to room {room_id}. Total: {len(self.active_connections[room_id])}")
    
    def disconnect(self, websocket: WebSocket, room_id: str):
        """Disconnect a client from a room"""
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
            logger.info(f"Client disconnected from room {room_id}")
    
    async def broadcast_to_room(self, room_id: str, message: dict):
        """Broadcast a message to all clients in a room"""
        if room_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for connection in disconnected:
                self.disconnect(connection, room_id)


manager = ConnectionManager()


@router.post("/messages", response_model=ChatMessageResponse)
async def send_message(
    message: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a chat message"""
    try:
        # Verify room exists
        room = db.query(Room).filter(Room.id == UUID(message.room_id)).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Create message
        db_message = ChatMessage(
            room_id=UUID(message.room_id),
            user_id=current_user.id,
            content=message.content,
            language=message.language
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        # Prepare response
        response = ChatMessageResponse(
            id=str(db_message.id),
            room_id=str(db_message.room_id),
            user_id=str(db_message.user_id),
            user_name=current_user.full_name or current_user.username,
            user_avatar=current_user.avatar_url,
            content=db_message.content,
            language=db_message.language,
            created_at=db_message.created_at
        )
        
        # Broadcast to all connected clients in the room
        await manager.broadcast_to_room(
            message.room_id,
            {
                "type": "new_message",
                "message": response.dict()
            }
        )
        
        return response
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/{room_id}", response_model=List[ChatMessageResponse])
async def get_messages(
    room_id: str,
    limit: int = 100,
    before: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat messages for a room"""
    try:
        # Verify room exists
        room = db.query(Room).filter(Room.id == UUID(room_id)).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Query messages
        query = db.query(ChatMessage, User).join(User).filter(
            ChatMessage.room_id == UUID(room_id)
        )
        
        if before:
            # Pagination: get messages before a certain timestamp
            query = query.filter(ChatMessage.created_at < datetime.fromisoformat(before))
        
        messages = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
        
        # Convert to response format
        result = []
        for msg, user in messages:
            result.append(ChatMessageResponse(
                id=str(msg.id),
                room_id=str(msg.room_id),
                user_id=str(msg.user_id),
                user_name=user.full_name or user.username,
                user_avatar=user.avatar_url,
                content=msg.content,
                language=msg.language,
                created_at=msg.created_at
            ))
        
        # Return in chronological order (oldest first)
        return list(reversed(result))
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _normalize_language(code: Optional[str]) -> str:
    """Normalize language codes like pt-BR to pt"""
    if not code:
        return "en"
    normalized = code.lower().replace("_", "-")
    return normalized.split("-")[0]


@router.post("/translate", response_model=TranslateMessageResponse)
async def translate_chat_message(
    request: TranslateMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Translate chat message content using NLLB service"""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required for translation")

    _ = current_user  # Ensure authentication dependency is executed

    source_language = _normalize_language(request.source_language)
    target_language = _normalize_language(request.target_language)

    if source_language == target_language:
        return TranslateMessageResponse(
            translated_text=text,
            source_language=source_language,
            target_language=target_language
        )

    try:
        await lazy_loader.ensure_loaded(ModelType.NLLB)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to ensure NLLB model is loaded: {exc}")

    try:
        translated_text = await nllb_service.translate(text, source_language, target_language)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Translation failed: {exc}")
        raise HTTPException(status_code=500, detail="Translation service unavailable") from exc

    return TranslateMessageResponse(
        translated_text=translated_text,
        source_language=source_language,
        target_language=target_language
    )


@router.websocket("/ws/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, room_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_json()
            
            # Messages are sent via HTTP POST, this is just for keep-alive
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        logger.info(f"Client disconnected from room {room_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, room_id)
