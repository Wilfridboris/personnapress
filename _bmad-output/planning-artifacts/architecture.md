---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-06-14'
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md'
  - '_bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/addendum.md'
workflowType: 'architecture'
project_name: 'PersonnaPress'
user_name: 'Boris'
date: '2026-06-14'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
28 FRs across 10 feature areas. The operational core is a multi-stage async pipeline:
Brain Dump → (Gemini blog generation + voice fidelity check) + (Gemini social generation) +
(FLUX.1 [pro] image) → human Approval Gate → multi-platform publish (WordPress, Webflow, X, LinkedIn).
Every stage runs as a FastAPI BackgroundTask backed by a persistent job record.

Feature areas and FR distribution:
- Account Management (FR-1 to FR-3): Registration, auth (email/password + Google OAuth), Stripe subscriptions
- Client Management (FR-4 to FR-7): CRUD for multi-client brand profiles (multi-tenancy)
- Brand Voice Ingestion (FR-8 to FR-11): Website scraping, file upload (Supabase Storage), Gemini extraction, manual questionnaire fallback
- Brain Dump Capture (FR-12): Text input (20–10,000 chars), triggers Campaign creation
- Content Generation (FR-13 to FR-15): Blog (SEO HTML, 800–1,500 words, 512 thinking tokens), social (X + LinkedIn, 0 thinking tokens), advisory voice fidelity check (256 tokens), 202 Accepted + polling pattern
- Image Generation (FR-16 to FR-17): FLUX.1 [pro] via Replicate, 1200x630 PNG, 3-regeneration cap
- Approval Gate (FR-18 to FR-21): Full preview (rendered HTML + social + image), WYSIWYG blog edit, approve/reject, rejection reason stored
- Publishing (FR-22 to FR-25): OAuth 2.0 (X PKCE, LinkedIn), credential-based (WordPress, Webflow), per-platform independence, immediate + scheduled, retry (3 attempts, persistent job records)
- Dashboard (FR-26 to FR-27): Campaign list with status filter, read-only content calendar
- Trial & Conversion (FR-28): 14-day trial, restricted state on expiry, 30+7 day retention policy, in-app nudges

**Non-Functional Requirements:**
- Performance: Content generation (blog + social + image) within 120s at 95th percentile; frontend interactive within 2s on 4G
- Availability: 99.5% uptime; Droplet is single point of failure for API layer in v1
- Security: HTTPS/TLS 1.3; AES-256-GCM credential encryption (key in env vars, not Supabase); parameterized queries; output encoding for user HTML; CSRF via origin checking; OAuth scopes minimized per platform
- Scalability: Supabase removes DB bottleneck; Droplet ceiling ~50 concurrent gen requests ($6), ~100 ($12); path to container orchestration beyond that
- Data Integrity: Supabase Pro PITR; persistent job records for all async work
- Observability: Structured JSON logging; Sentry (or equivalent)
- Job Durability: All generation, publishing, scheduling, retry tasks backed by Supabase Postgres job records -- survive process restarts

**Scale & Complexity:**
- Primary domain: Full-stack web + async backend pipeline
- Complexity level: High
- Estimated architectural components: ~12 (auth layer, client management, brand ingestion pipeline, brain dump intake, generation pipeline, image pipeline, approval gate, publishing dispatcher, scheduler, job tracker, subscription enforcer, dashboard/calendar)

### Technical Constraints & Dependencies

External dependencies (9):
1. Google Gemini 2.5 Flash -- generation + voice extraction (tiered thinking budgets: 0/256/512/1024)
2. Replicate FLUX.1 [pro] -- featured image generation
3. Stripe -- subscription billing, Customer Portal, webhook events
4. Google Cloud OAuth 2.0 -- Google sign-in
5. Twitter API v2 (OAuth 2.0 PKCE) -- X publishing
6. LinkedIn UGC Posts API v2 (OAuth 2.0, `w_member_social` scope) -- LinkedIn publishing
7. WordPress REST API v2 -- blog publishing (draft-first publish pattern)
8. Webflow CMS API v2 -- blog publishing (create + separate publish endpoint)
9. Supabase -- Postgres (application data + APScheduler job store) + Storage (uploads + FLUX images)

Infrastructure:
- Next.js (App Router) on Vercel -- frontend
- FastAPI on DigitalOcean $6 Droplet (1 vCPU / 1 GB) + Nginx reverse proxy + systemd
- APScheduler with SQLAlchemy job store pointing at Supabase Postgres
- Serverless timeout constraint (10--60s on Vercel) drives all long-running work to FastAPI BackgroundTasks

Hard constraints:
- All LLM and image generation must run server-side (API keys not exposed to client)
- Credential decryption happens only at publish time on the Droplet; keys never touch Supabase
- Gemini 2.5 Flash is single-provider; 3 consecutive 5xx/429 responses set Campaign to `failed`
- Outbound publish calls staggered: 2s between X posts, 5s between LinkedIn posts

### Cross-Cutting Concerns Identified

1. **Authentication & session gating** -- All API routes require valid session token; 7-day session duration
2. **Subscription tier enforcement** -- Client count, campaign count, image generation count checked before every create/generate action
3. **Job durability** -- Persistent Supabase Postgres job records for all async operations (generation, publish, schedule, retry); APScheduler recovers on restart
4. **Credential encryption/decryption lifecycle** -- Encrypt on storage, decrypt only at publish time, key in Droplet env only, never logged
5. **Campaign status state machine** -- `pending_approval -> approved -> published / rejected / failed`; transitions must be atomic and consistent across all code paths
6. **Per-user rate limiting** -- 10 req/min/user enforced at FastAPI layer
7. **Outbound API rate-limit mitigation** -- Staggered publish calls per platform (2--5s intervals); X API uses `tweet.fields` selective parameters
8. **Error taxonomy** -- 5 independent publishers; per-platform failure tracking; partial publish not distinguished from full failure in v1 (both show as `failed`)
9. **Cost control** -- Per-user Gemini token usage + Replicate image count logged to `generation_logs` table; hard limits enforce plan tier before generation starts
10. **Content security** -- User-submitted HTML content (Brain Dump + edited blog drafts) must be sanitized before rendering in approval preview (XSS)

## Starter Template Evaluation

### Primary Technology Domain

Full-stack web + async backend pipeline: dual-application architecture
(Next.js frontend + FastAPI backend as separate applications, both backed by
Supabase Postgres + Storage).

### Technical Preferences

Stack is pre-defined in the PRD -- no discovery needed:
- Frontend: Next.js 16.2.9 LTS (App Router, TypeScript, Tailwind CSS) on Vercel
- Backend: Python 3.12 + FastAPI (latest) on DigitalOcean Droplet
- Database/Storage: Supabase Postgres + Supabase Storage
- Deployment: Vercel (frontend) + DigitalOcean Droplet via systemd + Nginx (backend)

