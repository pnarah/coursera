# Task 06: Vendor & Hotel Employee Management - Completion Report

## Overview
Implemented comprehensive vendor registration workflow, hotel employee management, and invitation system. This enables vendors to manage their hotels and assign employees with specific roles and permissions.

## Components Implemented

### 1. Database Schema (Migration 006_vendor_employee_mgmt)

#### Tables Created:
- **vendor_approval_requests**: Vendor registration and approval workflow
  - Fields: user_id, business_name, business_address, tax_id, contact_email, contact_phone, status, reviewed_by, reviewed_at, rejection_reason
  - Tracks vendor application process from submission to approval/rejection
  - Status tracking: PENDING, APPROVED, REJECTED

- **employee_invitations**: Employee invitation system
  - Fields: hotel_id, mobile_number, role, permissions, invited_by, token, expires_at, accepted_at
  - Generates secure tokens for employee invitations
  - 7-day expiration period for invitations
  - Unique constraint on token

- **hotel_employees**: Employee-hotel assignments
  - Fields: user_id, hotel_id, role, permissions, is_active, invited_by, invited_at, joined_at
  - Tracks employee assignments to hotels
  - Custom permissions per employee
  - Unique constraint on (user_id, hotel_id) to prevent duplicate assignments

#### Enums Created:
- **employee_role**: MANAGER, RECEPTIONIST, HOUSEKEEPING, MAINTENANCE
- **approval_status**: PENDING, APPROVED, REJECTED

#### Users Table Updates:
- Added **vendor_approved** (boolean): Tracks vendor approval status
- Added **approval_date** (timestamp): When vendor was approved
- Added **approved_by** (foreign key): Admin who approved the vendor

### 2. Models (app/models/employee.py)

#### VendorApprovalRequest
- Handles vendor registration workflow
- Links to User who submitted request
- Links to admin User who reviewed request
- Stores business information for verification

#### EmployeeInvitation
- Manages employee invitation process
- Generates unique secure tokens (32 bytes URL-safe)
- Links to Hotel and inviting User
- Expires after 7 days
- Tracks acceptance timestamp

#### HotelEmployee
- Represents employee assignment to hotel
- Stores role and custom permissions (JSONB)
- Tracks invitation history
- Supports active/inactive status
- Links employee User to Hotel

### 3. User and Hotel Model Updates

#### User Model (app/models/hotel.py)
- Added vendor approval fields
- Added relationships:
  - `vendor_requests`: All vendor approval requests by this user
  - `employee_assignments`: All hotel assignments for this employee
  - `approver`: Admin who approved this vendor

#### Hotel Model (app/models/hotel.py)
- Added relationship:
  - `employees`: All employees assigned to this hotel

### 4. Schemas (app/schemas/employee.py)

#### VendorApprovalRequestCreate
- Business name (required, max 255 chars)
- Business address (optional)
- Tax ID (optional, max 50 chars)
- Contact email (required, validated format)
- Contact phone (required, 10-15 digits)

#### VendorApprovalRequestResponse
- Complete request details
- Approval status
- Reviewer information
- Rejection reason (if rejected)

#### VendorApprovalAction
- Approval/rejection action
- Rejection reason (required when rejecting)

#### EmployeeInvitationCreate
- Hotel ID
- Mobile number (10-15 digits)
- Employee role (MANAGER, RECEPTIONIST, HOUSEKEEPING, MAINTENANCE)
- Custom permissions (optional JSONB)

#### EmployeeInvitationResponse
- Complete invitation details
- Secure token for acceptance
- Expiration and acceptance timestamps

#### EmployeeInvitationAccept
- Token for accepting invitation

#### HotelEmployeeResponse
- Complete employee assignment details
- Role and permissions
- Active status
- Invitation and join timestamps

#### HotelEmployeeUpdate
- Update role
- Update permissions
- Update active status

### 5. Service Layer (app/services/vendor_service.py)

#### Vendor Management Methods:
- **create_vendor_request()**: Create vendor approval request with validation
- **approve_vendor_request()**: Approve request and upgrade user to VENDOR_ADMIN
- **reject_vendor_request()**: Reject request with reason
- **get_pending_requests()**: List all pending vendor requests (admin)
- **get_user_requests()**: Get requests for specific user

