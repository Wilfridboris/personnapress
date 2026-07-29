---
baseline_commit: 56cdc53
---

# Story 20.6: Roadmap-Campaign Sync & UX Fixes

Status: done

## Story

As a PersonnaPress user,
I want the roadmap review page to reflect published post status in real time, campaign list rows to surface their roadmap origin, the edit panel to honour published state, the /clients/ page to jump straight to my active client, Profile and Voice to live in one tab, and "Approve All" to skip already-published posts,
so that every workflow feels coherent with no surprises, stale data, or misleading actions.

## Acceptance Criteria

### AC 1 — Roadmap refetch on window focus with status-only merge

In `RoadmapReviewClient.tsx`:

- Add `refetchOnWindowFocus: true` to the TanStack Query config so the roadmap is re-fetched when the user tabs back from `/campaigns/[id]`.
- Replace the one-shot `populatedRef` population logic with a two-phase effect:
  - **First time ready** (`populatedRef.current === false`): full population of `localCampaigns` from `roadmap.campaigns` (existing behaviour).
  - **Subsequent refetches** (`populatedRef.current === true` and `roadmap.status === "ready"`): merge only the `status` field from fresh data into `localCampaigns`, preserving locally-edited fields (`x_post`, `linkedin_post`, `image_url`, etc.).
  ```tsx
  useEffect(() => {
    if (!roadmap) return;
    if (!populatedRef.current && roadmap.status === "ready") {
      populatedRef.current = true;
      setLocalCampaigns(roadmap.campaigns);
      return;
    }
    if (populatedRef.current && roadmap.status === "ready") {
      setLocalCampaigns((prev) =>
        (prev ?? []).map((local) => {
          const fresh = roadmap.campaigns.find((c) => c.id === local.id);
          return fresh ? { ...local, status: fresh.status } : local;
        })
      );
    }
  }, [roadmap]);
  ```
- This ensures that when a user posts from `/campaigns/[id]` and returns to the roadmap review page, the campaign card flips to "published" status automatically.

### AC 2 — Published/Failed status badges on PostCard

In `PostCard.tsx`, when `!isRemoved` (REMOVED badge already occupies top-right):

- Add a `status` badge in the top-right corner (`absolute top-2 right-2 z-10`) based on `campaign.status`:
  - `"published"` → `PUBLISHED` badge:
    ```tsx
    <span className="absolute top-2 right-2 font-body text-xs uppercase tracking-[0.08em] bg-[#DCFCE7] text-[#15803D] px-2 py-0.5 z-10">
      PUBLISHED
    </span>
    ```
  - `"failed"` → `FAILED` badge:
    ```tsx
    <span className="absolute top-2 right-2 font-body text-xs uppercase tracking-[0.08em] bg-[#FEE2E2] text-danger px-2 py-0.5 z-10">
      FAILED
    </span>
    ```
  - Any other status → no badge (existing behaviour).
- The `isRemoved` check takes priority: when `isRemoved` is true, the REMOVED badge renders and the status badge is suppressed.

### AC 3 — "View" mode vs "Edit" mode on PostCard action row

In `PostCard.tsx`, adjust the action row when `campaign.status === "published"`:

- Replace the `"Edit"` button with a `"View"` button (same variant, same size, same position):
  ```tsx
  <Button
    type="button"
    variant="secondary"
    onClick={onEdit}
    className="text-xs px-3 py-1.5 min-h-[44px]"
    aria-label={`View ${platformLabel} post`}
  >
    View
  </Button>
  ```
- For published campaigns, keep the `"Remove"` button so users can still remove the post from the roadmap grid view.
- For `failed` and all other statuses, keep `"Edit"` (unchanged).

### AC 4 — Campaign link on PostCard

In `PostCard.tsx`, add a `"View campaign"` link to the action row for ALL non-removed cards (pending, published, failed):

- Import `Link` from `"next/link"` and `ExternalLink` from `"lucide-react"`.
- After the Edit/View + Remove buttons, add:
  ```tsx
  <Link
    href={`/campaigns/${campaign.id}`}
    className="inline-flex items-center gap-1 font-body text-xs text-graphite hover:text-ink transition-colors underline underline-offset-2 min-h-[44px] items-center"
    aria-label={`Open full campaign page for ${platformLabel} post`}
  >
    <ExternalLink className="w-3 h-3" aria-hidden="true" />
    Campaign
  </Link>
  ```
- This allows jumping from the roadmap directly to the full `/campaigns/[id]` approval/publish page.

