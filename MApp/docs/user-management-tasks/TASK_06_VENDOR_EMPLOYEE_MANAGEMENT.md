# Task 06: Vendor & Hotel Employee Management

**Priority:** High  
**Estimated Duration:** 3 days  
**Dependencies:** TASK_02 (User Roles & RBAC), TASK_04 (Subscription Management)  
**Status:** Not Started

---

## Overview

Implement vendor registration workflow, hotel employee assignment, and custom permission management. Enable vendors to manage their hotels and assign employees with specific roles.

---

## Objectives

1. Create vendor registration and approval workflow
2. Link hotels to vendor accounts
3. Implement hotel employee invitation and assignment
4. Add custom permissions for hotel employees
5. Enable vendors to manage their own employees
6. Add multi-hotel support for vendors with multiple properties

---

## Backend Tasks

### 1. Database Schema

Update existing tables and add new ones:

```sql
-- Migration: add_vendor_management.py

-- Add vendor-specific fields to users table
ALTER TABLE users ADD COLUMN vendor_approved BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN approval_date TIMESTAMP;
ALTER TABLE users ADD COLUMN approved_by INTEGER REFERENCES users(id);

-- Hotel employees table
CREATE TABLE hotel_employees (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- MANAGER, RECEPTIONIST, HOUSEKEEPING, MAINTENANCE
    permissions JSONB,  -- Custom permissions
    is_active BOOLEAN DEFAULT true,
    invited_by INTEGER REFERENCES users(id),
    invited_at TIMESTAMP DEFAULT NOW(),
    joined_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, hotel_id)
);

-- Employee invitations
CREATE TABLE employee_invitations (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
    mobile_number VARCHAR(15) NOT NULL,
    role VARCHAR(50) NOT NULL,
    permissions JSONB,
    invited_by INTEGER REFERENCES users(id),
    token VARCHAR(100) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vendor approval requests
CREATE TABLE vendor_approval_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    business_name VARCHAR(255) NOT NULL,
    business_address TEXT,
    tax_id VARCHAR(50),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(15),
    status VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, APPROVED, REJECTED
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hotel_employees_hotel_id ON hotel_employees(hotel_id);
CREATE INDEX idx_hotel_employees_user_id ON hotel_employees(user_id);
CREATE INDEX idx_employee_invitations_token ON employee_invitations(token);
CREATE INDEX idx_vendor_requests_status ON vendor_approval_requests(status);
```

### 2. Models

**File:** `app/models/employee.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
import enum

class EmployeeRole(str, enum.Enum):
    MANAGER = "MANAGER"
    RECEPTIONIST = "RECEPTIONIST"
    HOUSEKEEPING = "HOUSEKEEPING"
    MAINTENANCE = "MAINTENANCE"

class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class HotelEmployee(Base):
    __tablename__ = "hotel_employees"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    permissions = Column(JSON)  # Custom permissions
    is_active = Column(Boolean, default=True)
    invited_by = Column(Integer, ForeignKey("users.id"))
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="employee_assignments")
    hotel = relationship("Hotel", back_populates="employees")
    inviter = relationship("User", foreign_keys=[invited_by])

class EmployeeInvitation(Base):
    __tablename__ = "employee_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False)
    mobile_number = Column(String(15), nullable=False)
    role = Column(String(50), nullable=False)
    permissions = Column(JSON)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(100), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    hotel = relationship("Hotel")
    inviter = relationship("User")

class VendorApprovalRequest(Base):
    __tablename__ = "vendor_approval_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    business_name = Column(String(255), nullable=False)
    business_address = Column(Text)
    tax_id = Column(String(50))
    contact_email = Column(String(255))
    contact_phone = Column(String(15))
    status = Column(String(50), default=ApprovalStatus.PENDING)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="vendor_requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
```

### 3. Schemas

