# Task 05: Notification System

**Priority:** High  
**Estimated Duration:** 3-4 days  
**Dependencies:** TASK_04 (Subscription Management)  
**Status:** Not Started

---

## Overview

Implement a multi-channel notification system to send alerts via Email, SMS, and In-app notifications. Focus on subscription-related notifications (expiry warnings, renewal confirmations) and booking-related updates.

---

## Objectives

1. Build notification service with multi-channel support (Email, SMS, In-app)
2. Implement subscription expiry alerts (7 days, 3 days, 1 day before)
3. Create scheduled background jobs for automated notifications
4. Add notification preferences per user
5. Implement notification history and delivery tracking
6. Add push notifications for mobile app

---

## Backend Tasks

### 1. Database Schema

Create migrations for notification tables:

```sql
-- Migration: create_notifications_table.py
CREATE TYPE notification_channel AS ENUM ('EMAIL', 'SMS', 'IN_APP', 'PUSH');
CREATE TYPE notification_status AS ENUM ('PENDING', 'SENT', 'FAILED', 'READ');

CREATE TABLE notification_templates (
    id SERIAL PRIMARY KEY,
    template_key VARCHAR(100) UNIQUE NOT NULL,
    channel notification_channel NOT NULL,
    subject VARCHAR(255),
    body_template TEXT NOT NULL,
    variables JSONB,  -- List of required variables
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES notification_templates(id),
    channel notification_channel NOT NULL,
    subject VARCHAR(255),
    body TEXT NOT NULL,
    metadata JSONB,  -- Additional data (subscription_id, booking_id, etc.)
    status notification_status DEFAULT 'PENDING',
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    email_enabled BOOLEAN DEFAULT true,
    sms_enabled BOOLEAN DEFAULT true,
    push_enabled BOOLEAN DEFAULT true,
    subscription_alerts BOOLEAN DEFAULT true,
    booking_alerts BOOLEAN DEFAULT true,
    marketing_emails BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_scheduled_at ON notifications(scheduled_at);
```

### 2. Models

**File:** `app/models/notification.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
import enum

class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    IN_APP = "IN_APP"
    PUSH = "PUSH"

class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    READ = "READ"

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_key = Column(String(100), unique=True, nullable=False, index=True)
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    subject = Column(String(255))
    body_template = Column(Text, nullable=False)
    variables = Column(JSON)  # List of required variables
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    notifications = relationship("Notification", back_populates="template")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(Integer, ForeignKey("notification_templates.id"))
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    subject = Column(String(255))
    body = Column(Text, nullable=False)
    metadata = Column(JSON)
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING)
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    read_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")
    template = relationship("NotificationTemplate", back_populates="notifications")

class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    subscription_alerts = Column(Boolean, default=True)
    booking_alerts = Column(Boolean, default=True)
    marketing_emails = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="notification_preferences")
```

### 3. Schemas

**File:** `app/schemas/notification.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.notification import NotificationChannel, NotificationStatus

class NotificationPreferencesBase(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    subscription_alerts: bool = True
    booking_alerts: bool = True
    marketing_emails: bool = False

class NotificationPreferencesUpdate(NotificationPreferencesBase):
    pass

class NotificationPreferencesResponse(NotificationPreferencesBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    user_id: int
    channel: NotificationChannel
    subject: Optional[str] = None
    body: str
    metadata: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    channel: NotificationChannel
    subject: Optional[str]
    body: str
    status: NotificationStatus
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
```

### 4. Notification Service

**File:** `app/services/notification_service.py`

