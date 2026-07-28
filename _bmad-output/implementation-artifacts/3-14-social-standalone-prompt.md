---
baseline_commit: 6f2e3f5c741dfb6071251fd4ab62c42d57832797
---

# Story 3.14: Social Standalone Prompt -- Plan My Week Social Post Quality

Status: done

## Story

As a PersonnaPress user generating social posts via Plan My Week,
I want the X and LinkedIn posts to be written as native, standalone social content,
so that posts have proper platform-native hooks and structure instead of blog-teaser language that references a guide that doesn't exist.

## Context & Motivation

**The bug:** `generate_social_only()` (the Plan My Week path) calls `_llm.generate_social()` -- the same function used when a blog post exists. That function's prompt (`_SOCIAL_PROMPT`) is designed to tease a blog: the X instruction says "tease the blog without duplicating it" and passes `blog_title=""`. The result is X posts that end with "Read the full guide -->" pointing at nothing, and LinkedIn posts with one first-person opener but no structure beyond that.

**Three confirmed issues from live output:**

1. **X post:** `"Facebook ads seem complicated until you realize they're not. $7M in revenue later, I'm breaking down the exact 4-step setup that works. Read the full guide -->"` -- "Read the full guide" is a dead CTA with no blog to link to.
2. **LinkedIn post:** Em-dash `—` in `"Not technical complexity—it's confidence."` -- violates the project-wide em-dash ban (present in `_BLOG_PROMPT` but missing from `_SOCIAL_PROMPT`).
3. **LinkedIn CTA:** `"You can too. Just follow the system."` -- motivational filler, not a specific engagement action.

**Fix scope:**

- Add `_SOCIAL_STANDALONE_PROMPT` for the social-only path with proper native-post structure.
- Add `generate_social_standalone()` in both LLM integrations using the new prompt.
- Wire `generate_social_only()` in `generation.py` to call `generate_social_standalone` instead.
- Add em-dash post-processing to `generate_social()` (affects all campaigns -- belt-and-suspenders).
- Raise LinkedIn char ceiling to 2,500 for standalone posts (research: 1,200-3,000 performs best; 2,500 leaves buffer for LLM variance).
- Inject three BVP fields into the standalone prompt that exist in the data model but are currently ignored: `post_structure_template`, `opening_pattern`, `closing_pattern`.

No schema changes. No migration. No frontend changes.

---

## Acceptance Criteria

### AC1 -- `_SOCIAL_STANDALONE_PROMPT` exists with correct X structure

**Given** `_SOCIAL_STANDALONE_PROMPT` in `generation_prompts.py`,
**When** rendered for any brain dump,
**Then** the X post instruction:
- Specifies 70-280 character target
- Describes Hook --> Value --> Proof --> Nudge structure
- Explicitly states: "this is a standalone post -- no 'Read the full guide', no blog link CTA"
- Includes em-dash ban ("no em-dash character (--) anywhere")

### AC2 -- `_SOCIAL_STANDALONE_PROMPT` exists with correct LinkedIn structure

**Given** `_SOCIAL_STANDALONE_PROMPT` in `generation_prompts.py`,
**When** rendered for any brain dump,
**Then** the LinkedIn post instruction:
- Specifies 1,200-2,500 character target
- Lists hook patterns the LLM must choose from: bold data claim, before/after transformation, contrarian one-liner, personal reveal, timeline/result, mistake/pain
- Specifies post structure: hook (lines 1-2) --> re-hook (lines 3-4) --> problem/stakes (3-6 lines with specifics) --> story/insight (5-10 lines) --> steps/framework (3-7 bullets) --> soft CTA (1-2 lines with a specific action, not "thoughts?")
- Includes em-dash ban
- Has no "tease the blog" or "blog title" references

### AC3 -- BVP fields injected into standalone prompt

**Given** a BVP with `post_structure_template`, `opening_pattern`, and/or `closing_pattern` fields,
**When** the standalone prompt is built,
**Then** a `BRAND STRUCTURE HINTS` section is injected into the prompt containing:
- `opening_pattern` mapped to the LinkedIn hook bias (e.g. "bold_claim" --> prefer data/contrarian hooks)
- `closing_pattern` mapped to the CTA style (e.g. "cta" --> use a direct action CTA, "question" --> close with a specific question)
- `post_structure_template` included verbatim as the author's preferred structure guide

