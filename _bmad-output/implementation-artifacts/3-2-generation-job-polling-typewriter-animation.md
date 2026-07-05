---
baseline_commit: bd14667d840c82d29ddd3482975e749fa9961847
---

# Story 3.2: Generation Job Polling & Typewriter Animation

Status: done

## Story

As an authenticated user,
I want to see real-time visual feedback while my content is being generated,
So that I know the system is working and can follow the progress through each stage of the pipeline.

## Acceptance Criteria

1. **Given** the user lands on `/campaigns/{id}` while the campaign's job status is `pending` or `in_progress`, **When** the page renders, **Then** the full content area is occupied by the typewriter animation component: character-by-character text reveal in JetBrains Mono on a Paper background; a status message line below cycles through: "Analyzing your voice profile..." → "Drafting blog post..." → "Checking voice fidelity..." → "Generating featured image..." → "Done." with each message appearing as the pipeline advances.

2. **Given** the typewriter animation is running, **When** rendered for screen readers, **Then** the character-reveal animation has `aria-hidden="true"`; the status message line has `aria-live="polite"` so each new status message is announced.

3. **Given** `prefers-reduced-motion` is enabled in the OS, **When** the generation state is active, **Then** the typewriter character-reveal animation is replaced by a simple "Generating..." static label with a pulsing opacity animation only — no character-by-character reveal.

4. **Given** React Query is polling the job status endpoint, **When** the generation page is open, **Then** the `useJobStatus` hook calls `GET /api/v1/jobs/{job_id}` with `refetchInterval: 2000` while `job.status` is `'pending'` or `'in_progress'`; polling stops automatically when `job.status` reaches a terminal state (`'complete'` or `'failed'`).

5. **Given** the job reaches `status='complete'`, **When** the polling detects the terminal state, **Then** React Query invalidates the `["campaign", campaignId]` query key; the Approval Gate content (blog preview, social posts, image) loads in place of the typewriter animation (Approval Gate UI implemented in Epic 4 — for now the existing static campaign page renders).

6. **Given** the job reaches `status='failed'`, **When** the polling detects failure, **Then** the typewriter animation is replaced by an error state showing the `error_details` message (e.g., "Generation service temporarily unavailable.") with a "Retry generation" primary button that re-submits the same Brain Dump text to create a new Campaign and job (calls `POST /api/v1/campaigns` with the original `brain_dump` text and `client_id`).

7. **Given** the user attempts to navigate away from the generation page while polling is active, **When** they click a nav link or the browser back button, **Then** a confirmation dialog appears: "Generation is in progress. Leaving will not cancel it — your draft will be available on the Dashboard when complete." with "Stay on page" and "Leave" options; if they choose Leave, navigation proceeds and polling stops on this page, but the job continues server-side.

8. **Given** no `job_id` is available in the URL query params and the campaign status is terminal (`complete`/`failed`/`published`/`rejected`), **When** the page loads, **Then** the typewriter overlay is NOT shown — the page renders the existing static campaign content directly.

9. **Given** the `/campaigns/new` page navigates to `/campaigns/{id}?job_id={jobId}`, **When** the campaign page loads with a `job_id` query param, **Then** polling begins immediately using that `job_id` without requiring an additional fetch to discover it.

## Tasks / Subtasks

