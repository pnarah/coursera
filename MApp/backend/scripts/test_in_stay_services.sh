#!/bin/bash

# Test script for in-stay service ordering (Task 14)
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

echo -e "\n${YELLOW}=== Task 14: In-Stay Service Ordering Tests ===${NC}\n"

# Step 0: Get availability lock first
echo -e "${YELLOW}Step 0: Get availability lock${NC}"
LOCK_RESPONSE=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "double",
    "check_in_date": "2026-02-20",
    "check_out_date": "2026-02-22",
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

# Test 1: Create a booking without services (will add services later)
echo -e "\n${YELLOW}Test 1: Create booking without pre-services${NC}"
BOOKING_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "double",
    "check_in": "2026-02-20",
    "check_out": "2026-02-22",
    "guests": 1,
    "lock_id": "'"$LOCK_ID"'",
    "guest_list": [
      {
        "guest_name": "Alice Johnson",
        "guest_email": "alice.johnson@example.com",
        "guest_phone": "+919876543210",
        "is_primary": true
      }
    ]
  }')

BOOKING_ID=$(echo $BOOKING_RESPONSE | jq -r '.booking_id')
if [ "$BOOKING_ID" != "null" ] && [ -n "$BOOKING_ID" ]; then
    echo -e "${GREEN}✓ Booking created successfully: ID $BOOKING_ID${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to create booking${NC}"
    echo "Response: $BOOKING_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    exit 1
fi

# Test 2: Add first service (Airport Pickup) to the booking
echo -e "\n${YELLOW}Test 2: Add Airport Pickup service (quantity 1)${NC}"
SERVICE1_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings/$BOOKING_ID/services" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": 1,
    "quantity": 1,
    "notes": "Flight arrival at 3 PM"
  }')

SERVICE1_ID=$(echo $SERVICE1_RESPONSE | jq -r '.id')
SERVICE1_PRICE=$(echo $SERVICE1_RESPONSE | jq -r '.total_price')
SERVICE1_STATUS=$(echo $SERVICE1_RESPONSE | jq -r '.status')

if [ "$SERVICE1_ID" != "null" ] && [ "$SERVICE1_STATUS" = "pending" ]; then
    echo -e "${GREEN}✓ Service 1 added: ID $SERVICE1_ID, Price \$$SERVICE1_PRICE, Status: $SERVICE1_STATUS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to add service 1${NC}"
    echo "Response: $SERVICE1_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 3: Add second service (Breakfast Buffet) to the booking
echo -e "\n${YELLOW}Test 3: Add Breakfast Buffet service (quantity 2)${NC}"
SERVICE2_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings/$BOOKING_ID/services" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": 2,
    "quantity": 2,
    "notes": "For 2 guests, both mornings"
  }')

SERVICE2_ID=$(echo $SERVICE2_RESPONSE | jq -r '.id')
SERVICE2_PRICE=$(echo $SERVICE2_RESPONSE | jq -r '.total_price')
SERVICE2_STATUS=$(echo $SERVICE2_RESPONSE | jq -r '.status')

if [ "$SERVICE2_ID" != "null" ] && [ "$SERVICE2_STATUS" = "pending" ]; then
    echo -e "${GREEN}✓ Service 2 added: ID $SERVICE2_ID, Price \$$SERVICE2_PRICE, Status: $SERVICE2_STATUS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to add service 2${NC}"
    echo "Response: $SERVICE2_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 4: Update service 1 status: PENDING → CONFIRMED
echo -e "\n${YELLOW}Test 4: Update service 1 status to CONFIRMED${NC}"
UPDATE1_RESPONSE=$(curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE1_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "confirmed"
  }')

UPDATE1_STATUS=$(echo $UPDATE1_RESPONSE | jq -r '.status')
if [ "$UPDATE1_STATUS" = "confirmed" ]; then
    echo -e "${GREEN}✓ Service 1 status updated to CONFIRMED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to update service 1 status${NC}"
    echo "Response: $UPDATE1_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 5: Update service 1 status: CONFIRMED → IN_PROGRESS
echo -e "\n${YELLOW}Test 5: Update service 1 status to IN_PROGRESS${NC}"
UPDATE2_RESPONSE=$(curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE1_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress"
  }')

