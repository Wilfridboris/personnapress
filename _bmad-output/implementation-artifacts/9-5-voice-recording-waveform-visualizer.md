---
baseline_commit: 37efa90
---

# Story 9.5: Voice Recording Waveform Visualizer

Status: review

## Story

As a user recording a voice brain dump,
I want to see animated waveform bars that pulse with my voice amplitude during recording,
so that I have clear real-time visual feedback that the microphone is actively picking up my speech.

## Context & Motivation

The existing recording state in `VoiceBrainDump.tsx` shows a red pulse dot plus "Recording..." text. The dot is a fixed CSS animation — it conveys "active" but gives no feedback about whether the mic is actually picking up sound. A waveform visualizer driven by real audio data gives the user confidence their voice is being captured.

The `MediaStream` from `getUserMedia` is already held in `streamRef.current` inside `useVoiceTranscription`. An `AnalyserNode` can tap into this stream as a passive observer — it does not affect `MediaRecorder` or the audio data sent to the backend.

**Scope:** Frontend-only. No backend changes, no DB migrations, no new npm packages. Web Audio API is a browser built-in.

---

## Acceptance Criteria

### AC 1 — Hook exposes `analyserNodeRef`

**Given** `useVoiceTranscription.ts` is updated,
**When** `startRecording()` succeeds and the `MediaStream` is obtained,
**Then** an `AudioContext` is created and stored in `audioCtxRef.current`,
**And** `analyser.fftSize` is set to `64` (producing 32 frequency bins),
**And** `audioCtx.createMediaStreamSource(stream)` is connected to the `AnalyserNode`,
**And** `analyserNodeRef.current` is set to the `AnalyserNode` before `recorder.start(100)` is called,
**And** `analyserNodeRef` (the ref object, not `.current`) is added to the hook's return value,
**And** `UseVoiceTranscriptionReturn` interface is updated to include `analyserNodeRef: React.RefObject<AnalyserNode | null>`.

### AC 2 — Analyser cleans up in `recorder.onstop`

**Given** recording stops (user clicks Stop),
**When** `recorder.onstop` fires,
**Then** `analyserNodeRef.current?.disconnect()` is called,
**And** `analyserNodeRef.current` is set to `null`,
**And** `void audioCtxRef.current?.close()` is called (fire-and-forget, no await),
**And** `audioCtxRef.current` is set to `null`,
**And** this cleanup runs before `setStatus("uploading")` so the RAF loop in `WaveformBars` sees a null analyser and stops.

### AC 3 — Safari suspended state guard

**Given** `AudioContext` is created on Safari (which initialises in `"suspended"` state),
**When** the context is constructed in `startRecording()`,
**Then** `if (audioCtx.state === "suspended") await audioCtx.resume()` is called before connecting the analyser.

### AC 4 — `WaveformBars` component renders correctly

**Given** `WaveformBars` receives a non-null or null `analyserNode` prop,
**When** the component renders,
**Then** exactly 6 bar `<span>` elements are rendered inside a container `<span data-testid="voice-waveform">`,
**And** each bar has Tailwind classes `w-[3px] bg-ink transition-[height] duration-75 ease-out motion-reduce:transition-none`,
**And** initial `style.height` is `"3px"` (minimum),
**And** the container has `aria-hidden="true"` and `className="inline-flex items-end gap-[2px] h-5"`.

### AC 5 — RAF loop drives bar heights from audio data

**Given** `analyserNode` prop is a live `AnalyserNode`,
**When** the `WaveformBars` component mounts,
**Then** a `requestAnimationFrame` loop starts calling `analyserNode.getByteFrequencyData(dataArray)` each frame,
**And** each bar `i` reads from `dataArray[BIN_INDICES[i]]` where `BIN_INDICES = [2, 5, 9, 13, 17, 21]`,
**And** bar height is computed as `3 + (value / 255) * 17` (range 3px to 20px),
**And** the loop is cancelled via `cancelAnimationFrame` in the `useEffect` cleanup.

**Given** `analyserNode` prop is `null`,
**When** `WaveformBars` mounts,
**Then** the `useEffect` returns early with no RAF loop started,
**And** all 6 bars remain at their initial 3px height,
**And** no JavaScript error is thrown.

### AC 6 — Recording state renders waveform, not pulse dot

