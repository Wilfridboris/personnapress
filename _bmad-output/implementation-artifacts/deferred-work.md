# Deferred Work

## Deferred from: code review of 5-6-wordpress-com-oauth-integration (2026-07-03)

- CSRF state-in-cookie pattern — standard OAuth PKCE-less flow, consistent with X/LinkedIn implementations already in production.
- Session cookie forwarding to backend — pre-existing project pattern documented in prior story reviews.
- WP_COM_CLIENT_SECRET defaults to "" — same pattern as all other OAuth secrets (LINKEDIN_CLIENT_SECRET, etc.).
- Cookie Secure only in production — pre-existing, X/LinkedIn callback routes identical.
- _extract_title null-safety — pre-existing imported function from wordpress.py, outside this story's scope.
- Safari ITP may strip lax cookie on cross-site redirect — pre-existing; X/LinkedIn same-site pattern, not yet reported in prod.
- Parallel tabs overwrite state cookie — pre-existing pattern affecting all OAuth flows.
- Disconnect error handling silently ignored — pre-existing UI pattern across all platform cards.
- publish_post URL return value discarded — consistent with all platform integrations (wordpress, webflow, x, linkedin).
- scope=global requests full WordPress.com access — spec-mandated (AC4 explicitly specifies scope=global).

## Deferred from: code review of 5-4-scheduled-publishing (2026-07-03)

- **D1 (Medium)**: Concurrent schedule requests TOCTOU — two simultaneous POSTs for the same campaign can both pass the `campaign.scheduled_at is None` guard, creating duplicate scheduled jobs. Requires `SELECT FOR UPDATE` row-level locking. Out of scope for this story.
- **D2 (Low)**: Magic strings for job_type/status — `"scheduled_publish"` and `"scheduled"` used as raw strings in repository queries and create calls. Pre-existing pattern throughout codebase; should be consolidated into enums in a future refactor.

## Deferred from: code review of 5-3-immediate-multi-platform-publishing (2026-07-03)

- **D1 (Medium)**: Published footer missing platform names — AC7 requires "Published to [Platform] — [Date], [Time]." but dev notes explicitly allow v2 deferral when URLs aren't stored. Frontend shows "Published — [date]" only. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- **D2 (Story 5.5)**: Retry Panel not rendered on publish failure — `approval-panel.tsx` shows error toast but no RetryPanel component. Explicitly scoped to Story 5.5. [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- **D3 (Low)**: `str(exc)` in `results[platform]` could theoretically expose exception messages containing credentials — integrations never hold raw creds so real-world risk is negligible. [backend/app/services/publishing.py:78]
- **D4 (Low)**: `_extract_title` duplicated in `webflow.py` and `wordpress.py` — same implementation, should be extracted to a shared utility module in a future cleanup story.

## Deferred from: code review of 5-2-platform-connection-setup-x-twitter-linkedin-oauth (2026-07-03)

- `get_user_handle` returns "unknown" silently on failure — acceptable degradation, connection still stored. [backend/app/integrations/twitter.py]
- `useEffect` empty deps in PlatformConnectionsClient — intentional run-once on mount, acknowledged with eslint suppression. [frontend/components/publishing/PlatformConnectionsClient.tsx]
- Cookie forwarding passes all cookies to backend — documented project pattern for session forwarding (same as Google OAuth callback). [frontend/app/api/auth/x/callback/route.ts]
- `connectionsUrl` computed from cookie before state validation — same-origin redirect only, no external open redirect risk. [frontend/app/api/auth/x/callback/route.ts]
- `refresh_token` stored with no refresh logic — X tokens expire in 2 hours; refresh flow is future story work (Story 5.5 or later). [backend/app/routers/publishing.py]

## Deferred from: code review of 4-3-social-post-editing-with-character-counters (2026-07-02)

- **W1 (High)**: Backend schema allows x_post/linkedin_post up to 5000 chars — platform limits (280/1300) not enforced at DB schema layer; only visual danger indicators in UI. [backend/app/schemas/campaign.py]

## Deferred from: code review of 4-4-approve-reject-campaign (2026-07-02)

