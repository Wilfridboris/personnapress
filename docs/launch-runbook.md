# PersonnaPress — Production Launch Runbook

This runbook covers every manual step required to take PersonnaPress from a passing local dev environment to a live production system on `personnapress.com`. Follow each section in order — later sections depend on values produced by earlier ones.

**Audience:** Boris (operator). Code changes from Story 9.1 Group A are already committed and deployed.

---

## Architecture Overview

```mermaid
graph TB
    User["Browser / Social Crawler"]
    Vercel["Vercel (Next.js 16)\npersonnapress.com"]
    DO["DigitalOcean Droplet\napi.personnapress.com\n(FastAPI + uvicorn)"]
    Supabase["Supabase\n(PostgreSQL)"]
    Stripe["Stripe\n(Billing)"]
    Resend["Resend\n(Transactional Email)"]
    Sentry["Sentry\n(Error Tracking)"]

    User -->|HTTPS| Vercel
    Vercel -->|HTTPS API calls| DO
    DO -->|asyncpg| Supabase
    DO -->|webhooks & portal| Stripe
    DO -->|send email| Resend
    DO -->|error events| Sentry
    Vercel -->|Stripe webhook forward| DO
```

**Key constraint:** The Next.js frontend on Vercel forwards Stripe webhooks to FastAPI on the Droplet via the `INTERNAL_API_URL` env var. Both services must be live before end-to-end testing.

---

## Pre-flight Checklist

Work through this checklist before starting any provisioning.

- [ ] You have SSH access to a key pair (will be used for the Droplet)
- [ ] `personnapress.com` is registered and you have DNS management access
- [ ] Stripe account exists and you know how to switch to Live mode
- [ ] Resend account exists with API key available
- [ ] Supabase project is provisioned (reuse dev project or create a production one)
- [ ] Sentry account exists (or will be created in Step 7)
- [ ] GitHub repo is accessible at the URL you will use for `git clone`

---

## Step B1 — Fix Local `.env` (Do This First)

Your local `backend/.env` has a **duplicate** `CREDENTIAL_ENCRYPTION_KEY` entry that causes pydantic-settings to silently use the shorter key. Fix this before any other step so your local testing uses the correct key.

1. Open `backend/.env`
2. Find the two `CREDENTIAL_ENCRYPTION_KEY` lines
3. **Delete** the second one (the shorter `bugrn2MrPTe4LZHxAen7EPcqDy8Bu+1Z` entry on line 38)
4. Verify only one entry remains

> **Why this matters:** pydantic-settings reads the *last* occurrence of a duplicate key. The 32-char shorter key was silently overriding your hex key locally. Production will use a freshly generated key, so this only matters for local consistency.

---

## Step B2 — Stripe Live Mode Setup

### 2.1 Switch to Live Mode

In Stripe Dashboard, click the **Live mode** toggle in the top-left corner (it will turn green).

### 2.2 Create Products and Prices

Create three recurring monthly subscription products:

| Product Name | Price / month | Env var |
|---|---|---|
| Starter | $29 | `STRIPE_PRICE_STARTER` |
| Growth | $79 | `STRIPE_PRICE_GROWTH` |
| Agency | $199 | `STRIPE_PRICE_AGENCY` |

For each:
1. **Products → Add product** → set name and description
2. Add a **recurring monthly price** at the correct amount
3. Copy the `price_live_...` ID — you will need it for the Droplet `.env`

### 2.3 Copy API Keys

From **Developers → API keys**:
- `sk_live_...` → `STRIPE_SECRET_KEY` (backend Droplet + Vercel)
- `pk_live_...` → `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (Vercel only)

### 2.4 Create the Webhook Endpoint

1. **Developers → Webhooks → Add endpoint**
2. URL: `https://api.personnapress.com/api/v1/webhooks/stripe`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy the `whsec_...` signing secret → `STRIPE_WEBHOOK_SECRET`

### 2.5 Configure the Customer Portal

**Settings → Billing → Customer portal:**

| Setting | Value |
|---|---|
| Products and prices | Add all 3 live products |
| Allow customers to switch plans | Enabled |
| Allow customers to cancel subscriptions | Enabled |
| Allow customers to subscribe to products | Enabled (needed for trialing users) |
| Business information → Support email | your support email |
| Business information → Privacy policy URL | `https://personnapress.com/privacy` |

