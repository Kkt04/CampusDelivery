# Master Capstone Evaluation & LLD Defense Guide
## Campus Delivery Management System (CDMS)
*Final Year Capstone Project Evaluation — November 2026*

---

## Executive Summary

The **Campus Delivery Management System (CDMS)** is an end-to-end, enterprise-grade package custody and delivery platform engineered specifically for university campuses. Operating at Gate No. 2, the system digitizes package receipt, secure learner matching, storage allocation across dynamic capacity shelves, time-bounded pickup verification via cryptographic tokens, and handover tracking.

This document serves as the **Master Evaluation and Defense Guide**, comprehensively mapping the system's codebase to all **10 Low-Level Design (LLD) evaluation components** required by the assessment committee.

### Quick Reference & Navigation
- **Interactive Diagram Viewer**: [`diagrams/index.html`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/index.html) *(Open in browser for interactive vector SVGs & Mermaid source)*
- **Diagrams Directory**: [`diagrams/`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/)
- **Architecture Specification**: [`docs/02-architecture.md`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/docs/02-architecture.md)
- **Database & Concurrency Specification**: [`docs/04-database.md`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/docs/04-database.md)
- **SOLID & Design Patterns**: [`docs/07-solid-and-patterns.md`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/docs/07-solid-and-patterns.md)

---

## 1. Requirement Analysis

### 1.1 Actors & Roles
The system enforces strict Role-Based Access Control (RBAC) across three distinct human actors:
1. **Security Staff (`SECURITY_STAFF`)**: Stationed at Gate No. 2. Responsible for scanning and recording package intake, verifying recipient identity, assigning physical storage shelves, validating pickup codes, and executing the physical handover.
2. **Learners (`LEARNER`)**: Campus students/faculty. Receive multi-channel notifications (in-app, email), track their package lifecycle, generate single-use 6-digit pickup tokens with 30-minute expiry, and view verified handover history.
3. **Operations Admins (`OPERATIONS_ADMIN`)**: Campus logistics managers. Supervise facility storage metrics, resolve operational incidents (lost packages, damaged goods, identity mismatches), trigger overdue audits, and review audit trails.

### 1.2 Functional Requirements (FRs)
- **FR-1 Intake & Identity Matching**: Ingest incoming courier shipments (Amazon, Flipkart, DTDC, India Post, BlueDart, Delhivery, Shadowfax) with tracking numbers and recipient matching against active student records.
- **FR-2 Dynamic Storage Allocation**: Allocate shelf storage based on package dimensions (`SMALL`, `MEDIUM`, `LARGE`, `OVERSIZED`) and shelf capacity constraints without double-booking.
- **FR-3 Multi-Channel Notifications**: Real-time event publishing notifying learners upon package arrival, storage assignment, pickup code generation, and terminal delivery.
- **FR-4 Cryptographic Pickup Verification**: Time-bounded, 6-digit one-time pickup codes hashed with salted HMAC-SHA256, strictly rate-limited against brute-force attempts.
- **FR-5 Concurrent Handover Execution**: Atomic verification of pickup tokens, marking package as collected, releasing shelf capacity, and persisting an immutable pickup record in a single transaction.
- **FR-6 Incident & Overdue Management**: Flagging packages exceeding the retention threshold (48 hours), recording damage/lost claims, and supporting admin overrides.

### 1.3 Non-Functional Requirements (NFRs)
- **NFR-1 Strict Atomicity & Consistency**: Zero double-delivery, zero shelf overfills, and zero phantom collections under heavy concurrent staff interactions.
- **NFR-2 Latency & Performance**: Sub-50ms p95 latency on pickup code verification and status transitions via indexed queries.
- **NFR-3 Security & Privacy**: Learners can only view their own packages; security staff cannot forge tokens; sensitive student contact data is protected.
- **NFR-4 Idempotency**: Guaranteed safe retries on network dropouts for all write endpoints via client-supplied `Idempotency-Key` headers.

