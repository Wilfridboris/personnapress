---
baseline_commit: 17f3e5e
depends_on: 9-2-backend-transcription-api
---

# Story 9.3: Frontend Voice Capture Component

Status: done

## Story

As an authenticated user,
I want a microphone button on the Brain Dump input that lets me record my idea, receive the transcript in the textarea, and review it before generating a campaign,
So that I can capture a Brain Dump by speaking in situations where typing is impractical or slower.

## Context & Motivation

This is Story 9.2 from the epics file (numbered 9.3 in sprint status because `9-1-production-launch-infrastructure` is already done). It implements the browser-side half of the Voice-to-text Brain Dump feature: a `VoiceBrainDump` component containing a mic button, recording state indicator, and transcript handoff logic.

**Depends on Story 9.2 (backend):** The `result` field must exist on `Job` model and `JobResponse` schema before this story's polling logic can work. Verify `GET /api/v1/jobs/{job_id}` returns `result.transcript` before testing end-to-end.

**Architecture paradigm:** Stateless I/O Proxy. The voice component is a pure adapter — audio in, text out. It rejoins the existing Brain Dump flow at the textarea. No new campaign fields, no new API routes beyond what Story 9.2 ships.

**Zero new npm packages.** `MediaRecorder` is a browser built-in. Job polling uses the existing `useJobStatus` hook infrastructure. Icons are already in `lucide-react`.

---

## Acceptance Criteria

### AC 1 — `@keyframes voice-pulse` in `globals.css`

**Given** `frontend/app/globals.css` is reviewed,
**When** the CSS is opened,
**Then** a `@keyframes voice-pulse` animation is defined:
```css
@keyframes voice-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.15; }
}
```
This keyframe is used by the recording state pulsing dot via `animate-[voice-pulse_1.4s_ease-in-out_infinite]`.

### AC 2 — `Job` type updated to include `result`

**Given** `frontend/lib/types.ts` is reviewed,
**When** the `Job` type/interface is found,
**Then** it includes a `result?: Record<string, unknown> | null` field (or `result?: { transcript?: string } | null`).

**Why:** Story 9.2 adds `result JSONB` to the backend `JobResponse`. Without this field in the frontend `Job` type, TypeScript will error when the polling hook tries to read `job.result.transcript`.

### AC 3 — `useVoiceTranscription` hook

**Given** `frontend/hooks/useVoiceTranscription.ts` is reviewed,
**When** the hook is called with `{ onTranscript: (text: string) => void }`,
**Then** it exposes:
```ts
{
  status: 'idle' | 'recording' | 'uploading' | 'transcribing' | 'complete' | 'error',
  error: string | null,
  startRecording: () => Promise<void>,
  stopRecording: () => void,
}
```

**`startRecording` behavior:**
- Calls `navigator.mediaDevices.getUserMedia({ audio: true })`
- Creates a `MediaRecorder` preferring `audio/webm;codecs=opus` (Chrome/Firefox/Edge); falls back to `audio/mp4` (Safari, which does not support webm)
- Starts recording with 100ms timeslice (chunks collected in `ondataavailable`)
- Sets `status = 'recording'`
- On permission denial or `getUserMedia` error: sets `error` string and `status = 'error'` — does NOT throw; handles gracefully

**`stopRecording` behavior:**
- Stops the MediaRecorder
- Assembles the Blob from collected chunks
- Calls `stream.getTracks().forEach(t => t.stop())` to release the microphone
- Sets `status = 'uploading'`
- POSTs the blob as multipart to `/api/v1/voice/transcribe` with `credentials: 'include'` and the blob's MIME type as `Content-Type` (use `fetch` with `FormData` — do NOT use `jobsApi` which is for GET /jobs only)
- On 202 response: saves the returned `job_id`, sets `status = 'transcribing'`
- On HTTP error or network error: parses the error body, sets `error` to a human-readable string, sets `status = 'error'`

