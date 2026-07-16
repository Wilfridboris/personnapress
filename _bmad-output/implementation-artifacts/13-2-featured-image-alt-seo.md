---
baseline_commit: b3170c1
---

# Story 13.2: Featured Image Alt Text — SEO & Accessibility

Status: done

## Story

As a content editor,
I want to write descriptive alt text for each article's featured image,
so that search engines index the image correctly and screen readers describe it meaningfully instead of falling back to the article title.

## Acceptance Criteria

1. **Given** the article editor right rail, **When** an article has a featured image (or placeholder), **Then** the "Featured image" card contains a text input labelled "Image alt text" positioned between the image preview and the Replace button, styled identically to the Details card inputs (`border-b border-[#E5E5E5] focus:border-[#111111]`, label `text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]`).

2. **Given** the alt text input, **When** the user edits it and clicks "Save changes", **Then** the value is persisted to the `featured_image_alt` column on the `articles` table without creating an article revision (same pattern as `featured_image_url`).

3. **Given** the user uploads a new featured image (Replace button), **When** the upload succeeds, **Then** the existing alt text is preserved (not cleared), and a one-line contextual hint "Update after replacing image." appears below the alt input in `text-[11px] italic text-[#8B4513]`. The hint disappears once the user edits the alt field or clicks Save.

4. **Given** an article with `featured_image_alt` set, **When** the public headless delivery API returns the article (list or detail endpoint), **Then** `featured_image_alt` is included in the response alongside `featured_image_url`.

5. **Given** the PersonnaPress company blog list page (`/blog`), **When** an article has `featured_image_alt` set, **Then** both the featured article image and grid card images use `alt={article.featured_image_alt || article.title}`.

6. **Given** the PersonnaPress company blog detail page (`/blog/[slug]`), **When** an article has `featured_image_alt` set, **Then** the featured image uses `alt={article.featured_image_alt || article.title}`.

7. **Given** the `ArticleResponse` Pydantic schema returned by the private articles API, **When** an article is fetched or patched, **Then** `featured_image_alt` is present in the response (null if unset).

8. **Given** the alt text is empty or whitespace when Save is clicked, **Then** the field is omitted from the PATCH body (same `trim() || undefined` pattern as all other nullable text fields — clearing to null is not supported in this story, consistent with `excerpt`, `meta_description`, `author`).

## Tasks / Subtasks

- [x] **Task 1: DB migration** (AC: 2)
  - [x] Create `backend/alembic/versions/<hash>_add_featured_image_alt_to_articles.py`
  - [x] `down_revision = "cc76abfc05a1"` (the articles+revisions migration)
  - [x] `upgrade()`: `op.add_column("articles", sa.Column("featured_image_alt", sa.Text(), nullable=True))`
  - [x] `downgrade()`: `op.drop_column("articles", "featured_image_alt")`

- [x] **Task 2: SQLModel** (AC: 2, 7)
  - [x] `backend/app/db/repositories/models.py` — add after line 175 (`featured_image_url`):
    `featured_image_alt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))`

- [x] **Task 3: Pydantic schemas** (AC: 2, 7)
  - [x] `backend/app/schemas/article.py` — `ArticlePatch`: add `featured_image_alt: Optional[str] = Field(None, max_length=500)` after `featured_image_url`; add `"featured_image_alt"` to the `strip_text` validator field tuple
  - [x] `ArticleResponse`: add `featured_image_alt: Optional[str]` after `featured_image_url`

- [x] **Task 4: Backend PATCH router** (AC: 2)
  - [x] `backend/app/routers/articles.py` — in the PATCH handler, add a new no-revision block immediately after the `featured_image_url` block (lines 217–221):
    ```python
    if body.featured_image_alt is not None:
        article.featured_image_alt = body.featured_image_alt
        article.updated_at = utcnow()
        db.add(article)
    ```
  - [x] Do NOT add `featured_image_alt` to `content_fields` — it must not trigger a revision

- [x] **Task 5: Public delivery API** (AC: 4)
  - [x] `backend/app/routers/public_articles.py` — `_article_list_item()`: add `"featured_image_alt": article.featured_image_alt,` after `featured_image_url`
  - [x] Detail endpoint gets it for free via `**_article_list_item(article)` spread (line 323)

- [x] **Task 6: Frontend TypeScript types** (AC: 5, 6)
  - [x] `frontend/lib/types.ts` — `Article` interface: add `featured_image_alt: string | null;` after `featured_image_url` (line 294)

- [x] **Task 7: Frontend API client** (AC: 2)
  - [x] `frontend/lib/api.ts` — `articlesApi.patch` data type: add `featured_image_alt?: string;` after `featured_image_url` (line 285)

