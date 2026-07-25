---
baseline_commit: b78295c2623ce47f4c08c3e646abac2b8b0417d8
---

# Story 7.4: Stripe Checkout Flow + In-App Plan Picker

Status: done

## Story

As a PersonnaPress user in a trial or expired trial state,
I want to see the three subscription plans and be able to subscribe to one directly from within the app,
so that I can activate my account without landing on an empty Stripe portal that has nothing to offer me.

## Acceptance Criteria

1. **Given** an authenticated user with `status = 'trialing'` navigates to `/account`, **When** the page loads, **Then** a "Choose your plan" section appears after the billing cycle usage section showing three plan cards: Starter ($29/mo), Growth ($49/mo, marked "Most popular" and "Current trial"), Agency ($149/mo) — each with feature list and "Subscribe to [Plan]" button; the existing "Manage subscription" portal button does NOT appear.

2. **Given** an authenticated user with `status = 'trial_expired'` navigates to `/account`, **When** the page loads, **Then** the same three-plan picker appears (status remains trial_expired, Growth is "Current trial") — identical to AC 1.

3. **Given** a user with `status = 'active'` or `'past_due'` or `'canceled'` navigates to `/account`, **When** the page loads, **Then** the existing "Manage subscription" button appears (opens Stripe Customer Portal) and NO plan picker is shown.

4. **Given** a user clicks "Subscribe to Growth" (or any plan) in the plan picker, **When** the button is clicked, **Then** a `POST /api/v1/subscriptions/checkout` request is sent with `{"plan": "growth"}`, the backend creates a Stripe Checkout Session, and the user is redirected to the Stripe-hosted checkout page; all three "Subscribe" buttons are disabled during the in-flight request.

5. **Given** the backend receives `POST /api/v1/subscriptions/checkout` with a valid plan, **When** processing, **Then** it creates a `stripe.checkout.Session` with `mode="subscription"`, the correct `price_id` for the plan, `success_url=APP_URL + "/account?checkout_success=1"`, `cancel_url=APP_URL + "/pricing"`, `allow_promotion_codes=True`; if the user already has a `stripe_customer_id`, it passes `customer=stripe_customer_id`; otherwise it passes `customer_email=user.email`.

6. **Given** Stripe fires a `checkout.session.completed` event after a successful payment by a new user (no prior `stripe_customer_id`), **When** the webhook handler processes it, **Then** the user's `users.stripe_customer_id` is updated with the Stripe customer ID from the event so future portal and checkout sessions reuse the same customer.

7. **Given** a `POST /api/v1/subscriptions/checkout` request arrives with an unrecognized plan value (not "starter", "growth", or "agency"), **When** processing, **Then** the endpoint returns HTTP 400 with `{"error": {"code": "INVALID_PLAN", "message": "Invalid plan.", "detail": {}}}`.

8. **Given** the `TrialBanner` (shown on `trial_expired`) displays its "Subscribe" CTA, **When** the user clicks it, **Then** the user is navigated to `/account#choose-plan` (no portal session created); the plan picker on `/account` scrolls into view.

9. **Given** the `UpgradePromptModal` (shown on create/generate/publish attempt by expired user) shows its "Subscribe" button, **When** clicked, **Then** the modal closes and the user is navigated to `/account#choose-plan`.

10. **Given** the `TrialNudgeToast` (shown ≤4 days before trial ends) shows its "Subscribe" link, **When** clicked, **Then** the user navigates to `/account#choose-plan`.

11. **Given** a checkout session is being created, **When** the `POST /subscriptions/checkout` API call errors (network error or server error), **Then** an inline error message appears below the plan picker heading: `role="alert"`, no page navigation occurs, the buttons re-enable.

12. **Given** backend tests run, **When** 4 new tests execute, **Then** all pass: `test_create_checkout_session_valid_plan` (mock stripe, assert correct price_id used), `test_create_checkout_session_uses_existing_customer` (assert `customer=` kwarg when stripe_customer_id exists), `test_create_checkout_session_new_customer_uses_email` (assert `customer_email=` when no stripe_customer_id), `test_create_checkout_session_invalid_plan` (assert HTTPException 400).

## Tasks / Subtasks

