---
baseline_commit: 0196298
---

# Story 19.3: Post-Verification Welcome Email

Status: done

## Story

As a new user who just verified their email,
I want to receive a branded welcome email immediately,
so that I know I'm in, what to do first, and feel like a real person is paying attention.

## Acceptance Criteria

1. **Given** a user clicks their verification link and `user.verified` transitions from `False` to `True` in `verify_email()`, **When** the DB commit succeeds, **Then** a welcome email is sent to their address as a fire-and-forget task — the verification response is NOT delayed waiting for Resend.

2. **Given** a brand-new Google OAuth user is created (the `if user is None:` branch in `auth_google()`), **When** the user record is committed, **Then** a welcome email is also sent to their address as a fire-and-forget task.

3. **Given** a user's `verified` flag is already `True` when `verify_email()` is called (re-click of the verification link), **When** the early-return path (`if user.verified: return await _issue_session(...)`) executes, **Then** no welcome email is sent — the early return is the natural idempotency guard, so no duplicate email is possible.

4. **Given** a returning Google OAuth user logs in (the `else:` branch in `auth_google()`), **When** the session is issued, **Then** no welcome email is sent.

5. **Given** `send_welcome_email` is called, **When** it runs, **Then** it sends via Resend with: subject `"You're in - here's what to do first"`, `reply_to: support@personnapress.com`, the branded `build_email_html()` template, a CTA button `"Create your first client"` linking to `{APP_URL}/dashboard`, and a personal letter-style body (no heading block) with Boris's name signed at the end.

6. **Given** `send_welcome_email` is called with a non-None `first_name`, **When** the email renders, **Then** the salutation reads `"Hey {first_name},"`. **Given** `first_name` is `None`, **Then** the salutation reads `"Hey,"`.

7. **Given** `send_welcome_email` raises an exception (Resend network error), **When** the exception is caught inside the fire-and-forget task, **Then** it is logged with `logger.warning` and does NOT propagate — the user's session is issued normally and the welcome email failure is silent to the user.

8. **Given** no em-dash character appears anywhere in the subject line, body copy, or CTA label of the welcome email, **When** the copy is reviewed, **Then** it passes — per the project-wide no-em-dash rule.

## Tasks / Subtasks

- [x] Task 1 — Add `send_welcome_email` to `email.py` (AC: 5, 6, 8)
  - [x] Add `send_welcome_email(to_email: str, first_name: str | None) -> None` to `backend/app/integrations/email.py`
  - [x] Use `build_email_html()` with no `heading` arg (letter style), CTA `"Create your first client"` → `{settings.APP_URL}/dashboard`
  - [x] Use personal copy (see Dev Notes for approved draft)
  - [x] Set `reply_to: "support@personnapress.com"` on the Resend call

- [x] Task 2 — Hook into `verify_email()` in `auth_service.py` (AC: 1, 3, 7)
  - [x] Import `send_welcome_email` alongside the existing import of `send_verification_email`
  - [x] Add a `_schedule_welcome_email(email: str) -> None` helper using the same `asyncio.create_task(_run())` pattern as `_schedule_add_contact`
  - [x] Call `_schedule_welcome_email` after `_schedule_add_contact` at the end of `verify_email()` (line ~154), only in the `user.verified = True` branch — NOT inside the `if user.verified: return` early-return branch

- [x] Task 3 — Hook into `auth_google()` new-user branch (AC: 2, 4, 7)
  - [x] In the `if user is None:` branch of `auth_google()`, after `_new_subscription` is called, add `_schedule_welcome_email(email)`
  - [x] Do NOT add a welcome email call to the `else:` branch (returning users)

