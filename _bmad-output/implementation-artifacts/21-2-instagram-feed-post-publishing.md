---
baseline_commit: 8131e13
---

# Story 21.2: Instagram Feed Post Publishing

Status: done

## Story

As a PersonnaPress user with Instagram connected,
I want to publish my campaign to Instagram as a captioned image post,
so that my Instagram audience receives visually compelling content without me writing a separate caption.

## Context & Motivation

Depends on Story 21.1 (Meta Platform Connection) being done.
Instagram feed posts require a two-step API flow: create a media container, poll until the image
is processed, then publish the container. Instagram also requires a `featured_image_url` -- posts
without an image are not possible as feed posts.

**API version: v25.0** (not v21.0 from the epics file -- v21.0 is deprecated).

---

## Acceptance Criteria

### AC 1: Instagram publish worker

**Given** a campaign with `featured_image_url` set and Instagram connected for the client,
**When** the user selects Instagram as a publish destination and approves,
**Then** `dispatch_publish` in `backend/app/services/publishing.py` calls
`meta_integration.publish_instagram_feed_post(instagram_user_id, page_access_token, image_url, caption)`
which performs:

a) Create media container:
```
POST https://graph.facebook.com/v25.0/{instagram_user_id}/media
  image_url={featured_image_url}
  caption={linkedin_post truncated to 2200 chars}
  access_token={page_access_token}
```
Returns `{id: container_id}`.

b) Poll container status (use exponential-ish approach; Meta recommends once per minute max 5 minutes):
```
GET https://graph.facebook.com/v25.0/{container_id}?fields=status_code&access_token={page_access_token}
```
Possible `status_code` values: `FINISHED`, `IN_PROGRESS`, `PUBLISHED`, `EXPIRED`, `ERROR`.
Stop polling when `FINISHED`. Raise `PlatformError("instagram", 422, "...")` on `ERROR` or `EXPIRED`.
After max retries without `FINISHED`, raise `PlatformError("instagram", 408, "container processing timed out")`.

**Polling implementation**: 6 polls at 10-second intervals (60s total max) -- more forgiving than
the spec's "10 polls at 3s" (30s total); Meta's own guidance says give containers time to process.

c) Publish container:
```
POST https://graph.facebook.com/v25.0/{instagram_user_id}/media_publish
  creation_id={container_id}
  access_token={page_access_token}
```
Returns `{id: media_id}`. Return this `media_id` from the function.

### AC 2: Instagram disabled when no featured image

**Given** a campaign has no `featured_image_url`,
**When** the user views the platform destination picker,
**Then** Instagram appears disabled with note:
"Instagram requires a featured image. Generate or upload one first."
Instagram cannot be selected until `featured_image_url` is populated.

Implementation: in `approval-panel.tsx`, add Instagram to the disabled-platforms logic when
`!campaign.image_url`. Check how existing chips use the `disabled` prop.

### AC 3: Error handling and per-platform independence

**Given** the Instagram publish call fails (429 rate limit, 401 expired token, invalid image format),
**When** the failure occurs,
**Then** `PlatformError("instagram", status_code, message)` is raised;
`dispatch_publish` catches it and marks the Instagram result as failed;
other platform results in the same campaign are unaffected.

This follows the existing exception handling in `dispatch_publish` at `publishing.py:694-702`.
No special handling needed -- the existing catch-all handles it.

### AC 4: Publish results shape

**Given** a publish job completes for Instagram,
**When** the job status is queried,
**Then** `publish_results` contains:
- Success: `{"instagram": "success"}`
- Failure: `{"instagram": "instagram returned {code}: {message}"}`

This matches the existing pattern -- `results[platform] = "success"` on success,
`results[platform] = str(exc)` on exception (line 702 of publishing.py).

### AC 5: Destination chip in approval panel

**Given** the approval gate destination picker (Story 14.1),
**When** Instagram is connected and `featured_image_url` is present,
**Then** Instagram appears as a selectable destination chip showing the `Camera` Lucide icon
and `@{username}` as the label.

Required changes in `approval-panel.tsx`:
- Import `Camera` from `lucide-react`
- Add to `PLATFORM_ICON_MAP`: `instagram: Camera`
- Add to `PLATFORM_LABEL_MAP`: `instagram: "Instagram"`
- Add `instagram` to `platformLabel()` function map

### AC 6: Caption length indicator

**Given** Paper Style constraints,
**When** Instagram is selected as a destination,
**Then** `rounded-none` surfaces; Lucide icons only; no em-dashes;
caption length shown as `{length}/2200 chars` below the LinkedIn post editor when Instagram
is selected as a destination.

---

## Dev Notes

### New function in `backend/app/integrations/meta.py`

