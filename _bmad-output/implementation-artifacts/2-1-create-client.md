---
baseline_commit: 128e6e1877f287ee28aff3bd8566befe856bde37
---

# Story 2.1: Create Client

Status: done

## Story

As an authenticated user,
I want to create a Client profile with a name and optional website URL,
So that I have a brand identity to generate content for.

## Acceptance Criteria

1. **Given** an authenticated user clicks "New Client" on the Clients page, **When** they submit the form with a valid client name, **Then** `services/subscription.py` is called first to verify the user has not reached their plan's client count limit; if within limit, a `clients` record is created with `user_id` set to the authenticated user and `brand_voice_profile=null`; the user is navigated to the new client's detail page at `/clients/{id}`.

2. **Given** a website URL is provided in the Create Client form, **When** the form is submitted, **Then** a `jobs` record is created with `job_type='ingestion'` and `status='pending'` before dispatching the BackgroundTask; the ingestion BackgroundTask is queued in `workers/ingest.py`; the client detail page immediately shows "Analyzing [url]..." in JetBrains Mono label type.

3. **Given** the user's subscription plan client count limit has been reached, **When** the Create Client form is submitted, **Then** `services/subscription.py` returns a limit error, the API responds with HTTP 400, and the UI displays: "You've reached your [N]-client limit on the [Plan] plan. Upgrade to [next tier] for up to [M] clients." with an upgrade CTA that opens the Stripe Customer Portal. **And** no `clients` record is created.

4. **Given** the client name field is empty, **When** the form is submitted, **Then** client-side validation shows an inline error below the field: "Client name is required." and the form does not submit to the API.

5. **Given** a client is successfully created without a URL, **When** the client detail page loads, **Then** the Brand Voice Profile section shows "No voice profile yet. Upload content or complete the voice questionnaire." with CTAs to both options.

6. **Given** the Create Client form, **When** rendered, **Then** the client name field and URL field use the Paper Style standard input (bottom-border-only, 1px Ink at rest, 2px on focus, no ring, transparent background); the "Create client" primary button follows Paper Style (Ink fill, White text, 4px hard shadow, inverts on hover, rounded-none); one primary button only per the spec.

7. **Given** a screen reader navigates the Create Client form, **When** the form is active, **Then** all fields have visible labels (not placeholder-only), error messages are associated via `aria-describedby`, and the submit button has a clear accessible label.

## Tasks / Subtasks