**Given** a BVP without these fields,
**When** the standalone prompt is built,
**Then** the `BRAND STRUCTURE HINTS` section is omitted (no empty section injected).

### AC4 -- Em-dash ban added to existing `_SOCIAL_PROMPT`

**Given** the existing `_SOCIAL_PROMPT` in `generation_prompts.py` (used for blog+social campaigns),
**When** any campaign with a blog generates social posts,
**Then** the prompt contains the instruction: "No em-dash character (--) anywhere in either post."

### AC5 -- `generate_social_standalone()` in both LLM integrations

**Given** `backend/app/integrations/anthropic_client.py` and `backend/app/integrations/gemini.py`,
**When** `generate_social_standalone(brain_dump, bvp, thinking_tokens)` is called,
**Then:**
- Uses `_SOCIAL_STANDALONE_PROMPT` (not `_SOCIAL_PROMPT`)
- Returns `{"x_post": str, "linkedin_post": str}` -- same schema as `generate_social()`
- X post: truncated at 280 chars with `…` suffix if over (unchanged from `generate_social`)
- LinkedIn post: truncated at 2,500 chars with `…` suffix if over; warning logged if under 1,200 chars
- Voice brief (`voice_brief`) injected into `linkedin_voice_section` (same pattern as `generate_social`)
- BVP structure hints built via new `_build_standalone_voice_injection()` helper

### AC6 -- `generate_social_only()` calls `generate_social_standalone`

**Given** `backend/app/services/generation.py`, `generate_social_only()` function,
**When** called by the Plan My Week roadmap pipeline,
**Then:**
- Calls `_llm.generate_social_standalone(brain_dump, bvp, _SOCIAL_THINKING_TOKENS)` -- not `_llm.generate_social`
- The `blog_title=""` argument is removed (not a parameter of `generate_social_standalone`)
- All other behaviour (platform field routing, error handling, DB commit) unchanged

### AC7 -- Tests

**Given** the new `generate_social_standalone` function,
**When** tests run,
**Then:**
- Happy path: returns valid `x_post` and `linkedin_post` (both integrations)
- LinkedIn over 2,500 chars is truncated to 2,499 + `…`
- LinkedIn under 1,200 chars logs a warning
- `generate_social_only` service test mocks `generate_social_standalone` (not `generate_social`)
- X post does not contain the string "Read the full guide" (regression test)
- Neither post contains the em-dash character `—` (regression test)

---

## Tasks / Subtasks

### Group A -- `generation_prompts.py` (AC1, AC2, AC3, AC4)

- [x] **A1: Add `_SOCIAL_STANDALONE_PROMPT`**

  ```python
  _SOCIAL_STANDALONE_PROMPT = """You are an expert social media copywriter. Write two native social posts.
  These posts stand alone -- there is no blog article to link to or tease.

  BRAND VOICE PROFILE:
  {bvp_json}
  {linkedin_voice_section}
  {bvp_structure_hints}
  BRAIN DUMP:
  {brain_dump}

  Return ONLY a valid JSON object (no markdown):
  {{
    "x_post": "<X post, 70-280 characters. Structure: Hook (first ~70 chars, stops the scroll) then Value (1 core insight or 2-3 short bullets) then Proof (a number or outcome from the brain dump if available) then Nudge (simple ask: Save this / Reply with X / Drop a comment). This is the complete thought -- no 'Read the full guide', no link CTA, no em-dash character anywhere.>",
    "linkedin_post": "<LinkedIn post, 1200-2500 characters. Use blank lines between each section. Structure must follow this order: (1) HOOK lines 1-2: choose the strongest pattern for this content -- bold data claim (I analyzed N things. Here is the pattern.), before/after transformation (X months ago [pain]. Today [outcome]. Here is what changed.), contrarian one-liner (Everyone says X. Here is why that costs you.), personal reveal (I almost [negative outcome]. The problem was not what you think.), timeline/result (In N days we [result]. Here is exactly what changed.), mistake/pain (Most [audience] do X. Here is the cost.). (2) RE-HOOK lines 3-4: one sharp line clarifying who this is for. (3) PROBLEM/STAKES: 3-6 short lines with concrete specifics -- numbers, budget, time, emotional cost -- pulled from the brain dump. (4) STORY/INSIGHT: 5-10 lines with specific details, named tools, outcomes, or data from the brain dump. (5) STEPS/FRAMEWORK: 3-7 bullets, each a clear action or belief shift, not a vague principle. (6) SOFT CTA: 1-2 lines -- a specific question the reader can answer, a comment trigger ('Comment X and I will send it'), or a DM invite. Never close with 'thoughts?' or 'you can too'. No em-dash character anywhere. No 'Read the full guide' or blog link CTA.>"
  }}
  """
  ```

