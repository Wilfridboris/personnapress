---
baseline_commit: 93a54ff15ade15a25d4b64fd5ff88c05c455973e
---

# Story 2.6: Voice Profile Refresh

Status: done

## Story

As an authenticated user,
I want to trigger a fresh voice analysis using my latest website content or new uploads,
So that my Brand Voice Profile stays current as my writing style evolves.

## Acceptance Criteria

1. **Given** a user with an existing Brand Voice Profile visits `/clients/{id}/voice`, **When** the page renders, **Then** the profile fields are displayed with their current values alongside a "Refresh voice profile" secondary button.

2. **Given** a user clicks "Refresh voice profile," **When** the button is clicked, **Then** a confirmation dialog appears: "Re-analyzing [Client Name]'s voice profile will overwrite the current profile. This cannot be undone. Continue?" with a "Re-analyze" primary button and a "Cancel" secondary button.

3. **Given** the user confirms the refresh, **When** `POST /api/v1/clients/{client_id}/ingest` is called, **Then** `clients.brand_voice_profile` is set to null; a new `jobs` record is created with `job_type='ingestion'` and `status='pending'` before dispatch; a new ingestion BackgroundTask is queued; the UI immediately transitions to the ingestion-in-progress state showing "Scraping [url]..." or the questionnaire if no URL is set. **And** the previous Brand Voice Profile is permanently overwritten — there is no version history in v1.

4. **Given** the refreshed ingestion completes, **When** Gemini returns the new profile, **Then** `clients.brand_voice_profile` is updated with the new JSON; the profile review page shows the updated fields pre-populated for confirmation; the user must click "Confirm profile" to finalize.

5. **Given** a client has no website URL and no uploaded files, **When** the user clicks "Refresh voice profile" and confirms, **Then** the ingestion job is created and the UI transitions to show the voice questionnaire (rather than a scraping progress state) — same fallback as the initial setup flow.

6. **Given** a refresh ingestion job fails (Gemini error after 3 retries), **When** the failure is detected, **Then** the `jobs` record is set to `status='failed'`; the UI shows "Voice profile extraction failed. Complete the questionnaire to set up your profile manually." with a CTA to the questionnaire — the `clients.brand_voice_profile` remains null (it was nulled on refresh start, not restored on failure — no version history per spec).

## Tasks / Subtasks

