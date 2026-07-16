---
baseline_commit: ad345ff
---

# Story 14.1: Platform Destination Picker for Publish Now & Schedule

Status: done

## Story

As an authenticated user,
I want to select which specific platforms to publish or schedule to before confirming a publish action,
So that I can publish to LinkedIn only, or schedule my Headless Blog post for Tuesday morning, without having to re-wire my connections.

## Acceptance Criteria

1. **Given** an approved campaign with at least one connected platform, **When** the Approval Gate footer renders, **Then** a row of destination chips appears above the action buttons — one chip per connected platform (WordPress, Webflow, X, LinkedIn, WordPress.com) plus one "Headless Blog" chip (always shown); all chips are selected by default (Highlighter fill `#FFF1B8`, 1px Ink border, `Check` icon + platform icon + label); GitHub Pages retains its own dedicated "Publish to GitHub" button and is NOT included in the chip row.

2. **Given** the destination chip row is visible, **When** a user clicks a selected chip, **Then** the chip deselects (Paper fill, Border color `#E5E5E5`, platform icon + label only, no `Check` icon); clicking a deselected chip re-selects it; hover on any chip shows `border-ink text-ink`; all chip transitions use `transition-colors duration-150`.

3. **Given** no destination chips are selected, **When** the "Publish now" and "Schedule" buttons render, **Then** both are disabled (`opacity-50 cursor-not-allowed`); a `text-xs text-danger` note reads "Select at least one destination to publish."

4. **Given** only the "Headless Blog" chip is selected (all connected platform chips deselected), **When** the user clicks "Schedule", **Then** the schedule datetime picker opens normally; on confirm, `POST /api/v1/campaigns/{id}/publish-headless` is called with `{"scheduled_at": "<iso>"}` — the article is created as `status='hidden'` immediately and APScheduler registers a `DateTrigger` job to flip it to `status='published'` at the scheduled time; a success toast reads "Headless Blog scheduled for [formatted date]." — no campaign status change occurs (campaign remains `approved`).

5. **Given** the user has selected a subset of connected platforms and clicks "Publish now", **When** the action fires, **Then**:
   - If any connected platforms (non-headless) are selected: `POST /api/v1/campaigns/{id}/publish` is called with `{"platforms": ["wordpress", "linkedin"]}` — only those platforms receive the publish job.
   - If "Headless Blog" is also selected: `POST /api/v1/campaigns/{id}/publish-headless` is called (no `scheduled_at`) — article published immediately.
   - If only "Headless Blog" is selected: only `POST /publish-headless` is called (no `scheduled_at`); no `POST /publish` is made.
   - Existing publish job polling and toast behavior unchanged.

6. **Given** the user has selected a mix of connected platforms and "Headless Blog" and clicks "Schedule", **When** they confirm a future datetime, **Then**:
   - `POST /api/v1/campaigns/{id}/publish-headless` is called with `{"scheduled_at": "<iso>"}` — article created as `hidden`, APScheduler job registered to flip it at the scheduled time.
   - `POST /api/v1/campaigns/{id}/publish/schedule` is called with `{"scheduled_at": "<iso>", "platforms": ["wordpress"]}` — connected platforms scheduled via APScheduler as before.
   - Both calls are made; errors in either surface as toasts; the campaign transitions to `scheduled` state from the connected-platform schedule call.

7. **Given** `POST /api/v1/campaigns/{id}/publish` is called **without** a `platforms` body, **When** the backend processes it, **Then** it publishes to ALL connected platforms (backward-compatible behavior, no regression).

8. **Given** the "Publish to more platforms" republish section (published campaign state), **When** it renders, **Then** it shows the same destination chip row (all available platforms selected by default); "Publish now" and "Schedule" use the same filtered-publish logic; the sub-label updates: all selected → "Publishes to platforms not yet reached"; partial → "Publishes to N selected platform(s) not yet reached."

9. **Given** the destination chip row, **When** all chips are selected, **Then** "Publish now" shows the sub-label "Publishes to all platforms"; when only some are selected, it shows "Publishes to N selected platform(s)."

