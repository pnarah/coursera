# FastAPI Backend

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start the server:
```bash
uvicorn app.main:app --reload
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── core/
│   │   └── config.py        # Pydantic settings
│   ├── db/
│   │   ├── base.py          # SQLAlchemy base
│   │   ├── session.py       # Database session
│   │   └── redis.py         # Redis connection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── api/
│   │   └── v1/              # API endpoints
│   └── services/            # Business logic
├── tests/                   # Test files
├── requirements.txt
└── .env
```

## API Documentation

Once the server is running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## Development

Run with auto-reload:
```bash
uvicorn app.main:app --reload --port 8000
```

Run tests:
```bash
pytest tests/
```

Format code:
```bash
black app/
ruff check app/
```
