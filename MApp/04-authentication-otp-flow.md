# 04 Authentication OTP Flow

## Objective
Implement mobile number OTP generation and verification endpoints.

## Prerequisites
- Backend scaffold
- Redis provision plan (or mock)

## Deliverables
- Endpoint: POST /api/auth/send-otp
- Endpoint: POST /api/auth/verify-otp
- OTP generation (6 digits, TTL 5 min)
- Twilio/SNS integration stub or mock service

## Suggested Steps
1. Create app/api/v1/auth.py router
2. Create app/services/otp_service.py for OTP generation and validation
3. Create app/core/security.py for JWT token functions
4. Create app/schemas/auth.py with Pydantic models (OTPRequest, OTPVerify, TokenResponse)
5. Implement POST /api/v1/auth/send-otp endpoint
6. Implement POST /api/v1/auth/verify-otp endpoint
7. Add rate limiting using Redis (max 3 OTP per 30 min per mobile)

## Prompts You Can Use
- "Create FastAPI OTP service using Redis with 5-minute TTL."
- "Implement send-otp and verify-otp endpoints with Pydantic validation."
- "Generate JWT access and refresh tokens using python-jose."
- "Add rate limiting for OTP requests using Redis counters."

## Example Code

### app/schemas/auth.py
```python
from pydantic import BaseModel, Field
import re

class OTPRequest(BaseModel):
    mobile_number: str = Field(..., regex=r'^\+?[1-9]\d{9,14}$')
    country_code: str = Field(default="+1")

class OTPVerify(BaseModel):
    mobile_number: str
    otp: str = Field(..., regex=r'^\d{6}$')
    device_info: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

### app/services/otp_service.py
```python
import random
from redis.asyncio import Redis

class OTPService:
    @staticmethod
    def generate_otp() -> str:
        return str(random.randint(100000, 999999))
    
    @staticmethod
    async def store_otp(redis: Redis, mobile: str, otp: str):
        key = f"otp:{mobile}"
        await redis.setex(key, 300, otp)  # 5 min TTL
    
    @staticmethod
    async def verify_otp(redis: Redis, mobile: str, otp: str) -> bool:
        key = f"otp:{mobile}"
        stored_otp = await redis.get(key)
        if stored_otp and stored_otp == otp:
            await redis.delete(key)
            return True
        return False
```

## Acceptance Criteria
- Valid mobile triggers OTP storage.
- Verification returns accessToken & refreshToken.
- Invalid OTP returns proper error message.

## Next Task
Proceed to 05 Session Management & Redis.