- [x] Task 4 — Tests (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Create `backend/tests/test_welcome_email.py`
  - [x] Test: `send_welcome_email` calls `resend.Emails.send` with correct subject, reply_to, and CTA in html
  - [x] Test: salutation uses first_name when provided
  - [x] Test: salutation falls back to `"Hey,"` when first_name is None
  - [x] Test: `verify_email()` fires `send_welcome_email` when `user.verified` was False
  - [x] Test: `verify_email()` does NOT fire `send_welcome_email` when `user.verified` was already True (early-return path)
  - [x] Test: `auth_google()` fires `send_welcome_email` for brand-new user (user is None branch)
  - [x] Test: `auth_google()` does NOT fire `send_welcome_email` for returning user (else branch)

## Dev Notes

### Email copy (approved draft — use verbatim, no em-dashes)

```
subject: "You're in - here's what to do first"

body:
Hey [first_name / there],

Your email is confirmed - you're in.

To get your first blog post, start by creating a client profile. Then paste a few bullet points about what's on your mind this week, and PersonnaPress writes a full post in your voice and publishes it wherever you need it.

If you hit a snag or have a question, just reply to this email. It comes straight to me.

Boris
Founder, PersonnaPress
```

The sign-off `Boris / Founder, PersonnaPress` can be rendered as a final `<p>` in the `body_html` string — no separate heading block. Do not use `heading=` parameter.

### Fire-and-forget pattern

Follow the exact same helper pattern already in `auth_service.py` for `_schedule_add_contact`:

```python
def _schedule_welcome_email(email: str) -> None:
    async def _run() -> None:
        try:
            await asyncio.to_thread(send_welcome_email, email, None)
        except Exception:
            logger.warning("Failed to send welcome email to %s", email)
    asyncio.create_task(_run())
```

`first_name` is `None` for now — Users model has no `first_name` column. If it is added later, the call can be updated.

### verify_email() insertion point

In `backend/app/services/auth_service.py`, the insertion is after line 154 (`_schedule_add_contact` call), still inside the `if not user.verified` flow that has now set `user.verified = True`:

```python
    user.verified = True
    await db.commit()
    await db.refresh(user)
    _schedule_add_contact(user.email, "signup")
    _schedule_welcome_email(user.email)          # <-- add here
    return await _issue_session(user, db)
```

### auth_google() insertion point

In `backend/app/services/auth_service.py`, the `if user is None:` branch currently calls `_new_subscription` then falls through to the `return await _issue_session(...)` path. Add after `await _new_subscription(user.id, db)`:

```python
    if user is None:
        user = User(email=email, google_sub=google_sub, verified=True)
        db.add(user)
        await db.flush()
        await _new_subscription(user.id, db)
        _schedule_welcome_email(email)           # <-- add here
```

### Idempotency — no DB column needed

`user.verified` is the natural guard:
- Email/password: `verify_email()` lines 148-149 return early if `user.verified` is already True, so the welcome email block is unreachable on re-clicks.
- Google OAuth: the `if user is None:` branch only executes when no matching user exists — a returning Google user always hits `else:`.

No `welcome_email_sent_at` column is needed.

### No scheduler changes

`scheduler.py` and `workers/` are not touched by this story.

### Test mocking pattern

Follow the pattern from `tests/workers/test_cleanup.py` — use `unittest.mock.patch` and `AsyncMock`/`MagicMock`. For `asyncio.create_task` tests, patch `asyncio.create_task` and assert it was called, or run the inner `_run()` coroutine directly by extracting it from the patched call.

A simpler approach used in several auth tests: patch `app.integrations.email.send_welcome_email` directly and assert it gets called (or not) when the service function runs. For fire-and-forget tasks you may need to patch `asyncio.create_task` or use `asyncio.run` in the test.

### Project-wide rules (from project-context.md)

- No em-dashes anywhere in user-facing text — subject line, body, CTA
- All email styles must be inline (no `<style>` block) — already enforced by `build_email_html()`
- `reply_to` must be set on every Resend send call (established in 19.2)

### References

- Existing email functions: `backend/app/integrations/email.py` — `build_email_html`, `send_reengagement_email` (direct model to follow)
- Fire-and-forget helper: `backend/app/services/auth_service.py` — `_schedule_add_contact` (lines 41-48)
- Verification trigger: `backend/app/services/auth_service.py` — `verify_email()` (lines 113-155)
- Google OAuth trigger: `backend/app/services/auth_service.py` — `auth_google()` (lines 208-260)
- Worker test pattern: `backend/tests/workers/test_cleanup.py`
- No-em-dash rule: `backend/_bmad-output/project-context.md`

### Review Findings

- [x] [Review][Patch] exc_info missing from warning log [backend/app/services/auth_service.py:56]
- [x] [Review][Patch] Extra blank line between _schedule_welcome_email and _err [backend/app/services/auth_service.py:59]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `send_welcome_email(to_email, first_name)` added to `email.py` following the `send_reengagement_email` pattern: letter-style body (no heading block), CTA "Create your first client" to `/dashboard`, `reply_to: support@personnapress.com`, subject `"You're in - here's what to do first"`, no em-dashes.
- `_schedule_welcome_email(email)` helper added to `auth_service.py` mirroring the `_schedule_add_contact` fire-and-forget pattern via `asyncio.create_task`.
- Called after `_schedule_add_contact` in `verify_email_token()` (only in the `user.verified = True` branch — idempotency guard is the early-return on line 148).
- Called after `_schedule_add_contact` in `auth_google()` `if user is None:` branch only (not the `else:` returning-user branch).
- 9 tests written and passing: subject/reply_to, CTA in HTML, salutation with first_name, salutation without first_name, no em-dash, verify fires welcome, verify does NOT fire on re-click, google new-user fires welcome, google returning-user does NOT fire welcome.

### File List

- backend/app/integrations/email.py
- backend/app/services/auth_service.py
- backend/tests/test_welcome_email.py

## Change Log

- 2026-07-26: Implemented story 19.3 — added `send_welcome_email` to email.py, `_schedule_welcome_email` helper to auth_service.py, hooked into verify_email_token() and auth_google() new-user branch, 9 tests passing.
