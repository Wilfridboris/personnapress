---
baseline_commit: 42ed019a11a827808a4ba5d7c682eb54348f6326
---

# Story 16.3: Expanded BVP Review and Edit UI

Status: done

## Story

As a PersonnaPress user,
I want to review and edit all 20 dimensions of my Brand Voice Profile including the Voice Brief,
so that I can correct any field the system got wrong before it shapes my generated content.

## Acceptance Criteria

### AC 1 -- Voice Brief panel

1. **Given** the `/clients/{id}/voice` page and a BVP containing a non-empty `voice_brief` field, **When** the page loads in any mode, **Then** the Voice Brief panel is the FIRST element rendered below the action bar, with:
   - Background: `#FFF1B8` (Highlighter)
   - Border: `1px solid #111111` (Ink)
   - Heading: Playfair Display, "How PersonnaPress understands your writing"
   - Body: the `voice_brief` string in Inter, `text-sm`, `leading-[1.7]`
   - Footer label: "REGENERATED AUTOMATICALLY WHEN YOU REFRESH YOUR PROFILE" in 11px uppercase tracked Inter, Graphite
   - The Voice Brief is read-only; no edit control appears for it

---

### AC 2 -- Legacy BVP upgrade nudge

2. **Given** a BVP that has no `voice_brief`, `pronoun_preference`, or `formality_scale` (legacy 3-field BVP), **When** the page loads, **Then** a nudge panel appears below the action bar (in place of the Voice Brief panel) with:
   - Body text: "Refresh your voice profile to unlock 17 additional dimensions including Voice Brief synthesis, writing patterns, and anchor phrases. Your current profile stays intact during the refresh."
   - A Secondary Button: "Refresh profile" (with Lucide `RefreshCw` icon)
   - The existing tone, cadence, and banned_jargon fields continue to display below the nudge panel (backward compatibility)

---

### AC 3 -- Identity group

3. **Given** the Identity section, **When** in read-only mode, **Then** each field shows a static chip: Border fill, Graphite text, plain display value (e.g. "First person (I / we)").

4. **Given** the Identity section, **When** in edit mode, **Then**:
   - `pronoun_preference`: 3-option chip group with aria-pressed (options: "First person (I / we)", "Second person (you)", "Mixed")
   - `formality_scale`: a 5-cell segmented control, each cell `min-h-[44px] w-12`, selected cell shows Highlighter fill; labeled "Casual" (left) and "Formal" (right); `aria-label="Formality scale 1 to 5"` on the group, `aria-label="Formality N of 5"` on each cell
   - `humor_style`: 4-option chip group (None, Dry, Playful, Self-deprecating)
   - `vocabulary_complexity`: 3-option chip group (Plain, Mixed, Technical)
   - All option chips: `min-h-[44px]`, active state Highlighter + 1px Ink border, inactive state `border-[#E5E5E5]` hover `border-[#111111]`, `border-transition-colors duration-150`

---

### AC 4 -- Computed metrics section (always read-only)

5. **Given** the Writing Metrics section with computed fields from Story 16.1, **When** rendered, **Then** fields appear as stat chips: `border-[#E5E5E5] bg-[#F9F9F6]`, each chip shows a Graphite `text-[10px] uppercase` label and an Ink `text-sm` value side by side. A Lucide `Lock` icon (12px, Graphite) and label "Computed from your writing -- not editable" appears above the chips.

6. **Given** no computed fields are present in the BVP, **When** the Writing Metrics section renders, **Then** it is hidden entirely (do not show an empty section).

---

### AC 5 -- Patterns group

7. **Given** the Patterns section, **When** in edit mode, **Then**:
   - `example_style`: 4-option chip group (Analogy, Data, Story, Direct)
   - `specificity_preference`: 3-option chip group (Concrete numbers, Vague quantifiers, Mixed)
   - `opening_pattern`: 5-option chip group (Question, Bold claim, Anecdote, Statistic, Problem)
   - `closing_pattern`: 5-option chip group (CTA, Question, Summary, One-liner, None)
   - `header_style`: 4-option chip group (Question, Command, Statement, Mixed)
   - `post_structure_template`: plain text `Input` component (existing) with placeholder "hook -> pain -> insight -> example -> CTA"

8. **Given** the Patterns section, **When** in read-only mode, **Then** each enum field shows a static chip with the current value; `post_structure_template` shows as plain `text-sm` body text.

---

### AC 6 -- Anchors group

