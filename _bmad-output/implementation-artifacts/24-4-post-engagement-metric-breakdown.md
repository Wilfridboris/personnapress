---
baseline_commit: 9811c4eb982b19b3d51e13d03675e7a1d21ab2ab
---

# Story 24.4: Post Engagement Metric Breakdown (likes / comments / shares + engagement rate)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a client owner viewing my analytics dashboard,
I want to see likes, comments, and shares broken out per post (not just one opaque "engagements" number) plus an engagement rate,
so that I can understand *what kind* of interaction each post earned and judge performance at a glance.

## Context

Fourth story of Epic 24 (Post Analytics). Epic 24 is currently `done`; this story **reopens it to `in-progress`** to extend the existing spine. It follows **24-2** (the `meta_metrics.py` collection pipeline + `post_metrics` table) and **24-3** (the dashboard tab). It touches the write side (integration + one migration), the read side (service + schema), and the UI (dashboard table + summary), plus two latent-bug fixes discovered during analysis.

**Why this story exists.** Today the pipeline collapses all interactions into a single normalized `engagements` column (`likes + comments + saved + shares` for IG; `post_engaged_users`/reactions for FB; `likes + replies + reposts + quotes` for Threads). The component counts are *fetched* (IG/Threads) or *fetchable* (FB) but discarded. Users see "42 engagements" with no idea whether that was 42 likes or 42 comments. This story surfaces the breakdown users actually recognize.

**This is a deliberate architecture-spine amendment — do not treat it as always-in-scope.** See "Architecture Spine Amendment" below. The spine (AD-A7) fixed the normalized set at exactly `impressions` + `engagements`, with everything else in `raw` JSONB. This story consciously widens that to a **small, bounded** set of engagement-component columns. Record the amendment; do not silently violate AD-A7.

**Scope discipline (inherited from 24-2):**
- Append-only remains sacred (AD-A3): new columns are populated **at write time** from the single API response; **never** recompute normals from `raw` on the read path. Multi-row aggregation (totals, engagement rate over a client) stays in read-time SQL.
- Backfill is a **one-time migration** reading historical `raw` -> new columns. That is a migration operation, not a read-path operation, so it does not violate AD-A3's read-path rule.
- No new backend packages. No pandas/numpy (AD-A2).

## Architecture Spine Amendment

Record this in the story's Dev Agent Record on completion, and (dev's call) leave a one-line note in `ARCHITECTURE-SPINE.md` so the spine stays honest:

