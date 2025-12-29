# Task 08: Frontend Dashboards (All User Roles)

**Priority:** Critical  
**Estimated Duration:** 5-6 days  
**Dependencies:** ALL Backend Tasks (TASK_01 through TASK_07)  
**Status:** Not Started

---

## Overview

Build comprehensive, role-specific frontend dashboards for all four user types: Guest, Hotel Employee, Vendor Admin, and System Admin. Each dashboard provides tailored functionality and navigation based on user permissions.

---

## Objectives

1. Create Guest dashboard (booking history, services, bill)
2. Build Hotel Employee dashboard (check-ins, room status, service orders)
3. Implement Vendor Admin dashboard (hotels, employees, subscriptions)
4. Develop System Admin dashboard (platform management)
5. Add role-based navigation and menu system
6. Implement unified state management across dashboards
7. Add responsive design for mobile and tablet

---

## Frontend Architecture

### State Management Structure

```
lib/
├── core/
│   ├── providers/
│   │   ├── auth_provider.dart          # Authentication state
│   │   └── user_provider.dart           # Current user info
│   ├── services/
│   │   └── api_client.dart              # HTTP client
│   └── theme/
│       └── app_theme.dart               # Theming
├── features/
│   ├── guest/
│   │   ├── screens/
│   │   │   ├── guest_dashboard_screen.dart
│   │   │   ├── booking_history_screen.dart
│   │   │   └── running_bill_screen.dart
│   │   ├── widgets/
│   │   │   ├── booking_card.dart
│   │   │   └── service_order_card.dart
│   │   └── providers/
│   │       └── guest_provider.dart
│   ├── employee/
│   │   ├── screens/
│   │   │   ├── employee_dashboard_screen.dart
│   │   │   ├── checkin_screen.dart
│   │   │   └── room_status_screen.dart
│   │   ├── widgets/
│   │   │   ├── room_card.dart
│   │   │   └── service_request_card.dart
│   │   └── providers/
│   │       └── employee_provider.dart
│   ├── vendor/
│   │   ├── screens/
│   │   │   ├── vendor_dashboard_screen.dart
│   │   │   ├── hotel_management_screen.dart
│   │   │   └── employee_management_screen.dart
│   │   ├── widgets/
│   │   │   ├── hotel_card.dart
│   │   │   └── subscription_card.dart
│   │   └── providers/
│   │       └── vendor_provider.dart
│   └── admin/
│       ├── screens/
│       │   ├── admin_dashboard_screen.dart
│       │   ├── vendor_approval_screen.dart
│       │   └── analytics_screen.dart
│       ├── widgets/
│       │   ├── metric_card.dart
│       │   └── vendor_request_card.dart
│       └── providers/
│           └── admin_provider.dart
└── shared/
    ├── widgets/
    │   ├── app_drawer.dart              # Role-based navigation
    │   ├── loading_indicator.dart
    │   └── error_widget.dart
    └── utils/
        └── role_helper.dart
```

---

## 1. Guest Dashboard

### Features:
- Current booking status
- Room details
- Running bill
- Service ordering
- Booking history
- Notifications

**File:** `lib/features/guest/screens/guest_dashboard_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/guest_provider.dart';
import '../../booking/providers/booking_provider.dart';

class GuestDashboardScreen extends ConsumerWidget {
  const GuestDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentBooking = ref.watch(currentBookingProvider);
    final bookingHistory = ref.watch(bookingHistoryProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications),
            onPressed: () => Navigator.pushNamed(context, '/notifications'),
          ),
        ],
      ),
      drawer: const AppDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(currentBookingProvider);
          ref.invalidate(bookingHistoryProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Current Booking Section
              _buildSectionTitle(context, 'Current Stay'),
              currentBooking.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, stack) => _ErrorCard(message: error.toString()),
                data: (booking) {
                  if (booking == null) {
                    return _NoBookingCard(
                      onBookNow: () => Navigator.pushNamed(context, '/search-hotels'),
                    );
                  }
                  return _CurrentBookingCard(booking: booking);
                },
              ),
              
              const SizedBox(height: 24),
              
              // Quick Actions
              _buildSectionTitle(context, 'Quick Actions'),
              _QuickActionsGrid(),
              
              const SizedBox(height: 24),
              
              // Booking History
              _buildSectionTitle(context, 'Past Bookings'),
              bookingHistory.when(
                loading: () => const CircularProgressIndicator(),
                error: (error, stack) => Text('Error: $error'),
                data: (bookings) {
                  if (bookings.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('No past bookings'),
                    );
                  }
                  return ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: bookings.take(3).length,
                    itemBuilder: (context, index) {
                      return BookingHistoryCard(booking: bookings[index]);
                    },
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildSectionTitle(BuildContext context, String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

class _CurrentBookingCard extends StatelessWidget {
  final Booking booking;
  
  const _CurrentBookingCard({required this.booking});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              booking.hotelName,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.calendar_today, size: 16),
                const SizedBox(width: 8),
                Text('${booking.checkInDate} - ${booking.checkOutDate}'),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.room, size: 16),
                const SizedBox(width: 8),
                Text('Room ${booking.roomNumber} - ${booking.roomType}'),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _ActionButton(
                  icon: Icons.restaurant,
                  label: 'Order Food',
                  onTap: () => Navigator.pushNamed(context, '/order-services'),
                ),
                _ActionButton(
                  icon: Icons.receipt,
                  label: 'View Bill',
                  onTap: () => Navigator.pushNamed(context, '/running-bill'),
                ),
                _ActionButton(
                  icon: Icons.chat,
                  label: 'Help',
                  onTap: () => Navigator.pushNamed(context, '/support'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickActionsGrid extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 3,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      children: [
        _QuickActionCard(
          icon: Icons.search,
          label: 'Search Hotels',
          onTap: () => Navigator.pushNamed(context, '/search-hotels'),
        ),
        _QuickActionCard(
          icon: Icons.receipt_long,
          label: 'My Bookings',
          onTap: () => Navigator.pushNamed(context, '/booking-history'),
        ),
        _QuickActionCard(
          icon: Icons.person,
          label: 'Profile',
          onTap: () => Navigator.pushNamed(context, '/profile'),
        ),
      ],
    );
  }
}
```

