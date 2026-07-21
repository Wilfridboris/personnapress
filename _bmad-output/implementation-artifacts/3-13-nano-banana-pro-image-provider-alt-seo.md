# Story 3.13: Nano Banana Pro Image Provider + Alt Text + SEO Filenames

Status: done

## Story

As a PersonnaPress user,
I want generated featured images to have no accidental text artifacts, carry descriptive alt text, and be stored with SEO-friendly filenames,
So that published blog posts look professional, rank better in image search, and are fully accessible.

## Context

Three independent improvements are bundled here because they all touch the same code path (`services/image.py` → `integrations/replicate.py`):

1. **Model switch:** `flux-1.1-pro` → `google/nano-banana-pro` (Nano Banana Pro, Gemini 3 Pro Image).  
   Root cause of "text appears on images / images look off": FLUX 1.1 Pro uses a T5-XXL encoder that cannot reliably suppress text when instructed. Nano Banana Pro (Gemini-based) has significantly stronger instruction following for "no text" constraints and better illustration quality.

2. **Provider/model configurability:** Both model and provider (Replicate vs native Gemini) must be configurable via env vars, defaulting to Replicate + Nano Banana Pro. This mirrors the `LLM_PROVIDER` / `GEMINI_MODEL` pattern already in place for text generation (story 3-12).

3. **Alt text + SEO filename:** Every generated image must receive (a) a descriptive, SEO-compliant alt text stored in the DB and returned to the frontend, and (b) a slug-based storage filename derived from the blog title, replacing the generic `featured.png`.

## Acceptance Criteria

### AC1 — Model switched to Nano Banana Pro (default)

**Given** image generation runs for any campaign,
**When** `IMAGE_PROVIDER=replicate` and `IMAGE_MODEL=google/nano-banana-pro` (the defaults),
**Then** the Replicate API call uses model `google/nano-banana-pro` with inputs `{ aspect_ratio: "16:9", output_format: "png" }` — no `width`, `height`, or `aspect_ratio: "custom"` (those are FLUX-specific parameters not supported by Nano Banana Pro).

### AC2 — Provider/model env vars

**Given** `.env.local` has `IMAGE_PROVIDER=replicate` and `IMAGE_MODEL=google/nano-banana-pro`,
**When** the application starts,
**Then** these values appear in `settings.IMAGE_PROVIDER` and `settings.IMAGE_MODEL` with those as defaults.

**Given** `IMAGE_PROVIDER=gemini` is set,
**When** image generation is triggered,
**Then** the service dispatches to `integrations/gemini_image.py` instead of `integrations/replicate.py`; the interface (`generate_image(prompt) → str`) is identical so `services/image.py` requires no branching beyond the module-level import dispatch.

### AC3 — Model switchback: FLUX 1.1 Pro still works via env var

**Given** `.env.local` has `IMAGE_PROVIDER=replicate` and `IMAGE_MODEL=black-forest-labs/flux-1.1-pro`,
**When** image generation runs,
**Then** the FLUX 1.1 Pro input schema is used (`aspect_ratio: "custom"`, `width: 1200`, `height: 630`, `output_format: "png"`, `output_quality: 100`, `safety_tolerance: 2`) instead of the Nano Banana Pro schema.
_Rationale: model-specific parameter schemas differ; the integration must detect which model family is active._

### AC4 — Updated prompt: "photograph" removed, "image" used

**Given** any campaign runs image generation,
**When** `_build_image_prompt()` is called,
**Then** the returned prompt contains `"A professional editorial image for the article titled"` — NOT `"photograph"` (removing the word allows Nano Banana Pro to choose photorealistic or illustrative style based on topic context).

### AC5 — Alt text generated and persisted

**Given** image generation succeeds (initial or regeneration),
**When** the campaign record is updated,
**Then** `campaigns.image_alt` is set to an SEO-compliant string derived from the blog title in the format:  
`"{blog_title} – featured article image"`  
(title first for keyword proximity, descriptor second, under 125 chars, no "image of" prefix per SEO best practice).

