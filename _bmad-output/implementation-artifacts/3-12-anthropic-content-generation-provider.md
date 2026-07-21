---
baseline_commit: 104bc34
---

# Story 3.12: Anthropic Content Generation Provider

Status: done

## Story

As a PersonnaPress developer,
I want the content generation pipeline (blog, fidelity check, social posts) to use the Anthropic API (Claude Haiku 4.5) instead of Gemini when `LLM_PROVIDER=anthropic`,
so that output HTML quality is higher, markdown leakage is eliminated, and prompt instruction-following is tighter without changing any prompts.

## Acceptance Criteria

### AC 1 — Provider dispatch in generation.py

1. **Given** `settings.LLM_PROVIDER == "anthropic"`, **When** `run_generation_pipeline` is invoked, **Then** it calls `anthropic_client.generate_blog`, `anthropic_client.check_fidelity`, and `anthropic_client.generate_social` — not their Gemini equivalents.
2. **Given** `settings.LLM_PROVIDER == "gemini"` (or any value other than `"anthropic"`), **When** `run_generation_pipeline` is invoked, **Then** it calls the Gemini functions exactly as before — zero behavioral change.

### AC 2 — generation_prompts.py extracted module

3. **Given** `backend/app/integrations/generation_prompts.py` exists, **When** it is imported, **Then** it exports all of the following without error: `_DEFAULT_VOICE`, `_BLOG_PROMPT`, `_FIDELITY_PROMPT`, `_SOCIAL_PROMPT`, `_build_seo_section`, `_build_voice_injection`, `_meta_voice_note`, `_strip_fences`, `_md_to_html`.
4. **Given** the extraction, **When** `gemini.py` is imported, **Then** all five existing public functions (`extract_brand_voice`, `synthesize_voice_brief`, `generate_blog`, `check_fidelity`, `generate_social`) still work correctly by importing from `generation_prompts`.

### AC 3 — anthropic_client.py generate_blog

5. **Given** `LLM_PROVIDER=anthropic`, **When** `generate_blog` is called, **Then** it posts the same prompt (built from `generation_prompts._BLOG_PROMPT`) to `anthropic.AsyncAnthropic.messages.create` using `model=settings.ANTHROPIC_MODEL` and `max_tokens=max(8192, thinking_tokens + 4096)`.
6. **Given** an Anthropic response, **When** the text is returned, **Then** it passes through `_md_to_html`, `_strip_fences`, and em-dash replacement (`"—"` → `", "`) — identical post-processing to the Gemini path.
7. **Given** the result, **When** the TL;DR block is absent, **Then** the same fallback injection logic is applied as in `gemini.generate_blog`.
8. **Given** `thinking_tokens > 0`, **When** `generate_blog` is called, **Then** the Anthropic call includes `thinking={"type": "enabled", "budget_tokens": thinking_tokens}` and the beta header `anthropic-beta: interleaved-thinking-2025-05-14`. The response text is extracted by finding the first `TextBlock` in `response.content` (`next(b.text for b in response.content if b.type == "text")`), not by indexing `[0]` (which may be a `ThinkingBlock`).
9. **Given** `thinking_tokens == 0`, **When** `generate_blog` is called, **Then** no `thinking` parameter is sent and `response.content[0].text` is used directly (safe — no thinking blocks present).

### AC 4 — anthropic_client.py check_fidelity

9. **Given** `LLM_PROVIDER=anthropic`, **When** `check_fidelity` is called, **Then** it posts the `_FIDELITY_PROMPT` to Anthropic with `max_tokens=1024`.
10. **Given** an Anthropic response, **When** the JSON is parsed, **Then** it applies identical validation to the Gemini path: required numeric fields, required bool fields, `seo_h2_count` int check, `tags` list coercion, advisory field coercion.
11. **Given** `brand_voice_profile is None`, **When** `check_fidelity` is called, **Then** it returns the same hardcoded default dict as `gemini.check_fidelity` — no Anthropic call is made.

### AC 5 — anthropic_client.py generate_social

