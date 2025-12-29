"""Location schemas for API responses."""
from pydantic import BaseModel, Field


class CityInfo(BaseModel):
    """Schema for city information."""
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State/province name")
    country: str = Field(..., description="Country name")
    hotel_count: int = Field(..., description="Number of hotels in this city")
    
    model_config = {"from_attributes": True}


class CitiesResponse(BaseModel):
    """Schema for cities list response."""
    cities: list[CityInfo] = Field(..., description="List of cities with hotels")
    total: int = Field(..., description="Total number of cities")
