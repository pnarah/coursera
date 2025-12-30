#!/bin/bash
set -e

# Send OTP
curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "8888888888", "country_code": "+1"}' > /dev/null

sleep 1

# Verify OTP and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"mobile_number": "8888888888", "country_code": "+1", "otp": "123456"}' | jq -r '.access_token')

echo "Access Token obtained: ${TOKEN:0:50}..."

# Call metrics with verbose
echo -e "\n=== Calling /api/v1/admin/metrics ==="
curl -v -X GET "http://localhost:8000/api/v1/admin/metrics" \
  -H "Authorization: Bearer $TOKEN" 2>&1 | tail -20

