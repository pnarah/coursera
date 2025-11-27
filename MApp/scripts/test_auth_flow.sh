#!/bin/bash
# Test script for OTP authentication flow

BASE_URL="http://localhost:8001/api/v1"
MOBILE="5555555555"

echo "=================================================="
echo "Testing MApp Authentication Flow"
echo "=================================================="
echo ""

# Step 1: Send OTP
echo "Step 1: Sending OTP to mobile $MOBILE..."
RESPONSE=$(curl -s -X POST $BASE_URL/auth/send-otp \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"country_code\": \"+1\"}")

echo "Response: $RESPONSE"
echo ""

# Extract OTP from logs (in production, user receives via SMS)
echo "Step 2: Check logs for OTP (simulating SMS receipt)..."
sleep 2
OTP=$(tail -50 /tmp/mapp_backend.log | grep "Your MApp verification code is:" | tail -1 | awk '{print $6}')
echo "OTP received: $OTP"
echo ""

# Step 3: Verify OTP
echo "Step 3: Verifying OTP..."
RESPONSE=$(curl -s -X POST $BASE_URL/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP\", \"device_info\": \"Test Device\"}")

echo "Response: $RESPONSE" | jq .
echo ""

# Extract access token
ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')

if [ "$ACCESS_TOKEN" != "null" ]; then
    echo "✅ Authentication successful!"
    echo "Access Token: ${ACCESS_TOKEN:0:50}..."
else
    echo "❌ Authentication failed!"
fi

echo ""
echo "=================================================="
