---
baseline_commit: 0959709
---

# Story 21.15: Social Platform Publishing Bug Fixes

Status: done

---

## Story

As a PersonnaPress user publishing to Facebook,
I want my image to appear as a native Facebook photo post,
so that clicking the post opens the photo viewer instead of redirecting to a Supabase storage URL.

As a PersonnaPress user publishing to X (Twitter),
I want to know when my image could not be attached to a tweet,
so that I am not surprised by a text-only post with no explanation.

As a PersonnaPress user publishing to Threads,
I want my campaign image attached to my Threads post,
so that the post has visual presence on the platform.

As a PersonnaPress user who has hit their image generation limit,
I want to see a clear explanation in the campaign approval gate,
so that I know why no image was generated and how to get more.

As a PersonnaPress user reviewing a social-only campaign,
I want the campaign page to be titled "Social Campaign" (not "X Post"),
so that the title reflects the actual content type.

---

## Context and Motivation

Story 21-14 shipped AI image generation and upload for social-only campaigns. After observing real publishing results, five bugs were identified:

1. **Facebook image links to Supabase** -- `publish_facebook_page_post` uses `payload["link"] = image_url` on the `/feed` endpoint. This creates a link-preview card where the Supabase URL IS the click destination. Meta's servers fetch the thumbnail from that URL, but clicking the card/image in the feed redirects the viewer to the raw Supabase storage URL. Fix: switch to `/{page_id}/photos` with `url=image_url` -- Meta fetches and hosts the image natively; clicking opens the Facebook photo viewer with no external redirect.

2. **X image silently falls back to text** -- `dispatch_publish` / `dispatch_publish_for_platform` both catch `Exception` on the image upload path and fall back to `create_tweet` with no `exc_info=True` on the warning log, making the root cause invisible in production. Additionally, no user-facing signal is emitted when the fallback fires. `media.write` IS already in the PKCE scope list (`frontend/app/api/auth/x/route.ts:15`), so scope is not the issue -- the error must be diagnosed via logs.

3. **Threads: no image** -- `publish_threads_post` uses `media_type=TEXT` unconditionally. The Threads API supports `media_type=IMAGE` with an `image_url` parameter using the same 2-step container+publish pattern. This is the only platform where we have the infrastructure (image_url on campaign) but do not use it.

4. **Image limit: silent failure** -- When `check_image_limit` raises in `run_image_generation` (`image.py:158-167`), the job is set to `complete` with `error_details` left as `None`. The ImagePanel renders "No featured image yet." with no indication of why. The user does not know they hit their plan limit.

5. **Campaign title "X Post"** -- `getCampaignTitle` in `ApprovalGateClient.tsx:49` returns `"X Post"` for any `social_only` campaign that has an `x_post` field -- even when Instagram, Facebook, and Threads are also being published. The title should reflect campaign type, not a single content field.

**No DB migration required.** No new columns, no new tables.

---

## Acceptance Criteria

### AC 1: Facebook posts image natively (no Supabase redirect)

**Given** a campaign with `image_url` set and Facebook Page connected,
**When** the user publishes to Facebook Page,
**Then** `publish_facebook_page_post` calls `POST /v21.0/{page_id}/photos` with `url={image_url}`, `caption={message}`, `published=true`, and `access_token={page_access_token}`.
**And** the response `id` is returned as the post identifier.
**And** clicking the post or image in the Facebook feed opens the Facebook photo viewer (no external URL redirect).

**Given** a campaign with no `image_url`,
**When** the user publishes to Facebook Page,
**Then** `publish_facebook_page_post` falls back to `POST /v21.0/{page_id}/feed` with `message={text}` only (text-only post, no link field).

### AC 2: X image upload failure is logged and surfaced

**Given** image upload to X fails for any reason,
**When** the fallback to text-only fires,
**Then** the warning log call includes `exc_info=True` so the full traceback is captured.
**And** the publish result for the `x` platform is `"success_text_only"` (not `"success"`), distinguishable in the publish results dict.
**And** after publishing, a frontend toast reads: "X post published -- image could not be attached."

