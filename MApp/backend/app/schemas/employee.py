"""Employee and vendor management schemas."""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.employee import EmployeeRole, ApprovalStatus
import re


class VendorApprovalRequestCreate(BaseModel):
    """Schema for creating a vendor approval request"""
    business_name: str = Field(..., min_length=1, max_length=255, description="Business name")
    business_address: Optional[str] = Field(None, description="Business address")
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax ID or business registration number")
    contact_email: str = Field(..., description="Contact email address")
    contact_phone: str = Field(..., description="Contact phone number (10-15 digits)")
    
    @field_validator('contact_email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('contact_phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format"""
        digits_only = re.sub(r'\D', '', v)
        if not 10 <= len(digits_only) <= 15:
            raise ValueError('Phone number must be 10-15 digits')
        return digits_only


class VendorApprovalRequestResponse(BaseModel):
    """Schema for vendor approval request response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    business_name: str
    business_address: Optional[str] = None
    tax_id: Optional[str] = None
    contact_email: str
    contact_phone: str
    status: ApprovalStatus
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime


class VendorApprovalAction(BaseModel):
    """Schema for approving/rejecting vendor request"""
    approved: bool = Field(..., description="True to approve, False to reject")
    rejection_reason: Optional[str] = Field(None, description="Required if rejecting")
    
    @field_validator('rejection_reason')
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure rejection reason is provided when rejecting"""
        if not info.data.get('approved') and not v:
            raise ValueError('Rejection reason is required when rejecting request')
        return v


class EmployeeInvitationCreate(BaseModel):
    """Schema for creating an employee invitation"""
    hotel_id: int = Field(..., description="Hotel ID")
    mobile_number: str = Field(..., description="Mobile number of employee to invite (10-15 digits)")
    role: EmployeeRole = Field(..., description="Employee role")
    permissions: Optional[Dict[str, bool]] = Field(None, description="Custom permissions")
    
    @field_validator('mobile_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format"""
        digits_only = re.sub(r'\D', '', v)
        if not 10 <= len(digits_only) <= 15:
            raise ValueError('Phone number must be 10-15 digits')
        return digits_only


class EmployeeInvitationResponse(BaseModel):
    """Schema for employee invitation response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    hotel_id: int
    mobile_number: str
    role: str
    permissions: Optional[Dict[str, bool]] = None
    token: str
    invited_by: int
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime


class EmployeeInvitationAccept(BaseModel):
    """Schema for accepting an employee invitation"""
    token: str = Field(..., min_length=1, description="Invitation token")


class HotelEmployeeResponse(BaseModel):
    """Schema for hotel employee response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    hotel_id: int
    role: str
    permissions: Optional[Dict[str, bool]] = None
    is_active: bool
    invited_by: Optional[int] = None
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class HotelEmployeeUpdate(BaseModel):
    """Schema for updating hotel employee"""
    role: Optional[EmployeeRole] = Field(None, description="Employee role")
    permissions: Optional[Dict[str, bool]] = Field(None, description="Custom permissions")
    is_active: Optional[bool] = Field(None, description="Active status")


class HotelEmployeeListItem(BaseModel):
    """Schema for employee in list (with user details)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    hotel_id: int
    role: str
    is_active: bool
    joined_at: Optional[datetime] = None
    # User details (to be added via join)
    user_name: Optional[str] = None
    user_mobile: Optional[str] = None
    user_email: Optional[str] = None


class VendorRequestsListResponse(BaseModel):
    """Response wrapper for vendor approval requests list"""
    requests: List[VendorApprovalRequestResponse]
    
    model_config = ConfigDict(from_attributes=True)
