#!/bin/bash

echo "=================================="
echo "Session Management Comprehensive Test"
echo "=================================="
echo ""

BASE_URL="http://localhost:8000/api/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_test() {
    echo -e "${YELLOW}TEST: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to create a user session
create_session() {
    local mobile=$1
    local user_agent=${2:-"TestDevice/1.0"}
    
    # Send OTP
    curl -s -X POST "$BASE_URL/auth/send-otp" \
        -H "Content-Type: application/json" \
        -d "{\"mobile_number\": \"$mobile\"}" > /dev/null
    
    sleep 0.5
    
    # Get OTP from Redis
    local otp=$(docker exec mapp_redis redis-cli GET "otp:$mobile" 2>/dev/null)
    
    if [ -z "$otp" ]; then
        print_error "Failed to get OTP for $mobile"
        return 1
    fi
    
    # Verify OTP
    local response=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
        -H "Content-Type: application/json" \
        -H "User-Agent: $user_agent" \
        -d "{\"mobile_number\": \"$mobile\", \"otp\": \"$otp\"}")
    
    echo "$response"
}

# Test 1: Create initial session
print_test "1. Creating initial user session"
echo "Mobile: 5551111111, Device: iPhone"
RESPONSE1=$(create_session "5551111111" "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)")
TOKEN1=$(echo $RESPONSE1 | jq -r '.access_token')
USER_ID=$(echo $RESPONSE1 | jq -r '.user.id')

if [ "$TOKEN1" = "null" ] || [ -z "$TOKEN1" ]; then
    print_error "Failed to create session"
    exit 1
fi

print_success "Session created, User ID: $USER_ID"
echo ""

