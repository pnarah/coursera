"""
User management API endpoints with RBAC
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.models.hotel import User, UserRole, HotelEmployeePermission, AuditLog
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    PermissionAssignment, PermissionResponse, UserPermissionsResponse,
    AuditLogResponse, AuditLogListResponse
)
from app.api.deps import (
    get_current_active_user, require_role, require_permission,
    require_hotel_access, _get_user_permissions
)
from app.core.permissions import Permission, get_role_permissions


router = APIRouter(prefix="/users", tags=["User Management"])


# ==================
# Audit Log Helper
# ==================

async def create_audit_log(
    db: AsyncSession,
    user_id: Optional[int],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """Helper function to create audit log entries"""
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.add(audit_entry)
    await db.commit()


# ==================
# User CRUD Endpoints
# ==================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Update current user's own profile (limited fields)"""
    # Users can only update their email and full_name
    if user_update.email:
        current_user.email = user_update.email
        current_user.email_verified = False  # Requires re-verification
    
    if user_update.full_name:
        current_user.full_name = user_update.full_name
    
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    # Audit log
    await create_audit_log(
        db, current_user.id, "update_profile", "user",
        str(current_user.id), {"fields": ["email", "full_name"]},
        request.client.host if request else None
    )
    
    return current_user


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    hotel_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_permission(Permission.VIEW_ALL_USERS)),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (with filters).
    Requires VIEW_ALL_USERS permission.
    Vendor admins see only users from their hotel.
    """
    # Build query filters
    filters = []
    
    if role:
        filters.append(User.role == role)
    
    if is_active is not None:
        filters.append(User.is_active == is_active)
    
    # Hotel isolation for vendor admins and hotel employees
    if current_user.role in [UserRole.VENDOR_ADMIN, UserRole.HOTEL_EMPLOYEE]:
        if current_user.hotel_id:
            filters.append(User.hotel_id == current_user.hotel_id)
    elif hotel_id is not None:
        # System admins can filter by any hotel
        filters.append(User.hotel_id == hotel_id)
    
    # Count total
    count_query = select(func.count()).select_from(User)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Fetch users
    query = select(User).where(and_(*filters)).offset(skip).limit(limit).order_by(User.id)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        users=users,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission(Permission.VIEW_ALL_USERS)),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID.
    Vendor admins can only view users from their hotel.
    """
    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hotel isolation check
    if current_user.role in [UserRole.VENDOR_ADMIN, UserRole.HOTEL_EMPLOYEE]:
        if user.hotel_id != current_user.hotel_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view users from your hotel"
            )
    
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission(Permission.CREATE_USER)),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Create a new user (employee/admin).
    Vendor admins can only create users for their hotel.
    """
    # Check if mobile number already exists
    result = await db.execute(
        select(User).where(User.mobile_number == user_data.mobile_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="User with this mobile number already exists"
        )
    
    # Hotel isolation for vendor admins
    if current_user.role == UserRole.VENDOR_ADMIN:
        if user_data.hotel_id != current_user.hotel_id:
            raise HTTPException(
                status_code=403,
                detail="You can only create users for your hotel"
            )
    
    # Create user
    new_user = User(
        mobile_number=user_data.mobile_number,
        country_code=user_data.country_code,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        hotel_id=user_data.hotel_id,
        created_by=current_user.id,
        is_active=True
    )
    
    # TODO: Hash password if provided (future feature)
    # if user_data.password:
    #     new_user.password_hash = hash_password(user_data.password)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Audit log
    await create_audit_log(
        db, current_user.id, "create_user", "user",
        str(new_user.id),
        {"role": user_data.role.value, "hotel_id": user_data.hotel_id},
        request.client.host if request else None
    )
    
    return new_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_permission(Permission.UPDATE_USER)),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Update user details.
    Vendor admins can only update users from their hotel.
    """
    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hotel isolation
    if current_user.role == UserRole.VENDOR_ADMIN:
        if user.hotel_id != current_user.hotel_id:
            raise HTTPException(
                status_code=403,
                detail="You can only update users from your hotel"
            )
    
    # Update fields
    updated_fields = []
    if user_update.email is not None:
        user.email = user_update.email
        user.email_verified = False
        updated_fields.append("email")
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
        updated_fields.append("full_name")
    
    if user_update.role is not None:
        user.role = user_update.role
        updated_fields.append("role")
    
    if user_update.hotel_id is not None:
        user.hotel_id = user_update.hotel_id
        updated_fields.append("hotel_id")
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
        updated_fields.append("is_active")
    
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user)
    
    # Audit log
    await create_audit_log(
        db, current_user.id, "update_user", "user",
        str(user.id), {"fields": updated_fields},
        request.client.host if request else None
    )
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission(Permission.DELETE_USER)),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Delete user (soft delete - set is_active=False).
    Vendor admins can only delete users from their hotel.
    """
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hotel isolation
    if current_user.role == UserRole.VENDOR_ADMIN:
        if user.hotel_id != current_user.hotel_id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete users from your hotel"
            )
    
    # Soft delete
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Audit log
    await create_audit_log(
        db, current_user.id, "delete_user", "user",
        str(user.id), None,
        request.client.host if request else None
    )
    
    return None


# ==================
# Permission Management
# ==================

@router.get("/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(require_permission(Permission.VIEW_ALL_USERS)),
    db: AsyncSession = Depends(get_db)
):
    """Get all permissions for a user (role-based + granted)"""
    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hotel isolation
    if current_user.role in [UserRole.VENDOR_ADMIN, UserRole.HOTEL_EMPLOYEE]:
        if user.hotel_id != current_user.hotel_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get role permissions
    role_perms = get_role_permissions(user.role.value)
    role_perm_strings = [p.value for p in role_perms]
    
    # Get granted permissions
    result = await db.execute(
        select(HotelEmployeePermission).where(
            HotelEmployeePermission.user_id == user_id,
            HotelEmployeePermission.revoked_at.is_(None)
        )
    )
    granted_perms = result.scalars().all()
    
    # Combine all permissions
    all_perms = set(role_perm_strings)
    all_perms.update([p.permission for p in granted_perms])
    
    return UserPermissionsResponse(
        user_id=user.id,
        role=user.role,
        role_permissions=role_perm_strings,
        granted_permissions=granted_perms,
        all_permissions=sorted(list(all_perms))
    )


@router.post("/{user_id}/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def grant_permission(
    user_id: int,
    perm_data: PermissionAssignment,
    current_user: User = Depends(require_permission(Permission.ASSIGN_PERMISSIONS)),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Grant individual permission to a hotel employee"""
    # Verify user exists and is a hotel employee
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role != UserRole.HOTEL_EMPLOYEE:
        raise HTTPException(
            status_code=400,
            detail="Individual permissions can only be granted to hotel employees"
        )
    
    # Hotel isolation
    if current_user.role == UserRole.VENDOR_ADMIN:
        if user.hotel_id != current_user.hotel_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if permission already granted
    result = await db.execute(
        select(HotelEmployeePermission).where(
            HotelEmployeePermission.user_id == user_id,
            HotelEmployeePermission.permission == perm_data.permission,
            HotelEmployeePermission.revoked_at.is_(None)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Permission already granted")
    
    # Grant permission
    new_perm = HotelEmployeePermission(
        user_id=user_id,
        permission=perm_data.permission,
        granted_by=current_user.id
    )
    
    db.add(new_perm)
    await db.commit()
    await db.refresh(new_perm)
    
    # Audit log
    await create_audit_log(
        db, current_user.id, "grant_permission", "permission",
        str(new_perm.id),
        {"user_id": user_id, "permission": perm_data.permission},
        request.client.host if request else None
    )
    
    return new_perm


@router.delete("/{user_id}/permissions/{permission_value}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_permission(
    user_id: int,
    permission_value: str,
    current_user: User = Depends(require_permission(Permission.ASSIGN_PERMISSIONS)),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Revoke individual permission from a hotel employee"""
    # Find permission grant
    result = await db.execute(
        select(HotelEmployeePermission).where(
            HotelEmployeePermission.user_id == user_id,
            HotelEmployeePermission.permission == permission_value,
            HotelEmployeePermission.revoked_at.is_(None)
        )
    )
    perm_grant = result.scalar_one_or_none()
    
    if not perm_grant:
        raise HTTPException(status_code=404, detail="Permission grant not found")
    
    # Verify user belongs to current user's hotel (for vendor admins)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if current_user.role == UserRole.VENDOR_ADMIN:
        if user.hotel_id != current_user.hotel_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Revoke permission
    perm_grant.revoked_at = datetime.utcnow()
    
    await db.commit()
    
    # Audit log
    await create_audit_log(
        db, current_user.id, "revoke_permission", "permission",
        str(perm_grant.id),
        {"user_id": user_id, "permission": permission_value},
        request.client.host if request else None
    )
    
    return None


# ==================
# Audit Log Endpoints
# ==================

@router.get("/audit-logs/", response_model=AuditLogListResponse)
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    current_user: User = Depends(require_permission(Permission.VIEW_AUDIT_LOG)),
    db: AsyncSession = Depends(get_db)
):
    """
    List audit logs with filters.
    Vendor admins see only logs for users from their hotel.
    """
    # Build filters
    filters = []
    
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    
    if action:
        filters.append(AuditLog.action == action)
    
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    
    # Hotel isolation for vendor admins
    if current_user.role == UserRole.VENDOR_ADMIN:
        # Get all user IDs from current user's hotel
        hotel_users_result = await db.execute(
            select(User.id).where(User.hotel_id == current_user.hotel_id)
        )
        hotel_user_ids = [row[0] for row in hotel_users_result.all()]
        filters.append(AuditLog.user_id.in_(hotel_user_ids))
    
    # Count total
    count_query = select(func.count()).select_from(AuditLog)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Fetch logs
    query = (
        select(AuditLog)
        .where(and_(*filters))
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return AuditLogListResponse(
        logs=logs,
        total=total,
        skip=skip,
        limit=limit
    )
