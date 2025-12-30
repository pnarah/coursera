from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from fastapi import HTTPException, status
from app.models.subscription import (
    SubscriptionPlan, VendorSubscription, SubscriptionPayment,
    SubscriptionNotification, SubscriptionStatus, PaymentStatus
)
from app.models.hotel import User, UserRole, Hotel
import uuid


class SubscriptionService:
    """Service for managing vendor subscriptions"""
    
    GRACE_PERIOD_DAYS = 7
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_active_plans(self) -> List[SubscriptionPlan]:
        """Get all active subscription plans"""
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_plan_by_id(self, plan_id: int) -> Optional[SubscriptionPlan]:
        """Get a specific subscription plan by ID"""
        return await self.db.get(SubscriptionPlan, plan_id)
    
    async def get_plan_by_code(self, code: str) -> Optional[SubscriptionPlan]:
        """Get a specific subscription plan by code"""
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_subscription(
        self,
        vendor_id: int,
        hotel_id: int,
        plan_id: int,
        auto_renew: bool = False
    ) -> VendorSubscription:
        """Create new subscription for vendor/hotel"""
        # Verify vendor exists and has correct role
        vendor = await self.db.get(User, vendor_id)
        if not vendor or vendor.role != UserRole.VENDOR_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a vendor admin"
            )
        
        # Verify hotel exists
        hotel = await self.db.get(Hotel, hotel_id)
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hotel not found"
            )
        
        # Get plan
        plan = await self.db.get(SubscriptionPlan, plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found or inactive"
            )
        
        # Calculate dates
        start_date = date.today()
        end_date = start_date + timedelta(days=plan.duration_months * 30)
        
        # Create subscription
        subscription = VendorSubscription(
            vendor_id=vendor_id,
            hotel_id=hotel_id,
            plan_id=plan_id,
            plan_type=plan.code,
            amount=plan.price,
            currency=plan.currency,
            start_date=start_date,
            end_date=end_date,
            status=SubscriptionStatus.PENDING,
            auto_renew=auto_renew,
            next_billing_date=end_date if auto_renew else None
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        return subscription
    
    async def process_payment(
        self,
        subscription_id: int,
        payment_method: str,
        transaction_id: Optional[str] = None,
        payment_gateway: str = "stripe",
        processed_by: Optional[int] = None
    ) -> SubscriptionPayment:
        """Process subscription payment"""
        subscription = await self.db.get(VendorSubscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Generate transaction ID if not provided
        if not transaction_id:
            transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
        
        # Create payment record
        payment = SubscriptionPayment(
            subscription_id=subscription_id,
            amount=subscription.amount,
            currency=subscription.currency,
            payment_method=payment_method,
            transaction_id=transaction_id,
            payment_gateway=payment_gateway,
            status=PaymentStatus.PENDING,
            processed_by=processed_by
        )
        
        self.db.add(payment)
        
        try:
            # TODO: Integrate with actual payment gateway (Stripe, PayPal, etc.)
            # For now, simulate successful payment
            payment.status = PaymentStatus.COMPLETED
            payment.gateway_response = {
                "status": "success",
                "simulated": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Activate subscription
            subscription.status = SubscriptionStatus.ACTIVE
            
            # Enable hotel
            hotel = await self.db.get(Hotel, subscription.hotel_id)
            if hotel:
                hotel.is_active = True
                hotel.is_subscription_active = True
            
            await self.db.commit()
            await self.db.refresh(payment)
            
            return payment
            
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = str(e)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed: {str(e)}"
            )
    
    async def check_subscription_status(
        self,
        hotel_id: int
    ) -> tuple[bool, Optional[str]]:
        """Check if hotel has active subscription"""
        stmt = select(VendorSubscription).where(
            and_(
                VendorSubscription.hotel_id == hotel_id,
                VendorSubscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.GRACE_PERIOD
                ])
            )
        ).order_by(VendorSubscription.end_date.desc())
        
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return False, "No active subscription"
        
        if subscription.status == SubscriptionStatus.GRACE_PERIOD:
            if subscription.grace_period_end:
                days_left = (subscription.grace_period_end - date.today()).days
                return True, f"Grace period: {days_left} days remaining"
            return True, "Grace period active"
        
        return True, None
    
    async def get_hotel_subscription(
        self,
        hotel_id: int
    ) -> Optional[VendorSubscription]:
        """Get current active subscription for hotel"""
        stmt = select(VendorSubscription).where(
            and_(
                VendorSubscription.hotel_id == hotel_id,
                VendorSubscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.GRACE_PERIOD,
                    SubscriptionStatus.PENDING
                ])
            )
        ).order_by(VendorSubscription.end_date.desc())
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_vendor_subscriptions(
        self,
        vendor_id: int,
        status: Optional[SubscriptionStatus] = None
    ) -> List[VendorSubscription]:
        """Get all subscriptions for a vendor"""
        stmt = select(VendorSubscription).where(
            VendorSubscription.vendor_id == vendor_id
        )
        
        if status:
            stmt = stmt.where(VendorSubscription.status == status)
        
        stmt = stmt.order_by(VendorSubscription.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def renew_subscription(
        self,
        subscription_id: int,
        plan_id: Optional[int] = None
    ) -> VendorSubscription:
        """Renew existing subscription"""
        old_subscription = await self.db.get(VendorSubscription, subscription_id)
        if not old_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Use same plan or new plan
        if plan_id:
            plan = await self.db.get(SubscriptionPlan, plan_id)
        else:
            plan = await self.db.get(SubscriptionPlan, old_subscription.plan_id)
        
        if not plan or not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found or inactive"
            )
        
        # Create new subscription
        start_date = max(old_subscription.end_date + timedelta(days=1), date.today())
        end_date = start_date + timedelta(days=plan.duration_months * 30)
        
        new_subscription = VendorSubscription(
            vendor_id=old_subscription.vendor_id,
            hotel_id=old_subscription.hotel_id,
            plan_id=plan.id,
            plan_type=plan.code,
            amount=plan.price,
            currency=plan.currency,
            start_date=start_date,
            end_date=end_date,
            status=SubscriptionStatus.PENDING,
            auto_renew=old_subscription.auto_renew
        )
        
        self.db.add(new_subscription)
        
        # Mark old subscription as expired
        old_subscription.status = SubscriptionStatus.EXPIRED
        
        await self.db.commit()
        await self.db.refresh(new_subscription)
        
        return new_subscription
    
    async def auto_renew_subscription(
        self,
        subscription_id: int
    ) -> VendorSubscription:
        """Automatically renew a subscription (for background jobs)"""
        subscription = await self.db.get(VendorSubscription, subscription_id)
        if not subscription or not subscription.auto_renew:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription not found or auto-renew not enabled"
            )
        
        # Create renewed subscription
        new_subscription = await self.renew_subscription(subscription_id)
        
        # Automatically process payment (in real implementation, use saved payment method)
        try:
            await self.process_payment(
                subscription_id=new_subscription.id,
                payment_method=subscription.payment_method_id or "saved_card",
                payment_gateway="stripe"
            )
        except Exception as e:
            # Auto-renewal payment failed, will enter grace period
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Auto-renewal payment failed: {str(e)}"
            )
        
        return new_subscription
    
    async def cancel_subscription(
        self,
        subscription_id: int,
        cancellation_reason: Optional[str] = None
    ) -> VendorSubscription:
        """Cancel a subscription"""
        subscription = await self.db.get(VendorSubscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
        subscription.cancellation_reason = cancellation_reason
        subscription.auto_renew = False
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        return subscription
    
    async def process_expiring_subscriptions(self):
        """Background job: Process subscriptions expiring today"""
        today = date.today()
        
        # Find subscriptions expiring today
        stmt = select(VendorSubscription).where(
            and_(
                VendorSubscription.end_date == today,
                VendorSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        result = await self.db.execute(stmt)
        expiring_subscriptions = list(result.scalars().all())
        
        for subscription in expiring_subscriptions:
            if subscription.auto_renew:
                # Attempt auto-renewal
                try:
                    await self.auto_renew_subscription(subscription.id)
                except Exception:
                    # Auto-renewal failed, start grace period
                    await self._start_grace_period(subscription)
            else:
                # No auto-renewal, start grace period
                await self._start_grace_period(subscription)
        
        await self.db.commit()
    
    async def _start_grace_period(self, subscription: VendorSubscription):
        """Start grace period for expired subscription"""
        subscription.status = SubscriptionStatus.GRACE_PERIOD
        subscription.grace_period_end = date.today() + timedelta(
            days=self.GRACE_PERIOD_DAYS
        )
    
    async def process_grace_period_end(self):
        """Background job: Disable subscriptions after grace period ends"""
        today = date.today()
        
        stmt = select(VendorSubscription).where(
            and_(
                VendorSubscription.status == SubscriptionStatus.GRACE_PERIOD,
                VendorSubscription.grace_period_end < today
            )
        )
        result = await self.db.execute(stmt)
        expired_subscriptions = list(result.scalars().all())
        
        for subscription in expired_subscriptions:
            await self.disable_subscription(subscription.id)
        
        await self.db.commit()
    
    async def disable_subscription(self, subscription_id: int):
        """Disable subscription and hotel"""
        subscription = await self.db.get(VendorSubscription, subscription_id)
        if not subscription:
            return
        
        subscription.status = SubscriptionStatus.DISABLED
        
        # Disable hotel
        hotel = await self.db.get(Hotel, subscription.hotel_id)
        if hotel:
            hotel.is_active = False
            hotel.is_subscription_active = False
    
    async def extend_subscription(
        self,
        subscription_id: int,
        extension_days: int,
        extended_by: User
    ) -> VendorSubscription:
        """Manually extend subscription (System Admin only)"""
        if extended_by.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system admins can extend subscriptions"
            )
        
        subscription = await self.db.get(VendorSubscription, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        subscription.end_date = subscription.end_date + timedelta(days=extension_days)
        
        if subscription.status in [SubscriptionStatus.DISABLED, SubscriptionStatus.EXPIRED]:
            subscription.status = SubscriptionStatus.ACTIVE
            # Re-enable hotel
            hotel = await self.db.get(Hotel, subscription.hotel_id)
            if hotel:
                hotel.is_active = True
                hotel.is_subscription_active = True
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        return subscription
    
    async def get_subscription_payments(
        self,
        subscription_id: int
    ) -> List[SubscriptionPayment]:
        """Get all payments for a subscription"""
        stmt = select(SubscriptionPayment).where(
            SubscriptionPayment.subscription_id == subscription_id
        ).order_by(SubscriptionPayment.payment_date.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
