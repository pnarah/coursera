# 03A FastAPI Backend Deep Dive & Setup

## Objective
Understand FastAPI-specific implementation patterns and set up the backend with proper async architecture.

## Prerequisites
- Python 3.11+ installed
- PostgreSQL and Redis available (local or Docker)
- Understanding of async/await concepts

## FastAPI Advantages for This Project

### Why FastAPI Over Alternatives?

**vs NestJS (Node.js/TypeScript)**:
- ✅ Native async support without callback hell
- ✅ Better performance for CPU-bound pricing calculations
- ✅ Pydantic validation more powerful than class-validator
- ✅ Smaller memory footprint
- ❌ Less mature TypeScript ecosystem integration

**vs Spring Boot (Java)**:
- ✅ Faster development cycle (less boilerplate)
- ✅ Better async I/O performance
- ✅ Auto-generated OpenAPI docs
- ✅ Easier integration with ML/data science if needed later
- ❌ Less enterprise tooling and conventions

**vs Django (Python)**:
- ✅ True async support (Django's is bolted-on)
- ✅ API-first design (not full-stack framework overhead)
- ✅ Better performance for API-only workloads
- ❌ Less built-in features (need to compose libraries)

## Key Complexity Areas in FastAPI

### 1. Async Database with SQLAlchemy 2.0

**Challenge**: SQLAlchemy async requires different patterns than sync.

**Setup**:
```bash
pip install sqlalchemy[asyncio] asyncpg alembic
```

**Pattern**:
```python
# Don't do this (old SQLAlchemy 1.x style)
user = session.query(User).filter(User.id == user_id).first()

# Do this (SQLAlchemy 2.0 async)
from sqlalchemy import select
stmt = select(User).where(User.id == user_id)
result = await session.execute(stmt)
user = result.scalar_one_or_none()
```

**Common Pitfalls**:
- Forgetting `await` on database operations
- Using `.query()` API (deprecated in 2.0)
- Not handling `expire_on_commit` properly
- Lazy loading relationships in async context

**Solution**: Always use explicit loading:
```python
# Eager load relationships
stmt = select(Hotel).options(
    selectinload(Hotel.room_types),
    selectinload(Hotel.location)
).where(Hotel.id == hotel_id)
```

### 2. Redis Distributed Locking

**Challenge**: Preventing double-booking requires atomic operations.

**Why Complex**:
- Race conditions between check and book
- Lock expiration handling
- Ensuring lock owner can release
- Dealing with lock holder crashes

**Implementation Pattern**:
```python
import asyncio
from redis.asyncio import Redis

class InventoryLock:
    def __init__(self, redis: Redis, resource_key: str):
        self.redis = redis
        self.lock_key = f"lock:{resource_key}"
        self.lock_value = str(uuid.uuid4())
        self.timeout = 120  # 2 minutes
    
    async def acquire(self, timeout: float = 10.0) -> bool:
        """Try to acquire lock with timeout"""
        end_time = time.time() + timeout
        while time.time() < end_time:
            acquired = await self.redis.set(
                self.lock_key,
                self.lock_value,
                nx=True,
                ex=self.timeout
            )
            if acquired:
                return True
            await asyncio.sleep(0.05)
        return False
    
    async def release(self):
        """Release lock only if we own it"""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(lua_script, 1, self.lock_key, self.lock_value)

# Usage
lock = InventoryLock(redis, f"hotel:{hotel_id}:roomtype:{room_type_id}")
if await lock.acquire():
    try:
        # Check availability and book
        pass
    finally:
        await lock.release()
else:
    raise HTTPException(423, "Resource locked")
```

**Why Lua Script**: Ensures atomic check-and-delete (prevents releasing someone else's lock).

### 3. Transaction Management Across Services

**Challenge**: Booking involves multiple operations that must be atomic.

**Scenario**:
1. Create booking record
2. Add guest records
3. Add service records
4. Generate invoice
5. Decrement inventory
6. Release Redis lock

**Pattern**:
```python
from sqlalchemy.ext.asyncio import AsyncSession

async def create_booking_transaction(
    db: AsyncSession,
    redis: Redis,
    data: BookingCreate
):
    # Start database transaction
    async with db.begin():
        try:
            # All DB operations here
            booking = Booking(...)
            db.add(booking)
            await db.flush()  # Get ID without committing
            
            for guest in data.guests:
                db.add(Guest(booking_id=booking.id, ...))
            
            invoice = Invoice(booking_id=booking.id, ...)
            db.add(invoice)
            
            # Redis operations (not transactional with DB!)
            await redis.delete(f"lock:...")
            
            # Commit happens automatically at end of `async with`
            return booking
            
        except Exception as e:
            # Rollback happens automatically
            # But Redis changes are NOT rolled back!
            await redis.set(f"lock:...", "1", ex=120)  # Restore lock
            raise
```

**Complexity**: DB transactions don't cover Redis. Need compensating actions on failure.

**Advanced Pattern - Saga Pattern**:
For distributed transactions across multiple services, implement saga pattern with compensation.

### 4. JWT + Redis Hybrid Auth

**Challenge**: Need stateless JWT benefits but also revocation capability.

**Why Complex**:
- JWT is stateless but we need to revoke sessions
- Can't invalidate JWT without server-side state
- Need to balance performance vs security

**Solution - Hybrid Approach**:
```python
# Token includes session_id claim
payload = {
    "sub": user_id,
    "session_id": session_id,  # Links to Redis
    "exp": datetime.utcnow() + timedelta(minutes=15)
}
token = jwt.encode(payload, SECRET)

# Verification checks both JWT and Redis
async def verify_token(token: str, redis: Redis):
    # Step 1: Verify JWT signature and expiry
    payload = jwt.decode(token, SECRET)
    
    # Step 2: Check session exists in Redis
    session_key = f"session:{payload['sub']}:{payload['session_id']}"
    if not await redis.exists(session_key):
        raise HTTPException(401, "Session revoked")
    
    # Step 3: Check token not blacklisted (for logout before expiry)
    if await redis.exists(f"blacklist:{token}"):
        raise HTTPException(401, "Token blacklisted")
    
    return payload
```

**Trade-offs**:
- ✅ Can revoke individual sessions
- ✅ Can logout and blacklist token
- ❌ Every request hits Redis (but fast)
- ❌ More complex than pure JWT

### 5. Background Tasks - BackgroundTasks vs Celery

**When to Use Each**:

**FastAPI BackgroundTasks** (lightweight):
- ✅ Sending SMS/email after response
- ✅ Logging/analytics
- ✅ Cache warming
- ❌ NOT for long-running tasks
- ❌ NOT for tasks that must complete

**Celery** (heavy):
- ✅ PDF generation (1-5 seconds)
- ✅ Batch invoice processing
- ✅ Scheduled tasks (nightly cleanup)
- ✅ Retry logic and monitoring
- ❌ Overkill for simple tasks

**Example - Background SMS**:
```python
from fastapi import BackgroundTasks

async def send_sms_background(mobile: str, message: str):
    await twilio_client.send_sms(mobile, message)

@router.post("/auth/send-otp")
async def send_otp(
    data: OTPRequest,
    background_tasks: BackgroundTasks
):
    otp = generate_otp()
    await redis.setex(f"otp:{data.mobile}", 300, otp)
    
    # Send SMS in background (doesn't block response)
    background_tasks.add_task(send_sms_background, data.mobile, otp)
    
    return {"success": True}
```

**Example - Celery Invoice**:
```python
# tasks.py
from celery import Celery
celery_app = Celery(broker=REDIS_URL)

@celery_app.task(bind=True, max_retries=3)
def generate_invoice_pdf(self, booking_id: str):
    try:
        # Heavy PDF generation
        pdf = create_pdf(booking_id)
        upload_to_s3(pdf)
    except Exception as e:
        self.retry(countdown=60)

# In route
@router.post("/bookings/{booking_id}/checkout")
async def checkout(booking_id: UUID):
    # ... process checkout ...
    generate_invoice_pdf.delay(str(booking_id))
    return {"status": "processing"}
```

### 6. Pydantic Validation Complexity

**Challenge**: Complex nested data with cross-field validation.

**Example - Booking Validation**:
```python
from pydantic import BaseModel, validator, root_validator
from typing import List

class BookingCreate(BaseModel):
    checkin_date: date
    checkout_date: date
    num_guests: int
    guests: List[GuestCreate]
    
    @validator('checkout_date')
    def checkout_after_checkin(cls, v, values):
        if 'checkin_date' in values and v <= values['checkin_date']:
            raise ValueError('Checkout must be after checkin')
        if 'checkin_date' in values:
            nights = (v - values['checkin_date']).days
            if nights > 30:
                raise ValueError('Maximum 30 night stay')
        return v
    
    @root_validator
    def validate_guests(cls, values):
        num_guests = values.get('num_guests')
        guests = values.get('guests', [])
        if len(guests) != num_guests:
            raise ValueError(f'Expected {num_guests} guests, got {len(guests)}')
        return values
```

**Advanced - Custom Types**:
```python
from pydantic import constr, conint

MobileNumber = constr(regex=r'^\+?[1-9]\d{9,14}$')
OTP = constr(regex=r'^\d{6}$')
GuestAge = conint(ge=0, le=150)

class OTPVerifyRequest(BaseModel):
    mobile: MobileNumber
    otp: OTP
```

### 7. Query Optimization & N+1 Problem

**Challenge**: Async makes N+1 queries less obvious.

**Anti-pattern**:
```python
# DON'T DO THIS - N+1 queries
hotels = await db.execute(select(Hotel).where(Hotel.city == "Delhi"))
for hotel in hotels:
    # Each iteration hits DB again!
    room_types = await db.execute(
        select(RoomType).where(RoomType.hotel_id == hotel.id)
    )
```

**Correct Pattern**:
```python
# DO THIS - Single query with join
stmt = (
    select(Hotel)
    .options(selectinload(Hotel.room_types))
    .where(Hotel.city == "Delhi")
)
result = await db.execute(stmt)
hotels = result.scalars().all()
# room_types already loaded for each hotel
```

**Complex Query Example**:
```python
# Get hotels with available rooms for date range
from sqlalchemy import func, and_, or_, not_

async def get_available_hotels(
    db: AsyncSession,
    city: str,
    checkin: date,
    checkout: date
):
    # Subquery for booked room IDs in date range
    booked_rooms = (
        select(Room.id)
        .join(Booking)
        .where(
            and_(
                or_(
                    and_(Booking.checkin_date <= checkin, Booking.checkout_date > checkin),
                    and_(Booking.checkin_date < checkout, Booking.checkout_date >= checkout)
                ),
                Booking.status == 'CONFIRMED'
            )
        )
    )
    
    # Main query
    stmt = (
        select(
            Hotel,
            func.count(Room.id).label('available_rooms')
        )
        .join(Hotel.location)
        .join(Hotel.rooms)
        .where(
            and_(
                Location.city == city,
                Room.status == 'AVAILABLE',
                not_(Room.id.in_(booked_rooms))
            )
        )
        .group_by(Hotel.id)
        .having(func.count(Room.id) > 0)
    )
    
    result = await db.execute(stmt)
    return result.all()
```

## Deliverables

1. **requirements.txt**:
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.12.1
redis==5.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic[email]==2.5.0
pydantic-settings==2.1.0
twilio==8.10.0
stripe==7.6.0
celery==5.3.4
```

2. **Project structure** (see section 3.2 in DESIGN.md)

3. **Core configuration**:
```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Prompts You Can Use

- "Set up FastAPI project with async SQLAlchemy and Redis integration"
- "Implement distributed locking for room inventory using Redis Lua scripts"
- "Create booking transaction handling multiple tables atomically"
- "Add JWT authentication with Redis session tracking"
- "Implement Pydantic models with complex cross-field validation"
- "Optimize hotel search query to avoid N+1 problem"
- "Set up Celery for background invoice generation"

## Acceptance Criteria

- Server starts with `uvicorn app.main:app --reload`
- `/docs` shows auto-generated OpenAPI documentation
- Database connection pool works asynchronously
- Redis lock prevents race conditions in tests
- All Pydantic validations have unit tests

## Common Pitfalls to Avoid

1. **Mixing sync and async**: Don't use `requests`, use `httpx` async client
2. **Forgetting await**: IDE should catch, but easy to miss
3. **DB session lifecycle**: Always use dependency injection
4. **Redis not atomic**: Use Lua for check-and-set operations
5. **Pydantic performance**: Use `model_validate()` not `parse_obj()` in v2

## Performance Tips

- Use connection pooling (20-50 for PostgreSQL)
- Redis pipeline for bulk operations
- Background tasks for non-critical operations
- Proper indexes on frequently queried columns
- Use `EXPLAIN ANALYZE` for slow queries

## Next Task

Proceed to 04 Authentication OTP Flow (now with FastAPI-specific implementation).
