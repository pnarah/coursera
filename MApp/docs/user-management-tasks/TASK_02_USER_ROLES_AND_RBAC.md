# Task 02: User Roles & Basic RBAC

**Priority:** Critical  
**Estimated Duration:** 3-4 days  
**Dependencies:** TASK_01_CORE_AUTHENTICATION  
**Status:** Not Started

---

## Overview

Implement role-based access control (RBAC) system with four user types: Guest, Hotel Employee, Vendor Admin, and System Admin. Each role has specific permissions and access levels.

---

## Objectives

1. Define user roles and permissions
2. Implement authentication middleware
3. Add role-based decorators for API endpoints
4. Create permission checking system
5. Add user profile management
6. Implement role upgrade/assignment functionality

---

## Backend Tasks

### 1. Database Schema Updates

Create migration `002_add_role_permissions.py`:

```sql
-- Create enum for user roles
CREATE TYPE user_role AS ENUM ('GUEST', 'HOTEL_EMPLOYEE', 'VENDOR_ADMIN', 'SYSTEM_ADMIN');

-- Update users table to use enum
ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::user_role;

-- Add additional user fields
ALTER TABLE users ADD COLUMN created_by INTEGER REFERENCES users(id);
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);  -- For admin users
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false;

-- Create hotel employee permissions table
CREATE TABLE hotel_employee_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, permission)
);

CREATE INDEX idx_permissions_user ON hotel_employee_permissions(user_id);

-- Create audit log table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

### 2. Models

Update `app/models/user.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class UserRole(str, enum.Enum):
    GUEST = "GUEST"
    HOTEL_EMPLOYEE = "HOTEL_EMPLOYEE"
    VENDOR_ADMIN = "VENDOR_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String(15), unique=True, nullable=False, index=True)
    country_code = Column(String(5), default="+1")
    full_name = Column(String(255))
    email = Column(String(255), unique=True, nullable=True)
    email_verified = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.GUEST, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    permissions = relationship("HotelEmployeePermission", back_populates="user", cascade="all, delete-orphan")
    hotel = relationship("Hotel", foreign_keys=[hotel_id])

class HotelEmployeePermission(Base):
    __tablename__ = "hotel_employee_permissions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(String(100), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"))
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", foreign_keys=[user_id], back_populates="permissions")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 3. Permissions Constants

Create `app/core/permissions.py`:

```python
from enum import Enum

class Permission(str, Enum):
    # Booking permissions
    VIEW_BOOKINGS = "view_bookings"
    CREATE_BOOKING = "create_booking"
    MODIFY_BOOKING = "modify_booking"
    CANCEL_BOOKING = "cancel_booking"
    
    # Room permissions
    VIEW_ROOMS = "view_rooms"
    MANAGE_ROOM_STATUS = "manage_room_status"
    
    # Guest permissions
    VIEW_GUESTS = "view_guests"
    MANAGE_GUESTS = "manage_guests"
    
    # Service permissions
    VIEW_SERVICES = "view_services"
    PROCESS_SERVICES = "process_services"
    
    # Payment permissions
    PROCESS_PAYMENTS = "process_payments"
    VIEW_INVOICES = "view_invoices"
    
    # Analytics permissions
    VIEW_ANALYTICS = "view_analytics"
    
    # Staff permissions
    MANAGE_STAFF = "manage_staff"
    
    # Hotel permissions
    MANAGE_HOTEL = "manage_hotel"

# Default permissions by role
ROLE_PERMISSIONS = {
    "GUEST": [],
    "HOTEL_EMPLOYEE": [
        Permission.VIEW_BOOKINGS,
        Permission.CREATE_BOOKING,
        Permission.VIEW_ROOMS,
        Permission.MANAGE_ROOM_STATUS,
        Permission.VIEW_GUESTS,
        Permission.VIEW_SERVICES,
        Permission.PROCESS_SERVICES,
        Permission.VIEW_INVOICES,
    ],
    "VENDOR_ADMIN": [
        Permission.VIEW_BOOKINGS,
        Permission.CREATE_BOOKING,
        Permission.MODIFY_BOOKING,
        Permission.CANCEL_BOOKING,
        Permission.VIEW_ROOMS,
        Permission.MANAGE_ROOM_STATUS,
        Permission.VIEW_GUESTS,
        Permission.MANAGE_GUESTS,
        Permission.VIEW_SERVICES,
        Permission.PROCESS_SERVICES,
        Permission.PROCESS_PAYMENTS,
        Permission.VIEW_INVOICES,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_STAFF,
        Permission.MANAGE_HOTEL,
    ],
    "SYSTEM_ADMIN": ["*"],  # All permissions
}
```

