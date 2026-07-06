---
baseline_commit: 03b523a38d94cb9469b37aa64c7b2e817a7c577a
---

# Story 7.1: Trial Expiry Nudge Notifications

Status: done

## Story

As a user approaching the end of my free trial,
I want to receive timely in-app notifications reminding me to subscribe before my trial ends,
so that I can decide whether to continue without an unexpected access interruption.

## Acceptance Criteria

1. **Given** a user whose trial has 4 days remaining (day 10 of a 14-day trial, calculated from `subscriptions.created_at`), **When** they load any authenticated page, **Then** a non-blocking toast notification appears in the top-right of the viewport: "4 days left on your trial. Subscribe to keep publishing." with a "Subscribe" link that opens the Stripe Customer Portal; the toast is dismissible (× close button); it appears once per login session, not on every page navigation.

2. **Given** a user whose trial has 1 day remaining (day 13 of trial), **When** they load any authenticated page, **Then** the same toast pattern fires with more urgent copy: "1 day left on your trial. Subscribe now to avoid interruption." — still dismissible, still appears once per login session; this replaces the day-10 nudge if both would apply (they cannot overlap in a single session).

3. **Given** a user who has already dismissed a trial nudge in the current session, **When** they navigate between pages, **Then** the nudge toast does not reappear — it is suppressed until the next login session (use `sessionStorage` key `trial_nudge_dismissed`).

4. **Given** a user who subscribes after seeing a nudge, **When** the Stripe webhook processes the subscription activation, **Then** `subscriptions.status` is updated from `'trialing'` to `'active'`; no further trial nudges appear for this account.

5. **Given** a user's trial has not yet reached day 10, **When** they use the application, **Then** no trial-related nudges or banners appear — trial state is not surfaced until nudge days are reached.

## Tasks / Subtasks

