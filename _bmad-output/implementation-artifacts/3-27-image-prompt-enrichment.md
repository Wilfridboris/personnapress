---
baseline_commit: 1d6b543
---

# Story 3.27: Image Prompt Enrichment

Status: done

---

## Story

As a PersonnaPress user generating a campaign image,
I want the image AI to receive the article's keyword, audience, and a brief content summary in addition to the title,
so that the generated image reflects what the article is actually about rather than just its headline phrasing.

As a PersonnaPress user regenerating an image on a social-only campaign,
I want the regeneration to work the same as the initial generation,
so that clicking Regenerate does not produce a blank "Untitled" brief that wastes a regeneration credit.

---

## Context and Motivation

`_build_image_prompt` in `services/image.py` constructs a 6-sentence prompt from just two inputs: the blog H1 title and up to 2 tone words from the BVP. Everything else is ignored. The image AI has no idea what the post is about beyond its headline.

Three specific gaps:

**Gap 1: Thin content brief**
The current prompt:
```
A professional editorial image for the article titled 'How to Scale Your SaaS Without Burning Out'.
The image has a clean, corporate editorial aesthetic.
The composition is clean, with no text overlays, watermarks, or logos.
...
```
The image AI cannot distinguish "SaaS scaling" from "burnout wellness" from this brief alone. The title alone is not enough for a meaningful image. What would help: the target keyword (topic specificity), target audience (scene composition), and the excerpt/TL;DR (concrete hook to visualize).

**Gap 2: Wrong social fallback**
`run_image_generation` in `services/image.py` (lines 184-186) uses `x_post[:120].split("\n")[0]` as the fallback when `blog_html` is None (social-only campaigns). The X post is a hook/tease designed to stop the scroll -- not a content description. It is the worst field for an image brief. Better priority: `linkedin_post[:200]` (descriptive and informative), then `brain_dump[:200]` (the source of truth), then "Untitled".

**Gap 3: `regenerate_image` has no social fallback**
`regenerate_image` (lines 357-361) reads only `campaign.blog_html`. If `blog_html` is None, `h1_match` is None, `blog_title` becomes "Untitled", and the user wastes a regeneration credit on a blank brief. The same fallback logic from `run_image_generation` was never ported here.

---

## Acceptance Criteria

**AC 1: `_build_image_prompt` signature extended**
- `_build_image_prompt(blog_title, brand_voice_profile)` gains two optional parameters:
  - `target_keyword: str | None = None`
  - `target_audience: str | None = None`
  - `content_excerpt: str | None = None`
- All existing callers compile and pass tests with no argument changes (new params default to None)

**AC 2: Image prompt enriched with keyword**
- When `target_keyword` is provided, the prompt includes: "The subject of the article is [target_keyword]."
- This sentence is inserted after the title sentence and before the tone sentence

**AC 3: Image prompt enriched with audience**
- When `target_audience` is provided, the prompt includes: "The intended audience is [target_audience]."
- This sentence is inserted after the keyword sentence (or after the title sentence if no keyword)

**AC 4: Image prompt enriched with content excerpt**
- When `content_excerpt` is provided (max 200 chars used), the prompt includes: "The article covers: [excerpt]."
- This sentence is inserted after the audience sentence (or the last injected sentence if others are absent)
- `content_excerpt` is capped at 200 chars before injection to prevent prompt bloat

**AC 5: `run_image_generation` passes enrichment fields**
- `run_image_generation` passes `target_keyword=campaign.target_keyword`, `target_audience=campaign.target_audience`, `content_excerpt=campaign.excerpt` to `_build_image_prompt`
- `campaign.excerpt` is the pre-computed excerpt column (set by `_extract_excerpt` during text generation); no new DB query is needed

