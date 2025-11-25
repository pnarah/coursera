# 14 In-Stay Service Ordering

## Objective
Enable users to request additional services after check-in with status tracking.

## Prerequisites
- booking_services early stage

## Deliverables
- Endpoint: POST /api/bookings/:bookingId/services
- Endpoint: PUT /api/bookings/:bookingId/services/:id (status updates)
- Status transitions logic

## Suggested Steps
1. Implement service ordering controller functions.
2. Validate booking is in stay window (checkin <= now < checkout).
3. Add status transition rules (REQUESTED -> SCHEDULED -> IN_PROGRESS -> COMPLETED).
4. Update invoice recalculation trigger on COMPLETED.

## Prompts You Can Use
- "Implement in-stay service ordering endpoint with status transitions." 
- "Add validation ensuring booking is active for service requests." 
- "Trigger invoice update when service completes."

## Acceptance Criteria
- Services can be added and progressed through lifecycle.
- Completed services reflected in invoice totals.

## Next Task
Proceed to 15 Invoice Generation & Updates.