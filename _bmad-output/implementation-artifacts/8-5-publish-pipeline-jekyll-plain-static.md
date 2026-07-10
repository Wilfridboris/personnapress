---
baseline_commit: 912f44ef33b8fec5b11215fe262a131c3d25a18a
---

# Story 8.5: Publish Pipeline — Jekyll & Plain Static
<!-- epics.md reference: Epic 8, Story 8.3 (GitHub Blog Publishing Phase 2) -->

Status: done

## Story

As an authenticated user,
I want to publish my approved Campaign blog post to my Jekyll or plain static GitHub Pages repo,
so that my post goes live in the correct format without me manually editing any files.

## Acceptance Criteria

1. When the GitHub App is connected and `detected_framework` is `jekyll` or `plain_static` and the Campaign is in `approved` status, a "Publish to GitHub" Secondary button appears in the Approval Gate sticky action footer alongside the existing "Publish now" and "Schedule" buttons.
2. For Jekyll repos: `integrations/github.py` generates a markdown file at `_posts/{YYYY-MM-DD}-{slug}.md`; slug is derived from the blog post H1 (lowercased, spaces → hyphens, non-alphanumeric stripped, max 60 chars); YAML front matter contains `layout: post`, `title`, `date` (ISO 8601), `description` (meta description), `categories` (tags from brand voice profile); the blog HTML is converted to clean Markdown with H1 only in front matter (not repeated in body), H2/H3 preserved, featured image as `![{alt}]({supabase_cdn_url})`.
3. For plain static repos: `integrations/github.py` commits an HTML file at `{publish_path}/{slug}.html` (default publish_path: `docs/` if present, else repo root); the blog HTML is wrapped in a minimal HTML5 shell referencing the existing stylesheet if a `<link>` tag is detectable in `index.html`; a `.nojekyll` file is created at the repo root if not already present.
4. On successful commit (direct commit mode): `campaigns.status` transitions to `published`; the `jobs` record is set to `status='complete'` with `completed_at=now()`.
5. On GitHub API error (429, 403, 422): `jobs.status` is set to `'failed'` with `error_details` containing HTTP status code and GitHub API message; the Approval Gate Retry Panel lists GitHub with its specific error; the retry button calls `POST /api/v1/campaigns/{id}/publish/retry` with `platform='github_pages'`.
6. All GitHub API write calls (blob, tree, commit, update_ref) execute only from within `integrations/github.py` functions; these functions are called only from `services/publishing.py`; decrypted installation tokens do not leave the calling function scope.

## Tasks / Subtasks

- [x] **Prerequisite check** (AC: all)
  - [x] Confirm Story 8.3 Alembic migration (002_github_platform.py) has been applied — `github_pages` in platform enum, `github_pr_url` on campaigns table
  - [x] Confirm `integrations/github.py` exists with `get_installation_token()` from Story 8.3

- [x] **Backend — HTML-to-Markdown conversion** (AC: 2)
  - [x] `backend/app/integrations/github.py`: Add `html_to_markdown(html: str) -> str` utility
  - [x] Use `markdownify` library (add `markdownify>=0.13.1` to `requirements.txt`); strip the H1 from the body (it goes to front matter title only); convert `<img>` tags to `![alt](src)` format; preserve H2, H3, lists, bold, italic, links
  - [x] `slug_from_title(title: str) -> str`: lowercase, replace spaces with hyphens, strip non-alphanumeric, truncate to 60 chars

- [x] **Backend — GitHub write operations** (AC: 2, 3, 6)
  - [x] `backend/app/integrations/github.py`: Add `create_file_commit(installation_token: str, repo_full_name: str, file_path: str, content: str, commit_message: str, branch: str = "HEAD") -> str`:
    - `GET /repos/{repo}/contents/{file_path}` to check if file exists and get SHA (for updates)
    - `PUT /repos/{repo}/contents/{file_path}` with `{"message": commit_message, "content": base64(content), "sha": existing_sha_or_None}`
    - Returns the commit SHA (7-char short form)
  - [x] Add `get_file_contents(installation_token: str, repo_full_name: str, file_path: str) -> str | None`: returns decoded file content or None if 404
  - [x] Add `get_default_branch(installation_token: str, repo_full_name: str) -> str`: `GET /repos/{repo}` → `default_branch`
  - [x] All functions raise `PlatformError("github", status_code, message)` on non-2xx (except 404 returns None in `get_file_contents`)

