#!/bin/bash

# Test script for invoice generation and updates (Task 15)
# Prerequisites: User must be logged in with valid JWT token

BASE_URL="http://localhost:8001/api/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# JWT token - replace with actual token from login
read -p "Enter your JWT token: " JWT_TOKEN

echo -e "\n${YELLOW}=== Task 15: Invoice Generation & Updates Tests ===${NC}\n"

# Step 0: Get availability lock
echo -e "${YELLOW}Step 0: Get availability lock${NC}"
LOCK_RESPONSE=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "double",
    "check_in_date": "2026-03-01",
    "check_out_date": "2026-03-03",
    "quantity": 1
  }')

LOCK_ID=$(echo $LOCK_RESPONSE | jq -r '.lock_id')
if [ "$LOCK_ID" != "null" ] && [ -n "$LOCK_ID" ]; then
    echo -e "${GREEN}✓ Lock obtained: $LOCK_ID${NC}"
else
    echo -e "${RED}✗ Failed to get lock${NC}"
    echo "Response: $LOCK_RESPONSE"
    exit 1
fi

# Test 1: Create booking (should auto-create invoice)
echo -e "\n${YELLOW}Test 1: Create booking (invoice should be auto-created)${NC}"
BOOKING_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "double",
    "check_in": "2026-03-01",
    "check_out": "2026-03-03",
    "guests": 2,
    "lock_id": "'"$LOCK_ID"'",
    "guest_list": [
      {
        "guest_name": "John Doe",
        "guest_email": "john.doe@example.com",
        "guest_phone": "+919876543210",
        "is_primary": true
      },
      {
        "guest_name": "Jane Doe",
        "guest_email": "jane.doe@example.com",
        "guest_phone": "+919876543211",
        "is_primary": false
      }
    ]
  }')

BOOKING_ID=$(echo $BOOKING_RESPONSE | jq -r '.booking_id')
BOOKING_TOTAL=$(echo $BOOKING_RESPONSE | jq -r '.total_amount')

if [ "$BOOKING_ID" != "null" ] && [ -n "$BOOKING_ID" ]; then
    echo -e "${GREEN}✓ Booking created: ID $BOOKING_ID, Total \$$BOOKING_TOTAL${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to create booking${NC}"
    echo "Response: $BOOKING_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    exit 1
fi

# Test 2: Get invoice (should exist)
echo -e "\n${YELLOW}Test 2: Get invoice for booking${NC}"
INVOICE_RESPONSE=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID/invoice" \
  -H "Authorization: Bearer $JWT_TOKEN")

INVOICE_ID=$(echo $INVOICE_RESPONSE | jq -r '.id')
INVOICE_NUMBER=$(echo $INVOICE_RESPONSE | jq -r '.invoice_number')
INVOICE_SUBTOTAL=$(echo $INVOICE_RESPONSE | jq -r '.subtotal')
INVOICE_TAX=$(echo $INVOICE_RESPONSE | jq -r '.tax_amount')
INVOICE_TOTAL=$(echo $INVOICE_RESPONSE | jq -r '.total_amount')
INVOICE_STATUS=$(echo $INVOICE_RESPONSE | jq -r '.status')
LINE_ITEMS_COUNT=$(echo $INVOICE_RESPONSE | jq -r '.line_items | length')

if [ "$INVOICE_ID" != "null" ] && [ "$INVOICE_NUMBER" != "null" ]; then
    echo -e "${GREEN}✓ Invoice retrieved: $INVOICE_NUMBER${NC}"
    echo "  - Subtotal: \$$INVOICE_SUBTOTAL"
    echo "  - Tax (18%): \$$INVOICE_TAX"
    echo "  - Total: \$$INVOICE_TOTAL"
    echo "  - Status: $INVOICE_STATUS"
    echo "  - Line Items: $LINE_ITEMS_COUNT"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to retrieve invoice${NC}"
    echo "Response: $INVOICE_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 3: Add service to booking
echo -e "\n${YELLOW}Test 3: Add Airport Pickup service${NC}"
SERVICE_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings/$BOOKING_ID/services" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": 1,
    "quantity": 2,
    "notes": "Pickup for 2 guests"
  }')

SERVICE_ID=$(echo $SERVICE_RESPONSE | jq -r '.id')
SERVICE_PRICE=$(echo $SERVICE_RESPONSE | jq -r '.total_price')
SERVICE_STATUS=$(echo $SERVICE_RESPONSE | jq -r '.status')

if [ "$SERVICE_ID" != "null" ]; then
    echo -e "${GREEN}✓ Service added: ID $SERVICE_ID, Price \$$SERVICE_PRICE, Status: $SERVICE_STATUS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to add service${NC}"
    echo "Response: $SERVICE_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 4: Get invoice again (should still have same total, service is PENDING)