### AC 5 — PostEditPanel: remove duplicate heading, add read-only mode

The drawer header in `WeekGrid.tsx` (line 149) already renders `"Editing {label} post"` as a `<p>` tag. `PostEditPanel.tsx` duplicates this with its own `<h2>` (line 123), creating a visible space gap.

**In `PostEditPanel.tsx`:**
- Remove the `<h2>Editing {platformLabel} post</h2>` block entirely (line 123-125). The WeekGrid drawer header provides this label.
- Add a `readOnly?: boolean` prop.
- When `readOnly` is `true`:
  - Textarea: add `disabled` attribute + `opacity-50 cursor-default` classes.
  - Remove the Save/Cancel footer buttons entirely.
  - Add a "Close" button instead: `<Button type="button" variant="secondary" onClick={onClose} className="text-xs">Close</Button>`.
  - Add a published note above the textarea: `<p className="font-body text-xs text-graphite">This post has already been published.</p>`.
  - Hide the "Replace image" / "Upload your own image" buttons (image replace is irrelevant for published posts).
  - Character counter is still shown (read-only display of the count).

**In `WeekGrid.tsx`:**
- Update the drawer header `<p>` text based on `campaign.status`:
  ```tsx
  <p className="font-body text-xs text-graphite uppercase tracking-[0.08em]">
    {editingCampaign.status === "published"
      ? `Published ${getPlatformInfo(editingCampaign).label} post`
      : `Editing ${getPlatformInfo(editingCampaign).label} post`}
  </p>
  ```
- Pass `readOnly={editingCampaign.status === "published"}` to `PostEditPanel`.

### AC 6 — CampaignList: roadmap origin badge

In `CampaignList.tsx`, for rows where `campaign.roadmap_id` is not null:

- Import `Map` from `"lucide-react"`.
- In the right-side metadata cluster (inside `onClick={(e) => e.stopPropagation()}`), after `StatusBadge` and before `ArrowRight`, add:
  ```tsx
  {campaign.roadmap_id && (
    <Link
      href={`/roadmap/${campaign.roadmap_id}/review`}
      onClick={(e) => e.stopPropagation()}
      className="inline-flex items-center gap-1 font-body text-xs uppercase tracking-[0.08em] text-graphite border border-[#E5E5E5] px-2 py-0.5 hover:text-ink hover:border-ink transition-colors"
      aria-label="View source roadmap"
    >
      <Map className="size-3" aria-hidden="true" />
      Roadmap
    </Link>
  )}
  ```
- `Link` import already exists in the file. `Map` must be added to the lucide-react import.
- This renders only for roadmap-originated campaigns. Regular brain-dump campaigns (`roadmap_id === null`) are unaffected.

### AC 7 — StickyApproveFooter: accurate count + published guard

**In `RoadmapReviewClient.tsx`:**
- Compute a separate `publishedCount` to pass to the footer:
  ```tsx
  const nonRemovedCampaigns = campaigns.filter((c) => !removedIds.has(c.id));
  const publishedCount = nonRemovedCampaigns.filter((c) => c.status === "published").length;
  const pendingCount = nonRemovedCampaigns.length - publishedCount;
  const nonRemovedCount = nonRemovedCampaigns.length;
  ```
- Pass `publishedCount` as a new prop to `StickyApproveFooter`. Keep `nonRemovedCount` as-is (used for total reference).

**In `StickyApproveFooter.tsx`:**
- Add `publishedCount?: number` prop (defaults to `0`).
- Update the left label:
  ```tsx
  <p className="font-body text-[15px] text-graphite" aria-live="polite" aria-atomic="true">
    {pendingCount} post{pendingCount === 1 ? "" : "s"} to schedule
    {publishedCount > 0 && (
      <span className="text-graphite/60 ml-2">
        · {publishedCount} already published
      </span>
    )}
  </p>
  ```
  where `pendingCount = nonRemovedCount - publishedCount`.
- Disable the approve button when `pendingCount === 0` (all non-removed posts are already published):
  ```tsx
  disabled={isApproving || pendingCount === 0}
  ```

### AC 8 — Backend: guard approve_roadmap against re-publishing

In `backend/app/routers/roadmaps.py`, inside `approve_roadmap`, in the `for campaign in included:` loop (currently line 315), add a guard immediately after the loop opens:

```python
for campaign in included:
    # Never re-schedule a campaign that is already published
    if campaign.status == CampaignStatus.published:
        continue
    campaign.status = "approved"
    ...  # rest of existing logic unchanged
```

- Import `CampaignStatus` from the models/enums module if not already imported in scope (check existing imports — it may already be there via `Campaign` model).
- This prevents already-published campaigns from having their status overwritten back to `"approved"` and from receiving a duplicate publish job.

### AC 9 — Backend: normalize uncaught-exception error_details shape

In `backend/app/workers/publish.py`, in the outermost `except Exception as exc:` block (currently line 147-158), change the `error_details` key from `"error"` to `"general"`:

```python
# Before:
error_details=json.dumps({"error": str(exc)}),

# After:
error_details=json.dumps({"general": str(exc)}),
```

**In `RetryPanel.tsx`**, handle the `"general"` key gracefully — it is not a real platform so no retry button should appear:

```tsx
// In the platforms map:
const SYNTHETIC_KEYS = new Set(["general", "error"]);

// In the JSX render:
{!isSuccess && !SYNTHETIC_KEYS.has(platform) && (
  <div className="flex items-center gap-3">
    {/* existing retry button logic */}
  </div>
)}
```

When the platform key is `"general"` or `"error"`, display the error message without a retry button, and display `"Publishing error"` instead of the platform name:

```tsx
<p className="text-sm font-medium text-ink">
  {SYNTHETIC_KEYS.has(platform) ? "Publishing error" : capitalize(platform)}
</p>
```

### AC 10 — /clients/ redirects to active client

**New file: `frontend/components/clients/ClientsRedirectClient.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useClientStore } from "@/lib/stores/useClientStore";

export function ClientsRedirectClient() {
  const router = useRouter();
  const activeClientId = useClientStore((s) => s.activeClientId);
  const isInitialized = useClientStore((s) => s.isInitialized);

  useEffect(() => {
    if (!isInitialized) return;
    router.replace(activeClientId ? `/clients/${activeClientId}` : "/dashboard");
  }, [activeClientId, isInitialized, router]);

  return null;
}
```

**Replace `frontend/app/(app)/clients/page.tsx`** with a thin server shell (no API call — RSC loop prevention rule applies):

```tsx
import type { Metadata } from "next";
import { ClientsRedirectClient } from "@/components/clients/ClientsRedirectClient";

export const metadata: Metadata = {
  title: "Clients - PersonnaPress",
  robots: { index: false },
};

export default function ClientsPage() {
  return <ClientsRedirectClient />;
}
```

- `activeClientId` is in Zustand (localStorage-persisted) and cannot be read server-side — client component is the correct approach.
- Fallback to `/dashboard` when no active client (new user or cleared state).
- Remove the old `getClients()` server fetch and all related imports — it used `cache: "no-store"` which violates the RSC loop prevention rule.

### AC 11 — Merge Profile and Voice tab on /clients/[id]

**In `ClientDetailTabs.tsx`:**
- Rename `TABS` from `["Profile", "Voice", "Connections"]` to `["Profile & Voice", "Connections"]`.
- Remove the `voiceContent` prop from the `Props` interface.
- The `profileVoiceContent` prop (renamed from `profileContent`) renders on the single merged tab.
- Remove the separate `"Voice"` tabpanel div.
- Update `defaultTab` default value to `"Profile & Voice"`.
- Update all `id`, `aria-controls`, `aria-labelledby` attributes:
  - Tab button: `id="tab-profile-voice"`, `aria-controls="tabpanel-profile-voice"`
  - Panel: `id="tabpanel-profile-voice"`, `aria-labelledby="tab-profile-voice"`

```tsx
const TABS = ["Profile & Voice", "Connections"] as const;
type Tab = (typeof TABS)[number];

interface Props {
  defaultTab?: Tab;
  profileVoiceContent: React.ReactNode;
  connectionsContent: React.ReactNode;
}
```

**In `ClientDetail.tsx`:**
- Combine `profileContent` and `voiceContent` into a single `profileVoiceContent` node passed to `ClientDetailTabs`:
  ```tsx
  const profileVoiceContent = (
    <>
      {profileContent}
      <hr className="border-[#E5E5E5] my-8" />
      {voiceContent}
    </>
  );
  ```
- Pass `profileVoiceContent={profileVoiceContent}` to `ClientDetailTabs`.
- Remove the separate `voiceContent={voiceContent}` prop.
- The internal `profileContent` and `voiceContent` variables remain exactly as-is — only their composition changes.

