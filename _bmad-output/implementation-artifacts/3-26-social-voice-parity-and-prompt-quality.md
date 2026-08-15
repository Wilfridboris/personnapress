---
baseline_commit: 1d6b543
---

# Story 3.26: Social Voice Parity and Prompt Quality

Status: done

---

## Story

As a PersonnaPress user generating social posts,
I want the social posts to enforce the same voice rules as the blog (banned jargon, banned openers, resolved tone/cadence, signature phrases, natural em-dash rewrites),
so that my brand voice is consistent across all five platforms and social quality matches blog quality.

As a PersonnaPress operator running on Anthropic,
I want social post generation to never fail with a JSON parse error due to token truncation,
so that the Anthropic path is as reliable as the Gemini path.

---

## Context and Motivation

A thorough audit of `generation_prompts.py`, `gemini.py`, and `anthropic_client.py` identified 18 gaps between blog and social post quality. This story closes all of them. They fall into three groups:

**Group 1: Critical bug (fix first)**
Anthropic social calls use `max_tokens=2048`. Standalone LinkedIn can be 2500 chars alone. With all 5 platforms plus JSON structure, output routinely needs 1800-2200 tokens. Truncation produces partial JSON that raises `ValueError` and fails the entire job. Blog generation uses `max(8192, ...)`. This is the most urgent fix.

**Group 2: Voice and quality gaps**
Social prompts receive raw BVP JSON and tell the model to figure out tone, cadence, jargon, and contractions itself. The blog resolves all of these into explicit instructions. Social posts also lack banned-jargon enforcement, banned-opener enforcement, passive-voice prohibition, and the specificity rule.

**Group 3: Structural and consistency gaps**
Threads gets no voice_brief injection. Blog-paired social (`_SOCIAL_PROMPT`) has no persona line and no `bvp_structure_hints`. Standalone LinkedIn has no hashtag instruction. Instagram and Facebook have no hard truncation. The anti-pattern hint is scoped under a "linkedin_post only" label. Em-dash instructions say "don't use it" rather than "rewrite naturally." The blog-paired X post has no minimum length and no structure guidance. The `_VOICE_BRIEF_PROMPT` instructs the model to use `--` as an em-dash substitute, which is also wrong per project rules.

**Project rule on dashes:** Neither em-dash (`—`) nor double-dash (`--`) should appear in generated copy. Both look artificial. The instruction to the model must always be to rewrite the sentence naturally, not to substitute any dash form. The code-level strip (`replace("—", ", ")`) stays as a safety net but the prompt must prevent the model from emitting either form in the first place.

---

## Acceptance Criteria

**AC 1 (Critical bug): Anthropic max_tokens raised**
- `generate_social` in `anthropic_client.py` uses `max_tokens=4096`
- `generate_social_standalone` in `anthropic_client.py` uses `max_tokens=6144`
- `check_fidelity` max_tokens is unchanged (2048 is sufficient for its short JSON response)

**AC 2: Resolved tone + cadence injected into social prompts**
- Both `generate_social` and `generate_social_standalone` in both `gemini.py` and `anthropic_client.py` resolve `tone_list` and `cadence_instruction` from BVP the same way `generate_blog` does
- Both social prompt templates receive a `{social_universal_rules}` block that includes the resolved tone and cadence as explicit instructions (not raw JSON)

**AC 3: Banned jargon enforced in social posts**
- Both `generate_social` and `generate_social_standalone` resolve `banned_jargon_list` from `bvp.get("banned_jargon", [])` as a comma-separated string
- The `{social_universal_rules}` block includes: `BANNED WORDS, do not use anywhere in any post: {banned_jargon_list}`
- When BVP has no banned_jargon, the instruction is omitted (not "none specified")

**AC 4: Banned opener phrases enforced in social posts**
- Both social prompt templates include a condensed banned-openers block in `{social_universal_rules}`:
  - "In today's fast-paced world"
  - "In today's digital landscape"
  - "As we all know"
  - "It's no secret that"

