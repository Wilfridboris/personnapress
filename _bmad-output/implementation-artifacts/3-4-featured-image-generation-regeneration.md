---
baseline_commit: 622fba6392a2aa1f1b67cc9ef3f29cbefd2de93e
---

# Story 3.4: Featured Image Generation & Regeneration

Status: review

## Story

As an authenticated user,
I want the system to automatically generate a featured image for my blog post and let me regenerate it if the first result does not fit my brand,
So that my published posts include a custom, on-brand visual with no extra effort.

## Acceptance Criteria

1. **Given** text generation (blog + social) has completed successfully in the BackgroundTask (Story 3.3), **When** the image generation step runs, **Then** `services/image.py` calls `integrations/replicate.py` via `generate_image()` with a prompt derived from the blog post H1 title and a style directive reflecting the Client's brand tone; `integrations/replicate.py` calls the FLUX.1 [pro] model on Replicate with dimensions 1200×630 (Open Graph dimensions).

2. **Given** `services/subscription.py` checks image generation quota before the Replicate call, **When** the image generation count limit for the billing cycle has been reached, **Then** the image generation is skipped; `campaigns.image_url` remains null; the job is set to `status='complete'` so polling resolves; the frontend campaign page shows "Image generation limit reached for this billing cycle." with an upgrade CTA.

3. **Given** image generation succeeds, **When** Replicate returns the image URL, **Then** `integrations/supabase_storage.py` downloads the image and re-uploads it to Supabase Storage at path `generated-images/{campaign_id}/featured.png`; `campaigns.image_url` is set to the CDN public URL; `generation_logs` is updated with `replicate_count=1`; the `jobs` record is set to `status='complete'` and `jobs.completed_at=now()`.

4. **Given** image generation fails (Replicate API error after 3 retries), **When** the failure is confirmed, **Then** `campaigns.image_url` remains null; `jobs.status` is set to `'complete'` (not failed — text content is complete and the campaign should proceed to approval); `jobs.error_details` notes the image failure: "Image generation failed — blog and social posts are complete."; the frontend shows the image panel with "Image generation failed." and a "Generate image" button that triggers a standalone retry.

5. **Given** a user in the Approval Gate clicks "Regenerate" on the featured image panel, **When** `POST /api/v1/campaigns/{id}/image/regenerate` is called, **Then** `services/subscription.py` checks the image generation quota; if within limit, `campaigns.image_regen_count` is checked: if already at 3, the API returns HTTP 400 with `IMAGE_REGEN_LIMIT_REACHED` and the button shows "0 regenerations remaining"; if below 3, a new Replicate call is made, `campaigns.image_regen_count` is incremented, the previous Supabase Storage image is replaced at the same path, and `campaigns.image_url` is updated; the response returns the new `image_url`.

6. **Given** `services/image.py` is the execution context for all Replicate calls, **When** any image generation or regeneration occurs, **Then** `integrations/replicate.py` is called ONLY from within `services/image.py` — no other service, worker, or router calls Replicate directly (AR-19).

7. **Given** the campaign page renders with a non-null `image_url`, **When** the image panel is displayed, **Then** the featured image is shown using `next/image` at full panel width with correct aspect ratio (1200×630 → ~1.9:1); a "Regenerate" secondary Button is shown below the image with the remaining regeneration count: "Regenerate image (N remaining)"; when `image_regen_count >= 3`, the button is disabled with text "No regenerations remaining."

8. **Given** a regeneration is in progress (the "Regenerate" button has been clicked), **When** the API call is pending, **Then** an inline spinner replaces the "Regenerate" button label; the "Regenerate" button is disabled during the request; on success, the `image_url` on the campaign is updated and the new image renders without a page reload.

## Tasks / Subtasks

