#!/bin/bash

# Test script for Room APIs
# This script tests all room endpoints including search and availability checking

BASE_URL="http://localhost:8001/api/v1"

echo "=================================="
echo "Testing Room APIs"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Get room types
echo -e "${BLUE}Test 1: Get available room types${NC}"
echo "GET $BASE_URL/rooms/types"
ROOM_TYPES=$(curl -s -X GET "$BASE_URL/rooms/types")
echo "Response: $ROOM_TYPES"
echo ""

# Test 2: List rooms for a hotel (Hotel ID 1 - Grand Manhattan Hotel)
echo -e "${BLUE}Test 2: List rooms for Hotel ID 1 (Grand Manhattan Hotel)${NC}"
echo "GET $BASE_URL/hotels/1/rooms?skip=0&limit=5"
HOTEL_ROOMS=$(curl -s -X GET "$BASE_URL/hotels/1/rooms?skip=0&limit=5")
echo "$HOTEL_ROOMS" | jq '{total: .total, returned: (.rooms | length), rooms: [.rooms[] | {id, room_number, room_type, capacity, base_price, hotel_name}]}'
echo ""

# Test 3: Get specific room details
echo -e "${BLUE}Test 3: Get details for Room ID 1${NC}"
echo "GET $BASE_URL/rooms/1"
ROOM_DETAILS=$(curl -s -X GET "$BASE_URL/rooms/1")
echo "$ROOM_DETAILS" | jq '{id, room_number, room_type, capacity, base_price, hotel_name, city, amenities}'
echo ""

# Test 4: Search rooms by room type (SUITE)
echo -e "${BLUE}Test 4: Search for SUITE rooms${NC}"
echo "GET $BASE_URL/rooms/search?room_type=SUITE&limit=5"
SUITE_ROOMS=$(curl -s -X GET "$BASE_URL/rooms/search?room_type=SUITE&limit=5")
echo "$SUITE_ROOMS" | jq '{total: .total, rooms: [.rooms[] | {id, room_number, room_type, capacity, base_price, hotel_name, city}]}'
echo ""

# Test 5: Search rooms by price range
echo -e "${BLUE}Test 5: Search rooms with price <= 200${NC}"
echo "GET $BASE_URL/rooms/search?max_price=200&limit=5"
PRICE_SEARCH=$(curl -s -X GET "$BASE_URL/rooms/search?max_price=200&limit=5")
echo "$PRICE_SEARCH" | jq '{total: .total, rooms: [.rooms[] | {id, room_number, room_type, base_price, hotel_name}]}'
echo ""

# Test 6: Search rooms by city
echo -e "${BLUE}Test 6: Search rooms in Los Angeles${NC}"
echo "GET $BASE_URL/rooms/search?city=Los%20Angeles&limit=5"
LA_ROOMS=$(curl -s -X GET "$BASE_URL/rooms/search?city=Los%20Angeles&limit=5")
echo "$LA_ROOMS" | jq '{total: .total, rooms: [.rooms[] | {id, room_number, room_type, base_price, hotel_name, city}]}'
echo ""

# Test 7: Search rooms by capacity
echo -e "${BLUE}Test 7: Search rooms with capacity >= 4${NC}"
echo "GET $BASE_URL/rooms/search?min_capacity=4&limit=5"
CAPACITY_SEARCH=$(curl -s -X GET "$BASE_URL/rooms/search?min_capacity=4&limit=5")
echo "$CAPACITY_SEARCH" | jq '{total: .total, rooms: [.rooms[] | {id, room_number, room_type, capacity, base_price, hotel_name}]}'
echo ""

# Test 8: Complex search (city + room type + price)
echo -e "${BLUE}Test 8: Complex search - DOUBLE rooms in New York City, price <= 500${NC}"
echo "GET $BASE_URL/rooms/search?city=New%20York&room_type=DOUBLE&max_price=500&limit=5"
COMPLEX_SEARCH=$(curl -s -X GET "$BASE_URL/rooms/search?city=New%20York&room_type=DOUBLE&max_price=500&limit=5")
echo "$COMPLEX_SEARCH" | jq '{total: .total, rooms: [.rooms[] | {id, room_number, room_type, base_price, hotel_name, city}]}'
echo ""

# Test 9: Check availability for future dates (no bookings yet)
echo -e "${BLUE}Test 9: Check availability for Hotel 1 (future dates)${NC}"
CHECK_IN=$(date -v+7d +%Y-%m-%d)
CHECK_OUT=$(date -v+10d +%Y-%m-%d)
echo "POST $BASE_URL/rooms/availability"
echo "Check-in: $CHECK_IN, Check-out: $CHECK_OUT"
AVAILABILITY=$(curl -s -X POST "$BASE_URL/rooms/availability" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'"
  }')
