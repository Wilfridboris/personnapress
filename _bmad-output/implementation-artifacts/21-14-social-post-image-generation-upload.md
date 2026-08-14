---
baseline_commit: 7a422db
---

# Story 21.14: Social Post AI Image Generation and Upload

Status: done

---

## Story

As a PersonnaPress user creating a social-only campaign,
I want to opt in to AI image generation during the brain dump,
so that my social posts have a featured image for Instagram and visual context on other platforms.

As a PersonnaPress user reviewing a social-only campaign,
I want the full ImagePanel (generate / upload / replace) available in the approval gate,
so that I can add or change the campaign image before publishing.

---

## Context and Motivation

Story 21-13 added a read-only image thumbnail to `SocialPostEditors` and an Instagram skip warning -- but only for campaigns that already had an image. Social-only campaigns (`campaign_type="social_only"`) currently never generate an image because three separate gaps prevent it:

1. **Brain dump** forces `skip_image: true` for social_only regardless of the checkbox state (line 275 of `campaigns/new/page.tsx`)
2. **Approval gate** suppresses `ImagePanel` for social_only (`{!isSocialOnly && <ImagePanel />}` in `ApprovalGateClient.tsx:198`)
3. **Worker** exits before image generation for social_only -- `run_social_only_pipeline` marks the job `complete` (line 333 of `generation.py`) before returning, so the worker's skip_image gate never runs

This story closes all three gaps. The fix is intentionally minimal -- no new DB columns, no new API endpoints, no new components.

### What is NOT in scope

- Platform-specific image sizes (Instagram 1:1 square vs. 16:9 landscape) -- deferred to Story 21-15
- Roadmap post image generation -- roadmap posts (`isRoadmapSocialPost=true`) already show ImagePanel; no changes to their behavior
- Any new backend API endpoints or Alembic migrations

---

## Acceptance Criteria

### AC 1: Brain dump -- AI image checkbox shows for social_only

**Given** the user selects "Social post only" content type,
**When** the brain dump page renders,
**Then** the "AI featured image" checkbox appears in the same position as it does for blog_full (below the textarea section, before the submit button).
**And** the checkbox defaults to checked.
**And** when unchecked, the hint text reads: "Upload your own image from the approval page."

---

### AC 2: skip_image logic respects the checkbox for social_only

**Given** the user selects "Social post only" and leaves "AI featured image" checked,
**When** they submit the brain dump,
**Then** `skip_image: false` is sent to the API (image will be generated during the job).

**Given** the user selects "Social post only" and unchecks "AI featured image",
**When** they submit the brain dump,
**Then** `skip_image: true` is sent (no image generation, upload from approval page).

---

### AC 3: Content type descriptions and status note updated

**Given** any user on the brain dump page,
**When** the content type fieldset renders,
**Then** "Blog + Social" description reads: "Blog post, social posts, and featured image"
**And** "Social post only" description reads: "Social posts for all connected platforms - no blog article. Featured image optional."
**And** the inline note shown when social_only is selected reads: "Shorter generation time. Publish to all connected social platforms after approval."

---

### AC 4: Worker runs image generation for social_only when skip_image=False

**Given** a social_only campaign with skip_image=False,
**When** the generation worker runs,
**Then** `run_social_only_pipeline` completes text generation and leaves `job.status = "in_progress"` (not "complete"),
**And** the worker applies the skip_image gate (same pattern as blog_full),
**And** `image_service.run_image_generation` is called.

**Given** a social_only campaign with skip_image=True,
**When** the generation worker runs,
**Then** after `run_social_only_pipeline` returns, the worker marks the job complete without calling image generation.

---

### AC 5: Approval gate -- ImagePanel renders for social-only campaigns

**Given** a social_only campaign in any status,
**When** the approval gate renders,
**Then** `ImagePanel` is rendered (generate / upload / replace controls available).

**Given** a roadmap social post (`isRoadmapSocialPost=true`),
**When** the approval gate renders,
**Then** `ImagePanel` is NOT rendered (behavior unchanged).

---

### AC 6: Approval gate aside fills full width for hideBlogSection campaigns

**Given** any campaign where `hideBlogSection=true` (social_only or roadmap),
**When** the approval gate renders on desktop (lg breakpoint),
**Then** the aside uses `lg:col-span-2`, spanning both columns of the 2-col grid -- no empty right column.
**And** ImagePanel is stacked above SocialPostEditors inside the full-width aside.

---

### AC 7: Existing behavior fully preserved

**Given** a blog_full campaign,
**When** the brain dump or approval gate renders,
**Then** all existing behavior is unchanged: checkbox visibility, skip_image logic, ImagePanel, aside class, SocialPostEditors thumbnail.

