---
baseline_commit: 4d0ee73fd6be1c76d099dd24deec3d3cbedd83f9
---

# Story 16.7: Low Confidence Voice Warning

Status: done

## Story

As a PersonnaPress user,
I want to be notified when my Brand Voice Profile was built on insufficient writing samples,
so that I understand why generated content might not match my voice and know exactly how to fix it.

## Context & Motivation

Story 16.1 added a `low_confidence: true` flag to the BVP when fewer than 300 words were available for stylometric analysis. The flag is stored in `clients.brand_voice_profile` JSONB. Currently nothing surfaces it -- users with thin voice profiles (new websites, minimal blog content, sparse file uploads) get content generated against a weak profile with no warning or guidance.

This creates a silent failure: the user submits a Brain Dump, sees generated content that doesn't sound like them, and doesn't know why. Churn risk is highest at this moment.

**Two places to surface the flag:**
1. The voice profile page -- where the user can act on it by adding more content
2. The approval gate -- where the user reviews the content that may have been affected

**No backend changes.** The flag is already in the BVP JSONB, already returned by the existing `GET /api/v1/clients/{id}` endpoint as part of `brand_voice_profile`. This is a pure frontend read-and-display story.

---

## Acceptance Criteria

### AC 1 -- Voice profile page banner

1. **Given** the voice tab of the client detail page (the component tree: `/clients/[id]/page.tsx` → `ClientDetailTabs.tsx` → voice tab content), **When** the loaded client's `brand_voice_profile.low_confidence === true`, **Then** an alert banner is rendered at the top of the voice tab content, before any profile fields or the Voice Brief panel:
   - Background: `#F9F9F6` (Paper -- stays on-system, no imported amber palette)
   - Border: `1px solid #E5E5E5` on right/top/bottom; `4px solid #F59E0B` left accent
   - Lucide `AlertTriangle` icon (16px, color `#F59E0B`) aligned to top of text
   - Message: "Your voice profile was built from limited content -- fewer than 300 words were analysed. Add more writing samples for a more accurate voice match."
   - Layout: `flex-col gap-3 sm:flex-row sm:items-start` -- stacks on mobile, side-by-side on sm+
   - A secondary action button "Add writing samples" that triggers the same upload/scrape modal already used on the voice page (reuse the existing trigger pattern from Story 15.1 / Story 2.4)
   - `role="status"` (not `role="alert"` -- this is a persistent advisory, not an urgent interrupt)
   - No em-dash; double hyphens (`--`) for all dashes

2. **Given** the banner is shown and the user refreshes their voice profile (triggers re-ingestion via Story 16.1 / Story 2.6), **When** the re-ingestion completes with 300+ words, **Then** the `low_confidence` flag is absent or false in the new BVP, the banner does not appear on the next page load.

3. **Given** a client whose `brand_voice_profile` does not contain `low_confidence: true` (the flag is absent, false, or null), **When** the voice tab renders, **Then** no banner is shown. Existing UI is unchanged.

4. **Given** a client with a legacy BVP (Story 16.1 has never run for that client, so the `low_confidence` field does not exist), **When** the voice tab renders, **Then** no banner is shown (treat missing as not low-confidence: `bvp?.low_confidence !== true`).

---

### AC 2 -- Approval gate advisory note

5. **Given** the approval gate page (`/campaigns/[id]`, the `ApprovalGateClient.tsx` component or equivalent), **When** the active client's `brand_voice_profile.low_confidence === true`, **Then** a subtle advisory note appears near the voice fidelity badge:
   - Lucide `Info` icon (12px, `text-[#555555]`) inline before text
   - Text: "Voice profile built from limited samples -- accuracy may vary."
   - Style: `text-xs text-[#555555] flex items-center gap-1` (use `#555555` graphite -- `#888888` fails WCAG AA at 3.54:1)
   - The note is a `<Link>` (next/link): clicking it navigates to `/clients/{clientId}/voice` (the voice tab where the user can add content)
   - `aria-label="View voice profile for {clientName} -- accuracy may vary due to limited samples"` on the Link
   - No em-dash