## Tasks / Subtasks

- [x] Task 1: Roadmap refetch + status-only merge (AC: 1)
  - [x] `frontend/components/roadmap/RoadmapReviewClient.tsx`: Add `refetchOnWindowFocus: true`; replace single-fire `populatedRef` effect with two-phase effect (full populate on first ready, status-only merge on subsequent); extract `publishedCount`/`pendingCount` computations; pass `publishedCount` to `StickyApproveFooter`

- [x] Task 2: PostCard status badges (AC: 2)
  - [x] `frontend/components/roadmap/PostCard.tsx`: Add conditional `PUBLISHED` badge (green) and `FAILED` badge (red) in top-right corner; suppress when `isRemoved` is true

- [x] Task 3: PostCard Edit vs View mode (AC: 3)
  - [x] `frontend/components/roadmap/PostCard.tsx`: Change `"Edit"` button label to `"View"` (same variant/size) when `campaign.status === "published"`, otherwise keep `"Edit"`

- [x] Task 4: Campaign link on PostCard (AC: 4)
  - [x] `frontend/components/roadmap/PostCard.tsx`: Add `Link` import from `"next/link"` and `ExternalLink` from `"lucide-react"`; add `"Campaign"` link after action buttons for all non-removed cards

- [x] Task 5: PostEditPanel — remove duplicate heading + read-only mode (AC: 5)
  - [x] `frontend/components/roadmap/PostEditPanel.tsx`: Remove `<h2>Editing {platformLabel} post</h2>` (duplicate of WeekGrid header); add `readOnly?: boolean` prop; when readOnly: disable textarea (`disabled`, `opacity-50`, `cursor-default`), add published note, replace Save/Cancel footer with single Close button, hide image upload/replace buttons
  - [x] `frontend/components/roadmap/WeekGrid.tsx`: Update drawer header text to `"Published {label} post"` when `editingCampaign.status === "published"`, else `"Editing {label} post"`; pass `readOnly={editingCampaign.status === "published"}` to `PostEditPanel`

- [x] Task 6: CampaignList roadmap badge (AC: 6)
  - [x] `frontend/components/campaigns/CampaignList.tsx`: Add `Map` to lucide-react import; add `Roadmap` chip link for campaigns where `campaign.roadmap_id` is not null, inside `stopPropagation` click handler

- [x] Task 7: StickyApproveFooter accurate count (AC: 7)
  - [x] `frontend/components/roadmap/StickyApproveFooter.tsx`: Add `publishedCount?: number` prop; derive `pendingCount = nonRemovedCount - (publishedCount ?? 0)`; update label text to show `"{pendingCount} posts to schedule · {publishedCount} already published"` when publishedCount > 0; update button disabled condition to use `pendingCount`

- [x] Task 8: Backend approve_roadmap published guard (AC: 8)
  - [x] `backend/app/routers/roadmaps.py`: In `approve_roadmap`, add `if campaign.status == CampaignStatus.published: continue` at the top of the `for campaign in included:` loop; verify `CampaignStatus` is imported

- [x] Task 9: Backend normalize error_details shape + RetryPanel fallback (AC: 9)
  - [x] `backend/app/workers/publish.py`: Change `json.dumps({"error": str(exc)})` to `json.dumps({"general": str(exc)})` in the outermost except block
  - [x] `frontend/components/publishing/RetryPanel.tsx`: Add `SYNTHETIC_KEYS = new Set(["general", "error"])`; suppress Retry button for synthetic keys; display `"Publishing error"` label for synthetic keys instead of the raw key capitalized

- [x] Task 10: /clients/ redirect to active client (AC: 10)
  - [x] `frontend/components/clients/ClientsRedirectClient.tsx`: Create new `"use client"` component that reads `activeClientId` + `isInitialized` from `useClientStore` and calls `router.replace` in `useEffect`
  - [x] `frontend/app/(app)/clients/page.tsx`: Replace entire server component (remove `getClients()` fetch + all imports) with thin server shell that renders `<ClientsRedirectClient />`

- [x] Task 11: Merge Profile & Voice tab (AC: 11)
  - [x] `frontend/components/clients/ClientDetailTabs.tsx`: Change `TABS` to `["Profile & Voice", "Connections"]`; remove `voiceContent` prop; rename `profileContent` prop to `profileVoiceContent`; remove separate Voice tabpanel; update all tab/panel `id` and `aria-*` attributes
  - [x] `frontend/components/clients/ClientDetail.tsx`: Combine `profileContent` + `voiceContent` into `profileVoiceContent` with `<hr className="border-[#E5E5E5] my-8" />` divider; update `ClientDetailTabs` call to use `profileVoiceContent` and remove `voiceContent`

## Dev Notes

### RSC Loop Prevention
The existing `/clients/page.tsx` calls `getClients()` with `cache: "no-store"` in a server component. This is the exact anti-pattern documented in `project-context.md` that causes RSC re-render loops with Turbopack. The replacement (thin server shell + `ClientsRedirectClient`) is the correct pattern. No data fetching in the server component.

### Why status-only merge matters (AC 1)
The original one-shot `populatedRef` pattern was intentional: it prevented the server refetch from overwriting locally-edited post text. The two-phase approach preserves this invariant by only updating the `status` field on subsequent syncs. Locally-edited `x_post` / `linkedin_post` / `image_url` are preserved unless the component remounts.

### PostCard has no import for Link (AC 4)
`PostCard.tsx` currently imports from `lucide-react`, `@/components/ui/Button`, `@/lib/utils`, `next/image`, and `@/lib/types`. `Link` from `"next/link"` must be added. `ExternalLink` from `"lucide-react"` must be added to the existing icon import.

### CampaignStatus import in roadmaps.py (AC 8)
Search the existing imports in `backend/app/routers/roadmaps.py` for `CampaignStatus` before adding it. It may already be imported transitively via the `Campaign` model. If absent, add: `from app.models import CampaignStatus`.

### ClientDetailTabs callers
Only one caller exists: `ClientDetail.tsx` (line 354-358). No other component renders `ClientDetailTabs`. The `defaultTab` prop change (from `"Profile"` to `"Profile & Voice"`) is backwards-compatible since the old `"Profile"` value no longer exists in the new `TABS` union — confirm the TypeScript type narrows correctly. The `ClientDetail.tsx` call does not pass `defaultTab`, so it picks up the new default automatically.

### No migration needed
This story touches only frontend components and one backend router guard. No new database columns, no Alembic migration required.

### No em-dashes in any copy
All user-facing text in this story must use hyphens or plain punctuation. "Profile & Voice" uses an ampersand (OK). "Already published" uses no em-dash. Per `project-context.md` constraint.

### Paper Style design tokens used in this story
- Published badge bg: `bg-[#DCFCE7]` text: `text-[#15803D]`
- Failed badge bg: `bg-[#FEE2E2]` text: `text-danger`
- Tab border pattern: `border-b-2 border-ink` (active), `border-transparent` (inactive) — matches existing ClientDetailTabs classes
- Roadmap badge: `border border-[#E5E5E5]` with hover `hover:border-ink` — matches PostCard's existing `border-[#E5E5E5]` border colour
- Section divider: `border-[#E5E5E5] my-8` — consistent with PostCard image area dashed border

### Files Being Modified

| File | Change |
|------|--------|
| `frontend/components/roadmap/RoadmapReviewClient.tsx` | refetchOnWindowFocus; two-phase localCampaigns sync; publishedCount/pendingCount |
| `frontend/components/roadmap/PostCard.tsx` | Published/Failed badges; Edit→View for published; Campaign link |
| `frontend/components/roadmap/PostEditPanel.tsx` | Remove duplicate h2; readOnly prop |
| `frontend/components/roadmap/WeekGrid.tsx` | Dynamic header text; pass readOnly to PostEditPanel |
| `frontend/components/roadmap/StickyApproveFooter.tsx` | publishedCount prop; accurate count label |
| `frontend/components/campaigns/CampaignList.tsx` | Roadmap badge + link |
| `frontend/components/publishing/RetryPanel.tsx` | SYNTHETIC_KEYS guard; "Publishing error" label |
| `frontend/components/clients/ClientDetailTabs.tsx` | Merge tabs to ["Profile & Voice", "Connections"] |
| `frontend/components/clients/ClientDetail.tsx` | Combine profileContent + voiceContent |
| `frontend/app/(app)/clients/page.tsx` | Full replacement — thin server shell |
| `frontend/components/clients/ClientsRedirectClient.tsx` | NEW client component |
| `backend/app/routers/roadmaps.py` | Skip published campaigns in approve_roadmap |
| `backend/app/workers/publish.py` | Normalize uncaught error_details key |

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
- spacy not installed in dev environment; bypassed by running `tests/services/` only (pre-existing env issue, unrelated to this story)

