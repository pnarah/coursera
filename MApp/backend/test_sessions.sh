#!/bin/bash

# Test max sessions enforcement for GUEST role (max 5 sessions)
echo "Testing max sessions enforcement..."
echo "GUEST role allows maximum 5 sessions"
echo ""

# Create 6 sessions to test enforcement
for i in {1..6}; do
    echo "Creating session $i..."
    
    # Send OTP
    SEND_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/send-otp \
        -H "Content-Type: application/json" \
        -d "{\"mobile_number\": \"5555551111\"}")
    
    echo "OTP sent: $SEND_RESPONSE"
    
    # Get OTP from Redis
    OTP=$(docker exec mapp_redis redis-cli GET "otp:5555551111" 2>/dev/null)
    echo "OTP retrieved: $OTP"
    
    # Verify OTP with different user agents to simulate different devices
    USER_AGENT="Device-$i/1.0"
    VERIFY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify-otp \
        -H "Content-Type: application/json" \
        -H "User-Agent: $USER_AGENT" \
        -d "{\"mobile_number\": \"5555551111\", \"otp\": \"$OTP\"}")
    
    SESSION_ID=$(echo $VERIFY_RESPONSE | jq -r '.access_token' | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
    echo "Session $i created with ID: $SESSION_ID"
    echo "---"
    sleep 1
done

echo ""
echo "Checking total sessions in database..."
docker exec -it mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "SELECT COUNT(*) as total_sessions, COUNT(CASE WHEN is_active THEN 1 END) as active_sessions FROM user_sessions WHERE user_id = 6;"

echo ""
echo "Listing all sessions:"
docker exec -it mapp_postgres psql -U mapp_user -d mapp_hotel_booking -c "SELECT id, device_info, created_at, is_active, invalidation_reason FROM user_sessions WHERE user_id = 6 ORDER BY created_at;"
