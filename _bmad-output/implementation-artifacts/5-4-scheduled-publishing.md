---
baseline_commit: 88b45a01f457f541838390bd5a952d26899cb81f
---

# Story 5.4: Scheduled Publishing

Status: done

## Story

As an authenticated user,
I want to set a future date and time for an approved Campaign to publish automatically,
So that my content goes live at the optimal time without me needing to be present.

## Acceptance Criteria

1. **Given** an approved Campaign in the Approval Gate with "approved, not yet published" state, **When** the user clicks the "Schedule" secondary button, **Then** a datetime picker appears inline below the action buttons; the picker shows combined date + time inputs (native `<input type="datetime-local">` or equivalent); the resolved account-level timezone is displayed next to the input: "Schedules in America/New_York" (defaulting to "UTC" if no timezone is configured on the account).

2. **Given** the user selects a future date and time and clicks "Confirm schedule," **When** `POST /api/v1/campaigns/{id}/publish/schedule` is called with the ISO 8601 scheduled datetime, **Then** a `jobs` record is created with `job_type='scheduled_publish'`, `status='scheduled'`, and `jobs.scheduled_at` set to the requested UTC time; APScheduler registers a one-off job from the database record; the Approval Gate footer shows "Scheduled — [Weekday], [Month] [Day], [Year], [Time] [Timezone]"; `campaigns.scheduled_at` is updated with the scheduled time.

3. **Given** APScheduler starts up (or restarts after a Droplet restart), **When** the `scheduler/scheduler.py` lifespan hook runs in FastAPI startup, **Then** APScheduler's `SQLAlchemyJobStore` reads from the `apscheduler_jobs` table in Supabase Postgres (the APScheduler native table, separate from our `jobs` table); all pending scheduled jobs pointing at `run_publish` are recovered automatically; no scheduled job is lost across a restart.

4. **Given** the scheduled time arrives, **When** APScheduler fires the job, **Then** the same `workers/publish.py:run_publish(job_id, campaign_id)` BackgroundTask function is called as for immediate publishing (Story 5.3); on success, `campaigns.status` transitions to `published`; on failure, `campaigns.status` is set to `failed` and an in-app notification is queued: the `jobs.error_details` captures the failure so the Retry Panel appears on next login.

5. **Given** a scheduled Campaign appears in the Approval Gate before the scheduled time, **When** the user views it, **Then** the footer shows the scheduled datetime with a "Cancel schedule" secondary link below the scheduled time; clicking "Cancel schedule" calls `DELETE /api/v1/campaigns/{id}/publish/schedule` which deletes the `jobs` row and removes the APScheduler job, returning `campaigns.status` to `approved` (clearing `campaigns.scheduled_at`); the footer transitions back to the "approved, not yet published" state.

6. **Given** the datetime picker is used, **When** the user selects a time in the past, **Then** the "Confirm schedule" button is disabled and an inline message reads "Scheduled time must be in the future." — the form does not submit.

7. **Given** the user enters a scheduled time, **When** the "Confirm schedule" button is enabled and clicked, **Then** the button shows an inline spinner and is disabled until the API responds; on success, the Approval Gate updates without page reload; on error, a toast shows the error message.

8. **Given** a Campaign is in "scheduled" state (status `approved`, `scheduled_at` set), **When** the Approval Gate loads, **Then** the footer correctly shows the "Scheduled" state with the cancel link — the state is determined by `campaign.status === 'approved' && campaign.scheduled_at !== null`.

## Tasks / Subtasks

