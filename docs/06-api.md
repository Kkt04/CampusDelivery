# 6. API endpoint documentation

Base path `/api/v1`. Interactive docs: `http://localhost:8000/docs` (Swagger) and `/redoc`; the machine-readable schema is `/openapi.json`.

This table is generated from the running application's routes and their permission dependencies, so the roles shown are exactly what the server enforces.

## Conventions

- **Auth:** `Authorization: Bearer <access_token>` from `POST /auth/login`.
- **Errors:** `{"error": {"code", "message", "details", "request_id"}}`. 401 not signed in / inactive, 403 role lacks permission, 404 not found or not yours, 409 conflict (invalid transition, duplicate, full storage, already collected), 422 validation (`details` lists fields), 429 rate limited, 500 internal (no details).
- **Idempotency:** `POST /packages` and `POST /pickups/complete` accept `Idempotency-Key` (8–80 chars). A replay returns `200` with header `Idempotent-Replayed: true`.
- **Pagination:** list endpoints take `page` and `page_size` and return `{items, total, page, page_size}`.
- **Times** are ISO 8601 UTC.

## Endpoints

| Area | Method | Path | Purpose | Who may call |
|---|---|---|---|---|
| Authentication | POST | `/api/v1/auth/login` | Sign in with institutional ID or email | Public |
| Authentication | GET | `/api/v1/auth/me` | Current user profile | Any signed-in user (scoped in code) |
| Packages | POST | `/api/v1/packages` | Register an incoming package | Admin, Security (`package:register`) |
| Packages | GET | `/api/v1/packages` | Search packages (learners: own packages only) | Any signed-in user (scoped in code) |
| Packages | GET | `/api/v1/packages/{package_id}` | Package details (learners: own only, else 404) | Any signed-in user (scoped in code) |
| Packages | GET | `/api/v1/packages/{package_id}/history` | Status history (learners: own, without staff names) | Any signed-in user (scoped in code) |
| Packages | POST | `/api/v1/packages/{package_id}/storage` | Assign or move storage | Admin, Security (`package:manage`) |
| Packages | POST | `/api/v1/packages/{package_id}/recipient` | Identify an unknown recipient | Admin, Security (`package:manage`) |
| Packages | POST | `/api/v1/packages/{package_id}/transitions` | Apply a lifecycle transition | Admin, Security (`package:manage`) |
| Pickup | POST | `/api/v1/packages/{package_id}/pickup-request` | Learner: request pickup and receive a one-time code | Learner (`pickup:request`) |
| Pickup | POST | `/api/v1/pickups/verify` | Security: check a learner's code without handing over | Security (`pickup:handover`) |
| Pickup | POST | `/api/v1/pickups/complete` | Security: verify the code and hand the package over (idempotent with Idempotency-Key) | Security (`pickup:handover`) |
| Pickup | GET | `/api/v1/pickups` | Collection history (learners: own; staff: all) | Any signed-in user (scoped in code) |
| Storage | GET | `/api/v1/storage-locations` | List storage locations with occupancy | Admin, Security (`storage:view`) |
| Storage | POST | `/api/v1/storage-locations` | Create a storage location | Admin (`storage:manage`) |
| Storage | PATCH | `/api/v1/storage-locations/{location_id}` | Change capacity/size/description, close or reopen | Admin (`storage:manage`) |
| Users | GET | `/api/v1/users/learners` | Security: find a learner by institutional ID, name, email or phone | Admin, Security (`learner:search`) |
| Users | GET | `/api/v1/users` | Search and list accounts | Admin (`user:manage`) |
| Users | POST | `/api/v1/users` | Create an account | Admin (`user:manage`) |
| Users | PATCH | `/api/v1/users/{user_id}` | Rename, change phone, (de)activate, reset password | Admin (`user:manage`) |
| Notifications | GET | `/api/v1/notifications` | My in-app notifications | Any signed-in user (scoped in code) |
| Notifications | GET | `/api/v1/notifications/unread-count` | Unread in-app notification count | Any signed-in user (scoped in code) |
| Notifications | POST | `/api/v1/notifications/{notification_id}/read` | Mark one notification read (own only) | Any signed-in user (scoped in code) |
| Notifications | POST | `/api/v1/notifications/read-all` | Mark all own notifications read | Any signed-in user (scoped in code) |
| Notifications | POST | `/api/v1/notifications/retry-failed` | Admin: retry FAILED or stuck PENDING notifications | Admin (`notification:admin`) |
| Incidents | POST | `/api/v1/incidents` | Report an incident (learners: issue about their own package) | Admin, Learner, Security (`incident:report`) |
| Incidents | GET | `/api/v1/incidents` | List incidents (learners: only their own reports) | Any signed-in user (scoped in code) |
| Incidents | POST | `/api/v1/incidents/{incident_id}/resolve` | Resolve with a note | Admin (`incident:resolve`) |
| Reports & audit | GET | `/api/v1/reports/dashboard` | Live statistics | Admin, Security (`package:view_all`) |
| Reports & audit | GET | `/api/v1/reports/daily` | Received vs collected per day | Admin (`report:view`) |
| Reports & audit | GET | `/api/v1/audit-logs` | Filter the audit log | Admin (`audit:view`) |
| Health | GET | `/api/v1/health` | Liveness check | Public |

## Key request examples

Register a package:
```http
POST /api/v1/packages
Idempotency-Key: 6f0c3c7e-1b7a-4c1e-9a36-0c2f7b1d2e11

{"courier_name": "BlueDart", "tracking_id": "BD7781200345", "recipient_institutional_id": "LRN-1001",
 "size": "SMALL", "condition": "GOOD"}
```
Unknown recipient: omit `recipient_institutional_id` and send `recipient_hint`. Damaged: `"condition": "DAMAGED"` with `condition_notes`.

Assign storage (omit `location_id` to auto-allocate):
```http
POST /api/v1/packages/12/storage

{"location_id": null, "mark_ready": true}
```
Generic transition:
```http
POST /api/v1/packages/12/transitions

{"target_status": "RETURN_REQUESTED", "reason": "Uncollected after deadline"}
```
Handover:
```http
POST /api/v1/pickups/complete
Idempotency-Key: 0d9e…

{"package_code": "PKG-261017-ABCDE", "learner_institutional_id": "LRN-1001", "code": "482913"}
```
Package filters (`GET /packages`): `q`, `status` (repeatable), `condition`, `overdue=true`, `arrived_from`, `arrived_to` (dates), `storage_location_id`, `page`, `page_size`. Learners are always limited to their own packages.
