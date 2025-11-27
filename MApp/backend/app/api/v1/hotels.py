"""
Hotels API endpoints.
Provides hotel search, listing, and detail operations.
"""
from datetime import date
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.hotel import HotelSearchParams, HotelSearchResponse, HotelDetailResponse, LocationResponse
from app.services.hotel_service import HotelService


router = APIRouter(prefix="/hotels", tags=["hotels"])


@router.get(
    "/search",
    response_model=HotelSearchResponse,
    summary="Search hotels with filters",
    description="""
    Search and list hotels with various filters.
    
    Features:
    - Filter by city (partial match, case-insensitive)
    - Filter by check-in/check-out dates
    - Filter by number of guests (capacity filter)
    - Filter by star rating
    - Filter by price range
    - Pagination support
    - Dynamic pricing calculation
    - Real-time availability checking
    
    Returns hotels with minimum room price for the specified dates.
    If no dates provided, returns base room prices.
    """
)
async def search_hotels(
    city: Optional[str] = Query(None, description="City name (partial match)"),
    check_in: Optional[date] = Query(None, description="Check-in date (YYYY-MM-DD)"),
    check_out: Optional[date] = Query(None, description="Check-out date (YYYY-MM-DD)"),
    guests: Optional[int] = Query(None, description="Number of guests", ge=1, le=20),
    min_price: Optional[Decimal] = Query(None, description="Minimum price per night", ge=0),
    max_price: Optional[Decimal] = Query(None, description="Maximum price per night", ge=0),
    star_rating: Optional[int] = Query(None, description="Hotel star rating", ge=1, le=5),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(10, description="Results per page", ge=1, le=50),
    db: AsyncSession = Depends(get_db)
) -> HotelSearchResponse:
    """
    Search hotels with filters and pagination.
    
    Args:
        city: City name filter
        check_in: Check-in date
        check_out: Check-out date
        guests: Number of guests
        min_price: Minimum price filter
        max_price: Maximum price filter
        star_rating: Hotel star rating
        page: Page number
        page_size: Results per page
        db: Database session
        
    Returns:
        HotelSearchResponse with hotels and pagination info
    """
    # Validate date range if both provided
    if check_in and check_out and check_out <= check_in:
        raise HTTPException(
            status_code=400,
            detail="check_out must be after check_in"
        )
    
    # Create search params
    params = HotelSearchParams(
        city=city,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        min_price=min_price,
        max_price=max_price,
        star_rating=star_rating,
        page=page,
        page_size=page_size
    )
    
    # Execute search
    hotel_service = HotelService(db)
    return await hotel_service.search_hotels(params)


@router.get(
    "/{hotel_id}",
    response_model=HotelDetailResponse,
    summary="Get hotel details",
    description="Get detailed information about a specific hotel including location and room count."
)
async def get_hotel(
    hotel_id: int,
    db: AsyncSession = Depends(get_db)
) -> HotelDetailResponse:
    """
    Get hotel details by ID.
    
    Args:
        hotel_id: Hotel ID
        db: Database session
        
    Returns:
        HotelDetailResponse with full hotel details
    """
    hotel_service = HotelService(db)
    hotel = await hotel_service.get_hotel_by_id(hotel_id)
    
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    
    # Count total rooms
    from sqlalchemy import select, func
    from app.models.hotel import Room
    
    rooms_count_query = select(func.count(Room.id)).where(Room.hotel_id == hotel_id)
    result = await db.execute(rooms_count_query)
    total_rooms = result.scalar() or 0
    
    # Build response
    return HotelDetailResponse(
        id=hotel.id,
        name=hotel.name,
        description=hotel.description,
        location_id=hotel.location_id,
        location=LocationResponse(
            id=hotel.location.id,
            name=hotel.location.city,
            state=hotel.location.state,
            country=hotel.location.country
        ),
        address=hotel.address,
        latitude=Decimal(str(hotel.latitude)) if hotel.latitude else None,
        longitude=Decimal(str(hotel.longitude)) if hotel.longitude else None,
        star_rating=hotel.star_rating,
        contact_number=hotel.contact_number,
        email=hotel.email,
        check_in_time=hotel.check_in_time,
        check_out_time=hotel.check_out_time,
        is_active=hotel.is_active,
        total_rooms=total_rooms
    )
