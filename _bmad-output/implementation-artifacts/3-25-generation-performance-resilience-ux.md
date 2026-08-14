---
baseline_commit: 2a9157e
---

# Story 3.25: Generation Performance, Resilience & UX

Status: done

---

## Story

As a PersonnaPress user who just submitted a brain dump,
I want to see my new campaign immediately in the campaign list with a "Generating" indicator,
so that I know generation is in progress without being confused by a misleading "Pending Approval" badge.

As a PersonnaPress user whose image failed to generate,
I want to see a small "No image" chip on the campaign card,
so that I understand why the campaign has no image without thinking the campaign itself failed.

As a PersonnaPress operator,
I want the generation pipeline to complete faster and cancel hung Replicate predictions,
so that users wait less and Replicate credits are not wasted on predictions we have already abandoned.

---

## Context and Motivation

Four independent problems are fixed in this story. They are batched because they all touch the same generation pipeline and campaign list surface, and fixing them separately would cause churn on the same files.

### Problem 1: Campaign not appearing in list after creation

`useCampaigns.ts` has `staleTime: 30_000`. The brain dump submit handler navigates to `/campaigns/{id}` without calling `queryClient.invalidateQueries`. If the user navigates to `/campaigns` within 30 seconds of creation, TanStack Query serves stale cache that predates the new campaign — the campaign is invisible. After 30 seconds it re-fetches and the campaign appears. This is a pure frontend cache gap; the backend creates the campaign with `status="pending_approval"` immediately before the worker starts, and the list endpoint has no status filter.

`CampaignGenerationOverlay.tsx` also only invalidates `["campaign", campaignId]` on job complete, not `["campaigns"]`.

### Problem 2: Misleading "Pending Approval" badge during generation

`CampaignStatus` is a constrained SA Enum. Adding a `"generating"` value would require `ALTER TYPE campaign_status_enum ADD VALUE 'generating'` — a migration with lock risk. The cleaner solution is to join the latest generation job to the campaign list response and surface `generation_job_status: Optional[str]`. The frontend then renders a spinner badge when the job is active, without touching the campaign status column.

### Problem 3: Image failure invisible to the user

When Replicate fails after 3 retries, `run_image_generation` sets `job.error_details = "Image generation failed: blog and social posts are complete."` and sets `job.status = "complete"`. The campaign's `image_url` stays `null`. The user sees a campaign without an image and gets no explanation. The same `generation_job_status` JOIN (from Problem 2) gives the frontend everything it needs: `job.status == "complete"` + `image_url == null` + `skip_image == false` → show "No image" chip.

### Problem 4: Generation pipeline is slower than it needs to be

The text generation pipeline runs three LLM calls fully sequentially: blog → fidelity check → social posts. Fidelity check and social post generation are independent of each other — only the blog must finish first (social needs the H1 title, fidelity needs the blog HTML). Running them with `asyncio.gather` saves 5-15 seconds of wall-clock time with zero risk: both calls are read-only (no DB operations happen inside), so sharing the same session during the gather is safe.

### Problem 5: Replicate retry backoff is deterministic and predictions are never cancelled

All concurrent campaigns retry at exactly `t+8s`, `t+24s` — a thundering herd. Adding `±20%` jitter staggers retries across concurrent requests.

More importantly: when `asyncio.wait_for` raises `TimeoutError` after 120 seconds, the Replicate prediction keeps running on their infrastructure indefinitely. We pay for it and get nothing. Switching `generate_image` from the high-level `_client.async_run()` (which hides the prediction ID) to `_client.predictions.create()` gives us the prediction ID upfront, so we can call `predictions.cancel(prediction.id)` on timeout.

### What is NOT in scope

- Replicate webhook migration (deferred — webhook infrastructure adds complexity disproportionate to the improvement at current scale)
- A `"generating"` Campaign DB status value or migration
- Changes to the social_only pipeline (no LLM parallelism opportunity there — both X and LinkedIn are generated in one call)
- Changes to manual image regeneration (`/campaigns/{id}/image/regenerate`) — it is a synchronous user-triggered action with its own spinner; it already uses `asyncio.wait_for` via `_generate_with_retry`

