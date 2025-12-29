# Task 10: Testing & Documentation

**Priority:** Critical  
**Estimated Duration:** 4-5 days  
**Dependencies:** ALL Tasks (TASK_01 through TASK_09)  
**Status:** Not Started

---

## Overview

Comprehensive testing strategy implementation and complete system documentation for the MApp user management system.

---

## Objectives

1. Write unit tests for all services and models
2. Create integration tests for API endpoints
3. Implement end-to-end tests for critical workflows
4. Generate API documentation (OpenAPI/Swagger)
5. Write user guides for all user roles
6. Create developer documentation
7. Add code coverage reporting
8. Document deployment procedures

---

## 1. Unit Testing

### Backend Unit Tests

**Test Structure:**

```
tests/
├── __init__.py
├── conftest.py                  # Pytest fixtures
├── unit/
│   ├── test_auth_service.py
│   ├── test_otp_service.py
│   ├── test_session_service.py
│   ├── test_notification_service.py
│   ├── test_vendor_service.py
│   ├── test_admin_service.py
│   └── test_security.py
├── integration/
│   ├── test_auth_api.py
│   ├── test_vendor_api.py
│   ├── test_admin_api.py
│   └── test_booking_flow.py
└── e2e/
    ├── test_guest_journey.py
    ├── test_vendor_onboarding.py
    └── test_employee_workflow.py
```

**File:** `tests/conftest.py`

```python
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.base import Base
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.hotel import Hotel, Location
from datetime import datetime

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests"""
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user"""
    user = User(
        mobile_number="1234567890",
        role=UserRole.GUEST,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def vendor_user(db_session: AsyncSession) -> User:
    """Create test vendor user"""
    user = User(
        mobile_number="9876543210",
        role=UserRole.VENDOR_ADMIN,
        is_active=True,
        vendor_approved=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create test admin user"""
    user = User(
        mobile_number="5555555555",
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def test_location(db_session: AsyncSession) -> Location:
    """Create test location"""
    location = Location(
        city="Test City",
        state="Test State",
        country="Test Country"
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location

@pytest.fixture
async def test_hotel(db_session: AsyncSession, vendor_user: User, test_location: Location) -> Hotel:
    """Create test hotel"""
    hotel = Hotel(
        name="Test Hotel",
        location_id=test_location.id,
        vendor_id=vendor_user.id,
        address="123 Test St",
        star_rating=4,
        is_active=True
    )
    db_session.add(hotel)
    await db_session.commit()
    await db_session.refresh(hotel)
    return hotel
```

**File:** `tests/unit/test_auth_service.py`

```python
import pytest
from app.services.otp_service import OTPService
from app.services.session_service import SessionService
from app.models.user import User, UserRole

@pytest.mark.asyncio
async def test_generate_otp():
    """Test OTP generation"""
    otp_service = OTPService()
    mobile = "1234567890"
    
    otp = await otp_service.generate_otp(mobile)
    
    assert otp is not None
    assert len(otp) == 6
    assert otp.isdigit()

@pytest.mark.asyncio
async def test_verify_otp_valid():
    """Test valid OTP verification"""
    otp_service = OTPService()
    mobile = "1234567890"
    
    otp = await otp_service.generate_otp(mobile)
    result = await otp_service.verify_otp(mobile, otp)
    
    assert result is True

@pytest.mark.asyncio
async def test_verify_otp_invalid():
    """Test invalid OTP verification"""
    otp_service = OTPService()
    mobile = "1234567890"
    
    await otp_service.generate_otp(mobile)
    result = await otp_service.verify_otp(mobile, "000000")
    
    assert result is False

@pytest.mark.asyncio
async def test_otp_expiry():
    """Test OTP expiry"""
    import time
    from app.core.config import settings
    
    otp_service = OTPService()
    mobile = "1234567890"
    
    otp = await otp_service.generate_otp(mobile)
    
    # Wait for expiry
    time.sleep(settings.OTP_EXPIRE_SECONDS + 1)
    
    result = await otp_service.verify_otp(mobile, otp)
    assert result is False

@pytest.mark.asyncio
async def test_create_session(db_session):
    """Test session creation"""
    session_service = SessionService()
    user_id = 1
    
    session_id = await session_service.create_session(
        user_id=user_id,
        device_info="Test Device"
    )
    
    assert session_id is not None
    assert len(session_id) > 20
```

**File:** `tests/unit/test_security.py`