**Given** `VoiceBrainDump` status is `"recording"`,
**When** the component renders,
**Then** `<WaveformBars analyserNode={analyserNodeRef.current} />` appears between the Stop button and the "Recording..." text,
**And** the red pulse dot span (`animate-[voice-pulse]`) is NOT present,
**And** the Stop button (`aria-label="Stop recording"`) is unchanged,
**And** the "Recording..." text (`text-[11px] font-mono text-graphite`) remains.

### AC 7 — Waveform absent in all non-recording states

**Given** `VoiceBrainDump` status is `"idle"`, `"uploading"`, `"transcribing"`, `"complete"`, or `"error"`,
**When** the component renders,
**Then** no element with `data-testid="voice-waveform"` is present in the DOM.

### AC 8 — Three new tests pass in `VoiceBrainDump.test.tsx`

1. `"renders waveform bars in recording state"` — sets `mockStatus = "recording"`, queries `container.querySelector('[data-testid="voice-waveform"]')`, asserts it exists and has 6 child spans.
2. `"waveform bars absent in non-recording states"` — iterates `["idle", "uploading", "transcribing", "error"]`, asserts `data-testid="voice-waveform"` is not present.
3. `"recording state has no pulse dot"` — sets `mockStatus = "recording"`, asserts no element with class `animate-[voice-pulse]` exists.
**And** the hook mock is updated to include `analyserNodeRef: { current: null }`.

---

## Dev Notes & Implementation Guardrails

### File locations (match project pattern exactly)

- New component: `frontend/components/campaigns/WaveformBars.tsx` — same directory as `VoiceBrainDump.tsx`; all campaign components are top-level files in this folder, not nested
- Hook: `frontend/hooks/useVoiceTranscription.ts` — already exists, extend it
- Component: `frontend/components/campaigns/VoiceBrainDump.tsx` — already exists, extend it
- Tests: `frontend/__tests__/components/campaigns/VoiceBrainDump.test.tsx` — already exists, extend it

### Exact hook changes (`useVoiceTranscription.ts`)

Add two refs at the top of the hook (after existing refs, before `useEffect`):

```ts
const analyserNodeRef = useRef<AnalyserNode | null>(null);
const audioCtxRef = useRef<AudioContext | null>(null);
```

Inside `startRecording()`, immediately after `streamRef.current = stream` (line 103) and before creating `MediaRecorder`:

```ts
const audioCtx = new AudioContext();
if (audioCtx.state === "suspended") await audioCtx.resume();
audioCtxRef.current = audioCtx;
const analyser = audioCtx.createAnalyser();
analyser.fftSize = 64;
audioCtx.createMediaStreamSource(stream).connect(analyser);
analyserNodeRef.current = analyser;
```

Inside `recorder.onstop`, immediately after `streamRef.current?.getTracks().forEach((t) => t.stop())` and before `streamRef.current = null`:

```ts
analyserNodeRef.current?.disconnect();
analyserNodeRef.current = null;
void audioCtxRef.current?.close();
audioCtxRef.current = null;
```

Add `analyserNodeRef` to the return object at line 194:

```ts
return { status, error, isSupported, startRecording, stopRecording, analyserNodeRef };
```

Update the `UseVoiceTranscriptionReturn` interface (around line 23):

```ts
export interface UseVoiceTranscriptionReturn {
  status: VoiceStatus;
  error: string | null;
  isSupported: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  analyserNodeRef: React.RefObject<AnalyserNode | null>;
}
```

Add `import { useRef, useEffect, useState } from "react"` — `useRef` is already imported, no change needed.

### `WaveformBars.tsx` — complete file

```tsx
"use client";

import { useEffect, useRef } from "react";

interface WaveformBarsProps {
  analyserNode: AnalyserNode | null;
}

const NUM_BARS = 6;
const MIN_H = 3;
const MAX_H = 20;
// Voice-range frequency bin indices from a 32-bin (fftSize=64) analyser
const BIN_INDICES = [2, 5, 9, 13, 17, 21] as const;

export function WaveformBars({ analyserNode }: WaveformBarsProps) {
  const barsRef = useRef<(HTMLSpanElement | null)[]>([]);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!analyserNode) return;

    const dataArray = new Uint8Array(analyserNode.frequencyBinCount);

    function tick() {
      analyserNode!.getByteFrequencyData(dataArray);
      barsRef.current.forEach((bar, i) => {
        if (!bar) return;
        const value = dataArray[BIN_INDICES[i]] ?? 0;
        bar.style.height = `${MIN_H + (value / 255) * (MAX_H - MIN_H)}px`;
      });
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [analyserNode]);

  return (
    <span
      data-testid="voice-waveform"
      aria-hidden="true"
      className="inline-flex items-end gap-[2px] h-5"
    >
      {Array.from({ length: NUM_BARS }, (_, i) => (
        <span
          key={i}
          ref={(el) => {
            barsRef.current[i] = el;
          }}
          className="w-[3px] bg-ink transition-[height] duration-75 ease-out motion-reduce:transition-none"
          style={{ height: `${MIN_H}px` }}
        />
      ))}
    </span>
  );
}
```

