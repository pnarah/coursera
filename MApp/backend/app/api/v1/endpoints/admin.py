from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.models.hotel import User, UserRole
from app.services.admin_service import AdminService
from app.schemas.admin import (
    PlatformMetrics,
    VendorListItem,
    VendorsListResponse,
    SubscriptionExtension,
    SystemConfigUpdate,
    AuditLogResponse
)
from app.schemas.employee import VendorApprovalRequestResponse, VendorRequestsListResponse
from app.models.employee import VendorApprovalRequest, ApprovalStatus
from sqlalchemy import select

router = APIRouter()


@router.get("/metrics", response_model=PlatformMetrics)
async def get_platform_metrics(
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get platform-wide metrics (SYSTEM_ADMIN only)"""
    service = AdminService(db)
    metrics = await service.get_platform_metrics()
    return PlatformMetrics(**metrics)


@router.get("/vendors", response_model=VendorsListResponse)
async def get_all_vendors(
    limit: int = 50,
    skip: int = 0,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get all vendors with details (SYSTEM_ADMIN only)"""
    service = AdminService(db)
    vendors = await service.get_all_vendors(limit=limit, skip=skip)
    return {"vendors": vendors}


@router.get("/vendor-requests", response_model=VendorRequestsListResponse)
async def get_pending_vendor_requests(
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get pending vendor approval requests (SYSTEM_ADMIN only)"""
    result = await db.execute(
        select(VendorApprovalRequest).where(
            VendorApprovalRequest.status == ApprovalStatus.PENDING
        )
    )
    requests = result.scalars().all()
    return {"requests": requests}


@router.post("/subscriptions/extend")
async def extend_subscription(
    extension: SubscriptionExtension,
    request: Request,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Manually extend subscription (SYSTEM_ADMIN only)"""
    service = AdminService(db)

    try:
        await service.extend_subscription(
            admin_user_id=current_user.id,
            subscription_id=extension.subscription_id,
            extend_days=extension.extend_days,
            reason=extension.reason
        )
        return {"message": "Subscription extended successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    admin_user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs (SYSTEM_ADMIN only)"""
    service = AdminService(db)
    logs = await service.get_audit_logs(
        admin_user_id=admin_user_id,
        action=action,
        limit=limit,
        offset=offset
    )
    return logs


@router.put("/system-config")
async def update_system_config(
    config_update: SystemConfigUpdate,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Update system configuration (SYSTEM_ADMIN only)"""
    service = AdminService(db)

    try:
        await service.update_system_config(
            admin_user_id=current_user.id,
            config_key=config_update.config_key,
            config_value=config_update.config_value
        )
        return {"message": "Configuration updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
