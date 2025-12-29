# FastAPI Implementation Patterns for Hotel Booking System

## Quick Reference Guide

### 1. Async Database Session Pattern

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/hotel_booking"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True  # Verify connections before use
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Important for async
    autoflush=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Usage in routes**:
```python
@router.get("/hotels/{hotel_id}")
async def get_hotel(
    hotel_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(404, "Hotel not found")
    return hotel
```

---

### 2. Redis Connection Pool Pattern

```python
# app/db/redis.py
from redis.asyncio import Redis, ConnectionPool

redis_pool = ConnectionPool.from_url(
    "redis://localhost:6379/0",
    decode_responses=True,
    max_connections=50
)

async def get_redis() -> Redis:
    redis = Redis(connection_pool=redis_pool)
    try:
        yield redis
    finally:
        await redis.close()
```

**Usage**:
```python
@router.post("/auth/send-otp")
async def send_otp(
    data: OTPRequest,
    redis: Redis = Depends(get_redis)
):
    otp = generate_otp()
    await redis.setex(f"otp:{data.mobile}", 300, otp)
    return {"success": True}
```

---

### 3. Distributed Lock Pattern (Redis)

```python
# app/utils/redis_locks.py
import asyncio
import uuid
from redis.asyncio import Redis

class DistributedLock:
    def __init__(self, redis: Redis, resource_id: str, timeout: int = 120):
        self.redis = redis
        self.key = f"lock:{resource_id}"
        self.token = str(uuid.uuid4())
        self.timeout = timeout
    
    async def __aenter__(self):
        # Try to acquire lock with exponential backoff
        max_wait = 10  # seconds
        wait_time = 0.05
        total_waited = 0
        
        while total_waited < max_wait:
            acquired = await self.redis.set(
                self.key,
                self.token,
                nx=True,  # Only set if not exists
                ex=self.timeout
            )
            if acquired:
                return self
            
            await asyncio.sleep(wait_time)
            total_waited += wait_time
            wait_time = min(wait_time * 2, 1.0)  # Exponential backoff
        
        raise TimeoutError(f"Could not acquire lock for {self.key}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Atomic release using Lua script
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(lua_script, 1, self.key, self.token)
```

**Usage in availability service**:
```python
async def lock_and_book_room(
    hotel_id: UUID,
    room_type_id: UUID,
    redis: Redis = Depends(get_redis)
):
    lock_key = f"hotel:{hotel_id}:roomtype:{room_type_id}"
    
    async with DistributedLock(redis, lock_key, timeout=120):
        # Check availability
        available = await check_room_availability(...)
        if not available:
            raise HTTPException(409, "Room not available")
        
        # Create booking
        booking = await create_booking(...)
        
        # Lock automatically released on exit
        return booking
```

---

### 4. Transaction Management Pattern

```python
# app/services/booking_service.py
from sqlalchemy.ext.asyncio import AsyncSession

class BookingService:
    async def create_booking_with_guests(
        self,
        db: AsyncSession,
        booking_data: BookingCreate,
        user_id: UUID
    ) -> Booking:
        # Use nested transaction
        async with db.begin_nested():
            # Create booking
            booking = Booking(
                user_id=user_id,
                hotel_id=booking_data.hotel_id,
                room_type_id=booking_data.room_type_id,
                checkin_date=booking_data.checkin_date,
                checkout_date=booking_data.checkout_date,
                num_guests=booking_data.num_guests
            )
            db.add(booking)
            await db.flush()  # Get booking.id without committing
            
            # Add guests
            for guest_data in booking_data.guests:
                guest = Guest(
                    booking_id=booking.id,
                    name=guest_data.name,
                    age=guest_data.age,
                    gender=guest_data.gender
                )
                db.add(guest)
            
            # Add services
            total_service_amount = 0
            for service in booking_data.pre_services:
                bs = BookingService(
                    booking_id=booking.id,
                    service_id=service.service_id,
                    quantity=service.quantity,
                    unit_price=service.price,
                    total_price=service.price * service.quantity
                )
                db.add(bs)
                total_service_amount += bs.total_price
            
            # Create invoice
            invoice = Invoice(
                booking_id=booking.id,
                subtotal=booking.total_room_amount + total_service_amount,
                taxes=0,  # Calculate taxes
                total_due=booking.total_room_amount + total_service_amount
            )
            db.add(invoice)
            
            # Nested transaction commits here
            
        # Refresh to get all relationships
        await db.refresh(booking)
        return booking
```

