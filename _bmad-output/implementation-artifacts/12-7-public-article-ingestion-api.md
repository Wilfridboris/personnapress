---
baseline_commit: 185cd2068c272f45c267d7f37d11af6a96d97ef3
---

# Story 12.7: Public Article Ingestion API (write-scoped delivery token)

Status: done

## Story

As a customer developer or AI agent (for example, Claude running in a terminal),
I want to POST a blog post to PersonnaPress with a write-scoped API key and have it land directly as a hidden article in the client's Article Manager,
so that I author content programmatically with no brain dump, no generation job, and no voice/AI transformation.

## Context

Epic 12 shipped the outbound half of the headless surface: read-only `ppd_` delivery tokens and the `/public/v1/*` read API (Story 12.2), a cluster page (12.4), and a developer docs page (12.6). This story adds the inbound half: a write-scoped token and a single ingestion endpoint that creates an article verbatim.

Key facts confirmed against the codebase before writing this story:

- **Unpublished state = `hidden`.** `ArticleStatus` is `published | hidden` only — there is no `draft` status. We deliberately reuse `hidden` (no new enum, no status migration). The read API hard-filters `status="published"`, so a hidden article can never leak to the public read endpoints. The in-app Article Manager (`frontend/app/(app)/blog/blog-list.tsx`) already lists hidden articles with a "Hidden" badge and links each to `/articles/{id}`, where the editor's `PATCH /api/v1/articles/{id}` status change (`set_article_status`) publishes it. So an ingested hidden article is findable and publishable through existing UI with zero frontend list changes.
- **Versioning is explicit on create.** `create_article()` (repo) inserts only the Article row. The initial `ArticleRevision(revision_number=1, source="initial")` is created explicitly in `services/articles.py` (`create_or_update_article_from_campaign`, lines 127-139). This endpoint must do the same or the article will have no revision history.
- **Delivery tokens are client-bound and read-only today.** `DeliveryToken` (models.py ~334) has no scope column; every public query hard-codes `status="published"`. A write token binds to exactly one client (tokens are created nested under `/clients/{client_id}/delivery-tokens`), so the caller never specifies a client.

## Acceptance Criteria

1. **Given** the Alembic migration runs, **When** it completes, **Then** the `delivery_tokens` table has a new `scope` column (Text, NOT NULL, server_default `'read'`), all existing rows backfilled to `'read'`. Downgrade drops the column. No other schema changes (no new `ArticleStatus` value, no `ArticleRevision.source` CHECK change).

2. **Given** an authenticated app user on a client they own, **When** they call `POST /api/v1/clients/{client_id}/delivery-tokens` with an optional `scope` of `read` or `write` (default `read`), **Then** a read token is generated with the `ppd_` prefix and a write token with the `ppw_` prefix (both `<prefix>_` + `secrets.token_urlsafe(32)`), its SHA-256 hash + first-8-char prefix + scope are stored, and the raw token is returned exactly once. `GET` list includes each token's `scope` and never a secret. An invalid `scope` value returns 422.

3. **Given** a request to `POST /public/v1/articles`, **When** the `Authorization: Bearer ppw_...` header is missing, malformed, not `ppw_`-prefixed, revoked, or does not hash-match a stored token, **Then** the response is **401** `INVALID_DELIVERY_TOKEN`. **When** the header resolves to a valid but **read-scoped** token, **Then** the response is **403** `WRITE_SCOPE_REQUIRED` (valid identity, insufficient permission). A valid write token resolves to exactly one `client_id` and updates `last_used_at` at most once per 60s.

