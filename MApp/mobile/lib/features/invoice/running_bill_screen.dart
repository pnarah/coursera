import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/services/api_service.dart';
import '../hotels/hotel_search_screen.dart';

class RunningBillScreen extends ConsumerStatefulWidget {
  final String bookingId;

  const RunningBillScreen({
    super.key,
    required this.bookingId,
  });

  @override
  ConsumerState<RunningBillScreen> createState() => _RunningBillScreenState();
}

class _RunningBillScreenState extends ConsumerState<RunningBillScreen> {
  Map<String, dynamic>? _invoice;
  bool _isLoading = true;
  String? _errorMessage;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadInvoice();
    // Auto-refresh every 30 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _loadInvoice(showLoading: false);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadInvoice({bool showLoading = true}) async {
    if (showLoading) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.getInvoice(int.parse(widget.bookingId));

      if (mounted) {
        setState(() {
          _invoice = response;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'Failed to load invoice: ${e.toString()}';
        });
      }
    }
  }

  Future<void> _initiatePayment() async {
    if (_invoice == null) return;

    final balance = (_invoice!['balance'] ?? 0) as num;
    if (balance <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No balance to pay'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    // Show confirmation dialog
    final confirmed = await _showPaymentDialog(balance);
    if (confirmed != true) return;

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.createPayment(
        bookingId: int.parse(widget.bookingId),
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Payment initiated: ${response['payment_id']}'),
          backgroundColor: Colors.green,
        ),
      );

      // Reload invoice to show updated payment status
      _loadInvoice();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to initiate payment: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<bool?> _showPaymentDialog(num amount) async {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm Payment'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('You are about to pay:'),
            const SizedBox(height: 16),
            Center(
              child: Text(
                '\$${amount.toStringAsFixed(2)}',
                style: const TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: Colors.green,
                ),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'This will process the full balance amount.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm Payment'),
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status.toUpperCase()) {
      case 'PENDING':
        return Colors.orange;
      case 'PAID':
        return Colors.green;
      case 'PARTIALLY_PAID':
        return Colors.blue;
      case 'CANCELLED':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Running Bill'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            onPressed: () => _loadInvoice(),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ],
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
                          onPressed: () => _loadInvoice(),
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: () => _loadInvoice(),
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Invoice Header
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    const Text(
                                      'Invoice',
                                      style: TextStyle(
                                        fontSize: 24,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 12,
                                        vertical: 6,
                                      ),
                                      decoration: BoxDecoration(
                                        color: _getStatusColor(
                                          _invoice?['status'] ?? '',
                                        ).withOpacity(0.2),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: Text(
                                        _invoice?['status'] ?? 'PENDING',
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: _getStatusColor(
                                            _invoice?['status'] ?? '',
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Invoice #${_invoice?['id'] ?? widget.bookingId}',
                                  style: const TextStyle(color: Colors.grey),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Line Items
                        const Text(
                          'Charges',
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
                                // Room Charges
                                _LineItem(
                                  description: 'Room Charges',
                                  amount: _invoice?['room_charges'] ?? 0,
                                ),
                                const Divider(),

                                // Service Charges
                                _LineItem(
                                  description: 'Service Charges',
                                  amount: _invoice?['service_charges'] ?? 0,
                                ),
                                const Divider(),

                                // Subtotal
                                _LineItem(
                                  description: 'Subtotal',
                                  amount: (_invoice?['room_charges'] ?? 0) +
                                      (_invoice?['service_charges'] ?? 0),
                                ),
                                const Divider(),

                                // Tax
                                _LineItem(
                                  description: 'Tax',
                                  amount: _invoice?['tax'] ?? 0,
                                ),
                                const Divider(thickness: 2),

                                // Total
                                _LineItem(
                                  description: 'Total Amount',
                                  amount: _invoice?['total_amount'] ?? 0,
                                  isBold: true,
                                  fontSize: 18,
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Payment Summary
                        const Text(
                          'Payment Summary',
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
                                _LineItem(
                                  description: 'Paid Amount',
                                  amount: _invoice?['paid_amount'] ?? 0,
                                  color: Colors.green,
                                ),
                                const Divider(),
                                _LineItem(
                                  description: 'Balance Due',
                                  amount: _invoice?['balance'] ?? 0,
                                  color: Colors.orange,
                                  isBold: true,
                                  fontSize: 18,
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 32),

                        // Payment Button
                        if ((_invoice?['balance'] ?? 0) > 0)
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: _initiatePayment,
                              icon: const Icon(Icons.payment),
                              label: const Text(
                                'Pay Now',
                                style: TextStyle(fontSize: 16),
                              ),
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.all(16),
                                backgroundColor: Colors.green,
                                foregroundColor: Colors.white,
                              ),
                            ),
                          ),

                        const SizedBox(height: 16),

                        // Auto-refresh indicator
                        Center(
                          child: Text(
                            'Auto-refreshes every 30 seconds',
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.grey[600],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
    );
  }
}

class _LineItem extends StatelessWidget {
  final String description;
  final num amount;
  final bool isBold;
  final double fontSize;
  final Color? color;

  const _LineItem({
    required this.description,
    required this.amount,
    this.isBold = false,
    this.fontSize = 16,
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
            description,
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
              color: color,
            ),
          ),
          Text(
            '\$${amount.toStringAsFixed(2)}',
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
