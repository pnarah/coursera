import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/services/api_service.dart';
import 'hotel_search_screen.dart';

class HotelDetailsScreen extends ConsumerStatefulWidget {
  final String hotelId;

  const HotelDetailsScreen({
    super.key,
    required this.hotelId,
  });

  @override
  ConsumerState<HotelDetailsScreen> createState() => _HotelDetailsScreenState();
}

class _HotelDetailsScreenState extends ConsumerState<HotelDetailsScreen> {
  Map<String, dynamic>? _hotel;
  List<dynamic> _rooms = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadHotelDetails();
  }

  Future<void> _loadHotelDetails() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = ref.read(apiServiceProvider);
      final hotelResponse = await apiService.getHotelDetails(int.parse(widget.hotelId));
      final roomsResponse = await apiService.getHotelRooms(int.parse(widget.hotelId));

      setState(() {
        _hotel = hotelResponse;
        _rooms = roomsResponse['rooms'] ?? [];
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load hotel details: ${e.toString()}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Get extras passed from search screen
    final extras = GoRouterState.of(context).extra as Map<String, dynamic>?;
    final checkIn = extras?['checkIn'] as DateTime?;
    final checkOut = extras?['checkOut'] as DateTime?;
    final guests = extras?['guests'] as int? ?? 1;

    return Scaffold(
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 64, color: Colors.red),
                      const SizedBox(height: 16),
                      Text(
                        _errorMessage!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.red),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadHotelDetails,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : CustomScrollView(
                  slivers: [
                    // Hotel Image Header
                    SliverAppBar(
                      expandedHeight: 300,
                      pinned: true,
                      flexibleSpace: FlexibleSpaceBar(
                        title: Text(
                          _hotel?['name'] ?? 'Hotel Details',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            shadows: [
                              Shadow(
                                offset: Offset(0, 1),
                                blurRadius: 3,
                                color: Colors.black45,
                              ),
                            ],
                          ),
                        ),
                        background: Stack(
                          fit: StackFit.expand,
                          children: [
                            Container(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                  colors: [
                                    Colors.blue.shade300,
                                    Colors.purple.shade400,
                                  ],
                                ),
                              ),
                              child: const Icon(
                                Icons.hotel_rounded,
                                size: 100,
                                color: Colors.white70,
                              ),
                            ),
                            Container(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                  colors: [
                                    Colors.transparent,
                                    Colors.black.withOpacity(0.7),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    
                    // Hotel Content
                    SliverToBoxAdapter(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [

                          // Hotel Info Card
                          Container(
                            margin: const EdgeInsets.all(16),
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.08),
                                  blurRadius: 10,
                                  spreadRadius: 2,
                                ),
                              ],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Location
                                Row(
                                  children: [
                                    Icon(Icons.location_on, size: 22, color: Colors.red.shade400),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        '${_hotel?['address'] ?? ''}, ${_hotel?['city'] ?? ''}, ${_hotel?['state'] ?? ''} ${_hotel?['zipcode'] ?? ''}',
                                        style: TextStyle(
                                          fontSize: 15,
                                          color: Colors.grey.shade700,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 16),

                                // Rating
                                if (_hotel?['rating'] != null)
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: Colors.amber.shade50,
                                      borderRadius: BorderRadius.circular(24),
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        const Icon(Icons.star, size: 22, color: Colors.amber),
                                        const SizedBox(width: 6),
                                        Text(
                                          _hotel!['rating'].toString(),
                                          style: const TextStyle(
                                            fontSize: 18,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        const SizedBox(width: 4),
                                        const Text(
                                          'Rating',
                                          style: TextStyle(
                                            fontSize: 14,
                                            color: Colors.grey,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                const SizedBox(height: 16),

                                // Description
                                if (_hotel?['description'] != null) ...[
                                  const Text(
                                    'About',
                                    style: TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    _hotel!['description'],
                                    style: const TextStyle(fontSize: 14),
                                  ),
                                  const SizedBox(height: 16),
                                ],

                                // Amenities
                                if (_hotel?['amenities'] != null) ...[
                                  const Text(
                                    'Amenities',
                                    style: TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: (_hotel!['amenities'] as List)
                                        .map((amenity) => Chip(
                                              label: Text(amenity.toString()),
                                            ))
                                        .toList(),
                                  ),
                                  const SizedBox(height: 16),
                                ],

                                // Rooms Section
                                const Divider(),
                                const SizedBox(height: 16),
                                const Text(
                                  'Available Rooms',
                                  style: TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 16),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    
                    // Room Cards
                    if (_rooms.isEmpty)
                      const SliverToBoxAdapter(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Center(
                            child: Text('No rooms available'),
                          ),
                        ),
                      )
                    else
                      SliverList(
                        delegate: SliverChildBuilderDelegate(
                          (context, index) {
                            final room = _rooms[index];
                            return Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              child: _RoomCard(
                                room: room,
                                hotelId: int.parse(widget.hotelId),
                                checkIn: checkIn,
                                checkOut: checkOut,
                                guests: guests,
                              ),
                            );
                          },
                          childCount: _rooms.length,
                        ),
                      ),
                    const SliverToBoxAdapter(
                      child: SizedBox(height: 24),
                    ),
                  ],
                ),
    );
  }
}

class _RoomCard extends StatelessWidget {
  final Map<String, dynamic> room;
  final int hotelId;
  final DateTime? checkIn;
  final DateTime? checkOut;
  final int guests;

  const _RoomCard({
    required this.room,
    required this.hotelId,
    required this.checkIn,
    required this.checkOut,
    required this.guests,
  });

  @override
  Widget build(BuildContext context) {
    final roomType = room['room_type'] ?? 'Unknown';
    final pricePerNight = room['price_per_night'] ?? 0;
    final maxOccupancy = room['max_occupancy'] ?? 0;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  roomType,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '\$$pricePerNight/night',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Room Details
            Row(
              children: [
                const Icon(Icons.people, size: 16, color: Colors.grey),
                const SizedBox(width: 4),
                Text('Max $maxOccupancy guests'),
              ],
            ),
            const SizedBox(height: 16),

            // Select Room Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: checkIn == null || checkOut == null
                    ? null
                    : () {
                        context.push(
                          '/booking/room-selection',
                          extra: {
                            'hotelId': hotelId,
                            'roomType': roomType,
                            'checkIn': checkIn,
                            'checkOut': checkOut,
                            'guests': guests,
                            'pricePerNight': pricePerNight,
                          },
                        );
                      },
                child: const Text('Select Room'),
              ),
            ),
            if (checkIn == null || checkOut == null)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Please select dates from search',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.red,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
