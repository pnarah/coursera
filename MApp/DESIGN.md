# Hotel Room Booking Mobile Application - Design Document

## 1. Overview

A cross-platform mobile application (Android & iOS) enabling users to search hotels across multiple geographical locations, view real‑time room availability and pricing, book rooms, pre‑order and in‑stay services (airport pickup/drop, cab, laundry, leisure/spa, food & room service), manage bookings, track invoices, and perform secure checkout with consolidated billing. Authentication uses mobile number + OTP with robust concurrent session management. The system supports dynamic pricing, inventory locking to prevent double booking, and granular service lifecycle tracking.

## 2. Technology Stack

### 2.1 Mobile Application
- **Framework**: Flutter (recommended) or React Native
  - Flutter advantage: unified UI toolkit, better performance for rich interactions (calendar, filters, service selection grids)
  - React Native alternative for JS teams
- **State Management**:
  - Flutter: Riverpod (preferred) or Provider
  - React Native: Redux Toolkit or Zustand
- **Navigation**:
  - Flutter: go_router
  - React Native: React Navigation
- **HTTP Client**:
  - Flutter: dio
  - React Native: axios
- **Secure Storage**:
  - Flutter: flutter_secure_storage
  - React Native: react-native-keychain

### 2.2 Backend Application
- **Framework**: Node.js (NestJS recommended for modular domain separation) or Spring Boot / FastAPI
- **Primary Database**: PostgreSQL (users, hotels, rooms, bookings, services, invoices, payments)
- **Cache/Session/Locking**: Redis (OTP, sessions, room availability locks, rate limiting)
- **Search Layer (Optional Phase 2)**: Elasticsearch for full‑text hotel search & geo queries
- **Authentication**: JWT (access + refresh) + Redis session context
- **OTP Delivery**: Twilio SMS / AWS SNS
- **Payment Gateway**: Stripe / Razorpay (India) / Adyen (global) integrated with Payments Service
- **API Documentation**: OpenAPI / Swagger

### 2.3 Infrastructure
- **Cloud**: AWS (recommended) / GCP / Azure
- **Containerization**: Docker images
- **Orchestration**: Kubernetes (separate deployments per service: Auth, Hotel, Room Availability, Booking, Service Ordering, Billing)
- **Load Balancer / API Gateway**: AWS ALB + Kong / NGINX
- **CI/CD**: GitHub Actions (build, test, deploy) with environment gates
- **Monitoring & Observability**: Prometheus + Grafana, OpenTelemetry traces, Loki for logs
- **Secrets Management**: AWS Secrets Manager / Vault
- **File/Object Storage**: S3 for hotel images / invoices (PDF)

## 3. Architecture Design

### 3.1 System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Mobile Applications                      │
│            (Android & iOS - Flutter / React Native)         │
└───────────────────────────┬────────────────────────────────┘
          │ HTTPS / REST / WebSocket (events)
┌───────────────────────────▼────────────────────────────────┐
│                 API Gateway / Load Balancer                │
└───────────────────────────┬────────────────────────────────┘
          │
  ┌───────────────────┼─────────────────────┬──────────────────────┬───────────────────────┐
  │                   │                     │                      │                       │
┌───────▼──────┐   ┌───────▼────────┐   ┌────────▼─────────┐   ┌─────────▼────────┐   ┌────────▼──────┐
│ Auth Service │   │ Hotel Service  │   │ Room Availability │   │ Booking Service   │   │ Service Order │
│ (OTP/JWT)    │   │ (Locations,    │   │ Service (inventory│   │ (room booking,    │   │ Service (cab, │
│              │   │ metadata, imgs)│   │ locking, pricing) │   │ modifications)    │   │ laundry, food)│
└───────┬──────┘   └────────┬───────┘   └─────────┬────────┘   └──────────┬────────┘   └────────┬──────┘
  │                    │                      │                     │                      │
  └───────────────┬────┴───────┬──────────────┴────────────┬─────────┴────────────┬────────┴─────────┐
      │            │                             │                      │                  │
     ┌──────▼─────┐ ┌────▼─────┐                ┌──────▼─────┐        ┌──────▼─────┐      ┌─────▼─────┐
     │ PostgreSQL │ │ Redis    │                │ Payment    │        │ OTP Service│      │ Analytics  │
     │ (Primary)  │ │ (Cache & │                │ Gateway    │        │ (Twilio/SNS)│     │ / Events   │
     │            │ │ locks)   │                │ (Stripe etc)│       │            │      │ (Kafka)    │
     └────────────┘ └──────────┘                └────────────┘        └────────────┘      └────────────┘
