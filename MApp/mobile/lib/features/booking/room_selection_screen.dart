import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/services/api_service.dart';
import '../hotels/hotel_search_screen.dart';

class RoomSelectionScreen extends ConsumerStatefulWidget {
  const RoomSelectionScreen({super.key});

  @override
  ConsumerState<RoomSelectionScreen> createState() => _RoomSelectionScreenState();
}

class _RoomSelectionScreenState extends ConsumerState<RoomSelectionScreen> {
  String? _lockId;
  DateTime? _lockExpiry;
  Timer? _countdownTimer;
  Duration _remainingTime = Duration.zero;
  bool _isLocking = false;
  bool _lockExpired = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _lockAvailability();
    });
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  Future<void> _lockAvailability() async {
    final extras = GoRouterState.of(context).extra as Map<String, dynamic>?;
    if (extras == null) {
      setState(() {
        _errorMessage = 'Missing booking information';
      });
      return;
    }

    final hotelId = extras['hotelId'] as int;
    final roomType = extras['roomType'] as String;
    final checkIn = extras['checkIn'] as DateTime;
    final checkOut = extras['checkOut'] as DateTime;
    final quantity = 1; // Always lock 1 room for now

    setState(() {
      _isLocking = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.lockAvailability(
        hotelId: hotelId,
        roomType: roomType,
        checkInDate: checkIn,
        checkOutDate: checkOut,
        quantity: quantity,
      );

      final lockId = response['lock_id'];
      final expiryStr = response['expires_at'];
      final expiry = DateTime.parse(expiryStr);

      setState(() {
        _lockId = lockId;
        _lockExpiry = expiry;
        _isLocking = false;
      });

      _startCountdown();
    } catch (e) {
      setState(() {
        _isLocking = false;
        _errorMessage = 'Failed to lock availability: ${e.toString()}';
      });
    }
  }

  void _startCountdown() {
    if (_lockExpiry == null) return;

    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      final now = DateTime.now();
      final remaining = _lockExpiry!.difference(now);

      if (remaining.isNegative) {
        setState(() {
          _lockExpired = true;
          _remainingTime = Duration.zero;
        });
        timer.cancel();
      } else {
        setState(() {
          _remainingTime = remaining;
        });
      }
    });
  }

  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes;
    final seconds = duration.inSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final extras = GoRouterState.of(context).extra as Map<String, dynamic>?;
    final roomType = extras?['roomType'] as String? ?? 'Unknown';
    final checkIn = extras?['checkIn'] as DateTime?;
    final checkOut = extras?['checkOut'] as DateTime?;
    final guests = extras?['guests'] as int? ?? 1;
    final pricePerNight = extras?['pricePerNight'] as num? ?? 0;

    final nights = checkIn != null && checkOut != null
        ? checkOut.difference(checkIn).inDays
        : 0;
    final totalPrice = nights * pricePerNight;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Confirm Selection'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLocking
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Locking availability...'),
                ],
              ),
            )
          : _errorMessage != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 64, color: Colors.red),
                        const SizedBox(height: 16),
                        Text(
                          _errorMessage!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.red),
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton(
                          onPressed: () => context.pop(),
                          child: const Text('Go Back'),
                        ),
                      ],
                    ),
                  ),
                )
              : _lockExpired
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.timer_off, size: 64, color: Colors.orange),
                            const SizedBox(height: 16),
                            const Text(
                              'Lock Expired',
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Your room lock has expired. Please try again.',
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 24),
                            ElevatedButton(
                              onPressed: _lockAvailability,
                              child: const Text('Try Again'),
                            ),
                            const SizedBox(height: 12),
                            TextButton(
                              onPressed: () => context.pop(),
                              child: const Text('Go Back'),
                            ),
                          ],
                        ),
                      ),
                    )
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Timer Card
                          Card(
                            color: _remainingTime.inSeconds < 30
                                ? Colors.red[50]
                                : Colors.green[50],
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                children: [
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(
                                        Icons.timer,
                                        size: 32,
                                        color: _remainingTime.inSeconds < 30
                                            ? Colors.red
                                            : Colors.green,
                                      ),
                                      const SizedBox(width: 8),
                                      Text(
                                        _formatDuration(_remainingTime),
                                        style: TextStyle(
                                          fontSize: 32,
                                          fontWeight: FontWeight.bold,
                                          color: _remainingTime.inSeconds < 30
                                              ? Colors.red
                                              : Colors.green,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'Time remaining to complete booking',
                                    style: TextStyle(
                                      color: Colors.grey[700],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // Booking Summary
                          const Text(
                            'Booking Summary',
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 16),

                          Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  _SummaryRow(
                                    label: 'Room Type',
                                    value: roomType,
                                  ),
                                  const Divider(),
                                  _SummaryRow(
                                    label: 'Check-in',
                                    value: checkIn != null
                                        ? '${checkIn.day}/${checkIn.month}/${checkIn.year}'
                                        : 'N/A',
                                  ),
                                  const Divider(),
                                  _SummaryRow(
                                    label: 'Check-out',
                                    value: checkOut != null
                                        ? '${checkOut.day}/${checkOut.month}/${checkOut.year}'
                                        : 'N/A',
                                  ),
                                  const Divider(),
                                  _SummaryRow(
                                    label: 'Nights',
                                    value: '$nights',
                                  ),
                                  const Divider(),
                                  _SummaryRow(
                                    label: 'Guests',
                                    value: '$guests',
                                  ),
                                  const Divider(),
                                  _SummaryRow(
                                    label: 'Price per night',
                                    value: '\$$pricePerNight',
                                  ),
                                  const Divider(),
                                  _SummaryRow(
                                    label: 'Total',
                                    value: '\$$totalPrice',
                                    isBold: true,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // Lock ID (for debugging)
                          if (_lockId != null)
                            Text(
                              'Lock ID: $_lockId',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey[600],
                              ),
                            ),
                          const SizedBox(height: 24),

                          // Continue Button
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _lockExpired
                                  ? null
                                  : () {
                                      if (_lockId != null) {
                                        context.push(
                                          '/booking/guest-details',
                                          extra: {
                                            'lockId': _lockId,
                                            ...extras!,
                                          },
                                        );
                                      }
                                    },
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.all(16),
                              ),
                              child: const Text(
                                'Continue to Guest Details',
                                style: TextStyle(fontSize: 16),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final bool isBold;

  const _SummaryRow({
    required this.label,
    required this.value,
    this.isBold = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: isBold ? 16 : 14,
              fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: isBold ? 16 : 14,
              fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ],
      ),
    );
  }
}