- [x] **Task 8: Article editor UI** (AC: 1, 2, 3)
  - [x] `frontend/app/(app)/blog/[id]/article-editor.tsx`
  - [x] Add state: `const [featuredImageAlt, setFeaturedImageAlt] = useState("");`
  - [x] Add state: `const [imageJustReplaced, setImageJustReplaced] = useState(false);`
  - [x] Initialize in `useEffect` from article: `setFeaturedImageAlt(article.featured_image_alt ?? "");`
  - [x] In `handleFeaturedImageChange` — after the successful upload sets the URL, add: `setImageJustReplaced(true);`
  - [x] In `handleSave` patch object, add: `featured_image_alt: featuredImageAlt.trim() || undefined`
  - [x] In `saveMutation.onSuccess`, add: `setImageJustReplaced(false);`
  - [x] Add UI in the Featured image card between the image/placeholder and the Replace button (see Dev Notes for exact JSX)

- [x] **Task 9: Public blog list page** (AC: 5)
  - [x] `frontend/app/(public)/blog/page.tsx`
  - [x] `ArticleListItem` interface: add `featured_image_alt: string | null;`
  - [x] Featured article image (line 145–152): change `alt={featured.title}` → `alt={featured.featured_image_alt || featured.title}`
  - [x] Grid cards image (line 197–204): change `alt={article.title}` → `alt={article.featured_image_alt || article.title}`

- [x] **Task 10: Public blog detail page** (AC: 6)
  - [x] `frontend/app/(public)/blog/[slug]/page.tsx`
  - [x] `ArticleDetail` interface: add `featured_image_alt: string | null;`
  - [x] Featured image (line 184): change `alt={article.title}` → `alt={article.featured_image_alt || article.title}`

- [x] **Task 11: Tests** (AC: 2, 4)
  - [x] `backend/tests/routers/test_articles.py` — add test: PATCH `featured_image_alt` sets the column without calling `update_article_content` (no revision) — mirror the existing `test_patch_article_featured_image_url_success_no_revision` pattern
  - [x] `backend/tests/routers/test_public_articles.py` — add `featured_image_alt` to the fixture article and assert it appears in the list and detail response bodies

## Dev Notes

### Critical: No-revision pattern — do not add to content_fields

The PATCH handler in `articles.py` splits fields into two paths:

```python
# Content fields → revision created
content_fields = {}
if body.title is not None: content_fields["title"] = body.title
if body.html is not None: content_fields["html"] = body.html
# ... etc (title, html, excerpt, meta_description, tags, category, author)

# Non-content fields → direct column update, no revision
if body.featured_image_url is not None:
    article.featured_image_url = body.featured_image_url
    article.updated_at = utcnow()
    db.add(article)
```

`featured_image_alt` MUST follow the non-content path. Do not add it to `content_fields`. The existing test `test_patch_article_featured_image_url_success_no_revision` (line 822) asserts that `update_article_content` is NOT called — write the same assertion for `featured_image_alt`.

### strip_text validator — extend the existing tuple

Current in `article.py`:
```python
@field_validator("title", "excerpt", "meta_description", "category", "author", mode="before")
@classmethod
def strip_text(cls, v: object) -> object:
    if isinstance(v, str):
        stripped = v.strip()
        return stripped if stripped else None
    return v
```

Add `"featured_image_alt"` to the tuple:
```python
@field_validator("title", "excerpt", "meta_description", "category", "author", "featured_image_alt", mode="before")
```

### Public API: detail endpoint spreads _article_list_item

The detail endpoint (`/v1/articles/{slug}`) builds its body as:
```python
body = {
    **_article_list_item(article),   # ← spreads all list fields
    "html": _strip_scripts(article.html or ""),
    "seo": seo,
}
```

Adding `featured_image_alt` to `_article_list_item()` automatically includes it in both endpoints. No separate change needed for the detail route.

### Article editor UI — exact JSX for Featured image card

Insert this block in the Featured image card between the image/placeholder (`</img>` or `</div>`) and the Replace button:

```tsx
{/* Alt text input */}
<div className="space-y-1.5">
  <label
    htmlFor="article-featured-alt"
    className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
  >
    Image alt text
  </label>
  <input
    id="article-featured-alt"
    type="text"
    value={featuredImageAlt}
    onChange={(e) => {
      setFeaturedImageAlt(e.target.value);
      setImageJustReplaced(false);
    }}
    placeholder="Describe what the image shows…"
    className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
    maxLength={500}
  />
  {imageJustReplaced && (
    <p className="text-[11px] italic text-[#8B4513]">
      Update after replacing image.
    </p>
  )}
</div>
```

Note: `setImageJustReplaced(false)` in the `onChange` clears the hint the moment the user begins typing — this is intentional per the UX spec. No separate flag reset needed in `saveMutation.onSuccess` since clearing on type covers the common case, but add it there too for correctness.

### Exact location in article-editor.tsx right rail