**Given** image upload to X succeeds,
**When** `create_tweet_with_media` completes,
**Then** the publish result is `"success"` (unchanged behavior).

### AC 3: Threads posts image when image_url is present

**Given** a campaign with `image_url` set and Threads connected,
**When** the user publishes to Threads,
**Then** `publish_threads_post` creates a container via `POST /{threads_user_id}/threads` with `media_type=IMAGE`, `image_url={image_url}`, `text={text}`, and `access_token={user_access_token}`.
**And** the 30-second processing wait is preserved before `threads_publish`.
**And** if the image container creation fails (`PlatformError`), the function raises (no silent fallback to text -- let the caller handle retry).

**Given** a campaign with no `image_url` and Threads connected,
**When** the user publishes to Threads,
**Then** `publish_threads_post` creates a container with `media_type=TEXT` and `text={text}` (unchanged behavior).

**Note:** The Threads API requires `image_url` to be a publicly accessible URL. The Supabase bucket must not gate this URL with auth. Verify this is the case -- the same constraint exists for Instagram (already working).

### AC 4: Image limit shows user-facing explanation

**Given** `check_image_limit` raises in `run_image_generation` (user is at plan limit),
**When** the image generation worker handles the exception,
**Then** `job.error_details` is set to `"Image generation skipped: you have reached your plan limit for image generations this billing cycle."` before `job.status = "complete"` is committed.

**Given** `job.error_details` contains the string `"image generation skipped"` (case-insensitive),
**When** the campaign approval gate renders with `jobErrorDetails` set to this string,
**Then** `ImagePanel` shows the message: `"Image limit reached for this billing cycle."` followed by an inline link `"Upgrade your plan"` pointing to `/account#choose-plan`.
**And** the "Generate image" button remains visible so the user can try again after upgrading.

**Given** `job.error_details` contains `"Image generation failed"` (existing failure path, unchanged),
**When** `ImagePanel` renders,
**Then** the existing message `"Image generation failed. Blog and social posts are complete."` is shown (no regression).

### AC 5: Social campaign page title is "Social Campaign"

**Given** a campaign with `campaign_type === "social_only"` or `roadmap_id` set and no `blog_html`,
**When** the `ApprovalGateClient` renders,
**Then** `getCampaignTitle` returns `"Social Campaign"` regardless of which post fields (`x_post`, `linkedin_post`) are populated.

**Given** a campaign with `blog_html` set (blog_full or blog_full+social),
**When** `getCampaignTitle` is called,
**Then** it returns `"Campaign"` (unchanged).

---

## Files to Modify

### Backend

| File | Change |
|---|---|
| `backend/app/integrations/meta.py` | `publish_facebook_page_post`: switch from `/feed`+`link` to `/photos`+`url`+`caption`+`published=true` for image path; text-only path uses `/feed`+`message` only. `publish_threads_post`: add `image_url: Optional[str] = None` param; branch on `media_type=IMAGE` vs `TEXT`. |
| `backend/app/services/image.py` | `run_image_generation`: set `job.error_details` before commit when image limit hit. |
| `backend/app/services/publishing.py` | X platform branch (both `dispatch_publish_for_platform` and `dispatch_publish`): add `exc_info=True` to warning log; return `"success_text_only"` on fallback. Threads branch (both functions): pass `image_url=campaign.image_url or None` to `publish_threads_post`. |

### Frontend

| File | Change |
|---|---|
| `frontend/components/campaigns/ImagePanel.tsx` | Add `IMAGE_LIMIT` branch in the no-image state: check `jobErrorDetails` for `"image generation skipped"` (case-insensitive) and show limit message + upgrade link. |
| `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` | `getCampaignTitle`: return `"Social Campaign"` for social_only/roadmap social path. |
| `frontend/components/publishing/RetryPanel.tsx` or toast emit path | Show `"X post published -- image could not be attached."` toast when X result is `"success_text_only"`. |

---

## Dev Notes

