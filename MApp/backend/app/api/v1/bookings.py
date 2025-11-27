"""
API endpoints for booking operations.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.db.session import get_db
from app.db.redis import get_redis
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingDetail,
    BookingListItem,
    BookingListResponse
)
from app.services.booking_service import BookingService
from app.core.dependencies import get_current_user
from app.models.hotel import User


router = APIRouter()


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new booking.
    
    **Process:**
    1. Validates the provided lock_id is valid and matches booking parameters
    2. Calculates total price using the pricing engine
    3. Finds an available room of the requested type
    4. Creates the booking record with CONFIRMED status
    5. Releases the availability lock
    
    **Requirements:**
    - Valid lock_id obtained from POST /api/v1/availability/lock
    - Lock must not be expired (2-minute TTL)
    - Lock parameters must match booking request
    - At least one room must be available
    
    **Returns:**
    - Booking confirmation with booking_reference and total_amount
    """
    try:
        booking = await BookingService.create_booking(
            db=db,
            redis=redis,
            user_id=current_user["user_id"],
            booking_data=booking_data
        )
        return booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create booking: {str(e)}"
        )


@router.get("/bookings/{booking_id}", response_model=BookingDetail)
async def get_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get booking details by ID.
    
    **Authorization:**
    - Users can only view their own bookings
    - Admin users can view any booking
    
    **Returns:**
    - Complete booking details including hotel, room, guest info, and pricing
    """
    # Check if user is admin
    is_admin = current_user.get("role") == "admin"
    
    booking = await BookingService.get_booking_by_id(
        db=db,
        booking_id=booking_id,
        user_id=None if is_admin else current_user["user_id"]
    )
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return booking


@router.get("/bookings", response_model=BookingListResponse)
async def list_user_bookings(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated list of current user's bookings.
    
    **Pagination:**
    - Default: page=1, page_size=10
    - Max page_size: 100
    
    **Sorting:**
    - Bookings are sorted by creation date (newest first)
    
    **Returns:**
    - Paginated list of bookings with summary information
    """
    bookings, total = await BookingService.get_user_bookings(
        db=db,
        user_id=current_user["user_id"],
        page=page,
        page_size=page_size
    )
    
    # Convert to list items
    booking_items = []
    for booking in bookings:
        booking_reference = f"BK{booking.id:06d}-{booking.created_at.strftime('%Y%m%d')}"
        booking_items.append(
            BookingListItem(
                booking_id=booking.id,
                booking_reference=booking_reference,
                status=booking.status.value,
                hotel_name=booking.room.hotel.name,
                room_type=booking.room.room_type.value,
                check_in=booking.check_in_date.date(),
                check_out=booking.check_out_date.date(),
                total_amount=booking.total_amount,
                created_at=booking.created_at
            )
        )
    
    # Calculate total pages
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return BookingListResponse(
        bookings=booking_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/bookings/{booking_id}/services", status_code=status.HTTP_201_CREATED)
async def add_service_to_booking(
    booking_id: int,
    service_request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a service to an existing booking (in-stay service ordering).
    
    **Process:**
    1. Validates booking exists and user owns it
    2. Verifies booking is in active status (CONFIRMED or CHECKED_IN)
    3. Validates service exists and is available
    4. Creates service order with PENDING status
    5. Updates booking total amount
    
    **Requirements:**
    - Valid JWT token
    - User must own the booking
    - Booking must be CONFIRMED or CHECKED_IN
    - Service must be active and available at the hotel
    
    **Request Body:**
    - service_id: ID of the service to add
    - quantity: Quantity of service (1-100)
    - notes: Optional notes
    
    **Returns:**
    - Created service order details
    """
    try:
        user_mobile = current_user["mobile"]
        
        service_order = await BookingService.add_service_to_booking(
            db=db,
            booking_id=booking_id,
            user_mobile=user_mobile,
            service_id=service_request["service_id"],
            quantity=service_request["quantity"],
            notes=service_request.get("notes")
        )
        
        return service_order
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add service to booking: {str(e)}"
        )


@router.put("/bookings/{booking_id}/services/{service_order_id}", status_code=status.HTTP_200_OK)
async def update_service_order_status(
    booking_id: int,
    service_order_id: int,
    status_request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the status of a service order.
    
    **Valid Status Transitions:**
    - PENDING → CONFIRMED, CANCELLED
    - CONFIRMED → IN_PROGRESS, CANCELLED
    - IN_PROGRESS → COMPLETED, CANCELLED
    - COMPLETED → (final state, no transitions)
    - CANCELLED → (final state, no transitions)
    
    **Process:**
    1. Validates service order exists and user owns it
    2. Verifies status transition is valid
    3. Updates service order status
    4. Sets completed_at timestamp if status is COMPLETED
    
    **Requirements:**
    - Valid JWT token
    - User must own the booking
    - Status transition must follow the state machine rules
    
    **Request Body:**
    - status: New status (pending, confirmed, in_progress, completed, cancelled)
    
    **Returns:**
    - Updated service order details
    """
    try:
        user_mobile = current_user["mobile"]
        
        service_order = await BookingService.update_service_order_status(
            db=db,
            booking_id=booking_id,
            service_order_id=service_order_id,
            user_mobile=user_mobile,
            new_status=status_request["status"]
        )
        
        return service_order
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update service order status: {str(e)}"
        )


@router.get("/bookings/{booking_id}/invoice", status_code=status.HTTP_200_OK)
async def get_booking_invoice(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get invoice for a booking with itemized breakdown.
    
    **Process:**
    1. Validates booking exists and user owns it
    2. Retrieves invoice with all line items
    3. Returns detailed breakdown of charges
    
    **Invoice Structure:**
    - Line items: Room charges and individual services
    - Room subtotal: Total room charges
    - Services subtotal: Total service charges (only COMPLETED services)
    - Subtotal: Room + Services
    - Tax: Calculated on subtotal (default 18% GST)
    - Discount: Any discounts applied
    - Total: Final amount to be paid
    
    **Requirements:**
    - Valid JWT token
    - User must own the booking
    
    **Returns:**
    - Complete invoice details with line item breakdown
    """
    try:
        from app.services.invoice_service import InvoiceService
        
        # Get user ID from mobile number
        user_mobile = current_user["mobile"]
        user_query = select(User.id).where(User.mobile_number == user_mobile)
        user_result = await db.execute(user_query)
        actual_user_id = user_result.scalar_one_or_none()
        
        if not actual_user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        invoice = await InvoiceService.get_invoice_by_booking_id(
            db=db,
            booking_id=booking_id,
            user_id=actual_user_id
        )
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found for this booking"
            )
        
        return invoice
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve invoice: {str(e)}"
        )