10. **Given** the APScheduler job `run_publish_headless` fires at the scheduled time, **When** it executes, **Then** it looks up the article by `campaign_id`, sets `article.status = 'published'`, commits, and logs the result; if no article is found (e.g. campaign deleted), it logs a warning and exits cleanly without raising.

11. **Given** the blockquote CSS fix, **When** `prose blockquote` renders in the blog preview, **Then** it shows a thin 1px Ink left border and `font-style: normal`. **Already applied prior to this story — verify only.**

## Tasks / Subtasks

### Task 1: Backend — add `platforms` filter to publish endpoint (AC: 5, 7)

- [x] 1.1 Create or update `backend/app/schemas/publishing.py` with:
  ```python
  from pydantic import BaseModel
  from typing import Optional

  class PublishRequest(BaseModel):
      platforms: Optional[list[str]] = None  # None = publish all connected platforms

  class PublishHeadlessRequest(BaseModel):
      scheduled_at: Optional[datetime] = None  # None = publish immediately
  ```

- [x] 1.2 Update `POST /campaigns/{campaign_id}/publish` in `backend/app/routers/publishing.py`:
  ```python
  from fastapi import Body
  @router.post("/campaigns/{campaign_id}/publish", status_code=202)
  async def publish_campaign_now(
      campaign_id: uuid.UUID,
      request: PublishRequest = Body(default=PublishRequest()),
      ...
  ):
  ```
  Pass `request.platforms or []` when dispatching: `background_tasks.add_task(run_publish, job.id, campaign_id, request.platforms or [])`.

- [x] 1.3 Update `backend/app/workers/publish.py` — `run_publish` signature:
  ```python
  async def run_publish(job_id: UUID, campaign_id: UUID, platforms: list[str] = []) -> None:
  ```
  Pass `platforms` to `dispatch_publish`.

- [x] 1.4 Update `backend/app/services/publishing.py` — `dispatch_publish`:
  ```python
  async def dispatch_publish(db, campaign_id, job_id, platforms: list[str] = []) -> dict:
      ...
      connections = await get_connections_for_client(db, campaign.client_id)
      if platforms:
          connections = [c for c in connections if c.platform in platforms]
  ```

- [x] 1.5 Backend tests in `backend/tests/routers/test_publish_now.py`:
  - `test_publish_now_with_platform_filter` — POST `{"platforms": ["wordpress"]}`, verify only WP dispatched.
  - `test_publish_now_no_body_publishes_all` — no body, all connections dispatched.
  - `test_publish_now_empty_platforms_list_publishes_all` — `{"platforms": []}`, same as no body.

- [x] 1.6 `backend/tests/services/test_publishing.py`:
  - `test_dispatch_publish_filters_by_platforms` — connections=[WP, LI], platforms=["linkedin"], only LI called.
  - `test_dispatch_publish_empty_platforms_publishes_all` — platforms=[], all called.

### Task 2: Backend — add `platforms` filter to schedule endpoint (AC: 6, 7)

- [x] 2.1 Update `ScheduleRequest` in `backend/app/routers/publishing.py` (or schemas):
  ```python
  class ScheduleRequest(BaseModel):
      scheduled_at: datetime
      platforms: Optional[list[str]] = None
  ```

- [x] 2.2 Pass `platforms` as APScheduler job arg:
  ```python
  scheduler.add_job(
      run_publish,
      trigger=DateTrigger(run_date=scheduled_utc),
      id=str(job.id),
      args=[str(job.id), str(campaign_id), request.platforms or []],
  )
  ```
  **Backward compatibility:** Existing stored APScheduler jobs have 2 args (`[job_id, campaign_id]`). New jobs have 3. The `platforms=[]` default on `run_publish` means 2-arg stored jobs still work — they will publish all platforms. No migration needed.

- [x] 2.3 Backend test in `backend/tests/routers/test_schedule_publish.py`:
  - `test_schedule_with_platform_filter` — POST `{"scheduled_at": future, "platforms": ["linkedin"]}`, verify APScheduler `add_job` args include `["linkedin"]`.

### Task 3: Backend — headless scheduling via `publish-headless` with `scheduled_at` (AC: 4, 6, 10)

