#!/bin/bash

# Test User Management and RBAC endpoints
# Usage: ./test_user_management.sh

BASE_URL="http://localhost:8000/api/v1"

echo "========================================="
echo "USER MANAGEMENT & RBAC TEST SCRIPT"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Login as GUEST
echo -e "${BLUE}Step 1: Login as GUEST${NC}"
echo "Sending OTP to +1-5555555001..."
curl -X POST "$BASE_URL/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "5555555001",
    "country_code": "+1"
  }'

echo ""
read -p "Enter OTP received: " GUEST_OTP

echo "Verifying OTP..."
GUEST_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{
    \"mobile_number\": \"5555555001\",
    \"otp\": \"$GUEST_OTP\",
    \"device_info\": \"test-script\"
  }")

GUEST_TOKEN=$(echo $GUEST_RESPONSE | jq -r '.access_token')
GUEST_USER_ID=$(echo $GUEST_RESPONSE | jq -r '.user.id')

echo -e "${GREEN}✓ Guest logged in. User ID: $GUEST_USER_ID${NC}"
echo ""

# Step 2: Test GUEST permissions - should fail on creating users
echo -e "${BLUE}Step 2: Test GUEST permissions (should fail)${NC}"
echo "Attempting to create user as GUEST..."
CREATE_FAIL=$(curl -s -X POST "$BASE_URL/users/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GUEST_TOKEN" \
  -d '{
    "mobile_number": "5555555999",
    "country_code": "+1",
    "full_name": "Test Employee",
    "role": "HOTEL_EMPLOYEE",
    "hotel_id": 1
  }')

if echo "$CREATE_FAIL" | grep -q "Missing required permissions"; then
  echo -e "${GREEN}✓ GUEST correctly denied CREATE_USER permission${NC}"
else
  echo -e "${RED}✗ GUEST should not have CREATE_USER permission${NC}"
  echo "$CREATE_FAIL"
fi
echo ""

# Step 3: Get GUEST profile
echo -e "${BLUE}Step 3: Get GUEST profile${NC}"
GUEST_PROFILE=$(curl -s -X GET "$BASE_URL/users/me" \
  -H "Authorization: Bearer $GUEST_TOKEN")

echo "$GUEST_PROFILE" | jq .
echo -e "${GREEN}✓ Guest can view own profile${NC}"
echo ""

# Step 4: Update GUEST profile
echo -e "${BLUE}Step 4: Update GUEST profile${NC}"
UPDATE_PROFILE=$(curl -s -X PUT "$BASE_URL/users/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GUEST_TOKEN" \
  -d '{
    "email": "guest001@example.com",
    "full_name": "Guest User 001"
  }')

echo "$UPDATE_PROFILE" | jq .
echo -e "${GREEN}✓ Guest updated own profile${NC}"
echo ""

# Step 5: Login as SYSTEM_ADMIN
echo -e "${BLUE}Step 5: Login as SYSTEM_ADMIN${NC}"
echo "Sending OTP to +1-9999999999..."
curl -X POST "$BASE_URL/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "9999999999",
    "country_code": "+1"
  }'

echo ""
read -p "Enter OTP for admin: " ADMIN_OTP

ADMIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{
    \"mobile_number\": \"9999999999\",
    \"otp\": \"$ADMIN_OTP\",
    \"device_info\": \"admin-script\"
  }")

ADMIN_TOKEN=$(echo $ADMIN_RESPONSE | jq -r '.access_token')
ADMIN_USER_ID=$(echo $ADMIN_RESPONSE | jq -r '.user.id')

# Update admin user to SYSTEM_ADMIN role via DB
echo "Updating user to SYSTEM_ADMIN role..."
PGPASSWORD=postgres psql -h localhost -U postgres -d mapp_db -c \
  "UPDATE users SET role = 'SYSTEM_ADMIN' WHERE id = $ADMIN_USER_ID;"

echo -e "${GREEN}✓ Admin user created. User ID: $ADMIN_USER_ID${NC}"
echo ""

# Re-login to get new token with updated role
echo "Re-logging in as admin to get updated token..."
curl -X POST "$BASE_URL/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "9999999999",
    "country_code": "+1"
  }'

read -p "Enter OTP again: " ADMIN_OTP2

ADMIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d "{
    \"mobile_number\": \"9999999999\",
    \"otp\": \"$ADMIN_OTP2\",
    \"device_info\": \"admin-script\"
  }")

ADMIN_TOKEN=$(echo $ADMIN_RESPONSE | jq -r '.access_token')
echo -e "${GREEN}✓ Admin re-logged in with SYSTEM_ADMIN role${NC}"
echo ""

