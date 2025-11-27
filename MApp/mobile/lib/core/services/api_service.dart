import 'package:dio/dio.dart';
import '../config/app_config.dart';
import 'secure_storage_service.dart';

/// Comprehensive API service for MApp backend
class ApiService {
  late final Dio _dio;
  final SecureStorageService _storage;

  ApiService(this._storage) {
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

    // Add interceptor for auth token
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.getToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            // Token expired - user needs to re-login
          }
          return handler.next(error);
        },
      ),
    );
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
}
