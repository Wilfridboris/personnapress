---
baseline_commit: 2d4faad91b116b65a3423c4c7847f3831cafce43
---

# Story 11.8: Fix Publish Toast and Character Counter

Status: done

## Story

As an authenticated PersonnaPress user,
I want to see a success toast when a campaign publishes, and a character counter that only turns red after I've started typing,
so that I have clear feedback on publish completion and no false warnings on an empty New Campaign form.

## Acceptance Criteria

1. **Given** a campaign has been approved and the user clicks "Publish now", **When** the publish job completes with `status === "complete"`, **Then** a success toast notification ("Published successfully.") appears — in addition to the page refresh that already happens.

2. **Given** the user opens the New Campaign page (`/campaigns/new`), **When** the brain dump textarea is empty (0 characters), **Then** the character counter is displayed in neutral `text-graphite` color (not red/danger).

3. **Given** the user starts typing in the brain dump textarea, **When** the character count is between 1 and 19 (below the 20-character minimum), **Then** the character counter turns red (`text-danger`) to indicate the input is too short.

4. **Given** the user has typed 20 or more characters, **When** the character count meets or exceeds `MIN_CHARS` (20), **Then** the counter returns to `text-graphite`.

## Tasks / Subtasks

### Task 1: Add success toast on publish complete (AC: 1)

- [x] 1.1 In `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`, locate the regular publish polling `useEffect` (around line 374).

  Find the `job.status === "complete"` branch (around line 379) and add a toast call before `router.refresh()`:

  **Current:**
  ```typescript
  if (job.status === "complete") {
    clearInterval(interval);
    setIsPublishing(false);
    setActiveJobId(null);
    setClientHasPlatforms(null);
    router.refresh();
  }
  ```

  **Fixed:**
  ```typescript
  if (job.status === "complete") {
    clearInterval(interval);
    setIsPublishing(false);
    setActiveJobId(null);
    setClientHasPlatforms(null);
    addToast("Published successfully.", "success");
    router.refresh();
  }
  ```

  `addToast` is already available in the component scope via `useUIStore` (line 116). No new imports needed.

### Task 2: Fix character counter condition (AC: 2, 3, 4)

- [x] 2.1 In `frontend/app/(app)/campaigns/new/page.tsx`, locate the character counter `<p>` element (line 239–246).

  **Current condition (line 242):**
  ```typescript
  charCount < MIN_CHARS ? "text-danger" : "text-graphite"
  ```

  **Fixed:**
  ```typescript
  charCount > 0 && charCount < MIN_CHARS ? "text-danger" : "text-graphite"
  ```

  This is a one-word change: add `charCount > 0 &&` before the existing condition. `MIN_CHARS` is defined at the top of the file as `20`.

## Dev Notes

- These are two isolated, single-line frontend changes with zero blast radius on each other or other features.
- `addToast` signature: `addToast(message: string, type: "success" | "error" | "info")` — `useUIStore` in `frontend/lib/stores/useUIStore.ts`.
- The GitHub publish polling (`activeGitHubJobId` effect, around line 405) already handles its own success state differently (shows PR/commit result inline) so does NOT need a toast added there.
- No new imports, no new state, no API changes.

### References

- [Source: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`] Lines 374–402: regular publish polling useEffect
- [Source: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`] Line 116: `addToast` binding
- [Source: `frontend/app/(app)/campaigns/new/page.tsx`] Lines 239–246: character counter `<p>` element
- [Source: `backend/app/schemas/campaign.py`] `CampaignCreate.brain_dump`: `min_length=20` confirms `MIN_CHARS = 20`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1: Added `addToast("Published successfully.", "success")` call before `router.refresh()` in the regular publish polling `useEffect` completion branch in `approval-panel.tsx`. `addToast` was already available via `useUIStore` — no new imports needed.
- Task 2: Changed character counter color condition from `charCount < MIN_CHARS` to `charCount > 0 && charCount < MIN_CHARS` in `campaigns/new/page.tsx` so an empty textarea (0 chars) shows neutral `text-graphite` instead of red.

### File List

- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
- `frontend/app/(app)/campaigns/new/page.tsx`

### Review Findings

- [x] [Review][Defer] Toast string not i18n-ready [frontend/app/(app)/campaigns/[id]/approval-panel.tsx] — deferred, pre-existing
- [x] [Review][Defer] No aria-live region on toast system for screen readers [frontend/app/(app)/campaigns/[id]/approval-panel.tsx] — deferred, pre-existing
- [x] [Review][Defer] No test coverage for polling state machine or counter colour logic — deferred, pre-existing
- [x] [Review][Defer] Unknown job status (not "complete" / "failed") causes polling interval to run indefinitely [frontend/app/(app)/campaigns/[id]/approval-panel.tsx] — deferred, pre-existing

## Change Log

- 2026-07-11: Added success toast on publish complete; fixed character counter to not show red on empty input (Story 11.8)
