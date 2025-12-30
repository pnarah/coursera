import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Dialog shown when session is about to expire
class SessionTimeoutDialog extends StatefulWidget {
  final int secondsRemaining;
  final VoidCallback onExtend;
  final VoidCallback onLogout;

  const SessionTimeoutDialog({
    super.key,
    required this.secondsRemaining,
    required this.onExtend,
    required this.onLogout,
  });

  @override
  State<SessionTimeoutDialog> createState() => _SessionTimeoutDialogState();
}

class _SessionTimeoutDialogState extends State<SessionTimeoutDialog> {
  late int _remainingSeconds;
  bool _isExtending = false;

  @override
  void initState() {
    super.initState();
    _remainingSeconds = widget.secondsRemaining;
    _startCountdown();
  }

  void _startCountdown() {
    Future.delayed(const Duration(seconds: 1), () {
      if (mounted && _remainingSeconds > 0) {
        setState(() {
          _remainingSeconds--;
        });
        _startCountdown();
      } else if (mounted && _remainingSeconds == 0) {
        // Auto logout when time runs out
        widget.onLogout();
        Navigator.of(context).pop();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false, // Prevent dismissal by back button
      child: AlertDialog(
        icon: Icon(
          Icons.access_time,
          size: 48,
          color: Colors.orange.shade700,
        ),
        title: const Text('Session Expiring Soon'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Your session will expire in',
              style: TextStyle(color: Colors.grey.shade700),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.orange.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.orange.shade200),
              ),
              child: Text(
                _formatTime(_remainingSeconds),
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: Colors.orange.shade900,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Would you like to continue your session?',
              style: TextStyle(color: Colors.grey.shade700),
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: _isExtending
                ? null
                : () {
                    widget.onLogout();
                    Navigator.of(context).pop();
                  },
            child: const Text('Logout'),
          ),
          ElevatedButton(
            onPressed: _isExtending
                ? null
                : () async {
                    setState(() => _isExtending = true);
                    widget.onExtend();
                    Navigator.of(context).pop();
                  },
            child: _isExtending
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Continue Session'),
          ),
        ],
      ),
    );
  }

  String _formatTime(int seconds) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }
}

/// Shows session timeout dialog
Future<void> showSessionTimeoutDialog({
  required BuildContext context,
  int secondsRemaining = 60,
  required VoidCallback onExtend,
  required VoidCallback onLogout,
}) {
  return showDialog(
    context: context,
    barrierDismissible: false,
    builder: (context) => SessionTimeoutDialog(
      secondsRemaining: secondsRemaining,
      onExtend: onExtend,
      onLogout: onLogout,
    ),
  );
}

/// Auto-logout overlay shown when session expired
class SessionExpiredOverlay extends StatelessWidget {
  final VoidCallback onLoginAgain;

  const SessionExpiredOverlay({
    super.key,
    required this.onLoginAgain,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.black54,
      child: Center(
        child: Card(
          margin: const EdgeInsets.all(32),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.timer_off,
                  size: 64,
                  color: Colors.red.shade400,
                ),
                const SizedBox(height: 16),
                const Text(
                  'Session Expired',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Your session has expired due to inactivity.\nPlease login again to continue.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey.shade700),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: onLoginAgain,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: const Text('Login Again'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Show session expired overlay
void showSessionExpiredOverlay(BuildContext context) {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (context) => SessionExpiredOverlay(
      onLoginAgain: () {
        Navigator.of(context).pop();
        context.go('/login');
      },
    ),
  );
}