**Polling behavior:**
- Uses `useQuery` from `@tanstack/react-query` (same dependency as `useJobStatus`) with `refetchInterval: 2000` while job status is `'pending'` or `'in_progress'`; stops on terminal status
- When status reaches `'complete'`: reads `job.result?.transcript` and calls `onTranscript(transcript)`; sets `status = 'complete'`; after 1200ms, resets to `status = 'idle'`
- When status reaches `'failed'`: sets `error` from `job.error_details` and `status = 'error'`

**Note on `useJobStatus`:** The existing hook polls at 3s. The voice feature requires 2s polling. `useVoiceTranscription` should use `useQuery` directly for the voice job poll (separate from the generation job polling) — do NOT call `useJobStatus` and rely on its 3s interval. The hook must be always-mounted (enabled when `jobId` is non-null) to match the AC requirement of always calling the query hook.

**MicCheck before hook:**
- The hook detects browser support (`typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia`) and exposes an `isSupported: boolean` value, checked after hydration via `useEffect` to prevent SSR mismatch.

### AC 4 — `VoiceBrainDump` component

**Given** `frontend/components/campaigns/VoiceBrainDump.tsx` is reviewed,

**Browser unsupported state:**
- If `isSupported` is false after hydration, renders:
  ```
  <p class="text-[11px] font-mono text-graphite min-h-[44px] flex items-center">
    Microphone access unavailable. Type your Brain Dump below.
  </p>
  ```
  The mic button is NOT rendered. No console errors thrown.

**Idle / Complete state — "Record" button:**
```
<div class="flex items-center gap-3 min-h-[44px]">
  <button
    aria-label="Record voice Brain Dump"
    class="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-ink rounded-none bg-transparent text-[11px] font-mono text-ink uppercase tracking-[0.08em] hover:bg-ink hover:text-paper transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
  >
    <Mic size-3.5 aria-hidden="true" />
    <span>Record</span>
  </button>
  <span role="status" aria-live="polite" aria-atomic="true">{/* empty */}</span>
</div>
```

**Recording state — "Stop recording" button + pulsing indicator:**
```
<button
  aria-label="Stop recording"
  class="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-ink rounded-none bg-ink text-paper hover:bg-transparent hover:text-ink transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
>
  <Square size-3.5 aria-hidden="true" />
  <span>Stop recording</span>
</button>
<span role="status" aria-live="polite" aria-atomic="true">
  <span class="inline-block size-2 rounded-full bg-danger animate-[voice-pulse_1.4s_ease-in-out_infinite] motion-reduce:animate-none" aria-hidden="true" />
  <span class="text-[11px] font-mono text-graphite ml-1.5">Recording...</span>
</span>
```

**Uploading state — disabled button:**
```
<button
  disabled
  aria-label="Uploading audio, please wait"
  class="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-border rounded-none bg-transparent text-graphite opacity-60 cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
>
  <Loader2 size-3.5 animate-spin aria-hidden="true" />
  <span>Uploading</span>
</button>
<span role="status" aria-live="polite" aria-atomic="true">
  <span class="text-[11px] font-mono text-graphite">Uploading...</span>
</span>
```

**Transcribing state — identical disabled style, different copy:**
- Button `aria-label="Transcribing audio, please wait"`, label text `Transcribing`, status span text `Transcribing...`

**Error state — "Try again" button:**
```
<button
  aria-label="Try recording again"
  class="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-ink rounded-none bg-transparent text-ink hover:bg-ink hover:text-paper transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
>
  <RotateCcw size-3.5 aria-hidden="true" />
  <span>Try again</span>
</button>
<span role="status" aria-live="polite" aria-atomic="true">
  <span class="text-[11px] font-mono text-danger">
    {error ?? "Transcription failed. Try again."}
  </span>
</span>
```

Clicking "Try again" calls `startRecording` — no page navigation.

### AC 5 — Brain Dump page wired up