- [x] **A2: Add `_build_standalone_voice_injection()` helper**

  ```python
  def _build_standalone_voice_injection(bvp: dict) -> str:
      """Build BRAND STRUCTURE HINTS section for standalone social posts.

      Injects BVP fields that are captured during voice extraction but unused
      in the standard social prompt: opening_pattern, closing_pattern,
      post_structure_template.
      Returns empty string when none of these fields are present.
      """
      if not bvp:
          return ""
      hints: list[str] = []

      opening = (bvp.get("opening_pattern") or "").strip()
      opening_map = {
          "question": "question hook (open with a question the audience is already asking)",
          "bold_claim": "bold claim or data hook (open with a specific number or contrarian statement)",
          "anecdote": "personal reveal or before/after hook (open with a micro-story or confession)",
          "stat": "data/numbers hook (open with a statistic or surprising figure)",
          "problem": "mistake/pain hook (open by naming a common mistake or its cost)",
      }
      if opening and opening in opening_map:
          hints.append(f"- LinkedIn hook should lean toward: {opening_map[opening]}")

      closing = (bvp.get("closing_pattern") or "").strip()
      closing_map = {
          "cta": "end with a direct action CTA (comment trigger or DM invite)",
          "question": "end with a specific question the reader can answer in the comments",
          "summary": "end with one crisp sentence that crystallises the main lesson",
          "one_liner": "end with a punchy one-liner that creates a memorable takeaway",
      }
      if closing and closing in closing_map:
          hints.append(f"- LinkedIn CTA should: {closing_map[closing]}")

      structure = (bvp.get("post_structure_template") or "").strip()
      if structure:
          hints.append(f"- Author's preferred post structure: {structure} -- use as guide for section ordering")

      if not hints:
          return ""
      return (
          "\nBRAND STRUCTURE HINTS (from voice profile -- apply to linkedin_post only):\n"
          + "\n".join(hints)
          + "\n"
      )
  ```

- [x] **A3: Add em-dash ban to existing `_SOCIAL_PROMPT`**

  Append this line to the `linkedin_post` instruction inside `_SOCIAL_PROMPT` (after the existing tease instruction):
  ```
  No em-dash character (--) anywhere in either post.
  ```
  Place it inside the JSON schema description for `linkedin_post`, after the last existing sentence.

- [x] **A4: Export new symbols**

  Ensure `_SOCIAL_STANDALONE_PROMPT` and `_build_standalone_voice_injection` are importable (no `__all__` restriction -- follow existing pattern of module-level names).

### Group B -- `anthropic_client.py` (AC4, AC5)

- [x] **B1: Import new symbols**

  Add to existing import from `generation_prompts`:
  ```python
  from app.integrations.generation_prompts import (
      ...
      _SOCIAL_STANDALONE_PROMPT,
      _build_standalone_voice_injection,
  )
  ```

