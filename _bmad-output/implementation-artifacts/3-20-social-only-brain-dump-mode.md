---
baseline_commit: 1a6c572
---

# Story 3.20: Social-Only Brain Dump Mode

Status: done

## Story

As a PersonnaPress user who wants to post directly to X or LinkedIn without writing a blog post,
I want to select "Social post only" on the brain dump page,
so that the system generates X and LinkedIn posts immediately -- no blog, no image, faster approval.

## Context & Motivation

Today every brain dump triggers the full pipeline: blog → voice fidelity → social posts → image
generation. This is the right default for content marketing, but it is wrong for users who want
to react quickly to a trending topic, share a quick take, or batch social content without a
corresponding article. They're forced to approve and ignore a blog post they didn't ask for.

The roadmap feature already has the concept of social-only campaigns (`skip_blog`, `generate_social_only`
in generation.py), but this is only accessible via the roadmap planner. Standalone brain dump
campaigns have no equivalent. This story surfaces that same capability as a first-class choice
at the point of content creation.

---

## Acceptance Criteria

### AC 1 -- Content type selector on brain dump page

**Given** a user is on `/campaigns/new`,
**When** the page loads,
**Then** a "Content type" fieldset appears between the page header and the brain dump textarea,
with two radio options:
- "Blog + Social" (default checked) -- "Blog post, X and LinkedIn posts, featured image"
- "Social post only" -- "X and LinkedIn posts only -- no blog or featured image"

### AC 2 -- Keyword fields hidden for social-only

**Given** the user selects "Social post only",
**When** the selection changes,
**Then** the Focus keyword and Supporting keywords fields collapse and are removed from the DOM
(or hidden via `grid-rows-[0fr]` collapse matching the existing tips toggle pattern).
Target audience field remains visible and functional.

### AC 3 -- Inline notice for social-only

**Given** the user selects "Social post only",
**When** the selection changes,
**Then** an `aria-live="polite"` inline note appears below the fieldset:
"Shorter generation time. You can publish directly to X and LinkedIn after approval."

### AC 4 -- `campaign_type` stored on Campaign model

**Given** a brain dump is submitted with type "social_only",
**When** the POST /campaigns request is received,
**Then** the Campaign row is created with `campaign_type = "social_only"`.
When submitted with "Blog + Social" (or no type), `campaign_type = "blog_full"`.

### AC 5 -- Social-only generation pipeline

**Given** a campaign with `campaign_type = "social_only"` has a pending generation job,
**When** the worker picks it up,
**Then**:
1. The worker calls `run_social_only_pipeline(job_id, db)` instead of the full pipeline.
2. `run_social_only_pipeline` marks the job `in_progress`, calls `_llm.generate_social_standalone(brain_dump, bvp, 0)`, writes BOTH `campaign.x_post` and `campaign.linkedin_post`, then marks job `status = "complete"` and sets `job.completed_at`.
3. No blog HTML, no voice fidelity check, no image generation is triggered.
4. If x_post or linkedin_post is empty after the LLM call, the job is marked `failed` with a descriptive error message.

### AC 6 -- Generation overlay shows social-only copy

**Given** the GenerationGate is polling a social-only campaign's job,
**When** the job is in any non-terminal state,
**Then** the `CampaignGenerationOverlay` shows social-only status messages:
- Pending: "Analyzing your voice profile..."
- In progress: "Generating your social posts..."
- Complete: "Done."
(The blog/image steps are absent from the cycle entirely.)

### AC 7 -- Approval panel: blog section hidden for social-only

**Given** a social-only campaign reaches `pending_approval` status,
**When** the user opens the approval gate `/campaigns/{id}`,
**Then**:
1. The blog editor section (`BlogEditor`) is not rendered.
2. The `ImagePanel` is not rendered.
3. The voice fidelity badge is not rendered.
4. The X post editor and LinkedIn post editor are shown at full width.

### AC 8 -- Approval panel: blog platforms excluded for social-only

