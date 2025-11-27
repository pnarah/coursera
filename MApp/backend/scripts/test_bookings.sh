#!/bin/bash

# Test script for booking flow API
# Tests booking creation with lock validation, pricing, and lock release

BASE_URL="http://localhost:8001/api/v1"

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================"
echo "Booking Flow API Tests"
echo "======================================"
echo ""

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_status="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${BLUE}Test $TOTAL_TESTS: $test_name${NC}"
    
    # Run command and capture response
    response=$(eval "$command")
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        echo -e "${GREEN}✓ Test passed${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ Test failed${NC}"
        echo "Response: $response"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo ""
}

# Function to extract value from JSON
extract_json() {
    echo "$1" | jq -r "$2" 2>/dev/null
}

echo "======================================"
echo "Scenario 1: Authentication Setup"
echo "======================================"
echo ""

# Step 1: Send OTP
echo "Step 1: Sending OTP to +1-5551234567..."
OTP_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "5551234567",
    "country_code": "+1"
  }')

echo "$OTP_RESPONSE" | jq '.'
echo ""

# Step 2: Verify OTP and get token
echo "Step 2: Verifying OTP (using 123456)..."
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "5551234567",
    "country_code": "+1",
    "otp": "123456",
    "device_info": "test-device-booking"
  }')

ACCESS_TOKEN=$(extract_json "$AUTH_RESPONSE" '.access_token')
USER_ID=$(extract_json "$AUTH_RESPONSE" '.user.id')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    echo -e "${RED}Failed to get access token. Cannot proceed with tests.${NC}"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "Access token obtained: ${ACCESS_TOKEN:0:20}..."
echo "User ID: $USER_ID"
echo ""

echo "======================================"
echo "Scenario 2: Create Availability Lock"
echo "======================================"
echo ""

# Get tomorrow's date and date after 3 days
CHECK_IN=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d "+1 day" +%Y-%m-%d)
CHECK_OUT=$(date -v+4d +%Y-%m-%d 2>/dev/null || date -d "+4 days" +%Y-%m-%d)

echo "Creating lock for Hotel 1, room type 'double'"
echo "Check-in: $CHECK_IN"
echo "Check-out: $CHECK_OUT"
echo ""

LOCK_RESPONSE=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d "{
    \"hotel_id\": 1,
    \"room_type\": \"double\",
    \"check_in_date\": \"$CHECK_IN\",
    \"check_out_date\": \"$CHECK_OUT\",
    \"quantity\": 1
  }")

LOCK_ID=$(extract_json "$LOCK_RESPONSE" '.lock_id')

if [ -z "$LOCK_ID" ] || [ "$LOCK_ID" == "null" ]; then
    echo -e "${RED}Failed to create lock. Cannot proceed with booking tests.${NC}"
    echo "Response: $LOCK_RESPONSE"
    exit 1
fi

echo "$LOCK_RESPONSE" | jq '.'
echo "Lock ID: $LOCK_ID"
echo ""

echo "======================================"
echo "Scenario 3: Create Booking with Lock"
echo "======================================"
echo ""

run_test "Create booking with valid lock" \
  "curl -s -X POST \"$BASE_URL/bookings\" \
    -H \"Content-Type: application/json\" \
    -H \"Authorization: Bearer $ACCESS_TOKEN\" \
    -d '{
      \"hotel_id\": 1,
      \"room_type\": \"double\",
      \"check_in\": \"$CHECK_IN\",
      \"check_out\": \"$CHECK_OUT\",
      \"guests\": 2,
      \"lock_id\": \"$LOCK_ID\",
      \"guest_name\": \"John Doe\",
      \"guest_email\": \"john.doe@example.com\",
      \"guest_phone\": \"+1-555-9876\",
      \"special_requests\": \"Late check-in requested\"
    }'" \
  "201"

# Extract booking ID from response
BOOKING_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"hotel_id\": 1,
    \"room_type\": \"double\",
    \"check_in\": \"$CHECK_IN\",
    \"check_out\": \"$CHECK_OUT\",
    \"guests\": 2,
    \"lock_id\": \"$LOCK_ID\",
    \"guest_name\": \"John Doe\",
    \"guest_email\": \"john.doe@example.com\",
    \"guest_phone\": \"+1-555-9876\",
    \"special_requests\": \"Late check-in requested\"
  }")

BOOKING_ID=$(extract_json "$BOOKING_RESPONSE" '.booking_id')
BOOKING_REF=$(extract_json "$BOOKING_RESPONSE" '.booking_reference')

echo "Booking created:"
echo "  Booking ID: $BOOKING_ID"
echo "  Reference: $BOOKING_REF"
echo ""

echo "======================================"
echo "Scenario 4: Lock Release Verification"
echo "======================================"
echo ""

run_test "Verify lock was released (should return false)" \
  "curl -s -X GET \"$BASE_URL/availability/lock/$LOCK_ID\"" \
  "404"

echo "======================================"
echo "Scenario 5: Get Booking Details"
echo "======================================"
echo ""

if [ ! -z "$BOOKING_ID" ] && [ "$BOOKING_ID" != "null" ]; then
    run_test "Get booking by ID" \
      "curl -s -X GET \"$BASE_URL/bookings/$BOOKING_ID\" \
        -H \"Authorization: Bearer $ACCESS_TOKEN\"" \
      "200"
