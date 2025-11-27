import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/services/api_service.dart';
import '../hotels/hotel_search_screen.dart';

class GuestDetailsScreen extends ConsumerStatefulWidget {
  const GuestDetailsScreen({super.key});

  @override
  ConsumerState<GuestDetailsScreen> createState() => _GuestDetailsScreenState();
}

class _GuestDetailsScreenState extends ConsumerState<GuestDetailsScreen> {
  final _formKey = GlobalKey<FormState>();
  final List<GuestFormData> _guests = [GuestFormData(isPrimary: true)];
  bool _isSubmitting = false;
  String? _errorMessage;

  void _addGuest() {
    setState(() {
      _guests.add(GuestFormData(isPrimary: false));
    });
  }

  void _removeGuest(int index) {
    if (_guests[index].isPrimary) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Cannot remove primary guest')),
      );
      return;
    }
    
    setState(() {
      _guests.removeAt(index);
    });
  }

  Future<void> _submitBooking() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    _formKey.currentState!.save();

    final extras = GoRouterState.of(context).extra as Map<String, dynamic>?;
    if (extras == null) {
      setState(() {
        _errorMessage = 'Missing booking information';
      });
      return;
    }

    final lockId = extras['lockId'] as String;
    final hotelId = extras['hotelId'] as int;
    final roomType = extras['roomType'] as String;
    final checkIn = extras['checkIn'] as DateTime;
    final checkOut = extras['checkOut'] as DateTime;
    final guestsCount = extras['guests'] as int;

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      
      // Convert guest data to API format
      final guestList = _guests.map((guest) => {
        'name': guest.name,
        'email': guest.email,
        'phone': guest.phone,
        'is_primary': guest.isPrimary,
      }).toList();

      final response = await apiService.createBooking(
        hotelId: hotelId,
        roomType: roomType,
        checkIn: checkIn,
        checkOut: checkOut,
        guests: guestsCount,
        lockId: lockId,
        guestList: guestList,
      );

      final bookingId = response['id'];

      if (!mounted) return;

      // Navigate to confirmation
      context.go('/booking/confirmation/$bookingId', extra: response);
    } catch (e) {
      setState(() {
        _isSubmitting = false;
        _errorMessage = 'Failed to create booking: ${e.toString()}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Guest Details'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isSubmitting
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Creating your booking...'),
                ],
              ),
            )
          : Form(
              key: _formKey,
              child: Column(
                children: [
                  Expanded(
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _guests.length,
                      itemBuilder: (context, index) {
                        return _GuestForm(
                          key: ValueKey('guest_$index'),
                          guest: _guests[index],
                          guestNumber: index + 1,
                          canRemove: !_guests[index].isPrimary && _guests.length > 1,
                          onRemove: () => _removeGuest(index),
                        );
                      },
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

                  // Bottom Actions
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.1),
                          blurRadius: 4,
                          offset: const Offset(0, -2),
                        ),
                      ],
                    ),
                    child: Column(
                      children: [
                        if (_guests.length < 10)
                          OutlinedButton.icon(
                            onPressed: _addGuest,
                            icon: const Icon(Icons.person_add),
                            label: const Text('Add Another Guest'),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size(double.infinity, 48),
                            ),
                          ),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: _submitBooking,
                          style: ElevatedButton.styleFrom(
                            minimumSize: const Size(double.infinity, 48),
                          ),
                          child: const Text(
                            'Complete Booking',
                            style: TextStyle(fontSize: 16),
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

class GuestFormData {
  String name = '';
  String email = '';
  String phone = '';
  final bool isPrimary;

  GuestFormData({required this.isPrimary});
}

class _GuestForm extends StatelessWidget {
  final GuestFormData guest;
  final int guestNumber;
  final bool canRemove;
  final VoidCallback onRemove;

  const _GuestForm({
    super.key,
    required this.guest,
    required this.guestNumber,
    required this.canRemove,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  guest.isPrimary ? 'Primary Guest' : 'Guest $guestNumber',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (canRemove)
                  IconButton(
                    icon: const Icon(Icons.delete_outline, color: Colors.red),
                    onPressed: onRemove,
                  ),
              ],
            ),
            const SizedBox(height: 16),

            // Name Field
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'Full Name *',
                hintText: 'John Doe',
                prefixIcon: Icon(Icons.person),
                border: OutlineInputBorder(),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Name is required';
                }
                if (value.trim().length < 2) {
                  return 'Name must be at least 2 characters';
                }
                return null;
              },
              onSaved: (value) {
                guest.name = value!.trim();
              },
            ),
            const SizedBox(height: 16),

            // Email Field
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'Email *',
                hintText: 'john@example.com',
                prefixIcon: Icon(Icons.email),
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.emailAddress,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Email is required';
                }
                final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
                if (!emailRegex.hasMatch(value.trim())) {
                  return 'Enter a valid email address';
                }
                return null;
              },
              onSaved: (value) {
                guest.email = value!.trim();
              },
            ),
            const SizedBox(height: 16),

            // Phone Field
            TextFormField(
              decoration: const InputDecoration(
                labelText: 'Phone Number *',
                hintText: '+1 234 567 8900',
                prefixIcon: Icon(Icons.phone),
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.phone,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Phone number is required';
                }
                // Remove spaces and dashes for validation
                final cleaned = value.replaceAll(RegExp(r'[\s\-\(\)]'), '');
                if (cleaned.length < 10) {
                  return 'Enter a valid phone number';
                }
                return null;
              },
              onSaved: (value) {
                guest.phone = value!.trim();
              },
            ),
          ],
        ),
      ),
    );
  }
}
