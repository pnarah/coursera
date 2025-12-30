from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class PlatformMetrics(BaseModel):
    """Platform-wide metrics for admin dashboard"""
    total_users: int
    total_vendors: int
    total_hotels: int
    active_subscriptions: int
    expired_subscriptions: int
    new_users_this_week: int
    pending_vendor_requests: int

    model_config = ConfigDict(from_attributes=True)


class VendorListItem(BaseModel):
    """Vendor list item with details"""
    user_id: int
    mobile_number: str
    total_hotels: int
    subscription_status: str
    subscription_end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionExtension(BaseModel):
    """Request to extend subscription"""
    subscription_id: int
    extend_days: int
    reason: str


class SystemConfigUpdate(BaseModel):
    """Update system configuration"""
    config_key: str
    config_value: Dict[str, Any]


class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: int
    admin_user_id: int
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorsListResponse(BaseModel):
    """Response wrapper for vendors list"""
    vendors: List[VendorListItem]

    model_config = ConfigDict(from_attributes=True)
