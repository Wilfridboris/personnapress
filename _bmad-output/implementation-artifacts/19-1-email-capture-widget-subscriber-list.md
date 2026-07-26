---
baseline_commit: 955e634
---

# Story 19.1: Email Capture Widget — Pre-launch Subscriber List via Resend

Status: done

## Story

As Boris (founder),
I want an email capture widget on every public-facing page,
so that I can build a 500+ subscriber list before the Product Hunt launch using Resend's contact/segments feature as the backend — no additional tool needed.

## Acceptance Criteria

1. **Given** any visitor lands on the homepage, `/pricing`, `/about`, or any `/blog/[slug]` page, **When** they scroll to the bottom of the main content (above the footer), **Then** an `EmailCaptureWidget` section is visible with heading "Get the free Brand Voice Audit checklist", a bottom-border-only email input, and a primary Ink-fill button labeled "Get the checklist".

2. **Given** a visitor types a valid email and clicks "Get the checklist", **When** the form submits, **Then** the button shows "Sending…" text (disabled, no spinner — text change only), a `POST` request fires to `/api/email-capture` with `{ email, source }`, and the page does not reload.

3. **Given** the POST to `/api/email-capture` returns 200, **When** the response arrives, **Then** the form is replaced inline (no page reload) by a success state: a `CheckCircle` icon + text `"You're on the list. We'll send your free Brand Voice Audit checklist shortly."` — animated via `.animate-fade-in-up`.

4. **Given** the POST returns a non-200 or the network fails, **When** the error occurs, **Then** a `role="alert"` error message appears below the input in `text-danger` (`#8B0000`): `"Something went wrong. Please try again."` — the form remains usable.

5. **Given** a visitor submits an email that is already in Resend, **When** the API responds with a duplicate/409, **Then** the frontend treats it as success (same success state) — re-subscribing is not an error.

6. **Given** the Next.js API route `POST /api/email-capture` receives a request, **When** processed, **Then** it calls `resend.contacts.create()` with `{ email, unsubscribed: false, properties: { source } }` plus `audience_id: RESEND_AUDIENCE_ID` from env, validates email format server-side before calling Resend, and returns `{ subscribed: true }` on success.

7. **Given** `RESEND_AUDIENCE_ID` or `RESEND_API_KEY` is missing from env, **When** the API route is called, **Then** it logs a warning and returns 500 — it does NOT expose the missing key name in the response body.

8. **Given** the widget renders on mobile (< 640px), **When** the layout is inspected, **Then** the input and button are stacked vertically (full-width). At `sm:` breakpoint and above they sit side by side (input flex-1, button fixed width).

9. **Given** the widget renders, **When** accessibility is checked, **Then**: the input has `id="email-capture-input"` with a `<label>` (visually hidden via `sr-only`); error message has `role="alert"`; button has `aria-disabled` when loading; the section has `aria-label="Newsletter signup"`.

10. **Given** `.env.local` (frontend) and `.env.local.example` are inspected, **When** the new keys are checked, **Then** both files contain `RESEND_API_KEY` and `RESEND_AUDIENCE_ID` — `RESEND_API_KEY` has the same value as the backend env var (same Resend account); `.env.local.example` has placeholder values with comments.

11. **Given** a new user completes email verification (`verify_email_token`), **When** `user.verified` is set to `True` and committed, **Then** `add_contact_to_audience(email, source="signup")` is called in a fire-and-forget `asyncio.to_thread` — a Resend failure must NOT raise or block the login response.

12. **Given** a new user registers via Google OAuth (new user branch in `auth_google`), **When** the new `User` row is committed, **Then** `add_contact_to_audience(email, source="google_signup")` is called the same way — fire-and-forget, never blocking login.

## Dev Notes

### User-facing Copy Rule

**No em-dashes (`—`) anywhere in user-facing text.** This applies to all UI labels, button text, descriptions, success/error messages, and any copy rendered to the user.

### Resend API — Contacts Endpoint (verified 2026-07-26)