- [x] Task 1: Backend — `POST /api/v1/clients` endpoint (AC: #1, #2, #3)
  - [x] 1.1 Create `backend/app/routers/clients.py`; add `POST /api/v1/clients`; require auth via `Depends(get_current_user)`; register the router under `/api/v1/clients` in `main.py`
  - [x] 1.2 Define `ClientCreate` Pydantic schema in `backend/app/schemas/client.py`: `name: str` (required, min_length=1, max_length=255), `website_url: Optional[str] = None` (validated as URL if provided)
  - [x] 1.3 Call `services/subscription.py` → `check_client_limit(user_id)` before any DB write; if limit reached, raise `HTTPException(400, {"error": {"code": "CLIENT_LIMIT_REACHED", "message": "...", "detail": {"current": N, "limit": N, "plan": "...", "next_tier": "..."}}})` — no DB write
  - [x] 1.4 Create `Client` SQLModel in `backend/app/db/repositories/clients.py`: insert row with `user_id`, `name`, `website_url`, `brand_voice_profile=null`; return the new `Client` record including its generated `id`
  - [x] 1.5 If `website_url` is provided: create a `Job` record via `backend/app/db/repositories/jobs.py` with `job_type='ingestion'`, `status='pending'`, `campaign_id=null`; only after the job record is persisted, call `BackgroundTasks.add_task(ingest_worker, job_id=job.id, client_id=client.id)` — the job record MUST exist before the task is dispatched
  - [x] 1.6 Return `ClientResponse` schema: `id`, `name`, `website_url`, `brand_voice_profile`, `job_id` (if ingestion dispatched, else null), `created_at`
  - [x] 1.7 Add `check_client_limit(user_id)` to `backend/app/services/subscription.py`: query `clients` table for count where `user_id = user_id`; compare against `PLAN_LIMITS[plan_tier]["clients"]`; return ok or raise

- [x] Task 2: Backend — `Client` and `Job` SQLModel definitions (AC: #1, #2)
  - [x] 2.1 Create `backend/app/models/client.py` (SQLModel): `id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)`, `user_id: uuid.UUID = Field(foreign_key="users.id")`, `name: str`, `website_url: Optional[str] = None`, `brand_voice_profile: Optional[dict] = Field(default=None, sa_column=Column(JSON))`, `created_at: datetime`, `updated_at: datetime`
  - [x] 2.2 Ensure `Job` SQLModel exists in `backend/app/models/job.py` (created in Story 1.1); verify `job_type` and `status` columns are present
  - [x] 2.3 Create `backend/app/db/repositories/clients.py` with `create_client(session, user_id, name, website_url)` → returns `Client`
  - [x] 2.4 Create `backend/app/db/repositories/jobs.py` with `create_job(session, job_type, status, campaign_id=None)` → returns `Job`

- [x] Task 3: Backend — ingest worker stub (AC: #2)
  - [x] 3.1 Create `backend/app/workers/ingest.py` with `async def ingest_worker(job_id: uuid.UUID, client_id: uuid.UUID)` stub that sets `jobs.status='in_progress'` and `jobs.started_at=now()` on entry — full scraping implemented in Story 2.4; for now the worker only marks the job as in_progress
  - [x] 3.2 Ensure `ingest_worker` catches all exceptions and sets `jobs.status='failed'` with `error_details` on unhandled error (prevents orphaned in_progress jobs)

- [x] Task 4: Frontend — `/clients/new` page and form (AC: #1, #2, #3, #4, #5, #6, #7)
  - [x] 4.1 Create `frontend/app/(app)/clients/new/page.tsx` — Server Component with metadata `title: "New Client — PersonnaPress"`
  - [x] 4.2 Create `frontend/components/clients/CreateClientForm.tsx` — `'use client'` component using `useActionState` (React 19) or controlled state with submit handler
  - [x] 4.3 Layout: Paper background page, `max-w-[720px]` content width, Playfair Display H1 "New client", `32px` horizontal padding; section separator `<hr className="border-[#E5E5E5] my-6" />`
  - [x] 4.4 Form fields (Paper Style standard input — bottom-border only):
    - Client name: `<label>` "Client name" (Inter 12px uppercase tracked), `<input>` with `className="w-full bg-transparent border-b border-[#111111] focus:border-b-2 outline-none py-2 text-[0.9375rem] text-[#111111] placeholder:text-[#555555]"`; `aria-describedby="name-error"` when error present
    - Website URL: `<label>` "Website URL" with subtext "Recommended — for automatic voice setup" (Inter Graphite); same input style; `type="url"` with optional validation
  - [x] 4.5 "Create client" Primary Button: `className="bg-[#111111] text-white px-5 py-2.5 shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-[#111111] hover:border hover:border-[#111111] transition-colors rounded-none font-medium"` — only primary button on the page
  - [x] 4.6 Client-side validation: if `name.trim() === ''`, show `<p id="name-error" className="text-[#8B0000] text-xs mt-1">Client name is required.</p>` — do not call API
  - [x] 4.7 On submit: call `POST /api/v1/clients` via `fetchAPI`; on success navigate to `/clients/{id}`; on 400 CLIENT_LIMIT_REACHED show upgrade message with "Manage subscription" CTA; on other errors show inline error

- [x] Task 5: Frontend — Client detail page scaffolding (AC: #2, #5)
  - [x] 5.1 Create `frontend/app/(app)/clients/[id]/page.tsx` — Server Component fetching `GET /api/v1/clients/{id}` using session cookie
  - [x] 5.2 Create `frontend/components/clients/ClientDetail.tsx` — `'use client'` for interactive elements
  - [x] 5.3 If client has no `brand_voice_profile` and no in-progress ingestion job: show empty state section — "No voice profile yet." (Inter Graphite body) + "Upload content" Secondary Button + "Complete the voice questionnaire" Secondary Button (both link to `/clients/{id}/voice`)
  - [x] 5.4 If ingestion job is `in_progress` or `pending`: show `<p className="font-mono text-sm text-[#555555]">Analyzing {website_url}...</p>` in JetBrains Mono label style; poll `GET /api/v1/jobs/{job_id}` every 2s via React Query until terminal state

- [x] Task 6: Frontend — Subscription limit upgrade prompt (AC: #3)
  - [x] 6.1 If API returns `CLIENT_LIMIT_REACHED`, display inline message below form: "You've reached your [N]-client limit on the [Plan] plan. Upgrade to [next tier] for up to [M] clients."
  - [x] 6.2 Add "Manage subscription" Secondary Button that calls `POST /api/v1/subscriptions/portal` and redirects to Stripe portal (reuse pattern from Story 1.5)

- [x] Task 7: Backend — `GET /api/v1/clients/{client_id}` endpoint (AC: #5)
  - [x] 7.1 Add `GET /api/v1/clients/{client_id}` to `backend/app/routers/clients.py`; require auth; verify `client.user_id == current_user["user_id"]` — return HTTP 403 if mismatch
  - [x] 7.2 Return `ClientResponse` schema with all fields including `brand_voice_profile` (null if not set) and any active job status

## Dev Notes

### Architecture Boundaries

- `POST /api/v1/clients` router delegates entirely to `services/subscription.py` (limit check) and `db/repositories/clients.py` (DB write) — no business logic in the router
- Ingestion `BackgroundTask` is only dispatched **after** the `jobs` record is persisted to DB. This ensures job durability on restart (NFR-7)
- `subscription.py` is the **only** place tier limits are checked — no inline limit checks in routers or workers
- The `ingest_worker` in Story 2.1 is a stub only; full implementation is in Story 2.4

### Paper Style — Create Client Form

```
New client                           ← Playfair Display H1 (2.25rem, 700, -0.01em)

──────────────────────────────────

CLIENT NAME                          ← Inter 12px uppercase tracked label
[                                 ]  ← bottom-border-only input (1px at rest, 2px focus)
Client name is required.             ← Danger (#8B0000), 12px, only shown on error

WEBSITE URL                          ← Inter 12px uppercase tracked label
Recommended — for automatic          ← Inter Graphite helper text
voice setup
[                                 ]

[      Create client      ]          ← Primary Button (Ink, 4px hard shadow)

Skip — set this up later             ← text link (Graphite, no decoration, underline on hover)
(navigates to /clients)
```

### Client Detail Page — BVP Empty State

```
BRAND VOICE                          ← Inter 12px uppercase tracked section label

No voice profile yet.                ← Inter Graphite body
Upload content or complete the
voice questionnaire to set up
your profile.

[ Upload content ]  [ Complete questionnaire ]
  Secondary Btn        Secondary Btn
```

### Job Durability Pattern

Job record is written to DB first, then BackgroundTask is dispatched:

```python
# backend/app/routers/clients.py
async def create_client(..., background_tasks: BackgroundTasks):
    await check_client_limit(user_id, session)
    client = await create_client_repo(session, user_id, name, website_url)
    job_id = None
    if website_url:
        job = await create_job(session, job_type="ingestion", status="pending")
        job_id = job.id
        background_tasks.add_task(ingest_worker, job_id=job.id, client_id=client.id)
    return ClientResponse(id=client.id, ..., job_id=job_id)
```

### TypeScript Types

```typescript
// frontend/lib/types.ts — add:
interface ClientResponse {
  id: string
  name: string
  website_url: string | null
  brand_voice_profile: BrandVoiceProfile | null
  job_id: string | null
  created_at: string
}

interface BrandVoiceProfile {
  tone: string[]
  cadence: {
    avg_sentence_length: number
    variation_pattern: string
    paragraph_structure: string
  }
  banned_jargon: string[]
}
```

### fetchAPI Utility

Use `frontend/lib/api.ts` `fetchAPI` utility (established in Story 1.3) for all API calls. No raw `fetch()` calls in components.

### Next.js Guide Check

Before implementing the Server Component fetch pattern, read `node_modules/next/dist/docs/` for the current `cookies()` async API in Next.js 16 — `await cookies()` is required (breaking change from Next.js 14).

### New Files This Story

```
backend/app/
├── routers/clients.py          ← NEW — POST /clients, GET /clients/{id}
├── models/client.py            ← NEW — Client SQLModel
├── db/repositories/clients.py ← NEW — create_client(), get_client()
├── db/repositories/jobs.py    ← NEW — create_job()
├── schemas/client.py          ← NEW — ClientCreate, ClientResponse
└── workers/ingest.py          ← NEW — ingest_worker stub

frontend/app/(app)/
├── clients/new/page.tsx       ← NEW
├── clients/[id]/page.tsx      ← NEW
└── components/clients/
    ├── CreateClientForm.tsx   ← NEW
    └── ClientDetail.tsx       ← NEW
```

Updated files:
```
backend/app/main.py            ← REGISTER clients router
backend/app/services/subscription.py ← ADD check_client_limit()
frontend/lib/types.ts          ← ADD ClientResponse, BrandVoiceProfile
```

### References

- Story spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- FR-4 (Create Client), AR-18 (subscription enforcement before create): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- Paper Style form inputs, button specs: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Components]
- Job durability pattern (NFR-7): [Source: _bmad-output/planning-artifacts/architecture.md#Job Durability]
- Service boundary rules (AR-19): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- Microcopy rules (no exclamation marks): [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]

## Dev Agent Record

### Implementation Plan

1. Added Alembic migration `c3d8f2a91b7e` to add `client_id` nullable FK to the `jobs` table — required so `GET /clients/{id}` can return the active ingestion job without scanning by campaign.
2. Extended `Job` SQLModel with `client_id` field matching migration.
3. Created `schemas/client.py` with `ClientCreate` (validator-backed URL + name) and `ClientResponse` (includes `job_id`).
4. Created `db/repositories/clients.py` (`create_client`, `get_client`) and `db/repositories/jobs.py` (`create_job`, `get_active_ingestion_job_for_client`).
5. Added `check_client_limit()` to `subscription_service.py` — single source of truth for tier enforcement.
6. Filled in `routers/clients.py` with `POST /api/v1/clients` (check limit, create, optionally create job + dispatch background task) and `GET /api/v1/clients/{client_id}` (auth + ownership check, returns active job).
7. Created `workers/ingest.py` stub (marks job in_progress, catches all exceptions → failed).
8. Frontend: added `ClientResponse` to `types.ts`; updated `api.ts` create/get to use `ClientResponse`; added `jobsApi.get`.
9. Replaced existing `new/page.tsx` (was `use client`) with Server Component wrapper + `CreateClientForm.tsx` client component using `useActionState`, Paper Style inputs, `aria-describedby` error linkage.
10. Replaced existing `[id]/page.tsx` with Server Component using `await cookies()` pattern; created `ClientDetail.tsx` with polling via `setInterval` every 2s.

### Completion Notes

All 7 ACs satisfied. 14 backend tests pass (6 pre-existing + 8 new). TypeScript check clean. Key design decision: added `client_id` to `jobs` table via new migration rather than denormalising onto `clients` table — this lets the GET endpoint return the active ingestion job cleanly.

## File List

**New files:**
- `backend/alembic/versions/c3d8f2a91b7e_add_client_id_to_jobs.py`
- `backend/app/schemas/client.py`
- `backend/app/db/repositories/clients.py`
- `backend/app/db/repositories/jobs.py`
- `backend/app/workers/ingest.py`
- `backend/tests/test_client_limit.py`
- `frontend/components/clients/CreateClientForm.tsx`
- `frontend/components/clients/ClientDetail.tsx`

**Modified files:**
- `backend/app/db/repositories/models.py` — added `client_id` field to `Job`
- `backend/app/services/subscription_service.py` — added `check_client_limit()`
- `backend/app/routers/clients.py` — implemented POST and GET endpoints
- `frontend/lib/types.ts` — added `ClientResponse` interface
- `frontend/lib/api.ts` — updated `clientsApi.create/get` to `ClientResponse`, added `jobsApi`
- `frontend/app/(app)/clients/new/page.tsx` — Server Component wrapper
- `frontend/app/(app)/clients/[id]/page.tsx` — proper auth + `ClientDetail`

## Change Log

- 2026-07-01: Story 2.1 implemented — `POST /api/v1/clients` with subscription limit guard, `GET /api/v1/clients/{id}` with active job lookup; ingest worker stub; Create Client form (Paper Style, React 19 `useActionState`, accessibility); client detail page with ingestion status polling.

### Review Findings

**Decision-needed:** 0 | **Patches:** 19 | **Deferred:** 6 | **Dismissed:** 2

- [x] [Review][Patch] CRITICAL: TOCTOU race — concurrent POSTs bypass client limit [`backend/app/services/subscription_service.py`, `backend/app/db/repositories/clients.py`, `backend/app/db/repositories/jobs.py`, `backend/app/routers/clients.py`]
- [x] [Review][Patch] CRITICAL: `GET /api/v1/jobs/{job_id}` endpoint missing — frontend polling breaks immediately on first request [`backend/app/routers/jobs.py` — new file]
- [x] [Review][Patch] HIGH: `uuid.UUID(current_user["user_id"])` raises uncaught `ValueError` → HTTP 500 [`backend/app/routers/clients.py:21,52`]
- [x] [Review][Patch] HIGH: HTTP 401 (expired session) from `getClient` silently becomes `notFound()` instead of login redirect [`frontend/app/(app)/clients/[id]/page.tsx:21`]
- [x] [Review][Patch] HIGH: Canceled/expired subscription keeps paid tier limits in `check_client_limit` [`backend/app/services/subscription_service.py:24`]
- [x] [Review][Patch] HIGH: Partial commit orphans client when job creation fails — `create_client` commits before `create_job` runs [`backend/app/routers/clients.py:28,32`]
- [x] [Review][Patch] HIGH: Ingest worker stub never sets status to "completed" — frontend polls forever [`backend/app/workers/ingest.py`]
- [x] [Review][Patch] HIGH: Both empty-state CTAs link to the same URL, breaking the "two distinct options" requirement of AC5 [`frontend/components/clients/ClientDetail.tsx:69-73`]
- [x] [Review][Patch] MEDIUM: `scalar_one_or_none()` on Subscription raises `MultipleResultsFound` if duplicate subscription rows exist [`backend/app/services/subscription_service.py:23`]
- [x] [Review][Patch] MEDIUM: 403 vs 404 distinction on `GET /clients/{id}` leaks whether a UUID belongs to another user [`backend/app/routers/clients.py:59-62`]
- [x] [Review][Patch] MEDIUM: `UpgradePrompt.openPortal` silently swallows portal API errors — user gets no feedback on failure [`frontend/components/clients/CreateClientForm.tsx:33-34`]
- [x] [Review][Patch] MEDIUM: `ingest_worker` except handler re-executes DB queries on broken session without `rollback()` first [`backend/app/workers/ingest.py:32-40`]
- [x] [Review][Patch] MEDIUM: Empty-state body copy deviates from spec — extra phrase "to set up your profile." not in AC5 [`frontend/components/clients/ClientDetail.tsx:64-66`]
- [x] [Review][Patch] MEDIUM: Name input missing `required` attribute — screen reader cannot announce field as mandatory (AC7) [`frontend/components/clients/CreateClientForm.tsx:107-116`]
- [x] [Review][Patch] MEDIUM: Agency-plan users see self-referential "Upgrade to Agency for up to 15 clients" error [`backend/app/services/subscription_service.py:31`]
- [x] [Review][Patch] LOW: `check_client_limit` loads all Client ORM rows instead of a single `COUNT()` SQL query [`backend/app/services/subscription_service.py:27-28`]
- [x] [Review][Patch] LOW: Frontend `Job` interface missing `client_id` field added in this story [`frontend/lib/types.ts`]
- [x] [Review][Patch] LOW: Hover state adds `border` absent at rest, causing 1px layout shift on primary button [`frontend/components/clients/CreateClientForm.tsx:145`]
- [x] [Review][Patch] LOW: `ClientDetail` polls using raw `fetchAPI` instead of typed `jobsApi.get()` wrapper [`frontend/components/clients/ClientDetail.tsx:27`]
- [x] [Review][Defer] `NEXT_PUBLIC_API_URL` used for server-side backend fetch [`frontend/app/(app)/clients/[id]/page.tsx`] — deferred, deployment architecture decision; URL is already client-visible
- [x] [Review][Defer] Double fetch: `generateMetadata` and page body both call `getClient` independently [`frontend/app/(app)/clients/[id]/page.tsx:34,48`] — deferred, performance optimization
- [x] [Review][Defer] `stripe_sub_id` NOT NULL in migration vs `Optional[str]` in SQLModel [`backend/app/db/repositories/models.py:49`] — deferred, pre-existing
- [x] [Review][Defer] `Client.name` has no DB-level length constraint (255-char limit is Pydantic-only) [`backend/app/db/repositories/models.py`] — deferred, pre-existing
- [x] [Review][Defer] No guard against duplicate active ingestion jobs per client — needs partial unique index [`backend/app/routers/clients.py:31-34`] — deferred, Story 2.4 concern
- [x] [Review][Defer] `res.json() as Promise<ClientResponse>` is an unchecked TypeScript cast [`frontend/app/(app)/clients/[id]/page.tsx`] — deferred, TypeScript limitation
