---
baseline_commit: a33c7dbb2abab162579d40f2a6543d1c71776b51
---

# Story 25.2: LinkedIn Personal Profile Analytics (member path)

Status: backlog

<!-- BACKLOG: blocked on LinkedIn access. Requires the Community Management API product approved on the app AND the r_member_postAnalytics scope granted (current grant is write-only w_member_social). Flip to ready-for-dev only after both are in place. Depends on 25-1. -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user who publishes to my personal LinkedIn profile,
I want my published personal posts to show real impressions and engagement in the Analytics dashboard,
so that I can measure my personal LinkedIn presence next to my company-page and Meta posts in one place.

## Context

Second LinkedIn story of Epic 25, and the **member/personal-profile** branch of the spine's LinkedIn split (AD-A8). It depends on **25-1** having landed the shared LinkedIn plumbing: `integrations/linkedin_metrics.py`, LinkedIn post-id capture in `services/publishing.py`, the `"linkedin"` platform wired into the harvester + read path + dashboard. This story adds the **member path** on top of that plumbing and flips personal-profile posts from the "not available" state (rendered by 25-1) to real metrics.

**Why this is blocked (and separate from 25-1):** personal-post analytics uses a different endpoint, `memberCreatorPostAnalytics`, which requires **all** of:
1. The **Community Management API** product approved on the LinkedIn app (Development Tier is a build/test sandbox; production requires LinkedIn app review, including a verified company Page, use-case description, and a screencast).
2. The **`r_member_postAnalytics`** scope. The app's current LinkedIn grant is write-only `w_member_social`; the read analytics scope is not held. (The architecture spine names this `r_member_social`; current LinkedIn docs specify `r_member_postAnalytics` for `memberCreatorPostAnalytics` — treat `r_member_postAnalytics` as authoritative and verify at build.)
3. Per-user member consent — each user must reconnect LinkedIn to grant the new scope.

Until all three hold, the member path stays behind `LINKEDIN_MEMBER_METRICS_ENABLED` (default false) and personal posts keep 25-1's AD-A5 "not available" state. This story is the work to do **once approval lands**.

## Acceptance Criteria

1. **Given** the LinkedIn app has the Community Management API product approved and `r_member_postAnalytics` granted, **When** a user connects/reconnects LinkedIn, **Then** the requested OAuth scope set includes `r_member_postAnalytics`, the granted scopes are persisted on the connection (existing `scopes` field), and the app can detect member-analytics capability per connection (mirroring how `_extract_linkedin_target` derives `org_capable` from `w_organization_social`). A connection lacking the scope degrades gracefully (personal posts stay "not available").

2. **Given** a `LINKEDIN_MEMBER_METRICS_ENABLED` feature flag (default false), **When** it is false, **Then** personal-profile posts are recorded/rendered unavailable (`member_metrics_disabled`) exactly as in 25-1; **When** true and the connection has the scope, **Then** personal posts are collected via the member path.

3. **Given** the member branch of `integrations/linkedin_metrics.py`, **When** `fetch` runs for a personal-profile post, **Then** it calls `memberCreatorPostAnalytics` (single-post lookup via the `entity` param, current `li-lms-2026-*` version) with the member's access token, and maps the response to normalized `impressions`/`engagements` + `raw`. It reuses the same `MetricSnapshot` shape and unavailable-reason convention as the org path.

4. **Given** the member metric set, **When** a snapshot is built (AD-A3 convention), **Then** `impressions` <- `IMPRESSION` (fallback `MEMBERS_REACHED`); `engagements` <- `REACTION + COMMENT + RESHARE` (plus `POST_SAVE`, `LINK_CLICKS` where present). All member metrics returned (POST_SEND, FOLLOWER_GAINED_FROM_CONTENT, PROFILE_VIEW_FROM_CONTENT, etc.) are preserved in `raw`. Per-field mapping documented inline.

5. **Given** LinkedIn post-id capture (from 25-1), **When** a personal-profile post is published, **Then** its member post URN + permalink are persisted to `published_posts` (`platform="linkedin"`), so the member path has a poll key. If 25-1 captured only org posts, extend capture to personal posts here.

6. **Given** the harvester sweep, **When** it selects due LinkedIn posts, **Then** it branches on the stored publish target: `organization` -> org path (25-1); personal profile -> member path (this story) when enabled and scoped, else unavailable. Personal posts poll on the same decaying cadence and ~5s LinkedIn stagger. Per-item fault isolation unchanged (AD-A10).

