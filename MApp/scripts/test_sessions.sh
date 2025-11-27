#!/bin/bash
# Test script for session management

BASE_URL="http://localhost:8001/api/v1"
MOBILE="7777777777"

echo "=================================================="
echo "Testing Session Management Flow"
echo "=================================================="
echo ""

# Step 1: Send OTP
echo "Step 1: Sending OTP to mobile $MOBILE..."
curl -s -X POST $BASE_URL/auth/send-otp \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"country_code\": \"+1\"}" | jq .
echo ""

# Get OTP from logs
sleep 2
OTP=$(tail -50 /tmp/mapp_backend.log | grep "Your MApp verification code is:" | tail -1 | awk '{print $6}')
echo "OTP received: $OTP"
echo ""

# Step 2: Login from Device 1
echo "Step 2: Login from Device 1 (iPhone)..."
RESPONSE1=$(curl -s -X POST $BASE_URL/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP\", \"device_info\": \"iPhone 15 Pro\"}")

TOKEN1=$(echo $RESPONSE1 | jq -r '.access_token')
echo "Token 1: ${TOKEN1:0:50}..."
echo ""

# Step 3: Send OTP again for second device
echo "Step 3: Sending OTP for second device login..."
curl -s -X POST $BASE_URL/auth/send-otp \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"country_code\": \"+1\"}" | jq .
echo ""

# Get new OTP
sleep 2
OTP2=$(tail -50 /tmp/mapp_backend.log | grep "Your MApp verification code is:" | tail -1 | awk '{print $6}')
echo "OTP received: $OTP2"
echo ""

# Step 4: Login from Device 2
echo "Step 4: Login from Device 2 (Android)..."
RESPONSE2=$(curl -s -X POST $BASE_URL/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP2\", \"device_info\": \"Samsung Galaxy S24\"}")

TOKEN2=$(echo $RESPONSE2 | jq -r '.access_token')
echo "Token 2: ${TOKEN2:0:50}..."
echo ""

# Step 5: List all sessions from Device 2
echo "Step 5: List all active sessions..."
curl -s -X GET $BASE_URL/auth/sessions \
  -H "Authorization: Bearer $TOKEN2" | jq .
echo ""

# Step 6: Revoke Device 1 session from Device 2
echo "Step 6: Get session IDs and revoke one..."
SESSIONS=$(curl -s -X GET $BASE_URL/auth/sessions -H "Authorization: Bearer $TOKEN2")
SESSION1_ID=$(echo $SESSIONS | jq -r '.sessions[1].session_id')

if [ "$SESSION1_ID" != "null" ] && [ ! -z "$SESSION1_ID" ]; then
    echo "Revoking session: $SESSION1_ID"
    curl -s -X DELETE "$BASE_URL/auth/sessions/$SESSION1_ID" \
      -H "Authorization: Bearer $TOKEN2" | jq .
    echo ""
fi

# Step 7: Try to use revoked token
echo "Step 7: Try to access with revoked token (should fail)..."
curl -s -X GET $BASE_URL/auth/sessions \
  -H "Authorization: Bearer $TOKEN1" | jq .
echo ""

# Step 8: Logout from all devices
echo "Step 8: Logout from all devices..."
curl -s -X POST $BASE_URL/auth/logout-all \
  -H "Authorization: Bearer $TOKEN2" | jq .
echo ""

# Step 9: Verify all sessions are revoked
echo "Step 9: Try to access after logout-all (should fail)..."
curl -s -X GET $BASE_URL/auth/sessions \
  -H "Authorization: Bearer $TOKEN2" | jq .
echo ""

echo "=================================================="
echo "Session Management Test Complete!"
echo "=================================================="
