import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/services/api_service.dart';

class HotelSearchScreen extends ConsumerStatefulWidget {
  const HotelSearchScreen({super.key});

  @override
  ConsumerState<HotelSearchScreen> createState() => _HotelSearchScreenState();
}

class _HotelSearchScreenState extends ConsumerState<HotelSearchScreen> {
  final _formKey = GlobalKey<FormState>();
  final _cityController = TextEditingController();
  DateTime? _checkInDate;
  DateTime? _checkOutDate;
  int _guests = 1;
  String? _roomType;
  
  List<dynamic> _searchResults = [];
  bool _isLoading = false;
  String? _errorMessage;

  final List<String> _roomTypes = [
    'SINGLE',
    'DOUBLE',
    'DELUXE',
    'SUITE',
    'FAMILY',
  ];

  @override
  void dispose() {
    _cityController.dispose();
    super.dispose();
  }

  Future<void> _selectDate(BuildContext context, bool isCheckIn) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: isCheckIn 
          ? (_checkInDate ?? DateTime.now())
          : (_checkOutDate ?? DateTime.now().add(const Duration(days: 1))),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    
    if (picked != null) {
      setState(() {
        if (isCheckIn) {
          _checkInDate = picked;
          // Reset checkout if it's before new checkin
          if (_checkOutDate != null && _checkOutDate!.isBefore(_checkInDate!)) {
            _checkOutDate = null;
          }
        } else {
          _checkOutDate = picked;
        }
      });
    }
  }

  Future<void> _searchHotels() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_checkInDate == null || _checkOutDate == null) {
      setState(() {
        _errorMessage = 'Please select check-in and check-out dates';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final response = await apiService.searchHotels(
        city: _cityController.text.trim(),
        checkIn: _checkInDate,
        checkOut: _checkOutDate,
        guests: _guests,
        roomType: _roomType,
      );

      setState(() {
        _searchResults = response['hotels'] ?? [];
        _isLoading = false;
      });

      if (_searchResults.isEmpty) {
        setState(() {
          _errorMessage = 'No hotels found matching your criteria';
        });
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to search hotels: ${e.toString()}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Search Hotels'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Column(
        children: [
          // Search Form
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.grey[100],
            child: Form(
              key: _formKey,
              child: Column(
                children: [
                  // City Input
                  TextFormField(
                    controller: _cityController,
                    decoration: const InputDecoration(
                      labelText: 'City',
                      hintText: 'e.g., New York, San Francisco',
                      prefixIcon: Icon(Icons.location_city),
                      border: OutlineInputBorder(),
                      filled: true,
                      fillColor: Colors.white,
                    ),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter a city';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 12),

                  // Dates Row
                  Row(
                    children: [
                      Expanded(
                        child: InkWell(
                          onTap: () => _selectDate(context, true),
                          child: InputDecorator(
                            decoration: const InputDecoration(
                              labelText: 'Check-in',
                              prefixIcon: Icon(Icons.calendar_today),
                              border: OutlineInputBorder(),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                            child: Text(
                              _checkInDate == null
                                  ? 'Select date'
                                  : '${_checkInDate!.day}/${_checkInDate!.month}/${_checkInDate!.year}',
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: InkWell(
                          onTap: () => _selectDate(context, false),
                          child: InputDecorator(
                            decoration: const InputDecoration(
                              labelText: 'Check-out',
                              prefixIcon: Icon(Icons.calendar_today),
                              border: OutlineInputBorder(),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                            child: Text(
                              _checkOutDate == null
                                  ? 'Select date'
                                  : '${_checkOutDate!.day}/${_checkOutDate!.month}/${_checkOutDate!.year}',
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Guests and Room Type Row
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<int>(
                          value: _guests,
                          decoration: const InputDecoration(
                            labelText: 'Guests',
                            prefixIcon: Icon(Icons.people),
                            border: OutlineInputBorder(),
                            filled: true,
                            fillColor: Colors.white,
                          ),
                          items: List.generate(10, (index) => index + 1)
                              .map((count) => DropdownMenuItem(
                                    value: count,
                                    child: Text('$count'),
                                  ))
                              .toList(),
                          onChanged: (value) {
                            setState(() {
                              _guests = value!;
                            });
                          },
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _roomType,
                          decoration: const InputDecoration(
                            labelText: 'Room Type',
                            prefixIcon: Icon(Icons.bed),
                            border: OutlineInputBorder(),
                            filled: true,
                            fillColor: Colors.white,
                          ),
                          hint: const Text('Any'),
                          items: _roomTypes
                              .map((type) => DropdownMenuItem(
                                    value: type,
                                    child: Text(type),
                                  ))
                              .toList(),
                          onChanged: (value) {
                            setState(() {
                              _roomType = value;
                            });
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Search Button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _searchHotels,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.all(16),
                      ),
                      child: _isLoading
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text(
                              'Search Hotels',
                              style: TextStyle(fontSize: 16),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Error Message
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(16),
              color: Colors.red[50],
              child: Row(
                children: [
                  const Icon(Icons.error_outline, color: Colors.red),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                ],
              ),
            ),

          // Search Results
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _searchResults.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.search, size: 64, color: Colors.grey),
                            SizedBox(height: 16),
                            Text(
                              'Search for hotels',
                              style: TextStyle(
                                fontSize: 18,
                                color: Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _searchResults.length,
                        itemBuilder: (context, index) {
                          final hotel = _searchResults[index];
                          return _HotelCard(
                            hotel: hotel,
                            checkIn: _checkInDate!,
                            checkOut: _checkOutDate!,
                            guests: _guests,
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

class _HotelCard extends StatelessWidget {
  final Map<String, dynamic> hotel;
  final DateTime checkIn;
  final DateTime checkOut;
  final int guests;

  const _HotelCard({
    required this.hotel,
    required this.checkIn,
    required this.checkOut,
    required this.guests,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: InkWell(
        onTap: () {
          context.push(
            '/hotels/${hotel['id']}',
            extra: {
              'hotel': hotel,
              'checkIn': checkIn,
              'checkOut': checkOut,
              'guests': guests,
            },
          );
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Hotel Image Placeholder
            Container(
              height: 200,
              width: double.infinity,
              color: Colors.grey[300],
              child: const Icon(Icons.hotel, size: 64, color: Colors.grey),
            ),

            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Hotel Name
                  Text(
                    hotel['name'] ?? 'Unknown Hotel',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Location
                  Row(
                    children: [
                      const Icon(Icons.location_on, size: 16, color: Colors.grey),
                      const SizedBox(width: 4),
                      Text(
                        '${hotel['city'] ?? ''}, ${hotel['state'] ?? ''}',
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // Rating
                  if (hotel['rating'] != null)
                    Row(
                      children: [
                        const Icon(Icons.star, size: 16, color: Colors.amber),
                        const SizedBox(width: 4),
                        Text(
                          hotel['rating'].toString(),
                          style: const TextStyle(fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                  const SizedBox(height: 12),

                  // View Details Button
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () {
                        context.push(
                          '/hotels/${hotel['id']}',
                          extra: {
                            'hotel': hotel,
                            'checkIn': checkIn,
                            'checkOut': checkOut,
                            'guests': guests,
                          },
                        );
                      },
                      child: const Text('View Details'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Provider for API Service
final apiServiceProvider = Provider<ApiService>((ref) {
  final storage = ref.read(storageServiceProvider);
  return ApiService(storage);
});

final storageServiceProvider = Provider<dynamic>((ref) {
  throw UnimplementedError('Storage service must be provided');
});