> **Critical:** Without "Allow customers to subscribe to products", trialing users who click "Subscribe" see an empty portal and cannot add a payment method.

---

## Step B3 — Provision DigitalOcean Droplet

### 3.1 Create the Droplet

In DigitalOcean Dashboard:
- **Image:** Ubuntu 24.04 LTS
- **Size:** $6/mo — 1 vCPU / 1 GB RAM
- **Region:** NYC1 or SFO3
- **Authentication:** add your SSH key
- Note the Droplet's **IPv4 address** — you need it for DNS (Step B5)

### 3.2 Run the Provisioning Commands

SSH in as root and run:

```bash
# Update system
apt-get update && apt-get upgrade -y
apt-get install -y python3.12 python3.12-venv python3-pip git nginx certbot python3-certbot-nginx

# Create app directory
mkdir -p /var/www/personnapress
chown www-data:www-data /var/www/personnapress

# Clone the repo
git clone https://github.com/<your-org>/PersonnaPress.git /var/www/personnapress
chown -R www-data:www-data /var/www/personnapress

# Create Python venv and install dependencies
python3.12 -m venv /var/www/personnapress/.venv
/var/www/personnapress/.venv/bin/pip install --upgrade pip
/var/www/personnapress/.venv/bin/pip install -r /var/www/personnapress/backend/requirements.txt
```

### 3.3 Create the Production `.env`

```bash
nano /var/www/personnapress/backend/.env
```

Populate using the checklist below. **Generate fresh secrets** — do not reuse dev values.

**Generate a new `CREDENTIAL_ENCRYPTION_KEY`:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

**Generate a new `JWT_SECRET`:**
```bash
openssl rand -hex 32
```

#### Backend `.env` Checklist

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-1-us-west-2.pooler.supabase.com:5432/postgres

# Secrets (generate fresh — do NOT reuse dev values)
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

# Stripe (live mode — from Step B2)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_live_...
STRIPE_PRICE_GROWTH=price_live_...
STRIPE_PRICE_AGENCY=price_live_...

# AI services
GEMINI_API_KEY=<same as dev or new key>
REPLICATE_API_TOKEN=<same as dev or new key>

# Observability (from Step B7)
SENTRY_DSN=https://<key>@sentry.io/<project-id>

# Email (from Step B8)
RESEND_API_KEY=re_...
EMAIL_FROM="PersonnaPress <noreply@personnapress.com>"

# App URL
APP_URL=https://personnapress.com

# Supabase Storage
SUPABASE_URL=https://btulxmvzxhlqfrnwoxtm.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<from Supabase Dashboard → Settings → API>

# Trial period
TRIAL_DAYS=14
```

> **Security:** After creating the file, run `chmod 600 /var/www/personnapress/backend/.env`. The file must not be world-readable.

### 3.4 Initialize the Database

```bash
cd /var/www/personnapress/backend
/var/www/personnapress/.venv/bin/alembic upgrade head
```

### 3.5 Install the spaCy Model

```bash
/var/www/personnapress/.venv/bin/python -m spacy download en_core_web_sm
```

> **Required:** the API will crash-loop on startup without this. The `deploy.sh` script runs this automatically on every deploy, but it must be done manually on first install.

### 3.6 Install and Start the Service

```bash
# Install systemd service
cp /var/www/personnapress/backend/deploy/personnapress-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable personnapress-api
systemctl start personnapress-api
systemctl status personnapress-api  # confirm: "active (running)"
```

### 3.6 Configure Nginx

> **Do this after DNS is pointing to the Droplet IP** — Certbot needs the domain to resolve.

```bash
# Install the site config
cp /var/www/personnapress/backend/deploy/nginx.conf /etc/nginx/sites-available/personnapress
ln -s /etc/nginx/sites-available/personnapress /etc/nginx/sites-enabled/personnapress
rm -f /etc/nginx/sites-enabled/default

# Test and reload
nginx -t          # must print "syntax is ok"
systemctl reload nginx

