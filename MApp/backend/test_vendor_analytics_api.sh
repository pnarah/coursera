#!/bin/bash

# Test script for /api/v1/vendor/analytics endpoint

BASE_URL="http://localhost:8000"
MOBILE="9999999999"
OTP="123456"

echo "======================================================================"
echo "Testing Vendor Analytics API Endpoint"
echo "======================================================================"
echo ""

# Step 1: Send OTP
echo "Step 1: Sending OTP to $MOBILE..."
curl -s -X POST "$BASE_URL/api/v1/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"country_code\": \"+1\"}" | python3 -m json.tool
echo ""
echo ""

# Step 2: Verify OTP and get token
echo "Step 2: Verifying OTP and getting access token..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP\"}")

echo "$TOKEN_RESPONSE" | python3 -m json.tool
echo ""
echo ""

# Extract access token
TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))")

if [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to get access token"
    exit 1
fi

echo "Access Token: ${TOKEN:0:50}..."
echo ""
echo ""

# Step 3: Call vendor analytics endpoint
echo "Step 3: Fetching vendor analytics..."
echo "======================================================================"
curl -s -X GET "$BASE_URL/api/v1/vendor/analytics" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""
echo ""

# Step 4: Call vendor hotels endpoint for comparison
echo "Step 4: Fetching vendor hotels (for context)..."
echo "======================================================================"
curl -s -X GET "$BASE_URL/api/v1/vendor/hotels" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""
echo ""
echo "======================================================================"
echo "Test Complete!"
echo "======================================================================"
