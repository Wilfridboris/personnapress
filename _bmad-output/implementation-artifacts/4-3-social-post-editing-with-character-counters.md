---
baseline_commit: b111298423eb32912bf11d95fe447e91e25ccd4d
---

# Story 4.3: Social Post Editing with Character Counters

Status: done

## Story

As an authenticated user,
I want to edit the generated X and LinkedIn posts with live character counters in the Approval Gate,
So that I can refine the social content to fit platform requirements and match my voice before publishing.

## Acceptance Criteria

1. **Given** the social posts panel in the Approval Gate, **When** it renders for a `pending_approval` Campaign, **Then** two plain textarea editors are shown: one for the X post (pre-filled with `campaigns.x_post`) and one for the LinkedIn post (pre-filled with `campaigns.linkedin_post`); each has a live character counter below it.

2. **Given** the X post textarea, **When** the user types or edits content, **Then** a live counter below reads "N / 280"; when N reaches 95% of 280 (267 characters), the counter text color changes to Danger (#8B0000); the textarea does not enforce a hard character limit in the UI (the user may go over, but the publish endpoint validates ≤280 at submission time).

3. **Given** the LinkedIn post textarea, **When** the user types or edits content, **Then** a live counter below reads "N / 1300"; when N reaches 95% of 1300 (1235 characters), the counter text color changes to Danger; the textarea does not enforce a hard character limit in the UI.

4. **Given** the user edits either social post field and the changes are saved (on approve or explicit save), **When** `PATCH /api/v1/campaigns/{id}` is called with updated social post fields, **Then** `campaigns.x_post` and/or `campaigns.linkedin_post` are updated with the edited text, overwriting the generated content.

5. **Given** the social post editors in the Approval Gate, **When** the user uses the keyboard to navigate, **Then** Tab from the X post textarea moves focus to the LinkedIn post textarea; Tab from LinkedIn moves to the next actionable element (Save button or Approve/Reject footer); this Tab order matches the visual sequence.

6. **Given** a Campaign in a terminal state (`published`, `rejected`, `failed`), **When** the social post panels render, **Then** both social post textareas are disabled (read-only); no character counters are shown; the content is displayed as plain text for reference only.

## Tasks / Subtasks

- [x] Task 1: Create `SocialPostEditors.tsx` Client Component (AC: #1, #2, #3, #5, #6)
  - [x] 1.1 Create `frontend/components/campaigns/SocialPostEditors.tsx` as `"use client"` component
  - [x] 1.2 Props interface:
    ```typescript
    interface SocialPostEditorsProps {
      campaignId: string;
      initialXPost: string | null;
      initialLinkedInPost: string | null;
      readOnly?: boolean;  // true for published/rejected/failed
    }
    ```
  - [x] 1.3 Internal state: `xPost: string` (init from `initialXPost ?? ''`), `linkedinPost: string` (init from `initialLinkedInPost ?? ''`), `isSaving: boolean`, `isDirty: boolean`
  - [x] 1.4 Render two editor sections vertically stacked; each section:
    - Label: `<label htmlFor="x-post" className="block text-xs font-mono uppercase tracking-widest text-graphite mb-2">X (Twitter)</label>`
    - Textarea (see Task 2 for exact specs)
    - Character counter (see Task 3 for exact specs)
  - [x] 1.5 When `readOnly=true`: render `<textarea disabled>` or `<p>` with the content as plain monospace text; hide character counters; hide Save button
  - [x] 1.6 Expose current values to parent (Story 4.4 approve flow) via `forwardRef` + `useImperativeHandle`:
    ```typescript
    export interface SocialPostEditorsHandle {
      getCurrentValues: () => { x_post: string; linkedin_post: string };
    }
    ```

- [x] Task 2: Textarea styling per Paper Style (AC: #1, #5)
  - [x] 2.1 X post textarea: bottom-border-only, transparent bg, font-mono, aria-describedby="x-post-counter"
  - [x] 2.2 LinkedIn post textarea: rows={8}, aria-describedby="linkedin-post-counter"
  - [x] 2.3 Paper Style input spec: `border-b border-ink focus:border-b-2 focus:outline-none bg-transparent rounded-none`
  - [x] 2.4 Tab order: X textarea before LinkedIn in DOM — natural tab sequence ✓

- [x] Task 3: Live character counters (AC: #2, #3)
  - [x] 3.1 X post counter: id="x-post-counter", danger at count >= 267
  - [x] 3.2 LinkedIn counter: id="linkedin-post-counter", danger at count >= 1235
  - [x] 3.3 `aria-live="polite"` on counter spans
  - [x] 3.4 Counter hidden when `readOnly=true`

- [x] Task 4: Save button for social posts (AC: #4)
  - [x] 4.1 "Save social posts" button only shown when `!readOnly && isDirty`
  - [x] 4.2 On click: call `campaignsApi.patch`; show inline spinner
  - [x] 4.3 On success: `setIsDirty(false)`, show success toast; on error: show error toast
  - [x] 4.4 Import `useUIStore` and `campaignsApi, APIError` from correct paths
  - [x] 4.5 Button styling: secondary Paper Style with focus-visible ring
  - [x] 4.6 `campaignsApi.patch` already added by Story 4.2 — reused as-is

- [x] Task 5: Integrate SocialPostEditors into campaign page (AC: #1, #6)
  - [x] 5.1 Replaced static X post and LinkedIn post sections in `page.tsx` with `<SocialPostEditors>`
  - [x] 5.2 Pass `readOnly={!isPending}` — editing only for `pending_approval`
  - [x] 5.3 Server Component passes string props to Client Component ✓
  - [x] 5.4 Section headers owned by component; removed static headers from `page.tsx`

- [x] Task 6: Backend PATCH validation (AC: #4)
  - [x] 6.1 `PATCH /api/v1/campaigns/{id}` already exists from Story 4.2 — reused
  - [x] 6.2 Not duplicated — Story 4.2 endpoint handles `x_post` and `linkedin_post`
  - [x] 6.3 No character limits enforced on backend for PATCH — advisory only per spec

- [x] Task 7: Tests (AC: #1, #2, #3, #5, #6)
  - [x] 7.1 Created `frontend/__tests__/components/SocialPostEditors.test.tsx`
  - [x] 7.2 Test: X counter renders "0 / 280" on init with empty post
  - [x] 7.3 Test: X counter turns danger color when `length >= 267`; returns to graphite when below
  - [x] 7.4 Test: LinkedIn counter turns danger at `>= 1235`
  - [x] 7.5 Test: Save button hidden when `!isDirty`; appears after typing
  - [x] 7.6 Test: Save calls `campaignsApi.patch` with correct payload
  - [x] 7.7 Test: `readOnly=true` → textareas disabled, counters hidden, save button hidden
  - [x] 7.8 Test: `getCurrentValues()` ref returns current textarea values

## Dev Notes

### Input Style — Bottom-Border Only (Critical)

DESIGN.md `components.input`:
```
background: transparent
border: none
border-bottom: 1px solid ink (at rest)
border-bottom-focus: 2px solid ink (on focus)
radius: 0px (rounded-none)
outline: none
```

Do NOT use `border` (box border) on these textareas. The pattern is `border-b border-ink focus:border-b-2 focus:outline-none` with `bg-transparent rounded-none`.

No `ring` or `ring-offset` on these inputs — focus is communicated only by the thicker bottom border. The `focus-visible:ring-*` classes are for buttons only (WCAG keyboard indicators on interactive controls that can't use the border pattern).

### Social Post Content in Monospace

The social post content uses `font-mono` (JetBrains Mono). Per DESIGN.md: "JetBrains Mono is for user-generated raw text only." Social posts are generated output that the user edits — treating them as monospace signals "this is the raw post content, not prose."

This is intentional and matches the typewriter output aesthetic.

### forwardRef Pattern for Approve Integration (Story 4.4)

Story 4.4 will need to save social posts before calling approve. Implement the ref now:

```typescript
import { forwardRef, useImperativeHandle } from 'react'

export const SocialPostEditors = forwardRef<SocialPostEditorsHandle, SocialPostEditorsProps>(
  ({ campaignId, initialXPost, initialLinkedInPost, readOnly = false }, ref) => {
    const [xPost, setXPost] = useState(initialXPost ?? '')
    const [linkedinPost, setLinkedInPost] = useState(initialLinkedInPost ?? '')

    useImperativeHandle(ref, () => ({
      getCurrentValues: () => ({ x_post: xPost, linkedin_post: linkedinPost }),
    }))
    // ...
  }
)
SocialPostEditors.displayName = 'SocialPostEditors'
```

Story 4.4 creates `const socialRef = useRef<SocialPostEditorsHandle>(null)` and calls `socialRef.current?.getCurrentValues()` just before submitting the approve action.

### Avoid Double-Save on Approve

The explicit "Save social posts" button saves immediately. The approve flow in Story 4.4 also saves current values via the ref. This means if the user edits AND clicks Save AND then Approves, the PATCH will be called twice — this is acceptable and idempotent. The second call (from approve) ensures the final state is always saved even if the user forgot to click Save.

### Danger Threshold Calculation

Per spec: "counter color changes to Danger at 95% capacity."
- X: 95% of 280 = 266.0 → `Math.ceil(280 * 0.95) = 267` — so danger at `count >= 267`
- LinkedIn: 95% of 1300 = 1235.0 → exactly 1235 — so danger at `count >= 1235`

These exact numbers should be constants:
```typescript
const X_LIMIT = 280
const LINKEDIN_LIMIT = 1300
const X_DANGER_THRESHOLD = Math.ceil(X_LIMIT * 0.95)       // 267
const LINKEDIN_DANGER_THRESHOLD = Math.ceil(LINKEDIN_LIMIT * 0.95)  // 1235
```

### Campaign PATCH — Reuse from Story 4.2

The `PATCH /api/v1/campaigns/{id}` endpoint and `campaignsApi.patch` frontend method are defined in Story 4.2. This story **depends on Story 4.2 being done first OR implementing the PATCH infrastructure as part of this story** if running in parallel.

If Story 4.2 is complete, this story only adds the frontend component — no new backend changes required.

If Story 4.2 is NOT yet done, implement the PATCH endpoint following the exact spec in Story 4.2 Task 5 to avoid duplication.

### No New Backend Routes

This story only adds `SocialPostEditors.tsx`. The PATCH endpoint is shared with Story 4.2. No new backend files.

### File List for This Story

**New files:**
```
frontend/components/campaigns/SocialPostEditors.tsx
frontend/__tests__/components/SocialPostEditors.test.tsx
```

**Modified files:**
```
frontend/app/(app)/campaigns/[id]/page.tsx   ← replace static social post sections with SocialPostEditors
frontend/lib/api.ts                          ← add campaignsApi.patch if not already added by Story 4.2
```

### References

- Story 4.3 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3]
- FR-19: Inline editing — social posts editable as plain text with live char count: [Source: _bmad-output/planning-artifacts/epics.md#FR-19]
- UX-DR18: Social Post editors spec — plain textarea, live counter, danger at 95%, Tab nav: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR18]
- DESIGN.md components.input — bottom-border-only input style: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md]
- EXPERIENCE.md Component Patterns — Social post editors behavioral rules: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md]
- EXPERIENCE.md Interaction Primitives — Tab in social post editors: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md]
- Architecture: snake_case fields throughout, React Query mutation pattern: [Source: _bmad-output/planning-artifacts/architecture.md]
- Story 4.2 PATCH endpoint spec (shared): [Source: _bmad-output/implementation-artifacts/4-2-blog-post-wysiwyg-editing.md#Task 5]
- Existing campaignsApi: [Source: frontend/lib/api.ts]
- Existing campaign page (integration point): [Source: frontend/app/(app)/campaigns/[id]/page.tsx]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- X_DANGER_THRESHOLD was initially computed as `Math.ceil(280 * 0.95)` = 266 (not 267 as stated in story dev notes). Used literal `267` per AC #2 parenthetical "(267 characters)".
- `tailwind-merge` doesn't de-duplicate custom color utilities (`text-danger` vs `text-graphite`). Replaced `cn(...)` conditional with template literal to ensure only one color class is applied.

### Completion Notes List

- Created `SocialPostEditors.tsx` as a forwardRef Client Component with `useImperativeHandle` exposing `getCurrentValues()` for Story 4.4 integration.
- Textareas use Paper Style bottom-border-only pattern matching DESIGN.md `components.input`.
- X counter: danger at >= 267 chars; LinkedIn counter: danger at >= 1235 chars; both use `aria-live="polite"`.
- Save button only renders when `!readOnly && isDirty`; calls existing `campaignsApi.patch` from Story 4.2.
- Campaign page `page.tsx` updated: static X/LinkedIn post blocks replaced with single `<SocialPostEditors>` component; `readOnly={!isPending}`.
- All 11 tests pass; full suite 47/47 pass.

### File List

- frontend/components/campaigns/SocialPostEditors.tsx (new)
- frontend/__tests__/components/SocialPostEditors.test.tsx (new)
- frontend/app/(app)/campaigns/[id]/page.tsx (modified)

### Review Findings

- [x] [Review][Patch] `test_patch_campaign_raises_400` uses undefined `requester_id` — NameError; fix to `user_id` [backend/tests/test_campaigns_router.py]
- [x] [Review][Patch] `useImperativeHandle` missing `[xPost, linkedinPost]` dependency array — fragile stale-closure risk [frontend/components/campaigns/SocialPostEditors.tsx:36]
- [x] [Review][Patch] Dangling `aria-describedby` on disabled textareas when readOnly=true — counter spans not rendered but IDs still referenced [frontend/components/campaigns/SocialPostEditors.tsx:86,121]
- [x] [Review][Patch] Missing error toast test for save failure — catch branch (APIError + generic fallback) untested [frontend/__tests__/components/SocialPostEditors.test.tsx]
- [x] [Review][Patch] Dynamic `await import()` inside tests after top-level `vi.mock()` — use top-level mock reference via `vi.mocked()` [frontend/__tests__/components/SocialPostEditors.test.tsx]
- [x] [Review][Defer] Backend schema allows x_post/linkedin_post up to 5000 chars — platform limits (280/1300) not enforced at DB layer [backend/app/schemas/campaign.py] — deferred, pre-existing
- [x] [Review][Defer] No timeout/abort on campaignsApi.patch() hung calls — isSaving stuck if network hangs — deferred, pre-existing pattern across app
- [x] [Review][Defer] No test for save button disabled state during isSaving — low-value test coverage gap — deferred, pre-existing
- [x] [Review][Defer] AC5 tab order gap when Save button absent (isDirty=false) — focus skips from LinkedIn to unrelated elements — deferred, low priority UX edge case
