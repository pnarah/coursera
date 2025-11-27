"""
Pydantic schemas for dynamic pricing engine.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.config.pricing_config import Season, DiscountType


class PriceQuoteRequest(BaseModel):
    """Request for a price quote"""
    hotel_id: int = Field(..., description="Hotel ID", gt=0)
    room_type: str = Field(..., description="Room type (single, double, suite, etc.)")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    quantity: int = Field(1, description="Number of rooms", ge=1, le=10)
    discount_type: DiscountType = Field(
        DiscountType.NONE,
        description="Discount type to apply (if applicable)"
    )
    
    @field_validator("check_out")
    @classmethod
    def validate_checkout_after_checkin(cls, v: date, info) -> date:
        """Ensure check-out is after check-in"""
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("check_out must be after check_in")
        return v


class PriceBreakdown(BaseModel):
    """Detailed breakdown of price calculation"""
    base_price: Decimal = Field(..., description="Base room price per night")
    nights: int = Field(..., description="Number of nights")
    quantity: int = Field(..., description="Number of rooms")
    
    # Multipliers and their values
    season: Season = Field(..., description="Season classification")
    season_multiplier: float = Field(..., description="Season pricing multiplier")
    
    occupancy_rate: float = Field(..., description="Hotel occupancy rate (0.0-1.0)")
    occupancy_multiplier: float = Field(..., description="Occupancy surge multiplier")
    
    discount_type: DiscountType = Field(..., description="Applied discount type")
    discount_multiplier: float = Field(..., description="Discount multiplier (1.0 = no discount)")
    discount_reason: str = Field(..., description="Human-readable discount reason")
    
    # Price calculation stages
    price_after_season: Decimal = Field(..., description="base_price * season_multiplier")
    price_after_occupancy: Decimal = Field(..., description="price_after_season * occupancy_multiplier")
    price_after_discount: Decimal = Field(..., description="price_after_occupancy * discount_multiplier")
    
    # Final prices
    price_per_night: Decimal = Field(..., description="Final price per room per night")
    subtotal: Decimal = Field(..., description="price_per_night * nights * quantity")
    tax_rate: float = Field(0.10, description="Tax rate (default 10%)")
    tax_amount: Decimal = Field(..., description="Tax amount")
    total_price: Decimal = Field(..., description="Final price including tax")
    
    class Config:
        json_schema_extra = {
            "example": {
                "base_price": "150.00",
                "nights": 3,
                "quantity": 2,
                "season": "high",
                "season_multiplier": 1.25,
                "occupancy_rate": 0.75,
                "occupancy_multiplier": 1.2,
                "discount_type": "early_bird",
                "discount_multiplier": 0.9,
                "discount_reason": "Early bird (30+ days advance)",
                "price_after_season": "187.50",
                "price_after_occupancy": "225.00",
                "price_after_discount": "202.50",
                "price_per_night": "202.50",
                "subtotal": "1215.00",
                "tax_rate": 0.10,
                "tax_amount": "121.50",
                "total_price": "1336.50"
            }
        }


class PriceQuoteResponse(BaseModel):
    """Response for price quote request"""
    hotel_id: int
    hotel_name: str
    room_type: str
    check_in: date
    check_out: date
    quantity: int
    available: bool
    available_rooms: int
    breakdown: Optional[PriceBreakdown] = None
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "hotel_id": 1,
                "hotel_name": "Grand Plaza Hotel",
                "room_type": "deluxe",
                "check_in": "2024-07-15",
                "check_out": "2024-07-18",
                "quantity": 2,
                "available": True,
                "available_rooms": 5,
                "breakdown": {
                    "base_price": "150.00",
                    "nights": 3,
                    "quantity": 2,
                    "season": "high",
                    "season_multiplier": 1.25,
                    "occupancy_rate": 0.75,
                    "occupancy_multiplier": 1.2,
                    "discount_type": "early_bird",
                    "discount_multiplier": 0.9,
                    "discount_reason": "Early bird (30+ days advance)",
                    "price_after_season": "187.50",
                    "price_after_occupancy": "225.00",
                    "price_after_discount": "202.50",
                    "price_per_night": "202.50",
                    "subtotal": "1215.00",
                    "tax_rate": 0.10,
                    "tax_amount": "121.50",
                    "total_price": "1336.50"
                },
                "message": None
            }
        }


class SimplePriceResponse(BaseModel):
    """Simplified price response for quick lookups"""
    room_type: str
    price_per_night: Decimal
    total_price: Decimal
    available: bool
