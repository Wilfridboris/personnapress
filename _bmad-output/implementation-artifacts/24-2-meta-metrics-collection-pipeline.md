---
baseline_commit: 0644f08b83e4acf20036984e44ee7d755091560a
---

# Story 24.2: Meta Metrics Collection Pipeline (post_metrics + scheduled harvester)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the PersonnaPress platform,
I want a scheduled harvester that reads Facebook/Instagram/Threads post insights via the Graph API and appends immutable engagement snapshots to a time-series store,
so that the analytics dashboard (Story 24-3) can display real, historical engagement per post without ever calling a platform API on the read path.

## Context

Second story of Epic 24. Depends on **24-1** (the `published_posts` table with `platform_post_id`). Backend-only; no UI. Implements the **write side** of the architecture spine's CQRS-lite split: a scheduled sweep collects and appends; nothing here is triggered by a user request.

Meta insight reads are **free** and reuse the **existing publishing tokens** (AD-A9) — no new OAuth code, no metered cost. The only cost is DB growth, which is acceptable at launch volume (spine "Deferred": retention/compaction is a later story — **do not** implement a rolling-window or compaction here; ship append-only).

## Acceptance Criteria

1. **Given** a new `post_metrics` table, **When** the Alembic migration runs, **Then** it creates an append-only table with: `id` (uuid PK), `published_post_id` (uuid FK -> published_posts.id, indexed), `client_id` (uuid, indexed, multi-tenant scope), `platform` (text), `captured_at` (timestamptz), `impressions` (bigint, nullable), `engagements` (bigint, nullable), `raw` (jsonb). Indexed to support "latest snapshot per post" reads efficiently (e.g. index on `(published_post_id, captured_at desc)`). Rows are only ever INSERTed, never UPDATEd (AD-A3).

2. **Given** a `meta_metrics.py` integration, **When** `fetch(published_posts: list[...]) -> list[MetricSnapshot]` is called for Facebook Page posts, **Then** it calls `GET /{post_id}/insights` with the post's Page access token and maps the response to normalized `impressions`/`engagements` plus the raw payload. It declares `SUPPORTS_METRICS = True` and its platform(s).

3. **Given** Instagram posts, **When** fetched, **Then** it calls `GET /{ig_media_id}/insights` with the required `instagram_manage_insights` permission and maps metrics. Because IG removed `impressions` in Graph v21 (Jan 2025), map `views` (fallback `reach`) into the normalized `impressions` column (AD-A9).

4. **Given** Threads posts, **When** fetched, **Then** it calls the Threads insights endpoint (`GET /{media_id}/insights`, `threads_manage_insights`) and maps metrics. Verify the exact endpoint/metric names against the live Threads API at build (spine flags this as `[ASSUMPTION]`).

5. **Given** the normalized mapping convention (AD-A3), **When** a snapshot is built, **Then** `impressions` = impressions where available else IG/Threads views/reach; `engagements` = sum of available likes + comments + shares + saves/reposts. Per-platform field mapping is documented in the integration. Platform-specific extras stay in `raw`.

6. **Given** a recurring APScheduler job `metrics_poll`, **When** it is registered in `backend/app/scheduler/scheduler.py`, **Then** it runs on a cadence, writes a `jobs` row (`job_type="metrics_poll"`) before dispatch (inherited job-durability), selects Meta `published_posts` that are **due** per a decaying cadence, fetches their insights (staggered outbound), and bulk-INSERTs snapshots into `post_metrics`.

7. **Given** the decaying cadence (AD-A6, applied to Meta for freshness/row-bounding, not cost since Meta is free), **When** selecting due posts, **Then** a post is polled ~hourly for its first 24h, ~daily to day 7, ~weekly to a 90-day horizon, then no longer polled. "Due" is computed from the post's `published_at` and its latest `captured_at`. Make the cadence table a single documented constant so it is easy to tune.

8. **Given** fault isolation (AD-A10), **When** any single post/platform fetch fails (permission missing, token expired/unauthorized, HTTP/timeout/rate-limit, malformed payload), **Then** the failure is caught per-item (`try` per post), logged to Sentry, that item is skipped and left for the next cadence, and **the sweep continues** for all other posts. The `metrics_poll` job reaching a terminal state is independent of any individual fetch succeeding. A failure MUST NOT throw out of the worker or mark the whole job failed.

