# Story 4.6: Post-Approval Content Editing and Scheduling UX

---
baseline_commit: 0a2d1df5c1a210cdeffc27629c9533c22c7df97b
---

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **content creator reviewing a campaign**,
I want **to edit an approved or scheduled campaign's blog and social content, reschedule a scheduled post instead of only cancelling it, pick a send time from sensible presets, and write in text boxes that grow with my content**,
so that **I can correct or improve a post right up until it goes out, without cancelling and starting over, and without fighting a cramped scrolling box**.

## Context and Problem

Today the approval gate locks everything the moment a campaign leaves `pending_approval`:

- **No editing after approval.** `ApprovalGateClient` renders the editable `BlogEditor` only when the campaign is `pending_approval`; otherwise it shows the read-only `BlogHtmlRenderer`. `SocialPostEditors` is passed `readOnly={!isPending}`. The backend enforces the same rule: `patch_campaign` rejects any edit unless status is `pending_approval` (`INVALID_STATUS_FOR_EDIT`). So once you approve or schedule, the only way to change a word is to reject/regenerate or Re-voice into a brand new draft.
- **Scheduled posts can only be cancelled.** The scheduled state in `approval-panel.tsx` shows a single "Cancel schedule" link. To move the time you must cancel and re-schedule from scratch.
- **The date picker is the raw browser control.** The schedule picker is a bare `<input type="datetime-local">` with no presets and no Paper Style treatment.
- **Social text boxes force internal scrolling.** `SocialPostEditors` uses fixed-`rows` textareas with `resize-none`. A LinkedIn post (up to 1500 chars) sits in a `rows={8}` box, so long content scrolls inside a small locked area. This is the "limit height, bad UX, have to scroll" complaint and it is not acceptable for an editing surface.

This story removes those locks for the safe states (`approved` and `scheduled-but-not-yet-sent`), adds reschedule, replaces the generic picker with presets, and makes the social textareas grow with their content. **Published campaigns stay read-only** (the content is already live on external platforms and cannot be un-sent; editing there is out of scope and handled by the existing article editor / Re-voice paths).

## Acceptance Criteria

1. **Edit an approved campaign's content.**
   - Given a campaign with status `approved` (not article-backed, not published),
   - When I open its review page,
   - Then I see an "Edit" affordance that switches the blog and social sections from read-only into the existing editors, and saving persists via `PATCH /campaigns/{id}`.

2. **Edit a scheduled campaign without changing its send time.**
   - Given a campaign that is `approved` with a future `scheduled_at`,
   - When I edit and save its blog or social content,
   - Then the content is updated and `scheduled_at` is unchanged (the scheduled job still fires at the original time and publishes the updated content).

3. **Backend allows content edits in approved/scheduled state only.**
   - Given a `PATCH /campaigns/{id}` with content fields,
   - When the campaign status is `approved` (with or without `scheduled_at`),
   - Then the patch succeeds; and when the status is `published`, `rejected`, or `failed`, the patch is rejected with `INVALID_STATUS_FOR_EDIT`.

4. **Published campaigns remain read-only.**
   - Given a `published` campaign,
   - When I open its review page,
   - Then no "Edit" affordance is shown for blog/social content and the existing published/republish UI is unchanged.

5. **Reschedule a scheduled post.**
   - Given a scheduled campaign,
   - When I choose "Reschedule" and confirm a new future date/time,
   - Then the existing scheduled job is moved to the new time (no duplicate job is created), `scheduled_at` is updated, and the scheduled bar reflects the new time. "Cancel schedule" remains available as a separate action.

6. **Reschedule rejects invalid times.**
   - Given the reschedule picker,
   - When the chosen time is in the past,
   - Then the confirm action is disabled and an inline message states the time must be in the future (mirrors the existing schedule validation).

7. **Date/time presets.**
   - Given the schedule or reschedule picker,
   - When it opens,
   - Then I see quick presets computed in my local timezone (for example "Tomorrow 9 AM", "Tomorrow 1 PM", "This weekend", "Next Monday 9 AM") plus a "Custom" option that reveals the datetime field; selecting a preset fills the time and shows the resolved "Will publish: ..." line and the timezone note.

8. **Auto-growing social textareas.**
   - Given any social post editor (X, LinkedIn, Instagram, Facebook, Threads),
   - When content exceeds the default height,
   - Then the textarea grows to fit its content up to a generous maximum (no internal scrollbar for normal-length posts), starting from a sensible minimum height. Character counters and danger thresholds are unchanged.

9. **No regressions to publish/approve/reject/GitHub/headless flows.**
   - Given the approval panel in `pending_approval`, `approved` (unscheduled), `published`, and `failed` states,
   - When I use existing actions (approve, reject, publish now, schedule, GitHub publish, republish, retry),
   - Then they behave exactly as before.

