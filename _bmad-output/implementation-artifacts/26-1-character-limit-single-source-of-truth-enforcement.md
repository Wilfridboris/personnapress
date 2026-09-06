# Story 26.1: Character Limit Single Source of Truth and Enforcement

Status: done
baseline_commit: a492c76b305cd825645204cb1a4c83483288b795

## Story

As a user approving social posts,
I want every platform's character limit defined once and enforced at generation, approval, and publish time,
so that a post never exceeds a platform limit, never gets blindly truncated mid-sentence, and never fails at the platform API for a reason I could not see.

## Acceptance Criteria

1. **Given** a new shared limits module `backend/app/services/platform_limits.py` and a frontend mirror `frontend/lib/platformLimits.ts`, **When** any code needs a platform character limit, **Then** it reads from these modules only. Canonical hard limits: X 280 (weighted), LinkedIn 3000, Instagram 2200, Facebook 63206, Threads 500. Canonical target ranges used by prompts stay stricter than hard limits (X 70-280, LinkedIn 300-1300 linked / 1200-2500 standalone, Instagram 150-600, Facebook 200-800, Threads max 500). The frontend counter maxima in `SocialPostEditors.tsx` (currently 280/1500/2200/1000/500) are replaced by the canonical hard limits.

2. **Given** X counts URLs as 23 characters regardless of actual length, **When** the frontend counts an X post and when the backend validates one, **Then** both use a shared weighted-count implementation (URLs matched with the same regex count as 23; all other characters count via code points), and the X counter in the editor reflects the weighted count.

3. **Given** an LLM social generation response exceeds a hard limit for its platform, **When** the provider (`gemini.py`, `anthropic_client.py`) parses the response, **Then** instead of blind truncation with an ellipsis, it makes ONE repair call asking the model to shorten that specific post below the limit while preserving the hook and voice; only if the repair still exceeds the limit does it truncate at the last sentence boundary below the limit (never mid-word) and log a warning.

4. **Given** a user is on the approval panel with any post over its hard limit for a platform they can publish to, **When** they attempt to Approve, **Then** the action is blocked with an inline message naming the platform(s) and the overage (e.g. "X post is 12 characters over the limit"), and the corresponding counter shows the danger state.

5. **Given** `dispatch_publish` and `dispatch_publish_for_platform` in `backend/app/services/publishing.py`, **When** a post exceeds its platform hard limit at publish time, **Then** the platform is marked failed with a distinct machine-readable reason (`error_details="over_limit"`) BEFORE any API call, the naive `[:280]` slices in `twitter.py` and `[:2200]` in `meta.py` are removed, and the frontend retry panel surfaces "post is over the X character limit, shorten it and retry" instead of a generic error.

6. **Given** backend tests, **When** run, **Then** they cover: weighted X counting with URLs, repair-call path when generation is over limit, sentence-boundary fallback truncation, publish-time over-limit rejection per platform, and parity between frontend and backend limit constants (a test reads both files or a shared JSON fixture).

## Tasks / Subtasks

- [x] Task 1: Create the canonical limits modules (AC: 1)
  - [x] `backend/app/services/platform_limits.py`: `HARD_LIMITS: dict[str, int]` = {"x": 280, "linkedin": 3000, "instagram": 2200, "facebook_page": 63206, "threads": 500}, plus `TARGET_RANGES` used only for prompt text, plus `count_chars(platform, text) -> int` and `over_limit(platform, text) -> int` (returns overage, 0 if within).
  - [x] `frontend/lib/platformLimits.ts`: same values and a `countChars(platform, text)` with identical URL weighting logic. Keep field-name mapping consistent with campaign fields (x_post, linkedin_post, instagram_caption, facebook_post, threads_post).
  - [x] Replace the constants at `frontend/components/campaigns/SocialPostEditors.tsx:9-13` with imports; recompute danger thresholds as 95% of the imported limits.
- [x] Task 2: Weighted X counting (AC: 2)
  - [x] Backend: URL regex `https?://[^\s]+` (same pattern the onboarding link detector uses) replaced by a 23-char token before `len()` on code points.
  - [x] Frontend: identical regex and substitution; wire into the X counter (`xCount`) in SocialPostEditors so the editor displays the weighted count.
  - [x] Do NOT attempt full twitter-text weighting (emoji weighting, ranges); URL weighting only, per AC. Note this boundary in code comment.
- [x] Task 3: Provider repair-then-fallback (AC: 3)
  - [x] In `gemini.py` (lines ~554-603) and `anthropic_client.py` (lines ~379-428): replace each blind `[:N] + "…"` truncation with: detect overage via `platform_limits.over_limit`, issue one short repair call ("Shorten this {platform} post to under {limit} characters. Preserve the opening hook, the core point, and the writer's voice. Return only the post text."), re-check, then sentence-boundary truncate as last resort (split on `.`, `!`, `?`, newline; take longest prefix under limit; never cut mid-word; no ellipsis appended).
  - [x] Both `generate_social` and `generate_social_standalone` in BOTH providers (4 sites). Keep the existing warning logs, add `repair_applied` log line.
  - [x] LinkedIn: hard limit for repair purposes is 3000, not the 1300/2500 prompt targets; targets remain prompt-only guidance.
