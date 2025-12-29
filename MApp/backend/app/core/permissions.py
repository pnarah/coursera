"""
Permission system for RBAC
"""
import enum
from typing import Set


class Permission(str, enum.Enum):
    """All available permissions in the system"""
    
    # Booking Permissions
    VIEW_OWN_BOOKINGS = "view_own_bookings"
    CREATE_BOOKING = "create_booking"
    CANCEL_OWN_BOOKING = "cancel_own_booking"
    VIEW_ALL_BOOKINGS = "view_all_bookings"
    MODIFY_ANY_BOOKING = "modify_any_booking"
    CANCEL_ANY_BOOKING = "cancel_any_booking"
    
    # Room Management
    VIEW_ROOMS = "view_rooms"
    CREATE_ROOM = "create_room"
    UPDATE_ROOM = "update_room"
    DELETE_ROOM = "delete_room"
    MANAGE_INVENTORY = "manage_inventory"
    
    # Pricing Management
    VIEW_PRICING = "view_pricing"
    UPDATE_PRICING = "update_pricing"
    MANAGE_DYNAMIC_PRICING = "manage_dynamic_pricing"
    
    # Service Management
    VIEW_SERVICES = "view_services"
    ORDER_SERVICE = "order_service"
    MANAGE_SERVICES = "manage_services"
    APPROVE_SERVICE_ORDER = "approve_service_order"
    
    # Invoice & Payment
    VIEW_OWN_INVOICES = "view_own_invoices"
    VIEW_ALL_INVOICES = "view_all_invoices"
    GENERATE_INVOICE = "generate_invoice"
    PROCESS_PAYMENT = "process_payment"
    REFUND_PAYMENT = "refund_payment"
    
    # User Management
    VIEW_OWN_PROFILE = "view_own_profile"
    UPDATE_OWN_PROFILE = "update_own_profile"
    VIEW_ALL_USERS = "view_all_users"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    ASSIGN_PERMISSIONS = "assign_permissions"
    
    # Hotel Management
    VIEW_HOTEL_DETAILS = "view_hotel_details"
    UPDATE_HOTEL_DETAILS = "update_hotel_details"
    VIEW_ALL_HOTELS = "view_all_hotels"
    CREATE_HOTEL = "create_hotel"
    DELETE_HOTEL = "delete_hotel"
    
    # Analytics & Reports
    VIEW_HOTEL_ANALYTICS = "view_hotel_analytics"
    VIEW_SYSTEM_ANALYTICS = "view_system_analytics"
    EXPORT_REPORTS = "export_reports"
    
    # System Administration
    VIEW_AUDIT_LOG = "view_audit_log"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    ACCESS_ADMIN_PANEL = "access_admin_panel"


# Base permission sets
GUEST_PERMISSIONS: Set[Permission] = {
    # Booking permissions
    Permission.VIEW_OWN_BOOKINGS,
    Permission.CREATE_BOOKING,
    Permission.CANCEL_OWN_BOOKING,
    
    # Service permissions
    Permission.VIEW_SERVICES,
    Permission.ORDER_SERVICE,
    
    # Profile permissions
    Permission.VIEW_OWN_PROFILE,
    Permission.UPDATE_OWN_PROFILE,
    
    # Invoice permissions
    Permission.VIEW_OWN_INVOICES,
    
    # Room viewing
    Permission.VIEW_ROOMS,
    Permission.VIEW_HOTEL_DETAILS,
}

