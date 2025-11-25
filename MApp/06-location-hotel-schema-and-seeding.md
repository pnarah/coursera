# 06 Location & Hotel Schema & Seeding

## Objective
Create database tables for locations and hotels, and seed initial data.

## Prerequisites
- Database connection configured
- Migration tool chosen (e.g., Prisma, TypeORM, Flyway)

## Deliverables
- Tables: locations, hotels
- Migration scripts committed
- Seed script populating sample locations and hotels

## Suggested Steps
1. Define entities with fields (country, city, timezone, star_rating...).
2. Add migration for schema creation.
3. Create seed script with 3-5 sample hotels in different cities.
4. Endpoint: GET /api/hotels/:hotelId.

## Prompts You Can Use
- "Create TypeORM entities for locations and hotels with migrations."
- "Add seed script to insert sample locations and hotels." 
- "Implement hotel details endpoint."

## Acceptance Criteria
- Schema deployed successfully.
- Seeded data retrievable via API.

## Next Task
Proceed to 07 Room Types & Room Inventory.