```python
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.notification import (
    Notification, NotificationTemplate, UserNotificationPreference,
    NotificationChannel, NotificationStatus
)
from app.models.user import User
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class NotificationService:
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
        template_result = await self.db.execute(
            select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.template_key == template_key,
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.is_active == True
                )
            )
        )
        template = template_result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template {template_key} not found for channel {channel}")
        
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
            metadata=variables,
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
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            return False
        
        # Check user preferences
        prefs = await self.get_user_preferences(notification.user_id)
        
        if notification.channel == NotificationChannel.EMAIL and not prefs.email_enabled:
            logger.info(f"Email disabled for user {notification.user_id}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = "Email notifications disabled by user"
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
        """Send email via SendGrid/AWS SES"""
        # Get user email
        user_result = await self.db.execute(
            select(User).where(User.id == notification.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.email:
            logger.warning(f"No email for user {notification.user_id}")
            return False
        
        # TODO: Integrate with SendGrid/AWS SES
        # For now, just log
        logger.info(f"Sending email to {user.email}: {notification.subject}")
        logger.info(f"Body: {notification.body}")
        
        return True
    
    async def _send_sms(self, notification: Notification) -> bool:
        """Send SMS via Twilio/AWS SNS"""
        # Get user mobile
        user_result = await self.db.execute(
            select(User).where(User.id == notification.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return False
        
        # TODO: Integrate with Twilio/AWS SNS
        logger.info(f"Sending SMS to {user.mobile_number}: {notification.body}")
        
        return True
    
    async def _send_push(self, notification: Notification) -> bool:
        """Send push notification via FCM"""
        # TODO: Integrate with Firebase Cloud Messaging
        logger.info(f"Sending push notification to user {notification.user_id}")
        
        return True
    
    async def get_user_preferences(self, user_id: int) -> UserNotificationPreference:
        """Get or create user notification preferences"""
        result = await self.db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == user_id
            )
        )
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
            if hasattr(prefs, key):
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
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            return False
        
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        return True
    
    async def send_subscription_expiry_alerts(self):
        """Scheduled job: Send subscription expiry alerts"""
        from app.models.subscription import Subscription, SubscriptionStatus
        
        # Get subscriptions expiring in 7 days, 3 days, 1 day
        alert_days = [7, 3, 1]
        
        for days in alert_days:
            expiry_date = datetime.utcnow() + timedelta(days=days)
            
            result = await self.db.execute(
                select(Subscription).where(
                    and_(
                        Subscription.status == SubscriptionStatus.ACTIVE,
                        Subscription.end_date >= expiry_date,
                        Subscription.end_date < expiry_date + timedelta(days=1)
                    )
                )
            )
            subscriptions = result.scalars().all()
            
            for subscription in subscriptions:
                # Send email notification
                await self.create_notification(
                    user_id=subscription.user_id,
                    template_key="subscription_expiry_warning",
                    channel=NotificationChannel.EMAIL,
                    variables={
                        "days_remaining": days,
                        "expiry_date": subscription.end_date.strftime("%B %d, %Y"),
                        "plan_name": subscription.plan_name
                    }
                )
                
                # Send in-app notification
                await self.create_notification(
                    user_id=subscription.user_id,
                    template_key="subscription_expiry_warning",
                    channel=NotificationChannel.IN_APP,
                    variables={
                        "days_remaining": days,
                        "expiry_date": subscription.end_date.strftime("%B %d, %Y"),
                        "plan_name": subscription.plan_name
                    }
                )
                
                logger.info(f"Sent expiry alert for subscription {subscription.id}")
```

### 5. API Endpoints

**File:** `app/api/v1/notifications.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate
)

router = APIRouter()

@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
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
    
    # Count unread
    all_notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=False,
        limit=1000
    )
    unread_count = sum(1 for n in all_notifications if not n.read_at)
    
    return {
        "notifications": notifications,
        "total": len(all_notifications),
        "unread_count": unread_count
    }

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notification as read"""
    service = NotificationService(db)
    success = await service.mark_as_read(notification_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}

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
        preferences=preferences.model_dump()
    )
    return prefs
```

### 6. Background Jobs

**File:** `app/jobs/notification_jobs.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import AsyncSessionLocal
from app.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

async def send_subscription_expiry_alerts():
    """Daily job to send subscription expiry alerts"""
    async with AsyncSessionLocal() as db:
        service = NotificationService(db)
        await service.send_subscription_expiry_alerts()
        logger.info("Subscription expiry alerts sent")

def start_notification_scheduler():
    """Start background job scheduler"""
    scheduler = AsyncIOScheduler()
    
    # Run daily at 9 AM
    scheduler.add_job(
        send_subscription_expiry_alerts,
        'cron',
        hour=9,
        minute=0,
        id='subscription_expiry_alerts'
    )
    
    scheduler.start()
    logger.info("Notification scheduler started")
```