Story 21.1 creates this file. Add to it:

```python
import asyncio
import httpx
from app.core.exceptions import PlatformError

GRAPH_API_BASE = "https://graph.facebook.com/v25.0"

async def publish_instagram_feed_post(
    instagram_user_id: str,
    page_access_token: str,
    image_url: str,
    caption: str,
) -> str:
    """Create and publish an Instagram feed image post. Returns media_id."""
    caption_truncated = (caption or "")[:2200]

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Create container
        resp = await client.post(
            f"{GRAPH_API_BASE}/{instagram_user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption_truncated,
                "access_token": page_access_token,
            },
        )
        if resp.status_code != 200:
            raise PlatformError("instagram", resp.status_code, _extract_error(resp))
        container_id = resp.json().get("id", "")
        if not container_id:
            raise PlatformError("instagram", 200, "media container creation returned no id")

    # Step 2: Poll container status (6 polls, 10s apart = 60s max)
    for attempt in range(6):
        if attempt > 0:
            await asyncio.sleep(10)
        async with httpx.AsyncClient(timeout=15.0) as client:
            status_resp = await client.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": page_access_token},
            )
        if status_resp.status_code != 200:
            raise PlatformError("instagram", status_resp.status_code, "container status check failed")
        status_code = status_resp.json().get("status_code", "")
        if status_code == "FINISHED":
            break
        if status_code in ("ERROR", "EXPIRED"):
            raise PlatformError("instagram", 422, f"container processing failed: {status_code}")
    else:
        raise PlatformError("instagram", 408, "instagram container processing timed out after 60s")

    # Step 3: Publish
    async with httpx.AsyncClient(timeout=15.0) as client:
        pub_resp = await client.post(
            f"{GRAPH_API_BASE}/{instagram_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": page_access_token},
        )
    if pub_resp.status_code != 200:
        raise PlatformError("instagram", pub_resp.status_code, _extract_error(pub_resp))
    media_id = pub_resp.json().get("id", "")
    if not media_id:
        raise PlatformError("instagram", 200, "media_publish returned no id")
    return media_id


def _extract_error(resp: httpx.Response) -> str:
    """Extract error message from Meta API response."""
    try:
        body = resp.json()
        return body.get("error", {}).get("message", resp.text[:200])
    except Exception:
        return resp.text[:200]
```

### `dispatch_publish` in `publishing.py`

Add an `elif platform == "instagram":` branch after the `linkedin` branch:

```python
elif platform == "instagram":
    if not campaign.image_url:
        logger.debug("dispatch_publish: skipping instagram (no image_url) campaign=%s", campaign_id)
        results[platform] = "skipped"
        continue
    if not campaign.linkedin_post:
        logger.debug("dispatch_publish: skipping instagram (no linkedin_post for caption) campaign=%s", campaign_id)
        results[platform] = "skipped"
        continue
    await meta_integration.publish_instagram_feed_post(
        creds["instagram_user_id"],
        creds["page_access_token"],
        campaign.image_url,
        campaign.linkedin_post,
    )
```

Add `from app.integrations import meta as meta_integration` to imports in `publishing.py`.

### Credential shape from Story 21.1

Instagram credentials stored by Story 21.1:
```json
{"instagram_user_id": "...", "username": "...", "page_access_token": "...",
 "facebook_page_id": "...", "facebook_page_name": "..."}
```

### Rate limit: 100 posts per 24-hour moving window

Instagram enforces this at the `media_publish` endpoint. A 429 response means the daily limit
is hit. Surface as `PlatformError("instagram", 429, "Instagram publishing rate limit reached. Try again tomorrow.")`.

### No DB changes needed

Story 21.1 already creates the `instagram` enum value and `platform_connections` rows.
This story only adds publishing logic.

### Caption source: `linkedin_post`

Use `campaign.linkedin_post` as the Instagram caption (truncated to 2200 chars).
This is specified in the epics file AC 1. Instagram doesn't have its own post field.

---

## Tests Required

### Backend (pytest)

1. `test_publish_instagram_success` -- mock httpx; assert container created, polling done,
   media_publish called, media_id returned
2. `test_publish_instagram_container_error` -- mock status_code=ERROR; assert PlatformError raised
3. `test_publish_instagram_container_timeout` -- mock status_code=IN_PROGRESS for all 6 polls;
   assert PlatformError with "timed out" message
4. `test_publish_instagram_no_image` -- campaign without image_url; assert "skipped" returned
5. `test_publish_instagram_rate_limit` -- mock 429 on media_publish; assert PlatformError(429)
6. `test_dispatch_publish_instagram_platform_independence` -- instagram fails, x succeeds;
   assert x result is "success" and instagram result is error string
