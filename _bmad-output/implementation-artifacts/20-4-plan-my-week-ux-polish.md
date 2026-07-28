---
baseline_commit: 17b3060
---

# Story 20.4: Plan My Week UX Polish

Status: done

## Story

As a PersonnaPress user,
I want a Roadmap list page, a working week-review grid, and platform-aware guards when planning my week,
so that I can always find and resume a week plan, edit posts with full text, and avoid scheduling to platforms I haven't connected.

## Acceptance Criteria

1. **`/roadmap/` list page (new)**: A new page at `/roadmap/` shows all roadmaps for the active client, ordered by `created_at` descending. Each row shows: week label (e.g., "Week of Aug 4, 2026"), status badge, post count ("7 posts"), and a row-level action link. Status badge styles:
   - `pending` / `generating` → "Generating" (Highlighter bg, Ink text, Border border)
   - `ready` → "Ready to Review" (Highlighter bg, Ink text, Ink border)
   - `approved` → "Scheduled" (success/10 bg, success text, success/20 border)
   - `failed` → "Failed" (danger/10 bg, danger text, danger/20 border)
   Row action link targets:
   - `pending` / `generating` / `ready` → `/roadmap/{id}/review`
   - `approved` → `/calendar`
   - `failed` → `/roadmap/new`
   An "Plan My Week" primary button (Ink fill, White text, 4px Ink hard shadow) in the page header navigates to `/roadmap/new`. Empty state (no roadmaps yet): Graphite dashed border card with copy "No week plans yet." and the same "Plan My Week" button.

2. **Backend: `GET /api/v1/roadmaps`**: New list endpoint in `routers/roadmaps.py`. Auth-required (same `get_current_user` dependency). Accepts optional query param `client_id: UUID` — if provided, filters by `client_id` AND verifies `client.user_id == user_id` (return 404 if not found/not owned). If omitted, returns all roadmaps for the authenticated user. Orders by `created_at DESC`. Response model:
   ```python
   class RoadmapListItem(BaseModel):
       id: uuid.UUID
       status: str
       week_start_date: Optional[date] = None
       campaign_count: int
       created_at: datetime

   class RoadmapListResponse(BaseModel):
       items: list[RoadmapListItem]
   ```
   `campaign_count` is a scalar subquery count of `campaigns.roadmap_id == roadmap.id`. No pagination in v1 (roadmaps are rare, typically ≤ 52/year per client).

3. **Sidebar nav change**: In `frontend/components/layout/nav-items.ts`, change the "Plan My Week" nav item href from `/roadmap/new` to `/roadmap`. The label and icon (`CalendarDays`) remain unchanged. `NavItem` uses `pathname.startsWith(href + "/")` so `/roadmap/new` and `/roadmap/{id}/review` will correctly highlight the nav item as active.

4. **ClientSwitcher path handling**: In `frontend/components/layout/ClientSwitcher.tsx`:
   - Add `"/roadmap"` to `SAFE_BASES` so that `/roadmap` (the list page) stays on the same route when switching clients (the query re-fetches for the new client).
   - Add `"roadmap"` to `COLLAPSE_TO_PARENT` so that deep paths like `/roadmap/{id}/review` collapse to `/roadmap` on client switch (the roadmap belongs to the old client).
   - The existing guard `if (second === "new" && !third) return `/${first}/new`` runs before COLLAPSE_TO_PARENT and ensures `/roadmap/new` stays on `/roadmap/new` on client switch.

5. **Week grid: horizontal scroll layout**: In `frontend/components/roadmap/WeekGrid.tsx`, replace the current grid wrapper:
   ```tsx
   // BEFORE (line 81):
   <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-7 gap-3">
   
   // AFTER:
   <div className="overflow-x-auto pb-3 -mx-4 px-4 lg:-mx-0 lg:px-0">
     <div
       className="grid gap-3"
       style={{
         gridTemplateColumns: "repeat(7, minmax(180px, 1fr))",
         minWidth: "1260px",
       }}
     >
   ```
   Add the matching closing `</div>` for the scroll wrapper after the grid `</div>`. The 180px minimum ensures the card content (platform chip + time + 2-line text + 80px image + 44px buttons + padding) never collapses below a readable width. The `minWidth: 1260px` forces horizontal scroll on viewports narrower than 1260px rather than letting columns shrink further. No changes to the edit drawer — the right-side drawer pattern is correct and stays as-is.