- [x] Task 1: Backend schemas (AC: 4, 5, 7)
  - [x] In `backend/app/schemas/subscription.py`, add two Pydantic models:
    ```python
    from typing import Literal
    
    class CheckoutRequest(BaseModel):
        plan: Literal["starter", "growth", "agency"]
    
    class CheckoutResponse(BaseModel):
        checkout_url: str
    ```

- [x] Task 2: Backend service — `create_checkout_session` (AC: 5, 6, 7)
  - [x] In `backend/app/services/subscription_service.py`, add after `create_billing_portal_session`:
    ```python
    async def create_checkout_session(user_id: str, plan: str, db: AsyncSession) -> str:
        """Creates a Stripe Checkout Session for the given plan tier."""
        import app.integrations.stripe_client  # noqa: F401 — side-effect: sets stripe.api_key
        
        price_map = {v: k for k, v in get_stripe_price_to_tier().items()}
        price_id = price_map.get(plan)
        if not price_id:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "INVALID_PLAN", "message": "Invalid plan.", "detail": {}}}
            )
        
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "NOT_FOUND", "message": "User not found.", "detail": {}}}
            )
        
        kwargs: dict = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": settings.APP_URL + "/account?checkout_success=1",
            "cancel_url": settings.APP_URL + "/pricing",
            "allow_promotion_codes": True,
        }
        if user.stripe_customer_id:
            kwargs["customer"] = user.stripe_customer_id
        else:
            kwargs["customer_email"] = user.email
        
        session = stripe_sdk.checkout.Session.create(**kwargs)
        return session.url
    ```
  - [x] Ensure imports at the top of `subscription_service.py` include `get_stripe_price_to_tier` from `app.core.constants` — it is already imported alongside `PLAN_LIMITS`; verify it is there

- [x] Task 3: Backend webhook — `checkout.session.completed` handler (AC: 6)
  - [x] In `backend/app/services/subscription_service.py`, inside `handle_stripe_webhook`, add a new branch after the existing `customer.subscription.deleted` handler:
    ```python
    elif event["type"] == "checkout.session.completed":
        cs = event["data"]["object"]
        customer_id = cs.get("customer")
        customer_email = (cs.get("customer_details") or {}).get("email")
        if customer_id and customer_email:
            await db.execute(
                update(User)
                .where(User.email == customer_email)
                .values(stripe_customer_id=customer_id)
            )
            await db.commit()
    ```
  - [x] Verify `update` is imported from `sqlalchemy` (check existing imports in the file)

- [x] Task 4: Backend router — `POST /subscriptions/checkout` (AC: 4, 5, 7)
  - [x] In `backend/app/routers/subscriptions.py`, add endpoint (import `CheckoutRequest`, `CheckoutResponse`, `create_checkout_session`):
    ```python
    @router.post("/checkout", response_model=CheckoutResponse)
    async def create_checkout(
        body: CheckoutRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> CheckoutResponse:
        checkout_url = await create_checkout_session(current_user["user_id"], body.plan, db)
        return CheckoutResponse(checkout_url=checkout_url)
    ```

- [x] Task 5: Backend tests (AC: 12)
  - [x] In `backend/tests/services/test_subscription.py`, add 4 new tests. Study the existing test patterns in that file — they use an async pattern specific to this project. Follow the same fixtures and mock patterns:
    - [x] `test_create_checkout_session_valid_plan` — mock `stripe_sdk.checkout.Session.create`, call `create_checkout_session(user_id, "growth", db)`, assert the mock was called with `price_id=settings.STRIPE_PRICE_GROWTH` in `line_items`, assert returns the mock session URL
    - [x] `test_create_checkout_session_uses_existing_customer` — user with `stripe_customer_id="cus_123"`, assert `"customer": "cus_123"` in the mock call kwargs
    - [x] `test_create_checkout_session_new_customer_uses_email` — user with `stripe_customer_id=None`, assert `"customer_email": user.email` in the mock call kwargs
    - [x] `test_create_checkout_session_invalid_plan` — call with `plan="enterprise"`, assert `HTTPException` with `status_code=400`

