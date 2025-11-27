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
1. Set up pytest with pytest-asyncio for async testing
2. Write unit tests for pricing service using pytest fixtures
3. Create integration test fixtures (test database, async client)
4. Integration test: booking end-to-end scenario with TestClient
5. k6 script simulating parallel lock requests

## Example Test Setup

### tests/conftest.py
```python
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

## Prompts You Can Use
- "Add Jest unit tests for dynamic pricing scenarios." 
- "Write integration test covering booking creation with services." 
- "Produce k6 script for simulating 50 concurrent booking attempts." 

## Acceptance Criteria
- Tests pass in CI pipeline.
- Load test produces metrics for lock contention.

## Next Task
Proceed to 21 Monitoring & Observability Setup.