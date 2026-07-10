# Story 8.6: Publish Pipeline — Astro, Next.js, Hugo, Eleventy
<!-- epics.md reference: Epic 8, Story 8.4 (GitHub Blog Publishing Phase 2) -->

---
baseline_commit: 5967290cde0bfc58ded77e996c2f162be29749ac
---

Status: done

## Story

As an authenticated user,
I want to publish my blog post to my modern static site generator repo in the correct content format,
so that my site rebuilds automatically with the new post without any manual file management.

## Acceptance Criteria

1. **Astro:** File written to `src/content/blog/{slug}.mdx` (or `.md` if no `.mdx` files exist in the content directory); front matter uses the Astro content collection schema inferred from `content.config.*` — at minimum: `title`, `description`, `pubDate` (ISO format), `heroImage` (Supabase CDN URL); additional required schema fields are set to empty strings with `# TODO: fill in` comment so the PR is reviewable before merge.
2. **Next.js:** Publish path inferred from repo: if `posts/*.md` exists → write to `posts/{slug}.md`; if `content/*.mdx` exists → write to `content/{slug}.mdx`; if neither pattern found → `confidence` is set to `"low"`, connection card prompts "Content folder not detected. Confirm your publish path before your first post." with a manual path input and "Confirm path" Primary button (calling `PATCH /api/v1/clients/{id}/connections/github/framework`).
3. **Hugo:** File written to `content/posts/{slug}.md`; front matter format (TOML vs YAML) inferred by reading an existing post in `content/posts/`; front matter contains: `title`, `date`, `description`, `draft = false` (TOML) or `draft: false` (YAML), `tags`, `cover.image` (Supabase CDN URL for featured image).
4. **Eleventy:** Configured input directory read from `.eleventy.js` (default `src/`); post written to `{input_dir}/posts/{slug}.md` if `posts/` folder exists there, else `{input_dir}/{slug}.md`; YAML front matter contains: `title`, `date`, `description`, `tags`, `layout` (inferred from existing posts; omitted if not inferable).
5. For all frameworks: at most 3 existing post files are fetched from the content directory to infer front matter patterns; the first file is used as the template. Front matter keys not present in existing posts are NOT introduced.
6. On GitHub API error (429, 403, 422): same retry pattern as Story 8.5 — `jobs.status='failed'`, Retry Panel shown, retry calls `POST /api/v1/campaigns/{id}/publish/retry` with `platform='github_pages'`.
7. The "Publish to GitHub" Secondary button in the Approval Gate appears for all four of these frameworks (not only Jekyll/plain static) when the detected framework is one of: `astro`, `nextjs`, `hugo`, `eleventy`.

## Tasks / Subtasks

- [x] **Backend — Repo file inspection helpers** (AC: 1, 2, 3, 4, 5)
  - [x] `backend/app/integrations/github.py`: Add `list_files_in_directory(installation_token: str, repo: str, path: str, extension: str | None = None) -> list[str]`: calls `get_directory_contents()` (from Story 8.4), filters by extension if provided, returns list of file names; returns `[]` on 404 (directory not found)
  - [x] Add `get_first_post_files(installation_token: str, repo: str, path: str, max: int = 3) -> list[str]`: returns decoded content of up to `max` files from directory (to infer front matter patterns)
  - [x] Add `detect_front_matter_format(content: str) -> "toml" | "yaml"`: checks if first line is `+++` (TOML) or `---` (YAML); defaults to YAML

- [x] **Backend — Astro publish logic** (AC: 1)
  - [x] `backend/app/services/publishing.py`: In `_publish_github()`, add `elif detected_framework == "astro":` branch
  - [x] Check `list_files_in_directory(token, repo, "src/content/blog", ".mdx")` — if files found, use `.mdx` extension; else `.md`
  - [x] Attempt to fetch `content.config.ts` or `content.config.js` via `get_file_contents()`; parse required fields from the schema definition (basic regex: look for `z.string().optional()` vs `z.string()` patterns to identify required vs optional); for required non-standard fields, set `# TODO: fill in`
  - [x] Front matter minimum: `title`, `description`, `pubDate` (ISO 8601 date string), `heroImage` (campaign image URL or empty string)
  - [x] Call `create_file_commit()` for `src/content/blog/{slug}.mdx|md`

- [x] **Backend — Next.js publish logic** (AC: 2)
  - [x] `elif detected_framework == "nextjs":` branch
  - [x] Check `list_files_in_directory(token, repo, "posts", ".md")` — if files found, use `posts/{slug}.md`
  - [x] Else check `list_files_in_directory(token, repo, "content", ".mdx")` — if found, use `content/{slug}.mdx`
  - [x] If neither: set `confidence = "low"` on the connection credential (re-encrypt and upsert); return a `{"status": "low_confidence", "message": "Content folder not detected"}` dict; the frontend renders the manual path prompt when it sees this response (see frontend task)
  - [x] On confirmed path (`publish_path` already set manually): use it directly
  - [x] Infer front matter from existing file in the target directory