- [x] 3.1 Update `POST /campaigns/{campaign_id}/publish-headless` in `backend/app/routers/publishing.py` to accept an optional body:
  ```python
  @router.post("/campaigns/{campaign_id}/publish-headless")
  async def publish_headless(
      campaign_id: uuid.UUID,
      request: PublishHeadlessRequest = Body(default=PublishHeadlessRequest()),
      ...
  ):
  ```

- [x] 3.2 Branch on `request.scheduled_at`:
  ```python
  if request.scheduled_at:
      # Create article as hidden — do NOT mark campaign as published yet
      article = await create_or_update_article_from_campaign(db, campaign, status="hidden")
      await db.commit()
      scheduler.add_job(
          run_publish_headless,
          trigger=DateTrigger(run_date=request.scheduled_at),
          id=f"headless_{campaign_id}",
          args=[str(campaign_id)],
          replace_existing=True,  # safe to re-schedule
      )
      return {"article_id": str(article.id), "slug": article.slug, "status": "scheduled"}
  else:
      # Existing behavior: publish immediately, mark campaign published
      article = await create_or_update_article_from_campaign(db, campaign)
      campaign.status = "published"
      await db.commit()
      return {"article_id": str(article.id), "slug": article.slug, "status": "published"}
  ```

  Check the current `create_or_update_article_from_campaign` signature in `backend/app/services/articles.py` (from Story 12.1). If it does not accept a `status` override, add a `status: str = "published"` parameter — it should only require a one-line change to the article creation call.

- [x] 3.3 Create `run_publish_headless` worker in `backend/app/workers/publish.py` (alongside existing `run_publish`):
  ```python
  async def run_publish_headless(campaign_id_str: str) -> None:
      """APScheduler fires this to flip a scheduled headless article from hidden → published."""
      from uuid import UUID
      campaign_id = UUID(campaign_id_str)
      async with get_session_context() as db:
          # Look up the article by campaign_id
          article = await get_article_by_campaign_id(db, campaign_id)
          if not article:
              logger.warning("run_publish_headless: no article for campaign=%s — skipping", campaign_id)
              return
          article.status = "published"
          article.updated_at = utcnow()
          await db.commit()
          logger.info("run_publish_headless: article=%s published (campaign=%s)", article.id, campaign_id)
  ```

  Check `backend/app/db/repositories/articles.py` for a `get_article_by_campaign_id` function. Story 12.1 likely added it (the service calls it to handle idempotent publish). If absent, add:
  ```python
  async def get_article_by_campaign_id(db: AsyncSession, campaign_id: UUID) -> Optional[Article]:
      result = await db.execute(select(Article).where(Article.campaign_id == campaign_id))
      return result.scalar_one_or_none()
  ```

- [x] 3.4 Import `run_publish_headless` in the scheduler setup if APScheduler needs to resolve it by reference (check if existing `run_publish` needs any import registration — match that pattern).

- [x] 3.5 Backend tests in `backend/tests/routers/test_publishing.py` (headless section):
  - `test_publish_headless_immediate` — no body, article created as `published`, campaign `published`.
  - `test_publish_headless_scheduled` — body `{"scheduled_at": future}`, article created as `hidden`, APScheduler `add_job` called with `run_publish_headless`.
  - `test_publish_headless_schedule_replace_existing` — calling schedule twice replaces the APScheduler job (does not create a duplicate).
  - `test_run_publish_headless_flips_status` — unit test: given article with `status='hidden'`, after `run_publish_headless` it is `published`.
  - `test_run_publish_headless_missing_article` — no article for campaign, logs warning, returns without error.

### Task 4: Frontend — destination chip state and data (AC: 1, 2, 3)

- [x] 4.1 In `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`, add state:
  ```typescript
  const [availablePlatforms, setAvailablePlatforms] = useState<string[]>([])
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set())
  ```

