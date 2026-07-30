---
baseline_commit: 4d0ee73fd6be1c76d099dd24deec3d3cbedd83f9
---

# Story 16.6: Voice Signal Injection -- Signature Phrases, Voice Anchors & Anti-Pattern

Status: done

## Story

As a PersonnaPress system,
I want to inject `signature_phrases`, `voice_anchor_sentences`, and `anti_pattern_example` from the Brand Voice Profile into blog and social generation prompts as explicit few-shot style signals,
so that generated content uses the writer's actual verbal patterns rather than only descriptor-based approximations.

## Context & Motivation

Epic 16 built a 20-field Brand Voice Profile. Story 16.4 injected `voice_brief` (a prose description) and behavioral rules into the blog prompt via `_build_voice_injection()`. However three BVP fields are captured during extraction (Story 16.2) but never used at generation time:

- `signature_phrases` -- 5-10 verbatim phrases pulled from the user's actual writing
- `voice_anchor_sentences` -- 3-5 complete verbatim sentences representing the user's voice
- `anti_pattern_example` -- one sentence the writer would never produce

**Blog prompt:** these three fields are completely absent from `_build_voice_injection()` in `generation_prompts.py`.

**Social prompts:** `signature_phrases` and `voice_anchor_sentences` are technically present inside the `bvp_json` JSON dump that both social prompts receive, but they are buried in a 15-field JSON object with no instruction on how to apply them. The X post does not receive `voice_brief` at all, making it the lowest voice-fidelity generated content.

**Impact:** Without few-shot examples, voice matching is purely descriptor-based ("write like someone formal who uses specific numbers"). Adding the user's actual phrases and sentences shifts the model from "describing voice" to "showing voice" -- the strongest signal available.

This story closes that gap with minimal surface area: no schema changes, no API changes, no DB migrations, no frontend changes.

---

## Acceptance Criteria

### AC 1 -- Blog prompt: SIGNATURE PHRASES block

1. **Given** `_build_voice_injection(bvp: dict)` in `backend/app/integrations/generation_prompts.py`, **When** `bvp.get("signature_phrases")` returns a non-empty list of at least 1 string, **Then** the following block is appended to the returned string after all existing VOICE APPLICATION RULES:
   ```
   SIGNATURE PHRASES (short phrases this writer uses naturally -- weave 2-3 into the post where they fit organically; never force them and never repeat the same phrase twice):
   - [phrase 1]
   - [phrase 2]
   ...
   ```

2. **Given** `signature_phrases` contains more than 10 entries, **When** the block is built, **Then** only the first 10 phrases are included (cap to avoid exceeding prompt attention).

---

### AC 2 -- Blog prompt: VOICE ANCHORS block

3. **Given** `_build_voice_injection(bvp: dict)`, **When** `bvp.get("voice_anchor_sentences")` returns a non-empty list of at least 1 string, **Then** a `VOICE ANCHORS` block is appended directly after the SIGNATURE PHRASES block (or after VOICE APPLICATION RULES if signature_phrases is absent):
   ```
   VOICE ANCHORS (verbatim sentences from this writer -- these represent the target register, rhythm, and directness; match this level throughout the post):
   - [sentence 1]
   - [sentence 2]
   ...
   ```

4. **Given** `voice_anchor_sentences` contains more than 5 entries, **When** the block is built, **Then** only the first 5 are included.

---

### AC 3 -- Blog prompt: ANTI-PATTERN block

5. **Given** `_build_voice_injection(bvp: dict)`, **When** `bvp.get("anti_pattern_example")` returns a non-empty string, **Then** an `ANTI-PATTERN` note is appended after VOICE ANCHORS (or after the last existing block):
   ```
   ANTI-PATTERN (this writer would NEVER produce a sentence like this -- avoid this register, vocabulary, and structure throughout):
   "[anti_pattern_example]"
   ```

---

### AC 4 -- Backward compatibility

6. **Given** a BVP where `signature_phrases`, `voice_anchor_sentences`, and `anti_pattern_example` are all absent, empty lists, or empty strings, **When** `_build_voice_injection(bvp)` is called, **Then** no new blocks are added and the returned string is identical to the output produced by Story 16.4. Existing BVPs (pre-16.2 legacy profiles that only have tone/cadence/banned_jargon) are unaffected.