**Given** the `CampaignResponse` schema,
**When** any campaign endpoint returns a response,
**Then** `image_alt: Optional[str]` is present in the payload (null if no image has been generated yet).

**Given** `ImageRegenerateResponse`,
**When** the regenerate endpoint returns,
**Then** `image_alt: str` is included alongside `image_url` and `image_regen_count`.

### AC6 — Alt text used in ImagePanel

**Given** `ImagePanel.tsx` renders the featured image,
**When** `imageAlt` is provided as a prop,
**Then** `<Image alt={imageAlt} ... />` uses it; when `imageAlt` is null/undefined, falls back to `"Featured article image"`.

### AC7 — SEO filename in Supabase Storage

**Given** a blog post titled "5 Ways to Scale Your SaaS Business",
**When** image generation stores the file,
**Then** the Supabase Storage path is `generated-images/{campaign_id}/5-ways-to-scale-your-saas-business.png` — NOT `featured.png`.

**Given** image regen count N > 0,
**When** a regenerated image is stored,
**Then** the path is `generated-images/{campaign_id}/{title-slug}-{N}.png` (e.g. `5-ways-to-scale-your-saas-business-1.png`) — preserving the cache-busting mechanism from story 3-4.

**Given** a blog title that is empty or produces a blank slug,
**When** the slug helper is called,
**Then** it falls back to `featured` (preserving the previous behaviour for edge cases).

---
baseline_commit: ef7adc5492aa0fab4c1c872398fa9a3d27595afd

---

## Tasks / Subtasks

### Group A — Settings (AC2)

- [x] **A1: `backend/app/core/config.py`** — add two new settings after `GEMINI_MODEL`:
  ```python
  IMAGE_PROVIDER: str = "replicate"   # "replicate" | "gemini"
  IMAGE_MODEL: str = "google/nano-banana-pro"
  ```

### Group B — Replicate integration update (AC1, AC3)

- [x] **B1: `backend/app/integrations/replicate.py`** — make model and schema configurable:
  - [x] B1.1 Replace hardcoded `_FLUX_MODEL = "black-forest-labs/flux-1.1-pro"` with:
    ```python
    _MODEL = settings.IMAGE_MODEL
    _IS_FLUX = _MODEL.startswith("black-forest-labs/")
    ```
  - [x] B1.2 Update `generate_image()` to branch on `_IS_FLUX`:
    ```python
    async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str:
        if _IS_FLUX:
            input_payload = {
                "prompt": prompt,
                "aspect_ratio": "custom",
                "width": width,
                "height": height,
                "output_format": "png",
                "output_quality": 100,
                "safety_tolerance": 2,
            }
        else:
            # Nano Banana Pro (and other non-FLUX Replicate models)
            input_payload = {
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_format": "png",
            }
        output: Any = await _client.async_run(_MODEL, input=input_payload)
        ...
    ```
  - [x] B1.3 Update module docstring to reflect `IMAGE_MODEL` configurability (no longer FLUX-specific).
  - [x] B1.4 `width` and `height` params stay in signature for interface compatibility but are only used in the FLUX branch.

### Group C — Gemini native image integration (AC2)

- [x] **C1: Create `backend/app/integrations/gemini_image.py`**:
  ```python
  """Native Gemini image generation integration.

  Activated when IMAGE_PROVIDER=gemini. Uses the google-genai SDK (already a
  project dependency). Called ONLY from services/image.py (AR-19).
  """
  import io
  import logging
  from google import genai
  from google.genai import types
  from app.core.config import settings

  logger = logging.getLogger(__name__)
  _client = genai.Client(api_key=settings.GEMINI_API_KEY)
  _MODEL = settings.IMAGE_MODEL  # e.g. "nano-banana-pro" or Gemini Imagen model ID

  async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> bytes:
      """Generate image via Gemini Imagen API. Returns raw PNG bytes.

      NOTE: The Gemini Imagen API returns image bytes, not a URL. The caller
      (services/image.py) must upload these bytes directly to Supabase Storage
      rather than using upload_image_from_url(). See Dev Notes.
      """
      response = await _client.aio.models.generate_images(
          model=_MODEL,
          prompt=prompt,
          config=types.GenerateImagesConfig(
              number_of_images=1,
              aspect_ratio="16:9",
              output_mime_type="image/png",
          ),
      )
      return response.generated_images[0].image.image_data
  ```
  > **Important:** The Gemini path returns `bytes`, not a URL. See Dev Notes for how `services/image.py` handles both return types.

