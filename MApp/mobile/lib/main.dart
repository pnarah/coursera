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
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
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
        return HotelDetailsScreen(hotelId: int.parse(hotelId));
      },
    ),
    GoRoute(
      path: '/booking/room-selection',
      builder: (context, state) {
        final extras = state.extra as Map<String, dynamic>;
        return RoomSelectionScreen(
          hotelId: extras['hotelId'],
          checkIn: extras['checkIn'],
          checkOut: extras['checkOut'],
        );
      },
    ),
    GoRoute(
      path: '/booking/guest-details',
      builder: (context, state) {
        final extras = state.extra as Map<String, dynamic>;
        return GuestDetailsScreen(lockId: extras['lockId']);
      },
    ),
    GoRoute(
      path: '/booking/confirmation/:id',
      builder: (context, state) {
        final bookingId = state.pathParameters['id']!;
        return BookingConfirmationScreen(bookingId: int.parse(bookingId));
      },
    ),
    GoRoute(
      path: '/services/:bookingId',
      builder: (context, state) {
        final bookingId = state.pathParameters['bookingId']!;
        return ServicesListScreen(bookingId: int.parse(bookingId));
      },
    ),
    GoRoute(
      path: '/invoice/:bookingId',
      builder: (context, state) {
        final bookingId = state.pathParameters['bookingId']!;
        return RunningBillScreen(bookingId: int.parse(bookingId));
      },
    ),
  ],
);