The Featured image card JSX is at lines 378–419. Current structure inside `space-y-3`:
1. `<h2>Featured image</h2>` (line 380)
2. `<input ref={featuredFileRef} .../>` (hidden, line 384)
3. Image or placeholder block (lines 393–404)
4. Replace button (lines 405–418)

Insert the alt text `<div className="space-y-1.5">` **between items 3 and 4** (after the closing tag of the image/placeholder conditional, before the Replace `<button>`).

### Known limitation: cannot clear alt text to null

Empty string in Save → `featured_image_alt.trim() || undefined` → field omitted from PATCH → backend receives `None` (not present) → no update. This is intentional — identical behaviour to `excerpt`, `meta_description`, and `author`. Document in commit message but do not add workaround code.

### Migration chain

Alembic chain at time of writing:
```
f1a2b3c4d5e6 (add_github_pages_to_platform)
  └── cc76abfc05a1 (add_articles_and_revisions)   ← new migration's down_revision
        └── <new> (add_featured_image_alt_to_articles)
```

Run `alembic upgrade head` after creating the migration file.

### Existing test fixture shape (test_public_articles.py)

The fixture article is built at line 59 with `featured_image_url=None`. When adding `featured_image_alt` to the fixture, set it to `None` by default and pass a value explicitly in the tests that assert the API response shape. See lines 76–77 for the pattern of overriding fields on the mock article object.

### No change to services/articles.py

`backend/app/services/articles.py:103` creates the initial Article with `featured_image_url=campaign.image_url`. Do not add `featured_image_alt` here — it defaults to `None` on creation (no AI-generated alt at creation time).

### No change to revisions

`RevisionDetail` and `RevisionListItem` schemas do not include `featured_image_url` and should not include `featured_image_alt` either — image metadata is not versioned.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- All 11 tasks implemented across backend (migration, SQLModel, Pydantic, PATCH router, public API) and frontend (types, API client, editor UI, blog list, blog detail).
- `featured_image_alt` follows the same no-revision pattern as `featured_image_url` — direct column update, not added to `content_fields`.
- `strip_text` validator extended to cover `featured_image_alt`; empty/whitespace values are stripped to `None` (same as `excerpt`, `meta_description`, etc.).
- Public delivery API: `_article_list_item()` now includes `featured_image_alt`; detail endpoint gets it for free via the spread pattern.
- Editor UI: replace hint appears on image upload, clears on any keystroke in the alt field or on Save.
- `_make_article()` fixture in both test files updated to set `featured_image_alt = None` explicitly to prevent MagicMock JSON serialization errors.
- 4 new tests added (1 in test_articles.py, 3 in test_public_articles.py); all pass. Pre-existing unrelated failures (slowapi ModuleNotFoundError, campaigns, etc.) unchanged.

### File List

- backend/alembic/versions/d7e8f9a0b1c2_add_featured_image_alt_to_articles.py
- backend/app/db/repositories/models.py
- backend/app/schemas/article.py
- backend/app/routers/articles.py
- backend/app/routers/public_articles.py
- frontend/lib/types.ts
- frontend/lib/api.ts
- frontend/app/(app)/blog/[id]/article-editor.tsx
- frontend/app/(public)/blog/page.tsx
- frontend/app/(public)/blog/[slug]/page.tsx
- backend/tests/routers/test_articles.py
- backend/tests/routers/test_public_articles.py

### Review Findings

- [x] [Review][Patch] Hint dismissal fires on save success not save click — `setImageJustReplaced(false)` moved before `saveMutation.mutate()` so AC3 "clicks Save" condition is met immediately. [frontend/app/(app)/blog/[id]/article-editor.tsx]
- [x] [Review][Defer] `max_length=500` on `featured_image_alt` not enforced at DB column level — deferred, pre-existing pattern for all text fields [backend/app/schemas/article.py]
- [x] [Review][Defer] `og:image:alt` absent from `seo.og` block in public detail endpoint — deferred, pre-existing; out of scope for this story [backend/app/routers/public_articles.py]
- [x] [Review][Defer] No character count indicator for alt text input — deferred, UX enhancement; out of scope [frontend/app/(app)/blog/[id]/article-editor.tsx]
- [x] [Review][Defer] `db.add(article)` called on already-tracked ORM object (redundant) — deferred, pre-existing convention in `featured_image_url` block [backend/app/routers/articles.py]

## Change Log

- 2026-07-15: Implemented all 11 tasks — DB migration, SQLModel field, Pydantic schemas, PATCH router no-revision block, public delivery API serialisation, frontend TypeScript types and API client, article editor UI (alt input + replace hint), public blog list and detail alt fallback, and 4 new backend tests.
- 2026-07-15: Code review complete — 1 patch applied (hint dismissal on save click), 4 deferred, 10 dismissed.
