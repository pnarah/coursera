# 20 Testing Strategy Implementation

## Objective
Introduce unit, integration, and load tests for critical services.

## Prerequisites
- Functional endpoints

## Deliverables
- Unit tests (pricing, availability lock, invoice calc)
- Integration tests (booking flow)
- Load test scripts (k6/JMeter) for concurrent booking attempts

## Suggested Steps
1. Set up Jest config (NestJS default).
2. Write unit tests for pricing multipliers.
3. Integration test: booking end-to-end scenario.
4. k6 script simulating parallel lock requests.

## Prompts You Can Use
- "Add Jest unit tests for dynamic pricing scenarios." 
- "Write integration test covering booking creation with services." 
- "Produce k6 script for simulating 50 concurrent booking attempts." 

## Acceptance Criteria
- Tests pass in CI pipeline.
- Load test produces metrics for lock contention.

## Next Task
Proceed to 21 Monitoring & Observability Setup.