### 7. Seed Notification Templates

**File:** `scripts/seed_notification_templates.py`

```python
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.notification import NotificationTemplate, NotificationChannel

async def seed_templates():
    async with AsyncSessionLocal() as db:
        templates = [
            # Subscription expiry warnings
            {
                "template_key": "subscription_expiry_warning",
                "channel": NotificationChannel.EMAIL,
                "subject": "Your subscription expires in {days_remaining} days",
                "body_template": """
Hi,

Your {plan_name} subscription will expire on {expiry_date}.

To continue enjoying uninterrupted service, please renew your subscription before the expiry date.

Best regards,
MApp Team
                """,
                "variables": ["days_remaining", "expiry_date", "plan_name"]
            },
            {
                "template_key": "subscription_expiry_warning",
                "channel": NotificationChannel.IN_APP,
                "subject": None,
                "body_template": "Your {plan_name} subscription expires in {days_remaining} days on {expiry_date}",
                "variables": ["days_remaining", "expiry_date", "plan_name"]
            },
            # Subscription renewal
            {
                "template_key": "subscription_renewed",
                "channel": NotificationChannel.EMAIL,
                "subject": "Subscription Renewed Successfully",
                "body_template": """
Hi,

Your {plan_name} subscription has been successfully renewed.

New expiry date: {new_expiry_date}

Thank you for continuing with us!

Best regards,
MApp Team
                """,
                "variables": ["plan_name", "new_expiry_date"]
            },
            # Booking confirmation
            {
                "template_key": "booking_confirmed",
                "channel": NotificationChannel.EMAIL,
                "subject": "Booking Confirmed - {hotel_name}",
                "body_template": """
Hi {guest_name},

Your booking at {hotel_name} has been confirmed.

Check-in: {checkin_date}
Check-out: {checkout_date}
Room: {room_type}
Booking ID: {booking_id}

We look forward to hosting you!

Best regards,
{hotel_name}
                """,
                "variables": ["guest_name", "hotel_name", "checkin_date", "checkout_date", "room_type", "booking_id"]
            }
        ]
        
        for template_data in templates:
            template = NotificationTemplate(**template_data)
            db.add(template)
        
        await db.commit()
        print(f"Seeded {len(templates)} notification templates")

if __name__ == "__main__":
    asyncio.run(seed_templates())
```

---

## Frontend Tasks

### 1. Notification Preferences Screen

**File:** `lib/features/notifications/screens/notification_preferences_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/notification_provider.dart';

class NotificationPreferencesScreen extends ConsumerWidget {
  const NotificationPreferencesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferences = ref.watch(notificationPreferencesProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notification Preferences'),
      ),
      body: preferences.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
        data: (prefs) => ListView(
          children: [
            SwitchListTile(
              title: const Text('Email Notifications'),
              subtitle: const Text('Receive notifications via email'),
              value: prefs.emailEnabled,
              onChanged: (value) {
                ref.read(notificationPreferencesProvider.notifier)
                    .updatePreference('email_enabled', value);
              },
            ),
            SwitchListTile(
              title: const Text('SMS Notifications'),
              subtitle: const Text('Receive notifications via SMS'),
              value: prefs.smsEnabled,
              onChanged: (value) {
                ref.read(notificationPreferencesProvider.notifier)
                    .updatePreference('sms_enabled', value);
              },
            ),
            SwitchListTile(
              title: const Text('Push Notifications'),
              subtitle: const Text('Receive push notifications'),
              value: prefs.pushEnabled,
              onChanged: (value) {
                ref.read(notificationPreferencesProvider.notifier)
                    .updatePreference('push_enabled', value);
              },
            ),
            const Divider(),
            SwitchListTile(
              title: const Text('Subscription Alerts'),
              subtitle: const Text('Alerts about subscription status'),
              value: prefs.subscriptionAlerts,
              onChanged: (value) {
                ref.read(notificationPreferencesProvider.notifier)
                    .updatePreference('subscription_alerts', value);
              },
            ),
            SwitchListTile(
              title: const Text('Booking Alerts'),
              subtitle: const Text('Alerts about bookings and services'),
              value: prefs.bookingAlerts,
              onChanged: (value) {
                ref.read(notificationPreferencesProvider.notifier)
                    .updatePreference('booking_alerts', value);
              },
            ),
            SwitchListTile(
              title: const Text('Marketing Emails'),
              subtitle: const Text('Promotional offers and updates'),
              value: prefs.marketingEmails,
              onChanged: (value) {
                ref.read(notificationPreferencesProvider.notifier)
                    .updatePreference('marketing_emails', value);
              },
            ),
          ],
        ),
      ),
    );
  }
}
```

