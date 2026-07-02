---
baseline_commit: ec18f340d15caabb37fa174db040da46e8729094
---

# Story 2.7: 3-Step Onboarding Flow

Status: done

## Story

As a newly registered user,
I want a guided onboarding flow that walks me through creating my first client and setting up my brand voice,
So that I can go from sign-up to content-ready as quickly as possible without needing to discover these steps on my own.

## Acceptance Criteria

1. **Given** a user logs in for the first time (post-registration, email verified or Google OAuth), **When** they are redirected post-authentication, **Then** they land on `/onboarding` (Step 1) instead of `/dashboard`; the app shell sidebar is not shown — a clean centered card layout on a Paper background is used instead; a skip link is available.

2. **Given** Step 1 of onboarding renders, **When** the page loads, **Then** it shows: Playfair Display H1 "Who are you writing for?"; body text "A Client is the brand voice you're building. Start with yours."; a required "Client name" field; an optional "Website URL" field with label "Recommended — for automatic voice setup"; primary CTA "Create client and analyze voice"; skip link below the CTA: "Skip for now — I'll set this up later."

3. **Given** the user submits Step 1 with a website URL, **When** "Create client and analyze voice" is clicked, **Then** a client is created, an ingestion job is created and dispatched (as per Story 2.1), and Step 2 loads showing the ingestion-in-progress state: "Scraping [url]..." → "Extracting voice profile..." in JetBrains Mono; when extraction completes, the extracted Brand Voice Profile fields are shown for review.

4. **Given** the user submits Step 1 without a website URL, **When** "Create client and analyze voice" is clicked, **Then** the client is created (no ingestion dispatched) and Step 2 loads showing the voice questionnaire (as per Story 2.5) instead of the ingestion progress state.

5. **Given** Step 2 of onboarding renders, **When** the page loads, **Then** a progress indicator shows "2 of 3" at the top; a skip link reads "Skip — I'll refine this later" which advances to Step 3 with the profile flagged as incomplete.

6. **Given** Step 3 of onboarding renders, **When** the page loads, **Then** it shows: progress indicator "3 of 3"; Playfair H2 "What's on your mind this week?"; subtext "Paste anything — bullet points, half-formed thoughts, a topic title. PersonnaPress will do the rest."; the Brain Dump textarea (full width, JetBrains Mono, min 200px height); primary CTA "Generate my first campaign"; skip link "I'll write my first draft later" which navigates to `/dashboard` with a "Complete your first campaign" nudge card. **And** submitting the Brain Dump in Step 3 triggers the same campaign creation flow as Epic 3 Story 3.1; Step 3 submission integration is wired in Epic 3 Story 3.5 — this story implements the onboarding shell and Step 3 UI only.

7. **Given** a user clicks any skip link, **When** they are taken to the next step or Dashboard, **Then** the skipped step does not block future access — brand voice setup and brain dump remain accessible from the Client detail page and Dashboard at any time.

8. **Given** a returning user (not their first login) visits `/onboarding`, **When** the route is accessed, **Then** Next.js middleware redirects them to `/dashboard` — the onboarding flow is shown exactly once per account.