- [x] Task 6: Frontend — add `createCheckout` to `subscriptionsApi` (AC: 4)
  - [x] In `frontend/lib/api.ts`, inside the `subscriptionsApi` object, add after `createPortal`:
    ```typescript
    createCheckout: (plan: "starter" | "growth" | "agency") =>
      fetchAPI<{ checkout_url: string }>("/subscriptions/checkout", {
        method: "POST",
        body: JSON.stringify({ plan }),
      }),
    ```
  - [x] Note: `fetchAPI` already sets `Content-Type: application/json` and `credentials: "include"` — no additional headers needed

- [x] Task 7: Frontend types (AC: 1, 2, 3)
  - [x] In `frontend/lib/types.ts`, add (after existing type definitions):
    ```typescript
    export type SubscriptionStatus =
      | "trialing"
      | "active"
      | "canceled"
      | "past_due"
      | "trial_expired";
    ```

- [x] Task 8: Frontend — new `PlanPickerClient` component (AC: 1, 2, 4, 11)
  - [x] Create `frontend/app/(app)/account/PlanPickerClient.tsx`:
    ```tsx
    "use client";
    
    import { useState } from "react";
    import { CheckCircle2 } from "lucide-react";
    import { subscriptionsApi } from "@/lib/api";
    import type { PlanTier } from "@/lib/types";
    
    const PLANS = [
      {
        key: "starter" as PlanTier,
        name: "Starter",
        price: "$29",
        tagline: "For individuals getting started with AI content.",
        features: [
          "2 clients",
          "10 campaigns per month",
          "10 image generations per month",
          "All publishing platforms",
          "Content calendar",
          "Scheduled publishing",
          "Headless blog API",
        ],
        popular: false,
      },
      {
        key: "growth" as PlanTier,
        name: "Growth",
        price: "$49",
        tagline: "For businesses that publish weekly.",
        features: [
          "5 clients",
          "30 campaigns per month",
          "30 image generations per month",
          "Everything in Starter",
        ],
        popular: true,
      },
      {
        key: "agency" as PlanTier,
        name: "Agency",
        price: "$149",
        tagline: "For agencies managing multiple client voices.",
        features: [
          "20 clients",
          "Unlimited campaigns",
          "100 image generations per month",
          "Everything in Growth",
          "Priority support",
        ],
        popular: false,
      },
    ];
    
    interface PlanPickerClientProps {
      currentTier: PlanTier;
    }
    
    export function PlanPickerClient({ currentTier }: PlanPickerClientProps) {
      const [loadingPlan, setLoadingPlan] = useState<PlanTier | null>(null);
      const [error, setError] = useState("");
    
      async function handleSubscribe(plan: PlanTier) {
        setLoadingPlan(plan);
        setError("");
        try {
          const data = await subscriptionsApi.createCheckout(plan);
          window.location.href = data.checkout_url;
        } catch (err) {
          setError(err instanceof Error ? err.message : "Something went wrong.");
          setLoadingPlan(null);
        }
      }
    
      return (
        <section id="choose-plan" aria-labelledby="plan-picker-heading">
          <p
            id="plan-picker-heading"
            className="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-4"
          >
            Choose your plan
          </p>
    
          {error && (
            <p role="alert" className="font-body text-sm text-danger mb-4">
              {error}
            </p>
          )}
    
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-[#E5E5E5] bg-[#E5E5E5]">
            {PLANS.map((plan) => {
              const isCurrent = plan.key === currentTier;
              const isLoading = loadingPlan === plan.key;
              const isDisabled = loadingPlan !== null;
    
              return (
                <article key={plan.key} className="bg-paper p-6 flex flex-col">
                  {plan.popular && (
                    <p className="font-mono text-[10px] text-graphite tracking-widest uppercase mb-1">
                      Most popular
                    </p>
                  )}
                  {isCurrent && (
                    <p className="font-mono text-[10px] text-graphite tracking-widest uppercase mb-1">
                      Current trial
                    </p>
                  )}
    
                  <h3 className="font-display text-xl font-bold text-ink mb-1">
                    {plan.name}
                  </h3>
                  <p className="font-display text-3xl font-bold text-ink mb-1">
                    {plan.price}
                    <span className="font-mono text-xs text-graphite">/mo</span>
                  </p>
                  <p className="font-body text-sm text-graphite mb-4">{plan.tagline}</p>
    
                  <ul
                    className="space-y-1.5 mb-6 flex-1"
                    aria-label={`${plan.name} plan features`}
                  >
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm text-graphite">
                        <CheckCircle2
                          className="size-4 text-ink mt-0.5 shrink-0"
                          aria-hidden="true"
                        />
                        {f}
                      </li>
                    ))}
                  </ul>
    
                  <button
                    onClick={() => handleSubscribe(plan.key)}
                    disabled={isDisabled}
                    className="inline-flex w-full items-center justify-center bg-ink text-paper font-medium text-sm px-5 py-2.5 hover:bg-graphite transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                  >
                    {isLoading ? "Processing..." : `Subscribe to ${plan.name}`}
                  </button>
                </article>
              );
            })}
          </div>
        </section>
      );
    }
    ```

