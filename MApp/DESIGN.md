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
- **Framework**: FastAPI (Python 3.11+)
  - **Why FastAPI**: Native async/await support, automatic OpenAPI docs, Pydantic validation, high performance, excellent for microservices
  - **Alternative considerations**: NestJS (TypeScript) for JS-heavy teams, Spring Boot (Java) for enterprise
- **ORM**: SQLAlchemy 2.0 with async support (asyncpg driver for PostgreSQL)
- **Primary Database**: PostgreSQL 15+ (users, hotels, rooms, bookings, services, invoices, payments)
- **Cache/Session/Locking**: Redis 7+ (OTP, sessions, room availability locks, rate limiting)
- **Redis Client**: redis-py with async support or aioredis
- **Search Layer (Optional Phase 2)**: Elasticsearch for full‑text hotel search & geo queries
- **Authentication**: JWT (access + refresh) using python-jose + Redis session context
- **OTP Delivery**: Twilio SMS API / AWS SNS via boto3
- **Payment Gateway**: Stripe SDK / Razorpay SDK (India) / Adyen SDK integrated with Payments Service
- **API Documentation**: Auto-generated OpenAPI/Swagger via FastAPI
- **Dependency Injection**: FastAPI's native Depends() system
- **Background Tasks**: FastAPI BackgroundTasks + Celery with Redis broker for heavy async work
- **Migration Tool**: Alembic for database schema versioning
- **Validation**: Pydantic v2 for request/response models and configuration

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
- **Pattern**: Clean Architecture / Layered Architecture adapted for FastAPI
- **FastAPI Project Structure**:
  ```
  backend/
  ├── alembic/                    # Database migrations
  ├── app/
  │   ├── main.py                 # FastAPI app instance, middleware, CORS
  │   ├── core/
  │   │   ├── config.py           # Pydantic Settings management
  │   │   ├── security.py         # JWT, password hashing
  │   │   ├── dependencies.py     # Common dependencies (DB, Redis, current user)
  │   │   └── exceptions.py       # Custom exception handlers
  │   ├── db/
  │   │   ├── base.py             # SQLAlchemy declarative base
  │   │   ├── session.py          # Async session factory
  │   │   └── redis.py            # Redis connection pool
  │   ├── models/                 # SQLAlchemy ORM models
  │   │   ├── user.py
  │   │   ├── hotel.py
  │   │   ├── booking.py
  │   │   └── ...
  │   ├── schemas/                # Pydantic schemas (request/response)
  │   │   ├── user.py
  │   │   ├── hotel.py
  │   │   └── ...
  │   ├── api/                    # API routes organized by domain
  │   │   ├── v1/
  │   │   │   ├── auth.py
  │   │   │   ├── hotels.py
  │   │   │   ├── bookings.py
  │   │   │   ├── services.py
  │   │   │   └── payments.py
  │   ├── services/               # Business logic layer
  │   │   ├── auth_service.py
  │   │   ├── otp_service.py
  │   │   ├── hotel_service.py
  │   │   ├── availability_service.py
  │   │   ├── pricing_service.py
  │   │   ├── booking_service.py
  │   │   ├── invoice_service.py
  │   │   └── payment_service.py
  │   ├── repositories/           # Data access layer
  │   │   ├── user_repository.py
  │   │   ├── hotel_repository.py
  │   │   └── ...
  │   └── utils/
  │       ├── otp.py
  │       ├── redis_locks.py      # Distributed locking utilities
  │       └── validators.py
  ├── tests/
  ├── requirements.txt
  └── pyproject.toml
  ```
- **Layers**:
  - **API Layer** (FastAPI routers): Request validation, response serialization
  - **Service Layer**: Business logic, orchestration, transaction management
  - **Repository Layer**: Database queries, data access patterns
  - **Model Layer**: SQLAlchemy ORM models, database schema

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

## 6A. FastAPI Implementation Complexity & Best Practices

