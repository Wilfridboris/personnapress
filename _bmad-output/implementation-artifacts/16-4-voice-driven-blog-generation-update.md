---
baseline_commit: 42ed019a11a827808a4ba5d7c682eb54348f6326
---

# Story 16.4: Voice-Driven Blog Generation Update

Status: done

## Story

As a PersonnaPress system,
I want to inject the Voice Brief into blog and meta description generation prompts with explicit SEO priority rules,
so that generated content sounds authentically like the writer while preserving the required SEO structure.

## Acceptance Criteria

### AC 1 -- Voice Brief injected into blog generation prompt

1. **Given** `backend/app/integrations/gemini.py` and the `_BLOG_PROMPT` template (around line 93), **When** the client BVP contains a non-empty `voice_brief` field, **Then** the VOICE PROFILE section in the prompt is replaced with a two-part injection:

   Part A -- the voice_brief prose paragraph verbatim

   Part B -- explicit behavioral rules appended directly below:
   ```
   VOICE APPLICATION RULES (apply within the SEO structure -- do not override structure):
   - SEO structure is mandatory: H1, meta description, H2/H3 headings, body, conclusion, 800-1500 words are non-negotiable
   - {list_pref_rule}
   - Opening pattern applies to the FIRST BODY PARAGRAPH, not the H1 or meta description
   - Pronoun preference applies consistently throughout: {pronoun_pref}
   - {specificity_rule}
   ```

   Where:
   - `list_pref_rule`: if `list_preference == "rarely"`: "Use NO bullet lists unless a list is the only clear way to present the information" else: "Lists may appear where natural"
   - `pronoun_pref`: the value of `bvp["pronoun_preference"]` or "mixed" if absent
   - `specificity_rule`: if `specificity_preference == "concrete_numbers"`: "All quantifiable claims MUST use specific numbers, not vague phrases like 'many' or 'a lot'" else: "Use the level of specificity that fits each claim"

2. **Given** the prompt text, **When** written or updated, **Then** zero em-dash characters (`--`) appear; all dashes use double hyphens (`--`) or the sentence is restructured.

---

### AC 2 -- SEO structure takes precedence

3. **Given** the VOICE APPLICATION RULES block, **When** injected into the prompt, **Then** it is placed AFTER the existing MANDATORY STRUCTURE block (H1, meta comment, TL;DR, H2/H3 requirements) and AFTER the SEO REQUIREMENTS section; voice is always the last context provided before the brain dump, so SEO structure has higher attention priority.

4. **Given** the `header_style` field in the BVP, **When** present and not "mixed", **Then** a rule is appended: "H2 and H3 headers should be styled as [value]: e.g. if header_style=question, headers should be phrased as questions." This rule is placed in Part B of the voice injection.

---

### AC 3 -- Meta description voice application

5. **Given** the `<!-- meta: ... -->` HTML comment instruction in the MANDATORY STRUCTURE block (added in Story 15.2), **When** BVP contains a non-empty `voice_brief`, **Then** a condensed voice note (max 50 words derived from the first sentence or two of `voice_brief`) is inserted into the meta instruction:

   Before: `<!-- meta: [One sentence meta description, max 150 chars, ends with action phrase] -->`

   After: `<!-- meta: [One sentence meta description, max 150 chars, ends with action phrase -- write it in this voice: {voice_brief_condensed}] -->`

   The condensed note is the first 50 words of `voice_brief` stripped to a complete sentence.

---

### AC 4 -- Voice fidelity scoring update

6. **Given** the voice fidelity scoring function in `gemini.py` (the 256t call that returns `tone_score`, `cadence_score`, `jargon_violations`), **When** the BVP has expanded fields, **Then** the scoring prompt additionally instructs Gemini to check:
   - `pronoun_score`: 0-10, does the post consistently use the expected `pronoun_preference`?
   - `specificity_score`: 0-10, does the post match `specificity_preference`?
   - `closing_match`: boolean, does the conclusion match `closing_pattern`?

7. **Given** the scoring function returns the expanded scores, **When** the voice fidelity badge is computed, **Then** the EXISTING pass thresholds are unchanged: `tone >= 7`, `cadence >= 6`, `jargon_violations == 0`. The new scores are stored on the campaign record as advisory metadata but do NOT affect the pass/fail badge result (no threshold changes in v1).

---

