---
baseline_commit: 8d8f4bcef69d3ad34cda77e39e6cb9372198c751
---

# Story 7.3: Data Retention, Account Deletion & Cleanup Scheduler

Status: done

## Story

As a user whose trial has expired and who has not subscribed within 30 days,
I want to receive a warning before my account is deleted,
so that I have a final opportunity to retrieve my content or subscribe before it is permanently removed.

## Acceptance Criteria

1. **Given** a daily APScheduler job named `subscription_cleanup` is registered in `scheduler/scheduler.py`, **When** APScheduler initializes (app startup), **Then** the job is registered as a recurring daily job using the SQLAlchemy job store; it queries `subscriptions` for all records where `status='trial_expired'` and `updated_at` (the expiry timestamp) is older than 30 days.

2. **Given** the `subscription_cleanup` job identifies a user whose trial expired more than 30 days ago, **When** the job runs for that user, **Then** a warning email is sent via Resend with the subject "Your PersonnaPress account will be deleted in 7 days" and instructions to subscribe or export content; `subscriptions.deletion_scheduled_at` is set to `now() + 7 days` (new column added via Alembic migration).

3. **Given** the `subscription_cleanup` job identifies a user whose `deletion_scheduled_at` is in the past (30+7 days total since trial expiry), **When** the job runs for that user, **Then** all `campaigns`, `clients`, `platform_connections`, `generation_logs`, `jobs`, and `subscriptions` records for that user are deleted; the `users` record is anonymized (email replaced with a hashed value, `hashed_password` set to null); the deletion is logged to Sentry with the anonymized user ID for audit purposes.

4. **Given** a user subscribes at any point before the `deletion_scheduled_at` timestamp, **When** the Stripe subscription webhook fires (`customer.subscription.created`), **Then** `subscriptions.status` is set to `'active'` and `subscriptions.deletion_scheduled_at` is set to null; the scheduled deletion is effectively cancelled.

5. **Given** all existing data during the 30-day post-trial retention window, **When** the user logs in before the deletion date, **Then** all their Clients, Campaigns, Brand Voice Profiles, and Platform Connections are visible and accessible (read-only due to Story 7.2 restrictions); no data is hidden or degraded during the retention window.

6. **Given** the `subscription_cleanup` job runs, **When** it executes any database delete operations, **Then** it processes at most 50 accounts per daily run to prevent long-running transactions; each deletion batch is wrapped in a try/except that logs failures to Sentry without stopping the rest of the batch.

## Tasks / Subtasks