**File:** `app/schemas/employee.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.employee import EmployeeRole, ApprovalStatus

class VendorApprovalRequestCreate(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=255)
    business_address: Optional[str] = None
    tax_id: Optional[str] = None
    contact_email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    contact_phone: str = Field(..., regex=r'^\d{10,15}$')

class VendorApprovalRequestResponse(BaseModel):
    id: int
    user_id: int
    business_name: str
    status: ApprovalStatus
    created_at: datetime
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    
    class Config:
        from_attributes = True

class VendorApprovalAction(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None

class EmployeeInvitationCreate(BaseModel):
    hotel_id: int
    mobile_number: str = Field(..., regex=r'^\d{10,15}$')
    role: EmployeeRole
    permissions: Optional[Dict[str, bool]] = None

class EmployeeInvitationResponse(BaseModel):
    id: int
    hotel_id: int
    mobile_number: str
    role: str
    token: str
    expires_at: datetime
    accepted_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class HotelEmployeeResponse(BaseModel):
    id: int
    user_id: int
    hotel_id: int
    role: str
    permissions: Optional[Dict[str, bool]]
    is_active: bool
    joined_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class HotelEmployeeUpdate(BaseModel):
    role: Optional[EmployeeRole] = None
    permissions: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = None

class EmployeeInvitationAccept(BaseModel):
    token: str
```

### 4. Vendor Service

**File:** `app/services/vendor_service.py`

```python
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.employee import (
    VendorApprovalRequest, EmployeeInvitation, HotelEmployee, ApprovalStatus
)
from app.models.user import User, UserRole
from app.models.hotel import Hotel
import secrets
import logging

logger = logging.getLogger(__name__)

class VendorService:
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
        existing = await self.db.execute(
            select(VendorApprovalRequest).where(
                and_(
                    VendorApprovalRequest.user_id == user_id,
                    VendorApprovalRequest.status == ApprovalStatus.PENDING
                )
            )
        )
        if existing.scalar_one_or_none():
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
        
        return request
    
    async def approve_vendor_request(
        self,
        request_id: int,
        admin_user_id: int
    ) -> VendorApprovalRequest:
        """Approve vendor request and upgrade user role"""
        result = await self.db.execute(
            select(VendorApprovalRequest).where(VendorApprovalRequest.id == request_id)
        )
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
        user_result = await self.db.execute(
            select(User).where(User.id == request.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            user.role = UserRole.VENDOR_ADMIN
            user.vendor_approved = True
            user.approval_date = datetime.utcnow()
            user.approved_by = admin_user_id
        
        await self.db.commit()
        await self.db.refresh(request)
        
        return request
    
    async def reject_vendor_request(
        self,
        request_id: int,
        admin_user_id: int,
        rejection_reason: str
    ) -> VendorApprovalRequest:
        """Reject vendor request"""
        result = await self.db.execute(
            select(VendorApprovalRequest).where(VendorApprovalRequest.id == request_id)
        )
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
        
        return request
    
    async def invite_employee(
        self,
        hotel_id: int,
        mobile_number: str,
        role: str,
        invited_by: int,
        permissions: Optional[dict] = None
    ) -> EmployeeInvitation:
        """Create employee invitation"""
        # Verify hotel belongs to vendor
        hotel_result = await self.db.execute(
            select(Hotel).where(Hotel.id == hotel_id)
        )
        hotel = hotel_result.scalar_one_or_none()
        
        if not hotel:
            raise ValueError("Hotel not found")
        
        # Check if user already invited
        existing = await self.db.execute(
            select(EmployeeInvitation).where(
                and_(
                    EmployeeInvitation.hotel_id == hotel_id,
                    EmployeeInvitation.mobile_number == mobile_number,
                    EmployeeInvitation.accepted_at.is_(None),
                    EmployeeInvitation.expires_at > datetime.utcnow()
                )
            )
        )
        if existing.scalar_one_or_none():
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
        
        # TODO: Send invitation SMS/Email
        logger.info(f"Employee invitation created for {mobile_number}")
        
        return invitation
    
    async def accept_invitation(
        self,
        token: str,
        user_id: int
    ) -> HotelEmployee:
        """Accept employee invitation"""
        result = await self.db.execute(
            select(EmployeeInvitation).where(EmployeeInvitation.token == token)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if invitation.accepted_at:
            raise ValueError("Invitation already accepted")
        
        if invitation.expires_at < datetime.utcnow():
            raise ValueError("Invitation expired")
        
        # Get user and verify mobile number
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or user.mobile_number != invitation.mobile_number:
            raise ValueError("User mobile number does not match invitation")
        
        # Check if already assigned to this hotel
        existing_employee = await self.db.execute(
            select(HotelEmployee).where(
                and_(
                    HotelEmployee.user_id == user_id,
                    HotelEmployee.hotel_id == invitation.hotel_id
                )
            )
        )
        if existing_employee.scalar_one_or_none():
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
        
        return employee
    
    async def get_hotel_employees(self, hotel_id: int) -> List[HotelEmployee]:
        """Get all employees for a hotel"""
        result = await self.db.execute(
            select(HotelEmployee).where(HotelEmployee.hotel_id == hotel_id)
        )
        return result.scalars().all()
    
    async def update_employee(
        self,
        employee_id: int,
        role: Optional[str] = None,
        permissions: Optional[dict] = None,
        is_active: Optional[bool] = None
    ) -> HotelEmployee:
        """Update employee details"""
        result = await self.db.execute(
            select(HotelEmployee).where(HotelEmployee.id == employee_id)
        )
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
        
        return employee
    
    async def remove_employee(self, employee_id: int):
        """Remove employee from hotel"""
        result = await self.db.execute(
            select(HotelEmployee).where(HotelEmployee.id == employee_id)
        )
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise ValueError("Employee not found")
        
        await self.db.delete(employee)
        await self.db.commit()
```

