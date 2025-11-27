#!/bin/bash

# Test Payment Integration

BASE_URL="http://localhost:8001/api/v1"
TEST_MOBILE="5551234567"

echo "=== Payment Integration Test Suite ==="
echo

# Cleanup and setup
echo "Setting up test data..."
echo "Sending OTP to mobile $TEST_MOBILE..."
OTP_SEND=$(curl -s -X POST "$BASE_URL/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$TEST_MOBILE\", \"country_code\": \"+1\"}")

echo "OTP send response: $OTP_SEND"

# For development, the OTP is logged. In production, extract from SMS
# For this test, we'll use a fixed development OTP if available
echo "Attempting to verify OTP (using development mode)..."

# Try common dev OTPs or extract from logs
OTP_CODE="123456"  # Development OTP

TOKEN=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$TEST_MOBILE\", \"otp\": \"$OTP_CODE\", \"device_info\": \"Test Device\"}" | jq -r '.access_token')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get auth token"
  exit 1
fi

echo "✓ Auth token obtained"
echo

# Test 1: Lock availability
echo "Test 1: Lock availability for booking"
# Use future dates (7 days from now)
CHECK_IN=$(date -v+7d +%Y-%m-%d)
CHECK_OUT=$(date -v+10d +%Y-%m-%d)

LOCK_RESPONSE=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"hotel_id\": 1,
    \"room_type\": \"DELUXE\",
    \"check_in_date\": \"$CHECK_IN\",
    \"check_out_date\": \"$CHECK_OUT\",
    \"quantity\": 1
  }")

LOCK_ID=$(echo $LOCK_RESPONSE | jq -r '.lock_id')

if [ "$LOCK_ID" != "null" ]; then
  echo "✓ Availability locked: Lock ID=$LOCK_ID"
else
  echo "❌ Failed to lock availability"
  echo "$LOCK_RESPONSE"
  exit 1
fi
echo

# Test 2: Create booking with invoice
echo "Test 2: Create booking to generate invoice"
BOOKING_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"hotel_id\": 1,
    \"room_type\": \"DELUXE\",
    \"check_in\": \"$CHECK_IN\",
    \"check_out\": \"$CHECK_OUT\",
    \"guests\": 2,
    \"lock_id\": \"$LOCK_ID\",
    \"guest_list\": [
      {
        \"guest_name\": \"John Doe\",
        \"email\": \"john@example.com\",
        \"phone\": \"+1234567890\",
        \"is_primary\": true
      },
      {
        \"guest_name\": \"Jane Doe\",
        \"email\": \"jane@example.com\",
        \"phone\": \"+1234567891\",
        \"is_primary\": false
      }
    ]
  }")

BOOKING_ID=$(echo $BOOKING_RESPONSE | jq -r '.booking_id')
BOOKING_STATUS=$(echo $BOOKING_RESPONSE | jq -r '.status')

if [ "$BOOKING_ID" != "null" ] && [ ! -z "$BOOKING_STATUS" ]; then
  echo "✓ Booking created: ID=$BOOKING_ID, Status=$BOOKING_STATUS"
else
  echo "❌ Failed to create booking"
  echo "$BOOKING_RESPONSE"
  exit 1
fi
echo

# Test 3: Get invoice for booking
echo "Test 3: Get invoice for booking"
INVOICE_RESPONSE=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID/invoice" \
  -H "Authorization: Bearer $TOKEN")

INVOICE_TOTAL=$(echo $INVOICE_RESPONSE | jq -r '.total_amount')
INVOICE_STATUS=$(echo $INVOICE_RESPONSE | jq -r '.status')

if [ "$INVOICE_TOTAL" != "null" ]; then
  echo "✓ Invoice retrieved: Total=$INVOICE_TOTAL, Status=$INVOICE_STATUS"
else
  echo "❌ Failed to get invoice"
  echo "$INVOICE_RESPONSE"
  exit 1
fi
echo

# Test 4: Create payment for booking
echo "Test 4: Initiate payment for booking"
PAYMENT_RESPONSE=$(curl -s -X POST "$BASE_URL/payments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"booking_id\": $BOOKING_ID,
    \"currency\": \"USD\"
  }")

PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.id')
PAYMENT_AMOUNT=$(echo $PAYMENT_RESPONSE | jq -r '.amount')
PAYMENT_STATUS=$(echo $PAYMENT_RESPONSE | jq -r '.status')
CLIENT_SECRET=$(echo $PAYMENT_RESPONSE | jq -r '.client_secret')
GATEWAY_PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.gateway_payment_id')

if [ "$PAYMENT_ID" != "null" ] && [ "$PAYMENT_STATUS" == "pending" ]; then
  echo "✓ Payment created: ID=$PAYMENT_ID, Amount=$PAYMENT_AMOUNT, Status=$PAYMENT_STATUS"
  echo "  Client Secret: ${CLIENT_SECRET:0:30}..."
  echo "  Gateway Payment ID: $GATEWAY_PAYMENT_ID"
else
  echo "❌ Failed to create payment"
  echo "$PAYMENT_RESPONSE"
  exit 1
fi
echo

# Test 5: Verify payment defaults to invoice total
echo "Test 5: Verify payment amount matches invoice total"
if [ "$PAYMENT_AMOUNT" == "$INVOICE_TOTAL" ]; then
  echo "✓ Payment amount matches invoice total: $PAYMENT_AMOUNT"
else
  echo "❌ Payment amount mismatch: Payment=$PAYMENT_AMOUNT, Invoice=$INVOICE_TOTAL"
  exit 1
fi
echo

# Test 6: Get payment details
echo "Test 6: Get payment details"
PAYMENT_DETAIL=$(curl -s -X GET "$BASE_URL/payments/$PAYMENT_ID" \
  -H "Authorization: Bearer $TOKEN")

DETAIL_STATUS=$(echo $PAYMENT_DETAIL | jq -r '.status')

if [ "$DETAIL_STATUS" == "pending" ]; then
  echo "✓ Payment details retrieved: Status=$DETAIL_STATUS"
else
  echo "❌ Failed to get payment details"
  echo "$PAYMENT_DETAIL"
  exit 1
fi
echo

# Test 7: Simulate successful webhook
echo "Test 7: Simulate payment success webhook"
WEBHOOK_RESPONSE=$(curl -s -X POST "$BASE_URL/payments/webhooks/payment" \
  -H "Content-Type: application/json" \
  -H "x-webhook-signature: test_signature" \
  -d "{
    \"event_type\": \"payment_intent.succeeded\",
    \"payment_id\": \"$GATEWAY_PAYMENT_ID\",
    \"status\": \"completed\",
    \"data\": {
      \"payment_id\": $PAYMENT_ID,
      \"payment_method\": \"credit_card\"
    }
  }")

WEBHOOK_STATUS=$(echo $WEBHOOK_RESPONSE | jq -r '.status')

if [ "$WEBHOOK_STATUS" == "success" ]; then
  echo "✓ Webhook processed successfully"
else
  echo "❌ Webhook processing failed"
  echo "$WEBHOOK_RESPONSE"
  exit 1
fi
echo

# Wait a moment for processing
sleep 1

# Test 8: Verify payment status updated
echo "Test 8: Verify payment status updated to completed"
UPDATED_PAYMENT=$(curl -s -X GET "$BASE_URL/payments/$PAYMENT_ID" \
  -H "Authorization: Bearer $TOKEN")

UPDATED_STATUS=$(echo $UPDATED_PAYMENT | jq -r '.status')
PAID_AT=$(echo $UPDATED_PAYMENT | jq -r '.paid_at')
PAYMENT_METHOD=$(echo $UPDATED_PAYMENT | jq -r '.payment_method')

if [ "$UPDATED_STATUS" == "completed" ] && [ "$PAID_AT" != "null" ]; then
  echo "✓ Payment status updated: Status=$UPDATED_STATUS, Paid At=$PAID_AT"
  echo "  Payment Method: $PAYMENT_METHOD"
else
  echo "❌ Payment status not updated correctly"
  echo "$UPDATED_PAYMENT"
  exit 1
fi
echo

# Test 9: Verify invoice marked as paid
echo "Test 9: Verify invoice status updated to paid"
UPDATED_INVOICE=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID/invoice" \
  -H "Authorization: Bearer $TOKEN")

