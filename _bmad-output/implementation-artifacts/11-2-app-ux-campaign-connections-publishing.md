---
baseline_commit: c59c8a423d50a55337dba36edf295483e05209cd
---

# Story 11.2: App UX — Campaign Access, Connections Discoverability & Publishing Clarity

Status: done

## Story

As an authenticated PersonnaPress user,
I want faster access to creating campaigns, easier discovery of platform connections, and clearer feedback about where content is published,
so that I spend less time navigating the app and more time creating content.

## Acceptance Criteria

1. The Dashboard page header shows a prominent "New Campaign" CTA button alongside the "Dashboard" h1, linking directly to `/campaigns/new`.
2. The Client detail page (`/clients/[id]`) uses a tabbed layout with three tabs: "Profile", "Voice", and "Connections". Each tab shows the content currently in the corresponding section.
3. The "Connections" tab inlines the `PlatformConnectionsClient` component directly (instead of showing a link that navigates away).
4. The `/campaigns/new` page shows a small passive indicator of which platforms are currently connected for the active client (or a "No platforms connected" warning if none are connected).
5. When a campaign is in "published" status, the approval panel footer shows which platforms received the post (e.g. "Published to WordPress, X, LinkedIn") in addition to the timestamp.
6. When a campaign is in "published" status, a "Publish to more platforms" button is shown that re-surfaces the publish controls (Publish now / Schedule / GitHub) — identical UI to the approved state, but labeled "Publish to additional platforms".
7. The "Publish now" button in the approval panel has a subtitle line clarifying scope: "Publishes to all connected platforms".
8. No regressions: the existing "Profile" and "Voice" tab content functions identically to the current client detail page behaviour (save changes, re-analyze URL, file upload, voice profile display, ingestion polling).

## Tasks / Subtasks

- [x] Dashboard: Add "New Campaign" CTA button (AC: 1)
  - [x] Edit `frontend/app/(app)/dashboard/page.tsx`
  - [x] Wrap h1 + CTA in a flex header row: `<div className="flex items-start justify-between mb-10">`
  - [x] Add `<Link href="/campaigns/new">` with primary Paper Style button classes
  - [x] Import `{ ArrowRight, Plus }` from `lucide-react` and `Link` from `next/link`

- [x] Client detail: Convert to tabbed layout (AC: 2, 3, 8)
  - [x] Create `frontend/components/clients/ClientDetailTabs.tsx` (client component — needs `useState` for active tab)
  - [x] Move tab navigation and content-switching logic into this component
  - [x] Tab items: `["Profile", "Voice", "Connections"]`
  - [x] "Profile" tab: renders the "Edit client" form + "Danger zone" sections from current `ClientDetail`
  - [x] "Voice" tab: renders the "Brand voice" section + `FileUploadPanel` from current `ClientDetail`
  - [x] "Connections" tab: renders `<PlatformConnectionsClient clientId={clientId} />` directly (inline)
  - [x] The `ClientDetail` component still handles all existing state (jobId, ingestion polling, save/delete/reanalyze modals) — tabs only control which section is visible
  - [x] URL hash or `searchParams` for active tab is NOT required (simple local state is sufficient)
  - [x] Update `frontend/app/(app)/clients/[id]/page.tsx` — the existing `/clients/[id]/connections` sub-route still works (keep it for direct-link compatibility, e.g. from the approval panel "Connect a platform" link); the page can simply redirect to or render the Connections tab

