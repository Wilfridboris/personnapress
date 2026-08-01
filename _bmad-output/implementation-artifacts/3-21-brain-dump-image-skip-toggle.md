---
baseline_commit: 1a6c572
depends_on: 3-20-social-only-brain-dump-mode
---

# Story 3.21: Brain Dump Image Skip Toggle

Status: done

## Story

As a PersonnaPress user who wants to publish quickly or use my own image,
I want to uncheck "AI featured image" on the brain dump page,
so that image generation is skipped for that campaign and I can upload my own image from the approval page.

## Context & Motivation

Image generation is the slowest and most credit-intensive step in the generation pipeline. Some
users already know the image the AI will produce won't be suitable for their brand -- they have
a product screenshot, a photo from an event, or a custom graphic ready. Others want to publish
faster without waiting for image generation.

Currently there is no way to opt out: image generation always runs. The `ImagePanel` component
already handles the "no image" state gracefully with an "Upload image" button -- the only missing
piece is a way to signal at creation time that generation should be skipped.

**Dependency:** This story depends on Story 3-20 being done. Story 3-20 added `campaign_type` to
the Campaign model and its Alembic migration. This story adds a second column (`skip_image`) in a
new migration, and reuses the same brain dump page patterns established in Story 3-20.

**Social-only interaction:** When `campaign_type = "social_only"` (Story 3-20), `skip_image` is
always forced `true` by both the UI and the backend. The checkbox is hidden in social-only mode.

---

## Acceptance Criteria

### AC 1 -- AI featured image checkbox on brain dump page

**Given** the user is on `/campaigns/new` with "Blog + Social" content type selected,
**When** the page loads,
**Then** an "AI featured image" checkbox appears below the Target audience field and above the
Generate button:
- Checked by default
- Label: `font-mono text-xs text-graphite uppercase tracking-widest` -- "AI featured image"
- When unchecked: an `aria-live="polite"` note appears below: "Upload your own image from the approval page."

### AC 2 -- Checkbox hidden for social-only campaigns

**Given** the user has selected "Social post only" content type (Story 3-20),
**When** the checkbox would otherwise be visible,
**Then** the entire image checkbox control is hidden (not rendered).
There is no need to show or explain it -- social-only campaigns never generate images.

### AC 3 -- `skip_image` stored on Campaign model

**Given** a brain dump is submitted with the AI image checkbox unchecked,
**When** the POST /campaigns request is received,
**Then** the Campaign row is created with `skip_image = true`.
When submitted with the checkbox checked (or not provided), `skip_image = false`.
When `campaign_type = "social_only"`, `skip_image` is forced to `true` regardless of the
checkbox value in the request body.

### AC 4 -- Image generation skipped when `skip_image = true`

**Given** a campaign with `skip_image = true` has a pending blog_full generation job,
**When** the worker runs the full pipeline and text generation succeeds,
**Then** `image_service.run_image_generation()` is NOT called.
The job is marked `status = "complete"` with `completed_at` set immediately after text generation.
The campaign proceeds to `pending_approval` with `image_url = null`.

### AC 5 -- ImagePanel shows upload state immediately

**Given** a campaign with `skip_image = true` reaches `pending_approval`,
**When** the user opens the approval gate,
**Then** the `ImagePanel` renders the "no image" state (which already exists) showing:
- "No featured image yet."
- A "Generate image" button (triggers manual regen, costs credit as normal)
- An "Upload image" button

No spinner, no "generating..." placeholder. The panel goes directly to the actionable state.

### AC 6 -- Regeneration preserves `skip_image`

**Given** a campaign with `skip_image = true` is rejected and the user clicks "Regenerate",
**When** POST /campaigns/{id}/regenerate is called,
**Then** the new Campaign row is created with `skip_image = true` (copied from the original).
The new job respects the flag and also skips image generation.

### AC 7 -- `skip_image` exposed in API responses

**Given** the GET /campaigns or GET /campaigns/{id} endpoint returns a campaign,
**When** the campaign was created with `skip_image = true`,
**Then** `skip_image: true` is present in the JSON response.
For existing campaigns (before migration), the field returns `false`.

---

## Implementation Blueprint

### 1. Alembic migration

File: `backend/alembic/versions/YYYYMMDD_HHMM_<hash>_add_campaign_skip_image.py`

This is a NEW migration that runs AFTER the Story 3-20 migration (`add_campaign_type`).

```python
def upgrade():
    op.add_column(
        "campaigns",
        sa.Column("skip_image", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE campaigns SET skip_image = false WHERE skip_image IS NULL")
    op.alter_column("campaigns", "skip_image", nullable=False, server_default=sa.false())

def downgrade():
    op.drop_column("campaigns", "skip_image")
```

