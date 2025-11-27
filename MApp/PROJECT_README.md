# Hotel Booking Platform (MApp)

Multi-platform hotel booking application with FastAPI backend and Flutter mobile app.

## 🏗️ Project Structure

```
MApp/
├── backend/          # FastAPI backend service
├── mobile/           # Flutter mobile application
├── docs/             # Design documents and task guides
├── scripts/          # Utility scripts
└── docker-compose.yml
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** - Backend runtime
- **Docker Desktop** - For PostgreSQL and Redis
- **Flutter SDK** - For mobile development

### Setup Development Environment

1. **Start infrastructure services:**
```bash
docker-compose up -d
```

2. **Set up backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Set up mobile:**
```bash
cd mobile
flutter pub get
```

## 📚 Documentation

- **[DESIGN.md](./DESIGN.md)** - Complete system architecture and design
- **[README.md](./README.md)** - Project navigation guide
- **[docs/](./docs/)** - Sequential task implementation guides (01-23)
- **[FASTAPI-COMPLEXITY-ANALYSIS.md](./FASTAPI-COMPLEXITY-ANALYSIS.md)** - Backend complexity assessment
- **[FASTAPI-IMPLEMENTATION-PATTERNS.md](./FASTAPI-IMPLEMENTATION-PATTERNS.md)** - Code patterns and examples

## 🎯 Core Features

### Backend (FastAPI)
- **Authentication**: OTP-based mobile authentication with JWT
- **Hotel Management**: Multi-location hotels with room inventory
- **Booking Engine**: Real-time availability with distributed locking
- **Service Ordering**: Pre-stay (cab pickup) and in-stay services (food, laundry, leisure)
- **Billing System**: Dynamic pricing with automated invoicing

### Mobile App (Flutter)
- Cross-platform (iOS & Android)
- Hotel search and filtering
- Real-time availability checking
- Booking management
- Service ordering interface
- Payment integration

## 🛠️ Technology Stack

**Backend:**
- FastAPI (async Python framework)
- PostgreSQL 15+ (relational data)
- Redis 7+ (caching, sessions, distributed locks)
- SQLAlchemy 2.0 (async ORM)
- Alembic (database migrations)

**Mobile:**
- Flutter 3.x
- Riverpod (state management)
- Dio (HTTP client)

**Infrastructure:**
- Docker & Kubernetes
- GitHub Actions (CI/CD)
- Prometheus & Grafana (monitoring)

## 📋 Implementation Tasks

Follow the sequential task guides in `docs/`:

1. ✅ Project setup and repo structure
2. Mobile project bootstrap
3. Backend project bootstrap (FastAPI)
4. Authentication OTP flow
5. Session management
6. Hotel listing APIs
7. Room availability and locking
8. Booking creation and management
9. Service ordering
10. Payment integration
... (see docs/ for complete list)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/

# Mobile tests
cd mobile
flutter test
```

## 🔧 Development Workflow

1. Start Docker services: `docker-compose up -d`
2. Run backend: `uvicorn app.main:app --reload`
3. Run mobile: `flutter run`
4. Access API docs: `http://localhost:8000/docs`

## 📊 Monitoring

- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:8000/metrics`

## 🤝 Team Structure

- 1 Backend Developer (FastAPI/Python)
- 1 Mobile Developer (Flutter)
- 1 DevOps Engineer (part-time)

## 📄 License

Proprietary - All rights reserved

## 📞 Contact

For questions or support, contact the development team.
