---
baseline_commit: e256e0dd747dc1ac93990b4616fe993ccf31ef5f
---

# Story 6.2: Content Calendar — Read-Only Month View

Status: review

## Story

As an authenticated user,
I want to view a month-by-month calendar showing when my content was published and what is scheduled,
so that I can see my publishing cadence at a glance and spot gaps or scheduling conflicts across the month.

## Acceptance Criteria

1. **Given** an authenticated user navigates to `/calendar`, **When** the page loads, **Then** a month view calendar is displayed for the current month; the month name and year are shown in a Playfair Display H2 at the top; previous and next month navigation arrows are present.

2. **Given** the calendar renders for the current month, **When** campaigns are fetched via `GET /api/v1/campaigns?client_id={activeClientId}&status=published,approved`, **Then** published Campaigns appear on their `updated_at` date (publish date) with small platform icons (WP, Webflow, X, LinkedIn icons for each connected platform they were published to); scheduled Campaigns (status `approved` with `scheduled_at` set) appear on their `scheduled_at` date with a clock icon and formatted time (e.g., "8:00 AM").

3. **Given** a calendar day cell has one or more campaigns, **When** the user clicks on a campaign entry within a day cell, **Then** they are navigated to the Approval Gate at `/campaigns/{id}` for that Campaign.

4. **Given** a calendar day cell, **When** rendered for accessibility, **Then** each cell has `aria-label` including the full date and campaign count: "June 17, 2026, 2 campaigns" (or "June 17, 2026, no campaigns" if empty); all interactive campaign entries within the cell are keyboard-focusable and have descriptive labels.

5. **Given** the calendar is in read-only mode, **When** the user attempts to drag a campaign entry to a different date, **Then** nothing happens — no drag-and-drop rescheduling is available in v1; entries are click-only.

6. **Given** the active Client is switched via the Client Switcher while on the Calendar surface, **When** the new client context is set, **Then** the calendar reloads and shows the campaigns for the newly active Client for the currently viewed month.

7. **Given** no campaigns exist for the currently viewed month, **When** the calendar renders, **Then** all day cells are empty; a subdued message appears below the calendar: "Nothing scheduled. Approve a campaign to see it here." in Graphite body text.

## Tasks / Subtasks

- [x] Task 1: Verify backend `list_campaigns` supports comma-separated status filter (dependency on Story 6.1)
  - [x] 1.1 Confirm `GET /api/v1/campaigns?client_id={id}&status=published,approved` returns both published and approved campaigns — this is implemented in Story 6.1 Task 1.1. If Story 6.1 backend changes are not yet merged, implement them first (they are a shared dependency)
  - [x] 1.2 Verify the `CampaignListResponse` schema (`{"items": [...], "total": int}`) is in place from Story 6.1

