import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/services/api_service.dart';
import '../hotels/hotel_search_screen.dart';

class BookingConfirmationScreen extends ConsumerStatefulWidget {
  final String bookingId;

  const BookingConfirmationScreen({
    super.key,
    required this.bookingId,
  });

  @override
  ConsumerState<BookingConfirmationScreen> createState() =>
      _BookingConfirmationScreenState();
}

class _BookingConfirmationScreenState
    extends ConsumerState<BookingConfirmationScreen> {
  Map<String, dynamic>? _booking;
  Map<String, dynamic>? _invoice;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadBookingDetails();
  }

  Future<void> _loadBookingDetails() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final bookingResponse = await apiService.getBookingDetails(
        int.parse(widget.bookingId),
      );
      final invoiceResponse = await apiService.getInvoice(
        int.parse(widget.bookingId),
      );

      setState(() {
        _booking = bookingResponse;
        _invoice = invoiceResponse;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load booking details: ${e.toString()}';
      });
    }
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return 'N/A';
    try {
      final date = DateTime.parse(dateStr);
      return '${date.day}/${date.month}/${date.year}';
    } catch (e) {
      return dateStr;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Booking Confirmation'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        automaticallyImplyLeading: false,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
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
                          onPressed: _loadBookingDetails,
                          child: const Text('Retry'),
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
                      // Success Icon
                      Center(
                        child: Column(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(20),
                              decoration: BoxDecoration(
                                color: Colors.green[50],
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                Icons.check_circle,
                                size: 64,
                                color: Colors.green[600],
                              ),
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'Booking Confirmed!',
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Booking Reference: ${_booking?['reference'] ?? widget.bookingId}',
                              style: TextStyle(
                                fontSize: 16,
                                color: Colors.grey[600],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 32),

                      // Booking Details
                      const Text(
                        'Booking Details',
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
                              _DetailRow(
                                icon: Icons.hotel,
                                label: 'Hotel',
                                value: _booking?['hotel_name'] ?? 'N/A',
                              ),
                              const Divider(),
                              _DetailRow(
                                icon: Icons.bed,
                                label: 'Room Type',
                                value: _booking?['room_type'] ?? 'N/A',
                              ),
                              const Divider(),
                              _DetailRow(
                                icon: Icons.calendar_today,
                                label: 'Check-in',
                                value: _formatDate(_booking?['check_in']),
                              ),
                              const Divider(),
                              _DetailRow(
                                icon: Icons.calendar_today,
                                label: 'Check-out',
                                value: _formatDate(_booking?['check_out']),
                              ),
                              const Divider(),
                              _DetailRow(
                                icon: Icons.people,
                                label: 'Guests',
                                value: '${_booking?['guests'] ?? 0}',
                              ),
                              const Divider(),
                              _DetailRow(
                                icon: Icons.info_outline,
                                label: 'Status',
                                value: _booking?['status'] ?? 'N/A',
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),

                      // Invoice Summary
                      if (_invoice != null) ...[
                        const Text(
                          'Invoice Summary',
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
                              children: [
                                _PriceRow(
                                  label: 'Room Charges',
                                  amount: _invoice!['room_charges'] ?? 0,
                                ),
                                _PriceRow(
                                  label: 'Service Charges',
                                  amount: _invoice!['service_charges'] ?? 0,
                                ),
                                _PriceRow(
                                  label: 'Tax',
                                  amount: _invoice!['tax'] ?? 0,
                                ),
                                const Divider(thickness: 2),
                                _PriceRow(
                                  label: 'Total Amount',
                                  amount: _invoice!['total_amount'] ?? 0,
                                  isBold: true,
                                ),
                                const Divider(),
                                _PriceRow(
                                  label: 'Paid',
                                  amount: _invoice!['paid_amount'] ?? 0,
                                  color: Colors.green,
                                ),
                                _PriceRow(
                                  label: 'Balance',
                                  amount: _invoice!['balance'] ?? 0,
                                  color: Colors.orange,
                                  isBold: true,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 32),

                      // Action Buttons
                      Column(
                        children: [
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: () {
                                context.push('/invoice/${widget.bookingId}');
                              },
                              icon: const Icon(Icons.receipt_long),
                              label: const Text('View Running Bill'),
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.all(16),
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: () {
                                context.push('/services/${widget.bookingId}');
                              },
                              icon: const Icon(Icons.room_service),
                              label: const Text('Order Services'),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.all(16),
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: TextButton(
                              onPressed: () {
                                context.go('/home');
                              },
                              child: const Text('Back to Home'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PriceRow extends StatelessWidget {
  final String label;
  final num amount;
  final bool isBold;
  final Color? color;

  const _PriceRow({
    required this.label,
    required this.amount,
    this.isBold = false,
    this.color,
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
              color: color,
            ),
          ),
          Text(
            '\$${amount.toStringAsFixed(2)}',
            style: TextStyle(
              fontSize: isBold ? 16 : 14,
              fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
