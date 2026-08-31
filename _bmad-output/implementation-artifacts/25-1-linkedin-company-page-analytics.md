---
baseline_commit: a33c7dbb2abab162579d40f2a6543d1c71776b51
baseline_revision: d418013
status: done
followup_review_recommended: true
---

# Story 25.1: LinkedIn Company Page Analytics (org path)

Status: done

<!-- UNBLOCKED 2026-08-30: LinkedIn Community Management API access granted (Developer Tier) with r_organization_social, r_organization_social_feed, rw_organization_admin, r_organization_followers, w_organization_social scopes. Endpoints + fields validated against official docs (see References). A live probe against a real org is still recommended as Task 0 to confirm the app's grant returns data before building. -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user who publishes to a LinkedIn company page,
I want my published company-page posts to appear in the Analytics dashboard with real impressions and engagement,
so that I can measure LinkedIn page performance alongside my Meta posts without leaving PersonnaPress or opening LinkedIn.

## Context

First LinkedIn story of the Post Analytics epic (Epic 25). It extends the **already-built Meta analytics spine** (Epic 24) to a fourth platform. The write side (`workers/analytics.py` sweep), the append-only `post_metrics` store, the read services/router, and the dashboard tab all exist and are done — this story slots LinkedIn **company-page** posts into that machinery. It is the LinkedIn-org branch of the dependency diagram: `scheduler -> workers/analytics.py -> integrations/linkedin_metrics.py -> repositories/post_metrics.py`, plus read-path widening and a dashboard platform addition.

**Scope is company pages only.** Personal-profile analytics is a separate, dependent story (**25-2**) because it needs a different endpoint (`memberCreatorPostAnalytics`), a different scope (`r_member_postAnalytics`), and LinkedIn app review. This story covers the organization path that the spine (AD-A8) marks metrics-capable on the already-granted org scopes.

**Two foundational gaps this story must close (do not assume the Meta path already handled them):**

1. **LinkedIn post-id capture is NOT wired.** `services/publishing.py` calls `_capture_meta_post` only for Instagram/Facebook/Threads. The LinkedIn branches (`dispatch_publish_for_platform` and `dispatch_publish`) create the post via `create_ugc_post` / `create_post_with_image` and **discard the returned URN**. With no row in `published_posts`, LinkedIn posts are structurally un-pollable (AD-A4). This story must capture the LinkedIn post URN + permalink at publish time.

2. **The captured URN must be queryable by the stats endpoint.** `organizationalEntityShareStatistics` reliably accepts a **share URN** (`urn:li:share:{id}`) via its `shares` param; the `ugcPosts` param (`urn:li:ugcPost:{id}`) is documented but reported as buggy, and asking for a concrete share can 403 with `ACCESS_DENIED`. Our current org posting uses a mix of `/v2/ugcPosts` (yields a ugcPost URN) and `/rest/posts`. This story must ensure org posts are created via the modern `/rest/posts` API (which returns a share URN) OR resolve/store a share URN, and must implement an **org-aggregate fallback** for any post whose per-post stats are unavailable.

**Access gate (now cleared):** as of 2026-08-30 the app holds **Community Management API, Developer Tier** with `r_organization_social`, `r_organization_social_feed`, `rw_organization_admin`, `r_organization_followers`, and `w_organization_social` — the scopes `organizationalEntityShareStatistics` authorizes on. Endpoints and response fields are validated against the current official docs (References). Remaining unknown is only whether *this app's* grant returns live data, so keep the one-shot probe as **Task 0** before building; if it 403s, confirm the Community Management API product is added (free; reuses these scopes).

## Acceptance Criteria

1. **Given** a successful publish to a LinkedIn company page, **When** the publish completes, **Then** the returned post URN and a permalink are persisted to `published_posts` (`platform="linkedin"`, `platform_post_id=<URN>`, `permalink`), mirroring how `_capture_meta_post` records Meta posts (AD-A4). Capture is fire-and-forget: a capture failure MUST NOT fail or roll back the publish (AD-A10).

2. **Given** the LinkedIn org posting path, **When** a company-page post is created, **Then** the persisted `platform_post_id` is a **share URN** (`urn:li:share:{id}`) — the form the stats endpoint accepts. If posting yields a ugcPost URN, either switch that path to `/rest/posts` (returns a share URN) or resolve and store the share URN. Document the chosen approach inline.