- [x] Task 2: Create `hooks/useCalendarCampaigns.ts` hook (AC: #2, #6)
  - [x] 2.1 Create `frontend/hooks/useCalendarCampaigns.ts`:
    ```typescript
    "use client";
    import { useQuery } from "@tanstack/react-query";
    import { campaignsApi } from "@/lib/api";
    import type { Campaign } from "@/lib/types";

    export function useCalendarCampaigns(clientId: string | null) {
      return useQuery({
        queryKey: ["calendar-campaigns", clientId],
        queryFn: async (): Promise<Campaign[]> => {
          const res = await campaignsApi.listPaginated({
            client_id: clientId ?? undefined,
            status: "published,approved",
            per_page: 100,  // calendars rarely have >100 campaigns in view; safe upper bound
          });
          return res.items;
        },
        enabled: !!clientId,
        staleTime: 30_000,
      });
    }
    ```
  - [x] 2.2 This hook depends on `campaignsApi.listPaginated()` from Story 6.1 Task 2.2 — confirm it is available before implementing

- [x] Task 3: Create `ContentCalendar.tsx` client component (AC: #1–#7)
  - [x] 3.1 Create `frontend/components/calendar/ContentCalendar.tsx` as a `"use client"` component:
    - Reads `activeClientId` from `useClientStore`
    - Maintains `viewYear` and `viewMonth` state (default: current month)
    - Fetches campaigns via `useCalendarCampaigns(clientId)` — returns ALL published+approved campaigns for the client
    - Filters the fetched campaigns to only those whose relevant date falls within the viewed month
    - Renders the month grid with campaign entries per day
  - [x] 3.2 Month navigation state and helpers:
    ```typescript
    const now = new Date();
    const [viewYear, setViewYear] = useState(now.getFullYear());
    const [viewMonth, setViewMonth] = useState(now.getMonth()); // 0-indexed

    function prevMonth() {
      if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); }
      else setViewMonth(m => m - 1);
    }

    function nextMonth() {
      if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); }
      else setViewMonth(m => m + 1);
    }

    const monthLabel = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" })
      .format(new Date(viewYear, viewMonth, 1));
    ```
  - [x] 3.3 Calendar grid computation:
    ```typescript
    // Build an array of day cells for the month grid (including leading/trailing empty cells)
    function buildMonthGrid(year: number, month: number): Array<Date | null> {
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);
      const startDow = firstDay.getDay(); // 0=Sun
      const daysInMonth = lastDay.getDate();
      const cells: Array<Date | null> = [];
      // Leading empty cells (before month start)
      for (let i = 0; i < startDow; i++) cells.push(null);
      // Month days
      for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
      // Trailing empty cells (to complete last row to 7)
      while (cells.length % 7 !== 0) cells.push(null);
      return cells;
    }
    ```
  - [x] 3.4 Campaign date mapping:
    ```typescript
    // Map each campaign to the date it should appear on the calendar
    function campaignCalendarDate(campaign: Campaign): Date | null {
      if (campaign.status === "published") {
        return new Date(campaign.updated_at); // publish date
      }
      if (campaign.status === "approved" && campaign.scheduled_at) {
        return new Date(campaign.scheduled_at); // scheduled date
      }
      return null; // approved but not scheduled → do not show on calendar
    }

    // Group campaigns by ISO date string "YYYY-MM-DD"
    const campaignsByDate = useMemo(() => {
      const map = new Map<string, Campaign[]>();
      for (const c of campaigns ?? []) {
        const d = campaignCalendarDate(c);
        if (!d) continue;
        const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(c);
      }
      return map;
    }, [campaigns]);
    ```
  - [x] 3.5 Full month view layout (Paper Style — strict grid, no shadows):
    ```tsx
    <div className="select-none">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-display text-2xl font-bold text-ink tracking-tight">
          {monthLabel}
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={prevMonth}
            aria-label="Previous month"
            className="p-2 border border-border hover:border-ink hover:bg-ink hover:text-paper transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
          >
            <ChevronLeft className="size-4" aria-hidden="true" />
          </button>
          <button
            onClick={nextMonth}
            aria-label="Next month"
            className="p-2 border border-border hover:border-ink hover:bg-ink hover:text-paper transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
          >
            <ChevronRight className="size-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Day-of-week header */}
      <div className="grid grid-cols-7 border-t border-l border-border mb-0">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(d => (
          <div key={d} className="border-b border-r border-border px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider text-graphite text-center">
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 border-l border-border">
        {grid.map((date, idx) => {
          if (!date) {
            return <div key={idx} className="border-b border-r border-border min-h-[80px] bg-border/20" aria-hidden="true" />;
          }
          const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
          const dayCampaigns = campaignsByDate.get(key) ?? [];
          const count = dayCampaigns.length;
          const isToday = key === todayKey;
          const ariaLabel = `${date.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}, ${count === 0 ? "no campaigns" : `${count} campaign${count > 1 ? "s" : ""}`}`;

          return (
            <div
              key={key}
              className={clsx("border-b border-r border-border min-h-[80px] p-1.5 flex flex-col gap-1", isToday && "bg-highlighter/30")}
              aria-label={ariaLabel}
            >
              <span className={clsx("text-xs font-mono self-start px-1", isToday ? "bg-ink text-paper font-bold" : "text-graphite")}>
                {date.getDate()}
              </span>
              {dayCampaigns.map(c => (
                <CalendarEntry key={c.id} campaign={c} connectedPlatforms={connectedPlatforms} />
              ))}
            </div>
          );
        })}
      </div>

      {/* Empty state message */}
      {!isLoading && (campaigns ?? []).length === 0 && (
        <p className="mt-6 text-sm text-graphite font-body text-center">
          Nothing scheduled. Approve a campaign to see it here.
        </p>
      )}
    </div>
    ```
  - [x] 3.6 Create `CalendarEntry` sub-component within `ContentCalendar.tsx` (AC: #2, #3, #4, #5):
    ```tsx
    function CalendarEntry({
      campaign,
      connectedPlatforms,
    }: {
      campaign: Campaign;
      connectedPlatforms: string[];
    }) {
      const router = useRouter();
      const title = extractTitle(campaign.blog_html);
      const shortTitle = title.length > 24 ? title.slice(0, 24) + "…" : title;

      const timeLabel =
        campaign.status === "approved" && campaign.scheduled_at
          ? new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" }).format(
              new Date(campaign.scheduled_at)
            )
          : null;

      return (
        <button
          type="button"
          onClick={() => router.push(`/campaigns/${campaign.id}`)}
          draggable={false}  // AC: #5 — no drag-and-drop
          onDragStart={e => e.preventDefault()}  // belt-and-suspenders
          aria-label={`${shortTitle} — ${campaign.status === "published" ? "Published" : `Scheduled ${timeLabel}`}`}
          className={clsx(
            "w-full text-left px-1.5 py-0.5 text-[10px] font-body leading-tight",
            "border transition-colors cursor-pointer",
            "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ink focus-visible:ring-offset-1",
            campaign.status === "published"
              ? "bg-success/10 border-success/30 text-success hover:bg-success/20"
              : "bg-border border-border text-graphite hover:border-ink hover:text-ink"
          )}
        >
          <span className="block truncate">{shortTitle}</span>
          <div className="flex items-center gap-0.5 mt-0.5">
            {campaign.status === "published" &&
              connectedPlatforms.map(p => (
                <PlatformIcon key={p} platform={p} className="size-2.5 shrink-0" />
              ))}
            {timeLabel && (
              <>
                <Clock className="size-2.5 shrink-0 text-graphite" aria-hidden="true" />
                <span className="text-graphite">{timeLabel}</span>
              </>
            )}
          </div>
        </button>
      );
    }
    ```
  - [x] 3.7 Fetch connected platforms to show icons on published entries:
    - Use `usePlatformConnections(clientId)` hook (created in Story 6.1 Task 3.2)
    - Extract connected platform names: `const connectedPlatforms = (connections?.items ?? []).filter(p => p.connected).map(p => p.platform)`
    - Pass `connectedPlatforms` down to each `CalendarEntry`
  - [x] 3.8 Skeleton loading state (AC: #4 — no skeleton-per-cell; show a full-width skeleton bar while fetching):
    ```tsx
    {isLoading && (
      <div className="space-y-2 mt-4">
        <Skeleton className="h-[400px] w-full" />
      </div>
    )}
    ```
    Only show the full calendar grid when `!isLoading`. While loading, render the month header + navigation (so the user can navigate months) but show the skeleton in place of the grid.

- [x] Task 4: Create `frontend/app/(app)/calendar/page.tsx` (AC: #1)
  - [x] 4.1 Create the page as a Server Component that renders the `ContentCalendar` client island:
    ```tsx
    import type { Metadata } from "next";
    import { Suspense } from "react";
    import { ContentCalendar } from "@/components/calendar/ContentCalendar";
    import { Skeleton } from "@/components/ui/Skeleton";

    export const metadata: Metadata = {
      title: "Content Calendar",
      robots: { index: false },
    };

    export default function CalendarPage() {
      return (
        <>
          <header className="mb-8">
            <h1 className="font-display text-3xl font-bold text-ink mb-1">Content Calendar</h1>
            <p className="text-sm text-graphite font-mono">
              Your publishing cadence at a glance.
            </p>
          </header>
          <Suspense fallback={<Skeleton className="h-[500px] w-full" />}>
            <ContentCalendar />
          </Suspense>
        </>
      );
    }
    ```
  - [x] 4.2 Verify the sidebar navigation has a "Calendar" link to `/calendar` — check `frontend/components/layout/Sidebar.tsx` and add if missing

- [x] Task 5: Client switch cache invalidation (AC: #6)
  - [x] 5.1 Verify `useCalendarCampaigns` reacts automatically to `activeClientId` changes via the React Query key `["calendar-campaigns", clientId]` — no explicit invalidation needed in `ContentCalendar`
  - [x] 5.2 If the ClientSwitcher calls `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` on switch (from Story 6.1 verification), ensure it does NOT accidentally invalidate `["calendar-campaigns"]` (different key prefix). If broader invalidation is needed, the switcher can also invalidate `["calendar-campaigns"]`.

- [x] Task 6: Accessibility (AC: #4, #5)
  - [x] 6.1 Each `<div>` day cell must have `aria-label` with full date + campaign count as specified in AC #4:
    - Format: `"June 17, 2026, 2 campaigns"` or `"June 17, 2026, no campaigns"`
  - [x] 6.2 Each `CalendarEntry` button must have `aria-label` describing the campaign title and status
  - [x] 6.3 `draggable={false}` and `onDragStart={e => e.preventDefault()}` on all `CalendarEntry` buttons (AC: #5)
  - [x] 6.4 The month navigation buttons use `aria-label="Previous month"` and `aria-label="Next month"` (icon-only buttons)
  - [x] 6.5 Day-of-week header cells (`Sun`, `Mon`, etc.) use `role="columnheader"` within a `role="grid"` container for screen reader table semantics — or use `<abbr title="Sunday">Sun</abbr>` pattern

- [x] Task 7: Sidebar navigation — add Calendar link (AC: #1)
  - [x] 7.1 Open `frontend/components/layout/Sidebar.tsx`, find the nav items array, and add:
    ```typescript
    { href: "/calendar", label: "Calendar", icon: CalendarDays }
    ```
    Import `CalendarDays` from `lucide-react`. Place it after the "Dashboard" link.

- [x] Task 8: Frontend tests (AC: #1, #2, #4, #5, #6, #7)
  - [x] 8.1 Create `frontend/__tests__/components/calendar/ContentCalendar.test.tsx`:
    - `test_renders_current_month_header` — verify Playfair H2 shows current month and year
    - `test_renders_published_campaigns_on_correct_date` — mock campaign with `status="published"` and `updated_at="2026-07-17T10:00:00Z"`, verify it appears in the July 17 cell
    - `test_renders_scheduled_campaigns_on_scheduled_date` — mock campaign with `status="approved"` and `scheduled_at="2026-07-20T08:00:00Z"`, verify it appears in the July 20 cell with "8:00 AM"
    - `test_empty_state_message` — mock empty response, verify "Nothing scheduled. Approve a campaign to see it here."
    - `test_campaign_entry_click_navigates` — simulate click on a CalendarEntry, verify `router.push` called with correct campaign URL
    - `test_drag_disabled` — simulate dragstart on CalendarEntry, verify `preventDefault` called
    - `test_day_cell_aria_label` — verify a cell with 2 campaigns has aria-label "July 17, 2026, 2 campaigns"
    - `test_prev_next_month_navigation` — click ChevronLeft, verify viewMonth decrements and grid rebuilds
    - `test_client_switch_reloads_calendar` — change activeClientId in store, verify query key changes and refetch fires

## Dev Notes

### Dependency on Story 6.1

This story shares the backend `list_campaigns` endpoint changes from Story 6.1:
- `CampaignListResponse` schema must be in place
- `status` query param must support comma-separated values (`published,approved`)
- `campaignsApi.listPaginated()` must be added to `frontend/lib/api.ts`

**If devving 6.2 before 6.1 backend is merged:** Implement the backend changes from Story 6.1 Tasks 1.1–1.5 first as a prerequisite. Both stories share the same backend endpoint extension.

### Calendar Grid Algorithm

The calendar grid is a 7-column CSS grid (7 columns = days of week, Sun–Sat). Each month starts on a different day of the week, requiring leading empty cells.

**Date cells include the current month only.** Leading/trailing empty cells (`null` in the grid array) render as lightly shaded `bg-border/20` background with no content.

**"Today" highlighting:** The current date (today's date in the user's local timezone) gets a subtle Highlighter background on the cell (`bg-highlighter/30`) and the day number renders as white-on-ink (`bg-ink text-paper`). Use local timezone for comparison — `new Date()` returns local time.

**Campaign date resolution:**
- `published` → use `campaign.updated_at` as the publish date (the `updated_at` timestamp is set when the campaign is published; this matches the AC spec)
- `approved` with `scheduled_at` set → use `campaign.scheduled_at` as the scheduled date
- `approved` with `scheduled_at = null` → campaign is approved but not yet scheduled; **do NOT show on calendar** (it has no date to place it on)

**Per-month filtering:** The `useCalendarCampaigns` hook fetches ALL published+approved campaigns for the client (up to 100). The `campaignsByDate` memoized map groups them by date string. When the user navigates to a different month, the same fetched data is re-grouped — no additional API calls. Only when `clientId` changes does a refetch occur.

This design avoids month-specific API calls, which would require date range params not currently in the API. The 100-campaign limit is a pragmatic v1 ceiling — for users with many campaigns, a future story can add date-range filtering to the API.

### Paper Style Calendar Design

The calendar uses a strict grid aesthetic consistent with the "brutalist sharp edges" Paper Style philosophy:

```
border-l border-t border-border on the outer grid container
border-r border-b border-border on each cell
```

This creates a 1px bordered grid with no gaps — cells appear as a seamless table with inner dividers.

**No hover lift shadows on calendar cells.** Campaign entries within cells have a subtle background color change on hover, not shadows. The shadow (`shadow-[4px_4px_0px_0px_var(--color-ink)]`) is reserved for campaign cards and primary buttons per DESIGN.md.

**Campaign entry colors (Paper Style):**
- Published: `bg-success/10 border-success/30 text-success` (muted green, consistent with StatusBadge published state)
- Approved/Scheduled: `bg-border border-border text-graphite` (neutral, waiting)

**Month/Year heading:** Playfair Display H2 (`font-display text-2xl font-bold text-ink`) per DESIGN.md §Typography: "H2 at 1.5rem" for section headers. The page-level H1 is "Content Calendar" (rendered in `page.tsx`); the month/year H2 is within the `ContentCalendar` component.

**Navigation arrows:** Sharp 1px border buttons, no rounded corners. Hover inverts to black fill / white text. No icon-only pill shapes per DESIGN.md §Shapes.

### EXPERIENCE.md UX Copy (AC: #7)

From `EXPERIENCE.md:56`: Empty Calendar copy: "Nothing scheduled. Approve a campaign to see it here." (this matches AC #7 exactly — use this verbatim).

### `usePlatformConnections` Shared Hook

Both Story 6.1 (dashboard row icons) and Story 6.2 (calendar entry icons) need platform connection data. The hook is created in Story 6.1 Task 3.2 at `frontend/hooks/usePlatformConnections.ts`. This story imports and uses it.

The `PlatformIcon` shared component is extracted in Story 6.1 Task 4.1 at `frontend/components/ui/PlatformIcon.tsx`. Import it in `ContentCalendar.tsx`.

### No Drag-and-Drop (AC: #5)

The read-only spec explicitly says no drag-and-drop in v1. Prevent drag by:
1. `draggable={false}` attribute on each `CalendarEntry` button
2. `onDragStart={e => e.preventDefault()}` event handler
3. CSS `user-select: none` on the calendar container (`select-none` Tailwind utility)

Do NOT implement drag-and-drop handlers or import any drag-and-drop libraries.

### Accessibility Details (AC: #4)

Per EXPERIENCE.md §Accessibility: "Each calendar day cell has `aria-label` including the date and campaign count: 'June 17, 2026, 2 campaigns scheduled.'"

**Note:** The AC spec says "2 campaigns" (without "scheduled"), while EXPERIENCE.md says "2 campaigns scheduled". Use the AC wording: "June 17, 2026, 2 campaigns" — the AC is the authoritative source.

For the overall grid container, consider `role="grid"` with `aria-label="Content calendar for {monthLabel}"`. Each row (7-cell `grid grid-cols-7` row) gets `role="row"`. Each day cell gets `role="gridcell"`.

However, given the complexity of ARIA grid patterns and the visual calendar layout, a simpler approach using `aria-label` on each day `<div>` (without explicit `role="gridcell"`) is acceptable for v1. The campaign entries within each cell are `<button>` elements which are keyboard-focusable by default.

### Sidebar Navigation

Check `frontend/components/layout/Sidebar.tsx` — if `Calendar` is not in the nav items list, add it. The nav should show:
1. Dashboard (`/dashboard`)
2. Campaigns (`/campaigns`)  ← if this link exists
3. Calendar (`/calendar`) ← add this
4. Clients (`/clients`)

Use `CalendarDays` from `lucide-react` as the nav icon (matches the calendar use case better than `Calendar` icon).

### Files to Create / Modify

**New files:**
```
frontend/app/(app)/calendar/page.tsx
frontend/components/calendar/ContentCalendar.tsx
frontend/hooks/useCalendarCampaigns.ts
frontend/__tests__/components/calendar/ContentCalendar.test.tsx
```

**Modified files:**
```
frontend/components/layout/Sidebar.tsx    ← Add Calendar nav link
frontend/lib/types.ts                     ← (already updated in 6.1 — no new changes needed)
frontend/lib/api.ts                       ← (already updated in 6.1 — no new changes needed)
```

**Story 6.1 prerequisite files (must exist before devving 6.2):**
```
frontend/hooks/usePlatformConnections.ts
frontend/components/ui/PlatformIcon.tsx
frontend/hooks/useCampaigns.ts (for listPaginated in api.ts)
backend/app/schemas/campaigns.py (CampaignListResponse)
backend/app/routers/campaigns.py (updated with status comma-split)
```

### References

- Epic 6 story AC: `_bmad-output/planning-artifacts/epics.md#Story-6.2`
- Architecture calendar mapping: `_bmad-output/planning-artifacts/architecture.md#FR-26-27-Dashboard` — `frontend/components/calendar/ContentCalendar.tsx ← FR-27: month view, read-only`
- Architecture calendar page: `_bmad-output/planning-artifacts/architecture.md` — `frontend/app/(app)/calendar/page.tsx ← FR-27: Standalone content calendar (read-only)`
- Paper Style design tokens and calendar grid expectations: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md`
- UX experience: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md:26-33` (Dashboard and Calendar surface definitions)
- Empty state copy: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md:56`
- Accessibility: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md:142`
- `usePlatformConnections` hook: `frontend/hooks/usePlatformConnections.ts` (created in Story 6.1)
- `PlatformIcon` component: `frontend/components/ui/PlatformIcon.tsx` (created in Story 6.1)
- `extractTitle` utility: `frontend/lib/utils.ts` (created in Story 6.1)
- `campaignsApi.listPaginated()`: `frontend/lib/api.ts` (updated in Story 6.1)
- Existing Skeleton component: `frontend/components/ui/Skeleton.tsx`
- Sidebar component to update: `frontend/components/layout/Sidebar.tsx`
- Previous story patterns (5-6): `_bmad-output/implementation-artifacts/5-6-wordpress-com-oauth-integration.md`
- Story 6.1 (prerequisite): `_bmad-output/implementation-artifacts/6-1-campaign-list-dashboard-with-status-filtering.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- All 6.1 prerequisites confirmed in place: comma-separated status filter in backend router, `CampaignListResponse` schema in `types.ts`, `campaignsApi.listPaginated()` in `api.ts`, `usePlatformConnections` hook, `PlatformIcon` component, `extractTitle` utility.
- Calendar nav link (`/calendar`) already existed in `nav-items.ts` from Story 6.1; no modification needed.
- `useCalendarCampaigns` hook fetches all published+approved campaigns; month filtering is done client-side via `campaignsByDate` memoized map — no extra API calls on month navigation.
- `ContentCalendar` uses `role="grid"` + `role="gridcell"` + `role="columnheader"` for accessible table semantics; day headers use `<abbr title="...">` pattern.
- `CalendarEntry` buttons use `draggable={false}` + `onDragStart={e => e.preventDefault()}` per AC #5 (belt-and-suspenders no-drag).
- 10 Vitest tests added covering: month header, published campaign date placement, scheduled campaign date placement, empty state, click navigation, drag prevention, cell aria-label, prev/next month navigation, client switch reactivity.
- Full test suite: 125 tests passed, 0 failures, 0 regressions.

### File List

frontend/app/(app)/calendar/page.tsx (new)
frontend/components/calendar/ContentCalendar.tsx (new)
frontend/hooks/useCalendarCampaigns.ts (new)
frontend/__tests__/components/calendar/ContentCalendar.test.tsx (new)

## Change Log

- 2026-07-04: Implemented Story 6.2 — Content Calendar read-only month view. Created `useCalendarCampaigns` hook, `ContentCalendar` client component with Paper Style grid, `CalendarEntry` sub-component, and `/calendar` page route. Added 10 Vitest tests (all passing). All 7 ACs satisfied.
