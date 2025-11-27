"""
Hotel service for search and listing operations.
"""
from datetime import date
from typing import List, Tuple, Optional
from decimal import Decimal
import math

from sqlalchemy import select, func, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.hotel import Hotel, Location, Room, RoomType
from app.schemas.hotel import HotelSearchParams, HotelSummary, HotelSearchResponse
from app.services.pricing_service import PricingService
from app.schemas.pricing import PriceQuoteRequest
from app.config.pricing_config import DiscountType


class HotelService:
    """Service for hotel search and management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_service = PricingService(db)
    
    async def search_hotels(
        self,
        params: HotelSearchParams
    ) -> HotelSearchResponse:
        """
        Search hotels with filters and compute minimum prices.
        
        Args:
            params: Search parameters including city, dates, guests, pagination
            
        Returns:
            HotelSearchResponse with hotels, min prices, and pagination info
        """
        # Build base query
        query = select(Hotel).options(
            joinedload(Hotel.location)
        ).where(Hotel.is_active == True)
        
        # Apply city filter
        if params.city:
            query = query.join(Location).where(
                func.lower(Location.city).like(f"%{params.city.lower()}%")
            )
        
        # Apply star rating filter
        if params.star_rating:
            query = query.where(Hotel.star_rating == params.star_rating)
        
        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Calculate pagination
        total_pages = math.ceil(total / params.page_size) if total > 0 else 0
        offset = (params.page - 1) * params.page_size
        
        # Apply pagination
        query = query.offset(offset).limit(params.page_size)
        
        # Execute query
        result = await self.db.execute(query)
        hotels = result.unique().scalars().all()
        
        # Build hotel summaries with min prices
        hotel_summaries = []
        for hotel in hotels:
            summary = await self._build_hotel_summary(
                hotel=hotel,
                check_in=params.check_in,
                check_out=params.check_out,
                guests=params.guests,
                min_price_filter=params.min_price,
                max_price_filter=params.max_price
            )
            
            # Apply price filters if provided
            if params.min_price and summary.min_price and summary.min_price < params.min_price:
                total -= 1
                continue
            if params.max_price and summary.min_price and summary.min_price > params.max_price:
                total -= 1
                continue
                
            hotel_summaries.append(summary)
        
        # Recalculate total pages after price filtering
        total_pages = math.ceil(total / params.page_size) if total > 0 else 0
        
        return HotelSearchResponse(
            hotels=hotel_summaries,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages
        )
    
    async def _build_hotel_summary(
        self,
        hotel: Hotel,
        check_in: Optional[date],
        check_out: Optional[date],
        guests: Optional[int],
        min_price_filter: Optional[Decimal],
        max_price_filter: Optional[Decimal]
    ) -> HotelSummary:
        """
        Build hotel summary with minimum price calculation.
        
        Args:
            hotel: Hotel object
            check_in: Check-in date (optional)
            check_out: Check-out date (optional)
            guests: Number of guests (optional)
            min_price_filter: Minimum price filter
            max_price_filter: Maximum price filter
            
        Returns:
            HotelSummary with min price and availability
        """
        # Get all room types for this hotel
        room_types_query = select(distinct(Room.room_type)).where(
            and_(
                Room.hotel_id == hotel.id,
                Room.is_active == True
            )
        )
        result = await self.db.execute(room_types_query)
        room_types = result.scalars().all()
        
        min_price = None
        total_available_rooms = 0
        
        # If dates provided, calculate min price using pricing engine
        if check_in and check_out and room_types:
            min_price_value = None
            
            for room_type in room_types:
                # Get price quote for this room type
                quote_request = PriceQuoteRequest(
                    hotel_id=hotel.id,
                    room_type=room_type.value,
                    check_in=check_in,
                    check_out=check_out,
                    quantity=1,
                    discount_type=DiscountType.NONE
                )
                
                quote = await self.pricing_service.get_price_quote(quote_request)
                
                if quote.available and quote.breakdown:
                    price_per_night = quote.breakdown.price_per_night
                    
                    # Filter by capacity if guests specified
                    if guests:
                        # Get room capacity
                        capacity_query = select(Room.capacity).where(
                            and_(
                                Room.hotel_id == hotel.id,
                                Room.room_type == room_type,
                                Room.is_active == True
                            )
                        ).limit(1)
                        capacity_result = await self.db.execute(capacity_query)
                        capacity = capacity_result.scalar()
                        
                        if capacity and capacity < guests:
                            continue  # Skip rooms that can't accommodate guests
                    
                    # Track minimum price
                    if min_price_value is None or price_per_night < min_price_value:
                        min_price_value = price_per_night
                    
                    total_available_rooms += quote.available_rooms
            
            min_price = min_price_value
        
        # If no dates provided, get base price from rooms
        elif room_types:
            base_price_query = select(func.min(Room.base_price)).where(
                and_(
                    Room.hotel_id == hotel.id,
                    Room.is_active == True
                )
            )
            
            # Filter by capacity if guests specified
            if guests:
                base_price_query = base_price_query.where(Room.capacity >= guests)
            
            result = await self.db.execute(base_price_query)
            base_price = result.scalar()
            min_price = Decimal(str(base_price)) if base_price else None
            
            # Get total rooms count
            rooms_count_query = select(func.count(Room.id)).where(
                and_(
                    Room.hotel_id == hotel.id,
                    Room.is_active == True
                )
            )
            if guests:
                rooms_count_query = rooms_count_query.where(Room.capacity >= guests)
            
            count_result = await self.db.execute(rooms_count_query)
            total_available_rooms = count_result.scalar() or 0
        
        return HotelSummary(
            id=hotel.id,
            name=hotel.name,
            description=hotel.description,
            address=hotel.address,
            city=hotel.location.city if hotel.location else "Unknown",
            state=hotel.location.state if hotel.location else None,
            country=hotel.location.country if hotel.location else "Unknown",
            latitude=Decimal(str(hotel.latitude)) if hotel.latitude else None,
            longitude=Decimal(str(hotel.longitude)) if hotel.longitude else None,
            star_rating=hotel.star_rating,
            contact_number=hotel.contact_number,
            email=hotel.email,
            check_in_time=hotel.check_in_time,
            check_out_time=hotel.check_out_time,
            min_price=min_price,
            available_rooms=total_available_rooms
        )
    
    async def get_hotel_by_id(self, hotel_id: int) -> Optional[Hotel]:
        """
        Get hotel by ID with location relationship.
        
        Args:
            hotel_id: Hotel ID
            
        Returns:
            Hotel object or None
        """
        query = select(Hotel).options(
            joinedload(Hotel.location)
        ).where(
            and_(
                Hotel.id == hotel_id,
                Hotel.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()