---

## Files to Modify

| File | Change |
|---|---|
| `frontend/app/(app)/campaigns/new/page.tsx` | Remove blog_full guard on checkbox; fix skip_image; update 3 copy strings |
| `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` | Guard change + aside class simplification |
| `backend/app/services/generation.py` | Remove job.status="complete" from run_social_only_pipeline |
| `backend/app/workers/generate.py` | Add skip_image gate after social_only pipeline |
| `backend/tests/test_generation_service.py` | Update 2 existing tests + add 2 new worker tests |

---

## Dev Notes

### 1. Brain dump page -- `campaigns/new/page.tsx`

**Change 1: Remove the `blog_full` guard on the image checkbox.**

Find this block (around line 638):
```tsx
{campaignType === "blog_full" && (
  <div className="mb-6">
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={generateImage}
        onChange={(e) => setGenerateImage(e.target.checked)}
        ...
      />
      ...
    </label>
  </div>
)}
```

Remove the outer `{campaignType === "blog_full" && (` conditional entirely. The `<div className="mb-6">` block renders unconditionally for both campaign types.

**Change 2: Fix skip_image logic (around line 275 inside `handleSubmit`).**

```tsx
// BEFORE:
skip_image: campaignType === "social_only" ? true : !generateImage,

// AFTER:
skip_image: !generateImage,
```

The `useEffect` at lines 105-108 already resets `generateImage` to `true` on every `campaignType` change -- no additional change needed there.

**Change 3: Update 3 copy strings.**

| Location | Old text | New text |
|---|---|---|
| Line 446 (`ct-blog-desc`) | "Blog post, X and LinkedIn posts, featured image" | "Blog post, social posts, and featured image" |
| Line 469 (`ct-social-desc`) | "X and LinkedIn posts only, no blog or featured image" | "Social posts for all connected platforms - no blog article. Featured image optional." |
| Lines 478-480 (status note) | "Shorter generation time. You can publish directly to X and LinkedIn after approval." | "Shorter generation time. Publish to all connected social platforms after approval." |

No em-dashes anywhere. Use hyphens only.

---

### 2. ApprovalGateClient.tsx -- two changes

**Change 1: Guard on ImagePanel (around line 198).**

```tsx
// BEFORE:
{!isSocialOnly && (
  <ImagePanel
    campaignId={campaign.id}
    clientId={campaign.client_id}
    imageUrl={campaign.image_url}
    imageAlt={campaign.image_alt ?? undefined}
    imageRegenCount={campaign.image_regen_count}
    jobErrorDetails={jobErrorDetails ?? null}
    isGenerating={jobIsActive}
  />
)}

// AFTER:
{!isRoadmapSocialPost && (
  <ImagePanel
    campaignId={campaign.id}
    clientId={campaign.client_id}
    imageUrl={campaign.image_url}
    imageAlt={campaign.image_alt ?? undefined}
    imageRegenCount={campaign.image_regen_count}
    jobErrorDetails={jobErrorDetails ?? null}
    isGenerating={jobIsActive}
  />
)}
```

`isRoadmapSocialPost` is already computed at line 90: `const isRoadmapSocialPost = !!campaign.roadmap_id && campaign.blog_html === null;` -- no new variable needed.

Effect on each campaign type:
- blog_full: `isRoadmapSocialPost=false` → shows ImagePanel (unchanged) ✓
- social_only brain dump: `isRoadmapSocialPost=false` → shows ImagePanel (NEW) ✓
- roadmap social: `isRoadmapSocialPost=true` → hides ImagePanel (unchanged) ✓

**Change 2: Simplify aside class (around line 197).**

```tsx
// BEFORE:
<aside className={hideBlogSection ? "space-y-8" : "lg:col-span-2 space-y-8"}>

// AFTER:
<aside className="lg:col-span-2 space-y-8">
```

`lg:col-span-2` is valid in both grids:
- `hideBlogSection` uses `lg:grid-cols-2`: col-span-2 fills the full width (both columns) ✓
- `!hideBlogSection` uses `lg:grid-cols-5`: col-span-2 is 2/5 width (right panel, unchanged) ✓

The result for social_only and roadmap: ImagePanel stacked above SocialPostEditors, full-width aside, no empty right column. Same stacked layout roadmap posts have always used -- consistent visual language across all social campaign types.

The SocialPostEditors inline image thumbnail (from 21-13) remains visible -- it serves as a reference while the user types, since ImagePanel may scroll out of view above.

---

### 3. Backend: `generation.py` -- `run_social_only_pipeline`