---

## 2. Hotel Employee Dashboard

### Features:
- Check-in/Check-out management
- Room status overview
- Service requests
- Guest list
- Daily tasks

**File:** `lib/features/employee/screens/employee_dashboard_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/employee_provider.dart';

class EmployeeDashboardScreen extends ConsumerWidget {
  const EmployeeDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hotelInfo = ref.watch(employeeHotelProvider);
    final todayCheckIns = ref.watch(todayCheckInsProvider);
    final pendingServices = ref.watch(pendingServiceRequestsProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Employee Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: () => Navigator.pushNamed(context, '/scan-checkin'),
          ),
        ],
      ),
      drawer: const AppDrawer(),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(todayCheckInsProvider);
          ref.invalidate(pendingServiceRequestsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Hotel Info
            hotelInfo.when(
              loading: () => const CircularProgressIndicator(),
              error: (error, stack) => Text('Error: $error'),
              data: (hotel) => Card(
                child: ListTile(
                  leading: const Icon(Icons.hotel, size: 40),
                  title: Text(hotel.name),
                  subtitle: Text(hotel.address),
                ),
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Today's Stats
            _buildStatsRow(context, todayCheckIns, pendingServices),
            
            const SizedBox(height: 24),
            
            // Quick Actions
            Text(
              'Quick Actions',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              children: [
                _ActionCard(
                  icon: Icons.how_to_reg,
                  label: 'Check-In Guest',
                  color: Colors.green,
                  onTap: () => Navigator.pushNamed(context, '/checkin'),
                ),
                _ActionCard(
                  icon: Icons.exit_to_app,
                  label: 'Check-Out',
                  color: Colors.orange,
                  onTap: () => Navigator.pushNamed(context, '/checkout'),
                ),
                _ActionCard(
                  icon: Icons.meeting_room,
                  label: 'Room Status',
                  color: Colors.blue,
                  onTap: () => Navigator.pushNamed(context, '/room-status'),
                ),
                _ActionCard(
                  icon: Icons.room_service,
                  label: 'Service Requests',
                  color: Colors.purple,
                  onTap: () => Navigator.pushNamed(context, '/service-requests'),
                ),
              ],
            ),
            
            const SizedBox(height: 24),
            
            // Today's Check-Ins
            Text(
              'Today\'s Check-Ins',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            todayCheckIns.when(
              loading: () => const CircularProgressIndicator(),
              error: (error, stack) => Text('Error: $error'),
              data: (checkIns) {
                if (checkIns.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('No check-ins today'),
                  );
                }
                return ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: checkIns.length,
                  itemBuilder: (context, index) {
                    return CheckInCard(checkIn: checkIns[index]);
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildStatsRow(
    BuildContext context,
    AsyncValue<List<CheckIn>> checkIns,
    AsyncValue<List<ServiceRequest>> services,
  ) {
    return Row(
      children: [
        Expanded(
          child: Card(
            color: Colors.green.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Icon(Icons.person_add, size: 32, color: Colors.green),
                  const SizedBox(height: 8),
                  Text(
                    checkIns.value?.length.toString() ?? '0',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const Text('Check-Ins Today'),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Card(
            color: Colors.orange.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Icon(Icons.pending_actions, size: 32, color: Colors.orange),
                  const SizedBox(height: 8),
                  Text(
                    services.value?.length.toString() ?? '0',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const Text('Pending Services'),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
```