```python
import pytest
from app.core.security import SecurityManager

def test_rate_limiting():
    """Test rate limiting functionality"""
    identifier = "test_user_1"
    
    # First 10 requests should pass
    for i in range(10):
        result = SecurityManager.check_rate_limit(
            identifier, max_requests=10, window_seconds=60
        )
        assert result is True
    
    # 11th request should fail
    result = SecurityManager.check_rate_limit(
        identifier, max_requests=10, window_seconds=60
    )
    assert result is False

def test_failed_login_attempts():
    """Test failed login tracking"""
    identifier = "attacker_ip"
    
    # Record 5 failed attempts
    for i in range(5):
        count = SecurityManager.record_failed_login(identifier)
    
    assert count == 5
    assert SecurityManager.is_blocked(identifier) is True

def test_input_sanitization():
    """Test XSS prevention"""
    malicious_input = "<script>alert('XSS')</script>"
    sanitized = SecurityManager.sanitize_input(malicious_input)
    
    assert "<script>" not in sanitized
    assert "alert" in sanitized  # Content preserved but escaped

def test_mobile_validation():
    """Test mobile number validation"""
    assert SecurityManager.validate_mobile_number("1234567890") is True
    assert SecurityManager.validate_mobile_number("123") is False
    assert SecurityManager.validate_mobile_number("abc1234567") is False

def test_email_validation():
    """Test email validation"""
    assert SecurityManager.validate_email("test@example.com") is True
    assert SecurityManager.validate_email("invalid-email") is False
    assert SecurityManager.validate_email("test@") is False
```

---

## 2. Integration Testing

**File:** `tests/integration/test_auth_api.py`

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_send_otp_success():
    """Test OTP send endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "1234567890"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["expires_in"] == 600

@pytest.mark.asyncio
async def test_send_otp_invalid_mobile():
    """Test OTP send with invalid mobile"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "123"}
        )
    
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_verify_otp_success():
    """Test OTP verification endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Send OTP
        await client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "1234567890"}
        )
        
        # Verify OTP (use fixed OTP in test mode)
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "mobile_number": "1234567890",
                "otp": "123456",  # Test OTP
                "device_info": "Test Device"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data

@pytest.mark.asyncio
async def test_refresh_token():
    """Test token refresh endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get initial tokens
        verify_response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "mobile_number": "1234567890",
                "otp": "123456",
                "device_info": "Test Device"
            }
        )
        refresh_token = verify_response.json()["refresh_token"]
        
        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh-token",
            json={"refresh_token": refresh_token}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
```

**File:** `tests/e2e/test_guest_journey.py`

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_complete_guest_journey():
    """Test complete guest booking journey"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Send OTP
        otp_response = await client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "9999999999"}
        )
        assert otp_response.status_code == 200
        
        # 2. Verify OTP and login
        verify_response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "mobile_number": "9999999999",
                "otp": "123456",
                "device_info": "Test Device"
            }
        )
        assert verify_response.status_code == 200
        access_token = verify_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 3. Search hotels
        search_response = await client.get(
            "/api/v1/hotels/search",
            params={"location_id": 1},
            headers=headers
        )
        assert search_response.status_code == 200
        
        # 4. Create booking
        booking_response = await client.post(
            "/api/v1/bookings",
            json={
                "hotel_id": 1,
                "room_type_id": 1,
                "checkin_date": "2025-01-15",
                "checkout_date": "2025-01-17",
                "guest_details": {
                    "full_name": "Test Guest",
                    "email": "test@example.com",
                    "mobile": "9999999999"
                }
            },
            headers=headers
        )
        assert booking_response.status_code == 201
        booking_id = booking_response.json()["id"]
        
        # 5. View running bill
        bill_response = await client.get(
            f"/api/v1/invoices/booking/{booking_id}",
            headers=headers
        )
        assert bill_response.status_code == 200
```

---

## 3. Code Coverage

**File:** `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

# Coverage settings
addopts = 
    --cov=app
    --cov-report=html
    --cov-report=term
    --cov-fail-under=80
```

**Run tests with coverage:**

```bash
# Install pytest and coverage
pip install pytest pytest-asyncio pytest-cov httpx

# Run tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html
```

---

## 4. API Documentation

### OpenAPI/Swagger

**Update:** `app/main.py`

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="MApp Hotel Booking API",
    description="""
    ## MApp API Documentation
    
    Complete hotel booking and management platform with user management.
    
    ### Features
    
    * **Authentication**: Mobile OTP-based authentication
    * **User Roles**: Guest, Hotel Employee, Vendor Admin, System Admin
    * **Booking**: Search, book, and manage hotel stays
    * **Services**: Order in-stay services
    * **Vendor Management**: Manage hotels and employees
    * **Admin Dashboard**: Platform management and analytics
    
    ### Authentication
    
    Most endpoints require authentication. Use the `/auth/send-otp` and 
    `/auth/verify-otp` endpoints to obtain access tokens.
    
    Include the access token in the `Authorization` header:
    ```
    Authorization: Bearer <access_token>
    ```
    """,
    version="1.0.0",
    contact={
        "name": "MApp Support",
        "email": "support@mapp.com",
    },
    license_info={
        "name": "Proprietary",
    },
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="MApp API",
        version="1.0.0",
        description="Hotel booking and management platform",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

**Generate static API docs:**

```bash
# Export OpenAPI JSON
curl http://localhost:8000/openapi.json > docs/api/openapi.json

# Generate Markdown docs
pip install openapi-spec-validator openapi-cli-tool
openapi-cli bundle docs/api/openapi.json --output docs/api/api-docs.md
```

---

## 5. User Documentation

### Guest User Guide

**File:** `docs/user-guides/GUEST_USER_GUIDE.md`