### AC 1 -- Facebook `/photos` implementation

Replace the entire `publish_facebook_page_post` body:

```python
async def publish_facebook_page_post(
    page_id: str,
    page_access_token: str,
    message: str,
    image_url: Optional[str] = None,
) -> str:
    """Post to a Facebook Page feed. Returns post ID.

    With image: POST /{page_id}/photos (url + caption + published=true).
    Text only: POST /{page_id}/feed (message only, no link field).
    """
    if image_url:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{META_GRAPH_BASE}/{page_id}/photos",
                data={
                    "url": image_url,
                    "caption": (message or ""),
                    "published": "true",
                    "access_token": page_access_token,
                },
            )
    else:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{META_GRAPH_BASE}/{page_id}/feed",
                data={
                    "message": (message or ""),
                    "access_token": page_access_token,
                },
            )
    if resp.status_code == 429:
        raise PlatformError("facebook_page", 429, "Facebook Page rate limit reached")
    if resp.status_code == 401:
        raise PlatformError("facebook_page", 401, "Facebook Page connection expired - reconnect in Connections")
    if resp.status_code != 200:
        raise PlatformError("facebook_page", resp.status_code, _extract_error(resp))
    post_id = resp.json().get("id", "")
    if not post_id:
        raise PlatformError("facebook_page", 200, "post returned no id")
    return post_id
```

**Permissions note:** `/photos` uses the same `pages_manage_posts` permission already granted. No OAuth change needed.

**`META_GRAPH_BASE`**: already defined in `meta.py` as `https://graph.facebook.com/v21.0` (or current version). Use as-is.

### AC 3 -- Threads image implementation

```python
async def publish_threads_post(
    threads_user_id: str,
    user_access_token: str,
    text: str,
    image_url: Optional[str] = None,
) -> str:
    """Create and publish a Threads post. Returns Threads post ID.

    With image_url: IMAGE container. Without: TEXT container.
    """
    container_data: dict = {
        "text": (text or ""),
        "access_token": user_access_token,
    }
    if image_url:
        container_data["media_type"] = "IMAGE"
        container_data["image_url"] = image_url
    else:
        container_data["media_type"] = "TEXT"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{THREADS_GRAPH_BASE}/{threads_user_id}/threads",
            data=container_data,
        )
    if resp.status_code != 200:
        raise PlatformError("threads", resp.status_code, _extract_error(resp))
    container_id = resp.json().get("id", "")
    if not container_id:
        raise PlatformError("threads", 200, "threads container creation returned no id")

    # Poll for container readiness instead of a fixed sleep.
    # TEXT containers are instant; IMAGE containers can take 10-60s to process.
    # Mirror the same polling pattern used in publish_instagram_feed_post.
    for attempt in range(15):
        await asyncio.sleep(5)
        async with httpx.AsyncClient(timeout=10.0) as status_client:
            status_resp = await status_client.get(
                f"{THREADS_GRAPH_BASE}/{container_id}",
                params={"fields": "status,error_message", "access_token": user_access_token},
            )
        if status_resp.status_code != 200:
            raise PlatformError("threads", status_resp.status_code, _extract_error(status_resp))
        status_data = status_resp.json()
        status = status_data.get("status", "")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise PlatformError(
                "threads", 500,
                f"Threads container processing failed: {status_data.get('error_message', 'unknown error')}",
            )
        # IN_PROGRESS or PUBLISHED -- keep polling
    else:
        raise PlatformError("threads", 500, "Threads container did not finish processing after 75s")

    async with httpx.AsyncClient(timeout=15.0) as client:
        pub_resp = await client.post(
            f"{THREADS_GRAPH_BASE}/{threads_user_id}/threads_publish",
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

**Note on polling vs sleep:** The original TEXT path uses a fixed `asyncio.sleep(30)`. IMAGE containers take variable time (5-60s). The polling loop above checks every 5s up to 15 times (75s max), mirroring `publish_instagram_feed_post`. For TEXT containers the status will be `FINISHED` on the first poll, so there is no regression on the existing TEXT path -- the sleep is replaced by a single 5s wait + one status check.

Both `dispatch_publish_for_platform` (line ~621) and `dispatch_publish` (line ~798) call `publish_threads_post` -- update both call sites to pass `image_url=campaign.image_url or None`.

### AC 2 -- X image fallback changes

In both `dispatch_publish_for_platform` (lines ~546-560) and `dispatch_publish` (lines ~709-723):

```python
if campaign.image_url:
    try:
        async with httpx.AsyncClient(timeout=15.0) as _img_client:
            img_resp = await _img_client.get(campaign.image_url)
        img_resp.raise_for_status()
        media_id = await twitter_integration.upload_media(creds["access_token"], img_resp.content)
        await twitter_integration.create_tweet_with_media(creds["access_token"], campaign.x_post, media_id)
    except Exception as exc:
        logger.warning(
            "social image upload failed for campaign %s on X: %s -- falling back to text-only post",
            campaign_id, exc,
            exc_info=True,   # ADD THIS
        )
        await twitter_integration.create_tweet(creds["access_token"], campaign.x_post)
        return {platform: "success_text_only"}   # dispatch_publish_for_platform path
        # (dispatch_publish path: results[platform] = "success_text_only"; continue)