### Group D — Service layer dispatch (AC2)

- [x] **D1: `backend/app/services/image.py`** — add provider dispatch (mirror story 3-12 `LLM_PROVIDER` pattern):
  ```python
  if settings.IMAGE_PROVIDER == "gemini":
      from app.integrations import gemini_image as _img
  else:
      from app.integrations import replicate as _img  # type: ignore[assignment]
  ```
  Place this at module level after imports (same position as the `_llm` dispatch in `generation.py`).

- [x] **D2** — Update `_replicate_with_retry` → rename to `_generate_with_retry`. Update the inner call to dispatch correctly:
  - For Replicate path (`_img.generate_image` returns `str`): existing Supabase `upload_image_from_url(url, path)` flow unchanged.
  - For Gemini path (`_img.generate_image` returns `bytes`): call `supabase_storage.upload_image_bytes(image_bytes, path)` instead (see Group F).
  - Use `inspect.isawaitable` or check return type to handle both. Simpler: always call `_img.generate_image(prompt)`, then branch on whether the result is `str` or `bytes`.

### Group E — Prompt update (AC4)

- [x] **E1: `backend/app/services/image.py`** — update `_build_image_prompt()`:
  - Change `"A professional editorial photograph for a blog post titled"` → `"A professional editorial image for the article titled"`.
  - The rest of the function (tone sentences, "no text" instruction) remains unchanged.

### Group F — Supabase Storage: direct byte upload (AC2, Gemini path)

- [x] **F1: `backend/app/integrations/supabase_storage.py`** — add `upload_image_bytes()`:
  ```python
  async def upload_image_bytes(image_bytes: bytes, storage_path: str) -> str:
      """Upload raw image bytes to Supabase Storage. Returns public CDN URL.
      Used by the Gemini image provider path (which returns bytes, not a URL).
      """
      bucket = "generated-images"
      prefix = f"{bucket}/"
      if not storage_path.startswith(prefix):
          raise ValueError(f"storage_path must start with '{prefix}', got: {storage_path!r}")
      object_path = storage_path[len(prefix):]
      # Follow existing upload pattern from upload_image_from_url
      ...
  ```
  Model this exactly on the upload logic already in `upload_image_from_url` (extract the shared upload call into a private `_upload_bytes` helper if that reduces duplication — dev discretion).

### Group G — Database: image_alt column (AC5)

- [x] **G1: Alembic migration** — create `backend/alembic/versions/<hash>_add_image_alt_to_campaigns.py`:
  ```python
  down_revision = "a3b4c5d6e7f8"  # add_secondary_keywords_to_campaigns (current head)
  
  def upgrade():
      op.add_column("campaigns", sa.Column("image_alt", sa.Text(), nullable=True))
  
  def downgrade():
      op.drop_column("campaigns", "image_alt")
  ```

- [x] **G2: `backend/app/db/repositories/models.py`** — add to `Campaign` class after `image_url` (line 114):
  ```python
  image_alt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
  ```

### Group H — Schemas: image_alt in API responses (AC5)

- [x] **H1: `backend/app/schemas/campaign.py`**:
  - `CampaignResponse`: add `image_alt: Optional[str] = None` after `image_url`.
  - `ImageRegenerateResponse` (currently `{"image_url": ..., "image_regen_count": ...}`): add `image_alt: str` field.

### Group I — Alt text + SEO filename generation (AC5, AC7)