**Given** a social-only campaign's approval panel loads platform connections,
**When** `availablePlatforms` is built from the connections response,
**Then** `wordpress`, `wordpress-com`, `webflow`, `github_pages`, and `headless` are excluded.
Only social platforms (x, linkedin, instagram, facebook_page, threads) remain.

### AC 9 -- Campaign list: social-only title fallback

**Given** a social-only campaign has no `blog_html`,
**When** the campaign list or any UI needs to display its title,
**Then** the title is derived from the first 60 characters of `x_post` (ellipsised if longer),
falling back to "Social post" if x_post is also absent.

### AC 10 -- Regeneration preserves campaign_type

**Given** a social-only campaign is rejected and the user clicks "Regenerate",
**When** POST /campaigns/{id}/regenerate is called,
**Then** the new Campaign row is created with `campaign_type = "social_only"` (copied from the
original), and the new job triggers `run_social_only_pipeline` not the full pipeline.

### AC 11 -- `campaign_type` exposed in API responses

**Given** the GET /campaigns or GET /campaigns/{id} endpoint returns a campaign,
**When** the campaign was created as social-only,
**Then** `campaign_type: "social_only"` is present in the JSON response.
For existing campaigns created before this migration, the field returns `"blog_full"`.

---

## Implementation Blueprint

### 1. Alembic migration

File: `backend/alembic/versions/YYYYMMDD_HHMM_<hash>_add_campaign_type.py`

```python
def upgrade():
    op.add_column(
        "campaigns",
        sa.Column("campaign_type", sa.Text(), nullable=True),
    )
    op.execute("UPDATE campaigns SET campaign_type = 'blog_full' WHERE campaign_type IS NULL")
    op.alter_column("campaigns", "campaign_type", nullable=False, server_default="blog_full")

def downgrade():
    op.drop_column("campaigns", "campaign_type")
```

### 2. Campaign model (`backend/app/db/repositories/models.py`)

Add to the `Campaign` SQLModel class:
```python
campaign_type: str = Field(
    default="blog_full",
    sa_column=Column(Text, nullable=False, server_default="blog_full"),
)
```

### 3. Campaign schema (`backend/app/schemas/campaign.py`)

`CampaignCreate` -- add:
```python
campaign_type: Literal["blog_full", "social_only"] = "blog_full"
```

`CampaignResponse` / `CampaignDetailResponse` -- add:
```python
campaign_type: str = "blog_full"
```

### 4. Campaign repository (`backend/app/db/repositories/campaigns.py`)

`create_campaign()` -- add param and pass to model:
```python
async def create_campaign(
    ...,
    campaign_type: str = "blog_full",
) -> Campaign:
    campaign = Campaign(
        ...,
        campaign_type=campaign_type,
    )
```

### 5. Campaigns router (`backend/app/routers/campaigns.py`)

`create_new_campaign` -- pass through:
```python
campaign = await create_campaign(
    db,
    body.client_id,
    body.brain_dump,
    target_keyword=body.target_keyword,
    target_audience=body.target_audience,
    secondary_keywords=body.secondary_keywords,
    campaign_type=body.campaign_type,
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
    campaign_type=campaign.campaign_type,  # preserve type
)
```

### 6. Generation service (`backend/app/services/generation.py`)

New function after `generate_social_only`:

