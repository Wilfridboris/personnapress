---
baseline_commit: 4d0ee73fd6be1c76d099dd24deec3d3cbedd83f9
---

# Story 3.15: Brain Dump Quality Guidance -- Placeholder & Tips Panel

Status: done

## Story

As a PersonnaPress user writing a Brain Dump,
I want in-context guidance that helps me provide richer, more specific input,
so that the AI has enough E-E-A-T material to generate content that genuinely sounds like me and ranks better.

## Context & Motivation

The blog generation prompt in `generation_prompts.py` explicitly tries to preserve E-E-A-T signals: "RETAIN all first-person experiences, specific numbers, dates, named tools, or unique outcomes." And the prompt warns: "If the Brain Dump says 'I found X', 'I tested X', or 'I built X': use first-person voice in the post."

But this only works if those signals exist in the Brain Dump. When a user submits thin input ("write about AI tools for marketing") the AI has nothing to preserve -- it falls back to generic content regardless of how good the BVP is.

The voice profile solves "sounds like me." The brain dump quality solves "has something worth saying." Both matter for the marketing claim "AI writes exactly in my style."

**Fix:** Two small UX additions to the brain dump textarea:
1. A rich placeholder that models ideal input (replaces the current sparse placeholder)
2. A subtle quality hint for short inputs (< 150 chars) + a collapsible tips panel

No backend changes. No schema changes. Pure frontend.

---

## Acceptance Criteria

### AC 1 -- Rich placeholder text

1. **Given** the Brain Dump textarea on the new campaign page (`/campaigns/new` or equivalent) and on onboarding Step 3, **When** the textarea is empty (no user input), **Then** the placeholder text is replaced with a multi-line example that models high-quality input. The new placeholder:
   - Shows a realistic example with: a specific number, a named tool or platform, a first-person experience marker, and a before/after or outcome
   - Example placeholder text: `e.g. "I ran a 90-day test comparing 3 LinkedIn posting strategies -- daily tips vs. 3x storytelling vs. 2x case studies. Case studies drove 4x more DMs. Most people post daily tips because it feels safe. Here's what I found and why I switched..."`
   - The placeholder disappears on first keystroke (standard HTML textarea placeholder behavior -- no JS needed)
   - The textarea's minimum character validation (20 chars) and maximum (10,000 chars) are unaffected
   - No em-dash in the placeholder text (use `--` instead)

2. **Given** the textarea already contains user-typed content, **When** the page renders, **Then** the placeholder is not visible (standard browser behavior).

---

### AC 2 -- Inline quality hint for short input

3. **Given** the user has typed at least 1 character and the current input is fewer than 150 characters, **When** the character count is evaluated, **Then** a quality hint appears below the existing character counter:
   - Lucide `Lightbulb` icon (12px, `text-[#555555]`) inline before text
   - Text: "Tip: include a specific number, personal outcome, or named tool for best results."
   - Style: `flex items-center gap-1 text-xs text-[#555555] mt-1` (graphite -- WCAG AA compliant; not `#888888` which fails at 3.54:1)
   - The hint container has `aria-live="polite"` so screen readers announce it when it appears
   - No em-dash

4. **Given** the textarea has 150 or more characters, **When** the hint is evaluated, **Then** the hint is not rendered. The 150-character threshold is a simple length proxy -- no NLP analysis is required.

5. **Given** the textarea is empty (0 characters), **When** evaluated, **Then** no hint is shown (the hint only appears when the user has started typing but the input is still short).

---

### AC 3 -- Collapsible tips panel

6. **Given** the Brain Dump section, **When** the page loads, **Then** a collapsed "Tips for better results" disclosure is visible below the textarea (and below the character counter / quality hint area). Default state: collapsed.

7. **Given** the collapsed disclosure, **When** the user clicks the toggle button, **Then** the panel expands with a smooth height animation to show a compact list of brain dump tips:
   - "Start with a specific number, date, or outcome:" followed by the example styled as `<code>` (monospace, visually distinct)
   - "Mention tools or platforms by name:" followed by the example styled as `<code>`
   - "Use first-person:" followed by examples styled as `<code>`
   - "Describe the before/after or the problem you solved"
   - Expand/collapse uses CSS `grid-rows-[0fr]` → `grid-rows-[1fr]` transition (no Framer Motion needed; CSS handles this natively). Inner content wrapped in an overflow-hidden div.
   - `role="region"` and `aria-labelledby` pointing to the toggle button id on the panel div
   - Toggle button has `aria-controls` pointing to the panel id

8. **Given** the expanded panel, **When** the user clicks the toggle again, **Then** the panel collapses with the same CSS transition. Toggle label changes: collapsed shows "Tips for better results" + `ChevronDown` icon; expanded shows "Hide tips" + `ChevronUp` icon (chevron direction is the primary visual cue).

