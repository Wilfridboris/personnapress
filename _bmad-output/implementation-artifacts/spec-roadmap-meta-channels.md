---
title: 'Add Meta (Facebook Page + Instagram) channels to Plan My Week roadmap'
type: 'feature'
created: '2026-09-20'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'cf1f6ecf66680439b0891b36f8ca7e4eca34284e'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Plan My Week roadmap generator (`/roadmap/new`) only offers LinkedIn, X, and Blog. Facebook Page and Instagram are fully supported everywhere else in the app (native content generation via `generate_social_only`, production-ready Meta publishing), so they are missing only from roadmap planning.

**Approach:** Wire Facebook Page and Instagram through the existing roadmap pipeline as first-class channels: add per-channel counts to config/API, generate their posts in the roadmap loop, extend the one-shot LLM week planner to author angles+hooks for all four social channels, classify/schedule Meta campaigns, and render+edit them in the review UI. No new DB columns (JSONB config + existing `facebook_post` / `instagram_caption` campaign columns).

Critical: Instagram publishing REQUIRES an image (`meta.py:126` `image_url` is mandatory; `publishing.py:697,908` silently skip Instagram when `image_url` is empty), while Facebook publishes fine as a text post. So this feature must prioritize Instagram campaigns for image assignment and warn the user when Instagram is enabled but images are off or under quota, otherwise planned Instagram posts silently never publish.

## Boundaries & Constraints

**Always:**
- Reuse existing `generate_social_only(platform="facebook_page"|"instagram")` and existing Meta publishing untouched. Facebook uses platform id `facebook_page`; Instagram uses `instagram`.
- Mirror the exact LinkedIn/X pattern for toggles, counts, connection-gating, validation, generation loops, scheduling, and review rendering.
- Keep count fields `ge=0, le=14` on the backend, matching existing request models.
- Because Instagram cannot publish without an image, prioritize Instagram roadmap campaigns first for image assignment, and gate/warn in the UI when Instagram is enabled without enough image quota.
- All frontend/UI work in this spec must be done with the `/web-uiux-architect` skill (Paper Style design system, no emojis, icons only from the installed library; `PlatformIcon` already covers `instagram`/`facebook_page`).
- No em-dash or double-dash in any user-facing copy, prompt text, or generated hooks.

**Ask First:**
- Any DB schema/migration (should not be needed — if one seems required, stop).
- Adding a channel beyond Facebook Page + Instagram (Threads is explicitly out).

**Never:**
- Do not add Threads. Do not touch the Meta publishing integration or `dispatch_publish_*`. Do not change how blog generation works.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| FB+IG counts set | `facebook_count=2, instagram_count=3` in create request | roadmap generates 2 Facebook-only + 3 Instagram-only campaigns with distinct planned angles | N/A |
| Channel not connected | Facebook not connected for active client | Facebook toggle disabled + "Connect Facebook" link; toggle cannot be enabled | N/A |
| All channels zero | `blog=false`, all counts 0 | request rejected by validator | 422 "At least one post type must be enabled" |
| Planner LLM fails | `generate_week_plan` raises | fallback angle rotation supplies facebook/instagram slots; generation still completes | logged + Sentry, non-fatal |
| Meta-only campaign in review | campaign has only `facebook_post` | review card labeled "Facebook", shows/edit `facebook_post`; Instagram analogous | N/A |
| Instagram + image quota | `instagram_count=3`, image quota=1 | Instagram campaigns get images first (1 of 3); UI warns remaining Instagram posts need an image to publish | N/A |
| Instagram, images off | `instagram_count>0`, `generate_images=false` | UI warns Instagram posts will not publish without an image before submit | N/A |

</frozen-after-approval>

## Code Map

