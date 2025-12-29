import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/services/api_service.dart';
import 'core/services/secure_storage_service.dart';
import 'features/authentication/login_screen.dart';
import 'features/home/home_screen.dart';
import 'features/hotels/hotel_search_screen.dart';
import 'features/hotels/hotel_details_screen.dart';
import 'features/booking/room_selection_screen.dart';
import 'features/booking/guest_details_screen.dart';
import 'features/booking/booking_confirmation_screen.dart';
import 'features/services/services_list_screen.dart';
import 'features/invoice/running_bill_screen.dart';

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
  routes: [
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/home',
      builder: (context, state) => const HomeScreen(),
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
