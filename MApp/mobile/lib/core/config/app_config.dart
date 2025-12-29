/// Application configuration
class AppConfig {
  // API Base URL - update this to your backend URL
  static const String apiBaseUrl = 'http://localhost:8000/api/v1';
  
  // For iOS simulator use: http://localhost:8000/api/v1
  // For Android emulator use: http://10.0.2.2:8000/api/v1
  // For physical device use: http://YOUR_COMPUTER_IP:8000/api/v1
  
  static const String apiTimeout = '30';
  
  // Storage keys
  static const String tokenKey = 'auth_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userMobileKey = 'user_mobile';
}