12. **Given** `LLM_PROVIDER=anthropic`, **When** `generate_social` is called, **Then** it posts the `_SOCIAL_PROMPT` to Anthropic with `max_tokens=1024`.
13. **Given** an Anthropic response, **When** the JSON is parsed, **Then** it applies identical validation and truncation guards as `gemini.generate_social` (X post ≤ 280 chars with `…` truncation, LinkedIn 500–1300 chars with warning + truncation).

### AC 6 — retry wrapper handles Anthropic errors

14. **Given** `generation.py`, **When** `_gemini_with_retry` is renamed to `_llm_with_retry`, **Then** it still correctly retries transient Gemini errors (`ResourceExhausted`, `ServiceUnavailable`, genai `ClientError` 429/503).
15. **Given** `LLM_PROVIDER=anthropic`, **When** an Anthropic `RateLimitError` or `InternalServerError` is raised, **Then** `_llm_with_retry` retries with exponential backoff (same 4-attempt, 1s/2s/4s cadence) — it does NOT reraise immediately on these error types.

### AC 7 — Config additions

16. **Given** `backend/app/core/config.py`, **When** loaded, **Then** it contains:
    ```
    LLM_PROVIDER: str = "anthropic"    # "anthropic" | "gemini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    ```
17. **Given** no `ANTHROPIC_API_KEY` is set, **When** `LLM_PROVIDER=anthropic` and `generate_blog` is called, **Then** the Anthropic client raises `anthropic.AuthenticationError` — the system does NOT silently produce empty content. (No special guard needed; let it propagate and be caught by `_fail_job`.)

### AC 8 — requirements.txt and .env.example

18. **Given** `backend/requirements.txt`, **When** installed, **Then** `anthropic` package is present under the `# LLM` comment block.
19. **Given** `backend/.env.example`, **When** read, **Then** it contains the three new variables with comments:
    - `LLM_PROVIDER=anthropic` — with note `"anthropic" | "gemini"`
    - `ANTHROPIC_API_KEY=sk-ant-...` — with note about where to obtain it
    - `ANTHROPIC_MODEL=claude-haiku-4-5-20251001` — with note listing available fast models

### AC 9 — Tests

20. **Given** `backend/tests/test_anthropic_generation.py`, **When** run with `pytest`, **Then** tests cover:
    - `generate_blog` (no thinking): happy path returns HTML string; TL;DR fallback injection when absent; em-dash replacement.
    - `generate_blog` (with thinking): when `thinking_tokens=512`, the mock verifies `messages.create` was called with `thinking={"type": "enabled", "budget_tokens": 512}` and the beta header; response with a leading `ThinkingBlock` still returns correct text.
    - `check_fidelity`: happy path returns validated dict; `brand_voice_profile=None` returns default dict without calling Anthropic.
    - `generate_social`: happy path returns `x_post` and `linkedin_post`; X post truncation to 280 + `…`; LinkedIn warning logged when < 500 chars.
    All tests mock `anthropic.AsyncAnthropic` — no live API calls.

---

## Tasks / Subtasks

- [x] Task 1 — Create `generation_prompts.py` (AC 2)
  - [x] Move `_DEFAULT_VOICE`, `_BLOG_PROMPT`, `_FIDELITY_PROMPT`, `_SOCIAL_PROMPT`, `_build_seo_section`, `_build_voice_injection`, `_meta_voice_note`, `_strip_fences`, `_md_to_html` out of `gemini.py` into new file
  - [x] Add `from app.integrations.generation_prompts import ...` at top of `gemini.py`; verify it still imports cleanly

- [x] Task 2 — Update `config.py` (AC 7)
  - [x] Add `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` fields after `GEMINI_MODEL`

- [x] Task 3 — Update `requirements.txt` and `.env.example` (AC 8)
  - [x] Add `anthropic` under `# LLM` block in `requirements.txt`
  - [x] Append three new vars to `.env.example` under `# AI services`

