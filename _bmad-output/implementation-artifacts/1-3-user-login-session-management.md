# Story 1.3: User Login & Session Management

Status: ready-for-dev

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

- [ ] Task 1: Backend — `POST /api/v1/auth/login` (AC: #1, #2, #3)
  - [ ] 1.1 Add `POST /api/v1/auth/login` route in `app/routers/auth.py`
  - [ ] 1.2 Create `LoginRequest` schema: `email: str`, `password: str`
  - [ ] 1.3 In `auth_service.py` add `login_user()`: fetch user by email → if not found return generic error → verify bcrypt hash via `passlib` → if not verified return "Please verify your email before logging in." → issue session JWT → set httpOnly cookie
  - [ ] 1.4 Generic error for wrong credentials: HTTP 401 with `{"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password.", "detail": {}}}`
  - [ ] 1.5 Unverified user error: HTTP 403 with `{"error": {"code": "EMAIL_NOT_VERIFIED", "message": "Please verify your email before logging in.", "detail": {}}}`
  - [ ] 1.6 Success response: HTTP 200 with `{"success": true}` plus the JWT cookie set on the response

- [ ] Task 2: Backend — `POST /api/v1/auth/logout` (AC: #7)
  - [ ] 2.1 Add `POST /api/v1/auth/logout` route (requires auth — any authenticated user can call it)
  - [ ] 2.2 Clear the `session` cookie: `response.delete_cookie(key="session", path="/")`
  - [ ] 2.3 Return `{"success": true}`; no server-side token invalidation (stateless JWT in v1)

- [ ] Task 3: Frontend — `middleware.ts` (AC: #4, #5, #6)
  - [ ] 3.1 Create `frontend/middleware.ts` at the root of `frontend/` (not inside `app/`)
  - [ ] 3.2 Import from `jose` only — NOT from `jsonwebtoken`, `next-auth`, or any Node.js-only JWT lib
  - [ ] 3.3 Read `JWT_SECRET` from `process.env.JWT_SECRET` (server-side env var, not `NEXT_PUBLIC_`)
  - [ ] 3.4 On every request to `(app)/` routes: read `session` cookie → `jwtVerify(token, secret)` with `jose` → if invalid/missing → redirect to `/login`
  - [ ] 3.5 If JWT payload has `verified=false` → redirect to `/verify-email` (this guards unverified users already registered)
  - [ ] 3.6 On requests to `/login` or `/register` with a valid JWT: redirect to `/dashboard`
  - [ ] 3.7 Use `NextResponse.redirect()` for all redirects in middleware; set `matcher` config to exclude `_next/static`, `_next/image`, `favicon.ico`, and API routes
  - [ ] 3.8 Attach `user_id` and `plan_tier` from JWT payload to request headers for Server Components downstream (via `response.headers.set('x-user-id', payload.user_id)`)

- [ ] Task 4: Frontend — `/login` page (AC: #1, #2, #3, #6, #8)
  - [ ] 4.1 Create `frontend/app/(auth)/login/page.tsx` — Server Component with metadata
  - [ ] 4.2 Create `frontend/app/(auth)/login/LoginForm.tsx` — Client Component
  - [ ] 4.3 Form fields (Paper Style): Email (`<Input>` Standard, `id="email"`, explicit `<label>`), Password (`<Input type="password"`, `id="password"`, explicit `<label>`), "Log in" Primary `<Button>`
  - [ ] 4.4 On success (API returns 200 with cookie set): call `router.push('/dashboard')` — React Router `useRouter` from `next/navigation`
  - [ ] 4.5 On `INVALID_CREDENTIALS` (401): show "Invalid email or password." below the form via `aria-describedby`
  - [ ] 4.6 On `EMAIL_NOT_VERIFIED` (403): show "Please verify your email before logging in." with a "Resend verification email" text link (calls `POST /api/v1/auth/resend-verification`)
  - [ ] 4.7 "Sign in with Google" Secondary `<Button>` — same Google OAuth flow as Story 1.2; redirects to `/dashboard` on success
  - [ ] 4.8 Link to `/register`: "No account? Create one."
  - [ ] 4.9 Page layout: same centered-card auth layout as `/register` — no sidebar

- [ ] Task 5: Frontend — Logout action (AC: #7)
  - [ ] 5.1 Create `frontend/lib/auth.ts` with `logout()` async function: `POST /api/v1/auth/logout` with `credentials: 'include'` → on success call `router.push('/login')`
  - [ ] 5.2 Wire "Log out" link in the sidebar (added in Story 1.4) to call `logout()` — for now expose the function; Story 1.4 connects it to the UI

- [ ] Task 6: Frontend — API utility setup (AC: #4)
  - [ ] 6.1 Update `frontend/lib/api.ts` to export a `fetchAPI` utility: wraps `fetch(NEXT_PUBLIC_API_URL + path, { credentials: 'include', ...opts })` with JSON parse and error extraction from `{"error": {...}}` shape
  - [ ] 6.2 All API calls in this story and subsequent stories use `fetchAPI` — never raw `fetch` inline in components

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

### Completion Notes List

### File List