- [x] Task 9: Frontend — update `AccountClient` to accept `status` and `currentTier` props (AC: 1, 2, 3)
  - [x] Modify `frontend/app/(app)/account/AccountClient.tsx`:
    - [x] Add import: `import { PlanPickerClient } from "./PlanPickerClient";`
    - [x] Add import: `import type { PlanTier } from "@/lib/types";`
    - [x] Replace the existing prop-less function signature with:
      ```tsx
      interface AccountClientProps {
        status: string;
        currentTier: PlanTier;
      }
      
      export function AccountClient({ status, currentTier }: AccountClientProps) {
        const showPlanPicker = status === "trialing" || status === "trial_expired";
        // ... existing useState hooks unchanged
      ```
    - [x] In the JSX return, replace the existing "Manage subscription" `<Button>` (and its surrounding `<hr>`) with:
      ```tsx
      <hr className="border-[#E5E5E5] my-6" />
      
      {error && (
        <p role="alert" className="font-body text-sm text-danger mb-4">
          {error}
        </p>
      )}
      
      {showPlanPicker ? (
        <PlanPickerClient currentTier={currentTier} />
      ) : (
        <Button
          variant="primary"
          onClick={handleManageSubscription}
          disabled={portalLoading}
          className="w-full"
        >
          {portalLoading ? "Loading..." : "Manage subscription"}
        </Button>
      )}
      ```
    - [x] Keep the existing `error` state and `handleManageSubscription` function — they are still used for the portal path when `showPlanPicker` is false
    - [x] The existing `<hr>` before the logout button and the logout button itself are UNCHANGED

- [x] Task 10: Frontend — update `account/page.tsx` to pass props to `AccountClient` (AC: 1, 2, 3)
  - [x] In `frontend/app/(app)/account/page.tsx`, change the `<AccountClient />` call to:
    ```tsx
    <AccountClient status={subscription.status} currentTier={subscription.plan_tier} />
    ```
  - [x] No other changes to this file

- [x] Task 11: Frontend — fix `TrialBanner` Subscribe CTA (AC: 8)
  - [x] In `frontend/components/layout/TrialBanner.tsx`, find the "Subscribe" button that calls `subscriptionsApi.createPortal()`. Replace it with a plain anchor tag using the same visual styles (keep the existing `className` value unchanged, just change the element):
    ```tsx
    <a
      href="/account#choose-plan"
      className="shrink-0 border border-white px-4 py-1.5 text-sm font-medium transition-colors hover:bg-white hover:text-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#111111]"
    >
      Subscribe
    </a>
    ```
  - [x] Remove the `useState` for portal loading and the `handleSubscribe` / `createPortal` call if it is now unused; remove `subscriptionsApi` import if no longer used

- [x] Task 12: Frontend — fix `UpgradePromptModal` Subscribe CTA (AC: 9)
  - [x] In `frontend/components/common/UpgradePromptModal.tsx`, find the "Subscribe" button that calls the portal. Replace the `onClick` handler to:
    1. Call `hideUpgradePrompt()` (close the modal)
    2. Navigate to `/account#choose-plan` using `window.location.href = "/account#choose-plan"`
    ```tsx
    onClick={() => {
      hideUpgradePrompt();
      window.location.href = "/account#choose-plan";
    }}
    ```
  - [x] Remove the `useState` for portal loading and `createPortal` call if now unused; remove `subscriptionsApi` import if no longer used
  - [x] Keep the focus trap, Escape key handler, and modal backdrop unchanged

