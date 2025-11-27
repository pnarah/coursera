#!/bin/bash

# Test script for Availability Locking APIs
# This script tests lock creation, status checking, extension, and release

BASE_URL="http://localhost:8001/api/v1"

echo "=================================="
echo "Testing Availability Locking APIs"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Create a lock for SUITE rooms
echo -e "${BLUE}Test 1: Create availability lock for 2 SUITE rooms${NC}"
CHECK_IN=$(date -v+7d +%Y-%m-%d)
CHECK_OUT=$(date -v+10d +%Y-%m-%d)
echo "POST $BASE_URL/availability/lock"
echo "Check-in: $CHECK_IN, Check-out: $CHECK_OUT"
LOCK_RESPONSE=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "SUITE",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 2
  }')
echo "$LOCK_RESPONSE" | jq '.'
LOCK_ID=$(echo "$LOCK_RESPONSE" | jq -r '.lock_id')
echo -e "${GREEN}Lock ID: $LOCK_ID${NC}"
echo ""

# Test 2: Check lock status
echo -e "${BLUE}Test 2: Check lock status${NC}"
echo "GET $BASE_URL/availability/lock/$LOCK_ID"
curl -s -X GET "$BASE_URL/availability/lock/$LOCK_ID" | jq '.'
echo ""

# Test 3: Try to create another lock for same rooms (should work as there are 3 SUITE rooms)
echo -e "${BLUE}Test 3: Create second lock for 1 SUITE room (should succeed)${NC}"
echo "POST $BASE_URL/availability/lock"
LOCK_RESPONSE_2=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "SUITE",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 1
  }')
echo "$LOCK_RESPONSE_2" | jq '.'
LOCK_ID_2=$(echo "$LOCK_RESPONSE_2" | jq -r '.lock_id')
echo -e "${GREEN}Second Lock ID: $LOCK_ID_2${NC}"
echo ""

# Test 4: Try to over-lock (should fail - total 3 SUITE rooms, already locked 3)
echo -e "${BLUE}Test 4: Try to over-lock (should fail - insufficient rooms)${NC}"
echo "POST $BASE_URL/availability/lock"
curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "SUITE",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 1
  }' | jq '.'
echo ""

# Test 5: Extend first lock
echo -e "${BLUE}Test 5: Extend first lock TTL${NC}"
echo "POST $BASE_URL/availability/lock/$LOCK_ID/extend"
curl -s -X POST "$BASE_URL/availability/lock/$LOCK_ID/extend" | jq '.'
echo ""

# Test 6: Release second lock
echo -e "${BLUE}Test 6: Release second lock${NC}"
echo "POST $BASE_URL/availability/release"
curl -s -X POST "$BASE_URL/availability/release" \
  -H "Content-Type: application/json" \
  -d '{
    "lock_id": "'"$LOCK_ID_2"'"
  }' | jq '.'
echo ""

# Test 7: Check second lock status (should not exist)
echo -e "${BLUE}Test 7: Check released lock status (should not exist)${NC}"
echo "GET $BASE_URL/availability/lock/$LOCK_ID_2"
curl -s -X GET "$BASE_URL/availability/lock/$LOCK_ID_2" | jq '.'
echo ""

# Test 8: Try to create lock for released capacity (should now succeed)
echo -e "${BLUE}Test 8: Create lock after release (should succeed with freed capacity)${NC}"
echo "POST $BASE_URL/availability/lock"
LOCK_RESPONSE_3=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "SUITE",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 1
  }')
echo "$LOCK_RESPONSE_3" | jq '.'
LOCK_ID_3=$(echo "$LOCK_RESPONSE_3" | jq -r '.lock_id')
echo ""

# Test 9: Lock different room type (DOUBLE)
echo -e "${BLUE}Test 9: Lock different room type (DOUBLE)${NC}"
echo "POST $BASE_URL/availability/lock"
LOCK_RESPONSE_4=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "DOUBLE",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 3
  }')
