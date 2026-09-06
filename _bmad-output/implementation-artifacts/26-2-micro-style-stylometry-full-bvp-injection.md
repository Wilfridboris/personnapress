# Story 26.2: Micro-Style Stylometry and Full BVP Injection

Status: ready-for-dev

## Story

As a writer whose style includes lowercase openers, comma-heavy sentences, and other micro-habits,
I want the system to measure those habits and actually apply every extracted voice field during generation,
so that generated content carries my punctuation and casing fingerprint instead of default LLM style.

## Acceptance Criteria

1. **Given** `compute_stylometric_fields()` in `backend/app/services/stylometry.py`, **When** extended, **Then** it additionally computes: `casing_style` ("standard" | "lowercase_leaning" | "mixed", from the share of sentence-initial lowercase letters), `comma_density` ("light" | "moderate" | "heavy", commas per 100 words), `exclamation_frequency` ("never" | "rare" | "frequent"), `ellipsis_usage` (bool), `parenthetical_usage` ("rare" | "occasional" | "frequent"), and `sentence_length_stdev` (int), with the same never-raise, 50K-cap behavior as the existing metrics.

2. **Given** the seven extracted-but-never-injected qualitative fields (`formality_scale`, `humor_style`, `vocabulary_complexity`, `example_style`, `target_audience`, plus computed `sentence_rhythm`, `paragraph_density`, `contraction_frequency`), **When** `_build_voice_injection()` and `_build_social_universal_rules()` in `generation_prompts.py` build the voice sections, **Then** each field present in the BVP produces a concrete instruction line (e.g. formality_scale 1-2 maps to "casual register, contractions expected"; humor_style "dry" maps to "occasional dry humor, never slapstick"; paragraph_density "airy" maps to "1-2 sentence paragraphs"), and `contraction_frequency` drives the contraction rule directly instead of being inferred from tone keywords.

3. **Given** the new micro-style fields, **When** the voice section is built, **Then** `casing_style="lowercase_leaning"` injects an explicit rule ("this writer often opens sentences in lowercase in social posts; mirror this in social content, keep standard casing in blog headings"), and `comma_density`, `exclamation_frequency`, `ellipsis_usage`, `parenthetical_usage` each map to one instruction line; fields absent from legacy BVPs inject nothing and never raise.

4. **Given** the social prompts (`_SOCIAL_PROMPT`, `_SOCIAL_STANDALONE_PROMPT`), **When** voice signals are injected, **Then** `signature_phrases`, `voice_anchor_sentences`, and `anti_pattern_example` are injected into social generation the same way blog generation already injects them (today they are blog-only).

5. **Given** a BVP refresh or new extraction, **When** stylometry runs, **Then** the new fields are computed and merged following the Story 16.1 independent-update pattern, and the BVP review UI (`ClientDetailTabs` voice tab) renders the new fields read-only in the existing computed-metrics section.

6. **Given** tests in `backend/tests/test_stylometry.py` and prompt tests, **When** run, **Then** they cover lowercase-leaning detection, comma density boundaries, injection lines for each new field, legacy-BVP absence safety, and social-prompt signature-phrase injection for both providers.

## Tasks / Subtasks

- [ ] Task 1: Extend stylometry (AC: 1)
  - [ ] Add the 6 new metrics to `compute_stylometric_fields()` using the existing spaCy doc where possible (sentence iteration already exists for `sentence_length_avg` / `sentence_rhythm`); reuse, do not re-tokenize.
  - [ ] Thresholds: `casing_style` lowercase_leaning if > 30% of sentences start lowercase, mixed if 10-30%, else standard. `comma_density` light < 4, moderate 4-8, heavy > 8 commas per 100 words. `exclamation_frequency` never = 0, rare < 0.5 per 100 words, else frequent. `ellipsis_usage` true if "..." or "…" appears more than once. `parenthetical_usage` rare < 1, occasional 1-3, frequent > 3 pairs per 1000 words.
  - [ ] Preserve invariants: never raise, cap input at 50K chars, work on < 300 words (fields still computed, `low_confidence` already flags it).
