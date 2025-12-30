from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class AdminAuditLog(Base):
    """Track all admin actions for compliance and auditing"""
    __tablename__ = "admin_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "SUBSCRIPTION_EXTENDED", "VENDOR_APPROVED"
    resource_type = Column(String(50), nullable=False, index=True)  # e.g., "SUBSCRIPTION", "VENDOR"
    resource_id = Column(Integer, nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    admin_user = relationship("User", foreign_keys=[admin_user_id])


class SystemConfig(Base):
    """System-wide configuration settings"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), nullable=False, unique=True, index=True)
    config_value = Column(JSONB, nullable=False)
    is_editable = Column(Boolean, nullable=False, default=False)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    updated_by_user = relationship("User", foreign_keys=[updated_by])


class PlatformMetrics(Base):
    """Cached platform-wide metrics for dashboard"""
    __tablename__ = "platform_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_key = Column(String(100), nullable=False, unique=True, index=True)
    metric_value = Column(JSONB, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