- [x] Task 13: Frontend — fix `TrialNudgeToast` Subscribe link (AC: 10)
  - [x] In `frontend/components/layout/TrialNudgeToast.tsx`, find the "Subscribe" element that calls the portal. Replace with a simple anchor:
    ```tsx
    <a
      href="/account#choose-plan"
      className="underline text-white text-sm font-medium hover:no-underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white"
    >
      Subscribe
    </a>
    ```
  - [x] Remove portal-related `useState`, `handleSubscribe`, and `subscriptionsApi` import if now unused

## Dev Notes

### Backend patterns — follow exactly

**Imports already in `subscription_service.py`:**
```python
import uuid
import stripe as stripe_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.constants import PLAN_LIMITS, UNLIMITED, get_stripe_price_to_tier
from app.db.models import User, Subscription
```

Verify `update` is imported from sqlalchemy for the webhook handler: `from sqlalchemy import select, update`. Add `update` if missing.

**`get_stripe_price_to_tier()` returns `{price_id: tier_name}`.** The checkout function needs the inverse map `{tier_name: price_id}`. Build it as:
```python
price_map = {v: k for k, v in get_stripe_price_to_tier().items()}
```

If `STRIPE_PRICE_GROWTH` is empty string in dev (env not set), `price_map.get("growth")` returns `""` — the `if not price_id:` guard will correctly raise 400 in that case.

**Stripe SDK module:** `stripe_sdk.checkout.Session.create(...)` — the SDK module is aliased to `stripe_sdk` throughout this codebase. Do NOT use bare `stripe`.

### Frontend patterns

**`subscriptionsApi` is defined in `frontend/lib/api.ts`.** Confirm via text search before adding. The pattern:
```typescript
export const subscriptionsApi = {
  getMe: ...,
  getStatus: ...,
  createPortal: ...,
  // ADD HERE:
  createCheckout: (plan: "starter" | "growth" | "agency") =>
    fetchAPI<{ checkout_url: string }>("/subscriptions/checkout", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),
};
```

**`fetchAPI` vs `apiFetch`:** There may be an alias `const apiFetch = fetchAPI`. `subscriptionsApi` currently uses `apiFetch` internally. Use the same alias the existing methods use.

**`AccountClient` breaking change:** The existing component has no props. After this story it has `{ status: string; currentTier: PlanTier }`. Since `page.tsx` is the only caller, this is safe — update both files in the same pass.

**The `error` state in `AccountClient`:** The existing `AccountClient` has `const [error, setError] = useState("")` for portal errors. Keep this state. The portal error `<p role="alert">` should only render when `!showPlanPicker && error`. The plan picker component has its own internal error state.

**`id="choose-plan"` is on the `<section>` inside `PlanPickerClient`.** When the user navigates to `/account#choose-plan`, the browser scrolls to this element. This works because:
- For `trial_expired` users: `TrialBanner` is visible at top AND `PlanPickerClient` is in the DOM simultaneously
- For `trialing` users: `TrialNudgeToast` CTA navigates to the same anchor

### File structure

| File | Change |
|------|--------|
| `backend/app/schemas/subscription.py` | ADD `CheckoutRequest`, `CheckoutResponse` |
| `backend/app/services/subscription_service.py` | ADD `create_checkout_session()`, ADD `checkout.session.completed` branch in `handle_stripe_webhook` |
| `backend/app/routers/subscriptions.py` | ADD `POST /checkout` endpoint |
| `backend/tests/services/test_subscription.py` | ADD 4 new tests |
| `frontend/lib/api.ts` | ADD `createCheckout` to `subscriptionsApi` |
| `frontend/lib/types.ts` | ADD `SubscriptionStatus` type |
| `frontend/app/(app)/account/PlanPickerClient.tsx` | NEW — plan picker client component |
| `frontend/app/(app)/account/AccountClient.tsx` | MODIFY — accept status/currentTier props, conditionally render picker vs portal button |
| `frontend/app/(app)/account/page.tsx` | MODIFY — pass `status` and `plan_tier` to `AccountClient` |
| `frontend/components/layout/TrialBanner.tsx` | MODIFY — Subscribe → anchor `/account#choose-plan` |
| `frontend/components/common/UpgradePromptModal.tsx` | MODIFY — Subscribe → `hideUpgradePrompt()` + navigate |
| `frontend/components/layout/TrialNudgeToast.tsx` | MODIFY — Subscribe → anchor `/account#choose-plan` |