### `VoiceBrainDump.tsx` — recording state changes only

Add import:

```tsx
import { WaveformBars } from "@/components/campaigns/WaveformBars";
```

Destructure `analyserNodeRef` from the hook:

```tsx
const { status, error, isSupported, startRecording, stopRecording, analyserNodeRef } =
  useVoiceTranscription({ onTranscript });
```

Replace the recording state block (currently lines 22-44). Remove the pulse dot span entirely; add `WaveformBars` inside the `role="status"` span:

```tsx
if (status === "recording") {
  return (
    <div className="flex items-center gap-3 min-h-[44px]">
      <button
        type="button"
        onClick={stopRecording}
        aria-label="Stop recording"
        className="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-ink rounded-none bg-ink text-paper hover:bg-transparent hover:text-ink transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
      >
        <Square size={14} aria-hidden="true" />
        <span>Stop recording</span>
      </button>
      <span role="status" aria-live="polite" aria-atomic="true" className="flex items-center gap-2">
        <WaveformBars analyserNode={analyserNodeRef.current} />
        <span className="text-[11px] font-mono text-graphite">
          Recording...
        </span>
      </span>
    </div>
  );
}
```

### Test mock update (`VoiceBrainDump.test.tsx`)

The `vi.mock` at line 12 must include `analyserNodeRef`:

```ts
vi.mock("@/hooks/useVoiceTranscription", () => ({
  useVoiceTranscription: () => ({
    status: mockStatus,
    error: mockError,
    isSupported: mockIsSupported,
    startRecording: mockStartRecording,
    stopRecording: mockStopRecording,
    analyserNodeRef: { current: null },
  }),
}));
```

Add a `describe("waveform visualizer")` block:

```ts
describe("waveform visualizer", () => {
  it("renders waveform bars in recording state", () => {
    mockStatus = "recording";
    const { container } = renderComponent();
    const waveform = container.querySelector('[data-testid="voice-waveform"]');
    expect(waveform).toBeInTheDocument();
    expect(waveform!.children).toHaveLength(6);
  });

  it("waveform bars absent in non-recording states", () => {
    const states = ["idle", "uploading", "transcribing", "error"] as const;
    for (const s of states) {
      mockStatus = s;
      const { container, unmount } = renderComponent();
      expect(
        container.querySelector('[data-testid="voice-waveform"]'),
      ).not.toBeInTheDocument();
      unmount();
    }
  });

  it("recording state has no pulse dot", () => {
    mockStatus = "recording";
    const { container } = renderComponent();
    expect(
      container.querySelector('.animate-\\[voice-pulse\\]'),
    ).not.toBeInTheDocument();
  });
});
```

### Critical guardrails

**Do NOT create an `AudioContext` at module or component level.** It must be created inside `startRecording()` which is always triggered by a user gesture (button click). Browsers block `AudioContext` creation outside user gestures on Safari and some mobile browsers.

**Do NOT add `requestAnimationFrame` calls anywhere in `VoiceBrainDump.tsx` or `useVoiceTranscription.ts`.** The RAF loop lives exclusively in `WaveformBars.tsx` as a `useEffect`. This keeps the hook and the parent component free of animation concerns.

**Do NOT update React state from inside the RAF loop.** Bar heights are mutated directly via `bar.style.height`. This is intentional — 60fps state updates would cause 60 re-renders/second. The existing hook is already ref-heavy for this reason.

**The `recorder.onstop` cleanup order matters.** Track stop → analyser disconnect + audioCtx close → stream ref null → status update. The current `recorder.onstop` in the hook runs `streamRef.current?.getTracks().forEach((t) => t.stop())` before nulling the stream. Insert the analyser cleanup immediately after `t.stop()` (same block, before `streamRef.current = null`).

