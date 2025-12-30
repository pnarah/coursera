from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.hotel import User, UserRole
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    SendNotificationRequest,
    BulkNotificationRequest
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(False, description="Filter to show only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user notifications"""
    service = NotificationService(db)
    
    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset
    )
    
    # Get total count and unread count
    all_notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=False,
        limit=1000  # Get all for counting
    )
    unread_count = await service.get_unread_count(current_user.id)
    
    return {
        "notifications": notifications,
        "total": len(all_notifications),
        "unread_count": unread_count
    }


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications"""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.put("/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    service = NotificationService(db)
    success = await service.mark_as_read(notification_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}


@router.put("/mark-all-read", response_model=dict)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read"""
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)
    return {"message": f"Marked {count} notifications as read"}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user notification preferences"""
    service = NotificationService(db)
    prefs = await service.get_user_preferences(current_user.id)
    return prefs


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user notification preferences"""
    service = NotificationService(db)
    prefs = await service.update_preferences(
        user_id=current_user.id,
        preferences=preferences.model_dump(exclude_unset=True)
    )
    return prefs


# Admin-only endpoints
@router.post("/send", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def send_notification(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a notification to current user (for testing or manual sends)"""
    service = NotificationService(db)
    
    try:
        notification = await service.create_notification(
            user_id=current_user.id,
            template_key=request.template_key,
            channel=request.channel,
            variables=request.variables,
            scheduled_at=request.scheduled_at
        )
        return notification
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/send-bulk", response_model=dict, status_code=status.HTTP_201_CREATED)
async def send_bulk_notifications(
    request: BulkNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send bulk notifications (System Admin only)"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admins can send bulk notifications"
        )
    
    service = NotificationService(db)
    sent_count = 0
    failed_count = 0
    
    for user_id in request.user_ids:
        try:
            await service.create_notification(
                user_id=user_id,
                template_key=request.template_key,
                channel=request.channel,
                variables=request.variables
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            continue
    
    return {
        "message": f"Sent {sent_count} notifications, {failed_count} failed",
        "sent": sent_count,
        "failed": failed_count
    }