### 6A.1 Complexity Areas & Solutions

#### **1. Async Database Operations with SQLAlchemy**
**Challenge**: SQLAlchemy 2.0 async requires careful session management and proper async context handling.

**Solution**:
```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

**Key Points**:
- Use `asyncpg` driver (not psycopg2)
- Always use `async with` for sessions
- Set `expire_on_commit=False` to avoid lazy-loading issues
- Use `await session.execute()` for queries, not `.query()`

#### **2. Redis Distributed Locking for Inventory**
**Challenge**: Preventing race conditions during concurrent booking attempts requires atomic operations.

**Solution**:
```python
# app/utils/redis_locks.py
import asyncio
from redis.asyncio import Redis
from typing import Optional
import uuid

class RedisLock:
    def __init__(self, redis: Redis, key: str, timeout: int = 120):
        self.redis = redis
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.token = str(uuid.uuid4())
    
    async def __aenter__(self):
        while True:
            acquired = await self.redis.set(
                self.key, 
                self.token, 
                nx=True, 
                ex=self.timeout
            )
            if acquired:
                return self
            await asyncio.sleep(0.1)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Lua script ensures atomic delete only if we own the lock
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(lua_script, 1, self.key, self.token)

# Usage in availability service
async def lock_inventory(hotel_id, room_type_id, date_range):
    lock_key = f"hotel:{hotel_id}:room_type:{room_type_id}"
    async with RedisLock(redis_client, lock_key, timeout=120):
        # Check availability
        # Decrement inventory
        # Create booking
        pass
```

**Complexity**: Requires Lua scripting for atomic operations and proper timeout handling.

#### **3. Transaction Management with Multiple Services**
**Challenge**: Booking creation involves multiple tables (booking, guests, booking_services, invoice) and must be atomic.

**Solution**:
```python
# app/services/booking_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class BookingService:
    async def create_booking(
        self,
        db: AsyncSession,
        redis: Redis,
        booking_data: BookingCreate,
        user_id: UUID
    ) -> Booking:
        async with db.begin():  # Transaction context
            # 1. Validate lock
            lock_key = f"lock:{booking_data.hotel_id}:{booking_data.room_type_id}"
            lock_exists = await redis.exists(lock_key)
            if not lock_exists:
                raise LockExpiredException()
            
            # 2. Create booking
            booking = Booking(**booking_data.dict(), user_id=user_id)
            db.add(booking)
            await db.flush()  # Get booking.id without committing
            
            # 3. Add guests
            for guest_data in booking_data.guests:
                guest = Guest(**guest_data.dict(), booking_id=booking.id)
                db.add(guest)
            
            # 4. Add pre-services
            for service in booking_data.pre_services:
                bs = BookingService(
                    booking_id=booking.id,
                    service_id=service.service_id,
                    quantity=service.quantity
                )
                db.add(bs)
            
            # 5. Create invoice
            invoice = await self.invoice_service.generate_invoice(db, booking.id)
            db.add(invoice)
            
            # 6. Release lock
            await redis.delete(lock_key)
            
            # Transaction commits here automatically
            return booking
```

**Complexity**: Managing transaction boundaries with async, handling rollback on failure, coordinating Redis and DB state.

#### **4. JWT + Redis Session Hybrid**
**Challenge**: Maintaining stateless JWT with stateful session revocation capability.

**Solution**:
```python
# app/core/security.py
from jose import jwt, JWTError
from datetime import datetime, timedelta

