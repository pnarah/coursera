"""Employee and vendor management models."""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, ENUM as PG_ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from datetime import datetime
import enum


class EmployeeRole(str, enum.Enum):
    """Employee role types"""
    MANAGER = "MANAGER"
    RECEPTIONIST = "RECEPTIONIST"
    HOUSEKEEPING = "HOUSEKEEPING"
    MAINTENANCE = "MAINTENANCE"


class ApprovalStatus(str, enum.Enum):
    """Vendor approval status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VendorApprovalRequest(Base):
    """Vendor approval request model"""
    __tablename__ = "vendor_approval_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    business_name = Column(String(255), nullable=False)
    business_address = Column(Text)
    tax_id = Column(String(50))
    contact_email = Column(String(255))
    contact_phone = Column(String(15))
    status = Column(PG_ENUM(ApprovalStatus, name='approval_status', create_type=False), default=ApprovalStatus.PENDING, nullable=False, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="vendor_requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class EmployeeInvitation(Base):
    """Employee invitation model"""
    __tablename__ = "employee_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    mobile_number = Column(String(15), nullable=False)
    role = Column(PG_ENUM(EmployeeRole, name='employee_role', create_type=False), nullable=False)
    permissions = Column(JSONB)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    hotel = relationship("Hotel")
    inviter = relationship("User")


class HotelEmployee(Base):
    """Hotel employee assignment model"""
    __tablename__ = "hotel_employees"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(PG_ENUM(EmployeeRole, name='employee_role', create_type=False), nullable=False)
    permissions = Column(JSONB)
    is_active = Column(Boolean, default=True, index=True)
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    invited_at = Column(DateTime(timezone=True))
    joined_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="employee_assignments")
    hotel = relationship("Hotel", back_populates="employees")
    inviter = relationship("User", foreign_keys=[invited_by])