**Given** `frontend/app/(app)/campaigns/new/page.tsx` is reviewed,
**When** the component is inspected,
**Then** `<VoiceBrainDump onTranscript={...} />` is rendered above the Brain Dump `<textarea>` element.
**And** `onTranscript` is wired to set the page's brain dump state (the same `useState` setter that controls the textarea value): when a transcript arrives, the textarea's value is set to the transcript string (overwriting any prior content) and the character counter updates.

**Important:** There is NO `BrainDumpInput.tsx` component file — the Brain Dump textarea is implemented inline in `new/page.tsx` directly (raw `<textarea>` with `textareaRef` and `resizeTextarea()`). Do NOT create a new `BrainDumpInput.tsx` file. Instead, render `VoiceBrainDump` as a sibling element immediately above the `<textarea>` in the existing JSX layout. Connect `onTranscript` to the same `setBrainDump` state setter and trigger the existing `resizeTextarea()` after setting the value.

The story AC says "between the label and the textarea element" — the recommended layout is:
```jsx
<div className="space-y-1">
  <label ...>Brain Dump</label>
  <VoiceBrainDump onTranscript={(t) => { setBrainDump(t); resizeTextarea(); }} />
  <textarea ref={textareaRef} value={brainDump} ... />
  {/* character counter, quality guidance, etc. below */}
</div>
```

**Cursor positioning:** After setting `setBrainDump(transcript)`, use a `useEffect` or `setTimeout(0)` to move the textarea cursor to the end: `textareaRef.current?.setSelectionRange(transcript.length, transcript.length)`.

### AC 6 — Touch target and focus ring

**Given** all interactive elements are measured at desktop ≥ 1024px, tablet 768–1023px, and mobile < 768px,
**When** rendered,
**Then** every button has `h-11 min-w-[44px]` (44px minimum touch target in both axes).
**And** all buttons have `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1`.
**And** the row container `flex items-center gap-3 min-h-[44px]` reflows without horizontal overflow at all breakpoints.

### AC 7 — Copy rules enforced throughout

**Given** all copy in `VoiceBrainDump.tsx` and `useVoiceTranscription.ts` is reviewed,
**When** every string is checked,
**Then** no exclamation marks are present; no em-dashes (`—`) or double-dashes (`--`) appear in any user-visible string; all error messages name the specific issue rather than using generic phrases.

**Exact copy strings:**

| Context | String |
|---|---|
| Idle button | `Record` / `aria-label="Record voice Brain Dump"` |
| Recording button | `Stop recording` / `aria-label="Stop recording"` |
| Uploading button | `Uploading` / `aria-label="Uploading audio, please wait"` |
| Transcribing button | `Transcribing` / `aria-label="Transcribing audio, please wait"` |
| Try again button | `Try again` / `aria-label="Try recording again"` |
| Recording status | `Recording...` |
| Uploading status | `Uploading...` |
| Transcribing status | `Transcribing...` |
| Default error | `Transcription failed. Try again.` |
| Mic denied | `Microphone access denied.` |
| Service unavailable | `Transcription service unavailable.` |
| File too large | `Audio file too large. Max 10 MB.` |
| Browser unsupported | `Microphone access unavailable. Type your Brain Dump below.` |

### AC 8 — No new npm packages

**Given** `package.json` is reviewed after this story ships,
**When** it is opened,
**Then** no new packages have been added — `MediaRecorder` is a browser built-in, polling uses the existing `@tanstack/react-query` dependency, icons use the existing `lucide-react` dependency.

---

## Dev Notes & Implementation Guardrails

### Current State of Files Being Modified

**`frontend/app/(app)/campaigns/new/page.tsx`**
This is the primary Brain Dump page — it is a `"use client"` component. Brain dump state is `const [brainDump, setBrainDump] = useState("")`. The page contains an inline `<textarea>` (NOT a separate `BrainDumpInput.tsx` component). The textarea has `ref={textareaRef}` with a `resizeTextarea()` function that auto-resizes up to `MAX_TEXTAREA_HEIGHT = 480`. The page already uses autosave, character counter, draft restore banner, quality tips, link detection, content type selector, and other features — be careful not to disturb any of these.