9. **Given** the Anchors section, **When** in edit mode, **Then**:
   - `signature_phrases`: existing TagChip add/remove pattern with Input; placeholder "Add a phrase and press Enter"
   - `banned_jargon`: existing TagChip add/remove pattern; placeholder "Add a word or phrase and press Enter"
   - `voice_anchor_sentences`: numbered list display using JetBrains Mono `text-xs`; each item in a `border-[#E5E5E5] bg-[#F9F9F6]` box; remove button is a Lucide `X` icon (14px), `min-h-[44px] min-w-[44px]`; add Input accepts one sentence at a time; max 5 items enforced (input hidden when 5 are present)
   - `anti_pattern_example`: textarea using bottom-border only pattern (`border-b border-[#111111]`, no ring), 2 rows, placeholder "e.g. Synergizing our core competencies to leverage actionable insights..."

10. **Given** the Anchors section, **When** in read-only mode, **Then** TagChips display without remove buttons; voice_anchor_sentences display as numbered list in JetBrains Mono; `anti_pattern_example` displays in JetBrains Mono `text-xs text-[#555555]`.

---

### AC 7 -- Save behavior

11. **Given** the user clicks "Save profile", **When** `PATCH /api/v1/clients/{client_id}` is called, **Then** the PATCH body contains `brand_voice_profile` with all editable fields; computed fields (`sentence_length_avg`, `sentence_rhythm`, `paragraph_density`, `contraction_frequency`, `list_preference`) and `voice_brief` are EXCLUDED from the PATCH body (server owns them).

12. **Given** the PATCH succeeds, **When** the response arrives, **Then** a success message "Voice profile saved." appears in `text-sm text-[#2E4F2E]`; edit mode exits; the action bar returns to "Refresh profile" / "Edit profile" state.

13. **Given** the PATCH fails, **When** the error arrives, **Then** an error message appears in `text-sm text-[#8B0000]`; the user remains in edit mode so they can retry.

---

### AC 8 -- Design system compliance

14. **Given** the page, **When** assessed against the Paper Style design system, **Then**:
    - All borders: `rounded-none` (no border-radius)
    - All interactive elements: `min-h-[44px]` minimum touch target
    - All interactive elements: `focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1`
    - No emojis anywhere; Lucide icons only
    - Transitions: `transition-colors duration-150` (no Framer Motion)
    - Section containers: `border border-[#E5E5E5] bg-white p-6`
    - Section labels: `text-xs uppercase tracking-[0.06em] text-[#111111]`
    - Field labels: `text-[11px] uppercase tracking-[0.06em] text-[#555555]`

---

## Tasks / Subtasks

### Task 1 -- Add `ExpandedBrandVoiceProfile` type to `frontend/lib/types.ts`

- [x] 1.1 Add the type definition:
  ```ts
  export interface ExpandedBrandVoiceProfile {
    // Legacy fields (preserved)
    tone?: string[];
    cadence?: { avg_sentence_length: number; variation_pattern: string; paragraph_structure: string };
    banned_jargon?: string[];
    target_audience?: string | null;
    // Computed (read-only)
    sentence_length_avg?: number;
    sentence_rhythm?: "uniform" | "varied";
    paragraph_density?: "airy" | "moderate" | "dense";
    contraction_frequency?: "never" | "occasional" | "frequent";
    list_preference?: "rarely" | "sometimes" | "often";
    low_confidence?: boolean;
    // Qualitative identity
    pronoun_preference?: "first_person" | "second_person" | "mixed";
    formality_scale?: number;
    humor_style?: "none" | "dry" | "playful" | "self_deprecating";
    vocabulary_complexity?: "plain" | "mixed" | "technical";
    // Qualitative patterns
    example_style?: "analogy" | "data" | "story" | "direct";
    specificity_preference?: "concrete_numbers" | "vague_quantifiers" | "mixed";
    opening_pattern?: "question" | "bold_claim" | "anecdote" | "stat" | "problem";
    closing_pattern?: "cta" | "question" | "summary" | "one_liner" | "none";
    header_style?: "question" | "command" | "statement" | "mixed";
    post_structure_template?: string;
    // Anchors
    signature_phrases?: string[];
    voice_anchor_sentences?: string[];
    anti_pattern_example?: string;
    // Synthesized
    voice_brief?: string;
  }
  ```

- [x] 1.2 Update `ClientResponse` type (or wherever `brand_voice_profile` is typed) to use `ExpandedBrandVoiceProfile` instead of `BrandVoiceProfile`. Check `frontend/lib/types.ts` for the existing `BrandVoiceProfile` definition and update all references.

---

### Task 2 -- Create `ExpandedProfileReview.tsx`

