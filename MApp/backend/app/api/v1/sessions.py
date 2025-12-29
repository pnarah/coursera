from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.schemas.session import SessionListResponse, SessionResponse
from app.services.session_service import SessionService
from app.db.redis import get_redis
from app.db.session import get_db
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=List[SessionResponse], status_code=status.HTTP_200_OK)
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    List all active sessions for the current user.
    
    Returns session details including:
    - Session ID
    - Device information
    - IP address
    - Creation time
    - Last activity
    - Expiration time
    """
    user_id = current_user["user_id"]
    
    # Get session service
    session_service = SessionService(db)
    
    # Get all active sessions
    sessions = await session_service.get_user_sessions(user_id, active_only=True)
    
    # Format response
    session_list = []
    for session in sessions:
        session_list.append(SessionResponse(
            id=str(session.id),
            device_info=session.device_info,
            ip_address=session.ip_address,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            is_current=(str(session.id) == current_user.get("session_id"))
        ))
    
    return session_list


@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Delete (invalidate) a specific session.
    
    The user can delete any of their sessions except the current one.
    To logout from the current session, use the /auth/logout endpoint.
    """
    user_id = current_user["user_id"]
    current_session_id = current_user.get("session_id")
    
    # Prevent deleting current session
    if session_id == current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete current session. Use /auth/logout to end your current session."
        )
    
    # Get session service
    session_service = SessionService(db)
    
    # Verify session belongs to user
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    # Get all user sessions to verify ownership
    user_sessions = await session_service.get_user_sessions(user_id, active_only=False)
    session_exists = any(str(s.id) == session_id for s in user_sessions)
    
    if not session_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or does not belong to you"
        )
    
    # Invalidate the session
    await session_service.invalidate_session(
        redis=redis,
        session_id=session_id,
        reason="user_revoked"
    )
    
    return {
        "message": "Session deleted successfully",
        "session_id": session_id
    }


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_all_sessions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Delete (invalidate) all sessions except the current one.
    
    Useful for security purposes when you suspect unauthorized access.
    This will log out all other devices while keeping your current session active.
    """
    user_id = current_user["user_id"]
    current_session_id = current_user.get("session_id")
    
    # Get session service
    session_service = SessionService(db)
    
    # Invalidate all sessions except current
    invalidated_count = await session_service.invalidate_all_user_sessions(
        redis=redis,
        user_id=user_id,
        except_session_id=current_session_id,
        reason="user_revoked_all"
    )
    
    return {
        "message": f"Successfully deleted {invalidated_count} session(s)",
        "sessions_deleted": invalidated_count,
        "current_session_preserved": True
    }
