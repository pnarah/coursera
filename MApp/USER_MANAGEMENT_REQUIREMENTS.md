# User Management & Access Control Requirements

**MApp Hotel Booking Platform**  
**Version:** 1.0  
**Date:** December 29, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [User Types & Roles](#user-types--roles)
3. [Authentication & Registration](#authentication--registration)
4. [Session Management](#session-management)
5. [Access Control & Multi-Tenancy](#access-control--multi-tenancy)
6. [Subscription Management](#subscription-management)
7. [Notification System](#notification-system)
8. [Backend Requirements](#backend-requirements)
9. [Frontend Requirements](#frontend-requirements)
10. [Database Schema](#database-schema)
11. [API Endpoints](#api-endpoints)
12. [Security Considerations](#security-considerations)

---

## Overview

The MApp Hotel Booking Platform requires a comprehensive user management system supporting multiple user types with varying levels of access and permissions. The system must handle guest bookings, hotel management, and platform administration while ensuring data isolation and subscription-based access control.

### Key Requirements

- Multi-role user system
- Mobile number-based authentication
- Role-based access control (RBAC)
- Multi-tenant architecture
- Subscription-based hotel access
- Session management across devices
- Automated notifications and renewals

---

## User Types & Roles

### 1. Guest User
**Description:** Customers who book hotel rooms through the platform.

**Capabilities:**
- Register/Login with mobile number
- Search and view hotels
- Make bookings
- View booking history
- Manage profile
- Add/update guest details
- View running bills
- Make payments
- Order in-stay services
- Receive booking confirmations

**Access Level:** Lowest - Limited to own data only

---

### 2. System Admin
**Description:** Platform administrators with complete control over the application.

**Capabilities:**
- Full platform oversight and control
- Manage all users (view, create, edit, disable)
- Manage all hotels and vendors
- Approve/reject vendor registrations
- View all bookings and transactions
- Configure platform settings
- Manage subscription plans
- Extend vendor subscriptions
- Enable/disable vendor accounts
- View analytics and reports
- Manage pricing and commissions
- Configure notification templates
- Access audit logs
- System configuration

**Access Level:** Highest - Global access to all data

**Dashboard Features:**
- Total hotels, bookings, revenue
- Active/inactive vendors
- Subscription expiry alerts
- Platform analytics
- User activity monitoring

---

### 3. Vendor Admin (Hotel Owner)
**Description:** Hotel owners who register their properties on the platform.

**Capabilities:**
- Register hotel on platform
- Complete hotel profile (name, location, amenities, images)
- Manage hotel information
- Add/edit room types and inventory
- Set pricing and availability
- View hotel bookings
- Manage hotel staff (add/remove employees)
- View hotel revenue and analytics
- Manage subscription and payments
- Upload hotel images and documents
- Configure hotel policies (cancellation, check-in/out times)
- Respond to guest reviews
- Generate hotel reports

**Access Level:** Medium - Full access to own hotel data only

**Restrictions:**
- Cannot view other hotels' data
- Cannot access platform-wide settings
- Account subject to subscription status

**Dashboard Features:**
- Hotel occupancy rates
- Revenue by date range
- Active bookings
- Staff list
- Subscription status
- Payment history

---

### 4. Hotel Employee (Front Desk)
**Description:** Staff members who manage day-to-day hotel operations.

**Capabilities:**
- Login with assigned credentials
- View hotel bookings (assigned hotel only)
- Check-in/check-out guests
- Modify bookings (subject to permissions)
- Cancel bookings
- Process walk-in reservations
- Update room status (clean, maintenance)
- Process guest requests
- View room availability
- Add guest notes
- Process in-stay service orders
- Generate invoices
- Accept payments

**Access Level:** Low-Medium - Limited to assigned hotel, operational tasks only

**Restrictions:**
- Cannot modify hotel settings
- Cannot manage staff
- Cannot view revenue/analytics (unless granted)
- Cannot access other hotels
- Permissions set by Vendor Admin

**Dashboard Features:**
- Today's check-ins/check-outs
- Available rooms
- Current guests
- Pending service requests
- Quick booking interface

---

## Authentication & Registration

### Mobile Number-Based Authentication

#### Registration Flow

```
1. User enters mobile number
2. System checks if number exists
   - IF EXISTS: Treat as existing user (login flow)
   - IF NEW: Treat as new user (registration flow)
3. Send OTP to mobile number
4. User enters OTP
5. Verify OTP
6. IF NEW USER:
   - Prompt for user type selection (for non-guest)
   - Collect basic info (name, email)
   - Create user account with default role (Guest)
7. IF EXISTING USER:
   - Login and redirect based on role
8. Generate access token and refresh token
9. Create session record
10. Redirect to appropriate dashboard
```

#### Backend Requirements

- **OTP Generation:** 6-digit numeric code
- **OTP Validity:** 10 minutes
- **OTP Retry Limit:** 3 attempts per session
- **Rate Limiting:** Max 3 OTP requests per mobile per 30 minutes
- **Token Type:** JWT (JSON Web Tokens)
- **Access Token Expiry:** 1 hour
- **Refresh Token Expiry:** 30 days
- **Password (Optional):** For admin users, allow password setup
- **2FA:** Optional for admin users

#### Frontend Requirements

```dart
// Mobile number input
- Phone number validation (10 digits)
- Country code selection (default: +1)
- Clear error messaging

// OTP screen
- 6-digit OTP input
- Resend OTP button (disabled for 60 seconds)
- Auto-submit on 6 digits entered
- Countdown timer display

// User type selection (for new non-guest users)
- Radio buttons: Guest, Vendor Admin, Hotel Employee
- Note: System Admin created by existing admin only

// Profile completion
- Full name (required)
- Email (optional for guests, required for others)
- Role-specific fields
```

---

## Session Management

### Backend Session Management

#### Session Storage

```python
# Redis-based session storage
Session {
    session_id: UUID
    user_id: int
    mobile_number: string
    role: enum (GUEST, VENDOR_ADMIN, HOTEL_EMPLOYEE, SYSTEM_ADMIN)
    hotel_id: int (nullable - for hotel-specific users)
    device_info: string
    ip_address: string
    access_token: string
    refresh_token: string
    created_at: timestamp
    last_activity: timestamp
    expires_at: timestamp
    is_active: boolean
}
```

#### Session Requirements

- **Storage:** Redis (in-memory for fast access)
- **Session Timeout:** 
  - Guest: 24 hours of inactivity
  - Hotel Employee: 8 hours of inactivity
  - Vendor Admin: 12 hours of inactivity
  - System Admin: 4 hours of inactivity (higher security)
- **Concurrent Sessions:** 
  - Guest: Maximum 5 devices
  - Hotel Employee: Maximum 2 devices
  - Vendor Admin: Maximum 3 devices
  - System Admin: Maximum 2 devices
- **Session Invalidation:** On logout, password change, role change
- **Activity Tracking:** Update last_activity on each request
- **Auto Cleanup:** Remove expired sessions every hour

#### Session Security

```python
# Middleware checks
1. Validate access token signature
2. Check token expiry
3. Verify session exists in Redis
4. Validate user is active
5. Check hotel subscription status (for hotel users)
6. Update last_activity timestamp
7. Refresh token if expiring soon (< 5 minutes)
```

### Frontend Session Management

#### Session Storage

```dart
// Secure Storage (encrypted)
- access_token
- refresh_token
- user_id
- user_role
- hotel_id (for hotel-specific users)
- session_expiry

// App State Management (Riverpod/Provider)
- Current user object
- Session status
- Auto-logout on expiry
```

#### Session Handling

```dart
// Auto token refresh
- Check token expiry on app resume
- Refresh if expiring in < 5 minutes
- Silent refresh in background

// Auto logout
- On token expiry
- On session invalidation
- After inactivity timeout

// Session restoration
- On app restart, check stored tokens
- Validate with backend
- Restore user session or redirect to login

// Multi-device handling
- Show active sessions list
- Allow logout from other devices
- Notify on new device login
```

---

## Access Control & Multi-Tenancy

### Role-Based Access Control (RBAC)

#### Permission Matrix

| Feature | Guest | Hotel Employee | Vendor Admin | System Admin |
|---------|-------|----------------|--------------|--------------|
| View own bookings | ✅ | ✅ | ✅ | ✅ |
| Create booking | ✅ | ✅ | ✅ | ✅ |
| Cancel own booking | ✅ | ❌ | ✅ | ✅ |
| View hotel bookings | ❌ | ✅ (own hotel) | ✅ (own hotel) | ✅ (all) |
| Modify hotel bookings | ❌ | ✅ (own hotel) | ✅ (own hotel) | ✅ (all) |
| Manage hotel details | ❌ | ❌ | ✅ (own hotel) | ✅ (all) |
| Manage room inventory | ❌ | ❌ | ✅ (own hotel) | ✅ (all) |
| View hotel analytics | ❌ | ❌* | ✅ (own hotel) | ✅ (all) |
| Manage staff | ❌ | ❌ | ✅ (own hotel) | ✅ (all) |
| Manage subscriptions | ❌ | ❌ | ✅ (own) | ✅ (all) |
| Enable/disable hotels | ❌ | ❌ | ❌ | ✅ |
| View platform analytics | ❌ | ❌ | ❌ | ✅ |
| Manage all users | ❌ | ❌ | ❌ | ✅ |

*Can be granted by Vendor Admin

### Multi-Tenant Data Isolation

#### Backend Implementation

```python
# Decorator for hotel-scoped access
@require_hotel_access
def get_bookings(user, hotel_id):
    # Automatically filters based on user's hotel_id
    if user.role == 'SYSTEM_ADMIN':
        # Can access any hotel
        pass
    elif user.role in ['VENDOR_ADMIN', 'HOTEL_EMPLOYEE']:
        # Can only access own hotel
        if user.hotel_id != hotel_id:
            raise PermissionDenied("Access denied")
    else:
        # Guests cannot access hotel admin features
        raise PermissionDenied("Access denied")
    
    return get_hotel_bookings(hotel_id)

# Database query filters
# All hotel-related queries automatically filtered by hotel_id
SELECT * FROM bookings 
WHERE hotel_id = :user_hotel_id  # Injected by middleware
```

#### Frontend Implementation

```dart
// Route guards
class HotelAccessGuard {
  bool canAccess(User user, int hotelId) {
    if (user.role == UserRole.SYSTEM_ADMIN) return true;
    if (user.role == UserRole.VENDOR_ADMIN || 
        user.role == UserRole.HOTEL_EMPLOYEE) {
      return user.hotelId == hotelId;
    }
    return false;
  }
}

// UI element visibility
if (user.role.canManageHotel && user.hotelId == hotelId) {
  // Show management options
}

// API requests
// Automatically include hotel_id from user context
apiService.getBookings(hotelId: currentUser.hotelId);
```

---

## Subscription Management

### Subscription Plans

#### Available Plans

```yaml
Plans:
  - name: "Quarterly Plan"
    duration: 3 months
    price: $299
    features:
      - Up to 50 rooms
      - Unlimited bookings
      - Basic analytics
      - Email support
  
  - name: "Half-Yearly Plan"
    duration: 6 months
    price: $549
    discount: 8%
    features:
      - Up to 100 rooms
      - Unlimited bookings
      - Advanced analytics
      - Priority support
      - Custom branding
  
  - name: "Annual Plan"
    duration: 12 months
    price: $999
    discount: 17%
    features:
      - Unlimited rooms
      - Unlimited bookings
      - Premium analytics
      - 24/7 phone support
      - Custom branding
      - API access
      - Dedicated account manager
```

### Subscription Lifecycle

#### 1. Initial Subscription
```
1. Vendor Admin registers hotel
2. System creates vendor account (status: PENDING)
3. Vendor selects subscription plan
4. Payment processing
5. On payment success:
   - Activate subscription
   - Set expiry date (start_date + plan_duration)
   - Enable hotel (is_active = true)
   - Send confirmation email/SMS
6. On payment failure:
   - Keep account as PENDING
   - Allow retry
```

#### 2. Subscription Renewal
```
1. Auto-renewal (if enabled):
   - 7 days before expiry: Attempt payment
   - On success: Extend subscription
   - On failure: Send notification

2. Manual renewal:
   - Vendor receives expiry notifications
   - Vendor selects plan and pays
   - Subscription extended
```

#### 3. Subscription Expiry
```
Timeline:
- 30 days before expiry: First notification
- 15 days before expiry: Second notification
- 7 days before expiry: Urgent notification
- 3 days before expiry: Final warning
- On expiry day: Grace period starts (7 days)
- During grace period: Daily notifications
- After grace period: Disable hotel
```

#### 4. Hotel Disablement
```
When subscription expires and grace period ends:
1. Set hotel.is_active = false
2. Disable all hotel employees' access
3. Vendor admin can only:
   - View subscription status
   - Renew subscription
   - View historical data (read-only)
4. Cannot:
   - Accept new bookings
   - Modify hotel data
   - Manage staff
5. Existing bookings:
   - Honored until completion
   - Guests can check-in/out
   - No new bookings accepted
```

#### 5. Reactivation
```
When vendor renews after disablement:
1. Process payment
2. Set new expiry date
3. Set hotel.is_active = true
4. Re-enable hotel employees' access
5. Send reactivation notification
6. Allow full functionality
```

### Backend Requirements

#### Database Schema

```sql
CREATE TABLE vendor_subscriptions (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER REFERENCES users(id),
    hotel_id INTEGER REFERENCES hotels(id),
    plan_type VARCHAR(50), -- 'QUARTERLY', 'HALF_YEARLY', 'ANNUAL'
    amount DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20), -- 'ACTIVE', 'EXPIRED', 'GRACE_PERIOD', 'DISABLED'
    auto_renew BOOLEAN DEFAULT false,
    payment_method_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE subscription_payments (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES vendor_subscriptions(id),
    amount DECIMAL(10, 2),
    payment_date TIMESTAMP,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    status VARCHAR(20), -- 'PENDING', 'COMPLETED', 'FAILED', 'REFUNDED'
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE subscription_notifications (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES vendor_subscriptions(id),
    notification_type VARCHAR(50), -- '30_DAYS', '15_DAYS', '7_DAYS', etc.
    sent_at TIMESTAMP,
    delivery_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### API Requirements

```python
# Check subscription status (middleware)
def check_subscription_status(hotel_id):
    subscription = get_active_subscription(hotel_id)
    
    if not subscription:
        return False, "No active subscription"
    
    if subscription.status == 'DISABLED':
        return False, "Subscription expired"
    
    if subscription.status == 'GRACE_PERIOD':
        days_left = (subscription.end_date - today()).days
        return True, f"Grace period: {days_left} days left"
    
    if subscription.status == 'ACTIVE':
        return True, None
    
    return False, "Unknown subscription status"

# Background jobs
@scheduled(cron="0 0 * * *")  # Daily at midnight
def check_expiring_subscriptions():
    # Find subscriptions expiring in 30, 15, 7, 3 days
    # Send notifications
    # Update status to GRACE_PERIOD if expired
    # Disable after grace period
```

### Frontend Requirements

#### Vendor Dashboard

```dart
// Subscription status widget
SubscriptionStatusCard(
  status: subscription.status,
  expiryDate: subscription.endDate,
  daysRemaining: subscription.daysRemaining,
  planType: subscription.planType,
  onRenew: () => navigateToRenewal(),
  onUpgrade: () => navigateToUpgrade(),
);

// Features
- Visual status indicator (active/expiring/expired)
- Days remaining countdown
- Renew now button
- Upgrade plan option
- View payment history
- Download invoices
```

#### System Admin Dashboard

```dart
// Vendor subscription management
VendorSubscriptionList(
  filters: ['All', 'Active', 'Expiring Soon', 'Expired'],
  actions: [
    'Extend subscription',
    'Disable vendor',
    'Enable vendor',
    'View details',
  ],
);

// Features
- List all vendor subscriptions
- Filter by status
- Search by hotel name
- Bulk actions
- Manual extension option
- Override disable/enable
```

---

## Notification System

### Notification Types

#### 1. Subscription Notifications

```yaml
Expiry Reminders:
  - trigger: 30 days before expiry
    recipients: [Vendor Admin]
    channels: [Email, SMS, In-app]
    message: "Your subscription expires in 30 days. Renew now to continue service."
  
  - trigger: 15 days before expiry
    recipients: [Vendor Admin]
    channels: [Email, SMS, In-app]
    message: "Your subscription expires in 15 days. Avoid service interruption - renew today."
  
  - trigger: 7 days before expiry
    recipients: [Vendor Admin]
    channels: [Email, SMS, In-app]
    priority: HIGH
    message: "URGENT: Your subscription expires in 7 days. Renew now!"
  
  - trigger: 3 days before expiry
    recipients: [Vendor Admin]
    channels: [Email, SMS, In-app, WhatsApp]
    priority: CRITICAL
    message: "FINAL WARNING: Your subscription expires in 3 days!"

Grace Period:
  - trigger: On expiry day
    message: "Your subscription has expired. You have 7 days grace period to renew."
  
  - trigger: Daily during grace period
    message: "Grace period day {X} of 7. Renew now to avoid disablement."
  
  - trigger: End of grace period
    message: "Your hotel has been disabled due to expired subscription."

Renewal Success:
  - trigger: Payment successful
    message: "Subscription renewed successfully! Valid until {date}."
```

#### 2. Access Notifications

```yaml
New Login:
  - trigger: Login from new device
    recipients: [User]
    message: "New login detected on {device} from {location}."

Account Changes:
  - trigger: Role change, hotel assignment
    recipients: [User, System Admin]
    message: "Your account has been updated."

Access Denied:
  - trigger: Subscription expired
    recipients: [Hotel Employee, Vendor Admin]
    message: "Access restricted due to expired subscription."
```

### Backend Implementation

```python
# Notification service
class NotificationService:
    def send_subscription_expiry_notification(self, subscription):
        days_remaining = (subscription.end_date - today()).days
        
        notification = {
            'type': 'SUBSCRIPTION_EXPIRY',
            'priority': self.get_priority(days_remaining),
            'recipient': subscription.vendor,
            'channels': self.get_channels(days_remaining),
            'template': 'subscription_expiry',
            'data': {
                'days_remaining': days_remaining,
                'hotel_name': subscription.hotel.name,
                'renewal_link': generate_renewal_link(subscription)
            }
        }
        
        self.queue_notification(notification)
    
    def get_priority(self, days):
        if days <= 3: return 'CRITICAL'
        if days <= 7: return 'HIGH'
        return 'NORMAL'
    
    def get_channels(self, days):
        if days <= 3: return ['email', 'sms', 'in_app', 'whatsapp']
        if days <= 7: return ['email', 'sms', 'in_app']
        return ['email', 'in_app']

# Background job
@scheduled(cron="0 9 * * *")  # Daily at 9 AM
def send_expiry_reminders():
    # Find subscriptions expiring in 30, 15, 7, 3 days
    expiring_subscriptions = get_expiring_subscriptions([30, 15, 7, 3])
    
    for subscription in expiring_subscriptions:
        NotificationService().send_subscription_expiry_notification(subscription)
```

### Frontend Implementation

```dart
// In-app notification center
NotificationCenter(
  notifications: [
    {
      'type': 'subscription_expiry',
      'priority': 'high',
      'message': 'Subscription expires in 7 days',
      'action': 'Renew Now',
      'timestamp': DateTime.now(),
    }
  ],
  onNotificationTap: (notification) => handleNotification(notification),
);

// Push notification handler
void handlePushNotification(RemoteMessage message) {
  if (message.data['type'] == 'subscription_expiry') {
    showDialog(
      title: 'Subscription Expiring',
      message: message.notification.body,
      actions: [
        TextButton(text: 'Renew', onPressed: () => navigateToRenewal()),
        TextButton(text: 'Later', onPressed: () => dismiss()),
      ],
    );
  }
}
```

---

## Backend Requirements

### Database Schema Updates

```sql
-- Users table enhancement
ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'GUEST';
ALTER TABLE users ADD COLUMN hotel_id INTEGER REFERENCES hotels(id);
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT true;
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;
ALTER TABLE users ADD COLUMN created_by INTEGER REFERENCES users(id);

-- User roles enum
CREATE TYPE user_role AS ENUM ('GUEST', 'HOTEL_EMPLOYEE', 'VENDOR_ADMIN', 'SYSTEM_ADMIN');

-- Hotel employee permissions
CREATE TABLE hotel_employee_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    permission VARCHAR(100),
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW()
);

-- Session management
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    access_token TEXT,
    refresh_token TEXT,
    device_info TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Audit log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### API Middleware

```python
# Authentication middleware
async def authenticate_request(request):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        raise Unauthorized("No token provided")
    
    try:
        payload = decode_jwt(token)
        user_id = payload.get('user_id')
        
        # Check session in Redis
        session = await redis.get(f"session:{user_id}:{token}")
        if not session:
            raise Unauthorized("Invalid session")
        
        # Get user from database
        user = await get_user(user_id)
        if not user or not user.is_active:
            raise Unauthorized("User inactive")
        
        # Check hotel subscription if applicable
        if user.role in ['VENDOR_ADMIN', 'HOTEL_EMPLOYEE']:
            subscription = await get_hotel_subscription(user.hotel_id)
            if subscription.status == 'DISABLED':
                raise Forbidden("Hotel subscription expired")
        
        # Update last activity
        await redis.set(f"session:{user_id}:{token}", 
                       json.dumps({'last_activity': now()}),
                       ex=SESSION_TTL)
        
        request.state.user = user
        return user
        
    except JWTError:
        raise Unauthorized("Invalid token")

# Role-based access control decorator
def require_role(*allowed_roles):
    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            user = request.state.user
            if user.role not in allowed_roles:
                raise Forbidden("Insufficient permissions")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Hotel access decorator
def require_hotel_access(func):
    async def wrapper(request, hotel_id, *args, **kwargs):
        user = request.state.user
        
        if user.role == 'SYSTEM_ADMIN':
            # System admin can access any hotel
            pass
        elif user.role in ['VENDOR_ADMIN', 'HOTEL_EMPLOYEE']:
            # Can only access own hotel
            if user.hotel_id != hotel_id:
                raise Forbidden("Access denied to this hotel")
        else:
            raise Forbidden("Insufficient permissions")
        
        return await func(request, hotel_id, *args, **kwargs)
    return wrapper
```

### Service Layer

```python
# User service
class UserService:
    async def register_or_login(self, mobile_number, otp):
        # Check if user exists
        user = await self.get_user_by_mobile(mobile_number)
        
        if user:
            # Existing user - login
            if not user.is_active:
                raise Forbidden("Account disabled")
            
            user.last_login = now()
            await self.save(user)
            
            action = "login"
        else:
            # New user - register
            user = await self.create_user({
                'mobile_number': mobile_number,
                'role': 'GUEST',
                'is_active': True
            })
            
            action = "register"
        
        # Create session
        tokens = self.generate_tokens(user)
        session = await self.create_session(user, tokens)
        
        # Log activity
        await self.log_activity(user, action)
        
        return {
            'user': user,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'action': action
        }
    
    async def assign_hotel_employee(self, employee_id, hotel_id, 
                                    permissions, assigned_by):
        # Verify assigner is vendor admin of hotel
        if assigned_by.role != 'VENDOR_ADMIN' or \
           assigned_by.hotel_id != hotel_id:
            raise Forbidden("Cannot assign employee to this hotel")
        
        # Update employee
        employee = await self.get_user(employee_id)
        employee.role = 'HOTEL_EMPLOYEE'
        employee.hotel_id = hotel_id
        await self.save(employee)
        
        # Assign permissions
        for permission in permissions:
            await self.grant_permission(employee_id, permission, assigned_by.id)
        
        return employee

# Subscription service
class SubscriptionService:
    async def check_and_update_subscriptions(self):
        # Find expiring subscriptions
        expiring = await self.get_expiring_subscriptions()
        
        for subscription in expiring:
            days_remaining = (subscription.end_date - today()).days
            
            if days_remaining in [30, 15, 7, 3]:
                # Send notification
                await NotificationService().send_expiry_reminder(subscription)
            
            if days_remaining == 0:
                # Start grace period
                subscription.status = 'GRACE_PERIOD'
                subscription.grace_period_end = today() + timedelta(days=7)
                await self.save(subscription)
            
            if subscription.status == 'GRACE_PERIOD' and \
               today() > subscription.grace_period_end:
                # Disable hotel
                await self.disable_hotel(subscription.hotel_id)
                subscription.status = 'DISABLED'
                await self.save(subscription)
```

---

## Frontend Requirements

### State Management

```dart
// User state provider (Riverpod)
final userProvider = StateNotifierProvider<UserNotifier, UserState>((ref) {
  return UserNotifier();
});

class UserState {
  final User? user;
  final bool isAuthenticated;
  final String? accessToken;
  final UserRole? role;
  final int? hotelId;
  
  const UserState({
    this.user,
    this.isAuthenticated = false,
    this.accessToken,
    this.role,
    this.hotelId,
  });
}

class UserNotifier extends StateNotifier<UserState> {
  UserNotifier() : super(const UserState()) {
    _checkSession();
  }
  
  Future<void> _checkSession() async {
    final storage = SecureStorageService();
    final token = await storage.getToken();
    
    if (token != null) {
      // Validate token with backend
      final user = await apiService.validateSession();
      if (user != null) {
        state = UserState(
          user: user,
          isAuthenticated: true,
          accessToken: token,
          role: user.role,
          hotelId: user.hotelId,
        );
      }
    }
  }
  
  Future<void> login(String mobile, String otp) async {
    final result = await apiService.verifyOTP(mobile, otp);
    
    state = UserState(
      user: result.user,
      isAuthenticated: true,
      accessToken: result.accessToken,
      role: result.user.role,
      hotelId: result.user.hotelId,
    );
    
    await SecureStorageService().saveTokens(
      result.accessToken,
      result.refreshToken,
    );
  }
  
  Future<void> logout() async {
    await apiService.logout();
    await SecureStorageService().clearAll();
    state = const UserState();
  }
}
```

### Route Guards

```dart
// Role-based routing
class AppRouter {
  static Route<dynamic> generateRoute(RouteSettings settings) {
    final user = getCurrentUser();
    
    switch (settings.name) {
      case '/login':
        return MaterialPageRoute(builder: (_) => LoginScreen());
      
      case '/dashboard':
        if (!user.isAuthenticated) {
          return MaterialPageRoute(builder: (_) => LoginScreen());
        }
        
        // Route based on role
        switch (user.role) {
          case UserRole.GUEST:
            return MaterialPageRoute(builder: (_) => GuestDashboard());
          case UserRole.HOTEL_EMPLOYEE:
            return MaterialPageRoute(builder: (_) => EmployeeDashboard());
          case UserRole.VENDOR_ADMIN:
            return MaterialPageRoute(builder: (_) => VendorDashboard());
          case UserRole.SYSTEM_ADMIN:
            return MaterialPageRoute(builder: (_) => AdminDashboard());
        }
      
      case '/hotel/:id/manage':
        if (!canManageHotel(user, settings.arguments)) {
          return MaterialPageRoute(builder: (_) => AccessDeniedScreen());
        }
        return MaterialPageRoute(builder: (_) => HotelManagementScreen());
      
      default:
        return MaterialPageRoute(builder: (_) => NotFoundScreen());
    }
  }
  
  static bool canManageHotel(User user, dynamic hotelId) {
    if (user.role == UserRole.SYSTEM_ADMIN) return true;
    if (user.role == UserRole.VENDOR_ADMIN && user.hotelId == hotelId) return true;
    return false;
  }
}
```

### UI Components

```dart
// Role-based UI rendering
class RoleBasedWidget extends StatelessWidget {
  final UserRole requiredRole;
  final Widget child;
  final Widget? fallback;
  
  Widget build(BuildContext context) {
    final user = context.read(userProvider);
    
    if (user.role == requiredRole || user.role == UserRole.SYSTEM_ADMIN) {
      return child;
    }
    
    return fallback ?? SizedBox.shrink();
  }
}

// Usage
RoleBasedWidget(
  requiredRole: UserRole.VENDOR_ADMIN,
  child: ElevatedButton(
    onPressed: () => navigateToHotelSettings(),
    child: Text('Hotel Settings'),
  ),
);

// Subscription status banner
class SubscriptionBanner extends ConsumerWidget {
  Widget build(BuildContext context, WidgetRef ref) {
    final subscription = ref.watch(subscriptionProvider);
    
    if (subscription.status == SubscriptionStatus.EXPIRING) {
      return Container(
        color: Colors.orange,
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.warning, color: Colors.white),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Subscription expires in ${subscription.daysRemaining} days',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
              ),
            ),
            ElevatedButton(
              onPressed: () => navigateToRenewal(),
              child: Text('Renew Now'),
            ),
          ],
        ),
      );
    }
    
    if (subscription.status == SubscriptionStatus.EXPIRED) {
      return Container(
        color: Colors.red,
        padding: EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.error, color: Colors.white),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Subscription expired! Renew to continue service.',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
              ),
            ),
            ElevatedButton(
              onPressed: () => navigateToRenewal(),
              style: ElevatedButton.styleFrom(backgroundColor: Colors.white),
              child: Text('Renew Now', style: TextStyle(color: Colors.red)),
            ),
          ],
        ),
      );
    }
    
    return SizedBox.shrink();
  }
}
```

---

## Security Considerations

### 1. Authentication Security
- **OTP Security:** 
  - Use cryptographically secure random number generation
  - Hash OTPs before storing
  - Implement rate limiting (3 attempts per 30 min)
  - Auto-expire after 10 minutes
- **Token Security:**
  - Use RS256 algorithm for JWT signing
  - Store private keys securely (environment variables/secrets manager)
  - Implement token rotation
  - Blacklist tokens on logout

### 2. Authorization Security
- **Principle of Least Privilege:** Users only have minimum required permissions
- **Multi-Tenant Isolation:** Strict hotel_id filtering in all queries
- **Permission Checks:** Validate on both frontend and backend
- **Audit Logging:** Log all sensitive operations

### 3. Data Security
- **Encryption at Rest:** Encrypt sensitive user data
- **Encryption in Transit:** Use HTTPS/TLS for all communications
- **PII Protection:** Mask mobile numbers in logs (988-***-4416)
- **Data Retention:** Define policies for user data deletion

### 4. Session Security
- **Secure Storage:** Use HttpOnly, Secure cookies for web; encrypted storage for mobile
- **CSRF Protection:** Implement CSRF tokens for state-changing operations
- **XSS Prevention:** Sanitize all user inputs
- **Session Fixation:** Generate new session ID on login

### 5. Subscription Security
- **Payment Security:** Use PCI-compliant payment gateway
- **Fraud Detection:** Monitor unusual subscription patterns
- **Graceful Degradation:** Allow data access during grace period
- **Backup & Recovery:** Ensure data preservation during disablement

---

## Implementation Timeline

### Phase 1: Core User Management (2-3 weeks)
- Mobile number authentication
- User roles and permissions
- Session management
- Basic RBAC

### Phase 2: Multi-Tenant Access Control (2 weeks)
- Hotel-scoped data isolation
- Employee management
- Permission system

### Phase 3: Subscription Management (3 weeks)
- Subscription plans
- Payment integration
- Grace period handling
- Hotel enable/disable

### Phase 4: Notification System (1-2 weeks)
- Notification service
- Email/SMS integration
- In-app notifications
- Scheduled jobs

### Phase 5: Admin Dashboard (2 weeks)
- System admin features
- Vendor management
- Analytics and reporting
- Manual overrides

---

## Testing Requirements

### Unit Tests
- User registration/login flows
- Role-based permission checks
- Subscription lifecycle
- Token generation/validation

### Integration Tests
- End-to-end authentication flow
- Multi-tenant data isolation
- Subscription payment processing
- Notification delivery

### Security Tests
- Penetration testing
- Session hijacking attempts
- SQL injection prevention
- XSS vulnerability checks

### User Acceptance Tests
- Guest booking flow
- Hotel employee operations
- Vendor admin management
- System admin oversight

---

## Appendix

### User Role Comparison

| Aspect | Guest | Hotel Employee | Vendor Admin | System Admin |
|--------|-------|----------------|--------------|--------------|
| Registration | Self | Created by Vendor Admin | Self | Created by System Admin |
| Authentication | OTP | OTP + Credentials | OTP + Password | Password + 2FA |
| Session Timeout | 24h | 8h | 12h | 4h |
| Max Devices | 5 | 2 | 3 | 2 |
| Data Scope | Own bookings | Own hotel | Own hotel | All |
| Subscription Required | No | Yes (hotel) | Yes | No |

### Glossary

- **RBAC:** Role-Based Access Control
- **OTP:** One-Time Password
- **JWT:** JSON Web Token
- **2FA:** Two-Factor Authentication
- **PII:** Personally Identifiable Information
- **Multi-Tenancy:** Single system serving multiple isolated tenants
- **Grace Period:** Time after expiry before complete disablement

---

**Document Version:** 1.0  
**Last Updated:** December 29, 2025  
**Maintained By:** Development Team