- [x] **I1: `backend/app/services/image.py`** — add helper functions:
  ```python
  import re

  def _slugify(text: str) -> str:
      """Convert blog title to SEO-friendly filename slug."""
      text = text.lower().strip()
      text = re.sub(r"[^\w\s-]", "", text)        # remove non-word chars
      text = re.sub(r"[-\s]+", "-", text)          # collapse spaces/hyphens
      text = text.strip("-")
      return text[:60] or "featured"               # cap length; fallback for empty

  def _build_image_alt(blog_title: str) -> str:
      """Generate SEO-compliant alt text from blog title.
      
      Format: "{title} – featured article image"
      - Title-first for keyword proximity
      - Descriptor appended (not prefixed)
      - No "image of / photo of" prefix (SEO anti-pattern)
      - Capped at 125 chars
      """
      alt = f"{blog_title} – featured article image"
      return alt[:125]
  ```

- [x] **I2** — In `run_image_generation()`, after extracting `blog_title`:
  ```python
  image_alt = _build_image_alt(blog_title)
  title_slug = _slugify(blog_title)
  storage_path = f"generated-images/{campaign_id}/{title_slug}.png"
  ```
  And after successful upload: `campaign.image_alt = image_alt`

- [x] **I3** — In `regenerate_image()`, same pattern:
  ```python
  image_alt = _build_image_alt(blog_title)
  title_slug = _slugify(blog_title)
  new_regen_count = campaign.image_regen_count + 1
  storage_path = f"generated-images/{campaign_id}/{title_slug}-{new_regen_count}.png"
  ```
  And after commit: include `image_alt` in return tuple → update signature to `-> tuple[str, str, int]` (url, alt, regen_count).

- [x] **I4** — Update `campaigns.py` router regenerate endpoint to extract `image_alt` from the new tuple and include it in `ImageRegenerateResponse`.

### Group J — Frontend: alt text in ImagePanel (AC6)

- [x] **J1: `frontend/components/campaigns/ImagePanel.tsx`**:
  - Add `imageAlt?: string` to the component Props interface.
  - Change `<Image alt="Featured image" ...>` → `<Image alt={imageAlt ?? "Featured article image"} ...>`.

- [x] **J2: `frontend/app/(app)/campaigns/[id]/page.tsx`**:
  - Pass `imageAlt={campaign.image_alt ?? undefined}` to `<ImagePanel>`.

- [x] **J3: `frontend/lib/api.ts`**:
  - Add `image_alt: string | null` to `Campaign` type (alongside `image_url`).
  - Update `regenerateImage()` return type to include `image_alt: string`.

### Group K — Tests (AC1, AC2, AC3, AC5, AC7)

- [x] **K1: `backend/tests/services/test_image.py`**:
  - Update existing tests: mock now dispatches to `_img.generate_image` via the module-level provider variable.
  - Add test: `_build_image_alt("5 Ways to Scale Your SaaS Business")` → `"5 Ways to Scale Your SaaS Business – featured article image"`.
  - Add test: `_build_image_alt` on a 200-char title truncates to 125 chars.
  - Add test: `_slugify("5 Ways to Scale Your SaaS Business!")` → `"5-ways-to-scale-your-saas-business"`.
  - Add test: `_slugify("")` → `"featured"`.
  - Add test: `_slugify` on 80-char title → truncates to 60 chars.
  - Add test: storage path for initial generation uses `{title_slug}.png`.
  - Add test: storage path for regen N=2 uses `{title_slug}-2.png`.
  - Add test: `_build_image_prompt` no longer contains the word "photograph".
  - Add test: FLUX model detection (`_IS_FLUX=True`) produces `aspect_ratio: "custom"` input.
  - Add test: Nano Banana model (`_IS_FLUX=False`) produces `aspect_ratio: "16:9"` input without `width`/`height`.

- [x] **K2: `backend/tests/integrations/test_replicate.py`** (create if not exists):
  - Add parametrised test: with `IMAGE_MODEL=google/nano-banana-pro`, `generate_image` sends `aspect_ratio: "16:9"`.
  - Add parametrised test: with `IMAGE_MODEL=black-forest-labs/flux-1.1-pro`, `generate_image` sends `aspect_ratio: "custom"`, `width: 1200`, `height: 630`.

