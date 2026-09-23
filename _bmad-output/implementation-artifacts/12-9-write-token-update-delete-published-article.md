---
baseline_commit: 8261f6a4249211527960b61994b63d435d588890
---

# Story 12.9: Write-Token Update / Unpublish of Published Articles

Status: done

## Story

As a customer developer or AI agent holding a write-scoped `ppw_` delivery token,
I want to update an existing article in place (including a published one) and to take a published article back down,
so that I can correct or refresh live content and withdraw a post programmatically, without logging into the app.

## Context

Story 12.7 shipped `POST /public/v1/articles`, which deliberately **refuses to overwrite a live post**: a slug that matches a `published` article returns `409 SLUG_CONFLICT_PUBLISHED`. That 409 is a safety guardrail for the *create* flow - it stops an agent from clobbering a live post by accident. Story 12.8 added authenticated read-back (`GET /public/v1/authored/articles` + `/{id}`), which is the **read-before-write** capability that makes editing a live post safe: an agent can fetch the current state, then decide.

This story adds the deliberate, explicit mutation paths that 12.7 left out, and it consciously crosses the "never overwrite a live post" line - but only through an **unambiguous, id-targeted gesture**, never through the create flow:

- **`PUT /public/v1/authored/articles/{id}`** - replace an existing article's content in place (works for a `hidden` or a `published` target). Editing a published article is immediately live.
- **`DELETE /public/v1/authored/articles/{id}`** - take a published article down. This is a **soft unpublish** (status -> `hidden`), never a hard row delete.

Key facts confirmed against the codebase before writing this story:

- **Targeting by `id`, not slug, is the consent gesture.** The `POST` create path stays exactly as-is (409 guardrail intact). Mutation is a separate id-addressed surface: the agent already holds the `id` (from the 12.7 create response or 12.8 read-back), so `PUT {id}` / `DELETE {id}` is an explicit "I mean *this* article" - it cannot be triggered accidentally by a colliding create.
- **The content-update repo function already does the right thing.** `update_article_content(session, article, fields, source="edit")` (`backend/app/db/repositories/articles.py:72`) replaces the content fields, creates an `ArticleRevision` **only if content actually changed**, and (as of the C1 fix) **recomputes `reading_time_minutes` when `html` changes**. The `source` CHECK constraint is `initial | edit | restore` - use `"edit"`; no new source value, no migration.
- **Soft unpublish reuses existing status semantics.** `ArticleStatus` is `published | hidden` only (no `draft`). `set_article_status(session, article, status)` (`articles.py:117`) flips status **without** creating a revision. Reverting a published article to `hidden` removes it from every public read endpoint (which hard-filter `status="published"`) while preserving the row, its revision history, and its live-URL recoverability. No new enum value, no migration.
- **The write auth, body cap, validation, pipeline, response, limiter, and error handlers all already exist** from 12.7 and are reused verbatim (see Reuse map). This story adds two routes and one request model; it introduces no new dependency, migration, model column, or frontend-app change.

## Acceptance Criteria

1. **Given** either mutation endpoint, **When** the `Authorization` header is missing, malformed, not `ppw_`-prefixed, revoked, or hash-mismatched, **Then** the response is **401 `INVALID_DELIVERY_TOKEN`**; **When** it resolves to a valid **read-scoped** (`ppd_`) token, **Then** it is **403 `WRITE_SCOPE_REQUIRED`**. (Reuse `get_delivery_client_write`; `last_used_at` throttled to once per 60s.)

2. **Given** `PUT /public/v1/authored/articles/{id}`, **When** called, **Then** the raw body is capped at **200 KB** (over cap -> **413 `CONTENT_TOO_LARGE`** before parsing), and the JSON body is validated (Pydantic, `extra="forbid"`) with the **same field set and caps as the 12.7 ingest body except `slug`**: `title` required/non-empty/<=300; `content` required/non-empty; `format` exactly `markdown` or `html`; optional `excerpt` (<=500), `meta_description` (<=320), `author` (<=200), `category` (<=100), `featured_image_alt` (<=300), `featured_image_url` (valid http(s)), `tags` (<=20 strings each <=50). **`slug` is not accepted** - sending it is rejected by `extra="forbid"` as **422 `VALIDATION_ERROR`** (slug is immutable via this endpoint; see Dev Notes). Any validation failure returns the nested `{"detail": {"error": {"code", "message"}}}` 422 shape.

