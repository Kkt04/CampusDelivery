# 12. Viva preparation guide

Answers are short and accurate to this codebase. File references let you open the code if asked.

## Architecture and design

**Q1. Why a modular monolith?**
The handover must update several tables atomically (token, package, storage, pickup record, history,
audit). In one database that is one transaction. Microservices would need distributed transactions or
sagas, and campus scale does not need independent scaling. We still keep modules and seams (§2.4, §2.11).

**Q2. What does each layer do? Where is business logic?**
Routes handle HTTP; services are use cases and own transactions; domain holds pure rules
(`state_machine.py`, `pickup_rules.py`, `overdue.py`, `allocation.py`); repositories hold SQL. Business
logic is in services and domain, not in routes or React components.

**Q3. What is the Unit of Work and why use it?**
`repositories/unit_of_work.py`. It gives all repositories one session, so a use case commits or rolls back
as a whole, and it buffers domain events until after the commit.

**Q4. What is `container.py`?**
The composition root: the one place that picks concrete classes (allocation strategy, notification
channels) from configuration and wires the event bus. Services receive abstractions.

## OOP and SOLID

**Q5. Why not `Learner`, `SecurityStaff`, `Admin` subclasses?**
They have identical attributes and no different behaviour of their own; only permissions differ. A role
value plus a permission table is simpler and lets a person's role change without changing their type.
Inheritance is used where substitution is real: strategies, channels, the exception hierarchy.

**Q6. Show encapsulation.**
`StorageCandidate.accepts()` hides the "active, has space, size fits" rule. `PackageTransitioner.apply`
hides every step of a status change; callers cannot change status without history and audit.

**Q7. Show polymorphism.**
`StorageAllocationService` calls `self._strategy.rank(...)` without knowing which strategy it has.
`NotificationDispatcher` calls `channel.send(...)` for in-app and email alike.

**Q8. Give one example per SOLID principle.**
See `07-solid-and-patterns.md`: SRP `PickupService` vs `PackageIntakeService`; OCP channel factory
registration; LSP both strategies only return accepting candidates; ISP one-method protocols; DIP
strategy injected into `StorageAllocationService`.

**Q9. Where did you choose not to apply a principle strictly?**
Repositories are not individually injected as protocols, and ORM models double as entities. A second
implementation does not exist, so extra indirection would add complexity without benefit; the important
rules are still pure and tested without a database.

## Patterns

**Q10. How is the State pattern implemented? Why not a class per state?**
A table of `Transition` objects (source, target, roles, guard) in `domain/state_machine.py`, checked by
`PackageStateMachine.check`. Twelve state classes with mostly empty methods would be harder to review
than a single table that matches the diagram.

**Q11. Why does a strategy only rank candidates?**
So it stays pure and race-free. The service then reserves the first candidate with an atomic UPDATE; if it
loses a race, it tries the next.

**Q12. How is Observer used and what if the subscriber fails?**
`UnitOfWork.commit()` publishes `PackageStatusChanged` after commit; `NotificationDispatcher.handle`
subscribes. `EventBus.publish` catches and logs subscriber exceptions, so a failing subscriber never
affects the committed change.

## Concurrency and reliability

**Q13. Two guards complete the same pickup at the same moment. What happens, step by step?**
Both requests try `SELECT … FOR UPDATE` on the package. One gets the lock; the other waits. The first
consumes the token (`used_at IS NULL` → 1 row), changes status (`status = PICKUP_REQUESTED` → 1 row),
inserts the pickup record and commits. The second then reads status `COLLECTED` and receives
`409 ALREADY_COLLECTED`. Even without the lock, the conditional updates and `UNIQUE(package_id)` would stop it.

**Q14. How do you stop a shelf being overfilled by concurrent requests?**
`UPDATE … SET occupied_count = occupied_count + 1 WHERE id = ? AND is_active AND occupied_count < capacity`;
0 rows means full. Plus `CHECK (occupied_count <= capacity)`.

