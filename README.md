# Campus Delivery Management System

A full-stack application that digitises the lifecycle of a campus package, from arrival at
**Gate No. 2** to a verified handover to the learner it belongs to.

- **Security staff** register packages, match them to learners, assign shelves, verify pickup codes and hand packages over.
- **Learners** see only their own packages, get in-app notifications, request a one-time pickup code and view their collection history.
- **Operations admins** monitor live statistics, manage users and storage, review incidents, overdue and unidentified packages, and read the audit log.

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, PyMongo (MongoDB), Pydantic 2, PyJWT, bcrypt |
| Database | MongoDB 6+ (documents, indexes and conditional updates replace migrations) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router |
| Testing | Pytest (unit, API, concurrency) against an isolated test database |
| Dev tooling | Swagger/OpenAPI at `/docs` |

Architecture: a **layered modular monolith** (see `docs/02-architecture.md`).

---

## 1. Repository layout

```
campus-delivery/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, error handlers, routers
│   │   ├── container.py         # composition root: wires strategies, channels, event bus
│   │   ├── seed.py              # development-only demo data
│   │   ├── core/                # config, security (hashing/JWT/codes), exceptions, rate limit, time
│   │   ├── domain/              # pure business rules: enums, state machine, permissions,
│   │   │                        #   pickup rules, overdue, allocation strategies, events, interfaces
│   │   ├── repositories/        # repository protocols, MongoDB implementations, Unit of Work
│   │   ├── services/            # use cases: intake, storage, pickup, lifecycle, incidents, ...
│   │   ├── api/                 # dependencies (auth/RBAC), presenters, routes/
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── infrastructure/      # MongoDB connection/indexes, document models, notification channels
│   ├── tests/                   # unit/, api/
│   ├── requirements.txt         # pinned versions
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/                 # client.ts (fetch wrapper), endpoints.ts, types.ts
│       ├── auth/                # AuthContext, RequireRole route guard
│       ├── components/          # Layout, StatusBadge, PackageTable, LifecycleTrack, ui.tsx, ...
│       ├── lib/                 # formatting, status metadata, useApi/useAction hooks
│       └── pages/               # learner/, security/, ops/, shared/
└── docs/                        # requirements, architecture, UML, ER, API, SOLID, viva prep, ...
```

## 2. Prerequisites

| Requirement | You need |
|---|---|
| Python | 3.11 or 3.12 |
| Node.js | 20+ and npm |
| MongoDB | A running MongoDB 6+ server (local `mongod` or MongoDB Atlas) |

## 3. Start MongoDB

Install MongoDB Community Edition and run it locally, or use MongoDB Atlas:

```bash
# macOS (Homebrew)
brew tap mongodb/brew && brew install mongodb-community
brew services start mongodb-community

# or run in the foreground
mongod --dbpath /path/to/data
```

The default connection string is `mongodb://localhost:27017`. Indexes are created
automatically on API start-up and before seeding.

## 4. Local setup (path B)

### 4.1 Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then set SECRET_KEY (command is in the file)

python -m app.seed                 # load demo data (development only)
uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs> (Swagger UI) and <http://localhost:8000/redoc>.

There are no migrations: the API creates the required MongoDB indexes at start-up
(`app.infrastructure.database.init_db`).

### 4.2 Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to `http://localhost:8000`, so no CORS setup is needed.

## 5. Data model and concurrency

Each former table is now a MongoDB collection: `users`, `storage_locations`, `packages`,
`package_status_history`, `pickup_tokens`, `pickup_records`, `notifications`, `incidents`,
`audit_logs` and `idempotency_keys`. Documents keep an integer `id` (allocated from a
`counters` collection) so the API and frontend are unchanged.

Standalone MongoDB has no multi-document transactions, so the "one transaction per use case"
guarantee is provided by:

- **Conditional single-document updates** — a shelf slot is reserved with
  `find_one_and_update({occupied_count < capacity}, {$inc: {occupied_count: 1}})`, a code is
  consumed only while `used_at` is null, and a status change only matches the expected status;
- **Unique indexes** — `pickup_records.package_id`, `packages.internal_code`,
  `packages.tracking_id`, `users.institutional_id`, `users.email` and
  `idempotency_keys (user_id, scope, key)`, which make double collection and duplicate retries
  impossible.

## 6. Demo accounts (LOCAL TESTING CREDENTIALS ONLY)

These are created by `python -m app.seed` for a fictional campus. They are not real people
and must never be used outside a local machine. The seed script refuses to run when `ENVIRONMENT=production`.

| Role | Login (ID or email) | Password | Name |
|---|---|---|---|
| Operations admin | `ADM-001` | `Admin@12345` | Priya Raman |
| Security | `SEC-001` | `Security@123` | Arjun Mehta |
| Security | `SEC-002` | `Security@123` | Kavya Nair |
| Learner | `LRN-1001` | `Learner@123` | Ananya Iyer (has a package ready for pickup) |
| Learner | `LRN-1002` | `Learner@123` | Rohan Das (has an overdue package) |
| Learner | `LRN-1003` | `Learner@123` | Meera Joshi (has collection history) |
| Learner | `LRN-1004` | `Learner@123` | Vikram Singh (has a damaged package) |

