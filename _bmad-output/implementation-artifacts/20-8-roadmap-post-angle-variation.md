---
baseline_commit: a3a9692fef14c1a52c422c7f6bff6e2682ce9580
---

# Story 20.8: Angle Variation Engine for Weekly Posts

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a PersonnaPress user reviewing a planned week,
I want each social post generated for the week to take a distinct content angle on my brain dump, with the angle shown on each post card,
so that my week reads like a deliberate content series instead of the same post restated three to five times.

## Context and Root Cause

Today `generate_roadmap` (`backend/app/services/roadmap.py`) loops over the LinkedIn and X slot counts and calls `generate_social_only(roadmap.brain_dump, bvp, platform, campaign_id, db)` with **identical inputs on every iteration** (same brain dump, same BVP, no distinguishing signal). Each call runs the same `generate_social_standalone` prompt, so the only thing separating post 1 from post 5 is LLM sampling randomness. Result: near-duplicate posts.

This story introduces a **two-stage angle planner** (the approach chosen by the product owner):
1. **Stage 1 — Week Planner (one LLM call):** given the brain dump, BVP, and slot counts, produce a deduped plan assigning a distinct `{angle, hook, facet}` to each social slot, biased by platform. The planner sees the whole week at once, which is what guarantees non-overlap.
2. **Stage 2 — Per-post writer (existing pipeline):** each slot calls the existing `generate_social_only`, now passed its assigned angle + hook as a prompt directive. Retry, image, and scheduling flows are unchanged.

The assigned angle is persisted on the campaign and surfaced as a small label chip on each week-review `PostCard`.

Best-practice grounding (2026): the highest-performing social angle families are contrarian takes, specific-number/data proof, pain-point confession / personal story, how-to / framework, myth-busting, and engagement questions. The taxonomy below maps to these. [See References.]

## Design Decisions (locked with product owner)

- **Two-stage planner (not per-slot rotation, not one-shot all-posts).** Guarantees variety while preserving the robust per-post generation and image pipeline.
- **Platform-aware angles.** LinkedIn favors narrative/long-form angles; X favors punchy/short angles.
- **Stretch, do not invent.** When the brain dump only supports a few real ideas, the planner spreads them across different angles/formats. It must NOT fabricate facts, numbers, or claims not supported by the brain dump. Voice fidelity and factual honesty outrank variety.
- **Angle is visible.** Each post card shows an angle label chip so the variety reads as intentional and can inform future per-post regeneration.
- **Resilient, not a hard dependency.** If the planner call fails or returns fewer slots than needed, generation falls back to a deterministic angle rotation over the taxonomy so posts are still produced and still varied.

## Angle Taxonomy

Canonical angle codes with display labels (single source of truth, defined once in the backend and mirrored in the frontend chip renderer):

| code | display label | platforms | intent |
|------|---------------|-----------|--------|
| `personal_story` | Personal story | linkedin | first-person narrative / behind-the-scenes |
| `lesson_learned` | Lesson learned | linkedin | mistake or hard-won takeaway |
| `how_to` | How-to | linkedin, x | actionable framework or steps |
| `data_proof` | Data proof | linkedin, x | number/outcome-led credibility |
| `contrarian` | Contrarian take | linkedin, x | challenges conventional wisdom |
| `myth_bust` | Myth-buster | linkedin, x | corrects a common misconception |
| `prediction` | Prediction | linkedin | trend / where things are heading |
| `engagement_q` | Question | linkedin, x | opinion-eliciting prompt |
| `quick_tip` | Quick tip | x | one sharp, immediately usable tip |
| `hot_take` | Hot take | x | blunt one-liner opinion |

Platform preference order (planner and fallback rotation both draw in this order, skipping repeats until the pool is exhausted, then cycling):
- **LinkedIn:** `personal_story`, `data_proof`, `how_to`, `contrarian`, `lesson_learned`, `myth_bust`, `prediction`, `engagement_q`
- **X:** `contrarian`, `data_proof`, `quick_tip`, `hot_take`, `how_to`, `myth_bust`, `engagement_q`

