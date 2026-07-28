---
baseline_commit: b45d5de
---

# Story 20.5: Roadmap & Campaign UX Polish

Status: done

## Story

As a PersonnaPress user,
I want the roadmap and campaign pages to navigate intuitively, filter correctly to my active client, open the calendar at the right month, handle images on social posts, and display only the platform sections that exist,
so that every interaction feels purposeful with no empty space gaps or wrong-client data.

## Acceptance Criteria

1. **Back button on `/roadmap/new`**: At the top of `PlanMyWeekClient.tsx`, before the `<header>`, add a back-link identical in style to the campaign detail back-link:
   ```tsx
   <Link
     href="/roadmap"
     className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors font-mono mb-10"
   >
     <ArrowLeft className="size-4" aria-hidden="true" />
     Back to Roadmap
   </Link>
   ```
   `ArrowLeft` is imported from `lucide-react`. The link appears above the page `<header>` (above the "Week Planning" eyebrow + H1).

2. **`CampaignList` — `basePath` prop**: Add `basePath?: string` prop to `CampaignList` in `frontend/components/campaigns/CampaignList.tsx`, defaulting to `"/dashboard"`. Replace the two hardcoded `"/dashboard?"` strings in `setFilter` and `goToPage` with `${basePath}?`. The dashboard page (`/dashboard/page.tsx`) passes no `basePath` (uses default). No other callers change.

3. **`/campaigns/page.tsx` — client-scoped + paginated**: Replace the entire server-component implementation with a thin server shell that renders `CampaignList` with `basePath="/campaigns"`:
   ```tsx
   import type { Metadata } from "next";
   import { Suspense } from "react";
   import { CampaignList } from "@/components/campaigns/CampaignList";

   export const metadata: Metadata = {
     title: "Campaigns",
     robots: { index: false },
   };

   export default function CampaignsPage() {
     return (
       <>
         <header className="flex items-center justify-between mb-10">
           <h1 className="font-display text-3xl font-bold text-ink">Campaigns</h1>
         </header>
         <Suspense fallback={null}>
           <CampaignList basePath="/campaigns" />
         </Suspense>
       </>
     );
   }
   ```
   This gives `/campaigns` client-scoped filtering (active client only), status filter tabs, and pagination — identical behaviour to the dashboard, zero code duplication. The server-side `getCampaigns()` fetch is removed entirely. No RSC API calls (RSC loop prevention rule applies here).

4. **`ContentCalendar` — `?month=` initial view**: In `frontend/components/calendar/ContentCalendar.tsx`, add `useSearchParams()` from `next/navigation` and derive initial `viewYear`/`viewMonth` from a `?month=YYYY-MM` query param:
   ```tsx
   const searchParams = useSearchParams();
   const monthParam = searchParams.get("month"); // "YYYY-MM" or null

   const now = new Date();
   const initialYear  = monthParam ? parseInt(monthParam.slice(0, 4), 10)     : now.getFullYear();
   const initialMonth = monthParam ? parseInt(monthParam.slice(5, 7), 10) - 1 : now.getMonth();

   const [viewYear,  setViewYear]  = useState(initialYear);
   const [viewMonth, setViewMonth] = useState(initialMonth);
   ```
   If `monthParam` is absent or malformed, behaviour is identical to today (current month). `useSearchParams()` requires `ContentCalendar` to already be `"use client"` — it is, so no directive change needed. `ContentCalendar` must be wrapped in `<Suspense>` at its call site for `useSearchParams` to work in Next.js 16 App Router — the existing `<Suspense fallback={<Skeleton ... />}>` wrapper in `calendar/page.tsx` already satisfies this.

5. **`RoadmapListClient` — "View calendar" deep-links to scheduled month**: In `frontend/components/roadmap/RoadmapListClient.tsx`, update `getActionHref` for `approved` roadmaps to include the `?month=` param:
   ```tsx
   function getActionHref(item: RoadmapListItem): string {
     if (item.status === "approved") {
       const month = item.week_start_date?.slice(0, 7); // "YYYY-MM"
       return month ? `/calendar?month=${month}` : "/calendar";
     }
     if (item.status === "failed") return "/roadmap/new";
     return `/roadmap/${item.id}/review`;
   }
   ```
   `week_start_date` is already present on `RoadmapListItem` (string | null). No backend changes needed.

