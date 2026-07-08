---
baseline_commit: 15d27d402fdd327af79c965e2e01b9cd90dedc3a
---

# Story 9.1: Production Launch & Infrastructure Setup

Status: done

## Story

As the engineering team,
We want to deploy PersonnaPress to production on Vercel + DigitalOcean, configure live Stripe billing, and fix all hardcoded domain/email references,
So that real users can register, pay, and use the product on `personnapress.com`.

## Acceptance Criteria

1. **Given** any transactional email is sent by the backend, **When** the email is delivered, **Then** the `from` header reads the value of the `EMAIL_FROM` environment variable (default: `PersonnaPress <noreply@personnapress.com>`) — the address is never hardcoded in source code.

2. **Given** the frontend is deployed to production, **When** search engine crawlers or social crawlers read `sitemap.xml`, `robots.txt`, or Open Graph metadata, **Then** all URLs reference `https://personnapress.com` (not `personapress.io`) and the brand name reads **"PersonnaPress"** (double-n) in all page titles, OG tags, and Twitter card metadata.

3. **Given** `next.config.ts` remote image patterns, **When** the Next.js build compiles, **Then** the image remote pattern for the old domain `*.personapress.io` is replaced with `*.personnapress.com`; all other remote patterns (Supabase, Replicate) are unchanged.

4. **Given** the `metadataBase` in `frontend/app/layout.tsx`, **When** Next.js resolves absolute metadata URLs, **Then** `metadataBase` reads from the `NEXT_PUBLIC_APP_URL` environment variable so no URL is hardcoded; OG and Twitter card image URLs use relative paths (`/images/PersonnaPress-opengraph.png`) resolved against `metadataBase`.

5. **Given** the files `backend/deploy/personnapress-api.service` and `backend/deploy/nginx.conf` exist in the repo, **When** an operator follows the Droplet provisioning runbook in Dev Notes, **Then** running the documented commands produces a working HTTPS-secured FastAPI service accessible at `https://api.personnapress.com`.

6. **Given** `vercel.json` exists at the repository root, **When** a Vercel deployment is triggered from the `main` branch, **Then** Vercel builds and deploys only the `frontend/` subdirectory as a Next.js application.

7. **Given** all environment variables listed in the Dev Notes are set on the Vercel project and the DO Droplet, **When** the deployed application is exercised end-to-end, **Then** login, OAuth, campaign generation, and Stripe billing portal all function correctly with no localhost or test-mode references active.

8. **Given** the Stripe live-mode setup is complete, **When** a trialing user clicks "Subscribe" and completes checkout in the Stripe Customer Portal, **Then** a `customer.subscription.updated` webhook fires, the backend webhook handler updates `subscriptions.plan_tier` and `subscriptions.status`, and the user gains access at the correct plan tier.

9. **Given** the Sentry DSN in backend `.env` is set to a real Sentry project DSN, **When** a backend exception is raised in production, **Then** the event appears in the Sentry project dashboard; the placeholder `examplePublicKey` DSN is not present on the production Droplet.

10. **Given** `backend/.env.example` is read by any developer, **When** they see the `CREDENTIAL_ENCRYPTION_KEY` entry, **Then** there is exactly one entry for that variable with a clear generation command comment; the duplicate second entry that was present in the local `.env` is absent from the example and must never be present on the production Droplet.

---

## Tasks / Subtasks

### Group A — Code changes (dev agent implements)