6. **Fix `x_post` / `linkedin_post` truncation at 100 chars**: In `backend/app/routers/roadmaps.py`, in the `get_roadmap_status` handler, remove the `[:100]` slices on lines 192–193:
   ```python
   # BEFORE:
   x_post=c.x_post[:100] if c.x_post else None,
   linkedin_post=c.linkedin_post[:100] if c.linkedin_post else None,
   
   # AFTER:
   x_post=c.x_post,
   linkedin_post=c.linkedin_post,
   ```
   These slices were the sole cause of "100 / 280" in the edit panel. The PostCard uses CSS `line-clamp-2` for visual truncation and needs no data-level cap. The PostEditPanel needs the full text for editing.

7. **Campaign list title fallback for roadmap social posts**: In `frontend/components/campaigns/CampaignList.tsx` (line 127), add a fallback chain for campaigns without `blog_html`:
   ```tsx
   // BEFORE:
   const title = extractTitle(campaign.blog_html);
   
   // AFTER:
   const title =
     extractTitle(campaign.blog_html) ??
     (campaign.x_post ? campaign.x_post.slice(0, 60) + (campaign.x_post.length > 60 ? "…" : "") : null) ??
     (campaign.linkedin_post ? campaign.linkedin_post.slice(0, 60) + (campaign.linkedin_post.length > 60 ? "…" : "") : null) ??
     "Untitled post";
   ```
   Apply the same fallback in `frontend/app/(app)/campaigns/page.tsx` (server component campaign list, line 94) using the same pattern.

8. **Campaign detail H1 fix for roadmap social campaigns**: In `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`, replace the H1 logic (currently `campaign.blog_html ? "Campaign" : "Generating..."`) with a helper that accounts for roadmap social-only campaigns:
   ```tsx
   function getCampaignTitle(campaign: Campaign): string {
     if (campaign.blog_html) return "Campaign";
     if (campaign.roadmap_id) {
       if (campaign.x_post !== null) return "X Post";
       if (campaign.linkedin_post !== null) return "LinkedIn Post";
       return "Social Post";
     }
     return "Generating...";
   }
   // Usage in JSX:
   <h1 className="font-display text-3xl font-bold text-ink text-balance leading-tight">
     {getCampaignTitle(campaign)}
   </h1>
   ```

9. **Blog skeleton suppression for roadmap social campaigns**: In `ApprovalGateClient.tsx`, add a derived boolean at the top of the component body:
   ```tsx
   // A campaign is a roadmap social post if it belongs to a roadmap but has no blog HTML.
   // These campaigns will never have blog_html — skip the Blog Post section entirely.
   const isRoadmapSocialPost = !!campaign.roadmap_id && campaign.blog_html === null;
   ```
   Gate the entire "Blog Post (HTML)" section:
   ```tsx
   // BEFORE: always renders
   <div className="border border-border">
     <div className="px-6 py-4 border-b border-border">
       <h2>Blog Post (HTML)</h2>
     </div>
     {rawBlogHtml ? ... : <GeneratingPlaceholder />}
   </div>
   
   // AFTER: skip section entirely for roadmap social campaigns
   {!isRoadmapSocialPost && (
     <div className="border border-border">
       <div className="px-6 py-4 border-b border-border">
         <h2>Blog Post (HTML)</h2>
       </div>
       {rawBlogHtml ? ... : <GeneratingPlaceholder lines={8} />}
     </div>
   )}
   ```
   The `ImagePanel` remains visible for roadmap social posts — roadmap generation does produce images for social posts, and users can upload their own via the edit panel.

10. **Platform connection guard on `/roadmap/new`**: In `frontend/components/roadmap/PlanMyWeekClient.tsx`:
    - Import `usePlatformConnections` from `@/hooks/usePlatformConnections`.
    - Call it: `const { data: connectionsData } = usePlatformConnections(activeClientId);`
    - Derive: 
      ```tsx
      const connectedPlatforms = new Set(
        (connectionsData?.items ?? [])
          .filter((c) => c.connected)
          .map((c) => c.platform)
      );
      const hasLinkedIn = connectedPlatforms.has("linkedin");
      const hasTwitter = connectedPlatforms.has("x");
      ```
    - Pass `disabled={!hasLinkedIn}` to the LinkedIn `Toggle` and `disabled={!hasTwitter}` to the X/Twitter `Toggle`. The `Toggle` component already accepts and applies a `disabled` prop (renders with `cursor-not-allowed opacity-50`).
    - When a platform toggle is disabled due to missing connection, render a small inline note below it (not a tooltip — always visible):
      ```tsx
      {!hasLinkedIn && (
        <p className="font-body text-xs text-graphite">
          Not connected.{" "}
          <Link href={`/clients/${activeClientId}/connections`} className="underline hover:text-ink">
            Connect LinkedIn
          </Link>
        </p>
      )}
      ```
      Apply same pattern for X. The note only renders when `activeClientId` is set and connections data has loaded (`connectionsData` is defined). While loading (connectionsData is undefined), toggles remain enabled — the guard is advisory, not a hard block during load.
    - Blog toggle needs no connection check (blog posts go to headless delivery / GitHub).

