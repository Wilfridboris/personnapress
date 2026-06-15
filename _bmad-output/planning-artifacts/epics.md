---
stepsCompleted: [1, 2, 3, 4]
lastStep: 4
status: 'complete'
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md'
  - '_bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/addendum.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md'
project_name: PersonnaPress
user_name: Boris
date: '2026-06-14'
---

# PersonnaPress - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for PersonnaPress, decomposing the requirements from the PRD, UX Design, and Architecture documents into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1: User can register with email/password or Google OAuth (via Google Cloud OAuth 2.0). System sends verification email on signup. User cannot access features until email is verified. Google OAuth users skip verification.

FR-2: Registered user can log in via email/password or Google OAuth and receive a session token. Session persists across browser tabs for 7 days. Invalid credentials return a generic error (no credential enumeration).

FR-3: Authenticated user can view their current plan, upgrade, downgrade, or cancel subscription via Stripe Customer Portal. Upgrade is immediate; downgrade takes effect next billing cycle; cancellation retains access until end of current billing period.

FR-4: Authenticated user can create a new Client by providing a name and optional website URL. Client record is created with empty Brand Voice Profile. If URL provided, Brand Ingestion triggers automatically. Client count is enforced per subscription tier with upgrade prompt on limit.

FR-5: User can update a Client's name, website URL, and Brand Voice Profile. Changing URL triggers re-ingestion with confirmation. BVP edits are saved immediately and applied to all future Campaigns.

FR-6: User can delete a Client and all associated Campaigns and Platform Connections. System shows destructive-action confirmation with client name and Campaign count. Deletion cascades to all Campaigns, Platform Connections, and BVP.

FR-7: User can view all Clients and switch active context between them. Dashboard always shows the active Client. Switching Clients loads that Client's Campaign history, BVP, and Platform Connections.

FR-8: System can scrape a provided website URL and extract text content from blog posts and public-facing written content. Extracts at least 10 most recent blog posts. Strips non-content elements. Completes within 60 seconds for sites up to 50 pages. On failure, surfaces error and offers manual fallback (FR-10).

FR-9: User can upload text files (.txt, .md, .docx) or paste raw text to supplement or replace scraped content. Uploaded content is appended to scraped content before voice extraction. Stored in Supabase Storage. Max 5 MB per file, 10 files per Client.

FR-10: System uses Gemini 2.5 Flash (1024 thinking tokens) to analyze collected content and produce a Brand Voice Profile containing Tone, Cadence, and Banned Jargon. Profile stored as structured JSON on Client record. User can review and edit every field before finalization. If no content is available, falls back to a manual voice questionnaire (tone sliders, sample text, example URLs).

FR-11: User can trigger re-extraction of the Brand Voice Profile at any time using updated website content or new uploads. Re-extraction overwrites existing profile after user confirmation. No profile version history in v1.

FR-12: User can enter free-form text or bullet points as a Brain Dump for the active Client. Input field uses monospace typography and auto-expands. Minimum 20 characters, maximum 10,000 characters. Submitting creates a new Campaign in pending_approval status and triggers content generation.

FR-13: System generates an SEO-structured blog post in HTML from the Brain Dump, conforming to the Client's BVP. Output includes title (H1), meta description, structured headings (H2/H3), body paragraphs, and conclusion. Targets 800-1,500 words. Uses Gemini 2.5 Flash with 512 thinking tokens. After generation, runs a second Gemini call (256 thinking tokens) to score the draft on tone alignment (0-10), cadence match (0-10), and banned-jargon violations. Draft passes if tone >= 7, cadence >= 6, jargon violations = 0. Failing score surfaces an advisory warning badge ("Voice match: 6/10 — review tone") but does not block approval.

FR-14: System generates platform-specific social posts from the same Brain Dump and BVP. X post is ≤280 characters (no threads). LinkedIn post is 500-1,300 characters with line breaks for readability. Both reference/tease the blog without duplicating it. Uses Gemini 2.5 Flash with 0 thinking tokens.

FR-15: System returns 202 Accepted immediately on Campaign creation and provides real-time status updates during generation. A job record is created in Supabase Postgres tracking task type, status, timestamps, and error details. Frontend polls this record for progress. If generation fails, job record and Campaign status are set to `failed` with error message and retry prompt. Job records survive process restarts. Total generation time under 90 seconds for typical inputs.

FR-16: System generates a featured image based on the blog post title and content summary using FLUX.1 [pro] via Replicate API. Image is 1200x630 PNG stored in Supabase Storage and served via CDN public URL. If image generation fails, Campaign still proceeds and user is notified with independent retry option.

FR-17: User can preview the generated image and request a new generation with optional prompt override. "Regenerate" button triggers a new FLUX.1 [pro] call and replaces previous image. Maximum 3 regenerations per Campaign.

FR-18: User can view a full preview of all Campaign content: blog post (rendered HTML), X post, LinkedIn post, and featured image. Blog preview renders HTML as it would appear on target CMS. Social posts display with platform-appropriate formatting. Featured image displays at full resolution.

FR-19: User can edit any generated content directly in the preview before approving. Blog post is editable via WYSIWYG editor. Social posts are editable as plain text with live character count. Edits are saved to the Campaign record.

FR-20: User can approve a Campaign, transitioning status from `pending_approval` to `approved`. If no Platform Connections exist for the active Client, system prompts user to connect at least one platform before publishing.

FR-21: User can reject a Campaign with an optional reason, transitioning status to `rejected`. User can trigger regeneration from the same Brain Dump (generates new content, resets to `pending_approval`). Rejection reason stored on Campaign record.

FR-22: User can connect a Client to external publishing platforms by providing API credentials. WordPress: URL + Application Password (validated via test API call). Webflow: API Bearer Token + Collection ID (validated). X: OAuth 2.0 PKCE flow. LinkedIn: OAuth 2.0 with `w_member_social` scope. All credentials encrypted at rest using AES-256-GCM. Connection validation fails gracefully with specific error messages.

FR-23: User can publish an approved Campaign immediately to all connected platforms. WordPress: draft-first pattern (POST draft → upload featured image → PATCH to publish; clean up draft on failure). Webflow: CMS API v2 create + separate publish endpoint. X: Twitter API v2 OAuth 2.0 PKCE. LinkedIn: UGC Posts API v2 with version header 202602. Each platform publish is independent. Campaign status transitions to `published` only when all connected platforms succeed. Partial failures set status to `failed` with per-platform error details.

FR-24: User can set a future date/time for an approved Campaign to publish automatically. User selects date/time via datetime picker. Timezone set at account level. Persistent job record written to Supabase Postgres with Campaign ID, scheduled time, and status. APScheduler reads from this table on startup to recover pending jobs. Failed scheduled publishes capture failure detail and notify user in-app.

FR-25: User can retry a failed publish on specific platforms without regenerating content. Failed platforms listed with error messages. Retry attempts only the failed platforms. Each retry creates or updates persistent job record with attempt count. Maximum 3 retry attempts per platform per Campaign. If backend restarts between retries, job record persists for user-initiated retry.

FR-26: User sees a list of all Campaigns for the active Client, ordered by creation date (newest first). Each Campaign shows title, status badge, creation date, and publish date (if published). List is filterable by status. Clicking a Campaign opens the Approval Gate view. Paginated at 20 per page.

FR-27: User sees a calendar view of published and scheduled Campaigns in a read-only month view. Published Campaigns show with linked platform icons. Scheduled Campaigns show with clock icon and scheduled time. Read-only in v1 — no drag-and-drop rescheduling. Clicking a date entry navigates to the Approval Gate for that Campaign.

FR-28: When a user's 14-day trial expires without subscribing, the system transitions them to a restricted state. User can log in and view existing data but cannot create new Campaigns, generate content, or publish. Persistent upgrade banner appears on every page. All existing data preserved for 30 days after trial expiration. After 30 days, account scheduled for deletion with 7-day warning email. In-app upgrade nudges appear at day 10 (4 days remaining) and day 13 (1 day remaining).

### NonFunctional Requirements

NFR-1: Performance — Content generation (blog + social + image) completes within 120 seconds at 95th percentile. Frontend is interactive within 2 seconds on a 4G connection. Generation target of 90 seconds for typical inputs.

NFR-2: Availability — 99.5% uptime target. Supabase provides managed Postgres with built-in availability. FastAPI Droplet is a single point of failure for the API layer in v1 (explicitly accepted).

NFR-3: Security — All API traffic over HTTPS (TLS 1.3). Frontend-to-backend communication authenticated via session tokens (JWT in httpOnly cookie: secure=True, samesite=lax). No plaintext credentials stored anywhere. Parameterized queries for all database access (SQL injection prevention). Output encoding for user-submitted content rendered in HTML previews (XSS prevention). CSRF protection via origin checking on state-changing requests. AES-256-GCM credential encryption at rest (key in Droplet env var only, never in DB). OAuth token scoping to minimum required permissions per platform.

NFR-4: Scalability — Supabase Postgres removes database bottleneck. $6 DO Droplet (1 vCPU/1 GB) handles ~50 concurrent generation requests. Upgrade path: $12 Droplet (2 vCPU/2 GB) for ~100 concurrent, then container orchestration (DO App Platform / Fly.io) beyond that.

NFR-5: Data Integrity — Supabase Postgres with point-in-time recovery (PITR) on Pro plan ($25/mo). Supabase Storage provides durable CDN-backed file hosting.

NFR-6: Observability — Structured JSON logging for all API requests, generation events, and publish events. Error tracking via Sentry (or equivalent) in both Next.js and FastAPI apps. Supabase Dashboard for DB and Storage metrics.

NFR-7: Job Durability — All generation, publishing, scheduling, and retry tasks backed by persistent job records in Supabase Postgres. APScheduler uses SQLAlchemy job store pointing at Supabase Postgres to recover on restart. Process restarts do not lose in-flight or scheduled work.

NFR-8: Rate Limiting — 10 requests/minute/user enforced at FastAPI middleware layer via slowapi. Returns HTTP 429 with Retry-After header on violation.

NFR-9: Cost Controls — Per-user Gemini token usage and Replicate image count logged to `generation_logs` table for internal monitoring. Hard limits per plan tier enforced before generation or client-creation. Gemini thinking budgets tuned per task (0 social / 256 voice check / 512 blog / 1024 ingestion). FLUX.1 [pro] image generation capped per plan tier. Staggered outbound publishing (2s between X posts, 5s between LinkedIn posts). X API uses tweet.fields selective parameters to reduce rate-limit pressure. Gemini 5xx/429 errors: after 3 consecutive failures, Campaign is set to `failed` — no silent infinite retry.

NFR-10: Privacy and Data Ownership — Users own all generated content. All third-party credentials encrypted at rest (AES-256-GCM, key in env vars only). Brain Dump text stored for Campaign lifetime; users can delete at any time. Privacy Policy must disclose Gemini API and Replicate data usage policies. English-language content only in v1.

### Additional Requirements

- AR-1: Project structure is a mono-repo with two application roots: `frontend/` (Next.js 16.2.9) and `backend/` (FastAPI Python 3.12), alongside `_bmad-output/` for planning artifacts.
- AR-2: Frontend initialized via `create-next-app` with TypeScript (strict mode), Tailwind CSS v4, ESLint, App Router, `@/*` import alias. Paper Style design tokens added as Tailwind theme extension.
- AR-3: Backend initialized manually: FastAPI + SQLModel + Alembic + APScheduler (SQLAlchemy job store) + cryptography + httpx + BeautifulSoup4 + all platform integrations (stripe, google-generativeai, replicate) + sentry-sdk.
- AR-4: Supabase project must be created and Alembic initial migration run for all 7 tables before any feature stories. Tables: `users`, `subscriptions`, `clients`, `platform_connections`, `campaigns` (with `image_regen_count` column), `jobs`, `generation_logs`.
- AR-5: Transactional email provider must be decided before auth implementation story. Resend is recommended (RESEND_API_KEY env var, one call in services/email.py). This is a pre-implementation blocker for FR-1.
- AR-6: `jose` npm package required in frontend for edge-runtime JWT verification in Next.js middleware.ts (Node.js-only JWT libraries cannot run in edge runtime).
- AR-7: Custom JWT authentication: FastAPI issues signed JWT on login; cookie flags httpOnly=True, secure=True, samesite="lax", 7-day expiry; payload: user_id, email, plan_tier, exp. Same JWT_SECRET used by Next.js middleware (server-side only, never NEXT_PUBLIC_).
- AR-8: Google OAuth flow: Next.js `/api/auth/google/callback` exchanges auth code for Google profile server-side, then calls FastAPI `POST /auth/google` which creates/finds user and issues JWT.
- AR-9: ORM: SQLModel (latest). Migrations: Alembic with SQLAlchemy backend. snake_case naming throughout: DB columns, API response fields, TypeScript types (no camelCase conversion layer).
- AR-10: State management: Zustand for UI state (useClientStore, useUIStore); React Query for all server state including job status polling (refetchInterval: 2000 while pending/in_progress, stops at terminal state).
- AR-11: Rich text editor: Tiptap (@tiptap/react + @tiptap/starter-kit + @tiptap/extension-link). Input: setContent(htmlString) on mount. Output: editor.getHTML() on save/approve. Styled via @tailwindcss/typography prose classes.
- AR-12: HTML sanitization: DOMPurify used in BlogPreview.tsx to sanitize user-submitted and AI-generated HTML before rendering.
- AR-13: X OAuth PKCE state stored in short-lived httpOnly cookie (oauth_state, SameSite=Lax, 10-minute expiry) set before redirect, verified in callback route.
- AR-14: Trial expiration and account deletion: daily recurring APScheduler job `subscription_cleanup` in scheduler/scheduler.py queries subscriptions for expired trials and enqueues deletion warnings and deletion actions.
- AR-15: Stripe webhooks handled by Next.js API route (`/api/webhooks/stripe/route.ts`), not FastAPI. Google OAuth callbacks handled by Next.js (`/api/auth/google/callback/route.ts`).
- AR-16: Manual deploy.sh script for backend (SSH → git pull → pip install → alembic upgrade head → systemctl restart). Frontend auto-deploys to Vercel on push to main.
- AR-17: All FastAPI routes prefixed with `/api/v1/`. Standard error response format: `{"error": {"code": "SCREAMING_SNAKE_CASE", "message": "...", "detail": {}}}`. HTTP status codes per REST convention.
- AR-18: Subscription tier enforcement via `services/subscription.py` must be called by ALL routers before any create/generate action. Client count, Campaign count, and image generation count checked before execution.
- AR-19: Service boundaries enforced: `services/publishing.py` is the ONLY place that calls `decrypt_credential()`; `services/generation.py` is the ONLY place that calls gemini.py; `services/image.py` is the ONLY place that calls replicate.py; routers delegate to services only (no business logic in routers).

