# 7. SOLID principles and design patterns

## 7.1 SOLID mapped to the code

### S: Single Responsibility Principle

| Responsibility | Lives in (and only there) |
|---|---|
| Package intake and recipient identification | `services/package_intake.py` → `PackageIntakeService` |
| Storage allocation | `services/storage_allocation.py` → `StorageAllocationService` |
| Storage location administration | `services/storage_locations.py` → `StorageLocationService` |
| Pickup codes and handover | `services/pickup.py` → `PickupService` |
| Applying any status change | `services/transitions.py` → `PackageTransitioner` |
| Generic lifecycle actions | `services/lifecycle.py` → `PackageLifecycleService` |
| Notifications | `services/notifications.py` → `NotificationDispatcher`, `NotificationService` |
| Authentication | `services/users.py` → `AuthService`; hashing/JWT in `core/security.py` |
| Reporting | `services/reports.py` → `ReportService` |
| Audit logging | `services/audit.py` → `AuditService` |
| Lifecycle rules | `domain/state_machine.py`; pickup rules `domain/pickup_rules.py`; overdue `domain/overdue.py` |

**Decision.** Each class has one reason to change: e.g. a new pickup policy changes `PickupService`
and `pickup_rules`, never the intake code.
**Without it.** One `PackageService` doing everything would grow to hundreds of lines; a change to
code expiry could break registration, and tests would need the whole world set up.
**Concrete example.** History rows and audit entries for status changes are written in one place,
`PackageTransitioner.apply`. Intake, storage, pickup and lifecycle all call it, so the recording
rule exists exactly once.

### O: Open/Closed Principle

**Decision.** New allocation policies and notification channels are added by writing a new class and
registering it, without editing the workflow that uses them.
- Strategies: registry `ALLOCATION_STRATEGIES` in `container.py`; `StorageAllocationService` only calls `strategy.rank(...)`.
- Channels: `NotificationChannelFactory.register("console_email", ConsoleEmailChannel)` in `infrastructure/notifications.py`; the dispatcher loops over whatever channels it was given.
- Messages: the `TEMPLATES` dict in `services/notifications.py` maps a status to a message builder; adding a message for a new status is a new entry.

**Without it.** Every new channel would mean another `if channel == "sms": …` inside the package
workflow, risking regressions in code that already works.
**Concrete example.** Adding an SMS channel is: `class SmsChannel: channel_type = …; def send(...)`, then
`channel_factory.register("sms", SmsChannel)` and `NOTIFICATION_CHANNELS=in_app,sms`. No service changes
(live-coding task 1 in `13-live-coding-tasks.md`).

### L: Liskov Substitution Principle

**Decision.** Every implementation of a protocol honours the same contract, so any can replace another.
- `FirstAvailableStrategy` and `SuitableSizeStrategy`: both return only candidates that `accepts(size)`, ordered by preference, and never write to the database. The service's "try each in order" loop works for both.
- `InAppChannel`, `ConsoleEmailChannel` (and the test doubles `BrokenEmail`, `WorkingEmail`): `send` either returns (handed over) or raises (`NotificationDeliveryError` or any exception), which the dispatcher records as `FAILED`. None of them has extra preconditions.
- Exceptions: every `ConflictError` subclass can be handled as a 409 by the generic handler.

**Without it.** If one strategy returned full locations, or a channel silently swallowed failures,
code written against the abstraction would behave wrongly only for that subtype.
**Concrete example.** `test_large_package_only_fits_large_locations` runs the same assertion against
both strategies; `test_notification_failure_does_not_undo_the_package_update` swaps in a failing
email channel and the workflow behaves correctly.

### I: Interface Segregation Principle

**Decision.** Protocols are small and specific (`domain/interfaces.py`, `repositories/interfaces.py`):
- `StorageAllocationStrategy` has one method, `rank`.
- `NotificationChannel` has one method, `send`.
- `StorageRepository` declares only `get`, `candidates`, `try_reserve`, `release`; `PickupTokenRepository` only the token operations the pickup service uses.

**Without it.** A large `INotificationProvider` with `send`, `schedule`, `track_delivery`, `get_bounces`
would force `InAppChannel` to implement meaningless methods.
**Concrete example.** `AuditService` depends only on something with `add(entry)` (`AuditRepository`), so
it can be given any object with that one method.

### D: Dependency Inversion Principle

