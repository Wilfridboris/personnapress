---
baseline_commit: 8131e13
---

# Story 21.4: Threads Text Post Publishing

Status: done

## Story

As a PersonnaPress user with Threads connected,
I want to publish my campaign's X post content to Threads,
so that my Threads audience receives concise, brand-voice content without me writing a separate post.

## Context & Motivation

Depends on Stories 21.1 (Meta Platform Connection) and 21.2 (to have `meta.py` fully structured).
Threads publishing is a two-step API flow (create container, publish) similar to Instagram.
The X post is used as the Threads text since both are short-form (X: 280 chars, Threads: 500 chars).

**API version: v25.0** (not v21.0 from the epics file -- v21.0 is deprecated).

---

## Acceptance Criteria

### AC 1: Threads publish worker

**Given** Threads connected for the client,
**When** the user selects Threads as a publish destination and approves,
**Then** `dispatch_publish` calls
`meta_integration.publish_threads_post(threads_user_id, user_access_token, text)` which:

a) Create text container:
```
POST https://graph.facebook.com/v25.0/{threads_user_id}/threads
  media_type=TEXT
  text={x_post}
  access_token={user_access_token}
```
Returns `{id: container_id}`.

b) Publish container:
```
POST https://graph.facebook.com/v25.0/{threads_user_id}/threads_publish
  creation_id={container_id}
  access_token={user_access_token}
```
Returns `{id: threads_post_id}`.

Returns the Threads post ID from step b.

Note: The `x_post` is always <=280 chars, well within the 500-char Threads limit. No truncation needed.

### AC 2: Error handling

**Given** the Threads publish call fails,
**When** the failure occurs,
**Then** `PlatformError("threads", status_code, message)` is raised;
the Threads result is marked as failed;
other platform publish results in the same campaign are unaffected.

### AC 3: Publish results shape

**Given** a publish job completes for Threads,
**When** the job status is queried,
**Then** `publish_results` contains:
- Success: `{"threads": "success"}`
- Failure: `{"threads": "threads returned {code}: {message}"}`

### AC 4: Destination chip in approval panel

**Given** the approval gate destination picker,
**When** Threads is connected,
**Then** it appears as a selectable destination chip showing the `MessageSquare` Lucide icon
and `@{username}`; its selection behaviour matches the existing X and LinkedIn chip pattern.

Required changes in `approval-panel.tsx`:
- Import `MessageSquare` from `lucide-react`
- Add to `PLATFORM_ICON_MAP`: `threads: MessageSquare`
- Add to `PLATFORM_LABEL_MAP`: `threads: "Threads"`
- Add to `platformLabel()` function map

Additionally: when both X and Threads are selected as destinations, show a note below the
X post preview card: "Also posts to Threads". This helps the user understand the X post
content will be reused on Threads.

**Threads cannot be selected if no `x_post` content is generated.** Apply the same disabled
logic as the Instagram/no-image rule: disable the Threads chip when `!campaign.x_post`.

### AC 5: Paper Style compliance

**When** any Threads UI renders,
**Then** `rounded-none` surfaces; Lucide icons only; no em-dashes in any visible text.

---

## Dev Notes

### New function in `backend/app/integrations/meta.py`

Add to the file from Stories 21.1 and 21.2:

```python
async def publish_threads_post(
    threads_user_id: str,
    user_access_token: str,
    text: str,
) -> str:
    """Create and publish a Threads text post. Returns Threads post ID."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Create text container
        resp = await client.post(
            f"{GRAPH_API_BASE}/{threads_user_id}/threads",
            data={
                "media_type": "TEXT",
                "text": (text or ""),
                "access_token": user_access_token,
            },
        )
        if resp.status_code != 200:
            raise PlatformError("threads", resp.status_code, _extract_error(resp))
        container_id = resp.json().get("id", "")
        if not container_id:
            raise PlatformError("threads", 200, "threads container creation returned no id")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 2: Publish container
        pub_resp = await client.post(
            f"{GRAPH_API_BASE}/{threads_user_id}/threads_publish",
            data={"creation_id": container_id, "access_token": user_access_token},
        )
    if pub_resp.status_code == 429:
        raise PlatformError("threads", 429, "Threads rate limit reached. Try again later.")
    if pub_resp.status_code == 401:
        raise PlatformError("threads", 401, "Threads connection expired - reconnect in Connections")
    if pub_resp.status_code != 200:
        raise PlatformError("threads", pub_resp.status_code, _extract_error(pub_resp))
    post_id = pub_resp.json().get("id", "")
    if not post_id:
        raise PlatformError("threads", 200, "threads_publish returned no id")
    return post_id
```

### `dispatch_publish` in `publishing.py`

Add an `elif platform == "threads":` branch (after `facebook_page`):

```python
elif platform == "threads":
    if not campaign.x_post:
        logger.debug("dispatch_publish: skipping threads (no x_post) campaign=%s", campaign_id)
        results[platform] = "skipped"
        continue
    await meta_integration.publish_threads_post(
        creds["threads_user_id"],
        creds["user_access_token"],
        campaign.x_post,
    )
```

### Credential shape from Story 21.1

Threads credentials stored by Story 21.1:
```json
{"threads_user_id": "...", "username": "...", "user_access_token": "..."}
```

Note: Threads uses the **user access token** (long-lived), NOT a page access token.
This is distinct from Instagram (page token) and Facebook Page (page token).

### Rate limit: 250 Threads posts per 24-hour window

Higher than Instagram's 100/day. A 429 at `threads_publish` means the daily limit is hit.
The `PlatformError("threads", 429, ...)` at the publish step handles this correctly.

### Threads container: no polling needed

Unlike Instagram where the container needs time to process an image, a TEXT container on Threads
is typically immediately `PUBLISHED` after creation -- there's no async image processing.
The two-step create/publish is the API's design; no status polling is needed.

### "Also posts to Threads" note in approval panel

When both `x` and `threads` are in `selectedPlatforms`, show a note below the X post content:
```tsx
{selectedPlatforms.has("threads") && selectedPlatforms.has("x") && (
  <p className="text-xs text-[#555555] mt-1">Also posts to Threads</p>
)}
```
Place this directly below the X post preview card or editor.

### Threads chip disabled when no x_post

```tsx
// In DestinationChip row rendering
disabled={platform === "threads" && !campaign.x_post}
```

Add a tooltip or aria-description: "Requires an X post to be generated."

### No DB changes needed

Story 21.1 handles the `threads` enum value and credential storage.

### Rate-limiting note for publish sequencing

No staggered-publish delays are needed for Meta platforms in this v1 implementation
(unlike the 2s X delay and 5s LinkedIn delay). If future rate limiting becomes an issue,
add delays following the same pattern as `last_x_publish_time` and `last_linkedin_publish_time`.

---

## Tests Required

### Backend (pytest)

1. `test_publish_threads_success` -- mock httpx; assert container creation with media_type=TEXT,
   publish with creation_id, threads_id returned
2. `test_publish_threads_401` -- mock 401 on threads_publish; assert PlatformError(401)
3. `test_publish_threads_429` -- mock 429 on threads_publish; assert PlatformError(429)
   with rate-limit message
4. `test_publish_threads_no_x_post` -- campaign without x_post; assert "skipped" in results
5. `test_dispatch_publish_threads_independence` -- threads fails, linkedin succeeds;
   assert linkedin result is "success"
6. `test_publish_threads_container_no_id` -- container response missing `id`; assert PlatformError