Backend:
- `backend/app/routers/roadmaps.py` -- `RoadmapCreateRequest` (L60-74: add 2 counts + validator), `create_roadmap` (L196-201: config dict), `CampaignSummary` (L82-92: add `facebook_post`/`instagram_caption`), `_platform_hint` (L105-110), `get_roadmap_status` mapping (L249-262).
- `backend/app/routers/clients.py` -- `RoadmapConfigRequest` (L476-480) + `patch_roadmap_config` dict (L503-508).
- `backend/app/services/roadmap.py` -- `generate_roadmap`: read counts (L65-66), `total_posts` (L69), `plan_week_angles` call (L82-84), add FB + IG generation loops after LinkedIn loop (after L163, mirror L139-163), image-assignment step (L165-169) must prioritize Instagram campaigns first (they cannot publish without an image), `_campaign_platform` (L211-216), `_PLATFORM_ORDER` (L207) + base-hour handling in `distribute_schedule` (L262-269).
- `backend/app/services/publishing.py` -- READ ONLY, do not change. Confirms Instagram is skipped without `image_url` (L697-699, L908-909) and Facebook publishes as text without image (L715-730). This is why Instagram image priority + UI warning are required.
- `frontend/components/ui/PlatformIcon.tsx` -- READ ONLY. Already renders `instagram` + `facebook_page` icons and brand colors; reuse, do not modify.
- `backend/app/services/generation.py` -- `plan_week_angles` (L339-378): add counts to signature, planner call, fallback dict. `generate_social_only` (L263-336) already supports `facebook_page`/`instagram` — no change.
- `backend/app/services/angles.py` -- add `_FACEBOOK_ORDER`, `_INSTAGRAM_ORDER`, register both in `_PLATFORM_ORDER` (L46-49). Draw only from existing `ANGLE_LABELS` codes.
- `backend/app/integrations/generation_prompts.py` -- `_WEEK_PLAN_PROMPT` (L1128-1173): add FB + IG slot counts, allowed angles, output lists, count assertions (new placeholders `facebook_count`, `instagram_count`, `facebook_angles`, `instagram_angles`).
- `backend/app/integrations/anthropic_client.py` -- `generate_week_plan` (L684-732): signature + `.format()` + validate/repair `facebook`/`instagram`. `_next_fallback` (L766) / `_pad_fallback` (L774) hardcode linkedin-vs-x pool: generalize to select pool by platform.
- `backend/app/integrations/gemini.py` -- `generate_week_plan` (L868-921) + its own repair/fallback helpers: apply the identical changes as `anthropic_client.py`. (Active client chosen by `settings.LLM_PROVIDER`; both must work.)

