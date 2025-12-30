import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../core/services/api_service.dart';
import '../../shared/widgets/common_widgets.dart';

/// Provider for sessions list
final sessionsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final apiService = ref.read(apiServiceProvider);
  return await apiService.getSessions();
});

class SessionsListScreen extends ConsumerWidget {
  const SessionsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessionsAsync = ref.watch(sessionsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Active Sessions'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(sessionsProvider),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: sessionsAsync.when(
        loading: () => const AppLoadingIndicator(),
        error: (error, stack) => AppErrorWidget(
          message: 'Failed to load sessions',
          onRetry: () => ref.invalidate(sessionsProvider),
        ),
        data: (sessions) {
          if (sessions.isEmpty) {
            return EmptyStateWidget(
              icon: Icons.devices_outlined,
              title: 'No Active Sessions',
              message: 'You don\'t have any active sessions',
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(sessionsProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: sessions.length,
              itemBuilder: (context, index) {
                final session = sessions[index];
                return _SessionCard(
                  session: session,
                  onRevoke: () => _revokeSession(context, ref, session),
                );
              },
            ),
          );
        },
      ),
    );
  }

  Future<void> _revokeSession(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> session,
  ) async {
    final sessionId = session['id']?.toString() ?? session['session_id']?.toString();
    final isCurrent = session['is_current'] == true;

    if (sessionId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invalid session ID')),
      );
      return;
    }

    // Warn if trying to revoke current session
    if (isCurrent) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Revoke Current Session?'),
          content: const Text(
            'This will log you out of this device. Are you sure?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              style: TextButton.styleFrom(foregroundColor: Colors.red),
              child: const Text('Revoke'),
            ),
          ],
        ),
      );

      if (confirmed != true) return;
    }

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.revokeSession(sessionId);

      if (!context.mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Session revoked successfully'),
          backgroundColor: Colors.green,
        ),
      );

      // Refresh the list
      ref.invalidate(sessionsProvider);

      // If current session was revoked, redirect to login
      if (isCurrent) {
        // TODO: Navigate to login and clear local storage
        // context.go('/login');
      }
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to revoke session: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}

class _SessionCard extends StatelessWidget {
  final Map<String, dynamic> session;
  final VoidCallback onRevoke;

  const _SessionCard({
    required this.session,
    required this.onRevoke,
  });

  @override
  Widget build(BuildContext context) {
    final isCurrent = session['is_current'] == true;
    final deviceInfo = session['device_info'] ?? session['user_agent'] ?? 'Unknown device';
    final ipAddress = session['ip_address'] ?? 'Unknown IP';
    final createdAt = session['created_at'] != null
        ? DateTime.parse(session['created_at'].toString())
        : null;
    final lastActivity = session['last_activity'] != null
        ? DateTime.parse(session['last_activity'].toString())
        : null;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: isCurrent ? 4 : 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: isCurrent
            ? BorderSide(color: Theme.of(context).colorScheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isCurrent
                        ? Theme.of(context).colorScheme.primary.withOpacity(0.1)
                        : Colors.grey.shade100,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    _getDeviceIcon(deviceInfo),
                    color: isCurrent
                        ? Theme.of(context).colorScheme.primary
                        : Colors.grey.shade600,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              _getDeviceName(deviceInfo),
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ),
                          if (isCurrent)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.green.shade100,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                'Current',
                                style: TextStyle(
                                  color: Colors.green.shade900,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        ipAddress,
                        style: TextStyle(
                          color: Colors.grey.shade600,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _InfoItem(
                    icon: Icons.access_time,
                    label: 'Created',
                    value: createdAt != null
                        ? _formatDateTime(createdAt)
                        : 'Unknown',
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _InfoItem(
                    icon: Icons.update,
                    label: 'Last Active',
                    value: lastActivity != null
                        ? _formatRelativeTime(lastActivity)
                        : 'Unknown',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: onRevoke,
                icon: const Icon(Icons.block, size: 18),
                label: Text(isCurrent ? 'Logout This Session' : 'Revoke Session'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.red,
                  side: const BorderSide(color: Colors.red),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getDeviceIcon(String deviceInfo) {
    final lower = deviceInfo.toLowerCase();
    if (lower.contains('mobile') || lower.contains('android') || lower.contains('iphone')) {
      return Icons.smartphone;
    } else if (lower.contains('tablet') || lower.contains('ipad')) {
      return Icons.tablet;
    } else if (lower.contains('windows') || lower.contains('mac') || lower.contains('linux')) {
      return Icons.computer;
    }
    return Icons.devices;
  }

  String _getDeviceName(String deviceInfo) {
    final lower = deviceInfo.toLowerCase();
    if (lower.contains('iphone')) return 'iPhone';
    if (lower.contains('ipad')) return 'iPad';
    if (lower.contains('android')) return 'Android Device';
    if (lower.contains('windows')) return 'Windows PC';
    if (lower.contains('mac')) return 'Mac';
    if (lower.contains('linux')) return 'Linux';
    return 'Unknown Device';
  }

  String _formatDateTime(DateTime dateTime) {
    return DateFormat('MMM dd, yyyy HH:mm').format(dateTime);
  }

  String _formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 30) {
      return '${difference.inDays}d ago';
    } else {
      return _formatDateTime(dateTime);
    }
  }
}

class _InfoItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoItem({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey.shade600),
        const SizedBox(width: 6),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey.shade600,
                ),
              ),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