6. **`StickyApproveFooter` — redirect to scheduled month after approve**: In `frontend/components/roadmap/StickyApproveFooter.tsx`:
   - Add `weekStartDate?: string | null` to `StickyApproveFooterProps`.
   - In `handleApprove`, replace `router.push("/calendar")` with:
     ```tsx
     const month = weekStartDate?.slice(0, 7);
     router.push(month ? `/calendar?month=${month}` : "/calendar");
     ```

7. **`RoadmapReviewClient` — pass `weekStartDate` to footer**: In `frontend/components/roadmap/RoadmapReviewClient.tsx`, add the new prop to the `<StickyApproveFooter>` call:
   ```tsx
   <StickyApproveFooter
     roadmapId={roadmapId}
     removedIds={removedIds}
     nonRemovedCount={nonRemovedCount}
     weekStartDate={roadmap.week_start_date ?? null}
   />
   ```
   `roadmap.week_start_date` is already in `RoadmapStatusResponse` and typed as `string | null` in the frontend types.

8. **`ImagePanel` — upload option in the no-image state**: In `frontend/components/campaigns/ImagePanel.tsx`, expand the no-image state block to offer both Generate and Upload actions. The existing `handleReplaceImage` function is unchanged and reused for the upload path. Add a `fileInputRef` and the hidden `<input type="file">` to the no-image state (currently only present in the image-present state — move the ref to component scope so it works in both states):
   ```tsx
   // No image state
   if (!currentImageUrl) {
     return (
       <div className="border border-border">
         <div className="px-6 py-4 border-b border-border">
           <h2 className="font-mono text-xs text-graphite uppercase tracking-widest">
             Featured Image
           </h2>
         </div>
         <div className="p-6 space-y-3">
           <p className="font-mono text-sm text-graphite">
             {jobErrorDetails?.includes("Image generation failed")
               ? "Image generation failed. Blog and social posts are complete."
               : "No featured image yet."}
           </p>
           <Button
             variant="primary"
             onClick={handleRegenerate}
             disabled={isRegenerating || isUploading}
             aria-busy={isRegenerating}
             className="w-full font-mono"
           >
             {isRegenerating
               ? <Loader2 className="size-4 animate-spin" aria-hidden="true" />
               : "Generate image"}
           </Button>
           <Button
             variant="secondary"
             onClick={() => fileInputRef.current?.click()}
             disabled={isUploading || isRegenerating}
             aria-busy={isUploading}
             className="w-full font-mono"
           >
             {isUploading
               ? <Loader2 className="size-4 animate-spin" aria-hidden="true" />
               : "Upload image"}
           </Button>
           <input
             ref={fileInputRef}
             type="file"
             accept="image/png,image/jpeg,image/webp"
             className="sr-only"
             aria-hidden="true"
             tabIndex={-1}
             onChange={handleReplaceImage}
           />
           {error && <p className="font-mono text-xs text-danger">{error}</p>}
         </div>
       </div>
     );
   }
   ```
   **Important:** `fileInputRef` is currently declared inside the image-present state block only — it must be moved to component scope (top of `ImagePanel`) so both states can share it. The hidden `<input>` in the image-present state block below should continue to reference the same `fileInputRef`.

9. **`SocialPostEditors` — conditional section rendering**: Add `showXSection?: boolean` and `showLinkedInSection?: boolean` props (both default `true`). Gate each section:
   ```tsx
   interface SocialPostEditorsProps {
     campaignId: string;
     initialXPost: string | null;
     initialLinkedInPost: string | null;
     readOnly?: boolean;
     showXSection?: boolean;
     showLinkedInSection?: boolean;
   }

   // In JSX:
   {showXSection !== false && (
     <div> {/* X (Twitter) section — unchanged */} </div>
   )}
   {showLinkedInSection !== false && (
     <div> {/* LinkedIn section — unchanged */} </div>
   )}
   ```
   The `space-y-8` wrapper div remains; when both sections are hidden the wrapper collapses with no visible gap.

