"""
Pricing API endpoints.
Provides dynamic pricing quotes based on availability, season, and occupancy.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.pricing import PriceQuoteRequest, PriceQuoteResponse
from app.services.pricing_service import PricingService


router = APIRouter(prefix="/availability", tags=["pricing"])


@router.post(
    "/quote",
    response_model=PriceQuoteResponse,
    summary="Get price quote for room booking",
    description="""
    Get a detailed price quote for a room booking with dynamic pricing.
    
    Price is calculated based on:
    - Base room price
    - Season multiplier (peak/high/regular/low)
    - Occupancy surge pricing (higher demand = higher price)
    - Discount eligibility (early bird, last minute, extended stay)
    
    Returns availability status and full price breakdown showing all applied factors.
    """
)
async def get_price_quote(
    request: PriceQuoteRequest,
    db: AsyncSession = Depends(get_db)
) -> PriceQuoteResponse:
    """
    Get a price quote for a room booking.
    
    Args:
        request: Quote request with hotel, room type, dates, quantity
        db: Database session
        
    Returns:
        Price quote with availability and detailed breakdown
    """
    pricing_service = PricingService(db)
    return await pricing_service.get_price_quote(request)