- [ ] Task 2: Inject the seven dormant fields (AC: 2)
  - [ ] In `_build_voice_injection()` (`generation_prompts.py:15-104`): add one instruction line per present field. Map every enum value explicitly (no passthrough of raw enum tokens into prose); values outside the known enum inject nothing (the 3-14 review deferred exactly this trap: unknown BVP enum values must be silently dropped, add the guard now).
  - [ ] In `_build_social_universal_rules()` (`generation_prompts.py:123-161`): replace the tone-keyword contraction inference with a direct `contraction_frequency` rule when the field exists; keep tone inference as fallback for legacy BVPs.
  - [ ] `target_audience`: inject as "Write for: {target_audience}" in both blog and social sections when non-empty.
- [ ] Task 3: Inject micro-style fields (AC: 3)
  - [ ] Blog: casing rule applies to body prose only, never headings, H1, or meta description (state this in the instruction line).
  - [ ] Social: casing rule applies fully. Note: `ellipsis_usage` true permits "..." but the em-dash ban stays absolute.
- [ ] Task 4: Social voice signal parity (AC: 4)
  - [ ] Port the 16-6 signal blocks (signature_phrases, voice_anchor_sentences, anti_pattern_example) into `_SOCIAL_PROMPT` and complete them in `_SOCIAL_STANDALONE_PROMPT` (standalone already has phrases + anti-pattern via `_build_standalone_voice_injection()` lines 452-518 but lacks voice_anchor_sentences; linked social has none of the three).
  - [ ] Reuse the 16-6 sanitization exactly: non-list guards, newline stripping, double-quote escaping (these were review patches on 16-6, do not regress them).
- [ ] Task 5: Voice tab UI (AC: 5)
  - [ ] Add the 6 new computed fields to the read-only computed-metrics section of the voice tab in `ClientDetailTabs` (the 16-3 expanded BVP review UI). Follow the existing metric-row markup exactly; labels in plain language ("Casing", "Comma density", "Exclamation marks", "Ellipsis", "Parentheticals", "Sentence variation").
  - [ ] Fields absent (legacy BVP) render nothing, no empty rows, no dashes-as-placeholders.
- [ ] Task 6: Tests (AC: 6)
  - [ ] `test_stylometry.py`: lowercase-leaning vs standard vs mixed boundary cases, comma density at each threshold, exclamation/ellipsis/parenthetical detection, short-text safety, all-new-fields-present shape.
  - [ ] Prompt tests in BOTH provider test files: each new injection line appears when field present, absent when missing, unknown enum value injects nothing, social prompts contain signature phrase / anchor / anti-pattern blocks, contraction rule driven by contraction_frequency.

## Dev Notes

### Why this story exists (evidence, 2026-09-05 code analysis)

- The BVP captures 25 fields; 7 extracted fields are never injected into any prompt: `formality_scale`, `humor_style`, `vocabulary_complexity`, `example_style`, `target_audience`, plus computed `sentence_rhythm` and `paragraph_density`. `contraction_frequency` is computed but only inferred indirectly from tone keywords.
- Capitalization and punctuation habits are not measured at all. A user who writes lowercase-leaning, comma-heavy prose gets standard LLM casing back every time. This is the exact user complaint driving Epic 26.
- Social generation is voice-poorer than blog: `signature_phrases`, `voice_anchor_sentences`, `anti_pattern_example` are blog-only (16-6 scoped them to `_build_voice_injection`), so social posts drift furthest from the user's voice.

### Constraints and guardrails

