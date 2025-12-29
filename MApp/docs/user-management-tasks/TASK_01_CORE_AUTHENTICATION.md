# Task 01: Core Authentication & OTP System

**Priority:** Critical  
**Estimated Duration:** 4-5 days  
**Dependencies:** None  
**Status:** Not Started

---

## Overview

Implement mobile number-based authentication with OTP verification for user registration and login. This is the foundation of the entire user management system.

---

## Objectives

1. Create mobile number-based authentication flow
2. Implement OTP generation and verification
3. Add rate limiting for OTP requests
4. Generate JWT tokens for authenticated sessions
5. Support both new user registration and existing user login
6. Add basic user model to database

---

## Backend Tasks

### 1. Database Schema

Create migration for users table:

```sql
-- Migration: 001_create_users_table.py
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    mobile_number VARCHAR(15) UNIQUE NOT NULL,
    country_code VARCHAR(5) DEFAULT '+1',
    full_name VARCHAR(255),
    email VARCHAR(255),
    role VARCHAR(50) DEFAULT 'GUEST',
    hotel_id INTEGER REFERENCES hotels(id),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_mobile ON users(mobile_number);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_hotel_id ON users(hotel_id);
```

### 2. OTP Storage in Redis

```python
# Store OTP with expiry
redis.setex(
    f"otp:{mobile_number}",
    600,  # 10 minutes
    hashed_otp
)

# Store attempt count
redis.setex(
    f"otp_attempts:{mobile_number}",
    1800,  # 30 minutes
    attempt_count
)
```

### 3. Models

Create `app/models/user.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String(15), unique=True, nullable=False, index=True)
    country_code = Column(String(5), default="+1")
    full_name = Column(String(255))
    email = Column(String(255))
    role = Column(String(50), default="GUEST", index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 4. Schemas

Create `app/schemas/auth.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional

class OTPRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)
    country_code: str = Field(default="+1")
    
    @validator('mobile_number')
    def validate_mobile(cls, v):
        if not v.isdigit():
            raise ValueError('Mobile number must contain only digits')
        return v

class OTPVerify(BaseModel):
    mobile_number: str
    otp: str = Field(..., min_length=6, max_length=6)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    action: str  # "login" or "register"

class UserBase(BaseModel):
    id: int
    mobile_number: str
    full_name: Optional[str]
    email: Optional[str]
    role: str
    hotel_id: Optional[int]
    
    class Config:
        from_attributes = True
