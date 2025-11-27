"""
API endpoints for room availability locking.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.db.session import get_db
from app.db.redis import get_redis
from app.services.availability_lock_service import AvailabilityLockService
from app.schemas.availability_lock import (
    AvailabilityLockRequest,
    AvailabilityLockResponse,
    AvailabilityReleaseRequest,
    AvailabilityReleaseResponse,
    LockStatusResponse,
)

router = APIRouter()


@router.post("/availability/lock", response_model=AvailabilityLockResponse, status_code=status.HTTP_201_CREATED)
async def lock_availability(
    request: AvailabilityLockRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Lock room availability to prevent race conditions during booking.
    
    Creates a temporary lock on the specified number of rooms for the given
    hotel, room type, and date range. The lock expires after 2 minutes (120 seconds).
    
    **Use case**: Call this endpoint before starting the booking process to ensure
    rooms remain available while the user completes their reservation.
    
    **Lock behavior**:
    - Validates room availability before creating lock
    - Considers existing locks from other users
    - Automatically expires after TTL (2 minutes)
    - Tracks locked quantities per room type and date range
    
    **Parameters**:
    - **hotel_id**: ID of the hotel
    - **room_type**: Type of room (SINGLE, DOUBLE, DELUXE, SUITE, FAMILY) - case insensitive
    - **check_in_date**: Check-in date (YYYY-MM-DD)
    - **check_out_date**: Check-out date (YYYY-MM-DD)
    - **quantity**: Number of rooms to lock (1-10)
    
    **Returns**:
    - **lock_id**: Unique identifier for this lock (use for release)
    - **expires_at**: When the lock will automatically expire
    - **ttl_seconds**: Time to live in seconds
    
    **Errors**:
    - 400: Invalid dates, room type, or insufficient rooms available
    - 404: Hotel not found
    """
    try:
        lock_id, expires_at = await AvailabilityLockService.create_lock(
            db=db,
            redis=redis,
            hotel_id=request.hotel_id,
            room_type_str=request.room_type,
            check_in_date=request.check_in_date,
            check_out_date=request.check_out_date,
            quantity=request.quantity,
        )
        
        return AvailabilityLockResponse(
            lock_id=lock_id,
            hotel_id=request.hotel_id,
            room_type=request.room_type.lower(),
            check_in_date=request.check_in_date,
            check_out_date=request.check_out_date,
            quantity=request.quantity,
            expires_at=expires_at,
            ttl_seconds=AvailabilityLockService.LOCK_TTL_SECONDS,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating lock: {str(e)}"
        )


@router.post("/availability/release", response_model=AvailabilityReleaseResponse)
async def release_availability(
    request: AvailabilityReleaseRequest,
    redis: Redis = Depends(get_redis),
):
    """
    Release a room availability lock.
    
    Call this endpoint to manually release a lock before it expires. This should be done:
    - After successfully completing a booking
    - When a user cancels the booking process
    - On booking form errors or abandonment
    
    **Note**: Locks auto-expire after 2 minutes if not released manually.
    
    **Parameters**:
    - **lock_id**: The lock ID returned from the lock endpoint
    
    **Returns**:
    - **released**: Whether the lock was successfully released
    - **message**: Status message
    
    **Behavior**:
    - Returns success even if lock doesn't exist (idempotent)
    - Immediately frees the locked room quantity
    """
    try:
        released = await AvailabilityLockService.release_lock(redis, request.lock_id)
        
        if released:
            return AvailabilityReleaseResponse(
                lock_id=request.lock_id,
                released=True,
                message="Lock released successfully"
            )
        else:
            return AvailabilityReleaseResponse(
                lock_id=request.lock_id,
                released=False,
                message="Lock not found (may have already expired)"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error releasing lock: {str(e)}"
        )


@router.get("/availability/lock/{lock_id}", response_model=LockStatusResponse)
async def get_lock_status(
    lock_id: str,
    redis: Redis = Depends(get_redis),
):
    """
    Check the status of an availability lock.
    
    Use this endpoint to verify if a lock still exists and check its remaining TTL.
    
    **Parameters**:
    - **lock_id**: The lock ID to check
    
    **Returns**:
    - Lock details if it exists
    - **exists**: False if lock doesn't exist or has expired
    """
    try:
        lock_data = await AvailabilityLockService.get_lock_status(redis, lock_id)
        
        if lock_data:
            from datetime import date
            return LockStatusResponse(
                lock_id=lock_id,
                exists=True,
                hotel_id=lock_data["hotel_id"],
                room_type=lock_data["room_type"],
                check_in_date=date.fromisoformat(lock_data["check_in_date"]),
                check_out_date=date.fromisoformat(lock_data["check_out_date"]),
                quantity=lock_data["quantity"],
                ttl_seconds=lock_data.get("ttl_seconds", 0),
            )
        else:
            return LockStatusResponse(
                lock_id=lock_id,
                exists=False,
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking lock status: {str(e)}"
        )


@router.post("/availability/lock/{lock_id}/extend")
async def extend_lock(
    lock_id: str,
    redis: Redis = Depends(get_redis),
):
    """
    Extend the TTL of an existing lock.
    
    Resets the lock's TTL back to 2 minutes. Useful when a booking is taking
    longer than expected but the user is still actively working on it.
    
    **Parameters**:
    - **lock_id**: The lock ID to extend
    
    **Returns**:
    - Success message if extended
    - 404 if lock doesn't exist
    """
    try:
        extended = await AvailabilityLockService.extend_lock(redis, lock_id)
        
        if extended:
            return {
                "lock_id": lock_id,
                "extended": True,
                "message": f"Lock TTL extended to {AvailabilityLockService.LOCK_TTL_SECONDS} seconds",
                "new_ttl_seconds": AvailabilityLockService.LOCK_TTL_SECONDS,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lock not found or has expired"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extending lock: {str(e)}"
        )
