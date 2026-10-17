# 9. Testing strategy and results

## 9.1 Strategy

| Level | What it covers | Database | Files |
|---|---|---|---|
| Unit | Pure domain rules: state machine transitions/roles/guards, allocation strategies, pickup-token validation, permissions, overdue rule, tracking-ID normalisation, code hashing, event-bus isolation, rate limiter | none | `tests/unit/` |
| API / integration | Real HTTP requests through FastAPI `TestClient` into services, repositories and the database: auth, RBAC, data isolation, intake, duplicates, storage, pickup, idempotency, incidents, reports, notifications | isolated test DB | `tests/api/` |
| Concurrency | Threads with separate Units of Work racing for the same pickup / last shelf slot | isolated test DB | `test_concurrent_*` |
| Failure injection | A repository method is monkey-patched to raise mid-transaction; a notification channel that always fails | isolated test DB | `tests/api/test_reliability.py` |
| Migration | `alembic upgrade head` then `downgrade base` on a fresh database; all ORM tables must exist | fresh DB | `tests/test_migrations.py` |
| Frontend | Strict TypeScript type-check and production build (`npm run build`) | – | `frontend/` |

**Isolation.** `tests/conftest.py` sets `DATABASE_URL` to a temporary SQLite file (or `TEST_DATABASE_URL`) *before* the app is imported, uses `BCRYPT_ROUNDS=4` for speed, and drops/recreates every table before each test. No test touches development data.

**Fixtures.** `users` (admin, two security staff, two learners), `locations` (small cap 2, medium cap 2, large cap 1), `h` (auth headers per user), helpers `register`, `make_ready`, `request_code`.

## 9.2 How to run

```bash
cd backend && source .venv/bin/activate
pytest                       # SQLite
TEST_DATABASE_URL=postgresql+psycopg://campus:campus@localhost:5432/campus_delivery_test pytest
pytest -k concurrent -v       # just the race tests
```

## 9.3 Recorded results (clean setup, fresh virtualenv and node_modules)

Environment: Python 3.12.3, FastAPI 0.115.6, SQLAlchemy 2.0.36, Pydantic 2.10.3, Alembic 1.14.0, PostgreSQL 16.15, Node 22.

| Run | Result |
|---|---|
| Backend suite on SQLite | 74 passed in 6.18s |
| Backend suite on PostgreSQL 16 | 74 passed in 11.65s |
| Concurrency tests repeated (8× PostgreSQL, 5× SQLite) | all passed |
| `alembic upgrade head` + `python -m app.seed` | succeeded on PostgreSQL and SQLite |
| Frontend `npm ci && npm run build` | succeeded (strict TypeScript, 0 errors) |

## 9.4 Test list (SQLite run)

**`tests/api/test_auth_and_access.py`** (12 tests)

- ✅ `test_login_returns_token_and_profile`
- ✅ `test_login_by_email_works`
- ✅ `test_wrong_password_is_rejected_without_detail`
- ✅ `test_repeated_failed_logins_are_rate_limited`
- ✅ `test_requests_without_or_with_bad_token_are_rejected`
- ✅ `test_deactivated_user_loses_access_immediately`
- ✅ `test_learner_sees_only_their_own_packages`
- ✅ `test_learner_view_hides_staff_only_fields`
- ✅ `test_learner_cannot_perform_staff_operations`
- ✅ `test_security_cannot_perform_admin_operations`
- ✅ `test_admin_manages_users`
- ✅ `test_security_can_search_learners`

**`tests/api/test_intake_and_storage.py`** (12 tests)

- ✅ `test_register_and_store_package`
- ✅ `test_missing_and_malformed_fields_return_field_errors`
- ✅ `test_duplicate_tracking_id_is_rejected_and_audited`
- ✅ `test_invalid_learner_id_is_rejected_with_guidance`
- ✅ `test_unidentified_package_enters_workflow_and_can_be_identified`
- ✅ `test_damaged_package_is_held_and_incident_opened`
- ✅ `test_idempotent_registration_replays_instead_of_duplicating`
- ✅ `test_full_location_rejects_additional_allocation`
- ✅ `test_unavailable_location_and_size_mismatch_are_rejected`
- ✅ `test_capacity_cannot_drop_below_occupancy`
- ✅ `test_moving_storage_releases_the_old_slot`
- ✅ `test_concurrent_allocation_never_exceeds_capacity`

