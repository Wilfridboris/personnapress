---
title: 'Promote excerpt and meta_description to first-class Campaign columns'
type: 'bugfix'
created: '2026-07-24'
baseline_commit: '02a19f5'
status: 'done'
review_loop_iteration: 0
context:
  - 'spec-fix-excerpt-meta-generation-comments-stripped.md (done) — prior fix covered isDirty=false approve path only'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `<!-- excerpt: ... -->` and `<!-- meta: ... -->` HTML comments are the only source of truth for article excerpt and meta_description. They are stripped whenever a user edits and saves the blog (TipTap drops comments from its doc model; DOMPurify and nh3 strip anything that survives). The previous fix only skipped the `blog_html` PATCH when `isDirty=false`; the edit-then-save and edit-then-approve-directly paths still lose the comments.

**Root fix (Option B):** Promote `excerpt` and `meta_description` to dedicated nullable columns on the `campaigns` table. Populate them immediately after `blog_html` is written during generation. `create_or_update_article_from_campaign` reads from the new columns, falling back to HTML extraction only for campaigns that predate this migration. After this change, the HTML comments become redundant — the article pipeline is no longer coupled to whether HTML comments survive editing.

**What changes and why:**

| File | Change | Why |
|------|--------|-----|
| New Alembic migration | Add `excerpt TEXT NULLABLE`, `meta_description TEXT NULLABLE` to `campaigns` | Schema |
| `models.py` | Add two fields to `Campaign` SQLModel | ORM reflects schema |
| `generation.py` | After `campaign.blog_html = blog_html`, also set `campaign.excerpt` and `campaign.meta_description` | Populate at generation time, before any editor can touch the HTML |
| `articles.py` | Prefer `campaign.excerpt` / `campaign.meta_description` columns; fall back to HTML extraction | Works for both new and pre-migration campaigns |

No frontend changes. No changes to approval logic. Revoice creates a fresh campaign and goes through `run_generation_pipeline` — covered automatically.

## Boundaries & Constraints

**Always:**
- The fallback (`campaign.excerpt or _extract_excerpt(campaign.blog_html or "")`) must remain for any campaign that existed before the migration and has `NULL` in the new columns — some may still have intact HTML comments.
- Both new columns are nullable TEXT — no max length enforced at the DB level (extraction functions already cap at 300 / 160 chars respectively).
- `_extract_excerpt` and `_extract_meta_description` are NOT removed — they remain as the fallback path and for their own tests.
- The Alembic migration has no data backfill. Existing approved/published campaigns already have articles with the correct excerpt/meta (those were created from the original HTML). Pending-approval campaigns fall through to the HTML fallback.

**Never:**
- Do not expose `excerpt` or `meta_description` in `CampaignResponse` / `CampaignDetailResponse` — they are an internal implementation detail, not part of the campaign API contract.
- Do not remove the `_extract_excerpt` import from `articles.py` — it is still used in the fallback branch.

## I/O & Edge-Case Matrix

| Scenario | New column state | Article excerpt result |
|----------|-----------------|----------------------|
| Fresh campaign (after this fix) | `campaign.excerpt` populated by generation | Column value used — no HTML parsing |
| User edits blog, saves, then approves | `campaign.excerpt` already set; blog_html PATCH does not touch it | Column value used correctly |
| User edits blog, approves directly (isDirty=true) | `campaign.excerpt` already set; approval PATCH sends blog_html only | Column value used correctly |
| Pre-migration campaign with intact HTML comments | `campaign.excerpt` is NULL → fallback extracts from `blog_html` | Same as before |
| Pre-migration campaign with stripped comments | `campaign.excerpt` is NULL → fallback returns empty string | Same as before (no regression) |
| Revoice | New campaign created → goes through `run_generation_pipeline` → columns populated | Column value used |

</frozen-after-approval>

## Code Map

- `backend/alembic/versions/<new_revision_id>_add_excerpt_meta_to_campaigns.py` — NEW migration file
- `backend/app/db/repositories/models.py:105-135` — `Campaign` model; add two fields after `image_alt`
- `backend/app/services/generation.py:163` — after `campaign.blog_html = blog_html`; add two column assignments
- `backend/app/services/articles.py:100-101` — lines that call `_extract_meta_description` and `_extract_excerpt`; wrap with column preference
- `backend/app/services/articles.py:114` — `Article(...)` constructor; add `featured_image_alt=campaign.image_alt`

## Tasks & Acceptance

**Execution:**

