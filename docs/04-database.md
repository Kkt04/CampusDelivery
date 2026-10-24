# 4. Database design

## 4.1 ER diagram

```mermaid
erDiagram
  users ||--o{ packages : "receives (recipient_id, nullable)"
  users ||--o{ packages : "registers (received_by_id)"
  storage_locations |o--o{ packages : "holds (storage_location_id, nullable)"
  packages ||--|{ package_status_history : "has"
  users ||--o{ package_status_history : "changed_by"
  packages ||--o{ pickup_tokens : "issued for"
  users ||--o{ pickup_tokens : "issued to"
  packages ||--o| pickup_records : "collected as (UNIQUE)"
  pickup_tokens ||--o| pickup_records : "redeemed by (UNIQUE)"
  users ||--o{ pickup_records : "learner / handed_over_by"
  users ||--o{ notifications : "receives"
  packages |o--o{ notifications : "about"
  packages |o--o{ incidents : "concerns"
  users ||--o{ incidents : "reported_by / resolved_by"
  users |o--o{ audit_logs : "actor"
  users ||--o{ idempotency_keys : "owns"

  users {
    int id PK
    varchar institutional_id UK
    varchar full_name
    varchar email UK
    varchar phone
    varchar role "LEARNER|SECURITY|ADMIN"
    varchar password_hash "bcrypt"
    bool is_active
    timestamptz created_at
    timestamptz updated_at
  }
  storage_locations {
    int id PK
    varchar code UK
    varchar description
    int capacity "CHECK > 0"
    int occupied_count "CHECK 0..capacity"
    varchar max_package_size
    bool is_active
  }
  packages {
    int id PK
    varchar internal_code UK "PKG-yymmdd-XXXXX"
    varchar courier_name
    varchar tracking_id UK "nullable, normalised"
    int recipient_id FK
    varchar recipient_hint
    varchar size
    varchar condition "GOOD|DAMAGED"
    varchar condition_notes
    varchar status
    int storage_location_id FK
    timestamptz arrived_at
    int received_by_id FK
    timestamptz ready_at
    timestamptz closed_at
    varchar notes
    int version
  }
  package_status_history {
    int id PK
    int package_id FK
    varchar from_status
    varchar to_status
    int changed_by_id FK
    varchar reason
    timestamptz created_at
  }
  pickup_tokens {
    int id PK
    int package_id FK
    int learner_id FK
    varchar code_hash "HMAC-SHA256"
    varchar salt
    timestamptz expires_at
    timestamptz used_at
    timestamptz revoked_at
    int failed_attempts
  }
  pickup_records {
    int id PK
    int package_id FK,UK
    int token_id FK,UK
    int learner_id FK
    int handed_over_by_id FK
    varchar storage_location_code
    timestamptz collected_at
  }
  notifications {
    int id PK
    int user_id FK
    int package_id FK
    varchar channel "IN_APP|EMAIL"
    varchar title
    varchar message
    varchar delivery_status "PENDING|SENT|FAILED"
    int attempts
    varchar last_error
    timestamptz sent_at
    timestamptz read_at
  }
  incidents {
    int id PK
    int package_id FK
    varchar type
    varchar status "OPEN|RESOLVED"
    text description
    int reported_by_id FK
    int resolved_by_id FK
    text resolution_note
    timestamptz created_at
    timestamptz resolved_at
  }
  audit_logs {
    int id PK
    int actor_id FK
    varchar action "e.g. pickup.completed"
    varchar entity_type
    varchar entity_id
    json details
    timestamptz created_at
  }
  idempotency_keys {
    int id PK
    int user_id FK
    varchar scope
    varchar key
    varchar request_hash
    int resource_id
    timestamptz created_at
  }
```

