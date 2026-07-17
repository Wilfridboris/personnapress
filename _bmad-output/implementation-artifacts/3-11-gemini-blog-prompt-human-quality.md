---
baseline_commit: 49bbea2
---

# Story 3.11: Gemini Blog Prompt — Human Content Quality & Naturalness Pass

Status: done

## Story

As a PersonnaPress user,
I want the blog posts generated from my Brain Dump to read like a human expert wrote them from start to finish,
so that the content passes Google's Helpful Content behavioural signals, avoids AI-writing detection patterns, and faithfully mirrors the client's actual voice cadence — not just its average sentence length.

## Context & Motivation

Stories 3-7 and 3-8 resolved seven structural SEO gaps and four E-E-A-T/GEO gaps. The current `_BLOG_PROMPT` is strong on structure and information retention, but has four remaining quality layers that are still missing:

**Layer 1 — AI-detection structural signatures:**
AI detectors (Originality.ai, GPTZero, Copyleaks) and Google's own scaled-content classifiers measure two things with high accuracy: *sentence length variance* (burstiness) and *section symmetry*. The current prompt instructs `avg sentence length {cadence_instruction}` — Gemini interprets this as a target, producing uniform sentence rhythm. Every H2 section follows the identical `H2 → [optional GEO block] → H3 → p` pattern — three or four sections in structural lockstep is a measurable AI fingerprint. The conclusion is hard-coded as `<h2>Key Takeaways</h2>`, which is one of the most recognisable AI/content-mill section headings.

**Layer 2 — Google Helpful Content intent-completion gap:**
Google's Search Ranking system uses aggregated user interaction data in real time. When a user clicks an article then returns to search (a bounce-back), it registers as a failure signal and gradually demotes the page. The current prompt has no instruction to ensure the article leaves zero unanswered questions. A short brain dump can produce structurally valid content that still fails this test.

**Layer 3 — Vague quantifiers:**
Google's Helpful Content self-assessment explicitly asks: "Does the content provide insightful analysis beyond the obvious?" Sentences like "many businesses", "often results in", "can significantly improve" are the opposite of that. They pass the structure checks but fail the substance check. The current prompt has no rule against them.

**Layer 4 — Voice cadence data wasted:**
The BVP cadence JSON contains `variation_pattern` (e.g. `"short punchy sentences followed by explanatory expansion"`) and `paragraph_structure` (e.g. `"2-3 short paragraphs per section"`) — extracted from the client's actual writing. The prompt currently only uses `avg_sentence_length`. The richest part of the voice profile is ignored.

All changes are prompt-text and minor Python extraction changes in `gemini.py` only. No schema, no migration, no frontend.

---

## Acceptance Criteria

### AC 1 — Sentence burstiness instruction

1. **Given** `_BLOG_PROMPT` in `backend/app/integrations/gemini.py`, **When** the REQUIREMENTS section is rendered, **Then** it contains an instruction requiring dramatic sentence-length variation within paragraphs — specifically: mixing short sentences (3-8 words) with longer explanatory sentences (20+ words) in the same paragraph, and a statement that uniform sentence rhythm is a detectable AI writing signal.

---

### AC 2 — Section structural variation

2. **Given** the MANDATORY STRUCTURE block, **When** it specifies the 3-4 main H2 content sections, **Then** it instructs Gemini to use a **different structural approach for each section** — listing at minimum these options: `<ol>` numbered process (no H3), bold claim in `<p><strong>...</strong></p>` before an H3, H3 subheadings with short paragraphs, flowing paragraphs with no H3. The instruction must say: "never use the same structure twice in a row."

---

### AC 3 — Flexible conclusion heading

3. **Given** the MANDATORY STRUCTURE block, **When** the conclusion section is rendered, **Then** the hard-coded `<h2>Key Takeaways</h2>` is replaced with an instruction for Gemini to choose a heading that fits the article's argument and voice — with examples such as "What to Do Next", "My Recommendation", "The Bottom Line on [Topic]". The instruction must explicitly state: **never use "Key Takeaways" or "In Conclusion"**.

