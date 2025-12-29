"""
User management schemas for RBAC
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.hotel import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    country_code: str = Field(default="+1", max_length=5)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    
    @validator('mobile_number')
    def validate_mobile(cls, v):
        if not v.replace('+', '').isdigit():
            raise ValueError('Mobile number must contain only digits')
        return v


class UserCreate(UserBase):
    """Schema for creating a new user (admin/vendor creates employee)"""
    role: UserRole
    hotel_id: Optional[int] = None
    password: Optional[str] = Field(None, min_length=8)  # For future email/password login
    
    @validator('hotel_id')
    def validate_hotel_for_employee(cls, v, values):
        role = values.get('role')
        if role in [UserRole.HOTEL_EMPLOYEE, UserRole.VENDOR_ADMIN] and v is None:
            raise ValueError(f'{role.value} must have a hotel_id')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user details"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    hotel_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    mobile_number: str
    country_code: str
    email: Optional[str]
    full_name: Optional[str]
    role: UserRole
    hotel_id: Optional[int]
    is_active: bool
    email_verified: bool
    last_login: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list"""
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


class PermissionAssignment(BaseModel):
    """Schema for assigning/revoking individual permissions to hotel employees"""
    user_id: int
    permission: str  # Permission enum value
    
    @validator('permission')
    def validate_permission(cls, v):
        # Import here to avoid circular dependency
        from app.core.permissions import Permission, GRANTABLE_EMPLOYEE_PERMISSIONS
        
        try:
            perm = Permission(v)
        except ValueError:
            raise ValueError(f'Invalid permission: {v}')
        
        if perm not in GRANTABLE_EMPLOYEE_PERMISSIONS:
            raise ValueError(f'Permission {v} cannot be individually granted')
        
        return v


class PermissionResponse(BaseModel):
    """Schema for permission grant response"""
    id: int
    user_id: int
    permission: str
    granted_by: Optional[int]
    granted_at: datetime
    revoked_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserPermissionsResponse(BaseModel):
    """Schema for user's full permission set"""
    user_id: int
    role: UserRole
    role_permissions: List[str]  # Permissions from role
    granted_permissions: List[PermissionResponse]  # Individually granted permissions
    all_permissions: List[str]  # Combined unique permissions


class AuditLogResponse(BaseModel):
    """Schema for audit log entry"""
    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list"""
    logs: List[AuditLogResponse]
    total: int
    skip: int
    limit: int


class PasswordUpdate(BaseModel):
    """Schema for password update (future feature)"""
    current_password: Optional[str] = None
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
