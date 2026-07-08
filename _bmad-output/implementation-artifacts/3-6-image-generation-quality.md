---
baseline_commit: e78c0205e6bcc074607fa0e3b6ac8d200589e4c2
---

# Story 3.6: Image Generation Quality — FLUX 1.1 Pro + Natural Language Prompts

Status: done

## Story

As a PersonnaPress user,
I want generated featured images to look consistently professional and relevant to my blog post,
So that I can publish without having to spend my 3 regeneration attempts correcting poor results.

## Context & Root Cause

Two problems cause inconsistent image quality in the current implementation:

**Problem 1 — Wrong model:** `backend/app/integrations/replicate.py` uses `black-forest-labs/flux-pro` (FLUX.1 [pro]). The newer `black-forest-labs/flux-1.1-pro` (FLUX 1.1 Pro) has significantly better prompt adherence, is 6x faster, and costs ~27% less ($0.04 vs $0.055/image). The Replicate API parameters are different between models — see Dev Notes for exact schema.

**Problem 2 — Keyword-dump prompts:** `_build_image_prompt()` in `backend/app/services/image.py` produces prompts like:
```
corporate editorial style, featured blog image for 'Title', photorealistic, high resolution, 16:9 aspect ratio, professional photography, no text overlay, clean background
```
FLUX uses a T5-XXL text encoder that was pre-trained on natural English. Comma-separated keyword lists are the wrong format — they give T5 less syntactic context to correctly weight descriptors. Natural sentences produce more consistent, better-composed images.

**What Gemini does (and does not do):** Gemini is NOT involved in image prompt generation. `_build_image_prompt()` is a pure Python function. There is no LLM call for the prompt. This story improves the Python prompt builder to output natural sentences — adding a Gemini call is out of scope.

## Acceptance Criteria

1. **Given** image generation runs for any campaign, **When** the Replicate API is called, **Then** the model used is `black-forest-labs/flux-1.1-pro`.

2. **Given** the Replicate API input dict, **When** it is logged or inspected, **Then** it contains `aspect_ratio: "custom"`, `width: 1200`, `height: 630`, and `output_format: "png"` — NOT the old flat `width`/`height` without `aspect_ratio`. (FLUX 1.1 Pro requires `aspect_ratio="custom"` to honour explicit pixel dimensions.)

3. **Given** a blog post with title "5 Ways to Scale Your SaaS Business", **When** `_build_image_prompt()` is called, **Then** the output is one or more complete English sentences describing the image, with no bare comma-separated keyword lists.

4. **Given** a client with `brand_voice_profile.tone = ["professional"]`, **When** `_build_image_prompt()` incorporates the tone, **Then** the tone appears as a complete descriptive sentence (e.g. `"The image has a clean, corporate editorial aesthetic."`) not as a comma-prepended keyword like `"corporate editorial style,"`.

5. **Given** the `generate_image()` function signature after this story, **When** it is reviewed, **Then** it no longer has `width` and `height` as top-level parameters; instead it passes them inside an `aspect_ratio="custom"` payload (see Dev Notes).

6. **Given** image regeneration is triggered, **When** `regenerate_image()` calls `_build_image_prompt()` and `_replicate_with_retry()`, **Then** it uses the identical updated payload as the primary generation path — no divergence between the two paths.

7. **Given** the retry logic in `_replicate_with_retry()`, **When** the updated code is reviewed, **Then** the `8s, 16s` exponential backoff is unchanged; only the model ID and input payload change.

---

## Tasks / Subtasks

### Group A — Model upgrade

- [x] Task A1: Change model ID in `backend/app/integrations/replicate.py`
  - [x] A1.1 Change `_FLUX_MODEL = "black-forest-labs/flux-pro"` → `_FLUX_MODEL = "black-forest-labs/flux-1.1-pro"`
  - [x] A1.2 Update the module docstring: change "FLUX.1 [pro]" → "FLUX 1.1 Pro"

### Group B — Update Replicate API input for FLUX 1.1 Pro schema

FLUX 1.1 Pro has a different parameter schema from the old `flux-pro`. Explicit `width` and `height` are only honoured when `aspect_ratio="custom"` is also set.