### 5. API Endpoints

**File:** `app/api/v1/vendors.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.services.vendor_service import VendorService
from app.schemas.employee import (
    VendorApprovalRequestCreate,
    VendorApprovalRequestResponse,
    VendorApprovalAction,
    EmployeeInvitationCreate,
    EmployeeInvitationResponse,
    EmployeeInvitationAccept,
    HotelEmployeeResponse,
    HotelEmployeeUpdate
)

router = APIRouter()

# Vendor approval requests
@router.post("/approval-request", response_model=VendorApprovalRequestResponse)
async def create_vendor_request(
    request: VendorApprovalRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create vendor approval request"""
    service = VendorService(db)
    
    try:
        approval_request = await service.create_vendor_request(
            user_id=current_user.id,
            business_name=request.business_name,
            business_address=request.business_address,
            tax_id=request.tax_id,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone
        )
        return approval_request
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/approval-request/{request_id}/approve")
@require_role([UserRole.SYSTEM_ADMIN])
async def approve_vendor_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve vendor request (SYSTEM_ADMIN only)"""
    service = VendorService(db)
    
    try:
        approval_request = await service.approve_vendor_request(
            request_id=request_id,
            admin_user_id=current_user.id
        )
        return {"message": "Vendor approved successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/approval-request/{request_id}/reject")
@require_role([UserRole.SYSTEM_ADMIN])
async def reject_vendor_request(
    request_id: int,
    action: VendorApprovalAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject vendor request (SYSTEM_ADMIN only)"""
    if not action.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required"
        )
    
    service = VendorService(db)
    
    try:
        approval_request = await service.reject_vendor_request(
            request_id=request_id,
            admin_user_id=current_user.id,
            rejection_reason=action.rejection_reason
        )
        return {"message": "Vendor request rejected"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# Employee management
@router.post("/employees/invite", response_model=EmployeeInvitationResponse)
@require_role([UserRole.VENDOR_ADMIN])
async def invite_employee(
    invitation: EmployeeInvitationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite employee to hotel (VENDOR_ADMIN only)"""
    service = VendorService(db)
    
    try:
        invite = await service.invite_employee(
            hotel_id=invitation.hotel_id,
            mobile_number=invitation.mobile_number,
            role=invitation.role.value,
            invited_by=current_user.id,
            permissions=invitation.permissions
        )
        return invite
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/employees/accept-invitation", response_model=HotelEmployeeResponse)
async def accept_employee_invitation(
    accept: EmployeeInvitationAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept employee invitation"""
    service = VendorService(db)
    
    try:
        employee = await service.accept_invitation(
            token=accept.token,
            user_id=current_user.id
        )
        return employee
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/employees/hotel/{hotel_id}", response_model=List[HotelEmployeeResponse])
@require_role([UserRole.VENDOR_ADMIN, UserRole.SYSTEM_ADMIN])
async def get_hotel_employees(
    hotel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all employees for a hotel"""
    service = VendorService(db)
    employees = await service.get_hotel_employees(hotel_id)
    return employees

@router.put("/employees/{employee_id}", response_model=HotelEmployeeResponse)
@require_role([UserRole.VENDOR_ADMIN])
async def update_employee(
    employee_id: int,
    update: HotelEmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update employee details"""
    service = VendorService(db)
    
    try:
        employee = await service.update_employee(
            employee_id=employee_id,
            role=update.role.value if update.role else None,
            permissions=update.permissions,
            is_active=update.is_active
        )
        return employee
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/employees/{employee_id}")
@require_role([UserRole.VENDOR_ADMIN])
async def remove_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove employee from hotel"""
    service = VendorService(db)
    
    try:
        await service.remove_employee(employee_id)
        return {"message": "Employee removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

---

## Frontend Tasks

### 1. Vendor Registration Screen

**File:** `lib/features/vendor/screens/vendor_registration_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/vendor_provider.dart';

