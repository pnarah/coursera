"""Vendor and employee management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.models.hotel import User, UserRole
from app.services.vendor_service import VendorService
from app.schemas.employee import (
    VendorApprovalRequestCreate,
    VendorApprovalRequestResponse,
    VendorApprovalAction,
    EmployeeInvitationCreate,
    EmployeeInvitationResponse,
    EmployeeInvitationAccept,
    HotelEmployeeResponse,
    HotelEmployeeUpdate
)
from app.schemas.vendor import VendorHotelsResponse, VendorHotelItem, VendorAnalyticsResponse

router = APIRouter()


# ===== Vendor Dashboard Endpoints =====

@router.get("/hotels", response_model=VendorHotelsResponse)
async def get_vendor_hotels(
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all hotels owned/managed by the current vendor.
    VENDOR_ADMIN only.
    Returns hotel list with room counts and employee counts.
    """
    from sqlalchemy import select, func
    from app.models.hotel import Hotel
    from app.models.subscription import VendorSubscription
    from app.models.employee import HotelEmployee
    
    # Get all hotels for this vendor through active subscriptions
    query = (
        select(Hotel)
        .join(VendorSubscription, Hotel.id == VendorSubscription.hotel_id)
        .where(VendorSubscription.vendor_id == current_user.id)
        .distinct()
    )
    
    result = await db.execute(query)
    hotels = result.scalars().all()
    
    # Build response with counts
    hotel_items = []
    for hotel in hotels:
        # Count total rooms for this hotel
        room_count_query = select(func.count()).select_from(
            select(1).where(
                select(1).where(
                    select(1).correlate(Hotel).where(Hotel.id == hotel.id)
                ).exists()
            ).alias()
        )
        # Simpler approach - just count from relationship
        total_rooms = len(hotel.rooms) if hotel.rooms else 0
        
        # Count total employees for this hotel
        total_employees = len(hotel.employees) if hotel.employees else 0
        
        # Get location string
        location_str = None
        if hotel.location:
            location_parts = []
            if hotel.location.city:
                location_parts.append(hotel.location.city)
            if hotel.location.state:
                location_parts.append(hotel.location.state)
            location_str = ", ".join(location_parts) if location_parts else None
        
        hotel_items.append(VendorHotelItem(
            id=hotel.id,
            name=hotel.name,
            address=hotel.address,
            location=location_str,
            star_rating=hotel.star_rating,
            total_rooms=total_rooms,
            total_employees=total_employees
        ))
    
    return VendorHotelsResponse(hotels=hotel_items)


@router.get("/analytics", response_model=VendorAnalyticsResponse)
async def get_vendor_analytics(
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics for vendor's hotels (bookings, revenue, guests).
    VENDOR_ADMIN only.
    Returns aggregated data across all vendor's hotels.
    """
    from sqlalchemy import select, func
    from app.models.hotel import Hotel, Booking
    from app.models.subscription import VendorSubscription
    
    # Get all hotel IDs for this vendor through active subscriptions
    hotel_ids_query = (
        select(VendorSubscription.hotel_id)
        .where(VendorSubscription.vendor_id == current_user.id)
        .distinct()
    )
    
    result = await db.execute(hotel_ids_query)
    hotel_ids = [row[0] for row in result.fetchall()]
    
    if not hotel_ids:
        # No hotels for this vendor yet
        return VendorAnalyticsResponse(
            total_bookings=0,
            total_revenue=0.0,
            total_guests=0
        )
    
    # Get bookings for all vendor's hotels
    bookings_query = (
        select(Booking)
        .join(Booking.room)
        .where(Booking.room.has(hotel_id=hotel_ids[0]) if len(hotel_ids) == 1 
               else Booking.room.has(Hotel.id.in_(hotel_ids)))
    )
    
    # Simpler approach: just query bookings where room's hotel_id is in our list
    from app.models.hotel import Room
    bookings_query = (
        select(Booking)
        .join(Room, Booking.room_id == Room.id)
        .where(Room.hotel_id.in_(hotel_ids))
    )
    
    bookings_result = await db.execute(bookings_query)
    bookings = bookings_result.scalars().all()
    
    # Calculate analytics
    total_bookings = len(bookings)
    total_revenue = sum(booking.total_amount for booking in bookings)
    
    # Count unique guests (by user_id)
    unique_guest_ids = set(booking.user_id for booking in bookings)
    total_guests = len(unique_guest_ids)
    
    return VendorAnalyticsResponse(
        total_bookings=total_bookings,
        total_revenue=float(total_revenue),
        total_guests=total_guests
    )


# ===== Vendor Approval Requests =====

@router.post("/approval-request", response_model=VendorApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_request(
    request: VendorApprovalRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a vendor approval request.
    Any authenticated user can request to become a vendor.
    """
    service = VendorService(db)
    
    try:
        approval_request = await service.create_vendor_request(
            user_id=current_user.id,
            business_name=request.business_name,
            business_address=request.business_address,
            tax_id=request.tax_id,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone
        )
        return approval_request
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/approval-request/my-requests", response_model=List[VendorApprovalRequestResponse])
async def get_my_vendor_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get vendor requests for the current user"""
    service = VendorService(db)
    requests = await service.get_user_requests(current_user.id)
    return requests


@router.get("/approval-request/pending", response_model=List[VendorApprovalRequestResponse])
async def get_pending_vendor_requests(
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending vendor requests.
    SYSTEM_ADMIN only.
    """
    service = VendorService(db)
    requests = await service.get_pending_requests()
    return requests


@router.post("/approval-request/{request_id}/approve", status_code=status.HTTP_200_OK)
async def approve_vendor_request(
    request_id: int,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a vendor request.
    SYSTEM_ADMIN only.
    This will upgrade the user's role to VENDOR_ADMIN.
    """
    service = VendorService(db)
    
    try:
        approval_request = await service.approve_vendor_request(
            request_id=request_id,
            admin_user_id=current_user.id
        )
        return {
            "message": "Vendor approved successfully",
            "request_id": approval_request.id,
            "user_id": approval_request.user_id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/approval-request/{request_id}/reject", status_code=status.HTTP_200_OK)
async def reject_vendor_request(
    request_id: int,
    action: VendorApprovalAction,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject a vendor request.
    SYSTEM_ADMIN only.
    Rejection reason is required.
    """
    if not action.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required"
        )
    
    service = VendorService(db)
    
    try:
        approval_request = await service.reject_vendor_request(
            request_id=request_id,
            admin_user_id=current_user.id,
            rejection_reason=action.rejection_reason
        )
        return {
            "message": "Vendor request rejected",
            "request_id": approval_request.id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ===== Employee Management =====

@router.post("/employees/invite", response_model=EmployeeInvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_employee(
    invitation: EmployeeInvitationCreate,
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite an employee to a hotel.
    VENDOR_ADMIN only.
    Invitation is sent via SMS/Email (to be implemented).
    """
    service = VendorService(db)
    
    try:
        employee_invitation = await service.invite_employee(
            hotel_id=invitation.hotel_id,
            mobile_number=invitation.mobile_number,
            role=invitation.role.value,
            invited_by=current_user.id,
            permissions=invitation.permissions
        )
        return employee_invitation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/employees/accept-invitation", response_model=HotelEmployeeResponse, status_code=status.HTTP_201_CREATED)
async def accept_employee_invitation(
    acceptance: EmployeeInvitationAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept an employee invitation.
    The invitation token must match the user's mobile number.
    """
    service = VendorService(db)
    
    try:
        employee = await service.accept_invitation(
            token=acceptance.token,
            user_id=current_user.id
        )
        return employee
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/hotels/{hotel_id}/employees", response_model=List[HotelEmployeeResponse])
async def get_hotel_employees(
    hotel_id: int,
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN, UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all employees for a hotel.
    VENDOR_ADMIN or SYSTEM_ADMIN only.
    """
    service = VendorService(db)
    employees = await service.get_hotel_employees(hotel_id)
    return employees


@router.get("/hotels/{hotel_id}/invitations", response_model=List[EmployeeInvitationResponse])
async def get_pending_invitations(
    hotel_id: int,
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get pending employee invitations for a hotel.
    VENDOR_ADMIN only.
    """
    service = VendorService(db)
    invitations = await service.get_pending_invitations(hotel_id)
    return invitations


@router.put("/employees/{employee_id}", response_model=HotelEmployeeResponse)
async def update_employee(
    employee_id: int,
    update: HotelEmployeeUpdate,
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Update employee details.
    VENDOR_ADMIN only.
    """
    service = VendorService(db)
    
    try:
        employee = await service.update_employee(
            employee_id=employee_id,
            role=update.role.value if update.role else None,
            permissions=update.permissions,
            is_active=update.is_active
        )
        return employee
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_employee(
    employee_id: int,
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an employee from a hotel.
    VENDOR_ADMIN only.
    """
    service = VendorService(db)
    
    try:
        await service.remove_employee(employee_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/employees/{employee_id}", response_model=HotelEmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN, UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get employee details by ID.
    VENDOR_ADMIN or SYSTEM_ADMIN only.
    """
    service = VendorService(db)
    employee = await service.get_employee(employee_id)
    
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    
    return employee
