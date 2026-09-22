---
baseline_commit: 8261f6a4249211527960b61994b63d435d588890
---

# Story 12.8: Write-Token Authored Article Read-Back API

Status: done

## Story

As a customer developer or AI agent holding a write-scoped `ppw_` delivery token,
I want authenticated read-back endpoints that return my client's own articles (including the hidden ones I created through the ingestion API),
so that I can verify what I just created, list what already exists, and check whether a slug is taken (and its status) before I create or update, closing the create -> verify -> update loop that Story 12.7 left open.

## Context

Story 12.7 shipped the inbound half of the headless surface: a write-scoped `ppw_` token and `POST /public/v1/articles`, which creates a `hidden` article verbatim and returns `{id, slug, status, edit_url, created_at, updated_at, updated}`. But the write caller is **blind after the write**: it gets those fields back once and can never read the article again through the API. There is no way for an agent to:

1. **Verify** the article it just created (fetch it back by `id`).
2. **List** what it (or the client) already has.
3. **Check a slug before writing** - i.e. "does slug `x` already exist for this client, and is it `hidden` (upsertable) or `published` (409)?" - which is exactly the read-before-write that makes a future update-published story (deferred A1) safe.

The existing public read routes cannot serve this. `GET /public/v1/articles`, `/{slug}`, and `/tags` hard-filter `status="published"` and that filter **is the public isolation guarantee** - Story 12.7's dev notes are explicit: "do not add any parameter that widens it." A hidden article must never appear on those routes.

So read-back must be a **new, separate authenticated surface** that requires the write token and returns the caller's own articles at any status, strictly scoped to the token's `client_id`, without touching or widening the public read routes.

Key facts confirmed against the codebase before writing this story:

- **The public read routes are the isolation boundary and stay untouched.** `list_published_articles` / `get_published_article` / `get_tags_and_categories` (`backend/app/routers/public_articles.py:363,400,434`) all pass `status=ArticleStatus.published` to `list_articles` / hard-check `article.status != published`. This story adds routes; it does not modify these.
- **The write auth dependency already exists and is reusable.** `get_delivery_client_write` (`public_articles.py:211`) returns the token's `client_id`, raising **401 `INVALID_DELIVERY_TOKEN`** on any identity failure and **403 `WRITE_SCOPE_REQUIRED`** for a valid read-scoped (`ppd_`) token. Read-back is a write-holder capability (you can only have hidden articles if you can author them), so these endpoints reuse this dependency: a `ppd_` read token gets 403 and is told to use the public read routes.
- **The repository already supports the query we need.** `list_articles(session, client_id, status=None, tag, category, page, page_size)` (`backend/app/db/repositories/articles.py:41`) returns `(items, total)` scoped to `client_id`; when `status=None` it returns **all statuses**. `get_article_by_slug(session, client_id, slug)` (`articles.py:32`) and `get_article(session, article_id)` (`articles.py:27`) exist - note `get_article` looks up by id **only**, so the endpoint must verify `article.client_id == client_id` itself.
- **Read-back is client-scoped across ALL articles, not just API-authored ones.** This is a deliberate decision (see Critical constraints). Restricting to `campaign_id IS NULL` would make the slug-existence check lie: 12.7's slug-conflict logic checks `(client_id, slug)` across every article regardless of origin, so a campaign-generated published article can own a slug. Read-back must show the same universe the write path checks against, or an agent could think a slug is free when it is not.

## Acceptance Criteria

1. **Given** a valid write-scoped `ppw_` token, **When** `GET /public/v1/authored/articles` is called, **Then** it returns the token's client's articles at **every status** (hidden and published), newest-first, paginated (`page` >= 1 default 1, `page_size` 1..50 default 20), in the envelope `{"data": [...], "meta": {"page", "page_size", "total"}}`. Each item includes `id`, `slug`, `status`, `title`, `excerpt`, `featured_image_url`, `featured_image_alt`, `author`, `tags`, `category`, `published_at`, `updated_at`, `reading_time_minutes`, `edit_url` (`{APP_URL}/articles/{id}`), and `api_authored` (boolean, `true` when `campaign_id IS NULL` - i.e. created through this ingestion API rather than an in-app campaign). Optional query filters: `status` (`hidden` | `published`), `tag`, `category`, and `slug` (see AC2). All responses carry `Cache-Control: no-store`.