- [x] Task 1: Add `subscriptionsApi` to `frontend/lib/api.ts` (AC: #1, #2, #5)
  - [x] 1.1 Add `subscriptionsApi` object to `frontend/lib/api.ts`:
    ```typescript
    export const subscriptionsApi = {
      getMe: () => apiFetch<SubscriptionInfo>("/subscriptions/me"),
      createPortal: () => apiFetch<{ portal_url: string }>("/subscriptions/portal", { method: "POST" }),
    };
    ```
  - [x] 1.2 Add `SubscriptionInfo` type to `frontend/lib/types/index.ts` (or create `frontend/lib/types/subscription.ts`):
    ```typescript
    export interface SubscriptionInfo {
      plan_tier: string;
      status: string; // 'trialing' | 'active' | 'canceled' | 'trial_expired' | 'past_due'
      campaigns_used: number;
      clients_count: number;
      image_gen_used: number;
      billing_cycle_start: string; // ISO datetime string
      billing_cycle_end: string;   // ISO datetime string
      plan_limits: {
        clients: number;
        campaigns: number;
        image_gens: number;
      };
    }
    ```

- [x] Task 2: Create `useSubscription` hook (AC: #1, #2, #4, #5)
  - [x] 2.1 Create `frontend/hooks/useSubscription.ts`:
    ```typescript
    "use client";
    import { useQuery } from "@tanstack/react-query";
    import { subscriptionsApi } from "@/lib/api";
    import type { SubscriptionInfo } from "@/lib/types";

    export function useSubscription() {
      return useQuery<SubscriptionInfo>({
        queryKey: ["subscription"],
        queryFn: () => subscriptionsApi.getMe(),
        staleTime: 60_000,       // re-fetch at most once per minute
        refetchOnWindowFocus: false,
      });
    }
    ```
  - [x] 2.2 Add a derived helper `useTrialDaysRemaining()` in the same file:
    ```typescript
    export function useTrialDaysRemaining(): number | null {
      const { data } = useSubscription();
      if (!data || data.status !== "trialing") return null;
      const now = Date.now();
      const end = new Date(data.billing_cycle_end).getTime();
      const diffMs = end - now;
      return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
    }
    ```

- [x] Task 3: Create `TrialNudgeToast` component (AC: #1, #2, #3)
  - [x] 3.1 Create `frontend/components/layout/TrialNudgeToast.tsx` as `"use client"`:
    - Uses `useTrialDaysRemaining()` to determine nudge level
    - Reads/writes `sessionStorage` key `"trial_nudge_dismissed"` to suppress after dismiss
    - Shows nudge only if `daysRemaining !== null && daysRemaining <= 4` and not dismissed
    - Day-13 nudge (≤1 day) takes priority over day-10 (≤4 days)
    - Calls `subscriptionsApi.createPortal()` on "Subscribe" click, then `window.location.href = portal_url`
    - Dismisses on × click and sets `sessionStorage.setItem("trial_nudge_dismissed", "1")`
  - [x] 3.2 Paper Style specs per UX-DR9 / UX-DR3 — **Toast UI details:**
    - Position: `fixed top-4 right-4 z-50` — top-right, above page content
    - Container: `bg-[#111111] text-white px-4 py-3 flex items-center gap-3 max-w-sm shadow-md` (sharp corners `rounded-none` per Paper Style)
    - Message text: Inter 13px/Graphite body — white text on Ink background
    - "Subscribe" link: `text-white underline font-medium text-sm cursor-pointer` (opens portal)
    - × close button: `ml-auto text-white/70 hover:text-white transition-colors` with `aria-label="Dismiss trial notification"`
    - Entrance animation: CSS only — `animate-in slide-in-from-right-4 fade-in duration-300` (no Framer Motion needed; CSS can handle mount animation)
    - Exit: remove from DOM on dismiss (no exit animation required — CSS cannot unmount, but simple state removal is fine here per project's existing toast pattern in `useUIStore`)
  - [x] 3.3 Full component implementation:
    ```tsx
    "use client";
    import { useState, useEffect } from "react";
    import { X } from "lucide-react";
    import { useTrialDaysRemaining } from "@/hooks/useSubscription";
    import { subscriptionsApi } from "@/lib/api";

    export function TrialNudgeToast() {
      const daysRemaining = useTrialDaysRemaining();
      const [dismissed, setDismissed] = useState(false);
      const [portalLoading, setPortalLoading] = useState(false);

      useEffect(() => {
        if (sessionStorage.getItem("trial_nudge_dismissed") === "1") {
          setDismissed(true);
        }
      }, []);

      const shouldShow = daysRemaining !== null && daysRemaining <= 4 && !dismissed;
      if (!shouldShow) return null;

      const isUrgent = daysRemaining <= 1;
      const message = isUrgent
        ? `1 day left on your trial. Subscribe now to avoid interruption.`
        : `${daysRemaining} days left on your trial. Subscribe to keep publishing.`;

      function handleDismiss() {
        sessionStorage.setItem("trial_nudge_dismissed", "1");
        setDismissed(true);
      }

      async function handleSubscribe() {
        setPortalLoading(true);
        try {
          const { portal_url } = await subscriptionsApi.createPortal();
          window.location.href = portal_url;
        } finally {
          setPortalLoading(false);
        }
      }

      return (
        <div
          role="status"
          aria-live="polite"
          className="fixed top-4 right-4 z-50 flex max-w-sm items-start gap-3 bg-[#111111] px-4 py-3 text-white shadow-md animate-in slide-in-from-right-4 fade-in duration-300"
        >
          <p className="flex-1 text-sm leading-snug">
            {message}{" "}
            <button
              onClick={handleSubscribe}
              disabled={portalLoading}
              className="font-medium underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white"
            >
              {portalLoading ? "Opening..." : "Subscribe"}
            </button>
          </p>
          <button
            onClick={handleDismiss}
            aria-label="Dismiss trial notification"
            className="mt-0.5 shrink-0 text-white/70 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      );
    }
    ```

- [x] Task 4: Integrate `TrialNudgeToast` into `AppShell` (AC: #1, #2)
  - [x] 4.1 Import and render `<TrialNudgeToast />` inside `frontend/components/layout/AppShell.tsx`, after the existing layout elements but before `{children}` — so it renders once per app-shell mount (once per session login), not per page.
  - [x] 4.2 The existing `AppShell.tsx` renders `<Sidebar />`, `<MobileTopBar />`, `<MobileDrawer />` and `<main>`. Add `<TrialNudgeToast />` as a sibling alongside these, just before the closing `</div>`:
    ```tsx
    // In AppShell.tsx — add import and component
    import { TrialNudgeToast } from "./TrialNudgeToast";
    // ...
    return (
      <div className="min-h-screen bg-[#F9F9F6]">
        <Sidebar />
        <MobileTopBar />
        <MobileDrawer />
        <TrialNudgeToast />   {/* ← ADD THIS */}
        <main className="md:ml-14 lg:ml-60 pt-14 lg:pt-0 min-h-screen">
          <div className="max-w-5xl px-8 lg:px-12 py-8 mx-auto">
            {children}
          </div>
        </main>
      </div>
    );
    ```

- [x] Task 5: Verify Stripe webhook handles `customer.subscription.updated` → `'active'` (AC: #4)
  - [x] 5.1 Confirm `backend/app/services/subscription_service.py` `_handle_subscription_updated()` already sets `sub.status = sub_obj.get("status", sub.status)` — this covers `'active'` status on subscription activation. No new code needed; verify coverage in existing tests.
  - [x] 5.2 Add Stripe event type `customer.subscription.created` to `handle_stripe_webhook()` in `subscription_service.py` — currently only `updated` and `deleted` are handled. A new subscription created after trial expiry fires `customer.subscription.created`, not `updated`. Handle it by delegating to `_handle_subscription_updated()` (same logic applies — status will be `'active'`):
    ```python
    elif event_type == "customer.subscription.created":
        await _handle_subscription_updated(event["data"]["object"], db)
    ```

- [x] Task 6: Write tests (AC: #1–#5)
  - [x] 6.1 Create `frontend/__tests__/components/TrialNudgeToast.test.tsx`:
    - Mock `useTrialDaysRemaining` to return `4` → toast shows "4 days left..." copy
    - Mock return `1` → toast shows "1 day left..." copy
    - Mock return `5` → toast does not render
    - Mock `sessionStorage.getItem("trial_nudge_dismissed")` = `"1"` → toast does not render
    - Clicking × sets `sessionStorage` and removes toast from DOM
  - [x] 6.2 Add to `backend/tests/services/test_subscription.py`:
    - `test_handle_subscription_created_sets_active()`: posts `customer.subscription.created` event, verifies `sub.status == "active"`
    - Confirm existing `test_handle_subscription_updated()` covers the `'active'` transition

## Dev Notes

### Critical Rules

1. **Never put API calls in server components** — per `project-context.md` RSC re-render loop rule. `useSubscription()` hook is `"use client"` only. `AppShell.tsx` is already `"use client"` — safe to use hooks.

2. **Toast appears once per login session, not per navigation** — implement via `sessionStorage` (not `localStorage`). `sessionStorage` is cleared automatically when the browser tab/session ends. Key: `"trial_nudge_dismissed"`.

3. **Day priority rule**: if `daysRemaining <= 1` show urgent copy; else if `daysRemaining <= 4` show standard copy. Never show both simultaneously.

4. **`subscriptionsApi.createPortal()` already has a backend route** at `POST /api/v1/subscriptions/portal` — the `subscriptions.py` router is already registered in `main.py`. No new backend work required for portal link.

5. **Paper Style: no Framer Motion exit animation** — The existing `useUIStore` toast system uses simple state removal. Follow the same pattern: `setDismissed(true)` removes the element from the DOM. CSS `animate-in` handles mount; no AnimatePresence needed since the exit doesn't need a transition per Paper Style guidelines.

6. **Paper Style color tokens** — Use hardcoded hex values matching Paper Style spec (not arbitrary Tailwind classes):
   - Ink: `#111111`
   - White: `#FFFFFF`
   - Paper: `#F9F9F6`

### Architecture Compliance

- `TrialNudgeToast.tsx` → `frontend/components/layout/` (per architecture: layout components in `components/layout/`)
- `useSubscription.ts` → `frontend/hooks/` (per architecture: hooks in `hooks/`)
- `SubscriptionInfo` type → `frontend/lib/types/` (per architecture: types in `lib/types/`)
- `subscriptionsApi` → `frontend/lib/api.ts` (per architecture: all API calls go through `lib/api.ts`)
- Backend: no new routers needed; existing `POST /api/v1/subscriptions/portal` is sufficient

### Files to Create

- `frontend/components/layout/TrialNudgeToast.tsx` (NEW)
- `frontend/hooks/useSubscription.ts` (NEW)

### Files to Modify

- `frontend/lib/api.ts` — add `subscriptionsApi` object and `SubscriptionInfo` type import
- `frontend/lib/types/index.ts` (or equivalent types file) — add `SubscriptionInfo` interface
- `frontend/components/layout/AppShell.tsx` — add `<TrialNudgeToast />`
- `backend/app/services/subscription_service.py` — add `customer.subscription.created` handler
- `backend/tests/services/test_subscription.py` — add subscription created test

### UX Spec References

- UX-DR9: Upgrade Banner component spec (Ink fill + White text) — also applies to toast color palette
- UX-DR3: Button variant spec — Subscribe link uses inline text button style, not a full button component
- UX-DR16: WCAG 2.2 AA — `role="status"`, `aria-live="polite"`, dismiss button `aria-label`
- UX-DR21: Microcopy — no exclamation marks, direct language, no "magic" terms

### Existing Patterns to Follow

- `frontend/hooks/useCalendarCampaigns.ts` — pattern for TanStack Query hooks in this project
- `frontend/components/layout/AppShell.tsx` — integration point for layout-level components
- `frontend/lib/stores/useUIStore.ts` — existing toast system (do NOT use this for the trial nudge — it is a session-persistent component, not a transient error notification)
- `backend/app/services/subscription_service.py` — existing `handle_stripe_webhook()` switch for extending event handlers
- `backend/app/integrations/email.py` — Resend pattern (for reference only; no email in this story)

### Testing Standards

- Frontend: React Testing Library + vitest (follow pattern in `frontend/__tests__/`)
- Backend: pytest + AsyncSession mock (follow pattern in `backend/tests/`)
- Do NOT use snapshot tests for UI components — use behavioral assertions

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#File Tree - TrialBanner.tsx, useUIStore.ts, useSubscription.ts]
- [Source: _bmad-output/planning-artifacts/architecture.md#Requirements to Structure Mapping - FR-28: Trial]
- [Source: _bmad-output/planning-artifacts/epics.md#UX-DR9]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules - RSC Re-render Loop]
- [Source: backend/app/services/subscription_service.py — existing handle_stripe_webhook()]
- [Source: backend/app/routers/subscriptions.py — existing /subscriptions/portal endpoint]
- [Source: frontend/components/layout/AppShell.tsx — integration point]
- [Source: frontend/lib/stores/useUIStore.ts — existing Toast interface pattern]

### Review Findings

- [x] [Review][Patch] Hardcoded "1 day" copy when daysRemaining===0 [frontend/components/layout/TrialNudgeToast.tsx:22-25]
- [x] [Review][Patch] Toast flash on first render — lazy useState needed [frontend/components/layout/TrialNudgeToast.tsx:10]
- [x] [Review][Patch] handleSubscribe swallows API errors silently — no catch block [frontend/components/layout/TrialNudgeToast.tsx:32-39]
- [x] [Review][Patch] window.location.href fires after user dismisses mid-request [frontend/components/layout/TrialNudgeToast.tsx:35]
- [x] [Review][Defer] Direct key access in _handle_subscription_updated (current_period_start/end) — deferred, pre-existing
- [x] [Review][Defer] customer.subscription.created handler may not find sub row if stripe_sub_id unpopulated — deferred, pre-existing architectural concern
- [x] [Review][Defer] billing_cycle_end timezone parsing risk if backend returns naive datetime — deferred, pre-existing backend behavior

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation followed the story spec exactly without blockers.

### Completion Notes List

- Added `SubscriptionInfo` as a type alias for `SubscriptionResponse` in `frontend/lib/types.ts` (reused existing interface rather than duplicating fields).
- Added `subscriptionsApi` with `getMe()` and `createPortal()` to `frontend/lib/api.ts`.
- Created `frontend/hooks/useSubscription.ts` with `useSubscription()` and `useTrialDaysRemaining()` hooks; TanStack Query with 60s stale time and no window-focus refetch.
- Created `frontend/components/layout/TrialNudgeToast.tsx`: Paper Style (Ink bg, no rounded corners), sessionStorage-based session suppression, urgent copy for ≤1 day, standard copy for ≤4 days, WCAG `role="status"` / `aria-live="polite"`.
- Integrated `<TrialNudgeToast />` into `AppShell.tsx` as a sibling of Sidebar/TopBar components.
- Extended `handle_stripe_webhook()` to handle `customer.subscription.created` by delegating to `_handle_subscription_updated()` — covers new subscriptions created after trial expiry.
- 8 frontend tests (vitest + React Testing Library) and 4 backend tests (pytest-asyncio) all pass. Pre-existing backend failures (54) confirmed unrelated to this story.

### File List

- `frontend/lib/types.ts` — added `SubscriptionInfo` type alias
- `frontend/lib/api.ts` — added `subscriptionsApi` and `SubscriptionInfo` import
- `frontend/hooks/useSubscription.ts` — NEW
- `frontend/components/layout/TrialNudgeToast.tsx` — NEW
- `frontend/components/layout/AppShell.tsx` — added `TrialNudgeToast` import and render
- `backend/app/services/subscription_service.py` — extended webhook handler for `customer.subscription.created`
- `frontend/__tests__/components/TrialNudgeToast.test.tsx` — NEW (8 tests)
- `backend/tests/services/test_subscription.py` — NEW (4 tests)

## Change Log

- 2026-07-06: Implemented Story 7.1 — Trial Expiry Nudge Notifications. Added `subscriptionsApi`, `useSubscription`/`useTrialDaysRemaining` hooks, `TrialNudgeToast` component, AppShell integration, Stripe webhook `customer.subscription.created` handler, and full test coverage.
