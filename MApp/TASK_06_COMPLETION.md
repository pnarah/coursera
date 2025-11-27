# Task 06: Database Schema & Migrations - COMPLETED ✅

## Overview
Successfully implemented database schema with Alembic migrations and seeded initial data for the hotel booking platform.

## Completed Work

### 1. Database Models (SQLAlchemy ORM)
Created comprehensive models in `app/models/hotel.py`:

- **User Model**: Authentication and user management
  - Fields: mobile_number, country_code, email, full_name, role (GUEST/ADMIN/STAFF)
  - Relationships: bookings (one-to-many)
  
- **Location Model**: Geographic locations for hotels
  - Fields: country, state, city, postal_code, timezone
  - Relationships: hotels (one-to-many)
  
- **Hotel Model**: Hotel properties and details
  - Fields: name, description, address, lat/long, star_rating, contact info, check-in/out times
  - Relationships: location (many-to-one), rooms, services (one-to-many)
  
- **Room Model**: Hotel room inventory
  - Fields: room_number, room_type (SINGLE/DOUBLE/DELUXE/SUITE/FAMILY), capacity, base_price, amenities
  - Relationships: hotel (many-to-one), bookings (one-to-many)
  
- **Booking Model**: Guest reservations
  - Fields: check_in/out dates, guest details, total_amount, status (PENDING/CONFIRMED/CHECKED_IN/CHECKED_OUT/CANCELLED)
  - Relationships: user, room, service_orders (many-to-one for user/room, one-to-many for service_orders)
  
- **Service Model**: Hotel services catalog
  - Fields: name, service_type (CAB_PICKUP/FOOD/LAUNDRY/LEISURE/ROOM_SERVICE), description, price
  - Relationships: hotel (many-to-one), service_orders (one-to-many)
  
- **ServiceOrder Model**: Booking service orders
  - Fields: quantity, total_price, status
  - Relationships: booking, service (many-to-one)

### 2. Alembic Migration Setup
- Initialized Alembic: `alembic/` directory structure created
- Configured async SQLAlchemy support in `alembic/env.py`
- Updated `alembic.ini` with database connection: `postgresql+asyncpg://mapp_user:mapp_password@localhost:5432/mapp_hotel_booking`
- Generated initial migration: `7cdbabc3c4cb_initial_hotel_booking_schema.py`
- Applied migration: Created all tables with proper indexes and foreign keys

### 3. Database Seeding
Created `scripts/seed_data.py` with comprehensive seed data:

**Seeded Data Summary:**
- **5 Locations**: New York City, Los Angeles, Chicago, Miami, Seattle
- **7 Hotels**: Mix of 3-star, 4-star, and 5-star properties across all locations
  - Grand Manhattan Hotel (NYC - 5★)
  - Times Square Inn (NYC - 3★)
  - Hollywood Luxury Suites (LA - 5★)
  - Santa Monica Beach Resort (LA - 4★)
  - Magnificent Mile Hotel (Chicago - 4★)
  - South Beach Paradise (Miami - 5★)
  - Pike Place Boutique Hotel (Seattle - 4★)
  
- **161 Rooms**: Each hotel has 23 rooms with varied types:
  - 5 Single rooms (capacity: 1)
  - 8 Double rooms (capacity: 2)
  - 5 Deluxe rooms (capacity: 2)
  - 3 Suites (capacity: 4)
  - 2 Family rooms (capacity: 5)
  - Prices adjusted by star rating (3★: $100 base, 4★: $150 base, 5★: $250 base)
  
- **69 Services**: 10 service types per hotel (9 for 3-star hotels)
  - Airport Pickup (CAB_PICKUP)
  - Breakfast/Lunch/Dinner (FOOD)
  - Laundry Service
  - Spa Treatment (4★ & 5★ only)
  - Gym & Pool Access (LEISURE)
  - Room Service & Extra Cleaning
  - Prices adjusted by star rating

## Database Schema Features
- ✅ All tables with proper primary keys and auto-increment IDs
- ✅ Foreign key relationships with cascade rules
- ✅ Indexes on frequently queried columns (email, mobile_number, check-in/out dates, status)
- ✅ Enum types for type safety (UserRole, RoomType, BookingStatus, ServiceType, ServiceOrderStatus)
- ✅ Timestamp fields (created_at, updated_at) with automatic values
- ✅ JSON field for room amenities
- ✅ Soft delete support with is_active flags

## Files Created/Modified
```
backend/
├── alembic/
│   ├── versions/
│   │   └── 7cdbabc3c4cb_initial_hotel_booking_schema.py
│   ├── env.py (configured for async)
│   └── README
├── alembic.ini (configured with DB URL)
├── app/
│   └── models/
│       └── hotel.py (8 models, 5 enums)
└── scripts/
    └── seed_data.py
```

## Verification Commands
```bash
# Check migration status
alembic current

# View migration history
alembic history

# Verify data
docker exec mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "
  SELECT 'Locations' as table_name, COUNT(*) as count FROM locations
  UNION ALL
  SELECT 'Hotels', COUNT(*) FROM hotels
  UNION ALL
  SELECT 'Rooms', COUNT(*) FROM rooms
  UNION ALL
  SELECT 'Services', COUNT(*) FROM services;
"

# View sample hotel data
docker exec mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "
  SELECT h.name, h.star_rating, l.city, COUNT(r.id) as total_rooms
  FROM hotels h
  JOIN locations l ON h.location_id = l.id
  LEFT JOIN rooms r ON r.hotel_id = h.id
  GROUP BY h.id, h.name, h.star_rating, l.city
  ORDER BY h.star_rating DESC, h.name;
"
```

## Next Steps (Task 07)
Task 07 will implement:
- Room type management APIs
- Room availability checking algorithms
- Room inventory endpoints
- Room filtering and search

## Notes
- Database is production-ready with proper migrations
- Seed script is idempotent (can be run multiple times safely)
- All foreign key relationships are properly defined
- Indexes are strategically placed for query optimization
- Async SQLAlchemy operations throughout