- [x] Task B1: Update `generate_image()` function in `backend/app/integrations/replicate.py`
  - [x] B1.1 The function signature stays the same: `async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str`
  - [x] B1.2 Replace the input dict:

    **Before:**
    ```python
    input={
        "prompt": prompt,
        "width": width,
        "height": height,
        "output_format": "png",
    }
    ```

    **After:**
    ```python
    input={
        "prompt": prompt,
        "aspect_ratio": "custom",
        "width": width,
        "height": height,
        "output_format": "png",
        "output_quality": 100,
        "safety_tolerance": 2,
    }
    ```

    - `aspect_ratio: "custom"` is required by FLUX 1.1 Pro to honour explicit `width`/`height` values
    - `output_quality: 100` has no effect on PNG (PNG is lossless) but is explicit
    - `safety_tolerance: 2` is the model default; explicit prevents surprises if Replicate changes defaults
    - Do NOT add `negative_prompt` — FLUX 1.1 Pro does not support it (confirmed from official schema)
    - Do NOT add `prompt_upsampling: true` — it uses an internal LLM to rewrite the prompt which makes output less predictable; leave it at the default `false`

### Group C — Rewrite `_build_image_prompt()` to natural language sentences

- [x] Task C1: Replace the keyword-dump builder in `backend/app/services/image.py`

  **Current function output format (wrong):**
  ```
  corporate editorial style, featured blog image for 'Title', photorealistic, high resolution, 16:9 aspect ratio, professional photography, no text overlay, clean background
  ```

  **Replace entire `_build_image_prompt` function with:**
  ```python
  def _build_image_prompt(blog_title: str, brand_voice_profile: dict | None) -> str:
      tone_sentence = ""
      if brand_voice_profile:
          tone_list = brand_voice_profile.get("tone", [])
          tone_map = {
              "professional": "clean, corporate editorial aesthetic",
              "casual": "warm, approachable lifestyle atmosphere",
              "formal": "minimalist, refined editorial look",
              "friendly": "inviting, human-centered composition",
              "authoritative": "bold, confident editorial presence",
              "conversational": "relaxed, accessible visual tone",
          }
          visual_tones = [tone_map.get(t.lower(), t) for t in tone_list[:2]]
          if visual_tones:
              combined = " and ".join(visual_tones)
              tone_sentence = f" The image has a {combined}."

      return (
          f"A professional editorial photograph for a blog post titled '{blog_title}'."
          f"{tone_sentence}"
          " The composition is clean, with no text overlays, watermarks, or logos."
          " Sharp focus, natural lighting, suitable as a 16:9 hero banner."
      )
  ```

  Key changes:
  - Title appears in a complete subject-verb sentence, not a label
  - Tone is expressed as a descriptive sentence, not a prefixed keyword
  - "photorealistic", "high resolution", "professional photography" replaced with equivalents in sentence form
  - "no text overlay" → "no text overlays, watermarks, or logos" (more specific, full sentence)
  - No trailing comma-list

### Group D — Verify both code paths use the same prompt and payload

- [x] Task D1: Verify `run_image_generation()` in `backend/app/services/image.py`
  - [x] D1.1 Confirm `prompt = _build_image_prompt(blog_title, brand_voice_profile)` is still the only call — no changes to the surrounding logic
  - [x] D1.2 Confirm `await _replicate_with_retry(prompt)` still calls `replicate_integration.generate_image(prompt)` with default `width=1200, height=630` — no caller-level changes needed

- [x] Task D2: Verify `regenerate_image()` in `backend/app/services/image.py`
  - [x] D2.1 Same confirmation — `_build_image_prompt()` and `_replicate_with_retry()` calls are identical to the primary path; no divergence

### Review Findings