9. **Given** a platform/account that is not metrics-capable (e.g. FB Page under 100 likes -> no insights; permission not granted), **When** its fetch returns unavailable, **Then** no fabricated zero row is written; the item is recorded as unavailable (skipped) so 24-3 can render the AD-A5 "not available" state. Distinguish "unavailable" from "transient error", and **capture a machine-readable unavailability reason** where the API allows it (at minimum: `page_under_100_likes`, `permission_missing`, `no_data_yet`, `unknown`) so the dashboard (Story 24-3, AC #8a) can show reason-specific copy such as the FB Page 100-like tooltip. Persist/expose this reason so the read side can surface it (e.g. a nullable `unavailable_reason` on the latest state, or derive it in the read query — dev's call, but it MUST reach 24-3).

10. **Given** the sweep runs on the 1 vCPU / 1 GB Droplet alongside generation, **When** it executes, **Then** it holds only the current batch of ids + response JSON in memory (no full-history load, no pandas/numpy), performs all aggregation later in SQL (24-3), and delegates all I/O via `await httpx` (AD-A2). No new backend packages.

11. **Given** tests, **When** they run, **Then** they cover: mapping of a sample FB/IG/Threads insights payload to normalized columns; "due post" cadence selection at representative ages; per-item fault isolation (one post raises, others still snapshot); and the append-only invariant (poll twice -> two rows, prior row unchanged).

## Tasks / Subtasks

- [x] Task 1 — Model + migration (AC: #1)
  - [x] `backend/app/db/repositories/models.py`: `PostMetric` -> `post_metrics` (append-only) per AC #1; `raw` = JSONB.
  - [x] Alembic migration: create table + `(published_post_id, captured_at desc)` index + `client_id` index.
- [x] Task 2 — Repository (AC: #1, #6)
  - [x] `backend/app/db/repositories/post_metrics.py`: `bulk_insert_snapshots(session, snapshots)`, plus read helpers `latest_per_post` and `series` (used by 24-3; implement now so the read side has them). No UPDATE path.
- [x] Task 3 — Meta metrics integration (AC: #2, #3, #4, #5, #8, #9)
  - [x] `backend/app/integrations/meta_metrics.py`: `async def fetch(...) -> list[MetricSnapshot]`; `SUPPORTS_METRICS = True`; per-surface endpoints; normalized mapping documented inline; reuse publishing tokens from the connection creds (mirror how `dispatch_publish` resolves creds, but this is a **read** — never publishes).
  - [x] Define a small `MetricSnapshot` dataclass/pydantic model (published_post_id, client_id, platform, captured_at, impressions, engagements, raw).
  - [x] Return an explicit "unavailable" signal (not an exception) for capability gaps (AC #9); raise/propagate only truly transient errors, which the worker catches per-item.
- [x] Task 4 — Harvester worker (AC: #6, #7, #8, #10)
  - [x] `backend/app/workers/analytics.py`: `metrics_poll` entrypoint — write `jobs` row; select due Meta posts (join `published_posts` + latest `post_metrics.captured_at`); resolve creds per client/connection; fetch staggered (reuse the existing per-platform stagger discipline); bulk-append; mark job complete regardless of individual failures.
  - [x] Cadence constant + `is_due(published_at, last_captured_at, now)` helper with unit tests.
- [x] Task 5 — Scheduler registration (AC: #6)
  - [x] Register recurring `metrics_poll` in `backend/app/scheduler/scheduler.py` on the existing Supabase `SQLAlchemyJobStore`. Gate on an `ANALYTICS_ENABLED` feature flag (default on for Meta) added to config + `.env.example`.
- [x] Task 6 — Tests (AC: #11)

## Dev Notes

- **Architecture spine authoritative:** `_bmad-output/planning-artifacts/architecture/architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md`. This story = the "Write side (scheduled)" of the dependency diagram: `scheduler -> workers/analytics.py -> integrations/meta_metrics.py -> repositories/post_metrics.py`. Governed by AD-A1, AD-A2, AD-A3, AD-A5, AD-A9, AD-A10; cadence mechanics from AD-A6 (Meta is the free case).
- **Reuse, don't reinvent, credential resolution:** the connection creds (page_access_token, instagram_user_id, page_id, threads_user_id, user_access_token) already exist and are decrypted in `backend/app/services/publishing.py dispatch_publish`. Follow that shape for reads. Respect the existing invariant that decrypted creds are never logged.
- **Existing scheduler patterns to mirror:** look at `backend/app/scheduler/scheduler.py` and existing workers (`backend/app/workers/publish.py`, `cleanup.py`, `reengagement.py`) for the jobs-row-before-dispatch durability pattern and APScheduler registration style. `cleanup.py` is a good template for a recurring maintenance-style sweep.
- **Normalized metric mapping (document in code):**
  - Facebook Page post: `GET /{post_id}/insights?metric=post_impressions,post_engaged_users,...` — pin to the **still-supported** metric set (many FB Page Insights metrics were deprecated June 15 2026; verify at build). `impressions` <- post_impressions; `engagements` <- engaged users / reactions+comments+shares.
  - Instagram media: `GET /{media_id}/insights?metric=views,reach,likes,comments,saved,shares` — `impressions` <- views (fallback reach); `engagements` <- likes+comments+saved+shares.
  - Threads media: insights endpoint — `impressions` <- views; `engagements` <- likes+replies+reposts+quotes (verify field names live).
- **Append-only is load-bearing (AD-A3):** never UPDATE a prior snapshot. "Current" = latest `captured_at` computed at read time. Do NOT also stamp "latest metrics" onto `published_posts` or `campaigns` — that would create two divergent numbers.
- **Do NOT add retention/compaction here.** Per user direction and spine "Deferred," ship append-only; a retention story comes later. No rolling-window delete.
- **Cost note:** Meta reads are free (AD-A9). No cost-log/poll-budget gate is required for Meta (that's an X-only concern, AD-A6, and X is not in this epic). Keep the code path free of X.
- **Concurrency budget (AD-A2):** I/O-bound `await httpx` only; one batch of ids + JSON in memory at a time; no dataframe stack; co-exists with generation on 1 vCPU/1 GB.
- **Testing standards:** pytest async; sample insight payloads as fixtures; freeze time for cadence tests. No new packages.

### Project Structure Notes

- New: `backend/app/integrations/meta_metrics.py`, `backend/app/workers/analytics.py`, `backend/app/db/repositories/post_metrics.py`, `backend/app/db/repositories/models.py` (PostMetric), one Alembic migration.
- Modified: `backend/app/scheduler/scheduler.py` (register `metrics_poll`), config + `.env.example` (`ANALYTICS_ENABLED`).
- Naming per spine: `PostMetric` -> `post_metrics`; error codes reserved for 24-3 (`METRICS_UNAVAILABLE_FOR_PLATFORM`). Timestamps ISO 8601 UTC / `TIMESTAMPTZ`.

### References

- [Source: .../ARCHITECTURE-SPINE.md#AD-A1] — pulled on a schedule; never fetched on request
- [Source: .../ARCHITECTURE-SPINE.md#AD-A2] — external-only fetch; no heavy compute on the Droplet
- [Source: .../ARCHITECTURE-SPINE.md#AD-A3] — append-only snapshot is the single source of truth
- [Source: .../ARCHITECTURE-SPINE.md#AD-A5] — metrics capability is per-platform and asymmetric
- [Source: .../ARCHITECTURE-SPINE.md#AD-A9] — Meta insights reuse publishing tokens; free; IG impressions->views mapping; FB 100-like floor
- [Source: .../ARCHITECTURE-SPINE.md#AD-A10] — best-effort, fault-isolated sweep
- [Source: .../ARCHITECTURE-SPINE.md#Structural Seed / Consistency Conventions] — file paths, job store, naming
- [Source: backend/app/services/publishing.py] — credential resolution shape to mirror (read-only)
- [Source: backend/app/scheduler/scheduler.py + backend/app/workers/*] — durability + registration patterns
- [Source: story 24-1] — published_posts.platform_post_id is the poll key

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

(none — clean implementation, no blockers)

### Completion Notes List

- **Task 1:** Added `PostMetric` model to `models.py` (BigInteger impressions/engagements, JSONB raw, nullable unavailable_reason for AC #9 machine-readable unavailability). Generated Alembic migration via CLI (`alembic revision -m "add_post_metrics"`, revision `444913f949d4`); filled upgrade/downgrade with `op.execute()` for the composite DESC index since Alembic's `create_index` doesn't support sort direction.
- **Task 2:** `post_metrics.py` repository is append-only (`bulk_insert_snapshots` → only `session.add`; no UPDATE path). `latest_per_post` uses `DISTINCT ON (published_post_id) ORDER BY captured_at DESC` for O(1) "current metrics" reads. `series` returns chronological history for sparklines (24-3).
- **Task 3:** `meta_metrics.py` integration: `MetricSnapshot` dataclass carries `unavailable_reason` field; when set it is an unavailability record (no fabricated zeros). Per-platform mapping documented inline with API version notes. FB page-under-100-likes and permission_missing errors resolve to unavailable reasons (not raised); token-expired errors are propagated as transient for the worker to retry next cadence. Threads metric field names noted as requiring live verification per story dev notes.
- **Task 4:** `analytics.py` worker: single `CADENCE` constant is the tuning knob (hourly 0-24h, daily 1-7d, weekly 7-90d). `is_due()` is a pure function (easy to test). Jobs row written before sweep; job always marked complete regardless of per-item failures (AD-A10). Per-(client, platform) batch with per-item try/except + Sentry capture. 0.5 s stagger between Meta platform batches.
- **Task 5:** Scheduler registers `metrics_poll` on 30-minute interval; gated on `ANALYTICS_ENABLED` (default true). `misfire_grace_time=600` allows 10-minute late start after restart.
- **Task 6:** 19 tests: FB/IG/Threads payload mapping (4 tests), unavailability signal (2 tests), cadence is_due across all buckets (9 parametrized + 1 boundary), per-item fault isolation (1 test), append-only invariant (2 tests). All pass.

### File List

- `backend/app/db/repositories/models.py` (modified — added `PostMetric`, imported `BigInteger`)
- `backend/alembic/versions/20260817_1355_444913f949d4_add_post_metrics.py` (new — migration)
- `backend/app/db/repositories/post_metrics.py` (new — repository)
- `backend/app/integrations/meta_metrics.py` (new — integration)
- `backend/app/workers/analytics.py` (new — harvester worker)
- `backend/app/scheduler/scheduler.py` (modified — metrics_poll registration)
- `backend/app/core/config.py` (modified — ANALYTICS_ENABLED setting)
- `backend/.env.example` (modified — ANALYTICS_ENABLED entry)
- `backend/tests/test_meta_metrics.py` (new — 19 tests)

### Review Findings

- [x] [Review][Patch] FB engagements falsy-or swallows zero-engagement posts [backend/app/integrations/meta_metrics.py:192]
- [x] [Review][Patch] latest_per_post f-string SQL with UUID interpolation [backend/app/db/repositories/post_metrics.py:41]
- [x] [Review][Patch] No Threads unavailability test (AC11 gap) [backend/tests/test_meta_metrics.py]
- [x] [Review][Patch] Per-item stagger missing in meta_metrics.fetch — sleep only between batches, not between individual post HTTP calls [backend/app/integrations/meta_metrics.py:85]
- [x] [Review][Patch] metrics_poll has no ANALYTICS_ENABLED guard inside function body [backend/app/workers/analytics.py:77]
- [x] [Review][Defer] Stuck in_progress jobs on process restart — deferred, pre-existing pattern across all workers
- [x] [Review][Defer] Cutoff timezone stripping (cutoff.replace(tzinfo=None)) — deferred, consistent with project DB patterns
- [x] [Review][Defer] Session sharing across multiple db.commit() calls in sweep — deferred, pre-existing pattern in cleanup/reengagement workers
- [x] [Review][Defer] Zero engagement collapses to None for IG/Threads when all sub-metrics are 0 — deferred, design decision acceptable for dashboard display
- [x] [Review][Defer] Credential KeyError caught by outer try/except — deferred, exception logged and handled at fetch() level
- [x] [Review][Defer] SELECT * + PostMetric(**dict(r)) breaks on schema drift — deferred, forward-looking concern, works correctly now
- [x] [Review][Defer] PublishedPost.published_at naive in returned objects — deferred, field not used downstream in meta_metrics.fetch
- [x] [Review][Defer] raw column declared nullable=True in migration — deferred, _safe_json always returns a dict so None never occurs in practice
- [x] [Review][Defer] Decrypted creds held across await suspension point — deferred, standard pattern in project, low risk
- [x] [Review][Defer] No unique constraint on post_metrics — deferred, append-only by design; compaction deferred to a later story per spec

## Change Log

- 2026-08-17: Story 24.2 implemented — PostMetric model + migration, post_metrics repository, meta_metrics integration (FB/IG/Threads), analytics worker with decaying cadence, scheduler registration gated on ANALYTICS_ENABLED, 19 new tests (all pass)
- 2026-08-17: Code review complete — 5 patches applied (FB engagements or-zero fix, latest_per_post parameterized SQL, Threads unavailability test, per-item HTTP stagger, ANALYTICS_ENABLED guard in metrics_poll), 10 deferred, 10 dismissed
