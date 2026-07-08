# Deferred Work

## Deferred from: code review of 8-2-landing-page-conversion-keyword-optimization (2026-07-07)

- **D1 (Low)**: DOMPurify config mutability — `_DOMPURIFY_CONFIG` changed from `as const` to typed `Config`; removes readonly guarantee. DOMPurify does not mutate configs in practice but future spread/assign could silently drop `FORBID_ATTR`. [frontend/components/campaigns/BlogEditor.tsx:21]
- **D2 (Low)**: `window.prompt` in BlogEditor inside sandboxed iframe — link toolbar button uses `window.prompt` which is blocked/silent in sandboxed iframes; breaks link insertion UX in embed contexts. Pre-existing, outside this story's scope. [frontend/components/campaigns/BlogEditor.tsx:121]

## Deferred from: code review of 7-3-data-retention-account-deletion-cleanup-scheduler (2026-07-06)

- **D1 (Medium)**: Multiple `trial_expired` subscription rows for same `user_id` causes Phase 2 to re-anonymize the already-hashed email, corrupting the audit trail. No `UNIQUE` constraint on `subscriptions.user_id`. Pre-existing schema design gap; low probability in practice. [backend/app/workers/cleanup.py]
- **D2 (Medium)**: Stripe customer object not deleted from Stripe on account anonymization — only the local `stripe_customer_id` field is cleared. GDPR Art. 17 gap. Out of scope for this story; requires Stripe API call + error handling in `_anonymize_user`. [backend/app/workers/cleanup.py:_anonymize_user]
- **D3 (Low)**: Truncated 64-bit SHA-256 prefix for email anonymization is brute-forceable over structured email namespaces (no salt). Design decision; acceptable given the low-value target. If GDPR compliance is hardened, replace with salted full hash or random UUID. [backend/app/workers/cleanup.py:_anonymize_user]

## Deferred from: code review of 7-2-trial-expiry-restricted-state-upgrade-banner (2026-07-06)

- **D1 (Low)**: `.replace(tzinfo=timezone.utc)` used to make `billing_cycle_end` tz-aware in `check_and_expire_trial`, but Stripe webhook handler stores tz-aware datetimes; inconsistency is harmless now (Postgres strips tzinfo on write for naive columns) but creates a fragile convention. [backend/app/services/subscription_service.py:35]
- **D2 (Low)**: TrialBanner flash-of-absent-content — on first load of a newly-expired user, `useSubscriptionStatus` returns `null` until AppShell's async `/status` call completes and invalidates the query cache; banner appears ~100–300ms late. Architectural RSC limitation; server components cannot do data fetching per project rule.
- **D3 (Low)**: Long-lived sessions never re-expire mid-session — AppShell's `useEffect` that calls `/status` runs once on mount; a user whose trial expires while they have the tab open will not see the banner until they navigate away or refresh. Spec intent was on-login check, not real-time enforcement.
- **D4 (Low)**: `useSubscription` stale up to 60s after Stripe portal return — `staleTime: 60_000` in the subscription query means the banner may not disappear immediately after a user subscribes and returns from the portal. Pre-existing from 7.1 hook design.
- **D5 (Low)**: Trial expiry not enforced at session-validation/auth-middleware layer — AC1 spec intent ("When login/session validated") is partially met; actual DB write only occurs when frontend hits `GET /subscriptions/status`. Intentional trade-off given the RSC/no-server-data-fetch architectural rule.

## Deferred from: code review of 7-1-trial-expiry-nudge-notifications (2026-07-06)

- **D1 (Medium)**: Direct key access (`sub_obj["current_period_start"]`, `sub_obj["current_period_end"]`) in `_handle_subscription_updated` — raises `KeyError` on partial Stripe payloads (paused subscriptions, free trials with no billing period). Pre-existing; all other fields use `.get()`. [backend/app/services/subscription_service.py:263-264]
- **D2 (Medium)**: `customer.subscription.created` handler delegates to `_handle_subscription_updated` which looks up by `stripe_sub_id` — if the DB row was not yet populated with `stripe_sub_id` (race with `checkout.session.completed`), lookup returns None and billing dates are not updated. Architectural Stripe webhook ordering concern; pre-existing. [backend/app/services/subscription_service.py]
- **D3 (Low)**: `billing_cycle_end` timezone parsing — if backend ever returns naive datetime string (without UTC offset), browser parses as local time. Backend currently uses `tz=timezone.utc` so FastAPI serializes with offset; defensive `+"Z"` append not added. Pre-existing risk. [frontend/hooks/useSubscription.ts:20]

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