7. **Given** a BVP where `voice_brief` is absent (legacy BVP), **When** `_build_voice_injection(bvp)` is called, **Then** the function still returns an empty string as it did in Story 16.4 -- the new blocks are only added when `voice_brief` is present (the existing guard `if not voice_brief: return ""` stays in place).

---

### AC 5 -- Em-dash sanitization

8. **Given** any signature phrase, voice anchor sentence, or anti-pattern example that contains an em-dash character (`—`), **When** `_build_voice_injection(bvp)` formats it for the prompt, **Then** all em-dashes are replaced with `--` before injection. This prevents the injected voice signals from violating the project-wide em-dash ban that applies to all generated output.

---

### AC 6 -- Standalone social prompt: phrase signals

9. **Given** `_build_standalone_voice_injection(bvp: dict)` in `generation_prompts.py` (used for the Plan My Week social-only path via `_SOCIAL_STANDALONE_PROMPT`), **When** `bvp.get("signature_phrases")` returns a non-empty list, **Then** the `BRAND STRUCTURE HINTS` section includes an additional bullet:
   ```
   - Writer's signature phrases -- use 1-2 naturally in the LinkedIn post (not in x_post): [top 5 phrases, comma-separated]
   ```
   If `bvp.get("anti_pattern_example")` is non-empty, also add:
   ```
   - ANTI-PATTERN: never produce text like "[anti_pattern_example]"
   ```

10. **Given** `_build_standalone_voice_injection(bvp)` returns a non-empty string with the new hints, **When** the standalone social prompt is rendered, **Then** the existing structure (opening_pattern, closing_pattern, post_structure_template hints) is preserved and the new phrase hints are appended after them. If none of the three fields (opening_pattern, closing_pattern, post_structure_template, signature_phrases) are present, the function returns an empty string as before.

---

### AC 7 -- Tests

11. **Given** a test file (extend `backend/tests/test_generation_prompts.py` if it exists, otherwise create it), **When** run, **Then** tests cover:
    - Blog voice injection with all three new fields populated: all three blocks appear in the returned string
    - Blog voice injection with empty/absent fields: output identical to Story 16.4 baseline (no new blocks)
    - Em-dash in a signature phrase is converted to `--`
    - Signature phrases capped at 10; voice_anchor_sentences capped at 5
    - Standalone social injection with signature_phrases: phrase hint and anti-pattern appear in BRAND STRUCTURE HINTS
    - Standalone social injection with empty signature_phrases: existing output unchanged

---

## Tasks / Subtasks

### Task 1 -- Extend `_build_voice_injection()` (AC 1-5, 8)

- [x] 1.1 Open `backend/app/integrations/generation_prompts.py`. Locate `_build_voice_injection(bvp: dict) -> str` (currently returns early if `voice_brief` is absent).

- [x] 1.2 After the existing Part B block is assembled (the `return (...)` statement that includes `voice_brief` + VOICE APPLICATION RULES), add logic to build optional new blocks:
  ```python
  sig_phrases = [p for p in (bvp.get("signature_phrases") or []) if isinstance(p, str) and p.strip()][:10]
  voice_anchors = [s for s in (bvp.get("voice_anchor_sentences") or []) if isinstance(s, str) and s.strip()][:5]
  anti_pattern = (bvp.get("anti_pattern_example") or "").strip().replace("—", "--")

  sig_block = ""
  if sig_phrases:
      phrases_clean = [p.replace("—", "--") for p in sig_phrases]
      bullet_list = "\n".join(f"- {p}" for p in phrases_clean)
      sig_block = (
          "\nSIGNATURE PHRASES (short phrases this writer uses naturally -- weave 2-3 into the post "
          "where they fit organically; never force them and never repeat the same phrase twice):\n"
          + bullet_list
      )

  anchor_block = ""
  if voice_anchors:
      anchors_clean = [s.replace("—", "--") for s in voice_anchors]
      bullet_list = "\n".join(f"- {s}" for s in anchors_clean)
      anchor_block = (
          "\nVOICE ANCHORS (verbatim sentences from this writer -- these represent the target register, "
          "rhythm, and directness; match this level throughout the post):\n"
          + bullet_list
      )

  anti_block = ""
  if anti_pattern:
      anti_block = (
          f'\nANTI-PATTERN (this writer would NEVER produce a sentence like this -- avoid this register, '
          f'vocabulary, and structure throughout):\n"{anti_pattern}"'
      )
  ```