### UX Design Requirements

UX-DR1: Implement Paper Style color palette as Tailwind CSS theme extension and CSS custom properties: Paper (#F9F9F6), Ink (#111111), Graphite (#555555), Border (#E5E5E5), Highlighter (#FFF1B8), Danger (#8B0000), Success (#2E4F2E), White (#FFFFFF). No additional colors permitted — redesign elements to fit existing vocabulary.

UX-DR2: Implement three typography families as global CSS/Tailwind tokens loaded via next/font: Playfair Display (H1/H2 only, 700 weight, -0.01em letter-spacing, 1.15 line-height), Inter (body 15px/UI 12px label, 0.06em letter-spacing for labels, uppercase transform, 1.6 line-height), JetBrains Mono (Brain Dump input and raw/machine output only, 14px, 1.7 line-height).

UX-DR3: Implement three Button variants with exact Paper Style specs: Primary (Ink fill, White text, 4px 4px 0px Ink hard shadow at rest, inverts to White fill + Ink border + Ink text on hover, rounded-none, 0.625rem/1.25rem padding); Secondary (transparent, 1px Ink border, no shadow, inverts on hover); Danger (Danger red fill, White text, no shadow). One primary button per page/modal context maximum.

UX-DR4: Implement Input components: Standard (bottom-border-only, 1px at rest, 2px on focus, no ring or background change, transparent background, Graphite placeholder); Brain Dump textarea (JetBrains Mono, auto-expanding, bottom-border only, disappears as form element, min 120px height, no resize handle).

UX-DR5: Implement Card components: Default (White fill, 1px Border, no shadow, hover adds 4px 4px 0px Ink hard shadow); Active variant (Highlighter fill, 1px Ink border, 4px hard shadow). Sharp corners on all cards (rounded-none).

UX-DR6: Implement five Campaign Status Badge variants at 2px border-radius with uppercase tracked Inter label text: Pending Approval (Highlighter fill, Ink border, "PENDING APPROVAL"); Approved (Border fill, Graphite text, "APPROVED"); Published (Success green fill, White text, "PUBLISHED"); Rejected (transparent fill, Border, strikethrough, "REJECTED"); Failed (Danger red fill, White text, "FAILED"). Badges never rely on color alone — text is always present.

UX-DR7: Implement Sidebar and navigation layout: Paper background + 1px right Border; Client switcher occupies top 56px; primary nav links below; account/subscription link pinned to bottom; width 240px at lg, 56px icon-only at md (768-1023px), slide-in drawer at <768px. Nav item: Graphite label, Highlighter bg + Ink text on hover. Active nav item: Highlighter bg, Ink text, 2px left Ink border.

UX-DR8: Implement Voice Score Warning badge component: Danger-color uppercase tracked Inter label text, "VOICE MATCH: N/10 — REVIEW TONE"; clicking expands inline detail showing per-dimension breakdown (tone score, cadence score, jargon violations); shown in Approval Gate header only when score fails threshold; does not block Approve action.

UX-DR9: Implement Upgrade Banner component: full-width sticky bar at top of viewport; Ink fill + White text; non-dismissible; pushes layout down (not an overlay); disappears when subscription is activated; contains trial status text and "Subscribe" CTA (White-on-Black secondary-inverted style).

UX-DR10: Implement Typewriter animation component for AI generation states: character-by-character text reveal in JetBrains Mono on Paper background; fills full content area during generation; status message line cycles through: "Analyzing your voice profile..." → "Drafting blog post..." → "Checking voice fidelity..." → "Generating featured image..." → "Done."; aria-live="polite" on status line; character-reveal is aria-hidden; prefers-reduced-motion fallback (simple "Generating..." text with pulsing opacity only). Used only for AI generation — not for other loading states.

UX-DR11: Implement 3-step Onboarding Flow (triggered on first login, replaces Dashboard on completion): Step 1 (centered card, no sidebar, Playfair H1 "Who are you writing for?", Client name + URL fields, primary CTA "Create client and analyze voice", skip link below); Step 2 (same centered layout, progress "2 of 3", ingestion typewriter if URL provided OR voice questionnaire if no URL, "Confirm my voice profile" CTA, skip link); Step 3 (full-width Brain Dump input, progress "3 of 3", Playfair H2 "What's on your mind this week?", "Generate my first campaign" CTA, skip link to Dashboard). Navigation is blocked until step completion or explicit skip.

UX-DR12: Implement Voice Questionnaire component (manual Brand Voice fallback): 3-step wizard: Step 1 = three tone slider pairs (Formal↔Casual 1-5, Professional↔Friendly 1-5, Concise↔Elaborate 1-5); Step 2 = up to 3 sample text paste areas labeled "Paste a piece of writing that sounds like you."; Step 3 (optional) = up to 3 URL input fields labeled "A writer whose style you admire." On submit, shows extraction typewriter animation then confirms profile.

UX-DR13: Implement responsive layout system: lg (≥1024px) = full 240px sidebar, content capped at 720px max-width, Approval Gate as two-panel layout (blog WYSIWYG ~60% left / social posts + image + voice score + action footer right); md (768-1023px) = 56px icon-only sidebar, Approval Gate single column (blog → social → image); <768px = slide-in drawer sidebar + top bar (Logo, hamburger, active client name), Brain Dump full-screen, Approval Gate single column stack. All interactive elements minimum 44px touch target height.

UX-DR14: Implement Content Calendar surface (/calendar): month view, read-only; Published campaigns show linked platform icons (WP, Webflow, X, LinkedIn) on the date; Scheduled campaigns show clock icon + time; each calendar day cell has aria-label including date and campaign count; clicking a date entry navigates to Approval Gate for that Campaign; no drag-to-reschedule.

UX-DR15: Implement Approval Gate Retry Panel (shown when Campaign status is `failed`): lists each platform that failed with its specific error message; per-platform "Retry" button; shows attempt count "Attempt N of 3"; Retry buttons disabled at maximum attempts.

UX-DR16: Implement WCAG 2.2 AA accessibility across all surfaces: screen reader page announcements on navigation ("Dashboard — PersonnaPress"); all inputs with visible labels (not placeholder-only) + aria-describedby on error messages; modals with role="dialog", aria-labelledby, focus trap (Tab cycles within modal), Esc to close, focus returns to trigger on close; no Tab traps outside modals/dialogs; featured images with descriptive alt text from blog title; WYSIWYG editor toolbar with accessible button labels + role="textbox" aria-multiline="true" on content area; calendar day cells with aria-label including date + campaign count.

UX-DR17: Implement skeleton loading placeholders (matching layout shape) for initial page content: sidebar links, campaign rows, form fields — no spinner for page loads. Inline spinner permitted only for action buttons (approve, publish, generate, retry) while action is in progress.

UX-DR18: Implement Social Post editors in Approval Gate: plain textarea per platform (X and LinkedIn); live character counter below each ("N / 280" for X, "N / 1300" for LinkedIn); counter color changes to Danger at 95% capacity; Tab key moves between X editor → LinkedIn editor → next action element in sequence.

UX-DR19: Implement Client Switcher dropdown in sidebar header: shows all Client names; active client has checkmark; switching client navigates to Dashboard and reloads with new active context; optimistic update of active client label before navigation completes.

UX-DR20: Implement Platform Connection management UI: per-platform connection card showing status (connected/not connected) + connected account identifier (@handle or site.com); "Connect" CTA opens OAuth popup or inline credential form; popup completion updates card to "Connected" without page reload; "Disconnect" opens confirmation dialog; Webflow: after successful OAuth shows Collection selector dropdown populated from Webflow CMS API, falls back to text input with documentation link if API call fails.

UX-DR21: Implement all microcopy per Paper Style voice/tone spec: no exclamation marks in UI copy; error messages always name the platform + HTTP status code (when applicable) + resolution path; empty state copy matches EXPERIENCE.md patterns ("No campaigns yet. Start with a Brain Dump.", "Nothing scheduled. Approve a campaign to see it here."); no "magic" / "supercharge" / "hang tight" language; destructive confirms name the specific item and impact ("Delete 'TechFounder Blog'? This will remove 12 campaigns and all platform connections.").

UX-DR22: Implement Approval Gate state machine UI: pending state (full content visible, sticky Approve/Reject footer, both disabled while publish or generation job is in flight); approved-not-yet-published state (approval section replaced by schedule picker + "Publish now" + "Schedule" CTAs); published state (footer replaced by "Published" summary with date/time + platform links "View on [Platform] →", read-only); rejected state ("Rejected" status shown + "Regenerate from same Brain Dump" primary CTA); failed state (Retry panel shown).

UX-DR23: Implement Brain Dump page interaction rules: submit button is the primary action (Enter key does NOT submit — prevents accidental generation); Cmd/Ctrl+Enter submits as power-user affordance; Esc does nothing (prevents accidental loss of long inputs); inline character counter below input "N / 10,000 characters"; submit button disabled below 20-character minimum; navigation away during generation is blocked with confirm dialog: "Generation is in progress. Leaving will not cancel it — your draft will be available on the Dashboard when complete."

### FR Coverage Map

```
FR-1:  Epic 1 — User registration (email/password + Google OAuth, email verification)
FR-2:  Epic 1 — User authentication (login, 7-day session, logout)
FR-3:  Epic 1 — Subscription management (Stripe Customer Portal link, plan/usage display)
FR-4:  Epic 2 — Create Client (name, URL, BVP init, tier limit enforcement)
FR-5:  Epic 2 — Edit Client (name, URL, BVP edits; URL change triggers re-ingestion)
FR-6:  Epic 2 — Delete Client (cascade confirm dialog)
FR-7:  Epic 2 — List and switch Clients (active context, sidebar switcher)
FR-8:  Epic 2 — Website scraping (10-post extraction, 60s timeout, fallback)
FR-9:  Epic 2 — Content upload (.txt/.md/.docx, Supabase Storage, 5MB/10 file limits)
FR-10: Epic 2 — Voice Profile Extraction (Gemini 1024t, Tone/Cadence/Jargon, manual questionnaire fallback)
FR-11: Epic 2 — Voice Profile Refresh (re-extraction on demand, overwrite confirm)
FR-12: Epic 3 — Brain Dump capture (monospace textarea, 20-10,000 chars, Campaign creation)
FR-13: Epic 3 — Blog post generation (SEO HTML, 512t, advisory voice fidelity check 256t)
FR-14: Epic 3 — Social post generation (X ≤280 chars, LinkedIn 500-1300 chars, 0 thinking tokens)
FR-15: Epic 3 — Generation status feedback (202 Accepted, job records, polling, typewriter, retry on fail)
FR-16: Epic 3 — Featured image generation (FLUX.1 [pro], 1200x630 PNG, Supabase Storage)
FR-17: Epic 3 — Image preview and regeneration (preview, Regenerate button, 3-regen cap)
FR-18: Epic 4 — Campaign review (rendered blog HTML, social posts, featured image at full res)
FR-19: Epic 4 — Inline editing (WYSIWYG blog editor, plain text social editors with live char count)
FR-20: Epic 4 — Approve Campaign (pending_approval → approved; prompt to connect platforms if none)
FR-21: Epic 4 — Reject Campaign (rejected status, optional reason, regenerate from same Brain Dump)
FR-22: Epic 5 — Platform connection setup (WordPress, Webflow, X OAuth PKCE, LinkedIn OAuth, AES-256-GCM)
FR-23: Epic 5 — Immediate publishing (WordPress draft-first, Webflow CMS, X API v2, LinkedIn UGC Posts)
FR-24: Epic 5 — Scheduled publishing (datetime picker, APScheduler + persistent job records)
FR-25: Epic 5 — Publishing retry (per-platform retry, 3-attempt cap, persistent job records)
FR-26: Epic 6 — Campaign list (ordered by date, status filter, 20/page pagination, click-to-open)
FR-27: Epic 6 — Content Calendar (read-only month view, platform icons, scheduled clock icon)
FR-28: Epic 7 — Trial expiration (restricted state, upgrade banner, 30+7 retention/deletion, nudges)
```

Coverage: 28/28 FRs — no gaps.

## Epic List

### Epic 1: Project Foundation, Authentication & Account Management

A developer can scaffold the full monorepo (Next.js frontend, FastAPI backend, Supabase schema with all 7 tables), deploy to Vercel + DigitalOcean, and configure the Paper Style design system. A user can register via email/password or Google OAuth, verify their email, log in with a persistent 7-day session, and access the protected app shell with sidebar navigation. Subscription management (Stripe portal link, plan/usage display) is available in the Account surface.

**FRs covered:** FR-1, FR-2, FR-3

### Epic 2: Client Management & Brand Voice Ingestion

A user can create and manage Client profiles (brand identities), trigger website scraping to automatically extract a Brand Voice Profile, upload supplementary content files, or complete the manual voice questionnaire as a fallback. They can edit, refresh, or delete Clients, and switch active context between multiple Clients in the sidebar. The 3-step onboarding flow guides new users through this on first login.

**FRs covered:** FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-10, FR-11

### Epic 3: Brain Dump & Content Generation

A user can submit a Brain Dump (free-form text, 20–10,000 chars) and receive a fully generated Campaign — SEO-structured blog post, X post, LinkedIn post, and featured image — all in their Brand Voice. Real-time typewriter animation provides generation status feedback. A persistent job record tracks the async generation pipeline through any backend restart. Voice fidelity scoring runs as an advisory check after blog generation.

**FRs covered:** FR-12, FR-13, FR-14, FR-15, FR-16, FR-17

### Epic 4: Approval Gate & Content Review

A user can view a full preview of all Campaign content (rendered blog HTML, social posts, featured image), edit the blog post in the WYSIWYG editor, edit social posts with live character counters, see an advisory voice fidelity badge with per-dimension breakdown, approve a Campaign (advancing it to `approved` status), or reject it with an optional reason and trigger regeneration from the same Brain Dump.

**FRs covered:** FR-18, FR-19, FR-20, FR-21

### Epic 5: Platform Connections & Publishing

A user can connect a Client to WordPress, Webflow, X, and LinkedIn via credential entry or OAuth flows (with AES-256-GCM encryption at rest), publish an approved Campaign immediately to all connected platforms using platform-specific APIs, schedule a Campaign for a future date/time with APScheduler-backed persistent job records, and retry failed platform publishes independently for up to 3 attempts.

**FRs covered:** FR-22, FR-23, FR-24, FR-25

### Epic 6: Dashboard & Content Calendar

A user can view all Campaigns for the active Client in the Dashboard (ordered by date, filterable by status, paginated at 20/page) and navigate to any Campaign's Approval Gate by clicking its row. The Content Calendar surface provides a read-only month view showing published Campaigns (with platform icons) and scheduled Campaigns (with clock icon and time).

**FRs covered:** FR-26, FR-27

### Epic 7: Trial Lifecycle & Subscription Enforcement

The system handles the complete 14-day trial lifecycle: in-app nudge notifications at day 10 and day 13, a non-dismissible upgrade banner on trial expiry, blocking of new Campaign creation/generation/publishing post-expiry while preserving all existing data, 30-day data retention post-trial, and a 30+7 day warning-then-deletion policy via a daily APScheduler cleanup job. Subscription tier enforcement (Client count, Campaign count, image generation count limits) is verified across all creation and generation actions.

**FRs covered:** FR-28

<!-- Epics with Stories begin below -->

## Epic 1: Project Foundation, Authentication & Account Management

A developer can scaffold the full monorepo (Next.js frontend, FastAPI backend, Supabase schema with all 7 tables), configure the Paper Style design system with all primitive UI components, and set up deployment pipelines. A user can register via email/password or Google OAuth, verify their email, log in with a persistent 7-day session, navigate the protected app shell with responsive sidebar navigation, and manage their subscription via Stripe.

### Story 1.1: Monorepo Scaffold, Infrastructure & Paper Style Design System

As a developer,
I want the monorepo initialized with both applications, the Paper Style design system configured, the Supabase database schema deployed, and deployment pipelines in place,
So that the team has a consistent, production-ready foundation on which all features can be built.

**Acceptance Criteria:**

**Given** the monorepo root is initialized,
**When** the setup is complete,
**Then** `/frontend` and `/backend` directories exist alongside `_bmad-output/`, `.github/workflows/frontend-deploy.yml`, `deploy.sh`, and a root `.gitignore` that excludes `.env`, `.venv`, and `node_modules`.

**Given** `cd frontend && npm run build` is executed,
**When** it completes,
**Then** Next.js 16.2.9 LTS builds successfully with TypeScript strict mode, Tailwind CSS v4, App Router, ESLint, and the `@/*` import alias configured; `jose` and `@tiptap/react` (and related Tiptap packages) and `dompurify` are present in `package.json`.

**Given** `frontend/tailwind.config.ts` is reviewed,
**When** the config is loaded,
**Then** the Paper Style color palette is present as named Tailwind theme extension tokens: `paper` (#F9F9F6), `ink` (#111111), `graphite` (#555555), `border` (#E5E5E5), `highlighter` (#FFF1B8), `danger` (#8B0000), `success` (#2E4F2E), `white` (#FFFFFF); and typography tokens reference Playfair Display, Inter, and JetBrains Mono loaded via `next/font`.

**Given** `frontend/app/globals.css` is reviewed,
**When** the file is loaded,
**Then** it contains CSS custom properties for all Paper Style design tokens, Tailwind base layers, and `@tailwindcss/typography` prose configuration.

**Given** `frontend/components/ui/` is reviewed,
**When** each component file is opened,
**Then** the following Paper Style primitive components exist and implement the exact visual specs from DESIGN.md: `Button.tsx` (Primary: ink fill, white text, `4px 4px 0px ink` hard shadow, inverts on hover; Secondary: transparent, 1px ink border; Danger: danger-red fill; all `rounded-none`); `Input.tsx` (Standard: bottom-border-only, 1px at rest, 2px on focus, no ring; BrainDump variant: JetBrains Mono, auto-expanding, subtle bottom border); `Card.tsx` (Default: white fill, 1px border, hover adds `4px 4px 0px ink` shadow; Active: highlighter fill, 1px ink border, hard shadow); `StatusBadge.tsx` (five Campaign lifecycle variants per DESIGN.md, 2px radius, uppercase tracked Inter label); `Skeleton.tsx` (layout-matching placeholder blocks); `Toast.tsx`; `Modal.tsx` (with focus trap and Esc-to-close behavior).

**Given** the FastAPI backend is set up,
**When** `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` completes,
**Then** all required packages are installed: `fastapi[standard]`, `uvicorn[standard]`, `sqlmodel`, `alembic`, `asyncpg`, `apscheduler`, `cryptography`, `python-jose[cryptography]`, `passlib[bcrypt]`, `httpx`, `beautifulsoup4`, `python-multipart`, `stripe`, `google-generativeai`, `replicate`, `sentry-sdk`, `slowapi`, `resend`.

**Given** `alembic upgrade head` is run against the configured Supabase Postgres connection,
**When** the migration completes,
**Then** all 7 tables are created with correct columns and constraints: `users` (id uuid PK, email unique, hashed_password nullable, google_sub nullable, stripe_customer_id nullable, verified bool, created_at timestamptz); `subscriptions` (id uuid PK, user_id FK, stripe_sub_id, plan_tier, status, campaigns_used int, clients_count int, image_gen_used int, billing_cycle_start timestamptz, billing_cycle_end timestamptz, created_at, updated_at); `clients` (id uuid PK, user_id FK, name, website_url nullable, brand_voice_profile jsonb nullable, created_at, updated_at); `platform_connections` (id uuid PK, client_id FK, platform enum, encrypted_credentials text, created_at, updated_at); `campaigns` (id uuid PK, client_id FK, brain_dump text, blog_html text nullable, x_post text nullable, linkedin_post text nullable, image_url text nullable, status enum, voice_score jsonb nullable, rejection_reason text nullable, scheduled_at timestamptz nullable, image_regen_count int default 0, created_at, updated_at); `jobs` (id uuid PK, campaign_id FK nullable, job_type, status, scheduled_at timestamptz nullable, started_at timestamptz nullable, completed_at timestamptz nullable, attempt_count int default 0, error_details text nullable, created_at); `generation_logs` (id uuid PK, user_id FK, campaign_id FK, gemini_tokens int nullable, replicate_count int nullable, created_at).

**Given** `backend/.env.example` is reviewed,
**When** the file is read,
**Then** all required environment variables are documented with descriptive comments: `DATABASE_URL`, `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `GEMINI_API_KEY`, `REPLICATE_API_TOKEN`, `SENTRY_DSN`, `RESEND_API_KEY`, `APP_URL`.

**Given** the FastAPI app is started with `uvicorn app.main:app`,
**When** `GET /api/v1/health` is called,
**Then** it responds with HTTP 200 and `{"status": "ok"}`; CORS is configured with `allow_origins=[APP_URL]`, `allow_credentials=True`; all routes are prefixed `/api/v1/`; Sentry SDK is initialized with the `SENTRY_DSN` env var.

**Given** `deploy.sh` is reviewed,
**When** the file is read,
**Then** it SSHes to the configured Droplet IP, runs `git pull origin main`, `pip install -r requirements.txt`, `alembic upgrade head`, and `sudo systemctl restart personnapress-api` in sequence.

---

### Story 1.2: User Registration

As a new user,
I want to create an account with my email and password or sign up via Google,
So that I can access PersonnaPress and begin building my content workflow.

**Acceptance Criteria:**

**Given** an unregistered user submits the registration form with a valid email and password (minimum 8 characters),
**When** the `POST /api/v1/auth/register` request is processed,
**Then** a `users` record is created with `verified=false` and `hashed_password` set via bcrypt; a `subscriptions` record is created with `plan_tier='growth'` and `status='trialing'` (14-day trial); a verification email is sent via Resend containing a signed, time-limited verification link; and the UI displays "Check your email to verify your account." in calm Paper Style copy with no exclamation mark.
**And** the password is hashed in FastAPI only — it is never stored in plaintext or processed in Next.js.

**Given** an already-registered email is submitted,
**When** the registration form is submitted,
**Then** the API returns a generic error message: "An account with this email already exists." — the response does not reveal whether the email has a verified account or a pending-verification account.

**Given** an unverified user attempts to navigate to any `(app)/` route,
**When** Next.js middleware evaluates their JWT (if present),
**Then** they are redirected to `/verify-email` with instructions to check their inbox; a "Resend verification email" link is available that calls `POST /api/v1/auth/resend-verification`.

**Given** a user clicks the email verification link,
**When** the token is valid and unexpired,
**Then** `POST /api/v1/auth/verify-email` sets `users.verified=true`, issues a JWT (payload: `user_id`, `email`, `plan_tier`, `exp`), sets the JWT as an httpOnly cookie (secure=True, samesite=lax, 7-day expiry), and redirects the user to `/onboarding` (the first-login flow placeholder, to be fully implemented in Epic 2).
**And** if the token is expired, the API returns "Verification link expired — request a new one." with a resend option.

**Given** a new user clicks "Sign up with Google" on the registration page,
**When** they complete the Google OAuth consent screen and are returned to `/api/auth/google/callback`,
**Then** the Next.js route exchanges the auth code for a Google profile server-side, calls `POST /api/v1/auth/google` with the verified profile, FastAPI creates or finds the user record (setting `google_sub`, `verified=true`, skipping email verification), issues a JWT cookie, and redirects the user to `/onboarding`.

**Given** the registration page is rendered,
**When** a screen reader navigates the form,
**Then** all fields have visible labels (not placeholder-only), error messages are associated via `aria-describedby`, and the "Sign up with Google" button has an accessible label.

---

### Story 1.3: User Login & Session Management

As a registered user,
I want to log in with my email and password or via Google and stay authenticated across browser sessions,
So that I can access PersonnaPress without re-authenticating every visit.

**Acceptance Criteria:**

**Given** a verified user submits valid email and password credentials,
**When** `POST /api/v1/auth/login` is processed,
**Then** FastAPI verifies the password with bcrypt, issues a JWT (payload: `user_id`, `email`, `plan_tier`, `exp`), sets it as an httpOnly cookie (secure=True, samesite=lax, 7-day expiry), and Next.js redirects the user to `/dashboard`.

**Given** a user submits an incorrect email or password,
**When** the login form is submitted,
**Then** a generic error message is returned: "Invalid email or password." — no indication of which field is incorrect, and no lockout in v1.

**Given** an unverified user attempts to log in with email/password,
**When** the form is submitted,
**Then** the API returns "Please verify your email before logging in." with a "Resend verification email" link.

**Given** a logged-in user closes and reopens the browser within 7 days,
**When** they visit any `(app)/` route,
**Then** Next.js middleware reads the httpOnly cookie, validates the JWT using the `jose` library (edge-runtime compatible), extracts `plan_tier` from the payload, and grants access — no re-login required.

**Given** Next.js middleware validates the JWT,
**When** the middleware runs on the Vercel edge runtime,
**Then** it uses `jose` for JWT verification (not a Node.js-only library), and the `JWT_SECRET` is read from a server-side environment variable only (never `NEXT_PUBLIC_`).

**Given** a logged-in user visits `/login` or `/register`,
**When** middleware detects a valid JWT cookie,
**Then** the user is immediately redirected to `/dashboard` — authenticated users are never shown the login/register pages.

**Given** a logged-in user clicks "Log out,"
**When** the logout action completes (`POST /api/v1/auth/logout`),
**Then** the httpOnly cookie is cleared (set to empty string with immediate expiry), the user is redirected to `/login`, and the prior session JWT cannot be reused for authenticated requests.

**Given** a returning Google OAuth user clicks "Sign in with Google,"
**When** the OAuth flow completes,
**Then** the same user record is found via `google_sub`, a new JWT cookie is issued, and they are redirected to `/dashboard`.

---

### Story 1.4: Protected App Shell & Responsive Navigation

As an authenticated user,
I want a persistent navigation shell with sidebar and responsive layout that adapts to my device,
So that I can navigate the application from any surface and always know my current context.

**Acceptance Criteria:**

**Given** an authenticated user visits any `(app)/` route,
**When** the page renders,
**Then** the full app shell is displayed: Paper-background sidebar (240px wide on lg, 1px right border, no shadow); logo and product name in the sidebar header; primary nav links — Dashboard, Clients, Calendar; account link pinned to sidebar bottom; client switcher placeholder in the sidebar header (shows "No clients yet — add one" until Epic 2 populates it); main content area with 720px max-width and correct horizontal padding (32px tablet, 48px desktop).

**Given** a viewport at 1024px or wider (lg),
**When** the app shell renders,
**Then** the full 240px sidebar is visible and persistent; page content renders at 720px max-width within the content pane.

**Given** a viewport between 768px and 1023px (md),
**When** the app shell renders,
**Then** the sidebar collapses to 56px icon-only width showing only nav icons; tooltips appear on icon hover; the content area expands to fill the remaining width.

**Given** a viewport below 768px,
**When** the app shell renders,
**Then** no sidebar is visible; instead a top bar is shown with logo, hamburger menu icon, and active client name; tapping the hamburger opens a slide-in drawer with the full nav links; the drawer can be closed by tapping outside it or pressing Esc.

**Given** the app shell is rendering,
**When** the initial data fetch is in progress,
**Then** skeleton placeholders matching the shape of sidebar nav links (3 rectangular blocks at correct heights) are shown — not a spinner — until the layout is ready.

**Given** a screen reader navigates the app shell,
**When** the user tabs through the interface,
**Then** the page announces "[Surface Name] — PersonnaPress" on navigation; all nav items are reachable via Tab with visible focus indicators (Highlighter-colored border); Tab order matches visual DOM reading order; there are no tab traps outside of modal/dialog contexts.

**Given** the active navigation item,
**When** it is rendered,
**Then** it displays Highlighter background (#FFF1B8), Ink text (#111111), and a 2px left border in Ink; all inactive items display Graphite (#555555) labels with Highlighter background and Ink text on hover.

**Given** all interactive elements in the app shell,
**When** measured for touch target size,
**Then** each has a minimum height and width of 44px to meet WCAG 2.2 AA touch target requirements.

---

### Story 1.5: Account & Subscription Management

As an authenticated user,
I want to view my current plan details and usage, and access the Stripe billing portal to manage my subscription,
So that I understand what I have access to and can upgrade, downgrade, or cancel when needed.

**Acceptance Criteria:**

**Given** an authenticated user navigates to `/account`,
**When** the page loads,
**Then** it displays: current plan tier name (Starter / Growth / Agency), campaigns used vs. plan limit for the current billing cycle, clients count vs. plan limit, image generations used vs. plan limit, subscription renewal date formatted with `Intl.DateTimeFormat` in the user's locale, and a "Manage subscription" button.

**Given** a user on any plan clicks "Manage subscription,"
**When** the button is clicked,
**Then** Next.js calls `POST /api/v1/subscriptions/portal` which creates a Stripe Customer Portal session using the user's `stripe_customer_id` and returns the portal URL; Next.js redirects the user to the Stripe-hosted portal page in the same tab.

**Given** Stripe fires a `customer.subscription.updated` webhook event,
**When** the Next.js webhook route at `/api/webhooks/stripe` receives it,
**Then** the route validates the Stripe webhook signature using `STRIPE_WEBHOOK_SECRET`; forwards the event payload to FastAPI `POST /api/v1/webhooks/stripe`; FastAPI updates `subscriptions.plan_tier`, `subscriptions.status`, `subscriptions.billing_cycle_start`, and `subscriptions.billing_cycle_end` accordingly.

**Given** Stripe fires a `customer.subscription.deleted` webhook event,
**When** the event is processed,
**Then** `subscriptions.status` is set to `'canceled'` and the user enters the trial-expiry restricted state on their next session (full enforcement implemented in Epic 7).

**Given** a user has used 8 of their 10 Starter plan campaigns this billing cycle,
**When** they view the account page,
**Then** the usage display shows "8 / 10 campaigns this billing cycle" in Graphite text — no warning banner appears until the limit is actually reached (limit-contact triggers are handled in Epic 7).

**Given** a user upgrades from Starter to Growth via the Stripe portal,
**When** the `customer.subscription.updated` webhook confirms the change,
**Then** `subscriptions.plan_tier` is updated to 'growth' and all subsequent tier-limit checks reflect the new Growth limits (5 clients, 30 campaigns, 30 image generations) immediately.

**Given** the Account page is viewed,
**When** all data fields are rendered,
**Then** all copy follows Paper Style microcopy rules: no exclamation marks, dates are human-readable ("Renews July 14, 2026"), usage is direct and factual — no progress bars or gamification in v1.

---

## Epic 2: Client Management & Brand Voice Ingestion

A user can create and manage Client profiles (brand identities), trigger website scraping to automatically extract a Brand Voice Profile, upload supplementary content files, or complete a manual voice questionnaire as a fallback. They can edit, refresh, or delete Clients, and switch active context between multiple Clients in the sidebar. A 3-step onboarding flow guides new users through creating their first client and setting up brand voice on first login.

### Story 2.1: Create Client

As an authenticated user,
I want to create a Client profile with a name and optional website URL,
So that I have a brand identity to generate content for.

**Acceptance Criteria:**

**Given** an authenticated user clicks "New Client" on the Clients page,
**When** they submit the form with a valid client name,
**Then** `services/subscription.py` is called first to verify the user has not reached their plan's client count limit; if within limit, a `clients` record is created with `user_id` set to the authenticated user and `brand_voice_profile=null`; the user is navigated to the new client's detail page at `/clients/{id}`.

**Given** a website URL is provided in the Create Client form,
**When** the form is submitted,
**Then** a `jobs` record is created with `job_type='ingestion'` and `status='pending'` before dispatching the BackgroundTask; the ingestion BackgroundTask is queued in `workers/ingest.py`; the client detail page immediately shows "Analyzing [url]..." in JetBrains Mono label type.

**Given** the user's subscription plan client count limit has been reached,
**When** the Create Client form is submitted,
**Then** `services/subscription.py` returns a limit error, the API responds with HTTP 400, and the UI displays: "You've reached your [N]-client limit on the [Plan] plan. Upgrade to [next tier] for up to [M] clients." with an upgrade CTA that opens the Stripe Customer Portal.
**And** no `clients` record is created.

**Given** the client name field is empty,
**When** the form is submitted,
**Then** client-side validation shows an inline error below the field: "Client name is required." and the form does not submit to the API.

**Given** a client is successfully created without a URL,
**When** the client detail page loads,
**Then** the Brand Voice Profile section shows "No voice profile yet. Upload content or complete the voice questionnaire." with CTAs to both options.

---

### Story 2.2: Edit & Delete Client

As an authenticated user,
I want to update a client's name and website URL, and permanently delete a client I no longer need,
So that my client list stays accurate and outdated clients do not clutter my workspace.

**Acceptance Criteria:**

**Given** a user edits the client name on the Client detail page and clicks "Save changes,"
**When** `PATCH /api/v1/clients/{client_id}` is called,
**Then** the `clients.name` is updated; the sidebar client switcher and any other displays of the client name reflect the new name immediately.

**Given** a user changes the website URL on the Client detail page,
**When** they click "Save changes,"
**Then** a confirmation dialog appears: "Updating the website URL will re-analyze [domain]. This will overwrite your current voice profile. Continue?" with a "Re-analyze" primary button and a "Cancel" secondary button.

**Given** the user confirms the URL change,
**When** they click "Re-analyze,"
**Then** `clients.brand_voice_profile` is set to null, `clients.website_url` is updated, and a new ingestion `jobs` record is created before a new ingestion BackgroundTask is dispatched; the UI transitions to the ingestion-in-progress state.

**Given** a user clicks "Delete client" on a Client detail page,
**When** the delete action is initiated,
**Then** a confirmation dialog appears with the exact text: "Delete '[Client Name]'? This will remove [N] campaigns and all platform connections." where N is the actual campaign count; the confirm button is styled as Danger (dark red fill) and labeled "Delete client"; a "Cancel" secondary button is present.

**Given** the user confirms client deletion,
**When** `DELETE /api/v1/clients/{client_id}` is processed,
**Then** the client record and all associated `campaigns`, `platform_connections`, and the `brand_voice_profile` JSON are cascade-deleted from the database; if the deleted client was the active client in `useClientStore`, the next remaining client is set as active, or the empty-clients state is shown if none remain; the user is redirected to `/clients`.

**Given** a user attempts to edit or delete a client they do not own,
**When** any PATCH or DELETE request is made with that `client_id`,
**Then** the API returns HTTP 403 Forbidden — ownership is verified by comparing `clients.user_id` to the JWT `user_id`.

---

### Story 2.3: Client List & Active Context Switching

As an authenticated user,
I want to view all my clients and switch which client is active in my workspace,
So that I can manage content for multiple brands without confusion about which context I am working in.

**Acceptance Criteria:**

**Given** an authenticated user navigates to `/clients`,
**When** the page loads,
**Then** all clients owned by the user are displayed as cards showing: client name, website URL (if set), Brand Voice Profile status ("Voice profile ready" / "Profile incomplete" / "Analyzing..."), and the number of campaigns associated with that client.

**Given** a user clicks the Client Switcher dropdown in the sidebar header,
**When** the dropdown opens,
**Then** all client names are listed alphabetically; the currently active client is marked with a checkmark; if no clients exist, the dropdown shows "No clients yet." with a "Create client" link to `/clients/new`.

**Given** a user selects a different client from the Client Switcher,
**When** the selection is made,
**Then** `useClientStore.setActiveClientId` is updated with the new client ID; the user is navigated to `/dashboard` which reloads campaign history, Brand Voice Profile status, and Platform Connection status for the newly active client; the sidebar switcher label updates to the selected client name.

**Given** an authenticated user logs in and has at least one client,
**When** the app shell initializes,
**Then** the most recently active client ID (stored in localStorage) is restored into `useClientStore` as the active client.

**Given** a user with no clients lands on `/dashboard`,
**When** the page renders,
**Then** an empty state is displayed: "No clients yet." as an H2, body text "Create a client to start generating content.", and a "Create your first client" primary CTA — no campaign rows or list skeleton.

**Given** a user on the Growth plan (5-client limit) already has 5 clients and views `/clients`,
**When** the page renders,
**Then** no "New Client" button is shown; instead, a text message reads "You've reached the 5-client limit on your Growth plan." with an "Upgrade to Agency" link.

---

### Story 2.4: Brand Voice Ingestion — Website Scraping & Content Upload

As an authenticated user,
I want the system to scrape my website and accept uploaded content files to gather writing samples,
So that PersonnaPress has enough of my writing to accurately learn my voice.

**Acceptance Criteria:**

**Given** a client with a website URL has an ingestion job queued,
**When** the BackgroundTask executes in `workers/ingest.py`,
**Then** `services/ingestion.py` uses httpx to fetch the website; BeautifulSoup is used to extract clean text from blog posts, about pages, and long-form pages; navigation menus, footers, sidebars, cookie banners, and ad containers are stripped; at least the 10 most recent blog posts are extracted, or all posts if fewer than 10 exist.

**Given** the website scraping completes successfully,
**When** the extracted text is ready,
**Then** it is passed in-memory to the voice extraction function (Story 2.5) within the same BackgroundTask — it is not stored as a separate database record.

**Given** the website URL is unreachable, returns a non-200 response, or scraping times out after 60 seconds,
**When** the failure occurs,
**Then** the `jobs` record is updated to `status='failed'` with descriptive `error_details`; `clients.brand_voice_profile` remains null; the client UI shows: "Couldn't extract content from [url]. Complete the voice questionnaire to set up your profile." with a primary CTA to the voice questionnaire.

**Given** a user navigates to the Client detail page and clicks "Upload content files,"
**When** they select up to 10 files (.txt, .md, or .docx, each no larger than 5 MB),
**Then** each file is uploaded to Supabase Storage at path `brand-content/{client_id}/{filename}`; upload progress is shown per file; upon completion the file list is displayed with file names and sizes.

**Given** a user attempts to upload a file larger than 5 MB or in an unsupported format,
**When** the file is selected,
**Then** the frontend validates the file before initiating upload and shows an inline error: "File must be under 5 MB." or "Only .txt, .md, and .docx files are supported." — the upload is not initiated.

**Given** uploaded files exist for a client alongside scraped content,
**When** the ingestion BackgroundTask processes voice extraction,
**Then** text is extracted from each file (.txt/.md read directly; .docx parsed via python-docx), and the extracted file text is appended to scraped website text before being passed to Gemini for voice extraction.

---

### Story 2.5: Voice Profile Extraction, Review & Manual Questionnaire

As an authenticated user,
I want the system to analyze my collected content and produce an editable Brand Voice Profile — or guide me through a questionnaire if no content is available — so that all generated content sounds authentically like me.

**Acceptance Criteria:**

**Given** collected content (scraped website text and/or uploaded file text) is available in the ingestion BackgroundTask,
**When** voice extraction runs,
**Then** `integrations/gemini.py` is called with the full collected text and a 1024 thinking token budget; Gemini 2.5 Flash returns a structured Brand Voice Profile containing: `tone` (array of descriptor strings), `cadence` (object: avg_sentence_length int, variation_pattern string, paragraph_structure string), `banned_jargon` (array of strings).
**And** `clients.brand_voice_profile` is updated with the returned JSON; the `jobs` record is set to `status='complete'`.

**Given** voice extraction completes successfully,
**When** the Client Voice Setup page at `/clients/{id}/voice` is loaded,
**Then** the extracted profile fields are pre-populated for user review: tone descriptors displayed as editable tags (add/remove); banned jargon listed as editable tags (add/remove); cadence fields shown with their values and editable text inputs; a "Confirm profile" primary CTA is present.

**Given** a user edits fields in the Brand Voice Profile review and clicks "Confirm profile,"
**When** the save action runs,
**Then** `PATCH /api/v1/clients/{client_id}` updates `clients.brand_voice_profile` with the edited JSON; a success message shows: "Voice profile confirmed." — no exclamation mark, Paper Style tone.

**Given** the Gemini voice extraction call fails or returns a 5xx/429 error after 3 consecutive retries,
**When** the failure is confirmed,
**Then** the `jobs` record is set to `status='failed'` with `error_details` populated; the error is logged to Sentry; the client UI shows: "Voice profile extraction failed. Complete the questionnaire to set up your profile manually." with a primary CTA to the voice questionnaire.

**Given** no website content is available (no URL provided, scraping failed, or no files uploaded),
**When** the user accesses the Brand Voice Setup page,
**Then** the voice questionnaire (FR-10 fallback) is shown instead of an extraction result — the UI transitions directly to the questionnaire flow without showing an error.

**Given** a client with no voice profile and the user submits the voice questionnaire (three steps: tone sliders, sample text pastes, optional reference URLs),
**When** the questionnaire is submitted,
**Then** a `jobs` record is created before dispatch; a BackgroundTask calls Gemini 2.5 Flash with a 1024 thinking token budget passing slider values (converted to tone descriptors), sample texts (if provided), and reference writer URLs (if provided); the UI shows "Extracting your voice profile..." in JetBrains Mono label type.

**Given** the questionnaire wizard,
**When** it is rendered,
**Then** Step 1 shows three paired tone slider pairs (Formal↔Casual 1–5, Professional↔Friendly 1–5, Concise↔Elaborate 1–5); Step 2 shows up to 3 textarea fields labeled "Paste a piece of writing that sounds like you." (all optional); Step 3 (optional) shows up to 3 URL input fields labeled "A writer whose style you admire." with a "Skip this step" secondary link; each step shows a progress indicator ("Step 1 of 3"), "Back" (except Step 1), and "Next" buttons; the final step has "Submit questionnaire" as the primary CTA.
**And** each slider pair has an accessible aria-label identifying both ends of the scale and the current numeric value is announced to screen readers.

---

### Story 2.6: Voice Profile Refresh

As an authenticated user,
I want to trigger a fresh voice analysis using my latest website content or new uploads,
So that my Brand Voice Profile stays current as my writing style evolves.

**Acceptance Criteria:**

**Given** a user with an existing Brand Voice Profile visits `/clients/{id}/voice`,
**When** the page renders,
**Then** the profile fields are displayed with their current values alongside a "Refresh voice profile" secondary button.

**Given** a user clicks "Refresh voice profile,"
**When** the button is clicked,
**Then** a confirmation dialog appears: "Re-analyzing [Client Name]'s voice profile will overwrite the current profile. This cannot be undone. Continue?" with a "Re-analyze" primary button and a "Cancel" secondary button.

**Given** the user confirms the refresh,
**When** `POST /api/v1/clients/{client_id}/ingest` is called,
**Then** `clients.brand_voice_profile` is set to null; a new `jobs` record is created with `job_type='ingestion'` and `status='pending'` before dispatch; a new ingestion BackgroundTask is queued; the UI immediately transitions to the ingestion-in-progress state showing "Scraping [url]..." or the questionnaire if no URL is set.
**And** the previous Brand Voice Profile is permanently overwritten — there is no version history in v1.

**Given** the refreshed ingestion completes,
**When** Gemini returns the new profile,
**Then** `clients.brand_voice_profile` is updated with the new JSON; the profile review page shows the updated fields pre-populated for confirmation; the user must click "Confirm profile" to finalize.

---

### Story 2.7: 3-Step Onboarding Flow

As a newly registered user,
I want a guided onboarding flow that walks me through creating my first client and setting up my brand voice,
So that I can go from sign-up to content-ready as quickly as possible without needing to discover these steps on my own.

**Acceptance Criteria:**

**Given** a user logs in for the first time (post-registration, email verified or Google OAuth),
**When** they are redirected post-authentication,
**Then** they land on `/onboarding` (Step 1) instead of `/dashboard`; the app shell sidebar is not shown — a clean centered card layout on a Paper background is used instead; a skip link is available.

**Given** Step 1 of onboarding renders,
**When** the page loads,
**Then** it shows: Playfair Display H1 "Who are you writing for?"; body text "A Client is the brand voice you're building. Start with yours."; a required "Client name" field; an optional "Website URL" field with label "Recommended — for automatic voice setup"; primary CTA "Create client and analyze voice"; skip link below the CTA: "Skip for now — I'll set this up later."

**Given** the user submits Step 1 with a website URL,
**When** "Create client and analyze voice" is clicked,
**Then** a client is created, an ingestion job is created and dispatched (as per Story 2.1), and Step 2 loads showing the ingestion-in-progress state: "Scraping [url]..." → "Extracting voice profile..." in JetBrains Mono; when extraction completes, the extracted Brand Voice Profile fields are shown for review.

**Given** the user submits Step 1 without a website URL,
**When** "Create client and analyze voice" is clicked,
**Then** the client is created (no ingestion dispatched) and Step 2 loads showing the voice questionnaire (as per Story 2.5) instead of the ingestion progress state.

**Given** Step 2 of onboarding renders,
**When** the page loads,
**Then** a progress indicator shows "2 of 3" at the top; a skip link reads "Skip — I'll refine this later" which advances to Step 3 with the profile flagged as incomplete.

**Given** Step 3 of onboarding renders,
**When** the page loads,
**Then** it shows: progress indicator "3 of 3"; Playfair H2 "What's on your mind this week?"; subtext "Paste anything — bullet points, half-formed thoughts, a topic title. PersonnaPress will do the rest."; the Brain Dump textarea (full width, JetBrains Mono, min 200px height); primary CTA "Generate my first campaign"; skip link "I'll write my first draft later" which navigates to `/dashboard` with a "Complete your first campaign" nudge card.
**And** submitting the Brain Dump in Step 3 triggers the same campaign creation flow as Epic 3 Story 3.1; Step 3 submission integration is wired in Epic 3 Story 3.5 — this story implements the onboarding shell and Step 3 UI only.

**Given** a user clicks any skip link,
**When** they are taken to the next step or Dashboard,
**Then** the skipped step does not block future access — brand voice setup and brain dump remain accessible from the Client detail page and Dashboard at any time.

**Given** a returning user (not their first login) visits `/onboarding`,
**When** the route is accessed,
**Then** Next.js middleware redirects them to `/dashboard` — the onboarding flow is shown exactly once per account.

---

## Epic 3: Brain Dump & Content Generation

A user can submit a Brain Dump (free-form text input) and receive a fully generated Campaign — an SEO-structured blog post, an X post, a LinkedIn post, and a featured image — all written in the active Client's Brand Voice. Real-time generation status feedback via typewriter animation keeps the user informed. A persistent job record tracks the entire async pipeline through any backend restart. Voice fidelity is scored as an advisory check after blog generation.

### Story 3.1: Brain Dump Input & Campaign Creation

As an authenticated user,
I want to type or paste my raw idea into a Brain Dump input and submit it to start content generation,
So that I can kick off the full content pipeline from a rough thought in seconds.

**Acceptance Criteria:**

**Given** an authenticated user navigates to `/dashboard/new` (or clicks "New Campaign" from Dashboard),
**When** the page loads,
**Then** a Brain Dump input page is shown: a full-width JetBrains Mono auto-expanding textarea with a subtle bottom border; a character counter below reads "0 / 10,000 characters"; a "Generate campaign" primary button is present and disabled until the minimum character threshold is met.

**Given** the user types fewer than 20 characters in the Brain Dump textarea,
**When** they attempt to click "Generate campaign,"
**Then** the submit button remains disabled; an inline counter message below the textarea reads "N / 10,000 characters" and turns Danger color when below 20 characters to signal the minimum has not been met.

**Given** the user has typed at least 20 characters and clicks "Generate campaign,"
**When** the form is submitted,
**Then** `services/subscription.py` is called to verify the user has not reached their plan's campaign count limit for the current billing cycle; if within limit, `POST /api/v1/campaigns` is called with the brain dump text and active client ID.

**Given** the campaign count limit has been reached,
**When** the form is submitted,
**Then** the API returns HTTP 400 and the UI displays: "You've reached your [N]-campaign limit for this billing cycle. Upgrade to [next tier] for more campaigns." with an upgrade CTA — no Campaign record is created.

**Given** the subscription limit check passes,
**When** `POST /api/v1/campaigns` is processed by FastAPI,
**Then** a `campaigns` record is created with `status='pending_approval'`, `brain_dump` set to the submitted text, and `client_id` from the request; a `jobs` record is created with `job_type='generation'` and `status='pending'` before the BackgroundTask is dispatched; the API returns HTTP 202 with `{"campaign_id": "...", "job_id": "..."}`.

**Given** the 202 response is received by the frontend,
**When** it arrives,
**Then** Next.js navigates to `/campaigns/{campaign_id}` (the Approval Gate route) which immediately enters the generation-in-progress state with the job ID ready for polling (full typewriter UI implemented in Story 3.2).

**Given** the Enter key is pressed while focus is in the Brain Dump textarea,
**When** the key event fires,
**Then** the form does NOT submit — Enter inserts a newline; only the "Generate campaign" button submits the form; Cmd/Ctrl+Enter also submits as a power-user shortcut.

**Given** the user presses Esc while focus is in the Brain Dump textarea,
**When** the key event fires,
**Then** nothing happens — the textarea is not cleared; this prevents accidental loss of long inputs.

---

### Story 3.2: Generation Job Polling & Typewriter Animation

As an authenticated user,
I want to see real-time visual feedback while my content is being generated,
So that I know the system is working and can follow the progress through each stage of the pipeline.

**Acceptance Criteria:**

**Given** the user lands on `/campaigns/{id}` while the campaign's job status is `pending` or `in_progress`,
**When** the page renders,
**Then** the full content area is occupied by the typewriter animation component: character-by-character text reveal in JetBrains Mono on a Paper background; a status message line below cycles through: "Analyzing your voice profile..." → "Drafting blog post..." → "Checking voice fidelity..." → "Generating featured image..." → "Done." with each message appearing when the corresponding pipeline stage completes.

**Given** the typewriter animation is running,
**When** rendered for screen readers,
**Then** the character-reveal animation has `aria-hidden="true"`; the status message line has `aria-live="polite"` so each new status message is announced.

**Given** `prefers-reduced-motion` is enabled in the OS,
**When** the generation state is active,
**Then** the typewriter character-reveal animation is replaced by a simple "Generating..." text label with a pulsing opacity animation only — no character-by-character reveal.

**Given** React Query is polling the job status endpoint,
**When** the generation page is open,
**Then** `useJobStatus` hook calls `GET /api/v1/jobs/{job_id}` with `refetchInterval: 2000` while `job.status` is `'pending'` or `'in_progress'`; polling stops automatically when `job.status` reaches a terminal state (`'complete'` or `'failed'`).

**Given** the job reaches `status='complete'`,
**When** the polling detects the terminal state,
**Then** React Query invalidates the `["campaign", campaignId]` query key; the Approval Gate content (blog preview, social posts, image) loads in place of the typewriter animation (Approval Gate UI implemented in Epic 4).

**Given** the job reaches `status='failed'`,
**When** the polling detects failure,
**Then** the typewriter animation is replaced by an error state showing the `error_details` message (e.g., "Generation service temporarily unavailable.") with a "Retry generation" primary button that re-submits the same Brain Dump text to create a new Campaign and job.

**Given** the user attempts to navigate away from the generation page while polling is active,
**When** they click a nav link or browser back button,
**Then** a confirmation dialog appears: "Generation is in progress. Leaving will not cancel it — your draft will be available on the Dashboard when complete." with "Stay on page" and "Leave" options; if they choose Leave, navigation proceeds and polling stops on this page, but the job continues server-side.

---

### Story 3.3: Blog & Social Content Generation Pipeline

As a developer,
I want the BackgroundTask generation worker to call Gemini 2.5 Flash to produce the blog post, run the voice fidelity check, and generate social posts — all persisted to the Campaign record,
So that submitted Brain Dumps produce complete, voice-aligned text content that the Approval Gate can display.

**Acceptance Criteria:**

**Given** a generation BackgroundTask is dispatched with a `job_id`,
**When** `workers/generate.py` executes,
**Then** it fetches the `jobs` record by `job_id`, sets `jobs.status='in_progress'` and `jobs.started_at=now()`, fetches the associated `campaigns` record and the client's `brand_voice_profile`; all operations happen in this order with no business logic in the router.

**Given** the blog generation step runs,
**When** `services/generation.py` calls `integrations/gemini.py` via `generate_blog()`,
**Then** Gemini 2.5 Flash is called with the brain dump text, brand voice profile JSON, and a 512 thinking token budget; the prompt instructs the model to produce a semantic HTML blog post (H1 title, meta description in a comment, H2/H3 headings, body paragraphs, conclusion) targeting 800–1,500 words, conforming to the tone, cadence, and banned jargon in the voice profile.

**Given** the blog generation call succeeds,
**When** the HTML is returned,
**Then** the voice fidelity check runs: `integrations/gemini.py` via `check_fidelity()` is called with the blog HTML and brand voice profile using a 256 thinking token budget; the response is a JSON object containing `tone_score` (0–10), `cadence_score` (0–10), and `jargon_violations` (int); `campaigns.voice_score` is updated with this JSON.

**Given** the social post generation step runs after blog generation,
**When** `services/generation.py` calls `integrations/gemini.py` via `generate_social()`,
**Then** Gemini 2.5 Flash is called with the brain dump text, brand voice profile, blog title, and a 0 thinking token budget; the prompt instructs the model to produce: an X post (text only, ≤280 characters) and a LinkedIn post (500–1,300 characters with line breaks for readability) that reference and tease the blog content without duplicating it.

**Given** text generation completes (blog + voice check + social posts),
**When** all calls succeed,
**Then** `campaigns.blog_html`, `campaigns.voice_score`, `campaigns.x_post`, and `campaigns.linkedin_post` are all updated in a single database write; the `jobs` record status remains `'in_progress'` pending image generation (Story 3.4).

**Given** any Gemini API call returns a 5xx or 429 error,
**When** it happens on the 3rd consecutive retry attempt,
**Then** `jobs.status` is set to `'failed'`, `jobs.error_details` is set to "Generation service temporarily unavailable — retry in a few minutes", `campaigns.status` remains `'pending_approval'` (not failed — the campaign can be retried from the same brain dump); the error is logged to Sentry.

**Given** `services/generation.py` is the execution context for all Gemini calls,
**When** any Gemini call is made,
**Then** `integrations/gemini.py` functions are called only from within `services/generation.py` — never directly from routers or workers; this is the only location where Gemini API calls originate.

---

### Story 3.4: Featured Image Generation & Regeneration

As an authenticated user,
I want the system to automatically generate a featured image for my blog post and let me regenerate it if the first result does not fit my brand,
So that my published posts include a custom, on-brand visual with no extra effort.

**Acceptance Criteria:**

**Given** text generation (blog + social) has completed successfully in the BackgroundTask,
**When** the image generation step runs,
**Then** `services/image.py` calls `integrations/replicate.py` via `generate_image()` with a prompt derived from the blog post H1 title and a style directive aligned with the Client's brand tone; `integrations/replicate.py` calls the FLUX.1 [pro] model on Replicate with dimensions 1200×630 (Open Graph dimensions).

**Given** `services/subscription.py` checks image generation quota before the Replicate call,
**When** the image generation count limit for the billing cycle has been reached,
**Then** the image generation is skipped; `campaigns.image_url` remains null; the Approval Gate shows "Image generation limit reached for this billing cycle." with an upgrade CTA — the Campaign still proceeds to `complete` status.

**Given** image generation succeeds,
**When** Replicate returns the image URL,
**Then** `integrations/supabase_storage.py` downloads the image and re-uploads it to Supabase Storage at path `generated-images/{campaign_id}/featured.png`; `campaigns.image_url` is set to the CDN public URL; `generation_logs` is appended with `replicate_count=1` for the user; the `jobs` record is set to `status='complete'` and `jobs.completed_at=now()`.

**Given** image generation fails (Replicate API error after 3 retries),
**When** the failure is confirmed,
**Then** `campaigns.image_url` remains null; `jobs.status` is set to `'complete'` (not failed) with `error_details` noting the image failure; the Campaign proceeds — the Approval Gate shows "Image generation failed." with a "Generate image" button that triggers a standalone retry.

**Given** a user in the Approval Gate clicks "Regenerate" on the image panel,
**When** the request is made via `POST /api/v1/campaigns/{id}/image/regenerate`,
**Then** `services/subscription.py` checks the image generation quota; if within limit, `campaigns.image_regen_count` is checked: if already at 3, the API returns HTTP 400 and the button is disabled showing "0 regenerations remaining"; if below 3, a new Replicate call is made, `campaigns.image_regen_count` is incremented, the previous Supabase Storage image is replaced, and `campaigns.image_url` is updated.

**Given** `services/image.py` is the execution context for all Replicate calls,
**When** any image generation or regeneration occurs,
**Then** `integrations/replicate.py` is called only from within `services/image.py` — no other service, worker, or router calls Replicate directly.

---

### Story 3.5: Onboarding Step 3 Completion & Generation Integration

As a new user completing onboarding,
I want the "Generate my first campaign" button in onboarding Step 3 to kick off the same full content generation pipeline as the main Brain Dump flow,
So that my onboarding experience leads directly to my first real Campaign without any context switch.

**Acceptance Criteria:**

**Given** a user on onboarding Step 3 enters a Brain Dump (≥20 characters) and clicks "Generate my first campaign,"
**When** the CTA is clicked,
**Then** the same Campaign creation flow runs as Story 3.1: `services/subscription.py` limit check → `POST /api/v1/campaigns` → `campaigns` record + `jobs` record created → BackgroundTask dispatched → 202 response received; the user is navigated to `/campaigns/{campaign_id}` showing the typewriter generation state (Story 3.2).

**Given** the Campaign generated from onboarding completes,
**When** the typewriter animation reaches "Done.",
**Then** the Approval Gate loads for the campaign (Epic 4), and the onboarding flow is considered complete — subsequent logins redirect directly to `/dashboard`, not `/onboarding`.

**Given** the user clicks "I'll write my first draft later" (skip link on Step 3),
**When** they are redirected to `/dashboard`,
**Then** a nudge card appears at the top of the campaign list: "Complete your first campaign" with a "New Campaign" CTA — this nudge is shown until the user creates their first Campaign, then disappears.

**Given** the onboarding completion state,
**When** it is persisted,
**Then** a `users.onboarding_completed` boolean field (added via Alembic migration) is set to `true` when the user either submits their first Brain Dump from onboarding Step 3 OR explicitly skips Step 3; this flag gates the onboarding redirect in Next.js middleware.

---

## Epic 4: Approval Gate & Content Review

A user can view a full preview of all Campaign content — rendered blog HTML, social posts, and featured image — edit the blog post via WYSIWYG, edit social posts with live character counters, see an advisory voice fidelity score, and approve or reject the Campaign before publishing. The Approval Gate's state machine UI adapts to each Campaign lifecycle state.

### Story 4.1: Approval Gate — Campaign Preview & Voice Fidelity Badge

As an authenticated user,
I want to view a complete, rendered preview of my generated Campaign content in the Approval Gate,
So that I can read and evaluate everything before deciding to approve or reject.

**Acceptance Criteria:**

**Given** a user navigates to `/campaigns/{id}` with a Campaign in `pending_approval` status,
**When** the Approval Gate page loads,
**Then** the full campaign content is displayed: the blog post rendered as HTML (left panel at lg breakpoint; full-width on md and below); the X post and LinkedIn post in their respective preview panels (right panel at lg, below blog at md and below); the featured image at full panel width; a sticky footer with "Approve" primary button and "Reject" secondary button; both footer buttons are always visible.

**Given** the blog HTML preview renders,
**When** DOMPurify sanitizes the HTML before display,
**Then** any script tags, event handlers, or unsafe attributes in the blog HTML are stripped; the sanitized HTML is rendered with `@tailwindcss/typography` prose styles to match the paper aesthetic.

**Given** the Campaign has a `voice_score` JSON with `tone_score < 7` OR `cadence_score < 6` OR `jargon_violations > 0`,
**When** the Approval Gate header renders,
**Then** a Voice Fidelity Badge is shown: Danger-colored uppercase tracked Inter label reading "VOICE MATCH: [N]/10 — REVIEW TONE" (tone score shown); clicking the badge expands an inline detail panel showing all three dimensions: "Tone: [N]/10", "Cadence: [N]/10", "Jargon violations: [N]"; the badge and panel are advisory only — they do not disable the Approve button.

**Given** the Campaign's `voice_score` has `tone_score >= 7`, `cadence_score >= 6`, and `jargon_violations = 0`,
**When** the Approval Gate header renders,
**Then** no Voice Fidelity Badge is shown — a passing score produces no visual noise.

**Given** the Approval Gate at lg (≥1024px) breakpoint,
**When** the layout renders,
**Then** the blog WYSIWYG panel occupies approximately 60% of the content width (left); the right panel contains social post editors, the featured image panel, voice score badge (if applicable), and the sticky action footer stacked vertically.

**Given** the Approval Gate at md or below breakpoint,
**When** the layout renders,
**Then** all panels stack in a single column: blog first, then social posts, then featured image, then the action footer; the sticky footer remains fixed at the bottom of the viewport.

**Given** a user navigates to an Approval Gate for a Campaign they do not own,
**When** the page loads,
**Then** the API returns HTTP 403 and the frontend shows a "Not found" error state — no Campaign content is displayed.

---

### Story 4.2: Blog Post WYSIWYG Editing

As an authenticated user,
I want to edit the generated blog post directly in the Approval Gate preview before approving,
So that I can fix any sentences that are off-brand without leaving the review flow.

**Acceptance Criteria:**

**Given** the blog post panel in the Approval Gate,
**When** it is in editable mode (default for `pending_approval` Campaigns),
**Then** the rendered HTML is loaded into a Tiptap editor instance (`@tiptap/react` + `@tiptap/starter-kit` + `@tiptap/extension-link`) via `editor.setContent(blog_html_string)` on mount; the editor toolbar shows: Bold, Italic, Link, H2, H3, Blockquote, Undo; no raw HTML toggle is shown in v1.

**Given** the Tiptap editor is initialized,
**When** the user edits content (types, formats, deletes),
**Then** all edits are reflected immediately in the editor; the toolbar buttons respond to the current selection (Bold button appears active when cursor is within bold text, etc.).

**Given** the user has made edits and clicks "Save edits" (or the edits are auto-saved on the approve action),
**When** the save occurs,
**Then** `editor.getHTML()` is called to extract the current HTML string; `PATCH /api/v1/campaigns/{id}` is called with `{"blog_html": "<html string>"}` updating `campaigns.blog_html`; the saved HTML overwrites the original generated content.

**Given** DOMPurify is applied to the edited HTML before saving,
**When** the PATCH request is processed on the backend,
**Then** the HTML is sanitized on the backend as well (defense in depth) — user-submitted HTML is never stored raw without sanitization.

**Given** the Tiptap editor content area,
**When** rendered for accessibility,
**Then** the content area has `role="textbox"` and `aria-multiline="true"` with an `aria-label` of "Edit blog post content"; toolbar buttons each have descriptive `aria-label` attributes; standard keyboard shortcuts work: Cmd/Ctrl+B (bold), Cmd/Ctrl+I (italic), Cmd/Ctrl+Z (undo).

**Given** a Campaign in `published`, `rejected`, or `failed` status,
**When** the Approval Gate renders the blog panel,
**Then** the Tiptap editor is rendered in read-only mode (no toolbar, no cursor); the blog content is displayed as styled prose only — editing is not available for terminal-state Campaigns.

---

### Story 4.3: Social Post Editing with Character Counters

As an authenticated user,
I want to edit the generated X and LinkedIn posts with live character counters in the Approval Gate,
So that I can refine the social content to fit platform requirements and match my voice before publishing.

**Acceptance Criteria:**

**Given** the social posts panel in the Approval Gate,
**When** it renders for a `pending_approval` Campaign,
**Then** two plain textarea editors are shown: one for the X post (pre-filled with `campaigns.x_post`) and one for the LinkedIn post (pre-filled with `campaigns.linkedin_post`); each has a live character counter below it.

**Given** the X post textarea,
**When** the user types or edits content,
**Then** a live counter below reads "N / 280"; when N reaches 95% of 280 (267 characters), the counter text color changes to Danger (#8B0000); the textarea does not enforce a hard character limit in the UI (the user may go over, but the publish endpoint validates ≤280 at submission time).

**Given** the LinkedIn post textarea,
**When** the user types or edits content,
**Then** a live counter below reads "N / 1300"; when N reaches 95% of 1300 (1235 characters), the counter text color changes to Danger; the textarea does not enforce a hard character limit in the UI.

**Given** the user edits either social post field and the changes are saved (on approve or explicit save),
**When** `PATCH /api/v1/campaigns/{id}` is called with updated social post fields,
**Then** `campaigns.x_post` and/or `campaigns.linkedin_post` are updated with the edited text, overwriting the generated content.

**Given** the social post editors in the Approval Gate,
**When** the user uses the keyboard to navigate,
**Then** Tab from the X post textarea moves focus to the LinkedIn post textarea; Tab from LinkedIn moves to the next actionable element (Approve/Reject footer); this Tab order matches the visual sequence.

**Given** a Campaign in a terminal state (`published`, `rejected`, `failed`),
**When** the social post panels render,
**Then** both social post textareas are disabled (read-only); no character counters are shown; the content is displayed as plain text for reference only.

---

### Story 4.4: Approve & Reject Campaign

As an authenticated user,
I want to approve a Campaign to mark it ready for publishing, or reject it with an optional reason to trigger regeneration,
So that nothing publishes without my explicit sign-off and I can refine content that does not meet my standards.

**Acceptance Criteria:**

**Given** a user clicks "Approve" in the Approval Gate footer,
**When** `POST /api/v1/campaigns/{id}/approve` is called,
**Then** `campaigns.status` transitions atomically from `pending_approval` to `approved`; if the transition is attempted from any other status, the API returns HTTP 400 with error code `INVALID_STATUS_TRANSITION`.

**Given** the approve action succeeds and the Client has at least one Platform Connection configured,
**When** the `approved` status is confirmed,
**Then** the Approval Gate footer transitions to the "approved, not yet published" state: the Approve/Reject buttons are replaced by a schedule picker and two CTAs — "Publish now" primary button and "Schedule" secondary button (fully wired in Epic 5).

**Given** the approve action succeeds and the Client has NO Platform Connections configured,
**When** the `approved` status is confirmed,
**Then** a prompt appears: "Connect a platform to publish. Your campaign is approved and ready." with a "Connect a platform" CTA that navigates to `/clients/{client_id}/connections`; the Campaign status badge shows "APPROVED" and the content is preserved.

**Given** a user clicks "Reject" in the Approval Gate footer,
**When** the Reject button is clicked,
**Then** a confirmation dialog appears with: a headline "Reject this campaign?"; an optional plain-text textarea labeled "Reason (optional) — helps us improve future generations"; a "Reject campaign" Danger-styled confirm button; a "Cancel" secondary button.

**Given** the user confirms rejection (with or without a reason),
**When** `POST /api/v1/campaigns/{id}/reject` is called,
**Then** `campaigns.status` transitions from `pending_approval` to `rejected`; if a reason was provided, it is saved to `campaigns.rejection_reason`; the Approval Gate transitions to the "rejected" state showing the rejection status and a "Regenerate from same Brain Dump" primary CTA.

**Given** the user clicks "Regenerate from same Brain Dump" on a rejected Campaign,
**When** the regeneration is triggered,
**Then** `POST /api/v1/campaigns/{id}/regenerate` creates a new Campaign record with the same `brain_dump` text and `client_id`, creates a new `jobs` record, dispatches a new generation BackgroundTask, and navigates to the new Campaign's Approval Gate at `/campaigns/{new_campaign_id}` — the old rejected Campaign is preserved with its rejected status.

**Given** a generation or publish job is in-flight for a Campaign,
**When** the Approval Gate footer renders,
**Then** both the Approve and Reject buttons are disabled until the job reaches a terminal state; a loading indicator (inline spinner) is shown on the button that corresponds to the active operation.

**Given** the Approve button is clicked,
**When** the action completes,
**Then** the Campaign status badge in the Approval Gate header updates optimistically to "APPROVED" before the API response; if the API returns an error, the badge reverts to "PENDING APPROVAL" and an error toast is shown.

---

## Epic 5: Platform Connections & Publishing

A user can connect a Client to WordPress, Webflow, X, and LinkedIn via credential entry or OAuth flows, with all credentials encrypted at rest using AES-256-GCM. Approved Campaigns can be published immediately to all connected platforms using each platform's native API, or scheduled for a future date/time. Failed publishes on individual platforms can be retried independently up to 3 times.

### Story 5.1: Platform Connection Setup — WordPress & Webflow

As an authenticated user,
I want to connect my Client to WordPress and Webflow by providing my API credentials,
So that PersonnaPress can publish blog posts directly to my CMS on my behalf.

**Acceptance Criteria:**

**Given** a user navigates to `/clients/{id}/connections`,
**When** the Platform Connections page loads,
**Then** four platform connection cards are displayed — WordPress, Webflow, X, LinkedIn — each showing the platform name, connection status ("Connected" / "Not connected"), and connected account identifier (site URL or CMS name if connected); "Connect" CTA is shown on disconnected platforms.

**Given** a user clicks "Connect" on the WordPress card,
**When** the connection form opens,
**Then** an inline form appears below the card with two fields: "WordPress site URL" (e.g., https://mysite.com) and "Application Password" (password input, masked); a "Connect" primary button and "Cancel" secondary button are present.

**Given** the user submits a WordPress site URL and Application Password,
**When** `POST /api/v1/clients/{client_id}/connections` is called,
**Then** FastAPI validates the credentials by making a test call to `{site_url}/wp-json/wp/v2/users/me` with the Application Password; if the test call returns HTTP 200, the credentials are encrypted using AES-256-GCM (`core/security.py:encrypt_credential()` using `CREDENTIAL_ENCRYPTION_KEY` from Droplet env) and stored as `platform_connections.encrypted_credentials` with `platform='wordpress'`; the connection card updates to "Connected — [site_url]" without a page reload.

**Given** the WordPress credentials fail validation (HTTP 401 from WordPress),
**When** the test call returns 401,
**Then** the API returns HTTP 400 and the inline form shows: "WordPress returned 401 — check your Application Password." — the form stays open for correction; no `platform_connections` record is created.

**Given** a user clicks "Connect" on the Webflow card,
**When** the connection form opens,
**Then** fields are shown for "Webflow API Bearer Token" and a "CMS Collection" selector; the selector is initially empty with a "Loading collections..." state; upon entering a valid token and clicking "Validate token," `GET /api/v1/clients/{client_id}/webflow/collections` is called which uses the token to fetch the user's Webflow collections from the Webflow CMS API v2 and populates the dropdown.

**Given** the Webflow token validation fails or the collections API returns an error,
**When** the dropdown population fails,
**Then** the dropdown is replaced by a plain text input labeled "Webflow Collection ID" with a documentation link: "Find your Collection ID in Webflow → CMS → [Collection] → Settings"; the user can enter the ID manually.

**Given** a user clicks "Disconnect" on any connected platform card,
**When** the disconnect action is triggered,
**Then** a confirmation dialog appears: "Disconnect [Platform]? Future campaigns will not publish to this platform." with a "Disconnect" Danger button and "Cancel"; on confirm, the `platform_connections` record is deleted; the card reverts to "Not connected."

---

### Story 5.2: Platform Connection Setup — X (Twitter) & LinkedIn OAuth

As an authenticated user,
I want to connect my Client to X and LinkedIn via OAuth authorization flows,
So that PersonnaPress can post on my behalf using secure, revocable OAuth tokens.

**Acceptance Criteria:**

**Given** a user clicks "Connect" on the X (Twitter) connection card,
**When** the "Connect X" button is clicked,
**Then** Next.js generates a random `state` value, stores it in a short-lived httpOnly cookie (`oauth_state`, SameSite=Lax, 10-minute expiry), and redirects the browser to the Twitter OAuth 2.0 PKCE authorization URL with the correct `client_id`, `redirect_uri`, `scope`, `state`, and `code_challenge` parameters.

**Given** the user authorizes the X app and is returned to the OAuth callback,
**When** the callback URL is hit with the authorization `code` and `state` parameters,
**Then** Next.js verifies the returned `state` matches the cookie value (CSRF protection); if valid, calls FastAPI `POST /api/v1/clients/{client_id}/connections/x/callback` with the authorization code; FastAPI exchanges the code for OAuth tokens via Twitter API v2 PKCE token endpoint; the access token and refresh token are encrypted with AES-256-GCM and stored in `platform_connections`; the X connection card updates to "Connected — @[twitter_handle]."

**Given** the `state` parameter in the callback does not match the cookie,
**When** the callback is received,
**Then** the OAuth flow is aborted, the `oauth_state` cookie is cleared, and an error is shown: "Authorization failed — the request was tampered with. Please try connecting again."

**Given** a user clicks "Connect" on the LinkedIn connection card,
**When** the "Connect LinkedIn" button is clicked,
**Then** the user is redirected to LinkedIn's OAuth 2.0 authorization URL with `scope=w_member_social`, `redirect_uri`, `state`, and `client_id`; the same `state` CSRF protection pattern (httpOnly cookie) is used as for X.

**Given** the user authorizes LinkedIn and is returned to the callback,
**When** FastAPI processes the LinkedIn OAuth code exchange,
**Then** FastAPI calls LinkedIn's token endpoint to obtain an access token; the token is encrypted and stored in `platform_connections` with `platform='linkedin'`; the LinkedIn connection card updates to "Connected — [LinkedIn profile name]."

**Given** any OAuth connection attempt fails on the provider side (user denies, token exchange error),
**When** the callback receives an error parameter or the exchange fails,
**Then** the error is surfaced: "[Platform] authorization failed — [error description]. Please try connecting again." — the connection card remains "Not connected."

---

### Story 5.3: Immediate Multi-Platform Publishing

As an authenticated user,
I want to publish an approved Campaign to all connected platforms at once,
So that my content goes live simultaneously on all my channels with a single click.

**Acceptance Criteria:**

**Given** an approved Campaign with at least one Platform Connection and the user clicks "Publish now" in the Approval Gate,
**When** `POST /api/v1/campaigns/{id}/publish` is called,
**Then** a `jobs` record is created with `job_type='publish'` and `status='pending'` before the BackgroundTask is dispatched; the API returns HTTP 202; the Approval Gate shows a publishing-in-progress state with an inline spinner on the "Publish now" button; both Approve and Reject buttons are disabled.

**Given** the publish BackgroundTask executes in `workers/publish.py`,
**When** it runs `services/publishing.py`,
**Then** for each platform connection, the encrypted credentials are retrieved from `platform_connections`, decrypted using `core/security.py:decrypt_credential()` (only within `services/publishing.py`), and the platform integration is called; the decrypted credential value does not leave the scope of the function that uses it and is never logged.

**Given** the WordPress publish step runs,
**When** `integrations/wordpress.py` publishes the blog post,
**Then** the draft-first pattern is followed: (1) `POST /wp-json/wp/v2/posts` with `status: "draft"` creates the post; (2) the featured image is uploaded via `POST /wp-json/wp/v2/media` and set as featured media; (3) `PATCH /wp-json/wp/v2/posts/{id}` sets `status: "publish"` only after both steps succeed; if step 3 fails, the draft post is cleaned up via DELETE.

**Given** the X publish step runs,
**When** `integrations/twitter.py` posts the X post,
**Then** `POST https://api.twitter.com/2/tweets` is called via OAuth 2.0 PKCE with the `tweet.fields` parameter set to selective fields to minimize rate-limit pressure; if multiple Campaigns publish X posts within 30 seconds, outbound calls are staggered with a 2-second delay between each.

**Given** the LinkedIn publish step runs,
**When** `integrations/linkedin.py` posts the LinkedIn update,
**Then** `POST https://api.linkedin.com/v2/ugcPosts` is called with the `LinkedIn-Version: 202602` header; if multiple Campaigns publish LinkedIn posts within 30 seconds, calls are staggered with a 5-second delay.

**Given** all connected platforms publish successfully,
**When** the BackgroundTask completes,
**Then** `campaigns.status` transitions to `published`; `jobs.status` is set to `complete`; the Approval Gate footer shows: "Published to [Platform icons] — [Date], [Time]." with "View on WordPress →" (and other platform links) as text links; the content is read-only.

**Given** one or more platforms fail during publish while others succeed,
**When** the BackgroundTask completes with mixed results,
**Then** `campaigns.status` is set to `failed`; `jobs.error_details` contains per-platform results (e.g., `{"wordpress": "success", "linkedin": "401 token expired"}`); the Retry Panel (Story 5.5) is shown in the Approval Gate; posts that succeeded are already live — v1 does not distinguish partial success from full failure in the status field.

---

### Story 5.4: Scheduled Publishing

As an authenticated user,
I want to set a future date and time for an approved Campaign to publish automatically,
So that my content goes live at the optimal time without me needing to be present.

**Acceptance Criteria:**

**Given** an approved Campaign in the Approval Gate with the "approved, not yet published" state,
**When** the user clicks the "Schedule" secondary button,
**Then** a datetime picker appears inline below the approve action area; the picker shows the date and time inputs; the resolved account-level timezone is displayed next to the input: "Schedules in America/New_York" (or the account timezone set in user preferences, defaulting to UTC if not configured).

**Given** the user selects a future date and time and clicks "Confirm schedule,"
**When** `POST /api/v1/campaigns/{id}/publish/schedule` is called with the ISO 8601 scheduled datetime,
**Then** a `jobs` record is created with `job_type='scheduled_publish'`, `status='scheduled'`, and `jobs.scheduled_at` set to the requested time; APScheduler registers a job from this database record pointing at the `workers/publish.py` BackgroundTask; the Approval Gate footer shows "Scheduled — [Weekday], [Month] [Day], [Year], [Time] [Timezone]."

**Given** APScheduler starts up (or restarts),
**When** the `scheduler/scheduler.py` lifespan hook runs,
**Then** APScheduler's SQLAlchemyJobStore reads from `jobs` where `status='scheduled'` and `scheduled_at > now()` and re-registers all pending scheduled jobs; no scheduled job is lost across a Droplet restart.

**Given** the scheduled time arrives,
**When** APScheduler fires the job,
**Then** the same `workers/publish.py` BackgroundTask runs as for immediate publishing (Story 5.3); on success, `campaigns.status` is set to `published`; on failure, `campaigns.status` is set to `failed` and an in-app notification is queued for the next time the user logs in: "Scheduled publish failed — [Campaign title] to [Platform]. Reconnect [Platform] and retry."

**Given** a scheduled Campaign appears in the Approval Gate,
**When** the user views it before the scheduled time,
**Then** the Approval Gate footer shows the scheduled datetime with a "Cancel schedule" secondary link; clicking "Cancel schedule" deletes the `jobs` record and removes the APScheduler job, returning the Campaign to the "approved, not yet published" state.

**Given** the datetime picker is used,
**When** the user selects a time in the past,
**Then** the "Confirm schedule" button is disabled and an inline message reads "Scheduled time must be in the future."

---

### Story 5.5: Publishing Retry & Failure Handling

As an authenticated user,
I want to retry publishing to specific platforms that failed without regenerating my content,
So that a temporary API issue on one platform does not require me to restart the entire publishing process.

**Acceptance Criteria:**

**Given** a Campaign with `status='failed'` due to publish errors is opened in the Approval Gate,
**When** the Approval Gate renders,
**Then** a Retry Panel is shown below the content previews listing each platform that failed: platform name, specific error message (e.g., "WordPress returned 401 — check your Application Password"), and a per-platform "Retry" button; platforms that published successfully show "Published" with a link to the live post.

**Given** the Retry Panel shows attempt counts,
**When** it renders,
**Then** each failed platform shows "Attempt [N] of 3" where N is the current `jobs.attempt_count` for that platform; when `attempt_count` reaches 3, the "Retry" button for that platform is disabled and replaced with the text "Maximum retries reached — reconnect [Platform] and try again."

**Given** a user clicks the "Retry" button for a specific failed platform,
**When** `POST /api/v1/campaigns/{id}/publish/retry` is called with the platform identifier,
**Then** `jobs.attempt_count` is incremented and `jobs.status` is set back to `'pending'` before the BackgroundTask is dispatched; only the specified failed platform is retried — already-published platforms are not called again.

**Given** the retry BackgroundTask executes,
**When** it completes successfully for the retried platform,
**Then** if all platforms are now published, `campaigns.status` transitions to `published` and the Retry Panel is replaced by the "Published" summary footer; if other platforms are still failing, `campaigns.status` remains `failed` and the Retry Panel updates to reflect the latest state.

**Given** a Droplet restart occurs while a retry job is in `pending` status,
**When** FastAPI restarts and the scheduler initializes,
**Then** the `jobs` record persists in Supabase Postgres; the user can trigger the next retry attempt from the Approval Gate on their next session — no retry state is lost.

---

## Epic 6: Dashboard & Content Calendar

A user can view all Campaigns for the active Client in the Dashboard (newest first, filterable by status, paginated at 20 per page) and navigate directly to any Campaign's Approval Gate by clicking its row. The Content Calendar surface provides a read-only month view showing published Campaigns with platform icons and scheduled Campaigns with time indicators.

### Story 6.1: Campaign List Dashboard with Status Filtering

As an authenticated user,
I want to see all my campaigns for the active client in a filterable list, ordered from newest to oldest,
So that I can quickly find and access any campaign regardless of its current status.

**Acceptance Criteria:**

**Given** an authenticated user navigates to `/dashboard`,
**When** the page loads with the active Client set,
**Then** the Campaign list is fetched via `GET /api/v1/campaigns?client_id={activeClientId}&page=1&per_page=20`; results are ordered by `created_at` descending (newest first); up to 20 campaigns are shown per page with pagination controls (previous/next) if more than 20 exist.

**Given** the Campaign list renders,
**When** a Campaign row is displayed,
**Then** each row shows: campaign title (derived from the blog post H1, truncated at 60 characters with an ellipsis), the Campaign's Status Badge (one of five variants: PENDING APPROVAL, APPROVED, PUBLISHED, REJECTED, FAILED), creation date formatted with `Intl.DateTimeFormat`, and the publish date (if status is `published`); platform icons (WP, Webflow, X, LinkedIn icons) are shown next to the date for published campaigns.

**Given** a user clicks anywhere on a Campaign row,
**When** the click event fires,
**Then** the user is navigated to `/campaigns/{id}` (the Approval Gate) for that Campaign.

**Given** status filter tabs or a filter dropdown is shown above the Campaign list,
**When** the user selects a specific status (e.g., "Pending Approval"),
**Then** the list refetches with `?status=pending_approval` and displays only campaigns matching that status; the URL updates to include the filter parameter so the filtered state is shareable and bookmarkable.

**Given** the page is loading Campaign data,
**When** the initial fetch is in progress,
**Then** skeleton placeholder rows matching the expected Campaign row height and layout are shown (no spinner); the number of skeleton rows matches `per_page` (20) or the previous known count, whichever is smaller.

**Given** the active Client has no Campaigns,
**When** the Dashboard loads,
**Then** the empty state is shown in the center of the content pane: H2 "No campaigns yet." and body text "Start with a Brain Dump and publish your first post." with a "New Campaign" primary CTA; no skeleton rows are shown.

**Given** a Campaign row for a `failed` status campaign,
**When** the row renders,
**Then** the status badge shows "FAILED" (Danger red), and a "Retry" inline text link is shown within the row that navigates directly to the Approval Gate for that campaign (where the Retry Panel is shown).

**Given** the user switches the active Client via the Client Switcher,
**When** the new client context is set,
**Then** the Campaign list React Query key `["campaigns", newClientId]` is invalidated and the list reloads for the new client immediately.

---

### Story 6.2: Content Calendar — Read-Only Month View

As an authenticated user,
I want to view a month-by-month calendar showing when my content was published and what is scheduled,
So that I can see my publishing cadence at a glance and spot gaps or scheduling conflicts across the month.

**Acceptance Criteria:**

**Given** an authenticated user navigates to `/calendar`,
**When** the page loads,
**Then** a month view calendar is displayed for the current month; the month name and year are shown in a Playfair Display H2 at the top; previous and next month navigation arrows are present.

**Given** the calendar renders for the current month,
**When** campaigns are fetched via `GET /api/v1/campaigns?client_id={activeClientId}&status=published,approved`,
**Then** published Campaigns appear on their `updated_at` date (publish date) with small platform icons (WP, Webflow, X, LinkedIn icons for each connected platform they were published to); scheduled Campaigns (status `approved` with `scheduled_at` set) appear on their `scheduled_at` date with a clock icon and formatted time (e.g., "8:00 AM").

**Given** a calendar day cell has one or more campaigns,
**When** the user clicks on a campaign entry within a day cell,
**Then** they are navigated to the Approval Gate at `/campaigns/{id}` for that Campaign.

**Given** a calendar day cell,
**When** rendered for accessibility,
**Then** each cell has `aria-label` including the full date and campaign count: "June 17, 2026, 2 campaigns" (or "June 17, 2026, no campaigns" if empty); all interactive campaign entries within the cell are keyboard-focusable and have descriptive labels.

**Given** the calendar is in read-only mode,
**When** the user attempts to drag a campaign entry to a different date,
**Then** nothing happens — no drag-and-drop rescheduling is available in v1; entries are click-only.

**Given** the active Client is switched via the Client Switcher while on the Calendar surface,
**When** the new client context is set,
**Then** the calendar reloads and shows the campaigns for the newly active Client for the currently viewed month.

**Given** no campaigns exist for the currently viewed month,
**When** the calendar renders,
**Then** all day cells are empty; a subdued message appears below the calendar: "Nothing scheduled. Approve a campaign to see it here." in Graphite body text.

---

## Epic 7: Trial Lifecycle & Subscription Enforcement

The system manages the complete 14-day trial lifecycle with proportional in-app nudges at day 10 and day 13, a non-dismissible upgrade banner on trial expiry that blocks new generation and publishing, 30-day data retention post-trial, and a 30+7 day warning-and-deletion policy executed by a daily APScheduler cleanup job. Subscription tier limits (Client count, Campaign count, image generation count) are enforced across all creation and generation actions throughout the application.

### Story 7.1: Trial Expiry Nudge Notifications

As a user approaching the end of my free trial,
I want to receive timely in-app notifications reminding me to subscribe before my trial ends,
So that I can decide whether to continue without an unexpected access interruption.

**Acceptance Criteria:**

**Given** a user whose trial has 4 days remaining (day 10 of a 14-day trial, calculated from `subscriptions.created_at`),
**When** they load any authenticated page,
**Then** a non-blocking toast notification appears in the top-right of the viewport: "4 days left on your trial. Subscribe to keep publishing." with a "Subscribe" link that opens the Stripe Customer Portal; the toast is dismissible (× close button); it appears once per login session, not on every page navigation.

**Given** a user whose trial has 1 day remaining (day 13 of trial),
**When** they load any authenticated page,
**Then** the same toast pattern fires with more urgent copy: "1 day left on your trial. Subscribe now to avoid interruption." — still dismissible, still appears once per login session; this replaces the day-10 nudge if both would apply (they cannot overlap in a single session).

**Given** a user who has already dismissed a trial nudge in the current session,
**When** they navigate between pages,
**Then** the nudge toast does not reappear — it is suppressed until the next login session.

**Given** a user who subscribes after seeing a nudge,
**When** the Stripe webhook processes the subscription activation,
**Then** `subscriptions.status` is updated from `'trialing'` to `'active'`; no further trial nudges appear for this account.

**Given** a user's trial has not yet reached day 10,
**When** they use the application,
**Then** no trial-related nudges or banners appear — trial state is not surfaced until nudge days are reached.

---

### Story 7.2: Trial Expiry Restricted State & Upgrade Banner

As a user whose trial has expired without subscribing,
I want to be clearly notified that my trial has ended and understand what I can and cannot do,
So that I can decide whether to subscribe while knowing my existing content is safe.

**Acceptance Criteria:**

**Given** a user's trial period has ended (`subscriptions.status='trialing'` and `now() > subscriptions.billing_cycle_end`) and they have not subscribed,
**When** they log in or their session is validated by Next.js middleware,
**Then** `subscriptions.status` is updated to `'trial_expired'`; a non-dismissible upgrade banner is rendered at the top of every authenticated page: full-width, Ink (#111111) fill, White (#FFFFFF) text, pushes layout down (not an overlay); banner text: "Your trial has ended. Subscribe to continue publishing." with a "Subscribe" CTA button (White-on-Black secondary-inverted style) that opens the Stripe Customer Portal.

**Given** a user in `trial_expired` status navigates to any page,
**When** the page renders,
**Then** they can view their existing Campaigns, Clients, Brand Voice Profiles, and Platform Connections — all read access is preserved; no existing content is deleted or hidden.

**Given** a user in `trial_expired` status attempts to create a new Campaign, generate content, or publish,
**When** they click "New Campaign," "Generate campaign," "Publish now," or "Schedule,"
**Then** the action is blocked by `services/subscription.py`; the UI shows an upgrade prompt: "Subscribe to [action — create campaigns / generate content / publish]." with a "Subscribe" CTA; the action does not proceed.

**Given** a user in `trial_expired` status clicks a disabled "New Campaign" CTA,
**When** the upgrade prompt appears,
**Then** it appears as a modal or inline message — not a toast — since the user is attempting a specific action, not just browsing.

**Given** a user subscribes after their trial has expired,
**When** the Stripe `customer.subscription.created` webhook fires,
**Then** `subscriptions.status` is updated to `'active'`; the upgrade banner disappears on their next page load; all previously blocked actions are immediately restored; no data was deleted during the expired period.

---

### Story 7.3: Data Retention, Account Deletion & Cleanup Scheduler

As a user whose trial has expired and who has not subscribed within 30 days,
I want to receive a warning before my account is deleted,
So that I have a final opportunity to retrieve my content or subscribe before it is permanently removed.

**Acceptance Criteria:**

**Given** a daily APScheduler job named `subscription_cleanup` is registered in `scheduler/scheduler.py`,
**When** APScheduler initializes (app startup),
**Then** the job is registered as a recurring daily job using the SQLAlchemy job store; it queries `subscriptions` for all records where `status='trial_expired'` and `updated_at` (the expiry timestamp) is older than 30 days.

**Given** the `subscription_cleanup` job identifies a user whose trial expired more than 30 days ago,
**When** the job runs for that user,
**Then** a warning email is sent via Resend with the subject "Your PersonnaPress account will be deleted in 7 days" and instructions to subscribe or export content; `subscriptions.deletion_scheduled_at` is set to `now() + 7 days` (new column added via Alembic migration).

**Given** the `subscription_cleanup` job identifies a user whose `deletion_scheduled_at` is in the past (30+7 days total since trial expiry),
**When** the job runs for that user,
**Then** all `campaigns`, `clients`, `platform_connections`, `generation_logs`, `jobs`, and `subscriptions` records for that user are deleted; the `users` record is anonymized (email replaced with a hashed value, `hashed_password` set to null); the deletion is logged to Sentry with the anonymized user ID for audit purposes.

**Given** a user subscribes at any point before the `deletion_scheduled_at` timestamp,
**When** the Stripe subscription webhook fires,
**Then** `subscriptions.status` is set to `'active'` and `subscriptions.deletion_scheduled_at` is set to null; the scheduled deletion is effectively cancelled — the next run of `subscription_cleanup` will skip this user.

**Given** all existing data during the 30-day post-trial retention window,
**When** the user logs in before the deletion date,
**Then** all their Clients, Campaigns, Brand Voice Profiles, and Platform Connections are visible and accessible (read-only due to Story 7.2 restrictions); no data is hidden or degraded during the retention window.

**Given** the `subscription_cleanup` job runs,
**When** it executes any database delete operations,
**Then** it processes at most 50 accounts per daily run to prevent long-running transactions; each deletion batch is wrapped in a try/except that logs failures to Sentry without stopping the rest of the batch.
