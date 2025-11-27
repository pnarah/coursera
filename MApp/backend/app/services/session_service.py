import uuid
import json
from datetime import datetime
from redis.asyncio import Redis
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing user sessions in Redis."""
    
    SESSION_PREFIX = "session"
    USER_SESSIONS_PREFIX = "user_sessions"
    SESSION_TTL = 7 * 24 * 60 * 60  # 7 days (matches refresh token)
    
    @staticmethod
    def _session_key(user_id: str, session_id: str) -> str:
        """Generate Redis key for session data."""
        return f"{SessionService.SESSION_PREFIX}:{user_id}:{session_id}"
    
    @staticmethod
    def _user_sessions_key(user_id: str) -> str:
        """Generate Redis key for user's session list."""
        return f"{SessionService.USER_SESSIONS_PREFIX}:{user_id}"
    
    @staticmethod
    async def create_session(
        redis: Redis,
        user_id: str,
        device_info: str,
        ip_address: Optional[str] = None,
        refresh_token: Optional[str] = None
    ) -> str:
        """
        Create a new session for user.
        
        Args:
            redis: Redis client
            user_id: User identifier (mobile number)
            device_info: Device information
            ip_address: IP address of the request
            refresh_token: Refresh token associated with session
            
        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "device_info": device_info,
            "ip_address": ip_address or "unknown",
            "created_at": now,
            "last_active": now,
            "refresh_token": refresh_token
        }
        
        # Store session data
        session_key = SessionService._session_key(user_id, session_id)
        await redis.setex(
            session_key,
            SessionService.SESSION_TTL,
            json.dumps(session_data)
        )
        
        # Add session to user's session list (sorted set with timestamp)
        user_sessions_key = SessionService._user_sessions_key(user_id)
        await redis.zadd(user_sessions_key, {session_id: datetime.utcnow().timestamp()})
        await redis.expire(user_sessions_key, SessionService.SESSION_TTL)
        
        logger.info(f"Session created: {session_id} for user: {user_id[:4]}***")
        return session_id
    
    @staticmethod
    async def get_session(redis: Redis, user_id: str, session_id: str) -> Optional[Dict]:
        """Get session data."""
        session_key = SessionService._session_key(user_id, session_id)
        session_data = await redis.get(session_key)
        
        if session_data:
            return json.loads(session_data)
        return None
    
    @staticmethod
    async def update_last_active(redis: Redis, user_id: str, session_id: str) -> None:
        """Update session's last active timestamp."""
        session = await SessionService.get_session(redis, user_id, session_id)
        if session:
            session["last_active"] = datetime.utcnow().isoformat()
            session_key = SessionService._session_key(user_id, session_id)
            await redis.setex(
                session_key,
                SessionService.SESSION_TTL,
                json.dumps(session)
            )
    
    @staticmethod
    async def list_sessions(redis: Redis, user_id: str) -> List[Dict]:
        """List all active sessions for a user."""
        user_sessions_key = SessionService._user_sessions_key(user_id)
        session_ids = await redis.zrange(user_sessions_key, 0, -1)
        
        sessions = []
        for session_id in session_ids:
            session = await SessionService.get_session(redis, user_id, session_id)
            if session:
                sessions.append(session)
        
        # Sort by last_active descending
        sessions.sort(key=lambda x: x.get("last_active", ""), reverse=True)
        return sessions
    
    @staticmethod
    async def revoke_session(redis: Redis, user_id: str, session_id: str) -> bool:
        """
        Revoke a specific session.
        
        Returns:
            True if session was revoked, False if not found
        """
        session_key = SessionService._session_key(user_id, session_id)
        user_sessions_key = SessionService._user_sessions_key(user_id)
        
        # Check if session exists
        session_exists = await redis.exists(session_key)
        if not session_exists:
            return False
        
        # Delete session data
        await redis.delete(session_key)
        
        # Remove from user's session list
        await redis.zrem(user_sessions_key, session_id)
        
        logger.info(f"Session revoked: {session_id} for user: {user_id[:4]}***")
        return True
    
    @staticmethod
    async def revoke_all_sessions(redis: Redis, user_id: str) -> int:
        """
        Revoke all sessions for a user.
        
        Returns:
            Number of sessions revoked
        """
        sessions = await SessionService.list_sessions(redis, user_id)
        count = 0
        
        for session in sessions:
            session_id = session.get("session_id")
            if session_id:
                await SessionService.revoke_session(redis, user_id, session_id)
                count += 1
        
        logger.info(f"All sessions revoked for user: {user_id[:4]}*** (count: {count})")
        return count
    
    @staticmethod
    async def verify_session(redis: Redis, user_id: str, session_id: str) -> bool:
        """Verify if a session is valid and active."""
        session = await SessionService.get_session(redis, user_id, session_id)
        return session is not None