Blog slots do NOT receive an angle (a full article already commits to a single angle via the existing blog prompt).

## Acceptance Criteria

1. **DB: persist angle on campaign**: Add a nullable `angle` column (`Text`, nullable) to the `campaigns` table via a new Alembic migration under `backend/alembic/versions/`. Add the field to the `Campaign` SQLModel in `backend/app/db/repositories/models.py` (mirror the pattern of `article_template: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))`). Existing rows and all non-roadmap / blog campaigns keep `angle = NULL`. The migration must have correct `upgrade`/`downgrade` and follow the existing timestamped filename convention (e.g. `backend/alembic/versions/20260809_1946_4317d2f4b9b7_add_target_word_count_to_campaigns.py`).

2. **Angle taxonomy module (single source of truth)**: Add the taxonomy from the section above as a Python structure (codes, display labels, per-platform preference order) in a backend module (e.g. `backend/app/services/angles.py` or a constant block in `roadmap.py`). Include a deterministic helper `fallback_angles(platform: str, count: int) -> list[str]` that returns `count` angle codes drawn in the platform preference order, cycling if `count` exceeds the pool. This helper is used both to seed the planner prompt's allowed set and as the no-LLM fallback.

3. **Stage 1 — Week Planner LLM method (both providers)**: Add `generate_week_plan(...)` to BOTH `backend/app/integrations/anthropic_client.py` and `backend/app/integrations/gemini.py` (the `_llm` indirection in `generation.py` requires interface parity — see `generation.py:26-29`). Signature (keyword-compatible across providers):
   ```python
   async def generate_week_plan(
       brain_dump: str,
       brand_voice_profile: dict | None,
       linkedin_count: int,
       twitter_count: int,
   ) -> dict:
       """Return {"linkedin": [{"angle","hook","facet"}, ...],
                  "x":        [{"angle","hook","facet"}, ...]}
       with exactly linkedin_count and twitter_count entries respectively."""
   ```
   - Uses a new `_WEEK_PLAN_PROMPT` in `backend/app/integrations/generation_prompts.py`.
   - Prompt requirements: instruct the model to assign a DISTINCT angle+hook per slot drawn from the allowed per-platform angle set; make the entries non-overlapping; when the brain dump is thin, STRETCH the same underlying ideas across different angles rather than inventing facts; `angle` MUST be one of the taxonomy codes; `hook` is a one-line opening thesis unique to that slot; `facet` names the specific part of the brain dump used. No em-dash / double-dash in any generated text.
   - Returns parsed JSON. Validate shape: each list has the requested length and each `angle` is a known code; coerce/repair minimally (see AC 6 for failure handling). Reuse the existing JSON-fence stripping + `json.loads` + validation pattern already used by `generate_social_standalone` in each provider file.
   - This is a lightweight call (compact JSON out, not full posts). Keep it in the existing retry wrapper style.

4. **Stage 2 — thread angle into the writer**: Extend `generate_social_only` in `backend/app/services/generation.py` to accept an optional `angle: str | None = None` and `hook: str | None = None`, and `generate_social_standalone` (both providers) to accept an optional angle directive. When an angle/hook is provided, inject a directive block into the prompt, e.g.:
   ```
   ANGLE FOR THIS POST (write ONLY from this angle):
   - Angle: {display_label}
   - Opening thesis / hook to build from: {hook}
   - Do not restate other angles. Commit fully to this one angle. Do not invent facts beyond the brain dump.
   ```
   When `angle`/`hook` are `None` (e.g., the existing `run_social_only_pipeline` social-only campaign path, which is NOT a roadmap), behavior is exactly as today — this keeps `campaign_type='social_only'` brain-dump campaigns unchanged. `generate_social_only` writes the resolved `angle` code onto `campaign.angle` before commit.

5. **Orchestration in `generate_roadmap`**: In `backend/app/services/roadmap.py`, before the X/LinkedIn slot loops, call the planner ONCE:
   ```python
   plan = await _plan_week_angles(roadmap.brain_dump, bvp, linkedin_count, twitter_count, db)
   ```
   - `_plan_week_angles` wraps `_llm.generate_week_plan` in the module's retry helper; on any failure it logs + `sentry_sdk.capture_exception` and returns a fallback plan built from `fallback_angles("linkedin", linkedin_count)` and `fallback_angles("x", twitter_count)` (angle codes only, `hook=None`). The roadmap MUST still generate — the planner is best-effort.
   - In the X loop, pass `plan["x"][i]`'s angle + hook to `generate_social_only`. In the LinkedIn loop, pass `plan["linkedin"][i]`'s angle + hook. Persist the angle on each campaign (via AC 4).
   - Preserve all existing behavior: blog slot first (no angle), image assignment for the first `allowed_images` campaigns, `title_hints`, status transitions, and error handling. Do not change the campaign creation order or the image-quota logic.

6. **Planner failure + partial-result handling**: If the planner returns fewer entries than requested for a platform, pad the remainder using `fallback_angles(platform, missing)` starting after the returned angles (avoid immediate repeats). If an individual returned `angle` is not a known code, replace it with the next fallback angle for that platform. A planner failure never fails the roadmap; a single post-writer failure is handled exactly as today (the existing try/except in `generate_roadmap` marks the roadmap failed only on unrecoverable errors).

7. **API: expose angle**: In `backend/app/routers/roadmaps.py`, add `angle: Optional[str] = None` to `CampaignSummary` and populate it from `c.angle` in `get_roadmap_status`. (Blog and non-roadmap campaigns return `null`.) No change to list or approve endpoints.

8. **Frontend type + PostCard chip**: 
   - `frontend/lib/types.ts`: add `angle?: string | null` to `RoadmapCampaignSummary`.
   - Add a display-label map mirroring the taxonomy (code -> label) in the frontend (e.g. in `PostCard.tsx` or a small `frontend/lib/angles.ts`).
   - In `frontend/components/roadmap/PostCard.tsx`, render a small angle chip next to the existing platform chip (same top row, `frontend/components/roadmap/PostCard.tsx:68-88`). The chip shows the display label; if `angle` is null/unknown or the card is a blog, render no chip. See UI/UX spec below for exact styling.

9. **No regression to single-campaign flows**: `campaign_type='social_only'` brain-dump campaigns (via `run_social_only_pipeline`) and full blog campaigns (via `run_generation_pipeline`) are unaffected: they do not call the planner and pass no angle, so `campaign.angle` stays `NULL` and their generation is byte-for-byte equivalent to today. Confirm `generate_social_standalone`'s existing callers still work when the new angle params default to `None`.

## UI/UX Specification (Paper Style)

Angle chip on `PostCard`, placed inline in the existing top row beside the platform chip (do not add a new row; keep the platform chip left, angle chip immediately to its right, status badge stays right-aligned):

```tsx
{/* inside the left cluster, after the platform label span, when angle exists and not blog */}
{angleLabel && platformLabel !== "Blog" && (
  <span className="font-body text-xs uppercase tracking-[0.08em] text-graphite border border-[#E5E5E5] px-1.5 py-0.5 shrink-0 whitespace-nowrap">
    {angleLabel}
  </span>
)}
```