UPDATE2_STATUS=$(echo $UPDATE2_RESPONSE | jq -r '.status')
if [ "$UPDATE2_STATUS" = "in_progress" ]; then
    echo -e "${GREEN}✓ Service 1 status updated to IN_PROGRESS${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to update service 1 status${NC}"
    echo "Response: $UPDATE2_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 6: Update service 1 status: IN_PROGRESS → COMPLETED
echo -e "\n${YELLOW}Test 6: Update service 1 status to COMPLETED${NC}"
UPDATE3_RESPONSE=$(curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE1_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed"
  }')

UPDATE3_STATUS=$(echo $UPDATE3_RESPONSE | jq -r '.status')
if [ "$UPDATE3_STATUS" = "completed" ]; then
    echo -e "${GREEN}✓ Service 1 status updated to COMPLETED${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to update service 1 status${NC}"
    echo "Response: $UPDATE3_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 7: Get booking details and verify services are included
echo -e "\n${YELLOW}Test 7: Retrieve booking and verify services${NC}"
BOOKING_DETAIL=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID" \
  -H "Authorization: Bearer $JWT_TOKEN")

SERVICES_COUNT=$(echo $BOOKING_DETAIL | jq -r '.booking_services | length')
TOTAL_AMOUNT=$(echo $BOOKING_DETAIL | jq -r '.total_amount')

if [ "$SERVICES_COUNT" = "2" ]; then
    echo -e "${GREEN}✓ Booking has 2 services${NC}"
    echo "Service 1: $(echo $BOOKING_DETAIL | jq -r '.booking_services[0].service_name') - \$$(echo $BOOKING_DETAIL | jq -r '.booking_services[0].total_price') ($(echo $BOOKING_DETAIL | jq -r '.booking_services[0].status'))"
    echo "Service 2: $(echo $BOOKING_DETAIL | jq -r '.booking_services[1].service_name') - \$$(echo $BOOKING_DETAIL | jq -r '.booking_services[1].total_price') ($(echo $BOOKING_DETAIL | jq -r '.booking_services[1].status'))"
    echo "Total Amount: \$$TOTAL_AMOUNT"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Expected 2 services, found $SERVICES_COUNT${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 8: Try invalid status transition (should fail)
echo -e "\n${YELLOW}Test 8: Test invalid status transition (COMPLETED → PENDING should fail)${NC}"
INVALID_RESPONSE=$(curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE1_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "pending"
  }')

ERROR_DETAIL=$(echo $INVALID_RESPONSE | jq -r '.detail')
if [[ "$ERROR_DETAIL" == *"Invalid status transition"* ]]; then
    echo -e "${GREEN}✓ Invalid transition correctly rejected${NC}"
    echo "Error: $ERROR_DETAIL"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Invalid transition was not rejected${NC}"
    echo "Response: $INVALID_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 9: Cancel service 2 (PENDING → CANCELLED)
echo -e "\n${YELLOW}Test 9: Cancel service 2 (PENDING → CANCELLED)${NC}"
CANCEL_RESPONSE=$(curl -s -X PUT "$BASE_URL/bookings/$BOOKING_ID/services/$SERVICE2_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "cancelled"
  }')

CANCEL_STATUS=$(echo $CANCEL_RESPONSE | jq -r '.status')
if [ "$CANCEL_STATUS" = "cancelled" ]; then
    echo -e "${GREEN}✓ Service 2 cancelled successfully${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Failed to cancel service 2${NC}"
    echo "Response: $CANCEL_RESPONSE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 10: Verify final booking state
echo -e "\n${YELLOW}Test 10: Verify final booking state${NC}"
FINAL_BOOKING=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID" \
  -H "Authorization: Bearer $JWT_TOKEN")

SERVICE1_FINAL=$(echo $FINAL_BOOKING | jq -r '.booking_services[0].status')
SERVICE2_FINAL=$(echo $FINAL_BOOKING | jq -r '.booking_services[1].status')
FINAL_TOTAL=$(echo $FINAL_BOOKING | jq -r '.total_amount')

echo "Final State:"
echo "  - Service 1 (Airport Pickup): $SERVICE1_FINAL"
echo "  - Service 2 (Breakfast Buffet): $SERVICE2_FINAL"
echo "  - Total Amount: \$$FINAL_TOTAL"

if [ "$SERVICE1_FINAL" = "completed" ] && [ "$SERVICE2_FINAL" = "cancelled" ]; then
    echo -e "${GREEN}✓ Final state is correct${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ Final state is incorrect${NC}"
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