- [x] **Backend — Jekyll publish logic** (AC: 2, 4, 5)
  - [x] `backend/app/services/publishing.py`: Add `async def _publish_github(campaign, connection_cred: dict, db) -> dict` private function:
    - Decrypts and retrieves `installation_token` (refresh if expired)
    - Reads `detected_framework` from `connection_cred`
    - For `jekyll`: builds front matter from campaign data; calls `html_to_markdown(campaign.blog_html)`; constructs full markdown content; calls `create_file_commit()` with path `_posts/{date}-{slug}.md`
    - For `plain_static`: calls `get_file_contents()` on `index.html` to detect stylesheet; wraps blog HTML in HTML5 shell; calls `create_file_commit()` for `{publish_path}/{slug}.html`; calls `create_file_commit()` for `.nojekyll` if not present (check first with `get_file_contents()`)
    - On success: returns `{"status": "success", "commit_sha": sha}`
    - Raises `PlatformError` on API errors (caller handles retry logic)
  - [x] Extend `dispatch_publish_for_platform()` in `services/publishing.py`: add `elif platform == "github_pages": result = await _publish_github(campaign, cred, db)` branch
  - [x] Update `dispatch_publish()` to include `github_pages` in the platform dispatch loop

- [x] **Backend — Campaign status transition for GitHub** (AC: 4)
  - [x] The existing campaign status transition to `published` in `workers/publish.py` handles this when `dispatch_publish_for_platform()` succeeds
  - [x] For `github_pages` direct commit: set `campaigns.github_pr_url = None` (null, since this is a commit not a PR); Campaign model updated with `github_pr_url` field

- [x] **Backend — Retry endpoint for GitHub** (AC: 5)
  - [x] `github_pages` is already in `ALL_PLATFORMS` in `routers/publishing.py`; retry routes through `dispatch_publish_for_platform()` which now handles `github_pages`

- [x] **Frontend — "Publish to GitHub" button in Approval Gate** (AC: 1)
  - [x] `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`: Add a "Publish to GitHub" button to the sticky action footer
  - [x] Show the button only when: campaign is `approved` AND the active client has a `github_pages` connection with `detected_framework` set to `jekyll` or `plain_static` AND `repo_full_name` is not null
  - [x] Button style: Secondary (UX-DR3 — transparent fill, 1px border, no shadow); `GitBranch` icon from `lucide-react` at 16px with `aria-hidden="true"` and visible label "Publish to GitHub"
  - [x] Clicking this button triggers `campaignsApi.publishNow(campaign.id)` call — the multi-platform dispatch includes `github_pages` automatically
  - [x] The button does NOT replace existing "Publish now" and "Schedule" buttons — all three appear in footer simultaneously

- [x] **Frontend — Connection data in Approval Gate** (AC: 1)
  - [x] `approval-panel.tsx`: Fetches platform connections via existing `fetchAPI` call; extended to extract `github_pages` connection and check `github_detection.detected_framework` for `jekyll`/`plain_static`

- [x] **Tests** (AC: 2, 3, 5, 6)
  - [x] `backend/tests/integrations/test_github.py`: Test `create_file_commit()` success, 403/422 → PlatformError; test `html_to_markdown()` — H1 stripped from body, image converted to markdown; test `slug_from_title()`; test `get_file_contents()` success and 404
  - [x] `backend/tests/services/test_publishing.py`: Test `_publish_github()` with mocked integration — Jekyll path produces correct front matter + markdown file call; plain static path produces HTML5 shell + .nojekyll call; skips .nojekyll when file already exists; omits categories when no tags

## Dev Notes

### GitHub API Version Header

Every call in `integrations/github.py` must include `X-GitHub-Api-Version: 2026-03-10`. Use the module-level `GITHUB_HEADERS` constant defined in Story 8.4 dev notes — do not repeat the header inline per call.

### Secret Scope Rule (Critical)

The decrypted `installation_token` must be obtained inside `_publish_github()` and passed directly to the integration functions in the same call. It must not be stored in a variable that outlives the function or passed to other service functions.

### Jekyll Front Matter Requirements

The `categories` field comes from `campaign.voice_score` (JSON) or the brand voice profile's `tags` field — check the exact Campaign model field. If no tags are available, omit `categories` from front matter rather than setting it to `[]`.

### Plain Static `.nojekyll` Check

Before creating `.nojekyll`, call `get_file_contents(token, repo, ".nojekyll")`. If it returns a non-None result (even empty string), skip the create step. This avoids unnecessary commits and 422 conflicts.

### markdownify Usage

```python
from markdownify import markdownify as md
body_md = md(html, heading_style="ATX", newline_style="backslash")
```

Strip the H1 before converting OR remove the first `# Heading` line from the markdown output. Do NOT include the H1 in the body since it lives in the front matter `title` field.

### PlatformError Mapping for Retry Panel

The Retry Panel (UX-DR15) reads `error_details` from the failed job. Make sure the `error_details` JSON includes:
```json
{"platform": "github_pages", "status_code": 422, "message": "...github api message..."}
```
This matches the existing format used by `wordpress.py`, `webflow.py` etc.

### Approval Gate Button Visibility Logic

The GitHub publish button visibility requires:
1. `campaign.status === "approved"`
2. Active client has a `platform_connections` entry with `platform === "github_pages"` and `connected === true`
3. The connection's account_identifier (or a separate field) includes `detected_framework` in `["jekyll", "plain_static"]`

