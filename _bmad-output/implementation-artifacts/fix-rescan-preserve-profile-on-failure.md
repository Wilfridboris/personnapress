---
baseline_commit: acf59e1ce0c11789e342eec78051c278dee1bade
---

# Story: Preserve Voice Profile When a Rescan Fails

Status: done

<!-- Bugfix / safety story. Sequenced BEFORE 2-8-client-detail-voice-refresh-button so the refresh button ships on already-safe behavior. -->

## Story

As an authenticated user who triggers a voice profile refresh (rescan),
I want my existing Brand Voice Profile to be kept if the rescan fails,
so that a failed re-analysis of my website does not destroy the working profile I already had.

## Problem

`POST /api/v1/clients/{client_id}/ingest` nulls the Brand Voice Profile **before** the worker runs (`backend/app/routers/clients.py:320`, `update_client(db, client_id, brand_voice_profile=None)`), then dispatches `ingest_worker`. If the worker then fails (site unreachable, `no_content`, or Gemini errors after 3 retries — `backend/app/workers/ingest.py:117-147`), nothing is written back. The old profile is already gone.

Net effect: a failed rescan leaves the client with **no** voice profile and forces a from-scratch questionnaire, even though the user only wanted to re-read updated website copy.

This was an explicitly accepted v1 tradeoff in Story 2.6 (AC#6 / "No Partial Failure Handling"; deferred item D1). This story removes that tradeoff.

## Goal / Approach

Only overwrite the profile on **success**. Leave the existing profile untouched until a new one is fully extracted, so a failed rescan is a no-op on the stored profile.

Preserve **Replace** semantics (a successful rescan still fully replaces the old profile; it does NOT enrich/merge). This matches current `/ingest` behavior and the decision recorded in Story 2.8.

## Acceptance Criteria

1. **Given** a client with an existing Brand Voice Profile, **When** `POST /api/v1/clients/{client_id}/ingest` is called, **Then** `clients.brand_voice_profile` is NOT nulled by the endpoint. The endpoint still verifies the client exists and is owned by the caller, still guards against concurrent jobs, still creates the job record (committed before dispatch), and still dispatches `ingest_worker`, returning HTTP 202 with `{job_id}`.

2. **Given** a rescan job runs to successful completion, **When** the new profile is extracted, **Then** `clients.brand_voice_profile` is fully replaced with the newly extracted profile (Replace semantics, no merge/enrich with the prior profile), identical in shape to an initial ingest.

3. **Given** a rescan job fails for any reason (scraping yields nothing / `no_content`, Gemini fails after retries, or any unhandled worker error), **When** the failure is recorded, **Then** `clients.brand_voice_profile` retains its previous value (the profile that existed before the rescan). No partial or empty profile is written.

4. **Given** the enrichment-merge path exists in `extract_voice_profile` (Story 16.2), **When** the ingest worker runs, **Then** the rescan does NOT accidentally trigger enrichment against the still-present old profile. The ingest worker performs a clean Replace. (The questionnaire worker's behavior is unchanged.)

5. **Given** a rescan fails, **When** the frontend reflects the outcome, **Then** the user is not told their profile is gone. The failure messaging on both `ClientDetail.tsx` and `VoiceSetupPage.tsx` reflects that the previous profile was kept (see Task 3). No silent data-loss wording remains.

6. Existing behavior preserved: initial ingest (client with a URL, no prior profile) produces the same profile as before; concurrent-job guard, commit-before-dispatch (NFR-7), auth/ownership guards, and the no-URL/no-content questionnaire fallback all still work.

## Tasks / Subtasks

- [x] Task 1: Backend endpoint — stop nulling the BVP (AC: #1, #6)
  - [x] 1.1 In `backend/app/routers/clients.py` `trigger_voice_ingest`, remove the `update_client(db, client_id, brand_voice_profile=None)` call (and its `updated`/P3 branch at ~lines 319-322).
  - [x] 1.2 Keep the existing existence + ownership checks (the function already fetched `client` and checked `None`/owner at ~lines 308-312). Ensure the client-existence guarantee that the removed null-write used to provide is still covered by those earlier checks; no new race is introduced beyond what already exists for job creation.
  - [x] 1.3 Leave intact: active-job guard, `create_job` + `db.commit()` before `background_tasks.add_task(...)`, HTTP 202 `{job_id}` return.

- [x] Task 2: Backend worker — Replace without merge, write only on success (AC: #2, #3, #4)
  - [x] 2.1 In `backend/app/workers/ingest.py` `_run_ingestion`, change the extraction call from `extract_voice_profile(combined_text, client.id, session=db)` (line ~129) to `session=None`. With `session=None`, `extract_voice_profile` does not read the existing BVP (so no enrichment-merge — preserves Replace) and does not write mid-pipeline; it returns the new profile dict.
  - [x] 2.2 Confirm the worker still persists the returned profile on success at the end of the pipeline (`client.brand_voice_profile = voice_profile` + commit, currently line ~150-153). This write now happens only after successful extraction, so failures never overwrite the prior profile.
  - [x] 2.3 Do NOT change the questionnaire worker's `extract_voice_profile(..., session=db)` call (line ~289). It relies on the internal write and its own semantics; it is out of scope.
  - [x] 2.4 Verify the `no_content` early-exit path (lines ~117-122) no longer disturbs the BVP (it already does not write BVP; with Task 1 the profile is simply retained).

- [x] Task 3: Frontend — failure copy reflects "profile kept" (AC: #5)
  - [x] 3.1 `frontend/components/clients/ClientDetail.tsx`: in the `jobFailed` branch of the Brand voice section, update copy so a failed rescan does not imply the profile is lost. When the client still has a profile, message should convey that the previous profile was kept and the refresh could not complete, keeping the questionnaire CTA as a secondary option. Do not strand a user who still has a valid profile.
  - [x] 3.2 `frontend/components/clients/VoiceSetupPage.tsx`: with the BVP no longer server-nulled, a failed rescan leaves `client.brand_voice_profile` present, so `initialView()` resolves to `review` (line ~311) rather than `failed`. Add a non-blocking failure notice on that path (the rescan failed, previous profile kept) so the failure is not silent. Keep the existing `no_content` → questionnaire behavior for clients that genuinely have no profile.
  - [x] 3.3 No changes to the success path on either page (existing completion handling already reloads the new profile).

- [x] Task 4: Tests (AC: #1, #2, #3, #4, #6)
  - [x] 4.1 `backend/tests/test_voice_refresh.py`: update `test_ingest_nulls_bvp_creates_job_dispatches_worker` — remove the `mock_update.assert_awaited_once_with(db, client.id, brand_voice_profile=None)` assertion and the null-write expectation; assert instead that the endpoint does not null the BVP and still creates the job + dispatches the worker + returns `{job_id}`.
  - [x] 4.2 `backend/tests/test_voice_refresh.py`: rework or remove `test_ingest_returns_404_when_update_client_returns_none` (P3) since the endpoint no longer calls `update_client` to null; keep an equivalent guard test if the existence check remains (e.g. `get_client` returning None → 404, which is already covered by `test_ingest_returns_404_when_client_not_found`).
  - [x] 4.3 `backend/tests/test_ingest_worker.py`: add a test that a worker failure (e.g. `VoiceExtractionError` or `no_content`) does NOT overwrite an existing `brand_voice_profile` — the pre-existing profile is retained after the worker runs.
  - [x] 4.4 `backend/tests/test_ingest_worker.py`: add/adjust a test asserting the ingest worker calls `extract_voice_profile` with `session=None` (or otherwise asserts Replace-not-merge: given a non-null prior BVP, a successful rescan yields the freshly extracted profile, not a union of old + new array fields).
  - [x] 4.5 Run the existing ingestion/worker suites to confirm no regression to initial ingest or questionnaire flows.

## Dev Notes

### Why `session=None` is the correct lever (do not "just remove the null")

`extract_voice_profile(combined_text, client_id, session=...)` (`backend/app/services/ingestion.py:240`) branches on `session`:
- With a session, it **reads the existing BVP** (`ingestion.py:278-294`) and, if one is present, runs the Story 16.2 enrichment-merge that unions `banned_jargon` / `signature_phrases` / `voice_anchor_sentences` and regenerates `voice_brief` (`ingestion.py:301-317`), then **writes** the result via `update_client` (`ingestion.py:319-320`).
- With `session=None`, it does neither: no existing-BVP read, no merge, no write. It just returns the freshly extracted dict.

Today this merge never fires through `/ingest` only because the endpoint nulls the BVP first (so the read finds nothing). If Task 1 removes the null but the worker keeps `session=db`, the read will find the old profile and the rescan will silently become an **Enrich** instead of a **Replace** — a behavior change we do not want. Passing `session=None` in the ingest worker keeps a clean Replace while the worker's own end-of-pipeline write (`ingest.py:150`) persists the new profile only on success.

For initial ingest (no prior profile), `session=None` vs `session=db` produce identical output; the only difference is which line performs the write, and the worker already writes at line ~150. So this change is behavior-neutral for initial ingest.

### Files to touch

```
backend/app/routers/clients.py        ← remove upfront BVP null in trigger_voice_ingest
backend/app/workers/ingest.py         ← ingest_worker: extract_voice_profile(..., session=None); write only on success (already at ~line 150)
frontend/components/clients/ClientDetail.tsx    ← jobFailed copy: profile kept
frontend/components/clients/VoiceSetupPage.tsx  ← failed-rescan notice (BVP now retained)
backend/tests/test_voice_refresh.py   ← update null-BVP + P3 assertions
backend/tests/test_ingest_worker.py   ← preserve-on-failure + Replace-not-merge tests
```

Do NOT change: `questionnaire_worker` / `_run_questionnaire` (its `extract_voice_profile(..., session=db)` call and merge behavior are intentional and out of scope).

### Interaction with Story 2.8

Story `2-8-client-detail-voice-refresh-button` surfaces the refresh button on the client detail page. This fix should land first so that button (and the existing Voice Setup page button) operate on preserve-on-failure behavior. 2.8's confirm-modal copy says the action "cannot be undone" (referring to the successful overwrite of the profile with new data); that remains accurate. After this fix, a *failed* rescan is a no-op on the stored profile, which only improves the user outcome and does not contradict 2.8's copy.

### Project constraints (from project memory)

- Brand name PersonnaPress (double-n). No emojis. Icons only from `lucide-react`.
- No em-dashes and no double-dashes in any user-facing copy. Restructure naturally.
- Next.js here has breaking changes vs. training data; consult `node_modules/next/dist/docs/` for anything framework-level. These frontend changes are copy/state only and should not need it.

### Deferred (still not in scope)

- Full profile version history / rollback UI.
- Re-applicable questionnaire input on rescan (persisting raw questionnaire answers as a re-readable source).
- "Last analyzed" timestamp on the detail page.

### References

- Endpoint that nulls BVP upfront: [Source: backend/app/routers/clients.py#trigger_voice_ingest (line 291, null at 320)]
- Ingest worker pipeline + failure paths: [Source: backend/app/workers/ingest.py#_run_ingestion (lines 43-154)]
- extract_voice_profile session branching + enrichment-merge: [Source: backend/app/services/ingestion.py#extract_voice_profile (lines 240-348; merge 278-317)]
- Accepted-tradeoff origin: [Source: _bmad-output/implementation-artifacts/2-6-voice-profile-refresh.md (AC#6, "No Partial Failure Handling", D1)]
- Existing endpoint tests: [Source: backend/tests/test_voice_refresh.py]
- Dependent surfacing story: [Source: _bmad-output/implementation-artifacts/2-8-client-detail-voice-refresh-button.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Added `spacy` and `textstat` to conftest stubs — these were missing since stylometry was added after the worker tests were originally written, causing collection failures.

### Completion Notes List

- **Task 1**: Removed `update_client(db, client_id, brand_voice_profile=None)` call and associated P3 guard from `trigger_voice_ingest`. Existence check at lines 308-312 remains; the only removed guarantee was the race-condition check on the null write, which was already a TOCTOU window anyway. Docstring updated to drop the "nulls BVP" description.
- **Task 2**: Changed `extract_voice_profile(..., session=db)` to `session=None` in `_run_ingestion` (ingest.py line ~129). This prevents the Story 16.2 enrichment-merge from silently firing on the preserved BVP, keeping Replace semantics. Success write at line ~150 unchanged — profile is only persisted on success. Questionnaire worker path (`session=db`) left untouched.
- **Task 3.1**: `ClientDetail.tsx` `jobFailed` branch now branches on `hasVoiceProfile`: kept profile → "The refresh could not be completed. Your previous profile has been kept..."; no profile → original "Couldn't extract content..." copy.
- **Task 3.2**: `VoiceSetupPage.tsx` changes: (a) removed `setBvp(null)` from `handleRefreshConfirm` (server no longer nulls it); (b) added `rescanFailed` state initialized to false; (c) job failure handler now checks `bvpRef.current` — if profile exists, stays on "review" and sets `rescanFailed=true`; (d) non-blocking notice rendered above `ExpandedProfileReview` when `rescanFailed && view==="review"`; (e) `setRescanFailed(false)` on new refresh start.
- **Task 4**: Renamed `test_ingest_nulls_bvp_creates_job_dispatches_worker` to `test_ingest_preserves_bvp_creates_job_dispatches_worker`; removed `update_client` patch and asserts `mock_update.assert_not_awaited()`. Removed P3 test (`test_ingest_returns_404_when_update_client_returns_none`) — covered by existing `test_ingest_returns_404_when_client_not_found`. Added two new worker tests: `test_ingest_worker_failure_preserves_existing_bvp` (VoiceExtractionError path) and `test_ingest_worker_calls_extract_with_session_none` (Replace semantics assertion). Cleaned dead `update_client` patches from 3 other tests. 18 tests pass.

### File List

- `backend/app/routers/clients.py`
- `backend/app/workers/ingest.py`
- `frontend/components/clients/ClientDetail.tsx`
- `frontend/components/clients/VoiceSetupPage.tsx`
- `backend/tests/test_voice_refresh.py`
- `backend/tests/test_ingest_worker.py`
- `backend/tests/conftest.py`

### Review Findings

- [x] [Review][Patch] ConfirmModal description implies merge/enrich, contradicts AC#4 Replace semantics [frontend/components/clients/VoiceSetupPage.tsx:446]
- [x] [Review][Patch] Test assertion for session=None passes vacuously if arg becomes positional [backend/tests/test_ingest_worker.py:437]
- [x] [Review][Patch] no_content early-exit with pre-existing BVP has no test — AC#3 lists it explicitly [backend/tests/test_ingest_worker.py]
- [x] [Review][Defer] P3 guard removed — client deleted between auth and create_job returns 500 instead of 404 [backend/app/routers/clients.py:318] — deferred, spec task 1.2 explicitly accepted this TOCTOU window

### Change Log

- 2026-08-25: Implemented preserve-on-failure behavior for voice profile rescans. Removed upfront BVP null from endpoint, switched ingest worker to session=None for Replace semantics, updated frontend failure copy and added non-blocking notice on VoiceSetupPage, updated and added 2 new worker tests.
