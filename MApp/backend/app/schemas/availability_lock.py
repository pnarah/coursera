"""
Pydantic schemas for room availability locking.
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class AvailabilityLockRequest(BaseModel):
    """Request to lock room availability."""
    hotel_id: int = Field(..., description="Hotel ID")
    room_type: str = Field(..., description="Room type to lock (SINGLE, DOUBLE, DELUXE, SUITE, FAMILY)")
    check_in_date: date = Field(..., description="Check-in date")
    check_out_date: date = Field(..., description="Check-out date")
    quantity: int = Field(..., ge=1, le=10, description="Number of rooms to lock (max 10)")


class AvailabilityLockResponse(BaseModel):
    """Response after locking availability."""
    lock_id: str = Field(..., description="Unique lock identifier")
    hotel_id: int
    room_type: str
    check_in_date: date
    check_out_date: date
    quantity: int
    expires_at: datetime = Field(..., description="Lock expiration timestamp")
    ttl_seconds: int = Field(..., description="Time to live in seconds")


class AvailabilityReleaseRequest(BaseModel):
    """Request to release a lock."""
    lock_id: str = Field(..., description="Lock ID to release")


class AvailabilityReleaseResponse(BaseModel):
    """Response after releasing a lock."""
    lock_id: str
    released: bool = Field(..., description="Whether the lock was successfully released")
    message: str = Field(..., description="Status message")


class LockStatusResponse(BaseModel):
    """Response for checking lock status."""
    lock_id: str
    exists: bool = Field(..., description="Whether the lock exists")
    hotel_id: Optional[int] = None
    room_type: Optional[str] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    quantity: Optional[int] = None
    ttl_seconds: Optional[int] = Field(None, description="Remaining time to live in seconds")