**AC 5: Contractions rule enforced in social posts**
- `{social_universal_rules}` includes the same contractions rule as the blog: use if tone is casual/friendly/conversational/approachable; avoid if professional/formal/authoritative/corporate
- The rule is resolved at prompt-build time using the same tone_list logic

**AC 6: Passive voice prohibition in social posts**
- `{social_universal_rules}` includes: "Never use passive voice when active voice is possible."

**AC 7: Specificity rule in social posts**
- Both `generate_social` and `generate_social_standalone` resolve `specificity_rule` from `bvp.get("specificity_preference")`
- When `specificity_preference == "concrete_numbers"`: inject "All quantifiable claims MUST use specific numbers, not vague phrases like 'many' or 'a lot'"
- Otherwise: omit (not injected)
- Injected as part of `{social_universal_rules}`

**AC 8: Em-dash and double-dash rewrite instructions upgraded everywhere**
- All 5 platform descriptions in `_SOCIAL_PROMPT` replace "No em-dash character (—) anywhere" with the natural-rewrite instruction
- All 5 platform descriptions in `_SOCIAL_STANDALONE_PROMPT` do the same
- The exact instruction to use: "Never use an em-dash (—) or double-dash (--). Rewrite any sentence that would need one so it flows naturally without any dash form."
- `_VOICE_BRIEF_PROMPT` changes "Use plain dashes (--) or restructure the sentence instead" to "Rewrite the sentence to flow naturally without any dash form instead."
- `_build_voice_injection`: `replace("—", "--")` on sig phrases and anchors changes to `replace("—", ", ")`
- `_build_standalone_voice_injection`: same change

**AC 9: Threads voice injection added**
- Both `generate_social` and `generate_social_standalone` in both LLM integration files inject `threads_voice_section` when `voice_brief` is present
- `threads_voice_section` uses only the first two sentences of `voice_brief` (split on `. `, take first 2, rejoin)
- Injected as: `"\nTHREADS BRAND VOICE (apply to threads_post only -- keep it raw and unpolished; voice is for register, not formality):\n{brief_excerpt}\n"`

**AC 10: `bvp_structure_hints` added to blog-paired `_SOCIAL_PROMPT`**
- `_SOCIAL_PROMPT` receives a `{bvp_structure_hints}` placeholder
- `generate_social` in both LLM files calls `_build_standalone_voice_injection(brand_voice_profile or {})` and passes the result as `bvp_structure_hints`

**AC 11: Anti-pattern scope fixed in `_build_standalone_voice_injection`**
- Anti-pattern is moved above the "apply to linkedin_post only" section header
- It becomes a global constraint labeled: `ANTI-PATTERN (apply to all posts -- never write text like this): "{anti_pattern}"`
- LinkedIn-specific hints (hook preference, CTA, structure, sig phrases) remain under "apply to linkedin_post only"

**AC 12: Hard truncation for Instagram and Facebook**
- Both `generate_social` and `generate_social_standalone` in both LLM files add hard truncation:
  - `instagram_caption`: truncate to 599 chars + `…` if over 600
  - `facebook_post`: truncate to 799 chars + `…` if over 800
- Both use `logger.warning` before truncating (matching the existing pattern for X/LinkedIn/Threads)

**AC 13: Blog-paired X post upgraded with minimum length and structure**
- `_SOCIAL_PROMPT` x_post description updated to:
  - Minimum 70 characters
  - Structure: Hook (first ~70 chars) then Value (1 core insight or 2-3 short bullets) then Proof (a number or outcome from the brain dump if available) then Link-nudge ("Full piece linked in bio" or "Link in first comment")
  - No "Read the full guide" CTA -- write the nudge as one short line, not a promotional pitch

**AC 14: Standalone LinkedIn hashtag instruction added**
- `_SOCIAL_STANDALONE_PROMPT` linkedin_post description updated to include: "End with 3-5 relevant professional hashtags on their own line at the very bottom (format: #hashtag #hashtag)." -- matching the blog-paired LinkedIn instruction

**AC 15: `_SOCIAL_PROMPT` gets a persona line**
- `_SOCIAL_PROMPT` opens with: "You are an expert social media copywriter writing platform-native posts that complement a blog article."

