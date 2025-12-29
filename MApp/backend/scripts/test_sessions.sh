#!/bin/bash

# Test script for session management endpoints
# Demonstrates listing, deleting specific, and deleting all sessions

echo "========================================"
echo "Session Management API Testing"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000/api/v1"
MOBILE="5551234567"
OTP="123456"

# Step 1: Create multiple sessions by logging in from different devices
echo "Step 1: Creating multiple sessions from different devices..."
echo "-----------------------------------------------------------"

TOKENS=()
DEVICE_NAMES=("iPhone-15" "MacBook-Pro" "iPad-Air")

for i in {0..2}; do
    echo ""
    echo "Creating session ${i} from ${DEVICE_NAMES[$i]}..."
    
    # Send OTP
    curl -s -X POST "$BASE_URL/auth/send-otp" \
        -H "Content-Type: application/json" \
        -d "{\"mobile_number\": \"$MOBILE\"}" > /dev/null
    
    sleep 1
    
    # Verify OTP with different User-Agent
    RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
        -H "Content-Type: application/json" \
        -H "User-Agent: ${DEVICE_NAMES[$i]}/1.0" \
        -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP\"}")
    
    TOKEN=$(echo $RESPONSE | jq -r '.access_token')
    TOKENS[$i]=$TOKEN
    
    if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
        echo "✓ Session created successfully"
        # Decode and show session ID
        SESSION_ID=$(echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
        echo "  Session ID: $SESSION_ID"
        echo "  Device: ${DEVICE_NAMES[$i]}"
    else
        echo "✗ Failed to create session"
        echo "  Response: $RESPONSE"
    fi
    
    sleep 2
done

echo ""
echo "========================================"
echo "Step 2: List all active sessions"
echo "========================================"
echo ""

# Use the first token to list sessions
if [ -n "${TOKENS[0]}" ]; then
    SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
        -H "Authorization: Bearer ${TOKENS[0]}" \
        -H "Content-Type: application/json")
    
    echo "Active sessions:"
    echo $SESSIONS | jq '.[] | {id: .id, device: .device_info, ip: .ip_address, is_current: .is_current, created: .created_at}'
    
    TOTAL_SESSIONS=$(echo $SESSIONS | jq 'length')
    echo ""
    echo "Total active sessions: $TOTAL_SESSIONS"
else
    echo "✗ No valid token available"
    exit 1
fi

echo ""
echo "========================================"
echo "Step 3: Delete a specific session"
echo "========================================"
echo ""

# Get the second session ID to delete it
if [ -n "${TOKENS[1]}" ]; then
    # Decode the session ID from the second token
    SESSION_TO_DELETE=$(echo ${TOKENS[1]} | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
    
    echo "Deleting session: $SESSION_TO_DELETE"
    
    # Use first token to delete second session
    DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/sessions/$SESSION_TO_DELETE" \
        -H "Authorization: Bearer ${TOKENS[0]}" \
        -H "Content-Type: application/json")
    
    echo $DELETE_RESPONSE | jq '.'
    
    # Verify deletion by listing sessions again
    echo ""
    echo "Remaining sessions after deletion:"
    SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
        -H "Authorization: Bearer ${TOKENS[0]}" \
        -H "Content-Type: application/json")
    echo $SESSIONS | jq '.[] | {id: .id, device: .device_info, is_current: .is_current}'
fi

echo ""
echo "========================================"
echo "Step 4: Test deleting current session (should fail)"
echo "========================================"
echo ""

# Try to delete current session
CURRENT_SESSION=$(echo ${TOKENS[0]} | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
echo "Attempting to delete current session: $CURRENT_SESSION"

DELETE_CURRENT=$(curl -s -X DELETE "$BASE_URL/sessions/$CURRENT_SESSION" \
    -H "Authorization: Bearer ${TOKENS[0]}" \
    -H "Content-Type: application/json")

echo $DELETE_CURRENT | jq '.'

echo ""
echo "========================================"
echo "Step 5: Delete all other sessions"
echo "========================================"
echo ""

echo "Deleting all sessions except current..."

DELETE_ALL_RESPONSE=$(curl -s -X DELETE "$BASE_URL/sessions" \
    -H "Authorization: Bearer ${TOKENS[0]}" \
    -H "Content-Type: application/json")

echo $DELETE_ALL_RESPONSE | jq '.'

echo ""
echo "Final session list (should only show current session):"
FINAL_SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer ${TOKENS[0]}" \
    -H "Content-Type: application/json")
echo $FINAL_SESSIONS | jq '.[] | {id: .id, device: .device_info, is_current: .is_current}'

echo ""
echo "========================================"
echo "Step 6: Verify database state"
echo "========================================"
echo ""

echo "Database session count:"
docker exec -it mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "
SELECT 
    COUNT(*) as total_sessions,
    COUNT(CASE WHEN is_active THEN 1 END) as active_sessions,
    COUNT(CASE WHEN NOT is_active THEN 1 END) as invalidated_sessions
FROM user_sessions 
WHERE user_id = (SELECT id FROM users WHERE mobile_number = '$MOBILE');"

echo ""
echo "Recent session details:"
docker exec -it mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "
SELECT 
    LEFT(id::text, 8) as session,
    device_info,
    is_active,
    invalidation_reason,
    created_at
FROM user_sessions 
WHERE user_id = (SELECT id FROM users WHERE mobile_number = '$MOBILE')
ORDER BY created_at DESC
LIMIT 5;"

echo ""
echo "========================================"
echo "Testing Complete!"
echo "========================================"