### 2. Campaign model (`backend/app/db/repositories/models.py`)

Add to the `Campaign` SQLModel class (after `campaign_type`):
```python
skip_image: bool = Field(
    default=False,
    sa_column=Column(Boolean, nullable=False, server_default=false()),
)
```
Import `false` from `sqlalchemy` if not already present.

### 3. Campaign schema (`backend/app/schemas/campaign.py`)

`CampaignCreate` -- add:
```python
skip_image: bool = False
```

`CampaignResponse` / `CampaignDetailResponse` -- add:
```python
skip_image: bool = False
```

### 4. Campaign repository (`backend/app/db/repositories/campaigns.py`)

`create_campaign()` -- add param:
```python
async def create_campaign(
    ...,
    campaign_type: str = "blog_full",   # added in Story 3-20
    skip_image: bool = False,           # new
) -> Campaign:
    campaign = Campaign(
        ...,
        campaign_type=campaign_type,
        skip_image=skip_image,
    )
```

### 5. Campaigns router (`backend/app/routers/campaigns.py`)

`create_new_campaign` -- enforce social_only → skip_image=True, then pass:
```python
effective_skip_image = True if body.campaign_type == "social_only" else body.skip_image

campaign = await create_campaign(
    db,
    body.client_id,
    body.brain_dump,
    target_keyword=body.target_keyword,
    target_audience=body.target_audience,
    secondary_keywords=body.secondary_keywords,
    campaign_type=body.campaign_type,
    skip_image=effective_skip_image,
)
```

`regenerate_campaign` -- copy from original:
```python
new_campaign = await create_campaign(
    db,
    campaign.client_id,
    campaign.brain_dump,
    target_keyword=campaign.target_keyword,
    target_audience=campaign.target_audience,
    secondary_keywords=campaign.secondary_keywords,
    campaign_type=campaign.campaign_type,
    skip_image=campaign.skip_image,     # preserve flag
)
```

### 6. Worker (`backend/app/workers/generate.py`)

In the `blog_full` branch (after `run_generation_pipeline` succeeds), gate the image call:

```python
if campaign_type == "social_only":
    await generation_service.run_social_only_pipeline(job_id, db)
else:
    await generation_service.run_generation_pipeline(job_id, db)

    # Image step: only if text succeeded AND skip_image is False
    job = await get_job(db, job_id)
    if job and job.status == "in_progress" and job.campaign_id:
        # Re-load campaign to read skip_image (campaign ref may be stale)
        from app.db.repositories.campaigns import get_campaign
        fresh_campaign = await get_campaign(db, job.campaign_id)
        if fresh_campaign and fresh_campaign.skip_image:
            # Mark complete without image
            job.status = "complete"
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            async with AsyncSessionLocal() as complete_db:
                # Use a fresh session to commit the job completion
                complete_job = await get_job(complete_db, job_id)
                if complete_job:
                    complete_job.status = "complete"
                    complete_job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    await complete_db.commit()
            logger.info("run_generation: skip_image=True for campaign %s, job %s marked complete", job.campaign_id, job_id)
        else:
            await image_service.run_image_generation(job.campaign_id, job_id, db)
```

**Simpler alternative** (recommended): The worker already has the `db` session open.
`run_generation_pipeline` does NOT close the session. The job is refreshed on line 38.
The simplest approach is to re-load the campaign after `run_generation_pipeline` and check `skip_image`:

