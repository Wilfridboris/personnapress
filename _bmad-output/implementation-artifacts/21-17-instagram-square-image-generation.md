---
baseline_commit: 0c1db2e
---

# Story 21.17: Instagram-Ready Image Generation (Square)

Status: done

**Depends on:** None. Can ship independently of 21-15 and 21-16.

---

## Story

As a PersonnaPress user publishing to Instagram,
I want my campaign image to look native on Instagram,
so that my post doesn't appear letterboxed or awkwardly cropped.

---

## Context and Motivation

Today PersonnaPress generates one image at 1200x630 (16:9 landscape), composed like a "hero banner." Instagram is a square-native platform (1:1 ratio). When this landscape image lands on Instagram, Meta either letterboxes it with white bars or auto-crops it in unpredictable ways depending on feed context.

**The fix is simpler than it sounds:** generate the image at 1080x1080 (square) instead of 1200x630, and update the prompt so the AI composes with a centered subject and safe margins on all sides. Because all platforms (blog, X, LinkedIn, Facebook) display images using `object-fit: cover` or their own cropping logic, a well-composed centered square image looks correct everywhere -- platforms crop to their own display ratio from center.

No second image generation. No new DB column. No crop code. No new publishing logic. Just a dimension change and a prompt update.

**Key constraint that makes this work:** the image prompt must NOT say "16:9 hero banner" or "wide landscape." If the AI composes for landscape, center-cropping to square chops the left and right edges of the subject. With a centered-subject prompt, center-cropping to any ratio looks natural.

---

## Acceptance Criteria

### AC 1: Image generated at 1080x1080 (square)

**Given** a campaign triggers image generation,
**When** the image provider is called,
**Then** the image is generated at 1080x1080 pixels (1:1 ratio).

**Given** the FLUX Replicate model is configured (default),
**When** `generate_image` is called,
**Then** the input payload uses `width=1080, height=1080` (FLUX already supports custom width/height -- no new code needed, just change the call-site defaults).

**Given** a non-FLUX Replicate model is configured,
**When** `generate_image` is called,
**Then** the input payload uses `aspect_ratio="1:1"` instead of `"16:9"`.

**Given** the Gemini Imagen provider is configured,
**When** `generate_image` is called,
**Then** the request uses `aspectRatio: "1:1"` instead of `"16:9"`.

### AC 2: Image prompt uses centered-subject composition

**Given** `_build_image_prompt` builds the visual prompt,
**When** the prompt is returned,
**Then** it does NOT contain "16:9", "hero banner", "wide", or "landscape" aspect references.
**And** it instructs the model to place the main subject in the center of the frame with safe margins on all sides.

### AC 3: Existing platforms unaffected

**Given** the image is now 1080x1080,
**When** it is stored in Supabase and `campaign.image_url` is set,
**Then** the blog approval gate, X publishing, LinkedIn publishing, Facebook publishing, and GitHub publishing all continue to use `campaign.image_url` unchanged -- no code changes in those paths.

**Given** the blog hero renders in the frontend,
**When** it displays the square image in a 16:9 container,
**Then** the CSS `object-fit: cover` centers the image and fills the container (existing behavior -- no CSS change needed).

### AC 4: Instagram receives a native square image

**Given** a campaign with `campaign.image_url` set and Instagram connected,
**When** publishing to Instagram,
**Then** `publish_instagram_feed_post` is called with `image_url=campaign.image_url` (unchanged).
**And** Meta receives a 1080x1080 image, which it displays natively without letterboxing.

No code change to the Instagram publishing path -- this AC is satisfied automatically by AC 1 and AC 2.

### AC 5: Approval gate renders image correctly at new dimensions

**Given** a campaign image is displayed in `ImagePanel`,
**When** the image is 1080x1080,
**Then** the image container uses `object-fit: cover` within its existing 16:9 container (no change to the container ratio).
**And** the centered-subject composition (enforced by the updated prompt) means the subject fills the visible crop naturally -- no awkward framing in the approval gate.

**Do NOT change the ImagePanel container from 16:9 to 1:1.** Changing the container ratio would cause all existing 16:9 campaign images (pre-21-17) to render pillarboxed (white bars on top and bottom) in the approval gate -- a visual regression for all past campaigns. The 16:9 container with `object-fit: cover` handles both ratios gracefully.

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/services/image.py` | `_build_image_prompt`: remove "16:9 hero banner" / "wide" / "landscape" language; add centered-subject composition instruction. |
| `backend/app/integrations/replicate.py` | Change default params from `width=1200, height=630` to `width=1080, height=1080`. Non-FLUX branch: change `aspect_ratio` from `"16:9"` to `"1:1"`. |
| `backend/app/integrations/gemini_image.py` | Change `"aspectRatio": "16:9"` to `"aspectRatio": "1:1"`. |

**No frontend files change.** No DB migration, no new column, no publishing changes, no schema changes. `ImagePanel.tsx` keeps its existing 16:9 container -- `object-fit: cover` handles the square image correctly.

---

## Dev Notes

### Image prompt change (`image.py` `_build_image_prompt`)

Current language to REMOVE (any variant of):
- "suitable as a 16:9 hero banner"
- "wide landscape composition"
- "horizontal format"

Replace with:
```
Center the main subject in the frame with generous safe margins on all sides.
The composition should work equally well cropped to any aspect ratio.
Square format (1:1).
```

The rest of the prompt (tone, style, brand colors, subject matter derived from brain dump) stays unchanged.

### `replicate.py` -- change defaults

The function signature is currently:
```python
async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str:
```

Change to:
```python
async def generate_image(prompt: str, width: int = 1080, height: int = 1080) -> str:
```

FLUX branch already reads `width` and `height` from params -- no logic change, just default values.

Non-FLUX branch currently hardcodes `"aspect_ratio": "16:9"`. Change to `"aspect_ratio": "1:1"`.

The non-FLUX branch does not use `width`/`height` -- leave that as-is for now. The `aspect_ratio` string is the only change in that branch.

### `gemini_image.py` -- change aspectRatio

```python
# Before
"parameters": {
    "sampleCount": 1,
    "aspectRatio": "16:9",
    ...
}

