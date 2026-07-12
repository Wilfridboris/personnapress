# Story 3.9: Configurable Gemini Model via Environment Variable

---
baseline_commit: 3b2d111a7b41e2668825604823a75e900c8cbbe2
---

Status: done

## Story

As a developer/operator,
I want the Gemini model name to be read from an environment variable (`GEMINI_MODEL`) with a safe default,
so that the running model can be switched between `gemini-2.5-flash`, `gemini-2.5-pro`, or any future model without a code change.

## Acceptance Criteria

1. **Given** `GEMINI_MODEL` is not set in the environment,
   **When** the backend starts,
   **Then** all Gemini calls use `gemini-2.5-flash` (the existing behavior is preserved — no regression).

2. **Given** `GEMINI_MODEL=gemini-2.5-pro` is set in the environment,
   **When** the backend starts,
   **Then** all four Gemini call sites (`extract_brand_voice`, `generate_blog`, `check_fidelity`, `generate_social`) use `gemini-2.5-pro`.

3. **Given** the backend `.env.example` is reviewed,
   **When** the file is read,
   **Then** a `GEMINI_MODEL` entry is present next to `GEMINI_API_KEY`, with a comment listing supported values and the default.

4. **Given** the settings module is reviewed,
   **When** `config.py` is read,
   **Then** `GEMINI_MODEL: str = "gemini-2.5-flash"` is present in the `Settings` class.

## Tasks / Subtasks

- [x] Add `GEMINI_MODEL` to Settings (AC: 1, 2, 4)
  - [x] Add `GEMINI_MODEL: str = "gemini-2.5-flash"` to `backend/app/core/config.py` `Settings` class, placed immediately after `GEMINI_API_KEY`
- [x] Wire `settings.GEMINI_MODEL` into gemini.py (AC: 1, 2)
  - [x] Change `_MODEL = "gemini-2.5-flash"` on line 20 of `backend/app/integrations/gemini.py` to `_MODEL = settings.GEMINI_MODEL`
- [x] Document in `.env.example` (AC: 3)
  - [x] Add `GEMINI_MODEL=gemini-2.5-flash` immediately after `GEMINI_API_KEY=` in `backend/.env.example`, with a comment listing known values

## Dev Notes

### Exact Files to Change (3 files, all small edits)

**1. `backend/app/core/config.py`** — current line 33 area:
```python
# BEFORE (line 33):
    GEMINI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""

# AFTER:
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    REPLICATE_API_TOKEN: str = ""
```

**2. `backend/app/integrations/gemini.py`** — current line 20:
```python
# BEFORE:
_MODEL = "gemini-2.5-flash"

# AFTER:
_MODEL = settings.GEMINI_MODEL
```
`settings` is already imported on line 14 (`from app.core.config import settings`) — no new import needed.

**3. `backend/.env.example`** — in the "# AI services" block (current line 38-39):
```
# AI services
GEMINI_API_KEY=your-gemini-api-key
# Gemini model to use for all AI calls. Default: gemini-2.5-flash (fast + cheap).
# Upgrade to gemini-2.5-pro for higher quality output at higher cost.
# Verify available model IDs at: https://ai.google.dev/models
GEMINI_MODEL=gemini-2.5-flash
REPLICATE_API_TOKEN=r8_...
```

### Architecture Compliance

- `services/generation.py` and `services/ingestion.py` call `gemini.py` functions (AR-19) — they do NOT need changes. Only gemini.py uses `_MODEL`, so the single-point change is sufficient.
- `_MODEL` is a module-level constant resolved at import time. Since `settings` is also module-level, this is safe — the value is read once when the module loads, which is the correct behavior.
- Do NOT add `GEMINI_MODEL` validation (e.g., an enum or whitelist). The Gemini client will return a clear API error for invalid model names. Over-engineering this is out of scope.
- Do NOT expose this setting via any API endpoint or admin UI. This is an operator-level env var only.

### Testing

- **No test changes required.** Existing tests in `backend/tests/test_gemini_generation.py` mock `_client` entirely with `@patch("app.integrations.gemini._client")` — the model string is never asserted in any test. All 49+ tests will continue to pass unchanged.
- Manual smoke test: Set `GEMINI_MODEL=gemini-2.5-pro` in local `.env` and run the app; trigger a generation to confirm calls succeed with the Pro model.

### Model Name Reference (verify against live API at implementation time)

As of mid-2025, confirmed Gemini model IDs via Google AI SDK:
- `gemini-2.5-flash` — current default, fastest, lowest cost
- `gemini-2.5-pro` — higher capability, higher cost
- `gemini-2.0-flash` — older generation, still supported

**Note:** "Gemini 3.1 Pro" does not exist as of this writing. Boris may have meant `gemini-2.5-pro`. Always verify model availability at `https://ai.google.dev/models` before deploying a non-default value to production.

### Previous Story Context

This story is an isolated infrastructure tweak with no functional change to existing behavior. No previous story learnings affect implementation. The `settings` import pattern used here is identical to every other env-var usage across the codebase.

### Project Structure Notes

- All env vars live in `backend/app/core/config.py` as `Settings` fields — never add env vars elsewhere
- `settings` singleton is imported as `from app.core.config import settings` — do not re-instantiate
- The `_MODEL` module-level constant pattern in `gemini.py` is intentional (single read at import time) — preserve it

### References

- [Source: backend/app/integrations/gemini.py#line 14-20] — existing import + `_MODEL` constant
- [Source: backend/app/core/config.py#line 33] — `GEMINI_API_KEY` placement (add `GEMINI_MODEL` after it)
- [Source: backend/.env.example#line 38-40] — "AI services" block where new entry belongs
- [Source: _bmad-output/planning-artifacts/epics.md#AR-19] — service boundary rule: only `services/generation.py` calls `gemini.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `GEMINI_MODEL: str = "gemini-2.5-flash"` to Settings after `GEMINI_API_KEY`; module-level `_MODEL` in gemini.py now reads from `settings.GEMINI_MODEL` at import time. All 41 existing tests pass unchanged (they mock `_client`, never assert on the model string). `.env.example` documents supported values and upgrade path.

### File List

- backend/app/core/config.py
- backend/app/integrations/gemini.py
- backend/.env.example

## Review Findings

- [x] [Review][Patch] No startup log of resolved model name [backend/app/integrations/gemini.py:21] — fixed: added `logger.info("Gemini model: %s", _MODEL)`
- [x] [Review][Defer] Empty string valid for GEMINI_MODEL — deferred, explicitly out of scope per story dev notes ("Do NOT add validation")
- [x] [Review][Defer] No allowlist/enum validation on model name — deferred, explicitly out of scope per story dev notes
- [x] [Review][Defer] Whitespace in GEMINI_MODEL not stripped — deferred, validation out of scope per story
- [x] [Review][Defer] Module-level singleton design limits per-request overrides — deferred, pre-existing pattern
