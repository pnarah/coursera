"""
Service layer for room-related operations.
"""
from datetime import date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hotel import Room, Hotel, Location, Booking, BookingStatus, RoomType
from app.schemas.room import (
    RoomCreate,
    RoomUpdate,
    RoomSearchParams,
    AvailabilityCheckRequest,
    AvailableRoomResponse,
)


class RoomService:
    """Service class for room operations."""

    @staticmethod
    async def get_room_by_id(db: AsyncSession, room_id: int) -> Optional[Room]:
        """Get room by ID with hotel and location details."""
        query = (
            select(Room)
            .options(
                joinedload(Room.hotel).joinedload(Hotel.location)
            )
            .where(Room.id == room_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_rooms_by_hotel(
        db: AsyncSession,
        hotel_id: int,
        skip: int = 0,
        limit: int = 10,
        is_active_only: bool = True
    ) -> Tuple[List[Room], int]:
        """Get all rooms for a hotel with pagination."""
        # Build base query
        conditions = [Room.hotel_id == hotel_id]
        if is_active_only:
            conditions.append(Room.is_active == True)

        # Count query
        count_query = select(func.count(Room.id)).where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Data query
        query = (
            select(Room)
            .options(joinedload(Room.hotel).joinedload(Hotel.location))
            .where(and_(*conditions))
            .offset(skip)
            .limit(limit)
            .order_by(Room.room_number)
        )
        result = await db.execute(query)
        rooms = result.scalars().unique().all()

        return list(rooms), total

    @staticmethod
    async def search_rooms(
        db: AsyncSession,
        params: RoomSearchParams
    ) -> Tuple[List[Room], int]:
        """Search rooms with various filters."""
        conditions = []

        # Apply filters
        if params.hotel_id:
            conditions.append(Room.hotel_id == params.hotel_id)
        
        if params.room_type:
            # Convert string to RoomType enum (case-insensitive)
            try:
                room_type_enum = RoomType(params.room_type.lower())
                conditions.append(Room.room_type == room_type_enum)
            except ValueError:
                raise ValueError(f"Invalid room type: {params.room_type}. Valid values: {[rt.value for rt in RoomType]}")
        
        if params.min_capacity:
            conditions.append(Room.capacity >= params.min_capacity)
        
        if params.max_price:
            conditions.append(Room.base_price <= params.max_price)
        
        if params.min_price:
            conditions.append(Room.base_price >= params.min_price)
        
        if params.is_available is not None:
            conditions.append(Room.is_available == params.is_available)
        
        # Always show only active rooms
        conditions.append(Room.is_active == True)

        # City filter (requires join with hotel and location)
        if params.city:
            conditions.append(Location.city.ilike(f"%{params.city}%"))

        # Count query
        count_query = (
            select(func.count(Room.id))
            .join(Hotel, Room.hotel_id == Hotel.id)
            .join(Location, Hotel.location_id == Location.id)
            .where(and_(*conditions))
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Data query with eager loading
        query = (
            select(Room)
            .options(
                joinedload(Room.hotel).joinedload(Hotel.location)
            )
            .join(Hotel, Room.hotel_id == Hotel.id)
            .join(Location, Hotel.location_id == Location.id)
            .where(and_(*conditions))
            .offset(params.skip)
            .limit(params.limit)
            .order_by(Room.base_price)
        )
        result = await db.execute(query)
        rooms = result.scalars().unique().all()

        return list(rooms), total

    @staticmethod
    async def check_availability(
        db: AsyncSession,
        request: AvailabilityCheckRequest
    ) -> Tuple[List[AvailableRoomResponse], Hotel]:
        """
        Check room availability for given dates.
        
        Returns rooms that are NOT booked during the requested period.
        A room is available if it has no overlapping bookings with status:
        - CONFIRMED
        - CHECKED_IN
        
        Cancelled and completed (CHECKED_OUT) bookings don't block availability.
        """
        # Validate dates
        if request.check_out_date <= request.check_in_date:
            raise ValueError("Check-out date must be after check-in date")
        
        if request.check_in_date < date.today():
            raise ValueError("Check-in date cannot be in the past")

        # Get hotel details
        hotel_query = select(Hotel).where(Hotel.id == request.hotel_id)
        hotel_result = await db.execute(hotel_query)
        hotel = hotel_result.scalar_one_or_none()
        
        if not hotel:
            raise ValueError(f"Hotel with ID {request.hotel_id} not found")

        # Build conditions for room filtering
        room_conditions = [
            Room.hotel_id == request.hotel_id,
            Room.is_active == True,
            Room.is_available == True,
        ]

        if request.room_type:
            # Convert string to RoomType enum (case-insensitive)
            try:
                room_type_enum = RoomType(request.room_type.lower())
                room_conditions.append(Room.room_type == room_type_enum)
            except ValueError:
                raise ValueError(f"Invalid room type: {request.room_type}. Valid values: {[rt.value for rt in RoomType]}")
        
        if request.min_capacity:
            room_conditions.append(Room.capacity >= request.min_capacity)

        # Get all rooms matching criteria
        rooms_query = (
            select(Room)
            .where(and_(*room_conditions))
            .order_by(Room.room_type, Room.base_price)
        )
        rooms_result = await db.execute(rooms_query)
        all_rooms = rooms_result.scalars().all()

        if not all_rooms:
            return [], hotel

        # Get bookings that overlap with requested period
        # Booking overlaps if: 
        #   (booking.check_in < request.check_out) AND (booking.check_out > request.check_in)
        overlapping_bookings_query = (
            select(Booking.room_id)
            .where(
                and_(
                    Booking.room_id.in_([room.id for room in all_rooms]),
                    Booking.check_in_date < request.check_out_date,
                    Booking.check_out_date > request.check_in_date,
                    or_(
                        Booking.status == BookingStatus.CONFIRMED,
                        Booking.status == BookingStatus.CHECKED_IN,
                    )
                )
            )
        )
        overlapping_result = await db.execute(overlapping_bookings_query)
        booked_room_ids = {row[0] for row in overlapping_result.all()}

        # Filter out booked rooms
        available_rooms = [
            AvailableRoomResponse(
                room_id=room.id,
                room_number=room.room_number,
                room_type=room.room_type,
                capacity=room.capacity,
                base_price=room.base_price,
                amenities=room.amenities,
                floor_number=room.floor_number,
            )
            for room in all_rooms
            if room.id not in booked_room_ids
        ]

        return available_rooms, hotel

    @staticmethod
    async def create_room(db: AsyncSession, room_data: RoomCreate) -> Room:
        """Create a new room."""
        # Verify hotel exists
        hotel_query = select(Hotel).where(Hotel.id == room_data.hotel_id)
        hotel_result = await db.execute(hotel_query)
        hotel = hotel_result.scalar_one_or_none()
        
        if not hotel:
            raise ValueError(f"Hotel with ID {room_data.hotel_id} not found")

        # Check if room number already exists for this hotel
        existing_room_query = select(Room).where(
            and_(
                Room.hotel_id == room_data.hotel_id,
                Room.room_number == room_data.room_number
            )
        )
        existing_result = await db.execute(existing_room_query)
        if existing_result.scalar_one_or_none():
            raise ValueError(
                f"Room number {room_data.room_number} already exists for this hotel"
            )

        # Create room
        room = Room(**room_data.model_dump())
        db.add(room)
        await db.commit()
        await db.refresh(room)

        return room

    @staticmethod
    async def update_room(
        db: AsyncSession,
        room_id: int,
        room_data: RoomUpdate
    ) -> Optional[Room]:
        """Update room details."""
        room = await RoomService.get_room_by_id(db, room_id)
        if not room:
            return None

        # Update only provided fields
        update_data = room_data.model_dump(exclude_unset=True)
        
        # If updating room number, check for duplicates
        if "room_number" in update_data and update_data["room_number"] != room.room_number:
            existing_room_query = select(Room).where(
                and_(
                    Room.hotel_id == room.hotel_id,
                    Room.room_number == update_data["room_number"],
                    Room.id != room_id
                )
            )
            existing_result = await db.execute(existing_room_query)
            if existing_result.scalar_one_or_none():
                raise ValueError(
                    f"Room number {update_data['room_number']} already exists for this hotel"
                )

        for field, value in update_data.items():
            setattr(room, field, value)

        await db.commit()
        await db.refresh(room)

        return room

    @staticmethod
    async def delete_room(db: AsyncSession, room_id: int) -> bool:
        """
        Soft delete a room (set is_active to False).
        
        Returns True if deleted, False if room not found.
        """
        room = await RoomService.get_room_by_id(db, room_id)
        if not room:
            return False

        room.is_active = False
        await db.commit()
        return True