9. **Given** the onboarding layout, **When** it renders at any step, **Then** the page uses a centered card layout (no sidebar, no top bar navigation) on a Paper (#F9F9F6) background; the card is `max-w-lg w-full mx-auto`; Paper Style design tokens apply throughout; all buttons and inputs follow the same Paper Style specs as the rest of the app.

10. **Given** the onboarding flow completes (Step 3 brain dump submitted or all steps skipped to Dashboard), **When** `users.onboarding_completed` is set to `true`, **Then** subsequent logins redirect to `/dashboard` instead of `/onboarding`.

## Tasks / Subtasks

- [x] Task 1: Backend — `users.onboarding_completed` field (AC: #8, #10)
  - [x] 1.1 Create a new Alembic migration: `alembic revision --autogenerate -m "add_onboarding_completed_to_users"`
  - [x] 1.2 Add `onboarding_completed: bool = Field(default=False)` to the `User` SQLModel in `backend/app/models/user.py`
  - [x] 1.3 Verify migration SQL: `ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE;`
  - [x] 1.4 Update `JWT` payload to include `onboarding_completed: bool` — re-issue the JWT with this field after registration so Next.js middleware can read it without a round-trip

- [x] Task 2: Backend — `POST /api/v1/auth/complete-onboarding` endpoint (AC: #10)
  - [x] 2.1 Add `POST /api/v1/auth/complete-onboarding` to `backend/app/routers/auth.py`; require auth
  - [x] 2.2 Set `users.onboarding_completed = True` via `db/repositories/users.py`
  - [x] 2.3 Re-issue JWT cookie with `onboarding_completed=True` in payload so middleware reflects the change on next request
  - [x] 2.4 Return HTTP 200 `{"status": "ok"}`
  - [x] 2.5 This endpoint is called by the frontend when: (a) Step 3 Brain Dump is submitted, (b) the user clicks "I'll write my first draft later" on Step 3, or (c) the user uses the top-level "Skip for now" on Step 1

- [x] Task 3: Backend — update JWT payload (AC: #8)
  - [x] 3.1 In `backend/app/core/security.py` (or wherever JWT is issued): add `onboarding_completed` to the payload from the `users` record
  - [x] 3.2 This allows Next.js middleware to check `onboarding_completed` from the JWT without a DB round-trip on every request

- [x] Task 4: Frontend — Next.js middleware — onboarding redirect (AC: #1, #8)
  - [x] 4.1 Update `frontend/middleware.ts` (Story 1.3): after validating the JWT, check `payload.onboarding_completed`
  - [x] 4.2 If `onboarding_completed === false` and the requested path is NOT `/onboarding` and NOT a public/auth route: redirect to `/onboarding`
  - [x] 4.3 If `onboarding_completed === true` and the requested path IS `/onboarding`: redirect to `/dashboard`
  - [x] 4.4 The middleware already uses `jose` for edge-runtime JWT verification — read `onboarding_completed` from the same decoded payload

- [x] Task 5: Frontend — `/onboarding` route and layout (AC: #1, #9)
  - [x] 5.1 Create `frontend/app/onboarding/page.tsx` — Server Component with metadata `title: "Welcome — PersonnaPress"`
  - [x] 5.2 This route is in the **root** app directory (NOT inside the `(app)/` group) — it does not use the sidebar app shell layout
  - [x] 5.3 Create `frontend/app/onboarding/layout.tsx` with no sidebar, no top bar; full-page Paper (#F9F9F6) background
  - [x] 5.4 Create `frontend/components/onboarding/OnboardingFlow.tsx` — `'use client'` with `currentStep: 1 | 2 | 3` state, `createdClientId: string | null`, `jobId: string | null`

- [x] Task 6: Frontend — Onboarding Step 1 (AC: #2, #4, #7)
  - [x] 6.1 In `OnboardingFlow.tsx`, render Step 1 UI when `currentStep === 1` with Playfair H1, body text, centered card without brutalist shadow
  - [x] 6.2 Form fields: "Client name" (required, Paper Style standard input); "Website URL" (optional, with helper text "Recommended — for automatic voice setup" in Graphite)
  - [x] 6.3 Primary Button: "Create client and analyze voice" — calls `POST /api/v1/clients`; advances to Step 2
  - [x] 6.4 Client-side validation: if `name.trim() === ''`, show inline "Client name is required." before calling API
  - [x] 6.5 Skip link: calls `POST /api/v1/auth/complete-onboarding`, then navigates to `/dashboard`

- [x] Task 7: Frontend — Onboarding Step 2 (AC: #3, #4, #5)
  - [x] 7.1 Render Step 2 with progress indicator "2 of 3" and same centered card layout
  - [x] 7.2 If `jobId` is set: render ingestion in-progress with polling; on complete show inline BVP review; on failed show questionnaire
  - [x] 7.3 If `jobId` is null (no URL): render embedded VoiceQuestionnaire component
  - [x] 7.4 Skip link: advances to Step 3 without API call

- [x] Task 8: Frontend — Onboarding Step 3 (AC: #6, #7)
  - [x] 8.1 Render Step 3 with progress "3 of 3", Playfair H2, subtext, BrainDumpInput, character counter, disabled CTA below 20 chars
  - [x] 8.2 Submit handler calls `complete-onboarding` and navigates to `/dashboard/new?prefill={encodedBrainDump}`
  - [x] 8.3 Skip link: calls `complete-onboarding`; navigates to `/dashboard?nudge=true`
  - [x] 8.4 Esc key: does nothing (prevents accidental textarea clear)
  - [x] 8.5 Enter key: inserts newline; Cmd/Ctrl+Enter submits

- [x] Task 9: Frontend — Dashboard nudge card (AC: #6)
  - [x] 9.1 In `frontend/app/(app)/dashboard/page.tsx`: check `?nudge=true` URL param and `campaigns.length === 0`
  - [x] 9.2 Show `NudgeCard` at top: "Complete your first campaign.", "New Campaign" button → `/campaigns/new`
  - [x] 9.3 Nudge card styling: white, 1px border, no shadow, Inter body text

- [x] Task 10: Frontend — returning user guard and accessibility (AC: #8, #9)
  - [x] 10.1 middleware.ts guards `/onboarding` for returning users (JWT `onboarding_completed=true`) → redirect to `/dashboard`
  - [x] 10.2 All form fields have visible `<label>` elements; error messages use `aria-describedby`
  - [x] 10.3 No focus trap — users Tab freely; logical tab order
  - [x] 10.4 Skip links use `<button>` elements for keyboard accessibility
  - [ ] 10.4 The skip link is a focusable `<a>` or `<button>` element — not a plain `<span>` — so keyboard users can reach it without a mouse

## Dev Notes

### Onboarding Layout — Paper Style

The onboarding card floats without the brutalist shadow — this is intentional. The shadow is a spatial signal for interactive elements (cards that navigate, buttons that act). The onboarding card is a container, not an interactive element itself.

```
(full Paper #F9F9F6 background, no sidebar, no top bar)

                Who are you writing for?
                (Playfair Display H1, Ink)

         A Client is the brand voice you're building.
              Start with yours.
              (Inter 15px, Graphite)

   ┌──────────────────────────────────────────┐
   │                                          │
   │  CLIENT NAME                             │
   │  [                                    ]  │
   │                                          │
   │  WEBSITE URL                             │
   │  Recommended — for automatic voice setup │
   │  [                                    ]  │
   │                                          │
   │  [   Create client and analyze voice  ]  │
   │                                          │
   │     Skip for now — I'll set this up      │
   │                    later.                │
   │                                          │
   └──────────────────────────────────────────┘
```

### Step 2 — Progress + Ingestion In Progress

```
2 of 3          ← Inter 12px uppercase tracked, Graphite
                  (top of card, no separate heading)

   ┌──────────────────────────────────────────┐
   │                                          │
   │  Scraping acmecorp.com...                │
   │  (JetBrains Mono, Graphite, pulsing)     │
   │                                          │
   │     (transitions to:)                    │
   │                                          │
   │  Extracting voice profile...             │
   │  (JetBrains Mono, Graphite, pulsing)     │
   │                                          │
   └──────────────────────────────────────────┘

   Skip — I'll refine this later.     ← text link below card
```

### Step 3 — Brain Dump in Onboarding

```
3 of 3          ← Inter 12px uppercase tracked, Graphite

        What's on your mind this week?
        (Playfair H2, Ink, centered)

   Paste anything — bullet points, half-formed
   thoughts, a topic title. PersonnaPress will do
   the rest.  (Inter 15px, Graphite, centered)

   ┌──────────────────────────────────────────┐
   │                                          │
   │ (JetBrains Mono, auto-expanding textarea │
   │  min 200px height, bottom-border only)   │
   │                                          │
   │                                          │
   └──────────────────────────────────────────┘
   0 / 10,000 characters   ← Inter 12px, Graphite

   [    Generate my first campaign    ]   ← Primary Button (disabled < 20 chars)

   I'll write my first draft later.   ← text link
```

### onboarding_completed Flow

```
User registers → JWT issued with onboarding_completed=false
  ↓
middleware: onboarding_completed=false + path != /onboarding → redirect /onboarding
  ↓
User completes or skips all 3 steps
  ↓
Frontend calls POST /api/v1/auth/complete-onboarding
  ↓
Backend: users.onboarding_completed=true; re-issues JWT cookie with updated payload
  ↓
Next request: middleware reads onboarding_completed=true → no redirect
```

### Step 3 Brain Dump Integration (Story 3.5 Note)

This story (2.7) implements Step 3 UI with a **stub submit handler**. The actual campaign creation is wired in Epic 3 Story 3.5 which:
- Calls `POST /api/v1/campaigns` with the brain dump text and `createdClientId`
- Navigates to the typewriter generation state at `/campaigns/{id}`

For Story 2.7, the "Generate my first campaign" button calls `complete-onboarding` and navigates to `/dashboard/new` with a pre-filled brain dump in URL state. Story 3.5 will refactor this to the full campaign creation.

### localStorage — `hasCompletedOnboarding` as Signal

Do NOT store `onboarding_completed` in localStorage — it's authoritative in the JWT and DB. localStorage is only used for `activeClientId` (Story 2.3). The middleware's JWT check is the single source of truth for the onboarding gate.

### New Files This Story

```
backend/alembic/versions/XXXX_add_onboarding_completed_to_users.py ← NEW migration
frontend/app/onboarding/page.tsx         ← NEW
frontend/app/onboarding/layout.tsx       ← NEW
frontend/components/onboarding/OnboardingFlow.tsx ← NEW
```

Updated files:
```
backend/app/models/user.py              ← ADD onboarding_completed field
backend/app/routers/auth.py             ← ADD POST /complete-onboarding
backend/app/core/security.py            ← ADD onboarding_completed to JWT payload
frontend/middleware.ts                  ← ADD onboarding redirect guard
frontend/app/(app)/dashboard/page.tsx   ← ADD nudge card
```

### References

- Story spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7]
- UX-DR11 (3-step Onboarding Flow full spec — centered card, no sidebar, skip links, steps): [Source: _bmad-output/planning-artifacts/epics.md#UX Design Requirements]
- AR-6 (`jose` for edge-runtime middleware JWT verification): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- Brain Dump textarea rules (Enter ≠ submit, Esc does nothing, Cmd+Enter submits): [Source: _bmad-output/planning-artifacts/epics.md#UX-DR23]
- Story 3.5 (Brain Dump campaign creation wiring, deferred to Epic 3): [Source: _bmad-output/planning-artifacts/epics.md#Story 3.5]
- Paper Style microcopy (no exclamation marks, sentence case CTAs): [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]
- WCAG labels and focus: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR16]
- Playfair H1/H2 only rule: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Typography]

## Dev Agent Record

### Implementation Plan
- Backend: added `onboarding_completed` field to `User` SQLModel; Alembic migration with `server_default=false`; updated `create_session_token` signature with `onboarding_completed` kwarg; updated `_issue_session` and `login_user` to pass the flag; added `complete_onboarding` service function that sets flag, commits, and re-issues JWT; added endpoint `POST /auth/complete-onboarding` requiring auth
- Frontend middleware: created `frontend/middleware.ts` using `jose@6 jwtVerify`; guards `/onboarding` (returning users redirect to `/dashboard`) and all protected routes (new users redirect to `/onboarding`); public paths include `/login`, `/register`, `/verify-email`, `/api/`, `/_next/`
- Frontend onboarding: created `frontend/app/onboarding/layout.tsx` (no sidebar, Paper bg); `frontend/app/onboarding/page.tsx` (Server Component); `frontend/components/onboarding/OnboardingFlow.tsx` with full 3-step wizard; Step 2 uses `useJobStatus` polling + `VoiceQuestionnaire` reuse + inline BVP review; Step 3 uses `BrainDumpInput` with Cmd+Enter submit, Esc prevention, 10k limit
- Dashboard: added `NudgeCard` component; dashboard `page.tsx` accepts `searchParams` (Promise) and conditionally renders nudge when `?nudge=true` and no campaigns
- Tests: updated `_User` fixture in `test_auth_login.py` to include `onboarding_completed`; added `tests/test_complete_onboarding.py` (3 tests covering 404, 200+cookie, JWT payload)

### Completion Notes
All 10 tasks and all subtasks complete. 137 backend tests pass (3 new). TypeScript type-checks clean. Pre-existing failure in `test_client_limit.py` is unrelated to this story.

## File List
- `backend/alembic/versions/d4e9f1a02b3c_add_onboarding_completed_to_users.py` (new)
- `backend/app/db/repositories/models.py` (modified — added `onboarding_completed` to User)
- `backend/app/core/security.py` (modified — added `onboarding_completed` param to `create_session_token`)
- `backend/app/services/auth_service.py` (modified — updated `_issue_session`, `login_user`; added `complete_onboarding`)
- `backend/app/routers/auth.py` (modified — added `POST /complete-onboarding` endpoint)
- `backend/tests/test_auth_login.py` (modified — added `onboarding_completed` to `_User` fixture)
- `backend/tests/test_complete_onboarding.py` (new)
- `frontend/middleware.ts` (new)
- `frontend/app/onboarding/layout.tsx` (new)
- `frontend/app/onboarding/page.tsx` (new)
- `frontend/components/onboarding/OnboardingFlow.tsx` (new)
- `frontend/app/(app)/dashboard/NudgeCard.tsx` (new)
- `frontend/app/(app)/dashboard/page.tsx` (modified — added NudgeCard and searchParams)
- `frontend/lib/api.ts` (modified — added `authApi.completeOnboarding`)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — story status updated)

### Review Findings

- [x] [Review][Patch] completeOnboarding best-effort swallows error — stale JWT traps user on hard reload [frontend/components/onboarding/OnboardingFlow.tsx:253-324]
- [x] [Review][Patch] handleStep3Submit loading state never resets — button stuck disabled on nav failure [frontend/components/onboarding/OnboardingFlow.tsx:305-314]
- [x] [Review][Patch] Step2Content currentView state desync when view prop changes after mount [frontend/components/onboarding/OnboardingFlow.tsx:151]
- [x] [Review][Patch] Middleware /onboarding exact-match should use startsWith for future sub-routes [frontend/middleware.ts:41,48]
- [x] [Review][Patch] isPublic "/favicon" prefix too broad — should match /favicon.ico exactly [frontend/middleware.ts:15]
- [x] [Review][Patch] db.refresh after commit is unnecessary — user fields already in memory [backend/app/services/auth_service.py:210]
- [x] [Review][Patch] step===2 && !createdClientId falls through silently to Step 3 UI [frontend/components/onboarding/OnboardingFlow.tsx:431]
- [x] [Review][Patch] ?nudge=true persists in browser URL — clean up client-side after render [frontend/app/(app)/dashboard/NudgeCard.tsx]
- [x] [Review][Defer] Old JWT token remains valid until expiry in multi-tab scenario [backend/app/services/auth_service.py] — deferred, stateless JWT inherent limitation; requires session store to fix
- [x] [Review][Defer] Dashboard server component fetches without forwarded cookies [frontend/app/(app)/dashboard/page.tsx] — deferred, pre-existing architecture (same-network design intent)
- [x] [Review][Defer] Brain dump URL length limit (max 30KB encoded) [frontend/components/onboarding/OnboardingFlow.tsx:312] — deferred, stub routing replaced in Story 3.5

## Change Log
- 2026-07-01: Implemented Story 2.7 — 3-step onboarding flow with backend `onboarding_completed` field, JWT flag, complete-onboarding endpoint, Next.js middleware redirect guard, full Step 1/2/3 wizard, and dashboard nudge card
