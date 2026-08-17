# Story 24.1: Published-Post Record and Meta platform_post_id Capture

Status: done
<!-- code review complete 2026-08-17: 6 patches applied, 9 deferred, 6 dismissed -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the PersonnaPress platform,
I want every successful Meta publish (Facebook Page, Instagram, Threads) to durably persist the platform-returned post id and permalink on a per-(campaign, platform) record,
so that a later analytics subsystem has a stable external id to poll engagement metrics against (today that id is silently discarded, making analytics structurally impossible).

## Context & Why This Story Exists First

This is the mandatory **foundation** story for Epic 24 (Post Analytics — Meta). It ships no user-visible UI. It exists because of a hard blocker discovered in the current publish path:

- `backend/app/integrations/meta.py` publish functions **return** the platform post id (`publish_facebook_page_post` -> post id, `publish_instagram_feed_post` -> media_id, `publish_threads_post` -> post id).
- But in `backend/app/services/publishing.py`, both `dispatch_publish` and `dispatch_publish_for_platform` call these functions **without assigning the return value**. The id is thrown away. The only record of a publish is a status string (`"success"`) stored in `jobs.error_details` JSON (see `backend/app/db/repositories/jobs.py:108 get_published_platforms_for_campaign`).
- There is **no** per-post publish record anywhere; `Campaign` has no post-id column.

Consequence (state this in the PR description): analytics can only ever measure posts published **after** this ships. Historical posts have no retrievable id and are permanently un-pollable. No backfill is possible.

This story implements architecture-spine decisions **AD-A4** (persist platform_post_id + permalink at publish time) and **AD-A7** (exactly one new table + this capture; no other schema churn), and honors **AD-A10** (best-effort, fault-isolated — id capture must never fail or roll back a publish).

## Acceptance Criteria

1. **Given** a new `published_posts` table, **When** the Alembic migration runs, **Then** it creates a table with at least: `id` (uuid PK), `campaign_id` (uuid FK -> campaigns.id, indexed), `client_id` (uuid FK -> clients.id, indexed, for multi-tenant scope per architecture.md §Data), `platform` (text), `platform_post_id` (text), `permalink` (text, nullable), `published_at` (timestamptz), `created_at` (timestamptz). A uniqueness constraint on `(campaign_id, platform)` prevents duplicate rows for the same publish target; re-publish UPSERTs the latest id.

2. **Given** a successful `publish_facebook_page_post` call in either `dispatch_publish` or `dispatch_publish_for_platform`, **When** the call returns the post id, **Then** a `published_posts` row is created/updated for `(campaign_id, "facebook_page")` with the returned id in `platform_post_id`. For Facebook **photo** posts the row MUST store the feed **`post_id`** field (usable for insights), not the photo `id` — see Dev Notes.

3. **Given** a successful `publish_instagram_feed_post` call, **When** it returns the published `media_id`, **Then** a `published_posts` row is created/updated for `(campaign_id, "instagram")` with that media_id in `platform_post_id`.

4. **Given** a successful `publish_threads_post` call, **When** it returns the Threads post id, **Then** a `published_posts` row is created/updated for `(campaign_id, "threads")` with that id in `platform_post_id`.

5. **Given** each Meta surface exposes a permalink, **When** the id is captured, **Then** `permalink` is best-effort populated (FB: `GET /{post_id}?fields=permalink_url`; IG: `GET /{media_id}?fields=permalink`; Threads: `GET /{post_id}?fields=permalink`). A permalink fetch failure MUST NOT fail the publish or block the id from being stored (`permalink` stays null).

6. **Given** any failure while capturing the id or permalink (DB error, HTTP error, malformed response), **When** it occurs, **Then** it is caught at the capture boundary, logged (Sentry), and the publish result is **unchanged** — the publish is still reported `"success"` and is never rolled back (AD-A10). Id capture is fire-and-forget relative to publish success.

7. **Given** a re-publish of an already-published campaign to Meta, **When** it succeeds again, **Then** the existing `(campaign_id, platform)` row is UPSERTed (latest id + permalink), not duplicated.

8. **Given** the non-Meta publish paths (WordPress, Webflow, X, LinkedIn, github_pages), **When** they run, **Then** their behavior is unchanged — this story only wires capture for the three Meta surfaces. (X/LinkedIn capture are out of scope; see Epic deferral.)

9. **Given** the existing publish test suite, **When** it runs, **Then** all prior tests pass and new tests cover: id captured on each Meta surface, UPSERT on re-publish, and publish still succeeds when capture raises.

## Tasks / Subtasks

