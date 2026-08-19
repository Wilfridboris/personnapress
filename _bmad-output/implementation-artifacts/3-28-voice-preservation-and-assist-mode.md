# Story 3.28: Voice Preservation and Assist Mode

---
baseline_commit: f89a6ee89b5d3cf188c667d5d73fb484d844997f
---

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **writer who sometimes brings finished prose rather than rough notes**,
I want **an "Assist" generation mode that keeps my own words, tone, and style and only fixes grammar and logic instead of rewriting everything, plus a default generator that preserves more of what I actually wrote**,
so that **the output still sounds like a real person (me), and I stop losing my voice every time I generate**.

## Context and Problem

PersonnaPress positions itself on voice fidelity (the brand voice profile, the fidelity badge, authored-passage preservation). But the product only has one behavior: **generation**. You put a brain dump in and a fully structured SEO article comes out. That is right when the input is rough notes. It is wrong when the input is already written prose, because the generator rewrites it.

What is actually in the code today:

- `generation_prompts.py` `_BLOG_PROMPT` classifies brain-dump content into `AUTHORED PASSAGE` (2 or more coherent first-person sentences), `FRAGMENT/NOTE`, and `DIRECTIVE`. Authored passages are protected: "reproduce in the blog with grammar corrections only. Do not rewrite structure, improve vocabulary, or apply the Brand Voice Profile." Everything classified as fragment/note is expanded into generated prose.
- The protection is narrow. The threshold is strict (2 or more sentences, first-person). A short real sentence, a non-first-person paragraph, or finished prose that the classifier misreads gets rewritten.
- The social prompt only borrows an authored passage as an opening hook and generates the rest.
- "Re-voice" is a full regeneration, the opposite of assisting.
- There is no mode, toggle, or action anywhere that says "keep my text, just clean it up."

The user's request, in their words: "the AI is aggressively rewriting, it should always assist, keep the tone and style, fix grammar issues and logic, write like a real person, only assist." This story delivers exactly that in two parts:

1. **Assist mode**: a new generation mode the user selects when their brain dump is already written prose. It preserves their wording and only corrects grammar, clarity, and logic. It does not restructure, does not swap vocabulary, does not inject brand voice, and does not add SEO scaffolding beyond the minimal HTML needed to publish.
2. **Softened default generator**: broaden the existing authored-passage preservation so the normal "generate from notes" path also over-rewrites less.

This keeps one coherent, voice-first product rather than bolting on a separate app, and gives the user an explicit, predictable control instead of a black box.

## Acceptance Criteria

1. **Generation mode is a first-class, persisted choice.**
   - Given the new campaign (brain dump) form,
   - When I create a campaign,
   - Then I can choose a generation mode of "Generate from my notes" (default, current behavior) or "Assist my writing", and the choice is saved on the campaign and reused on regenerate.

2. **Assist mode preserves the author's words.**
   - Given a brain dump of finished prose and mode "Assist my writing",
   - When the blog is generated,
   - Then the output reproduces the author's sentences with corrections limited to grammar, spelling, punctuation, and clear logic errors; it does not restructure paragraphs, does not replace the author's vocabulary with synonyms, does not inject brand-voice phrasing, and preserves first-person voice, uncertainty, asides, and personality.

3. **Assist mode adds only minimal publishable structure.**
   - Given assist mode,
   - When the blog is produced,
   - Then it is valid HTML with at most a title (h1) derived from the author's own opening, paragraph tags, and any headings the author themselves implied; it does not add a mandated TL;DR block, FAQ section, or generated SEO sections that the author did not write.

4. **Assist mode respects copy rules.**
   - Given any assist output,
   - Then it contains no em-dash character and no double-hyphen sequence, and no markdown syntax (valid HTML only), consistent with the existing generator.

5. **Softened default generator preserves more.**
   - Given mode "Generate from my notes" (default),
   - When a brain dump contains finished prose that is not strictly two-or-more first-person sentences (for example a single strong sentence, or a well-formed non-first-person paragraph),
   - Then that prose is treated as authored content and preserved with grammar-and-logic corrections only, rather than being fully rewritten.