---

## Dev Notes

### Provider dispatch pattern (mirrors story 3-12 LLM_PROVIDER)

```python
# backend/app/services/image.py — module level, after imports

if settings.IMAGE_PROVIDER == "gemini":
    from app.integrations import gemini_image as _img
else:
    from app.integrations import replicate as _img  # type: ignore[assignment]
```

The function signature on both modules must be:
```python
async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> str | bytes
```
- Replicate path returns `str` (temporary CDN URL) — existing `upload_image_from_url` flow.
- Gemini native path returns `bytes` (raw PNG) — new `upload_image_bytes` flow.

### Nano Banana Pro vs FLUX 1.1 Pro: API schema diff

| Parameter | FLUX 1.1 Pro | Nano Banana Pro |
|-----------|-------------|-----------------|
| `aspect_ratio` | `"custom"` (required for explicit dims) | `"16:9"` (standard ratio) |
| `width` / `height` | Required (with `custom`) | Not supported |
| `output_format` | `"png"` / `"webp"` / `"jpg"` | `"png"` / `"jpg"` |
| `output_quality` | 0–100 | Not applicable |
| `safety_tolerance` | 1–6 | `safety_filter_level` (different param name) |
| `prompt_upsampling` | Supported | Not applicable |
| Default resolution | Custom (`1200×630`) | ~1K equivalent at 16:9 (~1024×576) |
| Cost per image | ~$0.04 | ~$0.10–$0.15 |

**Output dimensions note:** Nano Banana Pro at default 1K resolution produces approximately 1024×576 at 16:9, vs the ideal 1200×630. This is within OG image spec tolerance (minimum 600×315). The quality improvement over FLUX outweighs the ~15% size reduction.

### Gemini native path — SDK call verification

The `google-genai` package is already in `requirements.txt`. The Gemini Imagen API call uses `generate_images()` on the `aio.models` namespace. **Before implementing Group C**, verify the exact method signature against the current installed SDK version:

```bash
python3 -c "from google.genai import types; help(types.GenerateImagesConfig)"
```

If `generate_images()` is not available on `aio.models`, use the sync `models.generate_images()` wrapped in `asyncio.to_thread()` (same pattern used in story 7-3 for the cleanup scheduler).

The Gemini Imagen model IDs available via `GEMINI_API_KEY` are separate from the Replicate model IDs. `IMAGE_MODEL` in Gemini context would be something like `"imagen-3.0-generate-001"` — the developer must verify the current model ID from Google Cloud AI docs.

### Env var defaults in `.env.local.example`

Add these two lines to `backend/.env.local.example` (place after `GEMINI_MODEL`):
```
IMAGE_PROVIDER=replicate      # replicate | gemini
IMAGE_MODEL=google/nano-banana-pro  # Replicate: google/nano-banana-pro or black-forest-labs/flux-1.1-pro
```

### SEO filename: slug character rules

```python
def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)   # strips punctuation, apostrophes etc.
    text = re.sub(r"[-\s]+", "-", text)     # collapses whitespace + hyphens
    text = text.strip("-")
    return text[:60] or "featured"
```

