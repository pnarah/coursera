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
    
    # Relationships
    subscriptions = relationship("VendorSubscription", back_populates="plan")


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
    hotel = relationship("Hotel", back_populates="subscriptions", foreign_keys=[hotel_id])
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    payments = relationship("SubscriptionPayment", back_populates="subscription", cascade="all, delete-orphan")
    notifications = relationship("SubscriptionNotification", back_populates="subscription", cascade="all, delete-orphan")
    
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
    
    # Relationships
    subscription = relationship("VendorSubscription", back_populates="payments")
    processor = relationship("User", foreign_keys=[processed_by])


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
    
    # Relationships
    subscription = relationship("VendorSubscription", back_populates="notifications")
    recipient = relationship("User", foreign_keys=[recipient_user_id])
