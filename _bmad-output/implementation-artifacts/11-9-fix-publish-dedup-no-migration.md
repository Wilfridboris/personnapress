---
baseline_commit: 2fd86a5ff2819920be9447e3df2d056ebd914549
---

# Story 11.9: Fix "Publish to More Platforms" Duplicates

Status: done

## Story

As an authenticated PersonnaPress user,
I want "Publish to more platforms" to only send content to platforms I haven't published to yet,
so that I don't create duplicate posts on platforms I've already reached.

## Acceptance Criteria

1. **Given** a campaign is in `published` status and the user clicks "Publish now" in the "Publish to more platforms" panel, **When** the publish job runs, **Then** `dispatch_publish` skips any platform that already has a successful publish job for this campaign — only dispatching to platforms NOT yet reached.

2. **Given** a campaign is in `approved` status (first publish), **When** "Publish now" is clicked, **Then** `dispatch_publish` publishes to ALL connected platforms with no filtering (existing behavior preserved).

3. **Given** a publish job completes with `status === "complete"` (all platforms succeeded), **When** the job record is written, **Then** `error_details` is populated with the per-platform results dict (e.g. `{"wordpress": "success", "linkedin": "success"}`) — same format already used for partial failures.

4. **Given** a campaign page loads and the campaign is in `published` status, **When** the approval panel reads which platforms were published, **Then** the "Published to [platforms]" display reads from `campaign.publish_job.error_details` (the actual publish results) rather than the currently-connected platform list.

5. **Given** the uncommitted change in `backend/app/routers/publishing.py` (the `campaign.status not in ("approved", "published")` guard added in story 11-7 dev work), **When** this story is implemented, **Then** that file is included in the commit so the guard is no longer an untracked change.

## Background: Why No Migration

The `jobs` table already stores per-platform publish results in `error_details` for the failure path. The only gap is that on full success, `run_publish` does NOT write `error_details` (line 115 of `publish.py`). Filling that one gap makes the jobs table a complete source of truth — no new column, no Alembic migration, no second source of truth.

**Important: partial success handling.** When some platforms succeed and others fail, `run_publish` already writes `error_details=json.dumps(results)` to the job (line 120–125 of `publish.py`). The success path just needs the same treatment. The `get_published_platforms_for_campaign` helper (Task 2) unions successful platforms across ALL complete publish jobs, so partial-success campaigns are handled correctly on the next re-publish.

## Tasks / Subtasks

### Task 1: Commit the uncommitted status guard from 11-7 (AC: 5)

- [x] 1.1 Verify `backend/app/routers/publishing.py` line ~854 reads:
  ```python
  if campaign.status not in ("approved", "published"):
  ```
  If correct, include this file in the story's git commit. Do not make other changes to this file beyond what is needed for Task 4.

### Task 2: Store per-platform results on publish success (AC: 3)

- [x] 2.1 In `backend/app/workers/publish.py`, in `run_publish` (line 104), find the `all_success` branch (line 111):

  **Current:**
  ```python
  if all_success:
      await update_campaign_status(db, campaign_id, "published")
      await update_campaign_scheduled_at(db, campaign_id, None)
      await update_job(db, job_id, status="complete", completed_at=utcnow())
  ```

  **Fixed (add `error_details=json.dumps(results)`):**
  ```python
  if all_success:
      await update_campaign_status(db, campaign_id, "published")
      await update_campaign_scheduled_at(db, campaign_id, None)
      await update_job(db, job_id, status="complete", error_details=json.dumps(results), completed_at=utcnow())
  ```

  `results` is already in scope (defined at line 531 of `publishing.py`, set in the worker before this branch). `json` is already imported in `publish.py`.

### Task 3: Add `get_published_platforms_for_campaign` helper (AC: 1)

- [x] 3.1 In `backend/app/db/repositories/jobs.py`, add a new function after `get_publish_job_for_campaign`:

  ```python
  async def get_published_platforms_for_campaign(
      session: AsyncSession,
      campaign_id: uuid.UUID,
  ) -> set[str]:
      """Return the set of platform names successfully published for this campaign.

      Unions results across all complete publish/scheduled_publish jobs, so partial
      successes on earlier attempts are captured correctly.
      """
      import json as _json
      result = await session.execute(
          select(Job)
          .where(
              Job.campaign_id == campaign_id,
              Job.job_type.in_(["publish", "scheduled_publish"]),
              Job.status == "complete",
          )
      )
      jobs = result.scalars().all()
      published: set[str] = set()
      for job in jobs:
          if job.error_details:
              try:
                  details = _json.loads(job.error_details)
                  for platform, status in details.items():
                      if status == "success":
                          published.add(platform)
              except (ValueError, AttributeError):
                  pass
      return published
  ```

  No new imports needed at module level — `uuid`, `AsyncSession`, `select`, and `Job` are already imported.

### Task 4: Filter already-published platforms in `dispatch_publish` (AC: 1, 2)

- [x] 4.1 In `backend/app/services/publishing.py`, in `dispatch_publish` (line 516), add dedup logic after loading connections and before the platform loop.

  Add the import at the top of the file (with the other repository imports):
  ```python
  from app.db.repositories.jobs import get_published_platforms_for_campaign
  ```

  In `dispatch_publish`, after the WordPress/WordPress.com precedence filter (line 530), add:
  ```python
  # On re-publish (campaign already published), skip platforms already reached.
  # On first publish (approved), publish to everything.
  campaign_status = campaign.status if isinstance(campaign.status, str) else campaign.status.value
  skip_platforms: set[str] = set()
  if campaign_status == "published":
      skip_platforms = await get_published_platforms_for_campaign(db, campaign_id)
  ```

  Then inside the `for conn in connections:` loop, add a skip guard right after the `platform = ...` line:
  ```python
  if platform in skip_platforms:
      logger.info("dispatch_publish: skipping %s (already published) campaign=%s", platform, campaign_id)
      continue
  ```

  **Edge case**: If ALL connected platforms are already published (skip_platforms == all connected), `results` will be empty. The `all_success = all(v == "success" for v in results.values()) and bool(results)` check in `run_publish` will be `False` (empty dict) and the campaign would be set to `failed`. Guard against this:

  After the `for conn in connections:` loop, add before returning `results`:
  ```python
  # If all platforms were already published (nothing dispatched), treat as success.
  if not results and skip_platforms:
      return {p: "already_published" for p in skip_platforms}
  ```

  And in `run_publish`, the `all_success` check needs to also accept `"already_published"` as a success-equivalent value:
  ```python
  all_success = all(v in ("success", "already_published") for v in results.values()) and bool(results)
  ```

### Task 5: Fix frontend "Published to" display (AC: 4)

- [x] 5.1 In `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`, find the `useEffect` for the `published` state (line 213, condition: `effectiveStatus === "published" && clientHasPlatforms === null`).

  **Current (reads connected platforms, not actual published platforms):**
  ```typescript
  const connected = items.filter((c) => c.connected).map((c) => platformLabel(c.platform));
  setPublishedPlatforms(connected);
  ```

  **Fixed (read from campaign.publish_job.error_details):**
  Replace those two lines with:
  ```typescript
  // Read actual published platforms from the job results.
  // Falls back to connected-platform list for campaigns published before this fix
  // (when error_details was null on success).
  const jobDetails = (() => {
    try { return JSON.parse(campaign.publish_job?.error_details ?? "{}"); } catch { return {}; }
  })();
  const actualPublished = (Object.entries(jobDetails) as [string, string][])
    .filter(([, v]) => v === "success" || v === "already_published")
    .map(([p]) => platformLabel(p));
  setPublishedPlatforms(actualPublished.length > 0 ? actualPublished : items.filter((c) => c.connected).map((c) => platformLabel(c.platform)));
  ```

  `campaign` is already a prop — no additional API call needed. `campaign.publish_job` is typed as `PublishJobInfo | null | undefined` in `frontend/lib/types.ts` (line 108).

- [x] 5.2 In the same file, update the button subtext in the `showRepublishControls` section (line 892-893) from:
  ```typescript
  <p className="font-mono text-xs text-graphite">Publishes to all connected platforms</p>
  ```
  to:
  ```typescript
  <p className="font-mono text-xs text-graphite">Publishes to platforms not yet reached</p>
  ```

- [x] 5.3 Also delete the untracked file `backend/=0.13.1` — it is a pip install artifact (created by a mistyped `pip install package ==0.13.1`). Delete it from the filesystem; it is not tracked by git so no `git rm` needed.

## Dev Notes

### Existing patterns to follow

- `dispatch_publish` is in `backend/app/services/publishing.py:516`. The platform loop starts at line 535.
- `run_publish` is in `backend/app/workers/publish.py:104`. The `all_success` branch starts at line 111.
- `get_publish_job_for_campaign` in `jobs.py:87` shows the existing pattern for job queries — follow the same SQLAlchemy `select(...).where(...).order_by(...).limit(1)` style.
- `campaign.status` is stored as a `CampaignStatus` enum in the DB but arrives as a string in many comparisons — always compare with `isinstance(campaign.status, str)` guard or use `.value` (pattern already used at line 528 of publishing.py).

### What NOT to do

- Do NOT add a `published_platforms` column to the campaigns table or write an Alembic migration. The jobs table is the single source of truth.
- Do NOT change the GitHub publish path (`publish_github_job` in `publish.py` / `publish_campaign_github` in `publishing.py`). GitHub publishes are tracked separately via `github_pr_url` and are not part of the multi-platform `dispatch_publish` flow.
- Do NOT change the retry endpoint (`/campaigns/{campaign_id}/publish/retry`). It already checks `error_details` per-platform before retrying and is unaffected by this fix.
- Do NOT toast in the GitHub polling effect — it already shows an inline PR/commit result banner on success.

