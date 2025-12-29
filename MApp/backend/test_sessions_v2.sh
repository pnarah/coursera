#!/bin/bash

# Test max sessions enforcement for different users
echo "Testing max sessions enforcement..."
echo ""

# Create sessions for 6 different users to avoid rate limiting
for i in {1..6}; do
    MOBILE="555555${i}${i}${i}${i}"
    echo "Creating session $i with mobile: $MOBILE..."
    
    # Send OTP
    curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
        -H "Content-Type: application/json" \
        -d "{\"mobile_number\": \"$MOBILE\"}" > /dev/null
    
    sleep 0.5
    
    # Get OTP from Redis
    OTP=$(docker exec mapp_redis redis-cli GET "otp:$MOBILE" 2>/dev/null)
    
    if [ -z "$OTP" ]; then
        echo "  Failed to get OTP"
        continue
    fi
    
    # Verify OTP
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify-otp \
        -H "Content-Type: application/json" \
        -H "User-Agent: Device-$i/1.0" \
        -d "{\"mobile_number\": \"$MOBILE\", \"otp\": \"$OTP\"}")
    
    USER_ID=$(echo $RESPONSE | jq -r '.user.id')
    echo "  User ID: $USER_ID, OTP: $OTP"
done

echo ""
echo "Now testing max sessions for a single user (5555551111)..."
echo "Creating 6 sessions to test the 5-session limit..."

# First, clear rate limit
docker exec mapp_redis redis-cli DEL "rate_limit:otp:5555551111" > /dev/null 2>&1

for i in {1..6}; do
    echo ""
    echo "Attempt $i/6:"
    
    # Send OTP
    curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
        -H "Content-Type: application/json" \
        -d '{"mobile_number": "5555551111"}' > /dev/null
    
    sleep 0.5
    
    # Get OTP
    OTP=$(docker exec mapp_redis redis-cli GET "otp:5555551111" 2>/dev/null)
    
    if [ -z "$OTP" ]; then
        echo "  Failed to get OTP, waiting 10 seconds..."
        sleep 10
        docker exec mapp_redis redis-cli DEL "rate_limit:otp:5555551111" > /dev/null 2>&1
        curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
            -H "Content-Type: application/json" \
            -d '{"mobile_number": "5555551111"}' > /dev/null
        sleep 0.5
        OTP=$(docker exec mapp_redis redis-cli GET "otp:5555551111" 2>/dev/null)
    fi
    
    # Verify OTP with different device
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify-otp \
        -H "Content-Type: application/json" \
        -H "User-Agent: iPhone-$i/16.0" \
        -d "{\"mobile_number\": \"5555551111\", \"otp\": \"$OTP\"}")
    
    SESSION_ID=$(echo $RESPONSE | jq -r 'if .access_token then (.access_token | split(".")[1] | @base64d | fromjson | .session_id) else "none" end' 2>/dev/null)
    echo "  Session created: $SESSION_ID"
    
    sleep 2
done

echo ""
echo "========================================"
echo "Final Results:"
echo "========================================"
docker exec -it mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "
SELECT 
    user_id,
    COUNT(*) as total_sessions, 
    COUNT(CASE WHEN is_active THEN 1 END) as active_sessions,
    COUNT(CASE WHEN NOT is_active THEN 1 END) as invalidated_sessions
FROM user_sessions 
WHERE user_id = 6
GROUP BY user_id;"

echo ""
echo "Session details (user_id=6):"
docker exec -it mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "
SELECT 
    LEFT(id::text, 8) as session_id,
    device_info, 
    created_at, 
    is_active, 
    invalidation_reason 
FROM user_sessions 
WHERE user_id = 6 
ORDER BY created_at DESC;"
