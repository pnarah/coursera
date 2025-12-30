"""Vendor-specific schemas for dashboard and analytics."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class VendorHotelItem(BaseModel):
    """Schema for a single hotel in vendor's portfolio"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    address: str
    location: Optional[str] = None
    star_rating: Optional[int] = None
    total_rooms: int
    total_employees: int


class VendorHotelsResponse(BaseModel):
    """Schema for vendor hotels list response"""
    hotels: List[VendorHotelItem]


class VendorAnalyticsResponse(BaseModel):
    """Schema for vendor analytics response"""
    total_bookings: int
    total_revenue: float
    total_guests: int