### `SubscriptionStatusBadge` — add `trial_expired` config entry

The `account/page.tsx` passes `subscription.status` to `<SubscriptionStatusBadge>`. Currently it does:
```tsx
const status = subscription.status as "trialing" | "active" | "canceled" | "past_due";
```
This type cast excludes `trial_expired`. After this story, users can have `status="trial_expired"`. The badge component (`frontend/components/ui/SubscriptionStatusBadge.tsx`) has a `BADGE_CONFIG` object — add the entry:
```typescript
trial_expired: { label: "TRIAL ENDED", className: "bg-danger/10 text-danger" },
```
Also update the type union in `account/page.tsx`:
```tsx
const status = subscription.status as "trialing" | "active" | "canceled" | "past_due" | "trial_expired";
```
This is a small change but prevents a runtime lookup miss on the badge config.

### Stripe test mock example

The project uses `anyio` async test pattern. Study existing tests to confirm, then follow this structure:
```python
from unittest.mock import patch, MagicMock

async def test_create_checkout_session_valid_plan(db_session, mock_user_with_customer):
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test_abc123"
    
    with patch("app.services.subscription_service.stripe_sdk.checkout.Session.create") as mock_create:
        mock_create.return_value = mock_session
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.STRIPE_PRICE_GROWTH = "price_growth_abc"
            mock_settings.STRIPE_PRICE_STARTER = "price_starter_abc"
            mock_settings.STRIPE_PRICE_AGENCY = "price_agency_abc"
            mock_settings.APP_URL = "https://personnapress.com"
            
            result = await create_checkout_session(str(mock_user_with_customer.id), "growth", db_session)
            
            assert result == "https://checkout.stripe.com/test_abc123"
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["mode"] == "subscription"
            assert call_kwargs["line_items"][0]["price"] == "price_growth_abc"
```
The exact fixture names (`db_session`, `mock_user_with_customer`) are taken from existing test files — look at how `create_billing_portal_session` is tested and reuse those fixtures.

### Regression checks

After implementation, verify:
- A `trialing` user on `/account` sees the plan picker (no portal button)
- An `active` user on `/account` sees the portal button (no plan picker)
- Clicking "Subscribe to Agency" disables all three cards while in flight, re-enables on error
- The `TrialBanner` Subscribe click navigates to `/account#choose-plan` (no POST to portal)
- All existing subscription service tests continue to pass

### Testing

Follow the exact async test patterns used in `backend/tests/services/test_subscription.py`. Look at the existing `test_check_campaign_limit_agency_bypasses_limit` test for the fixture and mock style. Do NOT use `asyncio.run()`. Stripe SDK calls must be mocked — do not make real Stripe API calls in tests.

### References

- `backend/app/services/subscription_service.py` — `create_billing_portal_session` (model for checkout function)
- `backend/app/routers/subscriptions.py` — `POST /portal` endpoint (model for checkout endpoint)
- `backend/app/core/constants.py` — `get_stripe_price_to_tier()` function
- `frontend/app/(app)/account/AccountClient.tsx` — current implementation (to modify)
- `frontend/components/layout/TrialBanner.tsx` — current portal CTA (to replace)
- `frontend/components/common/UpgradePromptModal.tsx` — current portal CTA (to replace)
- `frontend/components/layout/TrialNudgeToast.tsx` — current portal CTA (to replace)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers encountered.

### Completion Notes List

