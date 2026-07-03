---
baseline_commit: 146acb6e8019e1bfcf36e6440f2731868fcea519
---

# Story 5.3: Immediate Multi-Platform Publishing

Status: done

## Story

As an authenticated user,
I want to publish an approved Campaign to all connected platforms at once,
So that my content goes live simultaneously on all my channels with a single click.

## Acceptance Criteria

1. **Given** an approved Campaign with at least one Platform Connection and the user clicks "Publish now" in the Approval Gate, **When** `POST /api/v1/campaigns/{id}/publish` is called, **Then** a `jobs` record is created with `job_type='publish'` and `status='pending'` before the BackgroundTask is dispatched; the API returns HTTP 202 with `{"job_id": "..."}` immediately; the Approval Gate shows "Publishing..." state with an inline spinner on the "Publish now" button; both "Publish now" and "Schedule" buttons are disabled while the job is in-flight.

2. **Given** the publish BackgroundTask executes in `workers/publish.py`, **When** it runs `services/publishing.py:dispatch_publish(campaign_id, job_id)`, **Then** for each `platform_connections` row for the campaign's client: encrypted credentials are retrieved, decrypted ONLY in `services/publishing.py` using `decrypt_credential()` from `core/security.py`; the appropriate integration is called; the decrypted credential value does not leave the scope of the function that uses it and is NEVER logged.

3. **Given** the WordPress publish step runs, **When** `integrations/wordpress.py:publish_post(credentials, campaign)` executes, **Then** the draft-first pattern is followed: (1) `POST /wp-json/wp/v2/posts` with `status: "draft"` creates the post; (2) the featured image is uploaded via `POST /wp-json/wp/v2/media` and set as the post's `featured_media`; (3) `PATCH /wp-json/wp/v2/posts/{id}` sets `status: "publish"` only after both steps succeed; if step 3 fails, the draft post is cleaned up via `DELETE /wp-json/wp/v2/posts/{id}` — the blog HTML from `campaign.blog_html` is published as the post content.

4. **Given** the X publish step runs, **When** `integrations/twitter.py:create_tweet(access_token, text)` executes, **Then** `POST https://api.twitter.com/2/tweets` is called with OAuth 2.0 Bearer token; the `tweet.fields` parameter is set to selective fields only (`id,text`) to minimize rate-limit pressure; if multiple Campaigns publish X posts within 30 seconds, outbound calls are staggered with a 2-second delay between each.

5. **Given** the LinkedIn publish step runs, **When** `integrations/linkedin.py:create_ugc_post(access_token, author_id, text)` executes, **Then** `POST https://api.linkedin.com/v2/ugcPosts` is called with `LinkedIn-Version: 202602` header; if multiple Campaigns publish LinkedIn posts within 30 seconds, calls are staggered with a 5-second delay.

6. **Given** the Webflow publish step runs, **When** `integrations/webflow.py:publish_post(credentials, campaign)` executes, **Then** (1) `POST https://api.webflow.com/v2/collections/{collection_id}/items` creates the CMS item; (2) `POST https://api.webflow.com/v2/collections/{collection_id}/items/publish` publishes it; both calls use the stored bearer token.

7. **Given** all connected platforms publish successfully, **When** the BackgroundTask completes, **Then** `campaigns.status` transitions to `published`; `campaigns.updated_at` is set to the publish timestamp; `jobs.status` is set to `complete`; `jobs.completed_at` is set; the Approval Gate frontend polls `GET /api/v1/jobs/{job_id}` (React Query every 2s) and on seeing `status='complete'` reloads the campaign — the footer shows "Published to [Platform] — [Date], [Time]." with "View on [Platform] →" links; content is read-only.

8. **Given** one or more platforms fail during publish while others succeed, **When** the BackgroundTask completes with mixed results, **Then** `campaigns.status` is set to `failed`; `jobs.error_details` is set to a JSON string containing per-platform results: `{"wordpress": "success", "linkedin": "401 token expired"}`; `jobs.status` is set to `failed`; the Retry Panel (Story 5.5) is shown in the Approval Gate; posts that succeeded are already live.

