# Task 04: Subscription Management System

**Priority:** High  
**Estimated Duration:** 5-6 days  
**Dependencies:** TASK_02_USER_ROLES_AND_RBAC  
**Status:** Not Started

---

## Overview

Implement comprehensive subscription management for vendors/hotels including plan selection, payment processing, lifecycle management, grace periods, and automated renewals.

---

## Objectives

1. Create subscription plans (Quarterly, Half-Yearly, Annual)
2. Implement subscription lifecycle management
3. Add payment integration
4. Create grace period handling
5. Implement auto-renewal system
6. Add subscription expiry notifications
7. Enable/disable hotels based on subscription status
8. System admin manual extension capability

---

## Backend Tasks

### 1. Database Schema

Create migration `004_create_subscriptions.py`:

```sql
-- Subscription plans table
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,  -- 'QUARTERLY', 'HALF_YEARLY', 'ANNUAL'
    duration_months INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    max_rooms INTEGER,
    features JSONB,
    discount_percentage DECIMAL(5, 2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Vendor subscriptions
CREATE TABLE vendor_subscriptions (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES subscription_plans(id),
    plan_type VARCHAR(50) NOT NULL,  -- Snapshot at time of purchase
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, ACTIVE, EXPIRED, GRACE_PERIOD, DISABLED, CANCELLED
    grace_period_end DATE,
    auto_renew BOOLEAN DEFAULT false,
    payment_method_id INTEGER,
    next_billing_date DATE,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(hotel_id, start_date)
);

CREATE INDEX idx_subscriptions_vendor ON vendor_subscriptions(vendor_id);
CREATE INDEX idx_subscriptions_hotel ON vendor_subscriptions(hotel_id);
CREATE INDEX idx_subscriptions_status ON vendor_subscriptions(status);
CREATE INDEX idx_subscriptions_end_date ON vendor_subscriptions(end_date);

-- Subscription payments
CREATE TABLE subscription_payments (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES vendor_subscriptions(id),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_date TIMESTAMP DEFAULT NOW(),
    payment_method VARCHAR(50),  -- 'credit_card', 'debit_card', 'bank_transfer', etc.
    transaction_id VARCHAR(255) UNIQUE,
    payment_gateway VARCHAR(50),  -- 'stripe', 'paypal', etc.
    gateway_response JSONB,
    status VARCHAR(20) NOT NULL,  -- PENDING, COMPLETED, FAILED, REFUNDED
    failure_reason TEXT,
    notes TEXT,
    processed_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_subscription ON subscription_payments(subscription_id);
CREATE INDEX idx_payments_status ON subscription_payments(status);
CREATE INDEX idx_payments_transaction ON subscription_payments(transaction_id);

-- Subscription notifications
CREATE TABLE subscription_notifications (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES vendor_subscriptions(id),
    notification_type VARCHAR(50) NOT NULL,  -- EXPIRY_30_DAYS, EXPIRY_15_DAYS, etc.
    recipient_user_id INTEGER REFERENCES users(id),
    channels VARCHAR(50)[],  -- ['email', 'sms', 'in_app']
    sent_at TIMESTAMP,
    delivery_status VARCHAR(20),  -- PENDING, SENT, FAILED
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_subscription ON subscription_notifications(subscription_id);
CREATE INDEX idx_notifications_sent ON subscription_notifications(sent_at);

-- Add subscription check to hotels
ALTER TABLE hotels ADD COLUMN subscription_id INTEGER REFERENCES vendor_subscriptions(id);
ALTER TABLE hotels ADD COLUMN is_subscription_active BOOLEAN DEFAULT false;
```

### 2. Models

Create `app/models/subscription.py`:

```python
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from datetime import date, datetime, timedelta
import enum

class SubscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    GRACE_PERIOD = "GRACE_PERIOD"
    DISABLED = "DISABLED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    duration_months = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    max_rooms = Column(Integer)
    features = Column(JSONB)
    discount_percentage = Column(Numeric(5, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class VendorSubscription(Base):
    __tablename__ = "vendor_subscriptions"
    
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    plan_type = Column(String(50), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default=SubscriptionStatus.PENDING.value)
    grace_period_end = Column(Date)
    auto_renew = Column(Boolean, default=False)
    payment_method_id = Column(Integer)
    next_billing_date = Column(Date)
    cancelled_at = Column(DateTime(timezone=True))
    cancellation_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    vendor = relationship("User", foreign_keys=[vendor_id])
    hotel = relationship("Hotel", foreign_keys=[hotel_id], back_populates="subscription")
    plan = relationship("SubscriptionPlan")
    payments = relationship("SubscriptionPayment", back_populates="subscription")
    
    @property
    def days_remaining(self) -> int:
        """Calculate days remaining until expiry"""
        if self.end_date:
            return (self.end_date - date.today()).days
        return 0
    
    @property
    def is_expiring_soon(self) -> bool:
        """Check if subscription is expiring in next 30 days"""
        return 0 < self.days_remaining <= 30

class SubscriptionPayment(Base):
    __tablename__ = "subscription_payments"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("vendor_subscriptions.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    payment_method = Column(String(50))
    transaction_id = Column(String(255), unique=True)
    payment_gateway = Column(String(50))
    gateway_response = Column(JSONB)
    status = Column(String(20), nullable=False)
    failure_reason = Column(Text)
    notes = Column(Text)
    processed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    subscription = relationship("VendorSubscription", back_populates="payments")

class SubscriptionNotification(Base):
    __tablename__ = "subscription_notifications"
    
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("vendor_subscriptions.id"))
    notification_type = Column(String(50), nullable=False)
    recipient_user_id = Column(Integer, ForeignKey("users.id"))
    channels = Column(ARRAY(String(50)))
    sent_at = Column(DateTime(timezone=True))
    delivery_status = Column(String(20))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 3. Subscription Service

Create `app/services/subscription_service.py`:

```python
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fastapi import HTTPException
from app.models.subscription import (
    SubscriptionPlan, VendorSubscription, SubscriptionPayment,
    SubscriptionStatus, PaymentStatus
)
from app.models.user import User, UserRole
from app.models.hotel import Hotel

