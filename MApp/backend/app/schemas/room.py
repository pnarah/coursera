"""
Pydantic schemas for room-related operations.
"""
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.hotel import RoomType


class RoomBase(BaseModel):
    """Base room schema with common fields."""
    room_number: str = Field(..., description="Room number")
    room_type: RoomType = Field(..., description="Type of room")
    floor_number: Optional[int] = Field(None, description="Floor number")
    capacity: int = Field(..., ge=1, description="Maximum guest capacity")
    base_price: float = Field(..., gt=0, description="Base price per night")
    description: Optional[str] = Field(None, description="Room description")
    amenities: Optional[str] = Field(None, description="Comma-separated amenities")


class RoomCreate(RoomBase):
    """Schema for creating a new room."""
    hotel_id: int = Field(..., description="Hotel ID this room belongs to")
    is_available: bool = Field(True, description="Whether room is available for booking")
    is_active: bool = Field(True, description="Whether room is active")


class RoomUpdate(BaseModel):
    """Schema for updating room details."""
    room_number: Optional[str] = None
    room_type: Optional[RoomType] = None
    floor_number: Optional[int] = None
    capacity: Optional[int] = Field(None, ge=1)
    base_price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    amenities: Optional[str] = None
    is_available: Optional[bool] = None
    is_active: Optional[bool] = None


class RoomResponse(RoomBase):
    """Schema for room response."""
    id: int
    hotel_id: int
    is_available: bool
    is_active: bool
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class RoomWithHotelResponse(RoomResponse):
    """Schema for room response with hotel details."""
    hotel_name: str = Field(..., description="Hotel name")
    hotel_star_rating: int = Field(..., description="Hotel star rating")
    city: str = Field(..., description="City where hotel is located")


class RoomSearchParams(BaseModel):
    """Schema for room search parameters."""
    hotel_id: Optional[int] = Field(None, description="Filter by hotel ID")
    room_type: Optional[str] = Field(None, description="Filter by room type")
    min_capacity: Optional[int] = Field(None, ge=1, description="Minimum guest capacity")
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price per night")
    min_price: Optional[float] = Field(None, gt=0, description="Minimum price per night")
    is_available: Optional[bool] = Field(None, description="Filter by availability")
    city: Optional[str] = Field(None, description="Filter by city")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of records to return")


class AvailabilityCheckRequest(BaseModel):
    """Schema for checking room availability."""
    hotel_id: int = Field(..., description="Hotel ID to check")
    check_in_date: date = Field(..., description="Check-in date")
    check_out_date: date = Field(..., description="Check-out date")
    room_type: Optional[str] = Field(None, description="Specific room type to check")
    min_capacity: Optional[int] = Field(None, ge=1, description="Minimum guest capacity needed")


class AvailableRoomResponse(BaseModel):
    """Schema for available room in availability check."""
    room_id: int
    room_number: str
    room_type: RoomType
    capacity: int
    base_price: float
    amenities: Optional[str]
    floor_number: Optional[int]


class AvailabilityResponse(BaseModel):
    """Schema for availability check response."""
    hotel_id: int
    hotel_name: str
    check_in_date: date
    check_out_date: date
    nights: int
    available_rooms: List[AvailableRoomResponse]
    total_available: int


class RoomListResponse(BaseModel):
    """Schema for paginated room list response."""
    rooms: List[RoomWithHotelResponse]
    total: int
    skip: int
    limit: int