- Added `CheckoutRequest` and `CheckoutResponse` Pydantic models to `backend/app/schemas/subscription.py`
- Added `create_checkout_session()` to `subscription_service.py`: builds inverse price map, validates plan, selects user, passes `customer=` if `stripe_customer_id` exists else `customer_email=`
- Added `checkout.session.completed` webhook branch: updates `stripe_customer_id` on the user row matched by email
- Added `POST /subscriptions/checkout` endpoint to `backend/app/routers/subscriptions.py`
- Added `update` import from sqlalchemy to support the webhook handler
- Added 4 backend tests (all pass): valid plan, existing customer, new customer, invalid plan — using patch on `get_stripe_price_to_tier`, `stripe_sdk.checkout.Session.create`, and `settings`
- Added `createCheckout` method to `subscriptionsApi` in `frontend/lib/api.ts`
- Added `SubscriptionStatus` type union to `frontend/lib/types.ts`
- Created `PlanPickerClient.tsx`: 3-plan grid with "Most popular" / "Current trial" badges, loading/disabled state on all cards during in-flight request, inline `role="alert"` error
- Updated `AccountClient.tsx`: accepts `status` and `currentTier` props; conditionally renders `PlanPickerClient` (trialing/trial_expired) or portal button (active/past_due/canceled); portal error only shown when plan picker not visible
- Updated `account/page.tsx`: passes `subscription.status` and `subscription.plan_tier` to `AccountClient`; adds `trial_expired` to the status cast union
- Updated `SubscriptionStatusBadge.tsx`: added `trial_expired` config entry with "TRIAL ENDED" label
- Rewrote `TrialBanner.tsx`: removed portal loading state and `subscriptionsApi` import; Subscribe is now a plain `<a href="/account#choose-plan">` anchor
- Updated `UpgradePromptModal.tsx`: Subscribe button now calls `hide()` + `window.location.href = "/account#choose-plan"` instead of portal; removed loading state and `subscriptionsApi` import
- Rewrote `TrialNudgeToast.tsx`: Subscribe is now a plain `<a href="/account#choose-plan">` anchor; removed portal loading/error state and `subscriptionsApi` import; removed `cancelledRef`
- All 19 subscription service tests pass; 114 service tests total pass without regressions

### File List

- `backend/app/schemas/subscription.py`
- `backend/app/services/subscription_service.py`
- `backend/app/routers/subscriptions.py`
- `backend/tests/services/test_subscription.py`
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- `frontend/app/(app)/account/PlanPickerClient.tsx` (NEW)
- `frontend/app/(app)/account/AccountClient.tsx`
- `frontend/app/(app)/account/page.tsx`
- `frontend/components/ui/SubscriptionStatusBadge.tsx`
- `frontend/components/layout/TrialBanner.tsx`
- `frontend/components/common/UpgradePromptModal.tsx`
- `frontend/components/layout/TrialNudgeToast.tsx`

### Review Findings

- [x] [Review][Decision] AC7: CheckoutRequest.plan as Literal returns 422 not 400 for invalid plan — AC7 specifies 400 with INVALID_PLAN code; Pydantic Literal validation short-circuits with 422 Unprocessable Entity before the service guard runs; resolved by changing plan to str and relying on service-level 400 guard
- [x] [Review][Patch] Webhook should use client_reference_id for reliable user lookup [backend/app/services/subscription_service.py:342,352-362] — add client_reference_id=user_id to checkout kwargs; update webhook to look up user by id first, fallback to email; add warning log when update matches 0 rows
- [x] [Review][Patch] No guard prevents active subscribers from creating a second checkout session [backend/app/services/subscription_service.py:create_checkout_session] — fetch user's subscription after user lookup and raise 409 ALREADY_SUBSCRIBED if status is "active"
- [x] [Review][Patch] Silent no-op when webhook email update matches zero rows [backend/app/services/subscription_service.py:357-362] — covered by client_reference_id patch above (warning log on rowcount==0)
- [x] [Review][Defer] Stripe SDK synchronous calls in async context [backend/app/services/subscription_service.py:302,342] — deferred, pre-existing
- [x] [Review][Defer] Plan prices hardcoded in PlanPickerClient [frontend/app/(app)/account/PlanPickerClient.tsx] — deferred, pre-existing

## Change Log

- 2026-07-25: Implemented Stripe Checkout flow + in-app plan picker (Story 7-4). Backend: POST /subscriptions/checkout endpoint, create_checkout_session service, checkout.session.completed webhook. Frontend: PlanPickerClient 3-plan grid, AccountClient conditional rendering, SubscriptionStatusBadge trial_expired, TrialBanner/UpgradePromptModal/TrialNudgeToast Subscribe CTAs routed to /account#choose-plan.