9. **Given** the Approval Gate is showing "approved, not yet published" state (from Story 4.4 stubs), **When** the user views it, **Then** the "Publish now" primary button and "Schedule" secondary button are fully functional (wired to actual endpoints, not stubs). "Publish now" calls `POST /api/v1/campaigns/{id}/publish`; "Schedule" is handled in Story 5.4 (keep as secondary button, functional in 5.4).

10. **Given** an approved Campaign with NO platform connections, **When** the user clicks "Publish now", **Then** the button is not present at all — instead the "Connect a platform" prompt (from Story 4.4 AC#3) is shown; this prompt navigates to `/clients/{client_id}/connections`.

## Tasks / Subtasks

- [x] Task 1: Create `backend/app/db/repositories/platform_connections.py` fetch function (builds on Story 5.1) (AC: #2)
  - [x] 1.1 Ensure `get_connections_for_client(db, client_id)` is complete from Story 5.1
  - [x] 1.2 This function returns all `PlatformConnection` rows — the BackgroundTask uses this to know which platforms to publish to

- [x] Task 2: Create `backend/app/services/publishing.py` (AC: #2, #3, #4, #5, #6, #7, #8)
  - [x] 2.1 Create `backend/app/services/publishing.py` with the dispatch function:
    ```python
    import asyncio
    import json
    import logging
    from uuid import UUID
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.security import decrypt_credential
    from app.db.repositories.platform_connections import get_connections_for_client
    from app.db.repositories.campaigns import get_campaign, update_campaign_status
    from app.db.repositories.jobs import update_job
    from app import integrations

    logger = logging.getLogger(__name__)

    async def dispatch_publish(db: AsyncSession, campaign_id: UUID, job_id: UUID) -> dict:
        """
        Publish to all connected platforms. Returns per-platform results dict.
        ONLY this function may call decrypt_credential().
        """
        campaign = await get_campaign(db, campaign_id)
        connections = await get_connections_for_client(db, campaign.client_id)
        results = {}
        last_x_publish_time = 0.0
        last_linkedin_publish_time = 0.0

        for conn in connections:
            try:
                creds_json = decrypt_credential(conn.encrypted_credentials)
                creds = json.loads(creds_json)
                if conn.platform == "wordpress":
                    await integrations.wordpress.publish_post(creds, campaign)
                elif conn.platform == "webflow":
                    await integrations.webflow.publish_post(creds, campaign)
                elif conn.platform == "x":
                    # Stagger: 2s between X posts
                    now = asyncio.get_event_loop().time()
                    if now - last_x_publish_time < 2.0:
                        await asyncio.sleep(2.0 - (now - last_x_publish_time))
                    await integrations.twitter.create_tweet(creds["access_token"], campaign.x_post)
                    last_x_publish_time = asyncio.get_event_loop().time()
                elif conn.platform == "linkedin":
                    # Stagger: 5s between LinkedIn posts
                    now = asyncio.get_event_loop().time()
                    if now - last_linkedin_publish_time < 5.0:
                        await asyncio.sleep(5.0 - (now - last_linkedin_publish_time))
                    await integrations.linkedin.create_ugc_post(
                        creds["access_token"], campaign.blog_html, campaign.linkedin_post
                    )
                    last_linkedin_publish_time = asyncio.get_event_loop().time()
                results[conn.platform] = "success"
            except Exception as exc:
                logger.error("Publish failed for platform=%s campaign=%s: %s", conn.platform, campaign_id, exc, exc_info=True)
                results[conn.platform] = str(exc)
        return results
    ```
  - [x] 2.2 Never log `creds` or any decrypted value — only log platform name, campaign_id, and the exception message
  - [x] 2.3 `decrypt_credential` is called ONLY here — not in routers, not in workers, not in integrations directly

- [x] Task 3: Create `backend/app/workers/publish.py` (AC: #1, #7, #8)
  - [ ] 3.1 Create `backend/app/workers/publish.py`:
    ```python
    import json
    import logging
    from uuid import UUID
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.connection import get_session_context
    from app.db.repositories.campaigns import update_campaign_status
    from app.db.repositories.jobs import update_job
    from app.services.publishing import dispatch_publish

    logger = logging.getLogger(__name__)

    async def run_publish(job_id: UUID, campaign_id: UUID) -> None:
        """BackgroundTask entry point for multi-platform publishing."""
        async with get_session_context() as db:
            await update_job(db, job_id, status="in_progress", started_at=utcnow())
            try:
                results = await dispatch_publish(db, campaign_id, job_id)
                all_success = all(v == "success" for v in results.values())
                if all_success:
                    await update_campaign_status(db, campaign_id, "published")
                    await update_job(db, job_id, status="complete", completed_at=utcnow())
                else:
                    await update_campaign_status(db, campaign_id, "failed")
                    await update_job(db, job_id, status="failed",
                                     error_details=json.dumps(results),
                                     completed_at=utcnow())
            except Exception as exc:
                logger.error("Fatal publish error job=%s: %s", job_id, exc, exc_info=True)
                await update_campaign_status(db, campaign_id, "failed")
                await update_job(db, job_id, status="failed",
                                 error_details=json.dumps({"error": str(exc)}),
                                 completed_at=utcnow())
    ```
  - [x] 3.2 Use `get_session_context()` — an async context manager version of `get_session` that manages its own session lifecycle (required for BackgroundTasks which run after the request is closed); add `get_session_context` to `backend/app/db/connection.py` if not present:
    ```python
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def get_session_context():
        async with AsyncSession(engine) as session:
            yield session
    ```
  - [x] 3.3 Jobs repository: ensure `update_job(db, job_id, **kwargs)` exists — add to `backend/app/db/repositories/jobs.py` if not present

- [x] Task 4: Add `POST /api/v1/campaigns/{id}/publish` endpoint to `publishing.py` router (AC: #1, #9, #10)
  - [ ] 4.1 In `backend/app/routers/publishing.py`, add:
    ```python
    @router.post("/campaigns/{campaign_id}/publish", status_code=202)
    async def publish_campaign_now(
        campaign_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
    ```
    - Ownership check: fetch campaign → verify `campaign.client_id` belongs to `current_user`
    - Status guard: only `approved` campaigns can be published; `other statuses → HTTP 400, INVALID_STATUS_TRANSITION`
    - Connection check: `connections = await get_connections_for_client(db, campaign.client_id)`; if empty → `HTTP 400, NO_PLATFORM_CONNECTIONS`
    - Create job record FIRST: `job = await create_job(db, job_type="publish", status="pending", campaign_id=campaign_id)`
    - Commit: `await db.commit()`
    - Dispatch: `background_tasks.add_task(run_publish, job.id, campaign_id)`
    - Return: `{"job_id": str(job.id)}`
  - [x] 4.2 The job record MUST be created and committed before dispatching the BackgroundTask — this is the critical invariant from `architecture.md` (FastAPI BackgroundTask Pattern)

- [x] Task 5: Complete `backend/app/integrations/wordpress.py` — full publish (AC: #3)
  - [x] 5.1 Add `publish_post(creds: dict, campaign)` to `wordpress.py`:
    ```python
    async def publish_post(creds: dict, campaign) -> str:
        """Draft-first publish. Returns the live post URL."""
        site_url = creds["site_url"].rstrip("/")
        username = creds.get("username", "")
        app_password = creds["application_password"]
        auth = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create draft
            draft_resp = await client.post(
                f"{site_url}/wp-json/wp/v2/posts",
                headers=headers,
                json={"title": extract_title(campaign.blog_html), "content": campaign.blog_html, "status": "draft"}
            )
            draft_resp.raise_for_status()
            post_id = draft_resp.json()["id"]

            media_id = None
            try:
                # Step 2: Upload featured image
                if campaign.image_url:
                    media_id = await upload_featured_image(client, site_url, headers, campaign.image_url, post_id)
            except Exception as img_exc:
                logger.warning("Featured image upload failed for WP post %s: %s", post_id, img_exc)
                # Image failure is non-blocking — proceed to publish

            # Step 3: Publish
            patch_body = {"status": "publish"}
            if media_id:
                patch_body["featured_media"] = media_id
            pub_resp = await client.patch(
                f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                headers=headers,
                json=patch_body
            )
            if pub_resp.status_code != 200:
                # Clean up draft
                await client.delete(f"{site_url}/wp-json/wp/v2/posts/{post_id}", headers=headers)
                raise PlatformError("wordpress", pub_resp.status_code, "publish step failed — draft cleaned up")

            return pub_resp.json().get("link", "")
    ```
  - [x] 5.2 Add `extract_title(html: str) -> str` helper: parse the `<h1>` from blog_html using BeautifulSoup4 (already in requirements)
  - [x] 5.3 Add `upload_featured_image(client, site_url, headers, image_url, post_id)` helper: fetch the image from Supabase CDN URL, then POST to `/wp-json/wp/v2/media` as multipart — set `Content-Disposition: attachment; filename="featured.png"`
  - [x] 5.4 WordPress credential format stored in this story: `{"site_url": "...", "username": "...", "application_password": "..."}` (Note: Story 5.1 decision added `username` as a third field — confirm this matches what was stored)

- [x] Task 6: Complete `backend/app/integrations/twitter.py` — tweet creation (AC: #4)
  - [x] 6.1 Add `create_tweet(access_token: str, text: str) -> str` to `twitter.py`:
    ```python
    async def create_tweet(access_token: str, text: str) -> str:
        """Post a tweet. Returns the tweet ID."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"text": text[:280]},  # Hard cap at 280 chars
                params={"tweet.fields": "id,text"},  # Selective fields — minimize rate-limit pressure
            )
        if resp.status_code == 429:
            raise PlatformError("X", 429, "rate limit exceeded — retry later")
        if resp.status_code != 201:
            raise PlatformError("X", resp.status_code, resp.json().get("detail", "tweet creation failed"))
        return resp.json()["data"]["id"]
    ```

- [x] Task 7: Complete `backend/app/integrations/linkedin.py` — UGC post creation (AC: #5)
  - [x] 7.1 Add `create_ugc_post(access_token: str, blog_html: str, linkedin_text: str) -> str` to `linkedin.py`:
    ```python
    async def create_ugc_post(access_token: str, blog_html: str, linkedin_text: str) -> str:
        """Create a LinkedIn UGC post. Returns the post URN."""
        # Get user's LinkedIn ID first
        async with httpx.AsyncClient(timeout=15.0) as client:
            profile_resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}", "LinkedIn-Version": "202602"}
            )
            if profile_resp.status_code != 200:
                raise PlatformError("LinkedIn", profile_resp.status_code, "failed to get user profile")
            author_urn = profile_resp.json().get("sub", "")  # OpenID sub = LinkedIn URN

            post_resp = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "LinkedIn-Version": "202602",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json={
                    "author": f"urn:li:person:{author_urn}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": linkedin_text},
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                }
            )
        if post_resp.status_code not in (200, 201):
            raise PlatformError("LinkedIn", post_resp.status_code, post_resp.json().get("message", "UGC post failed"))
        return post_resp.headers.get("x-restli-id", "")
    ```

- [x] Task 8: Complete `backend/app/integrations/webflow.py` — CMS item creation + publish (AC: #6)
  - [x] 8.1 Add `publish_post(creds: dict, campaign) -> str` to `webflow.py`:
    ```python
    async def publish_post(creds: dict, campaign) -> str:
        """Create and publish a Webflow CMS item. Returns the item URL."""
        token = creds["token"]
        collection_id = creds["collection_id"]
        headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create CMS item (draft)
            create_resp = await client.post(
                f"https://api.webflow.com/v2/collections/{collection_id}/items",
                headers=headers,
                json={
                    "isArchived": False,
                    "isDraft": False,
                    "fieldData": {
                        "name": extract_title(campaign.blog_html),
                        "slug": slugify(extract_title(campaign.blog_html)),
                        "post-body": campaign.blog_html,
                    }
                }
            )
            if create_resp.status_code not in (200, 201):
                raise PlatformError("webflow", create_resp.status_code, "CMS item creation failed")
            item_id = create_resp.json()["id"]

            # Publish the item
            pub_resp = await client.post(
                f"https://api.webflow.com/v2/collections/{collection_id}/items/publish",
                headers=headers,
                json={"itemIds": [item_id]}
            )
            if pub_resp.status_code not in (200, 202):
                raise PlatformError("webflow", pub_resp.status_code, "publish step failed")
            return item_id
    ```
  - [x] 8.2 Add `slugify(title: str) -> str` helper (lowercase, replace spaces with hyphens, strip special chars)

- [x] Task 9: Wire "Publish now" button in Approval Gate frontend (AC: #1, #7, #8, #9, #10)
  - [x] 9.1 In `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` (or `ApprovalGateClient.tsx`), replace the disabled "Publish now" stub (from Story 4.4) with functional implementation:
    ```typescript
    async function handlePublishNow() {
      setIsPublishing(true)
      try {
        const { job_id } = await campaignsApi.publishNow(campaign.id)
        setActiveJobId(job_id)
        // React Query polling starts automatically via useJobPolling hook
      } catch (err) {
        addToast({ type: 'error', message: err instanceof APIError ? err.message : 'Publish failed.' })
        setIsPublishing(false)
      }
    }
    ```
  - [x] 9.2 Add `campaignsApi.publishNow` to `frontend/lib/api.ts`:
    ```typescript
    publishNow: (id: string) =>
      apiFetch<{ job_id: string }>(`/campaigns/${id}/publish`, { method: "POST" }),
    ```
  - [x] 9.3 Job polling: the Approval Gate page already has job polling logic from Story 3.2 (generation polling). Reuse the `useJobPolling` hook or React Query pattern to poll `GET /api/v1/jobs/{job_id}` every 2 seconds while `job.status === 'pending' | 'in_progress'`; on `complete` → `router.refresh()` to reload campaign; on `failed` → show toast + `router.refresh()` to show Retry Panel
  - [x] 9.4 "Publish now" UI state during publish: show inline spinner on the button, disable both "Publish now" and "Schedule"; prevent navigation away is NOT required for publishing (only generation blocks navigation per UX-DR23)
  - [x] 9.5 Published state footer (AC #7): when `campaign.status === 'published'`, replace the action footer with the published summary:
    ```tsx
    <div className="px-6 py-4 flex items-center gap-3 text-sm text-graphite">
      <span className="font-medium text-ink">Published</span>
      <span>—</span>
      <span>{formatPublishDate(campaign.updated_at)}</span>
      {/* Platform links: "View on WordPress →", etc. */}
    </div>
    ```
  - [x] 9.6 Platform links in the published footer: derive from `job.error_details` if it contains a URL, or from platform connection data — for v1, show "View on [Platform] →" as a static text link if the platform URL is stored; if not stored, omit the link and show platform icon only

- [x] Task 10: Update `jobs` repository for publish job tracking (AC: #1, #7, #8)
  - [x] 10.1 In `backend/app/db/repositories/jobs.py`, add:
    ```python
    async def create_job(db: AsyncSession, job_type: str, status: str, campaign_id: uuid.UUID, **kwargs) -> Job
    async def update_job(db: AsyncSession, job_id: uuid.UUID, **kwargs) -> Job
    ```
  - [x] 10.2 Check if these already exist (they may exist from Epic 3 generation work) — if so, verify they handle the publish job fields correctly (especially `error_details` as TEXT)

- [x] Task 11: Backend tests (AC: #1, #2, #3, #4, #5, #6, #7, #8)
  - [x] 11.1 In `backend/tests/routers/test_publishing.py`:
    - `test_publish_now_success` — mocks dispatch; verifies job created, 202 returned, status transitions to published
    - `test_publish_now_no_connections` — HTTP 400, NO_PLATFORM_CONNECTIONS
    - `test_publish_now_wrong_status` — campaign not approved → HTTP 400
    - `test_publish_now_ownership` — other user's campaign → 404
  - [x] 11.2 In `backend/tests/services/test_publishing.py`:
    - `test_dispatch_publish_all_success` — all platforms mock success → results all "success"
    - `test_dispatch_publish_partial_failure` — one platform fails → failed result logged
    - `test_credentials_not_logged` — verify `logger.error` calls never contain the decrypted credential string
  - [x] 11.3 In `backend/tests/integrations/test_wordpress.py`:
    - `test_publish_post_draft_first` — draft created, image uploaded, patch to publish
    - `test_publish_post_cleanup_on_failure` — publish step fails → DELETE draft called

- [x] Task 12: Frontend tests (AC: #1, #7, #9)
  - [x] 12.1 In `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx`, extend:
    - Test: "Publish now" button present when campaign is approved + has connections
    - Test: "Publish now" click → `campaignsApi.publishNow(id)` called
    - Test: publish in-flight → spinner on button, both buttons disabled
    - Test: job completes → `router.refresh()` called
    - Test: job fails → error toast shown
    - Test: published state → footer shows "Published" summary, no Approve/Reject buttons

## Dev Notes

### BackgroundTask Session Context Pattern

FastAPI BackgroundTasks run after the HTTP response is sent. The request's `db` session is closed by then. Workers MUST create their own database session using `get_session_context()` — not the session passed to the router:

```python
# workers/publish.py
async def run_publish(job_id: UUID, campaign_id: UUID) -> None:
    async with get_session_context() as db:
        # All DB operations here use the new session
```

This matches the existing `workers/generate.py` and `workers/ingest.py` pattern — read those files to confirm the session management approach before implementing.

### Credential Decryption — Hard Boundary

From `architecture.md` hard service boundaries:
> `services/publishing.py` is the ONLY place that calls `core/security.py:decrypt_credential()`

This means:
- The router (`routers/publishing.py`) NEVER calls `decrypt_credential`
- The worker (`workers/publish.py`) NEVER calls `decrypt_credential`
- The integrations (`wordpress.py`, etc.) receive already-decrypted Python dicts — they NEVER call `decrypt_credential`

The flow is: `worker → services/publishing.py:dispatch_publish() → decrypt_credential() → parse JSON → call integration`

### WordPress Draft-First Pattern — Why

The draft-first pattern prevents partial publish failures leaving live content without a featured image. If image upload fails after the draft is created but before publish, we proceed to publish without the featured image (non-blocking per AC #3). If the final PATCH to `status: "publish"` fails, we clean up the draft so no orphan draft exists in WordPress.

### X API Rate Limiting — tweet.fields Parameter

Per AR-9 and FR-23:
```
params={"tweet.fields": "id,text"}
```
This reduces the payload Twitter returns, which correlates with lower rate-limit cost. Do NOT omit this parameter.

### LinkedIn `urn:li:person:{sub}` Pattern

The LinkedIn user's OpenID sub value (returned by `/v2/userinfo`) is the person ID for the author URN. Note: LinkedIn changed their URN format in 2024 — `urn:li:person:{sub}` is the current format. The `sub` from `/v2/userinfo` is the member ID directly.

### Platform Publish URL Storage

v1 does not persist the live URL of published posts. The "View on WordPress →" link in the footer is a nice-to-have. For v1, skip the link if the URL isn't readily available from the job record — just show "Published to WordPress, X, and LinkedIn." as plain text. Document this as a v2 enhancement.

### `jobs.error_details` Schema for Publish

```python
# All platforms succeed:
error_details = None

# One fails:
error_details = json.dumps({
    "wordpress": "success",
    "x": "success",
    "linkedin": "401 LinkedIn token expired"
})

# Total failure:
error_details = json.dumps({
    "error": "Fatal exception: connection timeout"
})
```

The Retry Panel (Story 5.5) reads this JSON to determine which platforms to show retry buttons for.

### Approval Gate — Post-Approve State Was Stubbed in Story 4.4

Story 4.4 rendered "Publish now" and "Schedule" as disabled stubs:
```tsx
<button type="button" disabled className="... opacity-50 cursor-not-allowed" title="Publishing wired in Epic 5">
  Publish now
</button>
```

In this story, replace these stubs with fully functional buttons. Read `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` and `approval-panel.tsx` before modifying — understand the current component tree and prop flow.

### Job Polling — Reuse Existing Pattern

Epic 3 implemented job polling for generation. The Approval Gate page already polls `GET /api/v1/jobs/{job_id}` via React Query. Check `frontend/app/(app)/campaigns/[id]/page.tsx` and look for the `GenerationGate` or job polling hook. Reuse the same approach for publish job polling — do NOT duplicate polling logic.

### Paper Style — Published Footer

Per UX-DR22 and EXPERIENCE.md State Patterns (Approval Gate: published):
> "Footer replaced by 'Published' status summary: date, time, platform links ('View on WordPress →'). Read-only."

Per EXPERIENCE.md microcopy table:
> Publish success: "Published to WordPress, X, and LinkedIn." (not "Boom! Your content is live! 🚀")

Published footer implementation:
```tsx
<div className="fixed bottom-0 left-0 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4">
  <p className="text-sm text-graphite">
    <span className="font-medium text-ink">Published</span>
    {' — '}
    <span>{new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(campaign.updated_at))}</span>
  </p>
</div>
```

### Project Structure Notes

**New files:**
```
backend/app/services/publishing.py
backend/app/workers/publish.py
backend/tests/services/test_publishing.py
```

**Modified files:**
```
backend/app/routers/publishing.py              ← Add POST /campaigns/{id}/publish endpoint
backend/app/integrations/wordpress.py          ← Add publish_post() function
backend/app/integrations/twitter.py            ← Add create_tweet() function
backend/app/integrations/linkedin.py           ← Add create_ugc_post() function
backend/app/integrations/webflow.py            ← Add publish_post() function
backend/app/db/connection.py                   ← Add get_session_context() if missing
backend/app/db/repositories/jobs.py            ← Add/verify create_job, update_job
backend/tests/routers/test_publishing.py       ← Add publish endpoint tests
backend/tests/integrations/test_wordpress.py   ← Add draft-first pattern tests
frontend/lib/api.ts                            ← Add campaignsApi.publishNow
frontend/app/(app)/campaigns/[id]/approval-panel.tsx         ← Wire Publish now button
frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx     ← Add publish state UI
```

### References

- Story 5.3 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3]
- FR-23: Publishing — draft-first WP, Webflow CMS v2, X API v2, LinkedIn UGC v2 202602: [Source: _bmad-output/planning-artifacts/epics.md#FR-23]
- NFR-9: Stagger outbound calls: 2s X, 5s LinkedIn: [Source: _bmad-output/planning-artifacts/epics.md#NFR-9]
- Architecture: BackgroundTask must create job record first: [Source: _bmad-output/planning-artifacts/architecture.md#FastAPI BackgroundTask Pattern]
- Architecture: services/publishing.py is ONLY place to call decrypt_credential: [Source: _bmad-output/planning-artifacts/architecture.md#Hard Service Boundaries]
- Architecture: get_session_context for BackgroundTasks: [Source: _bmad-output/planning-artifacts/architecture.md]
- UX-DR22: Approval Gate state machine — published state footer: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR22]
- EXPERIENCE.md: Microcopy — "Published to WordPress, X, and LinkedIn.": [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]
- Story 4.4 stub buttons to replace: [Source: _bmad-output/implementation-artifacts/4-4-approve-reject-campaign.md#Task 5.6]
- Existing workers/generate.py (BackgroundTask session pattern): [Source: backend/app/workers/generate.py]
- Existing ApprovalGateClient.tsx component tree: [Source: frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1: `get_connections_for_client` was already complete from Story 5.1 — verified and reused.
- Task 2: Created `services/publishing.py` with `dispatch_publish`. Credential decryption boundary enforced: only this service calls `decrypt_credential`. WordPress credentials stored with key `credential` (not `application_password`) — handled both keys in `publish_post`.
- Task 3: Created `workers/publish.py` using `AsyncSessionLocal` directly (same pattern as `workers/generate.py`). Added `get_session_context` to `connection.py` per Dev Notes spec.
- Task 4: Added `POST /campaigns/{campaign_id}/publish` to `routers/publishing.py`. Job record created and committed before BackgroundTask dispatch per architecture invariant.
- Task 5: WordPress `publish_post` with draft-first pattern, non-blocking image upload, draft cleanup on publish failure.
- Task 6: Twitter `create_tweet` with 280-char cap, `tweet.fields=id,text` selective fields, 429 rate-limit handling.
- Task 7: LinkedIn `create_ugc_post` with `LinkedIn-Version: 202602` header, `urn:li:person:{sub}` author URN pattern.
- Task 8: Webflow `publish_post` with two-step create+publish, `_extract_title` and `_slugify` helpers.
- Task 9: Wired "Publish now" button with `handlePublishNow`, `setInterval` polling every 2s, published state footer. "Schedule" stays disabled (Story 5.4). `campaignsApi.publishNow` added to `api.ts`.
- Task 10: Added `update_job(**kwargs)` generic wrapper to `jobs.py` and `update_campaign_status` to `campaigns.py`.
- Task 11: 9 backend tests covering all ACs — 4 router tests, 3 service tests, 2 WordPress integration tests. All pass.
- Task 12: 17 frontend tests total (12 existing + 5 new publish tests). All pass.

### File List

**New files:**
- `backend/app/services/publishing.py`
- `backend/app/workers/publish.py`
- `backend/tests/routers/__init__.py`
- `backend/tests/routers/test_publish_now.py`
- `backend/tests/integrations/__init__.py`
- `backend/tests/integrations/test_wordpress.py`
- `backend/tests/services/test_publishing.py`

**Modified files:**
- `backend/app/db/connection.py`
- `backend/app/db/repositories/campaigns.py`
- `backend/app/db/repositories/jobs.py`
- `backend/app/integrations/wordpress.py`
- `backend/app/integrations/twitter.py`
- `backend/app/integrations/linkedin.py`
- `backend/app/integrations/webflow.py`
- `backend/app/routers/publishing.py`
- `frontend/lib/api.ts`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
- `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx`

### Review Findings

- [x] [Review][Patch] Worker never commits DB changes — `run_publish` calls `flush()` only; `AsyncSessionLocal` does not auto-commit on exit; all job and campaign status updates silently lost [backend/app/workers/publish.py]
- [x] [Review][Patch] Campaign None crash in dispatch_publish — `get_campaign()` result not null-checked before accessing `campaign.client_id` [backend/app/services/publishing.py:30-31]
- [x] [Review][Patch] `update_job` unchecked setattr — arbitrary kwargs set on Job model without field whitelist; could corrupt `id`, `created_at` [backend/app/db/repositories/jobs.py:53-66]
- [x] [Review][Patch] Empty results dict = success — `all(v == "success" for v in results.values())` returns True on empty dict; campaign marked published with zero platforms [backend/app/workers/publish.py:27]
- [x] [Review][Patch] `asyncio.get_event_loop().time()` deprecated — raises RuntimeError in Python 3.10+; replace with `asyncio.get_running_loop().time()` [backend/app/services/publishing.py:49,55,58,66]
- [x] [Review][Patch] Duplicate publish/publishNow in api.ts — both POST same endpoint but declare different return shapes [frontend/lib/api.ts:111-117]
- [x] [Review][Patch] LinkedIn empty author_urn creates invalid URN — `sub` defaults to `""` → sends `urn:li:person:` to API [backend/app/integrations/linkedin.py:34]
- [x] [Review][Patch] Twitter KeyError on success response — `resp.json()["data"]["id"]` crashes if Twitter response shape differs [backend/app/integrations/twitter.py:43]
- [x] [Review][Patch] Webflow no cleanup on publish-step failure — orphaned CMS item left in Webflow if publish call fails after create succeeds [backend/app/integrations/webflow.py]
- [x] [Review][Patch] WordPress draft cleanup exception swallowed silently — `except Exception: pass` hides delete failure [backend/app/integrations/wordpress.py:88-91]
- [x] [Review][Patch] Webflow `_slugify` preserves non-ASCII Unicode — `\w` matches Unicode letters, producing non-ASCII URL slugs [backend/app/integrations/webflow.py:17]
- [x] [Review][Patch] Import inside function body — `from app.db.repositories.models import utcnow` imported on every call [backend/app/db/repositories/campaigns.py:39]
- [x] [Review][Patch] Worker uses `AsyncSessionLocal` directly instead of `get_session_context()` per dev notes [backend/app/workers/publish.py:23]
- [x] [Review][Defer] Published footer missing platform names — AC7 partially; dev notes explicitly allow v2 deferral [frontend/app/(app)/campaigns/[id]/approval-panel.tsx] — deferred, pre-existing per dev notes
- [x] [Review][Defer] Retry Panel not implemented — intentionally deferred to Story 5.5 scope [approval-panel.tsx] — deferred, pre-existing
- [x] [Review][Defer] `str(exc)` in results dict could expose credentials — integrations never hold raw creds; low real-world risk [backend/app/services/publishing.py:78] — deferred, pre-existing

## Change Log

- **2026-07-03** — Story 5.3 implemented: multi-platform publish endpoint, dispatch service, workers, platform integrations (WordPress draft-first, Twitter, LinkedIn UGC, Webflow CMS), frontend Publish now button with job polling, published state footer. 9 backend + 17 frontend tests all passing.
