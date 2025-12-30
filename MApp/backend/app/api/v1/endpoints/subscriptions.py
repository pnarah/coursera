from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.models.hotel import User, UserRole
from app.models.subscription import SubscriptionStatus
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import (
    SubscriptionPlanResponse,
    VendorSubscriptionCreate,
    VendorSubscriptionResponse,
    VendorSubscriptionWithPlan,
    SubscriptionListResponse,
    SubscriptionRenewRequest,
    SubscriptionCancelRequest,
    SubscriptionExtendRequest,
    PaymentProcessRequest,
    SubscriptionPaymentResponse,
    SubscriptionStatusResponse
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# Subscription Plans Endpoints
@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    db: AsyncSession = Depends(get_db)
):
    """Get all active subscription plans (public endpoint)"""
    service = SubscriptionService(db)
    plans = await service.get_active_plans()
    return plans


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific subscription plan by ID"""
    service = SubscriptionService(db)
    plan = await service.get_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    return plan


# Vendor Subscription Endpoints
@router.post("", response_model=VendorSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: VendorSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription for a hotel (Vendor Admin only)"""
    if current_user.role not in [UserRole.VENDOR_ADMIN, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendor admins can create subscriptions"
        )
    
    service = SubscriptionService(db)
    subscription = await service.create_subscription(
        vendor_id=current_user.id,
        hotel_id=subscription_data.hotel_id,
        plan_id=subscription_data.plan_id,
        auto_renew=subscription_data.auto_renew
    )
    return subscription


@router.get("/my-subscriptions", response_model=SubscriptionListResponse)
async def get_my_subscriptions(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all subscriptions for current vendor"""
    if current_user.role not in [UserRole.VENDOR_ADMIN, UserRole.SYSTEM_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only vendor admins can view subscriptions"
        )
    
    service = SubscriptionService(db)
    
    # Parse status filter
    status_enum = None
    if status_filter:
        try:
            status_enum = SubscriptionStatus(status_filter.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    subscriptions = await service.get_vendor_subscriptions(
        vendor_id=current_user.id,
        status=status_enum
    )
    
    return {
        "subscriptions": subscriptions,
        "total": len(subscriptions)
    }


@router.get("/active", response_model=VendorSubscriptionWithPlan)
async def get_active_subscription(
    current_user: User = Depends(require_role(UserRole.VENDOR_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor's active subscription.
    VENDOR_ADMIN only.
    Returns the most recent active subscription with plan details.
    """
    from sqlalchemy import select, and_
    from app.models.subscription import VendorSubscription, SubscriptionPlan
    from datetime import datetime
    
    # Query for active subscription
    query = (
        select(VendorSubscription)
        .where(
            and_(
                VendorSubscription.vendor_id == current_user.id,
                VendorSubscription.status == SubscriptionStatus.ACTIVE.value,
                VendorSubscription.end_date >= datetime.now().date()
            )
        )
        .order_by(VendorSubscription.end_date.desc())
    )
    
    result = await db.execute(query)
    subscription = result.scalars().first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return subscription


@router.get("/{subscription_id}", response_model=VendorSubscriptionWithPlan)
async def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific subscription by ID"""
    subscription = await db.get(VendorSubscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SYSTEM_ADMIN]:
        if subscription.vendor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this subscription"
            )
    
    return subscription


@router.post("/{subscription_id}/pay", response_model=SubscriptionPaymentResponse)
async def process_subscription_payment(
    subscription_id: int,
    payment_data: PaymentProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process payment for a subscription"""
    from app.models.subscription import VendorSubscription
    
    subscription = await db.get(VendorSubscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SYSTEM_ADMIN]:
        if subscription.vendor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to pay for this subscription"
            )
    
    service = SubscriptionService(db)
    payment = await service.process_payment(
        subscription_id=subscription_id,
        payment_method=payment_data.payment_method,
        transaction_id=payment_data.transaction_id,
        payment_gateway=payment_data.payment_gateway,
        processed_by=current_user.id
    )
    return payment


@router.post("/{subscription_id}/renew", response_model=VendorSubscriptionResponse)
async def renew_subscription(
    subscription_id: int,
    renew_data: SubscriptionRenewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Renew a subscription"""
    from app.models.subscription import VendorSubscription
    
    subscription = await db.get(VendorSubscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SYSTEM_ADMIN]:
        if subscription.vendor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to renew this subscription"
            )
    
    service = SubscriptionService(db)
    new_subscription = await service.renew_subscription(
        subscription_id=subscription_id,
        plan_id=renew_data.plan_id
    )
    return new_subscription


@router.post("/{subscription_id}/cancel", response_model=VendorSubscriptionResponse)
async def cancel_subscription(
    subscription_id: int,
    cancel_data: SubscriptionCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a subscription"""
    from app.models.subscription import VendorSubscription
    
    subscription = await db.get(VendorSubscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SYSTEM_ADMIN]:
        if subscription.vendor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this subscription"
            )
    
    service = SubscriptionService(db)
    cancelled_subscription = await service.cancel_subscription(
        subscription_id=subscription_id,
        cancellation_reason=cancel_data.cancellation_reason
    )
    return cancelled_subscription


@router.post("/{subscription_id}/extend", response_model=VendorSubscriptionResponse)
async def extend_subscription(
    subscription_id: int,
    extend_data: SubscriptionExtendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually extend a subscription (System Admin only)"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admins can extend subscriptions"
        )
    
    service = SubscriptionService(db)
    extended_subscription = await service.extend_subscription(
        subscription_id=subscription_id,
        extension_days=extend_data.extension_days,
        extended_by=current_user
    )
    return extended_subscription


@router.get("/hotel/{hotel_id}/status", response_model=SubscriptionStatusResponse)
async def check_hotel_subscription_status(
    hotel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check subscription status for a hotel"""
    service = SubscriptionService(db)
    is_active, message = await service.check_subscription_status(hotel_id)
    
    subscription = None
    if is_active:
        subscription = await service.get_hotel_subscription(hotel_id)
    
    return {
        "is_active": is_active,
        "message": message,
        "subscription": subscription
    }


@router.get("/{subscription_id}/payments", response_model=List[SubscriptionPaymentResponse])
async def get_subscription_payments(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all payments for a subscription"""
    from app.models.subscription import VendorSubscription
    
    subscription = await db.get(VendorSubscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check permissions
    if current_user.role not in [UserRole.SYSTEM_ADMIN]:
        if subscription.vendor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view payments for this subscription"
            )
    
    service = SubscriptionService(db)
    payments = await service.get_subscription_payments(subscription_id)
    return payments