4. **Given** a valid write token, **When** `POST /public/v1/articles` is called with a JSON body, **Then** the body is validated (Pydantic, `extra="forbid"`): `title` required, non-empty trimmed, <= 300 chars; `content` required, non-empty; `format` required and exactly `markdown` or `html`; optional `slug` (<= 200), `excerpt` (<= 500), `meta_description` (<= 320), `author` (<= 200), `category` (<= 100), `featured_image_alt` (<= 300), `tags` (list of <= 20 strings each <= 50 chars), `featured_image_url` (valid `http(s)` URL). The raw request body is capped at 200 KB; over cap returns **413** `CONTENT_TOO_LARGE`. Any validation failure returns **422** `VALIDATION_ERROR` in the nested `{"detail": {"error": {"code", "message"}}}` shape.

5. **Given** a valid create request, **When** `format` is `markdown`, **Then** `content` is rendered to HTML by a maintained Markdown renderer with raw-HTML passthrough disabled, then run through the existing `_sanitize_html` allowlist; **When** `format` is `html`, **Then** `content` is run through `_sanitize_html` directly. The stored `html` is the sanitized output. No generation, fidelity, or voice function is ever called. The house "no em-dash / no double-dash" rule is **not** applied (this is customer-authored content, stored verbatim aside from sanitization).

6. **Given** a create request, **When** a `slug` is provided and an article with `(client_id, slug)` already exists with status `hidden`, **Then** its content fields are updated via `update_article_content(source="edit")` (which versions automatically only if content changed) and the response is **200**. **When** the existing article with that slug is `published`, **Then** the response is **409** `SLUG_CONFLICT_PUBLISHED` (the API never overwrites a live post). **When** no `slug` is provided, **Then** a base slug is derived from `title` via `slug_from_title` and made unique via `_unique_slug` (auto-suffix `-2`, `-3`, ...), and a new article is always created (**201**).

7. **Given** a new article is created, **When** it is inserted, **Then** `create_article` is called with `campaign_id=None`, `status="hidden"`, computed `reading_time_minutes` (via `_reading_time`), `published_at=utcnow()`, and the provided/derived fields; **and** an initial `ArticleRevision(revision_number=1, source="initial")` is inserted explicitly (mirroring `create_or_update_article_from_campaign`) so the hidden article has revision history from creation.

8. **Given** a successful create or update, **When** the response is returned, **Then** it carries `{id, slug, status: "hidden", edit_url: "{APP_URL}/articles/{id}", created_at, updated_at, updated: <true on the 200 hidden-slug update, false on create>}`.

9. **Given** the public sub-application, **When** the write route is added, **Then** `public_app` CORS remains `allow_methods=["GET", "HEAD", "OPTIONS"]` — POST is deliberately **not** CORS-allowed so a browser on a third-party site cannot drive writes with a victim's token; server/CLI callers ignore CORS and are unaffected. The main app's single-origin CORS is unchanged.

10. **Given** rate limiting, **When** `POST /public/v1/articles` is called, **Then** a per-token-prefix limit of **60 requests/minute** applies (falling back to IP), returning **429** in the standard error shape, registered on `public_app`.

11. **Given** the security/isolation test suite, **When** it runs, **Then** tests prove: a `ppd_` read token is rejected with 403 on the write route; a write token for client A cannot create or mutate an article under client B; an ingested article (`hidden`) never appears in any `GET /public/v1/articles`, `/{slug}`, or `/tags` response; a revoked write token gets 401; `<script>`, `on*` handlers, and `javascript:` hrefs in `content` are stripped; a slug collision with a published article returns 409 and with a hidden article returns 200 (update, with a new revision only when content changed); an oversized body and an unknown field are rejected; and no generation/voice function is invoked during ingest.

12. **Given** the token management UI, **When** a user creates a delivery token, **Then** the existing `DeliveryTokensCard` create flow offers a scope choice (**Read-only** / **Write (create articles)**), sends `scope`, and the token list shows a scope badge and the correct prefix. Paper Style (Ink 1px borders, `rounded-none`, Lucide `KeyRound`, no emojis), following the existing card patterns.