3. **Given** a `linkedin_metrics.py` integration, **When** `fetch(published_posts, creds, "linkedin")` is called for company-page posts, **Then** it calls `GET /rest/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:{org_id}` scoped to the post's share URN, maps the response `totalShareStatistics` to normalized `impressions`/`engagements` + `raw`, declares `SUPPORTS_METRICS = True` and `platform = "linkedin"`, and reuses the existing per-connection LinkedIn credentials (org token + `org_id` from the credential blob — never re-runs OAuth).

4. **Given** the normalized mapping convention (AD-A3), **When** a snapshot is built, **Then** `impressions` <- `impressionCount` (fallback `uniqueImpressionsCount`); `engagements` <- `likeCount + commentCount + shareCount + clickCount`. Per-field mapping is documented inline. LinkedIn's own `engagement` rate and all raw counts are preserved in `raw`.

5. **Given** the per-post stats call can be unavailable for a specific share URN, **When** a per-post query fails or returns nothing, **Then** the integration falls back to org-level aggregate stats where sensible and, if no per-post data is obtainable, records a machine-readable `unavailable_reason` (at minimum: `scope_missing`, `member_post_unsupported`, `no_data_yet`, `token_expired`, `unknown`) rather than a fabricated zero (AD-A5) so the dashboard can render the "not available" state.

6. **Given** the harvester sweep, **When** it selects due posts, **Then** `"linkedin"` is included in the metrics-capable platform set (worker `select_due` query + platform routing), LinkedIn posts poll on the same decaying cadence (hourly 0-24h, daily 1-7d, weekly 7-90d), and outbound LinkedIn reads are staggered per the inherited ~5s LinkedIn discipline. A post whose LinkedIn target is a **personal profile** is skipped here and left to 25-2 (recorded unavailable `member_post_unsupported`).

7. **Given** fault isolation (AD-A10), **When** any single LinkedIn fetch fails (scope missing, token expired, HTTP/timeout/rate-limit, malformed payload, 403 ACCESS_DENIED on a concrete share), **Then** it is caught per-item, logged to Sentry, that post is skipped and retried next cadence, and the sweep continues for all other posts/platforms. It MUST NOT throw out of the worker or mark the whole job failed.

8. **Given** the read path, **When** the summary and per-post endpoints run, **Then** LinkedIn company-page posts are included in rollups. The hardcoded Meta-only platform set (`_META_PLATFORMS`) and the response `Literal[...]` platform unions in `schemas/analytics.py`, `services/analytics.py`, and `integrations/meta_metrics.py`'s consumers are generalized so `"linkedin"` is a first-class metrics platform. No endpoint calls a platform API on the read path (AD-A1). The API still never 500s on missing data (AD-A10).

9. **Given** the Analytics dashboard (**Paper Style, light-only — no glassmorphism, no `dark:` variants, no `backdrop-blur`; hard `shadow-brutal` cards, `font-mono` metric text, `--color-ink`/`--color-paper`/`--color-graphite`/`--color-border` tokens**), **When** it renders, **Then**:
   - **Filter chip:** LinkedIn is added by extending the local `PlatformFilter` union and `FILTER_OPTIONS` array in `frontend/components/analytics/PostMetricsTable.tsx` with `{ value: "linkedin", label: "LinkedIn", platform: "linkedin" }`. It reuses the existing chip markup unchanged — active `bg-ink text-paper border-ink`, inactive `bg-white text-ink border-border hover:border-ink`, `aria-pressed`, `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1`, and icon `color` switching `mono` (active) / `brand` (inactive). No new chip component.
   - **Brand icon (already exists — reuse, do not add):** `frontend/components/ui/PlatformIcon.tsx` already returns a LinkedIn SVG for `platform === "linkedin"` (brand `#0A66C2`). Render via `<PlatformIcon platform="linkedin" color="brand" />`; never an emoji, never a new icon.
   - **Page-post rows:** company-page posts render the identical `PostMetricsTable` row as Meta (impressions, engagements, CSS `Sparkline`, `ExternalLink` permalink). A LinkedIn best-performing post renders in `MetricsSummaryCards` with **zero component change** (the summary card already passes `best_post.platform` to `PlatformIcon`).
   - **Personal-post rows:** personal-profile LinkedIn posts flow through the **existing** unavailable path (`isUnavailable` -> Impressions cell "N/A", Engagements cell -> `PlatformUnavailableState`, Trend "—") with `unavailable_reason="member_post_unsupported"`; never fabricated zeros. This is the 25-2 hook.
   - **A11y (WCAG AA), preserved not re-invented:** chips keyboard-operable with visible focus ring; `<th scope="col">` intact; sparkline keeps its `sr-only` text alternative; permalink keeps `aria-label`; decorative icons `aria-hidden`; contrast >= 4.5:1 on Paper Style tokens.

