import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/widgets/app_drawer.dart';
import '../../../shared/widgets/common_widgets.dart';
import '../../../core/providers/dashboard_providers.dart';
import '../../../core/models/models.dart';

class AdminDashboardScreen extends ConsumerWidget {
  const AdminDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(currentUserProvider);
    final platformMetrics = ref.watch(platformMetricsProvider);
    final allVendors = ref.watch(allVendorsProvider);
    final pendingRequests = ref.watch(pendingVendorRequestsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('System Admin Dashboard'),
      ),
      drawer: currentUser.when(
        loading: () => null,
        error: (_, __) => null,
        data: (user) => AppDrawer(
          userRole: user?.role ?? '',
          userName: user?.fullName ?? 'Admin',
          userMobile: user?.mobileNumber ?? '',
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(currentUserProvider);
          ref.invalidate(platformMetricsProvider);
          ref.invalidate(allVendorsProvider);
          ref.invalidate(pendingVendorRequestsProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Platform Overview
              _buildSectionTitle(context, 'Platform Overview'),
              const SizedBox(height: 12),
              platformMetrics.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: 'Failed to load platform metrics',
                  onRetry: () => ref.invalidate(platformMetricsProvider),
                ),
                data: (metrics) => GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 1.2,
                  children: [
                    MetricCard(
                      title: 'Total Users',
                      value: metrics.totalUsers.toString(),
                      icon: Icons.people,
                      color: Colors.blue,
                    ),
                    MetricCard(
                      title: 'Vendors',
                      value: metrics.totalVendors.toString(),
                      icon: Icons.business,
                      color: Colors.green,
                      onTap: () => context.push('/admin/vendors'),
                    ),
                    MetricCard(
                      title: 'Hotels',
                      value: metrics.totalHotels.toString(),
                      icon: Icons.hotel,
                      color: Colors.orange,
                    ),
                    MetricCard(
                      title: 'Active Subs',
                      value: metrics.activeSubscriptions.toString(),
                      icon: Icons.check_circle,
                      color: Colors.teal,
                    ),
                    MetricCard(
                      title: 'Expired Subs',
                      value: metrics.expiredSubscriptions.toString(),
                      icon: Icons.warning,
                      color: Colors.red,
                    ),
                    MetricCard(
                      title: 'New Users',
                      value: metrics.newUsersThisWeek.toString(),
                      icon: Icons.person_add,
                      color: Colors.purple,
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Pending Actions
              _buildSectionTitle(context, 'Pending Actions'),
              const SizedBox(height: 12),
              pendingRequests.when(
                loading: () => const AppLoadingIndicator(),
                error: (error, stack) => AppErrorWidget(
                  message: 'Failed to load pending requests',
                  onRetry: () => ref.invalidate(pendingVendorRequestsProvider),
                ),
                data: (requests) => Card(
                  child: Column(
                    children: [
                      ListTile(
                        leading: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            shape: BoxShape.circle,
                          ),
                          child: Icon(Icons.pending, color: Colors.red.shade700),
                        ),
                        title: const Text('Vendor Approval Requests'),
                        subtitle: Text('${requests.length} pending requests'),
                        trailing: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.red.shade100,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            requests.length.toString(),
                            style: TextStyle(
                              color: Colors.red.shade700,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        onTap: () => context.push('/admin/approvals'),
                      ),
                      const Divider(height: 1),
                      platformMetrics.when(
                        loading: () => const SizedBox.shrink(),
                        error: (_, __) => const SizedBox.shrink(),
                        data: (metrics) => ListTile(
                          leading: Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.orange.shade50,
                              shape: BoxShape.circle,
                            ),
                            child: Icon(Icons.warning_amber, color: Colors.orange.shade700),
                          ),
                          title: const Text('Expired Subscriptions'),
                          subtitle: Text('${metrics.expiredSubscriptions} subscriptions expired'),
                          trailing: Icon(Icons.chevron_right, color: Colors.grey.shade400),
                          onTap: () => context.push('/admin/subscriptions'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Recent Activity
              _buildSectionTitle(context, 'Recent Activity'),
              const SizedBox(height: 12),
              platformMetrics.when(
                loading: () => const AppLoadingIndicator(),
                error: (_, __) => const SizedBox.shrink(),
                data: (metrics) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.purple.shade50,
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            Icons.person_add,
                            color: Colors.purple.shade700,
                            size: 32,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'New Users This Week',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '${metrics.newUsersThisWeek} new users joined',
                                style: TextStyle(color: Colors.grey.shade600),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Quick Actions
              _buildSectionTitle(context, 'Quick Actions'),
              const SizedBox(height: 12),
              GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.5,
                children: [
                  _buildQuickAction(
                    context,
                    'Create Vendor',
                    Icons.person_add,
                    Colors.indigo,
                    () => context.push('/admin/create-vendor'),
                  ),
                  _buildQuickAction(
                    context,
                    'Add Employee',
                    Icons.group_add,
                    Colors.cyan,
                    () => context.push('/admin/create-employee'),
                  ),
                  _buildQuickAction(
                    context,
                    'Vendor Management',
                    Icons.business_center,
                    Colors.blue,
                    () => context.push('/admin/vendors'),
                  ),
                  _buildQuickAction(
                    context,
                    'Approvals',
                    Icons.approval,
                    Colors.green,
                    () => context.push('/admin/approvals'),
                  ),
                  _buildQuickAction(
                    context,
                    'Analytics',
                    Icons.analytics,
                    Colors.purple,
                    () => context.push('/admin/analytics'),
                  ),
                  _buildQuickAction(
                    context,
                    'Audit Logs',
                    Icons.history,
                    Colors.orange,
                    () => context.push('/admin/audit-logs'),
                  ),
                ],
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