# After
"parameters": {
    "sampleCount": 1,
    "aspectRatio": "1:1",
    ...
}
```

### `ImagePanel.tsx` -- no change needed

Do NOT change the aspect ratio of the image container. The existing 16:9 container with `object-fit: cover` centers and crops the square image cleanly. Changing to `aspect-square` would break the approval gate for all pre-21-17 campaigns (16:9 images would show pillarboxed).

### OG image trade-off (known, acceptable)

`campaign.image_url` is also used as the OG meta image for the public blog article page. When someone shares a blog URL on LinkedIn or Twitter, those platforms fetch the OG image and render a link card. LinkedIn recommends 1.91:1; Twitter cards expect 2:1. After this story, the OG image is 1080x1080 square. Both platforms will auto-crop the OG image to their preferred ratio from center -- with a centered subject this looks fine in practice, but the link card will appear slightly tighter on the subject than before.

This is a known trade-off of the single-image approach. A future story could generate a separate 1200x630 image specifically for OG/link-card use while keeping the 1080x1080 for direct posting. Not in scope here.

### Why this is enough

The blog page renders the image with CSS. If the container is 16:9 and the image is 1:1, `object-fit: cover` centers and crops -- the centered subject (enforced by the prompt) fills the frame naturally. The user may notice that the blog hero is slightly tighter on the subject than before, which is actually an improvement for readability. X and LinkedIn display attached images using their own viewport logic; both handle square images without issues.

---

## Tests to Write / Update

### Backend

**`test_image.py`** or `test_image_service.py` (extend):
- `test_build_image_prompt_does_not_contain_16_9_reference` -- assert "16:9" and "hero banner" absent from returned prompt string.
- `test_build_image_prompt_contains_centered_subject_instruction` -- assert centered/safe-margin language present.

**`test_replicate.py`** (new or extend):
- `test_generate_image_default_dimensions_are_square` -- mock prediction, assert `width=1080, height=1080` in FLUX payload.
- `test_generate_image_non_flux_uses_1_1_aspect_ratio` -- mock non-FLUX prediction, assert `"aspect_ratio": "1:1"` in payload.

**`test_gemini_image.py`** (new or extend):
- `test_gemini_image_uses_1_1_aspect_ratio` -- mock Vertex call, assert `"aspectRatio": "1:1"` in parameters.

### Frontend

No frontend changes -- no new frontend tests required for this story. Existing `ImagePanel` tests serve as regression guards.

---

## Trade-offs Accepted

- **Blog hero is now square-native:** The 16:9 display in the blog is a CSS crop of the center of the image. With centered-subject composition this looks better than before (subject fills the frame), not worse. Old campaigns keep their existing 16:9 images.
- **X and LinkedIn link cards:** When X/LinkedIn generate a card preview from the blog URL, they fetch the OG image. The OG image is now square; X and LinkedIn will auto-crop to their card ratio (2:1 and 1.91:1 respectively). With a centered subject this is acceptable. For direct-posting via our API (which is what PersonnaPress does), both platforms handle square images fine.
- **Resolution:** 1080x1080 is Instagram's recommended upload resolution. It's slightly smaller total pixel count than 1200x630 (1.16M vs 0.76M px -- actually larger at 1.17M vs 0.76M). No quality regression.

## What is NOT in Scope

- Per-platform image variants stored separately (original approach, deferred indefinitely)
- Threads 9:16 vertical image variant -- future story
- LinkedIn 1.91:1 specific variant -- future story
- Retroactively regenerating images for existing campaigns
- OG image optimization for the public blog URL (separate from our direct-post publishing)

---

## Dev Agent Record

### Completion Notes

- `_build_image_prompt` updated: removed "suitable as a 16:9 hero banner" phrase; added centered-subject / safe-margins / Square format (1:1) instructions. Tone sentence and all other copy unchanged.
- `replicate.py` default dims changed from 1200x630 to 1080x1080. Non-FLUX `aspect_ratio` changed from "16:9" to "1:1".
- `gemini_image.py` `aspectRatio` changed from "16:9" to "1:1".
- No frontend changes, no DB migration, no publishing path changes -- all per spec.
- Existing test in `test_image.py` that asserted `"16:9 hero banner" in result` updated to assert absence.
- 5 new tests added (2 prompt tests in `test_image.py`, 2 replicate tests in `test_replicate.py`, 1 gemini test in new `test_gemini_image.py`). All 38 new+updated tests pass.

---

## File List

- `backend/app/services/image.py` (modified)
- `backend/app/integrations/replicate.py` (modified)
- `backend/app/integrations/gemini_image.py` (modified)
- `backend/tests/services/test_image.py` (modified)
- `backend/tests/integrations/test_replicate.py` (modified)
- `backend/tests/integrations/test_gemini_image.py` (new)

---

## Change Log

- 2026-08-14: Code review complete. 1 patch applied: `gemini_image.py` function signature updated from `width=1200, height=630` to `width=1080, height=1080` (signature now consistent with square output). All 38 tests pass. Deferred: non-FLUX silent drop of caller-supplied dims (by design per spec), FLUX bypass via explicit dims (by design), brand-voice tone injection of aspect keywords (out of scope). Dismissed: prompt "Square format (1:1)" text (spec-prescribed), "wide" assertion breadth (acceptable), pre-existing prompt injection/module-caching issues.
