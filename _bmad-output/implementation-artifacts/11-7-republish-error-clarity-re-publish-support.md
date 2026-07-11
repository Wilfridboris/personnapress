---
baseline_commit: 32d2c1e
---

# Story 11.7: Republish Error Clarity & Re-Publish Support

Status: done

## Story

As an authenticated PersonnaPress user,
I want clear feedback when I try to publish a campaign that is already published,
and I want the option to re-publish to platforms I've connected since the original publish,
so that I understand what's happening and can get content to new platforms without confusion.

## Acceptance Criteria

1. **Given** the frontend `apiFetch` utility receives a non-2xx response with body `{"detail": {"error": {"code": "...", "message": "..."}}}` (FastAPI HTTPException format), **When** parsing the error, **Then** `APIError.message` is set to the value from `detail.error.message` and `APIError.code` is set from `detail.error.code` — so all backend error messages surface correctly in the UI instead of falling through to "Something went wrong."

2. **Given** the campaign is in `published` status and the user opens "Publish to more platforms", **When** they click "Publish now", **Then** the backend accepts the request (campaign in `published` status is treated as eligible for re-publishing) and dispatches the publish job to all currently connected platforms.

3. **Given** a re-publish job completes after AC 2, **When** all platforms succeed, **Then** the campaign status remains `published` and the job completes; the approval panel refreshes to show the updated "Published to [platforms]" summary reflecting the latest job results.

4. **Given** the backend `publish_campaign_now` endpoint, **When** evaluating whether to allow publishing, **Then** the guard becomes `campaign.status not in ("approved", "published")` — both `approved` and `published` are valid pre-publish states. All other statuses (`pending_approval`, `rejected`, `failed`) still return 400 with `INVALID_STATUS_TRANSITION`.

5. **Given** any error is thrown during `handlePublishNow` in the approval panel (including `INVALID_STATUS_TRANSITION` for any remaining edge cases), **When** the error is an `APIError`, **Then** `err.message` is the actual text from the backend (enabled by AC 1 fix), not "Something went wrong." The existing `err.code === "TRIAL_EXPIRED"` check continues to work correctly.

6. **Given** all existing error-handling code throughout the app (`TRIAL_EXPIRED`, `NO_PLATFORM_CONNECTIONS`, `GITHUB_TOKEN_EXCHANGE_FAILED`, etc.), **When** the `apiFetch` fix in AC 1 is deployed, **Then** all existing toast messages and code checks (`err.code === "TRIAL_EXPIRED"`, etc.) work correctly — the fix is additive and does not break any existing error path.

## Tasks / Subtasks

### Task 1: Fix `apiFetch` error parsing (AC: 1, 5, 6)

- [x] 1.1 In `frontend/lib/api.ts`, update the error-extraction block in `fetchAPI`:

  **Current (broken):**
  ```typescript
  if (!res.ok) {
    const errShape = data?.error as { message?: string; code?: string } | undefined;
    const message =
      errShape?.message ??
      (typeof data?.detail === "string" ? data.detail : undefined) ??
      "Something went wrong.";
    const code = errShape?.code ?? "UNKNOWN_ERROR";
    throw new APIError(message, code);
  }
  ```

  **Fixed:**
  ```typescript
  if (!res.ok) {
    // FastAPI HTTPException wraps detail as: {"detail": {"error": {"code": "...", "message": "..."}}}
    // Custom handlers (rate limiter) send: {"error": {"code": "...", "message": "..."}}
    // Support both shapes.
    const detail = data?.detail as Record<string, unknown> | string | undefined;
    const nestedError =
      typeof detail === "object" && detail !== null
        ? (detail as Record<string, unknown>).error
        : undefined;
    const errShape = (nestedError ?? data?.error) as
      | { message?: string; code?: string }
      | undefined;
    const message =
      errShape?.message ??
      (typeof detail === "string" ? detail : undefined) ??
      "Something went wrong.";
    const code = errShape?.code ?? "UNKNOWN_ERROR";
    throw new APIError(message, code);
  }
  ```

- [x] 1.2 Verify that after this fix, `err.code === "TRIAL_EXPIRED"` in `handlePublishNow` (and any other `err.code` checks in the codebase) still resolve correctly. The structure `{"detail": {"error": {"code": "TRIAL_EXPIRED", ...}}}` now correctly sets `code = "TRIAL_EXPIRED"`.

### Task 2: Backend — allow re-publishing from `published` status (AC: 2, 3, 4)

- [x] 2.1 In `backend/app/routers/publishing.py`, find the status guard in `publish_campaign_now` (around line 845):

  **Current:**
  ```python
  if campaign.status != "approved":
      raise HTTPException(
          status_code=400,
          detail={
              "error": {
                  "code": "INVALID_STATUS_TRANSITION",
                  "message": "Only approved campaigns can be published.",
                  "detail": {},
              }
          },
      )
  ```

  **Updated:**
  ```python
  if campaign.status not in ("approved", "published"):
      raise HTTPException(
          status_code=400,
          detail={
              "error": {
                  "code": "INVALID_STATUS_TRANSITION",
                  "message": "Only approved or published campaigns can be re-published.",
                  "detail": {},
              }
          },
      )
  ```

- [x] 2.2 In `backend/app/workers/publish.py`, verify the `run_publish` worker: after a successful re-publish, it sets `campaign.status = "published"`. This is already the behaviour — confirm it remains `"published"` and is not reset to `"approved"` anywhere.

### Task 3: Tests (AC: 1, 2, 4, 6)

- [x] 3.1 In `backend/tests/routers/test_publishing.py`, add a test that verifies `POST /api/v1/campaigns/{id}/publish` returns 202 when `campaign.status == "published"` (not just `approved`).

- [x] 3.2 Add a test that verifies `pending_approval`, `rejected`, and `failed` status campaigns still return 400 with `INVALID_STATUS_TRANSITION`.

- [x] 3.3 (Optional) Write a JS unit test for the updated `fetchAPI` error extraction if the project has a frontend test suite. If not, manually verify by triggering a 400 error in dev mode and confirming the toast shows the backend message text.

## Dev Notes

### Root cause of "Something went wrong"

FastAPI's `HTTPException` serializes to `{"detail": {...}}` wrapping whatever you pass as `detail`. The existing `apiFetch` code was checking `data?.error` (top-level), but the actual shape is `data.detail.error`. Only the custom rate-limit handler used `{"error": {...}}` at the top level, which is why that one worked.

This means **every** backend error that used `HTTPException` with the standard error envelope was silently showing "Something went wrong." — including `TRIAL_EXPIRED`. The fix in Task 1 makes the parser check `data.detail.error` first, then `data.error` as a fallback (for the rate-limit handler and any future custom responses).

### Why republish to all platforms is acceptable

The publish worker (`run_publish`) publishes to ALL connected platforms. If a platform already has the post (e.g. LinkedIn), it may create a duplicate. This is accepted behaviour for MVP — the user is explicitly choosing to re-publish. Social platforms (LinkedIn, X) do allow posting the same content multiple times. WordPress upserts by slug, so re-publishing to WordPress overwrites the existing post cleanly. Document this in UX if needed.

### Key files

| File | Change type | Purpose |
|------|-------------|---------|
| `frontend/lib/api.ts` | UPDATE | Fix `fetchAPI` error extraction for FastAPI HTTPException format |
| `backend/app/routers/publishing.py` | UPDATE | Allow `published` status in `publish_campaign_now` |
| `backend/tests/routers/test_publishing.py` | UPDATE | Tests for republish from `published` status |

### Architecture constraints

- Server components should only do session/auth checks. All data fetching in client components via TanStack Query (see `project-context.md`).
- No emojis anywhere.
- The `apiFetch` fix must be backward-compatible: never remove the `data?.error` fallback path, only add the `data.detail.error` path as the primary check.

### Baseline story context

This story depends on Story 11.6 only for the `apiFetch` fix side-effect (once error messages surface properly, the "Connections" nav makes it easier to add a platform before republishing). It can be implemented independently of 11.6.

### Frontend approval panel context (no changes needed)

The existing "Publish to more platforms" flow in `approval-panel.tsx` already calls `handlePublishNow` (line 878) and `handlePublishNow` already has:
```typescript
addToast(err instanceof APIError ? err.message : "Publish failed.", "error");
```
Once Task 1 fixes `apiFetch`, the `err.message` will be the actual backend text. No changes needed in `approval-panel.tsx` for the error display path.

## Dev Agent Record

### Implementation Plan

- Task 1: Fixed `fetchAPI` error extraction in `frontend/lib/api.ts` to check `data.detail.error` first (FastAPI HTTPException format), then fall back to `data.error` (custom rate-limiter format). Change is additive; all existing `err.code` checks remain correct.
- Task 2: Updated status guard in `publish_campaign_now` from `!= "approved"` to `not in ("approved", "published")`. Worker already sets `"published"` on success in both re-publish and first-publish paths — no worker change needed.
- Task 3: Added 5 new parameterized tests covering: re-publish from `published` (202), normal publish from `approved` (202), and 400 INVALID_STATUS_TRANSITION for `pending_approval`, `rejected`, `failed`.

### Completion Notes

All 3 tasks implemented and tested. 15/15 tests pass in `tests/routers/test_publishing.py` (5 new). Pre-existing failures in other test files confirmed as unrelated. Frontend fix is backward-compatible: `TRIAL_EXPIRED`, `NO_PLATFORM_CONNECTIONS`, and all other `err.code` checks continue to work correctly because the fix just adds the `data.detail.error` path as primary lookup.

## File List

- `frontend/lib/api.ts` — updated `fetchAPI` error extraction (Task 1.1)
- `backend/app/routers/publishing.py` — updated `publish_campaign_now` status guard (Task 2.1)
- `backend/tests/routers/test_publishing.py` — added 5 new tests (Task 3.1, 3.2)

### Review Findings

- [x] [Review][Patch] Hugo author omitted from `buildFrontMatterPreview` preview [`frontend/app/(app)/campaigns/[id]/approval-panel.tsx`:94]
- [x] [Review][Patch] `publishedPlatforms` stale after re-publish completes [`frontend/app/(app)/campaigns/[id]/approval-panel.tsx`:212]
- [x] [Review][Defer] FastAPI 422 array-shaped `detail` falls through to "Something went wrong" [`frontend/lib/api.ts`:35] — deferred, pre-existing (422 was never handled before this change either)
- [x] [Review][Defer] `connectGithubDirect` sends `installationId` without emptiness guard [`frontend/lib/api.ts`:214] — deferred, new API method has no active call site in this diff

## Change Log

- 2026-07-11: Implemented story 11.7 — fixed `apiFetch` error parsing for FastAPI HTTPException format, allowed re-publishing from `published` status, added backend tests.
- 2026-07-11: Code review — fixed 2 findings (Hugo author preview, stale publishedPlatforms after re-publish).