---

### 5. JWT Authentication Pattern

```python
# app/core/security.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from redis.asyncio import Redis

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

async def create_tokens(user_id: UUID, redis: Redis) -> dict:
    session_id = str(uuid.uuid4())
    
    # Access token (15 min)
    access_payload = {
        "sub": str(user_id),
        "session_id": session_id,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Refresh token (7 days)
    refresh_payload = {
        "sub": str(user_id),
        "session_id": session_id,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Store session in Redis
    session_key = f"session:{user_id}:{session_id}"
    session_data = {
        "user_id": str(user_id),
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "refresh_token": refresh_token
    }
    await redis.setex(session_key, 7 * 24 * 60 * 60, json.dumps(session_data))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

async def verify_token(token: str, redis: Redis) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        
        # Check session exists in Redis
        session_key = f"session:{user_id}:{session_id}"
        if not await redis.exists(session_key):
            raise HTTPException(401, "Session expired or revoked")
        
        # Check token blacklist
        if await redis.exists(f"blacklist:{token}"):
            raise HTTPException(401, "Token blacklisted")
        
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid token")

# Dependency for protected routes
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> User:
    payload = await verify_token(token, redis)
    user_id = UUID(payload["sub"])
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    
    return user
```

---

### 6. Complex Query Pattern (Avoiding N+1)

```python
# app/repositories/hotel_repository.py
from sqlalchemy import select, func, and_, or_, not_
from sqlalchemy.orm import selectinload, joinedload

class HotelRepository:
    async def search_hotels_with_availability(
        self,
        db: AsyncSession,
        city: str,
        checkin: date,
        checkout: date,
        guests: int,
        skip: int = 0,
        limit: int = 20
    ):
        # Subquery for booked rooms
        booked_rooms_subq = (
            select(Room.id)
            .join(Booking, Booking.room_id == Room.id)
            .where(
                and_(
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
        ).scalar_subquery()
        
        # Main query with eager loading
        stmt = (
            select(
                Hotel,
                func.min(RoomType.base_price).label('min_price'),
                func.count(Room.id).label('available_rooms')
            )
            .join(Hotel.location)
            .join(Hotel.room_types)
            .join(RoomType.rooms)
            .options(
                selectinload(Hotel.location),
                selectinload(Hotel.room_types)
            )
            .where(
                and_(
                    Location.city == city,
                    Room.status == 'AVAILABLE',
                    RoomType.capacity >= guests,
                    not_(Room.id.in_(booked_rooms_subq))
                )
            )
            .group_by(Hotel.id)
            .having(func.count(Room.id) > 0)
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        return result.all()
```

---

### 7. Pydantic Validation Pattern

