# Story 5.5: Publishing Retry & Failure Handling

---
baseline_commit: bf19d1f142a96cb4d1d5bb8171c55c62a478da85
---

Status: review

## Story

As an authenticated user,
I want to retry publishing to specific platforms that failed without regenerating my content,
So that a temporary API issue on one platform does not require me to restart the entire publishing process.

## Acceptance Criteria

1. **Given** a Campaign with `status='failed'` due to publish errors is opened in the Approval Gate, **When** the Approval Gate renders, **Then** a Retry Panel is shown listing each platform that failed: platform name, specific error message (e.g., "WordPress returned 401 — check your Application Password"), and a per-platform "Retry" button; platforms that published successfully in the prior attempt show "Published" with a check mark; the panel is shown below the content previews.

2. **Given** the Retry Panel shows attempt counts, **When** it renders, **Then** each failed platform shows "Attempt [N] of 3" where N is the current `jobs.attempt_count` for that platform; when `attempt_count` reaches 3, the "Retry" button for that platform is disabled and replaced with the text "Maximum retries reached — reconnect [Platform] and try again."

3. **Given** a user clicks the "Retry" button for a specific failed platform, **When** `POST /api/v1/campaigns/{id}/publish/retry` is called with `{"platform": "wordpress"}`, **Then** the `jobs` record for this campaign publish job is found; `jobs.attempt_count` is incremented; `jobs.status` is set back to `'pending'`; the `jobs.error_details` field is updated to mark that platform as `'retrying'`; a new BackgroundTask is dispatched; only the specified failed platform is retried — already-published platforms are not called again; the API returns HTTP 202 with `{"job_id": "..."}`.

4. **Given** the retry BackgroundTask executes, **When** it completes successfully for the retried platform, **Then** if all platforms are now `'success'` in `jobs.error_details`, `campaigns.status` transitions to `'published'` and the Approval Gate shows the Published footer; if other platforms are still in failed state, `campaigns.status` remains `'failed'` and the Retry Panel updates to reflect the new `error_details`.

5. **Given** a Droplet restart occurs while a retry job is in `'pending'` status, **When** FastAPI restarts, **Then** the `jobs` record persists in Supabase Postgres with `status='pending'`; the user can trigger the next retry attempt from the Approval Gate on their next session — the retry state shows "Attempt N of 3" from the persisted `attempt_count`.

6. **Given** the maximum retry count (3) is reached for a platform, **When** the user attempts to retry, **Then** the API returns HTTP 400 with `{"error": {"code": "MAX_RETRIES_REACHED", "message": "Maximum retries reached for [Platform]. Reconnect the platform and try again."}}` — the "Retry" button is disabled client-side before the call, so this serves as a server-side guard.

7. **Given** the Retry Panel "Retry" button is clicked for a platform, **When** the retry job is in-flight, **Then** the per-platform "Retry" button shows an inline spinner and is disabled until the job reaches a terminal state; other platform "Retry" buttons remain enabled; the React Query polling mechanism from Story 5.3 is reused to track job status.

8. **Given** a Campaign status is `'failed'` due to scheduled publish failure, **When** the user logs in and opens the Approval Gate, **Then** the same Retry Panel is shown — retry works identically whether the original failure was from immediate publishing or a scheduled publish.

## Tasks / Subtasks

