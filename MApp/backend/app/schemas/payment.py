"""
Schemas for payment operations.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """Schema for initiating a payment."""
    booking_id: int = Field(..., gt=0, description="ID of the booking to pay for")
    amount: Optional[float] = Field(None, gt=0, description="Payment amount (optional, defaults to invoice total)")
    currency: str = Field(default="USD", description="Currency code (USD, INR, etc.)")
    return_url: Optional[str] = Field(None, description="URL to redirect after payment")
    
    class Config:
        json_schema_extra = {
            "example": {
                "booking_id": 1,
                "amount": 1121.00,
                "currency": "USD",
                "return_url": "https://example.com/payment/success"
            }
        }


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    id: int
    booking_id: int
    invoice_id: int
    amount: float
    currency: str
    payment_method: Optional[str]
    gateway: str
    gateway_payment_id: Optional[str]
    status: str
    client_secret: Optional[str] = Field(None, description="Client secret for completing payment on client side")
    payment_url: Optional[str] = Field(None, description="URL to redirect for payment")
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaymentDetail(BaseModel):
    """Schema for detailed payment information."""
    id: int
    booking_id: int
    invoice_id: int
    amount: float
    currency: str
    payment_method: Optional[str]
    gateway: str
    gateway_payment_id: Optional[str]
    gateway_customer_id: Optional[str]
    status: str
    failure_reason: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Schema for payment webhook."""
    event_type: str
    payment_id: Optional[str] = None
    status: Optional[str] = None
    data: Optional[dict] = None