4. **Given** the updated REQUIREMENTS section, **When** the BANNED WORDS list is rendered, **Then** "Key Takeaways" and "in conclusion" appear in the banned list (belt-and-suspenders enforcement alongside the structural rule above).

---

### AC 4 — Intent completion rule

5. **Given** the REQUIREMENTS section, **When** rendered, **Then** it contains an instruction that: (a) before writing the FAQ, Gemini must identify the most likely unanswered follow-up question a reader would still have, (b) if not addressed in the body, it must be added as an additional FAQ entry, (c) the reader should not need to search again, (d) "for more information, see..." is forbidden — the answer goes here.

---

### AC 5 — Specificity enforcement

6. **Given** the REQUIREMENTS section, **When** rendered, **Then** it contains an explicit rule banning vague quantifiers — specifically: "many", "several", "some", "most", "often", "significant", "considerable", "various" — unless accompanied by a specific number, timeframe, or qualifier from the brain dump. If the brain dump does not supply the data: omit the claim or hedge it with first-person language ("in my experience", "from what I've seen").

---

### AC 6 — Voice cadence deep application

7. **Given** `generate_blog()` in `gemini.py`, **When** `brand_voice_profile` is provided, **Then** the function extracts `variation_pattern` and `paragraph_structure` from `brand_voice_profile["cadence"]` in addition to `avg_sentence_length`.

8. **Given** the three cadence fields are extracted, **When** the prompt is built, **Then** a single `cadence_instruction` string is passed to the prompt that: (a) always includes the avg sentence length, (b) appends `sentence variation: "{variation_pattern}"` when `variation_pattern` is non-empty, (c) appends `paragraph structure: "{paragraph_structure}"` when `paragraph_structure` is non-empty, (d) ends with a statement to apply all patterns literally in the prose.

9. **Given** `brand_voice_profile` is `None`, **When** the prompt is built, **Then** `cadence_instruction` falls back to `"avg sentence length 15 words"` (no variation or paragraph structure appended).

10. **Given** `brand_voice_profile` is provided but `variation_pattern` and `paragraph_structure` are absent from the cadence dict, **When** `cadence_instruction` is built, **Then** it contains only the avg sentence length sentence — no KeyError is raised.

---

### AC 7 — Paragraph opener variety

11. **Given** the REQUIREMENTS section, **When** rendered, **Then** it contains an instruction to vary how paragraphs begin — permitting openings with a specific example, a number, a named tool, or a conjunction (But, So, Because, And) when continuing from the prior sentence. The instruction must state: "aim for at least two paragraphs in the article that begin with a conjunction."

---

### AC 8 — Contractions tied to brand tone