### Repository Structure Decision

**Mono-repo with two application roots:**

```
/
├── frontend/     ← Next.js 16 App Router application
├── backend/      ← FastAPI application
└── _bmad-output/ ← Planning artifacts
```

Single repository simplifies shared context (env references, API contract
visibility) without requiring a monorepo toolchain (Turborepo, Nx, etc.).

### Frontend Starter: create-next-app (Next.js 16.2.9 LTS)

**Initialization Command:**

```bash
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --import-alias "@/*" \
  --use-npm
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:** TypeScript (strict mode) on Node.js 20+

**Styling Solution:** Tailwind CSS v4 (default in Next.js 16 starter). Paper Style
design tokens (palette, typography, spacing) added as Tailwind theme extension.

**Build Tooling:** Turbopack (default bundler in Next.js 16). Zero config needed.

**Testing Framework:** Not included -- add Vitest + React Testing Library as a
follow-on configuration story.

**Code Organization (App Router conventions):**

```
frontend/
├── app/
│   ├── (auth)/             ← Auth route group (login, register, verify)
│   ├── (app)/              ← Protected route group (dashboard, campaigns, etc.)
│   └── api/                ← Next.js API routes (Stripe webhooks, OAuth callbacks only)
├── components/
│   ├── ui/                 ← Base Paper Style design system components
│   └── [feature]/          ← Feature-scoped components
├── lib/                    ← API client, auth helpers, utilities
├── hooks/                  ← Custom React hooks
└── types/                  ← TypeScript types and API contract types
```

**Development Experience:** Hot reload via Turbopack, TypeScript inference on Server
Components, ESLint with Next.js ruleset.

### Backend Starter: FastAPI Manual Setup (FastAPI latest, Python 3.12)

No official CLI generator is used. FastAPI projects are bootstrapped manually
using a standard layered architecture.

**Initialization Commands:**

```bash
mkdir backend && cd backend
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install "fastapi[standard]" uvicorn[standard] \
  sqlalchemy asyncpg apscheduler \
  cryptography python-jose[cryptography] \
  httpx beautifulsoup4 python-multipart \
  stripe google-generativeai replicate \
  sentry-sdk