---

## 3. Vendor Admin Dashboard

### Features:
- Hotel overview
- Subscription status
- Employee management
- Revenue analytics
- Booking statistics

**File:** `lib/features/vendor/screens/vendor_dashboard_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/vendor_provider.dart';

class VendorDashboardScreen extends ConsumerWidget {
  const VendorDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hotels = ref.watch(vendorHotelsProvider);
    final subscription = ref.watch(activeSubscriptionProvider);
    final analytics = ref.watch(vendorAnalyticsProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Vendor Dashboard'),
      ),
      drawer: const AppDrawer(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.pushNamed(context, '/add-hotel'),
        icon: const Icon(Icons.add),
        label: const Text('Add Hotel'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(vendorHotelsProvider);
          ref.invalidate(vendorAnalyticsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Subscription Status
            subscription.when(
              loading: () => const CircularProgressIndicator(),
              error: (error, stack) => _SubscriptionWarningCard(),
              data: (sub) {
                if (sub == null) {
                  return _SubscriptionWarningCard();
                }
                return _SubscriptionCard(subscription: sub);
              },
            ),
            
            const SizedBox(height: 24),
            
            // Analytics Overview
            analytics.when(
              loading: () => const CircularProgressIndicator(),
              error: (error, stack) => Text('Error: $error'),
              data: (data) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'This Month',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _MetricCard(
                          title: 'Bookings',
                          value: data.totalBookings.toString(),
                          icon: Icons.calendar_month,
                          color: Colors.blue,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _MetricCard(
                          title: 'Revenue',
                          value: '\$${data.totalRevenue.toStringAsFixed(0)}',
                          icon: Icons.attach_money,
                          color: Colors.green,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Hotels List
            Text(
              'My Hotels',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            hotels.when(
              loading: () => const CircularProgressIndicator(),
              error: (error, stack) => Text('Error: $error'),
              data: (hotelList) {
                if (hotelList.isEmpty) {
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(32),
                      child: Column(
                        children: [
                          const Icon(Icons.hotel, size: 64, color: Colors.grey),
                          const SizedBox(height: 16),
                          const Text('No hotels added yet'),
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: () => Navigator.pushNamed(context, '/add-hotel'),
                            icon: const Icon(Icons.add),
                            label: const Text('Add Your First Hotel'),
                          ),
                        ],
                      ),
                    ),
                  );
                }
                return ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: hotelList.length,
                  itemBuilder: (context, index) {
                    return HotelCard(hotel: hotelList[index]);
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _SubscriptionCard extends StatelessWidget {
  final Subscription subscription;
  
  const _SubscriptionCard({required this.subscription});

  @override
  Widget build(BuildContext context) {
    final daysLeft = subscription.endDate.difference(DateTime.now()).inDays;
    final isExpiringSoon = daysLeft <= 7;
    
    return Card(
      color: isExpiringSoon ? Colors.orange.shade50 : Colors.green.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.card_membership,
                  color: isExpiringSoon ? Colors.orange : Colors.green,
                ),
                const SizedBox(width: 8),
                Text(
                  '${subscription.planName} Plan',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              isExpiringSoon
                  ? 'Expires in $daysLeft days - Renew now!'
                  : 'Active until ${subscription.endDate.toString().split(' ')[0]}',
              style: TextStyle(
                color: isExpiringSoon ? Colors.orange.shade900 : Colors.green.shade900,
              ),
            ),
            if (isExpiringSoon) ...[
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: () => Navigator.pushNamed(context, '/renew-subscription'),
                child: const Text('Renew Subscription'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

---

## 4. Role-Based Navigation

**File:** `lib/shared/widgets/app_drawer.dart`

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/user_provider.dart';
import '../../core/providers/auth_provider.dart';

class AppDrawer extends ConsumerWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider).value;
    
    if (user == null) {
      return const Drawer(child: Center(child: CircularProgressIndicator()));
    }
    
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          UserAccountsDrawerHeader(
            accountName: Text(user.fullName ?? 'User'),
            accountEmail: Text(user.mobileNumber),
            currentAccountPicture: CircleAvatar(
              backgroundColor: Colors.white,
              child: Text(
                (user.fullName ?? 'U')[0].toUpperCase(),
                style: const TextStyle(fontSize: 32),
              ),
            ),
          ),
          
          // Common items
          ListTile(
            leading: const Icon(Icons.home),
            title: const Text('Dashboard'),
            onTap: () => Navigator.pushReplacementNamed(context, '/dashboard'),
          ),
          ListTile(
            leading: const Icon(Icons.person),
            title: const Text('Profile'),
            onTap: () => Navigator.pushNamed(context, '/profile'),
          ),
          ListTile(
            leading: const Icon(Icons.notifications),
            title: const Text('Notifications'),
            onTap: () => Navigator.pushNamed(context, '/notifications'),
          ),
          
          const Divider(),
          
          // Role-specific items
          ..._buildRoleSpecificItems(context, user.role),
          
          const Divider(),
          
          // Settings
          ListTile(
            leading: const Icon(Icons.settings),
            title: const Text('Settings'),
            onTap: () => Navigator.pushNamed(context, '/settings'),
          ),
          ListTile(
            leading: const Icon(Icons.logout),
            title: const Text('Logout'),
            onTap: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) {
                Navigator.pushReplacementNamed(context, '/login');
              }
            },
          ),
        ],
      ),
    );
  }
  
  List<Widget> _buildRoleSpecificItems(BuildContext context, String role) {
    switch (role) {
      case 'GUEST':
        return [
          ListTile(
            leading: const Icon(Icons.search),
            title: const Text('Search Hotels'),
            onTap: () => Navigator.pushNamed(context, '/search-hotels'),
          ),
          ListTile(
            leading: const Icon(Icons.history),
            title: const Text('My Bookings'),
            onTap: () => Navigator.pushNamed(context, '/booking-history'),
          ),
          ListTile(
            leading: const Icon(Icons.receipt),
            title: const Text('Running Bill'),
            onTap: () => Navigator.pushNamed(context, '/running-bill'),
          ),
        ];
      
      case 'HOTEL_EMPLOYEE':
        return [
          ListTile(
            leading: const Icon(Icons.how_to_reg),
            title: const Text('Check-In'),
            onTap: () => Navigator.pushNamed(context, '/checkin'),
          ),
          ListTile(
            leading: const Icon(Icons.meeting_room),
            title: const Text('Room Status'),
            onTap: () => Navigator.pushNamed(context, '/room-status'),
          ),
          ListTile(
            leading: const Icon(Icons.room_service),
            title: const Text('Service Requests'),
            onTap: () => Navigator.pushNamed(context, '/service-requests'),
          ),
        ];
      
      case 'VENDOR_ADMIN':
        return [
          ListTile(
            leading: const Icon(Icons.hotel),
            title: const Text('My Hotels'),
            onTap: () => Navigator.pushNamed(context, '/hotels'),
          ),
          ListTile(
            leading: const Icon(Icons.people),
            title: const Text('Employees'),
            onTap: () => Navigator.pushNamed(context, '/employees'),
          ),
          ListTile(
            leading: const Icon(Icons.card_membership),
            title: const Text('Subscription'),
            onTap: () => Navigator.pushNamed(context, '/subscription'),
          ),
          ListTile(
            leading: const Icon(Icons.analytics),
            title: const Text('Analytics'),
            onTap: () => Navigator.pushNamed(context, '/analytics'),
          ),
        ];
      
      case 'SYSTEM_ADMIN':
        return [
          ListTile(
            leading: const Icon(Icons.dashboard),
            title: const Text('Admin Panel'),
            onTap: () => Navigator.pushNamed(context, '/admin/dashboard'),
          ),
          ListTile(
            leading: const Icon(Icons.business),
            title: const Text('Vendors'),
            onTap: () => Navigator.pushNamed(context, '/admin/vendors'),
          ),
          ListTile(
            leading: const Icon(Icons.pending_actions),
            title: const Text('Approvals'),
            onTap: () => Navigator.pushNamed(context, '/admin/approvals'),
          ),
          ListTile(
            leading: const Icon(Icons.analytics),
            title: const Text('Platform Analytics'),
            onTap: () => Navigator.pushNamed(context, '/admin/analytics'),
          ),
        ];
      
      default:
        return [];
    }
  }
}
```

---

## Testing

### Widget Tests

```dart
// test/features/guest/screens/guest_dashboard_screen_test.dart
void main() {
  testWidgets('Guest dashboard shows current booking', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          currentBookingProvider.overrideWith((ref) => mockBooking),
        ],
        child: MaterialApp(home: GuestDashboardScreen()),
      ),
    );
    
    expect(find.text('Current Stay'), findsOneWidget);
    expect(find.byType(BookingCard), findsOneWidget);
  });
}
```

---

## Acceptance Criteria

- [ ] Guest dashboard shows current booking and quick actions
- [ ] Hotel employee dashboard displays check-ins and service requests
- [ ] Vendor dashboard shows hotels, subscription status, and analytics
- [ ] System admin dashboard displays platform metrics
- [ ] Role-based navigation drawer working for all roles
- [ ] Responsive design for mobile and tablet
- [ ] Pull-to-refresh functionality on all dashboards
- [ ] Proper error handling and loading states
- [ ] Navigation flow works seamlessly
- [ ] Widget tests pass

---

## Next Task

**[TASK_09_SECURITY_AUDIT.md](./TASK_09_SECURITY_AUDIT.md)** - Security hardening and compliance checks.
