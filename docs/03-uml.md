# 3. UML diagrams

## 3.1 Use-case diagram

Mermaid has no native use-case diagram, so actors are shown on the left and use cases (rounded) are grouped by role.

```mermaid
flowchart LR
  L(["👤 Learner"])
  S(["👤 Security staff"])
  A(["👤 Operations admin"])

  subgraph CDMS["Campus Delivery Management System"]
    UC1([Sign in / sign out])
    UC2([View own packages and details])
    UC3([Receive in-app notifications])
    UC4([Request pickup code])
    UC5([View pickup history])
    UC6([Report a package issue])

    UC7([Register incoming package])
    UC8([Search learner])
    UC9([Identify unknown recipient])
    UC10([Assign / move storage])
    UC11([Mark ready for pickup])
    UC12([Verify pickup code])
    UC13([Complete handover])
    UC14([Record incident])
    UC15([Hand back to courier])

    UC16([View statistics and daily report])
    UC17([Search and filter packages])
    UC18([Review overdue / unidentified / damaged])
    UC19([Manage storage locations])
    UC20([Manage users])
    UC21([Resolve incidents])
    UC22([Request return / mark lost])
    UC23([View audit log])
    UC24([Retry failed notifications])
  end

  L --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6
  S --- UC1 & UC7 & UC8 & UC9 & UC10 & UC11 & UC12 & UC13 & UC14 & UC15 & UC17
  A --- UC1 & UC16 & UC17 & UC18 & UC19 & UC20 & UC21 & UC22 & UC23 & UC24 & UC9 & UC10
  UC13 -. includes .-> UC12
  UC7 -. includes .-> UC8
```

## 3.2 Class diagram (main domain and service classes)

```mermaid
classDiagram
  direction LR

  class User {
    +int id
    +str institutional_id
    +str full_name
    +str email
    +Role role
    +bool is_active
  }
  class Package {
    +int id
    +str internal_code
    +str courier_name
    +str? tracking_id
    +PackageSize size
    +PackageCondition condition
    +PackageStatus status
    +datetime arrived_at
    +datetime? ready_at
    +datetime? closed_at
    +int version
  }
  class StorageLocation {
    +str code
    +int capacity
    +int occupied_count
    +PackageSize max_package_size
    +bool is_active
  }
  class PickupToken {
    +str code_hash
    +str salt
    +datetime expires_at
    +datetime? used_at
    +datetime? revoked_at
    +int failed_attempts
  }
  class PickupRecord { +datetime collected_at +str? storage_location_code }
  class PackageStatusHistory { +PackageStatus? from_status +PackageStatus to_status +str? reason }
  class Notification { +NotificationChannelType channel +NotificationStatus delivery_status +int attempts +datetime? read_at }
  class Incident { +IncidentType type +IncidentStatus status +str description }
  class AuditLog { +str action +str entity_type +dict details }

  Package "*" --> "0..1" User : recipient
  Package "*" --> "1" User : received_by
  Package "*" --> "0..1" StorageLocation : stored at
  Package "1" *-- "*" PackageStatusHistory
  Package "1" o-- "*" PickupToken
  Package "1" -- "0..1" PickupRecord
  Package "1" o-- "*" Incident
  User "1" o-- "*" Notification

  class PackageStateMachine {
    +check(source, target, role, ctx) Transition
    +available(source, role, ctx) list~Transition~
    +find(source, target) Transition?
  }
  class Transition {
    +PackageStatus source
    +PackageStatus target
    +frozenset~Role~ roles
    +str action
    +Guard? guard
  }
  PackageStateMachine "1" o-- "*" Transition

  class StorageAllocationStrategy {
    <<interface>>
    +rank(candidates, size) list~StorageCandidate~
  }
  class FirstAvailableStrategy
  class SuitableSizeStrategy
  StorageAllocationStrategy <|.. FirstAvailableStrategy
  StorageAllocationStrategy <|.. SuitableSizeStrategy

  class NotificationChannel {
    <<interface>>
    +send(recipient, title, message)
  }
  class InAppChannel
  class ConsoleEmailChannel
  NotificationChannel <|.. InAppChannel
  NotificationChannel <|.. ConsoleEmailChannel
  class NotificationChannelFactory { +register(name, builder) +create(name) }
  NotificationChannelFactory ..> NotificationChannel : creates

  class UnitOfWork {
    +packages
    +storage
    +tokens
    +pickups
    +audit
    +record_event(e)
    +commit()
    +rollback()
  }
  class EventBus { +subscribe(type, handler) +publish(event) }
  class PackageTransitioner { +apply(package, target, actor, reason) }
  class PackageIntakeService { +register(...) +identify_recipient(...) }
  class StorageAllocationService { +assign(package_id, actor, location_id, mark_ready) }
  class PickupService { +request_pickup() +verify() +complete() }
  class NotificationDispatcher { +handle(event) +retry(session) }

  PackageTransitioner --> PackageStateMachine
  PackageTransitioner --> UnitOfWork
  PackageIntakeService --> PackageTransitioner
  StorageAllocationService --> PackageTransitioner
  StorageAllocationService --> StorageAllocationStrategy
  PickupService --> PackageTransitioner
  UnitOfWork --> EventBus : publishes after commit
  EventBus --> NotificationDispatcher : PackageStatusChanged
  NotificationDispatcher --> NotificationChannel
```

