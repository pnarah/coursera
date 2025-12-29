"""Add San Francisco location and hotels to the database."""
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import AsyncSessionLocal
from app.models.hotel import Location, Hotel
from sqlalchemy import select


async def add_san_francisco():
    async with AsyncSessionLocal() as session:
        # Check if SF exists
        result = await session.execute(
            select(Location).where(Location.city == 'San Francisco')
        )
        sf = result.scalar_one_or_none()
        
        if sf:
            print('San Francisco already exists')
            return
        
        # Add San Francisco location
        sf = Location(
            country='USA',
            state='California',
            city='San Francisco',
            postal_code='94102',
            timezone='America/Los_Angeles',
            is_active=True
        )
        session.add(sf)
        await session.commit()
        await session.refresh(sf)
        print(f'✓ Added San Francisco location (ID: {sf.id})')
        
        # Add hotels
        hotels = [
            Hotel(
                name='Golden Gate Grand Hotel',
                description='Luxury hotel with stunning Golden Gate Bridge views',
                location_id=sf.id,
                address='500 Post St, San Francisco, CA 94102',
                latitude=37.7875,
                longitude=-122.4083,
                star_rating=5,
                contact_number='+1-415-555-0250',
                email='info@goldengategrand.com',
                check_in_time='15:00',
                check_out_time='12:00',
                is_active=True
            ),
            Hotel(
                name="Fisherman's Wharf Inn",
                description="Charming hotel near Fisherman's Wharf and Pier 39",
                location_id=sf.id,
                address='2655 Hyde St, San Francisco, CA 94109',
                latitude=37.8080,
                longitude=-122.4177,
                star_rating=4,
                contact_number='+1-415-555-0251',
                email='reservations@fishermenswharfinn.com',
                check_in_time='15:00',
                check_out_time='11:00',
                is_active=True
            )
        ]
        session.add_all(hotels)
        await session.commit()
        print(f'✓ Added {len(hotels)} San Francisco hotels')
        print('✅ San Francisco setup complete!')


if __name__ == '__main__':
    asyncio.run(add_san_francisco())