pip freeze > requirements.txt
```

**Code Organization (layered architecture):**

```
backend/
├── app/
│   ├── routers/            ← HTTP route handlers (thin -- delegate to services)
│   │   ├── auth.py
│   │   ├── clients.py
│   │   ├── campaigns.py
│   │   ├── publishing.py
│   │   └── webhooks.py     ← Stripe webhook endpoint
│   ├── services/           ← Business logic and orchestration
│   │   ├── generation.py   ← Gemini pipeline + voice fidelity check
│   │   ├── image.py        ← Replicate FLUX.1 [pro] pipeline
│   │   ├── publishing.py   ← Multi-platform publish dispatcher
│   │   ├── ingestion.py    ← Website scraping + voice extraction
│   │   └── subscription.py ← Plan tier enforcement
│   ├── workers/            ← FastAPI BackgroundTasks handlers
│   │   ├── generate.py
│   │   └── publish.py
│   ├── scheduler/          ← APScheduler setup with SQLAlchemy job store -> Supabase Postgres
│   │   └── scheduler.py
│   ├── db/
│   │   ├── connection.py   ← Supabase Postgres connection pool
│   │   └── repositories/   ← One file per entity (users, clients, campaigns, jobs, etc.)
│   ├── schemas/            ← Pydantic request/response models
│   ├── core/
│   │   ├── config.py       ← Pydantic Settings (reads env vars)
│   │   ├── security.py     ← AES-256-GCM encrypt/decrypt, session token logic
│   │   └── rate_limit.py   ← 10 req/min/user enforcement
│   └── integrations/       ← One module per external API
│       ├── wordpress.py
│       ├── webflow.py
│       ├── twitter.py
│       ├── linkedin.py
│       ├── gemini.py
│       └── replicate.py
├── tests/
├── main.py                 ← App instantiation, router registration, lifespan hooks
├── requirements.txt
└── .env.example
```

**Note:** Project initialization using these commands should be the first
implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Auth mechanism: Custom JWT in httpOnly cookie
- Database access: SQLModel (Pydantic + SQLAlchemy unified)
- Migration tool: Alembic
- Frontend -> Backend communication: Direct client-side fetch with credentials
- Frontend state: Zustand (UI) + React Query (server state)
- Rich text editor: Tiptap

**Deferred Decisions (Post-MVP):**
- Transactional email provider (required for FR-1 email verification -- not specified in PRD;
  flagged as open item before implementation)
- HSM/KMS key management (env var approach sufficient for v1 per A-33)
- Failover for FastAPI Droplet (single point of failure accepted for v1 per §10)

---

### Data Architecture

**ORM / Data Access: SQLModel (latest)**
- Rationale: Single model definition covers both DB schema and Pydantic request/response
  validation. Eliminates the duplication of separate SQLAlchemy models + Pydantic schemas.
  Built on SQLAlchemy under the hood -- APScheduler's SQLAlchemy job store coexists without
  conflict.
- Affects: All backend repositories, all Pydantic schemas, APScheduler job store config

**Migration Tool: Alembic**
- Rationale: Version-controlled migration files with rollback support. Works natively with
  SQLAlchemy (SQLModel's underlying engine). Migration history lives in `backend/alembic/versions/`.
- `env.py` configured to read Supabase Postgres connection string from environment.
- Affects: All schema changes, initial schema creation story

**Schema (7 tables, from PRD Addendum §C):**
- `users` -- account records, Stripe customer ID, Google OAuth subject ID
- `subscriptions` -- Stripe subscription state, plan tier, billing cycle, usage counters
- `clients` -- brand identities per user, Brand Voice Profile JSON
- `platform_connections` -- one row per client-platform pair, encrypted credentials
- `campaigns` -- content production records, status state machine
- `jobs` -- persistent job records (generation, publish, schedule, retry tracking)
- `generation_logs` -- per-user Gemini token + Replicate image usage for internal cost monitoring

**Caching Strategy: None (v1)**
- Supabase Postgres with PgBouncer connection pooling handles concurrent reads.
- No Redis or in-memory cache layer. Revisit if query latency becomes measurable post-launch.

---

### Authentication & Security

**Session Mechanism: Custom JWT in httpOnly cookie**
- FastAPI issues a signed JWT on successful login (email/password or Google OAuth exchange).
- Cookie flags: `httpOnly=True`, `secure=True`, `samesite="lax"`, 7-day expiry.
- JWT payload: `user_id`, `email`, `plan_tier`, `exp`.
- JWT secret stored as `JWT_SECRET` env var on the Droplet. Same secret used by Next.js
  middleware for edge-side validation (server-side only -- never exposed as NEXT_PUBLIC_).
- FastAPI dependency `get_current_user` extracts and validates JWT on every protected route.

**Google OAuth Flow:**
1. Next.js redirects user to Google OAuth consent screen.
2. Google returns auth code to Next.js callback route (`/api/auth/google/callback`).
3. Next.js exchanges code for Google user profile (server-side).
4. Next.js calls FastAPI `POST /auth/google` with the verified Google profile.
5. FastAPI creates or finds the user record, issues JWT, sets httpOnly cookie.

**Password Hashing: bcrypt via `passlib[bcrypt]`**
- Hashing happens in FastAPI only -- never in Next.js.

**Credential Encryption: AES-256-GCM (cryptography library)**
- Encrypt on `platform_connections` write; decrypt only at publish time in `services/publishing.py`.
- Encryption key (`CREDENTIAL_ENCRYPTION_KEY`) in Droplet env only. Never logged, never in DB.

**CORS:**
- FastAPI `CORSMiddleware`: `allow_origins=[APP_URL]`, `allow_credentials=True`,
  `allow_methods=["*"]`, `allow_headers=["*"]`.
- All fetch calls from Next.js: `credentials: "include"`.

**Email Verification (FR-1, A-3) -- OPEN ITEM:**
- Email verification is required before first use but transactional email provider is not
  specified in the PRD. Must be decided before the auth implementation story.
- Options: Resend, SendGrid, AWS SES. Recommend Resend (developer-friendly, generous free tier).
- This is a pre-implementation blocker for Story: User Registration.

---

### API & Communication Patterns

**API Style: REST (JSON)**
- FastAPI auto-generates OpenAPI docs at `/docs` (development only -- disabled in production).
- All endpoints versioned under `/api/v1/` prefix.

**Error Response Standard:**
```json
{
  "error": {
    "code": "CAMPAIGN_LIMIT_EXCEEDED",
    "message": "Your plan allows 10 campaigns per billing cycle.",
    "detail": {}
  }
}
```
- Machine-readable `code` (SCREAMING_SNAKE_CASE) for frontend logic.
- Human-readable `message` for display (follows Paper Style tone -- specific and actionable).

**Frontend -> Backend: Direct client-side fetch**
- Next.js components call FastAPI directly via `NEXT_PUBLIC_API_URL`.
- All calls include `credentials: "include"` for cookie transport.
- Job status polling (FR-15): React Query `useQuery` with `refetchInterval: 2000` while
  job status is `pending` or `in_progress`. Polling stops when status reaches terminal state.
- Stripe webhooks: handled by Next.js `app/api/webhooks/stripe/route.ts` (not FastAPI).
- Google OAuth callbacks: handled by Next.js `app/api/auth/google/callback/route.ts`.

**Rate Limiting: slowapi (FastAPI middleware)**
- 10 requests/minute/user enforced at FastAPI middleware layer.
- Returns HTTP 429 with `Retry-After` header.

---

### Frontend Architecture

**State Management: Zustand (UI state) + React Query (server state)**

Zustand stores:
- `useClientStore`: active client ID, client list (client-side context switch)
- `useUIStore`: modal state, sidebar collapse, toast queue

React Query usage:
- All server data fetching and mutations (campaigns, clients, brand voice, platform connections)
- Job status polling with `refetchInterval`
- Automatic cache invalidation on mutations

**Component Architecture:**
- Server Components for initial page renders and SEO-sensitive content (dashboard shell,
  campaign list initial load).
- Client Components (`"use client"`) for interactive surfaces: Brain Dump input, Approval Gate,
  Tiptap editor, polling hooks.
- Route groups enforce auth boundary: `(auth)/` is public; `(app)/` requires valid JWT
  (enforced by Next.js middleware reading cookie).

**Rich Text Editor: Tiptap**
- Packages: `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/extension-link`
- Input: parse stored HTML string into Tiptap on editor mount (`setContent(htmlString)`)
- Output: `editor.getHTML()` on save/approve -- returns semantic HTML string stored on Campaign
- Styled via Tailwind CSS prose classes (`@tailwindcss/typography`)

**Performance:**
- React Query deduplicates in-flight requests and caches aggressively.
- Turbopack handles bundle splitting automatically.
- Images: `next/image` for all image rendering (including FLUX generated images from
  Supabase Storage CDN URLs).

---

### Infrastructure & Deployment

**CI/CD:**
- Frontend: Push to `main` auto-triggers Vercel deployment via GitHub Actions.
- Backend: Manual `deploy.sh` script run locally. SSHes into the DO Droplet and executes
  the deploy sequence including `alembic upgrade head` before service restart.

```bash
#!/bin/bash
# deploy.sh
ssh user@<droplet-ip> << 'EOF'
  cd /var/www/personnapress-api
  git pull origin main
  source .venv/bin/activate
  pip install -r requirements.txt
  alembic upgrade head
  sudo systemctl restart personnapress-api
EOF
```

**Environment Configuration:**
- Three environments: `development` (local), `staging` (optional), `production`.
- Frontend env vars: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`.
- Backend env vars: `DATABASE_URL`, `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`,
  `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `GEMINI_API_KEY`, `REPLICATE_API_TOKEN`, `SENTRY_DSN`.
- `.env.example` committed; `.env` gitignored.

**Process Management: systemd**
- FastAPI runs as `uvicorn app.main:app --workers 2 --port 8000`.
- Nginx reverse proxies port 80/443 -> 8000. TLS via Let's Encrypt (Certbot).

**Monitoring & Observability:**
- Sentry SDK integrated in both Next.js (`@sentry/nextjs`) and FastAPI (`sentry-sdk`).
- Structured JSON logging in FastAPI (Python `logging` with JSON formatter).
- Supabase Dashboard for database metrics and Storage usage.

**Scaling Path:**
- Launch: $6 DO Droplet (1 vCPU / 1 GB) -- ~50 concurrent gen requests
- Growth: $12 DO Droplet (2 vCPU / 2 GB) -- ~100 concurrent gen requests
- Scale: DO App Platform or Fly.io container orchestration

### Decision Impact Analysis

**Implementation Sequence (order matters):**
1. Resolve transactional email provider (blocks auth story)
2. Supabase project setup + Alembic initial migration (all stories depend on schema)
3. FastAPI project init + auth routes (JWT issue/validate, Google OAuth exchange)
4. Next.js project init + middleware (cookie validation, route group protection)
5. Stripe integration + subscription enforcement middleware
6. Client management + Brand Ingestion pipeline
7. Generation pipeline (Gemini + FLUX.1 [pro])
8. Approval Gate (Tiptap editor integration)
9. Publishing dispatcher (5 platform integrations)
10. APScheduler setup (scheduled publishing)
11. Dashboard + content calendar

**Cross-Component Dependencies:**
- Auth (JWT) is a hard dependency for every other backend route
- Subscription tier enforcement depends on auth (needs `plan_tier` from JWT payload)
- Generation pipeline depends on Client (needs Brand Voice Profile)
- Publishing depends on Platform Connections (needs encrypted credentials)
- APScheduler job store depends on Supabase Postgres being initialized
- Polling (React Query) depends on Jobs table existing in schema

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

12 areas where AI agents could make different, incompatible choices:
naming (DB, API, code, files), API response format, React Query key structure,
Zustand store shape, error handling surface, loading states, SQLModel conventions,
FastAPI dependency patterns, BackgroundTask patterns, date/time handling,
boolean/null representation, and test file placement.

---

### Naming Patterns

**Database Naming (Postgres / SQLModel):**
- Tables: `snake_case` plural -- `users`, `platform_connections`, `generation_logs`
- Columns: `snake_case` -- `created_at`, `user_id`, `brand_voice_profile`
- Foreign keys: `{referenced_table_singular}_id` -- `user_id`, `client_id`, `campaign_id`
- Indexes: `ix_{table}_{column}` -- `ix_users_email`, `ix_campaigns_client_id`
- SQLModel class names: PascalCase singular -- `User`, `Client`, `Campaign`, `Job`

```python
# CORRECT
class PlatformConnection(SQLModel, table=True):
    __tablename__ = "platform_connections"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

