from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.notification import (
    Notification, NotificationTemplate, UserNotificationPreference,
    NotificationChannel, NotificationStatus
)
from app.models.hotel import User
from app.models.subscription import VendorSubscription, SubscriptionStatus
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_notification(
        self,
        user_id: int,
        template_key: str,
        channel: NotificationChannel,
        variables: Dict[str, Any],
        scheduled_at: Optional[datetime] = None
    ) -> Notification:
        """Create notification from template"""
        # Get template
        stmt = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.template_key == template_key,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template '{template_key}' not found for channel {channel}")
        
        # Render template
        body = template.body_template
        subject = template.subject
        
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            body = body.replace(placeholder, str(value))
            if subject:
                subject = subject.replace(placeholder, str(value))
        
        # Create notification
        notification = Notification(
            user_id=user_id,
            template_id=template.id,
            channel=channel,
            subject=subject,
            body=body,
            notification_metadata=variables,
            scheduled_at=scheduled_at,
            status=NotificationStatus.PENDING
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        # Send immediately if not scheduled
        if not scheduled_at:
            await self.send_notification(notification.id)
        
        return notification
    
    async def send_notification(self, notification_id: int) -> bool:
        """Send a notification via appropriate channel"""
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await self.db.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if not notification:
            return False
        
        # Check user preferences
        prefs = await self.get_user_preferences(notification.user_id)
        
        # Check if channel is enabled
        if notification.channel == NotificationChannel.EMAIL and not prefs.email_enabled:
            logger.info(f"Email notifications disabled for user {notification.user_id}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Email notifications disabled by user"
            await self.db.commit()
            return False
        
        if notification.channel == NotificationChannel.SMS and not prefs.sms_enabled:
            logger.info(f"SMS notifications disabled for user {notification.user_id}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "SMS notifications disabled by user"
            await self.db.commit()
            return False
        
        if notification.channel == NotificationChannel.PUSH and not prefs.push_enabled:
            logger.info(f"Push notifications disabled for user {notification.user_id}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Push notifications disabled by user"
            await self.db.commit()
            return False
        
        try:
            if notification.channel == NotificationChannel.EMAIL:
                success = await self._send_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                success = await self._send_sms(notification)
            elif notification.channel == NotificationChannel.PUSH:
                success = await self._send_push(notification)
            else:
                # IN_APP notifications don't need sending
                success = True
            
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = NotificationStatus.FAILED
            
            await self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"Failed to send notification {notification_id}: {str(e)}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            await self.db.commit()
            return False
    
    async def _send_email(self, notification: Notification) -> bool:
        """Send email via SendGrid/AWS SES (placeholder)"""
        # Get user email
        user = await self.db.get(User, notification.user_id)
        
        if not user or not user.email:
            logger.warning(f"No email for user {notification.user_id}")
            return False
        
        # TODO: Integrate with SendGrid/AWS SES
        # For now, just log
        logger.info(f"📧 Sending email to {user.email}")
        logger.info(f"   Subject: {notification.subject}")
        logger.info(f"   Body: {notification.body[:100]}...")
        
        return True
    
    async def _send_sms(self, notification: Notification) -> bool:
        """Send SMS via Twilio/AWS SNS (placeholder)"""
        # Get user mobile
        user = await self.db.get(User, notification.user_id)
        
        if not user or not user.mobile_number:
            logger.warning(f"No mobile number for user {notification.user_id}")
            return False
        
        # TODO: Integrate with Twilio/AWS SNS
        logger.info(f"📱 Sending SMS to {user.country_code}{user.mobile_number}")
        logger.info(f"   Body: {notification.body[:160]}...")
        
        return True
    
    async def _send_push(self, notification: Notification) -> bool:
        """Send push notification via FCM (placeholder)"""
        # TODO: Integrate with Firebase Cloud Messaging
        logger.info(f"🔔 Sending push notification to user {notification.user_id}")
        logger.info(f"   Subject: {notification.subject}")
        logger.info(f"   Body: {notification.body[:100]}...")
        
        return True
    
    async def get_user_preferences(self, user_id: int) -> UserNotificationPreference:
        """Get or create user notification preferences"""
        stmt = select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id
        )
        result = await self.db.execute(stmt)
        prefs = result.scalar_one_or_none()
        
        if not prefs:
            # Create default preferences
            prefs = UserNotificationPreference(user_id=user_id)
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(prefs)
        
        return prefs
    
    async def update_preferences(
        self,
        user_id: int,
        preferences: Dict[str, bool]
    ) -> UserNotificationPreference:
        """Update user notification preferences"""
        prefs = await self.get_user_preferences(user_id)
        
        for key, value in preferences.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)
        
        prefs.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(prefs)
        
        return prefs
    
    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user"""
        stmt = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        
        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications"""
        stmt = select(func.count()).select_from(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.status != NotificationStatus.FAILED
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        stmt = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if not notification:
            return False
        
        if not notification.read_at:
            notification.read_at = datetime.utcnow()
            notification.status = NotificationStatus.READ
            await self.db.commit()
        
        return True
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user"""
        stmt = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.read_at.is_(None)
            )
        )
        result = await self.db.execute(stmt)
        notifications = result.scalars().all()
        
        count = 0
        for notification in notifications:
            notification.read_at = datetime.utcnow()
            notification.status = NotificationStatus.READ
            count += 1
        
        await self.db.commit()
        return count
    
    async def send_subscription_expiry_alerts(self):
        """Scheduled job: Send subscription expiry alerts for 7, 3, and 1 days"""
        # Alert days
        alert_days = [7, 3, 1]
        
        for days in alert_days:
            target_date = date.today() + timedelta(days=days)
            
            # Find subscriptions expiring on target date
            stmt = select(VendorSubscription).where(
                and_(
                    VendorSubscription.status == SubscriptionStatus.ACTIVE,
                    VendorSubscription.end_date == target_date
                )
            )
            result = await self.db.execute(stmt)
            subscriptions = list(result.scalars().all())
            
            logger.info(f"Found {len(subscriptions)} subscriptions expiring in {days} days")
            
            for subscription in subscriptions:
                # Get plan details
                plan = await self.db.get(subscription.__class__, subscription.id)
                
                variables = {
                    "days_remaining": str(days),
                    "expiry_date": subscription.end_date.strftime("%B %d, %Y"),
                    "plan_name": subscription.plan_type
                }
                
                try:
                    # Send email notification
                    await self.create_notification(
                        user_id=subscription.vendor_id,
                        template_key="subscription_expiry_warning",
                        channel=NotificationChannel.EMAIL,
                        variables=variables
                    )
                    
                    # Send in-app notification
                    await self.create_notification(
                        user_id=subscription.vendor_id,
                        template_key="subscription_expiry_warning",
                        channel=NotificationChannel.IN_APP,
                        variables=variables
                    )
                    
                    logger.info(f"Sent {days}-day expiry alert for subscription {subscription.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send expiry alert for subscription {subscription.id}: {e}")
        
        await self.db.commit()
    
    async def send_scheduled_notifications(self):
        """Background job: Send scheduled notifications that are due"""
        now = datetime.utcnow()
        
        stmt = select(Notification).where(
            and_(
                Notification.status == NotificationStatus.PENDING,
                Notification.scheduled_at.isnot(None),
                Notification.scheduled_at <= now
            )
        )
        result = await self.db.execute(stmt)
        notifications = list(result.scalars().all())
        
        logger.info(f"Processing {len(notifications)} scheduled notifications")
        
        for notification in notifications:
            try:
                await self.send_notification(notification.id)
            except Exception as e:
                logger.error(f"Failed to send scheduled notification {notification.id}: {e}")
