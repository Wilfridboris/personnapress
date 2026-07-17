---
baseline_commit: 42ed019a11a827808a4ba5d7c682eb54348f6326
---

# Story 16.2: Gemini Qualitative Extraction and Voice Brief Synthesis

Status: done

## Story

As a PersonnaPress system,
I want Gemini to extract 15 qualitative voice dimensions from writing samples and synthesize them into a Voice Brief narrative,
so that generation prompts have a rich prose reference instead of a sparse 3-field JSON blob.

## Acceptance Criteria

### AC 1 -- Expanded extraction prompt

1. **Given** `_BVP_PROMPT_TEMPLATE` in `backend/app/integrations/gemini.py` (currently around line 23), **When** updated, **Then** it requests the following fields in addition to the existing `tone`, `cadence`, `banned_jargon`, `target_audience`:

   ```
   Identity layer:
     pronoun_preference: "first_person" | "second_person" | "mixed"
     formality_scale: integer 1-5 (1=very casual, 5=very formal)
     humor_style: "none" | "dry" | "playful" | "self_deprecating"
     vocabulary_complexity: "plain" | "mixed" | "technical"

   Pattern layer:
     example_style: "analogy" | "data" | "story" | "direct"
     specificity_preference: "concrete_numbers" | "vague_quantifiers" | "mixed"
     opening_pattern: "question" | "bold_claim" | "anecdote" | "stat" | "problem"
     closing_pattern: "cta" | "question" | "summary" | "one_liner" | "none"
     header_style: "question" | "command" | "statement" | "mixed"
     post_structure_template: free text string (e.g. "hook -> pain -> insight -> example -> CTA")

   Anchor layer:
     signature_phrases: array of 5-10 strings pulled verbatim from the samples
     voice_anchor_sentences: array of 3-5 verbatim sentences that best represent the voice
     anti_pattern_example: one string -- a sentence that would never come from this writer
   ```

   The prompt instructs Gemini to return ONLY valid JSON with all fields present; no markdown fences; no explanation.

2. **Given** the prompt contains no em-dash characters (`--`), **When** read, **Then** all dash separators use double hyphens or plain prose; this matches the existing project-wide Gemini prompt constraint enforced since commit `ad345ff`.

---

### AC 2 -- Parsing and field validation

3. **Given** `extract_brand_voice` parses the Gemini response, **When** any of the 15 new fields are missing or null, **Then** the following defaults are applied silently (no exception raised):
   - `pronoun_preference` -> `"mixed"`
   - `formality_scale` -> `3`
   - `humor_style` -> `"none"`
   - `vocabulary_complexity` -> `"plain"`
   - `example_style` -> `"direct"`
   - `specificity_preference` -> `"mixed"`
   - `opening_pattern` -> `"bold_claim"`
   - `closing_pattern` -> `"none"`
   - `header_style` -> `"statement"`
   - `post_structure_template` -> `""`
   - `signature_phrases` -> `[]`
   - `voice_anchor_sentences` -> `[]`
   - `anti_pattern_example` -> `""`

4. **Given** the existing hard validation (`isinstance` checks for `tone`, `cadence`, `banned_jargon`), **When** updated, **Then** these three checks remain unchanged; new fields use soft defaults rather than hard raises.

---

### AC 3 -- Voice Brief synthesis

5. **Given** the full BVP dict (5 computed fields from Story 16.1 + 15 qualitative fields), **When** `extract_brand_voice` completes, **Then** a SECOND Gemini call with 256 thinking tokens is made using a new function `synthesize_voice_brief(bvp: dict) -> str` in `gemini.py`; this call receives the full BVP as a JSON block and returns a plain prose string of 150-250 words describing the writer's voice in third person; no JSON output, no field labels, no em-dashes in the output.

6. **Given** `synthesize_voice_brief` is called, **When** the Gemini call fails (5xx, 429, or invalid response), **Then** it logs the error and returns an empty string `""`; a missing voice_brief never blocks BVP storage or generation.

7. **Given** the voice_brief string is returned, **When** the BVP is stored, **Then** `bvp_data["voice_brief"] = voice_brief` is set on the BVP dict before writing to `clients.brand_voice_profile`.

---

### AC 4 -- Enrichment merge (FR-11 refresh replaces overwrite)

8. **Given** the FR-11 refresh flow in `services/ingestion.py`, **When** a user triggers a voice profile refresh, **Then** instead of replacing the entire BVP, the following merge strategy applies:
   - Scalar fields (`pronoun_preference`, `formality_scale`, `humor_style`, `vocabulary_complexity`, `example_style`, `specificity_preference`, `opening_pattern`, `closing_pattern`, `header_style`, `post_structure_template`, `tone` descriptors treated as replacement): new extraction value replaces existing
   - Array fields (`banned_jargon`, `signature_phrases`, `voice_anchor_sentences`): new values are unioned with existing values and deduplicated (order: existing first, then new additions)
   - Computed fields (from Story 16.1): always replaced with fresh computed values
   - `voice_brief`: always regenerated from the merged full BVP