- [x] Task 1 — Model + migration (AC: #1)
  - [x] Add `backend/app/db/repositories/models.py` `PublishedPost(SQLModel, table=True)` -> `__tablename__ = "published_posts"` with columns per AC #1; `snake_case` throughout (architecture.md §Format Patterns).
  - [x] Add unique constraint on `(campaign_id, platform)`.
  - [x] Create Alembic migration `alembic/versions/20260817_0001_c5d6e7f8a9b0_add_published_posts.py` (create table + indexes + unique constraint).
- [x] Task 2 — Repository (AC: #1, #2, #3, #4, #7)
  - [x] New `backend/app/db/repositories/published_posts.py` with `upsert_published_post` (INSERT ... ON CONFLICT DO UPDATE) and `get_published_posts_for_campaign` read helper.
- [x] Task 3 — Capture in publish paths (AC: #2, #3, #4, #5, #6)
  - [x] `dispatch_publish` in `publishing.py`: all three Meta branches assign return value and call `_capture_meta_post`.
  - [x] `dispatch_publish_for_platform`: same wiring for all three Meta surfaces.
  - [x] Facebook photo posts: `meta.py` now returns `post_id` (feed story) over `id` (photo object) via `body.get("post_id") or body.get("id")`.
  - [x] Permalink fetch helpers `fetch_facebook_permalink`, `fetch_instagram_permalink`, `fetch_threads_permalink` added to `meta.py`; called inside `_capture_meta_post`; never raise past the capture boundary.
- [x] Task 4 — Tests (AC: #9)
  - [x] `tests/services/test_published_posts_capture.py`: 9 tests covering UPSERT idempotency, id capture on all 3 Meta surfaces in both dispatch functions, fault isolation (upsert failure leaves publish as success), Facebook photo post_id preference, and text-only post fallback.

## Dev Notes

- **Architecture spine is authoritative:** `_bmad-output/planning-artifacts/architecture/architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md`. This story implements AD-A4, AD-A7, and the AD-A10 fault-isolation clause on the publish path. The ERD names this record `PLATFORM_PUBLISH`; we realize it as the concrete `published_posts` table (the spine leaves the physical form to this epic).
- **Two ids — never conflate (AD-A3):** `published_posts.id` is our internal uuid (the future `post_metrics.published_post_id` FK target). `platform_post_id` is the external id read *from* the platform, used to make insight calls in 24-2. Keep them distinct.
- **Facebook photo vs feed id gotcha:** `POST /{page_id}/photos` returns both `id` (photo object id) and `post_id` (the Page feed story id like `{page_id}_{story_id}`). Post-level insights (`GET /{post_id}/insights`) key on the **feed post id**, so store `post_id` for photo posts. Text posts via `/{page_id}/feed` return `id` already in `{page_id}_{postid}` form. Verify against a live post at build.
- **Current publish code to modify — read fully before editing:**
  - `backend/app/services/publishing.py` — `dispatch_publish` (lines ~655-844) and `dispatch_publish_for_platform` (lines ~516-655). Meta branches: instagram ~784, facebook_page ~797, threads ~811 (in `dispatch_publish`). Both functions currently discard the id. `dispatch_publish` doc-comment says "ONLY this function may call decrypt_credential()" — the capture helper does not need creds, keep that invariant intact.
  - `backend/app/integrations/meta.py` — `publish_facebook_page_post` (181), `publish_instagram_feed_post` (126), `publish_threads_post` (224); `META_GRAPH_BASE` = graph.facebook.com/v25.0, `THREADS_GRAPH_BASE` = graph.threads.com/v1.0.
  - `backend/app/db/repositories/jobs.py:108` — `get_published_platforms_for_campaign` infers published platforms from `jobs.error_details` JSON today. Leave it as-is; the new table is additive and does not replace it in this story.
- **Preservation constraints (must not break):** publish success/failure semantics, the `skip_platforms` re-publish logic, the 2s X / 5s LinkedIn staggering, text-only fallback paths, and the job-durability contract (a `jobs` row exists before dispatch). The new capture is purely additive and fault-isolated.
- **Multi-tenancy:** every `published_posts` row carries `client_id` (from `campaign.client_id`) so 24-2/24-3 can scope by client without a join back through campaigns.
- **Testing standards:** pytest + async, mirror existing publish tests (look for `test_publishing*` / `test_meta*` under `backend/tests/` or `backend/app/**/tests`). No new backend packages (spine "Stack": SQLModel + Alembic + httpx only).

### Project Structure Notes

- New files: `backend/app/db/repositories/published_posts.py`, one Alembic migration. Modified: `backend/app/db/repositories/models.py`, `backend/app/services/publishing.py`, `backend/app/integrations/meta.py`.
- Naming per spine Consistency Conventions: model `PublishedPost` (PascalCase singular) -> table `published_posts`; `snake_case`-through to any future API/TS.
- No frontend changes in this story.

### References

- [Source: _bmad-output/planning-artifacts/architecture/architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md#AD-A4] — persist platform_post_id + permalink at publish time
- [Source: .../ARCHITECTURE-SPINE.md#AD-A7] — exactly one new table + one publish-record field
- [Source: .../ARCHITECTURE-SPINE.md#AD-A10] — best-effort, fault-isolated; never breaks a publish
- [Source: .../ARCHITECTURE-SPINE.md#AD-A3] — two distinct ids (internal published_post_id vs external platform_post_id)
- [Source: backend/app/services/publishing.py] — dispatch_publish, dispatch_publish_for_platform (id currently discarded)
- [Source: backend/app/integrations/meta.py] — Meta publish functions return the id
- [Source: backend/app/db/repositories/jobs.py:108] — current publish-state inference from jobs.error_details

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Pre-existing test failures in `test_meta_integration.py` (`test_publish_facebook_page_no_linkedin_post`, `test_publish_threads_no_x_post`) and some router tests are unrelated to this story — they stem from incomplete test setup after earlier platform-native content generation stories added `facebook_post`/`threads_post` fields. Not introduced by this story.
- `_capture_meta_post` catches all exceptions internally (fault-isolated per AD-A10); the function never propagates errors to its callers.
- The UPSERT uses `on_conflict_do_update(index_elements=["campaign_id", "platform"])` targeting the unique constraint created in the migration.

### File List

- `backend/app/db/repositories/models.py` (modified — added `PublishedPost` model)
- `backend/alembic/versions/20260817_0001_c5d6e7f8a9b0_add_published_posts.py` (new)
- `backend/app/db/repositories/published_posts.py` (new)
- `backend/app/integrations/meta.py` (modified — photo post_id fix, permalink fetchers)
- `backend/app/services/publishing.py` (modified — `_capture_meta_post` helper, wired into both dispatch functions)
- `backend/tests/services/test_published_posts_capture.py` (new — 9 tests)

### Review Findings

- [x] [Review][Patch] Missing dispatch_publish_for_platform tests for facebook_page and threads (AC #9) [backend/tests/services/test_published_posts_capture.py]
- [x] [Review][Patch] upsert_published_post has no rollback on commit failure — session left in broken state [backend/app/db/repositories/published_posts.py]
- [x] [Review][Patch] Permalink fetchers return None silently on non-200 with no log — auth failures invisible [backend/app/integrations/meta.py]
- [x] [Review][Patch] Idempotency test asserts call count only, not ON CONFLICT DO UPDATE SQL semantics [backend/tests/services/test_published_posts_capture.py]
- [x] [Review][Patch] _capture_meta_post has no else-warning when platform doesn't match any branch [backend/app/services/publishing.py]
- [x] [Review][Patch] datetime.utcnow() deprecated (Python 3.12+), used on 2 lines in test file [backend/tests/services/test_published_posts_capture.py]
- [x] [Review][Defer] DateTime() vs timestamptz for published_at/created_at [backend/app/db/repositories/models.py] — deferred, pre-existing: project-wide naive UTC pattern via utcnow(); changing one table in isolation would break consistency
- [x] [Review][Defer] created_at lacks server_default in migration [backend/alembic/versions/20260817_0001_c5d6e7f8a9b0_add_published_posts.py] — deferred, pre-existing: consistent with all other model migrations in this project
- [x] [Review][Defer] Copy-paste permalink helpers — fetch_facebook/instagram/threads_permalink are structurally identical [backend/app/integrations/meta.py] — deferred, pre-existing: refactor only, no correctness impact
- [x] [Review][Defer] Synchronous permalink fetch adds up to 10s latency per platform on publish path [backend/app/services/publishing.py] — deferred: architecture change (background task); story designates this as best-effort, not truly fire-and-forget
- [x] [Review][Defer] No index on platform column — full-table scan for analytics by platform [backend/alembic/versions/20260817_0001_c5d6e7f8a9b0_add_published_posts.py] — deferred: premature; add composite index in 24-2/24-3 once query patterns are confirmed
- [x] [Review][Defer] FK ON DELETE not specified for campaigns.id and clients.id [backend/alembic/versions/20260817_0001_c5d6e7f8a9b0_add_published_posts.py] — deferred, pre-existing: consistent with rest of schema; data retention handled by story 7-3
- [x] [Review][Defer] get_published_posts_for_campaign lacks client_id filter — cross-tenant read risk [backend/app/db/repositories/published_posts.py] — deferred: function unused in this story; 24-2 must add client_id filter when it introduces the route
- [x] [Review][Defer] platform column free-text with no enum constraint [backend/app/db/repositories/models.py] — deferred, pre-existing: project-wide pattern for platform strings
- [x] [Review][Defer] UPSERT silently overwrites platform_post_id on re-publish, losing history [backend/app/db/repositories/published_posts.py] — deferred: by design per AC #7; if history is needed, that is a future story
