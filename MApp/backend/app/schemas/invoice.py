"""
Schemas for invoice operations.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    """Schema for individual line item in invoice."""
    description: str = Field(..., description="Description of the charge")
    item_type: str = Field(..., description="Type: 'room' or 'service'")
    quantity: int = Field(..., description="Quantity")
    unit_price: float = Field(..., description="Price per unit")
    total_price: float = Field(..., description="Total for this line item")
    status: Optional[str] = Field(None, description="Status for service items")


class InvoiceDetail(BaseModel):
    """Schema for invoice detail response."""
    id: int
    booking_id: int
    invoice_number: str
    
    # Line items
    line_items: List[InvoiceLineItem] = Field(default_factory=list, description="Itemized charges")
    
    # Amount breakdown
    room_subtotal: float = Field(..., description="Total room charges")
    services_subtotal: float = Field(..., description="Total service charges")
    subtotal: float = Field(..., description="Subtotal before tax and discount")
    tax_rate: float = Field(..., description="Tax rate (e.g., 0.18 for 18%)")
    tax_amount: float = Field(..., description="Calculated tax amount")
    discount_amount: float = Field(..., description="Total discounts applied")
    total_amount: float = Field(..., description="Final amount to be paid")
    
    # Metadata
    status: str = Field(..., description="Invoice status: draft, issued, paid, cancelled")
    issued_at: Optional[datetime] = Field(None, description="When invoice was issued")
    paid_at: Optional[datetime] = Field(None, description="When invoice was paid")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