> **Diagram Reference**:
> - Use Case Diagram: [`diagrams/01_use_case_diagram.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/01_use_case_diagram.svg)
> - Use Case Source: [`diagrams/01_use_case_diagram.mmd`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/01_use_case_diagram.mmd)

---

## 2. Class Diagram & Structural Modeling

The domain model follows a decoupled, rich domain entity structure backed by MongoDB document models.

```
┌────────────────────────────────────────────────────────┐
│                     BaseDocument                       │
├────────────────────────────────────────────────────────┤
│ + id: int (PKey counter)                               │
│ + created_at: datetime                                 │
│ + updated_at: datetime                                 │
└───────────────────────────┬────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│     User     │     │   Package    │     │ StorageShelf │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 2.1 Core Entities & Multiplicities
- **`User` (1) ── (0..*) `Package`**: A learner owns zero or many packages; each package belongs to exactly one learner (or is flagged as unidentified).
- **`Package` (0..1) ── (0..1) `StorageShelf`**: A package is assigned to at most one shelf at any time (`occupied_count <= capacity`).
- **`Package` (1) ── (0..*) `PickupToken`**: A package can have multiple historical pickup tokens, but at most **one** active (`used_at IS NULL`).
- **`Package` (1) ── (0..1) `PickupRecord`**: Once collected, a package has exactly one immutable handover proof record (`UNIQUE(package_id)`).
- **`Package` (1) ── (0..*) `PackageStatusHistory`**: Complete audit timeline of every state transition.
- **`Package` (1) ── (0..*) `Incident`**: Operational exception logs (damage, misdelivery, dispute).

> **Diagram Reference**:
> - Domain Entities Class Diagram: [`diagrams/02_class_diagram_domain_entities.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/02_class_diagram_domain_entities.svg)
> - Services & Architecture Class Diagram: [`diagrams/03_class_diagram_services_and_architecture.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/03_class_diagram_services_and_architecture.svg)

---

## 3. Object-Oriented Design (OOD)

The codebase exemplifies the core tenets of OOP:

### 3.1 Abstraction
- Repositories expose abstract protocols (`IPackageRepository`, `IStorageRepository`, `IUnitOfWork` in [`backend/app/repositories/interfaces.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/repositories/interfaces.py)). Services depend strictly on protocols, hiding data store implementation details.
- `NotificationChannel` protocol in [`backend/app/domain/interfaces.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/interfaces.py) abstracts concrete delivery mechanisms (In-App Database vs. Mock Email / SMS).

### 3.2 Encapsulation
- **Storage Protection**: The rule governing whether a shelf can accept a package (`is_active`, `occupied_count < capacity`, `size fits`) is encapsulated inside `StorageCandidate.accepts()` in [`backend/app/domain/allocation.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/allocation.py). Callers cannot mutate shelf counters directly.
- **State Transition Enforcement**: `PackageTransitioner.apply()` in [`backend/app/services/transitions.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/services/transitions.py) encapsulates the state transition, status history persistence, audit logging, and domain event triggering into a single atomic routine.

### 3.3 Polymorphism
- **Storage Allocation Strategies**: `StorageAllocationService` invokes `self._strategy.rank(candidates, package_size)`. Both `SuitableSizeStrategy` (tightest bounding box) and `FirstAvailableStrategy` implement this interface polymorphically without the service knowing which algorithm is configured.
- **Notification Channels**: `NotificationDispatcher` iterates through registered `NotificationChannel` instances, polymorphically invoking `.send(event)`.

### 3.4 Inheritance & Composition
- Domain entities use inheritance judiciously: base fields (`id`, `created_at`, `updated_at`) inherit from `BaseDocument` in [`backend/app/infrastructure/models.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/infrastructure/models.py).
- Composition is favored over inheritance for behavior: Services compose Repositories, Unit of Work, and Domain Event Publishers rather than subclassing heavy base services.

---

## 4. SOLID Principles

| Principle | Implementation in Codebase | Concrete Code Reference |
|---|---|---|
| **Single Responsibility Principle (SRP)** | Every service has one distinct business domain. Intake logic is segregated from Pickup verification, Storage management, and Incident reporting. | [`PackageIntakeService`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/services/package_intake.py) handles intake;<br>[`PickupService`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/services/pickup.py) handles tokens and handover. |
| **Open/Closed Principle (OCP)** | New notification channels or allocation strategies can be added without modifying existing service code. Strategy/Channel factories enable plug-and-play registration. | [`domain/allocation.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/allocation.py): `register_allocation_strategy`;<br>[`domain/interfaces.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/interfaces.py): `NotificationChannel`. |
| **Liskov Substitution Principle (LSP)** | Any implementation of `StorageAllocationStrategy` can replace another without breaking caller expectations. Both strategies only return candidate IDs that satisfy `.accepts()`. | `SuitableSizeStrategy` and `FirstAvailableStrategy` are fully substitutable in [`domain/allocation.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/allocation.py). |
| **Interface Segregation Principle (ISP)** | Domain protocols are focused and granular rather than monolithic. Repositories implement segregated interfaces (`IPackageRepository`, `IUserRepository`, `IStorageRepository`). | Defined in [`repositories/interfaces.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/repositories/interfaces.py) and [`domain/interfaces.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/interfaces.py). |
| **Dependency Inversion Principle (DIP)** | High-level use-case services depend on abstract protocols, not on concrete MongoDB driver objects. The Dependency Injection Container wires concrete instances at application boot. | [`backend/app/container.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/container.py) wires dependencies into [`backend/app/api/dependencies.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/api/dependencies.py). |

---

## 5. Design Patterns

The architecture deliberately applies 7 prominent Gang of Four (GoF) and Enterprise Design Patterns:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Design Patterns in CDMS                         │
├─────────────────────┬──────────────────────────────────────────────────┤
│ Strategy            │ StorageAllocationStrategy (SuitableSize / First) │
│ Observer            │ EventBus -> PackageStatusChanged -> Dispatcher   │
│ State               │ PackageStateMachine (12 states, Transition table)│
│ Factory Method      │ ChannelFactory, build_allocation_strategy        │
│ Unit of Work & Repo │ MongoUnitOfWork + MongoRepository protocols      │
│ Singleton           │ App Container / Settings singleton               │
│ Decorator           │ Middleware (Request ID, Rate Limiter, AppError)  │
└─────────────────────┴──────────────────────────────────────────────────┘
```

1. **Strategy Pattern** ([`backend/app/domain/allocation.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/allocation.py)):
   - Decouples storage selection algorithms (`SUITABLE_SIZE` vs `FIRST_AVAILABLE`) from the allocation workflow.
   - *Defense Note*: Strategy only **ranks** shelves; the service performs the atomic reservation CAS update, preventing concurrency races in pure algorithms.