else:
    await twitter_integration.create_tweet(creds["access_token"], campaign.x_post)
```

Note: The em-dash in the current warning log string `"— falling back"` must be replaced with `"--"` per project-wide no-em-dash rule.

**Frontend toast for `"success_text_only"`:** Find where publish results are consumed after `dispatch_publish` completes (the approval panel publish handler). When the `x` key in results equals `"success_text_only"`, emit a toast: `"X post published -- image could not be attached."`. This is additive (existing success toast still fires for overall success).

Locate the publish result handling in `approval-panel.tsx` (look for the POST to `/campaigns/{id}/approve` or similar publish endpoint) and the toast logic that follows.

### AC 4 -- Image limit error_details

In `image.py`, replace the image-limit catch block:

```python
    except HTTPException:
        logger.warning(
            "run_image_generation: image limit reached for user %s, skipping", user_id
        )
        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        job.error_details = (
            "Image generation skipped: you have reached your plan limit for image generations "
            "this billing cycle."
        )
        await db.commit()
        return
```

In `ImagePanel.tsx`, extend the no-image branch:

```tsx
const isLimitReached = (jobErrorDetails ?? "").toLowerCase().includes("image generation skipped");
const isGenerationFailed = (jobErrorDetails ?? "").includes("Image generation failed");

// In render:
<p className="font-mono text-sm text-graphite">
  {isLimitReached
    ? "Image limit reached for this billing cycle."
    : isGenerationFailed
    ? "Image generation failed. Blog and social posts are complete."
    : "No featured image yet."}
