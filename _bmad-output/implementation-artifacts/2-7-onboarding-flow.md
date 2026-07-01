# Story 2.7: 3-Step Onboarding Flow

Status: ready

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

- [ ] Task 1: Backend — `users.onboarding_completed` field (AC: #8, #10)
  - [ ] 1.1 Create a new Alembic migration: `alembic revision --autogenerate -m "add_onboarding_completed_to_users"`
  - [ ] 1.2 Add `onboarding_completed: bool = Field(default=False)` to the `User` SQLModel in `backend/app/models/user.py`
  - [ ] 1.3 Verify migration SQL: `ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE;`
  - [ ] 1.4 Update `JWT` payload to include `onboarding_completed: bool` — re-issue the JWT with this field after registration so Next.js middleware can read it without a round-trip

- [ ] Task 2: Backend — `POST /api/v1/auth/complete-onboarding` endpoint (AC: #10)
  - [ ] 2.1 Add `POST /api/v1/auth/complete-onboarding` to `backend/app/routers/auth.py`; require auth
  - [ ] 2.2 Set `users.onboarding_completed = True` via `db/repositories/users.py`
  - [ ] 2.3 Re-issue JWT cookie with `onboarding_completed=True` in payload so middleware reflects the change on next request
  - [ ] 2.4 Return HTTP 200 `{"status": "ok"}`
  - [ ] 2.5 This endpoint is called by the frontend when: (a) Step 3 Brain Dump is submitted, (b) the user clicks "I'll write my first draft later" on Step 3, or (c) the user uses the top-level "Skip for now" on Step 1

- [ ] Task 3: Backend — update JWT payload (AC: #8)
  - [ ] 3.1 In `backend/app/core/security.py` (or wherever JWT is issued): add `onboarding_completed` to the payload from the `users` record
  - [ ] 3.2 This allows Next.js middleware to check `onboarding_completed` from the JWT without a DB round-trip on every request

- [ ] Task 4: Frontend — Next.js middleware — onboarding redirect (AC: #1, #8)
  - [ ] 4.1 Update `frontend/middleware.ts` (Story 1.3): after validating the JWT, check `payload.onboarding_completed`
  - [ ] 4.2 If `onboarding_completed === false` and the requested path is NOT `/onboarding` and NOT a public/auth route: redirect to `/onboarding`
  - [ ] 4.3 If `onboarding_completed === true` and the requested path IS `/onboarding`: redirect to `/dashboard`
  - [ ] 4.4 The middleware already uses `jose` for edge-runtime JWT verification — read `onboarding_completed` from the same decoded payload

- [ ] Task 5: Frontend — `/onboarding` route and layout (AC: #1, #9)
  - [ ] 5.1 Create `frontend/app/onboarding/page.tsx` — Server Component with metadata `title: "Welcome — PersonnaPress"`
  - [ ] 5.2 This route is in the **root** app directory (NOT inside the `(app)/` group) — it does not use the sidebar app shell layout
  - [ ] 5.3 Create `frontend/app/onboarding/layout.tsx` with no sidebar, no top bar; full-page Paper (#F9F9F6) background:
    ```tsx
    // frontend/app/onboarding/layout.tsx
    export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
      return (
        <div className="min-h-screen bg-[#F9F9F6] flex items-start justify-center pt-16 px-4">
          {children}
        </div>
      )
    }
    ```
  - [ ] 5.4 Create `frontend/components/onboarding/OnboardingFlow.tsx` — `'use client'` with `currentStep: 1 | 2 | 3` state, `createdClientId: string | null`, `jobId: string | null`

- [ ] Task 6: Frontend — Onboarding Step 1 (AC: #2, #4, #7)
  - [ ] 6.1 In `OnboardingFlow.tsx`, render Step 1 UI when `currentStep === 1`:
    - Centered card: `<div className="bg-white border border-[#E5E5E5] p-8 w-full max-w-lg">`
    - No hard shadow on the onboarding card — it floats on Paper background without the brutalist shadow (the shadow is for interactive cards)
    - Playfair Display H1: `<h1 className="font-['Playfair_Display'] text-[2.25rem] font-bold leading-[1.15] tracking-[-0.01em] text-[#111111] mb-2">Who are you writing for?</h1>`
    - Body text: `<p className="text-[0.9375rem] text-[#555555] leading-[1.6] mb-8">A Client is the brand voice you're building. Start with yours.</p>`
  - [ ] 6.2 Form fields: "Client name" (required, Paper Style standard input); "Website URL" (optional, with helper text "Recommended — for automatic voice setup" in Graphite)
  - [ ] 6.3 Primary Button: "Create client and analyze voice" — calls `POST /api/v1/clients` with `{name, website_url}` on submit; on success: set `createdClientId`, set `jobId` (if URL provided), advance `currentStep` to 2
  - [ ] 6.4 Client-side validation: if `name.trim() === ''`, show inline "Client name is required." before calling API
  - [ ] 6.5 Skip link: `<a href="#" onClick={handleSkipAll} className="block text-center text-sm text-[#555555] mt-4 hover:text-[#111111] underline">Skip for now — I'll set this up later.</a>` → calls `POST /api/v1/auth/complete-onboarding`, then navigates to `/dashboard`

- [ ] Task 7: Frontend — Onboarding Step 2 (AC: #3, #4, #5)
  - [ ] 7.1 Render Step 2 when `currentStep === 2`:
    - Progress indicator: `<p className="text-xs font-medium uppercase tracking-[0.06em] text-[#555555] mb-6">2 of 3</p>`
    - Same centered card layout
  - [ ] 7.2 If `jobId` is set (URL was provided in Step 1): render ingestion in-progress UI — poll `useJobStatus(jobId)`:
    - While `pending` or `in_progress`: show JetBrains Mono status — "Scraping [url]..." cycling to "Extracting voice profile..." via local interval
    - On `complete`: show inline Profile Review (editable BVP fields, confirm CTA) within the Step 2 card; "Confirm profile" → set step 2 as complete, advance to Step 3
    - On `failed`: show error + voice questionnaire embedded in Step 2 card
  - [ ] 7.3 If `jobId` is null (no URL): render embedded voice questionnaire wizard (reuse `VoiceQuestionnaire` component from Story 2.5); on questionnaire submit + job complete: advance to Step 3
  - [ ] 7.4 Skip link: `<a href="#" onClick={handleSkipStep2} className="block text-center text-sm text-[#555555] mt-4 underline">Skip — I'll refine this later.</a>` → set `currentStep` to 3; no API call (BVP remains null/incomplete)

- [ ] Task 8: Frontend — Onboarding Step 3 (AC: #6, #7)
  - [ ] 8.1 Render Step 3 when `currentStep === 3`:
    - Progress: "3 of 3"
    - Playfair H2: `<h2 className="font-['Playfair_Display'] text-[1.5rem] font-bold ...">What's on your mind this week?</h2>`
    - Subtext: "Paste anything — bullet points, half-formed thoughts, a topic title. PersonnaPress will do the rest." (Inter, Graphite)
    - Full-width Brain Dump textarea: JetBrains Mono, bottom-border only, `minHeight: '200px'`, auto-expanding, character counter "N / 10,000 characters"
    - Primary Button "Generate my first campaign": disabled below 20-character minimum — **Note:** actual campaign creation wired in Story 3.5; in this story, the button navigates to `/dashboard/new` after calling `complete-onboarding`, OR if Story 3.5 is done, it creates the campaign directly
  - [ ] 8.2 Submit handler (Story 2.7 stub — wired fully in Epic 3 Story 3.5):
    - Call `POST /api/v1/auth/complete-onboarding` to mark onboarding done
    - Navigate to `/dashboard/new?prefill={encodedBrainDump}` so Epic 3 Story 3.5 can pick up the prefilled text
  - [ ] 8.3 Skip link: "I'll write my first draft later" → call `POST /api/v1/auth/complete-onboarding`; navigate to `/dashboard`; the nudge card on the Dashboard (Task 9) appears
  - [ ] 8.4 Esc key behavior: same as main Brain Dump (does nothing — prevents accidental textarea clear)
  - [ ] 8.5 Enter key: inserts newline (no submit on Enter); Cmd/Ctrl+Enter submits

- [ ] Task 9: Frontend — Dashboard nudge card (AC: #6)
  - [ ] 9.1 In `frontend/app/(app)/dashboard/page.tsx`: check `useClientStore.clients.length > 0 && hasNoCompletedCampaigns` (or a URL param `?nudge=true` set by the onboarding skip redirect)
  - [ ] 9.2 Show nudge card at the top of campaign list: Paper Style default card, text "Complete your first campaign.", "New Campaign" Secondary Button → `/dashboard/new`; the nudge card is shown until the user creates their first campaign, then removed (check `campaigns.length > 0`)
  - [ ] 9.3 Nudge card styling: Paper Style default card (white, 1px border, no shadow), Inter body text, no Highlighter or accent colors

- [ ] Task 10: Frontend — returning user guard and accessibility (AC: #8, #9)
  - [ ] 10.1 The `/onboarding` route is protected by `middleware.ts` (Task 4) — returning users (JWT `onboarding_completed=true`) are redirected to `/dashboard` before the page renders
  - [ ] 10.2 All form fields in onboarding have visible `<label>` elements (not placeholder-only); error messages associated via `aria-describedby`
  - [ ] 10.3 The onboarding layout has no focus trap — users can Tab freely; Tab order is logical (title → body → inputs → CTA → skip link)
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
