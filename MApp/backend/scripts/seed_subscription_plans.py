#!/usr/bin/env python3
"""
Seed subscription plans into the database.
Run this script after running migrations.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.subscription import SubscriptionPlan


async def seed_plans():
    """Seed subscription plans"""
    async with AsyncSessionLocal() as db:
        plans_data = [
            {
                "name": "Quarterly Plan",
                "code": "QUARTERLY",
                "duration_months": 3,
                "price": 299.00,
                "max_rooms": 50,
                "features": {
                    "max_rooms": 50,
                    "unlimited_bookings": True,
                    "analytics": "basic",
                    "support": "email",
                    "multi_device_access": True
                },
                "discount_percentage": 0
            },
            {
                "name": "Half-Yearly Plan",
                "code": "HALF_YEARLY",
                "duration_months": 6,
                "price": 549.00,
                "max_rooms": 100,
                "features": {
                    "max_rooms": 100,
                    "unlimited_bookings": True,
                    "analytics": "advanced",
                    "support": "priority",
                    "custom_branding": True,
                    "multi_device_access": True,
                    "revenue_reports": True
                },
                "discount_percentage": 8.00
            },
            {
                "name": "Annual Plan",
                "code": "ANNUAL",
                "duration_months": 12,
                "price": 999.00,
                "max_rooms": None,  # Unlimited
                "features": {
                    "max_rooms": "unlimited",
                    "unlimited_bookings": True,
                    "analytics": "premium",
                    "support": "24/7_phone",
                    "custom_branding": True,
                    "api_access": True,
                    "dedicated_account_manager": True,
                    "multi_device_access": True,
                    "revenue_reports": True,
                    "custom_integrations": True
                },
                "discount_percentage": 17.00
            }
        ]
        
        print("Seeding subscription plans...")
        
        for plan_data in plans_data:
            # Check if plan already exists
            from sqlalchemy import select
            stmt = select(SubscriptionPlan).where(
                SubscriptionPlan.code == plan_data["code"]
            )
            result = await db.execute(stmt)
            existing_plan = result.scalar_one_or_none()
            
            if existing_plan:
                print(f"  ℹ️  Plan '{plan_data['name']}' already exists, skipping...")
                continue
            
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)
            print(f"  ✅ Added plan: {plan_data['name']} - ${plan_data['price']}/{plan_data['duration_months']}m")
        
        await db.commit()
        print("\n✨ Subscription plans seeded successfully!")


async def main():
    """Main function"""
    try:
        await seed_plans()
    except Exception as e:
        print(f"\n❌ Error seeding plans: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
