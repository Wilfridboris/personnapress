# Epic 20 Context: Plan My Week / Weekly Content Roadmap

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Epic 20 introduces the "Plan My Week" feature, which lets a user submit a single brain dump and receive a full week of unique, platform-specific social posts (and optionally a blog post) in one session. The feature operates on a separate credit system (roadmap credits) independent of per-campaign credits, generates posts with distinct content angles via a two-stage LLM planner, schedules all approved posts automatically at platform-optimal times, and supports inline image management from the week-review grid. The end result is a zero-friction weekly content pipeline that replaces repetitive per-post creation with a single planning session.

## Stories

- Story 20.1: Roadmap Generation Engine
- Story 20.2: Week Review UI
- Story 20.3: Roadmap Post Management
- Story 20.4: Plan My Week UX Polish
- Story 20.5: Roadmap Campaign UX Polish
- Story 20.6: Roadmap Campaign Sync UX Fixes
- Story 20.7: Plan My Week Voice Recording
- Story 20.8: Roadmap Post Angle Variation
- Story 20.9: Roadmap Card Inline Image Upload

## Requirements & Constraints

**Credit model:** One roadmap submission consumes 1 roadmap credit (tracked in `subscriptions.roadmaps_used`), not N campaign credits. Campaign credits are never incremented for roadmap-generated campaigns. Plan limits: Starter 1, Growth 4, Agency unlimited. Image quota is handled via a non-raising batch check (`check_image_limit_batch`) that returns `(allowed, blocked)` — the roadmap generates images for the first `allowed` posts only.

**Post content rules:** Social-only roadmap campaigns have `blog_html = NULL` and only one platform post field set (`x_post` or `linkedin_post`). The other field is NULL. Publishing guards in `publishing.py` silently skip any platform whose field is NULL. Roadmap campaigns are never counted against `campaigns_used`.

**Character limits:** X posts 280 characters, LinkedIn posts 1,300 characters. These are enforced in both the edit panel counter (warning at 95% capacity) and in the tweet-creation truncation.

**Copy constraints (project-wide):** No em-dash (—), no double-dash (--), no emojis anywhere — in UI copy, placeholders, prompts, or generated content.

**Platform icons:** `Linkedin` and `Twitter` icons do not exist in the installed lucide-react version (v1.18.0). Use `AtSign` for LinkedIn and `Share2` for X, matching the existing `PlatformIcon` pattern.

**Approval Gate for roadmap social posts:** When a roadmap social campaign is opened individually, the Blog Post HTML section must be hidden (`isRoadmapSocialPost = !!roadmap_id && blog_html === null`). The ImagePanel remains visible. The H1 is derived by `getCampaignTitle()` which returns "X Post", "LinkedIn Post", or "Social Post" for roadmap social campaigns.

**Image fallback:** If image download or platform image upload fails during publishing, the post publishes as text-only silently (WARNING log only, no error badge shown to user).

**Scheduling is deterministic, not randomised:** LinkedIn posts at 09:00, X posts cycle 08:00/12:00/17:00. Mon-Fri first (Sat-Sun only if posts > 5). Same-platform posts stagger minimum 3 hours on the same day.

**Angle variation (20.8):** Each social slot receives a distinct `{angle, hook}` from a two-stage planner (one LLM call produces the week plan; per-post writers receive their angle as a directive). The planner is best-effort — failure falls back to deterministic rotation from `fallback_angles(platform, count)`. The `angle` code is persisted on `campaigns.angle` and displayed on the PostCard. Blog slots receive no angle.

## Technical Decisions

**Data model additions (all from 20.1):**
- New `roadmaps` table: `id, user_id, client_id, brain_dump, status (pending|generating|ready|approved|failed), week_start_date (DATE), generate_images, skip_blog, error_message, created_at, updated_at`.
- `campaigns.roadmap_id UUID FK roadmaps.id ON DELETE SET NULL` (nullable).
- `campaigns.angle TEXT` nullable — populated for roadmap social posts only.
- `clients.roadmap_config JSONB` nullable: `{linkedin_count, twitter_count, blog_enabled, images_enabled}`.
- `subscriptions.roadmaps_used INT NOT NULL DEFAULT 0`.

**Background generation:** Uses FastAPI `BackgroundTasks` (not APScheduler) for roadmap generation. Each background task opens its own `AsyncSessionLocal` session to avoid sharing the request-scoped session.

**Service boundaries:** `services/roadmap.py` is the sole orchestrator for multi-post roadmap generation. It delegates to `services/generation.py` for content and `services/image.py` for images. `publishing.py` is the only place that calls `decrypt_credential()`. `plan_week_angles()` lives in `generation.py` (not `roadmap.py`) to keep LLM provider isolation — roadmap.py calls `generation_service.plan_week_angles`.

**LLM provider parity:** Any method added to the generation pipeline (`generate_week_plan`, `generate_social_standalone` angle directive) must be implemented identically in both `integrations/anthropic_client.py` and `integrations/gemini.py`. The `_llm` indirection in `generation.py` binds to one provider at runtime based on `settings.LLM_PROVIDER`.

**Angle taxonomy single source of truth:** `backend/app/services/angles.py` defines `ANGLE_LABELS`, `KNOWN_CODES`, per-platform preference orders, and `fallback_angles(platform, count)`. The frontend mirrors the code-to-label map in `frontend/lib/angles.ts`. There is no compile-time sync enforcement between the two.