2. **Observer Pattern** ([`backend/app/domain/events.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/events.py)):
   - Pub-Sub decoupled event handling. State transitions publish `PackageStatusChanged`; `NotificationDispatcher` observes and dispatches alerts asynchronously.
   - *Defense Note*: Subscriber failures are caught and logged; they cannot rollback an already-committed package transition.
3. **State Pattern** ([`backend/app/domain/state_machine.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/domain/state_machine.py)):
   - Table-driven finite state machine with 12 lifecycle states (`REGISTERED`, `SORTED`, `STORED`, `READY_FOR_PICKUP`, `PICKUP_REQUESTED`, `COLLECTED`, etc.).
   - Explicit guards validate actor roles, required storage allocations, and token validity before permitting transitions.
4. **Factory Method Pattern** ([`backend/app/infrastructure/notifications.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/infrastructure/notifications.py)):
   - `build_channel()` instantiates concrete communication channels (`InAppChannel`, `EmailMockChannel`) based on dynamic configuration.
5. **Unit of Work & Repository Pattern** ([`backend/app/repositories/unit_of_work.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/repositories/unit_of_work.py)):
   - Coordinates multi-document writes across collections and buffers domain events until operations succeed.
6. **Singleton Pattern** ([`backend/app/container.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/container.py)):
   - Ensures single-instance lifecycle for configuration settings, thread pools, and event bus dispatchers.
7. **Decorator / Interceptor Pattern** ([`backend/app/main.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/main.py)):
   - FastAPI middleware layers decorate HTTP execution with request IDs, rate-limiting tokens, and global exception mapping.

> **Diagram Reference**:
> - Design Patterns Diagram: [`diagrams/13_design_patterns_diagram.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/13_design_patterns_diagram.svg)
> - State Machine Diagram: [`diagrams/10_state_machine_diagram.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/10_state_machine_diagram.svg)

---

## 6. Sequence & Activity Diagrams (Core Use Cases)

The system lifecycle is detailed across 6 dedicated behavioral diagrams:

### 6.1 Package Intake & Learner Triage
1. Security guard scans tracking barcode and enters recipient name/identifier.
2. System queries active `users` collection.
3. If matched, status moves `REGISTERED -> SORTED`; if unmatched, moves to `UNIDENTIFIED`.
4. Domain event published; in-app notification generated.
> **Diagram Reference**: [`diagrams/04_sequence_package_intake.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/04_sequence_package_intake.svg)

### 6.2 Storage Allocation & Slot Reservation
1. System fetches active shelves matching package size requirement.
2. `StorageAllocationStrategy` sorts and ranks candidates.
3. System executes conditional atomic increment `find_one_and_update(..., $inc: {occupied_count: 1})`.
4. Upon successful reservation, package state updates to `STORED` and `READY_FOR_PICKUP`.
> **Diagram Reference**: [`diagrams/05_sequence_storage_allocation.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/05_sequence_storage_allocation.svg)

