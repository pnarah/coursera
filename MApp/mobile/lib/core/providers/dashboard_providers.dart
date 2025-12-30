import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../services/secure_storage_service.dart';
import '../models/models.dart';
import 'storage_provider.dart';

// ====================
// AUTH PROVIDERS
// ====================

final currentUserProvider = FutureProvider<User?>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getCurrentUser();
    return User.fromJson(data);
  } catch (e) {
    return null;
  }
});

// ====================
// GUEST DASHBOARD PROVIDERS
// ====================

final currentBookingProvider = FutureProvider<Booking?>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getCurrentBooking();
    if (data == null) return null;
    return Booking.fromJson(data);
  } catch (e) {
    return null;
  }
});

final bookingHistoryProvider = FutureProvider<List<Booking>>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getBookingHistory(limit: 10);
    return data.map((json) => Booking.fromJson(json)).toList();
  } catch (e) {
    return [];
  }
});

// ====================
// EMPLOYEE DASHBOARD PROVIDERS
// ====================

final employeeHotelProvider = FutureProvider<Hotel?>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getEmployeeHotelInfo();
    return Hotel.fromJson(data);
  } catch (e) {
    return null;
  }
});

final todayCheckInsProvider = FutureProvider<List<CheckIn>>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getTodayCheckIns();
    return data.map((json) => CheckIn.fromJson(json)).toList();
  } catch (e) {
    return [];
  }
});

final pendingServiceRequestsProvider = FutureProvider<List<ServiceRequest>>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getPendingServiceRequests();
    return data.map((json) => ServiceRequest.fromJson(json)).toList();
  } catch (e) {
    return [];
  }
});

// ====================
// VENDOR DASHBOARD PROVIDERS
// ====================

final vendorHotelsProvider = FutureProvider<List<Hotel>>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getVendorHotels();
    return data.map((json) => Hotel.fromJson(json)).toList();
  } catch (e) {
    return [];
  }
});

final activeSubscriptionProvider = FutureProvider<Subscription?>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getActiveSubscription();
    if (data == null) return null;
    return Subscription.fromJson(data);
  } catch (e) {
    return null;
  }
});

final vendorAnalyticsProvider = FutureProvider<VendorAnalytics>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getVendorAnalytics();
    return VendorAnalytics.fromJson(data);
  } catch (e) {
    return VendorAnalytics(totalBookings: 0, totalRevenue: 0, totalGuests: 0);
  }
});

// ====================
// ADMIN DASHBOARD PROVIDERS
// ====================

final platformMetricsProvider = FutureProvider<PlatformMetrics>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    final data = await api.getPlatformMetrics();
    return PlatformMetrics.fromJson(data);
  } catch (e) {
    return PlatformMetrics(
      totalUsers: 0,
      totalVendors: 0,
      totalHotels: 0,
      activeSubscriptions: 0,
      expiredSubscriptions: 0,
      newUsersThisWeek: 0,
      pendingVendorRequests: 0,
    );
  }
});

final allVendorsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    return await api.getAllVendors();
  } catch (e) {
    return [];
  }
});

final pendingVendorRequestsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  try {
    final api = ref.watch(apiServiceProvider);
    return await api.getPendingVendorRequests();
  } catch (e) {
    return [];
  }
});