---

## Acceptance Criteria

### AC 1: Campaign appears in the list immediately after creation

**Given** the user submits the brain dump form,
**When** the API responds with `campaign_id` and `job_id`,
**Then** `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` is called before the router pushes to `/campaigns/{id}`,
**And** the campaign list re-fetches on the user's next visit regardless of stale time.

---

### AC 2: Campaign list re-fetches when generation overlay completes

**Given** `CampaignGenerationOverlay` detects `job.status === "complete"` or `"completed"`,
**When** it invalidates the single-campaign query,
**Then** it also invalidates `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` in the same effect.

---

### AC 3: Campaign list endpoint returns generation_job_status

**Given** a GET `/campaigns` request,
**When** the list is built,
**Then** each `CampaignResponse` item includes `generation_job_status: Optional[str]` populated from the latest `job_type="generation"` job for that campaign (one extra batch query after the main campaigns query; no JOIN needed on the main query).

**And** `generation_job_status` is `null` for campaigns that have no generation job (edge case: manually seeded rows).

**And** `CampaignResponse` in `schemas/campaign.py` has a new optional field: `generation_job_status: Optional[str] = None`.

---

### AC 4: "Generating" badge replaces StatusBadge during active generation

**Given** a campaign row in `CampaignList.tsx` where `campaign.generation_job_status` is `"pending"` or `"in_progress"`,
**When** the row renders,
**Then** `<StatusBadge status={campaign.status} />` is NOT rendered,
**And** this element renders instead:

```tsx
<span
  role="status"
  aria-label="Campaign is being generated"
  className="inline-flex items-center gap-1.5 border border-ink/25 px-2 py-0.5 font-mono text-xs text-graphite"
>
  <Loader2 className="size-3 animate-spin" aria-hidden="true" />
  Generating
</span>
```

`Loader2` must be imported from `lucide-react`. No Framer Motion.

**Given** the generation job has reached any terminal status (`"complete"`, `"failed"`),
**When** the row renders,
**Then** `<StatusBadge status={campaign.status} />` renders normally.

---

### AC 5: "No image" chip shown when image generation failed

**Given** a campaign row where `campaign.generation_job_status === "complete"` AND `campaign.image_url` is `null` AND `campaign.skip_image === false`,
**When** the row renders,
**Then** this element is shown alongside the `StatusBadge` (not instead of it):

```tsx
<span
  aria-label="Featured image could not be generated"
  title="Featured image could not be generated"
  className="inline-flex items-center gap-1 border border-[#E5E5E5] px-1.5 py-0.5 font-mono text-[10px] text-graphite/60"
>
  <ImageOff className="size-3" aria-hidden="true" />
  No image
</span>
```

`ImageOff` must be imported from `lucide-react`.

**Given** `campaign.skip_image === true` OR `campaign.image_url` is not null,
**When** the row renders,
**Then** the "No image" chip does NOT appear.

---

### AC 6: Fidelity check and social post generation run in parallel

**Given** `run_generation_pipeline` has completed blog generation,
**When** it proceeds to steps 3 and 4,
**Then** `check_fidelity` and `generate_social` are awaited via `asyncio.gather` rather than sequentially.

The blog H1 title extraction (the `re.search` for `<h1>`) must happen BEFORE the `asyncio.gather` call, because `generate_social` needs `blog_title` as input.

```python
# Extract blog title needed by both social and image step
h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", blog_html, re.IGNORECASE | re.DOTALL)
blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"

# Steps 3+4 in parallel — both are LLM-only, no DB writes inside
voice_score, social = await asyncio.gather(
    _llm_with_retry(
        _llm.check_fidelity,
        blog_html,
        brand_voice_profile,
        _FIDELITY_THINKING_TOKENS,
        campaign.brain_dump,
    ),
    _llm_with_retry(
        _llm.generate_social,
        campaign.brain_dump,
        blog_title,
        brand_voice_profile,
        _SOCIAL_THINKING_TOKENS,
    ),
)
campaign.voice_score = voice_score
campaign.x_post = social["x_post"]
campaign.linkedin_post = social["linkedin_post"]
```

The single atomic DB write (Step 5 commit) is unchanged — it still runs after the gather completes.

