# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kuberise Capital is an algorithmic trading platform: a Next.js 15 (App Router) frontend backed by a Python FastAPI API. Users register, get admin-approved, and subscribe to trading plans; admins manage users, subscriptions, strategies, and announcements. There is no Docker setup — run both servers locally against PostgreSQL + Redis. Note: broker (Fyers) integration was removed — there is no broker connection system.

## Commands

```bash
# Frontend (http://localhost:3000)
npm run dev
npm run build
npm run lint

# Backend (http://localhost:8000)
cd backend
python3 -m uvicorn app.main:app --reload

# Database migrations (DATABASE_URL comes from backend/.env via alembic/env.py)
cd backend
alembic upgrade head
# or: ./run_migration.sh

# Backend tests (stdlib unittest, not pytest)
cd backend
python -m unittest discover tests
# single test:
python -m unittest tests.test_admin_auth.AdminAuthenticationTests.test_login_accepts_the_seeded_admin_and_issues_tokens
```

The backend auto-creates a super admin on startup from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars. New user registration requires an invitation code from `REGISTRATION_INVITATION_CODES`.

## Architecture

**Monorepo, two halves, no shared code:**

- `src/` — Next.js 15 App Router, React 19, TypeScript, Tailwind CSS 4, TanStack Query (`@tanstack/react-query`), Zustand, react-hook-form + zod. Organized feature-first under `src/features/` (`admin/`, `dashboard/`), with shared components in `src/components/`, lib in `src/lib/`.
- `backend/` — FastAPI + SQLAlchemy 2.0, Alembic migrations, psycopg3, Redis. Routes in `app/api/`, domain models in `app/models/domain.py`, services in `app/services/`, middleware in `app/middleware/`.

**Two separate auth portals.** Client (`/api/v1/client/auth/*`) and admin (`/api/v1/admin/auth/*`) logins are independent routers with their own frontend login pages and session storage keys. Admin endpoints are gated on `SUPER_ADMIN` role via `app/api/dependencies.py`; regular user endpoints use `CurrentUser`.

**Session model.** Short-lived JWT access tokens (15 min admin / 30 min user) carry `sub`, `role`, and `sid` (refresh-session ID). Opaque refresh tokens are stored *hashed* in the `refresh_tokens` table with token rotation and family-based reuse detection (`app/services/refresh_sessions.py`). Access tokens are validated against DB session liveness (`session_is_active`) on every protected request. `session_lifetime_for` applies role-based inactivity timeouts.

**Frontend sessions live in `sessionStorage`, not cookies** (`src/lib/session-storage.ts`). Because `sessionStorage` is tab-scoped and unreadable server-side, the old `src/middleware.ts` was deleted; route protection is client-side via the `SessionGuard` component wrapped around the dashboard and admin portal layouts. Adding a protected page means wrapping it in `SessionGuard` with the correct `kind` (`"user"` vs `"admin"`).

**Security posture.** `app/core/config.py` rejects weak/short JWT secrets and admin passwords at startup (validation is the source of many confusing boot failures — see Gotchas). Redis-based rate limiting is applied per-endpoint via the `@limiter.limit(...)` decorator (5/min on auth logins, 3/hr on registration); `app/middleware/rate_limit.py` holds the limiter singleton. `SecurityHeadersMiddleware` is mounted globally in `main.py`. Admin strategy uploads (`POST /api/v1/admin/strategies`) run AST validation and scan for dangerous patterns (`os`, `eval`, `open`, etc.).

**Client dashboard data.** `src/features/dashboard/lib/mock-data.ts` exposes `USE_MOCK_DATA = false` — real data comes from `/api/v1/client/*` endpoints. Several dashboard snapshot fields (P&L, positions, strategy status) are still `None` on the backend (`client.py` marks them TODO).

## Gotchas

- **JWT secret and admin password validation.** `get_settings()` raises at import/startup if `JWT_SECRET_KEY` is < 32 chars, in a weak-secret list, or `ADMIN_PASSWORD` is < 12 chars / weak. A backend that "won't start" with no clear route often fails here. `backend/.env` and `.env.local` should share the same `JWT_SECRET_KEY` (the frontend no longer reads it directly, but keep them in sync).
- **Rate limiting needs Redis.** Auth endpoints fail fast if Redis isn't running.
- **Session expiration on every restart is expected:** access tokens expire in minutes and refresh is required; `session_is_active` re-checks the DB.
- **Do not move tokens to cookies/localStorage** to "fix" auth — the tab-scoped `sessionStorage` design is deliberate (per-tab session death) and documented in `session-storage.ts`.
- **CSRF middleware** (`app/middleware/csrf.py`) exists but is not mounted globally in `main.py`; only the rate limiter decorators and security headers are active.
- **Broker integration removed.** All Fyers/broker code was removed (services, API routes, models, config, env credentials, frontend pages, and session-generated docs). There is no broker connection flow; don't try to revive it without a fresh Fyers developer setup.
- **`next dev` breaks under `NODE_ENV=production`.** This working environment exports `NODE_ENV=production`, which puts `next dev` in a broken hybrid state — every route 500s with `ENOENT .next/required-server-files.json` (a production-build file a dev run never generates). Start the frontend with `env -u NODE_ENV npm run dev` and wipe `.next` if it holds production-build artifacts. If a running dev server is ever broken, restart it rather than deleting `.next` underneath it.
- **Backend + Redis are not supervised.** uvicorn and redis-server are started manually and can die on their own (e.g., when the launching terminal/session closes). If `/health` stops answering, check `redis-cli ping` and restart both (`redis-server --daemonize yes`, then uvicorn from `backend/`).
