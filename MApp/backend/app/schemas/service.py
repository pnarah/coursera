"""
Pydantic schemas for service operations.
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class ServiceResponse(BaseModel):
    """Schema for service response."""
    id: int
    hotel_id: int
    name: str
    service_type: str
    description: Optional[str] = None
    price: float
    is_available: bool
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class BookingServiceCreate(BaseModel):
    """Schema for adding a service to a booking at creation time."""
    service_id: int = Field(..., gt=0, description="ID of the service")
    quantity: int = Field(1, gt=0, description="Quantity of the service")
    notes: Optional[str] = Field(None, max_length=500, description="Special notes or instructions")
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is reasonable."""
        if v > 100:
            raise ValueError("Quantity cannot exceed 100")
        return v


class BookingServiceDetail(BaseModel):
    """Schema for booking service details in responses."""
    id: int
    service_id: int
    service_name: str
    service_type: str
    quantity: int
    unit_price: float
    total_price: float
    status: str
    notes: Optional[str] = None
    ordered_at: datetime
    
    model_config = {"from_attributes": True}