```

### 3.2 Application Architecture Pattern
- **Pattern**: Clean Architecture / Layered Architecture
- **Layers**:
  - **Presentation Layer**: UI Components, Screens
  - **Business Logic Layer**: Services, Use Cases
  - **Data Layer**: Repositories, API Clients, Local Storage

## 4. Authentication & Session Management

### 4.1 OTP-Based Login Flow

```
1. User enters mobile number
   └─> App sends request to /api/auth/send-otp
       └─> Backend generates 6-digit OTP
           └─> Store OTP in Redis (TTL: 5 minutes)
           └─> Send OTP via SMS (Twilio/SNS)
           └─> Return success response

2. User enters OTP
   └─> App sends request to /api/auth/verify-otp
       └─> Backend validates OTP from Redis
           └─> If valid:
               ├─> Generate JWT Access Token (15 min expiry)
               ├─> Generate JWT Refresh Token (7 days expiry)
               ├─> Create session in Redis
               └─> Return tokens to app
           └─> If invalid:
               └─> Return error (max 3 attempts)

3. Authenticated requests
   └─> App sends Access Token in Authorization header
       └─> Backend validates token
           └─> If expired: Use Refresh Token
           └─> If valid: Process request
```

### 4.2 Session Management

#### Session Storage (Redis)
```
Key: session:{userId}:{sessionId}
Value: {
  userId: string,
  sessionId: string,
  deviceInfo: string,
  loginTime: timestamp,
  lastActiveTime: timestamp,
  refreshToken: string
}
TTL: 7 days
```

#### Concurrent Session Handling
- Allow multiple active sessions per user
- Track each device/session separately
- User can view active sessions
- User can revoke specific sessions
- Automatic cleanup of expired sessions

### 4.3 Logout Flow
```
1. User clicks logout
   └─> App sends request to /api/auth/logout
       └─> Backend:
           ├─> Remove session from Redis
           ├─> Blacklist current access token
           └─> Return success response
       └─> App:
           ├─> Clear tokens from secure storage
           ├─> Clear app state
           └─> Navigate to login screen
```

## 5. Database Schema

### 5.0 Naming & Conventions
- All primary keys: UUID (server-generated)
- Timestamps: created_at, updated_at (UTC)
- Soft deletes (if needed future): deleted_at nullable
- Monetary fields: DECIMAL(12,2)

### 5.1 Users Table (same as original with hotels context)
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mobile_number VARCHAR(15) UNIQUE NOT NULL,
  country_code VARCHAR(5) NOT NULL,
  full_name VARCHAR(120),
  email VARCHAR(150),
  loyalty_tier VARCHAR(30) DEFAULT 'STANDARD',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT true
);
CREATE INDEX idx_users_mobile ON users(mobile_number);
```

### 5.2 Locations & Hotels
```sql
CREATE TABLE locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  country VARCHAR(80) NOT NULL,
  state VARCHAR(80),
  city VARCHAR(80) NOT NULL,
  latitude DECIMAL(10,6),
  longitude DECIMAL(10,6),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE hotels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id UUID REFERENCES locations(id),
  hotel_code VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(150) NOT NULL,
  description TEXT,
  star_rating INT CHECK (star_rating BETWEEN 1 AND 5),
  address TEXT,
  timezone VARCHAR(60) NOT NULL,
  checkin_time TIME DEFAULT '14:00',
  checkout_time TIME DEFAULT '11:00',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_hotels_location ON hotels(location_id);
```

### 5.3 Room Types & Rooms
```sql
CREATE TABLE room_types (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id UUID REFERENCES hotels(id),
  code VARCHAR(30) NOT NULL,
  name VARCHAR(100) NOT NULL,
  base_price DECIMAL(12,2) NOT NULL,
  capacity INT NOT NULL,
  bed_config VARCHAR(50), -- e.g. "Queen", "Twin"
  amenities JSONB,        -- list of amenity codes
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_room_types_code ON room_types(hotel_id, code);

CREATE TABLE rooms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id UUID REFERENCES hotels(id),
  room_type_id UUID REFERENCES room_types(id),
  room_number VARCHAR(20) NOT NULL,
  floor INT,
  status VARCHAR(20) DEFAULT 'AVAILABLE', -- AVAILABLE, MAINTENANCE
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_rooms_number ON rooms(hotel_id, room_number);
```

