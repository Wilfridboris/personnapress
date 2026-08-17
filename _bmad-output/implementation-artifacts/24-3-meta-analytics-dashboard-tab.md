---
baseline_commit: adfa7a3567e6e8ed0baefea027cac4f2b2a81743
---

# Story 24.3: Meta Analytics Dashboard Tab (read API + UI)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a new Analytics tab that shows how my published Facebook, Instagram, and Threads posts are performing (impressions, engagements, trend) for the active client,
so that I can see the results of the content I create without leaving PersonnaPress or opening each platform.

## Context

Third and final story of Epic 24 (Meta). Depends on **24-2** having produced real snapshots. Implements the **read side** of the architecture spine's CQRS-lite split: read-only endpoints project stored snapshots into display rollups with cheap SQL, and a new client-scoped dashboard renders them. **No platform API is ever called on this path (AD-A1).** UI follows the existing **Paper Style** design system (not glassmorphism/dark mode).

## Acceptance Criteria

1. **Given** read-only analytics endpoints under `/api/v1/analytics`, **When** a request arrives, **Then** each is JWT-protected (`get_current_user`), client-scoped, rate-limited (slowapi 10 req/min/user), and returns `snake_case` JSON. Endpoints: `GET /api/v1/analytics/clients/{client_id}/summary` (rollup totals) and a per-post/per-campaign metrics endpoint (latest metrics + trend series). No endpoint calls a platform API.

2. **Given** stored snapshots for a client's Meta posts, **When** the summary endpoint runs, **Then** it computes — **in SQL only** (AD-A2) — totals across metrics-capable Meta platforms: total impressions, total engagements, number of posts tracked, and the best-performing post (by engagements). "Current" per-post value = the latest `captured_at` row (`DISTINCT ON` / window). No history is loaded into process memory.

3. **Given** the per-post endpoint, **When** it runs, **Then** it returns, per published Meta post: platform, post preview (campaign title/excerpt), latest impressions, latest engagements, permalink, `captured_at`, and a small time-series (for a sparkline). Posts with no snapshots yet, or on a non-capable surface, are returned with an explicit unavailable marker (never fabricated zeros — AD-A5).

4. **Given** the app navigation, **When** the sidebar/mobile drawer render, **Then** a new **"Analytics"** item (Lucide `BarChart3`) appears in `frontend/components/layout/nav-items.ts` (after Calendar), routing to `/analytics`. It reads the **active client** via the existing `ClientSwitcher`, consistent with Dashboard and Calendar. Active/hover/focus-visible states match existing `NavItem` behavior.

5. **Given** the `/analytics` page, **When** it loads for the active client, **Then** it renders (top -> bottom): a row of summary cards (Total impressions · Total engagements · Best-performing post · Posts tracked) using Paper Style `shadow-brutal` cards; platform filter chips (All / Facebook / Instagram / Threads with brand icons); and a per-post table (`PostMetricsTable`) with preview, platform icon, impressions, engagements, a CSS sparkline trend, and a permalink link-out.

6. **Given** data is polled not live, **When** the page renders, **Then** it shows a freshness indicator ("Updated {relative time} ago") derived from the most recent `captured_at`, so users understand numbers are periodic snapshots, not real-time.

7. **Given** a client with no tracked posts yet, **When** the page loads, **Then** it shows an empty state ("No analytics yet — publish a post to Meta to start tracking") rather than an error or a zeroed dashboard.

8. **Given** a platform/post that is not metrics-capable (AD-A5/A9: FB Page under 100 likes, permission not granted, or a surface with no snapshots), **When** rendered, **Then** the row/section shows a `PlatformUnavailableState` ("analytics not available for this platform") — no fabricated metrics.

8a. **Given** a Facebook Page post shown as unavailable specifically because the Page is under Meta's 100-like threshold, **When** the user hovers/focuses the unavailable indicator, **Then** an accessible tooltip explains the caveat — e.g. "Facebook only provides post insights for Pages with 100+ likes. Analytics will appear here once this Page reaches that threshold." The tooltip is keyboard-focusable (not hover-only), dismissible, and uses the app's existing tooltip pattern. Where the API can distinguish the 100-like case from other unavailable reasons (permission missing, no snapshot yet), show the reason-specific copy; otherwise fall back to the generic unavailable message without a misleading tooltip.

9. **Given** the read path, **When** any snapshot is missing or a query returns nothing, **Then** the UI degrades gracefully and the API **never** 500s on missing metrics (AD-A10) — missing data renders empty/"not available."

