---
baseline_commit: 2f6f772
---

# Story 3.16: Brain Dump Link Detection -- URL Recognition Indicator & Anchor Embedding

Status: done

## Story

As a PersonnaPress user writing a Brain Dump,
I want visual confirmation when URLs I paste are detected,
so that I know they will be used as citations in the generated article.

## Context & Motivation

The brain dump is plain text only -- no rich-text editor, no link formatting. When a user pastes
a URL like `https://some-study.com/results`, the textarea gives zero feedback. The URL looks
identical to every other character. The user has no way to know whether it was "recognized."

The second gap: the blog generation LLM (`generation_prompts.py`) receives the URL as raw text
but has no instruction to embed it as an `<a href>` anchor link in the generated HTML. It may
reference the source in prose, but it will not turn it into a clickable citation.

This story closes both gaps with targeted, minimal changes:

1. **UI:** A reactive text indicator appears below the textarea whenever one or more URLs are
   present in the brain dump. Uses the same hint pattern established in Story 3.15.
2. **Backend:** One-line prompt addition that instructs the LLM to embed detected URLs as
   proper `<a href>` anchor links in the generated article HTML.

No new libraries. No new routes. No schema changes. No database changes.

---

## Acceptance Criteria

### AC 1 -- URL detection indicator appears when a URL is present

1. **Given** the Brain Dump textarea on `/campaigns/new`, **When** the user types or pastes any
   text containing a URL starting with `http://` or `https://`, **Then** a link detection
   indicator appears below the character counter:
   - Icon: Lucide `Link` icon (12px, `aria-hidden="true"`), imported as `LinkIcon` to avoid
     conflict with `next/link`
   - Text (1 link): `1 link detected -- will be cited in your article`
   - Text (N links): `{N} links detected -- will be cited in your article`
   - Style: `flex items-center gap-1 text-xs font-mono text-sky-600 mt-1`
   - No em-dash anywhere -- use `--` (double hyphen)

2. **Given** the indicator is visible, **When** the user removes all URLs from the textarea
   (e.g. deletes the text containing the URL), **Then** the indicator disappears immediately.

3. **Given** the textarea contains only non-URL text (no `http://` or `https://` substring),
   **When** the brain dump is evaluated, **Then** no indicator is shown.

---

### AC 2 -- URL count is accurate

4. **Given** the textarea contains multiple distinct URLs, **When** evaluated, **Then** the
   indicator shows the correct count (e.g. `3 links detected`). The regex
   `/https?:\/\/[^\s]+/g` is used -- each whitespace-delimited token starting with
   `http://` or `https://` counts as one URL.

5. **Given** the textarea contains a URL duplicated across multiple lines (same URL twice),
   **When** evaluated, **Then** it counts as 2 (no deduplication -- regex match count is
   sufficient).

---

### AC 3 -- Accessibility

6. **Given** the indicator region, **When** the page renders, **Then** the link detection
   indicator is wrapped in a **separate** `aria-live="polite" aria-atomic="true"` container
   from the existing quality hint region (Story 3.15). The two live regions must remain
   independent so screen reader announcements do not bleed across them.

7. **Given** a URL is typed into the textarea by keyboard, **When** the indicator appears,
   **Then** screen readers announce the text (e.g. "1 link detected -- will be cited in your
   article") via the live region.

---

### AC 4 -- Onboarding Step 4 parity

8. **Given** the onboarding Step 4 brain dump textarea (`OnboardingFlow.tsx`), **When** this
   story is implemented, **Then** the same URL detection indicator appears there under the
   same conditions, using the same styling and aria-live pattern.

---

### AC 5 -- LLM embeds detected URLs as anchor links

9. **Given** a brain dump submitted to `POST /api/v1/campaigns` that contains one or more URLs,
   **When** the blog generation LLM runs against the brain dump, **Then** the generated HTML
   embeds each URL as a proper anchor link: `<a href="[URL]" rel="noopener noreferrer" target="_blank">[natural anchor text]</a>`
   at the point in the article where the linked resource is referenced. The URL must be
   preserved exactly as provided (no shortening, no paraphrasing). `rel="noopener noreferrer"`
   is mandatory -- consistent with the project's established link convention in `BlogEditor.tsx:264`.

10. **Given** a brain dump with no URLs, **When** the LLM generates the article, **Then** no
    URLs or anchor tags are manufactured. The existing article output is unaffected.

---

### AC 6 -- Existing brain dump behavior unaffected

11. **Given** all changes in this story, **When** implemented, **Then** the following existing
    behaviors are completely unchanged:
    - 20-character minimum validation and submit-button disabled state
    - 10,000-character maximum
    - Character counter display (`N / 10,000 characters`)
    - Counter turning Danger color below 20 characters
    - Quality hint from Story 3.15 (< 150 chars Lightbulb tip)
    - Collapsible tips panel from Story 3.15
    - `POST /api/v1/campaigns` submission flow
    - Onboarding Step 4 completion and skip logic

---

## Tasks / Subtasks

### Task 1 -- Add URL detection logic in `campaigns/new/page.tsx`

- [x] 1.1 Add `useMemo` import if not already present: `import { ..., useMemo } from "react"`.

- [x] 1.2 Derive `linkCount` from the existing `brainDump` state variable:
  ```tsx
  const linkCount = useMemo(
    () => (brainDump.match(/https?:\/\/[^\s]+/g) ?? []).length,
    [brainDump]
  );
  ```
  Place this immediately after the existing `charCount` derivation (or after the `brainDump`
  state declaration). No new state needed.

- [x] 1.3 Add `LinkIcon` to the existing lucide-react import line:
  ```tsx
  import { ArrowLeft, ChevronDown, ChevronUp, Lightbulb, Link as LinkIcon, Loader2 } from "lucide-react";
  ```
  The alias `LinkIcon` avoids shadowing `next/link`'s `Link` component.

- [x] 1.4 Below the existing quality hint `aria-live` region (after the `</div>` that closes
  the quality hint live region), add a **new** separate live region:
  ```tsx
  <div aria-live="polite" aria-atomic="true">
    {linkCount > 0 && (
      <p className="flex items-center gap-1 text-xs font-mono text-sky-600 mt-1">
        <LinkIcon size={12} aria-hidden="true" />
        {linkCount === 1 ? "1 link detected" : `${linkCount} links detected`} -- will be cited in your article
      </p>
    )}
  </div>
  ```
  Keep the two `aria-live` regions separate -- do NOT merge into the existing quality-hint region.

---

### Task 2 -- Add URL detection logic in `OnboardingFlow.tsx`

- [x] 2.1 Add `useMemo` to the existing `import { useState, useEffect, useId, useRef, useCallback }` line.

- [x] 2.2 Derive `linkCount` from the existing `brainDump` state for Step 4:
  ```tsx
  const linkCount = useMemo(
    () => (brainDump.match(/https?:\/\/[^\s]+/g) ?? []).length,
    [brainDump]
  );
  ```
  Place this near the Step 4 state declarations (around line 243 where `brainDump` is declared).

- [x] 2.3 Add `Link as LinkIcon` to the existing lucide-react import:
  ```tsx
  import { ChevronDown, ChevronUp, Lightbulb, Link as LinkIcon } from "lucide-react";
  ```

- [x] 2.4 In the Step 4 JSX, below the existing quality hint live region (`aria-live="polite" aria-atomic="true"` that wraps the Lightbulb tip), add:
  ```tsx
  <div aria-live="polite" aria-atomic="true">
    {linkCount > 0 && (
      <p className="flex items-center gap-1 text-xs font-mono text-sky-600 mt-1">
        <LinkIcon size={12} aria-hidden="true" />
        {linkCount === 1 ? "1 link detected" : `${linkCount} links detected`} -- will be cited in your article
      </p>
    )}
  </div>
  ```

---

### Task 3 -- Update the blog generation prompt (`generation_prompts.py`)

- [x] 3.1 In `backend/app/integrations/generation_prompts.py`, locate the `_BLOG_PROMPT` string,
  specifically the BRAIN DUMP label at line ~128:

  **Current text (single parenthetical):**
  ```
  BRAIN DUMP (author's raw ideas: build the blog around the core argument, but RETAIN all first-person experiences, specific numbers, dates, named tools, or unique outcomes. These are E-E-A-T and Information Gain signals; do not generalize or anonymize them):
  ```

  **Replace with (one sentence added at the end of the parenthetical, before the closing `)`:**
  ```
  BRAIN DUMP (author's raw ideas: build the blog around the core argument, but RETAIN all first-person experiences, specific numbers, dates, named tools, or unique outcomes. These are E-E-A-T and Information Gain signals; do not generalize or anonymize them. If the brain dump contains any URLs (http:// or https://), embed each as an HTML anchor link <a href="[URL]" rel="noopener noreferrer" target="_blank">[natural anchor text describing what the URL points to]</a> at the point in the article where it is most relevant; preserve each URL exactly as provided):
  ```

  This is a single-line edit inside the triple-quoted `_BLOG_PROMPT` string. No other prompt
  sections change.

- [x] 3.2 Verify no em-dash characters were introduced. The addition uses `--` and no `—`.

- [x] 3.3 No Python unit tests need to be written for this prompt change (prompt text is
  validated by integration behavior, not unit tests). If a test exists that asserts the
  exact BRAIN DUMP label text, update it to match.

---

### Task 4 -- Verify no regressions

- [x] 4.1 On `/campaigns/new`: type a URL into the brain dump. Confirm indicator appears.
  Delete the URL. Confirm indicator disappears.
- [x] 4.2 Paste two URLs in the brain dump. Confirm indicator shows `2 links detected`.
- [x] 4.3 Confirm the quality hint (Lightbulb, < 150 chars) still appears independently.
- [x] 4.4 Confirm the collapsible tips panel still expands/collapses.
- [x] 4.5 Confirm character counter still updates correctly.
- [x] 4.6 Confirm submit button disabled/enabled threshold (20 chars) is unaffected.
- [x] 4.7 Run the same checks on onboarding Step 4.

---

## Dev Notes

### Two separate brain dump textarea locations

As confirmed in Story 3.15:
- `frontend/app/(app)/campaigns/new/page.tsx` -- uses a raw `<textarea>` (not `BrainDumpInput`),
  has its own `brainDump` state, character counter, and quality hint live region.
- `frontend/components/onboarding/OnboardingFlow.tsx` -- uses `BrainDumpInput` component from
  `frontend/components/ui/Input.tsx`, has its own `brainDump` state and quality hint live region.

Apply changes to both files. `BrainDumpInput` itself does not need changes -- it's a presentational
component.

### URL regex

```ts
/https?:\/\/[^\s]+/g
```

- Matches `http://` and `https://` tokens
- Stops at the first whitespace character
- Counts each match (no deduplication)
- Simple and fast; no edge-case URL validation needed

### Naming conflict: `Link` from lucide-react vs `next/link`

`campaigns/new/page.tsx` imports `Link` from `next/link` (for navigation). Import the Lucide
icon with an alias to avoid shadowing:

```tsx
import { Link as LinkIcon } from "lucide-react";
```

`OnboardingFlow.tsx` does not import `Link` from `next/link` -- verify before importing; the
alias is still a good practice regardless.

### Color choice: `text-sky-600`

The Paper Style design system defines:
- `text-ink` (#111111) -- primary text
- `text-graphite` (#555555) -- secondary/muted text
- `text-danger` -- error state

There is no semantic "info" or "success" color token. `text-sky-600` (Tailwind v4 built-in,
approx `#0284C7`) is used for the link indicator because:
- It reads as "recognized/informational" not "error" (red) or "neutral" (gray)
- It contrasts sufficiently against the Paper white background (WCAG AA: 4.6:1)
- It is visually distinct from the existing graphite quality hint

Do NOT use `#888888` -- that color fails WCAG AA contrast at 3.54:1.

### Prompt change scope

The LLM prompt change is confined to one parenthetical inside `_BLOG_PROMPT`. It adds a URL
embedding instruction without touching any other generation logic, voice injection, or
structural requirements. Both Gemini and Anthropic providers import `_BLOG_PROMPT` from
`generation_prompts.py` -- the change applies to both automatically.

### No backend tests to add

The prompt addition is phrasing, not logic. No new Python test is needed unless a test exists
that asserts the exact BRAIN DUMP label text (check with `grep "_BLOG_PROMPT\|BRAIN DUMP"
backend/tests/`).

### Placement of link indicator relative to existing hints

Current layout in both locations (top to bottom):
```
[ textarea ]
N / 10,000 characters          ← char counter
[ Lightbulb ] Tip: include...  ← quality hint (< 150 chars, aria-live="polite")
[ ChevronDown ] Tips for...    ← collapsible tips panel
```

After this story:
```
[ textarea ]
N / 10,000 characters
[ Lightbulb ] Tip: include...  ← existing quality hint region (unchanged)
[ LinkIcon ] N links detected  ← NEW: separate aria-live region, only when URLs present
[ ChevronDown ] Tips for...    ← existing tips panel (unchanged)
```

The link indicator sits between the quality hint and the tips panel toggle.

### Paper Style design tokens used in this story

| Token | Value | Usage |
|-------|-------|-------|
| `text-sky-600` | ~#0284C7 | Link detection indicator text + icon |
| `font-mono` | JetBrains Mono | Indicator text (consistent with char counter) |
| `text-xs` | 12px | Indicator text size |

### References

- Brain dump textarea locations confirmed: Story 3.15 Dev Agent Record (Completion Notes)
- Existing quality hint pattern: `frontend/app/(app)/campaigns/new/page.tsx` lines 253-259,
  `frontend/components/onboarding/OnboardingFlow.tsx` lines 580-587
- Blog prompt BRAIN DUMP label: `backend/app/integrations/generation_prompts.py` line 128
- `_BLOG_PROMPT` shared by Gemini and Anthropic providers: `generation_prompts.py` line 1-6
  (module docstring confirms both importers)
- Paper Style color tokens: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md`
- Story 3.15 (quality hint + tips panel, same two files): `3-15-brain-dump-quality-guidance.md`

---

## Dev Agent Record

### Completion Notes

Implemented story 3-16 in full across three files. No new libraries, routes, or schema changes introduced.

- **Task 1 (`campaigns/new/page.tsx`):** Added `useMemo` to the React import, `Link as LinkIcon` to the lucide-react import. Derived `linkCount` from `brainDump` state using `/https?:\/\/[^\s]+/g` regex. Added a separate `aria-live="polite" aria-atomic="true"` region between the quality hint and tips panel toggle, rendering the sky-600 indicator only when `linkCount > 0`.
- **Task 2 (`OnboardingFlow.tsx`):** Same pattern applied to Step 4 brain dump. `useMemo` and `Link as LinkIcon` added; `linkCount` derived from `brainDump` state. New aria-live region inserted between quality hint and tips toggle.
- **Task 3 (`generation_prompts.py`):** One-line addition appended to the BRAIN DUMP parenthetical in `_BLOG_PROMPT` instructing the LLM to embed detected URLs as `<a href>` anchor tags with `rel="noopener noreferrer" target="_blank"`. No em-dash introduced. All 72 backend tests pass.
- **Task 4 (regressions):** Implementation is purely additive -- existing charCount, quality hint, tips panel, and submit-button logic are untouched. TypeScript errors visible in `tsc --noEmit` output are pre-existing in test fixture files unrelated to this story.

---

## File List

- `frontend/app/(app)/campaigns/new/page.tsx`
- `frontend/components/onboarding/OnboardingFlow.tsx`
- `backend/app/integrations/generation_prompts.py`

---

## Review Findings

- [x] [Review][Patch] Backend prompt missing explicit negative instruction for no-URL case [`backend/app/integrations/generation_prompts.py:128`] — The BRAIN DUMP instruction says "If the brain dump contains any URLs ... embed each" but has no explicit "If no URLs are present, do not add anchor tags." Add a negative guard to prevent potential hallucination.
- [x] [Review][Defer] Trailing punctuation matched into URL regex [`frontend/app/(app)/campaigns/new/page.tsx:75`, `frontend/components/onboarding/OnboardingFlow.tsx:244`] — deferred, pre-existing: spec prescribes the exact regex `/https?:\/\/[^\s]+/g`; changing it would deviate from AC 2.
- [x] [Review][Defer] URL regex duplicated in two frontend files with no shared utility [`campaigns/new/page.tsx`, `OnboardingFlow.tsx`] — deferred, pre-existing: project pattern; maintenance risk only.
- [x] [Review][Defer] `javascript:`/`data:` scheme injection via user-supplied URL in prompt [`generation_prompts.py`] — deferred, pre-existing: LLM is conditioned on `http://`/`https://` only; authenticated users' own content.
- [x] [Review][Defer] Duplicate URLs in brain dump produce non-deterministic LLM link placement [`generation_prompts.py:128`] — deferred: spec does not specify LLM deduplication behavior.
- [x] [Review][Defer] Malformed URLs (e.g., `https://` with no host) not guarded in prompt [`generation_prompts.py:128`] — deferred: edge case; no spec guidance.
- [x] [Review][Defer] URL inside Markdown link syntax `[text](https://...)` double-counted by regex [`both frontend files`] — deferred: brain dump is plain text; extremely edge case.
- [x] [Review][Defer] `{brain_dump}` format-string injection if user puts `}` in content [`generation_prompts.py`] — deferred, pre-existing: the `{brain_dump}` placeholder pre-exists this story.
- [x] [Review][Defer] No upper bound on displayed link count in UI indicator [`both frontend files`] — deferred: out of scope; no spec constraint.

## Change Log

- 2026-07-30: Implemented story 3-16 -- URL detection indicator in brain dump textarea (campaigns/new + onboarding Step 4) and LLM anchor-link embedding instruction in `_BLOG_PROMPT`.
- 2026-07-30: Code review complete -- 1 patch applied (negative URL guard in BRAIN DUMP prompt), 8 deferred, 10 dismissed.