## Tasks / Subtasks

- [x] Task 1: Backend roadmap list endpoint (AC: 2)
  - [x] `backend/app/routers/roadmaps.py`: Add `RoadmapListItem` and `RoadmapListResponse` Pydantic models
  - [x] Add `GET /api/v1/roadmaps` handler — auth-required, optional `client_id` query param, filter by user_id, optional client_id filter with ownership check, count campaigns via subquery, order by `created_at DESC`
  - [x] No test required for this endpoint (consistent with other list endpoints in the project that skip integration tests; the approve and generate endpoints also have no integration tests)

- [x] Task 2: Backend text truncation fix (AC: 6)
  - [x] `backend/app/routers/roadmaps.py:192-193`: Remove `[:100]` slice from `x_post` and `linkedin_post` in `CampaignSummary` construction

- [x] Task 3: Frontend types and API client (AC: 1, 2)
  - [x] `frontend/lib/types.ts`: Add `RoadmapListItem` interface and `RoadmapListResponse` interface (matching backend models)
  - [x] `frontend/lib/api.ts`: Add `roadmapsApi.list(clientId?: string)` method — `apiFetch<RoadmapListResponse>("/roadmaps" + (clientId ? `?client_id=${clientId}` : ""))`

- [x] Task 4: Roadmap list page (AC: 1, 3)
  - [x] `frontend/app/(app)/roadmap/page.tsx`: New server component — reads session cookie, redirects to `/login` if missing; renders `<RoadmapListClient />`
  - [x] `frontend/components/roadmap/RoadmapListClient.tsx`: New client component. Uses `useClientStore` for `activeClientId`. TanStack Query: `queryKey: ["roadmaps", activeClientId]`, `queryFn: () => roadmapsApi.list(activeClientId ?? undefined)`, `staleTime: 30_000`, `enabled: !!activeClientId`. Renders: page header with H1 "Roadmap" + "Plan My Week" primary button → `/roadmap/new`; roadmap rows with week label, status badge, post count, action link; empty state card.
  - [x] `frontend/components/layout/nav-items.ts`: Change `href: "/roadmap/new"` to `href: "/roadmap"` for the "Plan My Week" nav item

- [x] Task 5: ClientSwitcher path handling (AC: 4)
  - [x] `frontend/components/layout/ClientSwitcher.tsx`: Add `"/roadmap"` to `SAFE_BASES` set; add `"roadmap"` to `COLLAPSE_TO_PARENT` set

- [x] Task 6: Week grid layout fix (AC: 5)
  - [x] `frontend/components/roadmap/WeekGrid.tsx:81`: Replace grid wrapper with horizontal scroll container + inline style grid as specified in AC 5

- [x] Task 7: Campaign list title fallbacks (AC: 7)
  - [x] `frontend/components/campaigns/CampaignList.tsx:127`: Add fallback chain for campaigns without `blog_html`
  - [x] `frontend/app/(app)/campaigns/page.tsx:94`: Same fallback chain in the server-rendered campaigns page

- [x] Task 8: Campaign detail fixes for roadmap social posts (AC: 8, 9)
  - [x] `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`: Add `isRoadmapSocialPost` derived bool; add `getCampaignTitle()` helper; update H1 to use helper; wrap Blog Post section in `{!isRoadmapSocialPost && (...)}` guard

- [x] Task 9: Platform connection guard on `/roadmap/new` (AC: 10)
  - [x] `frontend/components/roadmap/PlanMyWeekClient.tsx`: Add `usePlatformConnections`, derive `hasLinkedIn` / `hasTwitter`, pass `disabled` to toggles, render inline "Not connected. Connect [Platform]" note

## Dev Notes

### RSC Loop Prevention — No API Calls in Server Components
Per `project-context.md`: never put API calls in server components that could loop. All data fetching in the new `/roadmap/page.tsx` must go in `RoadmapListClient.tsx` (TanStack Query). The server component only reads the session cookie and redirects if absent. Pattern: identical to `RoadmapReviewPage` (`frontend/app/(app)/roadmap/[id]/review/page.tsx`).

