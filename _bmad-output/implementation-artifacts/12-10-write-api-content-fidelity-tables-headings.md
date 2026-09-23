---
baseline_commit: eaa3fb48cf3e6d03d42354352f987e152a9c06bd
---

# Story 12.10: Write-API Content Fidelity — Tables, Deep Headings, Rules, Strikethrough

Status: done

## Story

As a customer developer or AI agent publishing through the headless write API (`POST /public/v1/articles` and `PUT /public/v1/authored/articles/{id}`),
I want tables, `h5`/`h6` headings, horizontal rules, and strikethrough to be preserved instead of silently flattened,
so that structured content I author in Markdown or HTML arrives on my headless site intact.

## Context

The write/ingest pipeline is shared by the create path (Story 12.7 `POST`) and the update path (Story 12.9 `PUT`). Both run content through the same two stages in `backend/app/routers/public_articles.py`:

- `format: "markdown"` -> `_render_markdown` (`public_articles.py:505`) -> `_sanitize_html`
- `format: "html"` -> `_sanitize_html` (`backend/app/core/html_sanitize.py:71`) directly

Today both stages drop several common content elements, for two independent reasons:

1. **The Markdown renderer omits GFM table + strikethrough syntax.** `_render_markdown` builds `MarkdownIt("commonmark", {"html": False})` (`public_articles.py:511`). The CommonMark preset does not enable the `table` or `strikethrough` rules, so a pipe-table or `~~text~~` is emitted as literal text, never as `<table>` / `<s>`.
2. **The sanitizer allowlist is narrow.** `_ALLOWED_TAGS` (`html_sanitize.py:24-32`) permits only `h1-h4, p, ul, ol, li, strong, em, a, br, blockquote, code, pre, img, figure, figcaption`. Every other tag is `unwrap()`ed — the tag is removed and only its text survives. So even raw `format: "html"` containing `<table>`, `<h5>`, `<h6>`, `<hr>`, or `<s>` collapses to plain text.

`_sanitize_html` is the single allowlist shared by the public write API, the in-app editor save (`routers/articles.py`), and `routers/campaigns.py`; its own docstring/comment states it "mirrors frontend DOMPurify config in `BlogEditor.tsx`". To avoid drift, this story widens **both** the backend allowlist and the mirrored `_DOMPURIFY_CONFIG`.

Key facts confirmed against the codebase before writing this story:

- **`table` and `strikethrough` are core markdown-it-py rules**, bundled with the library and enabled via `md.enable([...])`. No new backend dependency, and we deliberately do **not** switch to the full `gfm-like` preset (that would also enable task lists, which emit `<input type="checkbox">` — an element we do not want in the allowlist).
- **This is a shared-pipeline change: the create path (12.7) and the update path (12.9) both benefit automatically.** No route logic changes; only `_render_markdown` and `_sanitize_html` change.
- **No migration, no model column, no new dependency.** Stored `html` is already free-form sanitized HTML in the existing `articles.html` column; `update_article_content(source="edit")` already recomputes `reading_time_minutes` when `html` changes, so wider content needs no extra handling.
- **The in-app editor is explicitly out of scope.** The Tiptap editor cannot author or preserve tables (no table extension; `strike`/`horizontalRule` disabled). Widening `_DOMPURIFY_CONFIG` only keeps the save-sanitizer from being a second stripper; it does **not** make tables authorable in-app, and Tiptap will still drop tables it cannot represent on load. That gap — including the near-term data-loss guard so the editor never clobbers API-authored tables — is logged as a follow-up in `deferred-work.md` ("review of write-API content fidelity (tables/headings) — 12-10 planning").

## Acceptance Criteria

1. **Given** `format: "markdown"` content containing a GFM pipe table, **When** it is ingested via `POST /public/v1/articles` or updated via `PUT /public/v1/authored/articles/{id}`, **Then** the stored `html` contains a well-formed `<table>` with `<thead>`/`<tbody>`, `<tr>`, and `<th>`/`<td>` cells (structure preserved end-to-end, not flattened to text).

2. **Given** `format: "markdown"` content with a column-alignment row (e.g. `|:---|:---:|---:|`), **When** it is rendered and sanitized, **Then** the alignment is preserved as an `align="left|center|right"` attribute on the affected `<th>`/`<td>` cells, and **no** `style` attribute survives on any table cell (alignment is carried by `align`, not inline CSS).