9. **Given** the disclosure panel state, **When** the page is reloaded or navigated away and back, **Then** the panel resets to collapsed (no localStorage persistence).

---

### AC 4 -- Design system compliance

10. **Given** all new UI elements (hint text, disclosure panel, tip list), **When** assessed against the Paper Style design system, **Then**:
    - Hint text: `text-xs text-[#555555]` with Lucide `Lightbulb` icon; hint container has `aria-live="polite"`
    - Disclosure toggle: `rounded-none`, `min-h-[44px]`, `px-2`, `focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1`, `transition-colors duration-150`; has `aria-controls` pointing to panel id
    - Tip list container: `text-sm text-[#555555]`, `rounded-none`, `1px border-[#E5E5E5]`, `bg-[#F9F9F6]` (Paper); has `role="region"` and `aria-labelledby` pointing to toggle id
    - Tip list items: instruction text in `text-[#555555]`, example text in `<code>` with `font-mono text-xs bg-[#F0F0ED] px-1`
    - Expand/collapse: CSS `grid-rows` transition -- no Framer Motion
    - No emojis anywhere; Lucide icons only (`Lightbulb`, `ChevronDown`, `ChevronUp`)
    - No em-dash in any visible text

---

### AC 5 -- Existing validation unaffected

11. **Given** all new UI additions, **When** this story is implemented, **Then** the following existing behaviors are completely unchanged:
    - 20-character minimum: submit button remains disabled below 20 chars
    - 10,000-character maximum
    - Character counter (`N / 10,000 characters`)
    - Counter turns Danger color when below 20 characters
    - `POST /api/v1/campaigns` submission flow
    - Onboarding Step 3 completion logic

---

### AC 6 -- Onboarding Step 3 parity

12. **Given** the onboarding Step 3 brain dump textarea (Story 3.5 / Story 11.4), **When** this story is implemented, **Then** the same placeholder, quality hint, and tips panel are present there as well. Both locations share the same brain dump textarea component (or the changes are applied to the shared component used in both places).

---

## Tasks / Subtasks

### Task 1 -- Find the Brain Dump textarea component

- [x] 1.1 Locate the Brain Dump textarea component. Search:
  ```
  grep -r "brain_dump\|BrainDump\|brain-dump\|10,000\|10000" frontend/components --include="*.tsx" -l
  ```
  Likely candidates: a component in `frontend/components/campaigns/` used on both the new-campaign page and onboarding Step 3.

- [x] 1.2 Confirm the component is shared between `/campaigns/new` and the onboarding Step 3. If they are two separate textarea instances, apply the changes to both. If they share a component, apply once.

---

### Task 2 -- Update the placeholder (AC 1-2)

- [x] 2.1 In the Brain Dump textarea element, replace the existing `placeholder` prop value with:
  ```
  e.g. "I ran a 90-day test comparing 3 LinkedIn posting strategies -- daily tips vs. 3x storytelling vs. 2x case studies. Case studies drove 4x more DMs. Most people post daily tips because it feels safe. Here's what I found and why I switched..."
  ```
  Verify the textarea uses the HTML `placeholder` attribute (standard `<textarea placeholder="...">` or the React equivalent `placeholder={...}`).

---

### Task 3 -- Add the quality hint (AC 3-5)

- [x] 3.1 Below the existing character counter, add a live region wrapper that always renders; the hint is conditionally rendered inside it:
  ```tsx
  <div aria-live="polite" aria-atomic="true">
    {value.length > 0 && value.length < 150 && (
      <p className="flex items-center gap-1 text-xs text-[#555555] mt-1">
        <Lightbulb size={12} aria-hidden="true" />
        Tip: include a specific number, personal outcome, or named tool for best results.
      </p>
    )}
  </div>
  ```
  Where `value` is the current textarea value (already tracked for the character counter). The outer `<div aria-live="polite">` always mounts so it is registered as a live region before content changes -- mounting/unmounting the live region itself prevents announcements.

- [x] 3.2 Import `Lightbulb` from `lucide-react`. Confirm the project uses `lucide-react` (it does -- see existing icon usage throughout the codebase).

---

### Task 4 -- Add the collapsible tips panel (AC 6-9)

- [x] 4.1 Add local state for the panel:
  ```tsx
  const [tipsOpen, setTipsOpen] = useState(false)
  ```