### NavItem Active State with New `/roadmap` Href
`NavItem.tsx:18`: `active = pathname === href || pathname.startsWith(href + "/")`. Changing the nav item href from `/roadmap/new` to `/roadmap` means the nav item correctly highlights for ALL roadmap sub-paths: `/roadmap` (list), `/roadmap/new` (create), `/roadmap/{id}/review` (review). No changes needed to `NavItem`.

### ClientSwitcher: Order of Guards Matters
In `getTargetPath` (`ClientSwitcher.tsx:15`), the existing guard `if (second === "new" && !third) return \`/${first}/new\`` runs at line 26, BEFORE the `COLLAPSE_TO_PARENT` check at line 30. So adding `"roadmap"` to `COLLAPSE_TO_PARENT` will:
- `/roadmap` → falls through to SAFE_BASES check (not caught by COLLAPSE_TO_PARENT because `second` is undefined) → stays on `/roadmap` ✓
- `/roadmap/new` → caught by `second === "new" && !third` guard → stays on `/roadmap/new` ✓  
- `/roadmap/{id}/review` → caught by COLLAPSE_TO_PARENT → collapses to `/roadmap` ✓

### Backend `campaign_count` Subquery
Use SQLAlchemy scalar subquery to avoid N+1:
```python
from sqlalchemy import func, select as sa_select
from app.db.repositories.models import Campaign, Roadmap

count_subq = (
    sa_select(func.count())
    .where(Campaign.roadmap_id == Roadmap.id)
    .correlate(Roadmap)
    .scalar_subquery()
)

stmt = (
    select(Roadmap, count_subq.label("campaign_count"))
    .where(Roadmap.user_id == user_id)
    # + optional client_id filter
    .order_by(Roadmap.created_at.desc())
)
```
Access `campaign_count` from each row tuple: `row.campaign_count`.

### Text Truncation Root Cause — Do Not Add Back
The `[:100]` slices in `roadmaps.py:192-193` were apparently added to reduce payload size for card previews. Do NOT re-add them or add a separate `preview` field — the `line-clamp-2` CSS in `PostCard.tsx:90` handles visual truncation. The full text must be available for `PostEditPanel`.

### `isRoadmapSocialPost` Detection Logic
A campaign is a roadmap social post when:
- `campaign.roadmap_id !== null` — belongs to a roadmap
- `campaign.blog_html === null` — has no blog HTML (social-only)

This condition is permanent: social roadmap campaigns will never have `blog_html`. A regular (non-roadmap) campaign in the generating state has `campaign.roadmap_id === null` and `blog_html === null` — correctly excluded from this guard. The `GeneratingPlaceholder` skeleton therefore only shows for non-roadmap campaigns with `blog_html === null` AND `jobIsActive`.

### Platform Connection Toggles — Load State Behavior
While `connectionsData` is undefined (initial load), `hasLinkedIn` and `hasTwitter` default to `false` (no connected platforms found). This means toggles would briefly appear disabled on first load. To avoid flicker: derive enabled state only when `connectionsData` is defined:
```tsx
const hasLinkedIn = connectionsData ? connectedPlatforms.has("linkedin") : true;
const hasTwitter = connectionsData ? connectedPlatforms.has("x") : true;
```
This keeps toggles enabled during load and only disables once data confirms no connection exists.

### PlatformConnection Type
`usePlatformConnections` returns `{ data: { items: PlatformConnection[] } }`. From `publishingApi.listConnections` — the `PlatformConnection` type has `platform: Platform` and `connected: boolean`. `Platform` = `"wordpress" | "webflow" | "x" | "linkedin"`. Use `"x"` (not `"twitter"`) for the X platform key — matches `Platform` type in `frontend/lib/types.ts:17`.

### Roadmap List Page Route Conflict
`frontend/app/(app)/roadmap/` currently contains two sub-folders: `[id]/` and `new/`. Adding a `page.tsx` at `frontend/app/(app)/roadmap/page.tsx` creates the list page at `/roadmap/`. This does NOT conflict with `[id]/review/page.tsx` or `new/page.tsx` — Next.js App Router correctly distinguishes a folder-level `page.tsx` from dynamic and static sub-segments.

### Files Being Modified / Created