**Key facts from official docs:**
- Endpoint: `POST https://api.resend.com/contacts`
- Required field: `email` (string)
- Optional: `first_name`, `last_name`, `unsubscribed` (bool), `properties` (custom key-value object), `segments` (array of segment IDs), `topics` (array)
- **Audiences are deprecated** in favor of Segments — but the `audience_id` param on the older endpoint still works. Use `RESEND_AUDIENCE_ID` to store whichever ID (audience or segment) Boris creates in the Resend dashboard.
- Duplicate handling: not explicitly documented — treat any `4xx` on a duplicate as success (AC5).
- Response shape: `{ object: "contact", id: "uuid" }`

**Using the `resend` npm package (already a dep on backend; add to frontend):**
```typescript
// frontend/app/api/email-capture/route.ts
import { Resend } from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

// Add contact to audience
await resend.contacts.create({
  audienceId: process.env.RESEND_AUDIENCE_ID!,
  email,
  unsubscribed: false,
  properties: { source },
});
```

> **Check first:** Run `npm list resend` in `frontend/`. If not installed, add it: `npm install resend`. The backend already has `resend` as a Python package but the frontend needs the npm package separately.

### EmailCaptureWidget — Paper Style Specs

Follow Paper Style strictly — no rounded corners, no glassmorphism, no dark mode variants:

```tsx
// frontend/components/marketing/EmailCaptureWidget.tsx
'use client';

import { useState } from 'react';
import { CheckCircle } from 'lucide-react';

export function EmailCaptureWidget({ source = 'homepage' }: { source?: string }) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('loading');
    setErrorMsg('');
    try {
      const res = await fetch('/api/email-capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source }),
      });
      // Treat 4xx (duplicate) as success per AC5
      if (!res.ok && res.status >= 500) throw new Error();
      setStatus('success');
    } catch {
      setStatus('error');
      setErrorMsg('Something went wrong. Please try again.');
    }
  }

  if (status === 'success') {
    return (
      <section aria-label="Newsletter signup" className="border-t border-border py-12 md:py-16">
        <div className="max-w-xl mx-auto px-4 text-center flex flex-col items-center gap-3 animate-fade-in-up">
          <CheckCircle className="size-8 text-success" aria-hidden="true" />
          <p className="font-body text-base text-ink">
            <span className="font-semibold">You're on the list.</span>{' '}
            We'll send your free Brand Voice Audit checklist shortly.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Newsletter signup" className="border-t border-border py-12 md:py-16">
      <div className="max-w-xl mx-auto px-4">
        {/* Label chip */}
        <p className="font-body text-xs uppercase tracking-[0.06em] text-graphite mb-2">
          Free resource
        </p>
        {/* Heading — Playfair via font-display token */}
        <h2 className="font-display text-2xl md:text-3xl text-ink mb-2 text-balance">
          Get the free Brand Voice Audit checklist
        </h2>
        <p className="font-body text-sm text-graphite mb-8 text-pretty">
          12 questions to find your writing fingerprint. Stop your content from sounding like everyone else's.
        </p>

        <form onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col sm:flex-row sm:items-end gap-3 sm:gap-0">
            <div className="flex-1">
              <label htmlFor="email-capture-input" className="sr-only">
                Email address
              </label>
              <input
                id="email-capture-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={status === 'loading'}
                placeholder="Your email address"
                aria-invalid={status === 'error'}
                aria-describedby={status === 'error' ? 'email-capture-error' : undefined}
                className="w-full bg-transparent border-0 border-b-2 border-border px-0 py-2
                           font-body text-base text-ink placeholder:text-graphite
                           focus:outline-none focus:border-ink focus-visible:outline-none
                           transition-colors duration-150
                           disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            <button
              type="submit"
              disabled={status === 'loading'}
              aria-disabled={status === 'loading'}
              className="sm:ml-4 px-5 py-2 font-body text-sm font-semibold uppercase tracking-[0.06em]
                         bg-ink text-white border border-ink shadow-brutal
                         hover:bg-white hover:text-ink
                         transition-colors duration-150
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2
                         disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {status === 'loading' ? 'Sending…' : 'Get the checklist'}
            </button>
          </div>

          {status === 'error' && (
            <p
              id="email-capture-error"
              role="alert"
              className="mt-2 font-body text-sm text-danger animate-fade-in"
            >
              {errorMsg}
            </p>
          )}
        </form>
      </div>
    </section>
  );
}
```