3. **Given** `format: "markdown"` content with strikethrough (`~~text~~`), **When** rendered and sanitized, **Then** the stored `html` contains `<s>text</s>`.

4. **Given** `format: "html"` content containing `<table>` (with `<thead>/<tbody>/<tr>/<th>/<td>/<caption>`), `<h5>`, `<h6>`, `<hr>`, `<s>`, or `<del>`, **When** it is ingested or updated, **Then** those tags survive `_sanitize_html` (tag preserved, inner text intact), with only allowlisted attributes retained.

5. **Given** any of the newly allowed tags, **When** sanitized, **Then** the existing security guarantees are unchanged: `style` and any `on*` event attribute are stripped from every tag (including table cells); disallowed/dangerous tags (`script`, `style`, `iframe`, `svg`, etc.) inside a table are still decomposed; `<img>` src allowlisting and `<a>` href-scheme / `rel="noopener noreferrer"` behaviour are unchanged; task-list `<input>` elements never appear in output.

6. **Given** the Markdown renderer configuration, **When** it is built, **Then** exactly the `table` and `strikethrough` rules are enabled on top of the CommonMark preset (raw-HTML passthrough stays disabled, `html: False`), and task lists / autolinking-to-raw-HTML are **not** enabled.

7. **Given** the frontend save-sanitizer, **When** `_DOMPURIFY_CONFIG` in `BlogEditor.tsx` is inspected, **Then** its `ALLOWED_TAGS` / `ALLOWED_ATTR` include the same additions as the backend allowlist (table family, `caption`, `s`, `del`, `h5`, `h6`, `hr`, and cell attributes `colspan`/`rowspan`/`align`/`scope`), keeping the mirror invariant intact. (Editor authoring behaviour is unchanged and out of scope.)

8. **Given** the headless-blog-api docs page, **When** the supported-elements / formatting section is reviewed, **Then** it lists the now-supported elements (tables with alignment, `h1`–`h6`, `hr`, strikethrough) so API authors know what round-trips.

## Tasks / Subtasks

- [x] 1. **Markdown renderer** (`backend/app/routers/public_articles.py`, `_render_markdown` ~line 505). (AC: 1, 3, 6)
  - [x] 1.1 After constructing `MarkdownIt("commonmark", {"html": False})`, enable the extra rules: `.enable(["table", "strikethrough"])`. Do **not** switch to the `gfm-like` preset. Keep the lazy-singleton pattern.
  - [x] 1.2 Add a code comment stating why the enable-list is narrow (task lists emit `<input>`, deliberately excluded).

- [x] 2. **Backend allowlist** (`backend/app/core/html_sanitize.py`). (AC: 1, 4, 5)
  - [x] 2.1 Add to `_ALLOWED_TAGS`: `table, thead, tbody, tr, td, th, caption, s, del, h5, h6, hr`.
  - [x] 2.2 Add to `_ALLOWED_ATTRS`: `td: ["colspan", "rowspan", "align"]`, `th: ["colspan", "rowspan", "align", "scope"]`.
  - [x] 2.3 Confirm the existing generic attribute-strip loop removes everything not in `_ALLOWED_ATTRS` (so `style` on cells is dropped) and that `on*` stripping still applies to the new tags — no code change expected, but assert with a test (Task 6).

- [x] 3. **Alignment preservation** (`backend/app/core/html_sanitize.py`, inside `_sanitize_html`). (AC: 2)
  - [x] 3.1 Before the attribute-strip step removes `style`, for each `<th>`/`<td>` node read any `text-align: left|center|right` from its `style` and set a corresponding `align` attribute (only these three literal values; ignore anything else). Then let the normal strip remove `style`. markdown-it-py emits alignment as `style="text-align:..."`, so this mapping is what carries alignment through a `style`-banned allowlist.
  - [x] 3.2 Guard against malformed/absent style (no crash, no `align` written when not applicable).