# WRONG -- never camelCase columns or mixed table naming
class platformConnection(SQLModel, table=True):
    __tablename__ = "PlatformConnections"
    clientId: uuid.UUID
```

**API Endpoint Naming:**
- Resource names: plural noun -- `/api/v1/clients`, `/api/v1/campaigns`
- Nested resources: `/{parent}/{id}/{child}` -- `/api/v1/clients/{client_id}/campaigns`
- Actions that are not CRUD: verb suffix -- `/api/v1/campaigns/{id}/approve`,
  `/api/v1/campaigns/{id}/publish`, `/api/v1/clients/{id}/ingest`
- Path parameters: `snake_case` -- `{client_id}`, `{campaign_id}`
- Query parameters: `snake_case` -- `?status=published&page=1`

**Python Code Naming (FastAPI / backend):**
- Modules/files: `snake_case.py` -- `generation.py`, `platform_connections.py`
- Functions: `snake_case` -- `get_current_user`, `encrypt_credential`
- Classes: `PascalCase` -- `GenerationService`, `PublishDispatcher`
- Constants: `SCREAMING_SNAKE_CASE` -- `MAX_RETRY_ATTEMPTS`, `JWT_ALGORITHM`
- Pydantic/SQLModel fields: `snake_case` -- `user_id`, `brand_voice_profile`

**TypeScript / Next.js Code Naming:**
- React components: `PascalCase` -- `CampaignCard`, `BrainDumpInput`
- Component files: `PascalCase.tsx` -- `CampaignCard.tsx`, `BrainDumpInput.tsx`
- Hooks: `camelCase` prefixed with `use` -- `useActiveClient`, `useCampaignStatus`
- Hook files: `camelCase.ts` -- `useActiveClient.ts`
- Utility functions: `camelCase` -- `formatCampaignStatus`, `sanitizeHtml`
- TypeScript types/interfaces: `PascalCase` -- `Campaign`, `BrandVoiceProfile`
- Zustand stores: `use{Domain}Store` -- `useClientStore`, `useUIStore`
- React Query keys: array format, kebab-case strings -- `["campaigns", clientId]`,
  `["campaign", campaignId, "status"]`

---

### Structure Patterns

**Test File Placement:**
- Backend: `backend/tests/` mirroring app structure --
  `tests/routers/test_campaigns.py`, `tests/services/test_generation.py`
- Frontend: co-located with source -- `CampaignCard.test.tsx` next to `CampaignCard.tsx`

**Frontend Component Organization:**
- Shared base components (Paper Style primitives): `components/ui/`
- Feature-scoped components: `components/{feature}/` -- `components/campaigns/`,
  `components/clients/`, `components/publishing/`
- Page-level components stay in `app/` route segments, not in `components/`

**Backend Router/Service/Repository Pattern:**
- Routers: HTTP concerns only (parse request, call service, return response)
- Services: business logic and orchestration (call repositories + integrations)
- Repositories: database queries only (no business logic)
- Integrations: one file per external API, no business logic

```python
# CORRECT -- router delegates immediately
@router.post("/campaigns/{campaign_id}/approve")
async def approve_campaign(
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
):
    return await service.approve(campaign_id, current_user.id)

# WRONG -- business logic in router
@router.post("/campaigns/{campaign_id}/approve")
async def approve_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign.status != "pending_approval":
        raise HTTPException(...)
    campaign.status = "approved"
    db.commit()
```

---

### Format Patterns

**API Response Format:**
- Success (single item): return the resource directly -- `return campaign`
- Success (list): `{"items": [...], "total": int}` wrapper
- Success (action): `{"success": true, "message": "Campaign approved."}`
- Error: `{"error": {"code": "SCREAMING_SNAKE_CASE", "message": "...", "detail": {}}}`
- HTTP status codes: 200 (GET/PATCH success), 201 (POST creates resource),
  202 (async task accepted), 400 (validation), 401 (unauthenticated),
  403 (forbidden), 404 (not found), 409 (conflict), 422 (unprocessable),
  429 (rate limited), 500 (server error)

**JSON Field Naming:**
- FastAPI responses: `snake_case` (Pydantic default, matches DB column names)
- Next.js receives `snake_case` and uses it as-is -- no camelCase conversion layer
- All TypeScript types mirror the snake_case API shape

```typescript
// CORRECT -- mirrors API snake_case directly
interface Campaign {
  id: string
  client_id: string
  brand_voice_score: number | null
  created_at: string
}

// WRONG -- camelCase conversion
interface Campaign {
  id: string
  clientId: string
  brandVoiceScore: number | null
  createdAt: string
}
```

**Date/Time Format:**
- All timestamps: ISO 8601 UTC strings -- `"2026-06-14T13:00:00Z"`
- Stored in Postgres as `TIMESTAMP WITH TIME ZONE`
- Never store or return Unix timestamps
- Frontend formatting: use `Intl.DateTimeFormat` with user's locale

**Null Handling:**
- Missing optional values: `null` in JSON (never `undefined`, never omitted)
- Empty lists: `[]` (never `null`)
- Boolean fields: `true`/`false` only (never `1`/`0`)

---

### State Management Patterns

**React Query Key Structure:**
```typescript
// Resource collections
["clients"]                          // all clients for current user
["campaigns", clientId]              // campaigns for a client
["campaigns", clientId, { status }]  // filtered campaigns

// Single resources
["client", clientId]
["campaign", campaignId]

// Polling targets (job status)
["job", jobId]                       // refetchInterval: 2000 while pending/in_progress

// Platform connections
["platform-connections", clientId]
```

**Zustand Store Shape:**
```typescript
// useClientStore
interface ClientStore {
  activeClientId: string | null
  setActiveClientId: (id: string) => void
}

// useUIStore
interface UIStore {
  isModalOpen: boolean
  modalType: string | null
  openModal: (type: string) => void
  closeModal: () => void
  toasts: Toast[]
  addToast: (toast: Toast) => void
  removeToast: (id: string) => void
}
```

**Mutation + Cache Invalidation Pattern:**
```typescript
// CORRECT -- always invalidate the relevant query after mutation
const approveCampaign = useMutation({
  mutationFn: (campaignId: string) => api.post(`/campaigns/${campaignId}/approve`),
  onSuccess: (_, campaignId) => {
    queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] })
    queryClient.invalidateQueries({ queryKey: ["campaigns", activeClientId] })
  },
})
```

---

### Process Patterns

**Error Handling:**

Backend:
- Validation errors: raise `HTTPException(status_code=422, detail=...)`
- Business rule violations: raise `HTTPException(status_code=400, detail=...)`
- Not found: raise `HTTPException(status_code=404)`
- Auth failures: raise `HTTPException(status_code=401)`
- All exceptions caught at service layer; never let raw Python exceptions bubble to router

Frontend:
- Server errors (4xx/5xx): surface via toast using `useUIStore.addToast`
- Form validation errors: inline under the relevant field
- Network errors: toast with retry option
- Never `console.error` as the sole error handler -- always surface to user

```typescript
// CORRECT
const submitBrainDump = useMutation({
  mutationFn: api.createCampaign,
  onError: (error) => addToast({ type: "error", message: error.message }),
})

// WRONG -- silent failure
const submitBrainDump = useMutation({
  mutationFn: api.createCampaign,
  onError: (error) => console.error(error),
})
```

**Loading State Pattern:**
- Use React Query's `isLoading`, `isFetching`, `isPending` -- never manage loading booleans manually
- Skeleton loaders for initial page content (not spinners)
- Inline spinner only for action buttons (approve, publish, generate)
- Typewriter animation for generation in-progress (per PRD design spec)

**FastAPI BackgroundTask Pattern:**
```python
# CORRECT -- create job record first, then dispatch
@router.post("/campaigns", status_code=202)
async def create_campaign(
    data: CampaignCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
):
    campaign, job = await service.create_with_job(data, current_user.id)
    background_tasks.add_task(generate_campaign_content, job.id)
    return {"campaign_id": campaign.id, "job_id": job.id}

# WRONG -- dispatch without creating job record
@router.post("/campaigns", status_code=202)
async def create_campaign(data: CampaignCreate, background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_campaign_content, data)
    return {"status": "processing"}