2. **Given** the `slug` query filter is provided, **When** the list endpoint runs, **Then** the filter value is FIRST normalized with `slug_from_title` (identically to the write path at `public_articles.py:632`) and the result is looked up via `get_article_by_slug(client_id, normalized)`; it returns at most one item - the matching article at any status, else an empty `data` with `total: 0` - so a caller can reliably predict whether a subsequent `POST /public/v1/articles` with that same `slug` would collide (upsert-if-hidden) or 409 (published). Pagination is ignored when `slug` is present. **Rationale:** the write path stores/looks up the normalized slug, so a raw (un-normalized) lookup here would give false "not found" for e.g. `slug="My Post"` when `my-post` exists - breaking the read-before-write guarantee this endpoint exists to provide.

3. **Given** a valid write token, **When** `GET /public/v1/authored/articles/{article_id}` is called with a UUID that belongs to the token's client, **Then** it returns the full article at any status: all list-item fields plus `html` (defense-in-depth script-stripped via `_strip_scripts`), `meta_description`, and `seo` (the `_build_seo` block). `Cache-Control: no-store`.

4. **Given** the by-id endpoint, **When** the `article_id` does not exist **or** belongs to a different client, **Then** the response is an **identical 404 `ARTICLE_NOT_FOUND`** (never distinguish missing from other-tenant, mirroring `get_published_article`). **When** `article_id` is not a valid UUID, **Then** FastAPI path validation yields **422** in the nested `VALIDATION_ERROR` shape.

5. **Given** authentication, **When** either authored endpoint is called with a missing/malformed/non-`ppw_`/revoked/hash-mismatch token, **Then** the response is **401 `INVALID_DELIVERY_TOKEN`**; **When** it is called with a valid **read-scoped** (`ppd_`) token, **Then** the response is **403 `WRITE_SCOPE_REQUIRED`**. (Reuse `get_delivery_client_write`; `last_used_at` is touched at most once per 60s by that dependency.)

6. **Given** an invalid `status` query value (anything other than `hidden` or `published`), **When** the list endpoint is called, **Then** the response is **422 `VALIDATION_ERROR`** in the nested shape. `page`/`page_size` out of range likewise return 422.

7. **Given** tenant isolation, **When** the security test suite runs, **Then** it proves: a write token for client A never sees any article of client B in the list, cannot fetch client B's article by id (404), and a `hidden` article that IS returned by these authored endpoints is STILL absent from every public route (`GET /public/v1/articles`, `/{slug}`, `/tags`) - i.e. this story does not widen the public filter.

8. **Given** rate limiting and CORS, **When** the authored routes are added, **Then** each is registered on `public_app` with the read-tier limit **120 requests/minute** keyed on token prefix (falling back to IP), returning **429** in the standard shape; **and** `public_app` CORS `allow_methods` remains `["GET", "HEAD", "OPTIONS"]` unchanged (these routes are GET; no new method is added).

9. **Given** the developer docs page (Story 12.6 / 12.7), **When** it is extended, **Then** it documents the two read-back endpoints: auth (`ppw_` bearer), the list endpoint with its filters, the by-id endpoint, the slug-existence-check use case, and the note that a `ppd_` read token receives 403 here and should use the public read routes instead. Includes a copy-paste `curl` example that creates an article then reads it back by `id`. No em-dash / no double-dash in copy.

10. **Given** the read-back endpoints, **When** they run, **Then** they invoke **no** generation, fidelity, voice, or write path - they are pure reads. The existing public read routes and the ingestion endpoint are unchanged in behavior (regression check).

## Tasks / Subtasks

### Task 1: Authored list endpoint (AC: 1, 2, 5, 6, 8, 10)

