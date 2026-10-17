# 13. Five live-coding tasks with guidance

Each task is sized for 15–30 minutes. Run `pytest` before and after.

---

## Task 1: Add an SMS notification channel (Open/Closed, Factory)

**Goal.** Learners can also receive SMS (development version logs to console). No service code changes.

**Files.** `backend/app/domain/enums.py`, `backend/app/infrastructure/notifications.py`, `backend/.env`, a new test.

**Steps.**
1. Add `SMS = "SMS"` to `NotificationChannelType`.
2. Create the channel:
   ```python
   class ConsoleSmsChannel:
       channel_type = NotificationChannelType.SMS
       def send(self, recipient, title, message):
           if not recipient.phone:
               raise NotificationDeliveryError("recipient has no phone number")
           logger.info("SMS to=%s body=%r", recipient.phone, f"{title}: {message}")
   ```
3. `NotificationRecipient` has no phone yet: add `phone: str | None` in `domain/interfaces.py` and pass `user.phone` in `NotificationDispatcher.attempt`.
4. Register it: `channel_factory.register("console_sms", ConsoleSmsChannel)`.
5. Enable: `NOTIFICATION_CHANNELS=in_app,console_sms`.
6. Test: set `container.dispatcher.channels = [InAppChannel(), ConsoleSmsChannel()]`, mark a package ready, assert an SMS row exists (FAILED for a learner without a phone, which also demonstrates failure handling).

**What to say.** Only the factory registration and configuration changed; the workflow is closed for modification.

---

## Task 2: Add a "least occupied" allocation strategy (Strategy, Liskov)

**Goal.** Spread packages across shelves by choosing the location with the lowest occupancy percentage.

**Files.** `backend/app/domain/allocation.py`, `backend/app/container.py`, `backend/tests/unit/test_allocation.py`.

**Steps.**
1. Add:
   ```python
   class LeastOccupiedStrategy:
       name = "least_occupied"
       def rank(self, candidates, size):
           return sorted((c for c in candidates if c.accepts(size)),
                         key=lambda c: (c.occupied / c.capacity, c.code))
   ```
2. Register in `ALLOCATION_STRATEGIES` in `container.py`.
3. Unit test with three candidates of different occupancy; also assert it never returns a full or inactive location (the LSP contract shared with the other strategies).
4. Switch with `STORAGE_ALLOCATION_STRATEGY=least_occupied`.

---

## Task 3: Let a learner cancel a pickup request (state machine, service, route, test)

**Goal.** A learner who cannot come today cancels; the code stops working and the package returns to READY_FOR_PICKUP.

**Files.** `domain/state_machine.py`, `services/pickup.py`, `api/routes/pickups.py`, `frontend/src/api/endpoints.ts`, `frontend/src/pages/learner/PickupCodePage.tsx`, `tests/api/test_pickup.py`.

**Steps.**
1. Add a transition: `_t(S.PICKUP_REQUESTED, S.READY_FOR_PICKUP, LEARNER, "cancel_pickup", "Cancel pickup", needs_recipient, dedicated=True)`.
2. In `PickupService` add `cancel_pickup(package_id, learner)`: lock the package, check ownership (404 otherwise), apply the transition, `self._uow.tokens.revoke_active(package.id, utcnow())`, audit `pickup.cancelled`, commit.
3. Route: `POST /packages/{package_id}/pickup-cancel` with `require(Permission.PICKUP_REQUEST)`.
4. Test: request a code, cancel, then `complete` with the old code returns `PICKUP_NOT_REQUESTED`; another learner cancelling gets 404.
5. Frontend: `pickupApi.cancel(id)` and a "Cancel pickup" button on the ticket.

**What to say.** The state machine table changed by one line; every rule about recording history and audit is reused via `PackageTransitioner`.

---

## Task 4: Add a "packages by courier" report (repository, service, route, UI)

**Goal.** Operations sees how many packages each courier delivered in a date range.

**Files.** `repositories/sqlalchemy_repos.py`, `services/reports.py`, `schemas/misc.py`, `api/routes/reports.py`, `frontend/src/api/endpoints.ts`, `frontend/src/pages/ops/OpsDashboard.tsx`.

**Steps.**
1. Repository: `count_by_courier(start, end)` → `select(Package.courier_name, func.count()).where(arrived_at between).group_by(Package.courier_name).order_by(func.count().desc())`.
2. Service method `by_courier(date_from, date_to)` reusing the 92-day validation from `daily`.
3. Schema `CourierCount(courier_name: str, count: int)`; route `GET /reports/couriers` with `require(Permission.REPORT_VIEW)`.
4. Test: register packages from two couriers; assert counts and that security gets 403.
5. Frontend: a card on the operations overview listing couriers with counts.

---

## Task 5: Send overdue reminders (query, events/notifications, idempotency thinking)

**Goal.** An admin presses "Send reminders" and every learner with an overdue package gets one in-app message.

**Files.** `services/notifications.py` (or a new `services/reminders.py`), `api/routes/reports.py`, `repositories/sqlalchemy_repos.py`, tests.

**Steps.**
1. Query overdue packages with `uow.packages.search(PackageFilters(overdue_only=True, overdue_deadline_days=settings.collection_deadline_days), page=1, page_size=500, now=utcnow())`.
2. For each package with a recipient, create a `Notification` (IN_APP, title "Please collect your package", status PENDING), then send it through `container.dispatcher.attempt(...)` so failures are recorded the same way.
3. Avoid spamming: skip a package if it already has a reminder created today (query `notifications` by `package_id`, title and `created_at >= start of today`). Explain this is a business-level idempotency rule.
4. Route `POST /reports/overdue-reminders` with `require(Permission.NOTIFICATION_ADMIN)`; return `{"reminded": n, "skipped": m}`; audit `notification.overdue_reminders`.
5. Test: backdate a package's `arrived_at` by 9 days, call twice, assert one reminder.

**Talking point.** In production this would run on a schedule (cron or a worker), which is why the logic belongs in a service rather than the route.