# Obtain TLS certificate
certbot --nginx -d api.personnapress.com
```

### 3.7 Smoke Test the API

```bash
curl https://api.personnapress.com/api/v1/health
# Expected: {"status":"ok"}
```

---

## Step B4 — Configure Vercel

### 4.1 Import the Project

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import the PersonnaPress GitHub repository
3. Vercel will detect `vercel.json` at the repo root and set the root directory to `frontend` automatically

### 4.2 Set Environment Variables

Add these in **Project → Settings → Environment Variables** (set scope to *Production*):

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.personnapress.com` |
| `NEXT_PUBLIC_APP_URL` | `https://personnapress.com` |
| `APP_URL` | `https://personnapress.com` |
| `BACKEND_URL` | `https://api.personnapress.com` |
| `INTERNAL_API_URL` | `https://api.personnapress.com` |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_live_...` |
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` (live) |
| `JWT_SECRET` | same as backend |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | same as backend |
| `GOOGLE_CLIENT_ID` | same as backend |
| `GOOGLE_CLIENT_SECRET` | same as backend ¹ |
| `NEXT_PUBLIC_X_CLIENT_ID` | `dW56bXF0YnhBTExiUUZRYUZYMGw6MTpjaQ` |
| `NEXT_PUBLIC_LINKEDIN_CLIENT_ID` | `86ayg7642eu9pw` |
| `WP_COM_CLIENT_ID` | `143164` |

> ¹ **Google only:** The Next.js Google callback route exchanges the token directly with Google's API, so `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are needed here. LinkedIn and X/Twitter callbacks just forward the auth code to the FastAPI backend — their secrets live on the Droplet only and must **not** be added to Vercel.

### 4.3 Trigger the First Deploy

Push to `main` or click **Redeploy** in the Vercel dashboard. Confirm the build succeeds and the preview URL loads the landing page.

### 4.4 Add Custom Domain

1. **Project → Settings → Domains** → add `personnapress.com` and `www.personnapress.com`
2. Vercel provides DNS records — you will apply them in Step B5

---

## Step B5 — DNS Configuration

In your DNS provider (wherever `personnapress.com` is registered):

| Record type | Name | Value |
|---|---|---|
| A or CNAME | `@` (root) | Vercel-provided value |
| CNAME | `www` | Vercel-provided value |
| A | `api` | Droplet IPv4 address |

> **Propagation:** DNS changes can take 5–30 minutes globally. Check with `dig personnapress.com` and `dig api.personnapress.com` until both resolve correctly.

After `api.personnapress.com` resolves, re-run the API smoke test:
```bash
curl https://api.personnapress.com/api/v1/health
# Expected: {"status":"ok"}
```

---

## Step B6 — Update OAuth Redirect URIs

Each OAuth provider must allowlist the production callback URL. Update all four.

### Twitter/X