**AC 16: No regressions**
- All existing tests in `tests/test_generation_prompts.py`, `tests/test_gemini.py`, `tests/test_anthropic_client.py` pass
- New tests cover: max_tokens values (AC 1), at least one banned-jargon check per platform path (AC 3), threads_voice_section injection (AC 9), hard truncation for IG and FB (AC 12), anti-pattern global scope (AC 11)

---

## Tasks / Subtasks

- [x] Task 1: Fix Anthropic max_tokens (AC 1) -- do this first
  - [x] In `anthropic_client.py` `generate_social` line 317: change `max_tokens=2048` to `max_tokens=4096`
  - [x] In `anthropic_client.py` `generate_social_standalone` line 430: change `max_tokens=2048` to `max_tokens=6144`
  - [x] Leave `check_fidelity` line 226 at `max_tokens=2048` (unchanged)

- [x] Task 2: Add `_build_social_universal_rules` helper to `generation_prompts.py` (ACs 2-7)
  - [x] New function signature: `_build_social_universal_rules(bvp: dict, tone_list: str, cadence_instruction: str) -> str`
  - [x] Returns a `WRITING RULES` block with: tone, cadence, contractions, passive voice, specificity (if concrete_numbers), banned jargon (if any), banned openers (always), dash ban (always)
  - [x] Contractions rule: if any of `["casual", "friendly", "conversational", "approachable"]` is in the resolved `tone_list.lower()`, use contractions; if any of `["professional", "formal", "authoritative", "corporate"]` is in it, avoid contractions; else omit
  - [x] Banned jargon: only inject if the list is non-empty after joining
  - [x] Specificity rule: only inject if `bvp.get("specificity_preference") == "concrete_numbers"`
  - [x] Dash ban: always inject: "Never use an em-dash (—) or double-dash (--). Rewrite any sentence that would need one so it flows naturally without any dash form."

- [x] Task 3: Fix dash handling in existing helpers (AC 8)
  - [x] In `_build_voice_injection`: change all `.replace("—", "--")` to `.replace("—", ", ")` -- lines 65, 75, 61
  - [x] In `_build_standalone_voice_injection`: change all `.replace("—", "--")` to `.replace("—", ", ")` -- lines 364, 361
  - [x] In `_VOICE_BRIEF_PROMPT` (line 113): change "Use plain dashes (--) or restructure the sentence instead." to "Rewrite the sentence to flow naturally without any dash form instead."

- [x] Task 4: Fix anti-pattern scope in `_build_standalone_voice_injection` (AC 11)
  - [x] Extract anti-pattern from the `hints` list
  - [x] Emit anti-pattern as a standalone block before the LinkedIn section:
    `f'\nANTI-PATTERN (apply to all posts -- never write text like this): "{anti_pattern}"\n'`
  - [x] Keep sig phrases and other structural hints inside the "apply to linkedin_post only" section

- [x] Task 5: Update `_SOCIAL_PROMPT` template in `generation_prompts.py` (ACs 10, 13, 15)
  - [x] Add persona line at the top: "You are an expert social media copywriter writing platform-native posts that complement a blog article."
  - [x] Add `{threads_voice_section}` placeholder after `{facebook_voice_section}`
  - [x] Add `{bvp_structure_hints}` placeholder after `{threads_voice_section}`
  - [x] Add `{social_universal_rules}` placeholder before "BRAIN DUMP:"
  - [x] Update x_post description: add 70-char minimum and Hook/Value/Proof/Link-nudge structure
  - [x] Update all 5 platform em-dash instructions to the natural-rewrite form (AC 8)

- [x] Task 6: Update `_SOCIAL_STANDALONE_PROMPT` template in `generation_prompts.py` (ACs 8, 14)
  - [x] Add `{threads_voice_section}` placeholder after `{facebook_voice_section}`
  - [x] Add `{social_universal_rules}` placeholder before "BRAIN DUMP:"
  - [x] Add hashtag instruction to linkedin_post description (end with 3-5 hashtags)
  - [x] Update all 5 platform em-dash instructions to the natural-rewrite form (AC 8)