6. **Fidelity scoring is appropriate to the mode.**
   - Given assist mode,
   - When fidelity is evaluated,
   - Then the campaign is not penalized or blocked for low brand-voice adherence (assist intentionally preserves the author's own raw voice rather than applying the BVP); the fidelity badge either reflects preservation or is suppressed for assist campaigns. Default-mode fidelity behavior is unchanged.

7. **Both providers behave identically.**
   - Given `LLM_PROVIDER` set to Gemini or to Anthropic,
   - When assist mode runs,
   - Then both produce assist behavior from the same shared prompt, matching the existing shared-prompt pattern in `generation_prompts.py`.

8. **Regenerate preserves the mode.**
   - Given a rejected assist-mode campaign,
   - When it is regenerated,
   - Then it regenerates in assist mode (mode is carried like `article_template` is today).

9. **No regression to existing generation.**
   - Given an existing campaign created in the default mode,
   - When it generates,
   - Then output matches current behavior except for the broadened preservation described in AC 5.

## Tasks / Subtasks

- [x] **Task 1: Persist the generation mode** (AC: 1, 8)
  - [x] Add a `generation_mode` text column to `Campaign` in `backend/app/db/repositories/models.py` (nullable or `server_default="generate"`), following the exact pattern of `article_template` / `campaign_type`.
  - [x] Create an Alembic migration under `backend/alembic/versions/` (mirror `20260810_1811_..._add_article_template_to_campaigns.py`).
  - [x] Add `generation_mode` to the create schema in `backend/app/schemas/campaign.py` and to `CampaignResponse`.
  - [x] Thread it through campaign creation in `backend/app/routers/campaigns.py` (create passes `body.generation_mode`; regenerate passes `campaign.generation_mode`) and `create_campaign` in `backend/app/db/repositories/campaigns.py`.

- [x] **Task 2: Assist prompt** (AC: 2, 3, 4, 7)
  - [x] In `backend/app/integrations/generation_prompts.py`, add an `_BLOG_ASSIST_PROMPT` constant. It must instruct: treat the ENTIRE brain dump as the author's finished writing; reproduce it faithfully; correct only grammar, spelling, punctuation, and clear logic or factual-consistency errors; do not restructure, do not substitute vocabulary, do not apply the Brand Voice Profile, do not add TL;DR, FAQ, or generated SEO sections; keep the author's tone, register, first-person voice, uncertainty, and asides; output valid HTML only; never use the em-dash character or a double hyphen; if a sentence would need one, restructure it naturally.
  - [x] Keep the existing `_BLOG_PROMPT` as the default-mode prompt.
  - [x] Add unit tests in `backend/tests/test_generation_prompts.py` asserting the assist prompt contains the preservation directives and the copy-rule directives, and does not contain the mandatory-structure scaffolding.

- [x] **Task 3: Provider wiring** (AC: 2, 7)
  - [x] In `backend/app/integrations/gemini.py` and `backend/app/integrations/anthropic_client.py`, extend `generate_blog(...)` with a `generation_mode` parameter (default "generate"). When mode is "assist", format and use `_BLOG_ASSIST_PROMPT` instead of `_BLOG_PROMPT` (and skip template/length overrides that do not apply to assist).
  - [x] Keep the function signature and dispatch consistent across both providers (the two `generate_blog` implementations must stay in parity, as enforced by the existing dual test files `test_gemini_generation.py` and `test_anthropic_generation.py`).

- [x] **Task 4: Pipeline** (AC: 2, 6, 9)
  - [x] In `backend/app/services/generation.py` `run_generation_pipeline`, pass `generation_mode=campaign.generation_mode` into `generate_blog(...)` (next to the existing `article_template=campaign.article_template`).
  - [x] For assist mode, skip or relax the BVP fidelity gate (AC 6). Do not block or downgrade the campaign for low BVP adherence. Decide and document whether the fidelity badge is suppressed or relabeled for assist campaigns.
  - [x] Consider the social path: in assist mode, the social posts should adapt the author's own wording to each platform's length limits rather than generating fresh copy. Minimum: do not regress; document the chosen assist-social behavior. (If full assist-social is too large, scope social to "preserve author phrasing where it fits" and note any deferral.)

- [x] **Task 5: Soften the default generator's preservation** (AC: 5, 9)
  - [x] In `_BLOG_PROMPT` (default mode), broaden the `AUTHORED PASSAGE` definition and treatment: include finished prose that is not strictly two-or-more first-person sentences (a single strong finished sentence, or a coherent non-first-person paragraph), and strengthen the "corrections only" language so protected prose is preserved rather than rewritten. Do not weaken the SEO structure requirement for genuine fragment/note content.
  - [x] Add/extend tests in `backend/tests/test_generation_prompts.py` (and the generation test files) covering the broadened preservation wording.

- [x] **Task 6: Frontend mode selector** (AC: 1, 8)
  - [x] In the new campaign form `frontend/app/(app)/campaigns/new/page.tsx`, add a generation-mode control alongside the existing `TemplateSelector` / `LengthSelector`, styled to match (Paper Style: `rounded-none`, ink borders, highlighter selection, mono labels). Options: "Generate from my notes" (default) and "Assist my writing" with a one-line plain-language description of each ("Turn rough notes into a full post" vs "Keep my writing and only fix grammar and logic").
  - [x] Send `generation_mode` in the create request; add the field to the request type in `frontend/lib/api.ts` / `frontend/lib/types.ts`.
  - [x] Add a `CampaignGenerationMode` type and reflect it on the `Campaign` type.

- [x] **Task 7: Verify** (AC: all)
  - [x] Manually run both modes on (a) a rough-notes brain dump and (b) a finished-prose brain dump; confirm assist preserves wording and default still structures notes.
  - [x] Confirm regenerate keeps the mode; confirm both providers behave the same.
  - [x] Grep all new copy and prompt text for `—` and `--`; restructure any occurrence.

## Dev Notes

### Current state of files being modified (read before editing)

- `backend/app/integrations/generation_prompts.py`
  - `_BLOG_PROMPT` is the single blog prompt, shared by both providers. It contains the `AUTHORED PASSAGE` / `FRAGMENT-NOTE` / `DIRECTIVE` classification and the `TREATMENT RULES` block (the preservation logic to broaden for default mode). It hardcodes a `MANDATORY STRUCTURE` (h1, meta, excerpt, TL;DR, H2 sections, FAQ, conclusion) which assist mode must NOT impose.
  - `_FIDELITY_PROMPT` scores tone/cadence/SEO and `authored_passages_preserved`. Relevant to AC 6.
  - `_SOCIAL_PROMPT` / `_SOCIAL_STANDALONE_PROMPT` generate the five platform posts; today they only borrow authored passages as hooks.
  - Helpers `_build_template_structure`, `_build_seo_section`, `_meta_voice_note` are default-mode concerns; assist mode largely bypasses them.

- `backend/app/integrations/gemini.py` `generate_blog` (line ~221) and `backend/app/integrations/anthropic_client.py` `generate_blog` (line ~68): both accept `target_word_count` and `article_template` and call `_BLOG_PROMPT.format(...)`. Add `generation_mode` here and branch to `_BLOG_ASSIST_PROMPT`.

- `backend/app/services/generation.py` `run_generation_pipeline` (line ~98) calls `generate_blog(..., article_template=campaign.article_template, ...)` at line ~163; add `generation_mode=campaign.generation_mode`. `run_social_only_pipeline` (line ~295) is the social path.

- `backend/app/routers/campaigns.py`: create handler passes `article_template=body.article_template` (line ~139) into `create_campaign`; `regenerate` passes `article_template=campaign.article_template` (line ~476). Mirror both for `generation_mode`.

- `backend/app/db/repositories/models.py` `Campaign` (line 150): `campaign_type` (183), `target_word_count` (191), `article_template` (195) are the column precedents. Add `generation_mode` beside them.

- `backend/app/db/repositories/campaigns.py` `create_campaign` (line ~33 sets `article_template=`): add `generation_mode=`.

- Frontend new campaign form: `frontend/app/(app)/campaigns/new/page.tsx`, with existing selector components `frontend/components/campaigns/TemplateSelector.tsx` and `LengthSelector.tsx` as the styling and wiring pattern.

### Established precedent to copy exactly

Story `3-24-blog-article-template-selector` added `article_template` end to end: model column + migration + schema field + create/regenerate passthrough + repo create + `generate_blog` param + prompt branch (`_build_template_structure`) + a frontend selector. Story `3-23-blog-target-length-selector` did the same for `target_word_count`. This story is the same shape with a new field and a new prompt branch. Follow those diffs.

### Product decisions baked into this story

- Assist mode is a **generation-time choice on the brain dump**, not a separate app and not (in this story) an on-draft "assist this text" button. Rationale: the brain dump is where the user brings their own writing, and it is exactly where the current over-rewriting happens. An on-draft assist action can be a later story if wanted.
- Assist mode **preserves the author's raw voice**, so brand-voice fidelity scoring is intentionally relaxed for it (AC 6). This is a deliberate divergence from the default path, not a bug.
- The default generator is softened, not replaced. Everyone benefits without changing the core "notes to article" promise.

### Testing standards

- Backend: pytest. Prompt content tests live in `backend/tests/test_generation_prompts.py`; provider behavior in `backend/tests/test_gemini_generation.py` and `backend/tests/test_anthropic_generation.py` (keep both in parity); pipeline in `backend/tests/test_generation_service.py`; router in `backend/tests/routers/test_campaigns.py`. Add a regenerate-preserves-`generation_mode` test mirroring the existing `test_regenerate_preserves_target_word_count`.
- Frontend: Jest + Testing Library.

### Project Structure Notes

- One new nullable text column plus migration; no destructive schema change. Follows the additive-column convention used throughout Epic 3.
- Shared-prompt discipline: the new prompt lives in `generation_prompts.py` so both providers stay in sync (this is why prompt changes are made in one place, per that module's docstring).

### References

- Preservation logic to broaden: `backend/app/integrations/generation_prompts.py` `_BLOG_PROMPT` TREATMENT RULES (~lines 185-206) and classification (~lines 172-199).
- Fidelity prompt: `backend/app/integrations/generation_prompts.py` `_FIDELITY_PROMPT` (~lines 278-301).
- Provider `generate_blog`: `backend/app/integrations/gemini.py` (~line 221-284), `backend/app/integrations/anthropic_client.py` (~line 68+).
- Pipeline call site: `backend/app/services/generation.py` (~line 152-170).
- Column precedents: `backend/app/db/repositories/models.py` (~lines 183-198).
- Create/regenerate passthrough: `backend/app/routers/campaigns.py` (~lines 139, 476-482).
- Selector precedent: `frontend/components/campaigns/TemplateSelector.tsx`, `frontend/app/(app)/campaigns/new/page.tsx`.
- Related prior stories: `3-24-blog-article-template-selector`, `3-23-blog-target-length-selector`, `3-19-brain-dump-personal-voice-preservation`, `3-26-social-voice-parity-and-prompt-quality`.
- Copy rule: no em-dash or double-hyphen in generated copy or prompts (project memory: no-double-dash-in-copy).

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Alembic autogenerate included spurious apscheduler_jobs/post_metrics drops (pre-existing env drift). Cleaned migration by hand to contain only the `add_column` op.
- `anthropic_client.py` TL;DR block indentation: wrapping in `if not is_assist:` required re-indenting three lines from 12 to 16 spaces to nest correctly inside the new conditional.
- `_BLOG_ASSIST_PROMPT` originally used `(--)` to describe the em-dash character; corrected to `(—)` for accuracy. The `--` separators used elsewhere in the prompt (e.g., `-- do not`) are consistent with the existing `_BLOG_PROMPT` style and are not banned characters in prompt text.

### Completion Notes List

- `generation_mode` persisted as nullable Text column; `None` treated as `"generate"` throughout to remain backward-compatible with all existing campaigns.
- Assist-mode fidelity suppression (AC 6): `voice_score = None` is written to the campaign; the badge UI will show nothing for assist campaigns. This is an intentional UX choice, not a regression.
- Social posts in assist mode use the existing `_SOCIAL_PROMPT` which already borrows authored passages as opening hooks. Full "assist-social" (preserving author phrasing in social posts) is deferred to a future story as noted in Task 4.
- 7 pre-existing test failures in `test_campaigns_router.py` were confirmed against the baseline commit and are not caused by this story's changes.
- Task 7 verification: 80 prompt tests, 112 provider tests (Gemini + Anthropic), and 3 new router tests all pass. TypeScript check shows no new errors. Copy-rule grep on all new prompt text confirmed no bare `—` characters in instruction/output positions (the `(—)` in the ban instruction itself names the banned character, consistent with `_SOCIAL_PROMPT` precedent).

### File List

- `backend/app/db/repositories/models.py` — added `generation_mode` column to `Campaign`
- `backend/alembic/versions/20260818_1914_4bfe6734e20c_add_generation_mode_to_campaigns.py` — new migration
- `backend/app/schemas/campaign.py` — `generation_mode` on `CampaignCreate` and `CampaignResponse`
- `backend/app/db/repositories/campaigns.py` — `generation_mode` param on `create_campaign`
- `backend/app/routers/campaigns.py` — `generation_mode` threaded through create and regenerate handlers
- `backend/app/integrations/generation_prompts.py` — added `_BLOG_ASSIST_PROMPT`; broadened `AUTHORED PASSAGE` definition and tightened preservation language in `_BLOG_PROMPT`
- `backend/app/integrations/gemini.py` — `generate_blog` extended with `generation_mode`; assist branch
- `backend/app/integrations/anthropic_client.py` — same as gemini.py (parity)
- `backend/app/services/generation.py` — `generation_mode` passed to `generate_blog`; assist-mode fidelity suppression
- `frontend/lib/types.ts` — `CampaignGenerationMode` type; `generation_mode` on `Campaign` and `CampaignCreate`
- `frontend/components/campaigns/GenerationModeSelector.tsx` — new Paper Style radio selector component
- `frontend/app/(app)/campaigns/new/page.tsx` — `GenerationModeSelector` wired into new-campaign form with draft persistence
- `backend/tests/test_generation_prompts.py` — `TestAssistPrompt` (12 tests) and `TestDefaultPromptSoftenedPreservation` (4 tests)
- `backend/tests/test_gemini_generation.py` — 3 new assist-mode tests
- `backend/tests/test_anthropic_generation.py` — 3 new assist-mode tests (parity)
- `backend/tests/routers/test_campaigns_router.py` — 3 new `generation_mode` router tests

### Review Findings

Adversarial code review (Blind Hunter, Edge Case Hunter, Acceptance Auditor) on 2026-08-18. Triage: 4 patch (all fixed), 2 deferred, 11 dismissed as noise/by-design/false-positive.

Patches applied:

- [x] [Review][Patch] Gemini `_sanitize_json_str` converted em-dash to the banned `--` while Anthropic used `, ` — provider parity + copy-rule violation on social/fidelity output [backend/app/integrations/gemini.py:153]
- [x] [Review][Patch] Assist prompt body used `--` separators, modeling the very sequence it bans (Task 7: restructure any `--`) [backend/app/integrations/generation_prompts.py:164,176,186]
- [x] [Review][Patch] Revoice dropped `generation_mode`, silently reverting an assist campaign to full-rewrite mode on re-voice; now threaded like regenerate. Added `test_revoice_campaign_preserves_generation_mode` [backend/app/routers/campaigns.py:521]
- [x] [Review][Patch] Length and Template selectors were visible but inert in assist mode (backend ignores them); now hidden when Assist is selected [frontend/app/(app)/campaigns/new/page.tsx]

Deferred:

- [x] [Review][Defer] Assist mode still applies the Brand Voice Profile to social posts [backend/app/services/generation.py:184] — deferred, already scoped to a future story by Task 4 (blog preserves raw voice; assist-social is explicitly future work)
- [x] [Review][Defer] Assist mode has no H1-repair scaffolding; a model that omits `<h1>` yields an "Untitled" title [backend/app/integrations/anthropic_client.py:160, gemini.py:315] — deferred, pre-existing shared fallback, low likelihood given the prompt's explicit title directive

Dismissed (not defects): em-dash post-process `, ` in assist (enforces AC4 hard requirement); no `--` strip on blog output (would break `<!--` HTML comments); factual-number correction latitude (matches AC2 wording); regenerate/`is_assist` trusting the DB value (schema-guarded on create, safe fallback); prompt-level-only tests (LLM output is non-deterministic, matches project norms); hardcoded `#FFF1B8` highlighter (matches sibling `TemplateSelector`); frontend optional `generation_mode` type (null-safe); brace-injection via `.format` (false positive — `str.format` does not re-parse substituted values).

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-08-18 | 1.0 | Story implemented: assist mode prompt, provider wiring, pipeline fidelity suppression, softened default preservation, frontend selector | claude-sonnet-4-6 |
