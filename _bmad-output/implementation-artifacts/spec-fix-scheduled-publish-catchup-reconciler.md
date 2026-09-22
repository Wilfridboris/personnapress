---
title: 'Self-healing catch-up for missed scheduled publishes'
type: 'bugfix'
created: '2026-09-22'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '3bd77a3565223e8e74f22268a54c9d14ad25578e'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Scheduled posts silently vanish, leaving the campaign stuck at `approved` with a past `scheduled_at` (confirmed: user's missed post "still shows as scheduled"). Two independent root causes: (1) **Deploy wipes the job store.** APScheduler persists each scheduled job in the `apscheduler_jobs` table, but that table is not in `SQLModel.metadata` and `alembic/env.py` has no autogenerate filter, so `alembic revision --autogenerate` keeps emitting `op.drop_table('apscheduler_jobs')` (already shipped in the 2026-08-09 and 2026-09-08 migrations). Running `alembic upgrade head` on deploy drops the table and every pending scheduled job with it. (2) **Misfire beyond grace.** A one-shot `DateTrigger` with `misfire_grace_time=3600` is discarded if the server is down when its time passes and recovers >1h later. The prior fix (`spec-fix-scheduled-publish-misfire`, 2026-08-17) only widened the grace window; it addresses neither cause durably.

**Approach:** Two layers. (Source) Exclude `apscheduler_jobs` from Alembic autogenerate via an `include_name` filter in `env.py`, so future deploys stop dropping the job store. (Safety net) Add a periodic self-healing catch-up worker (also runs once at startup) that finds `approved` campaigns whose `scheduled_at` has passed but whose APScheduler job is gone (orphaned — from a table drop, a misfire, or any loss), atomically claims each, and dispatches the correct existing worker: `run_publish` for social schedules and `run_publish_headless` for headless/blog schedules. Coordinate with APScheduler so a job still within its grace window is left alone — no double publishing. Emit a log + Sentry message whenever it recovers or fails a post (including how late each was), so silent misses become visible.

## Boundaries & Constraints

**Always:** Select due rows (`approved`, `scheduled_at IS NOT NULL`, `scheduled_at <= now - 60s` buffer to avoid racing an on-time fire) with `with_for_update(skip_locked=True)`. Classify each due campaign and act:
- **Social** — a `scheduled_publish` job row is still `status="scheduled"` (via `get_scheduled_job`): dispatch `run_publish(job_id, campaign_id, [])` ONLY IF `scheduler.get_job(str(job_id))` returns `None`. If a live APScheduler job still exists, skip (within grace).
- **Headless** — no `scheduled_publish` job row, but a hidden article exists for the campaign (`get_article_by_campaign_id`, `status == ArticleStatus.hidden`): dispatch `run_publish_headless(str(campaign_id))` ONLY IF `scheduler.get_job(f"headless_{campaign_id}")` returns `None`. If live, skip.
- **Already fulfilled** — no scheduled job and the article is already `published`: clear `scheduled_at` (housekeeping so it stops being re-scanned) and do not dispatch.
- **Otherwise** — leave untouched and log.

Claim each dispatched campaign atomically by setting `scheduled_at = None` before the single commit, so no other worker/tick re-picks it. `run_publish_headless` is already idempotent (it no-ops if the article is already published), and `run_publish` republish skip-logic protects social — so a stray double-fire is harmless. Store/compare times as naive UTC (`utcnow()`), matching the existing `scheduled_at` convention. Observability is primarily a `logger.warning` (visible in `journalctl` — Sentry is NOT configured yet) summarizing recoveries (count + per-post lateness) and each per-campaign dispatch failure; ALSO call `sentry_sdk.capture_message(...)` as a best-effort additive that is a harmless no-op until `SENTRY_DSN` is set. Recover regardless of how late (no staleness cap) but include the lateness in the log. The worker must never raise out of a per-campaign failure — log/continue.

For the Alembic filter: put the predicate in an importable helper (not inline in `env.py`, whose module body runs migrations on import) so it can be unit-tested; wire it into BOTH `context.configure(...)` calls (offline and online) via `include_name`. It must exclude only `apscheduler_jobs` (type `table`) and pass everything else through unchanged.

**Ask First:** None.

**Never:** Do not change `run_publish`'s partial-success/status logic, `dispatch_publish`, the single-channel-failure behavior, or the schedule/reschedule endpoints (those are deferred, separate work). Do not add or edit any migration file, and do not touch the two historical migrations that drop `apscheduler_jobs` (they are past head and will not re-run) — the source fix is autogenerate-only, forward-looking. Do not put `apscheduler_jobs` into `SQLModel.metadata` or disable APScheduler's runtime table creation (the library keeps owning its table). Do not import `scheduler` at module top in the worker (circular import) — import it lazily inside the function, as `routers/roadmaps.py` does.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Social orphaned | `approved`, `scheduled_at` 2h ago, `scheduled_publish` job `scheduled`, `scheduler.get_job` -> None | Claim (`scheduled_at=None`), `run_publish(job_id, campaign_id, [])`; log recovery + lateness | N/A |
| Social within grace | `approved`, `scheduled_at` 2m ago, `scheduler.get_job` -> job present | Skip; leave to APScheduler; `scheduled_at` unchanged | N/A |
| Headless orphaned | `approved`, `scheduled_at` 2h ago, no `scheduled_publish` job, article `hidden`, `scheduler.get_job("headless_<id>")` -> None | Claim, `run_publish_headless(str(campaign_id))`; log recovery + lateness | N/A |
| Headless within grace | Same but `scheduler.get_job("headless_<id>")` -> job present | Skip; `scheduled_at` unchanged | N/A |
| Already fulfilled (housekeeping) | `approved`, past `scheduled_at`, no scheduled job, article already `published` | Clear `scheduled_at`; do not dispatch | N/A |
| In-flight social | `scheduled_publish` job moved to `in_progress` (get_scheduled_job -> None) and no hidden/published article | Skip; log; do not dispatch (no double fire) | N/A |
| Not due / no schedule | `scheduled_at` future or `NULL`, or status != `approved` | Not selected by query | N/A |
| Within buffer | `approved`, `scheduled_at` 20s ago | Not selected (`<= now - 60s` excludes it) | N/A |
| Dispatch throws | a dispatch raises for one campaign | Log + Sentry, continue; remaining claimed campaigns still dispatched | Swallow per-campaign |

</frozen-after-approval>

## Code Map

- `backend/app/scheduler/scheduler.py:10` -- `create_scheduler()`; interval-job registration pattern (`metrics_poll`). Add the catch-up interval job here with an immediate first run.
- `backend/app/workers/cleanup.py:20` -- worker pattern to mirror: `async_session_factory()` session, `with_for_update(skip_locked=True)` batch claim, per-item try/except, `BATCH_LIMIT`.
- `backend/app/workers/publish.py:114` -- `run_publish(job_id, campaign_id, platforms=[])`; opens its own session, sets job in_progress, dispatches, sets campaign published/failed and `scheduled_at=None`. Reuse as-is.
- `backend/app/workers/publish.py:163` -- `run_publish_headless(campaign_id_str)`; flips the campaign's hidden article to published; already idempotent (no-ops if already published). Reuse as-is for headless recovery.
- `backend/app/routers/publishing.py:1816` -- headless schedule endpoint (context): sets `campaign.scheduled_at`, keeps status `approved`, creates a hidden article, registers `run_publish_headless` under APScheduler id `headless_{campaign_id}` (NO `scheduled_publish` job row). This is the discriminator for the headless branch.
- `backend/app/db/repositories/articles.py` -- `get_article_by_campaign_id`; and `ArticleStatus` (hidden/published) in `models.py`. Used to classify headless campaigns.
- `backend/app/workers/cleanup.py:6` -- `import sentry_sdk` + `sentry_sdk.capture_message(...)` pattern to mirror for observability.
- `backend/app/db/repositories/campaigns.py:43` -- repo module (naive-UTC `utcnow`); add the due-campaigns query here.
- `backend/app/db/repositories/jobs.py:84` -- `get_scheduled_job` (returns job only when `status="scheduled"`) and `create_job`; reuse for the claim decision.
- `backend/app/routers/roadmaps.py:302` -- example of the lazy `from app.scheduler.scheduler import scheduler` import inside a function (avoids circular import).
- `backend/app/db/connection.py:15` -- `async_session_factory` for worker sessions.
- `backend/app/routers/publishing.py:1526` -- schedule endpoint (context only): platforms are stored ONLY in APScheduler job args, not the DB, so catch-up cannot recover a specific platform subset -> passes `[]` (all connected). Read-only.
- `backend/alembic/env.py:29` -- `target_metadata = SQLModel.metadata`; `context.configure(...)` in both `do_run_migrations` (online, ~line 46) and `run_migrations_offline` (~line 34). No `include_name`/`include_object` today. Add the filter wiring here.
- `backend/alembic/versions/20260809_1946_4317d2f4b9b7_add_target_word_count_to_campaigns.py:26` and `backend/alembic/versions/20260908_1719_5c08a8909153_add_voice_samples_to_clients.py:25` -- context only (do NOT edit): existing `op.drop_table('apscheduler_jobs')` proving the drift; the filter prevents future recurrences.

## Tasks & Acceptance

**Execution:**
- [ ] `backend/app/db/alembic_filters.py` -- new module exporting `include_name(name, type_, parent_names) -> bool` that returns `False` only for `type_ == "table" and name == "apscheduler_jobs"`, else `True`. Keep it dependency-free so it imports without side effects.
- [ ] `backend/alembic/env.py` -- import `include_name` and pass `include_name=include_name` to `context.configure(...)` in BOTH `do_run_migrations` and `run_migrations_offline`, so autogenerate stops proposing `drop_table('apscheduler_jobs')`.
- [ ] `backend/app/db/repositories/campaigns.py` -- add `get_due_scheduled_campaigns(session, cutoff: datetime, limit: int) -> Sequence[Campaign]` selecting `status == "approved"`, `scheduled_at IS NOT NULL`, `scheduled_at <= cutoff`, `.limit(limit).with_for_update(skip_locked=True)`.
- [ ] `backend/app/workers/publish_catchup.py` -- new `scheduled_publish_catchup()`: lazy-import `scheduler`; `cutoff = utcnow() - timedelta(seconds=60)`; in one `async_session_factory()` session, fetch due campaigns (batch limit e.g. 20) and classify each per the Boundaries rules — social (`get_scheduled_job` + `scheduler.get_job(str(job.id)) is None`), headless (no scheduled job + hidden article via `get_article_by_campaign_id` + `scheduler.get_job(f"headless_{campaign.id}") is None`), already-fulfilled (published article -> clear `scheduled_at`, no dispatch), else leave+log. For claimed campaigns set `scheduled_at=None`/`updated_at=utcnow()` and record `("social", job.id, campaign.id, lateness)` or `("headless", None, campaign.id, lateness)`; commit once; then dispatch each (`run_publish(job_id, campaign_id, [])` or `run_publish_headless(str(campaign_id))`) in a try/except that logs+`sentry_sdk.capture_message` and continues. After the batch, emit one summary log + `sentry_sdk.capture_message` (recovered count + per-post lateness). Never raises.
- [ ] `backend/app/scheduler/scheduler.py` -- import and register `scheduled_publish_catchup` as an `interval` job (every 5 min, `id="scheduled_publish_catchup"`, `replace_existing=True`, `misfire_grace_time=300`, `next_run_time=datetime.now(timezone.utc)` so it also runs shortly after startup).
- [ ] `backend/tests/test_publish_catchup.py` -- unit-test every I/O Matrix row by mocking `async_session_factory`, `get_due_scheduled_campaigns`, `get_scheduled_job`, `get_article_by_campaign_id`, the lazily-imported `scheduler`, `run_publish`, and `run_publish_headless`: social orphaned -> `run_publish(job.id, campaign.id, [])` + `scheduled_at=None`; social within-grace -> no dispatch, `scheduled_at` unchanged; headless orphaned -> `run_publish_headless(str(campaign.id))` + `scheduled_at=None`; headless within-grace -> no dispatch; already-fulfilled (published article) -> `scheduled_at` cleared, no dispatch; in-flight social -> no dispatch; dispatch-throws -> other campaigns still dispatched; no-due -> no-op.
- [ ] `backend/tests/test_publish_catchup.py` -- add a query-guard test for `get_due_scheduled_campaigns` asserting the compiled SQL restricts by `status`, `scheduled_at IS NOT NULL`, and `scheduled_at <=` (mirrors the WHERE-clause guard used for the calendar fix).
- [ ] `backend/tests/test_alembic_filters.py` -- assert `include_name` returns `False` for `("apscheduler_jobs", "table", [])` and `True` for another table (e.g. `("campaigns", "table", [])`) and for non-table types (e.g. `("ix_x", "index", [])`).

**Acceptance Criteria:**
- Given an `approved` social campaign whose `scheduled_at` passed hours ago and whose APScheduler job no longer exists, when the catch-up worker runs, then `run_publish` is invoked once for it and its `scheduled_at` is cleared.
- Given an `approved` campaign with a hidden article and a past `scheduled_at` whose `headless_<id>` APScheduler job is gone, when the catch-up worker runs, then `run_publish_headless` is invoked once for it and its `scheduled_at` is cleared.
- Given any campaign whose APScheduler job (social or headless) is still registered (within grace), when the catch-up worker runs, then it is not dispatched and its `scheduled_at` is unchanged.
- Given the catch-up worker recovers one or more posts, when the pass finishes, then it emits a `logger.warning` with the recovered count and each post's lateness (and calls `sentry_sdk.capture_message`, a no-op until `SENTRY_DSN` is set).
- Given the app starts up, when the scheduler starts, then the catch-up worker is registered and runs an initial pass promptly, then every 5 minutes.
- Given Alembic autogenerate runs against a DB that has the `apscheduler_jobs` table, when it diffs against `SQLModel.metadata`, then it does not emit a `drop_table('apscheduler_jobs')` (the `include_name` filter excludes it).

## Design Notes

Idempotency rests on independent guards, so no post double-publishes: `get_scheduled_job` returns a row only while status is exactly `scheduled` (an in-flight/finished publish is invisible), `scheduler.get_job` being `None` means APScheduler truly dropped the job rather than being late within grace, and `run_publish_headless` self-checks the article status. The `with_for_update(skip_locked=True)` claim plus clearing `scheduled_at` before commit prevents two workers/ticks from grabbing the same campaign.

Social vs headless are disjoint by construction: social scheduling creates a `scheduled_publish` job row and registers `run_publish`; headless scheduling creates NO such job row, instead marking a hidden article and registering `run_publish_headless` under id `headless_{campaign_id}`. The worker keys off the presence of the `scheduled_publish` job row, so it can never fire a social publish on a headless campaign (or vice-versa). Because the normal headless path does not clear `scheduled_at`, fulfilled headless campaigns (article already `published`) would otherwise be re-scanned forever and could starve the batch limit — the housekeeping clear removes them from the working set.

Original per-post platform selection is not persisted (only lived in the APScheduler job args), so social recovery publishes to all connected platforms (`[]`); this matches the common case where no subset was chosen. There is intentionally no staleness cap — a missed post is recovered however late, with the lateness logged; add a cutoff later only if very-late posts become a problem.

## Verification

**Commands:**
- `cd backend && pytest tests/test_publish_catchup.py tests/test_alembic_filters.py -q` -- expected: all new tests pass.
- `cd backend && python -c "import app.main"` -- expected: imports cleanly (no circular-import error from the scheduler/worker wiring).
- `cd backend && python -c "from app.db.alembic_filters import include_name; assert include_name('apscheduler_jobs','table',[]) is False and include_name('campaigns','table',[]) is True"` -- expected: exits 0 (filter behaves).

## Suggested Review Order

**Alembic source fix (prevents future job-store drops)**

- The autogenerate filter — excludes only `apscheduler_jobs` table, passes all others.
  [`alembic_filters.py:9`](../../backend/app/db/alembic_filters.py#L9)

- Filter wired into both offline and online `context.configure` calls.
  [`env.py:41`](../../backend/alembic/env.py#L41)

**Catch-up worker (entry point and design)**

- Main worker: lazy imports, cutoff, batch fetch, classify, single commit, then dispatch.
  [`publish_catchup.py:29`](../../backend/app/workers/publish_catchup.py#L29)

- Social branch: dispatches only when APScheduler job truly gone (not within grace).
  [`publish_catchup.py:59`](../../backend/app/workers/publish_catchup.py#L59)

- Headless branch: hidden-article presence is the discriminator; same grace check.
  [`publish_catchup.py:77`](../../backend/app/workers/publish_catchup.py#L77)

- Already-fulfilled housekeeping: clears `scheduled_at` on published headless campaigns.
  [`publish_catchup.py:93`](../../backend/app/workers/publish_catchup.py#L93)

- Single atomic commit claims all campaigns before any dispatch starts.
  [`publish_catchup.py:125`](../../backend/app/workers/publish_catchup.py#L125)

- Dispatch loop: per-campaign try/except so one failure never blocks the rest.
  [`publish_catchup.py:129`](../../backend/app/workers/publish_catchup.py#L129)

**Repository query**

- `get_due_scheduled_campaigns`: approved + non-null + <= cutoff + skip_locked.
  [`campaigns.py:81`](../../backend/app/db/repositories/campaigns.py#L81)

**Scheduler registration**

- Interval job with `next_run_time=now()` for immediate startup pass.
  [`scheduler.py:59`](../../backend/app/scheduler/scheduler.py#L59)

**Tests**

- Worker behavior tests: all 9 I/O matrix rows including dispatch fault-isolation.
  [`test_publish_catchup.py:117`](../../backend/tests/test_publish_catchup.py#L117)

- Filter unit tests: excluded table, included tables, non-table types.
  [`test_alembic_filters.py:11`](../../backend/tests/test_alembic_filters.py#L11)