**Motion decision:** CSS-only (`.animate-fade-in-up`, `.animate-fade-in` from `globals.css`). No Framer Motion — no exit animation needed, no shared layout.

### Placement in Existing Pages

Add `<EmailCaptureWidget source="X" />` **above** `<PublicFooter />` in each target page. Check how each page imports `PublicFooter` to insert at the right place:

| File | Source value |
|------|-------------|
| `frontend/app/page.tsx` | `"homepage"` |
| `frontend/app/(public)/pricing/page.tsx` | `"pricing"` |
| `frontend/app/(public)/about/page.tsx` | `"about"` |
| `frontend/app/(public)/blog/[slug]/page.tsx` | `"blog"` |

The widget section has its own `border-t border-border` so it separates naturally from surrounding content. Do NOT add extra wrappers.

### API Route

```typescript
// frontend/app/api/email-capture/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { Resend } from 'resend';

const RESEND_API_KEY = process.env.RESEND_API_KEY;
const RESEND_AUDIENCE_ID = process.env.RESEND_AUDIENCE_ID;

export async function POST(req: NextRequest) {
  if (!RESEND_API_KEY || !RESEND_AUDIENCE_ID) {
    console.warn('[email-capture] Missing RESEND_API_KEY or RESEND_AUDIENCE_ID');
    return NextResponse.json({ error: 'Service unavailable' }, { status: 500 });
  }

  let email: string;
  let source: string;
  try {
    const body = await req.json();
    email = String(body.email ?? '').trim().toLowerCase();
    source = String(body.source ?? 'unknown').trim();
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }

  // Basic email format validation
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: 'Invalid email address' }, { status: 422 });
  }

  try {
    const resend = new Resend(RESEND_API_KEY);
    await resend.contacts.create({
      audienceId: RESEND_AUDIENCE_ID,
      email,
      unsubscribed: false,
      firstName: undefined,
      lastName: undefined,
    });
    return NextResponse.json({ subscribed: true });
  } catch (err: unknown) {
    // Resend throws on duplicate — treat as success (AC5)
    const status = (err as { statusCode?: number })?.statusCode ?? 0;
    if (status === 409 || status === 422) {
      return NextResponse.json({ subscribed: true });
    }
    console.error('[email-capture] Resend error:', err);
    return NextResponse.json({ error: 'Service error' }, { status: 500 });
  }
}
```

> **Note:** Resend's Node SDK does not currently expose a `properties` field on `contacts.create()` type. Pass `source` as a custom property only if the SDK type allows it — otherwise skip it; the Resend dashboard shows the `source` email metadata anyway.

### Files to Create

- `frontend/app/api/email-capture/route.ts`
- `frontend/components/marketing/EmailCaptureWidget.tsx`

### Files to Update

- `frontend/app/page.tsx` — import and place `<EmailCaptureWidget source="homepage" />`
- `frontend/app/(public)/pricing/page.tsx` — import and place widget
- `frontend/app/(public)/about/page.tsx` — import and place widget
- `frontend/app/(public)/blog/[slug]/page.tsx` — import and place widget
- `frontend/.env.local` — add `RESEND_API_KEY` and `RESEND_AUDIENCE_ID`
- `frontend/.env.local.example` — add both keys with placeholder comments

### Auto-adding Registrants to Audience (backend)

Registrants are a higher-quality signal than anonymous form submitters — add them automatically on email confirmation. Extract a shared helper so both the Next.js route and the FastAPI backend call the same logic:

**Backend helper** — add to `backend/app/integrations/email.py`:

```python
import resend as _resend

def add_contact_to_audience(email: str, source: str) -> None:
    """
    Adds a contact to the Resend audience. Fire-and-forget — caller must
    wrap in asyncio.to_thread and swallow exceptions.
    """
    audience_id = settings.RESEND_AUDIENCE_ID
    if not audience_id:
        logger.warning("[audience] RESEND_AUDIENCE_ID not set — skipping contact add")
        return
    _resend.Contacts.create({
        "audience_id": audience_id,
        "email": email,
        "unsubscribed": False,
        "properties": {"source": source},
    })
```

Add `RESEND_AUDIENCE_ID: str = ""` to `backend/app/core/config.py` `Settings` class.

