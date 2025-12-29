# 01 Project Setup & Repo Structure

## Objective
Establish foundational repository structure for backend and mobile apps with initial README and version control configuration.

## Prerequisites
- Git installed
- Python 3.11+ and Flutter (or React Native) environments ready
- Docker Desktop (for PostgreSQL and Redis)

## Deliverables
- Root README.md updated
- Backend folder scaffold (e.g., `backend/`)
- Mobile folder scaffold (e.g., `mobile/`)
- Base .gitignore files

## Suggested Steps
1. Create folders: backend, mobile, docs, scripts.
2. Add root README with high-level overview.
3. Add .gitignore for Python, Flutter.
4. Create backend/requirements.txt stub.
5. Document environment setup instructions (Python 3.11+, Docker).
6. Add docker-compose.yml for PostgreSQL and Redis.

## Prompts You Can Use
- "Create initial folder structure for FastAPI backend and Flutter mobile projects."
- "Generate a README summarizing hotel booking platform modules."
- "Add .gitignore files for Python (FastAPI) and Flutter."
- "Create docker-compose.yml with PostgreSQL 15 and Redis 7 services."

## Acceptance Criteria
- Repo contains logical structure enabling isolated development.
- No extraneous files; clean initial commit baseline.

## Next Task
Proceed to 02 Mobile Project Bootstrap.