UPDATED_INVOICE_STATUS=$(echo $UPDATED_INVOICE | jq -r '.status')
INVOICE_PAID_AT=$(echo $UPDATED_INVOICE | jq -r '.paid_at')

if [ "$UPDATED_INVOICE_STATUS" == "paid" ] && [ "$INVOICE_PAID_AT" != "null" ]; then
  echo "✓ Invoice status updated: Status=$UPDATED_INVOICE_STATUS, Paid At=$INVOICE_PAID_AT"
else
  echo "❌ Invoice status not updated correctly"
  echo "$UPDATED_INVOICE"
  exit 1
fi
echo

# Test 10: Create partial payment
echo "Test 10: Create partial payment (deposit)"
PARTIAL_PAYMENT=$(curl -s -X POST "$BASE_URL/payments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"booking_id\": $BOOKING_ID,
    \"amount\": 500.00,
    \"currency\": \"USD\"
  }")

PARTIAL_ID=$(echo $PARTIAL_PAYMENT | jq -r '.id')
PARTIAL_AMOUNT=$(echo $PARTIAL_PAYMENT | jq -r '.amount')

# Convert to integer for comparison (500.0 -> 500)
PARTIAL_AMOUNT_INT=$(echo $PARTIAL_AMOUNT | cut -d. -f1)

if [ "$PARTIAL_ID" != "null" ] && [ "$PARTIAL_AMOUNT_INT" == "500" ]; then
  echo "✓ Partial payment created: ID=$PARTIAL_ID, Amount=$PARTIAL_AMOUNT"
else
  echo "❌ Failed to create partial payment"
  echo "$PARTIAL_PAYMENT"
  exit 1
fi
echo

# Test 11: Simulate failed payment webhook
echo "Test 11: Simulate payment failure webhook"
FAIL_WEBHOOK=$(curl -s -X POST "$BASE_URL/payments/webhooks/payment" \
  -H "Content-Type: application/json" \
  -H "x-webhook-signature: test_signature" \
  -d "{
    \"event_type\": \"payment_intent.failed\",
    \"payment_id\": \"$(echo $PARTIAL_PAYMENT | jq -r '.gateway_payment_id')\",
    \"status\": \"failed\",
    \"data\": {
      \"payment_id\": $PARTIAL_ID,
      \"failure_reason\": \"Insufficient funds\"
    }
  }")

FAIL_WEBHOOK_STATUS=$(echo $FAIL_WEBHOOK | jq -r '.status')

if [ "$FAIL_WEBHOOK_STATUS" == "success" ]; then
  echo "✓ Failure webhook processed"
else
  echo "❌ Failure webhook processing failed"
  echo "$FAIL_WEBHOOK"
  exit 1
fi
echo

sleep 1

# Test 12: Verify failed payment status
echo "Test 12: Verify failed payment status"
FAILED_PAYMENT=$(curl -s -X GET "$BASE_URL/payments/$PARTIAL_ID" \
  -H "Authorization: Bearer $TOKEN")

FAILED_STATUS=$(echo $FAILED_PAYMENT | jq -r '.status')
FAILURE_REASON=$(echo $FAILED_PAYMENT | jq -r '.failure_reason')

if [ "$FAILED_STATUS" == "failed" ] && [ "$FAILURE_REASON" != "null" ]; then
  echo "✓ Failed payment verified: Status=$FAILED_STATUS"
  echo "  Failure Reason: $FAILURE_REASON"
else
  echo "❌ Failed payment status incorrect"
  echo "$FAILED_PAYMENT"
  exit 1
fi
echo

echo "=== All Payment Tests Passed ✓ ==="
echo
echo "Summary:"
echo "- Booking ID: $BOOKING_ID"
echo "- Invoice Total: $INVOICE_TOTAL"
echo "- Successful Payment ID: $PAYMENT_ID ($PAYMENT_AMOUNT)"
echo "- Failed Payment ID: $PARTIAL_ID ($PARTIAL_AMOUNT)"
echo "- Invoice Status: $UPDATED_INVOICE_STATUS"
echo "- Payment Method: $PAYMENT_METHOD"
