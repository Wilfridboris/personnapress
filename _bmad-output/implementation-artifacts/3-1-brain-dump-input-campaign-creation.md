---
baseline_commit: 44d907cadab9f414405a193249bee8c7fc44148d
---

# Story 3.1: Brain Dump Input & Campaign Creation

Status: done

## Story

As an authenticated user,
I want to type or paste my raw idea into a Brain Dump input and submit it to start content generation,
So that I can kick off the full content pipeline from a rough thought in seconds.

## Acceptance Criteria

1. **Given** an authenticated user navigates to `/campaigns/new`, **When** the page loads, **Then** a Brain Dump input page is shown: a full-width JetBrains Mono auto-expanding textarea with a subtle bottom-border-only style; a character counter below reads "0 / 10,000 characters"; a "Generate campaign" primary Button (Paper Style) is present and disabled until the minimum character threshold is met.

2. **Given** the user types fewer than 20 characters in the Brain Dump textarea, **When** the character count is below 20, **Then** the submit button remains disabled; the inline counter reads "N / 10,000 characters" in Danger color (#8B0000) to signal the minimum has not been met; the Danger color clears once ≥20 characters are entered.

3. **Given** the user has typed at least 20 characters and clicks "Generate campaign," **When** the form is submitted, **Then** `services/subscription.py` is called to verify the user has not reached their plan's campaign count limit for the current billing cycle; if within limit, `POST /api/v1/campaigns` is called with the brain dump text and the currently active client ID (from `useClientStore`).

4. **Given** the campaign count limit has been reached, **When** the form is submitted, **Then** the API returns HTTP 400 with error code `CAMPAIGN_LIMIT_EXCEEDED` and the UI displays: "You've reached your [N]-campaign limit for this billing cycle. Upgrade to [next tier] for more campaigns." with an upgrade CTA — no Campaign record is created.

5. **Given** the subscription limit check passes, **When** `POST /api/v1/campaigns` is processed by FastAPI, **Then** a `campaigns` record is created with `status='pending_approval'`, `brain_dump` set to the submitted text, and `client_id` from the request; a `jobs` record is created with `job_type='generation'` and `status='pending'` BEFORE the BackgroundTask is dispatched; the API returns HTTP 202 with `{"campaign_id": "...", "job_id": "..."}`.

6. **Given** the 202 response is received by the frontend, **When** it arrives, **Then** Next.js navigates to `/campaigns/{campaign_id}` — the Approval Gate/generation route — where the job_id is available for polling (typewriter UI implemented in Story 3.2).

7. **Given** the Enter key is pressed while focus is in the Brain Dump textarea, **When** the key event fires, **Then** the form does NOT submit — Enter inserts a newline. Only the "Generate campaign" button submits. Cmd/Ctrl+Enter submits as a power-user shortcut.

8. **Given** the user presses Esc while focus is in the Brain Dump textarea, **When** the key event fires, **Then** nothing happens — the textarea content is preserved.

9. **Given** no active client is set in `useClientStore`, **When** the page renders, **Then** the submit button is disabled with the message "Select a client first — use the switcher in the sidebar." and a "Go to Clients" link; the Brain Dump textarea is still editable so the user can compose while navigating.

10. **Given** the active client has no Brand Voice Profile (BVP is null), **When** the page renders, **Then** an advisory notice is shown: "This client has no voice profile yet. Content will be generated without brand alignment. Set up a voice profile first." with a link to the client's voice setup page — the submit button is NOT disabled (generation can still proceed without BVP per existing backend logic).

## Tasks / Subtasks

- [x] Task 1: Backend — Campaign + Job creation endpoint (AC: #3, #4, #5)
  - [x] 1.1 Create `backend/app/schemas/campaign.py` with `CampaignCreate` (client_id, brain_dump), `CampaignResponse` (all Campaign fields), and `CampaignCreateResponse` (campaign_id, job_id)
  - [x] 1.2 Create `backend/app/db/repositories/campaigns.py` with `create_campaign(db, client_id, brain_dump) -> Campaign` and `get_campaign(db, campaign_id) -> Campaign | None` async functions
  - [x] 1.3 Create `backend/app/db/repositories/generation_logs.py` with `create_generation_log(db, user_id, campaign_id, gemini_tokens=None, replicate_count=None) -> GenerationLog` (needed by Stories 3.3 and 3.4 but define the repo now)
  - [x] 1.4 In `backend/app/routers/campaigns.py`, add `POST /campaigns` endpoint: authenticate user → verify active client ownership → call `subscription_service.check_campaign_limit` → create Campaign record → create Job record (job_type='generation', status='pending') → dispatch BackgroundTask (stub: `workers.generate.run_generation(job_id)`) → return 202 `CampaignCreateResponse`
  - [x] 1.5 Add `GET /campaigns/{campaign_id}` endpoint in `campaigns.py`: authenticate user → verify ownership via campaign→client→user chain → return full Campaign; return 404 if not found or not owned
  - [x] 1.6 In `backend/app/services/subscription_service.py` add `check_campaign_limit(db, user_id) -> None` that reads `subscriptions.campaigns_used` vs plan tier limit and raises HTTPException 400 with `CAMPAIGN_LIMIT_EXCEEDED` if at limit; increment `campaigns_used` atomically on success
  - [x] 1.7 Create stub `backend/app/workers/generate.py` with `async def run_generation(job_id: uuid.UUID) -> None: pass` — real implementation in Story 3.3
  - [x] 1.8 Register `campaigns` and ensure the router is included in `backend/app/main.py` (already registered if campaigns router was scaffold — verify)

- [x] Task 2: Backend — campaigns router GET list endpoint (AC: used by frontend campaign list page)
  - [x] 2.1 Add `GET /campaigns` endpoint: returns list of Campaigns for the authenticated user (via client ownership), ordered by `created_at` DESC; this supports the existing `/campaigns` list page

- [x] Task 3: Frontend — Revamp `/campaigns/new` page to Paper Style spec (AC: #1, #2, #7, #8, #9, #10)
  - [x] 3.1 Delete the existing `useActionState`-based implementation in `frontend/app/(app)/campaigns/new/page.tsx` and rewrite as `'use client'` component using React state + `campaignsApi.create()` from `lib/api.ts`
  - [x] 3.2 Read active client from `useClientStore` (NOT a select dropdown); show client name as context label "Writing for: [Client Name]" above the textarea
  - [x] 3.3 Implement Brain Dump textarea using the existing BrainDump Input variant pattern: JetBrains Mono (`font-mono`), auto-expanding (dynamic `rows` based on content), `border-0 border-b border-ink` (bottom-border-only at 1px, 2px on focus via `focus:border-b-2`), transparent background, no resize handle (`resize-none`), min height `min-h-[200px]`
  - [x] 3.4 Character counter below textarea: `"N / 10,000 characters"` — use `text-danger` when N < 20, `text-graphite` otherwise; update live on each keystroke
  - [x] 3.5 Submit button: use `Button` component from `components/ui/Button.tsx` with `variant="primary"` — disabled when `charCount < 20` OR no active client OR `isSubmitting`; label: "Generate campaign"
  - [x] 3.6 Keyboard handling: add `onKeyDown` to textarea — if `e.key === 'Enter' && !e.metaKey && !e.ctrlKey` → `e.preventDefault()` (prevent form submit but DO NOT prevent default textarea newline behavior — only needed if the form has submit-on-enter behavior, which React forms don't by default for textareas); if `e.key === 'Enter' && (e.metaKey || e.ctrlKey)` → call submit handler; if `e.key === 'Escape'` → `e.preventDefault()` (do nothing, preserve content)
  - [x] 3.7 No-active-client state: show "Select a client first." warning and disable submit; show "Go to Clients" link to `/clients`
  - [x] 3.8 No-BVP advisory notice: when `activeClient.brand_voice_profile === null`, show advisory (non-blocking) notice above submit button; include link to `/clients/{id}/voice`
  - [x] 3.9 On form submit success: navigate to `/campaigns/${data.campaign_id}` using `router.push()` from `next/navigation`; pass `job_id` via URL query `?job_id=${data.job_id}` so the campaign page can start polling immediately without an extra fetch
  - [x] 3.10 On form submit error (CAMPAIGN_LIMIT_EXCEEDED): display upgrade prompt with the error message from API; other errors: show inline error message in Danger style

- [x] Task 4: Frontend — update `campaignsApi` in `lib/api.ts` (AC: #3, #5)
  - [x] 4.1 `campaignsApi.create` already exists — verify it sends `credentials: "include"` (it does via `apiFetch`) and returns `{ campaign_id, job_id }` — update TypeScript return type if needed
  - [x] 4.2 Ensure `campaignsApi.get(id)` returns `Campaign` type — already defined; verify response shape matches `CampaignResponse` from backend

- [x] Task 5: Backend tests (AC: #3, #4, #5)
  - [x] 5.1 Create `backend/tests/routers/test_campaigns.py` with tests: POST /campaigns with valid data → 202 + campaign_id + job_id; POST /campaigns with no active client → 404; POST /campaigns at plan limit → 400 CAMPAIGN_LIMIT_EXCEEDED; POST /campaigns with brain_dump < 20 chars → 422 (Pydantic validation); GET /campaigns/{id} → 200 Campaign; GET /campaigns/{id} for wrong user → 404

## Dev Notes

### Existing State — What Already Exists

The existing `frontend/app/(app)/campaigns/new/page.tsx` is a `useActionState`-based implementation that:
- Uses a `<select>` dropdown to pick a client (incorrect — should use active client from `useClientStore`)
- Has a regular full-border textarea (incorrect — should be bottom-border-only per UX-DR4)
- Character counter shows "N chars" (incorrect — should be "N / 10,000 characters")
- Uses inline fetch without `credentials: "include"` (incorrect — cookies won't be sent)
- Does NOT implement Cmd+Enter or proper Esc handling

**This page must be rewritten from scratch** (Task 3.1). The rewrite is in the same file path.

The `backend/app/routers/campaigns.py` is currently empty (3 lines, just the router definition). All campaign endpoints must be added.

### Backend Architecture Constraints

- `services/subscription_service.py` already exists and has the subscription check pattern — add `check_campaign_limit` following the same pattern as `check_client_limit` if it exists
- The Job record MUST be created in the same database transaction as the Campaign record before the BackgroundTask is dispatched — this ensures job durability (NFR-7). If the BackgroundTask fails to dispatch, the Job record is still in the DB so it can be retried
- Return HTTP 202 (not 201) — the campaign is created but not yet processed. The frontend polls for completion
- `BackgroundTasks` parameter in FastAPI: add `background_tasks: BackgroundTasks` to the endpoint signature; call `background_tasks.add_task(run_generation, job_id)` after both records are committed

### Subscription Limit Check Logic

Plan tiers and campaign limits (from `core/constants.py` or equivalent):
- `starter`: 10 campaigns/cycle
- `growth`: 30 campaigns/cycle
- `agency`: 100 campaigns/cycle

The `check_campaign_limit` service must:
1. Query `subscriptions` for the user's current active subscription
2. Compare `campaigns_used` against the tier limit
3. If at limit → raise `HTTPException(400, {"error": {"code": "CAMPAIGN_LIMIT_EXCEEDED", ...}})`
4. If within limit → increment `campaigns_used` by 1 atomically and commit

### Brain Dump Validation

- Minimum: 20 characters (enforced both client-side and server-side via Pydantic `Field(min_length=20)`)
- Maximum: 10,000 characters (enforced both client-side via counter and server-side via `Field(max_length=10000)`)
- Pydantic validation failure returns HTTP 422 — no custom error needed server-side for length violations

### UX — Brain Dump Textarea (Paper Style UX-DR4)

```
Brain Dump Input (JetBrains Mono, 14px, line-height 1.7):

  [____________________________________________________]
  ← bottom border only: 1px border-b border-ink/20 at rest
    2px border-b-2 border-ink on focus
  → transparent background
  → no resize handle (resize-none)
  → auto-expanding via scrollHeight approach or rows attr
  → min-h-[200px]
  → no placeholder shown once user starts typing

Counter below:
  "0 / 10,000 characters" → text-danger when < 20 chars
  "47 / 10,000 characters" → text-graphite when ≥ 20 chars
```

### UX — Page Layout

```
/campaigns/new page layout (max-w-2xl, centered within 720px content area):

  ← Back to campaigns      ← text link with ArrowLeft icon

  NEW CAMPAIGN             ← Inter 12px uppercase tracking-widest graphite label
  Brain Dump               ← Playfair Display H1, 3xl bold ink

  Writing for: Acme Corp   ← Inter 12px graphite (active client name from store)

  [advisory: no voice profile if applicable]

  [Brain Dump textarea — full width, JetBrains Mono, bottom border only]

  N / 10,000 characters    ← below textarea, right-aligned or left

  [Generate campaign]      ← Primary Button, full-width on mobile
```

### Navigate-Away Guard (Story 3.2 implements the full dialog)

This story only needs to navigate away cleanly on success. The "generation in progress" navigate-away dialog is implemented in Story 3.2 once polling is active. Story 3.1's navigation is pre-generation (the BackgroundTask hasn't produced visible output yet).

### Dependency Note for Story 3.3

Story 3.1 creates the `workers/generate.py` as a stub. Story 3.3 fills in the actual Gemini generation logic. The stub must be importable and callable without crashing — `async def run_generation(job_id: uuid.UUID) -> None: pass` is sufficient.

### File Structure

**New files this story:**
```
backend/app/schemas/campaign.py
backend/app/db/repositories/campaigns.py
backend/app/db/repositories/generation_logs.py
backend/app/workers/generate.py           ← stub, filled in Story 3.3
backend/tests/routers/test_campaigns.py
```

**Updated files this story:**
```
backend/app/routers/campaigns.py          ← add POST + GET endpoints
backend/app/services/subscription_service.py  ← add check_campaign_limit
backend/app/main.py                       ← verify campaigns router is registered
frontend/app/(app)/campaigns/new/page.tsx ← full rewrite
frontend/lib/api.ts                       ← verify/update campaignsApi types
```

### References

- FR-12 Brain Dump spec (20-10,000 chars, JetBrains Mono, auto-expand, Enter ≠ submit, Cmd+Enter submits, Esc=nothing): [Source: _bmad-output/planning-artifacts/epics.md#FR-12]
- FR-15 202 Accepted + job record before BackgroundTask: [Source: _bmad-output/planning-artifacts/epics.md#FR-15]
- UX-DR4 Brain Dump textarea style (bottom-border-only, JetBrains Mono, no resize): [Source: _bmad-output/planning-artifacts/epics.md#UX-DR4]
- UX-DR23 Brain Dump interaction rules (Enter=newline, Cmd+Enter=submit, Esc=nothing, N/10,000 counter, disabled <20 chars, navigate-away confirm): [Source: _bmad-output/planning-artifacts/epics.md#UX-DR23]
- UX-DR3 Primary Button spec (ink fill, white text, 4px hard shadow, inverts on hover): [Source: _bmad-output/planning-artifacts/epics.md#UX-DR3]
- AR-10 Zustand useClientStore for active client: [Source: _bmad-output/planning-artifacts/epics.md#AR-10]
- AR-17 FastAPI routes prefix /api/v1/, standard error response format: [Source: _bmad-output/planning-artifacts/epics.md#AR-17]
- AR-18 Subscription tier enforcement before create: [Source: _bmad-output/planning-artifacts/epics.md#AR-18]
- AR-19 Service boundaries (no business logic in routers): [Source: _bmad-output/planning-artifacts/epics.md#AR-19]
- NFR-7 Job durability (job record created before BackgroundTask dispatch): [Source: _bmad-output/planning-artifacts/epics.md#NFR-7]
- Story 3.2 (typewriter polling — the campaign page generation state is implemented there): [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2]
- Story 3.3 (workers/generate.py actual implementation — stub here): [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Pre-existing test failures confirmed in `test_client_limit.py` (4 tests) — these exist on baseline commit, unrelated to this story. The `_db_scalars` mock helper in that file does not set up `.scalar()` on the result object, causing a TypeError when `check_client_limit` compares the mock result to an int.

### Completion Notes List

- Implemented `POST /campaigns` (202) and `GET /campaigns`, `GET /campaigns/{id}` endpoints in `campaigns.py`.
- `check_campaign_limit` added to `subscription_service.py`, following the same TOCTOU-safe locking pattern as `check_client_limit`. Increments `campaigns_used` atomically on success.
- `workers/generate.py` created as importable stub (`async def run_generation(job_id) -> None: pass`).
- Frontend `/campaigns/new` page fully rewritten: reads active client from `useClientStore`, Paper Style BrainDump textarea (bottom-border-only, JetBrains Mono, auto-expand, min-h-[200px]), character counter with danger color below 20, Enter=newline, Cmd/Ctrl+Enter=submit, Esc=noop, no-client state disables submit, no-BVP advisory notice, navigates to `/campaigns/{id}?job_id={id}` on success.
- `campaignsApi` in `lib/api.ts` already correctly typed — verified `credentials: "include"` via `apiFetch` and return type matches backend.
- 15 new backend tests pass (10 router tests + 5 subscription limit tests). TypeScript check passes with 0 errors.

### File List

**New files:**
- `backend/app/schemas/campaign.py`
- `backend/app/db/repositories/campaigns.py`
- `backend/app/db/repositories/generation_logs.py`
- `backend/app/workers/generate.py`
- `backend/tests/test_campaigns_router.py`
- `backend/tests/test_campaign_limit.py`

**Modified files:**
- `backend/app/routers/campaigns.py`
- `backend/app/services/subscription_service.py`
- `frontend/app/(app)/campaigns/new/page.tsx`

### Review Findings

- [x] [Review][Patch] CAMPAIGN_LIMIT_EXCEEDED UI shows generic error — missing upgrade CTA per AC#4 [frontend/app/(app)/campaigns/new/page.tsx]
- [x] [Review][Patch] No-subscription users bypass campaign limit increment — unlimited campaigns allowed [backend/app/services/subscription_service.py:check_campaign_limit]
- [x] [Review][Dismiss] BVP check uses wrong field — false positive; ClientListItem only has brand_voice_profile_status, current check is correct
- [x] [Review][Patch] Whitespace-only brain dump (20 spaces) passes `min_length=20` — add server-side strip+recheck [backend/app/schemas/campaign.py]
- [x] [Review][Patch] `isSubmitting` not reset to `false` if navigation is slow/delayed [frontend/app/(app)/campaigns/new/page.tsx:handleSubmit]
- [x] [Review][Patch] Danger counter color active at 0 chars on load — spec says normal style initially [frontend/app/(app)/campaigns/new/page.tsx]
- [x] [Review][Patch] `&mdash;` HTML entity in JSX renders as literal string — use Unicode or `—` [frontend/app/(app)/campaigns/new/page.tsx]
- [x] [Review][Patch] Dead `with_for_update()` on User row when sub is None — no-op, remove [backend/app/services/subscription_service.py:check_campaign_limit]
- [x] [Review][Patch] Inline model import inside `list_campaigns` body — resolve circular import at module level [backend/app/routers/campaigns.py:list_campaigns]
- [x] [Review][Defer] `campaigns_used` never reset on billing cycle renewal — pre-existing Stripe webhook handler, not this story — deferred, pre-existing
- [x] [Review][Defer] `GET /campaigns` has no pagination — architectural gap, out of scope for this story — deferred, pre-existing
- [x] [Review][Defer] `run_generation` stub — intentional, filled in Story 3.3 — deferred, pre-existing
- [x] [Review][Decision] Character counter at 0 chars: applied option 1 (Danger per spec AC 3.1-2) — removed `charCount > 0 &&` guard so 0 chars shows Danger [frontend/app/(app)/campaigns/new/page.tsx]
- [x] [Review][Patch] TOCTOU: two concurrent campaign creates for a user with no Subscription row both pass limit check — added `.with_for_update()` on User row in no-sub branch [backend/app/services/subscription_service.py]
- [x] [Review][Patch] `create_campaign` does not explicitly set `status='pending_approval'` — added explicit `status="pending_approval"` to Campaign constructor [backend/app/db/repositories/campaigns.py]

## Change Log

- 2026-07-02: Implemented story 3.1 — Brain Dump input page rewrite, campaign/job creation endpoint (POST 202), campaign GET endpoints, subscription campaign limit check, generation worker stub, and full backend test coverage (15 tests).