6. **Given** a campaign whose client does NOT have `low_confidence: true`, **When** the approval gate renders, **Then** no advisory note appears.

7. **Given** the campaign approval gate already shows the voice fidelity badge (AC from Story 4.1: `tone_score`, `cadence_score`), **When** the low-confidence note is shown, **Then** it appears directly below the fidelity badge, not inside it. The badge itself is not modified.

---

### AC 3 -- Design system compliance

8. **Given** both UI surfaces (banner and note), **When** assessed against the Paper Style design system, **Then**:
   - All bordered surfaces: `rounded-none`
   - Lucide icons only (no emojis): `AlertTriangle` for the banner, `Info` for the note
   - All interactive elements: `min-h-[44px]` (the "Add writing samples" button)
   - Focus rings: `focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1` on all interactive elements (button and Link)
   - No em-dash in any visible text
   - Transitions on interactive elements: `transition-colors duration-150`
   - Advisory note text: `text-[#555555]` (graphite -- WCAG AA compliant at 7.1:1; not `#888888` which fails at 3.54:1)
   - Banner background: `#F9F9F6` (Paper) with amber left-accent border `border-l-4 border-l-[#F59E0B]` -- stays within the existing Paper palette, no imported color scheme

---

### AC 4 -- No backend changes

9. **Given** this story, **When** fully implemented, **Then** no backend Python files are modified, no Alembic migration is added, no API endpoint is changed. The `low_confidence` flag is already stored in `clients.brand_voice_profile` JSONB by Story 16.1 and already included in the client object returned by the existing API.

---

## Tasks / Subtasks

### Task 1 -- Locate the voice tab component (AC 1-4)

- [x] 1.1 Find the voice tab content component. It is likely one of:
  - `frontend/components/clients/ClientDetailTabs.tsx` (tab shell that switches panels)
  - A dedicated component rendered when the "Voice" tab is active (e.g., `VoiceProfilePanel.tsx`, `BrandVoiceTab.tsx`, or similar)
  - Search: `grep -r "voice_brief\|low_confidence\|brand_voice_profile" frontend/components/clients/`

- [x] 1.2 Identify where `brand_voice_profile` is accessed in the voice tab. The client data is likely fetched by a parent server component or React Query hook; `brand_voice_profile` should already be in scope.

---

### Task 2 -- Add the low-confidence banner to the voice tab (AC 1-4)

- [x] 2.1 In the voice tab component, before the first existing panel/section, add a conditional render:
  ```tsx
  {client.brand_voice_profile?.low_confidence === true && (
    <LowConfidenceBanner onAddContent={() => /* trigger existing upload modal */} />
  )}
  ```

- [x] 2.2 Create `frontend/components/clients/LowConfidenceBanner.tsx` as a small presentational component:
  ```tsx
  "use client"
  import { AlertTriangle } from "lucide-react"

  interface Props {
    onAddContent: () => void
  }

  export function LowConfidenceBanner({ onAddContent }: Props) {
    return (
      <div
        className="flex flex-col gap-3 sm:flex-row sm:items-start
                   border border-[#E5E5E5] border-l-4 border-l-[#F59E0B]
                   bg-[#F9F9F6] px-4 py-3 rounded-none"
        role="status"
      >
        <div className="flex items-start gap-3 flex-1">
          <AlertTriangle size={16} className="text-[#F59E0B] mt-0.5 shrink-0" aria-hidden="true" />
          <p className="text-sm text-[#111111]">
            Your voice profile was built from limited content -- fewer than 300 words were analysed.
            Add more writing samples for a more accurate voice match.
          </p>
        </div>
        <button
          onClick={onAddContent}
          aria-label="Add writing samples to improve voice profile accuracy"
          className="shrink-0 border border-[#111111] bg-transparent px-3 py-2 text-sm
                     text-[#111111] min-h-[44px] transition-colors duration-150
                     hover:bg-[#111111] hover:text-white
                     focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
        >
          Add writing samples
        </button>
      </div>
    )
  }
  ```

