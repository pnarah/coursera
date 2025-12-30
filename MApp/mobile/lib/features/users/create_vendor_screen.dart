import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/services/api_service.dart';
import '../../../shared/widgets/common_widgets.dart';

/// Screen for System Admin or Vendor Admin to create vendor accounts
class CreateVendorScreen extends ConsumerStatefulWidget {
  final String userRole; // 'SYSTEM_ADMIN' or 'VENDOR_ADMIN'
  final int? vendorHotelId; // Pre-filled hotel ID for VENDOR_ADMIN
  
  const CreateVendorScreen({
    super.key,
    this.userRole = 'SYSTEM_ADMIN',
    this.vendorHotelId,
  });

  @override
  ConsumerState<CreateVendorScreen> createState() => _CreateVendorScreenState();
}

class _CreateVendorScreenState extends ConsumerState<CreateVendorScreen> {
  final _formKey = GlobalKey<FormState>();
  final _mobileController = TextEditingController();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _hotelIdController = TextEditingController();
  bool _isLoading = false;
  List<Map<String, dynamic>> _vendorHotels = [];
  int? _selectedHotelId;
  bool _isLoadingHotels = false;

  @override
  void initState() {
    super.initState();
    _loadHotels();
    if (widget.vendorHotelId != null) {
      _selectedHotelId = widget.vendorHotelId;
    }
  }

  Future<void> _loadHotels() async {
    setState(() => _isLoadingHotels = true);
    try {
      final apiService = ref.read(apiServiceProvider);
      final response = widget.userRole == 'VENDOR_ADMIN'
          ? await apiService.getVendorHotels()
          : await apiService.getAllHotels();
      setState(() {
        if (response is Map<String, dynamic> && response['hotels'] != null) {
          _vendorHotels = List<Map<String, dynamic>>.from(response['hotels']);
        } else if (response is List) {
          _vendorHotels = List<Map<String, dynamic>>.from(response);
        }
        // Auto-select if only one hotel
        if (_vendorHotels.length == 1 && _selectedHotelId == null) {
          _selectedHotelId = _vendorHotels[0]['id'];
        }
        _isLoadingHotels = false;
      });
    } catch (e) {
      setState(() => _isLoadingHotels = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load hotels: $e')),
        );
      }
    }
  }

  @override
  void dispose() {
    _mobileController.dispose();
    _nameController.dispose();
    _emailController.dispose();
    _hotelIdController.dispose();
    super.dispose();
  }

  Future<void> _createVendor() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() => _isLoading = true);

    try {
      final apiService = ref.read(apiServiceProvider);
      await apiService.createUser(
        mobileNumber: _mobileController.text.trim(),
        role: 'VENDOR_ADMIN',
        fullName: _nameController.text.trim(),
        email: _emailController.text.trim().isEmpty ? null : _emailController.text.trim(),
        hotelId: _selectedHotelId, // Always required now
      );

      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Vendor account created successfully!'),
          backgroundColor: Colors.green,
        ),
      );
      
      context.pop(); // Return to admin dashboard
    } catch (e) {
      setState(() => _isLoading = false);
      
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Failed to create vendor: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.userRole == 'SYSTEM_ADMIN' 
          ? 'Create Vendor Account' 
          : 'Add Vendor Admin'),
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
                          Icon(Icons.business, color: Colors.blue.shade700),
                          const SizedBox(width: 12),
                          const Text(
                            'Vendor Details',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Create a new vendor admin account who can manage hotels',
                        style: TextStyle(color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              
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
              
              // Hotel Selection (required for all)
              if (_isLoadingHotels)
                const Center(child: CircularProgressIndicator())
              else if (_vendorHotels.isEmpty)
                Card(
                  color: Colors.orange.shade50,
                  child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          Icon(Icons.warning, color: Colors.orange.shade700),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Text('No hotels found. Please add a hotel first.'),
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  DropdownButtonFormField<int>(
                    value: _selectedHotelId,
                    decoration: InputDecoration(
                      labelText: 'Assign to Hotel *',
                      hintText: widget.userRole == 'SYSTEM_ADMIN' 
                        ? 'Select hotel to manage' 
                        : 'Choose a hotel',
                      prefixIcon: const Icon(Icons.hotel),
                      border: const OutlineInputBorder(),
                      helperText: widget.userRole == 'SYSTEM_ADMIN'
                        ? 'Vendor admin will manage this specific hotel'
                        : null,
                    ),
                    items: _vendorHotels.map((hotel) {
                      return DropdownMenuItem<int>(
                        value: hotel['id'],
                        child: Text(hotel['name'] ?? 'Hotel #${hotel['id']}'),
                      );
                    }).toList(),
                    onChanged: (value) {
                      setState(() => _selectedHotelId = value);
                    },
                    validator: (value) {
                      if (value == null) {
                        return 'Please select a hotel';
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
                  hintText: 'vendor@example.com',
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
                color: Colors.blue.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.info_outline, color: Colors.blue.shade700),
                          const SizedBox(width: 8),
                          Text(
                            widget.userRole == 'SYSTEM_ADMIN' 
                              ? 'Vendor Admin Capabilities' 
                              : 'Co-Admin Capabilities',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _buildInfoItem(widget.userRole == 'SYSTEM_ADMIN' 
                        ? 'Manages assigned hotel' 
                        : 'Co-manages assigned hotel'),
                      _buildInfoItem('Can add more vendors to same hotel'),
                      _buildInfoItem('Add hotel employees'),
                      _buildInfoItem('View analytics and reports'),
                      _buildInfoItem('Manage room inventory'),
                      if (widget.userRole == 'VENDOR_ADMIN')
                        _buildInfoItem('Full admin access to the hotel', color: Colors.orange.shade700),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              
              // Create Button
              ElevatedButton(
                onPressed: _isLoading ? null : _createVendor,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  backgroundColor: Colors.blue,
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
                        'Create Vendor Account',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoItem(String text, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(Icons.check_circle, size: 16, color: color ?? Colors.blue.shade700),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(color: color ?? Colors.blue.shade900),
            ),
          ),
        ],
      ),
    );
  }
}