```python
else:
    # Full pipeline
    await generation_service.run_generation_pipeline(job_id, db)

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

Use the simpler form. Do NOT open a second session. The existing session `db` is valid at this point.

### 7. Frontend: `lib/types.ts`

Add to `Campaign`:
```ts
skip_image: boolean;
```

Add to `CampaignCreate`:
```ts
skip_image?: boolean;
```

### 8. Frontend: `campaigns/new/page.tsx`

New state (add alongside `campaignType` from Story 3-20):
```ts
const [generateImage, setGenerateImage] = useState(true);
```

**Image checkbox** -- placed between Target audience field and the Generate button:
```tsx
{campaignType === "blog_full" && (
  <div className="mb-6">
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        checked={generateImage}
        onChange={(e) => setGenerateImage(e.target.checked)}
        className="mt-0.5 accent-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
        aria-describedby={generateImage ? undefined : "image-skip-hint"}
      />
      <span className="flex flex-col gap-0.5">
        <span className="font-mono text-xs text-graphite uppercase tracking-widest">
          AI featured image
        </span>
        {!generateImage && (
          <span
            id="image-skip-hint"
            role="status"
            aria-live="polite"
            className="font-mono text-xs text-graphite"
          >
            Upload your own image from the approval page.
          </span>
        )}
      </span>
    </label>
  </div>
)}
```

**handleSubmit** -- add `skip_image` to payload:
```ts
const data = await campaignsApi.create({
  client_id: activeClient.id,
  brain_dump: brainDump.trim(),
  target_keyword: campaignType === "blog_full" ? (targetKeyword.trim() || null) : null,
  secondary_keywords: campaignType === "blog_full" ? (supportingKeywords.trim() || null) : null,
  target_audience: targetAudience.trim() || null,
  campaign_type: campaignType,
  skip_image: campaignType === "social_only" ? true : !generateImage,
});
```

### 9. Frontend: `lib/api.ts`

`campaignsApi.create` call -- add `skip_image` to body (it is already typed via `CampaignCreate`).

---

## Files to Create / Update

| File | Action |
|------|--------|
| `backend/alembic/versions/YYYYMMDD_HHMM_<hash>_add_campaign_skip_image.py` | CREATE |
| `backend/app/db/repositories/models.py` | UPDATE -- add `skip_image` field to Campaign |
| `backend/app/schemas/campaign.py` | UPDATE -- add to CampaignCreate + CampaignResponse |
| `backend/app/db/repositories/campaigns.py` | UPDATE -- add `skip_image` param to `create_campaign` |
| `backend/app/routers/campaigns.py` | UPDATE -- enforce + pass skip_image in create; copy in regen |
| `backend/app/workers/generate.py` | UPDATE -- gate image call on skip_image |
| `frontend/lib/types.ts` | UPDATE -- Campaign + CampaignCreate types |
| `frontend/lib/api.ts` | UPDATE -- add `skip_image` to create payload |
| `frontend/app/(app)/campaigns/new/page.tsx` | UPDATE -- image checkbox + submit payload |
| `backend/tests/test_campaigns_router.py` | UPDATE -- skip_image create/regen tests |
| `backend/tests/workers/test_generate.py` (or test_generation_service.py) | UPDATE -- skip_image worker tests |

---

## Test Requirements

### Backend tests (add to `test_campaigns_router.py`)

1. `test_create_campaign_skip_image_true` -- POST with `skip_image: true`; campaign has `skip_image == true` in response
2. `test_create_campaign_skip_image_default_false` -- POST without `skip_image`; campaign has `skip_image == false`
3. `test_social_only_forces_skip_image` -- POST with `campaign_type: "social_only"`, `skip_image: false`; campaign has `skip_image == true` (backend override)
4. `test_regenerate_preserves_skip_image` -- reject a skip_image=true campaign and regenerate; new campaign has `skip_image == true`

### Backend tests (worker / generation service)

5. `test_worker_skips_image_when_flag_set` -- mock `run_generation_pipeline` completing (job in_progress); set campaign.skip_image=True; assert `image_service.run_image_generation` NOT called; assert job.status == "complete"
6. `test_worker_runs_image_when_flag_false` -- same setup with skip_image=False; assert `image_service.run_image_generation` IS called

---

## Dev Notes

- The `ImagePanel` component already handles `imageUrl = null` correctly -- it renders the "no image" state with both "Generate image" and "Upload image" buttons. No changes to `ImagePanel` are required.
- The `CampaignGenerationOverlay` STATUS_MESSAGES for `blog_full` include "Generating featured image..." as message index 3. When `skip_image=true`, the job completes at index 2 ("Checking voice fidelity..." is the last real step). The overlay will advance to "Done." automatically when it detects `job.status == "complete"` regardless of which message it is currently showing -- so no change is needed to the overlay for this story.
- The `effective_skip_image` enforcement in the router is a server-side safety check. The frontend already hides the checkbox for social-only mode, but the backend must not trust the client.
- Import `false` from `sqlalchemy` for the Boolean server_default: `from sqlalchemy import false`. Check if it's already imported; if not, add it.
- `get_campaign` is imported in the worker for this story. It was also needed in Story 3-20 for the campaign_type branch -- so it may already be imported from that story. If so, no duplicate import is needed.
- The session `db` inside `run_generation` (in `workers/generate.py`) is the same session used throughout the `async with AsyncSessionLocal() as db:` block. It is valid after `run_generation_pipeline` returns. Do NOT open a second session.
- Existing campaigns in the DB get `skip_image = false` via the migration's UPDATE + `server_default`. Their behavior is unchanged.

---

## Dev Agent Record

### Completion Notes

Implemented story 3.21 (Brain Dump Image Skip Toggle) across all layers:

- **Migration**: `20260801_0130_4a5b6c7d8e9f_add_campaign_skip_image.py` — adds `skip_image BOOLEAN NOT NULL DEFAULT false` to `campaigns` table, chains after `2e17c8e43612` (campaign_type migration).
- **Model**: Added `skip_image: bool` field to `Campaign` SQLModel using `Boolean` + `sa_false()` server_default.
- **Schema**: Added `skip_image: bool = False` to `CampaignCreate` (request input) and `CampaignResponse` (API output); `CampaignDetailResponse` inherits via `CampaignResponse`.
- **Repository**: Added `skip_image: bool = False` param to `create_campaign()`, sets it on the Campaign instance.
- **Router**: `create_new_campaign` enforces `effective_skip_image = True` when `campaign_type == "social_only"` (server-side safety). `regenerate_campaign` passes `skip_image=campaign.skip_image` to preserve the flag.
- **Worker**: After `run_generation_pipeline` completes, re-loads the campaign, checks `skip_image`. If True: marks job complete immediately (no image step). If False: calls `image_service.run_image_generation` as before.
- **Frontend types**: Added `skip_image: boolean` to `Campaign` and `skip_image?: boolean` to `CampaignCreate` in `lib/types.ts`.
- **Frontend page**: Added `generateImage` state (default `true`). Checkbox rendered only when `campaignType === "blog_full"`. Hint appears below when unchecked. Submit payload sends `skip_image: campaignType === "social_only" ? true : !generateImage`.
- **Tests**: 4 router tests (create with flag, default false, social_only override, regen preserves) + 2 worker tests (image skipped when flag set, image called when flag false). All 6 pass.
- Pre-existing 7 test failures in `test_campaigns_router.py` (subscription_service mock issue) and 3 in `BlogEditor.test.tsx` (function signature) were present before this story and not caused by 3-21 changes.
- Fixed `campaign_type`, `skip_image`, and `roadmap_id` missing from Campaign test fixtures in `ApprovalPanel.test.tsx` and `RetryPanel.test.tsx`.

---

## File List

- `backend/alembic/versions/20260801_0130_4a5b6c7d8e9f_add_campaign_skip_image.py` (CREATED)
- `backend/app/db/repositories/models.py` (UPDATED)
- `backend/app/schemas/campaign.py` (UPDATED)
- `backend/app/db/repositories/campaigns.py` (UPDATED)
- `backend/app/routers/campaigns.py` (UPDATED)
- `backend/app/workers/generate.py` (UPDATED)
- `frontend/lib/types.ts` (UPDATED)
- `frontend/app/(app)/campaigns/new/page.tsx` (UPDATED)
- `backend/tests/test_campaigns_router.py` (UPDATED)
- `backend/tests/test_generation_service.py` (UPDATED)
- `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx` (UPDATED)
- `frontend/__tests__/components/publishing/RetryPanel.test.tsx` (UPDATED)

---

## Change Log

- 2026-08-01: Implemented skip_image column + worker gate + checkbox UI (Story 3.21)
- 2026-08-01: Code review complete — 3 patches applied, 6 deferred, marked done

---

## Review Findings

- [x] [Review][Patch] `handleRetry` in CampaignGenerationOverlay drops `skip_image` on retry [frontend/components/campaigns/CampaignGenerationOverlay.tsx:101]
- [x] [Review][Patch] `generateImage` state not reset when user toggles campaign type back to blog_full [frontend/app/(app)/campaigns/new/page.tsx:49]
- [x] [Review][Patch] No warning log when client is None in `run_social_only_pipeline` [backend/app/services/generation.py]
- [x] [Review][Defer] `run_social_only_pipeline` commits job to `in_progress` before `campaign_id` check — pre-existing crash window from 3-20 [backend/app/services/generation.py] — deferred, pre-existing
- [x] [Review][Defer] `blogTitle` useMemo SSR issue if `blog_html` present during server render — pre-existing from 3-20 [frontend/app/(app)/campaigns/[id]/approval-panel.tsx] — deferred, pre-existing
- [x] [Review][Defer] `campaign_type` stored as `Text` with no DB-level enum constraint — unrecognized values silently fall through to blog_full [backend/app/db/repositories/models.py] — deferred, pre-existing pattern
- [x] [Review][Defer] `regenerate_campaign` copies `skip_image` verbatim without re-applying social_only override — theoretical since DB always has correct value [backend/app/routers/campaigns.py] — deferred, theoretical
- [x] [Review][Defer] `x_post` URL splitting in `blogTitle` truncation produces nonsensical title for URLs — cosmetic [frontend/app/(app)/campaigns/[id]/approval-panel.tsx] — deferred, cosmetic
- [x] [Review][Defer] `getCampaignTitle` always returns "X Post" for social_only with both posts — cosmetic/low impact [frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx] — deferred, cosmetic
