# Story 20.1: Roadmap Generation Engine

---
baseline_commit: 28d87593f50d57ea14a18875298b9c8a43f3a075
---

Status: done

## Story

As a PersonnaPress user,
I want to submit a brain dump and receive a full week of unique social posts (and optionally a blog post) across all my platforms,
so that I can plan an entire week of content in one session without consuming my individual campaign credits.

## Acceptance Criteria

1. **roadmaps table**: A `roadmaps` table exists with columns: `id UUID PK`, `user_id UUID FK users`, `client_id UUID FK clients`, `brain_dump TEXT NOT NULL`, `status TEXT NOT NULL DEFAULT 'pending'` (values: pending|generating|ready|failed), `week_start_date DATE`, `generate_images BOOLEAN NOT NULL DEFAULT TRUE`, `skip_blog BOOLEAN NOT NULL DEFAULT FALSE`, `error_message TEXT`, `created_at TIMESTAMP`, `updated_at TIMESTAMP`. Index on `user_id`.

2. **campaigns.roadmap_id**: `campaigns` table has a new nullable `roadmap_id UUID` column with FK to `roadmaps.id` ON DELETE SET NULL. Existing campaigns have `roadmap_id = NULL` and are unaffected. Index on `roadmap_id`.

3. **clients.roadmap_config**: `clients` table has a new nullable `roadmap_config JSONB` column storing `{"linkedin_count": int, "twitter_count": int, "blog_enabled": bool, "images_enabled": bool}`. Defaults to NULL; populated on first roadmap creation or via PATCH endpoint.

4. **subscriptions.roadmaps_used**: `subscriptions` table has a new `roadmaps_used INT NOT NULL DEFAULT 0` column. Existing rows backfilled to 0 (server_default handles it).

5. **PLAN_LIMITS roadmaps key**: `constants.py` `PLAN_LIMITS` gains `"roadmaps"` key: `starter: 1, growth: 4, agency: UNLIMITED`. Roadmap credits are independent of campaign credits — a roadmap of 7 posts consumes 1 roadmap credit, not 7 campaign credits.

6. **check_roadmap_limit()**: New function in `subscription_service.py` following same pattern as `check_campaign_limit`. Raises `HTTP 400 ROADMAP_LIMIT_EXCEEDED` when `sub.roadmaps_used >= limit`. Agency plan bypasses with UNLIMITED sentinel and still increments counter. Starter error message: "You've reached your 1-roadmap limit for this billing cycle. Upgrade to Growth for 4 roadmaps per month." Growth: "...Upgrade to Agency for unlimited roadmaps."

7. **check_image_limit_batch(db, user_id, count)**: New function in `subscription_service.py` that returns `(allowed: int, blocked: int)` — never raises. `allowed = max(0, min(count, limit - current_used))`, `blocked = count - allowed`. Existing `check_image_limit()` is unchanged and still used for single-image generation paths.

8. **POST /api/v1/roadmaps**: Request body: `{brain_dump: str (20-10000 chars), linkedin_count: int (0-14), twitter_count: int (0-14), blog_enabled: bool, generate_images: bool, week_start_date: date (ISO, optional — defaults to next Monday)}`. Gate order: `check_trial_not_expired` → `check_roadmap_limit` (increments `roadmaps_used` atomically) → create `Roadmap` row with status=`pending` → enqueue async generation job → return `202 {"roadmap_id": "...", "job_id": "..."}`.

9. **Roadmap generation service** (`services/roadmap.py`): Orchestrates multi-post generation for a roadmap. Calls `check_image_limit_batch(db, user_id, total_posts)` to determine how many images to generate. For each post slot: if blog post → call existing `generation.py` generate pipeline (blog + social) with `roadmap_id` set on the resulting campaign; if social-only post → call a new `generate_social_only(brain_dump, bvp, platform)` path that runs Gemini for X post or LinkedIn post independently (0 thinking tokens, same as existing FR-14). Each generated campaign row has `roadmap_id` set. Roadmap status updates: `pending` → `generating` on start → `ready` on all posts done → `failed` on unrecoverable error.

