# 19 Security Hardening & Rate Limits

## Objective
Add critical security measures: rate limits, input validation, token practices, and lock abuse prevention.

## Prerequisites
- Core APIs functional

## Deliverables
- Rate limiting middleware
- Input validation schemas (DTO with class-validator)
- Lock abuse detection (max attempts per minute)
- Secure headers configuration

## Suggested Steps
1. Implement global validation pipes.
2. Integrate rate limiter (Redis-based) on OTP & lock endpoints.
3. Add security headers (helmet) and CORS restrictions.
4. Log suspicious events.

## Prompts You Can Use
- "Add rate limiting to OTP send endpoint using slowapi and Redis."
- "Implement global request validation in FastAPI using Pydantic."
- "Configure CORS middleware with strict origins in FastAPI."
- "Add security headers using fastapi-security-headers or custom middleware." 

## Acceptance Criteria
- Excessive requests receive 429 errors.
- All inputs validated consistently.

## Next Task
Proceed to 20 Testing Strategy Implementation.