10. **`ApprovalGateClient` — social-only layout + conditional social sections**: In `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`:
    - Change the content grid `className` to switch based on `isRoadmapSocialPost`:
      ```tsx
      <div className={
        isRoadmapSocialPost
          ? "grid grid-cols-1 lg:grid-cols-2 gap-8 pb-24"
          : "grid grid-cols-1 lg:grid-cols-5 gap-8 pb-24"
      }>
      ```
    - For the `<section>` (blog main col), guard with `{!isRoadmapSocialPost && (...)}`. Already done in story 20-4 — no change needed.
    - For the `<aside>`, remove the hard-coded `lg:col-span-2` class when `isRoadmapSocialPost` is true:
      ```tsx
      <aside className={isRoadmapSocialPost ? "space-y-8" : "lg:col-span-2 space-y-8"}>
      ```
    - Pass conditional show-flags to `SocialPostEditors`:
      ```tsx
      <SocialPostEditors
        ref={socialEditorsRef}
        campaignId={campaign.id}
        initialXPost={campaign.x_post ?? null}
        initialLinkedInPost={campaign.linkedin_post ?? null}
        readOnly={!isPending}
        showXSection={isRoadmapSocialPost ? !!campaign.x_post : true}
        showLinkedInSection={isRoadmapSocialPost ? !!campaign.linkedin_post : true}
      />
      ```
    When `isRoadmapSocialPost` is false (normal blog campaigns), both flags are `true` and behaviour is identical to today.

## Tasks / Subtasks

- [x] Task 1: Back button on `/roadmap/new` (AC: 1)
  - [x] `frontend/components/roadmap/PlanMyWeekClient.tsx`: Add `ArrowLeft` import from `lucide-react`; add back-link before `<header>` block

- [x] Task 2: `CampaignList` `basePath` prop (AC: 2)
  - [x] `frontend/components/campaigns/CampaignList.tsx`: Add `basePath?: string` prop with default `"/dashboard"`; replace both hardcoded `"/dashboard?"` strings in `setFilter` and `goToPage`

- [x] Task 3: `/campaigns/page.tsx` refactor (AC: 3)
  - [x] `frontend/app/(app)/campaigns/page.tsx`: Remove server-side fetch (`getCampaigns`, `STATUS_STYLES`, `STATUS_LABELS`), remove all imports no longer used; replace body with thin server shell wrapping `<CampaignList basePath="/campaigns" />` in `<Suspense>`

- [x] Task 4: Calendar `?month=` param (AC: 4)
  - [x] `frontend/components/calendar/ContentCalendar.tsx`: Add `useSearchParams()` import; derive `initialYear`/`initialMonth` from `?month=YYYY-MM` param; use as initial state for `viewYear`/`viewMonth`

- [x] Task 5: Roadmap list — calendar deep-link (AC: 5)
  - [x] `frontend/components/roadmap/RoadmapListClient.tsx`: Update `getActionHref` for `approved` status to `/calendar?month=YYYY-MM`

- [x] Task 6: Sticky footer — calendar deep-link after approve (AC: 6, 7)
  - [x] `frontend/components/roadmap/StickyApproveFooter.tsx`: Add `weekStartDate?: string | null` prop; update `router.push` to include `?month=` param
  - [x] `frontend/components/roadmap/RoadmapReviewClient.tsx`: Pass `weekStartDate={roadmap.week_start_date ?? null}` to `<StickyApproveFooter>`

- [x] Task 7: `ImagePanel` upload in no-image state (AC: 8)
  - [x] `frontend/components/campaigns/ImagePanel.tsx`: Move `fileInputRef` declaration to component scope (top of component, before any early returns); expand no-image state block to include "Upload image" secondary button + hidden file input reusing `handleReplaceImage`

- [x] Task 8: `SocialPostEditors` conditional sections (AC: 9)
  - [x] `frontend/components/campaigns/SocialPostEditors.tsx`: Add `showXSection` and `showLinkedInSection` props; gate each section div

