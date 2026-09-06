# Story 26.4: Fidelity Repair Loop and Per-Mode Voice Differentiation

Status: ready-for-dev

## Story

As a user,
I want a failing voice score to trigger an automatic repair pass and each generation mode to apply my voice differently,
so that low-fidelity output fixes itself before I see it and blog, social, and template modes stop sounding identical.

## Acceptance Criteria

1. **Given** `check_fidelity()` returns `tone_score < 7` or `cadence_score < 6` or `jargon_violations > 0`, **When** the generation pipeline (`services/generation.py`) receives the score, **Then** it makes exactly ONE repair call per campaign passing the failing dimensions and the voice section, re-scores the repaired output, keeps whichever version scored higher, and stores both scores in `voice_score` (fields `initial` and `final`); the repair adds no user-visible wait state beyond the existing generation job.

2. **Given** the repair loop, **When** it runs, **Then** total added latency is bounded (one repair + one re-score maximum, no recursion), a log line records repaired dimensions, and a `repaired: true` flag in `voice_score` lets the frontend badge show "voice-tuned" instead of a failing badge.

3. **Given** the four article templates and blog vs social generation share one `voice_brief`, **When** prompts are built, **Then** a per-surface voice application layer differentiates them: blog uses the full voice section; LinkedIn keeps structure signals but compresses the brief to register + rhythm; X uses only cadence, casing, and banned words with an explicit "punchier than the blog voice" rule; Instagram and Facebook use the warm-register subset; Threads keeps the existing raw-register rule plus casing. Each surface's voice section is verifiably different in the built prompt (asserted in tests).

4. **Given** the `thought-leadership` and `how-to` templates, **When** blog generation runs, **Then** the voice application includes one template-specific line (thought-leadership amplifies opinion markers and first-person stance; how-to amplifies imperative mood and concrete steps) so template choice changes voice application, not just structure.

5. **Given** assist mode, **When** any of this story's changes run, **Then** assist behavior is untouched: no BVP injection, no repair loop, `voice_score` stays null.

6. **Given** tests, **When** run, **Then** they cover: repair triggered on each failing dimension, better-score-wins selection, single-repair bound, `repaired` flag persistence, per-surface prompt differentiation assertions, template voice lines, and assist-mode invariance.

## Tasks / Subtasks

- [ ] Task 1: Repair pass in the pipeline (AC: 1, 2)
  - [ ] New `repair_blog_voice(html, failing_dimensions, voice_section, samples)` in both providers: prompt states the specific failures ("tone scored 5/10 against this profile", "2 banned words found: ...") and instructs a minimal rewrite preserving structure (H1, H2s, FAQ, TL;DR, links, authored passages) while fixing only the failing dimensions. Returns full HTML.
  - [ ] In `run_generation_pipeline` (`services/generation.py:98-233`): after fidelity result arrives, if failing, call repair once, re-run `check_fidelity` on the repaired HTML, pick the higher-scoring version (compare tone_score + cadence_score, tiebreak fewer jargon_violations), store `voice_score = {**final_flat_fields, "initial": {...}, "final": {...}, "repaired": true/false}`.
  - [ ] CRITICAL sequencing: since 3-25, fidelity and social generation run in parallel via `asyncio.gather`. Repair the BLOG only, after the gather resolves; social posts were generated from the original blog and remain as-is (social has its own voice rules; a repaired blog body does not invalidate them). Do not serialize fidelity before social; do not regenerate social after repair.
  - [ ] Failure safety: repair call raising or timing out falls back to the original HTML and original score with `repaired: false`; the pipeline never fails a campaign because of repair.
- [ ] Task 2: voice_score backward compatibility (AC: 1, 2)
  - [ ] Keep the existing flat keys (`tone_score`, `cadence_score`, `jargon_violations`, seo_* fields, `tags`) at the top level holding FINAL values so the existing badge and any consumers keep working unchanged; `initial`, `final`, `repaired` are additive keys.
  - [ ] Frontend `VoiceFidelityBadge` (story 4-1): when `repaired` is true and the final score passes, show a "Voice-tuned" variant; when `repaired` is true and still failing, keep the existing failing badge. Campaigns with legacy flat-only `voice_score` render exactly as today.
- [ ] Task 3: Per-surface voice application layer (AC: 3)
  - [ ] New `build_voice_for_surface(bvp, surface)` in `generation_prompts.py` with surfaces: `blog`, `linkedin`, `x`, `instagram`, `facebook`, `threads`. Internally reuses the existing builders; each surface selects a documented subset:
    - blog: full voice section (current `_build_voice_injection` output).
    - linkedin: compressed brief (first 2 sentences of voice_brief) + structure signals (opening/closing pattern, post_structure_template) + cadence + banned words.
    - x: cadence + casing + banned words + fixed line "Punchier and more compressed than the blog voice; shorter sentences than the profile average."
    - instagram/facebook: warm-register subset: compressed brief + contraction rule forced toward casual + cadence + banned words.
    - threads: existing raw-register platform rule + casing + banned words (no brief).
  - [ ] Rewire `_SOCIAL_PROMPT` and `_SOCIAL_STANDALONE_PROMPT` platform sections to consume `build_voice_for_surface` instead of the shared whole-brief injection (today LinkedIn/IG/FB get the full `voice_brief` verbatim and Threads gets its first 2 sentences; X gets none).
  - [ ] Each surface's built section must differ from every other surface's for the same BVP (test asserts pairwise inequality).
- [ ] Task 4: Template voice lines (AC: 4)
  - [ ] In the blog voice section, append exactly one line for `thought-leadership` ("Lead with opinion and first-person stance; take positions plainly") and `how-to` ("Prefer imperative mood and concrete numbered steps"); `standard` and `listicle` add nothing.