Frontend:
- `frontend/lib/types.ts` -- `RoadmapConfig` (L38-43) add 2 counts; `RoadmapCampaignSummary` (L68+) add `facebook_post`/`instagram_caption: string | null`.
- `frontend/lib/api.ts` -- `roadmapsApi.create` param type (L318-325) add 2 counts.
- `frontend/components/roadmap/PlanMyWeekClient.tsx` -- `PlanConfig`/`DEFAULT_CONFIG` (L18-34), connection checks (L146-152), reset effect (L154-164), config-populate effect (L170-182), `totalPosts` (L213-216), `handleSubmit` payload (L240-247), and two new Toggle+Spinner blocks (mirror X block L353-380) with Connect links. `Platform` type (L17) already has `instagram`/`facebook_page`.
- `frontend/components/roadmap/PostCard.tsx` -- `getPlatformInfo` (L17-30): add `facebook_page` (label "Facebook", limit 63206, `facebook_post`) and `instagram` (label "Instagram", limit 2200, `instagram_caption`) branches.
- `frontend/components/roadmap/PostEditPanel.tsx` -- `getPostFieldKey` (L54-57) + `handleSave` (L62-72): add facebook/instagram field mapping.

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/services/angles.py` -- add `_FACEBOOK_ORDER` + `_INSTAGRAM_ORDER` (subset/reorder of existing angle codes suited to each network) and register in `_PLATFORM_ORDER` -- enables `fallback_angles` + planner pools for Meta.
- [x] `backend/app/integrations/generation_prompts.py` -- extend `_WEEK_PLAN_PROMPT` with Facebook + Instagram slot counts, allowed-angle lists, output arrays, and exact-count assertions -- one planner call covers all four social channels.
- [x] `backend/app/integrations/anthropic_client.py` -- add `facebook_count`/`instagram_count` to `generate_week_plan`, format new placeholders, validate + `_repair_plan_entries` for `facebook`/`instagram`, and make `_next_fallback`/`_pad_fallback` pick the pool by platform -- planner returns Meta slots.
- [x] `backend/app/integrations/gemini.py` -- apply the identical `generate_week_plan` + helper changes -- parity across LLM providers.
- [x] `backend/app/services/generation.py` -- extend `plan_week_angles` signature, planner call, and fallback dict to include `facebook`/`instagram` -- roadmap always gets Meta angle slots.
- [x] `backend/app/services/roadmap.py` -- read the two counts, add to `total_posts`, pass to `plan_week_angles`, add Facebook-only + Instagram-only generation loops (plan keys `facebook`/`instagram`; call `generate_social_only` with platform `facebook_page`/`instagram`), reorder image assignment so Instagram campaigns receive images first, extend `_campaign_platform`, `_PLATFORM_ORDER`, and give each Meta lane a base hour in `distribute_schedule` (e.g. Instagram 11:00, Facebook 14:00) -- Meta posts generated, classified, scheduled, and Instagram gets its required image.
- [x] `backend/app/routers/roadmaps.py` -- add `facebook_count`/`instagram_count` to `RoadmapCreateRequest` (+ validator), persist in `create_roadmap` config dict, add `facebook_post`/`instagram_caption` to `CampaignSummary`, detect them in `_platform_hint`, and pass them in `get_roadmap_status` -- API + review data flow.
- [x] `backend/app/routers/clients.py` -- add the two counts to `RoadmapConfigRequest` and persist in `patch_roadmap_config` -- saved plan remembers Meta counts.
- [x] `frontend/lib/types.ts` + `frontend/lib/api.ts` -- add the two counts to `RoadmapConfig` and `roadmapsApi.create`, and `facebook_post`/`instagram_caption` to `RoadmapCampaignSummary` -- typed contract.
- [x] `frontend/components/roadmap/PlanMyWeekClient.tsx` -- (use `/web-uiux-architect`) add Facebook + Instagram toggles/spinners, connection gating (`facebook_page`/`instagram`), config load/reset, `totalPosts`, submit payload, and an Instagram-needs-image warning shown when `instagram_count>0` and (images off or remaining quota < instagram_count) -- users choose Meta channels and are warned before scheduling unpublishable Instagram posts.
- [x] `frontend/components/roadmap/PostCard.tsx` + `PostEditPanel.tsx` -- (use `/web-uiux-architect`) render and edit Facebook/Instagram roadmap cards (label + `PlatformIcon` + char limits), and show a subtle "needs image to publish" badge on Instagram cards lacking `image_url` -- review parity with LinkedIn/X plus publish-safety cue.

**Acceptance Criteria:**
- Given a client with Facebook Page + Instagram connected, when I enable both with counts and submit Plan My Week, then the roadmap review shows that many Facebook and Instagram cards with distinct angles, each editable and schedulable.
- Given a channel is not connected, when I open the plan panel, then that channel's toggle is disabled with a Connect link and cannot be turned on.
- Given `blog=false` and all four social counts are 0, when I submit, then the request is rejected (422) and the button stays disabled client-side.
- Given the week planner LLM fails, when the roadmap generates, then Facebook/Instagram slots still receive fallback angles and generation completes successfully.
- Given a previously saved `roadmap_config` with Meta counts, when I reopen Plan My Week, then Facebook/Instagram toggles and counts are restored.
- Given Instagram is enabled with images off (or quota below the Instagram count), when I view the plan, then a clear warning states Instagram posts need an image, and when generation runs with quota available, then Instagram campaigns are the first to receive generated images.

## Design Notes

Angle pools draw only from existing `ANGLE_LABELS` codes (no new taxonomy). Suggested Instagram order favors visual/story angles (`personal_story`, `how_to`, `quick_tip`, `lesson_learned`, `engagement_q`, `data_proof`); Facebook favors community/discussion angles (`engagement_q`, `personal_story`, `how_to`, `contrarian`, `myth_bust`, `quick_tip`). The planner already de-duplicates within each platform list.

Generation loop shape (per Meta channel), mirroring the LinkedIn loop:
```python
fb_plan = plan.get("facebook", [])
for i in range(facebook_count):
    slot = fb_plan[i] if i < len(fb_plan) else {}
    ... create Campaign(roadmap_id=...) ; flush/commit ...
    await generation_service.generate_social_only(
        roadmap.brain_dump, bvp, "facebook_page", fb_campaign.id, db,
        angle=slot.get("angle"), hook=slot.get("hook"), voice_samples=voice_samples,
    )
    campaign_ids.append(fb_campaign.id); title_hints.append(f"Roadmap Facebook post {i+1}")
