# 15 Invoice Generation & Updates

## Objective
Generate and update invoices as services complete and booking changes occur.

## Prerequisites
- Bookings & booking_services

## Deliverables
- invoices table
- Endpoint: GET /api/bookings/:bookingId/invoice
- Invoice recalculation logic (subtotal, taxes, discounts)

## Suggested Steps
1. Create invoices table.
2. Implement InvoiceService to compute totals.
3. Hook invoice generation at booking creation.
4. Update invoice on service completion or cancellation.

## Prompts You Can Use
- "Create invoice service that aggregates booking costs and taxes." 
- "Implement endpoint to fetch current invoice state." 
- "Recalculate invoice when booking_service status changes." 

## Acceptance Criteria
- Invoice matches sum of room + services + taxes - discounts.
- Reflects updates promptly.

## Next Task
Proceed to 16 Payment Integration.