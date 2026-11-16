# Viva & LLD Evaluation Search Tags Index

This master index maps every evaluation criterion (1 through 10) directly to search tags embedded throughout the codebase comments. When asked in your viva or defense, simply type the search keyword into your IDE search (VS Code / PyCharm / grep: `Cmd+Shift+F`) to jump straight to the exact code, its architectural justification, and your defense talking points.

---

## Quick Reference Search Cheat Sheet

| # | LLD Evaluation Criterion | Search Keyword / Tag | Primary Files & Classes | What It Is For & How We Use It |
|---|---|---|---|---|
| **1** | **Requirement Analysis** | `[EVAL-1: REQUIREMENTS]` | `domain/enums.py`<br>`services/package_intake.py`<br>`services/storage_allocation.py`<br>`services/pickup.py`<br>`domain/state_machine.py` | Maps FR-1 through FR-8 and Actor Roles (Learner, Security, Admin) to domain operations, preconditions, and guards. |
| **2** | **Class Diagram & Relations** | `[EVAL-2: CLASS-DIAGRAM]` | `infrastructure/models.py`<br>`Document`, `Package`, `User`, `StorageLocation`, `PickupToken`, `PickupRecord` | Defines 1-to-N association, aggregation, composition, and 1-to-1 UK relationships with multiplicities. |
| **3** | **OOP: Abstraction** | `[EVAL-3: OOP-ABSTRACTION]` | `domain/interfaces.py`<br>`repositories/interfaces.py`<br>`StorageAllocationStrategy`<br>`NotificationChannel` | Defines abstract protocols and interfaces using `typing.Protocol` to decouple business logic from implementations. |
| **3** | **OOP: Encapsulation** | `[EVAL-3: OOP-ENCAPSULATION]` | `domain/allocation.py`<br>`repositories/filters.py`<br>`api/presenters.py` | Encapsulates storage ranking algorithms, query filters in value objects, and role-based field redactions. |
| **3** | **OOP: Inheritance** | `[EVAL-3: OOP-INHERITANCE]` | `infrastructure/models.py`<br>`Document` -> `User`, `Package`<br>`core/exceptions.py`<br>`AppError` -> `ConflictError` | Shared serialization/deserialization methods (`to_doc`, `from_doc`) and hierarchical domain error handling. |
| **3** | **OOP: Polymorphism** | `[EVAL-3: OOP-POLYMORPHISM]` | `domain/allocation.py`<br>`FirstAvailableStrategy`<br>`SuitableSizeStrategy` | Multiple strategy implementations satisfy `StorageAllocationStrategy.allocate()` with interchangeable behavior. |
| **4** | **SOLID: Single Responsibility** | `[EVAL-4: SOLID-SRP]` | `services/package_intake.py`<br>`services/storage_allocation.py`<br>`services/pickup.py`<br>`services/transitions.py` | Each service handles exactly one business lifecycle responsibility (intake, allocation, handover, transition). |
| **4** | **SOLID: Open/Closed** | `[EVAL-4: SOLID-OCP]` | `domain/allocation.py`<br>`infrastructure/notifications.py`<br>`container.py` | New allocation strategies or notification channels (SMS, Push) plug in via factory registries without modifying existing services. |
| **4** | **SOLID: Liskov Substitution** | `[EVAL-4: SOLID-LSP]` | `domain/allocation.py`<br>`infrastructure/notifications.py` | Any `NotificationChannel` or `StorageAllocationStrategy` subtype seamlessly substitutes without breaking callers. |
| **4** | **SOLID: Interface Segregation** | `[EVAL-4: SOLID-ISP]` | `domain/interfaces.py`<br>`repositories/interfaces.py` | Repositories and channels are segregated by aggregate root rather than combined into a bloated monolith. |
| **4** | **SOLID: Dependency Inversion** | `[EVAL-4: SOLID-DIP]` | `container.py`<br>`domain/interfaces.py`<br>`repositories/interfaces.py` | High-level services depend on abstract protocols; `container.py` composition root injects concrete dependencies. |
| **5** | **Pattern: Strategy** | `[EVAL-5: PATTERN-STRATEGY]` | `domain/allocation.py`<br>`StorageAllocationStrategy` | Interchangeable shelf assignment algorithms (`FirstAvailableStrategy`, `SuitableSizeStrategy`). |
| **5** | **Pattern: Factory** | `[EVAL-5: PATTERN-FACTORY]` | `infrastructure/notifications.py`<br>`NotificationChannelFactory` | Dynamic registry creating notification channels by name from configuration settings. |
| **5** | **Pattern: Observer** | `[EVAL-5: PATTERN-OBSERVER]` | `domain/events.py`<br>`EventBus`, `DomainEvent` | Decoupled event publication on UoW commit; isolated subscriber error handling prevents transaction disruption. |
| **5** | **Pattern: State** | `[EVAL-5: PATTERN-STATE]` | `domain/state_machine.py`<br>`PackageStateMachine` | Table-driven FSM enforcing 22 permitted lifecycle transitions, roles, and precondition guards. |
| **5** | **Pattern: Builder** | `[EVAL-5: PATTERN-BUILDER]` | `repositories/filters.py`<br>`PackageFilterBuilder` | Step-by-step fluent construction of multi-parameter package search filters without telescoping constructors. |
| **5** | **Pattern: Repository** | `[EVAL-5: PATTERN-REPOSITORY]` | `repositories/mongo_repos.py`<br>`MongoPackageRepository`, etc. | Encapsulates all PyMongo queries, projections, and BSON document translations away from business services. |
| **5** | **Pattern: Unit of Work** | `[EVAL-5: PATTERN-UNIT-OF-WORK]` | `repositories/unit_of_work.py`<br>`UnitOfWork` | Context manager tracking dirty state across repos, coordinating commit/rollback, and firing post-commit events. |
| **5** | **Pattern: Singleton** | `[EVAL-5: PATTERN-SINGLETON]` | `container.py` (`container`)<br>`infrastructure/database.py` (`_client`, `_db`) | Module-level singleton pattern ensuring a single shared MongoClient pool and DI container across requests. |
| **5** | **Pattern: Decorator** | `[EVAL-5: PATTERN-DECORATOR]` | `api/dependencies.py`<br>`require(Permission.X)` | Parameterized dependency decorator enforcing fine-grained role permissions before route execution. |
| **6** | **Sequence / Activity Flow** | `[EVAL-6: SEQUENCE-FLOW]` | `services/package_intake.py`<br>`services/storage_allocation.py`<br>`services/pickup.py` | Step-by-step execution flows documented inline: Gate Intake -> Storage Allocation -> Token Generation -> Handover. |
| **7** | **API & Layer Separation** | `[EVAL-7: API-LAYER-SEPARATION]` | `api/routes/packages.py`<br>`api/routes/pickups.py`<br>`api/presenters.py` | Strict 4-layer separation: HTTP Controller -> Application Service -> Domain Entity/FSM -> MongoDB Repository. |
| **8** | **Database Schema & Indexes** | `[EVAL-8: DB-SCHEMA-INDEXING]` | `infrastructure/database.py`<br>`infrastructure/models.py` | MongoDB collections, atomic sequence generator `next_id`, unique indexes, compound indexes, and partial filter indexes. |
| **9** | **Error Handling & Concurrency** | `[EVAL-9: ERROR-HANDLING-CONCURRENCY]` | `repositories/mongo_repos.py`<br>`services/pickup.py`<br>`core/exceptions.py`<br>`core/rate_limit.py`<br>`main.py` | Atomic CAS concurrency (`find_one_and_update`), anti-double collection defense, sliding-window rate limit, RFC 7807 handler. |
| **10** | **Working Implementation** | `[EVAL-10: WORKING-IMPLEMENTATION]` | `main.py`<br>`seed.py`<br>`tests/` (92 tests passing) | Fully functional FastAPI + MongoDB backend, automated demo seed data, health checks, and test suite. |

