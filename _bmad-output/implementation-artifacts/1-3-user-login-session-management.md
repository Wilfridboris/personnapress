---
baseline_commit: 7d911881382520f33fe6bbb6be9a3bc4016c8cb3
---

# Story 1.3: User Login & Session Management

Status: done

## Story

As a registered user,
I want to log in with my email and password or via Google and stay authenticated across browser sessions,
So that I can access PersonnaPress without re-authenticating every visit.

## Acceptance Criteria

1. **Given** a verified user submits valid email and password credentials, **When** `POST /api/v1/auth/login` is processed, **Then** FastAPI verifies the password with bcrypt, issues a JWT (payload: `user_id`, `email`, `plan_tier`, `exp`), sets it as an httpOnly cookie (`secure=True`, `samesite=lax`, 7-day expiry), and Next.js redirects the user to `/dashboard`.

2. **Given** a user submits an incorrect email or password, **When** the login form is submitted, **Then** a generic error message is returned: "Invalid email or password." — no indication of which field is incorrect, no lockout in v1.

3. **Given** an unverified user attempts to log in with email/password, **When** the form is submitted, **Then** the API returns "Please verify your email before logging in." with a "Resend verification email" link.

4. **Given** a logged-in user closes and reopens the browser within 7 days, **When** they visit any `(app)/` route, **Then** Next.js middleware reads the httpOnly cookie, validates the JWT using the `jose` library (edge-runtime compatible), extracts `plan_tier` from the payload, and grants access — no re-login required.

5. **Given** Next.js middleware validates the JWT, **When** the middleware runs on the Vercel edge runtime, **Then** it uses `jose` for JWT verification (not a Node.js-only library), and the `JWT_SECRET` is read from a server-side environment variable only (never `NEXT_PUBLIC_`).

6. **Given** a logged-in user visits `/login` or `/register`, **When** middleware detects a valid JWT cookie, **Then** the user is immediately redirected to `/dashboard` — authenticated users are never shown the login/register pages.

7. **Given** a logged-in user clicks "Log out," **When** the logout action completes (`POST /api/v1/auth/logout`), **Then** the httpOnly cookie is cleared (set to empty string with immediate expiry), the user is redirected to `/login`, and the prior session JWT cannot be reused for authenticated requests.

8. **Given** a returning Google OAuth user clicks "Sign in with Google," **When** the OAuth flow completes, **Then** the same user record is found via `google_sub`, a new JWT cookie is issued, and they are redirected to `/dashboard`.

## Tasks / Subtasks