- [x] Task 1: Frontend — `useJobStatus` React Query hook (AC: #4, #5, #6)
  - [x] 1.1 Create `frontend/hooks/useJobStatus.ts` (or `frontend/lib/hooks/useJobStatus.ts`) using `useQuery` from `@tanstack/react-query`
  - [x] 1.2 Query key: `["job", jobId]`; query function: `jobsApi.get(jobId)` (already in `lib/api.ts`)
  - [x] 1.3 `refetchInterval`: return `2000` (2s) when `data?.status === 'pending' || data?.status === 'in_progress'`; return `false` at all other statuses (terminal states `complete`/`failed`) — this stops polling automatically
  - [x] 1.4 `enabled`: only run when `jobId` is a non-null, non-empty string
  - [x] 1.5 Return: `{ job, isPolling, error }` — `isPolling` is `true` when status is pending/in_progress

- [x] Task 2: Frontend — `TypewriterAnimation` component (AC: #1, #2, #3)
  - [x] 2.1 Create `frontend/components/campaigns/TypewriterAnimation.tsx` as `'use client'`
  - [x] 2.2 Props: `{ statusMessages: string[]; currentMessageIndex: number; isComplete: boolean }`
  - [x] 2.3 Typewriter effect: use a `useEffect` with `setInterval` to reveal characters one at a time from the current status message string; character reveal runs at ~35ms per character; when message is fully revealed, hold for 800ms then `onMessageComplete()` is called by parent to advance to next message index
  - [x] 2.4 The animated text display element: `aria-hidden="true"` on the character-reveal span; use JetBrains Mono (`font-mono text-sm`), Paper background, Graphite color
  - [x] 2.5 Status message line: `role="status" aria-live="polite"` — displays the full current message (not the character-by-character one); this is what screen readers announce; visually hidden via `sr-only` or positioned off-screen
  - [x] 2.6 `prefers-reduced-motion` support: use `window.matchMedia('(prefers-reduced-motion: reduce)')` in a `useEffect`; if true, skip character-reveal and show static "Generating..." label with `animate-pulse` opacity only; the `aria-live` status messages still cycle normally
  - [x] 2.7 Visual layout: centered vertically within the content area using flexbox; full content area height (use `min-h-[400px]` or fill available space)

- [x] Task 3: Frontend — `GenerationStatusMessages` — message cycling logic (AC: #1)
  - [x] 3.1 Define the message sequence as a constant: `["Analyzing your voice profile...", "Drafting blog post...", "Checking voice fidelity...", "Generating featured image...", "Done."]`
  - [x] 3.2 Map job status to message index: `pending` → index 0; `in_progress` → advance through indices 1-3 on a timed basis (cycle every ~15 seconds within `in_progress` to show progress); `complete` → index 4 ("Done."); messages should NOT jump backwards
  - [x] 3.3 The message progression is time-based for `in_progress` (since the backend doesn't emit fine-grained stage signals) — start at index 1 when `in_progress` begins, advance every 15s until terminal state

- [x] Task 4: Frontend — `CampaignGenerationOverlay` compound component (AC: #1, #5, #6, #7)
  - [x] 4.1 Create `frontend/components/campaigns/CampaignGenerationOverlay.tsx` as `'use client'`
  - [x] 4.2 Props: `{ campaignId: string; jobId: string; brainDump: string; clientId: string }`
  - [x] 4.3 Compose `useJobStatus` + `TypewriterAnimation` + message cycling from Task 3
  - [x] 4.4 On job complete: call `queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] })` to trigger re-fetch of campaign data; set local `isGenerationComplete = true` state to hide overlay and show campaign content
  - [x] 4.5 On job failed: stop polling; render error state — Paper-style error card showing `job.error_details ?? "Generation service temporarily unavailable."` with a "Retry generation" primary Button; Retry handler calls `campaignsApi.create({ client_id: clientId, brain_dump: brainDump })` and navigates to the new campaign page
  - [x] 4.6 Navigate-away guard: use the `useBeforeUnload` pattern — add an event listener for `beforeunload` that returns a confirmation message string (browser-native dialog); also intercept Next.js router navigation using `useEffect` + `router.events` or `usePathname` change detection; show the Paper-style confirmation dialog: "Generation is in progress. Leaving will not cancel it — your draft will be available on the Dashboard when complete." with "Stay on page" (primary) and "Leave" (secondary) buttons; remove the guard when job reaches a terminal state

- [x] Task 5: Frontend — Update `/campaigns/[id]/page.tsx` to support generation overlay (AC: #5, #8, #9)
  - [x] 5.1 The current `page.tsx` is an RSC (Server Component). The generation overlay requires client-side polling. Create a new `frontend/app/(app)/campaigns/[id]/GenerationGate.tsx` as `'use client'` that:
    - Accepts `campaign: Campaign` and `jobId: string | null` as props
    - If `jobId` is non-null AND campaign status is pending/in_progress: render `CampaignGenerationOverlay`
    - Else: render `null` (campaign content is shown by the RSC parent)
  - [x] 5.2 In the RSC `page.tsx`, read the `job_id` query param from `searchParams` (Promise<{ id: string }> & { searchParams: Promise<{ job_id?: string }> }`)
  - [x] 5.3 Pass `jobId` from search params to `GenerationGate` component; `GenerationGate` is shown at the top of the page — it occupies full content area when overlay is active, hides otherwise
  - [x] 5.4 `GenerationGate` also needs `brainDump` and `clientId` from the campaign data to support the "Retry generation" action — pass from RSC

- [x] Task 6: Frontend tests (AC: #4)
  - [x] 6.1 Unit test `useJobStatus`: polling stops at terminal state; `refetchInterval` returns `false` when status is `complete`
  - [x] 6.2 Unit test `TypewriterAnimation`: characters appear over time; `prefers-reduced-motion` shows static text; `aria-live` region updates on message change

## Dev Notes

### Architecture Decision: RSC + Client Island

The `/campaigns/[id]/page.tsx` is correctly an RSC (Server Component) that fetches campaign data on the server. The typewriter overlay must be a Client Component for React Query polling. The solution is the `GenerationGate.tsx` island pattern:

```
page.tsx (RSC)
  ↓ fetches campaign data server-side
  ↓ reads jobId from searchParams
  ├── GenerationGate.tsx ('use client') ← overlay when generating
  │     ├── useJobStatus hook (React Query polling)
  │     ├── TypewriterAnimation
  │     └── CampaignGenerationOverlay
  └── Static campaign content (rendered by RSC, shown when overlay is hidden)
```

The RSC fetches the initial campaign state; the client island polls for job progress. When the job completes, `queryClient.invalidateQueries(["campaign", campaignId])` triggers a refetch via React Query's `useQuery` for the campaign — but since the page is an RSC, the overlay should instead simply set local state to hide itself and reload the page with `router.refresh()` to get fresh server-rendered campaign data.

**Revised approach:** When job reaches `complete`, call `router.refresh()` (from `next/navigation`) to trigger the RSC to re-fetch the campaign with full content. This is simpler than duplicating the campaign fetch in client state.

### TypewriterAnimation Implementation Pattern

```tsx
// Character-by-character reveal using useEffect + setInterval
const [displayedText, setDisplayedText] = useState('');
const [charIndex, setCharIndex] = useState(0);
const message = statusMessages[currentMessageIndex] ?? '';

useEffect(() => {
  if (prefersReducedMotion) return; // skip reveal for reduced motion
  setDisplayedText('');
  setCharIndex(0);
}, [currentMessageIndex, prefersReducedMotion]);

useEffect(() => {
  if (prefersReducedMotion) return;
  if (charIndex >= message.length) return; // fully revealed
  const timer = setTimeout(() => {
    setDisplayedText(message.slice(0, charIndex + 1));
    setCharIndex(c => c + 1);
  }, 35); // 35ms per character
  return () => clearTimeout(timer);
}, [charIndex, message, prefersReducedMotion]);
```

### Prefers-Reduced-Motion Detection

```tsx
const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
// or inline:
const prefersReducedMotion = typeof window !== 'undefined'
  ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
  : false;
```

Use a `useEffect` + `useState` pattern to avoid SSR/hydration mismatch:
```tsx
const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
useEffect(() => {
  const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  setPrefersReducedMotion(mq.matches);
  const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
  mq.addEventListener('change', handler);
  return () => mq.removeEventListener('change', handler);
}, []);
```

### Navigate-Away Guard Implementation

Next.js App Router does not expose `router.events` like Pages Router. Use the following approach:

```tsx
// Browser tab close / reload guard
useEffect(() => {
  if (!isPolling) return;
  const handler = (e: BeforeUnloadEvent) => {
    e.preventDefault();
    e.returnValue = ''; // shows browser's native dialog
  };
  window.addEventListener('beforeunload', handler);
  return () => window.removeEventListener('beforeunload', handler);
}, [isPolling]);
```

For in-app navigation (clicking sidebar links), use a custom `ConfirmModal` component (already exists at `frontend/components/ui/ConfirmModal.tsx`). Intercept navigation by wrapping nav link clicks — this requires the `GenerationGate` to communicate upward via context or by providing a `useNavigationGuard` hook that blocks `router.push` while polling is active.

**Pragmatic approach**: Browser `beforeunload` handles tab close. For in-app, show the ConfirmModal from `GenerationGate` and override the sidebar nav link behavior via context — but this is complex. A simpler approach: show a persistent info banner during generation: "Generation in progress — your draft will appear here when ready." This satisfies the UX intent without intercepting all navigation.

Implement the `beforeunload` guard + a sticky info banner during generation. The full modal intercept can be deferred if complex.

### Visual Design — Typewriter Overlay

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│                                                        │
│   Analyzing your voice profile...                      │
│   (JetBrains Mono, Graphite, character-by-character)   │
│                                                        │
│                                                        │
│   ─────────────────────────────────────────────────   │
│   Analyzing your voice profile...                      │
│   (aria-live="polite" status line, sr-only or small)   │
│                                                        │
└────────────────────────────────────────────────────────┘
                    Paper (#F9F9F6) background
                    Centered vertically in content area
                    JetBrains Mono 14px, line-height 1.7
```

### Error State Design

```
┌────────────────────────────────────────────────────────┐
│  Generation failed.                                    │
│  (Inter 15px, Ink)                                     │
│                                                        │
│  Generation service temporarily unavailable.           │
│  (Inter 14px, Graphite — the error_details text)       │
│                                                        │
│  [   Retry generation   ]  ← Primary Button            │
└────────────────────────────────────────────────────────┘
```

### React Query Setup

The app uses React Query (`@tanstack/react-query`) via a `QueryClientProvider` in `frontend/app/providers.tsx`. The `useJobStatus` hook must be called inside a component wrapped by that provider (which all `(app)/` route components are).

Existing `jobsApi.get` in `lib/api.ts` already calls `GET /api/v1/jobs/{job_id}` — use it directly.

### File Structure

**New files this story:**
```
frontend/hooks/useJobStatus.ts                              ← new React Query polling hook
frontend/components/campaigns/TypewriterAnimation.tsx       ← new animation component
frontend/components/campaigns/CampaignGenerationOverlay.tsx ← compound overlay component
frontend/app/(app)/campaigns/[id]/GenerationGate.tsx        ← client island for polling
```

**Updated files this story:**
```
frontend/app/(app)/campaigns/[id]/page.tsx  ← pass jobId from searchParams to GenerationGate
```

### References

- FR-15 Generation status feedback (202 Accepted, job polling, typewriter, retry on fail): [Source: _bmad-output/planning-artifacts/epics.md#FR-15]
- UX-DR10 Typewriter animation spec (JetBrains Mono, Paper bg, status cycling, aria-live, prefers-reduced-motion fallback): [Source: _bmad-output/planning-artifacts/epics.md#UX-DR10]
- UX-DR23 Navigate-away confirm dialog wording: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR23]
- AR-10 React Query `refetchInterval: 2000` for job polling: [Source: _bmad-output/planning-artifacts/epics.md#AR-10]
- Story 3.1 (job_id passed in URL query param from /campaigns/new): [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1]
- Story 3.3 (actual generation pipeline — this story only handles the polling/UI): [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]
- Epic 4 (Approval Gate full implementation — on job complete, campaign page shows existing static content): [Source: _bmad-output/planning-artifacts/epics.md#Epic 4]
- `frontend/components/ui/ConfirmModal.tsx` — existing confirm dialog component
- `frontend/app/providers.tsx` — QueryClientProvider wrapping all app routes
- `frontend/lib/api.ts:jobsApi.get` — existing job status fetch function

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Updated `useJobStatus` return shape from raw `useQuery` result to `{ job, isPolling, error }` to match story spec; updated 3 existing callers (ClientDetail, VoiceSetupPage, OnboardingFlow) from `{ data: job }` to `{ job }` destructuring.
- Used `router.refresh()` on job complete (as recommended in Dev Notes) rather than duplicating campaign fetch in client state.
- For the navigate-away guard, implemented `beforeunload` browser event + persistent info banner approach (as recommended in Dev Notes as the pragmatic approach). Full modal intercept for all in-app nav links was explicitly deferred per Dev Notes guidance.
- Installed Vitest + @testing-library/react as dev dependencies since no frontend test framework existed; project pattern confirmed via test-summary-2-5.md ("No E2E framework installed").

### Completion Notes List

- Task 1: `useJobStatus` hook updated to return `{ job, isPolling, error }`; query key `["job", jobId]`; polls every 2s while pending/in_progress; stops at terminal states (complete/completed/failed); enabled only for non-empty jobId strings. All 3 existing callers updated.
- Task 2: `TypewriterAnimation` component created; 35ms character reveal; `aria-hidden="true"` on animated span; `role="status" aria-live="polite"` on SR-only status line; `prefers-reduced-motion` detected via matchMedia with SSR-safe pattern; `min-h-[400px]` layout, Paper background, Graphite text, JetBrains Mono.
- Task 3: Message sequence constant defined in `CampaignGenerationOverlay`; pending→index 0; in_progress→cycle 1-3 every 15s; complete→index 4; failed→holds at current.
- Task 4: `CampaignGenerationOverlay` composes hook + animation + cycling; on complete: invalidates campaign query + `router.refresh()`; on failed: Paper-style error card + Retry button that calls `campaignsApi.create`; beforeunload guard + info banner.
- Task 5: `GenerationGate.tsx` client island created; `page.tsx` updated to accept `searchParams` Promise, reads `job_id`, passes to `GenerationGate`; `effectiveJobId` set to null when campaign is already in terminal status (AC #8).
- Task 6: 12 unit tests written and passing — 7 for `useJobStatus` (polling behavior, terminal states, null jobId) + 5 for `TypewriterAnimation` (aria-live, message update, typewriter timing, reduced motion, aria attributes).

### File List

- `frontend/hooks/useJobStatus.ts` — modified (return shape changed to `{ job, isPolling, error }`)
- `frontend/components/campaigns/TypewriterAnimation.tsx` — new
- `frontend/components/campaigns/CampaignGenerationOverlay.tsx` — new
- `frontend/app/(app)/campaigns/[id]/GenerationGate.tsx` — new
- `frontend/app/(app)/campaigns/[id]/page.tsx` — modified (added searchParams, GenerationGate)
- `frontend/components/clients/ClientDetail.tsx` — modified (useJobStatus caller updated)
- `frontend/components/clients/VoiceSetupPage.tsx` — modified (useJobStatus caller updated)
- `frontend/components/onboarding/OnboardingFlow.tsx` — modified (useJobStatus caller updated)
- `frontend/__tests__/hooks/useJobStatus.test.ts` — new
- `frontend/__tests__/components/TypewriterAnimation.test.tsx` — new
- `frontend/vitest.config.ts` — new
- `frontend/vitest.setup.ts` — new
- `frontend/package.json` — modified (added test scripts, vitest/testing-library devDependencies)

### Review Findings

- [x] [Review][Patch] Dead code: `showLeaveModal`/`pendingHrefRef` never set to true — modal JSX unreachable [`CampaignGenerationOverlay.tsx`]
- [x] [Review][Patch] `handleMessageComplete` fires when `!job` after `router.refresh()` clears cache [`CampaignGenerationOverlay.tsx`]
- [x] [Review][Patch] Stale closure in `in_progress` cycling effect — `messageIndex` read without dep inclusion [`CampaignGenerationOverlay.tsx`]
- [x] [Review][Patch] `isComplete` prop declared in `TypewriterAnimation` but never used in render logic [`TypewriterAnimation.tsx`]
- [x] [Review][Patch] Duplicate `TERMINAL_STATUSES` constant with divergent members in `useJobStatus.ts` vs `page.tsx` — rename page.tsx version to `CAMPAIGN_TERMINAL_STATUSES`
- [x] [Review][Patch] `searchParams.job_id` not guarded against array (repeated query param in URL) [`page.tsx`]
- [x] [Review][Patch] AC 3 violation — reduced-motion path cycles messages via 3s timer; spec requires static "Generating..." label only [`TypewriterAnimation.tsx`]
- [x] [Review][Defer] State machine gap: job status values outside known set cause undefined UI behavior — deferred, pre-existing backend contract risk
- [x] [Review][Defer] Null data polling loop with non-existent jobId (no backoff) — deferred, pre-existing
- [x] [Review][Defer] Hydration mismatch on `prefersReducedMotion` SSR→client — deferred, intentional progressive enhancement pattern
- [x] [Review][Defer] `router.refresh()` fired after 1500ms without awaiting `invalidateQueries` completion — deferred, pragmatic
- [x] [Review][Defer] AC 7 in-app navigation modal not wired up — deferred per Dev Notes (beforeunload + banner approach accepted)
- [x] [Review][Patch] CRITICAL: Generation overlay never renders — DISMISSED as false positive; HEAD code uses `!campaign.blog_html` (not `CAMPAIGN_TERMINAL_STATUSES`) which is correct logic; no fix needed [frontend/app/(app)/campaigns/[id]/page.tsx, frontend/app/(app)/campaigns/[id]/GenerationGate.tsx]
- [x] [Review][Patch] Generation info banner missing "Leaving will not cancel it" phrase — updated banner text to spec: "Generation is in progress. Leaving will not cancel it — your draft will be available on the Dashboard when complete." [frontend/components/campaigns/CampaignGenerationOverlay.tsx]
- [x] [Review][Patch] `beforeunload` guard not installed during first 2s poll window — fixed `isPolling` to `!!jobId && (!job || POLLING_STATUSES.has(job.status))` to cover pre-first-fetch window [frontend/hooks/useJobStatus.ts]
- [x] [Review][Defer] Retry handler creates new campaign per spec (AC 3.2-6) — orphaned failed campaigns accumulate as pre-existing design gap [frontend/components/campaigns/CampaignGenerationOverlay.tsx] — deferred, pre-existing
- [x] [Review][Defer] `"complete"`/`"completed"` dual terminal-status strings in both TERMINAL_STATUSES sets — defensive coverage, naming already fixed per prior review — deferred, pre-existing
- [x] [Review][Defer] `handleRetry` doesn't reset `isRetrying` to `false` on success — component unmounts on navigation anyway — deferred, pre-existing

## Change Log

- 2026-07-02: Story 3.2 implemented — generation job polling hook, typewriter animation, campaign generation overlay, GenerationGate RSC island, page.tsx updated for searchParams. Vitest + React Testing Library installed (no prior frontend test framework). 12 unit tests added and passing. 3 existing useJobStatus callers updated to new return shape.
