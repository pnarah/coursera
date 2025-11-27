"""
Seed room inventory for availability testing.
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://mapp_user:mapp_password@localhost:5432/mapp_hotel_booking"


async def seed_inventory():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if room_inventory exists
        result = await session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'room_inventory'
            );
        """))
        exists = result.scalar()
        
        if not exists:
            print("room_inventory table does not exist. Creating...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS room_inventory (
                    id SERIAL PRIMARY KEY,
                    hotel_id INTEGER NOT NULL,
                    room_type VARCHAR(50) NOT NULL,
                    date DATE NOT NULL,
                    total_rooms INTEGER NOT NULL DEFAULT 0,
                    available_rooms INTEGER NOT NULL DEFAULT 0,
                    locked_rooms INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(hotel_id, room_type, date)
                );
            """))
            await session.commit()
            print("room_inventory table created")
        
        # Check current count
        result = await session.execute(text("SELECT COUNT(*) FROM room_inventory"))
        count = result.scalar()
        print(f"Current inventory records: {count}")
        
        # Seed inventory for next 120 days
        start_date = date.today()
        room_types = ['SINGLE', 'DOUBLE', 'DELUXE', 'SUITE', 'FAMILY']
        hotels = [1, 2, 3, 4, 5, 6, 7]
        
        print(f"Seeding inventory from {start_date}...")
        
        for hotel_id in hotels:
            for room_type in room_types:
                # Determine room quantity based on type
                if room_type == 'SINGLE':
                    qty = 15
                elif room_type == 'DOUBLE':
                    qty = 20
                elif room_type == 'DELUXE':
                    qty = 10
                elif room_type == 'SUITE':
                    qty = 5
                else:  # FAMILY
                    qty = 8
                
                for i in range(120):
                    inv_date = start_date + timedelta(days=i)
                    await session.execute(text("""
                        INSERT INTO room_inventory 
                        (hotel_id, room_type, date, total_rooms, available_rooms, locked_rooms)
                        VALUES (:hotel_id, :room_type, :date, :total, :available, 0)
                        ON CONFLICT (hotel_id, room_type, date) 
                        DO UPDATE SET 
                            total_rooms = :total,
                            available_rooms = :available,
                            updated_at = CURRENT_TIMESTAMP
                    """), {
                        'hotel_id': hotel_id,
                        'room_type': room_type,
                        'date': inv_date,
                        'total': qty,
                        'available': qty
                    })
        
        await session.commit()
        
        # Verify
        result = await session.execute(text("SELECT COUNT(*) FROM room_inventory"))
        final_count = result.scalar()
        print(f"✓ Room inventory seeded: {final_count} records")
        print(f"  Hotels: {len(hotels)}")
        print(f"  Room types: {len(room_types)}")
        print(f"  Days: 120")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_inventory())