3. **Given** `PUT .../{id}`, **When** `{id}` is not a valid UUID, **Then** **422 `VALIDATION_ERROR`**; **When** the article does not exist **or** belongs to a different client than the token, **Then** an **identical 404 `ARTICLE_NOT_FOUND`** (never distinguish missing from other-tenant). The target may be `hidden` or `published` - both are updatable.

4. **Given** a valid `PUT`, **When** `format` is `markdown`, **Then** `content` is rendered (`_render_markdown`, raw-HTML passthrough disabled) then run through `_sanitize_html`; **When** `html`, **Then** `content` is run through `_sanitize_html` directly. Stored `html` is the sanitized output. **No** generation, fidelity, or voice function is called. The house no-em-dash / no-double-dash rule is **not** applied (customer-authored content, stored verbatim aside from sanitization).

5. **Given** a valid `PUT`, **When** it applies, **Then** it is a **full replace**: the request body is the article's complete new state, so every optional field the caller **omits** (`excerpt`, `meta_description`, `author`, `category`, `tags`, `featured_image_url`, `featured_image_alt`) is **cleared to null**, not left unchanged. The content fields (`title`, `html`, `excerpt`, `meta_description`, `tags`, `category`, `author`) are updated via `update_article_content(source="edit")` - which creates a revision **only if content changed** and recomputes `reading_time_minutes` when `html` changed; `featured_image_url` / `featured_image_alt` are set **unconditionally** to the body value (or null when omitted), so they obey the same full-replace rule as the text fields. **The article's `status` is unchanged** (a `published` target stays `published` and the edit is immediately live; a `hidden` target stays `hidden`). The response is **200** carrying `{id, slug, status, edit_url, created_at, updated_at, updated: true}` (the 12.7 `_ingest_response` shape). An identical-content `PUT` is a no-op for the revision/`updated_at` (no revision, timestamp unchanged) but still returns **200**.

6. **Given** `DELETE /public/v1/authored/articles/{id}`, **When** the target is a `published` article owned by the token's client, **Then** it is soft-unpublished: `set_article_status(hidden)` (content and revisions preserved, **no** new revision, **no** hard row delete), it immediately disappears from every public read endpoint, and the response is **200** `{id, slug, status: "hidden", edit_url, created_at, updated_at, updated: true}`. **When** the target is already `hidden`, **Then** it is an idempotent **200** no-op (no status write). **When** `{id}` is not a UUID -> **422**; missing / other-tenant -> identical **404 `ARTICLE_NOT_FOUND`**. Auth per AC 1.

