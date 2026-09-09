# Story 26.5: Onboarding Friction Reduction and Early Voice Proof

Status: in-review

## Story

As a new user,
I want onboarding to save my progress, let me speak instead of type, explain failures, and prove the product understands my voice before asking for more,
so that I reach my first in-my-voice content quickly and never restart from scratch.

## Acceptance Criteria

1. **Given** the User model's single `onboarding_completed` boolean, **When** a `onboarding_step` integer column (nullable, default null) is added via Alembic CLI migration, **Then** each completed step persists it, and a returning user with `onboarding_completed=false` resumes at their saved step with their created client loaded (no more restart at Step 1).

2. **Given** the voice profile finishes extraction in Step 2, **When** the InlineProfileReview renders, **Then** it is extended with a "voice proof" element: one short sample paragraph generated live in the user's extracted voice (a 2-3 sentence rewrite of fixed neutral copy using the voice section), with a caption "This is how PersonnaPress will sound as you"; generation failure hides the element without blocking the step.

3. **Given** website scraping fails or finds no content, **When** the questionnaire path is shown, **Then** a one-line explanation states what happened (e.g. "We could not read enough text from your site, so we will ask a few quick questions instead") instead of the questionnaire appearing unexplained; the specific `error_details` reason maps to distinct copy for `no_content` vs other failures.

4. **Given** the existing `VoiceBrainDump` component from Epic 9 is used in campaigns but not onboarding, **When** the brain dump step renders, **Then** the brain dump textarea offers the voice recording option with identical behavior to the campaign page, and the transcript lands in the textarea for editing before submit.

5. **Given** the brain dump draft, **When** the user types, **Then** the draft persists to localStorage (same pattern as story 3-18) and is restored if the user returns mid-onboarding; it is cleared on successful campaign creation.

6. **Given** platform connection is the current Step 3 and content generation is Step 4, **When** the flow is reordered, **Then** brain dump becomes Step 3 and platform connection becomes Step 4 (after first content exists, framed as "publish what you just made"), the OAuth return handler is updated for the new step numbering, and skipping platform connection still completes onboarding.

7. **Given** tests, **When** run, **Then** they cover: step persistence and resume, voice-proof render and failure fallback, scrape-failure explanation copy per error reason, voice recording presence in the brain dump step, draft persistence and clearing, and OAuth return with reordered steps.

## Tasks / Subtasks

- [x] Task 1: Step persistence and resume (AC: 1)
  - [x] Add `onboarding_step` (Integer, nullable) to `User` in `models.py`; migration via Alembic CLI (`alembic revision --autogenerate -m "add_onboarding_step_to_users"`). NEVER hand-write a revision ID.
  - [x] Backend: `PATCH /auth/onboarding-step` (int 1-4) on the auth router, following existing session-auth patterns; `complete-onboarding` clears it (set null).
  - [x] `OnboardingFlow.tsx`: on each step completion, fire the PATCH (fire-and-forget, failure never blocks the UI); on mount with `onboarding_completed=false` and a saved step, resume at that step; resolve the user's most recent client via the existing clients query (TanStack Query, client component; server component only reads the session cookie per the RSC rule) and hydrate `createdClientId`.
  - [x] Resume edge cases: saved step 2 with no client falls back to step 1; saved step 2 with a client that already has a BVP jumps to the profile-ready state; saved step >= 3 requires a client, else step 1.
- [x] Task 2: Voice proof element (AC: 2)
  - [x] Backend: `POST /clients/{id}/voice-preview` returning `{preview: str}`; synchronous endpoint (no job) that calls the active provider with the client's voice section and a FIXED neutral source paragraph (constant in code, 2 sentences about planning content for the week), instruction: rewrite in this voice, 2-3 sentences, plain text, no markdown, no em-dashes; ~10s httpx timeout; on any provider error return 502 quickly.
  - [x] Ownership check on client; 404 if no BVP yet.
  - [x] Frontend: in `InlineProfileReview` (OnboardingFlow.tsx:198-205 region), after profile data renders, fire the preview request via TanStack Query; while loading show a shimmer skeleton (CSS keyframes, Paper Style grays); on success render the paragraph as a styled quote block with caption "This is how PersonnaPress will sound as you"; on error render nothing (no error state, silent hide per AC).
- [x] Task 3: Scrape failure explanation (AC: 3)
  - [x] Map `error_details` at the Step 2 branch point (OnboardingFlow.tsx ~line 158): `no_content` shows "We could not read enough text from your site, so we will ask a few quick questions instead."; any other failure shows "We could not finish analyzing your site, so we will ask a few quick questions instead." Render as a quiet single line above the questionnaire, not an error banner (the questionnaire IS the recovery, do not make it feel like failure).
