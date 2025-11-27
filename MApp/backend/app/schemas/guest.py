"""
Schemas for guest management.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class GuestCreate(BaseModel):
    """Schema for creating a guest during booking."""
    guest_name: str = Field(..., min_length=1, max_length=255, description="Full name of the guest")
    guest_email: Optional[str] = Field(None, max_length=255, description="Email address of the guest")
    guest_phone: Optional[str] = Field(None, max_length=20, description="Phone number of the guest")
    age: Optional[int] = Field(None, ge=0, le=150, description="Age of the guest")
    id_type: Optional[str] = Field(None, max_length=50, description="Type of ID document (passport, driver_license, national_id, etc.)")
    id_number: Optional[str] = Field(None, max_length=100, description="ID document number")
    is_primary: bool = Field(default=False, description="Whether this is the primary guest")
    
    @field_validator('guest_name')
    @classmethod
    def validate_guest_name(cls, v: str) -> str:
        """Validate guest name is not empty after stripping."""
        if not v.strip():
            raise ValueError('Guest name cannot be empty')
        return v.strip()
    
    @field_validator('id_number')
    @classmethod
    def validate_id_with_type(cls, v: Optional[str], info) -> Optional[str]:
        """If id_number is provided, id_type must also be provided."""
        if v and not info.data.get('id_type'):
            raise ValueError('id_type is required when id_number is provided')
        return v


class GuestResponse(BaseModel):
    """Schema for guest response."""
    id: int
    booking_id: int
    guest_name: str
    guest_email: Optional[str]
    guest_phone: Optional[str]
    age: Optional[int]
    id_type: Optional[str]
    id_number: Optional[str]
    is_primary: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GuestDetail(BaseModel):
    """Detailed guest information for booking details."""
    guest_name: str
    guest_email: Optional[str]
    guest_phone: Optional[str]
    age: Optional[int]
    is_primary: bool