| File | Change |
|------|--------|
| `backend/app/routers/roadmaps.py` | Add `RoadmapListItem`, `RoadmapListResponse` models; add `GET /api/v1/roadmaps` handler; remove `[:100]` truncation at lines 192-193 |
| `frontend/lib/types.ts` | Add `RoadmapListItem`, `RoadmapListResponse` interfaces |
| `frontend/lib/api.ts` | Add `roadmapsApi.list()` method |
| `frontend/app/(app)/roadmap/page.tsx` | NEW: server component for roadmap list |
| `frontend/components/roadmap/RoadmapListClient.tsx` | NEW: client component with TanStack Query, roadmap rows, empty state |
| `frontend/components/layout/nav-items.ts` | Change "Plan My Week" href from `/roadmap/new` to `/roadmap` |
| `frontend/components/layout/ClientSwitcher.tsx` | Add `"/roadmap"` to SAFE_BASES; add `"roadmap"` to COLLAPSE_TO_PARENT |
| `frontend/components/roadmap/WeekGrid.tsx` | Replace grid wrapper with scroll container + inline style |
| `frontend/components/campaigns/CampaignList.tsx` | Add title fallback chain |
| `frontend/app/(app)/campaigns/page.tsx` | Add title fallback chain (server component) |
| `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` | Add `isRoadmapSocialPost`, `getCampaignTitle()`, update H1, gate Blog Post section |
| `frontend/components/roadmap/PlanMyWeekClient.tsx` | Add `usePlatformConnections`, derive connection booleans, disable toggles, render notes |

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- All 10 ACs satisfied across 9 tasks.
- Backend: Added `GET /api/v1/roadmaps` with scalar subquery for campaign_count; removed `[:100]` truncation from x_post/linkedin_post in get_roadmap_status.
- Frontend: New `/roadmap/` list page (server component + RoadmapListClient with TanStack Query); nav updated from `/roadmap/new` to `/roadmap`; ClientSwitcher SAFE_BASES + COLLAPSE_TO_PARENT updated; WeekGrid horizontal scroll layout; CampaignList fallback title chain; ApprovalGateClient isRoadmapSocialPost guard + getCampaignTitle helper; PlanMyWeekClient platform connection guard with inline notes.
- TypeScript check shows only pre-existing test errors (not caused by this story).

### File List

- `backend/app/routers/roadmaps.py`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `frontend/app/(app)/roadmap/page.tsx` (new)
- `frontend/components/roadmap/RoadmapListClient.tsx` (new)
- `frontend/components/layout/nav-items.ts`
- `frontend/components/layout/ClientSwitcher.tsx`
- `frontend/components/roadmap/WeekGrid.tsx`
- `frontend/components/campaigns/CampaignList.tsx`
- `frontend/app/(app)/campaigns/page.tsx`
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`
- `frontend/components/roadmap/PlanMyWeekClient.tsx`

### Review Findings

- [x] [Review][Patch] getCampaignTitle uses `!== null` for x_post/linkedin_post — returns "X Post" for empty-string post; change to truthy check [frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx]
- [x] [Review][Patch] RoadmapListClient shows "No week plans yet." when no client is selected — add early return with "Select a client" guidance [frontend/components/roadmap/RoadmapListClient.tsx]
- [x] [Review][Patch] RoadmapListClient has no error state — query error silently shows empty state with no feedback [frontend/components/roadmap/RoadmapListClient.tsx]
- [x] [Review][Patch] PlanMyWeekClient: config.linkedinOn/twitterOn not reset when connections load as disconnected — can submit generation for unconnected platform [frontend/components/roadmap/PlanMyWeekClient.tsx]
- [x] [Review][Dismiss] ClientSwitcher /new guard not scoped to COLLAPSE_TO_PARENT paths — on review, the guard is intentionally general (creation forms always stay put), consistent with the comment in the code
- [x] [Review][Defer] No LIMIT on list_roadmaps query [backend/app/routers/roadmaps.py] — deferred, spec explicitly says no pagination (roadmaps rare, ≤52/year)
- [x] [Review][Defer] connectionsData permanent fetch error keeps toggles enabled [frontend/components/roadmap/PlanMyWeekClient.tsx] — deferred, spec says guard is advisory not a hard block
- [x] [Review][Defer] Backdrop click on WeekGrid drawer while PostEditPanel save in-flight closes with no feedback [frontend/components/roadmap/WeekGrid.tsx] — deferred, minor UX edge case, out of scope
- [x] [Review][Defer] Title fallback chain duplicated verbatim in CampaignList.tsx and campaigns/page.tsx — deferred, DRY concern, not a bug

## Change Log

- 2026-07-27: Story implemented (Date: 2026-07-27). All 9 tasks complete, all 10 ACs satisfied. New GET /api/v1/roadmaps endpoint, x_post/linkedin_post truncation fix, new /roadmap list page, nav href change, ClientSwitcher guards, WeekGrid scroll layout, campaign title fallbacks, roadmap social post detection/gating in ApprovalGateClient, platform connection guard in PlanMyWeekClient.