### 5.4 Services & Service Categories
```sql
CREATE TABLE service_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(80) NOT NULL, -- "Transport", "Food", "Laundry", "Leisure", "Spa"
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id UUID REFERENCES hotels(id), -- null if global
  category_id UUID REFERENCES service_categories(id),
  code VARCHAR(40) NOT NULL,
  name VARCHAR(120) NOT NULL,
  description TEXT,
  pricing_model VARCHAR(30) NOT NULL, -- FIXED, PER_UNIT, PER_DAY
  unit_price DECIMAL(12,2) NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_services_code ON services(hotel_id, code);
```

### 5.5 Bookings & Guests
```sql
CREATE TABLE bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_reference VARCHAR(25) UNIQUE NOT NULL,
  user_id UUID REFERENCES users(id),
  hotel_id UUID REFERENCES hotels(id),
  room_type_id UUID REFERENCES room_types(id),
  checkin_date DATE NOT NULL,
  checkout_date DATE NOT NULL,
  num_rooms INT DEFAULT 1,
  num_guests INT NOT NULL,
  total_room_amount DECIMAL(12,2) DEFAULT 0,
  total_service_amount DECIMAL(12,2) DEFAULT 0,
  booking_status VARCHAR(20) DEFAULT 'CONFIRMED', -- CONFIRMED, CANCELLED, COMPLETED
  payment_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PARTIAL, PAID
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bookings_user ON bookings(user_id);
CREATE INDEX idx_bookings_hotel_dates ON bookings(hotel_id, checkin_date, checkout_date);

CREATE TABLE guests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID REFERENCES bookings(id),
  name VARCHAR(100) NOT NULL,
  age INT,
  gender VARCHAR(15),
  id_doc_type VARCHAR(30),
  id_doc_number VARCHAR(60),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.6 Booking Services (Pre & In-Stay)
```sql
CREATE TABLE booking_services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID REFERENCES bookings(id),
  service_id UUID REFERENCES services(id),
  requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  scheduled_for TIMESTAMP, -- when the service should occur (pickup time etc.)
  quantity INT DEFAULT 1,
  unit_price DECIMAL(12,2) NOT NULL,
  total_price DECIMAL(12,2) NOT NULL,
  status VARCHAR(25) DEFAULT 'REQUESTED', -- REQUESTED, SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_booking_services_booking ON booking_services(booking_id);
```

### 5.7 Payments & Invoices
```sql
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID REFERENCES bookings(id),
  subtotal DECIMAL(12,2) NOT NULL,
  taxes DECIMAL(12,2) NOT NULL,
  discounts DECIMAL(12,2) DEFAULT 0,
  total_due DECIMAL(12,2) NOT NULL,
  currency VARCHAR(10) DEFAULT 'USD',
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID REFERENCES bookings(id),
  invoice_id UUID REFERENCES invoices(id),
  gateway VARCHAR(40),
  transaction_id VARCHAR(80),
  amount DECIMAL(12,2) NOT NULL,
  status VARCHAR(20) DEFAULT 'SUCCESS', -- SUCCESS, FAILED, PENDING
  method VARCHAR(30), -- CARD, UPI, NETBANKING, WALLET
  paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.8 Room Inventory Lock (Redis)
```
Key: lock:hotel:{hotelId}:room_type:{roomTypeId}:{date}
Value: { held: int, expiresAt: timestamp }
TTL: short (e.g., 2 minutes) during booking funnel to prevent race conditions
```

## 6. Core Domain Flows

### 6.1 Room Booking Flow (High-Level)
```
1. User searches hotels by location, dates, guests
  -> Hotel Service returns matching hotels + room type availability + starting price
2. User selects hotel & room type
  -> Room Availability Service places a temporary lock (Redis) for desired rooms
3. User enters guest details & optional pre-book services (pickup, early check-in) 
4. Pricing engine calculates total (room base + dynamic adjustments + services)
5. User confirms -> Booking Service creates booking, persists guests & services
6. Invoice generated (Invoice Service) with initial subtotal
7. User pays deposit or full amount (Payment Service)
8. Lock released / inventory permanently decremented for stay interval
```