- [x] Task 7: Update `generate_social` in `gemini.py` (ACs 2, 3, 7, 9, 10, 12)
  - [x] Resolve `tone_list` and `cadence_instruction` from BVP (same pattern as `generate_blog` lines 231-243)
  - [x] Resolve `banned_jargon_list` from `bvp.get("banned_jargon", [])` (same as blog)
  - [x] Build `threads_voice_section`: extract first 2 sentences of `voice_brief` (split on ". ", take first 2, rejoin); wrap with the threads label
  - [x] Call `_build_standalone_voice_injection(brand_voice_profile or {})` and pass as `bvp_structure_hints`
  - [x] Call `_build_social_universal_rules(brand_voice_profile or {}, tone_list, cadence_instruction)` and pass as `social_universal_rules`
  - [x] Pass all new params to `_SOCIAL_PROMPT.format(...)`
  - [x] Add hard truncation for `instagram_caption` (>600) and `facebook_post` (>800) after existing truncation blocks

- [x] Task 8: Update `generate_social_standalone` in `gemini.py` (ACs 2, 3, 7, 9, 12)
  - [x] Same BVP resolution as Task 7
  - [x] Build and pass `threads_voice_section` and `social_universal_rules`
  - [x] Note: `bvp_structure_hints` already exists in this function
  - [x] Pass all new params to `_SOCIAL_STANDALONE_PROMPT.format(...)`
  - [x] Add hard truncation for `instagram_caption` (>600) and `facebook_post` (>800)

- [x] Task 9: Mirror Tasks 7 and 8 in `anthropic_client.py`
  - [x] Same changes as Tasks 7 and 8 for both `generate_social` and `generate_social_standalone`
  - [x] max_tokens changes are already done in Task 1

- [x] Task 10: Tests (AC 16)
  - [x] Verify `generate_social` in anthropic_client uses `max_tokens=4096`
  - [x] Verify `generate_social_standalone` in anthropic_client uses `max_tokens=6144`
  - [x] Test `_build_social_universal_rules` returns banned jargon block when BVP has jargon
  - [x] Test `_build_social_universal_rules` omits jargon block when list is empty
  - [x] Test `_build_social_universal_rules` contractions logic: professional tone → avoid, casual → use
  - [x] Test `threads_voice_section` is injected when voice_brief is present (mock generate_social, check prompt)
  - [x] Test hard truncation: instagram_caption at 601 chars gets truncated to 600; facebook_post at 801 chars gets truncated to 800 -- for both gemini.py and anthropic_client.py
  - [x] Test anti-pattern appears before "apply to linkedin_post only" in `_build_standalone_voice_injection` output

---

## Dev Notes

### Files to modify

| File | Type | What changes |
|------|------|-------------|
| `backend/app/integrations/generation_prompts.py` | UPDATE | Add `_build_social_universal_rules`, fix dash handling in 2 helpers, update `_VOICE_BRIEF_PROMPT`, update `_SOCIAL_PROMPT` (persona + 5 new placeholders + x_post structure + em-dash instructions), update `_SOCIAL_STANDALONE_PROMPT` (threads section + universal rules + LinkedIn hashtag + em-dash instructions), fix anti-pattern scope in `_build_standalone_voice_injection` |
| `backend/app/integrations/gemini.py` | UPDATE | `generate_social`: add BVP resolution + 3 new sections + pass to prompt; add IG/FB truncation. `generate_social_standalone`: same (bvp_structure_hints already exists; add others) |
| `backend/app/integrations/anthropic_client.py` | UPDATE | Same as gemini.py changes. Plus max_tokens fix in `generate_social` and `generate_social_standalone` |

No frontend changes. No DB migrations. No new endpoints. No schema changes.

### Current state of key code (read before editing)

**`_SOCIAL_PROMPT` current format call in `generate_social` (gemini.py:479-486 / anthropic_client.py:308-315):**
```python
prompt = _SOCIAL_PROMPT.format(
    bvp_json=bvp_json,
    linkedin_voice_section=linkedin_voice_section,
    instagram_voice_section=instagram_voice_section,
    facebook_voice_section=facebook_voice_section,
    brain_dump=brain_dump,
    blog_title=blog_title,
)
```
After this story, it gains: `threads_voice_section`, `bvp_structure_hints`, `social_universal_rules`.

