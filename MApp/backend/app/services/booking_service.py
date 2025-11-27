"""
Service layer for booking operations.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.hotel import Booking, BookingStatus, Room, Hotel, RoomType, User, Guest
from app.services.availability_lock_service import AvailabilityLockService
from app.services.pricing_service import PricingService
from app.schemas.booking import BookingCreate, BookingResponse, BookingDetail
from app.schemas.pricing import PriceQuoteRequest
from app.schemas.guest import GuestDetail


class BookingService:
    """Service for managing bookings."""
    
    @staticmethod
    def _generate_booking_reference() -> str:
        """Generate a unique booking reference."""
        # Format: BK-YYYYMMDD-XXXX (BK-20251127-A3F2)
        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:4].upper()
        return f"BK-{date_part}-{random_part}"
    
    @staticmethod
    async def create_booking(
        db: AsyncSession,
        redis: Redis,
        user_id: int,
        booking_data: BookingCreate
    ) -> BookingResponse:
        """
        Create a new booking.
        
        Process:
        1. Validate lock exists and matches booking parameters
        2. Calculate pricing using PricingService
        3. Find an available room of the requested type
        4. Create booking record
        5. Release the lock
        
        Args:
            db: Database session
            redis: Redis client
            user_id: ID of the user making the booking
            booking_data: Booking creation data
            
        Returns:
            BookingResponse with booking details
            
        Raises:
            ValueError: If validation fails or booking cannot be created
        """
        # 1. Validate lock
        lock_status = await AvailabilityLockService.get_lock_status(
            redis, booking_data.lock_id
        )
        
        if not lock_status:
            raise ValueError("Invalid or expired lock ID")
        
        # Validate lock matches booking parameters (case-insensitive for room_type)
        if (
            lock_status["hotel_id"] != booking_data.hotel_id or
            lock_status["room_type"].upper() != booking_data.room_type.upper() or
            lock_status["check_in_date"] != booking_data.check_in.isoformat() or
            lock_status["check_out_date"] != booking_data.check_out.isoformat()
        ):
            raise ValueError("Lock parameters do not match booking request")
        
        # Validate user exists (user_id from JWT is mobile_number)
        user_query = select(User).where(User.mobile_number == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User with mobile {user_id} not found")
        
        # Get actual database user ID
        actual_user_id = user.id
        
        # 2. Get hotel details
        hotel_query = select(Hotel).where(Hotel.id == booking_data.hotel_id)
        hotel_result = await db.execute(hotel_query)
        hotel = hotel_result.scalar_one_or_none()
        
        if not hotel:
            raise ValueError(f"Hotel with ID {booking_data.hotel_id} not found")
        
        # 3. Calculate pricing
        try:
            room_type_enum = RoomType(booking_data.room_type.upper())
        except ValueError:
            raise ValueError(f"Invalid room type: {booking_data.room_type}")
        
        # Create pricing service and get quote
        pricing_service = PricingService(db)
        price_quote_request = PriceQuoteRequest(
            hotel_id=booking_data.hotel_id,
            room_type=booking_data.room_type,
            check_in=booking_data.check_in,
            check_out=booking_data.check_out,
            quantity=1
        )
        price_quote_response = await pricing_service.get_price_quote(price_quote_request)
        
        if not price_quote_response.available:
            raise ValueError("Unable to calculate pricing for this booking")
        
        if not price_quote_response.breakdown:
            raise ValueError("Price breakdown not available")
        
        total_amount = price_quote_response.breakdown.total_price
        
        # 4. Find an available room
        # Get all rooms of the requested type at this hotel
        rooms_query = (
            select(Room)
            .where(
                Room.hotel_id == booking_data.hotel_id,
                Room.room_type == room_type_enum,
                Room.is_active == True,
                Room.is_available == True,
                Room.capacity >= booking_data.guests
            )
        )
        rooms_result = await db.execute(rooms_query)
        available_rooms = rooms_result.scalars().all()
        
        if not available_rooms:
            raise ValueError(
                f"No available rooms of type {booking_data.room_type} "
                f"for {booking_data.guests} guests"
            )
        
        # Check which rooms are not booked during the requested period
        for room in available_rooms:
            # Check for overlapping bookings
            overlapping_query = (
                select(Booking)
                .where(
                    Booking.room_id == room.id,
                    Booking.check_in_date < booking_data.check_out,
                    Booking.check_out_date > booking_data.check_in,
                    Booking.status.in_([
                        BookingStatus.PENDING,
                        BookingStatus.CONFIRMED,
                        BookingStatus.CHECKED_IN
                    ])
                )
            )
            overlapping_result = await db.execute(overlapping_query)
            overlapping_booking = overlapping_result.scalar_one_or_none()
            
            if not overlapping_booking:
                # This room is available
                selected_room = room
                break
        else:
            raise ValueError("No available rooms found for the requested dates")
        
        # 5. Validate guest count against room capacity
        if booking_data.guests > selected_room.capacity:
            raise ValueError(
                f"Number of guests ({booking_data.guests}) exceeds room capacity ({selected_room.capacity})"
            )
        
        # 6. Create booking record
        booking_reference = BookingService._generate_booking_reference()
        
        # Determine primary guest info (backwards compatibility)
        primary_guest_name = booking_data.guest_name
        primary_guest_email = booking_data.guest_email
        primary_guest_phone = booking_data.guest_phone
        
        if booking_data.guest_list:
            # Use primary guest from list
            primary_guest = [g for g in booking_data.guest_list if g.is_primary][0]
            primary_guest_name = primary_guest.guest_name
            primary_guest_email = primary_guest.guest_email
            primary_guest_phone = primary_guest.guest_phone
        
        new_booking = Booking(
            user_id=actual_user_id,
            room_id=selected_room.id,
            check_in_date=datetime.combine(booking_data.check_in, datetime.min.time()),
            check_out_date=datetime.combine(booking_data.check_out, datetime.min.time()),
            guest_name=primary_guest_name,
            guest_email=primary_guest_email,
            guest_phone=primary_guest_phone,
            number_of_guests=booking_data.guests,
            total_amount=float(total_amount),
            status=BookingStatus.CONFIRMED,
            special_requests=booking_data.special_requests
        )
        
        db.add(new_booking)
        await db.flush()  # Flush to get the booking ID
        
        # 7. Create guest records if guest_list is provided
        if booking_data.guest_list:
            from app.models.hotel import Guest
            for guest_data in booking_data.guest_list:
                guest = Guest(
                    booking_id=new_booking.id,
                    guest_name=guest_data.guest_name,
                    guest_email=guest_data.guest_email,
                    guest_phone=guest_data.guest_phone,
                    age=guest_data.age,
                    id_type=guest_data.id_type,
                    id_number=guest_data.id_number,
                    is_primary=guest_data.is_primary
                )
                db.add(guest)
        
        # 7b. Create service orders if pre_services is provided
        service_total = 0.0
        if booking_data.pre_services:
            from app.models.hotel import ServiceOrder, ServiceOrderStatus, Service
            
            # Fetch service details for validation and pricing
            service_ids = [s.service_id for s in booking_data.pre_services]
            services_query = select(Service).where(
                Service.id.in_(service_ids),
                Service.hotel_id == booking_data.hotel_id,
                Service.is_active == True,
                Service.is_available == True
            )
            services_result = await db.execute(services_query)
            services = {s.id: s for s in services_result.scalars().all()}
            
            # Validate all services exist and are available
            for pre_service in booking_data.pre_services:
                if pre_service.service_id not in services:
                    raise ValueError(f"Service with ID {pre_service.service_id} not found or not available")
                
                service = services[pre_service.service_id]
                unit_price = service.price
                total_price = unit_price * pre_service.quantity
                service_total += total_price
                
                # Create service order
                service_order = ServiceOrder(
                    booking_id=new_booking.id,
                    service_id=pre_service.service_id,
                    quantity=pre_service.quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                    status=ServiceOrderStatus.CONFIRMED,
                    notes=pre_service.notes
                )
                db.add(service_order)
            
            # Update booking total_amount to include services
            new_booking.total_amount = float(total_amount) + service_total
        
        # 8. Create invoice for the booking
        from app.services.invoice_service import InvoiceService
        
        # Room subtotal is the room cost without services
        room_subtotal = float(total_amount)
        await InvoiceService.create_invoice(
            db=db,
            booking_id=new_booking.id,
            room_subtotal=room_subtotal,
            tax_rate=0.18  # 18% GST
        )
        
        # 9. Release the lock
        lock_released = await AvailabilityLockService.release_lock(
            redis, booking_data.lock_id
        )
        
        if not lock_released:
            # Lock might have expired, but booking is still created
            # Log this for monitoring
            pass
        
        await db.commit()
        await db.refresh(new_booking)
        
        # Generate booking reference using booking ID
        # Format: BK-{booking_id}-{date}
        booking_reference = f"BK{new_booking.id:06d}-{datetime.utcnow().strftime('%Y%m%d')}"
        
        # Return booking response
        return BookingResponse(
            booking_id=new_booking.id,
            booking_reference=booking_reference,
            status=new_booking.status.value,
            hotel_id=hotel.id,
            hotel_name=hotel.name,
            room_type=booking_data.room_type,
            check_in=booking_data.check_in,
            check_out=booking_data.check_out,
            guests=booking_data.guests,
            guest_name=primary_guest_name,
            total_amount=Decimal(str(total_amount)),
            created_at=new_booking.created_at
        )
    
    @staticmethod
    async def get_booking_by_id(
        db: AsyncSession,
        booking_id: int,
        user_id: Optional[str] = None
    ) -> Optional[BookingDetail]:
        """
        Get booking details by ID.
        
        Args:
            db: Database session
            booking_id: Booking ID
            user_id: Optional user mobile number to filter by (for authorization)
            
        Returns:
            BookingDetail if found, None otherwise
        """
        from app.models.hotel import Guest, ServiceOrder, Service
        from app.schemas.guest import GuestDetail
        from app.schemas.service import BookingServiceDetail
        
        query = (
            select(Booking)
            .options(
                joinedload(Booking.room).joinedload(Room.hotel),
                joinedload(Booking.guests),
                joinedload(Booking.services).joinedload(ServiceOrder.service)
            )
            .where(Booking.id == booking_id)
        )
        
        if user_id:
            # user_id is mobile_number from JWT, convert to actual DB user ID
            user_query = select(User.id).where(User.mobile_number == user_id)
            user_result = await db.execute(user_query)
            actual_user_id = user_result.scalar_one_or_none()
            if actual_user_id:
                query = query.where(Booking.user_id == actual_user_id)
        
        result = await db.execute(query)
        booking = result.unique().scalar_one_or_none()
        
        if not booking:
            return None
        
        # Generate booking reference
        booking_reference = f"BK{booking.id:06d}-{booking.created_at.strftime('%Y%m%d')}"
        
        # Convert guests to GuestDetail list
        guest_details = None
        if booking.guests:
            guest_details = [
                GuestDetail(
                    guest_name=g.guest_name,
                    guest_email=g.guest_email,
                    guest_phone=g.guest_phone,
                    age=g.age,
                    is_primary=g.is_primary
                )
                for g in booking.guests
            ]
        
        # Convert services to BookingServiceDetail list
        booking_services = None
        if booking.services:
            booking_services = [
                BookingServiceDetail(
                    id=so.id,
                    service_id=so.service_id,
                    service_name=so.service.name,
                    service_type=so.service.service_type.value,
                    quantity=so.quantity,
                    unit_price=so.unit_price,
                    total_price=so.total_price,
                    status=so.status.value,
                    notes=so.notes,
                    ordered_at=so.ordered_at
                )
                for so in booking.services
            ]
        
        return BookingDetail(
            booking_id=booking.id,
            booking_reference=booking_reference,
            status=booking.status.value,
            hotel_id=booking.room.hotel.id,
            hotel_name=booking.room.hotel.name,
            hotel_address=booking.room.hotel.address,
            room_id=booking.room.id,
            room_type=booking.room.room_type.value,
            room_number=booking.room.room_number,
            check_in=booking.check_in_date.date(),
            check_out=booking.check_out_date.date(),
            guests=booking.number_of_guests,
            guest_name=booking.guest_name,
            guest_email=booking.guest_email,
            guest_phone=booking.guest_phone,
            special_requests=booking.special_requests,
            guest_details=guest_details,
            booking_services=booking_services,
            total_amount=Decimal(str(booking.total_amount)),
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )
    
    @staticmethod
    async def get_user_bookings(
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[list[Booking], int]:
        """
        Get paginated list of user's bookings.
        
        Args:
            db: Database session
            user_id: User mobile number (from JWT)
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Tuple of (bookings list, total count)
        """
        # Convert mobile number to actual DB user ID
        user_query = select(User.id).where(User.mobile_number == user_id)
        user_result = await db.execute(user_query)
        actual_user_id = user_result.scalar_one_or_none()
        
        if not actual_user_id:
            return [], 0
        
        # Count total bookings
        from sqlalchemy import func
        count_query = (
            select(func.count())
            .select_from(Booking)
            .where(Booking.user_id == actual_user_id)
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get paginated bookings
        offset = (page - 1) * page_size
        query = (
            select(Booking)
            .options(
                joinedload(Booking.room).joinedload(Room.hotel)
            )
            .where(Booking.user_id == actual_user_id)
            .order_by(Booking.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        
        result = await db.execute(query)
        bookings = result.scalars().all()
        
        return list(bookings), total
    
    @staticmethod
    async def add_service_to_booking(
        db: AsyncSession,
        booking_id: int,
        user_mobile: str,
        service_id: int,
        quantity: int,
        notes: Optional[str] = None
    ):
        """
        Add a service to an existing booking (in-stay service ordering).
        
        Validates:
        - Booking exists and user owns it
        - Booking is in active/checked-in status
        - Service exists and is available
        - Service belongs to the same hotel as the booking
        
        Args:
            db: Database session
            booking_id: ID of the booking
            user_mobile: User mobile number from JWT
            service_id: ID of the service to add
            quantity: Quantity of service
            notes: Optional notes
            
        Returns:
            Created ServiceOrder
        """
        from app.models.hotel import ServiceOrder, ServiceOrderStatus, Service
        from app.schemas.service import BookingServiceDetail
        
        # Get user ID from mobile number
        user_query = select(User.id).where(User.mobile_number == user_mobile)
        user_result = await db.execute(user_query)
        actual_user_id = user_result.scalar_one_or_none()
        
        if not actual_user_id:
            raise ValueError(f"User with mobile {user_mobile} not found")
        
        # Get booking with room and hotel info
        booking_query = (
            select(Booking)
            .options(joinedload(Booking.room).joinedload(Room.hotel))
            .where(
                Booking.id == booking_id,
                Booking.user_id == actual_user_id
            )
        )
        booking_result = await db.execute(booking_query)
        booking = booking_result.unique().scalar_one_or_none()
        
        if not booking:
            raise ValueError("Booking not found or access denied")
        
        # Validate booking is in active window (checked in or confirmed)
        if booking.status not in [BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]:
            raise ValueError(f"Cannot add services to booking with status: {booking.status.value}")
        
        # Get service and validate
        service_query = select(Service).where(
            Service.id == service_id,
            Service.hotel_id == booking.room.hotel.id,
            Service.is_active == True,
            Service.is_available == True
        )
        service_result = await db.execute(service_query)
        service = service_result.scalar_one_or_none()
        
        if not service:
            raise ValueError("Service not found or not available at this hotel")
        
        # Calculate pricing
        unit_price = service.price
        total_price = unit_price * quantity
        
        # Create service order
        service_order = ServiceOrder(
            booking_id=booking_id,
            service_id=service_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            status=ServiceOrderStatus.PENDING,
            notes=notes
        )
        db.add(service_order)
        
        # Update booking total amount
        booking.total_amount = float(booking.total_amount) + total_price
        
        await db.commit()
        await db.refresh(service_order)
        
        # Eagerly load service for response
        await db.refresh(service_order, ["service"])
        
        return BookingServiceDetail(
            id=service_order.id,
            service_id=service_order.service_id,
            service_name=service_order.service.name,
            service_type=service_order.service.service_type.value,
            quantity=service_order.quantity,
            unit_price=service_order.unit_price,
            total_price=service_order.total_price,
            status=service_order.status.value,
            notes=service_order.notes,
            ordered_at=service_order.ordered_at
        )
    
    @staticmethod
    async def update_service_order_status(
        db: AsyncSession,
        booking_id: int,
        service_order_id: int,
        user_mobile: str,
        new_status: str
    ):
        """
        Update the status of a service order with validation.
        
        Valid transitions:
        - PENDING -> CONFIRMED, CANCELLED
        - CONFIRMED -> IN_PROGRESS, CANCELLED
        - IN_PROGRESS -> COMPLETED, CANCELLED
        - COMPLETED -> (final state)
        - CANCELLED -> (final state)
        
        Args:
            db: Database session
            booking_id: ID of the booking
            service_order_id: ID of the service order
            user_mobile: User mobile number from JWT
            new_status: New status to set
            
        Returns:
            Updated ServiceOrder
        """
        from app.models.hotel import ServiceOrder, ServiceOrderStatus
        from app.schemas.service import BookingServiceDetail
        
        # Validate status value
        try:
            new_status_enum = ServiceOrderStatus(new_status.lower())
        except ValueError:
            valid_statuses = [s.value for s in ServiceOrderStatus]
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Get user ID from mobile number
        user_query = select(User.id).where(User.mobile_number == user_mobile)
        user_result = await db.execute(user_query)
        actual_user_id = user_result.scalar_one_or_none()
        
        if not actual_user_id:
            raise ValueError(f"User with mobile {user_mobile} not found")
        
        # Get service order with booking validation
        service_order_query = (
            select(ServiceOrder)
            .join(Booking)
            .options(joinedload(ServiceOrder.service))
            .where(
                ServiceOrder.id == service_order_id,
                ServiceOrder.booking_id == booking_id,
                Booking.user_id == actual_user_id
            )
        )
        service_order_result = await db.execute(service_order_query)
        service_order = service_order_result.unique().scalar_one_or_none()
        
        if not service_order:
            raise ValueError("Service order not found or access denied")
        
        # Validate status transition
        current_status = service_order.status
        
        # Define valid transitions
        valid_transitions = {
            ServiceOrderStatus.PENDING: [ServiceOrderStatus.CONFIRMED, ServiceOrderStatus.CANCELLED],
            ServiceOrderStatus.CONFIRMED: [ServiceOrderStatus.IN_PROGRESS, ServiceOrderStatus.CANCELLED],
            ServiceOrderStatus.IN_PROGRESS: [ServiceOrderStatus.COMPLETED, ServiceOrderStatus.CANCELLED],
            ServiceOrderStatus.COMPLETED: [],  # Final state
            ServiceOrderStatus.CANCELLED: []   # Final state
        }
        
        if new_status_enum not in valid_transitions.get(current_status, []):
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status_enum.value}"
            )
        
        # Update status
        service_order.status = new_status_enum
        
        # Set completed_at timestamp if status is COMPLETED
        if new_status_enum == ServiceOrderStatus.COMPLETED:
            service_order.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(service_order)
        
        # Recalculate invoice if service completed or cancelled
        if new_status_enum in [ServiceOrderStatus.COMPLETED, ServiceOrderStatus.CANCELLED]:
            from app.services.invoice_service import InvoiceService
            from app.models.hotel import Invoice
            
            # Get invoice for this booking
            invoice_query = select(Invoice).where(Invoice.booking_id == booking_id)
            invoice_result = await db.execute(invoice_query)
            invoice = invoice_result.scalar_one_or_none()
            
            if invoice:
                await InvoiceService.recalculate_invoice(db, invoice.id)
        
        return BookingServiceDetail(
            id=service_order.id,
            service_id=service_order.service_id,
            service_name=service_order.service.name,
            service_type=service_order.service.service_type.value,
            quantity=service_order.quantity,
            unit_price=service_order.unit_price,
            total_price=service_order.total_price,
            status=service_order.status.value,
            notes=service_order.notes,
            ordered_at=service_order.ordered_at
        )