13. **Given** the developer docs page (Story 12.6), **When** it is extended, **Then** it documents the write endpoint: auth (`ppw_` bearer), request body, `format`, success/error responses, and a copy-paste Claude/terminal `curl` example that creates a hidden article from Markdown. Documents the two known v1 limits: inline images whose `src` is not a PersonnaPress-hosted URL are stripped (upload images in-app), and Markdown tables / `h5`-`h6` / horizontal rules are flattened by the allowlist.

## Tasks / Subtasks

### Task 1: `scope` column + migration (AC: 1)

- [x] 1.1 Add `scope: str` (default `"read"`) to `DeliveryToken` in `backend/app/db/repositories/models.py`.
- [x] 1.2 Alembic migration (house style; chain from head): add `scope` Text NOT NULL server_default `'read'`; backfill existing rows to `'read'`. Downgrade drops the column.

### Task 2: Write-scoped token generation + management (AC: 2)

- [x] 2.1 In `backend/app/db/repositories/delivery_tokens.py`: `generate_raw_token(scope)` picks prefix `ppw_` for write, `ppd_` for read; persist `scope` on create.
- [x] 2.2 Extend the create schema/endpoint in `backend/app/routers/clients.py` (`POST /clients/{client_id}/delivery-tokens`) with an optional `scope` field (`read` | `write`, default `read`, validated). Ownership check unchanged. List response includes `scope`.

### Task 3: Write auth dependency (AC: 3)

- [x] 3.1 In `backend/app/routers/public_articles.py`, add `get_delivery_client_write(request) -> uuid.UUID`: parse `Authorization: Bearer ppw_...`, reject non-`ppw_` early, hash + look up active token; on any failure 401 `INVALID_DELIVERY_TOKEN`; if the matched token's `scope != "write"` return 403 `WRITE_SCOPE_REQUIRED`. Reuse the existing `touch_last_used` throttle. (Read routes keep the existing dependency and accept any active token.)

### Task 4: Ingestion endpoint (AC: 4, 5, 6, 7, 8, 9)

- [x] 4.1 Add `POST /v1/articles` to `public_app`. Request model with `extra="forbid"` and the field caps in AC 4; enforce the 200 KB body cap (413) before parsing/rendering.
- [x] 4.2 Content pipeline: `markdown` -> renderer (raw HTML disabled) -> `_sanitize_html`; `html` -> `_sanitize_html`. Do NOT call any generation/voice code. Do NOT apply the dash rule.
- [x] 4.3 Slug + idempotency per AC 6: explicit slug -> upsert-if-hidden (200) / 409-if-published; no slug -> `slug_from_title` + `_unique_slug` -> create (201).
- [x] 4.4 Create path: `create_article(campaign_id=None, status="hidden", reading_time_minutes=_reading_time(html), published_at=utcnow(), ...)` then insert `ArticleRevision(revision_number=1, source="initial")` explicitly. Update path: `update_article_content(article, fields, source="edit")`.
- [x] 4.5 Response shape per AC 8 (`edit_url` from `settings.APP_URL`). CORS unchanged (AC 9) — verify POST is not added to `public_app` allow_methods.

### Task 5: Rate limiting (AC: 10)

- [x] 5.1 slowapi decorator on the write route, 60/min keyed on token prefix (fallback IP), 429 standard shape, registered on `public_app`.

### Task 6: Sanitizer reuse (supports AC 5)

- [x] 6.1 `_sanitize_html` currently lives in `backend/app/routers/articles.py`. Lift it (and its `_ALLOWED_TAGS`/`_ALLOWED_ATTRS`/`_BLOCK_TAGS` + `is_allowed_image_src` usage) into `backend/app/core/html_sanitize.py` (where `is_allowed_image_src` already lives) and import it from both routers, to avoid a router-to-router import. No behavior change.

### Task 7: Frontend token scope (AC: 12)