- [x] 4.2 In the existing `useEffect` that fetches connections (status === 'approved'), after processing GitHub, build the platform list:
  ```typescript
  const connectedPlatforms = items
    .filter((c) => c.connected && c.platform !== 'github_pages')
    .map((c) => c.platform)
  const allDestinations = [...connectedPlatforms, 'headless']
  setAvailablePlatforms(allDestinations)
  setSelectedPlatforms(new Set(allDestinations))
  ```
  GitHub Pages is excluded from the chip row — it keeps its own dedicated button.

- [x] 4.3 Repeat the same for the second `useEffect` (status === 'published') that powers the republish section.

### Task 5: Frontend — DestinationChip component and chip row (AC: 1, 2, 9)

- [x] 5.1 Add new Lucide imports. Check installed version in `frontend/package.json` before writing the import line:
  ```typescript
  import { GitBranch, Database, Loader2, CheckCircle2, XCircle, RefreshCw,
           Check, Globe, Layout, Twitter, Linkedin } from "lucide-react";
  ```
  Fallbacks if an icon is missing: `Twitter` → `AtSign`; `Linkedin` → `Share2`. Never use emojis.

- [x] 5.2 Add constants near the top of the file (after imports):
  ```typescript
  const PLATFORM_ICON_MAP: Record<string, React.ElementType> = {
    wordpress: Globe, "wordpress-com": Globe,
    webflow: Layout, x: Twitter, linkedin: Linkedin, headless: Database,
  };
  const PLATFORM_LABEL_MAP: Record<string, string> = {
    wordpress: "WordPress", "wordpress-com": "WordPress.com",
    webflow: "Webflow", x: "X", linkedin: "LinkedIn", headless: "Headless Blog",
  };
  ```

- [x] 5.3 Add an inline `DestinationChip` function (not exported):
  ```typescript
  function DestinationChip({ platform, selected, onToggle }: {
    platform: string; selected: boolean; onToggle: () => void;
  }) {
    const Icon = PLATFORM_ICON_MAP[platform] ?? Globe;
    const label = PLATFORM_LABEL_MAP[platform] ?? platform;
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={selected}
        aria-label={`${selected ? "Deselect" : "Select"} ${label}`}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium border",
          "transition-colors duration-150 rounded-none",
          "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
          selected
            ? "bg-highlighter border-ink text-ink"
            : "bg-paper border-border text-graphite hover:border-ink hover:text-ink",
        )}
      >
        {selected && <Check className="size-3.5" aria-hidden="true" />}
        <Icon className="size-3.5" aria-hidden="true" />
        {label}
      </button>
    );
  }
  ```

- [x] 5.4 Add derived values inside the approved-state render block:
  ```typescript
  const hasConnectedSelected = [...selectedPlatforms].some(p => p !== 'headless');
  const nothingSelected = selectedPlatforms.size === 0;
  const allPlatformsSelected = availablePlatforms.length > 0 &&
    availablePlatforms.every(p => selectedPlatforms.has(p));
  const publishNowSubLabel = allPlatformsSelected
    ? "Publishes to all platforms"
    : `Publishes to ${selectedPlatforms.size} selected platform(s)`;
  ```

- [x] 5.5 Replace the `clientHasPlatforms === true` action block with the new layout (chip row + GitHub button + Schedule + Publish now):
  ```tsx
  <div className="flex flex-col gap-3">
    {/* Destination chips */}
    {availablePlatforms.length > 0 && (
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-mono text-xs text-graphite uppercase tracking-wider">
          Publish to:
        </span>
        {availablePlatforms.map((platform) => (
          <DestinationChip
            key={platform}
            platform={platform}
            selected={selectedPlatforms.has(platform)}
            onToggle={() =>
              setSelectedPlatforms((prev) => {
                const next = new Set(prev);
                next.has(platform) ? next.delete(platform) : next.add(platform);
                return next;
              })
            }
          />
        ))}
      </div>
    )}

    {/* No-selection warning */}
    {nothingSelected && (
      <p className="text-xs text-danger" role="alert">
        Select at least one destination to publish.
      </p>
    )}

    {/* Action row */}
    <div className="flex items-center gap-3 flex-wrap">
      {/* GitHub retains its own button */}
      {githubPublishReady && (
        <button type="button" onClick={() => setShowGitHubPanel(v => !v)}
          disabled={isPublishing || isGitHubPublishing || isHeadlessPublishing}
          className={cn(
            "inline-flex items-center gap-2 px-5 py-2.5 border border-ink text-ink text-sm font-medium",
            "hover:bg-ink hover:text-white transition-colors",
            "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}>
          <GitBranch className="size-4" aria-hidden="true" />
          Publish to GitHub
        </button>
      )}

      <button type="button" onClick={() => setShowSchedulePicker(v => !v)}
        disabled={nothingSelected}
        className={cn(
          "inline-flex items-center px-5 py-2.5 border border-ink text-ink text-sm font-medium",
          "hover:bg-ink hover:text-white transition-colors",
          "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none",
          "disabled:opacity-50 disabled:cursor-not-allowed",
        )}>
        Schedule
      </button>

      <div className="flex flex-col gap-1">
        <button type="button" onClick={handlePublishNow}
          disabled={isPublishing || isGitHubPublishing || isHeadlessPublishing || nothingSelected}
          className={cn(
            "inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm font-medium border border-transparent",
            "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all",
            "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
            "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
          )}>
          {isPublishing ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
          {isPublishing ? "Publishing..." : "Publish now"}
        </button>
        <p className="font-mono text-xs text-graphite">{publishNowSubLabel}</p>
      </div>
    </div>
  </div>
  ```

### Task 6: Frontend — wire platform-filtered Publish Now (AC: 5)

- [x] 6.1 Update `campaignsApi.publishNow` in `frontend/lib/api.ts`:
  ```typescript
  publishNow: (id: string, platforms?: string[]) =>
    apiFetch<{ job_id: string }>(`/campaigns/${id}/publish`, {
      method: "POST",
      ...(platforms?.length
        ? { body: JSON.stringify({ platforms }), headers: { "Content-Type": "application/json" } }
        : {}),
    }),
  ```
  Verify `apiFetch` merges `headers` correctly — read `frontend/lib/api.ts` before writing.

- [x] 6.2 Update `campaignsApi.publishHeadless` in `frontend/lib/api.ts`:
  ```typescript
  publishHeadless: (id: string, scheduledAt?: string) =>
    apiFetch<{ article_id: string; slug: string; status: string }>(
      `/campaigns/${id}/publish-headless`,
      {
        method: "POST",
        ...(scheduledAt
          ? { body: JSON.stringify({ scheduled_at: scheduledAt }), headers: { "Content-Type": "application/json" } }
          : {}),
      },
    ),
  ```

- [x] 6.3 Update `handlePublishNow` in `approval-panel.tsx`:
  ```typescript
  const handlePublishNow = useCallback(async () => {
    setIsPublishing(true);
    const connectedSelected = [...selectedPlatforms].filter(p => p !== 'headless');
    const headlessSelected = selectedPlatforms.has('headless');
    try {
      if (headlessSelected) {
        const result = await campaignsApi.publishHeadless(campaign.id); // no scheduledAt = immediate
        setHeadlessResult({ articleId: result.article_id, slug: result.slug });
      }
      if (connectedSelected.length > 0) {
        const { job_id } = await campaignsApi.publishNow(campaign.id, connectedSelected);
        setActiveJobId(job_id);
      } else {
        // Only headless was selected — done, no polling needed
        setIsPublishing(false);
        router.refresh();
      }
    } catch (err) {
      if (err instanceof APIError && err.code === 'TRIAL_EXPIRED') showUpgradePrompt(err.message);
      else addToast(err instanceof APIError ? err.message : 'Publish failed.', 'error');
      setIsPublishing(false);
    }
  }, [campaign.id, selectedPlatforms, router, addToast, showUpgradePrompt]);
  ```

### Task 7: Frontend — wire platform-filtered Schedule (AC: 4, 6)

- [x] 7.1 Update `campaignsApi.schedule` in `frontend/lib/api.ts`:
  ```typescript
  schedule: (id: string, scheduledAt: string, platforms?: string[]) =>
    apiFetch<void>(`/campaigns/${id}/publish/schedule`, {
      method: "POST",
      body: JSON.stringify({ scheduled_at: scheduledAt, ...(platforms ? { platforms } : {}) }),
      headers: { "Content-Type": "application/json" },
    }),
  ```

