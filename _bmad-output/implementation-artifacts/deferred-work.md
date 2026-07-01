# Deferred Work Log

## Deferred from: code review of 1-2-user-registration (2026-06-15)

- **Stale JWT claims after plan/status change** — `plan_tier` and `verified` are baked into the JWT at issuance with no revocation. A suspended user or downgraded plan keeps valid claims until cookie expiry (7 days). Architectural JWT tradeoff; needs a token blacklist or short-expiry + refresh strategy in a later story.
- **Session token refresh/rotation not implemented** — 7-day tokens are never rotated or refreshed. A stolen cookie stays valid for the full window. Address in auth hardening story.
- **`auth_google` always redirects returning users to `/onboarding`** — Spec says `/onboarding` for AC#5 but doesn't distinguish new vs returning users. Once a `/dashboard` route exists, returning Google sign-ins should go there instead. Fix when Story 1.4 (app shell) is complete.
- **`_get_key()` silently pads/truncates CREDENTIAL_ENCRYPTION_KEY** — Keys shorter than 32 bytes are zero-padded; keys longer are truncated silently. Pre-existing from story 1.1. Add startup validation of key length in `app/core/security.py`.
- **Backend `resend_verification` has no server-side rate limiting** — Client-side 60s cooldown is trivially bypassed (page reload). Backend needs per-email rate limiting (Redis, DB timestamp, or infrastructure-level). Out of scope for story 1.2; address before production launch.

## Deferred from: code review of 2-1-create-client (2026-07-01)

- **`NEXT_PUBLIC_API_URL` used for server-side backend fetch** — `frontend/app/(app)/clients/[id]/page.tsx` uses `NEXT_PUBLIC_API_URL` for server-component fetch calls. While not a bug (URL is already client-visible), a dedicated `API_URL` env var avoids embedding the value in the client bundle redundantly. Revisit when deploying to production.
- **Double fetch: `generateMetadata` and page body both call `getClient`** — Both use `cache: "no-store"` and a dynamic cookie, so Next.js fetch deduplication does not merge them. Performance optimization: use React `cache()` to deduplicate or remove client name from metadata title. Not a correctness issue.
- **`stripe_sub_id` NOT NULL in migration vs `Optional[str]` in SQLModel** — `backend/app/db/repositories/models.py`. Pre-existing inconsistency; admin tooling or test factories may produce a confusing `IntegrityError`. Add startup validation or migrate the column to nullable.
- **`Client.name` has no DB-level length constraint** — `backend/app/db/repositories/models.py`. The 255-char cap is enforced only in `ClientCreate`'s `field_validator`. Direct repository calls bypass it. Pre-existing schema issue; add `sa.String(255)` in a future migration.
- **No guard against duplicate active ingestion jobs per client** — `backend/app/routers/clients.py`. Two concurrent POSTs or a future "re-ingest" path can create two `pending` jobs for the same `client_id`. Needs a unique partial index on `(client_id, job_type)` where `status IN ('pending','in_progress')`. Address in Story 2.4 when full ingestion is implemented.

## Deferred from: code review of 2-2-edit-delete-client (2026-07-01)

- **Double DB fetch on every PATCH** — `update_client_detail` in `backend/app/routers/clients.py` calls `get_client` for ownership check, then `update_client` calls it again internally. Two sequential SELECT round-trips per mutation. Performance optimization; not a correctness issue.
- **No mechanism to clear website_url via PATCH** — `ClientUpdate` validator converts empty/blank URL to `None` but `url_changed` only fires when `body.website_url is not None`. There is no supported path to remove a client's website URL. Out of Story 2.2 spec scope.
- **PATCH 403 vs GET 404 for non-owned clients** — `get_client_detail` returns 404 when `not client or client.user_id != user_id`; `update_client_detail` returns distinct 403. Minor client-enumeration surface. Deliberate per AC#6; consider harmonizing in a later auth-hardening story.

## Deferred from: code review of 1-3-user-login-session-management (2026-06-28)

- **No rate limiting on `POST /api/v1/auth/login`** — `/login` has no throttling, lockout, or CAPTCHA. Combined with brute-force tooling this is a full credential-stuffing surface. Out of v1 scope; address before production launch with a rate-limiting middleware or infrastructure-level rule.
- **`x-user-id`/`x-plan-tier` headers can be spoofed** — Proxy injects these from the JWT payload into request headers, but if the FastAPI backend is reachable directly (dev, misconfigured infra), callers can send arbitrary header values. Backend must not use these headers for any security-critical authorization decision; always re-derive identity from the session token or a separate auth dependency.