### 6.2 In-Stay Service Ordering
```
1. User opens current booking
2. Navigates to Services tab -> filtered list (available now / scheduleable)
3. Selects service(s), quantity, optional schedule time
4. Booking Service adds booking_services rows (status REQUESTED)
5. Staff / automation transitions status -> SCHEDULED / IN_PROGRESS / COMPLETED
6. On COMPLETED: Invoice Service recalculates invoice (adds line items)
7. User can view real-time running bill
```

### 6.3 Checkout & Consolidated Billing
```
1. User initiates checkout (or auto-trigger on checkout_date)
2. System verifies all booking_services statuses are either COMPLETED/CANCELLED
3. Final invoice generated including taxes, discounts, loyalty adjustments
4. Payment Service requests remaining amount (if PARTIAL earlier)
5. On PAYMENT SUCCESS -> booking_status becomes COMPLETED, payment_status PAID
6. Session can retain limited post-stay access (invoice viewing) until TTL
```

### 6.4 Dynamic Pricing (Simplified)
Factors: seasonality, occupancy rate per hotel, loyalty tier, lead time.
Pricing engine formula example:
```
final_price = base_price
        * season_multiplier
        * occupancy_multiplier
        - loyalty_discount
        - promotional_discount
```

## 7. API Endpoints

### 7.1 Authentication
```
POST   /api/auth/send-otp             { mobileNumber, countryCode }
POST   /api/auth/verify-otp           { mobileNumber, otp, deviceInfo }
POST   /api/auth/refresh-token        { refreshToken }
POST   /api/auth/logout               (Authorization: Bearer)
GET    /api/auth/sessions             (Authorization)
DELETE /api/auth/sessions/:sessionId  (Authorization)
```

### 7.2 Hotel & Location Search
```
GET    /api/locations?query=delhi
GET    /api/hotels/search?city=Delhi&checkin=2025-01-10&checkout=2025-01-15&guests=2
GET    /api/hotels/:hotelId
GET    /api/hotels/:hotelId/room-types?checkin=...&checkout=...&guests=2
```

### 7.3 Room Availability & Pricing
```
POST   /api/availability/lock         { hotelId, roomTypeId, checkinDate, checkoutDate, numRooms }
POST   /api/availability/release      { lockId }
GET    /api/availability/quote        params: hotelId, roomTypeId, dates, guests
```

### 7.4 Booking
```
POST   /api/bookings                  { hotelId, roomTypeId, checkinDate, checkoutDate, guests: [], preServices: [] }
GET    /api/bookings?status=CONFIRMED&page=1&limit=10
GET    /api/bookings/:bookingId
PUT    /api/bookings/:bookingId/cancel
PUT    /api/bookings/:bookingId/checkout
```

### 7.5 Services (Pre & In-Stay)
```
GET    /api/hotels/:hotelId/services?category=Food
POST   /api/bookings/:bookingId/services        { serviceId, quantity, scheduledFor, notes }
PUT    /api/bookings/:bookingId/services/:id    { status }
```

### 7.6 Invoice & Payment
```
GET    /api/bookings/:bookingId/invoice
POST   /api/payments                          { bookingId, amount, method }
GET    /api/payments/:paymentId
```

### 7.7 User Profile
```
GET    /api/users/profile
PUT    /api/users/profile                     { fullName, email }
GET    /api/users/loyalty                     returns tier & points
```

## 8. Mobile Application Structure

### 5.4 Passengers Table
```sql
CREATE TABLE passengers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID REFERENCES bookings(id),
    name VARCHAR(100) NOT NULL,
    age INTEGER NOT NULL,
    gender VARCHAR(10),
    seat_number VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.5 Stations Table
```sql
CREATE TABLE stations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_code VARCHAR(10) UNIQUE NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 6. API Endpoints

### 6.1 Authentication APIs
```
POST   /api/auth/send-otp
       Body: { mobileNumber: string, countryCode: string }
       Response: { success: boolean, message: string }

POST   /api/auth/verify-otp
       Body: { mobileNumber: string, otp: string, deviceInfo: string }
       Response: { accessToken: string, refreshToken: string, user: object }

POST   /api/auth/refresh-token
       Body: { refreshToken: string }
       Response: { accessToken: string }

POST   /api/auth/logout
       Headers: Authorization: Bearer {token}
       Response: { success: boolean }

GET    /api/auth/sessions
       Headers: Authorization: Bearer {token}
       Response: { sessions: array }

DELETE /api/auth/sessions/:sessionId
       Headers: Authorization: Bearer {token}
       Response: { success: boolean }
```