- [x] 4.2 Below the quality hint live region, add the disclosure. Use CSS `grid-rows` for smooth expand/collapse -- no Framer Motion needed:
  ```tsx
  <div className="mt-2">
    <button
      id="brain-dump-tips-toggle"
      type="button"
      onClick={() => setTipsOpen(!tipsOpen)}
      aria-expanded={tipsOpen}
      aria-controls="brain-dump-tips-panel"
      className="flex items-center gap-1 text-xs text-[#555555] min-h-[44px] px-2 py-0
                 hover:text-[#111111] transition-colors duration-150
                 focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
    >
      {tipsOpen
        ? <ChevronUp size={12} aria-hidden="true" />
        : <ChevronDown size={12} aria-hidden="true" />}
      {tipsOpen ? "Hide tips" : "Tips for better results"}
    </button>

    {/* CSS grid-rows transition: no Framer Motion; panel always mounts so aria-controls resolves */}
    <div
      id="brain-dump-tips-panel"
      role="region"
      aria-labelledby="brain-dump-tips-toggle"
      className={`grid transition-[grid-template-rows] duration-200 ease-out ${
        tipsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
      }`}
    >
      <div className="overflow-hidden">
        <ul className="mt-2 border border-[#E5E5E5] bg-[#F9F9F6] p-3 rounded-none
                       list-none space-y-2 text-sm text-[#555555]">
          <li>Start with a specific number, date, or outcome:{" "}
            <code className="font-mono text-xs bg-[#F0F0ED] px-1">
              I increased conversion 28% in 6 weeks
            </code>
          </li>
          <li>Mention tools or platforms by name:{" "}
            <code className="font-mono text-xs bg-[#F0F0ED] px-1">
              We switched from Mailchimp to ConvertKit
            </code>
          </li>
          <li>Use first-person:{" "}
            <code className="font-mono text-xs bg-[#F0F0ED] px-1">I found</code>,{" "}
            <code className="font-mono text-xs bg-[#F0F0ED] px-1">I tested</code>,{" "}
            <code className="font-mono text-xs bg-[#F0F0ED] px-1">my client saw</code>
          </li>
          <li>Describe the before/after or the problem you solved</li>
        </ul>
      </div>
    </div>
  </div>
  ```

  **Why `grid-rows` instead of `{tipsOpen && <ul>}`:** The instant unmount/mount produces a jarring pop. The `grid-rows-[0fr]`→`grid-rows-[1fr]` CSS transition animates height from 0 to natural height without JavaScript measurement or Framer Motion. The panel always mounts (just visually collapsed), which also means `aria-controls` always resolves to a real element.

- [x] 4.3 Import `ChevronDown`, `ChevronUp` from `lucide-react`.

- [x] 4.4 Confirm `tipsOpen` is not persisted (no `localStorage`, no `useEffect` save). Refresh resets to `false`.

---

### Task 5 -- Apply to onboarding Step 3 if separate (AC 6, 12)

- [x] 5.1 If the onboarding Step 3 textarea is a separate component from the campaign-new textarea, apply the same placeholder, hint, and tips panel to that component as well.

- [x] 5.2 If both locations use the same shared textarea component, Task 5 is already done via Task 2-4.

---

### Task 6 -- Verify no regressions

- [x] 6.1 Confirm: typing in the textarea still increments the character counter correctly.
- [x] 6.2 Confirm: submit button is disabled when fewer than 20 chars, enabled at 20+.
- [x] 6.3 Confirm: quality hint appears when 1-149 chars, disappears at 150+.
- [x] 6.4 Confirm: placeholder text is not visible when the textarea contains user input.

---

## Dev Notes

### No backend changes

This is a pure frontend story. No API changes, no schema changes, no backend Python files.

### Textarea value is already tracked

The existing character counter (`N / 10,000 characters`) already tracks `value.length`. The quality hint uses the same `value` variable -- no new state is needed beyond what already exists.

### LightBulb icon name

Lucide uses `Lightbulb` (capital B). Import: `import { Lightbulb, ChevronDown, ChevronUp } from "lucide-react"`.

### Component location heuristic

Based on the codebase structure:
- New campaign page: `frontend/app/(app)/campaigns/new/page.tsx` or a client component it renders
- Brain dump textarea: likely in `frontend/components/campaigns/BrainDumpInput.tsx` or similar
- Onboarding Step 3: `frontend/components/onboarding/` or rendered inside the onboarding flow from Story 11.4

Run the grep in Task 1.1 to confirm before assuming.

### Paper Style colors used

- Hint text and toggle: `#555555` (graphite -- WCAG AA compliant at 7.1:1 on white; `#888888` fails at 3.54:1)
- Tips panel background: `#F9F9F6` (Paper)
- Tips panel border: `#E5E5E5` (Border)
- Tips instruction text: `#555555` (graphite)
- Code example background: `#F0F0ED` (one step darker than Paper -- keeps it Paper-adjacent without introducing a new color)
- Amber for low-confidence (Story 16.7, not this story): `#F59E0B`

### CSS grid-rows collapse pattern

