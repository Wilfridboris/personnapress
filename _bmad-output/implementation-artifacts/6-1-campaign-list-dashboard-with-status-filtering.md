---
baseline_commit: 1f46f6c60a016534fa9a2c888308b0b6e2de4268
---

# Story 6.1: Campaign List Dashboard with Status Filtering

Status: done

## Story

As an authenticated user,
I want to see all my campaigns for the active client in a filterable list, ordered from newest to oldest,
so that I can quickly find and access any campaign regardless of its current status.

## Acceptance Criteria

1. **Given** an authenticated user navigates to `/dashboard`, **When** the page loads with the active Client set, **Then** the Campaign list is fetched via `GET /api/v1/campaigns?client_id={activeClientId}&page=1&per_page=20`; results are ordered by `created_at` descending (newest first); up to 20 campaigns are shown per page with pagination controls (previous/next) if more than 20 exist.

2. **Given** the Campaign list renders, **When** a Campaign row is displayed, **Then** each row shows: campaign title (derived from the blog post H1, truncated at 60 characters with an ellipsis), the Campaign's Status Badge (one of five variants: PENDING APPROVAL, APPROVED, PUBLISHED, REJECTED, FAILED), creation date formatted with `Intl.DateTimeFormat`, and the publish date (if status is `published`); platform icons (WP, Webflow, X, LinkedIn icons) are shown next to the date for published campaigns.

3. **Given** a user clicks anywhere on a Campaign row, **When** the click event fires, **Then** the user is navigated to `/campaigns/{id}` (the Approval Gate) for that Campaign.

4. **Given** status filter tabs or a filter dropdown is shown above the Campaign list, **When** the user selects a specific status (e.g., "Pending Approval"), **Then** the list refetches with `?status=pending_approval` and displays only campaigns matching that status; the URL updates to include the filter parameter so the filtered state is shareable and bookmarkable.

5. **Given** the page is loading Campaign data, **When** the initial fetch is in progress, **Then** skeleton placeholder rows matching the expected Campaign row height and layout are shown (no spinner); the number of skeleton rows matches `per_page` (20) or the previous known count, whichever is smaller.

6. **Given** the active Client has no Campaigns, **When** the Dashboard loads, **Then** the empty state is shown in the center of the content pane: H2 "No campaigns yet." and body text "Start with a Brain Dump and publish your first post." with a "New Campaign" primary CTA; no skeleton rows are shown.

7. **Given** a Campaign row for a `failed` status campaign, **When** the row renders, **Then** the status badge shows "FAILED" (Danger red), and a "Retry" inline text link is shown within the row that navigates directly to the Approval Gate for that campaign (where the Retry Panel is shown).

8. **Given** the user switches the active Client via the Client Switcher, **When** the new client context is set, **Then** the Campaign list React Query key `["campaigns", newClientId]` is invalidated and the list reloads for the new client immediately.

## Tasks / Subtasks