- [x] Task 1: Backend — `POST /api/v1/clients/{client_id}/ingest` endpoint (AC: #3, #5)
  - [x] 1.1 Add `POST /api/v1/clients/{client_id}/ingest` to `backend/app/routers/clients.py`; require auth; verify ownership
  - [x] 1.2 Set `clients.brand_voice_profile = null` via `update_client(session, client_id, brand_voice_profile=None)`
  - [x] 1.3 Create `jobs` record: `job_type='ingestion'`, `status='pending'`, `client_id=client_id` — MUST be persisted to DB before BackgroundTask is dispatched
  - [x] 1.4 If `client.website_url` is set: dispatch `ingest_worker(job_id, client_id)` BackgroundTask (same worker as Story 2.4)
  - [x] 1.5 If no `website_url`: create the job record (so the frontend can poll it) but the worker immediately detects no URL and no files → transitions to questionnaire state (job ends as `failed` with `error_details='no_content_available'` — the frontend uses this to show the questionnaire UI)
  - [x] 1.6 Return HTTP 202 with `{job_id}` — client polls job status

- [x] Task 2: Backend — ingest worker — handle refresh case (AC: #4, #6)
  - [x] 2.1 The `ingest_worker` in `workers/ingest.py` (Story 2.4) already handles the full pipeline; no changes needed to the worker itself — a refresh is identical to an initial ingest
  - [x] 2.2 Verify the worker correctly handles the case where `brand_voice_profile` is null on entry (it was just cleared by the PATCH) — this is normal on first ingest too, so the worker already handles it

- [x] Task 3: Frontend — "Refresh voice profile" button in VoiceSetupPage (AC: #1, #2)
  - [x] 3.1 In `frontend/components/clients/VoiceSetupPage.tsx` (Story 2.5): add "Refresh voice profile" Secondary Button below the "Confirm profile" Primary Button — only shown when `brand_voice_profile` is non-null (the profile exists)
  - [x] 3.2 On click: open the refresh confirmation modal (reuse `ConfirmModal` from Story 2.2)
  - [x] 3.3 Modal content: title "Re-analyze voice profile?"; body "Re-analyzing [Client Name]'s voice profile will overwrite the current profile. This cannot be undone. Continue?"; Primary Button "Re-analyze"; Secondary Button "Cancel"
  - [x] 3.4 Modal Primary Button styles: Ink fill, White text, 4px hard shadow, rounded-none (standard Primary Button per Paper Style — NOT Danger style, because this is not a destructive delete, it's an overwrite with new data)

- [x] Task 4: Frontend — post-confirm state transition (AC: #3, #4, #5)
  - [x] 4.1 On modal confirm: call `POST /api/v1/clients/{id}/ingest`; receive `{job_id}` in response
  - [x] 4.2 Immediately set local component state to `ingestionState: 'in_progress'` — this triggers the ingestion-in-progress UI (JetBrains Mono status messages, polling) without waiting for the next poll cycle
  - [x] 4.3 Use `useJobStatus(jobId)` hook (Story 2.4, Task 8) to poll job; when `status='complete'`: invalidate `["client", clientId]` query to reload updated BVP; set `ingestionState: 'review'` to show the Profile Review with new values pre-populated
  - [x] 4.4 When `status='failed'`: check `error_details`:
    - If `error_details === 'no_content_available'`: set `ingestionState: 'questionnaire'` — show the questionnaire flow
    - Otherwise: set `ingestionState: 'failed'` — show error message + questionnaire CTA
  - [x] 4.5 On new BVP loaded: the Profile Review shows updated fields in editable mode (not confirmed mode) — user must click "Confirm profile" to lock it in (AC #4)

- [x] Task 5: Frontend — edge case: if client had an in-progress job at page load (AC: #3)
  - [x] 5.1 If the Voice Setup page loads and there is already an `in_progress` or `pending` ingestion job: show the polling UI directly (skip the "Refresh" button); do not allow triggering another refresh while one is running
  - [x] 5.2 "Refresh voice profile" button should be disabled (or hidden) while an ingestion job is active

## Dev Notes

### Endpoint is Idempotent

`POST /api/v1/clients/{client_id}/ingest` can be called for both the initial ingest trigger (Story 2.1, when the client has a URL) and for refresh. The behavior is identical:

1. Null out `brand_voice_profile`
2. Create job record
3. Dispatch worker

For Story 2.1, the initial ingest was triggered via the Create Client endpoint. The `/ingest` endpoint introduced here is for user-triggered re-ingestion only (refresh and from the client detail "re-analyze" CTA after a failed first ingest).

### "Refresh" vs "Danger" Button Distinction

This is a critical Paper Style design decision: the "Refresh voice profile" secondary button and the "Re-analyze" confirm button use **Primary style** (not Danger style). The rationale: refreshing the voice profile is not destructive in the sense of permanent loss — the user is actively replacing it with updated data. Danger style is reserved for permanent deletion (Delete client, Reject campaign) where no recovery is possible. Overwriting with new data is a different action category.

```
Danger style → "Delete client" (data gone forever)
Primary style → "Re-analyze" (data replaced with new analysis)
```

### Confirm Dialog — Paper Style Layout

```
┌───────────────────────────────────────┐
│ Re-analyze voice profile?             │ ← Inter 1.125rem Ink
│                                       │
│ Re-analyzing Acme Corp's voice        │ ← Inter 15px Graphite
│ profile will overwrite the current    │
│ profile. This cannot be undone.       │
│ Continue?                             │
│                                       │
│  [      Re-analyze      ]  [ Cancel ] │
│   Primary (Ink+4px shadow)  Secondary │
└───────────────────────────────────────┘
```

### State Machine in VoiceSetupPage

```
brand_voice_profile !== null + no active job
  → 'confirmed' state: show read-only BVP + [Edit] + [Refresh]

brand_voice_profile !== null + editing
  → 'editing' state: show editable BVP + [Confirm profile] + [Refresh]

active ingestion job (pending/in_progress)
  → 'in_progress' state: show JetBrains Mono polling UI; [Refresh] button hidden

ingestion job failed (with content)
  → 'failed' state: show error message + [Complete questionnaire] CTA

ingestion job failed (no_content_available)
  → 'questionnaire' state: show questionnaire wizard

brand_voice_profile === null + no job
  → 'questionnaire' state: show questionnaire wizard
```

### No Partial Failure Handling

If the refresh ingestion fails AFTER nulling out `brand_voice_profile`, the previous profile is gone. This is explicitly accepted per spec: "no profile version history in v1." The user must complete the questionnaire to set up a new profile.

### Job Record for "No Content" Case

When no URL and no files exist, the ingest endpoint still creates a `jobs` record and returns a `job_id`. The worker immediately sets `jobs.status='failed'` with `error_details='no_content_available'`. This allows the frontend to poll the job and get a definitive signal to show the questionnaire — instead of having the frontend make a different decision path before calling the API.

### New Files This Story

None — all changes are to existing files.

Updated files:
```
backend/app/routers/clients.py    ← ADD POST /ingest endpoint
frontend/components/clients/VoiceSetupPage.tsx ← ADD refresh button, modal, state machine
```

### References

- Story spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6]
- FR-11 (Voice Profile Refresh, re-extraction on demand, overwrite confirm, no version history): [Source: _bmad-output/planning-artifacts/epics.md#Functional Requirements]
- NFR-7 (job record before dispatch): [Source: _bmad-output/planning-artifacts/architecture.md]
- Paper Style Button distinction (Primary vs Danger): [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Buttons]
- ConfirmModal (reuse from Story 2.2): [Source: _bmad-output/implementation-artifacts/2-2-edit-delete-client.md]
- useJobStatus hook (reuse from Story 2.4): [Source: _bmad-output/implementation-artifacts/2-4-brand-voice-ingestion-scraping-upload.md]

## Dev Agent Record

### Implementation Notes

- Added `POST /clients/{client_id}/ingest` endpoint to `clients.py`. Nulls BVP, creates ingestion job (committed before BackgroundTask per NFR-7), dispatches `ingest_worker` unconditionally. Worker handles both URL and no-URL cases via its existing no-content detection.
- `error_details` value for no-content case is `"no_content"` (matches existing worker code); frontend checks this string for the questionnaire vs failed state branch.
- `VoiceSetupPage.tsx`: added `ConfirmModal` import, `showRefreshModal`/`refreshing`/`bvp`/`refreshBtnRef` state, `handleRefreshConfirm` (calls `clientsApi.ingest`, transitions view to in-progress), and `onRefresh` prop wired into `ProfileReview`. `refreshDisabled` uses `jobIsActive` derived from the polled job status (AC#5.2). Router.refresh() still used on job completion to reload server state.
- Worker (Task 2): no changes needed — refresh is identical to initial ingest from the worker's perspective.

### Completion Notes

All ACs satisfied:
- AC#1: profile fields shown with Refresh button when BVP exists
- AC#2: confirmation modal with correct copy and Primary (not Danger) confirm button
- AC#3: BVP nulled, job persisted, worker dispatched, HTTP 202 + job_id returned, UI transitions immediately to in-progress
- AC#4: on job completion router.refresh() reloads BVP; profile review shows updated fields; user must click Confirm profile
- AC#5: no-URL path dispatches worker; worker sets error_details='no_content'; frontend branches to questionnaire
- AC#6: other worker failures set view='failed' with questionnaire CTA

## File List

- `backend/app/routers/clients.py` — added `trigger_voice_ingest` endpoint
- `frontend/components/clients/VoiceSetupPage.tsx` — added refresh button, modal, state machine
- `backend/tests/test_voice_refresh.py` — new: 6 unit tests for the ingest endpoint

### Review Findings

- [x] [Review][Patch] P1 (Critical): `setActiveJobId(null)` missing on completed job — infinite `router.refresh()` loop [`VoiceSetupPage.tsx`]
- [x] [Review][Patch] P2 (High): No active-job guard in `POST /ingest` — concurrent workers on double-submit [`clients.py`]
- [x] [Review][Patch] P3 (High): `update_client` return value not checked — orphaned job if client deleted between auth and write [`clients.py`]
- [x] [Review][Patch] P4 (Medium): Silent error in `handleRefreshConfirm` catch — no user feedback on API failure [`VoiceSetupPage.tsx`, `ConfirmModal.tsx`]
- [x] [Review][Patch] P5 (Medium): No rollback safety around `update_client` + `create_job` before commit [`clients.py`]
- [x] [Review][Patch] P6 (Medium): `jobIsActive` falsy before first poll — Refresh button briefly re-enables after submit [`VoiceSetupPage.tsx`]
- [x] [Review][Patch] P7 (Low): `setBvp(null)` called after API call instead of before — old BVP briefly visible [`VoiceSetupPage.tsx`]
- [x] [Review][Defer] D1 (Low): No recovery from stuck in-progress when BVP is null after `router.refresh()` resolves (read-replica/timing edge case) — deferred, pre-existing
- [x] [Review][Defer] D2 (Medium): No rate-limiting/quota guard on ingest endpoint — deferred, architectural concern outside story scope

## Change Log

- 2026-07-01: Story 2.6 implemented — POST /ingest endpoint and VoiceSetupPage refresh flow
- 2026-07-01: Code review fixes applied — P1 through P7 patched; 8 tests passing