```

### 5. Services

Create `app/services/auth_service.py`:

```python
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import create_access_token, create_refresh_token
from app.core.redis import redis_client
from fastapi import HTTPException

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_otp(self, mobile_number: str) -> str:
        """Generate 6-digit OTP and store in Redis"""
        # Check rate limit
        attempt_key = f"otp_attempts:{mobile_number}"
        attempts = await redis_client.get(attempt_key)
        
        if attempts and int(attempts) >= 3:
            raise HTTPException(
                status_code=429,
                detail="Too many OTP requests. Please try again in 30 minutes."
            )
        
        # Generate OTP
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Hash OTP before storing
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        
        # Store in Redis (10 minutes expiry)
        otp_key = f"otp:{mobile_number}"
        await redis_client.setex(otp_key, 600, otp_hash)
        
        # Increment attempt counter
        current_attempts = int(attempts) if attempts else 0
        await redis_client.setex(attempt_key, 1800, current_attempts + 1)
        
        # TODO: Send OTP via SMS service
        print(f"OTP for {mobile_number}: {otp}")  # Development only
        
        return otp
    
    async def verify_otp(self, mobile_number: str, otp: str) -> Tuple[User, bool]:
        """Verify OTP and return user (create if new)"""
        # Get stored OTP hash
        otp_key = f"otp:{mobile_number}"
        stored_hash = await redis_client.get(otp_key)
        
        if not stored_hash:
            raise HTTPException(
                status_code=400,
                detail="OTP expired or invalid"
            )
        
        # Verify OTP
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        if otp_hash != stored_hash:
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP"
            )
        
        # Delete OTP after successful verification
        await redis_client.delete(otp_key)
        await redis_client.delete(f"otp_attempts:{mobile_number}")
        
        # Check if user exists
        stmt = select(User).where(User.mobile_number == mobile_number)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        is_new_user = False
        if not user:
            # Create new user
            user = User(
                mobile_number=mobile_number,
                role="GUEST",
                is_active=True
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            is_new_user = True
        else:
            # Update last login
            user.last_login = datetime.utcnow()
            await self.db.commit()
        
        return user, is_new_user
    
    def generate_tokens(self, user: User) -> dict:
        """Generate JWT access and refresh tokens"""
        token_data = {
            "user_id": user.id,
            "mobile_number": user.mobile_number,
            "role": user.role,
            "hotel_id": user.hotel_id
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
```

### 6. Security Utilities

Create `app/core/security.py`:

```python
from datetime import datetime, timedelta
from typing import Dict, Any
from jose import jwt
from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

def create_access_token(data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token"""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

### 7. API Endpoints

Create `app/api/v1/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import OTPRequest, OTPVerify, TokenResponse, UserBase

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/request-otp")
async def request_otp(
    request: OTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP for mobile number"""
    auth_service = AuthService(db)
    
    try:
        await auth_service.generate_otp(request.mobile_number)
        return {
            "success": True,
            "message": "OTP sent successfully",
            "expires_in": 600  # 10 minutes
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    request: OTPVerify,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and login/register user"""
    auth_service = AuthService(db)
    
    try:
        # Verify OTP and get/create user
        user, is_new_user = await auth_service.verify_otp(
            request.mobile_number,
            request.otp
        )
        
        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account is disabled"
            )
        
        # Generate tokens
        tokens = auth_service.generate_tokens(user)
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "mobile_number": user.mobile_number,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
                "hotel_id": user.hotel_id
            },
            "action": "register" if is_new_user else "login"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh-token")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    from app.core.security import decode_token, create_access_token
    
    try:
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        # Create new access token
        token_data = {
            "user_id": payload["user_id"],
            "mobile_number": payload["mobile_number"],
            "role": payload["role"],
            "hotel_id": payload.get("hotel_id")
        }
        
        new_access_token = create_access_token(token_data)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
```

### 8. Configuration Updates

Update `app/core/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings...
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # OTP Settings
    OTP_LENGTH: int = 6
    OTP_EXPIRY_SECONDS: int = 600
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RATE_LIMIT_SECONDS: int = 1800
    
    class Config:
        env_file = ".env"
```

### 9. Redis Client Setup

Create `app/core/redis.py`:

```python
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)

async def get_redis():
    return redis_client
```

---

## Frontend Tasks

### 1. Models

Create `mobile/lib/core/models/user.dart`:

```dart
enum UserRole {
  GUEST,
  HOTEL_EMPLOYEE,
  VENDOR_ADMIN,
  SYSTEM_ADMIN,
}

class User {
  final int id;
  final String mobileNumber;
  final String? fullName;
  final String? email;
  final UserRole role;
  final int? hotelId;

  User({
    required this.id,
    required this.mobileNumber,
    this.fullName,
    this.email,
    required this.role,
    this.hotelId,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      mobileNumber: json['mobile_number'],
      fullName: json['full_name'],
      email: json['email'],
      role: _parseRole(json['role']),
      hotelId: json['hotel_id'],
    );
  }

  static UserRole _parseRole(String roleStr) {
    switch (roleStr) {
      case 'GUEST':
        return UserRole.GUEST;
      case 'HOTEL_EMPLOYEE':
        return UserRole.HOTEL_EMPLOYEE;
      case 'VENDOR_ADMIN':
        return UserRole.VENDOR_ADMIN;
      case 'SYSTEM_ADMIN':
        return UserRole.SYSTEM_ADMIN;
      default:
        return UserRole.GUEST;
    }
  }
}
```

### 2. API Service Updates

Update `mobile/lib/core/services/api_service.dart`:

```dart
class ApiService {
  // Existing code...
  
  Future<Map<String, dynamic>> requestOTP(String mobileNumber) async {
    try {
      final response = await _dio.post('/auth/request-otp', data: {
        'mobile_number': mobileNumber,
        'country_code': '+1',
      });
      return response.data;
    } catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<Map<String, dynamic>> verifyOTP(String mobileNumber, String otp) async {
    try {
      final response = await _dio.post('/auth/verify-otp', data: {
        'mobile_number': mobileNumber,
        'otp': otp,
      });
      return response.data;
    } catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<Map<String, dynamic>> refreshToken(String refreshToken) async {
    try {
      final response = await _dio.post('/auth/refresh-token', data: {
        'refresh_token': refreshToken,
      });
      return response.data;
    } catch (e) {
      throw _handleError(e);
    }
  }
}
```

### 3. Secure Storage Service

Create `mobile/lib/core/services/secure_storage_service.dart`:

```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorageService {
  static final SecureStorageService _instance = SecureStorageService._internal();
  factory SecureStorageService() => _instance;
  SecureStorageService._internal();

  final _storage = const FlutterSecureStorage();

  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }

  Future<String?> getAccessToken() async {
    return await _storage.read(key: 'access_token');
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: 'refresh_token');
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Future<void> saveUser(Map<String, dynamic> userData) async {
    await _storage.write(key: 'user_data', value: jsonEncode(userData));
  }

  Future<Map<String, dynamic>?> getUser() async {
    final data = await _storage.read(key: 'user_data');
    if (data != null) {
      return jsonDecode(data);
    }
    return null;
  }

  Future<void> clearAll() async {
    await _storage.deleteAll();
  }
}
```

### 4. Update Login Screen

Update the existing `mobile/lib/features/authentication/login_screen.dart` to use OTP:

- Keep the mobile number input
- On submit, call requestOTP API
- Show OTP input screen
- Verify OTP
- Save tokens on success
- Navigate based on user role

---

## Testing

### Backend Tests

Create `backend/tests/test_auth.py`:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_request_otp(client: AsyncClient):
    response = await client.post("/api/v1/auth/request-otp", json={
        "mobile_number": "9876543210"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_verify_otp_invalid(client: AsyncClient):
    response = await client.post("/api/v1/auth/verify-otp", json={
        "mobile_number": "9876543210",
        "otp": "000000"
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_rate_limit_otp(client: AsyncClient):
    mobile = "9999999999"
    
    # Request OTP 3 times
    for _ in range(3):
        await client.post("/api/v1/auth/request-otp", json={
            "mobile_number": mobile
        })
    
    # 4th request should be rate limited
    response = await client.post("/api/v1/auth/request-otp", json={
        "mobile_number": mobile
    })
    assert response.status_code == 429
```

---

## Environment Variables

Add to `backend/.env`:

```env
# JWT Configuration
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
ALGORITHM=HS256

# OTP Configuration
OTP_EXPIRY_SECONDS=600
OTP_MAX_ATTEMPTS=3
```

---

## Integration with Existing Code

1. Add user relationship to bookings table (optional for now)
2. Update session management to use new user model
3. Integrate with existing rate limiting

---

## Acceptance Criteria

- ✅ User can request OTP with mobile number
- ✅ OTP is generated and stored in Redis
- ✅ OTP expires after 10 minutes
- ✅ Rate limiting prevents abuse (3 requests per 30 min)
- ✅ OTP verification creates new user if mobile not exists
- ✅ OTP verification logs in existing user
- ✅ JWT tokens are generated on successful verification
- ✅ Tokens include user_id, role, hotel_id
- ✅ Refresh token endpoint works
- ✅ Frontend can request and verify OTP
- ✅ Tokens are stored securely in mobile app
- ✅ User data is available after login

---

## Next Task

**TASK_02_USER_ROLES_AND_RBAC.md** - Implement role-based access control and permissions system