- [x] 1.3 Append `sig_block + anchor_block + anti_block` to the existing return value. The return statement currently builds a multi-line f-string; append the new blocks at the end of that string before it is returned.

- [x] 1.4 Do NOT change the early-return guard `if not voice_brief: return ""` -- that guard stays in place so legacy BVPs without `voice_brief` are unaffected.

---

### Task 2 -- Extend `_build_standalone_voice_injection()` (AC 6, 9-10)

- [x] 2.1 Open `_build_standalone_voice_injection(bvp: dict) -> str` in the same file. It currently checks `opening_pattern`, `closing_pattern`, and `post_structure_template`.

- [x] 2.2 After the existing hints are assembled, add:
  ```python
  sig_phrases = [p for p in (bvp.get("signature_phrases") or []) if isinstance(p, str) and p.strip()][:5]
  anti_pattern = (bvp.get("anti_pattern_example") or "").strip().replace("—", "--")

  if sig_phrases:
      phrases_str = ", ".join(p.replace("—", "--") for p in sig_phrases)
      hints.append(
          f"- Writer's signature phrases -- use 1-2 naturally in the LinkedIn post (not in x_post): {phrases_str}"
      )
  if anti_pattern:
      hints.append(f'- ANTI-PATTERN: never produce text like "{anti_pattern}"')
  ```

- [x] 2.3 The existing early-return `if not hints: return ""` is already at the bottom of the function -- no change needed there; the new hints are added to the same `hints` list.

---

### Task 3 -- Tests (AC 7, 11)

- [x] 3.1 Check if `backend/tests/test_generation_prompts.py` exists. If not, create it.

- [x] 3.2 Write tests for `_build_voice_injection()`:
  - Full BVP with all three new fields: assert SIGNATURE PHRASES, VOICE ANCHORS, and ANTI-PATTERN blocks all appear in the output
  - BVP with only `voice_brief` set (other new fields absent/empty): output must NOT contain "SIGNATURE PHRASES", "VOICE ANCHORS", or "ANTI-PATTERN"
  - Em-dash in signature phrase: `"test—phrase"` must appear as `"test--phrase"` in output
  - signature_phrases list of 15 items: only 10 appear
  - voice_anchor_sentences list of 8 items: only 5 appear
  - BVP without `voice_brief`: returns empty string (unchanged from 16.4)

- [x] 3.3 Write tests for `_build_standalone_voice_injection()`:
  - BVP with `signature_phrases` and `anti_pattern_example`: both hints appear in BRAND STRUCTURE HINTS
  - BVP without `signature_phrases` but with `opening_pattern`: existing hint present, no phrase hint
  - BVP with no relevant fields at all: returns empty string

---

## Dev Notes

### Files to modify

- `backend/app/integrations/generation_prompts.py` -- only file that changes; two functions updated
- `backend/tests/test_generation_prompts.py` -- create or extend

No router changes. No schema changes. No DB migrations. No frontend changes. No changes to `gemini.py` or `anthropic_client.py` (they call `_build_voice_injection()` and `_build_standalone_voice_injection()` which already pass through).

### Key existing patterns to reuse

- `_build_voice_injection()` currently returns a multi-line f-string. The new blocks are string concatenation appended to that return value. Match the existing style: `\n` newlines, `--` for dashes, no em-dashes.
- `_build_standalone_voice_injection()` builds a `hints: list[str]` then joins with `"\n"`. New items go onto the same `hints` list using `hints.append(...)`.
- The existing `.replace("—", "--")` pattern is already used in `gemini.py` post-processing (line ~240). Use the same pattern for pre-processing the injected values.

### How `_build_voice_injection()` is called (don't break these)

- `gemini.py::generate_blog()` calls `_build_voice_injection(brand_voice_profile)` and assigns result to `voice_section`. This is injected into `_BLOG_PROMPT` via `voice_section=voice_section`.
- `anthropic_client.py` does the same (it imports `_build_voice_injection` from `generation_prompts.py` per AR-19 -- Story 3.12 pattern).
- Neither caller changes in this story.

### How `_build_standalone_voice_injection()` is called

- `gemini.py::generate_social_standalone()` calls it and passes result as `bvp_structure_hints` into `_SOCIAL_STANDALONE_PROMPT.format(...)`.
- `anthropic_client.py` does the same.
- Neither caller changes.

### Voice brief guard -- MUST preserve