**`_SOCIAL_STANDALONE_PROMPT` current format call in `generate_social_standalone` (gemini.py:597-605 / anthropic_client.py:421-429):**
```python
prompt = _SOCIAL_STANDALONE_PROMPT.format(
    bvp_json=bvp_json,
    linkedin_voice_section=linkedin_voice_section,
    instagram_voice_section=instagram_voice_section,
    facebook_voice_section=facebook_voice_section,
    bvp_structure_hints=bvp_structure_hints,
    brain_dump=brain_dump,
)
```
After this story, it gains: `threads_voice_section`, `social_universal_rules`.

**BVP resolution pattern from `generate_blog` in `gemini.py` (lines 231-244) -- replicate exactly:**
```python
if brand_voice_profile:
    tone_list = ", ".join(str(t) for t in brand_voice_profile.get("tone", []))
    cadence = brand_voice_profile.get("cadence") or {}
    avg_sentence_length = cadence.get("avg_sentence_length") or 15
    variation_pattern = str(cadence.get("variation_pattern") or "").strip()
    paragraph_structure = str(cadence.get("paragraph_structure") or "").strip()
    cadence_parts = [f"avg sentence length {avg_sentence_length} words"]
    if variation_pattern:
        cadence_parts.append(f'sentence variation: "{variation_pattern}"')
    if paragraph_structure:
        cadence_parts.append(f'paragraph structure: "{paragraph_structure}"')
    cadence_instruction = "; ".join(cadence_parts)
    banned_jargon_list = ", ".join(str(j) for j in brand_voice_profile.get("banned_jargon", []))
else:
    tone_list = "professional, clear, authoritative"
    cadence_instruction = "avg sentence length 15 words"
    banned_jargon_list = ""
```

**Existing truncation pattern (gemini.py:514-553) -- extend this block:**
```python
if len(data["x_post"]) > 280:
    ...truncate...
# LinkedIn truncation
# Instagram: currently only logger.warning -- ADD hard truncation here
# Facebook: currently only logger.warning -- ADD hard truncation here
if len(data["threads_post"]) > 500:
    ...truncate...
```

**`_build_standalone_voice_injection` current structure (generation_prompts.py:318-377):**
The `hints` list is built from: opening_pattern, closing_pattern, structure, sig phrases, anti-pattern.
All go into one block labeled "apply to linkedin_post only". Anti-pattern must be moved outside.

**`_build_voice_injection` dash lines to fix (generation_prompts.py):**
- Line 65: `phrases_clean = [p.replace("—", "--").replace(...)` → `replace("—", ", ")`
- Line 75: `anchors_clean = [s.replace("—", "--").replace(...)` → `replace("—", ", ")`
- Line 61: `anti_pattern = ((...) or "").strip().replace("—", "--")` → `replace("—", ", ")`

**`_build_standalone_voice_injection` dash lines to fix:**
- Line 361: `anti_pattern = ((...) or "").strip().replace("—", "--")` → `replace("—", ", ")`
- Line 364: `phrases_str = ", ".join(p.replace("—", "--")...)` → `replace("—", ", ")`

### Threads voice injection -- implementation detail

Extract first 2 sentences from `voice_brief`:
```python
if voice_brief:
    sentences = [s.strip() for s in voice_brief.split(". ") if s.strip()]
    brief_excerpt = ". ".join(sentences[:2])
    if brief_excerpt and not brief_excerpt.endswith("."):
        brief_excerpt += "."
    threads_voice_section = (
        "\nTHREADS BRAND VOICE (apply to threads_post only -- keep it raw and unpolished; "
        "voice is for register, not formality):\n"
        f"{brief_excerpt}\n"
    )
else:
    threads_voice_section = ""
```

### `_build_social_universal_rules` -- implementation sketch