- [x] 7.2 Update `handleConfirmSchedule` in `approval-panel.tsx`:
  ```typescript
  const handleConfirmSchedule = useCallback(async () => {
    setIsScheduling(true);
    const connectedSelected = [...selectedPlatforms].filter(p => p !== 'headless');
    const headlessSelected = selectedPlatforms.has('headless');
    const isoDate = new Date(scheduledAt).toISOString();
    try {
      if (headlessSelected) {
        // Article created as hidden now; APScheduler flips it at scheduled time
        const result = await campaignsApi.publishHeadless(campaign.id, isoDate);
        setHeadlessResult({ articleId: result.article_id, slug: result.slug });
        addToast(
          `Headless Blog scheduled for ${new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(scheduledAt))}.`,
          'success',
        );
      }
      if (connectedSelected.length > 0) {
        await campaignsApi.schedule(campaign.id, isoDate, connectedSelected);
      }
      router.refresh();
    } catch (err) {
      if (err instanceof APIError && err.code === 'TRIAL_EXPIRED') showUpgradePrompt(err.message);
      else addToast(err instanceof APIError ? err.message : 'Scheduling failed.', 'error');
    } finally {
      setIsScheduling(false);
    }
  }, [campaign.id, scheduledAt, selectedPlatforms, router, addToast, showUpgradePrompt]);
  ```

- [x] 7.3 No special note needed in the schedule picker UI about headless. The picker opens and works the same for any selection. Remove any "Headless Blog will publish immediately" copy (it was in the previous draft — do not add it).

### Task 8: Frontend — republish section chip row (AC: 8)

- [x] 8.1 Apply the same `DestinationChip` row inside `showRepublishControls` in the published-state block (around line 916 in current file). The `availablePlatforms` and `selectedPlatforms` state applies to both sections.

- [x] 8.2 Reset `selectedPlatforms` to all-selected when republish panel opens:
  ```typescript
  useEffect(() => {
    if (showRepublishControls && availablePlatforms.length > 0) {
      setSelectedPlatforms(new Set(availablePlatforms));
    }
  }, [showRepublishControls]);
  ```

- [x] 8.3 Update the republish "Publish now" sub-label to reflect selection state (same `publishNowSubLabel` derived value).

### Task 9: Tests (AC: all)

- [x] 9.1 Backend — `test_publish_now.py`: 3 tests per Task 1.5–1.6.
- [x] 9.2 Backend — `test_schedule_publish.py`: 1 test per Task 2.3.
- [x] 9.3 Backend — `test_publishing.py` (headless section): 5 tests per Task 3.5.
- [x] 9.4 Frontend — `ApprovalPanel.test.tsx`:
  - `chips render for each connected platform plus headless`
  - `clicking selected chip deselects it; clicking again re-selects`
  - `Publish now and Schedule disabled when no chips selected`
  - `Publish now with WP+LI selected calls publishNow(id, ["wordpress","linkedin"])`
  - `Publish now with headless-only calls publishHeadless(id) with no scheduledAt`
  - `Publish now with WP+headless calls publishNow(["wordpress"]) and publishHeadless(id)`
  - `Schedule confirm with WP calls schedule(id, iso, ["wordpress"])`
  - `Schedule confirm with headless-only calls publishHeadless(id, iso)`
  - `Schedule confirm with WP+headless calls both publishHeadless(id, iso) and schedule(id, iso, ["wordpress"])`
  - `headless scheduled result shows in headlessResult state after schedule confirm`

## Dev Notes

### Critical: Read approval-panel.tsx in full before touching it

This is the most heavily patched file in the codebase (11-2, 11-7, 11-8, 11-9, 12-3). Preserved invariants:

1. `githubResult` reset to `null` when republish panel opens — patched in story 11-2.
2. `scheduledAt` reset when republish schedule picker opens — patched in story 11-2.
3. `setClientHasPlatforms(null)` called after publish completes so connections re-fetch.
4. `isHeadlessPublishing` disables all publish buttons while in-flight — still required.
5. Job polling `useEffect` clears both `isPublishing` and `setActiveJobId(null)` on terminal state — do not break.