### Five-minute demo script

1. Sign in as **SEC-001**. Open *Register package*, search learner "Meera", register a BlueDart parcel.
2. On the confirmation, choose *Assign storage now*, keep *Choose automatically*, tick *Mark ready*, assign.
3. Sign out, sign in as **LRN-1003**. The package is under *Ready to collect* and in *Notifications*. Tap *Get pickup code*.
4. In another browser (or private window), sign in as **SEC-002**. Open *Pickup handover*, enter the package code, `LRN-1003` and the 6-digit code, *Check code*, then *Hand over package*.
5. Try *Hand over package* again: it is rejected as already collected.
6. Sign in as **ADM-001**: see the counts change, open *Needs attention* (overdue, unidentified, damaged) and the *Audit log*.

## 7. Running the tests

```bash
cd backend
source .venv/bin/activate
pytest                     # uses an isolated test database (campus_delivery_test), dropped before every test
```

To point the suite at another MongoDB instance:

```bash
TEST_MONGO_URL=mongodb://localhost:27017 TEST_MONGO_DB=campus_delivery_test pytest
```

Tests drop every collection in the test database, so **never point the test database at data
you need.** Frontend checks: `cd frontend && npm run build`
(strict TypeScript type-check plus production build).

Latest recorded results are in `docs/09-testing.md`.

## 8. Configuration reference (`backend/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `MONGO_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `campus_delivery` | Database name |
| `SECRET_KEY` | development placeholder | Signs JWTs and keys pickup-code hashes. Must be ≥ 32 chars in production (enforced) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | Access token lifetime |
| `PICKUP_CODE_TTL_MINUTES` | 30 | How long a pickup code is valid |
| `PICKUP_CODE_MAX_ATTEMPTS` | 5 | Wrong attempts before a code locks |
| `COLLECTION_DEADLINE_DAYS` | 5 | After this, an uncollected package is *overdue* |
| `STORAGE_ALLOCATION_STRATEGY` | `suitable_size` | `suitable_size` or `first_available` |
| `NOTIFICATION_CHANNELS` | `in_app,console_email` | Channels used for each learner message |
| `LOGIN_RATE_LIMIT_ATTEMPTS` / `_WINDOW_SECONDS` | 5 / 300 | Failed logins allowed per ID+IP per window |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `BCRYPT_ROUNDS` | 12 | Password hashing cost (tests use 4 for speed) |

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `ServerSelectionTimeoutError` / `connection refused` on port 27017 | MongoDB is not running, or `MONGO_URL` host/port is wrong. Start `mongod` or fix the connection string. |
| `ModuleNotFoundError: No module named 'app'` | Run commands from the `backend/` folder with the virtual environment active. |
| Seed prints "Users already exist; skipping seed." | Expected on a second run. For a fresh start, drop the `campus_delivery` database (e.g. `mongosh` → `db.dropDatabase()`) and re-run the seed. |
| Login returns 429 | Five failed attempts in five minutes. Wait, or restart the API (the limiter is in memory). |
| Frontend shows "Cannot reach the server" | The API is not running on port 8000, or the Vite proxy target differs; set `VITE_PROXY_TARGET`. |
| `SECRET_KEY must be set to a strong value in production` | You set `ENVIRONMENT=production`; provide a long random `SECRET_KEY`. |
| Port 5173/8000/8080 already in use | Stop the other process or change the port (`npm run dev -- --port 5174`, `uvicorn … --port 8001`). |

## 10. Documentation index

| # | Document |
|---|---|
| 1 | `docs/01-requirements.md`: problem statement, objectives, scope, assumptions, functional and non-functional requirements |
| 2 | `docs/02-architecture.md`: component diagram, layers, request flow and the architecture questions (monolith, PostgreSQL, double pickup, capacity, retries, notification failure, scaling) |
| 3 | `docs/03-uml.md`: use-case diagram, class diagram, pickup sequence diagram |
| 4 | `docs/04-database.md`: ER diagram, relationships, constraints, indexes, transactions |
| 5 | `docs/05-state-machine.md`: package lifecycle diagram and full transition table |
| 6 | `docs/06-api.md`: every endpoint with roles and notes |
| 7 | `docs/07-solid-and-patterns.md`: SOLID mapped to code, design patterns and trade-offs |
| 8 | `docs/08-edge-cases.md`: the 20 edge cases, how each is handled and which test proves it |
| 9 | `docs/09-testing.md`: testing strategy and recorded results |
| 10 | `docs/10-limitations.md`: limitations and future improvements |
| 11 | `docs/11-presentation-outline.md`: M1 presentation outline |
| 12 | `docs/12-viva-guide.md`: likely faculty questions with answers |
| 13 | `docs/13-live-coding-tasks.md`: five realistic live-coding tasks with guidance |
| 14 | `docs/14-build-log.md`: phase-by-phase log of what was built and verified |
# CampusDelivery
# CampusDelivery
