---
baseline_commit: 3a6310c
---

# Story 21.8: Meta Token Auto-Renewal (Threads)

Status: done

**Depends on: Story 21-6** (Threads standalone OAuth). The `threads_auth.py` integration file
and `THREADS_APP_ID`/`THREADS_APP_SECRET` settings must exist before this story can be implemented.

---

## Story

As a PersonnaPress user with Threads connected,
I want my Threads access token to be renewed automatically before it expires,
so that publishing to Threads keeps working beyond the initial 60-day window without requiring me to manually reconnect.

---

## Context & Motivation

Meta long-lived user tokens expire after 60 days. After expiry, every Meta publish call returns
401 and the job fails -- the user must manually reconnect the platform.

The other platforms already handle this proactively:
- **X**: `_refresh_x_token_if_needed()` in `publishing.py` calls `twitter_integration.refresh_access_token()` using a stored `refresh_token` before every publish.
- **GitHub**: `_refresh_token_if_needed()` checks `expires_at` and fetches a fresh installation token when within 5 minutes of expiry.

Meta has no equivalent yet.

**Scope analysis:**
- **Instagram credentials** store a `page_access_token` (Facebook Page-level token derived from the user token). Page-level tokens do NOT expire. No renewal needed.
- **Facebook Page credentials** also store a `page_access_token` (Page-level). Does not expire. No renewal needed.
- **Threads credentials** (added in story 21-6) store a `user_access_token` -- a Threads long-lived API token that expires after 60 days. **This is what needs renewal.**

Facebook/Threads APIs support proactive renewal: call the long-lived token exchange endpoint again
with the existing (still-valid) long-lived token to receive a new 60-day token.