- [x] **B2: Add `generate_social_standalone()`**

  ```python
  async def generate_social_standalone(
      brain_dump: str,
      brand_voice_profile: dict | None,
      thinking_tokens: int = 0,
  ) -> dict:
      """Generate standalone social posts for Plan My Week (no blog exists).

      Uses _SOCIAL_STANDALONE_PROMPT with native-post structure for both
      LinkedIn (1200-2500 chars, hook/structure/CTA) and X (70-280 chars,
      Hook->Value->Proof->Nudge). BVP fields opening_pattern, closing_pattern,
      and post_structure_template are injected as structure hints.
      """
      if brand_voice_profile:
          bvp_without_voice = {k: v for k, v in brand_voice_profile.items() if k != "voice_brief"}
          bvp_json = json.dumps(bvp_without_voice)
      else:
          bvp_json = _DEFAULT_VOICE

      voice_brief = (brand_voice_profile or {}).get("voice_brief") or ""
      linkedin_voice_section = (
          "\nLINKEDIN BRAND VOICE (apply to linkedin_post only -- do not apply to x_post):\n"
          f"{voice_brief}\n"
      ) if voice_brief else ""

      bvp_structure_hints = _build_standalone_voice_injection(brand_voice_profile or {})

      prompt = _SOCIAL_STANDALONE_PROMPT.format(
          bvp_json=bvp_json,
          linkedin_voice_section=linkedin_voice_section,
          bvp_structure_hints=bvp_structure_hints,
          brain_dump=brain_dump,
      )

      raw = _strip_fences((await _call(prompt, max_tokens=1536)).strip())

      try:
          data = json.loads(raw)
      except json.JSONDecodeError as exc:
          logger.error("generate_social_standalone: Anthropic returned invalid JSON: %r", raw[:200])
          raise ValueError(f"generate_social_standalone: Anthropic returned invalid JSON: {exc}") from exc

      for key in ("x_post", "linkedin_post"):
          if key not in data:
              raise ValueError(f"generate_social_standalone: missing key '{key}' in Anthropic response")
          if not isinstance(data[key], str):
              raise ValueError(
                  f"generate_social_standalone: '{key}' must be a string, got {type(data[key]).__name__}"
              )

      if len(data["x_post"]) > 280:
          logger.warning(
              "generate_social_standalone: X post exceeded 280 chars (%d), truncating",
              len(data["x_post"]),
          )
          data["x_post"] = data["x_post"][:279] + "…"

      ln_len = len(data["linkedin_post"])
      if ln_len > 2500:
          logger.warning(
              "generate_social_standalone: LinkedIn post exceeded 2500 chars (%d), truncating",
              ln_len,
          )
          data["linkedin_post"] = data["linkedin_post"][:2499] + "…"
      elif ln_len < 1200:
          logger.warning(
              "generate_social_standalone: LinkedIn post length %d is below expected 1200 chars",
              ln_len,
          )

      return data
  ```

- [x] **B3: Add em-dash post-processing to existing `generate_social()`**

  After the JSON parse in `generate_social()`, add:
  ```python
  data["x_post"] = data["x_post"].replace("—", "--")
  data["linkedin_post"] = data["linkedin_post"].replace("—", "--")
  ```
  Place immediately after the `for key in ("x_post", "linkedin_post"):` validation block.

### Group C -- `gemini.py` (AC4, AC5)

- [x] **C1: Import new symbols** -- same as B1.

- [x] **C2: Add `generate_social_standalone()`** -- mirror B2 exactly, replacing `_call(prompt, max_tokens=1536)` with:
  ```python
  response = await _client.aio.models.generate_content(
      model=_MODEL,
      contents=prompt,
      config=_thinking_config(thinking_tokens),
  )
  raw = _strip_fences(response.text.strip())
  ```

- [x] **C3: Add em-dash post-processing to existing `generate_social()`** -- same as B3.

### Group D -- `generation.py` (AC6)

- [x] **D1: Update `generate_social_only()` to call `generate_social_standalone`**

  Current call (lines 247-254):
  ```python
  social: dict = await _llm_with_retry(
      _llm.generate_social,
      brain_dump,
      "",
      bvp,
      _SOCIAL_THINKING_TOKENS,
  )
  ```

  Replace with:
  ```python
  social: dict = await _llm_with_retry(
      _llm.generate_social_standalone,
      brain_dump,
      bvp,
      _SOCIAL_THINKING_TOKENS,
  )
  ```

  The `""` (empty blog_title) argument is removed -- `generate_social_standalone` does not accept it.