```

Char limits for review cards: Facebook 63206, Instagram 2200 (already in `frontend/lib/platformLimits.ts`). UI count max: 7 per Meta channel (feed cadence) even though backend accepts up to 14.

Image priority: in `generate_roadmap`, build the ordered list fed to the `campaign_ids[:allowed_images]` image loop so Instagram campaign ids come first, then blog/other, then Facebook. Instagram is the only channel that cannot publish without an image, so it must win scarce image quota. Keep `title_hints` aligned with whatever order you assign.

UI: all Plan/Review UI changes go through `/web-uiux-architect` to stay in the Paper Style system. Reuse `PlatformIcon` (`instagram`, `facebook_page`) and the existing Toggle/Spinner primitives; do not introduce emojis or new icon sources. The Instagram-needs-image warning should read plainly, e.g. "Instagram posts need an image to publish. Turn on Generate images or they will be skipped." (no dashes).

## Verification

**Commands:**
- `cd frontend && npm run lint && npx tsc --noEmit` -- expected: no new errors in touched files.
- `cd frontend && npm run build` -- expected: builds clean.
- `cd backend && python -c "import app.services.roadmap, app.services.generation, app.integrations.anthropic_client, app.integrations.gemini, app.routers.roadmaps, app.routers.clients"` -- expected: imports without error.
- `cd backend && pytest -q` (if a roadmap/generation test suite exists) -- expected: green; add/extend a test asserting `plan_week_angles` returns `facebook`/`instagram` keys and the create validator counts Meta.

**Manual checks:**
- With a Meta-connected client, run Plan My Week with FB=1, IG=1, blog off, LinkedIn/X off; confirm review shows one Facebook and one Instagram card with real captions, editable, and each lands on a scheduled slot after approve.

## Suggested Review Order

**Generation orchestration (entry point)**

- Reads FB/IG counts, then the two new per-channel generation loops
  [`roadmap.py:67`](../../backend/app/services/roadmap.py#L67)
- Facebook-only and Instagram-only slot loops mirror the LinkedIn loop
  [`roadmap.py:177`](../../backend/app/services/roadmap.py#L177)
- Instagram wins scarce image quota (it cannot publish without an image)
  [`roadmap.py:267`](../../backend/app/services/roadmap.py#L267)

**Scheduling**

- Per-lane base hours (Instagram 11:00, Facebook 14:00) and classifier
  [`roadmap.py:303`](../../backend/app/services/roadmap.py#L303)

**Week-plan LLM (all four channels)**

- Planner signature + validate/repair FB/IG + `_plan_pool` by platform
  [`anthropic_client.py:684`](../../backend/app/integrations/anthropic_client.py#L684)
- Prompt gains FB/IG slot counts, allowed angles, output arrays
  [`generation_prompts.py:1128`](../../backend/app/integrations/generation_prompts.py#L1128)
- `plan_week_angles` forwards counts and includes FB/IG in the fallback
  [`generation.py:339`](../../backend/app/services/generation.py#L339)
- Meta angle pools sized >= max post count so no duplicate angles
  [`angles.py:33`](../../backend/app/services/angles.py#L33)

**API + persistence**

- Create request validator now sums all four social counts + blog
  [`roadmaps.py:72`](../../backend/app/routers/roadmaps.py#L72)
- Review summary carries `facebook_post`/`instagram_caption`; hint detects Meta
  [`roadmaps.py:115`](../../backend/app/routers/roadmaps.py#L115)
- Saved plan config remembers Meta counts
  [`clients.py:476`](../../backend/app/routers/clients.py#L476)

**UI (Paper Style, via /web-uiux-architect)**

- Connection gating, config load, Facebook/Instagram toggles + spinners
  [`PlanMyWeekClient.tsx:161`](../../frontend/components/roadmap/PlanMyWeekClient.tsx#L161)
- Instagram-needs-image warning before submit
  [`PlanMyWeekClient.tsx:517`](../../frontend/components/roadmap/PlanMyWeekClient.tsx#L517)
- Review cards: Facebook/Instagram label, icon, char limit, image badge
  [`PostCard.tsx:29`](../../frontend/components/roadmap/PostCard.tsx#L29)

**Peripherals (types + tests)**

- Typed contract for counts and Meta post fields
  [`types.ts:41`](../../frontend/lib/types.ts#L41)
- Scheduling base-hour + image-priority + Meta classification tests
  [`test_roadmap_distribute.py:1`](../../backend/tests/services/test_roadmap_distribute.py#L1)