This story adds:
1. A `renew_long_lived_token()` helper in `threads_auth.py` (the file created in story 21-6).
2. A `_refresh_threads_token_if_needed()` helper in `publishing.py`, matching the pattern of `_refresh_x_token_if_needed()`.
3. Wiring in both `dispatch_publish_for_platform` and `dispatch_publish`.
4. A `renew_long_lived_user_token()` helper in `meta.py` for future Facebook user-token use (not wired into dispatch -- page tokens don't expire).

---

## Acceptance Criteria

### AC 1: `renew_long_lived_token` added to `threads_auth.py`

**Given** a valid (non-expired) Threads long-lived user access token,
**When** `renew_long_lived_token(token)` is called,
**Then** it calls `GET https://graph.threads.net/access_token` with `grant_type=th_exchange_token`,
returns the new access token string on HTTP 200,
and raises `PlatformError("threads", status_code, message)` on any non-200 response or a 200 with no `access_token` field.

### AC 2: `_refresh_threads_token_if_needed` added to `publishing.py`

**Given** a Threads credential dict,
**When** `_refresh_threads_token_if_needed(cred, db, client_id)` is called,
**Then**:
- If `cred` has no `token_acquired_at` key, return `cred` unchanged (legacy credential, no renewal).
- If the token is fewer than 53 days old (60-day expiry minus 7-day proactive buffer), return `cred` unchanged.
- If the token is 53 or more days old, call `threads_auth_integration.renew_long_lived_token()`, update `user_access_token` and `token_acquired_at` in the credential dict, encrypt and persist to the DB via `upsert_connection`, and return the updated dict.
- If renewal fails with `PlatformError`, `httpx.HTTPError`, or `httpx.TimeoutException`, log a warning and return the original `cred` (non-fatal -- the publish attempt still proceeds with the existing token).

### AC 3: Wired into both dispatch functions

**Given** a publish job targeting the `threads` platform,
**When** `dispatch_publish_for_platform` or `dispatch_publish` reaches the `threads` branch,
**Then** `_refresh_threads_token_if_needed(creds, db, campaign.client_id)` is called and its return value is used as `creds` before calling `meta_integration.publish_threads_post()`.

### AC 4: `renew_long_lived_user_token` added to `meta.py`

**Given** a valid (non-expired) Facebook long-lived user access token,
**When** `renew_long_lived_user_token(token)` is called,
**Then** it calls `GET https://graph.facebook.com/v25.0/oauth/access_token` with `grant_type=fb_exchange_token`,
returns the new token string on HTTP 200,
and raises `PlatformError("Meta", status_code, message)` on failure.
This function is added for completeness and future use; it is NOT wired into publish dispatch in this story.

### AC 5: No frontend changes

**Given** this story,
**When** implemented,
**Then** no frontend files are modified. Token renewal is entirely backend-side and transparent to the user.

### AC 6: Non-fatal on renewal failure

**Given** the Threads token renewal API call fails (network error, Threads API down, token already fully expired),
**When** `_refresh_threads_token_if_needed` catches the exception,
**Then** a `WARNING`-level log is emitted and the original credential is returned so the publish attempt still proceeds. The failure does not itself cause the job to fail (the subsequent publish call may still fail with a 401, which is the expected error path for an expired token).

---

## Dev Notes

### Prerequisite check before starting

Confirm story 21-6 is complete:
- `backend/app/integrations/threads_auth.py` exists with the Threads standalone OAuth flow.
- `settings.THREADS_APP_ID` and `settings.THREADS_APP_SECRET` are defined in `backend/app/core/config.py`.

---

### 1. `backend/app/integrations/threads_auth.py` -- add `renew_long_lived_token`

Add this function to the existing file from story 21-6. Place it after the existing OAuth helpers:

```python
async def renew_long_lived_token(token: str) -> str:
    """Renew an expiring Threads long-lived token. Returns new token string."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://graph.threads.net/access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_id": settings.THREADS_APP_ID,
                "client_secret": settings.THREADS_APP_SECRET,
                "access_token": token,
            },
        )
    if resp.status_code != 200:
        body = resp.json() if resp.content else {}
        detail = body.get("error", {}).get("message") or "Threads token renewal failed"
        raise PlatformError("threads", resp.status_code, detail)
    new_token = resp.json().get("access_token")
    if not new_token:
        raise PlatformError("threads", 200, "Threads token renewal returned no access_token")
    return new_token
```

---

### 2. `backend/app/services/publishing.py` -- add import and helper

**Add import** at the top of `publishing.py` alongside the other integration imports (around line 24-29):

```python
from app.integrations import threads_auth as threads_auth_integration
```

**Add `_refresh_threads_token_if_needed`** after the existing `_refresh_x_token_if_needed` function (after line 63) and before `_refresh_token_if_needed`:

```python
async def _refresh_threads_token_if_needed(cred: dict, db: AsyncSession, client_id: UUID) -> dict:
    """Renew Threads long-lived token if within 7 days of 60-day expiry.

    Token is renewed proactively when >= 53 days old (60 - 7 buffer).
    Non-fatal on failure -- returns original cred so publish attempt still proceeds.
    """
    token_acquired_at = cred.get("token_acquired_at")
    if not token_acquired_at:
        return cred  # legacy credential without timestamp -- skip renewal
    try:
        acquired = datetime.fromisoformat(token_acquired_at)
        days_old = (datetime.now(timezone.utc) - acquired).days
        if days_old < 53:
            return cred  # still fresh, no renewal needed
    except (ValueError, TypeError):
        return cred

    user_access_token = cred.get("user_access_token")
    if not user_access_token:
        return cred

    try:
        new_token = await threads_auth_integration.renew_long_lived_token(user_access_token)
        updated = dict(cred)
        updated["user_access_token"] = new_token
        updated["token_acquired_at"] = datetime.now(timezone.utc).isoformat()
        encrypted = encrypt_credential(json.dumps(updated))
        await upsert_connection(db, client_id, "threads", encrypted)
        logger.info("Threads token renewed for client %s", client_id)
        return updated
    except (PlatformError, httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("Threads token renewal failed for client %s: %s", client_id, exc)
        return cred  # non-fatal -- proceed with existing token
```

---

### 3. Wire into `dispatch_publish_for_platform` (single-platform dispatch)

The `threads` branch is currently at approximately line 575. Add the renewal call as the first line inside the `elif platform == "threads":` block, before the content check:

```python
elif platform == "threads":
    creds = await _refresh_threads_token_if_needed(creds, db, campaign.client_id)  # NEW
    if not (campaign.x_post or "").strip():
        logger.debug("dispatch_publish_for_platform: skipping threads (no x_post) campaign=%s", campaign_id)
        return {platform: "skipped"}
    await meta_integration.publish_threads_post(
        creds["threads_user_id"],
        creds["user_access_token"],
        campaign.x_post,
    )
```

---

### 4. Wire into `dispatch_publish` (multi-platform dispatch)

The `threads` branch is currently at approximately line 742. Same pattern:

```python
elif platform == "threads":
    creds = await _refresh_threads_token_if_needed(creds, db, campaign.client_id)  # NEW
    if not (campaign.x_post or "").strip():
        logger.debug("dispatch_publish: skipping threads (no x_post) campaign=%s", campaign_id)
        results[platform] = "skipped"
        continue
    await meta_integration.publish_threads_post(
        creds["threads_user_id"],
        creds["user_access_token"],
        campaign.x_post,
    )
```

---

### 5. `backend/app/integrations/meta.py` -- add `renew_long_lived_user_token`

Add to `meta.py` after the existing `exchange_code_for_short_lived_token` function. This is for completeness/future use; do NOT wire it into dispatch:

```python
async def renew_long_lived_user_token(token: str) -> str:
    """Renew an expiring Facebook long-lived user token (valid 60 days).

    Page-level tokens derived from long-lived user tokens do NOT expire,
    so this function is not used in the current publish flow. It is provided
    for future use if user-level token storage is added.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{META_GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "fb_exchange_token": token,
            },
        )
    if resp.status_code != 200:
        body = resp.json() if resp.content else {}
        detail = body.get("error", {}).get("message") or "Facebook token renewal failed"
        raise PlatformError("Meta", resp.status_code, detail)
    new_token = resp.json().get("access_token")
    if not new_token:
        raise PlatformError("Meta", 200, "Facebook token renewal returned no access_token")
    return new_token
```

---

### Credential shape reference

**Threads credentials** (written by story 21-6, read by this story):
```json
{
  "threads_user_id": "...",
  "username": "...",
  "user_access_token": "...",
  "token_acquired_at": "2026-08-01T00:00:00+00:00"
}
```

The `token_acquired_at` field is ISO-8601 with timezone. `datetime.fromisoformat()` on Python 3.11+ handles this natively. The renewal logic should treat missing `token_acquired_at` as "skip renewal" (legacy path) rather than erroring.

**Instagram credentials** (unchanged, no renewal):
```json
{"instagram_user_id": "...", "username": "...", "page_access_token": "...", "facebook_page_id": "...", "facebook_page_name": "..."}
```

**Facebook Page credentials** (unchanged, no renewal):
```json
{"page_id": "...", "page_name": "...", "page_access_token": "..."}
```

---

### Renewal endpoint reference

**Threads renewal:**
```
GET https://graph.threads.net/access_token
  ?grant_type=th_exchange_token
  &client_id={THREADS_APP_ID}
  &client_secret={THREADS_APP_SECRET}
  &access_token={existing_long_lived_token}
```
Success response: `{"access_token": "...", "token_type": "bearer"}`

**Facebook user-token renewal** (for the `meta.py` helper only):
```
GET https://graph.facebook.com/v25.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={META_APP_ID}
  &client_secret={META_APP_SECRET}
  &fb_exchange_token={existing_long_lived_token}
```
Success response: `{"access_token": "...", "token_type": "bearer"}`

---

### Why 53-day threshold?

60-day expiry minus 7-day proactive buffer = renew starting at day 53. This gives a one-week
window for renewal to succeed despite transient API failures. The renewal call is made on every
publish when the token is 53+ days old; once renewed, `token_acquired_at` is reset and the
53-day clock starts over.

---

## Tests Required

### Backend (pytest)

1. **`test_renew_long_lived_token_success`** -- mock httpx GET to `graph.threads.net/access_token`; assert returns new token string.
2. **`test_renew_long_lived_token_non_200`** -- mock 400 response; assert `PlatformError("threads", 400, ...)` raised.
3. **`test_renew_long_lived_token_no_access_token`** -- mock 200 with `{}` body; assert `PlatformError("threads", 200, ...)` raised.
4. **`test_refresh_threads_token_fresh`** -- `token_acquired_at` set 10 days ago; assert cred returned unchanged, no httpx call made.
5. **`test_refresh_threads_token_stale`** -- `token_acquired_at` set 55 days ago; assert `renew_long_lived_token` called, credential updated, `upsert_connection` called, new cred returned.
6. **`test_refresh_threads_token_no_timestamp`** -- credential without `token_acquired_at`; assert cred returned unchanged.
7. **`test_refresh_threads_token_renewal_failure`** -- 55-day-old token, renewal raises `PlatformError`; assert original cred returned (non-fatal), warning logged.
8. **`test_refresh_threads_token_timeout`** -- 55-day-old token, renewal raises `httpx.TimeoutException`; assert original cred returned.
9. **`test_renew_long_lived_user_token_success`** -- meta.py function; mock httpx GET; assert new token returned.
10. **`test_renew_long_lived_user_token_failure`** -- mock 401; assert `PlatformError("Meta", 401, ...)`.

---

## Dev Agent Record

### Implementation Notes

All 5 implementation tasks completed:

1. Added `renew_long_lived_token(token)` to `threads_auth.py` -- calls `GET https://graph.threads.net/access_token` with `grant_type=th_exchange_token`, raises `PlatformError` on non-200 or missing token.
2. Added `renew_long_lived_user_token(token)` to `meta.py` -- calls `GET https://graph.facebook.com/v25.0/oauth/access_token` with `grant_type=fb_exchange_token`, for future use only (page tokens don't expire).
3. Added `threads_auth as threads_auth_integration` import to `publishing.py`.
4. Added `_refresh_threads_token_if_needed(cred, db, client_id)` to `publishing.py` -- 53-day threshold (60-day expiry minus 7-day buffer), non-fatal on failure.
5. Wired `_refresh_threads_token_if_needed` into both `dispatch_publish_for_platform` (line ~576) and `dispatch_publish` (line ~743) threads branches.

### Completion Notes

All 10 required tests pass. 56/56 tests in `test_meta_integration.py` pass. Pre-existing failures in unrelated test files (spacy missing, test_jobs_router, test_questionnaire_worker) are not caused by this story.

---

## File List

- `backend/app/integrations/threads_auth.py` -- added `renew_long_lived_token`
- `backend/app/integrations/meta.py` -- added `renew_long_lived_user_token`
- `backend/app/services/publishing.py` -- added `threads_auth_integration` import, `_refresh_threads_token_if_needed`, wired into both dispatch functions
- `backend/tests/test_meta_integration.py` -- added 10 tests for token renewal

---

## Change Log

- 2026-08-01: Implemented story 21-8 -- Threads token auto-renewal with 53-day proactive buffer, non-fatal on failure; Facebook user-token renewal helper added to meta.py for future use.

---

### Review Findings

- [x] [Review][Patch] Broaden except clause in `_refresh_threads_token_if_needed` to catch `Exception` — DB/serialization errors from `upsert_connection`, `encrypt_credential`, `json.dumps` are not caught, violating the non-fatal intent of AC2/AC6 [publishing.py:97]
- [x] [Review][Patch] Guard `resp.json()` on error path in `renew_long_lived_token` — inconsistent with other functions in same file that wrap `resp.json()` in try/except [threads_auth.py:76]
- [x] [Review][Patch] Guard `resp.json()` on error path in `renew_long_lived_user_token` — same unguarded pattern [meta.py:94]
- [x] [Review][Patch] Add WARNING log assertion to `test_refresh_threads_token_renewal_failure` — AC6 requires log emission; test was missing this assertion [test_meta_integration.py:1443]
- [x] [Review][Patch] Add WARNING log assertion to `test_refresh_threads_token_timeout` — same AC6 gap [test_meta_integration.py:1465]
- [x] [Review][Patch] Add `test_renew_long_lived_user_token_no_access_token` test — 200-with-no-access_token path in `renew_long_lived_user_token` is implemented but untested [test_meta_integration.py]
- [x] [Review][Defer] Concurrent double-renewal race in multi-worker deployment [publishing.py:88-99] — deferred, pre-existing; same pattern as X token refresh; requires advisory lock / optimistic concurrency, out of scope
- [x] [Review][Defer] No integration test for AC3 dispatch wiring — deferred, pre-existing; consistent with codebase pattern (X, GitHub refresh also have no dispatch-level tests)
- [x] [Review][Defer] Future `token_acquired_at` (clock skew) silently skips renewal forever — deferred, low probability; guard exists for parse errors, clock skew is an ops concern
- [x] [Review][Defer] `renew_long_lived_token` is semantically identical to `exchange_short_lived_for_long_lived_token` — deferred, by Threads API design; both use same endpoint; refactor is out of scope
- [x] [Review][Defer] Python 3.10 compat for `fromisoformat` with `+00:00` suffix — deferred, project targets Python 3.11+