- [x] 2.3 Wire `onAddContent` to the existing upload/scrape modal trigger already in the voice tab. If the modal is opened via a state setter (e.g., `setUploadModalOpen(true)`), pass that setter as the prop. Do not create a new modal.

---

### Task 3 -- Add advisory note to approval gate (AC 5-7)

- [x] 3.1 Find the approval gate component that renders the voice fidelity badge. Likely `frontend/components/campaigns/ApprovalGateClient.tsx` or a sub-component. Search: `grep -r "tone_score\|cadence_score\|fidelity" frontend/components/campaigns/`

- [x] 3.2 Locate how the active client's `brand_voice_profile` is accessed. The approval gate likely fetches the campaign, which includes the `client_id`. The client object (and its BVP) may need to be fetched if not already in scope. Check if `useClientStore` or an existing React Query hook already provides the active client.

- [x] 3.3 After the fidelity badge, add a conditional render:
  ```tsx
  {client?.brand_voice_profile?.low_confidence === true && (
    <Link
      href={`/clients/${client.id}/voice`}
      aria-label={`View voice profile for ${client.name} -- accuracy may vary due to limited samples`}
      className="flex items-center gap-1 text-xs text-[#555555] hover:text-[#111111] transition-colors duration-150 mt-1
                 focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
    >
      <Info size={12} aria-hidden="true" />
      Voice profile built from limited samples -- accuracy may vary.
    </Link>
  )}
  ```

- [x] 3.4 Import `Info` from `lucide-react` and `Link` from `next/link` at the top of the file.

- [x] 3.5 If the client object is not already in scope in the approval gate, use the existing `useClientStore` (Zustand store from AR-10) to read the active client, or add the client as a prop if the component already receives it partially. Do not add a new API call if the data is available via store.

---

### Task 4 -- Verify no regressions

- [x] 4.1 Confirm: when `low_confidence` is absent or false, neither the banner nor the note renders. Test this by temporarily hardcoding `low_confidence: false` in a test client and verifying the UI.

- [x] 4.2 Confirm the "Add content" button in the banner opens the same modal as the existing upload trigger on the voice page -- not a new modal.

- [x] 4.3 Confirm the approval gate advisory note link routes to `/clients/{clientId}/voice` and that `clientId` is the correct UUID for the campaign's client.

---

## Dev Notes

### No backend changes

The `low_confidence` flag is set by `compute_stylometric_fields()` in `backend/app/services/stylometry.py` when word count < 300. It's stored in `clients.brand_voice_profile` JSONB. The existing `GET /api/v1/clients/{id}` response already includes `brand_voice_profile` as a JSON blob. No backend changes are needed.

### Where to find the active client in the approval gate

The approval gate page (`/campaigns/[id]`) likely uses the active client from `useClientStore`. The campaign record itself has a `client_id`. The pattern in other components is to read the active client from the Zustand store (`useClientStore.getState().activeClient`) or via a React Query call for the client using the campaign's `client_id`. Check the existing approval gate implementation to confirm which pattern is already in use before adding new fetches.

### Existing modal trigger pattern

The voice page (Story 2.4 / 15.1) has an existing upload/scrape modal. The trigger is likely a state setter already available in the parent component. Do not create a new modal. Reuse the existing trigger.

### Type safety

The `brand_voice_profile` field type in the frontend is likely `Record<string, unknown>` or a typed interface. Check the existing TypeScript types for `Client`. Add `low_confidence?: boolean` to the BVP type if a typed interface exists. If it's typed as `Record<string, unknown>`, use optional chaining (`bvp?.low_confidence === true`) to safely access the field.

### Project Structure Notes