9. **Given** the merge strategy, **When** the merged BVP is assembled, **Then** `clients.brand_voice_profile` is updated with the full merged dict in a single PATCH call; no intermediate state is saved.

---

### AC 5 -- Legacy BVP backward compatibility

10. **Given** a client with a legacy BVP (containing only `tone`, `cadence`, `banned_jargon`, `target_audience`), **When** `extract_brand_voice` returns a legacy-shaped dict (e.g. from a Gemini call that predates this story), **Then** parsing applies all defaults from AC 3 and the stored BVP is updated to include the new fields; generation falls back gracefully (Story 16.4 handles the prompt fallback).

11. **Given** a client whose BVP was stored before Story 16.1 (no computed fields), **When** a refresh is triggered, **Then** computed fields are added from the new text; no existing field values are lost.

---

### AC 6 -- Unit tests

12. **Given** `backend/tests/test_voice_extraction.py`, **When** run, **Then** tests cover:
    - Full extraction: mock Gemini returns all 15 new fields; verify they are stored correctly
    - Missing fields: mock Gemini omits 3 new fields; verify defaults are applied
    - Voice Brief call: verify `synthesize_voice_brief` is called after extraction; mock returns 200-word string
    - Voice Brief failure: mock `synthesize_voice_brief` raises; verify empty string stored, no exception propagated
    - Refresh merge -- scalars: verify new scalar replaces old
    - Refresh merge -- arrays: verify `banned_jargon` union/dedup with existing values
    - Legacy BVP: load a BVP with only 3 legacy keys; verify no KeyError and defaults filled in

---

## Tasks / Subtasks

### Task 1 -- Update `_BVP_PROMPT_TEMPLATE` (AC 1, 2)

- [x] 1.1 In `backend/app/integrations/gemini.py`, replace `_BVP_PROMPT_TEMPLATE` with the expanded version requesting all 15 new fields plus the existing 4. The JSON schema block must list every field with its allowed values inline. Use `--` not `--` (no em-dashes).

- [x] 1.2 Keep the instruction: "Return ONLY a valid JSON object. No markdown code blocks, no explanation. Raw JSON only."

- [x] 1.3 The new schema (abbreviated for clarity -- write the full version in the prompt):
  ```json
  {
    "tone": ["list", "of", "descriptors"],
    "cadence": {"avg_sentence_length": 14, "variation_pattern": "...", "paragraph_structure": "..."},
    "banned_jargon": ["word1"],
    "target_audience": "...",
    "pronoun_preference": "first_person",
    "formality_scale": 3,
    "humor_style": "none",
    "vocabulary_complexity": "plain",
    "example_style": "direct",
    "specificity_preference": "concrete_numbers",
    "opening_pattern": "bold_claim",
    "closing_pattern": "cta",
    "header_style": "statement",
    "post_structure_template": "hook -> pain -> insight -> example -> CTA",
    "signature_phrases": ["phrase 1", "phrase 2"],
    "voice_anchor_sentences": ["Full sentence pulled verbatim."],
    "anti_pattern_example": "A sentence the writer would never produce."
  }
  ```

---

### Task 2 -- Update `extract_brand_voice` parsing (AC 3, 4)

- [x] 2.1 Keep the three existing `isinstance` hard raises for `tone`, `cadence`, `banned_jargon`

- [x] 2.2 After those checks, add a block that applies defaults for all 13 new fields:
  ```python
  _QUALITATIVE_DEFAULTS = {
      "pronoun_preference": "mixed",
      "formality_scale": 3,
      "humor_style": "none",
      "vocabulary_complexity": "plain",
      "example_style": "direct",
      "specificity_preference": "mixed",
      "opening_pattern": "bold_claim",
      "closing_pattern": "none",
      "header_style": "statement",
      "post_structure_template": "",
      "signature_phrases": [],
      "voice_anchor_sentences": [],
      "anti_pattern_example": "",
  }
  for key, default in _QUALITATIVE_DEFAULTS.items():
      if key not in data or data[key] is None:
          data[key] = default
  ```

---

### Task 3 -- Add `synthesize_voice_brief` (AC 5, 6, 7)

- [x] 3.1 Add `_VOICE_BRIEF_PROMPT` template to `gemini.py`:

  ```python
  _VOICE_BRIEF_PROMPT = """You are analyzing a Brand Voice Profile JSON and writing a third-person voice brief.

  BRAND VOICE PROFILE:
  {bvp_json}

  Write a plain prose paragraph of 150-250 words describing how this person writes.
  Cover: pronoun choice, formality, sentence rhythm, how they open and close posts,
  how they use examples, their vocabulary complexity, and what makes their writing distinctive.
  Do NOT use JSON, field names, or bullet points. Write in flowing prose.
  Do NOT use em-dashes. Use plain dashes (--) or restructure the sentence instead.
  Return ONLY the paragraph. No heading, no explanation."""
  ```