- **W1 (Medium)**: Race condition — non-atomic status check+write on `/approve`, `/reject`, `/regenerate`: two concurrent requests can both pass the status guard before either commits. Requires SELECT FOR UPDATE or optimistic locking. Pre-existing systemic pattern across all campaign mutations. [backend/app/routers/campaigns.py]
- **W2 (Medium)**: `check_campaign_limit` TOCTOU gap on concurrent `/regenerate`: two simultaneous regenerate calls both pass limit check before either commits, creating one extra campaign. Same gap exists in `POST /campaigns`. Pre-existing systemic issue. [backend/app/routers/campaigns.py:290]
- **W2 (Medium)**: No timeout/abort on campaignsApi.patch() — if the network request hangs, isSaving remains true indefinitely with the button stuck disabled. Pre-existing pattern across the app. [frontend/components/campaigns/SocialPostEditors.tsx:handleSave]
- **W3 (Medium)**: No test asserting Save button is disabled (not just absent) while isSaving=true — low-value coverage gap. [frontend/__tests__/components/SocialPostEditors.test.tsx]
- **W4 (Low)**: AC5 tab order gap when Save button absent (isDirty=false) — Tab from LinkedIn textarea reaches unrelated elements before Approve/Reject footer. No tabIndex or focus management applied. [frontend/components/campaigns/SocialPostEditors.tsx]

## Deferred from: code review of 4-2-blog-post-wysiwyg-editing (2026-07-02)

- **D1 (Medium)**: Race condition — PATCH status check is non-atomic; a concurrent approve/reject could slip past the `pending_approval` guard before either commits. Needs `SELECT ... FOR UPDATE` or optimistic lock. [backend/app/routers/campaigns.py:patch_campaign]
- **D2 (Low)**: `onSave` prop declared in BlogEditorProps but never invoked after successful save — Story 4.4 must wire this up when orchestrating the approve flow. [frontend/components/campaigns/BlogEditor.tsx]
- **D3 (Low)**: `getCurrentHtml` forwardRef not passed from page.tsx — by design; Story 4.4 will add the ref when wiring the approve button. [frontend/app/(app)/campaigns/[id]/page.tsx]

## Deferred from: code review of 4-1-approval-gate-campaign-preview-voice-fidelity-badge (2026-07-02)

- **D1 (High)**: VoiceScore null safety — TypeScript types declare `number` but runtime API could return `null`. Add integration test or Zod validation at API boundary in a future story.
- **D2 (High)**: `id="voice-detail"` collision — hardcoded ID would break if VoiceFidelityBadge is ever used more than once per page. Refactor to use `useId()` hook when component is reused beyond single-instance context.
- **D3 (Medium)**: ApprovalPanel + sticky footer double-render for `isPending` — intentional stub; Story 4.4 dev agent must remove or hide `ApprovalPanel` when wiring the sticky footer.
- **D4 (Low)**: `lg:left-[240px]` and `pb-24` are hardcoded — tie to a CSS custom property or Tailwind token if sidebar width or footer height changes.

## Deferred from: code review of 3-3-blog-social-content-generation-pipeline (2026-07-02)

- **D1 (Low)**: `update_campaign_content`/`update_job_status` defined in repositories but unused — `services/generation.py` does direct ORM mutations instead. Design inconsistency; refactor in a future cleanup story. [backend/app/db/repositories/campaigns.py, jobs.py]
- **D2 (Low)**: `_strip_fences` helper not refactored into `extract_brand_voice` — pre-existing duplicate logic in gemini.py. Consolidate in a future cleanup. [backend/app/integrations/gemini.py:extract_brand_voice]
- **D3 (Medium)**: Prompt injection risk via user-supplied `brain_dump` interpolated directly into Gemini prompts — systemic security concern affecting all generation functions. Requires input sanitization strategy at the service boundary. [backend/app/integrations/gemini.py:generate_blog, generate_social]

## Deferred from: code review of 3-2-generation-job-polling-typewriter-animation (2026-07-02)