- Provider parity: `gemini.py` and `anthropic_client.py` share `generation_prompts.py`, so prompt-builder changes land once, but TESTS must exist in both provider test files (established 3-14/3-26 pattern).
- No em-dashes (—) and no double-dashes (--) in any prompt text or UI copy. `ellipsis_usage` never licenses dashes.
- Never let a casing rule touch H1/meta/headings: SEO structure is mandatory per `_build_voice_injection` ("SEO structure is mandatory" preamble). Blog casing rule is body-prose-only.
- The 16-2 defaults (`_QUALITATIVE_DEFAULTS`, `gemini.py:95-109`) mean fields like formality_scale default to 3 and humor_style to "none". Injection should treat DEFAULT values as real signals only when they carry information: formality_scale 3 and humor_style "none" and vocabulary_complexity "plain" produce NO line (they are the no-signal defaults); non-default values produce lines. State this in the mapping table in code.
- No schema migration: all new fields live in the existing `clients.brand_voice_profile` JSONB.
- Do not touch assist-mode prompts (`_BLOG_ASSIST_PROMPT`, `_SOCIAL_STANDALONE_ASSIST_PROMPT`): assist bypasses BVP by design (3-28 AC 6).
- Story 26.4 will restructure per-surface voice application; keep this story's injection lines inside the existing builder functions so 26.4 can partition them. Do not pre-build a per-surface layer here.

### Existing behavior that must not break

- `stylometry.py` invariants: pure local computation, no API calls, never raises, ingestion wraps it in try/except (16-1 review patch). Keep the wrapper working.
- 16-1 refresh semantics: each computed field updates independently without wiping the rest of the BVP.
- Legacy BVPs (3-field: tone, cadence, banned_jargon) must keep generating without errors (16.2 AC 5 regression).
- The em-dash sanitization in both providers replaces — with ", " (3-28 review patch chose comma over the banned "--"); do not alter.
- 16-6 sanitization guards on phrase/anchor injection were review patches; reuse the same helpers rather than duplicating escaping logic in social builders.

### UI/UX design guidance (web-uiux-architect, adapted to Paper Style)

- PersonnaPress is Paper Style, NOT glassmorphism: `--color-paper: #F9F9F6`, `--color-ink: #111111`, `rounded-none`, hard offset shadows (`4px 4px 0px 0px var(--color-ink)`), dot paper texture. Match the existing voice tab rows exactly; no new visual language.
- New metric rows are read-only text, not interactive; no focus states needed, but keep semantic markup (dl/dt/dd or the existing pattern) so screen readers get label-value pairs.
- No emojis; icons only if the existing section uses them, imported from Lucide.
- No motion needed here (static rows); do not add Framer Motion.

### Source tree components to touch

- `backend/app/services/stylometry.py` (UPDATE: new metrics)
- `backend/app/integrations/generation_prompts.py` (UPDATE: `_build_voice_injection` 15-104, `_build_social_universal_rules` 123-161, `_SOCIAL_PROMPT` 341-369, `_SOCIAL_STANDALONE_PROMPT` 371-398, `_build_standalone_voice_injection` 452-518)
- `frontend/components/clients/ClientDetailTabs.tsx` (UPDATE: voice tab computed-metrics section)
- `backend/tests/test_stylometry.py` (UPDATE), both provider prompt test files (UPDATE)

### Testing standards summary

- Backend: pytest; stylometry tests are pure-python (no mocks); prompt tests assert on the built prompt string with a constructed BVP dict, mocking the provider client per existing patterns in the gemini/anthropic test pairs.
- Frontend: vitest + testing-library; assert new labels render when fields present and are absent for legacy BVP fixture.

### Project Structure Notes

- Stylometry stays a pure service in `backend/app/services/`; prompt building stays centralized in `generation_prompts.py` (shared by both providers since 3-12).
- Frontend voice tab lives in `ClientDetailTabs` since the 20-6 Profile & Voice tab merge; there is no separate voice page section for these metrics.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 26, Story 26.2]
- [Source: backend/app/services/stylometry.py:24-107 (existing metrics, invariants)]
- [Source: backend/app/integrations/generation_prompts.py:15-104, 123-161, 452-518 (voice builders)]
- [Source: backend/app/integrations/gemini.py:45-109 (_BVP_PROMPT_TEMPLATE, _QUALITATIVE_DEFAULTS)]
- [Source: _bmad-output/implementation-artifacts/16-6-voice-signal-injection.md (sanitization guards, blog-only scope)]
- [Source: _bmad-output/project-context.md (no em-dash rule)]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