---

## Detailed Evaluation Breakdown & Viva Talking Points

### 1. Requirement Analysis (`[EVAL-1: REQUIREMENTS]`)
* **What it is for:** Proves the system completely models the university campus parcel reception problem.
* **How we use it:**
  * **FR-1 (Intake & Logging):** `services/package_intake.py` generates unique `PKG-YYMMDD-XXXXX` codes, records courier, condition, and recipient.
  * **FR-2 (Storage Allocation):** `services/storage_allocation.py` places packages onto capacity-constrained shelves by dimension.
  * **FR-4 & FR-5 (Pickup & Handover):** `services/pickup.py` generates single-use HMAC-SHA256 OTPs and enforces verified handover.
  * **FR-6 (Security Gatekeeper):** `domain/enums.py` and `domain/permissions.py` restrict operational tasks to security guards.
  * **FR-8 (Audit & Traceability):** Every transition writes immutable audit logs with actor ID and timestamp.
* **Viva Answer:** *"Requirements are segregated into functional workflows (Intake, Storage, Handover, Incidents) and enforced on the backend via Role-Based Access Control and finite state machine guards."*

### 2. Class Diagram & Relationships (`[EVAL-2: CLASS-DIAGRAM]`)
* **What it is for:** Shows entity structure, cardinality, and relationships.
* **How we use it in `infrastructure/models.py`:**
  * `User (1) ---- (0..*) Package`: Association via `recipient_id` and `received_by_id`.
  * `StorageLocation (1) ---- (0..*) Package`: Aggregation via `storage_location_id`.
  * `Package (1) ---- (0..*) PackageStatusHistory`: Composition (history cannot exist without a package).
  * `Package (1) ---- (0..*) PickupToken`: Composition (tokens belong exclusively to one package).
  * `Package (1) ---- (0..1) PickupRecord`: 1-to-1 association enforced by MongoDB unique index on `pickup_records.package_id`.