The `grid-rows-[0fr]` / `grid-rows-[1fr]` technique works as follows:
1. The outer `<div>` is always in the DOM, so `aria-controls` always resolves
2. When `tipsOpen = false`, `grid-rows-[0fr]` collapses the grid row to 0 height
3. The inner content `<div>` has `overflow-hidden` so it is visually clipped at 0 height
4. When `tipsOpen = true`, `grid-rows-[1fr]` expands to natural content height
5. `transition-[grid-template-rows] duration-200 ease-out` animates the change
6. No `max-height` hacks, no JavaScript measurement, no Framer Motion bundle weight

### Placeholder character encoding

The placeholder contains `--` (double hyphen) not em-dash. Verify the final string doesn't introduce any `—` characters. The content warning from the project applies to all user-facing text.

### Project Structure Notes

- All changes in `frontend/components/campaigns/` or `frontend/components/onboarding/`
- No new routes
- No new API calls
- No new backend files

### References

- Brain dump validation rules (20 min, 10000 max): `_bmad-output/planning-artifacts/epics.md` Story 3.1
- E-E-A-T retention instruction in blog prompt: `backend/app/integrations/generation_prompts.py` lines 85-86, 120-121
- Onboarding Step 3 brain dump: `_bmad-output/implementation-artifacts/3-5-onboarding-step-3-completion-generation-integration.md`
- Story 11.4 (onboarding platform connection step, Step 3 UX): `_bmad-output/implementation-artifacts/11-4-onboarding-platform-connection-step.md`
- Paper Style design tokens: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md`

### Review Findings

- [x] [Review][Patch] Duplicate hardcoded IDs across components [frontend/app/(app)/campaigns/new/page.tsx:261, frontend/components/onboarding/OnboardingFlow.tsx:588] — both components emit `id="brain-dump-tips-toggle"` and `id="brain-dump-tips-panel"`; use `useId()` per component to avoid fragile static IDs
- [x] [Review][Patch] `<ul>` with `list-none` missing `role="list"` — VoiceOver on iOS/macOS strips list semantics from `list-style: none` lists; add `role="list"` to both `<ul>` elements [frontend/app/(app)/campaigns/new/page.tsx:282, frontend/components/onboarding/OnboardingFlow.tsx:609]
- [x] [Review][Patch] No `prefers-reduced-motion` guard on `grid-rows` transition — add `motion-reduce:transition-none` to both grid containers [frontend/app/(app)/campaigns/new/page.tsx:277, frontend/components/onboarding/OnboardingFlow.tsx:604]
- [x] [Review][Defer] Onboarding step numbering mismatch — spec says "Step 3" but code comment says `// Step 4 state (brain dump)`; pre-existing discrepancy, not introduced by this story — deferred, pre-existing
- [x] [Review][Defer] DRY violation — tips JSX duplicated verbatim across `page.tsx` and `OnboardingFlow.tsx`; per-spec approach (separate components), consider extracting `<BrainDumpTipsPanel>` component in future — deferred, pre-existing
- [x] [Review][Defer] `tipsOpen` not reset on step navigation within `OnboardingFlow` — if user navigates away from Step 4 and back, panel stays expanded; spec only requires reset on page reload — deferred, pre-existing

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. Pure frontend story, TypeScript clean in all changed files. Pre-existing test failures (7 suites, 38 tests) confirmed unchanged by stash-verification.

### Completion Notes List

- Confirmed two separate brain dump locations: `frontend/app/(app)/campaigns/new/page.tsx` (raw `<textarea>`) and `frontend/components/onboarding/OnboardingFlow.tsx` (uses `BrainDumpInput` component). Changes applied to both.
- Replaced placeholder text with E-E-A-T-modeling example containing specific number, named platform, first-person marker, before/after outcome. Uses `--` (no em-dash).
- Added `aria-live="polite" aria-atomic="true"` wrapper that always mounts; quality hint rendered conditionally inside when `length > 0 && length < 150`. Uses `Lightbulb` icon at 12px.
- Added collapsible tips panel with CSS `grid-rows-[0fr]`/`grid-rows-[1fr]` transition (no Framer Motion). Panel always mounts so `aria-controls` resolves. `tipsOpen` defaults to `false`, no persistence.
- All Paper Style design tokens applied: `#555555`, `#F9F9F6`, `#E5E5E5`, `#F0F0ED`, `rounded-none`, `min-h-[44px]`, `focus-visible:ring-2 focus-visible:ring-[#111111]`.
- Existing validation (20-char min, 10,000-char max, danger color, submission flow) unchanged.

### File List

- frontend/app/(app)/campaigns/new/page.tsx
- frontend/components/onboarding/OnboardingFlow.tsx

### Change Log

- 2026-07-30: Implemented story 3-15 -- brain dump quality guidance (rich placeholder, quality hint, collapsible tips panel) in both `/campaigns/new` and onboarding Step 3