10. **Copy constraint.**
   - All new user-facing strings avoid the em-dash character and the double-hyphen sequence, per project copy rules.

## Tasks / Subtasks

- [x] **Task 1: Backend — allow content edits while approved/scheduled** (AC: 3, 2, 4)
  - [x] In `backend/app/routers/campaigns.py` `patch_campaign`, change the status guard from `!= "pending_approval"` to allow `pending_approval` and `approved` (scheduled campaigns keep status `approved` with a non-null `scheduled_at`, so they are covered). Continue to reject `published`, `rejected`, `failed` with `INVALID_STATUS_FOR_EDIT`.
  - [x] Confirm patch only touches `_PATCHABLE_FIELDS` (content fields) and never `scheduled_at` or `status`.
  - [x] Tests in `backend/tests/routers/test_campaigns.py`: patch succeeds when `approved`; patch succeeds when `approved` + future `scheduled_at` and leaves `scheduled_at` untouched; patch rejected when `published`/`rejected`/`failed`.

- [x] **Task 2: Backend — reschedule endpoint** (AC: 5, 6)
  - [x] In `backend/app/routers/publishing.py`, add reschedule support. Preferred: a `PUT /campaigns/{campaign_id}/publish/schedule` (or relax the existing `POST` when `scheduled_at is not None`) that: validates ownership and future time (reuse existing checks), finds the existing scheduled job via `get_scheduled_job`, calls `scheduler.remove_job` then `scheduler.add_job` (or `scheduler.reschedule_job`) at the new time, updates the job row `scheduled_at` and `update_campaign_scheduled_at`, and commits. Do NOT create a second job. Preserve the existing `platforms` filter on the job args.
  - [x] Keep the current `POST` "ALREADY_SCHEDULED" behavior intact if you add a separate reschedule route.
  - [x] Tests in `backend/tests/routers/test_publishing.py`: reschedule moves the job time and updates `scheduled_at`; reschedule to a past time returns `SCHEDULED_TIME_IN_PAST`; reschedule on a non-scheduled campaign returns the appropriate 400/404; no duplicate job rows after reschedule.

- [x] **Task 3: Frontend API client** (AC: 5)
  - [x] In `frontend/lib/api.ts`, add `campaignsApi.reschedule(id, scheduledAt, platforms?)` calling the new endpoint. Keep existing `schedule` and `cancelSchedule`.

- [x] **Task 4: Frontend — edit toggle in the approval gate** (AC: 1, 2, 4, 9)
  - [x] In `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`, introduce an `isEditing` state, allowed only when `displayStatus === "approved"` and `campaign.status !== "published"`. For article-backed campaigns (`campaign.article_id`) keep the existing "Content edits go here / Edit article" banner and do NOT enable inline blog editing.
  - [x] Render `BlogEditor` when `(isPending || isEditing) && !campaign.article_id`, else `BlogHtmlRenderer`.
  - [x] Pass `readOnly={!isPending && !isEditing}` to `SocialPostEditors`.
  - [x] Add an "Edit" / "Done editing" toggle button (Paper Style: ink border, hard shadow on primary, `rounded-none`, mono label) placed near the header or section headers. Show it only for editable states.
  - [x] Ensure the existing on-approve dirty-patch path in `approval-panel.tsx` (`blogEditorRef`/`socialEditorsRef`) is unaffected; the new edit path saves via the editors' own Save actions / `PATCH`.

- [x] **Task 5: Frontend — reschedule action + shared picker** (AC: 5, 6, 7)
  - [x] Extract the schedule picker markup in `approval-panel.tsx` into a small reusable block/component that takes an initial value, a confirm handler, and a confirm label, so it serves both "Schedule" and "Reschedule".
  - [x] In the scheduled state (currently only "Cancel schedule"), add a primary "Reschedule" button that opens the picker prefilled with the current `scheduled_at` (converted to the `datetime-local` local string), and on confirm calls `campaignsApi.reschedule`. Keep "Cancel schedule".
  - [x] Add preset chips above the datetime field (AC 7). Compute preset Date values in the user's local timezone; format into the `datetime-local` value string. Selected chip uses the highlighter fill treatment already used elsewhere (`bg-highlighter border-ink shadow-[2px_2px_0px_#111111]`). Include a "Custom" chip that reveals the raw datetime input. Keep the "Will publish: ..." resolved line and the "Schedules in {timezone}" note.