```python
async def run_social_only_pipeline(job_id: uuid.UUID, db: AsyncSession) -> None:
    """Social-only generation pipeline for campaign_type='social_only' brain dump campaigns.

    Steps:
      1. Load job + campaign + client BVP; mark job in_progress.
      2. Call generate_social_standalone (0 thinking tokens) for both X + LinkedIn.
      3. Write x_post + linkedin_post to campaign; mark job complete.

    Job is marked complete immediately -- there is no image step.
    """
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        logger.error("run_social_only_pipeline: job %s not found", job_id)
        return

    job.status = "in_progress"
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(job)

    if not job.campaign_id:
        await _fail_job(db, job, "Generation job has no campaign_id")
        return

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == job.campaign_id))
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        await _fail_job(db, job, f"Campaign {job.campaign_id} not found")
        return

    client_result = await db.execute(select(Client).where(Client.id == campaign.client_id))
    client = client_result.scalar_one_or_none()
    brand_voice_profile: dict | None = client.brand_voice_profile if client else None

    try:
        social: dict = await _llm_with_retry(
            _llm.generate_social_standalone,
            campaign.brain_dump,
            brand_voice_profile,
            _SOCIAL_THINKING_TOKENS,
        )

        x_post = social.get("x_post")
        linkedin_post = social.get("linkedin_post")

        if not x_post:
            raise ValueError("run_social_only_pipeline: LLM returned empty x_post")
        if not linkedin_post:
            raise ValueError("run_social_only_pipeline: LLM returned empty linkedin_post")

        campaign.x_post = x_post
        campaign.linkedin_post = linkedin_post
        campaign.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        job.status = "complete"
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        logger.info("run_social_only_pipeline: campaign %s complete", campaign.id)

    except Exception as exc:
        logger.exception("run_social_only_pipeline: error for job %s: %s", job_id, exc)
        sentry_sdk.capture_exception(exc)
        await _fail_job(db, job, "Social post generation failed. Please retry.")
```

### 7. Worker (`backend/app/workers/generate.py`)

```python
from app.services import generation as generation_service

async def run_generation(job_id: uuid.UUID) -> None:
    try:
        async with AsyncSessionLocal() as db:
            job = await get_job(db, job_id)
            if not job or job.status != "pending":
                ...
                return

            # Load campaign to check type
            from app.db.repositories.campaigns import get_campaign
            campaign = await get_campaign(db, job.campaign_id) if job.campaign_id else None
            campaign_type = campaign.campaign_type if campaign else "blog_full"

            if campaign_type == "social_only":
                await generation_service.run_social_only_pipeline(job_id, db)
            else:
                # Full pipeline: text → image
                await generation_service.run_generation_pipeline(job_id, db)
                job = await get_job(db, job_id)
                if job and job.status == "in_progress" and job.campaign_id:
                    await image_service.run_image_generation(job.campaign_id, job_id, db)
    except Exception as exc:
        ...
```

### 8. Frontend: `lib/types.ts`

Add to `Campaign`:
```ts
campaign_type: "blog_full" | "social_only";
```

Add to `CampaignCreate`:
```ts
campaign_type?: "blog_full" | "social_only";
```

### 9. Frontend: `campaigns/new/page.tsx`

New state:
```ts
const [campaignType, setCampaignType] = useState<"blog_full" | "social_only">("blog_full");
```

**Content type fieldset** -- placed between `<header>` and the textarea `<div>`:

```tsx
<fieldset className="mb-6">
  <legend className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
    Content type
  </legend>
  <div className="flex flex-col border border-ink/10">
    <label
      className={cn(
        "flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors duration-100",
        "hover:bg-ink/[0.02]",
        campaignType === "blog_full" ? "bg-ink/[0.03]" : ""
      )}
    >
      <input
        type="radio"
        name="campaign_type"
        value="blog_full"
        checked={campaignType === "blog_full"}
        onChange={() => setCampaignType("blog_full")}
        className="mt-0.5 accent-ink"
        aria-describedby="ct-blog-desc"
      />
      <span className="flex flex-col gap-0.5">
        <span className="font-mono text-sm text-ink">Blog + Social</span>
        <span id="ct-blog-desc" className="font-mono text-xs text-graphite">
          Blog post, X and LinkedIn posts, featured image
        </span>
      </span>
    </label>
    <div className="border-t border-ink/10" />
    <label
      className={cn(
        "flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors duration-100",
        "hover:bg-ink/[0.02]",
        campaignType === "social_only" ? "bg-ink/[0.03]" : ""
      )}
    >
      <input
        type="radio"
        name="campaign_type"
        value="social_only"
        checked={campaignType === "social_only"}
        onChange={() => setCampaignType("social_only")}
        className="mt-0.5 accent-ink"
        aria-describedby="ct-social-desc"
      />
      <span className="flex flex-col gap-0.5">
        <span className="font-mono text-sm text-ink">Social post only</span>
        <span id="ct-social-desc" className="font-mono text-xs text-graphite">
          X and LinkedIn posts only -- no blog or featured image
        </span>
      </span>
    </label>
  </div>
  {campaignType === "social_only" && (
    <p
      role="status"
      aria-live="polite"
      className="mt-2 font-mono text-xs text-graphite border-l-2 border-ink/30 pl-3"
    >
      Shorter generation time. You can publish directly to X and LinkedIn after approval.
    </p>
  )}
</fieldset>
```

