---
baseline_commit: 6f1a9f7
---

# Story 3.17: Brain Dump Large-Text Editing UX -- Capped Height & Scroll-Stable Textarea

Status: done

## Story

As a PersonnaPress user writing a long Brain Dump,
I want the editing experience to stay stable as my text grows,
so that clicking and typing at any position in 10,000 characters never jumps my view to the top.

## Context & Motivation

The brain dump textarea auto-expands via a `useEffect` that runs on every keystroke:

```js
ta.style.height = "auto";          // collapses textarea momentarily
ta.style.height = `${ta.scrollHeight}px`;  // re-expands to full content height
```

At 10,000 characters (JetBrains Mono 14px / 1.7 line-height, ~90 chars/line at `max-w-2xl`),
this produces a textarea approximately 2,600px tall. The "collapse then re-expand" pattern
triggers a full-page layout reflow on every keystroke. The browser compensates by scrolling
the viewport, which visually jumps the user back toward the top of the page every time they type.

Two surfaces are affected:
1. `frontend/app/(app)/campaigns/new/page.tsx` -- inline `<textarea>` with `useEffect([brainDump])`
2. `frontend/components/ui/Input.tsx` (`BrainDumpInput`) -- used by Onboarding Step 3; has
   THREE resize triggers (mount effect, `[controlledValue]` effect, `onInput` handler) all using
   the same collapse-expand pattern, causing TWO layout reflows per keystroke on the onboarding flow.

No backend changes. No schema changes. No new libraries. Pure frontend fix.

---

## Acceptance Criteria

### AC 1 -- Capped height with internal scroll on `/campaigns/new`

1. **Given** the brain dump textarea on `/campaigns/new`, **When** the user types or pastes
   content that causes the textarea to reach `MAX_TEXTAREA_HEIGHT` (480px), **Then** the textarea
   stops growing and content scrolls internally (`overflow-y: auto`). Below the cap, the textarea
   continues to auto-expand as before (`overflow-y: hidden`).

2. **Given** the textarea is below the cap, **When** the user clears content so `scrollHeight`
   drops below `MAX_TEXTAREA_HEIGHT`, **Then** the textarea shrinks back to fit the content
   (standard auto-expand behavior), and `overflow-y` returns to hidden.

3. **Given** the textarea is at or above the cap, **When** the user types any character,
   **Then** NO layout reflow occurs -- the resize logic fast-paths and returns early without
   touching the DOM. The textarea height stays at `MAX_TEXTAREA_HEIGHT`.

4. **Given** the textarea at any height, **When** the resize effect runs (growth phase below cap),
   **Then** `window.scrollY` is saved before the height-reset and restored after, so the page
   scroll position does not shift.

### AC 2 -- Same fix applied to `BrainDumpInput` (Onboarding Step 3)

5. **Given** the `BrainDumpInput` component in `components/ui/Input.tsx`, **When** its three
   resize triggers fire (mount effect, controlled-value effect, `onInput` handler), **Then** all
   three apply the same cap logic: `MAX_TEXTAREA_HEIGHT` of 360px (onboarding context is
   smaller -- CTA button must remain visible), fast-path when already capped, scroll-restore
   in the growth phase.

6. **Given** `BrainDumpInput` currently has `overflow-hidden` hardcoded in its base Tailwind
   class (`min-h-[120px] resize-none overflow-hidden`), **When** the textarea reaches the cap,
   **Then** `overflow-y: auto` is applied via inline `style` prop. Inline styles have higher
   specificity than Tailwind classes, so `overflow-y: auto` correctly overrides the `overflow-y:
   hidden` from `overflow: hidden`. `overflow-x` remains hidden (no horizontal scroll).

### AC 3 -- Remove `transition-all` from the textarea

7. **Given** the textarea in `campaigns/new/page.tsx` currently has `transition-all` in its
   className (line 243), **When** this story is implemented, **Then** `transition-all` is
   replaced with `transition-[border-width] duration-100`. This matches the pattern used in
   `Input.tsx` (line 32) and prevents the height-change animation from fighting the JS resize
   logic during the growth phase.

