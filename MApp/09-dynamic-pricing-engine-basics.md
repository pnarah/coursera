# 09 Dynamic Pricing Engine Basics

## Objective
Introduce a simple pricing engine adjusting base room price based on seasonality and occupancy.

## Prerequisites
- Room types and availability queries

## Deliverables
- Pricing service module
- Formula implementation (season_multiplier * occupancy_multiplier - discounts)
- Endpoint: GET /api/availability/quote

## Suggested Steps
1. Define pricing factors (season buckets, occupancy thresholds).
2. Implement calculation in service.
3. Integrate with availability quote endpoint.
4. Return breakdown JSON.

## Prompts You Can Use
- "Implement basic dynamic pricing service with season and occupancy multipliers." 
- "Add availability quote endpoint returning price breakdown." 
- "Write unit tests for pricing edge cases."

## Acceptance Criteria
- Quote endpoint returns final price and applied factors.
- Tests cover at least 3 occupancy scenarios.

## Next Task
Proceed to 10 Search & List Hotels API.