- [ ] Task 5: Assist invariance (AC: 5)
  - [ ] Assert no code path adds repair, surfaces, or template lines to assist prompts; `voice_score` stays null for assist campaigns (both blog and social assist).
- [ ] Task 6: Tests (AC: 6)
  - [ ] Pipeline tests: repair fires on each failing dimension independently; does not fire on passing scores; better-score-wins both directions; single call bound (mock call counts); repair exception falls back cleanly; `repaired` flag and `initial`/`final` persisted; flat keys hold final values.
  - [ ] Prompt tests (both providers): pairwise surface inequality, X punchier line, LinkedIn compressed brief is exactly 2 sentences, template lines present/absent per template, assist untouched.
  - [ ] Frontend: badge voice-tuned variant, legacy flat voice_score rendering, failing-after-repair state.

## Dev Notes

### Why this story exists (evidence, 2026-09-05 code analysis)

- `check_fidelity()` (`gemini.py:343-451`, `anthropic_client.py:184-284`) scores tone/cadence/jargon and stores `campaign.voice_score` (`models.py:174-176`) but NOTHING consumes the score: no retry, no repair, no publication gate. A failing badge is shown to the user with no recourse except manual regeneration.
- Every surface shares the same `voice_brief` prose: LinkedIn, Instagram, Facebook get it verbatim, Threads gets its first 2 sentences, blog gets it in full. Templates (3-24) change only structure. This is why "every mode sounds the same".

### Constraints and guardrails

- Latency budget: generation is already a 2-10 minute job. One repair + one rescore adds roughly 30-60s worst case; acceptable inside the job, but NEVER loop. Hard bound of one repair per campaign.
- The repair prompt must preserve: H1, meta description, H2/H3 structure, FAQ, TL;DR, embedded links and their rel attributes, authored passages from the brain dump (3-19 preservation), and the excerpt/meta fields promoted to Campaign columns. State each explicitly in the repair prompt.
- No em-dashes or double-dashes in the repair prompt or badge copy. Repair output goes through the same em-dash sanitization as generate (replace — with ", ").
- Provider parity: repair function and tests in both providers.
- 26.2 dependency: if 26.2 has landed, `build_voice_for_surface` partitions the enriched field set (casing rules travel to social surfaces). If not landed, partition the current fields; write the surface layer so new injection lines slot into a surface map, not hardcoded strings scattered per platform.
- 26.3 dependency: pass stored samples into the repair and rescore calls when available (same parameter the fidelity prompt gained in 26.3); if 26.3 is not landed, omit.
- Do not gate publication on score; repair is best-effort, approval stays human.

### Existing behavior that must not break

- 3-25 parallelization: `asyncio.gather` for fidelity + social must remain; repair happens strictly after the gather. Do not reintroduce serial latency.
- Roadmap pipeline (`run_social_only_pipeline`, 20-x): social-only campaigns have NO fidelity check today; this story does not add one (blog repair only). Assert social_only campaigns unaffected.
- Re-voice flow (16-5) writes new HTML and re-scores; it must tolerate the new voice_score shape (it writes flat fields; additive keys make old writers compatible, verify no strict-schema validation rejects extras).
- Badge display logic (tone>=7, cadence>=6, jargon==0) unchanged; it now reads final values from the same flat keys.

### UI/UX design guidance (web-uiux-architect, adapted to Paper Style)

- "Voice-tuned" badge variant: same badge component as 4-1, Paper Style (rounded-none, ink border), Lucide `Wand2` or `SlidersHorizontal` icon with `aria-hidden="true"` and text label "Voice-tuned" (icon never alone). Tooltip or title text: "This draft was automatically adjusted to match your voice profile." No emojis, no exclamation marks, no em-dashes.
- The variant is informational, not interactive; if rendered inside a button/tooltip pattern, keep the existing focus-visible ring idiom (`focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1`).
- No motion beyond existing badge behavior; CSS transitions only if any.

### Source tree components to touch

- `backend/app/services/generation.py` (UPDATE: repair orchestration ~98-233)
- `backend/app/integrations/gemini.py`, `backend/app/integrations/anthropic_client.py` (UPDATE: repair_blog_voice, rescore reuse)
- `backend/app/integrations/generation_prompts.py` (UPDATE: build_voice_for_surface, repair prompt, template lines, social prompt rewiring)
- `frontend/components/campaigns/VoiceFidelityBadge` (UPDATE: voice-tuned variant; locate the badge component from story 4-1, it may live inside the approval panel component tree)
- Tests: generation pipeline test file, both provider test files, frontend badge tests

### Testing standards summary

- Backend: pytest; mock both provider clients; count repair/rescore calls; simulate gather ordering with async test patterns already used in 3-25 tests.
- Frontend: vitest; badge fixtures for legacy flat, repaired-passing, repaired-failing shapes.

### Project Structure Notes

- The surface layer lives in `generation_prompts.py` (shared by providers since 3-12); providers only pass a surface name. Keep providers free of prompt text.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 26, Story 26.4]
- [Source: backend/app/integrations/gemini.py:343-451; anthropic_client.py:184-284 (check_fidelity)]
- [Source: backend/app/services/generation.py:98-233 (pipeline, 3-25 asyncio.gather)]
- [Source: backend/app/db/repositories/models.py:174-176 (voice_score JSONB)]
- [Source: _bmad-output/implementation-artifacts/3-25-generation-performance-resilience-ux.md (parallel fidelity+social)]
- [Source: _bmad-output/project-context.md (no em-dash rule)]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
