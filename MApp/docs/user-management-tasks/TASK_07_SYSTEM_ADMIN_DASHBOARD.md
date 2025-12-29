# Task 07: System Admin Dashboard & Platform Management

**Priority:** High  
**Estimated Duration:** 4-5 days  
**Dependencies:** TASK_02 (User Roles & RBAC), TASK_04 (Subscription Management)  
**Status:** Not Started

---

## Overview

Build a comprehensive system admin dashboard for platform management, vendor oversight, subscription management, and analytics.

---

## Objectives

1. Create system admin dashboard with key metrics
2. Implement vendor management (approval, monitoring)
3. Add manual subscription extension capabilities
4. Build platform analytics and reporting
5. Implement audit logging for admin actions
6. Add system configuration management

---

## Backend Tasks

### 1. Database Schema

```sql
-- Migration: add_admin_features.py

-- Audit log for admin actions
CREATE TABLE admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),  -- VENDOR, SUBSCRIPTION, USER, etc.
    resource_id INTEGER,
    old_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- System configuration
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_editable BOOLEAN DEFAULT true,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Platform metrics (for caching)
CREATE TABLE platform_metrics (
    id SERIAL PRIMARY KEY,
    metric_key VARCHAR(100) UNIQUE NOT NULL,
    metric_value JSONB NOT NULL,
    calculated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_admin ON admin_audit_log(admin_user_id);
CREATE INDEX idx_audit_log_created_at ON admin_audit_log(created_at);
CREATE INDEX idx_audit_log_action ON admin_audit_log(action);
```

### 2. Models

**File:** `app/models/admin.py`

```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    old_value = Column(JSON)
    new_value = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    admin_user = relationship("User")

class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text)
    is_editable = Column(Boolean, default=True)
    updated_by = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    updater = relationship("User")

class PlatformMetrics(Base):
    __tablename__ = "platform_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_key = Column(String(100), unique=True, nullable=False, index=True)
    metric_value = Column(JSON, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)
```

### 3. Schemas

**File:** `app/schemas/admin.py`

