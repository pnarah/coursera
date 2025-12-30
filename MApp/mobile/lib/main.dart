import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/services/api_service.dart';
import 'core/services/secure_storage_service.dart';
import 'features/authentication/login_screen.dart';
import 'features/home/home_screen.dart';
import 'features/hotels/hotel_search_screen.dart';
import 'features/hotels/hotel_details_screen.dart';
import 'features/hotels/add_hotel_screen.dart';
import 'features/booking/room_selection_screen.dart';
import 'features/booking/guest_details_screen.dart';
import 'features/booking/booking_confirmation_screen.dart';
import 'features/services/services_list_screen.dart';
import 'features/invoice/running_bill_screen.dart';
import 'features/dashboard/guest/guest_dashboard_screen.dart';
import 'features/dashboard/employee/employee_dashboard_screen.dart';
import 'features/dashboard/vendor/vendor_dashboard_screen.dart';
import 'features/dashboard/admin/admin_dashboard_screen.dart';
import 'features/users/create_vendor_screen.dart';
import 'features/users/create_employee_screen.dart';
import 'features/sessions/sessions_list_screen.dart';

void main() {
  runApp(
    const ProviderScope(
      child: MAppApplication(),
    ),
  );
}

class MAppApplication extends StatelessWidget {
  const MAppApplication({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'MApp Hotel Booking',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2196F3),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.grey[50],
        appBarTheme: AppBarTheme(
          elevation: 0,
          centerTitle: true,
          backgroundColor: Colors.white,
          foregroundColor: Colors.black87,
          titleTextStyle: const TextStyle(
            color: Colors.black87,
            fontSize: 20,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
        cardTheme: CardThemeData(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          clipBehavior: Clip.antiAlias,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            elevation: 2,
            padding: const EdgeInsets.symmetric(
              horizontal: 32,
              vertical: 16,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            textStyle: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
            ),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: Colors.grey[300]!),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(color: Colors.grey[300]!),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(
              color: Color(0xFF2196F3),
              width: 2,
            ),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 20,
            vertical: 16,
          ),
        ),
        chipTheme: ChipThemeData(
          backgroundColor: Colors.blue[50],
          labelStyle: TextStyle(
            color: Colors.blue[900],
            fontWeight: FontWeight.w600,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: 12,
            vertical: 8,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      routerConfig: _router,
    );
  }
}

final _router = GoRouter(
  initialLocation: '/login',
  redirect: (context, state) async {
    final storage = SecureStorageService();
    final isLoggedIn = await storage.isLoggedIn();
    final userRole = await storage.getUserRole();
    final currentPath = state.uri.path;

    // If not logged in and trying to access protected routes, redirect to login
    if (!isLoggedIn && currentPath != '/login') {
      return '/login';
    }

    // If logged in and on login page, redirect to dashboard
    if (isLoggedIn && currentPath == '/login') {
      return await storage.getRoleDashboardRoute();
    }

    // Route guards for dashboard routes - check role permissions
    if (currentPath.startsWith('/dashboard/')) {
      if (!isLoggedIn) return '/login';
      
      // Check role-specific access
      if (currentPath == '/dashboard/guest' && userRole != 'GUEST') {
        return await storage.getRoleDashboardRoute();
      }
      if (currentPath == '/dashboard/employee' && userRole != 'HOTEL_EMPLOYEE') {
        return await storage.getRoleDashboardRoute();
      }
      if (currentPath == '/dashboard/vendor' && userRole != 'VENDOR_ADMIN') {
        return await storage.getRoleDashboardRoute();
      }
      if (currentPath == '/dashboard/admin' && userRole != 'SYSTEM_ADMIN') {
        return await storage.getRoleDashboardRoute();
      }
    }

    // Route guards for admin-only routes
    if (currentPath.startsWith('/admin/')) {
      if (!isLoggedIn) return '/login';
      if (userRole != 'SYSTEM_ADMIN') {
        return await storage.getRoleDashboardRoute();
      }
    }

    // Route guards for vendor routes
    if (currentPath.startsWith('/vendor/')) {
      if (!isLoggedIn) return '/login';
      if (userRole != 'VENDOR_ADMIN') {
        return await storage.getRoleDashboardRoute();
      }
    }

    return null; // No redirect needed
  },
  routes: [
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/home',
      builder: (context, state) => const HomeScreen(),
    ),
    // Dashboard routes (role-based)
    GoRoute(
      path: '/dashboard',
      builder: (context, state) {
        // TODO: Determine user role from auth state and route accordingly
        // For now, returning guest dashboard as default
        return const GuestDashboardScreen();
      },
    ),
    GoRoute(
      path: '/dashboard/guest',
      builder: (context, state) => const GuestDashboardScreen(),
    ),
    GoRoute(
      path: '/dashboard/employee',
      builder: (context, state) => const EmployeeDashboardScreen(),
    ),
    GoRoute(
      path: '/dashboard/vendor',
      builder: (context, state) => const VendorDashboardScreen(),
    ),
    GoRoute(
      path: '/dashboard/admin',
      builder: (context, state) => const AdminDashboardScreen(),
    ),
    // User management routes
    GoRoute(
      path: '/admin/create-vendor',
      builder: (context, state) => const CreateVendorScreen(
        userRole: 'SYSTEM_ADMIN',
      ),
    ),
    GoRoute(
      path: '/vendor/create-vendor',
      builder: (context, state) {
        final vendorHotelId = state.uri.queryParameters['hotelId'];
        return CreateVendorScreen(
          userRole: 'VENDOR_ADMIN',
          vendorHotelId: vendorHotelId != null ? int.parse(vendorHotelId) : null,
        );
      },
    ),
    GoRoute(
      path: '/admin/create-employee',
      builder: (context, state) => const CreateEmployeeScreen(
        userRole: 'SYSTEM_ADMIN',
      ),
    ),
    GoRoute(
      path: '/vendor/create-employee',
      builder: (context, state) {
        final vendorHotelId = state.uri.queryParameters['hotelId'];
        return CreateEmployeeScreen(
          userRole: 'VENDOR_ADMIN',
          vendorHotelId: vendorHotelId != null ? int.parse(vendorHotelId) : null,
        );
      },
    ),
    GoRoute(
      path: '/vendor/add-hotel',
      builder: (context, state) => const AddHotelScreen(),
    ),
    // Session management
    GoRoute(
      path: '/sessions',
      builder: (context, state) => const SessionsListScreen(),
    ),
    GoRoute(
      path: '/hotels/search',
      builder: (context, state) => const HotelSearchScreen(),
    ),
    GoRoute(
      path: '/hotels/:id',
      builder: (context, state) {
        final hotelId = state.pathParameters['id']!;
        return HotelDetailsScreen(hotelId: hotelId);
      },
    ),
    GoRoute(
      path: '/booking/room-selection',
      builder: (context, state) => const RoomSelectionScreen(),
    ),
    GoRoute(
      path: '/booking/guest-details',
      builder: (context, state) => const GuestDetailsScreen(),
    ),
    GoRoute(
      path: '/booking/confirmation/:id',
      builder: (context, state) {
        final bookingId = state.pathParameters['id']!;
        return BookingConfirmationScreen(bookingId: bookingId);
      },
    ),
    GoRoute(
      path: '/services/:bookingId',
      builder: (context, state) {
        final bookingId = state.pathParameters['bookingId']!;
        return ServicesListScreen(bookingId: bookingId);
      },
    ),
    GoRoute(
      path: '/invoice/:bookingId',
      builder: (context, state) {
        final bookingId = state.pathParameters['bookingId']!;
        return RunningBillScreen(bookingId: bookingId);
      },
    ),
  ],
);