# Role to Permissions Mapping
ROLE_PERMISSIONS: dict[str, Set[Permission]] = {
    "GUEST": GUEST_PERMISSIONS,
    
    "HOTEL_EMPLOYEE": {
        # All guest permissions
        *GUEST_PERMISSIONS,
        
        # Booking management
        Permission.VIEW_ALL_BOOKINGS,
        Permission.MODIFY_ANY_BOOKING,
        Permission.CANCEL_ANY_BOOKING,
        
        # Room management (limited - specific permissions granted individually)
        Permission.VIEW_ROOMS,
        # Note: CREATE_ROOM, UPDATE_ROOM, DELETE_ROOM, MANAGE_INVENTORY 
        # are granted on a per-employee basis via hotel_employee_permissions table
        
        # Service management
        Permission.MANAGE_SERVICES,
        Permission.APPROVE_SERVICE_ORDER,
        
        # Invoice management
        Permission.VIEW_ALL_INVOICES,
        Permission.GENERATE_INVOICE,
        Permission.PROCESS_PAYMENT,
        
        # Pricing (view only by default)
        Permission.VIEW_PRICING,
        # Note: UPDATE_PRICING and MANAGE_DYNAMIC_PRICING granted individually
        
        # Analytics
        Permission.VIEW_HOTEL_ANALYTICS,
        Permission.EXPORT_REPORTS,
    },
    
    "VENDOR_ADMIN": {
        # Full hotel management for their hotel(s)
        Permission.VIEW_OWN_BOOKINGS,
        Permission.VIEW_ALL_BOOKINGS,
        Permission.MODIFY_ANY_BOOKING,
        Permission.CANCEL_ANY_BOOKING,
        
        # Complete room management
        Permission.VIEW_ROOMS,
        Permission.CREATE_ROOM,
        Permission.UPDATE_ROOM,
        Permission.DELETE_ROOM,
        Permission.MANAGE_INVENTORY,
        
        # Complete pricing control
        Permission.VIEW_PRICING,
        Permission.UPDATE_PRICING,
        Permission.MANAGE_DYNAMIC_PRICING,
        
        # Service management
        Permission.VIEW_SERVICES,
        Permission.ORDER_SERVICE,
        Permission.MANAGE_SERVICES,
        Permission.APPROVE_SERVICE_ORDER,
        
        # Invoice & Payment
        Permission.VIEW_OWN_INVOICES,
        Permission.VIEW_ALL_INVOICES,
        Permission.GENERATE_INVOICE,
        Permission.PROCESS_PAYMENT,
        Permission.REFUND_PAYMENT,
        
        # User management (for their hotel only)
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        Permission.VIEW_ALL_USERS,
        Permission.CREATE_USER,
        Permission.UPDATE_USER,
        Permission.DELETE_USER,
        Permission.ASSIGN_PERMISSIONS,
        
        # Hotel details
        Permission.VIEW_HOTEL_DETAILS,
        Permission.UPDATE_HOTEL_DETAILS,
        
        # Analytics
        Permission.VIEW_HOTEL_ANALYTICS,
        Permission.VIEW_SYSTEM_ANALYTICS,
        Permission.EXPORT_REPORTS,
        
        # Audit
        Permission.VIEW_AUDIT_LOG,
    },
    
    "SYSTEM_ADMIN": {
        # System admins have ALL permissions
        Permission.VIEW_OWN_BOOKINGS,
        Permission.CREATE_BOOKING,
        Permission.CANCEL_OWN_BOOKING,
        Permission.VIEW_ALL_BOOKINGS,
        Permission.MODIFY_ANY_BOOKING,
        Permission.CANCEL_ANY_BOOKING,
        
        Permission.VIEW_ROOMS,
        Permission.CREATE_ROOM,
        Permission.UPDATE_ROOM,
        Permission.DELETE_ROOM,
        Permission.MANAGE_INVENTORY,
        
        Permission.VIEW_PRICING,
        Permission.UPDATE_PRICING,
        Permission.MANAGE_DYNAMIC_PRICING,
        
        Permission.VIEW_SERVICES,
        Permission.ORDER_SERVICE,
        Permission.MANAGE_SERVICES,
        Permission.APPROVE_SERVICE_ORDER,
        
        Permission.VIEW_OWN_INVOICES,
        Permission.VIEW_ALL_INVOICES,
        Permission.GENERATE_INVOICE,
        Permission.PROCESS_PAYMENT,
        Permission.REFUND_PAYMENT,
        
        Permission.VIEW_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        Permission.VIEW_ALL_USERS,
        Permission.CREATE_USER,
        Permission.UPDATE_USER,
        Permission.DELETE_USER,
        Permission.ASSIGN_PERMISSIONS,
        
        Permission.VIEW_HOTEL_DETAILS,
        Permission.UPDATE_HOTEL_DETAILS,
        Permission.VIEW_ALL_HOTELS,
        Permission.CREATE_HOTEL,
        Permission.DELETE_HOTEL,
        
        Permission.VIEW_HOTEL_ANALYTICS,
        Permission.VIEW_SYSTEM_ANALYTICS,
        Permission.EXPORT_REPORTS,
        
        Permission.VIEW_AUDIT_LOG,
        Permission.MANAGE_SYSTEM_CONFIG,
        Permission.ACCESS_ADMIN_PANEL,
    }
}


def get_role_permissions(role: str) -> Set[Permission]:
    """Get all permissions for a given role"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: str, permission: Permission, extra_permissions: Set[Permission] = None) -> bool:
    """
    Check if a role has a specific permission.
    For HOTEL_EMPLOYEE, also checks extra_permissions (individual grants).
    """
    role_perms = get_role_permissions(role)
    
    if permission in role_perms:
        return True
    
    # Check extra permissions (for hotel employees with individual grants)
    if extra_permissions and permission in extra_permissions:
        return True
    
    return False


# Permissions that can be individually granted to hotel employees
GRANTABLE_EMPLOYEE_PERMISSIONS: Set[Permission] = {
    Permission.CREATE_ROOM,
    Permission.UPDATE_ROOM,
    Permission.DELETE_ROOM,
    Permission.MANAGE_INVENTORY,
    Permission.UPDATE_PRICING,
    Permission.MANAGE_DYNAMIC_PRICING,
}
