# 03 Backend Project Bootstrap

## Objective
Initialize FastAPI backend with clean architecture foundation and async database setup.

## Prerequisites
- Python 3.11+ installed
- Repo structure ready
- Docker running (PostgreSQL and Redis containers)

## Deliverables
- Backend project scaffold in `backend/`
- requirements.txt with FastAPI dependencies
- Pydantic Settings for configuration
- Basic health check endpoint
- Database connection setup (async SQLAlchemy)
- Redis connection pool

## Suggested Steps
1. Create backend folder structure (see DESIGN.md section 3.2)
2. Create requirements.txt with: fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, redis, pydantic[email], pydantic-settings, python-jose[cryptography]
3. Create app/core/config.py using Pydantic Settings
4. Create app/main.py with FastAPI app instance
5. Add app/db/session.py for async database sessions
6. Add app/db/redis.py for Redis connection pool
7. Implement GET /health endpoint returning {"status": "healthy"}
8. Test with: `uvicorn app.main:app --reload`

## Prompts You Can Use
- "Create FastAPI project structure following clean architecture pattern."
- "Set up async SQLAlchemy 2.0 with asyncpg for PostgreSQL connection."
- "Configure Pydantic Settings for environment variables management."
- "Create Redis async connection pool using redis-py."
- "Implement health check endpoint in FastAPI."

## Example Code Snippets

### requirements.txt
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
redis==5.0.1
pydantic[email]==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
```

### app/core/config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### app/main.py
```python
from fastapi import FastAPI

app = FastAPI(title="Hotel Booking API")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Acceptance Criteria
- Server starts with `uvicorn app.main:app --reload`
- `/health` endpoint returns JSON with 200 status
- Database connection pool created successfully
- Redis connection pool initialized
- Auto-generated docs available at `/docs`

## Next Task
Proceed to 04 Authentication OTP Flow.