**AC 6: Social-only fallback fixed in `run_image_generation`**
- When `campaign.blog_html` is None, fallback priority order:
  1. `campaign.linkedin_post[:200].split("\n")[0]` if non-empty after strip
  2. `campaign.brain_dump[:200].split("\n")[0]` if non-empty after strip
  3. `"Untitled"`
- No longer uses `x_post` for the image subject

**AC 7: `regenerate_image` gets the social fallback**
- `regenerate_image` mirrors the fallback logic from `run_image_generation`:
  - When `campaign.blog_html` is None, apply the same priority order as AC 6
- `regenerate_image` also passes `target_keyword`, `target_audience`, and `content_excerpt` to `_build_image_prompt`

**AC 8: `generate_image_for_roadmap_campaign` unchanged**
- This function receives a `title_hint` string (computed by the caller) and calls `_build_image_prompt(blog_title, brand_voice_profile)` with only those two args
- No change needed: roadmap images use a caller-provided title hint, not a campaign record
- Verify the function still compiles and passes existing tests

**AC 9: No regressions**
- All existing tests pass
- New tests cover: enriched prompt contains keyword sentence (AC 2), enriched prompt contains audience sentence (AC 3), enriched prompt contains excerpt sentence capped at 200 chars (AC 4), social fallback priority order (AC 6 -- linkedin first, then brain_dump, then Untitled), `regenerate_image` social fallback (AC 7)

---

## Tasks / Subtasks

- [x] Task 1: Extend `_build_image_prompt` signature and body (ACs 1-4)
  - [x] Add `target_keyword: str | None = None`, `target_audience: str | None = None`, `content_excerpt: str | None = None` parameters
  - [x] Build enrichment sentences conditionally and insert in the right order
  - [x] Cap `content_excerpt` at 200 chars before use
  - [x] Keep all existing logic unchanged (tone_sentence, composition sentences)

- [x] Task 2: Update `run_image_generation` to pass enrichment fields (ACs 5, 6)
  - [x] Pass `target_keyword`, `target_audience`, `content_excerpt` to `_build_image_prompt` call
  - [x] Fix the social-only fallback to use LinkedIn then brain_dump then "Untitled"

- [x] Task 3: Update `regenerate_image` (ACs 7)
  - [x] Port social fallback (same pattern as `run_image_generation`)
  - [x] Pass `target_keyword`, `target_audience`, `content_excerpt` to `_build_image_prompt` call
  - [x] Load `campaign.target_keyword`, `campaign.target_audience`, `campaign.excerpt` from the already-loaded `campaign` object (no new query)

- [x] Task 4: Tests (AC 9)
  - [x] Test `_build_image_prompt` with keyword only -- sentence present in output
  - [x] Test `_build_image_prompt` with audience only -- sentence present in output
  - [x] Test `_build_image_prompt` with excerpt > 200 chars -- capped in output
  - [x] Test `_build_image_prompt` with no enrichment fields -- output identical to current behavior
  - [x] Test social fallback in `run_image_generation`: blog_html=None, linkedin_post present -- uses linkedin_post
  - [x] Test social fallback: blog_html=None, linkedin_post=None, brain_dump present -- uses brain_dump
  - [x] Test social fallback: all None -- uses "Untitled"
  - [x] Test `regenerate_image` social fallback: blog_html=None -- uses linkedin_post fallback, not "Untitled"

### Review Findings

- [x] [Review][Patch] Whitespace-only target_keyword/target_audience injects blank sentence into prompt [image.py:80-81]
- [x] [Review][Patch] No combined enrichment ordering test (all 3 fields + tone ordering) [test_image.py]
- [x] [Review][Patch] No test for regenerate_image brain_dump fallback path (AC 7) [test_image.py]
- [x] [Review][Defer] Duplicate social fallback logic in run_image_generation and regenerate_image — no shared helper [image.py:198-206, 390-397] — deferred, pre-existing pattern, DRY improvement
- [x] [Review][Defer] Unsanitized user content (target_keyword/audience/excerpt) injected into image prompt — prompt injection risk [image.py:80-83] — deferred, pre-existing pattern across all prompt builders
- [x] [Review][Defer] Social fallback blog_title can be up to 200 chars vs _build_image_alt's 125-char cap — long slugs in storage paths [image.py:202-204] — deferred, pre-existing, no functional failure
- [x] [Review][Defer] No integration test verifying target_keyword/audience/excerpt flow end-to-end through run_image_generation/regenerate_image [test_image.py] — deferred, covered by _build_image_prompt unit tests

