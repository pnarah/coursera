# 05 Session Management & Redis

## Objective
Persist and manage user sessions with Redis for concurrent device logins.

## Prerequisites
- Auth tokens working
- Redis available or simulated

## Deliverables
- Session creation upon OTP verification
- GET /api/auth/sessions listing sessions
- DELETE /api/auth/sessions/:sessionId revocation
- Logout endpoint clearing session

## Suggested Steps
1. Define session schema: session:{userId}:{sessionId}.
2. Store deviceInfo, timestamps, refresh token.
3. Implement session listing and deletion logic.
4. Extend logout to remove session and blacklist access token.

## Prompts You Can Use
- "Add session management service in FastAPI using Redis hashes."
- "Implement sessions list and revoke endpoints with FastAPI dependencies."
- "Integrate session creation into OTP verify flow with JWT claims."
- "Create FastAPI dependency to get current user from JWT and Redis session."

## Acceptance Criteria
- Multiple sessions visible for same user.
- Revoking one doesn’t impact others.
- Logout fully clears tokens.

## Next Task
Proceed to 06 Location & Hotel Schema & Seeding.