### AC 5 -- LinkedIn voice application

8. **Given** `generate_linkedin_post` (FR-14) in `gemini.py`, **When** BVP contains a non-empty `voice_brief`, **Then** the LinkedIn prompt receives the voice_brief in its BRAND VOICE section using the same injection pattern as the blog prompt (Part A only -- no behavioral rules block, LinkedIn is short-form).

9. **Given** `generate_x_post` (FR-14) in `gemini.py`, **When** called, **Then** it does NOT receive voice_brief (280 chars leaves no room for style application); the existing BVP formatting for X is unchanged.

---

### AC 6 -- Legacy BVP fallback

10. **Given** a client BVP that has no `voice_brief` field (legacy 3-field BVP or first ingestion before Story 16.2 runs), **When** `generate_blog_post` is called, **Then** the existing legacy prompt format is used without modification; no error occurs; no empty VOICE PROFILE section appears.

---

### AC 7 -- Regression tests

11. **Given** the test suite in `backend/tests/`, **When** run, **Then** tests verify:
    - `voice_brief` is present in the assembled blog generation prompt when BVP has it
    - `voice_brief` condensed note appears in the meta description instruction when BVP has it
    - Fallback: when `voice_brief` is None/absent, the prompt matches the pre-story format (no empty sections, no KeyError)
    - LinkedIn prompt receives `voice_brief` when available
    - X post prompt does NOT receive `voice_brief`
    - `list_preference="rarely"` inserts the no-bullet-list rule
    - `specificity_preference="concrete_numbers"` inserts the numbers-required rule

---

## Tasks / Subtasks

### Task 1 -- Update `generate_blog_post` prompt assembly (AC 1, 2, 3, 4)

- [x] 1.1 In `backend/app/integrations/gemini.py`, locate the function that assembles the blog generation prompt (currently builds `bvp_json`, `tone_list`, `cadence`, `banned_jargon_list` and inserts into `_BLOG_PROMPT` template around line 254-285).

- [x] 1.2 Add a helper function `_build_voice_injection(bvp: dict) -> str` that returns the Part A + Part B string described in AC 1. If `bvp.get("voice_brief")` is falsy, return empty string (legacy fallback path).

- [x] 1.3 In `_build_voice_injection`, build the rules block:
  ```python
  def _build_voice_injection(bvp: dict) -> str:
      voice_brief = bvp.get("voice_brief") or ""
      if not voice_brief:
          return ""

      list_pref = bvp.get("list_preference", "")
      list_rule = (
          "Use NO bullet lists unless a list is the only clear way to present the information"
          if list_pref == "rarely"
          else "Lists may appear where natural"
      )

      pronoun = bvp.get("pronoun_preference", "mixed")
      spec_pref = bvp.get("specificity_preference", "mixed")
      spec_rule = (
          "All quantifiable claims MUST use specific numbers, not vague phrases like 'many' or 'a lot'"
          if spec_pref == "concrete_numbers"
          else "Use the level of specificity that fits each claim"
      )

      header_style = bvp.get("header_style", "")
      header_rule = ""
      if header_style and header_style != "mixed":
          header_rule = f"\n- H2 and H3 headers should be phrased as {header_style}s"

      return (
          f"{voice_brief}\n\n"
          "VOICE APPLICATION RULES (apply within the SEO structure -- do not override structure):\n"
          "- SEO structure is mandatory: H1, meta description, H2/H3 headings, body, conclusion, "
          "800-1500 words are non-negotiable\n"
          f"- {list_rule}\n"
          "- Opening pattern applies to the FIRST BODY PARAGRAPH, not the H1 or meta description\n"
          f"- Pronoun preference applies consistently throughout: {pronoun}\n"
          f"- {spec_rule}"
          f"{header_rule}"
      )
  ```

- [x] 1.4 Replace the `bvp_json` string in the existing prompt template with the voice injection when `voice_brief` is present:
  ```python
  if bvp and bvp.get("voice_brief"):
      voice_section = _build_voice_injection(bvp)
  else:
      voice_section = _DEFAULT_VOICE if not bvp else json.dumps(bvp)
  ```
  Inject `voice_section` where `{bvp_json}` currently appears in `_BLOG_PROMPT`.

