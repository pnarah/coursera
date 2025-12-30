import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/widgets/app_drawer.dart';
import '../../../shared/widgets/common_widgets.dart';
import '../../../core/providers/dashboard_providers.dart';
import '../../../core/models/models.dart';

class VendorDashboardScreen extends ConsumerWidget {
  const VendorDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(currentUserProvider);
    final vendorHotels = ref.watch(vendorHotelsProvider);
    final subscription = ref.watch(activeSubscriptionProvider);
    final analytics = ref.watch(vendorAnalyticsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Vendor Dashboard'),
      ),
      drawer: currentUser.when(
        loading: () => null,
        error: (_, __) => null,
        data: (user) => AppDrawer(
          userRole: user?.role ?? '',
          userName: user?.fullName ?? 'Vendor',
          userMobile: user?.mobileNumber ?? '',
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/vendor/add-hotel'),
        icon: const Icon(Icons.add),
        label: const Text('Add Hotel'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(currentUserProvider);
          ref.invalidate(vendorHotelsProvider);
          ref.invalidate(activeSubscriptionProvider);
          ref.invalidate(vendorAnalyticsProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Subscription Status
              subscription.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: 'Failed to load subscription',
                  onRetry: () => ref.invalidate(activeSubscriptionProvider),
                ),
                data: (sub) => sub != null 
                  ? _buildSubscriptionCard(context, sub)
                  : const Card(
                      child: Padding(
                        padding: EdgeInsets.all(16),
                        child: Text('No active subscription'),
                      ),
                    ),
              ),
              
              const SizedBox(height: 24),
              
              // Analytics Overview
              _buildSectionTitle(context, 'This Month'),
              const SizedBox(height: 12),
              analytics.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => Row(
                  children: [
                    Expanded(
                      child: MetricCard(
                        title: 'Bookings',
                        value: '0',
                        icon: Icons.calendar_month,
                        color: Colors.blue,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: MetricCard(
                        title: 'Revenue',
                        value: '\$0',
                        icon: Icons.attach_money,
                        color: Colors.green,
                      ),
                    ),
                  ],
                ),
                data: (analyticsData) => Row(
                  children: [
                    Expanded(
                      child: MetricCard(
                        title: 'Bookings',
                        value: analyticsData.totalBookings.toString(),
                        icon: Icons.calendar_month,
                        color: Colors.blue,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: MetricCard(
                        title: 'Revenue',
                        value: '\$${analyticsData.totalRevenue.toStringAsFixed(0)}',
                        icon: Icons.attach_money,
                        color: Colors.green,
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Quick Actions
              _buildSectionTitle(context, 'Quick Actions'),
              const SizedBox(height: 12),
              currentUser.when(
                loading: () => const SizedBox.shrink(),
                error: (_, __) => const SizedBox.shrink(),
                data: (user) => GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 1.5,
                  children: [
                    _buildQuickAction(
                      context,
                      'Add Vendor Admin',
                      Icons.admin_panel_settings,
                      Colors.deepPurple,
                      () => context.push('/vendor/create-vendor?hotelId=${user?.hotelId ?? ''}'),
                    ),
                    _buildQuickAction(
                      context,
                      'Add Employee',
                      Icons.person_add,
                      Colors.indigo,
                      () => context.push('/vendor/create-employee?hotelId=${user?.hotelId ?? ''}'),
                    ),
                    _buildQuickAction(
                      context,
                      'Manage Hotels',
                      Icons.hotel,
                      Colors.blue,
                      () => context.push('/vendor/hotels'),
                    ),
                    _buildQuickAction(
                      context,
                      'Bookings',
                      Icons.calendar_today,
                      Colors.green,
                      () => context.push('/vendor/bookings'),
                    ),
                    _buildQuickAction(
                      context,
                      'Reports',
                      Icons.analytics,
                      Colors.purple,
                      () => context.push('/vendor/reports'),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),
              
              // Hotels List
              _buildSectionTitle(context, 'My Hotels'),
              const SizedBox(height: 12),
              vendorHotels.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: 'Failed to load hotels',
                  onRetry: () => ref.invalidate(vendorHotelsProvider),
                ),
                data: (hotels) => _buildHotelsList(context, hotels),
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
  
  Widget _buildSubscriptionCard(BuildContext context, Subscription subscription) {
    final daysLeft = subscription.endDate.difference(DateTime.now()).inDays;
    final isExpiringSoon = daysLeft <= 7;
    final isActive = subscription.status == 'ACTIVE';
    
    return Card(
      color: isActive
          ? (isExpiringSoon ? Colors.orange.shade50 : Colors.green.shade50)
          : Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.card_membership,
                  color: isActive
                      ? (isExpiringSoon ? Colors.orange : Colors.green)
                      : Colors.red,
                  size: 32,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        subscription.planName,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      Text(
                        isActive
                            ? (isExpiringSoon
                                ? 'Expires in $daysLeft days - Renew now!'
                                : 'Active until ${subscription.endDate.toString().split(' ')[0]}')
                            : 'Subscription ${subscription.status}',
                        style: TextStyle(
                          color: isActive
                              ? (isExpiringSoon
                                  ? Colors.orange.shade900
                                  : Colors.green.shade900)
                              : Colors.red.shade900,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (isExpiringSoon || !isActive) ...[
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => context.push('/vendor/subscription'),
                  icon: const Icon(Icons.refresh),
                  label: Text(isActive ? 'Renew Subscription' : 'Subscribe Now'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildHotelsList(BuildContext context, List<Hotel> hotels) {
    if (hotels.isEmpty) {
      return EmptyStateWidget(
        icon: Icons.hotel_outlined,
        title: 'No Hotels Added',
        message: 'Start by adding your first hotel to the platform',
        action: ElevatedButton.icon(
          onPressed: () => context.push('/vendor/add-hotel'),
          icon: const Icon(Icons.add),
          label: const Text('Add Your First Hotel'),
        ),
      );
    }
    
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: hotels.length,
      itemBuilder: (context, index) {
        final hotel = hotels[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: InkWell(
            onTap: () => context.push('/vendor/hotels/${hotel.id}'),
            borderRadius: BorderRadius.circular(16),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: Colors.blue.shade50,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      Icons.hotel,
                      size: 40,
                      color: Colors.blue.shade700,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          hotel.name,
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          hotel.location ?? hotel.address,
                          style: TextStyle(color: Colors.grey.shade600),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            _buildHotelStat(Icons.meeting_room, '${hotel.totalRooms} rooms'),
                            const SizedBox(width: 16),
                            if (hotel.starRating != null)
                              _buildHotelStat(Icons.star, hotel.starRating!.toString()),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right, color: Colors.grey.shade400),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
  
  Widget _buildHotelStat(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey.shade600),
        const SizedBox(width: 4),
        Text(
          text,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }

  Widget _buildQuickAction(
    BuildContext context,
    String title,
    IconData icon,
    Color color,
    VoidCallback onTap,
  ) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, size: 28, color: color),
              ),
              const SizedBox(height: 8),
              Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.w600),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
