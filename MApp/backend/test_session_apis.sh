#!/bin/bash

echo "Testing Session Management APIs"
echo "================================"
echo ""

# First, login to get a token
echo "1. Logging in to get access token..."
curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
    -H "Content-Type: application/json" \
    -d '{"mobile_number": "5551234567"}' > /dev/null

sleep 1

RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify-otp \
    -H "Content-Type: application/json" \
    -H "User-Agent: TestDevice/1.0" \
    -d '{"mobile_number": "5551234567", "otp": "123456"}')

TOKEN=$(echo $RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "Failed to get token. Response:"
    echo $RESPONSE | jq '.'
    exit 1
fi

echo "✓ Logged in successfully"
echo ""

# Test 1: List sessions
echo "2. Testing GET /api/v1/sessions (list all sessions)"
echo "---------------------------------------------------"
SESSIONS=$(curl -s -X GET http://localhost:8000/api/v1/sessions \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo $SESSIONS | jq '.'
echo ""

# Test 2: Try to delete current session (should fail)
echo "3. Testing DELETE current session (should fail)"
echo "------------------------------------------------"
CURRENT_SESSION=$(echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
echo "Current session ID: $CURRENT_SESSION"

DELETE_CURRENT=$(curl -s -X DELETE "http://localhost:8000/api/v1/sessions/$CURRENT_SESSION" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo $DELETE_CURRENT | jq '.'
echo ""

# Test 3: Delete all sessions except current
echo "4. Testing DELETE /api/v1/sessions (delete all except current)"
echo "---------------------------------------------------------------"
DELETE_ALL=$(curl -s -X DELETE http://localhost:8000/api/v1/sessions \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo $DELETE_ALL | jq '.'
echo ""

# Test 4: List sessions again
echo "5. Listing sessions after deletion"
echo "-----------------------------------"
FINAL_SESSIONS=$(curl -s -X GET http://localhost:8000/api/v1/sessions \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo $FINAL_SESSIONS | jq '.'
echo ""

echo "Testing complete!"
