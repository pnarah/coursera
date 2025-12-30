"""Seed notification templates into the database."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine
from app.models.notification import NotificationTemplate, NotificationChannel


async def seed_notification_templates():
    """Seed default notification templates."""
    
    templates = [
        # Subscription Expiry Warning Templates
        {
            "template_key": "subscription_expiry_warning",
            "channel": NotificationChannel.EMAIL,
            "subject": "Your subscription is expiring soon",
            "body_template": """Dear {vendor_name},

Your {plan_name} subscription is set to expire in {days_remaining} days on {expiry_date}.

To ensure uninterrupted service, please renew your subscription before the expiry date.

You have a {grace_period_days} day grace period after expiry to renew without losing access to your data.

Best regards,
The MApp Team""",
            "is_active": True
        },
        {
            "template_key": "subscription_expiry_warning",
            "channel": NotificationChannel.SMS,
            "subject": None,
            "body_template": "MApp Alert: Your {plan_name} subscription expires in {days_remaining} days ({expiry_date}). Renew now to avoid service interruption.",
            "is_active": True
        },
        {
            "template_key": "subscription_expiry_warning",
            "channel": NotificationChannel.IN_APP,
            "subject": "Subscription Expiring Soon",
            "body_template": "Your {plan_name} subscription will expire in {days_remaining} days on {expiry_date}. Renew now to continue enjoying all features.",
            "is_active": True
        },
        
        # Subscription Renewed Templates
        {
            "template_key": "subscription_renewed",
            "channel": NotificationChannel.EMAIL,
            "subject": "Subscription Successfully Renewed",
            "body_template": """Dear {vendor_name},

Thank you for renewing your subscription!

Plan: {plan_name}
Start Date: {start_date}
End Date: {end_date}
Amount Paid: ${amount}

Your subscription is now active and all features are available.

Best regards,
The MApp Team""",
            "is_active": True
        },
        {
            "template_key": "subscription_renewed",
            "channel": NotificationChannel.SMS,
            "subject": None,
            "body_template": "MApp: Your {plan_name} subscription has been renewed successfully. Valid until {end_date}. Thank you!",
            "is_active": True
        },
        {
            "template_key": "subscription_renewed",
            "channel": NotificationChannel.IN_APP,
            "subject": "Subscription Renewed",
            "body_template": "Your {plan_name} subscription has been renewed and is active until {end_date}. Thank you for your continued trust!",
            "is_active": True
        },
        
        # Subscription Expired Templates
        {
            "template_key": "subscription_expired",
            "channel": NotificationChannel.EMAIL,
            "subject": "Your subscription has expired",
            "body_template": """Dear {vendor_name},

Your {plan_name} subscription expired on {expiry_date}.

You have a {grace_period_days} day grace period to renew your subscription. During this time, you can still access your data but some features may be limited.

After the grace period, your account will be suspended.

Please renew your subscription to continue enjoying all features.

Best regards,
The MApp Team""",
            "is_active": True
        },
        {
            "template_key": "subscription_expired",
            "channel": NotificationChannel.SMS,
            "subject": None,
            "body_template": "MApp Alert: Your subscription expired on {expiry_date}. You have {grace_period_days} days to renew. Renew now to avoid service suspension.",
            "is_active": True
        },
        {
            "template_key": "subscription_expired",
            "channel": NotificationChannel.IN_APP,
            "subject": "Subscription Expired",
            "body_template": "Your subscription expired on {expiry_date}. You have {grace_period_days} days grace period to renew. Please renew to avoid account suspension.",
            "is_active": True
        },
        
        # Booking Confirmed Templates
        {
            "template_key": "booking_confirmed",
            "channel": NotificationChannel.EMAIL,
            "subject": "Booking Confirmation - {booking_reference}",
            "body_template": """Dear {guest_name},

Your booking has been confirmed!

Booking Reference: {booking_reference}
Hotel: {hotel_name}
Room Type: {room_type}
Check-in: {check_in_date}
Check-out: {check_out_date}
Total Amount: ${total_amount}

We look forward to welcoming you!

Best regards,
{hotel_name}""",
            "is_active": True
        },
        {
            "template_key": "booking_confirmed",
            "channel": NotificationChannel.SMS,
            "subject": None,
            "body_template": "Booking confirmed! Ref: {booking_reference}. {hotel_name}, Check-in: {check_in_date}. See you soon!",
            "is_active": True
        },
        {
            "template_key": "booking_confirmed",
            "channel": NotificationChannel.IN_APP,
            "subject": "Booking Confirmed",
            "body_template": "Your booking at {hotel_name} is confirmed! Reference: {booking_reference}. Check-in: {check_in_date}.",
            "is_active": True
        },
        
        # Payment Received Templates
        {
            "template_key": "payment_received",
            "channel": NotificationChannel.EMAIL,
            "subject": "Payment Received - {transaction_id}",
            "body_template": """Dear {vendor_name},

We have received your payment.

Transaction ID: {transaction_id}
Amount: ${amount}
Payment Method: {payment_method}
Date: {payment_date}

Thank you for your payment!

Best regards,
The MApp Team""",
            "is_active": True
        },
        {
            "template_key": "payment_received",
            "channel": NotificationChannel.IN_APP,
            "subject": "Payment Received",
            "body_template": "Payment of ${amount} received successfully. Transaction ID: {transaction_id}. Thank you!",
            "is_active": True
        },
        
        # Welcome Templates
        {
            "template_key": "welcome_vendor",
            "channel": NotificationChannel.EMAIL,
            "subject": "Welcome to MApp!",
            "body_template": """Dear {vendor_name},

Welcome to MApp! We're excited to have you on board.

Your account has been created and you can now start managing your hotel properties.

To get started:
1. Complete your hotel profile
2. Add room types and inventory
3. Set up pricing rules
4. Start accepting bookings

If you need any assistance, our support team is here to help.

Best regards,
The MApp Team""",
            "is_active": True
        },
        {
            "template_key": "welcome_vendor",
            "channel": NotificationChannel.IN_APP,
            "subject": "Welcome to MApp!",
            "body_template": "Welcome {vendor_name}! Your account is ready. Start by setting up your hotel profile and room inventory.",
            "is_active": True
        },
    ]
    
    async with AsyncSession(engine) as session:
        try:
            # Check if templates already exist
            from sqlalchemy import select
            
            for template_data in templates:
                stmt = select(NotificationTemplate).where(
                    NotificationTemplate.template_key == template_data["template_key"],
                    NotificationTemplate.channel == template_data["channel"]
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"Template already exists: {template_data['template_key']} ({template_data['channel'].value})")
                    continue
                
                template = NotificationTemplate(**template_data)
                session.add(template)
                print(f"Created template: {template_data['template_key']} ({template_data['channel'].value})")
            
            await session.commit()
            print("\n✅ Notification templates seeded successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding notification templates: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_notification_templates())
