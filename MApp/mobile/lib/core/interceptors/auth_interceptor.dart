import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/secure_storage_service.dart';
import '../providers/storage_provider.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

/// Interceptor for handling authentication token refresh
class AuthInterceptor extends QueuedInterceptor {
  final Dio dio;
  final SecureStorageService storage;
  final Ref ref;
  
  bool _isRefreshing = false;
  final List<Function> _requestsWaitingForRefresh = [];

  AuthInterceptor({
    required this.dio,
    required this.storage,
    required this.ref,
  });

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip token check for auth endpoints
    if (_isAuthEndpoint(options.path)) {
      return handler.next(options);
    }

    try {
      final token = await storage.getToken();
      
      if (token == null) {
        // No token, let request proceed (will likely get 401)
        return handler.next(options);
      }

      // Check if token is expired or will expire soon (within 5 minutes)
      if (_isTokenExpiringSoon(token)) {
        // Try to refresh token before making the request
        final newToken = await _refreshToken();
        if (newToken != null) {
          options.headers['Authorization'] = 'Bearer $newToken';
        } else {
          // Refresh failed, use existing token (will likely get 401)
          options.headers['Authorization'] = 'Bearer $token';
        }
      } else {
        // Token is still valid, use it
        options.headers['Authorization'] = 'Bearer $token';
      }
      
      return handler.next(options);
    } catch (e) {
      // Error getting token, proceed without it
      return handler.next(options);
    }
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    // Handle 401 Unauthorized errors
    if (err.response?.statusCode == 401) {
      // Skip refresh for auth endpoints
      if (_isAuthEndpoint(err.requestOptions.path)) {
        return handler.next(err);
      }

      try {
        // Try to refresh the token
        final newToken = await _refreshToken();
        
        if (newToken != null) {
          // Retry the failed request with new token
          final options = err.requestOptions;
          options.headers['Authorization'] = 'Bearer $newToken';
          
          try {
            final response = await dio.fetch(options);
            return handler.resolve(response);
          } catch (e) {
            // Retry failed, pass error along
            return handler.next(err);
          }
        } else {
          // Refresh failed, trigger logout
          await _handleLogout();
          return handler.next(err);
        }
      } catch (e) {
        // Error during refresh, trigger logout
        await _handleLogout();
        return handler.next(err);
      }
    }
    
    return handler.next(err);
  }

  /// Check if the endpoint is an authentication endpoint
  bool _isAuthEndpoint(String path) {
    return path.contains('/auth/login') ||
           path.contains('/auth/logout') ||
           path.contains('/auth/refresh-token') ||
           path.contains('/auth/request-otp') ||
           path.contains('/auth/verify-otp');
  }

  /// Check if token is expired or expiring soon (within 5 minutes)
  bool _isTokenExpiringSoon(String token) {
    try {
      if (JwtDecoder.isExpired(token)) {
        return true; // Already expired
      }
      
      final expirationDate = JwtDecoder.getExpirationDate(token);
      final now = DateTime.now();
      final timeUntilExpiry = expirationDate.difference(now);
      
      // Refresh if token expires in less than 5 minutes
      return timeUntilExpiry.inMinutes < 5;
    } catch (e) {
      // Error decoding token, assume it needs refresh
      return true;
    }
  }

  /// Refresh the access token using refresh token
  Future<String?> _refreshToken() async {
    // Prevent multiple simultaneous refresh attempts
    if (_isRefreshing) {
      // Wait for ongoing refresh to complete
      return await _waitForRefresh();
    }

    _isRefreshing = true;

    try {
      final refreshToken = await storage.getRefreshToken();
      
      if (refreshToken == null) {
        _isRefreshing = false;
        return null;
      }

      // Check if refresh token is expired
      if (_isRefreshTokenExpired(refreshToken)) {
        _isRefreshing = false;
        await _handleLogout();
        return null;
      }

      // Make refresh request (without interceptor to avoid recursion)
      final response = await Dio(BaseOptions(
        baseUrl: dio.options.baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      )).post(
        '/auth/refresh-token',
        data: {'refresh_token': refreshToken},
      );

      if (response.statusCode == 200) {
        final newAccessToken = response.data['access_token'];
        final newRefreshToken = response.data['refresh_token'];

        // Save new tokens
        await storage.saveToken(newAccessToken);
        if (newRefreshToken != null) {
          await storage.saveRefreshToken(newRefreshToken);
        }

        _isRefreshing = false;
        
        // Resolve waiting requests
        _resolveWaitingRequests(newAccessToken);
        
        return newAccessToken;
      } else {
        _isRefreshing = false;
        _resolveWaitingRequests(null);
        return null;
      }
    } catch (e) {
      _isRefreshing = false;
      _resolveWaitingRequests(null);
      return null;
    }
  }

  /// Check if refresh token is expired
  bool _isRefreshTokenExpired(String token) {
    try {
      return JwtDecoder.isExpired(token);
    } catch (e) {
      return true; // Assume expired if can't decode
    }
  }

  /// Wait for ongoing refresh to complete
  Future<String?> _waitForRefresh() async {
    final completer = Completer<String?>();
    _requestsWaitingForRefresh.add(() {
      completer.complete(storage.getToken());
    });
    return completer.future;
  }

  /// Resolve all requests waiting for token refresh
  void _resolveWaitingRequests(String? token) {
    for (final callback in _requestsWaitingForRefresh) {
      callback();
    }
    _requestsWaitingForRefresh.clear();
  }

  /// Handle logout when refresh fails
  Future<void> _handleLogout() async {
    try {
      // Clear tokens
      await storage.deleteToken();
      await storage.deleteRefreshToken();
      
      // TODO: Navigate to login screen
      // This would require access to navigation context
      // For now, just clear storage - the app will redirect on next API call
    } catch (e) {
      // Ignore errors during cleanup
    }
  }
}

/// Provider for auth interceptor
final authInterceptorProvider = Provider.family<AuthInterceptor, Dio>((ref, dio) {
  final storage = ref.read(secureStorageServiceProvider);
  return AuthInterceptor(
    dio: dio,
    storage: storage,
    ref: ref,
  );
});
