"""Vendor and employee management service."""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.employee import (
    VendorApprovalRequest, EmployeeInvitation, HotelEmployee, ApprovalStatus
)
from app.models.hotel import User, UserRole, Hotel
import secrets
import logging

logger = logging.getLogger(__name__)


class VendorService:
    """Service for vendor and employee management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_vendor_request(
        self,
        user_id: int,
        business_name: str,
        business_address: Optional[str],
        tax_id: Optional[str],
        contact_email: str,
        contact_phone: str
    ) -> VendorApprovalRequest:
        """Create vendor approval request"""
        # Check if user already has pending request
        stmt = select(VendorApprovalRequest).where(
            and_(
                VendorApprovalRequest.user_id == user_id,
                VendorApprovalRequest.status == ApprovalStatus.PENDING
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError("User already has a pending vendor request")
        
        request = VendorApprovalRequest(
            user_id=user_id,
            business_name=business_name,
            business_address=business_address,
            tax_id=tax_id,
            contact_email=contact_email,
            contact_phone=contact_phone
        )
        
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        
        logger.info(f"Vendor request created for user {user_id}")
        return request
    
    async def approve_vendor_request(
        self,
        request_id: int,
        admin_user_id: int
    ) -> VendorApprovalRequest:
        """Approve vendor request and upgrade user role"""
        stmt = select(VendorApprovalRequest).where(VendorApprovalRequest.id == request_id)
        result = await self.db.execute(stmt)
        request = result.scalar_one_or_none()
        
        if not request:
            raise ValueError("Request not found")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError("Request already processed")
        
        # Update request status
        request.status = ApprovalStatus.APPROVED
        request.reviewed_by = admin_user_id
        request.reviewed_at = datetime.utcnow()
        
        # Upgrade user role to VENDOR_ADMIN
        user_stmt = select(User).where(User.id == request.user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if user:
            user.role = UserRole.VENDOR_ADMIN
            user.vendor_approved = True
            user.approval_date = datetime.utcnow()
            user.approved_by = admin_user_id
        
        await self.db.commit()
        await self.db.refresh(request)
        
        logger.info(f"Vendor request {request_id} approved by admin {admin_user_id}")
        return request
    
    async def reject_vendor_request(
        self,
        request_id: int,
        admin_user_id: int,
        rejection_reason: str
    ) -> VendorApprovalRequest:
        """Reject vendor request"""
        stmt = select(VendorApprovalRequest).where(VendorApprovalRequest.id == request_id)
        result = await self.db.execute(stmt)
        request = result.scalar_one_or_none()
        
        if not request:
            raise ValueError("Request not found")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError("Request already processed")
        
        request.status = ApprovalStatus.REJECTED
        request.reviewed_by = admin_user_id
        request.reviewed_at = datetime.utcnow()
        request.rejection_reason = rejection_reason
        
        await self.db.commit()
        await self.db.refresh(request)
        
        logger.info(f"Vendor request {request_id} rejected by admin {admin_user_id}")
        return request
    
    async def get_pending_requests(self) -> List[VendorApprovalRequest]:
        """Get all pending vendor requests"""
        stmt = select(VendorApprovalRequest).where(
            VendorApprovalRequest.status == ApprovalStatus.PENDING
        ).order_by(VendorApprovalRequest.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_user_requests(self, user_id: int) -> List[VendorApprovalRequest]:
        """Get vendor requests for a specific user"""
        stmt = select(VendorApprovalRequest).where(
            VendorApprovalRequest.user_id == user_id
        ).order_by(VendorApprovalRequest.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def invite_employee(
        self,
        hotel_id: int,
        mobile_number: str,
        role: str,
        invited_by: int,
        permissions: Optional[dict] = None
    ) -> EmployeeInvitation:
        """Create employee invitation"""
        # Verify hotel exists
        hotel_stmt = select(Hotel).where(Hotel.id == hotel_id)
        hotel_result = await self.db.execute(hotel_stmt)
        hotel = hotel_result.scalar_one_or_none()
        
        if not hotel:
            raise ValueError("Hotel not found")
        
        # Check if user already invited and invitation is active
        existing_stmt = select(EmployeeInvitation).where(
            and_(
                EmployeeInvitation.hotel_id == hotel_id,
                EmployeeInvitation.mobile_number == mobile_number,
                EmployeeInvitation.accepted_at.is_(None),
                EmployeeInvitation.expires_at > datetime.utcnow()
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise ValueError("Active invitation already exists for this user")
        
        # Generate invitation token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        invitation = EmployeeInvitation(
            hotel_id=hotel_id,
            mobile_number=mobile_number,
            role=role,
            permissions=permissions,
            invited_by=invited_by,
            token=token,
            expires_at=expires_at
        )
        
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        
        # TODO: Send invitation SMS/Email via notification service
        logger.info(f"Employee invitation created for {mobile_number} at hotel {hotel_id}")
        
        return invitation
    
    async def accept_invitation(
        self,
        token: str,
        user_id: int
    ) -> HotelEmployee:
        """Accept employee invitation"""
        stmt = select(EmployeeInvitation).where(EmployeeInvitation.token == token)
        result = await self.db.execute(stmt)
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if invitation.accepted_at:
            raise ValueError("Invitation already accepted")
        
        if invitation.expires_at < datetime.utcnow():
            raise ValueError("Invitation expired")
        
        # Get user and verify mobile number
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user or user.mobile_number != invitation.mobile_number:
            raise ValueError("User mobile number does not match invitation")
        
        # Check if already assigned to this hotel
        existing_employee_stmt = select(HotelEmployee).where(
            and_(
                HotelEmployee.user_id == user_id,
                HotelEmployee.hotel_id == invitation.hotel_id
            )
        )
        existing_employee_result = await self.db.execute(existing_employee_stmt)
        if existing_employee_result.scalar_one_or_none():
            raise ValueError("User already assigned to this hotel")
        
        # Create employee assignment
        employee = HotelEmployee(
            user_id=user_id,
            hotel_id=invitation.hotel_id,
            role=invitation.role,
            permissions=invitation.permissions,
            invited_by=invitation.invited_by,
            invited_at=invitation.created_at,
            joined_at=datetime.utcnow()
        )
        
        # Update user role if needed
        if user.role == UserRole.GUEST:
            user.role = UserRole.HOTEL_EMPLOYEE
        
        # Update user's hotel_id to first assigned hotel
        if not user.hotel_id:
            user.hotel_id = invitation.hotel_id
        
        # Mark invitation as accepted
        invitation.accepted_at = datetime.utcnow()
        
        self.db.add(employee)
        await self.db.commit()
        await self.db.refresh(employee)
        
        logger.info(f"User {user_id} accepted invitation and joined hotel {invitation.hotel_id}")
        return employee
    
    async def get_hotel_employees(self, hotel_id: int) -> List[HotelEmployee]:
        """Get all employees for a hotel"""
        stmt = select(HotelEmployee).where(HotelEmployee.hotel_id == hotel_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_employee(self, employee_id: int) -> Optional[HotelEmployee]:
        """Get employee by ID"""
        stmt = select(HotelEmployee).where(HotelEmployee.id == employee_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_employee(
        self,
        employee_id: int,
        role: Optional[str] = None,
        permissions: Optional[dict] = None,
        is_active: Optional[bool] = None
    ) -> HotelEmployee:
        """Update employee details"""
        stmt = select(HotelEmployee).where(HotelEmployee.id == employee_id)
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise ValueError("Employee not found")
        
        if role:
            employee.role = role
        if permissions is not None:
            employee.permissions = permissions
        if is_active is not None:
            employee.is_active = is_active
        
        employee.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(employee)
        
        logger.info(f"Employee {employee_id} updated")
        return employee
    
    async def remove_employee(self, employee_id: int) -> None:
        """Remove employee from hotel"""
        stmt = select(HotelEmployee).where(HotelEmployee.id == employee_id)
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise ValueError("Employee not found")
        
        await self.db.delete(employee)
        await self.db.commit()
        
        logger.info(f"Employee {employee_id} removed")
    
    async def get_pending_invitations(self, hotel_id: int) -> List[EmployeeInvitation]:
        """Get pending invitations for a hotel"""
        stmt = select(EmployeeInvitation).where(
            and_(
                EmployeeInvitation.hotel_id == hotel_id,
                EmployeeInvitation.accepted_at.is_(None),
                EmployeeInvitation.expires_at > datetime.utcnow()
            )
        ).order_by(EmployeeInvitation.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