```python
# app/schemas/booking.py
from pydantic import BaseModel, validator, root_validator, Field
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

class GuestCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=0, le=150)
    gender: Optional[str] = Field(None, regex=r'^(M|F|Other)$')
    id_doc_type: Optional[str]
    id_doc_number: Optional[str]

class PreServiceCreate(BaseModel):
    service_id: UUID
    quantity: int = Field(default=1, ge=1, le=10)
    scheduled_for: Optional[datetime] = None
    
    @validator('scheduled_for')
    def validate_schedule(cls, v):
        if v and v < datetime.utcnow():
            raise ValueError('Cannot schedule service in the past')
        return v

class BookingCreate(BaseModel):
    hotel_id: UUID
    room_type_id: UUID
    checkin_date: date
    checkout_date: date
    num_rooms: int = Field(default=1, ge=1, le=5)
    num_guests: int = Field(..., ge=1, le=20)
    guests: List[GuestCreate]
    pre_services: List[PreServiceCreate] = []
    
    @validator('checkin_date')
    def checkin_not_past(cls, v):
        if v < date.today():
            raise ValueError('Check-in date cannot be in the past')
        return v
    
    @validator('checkout_date')
    def checkout_after_checkin(cls, v, values):
        if 'checkin_date' in values and v <= values['checkin_date']:
            raise ValueError('Check-out must be after check-in')
        
        if 'checkin_date' in values:
            nights = (v - values['checkin_date']).days
            if nights > 30:
                raise ValueError('Maximum stay is 30 nights')
            if nights < 1:
                raise ValueError('Minimum stay is 1 night')
        
        return v
    
    @root_validator
    def validate_guests(cls, values):
        num_guests = values.get('num_guests')
        guests = values.get('guests', [])
        
        if len(guests) != num_guests:
            raise ValueError(
                f'Expected {num_guests} guest details, received {len(guests)}'
            )
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "hotel_id": "123e4567-e89b-12d3-a456-426614174000",
                "room_type_id": "223e4567-e89b-12d3-a456-426614174001",
                "checkin_date": "2025-12-01",
                "checkout_date": "2025-12-05",
                "num_rooms": 1,
                "num_guests": 2,
                "guests": [
                    {"name": "John Doe", "age": 30, "gender": "M"},
                    {"name": "Jane Doe", "age": 28, "gender": "F"}
                ],
                "pre_services": [
                    {
                        "service_id": "323e4567-e89b-12d3-a456-426614174002",
                        "quantity": 1,
                        "scheduled_for": "2025-12-01T14:00:00"
                    }
                ]
            }
        }
```

---

### 8. Background Task Pattern

```python
# Lightweight tasks - FastAPI BackgroundTasks
from fastapi import BackgroundTasks

async def send_booking_confirmation(booking_id: UUID, user_email: str):
    # Send email
    await email_client.send(...)

@router.post("/bookings")
async def create_booking(
    data: BookingCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    booking = await booking_service.create_booking(...)
    
    # Send confirmation in background
    background_tasks.add_task(
        send_booking_confirmation,
        booking.id,
        current_user.email
    )
    
    return booking

# Heavy tasks - Celery
# tasks.py
from celery import Celery

celery_app = Celery(
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task(bind=True, max_retries=3)
def generate_invoice_pdf(self, booking_id: str):
    try:
        # Heavy PDF generation
        pdf = create_pdf(booking_id)
        upload_to_s3(pdf)
        return {"success": True, "url": pdf_url}
    except Exception as e:
        self.retry(countdown=60, exc=e)

# In route
@router.post("/bookings/{booking_id}/invoice/generate")
async def generate_invoice(booking_id: UUID):
    task = generate_invoice_pdf.delay(str(booking_id))
    return {"task_id": task.id, "status": "processing"}
```

---

### 9. Error Handling Pattern

```python
# app/core/exceptions.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class BookingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

class RoomUnavailableError(BookingError):
    def __init__(self):
        super().__init__("Room not available for selected dates", 409)

class LockTimeoutError(BookingError):
    def __init__(self):
        super().__init__("Unable to acquire resource lock", 423)

# Exception handlers
async def booking_error_handler(request: Request, exc: BookingError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

# In main.py
app.add_exception_handler(BookingError, booking_error_handler)
```

---

### 10. Testing Pattern

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    engine = create_async_engine("postgresql+asyncpg://test@localhost/test_db")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

# Test example
@pytest.mark.asyncio
async def test_create_booking(client, db_session):
    # Create test data
    hotel = Hotel(...)
    db_session.add(hotel)
    await db_session.commit()
    
    # Test endpoint
    response = await client.post("/api/bookings", json={...})
    assert response.status_code == 201
    data = response.json()
    assert data["hotel_id"] == str(hotel.id)
```

---

## Quick Checklist

- [ ] Always `await` async functions
- [ ] Use `selectinload()` for relationships
- [ ] Implement distributed locks for critical resources
- [ ] Use transactions for multi-table operations
- [ ] Validate with Pydantic validators
- [ ] Handle errors with custom exceptions
- [ ] Add background tasks for non-critical operations
- [ ] Write async tests with proper fixtures
- [ ] Use connection pooling
- [ ] Monitor lock acquisition times and query performance