- **On-brand:** matches the existing mono/body uppercase `tracking-[0.08em]` chip language already used for the platform label and status badges; uses the same `#E5E5E5` border token and `text-graphite`; no fill, no shadow (keeps the card's single 4px hard shadow on hover as the only elevation). No emoji, no icon — text only, consistent with the platform label.
- **Layout:** lives in the `flex items-center gap-1.5 min-w-0` left cluster; `shrink-0` + `whitespace-nowrap` so it never wraps mid-label; if space is tight the platform label (which has `truncate`) yields first. Keep `gap-1.5` rhythm (multiple of the 8pt-ish scale already in the card).
- **States:** static label, non-interactive (not a button, no hover/focus target) so it adds no touch-target obligations. When `isRemoved`, it inherits the card's `opacity-50` like the rest of the card. Blog cards render no chip.
- **Accessibility:** decorative-adjacent but meaningful; render as plain text within the existing row. Because it is not interactive, no `aria`/focus handling is required. Do not use `title`-only tooltips to convey it. Ensure contrast: `text-graphite` (#555-ish) on white meets AA for this small-caps label as already used elsewhere on the card.
- **Motion:** none. The chip appears with the card; no separate entrance animation (the card grid already renders many instances, so per-chip motion is inappropriate).

## Tasks / Subtasks

- [x] Task 1: DB + model (AC: 1)
  - [x] New Alembic migration adding nullable `angle` `Text` column to `campaigns`
  - [x] Add `angle: Optional[str]` field to `Campaign` in `models.py`
- [x] Task 2: Angle taxonomy module + fallback helper (AC: 2)
  - [x] Define codes, display labels, per-platform preference order
  - [x] Implement `fallback_angles(platform, count)`
- [x] Task 3: Week Planner prompt + LLM methods (AC: 3)
  - [x] Add `_WEEK_PLAN_PROMPT` to `generation_prompts.py`
  - [x] Implement `generate_week_plan` in `anthropic_client.py`
  - [x] Implement `generate_week_plan` in `gemini.py` (interface parity)
  - [x] Shape validation + minimal repair of the returned plan
- [x] Task 4: Thread angle into the writer (AC: 4, 9)
  - [x] `generate_social_only(..., angle=None, hook=None)`; write `campaign.angle`
  - [x] `generate_social_standalone(..., angle directive)` in both providers, no-op when `None`
- [x] Task 5: Orchestration (AC: 5, 6)
  - [x] `_plan_week_angles(...)` wrapper with fallback in `roadmap.py`
  - [x] Call planner once; pass per-slot angle+hook into X and LinkedIn loops
  - [x] Pad/repair per AC 6; preserve image assignment, ordering, error handling
- [x] Task 6: API exposure (AC: 7)
  - [x] Add `angle` to `CampaignSummary`; populate from `c.angle`
- [x] Task 7: Frontend chip (AC: 8)
  - [x] `RoadmapCampaignSummary.angle`; code->label map; render chip in `PostCard`
- [x] Task 8: Tests (see Testing standards)
  - [x] Backend unit: `fallback_angles` cycles correctly; planner-failure path returns a valid fallback plan; `generate_social_only` persists `angle` and no-ops directive when `None`
  - [x] Roadmap generation test asserts distinct angles assigned across slots

## Dev Notes

### Reuse, do not reinvent
- The per-post writer, retry wrapper (`_llm_with_retry`), image pipeline (`image_service.generate_image_for_roadmap_campaign`), scheduling, and status machine already exist in `roadmap.py` / `generation.py`. This story ADDS a planner and a directive; it does not rewrite generation. Do not introduce a second generation path or a bulk "all posts in one call" method.
- The JSON handling (`_strip_fences`, `json.loads`, key/type validation, char-limit truncation) in `generate_social_standalone` is the template for `generate_week_plan`'s parsing. Follow it in each provider file for consistency.

### Provider parity is mandatory
`generation.py` binds `_llm` to `anthropic_client` OR `gemini` based on `settings.LLM_PROVIDER` (`generation.py:26-29`). Any new method the service calls (`generate_week_plan`) MUST exist in BOTH modules with the same signature and return shape, or the non-active provider breaks at runtime. Mirror the existing dual-implementation of `generate_social_standalone`.

### Keep social-only (non-roadmap) generation identical
`run_social_only_pipeline` (campaign_type='social_only') and blog campaigns must not touch the planner. The new `angle`/`hook` params default to `None`, and the directive block is only emitted when non-None. Verify existing tests for `generate_social_standalone` / social-only still pass with unchanged output.

### "Stretch, do not invent" is a hard rule
The planner and the writer directive both must forbid fabricating facts, numbers, tools, or outcomes not present in the brain dump. When material is thin, vary the ANGLE and FORMAT over the same facts, not the facts themselves. This protects the brand-voice/fidelity positioning that the rest of the pipeline enforces (voice fidelity check on the blog path). Bake this instruction into `_WEEK_PLAN_PROMPT` and the writer directive text.

### Do not break image assignment order
`generate_roadmap` assigns images to the FIRST `allowed_images` campaigns in creation order (blog, then X slots, then LinkedIn slots). Adding the planner must not reorder campaign creation or the `campaign_ids` / `title_hints` lists. Compute the plan up front, then consume it inside the existing loops without changing their structure.

### Copy constraints
No em-dash (—) or double-dash (--) in generated posts, hooks, or prompts; restructure naturally. No emojis. Applies to `_WEEK_PLAN_PROMPT` output and the writer directive. See project memory "No Double-Dash in Copy".

### Files being created / modified

| File | Change |
|------|--------|
| `backend/alembic/versions/<new>_add_angle_to_campaigns.py` | NEW: add nullable `angle` Text column |
| `backend/app/db/repositories/models.py` | Add `angle: Optional[str]` to `Campaign` |
| `backend/app/services/angles.py` (or const block in `roadmap.py`) | NEW: taxonomy + `fallback_angles` |
| `backend/app/integrations/generation_prompts.py` | Add `_WEEK_PLAN_PROMPT`; add angle directive text |
| `backend/app/integrations/anthropic_client.py` | Add `generate_week_plan`; angle directive in `generate_social_standalone` |
| `backend/app/integrations/gemini.py` | Add `generate_week_plan`; angle directive in `generate_social_standalone` |
| `backend/app/services/generation.py` | `generate_social_only(..., angle, hook)`; persist `campaign.angle`; pass directive |
| `backend/app/services/roadmap.py` | `_plan_week_angles` + fallback; wire per-slot angle/hook into loops |
| `backend/app/routers/roadmaps.py` | Add `angle` to `CampaignSummary`; populate from `c.angle` |
| `frontend/lib/types.ts` | Add `angle?: string \| null` to `RoadmapCampaignSummary` |
| `frontend/lib/angles.ts` (or map in PostCard) | NEW: angle code -> display label map |
| `frontend/components/roadmap/PostCard.tsx` | Render angle chip in the top row |

### Testing standards
- Backend tests live in `backend/tests/`. Roadmap generation already has tests: `backend/tests/services/test_roadmap_generation.py` and `test_roadmap_distribute.py`, and generation tests in `test_generation_service.py`. Add/extend:
  - `fallback_angles` returns the expected sequence and cycles past the pool length.
  - Planner-failure path (`generate_week_plan` raises) yields a fallback plan and generation still completes with distinct angles per platform.
  - `generate_social_only` writes `campaign.angle` and emits NO directive when `angle=None` (existing social-only output unchanged).
- Mock the LLM calls (do not hit live providers) — follow the existing mocking pattern in `test_generation_service.py` / `test_roadmap_generation.py`.
- Frontend: a small render test that `PostCard` shows the mapped label when `angle` is set and shows no chip for blog / null angle is welcome, matching `frontend/__tests__` conventions; not a hard gate (consistent with Epic 20 practice).

### References
- [Source: backend/app/services/roadmap.py#L104-L143] — X/LinkedIn slot loops calling `generate_social_only` with identical inputs (the bug)
- [Source: backend/app/services/generation.py#L248-L309] — `generate_social_only` to extend with angle/hook + persist
- [Source: backend/app/services/generation.py#L26-L29] — `_llm` provider indirection requiring parity
- [Source: backend/app/integrations/anthropic_client.py#L433-L577] — `generate_social_standalone` (parsing/validation template + directive injection point)
- [Source: backend/app/integrations/gemini.py#L608-L756] — gemini `generate_social_standalone` counterpart
- [Source: backend/app/integrations/generation_prompts.py#L371-L398] — `_SOCIAL_STANDALONE_PROMPT` (prompt style to match)
- [Source: backend/app/db/repositories/models.py#L150-L199] — `Campaign` model; `article_template` field is the pattern for the new `angle` column
- [Source: backend/app/routers/roadmaps.py#L82-L92] — `CampaignSummary` to extend
- [Source: frontend/components/roadmap/PostCard.tsx#L59-L95] — top row where the chip is added
- [Source: frontend/lib/types.ts#L61-L80] — `RoadmapCampaignSummary`
- [Source: https://buffer.com/resources/social-media-hooks/] — hook psychology (contrarian, specific numbers, pain-point, unexpected comparison)
- [Source: https://connectsafely.ai/articles/linkedin-post-ideas-engagement-2026] — LinkedIn post-type variety for 2026
- [Source: https://www.freeformagency.com/post/types-of-content-for-social-media] — content-type mix / avoiding single-format stagnation

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
- Removed redundant local `import sentry_sdk` inside `plan_week_angles` except block (module-level import already present) to fix mock-patch path in tests.
- `_repair_plan_entries` + `_next_fallback` + `_pad_fallback` helpers duplicated in both `anthropic_client.py` and `gemini.py` (cannot import angles module from integrations layer into each other, and generation.py is the sole caller of both).
- `plan_week_angles` placed in `generation.py` (not `roadmap.py`) to keep provider isolation: roadmap.py calls `generation_service.plan_week_angles` which internally uses `_llm.generate_week_plan`.

### Completion Notes List
- AC 1: Alembic migration `20260821_0930_f8a9b0c1d2e3_add_angle_to_campaigns.py` adds nullable `Text` column. `Campaign.angle` field added mirroring `article_template` pattern.
- AC 2: `backend/app/services/angles.py` is the single source of truth: ANGLE_LABELS, KNOWN_CODES, platform preference orders, `fallback_angles()`.
- AC 3: `_WEEK_PLAN_PROMPT` and `_ANGLE_DIRECTIVE_TEMPLATE` added to `generation_prompts.py`. `generate_week_plan` implemented in both providers with identical signature, JSON validation, and `_repair_plan_entries` repair logic.
- AC 4: `generate_social_only` extended with `angle`/`hook` kwargs (default None); passes them to `generate_social_standalone`; persists `campaign.angle` when set. Social-only campaigns (angle=None) unchanged.
- AC 5+6: `plan_week_angles` in `generation.py` wraps `_llm.generate_week_plan` with `_llm_with_retry`; fallback on any exception. `generate_roadmap` calls it once before both slot loops; per-slot angle+hook extracted and passed to `generate_social_only`. Campaign creation order, image quota, and blog logic unchanged.
- AC 7: `CampaignSummary.angle` added; populated from `c.angle` in `get_roadmap_status`.
- AC 8: `frontend/lib/angles.ts` with `ANGLE_LABELS` map and `getAngleLabel()`. `PostCard.tsx` renders angle chip in existing left cluster; blog cards and null angles show no chip.
- AC 9: `run_social_only_pipeline` not touched; defaults `angle=None, hook=None` ensure existing social-only output unchanged (confirmed 192 generation tests pass).
- Tests: 9 new tests in `test_angle_variation.py`; 407 service/integration tests pass; 0 regressions.

### File List
- `backend/alembic/versions/20260821_0930_f8a9b0c1d2e3_add_angle_to_campaigns.py` (NEW)
- `backend/app/db/repositories/models.py` (modified — angle field on Campaign)
- `backend/app/services/angles.py` (NEW — taxonomy, ANGLE_LABELS, fallback_angles)
- `backend/app/integrations/generation_prompts.py` (modified — _WEEK_PLAN_PROMPT, _ANGLE_DIRECTIVE_TEMPLATE)
- `backend/app/integrations/anthropic_client.py` (modified — generate_week_plan, _repair_plan_entries helpers, angle directive in generate_social_standalone)
- `backend/app/integrations/gemini.py` (modified — generate_week_plan, _repair_plan_entries helpers, angle directive in generate_social_standalone)
- `backend/app/services/generation.py` (modified — generate_social_only angle/hook params + persist, plan_week_angles)
- `backend/app/services/roadmap.py` (modified — call plan_week_angles once, pass angle/hook to slot loops)
- `backend/app/routers/roadmaps.py` (modified — angle field on CampaignSummary)
- `frontend/lib/types.ts` (modified — angle on RoadmapCampaignSummary)
- `frontend/lib/angles.ts` (NEW — ANGLE_LABELS, getAngleLabel)
- `frontend/components/roadmap/PostCard.tsx` (modified — angle chip in top row)
- `backend/tests/services/test_angle_variation.py` (NEW — 9 unit tests)

### Review Findings

- [x] [Review][Patch] Angle directive silently dropped when hook is empty/None — `if angle and hook:` guard must be `if angle:` [anthropic_client.py, gemini.py]
- [x] [Review][Patch] `_repair_plan_entries` accepts valid-but-duplicate angle codes — add `or code in used_angles` to the replacement check [anthropic_client.py, gemini.py]
- [x] [Review][Patch] `_pad_fallback` can repeat already-used angles — fix to prefer unused pool codes before cycling [anthropic_client.py, gemini.py]
- [x] [Review][Patch] `_WEEK_PLAN_PROMPT` Rule 5 uses `(--)` for em-dash example, embedding a double-dash in the prompt — change to `(—)` [generation_prompts.py]
- [x] [Review][Patch] Hook text not sanitized for em-dash before injection into angle directive — strip `—` in `_repair_plan_entries` [anthropic_client.py, gemini.py]
- [x] [Review][Patch] Missing test for `_repair_plan_entries` unknown-angle-code replacement path [test_angle_variation.py]
- [x] [Review][Defer] brain_dump brace injection risk in `.format()` call — pre-existing pattern across all prompts [generation_prompts.py]
- [x] [Review][Defer] Gemini `response.text` None crash on blocked response — pre-existing pattern across all Gemini calls [gemini.py]
- [x] [Review][Defer] Private symbols `_LINKEDIN_ORDER`, `_X_ORDER` imported across module boundary — style issue [angles.py]
- [x] [Review][Defer] `ANGLE_LABELS` maintained separately in Python and TypeScript — no compile-time sync enforcement [angles.py, angles.ts]
- [x] [Review][Defer] `_repair_plan_entries`/`_next_fallback`/`_pad_fallback` helpers duplicated across providers — architectural constraint noted in dev record [anthropic_client.py, gemini.py]
- [x] [Review][Defer] No input validation on `linkedin_count`/`twitter_count` — caller-controlled, not introduced here [roadmap.py]
- [x] [Review][Defer] Angle codes listed as bare comma-separated strings in prompt (not explicit JSON array syntax) — repair layer handles invalid returns [generation_prompts.py]

## Change Log
- 2026-08-21: Story implemented. Two-stage angle planner added: week planner LLM call (both providers) + per-slot angle directive injection + campaign.angle persistence + API exposure + frontend angle chip on PostCard.
- 2026-08-21: Code review complete. 6 patches applied (see Review Findings above). 7 deferred. 7 dismissed.