- [x] 4. **Frontend allowlist mirror** (`frontend/components/campaigns/BlogEditor.tsx`, `_DOMPURIFY_CONFIG` ~line 31). (AC: 7)
  - [x] 4.1 Add the same tags to `ALLOWED_TAGS` (`table, thead, tbody, tr, td, th, caption, s, del, h5, h6, hr`) and the cell attrs (`colspan, rowspan, align, scope`) to `ALLOWED_ATTR`. Update the "mirrors the backend" comment to stay accurate.
  - [x] 4.2 Do **not** change the Tiptap extension list or re-enable `strike`/`horizontalRule` here — editor authoring is the deferred follow-up. This task only keeps the save-sanitizer allowlist in sync.

- [x] 5. **Docs page** (`frontend/app/(public)/headless-blog-api/docs/page.tsx`). (AC: 8)
  - [x] 5.1 Update the formatting/supported-content section to list tables (with alignment), full `h1`–`h6`, `hr`, and strikethrough as supported in both `markdown` and `html` formats. Keep the no-em-dash house rule for the copy.

- [x] 6. **Tests**. (AC: 1-7)
  - [x] 6.1 Backend round-trip (extend the existing ingestion/authored-write suites): markdown pipe-table -> `<table>` present; markdown alignment row -> `align` attrs present and no `style`; markdown `~~x~~` -> `<s>x</s>`; `format:"html"` with `<table>/<h5>/<h6>/<hr>/<s>/<del>` -> preserved.
  - [x] 6.2 Backend security regression: `<td style="...">` -> `style` stripped; `<table onmouseover="x">` -> event attr stripped; `<script>`/`<iframe>` inside a `<td>` -> decomposed; confirm no `<input>` ever appears from `- [ ] task` Markdown.
  - [x] 6.3 Assert the change is exercised on **both** the `POST` ingest path and the `PUT` update path (shared pipeline), so a future regression on either surfaces.
  - [x] 6.4 Frontend: extend/duplicate the existing `_DOMPURIFY_CONFIG` assertion (if present) to check the new tags/attrs are allowlisted.

## Dev Notes

### Reuse map

| Need | Reuse |
| --- | --- |
| Markdown render (raw-HTML disabled) | `_render_markdown` in `public_articles.py:505` (add `.enable([...])`) |
| HTML sanitizer allowlist | `_sanitize_html` / `_ALLOWED_TAGS` / `_ALLOWED_ATTRS` in `backend/app/core/html_sanitize.py` |
| Frontend save-sanitizer | `_DOMPURIFY_CONFIG` in `frontend/components/campaigns/BlogEditor.tsx:31` |
| Content update + revision + reading-time | `update_article_content(source="edit")` in `backend/app/db/repositories/articles.py:72` (unchanged) |

### Decisions

- **Narrow rule-enable, not `gfm-like`.** Enabling only `table` + `strikethrough` gives the two elements authors actually want while keeping task-list `<input>` and other GFM surprises out of the allowlist. The allowlist is a security boundary; every tag added here is inert (no scripting capability).
- **Alignment via `align`, not `style`.** `style` stays banned (it is a common injection/exfil vector and is already in the DOMPurify `FORBID_ATTR`). Mapping `text-align` -> a three-value `align` attribute preserves table alignment without reopening `style`.
- **`s` and `del` both allowed.** Markdown strikethrough emits `<s>`; `<del>` is the semantic variant an HTML author may send. Both are inert and semantically "struck".
- **Full heading depth (`h5`, `h6`) + `hr`.** Cheap allowlist additions with no rendering work; they let deep-structured articles and section breaks round-trip.
- **Editor is a separate surface.** Widening `_DOMPURIFY_CONFIG` only prevents the save-sanitizer from double-stripping; it does not make tables authorable in Tiptap, and Tiptap still drops table nodes on load. The data-loss guard + optional table authoring UI are logged in `deferred-work.md` and must not be attempted here.

### Non-goals / out of scope

- In-app Tiptap authoring of tables / strikethrough / `hr` / `h5`-`h6` (deferred follow-up).
- A guard preventing the editor from clobbering API-authored tables (deferred follow-up — near-term data-integrity item, should ship close behind this story).
- Task lists, footnotes, definition lists, `div`/`span`/`section` and other generic layout tags (intentionally excluded to keep the allowlist semantic and the surface tight).
- Any change to public read routes, caching, CORS, rate limiting, or the JSON response shapes.

### Rendering note (informational)