- [x] **Backend — Hugo publish logic** (AC: 3)
  - [x] `elif detected_framework == "hugo":` branch
  - [x] Call `get_first_post_files(token, repo, "content/posts", max=1)` to get one existing post
  - [x] Call `detect_front_matter_format()` on that post
  - [x] Build front matter accordingly; `tags` from brand voice profile; `cover.image` = campaign image URL
  - [x] Call `create_file_commit()` for `content/posts/{date}-{slug}.md` (Hugo date-prefix convention)

- [x] **Backend — Eleventy publish logic** (AC: 4)
  - [x] `elif detected_framework == "eleventy":` branch
  - [x] Fetch `.eleventy.js` or `.eleventy.cjs` via `get_file_contents()`; use regex to find `dir.input` value (default: `"src"`)
  - [x] Check if `{input_dir}/posts/` exists via `get_directory_contents()`; if yes, target `{input_dir}/posts/{slug}.md`; else `{input_dir}/{slug}.md`
  - [x] Fetch one existing post for front matter inference; include `layout` if found; omit if not
  - [x] Call `create_file_commit()` for resolved path

- [x] **Frontend — Extend GitHub publish button** (AC: 7)
  - [x] `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`: Extend the `detected_framework` check from Story 8.5 to include `astro`, `nextjs`, `hugo`, `eleventy` — the "Publish to GitHub" button should appear for all six supported frameworks (jekyll, plain_static, astro, nextjs, hugo, eleventy)

- [x] **Frontend — Next.js low-confidence manual path prompt** (AC: 2)
  - [x] In `GitHubConnect.tsx` (from Story 8.4): if the connection's `confidence === "low"` AND `detected_framework === "nextjs"`: render the warning in Inter 14px Graphite: "Content folder not detected. Confirm your publish path before your first post."
  - [x] A bottom-border Input (UX-DR4) for `publish_path`; a "Confirm path" Primary button calls `PATCH /api/v1/clients/{id}/connections/github/framework` with `{"detected_framework": "nextjs", "publish_path": "<user-value>"}`

- [x] **Tests** (AC: 1, 2, 3, 4, 5)
  - [x] `backend/tests/services/test_publishing.py`: Add test cases for each framework branch in `_publish_github()`:
    - Astro: no `.mdx` files found → uses `.md`; `.mdx` files found → uses `.mdx`
    - Next.js: `posts/*.md` found → `posts/{slug}.md`; neither found → `low_confidence` result
    - Hugo: TOML format detected → correct front matter syntax
    - Eleventy: custom `dir.input = "docs"` parsed from `.eleventy.js`
  - [x] Test AC-5: `get_first_post_files` called with max=3; returned files used as template; no new keys introduced

## Dev Notes

### GitHub API Version Header

All calls added to `integrations/github.py` in this story must use the module-level `GITHUB_HEADERS` constant (with `X-GitHub-Api-Version: 2026-03-10`) defined in Story 8.4. Do not hardcode the header per-call.

### Front Matter Inference Rule (AC-5)

Fetch at most 3 existing post files from the target directory. Use the FIRST file as the template. Read its front matter keys. When building the new post's front matter: only include keys that are ALREADY present in the template. This prevents introducing unexpected keys that break site builds. The mandatory minimum fields (`title`, `date`, `description`) are always included even if absent from the template.

```python
# Safe front matter construction
template_keys = parse_front_matter_keys(first_post_content)
front_matter = {"title": ..., "date": ..., "description": ...}  # always included
if "tags" in template_keys:
    front_matter["tags"] = ...
if "layout" in template_keys:
    front_matter["layout"] = infer_layout(first_post_content)
```

### Astro Content Config Parsing Strategy

Avoid trying to fully parse TypeScript/JavaScript. Use simple regex to extract field names with `optional()` vs without. If the parse fails or the config file is absent, fall back to the minimum 4 fields and omit the `# TODO` comments entirely. Resilience > completeness here.

### Hugo Date Prefix Convention

Hugo posts typically use `{YYYY-MM-DD}-{slug}.md` naming. However, some Hugo themes use `{slug}/index.md` (Hugo leaf bundle). To avoid breaking the user's site structure, check if existing posts in `content/posts/` use date-prefixed names or directory-based names. Default to date-prefix only if at least one existing post uses that pattern.

### Eleventy Input Dir Parsing

`.eleventy.js` can return a config object in multiple formats:
```js
module.exports = function(eleventyConfig) {
  return { dir: { input: "src", output: "_site" } };
};
// OR
module.exports = { dir: { input: "docs" } };
```

Use a conservative regex: `input["']?\s*:\s*["']([^"']+)["']`. If the regex doesn't match, default to `"src"`. The input dir value is almost always 2-8 characters.

### Project Structure Notes

**No new files** — all logic added to existing files from Stories 8.3-8.5.

