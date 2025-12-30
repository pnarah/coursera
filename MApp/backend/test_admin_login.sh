#!/bin/bash

# Step 1: Send OTP
echo "=== Sending OTP to 8888888888 ==="
SEND_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "8888888888", "country_code": "+1"}')
echo "$SEND_RESPONSE" | jq .

# Step 2: Verify OTP
echo -e "\n=== Verifying OTP ==="
VERIFY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "8888888888", "country_code": "+1", "otp": "123456"}')
echo "$VERIFY_RESPONSE" | jq .

# Extract token
TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.access_token')
echo -e "\nAccess Token: $TOKEN"

# Step 3: Get Platform Metrics
echo -e "\n=== Getting Platform Metrics ==="
curl -s -X GET http://localhost:8000/api/v1/admin/metrics \
  -H "Authorization: Bearer $TOKEN" | jq .