- [x] Task A1: Make email `from` address configurable (AC: #1)
  - [x] A1.1 Add `EMAIL_FROM: str = "PersonnaPress <noreply@personnapress.com>"` to `backend/app/core/config.py` `Settings` class
  - [x] A1.2 Update `backend/app/integrations/email.py`: replace the two hardcoded `"from": "PersonnaPress <noreply@personnapress.io>"` strings with `"from": settings.EMAIL_FROM`
  - [x] A1.3 Add `EMAIL_FROM=PersonnaPress <noreply@personnapress.com>` to `backend/.env.example` with a comment explaining the format must be `Name <address@domain.com>`

- [x] Task A2: Fix frontend domain references (AC: #2, #3, #4)
  - [x] A2.1 `frontend/app/sitemap.ts`: replace `"https://personapress.io"` with `` `${process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com"}` ``
  - [x] A2.2 `frontend/app/robots.ts`: replace `"https://personapress.io/sitemap.xml"` with `` `${process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com"}/sitemap.xml` ``
  - [x] A2.3 `frontend/app/layout.tsx`:
    - Change `metadataBase: new URL("https://personapress.io")` → `metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com")`
    - Change `title.default: "PersonaPress - ..."` → `"PersonnaPress - Publish in Your Voice, Not AI's"`
    - Change `title.template: "%s | PersonaPress"` → `"%s | PersonnaPress"`
    - Change `openGraph.title: "PersonaPress - ..."` → `"PersonnaPress - Publish in Your Voice, Not AI's"`
    - Change `openGraph.siteName: "PersonaPress"` → `"PersonnaPress"`
    - Change `openGraph.images[0].url` from the absolute `https://personapress.io/...` URL to the relative path `"/images/PersonnaPress-opengraph.png"` (metadataBase will resolve it)
    - Change `openGraph.images[0].alt` from `"PersonaPress - ..."` → `"PersonnaPress - AI content engine that publishes in your voice"`
    - Change `twitter.title: "PersonaPress - ..."` → `"PersonnaPress - Publish in Your Voice, Not AI's"`
    - Change `twitter.images` from the absolute `https://personapress.io/...` URL to `["/images/PersonnaPress-opengraph.png"]`
  - [x] A2.4 `frontend/next.config.ts`: replace `hostname: "*.personapress.io"` with `hostname: "*.personnapress.com"`

- [x] Task A3: Update env examples to document all production variables (AC: #10)
  - [x] A3.1 `backend/.env.example`: ensure `CREDENTIAL_ENCRYPTION_KEY` appears exactly once with this comment above it:
    ```
    # AES-256-GCM key for encrypting platform credentials (must be exactly 32 chars)
    # Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(24))"
    CREDENTIAL_ENCRYPTION_KEY=your-32-char-encryption-key-here!
    ```
    Remove any second occurrence of `CREDENTIAL_ENCRYPTION_KEY`.
  - [x] A3.2 `backend/.env.example`: add `EMAIL_FROM=PersonnaPress <noreply@personnapress.com>` after `RESEND_API_KEY`
  - [x] A3.3 `backend/.env.example`: update `APP_URL=https://personnapress.com` (change from localhost placeholder)
  - [x] A3.4 `backend/.env.example`: add `SENTRY_DSN=` (empty by default; comment: "Get from sentry.io — required for production error tracking")
  - [x] A3.5 `frontend/.env.example` (the committed example): add `NEXT_PUBLIC_APP_URL=https://personnapress.com` with comment: "Public app URL — must match APP_URL in backend .env"
  - [x] A3.6 `frontend/.env.local.example`: sync same additions from A3.5

- [x] Task A4: Create Vercel configuration (AC: #6)
  - [x] A4.1 Create `vercel.json` at the repository root:
    ```json
    {
      "framework": "nextjs",
      "rootDirectory": "frontend",
      "buildCommand": "npm run build",
      "outputDirectory": ".next",
      "installCommand": "npm ci"
    }
    ```

- [x] Task A5: Create Droplet deployment artifacts (AC: #5)
  - [x] A5.1 Create `backend/deploy/personnapress-api.service` — systemd unit file (see Dev Notes for exact content)
  - [x] A5.2 Create `backend/deploy/nginx.conf` — Nginx server block template (see Dev Notes for exact content)
  - [x] A5.3 Verify `deploy.sh` at repo root is correct (it already exists — read it and confirm the remote path `/var/www/personnapress` matches the provisioning runbook)

### Group B — Manual operator steps (Boris completes after code changes are deployed)

- [ ] Task B1: Fix local `backend/.env` (pre-flight, before any other step)
  - [ ] B1.1 Open `backend/.env` locally and remove the second `CREDENTIAL_ENCRYPTION_KEY=bugrn2MrPTe4LZHxAen7EPcqDy8Bu+1Z` line (line 38) — keep only the first entry. This fixes a pydantic-settings override bug where the shorter key silently replaced the hex key.
  - [ ] B1.2 Verify there is now exactly one `CREDENTIAL_ENCRYPTION_KEY` line.

- [ ] Task B2: Stripe live mode setup
  - [ ] B2.1 In Stripe Dashboard, switch to **Live mode** (toggle in top-left)
  - [ ] B2.2 Create 3 Products: "Starter", "Growth", "Agency" — set as recurring monthly subscriptions with prices matching the landing page
  - [ ] B2.3 Copy the 3 live `price_XXXX` IDs — these go into `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_GROWTH`, `STRIPE_PRICE_AGENCY` in the production `.env`
  - [ ] B2.4 Copy the live `sk_live_...` secret key and `pk_live_...` publishable key
  - [ ] B2.5 Go to **Developers → Webhooks → Add endpoint**: URL = `https://personnapress.com/api/webhooks/stripe`, events = `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
  - [ ] B2.6 Copy the webhook signing secret (`whsec_...`) — this is `STRIPE_WEBHOOK_SECRET` in production
  - [ ] B2.7 Go to **Settings → Billing → Customer portal**: enable "Allow customers to switch plans", enable "Allow customers to cancel subscriptions", and if you want trialing users to be able to subscribe directly through the portal, enable "Allow customers to subscribe to products" and add all 3 products

- [ ] Task B3: Provision DigitalOcean Droplet (see full runbook in Dev Notes)
  - [ ] B3.1 Create $6/mo Droplet: Ubuntu 24.04 LTS, 1 vCPU / 1 GB RAM, NYC1 or SFO3
  - [ ] B3.2 Add SSH key, note the Droplet IPv4 address
  - [ ] B3.3 Run the provisioning commands from Dev Notes to install Python 3.12, Nginx, Git, Certbot
  - [ ] B3.4 Clone repo to `/var/www/personnapress`
  - [ ] B3.5 Create `/var/www/personnapress/backend/.env` with all production values (see env checklist in Dev Notes)
  - [ ] B3.6 Create Python venv, install requirements
  - [ ] B3.7 Run `alembic upgrade head` to initialize schema
  - [ ] B3.8 Copy `backend/deploy/personnapress-api.service` to `/etc/systemd/system/` and enable it
  - [ ] B3.9 Copy `backend/deploy/nginx.conf` to `/etc/nginx/sites-available/personnapress` and enable it
  - [ ] B3.10 Run Certbot: `sudo certbot --nginx -d api.personnapress.com`
  - [ ] B3.11 Confirm `https://api.personnapress.com/api/v1/health` returns `{"status": "ok"}`

- [ ] Task B4: Configure Vercel project
  - [ ] B4.1 Go to vercel.com → Add New Project → import this GitHub repo
  - [ ] B4.2 Set **Root Directory** to `frontend` (or rely on `vercel.json` — confirm which takes precedence in Vercel UI)
  - [ ] B4.3 Add all frontend environment variables listed in Dev Notes env checklist
  - [ ] B4.4 Confirm build succeeds and `https://personnapress.com` (or the Vercel preview URL) loads the landing page
  - [ ] B4.5 Add custom domain `personnapress.com` in Vercel → Domains; follow Vercel's DNS instructions

- [ ] Task B5: DNS configuration
  - [ ] B5.1 In your DNS provider (wherever `personnapress.com` is registered): add the DNS records Vercel provides for the root domain and `www` subdomain
  - [ ] B5.2 Add an `A` record: `api.personnapress.com` → Droplet IPv4 address
  - [ ] B5.3 After DNS propagates, re-run Certbot if needed and verify `https://api.personnapress.com/api/v1/health`

- [ ] Task B6: Update OAuth redirect URIs across all platforms
  - [ ] B6.1 **Twitter/X Developer Portal**: App → Auth settings → Callback URIs → add `https://personnapress.com/api/auth/x/callback`; also update `X_REDIRECT_URI` in backend production `.env` and `NEXT_PUBLIC_API_URL` is not needed for this but `X_REDIRECT_URI` must be exact
  - [ ] B6.2 **LinkedIn Developer Portal**: App → Auth → Authorized redirect URLs → add `https://personnapress.com/api/auth/linkedin/callback`; update `LINKEDIN_REDIRECT_URI` in production `.env`
  - [ ] B6.3 **WordPress.com App** (apps.wordpress.com): update the Redirect URL to `https://personnapress.com/api/auth/wordpress-com/callback`; update `WP_COM_REDIRECT_URI` in production `.env`
  - [ ] B6.4 **Google Cloud Console**: OAuth 2.0 Credentials → your client → Authorized redirect URIs → add `https://personnapress.com/api/auth/google/callback` and update `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` if using different credentials for production
  - [ ] B6.5 Update `APP_URL` in backend production `.env` to `https://personnapress.com`

- [ ] Task B7: Sentry setup
  - [ ] B7.1 Create a new Sentry project at sentry.io (or use existing organization): select Python platform for the backend
  - [ ] B7.2 Copy the DSN and set `SENTRY_DSN=https://...@sentry.io/PROJECTID` in production backend `.env`
  - [ ] B7.3 Optionally create a separate Sentry project for the Next.js frontend (add `SENTRY_DSN` to Vercel env vars and install `@sentry/nextjs` — this is a future story unless you want it now)

- [ ] Task B8: Resend email domain verification
  - [ ] B8.1 In Resend Dashboard → Domains → Add Domain: enter `personnapress.com`
  - [ ] B8.2 Add the provided DKIM and SPF DNS records to your DNS provider
  - [ ] B8.3 Verify the domain in Resend UI (green checkmark)
  - [ ] B8.4 Update `EMAIL_FROM=PersonnaPress <noreply@personnapress.com>` in production backend `.env`
  - [ ] B8.5 Send a test verification email through the app to confirm delivery

---

## Dev Notes

### Encryption key: understanding the duplicate bug

`backend/app/core/security.py` `_get_key()` encodes the key string and takes the first 32 bytes:
```python
key = settings.CREDENTIAL_ENCRYPTION_KEY.encode()
return key[:32].ljust(32, b"\x00")
```

The local `backend/.env` currently has TWO entries for `CREDENTIAL_ENCRYPTION_KEY` with different values. Pydantic-settings reads the last occurrence, so the 32-char string `bugrn2MrPTe4LZHxAen7EPcqDy8Bu+1Z` has been in use locally. Since there are no production users yet, there is no encrypted credential migration problem — use a freshly generated key in production:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```
This outputs a 32-char URL-safe string (24 random bytes base64-encoded = 32 chars). Use that as `CREDENTIAL_ENCRYPTION_KEY`.

### Files changed by dev agent (A tasks)

| File | Change |
|---|---|
| `backend/app/core/config.py` | Add `EMAIL_FROM` setting |
| `backend/app/integrations/email.py` | Use `settings.EMAIL_FROM` |
| `backend/.env.example` | Add `EMAIL_FROM`, fix `CREDENTIAL_ENCRYPTION_KEY` (one entry), update `APP_URL` |
| `frontend/app/sitemap.ts` | Use `NEXT_PUBLIC_APP_URL` env var |
| `frontend/app/robots.ts` | Use `NEXT_PUBLIC_APP_URL` env var |
| `frontend/app/layout.tsx` | Fix metadataBase, fix brand name (double-n), relative OG image URLs |
| `frontend/next.config.ts` | Update image remote pattern to `*.personnapress.com` |
| `frontend/.env.example` | Add `NEXT_PUBLIC_APP_URL` |
| `frontend/.env.local.example` | Add `NEXT_PUBLIC_APP_URL` |
| `vercel.json` | New file at repo root |
| `backend/deploy/personnapress-api.service` | New file |
| `backend/deploy/nginx.conf` | New file |

### Systemd service file: `backend/deploy/personnapress-api.service`

```ini
[Unit]
Description=PersonnaPress FastAPI API
After=network.target
Wants=network-online.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/personnapress/backend
EnvironmentFile=/var/www/personnapress/backend/.env
ExecStart=/var/www/personnapress/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=personnapress-api

[Install]
WantedBy=multi-user.target
```

### Nginx config: `backend/deploy/nginx.conf`

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    server_name api.personnapress.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS proxy to uvicorn
server {
    listen 443 ssl;
    server_name api.personnapress.com;

    ssl_certificate     /etc/letsencrypt/live/api.personnapress.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.personnapress.com/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

### Droplet provisioning runbook (Boris runs these commands)

```bash
# 1. SSH into the new Droplet as root
ssh root@<DROPLET_IP>

# 2. Update system and install dependencies
apt-get update && apt-get upgrade -y
apt-get install -y python3.12 python3.12-venv python3-pip git nginx certbot python3-certbot-nginx

# 3. Create app directory and www-data ownership
mkdir -p /var/www/personnapress
chown www-data:www-data /var/www/personnapress

# 4. Clone the repo (as root, then fix ownership)
git clone https://github.com/<your-org>/PersonnaPress.git /var/www/personnapress
chown -R www-data:www-data /var/www/personnapress

# 5. Create Python venv at repo root level
python3.12 -m venv /var/www/personnapress/.venv
/var/www/personnapress/.venv/bin/pip install --upgrade pip
/var/www/personnapress/.venv/bin/pip install -r /var/www/personnapress/backend/requirements.txt

# 6. Create production .env (fill in all values from checklist below)
nano /var/www/personnapress/backend/.env

# 7. Run Alembic migrations
cd /var/www/personnapress/backend
/var/www/personnapress/.venv/bin/alembic upgrade head

# 8. Install and enable systemd service
cp /var/www/personnapress/backend/deploy/personnapress-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable personnapress-api
systemctl start personnapress-api
systemctl status personnapress-api   # confirm "active (running)"

# 9. Configure Nginx (DNS must point api.personnapress.com to this IP first)
cp /var/www/personnapress/backend/deploy/nginx.conf /etc/nginx/sites-available/personnapress
ln -s /etc/nginx/sites-available/personnapress /etc/nginx/sites-enabled/personnapress
rm -f /etc/nginx/sites-enabled/default
nginx -t                             # confirm "syntax is ok"
systemctl reload nginx

# 10. Obtain TLS certificate
certbot --nginx -d api.personnapress.com

# 11. Smoke test
curl https://api.personnapress.com/api/v1/health
# Expected: {"status":"ok"}
```

### Using deploy.sh for subsequent deployments

The `deploy.sh` script at the repo root already handles all post-commit deployments:

```bash
# Set once in your shell or .zshrc/.bashrc:
export DROPLET_IP=<your-droplet-ip>
export SSH_USER=root        # or another user if you created one

# Run after each merge to main:
./deploy.sh
```

The script: SSHs into the Droplet → `git pull origin main` → `pip install -r requirements.txt` → `alembic upgrade head` → `systemctl restart personnapress-api`. It will fail fast if any step errors (`set -euo pipefail`).

### Production environment variable checklist

#### Backend Droplet `.env` (at `/var/www/personnapress/backend/.env`)

```bash
# Database (Supabase — same project as dev, or create a separate prod project)
DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-1-us-west-2.pooler.supabase.com:5432/postgres

# Secrets — generate fresh for production
JWT_SECRET=<openssl rand -hex 32>
CREDENTIAL_ENCRYPTION_KEY=<python3 -c "import secrets; print(secrets.token_urlsafe(24))">

# Google OAuth
GOOGLE_CLIENT_ID=229637131132-v86i6grtpllqgr2gqas1c3advori518g.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>

# Twitter/X OAuth
X_CLIENT_ID=dW56bXF0YnhBTExiUUZRYUZYMGw6MTpjaQ
X_CLIENT_SECRET=<from Twitter Dev Portal>
X_REDIRECT_URI=https://personnapress.com/api/auth/x/callback

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=86ayg7642eu9pw
LINKEDIN_CLIENT_SECRET=<from LinkedIn Developer Portal>
LINKEDIN_REDIRECT_URI=https://personnapress.com/api/auth/linkedin/callback

# WordPress.com OAuth
WP_COM_CLIENT_ID=143164
WP_COM_CLIENT_SECRET=<from WordPress.com App>
WP_COM_REDIRECT_URI=https://personnapress.com/api/auth/wordpress-com/callback

# Stripe — LIVE mode keys
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_live_...
STRIPE_PRICE_GROWTH=price_live_...
STRIPE_PRICE_AGENCY=price_live_...

# AI services
GEMINI_API_KEY=<same as dev or new key>
REPLICATE_API_TOKEN=<same as dev or new key>

# Observability
SENTRY_DSN=https://<key>@sentry.io/<project-id>

# Email
RESEND_API_KEY=re_...
EMAIL_FROM=PersonnaPress <noreply@personnapress.com>

# App URL (must match Vercel deployment URL)
APP_URL=https://personnapress.com

# Supabase Storage
SUPABASE_URL=https://btulxmvzxhlqfrnwoxtm.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<from Supabase Dashboard → Settings → API>

# Trial period
TRIAL_DAYS=14
```

#### Vercel environment variables (set in Vercel Dashboard → Project → Settings → Environment Variables)

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.personnapress.com` |
| `NEXT_PUBLIC_APP_URL` | `https://personnapress.com` |
| `APP_URL` | `https://personnapress.com` |
| `BACKEND_URL` | `https://api.personnapress.com` |
| `INTERNAL_API_URL` | `https://api.personnapress.com` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_live_...` |
| `STRIPE_SECRET_KEY` | `sk_live_...` (for webhook route) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` (live) |
| `JWT_SECRET` | same as backend |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | same as backend |
| `GOOGLE_CLIENT_ID` | same as backend |
| `GOOGLE_CLIENT_SECRET` | same as backend |
| `NEXT_PUBLIC_X_CLIENT_ID` | `dW56bXF0YnhBTExiUUZRYUZYMGw6MTpjaQ` |
| `X_CLIENT_SECRET` | same as backend |
| `NEXT_PUBLIC_LINKEDIN_CLIENT_ID` | `86ayg7642eu9pw` |
| `LINKEDIN_CLIENT_SECRET` | same as backend |
| `WP_COM_CLIENT_ID` | `143164` |

### Stripe Customer Portal — critical configuration

The app's subscription upgrade flow for trialing users goes entirely through the Stripe Customer Portal (not Stripe Checkout). Without configuring the portal, trialing users clicking "Subscribe" will see an empty portal with no way to add a payment method or subscribe.

In Stripe Dashboard → Settings → Billing → Customer portal:
1. **Products and prices**: Add all 3 live products (Starter, Growth, Agency) — this allows portal to offer plan switches
2. **Cancel subscriptions**: Enable (users need this per FR-3)
3. **Pause subscriptions**: Up to you
4. **Business information**: Set your support email and privacy policy URL (`https://personnapress.com/privacy`)

If you want trial users to start a subscription directly through the portal (before they have an existing subscription), you must also enable "Allow customers to subscribe to products" in the portal settings — otherwise trialing users (who have no active subscription object) will see an empty portal.

### Stripe webhook event to subscription flow

When a user subscribes via portal, the webhook flow is:
1. Stripe fires `customer.subscription.created` (or `customer.subscription.updated`)
2. Next.js `/api/webhooks/stripe` validates the signature and forwards raw body to `https://api.personnapress.com/api/v1/webhooks/stripe`
3. FastAPI `handle_stripe_webhook` maps the Stripe price ID → plan tier via `get_stripe_price_to_tier()` (using the 3 live price env vars) and updates the `subscriptions` table

The `INTERNAL_API_URL` env var on Vercel must point to `https://api.personnapress.com` so the forwarding works from Vercel's serverless functions.

### Notes on `layout.tsx` brand name fix

The public-facing brand name is **PersonnaPress** (double-n). The old value "PersonaPress" (single-n) was a typo introduced during the landing page story and should be corrected in all page titles and OG metadata. The product name in all user-facing UI (buttons, headings, toasts) should already use the correct spelling — only `layout.tsx` metadata strings need fixing.

### Architecture pattern: `proxy.ts` is the Next.js middleware

The auth middleware lives at `frontend/proxy.ts` (not the conventional `middleware.ts`). This is intentional and working — the compiled output is confirmed in `.next/server/middleware.js`. Do not rename or move this file.

### References

- `backend/app/core/config.py` — `Settings` class, all env vars
- `backend/app/integrations/email.py` — hardcoded from address
- `backend/app/core/security.py` — `_get_key()` showing how CREDENTIAL_ENCRYPTION_KEY is consumed
- `backend/app/services/subscription_service.py:264` — `create_billing_portal_session`; creates Stripe customer on first portal access for trialing users
- `backend/app/core/constants.py` — `get_stripe_price_to_tier()` mapping
- `frontend/app/layout.tsx` — metadataBase, OG metadata, brand name
- `frontend/app/sitemap.ts` and `robots.ts` — hardcoded domain
- `frontend/next.config.ts` — image remote patterns
- `deploy.sh` — existing deploy script at repo root
- Architecture doc §Infrastructure & Deployment — confirms Vercel + DO Droplet + systemd + Nginx + Certbot intent

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — all changes were straightforward configuration updates with no runtime errors.

### Completion Notes List

- Implemented all Group A (code) tasks. Group B tasks (B1–B8) are manual operator steps for Boris to complete during production provisioning.
- A1: `EMAIL_FROM` setting added to `Settings` class with default `PersonnaPress <noreply@personnapress.com>`; both email functions now use `settings.EMAIL_FROM` instead of the hardcoded `.io` address.
- A2: All hardcoded `personapress.io` / `PersonaPress` (single-n) references fixed in `sitemap.ts`, `robots.ts`, `layout.tsx`, and `next.config.ts`. `metadataBase` and sitemap/robots URLs now read from `NEXT_PUBLIC_APP_URL` env var with production default. OG/Twitter image URLs changed to relative paths so `metadataBase` resolves them correctly.
- A3: `backend/.env.example` rewritten to add `EMAIL_FROM`, update `SENTRY_DSN` to empty-with-comment, update `APP_URL` to `https://personnapress.com`, add key-generation comment for `CREDENTIAL_ENCRYPTION_KEY`, and add all missing Stripe price / WP.com / Supabase vars. Frontend env examples both receive `NEXT_PUBLIC_APP_URL`.
- A4: `vercel.json` created at repo root pointing to `frontend/` as root directory.
- A5: `backend/deploy/` directory created with `personnapress-api.service` (systemd unit) and `nginx.conf` (HTTP→HTTPS redirect + proxy). `deploy.sh` verified — remote path `/var/www/personnapress` matches runbook.
- TypeScript check: no errors in source files; 8 pre-existing test-file type errors (test mock shape mismatches) are unrelated to this story.

### File List

- `backend/app/core/config.py` — added `EMAIL_FROM` setting
- `backend/app/integrations/email.py` — use `settings.EMAIL_FROM` in both send functions
- `backend/.env.example` — rewritten: CREDENTIAL_ENCRYPTION_KEY (one entry + generate comment), EMAIL_FROM, SENTRY_DSN empty, APP_URL updated, WP.com/Stripe price vars added
- `frontend/app/sitemap.ts` — URL from `NEXT_PUBLIC_APP_URL` env var
- `frontend/app/robots.ts` — sitemap URL from `NEXT_PUBLIC_APP_URL` env var
- `frontend/app/layout.tsx` — metadataBase from env var; brand name PersonnaPress (double-n) throughout; relative OG/Twitter image URLs
- `frontend/next.config.ts` — image remote pattern `*.personnapress.com` (was `*.personapress.io`)
- `frontend/.env.example` — added `NEXT_PUBLIC_APP_URL`
- `frontend/.env.local.example` — added `NEXT_PUBLIC_APP_URL`
- `vercel.json` — new file at repo root
- `backend/deploy/personnapress-api.service` — new systemd unit file
- `backend/deploy/nginx.conf` — new Nginx server block

### Review Findings

- [x] [Review][Patch] page.tsx has 8 hardcoded personapress.io domain references missed by migration [frontend/app/page.tsx]
- [x] [Review][Patch] APScheduler fires in all uvicorn workers — --workers 2 risks duplicate job execution including account deletion [backend/deploy/personnapress-api.service]
- [x] [Review][Patch] nginx missing security headers (HSTS, X-Frame-Options, X-Content-Type-Options) [backend/deploy/nginx.conf]
- [x] [Review][Patch] .env.local.example sets NEXT_PUBLIC_APP_URL to production URL instead of localhost [frontend/.env.local.example]
- [x] [Review][Patch] nginx missing proxy_http_version 1.1 and Connection keepalive directives [backend/deploy/nginx.conf]
- [x] [Review][Patch] vercel.json missing maxDuration for long-running API routes [vercel.json]
- [x] [Review][Patch] EMAIL_FROM unquoted angle brackets in .env.example — shell-unsafe [backend/.env.example]
- [x] [Review][Patch] robots.ts and sitemap.ts double-slash vulnerable if NEXT_PUBLIC_APP_URL has trailing slash [frontend/app/robots.ts, frontend/app/sitemap.ts]
- [x] [Review][Patch] frontend/.env.example X/Twitter OAuth comment still references your-app.vercel.app [frontend/.env.example]
- [x] [Review][Patch] SUPABASE_SERVICE_ROLE_KEY lacks RLS-bypass warning comment [backend/.env.example]
- [x] [Review][Defer] CORS locked to single APP_URL origin — preview deploys and localhost blocked [backend/app/main.py] — deferred, pre-existing
- [x] [Review][Defer] nginx no rate limiting on auth endpoints [backend/deploy/nginx.conf] — deferred, infrastructure enhancement beyond story scope
- [x] [Review][Defer] systemd no security hardening directives (NoNewPrivileges, ProtectSystem) [backend/deploy/personnapress-api.service] — deferred, infrastructure hardening beyond story scope
- [x] [Review][Defer] EnvironmentFile permissions not documented in deploy runbook — deferred, operator concern
- [x] [Review][Defer] EMAIL_FROM default domain causes Resend 422 in dev/staging — deferred, pre-existing operational concern
- [x] [Review][Defer] resend.api_key frozen at module import breaks test isolation [backend/app/integrations/email.py] — deferred, pre-existing design

### Change Log

- 2026-07-07: Implemented Group A production launch code changes — EMAIL_FROM env var, domain fix (personnapress.com), brand name fix (double-n), vercel.json, deploy service/nginx artifacts, env example updates (Story 9.1)