---

## Dev Notes

### Files to modify

| File | Type | What changes |
|------|------|-------------|
| `backend/app/services/image.py` | UPDATE | `_build_image_prompt`: 3 new optional params + enrichment sentences. `run_image_generation`: pass enrichment + fix social fallback. `regenerate_image`: port social fallback + pass enrichment |

That is the only file that changes.

### Current state of `_build_image_prompt` (image.py:57-82)

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
        visual_tones = [tone_map.get(t.lower(), f"{t} visual style") for t in tone_list[:2]]
        if visual_tones:
            combined = " and ".join(visual_tones)
            tone_sentence = f" The image has a {combined}."

    return (
        f"A professional editorial image for the article titled '{blog_title}'."
        f"{tone_sentence}"
        " The composition is clean, with no text overlays, watermarks, or logos."
        " Sharp focus, natural lighting."
        " Center the main subject in the frame with generous safe margins on all sides."
        " The composition should work equally well cropped to any aspect ratio."
        " Square format (1:1)."
    )
```

After this story, the return statement becomes:
```python
    keyword_sentence = f" The subject of the article is {target_keyword}." if target_keyword else ""
    audience_sentence = f" The intended audience is {target_audience}." if target_audience else ""
    excerpt_text = (content_excerpt or "")[:200].strip()
    excerpt_sentence = f" The article covers: {excerpt_text}." if excerpt_text else ""

    return (
        f"A professional editorial image for the article titled '{blog_title}'."
        f"{keyword_sentence}"
        f"{audience_sentence}"
        f"{excerpt_sentence}"
        f"{tone_sentence}"
        " The composition is clean, with no text overlays, watermarks, or logos."
        " Sharp focus, natural lighting."
        " Center the main subject in the frame with generous safe margins on all sides."
        " The composition should work equally well cropped to any aspect ratio."
        " Square format (1:1)."
    )
```

### Current social fallback in `run_image_generation` (image.py:177-186)

```python
if campaign.blog_html:
    h1_match = re.search(...)
    blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
    blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"
else:
    # social_only campaign: derive image subject from x_post (first line, ≤120 chars)
    social_text = (campaign.x_post or campaign.linkedin_post or "").strip()
    blog_title = social_text[:120].split("\n")[0].strip() or "Untitled"
```

After this story:
```python
if campaign.blog_html:
    h1_match = re.search(...)
    blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
    blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"
else:
    # social_only campaign: derive image subject from best available text field
    linkedin_text = (campaign.linkedin_post or "").strip()
    brain_dump_text = (campaign.brain_dump or "").strip()
    if linkedin_text:
        blog_title = linkedin_text[:200].split("\n")[0].strip() or "Untitled"
    elif brain_dump_text:
        blog_title = brain_dump_text[:200].split("\n")[0].strip() or "Untitled"
    else:
        blog_title = "Untitled"
```

### Current `regenerate_image` title extraction (image.py:357-361)

```python
h1_match = re.search(
    r"<h1[^>]*>(.*?)</h1>", campaign.blog_html or "", re.IGNORECASE | re.DOTALL
)
blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"
prompt = _build_image_prompt(blog_title, brand_voice_profile)
```

After this story:
```python
if campaign.blog_html:
    h1_match = re.search(
        r"<h1[^>]*>(.*?)</h1>", campaign.blog_html, re.IGNORECASE | re.DOTALL
    )
    blog_title_raw = h1_match.group(1).strip() if h1_match else "Untitled"
    blog_title = re.sub(r"<[^>]+>", "", blog_title_raw).strip() or "Untitled"