**Keyword fields collapse** -- wrap existing focus/supporting keyword fields:
```tsx
<div className={`grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none ${
  campaignType === "blog_full" ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
}`}>
  <div className="overflow-hidden">
    <div className="space-y-1 mb-2">{/* Focus keyword */}</div>
    <div className="space-y-1 mb-2">{/* Supporting keywords */}</div>
  </div>
</div>
```

**handleSubmit** -- add `campaign_type`:
```ts
const data = await campaignsApi.create({
  client_id: activeClient.id,
  brain_dump: brainDump.trim(),
  target_keyword: campaignType === "blog_full" ? (targetKeyword.trim() || null) : null,
  secondary_keywords: campaignType === "blog_full" ? (supportingKeywords.trim() || null) : null,
  target_audience: targetAudience.trim() || null,
  campaign_type: campaignType,
  // skip_image handled in Story 3-21
});
```

### 10. Frontend: `lib/api.ts`

`campaignsApi.create` call -- add `campaign_type` to body.

### 11. Frontend: `CampaignGenerationOverlay.tsx`

Add prop and branching message set:

```tsx
const BLOG_FULL_MESSAGES = [
  "Analyzing your voice profile...",
  "Drafting blog post...",
  "Checking voice fidelity...",
  "Generating featured image...",
  "Done.",
];

const SOCIAL_ONLY_MESSAGES = [
  "Analyzing your voice profile...",
  "Generating your social posts...",
  "Done.",
];

interface CampaignGenerationOverlayProps {
  campaignId: string;
  jobId: string;
  brainDump: string;
  clientId: string;
  campaignType?: "blog_full" | "social_only";  // new
}
```

Inside the component, derive `STATUS_MESSAGES` and `IN_PROGRESS_END_INDEX` from `campaignType`:
```tsx
const STATUS_MESSAGES = campaignType === "social_only" ? SOCIAL_ONLY_MESSAGES : BLOG_FULL_MESSAGES;
const IN_PROGRESS_END_INDEX = campaignType === "social_only" ? 1 : 3;
```

The `handleRetry` call must also pass `campaign_type` when recreating.

### 12. Frontend: `GenerationGate.tsx`

Pass `campaign.campaign_type` to the overlay:
```tsx
<CampaignGenerationOverlay
  campaignId={campaign.id}
  jobId={jobId}
  brainDump={campaign.brain_dump}
  clientId={campaign.client_id}
  campaignType={campaign.campaign_type}
/>
```

### 13. Frontend: `approval-panel.tsx`

**Blog section gate** -- wrap `BlogEditor` section:
```tsx
{campaign.campaign_type !== "social_only" && (
  // BlogEditor + voice badge
)}
```

**ImagePanel gate** -- wrap the image panel:
```tsx
{campaign.campaign_type !== "social_only" && (
  <ImagePanel ... />
)}
```

**Voice badge gate** -- already inside the blog section above, no separate change needed.

**Platform filter for social-only** -- in the `useEffect` that builds `availablePlatforms`, add:

```tsx
const BLOG_ONLY_PLATFORMS = new Set(["wordpress", "wordpress-com", "webflow", "github_pages", "headless"]);

const platforms = items
  .filter((c) => c.connected && c.platform !== "github_pages")
  .map((c) => c.platform)
  .filter((p) => campaign.campaign_type === "social_only" ? !BLOG_ONLY_PLATFORMS.has(p) : true);
setAvailablePlatforms(platforms);
```

The same filter must be applied in BOTH `useEffect` blocks (initial load + published state re-load, lines ~252 and ~298).