7. **Given** the dashboard (**Paper Style, light-only — no glass, no `dark:`, no `backdrop-blur`; reuse the existing analytics components and tokens**), **When** it renders a personal-profile LinkedIn post, **Then**:
   - **Enabled + connection scoped:** the post shows real impressions, engagements, CSS `Sparkline`, and `ExternalLink` permalink in the **same `PostMetricsTable` row as every other platform** — no bespoke component, no longer the unavailable state. It reuses the LinkedIn `PlatformIcon` (`color="brand"`, already present) and can appear as the `MetricsSummaryCards` best-post with no card change.
   - **Not enabled / scope missing / consent revoked:** the row keeps the existing `isUnavailable` path (`PlatformUnavailableState`) with **reason-specific copy** — add keys to `REASON_COPY` in `PlatformUnavailableState.tsx` (`member_metrics_disabled`, `member_scope_missing`, `consent_revoked`) so users see actionable text, not `GENERIC_COPY`. Backend `unavailable_reason` strings MUST match these keys exactly (per 25-1 AC #9a).
   - **Reconnect hint:** where a scope/consent gap is the cause, surface a reconnect affordance. Preferred: extend `PlatformUnavailableState` to accept an optional action link (to `/connections`) rendered **inside** the existing tooltip, keyboard-focusable, preserving the current tooltip a11y (Escape + outside-click dismiss, `aria-expanded`/`aria-controls`, `shadow-brutal-sm`, `bg-ink text-paper`). Reuse the story 5.8 reconnect-hint copy/pattern; do not invent a new banner. Fallback: copy-only hint ("Reconnect LinkedIn in Connections to enable personal analytics") if the link extension is out of scope for the slice.
   - **A11y (WCAG AA):** metrics rows inherit 24-3's a11y; the only new surfaces are the LinkedIn reason copy (must read clearly for screen readers) and, if added, the tooltip reconnect link (visible focus ring, `aria-label`).

8. **Given** fault isolation (AD-A10), **When** a member fetch fails (scope missing, consent revoked, token expired, rate-limit, malformed payload), **Then** it is caught per-item, logged to Sentry, recorded with a machine-readable `unavailable_reason` (`scope_missing`, `consent_revoked`, `token_expired`, `no_data_yet`, `unknown`), skipped, and the sweep continues. It MUST NOT break the org path, the read path, or the sweep.

9. **Given** the read path, **When** rollups run, **Then** personal-profile LinkedIn posts are included the same way company-page posts are (no new platform value; still `"linkedin"`). Summary totals and best-post logic treat member posts as first-class. No read-path platform call (AD-A1); never 500 on missing data (AD-A10).

10. **Given** tests, **When** they run, **Then** they cover: mapping a sample `memberCreatorPostAnalytics` payload to normalized columns; the feature-flag off/on behavior; scope-missing and consent-revoked unavailable reasons; the harvester target-branch (org vs member) routing; member post-id capture; and dashboard rendering of a personal post as metrics (enabled) vs unavailable (disabled). Append-only invariant preserved.

## Tasks / Subtasks

- [ ] Task 1 — OAuth scope + capability detection (AC: #1, #2)
  - [ ] Add `r_member_postAnalytics` to the LinkedIn authorize scope set (frontend authorize URL + any backend constant). Verify the exact scope string against LinkedIn docs at build.
  - [ ] Persist granted scopes (existing `scopes` field) and derive a `member_metrics_capable` flag (mirror `org_capable` in `_extract_linkedin_target`).
  - [ ] Add `LINKEDIN_MEMBER_METRICS_ENABLED` handling (config already reserved by 25-1/spine; default false).
- [ ] Task 2 — Member metrics integration (AC: #3, #4, #8)
  - [ ] Extend `backend/app/integrations/linkedin_metrics.py` with a member branch calling `memberCreatorPostAnalytics` (single-post `entity` lookup); map per AC #4; unavailable-reason mapping per AC #8.
  - [ ] Keep org and member branches behind one `fetch` entry, selected by the post's publish target.
- [ ] Task 3 — Member post-id capture (AC: #5)
  - [ ] Ensure `_capture_linkedin_post` (from 25-1) covers personal-profile posts; extend if 25-1 scoped capture to org only.
- [ ] Task 4 — Harvester target-branch routing (AC: #6, #8)
  - [ ] In `workers/analytics.py`, branch LinkedIn posts on stored publish target: org -> org path; personal -> member path (flag+scope gated), else record unavailable.
- [ ] Task 5 — Dashboard member rendering (AC: #7)
  - [ ] Enabled+scoped: personal posts render real metrics through the existing `PostMetricsTable` row + `MetricsSummaryCards` best-post (no new component; LinkedIn `PlatformIcon` already present).
  - [ ] Not enabled/scoped: add `REASON_COPY` keys (`member_metrics_disabled`, `member_scope_missing`, `consent_revoked`) in `PlatformUnavailableState.tsx`, matching backend reason strings exactly.
  - [ ] Reconnect hint: extend `PlatformUnavailableState` with an optional keyboard-focusable link to `/connections` inside the tooltip (reuse story 5.8 pattern), preserving existing tooltip a11y; or copy-only fallback. No emoji; Paper Style only (no glass/`dark:`).
- [ ] Task 6 — Tests (AC: #10)

## Dev Notes

- **Blocked-on-access — do not start until confirmed.** This story is un-buildable-to-done without: (a) Community Management API product approved on the LinkedIn app, and (b) `r_member_postAnalytics` granted. Track the LinkedIn access application as the entry gate. The first "task" in practice is completing LinkedIn app review (verified company Page, use-case write-up, screencast).
- **Architecture spine authoritative:** `.../architecture-PersonnaPress-post-analytics-2026-08-16/ARCHITECTURE-SPINE.md`, **AD-A8** (member path gated; feature-flagged off until all of product + scope + consent hold), plus AD-A1/A2/A3/A5/A10 as in 25-1. The spine's "Deferred" section explicitly lists LinkedIn member analytics as the follow-on this story realizes.
- **Depends on 25-1.** Do not duplicate the LinkedIn plumbing; extend `integrations/linkedin_metrics.py`, the harvester LinkedIn branch, the read path, and the dashboard that 25-1 established. This story is additive: the member endpoint + the target-branch + flipping personal rows from unavailable to metrics.
- **Scope-name discrepancy to resolve at build:** spine says `r_member_social`; current LinkedIn docs specify `r_member_postAnalytics` for `memberCreatorPostAnalytics`. Verify the live scope string; prefer `r_member_postAnalytics`. Note that `w_member_social` (already held) is write-only and does NOT authorize analytics reads.
- **Member metrics available (for mapping):** IMPRESSION, MEMBERS_REACHED, REACTION, COMMENT, RESHARE, POST_SAVE, POST_SEND, LINK_CLICKS, FOLLOWER_GAINED_FROM_CONTENT, PROFILE_VIEW_FROM_CONTENT. Map into the shared normalized columns; keep the rest in `raw`.
- **Reconnect UX:** granting a new scope requires each user to reconnect LinkedIn. Reuse the reconnect-hint pattern shipped in story 5.8 (company-page posting) so the dashboard can prompt users whose connection predates the scope.
- **Testing standards:** pytest async with a `memberCreatorPostAnalytics` fixture; flag on/off tests; frontend RTL for metrics-vs-unavailable rendering. No new backend packages (AD-A2).

### UI/UX Consistency (web-uiux-architect review)

- **Design system is Paper Style, NOT the web-uiux-architect glass/dark defaults.** Same constraint as 25-1: light-only, `shadow-brutal`, `font-mono` metrics, ink/paper tokens; no glassmorphism, `backdrop-blur`, `dark:`, or Framer Motion.
- **The whole story is: flip personal rows from "unavailable" to "metrics", plus a reconnect hint.** There is no new page or layout — it reuses `PostMetricsTable`, `MetricsSummaryCards`, `PlatformIcon` (LinkedIn already present), and `PlatformUnavailableState` from 25-1/24-3. The only genuinely new UI is the optional reconnect link inside the existing tooltip.
- **Reason-copy parity (same trap as 25-1):** frontend `REASON_COPY` keys must equal backend `unavailable_reason` strings verbatim (`member_metrics_disabled`, `member_scope_missing`, `consent_revoked`).
- **Reconnect affordance stays inside the existing tooltip pattern.** Do not add a new modal or banner; extend `PlatformUnavailableState` with an optional action link so a member-scope gap is recoverable in one click to `/connections`, matching the story 5.8 reconnect hint. Keep the tooltip's current a11y (Escape/outside-click dismiss, `aria-expanded`/`aria-controls`).
- **Motion:** none — CSS-only, consistent with the rest of the Analytics tab.

### Project Structure Notes

- Modified: `backend/app/integrations/linkedin_metrics.py` (member branch), `backend/app/workers/analytics.py` (target branch), `backend/app/services/publishing.py` (personal-post capture if not covered by 25-1), LinkedIn OAuth scope set (frontend authorize URL + backend constants), `config.py`/`.env.example` (`LINKEDIN_MEMBER_METRICS_ENABLED`), dashboard components (reconnect hint / metrics rendering).
- No migration expected (LinkedIn still `platform="linkedin"`; no new column).

### References

- [Source: .../ARCHITECTURE-SPINE.md#AD-A8] — member path gated on product + scope + consent; feature-flag default false
- [Source: .../ARCHITECTURE-SPINE.md#Deferred] — LinkedIn member/personal-profile analytics as the follow-on
- [Source: story 25-1] — shared LinkedIn plumbing this story extends
- [Source: backend/app/integrations/linkedin.py + routers/publishing.py] — LinkedIn OAuth, scopes persistence, creds blob
- [Source: story 5.8 (enable-linkedin-company-page-posting)] — scope persistence + reconnect-hint pattern to reuse
- [LinkedIn Member Post Statistics](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/members/post-statistics?view=li-lms-2026-06)
- [LinkedIn Community Management App Review](https://learn.microsoft.com/en-us/linkedin/marketing/community-management-app-review?view=li-lms-2026-06)

## Dev Agent Record

### Agent Model Used

(pending)

### Debug Log References

(pending)

### Completion Notes List

(pending)

### File List

(pending)

### Review Findings

(pending)

## Change Log

- 2026-08-20: Story 25.2 drafted as backlog (LinkedIn personal-profile analytics; member path; blocked on Community Management API approval + r_member_postAnalytics scope; depends on 25-1).
- 2026-08-20: web-uiux-architect pass — expanded AC #7 into metrics-vs-unavailable-vs-reconnect rendering against the actual Paper Style components, added `REASON_COPY` parity + tooltip reconnect-link guidance, Task 5 detail, and a UI/UX Consistency dev note; confirmed no glass/dark/motion.
