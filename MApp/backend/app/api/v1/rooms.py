"""
API endpoints for room operations.
"""
from typing import List
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.room_service import RoomService
from app.schemas.room import (
    RoomResponse,
    RoomWithHotelResponse,
    RoomSearchParams,
    AvailabilityCheckRequest,
    AvailabilityResponse,
    AvailableRoomResponse,
    RoomListResponse,
)

router = APIRouter()


@router.get("/rooms/types", response_model=List[str])
async def get_room_types():
    """
    Get all available room types.
    
    Returns a list of valid room type values.
    """
    from app.models.hotel import RoomType
    return [room_type.value for room_type in RoomType]


@router.get("/rooms/search", response_model=RoomListResponse)
async def search_rooms(
    hotel_id: int = Query(None, description="Filter by hotel ID"),
    room_type: str = Query(None, description="Filter by room type (SINGLE, DOUBLE, DELUXE, SUITE, FAMILY)"),
    min_capacity: int = Query(None, ge=1, description="Minimum guest capacity"),
    max_price: float = Query(None, gt=0, description="Maximum price per night"),
    min_price: float = Query(None, gt=0, description="Minimum price per night"),
    is_available: bool = Query(None, description="Filter by availability"),
    city: str = Query(None, description="Filter by city name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for rooms with various filters.
    
    All filters are optional. Returns rooms matching all specified criteria.
    
    - **hotel_id**: Specific hotel to search in
    - **room_type**: Type of room (SINGLE, DOUBLE, DELUXE, SUITE, FAMILY)
    - **min_capacity**: Minimum number of guests the room can accommodate
    - **max_price**: Maximum price per night
    - **min_price**: Minimum price per night
    - **is_available**: Only show available/unavailable rooms
    - **city**: Search by city name (partial match)
    - **skip**: Pagination offset
    - **limit**: Maximum results to return
    """
    # Build search parameters
    params = RoomSearchParams(
        hotel_id=hotel_id,
        room_type=room_type,
        min_capacity=min_capacity,
        max_price=max_price,
        min_price=min_price,
        is_available=is_available,
        city=city,
        skip=skip,
        limit=limit,
    )

    try:
        rooms, total = await RoomService.search_rooms(db, params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Transform to response format
    room_responses = [
        RoomWithHotelResponse(
            id=room.id,
            hotel_id=room.hotel_id,
            room_number=room.room_number,
            room_type=room.room_type,
            floor_number=room.floor_number,
            capacity=room.capacity,
            base_price=room.base_price,
            description=room.description,
            amenities=room.amenities,
            is_available=room.is_available,
            is_active=room.is_active,
            created_at=room.created_at.isoformat(),
            updated_at=room.updated_at.isoformat(),
            hotel_name=room.hotel.name,
            hotel_star_rating=room.hotel.star_rating,
            city=room.hotel.location.city,
        )
        for room in rooms
    ]

    return RoomListResponse(
        rooms=room_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/hotels/{hotel_id}/rooms", response_model=RoomListResponse)
async def list_hotel_rooms(
    hotel_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all rooms for a specific hotel.
    
    - **hotel_id**: Hotel ID to get rooms for
    - **skip**: Pagination offset
    - **limit**: Maximum number of rooms to return
    """
    rooms, total = await RoomService.get_rooms_by_hotel(
        db=db,
        hotel_id=hotel_id,
        skip=skip,
        limit=limit
    )

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No rooms found for hotel ID {hotel_id}"
        )

    # Transform to response format
    room_responses = [
        RoomWithHotelResponse(
            id=room.id,
            hotel_id=room.hotel_id,
            room_number=room.room_number,
            room_type=room.room_type,
            floor_number=room.floor_number,
            capacity=room.capacity,
            base_price=room.base_price,
            description=room.description,
            amenities=room.amenities,
            is_available=room.is_available,
            is_active=room.is_active,
            created_at=room.created_at.isoformat(),
            updated_at=room.updated_at.isoformat(),
            hotel_name=room.hotel.name,
            hotel_star_rating=room.hotel.star_rating,
            city=room.hotel.location.city,
        )
        for room in rooms
    ]

    return RoomListResponse(
        rooms=room_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/rooms/{room_id}", response_model=RoomWithHotelResponse)
async def get_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific room.
    
    - **room_id**: Room ID to retrieve
    """
    room = await RoomService.get_room_by_id(db, room_id)

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found"
        )

    return RoomWithHotelResponse(
        id=room.id,
        hotel_id=room.hotel_id,
        room_number=room.room_number,
        room_type=room.room_type,
        floor_number=room.floor_number,
        capacity=room.capacity,
        base_price=room.base_price,
        description=room.description,
        amenities=room.amenities,
        is_available=room.is_available,
        is_active=room.is_active,
        created_at=room.created_at.isoformat(),
        updated_at=room.updated_at.isoformat(),
        hotel_name=room.hotel.name,
        hotel_star_rating=room.hotel.star_rating,
        city=room.hotel.location.city,
    )


@router.post("/rooms/availability", response_model=AvailabilityResponse)
async def check_availability(
    request: AvailabilityCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Check room availability for specific dates.
    
    Returns all available rooms for the given hotel and date range.
    A room is available if it has no confirmed or checked-in bookings
    that overlap with the requested period.
    
    - **hotel_id**: Hotel to check availability for
    - **check_in_date**: Desired check-in date (YYYY-MM-DD)
    - **check_out_date**: Desired check-out date (YYYY-MM-DD)
    - **room_type**: Optional - filter by specific room type
    - **min_capacity**: Optional - minimum guest capacity needed
    """
    try:
        available_rooms, hotel = await RoomService.check_availability(db, request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking availability: {str(e)}"
        )

    # Calculate number of nights
    nights = (request.check_out_date - request.check_in_date).days

    return AvailabilityResponse(
        hotel_id=hotel.id,
        hotel_name=hotel.name,
        check_in_date=request.check_in_date,
        check_out_date=request.check_out_date,
        nights=nights,
        available_rooms=available_rooms,
        total_available=len(available_rooms),
    )