### 2. In-App Notifications List

**File:** `lib/features/notifications/screens/notifications_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/notification_provider.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(userNotificationsProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.pushNamed(context, '/notification-preferences');
            },
          ),
        ],
      ),
      body: notifications.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
        data: (notificationList) {
          if (notificationList.notifications.isEmpty) {
            return const Center(
              child: Text('No notifications'),
            );
          }
          
          return ListView.builder(
            itemCount: notificationList.notifications.length,
            itemBuilder: (context, index) {
              final notification = notificationList.notifications[index];
              return ListTile(
                leading: Icon(
                  Icons.notifications,
                  color: notification.readAt == null 
                      ? Theme.of(context).primaryColor 
                      : Colors.grey,
                ),
                title: Text(
                  notification.subject ?? 'Notification',
                  style: TextStyle(
                    fontWeight: notification.readAt == null 
                        ? FontWeight.bold 
                        : FontWeight.normal,
                  ),
                ),
                subtitle: Text(notification.body),
                trailing: Text(
                  _formatTime(notification.createdAt),
                  style: const TextStyle(fontSize: 12),
                ),
                onTap: () {
                  if (notification.readAt == null) {
                    ref.read(userNotificationsProvider.notifier)
                        .markAsRead(notification.id);
                  }
                },
              );
            },
          );
        },
      ),
    );
  }
  
  String _formatTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }
}
```

---

## Testing

### Unit Tests

```python
# tests/test_notification_service.py
import pytest
from app.services.notification_service import NotificationService
from app.models.notification import NotificationChannel

@pytest.mark.asyncio
async def test_create_notification_from_template(db_session, test_user):
    service = NotificationService(db_session)
    
    notification = await service.create_notification(
        user_id=test_user.id,
        template_key="subscription_expiry_warning",
        channel=NotificationChannel.EMAIL,
        variables={
            "days_remaining": "7",
            "expiry_date": "January 15, 2025",
            "plan_name": "Premium"
        }
    )
    
    assert notification.id is not None
    assert notification.user_id == test_user.id
    assert "7" in notification.body
    assert "Premium" in notification.body

@pytest.mark.asyncio
async def test_user_preferences(db_session, test_user):
    service = NotificationService(db_session)
    
    prefs = await service.get_user_preferences(test_user.id)
    assert prefs.email_enabled == True
    
    updated = await service.update_preferences(
        test_user.id,
        {"email_enabled": False}
    )
    assert updated.email_enabled == False
```

---

## Environment Variables

Add to `.env`:

```env
# Email Service (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@mapp.com

# SMS Service (Twilio)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+1234567890

# Push Notifications (Firebase)
FCM_SERVER_KEY=your_fcm_server_key

# Notification Settings
NOTIFICATION_BATCH_SIZE=100
NOTIFICATION_RETRY_ATTEMPTS=3
```

---

## Acceptance Criteria

- [ ] Notification templates created in database
- [ ] Email notifications working (SendGrid/AWS SES)
- [ ] SMS notifications working (Twilio/AWS SNS)
- [ ] Push notifications working (FCM)
- [ ] In-app notifications displayed
- [ ] User preferences can be updated
- [ ] Subscription expiry alerts sent automatically (7, 3, 1 days)
- [ ] Notification history tracked
- [ ] Failed notifications logged with error messages
- [ ] Scheduled notifications sent at correct time
- [ ] Mobile app displays notification badge
- [ ] Unit tests pass (80%+ coverage)

---

## Next Task

**[TASK_06_VENDOR_EMPLOYEE_MANAGEMENT.md](./TASK_06_VENDOR_EMPLOYEE_MANAGEMENT.md)** - Vendor registration and employee management system.
