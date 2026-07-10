# Deferred Work

## Deferred from: code review of 8-4-repo-framework-detection-engine (2026-07-09)

- Token refresh race condition under concurrent requests — two tasks can both observe an expiring token, refresh independently, and overwrite each other's DB writes. [backend/app/routers/publishing.py:_refresh_github_token_if_needed]
- No rate limiting or cooldown on POST /detect endpoint — each call issues up to 10 GitHub API requests; add per-client cooldown when abuse becomes a concern. [backend/app/routers/publishing.py:detect_github_framework]
- `detect_framework` makes up to 9 sequential GitHub API calls with no retry-after logic on rate limit — add retry/backoff when GitHub secondary rate limiting triggers. [backend/app/services/repo_detection.py:detect_framework]
- Case-sensitive filename matching in `_find()` — repos with mixed-case config files (e.g., `_Config.yml`) won't match; inherent to git, acceptable for now. [backend/app/services/repo_detection.py:_find]
- `get_repo_root_contents` doesn't handle 301/302 redirects for renamed repos or >1000-entry roots — add pagination/redirect handling when needed. [backend/app/integrations/github.py:get_repo_root_contents]
- `_refresh_github_token_if_needed` raises HTTPException from a utility function, coupling it to the HTTP layer — refactor to PlatformError + router translation if reused outside routers. [backend/app/routers/publishing.py:_refresh_github_token_if_needed]
- DB write failure during token refresh leaves in-memory and persisted creds out of sync — next request will re-refresh; low probability, pre-existing pattern. [backend/app/routers/publishing.py:_refresh_github_token_if_needed]

## Deferred from: code review of 8-7-pr-first-workflow-preview-direct-commit (2026-07-10)

- BackgroundTask durability — `publish_github_job` is fire-and-forget with no retry if worker crashes mid-job; pre-existing pattern shared with `run_publish`. [backend/app/workers/publish.py]
- Preferences stored in encrypted credential blob — `direct_commit_default` in same envelope as installation token; coupling will cause preference loss on token rotation; refactor to separate user-settings table when warranted. [backend/app/routers/publishing.py]

## Deferred from: code review of 8-3-github-app-oauth-repository-connection (2026-07-09)

- `get_installation_repositories` uses `per_page=100` with no pagination — installations with >100 repos silently truncated; add Link header pagination when needed. [backend/app/integrations/github.py]
- Stale installation token remains in DB if `upsert_connection` fails during token refresh in `list_github_repos` — next call will re-refresh; low probability. [backend/app/routers/publishing.py:list_github_repos]
- CSRF cookie-stuffing via subdomain takeover with `SameSite=Lax` on `github_oauth_state` cookie — existing pattern across all OAuth flows; subdomain takeover is a separate concern. [frontend/app/api/auth/github/route.ts]
- Architecture: `decrypt_credential` called in router for connection management endpoints — spec rule "decrypt only in service layer" targets the publish path; existing `_extract_identifier` already does this. [backend/app/routers/publishing.py]
- No "Change repository" CTA when `connected-with-repo` state — user must disconnect and reconnect to change repo; spec is ambiguous; acceptable UX for MVP. [frontend/components/publishing/GitHubConnect.tsx]
- Token auto-refresh only in `list_github_repos`, not in publish path — must be added in story 8.5 when `services/publishing.py` GitHub publish handler is implemented. [backend/app/routers/publishing.py]
- `_check_github_ownership` returns 403 for non-existent client (vs 404 in other endpoints) — intentional security-by-obscurity; consistent with `test_connect_github_404_client_not_found` asserting 403. [backend/app/routers/publishing.py]
- `httpx.RequestError`/`TimeoutException` not caught in `github.py` — pre-existing pattern across all integrations (linkedin, twitter, webflow also unguarded); address as cross-cutting concern. [backend/app/integrations/github.py]
- No rate limiting / idempotency on `POST /clients/{id}/connections/github` — repeated calls silently overwrite existing connection; auth ownership check limits blast radius. [backend/app/routers/publishing.py:connect_github]

## Deferred from: code review of 8-8-github-publisher-landing-page (2026-07-10)

