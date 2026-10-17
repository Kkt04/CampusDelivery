# 1. Problem statement, objectives and requirements

## 1.1 Problem statement

Receiving and managing deliveries on campus takes time for learners, security staff and the
operations team. Learners wait or coordinate manually to collect packages. Security staff at
Gate No. 2 must manage, verify, store and hand over a large number of deliveries, usually with
paper registers. Nobody has a reliable picture of what is on the shelves, what is overdue, or
who handed what to whom.

The Campus Delivery Management System (CDMS) is a centralised application that digitises the
complete lifecycle of a package, from arrival at Gate No. 2 to a verified handover to its
intended recipient, making tracking, verification, storage, notification and pickup organised,
secure and auditable.

## 1.2 Objectives

1. Record every incoming package with courier, tracking ID, recipient, arrival time, condition and receiving staff member.
2. Never lose or silently drop a delivery: duplicates are rejected with a logged reason; unknown recipients enter an explicit workflow.
3. Track shelf locations and their capacity so packages are never assigned to a full or closed location.
4. Tell learners when a package arrives and when it is ready, inside the app.
5. Hand packages over only to the right learner, using a secure, short-lived, single-use code plus an ID check.
6. Make double collection impossible, even under concurrent requests or network retries.
7. Give operations live statistics, exception queues (overdue, unidentified, damaged) and a full audit trail.

## 1.3 Final MVP scope

**In scope:** authentication and three roles; package registration with validation and duplicate detection;
unidentified-recipient and damaged-on-arrival workflows; storage locations with capacity and two
allocation strategies; explicit lifecycle state machine with history; learner dashboard, package
details, pickup code, history and notifications; security dashboard, registration, incoming list,
storage assignment, pickup verification and handover, incident reporting; operations dashboard,
package search, exception queues, storage management, user management, incident review, audit log and
daily report; idempotent retries; in-app notifications with a development email channel; automated tests.

**Out of scope for M1 (see `10-limitations.md`):** real email/SMS providers, barcode/QR scanning,
photo upload of damage, multiple gates, background job scheduler, password reset by email, refresh tokens.

## 1.4 Assumptions

| # | Assumption |
|---|---|
| A1 | There is one physical intake point, Gate No. 2. Storage locations are shelves and bays there. |
| A2 | Every learner and staff member has a unique institutional ID (e.g. `LRN-1001`, `SEC-001`) and a campus email. |
| A3 | Accounts are created by operations admins; there is no self-registration. |
| A4 | A courier tracking ID identifies one shipment. Within CDMS a normalised tracking ID (spaces removed, upper-case) can be registered once. Packages without a tracking ID are allowed. |
| A5 | Security confirms identity by checking the learner's ID card, then entering the learner ID and the 6-digit code. |
| A6 | A package is overdue when it has waited more than `COLLECTION_DEADLINE_DAYS` (default 5) days since arrival while still awaiting collection. |
| A7 | Packages are never deleted; terminal states (collected, returned, lost) preserve history. |
| A8 | Notifications are in-app for M1. "Email" is a development channel that writes to the server log. |

## 1.5 Functional requirements

| ID | Requirement | Role |
|---|---|---|
| FR-01 | Sign in with institutional ID or email and password; sign out | All |
| FR-02 | Every API operation is authorised on the server by role permissions | All |
| FR-03 | Register a package with courier, tracking ID, recipient, arrival time, size, condition and notes; the receiving staff member is recorded automatically | Security, Admin |
| FR-04 | Validate required fields and formats; reject arrival times in the future | System |
| FR-05 | Reject a duplicate tracking ID with a reference to the existing package, and log the attempt | System |
| FR-06 | Register a package without a known recipient into the UNIDENTIFIED workflow; open an incident automatically | Security |
| FR-07 | Register a damaged package into the DAMAGED hold; open an incident automatically | Security |
| FR-08 | Search learners by institutional ID, name, email or phone | Security, Admin |
| FR-09 | Identify the recipient of an unidentified package | Security, Admin |
| FR-10 | Assign or move a package to a storage location, manually or automatically using the configured strategy; reject full, closed or too-small locations | Security, Admin |
| FR-11 | Mark a stored package ready for pickup and notify the learner | Security, Admin |
| FR-12 | Learners view only their own packages, with status labels, timestamps and (when ready) the shelf | Learner |
| FR-13 | Learner requests pickup and receives a one-time 6-digit code valid for 30 minutes; a new request replaces the old code | Learner |
| FR-14 | Security verifies package code + learner ID + pickup code, then completes the handover | Security |
| FR-15 | Handover records staff member and time, releases shelf capacity, sets status COLLECTED and notifies the learner | System |
| FR-16 | Learners view their collection history and notifications, and mark notifications read | Learner |
| FR-17 | Learners report an issue about their own package | Learner |
| FR-18 | Staff record incidents (damage, unidentified, missing, operational), optionally escalating the package to UNDER_INVESTIGATION | Security, Admin |
| FR-19 | Admins resolve incidents with a note | Admin |
| FR-20 | Lifecycle changes follow the documented state machine only; each change writes status history and an audit entry | System |
| FR-21 | Admins request returns to courier and mark packages lost; security completes returns | Admin, Security |
| FR-22 | Operations dashboard shows counts by status, overdue, unidentified, damaged, today's activity, storage use, open incidents and failed notifications, all from live data | Admin (Security sees a gate subset) |
| FR-23 | Search, filter (status, condition, overdue, date range) and paginate packages | Staff |
| FR-24 | Daily report of packages received vs collected for a date range (≤ 92 days) | Admin |
| FR-25 | Manage storage locations: create, change capacity (not below occupancy), close/reopen | Admin |
| FR-26 | Manage users: create, deactivate/reactivate (effective immediately), reset password | Admin |
| FR-27 | View and filter the audit log | Admin |
| FR-28 | Retry failed notifications | Admin |

## 1.6 Non-functional requirements

| ID | Category | Requirement and how it is met |
|---|---|---|
| NFR-01 | Integrity | Each use case runs in one database transaction (Unit of Work); a failure leaves no partial update. |
| NFR-02 | Concurrency | Row locks, conditional updates and unique constraints prevent double collection and over-allocation. |
| NFR-03 | Reliability | `Idempotency-Key` makes registration and handover safe to retry; notification failure never undoes a committed change. |
| NFR-04 | Security | bcrypt passwords; signed short-lived JWT; hashed, expiring, single-use, attempt-limited pickup codes; RBAC on every route; login rate limit; secrets from environment; no stack traces in responses. |
| NFR-05 | Auditability | Sensitive operations write `audit_logs` in the same transaction as the change. |
| NFR-06 | Privacy | Learners see only their packages; other learners' package IDs return 404. Staff names and notes are hidden from learners. No real learner data in seed files. |
| NFR-07 | Maintainability | Layered modules, small services, type hints, protocols for swappable parts, 74 automated tests. |
| NFR-08 | Usability | Responsive layout (mobile to desktop), consistent loading/empty/error states, accessible labels, visible keyboard focus, reduced-motion respected. |
| NFR-09 | Portability | Runs on PostgreSQL (primary) and SQLite (development) from the same migrations; Docker Compose for one-command start. |
| NFR-10 | Performance | Indexes on tracking ID, recipient, status, arrival date (plus status+arrival composite) and audit timestamps; paginated lists. |
| NFR-11 | Time | All timestamps stored as timezone-aware UTC; the browser formats them in local time. |
