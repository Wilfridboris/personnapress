---
baseline_commit: 955e634
---

# Story 19.2: Transactional Email Rebrand + Trial Re-engagement Drip

Status: done

## Story

As Boris (founder),
I want all PersonnaPress transactional emails to use a minimal branded HTML template matching the Paper Style design,
and I want an automatic re-engagement email sent to trial users who haven't created a campaign after 3 days,
so that every email touchpoint feels professional and dormant trial users get a personal nudge to activate.

## Acceptance Criteria

1. **Given** a new user registers and triggers `send_verification_email`, **When** the email arrives in their inbox, **Then** it renders with the branded HTML template: PersonnaPress wordmark header, body content inside the template scaffold, Paper Style colors (`#F9F9F6` background, `#111111` text), and a footer with `"Questions? Email support@personnapress.com"` — in Gmail, Apple Mail, and Outlook.

2. **Given** a trial-expired user triggers `send_deletion_warning_email`, **When** the email arrives, **Then** it uses the same branded template AND has `reply_to: support@personnapress.com` set on the Resend send call — so "Reply" in Gmail routes to the support alias (not a no-reply address).

3. **Given** the new re-engagement email is sent, **When** the recipient reads it in their email client, **Then** they see: subject `"Quick check-in from Boris at PersonnaPress"`, a plain personal tone (no big heading — letter style), a CTA button `"Create your first campaign"` linking to `{APP_URL}/dashboard`, and `reply_to: support@personnapress.com`.

4. **Given** a user has `subscription.status = "trialing"`, their account (`users.created_at`) is more than 3 days old, they have zero campaigns across all their clients, and `subscriptions.reengagement_email_sent_at IS NULL`, **When** the `trial_reengagement_check` APScheduler job runs, **Then** `send_reengagement_email` is called for that user.

5. **Given** `send_reengagement_email` is called, **When** Resend accepts the send, **Then** `subscriptions.reengagement_email_sent_at` is set to the current UTC datetime and committed — so the job never sends a second email to the same user even on re-run.

6. **Given** `trial_reengagement_check` is registered in the scheduler, **When** the FastAPI server starts, **Then** the job runs daily at `09:00 UTC` with `replace_existing=True` and `misfire_grace_time=3600`, identical pattern to the existing `subscription_cleanup` job.

7. **Given** a user already has at least one campaign, **When** `trial_reengagement_check` runs, **Then** that user is skipped (the SQL query excludes users with any campaign record across any client).

8. **Given** `send_reengagement_email` fails (Resend throws), **When** the exception is caught, **Then** it is logged with `logger.error` and captured with `sentry_sdk.capture_exception` — `reengagement_email_sent_at` is NOT set on failure so the next daily run will retry.

9. **Given** the new `reengagement_email_sent_at` column is added, **When** the Alembic migration is generated via CLI and `alembic upgrade head` is run, **Then** the column exists on the `subscriptions` table as a nullable datetime. The `Subscription` SQLModel must also be updated to include this field.

10. **Given** the HTML email template function `build_email_html()` exists in `integrations/email.py`, **When** called with `heading`, `body_html`, and optional `cta_text`/`cta_url`, **Then** it returns a complete table-based HTML string that renders correctly across Gmail, Apple Mail, and Outlook — using only inline styles (no external CSS, no `<style>` block in `<head>` since Outlook strips it).

## Dev Notes

### User-facing Copy Rule

**No em-dashes (`—`) anywhere in user-facing text.** This applies to all email subject lines, email body copy, CTA button labels, and any string rendered to the user.

### Alembic Migration — Run Via CLI (project rule)

**Never hand-write a revision ID.** Generate with:

```bash
cd backend
alembic revision --autogenerate -m "add_reengagement_email_sent_at_to_subscriptions"
```

The generated file will be timestamped automatically (e.g., `20260726_1430_xxxx_add_reengagement_email_sent_at_to_subscriptions.py`). Then update the `Subscription` SQLModel to match.

### Subscription Model Update

Add to `backend/app/db/repositories/models.py` `Subscription` class:

```python
reengagement_email_sent_at: Optional[datetime] = Field(default=None, nullable=True)
```

Run migration BEFORE referencing this field anywhere.

### Shared HTML Email Template

All existing emails AND the new re-engagement email use `build_email_html()`. Replace the raw HTML strings in the existing `send_verification_email` and `send_deletion_warning_email` functions.

**Design rules (email-client safe):**
- Table-based layout — no `<div>` for structure
- All styles are inline (`style="..."`) — no `<style>` block (Outlook strips it)
- Max width 600px, centered via `margin: 0 auto`
- Fonts: `Georgia, 'Times New Roman', serif` for heading (Playfair fallback), `Arial, Helvetica, sans-serif` for body
- Hard-shadow CTA button: `box-shadow: 4px 4px 0px 0px #111111` (works in Gmail + Apple Mail; Outlook ignores box-shadow — the button is still functional)
- No external images in header (text wordmark only — better deliverability)
- `reply_to` set on EVERY email going forward

```python
# backend/app/integrations/email.py

def build_email_html(
    body_html: str,
    cta_text: str | None = None,
    cta_url: str | None = None,
    heading: str | None = None,
) -> str:
    """
    Wraps body_html in the PersonnaPress branded email template.
    body_html: pre-formatted HTML paragraphs (<p> tags).
    heading: optional bold section heading rendered above body_html.
    cta_text + cta_url: optional CTA button (both must be provided together).
    """
    cta_block = ""
    if cta_text and cta_url:
        cta_block = f"""
        <tr>
          <td style="padding: 24px 40px 0 40px;">
            <a href="{cta_url}"
               style="display: inline-block; background-color: #111111; color: #ffffff;
                      font-family: Arial, Helvetica, sans-serif; font-size: 14px;
                      font-weight: bold; text-decoration: none; padding: 12px 24px;
                      border: 1px solid #111111;
                      box-shadow: 4px 4px 0px 0px #111111;">
              {cta_text}
            </a>
          </td>
        </tr>"""

    heading_block = ""
    if heading:
        heading_block = f"""
        <tr>
          <td style="padding: 0 40px 16px 40px;">
            <h2 style="margin: 0; font-family: Georgia, 'Times New Roman', serif;
                       font-size: 22px; font-weight: bold; color: #111111;
                       line-height: 1.3;">
              {heading}
            </h2>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #F9F9F6;
             font-family: Arial, Helvetica, sans-serif;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0"
         width="100%" style="background-color: #F9F9F6;">
    <tr>
      <td align="center" style="padding: 40px 16px;">

        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               width="600" style="max-width: 600px; width: 100%;
                                  background-color: #F9F9F6;
                                  border: 1px solid #E5E5E5;">

          <!-- Header: Wordmark -->
          <tr>
            <td style="padding: 28px 40px; border-bottom: 1px solid #E5E5E5;">
              <span style="font-family: Georgia, 'Times New Roman', serif;
                           font-size: 20px; font-weight: bold; color: #111111;
                           letter-spacing: -0.01em;">
                PersonnaPress
              </span>
            </td>
          </tr>

          <!-- Body: heading (optional) -->
          {heading_block}

          <!-- Body: content -->
          <tr>
            <td style="padding: 32px 40px 0 40px;
                       font-family: Arial, Helvetica, sans-serif;
                       font-size: 16px; color: #111111; line-height: 1.6;">
              {body_html}
            </td>
          </tr>

          <!-- CTA button (optional) -->
          {cta_block}

          <!-- Divider -->
          <tr>
            <td style="padding: 32px 40px 0 40px;">
              <hr style="border: none; border-top: 1px solid #E5E5E5; margin: 0;">
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 40px 32px 40px;
                       font-family: Arial, Helvetica, sans-serif;
                       font-size: 12px; color: #555555; line-height: 1.5;">
              <p style="margin: 0 0 8px 0;">
                <strong style="font-family: Georgia, 'Times New Roman', serif;
                               color: #111111;">PersonnaPress</strong>
              </p>
              <p style="margin: 0 0 8px 0;">
                Questions? Email
                <a href="mailto:support@personnapress.com"
                   style="color: #111111; text-decoration: underline;">
                  support@personnapress.com
                </a>
              </p>
              <!-- Social links placeholder — will be expanded in a future story -->
              <p style="margin: 0; color: #555555;">
                Follow us:
                <a href="https://x.com/personnapress"
                   style="color: #555555; text-decoration: none; margin-right: 8px;">X / Twitter</a>
                <a href="https://linkedin.com/company/personnapress"
                   style="color: #555555; text-decoration: none;">LinkedIn</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
```

