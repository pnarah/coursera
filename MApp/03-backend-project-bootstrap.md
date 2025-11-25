# 03 Backend Project Bootstrap

## Objective
Initialize NestJS (or Express) backend with modular architecture foundation.

## Prerequisites
- Node.js environment
- Repo structure ready

## Deliverables
- Backend project scaffold in `backend/`
- Prettier + ESLint setup
- Environment configuration loader
- Basic health check endpoint

## Suggested Steps
1. Run `npx @nestjs/cli new backend`.
2. Configure ESLint & Prettier.
3. Add `.env.example` with PORT and DATABASE_URL.
4. Implement `/health` endpoint.

## Prompts You Can Use
- "Initialize NestJS project with health check controller."
- "Add dotenv config and environment validation."
- "Set up Prettier and ESLint rules."

## Acceptance Criteria
- Server starts with `npm run start:dev`.
- `/health` returns status JSON.

## Next Task
Proceed to 04 Authentication OTP Flow.