- **D1 (Medium)**: State machine gap — job status values outside `["pending", "in_progress", "complete", "completed", "failed"]` cause undefined UI behavior (neither polling nor terminal). Backend contract should enumerate all possible values. [frontend/hooks/useJobStatus.ts, frontend/components/campaigns/CampaignGenerationOverlay.tsx]
- **D2 (Low)**: Null data polling loop — if `jobsApi.get` returns null without throwing for a non-existent jobId, `refetchInterval` returns 2000ms indefinitely with no backoff. Needs error-state handling. [frontend/hooks/useJobStatus.ts]
- **D3 (Low)**: Hydration mismatch on `prefersReducedMotion` — SSR renders animated version, client may switch to reduced-motion. Intentional progressive enhancement pattern; suppress with `suppressHydrationWarning` if needed. [frontend/components/campaigns/TypewriterAnimation.tsx]
- **D4 (Low)**: `router.refresh()` fired 1500ms after `invalidateQueries` without awaiting completion — under slow networks, server component may render with stale cache data. [frontend/components/campaigns/CampaignGenerationOverlay.tsx]
- **D5 (Medium)**: AC 7 in-app navigation modal not implemented — `beforeunload` guard covers tab close/reload but not in-app link clicks. Deferred per Dev Notes as complex. Implement via NavigationGuard context or Next.js route interceptors in a future story.

## Deferred from: code review of 3-1-brain-dump-input-campaign-creation (2026-07-02)

- **D1 (Critical)**: `campaigns_used` is never reset to 0 when a billing cycle renews — pre-existing issue in the Stripe webhook handler (`_handle_subscription_updated`). Users who exhaust their monthly quota are permanently blocked after cycle renewal. Fix: set `sub.campaigns_used = 0` in the renewal handler. [backend/app/services/subscription_service.py]
- **D2 (Medium)**: `GET /campaigns` returns all campaigns for the user with no `limit`/`offset` — will become a performance issue for agency-tier users. Needs pagination. [backend/app/routers/campaigns.py:list_campaigns]
- **D3 (Planned)**: `run_generation` is a stub (`pass`) — intentional for Story 3.1. Story 3.3 fills in the Gemini generation logic. [backend/app/workers/generate.py]

## Deferred from: code review of 2-7-onboarding-flow (2026-07-02)

- **D1 (Medium)**: Old JWT token remains valid until expiry in multi-tab scenario — completing onboarding in one tab issues a new cookie but tabs holding the old token still see `onboarding_completed=false` until expiry. Requires a server-side session store (e.g., Redis) to invalidate old tokens. [backend/app/services/auth_service.py]
- **D2 (Medium)**: Dashboard server component fetches (`getStats`, `getRecentCampaigns`) do not forward the session cookie — backend 401s are silently swallowed, dashboard shows empty data. Pre-existing design (same-network intent); fix in a future auth-header-on-SSR story. [frontend/app/(app)/dashboard/page.tsx]
- **D3 (Low)**: Brain dump `?prefill=` URL encoding can produce 30KB+ URLs exceeding proxy limits — stub routing in this story will be replaced by Story 3.5 full campaign creation endpoint, eliminating the issue. [frontend/components/onboarding/OnboardingFlow.tsx:312]

## Deferred from: code review of 2-6-voice-profile-refresh (2026-07-01)

- **D1 (Low)**: No recovery path from stuck in-progress state when `client.brand_voice_profile` is null after `router.refresh()` resolves — possible if read replica lags or model serialization error. Needs timeout/fallback transition to `"failed"` state.
- **D2 (Medium)**: No rate-limiting or quota guard on `POST /clients/{id}/ingest` — authenticated owner can spam the endpoint creating unbounded job records. Architectural concern; address at infra or middleware layer.

## Deferred from: code review of 6-1-campaign-list-dashboard-with-status-filtering (2026-07-04)

- **D1 (Low)**: `sys.modules` patching at module level in `backend/tests/routers/test_campaigns.py` pollutes the test session — stubs run at import time and persist across all tests. Refactor to use `@pytest.fixture` or `unittest.mock.patch` at function scope in a future test cleanup pass.