- [x] [Review][Patch] Unknown tone keys produce grammatically broken sentence `"The image has a mysterious."` — fixed by using `f"{t} visual style"` fallback in `_build_image_prompt` and updating corresponding test assertion [`backend/app/services/image.py:43`, `backend/tests/services/test_image.py:266`]
- [x] [Review][Defer] Blog title with apostrophe/single-quote formats awkwardly inside wrapping quotes [`backend/app/services/image.py:49`] — deferred, pre-existing
- [x] [Review][Defer] No dimension validation for out-of-range width/height passed to FLUX 1.1 Pro [`backend/app/integrations/replicate.py`] — deferred, pre-existing
- [x] [Review][Defer] `brand_voice_profile` truthy check passes for non-dict types, `.get()` would raise AttributeError [`backend/app/services/image.py:33`] — deferred, pre-existing
- [x] [Review][Defer] Empty/whitespace-only blog title edge case in prompt context — deferred, pre-existing (fallback exists in caller)
- [x] [Review][Defer] `tone_list[:2]` on a non-list value (e.g. comma-separated string) returns characters not tones [`backend/app/services/image.py:43`] — deferred, pre-existing
- [x] [Review][Defer] `_build_image_prompt` tested via direct private import rather than public API surface [`backend/tests/services/test_image.py`] — deferred, pre-existing test pattern

---

## Dev Notes

### Official FLUX 1.1 Pro input schema on Replicate (from https://replicate.com/black-forest-labs/flux-1.1-pro/api/schema)

```json
{
  "type": "object",
  "title": "Input",
  "required": ["prompt"],
  "properties": {
    "seed":             { "type": "integer", "description": "Set for reproducible generation" },
    "prompt":           { "type": "string", "description": "Text prompt for image generation" },
    "aspect_ratio":     { "enum": ["custom","1:1","16:9","3:2","2:3","4:5","5:4","9:16","3:4","4:3"], "default": "1:1" },
    "width":            { "type": "integer", "min": 256, "max": 1440, "description": "Only used when aspect_ratio=custom. Must be multiple of 32 (rounded automatically)." },
    "height":           { "type": "integer", "min": 256, "max": 1440, "description": "Only used when aspect_ratio=custom. Must be multiple of 32 (rounded automatically)." },
    "output_format":    { "enum": ["webp","jpg","png"], "default": "webp" },
    "output_quality":   { "type": "integer", "min": 0, "max": 100, "default": 80, "description": "Not relevant for PNG (lossless)" },
    "safety_tolerance": { "type": "integer", "min": 1, "max": 6, "default": 2 },
    "prompt_upsampling":{ "type": "boolean", "default": false, "description": "Uses an internal LLM to expand/modify the prompt for creative variation" },
    "image_prompt":     { "type": "string", "format": "uri", "description": "Image URL for Flux Redux img2img mode — not used here" }
  }
}
```

**Critical notes from official schema:**
- `negative_prompt` is NOT a parameter — do not add it
- `output_format` defaults to `"webp"` — must explicitly set `"png"` to keep current behaviour
- `width` and `height` are IGNORED unless `aspect_ratio="custom"` is also set
- 1200 and 630 are not multiples of 32, but the schema says they will be "rounded to nearest multiple of 32" automatically — this is acceptable (FLUX will produce 1216x640 or similar)
- `prompt_upsampling=true` rewrites the prompt via an internal LLM — intentionally left `false` for predictability

### Differences between old `flux-pro` and new `flux-1.1-pro`

| Parameter        | `flux-pro` (old)       | `flux-1.1-pro` (new)           |
|------------------|------------------------|--------------------------------|
| `width`/`height` | Top-level, always used | Only used when `aspect_ratio="custom"` |
| `aspect_ratio`   | Not supported          | Required for non-square output |
| `negative_prompt`| Supported              | NOT supported                  |
| `output_format`  | Supported (default png)| Supported (default webp!)      |
| `prompt_upsampling` | Not supported       | Supported (default false)      |
| Cost per image   | ~$0.055               | ~$0.04                         |
| Generation speed | Baseline               | ~6x faster                     |

### Why natural sentences beat keyword dumps for FLUX

