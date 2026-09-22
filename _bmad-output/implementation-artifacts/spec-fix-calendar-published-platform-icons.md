---
title: 'Calendar shows real published channels per post'
type: 'bugfix'
created: '2026-09-21'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '79bf3318a5fe30c50cb945afe1c4224b3b366435'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The content calendar paints a platform icon for every *currently-connected* account on every published post, so a post that actually went to only X + Threads appears to have been published to X, LinkedIn, Instagram, Facebook, Threads, and GitHub. The displayed channels are misleading; they reflect the client's connections, not where the post went.

**Approach:** Surface the true per-campaign published platforms from the backend (already computed from publish-job results) as a `published_platforms` field on the campaign list response, and render those icons in the calendar instead of the connected-platforms list.

## Boundaries & Constraints

**Always:** Derive published platforms from publish-job results (`error_details`), counting `success`, `already_published`, and `success_text_only` as published. Keep the existing `status === "published"` gate for showing icons (scheduled posts still show the clock, not icons). Use a single batched lookup for the whole campaign list (no per-campaign N+1 query), mirroring the existing `gen_job_map` pattern.

**Ask First:** None.

**Never:** Do not change publishing/dispatch behavior, the scheduler, or `run_publish` status logic (that is the separate scheduled-publish reliability fix). Do not alter the single-campaign `get_published_platforms_for_campaign` used by `dispatch_publish` skip logic. Do not add a DB migration or a new table — the data already exists in `jobs.error_details`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Published to subset | Complete publish job with `error_details` `{"x":"success","threads":"success","linkedin":"skipped"}` | `published_platforms` = `["threads","x"]` (sorted); calendar shows only X + Threads icons | N/A |
| Text-only fallback | `error_details` `{"x":"success_text_only"}` | `x` included in `published_platforms` | N/A |
| No publish job yet | Approved+scheduled campaign, no complete publish job | `published_platforms` = `[]`; calendar shows clock/time, no icons | N/A |
| Malformed error_details | `error_details` not valid JSON | Campaign contributes no platforms; other campaigns unaffected | Swallow parse error, continue |

</frozen-after-approval>

## Code Map

- `backend/app/db/repositories/jobs.py:108` -- `get_published_platforms_for_campaign` (single-campaign, reads `complete` publish/scheduled_publish jobs, unions `success`/`already_published` from `error_details`). Add a batched sibling here; do NOT change the existing one.
- `backend/app/routers/campaigns.py:151` -- `list_campaigns`; builds `campaign_ids`, `gen_job_map` (the N+1-avoidance pattern to mirror), and does `CampaignResponse.model_validate({**c.__dict__, ...})` at line 217.
- `backend/app/schemas/campaign.py:56` -- `CampaignResponse`; add the new field here (inherited by `CampaignDetailResponse`).
- `frontend/components/calendar/ContentCalendar.tsx:120-123` -- icon render maps over `connectedPlatforms` (the bug); `usePlatformConnections`/`connectedPlatforms` (lines 8, 155-163, 319) exist ONLY to feed this and can be removed.
- `frontend/lib/types.ts:200` -- `Campaign` interface; add the field.
- `backend/tests/test_campaigns_router.py` -- list_campaigns tests.
- `frontend/__tests__/components/calendar/ContentCalendar.test.tsx` -- calendar render tests.
- `frontend/components/ui/PlatformIcon.tsx` -- reference only; already handles `x`, `linkedin`, `instagram`, `facebook_page`, `threads`, `wordpress`, `wordpress-com`, `webflow`, `github_pages`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/db/repositories/jobs.py` -- add `get_published_platforms_for_campaigns(session, campaign_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[str]]` returning a per-campaign union of platforms whose `error_details` status is in `{"success","already_published","success_text_only"}` across `complete` publish/scheduled_publish jobs; return `{}` for empty input; guard JSON parse errors per job.
- [x] `backend/app/schemas/campaign.py` -- add `published_platforms: list[str] = []` to `CampaignResponse`.
- [x] `backend/app/routers/campaigns.py` -- in `list_campaigns`, after building `campaign_ids`, call the batched lookup once and pass `"published_platforms": sorted(pub_map.get(c.id, set()))` into each `CampaignResponse.model_validate(...)`.
- [x] `frontend/lib/types.ts` -- add `published_platforms?: string[];` to `Campaign`.
- [x] `frontend/components/calendar/ContentCalendar.tsx` -- render icons from `campaign.published_platforms ?? []` instead of `connectedPlatforms`; drop the now-unused `usePlatformConnections` import, `connections`/`connectedPlatforms` memo, and the `connectedPlatforms` prop on `CalendarEntry`.
- [x] `backend/tests/test_campaigns_router.py` -- test the I/O Matrix rows: subset publish, `success_text_only`, no-job (`[]`), malformed `error_details`.
- [x] `frontend/__tests__/components/calendar/ContentCalendar.test.tsx` -- assert a published campaign renders exactly its `published_platforms` icons and an approved/scheduled campaign renders the time, not icons.

**Acceptance Criteria:**
- Given a published campaign that reached only X and Threads, when the calendar loads, then only the X and Threads icons render on that entry regardless of which platforms the client currently has connected.
- Given a scheduled (approved) campaign, when the calendar loads, then its entry shows the scheduled time and no platform icons.
- Given the campaign list endpoint, when it returns N campaigns, then published platforms are resolved in a single batched query (no per-campaign query).

## Verification

**Commands:**
- `cd backend && pytest tests/test_campaigns_router.py -q` -- expected: pass, including the new published_platforms cases.
- `cd frontend && npx vitest run __tests__/components/calendar/ContentCalendar.test.tsx` -- expected: pass.
- `cd frontend && npx tsc --noEmit` -- expected: no type errors from the new `Campaign.published_platforms` field.

## Suggested Review Order

**Backend: derive true published channels**

- Entry point — list endpoint wires the batched lookup into each response row.
  [`campaigns.py:203`](../../backend/app/routers/campaigns.py#L203)
- The serialized field: real per-post platforms, sorted for stable order.
  [`campaigns.py:226`](../../backend/app/routers/campaigns.py#L226)
- The batched query itself — single query, complete publish jobs, counts the three success statuses, guards malformed JSON.
  [`jobs.py:139`](../../backend/app/db/repositories/jobs.py#L139)
- Review-fix: detail endpoint populated too, so it stays consistent with the list (no silent `[]`).
  [`campaigns.py:260`](../../backend/app/routers/campaigns.py#L260)
- Schema field exposed to clients.
  [`campaign.py:63`](../../backend/app/schemas/campaign.py#L63)

**Frontend: bind the calendar to real channels**

- The fix — published entries now map over the post's actual platforms, not connected accounts.
  [`ContentCalendar.tsx:119`](../../frontend/components/calendar/ContentCalendar.tsx#L119)
- Source of that list (and the unused connections fetch was removed).
  [`ContentCalendar.tsx:76`](../../frontend/components/calendar/ContentCalendar.tsx#L76)
- Type contract for the new field.
  [`types.ts:205`](../../frontend/lib/types.ts#L205)

**Tests**

- Router wiring, `success_text_only`, empty, batched/malformed, and the WHERE-clause guard.
  [`test_campaigns_router.py:1712`](../../backend/tests/test_campaigns_router.py#L1712)
- Calendar renders exactly the published platforms; scheduled entries show time, no icons.
  [`ContentCalendar.test.tsx:204`](../../frontend/__tests__/components/calendar/ContentCalendar.test.tsx#L204)
