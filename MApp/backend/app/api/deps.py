"""
Authentication and authorization dependencies for FastAPI
"""
from typing import Set, Optional, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.config import settings
from app.db.session import get_db
from app.models.hotel import User, UserRole, HotelEmployeePermission
from app.core.permissions import Permission, get_role_permissions, has_permission


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    Raises 401 if token is invalid or user not found.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory to require specific user roles.
    
    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.SYSTEM_ADMIN))])
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of these roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    
    return role_checker


async def _get_user_permissions(user: User, db: AsyncSession) -> Set[Permission]:
    """
    Helper function to get all permissions for a user (role-based + individually granted).
    """
    # Get role-based permissions
    role_perms = get_role_permissions(user.role.value)
    
    # For hotel employees, also fetch individually granted permissions
    if user.role == UserRole.HOTEL_EMPLOYEE:
        result = await db.execute(
            select(HotelEmployeePermission).where(
                HotelEmployeePermission.user_id == user.id,
                HotelEmployeePermission.revoked_at.is_(None)
            )
        )
        extra_perms = result.scalars().all()
        
        # Add individual permissions to the set
        for perm in extra_perms:
            try:
                role_perms.add(Permission(perm.permission))
            except ValueError:
                # Invalid permission string in database, skip it
                pass
    
    return role_perms


def require_permission(*required_permissions: Permission) -> Callable:
    """
    Dependency factory to require specific permissions.
    Checks both role-based permissions and individually granted permissions.
    
    Usage:
        @router.post("/rooms", dependencies=[Depends(require_permission(Permission.CREATE_ROOM))])
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Get all user permissions
        user_permissions = await _get_user_permissions(current_user, db)
        
        # Check if user has all required permissions
        missing_perms = set(required_permissions) - user_permissions
        
        if missing_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {[p.value for p in missing_perms]}"
            )
        
        return current_user
    
    return permission_checker


def require_any_permission(*required_permissions: Permission) -> Callable:
    """
    Dependency factory to require ANY of the specified permissions (OR logic).
    
    Usage:
        @router.get("/bookings", dependencies=[
            Depends(require_any_permission(
                Permission.VIEW_OWN_BOOKINGS,
                Permission.VIEW_ALL_BOOKINGS
            ))
        ])
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Get all user permissions
        user_permissions = await _get_user_permissions(current_user, db)
        
        # Check if user has at least one of the required permissions
        has_any = any(perm in user_permissions for perm in required_permissions)
        
        if not has_any:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these permissions: {[p.value for p in required_permissions]}"
            )
        
        return current_user
    
    return permission_checker


def require_hotel_access() -> Callable:
    """
    Dependency to ensure user has access to their hotel's resources only.
    System admins can access all hotels.
    Vendor admins and hotel employees can only access their assigned hotel.
    
    Usage:
        @router.get("/hotels/{hotel_id}/rooms")
        async def get_rooms(
            hotel_id: int,
            current_user: User = Depends(require_hotel_access())
        ):
            # current_user.hotel_id is validated against hotel_id
    """
    async def hotel_access_checker(
        request: Request,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # System admins have access to all hotels
        if current_user.role == UserRole.SYSTEM_ADMIN:
            return current_user
        
        # Get hotel_id from path parameters
        hotel_id = request.path_params.get("hotel_id")
        
        if hotel_id is None:
            # No hotel_id in path, allow access (will be validated by business logic)
            return current_user
        
        # Convert to int
        try:
            hotel_id = int(hotel_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid hotel_id format"
            )
        
        # Check if user belongs to this hotel
        if current_user.hotel_id != hotel_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this hotel's resources"
            )
        
        return current_user
    
    return hotel_access_checker


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get the current user.
    Returns None if no valid token is provided.
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    # Fetch user
    async def _get_user():
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        return result.scalar_one_or_none()
    
    return _get_user()


# Helper function to check permissions in route handlers
async def check_user_permission(
    user: User,
    permission: Permission,
    db: AsyncSession
) -> bool:
    """
    Utility function to check if a user has a specific permission.
    Can be used in route handlers for conditional logic.
    """
    user_permissions = await _get_user_permissions(user, db)
    return permission in user_permissions
