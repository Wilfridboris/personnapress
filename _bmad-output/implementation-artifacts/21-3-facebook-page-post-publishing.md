---
baseline_commit: 8131e13
---

# Story 21.3: Facebook Page Post Publishing

Status: done

## Story

As a PersonnaPress user with a Facebook Page connected,
I want to publish my campaign's social content to my Facebook Page,
so that my Facebook audience receives the same quality content as other platforms without extra work.

## Context & Motivation

Depends on Story 21.1 (Meta Platform Connection) and should be done after 21.2 since `meta.py`
is established by then. Facebook Page publishing is the simplest of the three Meta publish
stories -- it's a single API call to `/{page-id}/feed`.

**API version: v25.0** (not v21.0 from the epics file -- v21.0 is deprecated).

---

## Acceptance Criteria

### AC 1: Facebook Page publish worker

**Given** a Facebook Page connected for the client,
**When** the user selects Facebook Page as a publish destination and approves,
**Then** `dispatch_publish` calls
`meta_integration.publish_facebook_page_post(page_id, page_access_token, message, image_url=None)` which:

Posts to:
```
POST https://graph.facebook.com/v25.0/{page_id}/feed
  message={linkedin_post}
  access_token={page_access_token}
```

If `featured_image_url` is set, also include `link={featured_image_url}` in the request body.
Returns the created post ID (`{id}` from the response).

### AC 2: Error handling

**Given** the Facebook Page publish call fails,
**When** the failure occurs,
**Then** `PlatformError("facebook_page", status_code, message)` is raised;
the Facebook Page result is marked as failed;
other platform publish results in the same campaign are unaffected.

### AC 3: Publish results shape

**Given** a publish job completes for Facebook Page,
**When** the job status is queried,
**Then** `publish_results` contains:
- Success: `{"facebook_page": "success"}`
- Failure: `{"facebook_page": "facebook_page returned {code}: {message}"}`

### AC 4: Destination chip in approval panel

**Given** the approval gate destination picker,
**When** Facebook Page is connected,
**Then** it appears as a selectable destination chip showing the `Users` Lucide icon and the page name;
its selection behaviour matches the existing X and LinkedIn chip pattern.

Required changes in `approval-panel.tsx`:
- Import `Users` from `lucide-react`
- Add to `PLATFORM_ICON_MAP`: `facebook_page: Users`
- Add to `PLATFORM_LABEL_MAP`: `facebook_page: "Facebook Page"`
- Add to `platformLabel()` function map

### AC 5: Paper Style compliance

**When** any Facebook Page UI renders,
**Then** `rounded-none` surfaces; Lucide icons only; no em-dashes in any user-visible text.

---

## Dev Notes

### New function in `backend/app/integrations/meta.py`

Add to the file created by Story 21.1:

```python
async def publish_facebook_page_post(
    page_id: str,
    page_access_token: str,
    message: str,
    image_url: str | None = None,
) -> str:
    """Post to a Facebook Page feed. Returns post ID."""
    payload: dict = {
        "message": (message or ""),
        "access_token": page_access_token,
    }
    if image_url:
        payload["link"] = image_url

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{GRAPH_API_BASE}/{page_id}/feed",
            data=payload,
        )
    if resp.status_code == 429:
        raise PlatformError("facebook_page", 429, "Facebook Page rate limit reached")
    if resp.status_code == 401:
        raise PlatformError("facebook_page", 401, "Facebook Page connection expired - reconnect in Connections")
    if resp.status_code != 200:
        raise PlatformError("facebook_page", resp.status_code, _extract_error(resp))
    post_id = resp.json().get("id", "")
    if not post_id:
        raise PlatformError("facebook_page", 200, "feed post returned no id")
    return post_id
```

### `dispatch_publish` in `publishing.py`

Add an `elif platform == "facebook_page":` branch (after the `instagram` branch from Story 21.2):

```python
elif platform == "facebook_page":
    if not campaign.linkedin_post:
        logger.debug("dispatch_publish: skipping facebook_page (no linkedin_post) campaign=%s", campaign_id)
        results[platform] = "skipped"
        continue
    await meta_integration.publish_facebook_page_post(
        creds["page_id"],
        creds["page_access_token"],
        campaign.linkedin_post,
        campaign.image_url or None,
    )
```

### Credential shape from Story 21.1

Facebook Page credentials stored by Story 21.1:
```json
{"page_id": "...", "page_name": "...", "page_access_token": "..."}
```

### Page access token vs. user access token

Facebook Page posts MUST use a **page-level access token** (the `page_access_token` from
`/me/accounts`), NOT the user-level long-lived token. Story 21.1 stores the page-level token
correctly. Never use the user token for page posts -- it will return a permissions error.

### Message source: `linkedin_post`

Use `campaign.linkedin_post` as the Facebook post message.
Facebook Pages do not enforce a strict character limit on API posts (unlike X's 280 chars),
so no truncation needed.

### No DB changes needed

Story 21.1 handles the `facebook_page` enum value and credential storage. This story only
adds publishing logic.

### `_extract_error` helper

Already defined in `meta.py` by Story 21.2. Reuse it here.

---

## Tests Required

### Backend (pytest)

1. `test_publish_facebook_page_success` -- mock httpx; assert POST to /{page_id}/feed with
   correct message and access_token; assert post_id returned
2. `test_publish_facebook_page_with_image` -- assert `link` field included when image_url present
3. `test_publish_facebook_page_no_image` -- assert `link` field absent when image_url is None
4. `test_publish_facebook_page_401` -- mock 401; assert PlatformError(401) with reconnect message
5. `test_publish_facebook_page_no_linkedin_post` -- campaign without linkedin_post;
   assert "skipped" in results
6. `test_dispatch_publish_facebook_page_independence` -- facebook_page fails, instagram succeeds;
   assert other platform result is unaffected