**And** the `_ESTIMATED_TOTAL_TOKENS` constant is unchanged (same tokens used, just less wall-clock time).

---

### AC 7: Replicate retry backoff uses ±20% jitter

**Given** `_generate_with_retry` in `image.py` retries after a timeout or provider error,
**When** it sleeps before the next attempt,
**Then** the sleep duration is `8 * (2 ** attempt) * random.uniform(0.8, 1.2)` (import `random` at the top of `image.py`).

The first retry sleeps `~8s ± 20%` (range 6.4s–9.6s). The second sleeps `~16s ± 20%` (range 12.8s–19.2s).

---

### AC 8: Hung Replicate prediction is cancelled on timeout

**Given** `generate_image` in `replicate.py` starts a prediction,
**When** the prediction takes longer than 120 seconds,
**Then** the prediction is cancelled on Replicate's side (DELETE /predictions/{id}) before raising `asyncio.TimeoutError`.

**Implementation approach** — switch from `_client.async_run()` to the lower-level prediction API:

```python
import asyncio

async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str:
    # Build input_payload as before (FLUX vs non-FLUX branches unchanged)

    # Use predictions.create to get the prediction ID upfront
    # asyncio.to_thread is used because predictions.create is synchronous
    prediction = await asyncio.to_thread(
        _client.predictions.create,
        model=_MODEL,
        input=input_payload,
    )
    logger.info(
        "replicate.generate_image: prediction %s started (model=%s)", prediction.id, _MODEL
    )

    try:
        # prediction.wait() is a sync blocking poll; run in a thread with timeout
        completed = await asyncio.wait_for(
            asyncio.to_thread(prediction.wait),
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        # Cancel on Replicate's side so we don't keep paying for a hung prediction
        try:
            await asyncio.to_thread(_client.predictions.cancel, prediction.id)
            logger.info(
                "replicate.generate_image: cancelled hung prediction %s", prediction.id
            )
        except Exception as cancel_exc:
            logger.warning(
                "replicate.generate_image: could not cancel prediction %s: %s",
                prediction.id,
                cancel_exc,
            )
        raise  # re-raise TimeoutError for _generate_with_retry to handle

    if completed.status == "failed":
        raise ValueError(f"Replicate prediction {completed.id} failed: {completed.error}")
    if completed.status == "canceled":
        raise ValueError(f"Replicate prediction {completed.id} was canceled externally")

    output = completed.output
    if isinstance(output, (list, tuple)) and not output:
        raise ValueError("Replicate returned empty output list")
    image_url = str(output[0] if isinstance(output, (list, tuple)) else output)
    logger.info("replicate.generate_image: received URL %s", image_url[:60])
    return image_url
```

**SDK note**: `replicate==1.0.7` is installed. `_client.predictions.create()` is synchronous and returns a `Prediction` object with `.id` and `.wait()`. Check the SDK source at `site-packages/replicate/prediction.py` to confirm the exact `wait()` signature and any keyword args. If `prediction.wait()` is not available or has a different name in 1.0.7, use a manual polling loop via `_client.predictions.get(prediction.id)` in a `while` loop with `asyncio.sleep(1)`, wrapped in `asyncio.wait_for`. The key invariant is: prediction ID must be captured before the timeout window starts, and `predictions.cancel(id)` must be called on `TimeoutError`.

---

### AC 9: Existing behavior fully preserved

**Given** any existing blog_full or social_only campaign flow,
**When** these changes are deployed,
**Then** all existing AC for image generation, social post generation, fidelity checks, campaign approval, and publishing are unchanged.

**And** the `run_social_only_pipeline` is NOT modified (no parallelism opportunity; single LLM call for both platforms).