* **Viva Answer:** *"All entities inherit from a common `Document` dataclass. Relationships are referenced via foreign integer IDs and selectively hydrated by repositories without requiring heavy ORMs."*

### 3. Object-Oriented Design (`[EVAL-3]`)
* **Abstraction (`[EVAL-3: OOP-ABSTRACTION]`):** Defined via `typing.Protocol` in `domain/interfaces.py` (`StorageAllocationStrategy`, `NotificationChannel`) and `repositories/interfaces.py` (`PackageRepository`, `UserRepository`). Services never depend on PyMongo.
* **Encapsulation (`[EVAL-3: OOP-ENCAPSULATION]`):** Internal ranking logic in `SuitableSizeStrategy`, query construction in `PackageFilterBuilder`, and sensitive staff data redaction in `api/presenters.py`.
* **Inheritance (`[EVAL-3: OOP-INHERITANCE]`):** `Document` base class encapsulates BSON dictionary serialization (`to_doc`, `from_doc`, `apply_doc`). Domain exception hierarchy inherits from `AppError`.
* **Polymorphism (`[EVAL-3: OOP-POLYMORPHISM]`):** `FirstAvailableStrategy` and `SuitableSizeStrategy` provide polymorphic implementations of `allocate()`. Callers invoke the method identically regardless of which strategy is active.
* **Viva Answer:** *"We prioritize composition over inheritance; inheritance is used where behavioral sharing is absolute (`Document`, `AppError`), while abstraction and polymorphism are achieved via Python Protocols."*

### 4. SOLID Principles (`[EVAL-4]`)
* **S - Single Responsibility (`[EVAL-4: SOLID-SRP]`):** `PackageIntakeService` only handles parcel intake; `StorageAllocationService` only manages shelf reservations; `PickupService` only handles handover.
* **O - Open/Closed (`[EVAL-4: SOLID-OCP]`):** Adding a new storage strategy requires only creating a new class in `domain/allocation.py` and registering it in `container.py`. No existing service code is modified.
* **L - Liskov Substitution (`[EVAL-4: SOLID-LSP]`):** `SuitableSizeStrategy` and `FirstAvailableStrategy` adhere to the exact same return contract: `StorageCandidate | None`.
* **I - Interface Segregation (`[EVAL-4: SOLID-ISP]`):** Repositories are segregated into distinct protocols (`UserRepository`, `PackageRepository`, `StorageRepository`) rather than a giant God repository.
* **D - Dependency Inversion (`[EVAL-4: SOLID-DIP]`):** Services depend upon repository protocols. Concrete MongoDB repositories are instantiated and wired by `container.py`.
* **Viva Answer:** *"Every SOLID principle is implemented directly: SRP through specialized services, OCP via factory registries, LSP via Protocol contracts, ISP through focused repository interfaces, and DIP through the container composition root."*

### 5. Design Patterns (`[EVAL-5]`)
* **Strategy (`[EVAL-5: PATTERN-STRATEGY]`):** `domain/allocation.py` (`StorageAllocationStrategy`).
* **Factory (`[EVAL-5: PATTERN-FACTORY]`):** `infrastructure/notifications.py` (`NotificationChannelFactory`).
* **Observer (`[EVAL-5: PATTERN-OBSERVER]`):** `domain/events.py` (`EventBus`). Events are published post-commit; subscriber errors are caught to isolate transactions.
* **State (`[EVAL-5: PATTERN-STATE]`):** `domain/state_machine.py` (`PackageStateMachine`). Table-driven with 22 validated transitions and role guards.
* **Builder (`[EVAL-5: PATTERN-BUILDER]`):** `repositories/filters.py` (`PackageFilterBuilder`). Fluent construction of complex multi-criteria filters.
* **Repository (`[EVAL-5: PATTERN-REPOSITORY]`):** `repositories/mongo_repos.py`. Hides PyMongo queries and BSON translation.
* **Unit of Work (`[EVAL-5: PATTERN-UNIT-OF-WORK]`):** `repositories/unit_of_work.py` (`UnitOfWork`). Persistence context manager and dirty tracking.
* **Singleton (`[EVAL-5: PATTERN-SINGLETON]`):** `container.py` and `infrastructure/database.py`. Module-level singletons managing shared connection pools.
* **Decorator (`[EVAL-5: PATTERN-DECORATOR]`):** `api/dependencies.py` (`require(permission)`). Fast, declarative RBAC route protection.
* **Viva Answer:** *"We selected 9 design patterns based on concrete architectural needs, deliberately rejecting textbook patterns that added unnecessary bloat (e.g., using a table-driven State machine instead of 12 separate GoF classes)."*