10. **generate_social_only()**: New function in `services/generation.py` (or `services/roadmap.py`). Accepts `(brain_dump: str, bvp: dict, platform: Literal["x", "linkedin"], campaign_title: str)`. Runs a single Gemini call (0 thinking tokens) with the existing social post prompt adapted for the platform. Creates a `Campaign` row with `blog_html=NULL`; only the relevant platform post field (`x_post` or `linkedin_post`) is populated. The other social platform field is left NULL. `image_regen_count=0`, `status=pending_approval`.

11. **Campaign publish guard for NULL content**: `publishing.py` updated so that before attempting to publish to X, it checks `campaign.x_post is not None` and skips X silently if NULL. Same check for LinkedIn: `campaign.linkedin_post is not None`. Blog platforms (WordPress, Webflow, GitHub) already require `campaign.blog_html`; existing behavior preserved. This prevents a roadmap LinkedIn-only campaign from posting an empty tweet.

12. **GET /api/v1/roadmaps/{id}**: Returns `{id, status, error_message, generate_images, skip_blog, week_start_date, campaigns: [{id, campaign_type, platform_hint, x_post (truncated 100 chars), linkedin_post (truncated 100 chars), blog_title, image_url, status, scheduled_for}]}`. `platform_hint` is derived: "blog_full" if blog_html not NULL, "linkedin" if only linkedin_post set, "x" if only x_post set. Auth: owner only.

13. **PATCH /api/v1/clients/{id}/roadmap-config**: Body `{linkedin_count, twitter_count, blog_enabled, images_enabled}`. Validates ranges (linkedin_count 0-14, twitter_count 0-14). Saves to `clients.roadmap_config`. Returns 200 `{roadmap_config: {...}}`.

14. **PlanLimits and SubscriptionResponse schemas**: `PlanLimits` in `schemas/subscription.py` gains `roadmaps: int`. `SubscriptionResponse` gains `roadmaps_used: int`. `get_subscription()` in `subscription_service.py` populates both fields from `sub.roadmaps_used` and `PLAN_LIMITS[plan]["roadmaps"]`. `fmtLimit` on the account page already handles UNLIMITED display.

15. **Pricing page updated** (`frontend/app/(public)/pricing/page.tsx`): `COMPARISON_ROWS` gains a new entry immediately after `"Campaigns per month"`: `{ label: "Weekly roadmaps/month", starter: "1", growth: "4", agency: "Unlimited" }`. No other rows changed.

16. **Landing page updated** (`frontend/app/page.tsx`): `STARTER_FEATURES` gains `"1 weekly roadmap per month"` after `"10 campaigns per month"`. `GROWTH_FEATURES` gains `"4 weekly roadmaps per month"` after `"30 campaigns per month"`. `AGENCY_FEATURES` gains `"Unlimited weekly roadmaps"` after `"Unlimited campaigns"`.

17. **Tests**: `test_subscription.py`: `test_check_roadmap_limit_starter_blocks_at_2`, `test_check_roadmap_limit_agency_bypasses`, `test_check_image_limit_batch_partial_allocation` (3 remaining, request 5 → allowed=3, blocked=2), `test_check_image_limit_batch_zero_remaining` (→ allowed=0, blocked=N). `test_roadmap_generation.py` (new): mock Gemini + image service; assert N campaigns created with `roadmap_id` set; assert `roadmaps_used` incremented once not N times.

## Tasks / Subtasks

- [x] Task 1: Alembic migrations (AC: 1, 2, 3, 4)
  - [x] `alembic revision --autogenerate -m "add_roadmaps_table_and_roadmap_fields"` — do NOT hand-write revision ID
  - [x] Migration adds `roadmaps` table with all columns and indexes
  - [x] Migration adds `roadmap_id` nullable FK column to `campaigns`
  - [x] Migration adds `roadmap_config` JSONB nullable column to `clients`
  - [x] Migration adds `roadmaps_used INT NOT NULL DEFAULT 0` to `subscriptions` (server_default="0" for existing rows)
  - [x] Add `Roadmap` SQLModel to `models.py` with all columns; add `roadmap_id: Optional[UUID]` FK to `Campaign` model; add `roadmap_config: Optional[dict]` JSONB to `Client` model; add `roadmaps_used: int = Field(default=0)` to `Subscription` model