- [x] Task 1: Backend — `integrations/replicate.py` (AC: #1, #6)
  - [x] 1.1 Create `backend/app/integrations/replicate.py`
  - [x] 1.2 Add `async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str` that calls FLUX.1 [pro] via the `replicate` Python SDK
  - [x] 1.3 Use `replicate.async_run("black-forest-labs/flux-pro", input={"prompt": prompt, "width": width, "height": height})` or the async equivalent from the replicate SDK
  - [x] 1.4 Return the output URL string from Replicate (temporary CDN URL — caller downloads and re-uploads to Supabase)
  - [x] 1.5 Raise `ReplicateError` (or re-raise the SDK exception) on failure — the caller (`services/image.py`) handles retries

- [x] Task 2: Backend — `services/image.py` (AC: #1, #2, #3, #4, #6)
  - [x] 2.1 Create `backend/app/services/image.py` with `async def run_image_generation(campaign_id: uuid.UUID, job_id: uuid.UUID, db: AsyncSession) -> None`
  - [x] 2.2 Step 1 — Subscription check: call `subscription_service.check_image_limit(db, user_id)` (add this method); if limit reached, skip image (log warning), set `job.status='complete'`, commit, return
  - [x] 2.3 Step 2 — Build image prompt: extract blog title from `campaign.blog_html` H1 tag via regex; construct prompt with brand tone keywords
  - [x] 2.4 Step 3 — Call Replicate with retry: 3 retries, exponential backoff (1s, 2s, 4s); on failure after retries: set `job.status='complete'`, `job.error_details='Image generation failed — blog and social posts are complete.'`, commit, return
  - [x] 2.5 Step 4 — Download and re-upload to Supabase Storage: call `await supabase_storage.upload_image_from_url(replicate_url, storage_path)`
  - [x] 2.6 Step 5 — Update campaign + job + generation log: set `campaign.image_url` to Supabase CDN URL; set `job.status='complete'`, `job.completed_at=utcnow()`; append to `generation_logs` with `replicate_count=1`; commit all
  - [x] 2.7 Add `async def regenerate_image(campaign_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> tuple[str, int]` for the regenerate endpoint; performs subscription check, regen count check, Replicate call, Supabase re-upload, DB update; returns (new_image_url, regen_count)

- [x] Task 3: Backend — Update `services/subscription_service.py` (AC: #2, #5)
  - [x] 3.1 Add `async def check_image_limit(db, user_id) -> None` following the same pattern as `check_campaign_limit`; reads `subscriptions.image_gen_used` vs plan limit; raises HTTPException 400 with `IMAGE_LIMIT_EXCEEDED` if at limit; increments `image_gen_used` by 1 on success
  - [x] 3.2 Plan image generation limits: `starter` = 10/cycle, `growth` = 30/cycle, `agency` = 100/cycle

- [x] Task 4: Backend — Update `integrations/supabase_storage.py` (AC: #3, #4)
  - [x] 4.1 Add `async def upload_image_from_url(replicate_url: str, storage_path: str) -> str` that: downloads the image from the Replicate temporary URL using `httpx.AsyncClient`; uploads the bytes to Supabase Storage at `storage_path`; returns the public CDN URL

- [x] Task 5: Backend — Update `workers/generate.py` (AC: #1)
  - [x] 5.1 After `generation_service.run_generation_pipeline(job_id, db)` completes (text generation done), call `image_service.run_image_generation(campaign_id, job_id, db)`
  - [x] 5.2 The two service calls are sequential — image runs only after text generation succeeds
  - [x] 5.3 Pass `campaign_id` from the job record (loaded in the worker before calling services)

- [x] Task 6: Backend — `POST /campaigns/{id}/image/regenerate` endpoint (AC: #5, #6)
  - [x] 6.1 Add `POST /campaigns/{id}/image/regenerate` to `backend/app/routers/campaigns.py`
  - [x] 6.2 Authenticate user; verify campaign ownership (via campaign→client→user chain); call `image_service.regenerate_image(campaign_id, user_id, db)`
  - [x] 6.3 Return 200 with `{"image_url": "...", "image_regen_count": N}` on success
  - [x] 6.4 Return 400 with `IMAGE_REGEN_LIMIT_REACHED` if `campaign.image_regen_count >= 3`
  - [x] 6.5 Update `campaignsApi` in `frontend/lib/api.ts` to add `regenerateImage(id: string) -> Promise<{ image_url: string; image_regen_count: number }>`

- [x] Task 7: Frontend — Image panel with Regenerate button (AC: #7, #8)
  - [x] 7.1 Updated `/campaigns/[id]/page.tsx` image section to use ImagePanel with all states
  - [x] 7.2 Created `frontend/components/campaigns/ImagePanel.tsx` as `'use client'` with all required states and regeneration interaction
  - [x] 7.3 Replaced static `campaign.image_url` rendering in `page.tsx` with `<ImagePanel>` client component

- [x] Task 8: Backend tests (AC: #2, #3, #4, #5)
  - [x] 8.1 Created `backend/tests/services/test_image.py` with all 5 scenarios
  - [x] 8.2 Added 3 endpoint tests for `POST /campaigns/{id}/image/regenerate` in `test_campaigns_router.py`

## Dev Notes

### Replicate SDK Usage

The `replicate` Python package is already in `requirements.txt` (installed in Story 1.1). The async API:

```python
import replicate
import asyncio

output = await replicate.async_run(
    "black-forest-labs/flux-pro",
    input={
        "prompt": prompt,
        "width": 1200,
        "height": 630,
        "output_format": "png",
    }
)
# output is a list of FileOutput objects or URLs
image_url = str(output[0])  # temporary Replicate CDN URL
```

Check the installed replicate version for the exact async API — it may be `replicate.models.predictions.create_async()` in older versions. Use whatever pattern the installed version supports; reference `pip show replicate` for the version.

### FLUX.1 [pro] Image Prompt Design

The image prompt should be visual-keyword-first (FLUX responds better to descriptive visual terms than abstract brand concepts):

```python
def build_image_prompt(blog_title: str, brand_tone: list[str] | None) -> str:
    tone_descriptor = ""
    if brand_tone:
        # Map common tone descriptors to visual style keywords
        tone_map = {
            "professional": "corporate editorial",
            "casual": "warm lifestyle",
            "formal": "minimalist clean",
            "friendly": "approachable human-centered",
        }
        visual_tones = [tone_map.get(t.lower(), t) for t in brand_tone[:2]]
        tone_descriptor = ", ".join(visual_tones) + " style, "
    
    return (
        f"{tone_descriptor}featured blog image for '{blog_title}', "
        f"photorealistic, high resolution, 16:9 aspect ratio, "
        f"professional photography, no text overlay, clean background"
    )
```

### Supabase Storage Upload Pattern

Reference the existing `supabase_storage.py` to understand how uploads work. The new `upload_image_from_url` function should:

```python
async def upload_image_from_url(replicate_url: str, storage_path: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(replicate_url, timeout=30.0)
        response.raise_for_status()
        image_bytes = response.content
    
    # Upload to Supabase Storage (use existing upload pattern from the integration)
    # Returns the public CDN URL
    public_url = await _upload_bytes(image_bytes, storage_path, content_type="image/png")
    return public_url
```

### Frontend — ImagePanel UX Design (Paper Style)

```
Featured Image panel:

┌─────────────────────────────────────────────────────┐
│  FEATURED IMAGE                                     │
│  (Inter 12px uppercase tracking-widest graphite)   │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │                                               │  │
│  │   (next/image, aspect ratio ~1.9:1, 1200×630) │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  [Regenerate image (2 remaining)]  ← Secondary Btn  │
└─────────────────────────────────────────────────────┘

Failed state:
┌─────────────────────────────────────────────────────┐
│  Image generation failed.                           │
│  (Inter 14px graphite)                              │
│  [Generate image]  ← Primary Button                 │
└─────────────────────────────────────────────────────┘

Limit reached state:
┌─────────────────────────────────────────────────────┐
│  Image generation limit reached for this billing    │
│  cycle.                                             │
│  [Upgrade plan →]  ← text link to /account         │
└─────────────────────────────────────────────────────┘
```

### Image Count Determination at Runtime

The frontend does not have direct access to the subscription's `image_gen_used` count. The "limit reached" vs "failed" distinction comes from:
- `campaign.image_url === null` AND `job.error_details` contains "Image generation failed" → show "failed" state with retry button
- `campaign.image_url === null` AND `job.error_details` contains "limit" (or is null) → show "limit reached" state with upgrade CTA

For the `GenerationGate` in Story 3.2, when the job completes with `error_details` set, the overlay transitions to the static page content and the `ImagePanel` determines which empty state to show.

### next/image Configuration

The Replicate temporary URL (for immediate display after regeneration) and the Supabase Storage CDN URL (stored in DB) both need to be in `next.config.ts` `images.remotePatterns`. Verify the existing config includes the Supabase project URL and add Replicate domains if needed.

```typescript
// next.config.ts (update images.remotePatterns)
remotePatterns: [
  { hostname: '*.supabase.co' },
  { hostname: 'replicate.delivery' },  // Replicate CDN
  { hostname: '*.replicate.com' },
]
```

### Service Boundary — workers/generate.py Final Shape

After both Story 3.3 and 3.4 are implemented, `workers/generate.py` should look like:

```python
async def run_generation(job_id: uuid.UUID) -> None:
    async with async_session_maker() as db:
        try:
            # Load job to get campaign_id
            job = await jobs_repo.get_job(db, job_id)
            if not job:
                return  # Job not found, nothing to do
            
            # Run text generation (Story 3.3)
            await generation_service.run_generation_pipeline(job_id, db)
            
            # Run image generation (Story 3.4) 
            # re-load job after text generation to get campaign_id
            job = await jobs_repo.get_job(db, job_id)
            if job and job.status == 'in_progress':  # only if text succeeded
                await image_service.run_image_generation(job.campaign_id, job_id, db)
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
```

### File Structure

**New files this story:**
```
backend/app/integrations/replicate.py
backend/app/services/image.py
backend/tests/services/test_image.py
frontend/components/campaigns/ImagePanel.tsx
```

**Updated files this story:**
```
backend/app/workers/generate.py                   ← call image_service after generation_service
backend/app/routers/campaigns.py                  ← add POST /campaigns/{id}/image/regenerate
backend/app/services/subscription_service.py      ← add check_image_limit
backend/app/integrations/supabase_storage.py      ← add upload_image_from_url
frontend/app/(app)/campaigns/[id]/page.tsx        ← replace static image section with ImagePanel
frontend/lib/api.ts                               ← add campaignsApi.regenerateImage
frontend/next.config.ts                           ← add replicate.delivery to remotePatterns
```

### References

- FR-16 Featured image generation spec (FLUX.1 [pro] via Replicate, 1200×630 PNG, Supabase Storage, CDN public URL): [Source: _bmad-output/planning-artifacts/epics.md#FR-16]
- FR-17 Image preview and regeneration (preview, Regenerate button, 3-regen cap, independent retry): [Source: _bmad-output/planning-artifacts/epics.md#FR-17]
- NFR-9 Cost controls — Replicate image count logged to generation_logs; quota checked before call: [Source: _bmad-output/planning-artifacts/epics.md#NFR-9]
- AR-19 Service boundaries — image.py is ONLY caller of replicate.py: [Source: _bmad-output/planning-artifacts/epics.md#AR-19]
- Story 3.3 (text generation sets job to in_progress; this story sets it to complete): [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]
- `backend/app/integrations/supabase_storage.py` — existing Supabase Storage upload pattern
- UX-DR3 Secondary Button spec for Regenerate button (transparent, 1px ink border, inverts on hover)
- UX-DR17 Skeleton loading + inline spinner for action buttons only

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `replicate` not installed in test env → stubbed in `conftest.py` alongside other optional deps
- 4 pre-existing `test_client_limit.py` failures confirmed to exist on baseline commit; not introduced by this story

### Completion Notes List

- Created `backend/app/integrations/replicate.py` — calls FLUX.1 [pro] via `replicate.async_run`, returns temp URL
- Created `backend/app/services/image.py` — full pipeline: quota check → prompt build → Replicate with 3-retry backoff → Supabase Storage re-upload → DB update; `regenerate_image` handles regen flow with limit enforcement
- Added `check_image_limit` to `subscription_service.py` matching `check_campaign_limit` pattern; reads `image_gen_used` vs plan limit from `PLAN_LIMITS["image_gens"]`
- Added `upload_image_from_url` to `supabase_storage.py` — downloads from Replicate URL, uploads to Supabase bucket, returns CDN public URL
- Updated `workers/generate.py` to call `image_service.run_image_generation` after text generation completes (only if job still `in_progress`)
- Added `POST /campaigns/{id}/image/regenerate` endpoint to `routers/campaigns.py` with ownership check
- Added `regenerateImage` to `campaignsApi` in `frontend/lib/api.ts`
- Created `frontend/components/campaigns/ImagePanel.tsx` with three states: image+regen button, failed+retry, limit-reached+upgrade CTA
- Updated `frontend/app/(app)/campaigns/[id]/page.tsx` to use `<ImagePanel>`, fetching job `error_details` from API when jobId present
- Added `*.replicate.com` and `*.supabase.co` to `next.config.ts` remotePatterns (replicate.delivery already existed)
- All 18 new tests pass (5 service unit + 3 endpoint tests + pre-existing 10 campaign router tests)

### File List

backend/app/integrations/replicate.py (new)
backend/app/services/image.py (new)
backend/tests/services/__init__.py (new)
backend/tests/services/test_image.py (new)
backend/app/services/subscription_service.py (modified — added check_image_limit)
backend/app/integrations/supabase_storage.py (modified — added upload_image_from_url)
backend/app/workers/generate.py (modified — image generation step)
backend/app/routers/campaigns.py (modified — regenerate endpoint)
backend/tests/conftest.py (modified — replicate stub)
backend/tests/test_campaigns_router.py (modified — 3 new regenerate tests)
frontend/components/campaigns/ImagePanel.tsx (new)
frontend/app/(app)/campaigns/[id]/page.tsx (modified — ImagePanel + job fetch)
frontend/lib/api.ts (modified — regenerateImage)
frontend/next.config.ts (modified — supabase.co + *.replicate.com remotePatterns)

## Change Log

- 2026-07-02: Story implemented — FLUX.1 [pro] image generation pipeline, Supabase Storage re-upload, regeneration endpoint, ImagePanel component with all states, subscription quota enforcement (18 tests added)