- **AD-A7** was "exactly one new table + one publish-record field; two normalized columns (`impressions`, `engagements`); extras in `raw`." Amended to: **the normalized set may include a small bounded set of engagement-component columns (`likes`, `comments`, `shares`) alongside `engagements`; unbounded platform-specific extras still live in `raw`.** No new table. No column explosion (saves stays inside the `engagements` rollup and `raw`, not its own column).
- **AD-A9** normalized-mapping convention now also populates the three component columns per platform (mapping table in AC #3). `engagements` keeps its existing meaning and formula so nothing downstream breaks.
- **AD-A3** write/read split is preserved exactly: components are write-time single-snapshot projections; engagement rate is a read-time derivation.

## Acceptance Criteria

1. **Given** the `post_metrics` table and `PostMetric` model, **When** the Alembic migration runs, **Then** it adds three nullable columns `likes BIGINT NULL`, `comments BIGINT NULL`, `shares BIGINT NULL`. The existing `engagements` column and its formula are unchanged (no downstream break). Rows remain append-only (AD-A3) — the migration only adds columns; it never introduces an UPDATE path in normal operation.

2. **Given** the migration includes a **one-time backfill**, **When** it runs, **Then** for every existing `post_metrics` row that has a non-empty `raw` payload it derives `likes`/`comments`/`shares` from `raw` using the same per-platform mapping as AC #3 and writes them into the new columns. Rows whose `raw` lacks a given component leave that column NULL (never a fabricated zero). The backfill is idempotent and must not touch `impressions`/`engagements`. Unavailability rows (`unavailable_reason` set, `raw` = error payload) are left with NULL components.

3. **Given** `meta_metrics.py` builds a `MetricSnapshot`, **When** a snapshot is created, **Then** it populates `likes`/`comments`/`shares` at write time per this mapping, and `engagements` keeps its current value/formula:

   | Normalized column | Facebook Page | Instagram | Threads |
   | --- | --- | --- | --- |
   | `likes` | `LIKE` subtype from `post_reactions_by_type_total` (already fetched) | `likes` (already fetched) | `likes` (already fetched) |
   | `comments` | `comments.summary(true).total_count` — **object-edge field, NOT insights** (see AC #4) | `comments` (already fetched) | `replies` (already fetched) |
   | `shares` | `shares.count` — **object-edge field, NOT insights** (see AC #4) | `shares` (already fetched) | `reposts` (already fetched) |

   `MetricSnapshot`, `MetricSnapshotRow` (repository duck type), and `bulk_insert_snapshots` all carry the three new fields. Saves (IG) is **not** promoted to its own column — it stays inside the `engagements` rollup and in `raw`.

4. **Given** Facebook comments and shares are **not** available from `GET /{post_id}/insights` (confirmed against Graph API v21: `shares` is a post-object field with a nested `count`; comment count comes from `comments.summary(true).total_count`), **When** fetching a Facebook post, **Then** the integration makes a **second, fault-isolated** Graph call to the post object — e.g. `GET /{post_id}?fields=comments.summary(true),shares` (likes still come from the existing insights `post_reactions_by_type_total` LIKE subtype). This second call MUST be wrapped so that if it fails or returns partial data, `likes`/`impressions`/`engagements` from the primary insights call are still recorded and `comments`/`shares` degrade to NULL — never throw, never lose the primary snapshot (AD-A10). IG and Threads need **no** extra call; their components come from the existing single `/insights` response.

5. **Given** the read side, **When** `services/analytics.py` builds per-post items, **Then** each item exposes `latest_likes`, `latest_comments`, `latest_shares` (nullable) from the latest snapshot, and a derived **`engagement_rate`** = `engagements / impressions` computed **in read-time SQL** (NULL when impressions is NULL/0; do not divide by zero). The `analytics.py` schemas (`PostMetricItem`, and `ClientSummaryResponse` where a rollup is added) and the frontend `usePostMetrics.ts` TS interfaces are extended with matching `snake_case` fields (snake_case-through contract — inherited invariant).

6. **Given** the client summary rollup, **When** computed, **Then** it additionally returns client-level totals `total_likes`, `total_comments`, `total_shares` (SQL `SUM` over latest-per-post, same pattern as `total_engagements`) and an aggregate `engagement_rate` = `SUM(engagements) / SUM(impressions)` (NULL-safe). `best_post` selection logic is unchanged (still ranks by `engagements`).

7. **Given** the per-post table (`PostMetricsTable.tsx`), **When** a post row renders with available metrics, **Then** the breakdown is shown **without adding three more columns** (which would overflow on mobile). Present likes/comments/shares as a compact secondary line beneath the existing "Engagements" headline number — three `icon + value` pairs using Lucide icons only (`Heart` = likes, `MessageCircle` = comments/replies, `Repeat2` = shares/reposts). Each pair has an accessible platform-aware label (see AC #8). Values use the existing `fmt()` formatter. When a component is NULL it renders the Paper-Style em-dash placeholder `—` (never `0`). Follow Paper Style, not the skill's glassmorphism defaults: `font-mono`, `text-graphite`/`text-ink`, `size-3`/`size-3.5` icons, `aria-hidden` on decorative icons.

8. **Given** platform-specific vocabulary, **When** labels/tooltips render, **Then** the correct noun is used per platform via a single mapping constant: Facebook -> "Likes / Comments / Shares"; Instagram -> "Likes / Comments / Shares"; Threads -> "Likes / Replies / Reposts". Screen-reader labels (`sr-only` / `aria-label`) use the platform-correct noun (e.g. "12 replies" for a Threads post, not "12 comments"). Icons stay constant across platforms; only the words change.

9. **Given** the summary cards (`MetricsSummaryCards.tsx`), **When** rendered, **Then** the engagement breakdown and/or engagement rate is surfaced at the summary level without breaking the existing 4-card `grid-cols-2 lg:grid-cols-4` layout — either as a compact breakdown line inside the existing "Total Engagements" card (`Total Likes · Comments · Shares` with the same Lucide icons) or by adding an "Engagement Rate" card. Dev picks the cleaner option; keep it within Paper Style and the existing responsive grid. No emojis; Lucide only.

10. **Given** the "unavailable" and empty states, **When** a post is unavailable (`unavailable_reason` set, all metrics NULL), **Then** the breakdown line is **hidden** for that row (no icons, no zeros) and the existing `PlatformUnavailableState` behavior (AC from 24-3) is unchanged. The breakdown never fabricates data for unavailable rows.

11. **Given** the `unavailable_reason` code drift found during analysis, **When** this story ships, **Then** the FB under-100-likes reason string is consistent end to end. Today `meta_metrics.py` emits `page_under_100_likes` (`_REASON_PAGE_UNDER_100_LIKES`) but `PlatformUnavailableState.tsx` keys its tooltip copy on `facebook_under_100_likes` (line ~18) — so the tooltip never shows. Align them (pick one string, update both sides + any tests) so the reason-specific tooltip renders. This is a real user-facing bug, not a refactor.

12. **Given** the FB subcode-33 mapping is suspect (**Verify then fix**), **When** this story is worked, **Then** dev verifies the actual Meta error payload before trusting the current mapping. `meta_metrics.py:164` maps `code=100, subcode=33` to `page_under_100_likes`, but Meta docs describe subcode 33 as "Object with ID does not exist, cannot be loaded due to missing permissions, or does not support this operation" — a generic object-not-found/permission error, **not** the under-100-likes signal (the genuine under-100 condition surfaces as empty/zero insight data or a distinct message, not subcode 33). Verify against a real error response (a deleted post id and/or an under-100-likes Page in the sandbox), then correct the mapping: subcode 33 -> an object-not-found/permission reason, and detect under-100-likes by its actual response shape. If verification is inconclusive, leave the current mapping but add a clear code comment documenting the uncertainty and a Sentry breadcrumb capturing the raw error body so it can be settled from production data. Do not guess silently.

13. **Given** tests, **When** they run, **Then** they cover: mapping of a sample FB (insights + object-edge) / IG / Threads payload to `likes`/`comments`/`shares`; FB second-call fault isolation (object call fails -> primary snapshot still recorded, comments/shares NULL); backfill from a representative `raw` payload including a row missing a component (stays NULL) and an unavailability row (stays NULL); read-time `engagement_rate` (including impressions=0/NULL -> NULL, no divide-by-zero); the reason-string alignment (AC #11); and a frontend test that the breakdown line renders platform-correct nouns and hides on unavailable rows.

## Tasks / Subtasks

- [x] Task 1 — Model + migration + backfill (AC: #1, #2)
  - [x] `backend/app/db/repositories/models.py`: add `likes`, `comments`, `shares` (`Optional[int]`, `BigInteger`, nullable) to `PostMetric`.
  - [x] Alembic migration: `ADD COLUMN` x3 (nullable). Then a one-time backfill pass over existing rows deriving components from `raw` via the shared mapping (AC #3); idempotent; skips unavailability rows; never touches `impressions`/`engagements`.
  - [x] Extract the `raw -> (likes, comments, shares)` mapping into a single reusable function so the migration backfill and the live integration cannot drift.
- [x] Task 2 — Meta integration write-time population (AC: #3, #4, #12)
  - [x] `backend/app/integrations/meta_metrics.py`: add `likes`/`comments`/`shares` to `MetricSnapshot`; populate in `_map_facebook_snapshot`, `_map_instagram_snapshot`, `_map_threads_snapshot` using the mapping table. FB `likes` = LIKE subtype already parsed from `post_reactions_by_type_total`.
  - [x] FB second call: `GET /{post_id}?fields=comments.summary(true),shares` inside `_fetch_facebook`, fully fault-isolated (its own try; failure -> comments/shares NULL, primary snapshot preserved). Reuse the same page access token and the shared `httpx.AsyncClient`.
  - [x] Verify-then-fix subcode-33 (AC #12): confirmed inconclusive (no sandbox access); preserved original mapping + added Sentry breadcrumb capturing raw error body + clear code comment documenting the uncertainty per AC #12.
- [x] Task 3 — Repository (AC: #3)
  - [x] `backend/app/db/repositories/post_metrics.py`: add the three fields to `bulk_insert_snapshots` INSERT and to the `MetricSnapshotRow` duck type. `latest_per_post`/`series` already `SELECT *`, so they carry the new columns.
- [x] Task 4 — Read side (AC: #5, #6)
  - [x] `backend/app/schemas/analytics.py`: add `latest_likes`/`latest_comments`/`latest_shares`/`engagement_rate` to `PostMetricItem`; add `total_likes`/`total_comments`/`total_shares`/`engagement_rate` to `ClientSummaryResponse`.
  - [x] `backend/app/services/analytics.py`: extend both SQL queries to select the new latest columns and compute `engagement_rate` in SQL (NULL-safe `NULLIF(impressions,0)`); extend the client-summary rollup SUMs.
- [x] Task 5 — Frontend types + table breakdown (AC: #5, #7, #8, #10)
  - [x] `frontend/hooks/usePostMetrics.ts`: extend `PostMetricItem`/`ClientSummary` TS interfaces (`snake_case`).
  - [x] `frontend/components/analytics/PostMetricsTable.tsx`: render the compact breakdown line under the Engagements cell with `Heart`/`MessageCircle`/`Repeat2`; platform-noun mapping constant; NULL -> `—`; hide on unavailable rows; `aria-label` platform-correct labels.
- [x] Task 6 — Summary surfacing (AC: #6, #9)
  - [x] `frontend/components/analytics/MetricsSummaryCards.tsx`: added compact breakdown line inside "Total Engagements" card (likes/comments/shares with Lucide icons) + replaced "Posts Tracked" card with dedicated "Engagement Rate" card, preserving the 4-card `grid-cols-2 lg:grid-cols-4` grid.
- [x] Task 7 — Reason-string alignment (AC: #11)
  - [x] Aligned the FB under-100-likes reason string: `PlatformUnavailableState.tsx` key updated from `facebook_under_100_likes` to `page_under_100_likes` to match the backend constant `_REASON_PAGE_UNDER_100_LIKES`. Tests updated accordingly.
- [x] Task 8 — Tests (AC: #13)
  - [x] Backend: extended `backend/tests/test_meta_metrics.py` (component mapping FB/IG/Threads, FB second call + fault isolation x2, backfill extract_components_from_raw x5); extended `backend/tests/routers/test_analytics.py` (new fields, engagement_rate NULL-safety with impressions=0, reason string alignment). 39 backend tests pass.
  - [x] Frontend: extended `frontend/__tests__/components/analytics/AnalyticsDashboard.test.tsx` (breakdown line Instagram/Threads nouns, em-dash on NULL, hide-on-unavailable). 16 frontend tests pass.

## Dev Notes

### Current state of files being modified (read before editing)

- **`backend/app/integrations/meta_metrics.py`** — normalized mapping lives in `_map_facebook_snapshot` / `_map_instagram_snapshot` / `_map_threads_snapshot`. FB already sums `post_reactions_by_type_total` into a single int (line ~190) — you must instead keep the `LIKE` subtype for the `likes` column while `engagements` keeps using `post_engaged_users` (preferred) / reactions fallback. IG already fetches `views,reach,likes,comments,saved,shares`; Threads already fetches `views,likes,replies,reposts,quotes` — so IG/Threads components need **no** new API fields, only mapping into the new columns. `_FB_METRICS` does **not** contain comments/shares because they are not insights metrics (AC #4). Preserve: append-only, fault-isolation per item, credentials never logged, `unavailable_reason` recording.
- **`backend/app/services/analytics.py`** — all aggregation is SQL (AD-A2); two queries build the summary and the per-post list via `DISTINCT ON (published_post_id) ... ORDER BY captured_at DESC`. Add columns to the SELECT lists and the `engagement_rate` expression here; do not introduce in-process math.
- **`backend/app/db/repositories/post_metrics.py`** — `bulk_insert_snapshots` explicitly names columns on `PostMetric(...)`; add the three. `latest_per_post`/`series` use `SELECT *` so they pick up new columns automatically (verify).
- **`frontend/components/analytics/PostMetricsTable.tsx`** — Paper Style table (`border-border`, `font-mono`, `text-graphite`/`text-ink`, `shadow-brutal` elsewhere). The Engagements cell (line ~224) is where the breakdown line attaches. `isUnavailable` guard already exists (line ~186) — reuse it to hide the breakdown. Do **not** add columns to `<thead>`.
- **`frontend/components/analytics/PlatformUnavailableState.tsx`** — `REASON_COPY` keys (line ~17) must match the backend reason strings (AC #11).

### UI/UX guidance (from web-uiux-architect, adapted to Paper Style)

The project design system is **Paper Style / brutalist**, not the skill's glassmorphism/bento default — do **not** import glass cards, `backdrop-blur`, or Framer Motion here. Apply the skill's *principles* (hierarchy, accessibility, CSS-first motion) within Paper Style:

- **Breakdown line (per row):** a single `flex items-center gap-3 mt-1 font-mono text-xs text-graphite` under the Engagements number. Each pair: `<Heart className="size-3" aria-hidden="true" />` + value, etc. Keep it visually subordinate to the headline `engagements` number (smaller, `text-graphite`) so the table still scans top-down.
- **Icons (Lucide only):** `Heart` (likes), `MessageCircle` (comments/replies), `Repeat2` (shares/reposts). Constant across platforms — only the `sr-only`/`title` noun changes. No emojis (project rule).
- **Platform nouns:** one mapping constant `{ facebook_page: {comments:"Comments", shares:"Shares"}, instagram: {...}, threads: {comments:"Replies", shares:"Reposts"} }`; likes is "Likes" everywhere.
- **Motion:** none required. If a subtle mount fade is wanted, CSS only (`animate-in`), never Framer Motion (skill's Motion Decision Framework: CSS-first, and this is a dense data list).
- **Accessibility:** decorative icons `aria-hidden="true"`; each value pair carries an `sr-only` label like `12 replies`; NULL renders `—` with `aria-label="Not available"`. Contrast: `text-graphite` on `paper`/`white` already meets AA in this system; keep values at `text-ink` if graphite is too light at `text-xs`.
- **Summary card:** prefer a compact breakdown line inside the existing "Total Engagements" card over a 5th card, to preserve the clean 2x2 / 1x4 grid. If adding "Engagement Rate", format as a percentage with one decimal (`fmt` may need a percent variant — check `frontend/lib/formatters.ts` before adding).

### External API facts (verified Aug 2026)

- **Facebook (Graph v21):** likes via insights `post_reactions_by_type_total` (`LIKE` key). **Comments and shares are NOT insights** — `shares` is a post-object field returning `{ count }`; comment count is `comments.summary(true).total_count`. Fetch via a second call `GET /{post_id}?fields=comments.summary(true),shares`. FB Page insights still require a Page with 100+ likes; below that, existing AD-A5 unavailability applies.
- **Instagram (Graph v21+):** media `/insights` returns `likes,comments,shares,saved,reach,views`. `impressions` was removed (v21/deprecated v22) -> `views` is the replacement (already handled by 24-2). No second call needed. (Note a known third-party report of IG insight values doubling — sanity-check magnitudes against the post when verifying, but do not add correction logic without evidence.)
- **Threads:** `/insights` returns `likes,replies,reposts,quotes,views`. Map `replies` -> `comments`, `reposts` -> `shares`. Re-verify field names on the live API at build (spine `[ASSUMPTION]` on Threads).

### Project Structure Notes

- No new files required — this extends existing 24-2/24-3 modules plus one Alembic migration. Aligns with the spine Structural Seed (one table, normalized columns on `post_metrics`, read-time rollups in `services/analytics.py`, dashboard in `components/analytics/*`).
- **Variance from spine (recorded):** AD-A7's "two normalized columns" widened to include `likes`/`comments`/`shares` (bounded). See "Architecture Spine Amendment". This is the only intentional deviation; flag it in the retrospective for Epic 24.
- snake_case-through contract holds: DB columns `likes|comments|shares|engagement_rate` -> API JSON `latest_likes|...|engagement_rate` / `total_*` -> TS interface fields identical.

### References

- [Source: _bmad-output/planning-artifacts/architecture/architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md#AD-A3] write/read split — normals at write time, aggregates at read time, no raw parsing on read.
- [Source: ...ARCHITECTURE-SPINE.md#AD-A7] one table, bounded normalized columns (amended by this story).
- [Source: ...ARCHITECTURE-SPINE.md#AD-A9] Meta insights mapping, IG impressions->views, FB 100-likes gate, raw payloads in `post_metrics.raw`.
- [Source: ...ARCHITECTURE-SPINE.md#AD-A10] best-effort fault isolation — governs the FB second call.
- [Source: backend/app/integrations/meta_metrics.py] current mapping + `_fb_unavailable_reason` subcode-33 (AC #12).
- [Source: backend/app/services/analytics.py] read-time SQL rollups (engagement_rate, component SUMs).
- [Source: frontend/components/analytics/PostMetricsTable.tsx] Engagements cell + `isUnavailable` guard (breakdown attach point).
- [Source: frontend/components/analytics/PlatformUnavailableState.tsx] reason-string mismatch (AC #11).
- [Source: _bmad-output/implementation-artifacts/24-2-meta-metrics-collection-pipeline.md] prior story: normalized mapping + append-only + fault isolation conventions.
- External: Facebook Graph API `/docs/graph-api/reference/post/` (`shares.count`, comments summary); Instagram Platform Insights docs; verified Aug 2026.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — clean implementation with one frontend test fix (summary card label changed from "Posts Tracked" to "Engagement Rate" and scoped breakdown assertion to table section).

### Completion Notes List

- **Task 1:** Added `likes`, `comments`, `shares` (BigInteger, nullable) to `PostMetric` model + migration `4789135e4739`. Migration includes idempotent one-time backfill reading `raw` JSONB for pre-24.4 rows. Shared `extract_components_from_raw()` function canonical for both migration and live integration.
- **Task 2:** `MetricSnapshot` gains `likes/comments/shares`. All three platform mappers populate them. FB second call (`GET /{post_id}?fields=comments.summary(true),shares`) is fault-isolated in `_fetch_facebook` — failure degrades only `comments`/`shares` to NULL, preserving the primary `impressions`/`engagements` snapshot (AD-A10). Object-edge data stored in `raw["_object"]` for backfill parity. Subcode-33: inconclusive — original mapping preserved, Sentry breadcrumb added per AC #12.
- **Task 3:** `bulk_insert_snapshots` now inserts `likes`/`comments`/`shares`. `MetricSnapshotRow` duck type extended. `SELECT *` queries pick up new columns automatically.
- **Task 4:** Both SQL queries in `analytics.py` extended: `engagement_rate = NULLIF(impressions,0)` in per-post DISTINCT ON; `SUM(likes/comments/shares)` + aggregate `engagement_rate` in summary CTE. All new fields in Pydantic schemas.
- **Task 5:** `usePostMetrics.ts` TS interfaces extended. `PostMetricsTable.tsx` renders compact `EngagementBreakdown` line beneath the Engagements number — hidden on `isUnavailable` rows. `PLATFORM_NOUNS` constant maps Threads "replies"/"reposts". Icons `Heart`/`MessageCircle`/`Repeat2`, `aria-hidden`, `aria-label` per value.
- **Task 6:** `MetricsSummaryCards.tsx` — "Total Engagements" card gains a compact breakdown line (likes/comments/shares, Lucide icons). "Posts Tracked" replaced by "Engagement Rate" card. Grid stays `grid-cols-2 lg:grid-cols-4`.
- **Task 7:** `PlatformUnavailableState.tsx` `REASON_COPY` key updated from `facebook_under_100_likes` → `page_under_100_likes` to match backend constant. All tests updated.
- **Task 8:** 39 backend tests pass (test_meta_metrics + test_analytics). 16 frontend tests pass.
- **Architecture:** AD-A7 amendment noted in `ARCHITECTURE-SPINE.md`.

### File List

backend/app/db/repositories/models.py
backend/app/integrations/meta_metrics.py
backend/app/db/repositories/post_metrics.py
backend/app/schemas/analytics.py
backend/app/services/analytics.py
backend/alembic/versions/20260821_2251_4789135e4739_add_likes_comments_shares_to_post_.py
backend/tests/test_meta_metrics.py
backend/tests/routers/test_analytics.py
frontend/hooks/usePostMetrics.ts
frontend/components/analytics/PostMetricsTable.tsx
frontend/components/analytics/MetricsSummaryCards.tsx
frontend/components/analytics/PlatformUnavailableState.tsx
frontend/__tests__/components/analytics/AnalyticsDashboard.test.tsx
_bmad-output/planning-artifacts/architecture/architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md

### Review Findings

- [x] [Review][Patch] `_int_or_none` coerces integer 0 to None — valid zero metric stored as NULL [backend/app/integrations/meta_metrics.py:533]
- [x] [Review][Patch] `obj.get("comments", {}).get("summary")` — AttributeError if FB returns key with value None [backend/app/integrations/meta_metrics.py:121 + migration:55]
- [x] [Review][Patch] `_REASON_OBJECT_NOT_FOUND` constant defined but never used (dead code) [backend/app/integrations/meta_metrics.py:65]
- [x] [Review][Patch] No test for `engagement_rate` NULL when `impressions IS NULL` — only impressions=0 case is tested [backend/tests/routers/test_analytics.py]
- [x] [Review][Patch] No frontend test for Facebook-specific vocabulary in breakdown line (AC #13) [frontend/__tests__/components/analytics/AnalyticsDashboard.test.tsx]
- [x] [Review][Patch] `int(raw_like)` and `int(c)`/`int(s)` have no try/except — non-numeric value raises ValueError uncaught [backend/app/integrations/meta_metrics.py:115]
- [x] [Review][Defer] Sentry breadcrumb emitted unconditionally on every under-100-likes FB hit — persists indefinitely [backend/app/integrations/meta_metrics.py:275] — deferred, pre-existing design choice; remove once subcode-33 mystery settled in production
- [x] [Review][Defer] `extract_components_from_raw` early-exit on empty `data` drops FB `_object` in edge case [backend/app/integrations/meta_metrics.py:103] — deferred, pre-existing; only triggered if insights 200 returns empty data list (uncommon)
- [x] [Review][Defer] `MetricSnapshotRow.raw: dict` typed as non-Optional but DB column is nullable [backend/app/db/repositories/post_metrics.py:101] — deferred, pre-existing annotation inaccuracy; no runtime impact

## Change Log

- 2026-08-21: Story 24.4 implemented — added likes/comments/shares columns + engagement_rate to post_metrics (model, migration with backfill, integration write path, read SQL, API schemas, frontend types+UI); FB second-call fault isolation; Threads noun mapping (replies→comments, reposts→shares); reason-string alignment (page_under_100_likes); AD-A7 spine amendment recorded. 39 backend + 16 frontend tests added/updated.
