from fastapi import APIRouter, Depends, HTTPException, status, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import OTPRequest, OTPVerify, TokenResponse, OTPResponse
from app.schemas.session import SessionListResponse, SessionResponse
from app.services.otp_service import OTPService
from app.services.session_service import SessionService
from app.core.security import create_access_token, create_refresh_token
from app.db.redis import get_redis
from app.db.session import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/send-otp", response_model=OTPResponse, status_code=status.HTTP_200_OK)
async def send_otp(
    request: OTPRequest,
    redis: Redis = Depends(get_redis)
):
    """
    Send OTP to mobile number.
    
    Rate limited to 3 requests per 30 minutes per mobile number.
    """
    # Check rate limit
    within_limit = await OTPService.check_rate_limit(
        redis,
        request.mobile_number,
        max_attempts=settings.RATE_LIMIT_OTP_PER_MOBILE,
        window=settings.RATE_LIMIT_WINDOW_SECONDS
    )
    
    if not within_limit:
        remaining = await OTPService.get_remaining_attempts(
            redis,
            request.mobile_number,
            max_attempts=settings.RATE_LIMIT_OTP_PER_MOBILE
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many OTP requests. Please try again later. Remaining attempts: {remaining}"
        )
    
    # Generate OTP (use fixed OTP for test number in debug mode)
    if settings.DEBUG and request.mobile_number == "5551234567":
        otp = "123456"  # Fixed OTP for testing
    else:
        otp = OTPService.generate_otp(settings.OTP_LENGTH)
    
    # Store OTP in Redis
    await OTPService.store_otp(
        redis,
        request.mobile_number,
        otp,
        ttl=settings.OTP_EXPIRE_SECONDS
    )
    
    # Send OTP via SMS (mock)
    sms_sent = await OTPService.send_otp_sms(
        f"{request.country_code}{request.mobile_number}",
        otp
    )
    
    if not sms_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )
    
    return OTPResponse(
        message="OTP sent successfully",
        expires_in=settings.OTP_EXPIRE_SECONDS,
        mobile_number=request.mobile_number
    )


@router.post("/verify-otp", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def verify_otp(
    request_data: OTPVerify,
    http_request: Request,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and return JWT tokens with session creation.
    
    Returns access token (15 min) and refresh token (7 days).
    Creates a new session in Redis for session management.
    Creates user if doesn't exist.
    """
    # Verify OTP
    is_valid = await OTPService.verify_otp(
        redis,
        request_data.mobile_number,
        request_data.otp
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
    
    # Get or create user
    from sqlalchemy import select
    from app.models.hotel import User
    
    user_query = select(User).where(User.mobile_number == request_data.mobile_number)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            mobile_number=request_data.mobile_number,
            country_code="+1",  # Default country code
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    user_id = request_data.mobile_number
    
    # Create session
    ip_address = http_request.client.host if http_request.client else None
    session_id = await SessionService.create_session(
        redis=redis,
        user_id=user_id,
        device_info=request_data.device_info,
        ip_address=ip_address
    )
    
    # Generate tokens with session_id
    user_data = {
        "sub": user_id,
        "mobile": user_id,
        "device": request_data.device_info,
        "session_id": session_id
    }
    
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token({"sub": user_id, "session_id": session_id})
    
    # Update session with refresh token
    session = await SessionService.get_session(redis, user_id, session_id)
    if session:
        session["refresh_token"] = refresh_token
        import json
        await redis.setex(
            f"session:{user_id}:{session_id}",
            SessionService.SESSION_TTL,
            json.dumps(session)
        )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/sessions", response_model=SessionListResponse, status_code=status.HTTP_200_OK)
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
):
    """
    List all active sessions for the authenticated user.
    
    Shows device info, IP address, and timestamps for each session.
    """
    user_id = current_user["user_id"]
    current_session_id = current_user.get("session_id")
    
    sessions = await SessionService.list_sessions(redis, user_id)
    
    from datetime import datetime
    session_responses = [
        SessionResponse(
            session_id=s["session_id"],
            device_info=s["device_info"],
            ip_address=s.get("ip_address"),
            created_at=datetime.fromisoformat(s["created_at"]),
            last_active=datetime.fromisoformat(s["last_active"]),
            is_current=(s["session_id"] == current_session_id)
        )
        for s in sessions
    ]
    
    return SessionListResponse(
        sessions=session_responses,
        total_count=len(session_responses)
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
):
    """
    Revoke a specific session by session ID.
    
    The user can revoke any of their own sessions.
    """
    user_id = current_user["user_id"]
    
    revoked = await SessionService.revoke_session(redis, user_id, session_id)
    
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {
        "message": "Session revoked successfully",
        "session_id": session_id
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
):
    """
    Logout from current session.
    
    Revokes the current session only.
    """
    user_id = current_user["user_id"]
    session_id = current_user.get("session_id")
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active session found"
        )
    
    await SessionService.revoke_session(redis, user_id, session_id)
    
    return {
        "message": "Logged out successfully"
    }


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all(
    current_user: dict = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
):
    """
    Logout from all sessions.
    
    Revokes all sessions for the authenticated user.
    """
    user_id = current_user["user_id"]
    
    count = await SessionService.revoke_all_sessions(redis, user_id)
    
    return {
        "message": f"Logged out from all devices successfully",
        "sessions_revoked": count
    }
