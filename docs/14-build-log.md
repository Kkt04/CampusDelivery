# 14. Build log (phase by phase)

What was built, which commands verified it, and what remained, in the order of the M1 priorities.

## Phase 1: Foundation

**Created.** Requirements and scope (`docs/01`), architecture (`docs/02`); backend skeleton
(`app/core/*`: settings from environment, bcrypt + JWT + pickup-code hashing, exception hierarchy, rate
limiter, UTC time); MongoDB connection and index initialization in `app/infrastructure/database.py`; Document
models in `app/infrastructure/models.py`; authentication (`POST /auth/login`, `GET /auth/me`)
and RBAC (`domain/permissions.py`, `api/dependencies.require`).

**Verified.** `init_db()` index creation on MongoDB; app import; login and auth tests.

**Decisions.** Single `User` + role instead of subclasses; enums stored as readable strings; MongoDB as the primary document store with in-memory mongomock fallback for standalone testing.

## Phase 2: Core functionality

**Created.** State machine (`domain/state_machine.py`); `PackageTransitioner`; intake with duplicate
detection, unidentified and damaged workflows, automatic incidents; recipient identification; storage
allocation with two strategies; pickup request/verify/complete; learner, security and admin routes.

**Verified.** Seed script drives the full lifecycle through the real services (17 packages, history,
audit, 80 notifications); occupancy matched stored packages exactly; live API smoke test against MongoDB
(dashboard, overdue filter, 404 error shape, OpenAPI).

## Phase 3: Engineering quality

**Created.** Unit of Work with post-commit events; observer-based notification dispatcher with PENDING →
SENT/FAILED and admin retry; idempotency keys; atomic conditional updates (`find_one_and_update`) and CAS concurrency guards; audit logging; safe
error handler with request IDs; 91 tests (unit, API, concurrency, failure injection).

**Verified.** 91/91 passing on MongoDB; concurrency tests repeated 10 times without failure.

**Fixed during this phase.** Multi-word search fixed using `$and` of `$or` per term in `MongoUserRepository`;
demo emails moved to `example.edu`; capacity test verified with atomic CAS increments.

## Phase 4: M1 polish

**Created.** React frontend: login, unauthorised and not-found pages; learner overview, packages, package
details, claim-ticket pickup code with countdown, history, notifications; security dashboard, registration with
learner search, incoming list, detail with storage/identify/status panels, two-step handover, incidents;
operations overview with live counts, status bar, storage use and 14-day chart, package search, needs-attention
tabs, storage, incidents, users, audit log. Docker Compose, nginx config, documentation set.

**Verified.** Strict TypeScript build; Vite dev proxy serving real API data (login, learner package list);
clean-setup run: new virtualenv, `npm ci`, index creation + seed on MongoDB, full test suite (91 tests passed), production build.

**Not verified.** Visual rendering in a browser without headless browser tooling.

## Commands used for the final verification

```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m app.seed
pytest -v
pytest -k concurrent -v
cd ../frontend && npm ci && npm run build
```
