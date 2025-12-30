import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/widgets/app_drawer.dart';
import '../../../shared/widgets/common_widgets.dart';
import '../../../core/providers/dashboard_providers.dart';
import '../../../core/models/models.dart';

class GuestDashboardScreen extends ConsumerWidget {
  const GuestDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(currentUserProvider);
    final currentBooking = ref.watch(currentBookingProvider);
    final bookingHistory = ref.watch(bookingHistoryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () => context.push('/notifications'),
          ),
        ],
      ),
      drawer: AppDrawer(
        userRole: currentUser.value?.role ?? 'GUEST',
        userName: currentUser.value?.fullName ?? 'Guest',
        userMobile: currentUser.value?.mobileNumber ?? '',
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(currentBookingProvider);
          ref.invalidate(bookingHistoryProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Current Booking Section
              _buildSectionTitle(context, 'Current Stay'),
              const SizedBox(height: 12),
              currentBooking.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(currentBookingProvider),
                ),
                data: (booking) => booking != null
                    ? _buildCurrentBookingCard(context, booking)
                    : _buildNoBookingCard(context),
              ),
              
              const SizedBox(height: 24),
              
              // Quick Actions
              _buildSectionTitle(context, 'Quick Actions'),
              const SizedBox(height: 12),
              _buildQuickActions(context),
              
              const SizedBox(height: 24),
              
              // Past Bookings
              _buildSectionTitle(context, 'Past Bookings'),
              const SizedBox(height: 12),
              bookingHistory.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(bookingHistoryProvider),
                ),
                data: (bookings) => _buildPastBookings(context, bookings),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildSectionTitle(BuildContext context, String title) {
    return Text(
      title,
      style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
    );
  }
  
  Widget _buildCurrentBookingCard(BuildContext context, Booking booking) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        booking.hotelName,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        booking.status,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey.shade600,
                            ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    booking.status,
                    style: TextStyle(
                      color: Colors.green.shade700,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            Row(
              children: [
                Icon(Icons.calendar_today, size: 16, color: Colors.grey.shade600),
                const SizedBox(width: 8),
                Text('${booking.checkInDate.toString().split(' ')[0]} - ${booking.checkOutDate.toString().split(' ')[0]}'),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.room, size: 16, color: Colors.grey.shade600),
                const SizedBox(width: 8),
                Text('Room ${booking.roomNumber} - ${booking.roomType}'),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => context.push('/services/${booking.id}'),
                    icon: const Icon(Icons.restaurant),
                    label: const Text('Order Food'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => context.push('/invoice/${booking.id}'),
                    icon: const Icon(Icons.receipt),
                    label: const Text('View Bill'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildNoBookingCard(BuildContext context) {
    return EmptyStateWidget(
      icon: Icons.hotel_outlined,
      title: 'No Active Booking',
      message: 'You don\'t have any active bookings at the moment',
      action: ElevatedButton.icon(
        onPressed: () => context.push('/hotels/search'),
        icon: const Icon(Icons.search),
        label: const Text('Search Hotels'),
      ),
    );
  }
  
  Widget _buildQuickActions(BuildContext context) {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 3,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      children: [
        QuickActionCard(
          icon: Icons.search,
          label: 'Search Hotels',
          color: Colors.blue,
          onTap: () => context.push('/hotels/search'),
        ),
        QuickActionCard(
          icon: Icons.history,
          label: 'My Bookings',
          color: Colors.purple,
          onTap: () => context.push('/bookings/history'),
        ),
        QuickActionCard(
          icon: Icons.person,
          label: 'Profile',
          color: Colors.orange,
          onTap: () => context.push('/profile'),
        ),
        QuickActionCard(
          icon: Icons.support_agent,
          label: 'Support',
          color: Colors.green,
          onTap: () => context.push('/support'),
        ),
        QuickActionCard(
          icon: Icons.star,
          label: 'Favorites',
          color: Colors.amber,
          onTap: () => context.push('/favorites'),
        ),
        QuickActionCard(
          icon: Icons.settings,
          label: 'Settings',
          color: Colors.grey,
          onTap: () => context.push('/settings'),
        ),
      ],
    );
  }
  
  Widget _buildPastBookings(BuildContext context, List<Booking> bookings) {
    if (bookings.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Column(
              children: [
                Icon(Icons.history, size: 48, color: Colors.grey.shade400),
                const SizedBox(height: 8),
                Text(
                  'No past bookings',
                  style: TextStyle(color: Colors.grey.shade600),
                ),
              ],
            ),
          ),
        ),
      );
    }
    
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: bookings.length,
      itemBuilder: (context, index) {
        final booking = bookings[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(Icons.hotel, color: Colors.blue.shade700),
            ),
            title: Text(booking.hotelName),
            subtitle: Text('${booking.checkInDate.toString().split(' ')[0]} - ${booking.checkOutDate.toString().split(' ')[0]}'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/booking/confirmation/${booking.id}'),
          ),
        );
      },
    );
  }
}
