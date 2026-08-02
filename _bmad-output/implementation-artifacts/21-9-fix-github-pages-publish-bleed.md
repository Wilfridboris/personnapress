---
baseline_commit: fbb4f3e
---

# Story 21.9: Fix GitHub Pages Publish Bleed into Generic Publish Path

Status: done

---

## Story

As a PersonnaPress user with GitHub Pages connected (but using "Publish now" for social/blog platforms),
I want the generic publish job to never attempt GitHub Pages publishing,
so that my "Publish now" action succeeds without a spurious GitHub Pages failure crashing the whole job.

---

## Context & Motivation

### Root Cause

GitHub Pages has two completely separate publish paths in the codebase:

1. **Dedicated path** — "Publish to GitHub" button → `publish_github_job()` in `workers/publish.py`
   (handles mode, author, categories, framework detection)
2. **Generic path** — "Publish now" button → `dispatch_publish()` in `services/publishing.py`
   (handles all other platforms: social, WordPress, Webflow, etc.)

The bug: `dispatch_publish` contains a `github_pages` branch and will attempt GitHub publishing
when the `platforms` filter is empty (i.e., "publish to all connections in DB").

### How It Triggers

The frontend hides GitHub Pages from the platform chip list entirely (line 291,
`c.platform !== "github_pages"`), so the user never sees or selects it. When the user
clicks "Publish now" with all visible platforms selected, the frontend sends `platforms=undefined`
(the "publish to all" shortcut at line 455). The backend normalises `None` to `[]`, the
`if platforms:` guard at line 658 is falsy, so it skips the filter entirely and publishes to
every connection in the DB — including the GitHub Pages one.

If that GitHub Pages connection has no `repo_full_name` set, the publisher raises
`PlatformError("github", 0, "No repository selected")` and the entire job is marked failed.

### Why Two Changes Are Needed

**Backend fix (primary guard):** Add an `else` branch to the existing `if platforms:` block in
`dispatch_publish`. When no platforms are requested (i.e., "publish all"), always exclude
`github_pages`. The dedicated `publish_github_job` worker handles GitHub Pages; it never calls
`dispatch_publish`, so there is no risk of the exclusion interfering with intentional GitHub
publishing.

**Frontend fix (contract cleanup):** Remove the "send nothing if all are selected" optimisation.
Always send the explicit `connectedSelected` list. This closes the frontend/backend contract gap
and removes dead code (`connectedPlatformCount`). Even if the backend fix were the only change,
the frontend optimisation is a footgun that makes future platform additions risky.

---

## Acceptance Criteria

### AC 1: `dispatch_publish` excludes `github_pages` in "publish all" path

**Given** a client has a `github_pages` connection in the DB,
**When** `dispatch_publish` is called with `platforms=None` (or `platforms=[]`),
**Then** the `github_pages` connection is excluded from the `connections` list before any
dispatching begins, so no `github_pages` publish attempt is made.

Exact location: `backend/app/services/publishing.py`, inside `dispatch_publish`, after the
`if platforms is None: platforms = []` block (line 656), change the `if platforms:` block:

```python
# BEFORE (line 658-659):
if platforms:
    connections = [c for c in connections if (c.platform if isinstance(c.platform, str) else c.platform.value) in platforms]

# AFTER:
if platforms:
    connections = [c for c in connections if (c.platform if isinstance(c.platform, str) else c.platform.value) in platforms]
else:
    # github_pages has its own dedicated publish_github_job worker; never auto-include here
    connections = [c for c in connections if (c.platform if isinstance(c.platform, str) else c.platform.value) != "github_pages"]
```

### AC 2: `dispatch_publish` still targets `github_pages` when explicitly requested

**Given** a caller passes `platforms=["github_pages"]` explicitly,
**When** `dispatch_publish` runs,
**Then** `github_pages` connections are NOT excluded (the `if platforms:` branch runs, not the `else`).

This preserves backward compatibility for any future explicit use.

### AC 3: Frontend always sends explicit platforms list

**Given** the user has one or more connected platforms visible in the chip list (github_pages never included),
**When** the user clicks "Publish now" with all chips selected,
**Then** `campaignsApi.publishNow` is called with the explicit `connectedSelected` array,
never with `undefined`.

Exact change in `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`, `handlePublishNow`:

```tsx
// BEFORE (lines 448, 455-458):
const connectedPlatformCount = availablePlatforms.filter((p) => p !== "headless").length;
// ...
const filterPlatforms = connectedSelected.length < connectedPlatformCount ? connectedSelected : undefined;
const { job_id } = await campaignsApi.publishNow(
  campaign.id,
  ...(filterPlatforms !== undefined ? [filterPlatforms] : []),
);

// AFTER:
// connectedPlatformCount line removed entirely
// ...
const { job_id } = await campaignsApi.publishNow(campaign.id, connectedSelected);
```