Point 3 is the tricky one — the `account_identifier` in the list response only shows `repo_full_name`. Consider returning `detected_framework` in the connection list response so the frontend can make this decision without an extra API call.

### Project Structure Notes

**New dependency:**
- `backend/requirements.txt`: `markdownify>=0.13.1`

**Modified files:**
- `backend/app/integrations/github.py` — add commit/tree/markdown functions
- `backend/app/services/publishing.py` — add `_publish_github()` + github_pages branch in dispatch
- `backend/app/routers/publishing.py` — verify retry endpoint handles github_pages
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` — add GitHub publish button
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` — fetch connections to drive button visibility

### References

- Epics.md: Epic 8, Story 8.3 — full BDD criteria including file path and front matter specs
- Architecture: `services/publishing.py` dispatch pattern (existing `dispatch_publish_for_platform()` function)
- Architecture: "integrations/github.py functions called only from services/publishing.py" rule (architecture.md line ~961)
- Architecture: Approval Gate components — `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
- UX-DR3: Secondary button spec (transparent, 1px Ink border)
- UX-DR15: Retry Panel — reads `jobs.error_details`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `github_pr_url: Optional[str]` to Campaign model in `models.py` (was missing; migration `f1a2b3c4d5e6` already added it to the DB schema).
- Added `markdownify>=0.13.1` to `requirements.txt` for HTML→Markdown conversion.
- `integrations/github.py`: Added `slug_from_title()`, `html_to_markdown()`, `get_file_contents()`, `get_default_branch()`, `create_file_commit()`. All use `GITHUB_HEADERS` constant. Non-2xx responses raise `PlatformError("github", ...)`.
- `services/publishing.py`: Added `_refresh_token_if_needed()` helper and `_publish_github()` implementing Jekyll (front matter + markdown file) and plain_static (HTML5 shell + .nojekyll) paths. Extended both `dispatch_publish_for_platform()` and `dispatch_publish()` with `github_pages` branch. Token scoped to calling function.
- `approval-panel.tsx`: Added `githubPublishReady` and `isPublishingGitHub` state; extended connections `useEffect` to detect `github_pages` with `jekyll`/`plain_static` framework; added `handlePublishGitHub` callback; "Publish to GitHub" button (Secondary UX-DR3 style, `GitBranch` icon) appears alongside existing buttons only when GitHub is ready.
- Note: `lucide-react` in this project does not export a `Github` icon — used `GitBranch` instead as it is the closest semantic alternative available.
- 15 new tests added: 11 in `test_github.py` (slug, markdown, create_file_commit, get_file_contents) + 4 in `test_publishing.py` (_publish_github Jekyll and plain_static paths). All 15 pass. No regressions (42 pre-existing failures unchanged).

### File List

- `backend/app/db/repositories/models.py`
- `backend/app/integrations/github.py`
- `backend/app/services/publishing.py`
- `backend/requirements.txt`
- `backend/tests/integrations/test_github.py`
- `backend/tests/services/test_publishing.py`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`

### Review Findings

- [x] [Review][Patch] Empty slug fallback missing in `slug_from_title` — returns empty string for emoji/all-special-char titles, producing invalid paths like `_posts/2026-07-09-.md` [backend/app/integrations/github.py:26]
- [x] [Review][Patch] YAML injection: title/description with double quotes break Jekyll front matter [backend/app/services/publishing.py:92-94]
- [x] [Review][Patch] YAML injection: tag values with double quotes break Jekyll categories line [backend/app/services/publishing.py:82]
- [x] [Review][Patch] Plain-static HTML5 shell embeds raw blog_html — malformed closing tags can break shell structure; use BeautifulSoup re-serialization [backend/app/services/publishing.py:123]
- [x] [Review][Patch] `BeautifulSoup` imported inline inside function body — move to top-level import [backend/app/services/publishing.py:64]
- [x] [Review][Patch] `BeautifulSoup` imported inline inside `html_to_markdown` — move to top-level import [backend/app/integrations/github.py:31]
- [x] [Review][Patch] Jekyll date hardcoded to midnight UTC (`T00:00:00Z`) instead of actual publish datetime [backend/app/services/publishing.py:93]
- [x] [Review][Patch] `handlePublishGitHub` has no guard for missing `job_id` in API response — `setActiveJobId(undefined)` could break job polling [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:148]

## Change Log

- 2026-07-09: Story 8.5 implemented — Jekyll & plain-static GitHub Pages publish pipeline. Added HTML-to-Markdown conversion, GitHub Contents API write operations, `_publish_github()` service function, github_pages branch in dispatch functions, Campaign model `github_pr_url` field, "Publish to GitHub" button in Approval Gate. 15 new tests all passing.
- 2026-07-09: Code review — 8 patches applied (empty slug fallback, YAML injection escaping for title/description/tags, BeautifulSoup top-level imports, Jekyll publish datetime, HTML5 shell safe re-serialization, job_id guard in handlePublishGitHub).