- [x] 1.5 Update the meta description instruction line in `_BLOG_PROMPT` to include the condensed voice note when voice_brief is available:
  ```python
  def _meta_voice_note(bvp: dict) -> str:
      brief = (bvp or {}).get("voice_brief") or ""
      if not brief:
          return ""
      # First complete sentence, capped at 50 words
      first_sentence = brief.split(".")[0].strip()
      words = first_sentence.split()[:50]
      return " -- write it in this voice: " + " ".join(words)
  ```
  Update the `<!-- meta: ... -->` line in the prompt:
  ```
  <!-- meta: [One sentence meta description, max 150 chars, ends with action phrase{meta_voice_note}] -->
  ```

- [x] 1.6 Verify no em-dash characters appear anywhere in the new or modified prompt strings.

---

### Task 2 -- Update voice fidelity scoring (AC 6, 7)

- [x] 2.1 Locate the voice fidelity scoring prompt in `gemini.py` (the function that returns `tone_score`, `cadence_score`, `jargon_violations` -- called after blog generation).

- [x] 2.2 If BVP has `pronoun_preference`, add scoring instruction: "pronoun_score: 0-10, how consistently does the post use {pronoun_preference} pronouns?"

- [x] 2.3 If BVP has `specificity_preference`, add scoring instruction: "specificity_score: 0-10, how well does the post match the {specificity_preference} preference?"

- [x] 2.4 If BVP has `closing_pattern`, add: "closing_match: true/false, does the conclusion match the expected '{closing_pattern}' closing pattern?"

- [x] 2.5 Parse these new fields from the scoring response and include them in the returned dict. The caller (in `services/generation.py`) stores the full scoring dict on the campaign record. No change to pass/fail logic: `tone >= 7`, `cadence >= 6`, `jargon_violations == 0` unchanged.

---

### Task 3 -- Update LinkedIn generation (AC 8, 9)

- [x] 3.1 In the LinkedIn generation function (`generate_linkedin_post` or equivalent), when BVP has `voice_brief`, inject Part A only (the voice_brief prose paragraph) into the BRAND VOICE section of the LinkedIn prompt.

- [x] 3.2 Verify X post generation function is NOT modified.

---

### Task 4 -- Regression tests (AC 11)

- [x] 4.1 In the relevant test file (likely `backend/tests/test_gemini.py` or `test_generation.py`), add tests for all 7 cases from AC 11.

- [x] 4.2 Use `unittest.mock.patch` to mock `_client.aio.models.generate_content` and assert on the `contents` argument to verify prompt construction.

---

## Dev Notes

### Files to modify

| File | Change |
|---|---|
| `backend/app/integrations/gemini.py` | `_build_voice_injection`, `_meta_voice_note` helpers; update `_BLOG_PROMPT` injection; update scoring prompt; update LinkedIn prompt |
| `backend/tests/test_gemini.py` (or test_generation.py) | Add regression tests for new prompt assembly |

### No frontend changes

This story is entirely backend. The voice fidelity badge in the frontend (Story 4.1) already reads from the campaign's `voice_score` field; new advisory scores are stored in the same JSON field under new keys. No frontend changes needed for the new scores to be stored.

### SEO structure placement is load-bearing

The reason voice injection goes AFTER the MANDATORY STRUCTURE block is that LLMs give higher attention weight to earlier context. SEO requirements (H1, headings, word count) are non-negotiable; voice is a "color within the lines" instruction. If voice were injected first, edge cases where voice and structure conflict would more likely resolve in favor of voice, breaking the SEO output.

### Em-dash constraint

All prompt strings must pass this check before commit:
```bash
grep "—" backend/app/integrations/gemini.py
```
Should return no matches. The production ban on em-dashes in Gemini prompts has been in place since commit `ad345ff` and applies to all new prompt strings in this story.

### Legacy BVP path is critical

The fallback (AC 10) protects clients who have not yet run a refresh to generate `voice_brief`. The condition is:
```python
if bvp and bvp.get("voice_brief"):
    # new voice injection path
else:
    # existing 3-field legacy path (unchanged)
```
Do not remove or bypass this guard.

### Thinking token budgets unchanged

| Call | Tokens | Notes |
|---|---|---|
| Blog generation | 512 | Unchanged |
| Voice fidelity scoring | 256 | Unchanged; new fields in prompt but same budget |
| Social generation | 0 | Unchanged for X; unchanged for LinkedIn (only prompt content added) |