async def create_access_token(user_id: UUID, session_id: str) -> str:
    payload = {
        "sub": str(user_id),
        "session_id": session_id,
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "type": "access"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

async def verify_token(token: str, redis: Redis) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        
        # Check if session exists in Redis
        session_key = f"session:{user_id}:{session_id}"
        session_exists = await redis.exists(session_key)
        if not session_exists:
            raise SessionRevokedException()
        
        # Check token blacklist
        blacklisted = await redis.exists(f"blacklist:{token}")
        if blacklisted:
            raise TokenBlacklistedException()
        
        return payload
    except JWTError:
        raise InvalidTokenException()

# Dependency for protected routes
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> User:
    payload = await verify_token(token, redis)
    user = await db.get(User, UUID(payload["sub"]))
    if not user:
        raise UserNotFoundException()
    return user
```

**Complexity**: Double validation (JWT signature + Redis session), blacklist management, refresh token rotation.

#### **5. Background Task Orchestration**
**Challenge**: Some operations (OTP sending, invoice PDF generation, payment webhook processing) should be async.

**Solution**:
```python
# For lightweight tasks - FastAPI BackgroundTasks
from fastapi import BackgroundTasks

@router.post("/auth/send-otp")
async def send_otp(
    data: OTPRequest,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis)
):
    otp = generate_otp()
    await redis.setex(f"otp:{data.mobile_number}", 300, otp)
    
    # Send SMS in background
    background_tasks.add_task(send_sms_via_twilio, data.mobile_number, otp)
    
    return {"success": True}

# For heavy/scheduled tasks - Celery
# app/tasks/celery_app.py
from celery import Celery

celery_app = Celery(
    "hotel_booking",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task
def generate_invoice_pdf(booking_id: str):
    # Long-running PDF generation
    pass

@celery_app.task
def send_booking_confirmation_email(booking_id: str):
    pass

# Usage in endpoint
@router.post("/bookings/{booking_id}/checkout")
async def checkout(booking_id: UUID):
    # ... process checkout ...
    generate_invoice_pdf.delay(str(booking_id))
    return {"status": "completed"}
```

**Complexity**: Choosing between BackgroundTasks vs Celery, managing Celery workers, error handling in async tasks.

#### **6. Pydantic Model Complexity**
**Challenge**: Complex validation rules for nested booking data, date ranges, pricing calculations.

**Solution**:
```python
# app/schemas/booking.py
from pydantic import BaseModel, validator, Field
from datetime import date, timedelta
from typing import List, Optional

class GuestCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=0, le=150)
    gender: Optional[str]
    id_doc_type: Optional[str]
    id_doc_number: Optional[str]

class PreServiceCreate(BaseModel):
    service_id: UUID
    quantity: int = Field(default=1, ge=1)
    scheduled_for: Optional[datetime]

class BookingCreate(BaseModel):
    hotel_id: UUID
    room_type_id: UUID
    checkin_date: date
    checkout_date: date
    num_rooms: int = Field(default=1, ge=1, le=10)
    num_guests: int = Field(..., ge=1)
    guests: List[GuestCreate]
    pre_services: List[PreServiceCreate] = []
    
    @validator('checkout_date')
    def checkout_after_checkin(cls, v, values):
        if 'checkin_date' in values and v <= values['checkin_date']:
            raise ValueError('Checkout must be after checkin')
        return v
    
    @validator('checkin_date')
    def checkin_not_past(cls, v):
        if v < date.today():
            raise ValueError('Cannot book dates in the past')
        return v
    
    @validator('guests')
    def validate_guest_count(cls, v, values):
        if 'num_guests' in values and len(v) != values['num_guests']:
            raise ValueError('Guest count mismatch')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "hotel_id": "123e4567-e89b-12d3-a456-426614174000",
                "room_type_id": "223e4567-e89b-12d3-a456-426614174000",
                "checkin_date": "2025-12-01",
                "checkout_date": "2025-12-05",
                "num_rooms": 1,
                "num_guests": 2,
                "guests": [
                    {"name": "John Doe", "age": 30, "gender": "M"},
                    {"name": "Jane Doe", "age": 28, "gender": "F"}
                ]
            }
        }
```

**Complexity**: Custom validators, nested validation, maintaining sync between ORM models and Pydantic schemas.

#### **7. Database Query Optimization**
**Challenge**: N+1 query problems, eager loading relationships, pagination.

**Solution**:
```python
# app/repositories/hotel_repository.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload

class HotelRepository:
    async def get_hotels_with_rooms(
        self,
        db: AsyncSession,
        city: str,
        checkin: date,
        checkout: date,
        skip: int = 0,
        limit: int = 20
    ):
        # Eager load relationships to avoid N+1
        stmt = (
            select(Hotel)
            .join(Hotel.location)
            .options(
                selectinload(Hotel.room_types),
                selectinload(Hotel.location)
            )
            .where(Location.city == city)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_available_room_count(
        self,
        db: AsyncSession,
        hotel_id: UUID,
        room_type_id: UUID,
        checkin: date,
        checkout: date
    ) -> int:
        # Complex query to check overlapping bookings
        stmt = select(func.count(Room.id)).where(
            Room.hotel_id == hotel_id,
            Room.room_type_id == room_type_id,
            Room.status == 'AVAILABLE',
            ~Room.id.in_(
                select(Booking.room_id).where(
                    or_(
                        and_(
                            Booking.checkin_date <= checkin,
                            Booking.checkout_date > checkin
                        ),
                        and_(
                            Booking.checkin_date < checkout,
                            Booking.checkout_date >= checkout
                        )
                    ),
                    Booking.booking_status.in_(['CONFIRMED', 'COMPLETED'])
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()
```

**Complexity**: Understanding SQLAlchemy 2.0 select() API, relationship loading strategies, avoiding implicit async issues.

### 6A.2 Testing Complexity

#### **Async Test Setup**
```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import AsyncClient

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test_db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# tests/test_booking.py
@pytest.mark.asyncio
async def test_create_booking(client, db_session):
    response = await client.post("/api/bookings", json={...})
    assert response.status_code == 201
```

**Complexity**: Managing async fixtures, test database lifecycle, mocking Redis, isolating tests.

### 6A.3 Performance Considerations

**Connection Pooling**:
- PostgreSQL: Pool size 20-50 (adjust based on load)
- Redis: Connection pool with min 10, max 50

**Caching Strategy**:
- Hotel metadata: Cache for 1 hour
- Room availability: Cache for 5 minutes with invalidation on booking
- User sessions: 7-day TTL in Redis

**API Rate Limiting**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/send-otp")
@limiter.limit("3/30minutes")
async def send_otp(request: Request):
    pass
```

### 6A.4 When FastAPI Becomes Complex

**Use Cases Where FastAPI Shines**:
- ✅ High I/O workloads (database, API calls)
- ✅ Microservices with async communication
- ✅ Real-time features (WebSocket support)
- ✅ Rapid prototyping with auto docs
- ✅ Data validation heavy applications

**Potential Challenges**:
- ⚠️ Async learning curve for team unfamiliar with Python async
- ⚠️ SQLAlchemy async support still maturing (less ecosystem)
- ⚠️ Debugging async code can be harder
- ⚠️ Less enterprise tooling compared to Spring Boot
- ⚠️ Type hints improve experience but add verbosity

**Mitigation**:
- Invest in team training on async/await patterns
- Use structured logging with correlation IDs
- Leverage FastAPI's dependency injection for testability
- Use Pydantic for runtime validation (catches many errors early)

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
- **1 Backend Developer** (FastAPI/Python)
- **1 UI/UX Designer**
- **1 QA Engineer**
- **1 DevOps Engineer** (part-time)
- **1 Project Manager** (part-time)

---

## Conclusion

This document outlines a scalable, secure, and extensible hotel room booking ecosystem supporting multi-location search, dynamic room availability, pre & in-stay service ordering, real-time billing, and robust checkout. Concurrency safety (inventory locking, idempotent booking) and modular services (auth, hotel, availability, booking, services, billing/payment) enable future growth (loyalty, AI concierge, dynamic bundles). Flutter recommended for rich cross-platform UX; backend emphasizes clean boundaries, observability, and payment integrity.