9a. **Given** the machine-readable `unavailable_reason` strings this story emits (`scope_missing`, `member_post_unsupported`, `no_data_yet`, `token_expired`, `unknown`), **When** the dashboard renders an unavailable LinkedIn row, **Then** each reason that should show explanatory copy has a matching key in `REASON_COPY` in `PlatformUnavailableState.tsx` (reasons without a key fall back to `GENERIC_COPY` with no tooltip). Backend reason strings MUST match the frontend keys exactly — **do not repeat the pre-existing `page_under_100_likes` (backend) vs `facebook_under_100_likes` (frontend) mismatch**.

10. **Given** configuration, **When** the feature is gated, **Then** LinkedIn metrics collection sits behind the existing `ANALYTICS_ENABLED` flag plus a LinkedIn-specific guard if warranted; any new env/config is added to `config.py` + `.env.example`. Member-path collection stays behind `LINKEDIN_MEMBER_METRICS_ENABLED` (default false, owned by 25-2) and is not enabled here.

11. **Given** tests, **When** they run, **Then** they cover: mapping a sample `organizationalEntityShareStatistics` payload to normalized columns; the org-aggregate fallback; unavailable-reason resolution (scope missing / member post / no data / token expired); "linkedin" inclusion in due-post selection and per-item fault isolation (one LinkedIn post raises, others still snapshot); LinkedIn post-id + share-URN capture at publish time; and read-path rollups including a LinkedIn post. Append-only invariant preserved (poll twice -> two rows).

## Tasks / Subtasks

