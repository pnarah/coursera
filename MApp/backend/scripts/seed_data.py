"""
Seed script to populate initial data for hotels, locations, rooms, and services.
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.hotel import Location, Hotel, Room, Service, RoomType, ServiceType


async def seed_locations():
    """Seed locations data."""
    locations_data = [
        {
            "country": "USA",
            "state": "New York",
            "city": "New York City",
            "postal_code": "10001",
            "timezone": "America/New_York",
            "is_active": True,
        },
        {
            "country": "USA",
            "state": "California",
            "city": "Los Angeles",
            "postal_code": "90001",
            "timezone": "America/Los_Angeles",
            "is_active": True,
        },
        {
            "country": "USA",
            "state": "California",
            "city": "San Francisco",
            "postal_code": "94102",
            "timezone": "America/Los_Angeles",
            "is_active": True,
        },
        {
            "country": "USA",
            "state": "Illinois",
            "city": "Chicago",
            "postal_code": "60601",
            "timezone": "America/Chicago",
            "is_active": True,
        },
        {
            "country": "USA",
            "state": "Florida",
            "city": "Miami",
            "postal_code": "33101",
            "timezone": "America/New_York",
            "is_active": True,
        },
        {
            "country": "USA",
            "state": "Washington",
            "city": "Seattle",
            "postal_code": "98101",
            "timezone": "America/Los_Angeles",
            "is_active": True,
        },
    ]

    async with AsyncSessionLocal() as session:
        # Check if locations already exist
        result = await session.execute(select(Location))
        existing_locations = result.scalars().all()
        
        if existing_locations:
            print(f"Locations already seeded ({len(existing_locations)} locations exist). Skipping...")
            return existing_locations

        locations = [Location(**data) for data in locations_data]
        session.add_all(locations)
        await session.commit()
        
        # Refresh to get IDs
        for location in locations:
            await session.refresh(location)
        
        print(f"✓ Seeded {len(locations)} locations")
        return locations


async def seed_hotels(locations):
    """Seed hotels data."""
    hotels_data = [
        # New York City Hotels
        {
            "name": "Grand Manhattan Hotel",
            "description": "Luxury hotel in the heart of Manhattan with stunning city views",
            "location_id": locations[0].id,
            "address": "123 5th Avenue, New York, NY 10001",
            "latitude": 40.7484,
            "longitude": -73.9857,
            "star_rating": 5,
            "contact_number": "+1-212-555-0101",
            "email": "info@grandmanhattan.com",
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "is_active": True,
        },
        {
            "name": "Times Square Inn",
            "description": "Budget-friendly hotel near Times Square",
            "location_id": locations[0].id,
            "address": "456 Broadway, New York, NY 10036",
            "latitude": 40.7580,
            "longitude": -73.9855,
            "star_rating": 3,
            "contact_number": "+1-212-555-0102",
            "email": "reservations@timessquareinn.com",
            "check_in_time": "14:00",
            "check_out_time": "11:00",
            "is_active": True,
        },
        # Los Angeles Hotels
        {
            "name": "Hollywood Luxury Suites",
            "description": "Elegant suites near Hollywood Boulevard",
            "location_id": locations[1].id,
            "address": "789 Hollywood Blvd, Los Angeles, CA 90028",
            "latitude": 34.1016,
            "longitude": -118.3267,
            "star_rating": 5,
            "contact_number": "+1-323-555-0201",
            "email": "contact@hollywoodluxury.com",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "is_active": True,
        },
        {
            "name": "Santa Monica Beach Resort",
            "description": "Beachfront resort with ocean views",
            "location_id": locations[1].id,
            "address": "321 Ocean Ave, Santa Monica, CA 90401",
            "latitude": 34.0195,
            "longitude": -118.4912,
            "star_rating": 4,
            "contact_number": "+1-310-555-0202",
            "email": "info@smbeachresort.com",
            "check_in_time": "16:00",
            "check_out_time": "11:00",
            "is_active": True,
        },
        # San Francisco Hotels
        {
            "name": "Golden Gate Grand Hotel",
            "description": "Luxury hotel with stunning Golden Gate Bridge views",
            "location_id": locations[2].id,
            "address": "500 Post St, San Francisco, CA 94102",
            "latitude": 37.7875,
            "longitude": -122.4083,
            "star_rating": 5,
            "contact_number": "+1-415-555-0250",
            "email": "info@goldengategrand.com",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "is_active": True,
        },
        {
            "name": "Fisherman's Wharf Inn",
            "description": "Charming hotel near Fisherman's Wharf and Pier 39",
            "location_id": locations[2].id,
            "address": "2655 Hyde St, San Francisco, CA 94109",
            "latitude": 37.8080,
            "longitude": -122.4177,
            "star_rating": 4,
            "contact_number": "+1-415-555-0251",
            "email": "reservations@fishermenswharfinn.com",
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "is_active": True,
        },
        # Chicago Hotels
        {
            "name": "Magnificent Mile Hotel",
            "description": "Upscale hotel on Michigan Avenue",
            "location_id": locations[3].id,
            "address": "555 N Michigan Ave, Chicago, IL 60611",
            "latitude": 41.8919,
            "longitude": -87.6256,
            "star_rating": 4,
            "contact_number": "+1-312-555-0301",
            "email": "reservations@magmilehotel.com",
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "is_active": True,
        },
        # Miami Hotels
        {
            "name": "South Beach Paradise",
            "description": "Trendy hotel in the heart of South Beach",
            "location_id": locations[4].id,
            "address": "888 Ocean Drive, Miami Beach, FL 33139",
            "latitude": 25.7907,
            "longitude": -80.1300,
            "star_rating": 5,
            "contact_number": "+1-305-555-0401",
            "email": "info@southbeachparadise.com",
            "check_in_time": "15:00",
            "check_out_time": "12:00",
            "is_active": True,
        },
        # Seattle Hotels
        {
            "name": "Pike Place Boutique Hotel",
            "description": "Boutique hotel near Pike Place Market",
            "location_id": locations[5].id,
            "address": "999 Pike St, Seattle, WA 98101",
            "latitude": 47.6097,
            "longitude": -122.3421,
            "star_rating": 4,
            "contact_number": "+1-206-555-0501",
            "email": "contact@pikeplacehotel.com",
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "is_active": True,
        },
    ]

    async with AsyncSessionLocal() as session:
        # Check if hotels already exist
        result = await session.execute(select(Hotel))
        existing_hotels = result.scalars().all()
        
        if existing_hotels:
            print(f"Hotels already seeded ({len(existing_hotels)} hotels exist). Skipping...")
            return existing_hotels

        hotels = [Hotel(**data) for data in hotels_data]
        session.add_all(hotels)
        await session.commit()
        
        # Refresh to get IDs
        for hotel in hotels:
            await session.refresh(hotel)
        
        print(f"✓ Seeded {len(hotels)} hotels")
        return hotels


async def seed_rooms(hotels):
    """Seed rooms data for all hotels."""
    rooms_data = []
    
    # Room configurations per hotel
    room_configs = [
        # Single rooms
        {"room_type": RoomType.SINGLE, "capacity": 1, "price_multiplier": 1.0, "count": 5},
        # Double rooms
        {"room_type": RoomType.DOUBLE, "capacity": 2, "price_multiplier": 1.5, "count": 8},
        # Deluxe rooms
        {"room_type": RoomType.DELUXE, "capacity": 2, "price_multiplier": 2.0, "count": 5},
        # Suites
        {"room_type": RoomType.SUITE, "capacity": 4, "price_multiplier": 3.0, "count": 3},
        # Family rooms
        {"room_type": RoomType.FAMILY, "capacity": 5, "price_multiplier": 2.5, "count": 2},
    ]
    
    # Base prices per hotel star rating
    base_prices = {3: 100, 4: 150, 5: 250}
    
    room_number = 100
    for hotel in hotels:
        base_price = base_prices.get(hotel.star_rating, 120)
        
        for config in room_configs:
            for i in range(config["count"]):
                room_number += 1
                floor_number = (room_number // 100)
                
                amenities = []
                if config["room_type"] in [RoomType.DELUXE, RoomType.SUITE]:
                    amenities = ["King Bed", "Mini Bar", "City View", "Work Desk"]
                elif config["room_type"] == RoomType.FAMILY:
                    amenities = ["2 Queen Beds", "Kitchenette", "Living Area", "Balcony"]
                elif config["room_type"] == RoomType.DOUBLE:
                    amenities = ["Queen Bed", "Coffee Maker", "Work Desk"]
                else:
                    amenities = ["Single Bed", "Coffee Maker"]
                
                rooms_data.append({
                    "hotel_id": hotel.id,
                    "room_number": str(room_number),
                    "room_type": config["room_type"],
                    "floor_number": floor_number,
                    "capacity": config["capacity"],
                    "base_price": base_price * config["price_multiplier"],
                    "description": f"{config['room_type'].value} room with capacity for {config['capacity']} guests",
                    "amenities": ", ".join(amenities),
                    "is_available": True,
                    "is_active": True,
                })
        
        # Reset room number for next hotel
        room_number = 100

    async with AsyncSessionLocal() as session:
        # Check which hotels already have rooms
        result = await session.execute(select(Room.hotel_id).distinct())
        hotels_with_rooms = {row[0] for row in result.all()}
        
        # Filter to only add rooms for hotels that don't have them
        new_rooms_data = [r for r in rooms_data if r["hotel_id"] not in hotels_with_rooms]
        
        if not new_rooms_data:
            result = await session.execute(select(Room))
            existing_rooms = result.scalars().all()
            print(f"All hotels already have rooms ({len(existing_rooms)} rooms exist). Skipping...")
            return existing_rooms
        
        rooms = [Room(**data) for data in new_rooms_data]
        session.add_all(rooms)
        await session.commit()
        
        # Get all rooms to return
        result = await session.execute(select(Room))
        all_rooms = result.scalars().all()
        
        print(f"✓ Seeded {len(rooms)} new rooms (total: {len(all_rooms)} rooms)")
        return all_rooms


async def seed_services(hotels):
    """Seed services data for all hotels."""
    services_data = []
    
    # Service templates
    service_templates = [
        {
            "name": "Airport Pickup",
            "service_type": ServiceType.CAB_PICKUP,
            "description": "Comfortable airport transfer service",
            "price": 50.0,
        },
        {
            "name": "Breakfast Buffet",
            "service_type": ServiceType.FOOD,
            "description": "All-you-can-eat breakfast buffet",
            "price": 25.0,
        },
        {
            "name": "Lunch Service",
            "service_type": ServiceType.FOOD,
            "description": "In-room or restaurant lunch service",
            "price": 35.0,
        },
        {
            "name": "Dinner Service",
            "service_type": ServiceType.FOOD,
            "description": "Gourmet dinner options",
            "price": 50.0,
        },
        {
            "name": "Laundry Service",
            "service_type": ServiceType.LAUNDRY,
            "description": "Same-day laundry and dry cleaning",
            "price": 30.0,
        },
        {
            "name": "Spa Treatment",
            "service_type": ServiceType.LEISURE,
            "description": "Relaxing spa and massage services",
            "price": 120.0,
        },
        {
            "name": "Gym Access",
            "service_type": ServiceType.LEISURE,
            "description": "24/7 fitness center access",
            "price": 15.0,
        },
        {
            "name": "Pool Access",
            "service_type": ServiceType.LEISURE,
            "description": "Indoor/outdoor pool facilities",
            "price": 10.0,
        },
        {
            "name": "Room Service",
            "service_type": ServiceType.ROOM_SERVICE,
            "description": "24/7 in-room dining service",
            "price": 20.0,
        },
        {
            "name": "Extra Cleaning",
            "service_type": ServiceType.ROOM_SERVICE,
            "description": "Additional room cleaning service",
            "price": 25.0,
        },
    ]
    
    for hotel in hotels:
        # Adjust prices based on hotel star rating
        price_multiplier = 1.0 if hotel.star_rating <= 3 else (1.5 if hotel.star_rating == 4 else 2.0)
        
        for template in service_templates:
            # Not all hotels offer all services
            # 3-star hotels offer basic services, 4-5 star offer premium services
            if hotel.star_rating == 3 and template["service_type"] in [ServiceType.LEISURE]:
                if template["name"] in ["Spa Treatment"]:
                    continue  # Skip spa for 3-star hotels
            
            services_data.append({
                "hotel_id": hotel.id,
                "name": template["name"],
                "service_type": template["service_type"],
                "description": template["description"],
                "price": template["price"] * price_multiplier,
                "is_available": True,
                "is_active": True,
            })

    async with AsyncSessionLocal() as session:
        # Check if services already exist
        result = await session.execute(select(Service))
        existing_services = result.scalars().all()
        
        if existing_services:
            print(f"Services already seeded ({len(existing_services)} services exist). Skipping...")
            return existing_services

        services = [Service(**data) for data in services_data]
        session.add_all(services)
        await session.commit()
        
        print(f"✓ Seeded {len(services)} services")
        return services


async def main():
    """Main function to run all seed operations."""
    print("Starting database seeding...\n")
    
    try:
        # Seed in order due to foreign key dependencies
        locations = await seed_locations()
        hotels = await seed_hotels(locations)
        rooms = await seed_rooms(hotels)
        services = await seed_services(hotels)
        
        print("\n" + "="*50)
        print("Database seeding completed successfully!")
        print("="*50)
        print(f"Total locations: {len(locations)}")
        print(f"Total hotels: {len(hotels)}")
        print(f"Total rooms: {len(rooms)}")
        print(f"Total services: {len(services)}")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
