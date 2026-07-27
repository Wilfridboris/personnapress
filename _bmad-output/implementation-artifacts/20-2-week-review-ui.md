---
baseline_commit: d4064e97100aa51e3d63d4a2d1c60683e4cfdb9b
---

# Story 20.2: Week Review UI

Status: done

## Story

As a PersonnaPress user,
I want a "Plan My Week" page where I configure my weekly cadence, dump my ideas, and then review a calendar-style grid of all generated posts before approving everything at once,
so that I can fill an entire week of content with minimal friction and zero repetitive clicking.

## Acceptance Criteria

1. **Sidebar nav entry**: Sidebar navigation has a "Plan My Week" link between "Brain Dump" and "Calendar" using a `CalendarDays` Lucide icon; navigates to `/roadmap/new`; follows existing active-nav Paper Style (Highlighter bg, Ink text, 2px left Ink border when active).

2. **Settings panel on /roadmap/new**: A collapsible settings panel card (White fill, 1px Border, rounded-none) at the top of the page. Section label "THIS WEEK'S PLAN" (Inter, 12px, uppercase, tracked, Graphite). Contains:
   - LinkedIn toggle (ON/OFF) + number spinner when ON (1-7, default 3)
   - X/Twitter toggle (ON/OFF) + number spinner when ON (1-14, default 5)
   - Blog toggle (ON/OFF, default ON)
   - Panel collapses after first save; a "Change plan" secondary text button re-opens it
   - Values pre-populated from `client.roadmap_config` on load (via TanStack Query `GET /api/v1/clients/{id}`)

3. **Image generation toggle**: Within settings panel, an "Generate images" toggle (ON/OFF). When ON and quota > 0: shows `"You have N image generations remaining this month."` in Graphite Inter 12px. When ON but quota < total posts: shows `"You have N images remaining. The first N posts will include a generated image."` styled with Highlighter background + Ink border (1px) warning box. When quota = 0: toggle locked to OFF, shows `"No image generations remaining this cycle."` + inline upgrade link to `/pricing`. Values from TanStack Query on `/api/v1/subscriptions/status`.

4. **Roadmap quota warning**: If remaining roadmap credits = 0 before generation, show a Danger-bordered card `"You've reached your roadmap limit for this billing cycle."` with upgrade link. Disable "Plan My Week" button. If remaining campaigns would be insufficient (roadmap would exceed campaign limit — does not apply to Agency), show Highlighter warning box but do not block.

5. **Brain Dump input**: JetBrains Mono auto-expanding textarea (same component as existing `/brain-dump` page), min-height 160px, bottom-border-only Paper Style. Label: `"What's on your mind this week?"` (Inter, Graphite, 12px, uppercase, tracked above the input). Character counter below: `"N / 10,000 characters"`. Submit button disabled below 20 characters.

6. **"Plan My Week" primary button**: Ink fill, White text, 4px Ink hard shadow, rounded-none, full-width on mobile. On click: saves `roadmap_config` via `PATCH /api/v1/clients/{id}/roadmap-config`, then `POST /api/v1/roadmaps`; navigates to `/roadmap/{id}/review` immediately and begins polling.

7. **Generation polling on /roadmap/[id]/review**: TanStack Query polls `GET /api/v1/roadmaps/{id}` every 2 seconds while `status === "generating" || status === "pending"`. While polling, shows typewriter animation (reuse existing typewriter component) with cycling messages: `"Analyzing your voice profile..."` → `"Drafting LinkedIn posts..."` → `"Drafting X posts..."` → `"Drafting blog post..."` (only if blog enabled) → `"Generating images..."` (only if generate_images=true) → `"Done."`. On `status === "ready"`, query refetch interval stops and grid renders. On `status === "failed"`, shows error card with roadmap `error_message` and a "Try again" link back to `/roadmap/new`.

8. **Week review grid**: 7-column grid (Mon-Sun) at `lg`, 3-column at `md` (Mon-Wed | Thu-Sat | Sun), single column scrollable at `<768px`. Column headers: day abbreviation + date (`"Mon Jul 28"`, Inter 12px, uppercase, tracked, Graphite). Empty day cells show a Graphite dashed-border placeholder `"No posts this day"`.

