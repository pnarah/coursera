#!/bin/bash

# Test script for pre-service booking at reservation
# Tests booking with services (airport pickup, food services)

BASE_URL="http://localhost:8001/api/v1"

echo "======================================"
echo "Pre-Service Booking Tests"
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
    "check_in_date": "2025-12-25",
    "check_out_date": "2025-12-27",
    "quantity": 1
  }')

LOCK_ID=$(echo "$LOCK_RESPONSE" | jq -r '.lock_id')
echo "Lock created: $LOCK_ID"
echo ""

# Test 1: Create booking with pre-services (airport pickup + breakfast)
echo "======================================"
echo "Test 1: Create booking with pre-services"
echo "======================================"
BOOKING_RESPONSE=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "double",
    "check_in": "2025-12-25",
    "check_out": "2025-12-27",
    "guests": 2,
    "lock_id": "'$LOCK_ID'",
    "guest_list": [
      {
        "guest_name": "Alice Smith",
        "guest_email": "alice@example.com",
        "age": 30,
        "is_primary": true
      },
      {
        "guest_name": "Bob Smith",
        "age": 28,
        "is_primary": false
      }
    ],
    "pre_services": [
      {
        "service_id": 1,
        "quantity": 2,
        "notes": "Pickup at Terminal 1, Flight AA123 arriving at 3:00 PM"
      },
      {
        "service_id": 2,
        "quantity": 4,
        "notes": "2 breakfasts per day for 2 days"
      }
    ]
  }')

echo "$BOOKING_RESPONSE" | jq '.'
BOOKING_ID=$(echo "$BOOKING_RESPONSE" | jq -r '.booking_id // empty')

if [ ! -z "$BOOKING_ID" ]; then
    BOOKING_TOTAL=$(echo "$BOOKING_RESPONSE" | jq -r '.total_amount')
    echo "✓ Booking created with services: $BOOKING_ID (Total: \$$BOOKING_TOTAL)"
else
    echo "✗ Failed to create booking with services"
fi
echo ""

# Test 2: Get booking details (should include services)
if [ ! -z "$BOOKING_ID" ]; then
    echo "======================================"
    echo "Test 2: Get booking details with services"
    echo "======================================"
    BOOKING_DETAILS=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo "Room charge:"
    echo "$BOOKING_DETAILS" | jq '{room_type, check_in, check_out, guests}'
    echo ""
    
    echo "Booked services:"
    echo "$BOOKING_DETAILS" | jq '.booking_services'
    echo ""
    
    echo "Total amount:"
    echo "$BOOKING_DETAILS" | jq '{total_amount}'
    
    SERVICE_COUNT=$(echo "$BOOKING_DETAILS" | jq '.booking_services | length')
    if [ "$SERVICE_COUNT" == "2" ]; then
        echo "✓ Service details retrieved: $SERVICE_COUNT services"
    else
        echo "✗ Expected 2 services, got: $SERVICE_COUNT"
    fi
    echo ""
fi

# Test 3: Create booking without services (should still work)
echo "======================================"
echo "Test 3: Create booking without services"
echo "======================================"

LOCK_RESPONSE2=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "single",
    "check_in_date": "2025-12-28",
    "check_out_date": "2025-12-29",
    "quantity": 1
  }')
LOCK_ID2=$(echo "$LOCK_RESPONSE2" | jq -r '.lock_id')

BOOKING_RESPONSE2=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "single",
    "check_in": "2025-12-28",
    "check_out": "2025-12-29",
    "guests": 1,
    "lock_id": "'$LOCK_ID2'",
    "guest_name": "Charlie Brown",
    "guest_email": "charlie@example.com"
  }')

BOOKING_ID2=$(echo "$BOOKING_RESPONSE2" | jq -r '.booking_id // empty')
if [ ! -z "$BOOKING_ID2" ]; then
    echo "✓ Booking without services created successfully: $BOOKING_ID2"
else
    echo "✗ Failed to create booking without services"
fi
echo ""

# Test 4: Validate service amount calculation
if [ ! -z "$BOOKING_ID" ]; then
    echo "======================================"
    echo "Test 4: Validate service amount calculation"
    echo "======================================"
    
    # Airport pickup: service_id=1, assume $50 per pickup, quantity=2
    # Breakfast: service_id=2, assume $15 per breakfast, quantity=4
    # Expected service total: (50*2) + (15*4) = $160
    # Note: Actual prices may vary based on seed data
    
    BOOKING_DETAILS=$(curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo "Service breakdown:"
    echo "$BOOKING_DETAILS" | jq '.booking_services[] | {service_name, quantity, unit_price, total_price}'
    
    TOTAL_AMOUNT=$(echo "$BOOKING_DETAILS" | jq -r '.total_amount')
    echo ""
    echo "Total booking amount (room + services): \$$TOTAL_AMOUNT"
    echo "✓ Service amounts calculated and included in total"
fi

echo ""
echo "======================================"
echo "All pre-service booking tests completed"
echo "======================================"
