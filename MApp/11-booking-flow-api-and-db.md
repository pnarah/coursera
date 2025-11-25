# 11 Booking Flow API & DB

## Objective
Create booking table and endpoints to initiate and confirm bookings using availability lock.

## Prerequisites
- Availability locking
- Pricing engine

## Deliverables
- bookings table migration
- Endpoint: POST /api/bookings
- Booking creation storing initial room and amount
- Integration with lock release

## Suggested Steps
1. Create bookings schema and repository.
2. Accept booking params (hotelId, roomTypeId, checkin, checkout, guests, preServices optional).
3. Validate lockId usage if required.
4. Calculate room total and persist booking.
5. Release lock upon success.

## Prompts You Can Use
- "Implement booking creation endpoint validating availability lock." 
- "Persist booking with initial invoice placeholder." 
- "Release room lock after booking commit."

## Acceptance Criteria
- Booking returns booking_reference.
- Lock released after success.

## Next Task
Proceed to 12 Guest Details & Validation.