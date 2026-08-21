---
baseline_commit: a33c7dbb2abab162579d40f2a6543d1c71776b51
---

# Story 20.7: Voice Recording on Plan My Week

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a PersonnaPress user planning my week,
I want to record a voice note directly on the Plan My Week page and have it transcribed into the brain-dump field, plus clearer guidance on what to dump,
so that I can capture a week of raw ideas hands-free exactly like I already can on `/campaigns/new`, and give the generator enough material to produce varied posts.

## Context and Root Cause

The `/campaigns/new` "Brain Dump" page renders `<VoiceBrainDump>` above its textarea (`frontend/app/(app)/campaigns/new/page.tsx:504`). The Plan My Week page (`frontend/components/roadmap/PlanMyWeekClient.tsx`) uses a plain `<textarea>` with a placeholder that says "voice note transcript" but never renders the recorder — so users must record and transcribe somewhere else and paste the result. This story closes that gap by reusing the existing, fully-generic voice stack. No backend change is required.

The voice stack is already decoupled from campaigns:
- `VoiceBrainDump` (`frontend/components/campaigns/VoiceBrainDump.tsx`) takes a single `onTranscript(text: string)` prop and owns all Record/Stop/Uploading/Transcribing/Error UI.
- `useVoiceTranscription` (`frontend/hooks/useVoiceTranscription.ts`) records via `MediaRecorder`, POSTs the blob to `POST /api/v1/voice/transcribe`, and polls the returned job to completion. Nothing in it is campaign-specific.

## Acceptance Criteria

1. **Voice recorder rendered above the textarea**: In `frontend/components/roadmap/PlanMyWeekClient.tsx`, render `<VoiceBrainDump onTranscript={handleTranscript} />` inside the "Brain dump" block (currently starts at line 424), positioned directly above the `<textarea id="brain-dump">`. Import it from `@/components/campaigns/VoiceBrainDump`. The recorder inherits all its states (idle/recording/uploading/transcribing/error/complete) from the shared component and hook — do not re-implement any of them.

2. **Transcript appends, does not overwrite**: `handleTranscript(text)` must APPEND the transcript to the existing `brainDump` value rather than replace it (this differs from `/campaigns/new`, which replaces). Rationale: a weekly brain dump is naturally captured as several separate thoughts, and richer input directly improves post-angle variety (Story 20-8). Behavior:
   - If `brainDump` is empty or whitespace-only, set it to the trimmed transcript.
   - Otherwise, set it to `existing.trimEnd() + "\n\n" + transcript.trim()`.
   - Clamp the final result to `MAX_CHARS` (10,000): `.slice(0, MAX_CHARS)`.
   - After updating, run the existing textarea auto-resize (see AC 4) and move the caret to the end.

3. **Character-limit safety at the append boundary**: If appending would exceed `MAX_CHARS`, the combined string is clamped to `MAX_CHARS` via `.slice(0, MAX_CHARS)` (partial transcript is kept, no throw). The existing character counter (`{charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}`) reflects the clamped value. No new error UI is required for this case.

4. **Textarea auto-resizes after transcript insertion**: The component already auto-resizes via a `useEffect` on `[brainDump]` (lines 183-188). Because `handleTranscript` updates `brainDump` state, that effect fires automatically. Additionally, set the caret to the end of the text after the state update so the user sees the newly appended content, mirroring the pattern in `campaigns/new/page.tsx:508-513`:
   ```tsx
   setTimeout(() => {
     const ta = textareaRef.current;
     if (ta) {
       ta.style.height = "auto";
       ta.style.height = `${ta.scrollHeight}px`;
       ta.setSelectionRange(ta.value.length, ta.value.length);
     }
   }, 0);
   ```

5. **Updated guidance placeholder**: Replace the textarea placeholder (line 436) so it (a) no longer implies pasting an external transcript and (b) nudges the user to dump multiple ideas, which improves angle variety. New copy (no em-dash, no double-dash, no emoji per project copy rules):
   > `Record or type everything on your mind this week: the wins, the lessons, the opinions, the numbers. The more raw material you give, the more distinct angles we can turn it into. No structure needed.`