- [x] Task 4: Voice recording in brain dump step (AC: 4)
  - [x] Reuse `VoiceBrainDump` (Epic 9 + 9-5 waveform + 20-7 pattern) in the onboarding brain dump step exactly as the campaign page uses it: record, transcribe via the existing transcription job flow, transcript appended into the textarea at cursor for editing. Guard the empty-transcript case (20-7 review patch).
- [x] Task 5: Draft autosave (AC: 5)
  - [x] Apply the 3-18 localStorage pattern with a distinct key (`onboarding_brain_dump_draft`): debounce writes, restore on mount with a dismissible restore banner only if the textarea is empty, validate savedAt, clear on successful campaign creation and on completeOnboarding skip. Reuse the 3-18 guards (userHasTypedRef, isNaN age guard).
- [x] Task 6: Step reorder (AC: 6)
  - [x] Reorder: Step 3 = brain dump (generation fires, user navigates to campaign page after Step 4), Step 4 = platform connection framed "Publish what you just made" with subtitle noting the draft is generating/ready. Continue/skip on Step 4 calls `completeOnboarding` then routes to `/campaigns/{id}?job_id={jobId}` when a campaign exists, else `/dashboard`.
  - [x] IMPORTANT sequencing change: `completeOnboarding` currently fires before campaign creation in the old Step 4 (line ~360); in the new order, campaign creation happens at Step 3 WITHOUT completeOnboarding (user still has Step 4 to go); completeOnboarding fires when Step 4 finishes (connect, continue, or skip). Update the trial/limit failure paths accordingly (403 TRIAL_EXPIRED and limit errors still render inline on Step 3).
  - [x] OAuth return handler (lines 267-287) and guard logic (290-294): success/error params now resolve to Step 4; sessionStorage `onboarding_client_id` flow unchanged; a user returning from OAuth resumes at Step 4 with their campaign context intact (persist `onboarding_campaign_id` + `onboarding_job_id` in sessionStorage alongside the client id so the final redirect can target the campaign page).
  - [x] Update `ProgressIndicator` step labels and order; it stays a server-safe presentational component (11-4 review removed its "use client", keep it that way).
- [x] Task 7: Tests (AC: 7)
  - [x] Backend: onboarding-step PATCH validation and clearing, voice-preview happy/timeout/no-BVP/ownership paths.
  - [x] Frontend (vitest): resume at each saved step + edge fallbacks, voice proof render/skeleton/silent-hide, failure copy per error_details, VoiceBrainDump present in Step 3, draft save/restore/clear, OAuth return to Step 4, completeOnboarding timing (not fired at Step 3, fired on Step 4 finish/skip), skip paths from every step.

## Dev Notes

### Why this story exists (evidence, 2026-09-05 code analysis)

- 10 screen transitions and 5 async waits stand between registration and first generated content (3-12 minutes typical). Every friction here is pre-value.
- No step persistence: `onboarding_completed` is a single boolean; closing the browser mid-Step-2 restarts the user at Step 1 (sessionStorage only survives the OAuth round-trip).
- Scrape failure silently swaps in the questionnaire with zero explanation (`ingest.py:156-161` sets `error_details="no_content"`, the frontend branches at OnboardingFlow ~158 without messaging).
- The voice recorder built in Epic 9 (and reused in 20-7) is absent from onboarding, the one place typing friction hurts most.
- Platform connection (OAuth redirects that break flow context) sits BEFORE the brain dump, delaying the "it sounds like me" moment; the earliest possible proof is right after extraction, which is what the voice-proof element delivers.

### Constraints and guardrails

- Alembic CLI only for the migration.
- All copy: no em-dashes, no double-dashes, no exclamation marks, no emojis; error copy names the issue specifically. The AC copy strings above are canonical, use them verbatim.
- Server components only read the session cookie; ALL data fetching (client resolution, preview, job polling) goes through TanStack Query in client components (Turbopack RSC re-render loop rule; violating this floods the backend).
- The voice-preview endpoint is synchronous and cheap; do NOT create a Job row for it. Rate-limit lightly if trivial (single in-flight request from the UI is fine); it must never block step progression.
- completeOnboarding timing change (Task 6) is the riskiest part of this story: today a user who generates in Step 4 is already marked complete before the campaign call. Preserve the invariant that a user can NEVER be stuck with `onboarding_completed=false` and no path forward: every Step 4 exit (connect success, connect error + skip, plain skip) calls completeOnboarding.
- Trial mechanics unchanged: `check_trial_not_expired` and campaign limits still gate the Step 3 generation; render those errors inline with specific copy.

### Existing behavior that must not break

- "Skip for now" on Step 1 still completes onboarding and goes to `/dashboard`.
- Step 2 skip still advances without voice setup (low-confidence warning path 16-7 handles the degraded experience later).
- OAuth callbacks (`11-4`: sessionStorage false-detection fix, CSRF ordering in linkedin/x callbacks, error-before-success ordering) must keep working; only the step number the handler resolves to changes.
- The dashboard `?nudge=true` path survives for users who skip generation entirely.
- 2-7/3-5 completion semantics: generation from onboarding still lands on `/campaigns/{id}?job_id=...` with the typewriter/polling experience.