- [x] 1.1 Add `GET /v1/authored/articles` to `public_app` in `backend/app/routers/public_articles.py`, depending on `get_delivery_client_write` (401/403) and `get_session`. Query params: `page` (ge=1, default 1), `page_size` (ge=1, le=50, default 20), `status` (optional, validated to `hidden`|`published`), `tag` (optional), `category` (optional), `slug` (optional exact match).
- [x] 1.2 When `slug` is provided, normalize it with `slug_from_title` FIRST (mirror `public_articles.py:632`), then resolve via `get_article_by_slug(db, client_id, normalized)` and return a 0-or-1 `data` list (AC 2). Otherwise call `list_articles(db, client_id=client_id, status=<mapped or None>, tag=tag, category=category, page=page, page_size=page_size)` - `status=None` returns all statuses.
- [x] 1.3 Serialize items with a new authored serializer (Task 3). Envelope `{"data": [...], "meta": {"page", "page_size", "total"}}`. Header `Cache-Control: no-store`. Decorate with `@public_limiter.limit("120/minute")`.
- [x] 1.4 Validate `status` to the two allowed values so a bad value yields the nested `VALIDATION_ERROR` 422 (use a `Literal`/enum Query or explicit check that raises `RequestValidationError`; confirm it lands in `_validation_handler`).

### Task 2: Authored detail-by-id endpoint (AC: 3, 4, 5, 8, 10)

- [x] 2.1 Add `GET /v1/authored/articles/{article_id}` (`article_id: uuid.UUID` path param) depending on `get_delivery_client_write` + `get_session`. `@public_limiter.limit("120/minute")`.
- [x] 2.2 Fetch via `get_article(db, article_id)`; if `None` **or** `article.client_id != client_id`, return the identical **404 `ARTICLE_NOT_FOUND`** (`_ARTICLE_NOT_FOUND`, `Cache-Control: no-store`).
- [x] 2.3 On success, build the full body: authored list-item fields + `html` run through `_strip_scripts` + `meta_description` + `seo` from `_build_seo(article)`. Header `Cache-Control: no-store`.

### Task 3: Authored serializer (supports AC 1, 3)

- [x] 3.1 Add `_authored_list_item(article) -> dict` in `public_articles.py` that returns the public `_article_list_item` fields **plus** `id` (str), `status` (`.value` if enum else str), `edit_url` (`{settings.APP_URL.rstrip('/')}/articles/{id}`), and `api_authored` (`article.campaign_id is None`). Reuse `_article_list_item` internally to avoid drift. (The public serializer intentionally omits `id`/`status`/`campaign_id` because the public surface only ever exposes published articles and never leaks internal ids or origin - keep it that way; the authored serializer is the one that adds them. Expose `api_authored` as a boolean, NOT the raw `campaign_id` UUID, which is meaningless to an external caller.) The by-id detail body (Task 2.3) is built on top of this serializer, so it inherits `api_authored` too.

### Task 4: Tests (AC: 7 + all)

- [x] 4.1 New `backend/tests/routers/test_authored_readback.py`: auth matrix (no token / malformed -> 401; `ppd_` read token -> 403; revoked `ppw_` -> 401; valid `ppw_` -> 200); list returns hidden + published for the caller's client; each item carries `api_authored` (`true` for an ingest-created article, `false` for a campaign-created one - assert both); `status` filter (hidden|published) and invalid `status` -> 422; `slug` filter is normalized before lookup (assert `?slug=My Post` resolves the stored `my-post`, matching what the write path would find); `slug` filter returns the one article or empty; by-id happy path returns html (script-stripped) + status + id + edit_url + seo + api_authored; by-id 404 for unknown id and for another client's id (identical); non-UUID id -> 422; `no-store` header on all authored responses; 429 on the limiter.
- [x] 4.2 Isolation assertions (AC 7): a write token for client A never sees client B's articles (list + by-id 404); a `hidden` article returned by the authored endpoints is STILL absent from `GET /v1/articles`, `/{slug}`, and `/tags` (assert against the existing public routes in the same test).