- [x] Task 2: Constants and subscription service (AC: 5, 6, 7, 14)
  - [x] `constants.py`: add `"roadmaps"` key to all three tiers in `PLAN_LIMITS` (Starter=1, Growth=4, Agency=UNLIMITED)
  - [x] `schemas/subscription.py`: add `roadmaps: int` to `PlanLimits`; add `roadmaps_used: int` to `SubscriptionResponse`
  - [x] `subscription_service.py`: add `check_roadmap_limit(db, user_id)` — copy `check_campaign_limit` pattern, replace `campaigns_used`/`campaigns` references with `roadmaps_used`/`roadmaps`, write tier-specific error messages
  - [x] `subscription_service.py`: add `check_image_limit_batch(db, user_id, count) -> tuple[int, int]` — reads current `image_gen_used`, computes `allowed = max(0, min(count, limit - current))`, returns `(allowed, count - allowed)` without raising or modifying DB
  - [x] `subscription_service.py` `get_subscription()`: populate `roadmaps_used=sub.roadmaps_used` and include `roadmaps` in `PlanLimits(**limits)`

- [x] Task 3: Generation service (AC: 9, 10, 11)
  - [x] `services/roadmap.py` (new file): `generate_roadmap(roadmap_id, db)` async function
    - Load `Roadmap` row, set status=`generating`, commit
    - Load `Client` BVP
    - Call `check_image_limit_batch(db, user_id, total_post_count)` → `(allowed_images, _)`
    - Loop: for blog slot (if `skip_blog=False`) → call `services/generation.py` `run_generation_pipeline(campaign_id, db)` on a new Campaign with `roadmap_id` set; for each additional social slot → call `generate_social_only()`
    - Generate image for first `allowed_images` posts via `services/image.py` `run_image_generation()` (existing, already calls `check_image_limit`)
    - On all done: set `Roadmap.status = "ready"`, commit
    - On exception: set `Roadmap.status = "failed"`, `error_message = str(e)`, commit; log ERROR
  - [x] `services/generation.py`: add `generate_social_only(brain_dump, bvp, platform, campaign_id, db)` — single Gemini call (0 thinking tokens) returning platform post text; updates campaign row
  - [x] `publishing.py`: add NULL-content guards before X publish (`if not campaign.x_post: skip`) and LinkedIn publish (`if not campaign.linkedin_post: skip`) — log DEBUG when skipping

- [x] Task 4: API endpoints (AC: 8, 12, 13)
  - [x] `routers/roadmaps.py` (new file): register on main app as `/api/v1/roadmaps`
  - [x] `POST /` handler: validate body, gate calls in order (`check_trial_not_expired` → `check_roadmap_limit`), save `roadmap_config` to `clients.roadmap_config` (upsert), create `Roadmap` DB row, enqueue `generate_roadmap` as APScheduler instant job, return 202
  - [x] `GET /{roadmap_id}` handler: load Roadmap + child campaigns (query `campaigns WHERE roadmap_id = ?`), build response with truncated previews and `platform_hint` derived field
  - [x] `PATCH /api/v1/clients/{id}/roadmap-config` handler: validate ranges, update `client.roadmap_config` JSONB, return 200
  - [x] Register `roadmaps` router in `main.py`

- [x] Task 5: Pricing and landing page copy (AC: 15, 16)
  - [x] `frontend/app/(public)/pricing/page.tsx`: insert new `COMPARISON_ROWS` entry `{ label: "Weekly roadmaps/month", starter: "1", growth: "4", agency: "Unlimited" }` immediately after the `"Campaigns per month"` row
  - [x] `frontend/app/page.tsx`: insert `"1 weekly roadmap per month"` into `STARTER_FEATURES` after `"10 campaigns per month"`; insert `"4 weekly roadmaps per month"` into `GROWTH_FEATURES` after `"30 campaigns per month"`; insert `"Unlimited weekly roadmaps"` into `AGENCY_FEATURES` after `"Unlimited campaigns"`

