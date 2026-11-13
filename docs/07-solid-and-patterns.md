# 7. SOLID Principles and Design Patterns

## 7.1 SOLID Evidence Section

### S: Single Responsibility Principle (SRP)
- **Principle**: A class or module should have one, and only one, reason to change.
- **Exact File and Class**:
  - `backend/app/services/package_intake.py` → `PackageIntakeService` (responsible exclusively for package arrival, barcode validation, and recipient association).
  - `backend/app/services/pickup.py` → `PickupService` (responsible exclusively for pickup code generation, verification, and handover execution).
  - `backend/app/services/transitions.py` → `PackageTransitioner` (single centralized authority for applying lifecycle status mutations, status history persistence, and audit logging).
  - `backend/app/domain/state_machine.py` → `PackageStateMachine` (pure lifecycle edge transition rules and precondition guards).
- **What would break without it**: Modifying pickup code hashing or expiry policies would risk destabilizing intake registration, while adding new intake fields would pollute handover logic; a monolithic service would couple disparate database access paths and make unit testing without a full database mock impossible.
- **Concrete Live-Coding Extension Example**: Adding a "Damaged on Arrival Photo Verification" requirement requires changing only `PackageIntakeService.register` and `IncidentService`, without touching `PickupService`, `StorageAllocationService`, or `ReportService`.

---

### O: Open/Closed Principle (OCP)
- **Principle**: Software entities should be open for extension, but closed for modification.
- **Exact File and Class**:
  - `backend/app/domain/allocation.py` → `StorageAllocationStrategy` protocol, `FirstAvailableStrategy`, `SuitableSizeStrategy`.
  - `backend/app/container.py` → `ALLOCATION_STRATEGIES` registry dictionary.
  - `backend/app/infrastructure/notifications.py` → `NotificationChannelFactory`.
  - `backend/app/domain/interfaces.py` → `NotificationChannel` protocol.
- **What would break without it**: Adding SMS notifications or a new "least-loaded" shelf allocation algorithm would require editing core use-case service methods (`StorageAllocationService` or `NotificationDispatcher`) with branching `if/elif` statements, creating regression risks across existing tested production code.
- **Concrete Live-Coding Extension Example**: Adding a third allocation policy (`LeastLoadedStrategy`) requires only writing `class LeastLoadedStrategy` in `backend/app/domain/allocation.py` and registering it with one line in `backend/app/container.py` (`ALLOCATION_STRATEGIES["least_loaded"] = LeastLoadedStrategy`). `StorageAllocationService` remains 100% untouched.

---

### L: Liskov Substitution Principle (LSP)
- **Principle**: Subtypes or protocol implementations must be substitutable for their base types without altering system correctness.
- **Exact File and Class**:
  - `backend/app/domain/allocation.py` → `FirstAvailableStrategy` and `SuitableSizeStrategy` implementing `StorageAllocationStrategy`.
  - `backend/app/infrastructure/notifications.py` → `InAppChannel`, `ConsoleEmailChannel`, `SmtpEmailChannel`, and test doubles `BrokenEmail` / `WorkingEmail` implementing `NotificationChannel`.
- **What would break without it**: If a new allocation strategy mutated database state or returned candidates that did not satisfy `accepts(size)`, or if a notification channel raised uncaught exceptions that aborted caller execution, swapping implementations would break caller invariants.
- **Concrete Live-Coding Extension Example**: `test_large_package_only_fits_large_locations` executes identical assertions against both `FirstAvailableStrategy` and `SuitableSizeStrategy` interchangeably; `test_notification_failure_does_not_undo_the_package_update` injects `BrokenEmail()` into `container.dispatcher.channels`, and the dispatcher safely marks the channel `FAILED` without breaking the package update.

---

### I: Interface Segregation Principle (ISP)
- **Principle**: Clients should not be forced to depend on interfaces or methods they do not use.
- **Exact File and Class**:
  - `backend/app/domain/interfaces.py` → `StorageAllocationStrategy` (declares only `rank(candidates, size)`).
  - `backend/app/domain/interfaces.py` → `NotificationChannel` (declares only `send(recipient, title, message)`).
  - `backend/app/domain/allocation.py` → `StorageCandidate` (lean value object containing only the 6 properties necessary for ranking: `id`, `code`, `capacity`, `occupied`, `max_package_size`, `is_active`).
  - `backend/app/repositories/interfaces.py` → Protocols segregate repositories: `UserRepository`, `StorageRepository`, `PackageRepository`, `PickupTokenRepository`, `PickupRecordRepository`.
- **What would break without it**: If `StorageAllocationStrategy` required full database entities with persistence methods (`save`, `delete`, `commit`), writing a pure ranking algorithm or testing strategies in isolation would require mocking the database session and schema models.
- **Concrete Live-Coding Example**: `AuditService` requires only an object with `add(entry)` (`AuditRepository`); it has no dependency on query filters, pagination, or user lookups.

---