**Title derivation** -- update the title getter (line ~243):
```tsx
const campaignTitle = useMemo(() => {
  if (campaign.blog_html) {
    const tmp = document.createElement("div");
    tmp.innerHTML = campaign.blog_html;
    return tmp.querySelector("h1")?.textContent?.trim() || "Untitled";
  }
  if (campaign.x_post) {
    const first = campaign.x_post.trim().split(/[\n.!?]/)[0].trim();
    return first.length > 60 ? first.slice(0, 57) + "..." : first;
  }
  return "Social post";
}, [campaign.blog_html, campaign.x_post]);
```

---

## Files to Create / Update

| File | Action |
|------|--------|
| `backend/alembic/versions/YYYYMMDD_HHMM_<hash>_add_campaign_type.py` | CREATE |
| `backend/app/db/repositories/models.py` | UPDATE -- add `campaign_type` field to Campaign |
| `backend/app/schemas/campaign.py` | UPDATE -- add to CampaignCreate + CampaignResponse |
| `backend/app/db/repositories/campaigns.py` | UPDATE -- add `campaign_type` param to `create_campaign` |
| `backend/app/routers/campaigns.py` | UPDATE -- pass `campaign_type` in create + regen |
| `backend/app/services/generation.py` | UPDATE -- add `run_social_only_pipeline` |
| `backend/app/workers/generate.py` | UPDATE -- branch on `campaign_type` |
| `frontend/lib/types.ts` | UPDATE -- Campaign + CampaignCreate types |
| `frontend/lib/api.ts` | UPDATE -- add `campaign_type` to create payload |
| `frontend/app/(app)/campaigns/new/page.tsx` | UPDATE -- content type selector + field collapse + submit payload |
| `frontend/components/campaigns/CampaignGenerationOverlay.tsx` | UPDATE -- social-only message set + prop |
| `frontend/app/(app)/campaigns/[id]/GenerationGate.tsx` | UPDATE -- pass `campaignType` prop |
| `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` | UPDATE -- blog/image/voice gates + platform filter + title |
| `backend/tests/test_generation_service.py` | UPDATE -- add social-only pipeline tests |
| `backend/tests/test_campaigns_router.py` | UPDATE -- campaign_type create/regen tests |

---

## Test Requirements

### Backend tests (add to `test_generation_service.py`)

1. `test_run_social_only_pipeline_success` -- mock `_llm.generate_social_standalone` returning both posts; assert campaign.x_post set, campaign.linkedin_post set, job.status == "complete"
2. `test_run_social_only_pipeline_empty_x_post` -- LLM returns empty x_post; assert job.status == "failed"
3. `test_run_social_only_pipeline_empty_linkedin_post` -- LLM returns empty linkedin_post; assert job.status == "failed"
4. `test_run_social_only_pipeline_no_image_generated` -- assert `image_service.run_image_generation` is NOT called

### Backend tests (add to `test_campaigns_router.py`)

5. `test_create_campaign_social_only` -- POST with `campaign_type: "social_only"` returns 202; campaign has `campaign_type == "social_only"`
6. `test_create_campaign_default_blog_full` -- POST without `campaign_type` defaults to `"blog_full"`
7. `test_regenerate_preserves_campaign_type` -- reject then regenerate a social_only campaign; new campaign has `campaign_type == "social_only"`

---

## Dev Notes

- `generate_social_standalone` already returns both `x_post` and `linkedin_post` (see existing `generate_social_only` which reads both keys then writes only one). The new pipeline writes both.
- The worker loads the campaign BEFORE selecting the pipeline branch. Use `get_campaign` from `campaigns.py` (already imported in generate.py via the generation_service import chain... actually it is not -- add import directly in worker).
- The `IN_PROGRESS_END_INDEX` in `CampaignGenerationOverlay` must be adjusted per message set. For social-only: messages[0] = pending, messages[1] = in_progress (only one step), messages[2] = done. So `IN_PROGRESS_END_INDEX = 1` and `IN_PROGRESS_START_INDEX = 1`.
- The `handleRetry` in `CampaignGenerationOverlay` calls `campaignsApi.create({ client_id, brain_dump })` without `campaign_type`. This must be fixed to pass `campaignType` from the prop.
- Do NOT touch blog-related keywords (targetKeyword, secondaryKeywords) state for social-only -- just exclude them from the API payload. The state values can remain; they just aren't sent.
- The two `useEffect` blocks in `approval-panel.tsx` that build `availablePlatforms` (around line 252 and line 298) must BOTH have the platform filter applied -- they are for initial load and republish-state re-load respectively.
- `client_id` field type in `CampaignCreate` in `lib/types.ts` is already `string` (UUID as string). Add `campaign_type` as optional with default inferred on the backend.
- Existing campaigns in the DB get `campaign_type = 'blog_full'` via the migration's UPDATE statement and `server_default`.