## Deferred from: code review of 4-2-blog-post-wysiwyg-editing (2026-07-05)

- **D1 (Medium)**: Race condition — PATCH status check is non-atomic; a concurrent approve/reject could slip past the `pending_approval` guard before either commits. Needs `SELECT ... FOR UPDATE` or optimistic lock. [backend/app/routers/campaigns.py:patch_campaign]
- **D2 (Low)**: `onSave` prop declared in BlogEditorProps but never invoked after successful save — Story 4.4 must wire this up when orchestrating the approve flow. [frontend/components/campaigns/BlogEditor.tsx]
- **D3 (Low)**: `getCurrentHtml` forwardRef not passed from page.tsx — by design; Story 4.4 will add the ref when wiring the approve button. [frontend/app/(app)/campaigns/[id]/page.tsx]
- **D4 (High)**: Save in-flight + Approve race → false error toast — if user saves then immediately approves, the PATCH resolves against an already-approved campaign and shows a false error. BlogEditor's `isSaving` state not surfaced to ApprovalPanel. Fix in Story 4.4 approve flow. [frontend/components/campaigns/ApprovalGateClient.tsx]
- **D5 (High)**: handleApprove always patches blog_html even when user made no edits — bypasses dirty guard, re-sanitizes AI content through nh3 on every approval. Story 4.4 to add `isDirty` check via ref handle. [approval-panel.tsx]
- **D6 (Medium)**: Optimistic approval shows stale blog content in BlogHtmlRenderer until router.refresh() resolves — user sees pre-edit content for the duration of the RSC refresh. Story 4.4 to track last-saved HTML in local state. [frontend/components/campaigns/ApprovalGateClient.tsx]
- **D7 (Medium)**: `readOnly` prop change not propagated to Tiptap (`editor.setEditable` not called) — masked by current unmount/remount pattern but would break if BlogEditor is kept mounted while readOnly changes. Add `useEffect(() => { editor?.setEditable(!readOnly); }, [editor, readOnly])` as defensive fix. [frontend/components/campaigns/BlogEditor.tsx]

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

## Deferred from: epic-level code review of Epic 3 (2026-07-04)

- **D01 (Low)**: `completeOnboarding`-before-`create` trade-off — if campaign creation fails after onboarding is flagged complete, the flag stays set. Spec Dev Notes explicitly accept this as a UX trade-off (nudge card handles it). [frontend/components/onboarding/OnboardingFlow.tsx]
- **D02 (Low)**: Retry creates a new campaign per AC 3.2-6 — orphaned failed campaigns accumulate with no cleanup. Design gap in the spec; no clean-up endpoint exists. [frontend/components/campaigns/CampaignGenerationOverlay.tsx]
- **D03 (Low)**: `update_campaign_content` repo function defined but never called by the generation service (duplicate of existing D1 from story 3.3 review). [backend/app/db/repositories/campaigns.py]
- **D04 (Low)**: `ImagePanel` hardcodes regen limit as `3` — valid coupling concern; requires API to expose the limit in campaign/subscription response. [frontend/components/campaigns/ImagePanel.tsx]
- **D05 (Low)**: `"complete"`/`"completed"` dual terminal-status strings in both `TERMINAL_STATUSES` and `CAMPAIGN_TERMINAL_STATUSES` — defensive coverage; naming already consolidated per prior review. [frontend/hooks/useJobStatus.ts]
- **D06 (Medium)**: Jobs permanently stuck `in_progress` after server restart — no startup sweep or cron to detect and fail orphaned jobs. Pre-existing architectural gap. [backend/app/workers/generate.py]
- **D07 (Low)**: `handleRetry` doesn't reset `isRetrying` to `false` on success — component unmounts during navigation so no observable bug under normal conditions. [frontend/components/campaigns/CampaignGenerationOverlay.tsx]

## Deferred from: code review of 6-1-campaign-list-dashboard-with-status-filtering (2026-07-04)

- **D1 (Low)**: `sys.modules` patching at module level in `backend/tests/routers/test_campaigns.py` pollutes the test session — stubs run at import time and persist across all tests. Refactor to use `@pytest.fixture` or `unittest.mock.patch` at function scope in a future test cleanup pass.