### D: Dependency Inversion Principle (DIP)
- **Principle**: High-level modules should depend on abstractions, not concrete low-level implementations.
- **Exact File and Class**:
  - `backend/app/services/storage_allocation.py` → `StorageAllocationService` depends on `StorageAllocationStrategy` and repository protocols.
  - `backend/app/services/notifications.py` → `NotificationDispatcher` depends on `NotificationChannel` protocol instances.
  - `backend/app/container.py` → Composition root that binds abstractions to concrete implementations from configuration.
- **What would break without it**: High-level services would directly instantiate `SmtpEmailChannel`, PyMongo `MongoClient`, or specific strategy classes inside their constructors, coupling core business rules to third-party drivers and preventing isolated unit testing.
- **Concrete Live-Coding Example**: In tests, replacing an SMTP channel with an in-memory double requires only reassigning `container.dispatcher.channels = [InAppChannel(), WorkingEmail()]`; production service code is completely unaffected.

---

### Where the Design is Deliberately Weaker (Honest Assessment & Justification)

1. **Minimal Inheritance / Role Field on User**:
   - *Design Choice*: The system uses a single `User` document model with a `role: Role` enum rather than a class hierarchy (`LearnerUser`, `SecurityUser`, `AdminUser`).
   - *Justification*: In this domain, all actors share the exact same structural schema (institutional ID, email, hashed password, contact info, timestamps) and authentication mechanics (JWT tokens, password verification). Subclassing would complicate database mapping and repository queries without behavioral benefit. Role-based differences are behavioral authorizations enforced in dependencies (`api/dependencies.py: require(Permission.X)`) and state machine transitions.
2. **Repositories Bound Directly to UnitOfWork**:
   - *Design Choice*: Services receive `UnitOfWork` which exposes concrete PyMongo repositories (`uow.packages`, `uow.users`), rather than injecting nine separate abstract repository protocols into service constructors.
   - *Justification*: Injecting 9 individual repository interfaces into every service constructor creates excessive boilerplate and ceremony for a modular monolith that has a single persistent target (MongoDB). The protocols in `repositories/interfaces.py` clearly specify the architectural contract.
3. **Document Models Serve as Business Entities**:
   - *Design Choice*: `app.infrastructure.models.Document` subclasses are used directly across application services rather than translating between separate ORM/BSON models and pure domain entities.
   - *Justification*: Avoids maintaining dual mirrored class hierarchies and mapping layers for a 12-collection capstone project. Pure business rules that require strict protection (lifecycle transitions, token expiry/HMAC hashing, slot ranking, and overdue derivations) are isolated into pure domain modules (`state_machine.py`, `pickup_rules.py`, `allocation.py`, `overdue.py`) with zero database dependencies.

---

## 7.2 Design Patterns Registry

| Pattern | Category | Exact File and Class | Why Chosen | Simpler Alternative Rejected |
|---|---|---|---|---|
| **Strategy** | Behavioural | `backend/app/domain/allocation.py`<br>`FirstAvailableStrategy`, `SuitableSizeStrategy` | Decouples shelf ranking algorithms from database persistence; allows swapping allocation policies via `.env` without modifying services. | Hardcoded `if/elif` block in `StorageAllocationService._reserve` (rejected: couples algorithms, violates OCP, complicates testing). |
| **Factory** | Creational | `backend/app/infrastructure/notifications.py`<br>`NotificationChannelFactory` | Centralizes creation of notification channels by name; maps configuration strings (`NOTIFICATION_CHANNELS=in_app,smtp`) to channel instances. | Direct `if name == "in_app": return InAppChannel()` inline instantiation (rejected: scatters channel construction across multiple modules). |
| **Observer** | Behavioural | `backend/app/domain/events.py`<br>`EventBus`, `DomainEvent`, `PackageStatusChanged` | Decouples package workflow from side-effects (notifications); isolates failing subscribers so external delivery errors never abort package state changes. | Directly calling `NotificationDispatcher.notify()` inside services (rejected: couples workflow to notifications; risks sending notifications before database commit). |
| **State** (Table-Driven) | Behavioural | `backend/app/domain/state_machine.py`<br>`PackageStateMachine`, `Transition` | Authoritative declarative matrix defining 23 permitted transitions with guards and role permissions; eliminates illegal jumps (e.g. `COLLECTED -> READY`). | Classic GoF State pattern with 12 separate state classes (rejected: creates 12 classes with largely empty methods; table is easier to review and matches faculty diagrams). |
| **Repository** | Structural | `backend/app/repositories/mongo_repos.py`<br>`MongoPackageRepository`, `MongoStorageRepository`, etc. | Encapsulates PyMongo queries, atomic conditional updates (CAS), and projection mapping behind high-level business methods (`try_reserve`, `mark_used`). | Raw PyMongo queries in FastAPI route handlers or services (rejected: duplicates queries, leaks BSON syntax, makes unit testing difficult). |
| **Unit of Work** | Behavioural | `backend/app/repositories/unit_of_work.py`<br>`UnitOfWork` | Maintains dirty tracking across repositories (`Store`), coordinates post-commit domain event dispatching, and rolls back buffered events on failure. | Explicit manual commits and event publishing in every service method (rejected: risks sending notifications for changes that fail to persist). |
| **Dependency Injection / Composition Root** | Structural | `backend/app/container.py`<br>`Container`, `container` | Single composition root that reads settings, builds strategy instances, configures event subscribers, and supplies `UnitOfWork`. | Services constructing their own dependencies inline (rejected: hard-codes dependencies, prevents test double injection). |
| **Module-Level Singleton** | Creational | `backend/app/container.py` (`container`), `backend/app/infrastructure/database.py` (`_client`, `_db`) | Provides shared client connection pooling and application container without global class mutation; described honestly as a Python module-level instance. | Textbook Gang of Four Singleton class with `__new__` overriding (rejected: un-Pythonic, complicates test resetting). |
| **Builder** | Creational | `backend/app/repositories/filters.py`<br>`PackageFilterBuilder` | Fluent construction of complex multi-attribute query filters (`q`, `statuses`, `condition`, `overdue`, date ranges, location) with type safety and chaining. | Passing 9 optional parameters directly to constructor or query functions (rejected: error-prone argument ordering, verbose caller code in API routes). |

