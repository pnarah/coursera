import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorageService {
  static const _storage = FlutterSecureStorage();

  // Keys
  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';
  static const _userIdKey = 'user_id';
  static const _userRoleKey = 'user_role';
  static const _userHotelIdKey = 'user_hotel_id';
  static const _userFullNameKey = 'user_full_name';
  static const _userEmailKey = 'user_email';
  static const _userMobileKey = 'user_mobile';

  // Save tokens
  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  // Save individual token (alias for compatibility)
  Future<void> saveToken(String accessToken) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
  }

  // Save individual refresh token (alias for compatibility)
  Future<void> saveRefreshToken(String refreshToken) async {
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  // Get access token
  Future<String?> getAccessToken() async {
    return await _storage.read(key: _accessTokenKey);
  }

  // Get token (alias for getAccessToken)
  Future<String?> getToken() async {
    return await getAccessToken();
  }

  // Get refresh token
  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }

  // Delete access token
  Future<void> deleteToken() async {
    await _storage.delete(key: _accessTokenKey);
  }

  // Delete refresh token
  Future<void> deleteRefreshToken() async {
    await _storage.delete(key: _refreshTokenKey);
  }

  // Save user ID
  Future<void> saveUserId(String userId) async {
    await _storage.write(key: _userIdKey, value: userId);
  }

  // Get user ID
  Future<String?> getUserId() async {
    return await _storage.read(key: _userIdKey);
  }

  // Save user profile data
  Future<void> saveUserProfile({
    required String role,
    int? hotelId,
    String? fullName,
    String? email,
    String? mobile,
  }) async {
    await _storage.write(key: _userRoleKey, value: role);
    if (hotelId != null) {
      await _storage.write(key: _userHotelIdKey, value: hotelId.toString());
    }
    if (fullName != null) {
      await _storage.write(key: _userFullNameKey, value: fullName);
    }
    if (email != null) {
      await _storage.write(key: _userEmailKey, value: email);
    }
    if (mobile != null) {
      await _storage.write(key: _userMobileKey, value: mobile);
    }
  }

  // Get user role
  Future<String?> getUserRole() async {
    return await _storage.read(key: _userRoleKey);
  }

  // Get user hotel ID
  Future<int?> getUserHotelId() async {
    final hotelId = await _storage.read(key: _userHotelIdKey);
    return hotelId != null ? int.tryParse(hotelId) : null;
  }

  // Get user full name
  Future<String?> getUserFullName() async {
    return await _storage.read(key: _userFullNameKey);
  }

  // Get user email
  Future<String?> getUserEmail() async {
    return await _storage.read(key: _userEmailKey);
  }

  // Get user mobile
  Future<String?> getUserMobile() async {
    return await _storage.read(key: _userMobileKey);
  }

  // Clear all data
  Future<void> clearAll() async {
    await _storage.deleteAll();
  }

  // Check if user is logged in
  Future<bool> isLoggedIn() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }

  // Get role-specific dashboard route
  Future<String?> getRoleDashboardRoute() async {
    final role = await getUserRole();
    if (role == null) return null;
    
    switch (role) {
      case 'GUEST':
        return '/dashboard/guest';
      case 'HOTEL_EMPLOYEE':
        return '/dashboard/employee';
      case 'VENDOR_ADMIN':
        return '/dashboard/vendor';
      case 'SYSTEM_ADMIN':
        return '/dashboard/admin';
      default:
        return '/dashboard/guest'; // Default fallback
    }
  }
}