**Social image publishing (20.3):**
- X: INIT/APPEND/FINALIZE to `https://api.x.com/2/media/upload` (NOT the old `upload.twitter.com`). Chunks of 1 MB. Returns `media_id`.
- LinkedIn image posts: `POST https://api.linkedin.com/rest/posts` with `LinkedIn-Version: 202602` header (NOT `ugcPosts`). Image upload uses a pre-signed PUT URL — no Authorization header on the PUT step. Text-only LinkedIn posts continue using `ugcPosts` unchanged.
- Both platforms fall back silently to text-only on any image upload failure.

**Scheduling approve endpoint:** `POST /api/v1/roadmaps/{id}/approve` is idempotent-guarded, validates ownership (404 not 403), sets campaigns to `approved`, calls `distribute_schedule()` pure function, creates APScheduler jobs only after `db.commit()`.

**RSC pattern:** Server components on all roadmap routes (`/roadmap/new`, `/roadmap/[id]/review`, `/roadmap/`) read only the session JWT cookie and pass `clientId`/`userId` as props. All API calls live in client components via TanStack Query. This prevents the Turbopack dev-mode RSC re-render loop.

**Alembic:** Always use `alembic revision --autogenerate` from the `backend/` directory. Never hand-write revision IDs.

**Inline image upload (20.9):** `roadmapsApi.uploadCampaignImage(campaignId, clientId, file)` performs both the Supabase upload and the `PATCH /api/v1/campaigns/{id}/image` persistence in one call. The PostCard derives `displayedImage = pendingPreview ?? campaign.image_url` — never holds a stale `useState` copy.

## UX & Interaction Patterns

**Pages and routes:**
- `/roadmap/` — list of all roadmaps for the active client (TanStack Query, `RoadmapListClient`).
- `/roadmap/new` — settings panel + brain dump form (`PlanMyWeekClient`).
- `/roadmap/[id]/review` — polling week grid (`RoadmapReviewClient`).

**Settings panel:** Collapsible card on `/roadmap/new`. Contains LinkedIn/X count spinners (disabled with inline "Not connected. Connect [Platform]" note if the platform is not connected, checked via `usePlatformConnections`). Collapses after first save; "Change plan" reopens. Blog toggle defaults ON. Values pre-populated from `client.roadmap_config`.

**Generation polling:** TanStack Query polls `GET /api/v1/roadmaps/{id}` every 2 seconds while `status === "pending" || "generating"`. Shows the existing typewriter animation with roadmap-specific cycling messages. On `ready`, polling stops and the grid renders. On `failed`, shows an error card with `error_message` and a "Try again" link.

**Week review grid:** 7-column horizontal-scroll layout (`gridTemplateColumns: "repeat(7, minmax(180px, 1fr))"`, `minWidth: 1260px`). No Framer Motion on the grid — CSS transitions only, except for the PostEditPanel slide-open which uses `AnimatePresence` + `motion.div` height animation (CSS `max-height: auto` cannot animate to unknown height).

**Post card states:** Default, removed (opacity-50, line-through, "REMOVED" badge, Undo button), and edit (PostEditPanel slides open below card). Remove is client-side only until approve. Removed posts are excluded from the approve count and from `excluded_campaign_ids` in the approve payload.

**Sticky footer:** Fixed bottom bar visible only on the review page. Shows "N posts selected" (non-removed count) and the "Approve All & Schedule" primary button. Button has `aria-live` announcement when count changes.

**Voice recording (20.7):** `VoiceBrainDump` component rendered above the textarea on `/roadmap/new`. Transcript APPENDS to the brain dump (not replaces, unlike `/campaigns/new`). Combined text is clamped to 10,000 characters. Caret is moved to end after append.

**Angle chip (20.8):** Inline in the PostCard top row beside the platform chip. `font-body text-xs uppercase tracking-[0.08em] text-graphite border border-[#E5E5E5] px-1.5 py-0.5`. Static, non-interactive. Not shown for blog cards or null angles.

**Paper Style compliance:** `rounded-none` everywhere, no emojis, no exclamation marks. Colors: Paper `#F9F9F6`, Ink `#111111`, Graphite `#555555`, Border `#E5E5E5`, Highlighter `#FFF1B8` for warnings, Danger `#8B0000` for errors. Playfair Display for H1/H2, Inter for labels/body, JetBrains Mono for brain dump and post edit textareas.

**Accessibility:** All icon-only buttons have `aria-label`. Icons decorative-only have `aria-hidden`. Edit panel has `role="region"`. Minimum 44px touch targets. Error messages use `role="alert"`.

## Cross-Story Dependencies

- **20.1 is the foundation for all others.** It creates the `roadmaps` table, `campaigns.roadmap_id` FK, `campaigns.angle` (added in 20.8 via migration), `roadmaps_used` on subscriptions, the generation service, and all backend endpoints. No other story in this epic can ship without it.
- **20.2 depends on 20.1 and partially on 20.3.** The "Approve All & Schedule" button calls `POST /api/v1/roadmaps/{id}/approve`, which is implemented in 20.3. The approve button returns 404 until 20.3 ships.
- **20.3 depends on 20.1 and 20.2.** The approve endpoint routes to campaigns that exist only after 20.1 generation, and the ROADMAP badge in the campaign list requires the `roadmap_id` field on `CampaignResponse`.
- **20.4 depends on 20.1, 20.2, 20.3.** It fixes the `[:100]` truncation bug introduced in 20.1, adds the roadmap list page, and fixes the `ApprovalGateClient` for roadmap social campaigns.
- **20.7, 20.8, 20.9 depend on 20.2 and 20.4** (the review page and PostCard must exist). 20.8 also requires 20.1's `generate_social_only` function and adds a DB migration for `campaigns.angle`.
- **20.9 is purely additive** — single frontend file change to `PostCard.tsx`; no backend work; depends on the `roadmapsApi.uploadCampaignImage` helper from 20.2 and the `onUpdate` prop already wired in 20.2/20.4.