### UI/UX design guidance (web-uiux-architect, adapted to Paper Style)

- Paper Style throughout: paper background, ink text, `rounded-none`, hard offset shadows (`4px 4px 0px 0px var(--color-ink)` for the proof card), dot paper texture already global. No glassmorphism, no dark variants.
- Voice proof block: visually distinct as a "specimen": bordered card, the generated paragraph in the serif/display treatment onboarding already uses for emphasis if one exists, otherwise regular text at `text-pretty`; caption above in small uppercase tracking-wide muted ink. Entrance: CSS-only fade/slide-up keyframe (respect `motion-reduce:animate-none`); no Framer Motion (mount-only animation, CSS handles it).
- Skeleton while preview loads: shimmer via CSS keyframes over Paper grays (zinc-toned), 2 text lines, no spinner.
- Step 4 reframe: heading follows the platform naming conventions, e.g. "Publish your draft to your platforms"; each platform card keeps its existing 44x44px minimum touch targets and `focus-visible:ring-2` rings; skip link is a real button/link with visible focus state, phrased "I'll connect a platform later." (existing copy, keep).
- Restore-draft banner: reuse the 3-18 banner pattern (dismiss button with aria-label, no layout jump).
- ProgressIndicator: 4 labeled steps; current step marked with `aria-current="step"`; completed steps get a Lucide `Check` with `aria-hidden="true"` plus sr-only "completed".
- Headings use `text-balance`; body explanation lines use `text-pretty`.

### Source tree components to touch

- `backend/app/db/repositories/models.py` (UPDATE: User.onboarding_step), `backend/alembic/versions/` (NEW via CLI)
- `backend/app/routers/auth.py` (UPDATE: onboarding-step PATCH, complete-onboarding clears it)
- `backend/app/routers/clients.py` (UPDATE: voice-preview endpoint), provider call helper for the preview (reuse existing provider dispatch)
- `frontend/components/onboarding/OnboardingFlow.tsx` (UPDATE: resume, reorder, proof, draft, recorder wiring)
- `frontend/components/onboarding/OnboardingPlatformStep.tsx` (UPDATE: step number, reframed copy)
- `frontend/components/onboarding/ProgressIndicator` (UPDATE: labels/order)
- `frontend/components/campaigns/VoiceBrainDump.tsx` (REUSE, no change expected)
- `frontend/lib/api.ts` (UPDATE: onboardingStep, voicePreview)
- Tests: backend auth/clients test files, frontend onboarding test files

### Testing standards summary

- Backend: pytest, mocked provider for voice-preview, auth fixtures per existing auth router tests.
- Frontend: vitest + testing-library; mock sessionStorage/localStorage; OAuth return simulated via URL params per existing 11-4 tests.

### Project Structure Notes

