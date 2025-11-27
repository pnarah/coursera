#!/bin/bash

# Test script for guest details and validation
# Tests guest count validation, primary guest requirement, ID document fields

BASE_URL="http://localhost:8001/api/v1"

echo "======================================"
echo "Guest Details & Validation Tests"
echo "======================================"
echo ""

# Step 1: Authenticate
echo "Step 1: Authenticating..."
curl -s -X POST "$BASE_URL/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "5551234567",
    "country_code": "+1"
  }' > /dev/null

sleep 1

AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "5551234567",
    "otp": "123456",
    "device_info": "test-device"
  }')

ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    echo "Failed to get access token"
    exit 1
fi

echo "Authenticated successfully"
echo ""

# Step 2: Create availability lock
echo "Step 2: Creating availability lock..."
LOCK_RESPONSE=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "double",
    "check_in_date": "2025-12-10",
    "check_out_date": "2025-12-12",
    "quantity": 1
  }')

LOCK_ID=$(echo "$LOCK_RESPONSE" | jq -r '.lock_id')
echo "Lock created: $LOCK_ID"
echo ""

# Test 1: Create booking with guest list (valid)
echo "======================================"
echo "Test 1: Create booking with valid guest list"
echo "======================================"
BOOKING_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "double",
    "check_in": "2025-12-10",
    "check_out": "2025-12-12",
    "guests": 2,
    "lock_id": "'$LOCK_ID'",
    "special_requests": "Late check-in",
    "guest_list": [
      {
        "guest_name": "John Doe",
        "guest_email": "john@example.com",
        "guest_phone": "+1234567890",
        "age": 35,
        "id_type": "passport",
        "id_number": "AB123456",
        "is_primary": true
      },
      {
        "guest_name": "Jane Doe",
        "guest_email": "jane@example.com",
        "age": 32,
        "is_primary": false
      }
    ]
  }')

echo "$BOOKING_RESPONSE" | jq '.'
BOOKING_ID=$(echo "$BOOKING_RESPONSE" | jq -r '.booking_id // empty')

if [ ! -z "$BOOKING_ID" ]; then
    echo "✓ Booking created with guests: $BOOKING_ID"
else
    echo "✗ Failed to create booking"
fi
echo ""

# Test 2: Get booking details (should include guest_details)
if [ ! -z "$BOOKING_ID" ]; then
    echo "======================================"
    echo "Test 2: Get booking details with guests"
    echo "======================================"
    BOOKING_DETAILS=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo "$BOOKING_DETAILS" | jq '.guest_details'
    
    GUEST_COUNT=$(echo "$BOOKING_DETAILS" | jq '.guest_details | length')
    if [ "$GUEST_COUNT" == "2" ]; then
        echo "✓ Guest details retrieved: $GUEST_COUNT guests"
    else
        echo "✗ Expected 2 guests, got: $GUEST_COUNT"
    fi
    echo ""
fi

# Test 3: Guest count mismatch (should fail)
echo "======================================"
echo "Test 3: Guest count mismatch validation"
echo "======================================"

# Create new lock
LOCK_RESPONSE2=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "single",
    "check_in_date": "2025-12-10",
    "check_out_date": "2025-12-12",
    "quantity": 1
  }')
LOCK_ID2=$(echo "$LOCK_RESPONSE2" | jq -r '.lock_id')

ERROR_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "single",
    "check_in": "2025-12-10",
    "check_out": "2025-12-12",
    "guests": 3,
    "lock_id": "'$LOCK_ID2'",
    "guest_list": [
      {
        "guest_name": "John Doe",
        "is_primary": true
      },
      {
        "guest_name": "Jane Doe",
        "is_primary": false
      }
    ]
  }')

echo "$ERROR_RESPONSE" | jq '.'
if echo "$ERROR_RESPONSE" | grep -q "must match guests count"; then
    echo "✓ Guest count mismatch correctly rejected"
else
    echo "✗ Expected validation error for guest count mismatch"
fi
echo ""

# Test 4: No primary guest (should fail)
echo "======================================"
echo "Test 4: No primary guest validation"
echo "======================================"

# Create new lock
LOCK_RESPONSE3=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "single",
    "check_in_date": "2025-12-13",
    "check_out_date": "2025-12-15",
    "quantity": 1
  }')
LOCK_ID3=$(echo "$LOCK_RESPONSE3" | jq -r '.lock_id')

ERROR_RESPONSE2=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "single",
    "check_in": "2025-12-13",
    "check_out": "2025-12-15",
    "guests": 1,
    "lock_id": "'$LOCK_ID3'",
    "guest_list": [
      {
        "guest_name": "John Doe",
        "is_primary": false
      }
    ]
  }')

echo "$ERROR_RESPONSE2" | jq '.'
if echo "$ERROR_RESPONSE2" | grep -q "primary"; then
    echo "✓ No primary guest correctly rejected"
else
    echo "✗ Expected validation error for missing primary guest"
fi
echo ""

# Test 5: ID document validation
echo "======================================"
echo "Test 5: ID document fields validation"
echo "======================================"

# Create new lock
LOCK_RESPONSE4=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "deluxe",
    "check_in_date": "2025-12-16",
    "check_out_date": "2025-12-18",
    "quantity": 1
  }')
LOCK_ID4=$(echo "$LOCK_RESPONSE4" | jq -r '.lock_id')

ERROR_RESPONSE3=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "deluxe",
    "check_in": "2025-12-16",
    "check_out": "2025-12-18",
    "guests": 1,
    "lock_id": "'$LOCK_ID4'",
    "guest_list": [
      {
        "guest_name": "John Doe",
        "id_number": "AB123456",
        "is_primary": true
      }
    ]
  }')

echo "$ERROR_RESPONSE3" | jq '.'
if echo "$ERROR_RESPONSE3" | grep -q "id_type"; then
    echo "✓ ID document validation working (id_type required when id_number provided)"
else
    echo "✗ Expected validation error for missing id_type"
fi
echo ""

# Test 6: Backwards compatibility (without guest_list)
echo "======================================"
echo "Test 6: Backwards compatibility without guest_list"
echo "======================================"

# Create new lock
LOCK_RESPONSE5=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "suite",
    "check_in_date": "2025-12-19",
    "check_out_date": "2025-12-21",
    "quantity": 1
  }')
LOCK_ID5=$(echo "$LOCK_RESPONSE5" | jq -r '.lock_id')

BOOKING_RESPONSE2=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "suite",
    "check_in": "2025-12-19",
    "check_out": "2025-12-21",
    "guests": 1,
    "lock_id": "'$LOCK_ID5'",
    "guest_name": "Legacy User",
    "guest_email": "legacy@example.com",
    "guest_phone": "+1987654321"
  }')

echo "$BOOKING_RESPONSE2" | jq '.'
BOOKING_ID2=$(echo "$BOOKING_RESPONSE2" | jq -r '.booking_id // empty')

if [ ! -z "$BOOKING_ID2" ]; then
    echo "✓ Backwards compatibility working"
else
    echo "✗ Failed to create booking without guest_list"
fi
echo ""

echo "======================================"
echo "All guest validation tests completed"
echo "======================================"
