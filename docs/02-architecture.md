# 2. Architecture

## 2.1 Component diagram

```mermaid
flowchart LR
  subgraph Browser["Browser: React + TypeScript (Vite)"]
    Pages["pages/ (learner, security, ops, shared)"] --> Hooks["lib/useApi, useAction"]
    Pages --> AuthCtx["auth/AuthContext + RequireRole"]
    Hooks --> Endpoints["api/endpoints.ts"] --> Client["api/client.ts (fetch, token, errors)"]
  end

  Client -- "HTTPS JSON /api/v1 + Bearer JWT" --> Routes

  subgraph API["FastAPI modular monolith"]
    Routes["api/routes/*"] --> Deps["api/dependencies (auth, RBAC, UoW)"]
    Routes --> Presenters["api/presenters (role-aware output)"]
    Routes --> Services["services/* (use cases)"]
    Services --> Domain["domain/* (state machine, rules, strategies, events)"]
    Services --> UoW["repositories/UnitOfWork"]
    UoW --> Repos["repositories/sqlalchemy_repos"]
    UoW -- "publish after commit" --> Bus["domain/events.EventBus"]
    Bus --> Dispatcher["services/notifications.NotificationDispatcher"]
    Dispatcher --> Channels["infrastructure/notifications (InApp, ConsoleEmail)"]
    Container["container.py (composition root)"] -.wires.-> Services
    Container -.wires.-> Bus
  end

  Repos --> DB[("MongoDB 6+ Database")]
  Dispatcher --> DB
```

## 2.2 Layers and their rules

| Layer | Folder | Responsibility | May depend on |
|---|---|---|---|
| Presentation | `frontend/src` | Screens, forms, role-aware navigation. No business rules beyond convenience hiding. | Backend HTTP API only |
| API | `app/api` | HTTP: parse/validate input, authenticate, check permission, call a service, shape the response, map errors to status codes. | services, schemas, domain (read-only helpers) |
| Schemas | `app/schemas` | Pydantic request/response models and field validation. | domain enums |
| Services | `app/services` | Application use cases; own the transaction boundary (`uow.commit()`); coordinate repositories and domain rules. | domain, repositories |
| Domain | `app/domain` | Pure business rules: lifecycle state machine, permissions, pickup-token rules, overdue rule, allocation strategies, events, protocols. **No SQLAlchemy or FastAPI imports.** | `app/core` only |
| Repositories | `app/repositories` | Persistence: queries and atomic conditional updates; Unit of Work. | infrastructure models |
| Infrastructure | `app/infrastructure` | Engine/session, ORM models, notification channels. | core |

**Rule of thumb for the viva:** a route handler never decides *whether* something is allowed by
business rules; it asks a service. The service asks the domain (`state_machine.check`, `ensure_token_usable`).

## 2.3 How one request flows (complete handover)

1. `POST /api/v1/pickups/complete` with JSON body and `Idempotency-Key` header.
2. `require(Permission.PICKUP_HANDOVER)` decodes the JWT, loads the user from the DB (inactive → 401) and checks the role permission (→ 403).
3. Pydantic validates the body (`code` must be 6 digits, → 422).
4. `PickupService.complete` locks the package row, checks the idempotency key, validates the code via `domain.pickup_rules`, consumes the token with a conditional UPDATE, applies `PICKUP_REQUESTED → COLLECTED` through `PackageTransitioner` (which releases the shelf, writes history and audit, and queues an event), adds the `pickup_records` row and the idempotency record, then commits.
5. After commit the Unit of Work publishes `PackageStatusChanged`; the notification dispatcher writes and sends the "Package collected" message in its own transaction.
6. The presenter returns a `PickupRecordOut`. Errors anywhere are rolled back and returned as `{"error": {code, message, details, request_id}}`.

## 2.4 Why a modular monolith and not microservices

- **Scale does not require it.** One gate, a few thousand packages a month. A single process on one server handles this with large headroom.
- **The core operations need ACID transactions across several tables.** Handover touches packages, tokens, storage, pickup records, history, audit and idempotency keys. In one database this is one transaction. Across services it would need sagas, compensations and eventual consistency, which add failure modes we would then have to test and explain.
- **Team and timeline.** One student, one deployment, one codebase to debug.
- **We still keep the benefits of modularity**: clear layers, services per use case, protocols at the seams, and a composition root. Those seams are exactly where a module could be extracted later (section 2.10).

## 2.5 Why MongoDB and Document Model Architecture

- **Document flexibility with schema validation**: Package intake data contains rich nested and optional operational metadata (condition notes, recipient hints, incident links, token hashes). MongoDB documents naturally represent these entities while BSON models (`Document` base class in `infrastructure/models.py`) provide typed serialization.
- **Conditional atomic single-document updates**: Standalone MongoDB provides atomic document-level operations via `find_one_and_update`. Concurrency safety is achieved by placing preconditions directly in the write filter (e.g. `used_at: null`, `occupied_count < capacity`, `status: PICKUP_REQUESTED`).
- **Compound & Unique indexing**: Strict integrity guarantees via database indexes:
  - Unique: `users.institutional_id`, `users.email`, `packages.internal_code`, `packages.tracking_id` (partial filter on string), `pickup_records.package_id`, `pickup_records.token_id`, `idempotency_keys(user_id, scope, key)`.
  - Compound: `packages(status, arrived_at)` for overdue queues; `notifications(user_id, created_at)` for learner inboxes.
- **Auto-increment Integer IDs**: Managed via an atomic `counters` collection (`app.infrastructure.database.next_id`), ensuring clean REST URLs (`/packages/12`) without exposing raw ObjectIDs.
- **Operational simplicity**: Zero migration friction; indexes are bootstrapped automatically at application startup (`init_db()`).

## 2.6 How double pickup is prevented

Four independent layers in `services/pickup.py` and the schema guarantee that double collection is structurally impossible:

| Layer | Mechanism | Where |
|---|---|---|
| 1. Idempotency Guard | Replays previously completed handover if the same `Idempotency-Key` is retried. | `MongoIdempotencyRepository.find` |
| 2. Consume code once | `find_one_and_update({"_id": token_id, "used_at": None, "revoked_at": None}, {"$set": {"used_at": now}})`. Exactly 1 thread can update the document; racing requests return None. | `MongoPickupTokenRepository.mark_used` |
| 3. Status Compare-and-Set | `find_one_and_update({"_id": pkg_id, "status": "PICKUP_REQUESTED"}, {"$set": {"status": "COLLECTED", "closed_at": now}})`. Requires status to match `PICKUP_REQUESTED`. | `MongoPackageRepository.compare_and_set_status` |
| 4. Database constraint | Unique index on `pickup_records.package_id` and `pickup_records.token_id`. Any racing duplicate insert is rejected by MongoDB. | `init_db()` unique index |

Verified by `test_concurrent_handover_results_in_exactly_one_collection` (two threads, two staff members, same code).

## 2.7 How storage capacity is protected against concurrent allocations

A slot is reserved with one atomic conditional statement:

```python
db["storage_locations"].find_one_and_update(
    {"_id": location_id, "is_active": True, "occupied_count": {"$lt": capacity}},
    {"$inc": {"occupied_count": 1}},
    return_document=ReturnDocument.AFTER,
)
```

If multiple requests race for the last available slot, MongoDB serializes document-level updates:
1. The first request finds `occupied_count < capacity`, increments the counter, and succeeds.
2. The second request evaluates the filter, finds `occupied_count == capacity`, modifies 0 documents, and returns `None`.
3. The service raises `409 STORAGE_FULL` (or for automatic allocation, tries the next candidate ranked by `StorageAllocationStrategy`).
Releasing a slot upon package handover, return, or shelf relocation executes `{"$inc": {"occupied_count": -1}}` with filter `occupied_count: {"$gt": 0}`.

Invariant: `occupied_count` equals the count of active packages whose `storage_location_id` points to the shelf.
Verified by `test_concurrent_allocation_never_exceeds_capacity`.

## 2.8 How duplicate requests are handled

| Operation | Retry behaviour | How it is enforced |
|---|---|---|
| Register package (`POST /packages`) | **Idempotent with `Idempotency-Key`.** Same key + same body → `200` with the original package and header `Idempotent-Replayed: true`. Same key + different body → `409 IDEMPOTENCY_KEY_REUSED`. Without a key, a repeated tracking ID is still caught as a duplicate. | Table `idempotency_keys` with `UNIQUE(user_id, scope, key)`, written in the same transaction as the package. A concurrent duplicate hits the unique constraint, rolls back, and is answered with the stored result. |
| Complete handover (`POST /pickups/complete`) | **Idempotent with `Idempotency-Key`**: a retry returns the original pickup record (`200`). Without a key, a retry gets `409 ALREADY_COLLECTED`, which is safe (nothing happens twice). | Same table; key checked after the row lock, so a waiting retry sees the committed first attempt. |
| Request pickup code | **Safe retry**: every call issues a new code and revokes the previous one, so the latest response shown to the learner is always the valid code. We cannot replay the old response because the plaintext code is never stored. | `revoke_active` + new token in one transaction |
| Assign storage to the same location again | No-op (no second reservation). | `StorageAllocationService.assign` compares with current location |
| Resolve an incident twice, mark a notification read twice | No-op. | Status/`read_at` checks |

The frontend creates one key per form submission (`newIdempotencyKey()`) and reuses it if the user presses the button again after a network error.

## 2.9 What happens when notification delivery fails

1. The package change commits first. Only then does the Unit of Work publish the event.
2. The dispatcher (its own DB session) writes one `notifications` row per channel with status `PENDING` and commits, so the record exists even if every channel fails.
3. It calls each channel. Success → `SENT` (meaning *handed to the channel*, never "delivered" or "read"); failure → `FAILED` with `last_error`. Exceptions never propagate back to the request; the event bus also isolates each subscriber.
4. The dashboard shows the failed count; admins call `POST /notifications/retry-failed`, which retries `FAILED`/stuck `PENDING` rows up to `NOTIFICATION_MAX_ATTEMPTS` (3).
5. The in-app message is still in the learner's inbox, which is why the learner can always see it in the app.

Verified by `test_notification_failure_does_not_undo_the_package_update`.

Limitation: if the API process crashes between commit and dispatch, no notification row is written for that event. A transactional outbox (write the event row in the same transaction, process it later) closes that gap; see `10-limitations.md`.

## 2.10 How the system could scale

| Pressure | Step (in order of cost) |
|---|---|
| More API traffic | Run several Uvicorn/Gunicorn workers or containers behind a load balancer; the API is stateless except the in-memory login limiter (move it to the database or a shared cache at that point). |
| Larger tables | Existing indexes cover the hot queries; add pagination by keyset, archive closed packages older than N months into a history table, and add PostgreSQL read replicas for reports. |
| Slow notifications (real email/SMS) | Transactional outbox table + a background worker process that sends and retries, so requests never wait on a provider. |
| Several gates/campuses | Add a `gate` (or `site`) entity referenced by storage locations and packages; scope staff permissions by gate. |
| Heavy reporting | Materialised views or a nightly summary table; or a separate reporting replica. |

## 2.11 What would be extracted into a separate service, and only when

| Candidate | Extract only if … |
|---|---|
| Notification delivery worker | Real providers are added and sending becomes slow or needs its own retry/scaling policy. It already sits behind an event bus and channel protocol, so it can move to a worker consuming an outbox table. |
| Reporting/analytics | Report queries start to slow the transactional database; move to a read replica or warehouse fed by change events. |
| Identity/authentication | The campus adopts single sign-on (SAML/OIDC); replace local login with the identity provider rather than building our own service. |

The **package lifecycle, storage and pickup** must stay together: they share one transaction for the
handover and splitting them would reintroduce the double-collection problem across a network boundary.
