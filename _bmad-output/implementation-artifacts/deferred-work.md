# Deferred Work

## Deferred from: code review of 3-1-brain-dump-input-campaign-creation (2026-07-02)

- **D1 (Critical)**: `campaigns_used` is never reset to 0 when a billing cycle renews — pre-existing issue in the Stripe webhook handler (`_handle_subscription_updated`). Users who exhaust their monthly quota are permanently blocked after cycle renewal. Fix: set `sub.campaigns_used = 0` in the renewal handler. [backend/app/services/subscription_service.py]
- **D2 (Medium)**: `GET /campaigns` returns all campaigns for the user with no `limit`/`offset` — will become a performance issue for agency-tier users. Needs pagination. [backend/app/routers/campaigns.py:list_campaigns]
- **D3 (Planned)**: `run_generation` is a stub (`pass`) — intentional for Story 3.1. Story 3.3 fills in the Gemini generation logic. [backend/app/workers/generate.py]

## Deferred from: code review of 2-7-onboarding-flow (2026-07-02)

- **D1 (Medium)**: Old JWT token remains valid until expiry in multi-tab scenario — completing onboarding in one tab issues a new cookie but tabs holding the old token still see `onboarding_completed=false` until expiry. Requires a server-side session store (e.g., Redis) to invalidate old tokens. [backend/app/services/auth_service.py]
- **D2 (Medium)**: Dashboard server component fetches (`getStats`, `getRecentCampaigns`) do not forward the session cookie — backend 401s are silently swallowed, dashboard shows empty data. Pre-existing design (same-network intent); fix in a future auth-header-on-SSR story. [frontend/app/(app)/dashboard/page.tsx]
- **D3 (Low)**: Brain dump `?prefill=` URL encoding can produce 30KB+ URLs exceeding proxy limits — stub routing in this story will be replaced by Story 3.5 full campaign creation endpoint, eliminating the issue. [frontend/components/onboarding/OnboardingFlow.tsx:312]

## Deferred from: code review of 2-6-voice-profile-refresh (2026-07-01)

- **D1 (Low)**: No recovery path from stuck in-progress state when `client.brand_voice_profile` is null after `router.refresh()` resolves — possible if read replica lags or model serialization error. Needs timeout/fallback transition to `"failed"` state.
- **D2 (Medium)**: No rate-limiting or quota guard on `POST /clients/{id}/ingest` — authenticated owner can spam the endpoint creating unbounded job records. Architectural concern; address at infra or middleware layer.