- [x] Task 1: Backend — `POST /api/v1/auth/login` (AC: #1, #2, #3)
  - [x] 1.1 Add `POST /api/v1/auth/login` route in `app/routers/auth.py`
  - [x] 1.2 Create `LoginRequest` schema: `email: str`, `password: str`
  - [x] 1.3 In `auth_service.py` add `login_user()`: fetch user by email → if not found return generic error → verify bcrypt hash via `passlib` → if not verified return "Please verify your email before logging in." → issue session JWT → set httpOnly cookie
  - [x] 1.4 Generic error for wrong credentials: HTTP 401 with `{"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password.", "detail": {}}}`
  - [x] 1.5 Unverified user error: HTTP 403 with `{"error": {"code": "EMAIL_NOT_VERIFIED", "message": "Please verify your email before logging in.", "detail": {}}}`
  - [x] 1.6 Success response: HTTP 200 with `{"success": true}` plus the JWT cookie set on the response

- [x] Task 2: Backend — `POST /api/v1/auth/logout` (AC: #7)
  - [x] 2.1 Add `POST /api/v1/auth/logout` route (requires auth — any authenticated user can call it)
  - [x] 2.2 Clear the `session` cookie: `response.delete_cookie(key="session", path="/")`
  - [x] 2.3 Return `{"success": true}`; no server-side token invalidation (stateless JWT in v1)

- [x] Task 3: Frontend — `proxy.ts` (AC: #4, #5, #6)
  - [x] 3.1 Create `frontend/proxy.ts` at the root of `frontend/` (Next.js 16: `middleware.ts` deprecated → renamed to `proxy.ts`; function renamed to `proxy`)
  - [x] 3.2 Import from `jose` only — NOT from `jsonwebtoken`, `next-auth`, or any Node.js-only JWT lib
  - [x] 3.3 Read `JWT_SECRET` from `process.env.JWT_SECRET` (server-side env var, not `NEXT_PUBLIC_`)
  - [x] 3.4 On every request to `(app)/` routes: read `session` cookie → `jwtVerify(token, secret)` with `jose` → if invalid/missing → redirect to `/login`
  - [x] 3.5 If JWT payload has `verified=false` → redirect to `/verify-email` (this guards unverified users already registered)
  - [x] 3.6 On requests to `/login` or `/register` with a valid JWT: redirect to `/dashboard`
  - [x] 3.7 Use `NextResponse.redirect()` for all redirects in proxy; set `matcher` config to exclude `_next/static`, `_next/image`, `favicon.ico`, and API routes
  - [x] 3.8 Attach `user_id` and `plan_tier` from JWT payload to request headers for Server Components downstream (via `NextResponse.next({ request: { headers: requestHeaders } })`)

- [x] Task 4: Frontend — `/login` page (AC: #1, #2, #3, #6, #8)
  - [x] 4.1 Create `frontend/app/(auth)/login/page.tsx` — Server Component with metadata
  - [x] 4.2 Create `frontend/app/(auth)/login/LoginForm.tsx` — Client Component
  - [x] 4.3 Form fields (Paper Style): Email (`<Input>` Standard, `id="email"`, explicit `<label>`), Password (`<Input type="password"`, `id="password"`, explicit `<label>`), "Log in" Primary `<Button>`
  - [x] 4.4 On success (API returns 200 with cookie set): call `router.push('/dashboard')` — `useRouter` from `next/navigation`
  - [x] 4.5 On `INVALID_CREDENTIALS` (401): show "Invalid email or password." below the form via `aria-describedby`
  - [x] 4.6 On `EMAIL_NOT_VERIFIED` (403): show "Please verify your email before logging in." with a "Resend verification email" text link (calls `POST /api/v1/auth/resend-verification`)
  - [x] 4.7 "Sign in with Google" Secondary `<Button>` — same Google OAuth flow as Story 1.2; redirects to `/dashboard` on success
  - [x] 4.8 Link to `/register`: "No account? Create one."
  - [x] 4.9 Page layout: same centered-card auth layout as `/register` — no sidebar

- [x] Task 5: Frontend — Logout action (AC: #7)
  - [x] 5.1 Create `frontend/lib/auth.ts` with `logout()` async function: `POST /api/v1/auth/logout` with `credentials: 'include'` → on success call `router.push('/login')` (defensive: redirects in `finally` block)
  - [x] 5.2 Wire "Log out" link in the sidebar (added in Story 1.4) to call `logout()` — for now expose the function; Story 1.4 connects it to the UI

- [x] Task 6: Frontend — API utility setup (AC: #4)
  - [x] 6.1 Update `frontend/lib/api.ts` to export a `fetchAPI` utility: wraps `fetch(NEXT_PUBLIC_API_URL + path, { credentials: 'include', ...opts })` with JSON parse and error extraction from `{"error": {...}}` shape
  - [x] 6.2 All API calls in this story and subsequent stories use `fetchAPI` — never raw `fetch` inline in components

## Dev Notes

### Dependency on Story 1.2

- `app/routers/auth.py` must exist (created in Story 1.2)
- `app/services/auth_service.py` must exist with `create_session_token()`
- `users.verified` field must be in the JWT payload (established in Story 1.2)
- `(auth)/` route group layout must exist (no sidebar)

### Next.js Middleware — Critical Implementation Notes

`middleware.ts` runs on the Vercel **edge runtime**. Node.js built-ins are unavailable. This is why `jose` is required over `jsonwebtoken`:

```typescript
// frontend/middleware.ts
import { NextRequest, NextResponse } from 'next/server'
import { jwtVerify } from 'jose'

const secret = new TextEncoder().encode(process.env.JWT_SECRET)

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Public routes that never need auth check
  const isPublicRoute = pathname.startsWith('/login') ||
    pathname.startsWith('/register') ||
    pathname.startsWith('/verify-email') ||
    pathname.startsWith('/api/auth/') ||
    pathname.startsWith('/api/webhooks/')

  const sessionCookie = request.cookies.get('session')?.value

  if (!isPublicRoute) {
    if (!sessionCookie) return NextResponse.redirect(new URL('/login', request.url))
    try {
      const { payload } = await jwtVerify(sessionCookie, secret)
      if (!payload.verified) return NextResponse.redirect(new URL('/verify-email', request.url))
      // Propagate identity to server components
      const response = NextResponse.next()
      response.headers.set('x-user-id', payload.user_id as string)
      response.headers.set('x-plan-tier', payload.plan_tier as string)
      return response
    } catch {
      // JWT invalid or expired — clear cookie and redirect
      const response = NextResponse.redirect(new URL('/login', request.url))
      response.cookies.delete('session')
      return response
    }
  }

  // Redirect authenticated users away from public auth pages
  if ((pathname === '/login' || pathname === '/register') && sessionCookie) {
    try {
      await jwtVerify(sessionCookie, secret)
      return NextResponse.redirect(new URL('/dashboard', request.url))
    } catch { /* expired — let them see login */ }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|public/).*)'],
}
```

**Warning:** Do NOT use `process.env.JWT_SECRET` in `config` — it must be read at runtime, not build time.

### Login Page Layout (Paper Style)

```
[Centered card, no sidebar, Paper background]

  PersonnaPress              ← Playfair Display H1

  [ Email address           ]  ← Input Standard
  [ Password                ]  ← Input Standard, type="password"

  [         Log in          ]  ← Button Primary

  ─── or ───

  [     Sign in with Google ]  ← Button Secondary

  No account? Create one.     ← link to /register
```

Error appears between the Password field and the Log in button.

### fetchAPI Utility

```typescript
// frontend/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL

export async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  const data = await res.json()

  if (!res.ok) {
    // data.error.message per architecture standard
    throw new Error(data?.error?.message ?? 'Something went wrong.')
  }

  return data as T
}
```

Use `fetchAPI` everywhere — never raw `fetch` with inline error handling.

### Google OAuth for Login (Returning User)

The same Next.js `/api/auth/google/callback` route from Story 1.2 handles both sign-up and sign-in. FastAPI's `POST /api/v1/auth/google` does `upsert` logic: find by `google_sub` → if found, issue new JWT; if not found, create user. Redirect destination differs based on whether user has `onboarding_completed` (checked in this call, redirect to `/onboarding` or `/dashboard`). For v1, redirect to `/dashboard` for returning users (no onboarding flag yet — that's Story 2.7/3.5).

### Architecture Rules for this Story

- `POST /api/v1/auth/login` and `POST /api/v1/auth/logout` are thin router methods — delegate to `auth_service`
- `middleware.ts` must use `jose` exclusively; `JWT_SECRET` is server-side only
- Logout does not invalidate the JWT server-side (stateless JWT); the cookie deletion is sufficient
- All API calls from the frontend use `fetchAPI` from `lib/api.ts` with `credentials: 'include'`
- No `NEXT_PUBLIC_JWT_SECRET` — the secret is only in `process.env.JWT_SECRET` read server-side in middleware

### Project Structure Notes

New files this story adds:
```
frontend/
├── middleware.ts                         ← NEW — JWT gate, runs on edge
├── app/(auth)/login/
│   ├── page.tsx                          ← NEW
│   └── LoginForm.tsx                     ← NEW
└── lib/auth.ts                           ← NEW — logout() utility
```

Updated files:
```
frontend/lib/api.ts                       ← UPDATE — add fetchAPI wrapper
backend/app/routers/auth.py               ← UPDATE — add login, logout routes
backend/app/services/auth_service.py      ← UPDATE — add login_user()
```

### References

- Login & session spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- FR-2 (auth), AR-6 (jose edge runtime), AR-7 (JWT cookie), AR-8 (Google OAuth): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- `jose` requirement for edge runtime: [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Frontend error handling pattern: [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns]
- Login page microcopy rules: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Next.js 16 breaking change: `middleware.ts` → `proxy.ts`, function `middleware` → `proxy`. Edge runtime no longer supported in proxy (Node.js only). Story spec said `middleware.ts` but Next.js 16 docs (`node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md`) explicitly deprecate it. Implemented as `proxy.ts` with `export function proxy(...)`.
- Header propagation to RSC: must use `NextResponse.next({ request: { headers: requestHeaders } })` not `response.headers.set(...)` which only sets response headers visible to clients.
- bcrypt/passlib incompatibility in Python 3.14 test environment: test suite mocks `_pwd_ctx.verify` instead of doing real bcrypt hashing to avoid version conflicts between passlib 1.7.4 and bcrypt 4.x.

### Completion Notes List

- Implemented `POST /api/v1/auth/login`: fetches user by email, verifies bcrypt hash via passlib, returns 401 for bad credentials (including Google-only users with no hashed_password), 403 for unverified users, 200 + session cookie on success.
- Implemented `POST /api/v1/auth/logout`: stateless — deletes session cookie, returns `{"success": true}`.
- Created `frontend/proxy.ts` (Next.js 16 replacement for middleware.ts): jose-based JWT gate on all non-public routes; propagates `x-user-id` and `x-plan-tier` to Server Components via request headers.
- Created `/login` page (Server Component + `LoginForm` Client Component): Paper Style layout matching `/register`, handles all error states (INVALID_CREDENTIALS, EMAIL_NOT_VERIFIED), Google OAuth sign-in, link to `/register`.
- Created `frontend/lib/auth.ts` with `logout()` utility (defensive — redirects in `finally` block).
- Exported `fetchAPI` from `frontend/lib/api.ts`; existing `apiFetch` delegates to it for backward compatibility.
- Test infrastructure: `backend/pytest.ini`, `backend/tests/conftest.py` (stubs `resend`), `backend/tests/test_auth_login.py` (6 unit tests, all passing).

### File List

**New files:**
- `backend/pytest.ini`
- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth_login.py`
- `frontend/proxy.ts`
- `frontend/app/(auth)/login/page.tsx`
- `frontend/app/(auth)/login/LoginForm.tsx`
- `frontend/lib/auth.ts`

**Modified files:**
- `backend/app/schemas/auth.py` — added `LoginRequest`
- `backend/app/services/auth_service.py` — added `login_user()`
- `backend/app/routers/auth.py` — added login and logout routes
- `frontend/lib/api.ts` — exported `fetchAPI`
- `_bmad-output/implementation-artifacts/1-3-user-login-session-management.md` — story tracking
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — status updates

## Review Findings

- [x] [Review][Patch] Delete `middleware.ts` — replaced by `proxy.ts` in Next.js 16; old file was dead code [frontend/middleware.ts]
- [x] [Review][Patch] Add `JWT_SECRET` startup guard in `proxy.ts` — undefined env var was silently encoding `"undefined"` as secret [frontend/proxy.ts:4]
- [x] [Review][Patch] `fetchAPI`: guard `res.json()` against non-JSON error bodies — SyntaxError on 502/HTML responses [frontend/lib/api.ts:16]
- [x] [Review][Patch] `fetchAPI`: restore FastAPI `detail` fallback for 422 validation errors [frontend/lib/api.ts:20]
- [x] [Review][Patch] Timing attack: run dummy bcrypt verify for unknown/Google-only users — prevented email enumeration via response-time delta [backend/app/services/auth_service.py:130]
- [x] [Review][Patch] `logout()`: remove `finally` redirect — cookie stays alive if backend unreachable, causing proxy redirect loop [frontend/lib/auth.ts:5]
- [x] [Review][Patch] `login_user`: use `bool(user.verified)` instead of hardcoded `True` in `create_session_token` [backend/app/services/auth_service.py:145]
- [x] [Review][Patch] `LoginForm`: use `APIError.code` for error routing — substring matching was fragile dead code [frontend/app/(auth)/login/LoginForm.tsx:33]
- [x] [Review][Patch] Add `router.refresh()` before `router.push('/dashboard')` — prevents stale RSC cache after login [frontend/app/(auth)/login/LoginForm.tsx:29]
- [x] [Review][Patch] `delete_cookie`: add `httponly=True, secure=True, samesite="lax"` to match original cookie attributes [backend/app/services/auth_service.py (logout_user)]
- [x] [Review][Patch] Delegate logout to `auth_service.logout_user()` per architecture spec [backend/app/routers/auth.py:40]
- [x] [Review][Patch] `LoginRequest.password`: add `min_length=1, max_length=128` [backend/app/schemas/auth.py:26]
- [x] [Review][Patch] `handleResendVerification`: add `sending`/`sent`/`error` feedback states [frontend/app/(auth)/login/LoginForm.tsx:48]
- [x] [Review][Patch] Capture email into `verificationEmail` at error time — prevents resend using a modified field value [frontend/app/(auth)/login/LoginForm.tsx:35]
- [x] [Review][Defer] No rate limiting on `POST /api/v1/auth/login` [backend/app/routers/auth.py:35] — deferred, pre-existing
- [x] [Review][Defer] `x-user-id`/`x-plan-tier` headers can be spoofed if backend is directly accessible [frontend/proxy.ts:28] — deferred, architectural concern

## Change Log

- 2026-06-28: Implemented Story 1.3 — email/password login, logout, Next.js 16 proxy JWT gate, login page, fetchAPI utility, and logout helper. Key deviation: `frontend/proxy.ts` used instead of deprecated `middleware.ts` per Next.js 16 breaking change. All 6 backend unit tests pass; TypeScript type check clean.
