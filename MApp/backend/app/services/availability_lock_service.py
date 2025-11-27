"""
Service layer for room availability locking using Redis.
"""
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, Tuple
from redis.asyncio import Redis

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hotel import Room, Hotel, Booking, BookingStatus, RoomType
from app.db.redis import get_redis


class AvailabilityLockService:
    """Service for managing room availability locks in Redis."""
    
    # Lock TTL: 2 minutes (120 seconds)
    LOCK_TTL_SECONDS = 120
    
    # Redis key prefix for locks
    LOCK_KEY_PREFIX = "availability_lock:"
    
    # Redis key prefix for tracking locked quantities per room type
    QUANTITY_KEY_PREFIX = "locked_quantity:"
    
    @staticmethod
    def _generate_lock_id() -> str:
        """Generate a unique lock ID."""
        return f"lock_{uuid.uuid4().hex}"
    
    @staticmethod
    def _get_lock_key(lock_id: str) -> str:
        """Get Redis key for a lock."""
        return f"{AvailabilityLockService.LOCK_KEY_PREFIX}{lock_id}"
    
    @staticmethod
    def _get_quantity_key(
        hotel_id: int,
        room_type: str,
        check_in_date: date,
        check_out_date: date
    ) -> str:
        """
        Get Redis key for tracking locked quantities.
        
        Format: locked_quantity:{hotel_id}:{room_type}:{check_in}:{check_out}
        """
        return (
            f"{AvailabilityLockService.QUANTITY_KEY_PREFIX}"
            f"{hotel_id}:{room_type}:{check_in_date}:{check_out_date}"
        )
    
    @staticmethod
    async def _get_available_room_count(
        db: AsyncSession,
        hotel_id: int,
        room_type: RoomType,
        check_in_date: date,
        check_out_date: date
    ) -> int:
        """
        Get count of available rooms for given criteria.
        
        A room is available if:
        1. It's the correct type and hotel
        2. It's active and available for booking
        3. It has no overlapping confirmed/checked-in bookings
        """
        # Get all rooms matching criteria
        rooms_query = (
            select(Room)
            .where(
                and_(
                    Room.hotel_id == hotel_id,
                    Room.room_type == room_type,
                    Room.is_active == True,
                    Room.is_available == True,
                )
            )
        )
        rooms_result = await db.execute(rooms_query)
        all_rooms = rooms_result.scalars().all()
        
        if not all_rooms:
            return 0
        
        # Get overlapping bookings
        overlapping_bookings_query = (
            select(Booking.room_id)
            .where(
                and_(
                    Booking.room_id.in_([room.id for room in all_rooms]),
                    Booking.check_in_date < check_out_date,
                    Booking.check_out_date > check_in_date,
                    or_(
                        Booking.status == BookingStatus.CONFIRMED,
                        Booking.status == BookingStatus.CHECKED_IN,
                    )
                )
            )
        )
        overlapping_result = await db.execute(overlapping_bookings_query)
        booked_room_ids = {row[0] for row in overlapping_result.all()}
        
        # Count available rooms
        available_count = len([room for room in all_rooms if room.id not in booked_room_ids])
        return available_count
    
    @staticmethod
    async def _get_locked_quantity(
        redis: Redis,
        hotel_id: int,
        room_type: str,
        check_in_date: date,
        check_out_date: date
    ) -> int:
        """Get currently locked quantity for given criteria."""
        quantity_key = AvailabilityLockService._get_quantity_key(
            hotel_id, room_type, check_in_date, check_out_date
        )
        
        locked_qty = await redis.get(quantity_key)
        return int(locked_qty) if locked_qty else 0
    
    @staticmethod
    async def _increment_locked_quantity(
        redis: Redis,
        hotel_id: int,
        room_type: str,
        check_in_date: date,
        check_out_date: date,
        quantity: int,
        ttl_seconds: int
    ) -> None:
        """Increment locked quantity and set TTL."""
        quantity_key = AvailabilityLockService._get_quantity_key(
            hotel_id, room_type, check_in_date, check_out_date
        )
        
        # Increment quantity
        await redis.incrby(quantity_key, quantity)
        
        # Set/update TTL (extend if key exists)
        await redis.expire(quantity_key, ttl_seconds)
    
    @staticmethod
    async def _decrement_locked_quantity(
        redis: Redis,
        hotel_id: int,
        room_type: str,
        check_in_date: date,
        check_out_date: date,
        quantity: int
    ) -> None:
        """Decrement locked quantity."""
        quantity_key = AvailabilityLockService._get_quantity_key(
            hotel_id, room_type, check_in_date, check_out_date
        )
        
        # Decrement quantity
        new_value = await redis.decrby(quantity_key, quantity)
        
        # If quantity reaches 0 or below, delete the key
        if new_value <= 0:
            await redis.delete(quantity_key)
    
    @staticmethod
    async def create_lock(
        db: AsyncSession,
        redis: Redis,
        hotel_id: int,
        room_type_str: str,
        check_in_date: date,
        check_out_date: date,
        quantity: int
    ) -> Tuple[str, datetime]:
        """
        Create a room availability lock.
        
        Returns:
            Tuple of (lock_id, expires_at)
            
        Raises:
            ValueError: If validation fails or insufficient rooms available
        """
        # Validate dates
        if check_out_date <= check_in_date:
            raise ValueError("Check-out date must be after check-in date")
        
        if check_in_date < date.today():
            raise ValueError("Check-in date cannot be in the past")
        
        # Validate and convert room type
        try:
            room_type = RoomType(room_type_str.lower())
        except ValueError:
            raise ValueError(
                f"Invalid room type: {room_type_str}. "
                f"Valid values: {[rt.value for rt in RoomType]}"
            )
        
        # Verify hotel exists
        hotel_query = select(Hotel).where(Hotel.id == hotel_id)
        hotel_result = await db.execute(hotel_query)
        hotel = hotel_result.scalar_one_or_none()
        
        if not hotel:
            raise ValueError(f"Hotel with ID {hotel_id} not found")
        
        # Get available room count
        available_count = await AvailabilityLockService._get_available_room_count(
            db, hotel_id, room_type, check_in_date, check_out_date
        )
        
        # Get currently locked quantity
        locked_quantity = await AvailabilityLockService._get_locked_quantity(
            redis, hotel_id, room_type_str.lower(), check_in_date, check_out_date
        )
        
        # Check if enough rooms available
        actually_available = available_count - locked_quantity
        if actually_available < quantity:
            raise ValueError(
                f"Insufficient rooms available. "
                f"Requested: {quantity}, Available: {actually_available} "
                f"(Total: {available_count}, Locked: {locked_quantity})"
            )
        
        # Generate lock ID
        lock_id = AvailabilityLockService._generate_lock_id()
        
        # Create lock data
        lock_data = {
            "lock_id": lock_id,
            "hotel_id": hotel_id,
            "room_type": room_type_str.lower(),
            "check_in_date": check_in_date.isoformat(),
            "check_out_date": check_out_date.isoformat(),
            "quantity": quantity,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Store lock in Redis with TTL
        lock_key = AvailabilityLockService._get_lock_key(lock_id)
        await redis.setex(
            lock_key,
            AvailabilityLockService.LOCK_TTL_SECONDS,
            json.dumps(lock_data)
        )
        
        # Increment locked quantity
        await AvailabilityLockService._increment_locked_quantity(
            redis,
            hotel_id,
            room_type_str.lower(),
            check_in_date,
            check_out_date,
            quantity,
            AvailabilityLockService.LOCK_TTL_SECONDS
        )
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(
            seconds=AvailabilityLockService.LOCK_TTL_SECONDS
        )
        
        return lock_id, expires_at
    
    @staticmethod
    async def release_lock(redis: Redis, lock_id: str) -> bool:
        """
        Release a room availability lock.
        
        Returns:
            True if lock was released, False if lock doesn't exist
        """
        lock_key = AvailabilityLockService._get_lock_key(lock_id)
        
        # Get lock data
        lock_data_json = await redis.get(lock_key)
        if not lock_data_json:
            return False
        
        # Parse lock data
        lock_data = json.loads(lock_data_json)
        
        # Decrement locked quantity
        await AvailabilityLockService._decrement_locked_quantity(
            redis,
            lock_data["hotel_id"],
            lock_data["room_type"],
            date.fromisoformat(lock_data["check_in_date"]),
            date.fromisoformat(lock_data["check_out_date"]),
            lock_data["quantity"]
        )
        
        # Delete lock
        await redis.delete(lock_key)
        
        return True
    
    @staticmethod
    async def get_lock_status(redis: Redis, lock_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a lock.
        
        Returns:
            Lock data if exists, None otherwise
        """
        lock_key = AvailabilityLockService._get_lock_key(lock_id)
        
        # Get lock data
        lock_data_json = await redis.get(lock_key)
        if not lock_data_json:
            return None
        
        # Parse lock data
        lock_data = json.loads(lock_data_json)
        
        # Get TTL
        ttl = await redis.ttl(lock_key)
        lock_data["ttl_seconds"] = ttl if ttl > 0 else 0
        
        return lock_data
    
    @staticmethod
    async def extend_lock(redis: Redis, lock_id: str, additional_seconds: int = None) -> bool:
        """
        Extend the TTL of an existing lock.
        
        Args:
            redis: Redis client
            lock_id: Lock ID to extend
            additional_seconds: Additional seconds to add (default: reset to LOCK_TTL_SECONDS)
            
        Returns:
            True if lock was extended, False if lock doesn't exist
        """
        lock_key = AvailabilityLockService._get_lock_key(lock_id)
        
        # Check if lock exists
        exists = await redis.exists(lock_key)
        if not exists:
            return False
        
        # Set new TTL
        new_ttl = additional_seconds if additional_seconds else AvailabilityLockService.LOCK_TTL_SECONDS
        await redis.expire(lock_key, new_ttl)
        
        return True