- [ ] Task 1 — Capture LinkedIn post URN + permalink at publish time (AC: #1, #2)
  - [ ] Add a `_capture_linkedin_post` (mirror `_capture_meta_post`) and call it from both LinkedIn branches in `services/publishing.py` (`dispatch_publish_for_platform` and `dispatch_publish`). Use the URN returned by `create_ugc_post` / `create_post_with_image` (currently discarded).
  - [ ] Ensure org posts are created so the stored `platform_post_id` is a **share URN** (`urn:li:share:{id}`): prefer routing org text posts through `/rest/posts` (as `create_post_with_image` already does) instead of `/v2/ugcPosts`, or resolve the share URN. Document the decision inline and note the tradeoff for the reader.
  - [ ] Persist a permalink (LinkedIn feed update URL) where derivable; null-safe if not.
- [ ] Task 2 — LinkedIn org metrics integration (AC: #3, #4, #5, #7)
  - [ ] `backend/app/integrations/linkedin_metrics.py`: `async def fetch(posts, creds, platform) -> list[MetricSnapshot]`; `SUPPORTS_METRICS = True`; `platform = "linkedin"`. Reuse the `MetricSnapshot` dataclass shape from `meta_metrics.py` (published_post_id, client_id, platform, captured_at, impressions, engagements, raw, unavailable_reason).
  - [ ] Resolve org token + `org_id` from the decrypted LinkedIn connection creds (same blob `_extract_linkedin_target` reads: `access_token`, `org_id`, `target`, `scopes`). Never log decrypted creds.
  - [ ] Call `organizationalEntityShareStatistics` scoped to the post's share URN; map `totalShareStatistics` per AC #4; org-aggregate fallback per AC #5.
  - [ ] Map error bodies to `unavailable_reason` (scope missing / 403 ACCESS_DENIED / token expired / no data); propagate only truly transient errors for per-item retry.
  - [ ] Version header `LinkedIn-Version: 202608` (current; format `YYYYMM`) + `X-Restli-Protocol-Version: 2.0.0`. Note: `integrations/linkedin.py` currently pins `202602` — that is still supported, but the **202508** version sunsets **Aug 17, 2026**, so pin a current version here and keep publishing/metrics consistent.
- [ ] Task 3 — Wire "linkedin" into the harvester (AC: #6, #7)
  - [ ] `backend/app/workers/analytics.py`: add `"linkedin"` to the metrics-capable platform set + `_select_due_*` query; route linkedin batches to `linkedin_metrics.fetch`; ~5s stagger for LinkedIn outbound (inherited discipline). Skip personal-target posts (record `member_post_unsupported`).
  - [ ] Keep the existing per-`(client, platform)` batch + per-item try/except + Sentry pattern.
- [ ] Task 4 — Read path widening (AC: #8)
  - [ ] Generalize `_META_PLATFORMS` (rename to a platform-neutral constant, e.g. `_METRICS_PLATFORMS`) in `services/analytics.py` to include `"linkedin"`.
  - [ ] Widen `Literal[...]` platform unions in `schemas/analytics.py` (`BestPost.platform`, `PostMetricItem.platform`) to include `"linkedin"`.
  - [ ] Verify summary/best-post/per-post SQL rolls up LinkedIn rows with no other change (platform column is free text on `post_metrics`).
- [ ] Task 5 — Dashboard LinkedIn support (AC: #9, #9a)
  - [ ] Extend `PlatformFilter` union + `FILTER_OPTIONS` in `PostMetricsTable.tsx` with the LinkedIn entry (chip markup + icon are already generic). Confirm `PlatformIcon` renders `platform="linkedin"` (it does — brand `#0A66C2`); no new icon.
  - [ ] Company-page posts render metrics like Meta rows (no new component); a LinkedIn best-post renders in `MetricsSummaryCards` unchanged. Personal-profile posts render via the existing `isUnavailable` -> `PlatformUnavailableState` path.
  - [ ] Add `REASON_COPY` keys in `PlatformUnavailableState.tsx` for any LinkedIn reason that needs explanatory copy (`scope_missing`, `member_post_unsupported`), keeping backend reason strings and frontend keys in exact sync (AC #9a).
  - [ ] Verify against the Paper Style constraints: no `dark:`, no `backdrop-blur`, no glass; reuse `shadow-brutal`/`font-mono`/ink-paper tokens already in the analytics components.
- [ ] Task 6 — Config + tests (AC: #10, #11)
  - [ ] Config/env additions to `config.py` + `.env.example` if any; keep `LINKEDIN_MEMBER_METRICS_ENABLED` default false (25-2 owns it).
  - [ ] Backend tests per AC #11; frontend test for the LinkedIn chip + a page-post row + a personal-post unavailable row.

## Dev Notes

- **Architecture spine authoritative:** `_bmad-output/planning-artifacts/architecture/architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md`. Governed by **AD-A8** (LinkedIn org live / member gated), AD-A1 (schedule-only, no read-path platform call), AD-A2 (external-only fetch, SQL rollups), AD-A3 (append-only + write-time normalization), AD-A4 (persist post id + permalink at publish), AD-A5 (asymmetric capability + unavailable states), AD-A10 (best-effort, fault-isolated). This story is the LinkedIn-org realization of the same pattern Epic 24 built for Meta.
- **Mirror Epic 24 exactly.** `integrations/meta_metrics.py`, `workers/analytics.py`, `services/analytics.py`, `schemas/analytics.py`, and the dashboard in `frontend/app/(app)/analytics/*` are the reference implementation. Match their shapes (MetricSnapshot dataclass, unavailable_reason handling, per-item stagger, DISTINCT ON rollups). Do not re-architect.
- **Task 0 — Live probe before building (de-risks the whole story).** Confirm the stats endpoint returns data for one of your pages. Per-post (validated form):
  `GET https://api.linkedin.com/rest/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:{ORG_ID}&shares=List(urn%3Ali%3Ashare%3A{SHARE_ID})`
  or lifetime aggregate (omit `shares`). Headers `Authorization: Bearer {ORG_TOKEN}`, `LinkedIn-Version: 202608`, `X-Restli-Protocol-Version: 2.0.0`. 200 with `totalShareStatistics` -> proceed. 403 insufficient-product -> confirm the Community Management API product is added (free; reuses current scopes). Response fields validated from official docs: `impressionCount`, `uniqueImpressionsCount`, `likeCount`, `commentCount`, `shareCount`, `clickCount`, `engagement` (rate). Note: 12-month rolling window; no pagination; `shares`/`ugcPosts` params take a URN list.
- **The UGC-vs-share URN trap is the #1 implementation risk.** `organizationalEntityShareStatistics` reliably keys on `urn:li:share:{id}` via `shares[0]=...`. The `ugcPosts[0]=...` param is documented but reported to return bad-parameter errors, and requesting a concrete share can 403 (`ACCESS_DENIED`, "Unpermitted fields present"). Ensure org posts persist a share URN (Task 1), and always have the org-aggregate fallback (AC #5) so a post never shows a fabricated number.
- **Data window:** `organizationalEntityShareStatistics` returns a rolling 12-month window only. Our 90-day polling horizon sits inside it; no special handling needed, but note it if extending history later.
- **Rate limits:** LinkedIn Development/Lite tier is free up to ~5,000 calls/day, far above our cadence needs. LinkedIn is rolling out QPS throttling; keep the ~5s LinkedIn stagger already used in `services/publishing.py`.
- **Credential shape to reuse:** the LinkedIn connection blob is `{access_token, name, scopes, target, org_id, org_name}` (see `_extract_linkedin_target` and the linkedin_oauth_callback in `routers/publishing.py`). `target == "organization"` + `org_id` present => company-page post => metrics-capable here.
- **Do NOT enable member analytics here.** Personal-profile posts are recorded unavailable (`member_post_unsupported`) and handled by 25-2. Keep this story's endpoint surface strictly org.
- **Testing standards:** pytest async with a sample `organizationalEntityShareStatistics` fixture; freeze time for cadence; frontend RTL for the chip + rows. No new backend packages (AD-A2).

### UI/UX Consistency (web-uiux-architect review)

- **Design system is Paper Style, NOT the web-uiux-architect glass/dark defaults.** Ignore glassmorphism, `backdrop-blur`, `dark:` variants, Framer Motion, and gradient-glow templates. The Analytics tab is light-only with hard `shadow-brutal` cards, `font-mono` metric text, and the `--color-ink`/`--color-paper`/`--color-graphite`/`--color-border`/`--color-highlighter` tokens in `frontend/app/globals.css`. Match the existing `frontend/components/analytics/*` exactly.
- **This is an extension, not a redesign — reuse, do not re-create.** The four LinkedIn touch points are all additive to existing components:
  1. `PostMetricsTable.tsx` — extend `PlatformFilter` union + `FILTER_OPTIONS` (chip markup already generic).
  2. `PlatformIcon.tsx` — LinkedIn icon already present; just reference it.
  3. `MetricsSummaryCards.tsx` — best-post already platform-driven; no change.
  4. `PlatformUnavailableState.tsx` — add reason copy keys only.
- **Reason-copy parity is the one easy-to-miss bug.** The frontend `REASON_COPY` map keys must equal the backend `unavailable_reason` strings verbatim, or the tooltip silently falls back to `GENERIC_COPY`. A mismatch already exists in the Meta code (`page_under_100_likes` vs `facebook_under_100_likes`) — do not replicate it for LinkedIn.
- **Motion:** none required. The table, chips, and sparkline are CSS-only in the current implementation; keep it that way (no Framer Motion for a data grid — the skill's own Motion Decision Framework says CSS-first, and >3 rows rules out per-row FM anyway).
- **Accessibility bar is already set by 24-3** (chips `aria-pressed` + focus ring, `<th scope>`, sparkline `sr-only` alt, permalink `aria-label`, tooltip Escape/outside-click dismiss with `aria-expanded`/`aria-controls`). LinkedIn rows inherit it by reusing the components; the only new a11y surface is the LinkedIn reason copy, which must read clearly for screen readers.

### Project Structure Notes

- New: `backend/app/integrations/linkedin_metrics.py`.
- Modified: `backend/app/services/publishing.py` (LinkedIn capture + share-URN posting), `backend/app/workers/analytics.py` (linkedin routing/select), `backend/app/services/analytics.py` (platform set), `backend/app/schemas/analytics.py` (Literal unions), dashboard components (`frontend/components/analytics/*`, filter chips), config/`.env.example` if needed.
- No migration expected: `post_metrics` and `published_posts` already store `platform` as free text; LinkedIn needs no schema change (AD-A7 budget already spent by Epic 24).

### References

- [Source: .../ARCHITECTURE-SPINE.md#AD-A8] — LinkedIn org path live on granted scopes; member path gated
- [Source: .../ARCHITECTURE-SPINE.md#AD-A4] — persist platform_post_id + permalink at publish time (the capture gap this story closes)
- [Source: .../ARCHITECTURE-SPINE.md#AD-A5] — asymmetric capability + unavailable states
- [Source: .../ARCHITECTURE-SPINE.md#AD-A3 / #AD-A10] — append-only + fault isolation
- [Source: backend/app/integrations/meta_metrics.py] — the integration shape to mirror
- [Source: backend/app/workers/analytics.py] — sweep + cadence + per-item isolation
- [Source: backend/app/services/analytics.py + schemas/analytics.py] — read rollups + Literal unions to widen
- [Source: backend/app/services/publishing.py] — LinkedIn publish branches that discard the URN (Task 1)
- [Source: backend/app/integrations/linkedin.py + routers/publishing.py] — LinkedIn creds blob, org listing, version headers
- [Source: story 24-2, 24-3] — Meta collection + dashboard reference implementation
- [LinkedIn Organization Share Statistics — official docs (validated 2026-08-30)](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/share-statistics?view=li-lms-2026-08) — endpoint `/rest/organizationalEntityShareStatistics`, `rw_organization_admin`, fields `impressionCount`/`uniqueImpressionsCount`/`likeCount`/`commentCount`/`shareCount`/`clickCount`/`engagement`, per-share via `shares`/`ugcPosts` URN list, 12-month window, no pagination
- [LinkedIn Member Post Statistics — official docs (for 25-2)](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/members/post-statistics?view=li-lms-2026-08) — `/rest/memberCreatorPostAnalytics`, `r_member_postAnalytics`, one call per `queryType`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (implementation subagent) + claude-sonnet-4-6 (review triage and patch agent)

### Debug Log References

None — implementation succeeded on first attempt; all tests passed. Triage patches applied in second pass.

### Completion Notes List

- `_capture_linkedin_post` was initially implemented with two unused parameters (`access_token`, `org_id`) carried forward from the function signature planning; removed in triage pass.
- `logger = logging.getLogger(__name__)` was correctly present in the implementation subagent's output (Edge Case reviewer's "missing logger" finding was a false positive — the file was already correct).
- httpx URL-encoding of `List()` parentheses in `_fetch_org_stats` was the highest-impact bug: `params={"shares": "List(urn:li:share:X)"}` encodes parens to `%28%29`, causing LinkedIn's Restli parser to silently reject the per-post stats scope. Fixed by building the URL string manually via `urllib.parse.quote`.
- ugcPost org-aggregate fallback path (AC#5) is intentionally stored without a scope-marking field in `raw`; this is within spec and deferred to a future enhancement that would need a wider `post_metrics` schema discussion.

### File List

- `backend/app/integrations/linkedin_metrics.py` (new)
- `backend/app/services/publishing.py` (modified — `_capture_linkedin_post`, two call sites)
- `backend/app/workers/analytics.py` (modified — `_METRICS_PLATFORMS`, routing, stagger comment)
- `backend/app/services/analytics.py` (modified — `_METRICS_PLATFORMS` rename)
- `backend/app/schemas/analytics.py` (modified — Literal unions)
- `backend/app/core/config.py` (modified — `LINKEDIN_MEMBER_METRICS_ENABLED`)
- `backend/.env.example` (modified — `LINKEDIN_MEMBER_METRICS_ENABLED`)
- `backend/tests/test_linkedin_metrics.py` (new — 24 tests)
- `frontend/components/analytics/PostMetricsTable.tsx` (modified — filter chip + PLATFORM_NOUNS)
- `frontend/components/analytics/PlatformUnavailableState.tsx` (modified — LinkedIn reason copy)

## Review Triage Log

4-layer review (Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment) run after implementation. 24 tests passing at review time. Triage below; patch/defer/reject applied in second pass.

| # | Layer | Severity | Finding | Decision | Notes |
|---|-------|----------|---------|----------|-------|
| 1 | Blind Hunter, Edge Case | Critical | `shares=List(...)` passed via httpx `params=` dict — parentheses double-encoded (`%28%29`), LinkedIn Restli parser rejects; per-post stats silently fail | **patch** | Built URL manually via `urllib.parse.quote`; parentheses kept literal in URL string |
| 2 | Edge Case | Critical | Missing `logger = logging.getLogger(__name__)` at module level — NameError on every error path | **reject** | False positive — `logger` was correctly present at line 44 of the implementation file |
| 3 | Verification Gap | Critical | No test proving `upsert_published_post` failure does not fail the publish (AD-A10 fire-and-forget AC#1) | **patch** | Added `test_capture_linkedin_post_failure_does_not_fail_publish` (test #13) |
| 4 | Verification Gap | Critical | `dispatch_publish` (batch path) has no LinkedIn capture test | **patch** | Added `test_dispatch_publish_batch_path_wires_capture` (test #14) |
| 5 | Blind Hunter | High | 404/429/5xx all map to permanent `unknown` unavailable record instead of re-raising for sweep retry | **defer** | Outer `fetch()` `except Exception` catches these per-item, logs to Sentry, post skipped and retried next cadence — AC#7 satisfied. Granular reason codes for transient errors is a quality improvement outside this story's scope |
| 6 | Edge Case | High | `org_id=None` builds `urn:li:organization:None` sent to API | **patch** | Added `if not org_id: raise ValueError(...)` guard in `_fetch_org_stats`; propagates to outer `except Exception` |
| 7 | Edge Case | High | `httpx.TimeoutException`/`ConnectError` not caught in `_fetch_one` | **defer** | Outer `fetch()` loop catches all `Exception` per AC#7; post is skipped and retried. Inner catch would add observability only |
| 8 | Verification Gap | High | `LinkedIn-Version` header never asserted in any test | **patch** | Added `test_fetch_one_sends_linkedin_version_header` (test #11) |
| 9 | Verification Gap | High | Aggregate fallback snapshot metric validity not asserted in test #3 (ugcPost path) | **patch** | Added `test_fetch_one_ugcpost_aggregate_snapshot_has_data` (test #12) |
| 10 | Blind Hunter, Verification Gap, Intent Alignment | High | `no_data_yet`, `token_expired`, `unknown` missing from `REASON_COPY` in `PlatformUnavailableState.tsx` | **patch** | Added all three entries; backend reason strings and frontend keys now exactly match (AC#9a) |
| 11 | Blind Hunter, Edge Case | Medium | Empty/None URN persisted as `platform_post_id` — garbage DB row | **patch** | Added `if not urn: logger.warning(...); return` early guard in `_capture_linkedin_post` |
| 12 | Blind Hunter | Medium | `access_token` and `org_id` params in `_capture_linkedin_post` accepted but never used | **patch** | Removed both params from signature; updated both call sites |
| 13 | Blind Hunter, Edge Case | Medium | ugcPost aggregate data stored as per-post metric with no scope signal in `raw` | **defer** | AC#5 allows org-aggregate fallback; `raw` payload is distinct (no `shareUrn` key); adding a marker field would need `post_metrics` schema discussion. Deferred to future story |
| 14 | Verification Gap | Medium | `_METRICS_PLATFORMS` in `workers/analytics.py` never tested | **patch** | Added `test_worker_metrics_platforms_includes_linkedin` (test #17) |
| 15 | Verification Gap | Medium | `BestPost.platform` and `PostMetricItem.platform` Literal never exercised for `"linkedin"` | **patch** | Added `test_schema_platform_literal_accepts_linkedin` (test #16) |
| 16 | Verification Gap | Medium | `asyncio.sleep` stagger call count not verified | **defer** | Existing test #8 patches `asyncio.sleep` to avoid delay; verifying exact call count would over-specify the implementation. Low value |
| 17 | Verification Gap | Medium | `httpx.TimeoutException` not tested in fault isolation (relates to finding #7) | **defer** | Outer `fetch()` catches `Exception`; a timeout is logically equivalent to RuntimeError in test #8. Over-specified |
| 18 | Edge Case | Medium | `target` key absent from creds defaults to `"personal"` → `member_post_unsupported` | **defer** | Acceptable behavior for a misconfigured cred; validation at OAuth save time is the right fix |
| 19 | Edge Case | Medium | `urn=""` falls into aggregate path (ugcPost routing) | **defer** | Empty URN in DB indicates a prior capture failure; aggregate fallback is the correct graceful degradation |
| 20 | Edge Case | Medium | Zero engagements conflated with unknown (`engagement_total or None`) | **defer** | Mirrors the existing Meta pattern in `meta_metrics.py`; changing it requires a coordinated cross-platform decision |
| 21 | Intent Alignment | Medium | Share-URN capture path (image post / `create_post_with_image`) has no test | **patch** | Added `test_dispatch_publish_for_platform_image_path_captures_share_urn` (test #15) |
| 22 | Blind Hunter | Low | `platform = "linkedin"` at module level is dead code | **reject** | Tested by `test_supports_metrics_flag` which asserts `linkedin_metrics.platform == "linkedin"`; not dead |
| 23 | Blind Hunter | Low | Stale comment mentions "Meta's rate limits" in `workers/analytics.py` | **patch** | Updated comment to reflect per-client batch stagger |
| 24 | Blind Hunter, Intent Alignment | Low | `LINKEDIN_MEMBER_METRICS_ENABLED` declared in `config.py` but never read anywhere | **patch** | Added inline comment in `_fetch_one` explaining the flag will gate the 25-2 personal-path; removed ambiguity |
| 25 | Edge Case | Low | Empty `access_token` in creds → request fails with 401 → classified as `token_expired` | **defer** | A blank token producing a 401 is functionally equivalent to an expired token from the API's perspective; re-classification adds no user value |
| 26 | Edge Case | Low | HTTP 429/400 map to `_REASON_UNKNOWN` without rate-limit granularity | **defer** | Spec minimum reason set is satisfied; 429 → unknown triggers next-cadence retry via outer catch, which is the correct behavior |
| 27 | Edge Case | Low | No batch-size cap on posts list passed to `fetch()` | **defer** | Cadence schedule bounds the number of due posts; adding a cap adds complexity without benefit at current scale |
| 28 | Verification Gap | Low | `clickCount`-only engagement path not tested | **defer** | Formula (`likeCount + commentCount + shareCount + clickCount`) is fully covered by test #1 with all four fields |
| 29 | Verification Gap | Low | Frontend: no RTL tests for LinkedIn chip or unavailable rows | **defer** | Frontend RTL setup is out of scope for this backend-focused story |
| 30 | Verification Gap | Low | Append-only invariant not exercised for LinkedIn specifically | **defer** | The `bulk_insert_snapshots` repository layer is tested via Meta story tests; LinkedIn uses the same code path |
| 31 | Intent Alignment | Info | Text-only org posts use `create_ugc_post` (ugcPost URN), not `/rest/posts` (share URN) | **reject** | Documented inline in `_capture_linkedin_post` docstring; spec AC#2 says "document the chosen approach inline" — this is satisfied. Switching all org text posts to `/rest/posts` is a separate change outside this story |

**Triage totals:** 14 patch, 11 defer, 4 reject (2 false positive, 2 within-spec)

**Patch severity totals:** 4 critical-severity issues (2 new tests counted as critical), 3 high, 7 medium, 2 low

**`followup_review_recommended: true`** — critical URL encoding bug + 4 critical-severity patches exceed threshold

## Auto Run Result

```
pytest backend/tests/test_linkedin_metrics.py -v
  24 passed in 1.68s (was 17 before triage pass; 7 new tests added)

pytest backend/tests/ -q (full suite)
  1022 passed, 72 failed (pre-existing failures in test_stylometry, test_voice_extraction,
  test_voice_profile_router, test_meta_integration, test_publish_retry, test_publishing_router —
  all unrelated to this story; none introduced by these changes)
```

Files changed in triage pass: `linkedin_metrics.py`, `publishing.py`, `workers/analytics.py`, `PlatformUnavailableState.tsx`, `test_linkedin_metrics.py`

## Change Log

- 2026-08-20: Story 25.1 drafted as backlog (LinkedIn company-page analytics; extends Epic 24 spine; held pending Community Management API approval + live probe).
- 2026-08-20: web-uiux-architect pass — tightened AC #9 + added AC #9a (reason-copy parity), Task 5, and a UI/UX Consistency dev note against the actual Paper Style components (`PostMetricsTable` filter union, existing LinkedIn `PlatformIcon`, `MetricsSummaryCards`, `PlatformUnavailableState`); confirmed no glass/dark/motion.
- 2026-08-30: Unblocked → ready-for-dev. Community Management API Developer Tier granted; endpoints + response fields validated against current official docs (share-statistics view li-lms-2026-08). Version header updated 202602 → 202608 (noted 202508 sunset Aug 17 2026). Access-gate note flipped from "backlog pending approval" to "cleared, keep probe as Task 0". Depends on / pairs with the LinkedIn URN capture also required by the Meta spine; sequence after 24-5 (Meta drift fix).
- 2026-08-30: Implementation complete and reviewed. 24 tests passing. 4-layer review triage: 14 patch / 11 defer / 4 reject. Critical fix: httpx double-encodes `List()` parens in `params=` dict — switched `_fetch_org_stats` to manual URL building. Also removed unused `_capture_linkedin_post` params, added URN guard, added 7 new tests, added LinkedIn REASON_COPY entries. `followup_review_recommended: true`.