FLUX uses a T5-XXL text encoder. T5 was pre-trained on full natural-language text (Common Crawl, C4, Wikipedia etc.). When given `"photorealistic, high resolution, 16:9 aspect ratio"`, T5 processes these as disconnected tokens with minimal syntactic structure. When given `"A professional editorial photograph ... suitable as a 16:9 hero banner."`, T5 can assign proper noun, verb, and adjective roles, producing more precise visual grounding.

This is the highest-impact change in the story for output consistency.

### AR-19 compliance

AR-19: `services/image.py` is the ONLY place that calls `integrations/replicate.py`. This story does not introduce any new callers. `_build_image_prompt` stays in `services/image.py`; `generate_image` stays in `integrations/replicate.py`.

### Before / after prompt example

**Before:**
```
corporate editorial style, featured blog image for '5 Ways to Scale Your SaaS Business', photorealistic, high resolution, 16:9 aspect ratio, professional photography, no text overlay, clean background
```

**After:**
```
A professional editorial photograph for a blog post titled '5 Ways to Scale Your SaaS Business'. The image has a clean, corporate editorial aesthetic. The composition is clean, with no text overlays, watermarks, or logos. Sharp focus, natural lighting, suitable as a 16:9 hero banner.
```

### Test verification

After implementing, run a real end-to-end campaign generation and check:
1. The Replicate call logs show `flux-1.1-pro` as the model
2. The generated image looks relevant to the blog title
3. The Replicate dashboard shows the new model in usage logs
4. `backend/tests/services/test_image.py` mocks `replicate_integration.generate_image` — confirm tests still pass after the `_build_image_prompt` changes (the prompt content changed, but if tests assert on the mock call count, they will pass; if they assert exact prompt strings, update those assertions)

---

## Dev Agent Record

### Implementation Notes

- Group A+B: Updated `replicate.py` — model ID to `black-forest-labs/flux-1.1-pro`, module docstring, and `generate_image()` input dict now includes `aspect_ratio: "custom"`, `output_quality: 100`, `safety_tolerance: 2` per official FLUX 1.1 Pro schema.
- Group C: Replaced keyword-dump `_build_image_prompt()` in `image.py` with natural-sentence version using T5-friendly prose. Tone map expanded with fuller descriptors; tone appears as `"The image has a {combined}."` sentence, not a comma-prefixed keyword.
- Group D: Verified both `run_image_generation()` and `regenerate_image()` call `_build_image_prompt()` then `_replicate_with_retry()` identically — no divergence. No caller-level changes needed.
- Ruff auto-fixed pre-existing unused imports: `Subscription` from `image.py`, `datetime`/`timezone` from `test_image.py`.
- 6 new unit tests added for `_build_image_prompt` covering: no brand voice, professional tone, two tones joined, unknown tone verbatim, empty tone list, and three-tone truncation.
- All 11 tests pass; no regressions introduced.

### Completion Notes

All ACs satisfied:
1. Model is `black-forest-labs/flux-1.1-pro` ✅
2. Input dict contains `aspect_ratio: "custom"`, `width: 1200`, `height: 630`, `output_format: "png"` ✅
3. `_build_image_prompt("5 Ways to Scale Your SaaS Business", None)` returns natural sentences ✅
4. Professional tone appears as `"The image has a clean, corporate editorial aesthetic."` ✅
5. `generate_image()` signature unchanged; width/height passed inside `aspect_ratio="custom"` payload ✅
6. `regenerate_image()` uses identical prompt and payload path ✅
7. `8s, 16s` backoff in `_replicate_with_retry()` unchanged ✅

---

## File List

- `backend/app/integrations/replicate.py` — model ID, docstring, and input dict updated
- `backend/app/services/image.py` — `_build_image_prompt()` rewritten; unused `Subscription` import removed
- `backend/tests/services/test_image.py` — 6 new `_build_image_prompt` unit tests added; unused `datetime`/`timezone` imports removed

---

## Change Log

- 2026-07-08: Upgraded Replicate model from `flux-pro` to `flux-1.1-pro`; updated API input schema with `aspect_ratio="custom"`, `output_quality=100`, `safety_tolerance=2`; rewrote `_build_image_prompt()` to produce natural-language sentences for T5-XXL; added 6 unit tests for prompt builder.

---

Status: done