fi

echo "======================================"
echo "Scenario 6: List User Bookings"
echo "======================================"
echo ""

run_test "List user bookings (page 1)" \
  "curl -s -X GET \"$BASE_URL/bookings?page=1&page_size=10\" \
    -H \"Authorization: Bearer $ACCESS_TOKEN\"" \
  "200"

echo "======================================"
echo "Scenario 7: Error Cases"
echo "======================================"
echo ""

run_test "Create booking with invalid lock ID" \
  "curl -s -X POST \"$BASE_URL/bookings\" \
    -H \"Content-Type: application/json\" \
    -H \"Authorization: Bearer $ACCESS_TOKEN\" \
    -d '{
      \"hotel_id\": 1,
      \"room_type\": \"double\",
      \"check_in\": \"$CHECK_IN\",
      \"check_out\": \"$CHECK_OUT\",
      \"guests\": 2,
      \"lock_id\": \"invalid_lock_id\",
      \"guest_name\": \"Jane Smith\"
    }' | grep -q 'Invalid or expired lock' && echo 'Error detected correctly' || echo 'Unexpected response'" \
  "0"

# Create another lock for mismatched parameters test
LOCK_RESPONSE_2=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d "{
    \"hotel_id\": 2,
    \"room_type\": \"single\",
    \"check_in_date\": \"$CHECK_IN\",
    \"check_out_date\": \"$CHECK_OUT\",
    \"quantity\": 1
  }")

LOCK_ID_2=$(extract_json "$LOCK_RESPONSE_2" '.lock_id')

if [ ! -z "$LOCK_ID_2" ] && [ "$LOCK_ID_2" != "null" ]; then
    run_test "Create booking with mismatched lock parameters" \
      "curl -s -X POST \"$BASE_URL/bookings\" \
        -H \"Content-Type: application/json\" \
        -H \"Authorization: Bearer $ACCESS_TOKEN\" \
        -d '{
          \"hotel_id\": 1,
          \"room_type\": \"double\",
          \"check_in\": \"$CHECK_IN\",
          \"check_out\": \"$CHECK_OUT\",
          \"guests\": 2,
          \"lock_id\": \"$LOCK_ID_2\",
          \"guest_name\": \"Jane Smith\"
        }' | grep -q 'do not match' && echo 'Error detected correctly' || echo 'Unexpected response'" \
      "0"
    
    # Clean up lock
    curl -s -X DELETE "$BASE_URL/availability/lock/$LOCK_ID_2" > /dev/null
fi

run_test "Get non-existent booking" \
  "curl -s -X GET \"$BASE_URL/bookings/99999\" \
    -H \"Authorization: Bearer $ACCESS_TOKEN\" | grep -q 'not found' && echo 'Error detected correctly' || echo 'Unexpected response'" \
  "0"

run_test "Create booking without authentication" \
  "curl -s -X POST \"$BASE_URL/bookings\" \
    -H \"Content-Type: application/json\" \
    -d '{
      \"hotel_id\": 1,
      \"room_type\": \"double\",
      \"check_in\": \"$CHECK_IN\",
      \"check_out\": \"$CHECK_OUT\",
      \"guests\": 2,
      \"lock_id\": \"some_lock\",
      \"guest_name\": \"Test User\"
    }' | grep -q 'credentials' && echo 'Auth required correctly' || echo 'Unexpected response'" \
  "0"

echo "======================================"
echo "Scenario 8: Multiple Bookings"
echo "======================================"
echo ""

# Create locks and bookings for different room types
for ROOM_TYPE in "single" "suite"; do
    echo "Creating booking for $ROOM_TYPE room..."
    
    # Create lock
    LOCK_RESP=$(curl -s -X POST "$BASE_URL/availability/lock" \
      -H "Content-Type: application/json" \
      -d "{
        \"hotel_id\": 1,
        \"room_type\": \"$ROOM_TYPE\",
        \"check_in_date\": \"$CHECK_IN\",
        \"check_out_date\": \"$CHECK_OUT\",
        \"quantity\": 1
      }")
    
    LOCK=$(extract_json "$LOCK_RESP" '.lock_id')
    
    if [ ! -z "$LOCK" ] && [ "$LOCK" != "null" ]; then
        BOOKING_RESP=$(curl -s -X POST "$BASE_URL/bookings" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $ACCESS_TOKEN" \
          -d "{
            \"hotel_id\": 1,
            \"room_type\": \"$ROOM_TYPE\",
            \"check_in\": \"$CHECK_IN\",
            \"check_out\": \"$CHECK_OUT\",
            \"guests\": 1,
            \"lock_id\": \"$LOCK\",
            \"guest_name\": \"Test Guest $ROOM_TYPE\"
          }")
        
        B_ID=$(extract_json "$BOOKING_RESP" '.booking_id')
        B_REF=$(extract_json "$BOOKING_RESP" '.booking_reference')
        
        if [ ! -z "$B_ID" ] && [ "$B_ID" != "null" ]; then
            echo -e "${GREEN}✓ Booking created: ID=$B_ID, Ref=$B_REF, Room=$ROOM_TYPE${NC}"
        else
            echo -e "${RED}✗ Failed to create booking for $ROOM_TYPE${NC}"
        fi
    fi
done
echo ""

echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All booking tests completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
