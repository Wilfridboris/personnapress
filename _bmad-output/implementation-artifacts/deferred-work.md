# Deferred Work Log

## Deferred from: code review of 1-2-user-registration (2026-06-15)

- **Stale JWT claims after plan/status change** — `plan_tier` and `verified` are baked into the JWT at issuance with no revocation. A suspended user or downgraded plan keeps valid claims until cookie expiry (7 days). Architectural JWT tradeoff; needs a token blacklist or short-expiry + refresh strategy in a later story.
- **Session token refresh/rotation not implemented** — 7-day tokens are never rotated or refreshed. A stolen cookie stays valid for the full window. Address in auth hardening story.
- **`auth_google` always redirects returning users to `/onboarding`** — Spec says `/onboarding` for AC#5 but doesn't distinguish new vs returning users. Once a `/dashboard` route exists, returning Google sign-ins should go there instead. Fix when Story 1.4 (app shell) is complete.
- **`_get_key()` silently pads/truncates CREDENTIAL_ENCRYPTION_KEY** — Keys shorter than 32 bytes are zero-padded; keys longer are truncated silently. Pre-existing from story 1.1. Add startup validation of key length in `app/core/security.py`.
- **Backend `resend_verification` has no server-side rate limiting** — Client-side 60s cooldown is trivially bypassed (page reload). Backend needs per-email rate limiting (Redis, DB timestamp, or infrastructure-level). Out of scope for story 1.2; address before production launch.