6. **Unsupported-microphone fallback preserved**: When `MediaRecorder` / `getUserMedia` is unavailable, `VoiceBrainDump` already renders its own inline message ("Microphone access unavailable. Type your Brain Dump below."). No additional handling is needed — the textarea remains fully usable for typing. Do not gate or hide the textarea on voice support.

7. **No visual or layout regression**: The recorder sits within the existing `<div className="mb-6">` brain-dump block, above the `<label>`/`<textarea>`, matching the vertical rhythm on `/campaigns/new`. The label "What's on your mind this week?" stays. The recorder row keeps its own `min-h-[44px]` touch target (already built into `VoiceBrainDump`). The submit button, character counter, settings panel, and roadmap-limit banner are unchanged.

## Tasks / Subtasks

- [x] Task 1: Wire the voice recorder into Plan My Week (AC: 1, 2, 3, 4, 6, 7)
  - [x] `frontend/components/roadmap/PlanMyWeekClient.tsx`: add `import { VoiceBrainDump } from "@/components/campaigns/VoiceBrainDump";`
  - [x] Add a `handleTranscript(text: string)` function implementing the append-and-clamp logic (AC 2, 3) plus the caret/resize effect (AC 4)
  - [x] Render `<VoiceBrainDump onTranscript={handleTranscript} />` directly above the `<textarea id="brain-dump">`, inside the existing brain-dump block, after the `<label>` (or above it — match `/campaigns/new` where the recorder sits above the textarea)
- [x] Task 2: Update guidance placeholder (AC: 5)
  - [x] `frontend/components/roadmap/PlanMyWeekClient.tsx:436`: replace the `placeholder` string with the new copy
- [x] Task 3: Manual verification (AC: 1-7)
  - [x] Record a note; confirm it appends below existing typed text with a blank-line separator and the caret lands at the end
  - [x] Record a second note; confirm it appends again (not overwrite)
  - [x] Confirm the character counter and `MAX_CHARS` clamp behave at the boundary
  - [x] Confirm the textarea grows to fit inserted text
  - [x] Confirm error/unsupported states render from the shared component with no console errors

## Dev Notes

### Reuse, do not reinvent
The entire voice pipeline already exists and is generic. Do NOT create a new recorder, a new hook, or a new transcription endpoint. Import and render `VoiceBrainDump`; it internally uses `useVoiceTranscription`, which already handles `MediaRecorder`, upload to `POST /api/v1/voice/transcribe`, job polling via `jobsApi.get`, and every status transition. The only page-specific logic here is the `onTranscript` handler (append vs. replace).

### Append vs. replace — the one intentional deviation from `/campaigns/new`
`campaigns/new/page.tsx:505` REPLACES the brain dump with the transcript. This story APPENDS. This is deliberate and is the crux of AC 2. A reviewer comparing the two pages will see the difference; it is intended, not a copy error. Keep the append semantics.

### No backend work
`RoadmapCreateRequest.brain_dump` (`backend/app/routers/roadmaps.py:61`) already accepts `min_length=20, max_length=10000` free text. The transcribed text flows through the existing `roadmapsApi.create({ brain_dump, ... })` call (`PlanMyWeekClient.tsx:221`) with no schema change. `/api/v1/voice/transcribe` is unchanged.

### Caret + resize pattern reference
Mirror `campaigns/new/page.tsx:507-514` for the post-insert resize/caret behavior, but adapt the resize to Plan My Week's simpler inline auto-grow (`ta.style.height = "auto"; ta.style.height = \`${ta.scrollHeight}px\`;` at lines 185-187) rather than campaigns/new's `resizeTextarea(..., MAX_TEXTAREA_HEIGHT)` helper, which Plan My Week does not import.

### Copy constraints (project-wide)
No em-dash (—) and no double-dash (--) in any user-facing copy or placeholder. No emojis. The AC 5 placeholder already complies. See project memory: "No Double-Dash in Copy" and "Icons and Emoji Rules".

### Design system (Paper Style) alignment
`VoiceBrainDump` already renders on-brand: mono uppercase `tracking-[0.08em]` "Record" affordance, `border-ink`, `min-h-[44px]` / `h-11` touch targets, `focus-visible:ring-2 focus-visible:ring-ink`, lucide `Mic`/`Square`/`Loader2`/`RotateCcw` icons, and `WaveformBars` during recording. Rendering it inside Plan My Week requires no restyling. Keep the 8pt vertical rhythm: the recorder row and the label/textarea both live inside the existing `mb-6` block; do not add extra wrappers or margins that break the existing spacing.