10. **Given** data fetching, **When** the page mounts, **Then** it uses React Query via `frontend/hooks/usePostMetrics.ts` with keys `["analytics", clientId]` / `["post-metrics", campaignId]`, polling **only our own API** (never a platform), with shimmer skeletons while loading.

11. **Given** accessibility (WCAG AA), **When** assessed, **Then** filter chips are keyboard-operable with visible focus, the table uses proper `<th scope>`, icon-only controls have `sr-only`/`aria-label`, decorative icons are `aria-hidden`, sparklines have a text alternative (e.g. current value + trend label), and contrast >= 4.5:1 on Paper Style tokens.

## Tasks / Subtasks

- [x] Task 1 — Read API (AC: #1, #2, #3, #9)
  - [x] `backend/app/routers/analytics.py` (thin) — prefix `/api/v1/analytics`, `get_current_user`, slowapi limit, client-scope check (mirror existing routers that scope by client, e.g. campaigns router).
  - [x] `backend/app/services/analytics.py` — SQL rollups only (latest-per-post via `DISTINCT ON`, totals, best post); no platform calls, no in-process aggregation.
  - [x] Reuse `backend/app/db/repositories/post_metrics.py` `latest_per_post` / `series` (from 24-2).
  - [x] Response schemas in `backend/app/schemas/` (`analytics.py`); `snake_case`.
  - [x] Error codes `METRICS_UNAVAILABLE_FOR_PLATFORM`; standard error shape `{"error":{"code","message","detail"}}`.
- [x] Task 2 — Navigation (AC: #4)
  - [x] Add `{ href: "/analytics", label: "Analytics", icon: BarChart3 }` to `nav-items.ts`. Verify it renders in `sidebar.tsx` and `MobileDrawer.tsx` (both consume `NAV_ITEMS`; mind the `calendarIdx` slice logic so the item lands where intended).
- [x] Task 3 — Page + components (AC: #5, #6, #7, #8, #10, #11)
  - [x] `frontend/app/(app)/analytics/page.tsx` — client-scoped (active client from ClientSwitcher context, same mechanism Dashboard/Calendar use).
  - [x] `frontend/components/analytics/MetricsSummaryCards.tsx` (Paper Style `shadow-brutal`), `PostMetricsTable.tsx` (CSS sparkline), `PlatformUnavailableState.tsx`, and platform filter chips.
  - [x] `PlatformUnavailableState` accepts an unavailability `reason` and renders a keyboard-focusable, dismissible tooltip (reuse the app's existing tooltip primitive) with reason-specific copy — the FB Page 100-like caveat per AC #8a. Search `frontend/components/ui`/`common` for the existing tooltip component before adding a dependency.
  - [x] `frontend/hooks/usePostMetrics.ts` — React Query keys per spine; our-API-only.
  - [x] Freshness indicator + empty/skeleton states.
- [x] Task 4 — Tests
  - [x] Backend: summary/per-post rollup SQL correctness (latest-per-post, totals, best post); unavailable marker; no-data returns empty not 500.
  - [x] Frontend: renders summary cards + table from a mock payload; empty state; unavailable state; filter chips filter by platform; freshness label; a11y checks (roles, labels, focus).

## Dev Notes

- **Architecture spine authoritative:** `_bmad-output/planning-artifacts/architecture/architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md`. This is the "Read side (on request)" + Frontend of the dependency diagram. Governed by AD-A1 (no platform call on read), AD-A2 (SQL rollups, no in-process math), AD-A3 (latest-per-post at read time), AD-A5/A9 (unavailable states), AD-A10 (never 500 on missing metrics).
- **Design system = Paper Style (NOT the web-uiux-architect glass defaults).** Tokens in `frontend/app/globals.css`: `--color-paper` (#F9F9F6) bg, `--color-ink` (#111) text, `--color-graphite`, `--color-border`, `--color-highlighter`; hard shadows via `.shadow-brutal` (`4px 4px 0 var(--color-ink)`) and `.shadow-brutal-sm`. Light-only; **no** `dark:` variants, **no** `backdrop-blur`/glass. Match existing cards and the tab/chip styling already used in the app (e.g. `frontend/components/clients/ClientDetailTabs.tsx` for tab/`role="tablist"` patterns, campaigns list for tables/rows).
- **Icons:** Lucide React only (project constraint — no emoji, import from installed lib). `BarChart3` for the nav item; platform brand icons — reuse whatever the app already uses for Facebook/Instagram/Threads in the calendar/publishing UI (search `components/calendar`, `components/publishing`, `components/common` for existing platform-icon components before adding new ones).
- **Active-client mechanism:** replicate how `frontend/app/(app)/dashboard` and `/calendar` obtain the active client (ClientSwitcher writes it; those pages read it). Do not invent a new client-selection pattern; `/analytics` should feel identical.
- **Read-only guarantee:** the dashboard MUST NOT trigger any platform API call (AD-A1). It polls only `/api/v1/analytics/*`. React Query `refetchInterval` (if any) hits our API only.
- **Sparklines:** pure CSS/SVG from the returned series — no charting library unless one is already installed (verify `frontend/package.json` first; prefer a tiny inline SVG to avoid a new dependency).
- **Freshness honesty:** the "Updated Xh ago" stamp is important product-wise — snapshots are periodic (24-2 cadence), so never imply real-time.
- **Testing standards:** backend pytest async (rollup SQL against seeded snapshots); frontend RTL + jest/vitest per the repo's existing frontend test setup (check `frontend/` for the runner). Follow existing component test patterns.

### Project Structure Notes

- New backend: `routers/analytics.py`, `services/analytics.py`, `schemas/analytics.py`. New frontend: `app/(app)/analytics/page.tsx`, `components/analytics/*`, `hooks/usePostMetrics.ts`. Modified: `frontend/components/layout/nav-items.ts` (and verify sidebar/drawer slice logic).
- All `snake_case` DB->API->matched to TS types.

### References

- [Source: .../ARCHITECTURE-SPINE.md#AD-A1] — no platform call on the read path
- [Source: .../ARCHITECTURE-SPINE.md#AD-A2] — SQL rollups only, no in-process aggregation
- [Source: .../ARCHITECTURE-SPINE.md#AD-A5 / #AD-A9] — per-platform unavailable states; Meta specifics
- [Source: .../ARCHITECTURE-SPINE.md#AD-A10] — never 500 on missing metrics
- [Source: .../ARCHITECTURE-SPINE.md#Consistency Conventions] — routes, React Query keys, component names, error codes
- [Source: frontend/app/globals.css] — Paper Style tokens + shadow-brutal
- [Source: frontend/components/layout/nav-items.ts + sidebar.tsx + MobileDrawer.tsx] — nav wiring + calendarIdx slice
- [Source: frontend/components/clients/ClientDetailTabs.tsx] — existing tab/chip a11y pattern
- [Source: story 24-2] — post_metrics snapshots + repository read helpers

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

N/A — no significant debugging required.

### Completion Notes List

- Implemented two read-only analytics endpoints under `/api/v1/analytics/clients/{client_id}/summary` and `/api/v1/analytics/clients/{client_id}/posts`, both JWT-protected, client-scoped, and slowapi rate-limited at 10/min.
- All SQL aggregation uses `DISTINCT ON` for latest-per-post (AD-A3) and bulk series queries; no in-process aggregation (AD-A2). Never calls a platform API (AD-A1).
- Posts with no snapshot return `unavailable_reason="no_snapshot"`; posts from non-metrics-capable surfaces propagate their unavailable_reason through (AD-A5/A10).
- Added `{ href: "/analytics", label: "Analytics", icon: BarChart3 }` after Calendar in nav-items.ts. The `calendarIdx` slice in Sidebar and MobileDrawer places it automatically in the correct position (after Calendar).
- Analytics page uses `useClientStore((s) => s.activeClientId)` selector pattern consistent with Dashboard/Calendar. Server component does no data fetching; all fetching is in the `AnalyticsDashboard` client component via TanStack Query (avoids RSC re-render loop, project rule).
- `PlatformUnavailableState` is a keyboard-focusable, Escape-dismissible tooltip built inline with no new dependencies (no existing tooltip primitive was found in the project's UI library).
- CSS/SVG sparklines require no new charting library (none installed in frontend/package.json).
- `tests/routers/conftest.py` added with pass-through slowapi stub so router unit tests can import analytics router (existing top-level conftest did not cover slowapi).
- 10 backend tests pass (7 router, 3 service). 11 frontend tests pass. All failures in the full suite are pre-existing and unrelated to this story.

### File List

- `backend/app/routers/analytics.py` (new)
- `backend/app/services/analytics.py` (new)
- `backend/app/schemas/analytics.py` (new)
- `backend/app/main.py` (modified — added analytics router import and include)
- `backend/tests/routers/conftest.py` (new — slowapi pass-through stub)
- `backend/tests/routers/test_analytics.py` (new)
- `frontend/components/layout/nav-items.ts` (modified — Analytics nav item)
- `frontend/hooks/usePostMetrics.ts` (new)
- `frontend/app/(app)/analytics/page.tsx` (new)
- `frontend/app/(app)/analytics/AnalyticsDashboard.tsx` (new)
- `frontend/components/analytics/MetricsSummaryCards.tsx` (new)
- `frontend/components/analytics/PostMetricsTable.tsx` (new)
- `frontend/components/analytics/PlatformUnavailableState.tsx` (new)
- `frontend/__tests__/components/analytics/AnalyticsDashboard.test.tsx` (new)

### Review Findings

- [x] [Review][Patch] Error state missing + isEmpty races when one query errors [frontend/app/(app)/analytics/AnalyticsDashboard.tsx]
- [x] [Review][Patch] Filter chip ARIA broken: role=tablist without tabpanel [frontend/components/analytics/PostMetricsTable.tsx]
- [x] [Review][Patch] onBlur closes tooltip before keyboard user can read it (AC8a) [frontend/components/analytics/PlatformUnavailableState.tsx]
- [x] [Review][Patch] freshest_captured_at computed in Python loop, violates AD-A2 [backend/app/services/analytics.py]
- [x] [Review][Patch] client_id missing from bulk metric queries (defense-in-depth) [backend/app/services/analytics.py]
- [x] [Review][Patch] No refetchInterval: freshness indicator becomes stale [frontend/hooks/usePostMetrics.ts]
- [x] [Review][Patch] fmt() duplicated across MetricsSummaryCards and PostMetricsTable [frontend/lib/formatters.ts (new)]
- [x] [Review][Patch] platform field uses unbounded str in Pydantic schemas [backend/app/schemas/analytics.py]
- [x] [Review][Patch] Sparkline shows blank cell for posts with exactly 1 data point [frontend/components/analytics/PostMetricsTable.tsx]
- [x] [Review][Patch] Suspense wrapper around client component is dead code [frontend/app/(app)/analytics/page.tsx]
- [x] [Review][Defer] Two sequential DB round-trips for best_post lookup [backend/app/services/analytics.py] — deferred, performance optimization not a correctness bug
- [x] [Review][Defer] No pagination on /posts endpoint [backend/app/routers/analytics.py] — deferred, pre-existing scope boundary; add limit/cursor when user base grows
- [x] [Review][Defer] conftest.py sys.modules patch has no yield cleanup [backend/tests/routers/conftest.py] — deferred, low risk with asyncio_mode=auto; revisit if integration tests import real slowapi
- [x] [Review][Defer] Error response double-nested via HTTPException detail dict [backend/app/routers/analytics.py] — deferred, pre-existing project pattern across all routers
- [x] [Review][Defer] formatRelativeTime timezone: naive datetime risk if DB column is non-timestamptz [frontend/app/(app)/analytics/AnalyticsDashboard.tsx] — deferred, asyncpg returns aware datetimes for TIMESTAMPTZ; low real-world risk
- [x] [Review][Defer] brain_dump truncation used as campaign_title (no dedicated title field) [backend/app/services/analytics.py] — deferred, existing project convention; address in future campaign data model refactor
- [x] [Review][Defer] React Query keys deviate from spec ("analytics",clientId,"summary" vs spec shorthand) [frontend/hooks/usePostMetrics.ts] — deferred, implementation keys are more specific and correct; spec used shorthand
- [x] [Review][Defer] Stale data briefly visible when switching active client [frontend/app/(app)/analytics/AnalyticsDashboard.tsx] — deferred, pre-existing TanStack Query behavior
- [x] [Review][Defer] Non-deterministic tiebreak when two posts share max engagements [backend/app/services/analytics.py] — deferred, cosmetic; add secondary ORDER BY published_post_id in future
- [x] [Review][Defer] INNER JOIN silently drops published posts whose campaign was deleted [backend/app/services/analytics.py] — deferred, campaigns are never deleted (data retention story 7-3); revisit if soft-delete introduced
- [x] [Review][Defer] DISTINCT ON captured_at tiebreak non-deterministic for same-timestamp rows [backend/app/services/analytics.py] — deferred, vanishingly rare; add secondary ORDER BY id if dedup issues arise
