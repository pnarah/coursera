"""
Pricing service for dynamic pricing engine.
Calculates room prices based on season, occupancy, and discounts.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.hotel import Hotel, Room, Booking, RoomType, BookingStatus
from app.schemas.pricing import (
    PriceQuoteRequest,
    PriceQuoteResponse,
    PriceBreakdown
)
from app.config.pricing_config import (
    Season,
    DiscountType,
    get_season_for_date,
    get_occupancy_multiplier,
    calculate_discount_multiplier,
    SEASON_MULTIPLIERS
)


class PricingService:
    """Service for calculating dynamic room prices"""
    
    DEFAULT_TAX_RATE = 0.10  # 10% tax
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_price_quote(
        self,
        request: PriceQuoteRequest
    ) -> PriceQuoteResponse:
        """
        Get a price quote for a room booking with full breakdown.
        
        Args:
            request: Price quote request with dates, room type, quantity
            
        Returns:
            PriceQuoteResponse with availability and price breakdown
        """
        # Validate and get hotel
        hotel = await self._get_hotel(request.hotel_id)
        if not hotel:
            return PriceQuoteResponse(
                hotel_id=request.hotel_id,
                hotel_name="Unknown",
                room_type=request.room_type,
                check_in=request.check_in,
                check_out=request.check_out,
                quantity=request.quantity,
                available=False,
                available_rooms=0,
                message="Hotel not found"
            )
        
        # Convert room type string to enum
        try:
            room_type_enum = RoomType[request.room_type.upper()]
        except KeyError:
            return PriceQuoteResponse(
                hotel_id=request.hotel_id,
                hotel_name=hotel.name,
                room_type=request.room_type,
                check_in=request.check_in,
                check_out=request.check_out,
                quantity=request.quantity,
                available=False,
                available_rooms=0,
                message=f"Invalid room type: {request.room_type}"
            )
        
        # Check availability
        available_rooms = await self._get_available_room_count(
            hotel_id=request.hotel_id,
            room_type=room_type_enum,
            check_in=request.check_in,
            check_out=request.check_out
        )
        
        if available_rooms < request.quantity:
            return PriceQuoteResponse(
                hotel_id=request.hotel_id,
                hotel_name=hotel.name,
                room_type=request.room_type,
                check_in=request.check_in,
                check_out=request.check_out,
                quantity=request.quantity,
                available=False,
                available_rooms=available_rooms,
                message=f"Insufficient rooms available. Requested: {request.quantity}, Available: {available_rooms}"
            )
        
        # Get base price for room type
        base_price = await self._get_base_price(request.hotel_id, room_type_enum)
        
        # Calculate occupancy rate for the hotel
        occupancy_rate = await self._calculate_occupancy_rate(
            hotel_id=request.hotel_id,
            check_in=request.check_in,
            check_out=request.check_out
        )
        
        # Calculate price breakdown
        breakdown = self._calculate_price_breakdown(
            base_price=base_price,
            check_in=request.check_in,
            check_out=request.check_out,
            quantity=request.quantity,
            occupancy_rate=occupancy_rate,
            discount_type=request.discount_type
        )
        
        return PriceQuoteResponse(
            hotel_id=request.hotel_id,
            hotel_name=hotel.name,
            room_type=request.room_type,
            check_in=request.check_in,
            check_out=request.check_out,
            quantity=request.quantity,
            available=True,
            available_rooms=available_rooms,
            breakdown=breakdown
        )
    
    async def _get_hotel(self, hotel_id: int) -> Optional[Hotel]:
        """Get hotel by ID"""
        result = await self.db.execute(
            select(Hotel).where(Hotel.id == hotel_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_available_room_count(
        self,
        hotel_id: int,
        room_type: RoomType,
        check_in: date,
        check_out: date
    ) -> int:
        """
        Get count of available rooms for the date range.
        Same logic as room_service.check_availability but returns count.
        """
        # Get total rooms of this type
        total_rooms_result = await self.db.execute(
            select(func.count(Room.id))
            .where(
                and_(
                    Room.hotel_id == hotel_id,
                    Room.room_type == room_type
                )
            )
        )
        total_rooms = total_rooms_result.scalar() or 0
        
        if total_rooms == 0:
            return 0
        
        # Get booked rooms (overlapping bookings)
        booked_rooms_result = await self.db.execute(
            select(func.count(func.distinct(Booking.room_id)))
            .join(Room, Booking.room_id == Room.id)
            .where(
                and_(
                    Room.hotel_id == hotel_id,
                    Room.room_type == room_type,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
                    or_(
                        # Booking starts during requested period
                        and_(
                            func.date(Booking.check_in_date) >= check_in,
                            func.date(Booking.check_in_date) < check_out
                        ),
                        # Booking ends during requested period
                        and_(
                            func.date(Booking.check_out_date) > check_in,
                            func.date(Booking.check_out_date) <= check_out
                        ),
                        # Booking spans entire requested period
                        and_(
                            func.date(Booking.check_in_date) <= check_in,
                            func.date(Booking.check_out_date) >= check_out
                        )
                    )
                )
            )
        )
        booked_rooms = booked_rooms_result.scalar() or 0
        
        return total_rooms - booked_rooms
    
    async def _get_base_price(self, hotel_id: int, room_type: RoomType) -> Decimal:
        """
        Get base price for a room type at a hotel.
        Uses the price from the first room of that type.
        """
        result = await self.db.execute(
            select(Room.base_price)
            .where(
                and_(
                    Room.hotel_id == hotel_id,
                    Room.room_type == room_type
                )
            )
            .limit(1)
        )
        price = result.scalar_one_or_none()
        return Decimal(str(price)) if price else Decimal("100.00")  # Fallback price
    
    async def _calculate_occupancy_rate(
        self,
        hotel_id: int,
        check_in: date,
        check_out: date
    ) -> float:
        """
        Calculate hotel occupancy rate for the date range.
        Returns percentage (0.0 - 1.0) of rooms booked.
        """
        # Get total rooms in hotel
        total_rooms_result = await self.db.execute(
            select(func.count(Room.id)).where(Room.hotel_id == hotel_id)
        )
        total_rooms = total_rooms_result.scalar() or 1  # Avoid division by zero
        
        # Get count of rooms with overlapping bookings
        booked_rooms_result = await self.db.execute(
            select(func.count(func.distinct(Booking.room_id)))
            .join(Room, Booking.room_id == Room.id)
            .where(
                and_(
                    Room.hotel_id == hotel_id,
                    Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
                    or_(
                        and_(
                            func.date(Booking.check_in_date) >= check_in,
                            func.date(Booking.check_in_date) < check_out
                        ),
                        and_(
                            func.date(Booking.check_out_date) > check_in,
                            func.date(Booking.check_out_date) <= check_out
                        ),
                        and_(
                            func.date(Booking.check_in_date) <= check_in,
                            func.date(Booking.check_out_date) >= check_out
                        )
                    )
                )
            )
        )
        booked_rooms = booked_rooms_result.scalar() or 0
        
        occupancy_rate = booked_rooms / total_rooms
        return min(occupancy_rate, 1.0)  # Cap at 100%
    
    def _calculate_price_breakdown(
        self,
        base_price: Decimal,
        check_in: date,
        check_out: date,
        quantity: int,
        occupancy_rate: float,
        discount_type: DiscountType
    ) -> PriceBreakdown:
        """
        Calculate detailed price breakdown with all factors applied.
        
        Formula: base_price * season_multiplier * occupancy_multiplier * discount_multiplier
        
        Args:
            base_price: Base room price per night
            check_in: Check-in date
            check_out: Check-out date
            quantity: Number of rooms
            occupancy_rate: Current hotel occupancy (0.0 - 1.0)
            discount_type: Type of discount to apply
            
        Returns:
            PriceBreakdown with all calculation details
        """
        # Calculate number of nights
        nights = (check_out - check_in).days
        
        # Determine season (use check-in date)
        check_in_dt = datetime.combine(check_in, datetime.min.time())
        season = get_season_for_date(check_in_dt)
        season_multiplier = SEASON_MULTIPLIERS[season]
        
        # Get occupancy multiplier
        occupancy_multiplier = get_occupancy_multiplier(occupancy_rate)
        
        # Calculate discount
        days_until_checkin = (check_in - date.today()).days
        discount_multiplier, discount_reason = calculate_discount_multiplier(
            discount_type=discount_type,
            days_until_checkin=days_until_checkin,
            nights_stay=nights
        )
        
        # Apply multipliers stage by stage
        price_after_season = base_price * Decimal(str(season_multiplier))
        price_after_occupancy = price_after_season * Decimal(str(occupancy_multiplier))
        price_after_discount = price_after_occupancy * Decimal(str(discount_multiplier))
        
        # Final price per night (rounded to 2 decimals)
        price_per_night = price_after_discount.quantize(Decimal("0.01"))
        
        # Calculate subtotal (total before tax)
        subtotal = price_per_night * nights * quantity
        
        # Calculate tax
        tax_amount = (subtotal * Decimal(str(self.DEFAULT_TAX_RATE))).quantize(Decimal("0.01"))
        
        # Final total
        total_price = subtotal + tax_amount
        
        return PriceBreakdown(
            base_price=base_price,
            nights=nights,
            quantity=quantity,
            season=season,
            season_multiplier=season_multiplier,
            occupancy_rate=occupancy_rate,
            occupancy_multiplier=occupancy_multiplier,
            discount_type=discount_type,
            discount_multiplier=discount_multiplier,
            discount_reason=discount_reason,
            price_after_season=price_after_season.quantize(Decimal("0.01")),
            price_after_occupancy=price_after_occupancy.quantize(Decimal("0.01")),
            price_after_discount=price_after_discount.quantize(Decimal("0.01")),
            price_per_night=price_per_night,
            subtotal=subtotal,
            tax_rate=self.DEFAULT_TAX_RATE,
            tax_amount=tax_amount,
            total_price=total_price
        )
