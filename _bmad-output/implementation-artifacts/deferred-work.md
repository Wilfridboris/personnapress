# Deferred Work

## Deferred from: code review of 17-1-campaign-article-link-image-panel-nav-retention (2026-07-22)

- Orphaned CDN file when `patchImage` PATCH fails after successful upload — pre-existing 2-step upload pattern; requires CDN cleanup/rollback infrastructure. [frontend/components/campaigns/ImagePanel.tsx:handleReplaceImage]
- No rate-limiting on `PATCH /campaigns/{id}/image` — pre-existing, affects all endpoints. [backend/app/routers/campaigns.py:patch_campaign_image]
- No client-side file size/MIME check before upload — pre-existing from story 12-5 upload pattern; server validates. [frontend/components/campaigns/ImagePanel.tsx:handleReplaceImage]
- `db.refresh` on `AsyncMock` is a no-op in tests — pre-existing test infrastructure limitation. [backend/tests/test_campaigns_router.py]

## Deferred from: code review of 8-9-pricing-tier-revision (2026-07-20)

- Race condition: `current + 1` read-modify-write in `check_campaign_limit` campaign counter — pre-existing pattern used identically in `check_image_limit` and the non-agency path of `check_campaign_limit`; atomic SQL increment would be the proper fix. [backend/app/services/subscription_service.py:153]
- Starter client reduction 3→2 may affect existing starter users already at 3 clients — acknowledged in spec as intentional correction of landing page/code mismatch (page already said "2 clients"); existing users are not ejected, just blocked from adding more. [backend/app/core/constants.py:4]
- `UNLIMITED = 999_999` sentinel is a leaky abstraction — proper fix is `Optional[int]` in `PlanLimits` schema with `is_unlimited` flag in API response; out of scope for this pricing-change story. [backend/app/core/constants.py:1]

## Deferred from: code review of 4-5-blog-editor-link-rel-control (2026-07-18)

- `can().undo()` in `useEditorState` selector creates a temporary transaction on every editor state update — minor performance concern; pre-existing Tiptap pattern, acceptable for this editor size. [frontend/components/campaigns/BlogEditor.tsx:161]
- `handleLinkConfirm` useCallback recreated on every URL keystroke because `linkDialog` is in its dependency array — non-issue since the callback is not passed to memoized children. [frontend/components/campaigns/BlogEditor.tsx:~264]

## Deferred from: code review of 15-2-excerpt-meta-description-content-quality (2026-07-17)

- AC 1.2 — Meta prompt `<!-- meta: ... -->` instruction missing concrete CTA examples ("Learn how to…", "Discover why…") — pre-existing, meta line was not modified by this story; consider adding in a future prompt quality pass. [backend/app/integrations/gemini.py:106]

## Deferred from: code review of 15-1-upload-revision-relearn-ux (2026-07-16)

- No concurrency guard in `triggerRelearn` — backend ingest is idempotent so duplicate calls are safe, but a rapid double-upload could fire two in-flight ingest requests. [frontend/components/clients/FileUploadPanel.tsx:135]
- Stale `historyExpanded` if revision count drops ≤5 then bounces back above 5 — revisions only grow in normal flow; would auto-open panel unexpectedly if somehow count oscillated. [frontend/app/(app)/blog/[id]/article-editor.tsx]
- `clientId` in-flight ingest race on prop change — if component remounts with a different clientId during ingest, setState fires stale context; useEffect cleanup already cancels the 3s dismiss timer, so impact is minimal. [frontend/components/clients/FileUploadPanel.tsx]
- Relearn error state does not auto-clear between upload batches — error banner persists until next triggerRelearn fires and clears it immediately; minimal UX impact. [frontend/components/clients/FileUploadPanel.tsx]

## Deferred from: code review of 14-1-platform-destination-picker (2026-07-16)

- Atomicity hole: `create_or_update_article_from_campaign` committed before `scheduler.add_job` in `publish_headless` scheduled branch — if scheduler raises, article is stranded as `hidden` with no job to flip it; recoverable manually; architectural change needed to fix cleanly. [backend/app/routers/publishing.py]
- APScheduler platforms list serialization across process restart — new connected-platform jobs store `platforms` as a Python list in `args`; pickle/JSON round-trip assumed; pre-existing concern across all APScheduler job args in codebase.
- `platform` field polymorphism `isinstance(c.platform, str)` in `dispatch_publish` — masks a pre-existing ORM inconsistency where some rows store a string and others an enum; not introduced by this story. [backend/app/services/publishing.py]
- WordPress + WordPress.com dedup overrides explicit chip selection — existing precedence logic in `dispatch_publish` drops `wordpress-com` when both are present, regardless of the user's chip selection; pre-existing behavior. [backend/app/services/publishing.py]
- Partial success states in `handlePublishNow`/`handleConfirmSchedule` — if headless succeeds but connected-platform call fails (or vice-versa), only a generic error toast fires with no partial-success feedback; spec does not require atomic rollback. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]

## Deferred from: code review of 3-10-focus-keyword-supporting-keywords (2026-07-15)