### Updated Email Functions

Replace the raw HTML in all three existing functions with `build_email_html()`. Add `reply_to` to every Resend send call:

```python
def send_verification_email(to_email: str, token: str) -> None:
    verification_url = f"{settings.APP_URL}/verify-email/confirm?token={token}"
    html = build_email_html(
        body_html=(
            f"<p>Click the link below to verify your email address. "
            f"This link expires in 24 hours.</p>"
        ),
        cta_text="Verify email address",
        cta_url=verification_url,
    )
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "reply_to": "support@personnapress.com",
        "subject": "Verify your email address",
        "html": html,
    })


def send_deletion_warning_email(to_email: str, deletion_date: str) -> None:
    html = build_email_html(
        body_html=(
            f"<p>Your PersonnaPress trial ended 30 days ago. "
            f"Your account and all associated content will be permanently deleted "
            f"on <strong>{deletion_date}</strong>.</p>"
            f"<p>To keep your account, subscribe before that date.</p>"
            f"<p>If you have content you want to save, log in before {deletion_date} to copy it.</p>"
        ),
        cta_text="Subscribe now",
        cta_url=f"{settings.APP_URL}/account",
    )
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "reply_to": "support@personnapress.com",
        "subject": "Your PersonnaPress account will be deleted in 7 days",
        "html": html,
    })


def send_reengagement_email(to_email: str, first_name: str | None) -> None:
    salutation = f"Hey {first_name}," if first_name else "Hey,"
    html = build_email_html(
        body_html=(
            f"<p>{salutation}</p>"
            f"<p>I noticed you signed up for PersonnaPress but haven't created your first campaign yet. "
            f"I'm Boris, the founder.</p>"
            f"<p>Getting started is simple: paste a few bullet points about what's on your mind this week, "
            f"and PersonnaPress writes a full blog post in your voice and publishes it wherever you need it.</p>"
            f"<p>If you hit a snag or have questions, just reply to this email. "
            f"It goes straight to my inbox.</p>"
        ),
        cta_text="Create your first campaign",
        cta_url=f"{settings.APP_URL}/dashboard",
    )
    resend.Emails.send({
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "reply_to": "support@personnapress.com",
        "subject": "Quick check-in from Boris at PersonnaPress",
        "html": html,
    })
```

> **Note on `first_name`:** The `users` table has no `first_name` column. The function accepts `None` and falls back to `"Hey,"`. Do NOT add a `first_name` column for this story — use `None` for all sends. A future story can add it.

### Re-engagement Worker

Add to `backend/app/workers/cleanup.py` (or new file `backend/app/workers/reengagement.py`):

```python
async def trial_reengagement_check() -> None:
    """
    Daily APScheduler job. Finds trialing users with zero campaigns
    who signed up more than 3 days ago and haven't been emailed yet.
    """
    async with async_session_factory() as db:
        cutoff_3d = datetime.now(timezone.utc) - timedelta(days=3)

        # Subquery: user has at least one campaign across any client
        has_campaign = (
            select(Campaign.id)
            .join(Client, Campaign.client_id == Client.id)
            .where(Client.user_id == User.id)
            .exists()
        )

        result = await db.execute(
            select(User, Subscription)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                Subscription.status == "trialing",
                Subscription.reengagement_email_sent_at.is_(None),
                User.created_at <= cutoff_3d.replace(tzinfo=None),
                ~has_campaign,
            )
            .limit(BATCH_LIMIT)
            .with_for_update(skip_locked=True)
        )
        rows = result.all()

        for user, sub in rows:
            try:
                # Set sent_at BEFORE sending — on exception it rolls back (AC8)
                sub.reengagement_email_sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.flush()
                await asyncio.to_thread(send_reengagement_email, user.email, None)
                await db.commit()
                logger.info("Re-engagement email sent for user %s", str(user.id))
            except Exception as exc:
                await db.rollback()
                sentry_sdk.capture_exception(exc)
                logger.error("Re-engagement failed for user %s: %s", str(user.id), exc)
```