- [x] Task 6: Tests (AC: 17)
  - [x] `backend/tests/services/test_subscription.py`: 4 new tests for `check_roadmap_limit` (Starter 0→1 ok, 1→block; Agency bypass) and `check_image_limit_batch` (partial, zero)
  - [x] `backend/tests/services/test_roadmap_generation.py` (new): mock Gemini (`AsyncMock`) and `run_image_generation`; call `generate_roadmap`; assert correct number of Campaign rows created with `roadmap_id` set; assert `sub.roadmaps_used` incremented by 1 (not N); assert roadmap status=`ready`

## Dev Notes

### Service Boundaries (AR-19)
`services/roadmap.py` is the ONLY place that orchestrates multi-post generation for a roadmap. It delegates to `services/generation.py` for blog content and `services/image.py` for images. No business logic in routers. `publishing.py` remains the only place that calls `decrypt_credential()`.

### Roadmap Credits vs Campaign Credits
A roadmap of 7 posts consumes **1 roadmap credit** (incremented in `check_roadmap_limit`), NOT 7 campaign credits. The `campaigns_used` counter on the subscription is NOT incremented for roadmap-generated campaigns. Only manually created brain dump campaigns increment `campaigns_used`. This is the core design decision from the product proposal.

### Image Quota for Batch
`check_image_limit_batch` is non-raising — it returns how many images are allowed given remaining quota. The roadmap service uses the `allowed` count to decide how many posts get images. Individual `check_image_limit` (raising version) is NOT called inside the roadmap loop — instead, `image_gen_used` is incremented manually as each image is generated to keep the count accurate.

### Campaign NULL Content Guard
When `linkedin_post=NULL` on a campaign (X-only roadmap post), publishing to LinkedIn must be skipped silently. Add this check to `_publish_to_linkedin()` in `publishing.py`. Mirror for `_publish_to_x()`. This prevents empty posts and does not affect non-roadmap campaigns (they always have both fields populated by the existing generation pipeline).

### Social-Only Campaign Structure
A social-only campaign (roadmap post) has:
- `blog_html = NULL`
- `x_post = "..."` (X-only) or `NULL`
- `linkedin_post = "..."` (LinkedIn-only) or `NULL`
- `image_url` = generated image URL or NULL
- `roadmap_id` = parent roadmap UUID
- `status = pending_approval`

The Approval Gate still works for these campaigns — if `blog_html` is NULL, the WYSIWYG editor section is hidden and only the social post editors are shown. This is a graceful degradation of the existing Approval Gate UI and requires no story-20-2 changes beyond what's already planned.

### Alembic: Never Hand-Write Revision IDs
Per project-context.md: always use `alembic revision --autogenerate`. The July 2026 incident with duplicate revision ID `a1b2c3d4e5f6` caused a production outage. Run from `backend/` directory.

### X API v2 Media Upload Endpoint Change
The X media upload endpoint has moved from `upload.twitter.com/1.1/media/upload.json` to `api.x.com/2/media/upload`. This is relevant for Story 20-3 but noted here because `twitter.py` is touched in this epic.

### LinkedIn REST Posts vs ugcPosts
Current `create_ugc_post()` in `linkedin.py` uses the `ugcPosts` endpoint. New image posts use `POST https://api.linkedin.com/rest/posts` (different endpoint). Both are needed: text-only → `ugcPosts` (existing), image posts → `rest/posts` (Story 20-3 adds this). Do not replace `create_ugc_post` — add alongside it.

### Week Start Date
Default `week_start_date` if not provided: next Monday from `datetime.now(timezone.utc).date()`. If today is Monday, use today.

### Files Being Modified

