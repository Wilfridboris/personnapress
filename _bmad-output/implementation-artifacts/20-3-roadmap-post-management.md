---
baseline_commit: 8922ffcba7db95e0ab34fb9450a53c742a3dd964
---

# Story 20.3: Batch Scheduling, Post Management & Social Image Publishing

Status: done

## Story

As a PersonnaPress user,
I want approved roadmap posts to auto-schedule themselves across the week at platform-optimal times, and I want to manage each post individually after approval the same way I manage regular campaigns,
so that my content calendar fills itself and I never have to schedule posts manually or switch tools to post images.

## Acceptance Criteria

1. **POST /api/v1/roadmaps/{id}/approve**: Accepts `{excluded_campaign_ids: [UUID]}` (optional, defaults to empty list). Validates roadmap belongs to authenticated user. Sets all non-excluded child campaigns to `approved` status and schedules them via APScheduler (same persistent job mechanism as existing `schedule_campaign`). Updates `Roadmap.status = "approved"`. Returns `200 {"scheduled_count": N, "excluded_count": M}`.

2. **Scheduling distribution algorithm**: Posts are distributed Mon-Fri first; Sat-Sun used only if posts > 5. Platform-optimal times (UTC stored, displayed in user's account timezone): LinkedIn → 09:00; X → 08:00 / 12:00 / 17:00 cycling. Same-platform posts must be staggered minimum 2 hours apart on the same day. The week starts on `roadmap.week_start_date` (Monday). Distribution is deterministic: fill Mon first with each platform's first post, then Tue, etc., cycling through platforms before advancing to next day.

3. **Campaign list ROADMAP badge**: In the campaign list (`/campaigns`), campaigns where `roadmap_id IS NOT NULL` show a `"ROADMAP"` badge (Inter, 10px, uppercase, tracked, Border fill, Graphite text, 1px Border border, rounded-none) after the existing status badge. Existing layout, pagination, filtering unaffected. Backend `GET /api/v1/campaigns` response includes `roadmap_id` field on each campaign object.

4. **Content calendar roadmap posts**: `/calendar` shows roadmap-sourced campaigns with existing platform icons and scheduled time display. No calendar surface changes needed — roadmap campaigns are standard `Campaign` rows with `status=approved` and a scheduled job, which the existing calendar query already picks up.

5. **Individual post edit after approval**: A roadmap-sourced campaign opened from the campaign list uses the existing Approval Gate (`/campaigns/{id}`) unchanged. Edit, reschedule, and delete flows work identically to non-roadmap campaigns. No new surface needed.

6. **X media upload (INIT/APPEND/FINALIZE)**: `twitter.py` gains `upload_media(access_token: str, image_bytes: bytes, mime_type: str = "image/png") -> str` async function:
   - **INIT**: `POST https://api.x.com/2/media/upload` (form data, not JSON): `command=INIT`, `media_type={mime_type}`, `total_bytes={len(image_bytes)}`, `media_category=tweet_image`. Returns `{"data": {"id": "..."}}`. Extract `media_id = data["data"]["id"]`.
   - **APPEND**: Upload in chunks of 1MB: `POST https://api.x.com/2/media/upload` multipart form `command=APPEND`, `media_id={media_id}`, `segment_index={n}`, file chunk in `media` field.
   - **FINALIZE**: `POST https://api.x.com/2/media/upload` form data `command=FINALIZE`, `media_id={media_id}`.
   - Returns `media_id` string on success. Raises `PlatformError("X", status, detail)` on any non-2xx response.

7. **X tweet with image**: `twitter.py` gains `create_tweet_with_media(access_token: str, text: str, media_id: str) -> str` async function: `POST https://api.x.com/2/tweets` JSON body `{"text": text[:280], "media": {"media_ids": [media_id]}}`. Same headers and error handling as existing `create_tweet()`. Returns tweet ID.

8. **LinkedIn image upload**: `linkedin.py` gains `upload_image(access_token: str, author_urn: str, image_bytes: bytes) -> str` async function:
   - **Initialize**: `POST https://api.linkedin.com/rest/images?action=initializeUpload` with `{"initializeUploadRequest": {"owner": "urn:li:person:{author_urn}"}}`. Headers: `Authorization: Bearer`, `LinkedIn-Version: 202602`, `X-Restli-Protocol-Version: 2.0.0`, `Content-Type: application/json`. Returns `{"value": {"uploadUrl": "...", "image": "urn:li:image:..."}}`.
   - **Upload binary**: `PUT {uploadUrl}` with raw `image_bytes` in body (no auth header needed on the upload URL, it's pre-signed). `Content-Type: image/png`.
   - Returns image URN string `"urn:li:image:..."` on success. Raises `PlatformError("LinkedIn", status, detail)` on failure.

9. **LinkedIn post with image**: `linkedin.py` gains `create_post_with_image(access_token: str, author_urn: str, text: str, image_urn: str) -> str` async function: `POST https://api.linkedin.com/rest/posts` (NOT `ugcPosts` — `rest/posts` is the current endpoint for image posts) with body:
   ```json
   {
     "author": "urn:li:person:{author_urn}",
     "commentary": "{text}",
     "visibility": "PUBLIC",
     "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
     "content": {"media": {"altText": "Featured image", "id": "{image_urn}"}},
     "lifecycleState": "PUBLISHED",
     "isReshareDisabledByAuthor": false
   }
   ```
   Headers: `Authorization: Bearer`, `LinkedIn-Version: 202602`, `X-Restli-Protocol-Version: 2.0.0`. Returns post URN from `x-restli-id` response header. Raises `PlatformError` on non-201 response.

10. **Publishing service: image attachment flow**: `publishing.py` updated in `_publish_to_x()` and `_publish_to_linkedin()` so that when `campaign.image_url` is not None:
    - Download image bytes from the Supabase CDN URL: `httpx.get(campaign.image_url, timeout=15.0)`; on download failure → log `WARNING "image download failed for campaign {id}: {error}"` → fall back to text-only post (AC 11)
    - For X: call `upload_media(access_token, image_bytes)` → `create_tweet_with_media(access_token, text, media_id)`. On upload failure → fall back to text-only (AC 11)
    - For LinkedIn: get `author_urn` from `userinfo` sub (already fetched in existing `create_ugc_post`); call `upload_image(access_token, author_urn, image_bytes)` → `create_post_with_image(access_token, author_urn, text, image_urn)`. On upload failure → fall back to text-only (AC 11)
    - When `campaign.image_url` is None: use existing `create_tweet()` / `create_ugc_post()` text-only paths unchanged

11. **Image publish fallback**: If image download or platform image upload fails for any reason (exception OR non-2xx status), the post is published as text-only using the existing `create_tweet()` / `create_ugc_post()` functions. Campaign status is still set to `published`. A `WARNING` log is emitted: `"social image upload failed for campaign {id} on {platform}: {error} — falling back to text-only post"`. This fallback is silent to the user; no error badge shown.

12. **Existing `create_tweet()` and `create_ugc_post()` unchanged**: These text-only functions remain untouched. The image upload flow is additive — dispatched via an `if campaign.image_url` branch in the publishing service. No existing publishing tests break.

13. **Tests**: `test_twitter.py`: `test_upload_media_chunked` (mock httpx INIT→APPEND→FINALIZE; assert media_id returned); `test_create_tweet_with_media` (mock 201; assert `media_ids` in request body). `test_linkedin.py`: `test_upload_image` (mock initializeUpload + PUT; assert image_urn returned); `test_create_post_with_image` (mock 201; assert `content.media.id` in request body). `test_publishing.py`: `test_x_publish_with_image` (campaign with image_url; assert `create_tweet_with_media` called); `test_x_publish_image_download_failure` (image URL returns 404; assert `create_tweet` called as fallback); `test_linkedin_publish_image_upload_failure` (upload_image raises; assert `create_ugc_post` called as fallback).

14. **Approve endpoint auth guard**: `POST /api/v1/roadmaps/{id}/approve` validates that the authenticated user owns the roadmap (join `roadmaps` on `user_id`). Returns `HTTP 404` (not 403) if roadmap not found or not owned — consistent with project error response conventions.

## Tasks / Subtasks

- [x] Task 1: Approve endpoint and scheduling distribution (AC: 1, 2, 14)
  - [x] `routers/roadmaps.py`: add `POST /{roadmap_id}/approve` handler
    - Validate ownership (return 404 if not found/not owned)
    - Load all child campaigns with `roadmap_id = roadmap_id` and `id NOT IN excluded_campaign_ids`
    - Set each to `approved` status
    - Call scheduling distribution function to assign `scheduled_for` datetimes
    - For each campaign with a `scheduled_for`: create APScheduler job (same `schedule_campaign` helper as story 5-4); for campaigns with no `scheduled_for` (if fewer slots than posts): leave as `approved` (user can schedule manually)
    - Set `Roadmap.status = "approved"`
    - Return 200 with counts
  - [x] `services/roadmap.py`: add `distribute_schedule(campaigns, week_start_date) -> dict[UUID, datetime]` — pure function (no DB access) implementing the distribution algorithm: LinkedIn 09:00, X 08:00/12:00/17:00 cycling, Mon-Fri first, 2h minimum same-platform gap; returns `{campaign_id: scheduled_datetime}` mapping
  - [x] Unit test for `distribute_schedule` with various post count combinations

- [x] Task 2: Campaign list badge and content calendar (AC: 3, 4, 5)
  - [x] Backend: `GET /api/v1/campaigns` response — add `roadmap_id: Optional[UUID]` to campaign list item schema `CampaignListItem`; query already returns all campaign columns, just expose the field
  - [x] Frontend campaign list: in the campaign row component, if `campaign.roadmap_id` is present, render `"ROADMAP"` badge after the status badge (Paper Style: Border fill, Graphite text, 1px Border border, Inter 10px uppercase tracked, rounded-none)
  - [x] No calendar changes needed — roadmap campaigns appear automatically as scheduled/published campaigns in the existing month view

- [x] Task 3: X image upload functions (AC: 6, 7)
  - [x] `backend/app/integrations/twitter.py`: add `upload_media(access_token, image_bytes, mime_type="image/png") -> str`
    - INIT: POST to `https://api.x.com/2/media/upload` with form data (`command`, `media_type`, `total_bytes`, `media_category="tweet_image"`); extract `media_id` from `resp.json()["data"]["id"]`
    - APPEND: loop chunks of 1MB (`image_bytes[i:i+1_048_576]`); POST multipart form `command=APPEND`, `media_id`, `segment_index=n`, `files={"media": chunk}`
    - FINALIZE: POST form data `command=FINALIZE`, `media_id`
    - Raise `PlatformError("X", status, ...)` on any non-2xx; include step name in detail
  - [x] `twitter.py`: add `create_tweet_with_media(access_token, text, media_id) -> str` — copy `create_tweet()`, add `"media": {"media_ids": [media_id]}` to JSON body; keep `text[:280]` truncation
  - [x] Tests: `test_upload_media_chunked` and `test_create_tweet_with_media` (see AC 13)

- [x] Task 4: LinkedIn image upload functions (AC: 8, 9)
  - [x] `backend/app/integrations/linkedin.py`: add `upload_image(access_token, author_urn, image_bytes) -> str`
    - INIT: `POST https://api.linkedin.com/rest/images?action=initializeUpload` JSON `{"initializeUploadRequest": {"owner": "urn:li:person:{author_urn}"}}` with `LinkedIn-Version: 202602`, `X-Restli-Protocol-Version: 2.0.0` headers; extract `uploadUrl` and `image` URN from `resp.json()["value"]`
    - UPLOAD: `PUT {uploadUrl}` with `image_bytes` as body, `Content-Type: image/png` (no Authorization header — uploadUrl is pre-signed); expect 201 or 200
    - Return `image` URN string
    - Raise `PlatformError("LinkedIn", status, ...)` on failure
  - [x] `linkedin.py`: add `create_post_with_image(access_token, author_urn, text, image_urn) -> str`
    - `POST https://api.linkedin.com/rest/posts` (not ugcPosts)
    - Body per AC 9 spec; headers same as existing with `LinkedIn-Version: 202602`
    - Return `post_resp.headers.get("x-restli-id", "")`
    - Raise `PlatformError` on non-201
  - [x] Tests: `test_upload_image` and `test_create_post_with_image` (see AC 13)

- [x] Task 5: Publishing service image attachment (AC: 10, 11, 12)
  - [x] `services/publishing.py`: in `_publish_to_x()` (or wherever X publishing logic lives), add branch:
    ```python
    if campaign.image_url:
        try:
            img_resp = await httpx.AsyncClient().get(campaign.image_url, timeout=15.0)
            img_resp.raise_for_status()
            media_id = await twitter_integration.upload_media(access_token, img_resp.content)
            tweet_id = await twitter_integration.create_tweet_with_media(access_token, text, media_id)
        except Exception as e:
            logger.warning("social image upload failed for campaign %s on X: %s — falling back to text-only", campaign_id, e)
            tweet_id = await twitter_integration.create_tweet(access_token, text)
    else:
        tweet_id = await twitter_integration.create_tweet(access_token, text)
    ```
  - [x] Same pattern for LinkedIn in `_publish_to_linkedin()` using `upload_image` + `create_post_with_image` with fallback to `create_ugc_post`
  - [x] The `author_urn` for LinkedIn is already fetched inside `create_ugc_post` via `userinfo` endpoint; extract it to a shared helper `_get_linkedin_author_urn(access_token)` callable from both `create_ugc_post` and `create_post_with_image`
  - [x] Tests per AC 13: with-image path, download-failure fallback, upload-failure fallback

### Review Findings

- [x] [Review][Patch] Unclosed httpx.AsyncClient for image download — resource leak [backend/app/services/publishing.py:491,509,610,634]
- [x] [Review][Patch] APScheduler jobs registered before db.commit — phantom jobs on rollback [backend/app/routers/roadmaps.py:268]
- [x] [Review][Patch] No idempotency guard on approve_roadmap — double-approve creates duplicate DB job records [backend/app/routers/roadmaps.py:237]
- [x] [Review][Patch] Hour overflow in distribute_schedule — ValueError when hour>=24 [backend/app/services/roadmap.py:251]
- [x] [Review][Patch] Unguarded init_resp.json()["data"]["id"] in twitter.py — KeyError on unexpected API response [backend/app/integrations/twitter.py:72]
- [x] [Review][Patch] create_post_with_image error body access outside async with [backend/app/integrations/linkedin.py:108]

## Dev Notes

### X API Endpoint: api.x.com not upload.twitter.com
The X media upload endpoint has moved to `https://api.x.com/2/media/upload`. Do NOT use the old `upload.twitter.com/1.1/media/upload.json`. The new endpoint uses the same OAuth 2.0 Bearer token as tweet creation. The INIT/APPEND/FINALIZE commands are sent as form data (not JSON). The APPEND step sends chunks as multipart with `files={"media": chunk}` in httpx.

### LinkedIn: rest/posts vs ugcPosts
- Text-only posts: keep using `POST /v2/ugcPosts` (existing `create_ugc_post` — do not change)
- Image posts: use `POST /rest/posts` (new `create_post_with_image`)
- The `rest/posts` endpoint requires `LinkedIn-Version: 202602` and `X-Restli-Protocol-Version: 2.0.0` headers (same as current integration)
- Image URN format: `"urn:li:image:C4E10AQF..."` — returned by initializeUpload and passed directly to `content.media.id`
- Owner URN format: `"urn:li:person:{sub}"` where `sub` is the `sub` field from `/v2/userinfo` (already fetched in `create_ugc_post`)

### LinkedIn Image Upload: No Auth on PUT
The `uploadUrl` returned by initializeUpload is a pre-signed URL. The PUT request to upload the binary does NOT include an `Authorization` header — httpx should be called without auth for this step only. This is a common mistake.

### Scheduling Distribution: Deterministic Algorithm
The `distribute_schedule` function is a pure function for testability. No randomization. Posts are assigned deterministically:
- Sort platforms: blog_full first, then linkedin, then x
- Fill days Mon → Sun (use only Mon-Fri if total ≤ 5 posts)
- For each day, assign one post per platform at its optimal time
- If same platform needs multiple posts on the same day: stagger by 3 hours minimum (09:00 → 12:00 → 15:00 for LinkedIn)

### Fallback to Text-Only is Silent
The image fallback MUST NOT set campaign status to `failed` or show a platform error badge in the UI. The campaign is published successfully as text-only. Only a WARNING log is emitted server-side. This is correct behavior: content is published, image is bonus.

### Existing Test Coverage Preservation
The `create_tweet` and `create_ugc_post` functions are NOT modified. All existing tests for these functions continue to pass. New tests cover only the new `upload_media`, `create_tweet_with_media`, `upload_image`, `create_post_with_image` functions and the `if campaign.image_url` branch in publishing.py.

### Campaign List: roadmap_id Already in DB
After story 20-1, `campaigns.roadmap_id` column exists. The `GET /api/v1/campaigns` router only needs to expose it in the response schema. The frontend adds the badge based on its presence.

### Files Being Modified / Created

| File | Change |
|------|--------|
| `backend/app/routers/roadmaps.py` | Add `POST /{id}/approve` handler |
| `backend/app/services/roadmap.py` | Add `distribute_schedule()` pure function |
| `backend/app/schemas/campaign.py` | Add `roadmap_id: Optional[UUID]` to list response schema |
| `backend/app/routers/campaigns.py` | Expose `roadmap_id` in campaign list response |
| `backend/app/integrations/twitter.py` | Add `upload_media()`, `create_tweet_with_media()` |
| `backend/app/integrations/linkedin.py` | Add `upload_image()`, `create_post_with_image()`, extract `_get_linkedin_author_urn()` |
| `backend/app/services/publishing.py` | Add image attachment branch in X and LinkedIn publish paths |
| `frontend/app/(app)/campaigns/` (campaign row component) | Add ROADMAP badge when `roadmap_id` present |
| `backend/tests/integrations/test_twitter.py` | Add upload_media and create_tweet_with_media tests |
| `backend/tests/integrations/test_linkedin.py` | Add upload_image and create_post_with_image tests |
| `backend/tests/services/test_publishing.py` | Add with-image, download-fail, upload-fail tests |
| `backend/tests/services/test_roadmap_distribute.py` | New: unit tests for distribute_schedule |

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `approved` to `RoadmapStatus` enum and generated Alembic migration `20260727_1930_978fa9606dc3` to add `approved` to the PostgreSQL `roadmap_status_enum` type via `ALTER TYPE ... ADD VALUE IF NOT EXISTS`.
- Implemented `distribute_schedule()` pure function in `services/roadmap.py`: deterministic round-robin algorithm, 5-day Mon-Fri window for ≤5 posts, 7-day Mon-Sun for >5 posts, X cycling 08:00/12:00/17:00, LinkedIn/blog_full base 09:00, 3h stagger for same-platform same-day collisions.
- Added `POST /api/v1/roadmaps/{id}/approve` endpoint: validates ownership (404 not 403), sets campaigns to approved, calls distribute_schedule, creates APScheduler jobs via existing `run_publish` + DateTrigger pattern, sets Roadmap.status = approved.
- Added `roadmap_id: Optional[UUID]` to `CampaignResponse` schema (already in DB, just exposed). Updated frontend `Campaign` type and added ROADMAP badge in campaigns list page.
- Added `upload_media()` (INIT/APPEND/FINALIZE chunked) and `create_tweet_with_media()` to `twitter.py`.
- Added `_get_linkedin_author_urn()` helper, `upload_image()` (initializeUpload + pre-signed PUT), and `create_post_with_image()` to `linkedin.py`. Refactored `create_ugc_post()` to use the shared helper.
- Updated both `dispatch_publish()` and `dispatch_publish_for_platform()` in `publishing.py` with `if campaign.image_url` branch for X and LinkedIn — downloads image, attempts image post, falls back silently to text-only on any exception.
- 63 tests pass: 14 distribute_schedule tests, 6 X integration tests, 6 LinkedIn integration tests, 37 publishing service tests (all existing tests green).

### File List

- `backend/app/db/repositories/models.py` — added `approved` to `RoadmapStatus` enum
- `backend/alembic/versions/20260727_1930_978fa9606dc3_add_approved_to_roadmap_status.py` — new migration
- `backend/app/services/roadmap.py` — added `distribute_schedule()` + helpers
- `backend/app/routers/roadmaps.py` — added `POST /{roadmap_id}/approve` endpoint, request/response models
- `backend/app/schemas/campaign.py` — added `roadmap_id: Optional[UUID]` to `CampaignResponse`
- `backend/app/integrations/twitter.py` — added `upload_media()`, `create_tweet_with_media()`
- `backend/app/integrations/linkedin.py` — added `_get_linkedin_author_urn()`, `upload_image()`, `create_post_with_image()`; refactored `create_ugc_post()`
- `backend/app/services/publishing.py` — added `import httpx`; image upload branches in `dispatch_publish()` and `dispatch_publish_for_platform()` for X and LinkedIn
- `frontend/lib/types.ts` — added `roadmap_id: string | null` to `Campaign` interface
- `frontend/app/(app)/campaigns/page.tsx` — added ROADMAP badge when `campaign.roadmap_id` present
- `backend/tests/services/test_roadmap_distribute.py` — new: 14 unit tests for `distribute_schedule`
- `backend/tests/integrations/test_twitter.py` — new: 6 tests for `upload_media`, `create_tweet_with_media`
- `backend/tests/integrations/test_linkedin.py` — new: 6 tests for `upload_image`, `create_post_with_image`
- `backend/tests/services/test_publishing.py` — added 4 image-path tests

## Change Log

- 2026-07-27: Story implemented. Approve endpoint with batch scheduling, roadmap_id badge in campaign list, X and LinkedIn image upload functions, publishing service image attachment with silent text-only fallback. Alembic migration for `approved` roadmap status. 63 tests added/passing.