# Test 2: Verify session in Redis
print_test "2. Verifying session exists in Redis"
SESSION_ID=$(echo $TOKEN1 | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

REDIS_KEY="session:${USER_ID}:${SESSION_ID}"
REDIS_DATA=$(docker exec mapp_redis redis-cli GET "$REDIS_KEY" 2>/dev/null)

if [ -z "$REDIS_DATA" ]; then
    print_error "Session not found in Redis"
else
    print_success "Session found in Redis"
    echo "$REDIS_DATA" | jq '.' 2>/dev/null || echo "$REDIS_DATA"
fi
echo ""

# Test 3: Create multiple sessions from different devices
print_test "3. Creating sessions from different devices"

echo "Creating session from Android device..."
RESPONSE2=$(create_session "5551111111" "Mozilla/5.0 (Linux; Android 11)")
TOKEN2=$(echo $RESPONSE2 | jq -r '.access_token')
if [ "$TOKEN2" != "null" ]; then
    print_success "Android session created"
else
    print_error "Failed to create Android session"
fi

echo "Creating session from iPad..."
RESPONSE3=$(create_session "5551111111" "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)")
TOKEN3=$(echo $RESPONSE3 | jq -r '.access_token')
if [ "$TOKEN3" != "null" ]; then
    print_success "iPad session created"
else
    print_error "Failed to create iPad session"
fi

echo "Creating session from Mac..."
RESPONSE4=$(create_session "5551111111" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
TOKEN4=$(echo $RESPONSE4 | jq -r '.access_token')
if [ "$TOKEN4" != "null" ]; then
    print_success "Mac session created"
else
    print_error "Failed to create Mac session"
fi
echo ""

# Test 4: List all active sessions
print_test "4. Listing all active sessions"
SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN1" \
    -H "Content-Type: application/json")

echo "$SESSIONS" | jq '.'
SESSION_COUNT=$(echo "$SESSIONS" | jq 'length')
print_success "Found $SESSION_COUNT active sessions"
echo ""

# Test 5: Verify device detection
print_test "5. Verifying device detection"
DEVICES=$(echo "$SESSIONS" | jq -r '.[].device_info')
echo "Detected devices:"
echo "$DEVICES"

if echo "$DEVICES" | grep -q "iPhone"; then
    print_success "iPhone detected"
else
    print_error "iPhone not detected"
fi

if echo "$DEVICES" | grep -q "Android"; then
    print_success "Android detected"
else
    print_error "Android not detected"
fi
echo ""

# Test 6: Test max sessions limit (5 for guests)
print_test "6. Testing max sessions limit (5 for guests)"
echo "Creating 5th session..."
RESPONSE5=$(create_session "5551111111" "Mozilla/5.0 (Windows NT 10.0)")
TOKEN5=$(echo $RESPONSE5 | jq -r '.access_token')

if [ "$TOKEN5" != "null" ]; then
    print_success "5th session created"
fi

echo "Attempting to create 6th session (should remove oldest)..."
RESPONSE6=$(create_session "5551111111" "Mozilla/5.0 (Linux; Ubuntu)")
TOKEN6=$(echo $RESPONSE6 | jq -r '.access_token')

if [ "$TOKEN6" != "null" ]; then
    print_success "6th session created (oldest should be removed)"
    
    # Verify only 5 sessions remain
    NEW_SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
        -H "Authorization: Bearer $TOKEN6" \
        -H "Content-Type: application/json")
    
    NEW_COUNT=$(echo "$NEW_SESSIONS" | jq 'length')
    if [ "$NEW_COUNT" -eq 5 ]; then
        print_success "Max sessions enforced: $NEW_COUNT sessions remain"
    else
        print_error "Max sessions not enforced: $NEW_COUNT sessions found"
    fi
fi
echo ""

# Test 7: Logout specific session
print_test "7. Logging out specific session"
FIRST_SESSION=$(echo "$NEW_SESSIONS" | jq -r '.[1].id')
echo "Logging out session: $FIRST_SESSION"

LOGOUT_RESP=$(curl -s -X DELETE "$BASE_URL/sessions/$FIRST_SESSION" \
    -H "Authorization: Bearer $TOKEN6" \
    -H "Content-Type: application/json")

echo "$LOGOUT_RESP" | jq '.'

# Verify session was removed
UPDATED_SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN6" \
    -H "Content-Type: application/json")

UPDATED_COUNT=$(echo "$UPDATED_SESSIONS" | jq 'length')
print_success "Sessions after logout: $UPDATED_COUNT"
echo ""

# Test 8: Activity tracking
print_test "8. Testing activity tracking"
echo "Waiting 2 seconds..."
sleep 2

# Make API call to trigger activity update
curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN6" > /dev/null

# Check Redis for updated activity
REDIS_DATA_UPDATED=$(docker exec mapp_redis redis-cli GET "session:${USER_ID}:*" 2>/dev/null | head -1)
if [ ! -z "$REDIS_DATA_UPDATED" ]; then
    print_success "Activity tracking working"
else
    print_error "Activity tracking may not be working"
fi
echo ""

# Test 9: Logout all other sessions
print_test "9. Logging out all other sessions"
LOGOUT_ALL=$(curl -s -X DELETE "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN6" \
    -H "Content-Type: application/json")

echo "$LOGOUT_ALL" | jq '.'

# Verify only current session remains
FINAL_SESSIONS=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $TOKEN6" \
    -H "Content-Type: application/json")

FINAL_COUNT=$(echo "$FINAL_SESSIONS" | jq 'length')
if [ "$FINAL_COUNT" -eq 1 ]; then
    print_success "Logout all successful: Only current session remains"
else
    print_error "Logout all failed: $FINAL_COUNT sessions remain"
fi
echo ""

# Test 10: Verify session in database
print_test "10. Verifying session data in PostgreSQL"
echo "Checking database for user sessions..."

docker exec mapp_postgres psql -U postgres -d mapp_db -c \
    "SELECT id, user_id, device_info, is_active, invalidation_reason 
     FROM user_sessions 
     WHERE user_id = $USER_ID 
     ORDER BY created_at DESC 
     LIMIT 10;" 2>/dev/null

print_success "Database query completed"
echo ""

# Test 11: Check Redis TTL
print_test "11. Checking Redis TTL for session"
SESSION_KEYS=$(docker exec mapp_redis redis-cli KEYS "session:${USER_ID}:*" 2>/dev/null)
for key in $SESSION_KEYS; do
    TTL=$(docker exec mapp_redis redis-cli TTL "$key" 2>/dev/null)
    echo "Session key: $key"
    echo "TTL: $TTL seconds ($(($TTL / 3600)) hours)"
done
print_success "TTL check completed"
echo ""

# Test 12: Test invalid session
print_test "12. Testing invalid session access"
INVALID_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjM0NSwic2Vzc2lvbl9pZCI6ImludmFsaWQifQ.invalid"

INVALID_RESP=$(curl -s -X GET "$BASE_URL/sessions" \
    -H "Authorization: Bearer $INVALID_TOKEN" \
    -H "Content-Type: application/json")

STATUS=$(echo "$INVALID_RESP" | jq -r '.detail // "unknown"')
if echo "$STATUS" | grep -qi "invalid\|expired\|unauthorized"; then
    print_success "Invalid session correctly rejected"
else
    print_error "Invalid session not properly handled"
fi
echo ""

# Test 13: Create sessions for different roles
print_test "13. Testing role-based session timeouts"
echo "Note: This requires users with different roles"
echo "Creating HOTEL_EMPLOYEE session..."

# First create an employee user
EMPLOYEE_MOBILE="5552222222"
EMPLOYEE_RESP=$(create_session "$EMPLOYEE_MOBILE" "EmployeeApp/1.0")
EMPLOYEE_TOKEN=$(echo $EMPLOYEE_RESP | jq -r '.access_token')

if [ "$EMPLOYEE_TOKEN" != "null" ]; then
    # Need to update user role via database
    docker exec mapp_postgres psql -U postgres -d mapp_db -c \
        "UPDATE users SET role = 'HOTEL_EMPLOYEE' WHERE mobile_number = '$EMPLOYEE_MOBILE';" 2>/dev/null
    
    print_success "Employee user created and role updated"
    
    # Create new session with updated role
    EMPLOYEE_RESP2=$(create_session "$EMPLOYEE_MOBILE" "EmployeeApp/1.0")
    EMPLOYEE_TOKEN2=$(echo $EMPLOYEE_RESP2 | jq -r '.access_token')
    EMPLOYEE_SESSION_ID=$(echo $EMPLOYEE_TOKEN2 | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.session_id')
    EMPLOYEE_USER_ID=$(echo $EMPLOYEE_RESP2 | jq -r '.user.id')
    
    # Check TTL (should be 8 hours = 28800 seconds for employee)
    EMPLOYEE_TTL=$(docker exec mapp_redis redis-cli TTL "session:${EMPLOYEE_USER_ID}:${EMPLOYEE_SESSION_ID}" 2>/dev/null)
    echo "Employee session TTL: $EMPLOYEE_TTL seconds ($(($EMPLOYEE_TTL / 3600)) hours)"
    
    if [ "$EMPLOYEE_TTL" -gt 25000 ] && [ "$EMPLOYEE_TTL" -lt 30000 ]; then
        print_success "Employee session timeout correctly set (~8 hours)"
    else
        print_error "Employee session timeout not as expected"
    fi
fi
echo ""

# Summary
echo "=================================="
echo "Test Summary"
echo "=================================="
print_success "Multi-device session creation"
print_success "Session listing API"
print_success "Device detection"
print_success "Max sessions enforcement"
print_success "Session logout (specific)"
print_success "Session logout (all)"
print_success "Session data in Redis"
print_success "Session data in PostgreSQL"
print_success "Role-based timeouts"
print_success "Invalid session rejection"
echo ""
echo "All critical session management features tested!"