- [x] New campaign page: Active connections indicator (AC: 4)
  - [x] Edit `frontend/app/(app)/campaigns/new/page.tsx`
  - [x] Fetch connections for `activeClientId` using TanStack Query (key: `["platform-connections", activeClientId]`)
  - [x] Use the existing `publishingApi.listConnections(clientId)` API call
  - [x] Show below the client name line (after the "Writing for: X" mono text):
    - If loading: nothing (don't show skeleton — too noisy for a small passive indicator)
    - If connected platforms exist: small mono text chip row showing platform names
    - If no platforms connected: small warning banner
  - [x] Only fetch when `activeClientId` is set and `hasActiveClient` is true

- [x] Approval panel: Show platforms in published state (AC: 5)
  - [x] Edit `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
  - [x] In the `effectiveStatus === "published"` block, extract platform names from `publish_job.error_details` if available, OR fetch connections at mount time
  - [x] Simplest approach: when status transitions to "published", the `clientHasPlatforms` state is already set + the connections list was fetched during the approved state — store the platform names list in state alongside `clientHasPlatforms`
  - [x] Render: `"Published to WordPress, X, LinkedIn — Jan 1, 2024"` or fall back to `"Published — Jan 1, 2024"` if platform list unavailable

- [x] Approval panel: "Publish to more platforms" button on published state (AC: 6)
  - [x] In the `effectiveStatus === "published"` block, add a secondary action button: "Publish to more platforms"
  - [x] Clicking it sets local state `showRepublishControls = true`
  - [x] When `showRepublishControls` is true, render the same publish control row as the approved state (Publish now / Schedule / GitHub buttons) with a header label `"Publish to additional platforms"`
  - [x] The publish controls call the same handlers (`handlePublishNow`, `handleConfirmSchedule`, `handleConfirmGitHubPublish`)
  - [x] Re-fetch connections on mount of the published state (same effect as in approved state) so buttons are accurate

- [x] Approval panel: "Publishes to all connected platforms" subtitle (AC: 7)
  - [x] Below the "Publish now" button, add: `<p className="font-mono text-xs text-graphite mt-1">Publishes to all connected platforms</p>`
  - [x] Apply only to the "Publish now" button, not to Schedule or GitHub buttons

## Dev Notes

### Dashboard header CTA — Paper Style spec

```tsx
// Modified app/(app)/dashboard/page.tsx
import Link from "next/link";
import { ArrowRight } from "lucide-react";
// ...

export default async function DashboardPage() {
  return (
    <>
      <header className="mb-10 flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink mb-1">Dashboard</h1>
          <p className="text-sm text-graphite font-mono">Your content pipeline at a glance.</p>
        </div>
        <Link
          href="/campaigns/new"
          className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-2.5 shadow-brutal hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all shrink-0 focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
        >
          <ArrowRight className="size-3.5" aria-hidden="true" />
          New Campaign
        </Link>
      </header>
      {/* ... existing CampaignList Suspense ... */}
    </>
  );
}
```

Note: Dashboard is an RSC. The Link component works fine in RSC. No "use client" needed here.

### Client detail tabs — Paper Style spec

```tsx
// frontend/components/clients/ClientDetailTabs.tsx
"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";

const TABS = ["Profile", "Voice", "Connections"] as const;
type Tab = typeof TABS[number];

interface Props {
  clientId: string;
  defaultTab?: Tab;
  profileContent: React.ReactNode;
  voiceContent: React.ReactNode;
  connectionsContent: React.ReactNode;
}

export function ClientDetailTabs({ profileContent, voiceContent, connectionsContent, defaultTab = "Profile" }: Props) {
  const [active, setActive] = useState<Tab>(defaultTab);

  return (
    <div>
      {/* Tab bar */}
      <div className="flex border-b border-border mb-8" role="tablist" aria-label="Client settings">
        {TABS.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={active === tab}
            aria-controls={`tabpanel-${tab.toLowerCase()}`}
            id={`tab-${tab.toLowerCase()}`}
            onClick={() => setActive(tab)}
            className={cn(
              "font-mono text-xs uppercase tracking-widest px-6 py-3 border-b-2 -mb-px transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-inset",
              active === tab
                ? "border-ink text-ink"
                : "border-transparent text-graphite hover:text-ink hover:border-border"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      <div
        id="tabpanel-profile"
        role="tabpanel"
        aria-labelledby="tab-profile"
        hidden={active !== "Profile"}
      >
        {profileContent}
      </div>
      <div
        id="tabpanel-voice"
        role="tabpanel"
        aria-labelledby="tab-voice"
        hidden={active !== "Voice"}
      >
        {voiceContent}
      </div>
      <div
        id="tabpanel-connections"
        role="tabpanel"
        aria-labelledby="tab-connections"
        hidden={active !== "Connections"}
      >
        {connectionsContent}
      </div>
    </div>
  );
}
```

**Tab styling rationale:** Border-bottom indicator (`border-b-2 border-ink`) on active tab. Font-mono uppercase tracking-widest matches the Paper Style section labels used throughout the app. No rounded corners. No background fill on active tab. `hidden` prop (not `display:none` via class) on inactive panels preserves accessibility — screen readers skip `hidden` panels.

**Integration in ClientDetail.tsx:** Wrap the existing three sections into the tab component. The Profile tab gets: "Edit client" section + "Danger zone". The Voice tab gets: "Brand voice" section + `FileUploadPanel`. The Connections tab gets `<PlatformConnectionsClient clientId={clientId} />`.

**CRITICAL:** Keep all existing state and handlers in `ClientDetail` (or its parent). Do NOT split the modal state across components. The tab component is purely presentational (receives ReactNode children). All the `handleSave`, `showReAnalyzeModal`, `showDeleteModal` logic stays in `ClientDetail`.

**Connections sub-route:** `app/(app)/clients/[id]/connections/page.tsx` currently exists as a standalone page (used by the approval panel deep-link "Connect a platform"). Keep this page working — do NOT remove it. The `PlatformConnectionsClient` now renders in two places: the tab AND the standalone connections page. This is intentional.

### New campaign page — connections indicator spec

```tsx
// In app/(app)/campaigns/new/page.tsx
// Add TanStack Query import
import { useQuery } from "@tanstack/react-query";
import { publishingApi } from "@/lib/api";

// Inside NewCampaignPage(), after existing hooks:
const { data: connectionsData } = useQuery({
  queryKey: ["platform-connections", activeClientId],
  queryFn: () => publishingApi.listConnections(activeClientId!),
  enabled: !!activeClientId,
  staleTime: 2 * 60_000,
});

const connectedPlatforms = (connectionsData?.items ?? [])
  .filter((c) => c.connected)
  .map((c) => platformLabel(c.platform)); // helper below

// Platform label helper (add above component):
function platformLabel(platform: string): string {
  const MAP: Record<string, string> = {
    wordpress: "WordPress",
    "wordpress-com": "WordPress.com",
    webflow: "Webflow",
    x: "X",
    linkedin: "LinkedIn",
    github_pages: "GitHub Pages",
  };
  return MAP[platform] ?? platform;
}
```

**Render after the "Writing for: X" line (and before the warnings):**

```tsx
{hasActiveClient && (
  connectedPlatforms.length > 0 ? (
    <p className="font-mono text-xs text-graphite mb-4">
      Publishing to: <span className="text-ink">{connectedPlatforms.join(" · ")}</span>
    </p>
  ) : connectionsData !== undefined ? (
    <div className="mb-4 border border-ink/10 bg-paper px-4 py-3">
      <p className="text-sm font-mono text-graphite">
        No platforms connected.{" "}
        <Link
          href={`/clients/${activeClient!.id}/connections`}
          className="underline hover:text-ink"
        >
          Connect a platform
        </Link>
        {" "}to publish after approval.
      </p>
    </div>
  ) : null
)}
```

Note: Only show when `connectionsData !== undefined` (loaded) to avoid flash. When loading (`undefined`), render nothing.

### Approval panel: published state with platforms + republish

In the `effectiveStatus === "published"` block:

**State additions needed:**
```tsx
const [showRepublishControls, setShowRepublishControls] = useState(false);
const [publishedPlatforms, setPublishedPlatforms] = useState<string[]>([]);
```

**Fetch connections on published state mount** (same pattern as approved state but for published):
```tsx
useEffect(() => {
  if (effectiveStatus === "published" && clientHasPlatforms === null) {
    fetchAPI<{ items: Array<{ platform: string; connected: boolean }> }>(`/clients/${campaign.client_id}/connections`)
      .then((connections) => {
        const items = connections?.items ?? [];
        const connected = items.filter((c) => c.connected).map((c) => platformLabel(c.platform));
        setPublishedPlatforms(connected);
        setClientHasPlatforms(items.length > 0);
        // ... existing github detection logic if needed for republish
      })
      .catch(() => { setClientHasPlatforms(false); });
  }
}, [effectiveStatus, campaign.client_id, clientHasPlatforms]);
```

**Published state render:**
```tsx
if (effectiveStatus === "published") {
  const publishedLine = publishedPlatforms.length > 0
    ? `Published to ${publishedPlatforms.join(", ")}`
    : "Published";

  return (
    <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border">
      <div className="px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-graphite">
          <span className="font-medium text-ink">{publishedLine}</span>
          {" — "}
          <span>
            {new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(
              new Date(campaign.updated_at),
            )}
          </span>
        </p>
        <button
          type="button"
          onClick={() => setShowRepublishControls((v) => !v)}
          className="font-mono text-xs text-graphite underline underline-offset-2 hover:text-ink transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
        >
          {showRepublishControls ? "Hide publish options" : "Publish to more platforms"}
        </button>
      </div>

      {showRepublishControls && (
        <div className="px-6 pb-4 pt-0 border-t border-border">
          <p className="font-mono text-xs text-graphite uppercase tracking-wider mb-3 pt-3">
            Publish to additional platforms
          </p>
          {/* Re-use same publish button row from approved state */}
          <div className="flex items-center gap-3 flex-wrap">
            {githubPublishReady && (
              <button type="button" onClick={() => setShowGitHubPanel((v) => !v)}
                className="inline-flex items-center gap-2 px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none">
                <GitBranch className="size-4" aria-hidden="true" />
                Publish to GitHub
              </button>
            )}
            <button type="button" onClick={() => setShowSchedulePicker((v) => !v)}
              className="inline-flex items-center px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none">
              Schedule
            </button>
            <div className="flex flex-col gap-1">
              <button type="button" onClick={handlePublishNow} disabled={isPublishing || isGitHubPublishing}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm font-medium border border-transparent shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none">
                {isPublishing ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
                {isPublishing ? "Publishing..." : "Publish now"}
              </button>
              <p className="font-mono text-xs text-graphite">Publishes to all connected platforms</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

**"Publishes to all connected platforms" note (AC: 7)** also applies to the approved state panel. Add the same `<p>` below the "Publish now" button in the approved state's `clientHasPlatforms === true` branch.

### platformLabel helper

Add this helper near the top of `approval-panel.tsx` (outside the component, same file):
```tsx
function platformLabel(platform: string): string {
  const MAP: Record<string, string> = {
    wordpress: "WordPress",
    "wordpress-com": "WordPress.com",
    webflow: "Webflow",
    x: "X",
    linkedin: "LinkedIn",
    github_pages: "GitHub Pages",
  };
  return MAP[platform] ?? platform;
}
```

### RSC constraint reminder

`app/(app)/campaigns/new/page.tsx` is currently `"use client"` — it already has hooks. Adding `useQuery` there is safe and consistent with the RSC rule from project-context.md (all data fetching in client components via TanStack Query).

`app/(app)/dashboard/page.tsx` is currently an async RSC (no `"use client"`). The new CTA is a `<Link>` — no interactivity needed. Stays RSC. Do NOT add `"use client"` to the dashboard page.

### Project Structure Notes

- Modified: `frontend/app/(app)/dashboard/page.tsx` (add CTA)
- New: `frontend/components/clients/ClientDetailTabs.tsx`
- Modified: `frontend/components/clients/ClientDetail.tsx` (restructure content into tab children)
- Modified: `frontend/app/(app)/campaigns/new/page.tsx` (add connections query + indicator)
- Modified: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` (published state + republish + subtitle)
- Unchanged: `frontend/app/(app)/clients/[id]/connections/page.tsx` (keep standalone route for approval panel deep-link)

### References

- Dashboard page: `frontend/app/(app)/dashboard/page.tsx`
- ClientDetail: `frontend/components/clients/ClientDetail.tsx`
- PlatformConnectionsClient: `frontend/components/publishing/PlatformConnectionsClient.tsx`
- New campaign page: `frontend/app/(app)/campaigns/new/page.tsx`
- Approval panel: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` lines 334–651
- Published state block: `approval-panel.tsx` lines 637–651
- Approved state platform fetch: `approval-panel.tsx` lines 112–136
- Nav items (sidebar has no connections entry): `frontend/components/layout/nav-items.ts`
- RSC rule: `_bmad-output/project-context.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Dashboard `page.tsx`: Added "New Campaign" CTA link with ArrowRight icon using `shadow-brutal` Paper Style. Stays as RSC (no `"use client"` added).
- Created `ClientDetailTabs.tsx`: Pure presentational client component with `useState` for active tab; uses `hidden` prop for accessible tab panels.
- `ClientDetail.tsx`: Restructured return to split content into three ReactNode variables (profileContent, voiceContent, connectionsContent). All state/modals stay in ClientDetail. Connections tab renders `PlatformConnectionsClient` inline. Standalone `/clients/[id]/connections` route unchanged.
- `campaigns/new/page.tsx`: Added `useQuery` for connections via `publishingApi.listConnections`. Shows "Publishing to: X · Y" when loaded and connected, warning banner when no platforms connected, nothing while loading.
- `approval-panel.tsx`: Added `platformLabel` helper, `showRepublishControls` + `publishedPlatforms` state, `useEffect` for published state connection fetch (mirrors approved state effect). Published state now shows "Published to X, Y" with "Publish to more platforms" toggle button. Republish controls section includes full Publish now/Schedule/GitHub panel. "Publishes to all connected platforms" subtitle added to approved state "Publish now" button.
- TypeScript: 2 pre-existing errors in ClientDetail (unrelated to this story). Zero new errors introduced.

### File List

- frontend/app/(app)/dashboard/page.tsx (modified)
- frontend/components/clients/ClientDetailTabs.tsx (new)
- frontend/components/clients/ClientDetail.tsx (modified)
- frontend/app/(app)/campaigns/new/page.tsx (modified)
- frontend/app/(app)/campaigns/[id]/approval-panel.tsx (modified)

### Review Findings

- [x] [Review][Patch] GitHub republish panel body invisible on second open — `githubResult` from prior publish never reset when user clicks "Publish to GitHub" in republish controls [approval-panel.tsx:752]
- [x] [Review][Patch] Stale `scheduledAt` in republish Schedule picker — old datetime persists after publish, causing immediate `isPastTime` error [approval-panel.tsx:726]
- [x] [Review][Patch] `clientId` prop declared in ClientDetailTabs Props but never destructured or used [ClientDetailTabs.tsx:10]
- [x] [Review][Defer] `platformLabel` helper duplicated verbatim in approval-panel.tsx and new/page.tsx — deferred, pre-existing by spec placement

## Change Log

- 2026-07-10: Implemented all 6 tasks — Dashboard "New Campaign" CTA, Client detail tabbed layout (Profile/Voice/Connections), New campaign connections indicator, Approval panel published-state platform list + "Publish to more platforms" republish controls + "Publishes to all connected platforms" subtitle (claude-sonnet-4-6)
- 2026-07-10: Code review — 3 patches applied (githubResult reset on republish GitHub open, scheduledAt reset on republish schedule open, clientId removed from ClientDetailTabs Props), marked done (claude-sonnet-4-6)