- [x] 7.1 Extend `frontend/components/publishing/DeliveryTokensCard.tsx` create flow with a scope choice (Read-only / Write). Send `scope` via `deliveryTokensApi`. Show scope badge + prefix in the list. Update `frontend/lib/types.ts` + `frontend/lib/api.ts`.

### Task 8: Developer docs (AC: 13)

- [x] 8.1 Extend the Story 12.6 developer docs page with the write endpoint, a Claude/terminal `curl` example, and the two documented limits (inline external images stripped; tables/h5-h6/hr flattened).

### Task 9: Tests (AC: 11 + all)

- [x] 9.1 New `backend/tests/routers/test_article_ingestion.py`: auth matrix (no token / `ppd_` read -> 403 / revoked -> 401 / valid `ppw_` -> 201), markdown + html happy paths, `<script>`/`on*`/`javascript:` stripping, every 422 branch + 413 oversize + unknown-field, slug auto-generate, upsert-hidden (200 + revision only on change), 409-on-published, tenant isolation (A cannot write to B), the hidden article absent from all read endpoints, 429 on limiter, and an assertion that no generation function is called.
- [x] 9.2 Extend `backend/tests/routers/test_delivery_tokens.py`: write token creates `ppw_` prefix, `scope` stored + listed, default remains `read`.

## Dev Notes

### Critical constraints

- **"No transformation" is the core guarantee.** The ingest path stores content verbatim after HTML sanitization only. It must never import or call `generation`, fidelity, or voice code. Add a test that asserts this.
- **`hidden` is the unpublished state — there is no `draft` status.** Never introduce a new `ArticleStatus`. The read API's hard-coded `status="published"` is the isolation guarantee — do not add any parameter that widens it.
- **Sub-app isolation.** `public_app` has its own middleware, exception handlers, and limiter. Register the write route, its 422/409/413 handlers (nested shape), and the 60/min limiter on `public_app` explicitly. Do NOT loosen the main app CORS, and do NOT add POST to `public_app` CORS `allow_methods`.
- **Versioning on create is explicit.** `create_article()` does not create a revision; insert `ArticleRevision(revision_number=1, source="initial")` yourself (see `services/articles.py:127-139`). Use `source="edit"` for hidden-slug updates so the existing CHECK constraint (`initial|edit|restore`) is respected — no `"api"` source, no constraint migration. API-authored articles are already distinguishable by `campaign_id IS NULL`.

### Reuse map

| Need | Existing code |
|---|---|
| HTML sanitizer + allowlist | `_sanitize_html` in `backend/app/routers/articles.py:61` (lift to `backend/app/core/html_sanitize.py`) |
| Image src allowlist | `is_allowed_image_src` in `backend/app/core/html_sanitize.py` |
| Reading time | `_reading_time` in `backend/app/services/articles.py:44` |
| Slug base + uniqueness | `slug_from_title` (`integrations/github`) + `_unique_slug` (`services/articles.py:58`) |
| Article insert | `create_article` in `backend/app/db/repositories/articles.py:14` |
| Content update + auto-revision | `update_article_content` in `backend/app/db/repositories/articles.py:72` |
| Initial revision pattern | `create_or_update_article_from_campaign` in `backend/app/services/articles.py:127` |
| Token model + repo | `DeliveryToken` (models.py ~334), `backend/app/db/repositories/delivery_tokens.py` |
| Public sub-app + read auth dep | `backend/app/routers/public_articles.py` (Story 12.2) |
| Rate limiter pattern | slowapi on `public_app` (120/min read routes) |
| Error shape | `{"detail": {"error": {"code", "message"}}}` (all routers); flat `{"error": {...}}` for 429 |
| Token UI | `frontend/components/publishing/DeliveryTokensCard.tsx` |

### Previous story intelligence