**And** the manual image regeneration endpoint (`POST /campaigns/{id}/image/regenerate`) is NOT modified.

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/services/generation.py` | Parallelize fidelity + social via `asyncio.gather` in `run_generation_pipeline`; move H1 extraction before gather |
| `backend/app/services/image.py` | Add jitter to `_generate_with_retry` backoff sleep; `import random` at top |
| `backend/app/integrations/replicate.py` | Switch `async_run` → `predictions.create` + `prediction.wait` + `predictions.cancel` on timeout; `import asyncio` at top |
| `backend/app/routers/campaigns.py` | Add batch job query after campaigns fetch; populate `generation_job_status` on each item |
| `backend/app/schemas/campaign.py` | Add `generation_job_status: Optional[str] = None` to `CampaignResponse` |
| `frontend/app/(app)/campaigns/new/page.tsx` | Add `useQueryClient` import; call `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` in `handleSubmit` after `router.push` |
| `frontend/components/campaigns/CampaignGenerationOverlay.tsx` | In the `job.status === "complete"` effect, also invalidate `["campaigns"]` |
| `frontend/components/campaigns/CampaignList.tsx` | Add Generating badge (replaces StatusBadge when job active); add No image chip; import `Loader2`, `ImageOff` from lucide-react |

---

## Dev Notes

### 1. `routers/campaigns.py` — batch job query (AC 3)

After `campaigns = result.scalars().all()` and the client name batch query, add a second batch query for generation jobs. Do NOT join on the main query — `Campaign` already has no SQLModel relationship to `Job`, and adding an outerjoin to the paginated query complicates the count subquery.

```python
# Batch-fetch latest generation job status per campaign (no JOIN on main query)
campaign_ids = [c.id for c in campaigns]
gen_job_map: dict[uuid.UUID, str] = {}
if campaign_ids:
    gen_job_rows = await db.execute(
        select(Job.campaign_id, Job.status)
        .where(
            Job.campaign_id.in_(campaign_ids),
            Job.job_type == "generation",
        )
        .order_by(Job.campaign_id, Job.created_at.desc())
    )
    seen: set[uuid.UUID] = set()
    for row in gen_job_rows.all():
        if row.campaign_id not in seen:
            gen_job_map[row.campaign_id] = row.status
            seen.add(row.campaign_id)
```

Then in the `CampaignListResponse` builder:

```python
return CampaignListResponse(
    items=[
        CampaignResponse.model_validate({
            **c.__dict__,
            "client_name": client_name_map.get(c.client_id),
            "generation_job_status": gen_job_map.get(c.id),
        })
        for c in campaigns
    ],
    total=total,
)
```

`Job` is already imported at the top of `routers/campaigns.py` as part of `app.db.repositories.jobs`. Add `from app.db.repositories.models import ..., Job` if not already present (check existing imports — `Job` may already be imported via `create_job`/`get_publish_job_for_campaign`).

---

### 2. `campaigns/new/page.tsx` — cache invalidation (AC 1)

`useQueryClient` is not currently imported. Add it:

```tsx
import { useQuery, useQueryClient } from "@tanstack/react-query";
```

Then inside `NewCampaignPage`, initialise it:

```tsx
const queryClient = useQueryClient();
```

In `handleSubmit`, immediately after `router.push(...)`:

```tsx
router.push(`/campaigns/${data.campaign_id}?job_id=${data.job_id}`);
queryClient.invalidateQueries({ queryKey: ["campaigns"] });
```

`router.push` is non-blocking (it schedules navigation); calling `invalidateQueries` right after is safe and will cause the list to re-fetch when the user navigates there.

---

### 3. `CampaignGenerationOverlay.tsx` — list invalidation on completion (AC 2)

The existing effect at line ~79:

```tsx
useEffect(() => {
  if (job?.status === "complete" || job?.status === "completed") {
    queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
    const timer = setTimeout(() => {
      router.replace(`/campaigns/${campaignId}`);
    }, 1500);
    return () => clearTimeout(timer);
  }
}, [job?.status, campaignId, queryClient, router]);
```

Add the list invalidation alongside the existing single-campaign invalidation:

```tsx
queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
queryClient.invalidateQueries({ queryKey: ["campaigns"] });
```

---

### 4. `CampaignList.tsx` — new indicators (AC 4, AC 5)

Add imports at the top alongside the existing lucide imports:

```tsx
import { ArrowRight, ChevronLeft, ChevronRight, ImageOff, Loader2, Map as MapIcon } from "lucide-react";
```

The `Campaign` type in `frontend/lib/types.ts` needs the new field — add `generation_job_status?: string | null` to the `Campaign` interface. Check `lib/types.ts` for the existing `Campaign` type definition and add it there.

In the campaign row render, replace the `<StatusBadge status={campaign.status} />` line:

```tsx
{/* Status badge — replaced by spinner during active generation */}
{(campaign.generation_job_status === "pending" || campaign.generation_job_status === "in_progress") ? (
  <span
    role="status"
    aria-label="Campaign is being generated"
    className="inline-flex items-center gap-1.5 border border-ink/25 px-2 py-0.5 font-mono text-xs text-graphite"
  >
    <Loader2 className="size-3 animate-spin" aria-hidden="true" />
    Generating
  </span>
) : (
  <StatusBadge status={campaign.status} />
)}