```

**Credential Encrypt/Decrypt Pattern:**
- Encrypt: only in `app/routers/platform_connections.py` before calling repository
- Decrypt: only in `app/services/publishing.py` immediately before the API call
- Never pass decrypted credentials across function boundaries
- Never log credential values at any level

---

### Enforcement Guidelines

**All AI Agents MUST:**
- Use `snake_case` for all DB columns, API query params, and JSON fields (both directions)
- Create a `jobs` record before dispatching any `BackgroundTask`
- Validate subscription tier limits before any generation or client-creation action
- Return errors in `{"error": {"code": "...", "message": "...", "detail": {}}}` format
- Use React Query for all server state -- never `useState` + `useEffect` for data fetching
- Sanitize user-provided HTML before rendering in any preview context
- Prefix all FastAPI routes with `/api/v1/`

**Anti-Patterns (never do these):**
- `useState(false)` for loading state when React Query's `isLoading` is available
- Business logic in FastAPI routers
- Decrypted credentials stored in variables beyond the immediate API call scope
- Direct DB queries in routers (always go through repositories)
- `any` type in TypeScript without a comment explaining why
- Catching and swallowing exceptions without logging to Sentry

## Project Structure & Boundaries

### Complete Project Directory Structure

```
personnapress/                              ← mono-repo root
├── .github/
│   └── workflows/
│       └── frontend-deploy.yml            ← Vercel deploy on push to main (frontend/** changes)
├── deploy.sh                              ← Manual backend SSH deploy script
├── .gitignore
├── README.md
│
├── frontend/                              ← Next.js 16.2.9 LTS
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts                 ← Paper Style design tokens as theme extension
│   ├── tsconfig.json
│   ├── .env.local                         ← gitignored
│   ├── .env.example
│   ├── middleware.ts                       ← JWT cookie validation, (app)/ route protection
│   ├── app/
│   │   ├── layout.tsx                     ← Root layout: QueryClientProvider, Zustand init
│   │   ├── globals.css                    ← Tailwind base + Paper Style CSS custom properties
│   │   ├── (auth)/                        ← Public route group
│   │   │   ├── login/page.tsx
│   │   │   ├── register/page.tsx
│   │   │   └── verify-email/page.tsx
│   │   ├── (app)/                         ← Protected route group (JWT required via middleware)
│   │   │   ├── layout.tsx                 ← App shell: sidebar, client switcher, trial banner
│   │   │   ├── dashboard/page.tsx         ← FR-26: Campaign list + FR-27: Calendar tabs
│   │   │   ├── campaigns/
│   │   │   │   ├── new/page.tsx           ← FR-12: Brain Dump input
│   │   │   │   └── [id]/page.tsx          ← FR-18-21: Approval Gate
│   │   │   ├── clients/
│   │   │   │   ├── page.tsx               ← FR-7: Client list + switch
│   │   │   │   ├── new/page.tsx           ← FR-4: Create Client
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx           ← FR-5,8-11: Edit Client + Brand Voice Profile
│   │   │   │       └── connections/page.tsx ← FR-22: Platform Connection Setup
│   │   │   ├── settings/page.tsx          ← FR-3: Subscription management (Stripe Portal link)
│   │   │   └── calendar/page.tsx          ← FR-27: Standalone content calendar (read-only)
│   │   └── api/                           ← Next.js API routes (only these two)
│   │       ├── auth/google/callback/route.ts  ← Google OAuth code exchange -> calls FastAPI
│   │       └── webhooks/stripe/route.ts       ← Stripe webhook receiver -> calls FastAPI
│   ├── components/
│   │   ├── ui/                            ← Paper Style primitive components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx                  ← bottom-border style, monospace variant
│   │   │   ├── Badge.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── StatusBadge.tsx            ← Campaign status (pending/approved/published/rejected/failed)
│   │   ├── campaigns/
│   │   │   ├── BrainDumpInput.tsx         ← FR-12: monospace textarea, auto-expand, char count
│   │   │   ├── CampaignCard.tsx           ← FR-26: list item with status badge + dates
│   │   │   ├── CampaignList.tsx           ← FR-26: filterable list (status filter)
│   │   │   ├── ApprovalGate.tsx           ← FR-18-21: full review interface container
│   │   │   ├── BlogPreview.tsx            ← FR-18: rendered HTML (DOMPurify sanitized)
│   │   │   ├── BlogEditor.tsx             ← FR-19: Tiptap WYSIWYG editor
│   │   │   ├── SocialPostPreview.tsx      ← FR-18: X (280 char) + LinkedIn preview
│   │   │   ├── ImagePreview.tsx           ← FR-16-17: featured image + regenerate button
│   │   │   ├── GenerationStatus.tsx       ← FR-15: typewriter animation loading state
│   │   │   ├── VoiceFidelityBadge.tsx     ← FR-13: advisory score badge
│   │   │   ├── PublishButton.tsx          ← FR-23: immediate publish action + confirm
│   │   │   └── SchedulePicker.tsx         ← FR-24: datetime picker for scheduled publish
│   │   ├── clients/
│   │   │   ├── ClientCard.tsx             ← FR-7
│   │   │   ├── ClientSwitcher.tsx         ← FR-7: app shell dropdown
│   │   │   ├── BrandVoiceProfile.tsx      ← FR-10-11: display + inline edit
│   │   │   └── VoiceQuestionnaire.tsx     ← FR-10: manual fallback questionnaire
│   │   ├── publishing/
│   │   │   ├── PlatformConnectionCard.tsx ← FR-22: per-platform connection status
│   │   │   ├── WordPressConnect.tsx       ← FR-22: site URL + Application Password form
│   │   │   ├── WebflowConnect.tsx         ← FR-22: API token + Collection ID form
│   │   │   ├── TwitterConnect.tsx         ← FR-22: OAuth 2.0 PKCE flow initiation
│   │   │   └── LinkedInConnect.tsx        ← FR-22: OAuth 2.0 flow initiation
│   │   ├── calendar/
│   │   │   └── ContentCalendar.tsx        ← FR-27: month view, read-only
│   │   └── layout/
│   │       ├── AppShell.tsx
│   │       ├── Sidebar.tsx
│   │       ├── TopBar.tsx
│   │       └── TrialBanner.tsx            ← FR-28: persistent upgrade banner on trial expiry
│   ├── hooks/
│   │   ├── useActiveClient.ts
│   │   ├── useCampaigns.ts                ← React Query: campaigns list + create mutation
│   │   ├── useCampaign.ts                 ← React Query: single campaign + approve/reject
│   │   ├── useJobStatus.ts                ← React Query polling (refetchInterval: 2000)
│   │   ├── useClients.ts
│   │   ├── usePlatformConnections.ts
│   │   └── useSubscription.ts
│   ├── lib/
│   │   ├── api.ts                         ← fetch wrapper (base URL, credentials: include, error parsing)
│   │   ├── auth.ts                        ← JWT cookie helper for Next.js middleware (edge runtime)
│   │   ├── sanitize.ts                    ← DOMPurify HTML sanitization for BlogPreview
│   │   └── stripe.ts                      ← Stripe.js loadStripe() helper
│   ├── stores/
│   │   ├── useClientStore.ts              ← Zustand: activeClientId
│   │   └── useUIStore.ts                  ← Zustand: modals, toasts, sidebar
│   └── types/
│       ├── api.ts                         ← Base API response types, error shape
│       ├── campaign.ts                    ← Campaign, Job, CampaignStatus, JobStatus
│       ├── client.ts                      ← Client, BrandVoiceProfile
│       └── platform.ts                    ← PlatformConnection, PlatformType enum
│
└── backend/                               ← FastAPI + Python 3.12
    ├── main.py                            ← App factory, router registration, CORS, lifespan
    ├── requirements.txt
    ├── .env                               ← gitignored
    ├── .env.example
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py                         ← SQLModel metadata, reads DATABASE_URL
    │   └── versions/
    │       └── 001_initial_schema.py      ← All 7 tables
    ├── app/
    │   ├── routers/
    │   │   ├── auth.py                    ← POST /login, /register, /google, /logout, /verify-email
    │   │   ├── clients.py                 ← GET/POST/PATCH/DELETE /clients, POST /clients/{id}/ingest
    │   │   ├── campaigns.py               ← POST /campaigns, GET /campaigns/{id},
    │   │   │                              ←   POST /campaigns/{id}/approve|reject|regenerate
    │   │   ├── publishing.py              ← POST /clients/{id}/connections,
    │   │   │                              ←   POST /campaigns/{id}/publish|publish/schedule|publish/retry
    │   │   ├── images.py                  ← POST /campaigns/{id}/image/regenerate
    │   │   ├── jobs.py                    ← GET /jobs/{id} (polling endpoint)
    │   │   └── webhooks.py                ← POST /api/v1/webhooks/stripe
    │   ├── services/
    │   │   ├── auth.py                    ← JWT, bcrypt, Google exchange, email verification
    │   │   ├── clients.py                 ← Client CRUD, Brand Voice Profile merge
    │   │   ├── campaigns.py               ← Lifecycle, state machine (atomic transitions)
    │   │   ├── generation.py              ← Gemini pipeline (blog 512t + social 0t + voice check 256t)
    │   │   ├── image.py                   ← Replicate FLUX.1 [pro] + Supabase Storage upload
    │   │   ├── ingestion.py               ← httpx scraping + BeautifulSoup + Gemini (1024t)
    │   │   ├── publishing.py              ← Dispatch to platforms, stagger calls, decrypt credentials
    │   │   ├── subscription.py            ← Plan tier limit checks before every create/generate
    │   │   └── email.py                   ← Transactional email (provider TBD)
    │   ├── workers/
    │   │   ├── generate.py                ← BackgroundTask: run generation, update job to terminal state
    │   │   ├── publish.py                 ← BackgroundTask: run publish dispatcher, update job per platform
    │   │   └── ingest.py                  ← BackgroundTask: run ingestion, update client Brand Voice Profile
    │   ├── scheduler/
    │   │   └── scheduler.py               ← APScheduler AsyncIOScheduler, SQLAlchemyJobStore -> Supabase
    │   ├── db/
    │   │   ├── connection.py              ← create_engine, Session factory, get_session dependency
    │   │   └── repositories/
    │   │       ├── users.py
    │   │       ├── subscriptions.py       ← Usage counter increments
    │   │       ├── clients.py
    │   │       ├── platform_connections.py ← Stores encrypted credentials
    │   │       ├── campaigns.py           ← Status transition queries
    │   │       ├── jobs.py                ← Create/update, query pending scheduled jobs
    │   │       └── generation_logs.py     ← Append-only cost log
    │   ├── models/                        ← SQLModel table definitions (DB schema source of truth)
    │   │   ├── user.py                    ← id, email, hashed_password, google_sub, stripe_customer_id, verified
    │   │   ├── subscription.py            ← user_id, stripe_sub_id, plan_tier, status, usage counters, cycle dates
    │   │   ├── client.py                  ← user_id, name, website_url, brand_voice_profile (JSON)
    │   │   ├── platform_connection.py     ← client_id, platform, encrypted_credentials
    │   │   ├── campaign.py                ← client_id, brain_dump, blog_html, x_post, linkedin_post,
    │   │   │                              ←   image_url, status, voice_score (JSON), rejection_reason, scheduled_at
    │   │   ├── job.py                     ← campaign_id, job_type, status, scheduled_at, attempt_count, error_details
    │   │   └── generation_log.py          ← user_id, campaign_id, gemini_tokens, replicate_count
    │   ├── schemas/                       ← Pydantic request/response models (not table models)
    │   │   ├── auth.py                    ← LoginRequest, RegisterRequest, GoogleAuthRequest, TokenResponse
    │   │   ├── clients.py                 ← ClientCreate, ClientUpdate, ClientResponse
    │   │   ├── campaigns.py               ← CampaignCreate, CampaignResponse, ApproveRequest, RejectRequest
    │   │   ├── publishing.py              ← PlatformConnectionCreate, PublishRequest, ScheduleRequest
    │   │   └── jobs.py                    ← JobResponse
    │   ├── core/
    │   │   ├── config.py                  ← Pydantic BaseSettings: all env vars with types
    │   │   ├── security.py                ← AES-256-GCM encrypt/decrypt, JWT sign/verify, bcrypt
    │   │   ├── rate_limit.py              ← slowapi Limiter, 10/minute/user
    │   │   ├── dependencies.py            ← get_current_user, get_session, get_*_service
    │   │   └── exceptions.py              ← Custom exception classes + HTTP exception handlers
    │   └── integrations/
    │       ├── gemini.py                  ← generate_blog(), generate_social(), extract_voice(), check_fidelity()
    │       ├── replicate.py               ← generate_image() -> returns Supabase Storage URL
    │       ├── stripe_client.py           ← handle_webhook_event(), create_portal_session()
    │       ├── supabase_storage.py        ← upload_file(), delete_file(), get_public_url()
    │       ├── wordpress.py               ← create_draft() -> upload_image() -> publish()
    │       ├── webflow.py                 ← create_item() -> publish_item()
    │       ├── twitter.py                 ← OAuth PKCE helpers + create_tweet()
    │       └── linkedin.py                ← OAuth helpers + create_ugc_post()
    └── tests/
        ├── conftest.py                    ← pytest fixtures: test DB session, mock external APIs
        ├── routers/
        │   ├── test_auth.py
        │   ├── test_clients.py
        │   ├── test_campaigns.py
        │   └── test_publishing.py
        ├── services/
        │   ├── test_generation.py
        │   ├── test_ingestion.py
        │   └── test_publishing.py
        └── integrations/
            └── test_wordpress.py
```

### Architectural Boundaries

**API Boundaries:**

| Boundary | Handler | Notes |
|---|---|---|
| All app API calls | FastAPI `/api/v1/*` | Auth via JWT cookie |
| Google OAuth callback | Next.js `/api/auth/google/callback` | Server-side code exchange, then calls FastAPI |
| Stripe webhooks | Next.js `/api/webhooks/stripe` | Validates signature, forwards to FastAPI |
| Job status polling | FastAPI `GET /api/v1/jobs/{id}` | React Query polls every 2s while pending |
| Supabase Postgres | Backend only | Frontend never queries DB directly |
| Supabase Storage | Backend only | Frontend consumes CDN public URLs returned by backend |

**Hard Service Boundaries:**
- `services/publishing.py` is the ONLY place that calls `core/security.py:decrypt_credential()`
- `services/generation.py` is the ONLY place that calls `integrations/gemini.py`
- `services/image.py` is the ONLY place that calls `integrations/replicate.py`
- `services/subscription.py` must be called by ALL routers before any create/generate action

**Frontend Component Boundaries:**
- Server Components: read-only initial data (dashboard shell, campaign list first render)
- Client Components (`"use client"`): all interactivity, polling, mutations, editors
- `(auth)/` routes: minimal providers (no Zustand, no React Query)
- `(app)/` routes: full provider stack via `(app)/layout.tsx`

### Requirements to Structure Mapping

| FR Group | Frontend | Backend |
|---|---|---|
| FR-1-2: Auth | `(auth)/`, `middleware.ts`, `api/auth/` | `routers/auth.py`, `services/auth.py` |
| FR-3: Subscriptions | `settings/page.tsx` | `routers/webhooks.py`, `services/subscription.py` |
| FR-4-7: Clients | `clients/`, `components/clients/` | `routers/clients.py`, `services/clients.py` |
| FR-8-11: Ingestion | `components/clients/BrandVoiceProfile.tsx` | `services/ingestion.py`, `workers/ingest.py` |
| FR-12: Brain Dump | `campaigns/new/`, `BrainDumpInput.tsx` | `routers/campaigns.py` |
| FR-13-15: Generation | `GenerationStatus.tsx`, `hooks/useJobStatus.ts` | `services/generation.py`, `workers/generate.py`, `integrations/gemini.py` |
| FR-16-17: Image | `ImagePreview.tsx` | `services/image.py`, `integrations/replicate.py`, `integrations/supabase_storage.py` |
| FR-18-21: Approval | `campaigns/[id]/`, `ApprovalGate.tsx`, `BlogEditor.tsx` | `routers/campaigns.py`, `services/campaigns.py` |
| FR-22-25: Publishing | `clients/[id]/connections/`, `components/publishing/` | `routers/publishing.py`, `services/publishing.py`, `workers/publish.py`, `integrations/*.py` |
| FR-24: Scheduling | `SchedulePicker.tsx` | `scheduler/scheduler.py`, `repositories/jobs.py` |
| FR-26-27: Dashboard | `dashboard/page.tsx`, `CampaignList.tsx`, `ContentCalendar.tsx` | `routers/campaigns.py` list endpoint |
| FR-28: Trial | `TrialBanner.tsx` | `services/subscription.py`, `repositories/subscriptions.py` |

### Data Flow

**Campaign Generation Flow:**
```
Browser -> POST /api/v1/campaigns
        <- 202 {campaign_id, job_id}

Browser -> GET /api/v1/jobs/{id} [polls every 2s]
        <- {status: "in_progress"}
        [BackgroundTask running: generation.py -> gemini.py -> replicate.py -> supabase_storage.py]
        <- {status: "complete"}  [polling stops, React Query invalidates campaign query]
```

**Credential Flow:**
```
Connect:  User input -> Router -> encrypt_credential() -> Repository -> Supabase (encrypted TEXT)
Publish:  Repository -> Supabase -> encrypted TEXT -> decrypt_credential() [services/publishing.py only]
          -> Platform integration -> External API
          [decrypted value never leaves services/publishing.py function scope]
```

**Scheduled Publish Flow:**
```
User sets schedule -> POST /campaigns/{id}/publish/schedule
                   -> Job record written (status: scheduled, scheduled_at: T)
                   -> APScheduler registers job from DB on startup/event
                   -> At T: BackgroundTask fires publish worker
                   -> Job record updated to terminal state
```

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:** All technology choices are compatible.
- Next.js 16 + FastAPI split is driven by Vercel's serverless timeout constraint -- this is the correct resolution.
- SQLModel + Alembic: SQLModel uses SQLAlchemy under the hood; Alembic integrates natively.
- APScheduler SQLAlchemy job store + Supabase Postgres: standard supported configuration.
- Zustand + React Query: no conflicts -- distinct concerns (UI state vs server state).
- Tiptap in Next.js App Router: works as a Client Component with `"use client"`.
- Custom JWT + Next.js middleware: compatible, with one clarification noted in gaps below.

**Pattern Consistency:** All naming conventions, routing patterns, and structural rules are consistent across frontend and backend. The snake_case-through contract (DB -> API -> TypeScript types) is coherent end-to-end.

**Structure Alignment:** Project structure maps cleanly to all patterns and decisions. All 28 FRs have a defined structural home. Service boundaries are clearly drawn and non-overlapping.

---

### Requirements Coverage Validation

**Functional Requirements (28/28 covered):**
All FR groups (Auth, Client Management, Brand Ingestion, Brain Dump, Generation, Image, Approval Gate, Publishing, Dashboard, Trial) are mapped to specific files in both `frontend/` and `backend/`. See Requirements to Structure Mapping table in §Project Structure.

**Non-Functional Requirements:**
- Performance: Gemini thinking budgets tuned per task (0/256/512/1024); 202 Accepted + polling pattern prevents frontend blocking; generation target 90s / NFR ceiling 120s at 95th percentile.
- Security: AES-256-GCM credentials, JWT httpOnly cookie, DOMPurify HTML sanitization, CORS with credentials, SQLModel parameterized queries, SameSite=lax CSRF mitigation, OAuth scopes minimized.
- Availability: 99.5% target; Droplet SPOF explicitly accepted for v1 (documented in PRD §10).
- Scalability: Supabase removes DB bottleneck; Droplet scaling path documented ($6 -> $12 -> container orchestration).
- Job Durability: All async tasks (generation, publish, schedule, retry) backed by persistent job records.
- Observability: Sentry in both apps; structured JSON logging in FastAPI; Supabase Dashboard for DB/Storage metrics.

---

### Gap Analysis Results

**Pre-Implementation Actions (must resolve before first story):**

1. **JWT library for Next.js middleware (edge runtime)** -- The edge runtime in `middleware.ts` and Next.js API routes cannot use Node.js-only JWT libraries. Must use `jose` (npm) for JWT verification at the edge. Add `jose` to frontend dependencies. This does not change the architecture -- it specifies the implementation library.

2. **Transactional email provider** -- Required for FR-1 email verification (A-3). Recommendation: Resend. One env var (`RESEND_API_KEY`), one call in `services/email.py`. Must be decided and configured before the auth implementation story.

**Important Gaps (resolve before the affected story):**

3. **X OAuth PKCE state parameter storage** -- PKCE requires a `state` value stored temporarily between the OAuth redirect and callback to prevent CSRF. Options: httpOnly session cookie (simplest) or a short-lived `oauth_states` table in Postgres. Recommendation: short-lived cookie (`oauth_state`, SameSite=Lax, 10-minute expiry) set in Next.js before the redirect, verified in the callback route.

4. **Trial expiration deletion scheduling (FR-28)** -- The APScheduler job store handles scheduled publishes, but FR-28 requires checking for expired trials and scheduling account deletion after 30+7 days. Add a daily recurring APScheduler job (`subscription_cleanup`) in `scheduler/scheduler.py` that queries `subscriptions` for expired trials and enqueues deletion warnings/actions.

**Minor Gaps (can be resolved during story implementation):**

5. **Image regeneration count tracking (FR-17)** -- The 3-regeneration cap per Campaign needs an `image_regen_count: int = Field(default=0)` column on the `Campaign` model. Add this to the initial Alembic migration.

---

### Validation Issues Addressed

- **JWT edge runtime library:** resolved by specifying `jose` (npm) as the frontend JWT library for middleware and API route usage. No structural change required.
- **PKCE state storage:** resolved by recommending a short-lived httpOnly cookie set before OAuth redirect. No new table required.
- **Trial deletion scheduling:** resolved by adding `subscription_cleanup` as a named APScheduler recurring job. No new infrastructure required.
- **Image regen count:** resolved by adding `image_regen_count` column to Campaign model. One-line change to `models/campaign.py` and initial migration.

---

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

---

### Architecture Readiness Assessment

**Overall Status: READY WITH MINOR GAPS**

All 16 checklist items pass. Two pre-implementation actions (JWT edge library, email provider) must be resolved before the auth story begins. All gaps are additive (a library choice, a column, a scheduled job) -- none require structural changes to the architecture.

**Confidence Level: High**

**Key Strengths:**
- Split architecture solves the core timeout constraint cleanly
- Job durability pattern is consistent and covers all async surfaces (generation, publish, schedule, retry, ingestion)
- Credential security model is layered correctly (encrypt at write, decrypt only at publish, key never in DB)
- snake_case-through contract eliminates an entire class of frontend/backend type mismatches
- FR coverage is complete and each requirement maps to a specific file

**Areas for Future Enhancement (post-v1):**
- HSM/KMS key management for credential encryption keys (currently env vars)
- Failover for FastAPI Droplet (currently single point of failure)
- Separate `partially_published` campaign status (currently merged with `failed`)
- Email notification system beyond verification (publishing failures, trial reminders are in-app only in v1)
- JWT refresh token mechanism (currently 7-day expiry requires re-login)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented -- do not introduce new libraries or patterns without updating this document
- Use implementation patterns consistently across all components
- Respect service boundaries: routers delegate, services orchestrate, repositories query, integrations call external APIs
- Create a `jobs` record before every BackgroundTask dispatch
- Refer to the Requirements to Structure Mapping table for any question about where code belongs

**Pre-Implementation Actions (in order):**
1. Decide transactional email provider (recommend Resend) -- add `RESEND_API_KEY` to `.env.example`
2. Add `jose` to frontend `package.json` for edge-runtime JWT verification in `middleware.ts`

**First Implementation Story:**
```bash
# Frontend init
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --import-alias "@/*" --use-npm

# Backend init
mkdir backend && cd backend && python3.12 -m venv .venv
```
Then: Supabase project creation + Alembic initial migration (all 7 tables + `image_regen_count` on campaigns).