**`frontend/lib/types.ts` — `Job` type**
Current fields: `id, campaign_id, client_id, job_type, status, scheduled_at, started_at, completed_at, attempt_count, error_details, created_at`. Add `result?: Record<string, unknown> | null`. This change also affects `useJobStatus` callers — none of them currently read `result`, so adding the optional field is non-breaking.

**`frontend/app/globals.css`**
Currently has `@keyframes`: `cursor-blink`, `shimmer`, `fade-in-up`, `fade-in`, `typewriter`, `slideDown`. Add `voice-pulse` to this list.

### Lucide Icon Import Pattern

```typescript
import { Mic, Square, Loader2, RotateCcw } from "lucide-react";
```

All icons in this component use `size-3.5` (14px) — not the default Lucide size (24px). Pass as a JSX prop: `<Mic size={14} aria-hidden="true" />` or use className `className="size-3.5"`.

### MediaRecorder MIME Type Detection

Safari does not support `audio/webm`. Use `MediaRecorder.isTypeSupported()` to pick the right type:

```typescript
const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
  ? "audio/webm;codecs=opus"
  : "audio/mp4";
const recorder = new MediaRecorder(stream, { mimeType });
```

The backend allowlist includes both: `audio/webm`, `audio/webm;codecs=opus`, `audio/mp4`.

### Uploading Audio as Multipart

Do NOT use `jobsApi` for the upload — it only has `get()`. Use native `fetch` with `FormData`:

```typescript
const formData = new FormData();
formData.append("file", blob, "audio");  // filename doesn't matter to backend
const res = await fetch("/api/v1/voice/transcribe", {
  method: "POST",
  body: formData,
  credentials: "include",
});
```

The backend reads the blob's MIME type from the multipart content header automatically via FastAPI's `UploadFile`.

Note: The frontend calls `/api/v1/voice/transcribe` — this goes through the Next.js proxy configured in `frontend/next.config.ts` (or similar) which rewrites `/api/v1/**` to the FastAPI backend. Verify the proxy rule covers the new `/api/v1/voice/transcribe` path — it almost certainly does since it's a wildcard.

### Polling — Use `useQuery` Directly (Not `useJobStatus`)

`useJobStatus` has a hardcoded `refetchInterval: 3000`. The voice feature spec requires 2s polling. `useVoiceTranscription` should implement its own `useQuery` call for voice jobs:

```typescript
const { data: voiceJob } = useQuery<Job | null>({
  queryKey: ["voice-job", jobId],
  queryFn: async () => (jobId ? jobsApi.get(jobId) : null),
  enabled: !!jobId,
  refetchInterval: (q) => {
    const d = q.state.data;
    if (!d || TERMINAL.has(d.status)) return false;
    return 2000;
  },
  staleTime: 0,
});
```

Use a distinct query key (`"voice-job"`) so it does not interfere with the generation job query (`"job"`).

### Reading `job.result.transcript`

After `result` is added to the `Job` type:
```typescript
const transcript = (voiceJob?.result as { transcript?: string } | null)?.transcript ?? "";
if (voiceJob?.status === "complete" && transcript) {
  onTranscript(transcript);
  // then 1200ms timer to reset status
}
```

### Microphone Release

In `stopRecording`, release the microphone stream immediately after collecting chunks:
```typescript
stream.getTracks().forEach((t) => t.stop());
```
Failure to do this leaves the browser's mic indicator active indefinitely — a very noticeable UX issue.

### SSR Safety

`MediaRecorder` and `navigator.mediaDevices` do not exist during server-side rendering. The `isSupported` check MUST be inside `useEffect`:

```typescript
const [isSupported, setIsSupported] = useState(false);  // false default for SSR
useEffect(() => {
  setIsSupported(
    typeof MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia
  );
}, []);
```

Do not call `typeof MediaRecorder` outside of `useEffect` or a browser-only guard — it will cause SSR errors.