echo "$AVAILABILITY" | jq '{hotel_name, check_in_date, check_out_date, nights, total_available, sample_rooms: [.available_rooms[:3] | .[] | {room_id, room_number, room_type, capacity, base_price}]}'
echo ""

# Test 10: Check availability with room type filter
echo -e "${BLUE}Test 10: Check availability for SUITE rooms only${NC}"
echo "POST $BASE_URL/rooms/availability"
SUITE_AVAILABILITY=$(curl -s -X POST "$BASE_URL/rooms/availability" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "room_type": "SUITE"
  }')
echo "$SUITE_AVAILABILITY" | jq '{hotel_name, room_type_filter: "SUITE", total_available, available_rooms: [.available_rooms[] | {room_id, room_number, room_type, capacity, base_price}]}'
echo ""

# Test 11: Check availability with capacity filter
echo -e "${BLUE}Test 11: Check availability for rooms with capacity >= 4${NC}"
echo "POST $BASE_URL/rooms/availability"
CAPACITY_AVAILABILITY=$(curl -s -X POST "$BASE_URL/rooms/availability" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 2,
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "min_capacity": 4
  }')
echo "$CAPACITY_AVAILABILITY" | jq '{hotel_name, capacity_filter: ">=4", total_available, available_rooms: [.available_rooms[] | {room_id, room_number, room_type, capacity, base_price}]}'
echo ""

# Test 12: Test pagination
echo -e "${BLUE}Test 12: Test pagination - Get rooms 5-10 for Hotel 1${NC}"
echo "GET $BASE_URL/hotels/1/rooms?skip=5&limit=5"
PAGINATED_ROOMS=$(curl -s -X GET "$BASE_URL/hotels/1/rooms?skip=5&limit=5")
echo "$PAGINATED_ROOMS" | jq '{total, skip, limit, returned: (.rooms | length), rooms: [.rooms[] | {id, room_number, room_type}]}'
echo ""

# Test 13: Test error - invalid hotel ID
echo -e "${BLUE}Test 13: Test error handling - Invalid hotel ID${NC}"
echo "GET $BASE_URL/hotels/999/rooms"
ERROR_RESPONSE=$(curl -s -X GET "$BASE_URL/hotels/999/rooms")
echo "$ERROR_RESPONSE" | jq '.'
echo ""

# Test 14: Test error - past check-in date
echo -e "${BLUE}Test 14: Test validation - Past check-in date${NC}"
PAST_DATE=$(date -v-1d +%Y-%m-%d)
echo "POST $BASE_URL/rooms/availability (check-in: $PAST_DATE)"
PAST_DATE_ERROR=$(curl -s -X POST "$BASE_URL/rooms/availability" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "check_in_date": "'"$PAST_DATE"'",
    "check_out_date": "'"$CHECK_IN"'"
  }')
echo "$PAST_DATE_ERROR" | jq '.'
echo ""

# Test 15: Test error - check-out before check-in
echo -e "${BLUE}Test 15: Test validation - Check-out before check-in${NC}"
echo "POST $BASE_URL/rooms/availability"
INVALID_DATES=$(curl -s -X POST "$BASE_URL/rooms/availability" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "check_in_date": "'"$CHECK_OUT"'",
    "check_out_date": "'"$CHECK_IN"'"
  }')
echo "$INVALID_DATES" | jq '.'
echo ""

# Summary
echo "=================================="
echo -e "${GREEN}All room API tests completed!${NC}"
echo "=================================="
echo ""
echo -e "${YELLOW}Endpoints tested:${NC}"
echo "  ✓ GET  /rooms/types"
echo "  ✓ GET  /hotels/{hotel_id}/rooms"
echo "  ✓ GET  /rooms/{room_id}"
echo "  ✓ GET  /rooms/search (multiple filters)"
echo "  ✓ POST /rooms/availability (with filters)"
echo ""
echo -e "${YELLOW}Test coverage:${NC}"
echo "  ✓ List hotel rooms with pagination"
echo "  ✓ Get room details"
echo "  ✓ Search by room type, price, city, capacity"
echo "  ✓ Complex multi-filter search"
echo "  ✓ Check availability for date ranges"
echo "  ✓ Availability filtering by room type and capacity"
echo "  ✓ Error handling (invalid IDs, dates)"
echo "  ✓ Input validation"
echo ""