### 6. Sequence / Activity Diagrams (`[EVAL-6: SEQUENCE-FLOW]`)
* **Intake Flow (`services/package_intake.py`):** Check Idempotency -> Check duplicate tracking -> Generate internal code -> Check condition/recipient -> Commit Package -> Audit.
* **Handover Flow (`services/pickup.py`):** Learner requests OTP -> Salted HMAC token generated -> Security inputs code -> Verify token -> Atomic CAS marks token used -> Status CAS transitions to COLLECTED -> Insert PickupRecord -> Audit.
* **Storage Flow (`services/storage_allocation.py`):** Check storable status -> Consult Strategy -> Atomic `try_reserve()` on shelf -> Release old shelf if moving -> Transition to STORED -> Audit.

### 7. API / Interface Design (`[EVAL-7: API-LAYER-SEPARATION]`)
* **4 Distinct Layers:**
  1. **Controller / HTTP Layer:** `api/routes/*.py` handles query parameters, request validation, and status codes.
  2. **Presenter Layer:** `api/presenters.py` projects domain entities into Pydantic DTOs with role-based field redactions.
  3. **Application Service Layer:** `services/*.py` orchestrates business use cases and transaction boundaries.
  4. **Domain & Repository Layer:** `domain/*.py` and `repositories/*.py` enforce invariants and handle MongoDB persistence.

### 8. Database Schema & Indexing (`[EVAL-8: DB-SCHEMA-INDEXING]`)
* **Collections:** `users`, `packages`, `storage_locations`, `pickup_tokens`, `pickup_records`, `package_status_history`, `notifications`, `incidents`, `audit_logs`, `idempotency_keys`, `counters`.
* **Atomic Sequential ID:** `next_id(collection)` uses `find_one_and_update` on `counters` with `$inc: {"seq": 1}`.
* **Unique Indexes:**
  * `users.institutional_id`, `users.email`
  * `packages.internal_code`
  * `packages.tracking_id` (partial filter index where `tracking_id: {"$type": "string"}`)
  * `pickup_records.package_id` (guarantees anti-double collection at the database engine level)
  * `idempotency_keys(user_id, scope, key)`

### 9. Error Handling, Concurrency & Edge Cases (`[EVAL-9: ERROR-HANDLING-CONCURRENCY]`)
* **Atomic Compare-And-Set (CAS):**
  * `compare_and_set_status()`: Status change query matches `{"_id": id, "status": expected}`. If racing thread modified status first, update returns None and raises `ConcurrentModificationError`.
  * `try_reserve()`: Shelf capacity query matches `{"$expr": {"$lt": ["$occupied_count", "$capacity"]}}`.
  * `mark_used()`: Token query matches `{"_id": token_id, "used_at": None}`.
* **Anti-Double-Collection (Defense-in-Depth):**
  1. Atomic CAS `mark_used` on token.
  2. Status CAS `compare_and_set_status` on package.
  3. Database Unique Index on `pickup_records.package_id`.
  4. Idempotency Key deduplication.
* **RFC 7807 Exception Formatting:** Uniform error payload with correlation ID (`X-Request-ID`), machine-readable code, and zero stack traces leaked.
* **Brute-Force Protection:** `SlidingWindowRateLimiter` with `threading.Lock` and `Retry-After` headers.

### 10. Working Implementation (`[EVAL-10: WORKING-IMPLEMENTATION]`)
* **FastAPI Application:** Fully modular, asynchronous lifespan, CORS enabled.
* **Real MongoDB Integration:** Runs natively against standalone MongoDB 7 or MongoDB Atlas, with automatic seamless in-memory mongomock fallback for zero-setup demo environments.
* **Automated Seed Data:** `app/seed.py` creates demo accounts (Admin, Security, Learners) and realistic parcel lifecycles.
* **Test Suite:** 92 automated tests (40 unit, 52 API) verifying all workflows, edge cases, and concurrency scenarios.