- [x] Task 4 — Create `anthropic_client.py` (AC 3, 4, 5)
  - [x] Implement module-level `AsyncAnthropic(max_retries=0)` client
  - [x] Implement `_call(prompt, max_tokens)` — standard call, uses `response.content[0].text`
  - [x] Implement `_call_with_thinking(prompt, max_tokens, budget_tokens)` — adds `thinking` param + beta header; uses `next(b.text for b in response.content if b.type == "text")`
  - [x] Implement `generate_blog`: dispatch to `_call_with_thinking` when `thinking_tokens > 0`, else `_call`; `max_tokens=max(8192, thinking_tokens + 4096)`; identical prompt-building and post-processing as Gemini path
  - [x] Implement `check_fidelity` with identical signature, None-guard, prompt, validation (uses `_call`)
  - [x] Implement `generate_social` with identical signature, prompt, validation, truncation (uses `_call`)

- [x] Task 5 — Update `generation.py` (AC 1, 6)
  - [x] Add module-level provider dispatch (see Dev Notes)
  - [x] Rename `_gemini_with_retry` → `_llm_with_retry` (update all 3 call sites)
  - [x] Add Anthropic transient error detection to `_llm_with_retry` (see Dev Notes)
  - [x] Replace all `gemini.generate_blog` / `gemini.check_fidelity` / `gemini.generate_social` calls with `_llm.generate_blog` / etc.
  - [x] Keep `from app.integrations import gemini` for BVP ingestion path — this story does NOT touch `services/ingestion.py`

- [x] Task 6 — Write tests (AC 9)
  - [x] Create `backend/tests/test_anthropic_generation.py`
  - [x] 11 test functions covering the AC 9 requirements (7 required + 4 additional edge cases)

- [x] Task 7 — Smoke-test the dispatch (manual / integration)
  - [x] With `LLM_PROVIDER=anthropic` in `.env`, confirm `run_generation_pipeline` calls Anthropic
  - [x] With `LLM_PROVIDER=gemini`, confirm zero behavior change

---

## Dev Notes

### Architecture constraint — AR-19 boundary preserved

`services/generation.py` is the **ONLY** caller of the LLM integration for content generation. This story does NOT change that boundary. `anthropic_client.py` is a pure integration module: called only from `services/generation.py`. `services/ingestion.py` continues to call `gemini.py` directly (BVP extraction always uses Gemini — not affected by `LLM_PROVIDER`).

### generation_prompts.py — what moves and what stays

Items to move from `gemini.py` to `generation_prompts.py` (generation-related only):

```
_DEFAULT_VOICE
_build_voice_injection(bvp: dict) -> str
_meta_voice_note(bvp: dict) -> str
_BLOG_PROMPT
_FIDELITY_PROMPT
_SOCIAL_PROMPT
_build_seo_section(target_keyword, target_audience, secondary_keywords) -> tuple[str, str]
_strip_fences(raw: str) -> str
_md_to_html(html: str) -> str
```

Items that **stay** in `gemini.py` (BVP-specific or Gemini-infrastructure):
```
_client                        # genai.Client — Gemini only
_MODEL                         # settings.GEMINI_MODEL
_BVP_PROMPT_TEMPLATE           # used only by extract_brand_voice
_QUALITATIVE_DEFAULTS          # used only by extract_brand_voice
_VOICE_BRIEF_PROMPT            # used only by synthesize_voice_brief
_thinking_config()             # Gemini-specific config helper
extract_brand_voice()          # stays Gemini
synthesize_voice_brief()       # stays Gemini
```

`gemini.py` will gain `from app.integrations.generation_prompts import (...)` at the top. All 5 public functions keep working because the extracted symbols are simply re-imported.

### generation.py — provider dispatch pattern

Add after the existing imports (but AFTER `settings` is importable):

```python
from app.core.config import settings  # already imported at module top

if settings.LLM_PROVIDER == "anthropic":
    from app.integrations import anthropic_client as _llm
else:
    from app.integrations import gemini as _llm
```

Keep the bare `from app.integrations import gemini` import at the module level so `ingestion.py` patterns are not disturbed — but **generation.py does not import gemini directly for generation calls**. The generation calls change from:

```python
# BEFORE
await _gemini_with_retry(gemini.generate_blog, ...)
await _gemini_with_retry(gemini.check_fidelity, ...)
await _gemini_with_retry(gemini.generate_social, ...)
```

```python
# AFTER
await _llm_with_retry(_llm.generate_blog, ...)
await _llm_with_retry(_llm.check_fidelity, ...)
await _llm_with_retry(_llm.generate_social, ...)
```

Note: `_llm` only needs to expose `generate_blog`, `check_fidelity`, `generate_social` — `extract_brand_voice` and `synthesize_voice_brief` are NOT accessed via `_llm`.

### generation.py — retry wrapper update

Current name `_gemini_with_retry` becomes `_llm_with_retry`. Add Anthropic error detection:

```python
try:
    import anthropic as _anthropic_mod
    _RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC: tuple[type[Exception], ...] = (
        _anthropic_mod.RateLimitError,       # 429
        _anthropic_mod.InternalServerError,  # 500
        _anthropic_mod.OverloadedError,      # 529 — distinct from 500 per docs
    )
except ImportError:
    _RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC = ()
```

In `_llm_with_retry`, the error check becomes:

```python
if (
    (_RETRY_TRANSIENT_EXCEPTIONS and isinstance(exc, _RETRY_TRANSIENT_EXCEPTIONS))
    or _is_transient_genai_error(exc)
    or (_RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC and isinstance(exc, _RETRY_TRANSIENT_EXCEPTIONS_ANTHROPIC))
):
```

### anthropic_client.py — structure

```python
"""Anthropic LLM integration for content generation.

Called ONLY from services/generation.py (AR-19).
Implements same 3 function signatures as integrations/gemini.py generation functions.
BVP ingestion (extract_brand_voice, synthesize_voice_brief) always uses Gemini — not here.
"""

import json
import logging
import re

import anthropic

from app.core.config import settings
from app.integrations.generation_prompts import (
    _DEFAULT_VOICE, _BLOG_PROMPT, _FIDELITY_PROMPT, _SOCIAL_PROMPT,
    _build_seo_section, _build_voice_injection, _meta_voice_note,
    _strip_fences, _md_to_html,
)

logger = logging.getLogger(__name__)

# max_retries=0: disable SDK's built-in 2-attempt auto-retry so _llm_with_retry
# in generation.py has sole control over the backoff strategy (avoid double-retry).
_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=0)
_MODEL = settings.ANTHROPIC_MODEL
logger.info("Anthropic model: %s", _MODEL)


async def _call(prompt: str, max_tokens: int) -> str:
    """Standard call — no thinking. Safe to use response.content[0].text."""
    response = await _client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def _call_with_thinking(prompt: str, max_tokens: int, budget_tokens: int) -> str:
    """Call with extended thinking. response.content[0] may be a ThinkingBlock."""
    response = await _client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "enabled", "budget_tokens": budget_tokens},
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "interleaved-thinking-2025-05-14"},
    )
    return next(b.text for b in response.content if b.type == "text")


async def generate_blog(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 512,
    target_keyword: str | None = None,
    target_audience: str | None = None,
    secondary_keywords: str | None = None,
) -> str:
    # ... build prompt (identical to gemini.generate_blog) ...
    max_tokens = max(8192, thinking_tokens + 4096)
    if thinking_tokens > 0:
        raw = await _call_with_thinking(prompt, max_tokens, thinking_tokens)
    else:
        raw = await _call(prompt, max_tokens)
    # ... _md_to_html, _strip_fences, em-dash replace, TL;DR guard (identical) ...

async def check_fidelity(
    blog_html: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 256,    # not used — no thinking on fidelity check
) -> dict:
    ...

async def generate_social(
    brain_dump: str,
    blog_title: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 0,      # not used — no thinking on social
) -> dict:
    ...
```

**The prompt-building logic inside each function must be character-for-character identical to the corresponding Gemini function.** The only differences are the two `_call`/`_call_with_thinking` helpers and `max_tokens` calculation.

### Anthropic response access

Gemini: `response.text.strip()`
Anthropic: `response.content[0].text.strip()` (`.content` is a list of `ContentBlock`; `[0].text` is the text string)