echo -e "\n${YELLOW}Test 4: Get invoice (service PENDING, should not be included in total)${NC}"
INVOICE2_RESPONSE=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID/invoice" \
  -H "Authorization: Bearer $JWT_TOKEN")

INVOICE2_TOTAL=$(echo $INVOICE2_RESPONSE | jq -r '.total_amount')
INVOICE2_SERVICES_SUBTOTAL=$(echo $INVOICE2_RESPONSE | jq -r '.services_subtotal')
LINE_ITEMS2_COUNT=$(echo $INVOICE2_RESPONSE | jq -r '.line_items | length')

echo "  - Services Subtotal: \$$INVOICE2_SERVICES_SUBTOTAL"
echo "  - Total: \$$INVOICE2_TOTAL"
echo "  - Line Items: $LINE_ITEMS2_COUNT"

if [ "$INVOICE2_SERVICES_SUBTOTAL" == "0" ] || [ "$INVOICE2_SERVICES_SUBTOTAL" == "0.0" ]; then
    echo -e "${GREEN}✓ Pending service not included in invoice total${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Pending service incorrectly included in invoice${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 5: Mark service as COMPLETED
echo -e "\n${YELLOW}Test 5: Complete service (PENDING → CONFIRMED → IN_PROGRESS → COMPLETED)${NC}"

# PENDING → CONFIRMED
curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}' > /dev/null

# CONFIRMED → IN_PROGRESS
curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}' > /dev/null

# IN_PROGRESS → COMPLETED
COMPLETE_RESPONSE=$(curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}')

COMPLETE_STATUS=$(echo $COMPLETE_RESPONSE | jq -r '.status')

if [ "$COMPLETE_STATUS" == "completed" ]; then
    echo -e "${GREEN}✓ Service marked as COMPLETED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to complete service${NC}"
    echo "Response: $COMPLETE_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 6: Get invoice final (should include completed service)
echo -e "\n${YELLOW}Test 6: Get final invoice (should include completed service)${NC}"
sleep 1  # Brief pause to ensure invoice recalculation

INVOICE3_RESPONSE=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID/invoice" \
  -H "Authorization: Bearer $JWT_TOKEN")

INVOICE3_ROOM_SUBTOTAL=$(echo $INVOICE3_RESPONSE | jq -r '.room_subtotal')
INVOICE3_SERVICES_SUBTOTAL=$(echo $INVOICE3_RESPONSE | jq -r '.services_subtotal')
INVOICE3_SUBTOTAL=$(echo $INVOICE3_RESPONSE | jq -r '.subtotal')
INVOICE3_TAX=$(echo $INVOICE3_RESPONSE | jq -r '.tax_amount')
INVOICE3_TOTAL=$(echo $INVOICE3_RESPONSE | jq -r '.total_amount')
LINE_ITEMS3_COUNT=$(echo $INVOICE3_RESPONSE | jq -r '.line_items | length')

echo "  - Room Subtotal: \$$INVOICE3_ROOM_SUBTOTAL"
echo "  - Services Subtotal: \$$INVOICE3_SERVICES_SUBTOTAL"
echo "  - Subtotal: \$$INVOICE3_SUBTOTAL"
echo "  - Tax (18%): \$$INVOICE3_TAX"
echo "  - Total: \$$INVOICE3_TOTAL"
echo "  - Line Items: $LINE_ITEMS3_COUNT (1 room + 1 service)"

# Verify service is now included
if (( $(echo "$INVOICE3_SERVICES_SUBTOTAL > 0" | bc -l) )); then
    echo -e "${GREEN}✓ Completed service included in invoice${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Completed service not included in invoice${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 7: Verify line items
echo -e "\n${YELLOW}Test 7: Verify invoice line items${NC}"
echo "$INVOICE3_RESPONSE" | jq -r '.line_items[] | "  - \(.description): \(.quantity) x $\(.unit_price) = $\(.total_price) [\(.item_type)\(.status | if . then " - " + . else "" end)]"'

if [ "$LINE_ITEMS3_COUNT" == "2" ]; then
    echo -e "${GREEN}✓ Invoice has 2 line items (room + service)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Expected 2 line items, found $LINE_ITEMS3_COUNT${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 8: Verify tax calculation
echo -e "\n${YELLOW}Test 8: Verify tax calculation (18% of subtotal)${NC}"
EXPECTED_TAX=$(echo "scale=2; $INVOICE3_SUBTOTAL * 0.18" | bc)
TAX_DIFF=$(echo "scale=2; $INVOICE3_TAX - $EXPECTED_TAX" | bc | tr -d '-')

echo "  - Calculated Tax: \$$EXPECTED_TAX"
echo "  - Invoice Tax: \$$INVOICE3_TAX"

if (( $(echo "$TAX_DIFF < 0.01" | bc -l) )); then
    echo -e "${GREEN}✓ Tax calculation correct${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Tax calculation incorrect (diff: $TAX_DIFF)${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Summary
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed ✗${NC}"
    exit 1
fi
