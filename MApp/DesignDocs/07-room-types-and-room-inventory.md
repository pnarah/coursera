# 07 Room Types & Room Inventory

## Objective
Define room_types and rooms tables and basic CRUD endpoints.

## Prerequisites
- Hotels schema active

## Deliverables
- Tables: room_types, rooms
- Endpoint: GET /api/hotels/:hotelId/room-types
- Sample seed data (2-3 types per hotel, multiple rooms)

## Suggested Steps
1. Define room_types (code, base_price, capacity, amenities JSON).
2. Define rooms (room_number, status).
3. Create migrations.
4. Seed room types & rooms.
5. Implement listing endpoint with aggregation counts.

## Prompts You Can Use
- "Add room_types and rooms entities with amenities JSON column."
- "Implement endpoint to list room types with available room count." 
- "Seed room inventory for sample hotels."

## Acceptance Criteria
- Endpoint returns room types and counts.
- Data persisted and query performant.

## Next Task
Proceed to 08 Room Availability Locking.