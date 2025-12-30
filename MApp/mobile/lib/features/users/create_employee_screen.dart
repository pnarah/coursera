import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/services/api_service.dart';
import '../../../core/providers/dashboard_providers.dart';
import '../../../shared/widgets/common_widgets.dart';

/// Screen for Admin or Vendor to create employee accounts
/// Admin can create employees for any hotel
/// Vendor can only create employees for their own hotels
class CreateEmployeeScreen extends ConsumerStatefulWidget {
  final String userRole; // 'SYSTEM_ADMIN' or 'VENDOR_ADMIN'
  final int? vendorHotelId; // Set if vendor is creating employee

  const CreateEmployeeScreen({
    super.key,
    required this.userRole,
    this.vendorHotelId,
  });

  @override
  ConsumerState<CreateEmployeeScreen> createState() => _CreateEmployeeScreenState();
}

class _CreateEmployeeScreenState extends ConsumerState<CreateEmployeeScreen> {
  final _formKey = GlobalKey<FormState>();
  final _mobileController = TextEditingController();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  int? _selectedHotelId;
  bool _isLoading = false;
  List<Map<String, dynamic>> _availableHotels = [];

  @override
  void initState() {
    super.initState();
    _loadAvailableHotels();
  }

  @override
  void dispose() {
    _mobileController.dispose();
    _nameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _loadAvailableHotels() async {
    try {
      final apiService = ref.read(apiServiceProvider);
      
      if (widget.userRole == 'VENDOR_ADMIN') {
        // Vendor can only see their own hotels
        final hotels = await apiService.getVendorHotels();
        setState(() {
          _availableHotels = List<Map<String, dynamic>>.from(
            (hotels as List).map((h) => {
              'id': h['id'],
              'name': h['name'],
            })
          );
          // Pre-select vendor's hotel if only one
          if (_availableHotels.length == 1) {
            _selectedHotelId = _availableHotels[0]['id'];
          } else if (widget.vendorHotelId != null) {
            _selectedHotelId = widget.vendorHotelId;
          }
        });
      } else {
        // Admin can see all hotels
        // TODO: Implement getAllHotels() API
        // For now, show empty dropdown with manual ID input
        setState(() {
          _availableHotels = [];
        });
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load hotels: ${e.toString()}')),
      );
    }
  }

  Future<void> _createEmployee() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_selectedHotelId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('⚠️ Please select a hotel'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.createUser(
        mobileNumber: _mobileController.text.trim(),
        role: 'HOTEL_EMPLOYEE',
        fullName: _nameController.text.trim(),
        email: _emailController.text.trim().isEmpty ? null : _emailController.text.trim(),
        hotelId: _selectedHotelId!,
      );

      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Employee account created successfully!'),
          backgroundColor: Colors.green,
        ),
      );
      
      context.pop(); // Return to dashboard
    } catch (e) {
      setState(() => _isLoading = false);
      
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Failed to create employee: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Create Employee Account'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.badge, color: Colors.green.shade700),
                          const SizedBox(width: 12),
                          const Text(
                            'Employee Details',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Create a new hotel employee account',
                        style: TextStyle(color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              
              // Hotel Selection
              if (_availableHotels.isNotEmpty)
                DropdownButtonFormField<int>(
                  value: _selectedHotelId,
                  decoration: const InputDecoration(
                    labelText: 'Select Hotel *',
                    prefixIcon: Icon(Icons.hotel),
                    border: OutlineInputBorder(),
                  ),
                  items: _availableHotels.map((hotel) {
                    return DropdownMenuItem<int>(
                      value: hotel['id'],
                      child: Text(hotel['name']),
                    );
                  }).toList(),
                  onChanged: widget.userRole == 'VENDOR_ADMIN' && _availableHotels.length == 1
                      ? null // Disable if vendor has only one hotel
                      : (value) {
                          setState(() => _selectedHotelId = value);
                        },
                  validator: (value) {
                    if (value == null) {
                      return 'Please select a hotel';
                    }
                    return null;
                  },
                )
              else
                TextFormField(
                  decoration: const InputDecoration(
                    labelText: 'Hotel ID *',
                    hintText: 'Enter hotel ID',
                    prefixIcon: Icon(Icons.hotel),
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                  onChanged: (value) {
                    setState(() {
                      _selectedHotelId = int.tryParse(value);
                    });
                  },
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Hotel ID is required';
                    }
                    if (int.tryParse(value) == null) {
                      return 'Please enter a valid hotel ID';
                    }
                    return null;
                  },
                ),
              const SizedBox(height: 16),
              
              // Mobile Number
              TextFormField(
                controller: _mobileController,
                decoration: const InputDecoration(
                  labelText: 'Mobile Number *',
                  hintText: '5551234567',
                  prefixIcon: Icon(Icons.phone),
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.phone,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Mobile number is required';
                  }
                  if (value.trim().length < 10) {
                    return 'Mobile number must be at least 10 digits';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              
              // Full Name
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Full Name *',
                  hintText: 'John Doe',
                  prefixIcon: Icon(Icons.person),
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Full name is required';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              
              // Email (Optional)
              TextFormField(
                controller: _emailController,
                decoration: const InputDecoration(
                  labelText: 'Email (Optional)',
                  hintText: 'employee@example.com',
                  prefixIcon: Icon(Icons.email),
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.emailAddress,
                validator: (value) {
                  if (value != null && value.trim().isNotEmpty) {
                    if (!value.contains('@')) {
                      return 'Please enter a valid email';
                    }
                  }
                  return null;
                },
              ),
              const SizedBox(height: 24),
              
              // Info Card
              Card(
                color: Colors.green.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.info_outline, color: Colors.green.shade700),
                          const SizedBox(width: 8),
                          const Text(
                            'Employee Permissions',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '• Employee will have access to hotel operations\n'
                        '• Can manage check-ins/check-outs\n'
                        '• Can handle service requests\n'
                        '• Can view room status and bookings\n'
                        '• Additional permissions can be granted later',
                        style: TextStyle(color: Colors.grey.shade700),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              
              // Create Button
              ElevatedButton(
                onPressed: _isLoading ? null : _createEmployee,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Text(
                        'Create Employee Account',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
