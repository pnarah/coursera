"""
Pydantic schemas for booking operations.
"""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.guest import GuestCreate, GuestDetail
from app.schemas.service import BookingServiceCreate, BookingServiceDetail


class BookingCreate(BaseModel):
    """Schema for creating a new booking."""
    hotel_id: int = Field(..., gt=0, description="ID of the hotel")
    room_type: str = Field(..., description="Type of room (single, double, deluxe, suite, family)")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    guests: int = Field(..., gt=0, description="Number of guests")
    lock_id: str = Field(..., description="Availability lock ID obtained from lock endpoint")
    
    # Guest details (backwards compatibility - can be omitted if guest_list is provided)
    guest_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Primary guest full name (optional if guest_list provided)")
    guest_email: Optional[str] = Field(None, max_length=255, description="Guest email address")
    guest_phone: Optional[str] = Field(None, max_length=20, description="Guest phone number")
    special_requests: Optional[str] = Field(None, description="Special requests or notes")
    
    # New guest list support
    guest_list: Optional[List[GuestCreate]] = Field(None, description="List of guests (recommended approach)")
    
    # Pre-service booking support
    pre_services: Optional[List[BookingServiceCreate]] = Field(None, description="List of services to book with the reservation")
    
    @field_validator('room_type')
    @classmethod
    def validate_room_type(cls, v: str) -> str:
        """Validate room type is one of the allowed values."""
        allowed = ['single', 'double', 'deluxe', 'suite', 'family']
        if v.lower() not in allowed:
            raise ValueError(f"Room type must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @field_validator('check_out')
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        """Validate check-out is after check-in."""
        check_in = info.data.get('check_in')
        if check_in and v <= check_in:
            raise ValueError("Check-out date must be after check-in date")
        return v
    
    @model_validator(mode='after')
    def validate_guests(self):
        """Validate guest information."""
        # Ensure either guest_name or guest_list is provided
        if not self.guest_name and not self.guest_list:
            raise ValueError("Either guest_name or guest_list must be provided")
        
        # If guest_list is provided, validate it
        if self.guest_list:
            if len(self.guest_list) == 0:
                raise ValueError("guest_list cannot be empty")
            
            # Validate guest count matches
            if len(self.guest_list) != self.guests:
                raise ValueError(f"Number of guests in guest_list ({len(self.guest_list)}) must match guests count ({self.guests})")
            
            # Ensure at least one primary guest
            primary_guests = [g for g in self.guest_list if g.is_primary]
            if len(primary_guests) == 0:
                raise ValueError("At least one guest must be marked as primary")
            if len(primary_guests) > 1:
                raise ValueError("Only one guest can be marked as primary")
        
        return self


class BookingResponse(BaseModel):
    """Schema for booking response after creation."""
    booking_id: int
    booking_reference: str
    status: str
    hotel_id: int
    hotel_name: str
    room_type: str
    check_in: date
    check_out: date
    guests: int
    guest_name: str
    total_amount: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookingDetail(BaseModel):
    """Schema for detailed booking information."""
    booking_id: int
    booking_reference: str
    status: str
    
    # Hotel and room info
    hotel_id: int
    hotel_name: str
    hotel_address: str
    room_id: int
    room_type: str
    room_number: str
    
    # Dates and guests
    check_in: date
    check_out: date
    guests: int
    
    # Guest details
    guest_name: str
    guest_email: Optional[str]
    guest_phone: Optional[str]
    special_requests: Optional[str]
    guest_details: Optional[List[GuestDetail]] = Field(None, description="List of all guests")
    
    # Service details
    booking_services: Optional[List[BookingServiceDetail]] = Field(None, description="List of all booked services")
    
    # Financial
    total_amount: Decimal
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BookingListItem(BaseModel):
    """Schema for booking list items (simplified)."""
    booking_id: int
    booking_reference: str
    status: str
    hotel_name: str
    room_type: str
    check_in: date
    check_out: date
    total_amount: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    """Schema for paginated booking list."""
    bookings: list[BookingListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
