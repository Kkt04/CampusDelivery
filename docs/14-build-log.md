# 14. Build log (phase by phase)

What was built, which commands verified it, and what remained, in the order of the M1 priorities.

## Phase 1: Foundation

**Created.** Requirements and scope (`docs/01`), architecture (`docs/02`); backend skeleton
(`app/core/*`: settings from environment, bcrypt + JWT + pickup-code hashing, exception hierarchy, rate
limiter, UTC time); database engine with `UTCDateTime` and SQLite `BEGIN IMMEDIATE`; ORM models for all
10 tables; Alembic environment and migration `0001`; authentication (`POST /auth/login`, `GET /auth/me`)
and RBAC (`domain/permissions.py`, `api/dependencies.require`).

**Verified.** `alembic upgrade head` on SQLite and PostgreSQL 16; app import; login tests.

**Decisions.** Single `User` + role instead of subclasses; enums as VARCHAR for portability; PostgreSQL primary, SQLite for development.

## Phase 2: Core functionality

**Created.** State machine (`domain/state_machine.py`); `PackageTransitioner`; intake with duplicate
detection, unidentified and damaged workflows, automatic incidents; recipient identification; storage
allocation with two strategies; pickup request/verify/complete; learner, security and admin routes.

**Verified.** Seed script drives the full lifecycle through the real services (17 packages, history,
audit, 80 notifications); occupancy matched stored packages exactly; live API smoke test against PostgreSQL
(dashboard, overdue filter, 404 error shape, OpenAPI).

## Phase 3: Engineering quality

**Created.** Unit of Work with post-commit events; observer-based notification dispatcher with PENDING →
SENT/FAILED and admin retry; idempotency keys; conditional updates and row locks; audit logging; safe
error handler with request IDs; 74 tests (unit, API, concurrency, failure injection, migration).

**Verified.** 74/74 on SQLite and 74/74 on PostgreSQL; concurrency tests repeated 13 times without failure.

**Fixed during this phase.** Methods named `list` shadowed the built-in inside class bodies (renamed);
demo emails used the reserved `.test` domain which `email-validator` correctly rejects (moved to `example.edu`);
a capacity test that did not actually exercise its rule was rewritten.

## Phase 4: M1 polish

**Created.** React frontend: login, unauthorised and not-found pages; learner overview, packages, package
details, claim-ticket pickup code with countdown, history, notifications; security dashboard, registration with
learner search, incoming list, detail with storage/identify/status panels, two-step handover, incidents;
operations overview with live counts, status bar, storage use and 14-day chart, package search, needs-attention
tabs, storage, incidents, users, audit log. Docker Compose, nginx config, documentation set.

**Verified.** Strict TypeScript build; Vite dev proxy serving real API data (login, learner package list);
clean-setup run in a fresh folder: new virtualenv, `npm ci`, migrate + seed on both databases, full test suite on both, production build.

**Not verified.** Docker Compose start-up and visual rendering in a browser (neither was available in the build environment).

## Commands used for the final verification

```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
DATABASE_URL=postgresql+psycopg://campus:campus@localhost:5432/clean_dev alembic upgrade head
DATABASE_URL=postgresql+psycopg://campus:campus@localhost:5432/clean_dev python -m app.seed
pytest -v
TEST_DATABASE_URL=postgresql+psycopg://campus:campus@localhost:5432/clean_test pytest
cd ../frontend && npm ci && npm run build
```
