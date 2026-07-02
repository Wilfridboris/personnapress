# Deferred Work

## Deferred from: code review of 2-7-onboarding-flow (2026-07-02)

- **D1 (Medium)**: Old JWT token remains valid until expiry in multi-tab scenario — completing onboarding in one tab issues a new cookie but tabs holding the old token still see `onboarding_completed=false` until expiry. Requires a server-side session store (e.g., Redis) to invalidate old tokens. [backend/app/services/auth_service.py]
- **D2 (Medium)**: Dashboard server component fetches (`getStats`, `getRecentCampaigns`) do not forward the session cookie — backend 401s are silently swallowed, dashboard shows empty data. Pre-existing design (same-network intent); fix in a future auth-header-on-SSR story. [frontend/app/(app)/dashboard/page.tsx]
- **D3 (Low)**: Brain dump `?prefill=` URL encoding can produce 30KB+ URLs exceeding proxy limits — stub routing in this story will be replaced by Story 3.5 full campaign creation endpoint, eliminating the issue. [frontend/components/onboarding/OnboardingFlow.tsx:312]

## Deferred from: code review of 2-6-voice-profile-refresh (2026-07-01)

- **D1 (Low)**: No recovery path from stuck in-progress state when `client.brand_voice_profile` is null after `router.refresh()` resolves — possible if read replica lags or model serialization error. Needs timeout/fallback transition to `"failed"` state.
- **D2 (Medium)**: No rate-limiting or quota guard on `POST /clients/{id}/ingest` — authenticated owner can spam the endpoint creating unbounded job records. Architectural concern; address at infra or middleware layer.