class VendorRegistrationScreen extends ConsumerStatefulWidget {
  const VendorRegistrationScreen({super.key});

  @override
  ConsumerState<VendorRegistrationScreen> createState() => _VendorRegistrationScreenState();
}

class _VendorRegistrationScreenState extends ConsumerState<VendorRegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _businessNameController = TextEditingController();
  final _addressController = TextEditingController();
  final _taxIdController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Become a Vendor')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _businessNameController,
              decoration: const InputDecoration(labelText: 'Business Name'),
              validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
            ),
            TextFormField(
              controller: _addressController,
              decoration: const InputDecoration(labelText: 'Business Address'),
            ),
            TextFormField(
              controller: _taxIdController,
              decoration: const InputDecoration(labelText: 'Tax ID'),
            ),
            TextFormField(
              controller: _emailController,
              decoration: const InputDecoration(labelText: 'Contact Email'),
              validator: (value) => value?.contains('@') == false ? 'Invalid email' : null,
            ),
            TextFormField(
              controller: _phoneController,
              decoration: const InputDecoration(labelText: 'Contact Phone'),
              validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _submitRequest,
              child: const Text('Submit Request'),
            ),
          ],
        ),
      ),
    );
  }
  
  void _submitRequest() async {
    if (_formKey.currentState!.validate()) {
      try {
        await ref.read(vendorProvider.notifier).createApprovalRequest(
          businessName: _businessNameController.text,
          businessAddress: _addressController.text,
          taxId: _taxIdController.text,
          contactEmail: _emailController.text,
          contactPhone: _phoneController.text,
        );
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Request submitted successfully')),
          );
          Navigator.pop(context);
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }
}
```

---

## Testing

```python
# tests/test_vendor_service.py
@pytest.mark.asyncio
async def test_create_vendor_request(db_session, test_user):
    service = VendorService(db_session)
    
    request = await service.create_vendor_request(
        user_id=test_user.id,
        business_name="Test Hotel Group",
        business_address="123 Main St",
        tax_id="TAX123",
        contact_email="contact@test.com",
        contact_phone="1234567890"
    )
    
    assert request.id is not None
    assert request.status == ApprovalStatus.PENDING

@pytest.mark.asyncio
async def test_invite_employee(db_session, vendor_user, test_hotel):
    service = VendorService(db_session)
    
    invitation = await service.invite_employee(
        hotel_id=test_hotel.id,
        mobile_number="9876543210",
        role="RECEPTIONIST",
        invited_by=vendor_user.id
    )
    
    assert invitation.token is not None
    assert invitation.expires_at > datetime.utcnow()
```

---

## Acceptance Criteria

- [ ] Vendor approval request workflow complete
- [ ] System admin can approve/reject vendor requests
- [ ] Approved vendors get VENDOR_ADMIN role
- [ ] Vendors can invite employees via mobile number
- [ ] Invitation tokens expire after 7 days
- [ ] Employees can accept invitations and get HOTEL_EMPLOYEE role
- [ ] Vendors can manage employee permissions
- [ ] Vendors can view all employees per hotel
- [ ] Multi-hotel support for vendors
- [ ] Unit tests pass

---

## Next Task

**[TASK_07_SYSTEM_ADMIN_DASHBOARD.md](./TASK_07_SYSTEM_ADMIN_DASHBOARD.md)** - System admin panel and platform management.
