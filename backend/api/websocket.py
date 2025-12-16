"""
WebSocket endpoints for real-time audio streaming and translation
"""
import base64
import logging
from uuid import UUID
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.routing import APIRouter

from backend.services.audio_pipeline.websocket_manager import connection_manager, audio_chunk_manager
from backend.services.audio_pipeline.stream_processor import audio_stream_processor
from backend.api.deps import get_current_user_ws, get_current_user
from backend.db.session import get_db
from backend.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_participants_info(room_id: str) -> list:
    """Get detailed information about all participants in a room"""
    from backend.db.session import SessionLocal
    
    participants = []
    user_ids = connection_manager.room_connections.get(room_id, [])
    
    if not user_ids:
        return participants
    
    db = SessionLocal()
    try:
        for user_id in user_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                participants.append({
                    "id": str(user.id),
                    "username": user.username,
                    "full_name": user.full_name,
                    "name": user.full_name or user.username
                })
    finally:
        db.close()
    
    return participants


@router.websocket("/ws/audio/{room_id}")
async def websocket_audio_endpoint(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for real-time audio streaming
    
    Flow:
    1. Client connects with user authentication
    2. Client sends audio chunks as they speak
    3. Server processes and translates audio
    4. Server sends translated audio to other participants
    """
    
    
    logger.info(f"🔌 WebSocket connection attempt to room: {room_id}")
    logger.info(f"Query params: {websocket.query_params}")
    logger.info(f"Headers: {dict(websocket.headers)}")
    logger.info(f"Origin: {websocket.headers.get('origin', 'NO ORIGIN')}")
    
    # Check origin and log
    origin = websocket.headers.get("origin")
    if origin:
        logger.info(f"📍 WebSocket connection from origin: {origin}")
    
    # IMPORTANT: Accept connection FIRST (before authentication)
    # This prevents ngrok free tier from rejecting connections with query params
    await websocket.accept()
    logger.info("✅ WebSocket connection accepted")
    
    # NOW authenticate user
    try:
        logger.info("🔐 Attempting to authenticate WebSocket user...")
        user = await get_current_user_ws(websocket)
        if not user:
            logger.error("❌ Authentication failed: user is None")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        user_id = user.id
        logger.info(f"✅ User authenticated: {user_id}")
    except HTTPException as e:
        logger.error(f"❌ Authentication HTTPException: {e.detail}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    except Exception as e:
        logger.error(f"❌ Authentication error: {type(e).__name__}: {e}")
        await websocket.close(code=1011, reason="Internal server error")
        return
    
    # Store connection (don't call accept again, already done above)
    connection_manager.active_connections.setdefault(user_id, []).append(websocket)
    if room_id not in connection_manager.room_connections:
        connection_manager.room_connections[room_id] = []
    if user_id not in connection_manager.room_connections[room_id]:
        connection_manager.room_connections[room_id].append(user_id)
    connection_manager.user_rooms[user_id] = room_id
    logger.info(f"User {user_id} connected to room {room_id}")
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": str(user_id),
            "room_id": room_id,
            "message": "Connected to audio stream"
        })
        
        # Notify all participants in the room that someone joined
        participant_list = await get_participants_info(room_id)
        await connection_manager.broadcast_to_room(room_id, {
            "type": "participant_joined",
            "user_id": str(user_id),
            "user_name": user.full_name or user.username,
            "participants": participant_list
        }, exclude_user=None)
        
        # Get user's language preferences from database
        from backend.db.session import SessionLocal
        db = SessionLocal()
        try:
            user_with_langs = db.query(User).filter(User.id == user_id).first()
            speaks_pref = (user_with_langs.speaks_languages or []) if user_with_langs else []
            understands_pref = (user_with_langs.understands_languages or []) if user_with_langs else []
            # Use user's configured input/output if present; otherwise fall back
            input_lang = (speaks_pref[0] if speaks_pref else "auto")
            output_lang = (understands_pref[0] if understands_pref else "en")
            logger.info(
                "🌐 Loaded user languages from DB: speaks=%s (%s), wants_to_hear=%s (%s)",
                input_lang,
                speaks_pref,
                output_lang,
                understands_pref
            )
        finally:
            db.close()
        
        # Start audio processing for this user only if we have a concrete input language
        # If input is 'auto' and no speaks_pref, wait for init_settings from client to avoid wrong decisions
        should_start = bool(input_lang and input_lang != 'auto') or bool(speaks_pref)
        if should_start:
            await audio_stream_processor.start_processing(
                user_id,
                room_id,
                input_lang=input_lang,
                output_lang=output_lang,
                speaks_pref=speaks_pref,
                understands_pref=understands_pref
            )
        else:
            logger.warning(
                "⏸️ Deferring start_processing for user %s: input_lang=auto and no speaks_pref. Waiting for init_settings...",
                user_id
            )
        
        # If we deferred start (no concrete input language), auto-start after timeout using profile
        if not should_start:
            async def _delayed_autostart():
                try:
                    await asyncio.sleep(2.0)
                    if user_id not in audio_stream_processor.user_languages:
                        # Re-fetch latest language prefs from DB before starting
                        try:
                            db_prefs = await audio_stream_processor._fetch_user_language_prefs(user_id)
                        except Exception:
                            db_prefs = None
                        latest_speaks = (db_prefs or {}).get('speaks_languages') or speaks_pref or []
                        latest_understands = (db_prefs or {}).get('understands_languages') or understands_pref or []
                        in_lang = (latest_speaks[0] if latest_speaks else 'en')
                        out_lang = (latest_understands[0] if latest_understands else 'en')
                        await audio_stream_processor.start_processing(
                            user_id,
                            room_id,
                            input_lang=in_lang,
                            output_lang=out_lang,
                            speaks_pref=latest_speaks,
                            understands_pref=latest_understands
                        )
                        logger.info("⏱️ init_settings timeout — starting with latest profile prefers speaks=%s → wants_to_hear=%s", latest_speaks, latest_understands)
                except Exception as _e:
                    logger.error("Auto-start fallback failed: %s", _e)
            asyncio.create_task(_delayed_autostart())
        
        # Main message loop
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(user_id, room_id, data)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # Cleanup on disconnect
        await audio_stream_processor.stop_processing(user_id)
        connection_manager.disconnect(user_id)
        
        # Notify all remaining participants that someone left
        participant_list = await get_participants_info(room_id)
        await connection_manager.broadcast_to_room(room_id, {
            "type": "participant_left",
            "user_id": str(user_id),
            "participants": participant_list
        }, exclude_user=None)


async def handle_websocket_message(user_id: UUID, room_id: str, data: dict):
    """Handle different types of WebSocket messages"""
    message_type = data.get("type")
    
    if message_type == "init_settings":
        input_lang = data.get("input_language", "auto")
        output_lang = data.get("output_language", "en")
        speaks_pref = data.get("speaks_languages")
        understands_pref = data.get("understands_languages")

        # Normalize short codes like 'pt-BR' -> 'pt'
        def _norm(code: str | None):
            if not code:
                return code
            return (code.split('-')[0] or code).lower()

        # Update user language preferences
        audio_stream_processor.update_user_language(
            user_id,
            _norm(input_lang),
            _norm(output_lang),
            speaks_pref=speaks_pref,
            understands_pref=understands_pref
        )

        # If processing hasn't started yet (was deferred), start now with normalized values
        if user_id not in audio_stream_processor.user_languages:
            await audio_stream_processor.start_processing(
                user_id,
                room_id,
                input_lang=_norm(input_lang or 'en'),
                output_lang=_norm(output_lang or 'en'),
                speaks_pref=speaks_pref,
                understands_pref=understands_pref
            )

        await connection_manager.send_personal_message(user_id, {
            "type": "language_updated",
            "input_language": _norm(input_lang),
            "output_language": _norm(output_lang),
            "message": "Initial language preferences applied"
        })
        logger.info(
            "✅ Initial language settings for user %s: speaks=%s, wants_to_hear=%s",
            user_id,
            input_lang,
            output_lang
        )
        return

    if message_type == "audio_chunk":
        # If processing was deferred and still not started, keep buffering but warn once
        if user_id not in audio_stream_processor.user_languages:
            if not hasattr(handle_websocket_message, "_warned_deferred"):
                logger.warning("🎙️ Received audio before init_settings; buffering until settings arrive for user %s", user_id)
                handle_websocket_message._warned_deferred = True
        await handle_audio_chunk(user_id, data)
    
    elif message_type == "language_update":
        await handle_language_update(user_id, data)
    
    elif message_type == "control":
        await handle_control_message(user_id, room_id, data)
    
    # WebRTC Signaling messages
    elif message_type == "webrtc_offer":
        await handle_webrtc_offer(user_id, room_id, data)
    
    elif message_type == "webrtc_answer":
        await handle_webrtc_answer(user_id, room_id, data)
    
    elif message_type == "ice_candidate":
        await handle_ice_candidate(user_id, room_id, data)
    
    else:
        logger.warning(f"⚠️ Unknown message type: {message_type}")


async def handle_audio_chunk(user_id: UUID, data: dict):
    """Handle incoming audio chunk from client"""
    try:
        audio_data = data.get("audio_data")
        if not audio_data:
            return

        # Debug instrumentation to track incoming payloads
        debug_counter = getattr(handle_audio_chunk, "_debug_counter", 0) + 1
        handle_audio_chunk._debug_counter = debug_counter
        if logger.isEnabledFor(logging.DEBUG) and debug_counter % 25 == 0:
            logger.debug(
                "[AudioDebug] Incoming chunk #%s from %s (payload_type=%s, payload_length=%s)",
                debug_counter,
                user_id,
                type(audio_data).__name__,
                len(audio_data) if hasattr(audio_data, "__len__") else "n/a"
            )

        if isinstance(audio_data, str) and audio_data.startswith("data:"):
            _, _, audio_data = audio_data.partition(",")

        try:
            if isinstance(audio_data, str):
                audio_bytes = base64.b64decode(audio_data)
            elif isinstance(audio_data, (bytes, bytearray)):
                audio_bytes = bytes(audio_data)
            else:
                logger.warning("Unsupported audio payload type: %s", type(audio_data))
                return
        except (base64.binascii.Error, ValueError) as exc:
            logger.warning("Invalid audio chunk received for user %s: %s", user_id, exc)
            return

        if not audio_bytes:
            return

        if logger.isEnabledFor(logging.DEBUG) and debug_counter % 25 == 0:
            logger.debug(
                "[AudioDebug] Chunk #%s decoded bytes=%s", debug_counter, len(audio_bytes)
            )

        # Add audio chunk to buffer for processing
        audio_chunk_manager.add_audio_chunk(user_id, audio_bytes)
        
        # Log chunk receipt (debug)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Received audio chunk from user {user_id}")
            
    except Exception as e:
        logger.error(f"Error handling audio chunk from user {user_id}: {e}")


async def handle_language_update(user_id: UUID, data: dict):
    """Handle language preference updates"""
    try:
        input_lang = data.get("input_language", "auto")
        output_lang = data.get("output_language", "en")
        speaks_pref = data.get("speaks_languages")
        understands_pref = data.get("understands_languages")
        
        # Update user language preferences
        audio_stream_processor.update_user_language(
            user_id,
            input_lang,
            output_lang,
            speaks_pref=speaks_pref,
            understands_pref=understands_pref
        )
        
        # Send confirmation
        await connection_manager.send_personal_message(user_id, {
            "type": "language_updated",
            "input_language": input_lang,
            "output_language": output_lang,
            "message": "Language preferences updated"
        })
        
        logger.info(
            f"✅ User {user_id} updated languages: speaks={input_lang}, wants_to_hear={output_lang}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error updating languages for user {user_id}: {e}")


async def handle_control_message(user_id: UUID, room_id: str, data: dict):
    """Handle control messages (mute, pause translation, etc.)"""
    try:
        action = data.get("action")
        
        if action == "mute":
            # Temporarily stop processing user's audio
            await audio_stream_processor.stop_processing(user_id)
            
            await connection_manager.send_personal_message(user_id, {
                "type": "mute_status",
                "muted": True,
                "message": "Audio translation muted"
            })
            
        elif action == "unmute":
            # Resume processing user's audio
            await audio_stream_processor.start_processing(user_id, room_id)
            
            await connection_manager.send_personal_message(user_id, {
                "type": "mute_status",
                "muted": False,
                "message": "Audio translation unmuted"
            })
            
        elif action == "pause_translation":
            # Pause translation but keep audio streaming
            # Implementation would track translation state
            await connection_manager.send_personal_message(user_id, {
                "type": "translation_status",
                "paused": True,
                "message": "Translation paused"
            })
            
        elif action == "resume_translation":
            await connection_manager.send_personal_message(user_id, {
                "type": "translation_status",
                "paused": False,
                "message": "Translation resumed"
            })
            
        else:
            logger.warning(f"Unknown control action: {action}")
            
    except Exception as e:
        logger.error(f"Error handling control message for user {user_id}: {e}")


async def handle_webrtc_offer(user_id: UUID, room_id: str, data: dict):
    """Handle WebRTC offer from a peer"""
    try:
        target_user_id = data.get("target_user_id")
        offer = data.get("offer")
        
        if not target_user_id or not offer:
            logger.warning(f"Invalid WebRTC offer from {user_id}")
            return
        
        target_uuid = UUID(target_user_id)
        
        # Forward the offer to the target user
        await connection_manager.send_personal_message(target_uuid, {
            "type": "webrtc_offer",
            "from_user_id": str(user_id),
            "offer": offer
        })
        
        logger.info(f"Forwarded WebRTC offer from {user_id} to {target_user_id}")
        
    except Exception as e:
        logger.error(f"Error handling WebRTC offer: {e}")


async def handle_webrtc_answer(user_id: UUID, room_id: str, data: dict):
    """Handle WebRTC answer from a peer"""
    try:
        target_user_id = data.get("target_user_id")
        answer = data.get("answer")
        
        if not target_user_id or not answer:
            logger.warning(f"Invalid WebRTC answer from {user_id}")
            return
        
        target_uuid = UUID(target_user_id)
        
        # Forward the answer to the target user
        await connection_manager.send_personal_message(target_uuid, {
            "type": "webrtc_answer",
            "from_user_id": str(user_id),
            "answer": answer
        })
        
        logger.info(f"Forwarded WebRTC answer from {user_id} to {target_user_id}")
        
    except Exception as e:
        logger.error(f"Error handling WebRTC answer: {e}")


async def handle_ice_candidate(user_id: UUID, room_id: str, data: dict):
    """Handle ICE candidate from a peer"""
    try:
        target_user_id = data.get("target_user_id")
        candidate = data.get("candidate")
        
        if not target_user_id or not candidate:
            logger.warning(f"Invalid ICE candidate from {user_id}")
            return
        
        target_uuid = UUID(target_user_id)
        
        # Forward the ICE candidate to the target user
        await connection_manager.send_personal_message(target_uuid, {
            "type": "ice_candidate",
            "from_user_id": str(user_id),
            "candidate": candidate
        })
        
        logger.debug(f"Forwarded ICE candidate from {user_id} to {target_user_id}")
        
    except Exception as e:
        logger.error(f"Error handling ICE candidate: {e}")


@router.websocket("/ws/status/{room_id}")
async def websocket_status_endpoint(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for room status updates
    (participant join/leave, translation status, etc.)
    """
    # Accept WebSocket connection first
    await websocket.accept()
    logger.info(f"✅ Status WebSocket connection accepted for room: {room_id}")
    
    try:
        user = await get_current_user_ws(websocket)
        if not user:
            logger.error("❌ Status WebSocket authentication failed")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        user_id = user.id
        logger.info(f"✅ Status WebSocket user authenticated: {user_id}")
    except HTTPException as e:
        logger.error(f"❌ Status WebSocket authentication HTTPException: {e.detail}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Store connection (don't call connect(), already accepted above)
    connection_manager.active_connections.setdefault(user_id, []).append(websocket)
    if room_id not in connection_manager.room_connections:
        connection_manager.room_connections[room_id] = []
    if user_id not in connection_manager.room_connections[room_id]:
        connection_manager.room_connections[room_id].append(user_id)
    connection_manager.user_rooms[user_id] = room_id
    
    try:
        # Send current room status
        room_users = connection_manager.get_room_users(room_id)
        await websocket.send_json({
            "type": "room_status",
            "room_id": room_id,
            "participants": [str(uid) for uid in room_users],
            "active_translations": len([uid for uid in room_users if uid in audio_stream_processor.user_languages])
        })
        
        # Listen for status updates
        while True:
            data = await websocket.receive_json()
            # Handle status-related messages
            
    except WebSocketDisconnect:
        logger.info(f"Status WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Status WebSocket error for user {user_id}: {e}")
    finally:
        connection_manager.disconnect(user_id)