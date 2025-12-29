#!/bin/bash

echo "Comprehensive Redis & Session Testing"
echo "======================================"
echo ""

# Test 1: Check Redis directly
echo "TEST 1: Direct Redis Test"
echo "--------------------------"
docker exec mapp_redis redis-cli SET "direct_test" "working" EX 60
VALUE=$(docker exec mapp_redis redis-cli GET "direct_test")
echo "Direct Redis test: $VALUE"
echo ""

# Test 2: Check Python Redis connection
echo "TEST 2: Python Redis Connection"
echo "--------------------------------"
cd /Users/pnarah/git-pnarah/MApp/backend
/Users/pnarah/git-pnarah/MApp/backend/venv/bin/python -c "
import asyncio
from redis.asyncio import Redis

async def test():
    redis = Redis.from_url('redis://localhost:6379/0', encoding='utf-8', decode_responses=True)
    await redis.setex('python_test', 60, 'working')
    value = await redis.get('python_test')
    print(f'Python Redis test: {value}')
    await redis.aclose()

asyncio.run(test())
"
sleep 1
PYTHON_TEST=$(docker exec mapp_redis redis-cli GET "python_test")
echo "Redis value from CLI: $PYTHON_TEST"
echo ""

# Test 3: Check what the backend actually stores
echo "TEST 3: Backend OTP Flow"
echo "------------------------"
MOBILE="6666666666"

# Clear any existing data for this number
docker exec mapp_redis redis-cli DEL "otp:$MOBILE" > /dev/null 2>&1
docker exec mapp_redis redis-cli DEL "otp_rate:$MOBILE" > /dev/null 2>&1

echo "Sending OTP to $MOBILE..."
RESP=$(curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
    -H "Content-Type: application/json" \
    -d "{\"mobile_number\": \"$MOBILE\"}")

echo "$RESP" | jq '.'

# Immediately check all Redis keys
echo ""
echo "All Redis keys immediately after OTP send:"
docker exec mapp_redis redis-cli KEYS "*"

echo ""
echo "Checking specific OTP key patterns:"
docker exec mapp_redis redis-cli KEYS "otp:*"
docker exec mapp_redis redis-cli KEYS "*$MOBILE*"

# Check rate limit key
RATE_KEY=$(docker exec mapp_redis redis-cli KEYS "*rate*$MOBILE*")
if [ ! -z "$RATE_KEY" ]; then
    echo "Rate limit key found: $RATE_KEY"
    RATE_VALUE=$(docker exec mapp_redis redis-cli GET "$RATE_KEY")
    echo "Rate limit value: $RATE_VALUE"
fi

echo ""
echo "TEST 4: Check Backend Logs"
echo "--------------------------"
echo "Recent backend logs (if available):"
tail -20 /tmp/backend.log 2>/dev/null || echo "No log file found"

echo ""
echo "TEST 5: Test with Fixed OTP Number"
echo "-----------------------------------"

# Use test number with fixed OTP
TEST_MOBILE="5551234567"

# Clear rate limit
docker exec mapp_redis redis-cli FLUSHDB > /dev/null 2>&1

echo "Sending OTP to test number $TEST_MOBILE (should use fixed OTP 123456)..."
TEST_RESP=$(curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
    -H "Content-Type: application/json" \
    -d "{\"mobile_number\": \"$TEST_MOBILE\"}")

echo "$TEST_RESP" | jq '.'

sleep 1

echo ""
echo "Attempting verification with fixed OTP..."
VERIFY_RESP=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify-otp \
    -H "Content-Type: application/json" \
    -H "User-Agent: TestDevice/iOS 15.0" \
    -d "{\"mobile_number\": \"$TEST_MOBILE\", \"otp\": \"123456\"}")

echo "$VERIFY_RESP" | jq '.'

TOKEN=$(echo "$VERIFY_RESP" | jq -r '.access_token // empty')

if [ ! -z "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
    echo ""
    echo "✓ SUCCESS! Got access token"
    echo "Token preview: ${TOKEN:0:60}..."
    
    # Now test session management
    echo ""
    echo "TEST 6: Session Management APIs"
    echo "--------------------------------"
    
    echo "Listing sessions..."
    SESSIONS=$(curl -s -X GET http://localhost:8000/api/v1/sessions \
        -H "Authorization: Bearer $TOKEN")
    
    echo "$SESSIONS" | jq '.'
    
    SESSION_COUNT=$(echo "$SESSIONS" | jq 'length // 0')
    echo "Session count: $SESSION_COUNT"
    
    if [ "$SESSION_COUNT" -gt 0 ]; then
        echo "✓ Session created and retrieved successfully"
        
        # Extract session details
        USER_ID=$(echo "$VERIFY_RESP" | jq -r '.user.id')
        echo "User ID: $USER_ID"
        
        # Check Redis
        echo ""
        echo "Checking Redis for session data..."
        REDIS_SESSIONS=$(docker exec mapp_redis redis-cli KEYS "session:*")
        echo "Session keys in Redis:"
        echo "$REDIS_SESSIONS"
        
        # Check database
        echo ""
        echo "Checking PostgreSQL..."
        docker exec mapp_postgres psql -U postgres -d mapp_db -c \
            "SELECT id, user_id, device_info, is_active FROM user_sessions WHERE user_id = $USER_ID;" 2>/dev/null
        
    else
        echo "⚠️  No sessions returned from API"
    fi
else
    echo ""
    echo "❌ Failed to get access token"
    echo "This indicates the OTP verification is not working"
fi

echo ""
echo "=================================="
echo "Summary"
echo "=================================="
echo "1. Direct Redis: $([ ! -z \"$(docker exec mapp_redis redis-cli GET 'direct_test')\" ] && echo '✓ Working' || echo '❌ Failed')"
echo "2. Python Redis: $([ ! -z \"$PYTHON_TEST\" ] && echo '✓ Working' || echo '❌ Failed')"  
echo "3. OTP Storage: $([ ! -z \"$(docker exec mapp_redis redis-cli KEYS 'otp:*')\" ] && echo '✓ Working' || echo '❌ Not working')"
echo "4. Auth Flow: $([ ! -z \"$TOKEN\" ] && [ \"$TOKEN\" != \"null\" ] && echo '✓ Working' || echo '❌ Not working')"