### 4. Authentication Dependencies

Create `app/core/dependencies.py`:

```python
from typing import Optional
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import decode_token
from app.core.permissions import Permission, ROLE_PERMISSIONS

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        payload = decode_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is disabled")
        
        return user
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return current_user

def require_role(*allowed_roles: UserRole):
    """Dependency to check if user has required role"""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {allowed_roles}"
            )
        return current_user
    return role_checker

def require_permission(*required_permissions: Permission):
    """Dependency to check if user has required permission"""
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # System admin has all permissions
        if current_user.role == UserRole.SYSTEM_ADMIN:
            return current_user
        
        # Check role-based permissions
        role_perms = ROLE_PERMISSIONS.get(current_user.role.value, [])
        
        if "*" in role_perms:  # Has all permissions
            return current_user
        
        # For hotel employees, check custom permissions
        if current_user.role == UserRole.HOTEL_EMPLOYEE:
            stmt = select(HotelEmployeePermission).where(
                HotelEmployeePermission.user_id == current_user.id
            )
            result = await db.execute(stmt)
            custom_perms = {p.permission for p in result.scalars().all()}
            role_perms.extend(custom_perms)
        
        # Check if user has required permissions
        has_permission = any(perm in role_perms for perm in required_permissions)
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {required_permissions}"
            )
        
        return current_user
    
    return permission_checker

async def require_hotel_access(
    hotel_id: int,
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user has access to specific hotel"""
    # System admin can access any hotel
    if current_user.role == UserRole.SYSTEM_ADMIN:
        return current_user
    
    # Hotel-specific users can only access their hotel
    if current_user.role in [UserRole.VENDOR_ADMIN, UserRole.HOTEL_EMPLOYEE]:
        if current_user.hotel_id != hotel_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this hotel"
            )
        return current_user
    
    # Guests cannot access hotel admin features
    raise HTTPException(
        status_code=403,
        detail="Insufficient permissions"
    )
```

### 5. User Service Updates

Update `app/services/auth_service.py`:

```python
class AuthService:
    # ... existing methods ...
    
    async def update_user_profile(
        self,
        user_id: int,
        full_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> User:
        """Update user profile information"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if full_name:
            user.full_name = full_name
        if email:
            # Check if email already exists
            email_check = select(User).where(
                User.email == email,
                User.id != user_id
            )
            existing = await self.db.execute(email_check)
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already in use")
            user.email = email
            user.email_verified = False
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def upgrade_user_role(
        self,
        user_id: int,
        new_role: UserRole,
        hotel_id: Optional[int],
        upgraded_by: User
    ) -> User:
        """Upgrade user role (admin only)"""
        if upgraded_by.role != UserRole.SYSTEM_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only system admins can upgrade user roles"
            )
        
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.role = new_role
        user.hotel_id = hotel_id if new_role in [UserRole.VENDOR_ADMIN, UserRole.HOTEL_EMPLOYEE] else None
        user.created_by = upgraded_by.id
        
        await self.db.commit()
        
        # Log audit
        await self.log_audit(
            user_id=upgraded_by.id,
            action="UPGRADE_USER_ROLE",
            resource_type="user",
            resource_id=user.id,
            details={"old_role": user.role.value, "new_role": new_role.value}
        )
        
        return user
    
    async def log_audit(self, user_id: int, action: str, **kwargs):
        """Log audit event"""
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            **kwargs
        )
        self.db.add(log_entry)
        await self.db.commit()
```

### 6. API Endpoints

Create `app/api/v1/users.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserUpdate, UserResponse
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_profile(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    auth_service = AuthService(db)
    updated_user = await auth_service.update_user_profile(
        user_id=current_user.id,
        full_name=update.full_name,
        email=update.email
    )
    return updated_user

@router.post("/{user_id}/upgrade-role")
async def upgrade_user_role(
    user_id: int,
    new_role: UserRole,
    hotel_id: Optional[int] = None,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Upgrade user role (System Admin only)"""
    auth_service = AuthService(db)
    updated_user = await auth_service.upgrade_user_role(
        user_id=user_id,
        new_role=new_role,
        hotel_id=hotel_id,
        upgraded_by=current_user
    )
    return {"success": True, "user": updated_user}
```