### 6.2 Train Search APIs
```
GET    /api/trains/search
       Query: source, destination, date
       Response: { trains: array }

GET    /api/trains/:trainId
       Response: { train: object }

GET    /api/trains/:trainId/availability
       Query: date
       Response: { availableSeats: number, seatLayout: array }
```

### 6.3 Booking APIs
```
POST   /api/bookings
       Headers: Authorization: Bearer {token}
       Body: { trainId, journeyDate, passengers: array }
       Response: { booking: object, bookingReference: string }

GET    /api/bookings
       Headers: Authorization: Bearer {token}
       Query: status, page, limit
       Response: { bookings: array, pagination: object }

GET    /api/bookings/:bookingId
       Headers: Authorization: Bearer {token}
       Response: { booking: object }

PUT    /api/bookings/:bookingId/cancel
       Headers: Authorization: Bearer {token}
       Response: { success: boolean, refundAmount: number }
```

### 6.4 User Profile APIs
```
GET    /api/users/profile
       Headers: Authorization: Bearer {token}
       Response: { user: object }

PUT    /api/users/profile
       Headers: Authorization: Bearer {token}
       Body: { fullName: string, email: string }
       Response: { user: object }
```

### 6.5 Station APIs
```
GET    /api/stations
       Query: search (optional)
       Response: { stations: array }
```

## 7. Mobile Application Structure

### 8.1 Screens/Pages

```
├── Authentication
│   ├── Login Screen (Mobile Number Entry)
│   ├── OTP Verification Screen
│   └── Splash Screen
│
├── Home
│   ├── Home Screen (Location & Date Range Search)
│   └── Featured / Promotions / Loyalty Summary
│
├── Hotel Search & Booking
│   ├── Search Results (Hotel Cards)
│   ├── Hotel Details (Rooms, Amenities, Photos)
│   ├── Room Type Selection & Dynamic Pricing View
│   ├── Guest & Pre‑Service Selection Screen
│   └── Booking Confirmation / Deposit Payment Screen
│
├── My Stays / Bookings
│   ├── Bookings List (Upcoming / In-Stay / Past / Cancelled)
│   └── Booking Details (Room, Services, Invoice, Checkout)
│
├── Profile
│   ├── Profile Screen
│   ├── Active Sessions Screen
│   └── Settings Screen
│
├── Services
│   ├── Available Services List (filter by category)
│   ├── Service Request Screen (schedule, quantity)
│   └── Running Bill / Invoice Screen
│
├── Checkout
│   ├── Review Charges Screen
│   ├── Payment Method Selection
│   └── Confirmation / Receipt Screen
│
└── Common
  ├── Error Screen
  ├── No Internet Screen
  └── Maintenance / Room Locked Screen
```

### 8.2 Folder Structure (Flutter Example)

```
lib/
├── main.dart
├── core/
│   ├── constants/
│   │   ├── api_constants.dart
│   │   ├── app_constants.dart
│   │   └── route_constants.dart
│   ├── network/
│   │   ├── api_client.dart
│   │   ├── interceptors.dart
│   │   └── network_info.dart
│   ├── storage/
│   │   └── secure_storage.dart
│   ├── error/
│   │   ├── exceptions.dart
│   │   └── failures.dart
│   └── utils/
│       ├── validators.dart
│       ├── formatters.dart
│       └── date_utils.dart
│
├── features/
│   ├── authentication/
│   │   ├── data/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── datasources/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── repositories/
│   │   │   └── usecases/
│   │   └── presentation/
│   │       ├── providers/
│   │       ├── screens/
│   │       └── widgets/
│   │
│   ├── home/
│   │   └── [same structure]
│   │
│   ├── hotels/
│   │   └── [same structure]
│   │
│   ├── bookings/
│   ├── services/
│   ├── invoice/
│   ├── payments/
│   │   └── [same structure]
│   │
│   └── profile/
│       └── [same structure]
│
├── shared/
│   ├── widgets/
│   │   ├── custom_button.dart
│   │   ├── custom_text_field.dart
│   │   ├── loading_indicator.dart
│   │   └── error_widget.dart
│   └── theme/
│       ├── app_theme.dart
│       └── app_colors.dart
│
└── routes/
    └── app_router.dart
```