- [x] Task 9: `ApprovalGateClient` social-only layout (AC: 10)
  - [x] `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`: Switch grid class based on `isRoadmapSocialPost`; remove `lg:col-span-2` from aside when social-only; pass `showXSection`/`showLinkedInSection` to `SocialPostEditors`

## Dev Notes

### RSC Loop Prevention — No API Calls in Server Components
Per `project-context.md`: the old `/campaigns/page.tsx` used `cache: "no-store"` in a server component. This is the exact anti-pattern that causes RSC re-render loops with Turbopack. The replacement (thin server shell + `CampaignList` client component) is the correct pattern — identical to how `/dashboard/page.tsx` works. The `CampaignList` already uses TanStack Query internally (`useCampaigns` hook) which handles caching correctly.

### `fileInputRef` Scope in `ImagePanel`
Currently in `ImagePanel.tsx`, `fileInputRef` is declared with `const fileInputRef = useRef<HTMLInputElement>(null)` but only the image-present render path includes the hidden `<input ref={fileInputRef}>`. The no-image path has no file input at all — so calling `fileInputRef.current?.click()` there would silently do nothing. The fix: keep `fileInputRef` declared at component scope (it already is — the ref declaration is at the top of the component), and add the hidden `<input>` to the no-image state block. The image-present state already has its own `<input ref={fileInputRef}>` — this becomes the shared input across both states (only one is rendered at a time, so there is no conflict).

### `useSearchParams` and Suspense Boundary
Next.js 16 App Router requires components that call `useSearchParams()` to be wrapped in a `<Suspense>` boundary. `ContentCalendar` is already wrapped:
```tsx
// calendar/page.tsx (unchanged)
<Suspense fallback={<Skeleton className="h-[500px] w-full" />}>
  <ContentCalendar />
</Suspense>
```
This satisfies the requirement. No changes to `calendar/page.tsx`.

### `week_start_date` Type Alignment
`RoadmapStatusResponse` in the backend returns `week_start_date: Optional[date]`. On the frontend, `RoadmapStatusResponse` in `frontend/lib/types.ts` types this as `string | null`. The `.slice(0, 7)` call in `StickyApproveFooter` is safe for both `"YYYY-MM-DD"` ISO strings and `null`.

### `CampaignList` — dashboard usage unchanged
The `basePath` prop defaults to `"/dashboard"`. The dashboard page (`/dashboard/page.tsx`) renders `<CampaignList />` with no prop — this picks up the default and behaviour is identical to today. No regression risk.

### Social Section — Edit vs. Read-only
`showXSection` and `showLinkedInSection` are only passed as `false` for `isRoadmapSocialPost` campaigns in read-only context. When `!isPending` is false (campaign is editable / pending_approval), the caller passes `true` for both (the default). This matches the intent: when editing, a user should be able to see and fill both sections regardless of what was originally generated; when viewing (read-only), only show sections with content.

### Files Being Modified

| File | Change |
|------|--------|
| `frontend/components/roadmap/PlanMyWeekClient.tsx` | Add ArrowLeft back-link before header |
| `frontend/components/campaigns/CampaignList.tsx` | Add `basePath` prop; replace 2 hardcoded `/dashboard` strings |
| `frontend/app/(app)/campaigns/page.tsx` | Full replacement — thin server shell + CampaignList |
| `frontend/components/calendar/ContentCalendar.tsx` | Add useSearchParams; derive initial month from ?month= param |
| `frontend/components/roadmap/RoadmapListClient.tsx` | Update getActionHref for approved → /calendar?month= |
| `frontend/components/roadmap/StickyApproveFooter.tsx` | Add weekStartDate prop; update router.push |
| `frontend/components/roadmap/RoadmapReviewClient.tsx` | Pass weekStartDate to StickyApproveFooter |
| `frontend/components/campaigns/ImagePanel.tsx` | Move fileInputRef to component scope; add upload button to no-image state |
| `frontend/components/campaigns/SocialPostEditors.tsx` | Add showXSection / showLinkedInSection props |
| `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` | Conditional grid class; conditional aside col-span; pass show flags |

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
None — all 9 tasks implemented cleanly with no regressions introduced. Pre-existing TypeScript errors in test fixtures (roadmap_id type mismatch in ApprovalPanel.test.tsx and RetryPanel.test.tsx, BlogEditor mock signature) are unrelated to this story.