---

## Frontend Tasks

### 1. Auth State Management

Create `mobile/lib/core/providers/auth_provider.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mapp_mobile/core/models/user.dart';
import 'package:mapp_mobile/core/services/api_service.dart';
import 'package:mapp_mobile/core/services/secure_storage_service.dart';

class AuthState {
  final User? user;
  final bool isAuthenticated;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.user,
    this.isAuthenticated = false,
    this.isLoading = false,
    this.error,
  });

  AuthState copyWith({
    User? user,
    bool? isAuthenticated,
    bool? isLoading,
    String? error,
  }) {
    return AuthState(
      user: user ?? this.user,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiService _apiService;
  final SecureStorageService _storage;

  AuthNotifier(this._apiService, this._storage) : super(const AuthState()) {
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    state = state.copyWith(isLoading: true);
    
    try {
      final token = await _storage.getAccessToken();
      final userData = await _storage.getUser();
      
      if (token != null && userData != null) {
        final user = User.fromJson(userData);
        state = AuthState(
          user: user,
          isAuthenticated: true,
          isLoading: false,
        );
      } else {
        state = const AuthState(isLoading: false);
      }
    } catch (e) {
      state = AuthState(isLoading: false, error: e.toString());
    }
  }

  Future<void> login(String mobile, String otp) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final result = await _apiService.verifyOTP(mobile, otp);
      final user = User.fromJson(result['user']);
      
      await _storage.saveTokens(
        result['access_token'],
        result['refresh_token'],
      );
      await _storage.saveUser(result['user']);
      
      state = AuthState(
        user: user,
        isAuthenticated: true,
        isLoading: false,
      );
    } catch (e) {
      state = AuthState(isLoading: false, error: e.toString());
    }
  }

  Future<void> logout() async {
    await _storage.clearAll();
    state = const AuthState();
  }

  bool hasRole(UserRole role) {
    return state.user?.role == role || state.user?.role == UserRole.SYSTEM_ADMIN;
  }

  bool canAccessHotel(int hotelId) {
    if (state.user?.role == UserRole.SYSTEM_ADMIN) return true;
    if (state.user?.role == UserRole.VENDOR_ADMIN || 
        state.user?.role == UserRole.HOTEL_EMPLOYEE) {
      return state.user?.hotelId == hotelId;
    }
    return false;
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ApiService(), SecureStorageService());
});
```

### 2. Role-Based Widgets

Create `mobile/lib/core/widgets/role_based_widget.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mapp_mobile/core/models/user.dart';
import 'package:mapp_mobile/core/providers/auth_provider.dart';

class RoleBasedWidget extends ConsumerWidget {
  final UserRole requiredRole;
  final Widget child;
  final Widget? fallback;

  const RoleBasedWidget({
    Key? key,
    required this.requiredRole,
    required this.child,
    this.fallback,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final hasAccess = authState.user?.role == requiredRole ||
        authState.user?.role == UserRole.SYSTEM_ADMIN;

    if (hasAccess) {
      return child;
    }

    return fallback ?? const SizedBox.shrink();
  }
}
```

---

## Testing

### Backend Tests

```python
@pytest.mark.asyncio
async def test_role_based_access(client: AsyncClient, auth_headers):
    # Try to access admin endpoint as guest
    response = await client.get(
        "/api/v1/admin/users",
        headers=auth_headers['guest']
    )
    assert response.status_code == 403
    
    # Access same endpoint as system admin
    response = await client.get(
        "/api/v1/admin/users",
        headers=auth_headers['system_admin']
    )
    assert response.status_code == 200
```

---

## Acceptance Criteria

- ✅ Four user roles implemented (Guest, Hotel Employee, Vendor Admin, System Admin)
- ✅ Role-based middleware protects API endpoints
- ✅ Permission system allows granular access control
- ✅ Hotel employees have customizable permissions
- ✅ Multi-tenant isolation works (users can't access other hotels)
- ✅ System admin can upgrade user roles
- ✅ Audit log tracks sensitive operations
- ✅ Frontend state management reflects user role
- ✅ Role-based UI components work
- ✅ Profile update functionality works

---

## Next Task

**TASK_03_SESSION_MANAGEMENT.md** - Implement comprehensive session management with Redis
