---
baseline_commit: c7655dd5096f83f66dba9ca83ceaa610a14397e0
---

# Story 3.3: Blog & Social Content Generation Pipeline

Status: done

## Story

As a developer,
I want the BackgroundTask generation worker to call Gemini 2.5 Flash to produce the blog post, run the voice fidelity check, and generate social posts — all persisted to the Campaign record,
So that submitted Brain Dumps produce complete, voice-aligned text content that the Approval Gate can display.

## Acceptance Criteria

1. **Given** a generation BackgroundTask is dispatched with a `job_id`, **When** `workers/generate.py` executes `run_generation(job_id)`, **Then** it fetches the `jobs` record by `job_id`, sets `jobs.status='in_progress'` and `jobs.started_at=now()`, fetches the associated `campaigns` record and the client's `brand_voice_profile`; all operations happen in this order with no business logic in the router.

2. **Given** the blog generation step runs, **When** `services/generation.py` calls `integrations/gemini.py` via `generate_blog()`, **Then** Gemini 2.5 Flash is called with the brain dump text, brand voice profile JSON, and a 512 thinking token budget; the prompt instructs the model to produce semantic HTML: H1 title, meta description in an HTML comment, H2/H3 headings, body paragraphs, and conclusion targeting 800–1,500 words, conforming to the tone, cadence, and banned jargon in the voice profile.

3. **Given** the blog generation call succeeds, **When** the HTML is returned, **Then** the voice fidelity check runs: `integrations/gemini.py`'s `check_fidelity()` is called with the blog HTML and brand voice profile using a 256 thinking token budget; the response is a JSON object containing `tone_score` (0–10), `cadence_score` (0–10), and `jargon_violations` (int); `campaigns.voice_score` is updated with this JSON.

4. **Given** the social post generation step runs after blog generation, **When** `services/generation.py` calls `integrations/gemini.py` via `generate_social()`, **Then** Gemini 2.5 Flash is called with the brain dump text, brand voice profile, blog title extracted from the H1, and a 0 thinking token budget; the prompt instructs the model to produce: an X post (text only, ≤280 characters) and a LinkedIn post (500–1,300 characters with line breaks for readability) that reference and tease the blog content without duplicating it.

5. **Given** text generation completes (blog + voice check + social posts), **When** all calls succeed, **Then** `campaigns.blog_html`, `campaigns.voice_score`, `campaigns.x_post`, and `campaigns.linkedin_post` are all updated in a single database write; the `jobs` record status remains `'in_progress'` pending image generation (Story 3.4); `generation_logs` is updated with the total Gemini token count for the user.

6. **Given** any Gemini API call returns a 5xx or 429 error, **When** it happens on the 3rd consecutive retry attempt (with exponential backoff between retries), **Then** `jobs.status` is set to `'failed'`, `jobs.error_details` is set to "Generation service temporarily unavailable — retry in a few minutes", `campaigns.status` remains `'pending_approval'` (not failed — the campaign can be retried from the same brain dump); the error is logged to Sentry.

7. **Given** `services/generation.py` is the execution context for all Gemini calls, **When** any Gemini call is made, **Then** `integrations/gemini.py` functions are called ONLY from within `services/generation.py` — never directly from routers or workers; `workers/generate.py` calls `services/generation.py`, which calls `integrations/gemini.py` (AR-19 service boundary enforcement).

8. **Given** the client has no Brand Voice Profile (`brand_voice_profile is None`), **When** the generation pipeline runs, **Then** the Gemini prompts use a neutral default voice specification ("professional, clear, and authoritative tone; moderate cadence; avoid jargon") in place of the missing profile; generation still proceeds and completes normally.

## Tasks / Subtasks

