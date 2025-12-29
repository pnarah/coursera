# 12 Guest Details & Validation

## Objective
Add guests table and attach guest records to bookings with validation rules.

## Prerequisites
- Bookings schema

## Deliverables
- guests table migration
- Guest addition integrated into booking creation
- Validation (required name, optional ID docs)

## Suggested Steps
1. Create guests entity.
2. Extend booking endpoint to accept guest array.
3. Validate guest count vs capacity.
4. Persist guests in transaction with booking.

## Prompts You Can Use
- "Add guests entity and link to booking persistence transaction." 
- "Validate guest count does not exceed room capacity." 
- "Support ID document optional fields with schema validation."

## Acceptance Criteria
- Guests saved atomically with booking.
- Invalid counts rejected.

## Next Task
Proceed to 13 Pre-Service Booking at Reservation.