### Scheduler Registration

Add to `backend/app/scheduler/scheduler.py`:

```python
from app.workers.reengagement import trial_reengagement_check  # or cleanup if added there

scheduler.add_job(
    trial_reengagement_check,
    trigger="cron",
    hour=9,
    minute=0,
    id="trial_reengagement_check",
    replace_existing=True,
    misfire_grace_time=3600,
)
```

### Files to Create

- `backend/app/workers/reengagement.py` (or add to `cleanup.py` — prefer separate file for clarity)
- Alembic migration file (generated via CLI — see Alembic rule above)

### Files to Update

- `backend/app/integrations/email.py` — add `build_email_html()`, update all three send functions, add `send_reengagement_email()`
- `backend/app/db/repositories/models.py` — add `reengagement_email_sent_at` to `Subscription`
- `backend/app/scheduler/scheduler.py` — register `trial_reengagement_check` job

## Tasks / Subtasks

- [x] Task 1: Alembic migration for `reengagement_email_sent_at` (AC: 9)
  - [x] Run `cd backend && alembic revision --autogenerate -m "add_reengagement_email_sent_at_to_subscriptions"`
  - [x] Verify generated migration adds nullable datetime column to `subscriptions`
  - [x] Update `Subscription` SQLModel in `models.py` to include `reengagement_email_sent_at: Optional[datetime] = Field(default=None, nullable=True)`
  - [x] Run `alembic upgrade head` locally to verify

- [x] Task 2: Build `build_email_html()` template function (AC: 1, 10)
  - [x] Add `build_email_html(body_html, cta_text, cta_url, heading)` to `backend/app/integrations/email.py`
  - [x] Table-based, all inline styles, no `<style>` block (Outlook compatibility)
  - [x] `#F9F9F6` bg, `#111111` text, `#E5E5E5` borders, Georgia heading font
  - [x] Hard-shadow CTA button: `box-shadow: 4px 4px 0px 0px #111111`
  - [x] Footer: "Questions? Email support@personnapress.com" + X/LinkedIn text links placeholder

- [x] Task 3: Migrate existing email functions to new template (AC: 1, 2)
  - [x] Wrap `send_verification_email` body in `build_email_html()` with CTA button
  - [x] Wrap `send_deletion_warning_email` body in `build_email_html()` with CTA button
  - [x] Add `"reply_to": "support@personnapress.com"` to BOTH existing send calls (AC2 — backfill)
  - [x] Confirm the deletion warning email body text unchanged (only wrapping changes)

- [x] Task 4: Add `send_reengagement_email()` function (AC: 3)
  - [x] Add function per the spec — founder personal tone, no big heading
  - [x] Subject: `"Quick check-in from Boris at PersonnaPress"`
  - [x] CTA: "Create your first campaign" → `{APP_URL}/dashboard`
  - [x] `reply_to: support@personnapress.com`
  - [x] `first_name` param accepts `None` → fallback to `"Hey,"`

- [x] Task 5: Build `trial_reengagement_check` worker (AC: 4, 5, 7, 8)
  - [x] Create `backend/app/workers/reengagement.py` (import from `cleanup.py` constants)
  - [x] SQL query: `trialing` + `reengagement_email_sent_at IS NULL` + `created_at` > 3 days + no campaign subquery (AC4, AC7)
  - [x] Set `reengagement_email_sent_at` before `asyncio.to_thread` send; rollback on exception (AC5, AC8)
  - [x] `sentry_sdk.capture_exception` + `logger.error` on failure (AC8)