- [x] Create `backend/alembic/versions/<new_revision_id>_add_excerpt_meta_to_campaigns.py`
  - `down_revision = "bfba3f0b70ff"` (latest migration as of this story's baseline)
  - Pattern to follow: `bfba3f0b70ff_add_image_alt_to_campaigns.py`
  - `upgrade()`: two `op.add_column("campaigns", sa.Column("...", sa.Text(), nullable=True))`
  - `downgrade()`: two `op.drop_column("campaigns", "...")`
  - Column names: `excerpt` and `meta_description`
  - No backfill in the migration body

- [x] `backend/app/db/repositories/models.py` — Add to `Campaign` after `image_alt` field:
  ```python
  excerpt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
  meta_description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
  ```

- [x] `backend/app/services/generation.py` — Add imports at the top of the file (near other service imports):
  ```python
  from app.services.articles import _extract_excerpt
  from app.services.publishing import _extract_meta_description
  ```
  Then immediately after `campaign.blog_html = blog_html` (currently line 163):
  ```python
  campaign.excerpt = _extract_excerpt(blog_html)
  campaign.meta_description = _extract_meta_description(blog_html)
  ```
  These two assignments go before the voice fidelity check (Step 3) so they are included in the same atomic DB commit at Step 5.

- [x] `backend/app/services/articles.py` — In `create_or_update_article_from_campaign`, replace:
  ```python
  meta_description = _extract_meta_description(campaign.blog_html)
  excerpt = _extract_excerpt(campaign.blog_html)
  ```
  With:
  ```python
  excerpt = campaign.excerpt or _extract_excerpt(campaign.blog_html or "")
  meta_description = campaign.meta_description or _extract_meta_description(campaign.blog_html or "")
  ```
  Keep the existing imports of `_extract_meta_description` and `_extract_excerpt` — they are still used in the fallback.

- [x] `backend/app/services/articles.py` — In the `Article(...)` constructor, add `featured_image_alt=campaign.image_alt` alongside the existing `featured_image_url=campaign.image_url` line. The AI-generated alt text (populated in story 3-13) is stored on `campaign.image_alt`; the article model has a matching `featured_image_alt` column but it was never wired up during article creation.

**Acceptance Criteria:**

- Given a newly generated campaign, when `run_generation_pipeline` completes, then `campaign.excerpt` is non-empty, does not start with "TL;DR:", and `campaign.meta_description` is non-empty.
- Given the above campaign, when the user edits the blog in TipTap and clicks "Save edits", then `campaign.excerpt` and `campaign.meta_description` in the DB are unchanged (the PATCH endpoint only touches `blog_html`).
- Given the above campaign after a save, when the user clicks Approve, then the created article's `excerpt` and `meta_description` match `campaign.excerpt` and `campaign.meta_description` respectively.
- Given a pre-migration campaign where `campaign.excerpt IS NULL` but `campaign.blog_html` contains `<!-- excerpt: ... -->`, when `create_or_update_article_from_campaign` runs, then article excerpt is extracted from HTML (fallback path, no regression).
- Given a pre-migration campaign where both `campaign.excerpt IS NULL` and no comment exists in `blog_html`, when the function runs, then excerpt is empty string (no regression, same as today).
- Given the Alembic migration `upgrade()` runs against a database, then the `campaigns` table has `excerpt` and `meta_description` columns, both nullable TEXT with no default.
- Given a campaign with `image_alt = "An illustration of..."` when `create_or_update_article_from_campaign` runs, then `article.featured_image_alt == "An illustration of..."` — the AI-generated alt text is no longer lost on article creation.

## Design Notes

**Why no backfill in the migration:** Existing published campaigns already have their articles created (idempotency in `create_or_update_article_from_campaign` returns the existing article unchanged). Pending-approval campaigns that predate this fix hit the `or _extract_xxx(campaign.blog_html or "")` fallback — the HTML may still have intact comments. Already-broken campaigns (comments stripped) produced empty excerpt/meta before this fix too; no regression.

**Why not expose in `CampaignResponse`:** The new columns are pipeline internals consumed by article creation. The frontend never renders or edits campaign excerpt/meta — it reads article fields after publication. Adding them to the API schema would create a public field that clients then depend on, requiring a version bump later if we clean it up.

**`_make_campaign` mock in tests:** The existing test helper in `test_generation_service.py` creates a `MagicMock` campaign, so `campaign.excerpt = ...` and `campaign.meta_description = ...` assignments will just set attributes on the mock without errors. No helper changes required.

## Verification

**Commands:**
- `cd backend && alembic upgrade head` — migration must apply cleanly
- `cd backend && python -m pytest tests/services/test_articles.py -v` — all existing + new tests pass
- `cd backend && python -m pytest tests/test_generation_service.py -v` — new generation test passes
- `cd backend && python -m pytest -v` — full suite, no regressions

**New tests to add:**

In `backend/tests/services/test_articles.py`:
```python
@pytest.mark.asyncio
async def test_create_article_uses_campaign_excerpt_column():
    """When campaign.excerpt is populated, article excerpt comes from column not HTML."""
    # campaign.blog_html has no excerpt comment; excerpt should come from column
    ...
    assert article.excerpt == campaign.excerpt

@pytest.mark.asyncio
async def test_create_article_uses_campaign_meta_description_column():
    """When campaign.meta_description is populated, article meta comes from column."""
    ...
    assert article.meta_description == campaign.meta_description

@pytest.mark.asyncio
async def test_create_article_falls_back_to_html_when_columns_null():
    """When campaign columns are NULL, extraction falls back to HTML comment."""
    # campaign.excerpt = None, blog_html has <!-- excerpt: fallback value -->
    ...
    assert article.excerpt == "fallback value"
```

In `backend/tests/test_generation_service.py`:
```python
@pytest.mark.asyncio
async def test_run_generation_pipeline_sets_excerpt_and_meta():
    """After generation, campaign.excerpt and campaign.meta_description are populated."""
    # mock generate_blog to return HTML with both comments
    # assert campaign.excerpt != "" and campaign.meta_description != ""
```

In `backend/tests/services/test_articles.py`:
```python
@pytest.mark.asyncio
async def test_create_article_copies_image_alt_from_campaign():
    """campaign.image_alt is propagated to article.featured_image_alt on creation."""
    # campaign.image_alt = "A robot writing blog posts"
    # assert article.featured_image_alt == "A robot writing blog posts"
```

**Manual check:**
1. Generate a new campaign. In psql: `SELECT excerpt, meta_description FROM campaigns ORDER BY created_at DESC LIMIT 1;` — both must be non-empty.
2. Edit the blog, click "Save edits". Re-run the query — both columns unchanged.
3. Approve the campaign. Check the created article via the delivery API — excerpt and meta_description must match the column values.

## Dev Agent Record

### Completion Notes

All five implementation tasks completed:

1. **Migration** (`c9d1e2f3a4b5_add_excerpt_meta_to_campaigns.py`): adds `excerpt TEXT NULLABLE` and `meta_description TEXT NULLABLE` to `campaigns`, down_revision `bfba3f0b70ff`.

2. **models.py**: Two new fields added after `image_alt` on `Campaign` SQLModel.

3. **generation.py**: Imported `_extract_excerpt` from `articles.py` and `_extract_meta_description` from `publishing.py`. Both columns populated immediately after `campaign.blog_html = blog_html`, before the voice fidelity check, so they land in the same atomic commit.

4. **articles.py** (column preference): `excerpt` and `meta_description` now read from campaign columns first, falling back to HTML extraction. `_extract_excerpt` and `_extract_meta_description` imports kept for fallback.

5. **articles.py** (`featured_image_alt`): `featured_image_alt=campaign.image_alt` wired into `Article(...)` constructor alongside `featured_image_url`.

**Bonus fix**: `test_generation_service.py` was patching `app.services.generation.gemini` (not in module namespace; always failing). Fixed to `app.services.generation._llm`. 34/34 targeted tests pass. Zero new regressions introduced (other suite failures are pre-existing).

## File List

- `backend/alembic/versions/c9d1e2f3a4b5_add_excerpt_meta_to_campaigns.py` — NEW
- `backend/app/db/repositories/models.py` — MODIFIED
- `backend/app/services/generation.py` — MODIFIED
- `backend/app/services/articles.py` — MODIFIED
- `backend/tests/services/test_articles.py` — MODIFIED
- `backend/tests/test_generation_service.py` — MODIFIED

## Review Findings

### Code Review — 2026-07-24

- [x] [Review][Patch] `is not None` guard for excerpt/meta fallback [`backend/app/services/articles.py:100-101`] — `or`-based fallback incorrectly discards intentional empty string `""`; spec specifies fallback triggers on NULL only. Fixed: use `if … is not None else`.
- [x] [Review][Patch] Missing `meta_description` assertion in HTML-fallback test [`backend/tests/services/test_articles.py:395`] — `test_create_article_falls_back_to_html_when_columns_null` asserted `excerpt` only. Added `assert article.meta_description == ""`.
- [x] [Review][Defer] Unconditional overwrite on re-generation [`backend/app/services/generation.py:165-166`] — deferred, pre-existing design intent per spec; revoice creates new campaigns, not re-runs on existing ones.

**Dismissed (9):** Duplicate revision-ID comment (false positive — standard Alembic format), private cross-module imports (spec-mandated), `_reading_time` None path (unreachable — early return at line 85), `hasattr` heuristic (guard makes it correct), empty-string test gap (fixed by `is not None` patch), hand-crafted revision ID (cosmetic), `_extract_meta_description` divergence (same function in publishing.py), update-path untested (no update path exists — early return), slug-collision mock (sound logic).

## Change Log

- 2026-07-24: Implemented story spec-fix-blog-save-comments-stripped — promoted `excerpt` and `meta_description` to first-class `campaigns` columns; wired `featured_image_alt`; fixed pre-existing `_llm` patch bug in generation tests; added 5 new tests.
