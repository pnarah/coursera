import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../config/app_config.dart';
import '../interceptors/auth_interceptor.dart';
import 'secure_storage_service.dart';
import '../providers/storage_provider.dart';


/// Comprehensive API service for MApp backend
class ApiService {
  late final Dio _dio;
  final SecureStorageService _storage;
  final Ref? _ref;

  ApiService(this._storage, {Ref? ref}) : _ref = ref {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        headers: {
          'Content-Type': 'application/json',
        },
      ),
    );

    // Add auth interceptor for automatic token refresh
    if (_ref != null) {
      final authInterceptor = _ref!.read(authInterceptorProvider(_dio));
      _dio.interceptors.add(authInterceptor);
    } else {
      // Fallback: Basic token interceptor (for backward compatibility)
      _dio.interceptors.add(
        InterceptorsWrapper(
          onRequest: (options, handler) async {
            final token = await _storage.getToken();
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
            }
            return handler.next(options);
          },
        ),
      );
    }
  }

  // ====================
  // AUTHENTICATION APIs
  // ====================

  Future<Map<String, dynamic>> sendOTP(String mobileNumber) async {
    final response = await _dio.post('/auth/send-otp', data: {
      'mobile_number': mobileNumber,
      'country_code': '+1',
    });
    return response.data;
  }

  Future<Map<String, dynamic>> verifyOTP(
    String mobileNumber,
    String otp,
    String deviceInfo,
  ) async {
    final response = await _dio.post('/auth/verify-otp', data: {
      'mobile_number': mobileNumber,
      'otp': otp,
      'device_info': deviceInfo,
    });
    return response.data;
  }

  // ====================
  // HOTEL SEARCH APIs
  // ====================

  Future<Map<String, dynamic>> getCities() async {
    final response = await _dio.get('/hotels/cities');
    return response.data;
  }

  Future<Map<String, dynamic>> searchHotels({
    String? city,
    DateTime? checkIn,
    DateTime? checkOut,
    int? guests,
    String? roomType,
    int skip = 0,
    int limit = 20,
  }) async {
    final queryParams = {
      if (city != null) 'city': city,
      if (checkIn != null) 'check_in': checkIn.toIso8601String().split('T')[0],
      if (checkOut != null) 'check_out': checkOut.toIso8601String().split('T')[0],
      if (guests != null) 'guests': guests,
      if (roomType != null) 'room_type': roomType,
      'skip': skip,
      'limit': limit,
    };

    final response = await _dio.get('/hotels/search', queryParameters: queryParams);
    return response.data;
  }

  Future<Map<String, dynamic>> getHotelDetails(int hotelId) async {
    final response = await _dio.get('/hotels/$hotelId');
    return response.data;
  }

  Future<Map<String, dynamic>> getHotelRooms(int hotelId) async {
    final response = await _dio.get('/hotels/$hotelId/rooms');
    return response.data;
  }

  // ====================
  // AVAILABILITY & LOCK APIs
  // ====================

  Future<Map<String, dynamic>> lockAvailability({
    required int hotelId,
    required String roomType,
    required DateTime checkInDate,
    required DateTime checkOutDate,
    required int quantity,
  }) async {
    final response = await _dio.post('/availability/lock', data: {
      'hotel_id': hotelId,
      'room_type': roomType,
      'check_in_date': checkInDate.toIso8601String().split('T')[0],
      'check_out_date': checkOutDate.toIso8601String().split('T')[0],
      'quantity': quantity,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getLockStatus(String lockId) async {
    final response = await _dio.get('/availability/lock/$lockId');
    return response.data;
  }

  Future<Map<String, dynamic>> releaseLock(String lockId) async {
    final response = await _dio.post('/availability/release', data: {
      'lock_id': lockId,
    });
    return response.data;
  }

  // ====================
  // BOOKING APIs
  // ====================

  Future<Map<String, dynamic>> createBooking({
    required int hotelId,
    required String roomType,
    required DateTime checkIn,
    required DateTime checkOut,
    required int guests,
    required String lockId,
    required List<Map<String, dynamic>> guestList,
  }) async {
    final response = await _dio.post('/bookings', data: {
      'hotel_id': hotelId,
      'room_type': roomType,
      'check_in': checkIn.toIso8601String().split('T')[0],
      'check_out': checkOut.toIso8601String().split('T')[0],
      'guests': guests,
      'lock_id': lockId,
      'guest_list': guestList,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getBookingDetails(int bookingId) async {
    final response = await _dio.get('/bookings/$bookingId');
    return response.data;
  }

  Future<Map<String, dynamic>> getUserBookings({int skip = 0, int limit = 20}) async {
    final response = await _dio.get('/bookings', queryParameters: {
      'skip': skip,
      'limit': limit,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> cancelBooking(int bookingId) async {
    final response = await _dio.post('/bookings/$bookingId/cancel');
    return response.data;
  }

  // ====================
  // SERVICES APIs
  // ====================

  Future<Map<String, dynamic>> getHotelServices(int hotelId) async {
    final response = await _dio.get('/hotels/$hotelId/services');
    return response.data;
  }

  Future<Map<String, dynamic>> orderService({
    required int bookingId,
    required int serviceId,
    int quantity = 1,
    String? specialInstructions,
  }) async {
    final response = await _dio.post('/bookings/$bookingId/services', data: {
      'service_id': serviceId,
      'quantity': quantity,
      if (specialInstructions != null) 'special_instructions': specialInstructions,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getBookingServices(int bookingId) async {
    final response = await _dio.get('/bookings/$bookingId/services');
    return response.data;
  }

  // ====================
  // INVOICE APIs
  // ====================

  Future<Map<String, dynamic>> getInvoice(int bookingId) async {
    final response = await _dio.get('/bookings/$bookingId/invoice');
    return response.data;
  }

  // ====================
  // PAYMENT APIs
  // ====================

  Future<Map<String, dynamic>> createPayment({
    required int bookingId,
    double? amount,
    String currency = 'USD',
  }) async {
    final response = await _dio.post('/payments/', data: {
      'booking_id': bookingId,
      if (amount != null) 'amount': amount,
      'currency': currency,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> getPaymentDetails(int paymentId) async {
    final response = await _dio.get('/payments/$paymentId');
    return response.data;
  }

  // ====================
  // USER APIs
  // ====================

  Future<Map<String, dynamic>> getCurrentUser() async {
    final response = await _dio.get('/users/me');
    return response.data;
  }

  Future<Map<String, dynamic>> updateProfile({
    String? fullName,
    String? email,
  }) async {
    final response = await _dio.put('/users/me', data: {
      if (fullName != null) 'full_name': fullName,
      if (email != null) 'email': email,
    });
    return response.data;
  }

  // ====================
  // GUEST DASHBOARD APIs
  // ====================

  Future<Map<String, dynamic>?> getCurrentBooking() async {
    try {
      final response = await _dio.get('/bookings/current');
      return response.data;
    } catch (e) {
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> getBookingHistory({int limit = 10}) async {
    final response = await _dio.get('/bookings', queryParameters: {
      'skip': 0,
      'limit': limit,
    });
    return List<Map<String, dynamic>>.from(response.data['bookings'] ?? []);
  }

  // ====================
  // EMPLOYEE DASHBOARD APIs
  // ====================

  Future<Map<String, dynamic>> getEmployeeHotelInfo() async {
    final response = await _dio.get('/employee/hotel');
    return response.data;
  }

  Future<List<Map<String, dynamic>>> getTodayCheckIns() async {
    final response = await _dio.get('/employee/checkins/today');
    return List<Map<String, dynamic>>.from(response.data['checkins'] ?? []);
  }

  Future<List<Map<String, dynamic>>> getPendingServiceRequests() async {
    final response = await _dio.get('/employee/service-requests/pending');
    return List<Map<String, dynamic>>.from(response.data['requests'] ?? []);
  }

  // ====================
  // VENDOR DASHBOARD APIs
  // ====================

  Future<List<Map<String, dynamic>>> getVendorHotels() async {
    final response = await _dio.get('/vendor/hotels');
    return List<Map<String, dynamic>>.from(response.data['hotels'] ?? []);
  }

  Future<Map<String, dynamic>?> getActiveSubscription() async {
    try {
      final response = await _dio.get('/subscriptions/active');
      return response.data;
    } catch (e) {
      return null;
    }
  }

  Future<Map<String, dynamic>> getVendorAnalytics() async {
    final response = await _dio.get('/vendor/analytics');
    return response.data;
  }

  // ====================
  // ADMIN DASHBOARD APIs
  // ====================

  Future<Map<String, dynamic>> getPlatformMetrics() async {
    final response = await _dio.get('/admin/metrics');
    return response.data;
  }

  Future<List<Map<String, dynamic>>> getAllVendors({
    int skip = 0,
    int limit = 50,
  }) async {
    final response = await _dio.get('/admin/vendors', queryParameters: {
      'skip': skip,
      'limit': limit,
    });
    return List<Map<String, dynamic>>.from(response.data['vendors'] ?? []);
  }

  Future<List<Map<String, dynamic>>> getPendingVendorRequests() async {
    final response = await _dio.get('/admin/vendor-requests');
    return List<Map<String, dynamic>>.from(response.data['requests'] ?? []);
  }

  Future<Map<String, dynamic>> extendSubscription({
    required int subscriptionId,
    required int extendDays,
    required String reason,
  }) async {
    final response = await _dio.post('/admin/subscriptions/extend', data: {
      'subscription_id': subscriptionId,
      'extend_days': extendDays,
      'reason': reason,
    });
    return response.data;
  }

  Future<List<Map<String, dynamic>>> getAuditLogs({
    int? adminUserId,
    String? action,
    int limit = 100,
    int offset = 0,
  }) async {
    final response = await _dio.get('/admin/audit-logs', queryParameters: {
      if (adminUserId != null) 'admin_user_id': adminUserId,
      if (action != null) 'action': action,
      'limit': limit,
      'offset': offset,
    });
    return List<Map<String, dynamic>>.from(response.data['logs'] ?? []);
  }

  // ====================
  // NOTIFICATION APIs
  // ====================

  Future<List<Map<String, dynamic>>> getNotifications({
    int skip = 0,
    int limit = 20,
  }) async {
    final response = await _dio.get('/notifications/notifications', queryParameters: {
      'skip': skip,
      'limit': limit,
    });
    return List<Map<String, dynamic>>.from(response.data['notifications'] ?? []);
  }

  Future<Map<String, dynamic>> markNotificationRead(int notificationId) async {
    final response = await _dio.put('/notifications/notifications/$notificationId/read');
    return response.data;
  }

  // ====================
  // USER MANAGEMENT APIs
  // ====================

  /// Create a new user (Admin creates Vendor or Employee, Vendor creates Employee)
  /// - Admin can create: VENDOR_ADMIN, HOTEL_EMPLOYEE
  /// - Vendor can create: HOTEL_EMPLOYEE (only for their hotels)
  Future<Map<String, dynamic>> createUser({
    required String mobileNumber,
    required String role, // 'VENDOR_ADMIN' or 'HOTEL_EMPLOYEE'
    String? fullName,
    String? email,
    int? hotelId, // Required for HOTEL_EMPLOYEE
  }) async {
    final response = await _dio.post('/users/', data: {
      'mobile_number': mobileNumber,
      'country_code': '+1',
      'role': role,
      if (fullName != null) 'full_name': fullName,
      if (email != null) 'email': email,
      if (hotelId != null) 'hotel_id': hotelId,
    });
    return response.data;
  }

  /// Get all users (admin only)
  Future<Map<String, dynamic>> getAllUsers({
    String? role,
    int? hotelId,
    int skip = 0,
    int limit = 50,
  }) async {
    final queryParams = {
      if (role != null) 'role': role,
      if (hotelId != null) 'hotel_id': hotelId,
      'skip': skip,
      'limit': limit,
    };
    final response = await _dio.get('/users/', queryParameters: queryParams);
    return response.data;
  }

  /// Get all hotels (admin only)
  Future<Map<String, dynamic>> getAllHotels({
    int skip = 0,
    int limit = 100,
  }) async {
    final response = await _dio.get('/hotels/', queryParameters: {
      'skip': skip,
      'limit': limit,
    });
    return response.data;
  }

  /// Update user details
  Future<Map<String, dynamic>> updateUser(
    int userId, {
    String? fullName,
    String? email,
    String? role,
    int? hotelId,
    bool? isActive,
  }) async {
    final response = await _dio.put('/users/$userId', data: {
      if (fullName != null) 'full_name': fullName,
      if (email != null) 'email': email,
      if (role != null) 'role': role,
      if (hotelId != null) 'hotel_id': hotelId,
      if (isActive != null) 'is_active': isActive,
    });
    return response.data;
  }

  /// Delete user (admin only)
  Future<void> deleteUser(int userId) async {
    await _dio.delete('/users/$userId');
  }

  /// Logout from current session
  Future<void> logout() async {
    await _dio.post('/auth/logout');
  }

  /// Get active sessions
  Future<List<Map<String, dynamic>>> getSessions() async {
    final response = await _dio.get('/auth/sessions');
    return List<Map<String, dynamic>>.from(response.data['sessions'] ?? []);
  }

  /// Revoke a specific session
  Future<void> revokeSession(String sessionId) async {
    await _dio.delete('/auth/sessions/$sessionId');
  }
}

/// Provider for API service with token refresh support
final apiServiceProvider = Provider<ApiService>((ref) {
  final storage = ref.read(secureStorageServiceProvider);
  return ApiService(storage, ref: ref);
});