7. **Given** CORS and rate limiting, **When** the routes are added, **Then** `public_app` CORS `allow_methods` remains `["GET", "HEAD", "OPTIONS"]` - **`PUT` and `DELETE` are deliberately NOT added** (a browser on a third-party site must not drive mutations with a victim's token; server/CLI callers ignore CORS and are unaffected, exactly as 12.7 handled `POST`). Both routes carry the **60 requests/minute** write-tier limit keyed on token prefix (fallback IP), returning **429** in the standard shape. All responses carry `Cache-Control: no-store`.

8. **Given** the security/isolation test suite, **When** it runs, **Then** it proves: a `ppd_` read token gets 403 on both routes and a revoked `ppw_` gets 401; a write token for client A can neither `PUT` nor `DELETE` client B's article (404); a `PUT` to a `published` article keeps it `published` and the new content appears in the public `GET /v1/articles` / `/{slug}`; a `DELETE`d article disappears from all public read endpoints (`/v1/articles`, `/{slug}`, `/tags`) and shows as `hidden` via the 12.8 read-back; `<script>` / `on*` / `javascript:` in `content` are stripped on update; a content-changing `PUT` creates exactly one `edit` revision and an identical `PUT` creates none; sending `slug` in the body is 422; and no generation/voice function is invoked.

9. **Given** the developer docs page (`/headless-blog-api/docs`), **When** it is extended, **Then** it documents both endpoints: `ppw_` auth, the `PUT` body (noting `slug` is immutable and updates replace content, stored as sanitized HTML), that editing a `published` article is immediately live, that `DELETE` is a reversible **unpublish** (status -> hidden, not a destructive delete), success/error responses, and copy-paste `curl` examples for the full loop (create -> read back -> update -> unpublish). No em-dash / no double-dash in copy.

10. **Given** the change, **When** it ships, **Then** the existing `POST /public/v1/articles` ingest path and the public read routes are behavior-unchanged (regression), and the mutation paths invoke no generation/fidelity/voice code.

## Tasks / Subtasks

### Task 1: Update request model (AC: 2, 4)

- [x] 1.1 In `backend/app/routers/public_articles.py`, add `ArticleUpdateRequest` (`extra="forbid"`) with the same fields/validators as `ArticleIngestRequest` **minus `slug`**. To avoid validator drift, extract the shared fields + validators into a base model (e.g. `_ArticleContentBase`) that `ArticleIngestRequest` (adds `slug`) and `ArticleUpdateRequest` both inherit. No behavior change to the ingest model's existing contract.

### Task 2: PUT update endpoint (AC: 2, 3, 4, 5, 7, 10)

- [x] 2.1 Add `PUT /v1/authored/articles/{article_id}` (`article_id: uuid.UUID`) depending on `get_delivery_client_write` + `get_session`; `@public_limiter.limit(_WRITE_RATE_LIMIT)` (60/min).
- [x] 2.2 Enforce the 200 KB body cap (413) before parse; parse/validate `ArticleUpdateRequest` (422 nested shape via the existing handler / `_pydantic_errors`).
- [x] 2.3 Fetch via `get_article(db, article_id)`; if `None` or `article.client_id != client_id`, return identical **404 `ARTICLE_NOT_FOUND`** (`Cache-Control: no-store`).
- [x] 2.4 Content pipeline (`markdown` -> `_render_markdown` -> `_sanitize_html`; `html` -> `_sanitize_html`). No generation/voice; no dash rule.
- [x] 2.5 Full replace: build `content_fields` from **all** content fields (present or omitted -> `None`) and pass to `update_article_content(db, article, content_fields, source="edit")` (auto-revision on change, reading_time recomputed on html change); set `article.featured_image_url` and `article.featured_image_alt` **unconditionally** to the body value (`None` when omitted), so images follow the same full-replace rule; do **not** touch `status`. Commit + refresh. Return `_ingest_response(article, updated=True, status_code=200)`.

### Task 3: DELETE (soft unpublish) endpoint (AC: 1, 6, 7, 10)

- [x] 3.1 Add `DELETE /v1/authored/articles/{article_id}` depending on `get_delivery_client_write` + `get_session`; `@public_limiter.limit(_WRITE_RATE_LIMIT)`.
- [x] 3.2 Fetch + tenant-check exactly as 2.3 (identical 404).
- [x] 3.3 If `status == published`, `set_article_status(db, article, ArticleStatus.hidden)` (no revision); if already `hidden`, no write (idempotent). Commit + refresh. Return `_ingest_response(article, updated=True, status_code=200)` (status now `hidden`). Never hard-delete the row.

### Task 4: Tests (AC: 8 + all)

- [x] 4.1 New `backend/tests/routers/test_authored_write.py`: auth matrix on both routes (no/malformed -> 401; `ppd_` -> 403; revoked `ppw_` -> 401; valid `ppw_` -> 200); PUT markdown + html happy paths; PUT to a `published` article keeps it published and the public `GET` reflects the new content; PUT creates exactly one `edit` revision on content change and none on an identical PUT; reading_time recomputed on body change; **full-replace clearing** (a PUT that omits `excerpt`/`tags`/`featured_image_url` etc. clears those fields to null rather than leaving the old values); `<script>`/`on*`/`javascript:` stripped; every 422 branch + 413 oversize + unknown field + `slug`-in-body -> 422; non-UUID id -> 422; tenant isolation (A cannot PUT/DELETE B) -> 404.
- [x] 4.2 DELETE tests: published -> hidden (200) and gone from all public read endpoints + present as `hidden` in 12.8 read-back; already-hidden -> idempotent 200; row still exists + revisions preserved (no hard delete); 429 on the limiter for both routes; assertion that no generation function is invoked.

### Task 5: Developer docs (AC: 9)

- [x] 5.1 Extend `frontend/app/(public)/headless-blog-api/docs/page.tsx` with "Update an article" and "Unpublish an article" sections: auth, PUT body (slug immutable; **full replace - send the complete article, any omitted optional field is cleared**; stored as sanitized HTML; published edits go live immediately), DELETE = reversible unpublish to hidden (not destructive), error codes, the known cache-propagation limit (edits/unpublish are eventual for cached public consumers), and `curl` for the create -> read-back -> update -> unpublish loop. No em-dash / no double-dash.

## Dev Notes

### Critical constraints

- **Do NOT change `POST /public/v1/articles` or the public read routes.** The create-flow 409 guardrail and the public `status="published"` filter stay exactly as-is. This story only ADDS `PUT` and `DELETE` under `/v1/authored/articles/{id}`. AC 10 exists to prove the regression surface is clean.
- **Mutation is id-addressed and write-scoped.** Reuse `get_delivery_client_write` (401/403). Targeting by `id` (not slug) is the deliberate-consent gesture that makes editing a live post safe; there is no "overwrite by colliding create" path.
- **Editing a published article is immediately live and keeps `status="published"`.** Content still passes through `_sanitize_html`. Do not add a re-moderation or status change on update.
- **DELETE is a soft unpublish, never a hard delete.** `set_article_status(hidden)` preserves the row, revisions, and URL recoverability, and removes it from the public read API. No new `ArticleStatus` value; no migration. Do not call any row-delete.
- **Revisioning.** Content changes go through `update_article_content(source="edit")` - auto-revision only on change, and (C1 fix) reading_time recomputed on `html` change, so no manual reading-time handling is needed. Unpublish makes **no** revision (content is unchanged). `source` stays within the existing `initial|edit|restore` CHECK - no `"api"`/`"delete"` value.
- **Slug is immutable via this endpoint.** `ArticleUpdateRequest` omits `slug`; `extra="forbid"` turns a `slug` in the body into a 422 so the caller's wrong assumption is surfaced rather than silently ignored. Rename + redirect is deferred (URL stability / SEO).
- **No optimistic concurrency in v1.** No `If-Match` / 412. Recoverability rests on id-explicit targeting plus full `edit` revision history (a lost update is always recoverable from a revision). `If-Match` is a deferred follow-up.
- **Tenant isolation.** `get_article` fetches by id only; both routes must verify `article.client_id == client_id` and return the identical 404 otherwise (mirrors 12.8 / `get_published_article`).
- **Sub-app isolation.** Reuse the existing `public_app` handlers (413/422/404/429 nested shapes) and limiter. Do NOT loosen main-app CORS; do NOT add `PUT`/`DELETE` to `public_app` CORS `allow_methods`. All responses `Cache-Control: no-store`.
- **Pure mutation of stored fields only.** No import or call of `generation`, fidelity, or voice code (mirror 12.7's no-generation test).

### Reuse map

| Need | Existing code |
|---|---|
| Write auth dependency (401/403) | `get_delivery_client_write` in `backend/app/routers/public_articles.py:211` |
| Get by id (add client-ownership check) | `get_article` in `backend/app/db/repositories/articles.py:27` |
| Content update + auto-revision + reading_time recompute | `update_article_content` in `backend/app/db/repositories/articles.py:72` |
| Status flip without revision (soft unpublish) | `set_article_status` in `backend/app/db/repositories/articles.py:117` |
| Body cap constant + write rate limit | `_MAX_BODY_BYTES`, `_WRITE_RATE_LIMIT` in `public_articles.py:50,51` |
| Ingest request model + validators (extract shared base) | `ArticleIngestRequest` in `public_articles.py:497` |
| Markdown render (raw-HTML disabled) | `_render_markdown` in `public_articles.py:487` |
| HTML sanitizer | `_sanitize_html` in `backend/app/core/html_sanitize.py` |
| Response shape | `_ingest_response` in `public_articles.py:564` |
| 422 normalization | `_pydantic_errors` + `_validation_handler` in `public_articles.py:697,133` |
| Error bodies + 404 | `_ARTICLE_NOT_FOUND`, `_error_detail`, `_token_401`, `_write_scope_403` (`public_articles.py:92,102,192,200`) |
| Limiter | `public_limiter` / `@public_limiter.limit(_WRITE_RATE_LIMIT)` (`public_articles.py:66`) |
| Docs page | `frontend/app/(public)/headless-blog-api/docs/page.tsx` |

### Previous story intelligence

- **Story 12.8 (direct dependency):** the read-before-write capability that makes editing a live post safe, the by-id + identical-404 tenant pattern, and the `/v1/authored/*` path this story extends. Build 12.9 after 12.8.
- **Story 12.7:** the ingest body model + validators, the 200 KB cap, the content pipeline, `_ingest_response`, the 60/min limiter, the 409 create-guardrail this story complements (never modifies), and the CORS decision to keep mutations out of `allow_methods`.
- **Story 12.1:** article/revision schema, `published`/`hidden` semantics, the `source` CHECK (`initial|edit|restore`), `update_article_content` / `set_article_status`.
- **Story 12.2:** public read isolation (`status="published"` hard filter) - the routes this story must not touch.
- **Recurring review lessons:** validate/parse before DB work (413/422 before lookup); identical 404 for missing vs other-tenant; never leak raw internal errors; `no-store` for private/mutating responses; keep public error bodies in one of the two accepted shapes.

### Design decisions (resolved with Boris - do not re-open)

- **DELETE = soft unpublish (status -> hidden), not a hard delete.** Reversible, preserves row/revisions/SEO; hard delete deferred.
- **Update = `PUT` full-content replace** (same body as ingest minus slug), not `PATCH` partial. Read-back (12.8) makes full-replace workable; `PATCH` deferred.
- **No `If-Match` / optimistic concurrency in v1.** Revision history is the recoverability net; deferred.

### Project structure notes

- Backend: edits to `backend/app/routers/public_articles.py` only (2 new routes + `ArticleUpdateRequest` + a shared `_ArticleContentBase` extracted from the ingest model); new `backend/tests/routers/test_authored_write.py`. **No** migration, **no** model change, **no** new dependency, **no** repository change (existing `get_article` / `update_article_content` / `set_article_status` suffice).
- Frontend: docs page (`headless-blog-api/docs/page.tsx`) extension only. **No** in-app UI change (in-app editing/unpublishing already exists via the Article Manager), **no** `DeliveryTokensCard` change.

### Known v1 limits (documented, not fixed here)

- **Edits and unpublishes are not instantly visible to already-cached public consumers.** The public read routes cache `public, max-age=60, stale-while-revalidate=300` (Story 12.2). After a `PUT` to a live post or a `DELETE` (unpublish), a cached CDN/browser copy can keep serving the old content - or a withdrawn post - for up to that window before it revalidates against the `updated_at`-based ETag. Inherent to the headless caching model; document it so consumers do not expect instant propagation.

### Deferred follow-ups (explicitly out of scope)

- **Optimistic concurrency** (`If-Match` / `412 Precondition Failed`) to guard against two agents overwriting each other on a live post.
- **Hard delete** of an article via API (destructive; row + revisions removed).
- **Slug rename** on update (+ redirect handling for the old URL).
- **`PATCH` partial update** (change one field without resending full content).
- **Restore-from-revision** via API (roll a published article back to a prior `ArticleRevision`).

### References

- [Source: _bmad-output/implementation-artifacts/12-8-write-token-authored-article-readback.md]
- [Source: _bmad-output/implementation-artifacts/12-7-public-article-ingestion-api.md]
- [Source: _bmad-output/implementation-artifacts/12-1-article-model-revision-history.md]
- [Source: backend/app/routers/public_articles.py (write auth, ingest model/pipeline/response, limiter, handlers)]
- [Source: backend/app/db/repositories/articles.py (update_article_content, set_article_status, get_article)]

## Change Log

- 2026-09-21: Story drafted (ready-for-dev). Write-token mutation of existing articles: `PUT /public/v1/authored/articles/{id}` (full-content update in place; published edits go live immediately, status unchanged; slug immutable; auto-revision + reading_time recompute) and `DELETE /public/v1/authored/articles/{id}` (soft unpublish -> hidden, reversible, never hard-deletes). Reuses `get_delivery_client_write`, `get_article` (+tenant 404), `update_article_content(source="edit")`, `set_article_status`, the 12.7 body cap/pipeline/response/limiter, and existing handlers. `POST` 409 create-guardrail and public read routes untouched. Decisions with Boris: soft unpublish (not hard delete), PUT full-replace (not PATCH), no If-Match in v1. No migration, no model/dependency/frontend-app change; docs page extended. Depends on 12.8 (read-before-write).
- 2026-09-21: Self-review refinements folded in. (F1a) PUT semantics pinned as a true full replace - omitted optional fields (incl. `featured_image_url`/`featured_image_alt`) are cleared to null, so images obey the same rule as text fields; AC5, Task 2.5, Task 4.1, and the docs task updated. (F2) Added a "Known v1 limits" note: public read caching (max-age=60, swr=300) means edits/unpublish are eventual for already-cached consumers; also called out in the docs task.
- 2026-09-22: Implemented and reviewed (3-layer adversarial review). One patch applied: an image-only PUT (identical text, changed `featured_image_url`/`featured_image_alt`) did not bump `updated_at` because `update_article_content` returns early when text content is unchanged. Since the detail/list ETag and JSON-LD `dateModified` are keyed on `updated_at`, the new image would never propagate to conditional/cached consumers (304 forever). Fixed in the PUT route by bumping `updated_at` when only the image fields change; added two regression tests. All other review findings rejected as spec-mandated (`updated:true` on no-op responses per AC 5/6), explicitly deferred (If-Match/optimistic concurrency), or already covered by the shared 12.7/12.8 code and passing tests. 39 tests in `test_authored_write.py`; 102 passing across the authored/ingestion/read-back suites.

## Suggested Review Order

**Request model refactor (shared validators, slug immutability)**

- Shared base extracted so ingest and update bodies cannot drift; `extra="forbid"`.
  [`public_articles.py:515`](../../backend/app/routers/public_articles.py#L515)

- Update body inherits the base and omits `slug`, so a `slug` in the body is a 422.
  [`public_articles.py:594`](../../backend/app/routers/public_articles.py#L594)

**PUT full-content update in place (the design core)**

- Entry point: route wiring, write-scope dependency, and 60/min limiter.
  [`public_articles.py:857`](../../backend/app/routers/public_articles.py#L857)

- Full replace: every omitted optional field cleared to null; status untouched.
  [`public_articles.py:859`](../../backend/app/routers/public_articles.py#L859)

- Patch: image-only edit bumps `updated_at` so the ETag / `dateModified` flip.
  [`public_articles.py:932`](../../backend/app/routers/public_articles.py#L932)

**DELETE soft unpublish (reversible, never a hard delete)**

- Published -> hidden via `set_article_status` (no revision); already-hidden is an idempotent no-op.
  [`public_articles.py:940`](../../backend/app/routers/public_articles.py#L940)

**Developer docs**

- New "Update an Article" section: full-replace semantics, slug immutable, live-on-publish.
  [`page.tsx:1308`](../../frontend/app/(public)/headless-blog-api/docs/page.tsx#L1308)

- New "Unpublish an Article" section plus the cache-propagation caveat.
  [`page.tsx:1402`](../../frontend/app/(public)/headless-blog-api/docs/page.tsx#L1402)

**Tests (supporting)**

- Auth matrix, render/sanitize, full-replace clearing, tenant 404, DELETE idempotency, no-generation, and the two `updated_at`-bump regression tests.
  [`test_authored_write.py:352`](../../backend/tests/routers/test_authored_write.py#L352)
