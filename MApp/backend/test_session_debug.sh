#!/bin/bash

echo "Direct Session Management Test"
echo "==============================="
echo ""

# Use a fresh mobile number
MOBILE="8888888888"
BASE_URL="http://localhost:8000/api/v1"

echo "Step 1: Send OTP"
echo "----------------"
SEND_RESP=$(curl -s -X POST "$BASE_URL/auth/send-otp" \
    -H "Content-Type: application/json" \
    -d "{\"mobile_number\": \"$MOBILE\"}")

echo "$SEND_RESP" | jq '.'
echo ""

echo "Step 2: Check Redis for OTP"
echo "----------------------------"
sleep 1

# Try different key patterns
echo "Trying key: otp:$MOBILE"
docker exec mapp_redis redis-cli GET "otp:$MOBILE"

echo ""
echo "All OTP keys in Redis:"
docker exec mapp_redis redis-cli KEYS "otp:*"

echo ""
echo "All keys in Redis:"
docker exec mapp_redis redis-cli KEYS "*" | head -10

echo ""
echo "Step 3: Try with DEBUG test number (5551234567)"
echo "------------------------------------------------"

# Clear rate limit first
docker exec mapp_redis redis-cli DEL "otp_rate:5551234567" > /dev/null 2>&1

curl -s -X POST "$BASE_URL/auth/send-otp" \
    -H "Content-Type: application/json" \
    -d '{"mobile_number": "5551234567"}' | jq '.'

echo ""
echo "Verifying with fixed OTP 123456..."
sleep 1

VERIFY_RESP=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
    -H "Content-Type: application/json" \
    -H "User-Agent: TestDevice/1.0" \
    -d '{"mobile_number": "5551234567", "otp": "123456"}')

echo "$VERIFY_RESP" | jq '.'

TOKEN=$(echo "$VERIFY_RESP" | jq -r '.access_token // empty')

if [ ! -z "$TOKEN" ]; then
    echo ""
    echo "✓ Successfully got token!"
    echo "Token: ${TOKEN:0:60}..."
    
    echo ""
    echo "Step 4: List sessions"
    echo "---------------------"
    SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
        -H "Authorization: Bearer $TOKEN")
    
    echo "$SESSIONS" | jq '.'
    
    # Extract details
    USER_ID=$(echo "$VERIFY_RESP" | jq -r '.user.id')
    SESSION_ID=$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
    
    echo ""
    echo "Step 5: Check session in Redis"
    echo "-------------------------------"
    echo "User ID: $USER_ID"
    echo "Session ID: $SESSION_ID"
    
    if [ ! -z "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
        REDIS_SESSION=$(docker exec mapp_redis redis-cli GET "session:${USER_ID}:${SESSION_ID}")
        echo "Session data:"
        echo "$REDIS_SESSION" | jq '.' 2>/dev/null || echo "$REDIS_SESSION"
        
        TTL=$(docker exec mapp_redis redis-cli TTL "session:${USER_ID}:${SESSION_ID}")
        echo "TTL: $TTL seconds"
    fi
    
    echo ""
    echo "Step 6: Check session in PostgreSQL"
    echo "------------------------------------"
    docker exec mapp_postgres psql -U postgres -d mapp_db -c \
        "SELECT id, user_id, device_info, is_active, 
                to_char(created_at, 'HH24:MI:SS') as created,
                to_char(expires_at, 'HH24:MI:SS') as expires
         FROM user_sessions 
         WHERE user_id = $USER_ID
         ORDER BY created_at DESC LIMIT 3;" 2>/dev/null
    
else
    echo ""
    echo "❌ Failed to get token"
    echo "Response: $VERIFY_RESP"
fi
