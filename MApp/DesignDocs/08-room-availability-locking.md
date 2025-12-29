# 08 Room Availability Locking

## Objective
Prevent race conditions during booking by introducing short-lived redis locks for room type availability.

## Prerequisites
- Room inventory present
- Redis integration

## Deliverables
- Endpoint: POST /api/availability/lock
- Endpoint: POST /api/availability/release
- Lock key format documented
- Expiration TTL set (e.g., 2 minutes)

## Suggested Steps
1. Implement service generating lockId and storing held quantity.
2. Validate requested quantity vs available rooms.
3. Auto-expire locks using TTL.
4. Add release logic after booking finalization or cancellation.

## Prompts You Can Use
- "Create availability lock service using Redis TTL keys." 
- "Implement endpoints to lock and release room availability." 
- "Add validation for over-lock attempts."

## Acceptance Criteria
- Lock prevents second user from exceeding inventory.
- Releasing frees inventory immediately.

## Next Task
Proceed to 09 Dynamic Pricing Engine Basics.