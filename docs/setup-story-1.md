# Developer Setup Guide — Story 1 (Foundation & Auth)

This guide walks you through every external service needed to run and test Stories 1.1 through 1.5 locally. Follow each section in order — later sections depend on credentials produced by earlier ones.

**Prerequisites:** Node.js 20+, Python 3.12+, and `openssl` available in your terminal.

---

## Overview

| Story | What it tests | Services required |
|-------|--------------|-------------------|
| 1.1 | Monorepo scaffold, DB schema, design system | Supabase |
| 1.2 | User registration + email verification | Supabase, Google OAuth, Resend |
| 1.3 | Login, session management, logout | Supabase, Google OAuth |
| 1.4 | Protected app shell, responsive nav | Supabase (session cookie only) |
| 1.5 | Account page, Stripe billing portal, webhooks | Supabase, Stripe |

---

## 1. Supabase (Database)

PersonnaPress uses Supabase as a managed Postgres host. The backend connects via asyncpg.

### 1.1 Create a project

1. Go to [supabase.com](https://supabase.com) and sign in.
2. Click **New project**.
3. Set a project name (e.g. `personnapress-dev`), choose a region close to you, and set a database password. **Save this password** — you will need it for the connection string.
4. Wait for the project to finish provisioning (~2 minutes).

### 1.2 Get the connection string

1. In the Supabase dashboard, go to **Settings > Database**.
2. Under **Connection string**, select the **URI** tab.
3. Copy the string. It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
4. **Replace** `postgresql://` with `postgresql+asyncpg://` so SQLAlchemy uses the async driver:
   ```
   postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

This is your `DATABASE_URL` value.

### 1.3 Run the Alembic migrations

The initial migration creates all 7 tables (users, subscriptions, clients, platform_connections, campaigns, jobs, generation_logs). A second migration makes `stripe_sub_id` nullable for new registrations.

```bash
cd backend
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
# Windows — Git Bash
source .venv/Scripts/activate
# Windows — PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in `DATABASE_URL` (see Section 6 for the full `.env` template):

```bash
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL before running migrations
```

Run the migrations:

```bash
alembic upgrade head
```

Expected output ends with `Running upgrade ... -> 2a7f3c8d1e04, make stripe_sub_id nullable`. Verify in the Supabase Table Editor that the 7 tables are present.

---

## 2. Google OAuth

Google OAuth is used for "Sign up with Google" (Story 1.2) and "Sign in with Google" (Story 1.3). The exchange happens entirely server-side — the browser never sees `GOOGLE_CLIENT_SECRET`.

### 2.1 Create an OAuth 2.0 client

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in.
2. Create a new project (or select an existing one).
3. In the left nav, go to **APIs & Services > OAuth consent screen**.
   - User type: **External**
   - Fill in app name (`PersonnaPress Dev`), user support email, and developer contact email.
   - Scopes: add `email` and `profile` (under Google Account scopes). No other scopes are needed.
   - Save and continue through the remaining steps. Publishing status can stay **Testing** for local dev.
4. Go to **APIs & Services > Credentials**.
5. Click **Create Credentials > OAuth client ID**.
   - Application type: **Web application**
   - Name: `PersonnaPress Web`
   - Authorized JavaScript origins: `http://localhost:3000`
   - Authorized redirect URIs: `http://localhost:3000/api/auth/google/callback`
6. Click **Create**. Copy the **Client ID** and **Client Secret**.

> The redirect URI must exactly match what Next.js sends in the OAuth request. The backend at `frontend/app/api/auth/google/callback/route.ts` exchanges the `code` for a profile and then forwards verified fields to FastAPI — the secret never reaches the browser.

### 2.2 CSRF protection (state parameter)

The OAuth flow uses a `state` cookie to prevent CSRF. This is handled automatically by the Next.js route at `/api/auth/google/initiate` — no extra setup required. The flow is:

```
Browser -> /api/auth/google/initiate (sets state cookie, redirects to Google)
Google  -> /api/auth/google/callback?code=...&state=... (validates state, exchanges code)
Backend -> FastAPI POST /api/v1/auth/google (creates/finds user, issues JWT)
```

---

## 3. Stripe

Stripe is used in Story 1.5 for the billing portal and webhook processing. For Stories 1.1 through 1.4 you can leave Stripe keys as empty strings — the backend config accepts empty values and the billing portal is not reachable until Story 1.5.

### 3.1 Create a Stripe account and switch to Test mode

1. Go to [stripe.com](https://stripe.com) and create an account (or sign in).
2. In the Stripe Dashboard, ensure the toggle at the top shows **Test mode**. All keys and IDs below are test-mode values.

### 3.2 Get API keys

1. Go to **Developers > API keys**.
2. Copy the **Publishable key** (`pk_test_...`) — this goes in `frontend/.env` as `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`.
3. Copy the **Secret key** (`sk_test_...`) — this goes in `backend/.env` as `STRIPE_SECRET_KEY`.

Never commit these values. The secret key must never appear in frontend code or `NEXT_PUBLIC_` variables.

### 3.3 Create products and prices

PersonnaPress has three plan tiers. Create them in Stripe so the webhook handler can map price IDs to internal tier names.

1. Go to **Products > Add product**.
2. Create three products:

   | Product name | Price | Billing | Lookup key (important) |
   |---|---|---|---|
   | Starter | $29 | Monthly | `price_starter_monthly` |
   | Growth | $79 | Monthly | `price_growth_monthly` |
   | Agency | $199 | Monthly | `price_agency_monthly` |

   To set a lookup key: after creating a price, click it and set the **Lookup key** field. The backend maps these keys to internal tier names via `STRIPE_PRICE_TO_TIER` in `app/core/constants.py`.

3. After creating each price, copy the **Price ID** (`price_...`). These go in `backend/.env` as:
   ```
   STRIPE_PRICE_STARTER=price_...
   STRIPE_PRICE_GROWTH=price_...
   STRIPE_PRICE_AGENCY=price_...
   ```

### 3.4 Configure Stripe webhooks

The webhook flow: Stripe fires an event to the Next.js relay route at `/api/webhooks/stripe`, which validates the signature and forwards the raw body to FastAPI at `POST /api/v1/webhooks/stripe`.

**For local development**, use the Stripe CLI to tunnel events to localhost:

1. Install the [Stripe CLI](https://stripe.com/docs/stripe-cli):
   ```bash
   # macOS
   brew install stripe/stripe-cli/stripe
   # Windows (scoop)
   scoop install stripe
   ```

2. Log in:
   ```bash
   stripe login
   ```

3. Start the webhook forwarder (run this in a separate terminal while testing):
   ```bash
   stripe listen --forward-to localhost:3000/api/webhooks/stripe
   ```

4. The CLI prints a **webhook signing secret** (`whsec_...`). Copy it into both:
   - `backend/.env` as `STRIPE_WEBHOOK_SECRET`
   - `frontend/.env` as `STRIPE_WEBHOOK_SECRET`

   > The Next.js relay route validates the signature first (`frontend/app/api/webhooks/stripe/route.ts`), then forwards to FastAPI. Both sides must share the same `STRIPE_WEBHOOK_SECRET`.

**For production**, add a webhook endpoint in the Stripe Dashboard under **Developers > Webhooks**:
- Endpoint URL: `https://your-app.vercel.app/api/webhooks/stripe`
- Events to listen for: `customer.subscription.updated`, `customer.subscription.deleted`

### 3.5 Enable the Customer Portal

The billing portal (Story 1.5 "Manage subscription" button) requires the Stripe Customer Portal to be configured.

1. In the Stripe Dashboard, go to **Settings > Billing > Customer portal**.
2. Click **Activate portal link** (or configure it if you want to customize it).
3. Under **Business information**, add your return URL: `http://localhost:3000/account`.

---

## 4. Resend (Email)

Resend sends the email verification link (Story 1.2). Without a valid `RESEND_API_KEY`, registration completes but the verification email is silently logged instead of delivered.

### 4.1 Create a Resend account

1. Go to [resend.com](https://resend.com) and sign up.
2. Go to **API Keys > Create API key**. Give it a name like `PersonnaPress Dev`.
3. Copy the key (`re_...`). This is your `RESEND_API_KEY`.

### 4.2 Sender domain (optional for testing)

For local development, Resend allows sending from `onboarding@resend.dev` without domain verification. The `send_verification_email` function in `backend/app/integrations/email.py` currently uses a `from` address — if you have not configured a custom domain, update it to `onboarding@resend.dev` for local testing.

---

## 5. Optional Services

These are not required to test Stories 1.1 through 1.5 but are needed for Stories 2 and beyond.

| Service | Env var | When needed |
|---------|---------|-------------|
| Sentry | `SENTRY_DSN` | Error observability (Epic 1 infra, optional) |
| Gemini | `GEMINI_API_KEY` | Content generation (Epic 3) |
| Replicate | `REPLICATE_API_TOKEN` | Image generation (Epic 3) |

Leave these as empty strings in `.env` — the backend config allows empty values.

---

## 6. Environment Files

### 6.1 Backend — `backend/.env`

```bash
# Supabase Postgres (asyncpg driver)
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# JWT — generate with: openssl rand -hex 32
# Must match JWT_SECRET in frontend/.env exactly
JWT_SECRET=<output of: openssl rand -hex 32>

# AES-256-GCM key for encrypting platform credentials — must be exactly 32 characters
CREDENTIAL_ENCRYPTION_KEY=<exactly-32-chars-string-here!!>

# Google OAuth (server-side only)
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_GROWTH=price_...
STRIPE_PRICE_AGENCY=price_...

# AI — leave empty for Story 1 testing
GEMINI_API_KEY=
REPLICATE_API_TOKEN=

# Observability — leave empty for Story 1 testing
SENTRY_DSN=

# Email
RESEND_API_KEY=re_...

# Frontend origin for CORS — no trailing slash
APP_URL=http://localhost:3000

# Internal backend URL (used by backend services calling themselves)
INTERNAL_API_URL=http://localhost:8000
```

Generate `JWT_SECRET` and `CREDENTIAL_ENCRYPTION_KEY`:

```bash
# JWT_SECRET
openssl rand -hex 32

# CREDENTIAL_ENCRYPTION_KEY — must be exactly 32 printable characters
openssl rand -base64 24 | head -c 32
```

### 6.2 Frontend — `frontend/.env`

```bash
# Backend base URL — no trailing slash
NEXT_PUBLIC_API_URL=http://localhost:8000

# Server-side backend URL (used by Next.js Route Handlers)
BACKEND_URL=http://localhost:8000

# App public URL
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Stripe publishable key (safe to expose in client code)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# Stripe webhook secret (server-side only, no NEXT_PUBLIC_ prefix)
STRIPE_WEBHOOK_SECRET=whsec_...

# JWT secret — must match backend JWT_SECRET exactly
# NEVER prefix with NEXT_PUBLIC_
JWT_SECRET=<same value as backend JWT_SECRET>

# Google OAuth
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>
```

> `JWT_SECRET` must be identical in both `.env` files. The backend signs tokens; the Next.js proxy (`frontend/proxy.ts`) verifies them using the same secret.

---

## 7. Running the Stack

Open three terminals.

**Terminal 1 — FastAPI backend:**

```bash
cd backend
source .venv/bin/activate         # Linux/macOS
# source .venv/Scripts/activate   # Windows Git Bash
# .venv\Scripts\Activate.ps1      # Windows PowerShell
uvicorn app.main:app --reload --port 8000
```

Confirm the API is up:

```bash
curl http://localhost:8000/api/v1/health
# Expected: {"status":"ok"}
```

**Terminal 2 — Next.js frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

**Terminal 3 — Stripe CLI (Story 1.5 only):**

```bash
stripe listen --forward-to localhost:3000/api/webhooks/stripe
```

---

## 8. Testing Checklist — Story by Story

### Story 1.1 — Scaffold & DB Schema

- [ ] `GET http://localhost:8000/api/v1/health` returns `{"status":"ok"}`
- [ ] Supabase Table Editor shows all 7 tables: `users`, `subscriptions`, `clients`, `platform_connections`, `campaigns`, `jobs`, `generation_logs`
- [ ] `cd frontend && npm run build` exits with 0 errors

### Story 1.2 — User Registration

- [ ] Navigate to `http://localhost:3000/register`
- [ ] Submit the form with a valid email and password (8+ chars)
- [ ] Page shows "Check your email to verify your account." (no redirect, inline message)
- [ ] Resend dashboard (or terminal log) shows a verification email was sent
- [ ] `users` table in Supabase shows a new row with `verified=false`
- [ ] `subscriptions` table shows a corresponding row with `plan_tier='growth'`, `status='trialing'`, `stripe_sub_id=null`
- [ ] Click the verification link in the email; page redirects to `/onboarding`
- [ ] `users.verified` is now `true`
- [ ] Attempting to register with the same email shows "An account with this email already exists."
- [ ] Click "Sign up with Google" — completes OAuth and redirects to `/onboarding`

### Story 1.3 — Login & Session

- [ ] Navigate to `http://localhost:3000/login`
- [ ] Log in with the email/password registered above
- [ ] Redirects to `/dashboard`; browser DevTools > Application > Cookies shows `session` cookie (`HttpOnly`, `SameSite=Lax`)
- [ ] Close and reopen the browser tab — navigating to `/dashboard` does not require re-login
- [ ] Wrong credentials show "Invalid email or password." (generic — no field discrimination)
- [ ] Visiting `/login` while already authenticated redirects to `/dashboard`
- [ ] Click "Log out" — redirects to `/login`; `session` cookie is cleared

### Story 1.4 — Protected App Shell

- [ ] While logged in, all `(app)/` routes show the sidebar (240px on desktop, 56px icon-only on tablet, hamburger on mobile)
- [ ] Navigating to `/dashboard` while unauthenticated redirects to `/login`
- [ ] Navigating to `/dashboard` while authenticated but unverified redirects to `/verify-email`
- [ ] Active nav item has Highlighter background (#FFF1B8) and `aria-current="page"`
- [ ] Mobile (< 768px): hamburger opens slide-in drawer; Esc closes it

### Story 1.5 — Account & Subscription

- [ ] Navigate to `http://localhost:3000/account`
- [ ] Page shows plan tier, usage counters, and renewal date formatted as "Renews Month DD, YYYY"
- [ ] No progress bars or gamification — plain text only
- [ ] "Manage subscription" button → redirects to Stripe Customer Portal (only works if `stripe_customer_id` is populated)
- [ ] With Stripe CLI running: `stripe trigger customer.subscription.updated` — check terminal confirms the event was forwarded and `subscriptions` table is updated
- [ ] "Log out" on account page clears cookie and redirects to `/login`

---

## 9. Common Issues

**`alembic upgrade head` fails with connection error**
Verify `DATABASE_URL` in `backend/.env` uses `postgresql+asyncpg://` not `postgresql://`. Supabase requires SSL by default — if you see SSL errors, append `?ssl=require` to the connection string.

**`CREDENTIAL_ENCRYPTION_KEY` errors at startup**
This key must be exactly 32 characters. Verify: `echo -n "your-key-here" | wc -c`. Pad or trim as needed.

**Google OAuth redirect_uri_mismatch**
The redirect URI registered in Google Cloud Console must exactly match the one the app sends: `http://localhost:3000/api/auth/google/callback`. No trailing slash. Check spelling.

**Stripe webhook signature verification fails**
The `STRIPE_WEBHOOK_SECRET` used by the frontend relay route must be the one printed by `stripe listen`, not a webhook secret from the Stripe Dashboard. Dashboard secrets and CLI secrets are different.

**Emails not arriving**
Check the Resend dashboard for delivery logs. For local testing you can replace the `from` address in `backend/app/integrations/email.py` with `onboarding@resend.dev`.

**`JWT_SECRET` mismatch — 401 on all app routes**
Both `backend/.env` and `frontend/.env` must have the same `JWT_SECRET`. The backend signs the token; `frontend/proxy.ts` verifies it. If they differ, every authenticated request fails.