**Why no `Learner`/`SecurityStaff`/`Admin` subclasses?** The three roles have identical data and
differ only in permissions. A single `User` with a `role` value plus a permission table
(`domain/permissions.py`) is simpler, avoids type changes when a person's role changes, and avoids
subclasses that would override nothing (which would be inheritance only to "show OOP").
Inheritance is used where real substitutable behaviour exists: strategies and channels (via protocols),
exception hierarchy (`AppError → ConflictError → StorageFullError`), and `TimestampMixin`.

## 3.3 Sequence diagram: request code and complete handover

```mermaid
sequenceDiagram
  actor L as Learner
  actor S as Security
  participant API as FastAPI route
  participant PS as PickupService
  participant DB as PostgreSQL
  participant Bus as EventBus
  participant N as NotificationDispatcher

  L->>API: POST /packages/{id}/pickup-request
  API->>PS: request_pickup(id, learner)
  PS->>DB: SELECT package FOR UPDATE (must be learner's, READY_FOR_PICKUP)
  PS->>DB: UPDATE status READY→PICKUP_REQUESTED (conditional), revoke old tokens
  PS->>DB: INSERT pickup_token(hash(salt+code), expires_at), audit
  PS->>DB: COMMIT
  API-->>L: 201 {code: "482913", expires_at}  (shown once)

  S->>API: POST /pickups/complete {package_code, learner_id, code} + Idempotency-Key
  API->>PS: complete(...)
  PS->>DB: SELECT package FOR UPDATE
  PS->>DB: idempotency key already used? (replay if so)
  PS->>PS: ensure_token_usable + learner ID match + constant-time hash compare
  alt wrong / expired / locked
    PS->>DB: failed_attempts+1, audit, COMMIT
    API-->>S: 400 PICKUP_CODE_*
  else valid
    PS->>DB: UPDATE token SET used_at WHERE used_at IS NULL (1 row)
    PS->>DB: UPDATE package status→COLLECTED WHERE status=PICKUP_REQUESTED (1 row)
    PS->>DB: release storage slot, INSERT pickup_record (UNIQUE package_id), history, audit, idempotency
    PS->>DB: COMMIT
    PS->>Bus: publish PackageStatusChanged(COLLECTED)
    Bus->>N: handle(event)
    N->>DB: INSERT notification PENDING, COMMIT, send, mark SENT/FAILED
    API-->>S: 201 pickup record
  end
```
