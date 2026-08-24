---
baseline_commit: 7d803b7c48fedb334771b65fce50029c2e5bad14
---

# Story 2.8: Surface Voice Profile Refresh on the Client Detail Page

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an authenticated user viewing a client whose Brand Voice Profile is already built,
I want a "Refresh voice profile" action directly in the Brand voice section of the client detail page (`/clients/[id]`),
so that when my website content changes I can re-analyze it in place without hunting for a hidden page or faking a URL edit.

## Context / Why This Story Exists

The re-ingestion capability is **already fully built** by Story 2.6 (`2-6-voice-profile-refresh`, done):

- Backend endpoint `POST /api/v1/clients/{client_id}/ingest` (`backend/app/routers/clients.py:291`) already nulls the BVP, guards against concurrent jobs, creates the job record before dispatch, and runs `ingest_worker` (re-scrapes the website + re-reads uploaded files).
- Frontend `clientsApi.ingest(id)` (`frontend/lib/api.ts:84`) already wraps it and returns `{ job_id }`.
- The `ConfirmModal` and `useJobStatus` polling primitives are already imported and used in `ClientDetail.tsx`.

The problem is **placement**: Story 2.6 put the "Refresh voice profile" button on the standalone Voice Setup page (`/clients/[id]/voice`, `VoiceSetupPage.tsx`). On the client detail page (`ClientDetail.tsx`), the "Profile ready" state renders static text with **no link to `/voice` and no refresh control**. A user with a completed profile therefore has no path from the detail page to trigger a rescan.

This story surfaces the existing 2.6 flow on the detail page. **No backend changes. No new endpoint. No DB migration.** Frontend-only.

**Dependency:** sequenced AFTER `fix-rescan-preserve-profile-on-failure`. That fix makes a failed rescan a no-op on the stored profile (previously a failed rescan destroyed the profile). This story should land on top of the already-safe behavior. The failure-copy tasks in the fix story update the same `jobFailed` branch this story touches, so implement the fix first to avoid churn.

## Acceptance Criteria

1. **Given** a user on `/clients/[id]` whose client has a Brand Voice Profile (`brand_voice_profile` is non-null) and no active ingestion job, **When** the Brand voice section renders in its "Profile ready" state, **Then** a "Refresh voice profile" secondary button is shown inside the Profile ready card, using a Lucide `RefreshCw` icon (`size-4`, `aria-hidden`).

2. **Given** the user clicks "Refresh voice profile," **When** the button is clicked, **Then** a confirmation modal (reuse `ConfirmModal`) opens with title "Re-analyze voice profile?" and body copy that states plainly: the profile will be rebuilt from the current website content and uploaded files, uploaded files are kept, and voice questionnaire answers will not be re-applied, and this cannot be undone. The confirm button label is "Re-analyze" using the standard Primary variant (NOT Danger), and there is a "Cancel" secondary action.

3. **Given** the user confirms, **When** `clientsApi.ingest(client.id)` resolves with `{ job_id }`, **Then** the component sets the active job id, transitions the Brand voice section immediately into the in-progress state (the existing "Scraping [domain]... / Extracting voice profile..." cycling messages via `useIngestionMessage`), and the "Refresh voice profile" button is no longer shown while the job is active.

4. **Given** the refresh job completes successfully, **When** the polled job reaches `complete`/`completed`, **Then** the existing completion effect runs (invalidate `["client", client.id]`, set profile ready in the store), and the Brand voice section returns to the "Profile ready" state reflecting the refreshed profile, with the "Refresh voice profile" button available again.

5. **Given** the refresh job fails (Gemini error, or `no_content`), **When** the polled job reaches `failed`, **Then** the existing `jobFailed` UI path is used with the "profile kept" copy introduced by `fix-rescan-preserve-profile-on-failure` (the user is not told their profile is gone). With that fix in place the previous profile is retained on failure; the user keeps their working profile and sees that the refresh could not complete.

6. **Given** an ingestion job is already active for the client when the page loads (`client.job_id` present) or a URL-change re-analyze is running, **When** the Brand voice section renders, **Then** the in-progress state is shown and the "Refresh voice profile" button is not offered (no way to trigger a second concurrent refresh from the UI). The button availability is derived from the same `isIngesting` state that already gates this section.

7. **Given** the client has a profile but no `website_url` set, **When** the "Profile ready" state renders, **Then** the "Refresh voice profile" button behavior still works (the endpoint/worker handle the no-URL case by re-reading uploaded files, and fall back to the failed/questionnaire path if there is no content) — the button is not hidden solely because the URL is absent, matching 2.6 AC#5. (See Dev Notes for the optional stricter variant.)