```python
def _build_social_universal_rules(bvp: dict, tone_list: str, cadence_instruction: str) -> str:
    """Build the WRITING RULES block for social prompts.

    Resolves BVP fields into explicit instructions rather than leaving them
    as raw JSON for the model to interpret.
    """
    lines = [
        "WRITING RULES (apply to all five posts):",
        f"- Tone: {tone_list}",
        f"- Cadence: {cadence_instruction}",
    ]

    # Contractions rule
    tone_lower = tone_list.lower()
    casual_tones = {"casual", "friendly", "conversational", "approachable"}
    formal_tones = {"professional", "formal", "authoritative", "corporate"}
    if any(t in tone_lower for t in casual_tones):
        lines.append("- Contractions: use naturally throughout (don't, can't, I've, you'll, it's)")
    elif any(t in tone_lower for t in formal_tones):
        lines.append("- Contractions: avoid entirely")

    lines.append("- Never use passive voice when active voice is possible.")

    # Specificity rule
    if bvp.get("specificity_preference") == "concrete_numbers":
        lines.append(
            "- All quantifiable claims MUST use specific numbers, not vague phrases like 'many' or 'a lot'"
        )

    # Dash ban
    lines.append(
        "- Never use an em-dash (—) or double-dash (--). "
        "Rewrite any sentence that would need one so it flows naturally without any dash form."
    )

    # Banned jargon
    banned_jargon_list = ", ".join(str(j) for j in bvp.get("banned_jargon", []))
    if banned_jargon_list:
        lines.append(f"- BANNED WORDS, do not use anywhere: {banned_jargon_list}")

    # Banned openers
    lines.append(
        "- BANNED OPENERS, never begin any post with: "
        '"In today\'s fast-paced world", "In today\'s digital landscape", '
        '"As we all know", "It\'s no secret that"'
    )

    return "\n".join(lines)
```

### X post blog-paired upgrade -- exact new description

Replace the current x_post description in `_SOCIAL_PROMPT`:
```
"x_post": "<X post text, max 280 characters, tease the blog without duplicating it. No em-dash character (—) anywhere.>"
```
With:
```
"x_post": "<X post, 70-280 characters. Structure: Hook (first ~70 chars, stops the scroll) then Value (1 core insight from the blog) then Proof (a specific number or outcome from the brain dump if available) then Link-nudge (one short line: 'Full piece linked in bio' or 'Link in first comment' -- write it naturally, not as a promotional pitch). Never use an em-dash (—) or double-dash (--). Rewrite any sentence that would need one so it flows naturally without any dash form.>"
```

### `_VOICE_BRIEF_PROMPT` fix (generation_prompts.py line 113)

Current: `"Do NOT use em-dashes. Use plain dashes (--) or restructure the sentence instead."`
Change to: `"Do NOT use em-dashes or double-dashes (--). Rewrite the sentence to flow naturally without any dash form instead."`

### Truncation values

Per the story: Instagram hard cap = 600 chars, Facebook hard cap = 800 chars.
Pattern to follow (match existing X/LinkedIn style):
```python
ig_len = len(data["instagram_caption"])
if ig_len > 600:
    logger.warning(
        "generate_social: instagram_caption exceeded 600 chars (%d), truncating", ig_len,
    )
    data["instagram_caption"] = data["instagram_caption"][:599] + "…"

fb_len = len(data["facebook_post"])
if fb_len > 800:
    logger.warning(
        "generate_social: facebook_post exceeded 800 chars (%d), truncating", fb_len,
    )
    data["facebook_post"] = data["facebook_post"][:799] + "…"
```
Note: the existing `if not (150 <= ig_len <= 600)` warning logs can be removed once hard truncation is in place (they are redundant -- the truncation covers the upper bound, and a lower-bound warning for under 150 is still useful and can remain).

### Project constraints

- No em-dashes or double-dashes in any copy the system generates or in prompt instructions about copy style
- Brand name is PersonnaPress (double-n)
- All LLM provider changes must be made in BOTH `gemini.py` AND `anthropic_client.py` (they share `generation_prompts.py` templates but each implements the logic independently)
- `generation_prompts.py` is the single source of truth for prompt text -- never duplicate prompt strings in the integration files

### Recent related stories for pattern reference