- [x] Task 4: Approval blocking (AC: 4)
  - [x] `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` (~line 538-549): before approve mutation fires, compute overages via `platformLimits` for each platform with content the user can publish; if any overage > 0, block and render inline error listing each offending platform and overage count; do not disable silently, show the reason.
  - [x] Danger state already exists at 95% thresholds; keep it, add a hard over-limit state (counter turns error color at > 100%).
- [x] Task 5: Publish-time validation (AC: 5)
  - [x] `backend/app/services/publishing.py` `dispatch_publish` (line ~750) and `dispatch_publish_for_platform` (line ~601): before each platform call, check `over_limit`; on failure set result "failed" with `error_details="over_limit"` and skip the API call.
  - [x] Remove `(text or "")[:280]` at `twitter.py:66` and `twitter.py:135`; remove `caption_truncated = (caption or "")[:2200]` at `meta.py:133` (validation now happens upstream; pass text through unchanged).
  - [x] Frontend RetryPanel: map `error_details="over_limit"` to specific copy per platform ("Your X post is over the 280 character limit. Shorten it and retry."). Follow the existing error-reason mapping pattern used for other publish failures.
- [x] Task 6: Tests (AC: 6)
  - [x] `backend/tests/test_platform_limits.py`: weighted counting (URL of any length counts 23, multiple URLs, no URL), over_limit boundaries per platform.
  - [x] Provider tests (both `test_gemini*.py` and the anthropic test file, mirroring the 3-14/3-26 parity pattern): over-limit response triggers exactly one repair call; repaired output used when within limit; sentence-boundary fallback when repair still over; no ellipsis in output.
  - [x] Publishing tests: over-limit x_post/linkedin_post/threads_post marked failed with `error_details="over_limit"` and platform API mock NOT called.
  - [x] Parity test: canonical limits in `platform_limits.py` match `frontend/lib/platformLimits.ts` (regex-parse the TS file for the constant values, or emit a shared JSON fixture both import).
  - [x] Frontend tests for SocialPostEditors weighted X count and approval blocking (follow existing vitest patterns in the component's test file).

## Dev Notes

### Why this story exists (evidence, 2026-09-05 code analysis)

- Limits are defined in four places with four different values: frontend counters (280/1500/2200/1000/500 at `SocialPostEditors.tsx:9-13`), prompt target ranges (`generation_prompts.py:363-367` and `392-396`), provider truncation caps (gemini ~554-603, anthropic ~379-428: X 280, LinkedIn 1300 linked / 2500 standalone, IG 600, FB 800, Threads 500), and publish-path slices (`twitter.py:66,135` `[:280]`, `meta.py:133` `[:2200]`).
- LinkedIn is the worst offender: frontend says 1500, blog-linked prompt says 1300, standalone prompt says 2500, real platform limit is 3000. A standalone LinkedIn post of 2400 chars shows as over-limit in the editor (1500) despite being valid.
- Nothing blocks approval: counters show a 95% danger color but the Approve button stays clickable at any length (`approval-panel.tsx:~538-549`).
- No length validation exists anywhere in `dispatch_publish` (`publishing.py:750-828`); over-limit posts reach platform APIs and fail generically, or get silently mangled by the naive slices.
- X counting uses raw `.length` / `len()`; URLs actually count as 23 chars on X, so URL-bearing posts can be wrongly valid or wrongly invalid.
- Provider truncation appends "…" mid-sentence, which is exactly the "written by AI" tell this epic is eliminating.

### Constraints and guardrails

- Provider parity is mandatory: every prompt/parse change must land identically in `gemini.py` and `anthropic_client.py`, with tests in both test files (established pattern from stories 3-14, 3-26; reviews repeatedly patched missing parity).
- No em-dashes and no double-dashes in ANY user-facing copy or prompt text (firm project rule; reviews have patched violations repeatedly). The repair-call prompt must also comply.
- No emojis in UI copy; icons only from the installed Lucide React set.
- Error copy must name the issue specifically, never "Something went wrong".
- Alembic: no migration is needed for this story (no schema change). Do not add one.
- The repair call must be bounded: exactly one attempt, then deterministic fallback. No recursion, no loops.
- `facebook_page` limit 63206 is effectively unreachable; include it for completeness but the prompt targets (200-800) remain the real behavior shaper.
- Keep prompt target ranges unchanged in `generation_prompts.py`; this story does not rewrite prompt guidance, only enforcement. (Story 26.4 touches prompt voice sections; avoid collisions.)
- `dispatch_publish_for_platform` handles the image-path publish for LinkedIn org targets; make sure the over-limit check covers both dispatch functions and both LinkedIn targets (personal + org, story 5-7/5-8 feature flag `LINKEDIN_ORG_POSTING_ENABLED`).

### Existing behavior that must not break

- Approve currently works for campaigns with empty social fields (platform skipped at publish). The over-limit block must only consider non-empty posts.
- `run_publish_retry` re-dispatches failed platforms; `error_details="over_limit"` must flow through retry the same way other failure reasons do (see 21-12 skipped-platform handling and `11-7` republish error clarity for the established error surfacing pattern).
- The 95% danger threshold UX from story 4-3/11-8 stays; this story adds a hard >100% state on top.
- Instagram publish path also enforces image presence; do not disturb that gating.

### Source tree components to touch

- `backend/app/services/platform_limits.py` (NEW)
- `backend/app/services/publishing.py` (UPDATE: dispatch_publish ~750, dispatch_publish_for_platform ~601)
- `backend/app/integrations/twitter.py` (UPDATE: remove slices at 66, 135)
- `backend/app/integrations/meta.py` (UPDATE: remove slice at 133)
- `backend/app/integrations/gemini.py` (UPDATE: generate_social ~554-603, generate_social_standalone truncation blocks)
- `backend/app/integrations/anthropic_client.py` (UPDATE: ~379-428 and standalone equivalent)
- `frontend/lib/platformLimits.ts` (NEW)
- `frontend/components/campaigns/SocialPostEditors.tsx` (UPDATE: constants 9-13, counters, danger states)
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` (UPDATE: approve gating, retry panel copy)
- `backend/tests/test_platform_limits.py` (NEW), provider test files (UPDATE), publishing test file (UPDATE)

### Testing standards summary

- Backend: pytest, async tests with mocked httpx/provider clients; follow the existing patterns in `backend/tests/test_meta_integration.py` and the gemini/anthropic test pairs. Assert API mocks NOT called on over-limit rejection.
- Frontend: vitest + testing-library patterns already used for SocialPostEditors and approval-panel.
- Run backend tests from `backend/` (Windows dev machine, no tmux; plain `pytest`).

### Project Structure Notes

- Integrations live in `backend/app/integrations/`, cross-cutting services in `backend/app/services/`; the limits module is a service (no external API), matching `stylometry.py` placement.
- Frontend shared logic lives in `frontend/lib/` (see existing `frontend/lib/` API helpers); components import from `@/lib/...`.
- Use the `/web-uiux-architect` skill conventions for any visual changes (Paper Style, rounded-none, ink color tokens) when adjusting counter/danger states.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 26, Story 26.1]
- [Source: frontend/components/campaigns/SocialPostEditors.tsx:9-17 (current constants)]
- [Source: backend/app/integrations/generation_prompts.py:363-367, 392-396, 428-435 (prompt target ranges)]
- [Source: backend/app/integrations/gemini.py:554-603; backend/app/integrations/anthropic_client.py:379-428 (blind truncation)]
- [Source: backend/app/services/publishing.py:601, 750 (dispatch functions, no length checks)]
- [Source: backend/app/integrations/twitter.py:66,135; backend/app/integrations/meta.py:133 (naive slices)]
- [Source: _bmad-output/project-context.md (no em-dash rule, Alembic CLI rule, RSC data-fetching rule)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — all issues resolved inline during the review/patch cycle.

### Completion Notes List

- Provider parity maintained: `_repair_post` helper duplicated in both `gemini.py` and `anthropic_client.py` per established project pattern.
- LinkedIn hard limit for repair is 3000 (not prompt targets 1300/2500); prompt targets unchanged in `generation_prompts.py`.
- `sentence_boundary_truncate` accepts optional `platform` arg for weighted-count re-check on X (P4 patch).
- `dispatch_publish` `job_id` param added to test call after function signature check.
- `test_create_tweet_with_media_truncates_text` renamed and updated to assert pass-through (truncation intentionally removed per AC 5).
- 3 deferred items appended to `deferred-work.md`.

### File List

- `backend/app/services/platform_limits.py` (NEW)
- `backend/app/integrations/gemini.py` (UPDATED)
- `backend/app/integrations/anthropic_client.py` (UPDATED)
- `backend/app/integrations/twitter.py` (UPDATED)
- `backend/app/integrations/meta.py` (UPDATED)
- `backend/app/services/publishing.py` (UPDATED)
- `frontend/lib/platformLimits.ts` (NEW)
- `frontend/components/campaigns/SocialPostEditors.tsx` (UPDATED)
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` (UPDATED)
- `frontend/components/publishing/RetryPanel.tsx` (UPDATED)
- `backend/tests/test_platform_limits.py` (NEW)
- `backend/tests/test_platform_limits_provider.py` (NEW)
- `backend/tests/test_gemini_generation.py` (UPDATED)
- `backend/tests/test_meta_integration.py` (UPDATED)
- `backend/tests/integrations/test_twitter.py` (UPDATED)
- `frontend/__tests__/components/campaigns/SocialPostEditors.test.tsx` (UPDATED)
- `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx` (UPDATED)
- `frontend/__tests__/components/publishing/RetryPanel.test.tsx` (UPDATED)