12. **Given** the REQUIREMENTS section, **When** rendered, **Then** it contains a rule that: if the brand tone list includes "casual", "friendly", "conversational", or "approachable" — use contractions naturally (don't, can't, I've, you'll, it's); if the tone is "formal", "professional", "authoritative", or "corporate" — avoid contractions entirely.

---

### AC 9 — Hedging for unsupported claims

13. **Given** the REQUIREMENTS section, **When** rendered, **Then** it contains a rule that claims not directly supported by specific data in the brain dump must use first-person hedging ("in my experience", "from what I've seen", "based on the above") rather than being stated as universal facts.

---

### AC 10 — Banned words list extended

14. **Given** the BANNED WORDS line in `_BLOG_PROMPT`, **When** rendered, **Then** the following terms are added to the existing list: `it's worth noting`, `it's important to`, `plays a crucial role`, `serves as a reminder`, `in conclusion`, `in essence`, `moving forward`, `game-changer`, `leveraging`, `at the end of the day`, `the reality is`, `needless to say`.

---

### AC 11 — Regression: existing tests updated

15. **Given** the removal of `<h2>Key Takeaways</h2>` from the MANDATORY STRUCTURE, **When** `test_generate_blog_prompt_includes_mandatory_structure` in `test_gemini_generation.py` runs, **Then** the assertion `assert "Key Takeaways" in prompt_text` is **removed** and replaced with assertions that confirm the flexible conclusion instruction is present: check for `"Key Takeaways"` appearing in the BANNED WORDS/banned list context (i.e. the word appears as a banned term), and check that `"In Conclusion"` is also banned.

16. **Given** all other existing tests in `test_gemini_generation.py`, **When** the full test suite runs, **Then** all tests that passed before this story continue to pass. The only test requiring a change is the one in AC 11.

---

### AC 12 — New tests for story-3-11 changes

17. Five new test functions are added to `test_gemini_generation.py` under a `# -- Story 3-11` comment block:

    - `test_generate_blog_prompt_includes_burstiness_instruction` — capture the rendered prompt; assert the text contains a phrase about short sentences and long sentences in the same paragraph (check for "3-8 words" or "20+" or "uniform sentence" as the signal phrase).

    - `test_generate_blog_prompt_includes_section_structural_variation` — capture the rendered prompt; assert it contains "different structural approach" or "different approach for each section" (case-insensitive).

    - `test_generate_blog_prompt_no_key_takeaways_as_mandatory_heading` — capture the rendered prompt; assert `"<h2>Key Takeaways</h2>"` does NOT appear as a mandatory structure element (the word "Key Takeaways" may appear in the banned list, but not as an `<h2>` tag).

    - `test_generate_blog_prompt_includes_intent_completion_rule` — capture the rendered prompt; assert it contains "search again" or "follow-up" (case-insensitive).

    - `test_generate_blog_prompt_applies_bvp_variation_pattern` — call `generate_blog` with `_VALID_BVP` (which has `variation_pattern: "short"` and `paragraph_structure: "3-5 sentences"`); capture prompt; assert `"short"` and `"3-5 sentences"` both appear in the prompt text.

---

## Tasks / Subtasks

### Task 1 — Python: extract cadence fields and build `cadence_instruction` (AC 6)

- [x] 1.1 In `backend/app/integrations/gemini.py`, in `generate_blog()`, find the BVP extraction block (lines ~254-259). After `avg_sentence_length = cadence.get("avg_sentence_length", 15)`, add:
  ```python
  variation_pattern = cadence.get("variation_pattern", "")
  paragraph_structure = cadence.get("paragraph_structure", "")
  cadence_parts = [f"avg sentence length {avg_sentence_length} words"]
  if variation_pattern:
      cadence_parts.append(f'sentence variation: "{variation_pattern}"')
  if paragraph_structure:
      cadence_parts.append(f'paragraph structure: "{paragraph_structure}"')
  cadence_instruction = "; ".join(cadence_parts)
  if variation_pattern or paragraph_structure:
      cadence_instruction += ". Apply all of these patterns literally in the prose."
  ```

- [x] 1.2 In the `else` branch (no BVP, lines ~260-264), replace `avg_sentence_length = 15` with:
  ```python
  cadence_instruction = "avg sentence length 15 words"
  ```
  Remove the standalone `avg_sentence_length = 15` assignment from this branch.

- [x] 1.3 In the `prompt = _BLOG_PROMPT.format(...)` call (line ~268), replace `avg_sentence_length=avg_sentence_length` with `cadence_instruction=cadence_instruction`.

---

### Task 2 — Prompt: update REQUIREMENTS section (AC 1, 4, 5, 7, 8, 9)

- [x] 2.1 In `_BLOG_PROMPT`, find the REQUIREMENTS block. Replace the cadence line:
  ```
  - Match the cadence: avg sentence length {avg_sentence_length} words
  ```
  with:
  ```
  - Match the cadence: {cadence_instruction}
  ```

- [x] 2.2 Add the following new requirement lines to the REQUIREMENTS block. Place them after the existing E-E-A-T and Information Gain rules and before the HTML output rule:
  ```
  - Sentence length must vary dramatically within each paragraph. Mix short punches (3-8 words) with longer explanatory sentences (20+ words) in the same paragraph. Uniform sentence rhythm — every sentence near the same length — is the clearest measurable AI writing signal. Aim for a range of at least 12 words between your shortest and longest sentence within any given paragraph.
  - Vary how paragraphs begin. Not every paragraph should open with its topic sentence. Some may open with a specific example, a concrete number, a named tool or outcome, or a conjunction (But, So, Because, And) when continuing a thought directly from the prior sentence. Aim for at least two paragraphs in the article that begin with a conjunction.
  - Before writing the FAQ section: identify the most likely follow-up question a reader still has after finishing the body. If it is not answered, add it as an additional FAQ entry. A reader who searched for your focus keyword should not need to open another tab. Never write "for more information, see..." -- answer it here.
  - Never write "many", "several", "some", "most", "often", "significant", "considerable", or "various" without attaching a specific number, timeframe, or qualifier from the brain dump. If the brain dump does not supply the data: either omit the claim entirely or hedge it explicitly ("in my experience", "from what I've seen", "your results may vary depending on").
  - Contractions: if the brand tone list includes "casual", "friendly", "conversational", or "approachable" -- use contractions naturally throughout (don't, can't, I've, you'll, it's). If the tone list includes "formal", "professional", "authoritative", or "corporate" -- avoid contractions entirely.
  - When making a claim not directly supported by specific data in the brain dump: use first-person hedging ("in my experience", "from what I've seen", "based on the above") rather than stating it as universal fact. Never assert something is always true when the brain dump only documents a single case.
  ```
  **Critical formatting constraint:** The prompt bans em-dashes. All dashes in the new lines above use `--` (double hyphen), not `—`. Verify the final file contains no `—` characters in the new text.

---

### Task 3 — Prompt: update MANDATORY STRUCTURE (AC 2, 3)

- [x] 3.1 In the MANDATORY STRUCTURE block, find:
  ```
  [Repeat this H2 pattern for each main content section (3 to 4 total, not counting the FAQ and Key Takeaways sections below)]
  ```
  Replace with:
  ```
  [Write 3 to 4 main content H2 sections. VARY THE STRUCTURE of each section -- do not repeat the same H2 to H3 to paragraph pattern every time. Choose a different structural approach for each section. Options: (a) open with a <ol> numbered process (no H3 needed); (b) open with a bold single-sentence claim in <p><strong>...</strong></p> before the first H3; (c) use H3 subheadings with 2-3 short paragraphs each; (d) write as flowing paragraphs with no H3 at all. Never use the same structure twice in a row across the 3-4 sections.]
  ```

- [x] 3.2 Find the conclusion block:
  ```
  <h2>Key Takeaways</h2>
  <p>[Conclusion paragraph that leads with the single most important action the reader should take. Do not restate the intro.]</p>
  ```
  Replace with:
  ```
  <h2>[Conclusion heading chosen to fit this specific article and voice -- e.g. "What to Do Next", "My Recommendation", "The Bottom Line on [Topic]", or any heading that fits naturally. Never use "Key Takeaways" or "In Conclusion".]</h2>
  <p>[Closing paragraph: lead with the single most important action the reader should take. No section recap. End with forward momentum, not a summary.]</p>
  ```

---

### Task 4 — Prompt: extend BANNED WORDS (AC 10, AC 3 belt-and-suspenders)

- [x] 4.1 Find the BANNED WORDS line:
  ```
  BANNED WORDS, do not use anywhere: delve, moreover, testament, comprehensive, furthermore, tapestry, paradigm, bespoke, unlock, supercharge, navigate (as metaphor), em-dash
  ```
  Replace with:
  ```
  BANNED WORDS, do not use anywhere: delve, moreover, testament, comprehensive, furthermore, tapestry, paradigm, bespoke, unlock, supercharge, navigate (as metaphor), em-dash, it's worth noting, it's important to, plays a crucial role, serves as a reminder, Key Takeaways (as heading), in conclusion, in essence, moving forward, game-changer, leveraging, at the end of the day, the reality is, needless to say
  ```

---

### Task 5 — Tests: update existing test and add new tests (AC 11, 12)

- [x] 5.1 In `backend/tests/test_gemini_generation.py`, in `test_generate_blog_prompt_includes_mandatory_structure` (around line 90), remove:
  ```python
  assert "Key Takeaways" in prompt_text
  ```
  Replace with:
  ```python
  assert "Key Takeaways" in prompt_text  # appears as a BANNED term, not as a mandatory heading
  assert "<h2>Key Takeaways</h2>" not in prompt_text
  assert "In Conclusion" in prompt_text or "in conclusion" in prompt_text  # appears in banned list
  ```
  Note: "Key Takeaways" should still appear in the banned-words section of the prompt — confirm the assertion correctly tests that the word exists as a banned term (not as a mandatory heading).

- [x] 5.2 Add the following five new test functions at the bottom of `test_gemini_generation.py` under a `# -- Story 3-11: Human content quality pass` section comment:

  ```python
  # -- Story 3-11: Human content quality pass ──────────────────────────────────

  @pytest.mark.asyncio
  @patch("app.integrations.gemini._client")
  async def test_generate_blog_prompt_includes_burstiness_instruction(mock_client):
      """AC 1: REQUIREMENTS must instruct Gemini to vary sentence lengths dramatically."""
      from app.integrations import gemini

      captured_prompt = []

      async def capture(*args, **kwargs):
          captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
          return _make_response(_VALID_BLOG_HTML)

      mock_client.aio.models.generate_content = capture
      await gemini.generate_blog("My brain dump", _VALID_BVP)

      prompt_text = captured_prompt[0]
      # Check for key signal phrases from the burstiness instruction
      assert "uniform sentence" in prompt_text.lower() or "3-8 words" in prompt_text


  @pytest.mark.asyncio
  @patch("app.integrations.gemini._client")
  async def test_generate_blog_prompt_includes_section_structural_variation(mock_client):
      """AC 2: MANDATORY STRUCTURE must instruct Gemini to vary section structure."""
      from app.integrations import gemini

      captured_prompt = []

      async def capture(*args, **kwargs):
          captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
          return _make_response(_VALID_BLOG_HTML)

      mock_client.aio.models.generate_content = capture
      await gemini.generate_blog("My brain dump", _VALID_BVP)

      prompt_text = captured_prompt[0]
      assert "different structural approach" in prompt_text.lower() or "never use the same structure" in prompt_text.lower()


  @pytest.mark.asyncio
  @patch("app.integrations.gemini._client")
  async def test_generate_blog_prompt_no_key_takeaways_as_mandatory_heading(mock_client):
      """AC 3: <h2>Key Takeaways</h2> must not appear as a mandatory structure element."""
      from app.integrations import gemini

      captured_prompt = []

      async def capture(*args, **kwargs):
          captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
          return _make_response(_VALID_BLOG_HTML)

      mock_client.aio.models.generate_content = capture
      await gemini.generate_blog("My brain dump", _VALID_BVP)

      prompt_text = captured_prompt[0]
      assert "<h2>Key Takeaways</h2>" not in prompt_text
      # The word still appears in the banned list
      assert "Key Takeaways" in prompt_text


  @pytest.mark.asyncio
  @patch("app.integrations.gemini._client")
  async def test_generate_blog_prompt_includes_intent_completion_rule(mock_client):
      """AC 4: REQUIREMENTS must include intent-completion rule (no unanswered follow-ups)."""
      from app.integrations import gemini

      captured_prompt = []

      async def capture(*args, **kwargs):
          captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
          return _make_response(_VALID_BLOG_HTML)

      mock_client.aio.models.generate_content = capture
      await gemini.generate_blog("My brain dump", _VALID_BVP)

      prompt_text = captured_prompt[0]
      assert "search again" in prompt_text.lower() or "follow-up" in prompt_text.lower()


  @pytest.mark.asyncio
  @patch("app.integrations.gemini._client")
  async def test_generate_blog_prompt_applies_bvp_variation_pattern(mock_client):
      """AC 6: variation_pattern and paragraph_structure from BVP cadence must appear in the prompt."""
      from app.integrations import gemini

      captured_prompt = []

      async def capture(*args, **kwargs):
          captured_prompt.append(kwargs.get("contents") or (args[1] if len(args) > 1 else ""))
          return _make_response(_VALID_BLOG_HTML)

      mock_client.aio.models.generate_content = capture
      # _VALID_BVP has variation_pattern: "short" and paragraph_structure: "3-5 sentences"
      await gemini.generate_blog("My brain dump", _VALID_BVP)

      prompt_text = captured_prompt[0]
      assert "short" in prompt_text          # variation_pattern value
      assert "3-5 sentences" in prompt_text  # paragraph_structure value
  ```

---

## Dev Notes

### Files to touch

| File | Change |
|---|---|
| `backend/app/integrations/gemini.py` | `_BLOG_PROMPT` text (Tasks 2, 3, 4) + `generate_blog()` Python extraction logic (Task 1) |
| `backend/tests/test_gemini_generation.py` | Update 1 existing test (Task 5.1) + add 5 new tests (Task 5.2) |

### No other files

No schema changes, no migration, no frontend changes, no new dependencies. `re` and all other imports are unchanged.

### Template variable rename: `avg_sentence_length` → `cadence_instruction`

The `_BLOG_PROMPT` string currently uses `{avg_sentence_length}` as the placeholder. This must be renamed to `{cadence_instruction}` in the template string AND in the `.format()` call. Missing either one will cause a `KeyError` at generation time. The `else` branch that sets `avg_sentence_length = 15` must also be replaced with `cadence_instruction = "avg sentence length 15 words"`.

### Backward compatibility

- BVP profiles already in the database that lack `variation_pattern` or `paragraph_structure` will cause `cadence.get(...)` to return `""` — the `if variation_pattern:` guards mean these are silently skipped. No migration needed.
- BVP profiles that have these fields (all profiles extracted via story 3-8 or later, since the `_BVP_PROMPT_TEMPLATE` already includes the cadence schema) will have these values populated.

### No em-dashes in new prompt text

All new text in `_BLOG_PROMPT` must use `--` (double hyphen) as separator, never `—`. This is a project-wide constraint (commits `ad345ff`, `69faae8`). Verify the final file with a grep for `—` before marking done.

### `test_generate_blog_prompt_includes_mandatory_structure` update rationale

This test currently asserts `"Key Takeaways" in prompt_text`. After this story, the string "Key Takeaways" still appears in the prompt (in the BANNED WORDS list), so the assertion becomes more nuanced: we need to assert the *heading form* `<h2>Key Takeaways</h2>` is absent while the *banned-term reference* `Key Takeaways` is still present. See Task 5.1 for the exact replacement.

### `_VALID_BVP` already has cadence sub-fields

The test fixture `_VALID_BVP` at line 19 already contains `variation_pattern: "short"` and `paragraph_structure: "3-5 sentences"` — no test fixture update needed. The new test `test_generate_blog_prompt_applies_bvp_variation_pattern` uses this existing fixture directly.

### Story lineage

- 3-7: Structural SEO (TL;DR, BLUF, FAQ, banned openers, H2/H3 structure)
- 3-8: GEO & E-E-A-T (first-person retention, information gain, conditional GEO blocks, LinkedIn hook)
- 3-9: Configurable Gemini model via env var
- 3-10: Focus keyword rename + supporting keywords field
- **3-11 (this story):** Human quality pass (burstiness, section variation, flexible conclusion, intent completion, specificity, voice cadence depth, paragraph openers, contractions, hedging, extended banned words)

### References

- `backend/app/integrations/gemini.py:93–148` — `_BLOG_PROMPT` (Tasks 2, 3, 4)
- `backend/app/integrations/gemini.py:254–276` — `generate_blog()` extraction block (Task 1)
- `backend/tests/test_gemini_generation.py:90–110` — test to update (Task 5.1)
- `backend/tests/test_gemini_generation.py:704–756` — end of file; new tests go after this block (Task 5.2)
- No-em-dash constraint: commits `ad345ff`, `69faae8`, `aa3afcc`

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1 (AC 6): Extracted `variation_pattern` and `paragraph_structure` from BVP cadence dict; built `cadence_instruction` string with semicolon-joined parts; replaced `avg_sentence_length` template variable with `cadence_instruction` throughout `generate_blog()` and `_BLOG_PROMPT`.
- Task 2 (AC 1, 4, 5, 7, 8, 9): Added 6 new requirement lines to REQUIREMENTS block — burstiness/sentence variance, paragraph opener variety, intent completion (search again rule), specificity enforcement (vague quantifier ban), contractions by brand tone, first-person hedging for unsupported claims. All use `--` not em-dash.
- Task 3 (AC 2, 3): Replaced H2 repeat instruction with structural variation instruction (4 options, never same twice); replaced hard-coded `<h2>Key Takeaways</h2>` with flexible conclusion heading instruction banning "Key Takeaways" and "In Conclusion".
- Task 4 (AC 10, 3 belt-and-suspenders): Extended BANNED WORDS with 12 additional terms including "Key Takeaways (as heading)", "in conclusion", "leveraging", "game-changer", and others.
- Task 5 (AC 11, 12): Updated `test_generate_blog_prompt_includes_mandatory_structure` — replaced bare `"Key Takeaways" in prompt_text` with nuanced assertions (banned term present, `<h2>` heading absent, "in conclusion" in banned list). Added 5 new Story 3-11 tests — all 50 tests pass.

### File List

- backend/app/integrations/gemini.py
- backend/tests/test_gemini_generation.py

### Review Findings

- [x] [Review][Patch] Weak BVP variation_pattern assertion — `"short" in prompt_text` passes vacuously because "short" already appears in static prompt text; does not verify BVP cadence flows into rendered prompt [backend/tests/test_gemini_generation.py:856]
- [x] [Review][Patch] cadence None guard — `brand_voice_profile.get("cadence", {})` returns None when key exists with null value, causing AttributeError on subsequent `.get()` calls [backend/app/integrations/gemini.py:263]
- [x] [Review][Patch] avg_sentence_length None guard — if cadence key exists with null value, injects "None words" into prompt [backend/app/integrations/gemini.py:264]
- [x] [Review][Patch] Non-string cadence field cast — variation_pattern/paragraph_structure not coerced to str, would embed repr of non-string DB values into prompt [backend/app/integrations/gemini.py:265-266]
- [x] [Review][Patch] Dead assertion in AC 4 test — "search again" never appears in prompt (prompt says "open another tab"); left-hand or-clause is always false [backend/tests/test_gemini_generation.py:313]
- [x] [Review][Defer] Mixed-tone contractions conflict — tone list with both "professional" and "friendly" has no precedence tiebreaker; spec limitation — deferred, pre-existing
- [x] [Review][Defer] Unbounded FAQ intent-completion rule — no cap on additional FAQ entries; spec limitation — deferred, pre-existing
- [x] [Review][Defer] No test for cadence_instruction fallback path (brand_voice_profile=None) — AC 12 spec does not require it — deferred, pre-existing
- [x] [Review][Defer] Banned-words list case-variant coverage — "it is worth noting" not caught; fundamental limitation of literal banned-list approach — deferred, pre-existing
- [x] [Review][Defer] "Apply all of these patterns" suffix conditioned on non-empty variation/structure fields — task spec code block matches implementation; spec wording ambiguous — deferred, pre-existing

## Change Log

- Story 3-11 implemented: human content quality pass (burstiness instruction, section structural variation, flexible conclusion heading, intent-completion rule, vague quantifier ban, contractions by tone, hedging rule, extended banned words, deep BVP cadence application) (Date: 2026-07-17)
- Story 3-11 code review: 5 patches applied (BVP variation_pattern assertion strengthened, cadence None guard, avg_sentence_length None guard, non-string cadence field cast, dead AC 4 test assertion removed), marked done (Date: 2026-07-17)