**Decision.** High-level services depend on abstractions; concrete choices are made once in the
composition root (`container.py`).
- `StorageAllocationService(uow, strategy: StorageAllocationStrategy)`: receives the strategy; it does not construct one.
- `NotificationDispatcher(session_factory, channels: list[NotificationChannel])`.
- The domain layer imports no SQLAlchemy or FastAPI. Services reach the database through the Unit of Work's repositories.

**Without it.** Services would `import SmtpClient` and create it inline; tests would need a mail server,
and switching providers would mean editing business code.
**Concrete example.** Tests replace channels at runtime (`container.dispatcher.channels = [InAppChannel(), BrokenEmail()]`)
with no change to production code.

**Where we deliberately did not force SOLID.** Repositories are concrete classes held by the Unit of
Work, and services use `uow.packages` directly rather than receiving a separately injected protocol per
repository. Protocols document the contract, but adding constructor injection for nine repositories
would add ceremony without a second implementation to justify it. ORM models also double as entities
instead of mapping to separate domain classes, which avoids duplicate class hierarchies at this scale;
the rules that matter (state machine, token rules, allocation, overdue) are still pure and tested without a database.

## 7.2 Design patterns

### A. State pattern (table-driven state machine)

- **Problem.** Twelve statuses; arbitrary changes would create contradictions (e.g. collected → ready).
- **Where.** `domain/state_machine.py`: `Transition`, `PackageContext`, `PackageStateMachine`, `TRANSITIONS`; applied by `services/transitions.py: PackageTransitioner`.
- **How.** Each allowed edge is an object with roles and a guard. `check()` rejects anything else.
- **Simpler alternative?** `if/elif` chains in each service were rejected: rules would be scattered and duplicated. The classic GoF State pattern (one class per state) was also rejected: twelve classes with mostly empty methods is harder to read and to review than one table that faculty can compare line by line with the diagram.
- **Trade-offs.** Very readable and testable; the frontend can be driven from `available()`. Guards are simple functions, so complex per-state behaviour would need more structure.

### B. Strategy pattern

- **Problem.** Different shelf allocation policies; the choice should be configurable.
- **Where.** `domain/allocation.py`: `FirstAvailableStrategy`, `SuitableSizeStrategy`; protocol in `domain/interfaces.py`; selected in `container.py` by `STORAGE_ALLOCATION_STRATEGY`; used in `StorageAllocationService._reserve`.
- **Simpler alternative?** A single function with a `mode` argument would work for two policies but grows an `if` per policy and mixes them.
- **Trade-offs.** Strategies only *rank* candidates; the service performs the atomic reservation, so strategies stay pure and cannot create race conditions. One extra indirection to explain.

### C. Repository pattern (+ Unit of Work)

- **Problem.** Keep SQL out of business logic and make one use case one transaction.
- **Where.** `repositories/interfaces.py` (protocols), `repositories/sqlalchemy_repos.py` (implementations), `repositories/unit_of_work.py`.
- **Simpler alternative?** Calling the SQLAlchemy session in services is common in small FastAPI apps. We kept repositories because the concurrency-critical statements (`try_reserve`, `mark_used`, `compare_and_set_status`) deserve named, tested methods.
- **Trade-offs.** More files; some methods are thin wrappers. In return, services read like the business process.

### D. Observer (event-driven notifications)

- **Problem.** Lifecycle changes must notify learners without the workflow knowing about notifications, and a notification failure must not break the workflow.
- **Where.** `domain/events.py` (`PackageStatusChanged`, `EventBus`), `UnitOfWork.record_event/commit`, subscriber `NotificationDispatcher.handle` wired in `container.py`.
- **Simpler alternative?** Calling `notify()` directly in each service. Rejected: it couples every service to notifications, and calling it before commit could notify about changes that later roll back.
- **Trade-offs.** In-process and synchronous after commit (simple, no infrastructure). Events are lost if the process crashes between commit and dispatch; an outbox table would fix this when needed.

### E. Factory

- **Problem.** Build channel objects from configuration names without spreading `if name == …` around.
- **Where.** `infrastructure/notifications.py: NotificationChannelFactory`, used in `container.py`. The strategy registry in `container.py` is a small factory function, `build_allocation_strategy`.
- **Trade-offs.** A dictionary-based factory is enough; a full plugin system would be overkill.

### Also present, by name

- **Composition root / dependency injection**: `container.py`, FastAPI `Depends`.
- **Presenter / DTO**: `api/presenters.py` produces role-aware response models (learners do not see staff names or notes).
- **Value objects**: `StorageCandidate`, `TokenState`, `PackageContext` (frozen dataclasses).