</p>
{isLimitReached && (
  <p className="font-mono text-xs text-graphite mt-1">
    <a
      href="/account#choose-plan"
      className="underline hover:text-ink transition-colors"
    >
      Upgrade your plan
    </a>{" "}
    to generate more images.
  </p>
)}
```

### AC 5 -- Campaign title fix

In `ApprovalGateClient.tsx`:

```tsx
function getCampaignTitle(campaign: Campaign): string {
  if (campaign.blog_html) return "Campaign";
  if (campaign.roadmap_id || campaign.campaign_type === "social_only") {
    return "Social Campaign";
  }
  return "Generating...";
}
```

### Publishing service: both code paths

`publishing.py` has **two** X publish code paths that are near-identical:
- `dispatch_publish_for_platform` (~line 541) -- single-platform retry path
- `dispatch_publish` (~line 700) -- full multi-platform publish path

And **two** Threads code paths:
- `dispatch_publish_for_platform` (~line 616)
- `dispatch_publish` (~line 792)

**Both paths must be updated for AC 2 and AC 3.** Do not miss the retry path.

### No-em-dash rule

All string literals in new/modified Python and TypeScript code must use `--` not `—`. The existing warning log at line ~718 uses an em-dash in `"— falling back"` -- replace it in this story.

---

## Tests to Write / Update

### Backend (`backend/tests/`)

**`test_meta_integration.py`** (existing file, extend):
- `test_publish_facebook_page_post_with_image_uses_photos_endpoint` -- mock `httpx.AsyncClient.post`, assert URL contains `/photos`, assert payload has `url`, `caption`, `published`.
- `test_publish_facebook_page_post_no_image_uses_feed_endpoint` -- assert URL contains `/feed`, assert payload has `message` only (no `link`, no `url`).
- `test_publish_threads_post_with_image` -- assert container payload has `media_type=IMAGE` and `image_url`.
- `test_publish_threads_post_text_only` -- assert container payload has `media_type=TEXT`, no `image_url`.

**`test_image.py`** (existing file, extend):
- `test_run_image_generation_limit_reached_sets_error_details` -- mock `check_image_limit` to raise `HTTPException`, assert `job.error_details` contains `"image generation skipped"` and `job.status == "complete"`.

### Frontend (`frontend/__tests__/`)

**`ImagePanel.test.tsx`** (if exists) or new:
- `test_shows_limit_reached_message_when_error_details_contains_skipped` -- render with `jobErrorDetails="Image generation skipped: ..."`, assert message and upgrade link visible.
- `test_shows_generation_failed_message_unchanged` -- render with `jobErrorDetails="Image generation failed..."`, assert existing message (regression guard).
- `test_shows_no_image_yet_when_no_error_details` -- render with `jobErrorDetails=null`, assert "No featured image yet." (regression guard).

**`ApprovalGateClient.test.tsx`** (if exists) or inline:
- `test_getCampaignTitle_social_only_returns_social_campaign` -- assert returns `"Social Campaign"` when `campaign_type="social_only"` with `x_post` set.
- `test_getCampaignTitle_with_blog_html_returns_campaign` -- regression guard.

---

## What is NOT in Scope

- Platform-native content generation (separate `instagram_caption`, `facebook_post`, `threads_post` fields) -- Story 21-16
- Instagram 1:1 square image generation -- Story 21-17
- Investigating root cause of X image upload 403 beyond adding `exc_info=True` -- the log will reveal it; a follow-up patch can fix if needed
- Instagram "contenu d'IA" (AI content label) -- Meta platform behavior, not controllable via API
- Any Alembic migrations
- Any new API endpoints

---

## File List

### Modified
- `backend/app/integrations/meta.py` -- `publish_facebook_page_post` switched to `/photos` for image path; `publish_threads_post` added `image_url` param and IMAGE/TEXT branching with polling loop replacing fixed sleep
- `backend/app/services/image.py` -- `run_image_generation` image-limit catch block now sets `job.error_details` before commit
- `backend/app/services/publishing.py` -- both `dispatch_publish_for_platform` and `dispatch_publish`: X path adds `exc_info=True` + `"success_text_only"` fallback result; Threads call sites pass `image_url=campaign.image_url or None`
- `frontend/components/campaigns/ImagePanel.tsx` -- no-image branch checks `jobErrorDetails` for limit reached vs generation failed vs no error
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` -- `getCampaignTitle` returns `"Social Campaign"` for social_only/roadmap
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` -- `nonSkippedValues` filter excludes `"success_text_only"`; X `"success_text_only"` result emits info toast

### Added (Tests)
- `backend/tests/test_meta_integration.py` -- updated + new tests for Facebook `/photos` endpoint, Threads IMAGE container, X fallback returning `"success_text_only"`, `dispatch_publish_for_platform` X fallback
- `backend/tests/services/test_image.py` -- updated + new test asserting `job.error_details` set on image limit hit
- `frontend/__tests__/components/campaigns/ImagePanel.test.tsx` -- 3 tests: limit reached message, generation failed message, no error "no image yet"
- `frontend/__tests__/app/campaigns/ApprovalGateClient.test.tsx` -- 3 tests: social_only title, roadmap title, blog_html title

---

## Dev Agent Record

### Completion Notes

- Both `dispatch_publish_for_platform` and `dispatch_publish` in `publishing.py` were updated independently; they are near-identical code paths for single-platform retry vs full publish.
- Threads polling loop mirrors Instagram pattern (15 iterations x 5s = 75s max). TEXT containers finish on the first poll so there is no regression on existing text path.
- The `"success_text_only"` result is explicitly excluded from `nonSkippedValues` in `approval-panel.tsx` so it does not trigger the "all platforms already published" branch.
- `getCampaignTitle` regression: checking `blog_html` first ensures full-blog campaigns return "Campaign" even if `roadmap_id` is somehow set.
- All 102 backend tests pass. All 6 new frontend tests pass.

### Debug Log

- `test_dispatch_publish_instagram_platform_independence` failed because it set `campaign.image_url` but did not mock the httpx download -- the X image path threw → `"success_text_only"`. Fixed by adding httpx, `upload_media`, and `create_tweet_with_media` mocks.
- `test_publish_threads_success` failed because new polling code calls `status_client.get(...)` which was not mocked. Fixed by adding `mock_client.get = AsyncMock(return_value=status_finished)`.
- `test_dispatch_publish_for_platform_x_image_fallback_returns_success_text_only` had wrong arity (4 args). `dispatch_publish_for_platform` takes `(db, campaign_id, platform)`. Removed spurious `job_id` arg.

---

## Review Findings

- [x] [Review][Patch] "No image" badge shows on social_only campaigns that legitimately have no image [`frontend/components/campaigns/CampaignList.tsx`] — added `campaign.campaign_type !== "social_only"` guard + regression test
- [x] [Review][Patch] LinkedIn em-dash in warning logs — both `dispatch_publish_for_platform` (line ~585) and `dispatch_publish` (line ~759) use `— falling back` instead of `-- falling back` per project no-em-dash rule [`backend/app/services/publishing.py:585,759`]
- [x] [Review][Patch] `isGenerationFailed` case-sensitive while `isLimitReached` is case-insensitive — changed to `.toLowerCase().includes("image generation failed")` for consistency [`frontend/components/campaigns/ImagePanel.tsx`]
- [x] [Review][Defer] Threads poll loop first-iteration sleep (5s) unnecessary for TEXT containers — TEXT containers are instant per Threads API docs; sleeping 5s before first poll adds avoidable latency on every TEXT post [`backend/app/integrations/meta.py`] — deferred, pre-existing pattern matching Instagram
- [x] [Review][Defer] `asyncio.gather` cancel-both-on-failure behavior — if fidelity check or social gen raises, the other task is cancelled; previously the two were sequential so a fidelity failure would also stop social, making this equivalent, but `return_exceptions=True` would allow partial results [`backend/app/services/generation.py`] — deferred, equivalent to prior sequential behavior
- [x] [Review][Defer] Threads poll unknown terminal status causes misleading timeout — status values other than `FINISHED`/`ERROR` (e.g. `CANCELLED`) exhaust all 15 iterations and raise "did not finish after 75s" rather than surfacing the real status [`backend/app/integrations/meta.py`] — deferred, defensive edge case
- [x] [Review][Defer] `status_resp.json()` lacks non-JSON body guard in Threads poll — 200 with HTML/CDN error body raises `JSONDecodeError` instead of `PlatformError` [`backend/app/integrations/meta.py`] — deferred, same pattern used elsewhere in integrations
- [x] [Review][Defer] Threads timeout error message "75s" understates actual worst-case — 15 iterations × (5s sleep + 10s GET timeout) = 225s possible; "75s" is only the sleep component [`backend/app/integrations/meta.py`] — deferred, cosmetic inaccuracy

---

## Change Log

| Date | Change |
|---|---|
| 2026-08-14 | Implemented all 5 ACs; all backend and frontend tests pass; status set to review |
| 2026-08-14 | Code review: 3 patches, 5 deferred, 8 dismissed |