**Hook into `verify_email_token`** (`auth_service.py`):
```python
# After user.verified = True and await db.commit():
try:
    await asyncio.to_thread(add_contact_to_audience, user.email, "signup")
except Exception:
    logger.warning("Failed to add verified user to Resend audience: %s", user.email)
```

**Hook into `auth_google`** (new user branch only, after `await db.commit()`):
```python
try:
    await asyncio.to_thread(add_contact_to_audience, email, "google_signup")
except Exception:
    logger.warning("Failed to add Google user to Resend audience: %s", email)
```

The Next.js API route (`/api/email-capture`) uses the same Resend audience but via the npm SDK — no change needed there.

### One-time Resend Dashboard Setup (manual, not code)

Boris must do this before the story can be tested end-to-end:
1. Go to Resend dashboard → Audiences → Create Audience (e.g., "PersonnaPress Pre-launch")
2. Copy the Audience ID → paste as `RESEND_AUDIENCE_ID` in `.env.local`
3. The `RESEND_API_KEY` is the same key already used by the FastAPI backend

## Tasks / Subtasks

- [x] Task 1: Verify or install `resend` npm package in `frontend/`
  - [x] Run `npm list resend` in `frontend/`; if missing, `npm install resend`

- [x] Task 2: Create the API route (AC: 6, 7)
  - [x] Create `frontend/app/api/email-capture/route.ts` per the spec above
  - [x] Add env var guard — return 500 without leaking key names (AC7)
  - [x] Server-side email regex validation before calling Resend (AC6)
  - [x] Treat `409`/`422` Resend responses as success (AC5)

- [x] Task 3: Build `EmailCaptureWidget` component (AC: 1, 2, 3, 4, 8, 9)
  - [x] Create `frontend/components/marketing/EmailCaptureWidget.tsx` per spec
  - [x] Paper Style: `rounded-none`, `shadow-brutal`, `border-border`, `font-display`
  - [x] Bottom-border-only input (no ring, no background)
  - [x] Inline success state with `CheckCircle` + `.animate-fade-in-up`
  - [x] Inline error state with `role="alert"` + `text-danger`
  - [x] Mobile-stacked / desktop-horizontal layout (AC8)
  - [x] Accessibility: `sr-only` label, `aria-invalid`, `aria-describedby`, `aria-disabled` (AC9)
  - [x] No Framer Motion — CSS animations only

- [x] Task 4: Place widget on all four public pages (AC: 1)
  - [x] `frontend/app/page.tsx` — above `<PublicFooter />`
  - [x] `frontend/app/(public)/pricing/page.tsx` — above `<PublicFooter />`
  - [x] `frontend/app/(public)/about/page.tsx` — above `<PublicFooter />`
  - [x] `frontend/app/(public)/blog/[slug]/page.tsx` — above `<PublicFooter />`

- [x] Task 5: Environment variables (AC: 10)
  - [x] Add `RESEND_API_KEY` and `RESEND_AUDIENCE_ID` to `frontend/.env.local`
  - [x] Add both keys with comments to `frontend/.env.local.example`
  - [x] Add `RESEND_AUDIENCE_ID` to `backend/app/core/config.py` `Settings` class (empty default)
  - [x] Add `RESEND_AUDIENCE_ID` to backend `.env` and `.env.example`

- [x] Task 6: Auto-add registrants to audience (AC: 11, 12)
  - [x] Add `add_contact_to_audience(email, source)` helper to `backend/app/integrations/email.py`
  - [x] Hook into `verify_email_token` in `auth_service.py` — fire-and-forget after commit (AC11)
  - [x] Hook into `auth_google` new-user branch in `auth_service.py` — fire-and-forget after commit (AC12)
  - [x] Both hooks: swallow exceptions with `logger.warning` — must not block login response

## Dev Agent Record

### Completion Notes

All 6 tasks completed. Key implementation decisions:

- `resend` npm package installed (v6.18.0); `resend` Python package re-confirmed installed.
- API route (`/api/email-capture`) guards env vars and validates email with regex before calling Resend. 4xx Resend errors (duplicate contacts) are treated as success per AC5.
- `EmailCaptureWidget` uses CSS-only animations (`.animate-fade-in-up`, `.animate-fade-in`) already defined in `globals.css`. No Framer Motion. Paper Style throughout.
- Public layout (`app/(public)/layout.tsx`) has `<PublicFooter />` at layout level; widget placed at bottom of each page's content (inside `<main>`) to appear above the footer visually.
- Blog slug page has its own `<main>` — widget placed before the bottom nav section.
- Backend: `add_contact_to_audience` silently skips if `RESEND_AUDIENCE_ID` is empty (safe for local dev without a Resend audience configured). Both `verify_email_token` and `auth_google` (new-user path only) call it fire-and-forget wrapped in `asyncio.to_thread`.
- `frontend/.env.local` created (was missing); includes the real API key from backend `.env`. `RESEND_AUDIENCE_ID` left empty — Boris must create an Audience in Resend dashboard and paste the ID.

### One-time manual setup required (not code)

Boris must do before end-to-end testing:
1. Resend dashboard → Audiences → Create Audience "PersonnaPress Pre-launch"
2. Copy Audience ID → set as `RESEND_AUDIENCE_ID` in `frontend/.env.local` and `backend/.env`

## File List

**Created:**
- `frontend/app/api/email-capture/route.ts`
- `frontend/components/marketing/EmailCaptureWidget.tsx`
- `frontend/.env.local`

**Modified:**
- `frontend/app/page.tsx`
- `frontend/app/(public)/pricing/page.tsx`
- `frontend/app/(public)/about/page.tsx`
- `frontend/app/(public)/blog/[slug]/page.tsx`
- `frontend/.env.local.example`
- `frontend/package.json`
- `frontend/package-lock.json`
- `backend/app/core/config.py`
- `backend/app/integrations/email.py`
- `backend/app/services/auth_service.py`
- `backend/.env`
- `backend/.env.example`

### Review Findings

- [x] [Review][Patch] Frontend treats all non-500 errors as success — 400/422 from own route show false "subscribed" state [frontend/components/marketing/EmailCaptureWidget.tsx:22]
- [x] [Review][Patch] `await asyncio.to_thread` blocks login response — not truly fire-and-forget [backend/app/services/auth_service.py:144]
- [x] [Review][Patch] No rate limiting on `/api/email-capture` — open to spam/quota abuse [frontend/app/api/email-capture/route.ts]
- [x] [Review][Patch] `source` field attacker-controlled with no allowlist or length cap [frontend/app/api/email-capture/route.ts:18]
- [x] [Review][Patch] `add_contact_to_audience` doesn't check `RESEND_API_KEY` before calling SDK [backend/app/integrations/email.py:17]
- [x] [Review][Patch] Resend 422 treated as duplicate success — only 409 is a duplicate [frontend/app/api/email-capture/route.ts:39]
- [x] [Review][Patch] `Resend` client instantiated on every request instead of module-level singleton [frontend/app/api/email-capture/route.ts:28]
- [x] [Review][Patch] Whitespace-only env vars pass truthiness check [frontend/app/api/email-capture/route.ts:4]
- [x] [Review][Patch] Request body not validated as non-null object (null/array body produces wrong result) [frontend/app/api/email-capture/route.ts:16]
- [x] [Review][Patch] Resend 429 falls through to generic 500 [frontend/app/api/email-capture/route.ts:37]
- [x] [Review][Defer] No GDPR/CAN-SPAM consent disclosure adjacent to widget — deferred, product/legal decision
- [x] [Review][Defer] Dual code paths for Resend (frontend route + backend helper) diverge over time — deferred, pre-existing architectural constraint
- [x] [Review][Defer] No unit/integration tests for email capture route or `add_contact_to_audience` — deferred, separate story

## Change Log

- 2026-07-26: Story 19.1 implemented — email capture widget on 4 public pages, `/api/email-capture` Next.js route via Resend npm SDK, auto-add verified/Google registrants to Resend audience via backend fire-and-forget hooks.
- 2026-07-26: Code review complete — 10 patches applied (frontend 4xx-as-success fix, fire-and-forget create_task, rate limiting, source allowlist, RESEND_API_KEY guard, 422→409-only duplicate, Resend singleton, whitespace trim, body type check, 429 passthrough); 3 deferred; 4 dismissed.
