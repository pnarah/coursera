from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.models.admin import AdminAuditLog, SystemConfig, PlatformMetrics
from app.models.hotel import User
from app.models.subscription import VendorSubscription, SubscriptionStatus
from app.models.employee import VendorApprovalRequest, ApprovalStatus
from app.schemas.admin import VendorListItem


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_admin_action(
        self,
        admin_user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log admin action for audit trail"""
        audit_log = AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(audit_log)
        await self.db.commit()

    async def get_platform_metrics(self) -> Dict[str, Any]:
        """Get platform-wide metrics with caching"""
        # Check if we have cached metrics < 1 hour old
        result = await self.db.execute(
            select(PlatformMetrics).where(
                PlatformMetrics.metric_key == "dashboard_metrics"
            )
        )
        cached = result.scalar_one_or_none()

        if cached and (datetime.utcnow() - cached.calculated_at).total_seconds() < 3600:
            return cached.metric_value

        # Calculate fresh metrics
        # Total users
        total_users = await self.db.scalar(select(func.count(User.id)))

        # Total vendors
        from app.models.hotel import UserRole
        total_vendors = await self.db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.VENDOR_ADMIN)
        )

        # Total hotels
        from app.models.hotel import Hotel
        total_hotels = await self.db.scalar(select(func.count(Hotel.id)))

        # Active subscriptions
        active_subscriptions = await self.db.scalar(
            select(func.count(VendorSubscription.id)).where(
                VendorSubscription.status == SubscriptionStatus.ACTIVE
            )
        )

        # Expired subscriptions
        expired_subscriptions = await self.db.scalar(
            select(func.count(VendorSubscription.id)).where(
                VendorSubscription.status == SubscriptionStatus.EXPIRED
            )
        )

        # New users this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_this_week = await self.db.scalar(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )

        # Pending vendor requests
        pending_vendor_requests = await self.db.scalar(
            select(func.count(VendorApprovalRequest.id)).where(
                VendorApprovalRequest.status == ApprovalStatus.PENDING
            )
        )

        metrics = {
            "total_users": total_users or 0,
            "total_vendors": total_vendors or 0,
            "total_hotels": total_hotels or 0,
            "active_subscriptions": active_subscriptions or 0,
            "expired_subscriptions": expired_subscriptions or 0,
            "new_users_this_week": new_users_this_week or 0,
            "pending_vendor_requests": pending_vendor_requests or 0
        }

        # Cache the metrics
        if cached:
            cached.metric_value = metrics
            cached.calculated_at = datetime.utcnow()
        else:
            cached = PlatformMetrics(
                metric_key="dashboard_metrics",
                metric_value=metrics,
                calculated_at=datetime.utcnow()
            )
            self.db.add(cached)

        await self.db.commit()
        return metrics

    async def get_all_vendors(
        self,
        limit: int = 50,
        skip: int = 0
    ) -> List[VendorListItem]:
        """Get all vendors with their details"""
        from app.models.hotel import UserRole, Hotel

        # Query vendors with hotel count and subscription info
        query = select(
            User.id,
            User.mobile_number,
            func.count(Hotel.id).label("total_hotels")
        ).outerjoin(
            Hotel, User.id == Hotel.vendor_id
        ).where(
            User.role == UserRole.VENDOR_ADMIN
        ).group_by(
            User.id, User.mobile_number
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        vendor_data = result.all()

        vendors = []
        for user_id, mobile_number, total_hotels in vendor_data:
            # Get subscription info
            sub_result = await self.db.execute(
                select(VendorSubscription).where(
                    VendorSubscription.vendor_id == user_id
                ).order_by(VendorSubscription.created_at.desc())
            )
            subscription = sub_result.scalars().first()

            vendors.append(VendorListItem(
                user_id=user_id,
                mobile_number=mobile_number,
                total_hotels=total_hotels or 0,
                subscription_status=subscription.status.value if subscription else "NO_SUBSCRIPTION",
                subscription_end_date=subscription.end_date if subscription else None
            ))

        return vendors

    async def extend_subscription(
        self,
        admin_user_id: int,
        subscription_id: int,
        extend_days: int,
        reason: str
    ):
        """Manually extend a subscription (admin only)"""
        result = await self.db.execute(
            select(VendorSubscription).where(VendorSubscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise ValueError("Subscription not found")

        old_end_date = subscription.end_date
        subscription.end_date = subscription.end_date + timedelta(days=extend_days)

        # If subscription was expired, reactivate it
        if subscription.status == SubscriptionStatus.EXPIRED:
            subscription.status = SubscriptionStatus.ACTIVE

        await self.db.commit()

        # Log the action
        await self.log_admin_action(
            admin_user_id=admin_user_id,
            action="SUBSCRIPTION_EXTENDED",
            resource_type="SUBSCRIPTION",
            resource_id=subscription_id,
            old_value={"end_date": old_end_date.isoformat(), "reason": reason},
            new_value={"end_date": subscription.end_date.isoformat(), "extend_days": extend_days}
        )

    async def get_audit_logs(
        self,
        admin_user_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AdminAuditLog]:
        """Get audit logs with filters"""
        query = select(AdminAuditLog)

        if admin_user_id:
            query = query.where(AdminAuditLog.admin_user_id == admin_user_id)

        if action:
            query = query.where(AdminAuditLog.action == action)

        query = query.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_system_config(self, config_key: str) -> Optional[SystemConfig]:
        """Get system configuration"""
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.config_key == config_key)
        )
        return result.scalar_one_or_none()

    async def update_system_config(
        self,
        admin_user_id: int,
        config_key: str,
        config_value: Dict[str, Any]
    ):
        """Update system configuration"""
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.config_key == config_key)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError("Configuration not found")

        if not config.is_editable:
            raise ValueError("Configuration is not editable")

        old_value = config.config_value

        config.config_value = config_value
        config.updated_by = admin_user_id
        config.updated_at = datetime.utcnow()

        await self.db.commit()

        # Log action
        await self.log_admin_action(
            admin_user_id=admin_user_id,
            action="CONFIG_UPDATED",
            resource_type="SYSTEM_CONFIG",
            resource_id=config.id,
            old_value=old_value,
            new_value=config_value
        )