```python
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class PlatformMetrics(BaseModel):
    total_users: int
    total_vendors: int
    total_hotels: int
    total_bookings: int
    active_subscriptions: int
    expired_subscriptions: int
    revenue_this_month: float
    revenue_last_month: float
    new_users_this_week: int
    pending_vendor_requests: int

class VendorListItem(BaseModel):
    id: int
    mobile_number: str
    business_name: Optional[str]
    total_hotels: int
    subscription_status: str
    subscription_end_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SubscriptionExtension(BaseModel):
    subscription_id: int
    extend_days: int
    reason: str

class SystemConfigUpdate(BaseModel):
    config_key: str
    config_value: Dict[str, Any]

class AuditLogResponse(BaseModel):
    id: int
    admin_user_id: int
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### 4. Admin Service

**File:** `app/services/admin_service.py`

```python
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from app.models.admin import AdminAuditLog, SystemConfig, PlatformMetrics
from app.models.user import User, UserRole
from app.models.hotel import Hotel
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.booking import Booking
from app.models.employee import VendorApprovalRequest, ApprovalStatus
import logging

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_admin_action(
        self,
        admin_user_id: int,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log admin action for audit trail"""
        log_entry = AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(log_entry)
        await self.db.commit()
    
    async def get_platform_metrics(self) -> Dict[str, Any]:
        """Calculate platform-wide metrics"""
        # Check if cached metrics exist (< 1 hour old)
        result = await self.db.execute(
            select(PlatformMetrics).where(
                and_(
                    PlatformMetrics.metric_key == "platform_overview",
                    PlatformMetrics.calculated_at > datetime.utcnow() - timedelta(hours=1)
                )
            )
        )
        cached = result.scalar_one_or_none()
        
        if cached:
            return cached.metric_value
        
        # Calculate fresh metrics
        # Total users
        total_users_result = await self.db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()
        
        # Total vendors
        total_vendors_result = await self.db.execute(
            select(func.count(User.id)).where(User.role == UserRole.VENDOR_ADMIN)
        )
        total_vendors = total_vendors_result.scalar()
        
        # Total hotels
        total_hotels_result = await self.db.execute(select(func.count(Hotel.id)))
        total_hotels = total_hotels_result.scalar()
        
        # Active subscriptions
        active_subs_result = await self.db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        active_subscriptions = active_subs_result.scalar()
        
        # Expired subscriptions
        expired_subs_result = await self.db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == SubscriptionStatus.EXPIRED
            )
        )
        expired_subscriptions = expired_subs_result.scalar()
        
        # New users this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )
        new_users_this_week = new_users_result.scalar()
        
        # Pending vendor requests
        pending_requests_result = await self.db.execute(
            select(func.count(VendorApprovalRequest.id)).where(
                VendorApprovalRequest.status == ApprovalStatus.PENDING
            )
        )
        pending_vendor_requests = pending_requests_result.scalar()
        
        metrics = {
            "total_users": total_users,
            "total_vendors": total_vendors,
            "total_hotels": total_hotels,
            "active_subscriptions": active_subscriptions,
            "expired_subscriptions": expired_subscriptions,
            "new_users_this_week": new_users_this_week,
            "pending_vendor_requests": pending_vendor_requests
        }
        
        # Cache metrics
        cached_metric = PlatformMetrics(
            metric_key="platform_overview",
            metric_value=metrics
        )
        
        # Delete old cache
        await self.db.execute(
            select(PlatformMetrics).where(
                PlatformMetrics.metric_key == "platform_overview"
            )
        )
        old_cache = result.scalar_one_or_none()
        if old_cache:
            await self.db.delete(old_cache)
        
        self.db.add(cached_metric)
        await self.db.commit()
        
        return metrics
    
    async def get_all_vendors(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all vendors with their details"""
        result = await self.db.execute(
            select(User).where(User.role == UserRole.VENDOR_ADMIN)
            .offset(offset).limit(limit)
        )
        vendors = result.scalars().all()
        
        vendor_details = []
        for vendor in vendors:
            # Get hotel count
            hotel_count_result = await self.db.execute(
                select(func.count(Hotel.id)).where(Hotel.vendor_id == vendor.id)
            )
            hotel_count = hotel_count_result.scalar()
            
            # Get active subscription
            sub_result = await self.db.execute(
                select(Subscription).where(
                    and_(
                        Subscription.user_id == vendor.id,
                        Subscription.status == SubscriptionStatus.ACTIVE
                    )
                ).order_by(Subscription.end_date.desc())
            )
            subscription = sub_result.scalar_one_or_none()
            
            vendor_details.append({
                "id": vendor.id,
                "mobile_number": vendor.mobile_number,
                "email": vendor.email,
                "total_hotels": hotel_count,
                "subscription_status": subscription.status if subscription else "NONE",
                "subscription_end_date": subscription.end_date if subscription else None,
                "created_at": vendor.created_at
            })
        
        return vendor_details
    
    async def extend_subscription(
        self,
        admin_user_id: int,
        subscription_id: int,
        extend_days: int,
        reason: str
    ):
        """Manually extend subscription"""
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        old_end_date = subscription.end_date
        
        # Extend end date
        subscription.end_date = subscription.end_date + timedelta(days=extend_days)
        
        # Reactivate if expired
        if subscription.status == SubscriptionStatus.EXPIRED:
            subscription.status = SubscriptionStatus.ACTIVE
        
        await self.db.commit()
        
        # Log action
        await self.log_admin_action(
            admin_user_id=admin_user_id,
            action="SUBSCRIPTION_EXTENDED",
            resource_type="SUBSCRIPTION",
            resource_id=subscription_id,
            old_value={"end_date": old_end_date.isoformat()},
            new_value={
                "end_date": subscription.end_date.isoformat(),
                "extend_days": extend_days,
                "reason": reason
            }
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
```

### 5. API Endpoints

**File:** `app/api/v1/admin.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.services.admin_service import AdminService
from app.services.vendor_service import VendorService
from app.schemas.admin import (
    PlatformMetrics,
    VendorListItem,
    SubscriptionExtension,
    SystemConfigUpdate,
    AuditLogResponse
)
from app.schemas.employee import VendorApprovalRequestResponse

router = APIRouter()

@router.get("/metrics", response_model=PlatformMetrics)
@require_role([UserRole.SYSTEM_ADMIN])
async def get_platform_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get platform-wide metrics (SYSTEM_ADMIN only)"""
    service = AdminService(db)
    metrics = await service.get_platform_metrics()
    return metrics

@router.get("/vendors")
@require_role([UserRole.SYSTEM_ADMIN])
async def get_all_vendors(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all vendors with details (SYSTEM_ADMIN only)"""
    service = AdminService(db)
    vendors = await service.get_all_vendors(limit=limit, offset=offset)
    return vendors

@router.get("/vendor-requests", response_model=List[VendorApprovalRequestResponse])
@require_role([UserRole.SYSTEM_ADMIN])
async def get_pending_vendor_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending vendor approval requests (SYSTEM_ADMIN only)"""
    from app.models.employee import VendorApprovalRequest, ApprovalStatus
    from sqlalchemy import select
    
    result = await db.execute(
        select(VendorApprovalRequest).where(
            VendorApprovalRequest.status == ApprovalStatus.PENDING
        )
    )
    requests = result.scalars().all()
    return requests

@router.post("/subscriptions/extend")
@require_role([UserRole.SYSTEM_ADMIN])
async def extend_subscription(
    extension: SubscriptionExtension,
    request: Request,
    current_user: User = Depends(get_current_user),
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
@require_role([UserRole.SYSTEM_ADMIN])
async def get_audit_logs(
    admin_user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
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
@require_role([UserRole.SYSTEM_ADMIN])
async def update_system_config(
    config_update: SystemConfigUpdate,
    current_user: User = Depends(get_current_user),
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
```

---

## Frontend Tasks

### 1. Admin Dashboard Screen

**File:** `lib/features/admin/screens/admin_dashboard_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/admin_provider.dart';

class AdminDashboardScreen extends ConsumerWidget {
  const AdminDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final metrics = ref.watch(platformMetricsProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('System Admin Dashboard'),
      ),
      body: metrics.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
        data: (data) => GridView.count(
          crossAxisCount: 2,
          padding: const EdgeInsets.all(16),
          children: [
            _MetricCard(
              title: 'Total Users',
              value: data.totalUsers.toString(),
              icon: Icons.people,
              color: Colors.blue,
            ),
            _MetricCard(
              title: 'Vendors',
              value: data.totalVendors.toString(),
              icon: Icons.business,
              color: Colors.green,
            ),
            _MetricCard(
              title: 'Hotels',
              value: data.totalHotels.toString(),
              icon: Icons.hotel,
              color: Colors.orange,
            ),
            _MetricCard(
              title: 'Active Subscriptions',
              value: data.activeSubscriptions.toString(),
              icon: Icons.check_circle,
              color: Colors.teal,
            ),
            _MetricCard(
              title: 'Pending Requests',
              value: data.pendingVendorRequests.toString(),
              icon: Icons.pending,
              color: Colors.red,
              onTap: () => Navigator.pushNamed(context, '/admin/vendor-requests'),
            ),
            _MetricCard(
              title: 'New Users (Week)',
              value: data.newUsersThisWeek.toString(),
              icon: Icons.person_add,
              color: Colors.purple,
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 48, color: color),
              const SizedBox(height: 8),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              Text(
                title,
                style: Theme.of(context).textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

### 2. Vendor Management Screen

**File:** `lib/features/admin/screens/vendor_management_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/admin_provider.dart';

class VendorManagementScreen extends ConsumerWidget {
  const VendorManagementScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final vendors = ref.watch(allVendorsProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vendor Management'),
      ),
      body: vendors.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
        data: (vendorList) => ListView.builder(
          itemCount: vendorList.length,
          itemBuilder: (context, index) {
            final vendor = vendorList[index];
            return ListTile(
              title: Text(vendor.mobileNumber),
              subtitle: Text(
                '${vendor.totalHotels} hotels • ${vendor.subscriptionStatus}',
              ),
              trailing: vendor.subscriptionEndDate != null
                  ? Text(
                      'Expires: ${vendor.subscriptionEndDate.toString().split(' ')[0]}',
                      style: const TextStyle(fontSize: 12),
                    )
                  : null,
              onTap: () {
                // Navigate to vendor details
              },
            );
          },
        ),
      ),
    );
  }
}
```

---

## Testing

```python
# tests/test_admin_service.py
@pytest.mark.asyncio
async def test_get_platform_metrics(db_session):
    service = AdminService(db_session)
    metrics = await service.get_platform_metrics()
    
    assert "total_users" in metrics
    assert "total_vendors" in metrics
    assert metrics["total_users"] >= 0

@pytest.mark.asyncio
async def test_extend_subscription(db_session, admin_user, test_subscription):
    service = AdminService(db_session)
    
    old_end_date = test_subscription.end_date
    
    await service.extend_subscription(
        admin_user_id=admin_user.id,
        subscription_id=test_subscription.id,
        extend_days=30,
        reason="Customer support request"
    )
    
    # Verify extension
    assert test_subscription.end_date > old_end_date
```

---

## Acceptance Criteria

- [ ] Platform metrics dashboard working
- [ ] Vendor list with details displayed
- [ ] Pending vendor requests viewable
- [ ] Manual subscription extension working
- [ ] Audit log tracking all admin actions
- [ ] System configuration editable
- [ ] Metrics cached for performance
- [ ] Admin actions logged with IP and user agent
- [ ] Unit tests pass

---

## Next Task

**[TASK_08_FRONTEND_DASHBOARDS.md](./TASK_08_FRONTEND_DASHBOARDS.md)** - Role-specific frontend dashboards for all user types.