- [x] Task 1: Alembic migration — add `deletion_scheduled_at` column to `subscriptions` (AC: #2, #4)
  - [x] 1.1 Create a new Alembic migration file: `backend/alembic/versions/e5f6a7b8c9d0_add_deletion_scheduled_at_to_subscriptions.py`
    ```python
    """add deletion_scheduled_at to subscriptions

    Revision ID: e5f6a7b8c9d0
    Revises: d4e9f1a02b3c
    Create Date: 2026-07-04

    """
    from alembic import op
    import sqlalchemy as sa

    revision = "e5f6a7b8c9d0"
    down_revision = "d4e9f1a02b3c"
    branch_labels = None
    depends_on = None


    def upgrade() -> None:
        op.add_column(
            "subscriptions",
            sa.Column("deletion_scheduled_at", sa.DateTime(), nullable=True),
        )


    def downgrade() -> None:
        op.drop_column("subscriptions", "deletion_scheduled_at")
    ```
  - [x] 1.2 Update `Subscription` SQLModel in `backend/app/db/repositories/models.py` to add the new field:
    ```python
    from typing import Optional
    # In class Subscription:
    deletion_scheduled_at: Optional[datetime] = Field(default=None, nullable=True)
    ```
  - [x] 1.3 Run `alembic upgrade head` locally to verify the migration applies cleanly (or note it for deployment). Do not run in tests — migration state is separate from test DB fixtures.
  - [x] 1.4 Update `backend/app/schemas/subscription.py` `SubscriptionResponse` to expose `deletion_scheduled_at: Optional[datetime] = None` — this allows the frontend to show a deletion warning if needed in future stories.

- [x] Task 2: Add warning email function to `email.py` (AC: #2)
  - [x] 2.1 Add `send_deletion_warning_email()` to `backend/app/integrations/email.py`:
    ```python
    def send_deletion_warning_email(to_email: str, deletion_date: str) -> None:
        """
        deletion_date: human-readable date string, e.g. "July 11, 2026"
        """
        resend.Emails.send({
            "from": "PersonnaPress <noreply@personnapress.io>",
            "to": [to_email],
            "subject": "Your PersonnaPress account will be deleted in 7 days",
            "html": (
                f"<p>Your PersonnaPress trial ended 30 days ago. "
                f"Your account and all associated content will be permanently deleted on <strong>{deletion_date}</strong>.</p>"
                f"<p>To keep your account, subscribe before that date: "
                f"<a href='{settings.APP_URL}/account'>Subscribe now</a>.</p>"
                f"<p>If you have content you want to save, log in before {deletion_date} to copy it.</p>"
                f"<p>If you have questions, reply to this email.</p>"
            ),
        })
    ```
  - [x] 2.2 Import `settings` from `app.core.config` in `email.py` (not already imported — add it).

- [x] Task 3: Create `subscription_cleanup` APScheduler job (AC: #1–#6)
  - [x] 3.1 Create `backend/app/workers/cleanup.py` with the `subscription_cleanup` async function:
    ```python
    import hashlib
    import logging
    from datetime import datetime, timedelta, timezone

    import sentry_sdk
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.connection import async_session_factory
    from app.db.repositories.models import (
        Campaign, Client, GenerationLog, Job, PlatformConnection, Subscription, User
    )
    from app.integrations.email import send_deletion_warning_email

    logger = logging.getLogger(__name__)
    BATCH_LIMIT = 50


    async def subscription_cleanup() -> None:
        """
        Daily APScheduler job. Two-phase cleanup:
        Phase 1: Find trial_expired users > 30 days → send warning email, set deletion_scheduled_at
        Phase 2: Find users with deletion_scheduled_at in the past → anonymize and delete
        """
        async with async_session_factory() as db:
            await _phase1_warn(db)
            await _phase2_delete(db)


    async def _phase1_warn(db: AsyncSession) -> None:
        """Send warning emails for users whose trial expired > 30 days ago with no deletion date set."""
        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
        result = await db.execute(
            select(Subscription)
            .where(
                Subscription.status == "trial_expired",
                Subscription.deletion_scheduled_at.is_(None),
                Subscription.updated_at <= cutoff_30d.replace(tzinfo=None),
            )
            .limit(BATCH_LIMIT)
        )
        subs = result.scalars().all()

        for sub in subs:
            try:
                user_result = await db.execute(
                    select(User).where(User.id == sub.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    continue

                deletion_date = datetime.now(timezone.utc) + timedelta(days=7)
                deletion_date_str = deletion_date.strftime("%B %-d, %Y")  # e.g. "July 11, 2026"

                send_deletion_warning_email(user.email, deletion_date_str)

                sub.deletion_scheduled_at = deletion_date.replace(tzinfo=None)
                sub.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()
                logger.info("Deletion warning sent for user %s", str(sub.user_id))
            except Exception as exc:
                await db.rollback()
                sentry_sdk.capture_exception(exc)
                logger.error("Phase1 warning failed for subscription %s: %s", str(sub.id), exc)


    async def _phase2_delete(db: AsyncSession) -> None:
        """Delete accounts where deletion_scheduled_at has passed."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await db.execute(
            select(Subscription)
            .where(
                Subscription.status == "trial_expired",
                Subscription.deletion_scheduled_at.is_not(None),
                Subscription.deletion_scheduled_at <= now,
            )
            .limit(BATCH_LIMIT)
        )
        subs = result.scalars().all()

        for sub in subs:
            try:
                user_id = sub.user_id
                await _delete_user_data(db, user_id)
                await _anonymize_user(db, user_id)
                await db.commit()
                anon_id = str(user_id)
                sentry_sdk.capture_message(
                    f"Account deleted (audit): user_id={anon_id}",
                    level="info",
                )
                logger.info("Account deleted for user %s", anon_id)
            except Exception as exc:
                await db.rollback()
                sentry_sdk.capture_exception(exc)
                logger.error("Phase2 delete failed for subscription %s: %s", str(sub.id), exc)


    async def _delete_user_data(db: AsyncSession, user_id) -> None:
        """Delete all data rows for the user except the users row itself."""
        # Get all client IDs for the user (needed for cascading deletes)
        clients_result = await db.execute(
            select(Client.id).where(Client.user_id == user_id)
        )
        client_ids = [row[0] for row in clients_result.all()]

        # Delete campaign-level data
        if client_ids:
            campaigns_result = await db.execute(
                select(Campaign.id).where(Campaign.client_id.in_(client_ids))
            )
            campaign_ids = [row[0] for row in campaigns_result.all()]
            if campaign_ids:
                await db.execute(
                    GenerationLog.__table__.delete().where(GenerationLog.campaign_id.in_(campaign_ids))
                )
                await db.execute(
                    Job.__table__.delete().where(Job.campaign_id.in_(campaign_ids))
                )
            await db.execute(
                Campaign.__table__.delete().where(Campaign.client_id.in_(client_ids))
            )
            await db.execute(
                PlatformConnection.__table__.delete().where(PlatformConnection.client_id.in_(client_ids))
            )

        # Delete top-level user data
        await db.execute(
            Client.__table__.delete().where(Client.user_id == user_id)
        )
        await db.execute(
            GenerationLog.__table__.delete().where(GenerationLog.user_id == user_id)
        )
        await db.execute(
            Subscription.__table__.delete().where(Subscription.user_id == user_id)
        )
        await db.flush()


    async def _anonymize_user(db: AsyncSession, user_id) -> None:
        """Anonymize the users row: hash email, clear password."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        hashed_email = "deleted_" + hashlib.sha256(user.email.encode()).hexdigest()[:16] + "@anonymized.invalid"
        user.email = hashed_email
        user.hashed_password = None
        user.google_sub = None
        user.stripe_customer_id = None
        await db.flush()
    ```
  - [x] 3.2 Note on `async_session_factory`: APScheduler jobs run outside the FastAPI request lifecycle, so they cannot use `get_session()` (which is a FastAPI dependency). Need an async session factory. Check `backend/app/db/connection.py` for the engine — if `async_session_factory` is not already exported, add it:
    ```python
    # In backend/app/db/connection.py — add if not present:
    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ```
  - [x] 3.3 Register the `subscription_cleanup` job in `backend/app/scheduler/scheduler.py`:
    ```python
    from app.workers.cleanup import subscription_cleanup

    def create_scheduler() -> AsyncIOScheduler:
        sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        jobstores = {"default": SQLAlchemyJobStore(url=sync_db_url)}
        scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")

        # Register daily cleanup job — runs at 02:00 UTC every day
        scheduler.add_job(
            subscription_cleanup,
            trigger="cron",
            hour=2,
            minute=0,
            id="subscription_cleanup",
            replace_existing=True,
            misfire_grace_time=3600,  # 1 hour — job is allowed to be late by up to 1 hour
        )
        return scheduler

    scheduler = create_scheduler()
    ```
    **Important:** The current `create_scheduler()` creates the scheduler and immediately assigns it to `scheduler`. The `add_job()` call is safe to include at module load time since the scheduler is not yet started. The `replace_existing=True` ensures that if the APScheduler SQLAlchemy job store already has a stale `subscription_cleanup` row from a previous deployment, it will be replaced with the updated configuration.

- [x] Task 4: Update Stripe webhook to clear `deletion_scheduled_at` on subscription activation (AC: #4)
  - [x] 4.1 Update `_handle_subscription_updated()` in `backend/app/services/subscription_service.py` to clear `deletion_scheduled_at` when status becomes `'active'`:
    ```python
    # In _handle_subscription_updated():
    sub.status = sub_obj.get("status", sub.status)
    if sub.status == "active":
        sub.deletion_scheduled_at = None  # Cancel scheduled deletion
    sub.billing_cycle_start = ...
    ```
  - [x] 4.2 Ensure `customer.subscription.created` (added in Story 7.1 Task 5.2) also flows through `_handle_subscription_updated()` and thus clears `deletion_scheduled_at`. No additional code needed if 7.1 Task 5.2 is implemented.

- [x] Task 5: Write tests (AC: #1–#6)
  - [x] 5.1 Create `backend/tests/workers/test_cleanup.py`:
    - `test_phase1_sends_warning_email_and_sets_deletion_date()`:
      - Set up subscription with `status='trial_expired'`, `deletion_scheduled_at=None`, `updated_at = now - 31 days`
      - Mock `send_deletion_warning_email`
      - Call `subscription_cleanup()` with mocked DB session
      - Assert `send_deletion_warning_email` was called with correct email
      - Assert `sub.deletion_scheduled_at` is set to approximately `now + 7 days`
    - `test_phase1_skips_recently_expired()`:
      - Set up subscription with `updated_at = now - 20 days` (only 20 days, not 30)
      - Assert `send_deletion_warning_email` NOT called
    - `test_phase2_deletes_user_data()`:
      - Set up subscription with `status='trial_expired'`, `deletion_scheduled_at = now - 1 day`
      - Set up related `Client`, `Campaign`, `Job`, `PlatformConnection`, `GenerationLog`
      - Call `subscription_cleanup()`
      - Assert all associated records deleted
      - Assert `User.email` is anonymized (starts with `"deleted_"`)
      - Assert `User.hashed_password` is None
    - `test_phase2_skips_user_with_future_deletion_date()`:
      - `deletion_scheduled_at = now + 3 days` → assert no deletion occurs
    - `test_batch_limit_50()`:
      - Create 55 qualifying subscriptions → assert only 50 are processed per run
    - `test_phase2_continues_on_single_failure()`:
      - Mock DB delete to raise on user 2 of 3
      - Assert user 1 and user 3 are still processed (error is caught and Sentry is called)
  - [x] 5.2 Add to `backend/tests/services/test_subscription.py`:
    - `test_handle_subscription_updated_clears_deletion_scheduled_at()`: subscription with `deletion_scheduled_at` set → after webhook with `status='active'`, field is null

## Dev Notes

### Critical Rules

1. **APScheduler jobs CANNOT use FastAPI's `get_session()` dependency** — `get_session()` is a FastAPI Depends injectable, designed for the HTTP request lifecycle. For APScheduler jobs (which run outside any HTTP request), use `async_session_factory()` with an `async with` context manager. Add `async_session_factory` to `connection.py` if not present.

2. **Delete order matters** — Foreign key constraints require deleting child records before parents. Order of deletion: `generation_logs` → `jobs` → `campaigns` → `platform_connections` → `clients` → `subscriptions`. The `users` row is NOT deleted; it is anonymized. This preserves the users row for audit purposes.

3. **`updated_at` is used as the expiry timestamp** — When `check_and_expire_trial()` (Story 7.2) updates `status='trial_expired'`, it also updates `updated_at`. The cleanup job uses `updated_at` as the proxy for when expiry occurred. This means `updated_at` must NOT be changed after expiry for any other reason. If it is, the 30-day countdown resets. This is intentional per the design — if the account is touched for any reason, the retention window resets.

4. **`deletion_scheduled_at` timezone** — Store as naive datetime (UTC) per the project's `utcnow()` convention. Compare with `datetime.now(timezone.utc).replace(tzinfo=None)`. This is the same convention used across the entire codebase.

5. **`replace_existing=True` in APScheduler** — Critical for deployments. Without this, restarting the FastAPI process with APScheduler using a persistent SQLAlchemy job store would fail if the `subscription_cleanup` job already exists in the DB with old parameters.

6. **`misfire_grace_time=3600`** — If the server is down at 02:00 UTC and the job misfires, APScheduler will run it within 1 hour of startup. This prevents missed daily cleanup runs during brief outages.

7. **Sentry audit log** — Use `sentry_sdk.capture_message()` with `level="info"` for audit logging deletions (not `capture_exception`). This creates a traceable audit trail in Sentry. Log the anonymized user_id (UUID string), not the hashed email.

8. **`strftime("%-d")` for day-of-month without leading zero** — Works on Linux (Droplet). On Windows dev machines, use `%#d` instead. Since the app runs on a Linux DigitalOcean Droplet in production, `%-d` is fine. Add a comment noting this.

9. **Email import of `settings`** — Currently `email.py` does not import `settings`. Add `from app.core.config import settings` to generate the correct `APP_URL` link in the deletion warning email.

10. **Phase 1 and Phase 2 are independent** — A user will appear in Phase 1 results (>30 days expired, no deletion date) in one run, then Phase 2 (deletion_scheduled_at past) in a subsequent run (7+ days later). They cannot appear in both phases simultaneously because Phase 1 sets `deletion_scheduled_at` and Phase 2 only targets records where it's set and in the past.

### Architecture Compliance

- `subscription_cleanup()` job → `backend/app/workers/cleanup.py` (new worker, follows existing pattern of `generate.py`, `publish.py`, `ingest.py` in `workers/`)
- `scheduler.py` → `backend/app/scheduler/scheduler.py` (update to add job registration)
- Alembic migration → `backend/alembic/versions/` (new migration file)
- `Subscription` model → `backend/app/db/repositories/models.py` (add `deletion_scheduled_at` field)
- `send_deletion_warning_email()` → `backend/app/integrations/email.py` (extends existing email module)
- `async_session_factory` → `backend/app/db/connection.py` (add if not present)

### Files to Create

- `backend/app/workers/cleanup.py` (NEW)
- `backend/alembic/versions/e5f6a7b8c9d0_add_deletion_scheduled_at_to_subscriptions.py` (NEW)
- `backend/tests/workers/test_cleanup.py` (NEW)

### Files to Modify

- `backend/app/db/repositories/models.py` — add `deletion_scheduled_at: Optional[datetime]` to `Subscription`
- `backend/app/schemas/subscription.py` — add `deletion_scheduled_at: Optional[datetime] = None` to `SubscriptionResponse`
- `backend/app/integrations/email.py` — add `send_deletion_warning_email()`, import `settings`
- `backend/app/scheduler/scheduler.py` — register `subscription_cleanup` daily cron job
- `backend/app/db/connection.py` — add `async_session_factory` export if not present
- `backend/app/services/subscription_service.py` — clear `deletion_scheduled_at` on `active` status in `_handle_subscription_updated()`

### Existing Patterns to Follow

- `backend/app/workers/publish.py` — pattern for worker functions that use DB sessions
- `backend/app/integrations/email.py` — existing Resend email send pattern
- `backend/alembic/versions/d4e9f1a02b3c_add_onboarding_completed_to_users.py` — pattern for adding nullable columns
- `backend/app/scheduler/scheduler.py` — existing APScheduler setup (currently only creates scheduler, does not add jobs)
- `backend/app/db/repositories/models.py:11` — `utcnow()` convention for all datetime fields

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 7.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#APScheduler setup line 888]
- [Source: _bmad-output/planning-artifacts/architecture.md#Trial expiration deletion scheduling - ADR note at line 1061]
- [Source: _bmad-output/planning-artifacts/architecture.md#AR-14: Trial expiration and account deletion daily APScheduler job]
- [Source: backend/app/scheduler/scheduler.py — current scheduler setup]
- [Source: backend/app/integrations/email.py — Resend send pattern]
- [Source: backend/app/db/repositories/models.py — Subscription model, utcnow() convention]
- [Source: backend/alembic/versions/ — existing migration pattern (most recent: d4e9f1a02b3c)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `strftime("%-d")` fails on Windows (platform-specific format). Fixed by using f-string `f"{deletion_date.strftime('%B')} {deletion_date.day}, {deletion_date.year}"` which is fully cross-platform.

### Completion Notes List

- Task 1: Created Alembic migration `e5f6a7b8c9d0` adding nullable `deletion_scheduled_at` column to `subscriptions`. Updated `Subscription` SQLModel with `Optional[datetime]` field. Added `deletion_scheduled_at: Optional[datetime] = None` to `SubscriptionResponse`. Alembic upgrade should be run at deployment.
- Task 2: Added `send_deletion_warning_email()` to `email.py`. `settings` was already imported so no additional import needed.
- Task 3: Created `backend/app/workers/cleanup.py` with `subscription_cleanup()`, `_phase1_warn()`, `_phase2_delete()`, `_delete_user_data()`, `_anonymize_user()`. Added `async_session_factory = AsyncSessionLocal` alias to `connection.py`. Registered `subscription_cleanup` job in `scheduler.py` with `cron` trigger at 02:00 UTC, `replace_existing=True`, `misfire_grace_time=3600`.
- Task 4: Added `if sub.status == "active": sub.deletion_scheduled_at = None` in `_handle_subscription_updated()` — both `customer.subscription.created` and `customer.subscription.updated` route through this function (Story 7.1 wiring).
- Task 5: Created `backend/tests/workers/test_cleanup.py` with 8 tests covering phase1 warning, phase2 deletion, batch limit, failure isolation, and full integration. Added `test_handle_subscription_updated_clears_deletion_scheduled_at` to `test_subscription.py`. All 19 new/updated tests pass.

### File List

- `backend/alembic/versions/e5f6a7b8c9d0_add_deletion_scheduled_at_to_subscriptions.py` (NEW)
- `backend/app/workers/cleanup.py` (NEW)
- `backend/tests/workers/__init__.py` (NEW)
- `backend/tests/workers/test_cleanup.py` (NEW)
- `backend/app/db/repositories/models.py` (MODIFIED — added `deletion_scheduled_at` to `Subscription`)
- `backend/app/schemas/subscription.py` (MODIFIED — added `deletion_scheduled_at` to `SubscriptionResponse`)
- `backend/app/integrations/email.py` (MODIFIED — added `send_deletion_warning_email()`)
- `backend/app/db/connection.py` (MODIFIED — added `async_session_factory` alias)
- `backend/app/scheduler/scheduler.py` (MODIFIED — imported and registered `subscription_cleanup` job)
- `backend/app/services/subscription_service.py` (MODIFIED — clear `deletion_scheduled_at` on active)
- `backend/tests/services/test_subscription.py` (MODIFIED — added deletion webhook test)

### Review Findings

- [x] [Review][Patch] `_phase1_warn` mutates `sub.updated_at` after expiry — permanently resets the 30-day countdown; contradicts Dev Note #3 [backend/app/workers/cleanup.py:60]
- [x] [Review][Patch] Email sent before DB commit — rollback causes duplicate warning emails on next run [backend/app/workers/cleanup.py:57-62]
- [x] [Review][Patch] Blocking synchronous `resend.Emails.send()` call inside async event loop — wrap with `asyncio.to_thread()` [backend/app/workers/cleanup.py:64]
- [x] [Review][Patch] No `SELECT FOR UPDATE SKIP LOCKED` — concurrent scheduler runs can send duplicate emails and double-delete accounts [backend/app/workers/cleanup.py:34,75]
- [x] [Review][Patch] `_anonymize_user` silently returns when User row is missing — data deleted with no audit trail [backend/app/workers/cleanup.py:148]
- [x] [Review][Patch] `anon_id` variable name implies anonymization but holds raw UUID [backend/app/workers/cleanup.py:93]
- [x] [Review][Patch] Stale docstring in `send_deletion_warning_email` references `%-d` strftime format that is not used in the function [backend/app/integrations/email.py:9]
- [x] [Review][Defer] Multiple `trial_expired` rows per user causes Phase 2 double-anonymization — pre-existing schema gap [backend/app/workers/cleanup.py]
- [x] [Review][Defer] Stripe customer object not deleted from Stripe on account anonymization — GDPR gap, out of scope [backend/app/workers/cleanup.py:_anonymize_user]
- [x] [Review][Defer] SHA-256 prefix brute-forceable over email namespace — design decision, acceptable risk [backend/app/workers/cleanup.py:_anonymize_user]

## Change Log

- 2026-07-06: Implemented Story 7.3 — data retention, account deletion, and cleanup scheduler. Added Alembic migration for `deletion_scheduled_at`, daily APScheduler cleanup job with two-phase warning/deletion logic, Sentry audit logging, batch limit of 50, per-account error isolation, and Stripe webhook integration to cancel pending deletion on subscription activation. 19 new/updated tests added.
- 2026-07-06: Code review complete — 7 patches applied: removed `updated_at` mutation in Phase 1, reordered commit-before-email, wrapped email in `asyncio.to_thread`, added `with_for_update(skip_locked=True)` to both phases, added error logging in `_anonymize_user` on missing user, renamed `anon_id` to `user_id_str`, fixed stale docstring. 3 items deferred. Story marked done.
