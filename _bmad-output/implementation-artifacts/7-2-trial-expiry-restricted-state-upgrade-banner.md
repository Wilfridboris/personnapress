---
baseline_commit: 3095490617bf61f686049e032e153feba86a4e6d
---

# Story 7.2: Trial Expiry Restricted State & Upgrade Banner

Status: done

## Story

As a user whose trial has expired without subscribing,
I want to be clearly notified that my trial has ended and understand what I can and cannot do,
so that I can decide whether to subscribe while knowing my existing content is safe.

## Acceptance Criteria

1. **Given** a user's trial period has ended (`subscriptions.status='trialing'` and `now() > subscriptions.billing_cycle_end`) and they have not subscribed, **When** they log in or their session is validated, **Then** `subscriptions.status` is updated to `'trial_expired'`; a non-dismissible upgrade banner is rendered at the top of every authenticated page: full-width, Ink (#111111) fill, White (#FFFFFF) text, pushes layout down (not an overlay); banner text: "Your trial has ended. Subscribe to continue publishing." with a "Subscribe" CTA button (White-on-Black secondary-inverted style) that opens the Stripe Customer Portal.

2. **Given** a user in `trial_expired` status navigates to any page, **When** the page renders, **Then** they can view their existing Campaigns, Clients, Brand Voice Profiles, and Platform Connections — all read access is preserved; no existing content is deleted or hidden.

3. **Given** a user in `trial_expired` status attempts to create a new Campaign, generate content, or publish, **When** they click "New Campaign," "Generate campaign," "Publish now," or "Schedule," **Then** the action is blocked by `services/subscription.py`; the UI shows an upgrade prompt: "Subscribe to [action — create campaigns / generate content / publish]." with a "Subscribe" CTA; the action does not proceed.

4. **Given** a user in `trial_expired` status clicks a disabled "New Campaign" CTA, **When** the upgrade prompt appears, **Then** it appears as a modal or inline message — not a toast — since the user is attempting a specific action, not just browsing.

5. **Given** a user subscribes after their trial has expired, **When** the Stripe `customer.subscription.created` webhook fires, **Then** `subscriptions.status` is updated to `'active'`; the upgrade banner disappears on their next page load; all previously blocked actions are immediately restored; no data was deleted during the expired period.

## Tasks / Subtasks