Remove the job completion lines at the end of the `try` block (around line 333). Leave the campaign commit in place.

```python
# BEFORE (lines 329-337):
        campaign.x_post = x_post
        campaign.linkedin_post = linkedin_post
        campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        logger.info("run_social_only_pipeline: campaign %s complete", campaign.id)

# AFTER:
        campaign.x_post = x_post
        campaign.linkedin_post = linkedin_post
        campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        logger.info(
            "run_social_only_pipeline: campaign %s text complete, returning to worker",
            campaign.id,
        )
```

The job stays `in_progress`. The worker re-reads job status after the pipeline returns and applies the skip_image gate (see next section).

The `_fail_job` path in the `except` block is unchanged -- failures still mark the job as "failed" immediately.

---

### 4. Backend: `generate.py` -- worker skip_image gate for social_only

Add the image generation gate after `run_social_only_pipeline`. Mirror the existing blog_full pattern exactly.

```python
# BEFORE:
            if campaign_type == "social_only":
                await generation_service.run_social_only_pipeline(job_id, db)
            else:
                # Full pipeline: text then image
                await generation_service.run_generation_pipeline(job_id, db)

                # Image generation -- runs only after text succeeds and skip_image is False
                job = await get_job(db, job_id)
                if job and job.status == "in_progress" and job.campaign_id:
                    campaign_check = await get_campaign(db, job.campaign_id)
                    if campaign_check and campaign_check.skip_image:
                        job.status = "complete"
                        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        await db.commit()
                        logger.info(
                            "run_generation: skip_image=True, image skipped for campaign %s",
                            job.campaign_id,
                        )
                    else:
                        await image_service.run_image_generation(job.campaign_id, job_id, db)

# AFTER:
            if campaign_type == "social_only":
                await generation_service.run_social_only_pipeline(job_id, db)

                # Image generation gate -- same pattern as blog_full
                job = await get_job(db, job_id)
                if job and job.status == "in_progress" and job.campaign_id:
                    campaign_check = await get_campaign(db, job.campaign_id)
                    if campaign_check and campaign_check.skip_image:
                        job.status = "complete"
                        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        await db.commit()
                        logger.info(
                            "run_generation: skip_image=True, image skipped for social_only campaign %s",
                            job.campaign_id,
                        )
                    else:
                        await image_service.run_image_generation(job.campaign_id, job_id, db)
            else:
                # Full pipeline: text then image (unchanged)
                await generation_service.run_generation_pipeline(job_id, db)

                # Image generation -- runs only after text succeeds and skip_image is False
                job = await get_job(db, job_id)
                if job and job.status == "in_progress" and job.campaign_id:
                    campaign_check = await get_campaign(db, job.campaign_id)
                    if campaign_check and campaign_check.skip_image:
                        job.status = "complete"
                        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        await db.commit()
                        logger.info(
                            "run_generation: skip_image=True, image skipped for campaign %s",
                            job.campaign_id,
                        )
                    else:
                        await image_service.run_image_generation(job.campaign_id, job_id, db)
```

---

### 5. Backend tests -- `test_generation_service.py`

**Update `test_run_social_only_pipeline_success` (around line 452):**

The pipeline no longer marks the job complete. Update the assertion:

```python
# BEFORE:
    assert job.status == "complete"

# AFTER:
    assert job.status == "in_progress"
    assert campaign.x_post == ...
    assert campaign.linkedin_post == ...
```

**Rename and update `test_run_social_only_pipeline_no_image_generated` (around line 521):**

This test verified the OLD behavior. Repurpose it to confirm the pipeline leaves the job in_progress:

```python
async def test_run_social_only_pipeline_leaves_job_in_progress(mock_llm):
    """run_social_only_pipeline leaves job in_progress so worker can gate image generation."""
    from app.services.generation import run_social_only_pipeline

    job = _make_job()
    campaign = _make_campaign(campaign_type="social_only")
    client = _make_client()
    mock_llm.generate_social_standalone.return_value = {"x_post": "x", "linkedin_post": "li"}

    db = _make_db_social_only(job, campaign, client)
    await run_social_only_pipeline(job.id, db)

    assert job.status == "in_progress"  # worker handles completion
```

**Add 2 new worker-level tests** (add to the `# -- run_generation worker skip_image gate` section, after the existing blog_full tests):