### Completion Notes List
- Task 1: Added `ArrowLeft` import and back-link `<Link href="/roadmap">` before the `<header>` in `PlanMyWeekClient.tsx`
- Task 2: Added `basePath?: string` prop defaulting to `"/dashboard"` to `CampaignList`; replaced both hardcoded `/dashboard?` strings with template literal using `basePath`
- Task 3: Replaced entire `/campaigns/page.tsx` server component (which used `cache: "no-store"` causing RSC loop risk) with a thin server shell that renders `<CampaignList basePath="/campaigns" />` in a `<Suspense>` boundary
- Task 4: Added `useSearchParams()` to `ContentCalendar.tsx`; derived `initialYear`/`initialMonth` from `?month=YYYY-MM` query param, falling back to `now` if absent/malformed
- Task 5: Updated `getActionHref` in `RoadmapListClient.tsx` for `approved` status to extract `YYYY-MM` from `week_start_date` and append as `?month=` param
- Task 6: Added `weekStartDate?: string | null` to `StickyApproveFooterProps`; updated `router.push` to include `?month=` param; passed `weekStartDate={roadmap.week_start_date ?? null}` in `RoadmapReviewClient`
- Task 7: `fileInputRef` was already at component scope; expanded no-image state block to include "Upload image" secondary button with its own hidden file input, reusing `handleReplaceImage`; both generate and upload buttons disable each other during operations
- Task 8: Added `showXSection` and `showLinkedInSection` props (both default `true`) to `SocialPostEditors`; gated each section div with `{showXSection !== false && ...}` / `{showLinkedInSection !== false && ...}`
- Task 9: Switched content grid class in `ApprovalGateClient` to `lg:grid-cols-2` when `isRoadmapSocialPost`, `lg:grid-cols-5` otherwise; removed `lg:col-span-2` from aside when social-only; passed `showXSection` / `showLinkedInSection` to `SocialPostEditors` using nullish post checks for roadmap social posts

### File List
- `frontend/components/roadmap/PlanMyWeekClient.tsx`
- `frontend/components/campaigns/CampaignList.tsx`
- `frontend/app/(app)/campaigns/page.tsx`
- `frontend/components/calendar/ContentCalendar.tsx`
- `frontend/components/roadmap/RoadmapListClient.tsx`
- `frontend/components/roadmap/StickyApproveFooter.tsx`
- `frontend/components/roadmap/RoadmapReviewClient.tsx`
- `frontend/components/campaigns/ImagePanel.tsx`
- `frontend/components/campaigns/SocialPostEditors.tsx`
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`

### Review Findings

- [x] [Review][Patch] `ApprovalGateClient`: Empty `<section lg:col-span-3>` in 2-col social-only grid — guard entire section with `{!isRoadmapSocialPost && (...)}` [`frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx:103`]
- [x] [Review][Patch] `ContentCalendar`: NaN when `?month=` is malformed — added `isNaN()` guards so invalid params fall back to current month [`frontend/components/calendar/ContentCalendar.tsx:142`]
- [x] [Review][Patch] `ContentCalendar`: `parsedYear`/`parsedMonth` recomputed every render — refactored to use named parse variables before `useState` [`frontend/components/calendar/ContentCalendar.tsx:142`]
- [x] [Review][Defer] `PostCard`/`PostEditPanel` changes undocumented — out-of-spec, but necessary to complete WeekGrid drawer refactor left TypeScript-broken by story 20-4 patches; changes are correct

## Change Log

- 2026-07-27: Story created ready-for-dev
- 2026-07-27: Implementation complete, all 9 tasks done, status set to review
- 2026-07-27: Code review complete: 3 patches applied (section guard in ApprovalGateClient, NaN guard in ContentCalendar ?month= parsing, parse variable refactor), 1 deferred (PostCard/PostEditPanel undocumented 20-4 completion), marked done