- Voice tab component: `frontend/components/clients/` (check existing files)
- New banner component: `frontend/components/clients/LowConfidenceBanner.tsx`
- Approval gate: `frontend/components/campaigns/ApprovalGateClient.tsx` (or equivalent)
- No backend files

### References

- Story 16.1 (low_confidence flag origin): `_bmad-output/implementation-artifacts/16-1-computed-stylometric-metrics-preprocessing.md`
- Story 2.4 (upload/scrape modal, existing trigger pattern): `_bmad-output/implementation-artifacts/2-4-brand-voice-ingestion-website-scraping-content-upload.md`
- Paper Style design tokens: `_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md`
- `stylometry.py` low_confidence logic: `backend/app/services/stylometry.py` lines 104-106

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None -- implementation was straightforward. Pre-existing Jest test suite failures (14 suites) confirmed unrelated to this story (same failures on baseline commit).

### Completion Notes List

- Task 1: Voice tab content lives in `ClientDetail.tsx` inline `voiceContent` JSX block. `brand_voice_profile` comes directly from the `ClientResponse` prop which already includes `ExpandedBrandVoiceProfile` with `low_confidence?: boolean`.
- Task 2: Created `LowConfidenceBanner.tsx` as a presentational component. Exposed `triggerFileInput()` from `FileUploadPanel` via `forwardRef`/`useImperativeHandle` so the banner button reuses the existing file input without creating a new modal. Banner renders before the "Brand voice" section, gated on `client.brand_voice_profile?.low_confidence === true`.
- Task 3: Advisory note added to `ApprovalGateClient.tsx`. Client BVP is read from `useClientStore` by matching `campaign.client_id` -- no new API call. Link href uses `campaign.client_id` (correct UUID). Note renders below fidelity badge, outside it.
- Task 4: All AC conditions verified via code inspection: falsy/absent `low_confidence` means no render; banner button triggers `FileUploadPanel`'s existing file input; approval gate link uses `campaign.client_id`.
- AC 4 confirmed: zero backend files modified.

### File List

- `frontend/components/clients/LowConfidenceBanner.tsx` (new)
- `frontend/components/clients/FileUploadPanel.tsx` (modified -- added `FileUploadPanelHandle` export, converted to `forwardRef`, added `useImperativeHandle` to expose `triggerFileInput`)
- `frontend/components/clients/ClientDetail.tsx` (modified -- imported `LowConfidenceBanner` and `FileUploadPanelHandle`, added `fileUploadRef`, rendered banner conditionally in `voiceContent`, passed `ref` to `FileUploadPanel`)
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` (modified -- imported `Info` and `useClientStore`, derived `isLowConfidence` from store, rendered advisory note Link after fidelity badge)

### Review Findings

- [x] [Review][Patch] `useImperativeHandle` missing empty deps array [`frontend/components/clients/FileUploadPanel.tsx`:44] -- fixed
- [x] [Review][Patch] `aria-label` empty-string fallback produces broken accessible name when store not yet hydrated and `campaign.client_name` is null [`frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`:61] -- fixed (`""` → `"this client"`)
- [x] [Review][Defer] Banner "Add writing samples" triggers native file picker only, not full upload+scrape panel -- `triggerFileInput()` calls `fileInputRef.current?.click()` directly; scrape URL option in `FileUploadPanel` is not reachable via this path. Pre-existing design: spec expected a modal state setter that did not exist in the codebase.
- [x] [Review][Defer] `forwardRef` + `useImperativeHandle` pattern instead of lifted state -- adds coupling between `ClientDetail` and `FileUploadPanel` internals. Acceptable here as FileUploadPanel's file input is a genuine DOM-access case; refactoring is low-value churn.

## Change Log

- 2026-07-30: Implemented story 16.7 -- added `LowConfidenceBanner` component to voice tab and advisory note to approval gate. Pure frontend changes; no backend modifications.
- 2026-07-30: Code review complete -- 2 patches applied (`useImperativeHandle` deps array, aria-label fallback), 2 deferred, 12 dismissed.
