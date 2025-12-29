# 16 Payment Integration

## Objective
Integrate payment gateway (Stripe/Razorpay) for deposits and final checkout payments.

## Prerequisites
- Invoice generation

## Deliverables
- payments table
- Endpoint: POST /api/payments
- Webhook handler for payment confirmation
- Update booking payment_status

## Suggested Steps
1. Create payments table.
2. Implement PaymentService initiating gateway session.
3. Add webhook endpoint verifying signature.
4. Update booking on success (PARTIAL or PAID).

## Prompts You Can Use
- "Integrate Stripe payment intent creation for booking invoice." 
- "Add webhook to confirm payment and update booking status." 
- "Persist payment record with transaction_id and method." 

## Acceptance Criteria
- Successful payments mark booking appropriately.
- Failed payments logged and retriable.

## Next Task
Proceed to 17 Mobile Screens - Booking Funnel.