### Import Placement in `new/page.tsx`

Add the import at the top of the file alongside other component imports:
```typescript
import { VoiceBrainDump } from "@/components/campaigns/VoiceBrainDump";
```

The existing imports in this file use `@/` path aliases — follow that convention.

### Existing Brain Dump Page Features to Preserve (Do Not Break)

- `localStorage` autosave with 500ms debounce (`personnapress:brain-dump-draft:{clientId}`)
- Draft restore banner (shown on mount if draft exists)
- Character counter below textarea (`brainDump.length` / `MAX_CHARS`)
- Quality guidance tips (collapsible)
- Link detection indicator
- Content type selector (Blog / Social Only)
- `MIN_CHARS = 20` gate on submit
- `Cmd+Enter` keyboard shortcut to submit
- `useBeforeUnload` guard during generation

None of these features touch the `VoiceBrainDump` component or the `onTranscript` handler — they all read from `brainDump` state which the transcript setter updates via `setBrainDump`. They will automatically reflect the transcript once it arrives.

### File Path Conventions

| File | Path |
|---|---|
| New hook | `frontend/hooks/useVoiceTranscription.ts` |
| New component | `frontend/components/campaigns/VoiceBrainDump.tsx` |
| Modified types | `frontend/lib/types.ts` |
| Modified CSS | `frontend/app/globals.css` |
| Modified page | `frontend/app/(app)/campaigns/new/page.tsx` |

Note: The campaigns component folder already exists (`frontend/components/` has existing `.tsx` files). Place `VoiceBrainDump.tsx` directly in `frontend/components/` (not in a sub-folder) to match the flat structure of the existing components directory. Wait — looking at the story, it says `frontend/components/campaigns/VoiceBrainDump.tsx`. Check if a `campaigns/` subfolder exists. If not, create it. Existing campaign-specific components like `SocialPostEditors.tsx`, `CampaignList.tsx`, `CampaignGenerationOverlay.tsx` are in the flat `components/` folder — follow the flat pattern and place `VoiceBrainDump.tsx` directly in `frontend/components/` to match existing conventions.

---

## Files Checklist

### New Files to Create

| File | Purpose |
|---|---|
| `frontend/hooks/useVoiceTranscription.ts` | MediaRecorder → upload → poll → onTranscript |
| `frontend/components/VoiceBrainDump.tsx` | Mic button, state indicator, error display |

### Existing Files to Modify

| File | Change |
|---|---|
| `frontend/lib/types.ts` | Add `result?: Record<string, unknown> \| null` to `Job` type |
| `frontend/app/globals.css` | Add `@keyframes voice-pulse` |
| `frontend/app/(app)/campaigns/new/page.tsx` | Import + render `VoiceBrainDump`, wire `onTranscript` to `setBrainDump` |

---

## Dev Agent Record

### Implementation Notes

- `@keyframes voice-pulse` added to `globals.css` between `slideDown` and the Base section.
- `result?: Record<string, unknown> | null` added to `Job` interface in `types.ts` — non-breaking optional field.
- `useVoiceTranscription` hook: SSR-safe `isSupported` check via `useEffect`; MediaRecorder with `audio/webm;codecs=opus` / `audio/mp4` Safari fallback; `ondataavailable` 100ms timeslice; `onstop` assembles blob, stops tracks, POSTs FormData to `${API_URL}/api/v1/voice/transcribe`; `useQuery` with `["voice-job", jobId]` key and 2s polling; 1200ms reset-to-idle after `complete`; error messages per AC 7 copy table.
- `VoiceBrainDump` component: pure state-render pattern with 6 branches (unsupported, recording, uploading, transcribing, error, idle/complete); all touch targets h-11 min-w-[44px]; `role="status" aria-live="polite" aria-atomic="true"` on every status span.
- `new/page.tsx`: `VoiceBrainDump` rendered inside existing `<div className="space-y-2 mb-4">` immediately above the `<textarea>`; `onTranscript` slices to MAX_CHARS, then uses `setTimeout(0)` to resize and move cursor to end.
- API route: frontend calls `NEXT_PUBLIC_API_URL/api/v1/voice/transcribe` directly (same pattern as all other API calls — no Next.js proxy layer exists).
- 17 unit tests for `VoiceBrainDump` covering all 6 states, button interactions, and copy-rule enforcement.

