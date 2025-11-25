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
1. Create AuthModule, AuthController.
2. Implement OTPService storing codes in Redis (key: otp:{mobile}).
3. Add rate limiting (e.g., in-memory placeholder if Redis not ready).
4. Implement verification creating JWT tokens.

## Prompts You Can Use
- "Create NestJS OTP service with Redis storage (mock if absent)."
- "Implement send-otp and verify-otp endpoints with validation." 
- "Generate short-lived access and refresh tokens on OTP verify."

## Acceptance Criteria
- Valid mobile triggers OTP storage.
- Verification returns accessToken & refreshToken.
- Invalid OTP returns proper error message.

## Next Task
Proceed to 05 Session Management & Redis.