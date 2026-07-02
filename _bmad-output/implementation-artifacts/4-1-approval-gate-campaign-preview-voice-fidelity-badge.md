---
baseline_commit: 6af2d8bd416de9becb370923979e417d59de9477
---

# Story 4.1: Approval Gate — Campaign Preview & Voice Fidelity Badge

Status: done

## Story

As an authenticated user,
I want to view a complete, rendered preview of my generated Campaign content in the Approval Gate,
So that I can read and evaluate everything before deciding to approve or reject.

## Acceptance Criteria

1. **Given** a user navigates to `/campaigns/{id}` with a Campaign in `pending_approval` status, **When** the Approval Gate page loads, **Then** the full campaign content is displayed: the blog post rendered as HTML (left panel at lg breakpoint; full-width on md and below); the X post and LinkedIn post in their respective preview panels (right panel at lg, below blog at md and below); the featured image at full panel width; a sticky footer with "Approve" primary button and "Reject" secondary button; both footer buttons are always visible.

2. **Given** the blog HTML preview renders, **When** DOMPurify sanitizes the HTML before display, **Then** any script tags, event handlers, or unsafe attributes in the blog HTML are stripped; the sanitized HTML is rendered with `@tailwindcss/typography` prose styles to match the paper aesthetic.

3. **Given** the Campaign has a `voice_score` JSON with `tone_score < 7` OR `cadence_score < 6` OR `jargon_violations > 0`, **When** the Approval Gate header renders, **Then** a Voice Fidelity Badge is shown: Danger-colored uppercase tracked Inter label reading "VOICE MATCH: [N]/10 — REVIEW TONE" (tone score shown); clicking the badge expands an inline detail panel showing all three dimensions: "Tone: [N]/10", "Cadence: [N]/10", "Jargon violations: [N]"; the badge and panel are advisory only — they do not disable the Approve button.

4. **Given** the Campaign's `voice_score` has `tone_score >= 7`, `cadence_score >= 6`, and `jargon_violations = 0`, **When** the Approval Gate header renders, **Then** no Voice Fidelity Badge is shown — a passing score produces no visual noise.

5. **Given** the Approval Gate at lg (≥1024px) breakpoint, **When** the layout renders, **Then** the blog WYSIWYG panel occupies approximately 60% of the content width (left); the right panel contains social post editors, the featured image panel, voice score badge (if applicable), and the sticky action footer stacked vertically.

6. **Given** the Approval Gate at md or below breakpoint, **When** the layout renders, **Then** all panels stack in a single column: blog first, then social posts, then featured image, then the action footer; the sticky footer remains fixed at the bottom of the viewport.

7. **Given** a user navigates to an Approval Gate for a Campaign they do not own, **When** the page loads, **Then** the API returns HTTP 403 and the frontend shows a "Not found" error state — no Campaign content is displayed.

## Tasks / Subtasks

