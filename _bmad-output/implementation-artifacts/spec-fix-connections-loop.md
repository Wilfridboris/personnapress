---
title: 'Fix connections page RSC render loop'
type: 'bugfix'
created: '2026-07-04'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** The Platform Connections page (`/clients/{id}/connections`) fired 15+ repeated RSC re-renders after OAuth redirect, flooding the backend with `GET /api/v1/clients/{id}` requests at ~400ms/request. Root cause: `useSearchParams()` created a reactive Suspense subscription, and `router.replace()` stripped the `?success=...` param — but the RSC had `cache: "no-store"`, so Next.js treated the replacement as a cold navigation → unmounted + remounted the client component → effect re-ran → another `router.replace()` → loop.

**Approach:** Remove `useSearchParams()` (replaced by an imperative `new URLSearchParams(window.location.search)` read) and drop `router.replace()` entirely. Use `useRef` to guarantee the toast fires at most once per mount. Disable global `refetchOnWindowFocus` in the QueryClient to prevent unrelated queries from re-firing on every tab switch. Also commit leftover story-5-6 backend changes (rate-limit defaults, auth decorators, Platform enum, Alembic migration).

## Suggested Review Order

- `frontend/components/publishing/PlatformConnectionsClient.tsx:15` — core loop fix: removed `useSearchParams`/`router.replace`, added `handledRef` guard
- `frontend/app/providers.tsx:18` — global `refetchOnWindowFocus: false`
- `backend/app/core/rate_limit.py:4` — default rate limit 10→200/min (auth endpoints retain tight per-decorator limits)
- `backend/app/routers/auth.py:22` — explicit `@limiter.limit` on register/login/resend/google
- `backend/app/db/repositories/models.py:17` — `wordpress_com` added to Platform enum + `values_callable` fix for Python 3.11 StrEnum serialisation
- `backend/alembic/versions/a1b2c3d4e5f6_add_wordpress_com_to_platform_enum.py:19` — `ALTER TYPE platform_enum ADD VALUE 'wordpress-com'` in autocommit block
- `frontend/.env.example:23` — `WP_COM_CLIENT_ID` documentation

## Spec Change Log