- `3-14-social-standalone-prompt`: introduced `_SOCIAL_STANDALONE_PROMPT` and `_build_standalone_voice_injection`; established the bvp_structure_hints pattern
- `16-6-voice-signal-injection`: introduced sig phrases, voice anchors, anti-pattern injection -- the `_build_voice_injection` and `_build_standalone_voice_injection` functions
- `3-11-gemini-blog-prompt-human-quality`: introduced contractions, passive voice, specificity rules in the blog prompt -- replicate those patterns for social
- `3-22-strip-blog-compliance-report-trailer`: established the em-dash strip as a safety net; the prompt instruction is the primary defense

### Testing approach

Tests live in `backend/tests/`. Look at existing test files:
- `test_generation_prompts.py`: unit tests for `_build_voice_injection`, `_build_standalone_voice_injection`
- `test_gemini.py`: integration-style tests for `generate_social` and `generate_social_standalone` using `AsyncMock` on the Gemini client
- `test_anthropic_client.py`: same for Anthropic

New tests should follow existing mock patterns. For max_tokens, inspect the mock call args:
```python
mock_create.assert_called_once()
call_kwargs = mock_create.call_args[1]
assert call_kwargs["max_tokens"] == 4096
```

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — no blocking issues encountered.

### Completion Notes List

- Fixed missing `_build_social_universal_rules` import in `gemini.py` (was omitted from the import block during implementation).
- Three inline test JSON fixtures in `test_gemini_generation.py` (standalone LinkedIn truncation tests + emdash test) were missing the 3 new required keys (`instagram_caption`, `facebook_post`, `threads_post`); added them.
- Two `check_fidelity` bypass tests in both test files were missing `authored_passages_preserved: True` from their expected dict (pre-existing gap from a prior story); fixed to match actual bypass return value.
- All 171 tests in the three generation test files pass. The two spacy-dependent test files (`test_stylometry.py`, `test_voice_extraction.py`) fail with `ModuleNotFoundError: No module named 'spacy'` — this is a pre-existing environment issue unrelated to this story.

### File List

- `backend/app/integrations/generation_prompts.py`
- `backend/app/integrations/gemini.py`
- `backend/app/integrations/anthropic_client.py`
- `backend/tests/test_generation_prompts.py`
- `backend/tests/test_gemini_generation.py`
- `backend/tests/test_anthropic_generation.py`

### Review Findings

- [x] [Review][Patch] AC 3: missing "in any post" in BANNED WORDS instruction [`generation_prompts.py:153`] — fixed: "do not use anywhere" → "do not use anywhere in any post"
- [x] [Review][Defer] `tone_list` is empty string when BVP `tone=[]` [`generation_prompts.py:127`] — deferred, pre-existing pattern inherited from generate_blog
- [x] [Review][Defer] Voice-brief sentence splitting on `". "` is fragile (abbreviations, newlines) [`anthropic_client.py`, `gemini.py`] — deferred, by-spec design from dev notes
- [x] [Review][Defer] `threads_post` truncation is warning-only unlike IG/FB — deferred, outside this story's scope
- [x] [Review][Defer] `--` in prompt structural text (Threads voice section label etc.) — deferred, pervasive pre-existing pattern throughout prompt templates
- [x] [Review][Defer] `avg_sentence_length=0` silently replaced by 15 via `or 15` — deferred, same as generate_blog path, pre-existing
- [x] [Review][Defer] `_sanitize_json_str` in gemini.py still uses `replace("—","--")` — deferred, pre-existing, not touched by this diff
- [x] [Review][Defer] Contractions `if/elif` picks casual over formal on mixed-tone BVP — deferred, same design as blog generation, pre-existing

### Change Log

| Date | Change |
|------|--------|
| 2026-08-15 | Story implemented: 18 social-voice parity gaps closed, Anthropic max_tokens bug fixed, `_build_social_universal_rules` added, dash handling unified to `, ` replacement, anti-pattern scope made global, hard truncation added for IG/FB, Threads voice injection added to all 4 LLM functions, 171 tests passing |
| 2026-08-15 | Code review: 1 patch applied (BANNED WORDS "in any post" wording), 7 deferred, 16 dismissed |
