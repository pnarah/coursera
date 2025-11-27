#!/bin/bash

# Test script for hotel search API
# Tests various search scenarios including city filtering, dates, guests, pagination

BASE_URL="http://localhost:8001/api/v1"

echo "======================================"
echo "Hotel Search API Test Suite"
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

# Helper function to test hotel search
test_hotel_search() {
    local test_name=$1
    shift
    local query_params="$@"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${BLUE}Test $TOTAL_TESTS: $test_name${NC}"
    
    response=$(curl -s "$BASE_URL/hotels/search?$query_params")
    
    echo "$response" | jq '.'
    
    # Check if response has required fields
    hotels_count=$(echo "$response" | jq -r '.hotels | length')
    total=$(echo "$response" | jq -r '.total')
    
    if [ "$hotels_count" != "null" ] && [ "$total" != "null" ]; then
        echo -e "${GREEN}✓ Found $hotels_count hotels (Total: $total)${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ Invalid response${NC}"
    fi
    echo ""
}

# Calculate dates for testing
TODAY=$(date +%Y-%m-%d)
NEXT_WEEK=$(date -v+7d +%Y-%m-%d 2>/dev/null || date -d "+7 days" +%Y-%m-%d)
NEXT_WEEK_CHECKOUT=$(date -v+10d +%Y-%m-%d 2>/dev/null || date -d "+10 days" +%Y-%m-%d)
NEXT_MONTH=$(date -v+30d +%Y-%m-%d 2>/dev/null || date -d "+30 days" +%Y-%m-%d)
NEXT_MONTH_CHECKOUT=$(date -v+33d +%Y-%m-%d 2>/dev/null || date -d "+33 days" +%Y-%m-%d)

echo "======================================"
echo "Scenario 1: Search All Hotels"
echo "======================================"
echo ""

test_hotel_search \
    "Get all hotels (no filters)" \
    "page=1&page_size=10"

echo "======================================"
echo "Scenario 2: Search by City"
echo "======================================"
echo ""

test_hotel_search \
    "Search hotels in New York" \
    "city=New%20York&page=1&page_size=10"

test_hotel_search \
    "Search hotels in Los Angeles" \
    "city=Los%20Angeles&page=1&page_size=10"

test_hotel_search \
    "Search hotels with partial city name (York)" \
    "city=York&page=1&page_size=10"

echo "======================================"
echo "Scenario 3: Search with Dates"
echo "======================================"
echo ""

test_hotel_search \
    "Search with check-in/check-out dates" \
    "check_in=$NEXT_WEEK&check_out=$NEXT_WEEK_CHECKOUT&page=1&page_size=10"

test_hotel_search \
    "Search with dates in New York" \
    "city=New%20York&check_in=$NEXT_MONTH&check_out=$NEXT_MONTH_CHECKOUT&page=1&page_size=10"

echo "======================================"
echo "Scenario 4: Search by Guests"
echo "======================================"
echo ""

test_hotel_search \
    "Search for 2 guests" \
    "guests=2&page=1&page_size=10"

test_hotel_search \
    "Search for 4 guests (family)" \
    "guests=4&page=1&page_size=10"

test_hotel_search \
    "Search for 2 guests with dates" \
    "guests=2&check_in=$NEXT_WEEK&check_out=$NEXT_WEEK_CHECKOUT&page=1&page_size=10"

echo "======================================"
echo "Scenario 5: Search by Star Rating"
echo "======================================"
echo ""

test_hotel_search \
    "Search 5-star hotels" \
    "star_rating=5&page=1&page_size=10"

test_hotel_search \
    "Search 3-star hotels" \
    "star_rating=3&page=1&page_size=10"

test_hotel_search \
    "Search 5-star hotels in New York" \
    "city=New%20York&star_rating=5&page=1&page_size=10"

echo "======================================"
echo "Scenario 6: Search by Price Range"
echo "======================================"
echo ""

test_hotel_search \
    "Search hotels under \$300 per night" \
    "max_price=300&page=1&page_size=10"

test_hotel_search \
    "Search hotels \$200-\$500 per night" \
    "min_price=200&max_price=500&page=1&page_size=10"

test_hotel_search \
    "Search budget hotels (under \$200)" \
    "max_price=200&page=1&page_size=10"

echo "======================================"
echo "Scenario 7: Combined Filters"
echo "======================================"
echo ""

test_hotel_search \
    "Search: New York, 5-star, 2 guests, with dates" \
    "city=New%20York&star_rating=5&guests=2&check_in=$NEXT_WEEK&check_out=$NEXT_WEEK_CHECKOUT&page=1&page_size=10"

test_hotel_search \
    "Search: Los Angeles, under \$400, 4 guests" \
    "city=Los%20Angeles&max_price=400&guests=4&page=1&page_size=10"

echo "======================================"
echo "Scenario 8: Pagination"
echo "======================================"
echo ""

test_hotel_search \
    "First page (5 results per page)" \
    "page=1&page_size=5"

test_hotel_search \
    "Second page (5 results per page)" \
    "page=2&page_size=5"

test_hotel_search \
    "Large page size (20 results)" \
    "page=1&page_size=20"

echo "======================================"
echo "Scenario 9: Empty Results"
echo "======================================"
echo ""

test_hotel_search \
    "Search non-existent city" \
    "city=NonExistentCity&page=1&page_size=10"

test_hotel_search \
    "Search with impossible price range" \
    "min_price=10000&page=1&page_size=10"

echo "======================================"
echo "Scenario 10: Get Hotel Details"
echo "======================================"
echo ""

TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -e "${BLUE}Test $TOTAL_TESTS: Get hotel details by ID${NC}"
response=$(curl -s "$BASE_URL/hotels/1")
echo "$response" | jq '.'
hotel_name=$(echo "$response" | jq -r '.name')
if [ "$hotel_name" != "null" ] && [ "$hotel_name" != "" ]; then
    echo -e "${GREEN}✓ Retrieved hotel: $hotel_name${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗ Failed to retrieve hotel${NC}"
fi
echo ""

TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -e "${BLUE}Test $TOTAL_TESTS: Get non-existent hotel${NC}"
response=$(curl -s "$BASE_URL/hotels/9999")
echo "$response" | jq '.'
error=$(echo "$response" | jq -r '.detail')
if [ "$error" == "Hotel not found" ]; then
    echo -e "${GREEN}✓ Correctly returns 404 for non-existent hotel${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗ Expected 404 error${NC}"
fi
echo ""

echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $((TOTAL_TESTS - PASSED_TESTS))${NC}"
echo ""

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}All hotel search tests completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