---

## Tasks / Subtasks

- [x] Task 1: Alembic migration -- add `campaign_type` column
  - [x] 1.1 Generate migration with `alembic revision -m "add_campaign_type"`
  - [x] 1.2 Implement upgrade/downgrade logic with backfill
- [x] Task 2: Backend model, schema, repository
  - [x] 2.1 Add `campaign_type` field to `Campaign` SQLModel
  - [x] 2.2 Add `campaign_type` to `CampaignCreate` schema (Literal)
  - [x] 2.3 Add `campaign_type` to `CampaignResponse` schema
  - [x] 2.4 Add `campaign_type` param to `create_campaign()` repository
- [x] Task 3: Router pass-through
  - [x] 3.1 `create_new_campaign` passes `campaign_type` from body
  - [x] 3.2 `regenerate_campaign` copies `campaign_type` from source campaign
- [x] Task 4: Generation service -- `run_social_only_pipeline`
  - [x] 4.1 Implement `run_social_only_pipeline(job_id, db)` in `generation.py`
  - [x] 4.2 Worker branches on `campaign_type` to call the right pipeline
- [x] Task 5: Frontend types and API
  - [x] 5.1 Add `campaign_type` to `Campaign` and `CampaignCreate` in `lib/types.ts`
- [x] Task 6: Brain dump page UI
  - [x] 6.1 Add content type fieldset with two radio options
  - [x] 6.2 Collapse keyword fields for social-only with `grid-rows-[0fr]`
  - [x] 6.3 Add `aria-live="polite"` inline notice for social-only
  - [x] 6.4 Pass `campaign_type` in `handleSubmit`
- [x] Task 7: Generation overlay
  - [x] 7.1 Add `SOCIAL_ONLY_MESSAGES` and `BLOG_FULL_MESSAGES` arrays
  - [x] 7.2 Add `campaignType` prop; derive `STATUS_MESSAGES` and `IN_PROGRESS_END_INDEX`
  - [x] 7.3 Fix `handleRetry` to pass `campaign_type`
- [x] Task 8: Campaign detail page overlay signal
  - [x] 8.1 For social_only, use `x_post` instead of `blog_html` as content-ready signal
  - [x] 8.2 Pass `campaignType` prop to `CampaignGenerationOverlay` via `GenerationGate`
- [x] Task 9: Approval panel gating
  - [x] 9.1 Hide `BlogEditor`, `VoiceFidelityBadge` for social-only
  - [x] 9.2 Hide `ImagePanel` for social-only
  - [x] 9.3 Filter blog-only platforms from `availablePlatforms` in both useEffect blocks
  - [x] 9.4 Update title derivation (`blogTitle` useMemo) with x_post fallback
- [x] Task 10: Tests
  - [x] 10.1 `test_run_social_only_pipeline_success`
  - [x] 10.2 `test_run_social_only_pipeline_empty_x_post`
  - [x] 10.3 `test_run_social_only_pipeline_empty_linkedin_post`
  - [x] 10.4 `test_run_social_only_pipeline_no_image_generated`
  - [x] 10.5 `test_create_campaign_social_only`
  - [x] 10.6 `test_create_campaign_default_blog_full`
  - [x] 10.7 `test_regenerate_preserves_campaign_type`

### Review Findings