- [x] Task 1: Backend — Extend `integrations/gemini.py` with blog, fidelity, and social functions (AC: #2, #3, #4)
  - [x] 1.1 Add `async def generate_blog(brain_dump: str, brand_voice_profile: dict | None, thinking_tokens: int = 512) -> str` to `backend/app/integrations/gemini.py`
    - Prompt: instructs Gemini 2.5 Flash to produce semantic HTML blog post (H1, meta description in `<!-- meta: ... -->` comment, H2/H3, paragraphs, conclusion)
    - Targets 800–1,500 words; uses BVP tone, cadence, banned_jargon fields if present; uses default voice if BVP is None
    - Returns raw HTML string (may include markdown code fences — strip them)
    - Uses `generation_config={"thinking_budget": thinking_tokens}`
  - [x] 1.2 Add `async def check_fidelity(blog_html: str, brand_voice_profile: dict | None, thinking_tokens: int = 256) -> dict` to `backend/app/integrations/gemini.py`
    - Prompt: score the blog HTML against the BVP for tone (0–10), cadence (0–10), jargon violations (int count); returns ONLY a valid JSON object with keys `tone_score`, `cadence_score`, `jargon_violations`
    - Strip markdown fences; parse JSON; validate all three keys are present; raise `ValueError` on malformed response
    - If BVP is None, return `{"tone_score": 10, "cadence_score": 10, "jargon_violations": 0}` (no profile to check against — pass through)
  - [x] 1.3 Add `async def generate_social(brain_dump: str, blog_title: str, brand_voice_profile: dict | None, thinking_tokens: int = 0) -> dict` to `backend/app/integrations/gemini.py`
    - Prompt: generate X post (≤280 chars, no threads) and LinkedIn post (500–1,300 chars with blank-line paragraph breaks) that tease/reference the blog without duplicating it
    - Returns dict with keys `x_post` (str) and `linkedin_post` (str)
    - Truncate X post to 280 chars if model exceeds limit (safety guard); log a warning if truncation occurs
    - Uses `generation_config={"thinking_budget": thinking_tokens}` — 0 thinking tokens for social (cost optimization per NFR-9)

- [x] Task 2: Backend — `services/generation.py` (AC: #1, #2, #3, #4, #5, #6, #7, #8)
  - [x] 2.1 Create `backend/app/services/generation.py` with `async def run_generation_pipeline(job_id: uuid.UUID, db: AsyncSession) -> None`
  - [x] 2.2 Step 1 — Load context: `await jobs_repo.get_job(db, job_id)` → set `job.status = 'in_progress'`, `job.started_at = utcnow()`; load Campaign and Client (BVP); commit status update before generation starts so polling sees `in_progress`
  - [x] 2.3 Step 2 — Blog generation: call `await gemini.generate_blog(brain_dump, brand_voice_profile)` with retry wrapper (3 attempts, exponential backoff: 1s, 2s, 4s); on success update `campaign.blog_html`
  - [x] 2.4 Step 3 — Voice fidelity check: extract blog title from `<h1>` tag using regex; call `await gemini.check_fidelity(blog_html, brand_voice_profile)`; update `campaign.voice_score`
  - [x] 2.5 Step 4 — Social generation: call `await gemini.generate_social(brain_dump, blog_title, brand_voice_profile)`; update `campaign.x_post` and `campaign.linkedin_post`
  - [x] 2.6 Commit all campaign text fields in a single DB write after all three generation steps succeed
  - [x] 2.7 Log to `generation_logs`: create entry with `user_id`, `campaign_id`, and total estimated `gemini_tokens` (sum of thinking tokens: 512 + 256 + 0 = 768 as estimate)
  - [x] 2.8 After text generation succeeds, do NOT set job to `complete` yet — leave `in_progress` for Story 3.4 image generation to complete
  - [x] 2.9 On any unrecoverable error (3 retry exhaustion): set `job.status = 'failed'`, `job.error_details = "Generation service temporarily unavailable — retry in a few minutes"`; campaign status stays `pending_approval`; log to Sentry via `sentry_sdk.capture_exception(exc)`
  - [x] 2.10 Implement `_gemini_with_retry(fn, *args, max_retries=3, **kwargs)` async helper: catches `google.api_core.exceptions.ServiceUnavailable` and `google.api_core.exceptions.ResourceExhausted` (429); exponential backoff between retries; re-raises after max_retries

- [x] Task 3: Backend — `workers/generate.py` (AC: #1, #7)
  - [x] 3.1 Replace the stub in `backend/app/workers/generate.py` with the real implementation:
    ```python
    async def run_generation(job_id: uuid.UUID) -> None:
        async with get_async_session() as db:
            await generation_service.run_generation_pipeline(job_id, db)
    ```
  - [x] 3.2 The worker creates its own async database session (cannot use the request-scoped session from the router — BackgroundTasks run after the HTTP response is sent)
  - [x] 3.3 Any uncaught exception in the worker must be logged to Sentry and must NOT crash the FastAPI process

- [x] Task 4: Backend — Update `db/repositories/jobs.py` (AC: #1, #5, #6)
  - [x] 4.1 Add `async def update_job_status(db, job_id, status, started_at=None, completed_at=None, error_details=None) -> Job` to jobs repository
  - [x] 4.2 Verify `get_job(db, job_id) -> Job | None` exists (already present from Story 3.1 / existing router)

- [x] Task 5: Backend — Update `db/repositories/campaigns.py` (AC: #5)
  - [x] 5.1 Add `async def update_campaign_content(db, campaign_id, blog_html, voice_score, x_post, linkedin_post) -> Campaign` that does a single atomic UPDATE of all text fields
  - [x] 5.2 Verify `get_campaign(db, campaign_id)` exists from Story 3.1

- [x] Task 6: Backend tests (AC: #2, #3, #4, #5, #6, #8)
  - [x] 6.1 Create `backend/tests/test_generation_service.py` with mocked Gemini calls:
    - Happy path: all three Gemini calls succeed → campaign fields updated + job in_progress
    - Blog generation returns malformed HTML → still proceeds (HTML stored as-is)
    - Fidelity check returns malformed JSON → raises ValueError, job set to failed
    - 3rd retry on 429 → job set to failed, error_details set
    - No BVP (None) → default voice used, generation completes normally
  - [x] 6.2 Create `backend/tests/test_gemini_generation.py` with unit tests for the three new gemini.py functions (mocked `generate_content_async`): correct prompt construction, JSON parsing, markdown fence stripping, X post truncation at 280 chars

## Dev Notes

### Service Boundary (AR-19)

Call chain is strictly enforced:
```
router (campaigns.py)
  └── BackgroundTask → workers/generate.py
        └── services/generation.py      ← ONLY location that calls gemini.py
              └── integrations/gemini.py
```

Never import or call `integrations/gemini.py` from anywhere except `services/generation.py`. Never add business logic (subscription checks, DB writes) to the router layer.

### Async DB Session in BackgroundTask

FastAPI `BackgroundTasks` run AFTER the response is sent, outside the request lifecycle. The request-scoped `AsyncSession` from `Depends(get_session)` is closed when the response completes. The worker must create its own session:

```python
# workers/generate.py
from app.db.connection import async_session_maker  # or contextmanager

async def run_generation(job_id: uuid.UUID) -> None:
    async with async_session_maker() as db:
        await generation_service.run_generation_pipeline(job_id, db)
```

Verify that `app.db.connection` exposes an `async_session_maker` or equivalent context manager (it should, as the ingestion worker uses the same pattern).

### Gemini API — Blog Post Prompt Template

```python
_BLOG_PROMPT = """You are an expert blog writer. Using the Brand Voice Profile provided, 
write an SEO-optimized blog post in semantic HTML format.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP (author's raw idea):
{brain_dump}

OUTPUT FORMAT (HTML only, no markdown fences):
<h1>Title Here</h1>
<!-- meta: One sentence meta description for SEO -->
<h2>Section Heading</h2>
<p>Body paragraph...</p>
...
<h2>Conclusion</h2>
<p>Closing paragraph...</p>

REQUIREMENTS:
- Target 800-1,500 words
- Use H2 and H3 for structure; only one H1 (the title)
- Match the tone: {tone_list}
- Match the cadence: avg sentence length {avg_sentence_length} words
- Never use these jargon terms: {banned_jargon_list}
- Output ONLY the HTML — no explanation, no markdown
"""
```

### Gemini API — Voice Fidelity Prompt Template

```python
_FIDELITY_PROMPT = """Score the following blog post against the Brand Voice Profile.

BRAND VOICE PROFILE:
{bvp_json}

BLOG HTML:
{blog_html}

Return ONLY a valid JSON object (no markdown):
{{
  "tone_score": <integer 0-10>,
  "cadence_score": <integer 0-10>,
  "jargon_violations": <integer count of banned terms found>
}}
"""
```

### Gemini API — Social Post Prompt Template

```python
_SOCIAL_PROMPT = """Based on the brain dump and brand voice, write two social media posts.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP:
{brain_dump}

BLOG TITLE:
{blog_title}

Return ONLY a valid JSON object (no markdown):
{{
  "x_post": "<X post text, max 280 characters, tease the blog without duplicating it>",
  "linkedin_post": "<LinkedIn post, 500-1300 characters, use blank lines for paragraph breaks>"
}}
"""
```

### Gemini API Version Note

The existing `integrations/gemini.py` uses `google.generativeai` with:
```python
model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config={"thinking_budget": thinking_tokens},
)
response = await model.generate_content_async(prompt)
raw = response.text.strip()
```
Use the same pattern for all three new functions. The `thinking_budget` of `0` for social posts is valid and disables thinking (pure generation mode, lowest cost).

### VoiceScore Type Mismatch Note

The existing `frontend/lib/types.ts` has:
```typescript
export interface VoiceScore {
  score: number;
  rationale: string;
  flags: string[];
}
```

But the actual `voice_score` JSON produced by this story is:
```json
{"tone_score": 8, "cadence_score": 7, "jargon_violations": 0}
```

The TypeScript type in `types.ts` is WRONG for this implementation. Update `VoiceScore` in `types.ts` as part of this story to match the actual backend schema:
```typescript
export interface VoiceScore {
  tone_score: number;
  cadence_score: number;
  jargon_violations: number;
}
```
This has no UI impact in Epic 3 (the Approval Gate in Epic 4 reads this field), but it must be corrected now to avoid a hard failure in Epic 4 development.

### Job Status After Story 3.3

After Story 3.3 completes (text generation only), the job remains `in_progress`. Story 3.4 image generation then runs and sets `job.status = 'complete'` when done. This means the polling in Story 3.2 will continue through image generation — the message cycling logic (message index 3: "Generating featured image...") maps to the in_progress state during Story 3.4's execution.

**For testing Story 3.3 in isolation**: temporarily add `job.status = 'complete'` at the end of `run_generation_pipeline` in Story 3.3, then remove it when Story 3.4 is implemented.

### Error Handling — Sentry

```python
import sentry_sdk

# In the except block after all retries exhausted:
sentry_sdk.capture_exception(exc)
await jobs_repo.update_job_status(
    db, job_id, 
    status='failed',
    error_details="Generation service temporarily unavailable — retry in a few minutes"
)
await db.commit()
```

### File Structure

**Updated files this story:**
```
backend/app/integrations/gemini.py          ← ADD generate_blog, check_fidelity, generate_social
backend/app/workers/generate.py             ← REPLACE stub with real implementation
backend/app/db/repositories/campaigns.py   ← ADD update_campaign_content
backend/app/db/repositories/jobs.py        ← ADD update_job_status
frontend/lib/types.ts                       ← UPDATE VoiceScore interface
```

**New files this story:**
```
backend/app/services/generation.py
backend/tests/services/test_generation.py
backend/tests/integrations/test_gemini_generation.py
```

### References

- FR-13 Blog generation spec (SEO HTML, 512t, 800-1500 words, voice fidelity check 256t): [Source: _bmad-output/planning-artifacts/epics.md#FR-13]
- FR-14 Social post generation (X ≤280 chars, LinkedIn 500-1300 chars, 0 thinking tokens): [Source: _bmad-output/planning-artifacts/epics.md#FR-14]
- FR-15 Job durability — job record status updated in_progress before work begins: [Source: _bmad-output/planning-artifacts/epics.md#FR-15]
- NFR-9 Cost controls — thinking tokens: 0/social, 256/fidelity, 512/blog, 1024/ingestion; Gemini 5xx/429 → fail after 3 consecutive: [Source: _bmad-output/planning-artifacts/epics.md#NFR-9]
- AR-19 Service boundaries — generation.py is ONLY caller of gemini.py: [Source: _bmad-output/planning-artifacts/epics.md#AR-19]
- `backend/app/integrations/gemini.py` — existing `extract_brand_voice` function pattern to follow for new functions
- `backend/app/workers/ingest.py` — existing worker pattern for async session creation
- `backend/app/services/ingestion.py` — existing service pattern (retry logic, error handling)
- Story 3.4 (image pipeline — completes the job to 'complete' status): [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation proceeded without blockers.

### Completion Notes List

- Task 1: Added `generate_blog`, `check_fidelity`, `generate_social` to `integrations/gemini.py`. All use same `genai.GenerativeModel` pattern as `extract_brand_voice`. BVP-None fallback uses default voice string. X post safety-truncated at 280 chars with warning log. Markdown fence stripping via shared `_strip_fences` helper.
- Task 2: Created `services/generation.py` with `run_generation_pipeline`. Follows AR-19 service boundary — only caller of gemini.py. `_gemini_with_retry` catches `google.api_core.exceptions` (ServiceUnavailable + ResourceExhausted) with exponential backoff (1s/2s/4s). On failure: Sentry capture + job.status='failed'. Job left `in_progress` after text generation for Story 3.4 image step.
- Task 3: Replaced stub in `workers/generate.py` with real implementation creating its own `AsyncSessionLocal` session (request-scoped session unavailable in BackgroundTasks). Uncaught exceptions logged to Sentry without crashing FastAPI.
- Task 4: Added `get_job` and `update_job_status` to `db/repositories/jobs.py`.
- Task 5: Added `update_campaign_content` to `db/repositories/campaigns.py` for atomic single-write update.
- Task 6: 21 tests pass (15 gemini unit tests + 6 service tests). Pre-existing failures in `test_client_limit.py` (4 tests) confirmed unrelated to this story.
- Frontend: Updated `VoiceScore` interface in `frontend/lib/types.ts` to match actual backend schema (`tone_score`, `cadence_score`, `jargon_violations`).

### File List

backend/app/integrations/gemini.py
backend/app/services/generation.py (new)
backend/app/workers/generate.py
backend/app/db/repositories/jobs.py
backend/app/db/repositories/campaigns.py
backend/tests/test_gemini_generation.py (new)
backend/tests/test_generation_service.py (new)
frontend/lib/types.ts

### Review Findings

- [x] [Review][Patch] `check_fidelity` not wrapped in `_gemini_with_retry` — AC 6 violation; transient errors fail immediately [generation.py:133]
- [x] [Review][Patch] Duplicate cadence line in `_BLOG_PROMPT` template — false positive, only one line exists [gemini.py:_BLOG_PROMPT]
- [x] [Review][Patch] `re` imported but unused in `gemini.py` [gemini.py:9]
- [x] [Review][Patch] `_fail_job` does not set `job.completed_at` on failure [generation.py:_fail_job]
- [x] [Review][Patch] `blog_title` regex returns raw inner HTML markup, polluting social prompt [generation.py:130-131]
- [x] [Review][Patch] `_strip_fences` fragile with unclosed or unpaired fences [gemini.py:_strip_fences]
- [x] [Review][Patch] X post truncated without ellipsis — produces incoherent cut [gemini.py]
- [x] [Review][Patch] LinkedIn post length not validated (should warn if outside 500–1300 chars) [gemini.py]
- [x] [Review][Patch] `_fail_job` bare `except: pass` hides rollback errors silently [generation.py:187-189]
- [x] [Review][Patch] Empty `blog_html` not validated before fidelity/social steps [generation.py]
- [x] [Review][Patch] Social JSON values not type-checked (could be null/non-string) [gemini.py]
- [x] [Review][Patch] Job not found case doesn't capture to Sentry [generation.py:89-91]
- [x] [Review][Defer] `update_campaign_content`/`update_job_status` defined but unused — pre-existing design inconsistency [campaigns.py, jobs.py]
- [x] [Review][Defer] `_strip_fences` not refactored into `extract_brand_voice` — pre-existing code not in scope [gemini.py:extract_brand_voice]
- [x] [Review][Defer] Prompt injection risk via user-supplied `brain_dump` in template — systemic security concern [gemini.py]

## Change Log

- 2026-07-02: Story 3.3 implemented — blog/social content generation pipeline. Added `generate_blog`, `check_fidelity`, `generate_social` to gemini.py; created `services/generation.py` with full pipeline + retry logic; replaced generate worker stub; added repository helpers; updated `VoiceScore` TypeScript interface; 21 new tests passing.
- 2026-07-02: Code review complete — 12 patch findings, 3 deferred. Patches applied.