```markdown
# MApp Guest User Guide

## Getting Started

### 1. Registration & Login

1. Open the MApp mobile app
2. Enter your mobile number
3. Tap "Send OTP"
4. Enter the 6-digit OTP received via SMS
5. Tap "Verify"

### 2. Searching for Hotels

1. Tap "Search Hotels" from the dashboard
2. Select your destination
3. Choose check-in and check-out dates
4. Select number of guests
5. Tap "Search"
6. Browse available hotels

### 3. Making a Booking

1. Select a hotel from search results
2. Choose room type
3. Review pricing
4. Tap "Book Now"
5. Enter guest details
6. Confirm booking
7. Receive booking confirmation

### 4. Managing Your Stay

#### Viewing Running Bill
- Tap "Running Bill" from dashboard
- View all charges (room, services, taxes)
- Total amount updates in real-time

#### Ordering Services
- Tap "Order Services"
- Browse available services (food, laundry, etc.)
- Add items to cart
- Place order
- Services added to your bill

### 5. Payment & Checkout

1. At checkout, review final bill
2. Choose payment method
3. Complete payment
4. Download invoice

## FAQ

**Q: How do I cancel a booking?**
A: Contact the hotel directly or use the "Cancel Booking" option in your booking details.

**Q: When will I be charged?**
A: Payment is typically processed at checkout, unless hotel policy specifies otherwise.
```

### Vendor User Guide

**File:** `docs/user-guides/VENDOR_USER_GUIDE.md`

```markdown
# MApp Vendor Admin Guide

## Getting Started

### 1. Becoming a Vendor

1. Login to MApp
2. Go to Settings → "Become a Vendor"
3. Fill in business details
4. Submit application
5. Wait for admin approval (1-2 business days)

### 2. Adding Your First Hotel

1. After approval, go to "Add Hotel"
2. Enter hotel details:
   - Name
   - Location
   - Address
   - Star rating
   - Amenities
3. Upload hotel photos
4. Submit for review

### 3. Managing Employees

#### Inviting Employees
1. Go to "Employees" → "Invite Employee"
2. Enter employee mobile number
3. Select role (Manager, Receptionist, Housekeeping, Maintenance)
4. Set permissions
5. Send invitation
6. Employee receives SMS with invitation link

#### Managing Employee Permissions
- View all employees
- Edit employee roles
- Deactivate/activate employee access

### 4. Subscription Management

#### Viewing Subscription Status
- Dashboard shows current subscription status
- Days remaining until expiry
- Renewal options

#### Renewing Subscription
1. Go to "Subscription"
2. Choose renewal plan
3. Complete payment
4. Subscription extended automatically

### 5. Analytics & Reports

- View booking statistics
- Revenue reports
- Occupancy rates
- Customer feedback
```

---

## 6. Developer Documentation

**File:** `docs/developer/DEVELOPMENT_GUIDE.md`

```markdown
# MApp Development Guide

## Setup

### Backend Setup

```bash
# Clone repository
git clone https://github.com/yourorg/mapp.git
cd mapp/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Seed data
python scripts/seed_data.py

# Run server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd mapp/mobile

# Install dependencies
flutter pub get

# Run app
flutter run
```

## Architecture

### Backend Architecture
- Framework: FastAPI (async)
- Database: PostgreSQL with SQLAlchemy ORM
- Cache: Redis
- Authentication: JWT tokens
- OTP: Redis-based storage

### Frontend Architecture
- Framework: Flutter
- State Management: Riverpod
- HTTP Client: Dio
- Storage: flutter_secure_storage

## API Endpoints

See [API Documentation](../api/README.md) for complete endpoint reference.

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_auth_service.py

# Run with coverage
pytest --cov=app --cov-report=html
```

## Deployment

See [Deployment Guide](DEPLOYMENT_GUIDE.md)
```

---

## 7. Test Automation

**File:** `.github/workflows/tests.yml`

```yaml
name: Run Tests

on:
  push:
    branches: [ main, development ]
  pull_request:
    branches: [ main, development ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml --cov-report=term
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
```

---

## Acceptance Criteria

- [ ] Unit tests cover all services (80%+ coverage)
- [ ] Integration tests for all API endpoints
- [ ] E2E tests for critical user journeys
- [ ] API documentation complete (OpenAPI/Swagger)
- [ ] User guides for all roles
- [ ] Developer documentation complete
- [ ] Test automation CI/CD pipeline
- [ ] Code coverage reports generated
- [ ] All tests passing
- [ ] Documentation reviewed and approved

---

## Deliverables

1. **Test Suite**
   - 100+ unit tests
   - 50+ integration tests
   - 10+ E2E tests
   - 80%+ code coverage

2. **API Documentation**
   - OpenAPI/Swagger spec
   - Postman collection
   - API reference guide

3. **User Guides**
   - Guest user guide
   - Hotel employee guide
   - Vendor admin guide
   - System admin guide

4. **Developer Documentation**
   - Setup guide
   - Architecture overview
   - API development guide
   - Deployment guide
   - Contributing guide

---

**Project Status:** READY FOR PRODUCTION ✅