{/* No image chip — only when job is done but image is missing (not a skip) */}
{campaign.generation_job_status === "complete"
  && !campaign.image_url
  && !campaign.skip_image && (
  <span
    aria-label="Featured image could not be generated"
    title="Featured image could not be generated"
    className="inline-flex items-center gap-1 border border-[#E5E5E5] px-1.5 py-0.5 font-mono text-[10px] text-graphite/60"
  >
    <ImageOff className="size-3" aria-hidden="true" />
    No image
  </span>
)}
```

Place the "No image" chip immediately after the StatusBadge/Generating conditional, before the Roadmap badge. The row already uses `flex flex-wrap items-center gap-2` so both chips will flow naturally.

---

### 5. `generation.py` — parallelise steps 3+4 (AC 6)

The current steps 3 and 4 start at approximately line 171. Replace the sequential block:

```python
# BEFORE (sequential):
h1_match = re.search(...)
blog_title = ...
voice_score = await _llm_with_retry(_llm.check_fidelity, ...)
campaign.voice_score = voice_score
social = await _llm_with_retry(_llm.generate_social, ...)
campaign.x_post = social["x_post"]
campaign.linkedin_post = social["linkedin_post"]
```

With the parallel version:

```python
# AFTER (parallel):
# ── Steps 3+4: Voice fidelity + social posts (parallel after blog) ────
h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", blog_html, re.IGNORECASE | re.DOTALL)
blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"

voice_score, social = await asyncio.gather(
    _llm_with_retry(
        _llm.check_fidelity,
        blog_html,
        brand_voice_profile,
        _FIDELITY_THINKING_TOKENS,
        campaign.brain_dump,
    ),
    _llm_with_retry(
        _llm.generate_social,
        campaign.brain_dump,
        blog_title,
        brand_voice_profile,
        _SOCIAL_THINKING_TOKENS,
    ),
)
campaign.voice_score = voice_score
campaign.x_post = social["x_post"]
campaign.linkedin_post = social["linkedin_post"]
```

`asyncio` is already imported at the top of `generation.py`. No new imports needed.

The downstream Step 5 (`await db.commit()`) is unchanged. The blog_title extraction previously lived inside Step 3 in the code block — it moves to be the preamble before the gather, which is structurally identical.

**If `asyncio.gather` raises**: it propagates the first exception to the outer `except Exception as exc` block, which calls `_fail_job`. This is correct — if fidelity OR social fails, the job fails.

---

### 6. `image.py` — jitter (AC 7)

Add `import random` to the top of `image.py` (alongside existing `import asyncio`).

In `_generate_with_retry`, change:

```python
# BEFORE:
await asyncio.sleep(8 * (2 ** attempt))  # 8s, 16s

# AFTER:
await asyncio.sleep(8 * (2 ** attempt) * random.uniform(0.8, 1.2))
```

---

### 7. `replicate.py` — cancel on timeout (AC 8)

Add `import asyncio` to the top of `replicate.py` (it currently only imports `logging`, `typing.Any`, `replicate`, and `app.core.config`).

Replace the `generate_image` function body as described in AC 8.

**Verifying the SDK API before coding**: Open `backend/.venv/Lib/site-packages/replicate/prediction.py` (or equivalent venv path) and confirm:
- `Client.predictions.create(model, input, ...)` exists and returns a `Prediction`
- `Prediction.id` is the string prediction ID
- `Prediction.wait()` is a sync blocking method that polls until terminal state (or equivalent)
- `Client.predictions.cancel(prediction_id)` is the sync cancel call

If `prediction.wait()` is not available in 1.0.7, implement a manual polling loop:

```python
# Manual poll fallback if prediction.wait() is absent
async def _poll_prediction(prediction) -> Any:
    while True:
        refreshed = await asyncio.to_thread(_client.predictions.get, prediction.id)
        if refreshed.status in ("succeeded", "failed", "canceled"):
            return refreshed
        await asyncio.sleep(1.0)