### max_tokens per function

| Function | max_tokens | Thinking | Rationale |
|---|---|---|---|
| `generate_blog` | `max(8192, thinking_tokens + 4096)` | Yes — wired to `thinking_tokens` param | Ensures room for both thinking and ~2000 tokens of HTML output |
| `check_fidelity` | 1024 | No | JSON blob with ~10 fields |
| `generate_social` | 1024 | No | JSON with X (≤280 chars) + LinkedIn (≤1300 chars) |

Haiku 4.5 max output is **64k tokens** (confirmed from official model page). `max_tokens` must be greater than `budget_tokens` — the formula `max(8192, thinking_tokens + 4096)` satisfies this for any reasonable thinking budget. With the default `_BLOG_THINKING_TOKENS = 512` in `generation.py`, max_tokens resolves to 8192 (512 + 4096 = 4608 < 8192).

### extended thinking — generate_blog only

Extended thinking is wired up **only for `generate_blog`**. `check_fidelity` and `generate_social` ignore `thinking_tokens` entirely — they always use the standard `_call` helper.

`_BLOG_THINKING_TOKENS = 512` in `generation.py` is the budget passed to both Gemini (thinking budget) and the Anthropic path (extended thinking budget). With this budget, at $5/MTok output rate, thinking costs ~$0.0026 per blog call — negligible.

**Why only generate_blog?** The blog prompt has the most complex multi-constraint requirements (structural variation, vague-quantifier avoidance, E-E-A-T preservation). Fidelity check and social posts are deterministic enough that thinking adds latency without meaningful quality gain.

**Beta header required for Haiku 4.5:** `anthropic-beta: interleaved-thinking-2025-05-14` must be passed via `extra_headers`. Without it, the thinking parameter is silently ignored on Haiku 4.5.

**Critical: response content indexing.** When thinking is enabled, `response.content` is a list that may start with one or more `ThinkingBlock` objects followed by a `TextBlock`. Never use `response.content[0].text` — always use:
```python
next(b.text for b in response.content if b.type == "text")
```
For `_call` (no thinking), `response.content[0]` is always a `TextBlock`, so direct indexing is safe.

### generation_logs — no schema change

`generation_logs_repo.create_generation_log()` has `gemini_tokens` as the field name in both the Python function and the DB column. This story does NOT rename it. Continue to pass `_ESTIMATED_TOTAL_TOKENS` regardless of provider; this is cosmetic and out of scope.

### Test pattern for anthropic_client.py

Mock `anthropic.AsyncAnthropic` at the class level:

```python
from unittest.mock import AsyncMock, MagicMock, patch

def _make_anthropic_response(text: str):
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response

@pytest.mark.asyncio
@patch("app.integrations.anthropic_client._client")
async def test_generate_blog_returns_html(mock_client):
    mock_client.messages.create = AsyncMock(
        return_value=_make_anthropic_response(_VALID_BLOG_HTML)
    )
    ...
```

Mirror the fixture names and structure from `test_gemini_generation.py` for consistency.

### Files to create / modify

| Action | File |
|---|---|
| NEW | `backend/app/integrations/generation_prompts.py` |
| MODIFY | `backend/app/integrations/gemini.py` — import from generation_prompts; remove moved items |
| NEW | `backend/app/integrations/anthropic_client.py` |
| MODIFY | `backend/app/services/generation.py` — dispatch + retry rename |
| MODIFY | `backend/app/core/config.py` — 3 new settings |
| MODIFY | `backend/requirements.txt` — add `anthropic` |
| MODIFY | `backend/.env.example` — document 3 new vars |
| NEW | `backend/tests/test_anthropic_generation.py` |

### Do NOT touch

- `backend/app/services/ingestion.py` — calls `gemini.extract_brand_voice` and `gemini.synthesize_voice_brief` directly; stays on Gemini always.
- Any frontend file.
- Any database migration — no schema changes.
- `test_gemini_generation.py` — existing tests must still pass after gemini.py refactor.
- `test_gemini_integration.py` — existing tests must still pass.

