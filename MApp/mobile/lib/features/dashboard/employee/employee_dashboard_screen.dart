import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/widgets/app_drawer.dart';
import '../../../shared/widgets/common_widgets.dart';
import '../../../core/providers/dashboard_providers.dart';
import '../../../core/models/models.dart';

class EmployeeDashboardScreen extends ConsumerWidget {
  const EmployeeDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(currentUserProvider);
    final hotelInfo = ref.watch(employeeHotelProvider);
    final todayCheckIns = ref.watch(todayCheckInsProvider);
    final pendingServices = ref.watch(pendingServiceRequestsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Employee Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: () => context.push('/employee/scan-checkin'),
          ),
        ],
      ),
      drawer: AppDrawer(
        userRole: currentUser.value?.role ?? 'HOTEL_EMPLOYEE',
        userName: currentUser.value?.fullName ?? 'Employee',
        userMobile: currentUser.value?.mobileNumber ?? '',
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(todayCheckInsProvider);
          ref.invalidate(pendingServiceRequestsProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Hotel Info Card
              hotelInfo.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(employeeHotelProvider),
                ),
                data: (hotel) => hotel != null ? _buildHotelInfoCard(context, hotel) : const SizedBox(),
              ),
              
              const SizedBox(height: 24),
              
              // Today's Stats
              Row(
                children: [
                  Expanded(
                    child: todayCheckIns.when(
                      loading: () => const AppLoadingIndicator(),
                      error: (_, __) => MetricCard(
                        title: 'Check-Ins Today',
                        value: '0',
                        icon: Icons.person_add,
                        color: Colors.green,
                      ),
                      data: (checkIns) => MetricCard(
                        title: 'Check-Ins Today',
                        value: checkIns.length.toString(),
                        icon: Icons.person_add,
                        color: Colors.green,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: pendingServices.when(
                      loading: () => const AppLoadingIndicator(),
                      error: (_, __) => MetricCard(
                        title: 'Pending Services',
                        value: '0',
                        icon: Icons.pending_actions,
                        color: Colors.orange,
                      ),
                      data: (services) => MetricCard(
                        title: 'Pending Services',
                        value: services.length.toString(),
                        icon: Icons.pending_actions,
                        color: Colors.orange,
                        onTap: () => context.push('/employee/service-requests'),
                      ),
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 24),
              
              // Quick Actions
              _buildSectionTitle(context, 'Quick Actions'),
              const SizedBox(height: 12),
              _buildQuickActions(context),
              
              const SizedBox(height: 24),
              
              // Today's Check-Ins
              _buildSectionTitle(context, 'Today\'s Check-Ins'),
              const SizedBox(height: 12),
              todayCheckIns.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(todayCheckInsProvider),
                ),
                data: (checkIns) => _buildTodayCheckIns(context, checkIns),
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
  
  Widget _buildHotelInfoCard(BuildContext context, Hotel hotel) {
    return Card(
      child: ListTile(
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: Colors.blue.shade50,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(Icons.hotel, size: 32, color: Colors.blue.shade700),
        ),
        title: Text(
          hotel.name,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text(hotel.address),
      ),
    );
  }
  
  Widget _buildQuickActions(BuildContext context) {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.3,
      children: [
        _buildActionCard(
          context,
          title: 'Check-In Guest',
          icon: Icons.how_to_reg,
          color: Colors.green,
          onTap: () => context.push('/employee/checkin'),
        ),
        _buildActionCard(
          context,
          title: 'Check-Out',
          icon: Icons.exit_to_app,
          color: Colors.orange,
          onTap: () => context.push('/employee/checkout'),
        ),
        _buildActionCard(
          context,
          title: 'Room Status',
          icon: Icons.meeting_room,
          color: Colors.blue,
          onTap: () => context.push('/employee/room-status'),
        ),
        _buildActionCard(
          context,
          title: 'Service Requests',
          icon: Icons.room_service,
          color: Colors.purple,
          onTap: () => context.push('/employee/service-requests'),
        ),
      ],
    );
  }
  
  Widget _buildActionCard(
    BuildContext context, {
    required String title,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
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
                child: Icon(icon, size: 32, color: color),
              ),
              const SizedBox(height: 12),
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
  
  Widget _buildTodayCheckIns(BuildContext context, List<CheckIn> checkIns) {
    if (checkIns.isEmpty) {
      return EmptyStateWidget(
        icon: Icons.event_available,
        title: 'No Check-Ins Today',
        message: 'All check-ins for today are complete',
      );
    }
    
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: checkIns.length,
      itemBuilder: (context, index) {
        final checkIn = checkIns[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: Colors.blue.shade50,
              child: Text(
                checkIn.guestName.isNotEmpty ? checkIn.guestName[0].toUpperCase() : 'G',
                style: TextStyle(
                  color: Colors.blue.shade700,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            title: Text(checkIn.guestName),
            subtitle: Text('Room ${checkIn.roomNumber} - Expected: ${checkIn.expectedTime.toString().split(' ')[1].substring(0, 5)}'),
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: checkIn.status == 'PENDING' ? Colors.orange.shade50 : Colors.green.shade50,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                checkIn.status,
                style: TextStyle(
                  color: checkIn.status == 'PENDING' ? Colors.orange.shade700 : Colors.green.shade700,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
              ),
            ),
            onTap: () {
              // Navigate to check-in details
            },
          ),
        );
      },
    );
  }
}