completed = await asyncio.wait_for(_poll_prediction(prediction), timeout=120.0)
```

---

## Tests to Update / Add

| Test file | Change |
|---|---|
| `backend/tests/test_generation_service.py` | Add test that fidelity and social are called concurrently (mock `asyncio.gather` or assert both mocks called without ordering dependency); existing sequential tests may need updating if they assert call order |
| `backend/tests/test_image_service.py` | Update `_generate_with_retry` tests to assert jitter range (mock `random.uniform`); add test that `predictions.cancel` is called when `prediction.wait` raises `TimeoutError` |
| `backend/tests/test_replicate.py` (if it exists) | Update to mock `_client.predictions.create` and `prediction.wait` instead of `_client.async_run` |
| `frontend/__tests__/components/campaigns/CampaignList.test.tsx` | Add test: `generation_job_status="in_progress"` renders Generating badge not StatusBadge; `generation_job_status="complete"` + no `image_url` + `skip_image=false` renders No image chip |
| `frontend/__tests__/app/campaigns/new/page.test.tsx` (if exists) | Assert `invalidateQueries` called with `["campaigns"]` after successful submit |

---

## Dev Agent Record

### Implementation Plan

Implemented all 9 ACs in a single pass across 8 source files:

1. **AC 3 (schema)**: Added `generation_job_status: Optional[str] = None` to `CampaignResponse` in `schemas/campaign.py`.
2. **AC 3 (router)**: Added `Job` import and a batch query in `routers/campaigns.py` list endpoint. After the client name batch query, a second batch fetches the latest `"generation"` job status per campaign using `order_by + seen set` dedup. Populated `generation_job_status` in each `CampaignResponse`.
3. **AC 6 (parallelism)**: In `services/generation.py`, extracted H1 title before the gather, then awaited `check_fidelity` and `generate_social` via `asyncio.gather`. Single atomic DB commit unchanged.
4. **AC 7 (jitter)**: Added `import random` to `services/image.py` and updated the retry sleep to `8 * (2 ** attempt) * random.uniform(0.8, 1.2)`.
5. **AC 8 (cancel-on-timeout)**: Rewrote `integrations/replicate.py` to use `predictions.async_create` (async, SDK 1.0.7) instead of `async_run`. Wraps `prediction.async_wait()` in `asyncio.wait_for(timeout=120.0)`. On `TimeoutError`, calls `prediction.async_cancel()` before re-raising.
6. **AC 1 (cache invalidation)**: Added `useQueryClient` import and `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` after `router.push` in `campaigns/new/page.tsx`.
7. **AC 2 (overlay invalidation)**: Added `queryClient.invalidateQueries({ queryKey: ["campaigns"] })` alongside the existing single-campaign invalidation in `CampaignGenerationOverlay.tsx`.
8. **AC 4+5 (badges)**: In `CampaignList.tsx`, updated imports to include `ImageOff` and `Loader2`; replaced `<StatusBadge>` with conditional Generating badge when `generation_job_status` is `"pending"` or `"in_progress"`; added No image chip when job complete + `image_url` null + `skip_image` false.
9. **types.ts**: Added `generation_job_status?: string | null` to the `Campaign` interface.

### Completion Notes

All 9 ACs satisfied. Key decisions:
- Used `prediction.async_wait()` (SDK native async method) rather than `asyncio.to_thread(prediction.wait)` as the story spec's fallback path - cleaner and avoids thread overhead.
- Replicate cancel uses `prediction.async_cancel()` (SDK method that calls the Namespace cancel internally) rather than `_client.predictions.async_cancel(prediction.id)` directly - both work, the former is the idiomatic 1.0.7 approach.
- Pre-existing test failures (pagination text mismatch, `test_create_campaign_returns_202`) confirmed pre-existing before any changes were made. Fixed the pagination text mismatch (component renders "Previous"/"Next" not "← Previous"/"Next →").

Test results:
- Backend: 52 new/updated tests pass (test_generation_service: 22, test_image: 18, test_replicate: 5 + 2 parametrized)
- Frontend: 12 CampaignList tests pass (6 new, 6 existing + 1 pre-existing bug fixed)


## File List

- `backend/app/schemas/campaign.py` — Added `generation_job_status: Optional[str] = None` to `CampaignResponse`
- `backend/app/routers/campaigns.py` — Added `Job` import; batch job query; `generation_job_status` populated in list response
- `backend/app/services/generation.py` — `asyncio.gather` for fidelity+social; H1 extraction moved before gather
- `backend/app/services/image.py` — Added `import random`; jitter on retry backoff sleep
- `backend/app/integrations/replicate.py` — Switched to `predictions.async_create` + `prediction.async_wait()` + `prediction.async_cancel()` on timeout; added `import asyncio`
- `frontend/lib/types.ts` — Added `generation_job_status?: string | null` to `Campaign` interface
- `frontend/app/(app)/campaigns/new/page.tsx` — Added `useQueryClient`; `queryClient.invalidateQueries(["campaigns"])` after submit
- `frontend/components/campaigns/CampaignGenerationOverlay.tsx` — Added `queryClient.invalidateQueries(["campaigns"])` on job complete
- `frontend/components/campaigns/CampaignList.tsx` — Added `ImageOff`, `Loader2` imports; Generating badge; No image chip
- `backend/tests/test_generation_service.py` — Added 2 tests for asyncio.gather parallelism
- `backend/tests/services/test_image.py` — Added 2 tests for jitter range via mocked `random.uniform`
- `backend/tests/integrations/test_replicate.py` — Rewrote to use `async_create`; added 3 new tests (cancel-on-timeout, cancel-failure-passthrough, failed-prediction)
- `frontend/__tests__/components/campaigns/CampaignList.test.tsx` — Added 6 new tests; fixed pre-existing pagination text mismatch

### Review Findings

- [x] [Review][Patch] None output guard missing — `prediction.output` can be `None` on succeeded prediction; `str(None)` = "None" stored as URL [replicate.py:84] — fixed: added `if output is None: raise ValueError(...)` + test
- [x] [Review][Patch] async_cancel has no timeout — hung cancel blocks indefinitely on network drop [replicate.py:67] — fixed: wrapped in `asyncio.wait_for(..., timeout=10.0)`
- [x] [Review][Patch] Secondary sort key missing in gen_job_rows query — non-deterministic ordering when two jobs share identical created_at [campaigns.py:206] — fixed: added `Job.id.desc()`
- [x] [Review][Patch] `generation_job_status` typed as optional in types.ts — API always returns the field; `?` allows undefined [types.ts:185] — fixed: changed to `string | null`
- [x] [Review][Defer] LLM concurrency risk with asyncio.gather — speculative; depends on provider limits; spec requires this change — deferred
- [x] [Review][Defer] Outer asyncio.wait_for in image.py has no cancel path — pre-existing code, not introduced by this diff — deferred
- [x] [Review][Defer] Python-side dedup vs DB DISTINCT ON — performance concern at scale; functionally correct — deferred
- [x] [Review][Defer] social["x_post"] KeyError risk — pre-existing key access pattern, not introduced by this diff — deferred

## Change Log

- 2026-08-14: Story 3.25 code review complete — 4 patches applied (None output guard + cancel timeout in replicate.py, Job.id.desc() secondary sort in campaigns.py, generation_job_status non-optional in types.ts), 4 deferred, marked done
- 2026-08-14: Story 3.25 implemented — campaign list cache invalidation on create and overlay complete; `generation_job_status` JOIN via batch query; Generating badge and No image chip in CampaignList; fidelity+social parallelized via asyncio.gather; retry backoff jitter; Replicate cancel-on-timeout via predictions.async_create/async_wait/async_cancel