class SubscriptionService:
    GRACE_PERIOD_DAYS = 7
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_active_plans(self) -> List[SubscriptionPlan]:
        """Get all active subscription plans"""
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def create_subscription(
        self,
        vendor_id: int,
        hotel_id: int,
        plan_id: int,
        auto_renew: bool = False
    ) -> VendorSubscription:
        """Create new subscription for vendor/hotel"""
        # Get plan
        plan = await self.db.get(SubscriptionPlan, plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Plan not found or inactive")
        
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
        transaction_id: str,
        payment_gateway: str = "stripe"
    ) -> SubscriptionPayment:
        """Process subscription payment"""
        subscription = await self.db.get(VendorSubscription, subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Create payment record
        payment = SubscriptionPayment(
            subscription_id=subscription_id,
            amount=subscription.amount,
            currency=subscription.currency,
            payment_method=payment_method,
            transaction_id=transaction_id,
            payment_gateway=payment_gateway,
            status=PaymentStatus.PENDING
        )
        
        self.db.add(payment)
        
        try:
            # TODO: Integrate with actual payment gateway
            # For now, simulate successful payment
            payment.status = PaymentStatus.COMPLETED
            payment.gateway_response = {"status": "success", "simulated": True}
            
            # Activate subscription
            subscription.status = SubscriptionStatus.ACTIVE
            
            # Enable hotel
            hotel = await self.db.get(Hotel, subscription.hotel_id)
            if hotel:
                hotel.is_active = True
                hotel.subscription_id = subscription_id
                hotel.is_subscription_active = True
            
            await self.db.commit()
            await self.db.refresh(payment)
            
            return payment
            
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = str(e)
            await self.db.commit()
            raise HTTPException(status_code=400, detail=f"Payment failed: {str(e)}")
    
    async def check_subscription_status(self, hotel_id: int) -> tuple[bool, Optional[str]]:
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
            days_left = (subscription.grace_period_end - date.today()).days
            return True, f"Grace period: {days_left} days remaining"
        
        return True, None
    
    async def renew_subscription(
        self,
        subscription_id: int,
        plan_id: Optional[int] = None
    ) -> VendorSubscription:
        """Renew existing subscription"""
        old_subscription = await self.db.get(VendorSubscription, subscription_id)
        if not old_subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Use same plan or new plan
        if plan_id:
            plan = await self.db.get(SubscriptionPlan, plan_id)
        else:
            plan = await self.db.get(SubscriptionPlan, old_subscription.plan_id)
        
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Plan not found")
        
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
    
    async def process_expiring_subscriptions(self):
        """Background job: Process expiring subscriptions"""
        today = date.today()
        
        # Find subscriptions expiring today
        stmt = select(VendorSubscription).where(
            and_(
                VendorSubscription.end_date == today,
                VendorSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        result = await self.db.execute(stmt)
        expiring_subscriptions = result.scalars().all()
        
        for subscription in expiring_subscriptions:
            if subscription.auto_renew:
                # Attempt auto-renewal
                try:
                    await self.auto_renew_subscription(subscription.id)
                except Exception as e:
                    # Auto-renewal failed, start grace period
                    await self._start_grace_period(subscription)
            else:
                # No auto-renewal, start grace period
                await self._start_grace_period(subscription)
        
        await self.db.commit()
    
    async def _start_grace_period(self, subscription: VendorSubscription):
        """Start grace period for expired subscription"""
        subscription.status = SubscriptionStatus.GRACE_PERIOD
        subscription.grace_period_end = date.today() + timedelta(days=self.GRACE_PERIOD_DAYS)
    
    async def process_grace_period_end(self):
        """Background job: Disable subscriptions after grace period"""
        today = date.today()
        
        stmt = select(VendorSubscription).where(
            and_(
                VendorSubscription.status == SubscriptionStatus.GRACE_PERIOD,
                VendorSubscription.grace_period_end < today
            )
        )
        result = await self.db.execute(stmt)
        expired_subscriptions = result.scalars().all()
        
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
        
        # Disable hotel employees
        # (handled by access control checking subscription status)
    
    async def extend_subscription(
        self,
        subscription_id: int,
        extension_days: int,
        extended_by: User
    ) -> VendorSubscription:
        """Manually extend subscription (System Admin only)"""
        if extended_by.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only system admins can extend subscriptions"
            )
        
        subscription = await self.db.get(VendorSubscription, subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        subscription.end_date = subscription.end_date + timedelta(days=extension_days)
        
        if subscription.status == SubscriptionStatus.DISABLED:
            subscription.status = SubscriptionStatus.ACTIVE
            # Re-enable hotel
            hotel = await self.db.get(Hotel, subscription.hotel_id)
            if hotel:
                hotel.is_active = True
                hotel.is_subscription_active = True
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        return subscription
```

### 4. Seed Subscription Plans

Create `backend/scripts/seed_subscription_plans.py`:

```python
import asyncio
from app.db.session import async_session
from app.models.subscription import SubscriptionPlan

async def seed_plans():
    async with async_session() as db:
        plans = [
            SubscriptionPlan(
                name="Quarterly Plan",
                code="QUARTERLY",
                duration_months=3,
                price=299.00,
                max_rooms=50,
                features={
                    "max_rooms": 50,
                    "unlimited_bookings": True,
                    "analytics": "basic",
                    "support": "email"
                },
                discount_percentage=0
            ),
            SubscriptionPlan(
                name="Half-Yearly Plan",
                code="HALF_YEARLY",
                duration_months=6,
                price=549.00,
                max_rooms=100,
                features={
                    "max_rooms": 100,
                    "unlimited_bookings": True,
                    "analytics": "advanced",
                    "support": "priority",
                    "custom_branding": True
                },
                discount_percentage=8.00
            ),
            SubscriptionPlan(
                name="Annual Plan",
                code="ANNUAL",
                duration_months=12,
                price=999.00,
                max_rooms=None,  # Unlimited
                features={
                    "max_rooms": "unlimited",
                    "unlimited_bookings": True,
                    "analytics": "premium",
                    "support": "24/7_phone",
                    "custom_branding": True,
                    "api_access": True,
                    "dedicated_account_manager": True
                },
                discount_percentage=17.00
            )
        ]
        
        for plan in plans:
            db.add(plan)
        
        await db.commit()
        print("Subscription plans seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_plans())
```

---

## Acceptance Criteria

- ✅ Three subscription plans created and seeded
- ✅ Vendors can create subscriptions
- ✅ Payment processing workflow implemented
- ✅ Subscription activates on payment success
- ✅ Hotels enabled/disabled based on subscription
- ✅ Grace period (7 days) after expiry
- ✅ Auto-renewal system works
- ✅ Manual extension by System Admin
- ✅ Subscription status checks in middleware
- ✅ Background jobs process expiring subscriptions

---

## Next Task

**TASK_05_NOTIFICATION_SYSTEM.md** - Implement multi-channel notification system