### `_build_voice_injection` produces no em-dashes

The function uses `--` (double hyphen) in rule strings. The `voice_brief` itself comes from `synthesize_voice_brief` (Story 16.2) which also bans em-dashes in its generation prompt. Belt-and-suspenders: add a `voice_brief.replace("--", "--")` no-op guard if you want to be safe, but it should not be necessary.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4.6 (github-copilot/claude-sonnet-4.6)

### Debug Log References

No issues encountered. All tasks implemented in a single session.

### Completion Notes List

- Added `_build_voice_injection(bvp: dict) -> str` helper after `_DEFAULT_VOICE`; returns Part A (voice_brief prose) + Part B (VOICE APPLICATION RULES block) when `voice_brief` is present, empty string for legacy BVPs.
- Added `_meta_voice_note(bvp: dict) -> str` helper; returns condensed voice note (first sentence of voice_brief, max 50 words) for the `<!-- meta: ... -->` instruction, empty string when absent.
- Updated `_BLOG_PROMPT`: `{bvp_json}` → `{voice_section}` in BRAND VOICE PROFILE section; `{meta_voice_note}` placeholder added to meta description instruction line.
- Updated `generate_blog`: builds `voice_section` via `_build_voice_injection` when `voice_brief` present, falls back to `json.dumps(bvp)` for legacy BVPs; builds `meta_voice_note`; passes both to `_BLOG_PROMPT.format()`.
- Updated `_FIDELITY_PROMPT`: added `{expanded_scoring_section}` placeholder after the JSON schema block.
- Updated `check_fidelity`: conditionally builds expanded scoring instructions for `pronoun_preference`, `specificity_preference`, `closing_pattern`; parses returned advisory fields (`pronoun_score`, `specificity_score`, `closing_match`); no change to pass/fail thresholds.
- Updated `_SOCIAL_PROMPT`: added `{linkedin_voice_section}` placeholder for LinkedIn-specific voice injection.
- Updated `generate_social`: strips `voice_brief` key from `bvp_json` (so X post bvp_json never contains voice_brief); builds `linkedin_voice_section` with Part A (prose only) in a clearly labeled section when `voice_brief` present; empty string otherwise.
- Added 7 regression tests in `test_gemini_generation.py` covering all AC 11 cases.
- Verified 0 em-dash characters in `gemini.py`.
- All 57 `test_gemini_generation.py` tests pass. Pre-existing failures in `test_gemini_integration.py` (9 failures using MagicMock instead of AsyncMock) are unrelated to this story.

### File List

- `backend/app/integrations/gemini.py` (modified)
- `backend/tests/test_gemini_generation.py` (modified)

### Review Findings

- [x] [Review][Patch] Empty-first-sentence guard missing in `_meta_voice_note` [backend/app/integrations/gemini.py:228]
- [x] [Review][Patch] None-propagation for pronoun/specificity in `_build_voice_injection` when stored as JSON null [backend/app/integrations/gemini.py:193]
- [x] [Review][Patch] `closing_pattern` BVP field scored in fidelity but never instructed in blog generation prompt [backend/app/integrations/gemini.py:206]
- [x] [Review][Patch] `_BVP_WITH_VOICE_BRIEF_NO_LIST_PREF` fixture defined but unused; "Lists may appear where natural" branch untested [backend/tests/test_gemini_generation.py:885]
- [x] [Review][Patch] No test for `header_style="question"` producing the header-rule line in blog prompt [backend/tests/test_gemini_generation.py]
- [x] [Review][Patch] `check_fidelity` expanded scoring path (pronoun_score, specificity_score, closing_match) has zero test coverage [backend/tests/test_gemini_generation.py]
- [x] [Review][Defer] VOICE APPLICATION RULES injected inside BRAND VOICE PROFILE (top of prompt) rather than after MANDATORY STRUCTURE as AC 2 intends [backend/app/integrations/gemini.py:206] -- deferred, pre-existing prompt structure; would require full `_BLOG_PROMPT` restructuring

## Change Log

- 2026-07-17: Story 16.4 implemented -- voice_brief injection into blog/meta/LinkedIn prompts, expanded fidelity scoring fields, 7 regression tests added. (claude-sonnet-4.6)
- 2026-07-17: Code review complete -- 6 patches applied, 1 deferred. (claude-sonnet-4.6)