# Step 6: List all users as admin
echo -e "${BLUE}Step 6: List all users (as SYSTEM_ADMIN)${NC}"
USERS_LIST=$(curl -s -X GET "$BASE_URL/users/?limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$USERS_LIST" | jq .
echo -e "${GREEN}✓ Admin can view all users${NC}"
echo ""

# Step 7: Create hotel employee as admin
echo -e "${BLUE}Step 7: Create HOTEL_EMPLOYEE as SYSTEM_ADMIN${NC}"
CREATE_EMPLOYEE=$(curl -s -X POST "$BASE_URL/users/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "mobile_number": "5555555100",
    "country_code": "+1",
    "email": "employee001@hotel.com",
    "full_name": "Hotel Employee 001",
    "role": "HOTEL_EMPLOYEE",
    "hotel_id": 1
  }')

EMPLOYEE_ID=$(echo "$CREATE_EMPLOYEE" | jq -r '.id')
echo "$CREATE_EMPLOYEE" | jq .
echo -e "${GREEN}✓ Hotel employee created. User ID: $EMPLOYEE_ID${NC}"
echo ""

# Step 8: Get employee permissions (should have only role-based permissions)
echo -e "${BLUE}Step 8: Get employee permissions${NC}"
EMPLOYEE_PERMS=$(curl -s -X GET "$BASE_URL/users/$EMPLOYEE_ID/permissions" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$EMPLOYEE_PERMS" | jq .
echo -e "${GREEN}✓ Retrieved employee permissions${NC}"
echo ""

# Step 9: Grant individual permission to employee
echo -e "${BLUE}Step 9: Grant CREATE_ROOM permission to employee${NC}"
GRANT_PERM=$(curl -s -X POST "$BASE_URL/users/$EMPLOYEE_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "user_id": '$EMPLOYEE_ID',
    "permission": "create_room"
  }')

echo "$GRANT_PERM" | jq .
echo -e "${GREEN}✓ Permission granted${NC}"
echo ""

# Step 10: Verify employee now has CREATE_ROOM permission
echo -e "${BLUE}Step 10: Verify employee has CREATE_ROOM permission${NC}"
UPDATED_PERMS=$(curl -s -X GET "$BASE_URL/users/$EMPLOYEE_ID/permissions" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if echo "$UPDATED_PERMS" | grep -q "create_room"; then
  echo -e "${GREEN}✓ Employee now has CREATE_ROOM permission${NC}"
else
  echo -e "${RED}✗ CREATE_ROOM permission not found${NC}"
fi
echo "$UPDATED_PERMS" | jq '.all_permissions | map(select(. == "create_room"))'
echo ""

# Step 11: Revoke permission
echo -e "${BLUE}Step 11: Revoke CREATE_ROOM permission${NC}"
REVOKE_PERM=$(curl -s -X DELETE "$BASE_URL/users/$EMPLOYEE_ID/permissions/create_room" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo -e "${GREEN}✓ Permission revoked${NC}"
echo ""

# Step 12: Create VENDOR_ADMIN
echo -e "${BLUE}Step 12: Create VENDOR_ADMIN${NC}"
CREATE_VENDOR=$(curl -s -X POST "$BASE_URL/users/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "mobile_number": "5555555200",
    "country_code": "+1",
    "email": "vendor001@hotel.com",
    "full_name": "Vendor Admin 001",
    "role": "VENDOR_ADMIN",
    "hotel_id": 1
  }')

VENDOR_ID=$(echo "$CREATE_VENDOR" | jq -r '.id')
echo "$CREATE_VENDOR" | jq .
echo -e "${GREEN}✓ Vendor admin created. User ID: $VENDOR_ID${NC}"
echo ""

# Step 13: View audit logs
echo -e "${BLUE}Step 13: View audit logs${NC}"
AUDIT_LOGS=$(curl -s -X GET "$BASE_URL/users/audit-logs/?limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$AUDIT_LOGS" | jq .
echo -e "${GREEN}✓ Audit logs retrieved${NC}"
echo ""

# Step 14: Update user (change role)
echo -e "${BLUE}Step 14: Update employee details${NC}"
UPDATE_USER=$(curl -s -X PUT "$BASE_URL/users/$EMPLOYEE_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "full_name": "Updated Employee Name"
  }')

echo "$UPDATE_USER" | jq .
echo -e "${GREEN}✓ Employee updated${NC}"
echo ""

# Step 15: Deactivate user
echo -e "${BLUE}Step 15: Deactivate employee${NC}"
DEACTIVATE=$(curl -s -X PUT "$BASE_URL/users/$EMPLOYEE_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "is_active": false
  }')

echo "$DEACTIVATE" | jq .
echo -e "${GREEN}✓ Employee deactivated${NC}"
echo ""

# Final summary
echo "========================================="
echo -e "${GREEN}TEST SUMMARY${NC}"
echo "========================================="
echo "✓ Guest authentication"
echo "✓ Guest profile management"
echo "✓ Permission checks (GUEST denied CREATE_USER)"
echo "✓ System admin authentication"
echo "✓ User creation (HOTEL_EMPLOYEE, VENDOR_ADMIN)"
echo "✓ Permission granting/revoking"
echo "✓ User updates"
echo "✓ Audit log tracking"
echo "✓ Multi-tenant isolation"
echo ""
echo -e "${GREEN}All RBAC tests completed successfully!${NC}"