**`tests/api/test_pickup.py`** (11 tests)

- ✅ `test_full_pickup_flow_releases_storage_and_notifies`
- ✅ `test_pickup_cannot_be_requested_before_ready`
- ✅ `test_learner_cannot_request_pickup_for_someone_elses_package`
- ✅ `test_wrong_code_and_wrong_learner_are_rejected_and_counted`
- ✅ `test_code_locks_after_too_many_wrong_attempts`
- ✅ `test_expired_code_is_rejected_and_a_new_code_works`
- ✅ `test_requesting_again_revokes_the_previous_code`
- ✅ `test_reused_code_and_already_collected_package_are_rejected`
- ✅ `test_network_retry_of_handover_is_replayed`
- ✅ `test_shift_change_does_not_block_the_workflow`
- ✅ `test_concurrent_handover_results_in_exactly_one_collection`

**`tests/api/test_reliability.py`** (9 tests)

- ✅ `test_failure_halfway_through_handover_rolls_everything_back`
- ✅ `test_notification_failure_does_not_undo_the_package_update`
- ✅ `test_learner_notifications_can_be_marked_read`
- ✅ `test_overdue_packages_are_flagged_and_filterable`
- ✅ `test_return_to_courier_flow_releases_storage`
- ✅ `test_dedicated_transitions_cannot_be_forced_through_generic_endpoint`
- ✅ `test_incidents_escalate_and_resolve`
- ✅ `test_dashboard_and_daily_report_reflect_database`
- ✅ `test_search_filter_and_pagination`

**`tests/test_migrations.py`** (1 tests)

- ✅ `test_upgrade_and_downgrade_on_fresh_database`

**`tests/unit/test_allocation.py`** (5 tests)

- ✅ `test_first_available_uses_code_order_and_skips_full_and_inactive`
- ✅ `test_suitable_size_prefers_the_tightest_fitting_class`
- ✅ `test_large_package_only_fits_large_locations`
- ✅ `test_ties_go_to_the_location_with_more_free_slots`
- ✅ `test_no_candidate_returns_empty_list`

**`tests/unit/test_rules.py`** (14 tests)

- ✅ `test_valid_token_passes`
- ✅ `test_unusable_tokens_are_rejected_with_specific_codes[None-PICKUP_CODE_NOT_ISSUED]`
- ✅ `test_unusable_tokens_are_rejected_with_specific_codes[state1-PICKUP_CODE_USED]`
- ✅ `test_unusable_tokens_are_rejected_with_specific_codes[state2-PICKUP_CODE_REVOKED]`
- ✅ `test_unusable_tokens_are_rejected_with_specific_codes[state3-PICKUP_CODE_LOCKED]`
- ✅ `test_unusable_tokens_are_rejected_with_specific_codes[state4-PICKUP_CODE_EXPIRED]`
- ✅ `test_unusable_tokens_are_rejected_with_specific_codes[state5-PICKUP_WRONG_RECIPIENT]`
- ✅ `test_pickup_code_is_six_digits_and_only_hash_matches`
- ✅ `test_learner_can_only_view_own_packages`
- ✅ `test_role_permission_boundaries`
- ✅ `test_overdue_is_derived_from_arrival_and_status`
- ✅ `test_tracking_ids_are_normalised_before_duplicate_check`
- ✅ `test_event_bus_isolates_failing_subscribers`
- ✅ `test_rate_limiter_blocks_after_max_failures`

**`tests/unit/test_state_machine.py`** (10 tests)

- ✅ `test_happy_path_is_allowed_for_the_right_roles`
- ✅ `test_skipping_steps_is_rejected`
- ✅ `test_collected_package_can_never_become_ready_again`
- ✅ `test_terminal_states_have_no_exits[COLLECTED]`
- ✅ `test_terminal_states_have_no_exits[LOST]`
- ✅ `test_terminal_states_have_no_exits[RETURNED]`
- ✅ `test_wrong_role_is_rejected`
- ✅ `test_guards_enforce_preconditions`
- ✅ `test_available_actions_respect_role_and_guards`
- ✅ `test_every_status_is_reachable_and_table_has_no_duplicates`

## 9.5 Not covered by automated tests

- Frontend behaviour (no component or end-to-end tests yet; see limitations).
- Docker Compose start-up.
- Load/performance testing.
