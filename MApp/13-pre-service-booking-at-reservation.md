# 13 Pre-Service Booking at Reservation

## Objective
Allow selection of services (e.g., airport pickup) during initial booking creation.

## Prerequisites
- Services schema present (will add in later if not yet)
- Booking creation logic

## Deliverables
- booking_services table (initial subset)
- Extended booking endpoint to accept preServices array
- Service pricing integration

## Suggested Steps
1. Create service_categories and services tables if absent.
2. Extend booking request to include services with quantity/schedule.
3. Compute total service amount and add to booking totals.
4. Persist booking_services entries.

## Prompts You Can Use
- "Add booking_services table and integrate into booking transaction." 
- "Compute service totals and update booking service amount field." 
- "Validate service availability for pre-book stage."

## Acceptance Criteria
- Services appear linked to booking.
- Total amounts reflect added services.

## Next Task
Proceed to 14 In-Stay Service Ordering.