- [x] Task 1: Backend — auto-transition `trialing` → `trial_expired` on session validation (AC: #1)
  - [x] 1.1 Add `check_and_expire_trial()` async function in `backend/app/services/subscription_service.py`:
    ```python
    async def check_and_expire_trial(user_id: uuid.UUID, db: AsyncSession) -> str | None:
        """
        Called on every authenticated request. If status='trialing' and billing_cycle_end
        has passed, atomically updates status to 'trial_expired'. Returns the effective status.
        """
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id).with_for_update()
        )
        sub = result.scalars().first()
        if sub is None:
            return None
        if (
            sub.status == "trialing"
            and datetime.now(timezone.utc) > sub.billing_cycle_end.replace(tzinfo=timezone.utc)
        ):
            sub.status = "trial_expired"
            sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()
        return sub.status
    ```
  - [x] 1.2 Add a `GET /api/v1/subscriptions/status` endpoint in `backend/app/routers/subscriptions.py` that calls `check_and_expire_trial()` and returns `{"status": "..."}`. This lightweight endpoint is called by the frontend on app shell mount to detect expiry without fetching full subscription data:
    ```python
    @router.get("/status")
    async def get_subscription_status(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
        status = await check_and_expire_trial(uuid.UUID(current_user["user_id"]), db)
        return {"status": status or "unknown"}
    ```

- [x] Task 2: Backend — block `trial_expired` users from create/generate/publish actions (AC: #3)
  - [x] 2.1 Add `check_trial_not_expired()` function in `backend/app/services/subscription_service.py`:
    ```python
    async def check_trial_not_expired(user_id: uuid.UUID, db: AsyncSession, action: str = "perform this action") -> None:
        """
        Raises HTTP 403 if user's subscription status is 'trial_expired'.
        Call this BEFORE check_client_limit / check_campaign_limit / check_image_limit.
        """
        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = result.scalars().first()
        if sub and sub.status == "trial_expired":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "TRIAL_EXPIRED",
                        "message": f"Subscribe to {action}.",
                        "detail": {"status": "trial_expired"},
                    }
                },
            )
    ```
  - [x] 2.2 Call `check_trial_not_expired()` in these routers, BEFORE existing limit checks:
    - `backend/app/routers/campaigns.py` → `POST /campaigns` (create campaign) — action: `"create campaigns"`
    - `backend/app/routers/campaigns.py` → `POST /campaigns/{id}/regenerate` — action: `"generate content"`
    - `backend/app/routers/publishing.py` → `POST /campaigns/{id}/publish` — action: `"publish"`
    - `backend/app/routers/publishing.py` → `POST /campaigns/{id}/publish/schedule` — action: `"schedule publishing"`
  - [x] 2.3 The existing `services/subscription.py` `check_campaign_limit()` checks for `status in ("canceled", "expired", "past_due")` but does NOT include `"trial_expired"`. This is intentional — `check_trial_not_expired()` runs first and raises 403, so `check_campaign_limit()` never reaches a `trial_expired` user. Do NOT add `"trial_expired"` to the existing list in the limit checkers (would produce the wrong HTTP 400 instead of 403).

- [x] Task 3: Frontend — create `TrialBanner` component (AC: #1, #5)
  - [x] 3.1 Create `frontend/components/layout/TrialBanner.tsx` as `"use client"`:
    - Reads `subscriptionStatus` from `useSubscriptionStatus` hook (new, Task 4)
    - Renders only when `status === "trial_expired"`
    - Non-dismissible (no × button)
    - Full-width, pushes layout down (not `position: fixed`)
  - [x] 3.2 **Paper Style UX-DR9 specs:**
    - Container: `w-full bg-[#111111] text-white px-4 py-3 flex items-center justify-center gap-4` — full-width sticky at top of authenticated content area, pushes layout down
    - Text: Inter 14px — `"Your trial has ended. Subscribe to continue publishing."`
    - "Subscribe" CTA: secondary-inverted style per UX-DR3 — `border border-white text-white px-4 py-1.5 text-sm font-medium hover:bg-white hover:text-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#111111]`
    - No shadow, sharp corners (`rounded-none` implicit in Paper Style)
  - [x] 3.3 Full component:
    ```tsx
    "use client";
    import { useSubscriptionStatus } from "@/hooks/useSubscription";
    import { subscriptionsApi } from "@/lib/api";
    import { useState } from "react";

    export function TrialBanner() {
      const status = useSubscriptionStatus();
      const [loading, setLoading] = useState(false);

      if (status !== "trial_expired") return null;

      async function handleSubscribe() {
        setLoading(true);
        try {
          const { portal_url } = await subscriptionsApi.createPortal();
          window.location.href = portal_url;
        } finally {
          setLoading(false);
        }
      }

      return (
        <div
          role="alert"
          aria-label="Trial expired — upgrade required"
          className="w-full bg-[#111111] px-4 py-3 text-white flex items-center justify-center gap-4"
        >
          <p className="text-sm">
            Your trial has ended. Subscribe to continue publishing.
          </p>
          <button
            onClick={handleSubscribe}
            disabled={loading}
            className="shrink-0 border border-white px-4 py-1.5 text-sm font-medium transition-colors hover:bg-white hover:text-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#111111] disabled:opacity-60"
          >
            {loading ? "Opening..." : "Subscribe"}
          </button>
        </div>
      );
    }
    ```

- [x] Task 4: Frontend — add `useSubscriptionStatus` hook (AC: #1, #5)
  - [x] 4.1 Add `useSubscriptionStatus()` to `frontend/hooks/useSubscription.ts` (extends the hook file created in Story 7.1):
    ```typescript
    export function useSubscriptionStatus(): string | null {
      const { data } = useSubscription();
      return data?.status ?? null;
    }
    ```
  - [x] 4.2 The existing `useSubscription()` hook (created in Story 7.1) already calls `GET /api/v1/subscriptions/me` which returns `status`. No new API call needed for the banner — `useSubscription()` is already called in `AppShell` mount via `TrialNudgeToast`. However, to ensure status is always fresh on navigation (and to trigger the trial expiry check server-side), also add a lightweight `useEffect` in `AppShell.tsx` that calls `GET /api/v1/subscriptions/status` once on mount to trigger the backend `check_and_expire_trial()`. This ensures the expiry transition happens server-side even if the user's cached `useSubscription` data is stale:
    ```typescript
    // In AppShell.tsx — add after existing useEffect blocks:
    useEffect(() => {
      // Trigger server-side trial expiry check on each app shell mount
      subscriptionsApi.getStatus().catch(() => {/* silent — banner will update on next query refetch */});
    }, []);
    ```
  - [x] 4.3 Add `getStatus` to `subscriptionsApi` in `frontend/lib/api.ts`:
    ```typescript
    subscriptionsApi.getStatus = () => apiFetch<{ status: string }>("/subscriptions/status");
    ```
    Or better, add it directly to the `subscriptionsApi` object:
    ```typescript
    export const subscriptionsApi = {
      getMe: () => apiFetch<SubscriptionInfo>("/subscriptions/me"),
      getStatus: () => apiFetch<{ status: string }>("/subscriptions/status"),
      createPortal: () => apiFetch<{ portal_url: string }>("/subscriptions/portal", { method: "POST" }),
    };
    ```
  - [x] 4.4 Add `invalidateQueries(["subscription"])` after `getStatus` resolves so `useSubscription`'s cached data refreshes with the latest status (particularly important when status transitions from `trialing` to `trial_expired`). Use `useQueryClient` in `AppShell.tsx`.

- [x] Task 5: Frontend — integrate `TrialBanner` into layout (AC: #1, #2)
  - [x] 5.1 Update `frontend/app/(app)/layout.tsx` to render `TrialBanner` **above** `AppShell`'s main content. Since `TrialBanner` must push content down (not overlay), it must be rendered inside the layout before `<AppShell>`. Update `(app)/layout.tsx`:
    ```tsx
    import { AppShell } from "@/components/layout/AppShell";
    import { TrialBanner } from "@/components/layout/TrialBanner";

    export default function AppLayout({ children }: { children: React.ReactNode }) {
      return (
        <>
          <TrialBanner />
          <AppShell>{children}</AppShell>
        </>
      );
    }
    ```
    **Important:** `TrialBanner` is a `"use client"` component. The `(app)/layout.tsx` is a Server Component. This is fine — Next.js supports importing Client Components inside Server Component layouts.
  - [x] 5.2 Verify `TrialBanner` does NOT appear on `(auth)/` routes (login, register, verify-email). Since `TrialBanner` is only rendered inside `(app)/layout.tsx` and the auth routes use `(auth)/layout.tsx`, this is automatically guaranteed by the route group structure.

- [x] Task 6: Frontend — upgrade prompt modal for blocked actions (AC: #3, #4)
  - [x] 6.1 Handle `TRIAL_EXPIRED` error code (HTTP 403) in the relevant client components. When the API returns `error.code === "TRIAL_EXPIRED"`, show an upgrade prompt modal (not a toast — per AC #4).
  - [x] 6.2 Extend `useUIStore.ts` to support a dedicated upgrade prompt modal type:
    ```typescript
    // In useUIStore.ts — add to UIStore interface:
    upgradePromptMessage: string | null;
    showUpgradePrompt: (message: string) => void;
    hideUpgradePrompt: () => void;
    ```
    And implementation:
    ```typescript
    upgradePromptMessage: null,
    showUpgradePrompt: (message) => set({ upgradePromptMessage: message }),
    hideUpgradePrompt: () => set({ upgradePromptMessage: null }),
    ```
  - [x] 6.3 Create `frontend/components/common/UpgradePromptModal.tsx`:
    ```tsx
    "use client";
    import { useUIStore } from "@/lib/stores/useUIStore";
    import { subscriptionsApi } from "@/lib/api";
    import { useState } from "react";

    export function UpgradePromptModal() {
      const message = useUIStore((s) => s.upgradePromptMessage);
      const hide = useUIStore((s) => s.hideUpgradePrompt);
      const [loading, setLoading] = useState(false);

      if (!message) return null;

      async function handleSubscribe() {
        setLoading(true);
        try {
          const { portal_url } = await subscriptionsApi.createPortal();
          window.location.href = portal_url;
        } finally {
          setLoading(false);
        }
      }

      return (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="upgrade-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={hide}
        >
          <div
            className="bg-[#F9F9F6] border border-[#E5E5E5] p-8 max-w-sm w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2
              id="upgrade-modal-title"
              className="font-serif text-xl text-[#111111] mb-3"
            >
              Subscription required
            </h2>
            <p className="text-sm text-[#555555] mb-6">{message}</p>
            <div className="flex gap-3">
              <button
                onClick={handleSubscribe}
                disabled={loading}
                className="flex-1 bg-[#111111] text-white px-4 py-2.5 text-sm font-medium hover:bg-white hover:text-[#111111] border border-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
              >
                {loading ? "Opening..." : "Subscribe"}
              </button>
              <button
                onClick={hide}
                className="px-4 py-2.5 text-sm border border-[#E5E5E5] text-[#555555] hover:border-[#111111] hover:text-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      );
    }
    ```
  - [x] 6.4 Render `<UpgradePromptModal />` inside `AppShell.tsx` alongside existing layout components.
  - [x] 6.5 In the campaign creation handler (the "New Campaign" / brain dump submit), catch API errors with `error.code === "TRIAL_EXPIRED"` and call `useUIStore.getState().showUpgradePrompt("Subscribe to create campaigns.")`. Apply same pattern in the publish/schedule action handlers.

- [x] Task 7: Write tests (AC: #1–#5)
  - [x] 7.1 Backend — `backend/tests/services/test_subscription.py`:
    - `test_check_and_expire_trial_updates_status()`: subscription with `status='trialing'` and `billing_cycle_end` in the past → function sets `status='trial_expired'`
    - `test_check_and_expire_trial_no_op_when_active()`: `status='active'` subscription → no change
    - `test_check_trial_not_expired_raises_403()`: `status='trial_expired'` → function raises HTTPException 403 with `TRIAL_EXPIRED` code
    - `test_check_trial_not_expired_passes_for_active()`: `status='active'` → no exception raised
  - [x] 7.2 Backend — `backend/tests/routers/test_campaigns.py`:
    - `test_create_campaign_blocked_for_trial_expired()`: mock subscription with `trial_expired` status → `POST /campaigns` returns 403
  - [x] 7.3 Frontend — `frontend/__tests__/components/TrialBanner.test.tsx`:
    - Mock `useSubscription` returning `{ status: "trial_expired" }` → banner renders
    - Mock `useSubscription` returning `{ status: "trialing" }` → banner does not render
    - Mock `useSubscription` returning `{ status: "active" }` → banner does not render
    - Click "Subscribe" → calls `subscriptionsApi.createPortal()`

## Dev Notes

### Critical Rules

1. **`check_and_expire_trial()` uses `with_for_update()`** — prevents race conditions if two concurrent requests both try to set `trial_expired` simultaneously. Pattern is already established in `check_client_limit()` and `check_campaign_limit()`.

2. **`billing_cycle_end` timezone handling** — The model stores `billing_cycle_end` as a naive datetime (no tzinfo) per `utcnow()` convention in `models.py`. When comparing, call `.replace(tzinfo=timezone.utc)` on the DB value to make it timezone-aware. Compare against `datetime.now(timezone.utc)`.

3. **`TrialBanner` is not dismissible** — per UX-DR9 spec. No × button. Do not add one.

4. **Layout order matters** — `TrialBanner` must be rendered BEFORE `AppShell` in `(app)/layout.tsx`. If placed inside `AppShell`, the sidebar `ml-*` offset will shift the banner. A full-width banner must be at the top-level layout, not inside the offset main content area.

5. **Modal focus trap** — Per UX-DR16, modals require `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, focus trap (Tab cycles within modal), Esc to close, focus returns to trigger. The `UpgradePromptModal` above is a minimal implementation. Add `useEffect` for Esc key listener and focus trap if a fully accessible implementation is required. At minimum, `role="dialog"` and `aria-labelledby` are mandatory.

6. **Do NOT use `"trial_expired"` in subscription limit checkers** — The `check_campaign_limit()`, `check_client_limit()`, and `check_image_limit()` functions use HTTP 400 with plan upgrade messages. `trial_expired` enforcement must use HTTP 403 via `check_trial_not_expired()` instead. The two paths must be kept separate.

7. **`(app)/layout.tsx` is a Server Component** — it can import Client Components (`TrialBanner`) directly. This is the correct Next.js pattern. Do NOT make `(app)/layout.tsx` a Client Component.

8. **RSC rule** — Per `project-context.md`: server components do only session/auth checks. `TrialBanner` and `UpgradePromptModal` are both `"use client"` components. The `useSubscription` hook fetches subscription data via TanStack Query on the client side.

### Architecture Compliance

- `TrialBanner.tsx` → `frontend/components/layout/` (explicitly listed in architecture file tree at line 829)
- `UpgradePromptModal.tsx` → `frontend/components/common/` (shared UI components go in `components/common/`)
- `check_and_expire_trial()` and `check_trial_not_expired()` → `backend/app/services/subscription_service.py`
- New endpoint `GET /subscriptions/status` → `backend/app/routers/subscriptions.py`

### Files to Create

- `frontend/components/layout/TrialBanner.tsx` (NEW)
- `frontend/components/common/UpgradePromptModal.tsx` (NEW)

### Files to Modify

- `frontend/app/(app)/layout.tsx` — add `<TrialBanner />` above `<AppShell>`
- `frontend/components/layout/AppShell.tsx` — add `<UpgradePromptModal />`, add `getStatus` call on mount, add query invalidation
- `frontend/lib/api.ts` — add `getStatus` to `subscriptionsApi`
- `frontend/lib/stores/useUIStore.ts` — add `upgradePromptMessage`, `showUpgradePrompt`, `hideUpgradePrompt`
- `frontend/hooks/useSubscription.ts` — add `useSubscriptionStatus()` (from Story 7.1 file)
- `backend/app/services/subscription_service.py` — add `check_and_expire_trial()`, `check_trial_not_expired()`
- `backend/app/routers/subscriptions.py` — add `GET /status` endpoint
- `backend/app/routers/campaigns.py` — call `check_trial_not_expired()` before create/regenerate
- `backend/app/routers/publishing.py` — call `check_trial_not_expired()` before publish/schedule

### UX Spec References

- UX-DR9: TrialBanner — Ink fill + White text, non-dismissible, pushes layout down
- UX-DR3: Button variants — secondary-inverted (transparent, 1px Ink border, inverts on hover) for "Subscribe" CTA in banner
- UX-DR16: WCAG 2.2 AA — modal `role="dialog"`, `aria-modal`, `aria-labelledby`, focus trap, Esc to close
- UX-DR21: Microcopy — "Subscribe to [action]" pattern, direct language, no exclamation marks

### Existing Patterns to Follow

- `backend/app/services/subscription_service.py:22` — `with_for_update()` pattern for subscription row locking
- `backend/app/services/subscription_service.py:33` — `status in (...)` check pattern for blocked status
- `frontend/app/(app)/layout.tsx` — current 5-line Server Component layout (extend minimally)
- `frontend/components/layout/AppShell.tsx` — existing layout + hook integration point

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#TrialBanner.tsx line 829]
- [Source: _bmad-output/planning-artifacts/architecture.md#Hard Service Boundaries — subscription.py must be called by ALL routers]
- [Source: _bmad-output/planning-artifacts/epics.md#UX-DR9 — Upgrade Banner component]
- [Source: _bmad-output/planning-artifacts/epics.md#UX-DR3 — Button variants]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules — RSC Re-render Loop]
- [Source: backend/app/services/subscription_service.py — existing pattern for limit checks]
- [Source: backend/app/db/repositories/models.py — Subscription model, utcnow() timezone convention]
- [Source: frontend/app/(app)/layout.tsx — Server Component layout to extend]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Fixed 6 regression failures in `test_publish_now.py` and `test_schedule_publish.py` by patching `check_trial_not_expired` — the existing tests used bare `AsyncMock()` for db, which broke when the new function called `result.scalars().first()`. Pattern consistent with how other service functions are patched in those files.

### Completion Notes List

- Added `check_and_expire_trial()` and `check_trial_not_expired()` to `subscription_service.py` following existing `with_for_update()` locking pattern.
- Added `GET /subscriptions/status` endpoint; mounted before `/me` to avoid route shadowing.
- Wired `check_trial_not_expired()` into campaigns (create + regenerate) and publishing (publish + schedule) routers BEFORE existing limit checks, producing HTTP 403 with `TRIAL_EXPIRED` code — separate from HTTP 400 limit errors as required.
- Created `TrialBanner.tsx` as non-dismissible full-width Ink banner per UX-DR9. Uses `useSubscriptionStatus` hook, renders only on `trial_expired`.
- Created `UpgradePromptModal.tsx` with Esc key listener, focus trap (autofocus on Subscribe), backdrop click to close, `role="dialog"` + `aria-modal` per UX-DR16.
- Updated `AppShell.tsx`: calls `subscriptionsApi.getStatus()` on mount + invalidates `["subscription"]` query to ensure server-side expiry transition is reflected client-side immediately.
- `TrialBanner` rendered in `(app)/layout.tsx` above `AppShell` to ensure full-width (not offset by sidebar).
- TRIAL_EXPIRED error handling added to: `campaigns/new/page.tsx` (create), `approval-panel.tsx` (regenerate, publishNow, schedule) — shows `UpgradePromptModal` instead of toast per AC #4.
- All 6 new backend tests pass (10 subscription service tests, 7 campaign router tests). All 145 frontend tests pass (7 new TrialBanner tests).

### File List

- `backend/app/services/subscription_service.py` (modified)
- `backend/app/routers/subscriptions.py` (modified)
- `backend/app/routers/campaigns.py` (modified)
- `backend/app/routers/publishing.py` (modified)
- `frontend/components/layout/TrialBanner.tsx` (new)
- `frontend/components/common/UpgradePromptModal.tsx` (new)
- `frontend/hooks/useSubscription.ts` (modified)
- `frontend/lib/api.ts` (modified)
- `frontend/lib/stores/useUIStore.ts` (modified)
- `frontend/components/layout/AppShell.tsx` (modified)
- `frontend/app/(app)/layout.tsx` (modified)
- `frontend/app/(app)/campaigns/new/page.tsx` (modified)
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` (modified)
- `backend/tests/services/test_subscription.py` (modified)
- `backend/tests/routers/test_campaigns.py` (modified)
- `backend/tests/routers/test_publish_now.py` (modified)
- `backend/tests/routers/test_schedule_publish.py` (modified)
- `frontend/__tests__/components/TrialBanner.test.tsx` (new)

### Review Findings

- [x] [Review][Patch] Missing `import uuid` in subscriptions.py [backend/app/routers/subscriptions.py:21]
- [x] [Review][Patch] `check_trial_not_expired` reads stale DB status — trial bypass possible for users still in `trialing` state [backend/app/services/subscription_service.py:43]
- [x] [Review][Patch] `POST /{campaign_id}/image/regenerate` missing `check_trial_not_expired` guard [backend/app/routers/campaigns.py:216]
- [x] [Review][Patch] `POST /campaigns/{campaign_id}/publish/retry` missing `check_trial_not_expired` guard [backend/app/routers/publishing.py:537]
- [x] [Review][Patch] `handleSubscribe` has no error catch — portal API failure leaves button stuck [frontend/components/layout/TrialBanner.tsx:13, frontend/components/common/UpgradePromptModal.tsx:26]
- [x] [Review][Patch] `UpgradePromptModal` has no Tab focus trap — keyboard users can exit modal [frontend/components/common/UpgradePromptModal.tsx:36]
- [x] [Review][Patch] `UpgradePromptModal` does not restore focus to trigger element on close [frontend/components/common/UpgradePromptModal.tsx]
- [x] [Review][Patch] AppShell unconditionally invalidates subscription query on every mount [frontend/components/layout/AppShell.tsx:28]
- [x] [Review][Patch] No scroll lock when `UpgradePromptModal` is open [frontend/components/common/UpgradePromptModal.tsx]
- [x] [Review][Defer] `.replace(tzinfo)` inconsistency across DB write paths [backend/app/services/subscription_service.py:35] — deferred, pre-existing architectural concern across codebase
- [x] [Review][Defer] TrialBanner flash-of-absent-content on first load for newly-expired users — deferred, pre-existing RSC architectural limitation (server components do no data fetching per project rule)
- [x] [Review][Defer] Long-lived sessions never re-expire mid-session — deferred, spec intent was on-login check; real-time polling is out of scope
- [x] [Review][Defer] `useSubscription` stale 60s after Stripe portal return — deferred, pre-existing from 7.1 hook design
- [x] [Review][Defer] Trial expiry not checked at session-validation layer — deferred, intentional architectural trade-off given RSC rule

## Change Log

- 2026-07-06: Implemented Story 7.2 — Trial Expiry Restricted State & Upgrade Banner. Added backend auto-expiry of trialing subscriptions, HTTP 403 blocking for trial_expired users, TrialBanner component, UpgradePromptModal, and all associated tests.