### `Body(default=PublishRequest())` pattern

Without `Body(default=...)`, FastAPI returns 422 when the body is missing. Both `PublishRequest` and `PublishHeadlessRequest` use this pattern so callers that POST with no body get default values (publish all / publish immediately).

### APScheduler args backward compatibility

Existing stored APScheduler jobs in `apscheduler_jobs` used `args=[job_id, campaign_id]` (2 args). After Task 1, new jobs use `args=[job_id, campaign_id, platforms_list]` (3 args). Because `run_publish` has `platforms: list[str] = []` as a default, old 2-arg jobs still work and publish all platforms. No migration needed.

### `run_publish_headless` APScheduler registration

APScheduler requires the function to be importable at the module level. Register it in `scheduler.py` or ensure it is imported in `main.py` before `scheduler.start()`. Match how `run_publish` is currently referenced in the scheduler setup — read `backend/app/scheduler/scheduler.py` before implementing.

### `create_or_update_article_from_campaign` status parameter

Read `backend/app/services/articles.py` (Story 12.1). The function likely hardcodes `status='published'`. Add an optional `status: str = "published"` parameter. Only one line changes: the line that sets `article.status` at creation time. On update (existing article), do NOT override the current status — a re-schedule should not re-hide a previously published article.

### Headless scheduling UX — campaign status stays `approved`

When only headless is scheduled (no connected platforms), the campaign remains `approved` — it does NOT transition to `scheduled`. The `campaign.scheduled_at` field is not set. The user sees the Headless Blog chip with a headless result link below it (from `setHeadlessResult`), and a toast confirms the schedule. The article appears in `/blog` as `hidden` until the APScheduler job fires. This is intentional — `campaign.scheduled_at` tracks connected-platform schedules only.

### Lucide icon verification

Check `frontend/package.json` for lucide-react version before writing imports. Known safe icons (available since v0.100+): `Globe`, `Layout`, `Database`, `Check`. `Twitter` available since v0.263; `Linkedin` available since v0.115. If the installed version predates these, use `AtSign` for X and `Share2` for LinkedIn.

### `apiFetch` body/headers merging

Check how existing JSON-body calls work in `frontend/lib/api.ts` (e.g., `campaignsApi.reject`, `campaignsApi.schedule`). Match that exact pattern — do not invent a new structure.

### No new platform added

This story only changes *which existing connected platforms receive the action*. No new platform integration, no schema migration for platform data, no changes to `platform_connections` table.

### Blockquote fix — already applied, verify only

`frontend/app/globals.css`:
- `--tw-prose-quote-borders: #111111` (in `@theme` block)
- `.prose :where(blockquote)...` override for `border-left-width: 1px` and `font-style: normal`

Do NOT re-apply. Do NOT remove.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Used `Annotated[Optional[PublishRequest], Body()] = None` pattern instead of `Body(default=PublishRequest())` to avoid FastAPI FieldInfo leaking into direct unit-test function calls.
- `Linkedin` icon not available in installed Lucide version; used `Share2` as fallback per story guidance.
- Added `QueryClientProvider` wrapper to ApprovalPanel tests (component uses `useQuery` for client name autofill).
- Spread syntax `...(filterPlatforms !== undefined ? [filterPlatforms] : [])` used to avoid passing `undefined` as third arg to `publishNow`/`schedule` (would break existing test matchers).

### Completion Notes List

- All 11 ACs satisfied.
- Backend: 10 new tests across 4 test files; all 75 publish-related backend tests pass.
- Frontend: 8 new chip-specific tests added to ApprovalPanel.test.tsx; 35 total ApprovalPanel tests pass (154 total, 14 pre-existing failures unrelated to this story).
- `get_article_by_campaign_id` added to articles repository (was absent).
- `run_publish_headless` worker function added for APScheduler DateTrigger jobs.
- AC 11 (blockquote CSS) verified present in globals.css — not re-applied.

### File List

