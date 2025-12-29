import uuid
import json
from datetime import datetime, timedelta
from redis.asyncio import Redis
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from fastapi import Request
import logging

from app.models.hotel import UserSession, User, UserRole
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing user sessions in Redis and PostgreSQL."""
    
    SESSION_PREFIX = "session"
    USER_SESSIONS_PREFIX = "user_sessions"
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def get_session_timeout(role: UserRole) -> int:
        """Get session timeout based on user role (in seconds)"""
        timeouts = {
            UserRole.GUEST: settings.SESSION_TIMEOUT_GUEST,
            UserRole.HOTEL_EMPLOYEE: settings.SESSION_TIMEOUT_EMPLOYEE,
            UserRole.VENDOR_ADMIN: settings.SESSION_TIMEOUT_VENDOR,
            UserRole.SYSTEM_ADMIN: settings.SESSION_TIMEOUT_ADMIN,
        }
        return timeouts.get(role, settings.SESSION_TIMEOUT_GUEST)
    
    @staticmethod
    def get_max_sessions(role: UserRole) -> int:
        """Get maximum allowed sessions based on user role"""
        max_sessions = {
            UserRole.GUEST: settings.MAX_SESSIONS_GUEST,
            UserRole.HOTEL_EMPLOYEE: settings.MAX_SESSIONS_EMPLOYEE,
            UserRole.VENDOR_ADMIN: settings.MAX_SESSIONS_VENDOR,
            UserRole.SYSTEM_ADMIN: settings.MAX_SESSIONS_ADMIN,
        }
        return max_sessions.get(role, settings.MAX_SESSIONS_GUEST)
    
    @staticmethod
    def _extract_device_info(request: Request) -> str:
        """Extract device information from request"""
        user_agent = request.headers.get("user-agent", "")
        
        # Simple device detection
        if "Mobile" in user_agent:
            if "iPhone" in user_agent:
                return "iPhone"
            elif "Android" in user_agent:
                return "Android"
            return "Mobile"
        elif "iPad" in user_agent:
            return "iPad"
        elif "Macintosh" in user_agent:
            return "Mac"
        elif "Windows" in user_agent:
            return "Windows"
        elif "Linux" in user_agent:
            return "Linux"
        
        return "Unknown"
    
    @staticmethod
    def _session_key(user_id: int, session_id: str) -> str:
        """Generate Redis key for session data."""
        return f"{SessionService.SESSION_PREFIX}:{user_id}:{session_id}"
    
    @staticmethod
    def _user_sessions_key(user_id: int) -> str:
        """Generate Redis key for user's session list."""
        return f"{SessionService.USER_SESSIONS_PREFIX}:{user_id}"
    
    async def enforce_max_sessions(self, redis: Redis, user: User):
        """Ensure user doesn't exceed maximum session limit"""
        sessions = await self.get_user_sessions(user.id)
        max_allowed = self.get_max_sessions(user.role)
        
        if len(sessions) >= max_allowed:
            # Remove oldest session
            oldest = sessions[-1]
            await self.invalidate_session(
                redis=redis,
                session_id=str(oldest.id),
                reason="max_sessions_exceeded"
            )
            logger.info(f"Removed oldest session {oldest.id} for user {user.id} - max sessions exceeded")
    
    async def create_session(
        self,
        redis: Redis,
        user: User,
        access_token: str,
        refresh_token: str,
        request: Request
    ) -> UserSession:
        """Create a new session for user with role-based timeout"""
        # Enforce max sessions
        await self.enforce_max_sessions(redis, user)
        
        # Get device info
        device_info = self._extract_device_info(request)
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # Calculate expiry based on role
        timeout = self.get_session_timeout(user.role)
        expires_at = datetime.utcnow() + timedelta(seconds=timeout)
        
        # Create session in database
        session = UserSession(
            user_id=user.id,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            is_active=True
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        # Store session in Redis
        session_data = {
            "user_id": user.id,
            "session_id": str(session.id),
            "role": user.role.value,
            "hotel_id": user.hotel_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "last_activity": datetime.utcnow().isoformat(),
            "device_info": device_info,
            "ip_address": ip_address
        }
        
        redis_key = self._session_key(user.id, str(session.id))
        await redis.setex(
            redis_key,
            timeout,
            json.dumps(session_data)
        )
        
        logger.info(f"Session created: {session.id} for user: {user.id} ({user.role.value})")
        return session
    
    async def get_session(self, redis: Redis, user_id: int, session_id: str) -> Optional[Dict]:
        """Get session from Redis"""
        redis_key = self._session_key(user_id, session_id)
        session_data = await redis.get(redis_key)
        
        if session_data:
            return json.loads(session_data)
        return None
    
    async def update_activity(self, redis: Redis, user_id: int, session_id: str):
        """Update last activity timestamp"""
        redis_key = self._session_key(user_id, session_id)
        session_data = await redis.get(redis_key)
        
        if session_data:
            data = json.loads(session_data)
            data["last_activity"] = datetime.utcnow().isoformat()
            
            # Get remaining TTL
            ttl = await redis.ttl(redis_key)
            if ttl > 0:
                await redis.setex(redis_key, ttl, json.dumps(data))
            
            # Update database
            stmt = select(UserSession).where(UserSession.id == uuid.UUID(session_id))
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                session.last_activity = datetime.utcnow()
                await self.db.commit()
    
    async def invalidate_session(
        self,
        redis: Redis,
        session_id: str,
        reason: str = "user_logout"
    ):
        """Invalidate a specific session"""
        # Convert string to UUID
        try:
            session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id}")
            return
        
        # Get session from database
        stmt = select(UserSession).where(UserSession.id == session_uuid)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            # Update database
            session.is_active = False
            session.invalidated_at = datetime.utcnow()
            session.invalidation_reason = reason
            await self.db.commit()
            
            # Remove from Redis
            redis_key = self._session_key(session.user_id, str(session_uuid))
            await redis.delete(redis_key)
            
            logger.info(f"Session invalidated: {session_id}, reason: {reason}")
    
    async def invalidate_all_user_sessions(
        self,
        redis: Redis,
        user_id: int,
        except_session_id: Optional[str] = None,
        reason: str = "security_event"
    ) -> int:
        """Invalidate all sessions for a user, returns count of invalidated sessions"""
        # Get all active sessions
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        
        if except_session_id:
            try:
                except_uuid = uuid.UUID(except_session_id)
                stmt = stmt.where(UserSession.id != except_uuid)
            except ValueError:
                pass
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        for session in sessions:
            await self.invalidate_session(redis, str(session.id), reason)
        
        logger.info(f"Invalidated {len(sessions)} sessions for user {user_id}, reason: {reason}")
        return len(sessions)
    
    async def get_user_sessions(self, user_id: int, active_only: bool = True) -> List[UserSession]:
        """Get sessions for a user"""
        conditions = [UserSession.user_id == user_id]
        
        if active_only:
            conditions.extend([
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ])
        
        stmt = select(UserSession).where(and_(*conditions)).order_by(UserSession.last_activity.desc())
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def verify_session(redis: Redis, user_id: int, session_id: str) -> bool:
        """Verify if a session is valid and active"""
        redis_key = SessionService._session_key(user_id, session_id)
        session_data = await redis.get(redis_key)
        return session_data is not None
    
    @staticmethod
    async def update_last_active(redis: Redis, user_id: int, session_id: str):
        """Update last activity timestamp for a session"""
        redis_key = SessionService._session_key(user_id, session_id)
        session_data = await redis.get(redis_key)
        
        if session_data:
            data = json.loads(session_data)
            data["last_activity"] = datetime.utcnow().isoformat()
            
            # Get TTL and rewrite with updated data
            ttl = await redis.ttl(redis_key)
            if ttl > 0:
                await redis.setex(redis_key, ttl, json.dumps(data))
    
    async def refresh_session(
        self,
        redis: Redis,
        user: User,
        session_id: uuid.UUID,
        new_access_token: str
    ):
        """Refresh session with new access token"""
        redis_key = self._session_key(user.id, str(session_id))
        session_data = await redis.get(redis_key)
        
        if session_data:
            data = json.loads(session_data)
            data["access_token"] = new_access_token
            data["last_activity"] = datetime.utcnow().isoformat()
            
            # Extend expiry
            timeout = self.get_session_timeout(user.role)
            await redis.setex(redis_key, timeout, json.dumps(data))
            
            # Update database
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                session.expires_at = datetime.utcnow() + timedelta(seconds=timeout)
                session.last_activity = datetime.utcnow()
                await self.db.commit()
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions (background job)"""
        # Delete from database
        stmt = delete(UserSession).where(
            and_(
                UserSession.is_active == True,
                UserSession.expires_at < datetime.utcnow()
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} expired sessions")
        return deleted_count
    
    @staticmethod
    async def verify_session(redis: Redis, user_id: int, session_id: str) -> bool:
        """Verify if a session is valid and active"""
        redis_key = SessionService._session_key(user_id, session_id)
        session_data = await redis.get(redis_key)
        return session_data is not None
    
    @staticmethod
    async def update_last_active(redis: Redis, user_id: int, session_id: str):
        """Update last activity timestamp for a session"""
        redis_key = SessionService._session_key(user_id, session_id)
        session_data = await redis.get(redis_key)
        
        if session_data:
            data = json.loads(session_data)
            data["last_activity"] = datetime.utcnow().isoformat()
            
            # Get TTL and rewrite with updated data
            ttl = await redis.ttl(redis_key)
            if ttl > 0:
                await redis.setex(redis_key, ttl, json.dumps(data))