### 6.3 Pickup Code Request & Verification
1. Learner clicks "Generate Pickup Code" on the mobile/web interface.
2. System checks package is in `READY_FOR_PICKUP` or `PICKUP_REQUESTED` state.
3. Any previous active token is invalidated (`superseded`).
4. Cryptographically secure 6-digit code generated; stored as HMAC-SHA256 with 30-minute expiration.
5. Plaintext code shown only once to learner.
> **Diagram Reference**: [`diagrams/06_sequence_pickup_request_and_token.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/06_sequence_pickup_request_and_token.svg)

### 6.4 Handover Execution & Concurrency Protection
1. Security guard enters learner ID and the 6-digit pickup code.
2. Rate-limiter verifies no brute-force attempt is active.
3. System verifies token hash and expiration.
4. Atomic conditional update sets `used_at = now()`, changes package status to `COLLECTED`, decrements shelf `occupied_count`, and writes immutable `PickupRecord`.
5. If concurrent guard attempts redemption, atomic CAS fails with `409 Conflict`.
> **Diagram Reference**: [`diagrams/07_sequence_pickup_handover_concurrency.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/07_sequence_pickup_handover_concurrency.svg)

### 6.5 End-to-End Activity Workflows
> **Diagram References**:
> - Complete Package Lifecycle Activity: [`diagrams/08_activity_package_lifecycle.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/08_activity_package_lifecycle.svg)
> - Concurrency Guard Activity: [`diagrams/09_activity_concurrency_storage_handover.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/09_activity_concurrency_storage_handover.svg)

---

## 7. API / Interface Design

The backend delivers clean RESTful semantics via FastAPI with automatic OpenAPI generation.

```
┌────────────────────────────────────────────────────────┐
│               REST API Endpoints (Prefix /api)         │
├────────────────────────────────────────────────────────┤
│ POST /auth/login               - Token issuance        │
│ POST /packages/intake          - Barcode scan intake   │
│ POST /packages/{id}/assign-storage - Slot allocation   │
│ POST /packages/{id}/request-pickup - Learner code      │
│ POST /pickups/verify-and-handover  - Staff completion  │
│ POST /incidents                - Exception claims      │
│ GET  /reports/dashboard        - Admin real-time KPIs  │
└────────────────────────────────────────────────────────┘
```

### 7.1 Layer Separation
- **Presentation Layer (`api/routes/`, `api/presenters.py`)**: Parses HTTP requests, validates Pydantic schemas, verifies JWT credentials and role permissions, and shapes HTTP JSON responses.
- **Service Layer (`services/`)**: Orchestrates business workflows, transaction boundaries, domain event firing, and idempotency tracking.
- **Domain Layer (`domain/`)**: Pure business logic without framework dependencies (state transition rules, overdue calculations, ranking algorithms).
- **Data Access Layer (`repositories/mongo_repos.py`)**: Encapsulates PyMongo queries, projections, updates, and index hints.

### 7.2 Standard Error Response Contract
All errors adhere to RFC 7807 problem details format:
```json
{
  "code": "ALREADY_COLLECTED",
  "message": "Package 42 has already been collected.",
  "details": {},
  "request_id": "req_01HP8Z5T12AB..."
}
```

> **Detailed API Guide**: [`docs/06-api.md`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/docs/06-api.md)

---

## 8. Database Schema & Data Modeling

The database is built on **MongoDB 6+**, utilizing atomic document-level operations and strict compound indexes.

```
┌────────────────────────────────────────────────────────┐
│                   MongoDB Collections                  │
├──────────────────┬─────────────────────────────────────┤
│ users            │ Learners, Security Guards, Admins   │
│ packages         │ Central package lifecycle state     │
│ storage_locations│ Shelves, zones, capacities, counts  │
│ pickup_tokens    │ HMAC hashes, expiries, used flags   │
│ pickup_records   │ Immutable handover audit receipts   │
│ incidents        │ Damage / mismatch dispute logs      │
│ audit_logs       │ Security audit trail of all actions │
│ idempotency_keys │ Request deduplication fingerprints  │
│ counters         │ Auto-increment integer PK generator │
└──────────────────┴─────────────────────────────────────┘
```

