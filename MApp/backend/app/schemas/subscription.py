from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal


# Subscription Plan Schemas
class SubscriptionPlanBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    duration_months: int = Field(..., gt=0)
    price: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    max_rooms: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    discount_percentage: Decimal = Field(default=0, ge=0, le=100, decimal_places=2)
    is_active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    max_rooms: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    discount_percentage: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    is_active: Optional[bool] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Vendor Subscription Schemas
class VendorSubscriptionBase(BaseModel):
    vendor_id: int
    hotel_id: int
    plan_id: int
    auto_renew: bool = False


class VendorSubscriptionCreate(BaseModel):
    hotel_id: int
    plan_id: int
    auto_renew: bool = False


class VendorSubscriptionResponse(BaseModel):
    id: int
    vendor_id: int
    hotel_id: int
    plan_id: Optional[int] = None
    plan_type: str
    amount: Decimal
    currency: str
    start_date: date
    end_date: date
    status: str
    grace_period_end: Optional[date] = None
    auto_renew: bool
    payment_method_id: Optional[int] = None
    next_billing_date: Optional[date] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    days_remaining: Optional[int] = None
    is_expiring_soon: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


class VendorSubscriptionWithPlan(VendorSubscriptionResponse):
    plan: Optional[SubscriptionPlanResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


class SubscriptionRenewRequest(BaseModel):
    plan_id: Optional[int] = None


class SubscriptionCancelRequest(BaseModel):
    cancellation_reason: Optional[str] = None


class SubscriptionExtendRequest(BaseModel):
    extension_days: int = Field(..., gt=0, description="Number of days to extend subscription")


# Payment Schemas
class PaymentProcessRequest(BaseModel):
    payment_method: str = Field(..., max_length=50, description="Payment method (credit_card, debit_card, etc.)")
    transaction_id: Optional[str] = Field(None, max_length=255, description="External transaction ID")
    payment_gateway: str = Field(default="stripe", max_length=50)


class SubscriptionPaymentResponse(BaseModel):
    id: int
    subscription_id: int
    amount: Decimal
    currency: str
    payment_date: datetime
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    payment_gateway: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    notes: Optional[str] = None
    processed_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Notification Schemas
class SubscriptionNotificationResponse(BaseModel):
    id: int
    subscription_id: int
    notification_type: str
    recipient_user_id: Optional[int] = None
    channels: Optional[List[str]] = None
    sent_at: Optional[datetime] = None
    delivery_status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Status Check Response
class SubscriptionStatusResponse(BaseModel):
    is_active: bool
    message: Optional[str] = None
    subscription: Optional[VendorSubscriptionResponse] = None


# List Response
class SubscriptionListResponse(BaseModel):
    subscriptions: List[VendorSubscriptionWithPlan]
    total: int