### Task 5: Developer docs (AC: 9)

- [x] 5.1 Extend `frontend/app/(public)/headless-blog-api/docs/page.tsx` with a "Read back your articles" section: the two endpoints, auth, filters, the slug-existence-check use case, the `ppd_` -> 403 note, and a `curl` example that POSTs an article then GETs it back by `id`. No em-dash / no double-dash.

## Dev Notes

### Critical constraints

- **Do NOT modify the public read routes or widen their `status="published"` filter.** `list_published_articles`, `get_published_article`, and `get_tags_and_categories` are the public isolation boundary and must be byte-for-byte behavior-unchanged. This story only ADDS `/v1/authored/*` routes. AC 7 and AC 10 exist to prove you did not touch the public filter.
- **Read-back requires WRITE scope.** Reuse `get_delivery_client_write` - a `ppd_` read token must get **403 `WRITE_SCOPE_REQUIRED`**, not data. Rationale: only a write-capable caller can have hidden articles; read tokens are for public published delivery and already have the public routes. This keeps the scope model clean: `ppd_` = public published read, `ppw_` = author + read-back own content.
- **Client-scoped across ALL articles (any status, any origin).** Every query is filtered by the token's `client_id`. Do NOT additionally filter on `campaign_id IS NULL`. The read-back universe must match the universe 12.7's slug-conflict check inspects (all `(client_id, slug)` rows), or the slug-existence check (AC 2) would give false negatives for campaign-authored slugs. This means a write token can read back the client's in-app / campaign-generated articles too - that is intended: the token represents the client, and the data is the client's own.
- **Tenant isolation on by-id.** `get_article` fetches by id only. The endpoint MUST verify `article.client_id == client_id` and return the identical 404 otherwise - never a different status/body for "exists but not yours" vs "does not exist" (mirrors `get_published_article` at `public_articles.py:411`), so a caller cannot probe another tenant's id space.
- **Private caching only.** All authored responses carry `Cache-Control: no-store`. Hidden content must never be cached by intermediaries or the browser. Do NOT reuse `_CACHE_PUBLIC` / ETag stale-while-revalidate from the public routes; use `_CACHE_PRIVATE` (`"no-store"`, already defined at `public_articles.py:276`).
- **Defense-in-depth on html.** The detail response passes stored `html` through `_strip_scripts` (as `get_published_article` does), even though content was sanitized at write time.
- **Sub-app isolation.** Register the routes, the 120/min limiter, and rely on the existing `public_app` exception handlers (401/403/404/422/429 nested shapes are already wired). Do NOT loosen main-app CORS; do NOT add a method to `public_app` CORS `allow_methods`.
- **Pure reads.** No import or call of `generation`, fidelity, voice, or any write/create path. Add a test asserting no generation function is invoked (mirror 12.7's `test_ingest_does_not_call_generation`).

### Reuse map

| Need | Existing code |
|---|---|
| Write auth dependency (401/403) | `get_delivery_client_write` in `backend/app/routers/public_articles.py:211` |
| List by client + status + tag + category + pagination (status=None -> all) | `list_articles` in `backend/app/db/repositories/articles.py:41` |
| Get by (client_id, slug) | `get_article_by_slug` in `backend/app/db/repositories/articles.py:32` |
| Slug normalization (must mirror the write path) | `slug_from_title` in `backend/app/integrations/github` (same import 12.7 uses at `public_articles.py:44`) |
| Get by id (add client-ownership check in endpoint) | `get_article` in `backend/app/db/repositories/articles.py:27` |
| Public list-item fields (reuse, then add id/status/edit_url) | `_article_list_item` in `public_articles.py:293` |
| SEO / JSON-LD block | `_build_seo` in `public_articles.py:309` |
| Defense-in-depth html strip | `_strip_scripts` in `public_articles.py:347` |
| Private cache header | `_CACHE_PRIVATE` in `public_articles.py:276` |
| Rate limiter (read tier) | `public_limiter` / `@public_limiter.limit("120/minute")`, key `_token_or_ip` (`public_articles.py:57,66`) |
| Error shapes + 404 body | `_ARTICLE_NOT_FOUND`, `_error_detail`, `_token_401`, `_write_scope_403` (`public_articles.py:92,102,192,200`) |
| edit_url pattern | `settings.APP_URL.rstrip("/") + f"/articles/{id}"` in `_ingest_response` (`public_articles.py:565`) |
| Docs page to extend | `frontend/app/(public)/headless-blog-api/docs/page.tsx` |

### Previous story intelligence

- **Story 12.7 (direct dependency):** the `ppw_` write token, `get_delivery_client_write`, `POST /v1/articles`, and the slug semantics (`(client_id, slug)` across all origins; hidden -> upsert, published -> 409). The create response returns the `id` and `slug` an agent feeds into these read-back endpoints. Read its File List and the ingestion endpoint (`public_articles.py:582`) before starting.
- **Story 12.2:** the `ppd_` token mechanism, the `public_app` mount, isolated CORS/limiter/exception handlers, ETag + `Cache-Control` conventions, and the identical-404 pattern (`get_published_article`). The public read routes you must NOT modify live here.
- **Story 12.6:** the developer docs page to extend.
- **Recurring review lessons:** identical 404 for not-found vs other-tenant; validate/parse inputs before DB work (query-param validation must produce the nested `VALIDATION_ERROR` shape); never leak raw internal errors; `no-store` for private/sensitive responses; keep public error bodies in one of the two accepted shapes.

### Design decisions (resolved, for the dev agent - do not re-open)

- **New `/v1/authored/*` path, not a flag on the public routes.** Avoids any chance of widening the public `status="published"` filter and sidesteps the `/v1/articles/{slug}` route collision.
- **By-id detail + list-with-slug-filter, no by-slug detail route.** `id` is what the create response hands back (verify-after-create) and is collision-free as a path param; the `slug` exact filter on the list covers the read-before-write existence check. This keeps v1 minimal and unambiguous.
- **Write scope gates read-back** (not a new "read-hidden" scope) - documented above.

### Project structure notes

- Backend: edits to `backend/app/routers/public_articles.py` only (2 new GET routes + `_authored_list_item`); new `backend/tests/routers/test_authored_readback.py`. **No** migration, **no** model change, **no** new dependency, **no** repository change (existing `list_articles` / `get_article_by_slug` / `get_article` suffice).
- Frontend: docs page (`headless-blog-api/docs/page.tsx`) extension only. **No** in-app UI change (the Article Manager already lists hidden articles for logged-in users; read-back is an API-consumer surface). **No** `DeliveryTokensCard` change (the `ppw_` token already exists from 12.7).

### Deferred follow-ups (explicitly out of scope for this story)

- **A1 - Update/delete a *published* article via API.** This story is the safety prerequisite (read-before-write); the actual published-mutation path, its mandatory revisioning, and the product decision to cross 12.7's "never overwrite a live post" boundary are their own story.
- Read-back of full **revision history** via the write token (list/get `ArticleRevision` rows). Not needed for the verify/list/slug-check loop.
- A `campaign_id IS NULL` "API-authored only" filter, if a caller ever wants to see only what the API channel created (the opposite of this story's all-origins decision).

### References

- [Source: _bmad-output/implementation-artifacts/12-7-public-article-ingestion-api.md]
- [Source: _bmad-output/implementation-artifacts/12-2-public-delivery-api-tokens.md]
- [Source: _bmad-output/implementation-artifacts/12-6-headless-blog-api-developer-docs-page.md]
- [Source: backend/app/routers/public_articles.py (write auth dep, public read routes, serializers, limiter, handlers)]
- [Source: backend/app/db/repositories/articles.py (list_articles, get_article_by_slug, get_article)]

## Change Log

- 2026-09-21: Story drafted (ready-for-dev). Write-token authored read-back: `GET /public/v1/authored/articles` (list all statuses, client-scoped, filters incl. exact slug) + `GET /public/v1/authored/articles/{article_id}` (full article by id, tenant-checked). Reuses `get_delivery_client_write` (ppd_ read token -> 403), `list_articles`/`get_article_by_slug`/`get_article`, existing serializers/limiter/handlers. No migration, no model/frontend-app change; docs page extended. Client-scoped across all origins (consistency with 12.7 slug semantics). A1 (update published) deferred; this is its read-before-write prerequisite.
- 2026-09-21: Self-review refinements folded in before hand-off. (F2) `slug` filter now normalized via `slug_from_title` before lookup (AC2 + Task 1.2), so the read-before-write existence check matches what the write path stores/finds - fixes a false-"not found" for un-normalized slugs. (F3) Each authored item now carries `api_authored` (boolean, `campaign_id IS NULL`) so callers can distinguish ingest-created articles from in-app/campaign content - a semantic boolean, not the raw internal `campaign_id` UUID (AC1, Task 3.1, tests). Dismissed after verification: no `published_at`/`updated_at` null-guard needed (model fields are non-nullable with defaults).
- 2026-09-22: Code review (step-04) complete. 3 patches applied: (1) AUTHORED_DETAIL_RESPONSE docs example now includes `meta_description` and `og` keys in seo block (was missing both); (2) Cache-Control no-store assertion added to both slug-filter tests (normalizes + empty path); (3) `status` field value assertions added to `test_list_item_contains_id_status_edit_url` and `test_byid_happy_path` (were presence-only checks). 6 findings deferred (ppd_/401 pre-existing, slug+status ambiguity, caching section, auth section, error table, curl grep). All 24 tests pass. Story marked done.

## Suggested Review Order

**Entry point — list endpoint (auth, slug path, status filter)**

- List route: write-scope dep, slug normalization + status filter applied, paginated fallback.
  [`public_articles.py:731`](../../backend/app/routers/public_articles.py#L731)

- Slug+status fix: `mapped_status` now applied in the slug fast-exit branch (was silently dropped).
  [`public_articles.py:759`](../../backend/app/routers/public_articles.py#L759)

**By-id endpoint — tenant isolation**

- Identical 404 for missing vs other-tenant; html through `_strip_scripts`; no-store cache.
  [`public_articles.py:794`](../../backend/app/routers/public_articles.py#L794)

**Serializer**

- Extends public list-item with `id`, `status`, `edit_url`, `api_authored`; public route unchanged.
  [`public_articles.py:310`](../../backend/app/routers/public_articles.py#L310)

**Tests — slug+status and empty-slug edge cases**

- Slug+status mismatch returns empty; empty slug falls through to list; tag/category forwarded.
  [`test_authored_readback.py:401`](../../backend/tests/routers/test_authored_readback.py#L401)

**Tests — auth matrix**

- 401 (no token / malformed / revoked), 403 (ppd_ read token); mirrors 12.7 test structure.
  [`test_authored_readback.py:135`](../../backend/tests/routers/test_authored_readback.py#L135)

**Tests — list and by-id correctness**

- All list-item fields, api_authored, slug normalization, Cache-Control on every path.
  [`test_authored_readback.py:194`](../../backend/tests/routers/test_authored_readback.py#L194)

- By-id happy path: html stripped, seo, meta_description, api_authored, no-store.
  [`test_authored_readback.py:497`](../../backend/tests/routers/test_authored_readback.py#L497)

**Tests — isolation: public routes untouched**

- Hidden article absent from public list and slug routes; public filter stays `status=published`.
  [`test_authored_readback.py:617`](../../backend/tests/routers/test_authored_readback.py#L617)

**Developer docs**

- New "Read Back Articles" section: two EndpointBlock components + curl create+readback example.
  [`page.tsx:1127`](../../frontend/app/(public)/headless-blog-api/docs/page.tsx#L1127)

- WRITE_SCOPE_REQUIRED error table: description updated to include authored read-back endpoints.
  [`page.tsx:716`](../../frontend/app/(public)/headless-blog-api/docs/page.tsx#L716)