- Prompt injection via unsanitized user-controlled text (`secondary_keywords`, `target_keyword`, `target_audience`) interpolated directly into LLM prompt f-string — pre-existing pattern for all three fields; mitigate in a future hardening pass by stripping or encoding newlines. [backend/app/integrations/gemini.py]
- Frontend `maxLength` vs Pydantic `max_length` multi-byte Unicode semantics — `maxLength` counts UTF-16 code units; Pydantic counts code points; pre-existing gap for all text fields.
- No `min_length` guard allows empty-token keywords like `","` — pre-existing; LLM gracefully skips unplaceable terms. [backend/app/schemas/campaign.py]
- No per-keyword count limit on `secondary_keywords` — pre-existing pattern; a future pass could cap individual term count.
- Whitespace-only value could reach `_build_seo_section` via ORM-direct construction bypassing Pydantic — non-production path; only matters for admin scripts or migrations.
- Positional argument fragility in `run_generation_pipeline` → `generate_blog()` call — pre-existing style; consider switching to keyword-only arguments.

## Deferred from: code review of 13-2-featured-image-alt-seo (2026-07-15)

- `max_length=500` on `featured_image_alt` not enforced at DB column level — pre-existing pattern; add `VARCHAR(500)` or CHECK constraint in a future hardening pass. [backend/app/schemas/article.py]
- `og:image:alt` absent from `seo.og` block in public detail endpoint — add `og.image_alt` key to `_build_seo()` to let consumers avoid reconstructing it from the article payload. [backend/app/routers/public_articles.py]
- No character count indicator for alt text input — add a visible counter (e.g., `X / 500`) below the alt field; SEO best practice is under 125 chars. [frontend/app/(app)/blog/[id]/article-editor.tsx]
- `db.add(article)` called on already-tracked ORM object in both `featured_image_url` and `featured_image_alt` blocks — redundant; SQLAlchemy auto-tracks dirty objects. Remove in a future cleanup pass. [backend/app/routers/articles.py]

## Deferred from: code review of 12-5-user-image-uploads (2026-07-14)

- No rate-limiting on `POST /clients/{client_id}/images` — no per-user upload quota or storage quota check; pre-existing infrastructure gap (all endpoints share global limiter with no per-endpoint burst limit). Add per-user daily upload limit when abuse becomes a concern. [backend/app/routers/images.py]

## Deferred from: code review of 12-2-public-delivery-api-tokens (2026-07-13)

- Token prefix collision — only 4 bytes entropy after `ppd_` fixed prefix; `scalar_one_or_none` silently returns None on collision; birthday collision negligible below ~4096 tokens per client. Add DB unique constraint on (client_id, token_prefix) or extend prefix length in a future hardening pass. [backend/app/db/repositories/delivery_tokens.py]
- `/v1/tags` fan-out loads up to 10,000 published articles into memory for tag aggregation; counts silently truncate above that limit. Replace with a DB-level aggregation (unnest + group by) if article volumes grow. [backend/app/routers/public_articles.py]
- `TIMESTAMP(timezone=False)` in delivery_tokens migration — pre-existing pattern across all migrations; safe while app server and DB are both UTC. Migrate to TIMESTAMPTZ in a future infrastructure hardening pass. [backend/alembic/versions/b3c4d5e6f7a8_add_delivery_tokens.py]
- `list_delivery_tokens` returns all tokens (including revoked) with no pagination; acceptable at MVP scale. Add pagination + filter-by-revoked-state when UI needs it. [backend/app/db/repositories/delivery_tokens.py]
- `client_id` FK on delivery_tokens has no ON DELETE CASCADE — orphaned tokens possible after client deletion. Coordinate with client deletion logic (Story 7.3 cleanup scheduler) or add CASCADE in a future hardening migration. [backend/alembic/versions/b3c4d5e6f7a8_add_delivery_tokens.py]
- `If-None-Match` multi-value ETag parsing (RFC 7232 §3.2) — current code does exact equality; a client sending multiple ETags gets 200 instead of 304. Implement proper comma-split comparison in a future caching hardening pass. [backend/app/routers/public_articles.py]

## Deferred from: code review of 12-1-article-model-revision-history (2026-07-13)

- Empty slug — no DB non-empty constraint; `slug_from_title` always produces non-empty in practice; add `CheckConstraint("length(slug) > 0")` in a future hardening pass. [backend/alembic/versions/cc76abfc05a1_add_articles_and_revisions.py]
- `update_article_content` max_rev=None produces revision_number=1 collision — unreachable in normal flow (articles always created with revision 1); add a guard if the article creation/revision path is ever refactored. [backend/app/db/repositories/articles.py]
- `list_articles` page_size unbounded and page=0 silently returns first page — no API caller yet; add validation in Stories 12.2/12.3 when the endpoint is wired. [backend/app/db/repositories/articles.py]
- `set_article_status` accepts any string (no Python-side enum validation) — no external caller yet; add `ArticleStatus(status)` cast when endpoint is added in 12.3. [backend/app/db/repositories/articles.py]
- `create_article` repository function never called by service (service constructs Article directly) — future utility function; clean up or adopt when 12.3 adds an edit endpoint. [backend/app/db/repositories/articles.py]
- Backfill loads all campaigns to memory — acceptable at current scale for an ops script; add `yield_per` pagination if campaign count exceeds thousands. [backend/scripts/backfill_articles.py]
- `updated_at` has no server-side `onupdate` trigger — all update paths in this story set it manually; add `onupdate=sa.func.now()` if a bulk-update migration is ever needed. [backend/alembic/versions/cc76abfc05a1_add_articles_and_revisions.py]