On PersonnaPress-owned surfaces that render article `html` with the Tailwind `prose` class, tables are styled by `@tailwindcss/typography` automatically. Headless consumers render the returned semantic HTML with their own CSS — the API's contract is clean, allowlisted, semantic markup.

## References

- [Source: _bmad-output/implementation-artifacts/12-7-public-article-ingestion-api.md]
- [Source: _bmad-output/implementation-artifacts/12-9-write-token-update-delete-published-article.md]
- [Source: backend/app/routers/public_articles.py (`_render_markdown`, ingest + authored-update routes)]
- [Source: backend/app/core/html_sanitize.py (`_sanitize_html`, `_ALLOWED_TAGS`, `_ALLOWED_ATTRS`)]
- [Source: frontend/components/campaigns/BlogEditor.tsx (`_DOMPURIFY_CONFIG`, Tiptap extension config)]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md ("review of write-API content fidelity (tables/headings) — 12-10 planning")]

## Change Log

- 2026-09-23: Story drafted (ready-for-dev). Widens the shared headless write pipeline so tables (with alignment), `h5`/`h6`, `hr`, and strikethrough round-trip through both `POST /public/v1/articles` (12.7) and `PUT /public/v1/authored/articles/{id}` (12.9). Backend: enable markdown-it-py `table` + `strikethrough` rules (narrow, not `gfm-like`); widen `_sanitize_html` allowlist + cell attrs; map `style="text-align"` -> `align` to preserve alignment while keeping `style` banned. Frontend: mirror the allowlist in `_DOMPURIFY_CONFIG` to hold the sync invariant (editor authoring unchanged). Docs page updated. No migration / model / dependency change. In-app editor authoring of these elements and the editor data-loss guard are logged as a separate follow-up in deferred-work.md.
- 2026-09-23: Implementation complete (in-review). All 6 task groups implemented; 14 backend tests + 6 frontend tests added. 6 adversarial-review patches applied (thread-race fix on lazy singleton, BS4 list-type style guard, and others). 3 items deferred to deferred-work.md. Marked done.

## Suggested Review Order

**Markdown renderer (entry point)**

- Lazy singleton: narrow rule-enable (`table` + `strikethrough`) on top of CommonMark; prevents task-list `<input>`.
  [`public_articles.py:505`](../../backend/app/routers/public_articles.py#L505)

**Backend allowlist — new tags + alignment mapping**

- `_ALLOWED_TAGS` and `_ALLOWED_ATTRS` widened; table family, `s`, `del`, `h5`, `h6`, `hr` added.
  [`html_sanitize.py:25`](../../backend/app/core/html_sanitize.py#L25)

- Alignment preservation: maps `style="text-align:..."` to `align` attribute before `style` is stripped; BS4 list-type guard.
  [`html_sanitize.py:98`](../../backend/app/core/html_sanitize.py#L98)

**Frontend allowlist mirror**

- `_DOMPURIFY_CONFIG` widened to match backend; DATA-LOSS RISK comment documents Tiptap table-clobber hazard.
  [`BlogEditor.tsx:40`](../../frontend/components/campaigns/BlogEditor.tsx#L40)

**Public docs**

- "Supported formatting elements" section replaces stale "Known limits" bullet; tables, h1-h6, hr, strikethrough listed.
  [`page.tsx:1184`](../../frontend/app/(public)/headless-blog-api/docs/page.tsx#L1184)

**Tests**

- POST path round-trip + security regression (pipe table, alignment, strikethrough, raw-HTML path, task-list no-`<input>`).
  [`test_article_ingestion.py:611`](../../backend/tests/routers/test_article_ingestion.py#L611)

- PUT path shared-pipeline smoke (ensures a future regression surfaces on the update route too).
  [`test_authored_write.py:876`](../../backend/tests/routers/test_authored_write.py#L876)

- Direct `_sanitize_html` unit tests (covers the in-app editor save path at `articles.py:131`).
  [`test_articles.py:172`](../../backend/tests/routers/test_articles.py#L172)

- Frontend: `_DOMPURIFY_CONFIG` mirror assertions (table family, s/del, hr, cell attrs, style still forbidden).
  [`BlogEditor.test.tsx:329`](../../frontend/__tests__/components/BlogEditor.test.tsx#L329)
