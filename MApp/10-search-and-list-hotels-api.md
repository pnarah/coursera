# 10 Search & List Hotels API

## Objective
Implement hotel search endpoint filtering by city, dates, and returning starting prices.

## Prerequisites
- Pricing engine basics
- Hotel & room data populated

## Deliverables
- Endpoint: GET /api/hotels/search
- Query params: city, checkin, checkout, guests
- Response includes hotel summary & min price

## Suggested Steps
1. Parse query params and validate date range.
2. Fetch hotels by city.
3. For each hotel compute minimum room type price via pricing engine.
4. Return paginated results.

## Prompts You Can Use
- "Add hotels search endpoint with dynamic minimum price computation." 
- "Implement pagination for hotel search results." 
- "Optimize query for computing min price per hotel." 

## Acceptance Criteria
- Returns array of hotels with minPrice field.
- Handles empty results gracefully.

## Next Task
Proceed to 11 Booking Flow API & DB.