## Deferred from: code review of 3-9-configurable-gemini-model (2026-07-12)

- Empty string is a valid value for `GEMINI_MODEL` — Pydantic accepts it, Gemini client fails at call time. Out of scope per story dev notes ("Do NOT add validation"). Consider `Field(min_length=1)` in a future hardening pass.
- No allowlist/enum constraint on `GEMINI_MODEL` — invalid model names defer to runtime API error. Out of scope per story dev notes.
- Whitespace in `GEMINI_MODEL` not stripped — a padded value causes silent API rejection. Out of scope per story dev notes.
- Module-level `_MODEL` singleton locks the model at import time — no per-request override possible. Pre-existing design; refactor only if A/B or fallback logic is needed.

## Deferred from: code review of 11-9-fix-publish-dedup-no-migration (2026-07-11)

- `error_details` field name is semantically inverted — it now stores success data on complete jobs. Pre-existing design; rename to `result_details` would require a migration. [backend/app/workers/publish.py]
- No concurrency guard before creating a new publish job — multiple simultaneous re-publish jobs possible for the same campaign. Pre-existing gap. [backend/app/routers/publishing.py]
- `get_published_platforms_for_campaign` loads full ORM Job rows when only the `error_details` column is needed — minor I/O overhead for typical use. [backend/app/db/repositories/jobs.py]
- No automated test coverage for new dedup paths: all-already-published, partial re-publish, legacy campaigns with null error_details, concurrent re-publish. Pre-existing project pattern.
- `"already_published"` sentinel value appears in 4 locations with no shared constant or enum — any typo silently breaks the feature. Style concern; refactor when adding tests.

## Deferred from: code review of 11-8-fix-publish-toast-and-character-counter (2026-07-11)

- Toast string "Published successfully." is hardcoded English with no translation key — no i18n system exists today; revisit if localization is added. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- Toast system has no aria-live region for screen-reader announcement — pre-existing accessibility gap in `useUIStore` toast implementation. [frontend/lib/stores/useUIStore.ts]
- No unit tests for polling state machine (complete/failed branches) or character counter colour logic — pre-existing pattern; covered by manual testing.
- Unknown publish job status (not "complete" or "failed") leaves polling interval running indefinitely — pre-existing gap in polling logic. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]

## Deferred from: code review of 11-5-jekyll-frontmatter-author-categories (2026-07-10)

- D1 (LOW): Preview date computed at render time (`new Date()`) vs actual job execution time — the Jekyll frontmatter preview shown to the user will have a slightly different timestamp than the published file. Pre-existing architectural choice; preview is inherently approximate. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- D2 (MEDIUM): Unquoted category items in YAML flow sequences (`categories: [guides, facebook]`) — a category containing `:`, `[`, `]`, or `#` would produce malformed YAML. Intentional per spec AC7 example format; mitigated by newline stripping applied in P1 and typical slug usage pattern. [backend/app/services/publishing.py]

## Deferred from: code review of 11-4-onboarding-platform-connection-step (2026-07-10)

- No test coverage for OAuth return-path mount effect — the `useEffect` in `OnboardingFlow.tsx` that reads `?success`/`?error` and restores `createdClientId` from `sessionStorage` has no unit tests. Pre-existing pattern (OAuth callback flows are not unit-tested); manual test checklist covers it.

## Deferred from: code review of 11-3-github-frontmatter-description-tags (2026-07-10)

- Hugo TOML vs YAML mismatch in `buildFrontMatterPreview` — preview always shows YAML `---` delimiters even when actual published file uses TOML `+++`; pre-existing gap in the preview helper. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- `detectedFramework` state may be empty on first render in the approved-state GitHub panel — `useEffect` timing; pre-existing state management issue not introduced by this story. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]

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

## Deferred from: code review of 3-12-anthropic-content-generation-provider (2026-07-20)

- Unpinned `anthropic` in requirements.txt — pre-existing pattern (`google-genai` also unpinned); add version pin when stabilizing dependency tree. [backend/requirements.txt:27]
- `_md_to_html` DOTALL flag can span multi-line bold across tag boundaries — pre-existing behaviour moved unchanged from gemini.py; assess if LLM output ever triggers this. [backend/app/integrations/generation_prompts.py:232]
- `_strip_fences` no mid-output closing fence detection — pre-existing behaviour moved from gemini.py; only last-line ```` check implemented. [backend/app/integrations/generation_prompts.py:217]