---

## 7.3 Detailed Pattern Implementations

### 1. Strategy Pattern (`domain/allocation.py`)
- **Protocol**: `StorageAllocationStrategy` in `domain/interfaces.py`:
  ```python
  class StorageAllocationStrategy(Protocol):
      name: ClassVar[str]
      def rank(self, candidates: Sequence[StorageCandidate], size: PackageSize) -> list[StorageCandidate]: ...
  ```
- **Implementations**:
  - `FirstAvailableStrategy`: Selects the first suitable shelf ordered alphanumerically by code (`G2-A1`, `G2-A2`).
  - `SuitableSizeStrategy`: Conserves large bins by picking the tightest matching size class first (`max_package_size.rank - size.rank`), breaking ties by highest available slot count.
- **Architectural Boundary**: Strategies **only rank** candidates; they never write to the database. The `StorageAllocationService` executes the atomic conditional reservation (`occupied_count < capacity`), ensuring race-free concurrency.

### 2. Factory Pattern (`infrastructure/notifications.py`)
- **Class**: `NotificationChannelFactory` provides a dynamic registry:
  ```python
  channel_factory = NotificationChannelFactory()
  channel_factory.register("in_app", InAppChannel)
  channel_factory.register("console_email", ConsoleEmailChannel)
  channel_factory.register("smtp_email", SmtpEmailChannel)
  ```
- **Usage**: Used during application startup in `container.py` to instantiate channels declared in `settings.notification_channel_names`.

### 3. Observer Pattern (`domain/events.py`)
- **Class**: `EventBus` maintains an in-memory mapping of event types to callback handlers:
  ```python
  class EventBus:
      def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> None: ...
      def publish(self, event: DomainEvent) -> None: ...
  ```
- **Subscriber Isolation**: Each subscriber invocation is wrapped in a `try/except` block. If an external channel delivery fails, the error is logged and the remaining subscribers complete without aborting the caller.

### 4. State Pattern (`domain/state_machine.py`)
- **Implementation**: Table-driven transition matrix (`TRANSITIONS: tuple[Transition, ...]`).
- Each transition defines `(source, target, roles, action, label, guard, requires_dedicated_endpoint)`.
- Precondition guards (`needs_recipient`, `needs_storage`, `needs_recipient_and_storage`) ensure integrity before database interaction.

### 5. Repository & Unit of Work Pattern (`repositories/mongo_repos.py`, `unit_of_work.py`)
- Repositories encapsulate database access and translate between BSON documents and `Document` dataclasses.
- `UnitOfWork` coordinates dirty tracking via `Store`, flushes modifications on `commit()`, and clears uncommitted events on `rollback()`.

### 6. Builder Pattern (`repositories/filters.py`)
- **Class**: `PackageFilterBuilder` provides fluent construction of `PackageFilters`:
  ```python
  builder = (
      PackageFilterBuilder()
      .search(q)
      .with_statuses(status)
      .with_condition(condition)
      .overdue(overdue, settings.collection_deadline_days)
      .arrival_between(start_dt, end_dt)
      .for_location(storage_location_id)
  )
  if user.role == Role.LEARNER:
      builder.for_recipient(user.id)
  filters = builder.build()
  ```
- Tested in `backend/tests/unit/test_rules.py: test_package_filter_builder_constructs_expected_filters`.

### 7. Module-Level Singleton (`container.py`, `database.py`)
- Rather than an artificial GoF Singleton class with metaclasses, standard Python module scoping provides shared instances:
  - `database.py`: `_client` and `_db` are initialized once and returned via `get_client()` and `get_db()`.
  - `container.py`: `container = Container(get_settings())` is instantiated at module import time, providing a single composition root for the application.
