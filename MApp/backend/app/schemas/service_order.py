"""
Pydantic schemas for in-stay service ordering.
"""
from typing import Optional
from pydantic import BaseModel, Field


class AddServiceRequest(BaseModel):
    """Schema for adding a service to an existing booking."""
    service_id: int = Field(..., gt=0, description="ID of the service to add")
    quantity: int = Field(1, gt=0, le=100, description="Quantity of the service")
    notes: Optional[str] = Field(None, max_length=500, description="Special notes or instructions")


class UpdateServiceStatusRequest(BaseModel):
    """Schema for updating service order status."""
    status: str = Field(..., description="New status (confirmed, in_progress, completed, cancelled)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed"
            }
        }
