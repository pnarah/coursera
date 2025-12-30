class User {
  final int id;
  final String mobileNumber;
  final String? fullName;
  final String? email;
  final String role;
  final int? hotelId;
  final bool isActive;
  final DateTime createdAt;

  User({
    required this.id,
    required this.mobileNumber,
    this.fullName,
    this.email,
    required this.role,
    this.hotelId,
    required this.isActive,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      mobileNumber: json['mobile_number'],
      fullName: json['full_name'],
      email: json['email'],
      role: json['role'],
      hotelId: json['hotel_id'],
      isActive: json['is_active'] ?? true,
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'mobile_number': mobileNumber,
      'full_name': fullName,
      'email': email,
      'role': role,
      'hotel_id': hotelId,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

class Booking {
  final int id;
  final String hotelName;
  final String roomNumber;
  final String roomType;
  final DateTime checkInDate;
  final DateTime checkOutDate;
  final String status;
  final double totalAmount;

  Booking({
    required this.id,
    required this.hotelName,
    required this.roomNumber,
    required this.roomType,
    required this.checkInDate,
    required this.checkOutDate,
    required this.status,
    required this.totalAmount,
  });

  factory Booking.fromJson(Map<String, dynamic> json) {
    return Booking(
      id: json['id'],
      hotelName: json['hotel_name'] ?? 'Unknown Hotel',
      roomNumber: json['room_number'] ?? 'N/A',
      roomType: json['room_type'] ?? 'Standard',
      checkInDate: DateTime.parse(json['check_in_date']),
      checkOutDate: DateTime.parse(json['check_out_date']),
      status: json['status'] ?? 'PENDING',
      totalAmount: (json['total_amount'] ?? 0).toDouble(),
    );
  }
}

class Subscription {
  final int id;
  final String planName;
  final DateTime startDate;
  final DateTime endDate;
  final String status;
  final double amount;

  Subscription({
    required this.id,
    required this.planName,
    required this.startDate,
    required this.endDate,
    required this.status,
    required this.amount,
  });

  factory Subscription.fromJson(Map<String, dynamic> json) {
    return Subscription(
      id: json['id'],
      planName: json['plan_name'] ?? 'Unknown Plan',
      startDate: DateTime.parse(json['start_date']),
      endDate: DateTime.parse(json['end_date']),
      status: json['status'] ?? 'ACTIVE',
      amount: (json['amount'] ?? 0).toDouble(),
    );
  }
}

class Hotel {
  final int id;
  final String name;
  final String address;
  final String? location;
  final int? starRating;
  final int totalRooms;
  final int totalEmployees;

  Hotel({
    required this.id,
    required this.name,
    required this.address,
    this.location,
    this.starRating,
    required this.totalRooms,
    required this.totalEmployees,
  });

  factory Hotel.fromJson(Map<String, dynamic> json) {
    return Hotel(
      id: json['id'],
      name: json['name'],
      address: json['address'] ?? '',
      location: json['location'],
      starRating: json['star_rating'],
      totalRooms: json['total_rooms'] ?? 0,
      totalEmployees: json['total_employees'] ?? 0,
    );
  }
}

class PlatformMetrics {
  final int totalUsers;
  final int totalVendors;
  final int totalHotels;
  final int activeSubscriptions;
  final int expiredSubscriptions;
  final int newUsersThisWeek;
  final int pendingVendorRequests;

  PlatformMetrics({
    required this.totalUsers,
    required this.totalVendors,
    required this.totalHotels,
    required this.activeSubscriptions,
    required this.expiredSubscriptions,
    required this.newUsersThisWeek,
    required this.pendingVendorRequests,
  });

  factory PlatformMetrics.fromJson(Map<String, dynamic> json) {
    return PlatformMetrics(
      totalUsers: json['total_users'] ?? 0,
      totalVendors: json['total_vendors'] ?? 0,
      totalHotels: json['total_hotels'] ?? 0,
      activeSubscriptions: json['active_subscriptions'] ?? 0,
      expiredSubscriptions: json['expired_subscriptions'] ?? 0,
      newUsersThisWeek: json['new_users_this_week'] ?? 0,
      pendingVendorRequests: json['pending_vendor_requests'] ?? 0,
    );
  }
}

class CheckIn {
  final int id;
  final String guestName;
  final String roomNumber;
  final DateTime expectedTime;
  final String status;

  CheckIn({
    required this.id,
    required this.guestName,
    required this.roomNumber,
    required this.expectedTime,
    required this.status,
  });

  factory CheckIn.fromJson(Map<String, dynamic> json) {
    return CheckIn(
      id: json['id'],
      guestName: json['guest_name'] ?? 'Guest',
      roomNumber: json['room_number'] ?? 'N/A',
      expectedTime: DateTime.parse(json['expected_time']),
      status: json['status'] ?? 'PENDING',
    );
  }
}

class ServiceRequest {
  final int id;
  final String serviceName;
  final String roomNumber;
  final String status;
  final DateTime createdAt;

  ServiceRequest({
    required this.id,
    required this.serviceName,
    required this.roomNumber,
    required this.status,
    required this.createdAt,
  });

  factory ServiceRequest.fromJson(Map<String, dynamic> json) {
    return ServiceRequest(
      id: json['id'],
      serviceName: json['service_name'] ?? 'Service',
      roomNumber: json['room_number'] ?? 'N/A',
      status: json['status'] ?? 'PENDING',
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class VendorAnalytics {
  final int totalBookings;
  final double totalRevenue;
  final int totalGuests;

  VendorAnalytics({
    required this.totalBookings,
    required this.totalRevenue,
    required this.totalGuests,
  });

  factory VendorAnalytics.fromJson(Map<String, dynamic> json) {
    return VendorAnalytics(
      totalBookings: json['total_bookings'] ?? 0,
      totalRevenue: (json['total_revenue'] ?? 0).toDouble(),
      totalGuests: json['total_guests'] ?? 0,
    );
  }
}