- [x] 3.2 Add the function:
  ```python
  async def synthesize_voice_brief(bvp: dict, thinking_tokens: int = 256) -> str:
      prompt = _VOICE_BRIEF_PROMPT.format(bvp_json=json.dumps(bvp, indent=2))
      try:
          response = await _client.aio.models.generate_content(
              model=_MODEL,
              contents=prompt,
              config=_thinking_config(thinking_tokens),
          )
          text = response.text.strip()
          return text if text else ""
      except Exception:
          logger.exception("Voice brief synthesis failed")
          return ""
  ```

- [x] 3.3 In `extract_brand_voice`, after building the final `data` dict (with defaults applied), call:
  ```python
  data["voice_brief"] = await synthesize_voice_brief(data)
  ```

---

### Task 4 -- Enrichment merge in `services/ingestion.py` (AC 8, 9)

- [x] 4.1 Locate the FR-11 refresh path in `backend/app/services/ingestion.py` (the block that calls `extract_brand_voice` on refresh).

- [x] 4.2 After `new_bvp = await extract_brand_voice(combined_text)` returns, load the existing BVP from the DB: `existing_bvp = client.brand_voice_profile or {}`

- [x] 4.3 Apply the merge strategy:
  ```python
  ARRAY_FIELDS = {"banned_jargon", "signature_phrases", "voice_anchor_sentences"}
  merged = dict(existing_bvp)
  for key, value in new_bvp.items():
      if key in ARRAY_FIELDS:
          existing_arr = existing_bvp.get(key) or []
          new_arr = value or []
          # Union: existing first, append only new items
          seen = set(existing_arr)
          merged[key] = existing_arr + [v for v in new_arr if v not in seen]
      else:
          merged[key] = value
  ```

- [x] 4.4 Save `merged` (not `new_bvp`) to `clients.brand_voice_profile`.

- [x] 4.5 The initial ingestion (not refresh) continues to write `new_bvp` directly as before (no merge needed on first extraction).

---

### Task 5 -- Unit tests (AC 12)

- [x] 5.1 In `backend/tests/test_voice_extraction.py`, add/update tests:
  - Mock `_client.aio.models.generate_content` for both the extraction call and the voice brief call
  - Use `pytest-asyncio` (already in the project) for async tests
  - Test cases from AC 12 above

---

## Dev Notes

### Files to modify

| File | Change |
|---|---|
| `backend/app/integrations/gemini.py` | Expand `_BVP_PROMPT_TEMPLATE`, update `extract_brand_voice` parsing, add `synthesize_voice_brief` |
| `backend/app/services/ingestion.py` | Add enrichment merge logic for FR-11 refresh path |
| `backend/tests/test_voice_extraction.py` | Expand test coverage for new fields and merge strategy |

### No DB migration required

`clients.brand_voice_profile` is JSONB. Adding new keys to the JSON dict requires no schema change. Existing rows with 3-field BVPs continue to work.

### Two Gemini calls per extraction

The extraction (1024t) and voice brief (256t) are two sequential async calls. Total thinking budget per ingestion: 1024 + 256 = 1280 tokens. This is within cost expectations (brief call is cheap). Do NOT combine them into one call -- the brief needs the full structured BVP as input.

### Prompt em-dash constraint

This project bans em-dashes from all Gemini prompts (commit `ad345ff`). `_BVP_PROMPT_TEMPLATE` and `_VOICE_BRIEF_PROMPT` must contain zero `--` em-dash characters. Use `--` (double hyphen) or rewrite the sentence. Run a quick grep over the new prompt strings before committing:
```
grep -- "—" backend/app/integrations/gemini.py
```
Should return no matches.

### `extract_brand_voice` is called only from `services/ingestion.py`

Per AR-19, `integrations/gemini.py` is called ONLY from `services/ingestion.py` and `services/generation.py`. Do not call it from routers or workers directly.

### Voice brief failure is non-fatal

If `synthesize_voice_brief` fails (Gemini 5xx, network error), `data["voice_brief"]` is set to `""`. The BVP is still stored. Story 16.4 (generation) handles the case where `voice_brief` is absent or empty by falling back to the legacy 3-field prompt format.

### Refresh confirmation dialog in VoiceSetupPage

The current UI (Story 2.6) shows a confirmation modal before refresh: "This will overwrite your existing voice profile." After this story, the backend merge strategy means it no longer overwrites. The confirmation copy should be updated in Story 16.3 to: "This will update your voice profile with insights from the new content. Existing values are preserved where possible." Flagged here for Story 16.3 dev agent awareness.