- Story 12.2 (direct dependency): the `ppd_` token mechanism, SHA-256 hashing + `hmac.compare_digest`, the `public_app` mount, isolated CORS/limiter/handlers, `touch_last_used` 60s throttle. Read its File List before starting.
- Story 12.1: article/revision schema, `published`/`hidden` semantics, the `source` CHECK constraint, `create_article`/`update_article_content`.
- Story 12.5: `_sanitize_html` + `is_allowed_image_src` (inline images restricted to our storage buckets — this is why external body images are stripped).
- Story 12.6: the developer docs page to extend.
- Recurring review lessons: validate/format inputs before DB lookups; never leak raw internal errors; guard missing keys with `.get()`; keep public error bodies in one of the two accepted shapes.

### Known v1 limits (documented, not fixed here)

- Inline `<img>` whose `src` is not a PersonnaPress-hosted URL is stripped by the sanitizer. Callers upload images in-app; server-side image sideloading is a deferred follow-up (SSRF surface, own story).
- Markdown tables, `h5`/`h6`, and horizontal rules are flattened by the allowlist. Expanding the allowlist must be mirrored in the editor's DOMPurify config (`BlogEditor.tsx`) or the in-app editor will re-strip on save — deferred as its own change.
- `published_at` is set when the hidden article is created and is not reset when it is later published in-app (`set_article_status` does not touch it). Accepted for v1.

### Deferred follow-ups (not in scope)

- Update/delete a *published* article via API.
- Read-back of a caller's own hidden articles via the write token.
- An `Idempotency-Key` header (v1 idempotency is via explicit slug upsert).
- A thin MCP server / documented tool schema so agents get this as a first-class tool.
- Per-client article cap / audit log of which token created which article.

### Project structure notes

- Backend: migration under `backend/alembic/versions/`; edits to `models.py`, `delivery_tokens.py`, `clients.py`, `public_articles.py`; new `backend/app/core/html_sanitize.py` home for `_sanitize_html`; new `backend/tests/routers/test_article_ingestion.py`.
- Frontend: `DeliveryTokensCard.tsx`, `frontend/lib/api.ts`, `frontend/lib/types.ts`; docs page from Story 12.6.

### References

- [Source: _bmad-output/implementation-artifacts/12-2-public-delivery-api-tokens.md]
- [Source: _bmad-output/implementation-artifacts/12-1-article-model-revision-history.md]
- [Source: _bmad-output/implementation-artifacts/12-5-user-image-uploads.md]
- [Source: _bmad-output/implementation-artifacts/12-6-headless-blog-api-developer-docs-page.md]
- [Source: backend/app/services/articles.py (initial revision + slug + reading-time reuse)]
- [Source: backend/app/routers/articles.py (allowlist sanitizer, PATCH status)]
- [Source: frontend/app/(app)/blog/blog-list.tsx (hidden articles already listed + labeled)]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m]

### Debug Log References

- `pytest tests/routers/test_article_ingestion.py tests/routers/test_delivery_tokens.py tests/routers/test_public_articles.py` -> 74 passed.
- Full backend suite: 94 pre-existing env failures (spacy/textstat/live-DB stubs), unchanged by this story (baseline was 124 failed; delta is the +30 new passing tests here). No new regressions.
- `tsc --noEmit`: no errors in any file touched by this story (pre-existing errors are all in `__tests__/` fixtures).
- Verified `public_app` registers `POST /v1/articles`; CORS `allow_methods` remains `["GET","HEAD","OPTIONS"]`; markdown renderer escapes raw HTML (`<b>` -> `&lt;b&gt;`).

### Completion Notes List