`_build_voice_injection()` starts with:
```python
voice_brief = bvp.get("voice_brief") or ""
if not voice_brief:
    return ""
```
Do NOT remove this guard. Legacy BVPs (pre-Story 16.2) have no `voice_brief`. Adding signature phrases to a BVP without voice_brief would cause an inconsistent half-injection. The guard ensures the new blocks are only added when the full voice context is already present.

### LLM provider parity

The project supports two LLM providers (Gemini and Anthropic, set via `LLM_PROVIDER` env var). Both call the same `generation_prompts.py` functions. This story only changes `generation_prompts.py`, so both providers automatically get the improved prompts -- no parity work needed.

### Testing approach from prior stories

Story 16.4 added tests that mock the Gemini client and verify prompt content. Story 3.14 added similar tests for both providers. For this story, the functions under test (`_build_voice_injection`, `_build_standalone_voice_injection`) are pure Python string builders -- no LLM mocking needed. Unit test them directly.

### Project Structure Notes

- File: `backend/app/integrations/generation_prompts.py` -- shared prompt module, imported by both `gemini.py` and `anthropic_client.py` per AR-19. Never import LLM clients from here.
- Test file: `backend/tests/test_generation_prompts.py` (create if absent; pattern from `backend/tests/test_voice_extraction.py`).
- No frontend files.

### References

- `_build_voice_injection()` implementation: `backend/app/integrations/generation_prompts.py` lines 15-61
- `_build_standalone_voice_injection()`: same file, lines 204-247
- Story 16.2 (BVP extraction, signature_phrases defined): `_bmad-output/implementation-artifacts/16-2-gemini-qualitative-extraction-voice-brief.md`
- Story 16.4 (voice_brief injection, Part A + Part B pattern): `_bmad-output/implementation-artifacts/16-4-voice-driven-blog-generation-update.md`
- Story 3.14 (standalone social prompt, `_build_standalone_voice_injection` pattern): `_bmad-output/implementation-artifacts/3-14-social-standalone-prompt.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. Pure string-builder functions with no external dependencies.

### Completion Notes List

- Extended `_build_voice_injection()` to append SIGNATURE PHRASES (capped at 10), VOICE ANCHORS (capped at 5), and ANTI-PATTERN blocks after the existing VOICE APPLICATION RULES block. Em-dash sanitization applied to all three fields. Early-return guard on `voice_brief` preserved.
- Extended `_build_standalone_voice_injection()` to append signature phrase and anti-pattern hints onto the existing `hints` list before the `if not hints: return ""` check, so they contribute to the BRAND STRUCTURE HINTS section.
- Created `backend/tests/test_generation_prompts.py` with 23 unit tests covering all ACs: full field injection, empty/absent backward compat, em-dash replacement, caps (10/5), block ordering, standalone phrase hints, and empty-returns. All 23 pass.

### File List

- backend/app/integrations/generation_prompts.py (modified)
- backend/tests/test_generation_prompts.py (created)

### Change Log

- 2026-07-29: Story 16.6 -- injected signature_phrases, voice_anchor_sentences, anti_pattern_example into blog and standalone social prompts; 23 tests added

### Review Findings

- [x] [Review][Patch] Non-list value for `signature_phrases`/`voice_anchor_sentences` iterates characters [generation_prompts.py:50-54]
- [x] [Review][Patch] `anti_pattern_example` non-string truthy value causes AttributeError on `.strip()` [generation_prompts.py:56]
- [x] [Review][Patch] Embedded newlines in phrases/anchors break bullet-per-item structure [generation_prompts.py:60-71]
- [x] [Review][Patch] Embedded `"` in anti_pattern creates unbalanced quotes in wrapped prompt text [generation_prompts.py:82]
- [x] [Review][Patch] `bullet_list` var reused in same scope -- rename to `sig_bullet_list`/`anchor_bullet_list` [generation_prompts.py:61,71]
- [x] [Review][Defer] Prompt injection via user-controlled BVP content -- deferred, pre-existing pattern across all BVP fields; user's own content in their own prompts
- [x] [Review][Defer] Standalone ANTI-PATTERN hint fires independently of `signature_phrases` (AC 6 "also add" ambiguity) -- deferred, spec ambiguity; independent behavior is more functional; test explicitly validates it
- [x] [Review][Defer] Standalone hint hardcodes "(not in x_post)" -- deferred, pre-existing design choice for social-standalone path
