from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.notification import NotificationChannel, NotificationStatus


# Notification Template Schemas
class NotificationTemplateBase(BaseModel):
    template_key: str = Field(..., max_length=100)
    channel: NotificationChannel
    subject: Optional[str] = Field(None, max_length=255)
    body_template: str
    variables: Optional[List[str]] = None
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateResponse(NotificationTemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Notification Preferences Schemas
class NotificationPreferencesBase(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    subscription_alerts: bool = True
    booking_alerts: bool = True
    marketing_emails: bool = False


class NotificationPreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    subscription_alerts: Optional[bool] = None
    booking_alerts: Optional[bool] = None
    marketing_emails: Optional[bool] = None


class NotificationPreferencesResponse(NotificationPreferencesBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Notification Schemas
class NotificationCreate(BaseModel):
    user_id: int
    template_key: str
    channel: NotificationChannel
    variables: Dict[str, Any] = {}
    scheduled_at: Optional[datetime] = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    channel: NotificationChannel
    subject: Optional[str] = None
    body: str
    metadata: Optional[Dict[str, Any]] = None
    status: NotificationStatus
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


# Request schemas for creating notifications with template
class SendNotificationRequest(BaseModel):
    template_key: str
    channel: NotificationChannel
    variables: Dict[str, Any] = {}
    scheduled_at: Optional[datetime] = None


class BulkNotificationRequest(BaseModel):
    user_ids: List[int]
    template_key: str
    channel: NotificationChannel
    variables: Dict[str, Any] = {}
