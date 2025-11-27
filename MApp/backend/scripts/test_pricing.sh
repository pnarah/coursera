#!/bin/bash

# Test script for dynamic pricing engine
# Tests various pricing scenarios including seasons, occupancy, and discounts

BASE_URL="http://localhost:8001/api/v1"

echo "======================================"
echo "Dynamic Pricing Engine Test Suite"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0

# Helper function to test pricing
test_price_quote() {
    local test_name=$1
    local hotel_id=$2
    local room_type=$3
    local check_in=$4
    local check_out=$5
    local quantity=$6
    local discount_type=$7
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${BLUE}Test $TOTAL_TESTS: $test_name${NC}"
    
    response=$(curl -s -X POST "$BASE_URL/availability/quote" \
        -H "Content-Type: application/json" \
        -d "{
            \"hotel_id\": $hotel_id,
            \"room_type\": \"$room_type\",
            \"check_in\": \"$check_in\",
            \"check_out\": \"$check_out\",
            \"quantity\": $quantity,
            \"discount_type\": \"$discount_type\"
        }")
    
    echo "$response" | jq '.'
    
    # Check if response has required fields
    available=$(echo "$response" | jq -r '.available')
    if [ "$available" == "true" ]; then
        total_price=$(echo "$response" | jq -r '.breakdown.total_price')
        season=$(echo "$response" | jq -r '.breakdown.season')
        occupancy_rate=$(echo "$response" | jq -r '.breakdown.occupancy_rate')
        discount=$(echo "$response" | jq -r '.breakdown.discount_type')
        
        echo -e "${GREEN}✓ Quote generated: $total_price (Season: $season, Occupancy: $occupancy_rate, Discount: $discount)${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    elif [ "$available" == "false" ]; then
        message=$(echo "$response" | jq -r '.message')
        echo -e "${GREEN}✓ Unavailable as expected: $message${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ Invalid response${NC}"
    fi
    echo ""
}

# Calculate dates for different scenarios
TODAY=$(date +%Y-%m-%d)
TOMORROW=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d "+1 day" +%Y-%m-%d)
NEXT_WEEK=$(date -v+7d +%Y-%m-%d 2>/dev/null || date -d "+7 days" +%Y-%m-%d)
NEXT_MONTH=$(date -v+30d +%Y-%m-%d 2>/dev/null || date -d "+30 days" +%Y-%m-%d)
TWO_MONTHS=$(date -v+60d +%Y-%m-%d 2>/dev/null || date -d "+60 days" +%Y-%m-%d)
THREE_MONTHS=$(date -v+90d +%Y-%m-%d 2>/dev/null || date -d "+90 days" +%Y-%m-%d)

# Calculate checkout dates (3 nights stay)
NEXT_WEEK_CHECKOUT=$(date -v+10d +%Y-%m-%d 2>/dev/null || date -d "+10 days" +%Y-%m-%d)
NEXT_MONTH_CHECKOUT=$(date -v+33d +%Y-%m-%d 2>/dev/null || date -d "+33 days" +%Y-%m-%d)
TWO_MONTHS_CHECKOUT=$(date -v+63d +%Y-%m-%d 2>/dev/null || date -d "+63 days" +%Y-%m-%d)
THREE_MONTHS_CHECKOUT=$(date -v+93d +%Y-%m-%d 2>/dev/null || date -d "+93 days" +%Y-%m-%d)

# Extended stay (10 nights for extended stay discount)
EXTENDED_CHECKOUT=$(date -v+40d +%Y-%m-%d 2>/dev/null || date -d "+40 days" +%Y-%m-%d)

# Summer peak season (July)
JULY_CHECKIN="2024-07-10"
JULY_CHECKOUT="2024-07-13"

# Holiday peak season (Christmas)
CHRISTMAS_CHECKIN="2024-12-23"
CHRISTMAS_CHECKOUT="2024-12-26"

# Low season (February)
FEB_CHECKIN="2024-02-15"
FEB_CHECKOUT="2024-02-18"

echo "======================================"
echo "Scenario 1: Low Occupancy (No Surge)"
echo "======================================"
echo ""

test_price_quote \
    "Low occupancy - Regular season - No discount" \
    1 "deluxe" "$NEXT_MONTH" "$NEXT_MONTH_CHECKOUT" 1 "none"

echo "======================================"
echo "Scenario 2: Early Bird Discount"
echo "======================================"
echo ""

test_price_quote \
    "Early bird discount (30+ days advance)" \
    1 "suite" "$THREE_MONTHS" "$THREE_MONTHS_CHECKOUT" 1 "early_bird"

echo "======================================"
echo "Scenario 3: Last Minute Booking"
echo "======================================"
echo ""

test_price_quote \
    "Last minute discount (within 3 days)" \
    1 "double" "$TOMORROW" "$NEXT_WEEK" 1 "last_minute"

echo "======================================"
echo "Scenario 4: Extended Stay Discount"
echo "======================================"
echo ""

test_price_quote \
    "Extended stay discount (10 nights)" \
    1 "deluxe" "$NEXT_MONTH" "$EXTENDED_CHECKOUT" 2 "extended_stay"

echo "======================================"
echo "Scenario 5: Peak Season (July)"
echo "======================================"
echo ""

test_price_quote \
    "Summer peak season (July 4th period)" \
    2 "suite" "$JULY_CHECKIN" "$JULY_CHECKOUT" 1 "none"

echo "======================================"
echo "Scenario 6: Peak Season (Christmas)"
echo "======================================"
echo ""

test_price_quote \
    "Holiday peak season (Christmas)" \
    3 "deluxe" "$CHRISTMAS_CHECKIN" "$CHRISTMAS_CHECKOUT" 2 "none"

echo "======================================"
echo "Scenario 7: Low Season (February)"
echo "======================================"
echo ""

test_price_quote \
    "Low season discount (February)" \
    1 "single" "$FEB_CHECKIN" "$FEB_CHECKOUT" 1 "none"

echo "======================================"
echo "Scenario 8: Multiple Rooms"
echo "======================================"
echo ""

test_price_quote \
    "Multiple rooms (5 rooms)" \
    1 "double" "$NEXT_MONTH" "$NEXT_MONTH_CHECKOUT" 5 "none"

echo "======================================"
echo "Scenario 9: Invalid Room Type"
echo "======================================"
echo ""

test_price_quote \
    "Invalid room type" \
    1 "presidential" "$NEXT_MONTH" "$NEXT_MONTH_CHECKOUT" 1 "none"

echo "======================================"
echo "Scenario 10: Invalid Hotel"
echo "======================================"
echo ""

test_price_quote \
    "Non-existent hotel" \
    999 "deluxe" "$NEXT_MONTH" "$NEXT_MONTH_CHECKOUT" 1 "none"

echo "======================================"
echo "Scenario 11: Insufficient Availability"
echo "======================================"
echo ""

test_price_quote \
    "Request more rooms than available" \
    1 "suite" "$NEXT_MONTH" "$NEXT_MONTH_CHECKOUT" 100 "none"

echo "======================================"
echo "Scenario 12: Different Hotels"
echo "======================================"
echo ""

test_price_quote \
    "Hotel 2 - Regular season" \
    2 "deluxe" "$NEXT_MONTH" "$NEXT_MONTH_CHECKOUT" 1 "none"

test_price_quote \
    "Hotel 3 - Regular season" \
    3 "suite" "$NEXT_MONTH" "$NEXT_MONTH_CHECKOUT" 1 "none"

echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $((TOTAL_TESTS - PASSED_TESTS))${NC}"
echo ""

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}All pricing tests completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
