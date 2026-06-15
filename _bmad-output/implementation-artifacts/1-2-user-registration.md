# Story 1.2: User Registration

Status: done
Review: done (2026-06-15)

## Story

As a new user,
I want to create an account with my email and password or sign up via Google,
So that I can access PersonnaPress and begin building my content workflow.

## Acceptance Criteria

1. **Given** an unregistered user submits the registration form with a valid email and password (minimum 8 characters), **When** `POST /api/v1/auth/register` is processed, **Then** a `users` record is created with `verified=false` and `hashed_password` set via bcrypt; a `subscriptions` record is created with `plan_tier='growth'` and `status='trialing'`; a verification email is sent via Resend containing a signed time-limited verification link; and the UI displays "Check your email to verify your account." — no exclamation mark, Paper Style tone.
   **And** the password is hashed in FastAPI only — it is never stored in plaintext or processed in Next.js.

2. **Given** an already-registered email is submitted, **When** the registration form is submitted, **Then** the API returns the generic message "An account with this email already exists." — the response does not reveal whether the account is verified or unverified.

3. **Given** an unverified user attempts to navigate to any `(app)/` route, **When** Next.js middleware evaluates their JWT (if present), **Then** they are redirected to `/verify-email` with instructions to check their inbox; a "Resend verification email" link is available that calls `POST /api/v1/auth/resend-verification`.

4. **Given** a user clicks the email verification link, **When** the token is valid and unexpired, **Then** `POST /api/v1/auth/verify-email` sets `users.verified=true`, issues a JWT (payload: `user_id`, `email`, `plan_tier`, `exp`), sets the JWT as an httpOnly cookie (`secure=True`, `samesite=lax`, 7-day expiry), and redirects the user to `/onboarding`.
   **And** if the token is expired, the API returns "Verification link expired — request a new one." with a resend option.

5. **Given** a new user clicks "Sign up with Google" on the registration page, **When** they complete the Google OAuth consent screen and are returned to `/api/auth/google/callback`, **Then** the Next.js route exchanges the auth code for a Google profile server-side, calls `POST /api/v1/auth/google` with the verified profile, FastAPI creates or finds the user record (setting `google_sub`, `verified=true`, skipping email verification), issues a JWT cookie, and redirects the user to `/onboarding`.

6. **Given** the registration page is rendered, **When** a screen reader navigates the form, **Then** all fields have visible labels (not placeholder-only), error messages are associated via `aria-describedby`, and the "Sign up with Google" button has an accessible label.

## Tasks / Subtasks