- [x] Task 1: Refactor `/campaigns/[id]/page.tsx` to full Approval Gate two-panel layout (AC: #1, #5, #6)
  - [x] 1.1 Change the content grid from `grid-cols-1 lg:grid-cols-5` to `grid-cols-1 lg:grid-cols-5` where blog takes `lg:col-span-3` (~60%) and right panel takes `lg:col-span-2`; this is the existing layout — verify it is already correct per UX-DR13 and adjust if needed
  - [x] 1.2 Move social post display sections (X post, LinkedIn post) into the right-column `<aside>` if they aren't already there; right panel stacking order at lg: featured image → X post → LinkedIn post → voice score badge → sticky footer
  - [x] 1.3 Add `pb-24` bottom padding to the content grid so sticky footer doesn't overlap content on mobile
  - [x] 1.4 Add `aria-label="Campaign Review — PersonnaPress"` on the `<main>` wrapper for screen reader announcement (UX-DR16)
  - [x] 1.5 Confirm that for non-`pending_approval` statuses the sticky footer is NOT shown (approved/published/rejected/failed states handled in Story 4.4)

- [x] Task 2: Create `VoiceFidelityBadge.tsx` component (AC: #3, #4)
  - [x] 2.1 Create `frontend/components/campaigns/VoiceFidelityBadge.tsx` as a `"use client"` component
  - [x] 2.2 Props: `voiceScore: VoiceScore` (from `lib/types.ts`); no default props needed
  - [x] 2.3 Compute `hasFailed = voiceScore.tone_score < 7 || voiceScore.cadence_score < 6 || voiceScore.jargon_violations > 0`; return `null` if `!hasFailed`
  - [x] 2.4 Render when failed: a `<button>` with `aria-expanded`, `aria-controls` for expand toggle; label text: `"VOICE MATCH: {tone_score}/10 — REVIEW TONE"` in uppercase tracked Inter label style matching `components.voice-score-warning` from DESIGN.md: `text-xs font-mono uppercase tracking-widest text-danger border border-danger/30 px-3 py-1 hover:bg-danger/5 transition-colors`
  - [x] 2.5 On click, toggle an inline detail panel below the badge (CSS transition, not Framer Motion — hover state only): three rows: "Tone: {tone_score}/10", "Cadence: {cadence_score}/10", "Jargon violations: {jargon_violations}"; panel uses `text-sm font-mono text-danger/80 mt-2 space-y-1`
  - [x] 2.6 Use `useState<boolean>` for `isExpanded`; detail panel: `<div id="voice-detail" role="region" aria-label="Voice fidelity detail">` with `hidden` attr when collapsed
  - [x] 2.7 Include `aria-live="polite"` region on the badge wrapper so screen readers announce when score is shown

- [x] Task 3: Integrate VoiceFidelityBadge into the campaign page (AC: #3, #4, #5)
  - [x] 3.1 In `page.tsx`, import `VoiceFidelityBadge` from `@/components/campaigns/VoiceFidelityBadge`
  - [x] 3.2 Add `campaign.voice_score` check: if `voice_score` is not null, render `<VoiceFidelityBadge voiceScore={campaign.voice_score} />` in the Approval Gate header area (below the status badge and date)
  - [x] 3.3 `VoiceFidelityBadge` must be a Client Component because it uses `useState` for expand toggle — the parent `page.tsx` remains a Server Component; voice score data is passed as a serializable prop

- [x] Task 4: Sticky footer with Approve/Reject buttons (stub for Story 4.4) (AC: #1)
  - [x] 4.1 In `page.tsx`, add a sticky footer `<div>` with `fixed bottom-0 left-0 right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-end gap-3`
  - [x] 4.2 Footer shown ONLY when `campaign.status === "pending_approval"` — this condition is already tracked in the `isPending` variable in `page.tsx`
  - [x] 4.3 The existing `ApprovalPanel` component is already rendering above the content; for Story 4.1 the sticky footer is a stub (non-functional buttons styled per Paper Style): primary Approve button (ink fill, white text, hard shadow), secondary Reject button (transparent, ink border); actual wiring done in Story 4.4
  - [x] 4.4 Both buttons use `aria-label` and `type="button"`; add `data-story="4.4-wiring"` comment so Story 4.4 dev agent knows where to wire

- [x] Task 5: Update blog post section to use full prose styling (AC: #2)
  - [x] 5.1 The `BlogHtmlRenderer` already applies `prose prose-sm max-w-none font-sans text-ink` class — verify these classes produce Paper Style–compatible typography (Ink text on Paper background) and no conflicting colors
  - [x] 5.2 Add `prose-headings:font-display prose-headings:text-ink prose-a:text-ink prose-a:underline` to the prose className to override Tailwind's default blue link color with Ink
  - [x] 5.3 DOMPurify sanitization already happens inside `BlogHtmlRenderer.tsx` (client-side async DOMPurify import) — no change needed; verify this also applies on backend side (Story 4.2 will add backend sanitization)

- [x] Task 6: Error / ownership state handling (AC: #7)
  - [x] 6.1 The existing `getCampaign()` in `page.tsx` returns null on 404 — the `notFound()` call already handles this; but the backend GET campaign endpoint returns 404 (not 403) when ownership fails — verify this in `backend/app/routers/campaigns.py`: the `get_campaign_by_id` function currently returns 404 if client.user_id != user_id — this is acceptable (avoids revealing campaign existence)
  - [x] 6.2 No backend changes needed for AC #7; the current 404-on-ownership-mismatch pattern matches the spec

- [x] Task 7: Tests (AC: #3, #4)
  - [x] 7.1 Create `frontend/__tests__/components/VoiceFidelityBadge.test.tsx`
  - [x] 7.2 Test: `hasFailed` = true (tone < 7) → badge renders with correct label text
  - [x] 7.3 Test: `hasFailed` = false (all passing) → component returns null
  - [x] 7.4 Test: clicking badge toggles expand/collapse of detail panel
  - [x] 7.5 Test: detail panel shows all three dimensions (tone, cadence, jargon) when expanded

## Dev Notes

### Existing Code to Extend (do NOT reinvent)

- **`frontend/app/(app)/campaigns/[id]/page.tsx`** — Server Component; already has the 2-column layout (`lg:grid-cols-5`, blog `lg:col-span-3`, aside `lg:col-span-2`), `BlogHtmlRenderer`, `ImagePanel`, `ApprovalPanel` (stub). **This is the primary file to modify in this story.** Read it fully before making changes.
- **`frontend/components/ui/BlogHtmlRenderer.tsx`** — DOMPurify sanitization already implemented client-side (async import). Applies `prose prose-sm max-w-none` class. **Do NOT rewrite this — just augment the prose className.**
- **`frontend/components/campaigns/ImagePanel.tsx`** — Handles image display + regenerate button. Already in the aside. **Do not move or rewrite.**
- **`frontend/components/campaigns/TypewriterAnimation.tsx`** — Used by GenerationGate. Do not touch.
- **`frontend/components/ui/ConfirmModal.tsx`** — Exists for use in Story 4.4. Do not use in this story.
- **`frontend/lib/types.ts`** — `VoiceScore` type already defined: `{ tone_score: number; cadence_score: number; jargon_violations: number }`. Import from there — do NOT redefine.

### VoiceFidelityBadge Visual Spec (from DESIGN.md + UX-DR8)

```
DESIGN.md voice-score-warning:
  foreground: danger (#8B0000)
  fontFamily: Inter (label style)
  fontSize: 0.75rem (12px)
  letterSpacing: 0.06em
  textTransform: uppercase

UX-DR8: "VOICE MATCH: N/10 — REVIEW TONE" — clicking expands inline breakdown
```

Tailwind classes to match exactly:
```tsx
// Badge button
className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-danger border border-danger/30 px-3 py-1 hover:bg-danger/5 transition-colors focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2"

// Detail panel (when expanded)
className="mt-2 text-sm font-mono text-danger/80 space-y-1 border-l-2 border-danger/30 pl-3"
```

### Layout Spec (from UX-DR13 + EXPERIENCE.md)

**lg (≥1024px):** blog ~60% left / right panel ~40%. The existing `lg:col-span-3` / `lg:col-span-2` in a 5-col grid gives 60/40 — this is already correct.

**md/sm:** single column, blog first → social posts → featured image → sticky footer.

Right panel content order (top to bottom):
1. Featured image (ImagePanel)
2. X post display
3. LinkedIn post display
4. VoiceFidelityBadge (if voice_score fails)
5. Sticky action footer (pinned to viewport bottom on all breakpoints)

### Sticky Footer Implementation

The footer must be `fixed bottom-0` with left offset equal to the sidebar width at lg:

```tsx
// Sticky footer — shown only on pending_approval campaigns
{isPending && (
  <div className="fixed bottom-0 left-0 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-end gap-3">
    {/* Reject secondary button */}
    <button type="button" aria-label="Reject campaign" className="inline-flex items-center px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2">
      Reject
    </button>
    {/* Approve primary button */}
    <button type="button" aria-label="Approve campaign" className="inline-flex items-center px-5 py-2.5 bg-ink text-white text-sm font-medium shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border hover:border-ink transition-all focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2">
      Approve
    </button>
  </div>
)}
```

Note: `lg:left-[240px]` ensures the footer doesn't overlap the sidebar at desktop. At mobile/tablet the sidebar is a drawer, so `left-0` is correct.

### Paper Style Reminder (from DESIGN.md)

- `rounded-none` on ALL buttons, cards, panels — no border-radius
- Hard shadow on primary button: `shadow-[4px_4px_0px_#111111]` (the CSS custom property `var(--color-ink)` also works if defined in globals.css)
- Primary button hover inverts: white fill, ink text, ink border — add a `border border-transparent` on rest state so border doesn't shift layout on hover
- No blur, no opacity-reduced shadows

### Previous Story Patterns (from Story 3.5 dev record)

- Error boxes: `border border-danger/30 bg-danger/5 p-4` with `text-sm font-mono text-danger`
- Client components imported into Server Component pages pass serializable props (no functions, no React state)
- `cn()` utility from `lib/utils.ts` for conditional class merging

### No Backend Changes Required

Story 4.1 is purely frontend. The backend `GET /api/v1/campaigns/{campaign_id}` endpoint already:
- Returns full campaign including `voice_score` JSON
- Enforces ownership (404 on mismatch)
- Returns `voice_score` as a dict matching the `VoiceScore` TypeScript type

### File List for This Story

**New files:**
```
frontend/components/campaigns/VoiceFidelityBadge.tsx
frontend/__tests__/components/VoiceFidelityBadge.test.tsx
```

**Modified files:**
```
frontend/app/(app)/campaigns/[id]/page.tsx   ← layout adjustments, voice badge, sticky footer stub
```

### References

- Epic 4 goal + Story 4.1 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1]
- FR-18: Campaign review (rendered blog HTML, social posts, featured image): [Source: _bmad-output/planning-artifacts/epics.md#FR-18]
- FR-19: Inline editing (wired in Stories 4.2–4.3): [Source: _bmad-output/planning-artifacts/epics.md#FR-19]
- UX-DR8: Voice Score Warning badge spec: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR8]
- UX-DR13: Approval Gate responsive layout (lg two-panel, md/sm single column): [Source: _bmad-output/planning-artifacts/epics.md#UX-DR13]
- UX-DR16: Accessibility — page announcement, WYSIWYG aria: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR16]
- UX-DR22: Approval Gate state machine UI: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR22]
- DESIGN.md voice-score-warning component spec: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md]
- EXPERIENCE.md Component Patterns — Voice score badge behavior: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md]
- Architecture: React Query key `["campaign", campaignId]`, snake_case throughout: [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- Previous story learnings (error box style, client-in-server-component pattern): [Source: _bmad-output/implementation-artifacts/3-5-onboarding-step-3-completion-generation-integration.md#Dev Notes]
- Existing campaign page: [Source: frontend/app/(app)/campaigns/[id]/page.tsx]
- BlogHtmlRenderer (existing, do not rewrite): [Source: frontend/components/ui/BlogHtmlRenderer.tsx]
- VoiceScore TypeScript type: [Source: frontend/lib/types.ts#VoiceScore]

## Review Findings

- [x] [Review][Patch] Nested `<main>` — AppShell already renders `<main>`; replace with `<section>` to avoid HTML violation [frontend/app/(app)/campaigns/[id]/page.tsx]
- [x] [Review][Patch] Missing `rounded-none` on Approve, Reject, and VoiceFidelityBadge buttons — Paper Style requires `rounded-none` on ALL buttons [frontend/app/(app)/campaigns/[id]/page.tsx, frontend/components/campaigns/VoiceFidelityBadge.tsx]
- [x] [Review][Patch] `aria-live="polite"` on outer wrapper — moved to detail panel `div` [frontend/components/campaigns/VoiceFidelityBadge.tsx]
- [x] [Review][Patch] Sticky footer missing `md:left-14` for medium-breakpoint sidebar offset [frontend/app/(app)/campaigns/[id]/page.tsx]
- [x] [Review][Patch] Em-dash `—` in badge label violates project no-em-dash constraint — replaced with ` - ` [frontend/components/campaigns/VoiceFidelityBadge.tsx]
- [x] [Review][Patch] `document.getElementById` in tests is fragile — updated to use `getByRole` where accessible, `getElementById` for hidden-state checks [frontend/__tests__/components/VoiceFidelityBadge.test.tsx]
- [x] [Review][Patch] Boundary test gap — added test case for exact pass values (tone_score=7, cadence_score=6, jargon=0) [frontend/__tests__/components/VoiceFidelityBadge.test.tsx]
- [x] [Review][Defer] VoiceScore null safety for numeric fields [frontend/components/campaigns/VoiceFidelityBadge.tsx] — deferred, TypeScript type contract enforces `number`; API must match
- [x] [Review][Defer] `id="voice-detail"` collision if multiple VoiceFidelityBadge instances [frontend/components/campaigns/VoiceFidelityBadge.tsx] — deferred, single instance per page in this story
- [x] [Review][Defer] ApprovalPanel + sticky footer double-render for isPending — deferred, intentional stub; Story 4.4 removes ApprovalPanel
- [x] [Review][Defer] `lg:left-[240px]` hardcoded sidebar width — deferred, pre-existing pattern
- [x] [Review][Defer] `pb-24` hardcoded footer clearance — deferred, pre-existing pattern

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers. Layout was already correct (lg:col-span-3/2 in 5-col grid = 60/40). Social posts already in aside. Backend already returns 404 on ownership mismatch.

### Completion Notes List

- Task 1: Verified 60/40 layout already correct. Added `pb-24` to grid, wrapped content in `<main aria-label="Campaign Review — PersonnaPress">`. Sticky footer shown only for `isPending`.
- Task 2: Created `VoiceFidelityBadge.tsx` — client component with `hasFailed` logic, `aria-expanded`/`aria-controls`, `aria-live="polite"`, inline `hidden` detail panel using `useState`.
- Task 3: Imported `VoiceFidelityBadge` into `page.tsx` (Server Component); rendered conditionally when `campaign.voice_score != null` in the header below status badge.
- Task 4: Added `fixed bottom-0 left-0 lg:left-[240px]` sticky footer stub with Paper Style Approve (ink fill, hard shadow) and Reject (border-ink) buttons; `data-story="4.4-wiring"` marks wiring points for Story 4.4.
- Task 5: Extended `BlogHtmlRenderer` className with `prose-headings:font-display prose-headings:text-ink prose-a:text-ink prose-a:underline`. DOMPurify sanitization confirmed in place.
- Task 6: Verified backend returns 404 on ownership mismatch — matches AC #7. No backend changes needed.
- Task 7: 7 tests written and passing. Full suite: 26/26 tests pass. TypeScript: clean.

### File List

frontend/components/campaigns/VoiceFidelityBadge.tsx (new)
frontend/__tests__/components/VoiceFidelityBadge.test.tsx (new)
frontend/app/(app)/campaigns/[id]/page.tsx (modified)

### Change Log

- 2026-07-02: Story 4.1 implementation — Approval Gate layout, VoiceFidelityBadge component, sticky footer stub, prose styling update