- Added `markdown-it-py>=3.0.0` (raw-HTML passthrough disabled via `MarkdownIt("commonmark", {"html": False})`) — no MD->HTML renderer existed before.
- Lifted `_sanitize_html` + allowlist constants into `app/core/html_sanitize.py`; `routers/articles.py` now imports it (no behavior change), avoiding a router-to-router import.
- New migration `a7f2c9d3e8b1` chains from head `e5a6b7c8d9e0`; adds `scope` Text NOT NULL server_default `'read'` + explicit backfill; downgrade drops the column.
- Write auth dependency `get_delivery_client_write`: 401 on identity failure (missing/malformed/non-ppw_/unknown/revoked/hash-mismatch), 403 `WRITE_SCOPE_REQUIRED` for a valid read-scoped token; reuses `touch_last_used` throttle.
- `POST /public/v1/articles`: 200 KB body cap (413 `CONTENT_TOO_LARGE`) before parse; Pydantic model with `extra="forbid"` and all field caps; nested `VALIDATION_ERROR` 422 shape via a `RequestValidationError` handler on `public_app`; content pipeline (markdown->render->sanitize, html->sanitize) with no generation/voice call; slug upsert-if-hidden (200) / 409-if-published / auto-unique-create (201); explicit `ArticleRevision(revision_number=1, source="initial")`; 60/min limiter keyed on token prefix.
- Frontend: `DeliveryTokensCard` create modal gains a Read-only/Write scope choice, sends `scope`, and the token list shows a scope badge; `lib/types.ts` + `lib/api.ts` updated.
- Docs page extended with a Create Article section (auth, request fields table, request/response examples, Claude/terminal curl) and the two documented v1 limits; error table gained the four new codes. No em-dashes or banned words.

### File List

Backend:
- backend/app/core/html_sanitize.py (lifted `_sanitize_html` + allowlist here)
- backend/app/routers/articles.py (import sanitizer from new home; removed duplicate)
- backend/app/routers/public_articles.py (write auth dep, ingestion endpoint, validation handler, markdown renderer)
- backend/app/db/repositories/models.py (`DeliveryToken.scope`)
- backend/app/db/repositories/delivery_tokens.py (`generate_raw_token(scope)`, persist scope)
- backend/app/routers/clients.py (pass + return scope)
- backend/app/schemas/client.py (`scope` on create/list/create-response)
- backend/alembic/versions/20260920_0001_a7f2c9d3e8b1_add_scope_to_delivery_tokens.py (new)
- backend/requirements.txt (markdown-it-py)
- backend/tests/routers/test_article_ingestion.py (new)
- backend/tests/routers/test_delivery_tokens.py (scope tests + mock fix)

Frontend:
- frontend/lib/types.ts (`DeliveryTokenScope`, `scope` fields)
- frontend/lib/api.ts (create sends `scope`)
- frontend/components/publishing/DeliveryTokensCard.tsx (scope choice + badge)
- frontend/app/(public)/headless-blog-api/docs/page.tsx (Create Article section + errors + limits)

### Review Findings

Three-layer adversarial review (blind-hunter, edge-case-hunter, verification-gap) at Opus capability. No intent_gap or bad_spec findings, so no loopback. Outcome:

- **Patched (applied + re-verified):** The markdown raw-HTML passthrough test only asserted `<script>` was stripped, which the allowlist sanitizer does regardless of the `html=False` flag, so a passthrough regression would ship green. Strengthened it with a benign allowed tag (`<strong>`) whose escape is observable, and added a no-change (`updated:true`, no new revision) upsert coverage test. 48 tests pass.
- **Deferred (real, pre-existing / shared code):** (1) `reading_time_minutes` not recomputed by the shared `update_article_content` on content-replace; (2) `_sanitize_html` allows `target="_blank"` without forcing `rel="noopener noreferrer"`. Both filed in `deferred-work.md`.
- **Rejected (verified false / spec-sanctioned):** empty derived slug (`slug_from_title` already falls back to `"untitled"`); `updated_at`/`created_at` None crash (server defaults populate them); non-`published`/`hidden` status branch (enum is 2-valued); body-buffered-before-cap (413-before-parse met, nginx caps upstream); href obfuscation (prefix allowlist fails closed); `published_at=utcnow()` on hidden (explicit AC7 + documented v1 limit); markdown-it lazy-init race; `_pydantic_errors` fallback (unreachable); and assorted doc/style nitpicks.