## 9. Key Features Implementation

### 9.1 Secure Token Storage
```dart
// Flutter Example
class SecureStorageService {
  final FlutterSecureStorage _storage = FlutterSecureStorage();

  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }
}
```

### 9.2 API Interceptor with Token Refresh
```dart
// Flutter Example
class AuthInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await secureStorage.read(key: 'access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioError err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Token expired, try to refresh
      final refreshed = await refreshToken();
      if (refreshed) {
        // Retry the request
        return handler.resolve(await retry(err.requestOptions));
      }
    }
    handler.next(err);
  }
}
```

### 9.3 Session & Booking State (Extended)
```dart
class BookingState {
  final Booking? activeBooking;
  final Invoice? currentInvoice;
  final List<BookingService> pendingServices;
  final bool loading;
  BookingState({
    this.activeBooking,
    this.currentInvoice,
    this.pendingServices = const [],
    this.loading = false,
  });
}
```
```dart
// Flutter Example using Riverpod
class SessionState {
  final bool isAuthenticated;
  final User? user;
  final String? accessToken;
  final List<Session> activeSessions;

  SessionState({
    this.isAuthenticated = false,
    this.user,
    this.accessToken,
    this.activeSessions = const [],
  });
}
```

## 10. Security & Concurrency Considerations

### 10.1 Mobile App Security
- **SSL Pinning**: Implement certificate pinning to prevent MITM attacks
- **Code Obfuscation**: Obfuscate code during release builds
- **Root/Jailbreak Detection**: Detect and warn on compromised devices
- **Secure Storage**: Use platform-specific secure storage (Keychain/Keystore)
- **API Key Protection**: Never hardcode API keys, use environment variables
- **Input Validation**: Validate all user inputs on client and server

### 10.2 Backend Security & Concurrency
- **Room Inventory Locking**: Short-lived Redis locks preventing double allocation
- **Idempotent Booking Endpoint**: Client passes idempotency key to ensure single booking per attempt
- **Service Request Rate Limiting**: Avoid spam service creation
- **Payment Webhook Verification**: Signature & timestamp validation
- **PII Protection**: Guest documents encrypted at rest (column-level encryption)
- **Data Minimization**: Only essential guest data stored
- **Rate Limiting**: Implement rate limiting on OTP requests (max 3 per 30 min)
- **HTTPS Only**: Enforce HTTPS for all API communications
- **CORS Configuration**: Restrict CORS to mobile app origins only
- **SQL Injection Prevention**: Use parameterized queries
- **JWT Security**: Short-lived access tokens, secure refresh token storage
- **OTP Security**: 
  - 6-digit random OTP
  - 5-minute expiration
  - Max 3 attempts
  - Rate limit per mobile number

## 11. UI/UX Guidelines

### 11.1 Design Principles
- **Material Design** (Android) and **Human Interface Guidelines** (iOS)
- Responsive design for different screen sizes
- Dark mode support
- Accessibility support (screen readers, font scaling)
- Smooth animations and transitions
- Offline mode indicators

### 11.2 Color Scheme Example (Sample)
```
Primary Color: #1976D2 (Blue)
Secondary Color: #FF6F00 (Orange)
Background: #FFFFFF (Light) / #121212 (Dark)
Success: #4CAF50 (Green)
Error: #F44336 (Red)
Warning: #FFC107 (Amber)
```

### 11.3 Key UI Components
- Availability Calendar (date range picker with price hints)
- Dynamic Pricing Badge (displays discounts/surge)
- Service Category Chips (Transport, Food, Laundry, Leisure)
- Running Bill Card (updates after each service)
- Checkout Summary & Payment Status Timeline
- Loyalty Progress Bar
- Bottom Navigation Bar (Home, My Bookings, Profile)
- Search Card with source/destination/date pickers
- Train Card with details and book button
- Booking Status Timeline
- Session Management Cards

## 12. Testing Strategy

### 12.1 Mobile App Testing
- **Unit Tests**: Test business logic, utilities, validators
- **Widget Tests**: Test individual UI components
- **Integration Tests**: Test complete user flows
- **E2E Tests**: Test app with real backend