- [x] 2.1 Create `frontend/components/clients/ExpandedProfileReview.tsx` as a `"use client"` component. The complete reference implementation from the UX design session is below -- use it as the authoritative source:

  **Sub-components to implement:**
  - `FieldLabel` -- `text-[11px] uppercase tracking-[0.06em] text-[#555555]`
  - `FieldGroup` -- white card with 1px `border-[#E5E5E5]`, `p-6`, section header above children
  - `ChipSelect` -- radio chip group (read-only: single static chip; edit: chip group with `aria-pressed`)
  - `FormalityScale` -- 1-5 segmented control (read-only: static chip; edit: 5-cell row)
  - `ComputedMetricsRow` -- stat chips with Lock icon header; hidden if no computed fields
  - `VoiceBriefPanel` -- Highlighter panel, always read-only
  - `LegacyUpgradeNudge` -- shown when BVP has no expanded fields
  - `EditableTagList` -- wraps TagChip + Input for `signature_phrases`, `banned_jargon`
  - `VoiceAnchorList` -- numbered list with JetBrains Mono, X remove button, Input add, max 5

- [x] 2.2 The `isExpanded` guard: `bvp.voice_brief != null || bvp.pronoun_preference != null || bvp.formality_scale != null`

- [x] 2.3 PATCH body excludes: `sentence_length_avg`, `sentence_rhythm`, `paragraph_density`, `contraction_frequency`, `list_preference`, `voice_brief`

- [x] 2.4 All Fetch calls use `credentials: "include"` and `process.env.NEXT_PUBLIC_API_URL` prefix (existing pattern in the codebase)

---

### Task 3 -- Update `VoiceSetupPage.tsx` to use `ExpandedProfileReview`

- [x] 3.1 In `frontend/components/clients/VoiceSetupPage.tsx`, import `ExpandedProfileReview`

- [x] 3.2 Replace the `ProfileReview` render in the `"review"` view branch with `ExpandedProfileReview` (same props: `bvp`, `clientId`, `onRefresh`, `refreshDisabled`, `refreshBtnRef`)

- [x] 3.3 The existing `ProfileReview` component can remain in the file for the interim; it is no longer rendered in the review view. It can be removed in a future cleanup story.

- [x] 3.4 Update the refresh confirmation modal copy (inside `VoiceSetupPage`) from "This will overwrite your existing voice profile." to: "This will update your voice profile with insights from the new content. Existing values are preserved where possible."

---

### Task 4 -- RSC loop guard

- [x] 4.1 The `/clients/{id}/voice` page (`frontend/app/(app)/clients/[id]/voice/page.tsx`) is a server component that passes `client` to `VoiceSetupPage`. Verify that NO direct `fetch` calls to the backend are added inside `VoiceSetupPage` or `ExpandedProfileReview` for the initial BVP load. The BVP arrives via `client.brand_voice_profile` (already fetched in the server component). The only fetch calls in `ExpandedProfileReview` are user-triggered (PATCH on save, POST on refresh).

---

## Dev Notes

### Files to create

| File | Action |
|---|---|
| `frontend/components/clients/ExpandedProfileReview.tsx` | CREATE |

### Files to modify

| File | Change |
|---|---|
| `frontend/lib/types.ts` | Add `ExpandedBrandVoiceProfile` type, update `BrandVoiceProfile` references |
| `frontend/components/clients/VoiceSetupPage.tsx` | Replace ProfileReview with ExpandedProfileReview, update confirmation modal copy |

### No backend changes in this story

Story 16.1 and 16.2 handle the backend BVP schema. This story is frontend only.

### Paper Style token reference

```
bg-[#F9F9F6]     -- Paper (page background)
bg-white          -- White (card fill)
bg-[#FFF1B8]     -- Highlighter (Voice Brief panel, active chips)
border-[#E5E5E5] -- Border (default card border, inactive chips)
border-[#111111] -- Ink (active chip border, focus rings)
text-[#111111]   -- Ink (primary text)
text-[#555555]   -- Graphite (secondary text, labels)
text-[#2E4F2E]   -- Success (save confirmation)
text-[#8B0000]   -- Danger (error messages)
```

### UX design reference

The complete `ExpandedProfileReview.tsx` component was designed in the web-uiux-architect session and is the authoritative implementation reference. Key patterns to follow:

- `ChipSelect` uses `aria-pressed` (not radio inputs) for accessibility without form submission
- `FormalityScale` uses `border-r border-[#E5E5E5] last:border-r-0` to create the segmented look without gaps
- `VoiceAnchorList` items show `font-['JetBrains_Mono'] text-xs` to signal "this is your actual writing"
- `anti_pattern_example` textarea uses bottom-border pattern (`border-b border-[#111111]`) matching the rest of the app's Input components
- The `Lock` icon + "not editable" label on computed fields prevents user confusion about why those chips are not clickable

### Existing TagChip component

`frontend/components/ui/TagChip.tsx` already handles add/remove. `EditableTagList` in this story is a wrapper that adds the controlled Input below the chips. Do not modify TagChip.

### Framer Motion is installed but not used here

The project has `framer-motion` installed, but the Paper Style design system uses CSS transitions only. Use `transition-colors duration-150` for chip state changes.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Created `ExpandedProfileReview.tsx` with all AC sub-components: `VoiceBriefPanel`, `LegacyUpgradeNudge`, `ComputedMetricsRow`, `ChipSelect`, `FormalityScale`, `EditableTagList`, `VoiceAnchorList`.
- `isExpandedBVP` guard gates expanded sections; legacy BVP shows nudge + tone/banned-jargon only.
- PATCH body explicitly excludes all 6 computed/synthesized fields; uses `clientsApi.patch` (same fetch wrapper as rest of app).
- `ExpandedBrandVoiceProfile` type added to `types.ts`; `Client`, `ClientResponse`, `ClientListItem` updated to use it.
- `OnboardingFlow.tsx` updated to use `ExpandedBrandVoiceProfile` (collateral fix -- its `bvp` state was typed `BrandVoiceProfile | null` which became incompatible after type widening).
- No new fetch calls in server component path; RSC loop guard confirmed.
- TypeScript and ESLint pass with zero new errors.

### File List

- `frontend/components/clients/ExpandedProfileReview.tsx` (CREATED)
- `frontend/lib/types.ts` (MODIFIED -- added `ExpandedBrandVoiceProfile`; updated `Client`, `ClientResponse`, `ClientListItem`)
- `frontend/lib/api.ts` (MODIFIED -- patch type uses `ExpandedBrandVoiceProfile`; removed stale `BrandVoiceProfile` import)
- `frontend/components/clients/VoiceSetupPage.tsx` (MODIFIED -- import + render `ExpandedProfileReview`; updated modal copy)
- `frontend/components/onboarding/OnboardingFlow.tsx` (MODIFIED -- `bvp` state and `InlineProfileReviewProps` updated to `ExpandedBrandVoiceProfile`)

## Tasks / Review Findings

### Review Findings

- [x] [Review][Patch] Empty arrays/strings silently dropped from PATCH body [`ExpandedProfileReview.tsx:441`] -- `tone`, `bannedJargon`, `signaturePhrases`, `voiceAnchorSentences` guarded with `.length > 0`; `antiPatternExample`/`postStructureTemplate` guarded with truthiness -- deliberate clearing never persisted. Fixed: always include these fields; empty array/null sent when cleared.
- [x] [Review][Patch] `handleCancel` does not reset `saveSuccess` [`ExpandedProfileReview.tsx:469`] -- after save then re-enter edit mode then cancel, stale "Voice profile saved." banner reappears. Fixed: added `setSaveSuccess(false)` to cancel handler.
- [x] [Review][Patch] `textarea` missing `focus-visible` ring -- AC 9 violation [`ExpandedProfileReview.tsx:696`] -- `focus:ring-0` suppressed all focus indicators. Fixed: replaced with `focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1`.
- [x] [Review][Patch] Success toast missing `aria-live` region [`ExpandedProfileReview.tsx:522`] -- screen readers not notified of save success. Fixed: added `role="status"`.
- [x] [Review][Defer] `key={i}` on `VoiceAnchorList` items [`ExpandedProfileReview.tsx:294`] -- index key antipattern; benign since no per-item state. Deferred to cleanup story.
- [x] [Review][Defer] `cadence`/`target_audience` patched from prop not state [`ExpandedProfileReview.tsx:437`] -- these fields are not editable in the UI so reads from prop are intentional. Deferred, pre-existing.

## Change Log

- 2026-07-17: Implemented story 16-3 -- ExpandedBrandVoiceProfile type, ExpandedProfileReview component (Voice Brief panel, legacy nudge, computed metrics, identity/patterns/anchors groups, save/cancel flow), VoiceSetupPage wired to new component, refresh modal copy updated.
- 2026-07-17: Code review patches -- empty-array/string clear fix in handleSave, handleCancel resets saveSuccess, textarea focus-visible ring, success toast role="status", marked done.
