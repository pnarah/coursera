import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/providers/storage_provider.dart';
import '../../core/services/api_service.dart';
import '../../core/services/secure_storage_service.dart';

class AppDrawer extends ConsumerWidget {
  final String userRole;
  final String userName;
  final String userMobile;

  const AppDrawer({
    super.key,
    required this.userRole,
    required this.userName,
    required this.userMobile,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          UserAccountsDrawerHeader(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Theme.of(context).colorScheme.primary,
                  Theme.of(context).colorScheme.secondary,
                ],
              ),
            ),
            accountName: Text(userName),
            accountEmail: Text(userMobile),
            currentAccountPicture: CircleAvatar(
              backgroundColor: Colors.white,
              child: Text(
                userName.isNotEmpty ? userName[0].toUpperCase() : 'U',
                style: TextStyle(
                  fontSize: 32,
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          
          // Common items
          ListTile(
            leading: const Icon(Icons.dashboard),
            title: const Text('Dashboard'),
            onTap: () {
              Navigator.pop(context);
              context.go('/dashboard');
            },
          ),
          ListTile(
            leading: const Icon(Icons.person),
            title: const Text('Profile'),
            onTap: () {
              Navigator.pop(context);
              context.push('/profile');
            },
          ),
          ListTile(
            leading: const Icon(Icons.notifications),
            title: const Text('Notifications'),
            onTap: () {
              Navigator.pop(context);
              context.push('/notifications');
            },
          ),
          
          const Divider(),
          
          // Role-specific items
          ..._buildRoleSpecificItems(context, userRole),
          
          const Divider(),
          
          // Settings & Security
          ListTile(
            leading: const Icon(Icons.devices),
            title: const Text('Active Sessions'),
            onTap: () {
              Navigator.pop(context);
              context.push('/sessions');
            },
          ),
          ListTile(
            leading: const Icon(Icons.settings),
            title: const Text('Settings'),
            onTap: () {
              Navigator.pop(context);
              context.push('/settings');
            },
          ),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('Logout', style: TextStyle(color: Colors.red)),
            onTap: () => _handleLogout(context, ref),
          ),
        ],
      ),
    );
  }
  
  Future<void> _handleLogout(BuildContext context, WidgetRef ref) async {
    Navigator.pop(context); // Close drawer first

    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Logout'),
          ),
        ],
      ),
    );

    if (confirmed != true || !context.mounted) return;

    // Show loading indicator
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: CircularProgressIndicator(),
      ),
    );

    try {
      // Call logout API
      final apiService = ref.read(apiServiceProvider);
      await apiService.logout();

      // Clear local storage
      final storage = ref.read(secureStorageServiceProvider);
      await storage.deleteToken();
      await storage.deleteRefreshToken();

      if (!context.mounted) return;
      
      // Dismiss loading
      Navigator.pop(context);

      // Navigate to login
      context.go('/login');

      // Show success message
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Logged out successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!context.mounted) return;
      
      // Dismiss loading
      Navigator.pop(context);

      // Even if API call fails, clear local storage and logout
      try {
        final storage = ref.read(secureStorageServiceProvider);
        await storage.deleteToken();
        await storage.deleteRefreshToken();
        
        if (!context.mounted) return;
        context.go('/login');
      } catch (_) {
        // If everything fails, show error
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Logout failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  List<Widget> _buildRoleSpecificItems(BuildContext context, String role) {
    switch (role.toUpperCase()) {
      case 'GUEST':
        return [
          ListTile(
            leading: const Icon(Icons.search),
            title: const Text('Search Hotels'),
            onTap: () {
              Navigator.pop(context);
              context.push('/hotels/search');
            },
          ),
          ListTile(
            leading: const Icon(Icons.history),
            title: const Text('My Bookings'),
            onTap: () {
              Navigator.pop(context);
              context.push('/bookings/history');
            },
          ),
          ListTile(
            leading: const Icon(Icons.receipt),
            title: const Text('Running Bill'),
            onTap: () {
              Navigator.pop(context);
              context.push('/invoice/running-bill');
            },
          ),
        ];
      
      case 'HOTEL_EMPLOYEE':
        return [
          ListTile(
            leading: const Icon(Icons.how_to_reg),
            title: const Text('Check-In'),
            onTap: () {
              Navigator.pop(context);
              context.push('/employee/checkin');
            },
          ),
          ListTile(
            leading: const Icon(Icons.meeting_room),
            title: const Text('Room Status'),
            onTap: () {
              Navigator.pop(context);
              context.push('/employee/room-status');
            },
          ),
          ListTile(
            leading: const Icon(Icons.room_service),
            title: const Text('Service Requests'),
            onTap: () {
              Navigator.pop(context);
              context.push('/employee/service-requests');
            },
          ),
        ];
      
      case 'VENDOR_ADMIN':
        return [
          ListTile(
            leading: const Icon(Icons.hotel),
            title: const Text('My Hotels'),
            onTap: () {
              Navigator.pop(context);
              context.push('/vendor/hotels');
            },
          ),
          ListTile(
            leading: const Icon(Icons.people),
            title: const Text('Employees'),
            onTap: () {
              Navigator.pop(context);
              context.push('/vendor/employees');
            },
          ),
          ListTile(
            leading: const Icon(Icons.card_membership),
            title: const Text('Subscription'),
            onTap: () {
              Navigator.pop(context);
              context.push('/vendor/subscription');
            },
          ),
          ListTile(
            leading: const Icon(Icons.analytics),
            title: const Text('Analytics'),
            onTap: () {
              Navigator.pop(context);
              context.push('/vendor/analytics');
            },
          ),
        ];
      
      case 'SYSTEM_ADMIN':
        return [
          ListTile(
            leading: const Icon(Icons.admin_panel_settings),
            title: const Text('Admin Panel'),
            onTap: () {
              Navigator.pop(context);
              context.push('/admin/dashboard');
            },
          ),
          ListTile(
            leading: const Icon(Icons.business),
            title: const Text('Vendors'),
            onTap: () {
              Navigator.pop(context);
              context.push('/admin/vendors');
            },
          ),
          ListTile(
            leading: const Icon(Icons.pending_actions),
            title: const Text('Approvals'),
            onTap: () {
              Navigator.pop(context);
              context.push('/admin/approvals');
            },
          ),
          ListTile(
            leading: const Icon(Icons.analytics),
            title: const Text('Platform Analytics'),
            onTap: () {
              Navigator.pop(context);
              context.push('/admin/analytics');
            },
          ),
        ];
      
      default:
        return [];
    }
  }
}
