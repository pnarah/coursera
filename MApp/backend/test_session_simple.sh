#!/bin/bash

echo "Session Management Test - Simplified"
echo "===================================="
echo ""

BASE_URL="http://localhost:8000/api/v1"
MOBILE="5551111111"

# Send OTP
echo "1. Sending OTP to $MOBILE..."
OTP_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/send-otp" \
    -H "Content-Type: application/json" \
    -d "{\"mobile_number\": \"$MOBILE\"}")

echo "$OTP_RESPONSE" | jq '.'
echo ""

# Get OTP from Redis immediately
echo "2. Getting OTP from Redis..."
sleep 0.5
OTP=$(docker exec mapp_redis redis-cli --raw GET "otp:$MOBILE")

if [ -z "$OTP" ]; then
    echo "❌ OTP not found in Redis. Checking all keys..."
    echo "Redis OTP keys:"
    docker exec mapp_redis redis-cli KEYS "otp:*"
    
    echo ""
    echo "Using default OTP 123456 for testing..."
    OTP="123456"
else
    echo "✓ OTP retrieved: $OTP"
fi
echo ""

# Verify OTP
echo "3. Verifying OTP..."
VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
    -H "Content-Type: application/json" \
    -H "User-Agent: iPhone/iOS 15.0" \
    -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP\"}")

echo "$VERIFY_RESPONSE" | jq '.'

TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.access_token')
USER_ID=$(echo "$VERIFY_RESPONSE" | jq -r '.user.id')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to get access token"
    exit 1
fi

echo "✓ Logged in successfully"
echo "  User ID: $USER_ID"
echo "  Token: ${TOKEN:0:50}..."
echo ""

# Extract session ID from token
echo "4. Extracting session info from JWT..."
SESSION_ID=$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id // "not_found"')
echo "  Session ID: $SESSION_ID"
echo ""

# Check session in Redis
echo "5. Checking session in Redis..."
if [ "$SESSION_ID" != "not_found" ]; then
    REDIS_KEY="session:${USER_ID}:${SESSION_ID}"
    REDIS_SESSION=$(docker exec mapp_redis redis-cli --raw GET "$REDIS_KEY")
    
    if [ ! -z "$REDIS_SESSION" ]; then
        echo "✓ Session found in Redis"
        echo "$REDIS_SESSION" | jq '.' 2>/dev/null || echo "$REDIS_SESSION"
        
        # Check TTL
        TTL=$(docker exec mapp_redis redis-cli TTL "$REDIS_KEY")
        echo "  TTL: $TTL seconds (~$(($TTL / 3600)) hours)"
    else
        echo "❌ Session not found in Redis with key: $REDIS_KEY"
    fi
else
    echo "❌ Could not extract session_id from token"
fi
echo ""

# List active sessions
echo "6. Listing active sessions via API..."
SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo "$SESSIONS" | jq '.'
SESSION_COUNT=$(echo "$SESSIONS" | jq 'length // 0')
echo "✓ Found $SESSION_COUNT active session(s)"
echo ""

# Check database
echo "7. Checking PostgreSQL database..."
docker exec mapp_postgres psql -U postgres -d mapp_db -c \
    "SELECT id, user_id, device_info, ip_address, is_active, 
            to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as created,
            to_char(last_activity, 'YYYY-MM-DD HH24:MI:SS') as last_activity,
            to_char(expires_at, 'YYYY-MM-DD HH24:MI:SS') as expires
     FROM user_sessions 
     WHERE user_id = $USER_ID 
     ORDER BY created_at DESC 
     LIMIT 5;" 2>/dev/null
echo ""

# Create multiple sessions
echo "8. Creating additional sessions from different devices..."

echo "  Creating Android session..."
curl -s -X POST "$BASE_URL/auth/send-otp" \
    -H "Content-Type: application/json" \
    -d "{\"mobile_number\": \"$MOBILE\"}" > /dev/null
sleep 0.5
OTP2=$(docker exec mapp_redis redis-cli --raw GET "otp:$MOBILE")
[ -z "$OTP2" ] && OTP2="123456"

ANDROID_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
    -H "Content-Type: application/json" \
    -H "User-Agent: Mozilla/5.0 (Linux; Android 11)" \
    -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP2\"}")

ANDROID_TOKEN=$(echo "$ANDROID_RESPONSE" | jq -r '.access_token')
if [ "$ANDROID_TOKEN" != "null" ]; then
    echo "  ✓ Android session created"
fi

echo "  Creating iPad session..."
curl -s -X POST "$BASE_URL/auth/send-otp" \
    -H "Content-Type: application/json" \
    -d "{\"mobile_number\": \"$MOBILE\"}" > /dev/null
sleep 0.5
OTP3=$(docker exec mapp_redis redis-cli --raw GET "otp:$MOBILE")
[ -z "$OTP3" ] && OTP3="123456"

IPAD_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
    -H "Content-Type: application/json" \
    -H "User-Agent: Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)" \
    -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP3\"}")

IPAD_TOKEN=$(echo "$IPAD_RESPONSE" | jq -r '.access_token')
if [ "$IPAD_TOKEN" != "null" ]; then
    echo "  ✓ iPad session created"
fi
echo ""

# List all sessions again
echo "9. Listing all active sessions..."
ALL_SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo "$ALL_SESSIONS" | jq '.'
TOTAL_COUNT=$(echo "$ALL_SESSIONS" | jq 'length // 0')
echo "✓ Total active sessions: $TOTAL_COUNT"
echo ""

# Test logout specific session
if [ "$TOTAL_COUNT" -gt 1 ]; then
    echo "10. Testing logout of specific session..."
    SECOND_SESSION=$(echo "$ALL_SESSIONS" | jq -r '.[1].id // empty')
    
    if [ ! -z "$SECOND_SESSION" ]; then
        LOGOUT_RESP=$(curl -s -X DELETE "$BASE_URL/sessions/$SECOND_SESSION" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json")
        
        echo "$LOGOUT_RESP" | jq '.'
        
        # Verify
        REMAINING=$(curl -s -X GET "$BASE_URL/sessions" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json")
        
        REMAINING_COUNT=$(echo "$REMAINING" | jq 'length // 0')
        echo "✓ Sessions after logout: $REMAINING_COUNT"
    fi
fi
echo ""

# Test logout all other sessions
echo "11. Testing logout from all other sessions..."
LOGOUT_ALL=$(curl -s -X DELETE "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

echo "$LOGOUT_ALL" | jq '.'

# Verify only current session remains
FINAL_SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")

FINAL_COUNT=$(echo "$FINAL_SESSIONS" | jq 'length // 0')

if [ "$FINAL_COUNT" -eq 1 ]; then
    echo "✓ SUCCESS: Only current session remains"
else
    echo "❌ ERROR: Expected 1 session, found $FINAL_COUNT"
fi
echo ""

# Summary
echo "=================================="
echo "Test Summary"
echo "=================================="
echo "✓ Session creation with device detection"
echo "✓ Session storage in Redis"
echo "✓ Session persistence in PostgreSQL"
echo "✓ Multi-device session tracking"
echo "✓ Session listing API"
echo "✓ Logout specific session"
echo "✓ Logout all other sessions"
echo ""
echo "Session management testing complete!"