- [x] [Review][Patch] Hidden keyword inputs remain keyboard-focusable when collapsed [frontend/app/(app)/campaigns/new/page.tsx] — `tabIndex=-1` and `aria-hidden` added to `overflow-hidden` div and both inputs when `social_only` — **FIXED**
- [x] [Review][Patch] `CampaignResponse.campaign_type` is plain `str` instead of `Literal` [backend/app/schemas/campaign.py:66] — changed to `Literal["blog_full", "social_only"]` — **FIXED**
- [x] [Review][Patch] Redundant `github_pages` in `BLOG_ONLY_PLATFORMS` set [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:19] — removed; already filtered upstream by `platform !== "github_pages"` guard — **FIXED**
- [x] [Review][Defer] Double DB commit creates partial-write window in `run_social_only_pipeline` [backend/app/services/generation.py:290-296] — deferred, same pattern as existing `run_generation_pipeline`
- [x] [Review][Defer] Retry from overlay does not forward `target_keyword`/`secondary_keywords` [frontend/components/campaigns/CampaignGenerationOverlay.tsx] — deferred, pre-existing gap; overlay component has no access to keyword props
- [x] [Review][Defer] `blogTitle` useMemo calls `document.createElement` with SSR guard only inside `blog_html` branch [frontend/app/(app)/campaigns/[id]/approval-panel.tsx] — deferred, pre-existing bug from before this story
- [x] [Review][Defer] `_make_db_social_only` mock is order-dependent and fragile [backend/tests/test_generation_service.py] — deferred, test quality issue; not a correctness bug
- [x] [Review][Defer] No test for `campaign_id=None` early-exit path in `run_social_only_pipeline` [backend/tests/test_generation_service.py] — deferred, minor test coverage gap
- [x] [Review][Defer] Worker `get_campaign` returning None silently defaults to `blog_full` [backend/app/workers/generate.py:34] — deferred, theoretical only; `campaign_id` is set by router before the worker fires

---

## File List

| File | Action |
|------|--------|
| `backend/alembic/versions/20260801_0046_2e17c8e43612_add_campaign_type.py` | CREATED |
| `backend/app/db/repositories/models.py` | UPDATED |
| `backend/app/schemas/campaign.py` | UPDATED |
| `backend/app/db/repositories/campaigns.py` | UPDATED |
| `backend/app/routers/campaigns.py` | UPDATED |
| `backend/app/services/generation.py` | UPDATED |
| `backend/app/workers/generate.py` | UPDATED |
| `frontend/lib/types.ts` | UPDATED |
| `frontend/app/(app)/campaigns/new/page.tsx` | UPDATED |
| `frontend/components/campaigns/CampaignGenerationOverlay.tsx` | UPDATED |
| `frontend/app/(app)/campaigns/[id]/GenerationGate.tsx` | UPDATED |
| `frontend/app/(app)/campaigns/[id]/page.tsx` | UPDATED |
| `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` | UPDATED |
| `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` | UPDATED |
| `backend/tests/test_generation_service.py` | UPDATED |
| `backend/tests/test_campaigns_router.py` | UPDATED |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-08-01 | Full implementation of story 3-20: social-only brain dump mode. All 11 ACs implemented. 7 new backend tests added and passing. | Dev Agent |

---

## Dev Agent Record

### Implementation Plan

Implemented `campaign_type` field (`"blog_full"` | `"social_only"`) across the full stack:
1. Alembic migration with backfill of existing rows to `"blog_full"`
2. SQLModel field + Pydantic schema (CampaignCreate + CampaignResponse)
3. Repository `create_campaign()` + router pass-through for create and regenerate
4. New `run_social_only_pipeline` in generation.py; worker branching
5. Frontend: types, brain dump page radio fieldset with collapse animation, overlay message branching, approval panel gating (blog/image/voice/platform filter/title fallback)

### Completion Notes

- All 11 ACs implemented and verified
- 7 pre-existing test failures in `test_campaigns_router.py` confirmed pre-existing (missing `check_trial_not_expired` mock) -- not regressions from this story
- 4 new generation service tests + 3 new campaign router tests all pass
- New campaign router tests mock `check_trial_not_expired` so they pass cleanly