**`audioCtxRef.current?.close()` is `void` (fire-and-forget).** Do not `await` it — it returns a Promise but there is nothing to act on after close. Prefix with `void` to satisfy the linter.

**`BIN_INDICES = [2, 5, 9, 13, 17, 21]`** — these are voice-range bins from a 32-bin analyser (fftSize=64). Bin 0 is DC, bins 1-21 cover roughly 0-5kHz (human voice range). Do not use evenly-spaced bins starting from 0 or you'll include the DC component which distorts the visualizer.

**Copy rules (enforced throughout):**
- No em-dashes (`—`) in any string or JSX text
- No double-dashes (`--`) in any string
- No exclamation marks in user-facing text

---

## Files Checklist

### New Files

| File | Purpose |
|---|---|
| `frontend/components/campaigns/WaveformBars.tsx` | 6-bar waveform visualizer driven by AnalyserNode RAF loop |

### Modified Files

| File | Change |
|---|---|
| `frontend/hooks/useVoiceTranscription.ts` | Add `audioCtxRef`, `analyserNodeRef`; setup/teardown in `startRecording` + `recorder.onstop`; expose `analyserNodeRef` in return |
| `frontend/components/campaigns/VoiceBrainDump.tsx` | Import `WaveformBars`; destructure `analyserNodeRef`; replace pulse dot with `<WaveformBars>` in recording state |
| `frontend/__tests__/components/campaigns/VoiceBrainDump.test.tsx` | Add `analyserNodeRef` to hook mock; add 3 new waveform tests |

---

## Tasks/Subtasks

- [x] AC 1 + AC 3: Extend `useVoiceTranscription.ts` — add refs, AudioContext setup with Safari resume guard, connect AnalyserNode, update return type and return value
- [x] AC 2: Add analyser + audioCtx cleanup to `recorder.onstop` in hook
- [x] AC 4 + AC 5: Create `frontend/components/campaigns/WaveformBars.tsx` with RAF loop, null guard, and 6 ink bars
- [x] AC 6: Update `VoiceBrainDump.tsx` recording state — import WaveformBars, destructure analyserNodeRef, remove pulse dot, add WaveformBars
- [x] AC 7: Verify waveform absent in all non-recording states (no change needed — WaveformBars only renders in the recording branch)
- [x] AC 8: Update `VoiceBrainDump.test.tsx` — add analyserNodeRef to mock, add 3 new tests in waveform describe block; run `pnpm test` and confirm all tests pass

### Dev Agent Record

#### Agent Model Used

claude-sonnet-4-6

#### Completion Notes List

- Added `analyserNodeRef` (AnalyserNode) and `audioCtxRef` (AudioContext) refs to `useVoiceTranscription.ts`
- AudioContext created inside `startRecording()` (user-gesture gated); Safari suspended-state guard applied via `if (audioCtx.state === "suspended") await audioCtx.resume()`
- AnalyserNode connected as passive observer via `createMediaStreamSource`; fftSize=64 (32 bins); voice-range BIN_INDICES [2,5,9,13,17,21] used in WaveformBars
- Cleanup in `recorder.onstop`: analyser disconnected, audioCtx closed fire-and-forget with `void`, both refs nulled before `setStatus("uploading")`
- `analyserNodeRef` added to `UseVoiceTranscriptionReturn` interface and hook return value
- New `WaveformBars.tsx` component: 6 ink-colored `<span>` bars driven by RAF loop; heights mutated directly (not via state) to avoid 60fps re-renders; null guard returns early with no loop
- `VoiceBrainDump.tsx`: pulse dot replaced with `<WaveformBars analyserNode={analyserNodeRef.current} />`; WaveformBars only in recording branch so AC 7 satisfied with no extra code
- Hook mock updated with `analyserNodeRef: { current: null }`; 3 new tests added in `describe("waveform visualizer")` block; all 20 tests pass

#### File List

- `frontend/components/campaigns/WaveformBars.tsx` (new)
- `frontend/hooks/useVoiceTranscription.ts` (modified)
- `frontend/components/campaigns/VoiceBrainDump.tsx` (modified)
- `frontend/__tests__/components/campaigns/VoiceBrainDump.test.tsx` (modified)