### 12.2 Backend Testing
- **Inventory Lock Tests**: Simulate concurrent booking attempts
- **Pricing Engine Tests**: Seasonal & occupancy scenarios
- **Service Lifecycle Tests**: Status transitions & invoice recalculation
- **Payment Webhook Tests**: Replay & signature validation
- **Unit Tests**: Test services, utilities
- **Integration Tests**: Test API endpoints with database
- **Load Tests**: Test concurrent user handling (using JMeter/k6)
- **Security Tests**: Penetration testing, vulnerability scanning

## 13. Deployment Strategy

### 13.1 Mobile App Deployment
- **iOS**: Apple App Store via TestFlight (beta) → Production
- **Android**: Google Play Store via Internal Testing → Production
- **CI/CD**: GitHub Actions / GitLab CI for automated builds
- **Code Signing**: Proper certificate management

### 13.2 Backend Deployment
- Canary releases for pricing/availability service due to revenue sensitivity
- Database migration strategy with backward compatibility (expand then contract)
- **Environment**: Development → Staging → Production
- **Containerization**: Docker images
- **Orchestration**: Kubernetes with auto-scaling
- **Database Migration**: Flyway or Liquibase for version control
- **Blue-Green Deployment**: Zero-downtime deployments

## 14. Monitoring & Analytics

### 14.1 Application Monitoring
- Track conversion funnel (search -> select -> lock -> pay)
- Service usage frequency per category
- Average checkout duration
- **Crash Reporting**: Firebase Crashlytics or Sentry
- **Performance Monitoring**: Firebase Performance or New Relic
- **Analytics**: Firebase Analytics or Mixpanel
- **User Behavior**: Track key user journeys

### 14.2 Backend Monitoring
- Inventory lock contention rate
- Pricing calculation latency
- Payment success/failure ratios
- Service request SLA adherence
- **APM**: Application Performance Monitoring (New Relic, DataDog)
- **Logging**: Centralized logging (ELK Stack or CloudWatch)
- **Metrics**: API response times, error rates, throughput
- **Alerts**: Set up alerts for critical issues

## 15. Future Enhancements

- **Payment Integration Expansion**: BNPL, corporate accounts
- **Push Notifications**: Pre‑stay reminders, upsell targeted services, late checkout offers
- **Room Upgrade Suggestions**: ML-based upsell during booking funnel
- **Dynamic Bundles**: Room + breakfast + spa discount packaging
- **Multi-Currency Support**: FX rate caching & conversion
- **Loyalty Program**: Points accrual & redemption
- **AI Concierge Chat**: Service ordering via conversational interface
- **Early Check-In / Late Checkout**: Dynamic pricing adjustments
- **Smart IoT Integration**: In-room device status & service triggers
- **Staff Admin Portal**: Real-time service queue management

## 16. Development Timeline Estimate

### Phase 1: Foundation (2-3 weeks)
- Auth + OTP + session
- Hotel/location + room type CRUD (seed data)
- Basic search & availability quote (without dynamic pricing)
- Mobile skeleton (Auth, Search, Results)

### Phase 2: Core Features (4-5 weeks)
- Booking flow with inventory locking
- Guest details & invoice generation
- Pre-service booking at reservation time
- Dynamic pricing engine (initial rules)
- Profile & loyalty basics

### Phase 3: Services & In-Stay (2-3 weeks)
- In-stay service ordering & lifecycle
- Running bill updates & invoice adjustments
- Payment integration (Stripe/Razorpay)
- Concurrency & load testing

### Phase 4: Hardening & Deployment (1-2 weeks)
- Security, monitoring dashboards
- App store submissions
- Canary & rollback procedures
- Documentation & runbooks

**Total Estimated Timeline: 9-13 weeks**

## 17. Team Structure Recommendation

- **1 Mobile Developer** (Flutter/React Native)
- **1 Backend Developer** (Node.js/Spring Boot)
- **1 UI/UX Designer**
- **1 QA Engineer**
- **1 DevOps Engineer** (part-time)
- **1 Project Manager** (part-time)

---

## Conclusion

This document outlines a scalable, secure, and extensible hotel room booking ecosystem supporting multi-location search, dynamic room availability, pre & in-stay service ordering, real-time billing, and robust checkout. Concurrency safety (inventory locking, idempotent booking) and modular services (auth, hotel, availability, booking, services, billing/payment) enable future growth (loyalty, AI concierge, dynamic bundles). Flutter recommended for rich cross-platform UX; backend emphasizes clean boundaries, observability, and payment integrity.