- [x] Task 1: Create `backend/app/scheduler/scheduler.py` (AC: #3)
  - [x] 1.1 Create APScheduler setup with SQLAlchemy job store pointing at Supabase Postgres
  - [x] 1.2 Strip `+asyncpg` from DATABASE_URL for synchronous SQLAlchemy job store
  - [x] 1.3 Add APScheduler lifespan to FastAPI in `backend/app/main.py`
  - [x] 1.4 Merged into existing lifespan context manager (scheduler.start() / scheduler.shutdown())
  - [x] 1.5 APScheduler SQLAlchemyJobStore auto-recovers jobs from `apscheduler_jobs` on restart

- [x] Task 2: Add `POST /api/v1/campaigns/{id}/publish/schedule` endpoint (AC: #2)
  - [x] 2.1 Endpoint with ownership check, status guard, past-time guard, job creation, APScheduler registration
  - [x] 2.2 DateTrigger used for one-shot scheduling

- [x] Task 3: Add `DELETE /api/v1/campaigns/{id}/publish/schedule` endpoint (AC: #5)
  - [x] 3.1 Endpoint finds scheduled job, removes from APScheduler (try/except), deletes job row, clears campaign.scheduled_at

- [x] Task 4: Update `backend/app/db/repositories/jobs.py` for scheduled publish (AC: #2, #5)
  - [x] 4.1 Added `get_scheduled_job()` to jobs.py
  - [x] 4.2 Added `update_campaign_scheduled_at()` to campaigns.py

- [x] Task 5: Implement Schedule Picker UI in Approval Gate (AC: #1, #6, #7, #8)
  - [x] 5.1 Added state: showSchedulePicker, scheduledAt, isScheduling
  - [x] 5.2 Schedule button toggles picker inline below action buttons
  - [x] 5.3 Inline datetime picker with Paper Style inputs
  - [x] 5.4 isPastTime computed from scheduledAt vs now
  - [x] 5.5 userTimezone from Intl.DateTimeFormat().resolvedOptions().timeZone
  - [x] 5.6 handleConfirmSchedule converts to UTC ISO 8601, calls campaignsApi.schedule, refreshes
  - [x] 5.7 Added campaignsApi.schedule and campaignsApi.cancelSchedule to api.ts

- [x] Task 6: Implement Scheduled state UI in Approval Gate footer (AC: #5, #8)
  - [x] 6.1 Scheduled state detected via campaign.scheduled_at != null in approval-panel.tsx
  - [x] 6.2 Scheduled footer shows formatted datetime with Cancel schedule button
  - [x] 6.3 handleCancelSchedule calls campaignsApi.cancelSchedule and refreshes
  - [x] 6.4 Campaign.scheduled_at already in frontend/lib/types.ts

- [x] Task 7: Backend tests (AC: #2, #3, #5, #6)
  - [x] 7.1 Created backend/tests/routers/test_schedule_publish.py with 5 tests (all pass)
  - [x] 7.2 All scheduler calls mocked with unittest.mock.patch

- [x] Task 8: Frontend tests (AC: #1, #6, #7, #8)
  - [x] 8.1 Added 8 new tests to frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx (all pass)

### Review Findings

- [x] [Review][Patch] P1 [CRITICAL] Race condition: DB committed before scheduler.add_job — if add_job raises, campaign is permanently stuck as "scheduled" with no job to fire it [backend/app/routers/publishing.py:383]
- [x] [Review][Patch] P2 [HIGH] except Exception: pass swallows all APScheduler errors in cancel endpoint — only JobLookupError should be silenced [backend/app/routers/publishing.py:425]
- [x] [Review][Patch] P3 [HIGH] run_publish never clears campaign.scheduled_at on completion — campaign stays in "Scheduled" UI state even after successful or failed publish [backend/app/workers/publish.py]
- [x] [Review][Patch] P4 [MEDIUM] handleCancelSchedule has no isCancelling guard — rapid double-click sends two concurrent DELETE requests [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- [x] [Review][Patch] P5 [MEDIUM] ScheduleRequest.scheduled_at accepts naive datetimes — add field_validator to reject timezone-naive input [backend/app/routers/publishing.py:329]
- [x] [Review][Patch] P6 [LOW] campaign.scheduled_at stored as naive UTC, serialized without Z suffix — browser parses it as local time, displaying wrong scheduled time to user [backend/app/routers/publishing.py / frontend]
- [x] [Review][Defer] D1 Concurrent schedule requests TOCTOU (two simultaneous POSTs both pass scheduled_at is None guard) — requires SELECT FOR UPDATE; deferred, pre-existing pattern
- [x] [Review][Defer] D2 Magic strings for job_type/status — pre-existing pattern in codebase; deferred, pre-existing

## Dev Notes

### APScheduler SQLAlchemy Job Store — Connection String Difference

APScheduler's `SQLAlchemyJobStore` uses synchronous SQLAlchemy, NOT async. The `DATABASE_URL` env var uses `postgresql+asyncpg://` for our async app. For APScheduler, strip `+asyncpg`:

```python
sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
jobstores = {"default": SQLAlchemyJobStore(url=sync_db_url)}
```

APScheduler creates its own table (`apscheduler_jobs`) automatically on `scheduler.start()`. This is a separate table from our custom `jobs` table — both live in Supabase Postgres.

### APScheduler vs. Our `jobs` Table

Two tracking systems coexist:

| System | Table | Purpose |
|---|---|---|
| APScheduler | `apscheduler_jobs` | Internal job registry — fires `run_publish` at the right time |
| Our tracking | `jobs` | Frontend-visible status, error details, attempt counts |

When APScheduler fires, it calls `run_publish(job_id, campaign_id)` where `job_id` is our `jobs` table ID. `run_publish` updates our `jobs` table and `campaigns` table.

When FastAPI restarts: APScheduler recovers from `apscheduler_jobs`. Our `jobs` table shows `status='scheduled'` — the frontend knows to wait.

### Jobs Repository — Scheduled Job Lookup

For the cancel endpoint, we query our `jobs` table to find the APScheduler job ID (we stored our `job.id` as the APScheduler job ID via `id=str(job.id)`) — then call `scheduler.remove_job(str(job.id))`.

### datetime-local Input and Timezone

The browser's `<input type="datetime-local">` shows local time (user's browser timezone). When submitted, we convert it to UTC ISO 8601 before sending to the API:

```typescript
const localDate = new Date(scheduledAt)  // scheduledAt is "2026-07-10T09:00"
const utcIso = localDate.toISOString()   // "2026-07-10T13:00:00.000Z" (if user is UTC-4)
```

The backend stores UTC in `jobs.scheduled_at` and `campaigns.scheduled_at`. The frontend displays back in the user's local timezone using `Intl.DateTimeFormat` with `timeZoneName: 'short'` to show the timezone abbreviation.

### EXPERIENCE.md Schedule Picker Spec

> "Schedule picker — Appears inline below Approve button after approval. Datetime picker. Shows resolved timezone next to the input: 'Schedules in America/New_York.' Confirm sets the scheduled time; Cancel discards without changing status."

The timezone display uses the browser's resolved timezone: `Intl.DateTimeFormat().resolvedOptions().timeZone`. This returns IANA timezone names like `"America/New_York"` or `"UTC"`.

### Approval Gate Footer — Priority Order

The Approval Gate footer shows different content based on state. Priority order for rendering:

1. `campaign.status === 'published'` → Published summary (Story 5.3)
2. `campaign.status === 'approved' && campaign.scheduled_at !== null` → Scheduled state (this story)
3. `campaign.status === 'approved' && campaign.scheduled_at === null` → "Publish now" + "Schedule" CTAs (Stories 4.4 + 5.3 + this story)
4. `campaign.status === 'pending_approval'` → Approve + Reject buttons (Story 4.4)
5. `campaign.status === 'rejected'` → "Regenerate from same Brain Dump" (Story 4.4)
6. `campaign.status === 'failed'` → Retry Panel (Story 5.5)

### Paper Style — Schedule Picker

Per DESIGN.md input spec:
- `datetime-local` input: `border-b border-ink focus:border-b-2 outline-none bg-transparent py-2 text-sm text-ink w-full`
- No border-box, no ring, transparent background
- "Schedules in [Timezone]" microcopy: `text-xs text-graphite`
- "Confirm schedule" = Primary Button when enabled; disabled state: `opacity-50 cursor-not-allowed`
- "Cancel" = Secondary Button (border, no fill)

Per UX-DR23: the Brain Dump submit uses `Cmd+Enter` — there is no analogous shortcut for schedule picker; simple button click is the only affordance.

### `scheduled_at` on Campaign Model

The `Campaign` model in `backend/app/db/repositories/models.py` already has `scheduled_at: Optional[datetime] = None` (confirmed from file read). The frontend TypeScript `Campaign` type in `frontend/lib/types.ts` needs to include `scheduled_at?: string | null`.

### Project Structure Notes

**New files:**
```
backend/app/scheduler/scheduler.py   ← APScheduler setup (directory already exists per architecture)
```

**Modified files:**
```
backend/app/main.py                              ← Add scheduler lifespan hooks
backend/app/routers/publishing.py                ← Add schedule + cancel endpoints
backend/app/db/repositories/jobs.py              ← Add get_scheduled_job()
backend/app/db/repositories/campaigns.py         ← Verify/add update for scheduled_at field
backend/tests/routers/test_publishing.py         ← Add schedule/cancel tests
frontend/lib/api.ts                              ← Add campaignsApi.schedule, cancelSchedule
frontend/lib/types.ts                            ← Add scheduled_at to Campaign type
frontend/app/(app)/campaigns/[id]/approval-panel.tsx      ← Add Schedule picker UI
frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx  ← Add scheduled state footer
```

### References

- Story 5.4 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 5.4]
- FR-24: Scheduled publishing — datetime picker, APScheduler, persistent jobs: [Source: _bmad-output/planning-artifacts/epics.md#FR-24]
- NFR-7: Job Durability — APScheduler + SQLAlchemy job store + Supabase: [Source: _bmad-output/planning-artifacts/epics.md#NFR-7]
- AR-3: APScheduler with SQLAlchemy job store: [Source: _bmad-output/planning-artifacts/epics.md#AR-3]
- UX-DR22: Approval Gate state machine — approved-not-published → schedule picker → Scheduled state: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR22]
- EXPERIENCE.md: Schedule picker behavior — inline, timezone display, Cancel discards: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Component Patterns]
- EXPERIENCE.md: Approval Gate: approved state — "Publish now" + "Schedule" CTAs: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#State Patterns]
- Architecture: APScheduler in scheduler/scheduler.py: [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- Architecture: schemas/publishing.py — ScheduleRequest: [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- Story 5.3 run_publish worker (reused by APScheduler): [Source: _bmad-output/implementation-artifacts/5-3-immediate-multi-platform-publishing.md#Task 3]
- Campaign model scheduled_at field: [Source: backend/app/db/repositories/models.py]
- Story 4.4 stub "Schedule" button to replace: [Source: _bmad-output/implementation-artifacts/4-4-approve-reject-campaign.md#Task 5.6]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Created `backend/app/scheduler/scheduler.py` with APScheduler AsyncIOScheduler + SQLAlchemyJobStore using sync DB URL (stripped `+asyncpg`). APScheduler v3.11.2 already installed.
- Wired scheduler.start()/shutdown() into the existing lifespan context manager in `main.py`.
- Added `POST /campaigns/{id}/publish/schedule` and `DELETE /campaigns/{id}/publish/schedule` endpoints to `publishing.py` with full ownership, status, and past-time guards.
- Added `get_scheduled_job()` to `jobs.py` and `update_campaign_scheduled_at()` to `campaigns.py`.
- Schedule picker is inline (toggle on Schedule button click) in `approval-panel.tsx`, not a modal. Scheduled state is detected via `campaign.scheduled_at != null` within the same component — no changes to `ApprovalGateClient.tsx` needed.
- `Campaign.scheduled_at` was already in `frontend/lib/types.ts` from prior work.
- 5 backend tests (all pass) + 8 new frontend tests (all pass). No regressions in router/services/integrations suites. Pre-existing voice profile / questionnaire test failures are unrelated (google-genai import issue).

### File List

- backend/app/scheduler/scheduler.py (created)
- backend/app/main.py (modified — scheduler import + lifespan hooks)
- backend/app/routers/publishing.py (modified — imports + schedule/cancel endpoints)
- backend/app/db/repositories/jobs.py (modified — get_scheduled_job)
- backend/app/db/repositories/campaigns.py (modified — update_campaign_scheduled_at)
- backend/tests/routers/test_schedule_publish.py (created)
- frontend/lib/api.ts (modified — campaignsApi.schedule, cancelSchedule)
- frontend/app/(app)/campaigns/[id]/approval-panel.tsx (modified — schedule picker UI + scheduled state footer)
- frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx (modified — 8 new schedule tests)

## Change Log

- 2026-07-03: Implemented Story 5.4 — APScheduler setup, schedule/cancel API endpoints, schedule picker UI, scheduled state footer, backend + frontend tests (Date: 2026-07-03)