```python
async def test_run_generation_social_only_skip_image_false_calls_image_generation(
    mock_llm, mock_sentry
):
    """social_only + skip_image=False: image_service.run_image_generation is called."""
    # Use the existing _make_worker_campaign helper with campaign_type="social_only"
    # and skip_image=False. Mock run_social_only_pipeline to leave job in_progress.
    # Assert image_service.run_image_generation is called once.

async def test_run_generation_social_only_skip_image_true_skips_image_generation(
    mock_llm, mock_sentry
):
    """social_only + skip_image=True: image_service.run_image_generation not called, job complete."""
    # Use _make_worker_campaign with campaign_type="social_only", skip_image=True.
    # Mock run_social_only_pipeline to leave job in_progress.
    # Assert image_service.run_image_generation is NOT called.
    # Assert job.status == "complete".
```

Follow the exact mock patterns used by the existing `test_run_generation_skip_image_true_skips_image_generation` and `test_run_generation_skip_image_false_calls_image_generation` tests in the same file. The `_make_worker_campaign` helper already accepts `campaign_type` and `skip_image` kwargs (line 551).

---

## Key Constraints

- **No DB migration** -- `skip_image`, `image_url`, `image_regen_count` columns all exist
- **No new API endpoints** -- image generation and upload reuse existing endpoints
- **No new frontend components** -- ImagePanel and the checkbox are existing components
- **Paper Style** -- no visual design changes; no emojis; no em-dashes in any copy
- **Roadmap posts unchanged** -- guard changes from `!isSocialOnly` to `!isRoadmapSocialPost`; roadmap social posts keep their current behavior (no ImagePanel)
- **`isRoadmapSocialPost` is already defined** in ApprovalGateClient.tsx at line 90 -- do not redefine

---

## Future Story Note

**Story 21-15 (deferred): Platform-Native Image Sizing for Social**

Generate an Instagram-optimized square (1:1) image variant alongside the standard 16:9 for social campaigns. A landscape image is valid for Instagram today and this story unblocks the core value. Platform-specific sizing is a follow-on quality improvement requiring:
- DB migration: `instagram_image_url` column (or `social_image_url`)
- Worker: dual image generation call when Instagram is connected and skip_image=False
- `publish_instagram_feed_post`: use the square variant when available
- Approval gate: show both variants or label the image with its target platform

---

## File List

- `frontend/app/(app)/campaigns/new/page.tsx`
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`
- `backend/app/services/generation.py`
- `backend/app/workers/generate.py`
- `backend/tests/test_generation_service.py`

---

## Dev Agent Record

### Completion Notes

- Removed `job.status = "complete"` from `run_social_only_pipeline`; worker now handles completion via skip_image gate (same pattern as blog_full).
- Added image generation gate in `generate.py` for `social_only` branch, mirroring the existing blog_full pattern exactly.
- Removed `blog_full` guard on checkbox in `campaigns/new/page.tsx`; checkbox now renders unconditionally for both campaign types.
- Fixed `skip_image` logic: `!generateImage` (was `campaignType === "social_only" ? true : !generateImage`).
- Updated 3 copy strings: ct-blog-desc, ct-social-desc, and the status note -- no em-dashes.
- Changed `ApprovalGateClient.tsx` aside class from conditional to `lg:col-span-2` unconditionally.
- Changed `ImagePanel` guard from `!isSocialOnly` to `!isRoadmapSocialPost`.
- Updated `test_run_social_only_pipeline_success`: `assert job.status == "in_progress"`.
- Renamed and updated `test_run_social_only_pipeline_no_image_generated` to `test_run_social_only_pipeline_leaves_job_in_progress`.
- Added 2 new worker tests: `test_run_generation_social_only_skip_image_false_calls_image_generation` and `test_run_generation_social_only_skip_image_true_skips_image_generation`.
- All 20 tests pass; pre-existing BlogEditor.test.tsx TypeScript errors confirmed unrelated.

### Review Findings

- [x] [Review][Defer] No warning log when post-pipeline `get_job` returns None or non-in_progress status [backend/app/workers/generate.py:44] — deferred, pre-existing pattern shared with blog_full branch
- [x] [Review][Defer] `campaign_check` re-fetch is a redundant TOCTOU window [backend/app/workers/generate.py:45] — deferred, pre-existing pattern in blog_full branch; no behavior impact
- [x] [Review][Defer] No test for post-pipeline `get_job` returning None [backend/tests/test_generation_service.py] — deferred, pre-existing gap; blog_full worker tests also omit this edge case

## Change Log

- 2026-08-14: Story 21.14 created ready-for-dev -- social_only image generation: brain dump checkbox ungated, skip_image logic fixed, worker gate added, ImagePanel shown in approval gate, aside col-span-2 fix, 2 test updates + 2 new worker tests.
- 2026-08-14: Implemented -- all 5 files modified, 20 backend tests pass, status set to review.
- 2026-08-14: Code review complete: 0 patches applied, 3 deferred, 9 dismissed, marked done.