## 4.2 Tables and why each exists

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | Everyone who signs in. Role is a column, not a separate table, because the three roles share all attributes. | Referenced by most tables |
| `storage_locations` | Shelves/bays at Gate No. 2 with capacity and the largest size they hold. | `packages.storage_location_id` (0..1 per package) |
| `packages` | One row per physical parcel. Holds current status, condition, recipient (nullable while unidentified) and current shelf. | Many-to-one to users (recipient, receiver) and storage |
| `package_status_history` | Append-only record of every status change with actor and reason. Answers "who changed what, when". | Many-to-one to packages and users |
| `pickup_tokens` | Pickup codes. Only a salted HMAC is stored; one package can have several tokens over time (expired/revoked), and only the latest unused one is valid. | Many-to-one to packages and users |
| `pickup_records` | Proof of handover: who collected, who handed over, when, from which shelf. `UNIQUE(package_id)` and `UNIQUE(token_id)`. | One-to-zero-or-one with packages and tokens |
| `notifications` | In-app inbox rows plus a delivery record per channel. | Many-to-one to users, optional package |
| `incidents` | Damage, unidentified recipient, learner reports, missing packages, operational notes. | Optional package, reporter, resolver |
| `audit_logs` | Security-relevant actions (logins, registrations, rejected duplicates, storage, pickups, failed verifications, user and storage changes). | Optional actor (failed login for unknown ID has none) |
| `idempotency_keys` | Remembers retried POSTs. `UNIQUE(user_id, scope, key)`. | Many-to-one to users |

Normalisation: each fact is stored once. Two deliberate exceptions, both documented in code:
`storage_locations.occupied_count` (enables the atomic capacity check, section 2.7) and
`pickup_records.storage_location_code` (a historical snapshot, because the package's
`storage_location_id` is cleared when the shelf is released).

## 4.3 Constraints and deletion policy

- **No hard deletes**: Packages, users, and audit records are never deleted from MongoDB. Soft deactivation (`is_active = false`) preserves history, pickup proof, and audit integrity.
- **Unique Indexes (enforced by MongoDB)**:
  - `users`: `institutional_id`, `email`
  - `packages`: `internal_code`, `tracking_id` (partial filter where `tracking_id` is a string, allowing multiple null tracking IDs)
  - `storage_locations`: `code`
  - `pickup_records`: `package_id`, `token_id`
  - `idempotency_keys`: `(user_id, scope, key)` compound unique index
- **Guarded Counters**: `storage_locations.occupied_count` is maintained via conditional updates (`occupied_count < capacity`), mathematically preventing overfilling.
- **Enumerations**: Domain enums (`PackageStatus`, `Role`, `PackageSize`, `PackageCondition`, `IncidentStatus`) are validated in Pydantic schemas and serialized as string values in BSON documents.

## 4.4 Indexes (created by `app.infrastructure.database.init_db`)

| Collection | Index Keys | Serves |
|---|---|---|
| `packages` | `tracking_id` (Unique, partial) | Duplicate parcel detection at intake |
| `packages` | `internal_code` (Unique) | Package identification and handover verification |
| `packages` | `(status, arrived_at)` (Compound) | Status filter queues & overdue query |
| `packages` | `recipient_id` | "My Packages" query for learner dashboard |
| `users` | `institutional_id` (Unique), `email` (Unique) | Login authentication and learner search |
| `pickup_records` | `package_id` (Unique), `token_id` (Unique) | Structural prevention of double collection |
| `notifications` | `(user_id, created_at)` (Compound) | Learner in-app inbox sorted newest first |
| `idempotency_keys` | `(user_id, scope, key)` (Compound Unique) | Safe retry for registration and handover |

## 4.5 Timestamps

Every timestamp is stored as a timezone-aware UTC datetime (`app.core.time.utcnow`, `ensure_utc`). The API formats timestamps in ISO 8601 UTC, and the React frontend formats them in the viewer's local campus timezone.

## 4.6 Concurrency and Transaction Boundaries

In standalone MongoDB without multi-document distributed transactions, atomic integrity is guaranteed through:
1. **Atomic single-document writes with preconditions** (`find_one_and_update` with guard criteria).
2. **Database-level unique indexes** rejecting duplicate retries or duplicate collection.
3. **Sequential Unit of Work coordinator** (`MongoUnitOfWork`) that records domain events and publishes them only after operations succeed.

Index initialization is automated at startup via `app.infrastructure.database.init_db()`. Safe to call idempotently on fresh or existing databases.
