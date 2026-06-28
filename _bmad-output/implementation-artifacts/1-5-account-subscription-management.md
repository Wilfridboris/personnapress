# Story 1.5: Account & Subscription Management

Status: done

## Story

As an authenticated user,
I want to view my current plan details and usage, and access the Stripe billing portal to manage my subscription,
So that I understand what I have access to and can upgrade, downgrade, or cancel when needed.

## Acceptance Criteria

1. **Given** an authenticated user navigates to `/account`, **When** the page loads, **Then** it displays: current plan tier name (Starter / Growth / Agency), campaigns used vs. plan limit for the current billing cycle, clients count vs. plan limit, image generations used vs. plan limit, subscription renewal date formatted with `Intl.DateTimeFormat` in the user's locale, and a "Manage subscription" button.

2. **Given** a user on any plan clicks "Manage subscription," **When** the button is clicked, **Then** Next.js calls `POST /api/v1/subscriptions/portal`, FastAPI creates a Stripe Customer Portal session using the user's `stripe_customer_id` and returns `{"portal_url": "..."}`, and Next.js redirects the user to the Stripe-hosted portal page in the same tab.

3. **Given** Stripe fires a `customer.subscription.updated` webhook event, **When** the Next.js webhook route at `/api/webhooks/stripe` receives it, **Then** the route validates the Stripe webhook signature using `STRIPE_WEBHOOK_SECRET`; forwards the event payload to FastAPI `POST /api/v1/webhooks/stripe`; FastAPI updates `subscriptions.plan_tier`, `subscriptions.status`, `subscriptions.billing_cycle_start`, and `subscriptions.billing_cycle_end` accordingly.

4. **Given** Stripe fires a `customer.subscription.deleted` webhook event, **When** the event is processed, **Then** `subscriptions.status` is set to `'canceled'` — full access restriction happens on next session (Epic 7 implements enforcement).

5. **Given** a user has used 8 of their 10 Starter plan campaigns this billing cycle, **When** they view the account page, **Then** the usage display shows "8 / 10 campaigns this billing cycle" in Graphite text — no warning banner appears until the limit is actually reached (Epic 7 handles limit-contact triggers).

6. **Given** a user upgrades from Starter to Growth via the Stripe portal, **When** the `customer.subscription.updated` webhook confirms the change, **Then** `subscriptions.plan_tier` is updated to `'growth'` and all subsequent tier-limit checks reflect Growth limits (5 clients, 30 campaigns, 30 image generations).

7. **Given** the Account page is viewed, **When** all data fields are rendered, **Then** all copy follows Paper Style microcopy rules: no exclamation marks, dates are human-readable ("Renews July 14, 2026"), usage is direct and factual — no progress bars or gamification.

8. **Given** a logged-in user clicks "Log out" on the Account page, **When** `POST /api/v1/auth/logout` completes, **Then** the httpOnly cookie is cleared and the user is redirected to `/login`.

## Tasks / Subtasks