- Pricing in JSON-LD hardcoded ($29/$79/$199) — will silently go stale on pricing changes; no connection to config constants or DB. [frontend/app/github-publisher/page.tsx]
- Comparison table competitor data (Pages CMS, Decap CMS) unsubstantiated booleans with no audit mechanism; acceptable for MVP. [frontend/app/github-publisher/page.tsx]
- `lastModified: new Date()` in sitemap stamps all URLs as modified on every deploy — misleads crawlers; pre-existing pattern. [frontend/app/sitemap.ts]
- `style={{ borderRadius: 0 }}` repeated as inline style on 6+ elements; should be a Tailwind class when design system is formalized. [frontend/app/github-publisher/page.tsx]
- "See it work" terminal section heading is content-free; a keyword-rich heading would improve SEO. [frontend/components/marketing/TerminalDemo.tsx:64]
- Two consecutive `bg-paper px-6 py-20` sections (terminal + frameworks) have no visual separator; renders as one continuous block. [frontend/app/github-publisher/page.tsx]
- `dangerouslySetInnerHTML` + `JSON.stringify(jsonLd)` lacks `</script>`-sequence escaping; safe while data is static but unsafe if any field becomes dynamic. [frontend/app/github-publisher/page.tsx]
- Terminal animation has no skip/complete-immediately affordance for users who scroll past mid-animation. [frontend/components/marketing/TerminalDemo.tsx]
- `renderWithCheckmarks` splits on literal ✓ (U+2713); brittle if terminal text is copy-pasted with a look-alike codepoint. [frontend/components/marketing/TerminalDemo.tsx:17]

## Deferred from: deploy.sh status/log fix (2026-07-08)

- `systemctl is-active` validates systemd process state only, not application-level readiness (e.g., HTTP server fully bound). If the service type is `oneshot` or startup is async, the check may pass before traffic can be served — `deploy.sh:32`.
- `git pull origin main` has no non-fast-forward protection: if main was force-pushed, the pull fails mid-deploy leaving new pip deps installed but migration not run — pre-existing in `deploy.sh`.
- No rollback on `alembic upgrade head` failure: failed migration leaves the DB in a partially upgraded state with no automated revert — pre-existing in `deploy.sh`.

## Deferred from: code review of 3-7-seo-aware-content-generation (2026-07-09)

- `tone_score`/`cadence_score`/`jargon_violations` in `check_fidelity()` accept floats (not strictly int) — only the new `seo_h2_count` field enforces strict int; pre-existing validation gap in `backend/app/integrations/gemini.py`
- `_FIDELITY_PROMPT` asks Gemini to count `<h2>` tags in the blog HTML — LLMs are unreliable HTML parsers; deterministic counting from the actual HTML (already done in `generate_blog`) would be more accurate; pre-existing design decision in `backend/app/integrations/gemini.py`

## Deferred from: code review of 3-6-image-generation-quality (2026-07-08)

- Blog title with apostrophe/single-quote formats awkwardly inside wrapping quotes in `_build_image_prompt` (`backend/app/services/image.py:49`) — pre-existing in both old and new prompt formats
- No dimension validation for out-of-range width/height values passed to FLUX 1.1 Pro API (`backend/app/integrations/replicate.py`) — pre-existing, API will reject invalid values at runtime
- `brand_voice_profile` truthy check passes for non-dict types; `.get()` would raise AttributeError if DB returns a JSON scalar (`backend/app/services/image.py:33`) — pre-existing
- Empty/whitespace-only blog title edge case: H1 containing only HTML tags not covered by tests — pre-existing (caller has `or "Untitled"` fallback)
- `tone_list[:2]` on a non-list value (e.g. comma-separated string from DB) returns characters not tones (`backend/app/services/image.py:43`) — pre-existing
- `_build_image_prompt` tested via direct private import rather than through the public service API surface (`backend/tests/services/test_image.py`) — pre-existing test pattern

## Deferred from: code review of 11-2-app-ux-campaign-connections-publishing (2026-07-10)

- `platformLabel` helper duplicated verbatim in approval-panel.tsx and campaigns/new/page.tsx — extract to shared `lib/platformLabel.ts` utility when a third caller is added. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx, frontend/app/(app)/campaigns/new/page.tsx]

## Deferred from: code review of 11-1-public-nav-seo-links (2026-07-10)

- No mobile/responsive navigation in PublicHeader — pre-existing, inline header had the same issue; add hamburger menu below md breakpoint when mobile nav is prioritized
- Logo intrinsic dimensions `width={128} height={128}` are square for a wide logo — pre-existing, spec-prescribed extraction; update to match actual logo aspect ratio when image assets are audited
- `priority` on logo image in PublicHeader applies to all public pages — logo is above fold on all pages (sticky header) so acceptable; revisit if CWV regression observed on inner pages