echo "$LOCK_RESPONSE_4" | jq '.'
LOCK_ID_4=$(echo "$LOCK_RESPONSE_4" | jq -r '.lock_id')
echo ""

# Test 10: Lock for different hotel
echo -e "${BLUE}Test 10: Lock for different hotel${NC}"
echo "POST $BASE_URL/availability/lock"
LOCK_RESPONSE_5=$(curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 2,
    "room_type": "SINGLE",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 2
  }')
echo "$LOCK_RESPONSE_5" | jq '.'
LOCK_ID_5=$(echo "$LOCK_RESPONSE_5" | jq -r '.lock_id')
echo ""

# Test 11: Error - Invalid room type
echo -e "${BLUE}Test 11: Test error - Invalid room type${NC}"
echo "POST $BASE_URL/availability/lock"
curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "INVALID",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 1
  }' | jq '.'
echo ""

# Test 12: Error - Past check-in date
echo -e "${BLUE}Test 12: Test error - Past check-in date${NC}"
PAST_DATE=$(date -v-1d +%Y-%m-%d)
echo "POST $BASE_URL/availability/lock (check-in: $PAST_DATE)"
curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 1,
    "room_type": "SUITE",
    "check_in_date": "'"$PAST_DATE"'",
    "check_out_date": "'"$CHECK_IN"'",
    "quantity": 1
  }' | jq '.'
echo ""

# Test 13: Error - Invalid hotel ID
echo -e "${BLUE}Test 13: Test error - Invalid hotel ID${NC}"
echo "POST $BASE_URL/availability/lock"
curl -s -X POST "$BASE_URL/availability/lock" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_id": 9999,
    "room_type": "SUITE",
    "check_in_date": "'"$CHECK_IN"'",
    "check_out_date": "'"$CHECK_OUT"'",
    "quantity": 1
  }' | jq '.'
echo ""

# Cleanup: Release all locks
echo -e "${YELLOW}Cleanup: Releasing all locks${NC}"
for LOCK in "$LOCK_ID" "$LOCK_ID_3" "$LOCK_ID_4" "$LOCK_ID_5"; do
  if [ "$LOCK" != "null" ] && [ ! -z "$LOCK" ]; then
    echo "Releasing lock: $LOCK"
    curl -s -X POST "$BASE_URL/availability/release" \
      -H "Content-Type: application/json" \
      -d '{"lock_id": "'"$LOCK"'"}' | jq -r '.message'
  fi
done
echo ""

# Summary
echo "=================================="
echo -e "${GREEN}All availability locking tests completed!${NC}"
echo "=================================="
echo ""
echo -e "${YELLOW}Endpoints tested:${NC}"
echo "  ✓ POST /availability/lock"
echo "  ✓ POST /availability/release"
echo "  ✓ GET  /availability/lock/{lock_id}"
echo "  ✓ POST /availability/lock/{lock_id}/extend"
echo ""
echo -e "${YELLOW}Test coverage:${NC}"
echo "  ✓ Create locks with quantity validation"
echo "  ✓ Check lock status and TTL"
echo "  ✓ Extend lock TTL"
echo "  ✓ Release locks (manual)"
echo "  ✓ Over-lock prevention (insufficient rooms)"
echo "  ✓ Multi-lock handling (same room type)"
echo "  ✓ Different room types (independent locks)"
echo "  ✓ Different hotels (independent locks)"
echo "  ✓ Error handling (invalid room type, dates, hotel)"
echo ""
echo -e "${YELLOW}Lock TTL: 2 minutes (120 seconds)${NC}"
echo -e "${YELLOW}Lock key format: availability_lock:{lock_id}${NC}"
echo -e "${YELLOW}Quantity key format: locked_quantity:{hotel_id}:{room_type}:{check_in}:{check_out}${NC}"
echo ""