## Change Log

- 2026-09-20: Story drafted (ready-for-dev). Write-scoped `ppw_` delivery token + `POST /public/v1/articles` ingestion endpoint creating `hidden` articles verbatim (Markdown/HTML -> sanitized HTML, no transformation), slug upsert-if-hidden / 409-if-published, explicit initial revision, 60/min rate limit. Scope chosen with Boris: reuse `hidden` (no status enum), ignore inline-image/table fidelity and published_at reset (documented limits), no `Idempotency-Key` in v1.
- 2026-09-20: Implemented and reviewed. Migration `a7f2c9d3e8b1` (delivery_tokens.scope), scoped token generation (`ppw_`/`ppd_`), write auth dependency (401/403), ingestion endpoint (413/422/409/201/200), sanitizer lifted to `app/core/html_sanitize.py`, frontend scope toggle, docs page extended. Added `markdown-it-py`. 48 targeted tests pass, tsc clean. Review applied one test-hardening patch, deferred two shared-code items, rejected the rest.

## Suggested Review Order

**Ingestion endpoint (the core of the change)**

- Entry point: the write endpoint - body cap, validate, render/sanitize, slug idempotency, create+revision
  [`public_articles.py:582`](../../backend/app/routers/public_articles.py#L582)

- Write auth dependency: 401 on identity failure, 403 for a valid read-scoped token
  [`public_articles.py:211`](../../backend/app/routers/public_articles.py#L211)

- Markdown renderer with raw-HTML passthrough disabled (html=False)
  [`public_articles.py:487`](../../backend/app/routers/public_articles.py#L487)

- Nested VALIDATION_ERROR shape + request model with extra="forbid" and field caps
  [`public_articles.py:497`](../../backend/app/routers/public_articles.py#L497)

**HTML sanitization (security boundary)**

- Sanitizer + allowlist lifted to a shared home so neither router imports the other
  [`html_sanitize.py:71`](../../backend/app/core/html_sanitize.py#L71)

- Existing editor router now imports the sanitizer from its new home (no behavior change)
  [`articles.py:22`](../../backend/app/routers/articles.py#L22)

**Scope column + token generation**

- New scope column on the token model
  [`models.py:342`](../../backend/app/db/repositories/models.py#L342)

- Prefix encodes scope: ppw_ for write, ppd_ for read
  [`delivery_tokens.py:20`](../../backend/app/db/repositories/delivery_tokens.py#L20)

- Migration: scope Text NOT NULL server_default 'read' + backfill; downgrade drops it
  [`20260920_0001_a7f2c9d3e8b1_add_scope_to_delivery_tokens.py:1`](../../backend/alembic/versions/20260920_0001_a7f2c9d3e8b1_add_scope_to_delivery_tokens.py#L1)

- Token create endpoint accepts + returns scope (validated Literal read|write)
  [`clients.py:404`](../../backend/app/routers/clients.py#L404)

**Frontend token UI**

- Scope choice in the create flow + scope badge in the list
  [`DeliveryTokensCard.tsx:36`](../../frontend/components/publishing/DeliveryTokensCard.tsx#L36)

- API client sends scope; types add DeliveryTokenScope
  [`api.ts:211`](../../frontend/lib/api.ts#L211)

**Developer docs**

- Create Article section: auth, request fields, curl, error codes, v1 limits
  [`page.tsx:77`](../../frontend/app/(public)/headless-blog-api/docs/page.tsx#L77)

**Tests (peripherals)**

- Ingestion suite: auth matrix, sanitization, validation, slug idempotency, tenant isolation, no-generation
  [`test_article_ingestion.py:281`](../../backend/tests/routers/test_article_ingestion.py#L281)

- Token scope tests
  [`test_delivery_tokens.py:1`](../../backend/tests/routers/test_delivery_tokens.py#L1)