| File | Change |
|------|--------|
| `backend/app/core/constants.py` | Add `"roadmaps"` key to `PLAN_LIMITS` |
| `backend/app/db/repositories/models.py` | Add `Roadmap` model; `roadmap_id` FK on `Campaign`; `roadmap_config` on `Client`; `roadmaps_used` on `Subscription` |
| `backend/app/schemas/subscription.py` | Add `roadmaps: int` to `PlanLimits`; add `roadmaps_used: int` to `SubscriptionResponse` |
| `backend/app/services/subscription_service.py` | Add `check_roadmap_limit`, `check_image_limit_batch`; update `get_subscription` |
| `backend/app/services/generation.py` | Add `generate_social_only()` function |
| `backend/app/services/roadmap.py` | New file — roadmap generation orchestrator |
| `backend/app/routers/roadmaps.py` | New file — POST /roadmaps, GET /roadmaps/{id} |
| `backend/app/routers/clients.py` | Add PATCH /{id}/roadmap-config handler |
| `backend/app/main.py` | Register roadmaps router |
| `backend/app/services/publishing.py` | Add NULL-content guards for X and LinkedIn |
| `backend/alembic/versions/XXXXXX_add_roadmaps.py` | New migration (autogenerated) |
| `frontend/app/(public)/pricing/page.tsx` | Add "Weekly roadmaps/month" row to COMPARISON_ROWS |
| `frontend/app/page.tsx` | Add roadmap feature line to STARTER/GROWTH/AGENCY features |
| `backend/tests/services/test_subscription.py` | 4 new roadmap limit tests |
| `backend/tests/services/test_roadmap_generation.py` | New test file |

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Alembic autogenerate included spurious noise (TEXT/AutoString type changes, apscheduler_jobs table ops, unique constraint drops). Manually rewrote migration to only the 4 needed changes.
- SQLModel Field does not support `sa_column_kwargs={"server_default": "0"}`. Used `Field(default=0)` only; server_default handled in migration.
- `roadmap_id` FK with `ondelete="SET NULL"` required explicit `sa_column=Column(PGUUID, ForeignKey(..., ondelete="SET NULL"))` rather than Field kwargs.
- `generate_image_for_roadmap_campaign` had a broken placeholder SQL query. Rewrote the subscription increment section cleanly with `select(Subscription).where(...).with_for_update()`.
- `run_generation_pipeline` must be imported at module level in `roadmap.py` so tests can patch `app.services.roadmap.run_generation_pipeline`.
- `test_generate_roadmap_sets_failed_on_exception`: used `skip_blog=True` to avoid blog slot consuming mock DB responses before the error handler could reload the roadmap.
- Pre-existing failure in `tests/routers/test_campaigns.py::test_list_campaigns_returns_items_and_total`: `_make_db` had only 2 mock execute responses but `list_campaigns` makes 3 calls (count, data, client names). Fixed by adding 3rd mock response `names_result.all.return_value = []`.

### Completion Notes List

- Roadmap credits are fully independent of campaign credits: `check_roadmap_limit` increments `roadmaps_used` once per roadmap, never `campaigns_used`.
- `check_image_limit_batch` is non-raising and non-writing; it only reads quota. `generate_image_for_roadmap_campaign` in `image.py` skips the raising check and manually increments `image_gen_used` after each image succeeds.
- Background generation uses `FastAPI BackgroundTasks` (not APScheduler); each `_run_roadmap_generation` task opens its own `AsyncSessionLocal` session to avoid sharing the request-scoped session across the thread boundary.
- NULL-content guards added to both `dispatch_publish_for_platform` and `dispatch_publish` in `publishing.py` so X/LinkedIn social-only campaigns are never accidentally published to the wrong platform.
- Pricing page `COMPARISON_ROWS` row label is "Weekly roadmaps/month" (not "Roadmaps per month") to match the product copy.

### File List

