# 10. Limitations and future improvements

## Known limitations of the M1 version

| Area | Limitation | Impact | Planned improvement |
|---|---|---|---|
| Notifications | Only in-app is real. "Email" logs to the server console. Events are dispatched in-process after commit, so a crash between commit and dispatch loses that notification. | Low for M1 (in-app inbox is the source of truth for learners) | Transactional outbox table + background worker; real email/SMS providers behind the existing `NotificationChannel` protocol |
| Login rate limit | In-memory per process; resets on restart; not shared between workers. | Weaker brute-force protection with several workers | Store attempts in the database or a shared cache |
| Tokens | Access token only (60 min), kept in `sessionStorage`; no refresh token or server-side revocation list (deactivation is still immediate because the user is reloaded on every request). | Users sign in again after an hour; XSS could read the token | HttpOnly secure cookie with CSRF protection, refresh tokens |
| Pickup codes | 6 digits; protected by expiry (30 min), 5-attempt lock, package binding and the ID-card check. | Acceptable for an in-person handover | Optional QR code on the learner's screen scanned at the gate |
| Overdue follow-up | Overdue is flagged and listed, but no automatic reminder is sent. | Operations must act manually | Scheduled reminder job (see live-coding task 5) |
| Reports | Daily report groups timestamps in Python; days are UTC days. | Fine at campus scale; day boundary is UTC | SQL `date_trunc` in campus time zone, materialised summaries |
| Scanning | Package codes are typed, not scanned. | Slower intake | Barcode/QR label printing and scanning |
| Evidence | No photo upload for damage. | Text notes only | Object storage for images |
| Password lifecycle | No self-service reset or forced change of temporary passwords. | Admin resets passwords | Email reset flow, "must change password" flag |
| Multi-gate | One intake point assumed. | – | `site`/`gate` entity on locations, packages and staff |
| Frontend tests | Frontend is verified by strict TypeScript and build only, not by automated UI tests. | UI regressions caught manually | Vitest + React Testing Library, Playwright end-to-end tests |
| Docker | Compose files provided but not executed in the build environment. | Verify once on your machine | – |

## Verified versus not verified

Verified by running: migrations on PostgreSQL 16 and SQLite, seed script, 74 backend tests on both
databases (concurrency tests repeated 13 times), live API smoke test, frontend type-check and production
build, frontend dev server proxying real API calls. Not verified: Docker Compose start-up, and the visual
appearance of the UI in a browser (no browser was available in the build environment).