### Group E -- Tests (AC7)

- [x] **E1: `backend/tests/test_anthropic_generation.py`** -- add tests for `generate_social_standalone`:
  - Happy path: returns valid `x_post` and `linkedin_post` with `_SOCIAL_STANDALONE_PROMPT`
  - LinkedIn over 2,500 chars truncated to 2,499 + `…`
  - LinkedIn under 1,200 chars logs a warning (use `caplog`)
  - X post does not contain `"Read the full guide"` (assert `"Read the full guide" not in result["x_post"]`)
  - Neither post contains `"—"` when LLM emits one (post-processing strips it)
  - BVP with `post_structure_template` injects `BRAND STRUCTURE HINTS` section into prompt

- [x] **E2: `backend/tests/test_gemini_generation.py`** -- same tests as E1 for Gemini path.

- [x] **E3: `backend/tests/test_generation_service.py`** -- update `generate_social_only` mock:
  - Change `mock_gemini.generate_social = AsyncMock(...)` to `mock_gemini.generate_social_standalone = AsyncMock(...)` in any test that exercises `generate_social_only()`
  - Verify test still asserts the correct platform field is written to the campaign

---

## Dev Notes

### Why `generate_social_only` not `generate_social`

The key split: `generate_social()` is called with `blog_title` (the blog content just generated). `generate_social_standalone()` has no `blog_title` parameter at all -- its absence is intentional and communicated to the LLM via the prompt framing. The two paths must stay separate; do not merge them via a flag.

### `max_tokens` raised to 1,536 for standalone

Standard social `generate_social()` uses `max_tokens=1024`. A 2,500-character LinkedIn post is ~625 tokens of prose + ~100 tokens of JSON overhead. Raising to 1,536 gives comfortable headroom without unnecessary cost.

### BVP field values to expect

From `gemini.py` `_BVP_PROMPT_TEMPLATE`, these fields are always present (with defaults from `_QUALITATIVE_DEFAULTS` if absent):
- `opening_pattern`: `"question" | "bold_claim" | "anecdote" | "stat" | "problem"` (default: `"bold_claim"`)
- `closing_pattern`: `"cta" | "question" | "summary" | "one_liner" | "none"` (default: `"none"`)
- `post_structure_template`: free text string, e.g. `"hook -- pain -- insight -- example -- CTA"` (default: `""`)

When `closing_pattern == "none"` or `post_structure_template == ""`, omit those hints from the injected section. The `_build_standalone_voice_injection()` helper handles this.

### Em-dash post-processing: replace with `--` not `,`

The blog pipeline replaces `—` with `, ` (`result.replace("—", ", ")`). For social posts, `--` reads more naturally in short-form content. Use `data["x_post"].replace("—", "--")` and same for `linkedin_post`.

### AR-19 compliance

`generation.py` is the sole caller of LLM integration functions. `generate_social_standalone` follows the same pattern: only called via `_llm_with_retry` in `generation.py`. Never import it directly from routers.

### `_SOCIAL_PROMPT` em-dash fix scope

The em-dash ban added to `_SOCIAL_PROMPT` (Group A3) adds a prompt-level instruction. The post-processing added in Groups B3/C3 is the belt-and-suspenders code-level enforcement -- both are needed because the prompt instruction alone does not guarantee compliance.

### Test mock target for `generate_social_only`

Before this story, `test_generation_service.py` mocks `mock_gemini.generate_social`. After D1, `generate_social_only` calls `generate_social_standalone`. Update mocks accordingly:
```python
# Before:
mock_llm.generate_social = AsyncMock(return_value={"x_post": "...", "linkedin_post": "..."})
# After:
mock_llm.generate_social_standalone = AsyncMock(return_value={"x_post": "...", "linkedin_post": "..."})
```

---

## File List

**No new files.**