`connectedPlatformCount` becomes unused — remove it.

### AC 4: New backend test — github_pages excluded from "publish all"

**Given** a campaign whose client has a `github_pages` connection (with no `repo_full_name`) and a
`facebook_page` connection,
**When** `dispatch_publish` is called with `platforms=None`,
**Then** no publish attempt is made for `github_pages`, and the job does not fail due to the
missing repo.

Add this test to `backend/tests/test_meta_integration.py` (or a dedicated publishing test file if
one exists). Use the existing mocking patterns from that file (`AsyncMock`, `patch`, connection
fixture helpers).

---

## Dev Notes

### Files to Change

| File | Change |
|------|--------|
| `backend/app/services/publishing.py` | Add `else` branch after `if platforms:` at line 658 |
| `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` | Remove `connectedPlatformCount`, simplify `publishNow` call at lines 448, 455-458 |
| `backend/tests/test_meta_integration.py` | Add 1 new test for the "publish all excludes github_pages" case |

### Files NOT to Change

- `backend/app/workers/publish.py` — `publish_github_job` is the dedicated GitHub path and is correct as-is
- `backend/app/services/publishing.py` `_publish_github` / `generate_github_post_file` — untouched
- Any DB migration — no schema changes
- Any API router — no endpoint changes

### Key Invariants to Preserve

- `dispatch_publish` called with `platforms=["github_pages"]` explicitly must still reach the
  `github_pages` branch (AC 2). The `else` branch only fires when `platforms` is empty.
- The `if "wordpress" in platform_names and "wordpress-com" in platform_names:` dedup block
  (lines 660-663) runs AFTER the new exclusion — do not move it.
- `connectedSelected` in the frontend already excludes `"headless"` (line 446 filters it out)
  and already excludes `github_pages` (never added to `availablePlatforms` at line 297).
  Sending it explicitly is safe.

### No Migration Required

This is a pure logic fix. No DB schema changes. No Alembic migration needed.

### Pattern Reference

The WordPress dedup pattern immediately below the fix location (lines 660-663) shows how
platform string normalisation is done in this function — use the same
`(c.platform if isinstance(c.platform, str) else c.platform.value)` idiom.

---

## Dev Agent Record

### Implementation Notes

- AC 1 & 2: Added `else` branch in `dispatch_publish` after the `if platforms:` filter block. When `platforms` is empty (publish-all path), `github_pages` connections are excluded before any dispatching. When `platforms` is non-empty (explicit selection), the `if` branch runs and `github_pages` can pass through if explicitly requested.
- AC 3: Removed `connectedPlatformCount` variable and the "send nothing if all selected" optimisation from `approval-panel.tsx`. `publishNow` now always receives the explicit `connectedSelected` array.
- AC 4: Added `test_dispatch_publish_excludes_github_pages_when_no_platforms_filter` to `test_meta_integration.py`. Verifies `github_pages` is absent from results and `facebook_page` succeeds when `platforms=None` with both connections present.

### Completion Notes

All 4 ACs satisfied. 65 meta/publishing tests pass (65 → 65, +1 new). No DB migration required. WordPress dedup ordering preserved.

---

## File List

- `backend/app/services/publishing.py`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
- `backend/tests/test_meta_integration.py`

---

## Review Findings

- [x] [Review][Patch] No test for AC 2 — explicit `platforms=["github_pages"]` bypass path unverified [backend/tests/test_meta_integration.py]
- [x] [Review][Patch] Misleading test value: `linkedin_post = "test caption for facebook"` [backend/tests/test_meta_integration.py:1843]
- [x] [Review][Defer] Hardcoded `"github_pages"` string — pre-existing pattern throughout codebase [backend/app/services/publishing.py] — deferred, pre-existing
- [x] [Review][Defer] Platform routing knowledge embedded in dispatcher — pre-existing design [backend/app/services/publishing.py] — deferred, pre-existing
- [x] [Review][Defer] `isinstance(c.platform, str)` idiom triplicated — pre-existing [backend/app/services/publishing.py] — deferred, pre-existing
- [x] [Review][Defer] Test for dispatch_publish placed in test_meta_integration.py — pre-existing pattern [backend/tests/test_meta_integration.py] — deferred, pre-existing
- [x] [Review][Defer] `platforms=[]` coercion brittleness — pre-existing [backend/app/services/publishing.py] — deferred, pre-existing

---

## Change Log

- 2026-08-01: Implemented AC 1-4. Backend guard in `dispatch_publish` excludes `github_pages` from "publish all" path. Frontend always sends explicit platforms list. New regression test added.
- 2026-08-01: Code review: 2 patches applied (AC 2 regression test added, misleading linkedin_post test value fixed), 5 deferred, 4 dismissed. Marked done.