**Q15. Isn't `occupied_count` duplicated data?**
Yes, deliberately. Counting packages and then inserting is a check-then-act race; a counter makes the
check and reservation one atomic statement. The invariant is maintained only through `try_reserve`/`release`.

**Q16. What exactly is idempotent?**
Registration and handover with an `Idempotency-Key` header: the key, request fingerprint and resulting
resource ID are stored in the same transaction; retries replay the result. Pickup-code requests are safe
to retry (each supersedes the previous). Re-assigning the same shelf, resolving a resolved incident and
marking a read notification are no-ops.

**Q17. What if the database fails halfway through a handover?**
The exception propagates, the Unit of Work rolls back, nothing is saved, and the client gets a generic 500
with a request ID. `test_failure_halfway_through_handover_rolls_everything_back` forces this.

**Q18. What happens if the email provider is down?**
The package change is already committed. Notification rows are saved as PENDING, the failing channel is
marked FAILED with the error, the in-app message is SENT to the inbox, and admins can retry. We never
claim delivery: SENT means handed to the channel; `read_at` records reading.

**Q19. How does SQLite handle the concurrency tests without row locks?**
Every SQLite transaction starts with `BEGIN IMMEDIATE`, which takes the write lock at the start, so writers
run one at a time. PostgreSQL uses real row locks. The tests pass on both.

## Security

**Q20. How are passwords stored?** bcrypt with a per-password salt and configurable cost (`core/security.py`).

**Q21. Describe the token strategy.**
On login the server issues a signed HS256 JWT (`sub`, `role`, `iat`, `exp`, 60 minutes). The frontend
stores it in `sessionStorage` and sends `Authorization: Bearer …`. Every request reloads the user from the
database, so deactivated users are rejected immediately even with an unexpired token.

**Q22. Why is the pickup code secure if it is only 6 digits?**
It is random (`secrets`), valid for 30 minutes, single-use, bound to one package and recipient, locked after
5 wrong tries, and staff also check the learner's ID card. Only an HMAC of salt + code is stored, so a
database leak does not reveal usable codes.

**Q23. Hiding a button in React is not security. Where is authorisation enforced?**
In `api/dependencies.py`: `require(Permission.X)` on each route, plus ownership checks in services (a
learner's package must have `recipient_id == user.id`). Tests call the API directly to prove it.

**Q24. Why return 404, not 403, for another learner's package?**
403 would confirm the package exists. 404 reveals nothing.

**Q25. How do you avoid leaking errors?**
A catch-all handler in `main.py` logs the stack trace server-side and returns `INTERNAL_ERROR` with a request ID only.

## Database

**Q26. Explain the main relationships.**
A user receives many packages (recipient, nullable while unidentified) and registers many. A package has
many history rows and tokens, zero or one pickup record, and zero or one current storage location. See §4.

**Q27. Why ON DELETE RESTRICT everywhere?** History and proof of handover must never disappear; users are deactivated instead of deleted.

**Q28. Which indexes matter most and why?** `tracking_id` (duplicates), `recipient_id` (learner list), `(status, arrived_at)` (queues and overdue), `arrived_at` (reports).

**Q29. Why store enums as VARCHAR rather than native PostgreSQL enums?** Portability to SQLite and easier migrations (adding a status needs no `ALTER TYPE`); the application validates values.

## Lifecycle

**Q30. Difference between condition, status and overdue?**
Condition is a physical fact recorded at intake. Status is the lifecycle position, changed only through the
state machine. Overdue is calculated at read time from status and arrival date and never stored.

**Q31. Can a collected package become ready again?** No. COLLECTED is terminal with no outgoing transitions; the state machine rejects it (tested).

## Testing

**Q32. How do you test without touching real data?**
`tests/conftest.py` points the app at a temporary SQLite file (or `TEST_DATABASE_URL`) before importing it,
and recreates all tables for every test.

**Q33. How does the concurrency test work?**
Two threads, each with its own Unit of Work, start together on a `threading.Barrier` and call
`PickupService.complete` with the same code. The test asserts one success, one `ALREADY_COLLECTED`, one
pickup record, and that storage was released once.