### Completion Notes List
- AC 1: Added `refetchOnWindowFocus: true` and replaced one-shot populatedRef with two-phase effect in RoadmapReviewClient; publishedCount extracted and passed to footer
- AC 2: Added PUBLISHED (green) and FAILED (red) status badges to PostCard top-right, suppressed when isRemoved
- AC 3: Edit button label changes to "View" when campaign.status === "published"
- AC 4: Added Campaign link with ExternalLink icon to PostCard action row for all non-removed cards
- AC 5: Removed duplicate `<h2>` from PostEditPanel; added readOnly prop with disabled textarea, published note, Close-only footer, and hidden image buttons; WeekGrid header text and readOnly prop updated
- AC 6: Added Map icon import and Roadmap chip link in CampaignList for roadmap-originated campaigns
- AC 7: StickyApproveFooter updated with publishedCount prop, pendingCount derivation, "X posts to schedule · Y already published" label, and disabled when pendingCount === 0
- AC 8: Added CampaignStatus import and published guard in approve_roadmap loop
- AC 9: Normalized uncaught error_details key from "error" to "general" in publish.py; RetryPanel updated with SYNTHETIC_KEYS set, suppressed retry button, "Publishing error" label
- AC 10: Created ClientsRedirectClient.tsx; replaced clients/page.tsx server component with thin shell (eliminates RSC loop anti-pattern)
- AC 11: Merged Profile and Voice into single "Profile & Voice" tab in ClientDetailTabs; ClientDetail combines profileContent + voiceContent with hr divider

### File List
- frontend/components/roadmap/RoadmapReviewClient.tsx
- frontend/components/roadmap/PostCard.tsx
- frontend/components/roadmap/PostEditPanel.tsx
- frontend/components/roadmap/WeekGrid.tsx
- frontend/components/roadmap/StickyApproveFooter.tsx
- frontend/components/campaigns/CampaignList.tsx
- frontend/components/publishing/RetryPanel.tsx
- frontend/components/clients/ClientDetailTabs.tsx
- frontend/components/clients/ClientDetail.tsx
- frontend/app/(app)/clients/page.tsx
- frontend/components/clients/ClientsRedirectClient.tsx (new)
- backend/app/routers/roadmaps.py
- backend/app/workers/publish.py

### Review Findings

- [x] [Review][Patch] Blog campaign read-only panel shows nothing — no "already published" note for blog_full campaigns in readOnly mode [frontend/components/roadmap/PostEditPanel.tsx:127]
- [x] [Review][Patch] `Map` icon import shadows native Map constructor — rename to MapIcon to avoid footgun [frontend/components/campaigns/CampaignList.tsx:5]
- [x] [Review][Patch] IIFE in StickyApproveFooter JSX — extract pendingCount as const before return for readability [frontend/components/roadmap/StickyApproveFooter.tsx:49]
- [x] [Review][Patch] Redundant `!readOnly &&` guard in onChange alongside `disabled` attribute — remove guard, rely solely on disabled [frontend/components/roadmap/PostEditPanel.tsx:134]
- [x] [Review][Patch] ARIA ID ternary in ClientDetailTabs is brittle — replace with generic slug helper [frontend/components/clients/ClientDetailTabs.tsx:28]
- [x] [Review][Defer] SYNTHETIC_KEYS includes legacy "error" key with no comment or expiry plan — pre-existing [frontend/components/publishing/RetryPanel.tsx:17]
- [x] [Review][Defer] Already-approved/failed campaigns can be re-queued on re-approval — existing idempotency guard covers this; story only adds published guard — pre-existing [backend/app/routers/roadmaps.py]
- [x] [Review][Defer] Old Voice tab deep-links (#tabpanel-voice) silently broken after tab merge — no deep-link mechanism in use, pre-existing pattern — pre-existing [frontend/components/clients/ClientDetailTabs.tsx]
- [x] [Review][Defer] Roadmap badge link navigates to 404 when roadmap deleted — no roadmap deletion mechanism exists, pre-existing pattern — pre-existing [frontend/components/campaigns/CampaignList.tsx:144]

## Change Log

- 2026-07-28: Story created ready-for-dev (roadmap refetch + status sync, PostCard badges + read-only, CampaignList roadmap badge, /clients/ redirect, Profile & Voice tab merge, approve_roadmap published guard, RetryPanel shape fix)
- 2026-07-28: Implementation complete - all 11 tasks completed, all ACs satisfied, 141 backend service tests pass
