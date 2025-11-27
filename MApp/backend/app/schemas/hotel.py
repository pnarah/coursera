"""
Pydantic schemas for hotel operations.
"""
from datetime import date, time
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class HotelSearchParams(BaseModel):
    """Parameters for hotel search"""
    city: Optional[str] = Field(None, description="City name to filter hotels")
    check_in: Optional[date] = Field(None, description="Check-in date")
    check_out: Optional[date] = Field(None, description="Check-out date")
    guests: Optional[int] = Field(None, description="Number of guests", ge=1, le=20)
    min_price: Optional[Decimal] = Field(None, description="Minimum price filter", ge=0)
    max_price: Optional[Decimal] = Field(None, description="Maximum price filter", ge=0)
    star_rating: Optional[int] = Field(None, description="Hotel star rating", ge=1, le=5)
    page: int = Field(1, description="Page number", ge=1)
    page_size: int = Field(10, description="Results per page", ge=1, le=50)
    
    @field_validator("check_out")
    @classmethod
    def validate_checkout_after_checkin(cls, v: Optional[date], info) -> Optional[date]:
        """Ensure check-out is after check-in if both provided"""
        if v and "check_in" in info.data and info.data["check_in"]:
            if v <= info.data["check_in"]:
                raise ValueError("check_out must be after check_in")
        return v


class LocationResponse(BaseModel):
    """Location details"""
    id: int
    name: str
    state: Optional[str] = None
    country: str
    
    class Config:
        from_attributes = True


class HotelSummary(BaseModel):
    """Hotel summary for search results"""
    id: int
    name: str
    description: Optional[str] = None
    address: str
    city: str
    state: Optional[str] = None
    country: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    star_rating: int
    contact_number: Optional[str] = None
    email: Optional[str] = None
    check_in_time: Optional[time] = None
    check_out_time: Optional[time] = None
    min_price: Optional[Decimal] = Field(None, description="Minimum room price per night for the search dates")
    available_rooms: Optional[int] = Field(None, description="Number of available rooms")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Grand Manhattan Hotel",
                "description": "Luxury hotel in the heart of Manhattan",
                "address": "123 5th Avenue",
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "latitude": "40.7580",
                "longitude": "-73.9855",
                "star_rating": 5,
                "contact_number": "+1-212-555-0100",
                "email": "info@grandmanhattan.com",
                "check_in_time": "15:00:00",
                "check_out_time": "11:00:00",
                "min_price": "500.00",
                "available_rooms": 15
            }
        }


class HotelSearchResponse(BaseModel):
    """Response for hotel search with pagination"""
    hotels: List[HotelSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "hotels": [
                    {
                        "id": 1,
                        "name": "Grand Manhattan Hotel",
                        "description": "Luxury hotel in the heart of Manhattan",
                        "address": "123 5th Avenue",
                        "city": "New York",
                        "state": "NY",
                        "country": "USA",
                        "star_rating": 5,
                        "min_price": "500.00",
                        "available_rooms": 15
                    }
                ],
                "total": 25,
                "page": 1,
                "page_size": 10,
                "total_pages": 3
            }
        }


class HotelDetailResponse(BaseModel):
    """Detailed hotel information"""
    id: int
    name: str
    description: Optional[str] = None
    location_id: int
    location: LocationResponse
    address: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    star_rating: int
    contact_number: Optional[str] = None
    email: Optional[str] = None
    check_in_time: Optional[time] = None
    check_out_time: Optional[time] = None
    is_active: bool
    total_rooms: int
    available_rooms: Optional[int] = None
    
    class Config:
        from_attributes = True
