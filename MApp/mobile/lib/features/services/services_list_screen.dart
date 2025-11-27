import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/services/api_service.dart';
import '../hotels/hotel_search_screen.dart';

class ServicesListScreen extends ConsumerStatefulWidget {
  final String bookingId;

  const ServicesListScreen({
    super.key,
    required this.bookingId,
  });

  @override
  ConsumerState<ServicesListScreen> createState() => _ServicesListScreenState();
}

class _ServicesListScreenState extends ConsumerState<ServicesListScreen> {
  List<dynamic> _availableServices = [];
  List<dynamic> _orderedServices = [];
  bool _isLoadingServices = true;
  bool _isLoadingOrders = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadServices();
    _loadOrderedServices();
  }

  Future<void> _loadServices() async {
    setState(() {
      _isLoadingServices = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      
      // First get booking to get hotel_id
      final booking = await apiService.getBookingDetails(int.parse(widget.bookingId));
      final hotelId = booking['hotel_id'];
      
      final response = await apiService.getHotelServices(hotelId);

      setState(() {
        _availableServices = response['services'] ?? [];
        _isLoadingServices = false;
      });
    } catch (e) {
      setState(() {
        _isLoadingServices = false;
        _errorMessage = 'Failed to load services: ${e.toString()}';
      });
    }
  }

  Future<void> _loadOrderedServices() async {
    setState(() {
      _isLoadingOrders = true;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.getBookingServices(
        int.parse(widget.bookingId),
      );

      setState(() {
        _orderedServices = response['services'] ?? [];
        _isLoadingOrders = false;
      });
    } catch (e) {
      setState(() {
        _isLoadingOrders = false;
      });
    }
  }

  Future<void> _orderService(int serviceId, String serviceName) async {
    // Show quantity dialog
    final quantity = await _showQuantityDialog(serviceName);
    if (quantity == null || quantity < 1) return;

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.orderService(
        bookingId: int.parse(widget.bookingId),
        serviceId: serviceId,
        quantity: quantity,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$serviceName ordered successfully!'),
          backgroundColor: Colors.green,
        ),
      );

      // Reload ordered services
      _loadOrderedServices();
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to order service: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<int?> _showQuantityDialog(String serviceName) async {
    int quantity = 1;
    
    return showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Order $serviceName'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Select quantity:'),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  onPressed: () {
                    if (quantity > 1) {
                      quantity--;
                      (context as Element).markNeedsBuild();
                    }
                  },
                  icon: const Icon(Icons.remove_circle_outline),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '$quantity',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                IconButton(
                  onPressed: () {
                    if (quantity < 10) {
                      quantity++;
                      (context as Element).markNeedsBuild();
                    }
                  },
                  icon: const Icon(Icons.add_circle_outline),
                ),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, quantity),
            child: const Text('Order'),
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status.toUpperCase()) {
      case 'PENDING':
        return Colors.orange;
      case 'CONFIRMED':
        return Colors.blue;
      case 'IN_PROGRESS':
        return Colors.purple;
      case 'COMPLETED':
        return Colors.green;
      case 'CANCELLED':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Services'),
          backgroundColor: Theme.of(context).colorScheme.inversePrimary,
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Available', icon: Icon(Icons.shopping_cart)),
              Tab(text: 'My Orders', icon: Icon(Icons.receipt)),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            // Available Services Tab
            _buildAvailableServices(),
            
            // Ordered Services Tab
            _buildOrderedServices(),
          ],
        ),
      ),
    );
  }

  Widget _buildAvailableServices() {
    if (_isLoadingServices) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
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
                onPressed: _loadServices,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_availableServices.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.room_service_outlined, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No services available',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
          ],
        ),
      );
    }

    // Group services by category
    final Map<String, List<dynamic>> servicesByCategory = {};
    for (var service in _availableServices) {
      final category = service['category'] ?? 'Other';
      if (!servicesByCategory.containsKey(category)) {
        servicesByCategory[category] = [];
      }
      servicesByCategory[category]!.add(service);
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: servicesByCategory.length,
      itemBuilder: (context, index) {
        final category = servicesByCategory.keys.elementAt(index);
        final services = servicesByCategory[category]!;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(
                category,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            ...services.map((service) => _ServiceCard(
                  service: service,
                  onOrder: () => _orderService(
                    service['id'],
                    service['name'],
                  ),
                )),
            const SizedBox(height: 16),
          ],
        );
      },
    );
  }

  Widget _buildOrderedServices() {
    if (_isLoadingOrders) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_orderedServices.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.receipt_outlined, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text(
              'No orders yet',
              style: TextStyle(fontSize: 18, color: Colors.grey),
            ),
            SizedBox(height: 8),
            Text(
              'Order services from the Available tab',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadOrderedServices,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _orderedServices.length,
        itemBuilder: (context, index) {
          final order = _orderedServices[index];
          return _OrderCard(
            order: order,
            statusColor: _getStatusColor(order['status'] ?? ''),
          );
        },
      ),
    );
  }
}

class _ServiceCard extends StatelessWidget {
  final Map<String, dynamic> service;
  final VoidCallback onOrder;

  const _ServiceCard({
    required this.service,
    required this.onOrder,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                Icons.room_service,
                color: Theme.of(context).colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    service['name'] ?? 'Unknown Service',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (service['description'] != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      service['description'],
                      style: const TextStyle(
                        fontSize: 12,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                  const SizedBox(height: 4),
                  Text(
                    '\$${service['price']}',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: onOrder,
              icon: const Icon(Icons.add_shopping_cart),
              color: Theme.of(context).colorScheme.primary,
            ),
          ],
        ),
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  final Map<String, dynamic> order;
  final Color statusColor;

  const _OrderCard({
    required this.order,
    required this.statusColor,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    order['service_name'] ?? 'Unknown Service',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    order['status'] ?? 'PENDING',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: statusColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Quantity: ${order['quantity'] ?? 1}',
                  style: const TextStyle(color: Colors.grey),
                ),
                Text(
                  '\$${order['price'] ?? 0}',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            if (order['special_instructions'] != null) ...[
              const SizedBox(height: 8),
              Text(
                'Instructions: ${order['special_instructions']}',
                style: const TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: Colors.grey,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