**Modified files:**
```
backend/app/integrations/generation_prompts.py
backend/app/integrations/anthropic_client.py
backend/app/integrations/gemini.py
backend/app/services/generation.py
backend/tests/test_anthropic_generation.py
backend/tests/test_gemini_generation.py
backend/tests/test_generation_service.py
_bmad-output/implementation-artifacts/sprint-status.yaml
```

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `_SOCIAL_STANDALONE_PROMPT` to `generation_prompts.py` with Hook/Value/Proof/Nudge X structure (70-280 chars) and 6-part LinkedIn structure (1200-2500 chars), both with em-dash ban.
- Added `_build_standalone_voice_injection()` helper that maps `opening_pattern`, `closing_pattern`, and `post_structure_template` BVP fields into a `BRAND STRUCTURE HINTS` prompt section (omitted when all three fields are absent/empty).
- Added em-dash ban (`No em-dash character (—) anywhere in either post.`) to existing `_SOCIAL_PROMPT` for belt-and-suspenders coverage on blog+social campaigns.
- Added `generate_social_standalone()` to both `anthropic_client.py` and `gemini.py`: uses `_SOCIAL_STANDALONE_PROMPT`, max_tokens=1536, truncates LinkedIn at 2,500/warns below 1,200, truncates X at 280, strips `—` → `--` post-processing.
- Added `—` → `--` post-processing to existing `generate_social()` in both integrations.
- Updated `generate_social_only()` in `generation.py` to call `_llm.generate_social_standalone(brain_dump, bvp, _SOCIAL_THINKING_TOKENS)` -- removed the empty `blog_title=""` argument.
- Added 7 tests to `test_anthropic_generation.py` (happy path, truncation, warning, regression, em-dash, BVP hints, standalone prompt).
- Added 7 tests to `test_gemini_generation.py` (same coverage).
- Added 3 tests to `test_generation_service.py` (x platform routing, linkedin routing, `generate_social` not called).
- All 99 directly affected tests pass (99/99). Pre-existing `spacy` import failures in other test suites are unrelated to this story.

### File List

backend/app/integrations/generation_prompts.py
backend/app/integrations/anthropic_client.py
backend/app/integrations/gemini.py
backend/app/services/generation.py
backend/tests/test_anthropic_generation.py
backend/tests/test_gemini_generation.py
backend/tests/test_generation_service.py
_bmad-output/implementation-artifacts/sprint-status.yaml
_bmad-output/implementation-artifacts/3-14-social-standalone-prompt.md

### Review Findings

- [x] [Review][Patch] Tautological "Read the full guide" regression test -- fixture is hardcoded without the phrase so assert is trivially true; captures no regression [backend/tests/test_anthropic_generation.py, backend/tests/test_gemini_generation.py]
- [x] [Review][Patch] Stale docstring in generate_social_only -- says "Calls generate_social" but now calls generate_social_standalone [backend/app/services/generation.py:238]
- [x] [Review][Patch] No test for brand_voice_profile=None path in generate_social_standalone [backend/tests/test_anthropic_generation.py, backend/tests/test_gemini_generation.py]
- [x] [Review][Patch] No test for em-dash stripping added to existing generate_social [backend/tests/test_anthropic_generation.py, backend/tests/test_gemini_generation.py]
- [x] [Review][Patch] No negative test confirming BRAND STRUCTURE HINTS absent when BVP lacks all three structure fields (AC3) [backend/tests/test_anthropic_generation.py, backend/tests/test_gemini_generation.py]
- [x] [Review][Defer] _build_standalone_voice_injection silently drops unknown opening_pattern/closing_pattern enum values with no warning [backend/app/integrations/generation_prompts.py:_build_standalone_voice_injection] -- deferred, pre-existing guard pattern; BVP enum values are controlled

## Change Log

- 2026-07-28: Story 3-14 implemented -- added `_SOCIAL_STANDALONE_PROMPT`, `_build_standalone_voice_injection`, `generate_social_standalone` (Anthropic + Gemini), em-dash post-processing on all social paths, wired `generate_social_only` to standalone path, added 17 new tests (99/99 pass). Marked ready for review.
- 2026-07-28: Code review complete -- 5 patches applied (tautological regression test fixed, stale docstring, 3 missing test cases added), 1 deferred (unknown BVP enum values silently dropped), 15 dismissed. Marked done.