This matches standard SEO slug rules: lowercase, hyphens only, no special chars, capped at 60 chars (Google's recommended filename length). The `or "featured"` fallback handles edge cases (empty title, title with only special chars).

### SEO alt text: format rationale

```
"{blog_title} – featured article image"
```
- **Title first** → primary keyword at the start (highest SEO weight position in alt text).
- **"– featured article image"** → context descriptor (not "image of X" which is an SEO anti-pattern per Google's image guidelines).
- **No keyword stuffing** — one natural descriptor only.
- **Under 125 chars** — screen readers typically truncate at 125 chars (NVDA, JAWS).

### AR-19 compliance

AR-19: `services/image.py` is the ONLY caller of `integrations/replicate.py` (and now also `integrations/gemini_image.py`). The new dispatch (`_img` alias) keeps this constraint intact — `services/image.py` calls `_img.generate_image(prompt)` and never calls either integration directly elsewhere.

### Replicate output normalisation — unchanged

The existing output normalisation in `replicate.py` handles both list and single-value returns:
```python
image_url = str(output[0] if isinstance(output, (list, tuple)) else output)
```
Nano Banana Pro on Replicate returns a single FileOutput object, so `str(output)` resolves correctly. No change needed to normalisation logic.

### Test patching note

Tests currently patch `replicate_integration.generate_image`. After this story, they should patch `_img.generate_image` via the module reference in `services.image`. Use:
```python
with patch("app.services.image._img.generate_image", ...) as mock_gen:
```

### Campaign model: image_alt field position

Add after `image_url` at line 114 in `models.py`:
```python
image_url: Optional[str] = None
image_alt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))  # add this
image_regen_count: int = Field(default=0)
```

### `.env.local.example` additions

```
IMAGE_PROVIDER=replicate
IMAGE_MODEL=google/nano-banana-pro
```

---

## File List

**New files:**
```
backend/app/integrations/gemini_image.py
backend/alembic/versions/bfba3f0b70ff_add_image_alt_to_campaigns.py
backend/tests/integrations/test_replicate.py
```

**Modified files:**
```
backend/app/core/config.py
backend/app/integrations/replicate.py
backend/app/services/image.py
backend/app/integrations/supabase_storage.py
backend/app/db/repositories/models.py
backend/app/schemas/campaign.py
backend/app/routers/campaigns.py
backend/tests/services/test_image.py
backend/.env.example
frontend/components/campaigns/ImagePanel.tsx
frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx
frontend/lib/api.ts
frontend/lib/types.ts
frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx
frontend/__tests__/components/publishing/RetryPanel.test.tsx
_bmad-output/implementation-artifacts/sprint-status.yaml
```

## Dev Agent Record

### Completion Notes

Implemented all 11 groups (A–K) across backend and frontend:

- **A1**: Added `IMAGE_PROVIDER` and `IMAGE_MODEL` settings to `config.py` after `GEMINI_MODEL`.
- **B1**: Replaced hardcoded FLUX model in `replicate.py` with `_MODEL`/`_IS_FLUX` derived from settings; `generate_image` branches on `_IS_FLUX` for correct input schema.
- **C1**: Created `gemini_image.py` using `aio.models.generate_images` (confirmed available in installed SDK). Returns `bytes`, not URL. Used camelCase field names (`numberOfImages`, `aspectRatio`, `outputMimeType`) per SDK convention.
- **D1/D2**: Added `_img` dispatch at module level in `image.py`; renamed `_replicate_with_retry` → `_generate_with_retry`; added `_upload_generated_image()` helper that branches on `str`/`bytes` result type.
- **E1**: Changed "photograph for a blog post" → "image for the article" in `_build_image_prompt`.
- **F1**: Added `upload_image_bytes()` to `supabase_storage.py` delegating to existing `upload_file()`.
- **G1/G2**: Alembic migration `bfba3f0b70ff` adds `image_alt TEXT NULL` to campaigns; `Campaign` model updated.
- **H1**: `CampaignResponse` gains `image_alt: Optional[str] = None`; `ImageRegenerateResponse` gains `image_alt: str` (moved to `routers/campaigns.py`).
- **I1–I4**: `_slugify()` and `_build_image_alt()` added; `run_image_generation` and `regenerate_image` use SEO filename and persist alt text; `regenerate_image` return signature updated to `tuple[str, str, int]`.
- **J1–J3**: `ImagePanel` gains `imageAlt` prop with fallback; `ApprovalGateClient` passes `campaign.image_alt`; `types.ts` `Campaign` type and `api.ts` `regenerateImage` return type updated.
- **K1/K2**: 21 tests total, all passing. No regressions (59 pre-existing failures unchanged).

### Change Log

- 2026-07-21: Story 3-13 implemented — Nano Banana Pro model switch, IMAGE_PROVIDER/IMAGE_MODEL env vars, image_alt column + SEO slug filenames.