#### Employee Management Methods:
- **invite_employee()**: Create employee invitation with secure token
- **accept_invitation()**: Accept invitation and create employee assignment
- **get_hotel_employees()**: List all employees for a hotel
- **get_employee()**: Get specific employee details
- **update_employee()**: Update employee role, permissions, or status
- **remove_employee()**: Remove employee from hotel
- **get_pending_invitations()**: List pending invitations for a hotel

#### Key Features:
- Prevents duplicate pending vendor requests
- Validates mobile numbers match on invitation acceptance
- Prevents duplicate employee assignments
- Upgrades user role from GUEST to HOTEL_EMPLOYEE on first assignment
- Auto-assigns hotel_id to user on first hotel assignment
- Generates secure URL-safe tokens for invitations
- 7-day expiration for invitations

### 6. API Endpoints (app/api/v1/endpoints/vendor.py)

#### Vendor Approval Endpoints (15 total):

**Public Endpoints:**
- **POST /api/v1/vendor/approval-request**: Create vendor request (any authenticated user)
- **GET /api/v1/vendor/approval-request/my-requests**: Get own vendor requests

**Admin Endpoints (SYSTEM_ADMIN only):**
- **GET /api/v1/vendor/approval-request/pending**: List pending vendor requests
- **POST /api/v1/vendor/approval-request/{id}/approve**: Approve vendor request
- **POST /api/v1/vendor/approval-request/{id}/reject**: Reject vendor request

**Employee Management Endpoints:**

**VENDOR_ADMIN Endpoints:**
- **POST /api/v1/vendor/employees/invite**: Invite employee to hotel
- **GET /api/v1/vendor/hotels/{hotel_id}/employees**: List hotel employees
- **GET /api/v1/vendor/hotels/{hotel_id}/invitations**: List pending invitations
- **PUT /api/v1/vendor/employees/{id}**: Update employee details
- **DELETE /api/v1/vendor/employees/{id}**: Remove employee from hotel

**Public Employee Endpoints:**
- **POST /api/v1/vendor/employees/accept-invitation**: Accept employee invitation (any authenticated user)

**VENDOR_ADMIN/SYSTEM_ADMIN Endpoints:**
- **GET /api/v1/vendor/employees/{id}**: Get employee details

## Workflows

### Vendor Approval Workflow:
1. User creates vendor approval request via POST /approval-request
2. Request enters PENDING status
3. SYSTEM_ADMIN reviews requests via GET /approval-request/pending
4. SYSTEM_ADMIN approves or rejects:
   - **Approve**: User role upgraded to VENDOR_ADMIN, vendor_approved=true
   - **Reject**: Request marked REJECTED with reason
5. User can check status via GET /approval-request/my-requests

### Employee Invitation Workflow:
1. VENDOR_ADMIN invites employee via POST /employees/invite
2. System generates secure token, expires in 7 days
3. Invitation sent to mobile number (integration pending)
4. Employee accepts via POST /employees/accept-invitation with token
5. System validates:
   - Token exists and not expired
   - Mobile number matches invitation
   - Employee not already assigned to hotel
6. Creates HotelEmployee assignment
7. Upgrades user role to HOTEL_EMPLOYEE if currently GUEST
8. Sets user's hotel_id if not already set

### Employee Management Workflow:
1. VENDOR_ADMIN can view employees via GET /hotels/{id}/employees
2. Update employee role/permissions via PUT /employees/{id}
3. Deactivate employee via PUT /employees/{id} with is_active=false
4. Remove employee via DELETE /employees/{id}

## Security & Authorization

### Role-Based Access Control:
- **Any Authenticated User**: Can create vendor requests, accept employee invitations
- **VENDOR_ADMIN**: Can manage employees for their hotels, view/update assignments
- **SYSTEM_ADMIN**: Can approve/reject vendor requests, view all employees

### Validation & Security:
- Email format validation using regex
- Phone number validation (10-15 digits)
- Duplicate request prevention
- Token-based invitation system (32-byte URL-safe tokens)
- Token expiration (7 days)
- Mobile number verification on invitation acceptance
- Duplicate employee assignment prevention

## Integration Points