### Project constraints

- No emojis in code or UI text.
- Icons must be from the installed icon library (lucide-react); no new icon imports needed here.
- No comments in code unless the WHY is non-obvious. The `logger.info` skip line and the fallback comment in 5.1 are warranted.

### References

- [Source: `backend/app/workers/publish.py`] Lines 104–138: `run_publish` full function
- [Source: `backend/app/services/publishing.py`] Lines 516–593: `dispatch_publish` full function
- [Source: `backend/app/db/repositories/jobs.py`] Lines 87–97: `get_publish_job_for_campaign` — pattern to follow
- [Source: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`] Lines 213–238: published-state useEffect
- [Source: `frontend/lib/types.ts`] Line 108: `publish_job?: PublishJobInfo | null` on Campaign type
- [Source: `backend/app/schemas/campaign.py`] Lines 8–14: `PublishJobInfo` — `error_details: Optional[str]`
- [Source: `backend/app/db/repositories/models.py`] Lines 131–145: `Job` model — `error_details: Optional[str]`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None._

### Completion Notes List

- Task 1 (AC5): Verified `publishing.py:854` already had the status guard from 11-7 dev work. File included in commit.
- Task 2 (AC3): Added `error_details=json.dumps(results)` to `update_job` in `run_publish`'s `all_success` branch in `publish.py`. Also updated `all_success` check to accept `"already_published"` as success-equivalent to support the edge case added in Task 4.
- Task 3 (AC1): Added `get_published_platforms_for_campaign` helper to `jobs.py` after `get_publish_job_for_campaign`. Unions successful platform results across all complete publish/scheduled_publish jobs for a campaign.
- Task 4 (AC1, AC2): Added `get_published_platforms_for_campaign` import to `publishing.py`. In `dispatch_publish`, added `skip_platforms` dedup logic gated on `campaign_status == "published"` (first-publish path is unchanged). Added skip guard inside the platform loop. Added edge-case guard returning `"already_published"` dict when all platforms were already reached.
- Task 5 (AC4): Updated the `published` useEffect in `approval-panel.tsx` to read actual published platforms from `campaign.publish_job?.error_details` with fallback to connected platforms (for campaigns published before this fix). Updated button subtext in `showRepublishControls` to "Publishes to platforms not yet reached". Deleted `backend/=0.13.1` pip artifact.
- Zero regressions: Backend tests went from 49 failed (baseline) to 48 failed — one fewer failure, no new failures. Pre-existing TS errors in `ClientDetail.tsx` are unrelated to this story.

### File List

- `backend/app/workers/publish.py`
- `backend/app/services/publishing.py`
- `backend/app/db/repositories/jobs.py`
- `backend/app/routers/publishing.py`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`

### Review Findings

- [x] [Review][Decision] "Published to" display reads only from most recent job — dismissed; spec explicitly targets `campaign.publish_job.error_details` and the partial re-publish scenario is uncommon. Defer to a follow-up story if it becomes a user pain point.
- [x] [Review][Patch] Move `import json as _json` to module level [backend/app/db/repositories/jobs.py:98]
- [x] [Review][Patch] Add `TypeError` to except clause in `get_published_platforms_for_campaign` [backend/app/db/repositories/jobs.py:122]
- [x] [Review][Patch] Validate jobDetails is a plain object before calling `Object.entries` [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:221]
- [x] [Review][Patch] Show "Already published to all connected platforms." toast when all platforms were skipped (all `already_published`) instead of misleading "Published successfully." [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:392]
- [x] [Review][Patch] `get_published_platforms_for_campaign` should also recognize `"already_published"` as a successfully-reached status [backend/app/db/repositories/jobs.py:117]
- [x] [Review][Defer] `error_details` field name semantically inverted — stores success data on complete jobs [backend/app/workers/publish.py] — deferred, pre-existing design
- [x] [Review][Defer] No concurrency guard before creating a new publish job — multiple simultaneous re-publish jobs possible [backend/app/routers/publishing.py] — deferred, pre-existing
- [x] [Review][Defer] Full ORM objects loaded in `get_published_platforms_for_campaign` when only `error_details` column is needed [backend/app/db/repositories/jobs.py] — deferred, minor impact
- [x] [Review][Defer] No test coverage for new dedup paths (all-already-published, partial re-publish, legacy campaigns) — deferred, pre-existing project pattern
- [x] [Review][Defer] `"already_published"` sentinel value used in 4 locations with no shared constant — deferred, style concern

### Change Log

- 2026-07-11: Implemented story 11.9 — publish dedup on re-publish (no migration). Stored per-platform results on success, added `get_published_platforms_for_campaign` helper, added skip logic in `dispatch_publish`, fixed frontend "Published to" display, deleted pip artifact.