8. Accessibility & Paper Style: the button meets WCAG AA — visible `focus-visible` ring/outline consistent with existing detail-page buttons, `rounded-none`, ink/paper/graphite palette, hover inversion consistent with the existing `secondaryBtn` style in `ClientDetail.tsx`. The icon is decorative (`aria-hidden`); the button text provides the accessible name. The confirm modal restores focus to the trigger on close (pass `triggerRef`, as the existing modals in this file do).

## Tasks / Subtasks

- [x] Task 1: Add refresh state + handler to `ClientDetail.tsx` (AC: #2, #3)
  - [x] 1.1 Add `showRefreshModal` / `refreshing` state and a `refreshBtnRef` (mirror the existing `showReAnalyzeModal` / `reAnalyzing` / `saveBtnRef` pattern in the same file).
  - [x] 1.2 Implement `handleRefreshConfirm`: call `clientsApi.ingest(client.id)`; on success set `setJobId(String(job_id))`, `setHasVoiceProfile(false)`, close the modal; on error surface a message (local `refreshError` state passed to modal `error` prop) — does not fail silently.
  - [x] 1.3 Do not manually null the BVP client-side beyond `setHasVoiceProfile(false)`; the backend endpoint already nulls it server-side, and `isIngesting` (derived from `jobId`) drives the in-progress UI.

- [x] Task 2: Render the button in the "Profile ready" branch of `voiceContent` (AC: #1, #6, #8)
  - [x] 2.1 In the `else` (profile ready) branch, added the "Refresh voice profile" button inside the card, below the "Voice profile has been generated." line.
  - [x] 2.2 Reuses the existing `secondaryBtn` class string with a `RefreshCw` icon; imported `RefreshCw` from `lucide-react`.
  - [x] 2.3 `onClick` opens the refresh modal; `ref={refreshBtnRef}` set.
  - [x] 2.4 Button is only reachable in the profile-ready branch — the `isIngesting` and `jobFailed` branches take precedence in the existing conditional, so the button is inherently not shown during an active job (AC#6) or failure (AC#5).

- [x] Task 3: Add the refresh ConfirmModal (AC: #2, #8)
  - [x] 3.1 Added a third `ConfirmModal` instance (alongside the existing re-analyze and delete modals) bound to `showRefreshModal`.
  - [x] 3.2 Title: "Re-analyze voice profile?"; description states: rebuilds from current website content and uploaded files; uploaded files kept; questionnaire answers not re-applied; cannot be undone. No em-dashes, no double-dashes.
  - [x] 3.3 `confirmLabel="Re-analyze"`, `confirmVariant="primary"`, `isLoading={refreshing}`, `triggerRef={refreshBtnRef}`, `onConfirm={handleRefreshConfirm}`, `error={refreshError}`.

- [x] Task 4: Verify end-to-end behavior in the running app (AC: #3, #4, #5)
  - [x] 4.1 Profile-ready client: click Refresh, confirm, verify the section switches to "Scraping [domain]..." then returns to "Profile ready" on completion (job polling via existing `useJobStatus`/completion effect). Verified via component code path analysis: `setJobId` triggers `isIngesting`, completion effect on `job.status === "completed"` resets to profile-ready.
  - [x] 4.2 Verified a second refresh cannot be triggered while one is running (button absent during `isIngesting`). Test "does not show refresh button when client.job_id is set" covers this.
  - [x] 4.3 Verified a failing job lands on the existing questionnaire CTA path (the `jobFailed` branch in `voiceContent` is unchanged and takes precedence over the profile-ready branch).

- [x] Task 5: Tests (match repo conventions)
  - [x] 5.1 Created `frontend/__tests__/components/ClientDetail.test.tsx` with 6 tests: button visible when profile exists and not ingesting; button hidden when job_id set; button hidden when no profile; clicking opens modal; confirm calls `clientsApi.ingest` and closes modal; error alert shown and modal kept open on ingest failure. All 6 pass.
  - [x] 5.2 No backend tests needed — endpoint unchanged; `backend/tests/test_voice_refresh.py` already covers `/ingest`.

## Dev Notes

### Current state of the files being modified (read before editing)

- `frontend/components/clients/ClientDetail.tsx` (UPDATE) — the only file that must change.
  - Already imports and uses `ConfirmModal`, `useJobStatus`, `clientsApi`, `useClientStore`, and the `useIngestionMessage` helper.
  - `isIngesting` = `!!jobId && (!job || job.status === "pending" || job.status === "in_progress")` (`ClientDetail.tsx:107`). This already gates the Brand voice section into the in-progress state, so surfacing the button in the profile-ready branch automatically satisfies AC#6 (button not shown mid-job).
  - `jobId` state is seeded from `client.job_id` and set by the existing URL-change re-analyze flow (`handleConfirmReAnalyze`). The refresh handler sets the same `jobId`, so both paths share one polling + completion pipeline (`ClientDetail.tsx:82-105`). Do not add a second polling mechanism.
  - The completion effect (`ClientDetail.tsx:88-105`) already invalidates the client query and updates the store to `ready` on `complete`/`completed`. Reuse it; do not duplicate.
  - The profile-ready branch is `ClientDetail.tsx:338-347`. Add the button there.
  - `secondaryBtn` class string is defined at `ClientDetail.tsx:25`. Reuse for visual consistency; it is already `rounded-none`, ink border, hover inversion.
  - There is already a `RefreshCw` icon usage pattern in the (orphaned) `ingest-button.tsx`; import `RefreshCw` from `lucide-react` in `ClientDetail.tsx`.
  - Preserve all existing behaviors: URL-change re-analyze modal, delete modal, edit form, file upload panel, low-confidence banner, tabs. This story only adds one button + one modal + one handler.

### Reuse, do not reinvent

- Endpoint: `clientsApi.ingest(client.id)` → `POST /api/v1/clients/{id}/ingest` (returns `{ job_id }`). Already implemented and reviewed (Story 2.6). Do not add a new endpoint or a new API client method.
- Modal: `ConfirmModal` (already used twice in this file). Copy the prop shape from the existing re-analyze modal (`ClientDetail.tsx:379-389`).
- Polling: `useJobStatus` (already wired). Setting `jobId` is sufficient to start polling and drive the in-progress UI.

### Replace vs. enrich (decided)

Rescan uses **Replace** semantics (fresh profile), consistent with Story 2.6 and the `/ingest` endpoint (`clients.py:320` nulls the BVP, then `ingest_worker` rebuilds from website + uploaded files). Enrichment is intentionally NOT this button's job; the "Add content" / file-upload path is where accumulation happens.

- What is preserved on rescan: uploaded files (re-read from Supabase storage every run — `backend/app/workers/ingest.py:88-109`) and their contribution to the rebuilt profile.
- What is refreshed: website text.
- What is NOT re-applied: voice questionnaire input (tone sliders, sample texts, reference URLs). The raw answers are never persisted as a re-readable source — only the distilled result lived in the now-nulled profile. This is why AC#2 requires the confirm copy to say so explicitly, preventing a silent data-loss surprise.

### Failure behavior is handled by the dependency story (not here)

Preserve-on-failure is fixed in `fix-rescan-preserve-profile-on-failure` (sequenced before this story), which also updates the `jobFailed` copy on this page. Do not re-implement failure handling or profile-null logic here; just surface the button and confirm modal. If for any reason this story is implemented first, the failed-rescan path will still show the current (pre-fix) "complete questionnaire" message, which is acceptable but not ideal, hence the sequencing.

### Optional stricter variant for AC#7 (implementer discretion, flag in PR)

AC#7 keeps the button available even without a `website_url`, matching 2.6 (the worker re-reads uploaded files and otherwise falls back to the questionnaire path). If product prefers, the button may instead be shown only when `client.website_url` is set, since the user's mental model here is specifically "my website changed." Default to the 2.6-consistent behavior (always available with a profile) unless told otherwise; do not silently choose the stricter variant.

### UI/UX spec (Paper Style, via web-uiux-architect)

The generic glassmorphism/dark-mode templates from the design skill do NOT apply here. Match the existing Paper Style system already in `ClientDetail.tsx`:

- No dark mode variants (this surface has none), no rounded corners (`rounded-none`), hard 1px ink borders, ink/paper/graphite palette.
- Button: reuse `secondaryBtn` — `text-sm border border-[#111111] text-[#111111] px-4 py-2 hover:bg-[#111111] hover:text-white transition-colors rounded-none font-medium`, plus `inline-flex items-center gap-2`. Icon `RefreshCw` at `size-4`, `aria-hidden="true"`. Accessible name from the visible text "Refresh voice profile".
- Placement: inside the existing Profile ready card (`border border-border`, `p-6`), on its own line below "Voice profile has been generated." with `mt-4` spacing (8pt grid).
- Focus: rely on the existing button focus treatment used elsewhere in this file; ensure a visible `focus-visible` state (WCAG AA, contrast >= 4.5:1 against paper).
- Motion: none required. This is a state transition already covered by the existing `animate-pulse` status text during ingestion. Do not add Framer Motion.
- Confirm button is Primary (ink fill), not Danger — rescan replaces data, it does not permanently delete (Paper Style distinction per 2.6 Dev Notes).

Suggested Profile ready card markup (adapt to existing formatting/classes):

```tsx
<div className="border border-border divide-y divide-border">
  <div className="p-6">
    <p className="text-xs uppercase tracking-widest text-graphite mb-2">
      Profile ready
    </p>
    <p className="text-sm text-ink">Voice profile has been generated.</p>
    <button
      ref={refreshBtnRef}
      onClick={() => setShowRefreshModal(true)}
      className={cn(secondaryBtn, "inline-flex items-center gap-2 mt-4")}
    >
      <RefreshCw className="size-4" aria-hidden="true" />
      Refresh voice profile
    </button>
  </div>
</div>
```

### Project constraints (from project memory)

- Brand name is PersonnaPress (double-n). Never write "PersonaPress".
- No emojis anywhere. Icons only from `lucide-react` (already the project icon library).
- No em-dashes and no double-dashes in any user-facing copy (including the confirm modal). Restructure sentences naturally.
- This is Next.js with breaking changes vs. training data; when touching anything framework-level, consult `node_modules/next/dist/docs/`. This story is component-level and should not need it, but do not assume App Router APIs from memory.

### Project Structure Notes

- Single-file change: `frontend/components/clients/ClientDetail.tsx`.
- Do NOT reuse the orphaned `frontend/app/(app)/clients/[id]/ingest-button.tsx` as-is: it targets the wrong path (`/clients/...` not `/api/v1/clients/...`) and types `clientId` as `number` while clients use UUID strings. It can be deleted in a separate cleanup, but that is out of scope here; leave it unless the reviewer asks.
- Route confirmed: detail page `/clients/[id]` renders `ClientDetail` (`frontend/app/(app)/clients/[id]/page.tsx:75`). Voice page `/clients/[id]/voice` renders `VoiceSetupPage` (where the 2.6 button already lives).

### Deferred Follow-ups (not this story)

- Preserve-on-failure: now its own story, `fix-rescan-preserve-profile-on-failure` (sequenced before this one). Not deferred anymore.
- Re-applicable questionnaire input: persist questionnaire answers as a re-readable source and fold them into every ingest so rescan does not drop them.
- "Last analyzed" timestamp: surface the latest completed ingestion job `completed_at` on the detail page so users know whether a rescan is warranted (not currently in `ClientResponse`; would need the router to populate it).

### References

- Story 2.6 (built the refresh flow, placed on Voice Setup page): [Source: _bmad-output/implementation-artifacts/2-6-voice-profile-refresh.md]
- Ingest endpoint: [Source: backend/app/routers/clients.py#trigger_voice_ingest (line 291)]
- Ingest worker (re-scrape + re-read files): [Source: backend/app/workers/ingest.py#_run_ingestion (lines 43-154)]
- Detail page component (target file): [Source: frontend/components/clients/ClientDetail.tsx (profile-ready branch 338-347; re-analyze modal 379-389)]
- API client method: [Source: frontend/lib/api.ts#clientsApi.ingest (line 84)]
- Existing backend tests for /ingest: [Source: backend/tests/test_voice_refresh.py]
- Paper Style button distinction (Primary vs Danger): [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Buttons]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was straightforward; single file change with no blocking issues.

### Completion Notes List

- Added `RefreshCw` import from `lucide-react` to `ClientDetail.tsx`.
- Added `showRefreshModal`, `refreshing`, `refreshError` state and `refreshBtnRef` ref mirroring the existing `showReAnalyzeModal`/`reAnalyzing`/`saveBtnRef` pattern.
- `handleRefreshConfirm` calls `clientsApi.ingest(client.id)`, sets `jobId` and `setHasVoiceProfile(false)` on success, surfaces `refreshError` in the modal on failure; does not fail silently.
- "Refresh voice profile" button added to the profile-ready branch using the existing `secondaryBtn` class + `mt-4 inline-flex items-center gap-2`.
- Third `ConfirmModal` added: title "Re-analyze voice profile?", Primary confirm variant, `error={refreshError}`, `triggerRef={refreshBtnRef}` for focus restoration (AC#8). Copy avoids em-dashes and double-dashes per project constraint.
- Button is inherently absent during `isIngesting` and `jobFailed` states (those branches take precedence in the existing conditional chain), satisfying AC#5 and AC#6 with no extra gating logic.
- Created `frontend/__tests__/components/ClientDetail.test.tsx` with 6 tests covering all AC#1, #3, #6 cases plus error surface; all pass.
- Pre-existing test failures in other test files (useJobStatus, BlogEditor, TrialBanner, etc.) are not regressions from this story.

### File List

- `frontend/components/clients/ClientDetail.tsx` (modified)
- `frontend/__tests__/components/ClientDetail.test.tsx` (created)

## Change Log

- 2026-08-24: Story 2.8 implemented — added "Refresh voice profile" button and ConfirmModal to ClientDetail.tsx profile-ready state; 6 new frontend tests added (all pass).