### Current Integrations:
- **User Model**: Vendor approval fields and relationships
- **Hotel Model**: Employee relationship
- **Role System**: Automatic role upgrades (GUEST → HOTEL_EMPLOYEE, user → VENDOR_ADMIN)

### Pending Integrations:
- **Notification Service**: Send employee invitations via SMS/Email
- **Notification Service**: Send vendor approval/rejection notifications
- **Permission System**: Enforce custom employee permissions in endpoints

## Database Statistics

**Tables Created:** 3  
**Enums Created:** 2  
**User Fields Added:** 3  
**Hotel Fields Added:** 0  
**Relationships Added:** 4

## API Endpoints Summary

**Total Endpoints:** 12  
**Public Endpoints:** 2  
**VENDOR_ADMIN Endpoints:** 6  
**SYSTEM_ADMIN Endpoints:** 3  
**VENDOR_ADMIN/SYSTEM_ADMIN Endpoints:** 1

## Testing Recommendations

### Unit Tests:
- Vendor request creation and validation
- Vendor approval/rejection workflow
- Employee invitation generation and validation
- Invitation acceptance with mobile number matching
- Duplicate prevention logic
- Token expiration handling

### Integration Tests:
- Complete vendor approval flow
- Complete employee invitation flow
- Employee assignment and role upgrade
- Permission updates for employees
- Employee removal and cleanup

### API Tests:
- POST /approval-request with valid/invalid data
- Admin approval/rejection flow
- Employee invitation creation
- Invitation acceptance with valid/expired tokens
- Employee CRUD operations
- Authorization checks for each endpoint

## Future Enhancements

### Phase 1:
- [ ] Send employee invitations via SMS (Twilio integration)
- [ ] Send vendor approval/rejection notifications
- [ ] Email notifications for vendor status changes
- [ ] Employee invitation email alternative

### Phase 2:
- [ ] Multi-hotel vendor support (vendor managing multiple hotels)
- [ ] Employee permission enforcement in booking/room endpoints
- [ ] Employee activity tracking and audit logs
- [ ] Bulk employee invitation upload

### Phase 3:
- [ ] Employee scheduling system
- [ ] Employee performance tracking
- [ ] Advanced permission rules engine
- [ ] Employee hierarchy (manager → receptionist)

## Security Considerations

- All endpoints require authentication via JWT
- Role-based access control enforced
- Vendor approval requires SYSTEM_ADMIN role
- Employee management requires VENDOR_ADMIN role
- Invitation tokens are cryptographically secure (32 bytes)
- Tokens expire after 7 days
- Mobile number verification on invitation acceptance
- Duplicate request and assignment prevention

## Performance Considerations

- Indexed fields: user_id, hotel_id, status, token, is_active
- Unique constraints prevent duplicate data
- Lazy loading for relationships
- Pagination support for employee lists (to be added)
- Efficient token lookup with index

## Files Created/Modified

### Created:
- `/backend/alembic/versions/006_vendor_employee_mgmt.py`
- `/backend/app/models/employee.py`
- `/backend/app/services/vendor_service.py`
- `/backend/app/schemas/employee.py`
- `/backend/app/api/v1/endpoints/vendor.py`
- `/docs/user-management-tasks/TASK_06_COMPLETION.md`

### Modified:
- `/backend/app/models/__init__.py` - Exported employee models
- `/backend/app/models/hotel.py` - Added vendor/employee fields and relationships to User and Hotel
- `/backend/app/main.py` - Registered vendor router

## Completion Status

✅ **Task 06 - Vendor & Hotel Employee Management: COMPLETED**

- [x] Database schema and migration
- [x] SQLAlchemy models (VendorApprovalRequest, EmployeeInvitation, HotelEmployee)
- [x] Service layer with vendor approval and employee management
- [x] Pydantic schemas for all operations
- [x] API endpoints (12 endpoints)
- [x] Router registration
- [x] Documentation

**Migration Status:** Applied (006_vendor_employee_mgmt)  
**API Status:** Integrated and ready for testing

## Next Steps

1. Test vendor approval workflow via Swagger UI
2. Test employee invitation and acceptance flow
3. Integrate notification service for invitations
4. Proceed to next user management task

---

**Completed by:** GitHub Copilot  
**Date:** December 30, 2024  
**Migration Version:** 006_vendor_employee_mgmt