1. [developer.twitter.com](https://developer.twitter.com) → your App → **App settings → Authentication settings**
2. **Callback URIs** → add `https://personnapress.com/api/auth/x/callback`
3. Update `X_REDIRECT_URI` in the Droplet's backend `.env` (already set correctly if you used the checklist above)

### LinkedIn

1. [linkedin.com/developers](https://www.linkedin.com/developers) → your App → **Auth tab**
2. **Authorized redirect URLs** → add `https://personnapress.com/api/auth/linkedin/callback`
3. Update `LINKEDIN_REDIRECT_URI` in the Droplet `.env` (already set)

### WordPress.com

1. [apps.wordpress.com](https://developer.wordpress.com/apps/) → your App
2. **Redirect URL** → set to `https://personnapress.com/api/auth/wordpress-com/callback`
3. Update `WP_COM_REDIRECT_URI` in the Droplet `.env` (already set)

### Google

1. [console.cloud.google.com](https://console.cloud.google.com) → **APIs & Services → Credentials** → your OAuth client
2. **Authorized redirect URIs** → add `https://personnapress.com/api/auth/google/callback`
3. Update `APP_URL=https://personnapress.com` in the Droplet `.env` (already set) — the backend constructs the Google redirect URI from `APP_URL`

After updating all four, restart the backend service so the new env values take effect:
```bash
systemctl restart personnapress-api
```

---

## Step B7 — Sentry Error Tracking

### 7.1 Create a Sentry Project

1. Go to [sentry.io](https://sentry.io) → **Projects → Create Project**
2. Platform: **Python**
3. Set alert frequency and notification preferences

### 7.2 Configure the DSN

1. Copy the DSN from the project settings (format: `https://<key>@<org>.ingest.sentry.io/<project-id>`)
2. Set `SENTRY_DSN=<your-dsn>` in the Droplet's `/var/www/personnapress/backend/.env`
3. Restart the service: `systemctl restart personnapress-api`

### 7.3 Verify

Trigger a test error (or wait for the first natural exception in production). Confirm the event appears in your Sentry project dashboard within ~60 seconds.

---

## Step B8 — Resend Email Domain Verification

### 8.1 Add the Domain

1. [resend.com/domains](https://resend.com/domains) → **Add Domain** → enter `personnapress.com`
2. Resend provides DKIM and SPF DNS records

### 8.2 Add DNS Records

In your DNS provider, add:

| Record type | Name | Value |
|---|---|---|
| TXT | `resend._domainkey` | DKIM public key (from Resend) |
| TXT | `@` | SPF record (from Resend — merge with existing if present) |
| MX | `send` | Resend MX (only needed for inbound — optional) |

### 8.3 Verify in Resend

Click **Verify** in the Resend dashboard. Status turns green when DNS propagates (~5–15 minutes).

### 8.4 Send a Test Email

In the app, trigger a user verification email or deletion warning email. Confirm delivery to your inbox with the correct `from` header: `PersonnaPress <noreply@personnapress.com>`.

---

## End-to-End Smoke Test

Once all steps are complete, walk through this checklist:

```
[ ] Landing page loads at https://personnapress.com
[ ] "Get Started" button routes to /register
[ ] User can register with email — verification email arrives from noreply@personnapress.com
[ ] User can log in with Google OAuth
[ ] Authenticated user can reach /dashboard
[ ] User can create a client and run the onboarding flow
[ ] Brain dump → campaign generation completes successfully
[ ] "Subscribe" button opens the Stripe Customer Portal with plans visible
[ ] Test subscription via Stripe test card → subscription webhook fires → user tier updates
[ ] Platform connection (Twitter/LinkedIn/WordPress) OAuth flow completes
[ ] Stripe billing portal shows correct plan and cancel option
[ ] Any backend exception appears in Sentry within 60 seconds
[ ] curl https://api.personnapress.com/api/v1/health → {"status":"ok"}
```

---

## Ongoing Deployments

After the initial launch, use the `deploy.sh` script at the repo root for all subsequent releases.

### Setup (one-time)

```bash
# Add to your shell profile (~/.zshrc or ~/.bashrc)
export DROPLET_IP=<your-droplet-ip>
export SSH_USER=root
```

### Deploy

```bash
# After merging to main:
./deploy.sh
```

The script: SSHs into the Droplet → `git pull origin main` → `pip install -r requirements.txt` → `alembic upgrade head` → `systemctl restart personnapress-api`. It fails fast on any error (`set -euo pipefail`).

> **Vercel deploys automatically** on every push to `main` — no manual step needed on the frontend side.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `curl` to API returns `502 Bad Gateway` | uvicorn not running | `systemctl status personnapress-api` — check logs with `journalctl -u personnapress-api -n 50` |
| Stripe webhook returns `400` | Wrong `STRIPE_WEBHOOK_SECRET` | Re-copy the `whsec_...` from Stripe Dashboard → Webhooks → your endpoint |
| OAuth callback returns `400 Redirect URI mismatch` | Provider allowlist not updated | Recheck Step B6 for that provider |
| Email not delivered | Resend domain not verified | Check Resend → Domains → `personnapress.com` status |
| Sentry events not appearing | `SENTRY_DSN` empty or wrong | `grep SENTRY_DSN /var/www/personnapress/backend/.env` — restart service after fix |
| Trialing user sees empty Stripe portal | Customer portal not configured | Recheck Step B2.5 — "Allow customers to subscribe to products" must be enabled |
| `alembic upgrade head` fails | DB connection string wrong | Verify `DATABASE_URL` uses the **pooler** URL (not direct connection) from Supabase |