8. **Given** the existing focus behavior (border 1px at rest, 2px on focus), **When** the user
   focuses the textarea, **Then** the border-width transition still animates correctly. No visual
   regression on the focus state.

### AC 4 -- No regressions

9. **Given** all existing brain dump features (character counter, 20-char minimum validation,
   10,000-char maximum, quality hint at < 150 chars, tips panel, link detection indicator,
   Cmd+Enter submit, Escape no-op), **When** this story is implemented, **Then** all existing
   behavior is unaffected.

10. **Given** the Onboarding Step 3 brain dump, **When** this story is implemented, **Then**
    the step's submit/skip flow, character count display, and placeholder text are unaffected.

---

## Dev Notes

### Files to modify

| File | Change |
|---|---|
| `frontend/app/(app)/campaigns/new/page.tsx` | Resize `useEffect`, `MAX_TEXTAREA_HEIGHT` const, `transition-all` → `transition-[border-width] duration-100` |
| `frontend/components/ui/Input.tsx` | `handleInput`, mount effect, `controlledValue` effect -- all three triggers |

No other files. No new files. No backend changes.

### Resize logic pattern (apply to all triggers)

```ts
const MAX_TEXTAREA_HEIGHT = 480; // px -- use 360 for BrainDumpInput

function resizeTextarea(ta: HTMLTextAreaElement, maxH: number) {
  // Fast-path: already capped -- skip DOM mutation entirely
  if (ta.scrollHeight >= maxH && parseFloat(ta.style.height || "0") >= maxH) {
    ta.style.overflowY = "auto";
    return;
  }

  // Growth phase: save scroll, reset, measure, restore
  const scrollY = window.scrollY;
  ta.style.height = "auto";
  const newH = Math.min(ta.scrollHeight, maxH);
  ta.style.height = `${newH}px`;
  ta.style.overflowY = ta.scrollHeight > maxH ? "auto" : "hidden";
  window.scrollTo({ top: scrollY, behavior: "instant" });
}
```

Extract as a local helper in each file (not shared -- the two files have different `maxH` values
and are otherwise independent). Do NOT create a shared module for this one helper.

### `campaigns/new/page.tsx` -- useEffect change

```ts
// BEFORE:
useEffect(() => {
  const ta = textareaRef.current;
  if (!ta) return;
  ta.style.height = "auto";
  ta.style.height = `${ta.scrollHeight}px`;
}, [brainDump]);

// AFTER:
const MAX_TEXTAREA_HEIGHT = 480;

useEffect(() => {
  const ta = textareaRef.current;
  if (!ta) return;
  resizeTextarea(ta, MAX_TEXTAREA_HEIGHT);
}, [brainDump]);
```

### `campaigns/new/page.tsx` -- textarea className change

```tsx
// BEFORE (line 243):
"py-3 focus:outline-none transition-all min-h-[200px]",

// AFTER:
"py-3 focus:outline-none transition-[border-width] duration-100 min-h-[200px]",
```

### `Input.tsx` -- BrainDumpInput changes

All three triggers call `resizeTextarea(el, 360)`:

```ts
const MAX_BRAIN_DUMP_HEIGHT = 360;

const handleInput = (e: FormEvent<HTMLTextAreaElement>) => {
  resizeTextarea(e.currentTarget, MAX_BRAIN_DUMP_HEIGHT);
  onInput?.(e);
};

// mount effect
useEffect(() => {
  const el = internalRef.current;
  if (!el) return;
  resizeTextarea(el, MAX_BRAIN_DUMP_HEIGHT);
}, []);

// controlled value effect
useEffect(() => {
  const el = internalRef.current;
  if (!el) return;
  resizeTextarea(el, MAX_BRAIN_DUMP_HEIGHT);
}, [controlledValue]);
```

The `overflow-hidden` base class in `BrainDumpInput` remains in the Tailwind className string.
The `resizeTextarea` helper sets `el.style.overflowY` via inline style, which has higher CSS
specificity and correctly overrides the `overflow-y: hidden` from `overflow: hidden`. No
class change needed on the base className.

### Why `window.scrollTo({ behavior: "instant" })` not `"smooth"`