- [x] Task 1: Backend — `GET /api/v1/subscriptions/me` (AC: #1, #5)
  - [x] 1.1 Add `GET /api/v1/subscriptions/me` route to `app/routers/subscriptions.py` (create file if it doesn't exist); register router under `/api/v1/subscriptions` in `main.py`
  - [x] 1.2 Require authentication: extract `user_id` from JWT cookie via a `get_current_user` dependency in `app/core/dependencies.py`
  - [x] 1.3 In `app/services/subscription_service.py`, create `get_subscription(user_id)`: fetch `subscriptions` row for the user
  - [x] 1.4 Return response schema `SubscriptionResponse`: `plan_tier`, `status`, `campaigns_used`, `clients_count`, `image_gen_used`, `billing_cycle_start`, `billing_cycle_end`
  - [x] 1.5 Include computed `plan_limits` in response: lookup from `PLAN_LIMITS` dict keyed by `plan_tier`
  - [x] 1.6 Define `PLAN_LIMITS` constant in `app/core/constants.py`:
    ```python
    PLAN_LIMITS = {
        "starter": {"clients": 3, "campaigns": 10, "image_gens": 10},
        "growth":  {"clients": 5, "campaigns": 30, "image_gens": 30},
        "agency":  {"clients": 15, "campaigns": 100, "image_gens": 100},
    }
    ```

- [x] Task 2: Backend — `POST /api/v1/subscriptions/portal` (AC: #2)
  - [x] 2.1 Add `POST /api/v1/subscriptions/portal` route to `app/routers/subscriptions.py`; require auth
  - [x] 2.2 In `app/services/subscription_service.py`, add `create_billing_portal_session(user_id)`: fetch `subscriptions.stripe_customer_id` → call Stripe `billing_portal.Session.create(customer=stripe_customer_id, return_url=APP_URL + '/account')` → return session URL
  - [x] 2.3 If `stripe_customer_id` is null (trialing user who hasn't added payment): return HTTP 400 with `{"error": {"code": "NO_STRIPE_CUSTOMER", "message": "No billing account found. Please contact support.", "detail": {}}}`
  - [x] 2.4 Add `stripe` SDK to `requirements.txt` if not already present (it was listed in Story 1.1 delta)
  - [x] 2.5 Read `STRIPE_SECRET_KEY` from settings; initialize `stripe.api_key = settings.STRIPE_SECRET_KEY` at module level in `app/integrations/stripe_client.py`

- [x] Task 3: Backend — `POST /api/v1/webhooks/stripe` (AC: #3, #4, #6)
  - [x] 3.1 Create `app/routers/webhooks.py`; add `POST /api/v1/webhooks/stripe`; register under `/api/v1/webhooks` in `main.py`
  - [x] 3.2 This route is **public** (no auth dependency) — Stripe calls it directly
  - [x] 3.3 Read raw request body bytes for signature verification; do NOT parse as JSON before verifying
  - [x] 3.4 Verify Stripe signature: `stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)` — on failure return HTTP 400
  - [x] 3.5 In `app/services/subscription_service.py`, add `handle_stripe_webhook(event)`:
    - On `customer.subscription.updated`: update `plan_tier`, `status`, `billing_cycle_start` (`current_period_start`), `billing_cycle_end` (`current_period_end`); map Stripe `price.lookup_key` or `product.metadata.plan_tier` to internal tier name
    - On `customer.subscription.deleted`: set `status='canceled'`
    - All other event types: return early without error (log at INFO level)
  - [x] 3.6 Return HTTP 200 `{"received": true}` to Stripe for all handled events
  - [x] 3.7 Stripe plan tier mapping: define in `app/core/constants.py`:
    ```python
    STRIPE_PRICE_TO_TIER = {
        "price_starter_monthly": "starter",
        "price_growth_monthly": "growth",
        "price_agency_monthly": "agency",
    }
    ```
    These price IDs must match real Stripe price IDs in env config; use `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_GROWTH`, `STRIPE_PRICE_AGENCY` env vars

- [x] Task 4: Frontend — Next.js webhook relay route (AC: #3, #4)
  - [x] 4.1 Create `frontend/app/api/webhooks/stripe/route.ts` — Next.js Route Handler (server-side)
  - [x] 4.2 Read `STRIPE_WEBHOOK_SECRET` from `process.env.STRIPE_WEBHOOK_SECRET` (server-side only, no `NEXT_PUBLIC_`)
  - [x] 4.3 Validate Stripe webhook signature on the Next.js side using the `stripe` npm package: `stripe.webhooks.constructEvent(body, sig, secret)` — return 400 on failure
  - [x] 4.4 On valid signature, forward raw body + all headers to FastAPI `POST /api/v1/webhooks/stripe` via server-to-server fetch (use internal `INTERNAL_API_URL` env var for Droplet-to-Droplet, or `NEXT_PUBLIC_API_URL` for same network)
  - [x] 4.5 Return FastAPI's response status to Stripe; Stripe retries on non-2xx
  - [x] 4.6 Add `stripe` to `frontend/package.json` dependencies if not already present
  - [x] 4.7 The webhook route must be excluded from middleware auth checking — confirm it is already in the `matcher` exclusion list from Story 1.3 (`/api/webhooks/`)

- [x] Task 5: Backend — `get_current_user` dependency (AC: #1, #2)
  - [x] 5.1 Create `app/core/dependencies.py` with `get_current_user(request: Request)` FastAPI dependency
  - [x] 5.2 Read `session` cookie from request → decode JWT with `python-jose` → return `{"user_id": ..., "email": ..., "plan_tier": ..., "verified": ...}`
  - [x] 5.3 On missing/invalid cookie: raise `HTTPException(401, detail={"error": {"code": "UNAUTHENTICATED", "message": "Authentication required.", "detail": {}}})`
  - [x] 5.4 This dependency will be reused across all authenticated routes in subsequent epics

- [x] Task 6: Frontend — `/account` page (AC: #1, #5, #7, #8)
  - [x] 6.1 Create `frontend/app/(app)/account/page.tsx` — Server Component with metadata (`title: "Account — PersonnaPress"`)
  - [x] 6.2 Fetch subscription data server-side: call `GET /api/v1/subscriptions/me` using the session cookie forwarded from the request (read cookie in Server Component via `cookies()` from `next/headers`)
  - [x] 6.3 Create `frontend/app/(app)/account/AccountClient.tsx` — Client Component for interactive elements (portal button, logout button)
  - [x] 6.4 Server Component renders: plan tier name section, usage section (3 stats), renewal date, passes data to `AccountClient`

- [x] Task 7: Frontend — Account page layout (Paper Style) (AC: #1, #7)
  - [x] 7.1 Page heading: `<h1>` in Playfair Display — "Account"
  - [x] 7.2 Plan section: `<section>` with heading "Current plan" (Inter, 12px, uppercase, tracked), plan tier name (Inter, medium, Ink), subscription status badge (2px radius only rounded element, uppercase, Per-status color)
  - [x] 7.3 Usage section: `<section>` with heading "This billing cycle" — 3 stat rows:
    - "Campaigns: {campaigns_used} / {plan_limits.campaigns}"
    - "Clients: {clients_count} / {plan_limits.clients}"
    - "Image generations: {image_gen_used} / {plan_limits.image_gens}"
    - All in Inter, Graphite color
  - [x] 7.4 Renewal date: "Renews {date}" formatted using `Intl.DateTimeFormat(undefined, { month: 'long', day: 'numeric', year: 'numeric' }).format(new Date(billing_cycle_end))`
  - [x] 7.5 "Manage subscription" Primary Button — onClick calls `POST /api/v1/subscriptions/portal` via `fetchAPI`, then `window.location.href = portal_url`
  - [x] 7.6 "Log out" Secondary Button (or text link) — onClick calls `logout()` from `frontend/lib/auth.ts`
  - [x] 7.7 Section separator: `<hr className="border-[#E5E5E5] my-6" />`
  - [x] 7.8 No progress bars, no percentage rings, no gamification — plain text only per Paper Style

- [x] Task 8: Frontend — Status badge component (AC: #7)
  - [x] 8.1 Create `frontend/components/ui/StatusBadge.tsx` if it doesn't already exist from Story 1.1
  - [x] 8.2 Props: `status: 'trialing' | 'active' | 'canceled' | 'past_due'`
  - [x] 8.3 Style: `rounded-[2px] px-2 py-0.5 text-xs font-medium uppercase tracking-wide` — the ONLY element in the UI with any border radius
  - [x] 8.4 Status color map:
    - `trialing`: `bg-[#FFF1B8] text-[#111111]` (Highlighter)
    - `active`: `bg-[#2E4F2E]/10 text-[#2E4F2E]` (Success tint)
    - `canceled`: `bg-[#8B0000]/10 text-[#8B0000]` (Danger tint)
    - `past_due`: `bg-[#8B0000]/10 text-[#8B0000]` (Danger tint)

## Dev Notes

### Dependency on Stories 1.1 – 1.3

- `users`, `subscriptions` tables must exist (Story 1.1)
- `stripe` and `resend` in `requirements.txt` (Story 1.1 dependency)
- `get_current_user` dependency in `app/core/dependencies.py` is NEW this story; not yet created
- `fetchAPI` utility in `frontend/lib/api.ts` must exist (Story 1.3)
- `(app)/` route group layout with `AppShell` must exist (Story 1.4)
- `logout()` function in `frontend/lib/auth.ts` must exist (Story 1.3)

### Account Page Layout (Paper Style)

```
Account                          ← Playfair Display H1

─────────────────────────────

Current plan                     ← Inter 12px uppercase tracked label
Growth   [Trialing]              ← plan name (Inter medium) + StatusBadge

─────────────────────────────

This billing cycle               ← Inter 12px uppercase tracked label
Campaigns: 0 / 30               ← Inter, Graphite
Clients: 0 / 5
Image generations: 0 / 30

Renews July 28, 2026             ← Inter, Graphite

[    Manage subscription    ]    ← Button Primary

─────────────────────────────

[         Log out           ]    ← Button Secondary (or text link)
```

### `get_current_user` Dependency

```python
# app/core/dependencies.py
from fastapi import Request, HTTPException
from jose import jwt, JWTError
from app.core.config import settings

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHENTICATED", "message": "Authentication required.", "detail": {}}}
        )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Session expired. Please log in again.", "detail": {}}}
        )
```

Use as a route dependency: `current_user: dict = Depends(get_current_user)`.

### Stripe Portal Flow

```
Browser → POST /api/v1/subscriptions/portal
FastAPI → stripe.billing_portal.Session.create(customer_id, return_url)
FastAPI → returns {"portal_url": "https://billing.stripe.com/session/..."}
Browser → window.location.href = portal_url
```

The Stripe Customer Portal handles all plan changes, cancellations, and payment method updates. After the user finishes in the portal, Stripe redirects back to `APP_URL/account`.

### Webhook Signature Verification — Critical

Stripe webhooks MUST be verified before processing. Raw body bytes are required for verification — reading the body as JSON first destroys the signature. In Next.js:

```typescript
// frontend/app/api/webhooks/stripe/route.ts
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(request: Request) {
  const body = await request.text()  // raw string, not .json()
  const sig = request.headers.get('stripe-signature')!

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!)
  } catch {
    return new Response('Webhook signature verification failed', { status: 400 })
  }

  // Forward to FastAPI
  const res = await fetch(`${process.env.INTERNAL_API_URL}/api/v1/webhooks/stripe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'stripe-signature': sig,
    },
    body,
  })

  return new Response('OK', { status: res.ok ? 200 : 500 })
}
```

In FastAPI, re-verify the signature with `STRIPE_WEBHOOK_SECRET` before processing.

### Subscription Response Schema

```python
# app/schemas/subscription.py
from pydantic import BaseModel
from datetime import datetime

class PlanLimits(BaseModel):
    clients: int
    campaigns: int
    image_gens: int

class SubscriptionResponse(BaseModel):
    plan_tier: str
    status: str
    campaigns_used: int
    clients_count: int
    image_gen_used: int
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    plan_limits: PlanLimits
```

### Account Page — Server-Side Data Fetch Pattern

```typescript
// frontend/app/(app)/account/page.tsx
import { cookies } from 'next/headers'

export default async function AccountPage() {
  const cookieStore = cookies()
  const session = cookieStore.get('session')?.value

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/subscriptions/me`, {
    headers: { Cookie: `session=${session}` },
    cache: 'no-store',
  })
  const data = await res.json()

  return <AccountClient subscription={data} />
}
```

Use `cache: 'no-store'` so usage counts are always fresh.

### Stripe Price ID Mapping

The webhook handler maps Stripe price IDs to internal tier names. These price IDs must match the actual Stripe product/price configuration:

- `STRIPE_PRICE_STARTER` → maps to `"starter"` plan tier
- `STRIPE_PRICE_GROWTH` → maps to `"growth"` plan tier
- `STRIPE_PRICE_AGENCY` → maps to `"agency"` plan tier

For v1, trialing users (`status='trialing'`) start on the `growth` tier. On trial expiry without upgrade, Epic 7 handles the restricted state — this story does not gate access.

### Plan Limits Reference

```python
PLAN_LIMITS = {
    "starter": {"clients": 3,  "campaigns": 10,  "image_gens": 10},
    "growth":  {"clients": 5,  "campaigns": 30,  "image_gens": 30},
    "agency":  {"clients": 15, "campaigns": 100, "image_gens": 100},
}
```

Define once in `app/core/constants.py` — import everywhere enforcement is needed. Do NOT duplicate these numbers in router or service files.

### Architecture Rules for this Story

- `POST /api/v1/subscriptions/portal` and `GET /api/v1/subscriptions/me` require auth — use `Depends(get_current_user)` on both
- `POST /api/v1/webhooks/stripe` is public but MUST verify Stripe signature before processing
- Stripe SDK initialized once in `app/integrations/stripe_client.py`, not in routers or services
- No Stripe logic in routers — delegate to `subscription_service.py`
- `STRIPE_WEBHOOK_SECRET` is server-side only — never `NEXT_PUBLIC_`
- Webhook route at `/api/webhooks/stripe` is excluded from Next.js auth middleware (confirmed in Story 1.3 matcher config)

### Next.js Guide Check

Before implementing the Route Handler at `app/api/webhooks/stripe/route.ts`, read `node_modules/next/dist/docs/` for the current Route Handler API in Next.js 16 — specifically how to read raw request body bytes (`request.text()`) without the body being pre-parsed.

### Project Structure Notes

New files this story creates:
```
backend/app/
├── routers/
│   ├── subscriptions.py         ← NEW — /subscriptions/me, /subscriptions/portal
│   └── webhooks.py              ← NEW — /webhooks/stripe
├── services/
│   └── subscription_service.py  ← NEW — get_subscription(), create_billing_portal_session(), handle_stripe_webhook()
├── schemas/
│   └── subscription.py          ← NEW — SubscriptionResponse, PlanLimits
├── core/
│   ├── dependencies.py          ← NEW — get_current_user FastAPI dependency
│   └── constants.py             ← NEW — PLAN_LIMITS, STRIPE_PRICE_TO_TIER
└── integrations/
    └── stripe_client.py         ← NEW — stripe.api_key initialization

frontend/app/
├── (app)/account/
│   ├── page.tsx                 ← NEW — Server Component, fetches subscription
│   └── AccountClient.tsx        ← NEW — Client Component, portal + logout buttons
├── api/webhooks/stripe/
│   └── route.ts                 ← NEW — Stripe webhook relay
└── components/ui/
    └── StatusBadge.tsx          ← NEW (if not created in Story 1.1)
```

Updated files:
```
backend/app/main.py              ← REGISTER subscriptions + webhooks routers
backend/requirements.txt         ← CONFIRM stripe is listed
frontend/package.json            ← CONFIRM stripe npm package is listed
```

### References

- Account & subscription spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5]
- FR-3 (subscriptions), AR-9 (Stripe), AR-10 (webhook): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- Plan tier limits, PLAN_LIMITS enforcement pattern: [Source: _bmad-output/planning-artifacts/architecture.md#Subscription Enforcement]
- Stripe portal session creation: [Source: _bmad-output/planning-artifacts/architecture.md#External Integrations]
- Webhook signature verification pattern: [Source: _bmad-output/planning-artifacts/architecture.md#Security]
- Account page microcopy rules: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]
- StatusBadge component spec (2px radius only): [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Components]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- `stripe_customer_id` lives on the `users` table (not `subscriptions`); `create_billing_portal_session` fetches from `User` model accordingly.
- `StatusBadge.tsx` already existed for campaign statuses; created `SubscriptionStatusBadge.tsx` separately to avoid breaking existing component.
- No `middleware.ts` exists in the frontend, so webhook route exclusion from auth middleware is a non-issue.
- `cookies()` is async in Next.js 16 — used `await cookies()` in the Server Component.
- Stripe SDK initialized via `app/integrations/stripe_client.py` side-effect import in service/router files.
- `STRIPE_PRICE_TO_TIER` mapping built lazily via `get_stripe_price_to_tier()` function referencing settings, rather than as a module-level constant, to allow env vars to be set at runtime.

### File List

**Backend — new files:**
- `backend/app/core/constants.py`
- `backend/app/core/dependencies.py`
- `backend/app/integrations/stripe_client.py`
- `backend/app/schemas/subscription.py`
- `backend/app/services/subscription_service.py`

**Backend — updated files:**
- `backend/app/core/config.py` — added `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_GROWTH`, `STRIPE_PRICE_AGENCY`, `INTERNAL_API_URL`
- `backend/app/routers/subscriptions.py` — filled in `GET /me` and `POST /portal` routes
- `backend/app/routers/webhooks.py` — filled in `POST /stripe` webhook route

**Frontend — new files:**
- `frontend/app/(app)/account/page.tsx`
- `frontend/app/(app)/account/AccountClient.tsx`
- `frontend/app/api/webhooks/stripe/route.ts`
- `frontend/components/ui/SubscriptionStatusBadge.tsx`

**Frontend — updated files:**
- `frontend/lib/types.ts` — added `PlanLimits`, `SubscriptionResponse`
- `frontend/package.json` — added `stripe ^17.7.0`