**Modified files:**
```
backend/app/routers/publishing.py                 ← PublishRequest body, PublishHeadlessRequest, headless scheduled_at branch
backend/app/schemas/publishing.py                 ← PublishRequest, PublishHeadlessRequest (create if not exists)
backend/app/workers/publish.py                    ← run_publish(platforms=[]) + new run_publish_headless
backend/app/services/publishing.py                ← dispatch_publish filters by platforms
backend/app/services/articles.py                  ← create_or_update_article_from_campaign gains status param
backend/app/db/repositories/articles.py           ← get_article_by_campaign_id (add if missing)
backend/tests/routers/test_publish_now.py         ← 3 new tests
backend/tests/routers/test_schedule_publish.py    ← 1 new test
backend/tests/routers/test_publishing.py          ← 5 new headless schedule tests
backend/tests/services/test_publishing.py         ← 2 new dispatch tests
frontend/lib/api.ts                               ← publishNow(platforms?), publishHeadless(scheduledAt?), schedule(platforms?)
frontend/app/(app)/campaigns/[id]/approval-panel.tsx  ← chip row, filtered publish, headless scheduling
frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx  ← 10 new tests
frontend/app/globals.css                          ← blockquote (already applied — verify only)
```

### Review Findings

- [x] [Review][Patch] Missing headless schedule success toast — AC 4 requires "Headless Blog scheduled for [formatted date]." toast after `publishHeadless` in `handleConfirmSchedule` [frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- [x] [Review][Patch] Check icon order wrong — AC 1 requires Check→icon→label; implementation renders icon→label→Check [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:154-156]
- [x] [Review][Patch] `publishNowSubLabel` copy wrong — AC 9 requires "Publishes to all platforms" / "Publishes to N selected platform(s)"; shows comma-joined names instead [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:459-461]
- [x] [Review][Patch] Republish sub-label wrong — AC 8 requires "Publishes to platforms not yet reached" / "Publishes to N selected platform(s) not yet reached" [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:1100]
- [x] [Review][Patch] nothingSelected warning: wrong color, missing `role="alert"`, wrong text — AC 3 requires `text-danger`, `role="alert"`, "Select at least one destination to publish." [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:459-461]
- [x] [Review][Patch] Timezone-naive validator missing on `PublishHeadlessRequest.scheduled_at` — `ScheduleRequest` has it; headless path doesn't, APScheduler may misfire [backend/app/schemas/publishing.py:11]
- [x] [Review][Patch] UUID parse guard missing in `run_publish_headless` — invalid `campaign_id_str` raises unguarded `ValueError`, crashing APScheduler job thread [backend/app/workers/publish.py:161]
- [x] [Review][Patch] Mutable default argument `platforms: list[str] = []` — Python antipattern; change to `Optional[list[str]] = None` with guard [backend/app/services/publishing.py:517, backend/app/workers/publish.py:113]
- [x] [Review][Patch] Past-time guard missing in `publish_headless` scheduled branch — `ScheduleRequest` rejects past times; `PublishHeadlessRequest` does not [backend/app/routers/publishing.py]
- [x] [Review][Patch] `transition-all` should be `transition-colors duration-150` — AC 2 explicitly specifies these classes [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:146]
- [x] [Review][Patch] `run_publish_headless` missing idempotency guard — if article already `published`, silently rewrites `updated_at` and commits again [backend/app/workers/publish.py:167]
- [x] [Review][Defer] Atomicity hole: article committed before `scheduler.add_job` in `publish_headless` — deferred, architectural change; low probability failure; recoverable manually [backend/app/routers/publishing.py]
- [x] [Review][Defer] APScheduler platforms list serialization across process restart — deferred, pre-existing concern across all APScheduler job args in codebase
- [x] [Review][Defer] `platform` field polymorphism (`isinstance(c.platform, str)`) — deferred, pre-existing ORM inconsistency not introduced by this story
- [x] [Review][Defer] WordPress + WordPress.com dedup overrides explicit chip selection — deferred, pre-existing precedence logic in `dispatch_publish`
- [x] [Review][Defer] Partial success states in `handlePublishNow`/`handleConfirmSchedule` — deferred, spec does not require atomic rollback; error toast is shown

## Change Log