- [x] Task 6: Register scheduler job (AC: 6)
  - [x] Add job to `backend/app/scheduler/scheduler.py` at `09:00 UTC`
  - [x] `replace_existing=True`, `misfire_grace_time=3600`

## Dev Agent Record

### Completion Notes

All 6 tasks implemented and validated (2026-07-26).

- **Task 1:** Added `reengagement_email_sent_at: Optional[datetime]` to `Subscription` SQLModel. Generated migration `20260726_1903_d7c9202f2367` via CLI (autogenerate output trimmed to only the required `add_column` — autogenerate detected many false-positive type diffs between `TIMESTAMP(timezone=True)` and `DateTime()` that were left out). `alembic upgrade head` applied successfully.
- **Task 2:** `build_email_html()` in `email.py` — table-based layout, all inline styles, `#F9F9F6` bg, `#111111` text, Georgia heading, hard-shadow CTA button, PersonnaPress wordmark header, footer with support email and social links placeholder.
- **Task 3:** Both `send_verification_email` and `send_deletion_warning_email` now use `build_email_html()` and include `reply_to: support@personnapress.com`.
- **Task 4:** `send_reengagement_email()` added — personal letter tone, no heading, subject "Quick check-in from Boris at PersonnaPress", CTA to `/dashboard`, `first_name=None` fallback to "Hey,".
- **Task 5:** `backend/app/workers/reengagement.py` created. Worker queries trialing users older than 3 days with no campaigns and no prior email. Sets `reengagement_email_sent_at` before sending (so rollback on exception leaves field unset for retry). Sentry + logger.error on failure.
- **Task 6:** `trial_reengagement_check` registered in `scheduler.py` at 09:00 UTC with `replace_existing=True` and `misfire_grace_time=3600`.

Regression check: 46 pre-existing test failures exist on baseline (unrelated to this story). No new failures introduced.

## File List

- `backend/app/db/repositories/models.py` — added `reengagement_email_sent_at` to `Subscription`
- `backend/alembic/versions/20260726_1903_d7c9202f2367_add_reengagement_email_sent_at_to_.py` — new migration (created)
- `backend/app/integrations/email.py` — added `build_email_html()`, `send_reengagement_email()`; updated `send_verification_email` and `send_deletion_warning_email` to use template + `reply_to`
- `backend/app/workers/reengagement.py` — new file: `trial_reengagement_check` worker
- `backend/app/scheduler/scheduler.py` — registered `trial_reengagement_check` job

### Review Findings

- [x] [Review][Patch] Verification email missing raw URL fallback — added raw URL as small text below CTA button for clients that block buttons. [backend/app/integrations/email.py:161]
- [x] [Review][Patch] Missing html.escape() on cta_text, cta_url, heading in build_email_html — added _html.escape() guards on all three params. [backend/app/integrations/email.py:46]
- [x] [Review][Patch] Off-by-one on 3-day cutoff: `<=` changed to `<` to mean "more than 3 days old" per AC4. [backend/app/workers/reengagement.py:38]
- [x] [Review][Defer] Rollback called before sentry_sdk.capture_exception/logger.error — if rollback itself raises, original exception is lost. [backend/app/workers/reengagement.py:54] — deferred, pre-existing pattern in cleanup.py
- [x] [Review][Defer] WITH FOR UPDATE lock held across asyncio.to_thread network call to Resend — pre-existing pattern in cleanup.py [backend/app/workers/cleanup.py:64]
- [x] [Review][Defer] No unsubscribe link in re-engagement email — CAN-SPAM/GDPR concern for marketing emails — deferred, pre-existing on all emails in codebase; address before scaling
- [x] [Review][Defer] BATCH_LIMIT=50 pagination gap — users beyond limit deferred to next daily run — deferred, acceptable for daily job volume

## Change Log

- 2026-07-26: Implemented story 19.2 — branded HTML email template, existing email rebrand, re-engagement drip worker + scheduler job, Alembic migration for `reengagement_email_sent_at`.
- 2026-07-26: Code review complete — 3 patches applied (verification URL fallback, html.escape injection guard, off-by-one cutoff), 4 deferred, 10 dismissed.
