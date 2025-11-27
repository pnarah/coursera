from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from typing import Optional

from app.core.security import verify_token
from app.db.redis import get_redis
from app.services.session_service import SessionService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis)
) -> dict:
    """
    Dependency to get current authenticated user from JWT token.
    
    Validates token and optionally checks session validity.
    """
    token = credentials.credentials
    
    # Verify JWT token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Optional: Verify session if session_id is in token
    session_id = payload.get("session_id")
    if session_id:
        session_valid = await SessionService.verify_session(redis, user_id, session_id)
        if not session_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last active timestamp
        await SessionService.update_last_active(redis, user_id, session_id)
    
    return {
        "user_id": user_id,
        "mobile": payload.get("mobile"),
        "device": payload.get("device"),
        "session_id": session_id
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    redis: Redis = Depends(get_redis)
) -> Optional[dict]:
    """
    Dependency to optionally get current user.
    Returns None if no valid token provided.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, redis)
    except HTTPException:
        return None