- [x] Task 1: Backend — `POST /api/v1/auth/register` (AC: #1, #2)
  - [x] 1.1 Create `app/routers/auth.py` and register it under `/api/v1/auth` prefix in `main.py`
  - [x] 1.2 Create `app/schemas/auth.py` with `RegisterRequest` (`email: EmailStr`, `password: str` min 8 chars), `RegisterResponse`
  - [x] 1.3 Create `app/services/auth_service.py` with `register_user()`: check email uniqueness → hash password with `passlib[bcrypt]` → create `users` record → create `subscriptions` record → send verification email → return success
  - [x] 1.4 Generate a signed time-limited verification token in `app/core/security.py` using `python-jose` (HS256, `JWT_SECRET`, 24-hour expiry, `sub=email`, `type="email_verification"`)
  - [x] 1.5 Create `app/integrations/email.py` with `send_verification_email(to_email, token)` using Resend SDK; email body includes link `{APP_URL}/verify-email/confirm?token={token}`
  - [x] 1.6 Handle duplicate email: return HTTP 400 with `{"error": {"code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email already exists.", "detail": {}}}`

- [x] Task 2: Backend — `POST /api/v1/auth/verify-email` (AC: #4)
  - [x] 2.1 Add `GET /api/v1/auth/verify-email` route accepting `?token=` query param
  - [x] 2.2 Decode and validate the verification token (check `type="email_verification"`, expiry, `sub` exists as an unverified user)
  - [x] 2.3 Set `users.verified=true` in DB; issue full session JWT (payload: `user_id`, `email`, `plan_tier`, `exp=7d`)
  - [x] 2.4 Set httpOnly JWT cookie: `httpOnly=True`, `secure=True`, `samesite="lax"`, `max_age=604800` (7 days)
  - [x] 2.5 Return redirect response to `/onboarding` (or return a redirect URL for Next.js to follow)
  - [x] 2.6 Expired token: return HTTP 400 with `{"error": {"code": "TOKEN_EXPIRED", "message": "Verification link expired — request a new one.", "detail": {}}}`

- [x] Task 3: Backend — `POST /api/v1/auth/resend-verification` (AC: #3)
  - [x] 3.1 Accept `{"email": "..."}` in request body; look up unverified user; generate new verification token; call `send_verification_email()`
  - [x] 3.2 Always return HTTP 200 even if email not found (prevent email enumeration)

- [x] Task 4: Backend — `POST /api/v1/auth/google` (AC: #5)
  - [x] 4.1 Accept profile data forwarded from Next.js callback (`google_sub`, `email`, `email_verified`)
  - [x] 4.2 Profile data comes from trusted Next.js server-side Google token exchange (not client-supplied)
  - [x] 4.3 Create or find `users` record by `google_sub`; if email matches an existing password user, link by email
  - [x] 4.4 Create `subscriptions` record with `plan_tier='growth'` and `status='trialing'` if new user
  - [x] 4.5 Issue JWT cookie (same flags as Task 2); return success with redirect info

- [x] Task 5: Frontend — `/register` page (AC: #1, #2, #5, #6)
  - [x] 5.1 Create `frontend/app/(auth)/register/page.tsx` — Server Component with metadata (`title: "Create account — PersonnaPress"`)
  - [x] 5.2 Create `frontend/app/(auth)/register/RegisterForm.tsx` — Client Component with form state
  - [x] 5.3 Form fields (Paper Style): Email (`<Input>` Standard variant, `id="email"`, `<label htmlFor="email">Email address</label>`), Password (`<Input type="password"`, `id="password"`, `<label>Password</label>`, helper text "Minimum 8 characters"), "Create account" Primary `<Button>`
  - [x] 5.4 Client-side validation: password length < 8 → inline error below field via `aria-describedby`; no API call until valid
  - [x] 5.5 On success (API returns 200): show "Check your email to verify your account." inline message (not a toast, not a redirect — user stays on page)
  - [x] 5.6 On API error: display `error.message` from the API response inline below the form
  - [x] 5.7 "Sign up with Google" Secondary `<Button>` that initiates Google OAuth redirect; use accessible `aria-label="Sign up with Google"`
  - [x] 5.8 Link to `/login`: "Already have an account? Log in."
  - [x] 5.9 Page layout: centered card on Paper background, no sidebar (`(auth)` route group layout with no sidebar)

- [x] Task 6: Frontend — Next.js Google OAuth callback (AC: #5)
  - [x] 6.1 Create `frontend/app/api/auth/google/callback/route.ts` as a Next.js Route Handler (server-side only)
  - [x] 6.2 Exchange `code` from URL query params for Google user profile using `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (server-side only)
  - [x] 6.3 POST the verified profile to FastAPI `POST /api/v1/auth/google`
  - [x] 6.4 On success: relay the JWT `set-cookie` header from FastAPI; redirect to `/onboarding`
  - [x] 6.5 On error: redirect to `/register?error=oauth_failed`

- [x] Task 7: Frontend — `/verify-email` page (AC: #3, #4)
  - [x] 7.1 Create `frontend/app/(auth)/verify-email/page.tsx` — shows "Check your inbox" message with the user's email address (passed via query param)
  - [x] 7.2 "Resend verification email" button that POSTs to `POST /api/v1/auth/resend-verification`; on click shows "Verification email sent." (no repeat sends within 60s, enforced client-side)
  - [x] 7.3 Handle the verification link callback: `frontend/app/(auth)/verify-email/confirm/page.tsx` that reads `?token=` from URL and calls `GET /api/v1/auth/verify-email?token=`; on success redirects to `/onboarding`; on expired shows error with resend CTA

- [x] Task 8: Next.js Middleware — unverified user gate (AC: #3)
  - [x] 8.1 In `frontend/middleware.ts`: after validating the JWT with `jose`, check `verified` claim in the payload
  - [x] 8.2 If `verified=false` and route is under `(app)/`: redirect to `/verify-email?email=...`
  - [x] 8.3 If no JWT and route is under `(app)/`: redirect to `/login`

- [x] Task 9: Backend — `users` Alembic migration addition (AC: #1)
  - [x] 9.1 Confirmed `users.verified` column exists with `default=False` from Story 1.1 migration
  - [x] 9.2 Confirmed `subscriptions` table exists; created new migration `2a7f3c8d1e04` to make `stripe_sub_id` nullable (new registrations have no Stripe sub yet)

## Dev Notes

### Dependency on Story 1.1

This story requires Story 1.1 to be complete:
- `users` and `subscriptions` tables must exist in Supabase Postgres (Alembic migration applied)
- Backend `app/` layered architecture must be in place (routers, services, db, core, integrations)
- `passlib[bcrypt]`, `python-jose[cryptography]`, `resend`, `google-generativeai` must be in `requirements.txt`
- Frontend Paper Style `<Input>`, `<Button>` components must exist in `components/ui/`

### JWT Payload Structure (critical — used by middleware in 1.3)

```python
# app/core/security.py
import jwt  # python-jose
from datetime import datetime, timedelta

JWT_ALGORITHM = "HS256"
SESSION_EXPIRY_DAYS = 7

def create_session_token(user_id: str, email: str, plan_tier: str, verified: bool) -> str:
    payload = {
        "user_id": str(user_id),
        "email": email,
        "plan_tier": plan_tier,
        "verified": verified,
        "exp": datetime.utcnow() + timedelta(days=SESSION_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)
```

The `verified` field MUST be in the JWT payload so `middleware.ts` can gate unverified users without a DB call.

### Cookie Setting in FastAPI

```python
from fastapi import Response

def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
    )
```

Use `JSONResponse` with cookie set on it when returning from auth endpoints.

### Email Verification Token vs Session Token

Two distinct JWT types:
- **Verification token**: `type="email_verification"`, 24h expiry, `sub=user_email`. Used only for the email link.
- **Session token**: no `type` field, 7-day expiry, `user_id`+`email`+`plan_tier`+`verified`. Used for all authenticated requests.

Never reuse the verification token as a session token.

### Google OAuth Server-Side Exchange

The Next.js API route at `/api/auth/google/callback` must:
1. Read `code` from URL query string
2. Exchange with Google Token endpoint: `POST https://oauth2.googleapis.com/token` with `code`, `client_id`, `client_secret`, `redirect_uri`, `grant_type=authorization_code`
3. Decode the `id_token` to get `sub`, `email`, `email_verified` (or call Google userinfo endpoint)
4. Forward to FastAPI — never expose `client_secret` to browser

Use `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` as server-only env vars (no `NEXT_PUBLIC_` prefix).

### Subscription Record on Registration

Every new user gets a `subscriptions` row immediately on registration:
```python
new_subscription = Subscription(
    user_id=new_user.id,
    plan_tier="growth",
    status="trialing",
    campaigns_used=0,
    clients_count=0,
    image_gen_used=0,
    billing_cycle_start=datetime.utcnow(),
    billing_cycle_end=datetime.utcnow() + timedelta(days=14),
)
```
The `stripe_sub_id` is null until the user upgrades. Plan limits for `growth` trialing: 5 clients, 30 campaigns, 30 image gens. These limits are enforced by `services/subscription.py` (Story 1.5 implements the enforcement fully; this story just creates the record).

### Registration Form Layout (Paper Style)

```
[Paper background, centered, no sidebar]

  Who are you? (not shown — this is just registration)

  PersonnaPress  ← logo/wordmark, Playfair Display H1

  [ Email address                    ]  ← Input Standard variant (border-bottom only)
  [ Password                         ]  ← Input Standard variant, type="password"
    Minimum 8 characters               ← helper text, Inter 12px Graphite

  [        Create account           ]   ← Button Primary (ink, hard shadow)

  ─── or ───

  [      Sign up with Google        ]   ← Button Secondary (ink border)

  Already have an account? Log in.     ← link to /login, Inter body
```

No exclamation marks. No "Let's get started!". Copy: calm, direct.

### Error Display Pattern

Inline errors ONLY — no toast for form validation errors:
```tsx
{error && (
  <p id="form-error" role="alert" className="text-sm text-danger mt-2">
    {error}
  </p>
)}
```
Associate with field via `aria-describedby="form-error"`.

### Architecture Rules for this Story

- `POST /api/v1/auth/register` is a public route (no auth dependency)
- Password hashing happens ONLY in `app/services/auth_service.py` → never in a router
- Resend SDK called ONLY from `app/integrations/email.py`
- Error responses always: `{"error": {"code": "...", "message": "...", "detail": {}}}`
- No business logic in `app/routers/auth.py` — delegate immediately to `auth_service`

### Project Structure Notes

New files this story creates:
```
backend/app/
├── routers/auth.py          ← register, verify, resend, google, logout (shell)
├── services/auth_service.py ← registration, verification, google auth logic
├── integrations/email.py    ← Resend email sending
├── schemas/auth.py          ← Request/response Pydantic models

frontend/app/
├── (auth)/
│   ├── register/
│   │   ├── page.tsx         ← Server Component shell
│   │   └── RegisterForm.tsx ← Client Component with form state
│   └── verify-email/
│       ├── page.tsx         ← "Check your inbox" page
│       └── confirm/page.tsx ← Verification token redemption
├── api/auth/google/callback/route.ts  ← OAuth code exchange (server-side)
middleware.ts                ← NEW FILE — JWT gate for (app)/ routes
```

### References

- Email/password auth spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]
- FR-1 (registration), AR-5 (Resend), AR-6 (jose), AR-7 (JWT cookie), AR-8 (Google OAuth): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- JWT cookie pattern, httpOnly flags: [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Registration form microcopy: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]
- Button/Input Paper Style specs: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Components]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- `subscriptions.stripe_sub_id` was `nullable=False` in the initial migration; added Alembic migration `2a7f3c8d1e04` to make it nullable. New registrations create a subscription without a Stripe sub ID (Stripe is wired in Story 1.5).
- Verification email link points to `/verify-email/confirm?token=` (frontend confirm page), not directly to the FastAPI endpoint. The confirm page calls the backend on load.
- Google OAuth flow: Next.js callback route exchanges the auth code server-side using `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (never exposed to browser), then forwards verified profile fields to FastAPI.
- Middleware gates `/dashboard`, `/clients`, `/campaigns`, `/settings` — routes inside the `(app)` layout group.
- `VerifyEmailConfirmClient` is wrapped in `<Suspense>` in its page because it uses `useSearchParams()`.

### File List

**Backend:**
- `backend/app/core/security.py` — updated: added `create_session_token`, `create_verification_token`, `decode_verification_token`, `set_session_cookie`
- `backend/app/schemas/auth.py` — new: `RegisterRequest`, `RegisterResponse`, `ResendVerificationRequest`, `GoogleCallbackRequest`
- `backend/app/integrations/email.py` — new: `send_verification_email` via Resend SDK
- `backend/app/services/auth_service.py` — new: `register_user`, `verify_email_token`, `resend_verification`, `auth_google`
- `backend/app/routers/auth.py` — updated: `POST /register`, `GET /verify-email`, `POST /resend-verification`, `POST /google`
- `backend/app/db/repositories/models.py` — updated: `Subscription.stripe_sub_id` made `Optional[str] = None`
- `backend/alembic/versions/2a7f3c8d1e04_make_stripe_sub_id_nullable.py` — new migration

**Frontend:**
- `frontend/app/(auth)/layout.tsx` — new: centered auth layout without sidebar
- `frontend/app/(auth)/register/page.tsx` — new: Server Component with metadata
- `frontend/app/(auth)/register/RegisterForm.tsx` — new: Client Component form
- `frontend/app/(auth)/verify-email/page.tsx` — new: "Check your inbox" Server Component
- `frontend/app/(auth)/verify-email/VerifyEmailClient.tsx` — new: resend button Client Component
- `frontend/app/(auth)/verify-email/confirm/page.tsx` — new: Suspense wrapper page
- `frontend/app/(auth)/verify-email/confirm/VerifyEmailConfirmClient.tsx` — new: token redemption Client Component
- `frontend/app/api/auth/google/callback/route.ts` — new: OAuth code exchange Route Handler
- `frontend/middleware.ts` — new: JWT gate for app routes

### Review Findings

**Code review performed:** 2026-06-15 | Sources: Blind Hunter + Edge Case Hunter + Acceptance Auditor

- [x] [Review][Decision] Google OAuth email-linking without re-authentication — Resolved: Option 1 with email_verified guard. Existing users linked only when Google confirms email_verified=true; unverified Google accounts are rejected with EMAIL_NOT_VERIFIED. [backend/app/services/auth_service.py]
- [x] [Review][Patch] OAuth CSRF: no `state` parameter in Google sign-up flow — Fixed: added `/api/auth/google/initiate` route that generates state, sets httpOnly cookie, redirects to Google. Callback validates state against cookie. [frontend/app/api/auth/google/initiate/route.ts, frontend/app/api/auth/google/callback/route.ts]
- [x] [Review][Patch] JWT Secret fallback "change-me-in-production" if `JWT_SECRET` env var missing — Fixed: middleware throws at startup if JWT_SECRET is missing. [frontend/middleware.ts]
- [x] [Review][Patch] `decode_session_token` has no try/except — Fixed: wraps JWTError → HTTPException(401) with distinct messages for expired vs invalid. [backend/app/core/security.py]
- [x] [Review][Patch] All `JWTError` subtypes in `verify_email_token` map to TOKEN_EXPIRED — Fixed: catches `ExpiredSignatureError` → TOKEN_EXPIRED; other `JWTError` → TOKEN_INVALID. [backend/app/services/auth_service.py]
- [x] [Review][Patch] Sync `send_verification_email` blocks asyncio event loop — Fixed: wrapped with `asyncio.to_thread()` in both `register_user` and `resend_verification`. [backend/app/services/auth_service.py]
- [x] [Review][Patch] Silent email send failure swallowed with no logging — Fixed: `logger.exception()` in both email-send except blocks. [backend/app/services/auth_service.py]
- [x] [Review][Patch] Set-cookie relay in Google OAuth route uses `headers.set()` (overwrites) — Fixed: changed to `response.headers.append("set-cookie", ...)`. [frontend/app/api/auth/google/callback/route.ts]
- [x] [Review][Patch] `verify_email_token` issues session cookie via cross-origin browser fetch — Fixed: created `/api/auth/verify-email` Next.js proxy route; `VerifyEmailConfirmClient` now calls it instead of FastAPI directly. [frontend/app/api/auth/verify-email/route.ts, frontend/app/(auth)/verify-email/confirm/VerifyEmailConfirmClient.tsx]
- [x] [Review][Patch] `redirect_url` from backend JSON not validated before use — Fixed: `safeRedirectPath()` allowlist (`/onboarding`, `/dashboard`) in both `VerifyEmailConfirmClient` and callback route. [frontend/app/(auth)/verify-email/confirm/VerifyEmailConfirmClient.tsx, frontend/app/api/auth/google/callback/route.ts]
- [x] [Review][Patch] Google OAuth new user gets `verified=email_verified` instead of `verified=True` — Fixed: new users always get `verified=True`; email_verified guard is now an upfront check. [backend/app/services/auth_service.py]
- [x] [Review][Patch] `ResendVerificationRequest.email` uses plain `str` instead of `EmailStr` — Fixed. [backend/app/schemas/auth.py]
- [x] [Review][Patch] `GoogleCallbackRequest.email` uses plain `str` instead of `EmailStr`; `google_sub` has no length constraint — Fixed: `EmailStr`, `max_length=255` via `Annotated[str, Field(...)]`. [backend/app/schemas/auth.py]
- [x] [Review][Patch] Middleware only protects 4 named routes; `(app)/` group not fully covered — Fixed: matcher expanded to include `/onboarding`; inner redundant regex removed. [frontend/middleware.ts]
- [x] [Review][Patch] `VerifyEmailClient` silently returns null when `email` prop absent — Fixed: shows email input form when prop absent so user can still trigger resend. [frontend/app/(auth)/verify-email/VerifyEmailClient.tsx]
- [x] [Review][Patch] `verify_email_token` returns same TOKEN_INVALID for already-verified and user-not-found — Fixed: already-verified users silently receive a session token and redirect to `/onboarding`. [backend/app/services/auth_service.py]
- [x] [Review][Patch] `middleware.ts` inner regex and `config.matcher` are redundant and can diverge — Fixed: inner regex removed; matcher is the sole route filter. [frontend/middleware.ts]
- [x] [Review][Patch] `TRIAL_DAYS = 14` hardcoded constant duplicated across service — Fixed: moved to `settings.TRIAL_DAYS` in `config.py`. [backend/app/core/config.py, backend/app/services/auth_service.py]
- [x] [Review][Patch] `resend.api_key` mutated globally on every call — Fixed: set once at module level in `email.py`. [backend/app/integrations/email.py]
- [x] [Review][Defer] Stale `plan_tier`/`verified` claims in JWT after plan change — architectural JWT tradeoff, no revocation in scope [backend/app/core/security.py] — deferred, pre-existing
- [x] [Review][Defer] Session token has no refresh/rotation mechanism — out of scope for story 1.2 — deferred, pre-existing
- [x] [Review][Defer] `auth_google` always redirects to `/onboarding` for returning users — spec-compliant; no dashboard route exists yet — deferred, pre-existing
- [x] [Review][Defer] `_get_key()` silently pads/truncates CREDENTIAL_ENCRYPTION_KEY — pre-existing from story 1.1 [backend/app/core/security.py] — deferred, pre-existing
- [x] [Review][Defer] Backend `resend_verification` has no server-side rate limiting — requires Redis/infra, out of scope for story 1.2 — deferred, out of scope
