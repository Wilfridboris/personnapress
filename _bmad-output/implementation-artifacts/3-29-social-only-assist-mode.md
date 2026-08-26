# Story 3.29: Social-Only Assist Mode

---
baseline_commit: 2828423
---

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **writer who drafts my own social posts and only wants them polished**,
I want **the "Generate from my notes" / "Assist my writing" choice available when I pick "Social post only", not just for "Blog + Social"**,
so that **when I paste a post I already wrote, the tool keeps my wording and only cleans it up and fits each platform, instead of rewriting it from scratch**.

## Context and Problem

Story 3-28 shipped Assist mode (`generation_mode` = `generate` | `assist`) end to end for the **blog** path: a persisted column, a `_BLOG_ASSIST_PROMPT`, provider wiring, pipeline fidelity suppression, and a Paper Style `GenerationModeSelector`. But it was scoped to blog only. Its Task 4 and the code review both explicitly deferred "assist-social" (preserving the author's phrasing in the derived social posts) to a future story. This is that story.

What is actually in the code today:

- On the New Campaign form (`frontend/app/(app)/campaigns/new/page.tsx`), the `GenerationModeSelector` lives **inside the `blog_full`-only collapsing block** (the same block that holds Length, Template, and keyword fields). When the user selects "Social post only", the whole block collapses, so the mode selector disappears.
- On submit, the form hard-codes `generation_mode: campaignType === "blog_full" ? generationMode : null` (line ~293), so a social-only campaign is always persisted with `generation_mode = NULL` (treated as `generate`).
- The social-only generation path (`run_social_only_pipeline` -> `generate_social_standalone` in both `gemini.py` and `anthropic_client.py`) has **no `generation_mode` parameter and no assist branch at all**. It always uses `_SOCIAL_STANDALONE_PROMPT`, which writes fresh platform-native posts.

The result: a user who has already written a LinkedIn/X post and picks "Social post only" cannot ask for a light polish. The tool always rewrites. This is the same over-rewriting complaint that motivated 3-28, but on the social-only path.

The good news, confirmed by reading the code: because 3-28 already persists `generation_mode` for **all** campaign types (the create/regenerate/revoice handlers pass it unconditionally), this story needs **no DB migration, no schema change, and no router change**. It is:

1. **Frontend**: surface the existing `GenerationModeSelector` for social-only too, and stop nulling `generation_mode` on submit.
2. **Backend**: teach the social-only pipeline to honor assist mode via a new `_SOCIAL_STANDALONE_ASSIST_PROMPT` that preserves the author's wording and only adapts it to each platform's length and format, rather than composing new posts.

Assist for social means: the user's own sentences carry across all connected platforms, adjusted only for length and platform formatting. It does not invent a new angle, does not apply the Brand Voice Profile as a rewrite, and does not fabricate hooks or CTAs the author did not imply. This mirrors the blog assist contract from 3-28, applied to the fan-out shape of social.

## Acceptance Criteria

1. **Generation mode is selectable for social-only.**
   - Given the New Campaign form with Content type = "Social post only",
   - When the form is displayed,
   - Then the "Generation mode" selector ("Generate from my notes" / "Assist my writing") is visible and interactive, in the same position it occupies for "Blog + Social".

2. **Mode persists for social-only campaigns.**
   - Given Content type = "Social post only" and a selected generation mode,
   - When I create the campaign,
   - Then the chosen `generation_mode` is sent in the create request and persisted on the campaign (no longer forced to null for social), and it is carried on regenerate and re-voice exactly as it already is for blog campaigns.

3. **Blog-only fields stay blog-only.**
   - Given Content type = "Social post only",
   - Then the Length selector, Template selector, and Focus/Supporting keyword fields remain hidden (they are blog-only); only the Generation mode selector is added to the social-only view.

4. **Assist mode preserves the author's words in social posts.**
   - Given a brain dump of a finished social post and mode "Assist my writing" with Content type = "Social post only",
   - When the social posts are generated,
   - Then each platform post reproduces the author's own sentences with corrections limited to grammar, spelling, punctuation, and clear logic errors, and with only the trimming/splitting needed to fit that platform's length; it does not compose a new post, does not invent a hook or CTA the author did not write, does not substitute the author's vocabulary, and does not apply the Brand Voice Profile as a rewrite.

5. **Generate mode for social-only is unchanged.**
   - Given mode "Generate from my notes" (default) with Content type = "Social post only",
   - When the social posts are generated,
   - Then behavior matches today's `_SOCIAL_STANDALONE_PROMPT` output exactly (no regression for the default path).

6. **Assist mode respects copy rules.**
   - Given any assist-social output,
   - Then it contains no em-dash character and no double-hyphen sequence, consistent with the existing social generation (per project memory: no double-dash in copy).

7. **Both providers behave identically.**
   - Given `LLM_PROVIDER` set to Gemini or to Anthropic,
   - When assist-social runs,
   - Then both produce assist behavior from the same shared prompt in `generation_prompts.py`, matching the existing dual-provider parity pattern.

8. **Mode-aware supporting copy.**
   - Given the Generation mode selector,
   - Then each mode's one-line description reads correctly for the current Content type (social taglines describe per-platform posts, not a "full article"), and when Assist is selected the brain-dump placeholder invites a finished draft rather than rough notes.

9. **No regression to the blog path or roadmap path.**
   - Given a "Blog + Social" campaign, or a Plan My Week / roadmap social post (which also calls `generate_social_standalone`),
   - When it generates,
   - Then behavior is unchanged (the roadmap path passes no generation mode and defaults to generate).

## Tasks / Subtasks

- [x] **Task 1: Frontend - surface the selector for both content types** (AC: 1, 2, 3, 8)
  - [x] In `frontend/app/(app)/campaigns/new/page.tsx`, lift `<GenerationModeSelector>` OUT of the `blog_full`-only collapsing block so it renders for both content types, in the same visual slot (just below the brain-dump textarea, above the blog-only block). Keep Length/Template gated on `generationMode === "generate"` AND inside the `blog_full` collapsing block; keep Focus/Supporting keyword fields inside that block.
  - [x] Change the submit payload from `generation_mode: campaignType === "blog_full" ? generationMode : null` to `generation_mode: generationMode` (send for both types).
  - [x] Pass a `contentType={campaignType}` prop to `GenerationModeSelector`.
  - [x] Draft autosave/restore already persists `generationMode`; confirm it still round-trips for social-only (no change expected, but verify the restore path).

- [x] **Task 2: Frontend - mode-aware copy** (AC: 8)
  - [x] In `frontend/components/campaigns/GenerationModeSelector.tsx`, add a `contentType: "blog_full" | "social_only"` prop and swap each mode's tagline by content type. Suggested copy:
    - generate / blog_full: "Turn rough notes into a full article and social posts"
    - generate / social_only: "Turn rough notes into a post for each platform"
    - assist / blog_full: "Keep my writing and only fix grammar and logic" (current)
    - assist / social_only: "Keep my wording, just polish and fit each platform"
  - [x] Keep the mode labels identical across content types ("Generate from my notes" / "Assist my writing"). Preserve the existing Paper Style styling exactly (`border-ink/10`, `bg-[#FFF1B8]` selected highlight, `font-mono`); do not introduce new design tokens.
  - [x] When `generationMode === "assist"`, change the brain-dump textarea placeholder to invite a finished draft (for example: "Paste the post you already wrote. It will be kept as written, only cleaned up and fit to each platform."). Applies to both content types.

- [x] **Task 3: Backend - social assist prompt** (AC: 4, 6, 7)
  - [x] In `backend/app/integrations/generation_prompts.py`, add a `_SOCIAL_STANDALONE_ASSIST_PROMPT` constant. It must instruct: treat the ENTIRE brain dump as the author's finished social writing; for each platform (`x_post`, `linkedin_post`, `instagram_caption`, `facebook_post`, `threads_post`) reproduce the author's own wording, correcting only grammar/spelling/punctuation and clear logic errors; adapt ONLY by trimming or splitting to fit each platform's length limits and formatting norms; do not compose a new post, do not invent a hook, CTA, or hashtags the author did not write, do not substitute vocabulary, do not apply the Brand Voice Profile as a rewrite; preserve first-person voice, uncertainty, and asides; return the same JSON shape the standalone prompt returns; never use the em-dash character or a double hyphen (restructure naturally if tempted).
  - [x] Keep the existing `_SOCIAL_STANDALONE_PROMPT` as the default-mode prompt.
  - [x] Add unit tests in `backend/tests/test_generation_prompts.py` asserting the assist-social prompt contains the preservation + per-platform-length directives and the copy-rule directives, and does NOT contain fresh-composition scaffolding (hook/angle invention language).

- [x] **Task 4: Backend - provider wiring for both LLM clients** (AC: 4, 5, 7)
  - [x] In `backend/app/integrations/gemini.py` and `backend/app/integrations/anthropic_client.py`, extend `generate_social_standalone(...)` with a `generation_mode: str | None = None` parameter (default -> "generate"). When mode is "assist", format and use `_SOCIAL_STANDALONE_ASSIST_PROMPT`; otherwise keep the current `_SOCIAL_STANDALONE_PROMPT` path unchanged.
  - [x] Keep the two implementations in strict parity (enforced by the dual test files `test_gemini_generation.py` and `test_anthropic_generation.py`). The assist branch must still return the full 5-key dict and pass the existing non-empty validators.
  - [x] Add assist-mode tests to both `test_gemini_generation.py` and `test_anthropic_generation.py` (parity), mirroring the 3-28 `generate_blog` assist tests.

- [x] **Task 5: Backend - social-only pipeline honors the mode** (AC: 4, 5, 9)
  - [x] In `backend/app/services/generation.py` `run_social_only_pipeline`, pass `generation_mode=campaign.generation_mode` into the `generate_social_standalone(...)` call (the campaign is already loaded in that function).
  - [x] Do NOT change `generate_social_only` (the single-platform roadmap helper) beyond letting it default to generate; the roadmap/Plan My Week path has no mode selector and must keep current behavior (AC 9). If `generate_social_standalone` gains the new param with a safe default, `generate_social_only` needs no change.
  - [x] Confirm no fidelity gate exists on the social-only path (there is none today), so no suppression logic is required here (unlike the blog path in 3-28).

- [x] **Task 6: Tests - pipeline + regression** (AC: 4, 5, 9)
  - [x] In `backend/tests/test_generation_service.py`, add a test that `run_social_only_pipeline` passes `generation_mode="assist"` through to `generate_social_standalone` when the campaign has assist mode, and passes generate (or the default) otherwise.
  - [x] Confirm existing social-only pipeline tests still pass unchanged (default path).

- [x] **Task 7: Frontend tests** (AC: 1, 3, 8)
  - [x] Add/extend a test for `campaigns/new/page.tsx` (or `GenerationModeSelector`) verifying the selector renders when Content type = social_only, that Length/Template stay hidden for social_only, that the tagline copy switches with content type, and that submit sends `generation_mode` for a social-only campaign.

- [x] **Task 8: Verify** (AC: all)
  - [x] Manually run both modes on a "Social post only" campaign: (a) rough notes -> confirm Generate composes posts as today; (b) a finished LinkedIn/X post -> confirm Assist keeps the wording and only trims/formats per platform.
  - [x] Confirm regenerate and re-voice keep the mode for a social-only campaign; confirm both providers behave the same.
  - [x] Grep all new copy and prompt text for the em-dash character and `--`; restructure any occurrence.

## Dev Notes

### Current state of files being modified (read before editing)

- `frontend/app/(app)/campaigns/new/page.tsx`
  - `campaignType` state is `"blog_full" | "social_only"` (line ~89). `generationMode` state defaults to `"generate"` (line ~92).
  - The `GenerationModeSelector` is currently rendered INSIDE the collapsing block gated on `campaignType === "blog_full"` (the `grid grid-rows-[1fr|0fr]` block, ~lines 610-655), together with Length, Template, and the keyword inputs. This is why it vanishes for social. Move only the selector out; leave the rest.
  - Submit (line ~293) currently sends `generation_mode: campaignType === "blog_full" ? generationMode : null`. Change to send `generationMode` unconditionally. Note: `target_keyword`, `secondary_keywords`, `target_word_count`, `article_template` correctly stay blog-only and should remain nulled for social.
  - Draft autosave already includes `generationMode` in the `BrainDumpDraft` shape and restore path (lines ~137-190, ~263-267); no change needed, but verify.

- `frontend/components/campaigns/GenerationModeSelector.tsx`
  - Small presentational radio group. `MODES` array holds `label` + `tagline`. Add a `contentType` prop and convert `tagline` to a per-content-type lookup. Styling is Paper Style and must be preserved verbatim.

- `backend/app/services/generation.py`
  - `run_social_only_pipeline` (line ~364) loads the job, campaign, and client BVP, then calls `generate_social_standalone(campaign.brain_dump, brand_voice_profile, _SOCIAL_THINKING_TOKENS)` at line ~400. Add `generation_mode=campaign.generation_mode` to that call. The campaign object is already in scope.
  - `generate_social_only` (line ~248, single-platform roadmap helper) also calls `generate_social_standalone` (line ~272). Leave it on the default; do not add a mode there.
  - There is NO fidelity gate on the social-only path (unlike `run_generation_pipeline`), so the 3-28 AC-6 suppression concern does not apply here.

- `backend/app/integrations/gemini.py` and `backend/app/integrations/anthropic_client.py`
  - `generate_social_standalone(brain_dump, brand_voice_profile, thinking_tokens=0, angle=None, hook=None)` (gemini ~line 611, anthropic ~line 436). Both build the BVP injection then `_SOCIAL_STANDALONE_PROMPT.format(...)`. Add `generation_mode: str | None = None`; when assist, branch to `_SOCIAL_STANDALONE_ASSIST_PROMPT`. Follow exactly how 3-28 added `generation_mode` to `generate_blog` in these same two files (`is_assist = (generation_mode or "generate") == "assist"`).
  - Both have the em-dash post-process (`.replace("—", ...)`) and the 5-key non-empty validator; the assist branch must still satisfy them.

- `backend/app/integrations/generation_prompts.py`
  - `_SOCIAL_STANDALONE_PROMPT` is the shared standalone social prompt (native per-platform composition). Add `_SOCIAL_STANDALONE_ASSIST_PROMPT` beside it. Keep the JSON output contract identical (same 5 keys) so both providers' parsers and validators work unchanged.

### What this story does NOT need (confirmed by reading the code)

- No DB migration and no model change: `generation_mode` already exists on `Campaign` (added in 3-28).
- No schema change: `CampaignCreate.generation_mode` and `CampaignResponse.generation_mode` already exist (`backend/app/schemas/campaign.py`).
- No router change: `campaigns.py` create (line 140), regenerate (line 478), and revoice (line 525) already pass `generation_mode` for all campaign types. Once the frontend stops nulling it, social-only campaigns persist and carry the mode automatically.

### Established precedent to copy exactly

Story `3-28-voice-preservation-and-assist-mode` added assist mode for blog: a new `_BLOG_ASSIST_PROMPT`, a `generation_mode` branch inside `generate_blog` in both providers, and the pipeline passthrough. This story is the same shape applied to the standalone social path: a new `_SOCIAL_STANDALONE_ASSIST_PROMPT`, a `generation_mode` branch inside `generate_social_standalone` in both providers, and a `run_social_only_pipeline` passthrough. Follow the 3-28 diffs.

### UI/UX design (from /web-uiux-architect, Paper Style)

- Placement: the selector is lifted out of the blog-only collapsing block so it is always mounted and stable when toggling Content type. No enter/exit animation is needed (it no longer mounts/unmounts). The existing blog-only block keeps its `grid-rows-[1fr->0fr]` CSS collapse. No Framer Motion introduced (CSS-first rule).
- For social-only, selecting Generate vs Assist reveals no sub-fields (there is no length/template for social), so no additional collapse is needed.
- Copy is content-type-aware (labels constant, taglines swap) so the control reads as the same feature across types.
- Assist changes the brain-dump placeholder to set the "paste your finished post" expectation.
- Accessibility: the radio group semantics (`fieldset`/`legend`/`name="generation_mode"`) are unchanged; the selector is now always in the tab order for social too, which is correct since it is always actionable. The `#FFF1B8` highlight behind `text-ink`/`text-graphite` already passes AA and is reused, not changed.

### Product decisions baked into this story

- Assist-social preserves the author's raw wording and fans it across platforms by trimming/formatting only. It does not invent angles, hooks, CTAs, or hashtags, and does not apply the BVP as a rewrite. This is the deliberate assist contract, matching 3-28's blog assist.
- Scope is the "Social post only" campaign type on the New Campaign form (the `run_social_only_pipeline` path). The Plan My Week / roadmap social path (`generate_social_only`) is intentionally out of scope and unchanged; it has no mode selector.

### Testing standards

- Backend: pytest. Prompt content tests in `backend/tests/test_generation_prompts.py`; provider behavior in `backend/tests/test_gemini_generation.py` and `backend/tests/test_anthropic_generation.py` (keep both in parity); pipeline in `backend/tests/test_generation_service.py`.
- Frontend: Jest + Testing Library (`frontend/__tests__/...`).
- Prompt-level assertions only for LLM output (non-deterministic), per project norms.

### Project Structure Notes

- Additive only: one new prompt constant, one new optional param on an existing function in each provider, one pipeline passthrough, and a frontend re-parenting plus copy. No destructive change, no migration.
- Shared-prompt discipline: the new prompt lives in `generation_prompts.py` so both providers stay in sync (per that module's docstring).

### References

- Direct predecessor: `_bmad-output/implementation-artifacts/3-28-voice-preservation-and-assist-mode.md` (assist mode for blog; Task 4 defers assist-social).
- Deferred-work entry that scopes this story: `_bmad-output/implementation-artifacts/deferred-work.md` (code review of story-3.28, 2026-08-18: "Assist mode still applies the Brand Voice Profile to social posts ... Already scoped as future work by the story's Task 4 ... Revisit when assist-social is picked up.").
- Social-only pipeline: `backend/app/services/generation.py` `run_social_only_pipeline` (~line 364, `generate_social_standalone` call ~line 400) and `generate_social_only` (~line 248).
- Provider standalone social: `backend/app/integrations/gemini.py` (~line 611), `backend/app/integrations/anthropic_client.py` (~line 436).
- Blog assist precedent to mirror: `generate_blog` `generation_mode` branch in `backend/app/integrations/gemini.py` (~line 225-238) and `anthropic_client.py` (~line 72-86); `_BLOG_ASSIST_PROMPT` in `generation_prompts.py`.
- Worker dispatch to the social path: `backend/app/workers/generate.py` (~line 37-40, `campaign_type == "social_only"`).
- Persisted-and-carried mode (no router work needed): `backend/app/routers/campaigns.py` create (line 140), regenerate (line 478), revoice (line 525); `backend/app/schemas/campaign.py` (`generation_mode` fields).
- Frontend form + selector: `frontend/app/(app)/campaigns/new/page.tsx` (selector currently at ~line 614 inside the blog-only block; submit at ~line 293), `frontend/components/campaigns/GenerationModeSelector.tsx`.
- Copy rule: no em-dash or double-hyphen in generated copy or prompts (project memory: no-double-dash-in-copy).

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- GenerationModeSelector lifted out of the blog-only collapsing block; now always mounted for both content types. contentType prop added with per-type taglines.
- Submit payload now sends generationMode unconditionally (was nulled for social_only before).
- Brain-dump textarea placeholder switches to "Paste the post you already wrote..." when assist mode is active.
- _SOCIAL_STANDALONE_ASSIST_PROMPT added to generation_prompts.py with preservation + per-platform-length contract; no composition scaffolding, no BVP rewrite, copy rules enforced.
- generate_social_standalone in both gemini.py and anthropic_client.py extended with generation_mode param; assist branch uses _SOCIAL_STANDALONE_ASSIST_PROMPT, generate branch unchanged. 5-key validator + em-dash strip still run on both paths.
- run_social_only_pipeline passes campaign.generation_mode through to generate_social_standalone; generate_social_only (roadmap path) unchanged.
- No DB migration, schema change, or router change needed (3-28 already persists generation_mode for all campaign types).
- 17 new tests: 9 backend prompt/provider/pipeline tests + 8 frontend component tests. All 236 relevant backend tests pass; 8 new frontend tests pass; pre-existing failures unchanged.

### File List

- `frontend/app/(app)/campaigns/new/page.tsx` (modified)
- `frontend/components/campaigns/GenerationModeSelector.tsx` (modified)
- `frontend/__tests__/components/GenerationModeSelector.test.tsx` (created)
- `backend/app/integrations/generation_prompts.py` (modified)
- `backend/app/integrations/gemini.py` (modified)
- `backend/app/integrations/anthropic_client.py` (modified)
- `backend/app/services/generation.py` (modified)
- `backend/tests/test_generation_prompts.py` (modified)
- `backend/tests/test_gemini_generation.py` (modified)
- `backend/tests/test_anthropic_generation.py` (modified)
- `backend/tests/test_generation_service.py` (modified)

### Review Findings

- [x] [Review][Patch] Weak BVP-rewrite test assertion — `test_does_not_apply_bvp_as_rewrite` second assert `"not" in prompt.lower()` trivially true for any English text [backend/tests/test_generation_prompts.py:621]
- [x] [Review][Patch] Missing None-mode provider tests — no test confirms `generation_mode=None` coerces to generate behavior in Gemini/Anthropic [test_gemini_generation.py, test_anthropic_generation.py]
- [x] [Review][Patch] Missing page-level tests (Task 7 gaps) — no tests for: (a) submit payload has generation_mode for social_only; (b) blog-only block aria-hidden for social_only; (c) placeholder switches on assist mode [frontend/__tests__/app/campaigns/NewCampaignPage.test.tsx]
- [x] [Review][Patch] No em-dash absence assertion on assist prompt body — test only checks instruction text exists, not that prompt itself is clean [backend/tests/test_generation_prompts.py]
- [x] [Review][Patch] Provider assist tests don't assert BVP absent — assist mode skips BVP injection but no test verifies BVP content is excluded from captured prompt [test_gemini_generation.py, test_anthropic_generation.py]
- [x] [Review][Defer] `brain_dump` curly-brace format-injection — `str.format(brain_dump=brain_dump)` crashes on `{unknown}` in user text; pre-existing across all prompt `.format()` call sites — deferred, pre-existing
- [x] [Review][Defer] `angle`+`assist` simultaneous use — angle directive appended to assist prompt if caller supplies both; no current call path reaches this combination — deferred, pre-existing
- [x] [Review][Defer] Double-dash in BVP voice section strings — `"apply to linkedin_post only -- do not apply to x_post"` in generate-mode injection; not touched by this diff — deferred, pre-existing

## Change Log

- 2026-08-25: Story 3.29 implemented — GenerationModeSelector lifted to both content types, mode-aware taglines and placeholder, _SOCIAL_STANDALONE_ASSIST_PROMPT added, generate_social_standalone wired for assist in both providers, run_social_only_pipeline passes generation_mode through. 17 new tests. No migration.
- 2026-08-25: Code review complete — 5 patches applied (weak BVP test assertion fixed, None-mode parity tests added x2 providers, page-level tests added for Task 7 gaps, em-dash clean assertion added, BVP-absent assertion added), 3 deferred, 9 dismissed, marked done.