- [x] **Task 6: Frontend — auto-growing social textareas** (AC: 8)
  - [x] In `frontend/components/campaigns/SocialPostEditors.tsx`, replace fixed `rows` + `resize-none` behavior with auto-grow. Prefer CSS `field-sizing: content` with a `min-h`/`max-h` (Tailwind arbitrary values) and a small JS height-recalculation fallback on input for browsers without `field-sizing`. Keep `resize-none` visually but let height track content up to `max-h`, then allow scroll only past that ceiling.
  - [x] Preserve counters, danger thresholds, `disabled` (readOnly) styling, and the null-to-value sync effects.

- [x] **Task 7: Verify and regression-check** (AC: 9, 10)
  - [x] Manually exercise: pending edit+approve, approved edit+save, scheduled edit+save (time unchanged), reschedule, cancel, publish now, republish, GitHub publish, headless. Confirm published stays read-only.
  - [x] Grep new strings for `—` and `--`; restructure any that appear.
  - [x] Update/extend frontend tests under `frontend/__tests__/app/campaigns/` (`ApprovalGateClient.test.tsx`, `ApprovalPanel.test.tsx`) for the edit toggle, reschedule button presence, and preset selection.

## Dev Notes

### Current state of files being modified (read before editing)

- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`
  - `isPending = displayStatus === "pending_approval" && campaign.status === "pending_approval"`.
  - Blog: renders `<BlogEditor readOnly={false} />` only when `(isPending && !campaign.article_id)`; otherwise `<BlogHtmlRenderer />`. Article-backed campaigns show a banner linking to `/articles/{id}` ("Content edits go here").
  - Social: `<SocialPostEditors readOnly={!isPending} ... />`.
  - Must preserve: `metaContext` is passed only when `isPending` today; when enabling edit mode, gate `metaContext` on `(isPending || isEditing)` so platform-specific sections (Instagram/Facebook/Threads) still appear while editing.

- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
  - Post-approved branch (`effectiveStatus === "approved"`): if `campaign.scheduled_at != null` it renders a fixed bottom bar with the formatted scheduled time and only a "Cancel schedule" link (`handleCancelSchedule`). Otherwise it renders the full publish/schedule/GitHub UI.
  - Schedule picker: `showSchedulePicker` toggles a block with a raw `<input type="datetime-local" value={scheduledAt} .../>`, a "Will publish:" line, timezone note, past-time validation (`isPastTime`), and Confirm/Cancel. `handleConfirmSchedule` posts via `campaignsApi.schedule` / `publishHeadless` then routes to `/calendar`.
  - Reuse the existing `isPastTime`, `userTimezone`, and formatting logic when building the shared picker.

- `frontend/components/campaigns/SocialPostEditors.tsx`
  - Five textareas (X `rows={4}`, LinkedIn `rows={8}`, Instagram `rows={6}`, Facebook `rows={5}`, Threads `rows={4}`), all sharing `textareaBase` which includes `resize-none`. Counters and danger thresholds per platform. Has a `getCurrentValues` imperative handle and a local Save button that calls `campaignsApi.patch`. Null-to-value sync effects must be preserved.

- `backend/app/routers/campaigns.py`
  - `patch_campaign` (line ~263): guards `if campaign.status != "pending_approval": raise 400 INVALID_STATUS_FOR_EDIT`. Only `_PATCHABLE_FIELDS` are applied. This is the single backend gate to relax.

- `backend/app/routers/publishing.py`
  - `POST /campaigns/{id}/publish/schedule` (line 1414): requires `status == "approved"` and `scheduled_at is None` (else `ALREADY_SCHEDULED`); validates future time; creates a `scheduled_publish` job, sets `job.scheduled_at`, `update_campaign_scheduled_at`, registers `scheduler.add_job(run_publish, DateTrigger, args=[job_id, campaign_id, platforms])` with `replace_existing=True`, commits.
  - `DELETE /campaigns/{id}/publish/schedule` (line 1487): finds the scheduled job via `get_scheduled_job`, `scheduler.remove_job`, deletes the job row, `update_campaign_scheduled_at(None)`, returns status "approved".
  - Reschedule should mirror these primitives: locate existing job, move it, update `scheduled_at`. `scheduler` supports `reschedule_job(job_id, trigger=DateTrigger(...))` or remove+add.

### Design guardrails (Paper Style)

Tokens in use: `ink` (#111111), `paper`, `graphite` (#555555), `border` (#E5E5E5), `highlighter`/`highlight` (yellow), `danger`. Buttons: primary = `bg-ink text-paper shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink`; secondary = `border border-ink hover:bg-ink hover:text-white`. Selected chips = `bg-highlighter border-ink shadow-[2px_2px_0px_#111111]`. Everything `rounded-none`. Labels are `font-mono uppercase tracking` micro-labels. Always include `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`. Minimum touch target 44px on interactive controls (see `RevoiceButton` `min-h-[44px]` precedent).

### Semantics and safety

- Editing content while `scheduled` must never touch `scheduled_at`. Content patch and schedule/reschedule are independent operations.
- Do not silently revert status on edit. An approved campaign stays approved; a scheduled campaign stays scheduled.
- Published is deliberately excluded. If a stakeholder later wants "edit after publish", that is a separate story following the `12-3-edit-after-publish-revision-ui` article pattern (revisions + optional re-publish), not part of this one.

### Testing standards

- Backend: pytest, async httpx client, tests colocated under `backend/tests/routers/`. Follow existing patterns in `test_campaigns.py` and `test_publishing.py` (ownership 404s, status-transition 400s, scheduler interaction mocked).
- Frontend: Jest + Testing Library under `frontend/__tests__/`. Existing `ApprovalGateClient.test.tsx` and `ApprovalPanel.test.tsx` are the touchpoints.

### Project Structure Notes

- No new columns or migrations required. `scheduled_at` already exists on campaigns; content fields already patchable. This is a status-guard relaxation plus one new reschedule route plus frontend UX.
- Keep the reschedule route co-located with the other schedule routes in `publishing.py`.

### References

- Approval gate editability: `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` (blog editor gate ~line 171-190, `readOnly={!isPending}` ~line 217).
- Scheduled bar + schedule picker: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` (scheduled state ~line 654-685; schedule picker ~line 841-901; `handleConfirmSchedule` ~line 504; `handleCancelSchedule` ~line 557).
- Social textareas: `frontend/components/campaigns/SocialPostEditors.tsx` (`textareaBase` ~line 140, five textareas ~line 164-346).
- Backend patch gate: `backend/app/routers/campaigns.py` `patch_campaign` (~line 263-303).
- Backend schedule/cancel: `backend/app/routers/publishing.py` (~line 1414-1525).
- API client: `frontend/lib/api.ts` (`schedule`/`cancelSchedule` ~line 148-156).
- Copy rule: no em-dash or double-hyphen in generated copy or UI strings (project memory: no-double-dash-in-copy).

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (2026-08-17)

### Debug Log References

- Pre-existing backend failure: `test_list_campaigns_returns_items_and_total` fails with `StopAsyncIteration`; confirmed pre-existing by stashing changes and re-running.
- Pre-existing frontend failures in `ApprovalPanel.test.tsx`: 3 tests in "publish now" and "destination chips" describe blocks fail because `publishNow` now receives a platforms array arg but tests still assert `toHaveBeenCalledWith("campaign-123")`. Confirmed pre-existing via stash.
- Pre-existing frontend failures: `useJobStatus`, `BlogEditor`, `TrialBanner`, `TrialNudgeToast`, `ContentCalendar`, `PlatformConnectionCard`, `RetryPanel`, `meta.test.ts` — all confirmed pre-existing.
- `SchedulePicker` preset-first UI broke 4 existing `ApprovalPanel.test.tsx` schedule-picker tests; fixed by updating tests to use preset chips and clicking "Custom" before accessing the datetime input.

### Completion Notes List

- Backend guard changed from `!= "pending_approval"` to `not in ("pending_approval", "approved")` in `patch_campaign`. Scheduled campaigns have `status == "approved"` with non-null `scheduled_at`, so they are covered without any additional guard.
- `PUT /campaigns/{id}/publish/schedule` endpoint uses `scheduler.reschedule_job(job_id, trigger=DateTrigger(...))` to avoid duplicate job rows; falls back to `scheduler.add_job` only if `JobLookupError` (e.g., job expired between request and reschedule).
- `SchedulePicker` extracted as a file-local component in `approval-panel.tsx`, serving both "Schedule" and "Reschedule" flows. Presets: Tomorrow 9 AM, Tomorrow 1 PM, This weekend (next Saturday), Next Monday 9 AM; "Custom" chip reveals the `datetime-local` input.
- `field-sizing: content` CSS handles auto-grow natively in supported browsers; `useCallback autoResize` JS fallback fires on `onInput` for others. `min-h-[6rem]` / `max-h-[32rem]` bounds set via Tailwind arbitrary values.
- Edit toggle shows only for `approved` campaigns where `campaign.status !== "published"`. Article-backed campaigns show the existing "Content edits go here" banner with a link to `/articles/{id}` and do NOT get inline blog editing.

### File List

- `backend/app/routers/campaigns.py`
- `backend/tests/routers/test_campaigns.py`
- `backend/app/routers/publishing.py`
- `backend/tests/routers/test_schedule_publish.py`
- `frontend/lib/api.ts`
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
- `frontend/components/campaigns/SocialPostEditors.tsx`
- `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx`
- `frontend/__tests__/app/campaigns/ApprovalGateClient.test.tsx`

### Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-08-17 | Implemented all 7 tasks for story 4-6 | claude-sonnet-4-6 |