### Regression check

After the refactor, `from app.integrations import gemini; gemini.generate_blog(...)` must still work — the Gemini functions re-import from `generation_prompts` but expose the same interface. Run `pytest backend/tests/test_gemini_generation.py` and confirm 0 failures before writing tests for the new Anthropic client.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Extracted 9 generation symbols from `gemini.py` into new `generation_prompts.py`; gemini.py re-imports them — all 62 existing Gemini tests pass unchanged (AC 2 verified).
- Created `anthropic_client.py` with `_call`, `_call_with_thinking`, `generate_blog`, `check_fidelity`, `generate_social` — prompt-building logic is character-for-character identical to gemini.py counterparts (AC 3, 4, 5).
- Extended thinking wired only to `generate_blog` via `_call_with_thinking`; uses `next(b.text for b in response.content if b.type == "text")` to skip ThinkingBlocks (AC 3, AC 8 safety).
- `generation.py` provider dispatch via module-level `if settings.LLM_PROVIDER == "anthropic"` import; `_gemini_with_retry` renamed to `_llm_with_retry` with added Anthropic transient error types (`RateLimitError`, `InternalServerError`, `OverloadedError`) — AC 1, AC 6.
- `config.py`: added `LLM_PROVIDER="anthropic"`, `ANTHROPIC_API_KEY=""`, `ANTHROPIC_MODEL="claude-haiku-4-5-20251001"` (AC 7).
- `requirements.txt` + `.env.example` updated with `anthropic` package and three new env vars (AC 8).
- 11 tests written in `test_anthropic_generation.py`; all pass; no regressions in 73 combined generation tests (AC 9).

### File List

- backend/app/integrations/generation_prompts.py (NEW)
- backend/app/integrations/gemini.py (MODIFIED)
- backend/app/integrations/anthropic_client.py (NEW)
- backend/app/services/generation.py (MODIFIED)
- backend/app/core/config.py (MODIFIED)
- backend/requirements.txt (MODIFIED)
- backend/.env.example (MODIFIED)
- backend/tests/test_anthropic_generation.py (NEW)

### Review Findings

- [x] [Review][Patch] StopIteration guard in `_call_with_thinking` — `next()` without default raises StopIteration if Anthropic response has no text block [backend/app/integrations/anthropic_client.py:55] — **fixed**: use `next((…), None)` + ValueError on None
- [x] [Review][Patch] Empty content guard in `_call` — `response.content[0].text` raises IndexError if content list is empty [backend/app/integrations/anthropic_client.py:43] — **fixed**: guard added before indexing
- [x] [Review][Patch] Dead `from app.integrations import gemini` import in generation.py — bare import is unused; `_llm` dispatch handles all generation calls [backend/app/services/generation.py:24] — **fixed**: removed
- [x] [Review][Patch] `test_check_fidelity_none_bvp_returns_default_without_api_call` missing no-API-call assertion [backend/tests/test_anthropic_generation.py:181] — **fixed**: added `@patch` + `mock_client.messages.create.assert_not_called()`
- [x] [Review][Defer] Unpinned `anthropic` in requirements.txt [backend/requirements.txt:27] — deferred, pre-existing pattern (`google-genai` also unpinned)
- [x] [Review][Defer] `_md_to_html` DOTALL flag spans across multi-line bold [backend/app/integrations/generation_prompts.py:232] — deferred, pre-existing behaviour moved from gemini.py
- [x] [Review][Defer] `_strip_fences` no handling for mid-output closing fence [backend/app/integrations/generation_prompts.py:217] — deferred, pre-existing behaviour moved from gemini.py

## Change Log

- 2026-07-20: Implemented Anthropic content generation provider — generation_prompts.py extraction, anthropic_client.py, provider dispatch in generation.py, config/requirements/env updates, 11 tests (Date: 2026-07-20)
- 2026-07-20: Code review complete — 4 patches applied (StopIteration guard in _call_with_thinking, empty content guard in _call, dead gemini import removed from generation.py, assert_not_called added to None-BVP fidelity test), marked done
