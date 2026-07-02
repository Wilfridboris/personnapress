---
baseline_commit: f39c2ec8b8dd370dd90e08d1874703a23bc0d7db
---

# Story 3.5: Onboarding Step 3 Completion & Generation Integration

Status: done

## Story

As a new user completing onboarding,
I want the "Generate my first campaign" button in onboarding Step 3 to kick off the same full content generation pipeline as the main Brain Dump flow,
So that my onboarding experience leads directly to my first real Campaign without any context switch.

## Acceptance Criteria

1. **Given** a user on onboarding Step 3 enters a Brain Dump (≥20 characters) and clicks "Generate my first campaign," **When** the CTA is clicked, **Then** the same Campaign creation flow runs as Story 3.1: subscription limit check → `POST /api/v1/campaigns` with the brain dump text and `createdClientId` → `campaigns` record + `jobs` record created → BackgroundTask dispatched → 202 response; the user is navigated to `/campaigns/{campaign_id}?job_id={job_id}` showing the typewriter generation state (Story 3.2).

2. **Given** the Campaign generated from onboarding completes, **When** the typewriter animation reaches "Done." and polling stops, **Then** the Approval Gate content loads (campaign page renders the generated content); on subsequent logins the user is redirected directly to `/dashboard` — the `onboarding_completed` flag is already set (was set before campaign creation in Story 2.7's stub flow OR is set here as part of the submission).

3. **Given** the user clicks "I'll write my first draft later" (skip link on Step 3), **When** they are redirected to `/dashboard`, **Then** a nudge card appears at the top of the campaign list: "Complete your first campaign." with a "New Campaign" CTA — this nudge is shown until the user creates their first Campaign.

4. **Given** the onboarding Step 3 form is submitted, **When** the "Generate my first campaign" button is clicked, **Then** `POST /api/v1/auth/complete-onboarding` is called BEFORE `POST /api/v1/campaigns` so that the JWT is re-issued with `onboarding_completed=true`; this ensures the `/onboarding` redirect guard does not re-trigger when the user lands on `/campaigns/{id}`.

5. **Given** the `POST /api/v1/campaigns` call fails (subscription limit, server error), **When** the API returns an error, **Then** the error is shown inline in the onboarding Step 3 UI: "Could not start generation — [error message]." with a "Try again" link; the user stays on Step 3; onboarding is NOT marked complete (the `complete-onboarding` call is rolled back conceptually — see implementation note).

6. **Given** the `/dashboard/new?prefill={encodedBrainDump}` stub navigation from Story 2.7, **When** this story is implemented, **Then** the stub handler in `OnboardingFlow.tsx` Step 3 `handleStep3Submit` is REPLACED with the real campaign creation flow; the `/campaigns/new` page `prefill` query param handling added in the stub is also removed.

7. **Given** the `createdClientId` from onboarding Step 1 is set in `OnboardingFlow` state, **When** Step 3 submits, **Then** `createdClientId` is used as the `client_id` for the new Campaign; if `createdClientId` is null (user skipped Step 1), the `activeClientId` from `useClientStore` is used as fallback; if both are null, the submit button is disabled with "Create a client first." message.

## Tasks / Subtasks

- [x] Task 1: Frontend — Update `OnboardingFlow.tsx` Step 3 submit handler (AC: #1, #4, #5, #6, #7)
  - [x] 1.1 In `frontend/components/onboarding/OnboardingFlow.tsx`, locate the `handleStep3Submit` function (currently calls `authApi.completeOnboarding()` then navigates to `/dashboard/new?prefill=...`)
  - [x] 1.2 Replace the stub logic with the real campaign creation flow:
    ```typescript
    async function handleStep3Submit(brainDump: string) {
      setIsSubmitting(true);
      setStep3Error(null);
      
      try {
        // Step 1: Complete onboarding FIRST to update JWT
        await authApi.completeOnboarding();
        
        // Step 2: Determine client_id
        const clientId = createdClientId ?? activeClientId;
        if (!clientId) {
          setStep3Error("Create a client first — go back to Step 1.");
          return;
        }
        
        // Step 3: Create campaign
        const { campaign_id, job_id } = await campaignsApi.create({
          client_id: clientId,
          brain_dump: brainDump,
        });
        
        // Step 4: Navigate to campaign generation page
        router.push(`/campaigns/${campaign_id}?job_id=${job_id}`);
        
      } catch (err) {
        // If campaign creation fails after onboarding was completed:
        // onboarding_completed=true is already set but that's OK —
        // the user is redirected to /dashboard on next reload
        const message = err instanceof Error ? err.message : "Something went wrong.";
        setStep3Error(`Could not start generation — ${message}`);
      } finally {
        setIsSubmitting(false);
      }
    }
    ```
  - [x] 1.3 Add `step3Error: string | null` state to the component; render inline error below the textarea when non-null: Danger-color text, "Try again" link that clears the error
  - [x] 1.4 The `isSubmitting` state already exists for the loading state on the button — ensure it works correctly with the new async flow
  - [x] 1.5 Import `campaignsApi` from `lib/api.ts` in `OnboardingFlow.tsx`
  - [x] 1.6 The `activeClientId` fallback: import `useClientStore` and read `activeClientId` from it; if `createdClientId` is set (from Step 1 completion), prefer that over the store value

- [x] Task 2: Frontend — Remove stub `/campaigns/new?prefill` handling (AC: #6)
  - [x] 2.1 In `frontend/app/(app)/campaigns/new/page.tsx` (being rewritten in Story 3.1): do NOT add `prefill` URL param handling — the stub from Story 2.7 navigated to `/dashboard/new` not `/campaigns/new`; the stub is replaced entirely by this story
  - [x] 2.2 Verify no other file reads a `?prefill` query param and remove any such code if found

- [x] Task 3: Frontend — Validate submit button disabled state (AC: #7)
  - [x] 3.1 In the Step 3 render block of `OnboardingFlow.tsx`: the "Generate my first campaign" button must be disabled when:
    - `charCount < 20` (existing condition)
    - `isSubmitting` (existing condition)  
    - `createdClientId === null && activeClientId === null` (new condition — no client available)
  - [x] 3.2 Show "Create a client first." message near the button when both client IDs are null (though this is an edge case — user would have had to skip Step 1 and have no prior clients)

- [x] Task 4: Frontend — Onboarding completion flow verification (AC: #2, #3)
  - [x] 4.1 Verify that after navigating to `/campaigns/{id}?job_id=...`, the Next.js middleware does NOT redirect back to `/onboarding` — this is guaranteed by calling `complete-onboarding` FIRST in Task 1.2 (re-issues JWT with `onboarding_completed=true` before navigation)
  - [x] 4.2 The skip link flow (Task 1 in Story 2.7) already calls `complete-onboarding` and navigates to `/dashboard?nudge=true` — verify this still works unchanged
  - [x] 4.3 The `NudgeCard` in `dashboard/page.tsx` already checks `?nudge=true` and `campaigns.length === 0` — no changes needed for the nudge card itself

- [x] Task 5: Frontend — Update `campaignsApi` import in OnboardingFlow (AC: #1)
  - [x] 5.1 `campaignsApi` is defined in `lib/api.ts` — add the import to `OnboardingFlow.tsx`
  - [x] 5.2 Verify `campaignsApi.create` returns `{ campaign_id: string; job_id: string }` — this was defined in Story 3.1; if Story 3.1 is not yet implemented when this runs, the function signature should be assumed from the Story 3.1 spec

- [x] Task 6: Tests (AC: #1, #4, #5)
  - [x] 6.1 Update `OnboardingFlow` component tests (if any exist) to cover the new Step 3 submit flow
  - [x] 6.2 Test: Step 3 submit → complete-onboarding called → campaignsApi.create called → navigate to /campaigns/{id}
  - [x] 6.3 Test: campaignsApi.create fails → error displayed → user stays on Step 3
  - [x] 6.4 Test: no createdClientId and no activeClientId → button disabled, error message shown

## Dev Notes

### The complete-onboarding Before Campaign Creation Order

The reason `complete-onboarding` must be called BEFORE `POST /campaigns` is the JWT middleware:

```
Without this order:
  Submit Step 3 → POST /campaigns → redirect to /campaigns/{id}
  → middleware checks JWT: onboarding_completed=false → redirect to /onboarding ❌

With this order:
  Submit Step 3 → POST /auth/complete-onboarding (re-issues JWT with onboarding_completed=true)
                → POST /campaigns → redirect to /campaigns/{id}
  → middleware checks JWT: onboarding_completed=true → proceeds normally ✓
```

### Failure Recovery — If Campaign Creation Fails After complete-onboarding

If `POST /campaigns` fails after `POST /auth/complete-onboarding` succeeds:
- The JWT now has `onboarding_completed=true`
- The user sees the error on Step 3
- If they try again, `complete-onboarding` is called again (idempotent) then campaign creation is retried — this is fine
- If they reload the page: middleware sees `onboarding_completed=true`, redirects to `/dashboard` — the onboarding flow is considered done even without a campaign (the nudge card handles the "complete your first campaign" call-to-action)

This is an acceptable UX trade-off. The `complete-onboarding` endpoint is idempotent (setting a flag that's already true is a no-op).

### Story 2.7 Stub — What Was Implemented

From Story 2.7's implementation plan:
```
Task 8.2: Submit handler calls `complete-onboarding` and navigates to `/dashboard/new?prefill={encodedBrainDump}`
```

So the current `handleStep3Submit` in `OnboardingFlow.tsx` navigates to `/dashboard/new?prefill=...`. This story replaces that navigation with the real campaign creation call and redirect to `/campaigns/{id}?job_id=...`.

The `/campaigns/new` page (being rewritten in Story 3.1) should NOT read a `prefill` query param — that was a temporary stub mechanism. Since this story (3.5) replaces the stub before Story 3.1's new campaign page goes live, the timing works correctly as long as stories are implemented in order.

### createdClientId vs activeClientId Priority

The `createdClientId` state in `OnboardingFlow.tsx` tracks the client created in Step 1. This is the preferred client for the first campaign (the user just set it up). The `activeClientId` from `useClientStore` is a fallback for users who:
- Had existing clients before starting this onboarding run (edge case — onboarding is shown only once)
- Skipped Step 1 (no `createdClientId` set)

In practice, nearly all users will have `createdClientId` set because the onboarding only shows once and Step 1 creates the first client. The fallback handles the skip-Step-1 path.

### No Backend Changes Required

This story is purely frontend. The backend endpoints it uses (`POST /auth/complete-onboarding` and `POST /campaigns`) are both implemented in prior stories (Story 2.7 and Story 3.1 respectively). No new backend code is needed.

### UX — Step 3 Error State

```
3 of 3

   What's on your mind this week?

   [Brain Dump textarea]
   47 / 10,000 characters

   ╔════════════════════════════════════════════╗
   ║ Could not start generation — Campaign      ║
   ║ limit reached for this billing cycle.      ║
   ║ Try again                                  ║  ← text link clears the error
   ╚════════════════════════════════════════════╝

   [Generate my first campaign]   ← enabled again after error clear
```

Error box uses:
- `border border-danger/30 bg-danger/5 p-4` — Danger-tinted background, no harsh border
- `text-sm font-mono text-danger` — Danger-colored monospace error text
- "Try again" is a `<button type="button" className="underline hover:no-underline">` that calls `() => setStep3Error(null)`

### Dependency Order

This story depends on:
- **Story 2.7 done** ✓ — `OnboardingFlow.tsx` and `POST /auth/complete-onboarding` exist
- **Story 3.1 done** (recommended before or parallel) — `POST /api/v1/campaigns` endpoint exists; if implementing in parallel, the `campaignsApi.create` can be assumed from the Story 3.1 spec

### File Structure

**Updated files this story:**
```
frontend/components/onboarding/OnboardingFlow.tsx  ← replace Step 3 stub submit handler
```

**No new files required.** All the backend infrastructure was built in Stories 2.7 and 3.1.

### References

- Story 3.1 (POST /campaigns endpoint + campaignsApi.create): this story consumes it
- Story 2.7 (complete-onboarding endpoint, OnboardingFlow.tsx scaffold, Step 3 stub): [Source: _bmad-output/implementation-artifacts/2-7-onboarding-flow.md]
- Story 3.2 (TypewriterAnimation + /campaigns/{id}?job_id= route): where the user lands after submit
- FR-12 Brain Dump campaign creation (20-10,000 chars, same flow as main Brain Dump): [Source: _bmad-output/planning-artifacts/epics.md#FR-12]
- UX-DR11 Onboarding Step 3 — "Generate my first campaign" CTA, skip link behavior: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR11]
- Story 2.7 Dev Notes: "Step 3 Brain Dump Integration (Story 3.5 Note) — for Story 2.7, the button calls complete-onboarding and navigates to /dashboard/new. Story 3.5 will refactor this to the full campaign creation.": [Source: _bmad-output/implementation-artifacts/2-7-onboarding-flow.md#Dev Notes]
- AR-10 Zustand useClientStore for activeClientId: [Source: _bmad-output/planning-artifacts/epics.md#AR-10]
- UX-DR21 Paper Style microcopy — error messages name the specific error and resolution path: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR21]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Replaced `handleStep3Submit` stub in `OnboardingFlow.tsx` — now calls `authApi.completeOnboarding()` first (JWT re-issue), then resolves `clientId` (createdClientId ?? activeClientId), then `campaignsApi.create()`, then navigates to `/campaigns/{id}?job_id={id}`.
- Added `step3Error` state with inline error box (danger-tinted, "Try again" button clears error).
- Added "no client" guard: button disabled + "Create a client first." message when both `createdClientId` and `activeClientId` are null.
- Imported `campaignsApi` and `useClientStore` in `OnboardingFlow.tsx`.
- Verified `campaigns/new/page.tsx` has no `?prefill` param handling — confirmed clean.
- Skip link (`handleSkipStep3`) was already correct: calls `complete-onboarding` then navigates to `/dashboard?nudge=true`.
- NudgeCard and dashboard nudge flow verified unchanged.
- Created `frontend/__tests__/components/OnboardingFlow.test.tsx` with 6 tests covering happy path, client ID priority, error display, Try again, and disabled state.
- All 18 tests pass (3 test files), TypeScript passes with no errors.

### File List

- `frontend/components/onboarding/OnboardingFlow.tsx` (modified)
- `frontend/__tests__/components/OnboardingFlow.test.tsx` (created)

## Change Log

- 2026-07-02: Story 3.5 implemented — replaced Step 3 Brain Dump stub submit handler with real campaign creation flow: complete-onboarding → campaignsApi.create → navigate to /campaigns/{id}?job_id={id}. Added step3Error state with inline error UI and Try again button. Added no-client guard on submit button. Created 6 unit tests covering happy path, client ID priority, error display, and disabled state.

