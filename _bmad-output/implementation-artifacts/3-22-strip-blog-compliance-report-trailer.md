---
baseline_commit: 9e74d1e
depends_on: 3-12-anthropic-content-generation-provider
---

# Story 3.22: Strip Blog Compliance Report Trailer

Status: done

## Story

As a PersonnaPress user reading a generated blog post,
I want the blog HTML to contain only article content,
so that the self-verification compliance block some models append never leaks into the saved article.

## Context & Motivation

Some LLM responses (observed on both Gemini and Anthropic) append a self-verification report
after the closing HTML tag. Example of what leaks into the article:

```
--- Word count: 1,147 words  Primary keyword placement: H1 ✓ | First 100 words ✓ | H2 section ✓ |
Conclusion ✓  Signature phrases woven in: "Stop Boring Your Audience" (conclusion heading) | ...
Authored passage: Opens H2 section as required ✓  Sentence variation: Short (3-8 words) mixed with
long (20+ words) throughout ✓  Active voice: All sentences active ✓  Contractions: Natural
throughout (doesn't, can't, you're, isn't, don't, they'd) ✓  ...
```

This is the model "showing its work" -- it runs its internal compliance checklist and then
outputs the result as visible text instead of keeping it internal.

A fix was implemented in commit `7820803` and then reverted by `9e74d1e` without explanation.
This story re-applies that fix with one addition: a prompt-level instruction telling the model
not to output the compliance block at all. The post-processing stripper stays as a safety net for
models that ignore the instruction.

---

## Acceptance Criteria

### AC 1 -- Prompt-level suppression in `_BLOG_PROMPT`

**Given** the `_BLOG_PROMPT` constant in `backend/app/integrations/generation_prompts.py`,
**When** the story is implemented,
**Then** the final line (or a clearly terminal position) of the prompt body contains the
instruction:
> "Output ONLY the HTML above. Do NOT append any word count, compliance summary, keyword
> checklist, or verification notes after the closing HTML tag."

This must be placed after the BANNED WORDS block, as the last substantive instruction.

### AC 2 -- `_strip_blog_trailer()` helper in `generation_prompts.py`

**Given** `backend/app/integrations/generation_prompts.py`,
**When** the story is implemented,
**Then** a new private function `_strip_blog_trailer(html: str) -> str` exists immediately after
`_md_to_html`. It clips everything after the last `>` character:

```python
def _strip_blog_trailer(html: str) -> str:
    last_tag_end = html.rfind(">")
    if last_tag_end == -1:
        return html
    return html[: last_tag_end + 1].rstrip()
```

No docstring (follows project no-comment default). The function is exported (no `__all__`
restriction; it is already imported by name in the integration files).

### AC 3 -- `_strip_blog_trailer` wired into `gemini.py`

**Given** `backend/app/integrations/gemini.py` `generate_blog`,
**When** the story is implemented,
**Then**:
- `_strip_blog_trailer` is added to the import block from `generation_prompts` (alongside the
  existing `_md_to_html` import)
- The result line changes from:
  ```python
  result = _md_to_html(_strip_fences(response.text.strip()))
  ```
  to:
  ```python
  result = _strip_blog_trailer(_md_to_html(_strip_fences(response.text.strip())))
  ```
- Nothing else in `gemini.py` is changed

### AC 4 -- `_strip_blog_trailer` wired into `anthropic_client.py`

**Given** `backend/app/integrations/anthropic_client.py` `generate_blog`,
**When** the story is implemented,
**Then**:
- `_strip_blog_trailer` is added to the import block from `generation_prompts`
- The result line changes from:
  ```python
  result = _md_to_html(_strip_fences(raw.strip()))
  ```
  to:
  ```python
  result = _strip_blog_trailer(_md_to_html(_strip_fences(raw.strip())))
  ```
- Nothing else in `anthropic_client.py` is changed

### AC 5 -- Five tests in `test_generation_prompts.py`

**Given** `backend/tests/test_generation_prompts.py`,
**When** the story is implemented,
**Then** a new `TestStripBlogTrailer` class is appended to the file with exactly these five test
methods:

1. `test_strips_compliance_report_after_last_tag` -- HTML with trailing `--- Word count: ...`
   block is clipped to just the HTML
2. `test_no_trailer_unchanged` -- clean HTML with no trailing text is returned unchanged
3. `test_empty_string_unchanged` -- empty string returns empty string
4. `test_no_html_tags_unchanged` -- plain text with no `>` characters is returned unchanged
5. `test_strips_whitespace_after_last_tag` -- trailing whitespace/newlines after the last `>`
   are stripped

The import for `_strip_blog_trailer` is added to the existing import block at the top of the
file alongside the other `generation_prompts` imports.

### AC 6 -- Existing tests pass

**Given** the existing `test_generation_prompts.py` test suite,
**When** the changes are applied,
**Then** all pre-existing tests continue to pass (`pytest backend/tests/test_generation_prompts.py`).

---

## Dev Notes

### The reverted fix is the correct implementation

Commit `7820803` has the exact code this story requires. It was reverted in `9e74d1e` without a
code reason. Re-apply it verbatim. The only addition is AC 1 (the prompt instruction), which the
reverted commit did not include.