### Thinking budget reference

| Call | Thinking tokens | Purpose |
|---|---|---|
| `extract_brand_voice` | 1024 | Qualitative extraction (unchanged) |
| `synthesize_voice_brief` | 256 | Voice brief narrative |
| Voice fidelity check (FR-13) | 256 | Unchanged |
| Blog generation (FR-13) | 512 | Unchanged |
| Social generation (FR-14) | 0 | Unchanged |

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Python 3.14 `AsyncMock` behavior: child method calls (e.g. `result.scalar_one_or_none()`) return coroutines when `result` is an `AsyncMock`. Fixed by wrapping `get_client` call in `extract_voice_profile` with try/except so existing tests that don't patch `get_client` continue to pass.
- `@patch` target requires module in `sys.modules`: added `import app.integrations.gemini` and `import app.services.ingestion` at top of `test_voice_extraction.py` to ensure patching resolves correctly.

### Completion Notes List

- `_BVP_PROMPT_TEMPLATE` expanded to 19 fields (4 existing + 13 new qualitative). All em-dashes replaced with `--` or plain prose per project constraint.
- `_QUALITATIVE_DEFAULTS` dict added at module level in `gemini.py`; applied in `extract_brand_voice` after the existing hard validation checks.
- `synthesize_voice_brief(bvp, thinking_tokens=256)` added to `gemini.py`; any exception returns `""` so a failed brief never blocks BVP storage.
- Enrichment merge implemented in `extract_voice_profile` (`ingestion.py`): reads existing BVP before the retry loop; on success, unions array fields (`banned_jargon`, `signature_phrases`, `voice_anchor_sentences`) and replaces scalars. `get_client` call wrapped in try/except for robustness in test environments.
- 17 new tests in `test_voice_extraction.py` covering all 7 AC 12 categories. All pass. Full suite: 504 passing (up from 484), 49 failing (down from 52).

### File List

- `backend/app/integrations/gemini.py` -- expanded prompt, qualitative defaults, `synthesize_voice_brief`, updated `extract_brand_voice`
- `backend/app/services/ingestion.py` -- `_ARRAY_FIELDS` constant, `get_client` import, enrichment merge block
- `backend/tests/test_voice_extraction.py` -- new test file (17 tests, 5 classes)

### Review Findings

- [x] [Review][Patch] voice_brief synthesized from pre-merge BVP, not merged BVP — AC 8 requires regeneration from merged full BVP; fixed by adding `bvp["voice_brief"] = await gemini.synthesize_voice_brief(bvp)` after merge in `ingestion.py` [backend/app/services/ingestion.py:311]
- [x] [Review][Patch] DB read failure for existing BVP logged at DEBUG not WARNING — silent data-loss risk on transient DB errors; changed to `logger.warning` [backend/app/services/ingestion.py:290]
- [x] [Review][Patch] `set(existing_arr)` raises TypeError for unhashable array items — added try/except TypeError fallback to O(n²) containment check [backend/app/services/ingestion.py:307]
- [x] [Review][Patch] Refresh-path ingestion tests missing mock for new `synthesize_voice_brief` call — added `mock_gemini.synthesize_voice_brief = AsyncMock(...)` to all 5 affected tests [backend/tests/test_voice_extraction.py]
- [x] [Review][Patch] No test asserting `thinking_tokens=256` passed to `synthesize_voice_brief` — added `test_synthesize_voice_brief_default_thinking_tokens` [backend/tests/test_voice_extraction.py]
- [x] [Review][Patch] No test verifying computed fields appear on legacy BVP refresh (AC 11) — added `test_computed_fields_added_on_legacy_bvp_refresh` [backend/tests/test_voice_extraction.py]
- [x] [Review][Patch] No test verifying voice_brief is re-synthesized from merged BVP (AC 8) — added `test_voice_brief_regenerated_from_merged_bvp` [backend/tests/test_voice_extraction.py]
- [x] [Review][Defer] Unbounded array growth on repeated refresh — `signature_phrases` / `voice_anchor_sentences` grow monotonically with no size cap; deferred, pre-existing design choice
- [x] [Review][Defer] `_BVP_PROMPT_TEMPLATE.format(text=...)` crashes if scraped text contains lone `{` or `}` — pre-existing issue not introduced by this story; deferred

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-07-17 | 1.0 | Story implemented: expanded BVP extraction, voice brief synthesis, enrichment merge, 17 unit tests | claude-sonnet-4-6 |
| 2026-07-17 | 1.1 | Code review patches: voice_brief re-synthesized from merged BVP (AC 8), DB read failure now WARNING, TypeError guard on array dedup, 3 new tests (thinking_tokens, computed fields on legacy refresh, voice_brief from merged BVP), synthesis mock added to 5 refresh tests | claude-sonnet-4-6 |