- [x] Task 1: Update backend `list_campaigns` endpoint to support filtering and pagination (AC: #1, #4, #8)
  - [x] 1.1 Add query parameters to `GET /api/v1/campaigns` in `backend/app/routers/campaigns.py`:
    - `client_id: uuid.UUID | None = Query(default=None)` — filters by specific client (user ownership enforced)
    - `status: str | None = Query(default=None)` — comma-separated statuses e.g. `"pending_approval"` or `"published,approved"`
    - `page: int = Query(default=1, ge=1)` — page number (1-indexed)
    - `per_page: int = Query(default=20, ge=1, le=100)` — items per page
  - [ ] 1.2 Update the query in `list_campaigns` to apply filters:
    ```python
    @router.get("", response_model=CampaignListResponse)
    async def list_campaigns(
        client_id: uuid.UUID | None = Query(default=None),
        status: str | None = Query(default=None),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1, le=100),
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> CampaignListResponse:
        user_id = uuid.UUID(current_user["user_id"])
        query = (
            select(Campaign)
            .join(Client, Campaign.client_id == Client.id)
            .where(Client.user_id == user_id)
        )
        if client_id:
            client = await get_client(db, client_id)
            if not client or client.user_id != user_id:
                raise HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": "Access denied.", "detail": {}}})
            query = query.where(Campaign.client_id == client_id)
        if status:
            statuses = [s.strip() for s in status.split(",") if s.strip()]
            query = query.where(Campaign.status.in_(statuses))
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()
        result = await db.execute(
            query.order_by(Campaign.created_at.desc())
                 .offset((page - 1) * per_page)
                 .limit(per_page)
        )
        campaigns = result.scalars().all()
        return CampaignListResponse(items=[CampaignResponse.model_validate(c) for c in campaigns], total=total)
    ```
  - [x] 1.3 Add `CampaignListResponse` Pydantic schema to `backend/app/schemas/campaigns.py`:
    ```python
    class CampaignListResponse(BaseModel):
        items: list[CampaignResponse]
        total: int
    ```
  - [x] 1.4 Import `func` from `sqlalchemy` at the top of the router file if not already present
  - [x] 1.5 Add `CampaignListResponse` to router imports from schemas

- [x] Task 2: Update frontend API client and TypeScript types (AC: #1, #4)
  - [x] 2.1 Add `CampaignListResponse` type to `frontend/lib/types.ts`:
    ```typescript
    export interface CampaignListResponse {
      items: Campaign[];
      total: number;
    }
    ```
  - [ ] 2.2 Update `campaignsApi` in `frontend/lib/api.ts` — add `listPaginated` method accepting params:
    ```typescript
    listPaginated: (params: {
      client_id?: string;
      status?: string;
      page?: number;
      per_page?: number;
    }) => {
      const query = new URLSearchParams();
      if (params.client_id) query.set("client_id", params.client_id);
      if (params.status) query.set("status", params.status);
      if (params.page) query.set("page", String(params.page));
      if (params.per_page) query.set("per_page", String(params.per_page));
      const qs = query.toString();
      return apiFetch<CampaignListResponse>(`/campaigns${qs ? `?${qs}` : ""}`);
    },
    ```
    - Import `CampaignListResponse` at the top of `api.ts`

- [x] Task 3: Create `hooks/useCampaigns.ts` hook (AC: #1, #4, #5, #8)
  - [x] 3.1 Create `frontend/hooks/useCampaigns.ts`:
    ```typescript
    "use client";
    import { useQuery } from "@tanstack/react-query";
    import { campaignsApi } from "@/lib/api";

    export interface UseCampaignsParams {
      clientId: string | null;
      status?: string;
      page?: number;
      perPage?: number;
    }

    export function useCampaigns({ clientId, status, page = 1, perPage = 20 }: UseCampaignsParams) {
      return useQuery({
        queryKey: ["campaigns", clientId, { status, page, perPage }],
        queryFn: () =>
          campaignsApi.listPaginated({
            client_id: clientId ?? undefined,
            status,
            page,
            per_page: perPage,
          }),
        enabled: !!clientId,
        staleTime: 30_000,
        placeholderData: (prev) => prev,
      });
    }
    ```
  - [x] 3.2 Create `hooks/usePlatformConnections.ts` for fetching active client's connected platforms (used to render platform icons):
    ```typescript
    "use client";
    import { useQuery } from "@tanstack/react-query";
    import { publishingApi } from "@/lib/api";

    export function usePlatformConnections(clientId: string | null) {
      return useQuery({
        queryKey: ["platform-connections", clientId],
        queryFn: () => publishingApi.listConnections(clientId!),
        enabled: !!clientId,
        staleTime: 60_000,
      });
    }
    ```

- [x] Task 4: Create `CampaignList.tsx` client component (AC: #1–#8)
  - [x] 4.1 Create `frontend/components/campaigns/CampaignList.tsx` as a `"use client"` component:
    - Reads `activeClientId` from `useClientStore`
    - Reads `status` filter and `page` from URL search params via `useSearchParams()`
    - Uses `useCampaigns({ clientId, status, page })` for data fetching
    - Uses `usePlatformConnections(clientId)` to get the active client's connected platforms
    - Renders filter tab bar, campaign rows, skeleton loaders, empty state, pagination
  - [x] 4.2 Filter tab bar implementation (Paper Style — text-based tabs with underline indicator):
    ```tsx
    const FILTER_OPTIONS = [
      { value: "", label: "All" },
      { value: "pending_approval", label: "Pending Approval" },
      { value: "approved", label: "Approved" },
      { value: "published", label: "Published" },
      { value: "rejected", label: "Rejected" },
      { value: "failed", label: "Failed" },
    ];
    ```
    - Active tab: `border-b-2 border-ink text-ink font-medium`
    - Inactive tab: `text-graphite hover:text-ink transition-colors`
    - On tab click: `router.push` with `?status=<value>&page=1` (use `useRouter` from `next/navigation`)
    - All tabs in a horizontal scrollable `<nav role="tablist">` above the list
  - [x] 4.3 Campaign row implementation (see Dev Notes for full UX spec):
    - Clickable `<Link href={/campaigns/${campaign.id}}>` wrapping the full row
    - Title: `extractTitle(campaign.blog_html)` — first H1 from HTML, stripped of tags, truncated at 60 chars + "…" — fall back to `"(Generating…)"` if blog_html is null
    - Status badge: reuse existing `<StatusBadge status={campaign.status} />`
    - Creation date: `new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(campaign.created_at))`
    - Publish date (if published): same Intl.DateTimeFormat on `campaign.updated_at`
    - Platform icons (if published): map connected platforms → render small platform icon (size-3.5) — use the `PlatformIcon` pattern from `PlatformConnectionCard.tsx`
    - Failed campaign: show "Retry →" as an `<Link>` inside the row (same href as the row, since Retry Panel is in the Approval Gate)
  - [x] 4.4 Create utility `extractTitle(html: string | null): string` in `frontend/lib/utils.ts` (or add to existing):
    ```typescript
    export function extractTitle(html: string | null): string {
      if (!html) return "(Generating…)";
      const match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
      if (!match) return "(Untitled)";
      const text = match[1].replace(/<[^>]+>/g, "").trim();
      return text.length > 60 ? text.slice(0, 60) + "…" : text || "(Untitled)";
    }
    ```
  - [x] 4.5 Skeleton loader: render 20 skeleton rows (or `per_page` count) while `isLoading`. Each skeleton row mirrors the campaign row layout:
    ```tsx
    // Use existing <Skeleton> component from components/ui/Skeleton.tsx
    Array.from({ length: 20 }).map((_, i) => (
      <div key={i} className="flex items-center justify-between p-5 border-b border-border">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/5" />
          <Skeleton className="h-3 w-1/4" />
        </div>
        <div className="flex items-center gap-4 ml-4">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
    ))
    ```
  - [x] 4.6 Empty state (AC: #6):
    ```tsx
    <div className="border border-border p-16 text-center">
      <h2 className="font-display text-xl font-bold text-ink mb-2">No campaigns yet.</h2>
      <p className="text-sm text-graphite font-body mb-6">
        Start with a Brain Dump and publish your first post.
      </p>
      <Link href="/campaigns/new"
        className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-6 py-3 hover:bg-graphite transition-colors shadow-[4px_4px_0px_0px_var(--color-ink)] hover:shadow-none"
      >
        New Campaign
        <ArrowRight className="size-4" aria-hidden="true" />
      </Link>
    </div>
    ```
  - [x] 4.7 Pagination controls (AC: #1):
    ```tsx
    {totalPages > 1 && (
      <div className="flex items-center justify-between border-t border-border px-5 py-4">
        <button onClick={() => goToPage(page - 1)} disabled={page <= 1}
          className="text-sm font-mono text-graphite hover:text-ink disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          ← Previous
        </button>
        <span className="text-xs font-mono text-graphite">
          Page {page} of {totalPages}
        </span>
        <button onClick={() => goToPage(page + 1)} disabled={page >= totalPages}
          className="text-sm font-mono text-graphite hover:text-ink disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          Next →
        </button>
      </div>
    )}
    ```
    - `goToPage(n)` calls `router.push` with `?page=n&status=<current>`

- [x] Task 5: Update `frontend/app/(app)/dashboard/page.tsx` to use new `CampaignList` (AC: #1–#8)
  - [x] 5.1 Replace the inline campaign list and `getRecentCampaigns()` server-side fetch with `<CampaignList />` client component
  - [x] 5.2 Keep the page header ("Dashboard" H1) but remove the stats grid — it is out of scope for Epic 6 and duplicates information shown in the filtered list; the stats can be re-added in a future epic if needed
  - [x] 5.3 The page remains a Server Component (RSC). Import `CampaignList` as a client island:
    ```tsx
    import { CampaignList } from "@/components/campaigns/CampaignList";

    export default async function DashboardPage() {
      return (
        <>
          <header className="mb-10">
            <h1 className="font-display text-3xl font-bold text-ink mb-1">Dashboard</h1>
            <p className="text-sm text-graphite font-mono">Your content pipeline at a glance.</p>
          </header>
          <CampaignList />
        </>
      );
    }
    ```
  - [x] 5.4 Remove `DashboardEmptyState` import and usage from the page — empty state is now handled inside `CampaignList`
  - [x] 5.5 Remove `NudgeCard` import and `showNudge` logic — this belongs to Epic 7 (Trial Lifecycle); move `NudgeCard.tsx` to `components/account/` or delete if unused

- [x] Task 6: Client switch cache invalidation (AC: #8)
  - [x] 6.1 Verify that `CampaignList` reacts to `activeClientId` changes from `useClientStore`. Because `useCampaigns` includes `clientId` in the query key `["campaigns", clientId, ...]`, React Query automatically refetches when `activeClientId` changes — no explicit `invalidateQueries` needed in the component itself
  - [x] 6.2 If the ClientSwitcher component (in the sidebar/layout) currently calls `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` on switch, verify it works with the new key structure — the partial key `["campaigns"]` will invalidate all campaign queries regardless of `clientId`

- [x] Task 7: Backend tests (AC: #1, #4)
  - [x] 7.1 Add to `backend/tests/routers/test_campaigns.py` (or create if it doesn't exist):
    - `test_list_campaigns_with_client_id_filter` — verify only campaigns for that client_id are returned
    - `test_list_campaigns_status_filter` — verify `?status=pending_approval` returns only pending campaigns
    - `test_list_campaigns_multiple_status` — verify `?status=published,approved` returns campaigns with either status
    - `test_list_campaigns_pagination` — verify `?page=2&per_page=5` returns correct slice and `total` count
    - `test_list_campaigns_client_id_ownership` — verify user cannot filter by another user's client_id (403)
    - `test_list_campaigns_returns_items_and_total` — verify response shape has `items` and `total` keys

- [x] Task 8: Frontend tests (AC: #1, #3, #5, #6, #7)
  - [x] 8.1 Create `frontend/__tests__/components/campaigns/CampaignList.test.tsx`:
    - `test_renders_skeleton_while_loading` — mock query as loading state, verify skeleton rows render
    - `test_renders_campaign_rows` — mock query with campaign data, verify title, status badge, date render
    - `test_empty_state_when_no_campaigns` — mock empty response, verify "No campaigns yet." and CTA
    - `test_failed_campaign_shows_retry_link` — mock failed campaign, verify "Retry" link present
    - `test_filter_tab_updates_url` — click "Published" tab, verify router.push called with `?status=published&page=1`
    - `test_pagination_previous_next` — with `total > 20`, verify previous/next buttons, correct disabled state on page 1

## Dev Notes

### Existing Dashboard State (Critical Context)

The current `frontend/app/(app)/dashboard/page.tsx` is a **Server Component** that calls `GET /api/v1/campaigns` (no params) directly via `fetch` and renders a basic list of 8 campaigns. This story replaces that list entirely with the React Query-powered `CampaignList` client component.

**Current server-side fetches to remove:**
- `getRecentCampaigns()` — fetches all campaigns via direct server fetch, slice to 8 items. **Remove entirely.**
- `getClients()` — fetches all clients for stats. **Remove if stats are removed; keep if retained.**
- `DashboardEmptyState` and `NudgeCard` components currently imported — **DashboardEmptyState** is replaced by the empty state inside `CampaignList`; `NudgeCard` belongs to Epic 7 and should be kept in place for now but only rendered after the CampaignList as an addendum (not replacing it).

### Backend: `list_campaigns` Breaking Change

The endpoint currently returns `list[CampaignResponse]` (a JSON array). After this story, it returns `{"items": [...], "total": int}`. Any other consumers of `GET /api/v1/campaigns` must be updated:

**Scan for other consumers in the codebase:**
- `frontend/app/(app)/dashboard/page.tsx` — the `getRecentCampaigns()` function uses `fetch(`.../api/v1/campaigns`)` — **this is replaced by `CampaignList` client component, so this fetch is removed entirely**
- `frontend/lib/api.ts` — `campaignsApi.list()` currently returns `Campaign[]` — **update or deprecate; add `listPaginated()` as the new primary method**
- Search all other files with: `grep -r "campaignsApi.list\|/api/v1/campaigns" frontend/`

If `campaignsApi.list()` (the old non-paginated method) is used elsewhere, either:
a. Keep it as-is with its own route if needed, OR
b. Update callers to use `listPaginated()` with appropriate params

### Platform Icons Pattern

Reuse the `PlatformIcon` function from `frontend/components/publishing/PlatformConnectionCard.tsx`. **Do not duplicate** — extract it to `frontend/components/ui/PlatformIcon.tsx` as a shared component:

```tsx
// frontend/components/ui/PlatformIcon.tsx
import { Globe, LayoutGrid, Share2, Link2 } from "lucide-react";

interface Props {
  platform: string;
  className?: string;
}

export function PlatformIcon({ platform, className = "size-3.5" }: Props) {
  if (platform === "wordpress" || platform === "wordpress-com")
    return <Globe className={className} aria-hidden="true" />;
  if (platform === "webflow")
    return <LayoutGrid className={className} aria-hidden="true" />;
  if (platform === "x")
    return <Share2 className={className} aria-hidden="true" />;
  return <Link2 className={className} aria-hidden="true" />;  // linkedin
}
```

Then update `PlatformConnectionCard.tsx` to import from this shared location.

**For published campaign rows:** Fetch the active client's platform connections via `usePlatformConnections(clientId)`. For each `connected: true` connection, show its icon inline with the publish date. This efficiently reuses the React Query cache — platform connections are stale for 60s, so they won't re-fetch on every row render.

### URL State for Filter + Pagination

Use Next.js `useSearchParams()` and `useRouter()` from `next/navigation` to read/write URL params.

```typescript
// Reading current filter state
const searchParams = useSearchParams();
const status = searchParams.get("status") ?? "";
const page = Number(searchParams.get("page") ?? "1");

// Navigating to filtered state
function setFilter(newStatus: string) {
  const params = new URLSearchParams(searchParams.toString());
  if (newStatus) params.set("status", newStatus);
  else params.delete("status");
  params.set("page", "1");  // reset to page 1 on filter change
  router.push(`/dashboard?${params.toString()}`);
}
```

This makes the filtered view shareable and bookmarkable. The `CampaignList` component must be wrapped in React's `<Suspense>` in the page because `useSearchParams()` requires it in Next.js App Router.

```tsx
// dashboard/page.tsx
import { Suspense } from "react";
<Suspense fallback={null}>
  <CampaignList />
</Suspense>
```

### `extractTitle` Utility

Place in `frontend/lib/utils.ts` (create file if it doesn't exist; if it does exist, append):

```typescript
export function extractTitle(html: string | null): string {
  if (!html) return "(Generating…)";
  const match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  if (!match) return "(Untitled)";
  const text = match[1].replace(/<[^>]+>/g, "").trim();
  return text.length > 60 ? text.slice(0, 60) + "…" : text || "(Untitled)";
}
```

Regex approach (not DOMParser) because this runs in both client and server contexts. The `[\s\S]*?` handles multi-line H1 content.

### Paper Style for Campaign List (UX Enforced)

Following the `DESIGN.md` and established patterns from `dashboard/page.tsx`:

**Campaign row:** `flex items-center justify-between p-5 hover:bg-ink/5 transition-colors group` with `border-b border-border`. On hover, apply the brutalist card shadow: `hover:shadow-[2px_2px_0px_0px_var(--color-ink)]` (small shadow variant per DESIGN.md §Elevation).

**Filter tabs:** Use a horizontal `<nav>` with `border-b border-border mb-6`. Each tab is a `<button>` with `px-4 py-2 text-sm font-body`. Active: `border-b-2 border-ink text-ink font-medium -mb-px` (the -mb-px trick makes the tab border sit on top of the nav border). Inactive: `text-graphite hover:text-ink transition-colors`.

**No rounded corners** on any interactive elements. `rounded-none` is implicit from the design system globals.

**Status badge reuse:** Import `StatusBadge` from `@/components/ui/StatusBadge` — it already handles all 5 states with correct Paper Style colors.

**Date format (AC: #2):** `Intl.DateTimeFormat` with `{ month: 'short', day: 'numeric', year: 'numeric' }`. This produces "Jun 17, 2026" format with locale awareness.

**"Retry" link for failed campaigns (AC: #7):** The Retry Panel is shown in the Approval Gate (`/campaigns/{id}`). So the Retry link is simply another link to the same campaign ID. Render it as a secondary anchor in the row — ensure it doesn't interfere with the row's primary click (use `e.stopPropagation()` if the row has an outer click handler, or use proper `<Link>` nesting which Next.js handles correctly when the outer element is also a `<Link>` by making the retry a separate `<Link>` outside the main row's `<Link>` wrapper).

**IMPORTANT — Nested Links:** React/HTML does not allow nested `<a>` tags. Use a `<div role="link">` or `<tr>` clickable row with `onClick={() => router.push(...)}` for the outer row, and a proper `<Link>` for the "Retry →" inline anchor. Or restructure so the Retry link is a sibling `<td>` in the row rather than nested inside the row link.

**Recommended pattern for row with inline action:**
```tsx
<div
  key={campaign.id}
  className="flex items-center justify-between p-5 border-b border-border hover:bg-ink/5 transition-colors cursor-pointer group"
  onClick={() => router.push(`/campaigns/${campaign.id}`)}
  role="row"
>
  <div className="min-w-0 flex-1">
    <p className="font-medium text-ink text-sm truncate mb-1">{title}</p>
    <p className="text-xs text-graphite font-mono">{formattedDate}</p>
  </div>
  <div className="flex items-center gap-3 ml-4 shrink-0">
    <StatusBadge status={campaign.status} />
    {campaign.status === "published" && (
      <div className="flex items-center gap-1">
        {connectedPlatforms.map(p => <PlatformIcon key={p} platform={p} className="size-3.5 text-graphite" />)}
      </div>
    )}
    {campaign.status === "failed" && (
      <Link
        href={`/campaigns/${campaign.id}`}
        onClick={e => e.stopPropagation()}
        className="text-xs font-mono text-danger underline underline-offset-2 hover:text-ink transition-colors"
      >
        Retry →
      </Link>
    )}
    <ArrowRight className="size-3.5 text-graphite opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden="true" />
  </div>
</div>
```

### React Query Key Structure

Per architecture `patterns` section:
```typescript
// campaigns for specific client, with optional status filter
["campaigns", clientId, { status, page, perPage }]
```

When `activeClientId` changes in Zustand, React Query will naturally treat the new key as a different query and fetch fresh data. No explicit invalidation required in `CampaignList`. The client switcher in the sidebar may additionally call `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` — this is fine and matches the pattern from AC #8.

### Backend: SQLAlchemy Pagination Pattern

The count query uses a subquery to avoid full scan:
```python
# Import at top of router: from sqlalchemy import func, select
count_result = await db.execute(
    select(func.count()).select_from(query.subquery())
)
total = count_result.scalar_one()
```

This is safe with async SQLAlchemy. The `query.subquery()` converts the main query to a subquery for counting. Order the main query BEFORE applying offset/limit to ensure correct pagination.

### Status Filter Values (Backend ↔ Frontend)

| Display Label | URL param value | DB value |
|---|---|---|
| All | (omit param) | — |
| Pending Approval | `pending_approval` | `pending_approval` |
| Approved | `approved` | `approved` |
| Published | `published` | `published` |
| Rejected | `rejected` | `rejected` |
| Failed | `failed` | `failed` |

The status values are `snake_case` throughout (DB, API, and URL) — no conversion needed.

### Files to Create / Modify

**New files:**
```
frontend/components/campaigns/CampaignList.tsx
frontend/components/ui/PlatformIcon.tsx
frontend/hooks/useCampaigns.ts
frontend/hooks/usePlatformConnections.ts
frontend/__tests__/components/campaigns/CampaignList.test.tsx
```

**Modified files:**
```
backend/app/routers/campaigns.py          ← Add query params + update response model
backend/app/schemas/campaigns.py          ← Add CampaignListResponse schema
frontend/lib/types.ts                     ← Add CampaignListResponse type
frontend/lib/api.ts                       ← Add listPaginated() + import CampaignListResponse
frontend/lib/utils.ts                     ← Add extractTitle() utility (create if needed)
frontend/app/(app)/dashboard/page.tsx     ← Replace inline list with <CampaignList>
frontend/components/publishing/PlatformConnectionCard.tsx  ← Import PlatformIcon from shared location
backend/tests/routers/test_campaigns.py   ← Add 6 new tests
```

### References

- Epic 6 story AC: `_bmad-output/planning-artifacts/epics.md#Story-6.1`
- Architecture dashboard mapping: `_bmad-output/planning-artifacts/architecture.md#FR-26-27-Dashboard`
- Paper Style design tokens: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md`
- UX experience flows: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md`
- React Query key patterns: `_bmad-output/planning-artifacts/architecture.md#React-Query-Key-Structure`
- Existing Skeleton component: `frontend/components/ui/Skeleton.tsx`
- Existing StatusBadge component: `frontend/components/ui/StatusBadge.tsx`
- Platform icon pattern (extract from): `frontend/components/publishing/PlatformConnectionCard.tsx:23-29`
- Current dashboard page to refactor: `frontend/app/(app)/dashboard/page.tsx`
- Current backend campaigns router: `backend/app/routers/campaigns.py:83-100`
- Previous story (5.6) patterns: `_bmad-output/implementation-artifacts/5-6-wordpress-com-oauth-integration.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Implemented `CampaignListResponse` Pydantic schema and updated `list_campaigns` endpoint with `client_id`, `status`, `page`, `per_page` query params; returns `{items, total}` instead of bare array.
- Created shared `PlatformIcon` component extracted from `PlatformConnectionCard.tsx` to avoid duplication.
- Created `CampaignList.tsx` client component with filter tabs, skeleton loaders, campaign rows, empty state, and pagination — all URL-state driven via `useSearchParams`.
- Created `useCampaigns` and `usePlatformConnections` hooks using TanStack Query; query key includes `clientId` so client switching auto-refetches.
- Dashboard page replaced server-side fetching with `<CampaignList />` client island wrapped in `<Suspense>`.
- All 6 backend tests pass; all 115 frontend tests pass (6 new + 109 existing, no regressions).
- Pre-existing backend failures (59 before, 53 after) are unrelated to this story — the 6 new campaign tests now pass.

### File List

**New files:**
- `frontend/components/campaigns/CampaignList.tsx`
- `frontend/components/ui/PlatformIcon.tsx`
- `frontend/hooks/useCampaigns.ts`
- `frontend/hooks/usePlatformConnections.ts`
- `frontend/__tests__/components/campaigns/CampaignList.test.tsx`
- `backend/tests/routers/test_campaigns.py`

**Modified files:**
- `backend/app/routers/campaigns.py`
- `backend/app/schemas/campaign.py`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `frontend/lib/utils.ts`
- `frontend/app/(app)/dashboard/page.tsx`
- `frontend/components/publishing/PlatformConnectionCard.tsx`

### Review Findings

- [x] [Review][Decision] No distinct "select a client" empty state — deferred; users always have a client by dashboard load; generic empty state is acceptable.
- [x] [Review][Decision] `updated_at` used as publish date is semantically wrong — deferred; adding `published_at` requires a DB migration out of scope for this story.
- [x] [Review][Patch] `campaignsApi.list()` removed (dead code, wrong return type after breaking change) [frontend/lib/api.ts:95]
- [x] [Review][Patch] `page` URL param NaN handled with `parseInt(..., 10) || 1` [CampaignList.tsx:36]
- [x] [Review][Patch] Removed unused `perPage` local constant; `totalPages` uses inline `20` [CampaignList.tsx:47]
- [x] [Review][Patch] Double border removed from campaign rows — removed `border-b border-border` from row div [CampaignList.tsx:131]
- [x] [Review][Patch] ReDoS guard added to `extractTitle` — slices input to 2000 chars before regex [frontend/lib/utils.ts]
- [x] [Review][Patch] Removed invalid `role="row"` from campaign row divs [CampaignList.tsx:134]
- [x] [Review][Patch] Count query now uses clean `query` (no ORDER BY) for subquery count [backend/app/routers/campaigns.py:112]
- [x] [Review][Defer] `sys.modules` patching at module level in test file — pre-existing pattern; runs at import time and persists across session. Acceptable for now, tracked for future test refactor. [backend/tests/routers/test_campaigns.py:7-9] — deferred, pre-existing

### Change Log

- feat: campaign list dashboard with status filtering, pagination, and skeleton loaders (Story 6.1, 2026-07-04)