To inspect the reverted diff:
```
git show 7820803
```

### Why `rfind(">")` is safe here

Blog HTML always ends with a closing tag (`</p>`, `</div>`, `</section>`, `</article>`). The
compliance report always begins with non-HTML text (`---`, `Word count:`) after the last closing
tag. Clipping at `rfind(">")` is therefore correct for all valid blog output.

The only scenario where this would be wrong is if the model emits inline SVG or `<script>` as
the final element -- neither of which belongs in blog article HTML.

### Insertion point for the prompt instruction (AC 1)

The current `_BLOG_PROMPT` ends (line 230) with:

```
Every sentence must earn its place. If a sentence does not give the reader new information or a
specific action, cut it.
"""
```

Insert the new instruction as the last line of the string body, before the closing `"""`:

```
Every sentence must earn its place. If a sentence does not give the reader new information or a
specific action, cut it.

Output ONLY the HTML above. Do NOT append any word count, compliance summary, keyword checklist, or verification notes after the closing HTML tag.
"""
```

### Function position in `generation_prompts.py`

`_strip_blog_trailer` goes after `_md_to_html` (currently the last function, ending at line 450).
Append it as the new final function in the file.

### Import block format in integration files

Both `gemini.py` and `anthropic_client.py` import from `generation_prompts` using a multi-line
import. Add `_strip_blog_trailer` on a new line after `_md_to_html`:

```python
from app.integrations.generation_prompts import (
    ...
    _md_to_html,
    _strip_blog_trailer,
)
```

### No migration, no DB change, no frontend change

This story touches only:
- `backend/app/integrations/generation_prompts.py` (prompt text + new function)
- `backend/app/integrations/gemini.py` (import + one-line change)
- `backend/app/integrations/anthropic_client.py` (import + one-line change)
- `backend/tests/test_generation_prompts.py` (import + new test class)

No other files are involved. Do not touch `generation.py`, `workers/generate.py`, or any
frontend file.

### Existing `generate_blog` pipeline shape (for orientation)

Both `gemini.py` and `anthropic_client.py` follow the same pattern after getting the raw LLM
response:

```python
result = _md_to_html(_strip_fences(raw.strip()))   # ← becomes _strip_blog_trailer(...)
result = result.replace("—", ", ")                 # em-dash stripping -- unchanged
if "<h1" not in result.lower():                    # post-processing validation -- unchanged
    logger.warning(...)
```

The stripper goes on the first of these three lines only.

---

## Tasks/Subtasks

- [x] AC 1: Add prompt-level suppression instruction to `_BLOG_PROMPT`
- [x] AC 2: Add `_strip_blog_trailer()` helper to `generation_prompts.py`
- [x] AC 3: Wire `_strip_blog_trailer` into `gemini.py` `generate_blog`
- [x] AC 4: Wire `_strip_blog_trailer` into `anthropic_client.py` `generate_blog`
- [x] AC 5: Add `TestStripBlogTrailer` class with 5 tests to `test_generation_prompts.py`
- [x] AC 6: All existing tests pass (42/42)

### Review Findings

- [x] [Review][Patch] `rfind(">")` fooled when trailer contains `>` character — compliance reports containing comparisons like `keyword density > 2%` cause `rfind` to land inside the trailer, leaving it partially unstripped [backend/app/integrations/generation_prompts.py:456]
- [x] [Review][Defer] No debug log when `_strip_blog_trailer` actually strips content — silent truncation; no observability in production [backend/app/integrations/generation_prompts.py:455-459] — deferred, observability improvement
- [x] [Review][Defer] `_strip_blog_trailer` lives in wrong module — output post-processing belongs outside `generation_prompts.py` (a prompt-construction module) [backend/app/integrations/generation_prompts.py] — deferred, architectural cleanup
- [x] [Review][Defer] Pre-existing em-dash replacement inconsistency — Anthropic replaces `—` with `", "` while Gemini does too (consistent); pre-existing, not caused by this change [backend/app/integrations/gemini.py:272, backend/app/integrations/anthropic_client.py:119] — deferred, pre-existing

---

## Dev Agent Record

### Implementation Notes

Re-applied the fix from commit `7820803` (which was reverted in `9e74d1e`) with one addition: the prompt-level suppression instruction (AC 1). The `_strip_blog_trailer` function was implemented without a docstring per project convention. All 42 tests pass.

### Completion Notes

All 4 files modified exactly as specified. 5 new tests added in `TestStripBlogTrailer`. 42/42 tests pass with no regressions.

---

## File List

- `backend/app/integrations/generation_prompts.py` (modified: prompt instruction + `_strip_blog_trailer` function)
- `backend/app/integrations/gemini.py` (modified: import + result line)
- `backend/app/integrations/anthropic_client.py` (modified: import + result line)
- `backend/tests/test_generation_prompts.py` (modified: import + `TestStripBlogTrailer` class)

---

## Change Log

- 2026-08-09: Re-applied compliance report stripper from commit 7820803; added prompt-level suppression instruction; 5 new tests added.
