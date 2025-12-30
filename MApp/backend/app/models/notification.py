from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from datetime import datetime
import enum


class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    IN_APP = "IN_APP"
    PUSH = "PUSH"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    READ = "READ"


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_key = Column(String(100), nullable=False, index=True)
    channel = Column(PG_ENUM(NotificationChannel, name='notification_channel', create_type=False), nullable=False, index=True)
    subject = Column(String(255))
    body_template = Column(Text, nullable=False)
    variables = Column(JSONB)  # List of required variables
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    notifications = relationship("Notification", back_populates="template")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("notification_templates.id"))
    channel = Column(PG_ENUM(NotificationChannel, name='notification_channel', create_type=False), nullable=False, index=True)
    subject = Column(String(255))
    body = Column(Text, nullable=False)
    notification_metadata = Column(JSONB)  # Additional data (subscription_id, booking_id, etc.)
    status = Column(PG_ENUM(NotificationStatus, name='notification_status', create_type=False), default=NotificationStatus.PENDING, nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), index=True)
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    template = relationship("NotificationTemplate", back_populates="notifications")


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    subscription_alerts = Column(Boolean, default=True)
    booking_alerts = Column(Boolean, default=True)
    marketing_emails = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="notification_preferences")