else:
    linkedin_text = (campaign.linkedin_post or "").strip()
    brain_dump_text = (campaign.brain_dump or "").strip()
    if linkedin_text:
        blog_title = linkedin_text[:200].split("\n")[0].strip() or "Untitled"
    elif brain_dump_text:
        blog_title = brain_dump_text[:200].split("\n")[0].strip() or "Untitled"
    else:
        blog_title = "Untitled"
prompt = _build_image_prompt(
    blog_title,
    brand_voice_profile,
    target_keyword=campaign.target_keyword,
    target_audience=campaign.target_audience,
    content_excerpt=campaign.excerpt,
)
```

### Campaign model fields available (no new columns needed)

All enrichment fields already exist on the `Campaign` model:
- `campaign.target_keyword: str | None` -- set at campaign creation
- `campaign.target_audience: str | None` -- set at campaign creation
- `campaign.excerpt: str | None` -- set by `_extract_excerpt` during text generation (may be None for social-only campaigns)
- `campaign.brain_dump: str` -- always set
- `campaign.linkedin_post: str | None` -- set after generation

For `regenerate_image`, the `campaign` object is already loaded via `select(Campaign)` before the prompt is built. No new queries needed.

### Why excerpt not brain_dump for content_excerpt

`campaign.excerpt` is the pre-extracted editorial hook from the blog (max 240 chars, stripped of HTML). It is more concise and image-relevant than the raw brain_dump (which may be 10,000 chars of unstructured notes). For social-only campaigns, `excerpt` is None -- the enrichment simply does not fire (no excerpt sentence). The fallback title logic (AC 6) is separate from the enrichment (AC 4) and covers the image subject independently.

### Project constraints

- `generate_image_for_roadmap_campaign` (image.py:246-313) must NOT be changed. It uses a `title_hint` provided by the roadmap service, not a campaign record. Extending it to pass keyword/audience would require the roadmap service to fetch those fields per campaign, which is out of scope.
- No DB migrations.
- No changes to the image provider integrations (`gemini_image.py`, `replicate.py`).

### Testing approach

Tests likely live in `backend/tests/test_image_service.py` or similar. Use `AsyncMock` for the DB session and `patch` for `_img.generate_image` (returns a URL string). Focus on the prompt string that reaches the image provider:

```python
with patch("app.services.image._img.generate_image", new_callable=AsyncMock) as mock_gen:
    mock_gen.return_value = "https://example.com/image.png"
    ...
    prompt_used = mock_gen.call_args[0][0]
    assert "The subject of the article is SaaS scaling" in prompt_used
```

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Extended `_build_image_prompt` with 3 new optional params: `target_keyword`, `target_audience`, `content_excerpt`. Enrichment sentences (keyword, audience, excerpt) are injected in order after the title sentence, before the tone sentence. Excerpt capped at 200 chars.
- `run_image_generation`: passes all 3 enrichment fields from the campaign record; social-only fallback changed from x_post to linkedin_post first, then brain_dump, then "Untitled".
- `regenerate_image`: same social fallback logic ported; now also passes enrichment fields to `_build_image_prompt`.
- `generate_image_for_roadmap_campaign` left unchanged per AC 8.
- Added 8 new tests covering ACs 2-4, 6-7; updated 2 stale tests (`_make_campaign` helper + x_post→linkedin fallback test). All 35 image service tests pass (164/164 services tests green).

### File List

- backend/app/services/image.py
- backend/tests/services/test_image.py

## Change Log

- 2026-08-15: Implemented image prompt enrichment (keyword, audience, excerpt), fixed social-only fallback (linkedin > brain_dump > Untitled) in run_image_generation and regenerate_image, added 8 new tests.