9. **Post card**: White fill, 1px `Border` (#E5E5E5), rounded-none, `hover:shadow-[4px_4px_0px_#111111]` transition (CSS transition, no Framer Motion). Card contains top-to-bottom:
   - Platform chip: Lucide icon (for LinkedIn use `Linkedin`, for X use `Twitter`, for blog use `BookOpen`) + platform label, Inter 12px, uppercase, Graphite
   - Scheduled time chip: `"Mon 9:00 AM"`, same style
   - Post preview: 2-line text preview (`line-clamp-2`), Inter 15px, Ink
   - Image area (80px tall): if `image_url` present — `<Image>` thumbnail (next/image, 16:9, objectFit cover, rounded-none); if no image — dashed 1px `Border` area with `UploadCloud` Lucide icon + `"Add your own image"` text, Graphite, centered
   - Action row: `[Edit]` secondary button + `[Remove]` secondary button, both `rounded-none`, 1px Ink border, Inter 12px uppercase tracked

10. **Remove behavior**: Clicking [Remove] sets that card to a removed state: card gets `opacity-50`, post preview text gets `line-through` style, a `"REMOVED"` badge (Inter, 12px, uppercase, tracked, Border fill, Graphite text) appears in top-right corner of card; action row replaced by `[Undo]` secondary button. Removed posts are excluded from the approve count in the sticky footer. Removal is client-side only until "Approve All & Schedule" is clicked (excluded_campaign_ids are sent in the approve payload).

11. **Edit panel**: Clicking [Edit] on a card opens an inline panel that slides open below that card (CSS `max-height` transition from 0 to auto via a measured ref — use `AnimatePresence` with `motion.div` height animation here since CSS `max-height: auto` transition cannot animate to unknown height). Panel contains:
    - Header: platform icon + `"Editing [Platform] post"` (Playfair 18px, Ink)
    - Full post textarea (JetBrains Mono, same style as Brain Dump), auto-expanding
    - Character counter: `"N / 280"` for X, `"N / 1,300"` for LinkedIn; counter turns Danger color at 95% capacity
    - Image section: current thumbnail (if any) with `[Replace image]` secondary button; OR dashed placeholder with `[Upload your own image]` secondary button; file input (`accept="image/png,image/jpeg,image/webp"`, max 5MB, same pattern as existing image upload in 12-5); no quota cost for user-uploaded images
    - Footer: `[Save changes]` primary + `[Cancel]` secondary; saving updates the local campaign state (optimistic); calls `PATCH /api/v1/campaigns/{id}` for post text; calls `POST /api/v1/campaigns/{id}/upload-image` for image replacement
    - `AnimatePresence` for unmount animation when panel closes

12. **Sticky footer**: Fixed bottom bar (White bg, 1px top Border, no shadow). Left side: `"N posts selected"` (N = non-removed count, Inter, Graphite, 15px). Right side: `[Approve All & Schedule]` primary button (Ink fill, White text, 4px hard shadow). Footer only visible on `/roadmap/{id}/review` page.

13. **Account page roadmap usage**: `/account/page.tsx` shows a new usage line `"Roadmaps: {roadmaps_used} / {fmtLimit(plan_limits.roadmaps)}"` between "Campaigns" and "Image generations" usage lines. `fmtLimit` already handles UNLIMITED display (sentinel 999_999 → "Unlimited"). Data comes from existing `GET /api/v1/subscriptions/status` response (now includes `roadmaps_used` and `plan_limits.roadmaps` from story 20-1).

14. **No RSC data fetching**: ALL data fetching on `/roadmap/new` and `/roadmap/[id]/review` pages is done via TanStack Query in client components. Server components only read the session cookie for `clientId`/`userId`. This follows the RSC loop prevention pattern in `project-context.md` (Turbopack dev mode re-render issue).

15. **Paper Style compliance**: No emojis anywhere. No exclamation marks in any copy. All new components use Paper bg (`#F9F9F6`), Ink (`#111111`), Graphite (`#555555`), Border (`#E5E5E5`), Highlighter (`#FFF1B8`) for active/warning states, Danger (`#8B0000`) for errors, sharp corners (rounded-none) throughout. Playfair Display for H1/H2, Inter for all labels and body, JetBrains Mono only for Brain Dump textarea and post edit textarea.

16. **Accessibility**: All icon-only buttons have `aria-label`. Platform chip icons have `aria-hidden="true"`. Edit panel has `role="region"` and `aria-label="Edit [platform] post"`. "Plan My Week" button has `aria-disabled` when disabled. Sticky footer "Approve All & Schedule" button is `aria-live`-announced when count changes. All interactive elements minimum 44px touch target height.

## Tasks / Subtasks

- [x] Task 1: Routing and nav (AC: 1)
  - [x] Add `CalendarDays` nav item to sidebar between Brain Dump and Calendar in nav constants/component
  - [x] Create `frontend/app/(app)/roadmap/new/page.tsx` (server component — reads session, passes clientId to client component)
  - [x] Create `frontend/app/(app)/roadmap/[id]/review/page.tsx` (server component — reads session, passes roadmapId + clientId to client component)
  - [x] Add frontend API client functions: `createRoadmap(payload)`, `getRoadmap(id)`, `approveRoadmap(id, excludedIds)`, `patchRoadmapConfig(clientId, config)` to `frontend/lib/api.ts`

- [x] Task 2: Plan My Week page client component (AC: 2, 3, 4, 5, 6)
  - [x] `PlanMyWeekClient.tsx` (`'use client'`):
    - TanStack Query for `GET /api/v1/subscriptions/status` (for quota display)
    - TanStack Query for `GET /api/v1/clients/{id}` (for roadmap_config pre-population)
    - Settings panel component with cadence toggles + spinners; collapses/expands via local state
    - Image toggle with quota math: `remaining = plan_limits.image_gens - image_gen_used`; show correct warning/locked state
    - Roadmap quota check: `remaining_roadmaps = plan_limits.roadmaps - roadmaps_used`; block button if 0
    - Brain Dump textarea (reuse existing component if extracted, or inline same pattern)
    - Character counter below textarea
    - "Plan My Week" primary button: disabled < 20 chars or roadmap limit hit; on click: PATCH roadmap-config → POST /roadmaps → navigate to `/roadmap/{roadmapId}/review`

- [x] Task 3: Week review grid (AC: 7, 8, 9, 10)
  - [x] `RoadmapReviewClient.tsx` (`'use client'`):
    - TanStack Query `getRoadmap(id)` with `refetchInterval: (data) => data?.status === "ready" ? false : 2000`
    - While pending/generating: render `TypewriterAnimation` component (existing) with roadmap-specific message sequence
    - On ready: render week grid
  - [x] `WeekGrid.tsx`: 7-column CSS grid (`grid-cols-7 lg:grid-cols-7 md:grid-cols-3 grid-cols-1`); column headers with day + date
  - [x] `PostCard.tsx`: all states (default, removed); platform chip, time chip, preview, image area, action buttons; `hover:shadow-[4px_4px_0px_#111111] transition-shadow duration-150`
  - [x] Remove logic: local `removedIds: Set<string>` state; `[Remove]` adds to set; `[Undo]` removes from set; card renders removed state based on set membership

- [x] Task 4: Edit panel with AnimatePresence (AC: 11)
  - [x] `PostEditPanel.tsx` (`'use client'`): AnimatePresence owned by PostCard with `motion.div` height animation — PostEditPanel remounts fresh on each open (avoids useEffect-setState cascading render issue)
  - [x] Full post textarea (JetBrains Mono, same bottom-border-only pattern)
  - [x] Char counter with Danger color at 95% threshold (same pattern as existing `4-3-social-post-editing`)
  - [x] Image upload: `<input type="file" accept="image/png,image/jpeg,image/webp">`, max 5MB client-side check, preview on select, calls `PATCH /api/v1/campaigns/{id}` for text + image upload via `imagesApi` + `patchImage` for image
  - [x] Save: optimistic update to local campaign state in parent; API call in background; on error: revert optimistic update + show error

- [x] Task 5: Sticky footer and account page (AC: 12, 13, 14)
  - [x] Sticky footer: fixed bottom-0 bar; `N posts selected` count (non-removed); `[Approve All & Schedule]` primary; on click calls `POST /api/v1/roadmaps/{id}/approve` with `{excluded_campaign_ids: [...removedIds]}` (story 20-3 endpoint); on success: `router.push('/calendar')`
  - [x] Account page: add `"Roadmaps: {roadmaps_used} / {fmtLimit(plan_limits.roadmaps)}"` line in the usage section; `fmtLimit` already defined in `account/page.tsx` — reuse it

## Dev Notes

### Framer Motion Usage Justification
`AnimatePresence` + `motion.div` height animation is used ONLY for the PostEditPanel slide-open/close. CSS `max-height: auto` genuinely cannot animate smoothly to unknown height. All other interactions (card hover shadow, button active state, fade-in on grid render) use CSS transitions. This follows the Motion Decision Framework in the web-uiux-architect spec.

### RSC Pattern (project-context.md)
Server components on `/roadmap/new` and `/roadmap/[id]/review` must ONLY: read the session JWT cookie to extract `user_id`/`client_id`, then pass those as props to client components. ALL API calls go in client components via TanStack Query. No `async` data fetching in server components on these routes.

### Typewriter Component Reuse
The existing typewriter animation from the Brain Dump generation flow (UX-DR10) is reused here. The component accepts a `messages: string[]` prop that cycles. For roadmaps, pass the appropriate sequence based on what was requested (skip "Drafting blog post..." if `skip_blog=true`, skip "Generating images..." if `generate_images=false`).

### Post Card Image Area
For the image area: if `image_url` from `GET /api/v1/roadmaps/{id}` is present for a campaign, render `<Image src={image_url} ... />` with `width=240 height=135` (16:9 at card width). If NULL: render the dashed placeholder. On image upload in edit panel, update local state immediately (optimistic) — do not wait for API round-trip to show the thumbnail.

### Character Limits per Platform
- X: 280 characters (matches existing counter in `4-3-social-post-editing`)
- LinkedIn: 1,300 characters (matches existing counter)
- Blog title: no counter needed in roadmap review

### Existing Campaign Edit Reuse
The `PATCH /api/v1/campaigns/{id}` endpoint for updating `x_post`/`linkedin_post` already exists (used in Approval Gate story 4-3). The `upload-image` endpoint already exists (story 12-5). No new backend endpoints needed for the edit panel in this story.

### Files Being Modified / Created

| File | Change |
|------|--------|
| `frontend/app/(app)/layout.tsx` (or sidebar component) | Add "Plan My Week" nav item with CalendarDays icon |
| `frontend/app/(app)/roadmap/new/page.tsx` | New server component page |
| `frontend/app/(app)/roadmap/[id]/review/page.tsx` | New server component page |
| `frontend/components/roadmap/PlanMyWeekClient.tsx` | New client component |
| `frontend/components/roadmap/RoadmapReviewClient.tsx` | New client component |
| `frontend/components/roadmap/WeekGrid.tsx` | New component |
| `frontend/components/roadmap/PostCard.tsx` | New component |
| `frontend/components/roadmap/PostEditPanel.tsx` | New component with AnimatePresence |
| `frontend/components/roadmap/StickyApproveFooter.tsx` | New component |
| `frontend/app/(app)/account/page.tsx` | Add roadmaps_used usage line |
| `frontend/lib/api.ts` | Add createRoadmap, getRoadmap, approveRoadmap, patchRoadmapConfig |

### Review Findings

- [x] [Review][Patch] next/image used with blob: URL during upload preview — crashes in Next.js 16; use plain `<img>` for blob URLs [PostEditPanel.tsx:163]
- [x] [Review][Patch] weekStartDate ISO date string parsed as UTC — column headers off by one day for UTC- timezone users [WeekGrid.tsx:9]
- [x] [Review][Patch] configPopulated ref not reset on activeClientId change — switching clients shows stale roadmap config [PlanMyWeekClient.tsx:useEffect]
- [x] [Review][Patch] uploadData.url not validated before PATCH on image upload — empty url silently patches campaign with blank image [api.ts:126]
- [x] [Review][Patch] Image generation toggle not truly disabled when quota=0 — no `disabled` prop; keyboard users can still interact [PlanMyWeekClient.tsx]
- [x] [Review][Patch] "Removed" badge DOM text is "Removed" not "REMOVED" — CSS uppercase hides it visually; screen readers announce wrong text [PostCard.tsx:70]
- [x] [Review][Patch] Account page Roadmaps usage line inserted after Clients; AC13 requires it between Campaigns and Image generations [account/page.tsx:80]
- [x] [Review][Patch] Image quota warning branch (0<quota<totalPosts) suppresses remaining-count text; spec requires both count and warning [PlanMyWeekClient.tsx]
- [x] [Review][Patch] blog_enabled from roadmap_config can be undefined — falls back to false instead of default ON [PlanMyWeekClient.tsx]
- [x] [Review][Patch] Empty campaigns array on ready roadmap renders blank 7-column grid with no empty-state feedback [RoadmapReviewClient.tsx]
- [x] [Review][Patch] Cancel button not disabled during file upload — can close panel mid-upload losing progress [PostEditPanel.tsx:220]
- [x] [Review][Patch] Approve button double-click race before isApproving state update reflects in DOM [StickyApproveFooter.tsx:17]
- [x] [Review][Defer] Blog title edit (blog_full) updates local state only — campaignsApi.patch endpoint does not expose blog_title field [PostEditPanel.tsx:60] — deferred, backend gap (20-3 scope)
- [x] [Review][Defer] No polling timeout on /roadmap/[id]/review — backend stall would run 2s poll indefinitely with no escape path [RoadmapReviewClient.tsx] — deferred, backend concern
- [x] [Review][Defer] 401 from expired session not redirected in client components — pre-existing project pattern [RoadmapReviewClient.tsx] — deferred, pre-existing
- [x] [Review][Defer] Orphaned storage asset when image PATCH fails after upload succeeds — error is surfaced to user but file remains in storage [api.ts] — deferred, backend concern

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Used `subscriptionsApi.getMe()` (`/subscriptions/me`) instead of `/subscriptions/status` for quota display since only `/me` returns the full `SubscriptionResponse` including `roadmaps_used` and `plan_limits.roadmaps` (backend `getStatus()` only returns `{status: string}`).
- `AnimatePresence` moved from `PostEditPanel` to `PostCard` wrapping a `motion.div`. This causes `PostEditPanel` to remount fresh on each open (state initializes from props), eliminating the need for a `useEffect`-setState pattern that eslint `react-hooks/set-state-in-effect` would reject.
- `Linkedin` and `Twitter` icons don't exist in lucide-react v1.18.0. Used `AtSign` for LinkedIn and `Share2` for X (matching existing `PlatformIcon` pattern for X).
- Backend `ClientResponse` schema extended with `roadmap_config: Optional[dict] = None` so `GET /api/v1/clients/{id}` can return saved roadmap config for pre-population.
- `POST /api/v1/roadmaps/{id}/approve` is a story 20-3 endpoint (not yet implemented). The approve button in `StickyApproveFooter` will 404 until 20-3 ships.
- Settings panel config merged into a single `PlanConfig` state object (`setConfig({...})`) to avoid multiple setState calls in `useEffect`.

### File List

- `frontend/components/layout/nav-items.ts` (modified)
- `frontend/app/(app)/roadmap/new/page.tsx` (new)
- `frontend/app/(app)/roadmap/[id]/review/page.tsx` (new)
- `frontend/components/roadmap/PlanMyWeekClient.tsx` (new)
- `frontend/components/roadmap/RoadmapReviewClient.tsx` (new)
- `frontend/components/roadmap/WeekGrid.tsx` (new)
- `frontend/components/roadmap/PostCard.tsx` (new)
- `frontend/components/roadmap/PostEditPanel.tsx` (new)
- `frontend/components/roadmap/StickyApproveFooter.tsx` (new)
- `frontend/app/(app)/account/page.tsx` (modified)
- `frontend/lib/api.ts` (modified)
- `frontend/lib/types.ts` (modified)
- `backend/app/schemas/client.py` (modified)
- `backend/app/routers/clients.py` (modified)