**Modified files:**
- `backend/app/integrations/github.py` — add `list_files_in_directory()`, `get_first_post_files()`, `detect_front_matter_format()`
- `backend/app/services/publishing.py` — add Astro, Next.js, Hugo, Eleventy branches in `_publish_github()`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` — extend framework check for button visibility
- `frontend/components/publishing/GitHubConnect.tsx` — Next.js low-confidence path prompt

### References

- Epics.md: Epic 8, Story 8.4 — full BDD criteria per framework
- Architecture: `integrations/github.py` functions called only from `services/publishing.py` rule
- Story 8.5 (`8-5-publish-pipeline-jekyll-plain-static.md`) — `_publish_github()` function structure and `create_file_commit()` implementation to extend

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `list_files_in_directory()`, `get_first_post_files()`, `detect_front_matter_format()` helpers to `integrations/github.py`; all use module-level `GITHUB_HEADERS`
- Added Astro branch: detects `.mdx`/`.md` via directory listing; parses `content.config.ts/js` for required fields with regex; falls back to 4 minimum fields on parse failure
- Added Next.js branch: checks `posts/*.md` then `content/*.mdx`; returns `low_confidence` dict (updates credential, no exception) when neither found; uses confirmed `publish_path` when set
- Added Hugo branch: detects TOML vs YAML front matter from existing post; detects date-prefix naming convention; includes `cover.image` and `tags`
- Added Eleventy branch: reads `dir.input` from `.eleventy.js`/`.eleventy.cjs` via regex; checks for `posts/` subdir; infers `layout` from existing post front matter
- Extended `FrameworkSelectRequest` with optional `publish_path` field; endpoint uses it when provided (enables Next.js confirmed path flow)
- Extended `frameworkMutation` in `GitHubConnect.tsx` to accept `publishPath` arg; added `manualPublishPath` state + low-confidence UI section
- Extended GitHub publish button in `approval-panel.tsx` to show for all 6 supported frameworks (jekyll, plain_static, astro, nextjs, hugo, eleventy)
- Added `import re` to `publishing.py`
- 10 new tests added covering all 4 framework branches + AC-5 no-new-keys rule; all 49 service tests pass

### File List

- backend/app/integrations/github.py
- backend/app/services/publishing.py
- backend/app/routers/publishing.py
- backend/tests/services/test_publishing.py
- frontend/app/(app)/campaigns/[id]/approval-panel.tsx
- frontend/components/publishing/GitHubConnect.tsx
- frontend/lib/api.ts

### Review Findings

- [x] [Review][Patch] Path traversal in publish_path — no validation against `..` or leading `/`; user can commit to arbitrary repo paths [backend/app/routers/publishing.py:640]
- [x] [Review][Patch] Empty string publish_path stored as high-confidence credential — `is not None` check accepts `""` which writes to repo root [backend/app/routers/publishing.py:640]
- [x] [Review][Patch] low_confidence return swallowed as "success" in dispatch_publish — `_publish_github` returns dict but result is discarded; job marked success with no file written [backend/app/services/publishing.py:534]
- [x] [Review][Patch] Astro pubDate unquoted in YAML — `pubDate: 2026-07-10T12:00:00Z` is unquoted; quote for consistent YAML string handling [backend/app/services/publishing.py:194]
- [x] [Review][Patch] handleConfirmPublishPath hardcodes framework "nextjs" — should derive from activeDetection to avoid credential corruption if another framework reaches low-confidence [frontend/components/publishing/GitHubConnect.tsx:847]
- [x] [Review][Patch] Astro regex false positive for chained optional validators — `z.string().min(1).optional()` multi-line splits across lines making optional_pattern miss; add DOTALL cross-check [backend/app/services/publishing.py:178]
- [x] [Review][Patch] Front matter newline escaping incomplete — title/description from campaign data may contain `\n`; only `\` and `"` are escaped currently [backend/app/services/publishing.py:187]
- [x] [Review][Patch] Tags not escaped for embedded double-quotes — `", ".join(f'"{t}"' ...)` in all new branches; tags with `"` break YAML/TOML [backend/app/services/publishing.py:263]
- [x] [Review][Patch] Hugo YAML image_url not escaped for double-quotes — `cover:\n  image: "{image_url}"` unescaped [backend/app/services/publishing.py:334]
- [x] [Review][Patch] Hugo YAML branch has dead title_yaml alias — `title_yaml` recomputes same value as `title_escaped` then uses title_yaml instead of title_escaped [backend/app/services/publishing.py:322]
- [x] [Review][Patch] SUPPORTED_FRAMEWORKS constant defined inside render callback — new array allocated on each query resolution; move to module-level [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:800]
- [x] [Review][Defer] get_first_post_files makes sequential GitHub API calls — could use asyncio.gather; pre-existing pattern, performance optimization [backend/app/integrations/github.py] — deferred, pre-existing
- [x] [Review][Defer] max parameter name shadows Python builtin — rename to max_count; style cleanup [backend/app/integrations/github.py] — deferred, pre-existing
- [x] [Review][Defer] detect_front_matter_format placed in github.py — no GitHub dependency; architecture cleanup for later [backend/app/integrations/github.py] — deferred, pre-existing
- [x] [Review][Defer] Hugo publish path hardcoded to content/posts — no fallback for content/blog or custom contentDir; Story 8.7 territory [backend/app/services/publishing.py] — deferred, pre-existing
- [x] [Review][Defer] Eleventy .eleventy.mjs (ESM) config not attempted — minor edge case, low impact [backend/app/services/publishing.py] — deferred, pre-existing