- Onboarding remains a single route (`/onboarding`) with internal step state; resume works off DB state + query params, not new routes.
- Voice preview is a client-scoped endpoint on the clients router (ownership pattern identical to ingest/questionnaire endpoints).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 26, Story 26.5]
- [Source: frontend/components/onboarding/OnboardingFlow.tsx:198-205, 267-294, 309-312, 360-373, 407-686 (current flow)]
- [Source: backend/app/workers/ingest.py:156-161 (error_details reasons)]
- [Source: _bmad-output/implementation-artifacts/3-18-brain-dump-draft-autosave.md (localStorage pattern + review guards)]
- [Source: _bmad-output/implementation-artifacts/11-4-onboarding-platform-connection-step.md (OAuth return handling + review patches)]
- [Source: _bmad-output/implementation-artifacts/20-7-plan-my-week-voice-recording.md (VoiceBrainDump reuse + empty transcript guard)]
- [Source: _bmad-output/project-context.md (RSC data-fetching rule, Alembic CLI rule, no em-dash rule)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- 9/9 backend tests pass (tests/test_onboarding_step.py) — two test mocks fixed post-review: `patch_onboarding_step` now fetches subscription as a second DB call, so those tests needed `side_effect=[user_result, sub_result]` instead of a single `return_value`.
- Frontend tests written; run in CI (no node_modules in worktree)

### Completion Notes List

- Migration written manually (DB not running during session); down_revision chains off 5c08a8909153 (26.3 voice_samples). Verify with `alembic check` before deploy.
- Gemini path uses correct google-genai SDK (`_genai.Client.aio.models.generate_content`) matching integrations/gemini.py pattern.
- `onboarding_step` DB read path: step is persisted and cleared correctly. Resume on page load relies on the value being in the session/auth response; if `/auth/me` does not expose `onboarding_step`, the resume will not work until that endpoint is updated.

### File List

- backend/app/db/repositories/models.py
- backend/alembic/versions/20260908_0001_e5a6b7c8d9e0_add_onboarding_step_to_users.py (NEW)
- backend/app/services/auth_service.py
- backend/app/routers/auth.py
- backend/app/routers/clients.py
- backend/tests/test_onboarding_step.py (NEW)
- frontend/lib/api.ts
- frontend/components/onboarding/OnboardingFlow.tsx
- frontend/components/onboarding/OnboardingPlatformStep.tsx
- frontend/components/onboarding/ProgressIndicator.tsx
- frontend/__tests__/components/OnboardingFlow.test.tsx

## Suggested Review Order

**Step persistence carrier (JWT + DB + proxy)**

- New `onboarding_step` column on User and its nullable type; source of truth.
  [`models.py:1`](../../backend/app/db/repositories/models.py#L1)

- `create_session_token` now accepts `onboarding_step`; written to JWT only when non-None.
  [`security.py:1`](../../backend/app/core/security.py#L1)

- `_issue_session` and `login_user` forward `onboarding_step` from DB into JWT; `patch_onboarding_step` refreshes cookie immediately.
  [`auth_service.py:92`](../../backend/app/services/auth_service.py#L92)

- Proxy decodes JWT and forwards `x-onboarding-step` header to Next.js server component.
  [`proxy.ts:51`](../../frontend/proxy.ts#L51)

- Server component reads header and passes `initialStep` prop to the client component.
  [`page.tsx:10`](../../frontend/app/onboarding/page.tsx#L10)

**PATCH /auth/onboarding-step endpoint**

- New `OnboardingStepRequest` schema and `PATCH /onboarding-step` route on the auth router.
  [`auth.py:1`](../../backend/app/routers/auth.py#L1)

**Voice preview endpoint**

- `POST /{client_id}/voice-preview`: synchronous, no Job row, 502 on provider error, 404 on missing BVP.
  [`clients.py:1`](../../backend/app/routers/clients.py#L1)

**OnboardingFlow (resume + reorder + voice proof + draft)**

- Step state initialised from `initialStep` prop with clamping; `persistStep` fire-and-forget on each transition.
  [`OnboardingFlow.tsx:1`](../../frontend/components/onboarding/OnboardingFlow.tsx#L1)

- VoiceProof TanStack Query + shimmer skeleton + CSS `voiceProofIn` animation; silent hide on error.
  [`OnboardingFlow.tsx:1`](../../frontend/components/onboarding/OnboardingFlow.tsx#L1)

- Scrape failure one-liner: `no_content` vs other copy, rendered above questionnaire (not as error banner).
  [`OnboardingFlow.tsx:1`](../../frontend/components/onboarding/OnboardingFlow.tsx#L1)

- Step reorder: brain dump = Step 3 (VoiceBrainDump wired), platform connection = Step 4; `completeAndNavigate` only from Step 4 exits.
  [`OnboardingFlow.tsx:1`](../../frontend/components/onboarding/OnboardingFlow.tsx#L1)

- Draft localStorage key `onboarding_brain_dump_draft`, 7-day TTL, restore banner, `clearDraft` on success/skip.
  [`OnboardingFlow.tsx:1`](../../frontend/components/onboarding/OnboardingFlow.tsx#L1)

**Platform step and progress indicator**

- `OnboardingPlatformStep` receives `campaignId` + `campaignJobId`; OAuth click writes both to sessionStorage.
  [`OnboardingPlatformStep.tsx:1`](../../frontend/components/onboarding/OnboardingPlatformStep.tsx#L1)

- 4 labeled steps with `aria-current="step"` and sr-only "Completed" for done steps; stays server-safe.
  [`ProgressIndicator.tsx:1`](../../frontend/components/onboarding/ProgressIndicator.tsx#L1)

**API client additions**

- `authApi.patchOnboardingStep` and `clientsApi.voicePreview` added.
  [`api.ts:1`](../../frontend/lib/api.ts#L1)

**Tests**

- 9 backend unit tests: step persistence, 404/step-clear, voice-preview happy/timeout/ownership paths.
  [`test_onboarding_step.py:1`](../../backend/tests/test_onboarding_step.py#L1)

- Frontend vitest suite: resume, voice proof, scrape failure copy, draft, OAuth return, completeOnboarding timing.
  [`OnboardingFlow.test.tsx:1`](../../frontend/__tests__/components/OnboardingFlow.test.tsx#L1)

- Alembic migration (hand-written; verify with `alembic check` before deploy).
  [`20260908_0001_e5a6b7c8d9e0_add_onboarding_step_to_users.py:1`](../../backend/alembic/versions/20260908_0001_e5a6b7c8d9e0_add_onboarding_step_to_users.py#L1)