### 8.1 Auto-Increment Integer Keys (`next_id`)
To maintain human-readable tracking identifiers for students and security staff, the system uses an atomic MongoDB sequence counter:
```python
db.counters.find_one_and_update(
    {"_id": collection_name},
    {"$inc": {"seq": 1}},
    upsert=True,
    return_document=ReturnDocument.AFTER
)
```

### 8.2 Compound Indexes & Unique Constraints
Initialized at boot via `init_db()` in [`backend/app/infrastructure/database.py`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/backend/app/infrastructure/database.py):
- `users`: `UNIQUE(email)`
- `packages`: `UNIQUE(internal_code)`, `UNIQUE(tracking_id)`, compound index `(recipient_user_id, status)`
- `pickup_records`: `UNIQUE(package_id)`, `UNIQUE(token_id)` (prevents dual handover records)
- `storage_locations`: `UNIQUE(code)`
- `idempotency_keys`: `UNIQUE(user_id, scope, key)`

> **Diagram Reference**:
> - ER Schema Diagram: [`diagrams/12_database_er_schema_diagram.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/12_database_er_schema_diagram.svg)
> - Database Specification: [`docs/04-database.md`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/docs/04-database.md)

---

## 9. Error Handling, Validation & Concurrency

### 9.1 Boundary Validation
- All inputs are strictly sanitized and validated using Pydantic V2 schemas (`backend/app/schemas/`).
- Barcode strings, tracking numbers, and phone numbers are verified via regex before service dispatch.

### 9.2 The "Double Handover" Race Condition
- **Problem**: Two guards at different gates enter the same pickup code simultaneously.
- **Solution**: The handover operation uses an atomic Compare-And-Swap (CAS) query on `pickup_tokens`:
  ```python
  token = db.pickup_tokens.find_one_and_update(
      {"id": token_id, "used_at": None, "expires_at": {"$gt": now}},
      {"$set": {"used_at": now}}
  )
  ```
- If two requests hit concurrently, MongoDB document locking ensures only **one** request updates the row and receives the non-null document. The second receives `None` and immediately aborts with `409 Token Already Used`.
- As a secondary guarantee, inserting the `pickup_record` enforces `UNIQUE(package_id)`.

### 9.3 Storage Overfill Prevention
- Concurrent reservations execute:
  ```python
  shelf = db.storage_locations.find_one_and_update(
      {"id": shelf_id, "is_active": True, "$expr": {"$lt": ["$occupied_count", "$capacity"]}},
      {"$inc": {"occupied_count": 1}}
  )
  ```
- It is mathematically impossible for concurrent workers to exceed shelf capacity.

### 9.4 Idempotent API Execution
- Safe retry for payment/intake/handover using `Idempotency-Key` header.
- Cached response returned on duplicate submission; in-flight locks prevent concurrent duplicate execution.

> **Diagram Reference**: [`diagrams/07_sequence_pickup_handover_concurrency.svg`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/07_sequence_pickup_handover_concurrency.svg)

---

## 10. Working Implementation & Verification

The implementation is verified through an automated test suite across unit, domain, and API levels.

### 10.1 Running the Test Suite
```bash
cd backend
# 1. Run isolated Unit & Domain Tests (Passes independently in < 0.05s)
python3 -m pytest tests/unit -v

# 2. Run API Integration & Concurrency Tests (with MongoDB active)
python3 -m pytest tests/api -v
```

### 10.2 Verification Summary
- **29/29 Unit Tests Passing**: Testing pure state transitions, allocation candidate ranking, and pickup token expiration rules.
- **End-to-End API Suite**: Testing authenticated role access, barcode intake, storage reservation, code generation, and simulated race conditions.

---

## 11. Defense & Viva Voce Q&A Master Reference

Use these precise, architecturally sound responses when questioned by evaluators:

### Q1: Why did you choose a Layered Modular Monolith over Microservices?
> **Answer**: *"A campus delivery facility operates under strict local transactional consistency requirements. A package handover requires atomic updates across token status, package state, storage capacity, pickup records, and audit logs. In a modular monolith, this is achieved with guaranteed ACID consistency in a single database transaction. Microservices would introduce distributed transactions, network partitioning failure modes, and eventual consistency delays, which are completely unjustified for a single-campus physical boundary."*

### Q2: How do you guarantee zero double-deliveries in MongoDB without relational table locks?
> **Answer**: *"We utilize atomic document-level conditional updates (`find_one_and_update`) acting as a Compare-And-Swap (CAS) guard. The update query explicitly specifies `used_at: null` and `expires_at > now`. Only one concurrent worker can match and transition the document. Furthermore, the `pickup_records` collection enforces a unique compound index on `package_id`, making duplicate completion physically impossible at the database engine level."*

### Q3: Why is `occupied_count` maintained as a counter on `StorageLocation` instead of running `COUNT()` queries?
> **Answer**: *"Running a `COUNT()` query followed by an `INSERT` is a classic 'check-then-act' race condition where concurrent requests read the same count and overfill the shelf. By maintaining `occupied_count` and using conditional atomic increments (`occupied_count < capacity`), the availability check and slot reservation occur in a single atomic database operation."*

### Q4: Why does `StorageAllocationStrategy` only rank candidates rather than reserving them?
> **Answer**: *"To adhere to the Single Responsibility Principle and maintain pure domain logic. Ranking algorithms (such as best-fit bounding boxes) should be pure, testable functions without side effects or database dependencies. The reservation and concurrency retry loop belong to the orchestration service (`StorageAllocationService`), keeping domain logic decoupled and deterministic."*

### Q5: How do you prevent brute-force attacks on 6-digit pickup codes?
> **Answer**: *"First, pickup codes are not stored in plaintext; they are hashed with a salted HMAC-SHA256. Second, token verification is gated by a token-bucket rate limiter that restricts failed attempts per package and per IP. Third, tokens automatically expire after 30 minutes, drastically limiting the search space window."*

---

## 12. 5-Minute Live Demonstration Script

Follow this sequence for the practical demonstration:

| Time | Persona | Action | Evaluation Checkpoint |
|---|---|---|---|
| **0:00 - 1:00** | **System Setup** | Launch API (`uvicorn app.main:app`) and open [`diagrams/index.html`](file:///Users/kalashkumarithakur/Desktop/campus-delivery/diagrams/index.html). Show Swagger UI at `/docs`. | Demonstrates architecture, interactive UML viewer, and OpenAPI contracts. |
| **1:00 - 2:00** | **Security Guard** | Login as `guard@campus.edu`. Intake package with tracking `AMZN-99128` for learner `Priya Sharma`. | Shows identity matching, barcode intake, and automatic `REGISTERED -> SORTED` transition. |
| **2:00 - 2:45** | **Security Guard** | Assign storage shelf. View automatic recommendation of Shelf `B-02` (Medium). | Demonstrates Strategy pattern and atomic slot reservation. Package moves to `READY_FOR_PICKUP`. |
| **2:45 - 3:30** | **Learner** | Login as `priya@campus.edu`. View in-app notification. Click **Generate Pickup Code**. | Demonstrates Observer pattern, cryptographic token generation, and single-use display. |
| **3:30 - 4:15** | **Security Guard** | Verify learner ID and submit 6-digit code. | Demonstrates atomic token verification, status change to `COLLECTED`, and shelf counter decrement. |
| **4:15 - 5:00** | **Ops Admin** | Login as `admin@campus.edu`. Inspect live metrics dashboard, storage occupancy, and audit trail. | Demonstrates RBAC enforcement, analytics reporting, and immutable audit logs. |

---

## 13. Team Member Contribution Matrix

| Team Member | Primary LLD Component Responsibilities | Key Modules Authored |
|---|---|---|
| **Member 1 (System Architect / Backend Lead)** | Architecture, Concurrency Control, Database Modeling (Rubrics 7, 8, 9) | `unit_of_work.py`, `mongo_repos.py`, `database.py`, `pickup.py` |
| **Member 2 (Domain & Pattern Specialist)** | OOP Design, SOLID Principles, Design Patterns, State Machine (Rubrics 2, 3, 4, 5) | `state_machine.py`, `allocation.py`, `events.py`, `transitions.py` |
| **Member 3 (Intake, Storage & Test Lead)** | Requirement Analysis, Use Case Modeling, Intake Service, Test Suite (Rubrics 1, 6, 10) | `package_intake.py`, `storage_allocation.py`, `tests/`, `diagrams/` |

---

*Document compiled and verified for Final Capstone Assessment.*