`"smooth"` would create a visible scroll animation that fights the layout reflow, making the
scroll jump WORSE. `"instant"` is a synchronous correction that is invisible to the user.

### Design spec (from web-uiux-architect)

- `MAX_TEXTAREA_HEIGHT` for `/campaigns/new`: **480px** -- 20 lines visible, leaves room
  for the 3 optional fields and the submit button below without excessive page scroll.
- `MAX_TEXTAREA_HEIGHT` for `BrainDumpInput` (onboarding): **360px** -- shorter cap keeps
  the "Generate my first campaign" CTA button visible without scrolling.
- **No additional visual decoration** when in scrolling mode. The native browser scrollbar
  is the cue. `overflow-x` stays hidden. No gradient fades, no border changes.
- **No height animation** during the growth phase. `transition-[border-width]` only.
  CSS height transition must NOT be applied -- it conflicts with JS `scrollHeight` measurement.
- The transition from "expanding" to "scrolling" (growth → capped) happens instantly
  with no micro-animation. Paper Style is flat and does not animate layout changes.

---

## Out of Scope

- Draft autosave (separate story 3-18)
- Any changes to the backend, schema, or API
- Any changes outside `campaigns/new/page.tsx` and `components/ui/Input.tsx`
- Any new dependencies or shared utilities
- Changes to other textarea fields on the page (Focus keyword, Supporting keywords, Target
  audience are `<input>` elements, not textareas -- unaffected)

---

## Tasks / Subtasks

- [x] Task 1: Apply capped-height resize logic to `campaigns/new/page.tsx`
  - [x] Add `MAX_TEXTAREA_HEIGHT = 480` const and `resizeTextarea` helper
  - [x] Replace `useEffect` collapse-expand with `resizeTextarea(ta, MAX_TEXTAREA_HEIGHT)`
  - [x] Replace `transition-all` with `transition-[border-width] duration-100` on textarea className
- [x] Task 2: Apply capped-height resize logic to `BrainDumpInput` in `components/ui/Input.tsx`
  - [x] Add `MAX_BRAIN_DUMP_HEIGHT = 360` const and `resizeTextarea` helper
  - [x] Update `handleInput` to call `resizeTextarea(e.currentTarget, MAX_BRAIN_DUMP_HEIGHT)`
  - [x] Update mount effect to call `resizeTextarea(el, MAX_BRAIN_DUMP_HEIGHT)`
  - [x] Update controlled-value effect to call `resizeTextarea(el, MAX_BRAIN_DUMP_HEIGHT)`

---

## Dev Agent Record

### Implementation Plan

Applied the `resizeTextarea` helper pattern as specified in Dev Notes. The helper:
1. Fast-paths (no DOM mutation) when the textarea is already at or above the cap height
2. In the growth phase, saves `window.scrollY`, performs the collapse-measure-expand, then restores scroll position with `behavior: "instant"`

Each file gets its own copy of the helper with its own cap constant (480px for the campaign page, 360px for onboarding). No shared module created per spec.

### Completion Notes

- `campaigns/new/page.tsx`: Added `MAX_TEXTAREA_HEIGHT = 480`, `resizeTextarea` helper, updated `useEffect`, replaced `transition-all` with `transition-[border-width] duration-100`
- `components/ui/Input.tsx`: Added `MAX_BRAIN_DUMP_HEIGHT = 360`, `resizeTextarea` helper, updated all three resize triggers (`handleInput`, mount effect, controlled-value effect)
- TypeScript check: zero errors in modified files; 4 pre-existing errors in unrelated test files
- Test suite: 7 failed / 38 failed pre-existing on baseline; no regressions introduced

---

## File List

- `frontend/app/(app)/campaigns/new/page.tsx`
- `frontend/components/ui/Input.tsx`

---

## Change Log

- 2026-07-30: Implemented capped-height scroll-stable textarea UX for both brain dump surfaces (Boris / dev agent)

---

## Review Findings

✅ Clean review — all three layers passed (Blind Hunter, Edge Case Hunter, Acceptance Auditor). 0 patch, 0 defer, 0 dismissed.