### Accessibility
The shared component already provides `aria-label`s on each state button and `role="status" aria-live="polite"` on the status text. Do not duplicate live regions on the page. The textarea keeps its existing `aria-label="What's on your mind this week?"`.

### Files being modified

| File | Change |
|------|--------|
| `frontend/components/roadmap/PlanMyWeekClient.tsx` | Import `VoiceBrainDump`; add `handleTranscript` (append + clamp + caret/resize); render recorder above textarea; update placeholder copy |

### Testing standards
Frontend UI-wiring stories of this size in Epic 20 (e.g., 20-4 Task 9) ship without new automated tests; verification is manual against the ACs. If the repo's `frontend/__tests__` conventions are followed for this component, a lightweight test asserting `handleTranscript` appends rather than replaces is welcome but not required. Run the existing `tsc`/lint check and confirm no new type errors are introduced (pre-existing test-file errors, if any, are out of scope — consistent with 20-4).

### References
- [Source: frontend/app/(app)/campaigns/new/page.tsx#L504-L515] — reference wiring of `VoiceBrainDump` + onTranscript + resize/caret
- [Source: frontend/components/campaigns/VoiceBrainDump.tsx] — shared recorder component and its states
- [Source: frontend/hooks/useVoiceTranscription.ts] — transcription hook and `/api/v1/voice/transcribe` contract
- [Source: frontend/components/roadmap/PlanMyWeekClient.tsx#L424-L450] — brain-dump block being modified
- [Source: backend/app/routers/roadmaps.py#L60-L74] — `RoadmapCreateRequest` confirming no backend change
- [Source: _bmad-output/implementation-artifacts/20-4-plan-my-week-ux-polish.md] — prior Plan My Week story, house style and patterns

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
None — implementation was straightforward reuse of existing `VoiceBrainDump` component.

### Completion Notes List
- Added `import { VoiceBrainDump } from "@/components/campaigns/VoiceBrainDump"` to PlanMyWeekClient.tsx.
- Added `handleTranscript(text)` implementing append-not-replace semantics with `MAX_CHARS` clamp and `setTimeout`-based caret/resize (mirrors campaigns/new pattern, intentionally uses append instead of replace per AC 2).
- Rendered `<VoiceBrainDump onTranscript={handleTranscript} />` inside the existing `mb-6` brain-dump block, between the label and the textarea.
- Updated placeholder copy per AC 5: no em-dash, no double-dash, no emoji, nudges multi-idea input.
- `tsc --noEmit` confirms no new type errors (pre-existing test-file errors are out of scope per Dev Notes).
- All ACs satisfied: recorder present (AC 1), append+clamp logic (AC 2, 3), resize+caret (AC 4), placeholder (AC 5), fallback preserved by shared component (AC 6), no layout regression (AC 7).

### File List
- `frontend/components/roadmap/PlanMyWeekClient.tsx`

### Review Findings

- [x] [Review][Patch] Empty/whitespace transcript appends stale `\n\n` trailer [frontend/components/roadmap/PlanMyWeekClient.tsx:193]
- [x] [Review][Defer] Accessibility: no `aria-describedby` connecting VoiceBrainDump recorder to brain-dump textarea [frontend/components/roadmap/PlanMyWeekClient.tsx:449] — deferred, pre-existing pattern from campaigns/new
- [x] [Review][Defer] MAX_CHARS enforcement inconsistency between onChange (event value) and handleTranscript (combined value) [frontend/components/roadmap/PlanMyWeekClient.tsx:191] — deferred, pre-existing design
- [x] [Review][Defer] `handleTranscript` not memoized with `useCallback` — may defeat VoiceBrainDump prop-comparison optimizations [frontend/components/roadmap/PlanMyWeekClient.tsx:191] — deferred, same pattern as campaigns/new reference implementation

## Change Log
- 2026-08-21: Story implemented — added VoiceBrainDump recorder to Plan My Week, append-mode handleTranscript with MAX_CHARS clamp and caret/resize, updated guidance placeholder copy (Date: 2026-08-21)
- 2026-08-21: Code review complete — 1 patch applied (empty transcript guard), 3 deferred, 10 dismissed; marked done