### Completion Notes

All ACs satisfied:
- AC 1: `@keyframes voice-pulse` in `globals.css` ✓
- AC 2: `result?` field on `Job` type ✓
- AC 3: `useVoiceTranscription` hook with full MediaRecorder / upload / poll / onTranscript flow ✓
- AC 4: `VoiceBrainDump` component with all 6 states matching exact AC copy and class specs ✓
- AC 5: `VoiceBrainDump` wired into `new/page.tsx` above textarea, `onTranscript` → `setBrainDump` + resize + cursor ✓
- AC 6: All buttons `h-11 min-w-[44px]`, `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1` ✓
- AC 7: All copy strings match table exactly; no `!`, no `—`, no `--` ✓
- AC 8: No new npm packages added ✓
- 17/17 tests pass; 0 new regressions (pre-existing failures unchanged at 48)

---

## File List

### New Files
- `frontend/hooks/useVoiceTranscription.ts`
- `frontend/components/campaigns/VoiceBrainDump.tsx`
- `frontend/__tests__/components/campaigns/VoiceBrainDump.test.tsx`

### Modified Files
- `frontend/lib/types.ts` — added `result?` to `Job` interface
- `frontend/app/globals.css` — added `@keyframes voice-pulse`
- `frontend/app/(app)/campaigns/new/page.tsx` — imported and rendered `VoiceBrainDump`

---

## Review Findings

- [x] [Review][Patch] Empty transcript on completed job leaves status stuck in 'transcribing' forever [useVoiceTranscription.ts:65-75]
- [x] [Review][Patch] 1.2s cleanup timer not cleared when startRecording called again during 'complete' window [useVoiceTranscription.ts:71-74]
- [x] [Review][Patch] onstop async handler calls setState after unmount [useVoiceTranscription.ts:105-152]
- [x] [Review][Patch] setSelectionRange passes untruncated t.length instead of clamped Math.min(t.length, MAX_CHARS) [page.tsx:496]
- [x] [Review][Patch] startRecording sets status='idle' before getUserMedia resolves causing UI flash from error state [useVoiceTranscription.ts:85]
- [x] [Review][Patch] 'complete' status missing from copy-rule test state arrays [VoiceBrainDump.test.tsx:copy-rules]
- [x] [Review][Defer] onTranscript not stabilized with useCallback before being passed as hook dependency [useVoiceTranscription.ts:81] — deferred, pre-existing React design concern; guards prevent double-invocation
- [x] [Review][Defer] No client-side max recording duration or file-size guard before upload [useVoiceTranscription.ts] — deferred, backend enforces 10MB limit with 413 + error message
- [x] [Review][Defer] Tests use mutable module-level let variables for mock state [VoiceBrainDump.test.tsx] — deferred, Vitest runs serially, beforeEach resets state
- [x] [Review][Defer] TERMINAL set string values tied to backend Job.status enum [useVoiceTranscription.ts:16] — deferred, matches backend "complete"/"failed" values from 9-2
- [x] [Review][Defer] Query cache accumulates entries per jobId without explicit eviction [useVoiceTranscription.ts:50] — deferred, TanStack Query gcTime handles cleanup
- [x] [Review][Defer] Browser supports neither audio/webm nor audio/mp4 MIME type [useVoiceTranscription.ts:91-93] — deferred, no modern browser lacks both in 2026

---

## Change Log

- 2026-08-15: Story 9.3 implemented — voice capture component + hook + CSS keyframe + Job type update (Boris / Claude)
- 2026-08-16: Code review — 6 patches applied, 6 deferred, 4 dismissed