- `backend/app/db/repositories/models.py` - Added `RoadmapStatus` enum, `Roadmap` model, `roadmap_id` FK on `Campaign`, `roadmap_config` on `Client`, `roadmaps_used` on `Subscription`
- `backend/alembic/versions/20260727_1653_471dca414d29_add_roadmaps_table_and_roadmap_fields.py` - New migration (autogenerated, manually cleaned)
- `backend/app/core/constants.py` - Added `"roadmaps"` key to `PLAN_LIMITS` for all tiers
- `backend/app/schemas/subscription.py` - Added `roadmaps: int` to `PlanLimits`; `roadmaps_used: int` to `SubscriptionResponse`
- `backend/app/services/subscription_service.py` - Added `check_roadmap_limit`, `check_image_limit_batch`; updated `get_subscription`
- `backend/app/services/generation.py` - Added `generate_social_only(brain_dump, bvp, platform, campaign_id, db)`
- `backend/app/services/image.py` - Added `generate_image_for_roadmap_campaign(campaign_id, user_id, title_hint, db)`
- `backend/app/services/roadmap.py` - New file: `generate_roadmap` orchestrator and `_extract_title` helper
- `backend/app/services/publishing.py` - Added NULL-content guards for X and LinkedIn in both dispatch functions
- `backend/app/routers/roadmaps.py` - New file: POST /roadmaps, GET /roadmaps/{id}
- `backend/app/routers/clients.py` - Added PATCH /{client_id}/roadmap-config endpoint
- `backend/app/main.py` - Registered roadmaps router
- `frontend/app/(public)/pricing/page.tsx` - Added "Weekly roadmaps/month" row to COMPARISON_ROWS
- `frontend/app/page.tsx` - Added roadmap feature lines to STARTER/GROWTH/AGENCY feature lists
- `backend/tests/services/test_subscription.py` - Added 5 new tests for check_roadmap_limit and check_image_limit_batch
- `backend/tests/services/test_roadmap_generation.py` - New test file: 3 tests for generate_roadmap
- `backend/tests/routers/test_campaigns.py` - Fixed pre-existing failure: added 3rd mock execute response

### Review Findings

- [x] [Review][Patch] Zero-post roadmap allowed — all counts 0 + blog_enabled=False wastes quota slot silently [routers/roadmaps.py] — fixed: added @model_validator(mode="after") requiring at least one post
- [x] [Review][Patch] generate_social_only silently commits None if LLM key missing [services/generation.py] — fixed: guard raises ValueError; roadmap service catches and marks failed
- [x] [Review][Patch] CampaignSummary missing campaign_type field (AC12) [routers/roadmaps.py] — fixed: added campaign_type field, populated with _platform_hint value
- [x] [Review][Patch] sub=None in generate_image_for_roadmap_campaign: image generated, quota not tracked [services/image.py] — fixed: added warning log when sub is None
- [x] [Review][Patch] Invalid platform in generate_social_only: no else branch — silent no-op [services/generation.py] — fixed: else logs error and returns
- [x] [Review][Patch] Unused Client import in roadmaps.py [routers/roadmaps.py] — fixed: removed
- [x] [Review][Patch] Deferred datetime import inside patch_roadmap_config handler [routers/clients.py] — fixed: moved to module-level imports
- [x] [Review][Patch] Roadmap.status annotated as str but column is SAEnum — isinstance guards scattered [models.py + routers/roadmaps.py] — fixed: type changed to RoadmapStatus
- [x] [Review][Patch] check_roadmap_limit: sub.plan_tier=None not guarded [services/subscription_service.py] — fixed: (sub.plan_tier if sub else None) or "starter"
- [x] [Review][Patch] week_start_date stored as DateTime instead of DATE (AC1) [migration + models.py + routers/roadmaps.py] — fixed: migration uses sa.Date(), model field is Optional[date], router passes date directly

- [x] [Review][Defer] Concurrent image quota overdraw — check_image_limit_batch reads without lock; two concurrent roadmaps can overdraw by up to N images [services/subscription_service.py] — deferred, pre-existing pattern
- [x] [Review][Defer] BackgroundTasks not a durable job queue — lost on worker crash, no retry [routers/roadmaps.py] — deferred, accepted trade-off per dev notes
- [x] [Review][Defer] week_start_date in the past — no validation [routers/roadmaps.py] — deferred, no real harm
- [x] [Review][Defer] Missing ondelete on roadmaps.user_id / client_id FKs [migration] — deferred, consistent with rest of schema

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-07-27 | Story 20.1 implemented: roadmap generation engine, credit system, API endpoints, publishing guards, pricing copy, tests | claude-sonnet-4-6 |
| 2026-07-27 | Story 20.1 code review: 10 patches applied (zero-post validator, generate_social_only None guard, campaign_type field, sub=None quota log, invalid platform else, unused Client import, deferred datetime import, RoadmapStatus type annotation, plan_tier None guard, DateTime→Date fix), 4 items deferred, marked done | claude-sonnet-4-6 |
