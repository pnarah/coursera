# Flutter Mobile Application

## Setup Instructions

### Prerequisites
- Flutter SDK 3.0 or higher
- Android Studio / Xcode for emulators

### Installation

1. Install Flutter dependencies:
```bash
flutter pub get
```

2. Run the app:
```bash
flutter run
```

### Project Structure

```
lib/
├── main.dart                    # App entry point
├── core/
│   ├── services/
│   │   ├── api_service.dart     # HTTP client with Dio
│   │   └── secure_storage_service.dart  # Token storage
│   └── widgets/                 # Shared UI components
├── features/
│   ├── authentication/
│   │   └── login_screen.dart    # OTP login UI
│   ├── home/
│   │   └── home_screen.dart     # Main dashboard
│   ├── hotels/                  # Hotel listing & details
│   └── booking/                 # Booking flow
```

### Dependencies

- **flutter_riverpod**: State management
- **dio**: HTTP client
- **go_router**: Navigation
- **flutter_secure_storage**: Secure token storage
- **json_annotation**: JSON serialization

### Configuration

Update the API base URL in `lib/core/services/api_service.dart`:
```dart
static const String baseUrl = 'http://your-backend-url/api/v1';
```

### Testing

Run tests:
```bash
flutter test
```

### Build

Build for Android:
```bash
flutter build apk --release
```

Build for iOS:
```bash
flutter build ios --release
```