- [x] Task 1: Update `backend/app/services/publishing.py` — selective retry dispatch (AC: #3, #4)
  - [x] 1.1 Add a `dispatch_publish_for_platform(db, campaign_id, job_id, platform)` function:
    ```python
    async def dispatch_publish_for_platform(
        db: AsyncSession,
        campaign_id: UUID,
        job_id: UUID,
        platform: str,
    ) -> dict:
        """
        Retry publishing for a single platform.
        Returns updated per-platform results merged with existing error_details.
        """
        campaign = await get_campaign(db, campaign_id)
        connection = await get_connection_for_platform(db, campaign.client_id, platform)
        if not connection:
            return {platform: "no platform connection found"}
        try:
            creds_json = decrypt_credential(connection.encrypted_credentials)
            creds = json.loads(creds_json)
            if platform == "wordpress":
                await integrations.wordpress.publish_post(creds, campaign)
            elif platform == "webflow":
                await integrations.webflow.publish_post(creds, campaign)
            elif platform == "x":
                await integrations.twitter.create_tweet(creds["access_token"], campaign.x_post)
            elif platform == "linkedin":
                await integrations.linkedin.create_ugc_post(
                    creds["access_token"], campaign.blog_html, campaign.linkedin_post
                )
            return {platform: "success"}
        except Exception as exc:
            logger.error("Retry publish failed platform=%s campaign=%s: %s", platform, campaign_id, exc, exc_info=True)
            return {platform: str(exc)}
    ```
  - [x] 1.2 Add `get_connection_for_platform(db, client_id, platform)` to `backend/app/db/repositories/platform_connections.py`:
    ```python
    async def get_connection_for_platform(db: AsyncSession, client_id: UUID, platform: str) -> PlatformConnection | None
    ```
  - [x] 1.3 The merged result logic: load existing `jobs.error_details` (JSON dict), override the retried platform's value with the new result, determine overall success:
    ```python
    existing = json.loads(job.error_details or "{}")
    new_result = await dispatch_publish_for_platform(db, campaign_id, job.id, platform)
    merged = {**existing, **new_result}
    all_success = all(v == "success" for v in merged.values())
    ```

- [x] Task 2: Create `backend/app/workers/publish_retry.py` (AC: #3, #4, #5)
  - [x] 2.1 Create `backend/app/workers/publish_retry.py`:
    ```python
    import json
    import logging
    from uuid import UUID
    from app.db.connection import get_session_context
    from app.db.repositories.campaigns import update_campaign_status, get_campaign
    from app.db.repositories.jobs import update_job, get_job
    from app.services.publishing import dispatch_publish_for_platform

    logger = logging.getLogger(__name__)

    async def run_publish_retry(job_id: UUID, campaign_id: UUID, platform: str) -> None:
        """BackgroundTask: retry publishing for a single failed platform."""
        async with get_session_context() as db:
            await update_job(db, job_id, status="in_progress", started_at=utcnow())
            try:
                result = await dispatch_publish_for_platform(db, campaign_id, job_id, platform)
                job = await get_job(db, job_id)
                existing = json.loads(job.error_details or "{}")
                merged = {**existing, **result}
                all_success = all(v == "success" for v in merged.values())

                if all_success:
                    await update_campaign_status(db, campaign_id, "published")
                    await update_job(db, job_id, status="complete",
                                     error_details=None,
                                     completed_at=utcnow())
                else:
                    await update_campaign_status(db, campaign_id, "failed")
                    await update_job(db, job_id, status="failed",
                                     error_details=json.dumps(merged),
                                     completed_at=utcnow())
            except Exception as exc:
                logger.error("Fatal retry error job=%s: %s", job_id, exc, exc_info=True)
                await update_job(db, job_id, status="failed",
                                 error_details=json.dumps({platform: str(exc)}),
                                 completed_at=utcnow())
    ```

- [x] Task 3: Add `POST /api/v1/campaigns/{id}/publish/retry` endpoint (AC: #3, #6)
  - [x] 3.1 In `backend/app/routers/publishing.py`, add:
    ```python
    class RetryRequest(BaseModel):
        platform: str  # "wordpress" | "webflow" | "x" | "linkedin"

    @router.post("/campaigns/{campaign_id}/publish/retry", status_code=202)
    async def retry_platform_publish(
        campaign_id: uuid.UUID,
        body: RetryRequest,
        background_tasks: BackgroundTasks,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
    ```
    - Ownership check: fetch campaign + verify ownership
    - Status guard: campaign must be `failed` — only failed campaigns can be retried
    - Find existing publish `jobs` record: `job = await get_publish_job_for_campaign(db, campaign_id)` — find the most recent `publish` or `scheduled_publish` job
    - Platform guard: verify `platform` appears as failed in `job.error_details` (not already "success")
    - Max retries guard: `if job.attempt_count >= 3: raise HTTP 400 MAX_RETRIES_REACHED`
    - Increment attempt count: `job.attempt_count += 1`
    - Update job: `status = 'pending'`, mark platform as `'retrying'` in `error_details`
    - Commit
    - Dispatch: `background_tasks.add_task(run_publish_retry, job.id, campaign_id, body.platform)`
    - Return `{"job_id": str(job.id)}`
  - [x] 3.2 `get_publish_job_for_campaign(db, campaign_id)` — add to `jobs.py` repository:
    ```python
    async def get_publish_job_for_campaign(db: AsyncSession, campaign_id: UUID) -> Job | None:
        """Get the most recent publish or scheduled_publish job for a campaign."""
        result = await db.execute(
            select(Job)
            .where(Job.campaign_id == campaign_id, Job.job_type.in_(["publish", "scheduled_publish"]))
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    ```
  - [x] 3.3 Per-platform attempt count: in v1, `jobs.attempt_count` tracks attempts across ALL platforms in a publish job (not per-platform). The AC says "Attempt N of 3" per platform. Implement: `attempt_count` increments on each retry call; the UI shows the same count for all platforms in a job (simplification). Document this as a v2 enhancement if per-platform tracking is needed.

- [x] Task 4: Implement `RetryPanel` component (AC: #1, #2, #7)
  - [x] 4.1 Create `frontend/components/publishing/RetryPanel.tsx` as a `"use client"` component:
    ```tsx
    'use client'
    // Per UX-DR15: Shown when Campaign status is `failed`.
    // Lists each platform with error message and per-platform "Retry" button.
    // Shows attempt count "Attempt N of 3". Retry disabled at maximum.

    interface RetryPanelProps {
      campaign: Campaign
      jobErrorDetails: Record<string, string> | null
      attemptCount: number
      onRetrySuccess: () => void
    }
    ```
  - [x] 4.2 Parse `jobErrorDetails` from `jobs.error_details` JSON: the Approval Gate fetches the job status via `GET /api/v1/jobs/{job_id}` — parse `job.error_details` as a JSON dict; for each platform in the dict, render a row
  - [x] 4.3 How to get `job_id` for a failed campaign: the `campaign` object doesn't store `job_id`. Solution: the Approval Gate page fetches the campaign from the API; add a `GET /api/v1/campaigns/{id}/publish-job` endpoint OR store `job_id` on the campaign response; **simplest approach**: add a query to the existing `GET /api/v1/campaigns/{id}` endpoint to include the latest publish job's `id`, `attempt_count`, and `error_details` in the response as `publish_job?: { id, attempt_count, error_details }`.
  - [x] 4.4 RetryPanel row layout (per UX-DR15 and Paper Style):
    ```tsx
    <div className="border border-border p-4 space-y-3">
      <h2 className="text-sm font-medium uppercase tracking-[0.06em] text-ink">Publishing failed</h2>
      {platforms.map(({ platform, error, isSuccess }) => (
        <div key={platform} className="flex items-center justify-between py-2 border-b border-border last:border-0">
          <div>
            <p className="text-sm font-medium text-ink capitalize">{platform}</p>
            {isSuccess ? (
              <p className="text-xs text-[#2E4F2E]">Published</p>
            ) : (
              <p className="text-xs text-danger">{error}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {!isSuccess && (
              <>
                <span className="text-xs text-graphite">Attempt {attemptCount} of 3</span>
                {attemptCount >= 3 ? (
                  <span className="text-xs text-graphite">Maximum retries reached — reconnect {platform} and try again.</span>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleRetry(platform)}
                    disabled={isRetrying[platform]}
                    className="px-3 py-1.5 border border-ink text-ink text-xs font-medium hover:bg-ink hover:text-white transition-colors rounded-none disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                  >
                    {isRetrying[platform] ? <span className="inline-block size-3 border-2 border-ink border-t-transparent rounded-full animate-spin" /> : 'Retry'}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      ))}
    </div>
    ```
  - [x] 4.5 `handleRetry(platform)`:
    ```typescript
    async function handleRetry(platform: string) {
      setIsRetrying(prev => ({ ...prev, [platform]: true }))
      try {
        const { job_id } = await campaignsApi.retryPublish(campaign.id, platform)
        // Poll job status until terminal
        await pollUntilComplete(job_id)
        onRetrySuccess()  // triggers router.refresh() in parent
      } catch (err) {
        addToast({ type: 'error', message: err instanceof APIError ? err.message : 'Retry failed.' })
      } finally {
        setIsRetrying(prev => ({ ...prev, [platform]: false }))
      }
    }
    ```
  - [x] 4.6 Add `campaignsApi.retryPublish` to `frontend/lib/api.ts`:
    ```typescript
    retryPublish: (id: string, platform: string) =>
      apiFetch<{ job_id: string }>(`/campaigns/${id}/publish/retry`, {
        method: "POST",
        body: JSON.stringify({ platform }),
      }),
    ```

- [x] Task 5: Extend campaign API response to include publish job info (AC: #1, #2)
  - [x] 5.1 In `backend/app/routers/campaigns.py`, extend `GET /campaigns/{id}` response to include publish job info:
    ```python
    class PublishJobInfo(BaseModel):
        id: uuid.UUID
        attempt_count: int
        error_details: Optional[str]  # JSON string of per-platform results
        status: str

    class CampaignDetailResponse(CampaignResponse):
        publish_job: Optional[PublishJobInfo] = None
    ```
  - [x] 5.2 In the GET handler, after fetching the campaign, fetch the most recent publish job:
    ```python
    publish_job = await get_publish_job_for_campaign(db, campaign_id)
    return CampaignDetailResponse(**campaign.dict(), publish_job=publish_job)
    ```
  - [x] 5.3 Update `Campaign` TypeScript type in `frontend/lib/types.ts`:
    ```typescript
    export interface Campaign {
      // ... existing fields ...
      publish_job?: {
        id: string
        attempt_count: number
        error_details: string | null  // JSON string
        status: string
      } | null
    }
    ```
  - [x] 5.4 In `ApprovalGateClient.tsx`, parse `campaign.publish_job?.error_details` as JSON and pass to `RetryPanel`

- [x] Task 6: Integrate RetryPanel into Approval Gate (AC: #1, #8)
  - [x] 6.1 In `ApprovalGateClient.tsx`, render `RetryPanel` when `campaign.status === 'failed'`:
    ```tsx
    {campaign.status === 'failed' && campaign.publish_job && (
      <RetryPanel
        campaign={campaign}
        jobErrorDetails={parseErrorDetails(campaign.publish_job.error_details)}
        attemptCount={campaign.publish_job.attempt_count}
        onRetrySuccess={() => router.refresh()}
      />
    )}
    ```
  - [x] 6.2 `parseErrorDetails(errorDetails: string | null): Record<string, string> | null` — parse JSON safely:
    ```typescript
    function parseErrorDetails(raw: string | null): Record<string, string> | null {
      if (!raw) return null
      try { return JSON.parse(raw) } catch { return null }
    }
    ```
  - [x] 6.3 When `campaign.status === 'failed'`, the approval footer (Approve/Reject) should NOT be shown — the RetryPanel replaces the footer action area. The footer of the Approval Gate should show the Retry Panel content, not the Approve/Reject buttons.
  - [x] 6.4 Scroll behavior: the RetryPanel appears below the content previews, within the scrollable content area — it is NOT a sticky footer. The sticky footer area remains empty (or shows just the panel in a fixed position per layout preference).

- [x] Task 7: Backend tests (AC: #3, #4, #5, #6)
  - [x] 7.1 In `backend/tests/routers/test_publishing.py`:
    - `test_retry_publish_success` — mocks dispatch, verifies attempt_count incremented, 202 returned
    - `test_retry_wrong_campaign_status` — campaign not failed → HTTP 400
    - `test_retry_max_retries` — attempt_count=3 → HTTP 400 MAX_RETRIES_REACHED
    - `test_retry_ownership` — other user's campaign → 404
    - `test_retry_already_published_platform` — platform shows "success" in error_details → 400 or handle gracefully
  - [x] 7.2 In `backend/tests/services/test_publishing.py`:
    - `test_dispatch_retry_single_platform_success` — retries only the specified platform
    - `test_dispatch_retry_merges_results` — all success after retry → all_success=True
    - `test_dispatch_retry_still_failing` — retry fails again → all_success=False

- [x] Task 8: Frontend tests (AC: #1, #2, #7)
  - [x] 8.1 Create `frontend/__tests__/components/publishing/RetryPanel.test.tsx`:
    - Test: renders platform list with error messages from error_details JSON
    - Test: "Retry" button present for failed platforms; not present for successful platforms
    - Test: "Attempt 2 of 3" shown for attempt_count=2
    - Test: attempt_count=3 → "Retry" button replaced with "Maximum retries reached" text
    - Test: "Retry" click → `campaignsApi.retryPublish(id, platform)` called
    - Test: retry in-flight → per-platform spinner + disabled button; other platform buttons still enabled
    - Test: retry success + all platforms succeed → `onRetrySuccess()` called
  - [x] 8.2 In `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx`:
    - Test: `campaign.status === 'failed'` → RetryPanel rendered, not Approve/Reject footer

## Dev Notes

### `error_details` JSON Schema — Retry Logic

The `jobs.error_details` TEXT field stores a JSON dict of per-platform results:

```json
{
  "wordpress": "success",
  "x": "success",
  "linkedin": "401 LinkedIn token expired"
}
```

After a retry of `"linkedin"`:
```json
{
  "wordpress": "success",
  "x": "success",
  "linkedin": "retrying"   // temporarily while job is in-flight
}
```

After retry completes (success):
```json
{
  "wordpress": "success",
  "x": "success",
  "linkedin": "success"   // → all_success=True → campaign becomes 'published'
}
```

After retry completes (failure):
```json
{
  "wordpress": "success",
  "x": "success",
  "linkedin": "401 LinkedIn token expired again"
}
```

### RetryPanel — Paper Style Design

Per UX-DR15:
> "Retry panel — Shown when Campaign status is `failed`. Lists each platform with its error message and a per-platform 'Retry' button. Shows attempt count: 'Attempt 1 of 3'."

Per EXPERIENCE.md Component Patterns:
> "Shown when Campaign status is `failed`. Lists each platform with its error message and a per-platform 'Retry' button. Shows attempt count: 'Attempt 1 of 3.'"

Per EXPERIENCE.md State Patterns (Approval Gate: failed):
> "Retry panel shown (see Component Patterns)."

Key design decisions:
- Panel is NOT a modal — it's an inline section below the content
- "Retry" buttons are Secondary Button style (`border border-ink`)
- Error text is `text-[#8B0000]` (Danger color, `text-xs`)
- Platform names are `capitalize`d: "wordpress" → "WordPress"
- Success row shows muted green check: "Published" in `text-[#2E4F2E]`

### Error Microcopy — Platform Name in Error Messages

Per UX-DR21:
> "Error messages always name the platform + HTTP status code (when applicable) + resolution path"

The `dispatch_publish_for_platform` function catches `PlatformError` which includes `platform`, `status_code`, and `message`. The error string stored in `error_details` should be:
```
"WordPress returned 401 — check your Application Password"
```
NOT:
```
"PlatformError: ..."
```

In `services/publishing.py`, catch `PlatformError` specifically and format the message:
```python
except PlatformError as pe:
    error_msg = f"{pe.platform.capitalize()} returned {pe.status_code} — {pe.message}"
    return {platform: error_msg}
except Exception as exc:
    return {platform: f"Unexpected error — {str(exc)[:100]}"}
```

### `attempt_count` Semantics

v1 simplification: `jobs.attempt_count` tracks the total number of retry attempts on this publish job (across all platforms). The "Attempt N of 3" label in the UI shows this count for each failed platform.

This means:
- Initial publish: `attempt_count = 0` (the initial publish doesn't count as an "attempt")
- First retry: `attempt_count = 1` → "Attempt 1 of 3"
- Second retry: `attempt_count = 2` → "Attempt 2 of 3"
- Third retry: `attempt_count = 3` → "Attempt 3 of 3" → buttons disabled on next render
- Fourth retry: blocked by `if job.attempt_count >= 3` guard in the endpoint

### Frontend Job Polling — Reuse from Story 5.3

The retry polling uses the same mechanism as immediate publish polling (Story 5.3). The `job_id` returned from the retry endpoint is the SAME job ID as the original publish job (updated in place). React Query polling watches `GET /api/v1/jobs/{job_id}` until terminal state. After terminal state, `router.refresh()` reloads the campaign data.

### Campaign Detail Response — CampaignDetailResponse

Story 5.5 adds `publish_job` to the campaign detail response. This modifies the existing `GET /campaigns/{id}` endpoint in `backend/app/routers/campaigns.py`. Read this endpoint before modifying — ensure the existing `CampaignResponse` model is extended, not replaced, so earlier story tests still pass.

### Approval Gate — Failed State Footer

When `campaign.status === 'failed'`, the UX is:
- No Approve/Reject footer (those are for `pending_approval` only)
- No "Publish now" / "Schedule" (those are for `approved` only)
- Show the RetryPanel below the content previews
- The sticky footer area is empty (no sticky actions needed for failed state)

This aligns with UX-DR22 state machine:
> "failed state (Retry panel shown)"

### Project Structure Notes

**New files:**
```
backend/app/workers/publish_retry.py
frontend/components/publishing/RetryPanel.tsx
frontend/__tests__/components/publishing/RetryPanel.test.tsx
```

**Modified files:**
```
backend/app/routers/publishing.py              ← Add POST /publish/retry endpoint
backend/app/routers/campaigns.py               ← Extend GET /campaigns/{id} with publish_job
backend/app/services/publishing.py             ← Add dispatch_publish_for_platform()
backend/app/db/repositories/platform_connections.py  ← Add get_connection_for_platform()
backend/app/db/repositories/jobs.py            ← Add get_publish_job_for_campaign()
backend/tests/routers/test_publishing.py       ← Add retry endpoint tests
backend/tests/services/test_publishing.py      ← Add retry service tests
frontend/lib/api.ts                            ← Add campaignsApi.retryPublish
frontend/lib/types.ts                          ← Add publish_job to Campaign type
frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx  ← Integrate RetryPanel
frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx   ← Add failed state tests
```

### References

- Story 5.5 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 5.5]
- FR-25: Publishing retry — per-platform, 3-attempt cap, persistent job records: [Source: _bmad-output/planning-artifacts/epics.md#FR-25]
- UX-DR15: Approval Gate Retry Panel — platform list, error messages, attempt count, max retries: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR15]
- UX-DR21: Microcopy — "Maximum retries reached — reconnect [Platform] and try again.": [Source: _bmad-output/planning-artifacts/epics.md#UX-DR21]
- UX-DR22: Approval Gate state machine — failed state shows Retry panel: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR22]
- EXPERIENCE.md: Retry Panel behavior — per-platform, attempt count: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Component Patterns]
- EXPERIENCE.md: State Patterns — Approval Gate: failed: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#State Patterns]
- Architecture: BackgroundTask job-first pattern: [Source: _bmad-output/planning-artifacts/architecture.md#FastAPI BackgroundTask Pattern]
- Architecture: services/publishing.py is ONLY place for decrypt_credential: [Source: _bmad-output/planning-artifacts/architecture.md#Hard Service Boundaries]
- Story 5.3 publish worker (run_publish) — pattern for run_publish_retry: [Source: _bmad-output/implementation-artifacts/5-3-immediate-multi-platform-publishing.md#Task 3]
- Story 5.3 error_details schema definition: [Source: _bmad-output/implementation-artifacts/5-3-immediate-multi-platform-publishing.md#Dev Notes]
- Story 5.3 job polling pattern: [Source: _bmad-output/implementation-artifacts/5-3-immediate-multi-platform-publishing.md#Task 9.3]
- Existing ApprovalGateClient.tsx component tree: [Source: frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx]
- Existing GET /campaigns/{id} endpoint (to extend): [Source: backend/app/routers/campaigns.py]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Implemented `dispatch_publish_for_platform()` in `services/publishing.py` — formats PlatformError messages as "Platform returned N — message" per UX-DR21
- Created `workers/publish_retry.py` — loads existing error_details, merges retry result, updates campaign to published/failed based on all_success
- Added `POST /campaigns/{id}/publish/retry` to `routers/publishing.py` with all guards (ownership, status=failed, platform already published, max retries)
- Extended `GET /campaigns/{id}` to return `CampaignDetailResponse` with `publish_job` field (id, attempt_count, error_details, status)
- Created `RetryPanel.tsx` — Paper Style inline panel with per-platform rows, attempt count, per-platform retry buttons with spinners, max retries text
- Integrated RetryPanel into `ApprovalGateClient.tsx`; failed state returns null from `ApprovalPanel` (no Approve/Reject shown)
- Added `psycopg2` and `app.scheduler.scheduler` stubs to `conftest.py` — improved baseline: 70 pre-existing failures → 42 failures (28 fixed by stubs)
- Task 3.3 note: `attempt_count` is per-job (not per-platform) in v1 as documented in Dev Notes
- `get_connection_for_platform` delegates to existing `get_connection` — thin wrapper for semantic clarity

### File List

backend/app/services/publishing.py
backend/app/workers/publish_retry.py
backend/app/routers/publishing.py
backend/app/routers/campaigns.py
backend/app/schemas/campaign.py
backend/app/db/repositories/platform_connections.py
backend/app/db/repositories/jobs.py
backend/tests/conftest.py
backend/tests/routers/test_publish_retry.py
backend/tests/services/test_publish_retry.py
frontend/lib/types.ts
frontend/lib/api.ts
frontend/components/publishing/RetryPanel.tsx
frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx
frontend/app/(app)/campaigns/[id]/approval-panel.tsx
frontend/__tests__/components/publishing/RetryPanel.test.tsx
frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx
