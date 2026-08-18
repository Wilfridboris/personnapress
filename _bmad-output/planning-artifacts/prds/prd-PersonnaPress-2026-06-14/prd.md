---
title: PersonnaPress
created: 2026-06-14
updated: 2026-08-17
status: final
version: 2.0 (re-baselined to shipped product state)
---

# PRD: PersonnaPress

## 0. Document Purpose

This PRD describes PersonnaPress as it exists today: an AI content platform that learns a user's writing voice and publishes SEO-structured blog posts and social campaigns across many platforms. It is written for the product owner, designer, and engineering team.

**This is a re-baselined document.** The original PRD (2026-06-14) planned a pre-launch "v1" across Epics 1 to 7. Since then the product has shipped through Epic 23. Several capabilities the original PRD deferred to Phase 2 or v2 or explicitly excluded (Meta/Instagram/Facebook/Threads publishing, voice-to-text Brain Dump, email notifications, content revision history, a second LLM provider, an alternate image provider) are now live. This version drops the stale v1/Phase-2 phase framing and describes current capabilities as shipped. A short **Roadmap** section (§6) records what remains deferred.

Features are grouped with globally-numbered functional requirements (FR-N) nested under each feature section. FR-1 through FR-35 retain their original IDs; new capabilities are added as FR-36 onward. Assumptions still open are indexed in §14. Downstream detail (architecture, competitive analysis, data model) lives in `addendum.md`.

## 1. Vision

Content-driven founders, coaches, and agency owners in North America know that consistent publishing drives growth. But writing takes 3 to 6 hours per article, and generic AI tools produce output that sounds nothing like them. The result: sporadic publishing, off-brand content, or expensive ghostwriters.

PersonnaPress is an AI content platform that learns the user's exact writing style from their existing content, then turns rough ideas ("Brain Dumps") into SEO-ranked blog posts and matching social campaigns in their authentic voice. It stores, versions, and delivers that content, and publishes it across WordPress, Webflow, X, LinkedIn, Instagram, Facebook, Threads, GitHub-hosted blogs, and a headless delivery API. Nothing publishes without human approval. The system handles the entire pipeline from idea to live post, and can plan and schedule an entire week of content from a single session.

The product's core bet is that voice fidelity, not just content generation, is the unlock. Generic AI writing tools are a commodity. A tool that writes *as you*, versions your content, and publishes *for you* across every platform is a workflow replacement, not just a writing assistant. The public positioning has moved from "AI blog writer" to "the AI content platform that publishes in your brand voice," with "brand voice generator" as the primary differentiator.

## 2. Target User

### 2.1 Jobs To Be Done

- **Functional:** "I need to publish a blog post and matching social posts every week without spending half a day writing."
- **Functional:** "I need my content to rank on Google, and to show up in AI answers, not just exist."
- **Functional:** "I want to plan a whole week of posts in one sitting."
- **Emotional:** "I want my content to sound like me, not like every other AI-generated post."
- **Social:** "I want my audience to see me as a consistent, authentic thought leader."
- **Contextual:** "I have 20 minutes between meetings. I want to dump my idea (typed or spoken) and have a draft waiting for me later."
- **Functional (Agency):** "I manage content for multiple clients and need each client's voice maintained separately."
- **Emotional (Agency):** "I need my clients to not realize I'm using AI. Each client's content must sound distinctly like them, not like a template."
- **Functional (Developer):** "I blog on GitHub Pages / a headless frontend and want AI writing that publishes into my repo or via an API, not a CMS lock-in."

### 2.2 Non-Users

- **Enterprise marketing teams** with existing content management systems, approval chains, and compliance workflows. PersonnaPress has no RBAC, no multi-user approval chains beyond single-user approve/reject, and no SSO.
- **Users who want a full CMS.** PersonnaPress generates, versions, and publishes content. It does not manage an existing content library on a third-party CMS, handle comments, or provide engagement analytics dashboards.
- **Non-English content creators.** `[ASSUMPTION: content generation is tuned for English. Multi-language generation is not built.]`

### 2.3 Key User Journeys

- **UJ-1. Sarah onboards and publishes her first blog post.**
  - **Persona + context:** Sarah is a SaaS founder who blogs monthly but wants to go weekly. She just signed up.
  - **Path:** Onboarding walks her through four steps: (1) create her first client (company name + website URL), (2) review the extracted Brand Voice Profile and edit a field or two, (3) connect a publishing platform, (4) enter her first Brain Dump (typed or spoken). The system generates a blog draft (HTML preview), social posts, and a featured image. She tweaks a paragraph inline, approves, and publishes.
  - **Climax:** Sarah sees her blog post live on her WordPress site, written in her voice, with a generated featured image, minutes after she pasted three bullet points.
  - **Edge case:** If Sarah has no scrapable website content, Brand Ingestion falls back to a manual voice questionnaire. If her voice profile was built on thin content, a low-confidence banner tells her how to improve it.

- **UJ-2. Marcus runs his weekly content routine.**
  - **Persona + context:** Marcus is a business coach who publishes weekly. Voice profile and platform connections are already configured.
  - **Path:** Marcus opens "Plan My Week," sets his cadence (for example 3 LinkedIn posts, 5 X posts, 1 blog), and dumps a week of ideas. The system generates the full week as a reviewable grid. He edits a couple of posts, approves the batch, and schedules them across the week.
  - **Climax:** Marcus checks his phone on Thursday and sees LinkedIn engagement on a post he approved on Monday in one session.

- **UJ-3. Jenna manages content for three agency clients.**
  - **Persona + context:** Jenna runs a small marketing agency with three clients, each with a distinct brand voice and its own platform connections.
  - **Path:** Jenna switches to Client A, enters a Brain Dump, reviews drafts generated with Client A's voice, approves, and publishes to Client A's WordPress and LinkedIn. She switches to Client B and repeats.
  - **Climax:** Three clients' weekly content published in under 30 minutes total.

- **UJ-4. Dev publishes to a headless / GitHub blog.**
  - **Persona + context:** Dev runs a company blog on an Astro frontend and wants AI writing without a CMS.
  - **Path:** Dev either connects a GitHub repo (PersonnaPress detects the framework and opens a PR with the post in the right path) or publishes to the Headless Blog destination and fetches articles on the site via a delivery token and the public API.
  - **Climax:** A post generated in PersonnaPress appears on Dev's site through his own frontend, versioned and editable after publish.

## 3. Glossary

- **Brain Dump**: Raw, unstructured user input (typed or voice-transcribed) that serves as the creative brief for a Campaign or a Roadmap.
- **Brand Voice Profile (BVP)**: A structured representation of a Client's writing style. It now spans 20 dimensions (5 computed stylometric metrics plus 15 qualitative dimensions) and a synthesized **Voice Brief** narrative injected into generation prompts.
- **Voice Brief**: A 150 to 250 word third-person prose description of the writer's voice, synthesized from the BVP and included directly in generation system prompts.
- **Campaign**: The atomic unit of content production. A blog Campaign contains a blog post (HTML), social posts, and a featured image. A **social-only** Campaign skips the blog. A Campaign moves through `pending_approval → approved → published` (or `rejected` / `failed`).
- **Roadmap**: A batch of Campaigns generated from one Brain Dump to fill a week of content across platforms ("Plan My Week"). Consumes a separate roadmap credit, not per-post campaign credits.
- **Client**: A brand identity with its own Brand Voice Profile and platform connections. One account can manage multiple Clients.
- **Approval Gate**: The mandatory human review step before any Campaign publishes. Nothing auto-publishes.
- **Platform Connection**: An authenticated link between a Client and an external destination (WordPress, WordPress.com, Webflow, X, LinkedIn, Instagram, Facebook Page, Threads, GitHub Pages, Headless Blog).
- **Brand Ingestion**: Analyzing a Client's website and/or uploaded content to extract a Brand Voice Profile.
- **Featured Image**: An AI-generated image accompanying a post, produced via a configurable image provider.
- **Article**: A first-class, versioned blog content row stored in PersonnaPress, delivered to customer sites via the Headless Blog delivery API. Articles carry full revision history.
- **Delivery Token**: A hashed, revocable API token that authorizes read-only fetches of a Client's published Articles from the public delivery API.
- **GitHub App**: A first-party GitHub integration granting fine-grained, repo-scoped permissions for repo connection and blog publishing.
- **Framework Detection**: Scanning a connected repo for marker files to determine the static site generator and correct publish path.

## 4. Features

### 4.1 Account Management

**Description:** Users sign up, log in, and manage their account and subscription.

#### FR-1: User Registration
User can create an account with email and password or via Google OAuth.
**Consequences (testable):**
- System creates a user record and sends a branded verification email on signup.
- User cannot access features until email is verified; Google OAuth users skip verification.
- On verification (and on new Google signup) a welcome email is sent.

#### FR-2: User Authentication
Registered user can log in via email/password or Google OAuth and receive a session.
**Consequences (testable):**
- Session persists across tabs for 7 days. `[ASSUMPTION: 7-day session.]`
- Invalid credentials return a generic error (no enumeration).

#### FR-3: Subscription Management and Checkout
Authenticated user can start a subscription via Stripe Checkout, and view, upgrade, downgrade, or cancel via the Stripe Customer Portal. See §8 for plans and §4.10 for trial behavior.
**Consequences (testable):**
- Trial or expired users can subscribe through an in-app plan picker that opens a Stripe Checkout session; `checkout.session.completed` webhook activates the plan.
- User sees current plan tier, usage (campaigns, images, roadmaps this cycle), and renewal date.
- Upgrade takes effect immediately; downgrade at next cycle; cancellation retains access to end of period.

### 4.2 Client Management

**Description:** Users create and manage Client profiles (brand identities). Solo users have one Client; agency users manage several.

#### FR-4: Create Client
User can create a Client with a name and optional website URL. Client count is enforced per tier with an upgrade prompt at the limit. Providing a URL triggers Brand Ingestion (§4.3).

#### FR-5: Edit Client
User can update a Client's name, website URL, and full Brand Voice Profile. Changing the URL offers a re-run of ingestion; BVP edits apply to future Campaigns.

#### FR-6: Delete Client
User can delete a Client; deletion cascades to Campaigns, Articles, Platform Connections, and the BVP behind a destructive-action confirmation.

#### FR-7: List and Switch Clients
User can view all Clients and switch active context. The active Client is always shown, and switching loads that Client's Campaigns, Articles, BVP, and connections. Client navigation and creation are available directly from the sidebar switcher.

### 4.3 Brand Voice Ingestion and Deep Voice Profile

**Description:** The system analyzes a Client's existing content to extract a Brand Voice Profile, the platform's core differentiator. The profile has been expanded from 3 fields to a 20-dimension system with a synthesized Voice Brief, computed stylometry, and explicit voice signals injected into generation.

#### FR-8: Website Scraping
System scrapes a provided URL and extracts written content, stripping navigation/boilerplate. Extracts at least the 10 most recent posts, completes within roughly 60 seconds for typical sites, and offers the manual fallback on failure.

#### FR-9: Content Upload
User can upload text files (.txt, .md, .docx) or paste raw text to supplement or replace scraped content. Uploads are stored in Supabase Storage; limits apply (about 5 MB/file, 10 files/Client). Upload filename and revision are surfaced, and a re-learn can be triggered from new uploads.

#### FR-10: Voice Profile Extraction (20-dimension BVP + Voice Brief)
System analyzes collected content and produces a Brand Voice Profile with:
- **5 computed stylometric metrics** (no LLM call): average sentence length, sentence rhythm (uniform/varied), paragraph density (airy/moderate/dense), contraction frequency, list preference.
- **15 qualitative dimensions** extracted by the LLM: identity (pronoun preference, formality scale, humor style, vocabulary complexity), patterns (example style, specificity preference, opening/closing/header patterns, post-structure template), and anchors (signature phrases, voice-anchor sentences, anti-pattern example).
- Retained fields: tone, cadence, banned jargon, target audience.
- A **Voice Brief**: a 150 to 250 word prose narrative synthesized from the full BVP for direct injection into generation prompts.

**Consequences (testable):**
- Profile stored as JSON on the Client; user can review and edit every editable field (computed fields are read-only) in a grouped Identity/Patterns/Anchors UI, with the Voice Brief shown first.
- If content is under ~300 words, the profile is flagged `low_confidence` (FR-38).
- If no content is available, the system falls back to a manual voice questionnaire.
- Legacy 3-field profiles remain valid; generation falls back to the 3-field prompt format for them until refreshed.

#### FR-11: Voice Profile Refresh (additive enrichment)
User can re-extract the BVP from updated content. Refresh is **additive, not destructive**: scalar fields take the latest value, array fields (banned jargon, signature phrases, voice anchors) merge and dedupe, computed fields update, and the Voice Brief is regenerated from the merged profile.

#### FR-36: Voice Signal Injection into Generation
Signature phrases, voice-anchor sentences, and the anti-pattern example are injected into blog and social generation prompts as explicit few-shot style signals (use 2 to 3 signature phrases naturally, match anchor cadence, never produce the anti-pattern). Backward compatible: absent fields inject nothing. Em-dashes inside injected text are converted to double hyphens before injection.

#### FR-37: Voice-Driven Generation Priority Rules
The Voice Brief is injected after SEO structure instructions with an explicit priority note: SEO structure (H1, meta description, H2/H3, 800 to 1500 words) is mandatory; voice fills within that structure. Behavioral rules (list preference, opening pattern, pronoun consistency, concrete-number specificity) are applied. The voice-fidelity scoring call additionally checks pronoun consistency, specificity, and closing-pattern match.

#### FR-38: Low-Confidence Voice Warning
When a BVP is `low_confidence`, a banner on the voice page and a subtle note on the approval gate warn that the profile was built from limited samples and link to add content. Absent/false flag shows nothing (legacy-safe).

#### FR-39: Re-voice Existing Posts
User can regenerate any approved or published blog post using the Client's current BVP. This creates a new `pending_approval` Campaign from the original Brain Dump and leaves the original untouched.

### 4.4 Brain Dump Capture

**Description:** The primary input surface. Users capture a raw idea by typing or speaking. The Brain Dump becomes the creative brief for a Campaign or Roadmap.

#### FR-12: Text Brain Dump
User can enter free-form text or bullet points for the active Client. Minimum 20, maximum 10,000 characters. Submitting creates a Campaign in `pending_approval` and triggers generation.
**Consequences (testable):**
- Monospace, auto-expanding input with a capped height and stable scroll for large text.
- Inline quality guidance (placeholder + tips), URL/link detection with anchor embedding, and localStorage draft autosave with a restore banner.

#### FR-40: Voice-to-Text Brain Dump
User can record a Brain Dump with the browser microphone; audio is transcribed by the OpenAI Whisper API and delivered into the Brain Dump textarea for review before submitting.
**Consequences (testable):**
- A Record/Stop control with recording, uploading, and transcribing states, a waveform/pulse visualizer, and full keyboard/ARIA support; the mic is hidden with a fallback message where `MediaRecorder` is unsupported.
- Audio is transcribed via external inference and never written to disk or storage; a durable `transcription` job record backs the flow, polled via the existing job-status endpoint.
- Upload capped at 10 MB, rate-limited per hour, and owner-scoped (IDOR-guarded).

#### FR-41: Content Type and Image Options
User can choose the content type and image behavior before generating.
**Consequences (testable):**
- **Social-only mode** generates social posts without a blog (blog fields null), gating the approval and publish surfaces accordingly.
- An **AI featured image** toggle lets the user skip image generation for a Campaign.

### 4.5 Content Generation

**Description:** The generation engine takes a Brain Dump and BVP and produces a Campaign: SEO-structured blog post (HTML) and platform-specific social posts, in the Client's voice. Text generation runs through a configurable LLM provider.

#### FR-13: Blog Post Generation
System generates an SEO-structured blog post in HTML conforming to the BVP.
**Consequences (testable):**
- Output includes title (H1), meta description, structured headings, body, and conclusion in semantic HTML.
- **Length selector:** Quick Read / Standard / In-Depth target ranges.
- **Article template selector:** Standard, How-To, Listicle, Thought Leadership structures.
- **SEO/GEO/E-E-A-T:** focus keyword plus supporting keywords with natural placement; TL;DR/answer-first structuring for AI-answer visibility; distinct excerpt and meta description.
- **Voice fidelity check:** a second scoring call rates tone (0 to 10), cadence (0 to 10), and banned-jargon violations. Pass at tone >= 7, cadence >= 6, jargon = 0. Advisory in the Approval Gate (warning badge), not blocking.
- Generated compliance-report trailers are stripped from stored blog HTML.

#### FR-14: Social Post Generation
System generates platform-specific social posts from the same Brain Dump and BVP.
**Consequences (testable):**
- X post <= 280 chars; LinkedIn post 500 to 1,300 chars with line breaks.
- **Platform-native content:** where Meta platforms are connected, distinct Instagram caption, Facebook post, and Threads post copy are produced rather than reusing one text.
- Social generation runs standalone prompts tuned for voice parity with the blog.

#### FR-42: Assist Mode and Personal Voice Preservation
Generation preserves the user's own authored passages and offers an assist mode.
**Consequences (testable):**
- Passages the user wrote in the Brain Dump are detected and preserved rather than paraphrased away (information-gain classification).
- A `generation_mode` selection (default generate vs assist) tunes how heavily the model rewrites versus augments the user's own words.

#### FR-15: Generation Status Feedback
System returns 202 immediately and provides real-time status. Generation and publish tasks run as background tasks with persistent job records that survive process restarts.
**Consequences (testable):**
- Typewriter/loading state during generation; a "Generating" badge on the campaign list via job join.
- On failure the job and Campaign are set to `failed` with an error and a retry path; jitter backoff and cancel-on-timeout protect against provider slowness; fidelity and social generation run in parallel.

### 4.6 Image Generation

**Description:** Campaigns can include a custom AI-generated featured image via a configurable image provider. Social-only campaigns can also carry an image.

#### FR-16: Featured Image Generation
System generates a featured image from the blog title and content summary, with descriptive alt text and an SEO-slug filename, stored in Supabase Storage and served via CDN URL. Image failure never blocks the Campaign. Prompts are enriched with keyword, audience, and excerpt context.

#### FR-17: Image Preview, Regeneration, and Upload
User can preview the image, regenerate with an optional prompt override (capped per Campaign), replace it with an uploaded image, and edit alt text. Users can also upload their own inline images into the blog editor and replace the featured image (validated by type and magic bytes, stored in a public bucket, sanitized on all layers).

#### FR-43: Social Post Images
Social posts can carry a featured image, previewed per platform in the editors. Instagram requires an image; a square (1:1) image is generated for Instagram where applicable. (Per-platform image sizing beyond square Instagram is on the roadmap.)

### 4.7 Approval Gate

**Description:** The mandatory human review step. No Campaign publishes without explicit approval. This is a product principle.

#### FR-18: Campaign Review
User can view a full preview of all Campaign content: rendered blog HTML, each social post (with platform-appropriate formatting and character counts), and the featured image. Meta-platform context and per-platform notes appear where relevant.

#### FR-19: Inline Editing
User can edit any generated content before approving: blog as rich text (Tiptap WYSIWYG, with link rel/target control and inline images), social posts as plain text with live character counts. Edits overwrite the Campaign content; HTML is sanitized server-side.

#### FR-20: Approve Campaign
User can approve a Campaign, marking it ready for immediate or scheduled publishing. If no connections exist for the active Client, the user is prompted to connect one.

#### FR-21: Reject Campaign
User can reject with an optional reason (stored for analytics), returning the Campaign to a regenerable state.

#### FR-44: Post-Approval Editing and Scheduling
After approval, the user can still edit content, change the schedule, and re-publish. Scheduling presets and reschedule controls are available from the approved/published Campaign, and content edits after publish flow into Article revisions (§4.13).

### 4.8 Publishing

**Description:** The system publishes approved Campaigns to connected platforms via native APIs, immediately or scheduled. A destination picker lets the user choose exactly where each Campaign goes.

#### FR-22: Platform Connection Setup
User can connect a Client to publishing platforms:
- **WordPress (self-hosted):** site URL + Application Password, validated by a test call.
- **WordPress.com:** OAuth.
- **Webflow:** API token + Collection ID, validated.
- **X (Twitter):** OAuth 2.0 with PKCE.
- **LinkedIn:** OAuth; supports personal posting and, where enabled, company-page targets.
- **Instagram, Facebook Page, Threads:** via Meta OAuth (see §4.14).
- **GitHub Pages:** via GitHub App (see §4.11).
- **Headless Blog:** no external connection needed (see §4.13).

Credentials are encrypted at rest (AES-256-GCM). Connections use true brand icons and clear per-platform states; connection failures return specific errors. Connections are reusable and surfaced under a dedicated Connections nav item.

#### FR-23: Immediate Publishing
User can publish an approved Campaign immediately to selected connected platforms.
**Consequences (testable):**
- WordPress uses a draft-first pattern (create draft, upload featured media, then publish) to prevent broken live posts.
- Webflow via CMS API create + publish; X via API v2; LinkedIn via UGC Posts API.
- Each platform publish is independent; per-platform failure does not block others. NULL-content platforms are skipped silently (e.g., a LinkedIn-only social post does not post an empty tweet).
- Publish is deduplicated so re-publish does not double-post; a success toast names published and skipped platforms.

#### FR-24: Scheduled Publishing
User can schedule an approved Campaign (and batch-schedule a Roadmap) for future automatic publishing via APScheduler backed by persistent job records that recover on restart. Timezone is account-level. Scheduled Campaigns show on the dashboard and content calendar.

#### FR-25: Publishing Retry
User can retry failed platforms without regenerating content (capped attempts per platform), with clear per-platform error messages and re-publish support. Retry state is persisted.

#### FR-45: Platform Destination Picker
Before publishing or scheduling, the user selects destinations via a chip picker. Destinations are gated by capability (for example Instagram requires a featured image; Threads requires X-post content), and headless/blog-only versus social-only destinations are filtered by Campaign type.

### 4.9 Dashboard, Calendar and Content Roadmap

**Description:** The primary interface after login: Campaign status, the Brain Dump entry point, the content calendar, and the weekly content planner.

#### FR-26: Campaign List
User sees all Campaigns for the active Client (newest first) with title, status badge, dates, generating/roadmap badges, filter by status, and pagination. Clicking opens the Approval Gate. Re-voice is available on approved/published campaigns.

#### FR-27: Content Calendar
User sees a month calendar of published and scheduled Campaigns with platform icons and scheduled times, deep-linkable by month. Read-only.

#### FR-46: Content Roadmap ("Plan My Week")
User submits one Brain Dump and receives a full week of unique posts across platforms, reviewed as a grid and approved/scheduled in a batch.
**Consequences (testable):**
- A settings panel configures weekly cadence (LinkedIn 1 to 7, X 1 to 14, blog on/off) and image generation, pre-populated from and saved to per-Client roadmap config.
- Roadmaps consume a **separate roadmap credit** (Starter 1, Growth 4, Agency unlimited per cycle), not per-post campaign credits. A batch image budget allocates the remaining monthly image quota across posts.
- The engine generates a blog Campaign (full pipeline) and/or social-only Campaigns per slot, each linked by `roadmap_id`; roadmap status moves `pending → generating → ready → failed`.
- A week-review grid shows every generated post for batch approval; posts distribute across the week and sync status back to the roadmap.

### 4.10 Trial and Conversion

**Description:** Users start on a 14-day trial. Trial expiration is handled cleanly to protect the funnel.

#### FR-28: Trial Expiration
When a 14-day trial expires without subscribing, the user enters a restricted state.
**Consequences (testable):**
- User can log in and view existing data but cannot create Campaigns, generate, or publish.
- A persistent upgrade banner appears; in-app nudges fire at day 10 and day 13.
- Data is preserved for 30 days post-expiration, then scheduled for deletion with a 7-day warning email.
- A day-3 re-engagement email nudges trial users who have created no Campaign (§4.15).

### 4.11 GitHub Blog Publishing

**Description:** Users connect a Client to GitHub repositories via a GitHub App, and PersonnaPress detects the static site generator and publishes AI-generated posts into the repo in the correct format, defaulting to a Pull Request for human review. Supports Jekyll, Astro, Next.js (markdown/MDX), Hugo, Eleventy, and plain static sites. (Docusaurus and MkDocs remain deferred, see §6.)

#### FR-29: GitHub App Repository Connection
User installs the PersonnaPress GitHub App on selected repos and links a repo to a Client. Installation tokens are encrypted at rest; the connection card shows repo name and detected framework.

#### FR-30: Repository Framework Detection
System scans a connected repo (root config files, directory structure) and returns the detected generator with a confidence score and a proposed publish path, presenting candidates when ambiguous.

#### FR-31: GitHub Publish, Jekyll and Plain Static
Publishes to Jekyll (`_posts/YYYY-MM-DD-slug.md` with YAML front matter including author and categories) or plain static (HTML/Markdown at the configured root). PR-first by default; direct commit opt-in per connection.

#### FR-32: GitHub Publish, Astro, Next.js, Hugo, Eleventy
Publishes MDX/Markdown to the detected collection/content location per framework, with front matter (title, description, date, tags, author), prompting for the target folder when the Next.js pattern is ambiguous.

#### FR-33: GitHub Publish, Docusaurus and MkDocs
Deferred (see §6). Original intent: Docusaurus `blog/` conventions and MkDocs blog-plugin path.

#### FR-34: PR-First Publish Workflow
Publishing defaults to opening a Pull Request (new branch, title from H1, body with file path and front matter preview). PR link is surfaced in the Approval Gate. Campaign transitions to `published` on PR merge (via GitHub webhook, fail-closed signature validation) or immediately on direct commit. GitHub front matter includes description and tags.

#### FR-35: GitHub Publisher Landing Page
A public SSG marketing page at `/github-publisher` targets developer-blogger search intent with a framework-detection demo, a comparison table, JSON-LD, and a sign-up CTA.

### 4.12 Content Providers (Configurable)

**Description:** Text, image, and transcription generation run through configurable providers rather than a single hardcoded vendor.

#### FR-47: Configurable LLM Provider
Text generation dispatches through an `LLM_PROVIDER` setting. Google Gemini 2.5 Flash is the default (thinking budgets tuned per task: 0 social, 512 blog, 1024 voice extraction, 256 voice-brief/fidelity); Anthropic Claude (Haiku 4.5) is a supported alternative. The Gemini model is configurable via env, logged at startup.

#### FR-48: Configurable Image Provider
Image generation dispatches through `IMAGE_PROVIDER` / `IMAGE_MODEL`. Replicate FLUX.1 [pro] and Google's Nano Banana Pro (Gemini image) are supported, both producing alt text and SEO-slug filenames.

### 4.13 Headless Blog Delivery

**Description:** Blog content is a first-class, versioned Article stored in PersonnaPress and delivered to customer websites through a public read-only API. "Headless Blog" is a publish destination alongside WordPress, Webflow, and GitHub. This deliberately brings content revision history into scope.

#### FR-49: Article Model and Revision History
Publishing a Campaign creates or updates an Article (title from H1, unique per-Client slug, excerpt, meta description, tags, category, featured image, reading time, status `published`/`hidden`). Every content-field change snapshots a new revision (`initial`/`edit`/`restore`); status-only changes do not. An idempotent backfill converts existing published campaigns into `hidden` Articles for review. Article creation never fails a publish job.

#### FR-50: Public Delivery API and Delivery Tokens
A public read-only API (`/public/v1/*`) serves a Client's published Articles authenticated by a delivery token.
**Consequences (testable):**
- App users create, list, and revoke named delivery tokens (`ppd_` prefix; only the hash and prefix are stored; raw token shown once).
- `GET /public/v1/articles` returns paginated published-only list items (no full HTML), with tag/category filters; `GET /public/v1/articles/{slug}` returns full sanitized HTML plus an `seo` object (meta, OpenGraph, schema.org Article JSON-LD, reading time); `GET /public/v1/tags` returns tags/categories with counts.
- Mounted as a sub-application with its own permissive-read CORS, ETag/Cache-Control/304 support, and per-token rate limiting.
- Isolation is enforced and tested: a token for Client A can never read Client B's Articles; hidden Articles and drafts are never reachable; revoked tokens 401.

#### FR-51: Edit After Publish and Revision UI
A "Blog" section lists the active Client's Articles. Users edit live Articles (content and metadata) in the editor, with a slug-change warning, a revision history panel (preview and restore any revision; restore appends a new revision), and a hide/unhide toggle. "Headless Blog" appears as a no-connection publish destination.

#### FR-52: Developer Docs and Cluster Page
A public `/headless-blog-api` page documents the delivery API with copy-paste integration examples (plain fetch, Next.js App Router, Astro) against the real API, a response-bundle showcase, a comparison table, and FAQ/JSON-LD for AEO.

#### FR-53: PersonnaPress Company Blog
The marketing site runs its own blog at `/blog` powered by the headless delivery API (ISR list + detail), dogfooding the product with no backend changes.

### 4.14 Meta Platform Publishing

**Description:** Instagram, Facebook Page, and Threads are first-class publishing destinations, connected via a single Meta OAuth flow, completing social coverage. Gated behind a `META_PUBLISHING_ENABLED` feature flag pending Meta Business App review; development proceeds in sandbox mode.

#### FR-54: Meta Connection and OAuth
A single Meta OAuth flow discovers and connects the user's Instagram Business Account, Facebook Page, and Threads account, exchanging for long-lived tokens and upserting per-platform connections. Locked/disabled state shown while the flag is off. Long-lived tokens auto-renew.

#### FR-55: Instagram / Facebook / Threads Publishing
- **Instagram:** container-based image post (caption from platform-native or LinkedIn copy, truncated to 2,200 chars); requires a featured image.
- **Facebook Page:** feed post with message and optional image link.
- **Threads:** text post from the X-post content (within the 500-char limit).
- Each is an independently selectable destination chip with per-platform results; failures are isolated per platform.

Meta-specific reliability fixes, a Facebook Page picker, standalone Threads OAuth, a beta gate + support page, and error sanitization (no credential leakage) are included.

### 4.15 Email and Lifecycle Communications

**Description:** Transactional and lifecycle email, plus pre-launch list building, via Resend. (This supersedes the original "in-app notifications only" constraint.)

#### FR-56: Transactional Email
All transactional emails (verification, deletion warning, welcome) use a branded Paper Style HTML template with a support reply-to alias.

#### FR-57: Lifecycle and Re-engagement Email
A day-3 re-engagement email nudges trialing users with zero Campaigns (idempotent, scheduled daily). A welcome email fires on verification / new Google signup.

#### FR-58: Pre-launch Email Capture
An email-capture widget on public pages (homepage, pricing, about, blog) adds subscribers to a Resend audience, with duplicate-safe success handling, rate limiting, and server-side validation.

### 4.16 Marketing and Public Pages

**Description:** Public, SEO/AEO/GEO-optimized pages that drive acquisition and position the platform.

#### FR-59: Marketing Pages
Public pages include the landing/homepage, `/pricing`, `/about` (founder story + Person schema), `/github-publisher`, `/headless-blog-api`, and `/brand-voice-generator`. All follow the human-first SEO constraints (no AI tropes, no em-dashes), include JSON-LD, sitemap/robots entries, and legal pages with bot protection.

#### FR-60: Positioning and Keyword Strategy
The homepage is positioned as "the AI content platform that publishes in your brand voice" (pivoted from "AI blog writer"), targeting the "AI content platform" cluster, with "brand voice generator" as the primary differentiator landing page. Feature-page titles follow the [Feature] + [Action] + [Platform] pattern.

## 5. Product Principles (Non-Negotiable)

- **Human approval before publish.** Every Campaign requires explicit approval. Nothing auto-publishes.
- **Voice fidelity is the product.** Generation is always calibrated to the Client's Brand Voice Profile, and scored against it.
- **Fully cloud-based.** No local/on-device inference. Providers are cloud APIs (configurable).
- **Content ownership stays with the user.** PersonnaPress retains no rights to republish or reuse generated content beyond delivering the service.
- **No em-dashes and no double-dashes in generated copy or prompts.** Sentences are restructured naturally instead.
- **Paper Style, Lucide icons only, no emojis** across the product UI.

## 6. Roadmap (Deferred / In Progress)

- **Mobile responsive web (Epic 22, in progress).** A focused responsiveness pass (mobile nav/drawer, dashboard and Brain Dump, approval gate, connections/modals, calendar/roadmap reflow) using existing Tailwind breakpoints; no native app. Some surfaces already shipped.
- **GitHub Docusaurus and MkDocs publishing (FR-33).** Deferred within the GitHub epic.
- **Platform-native image sizing for social.** Beyond square Instagram, per-platform aspect-ratio variants (dual image generation) are deferred.
- **Meta general availability.** Live behind the `META_PUBLISHING_ENABLED` flag pending Meta Business App review; the three-condition gate (audit passed, <1% Phase-1 publish failure over 30 days, 100+ active paying users) governs GA.
- **Team/multi-user accounts and RBAC.** Not built.
- **Post-performance analytics.** Not built.
- **Multi-language content generation.** Not built.
- **Annual billing and usage overage.** Monthly-only, hard limits.

## 7. Success Metrics

**Primary**
- **SM-1: Time to First Publish**: median account-creation-to-first-publish under 15 minutes.
- **SM-2: Weekly Active Publishers**: 40% of paying users publish at least one Campaign or Roadmap per week by Month 3.
- **SM-3: Voice Fidelity Approval Rate**: 80% of generated Campaigns approved on first review.

**Secondary**
- **SM-4: Multi-Platform Adoption**: 60% of active users connect 2+ platforms.
- **SM-5: Agency Adoption**: 15% of paying users manage 2+ Clients.
- **SM-6: Publish Success Rate**: 99% of approved Campaigns publish successfully to all selected platforms.
- **SM-7: Roadmap Adoption**: share of active users who plan a week via "Plan My Week." `[ASSUMPTION: target TBD post-launch.]`

**Counter-metrics (do not optimize)**
- **SM-C1:** Do not push generation speed below ~30s if it degrades voice fidelity or SEO structure.
- **SM-C2:** Approval rate must not rise via blander, safer output. Monitor "too generic" rejection reasons.

## 8. Monetization

| Plan | Monthly Price | Clients | Campaigns/Month | Weekly Roadmaps/Month | Image Generations | Platforms |
|---|---|---|---|---|---|---|
| **Starter** | $29/mo | 2 | 10 | 1 | 10 | All |
| **Growth** (most popular) | $49/mo | 5 | 30 | 4 | 30 | All |
| **Agency** | $149/mo | 20 | Unlimited | Unlimited | 100 | All |

- **Trial:** 14-day free trial on the Growth plan, no credit card.
- **Checkout:** Stripe Checkout (in-app plan picker) for new subscriptions; Stripe Customer Portal for management. Older Stripe prices remain active for existing subscribers.
- **Billing:** monthly only. Annual billing is on the roadmap.
- **Overage:** hard limits with an upgrade prompt; no pay-per-use overage. Roadmap credits are independent of campaign credits.

## 9. Constraints and Guardrails

### 9.1 Privacy and Data Ownership
- **Content ownership:** users own all generated content; Terms of Service state this explicitly.
- **Credential storage:** all third-party platform credentials and tokens are encrypted at rest (AES-256-GCM), with the key in an environment variable, never in the database. `[ASSUMPTION: env-var key management is sufficient pre-scale; KMS/HSM is a later upgrade.]`
- **Delivery tokens** are stored only as SHA-256 hashes; raw tokens are shown once.
- **Voice audio** is transcribed via external inference and never persisted to disk, storage, or the database.
- **Provider data usage:** content sent to the configured LLM, image, and transcription providers is subject to those providers' data policies and must be disclosed in the Privacy Policy. `[ASSUMPTION: paid provider tiers do not train on submitted data. Verify per provider.]`

### 9.2 Cost Controls and Rate Limiting
- Per-user generation, image, and roadmap caps enforced at the tier level.
- LLM thinking budgets tuned per task; image regenerations and batch image budgets capped.
- Backend rate limiting per user; voice transcription and public delivery API each rate-limited.
- Outbound publishing is staggered per platform to avoid rate walls.
- Provider resilience: repeated 5xx/429 from a provider fails the Campaign with a clear message rather than retrying indefinitely; jitter backoff and cancel-on-timeout are applied. A second LLM provider is now available as a fallback lever (FR-47).
- Per-user API cost logging for internal monitoring; not exposed to users.

### 9.3 Licensing
- Generated images are subject to the configured image provider's output license (for example FLUX.1 [pro] commercial terms via Replicate). Terms of Service must reflect the active provider(s).

## 10. Cross-Cutting NFRs

- **Performance:** blog + social + image generation within ~120s at p95; frontend interactive within 2s on 4G.
- **Availability:** `[ASSUMPTION: 99.5% target. Supabase manages Postgres; the FastAPI Droplet is a single point of failure with no failover yet.]`
- **Security:** HTTPS/TLS 1.3; session-token auth; no plaintext credentials; parameterized queries, output encoding on rendered user content, multi-layer HTML sanitization (client DOMPurify + server nh3 + BeautifulSoup), CSRF origin checks, OAuth scope minimization, AES-256-GCM at rest; public delivery API isolation is test-enforced.
- **Scalability:** Supabase Postgres removes the DB bottleneck; the FastAPI Droplet is the compute ceiling with a documented Droplet-size upgrade path; Supabase Storage scales media independently.
- **Data integrity:** Supabase Postgres with PITR (Pro plan); durable CDN-backed storage.
- **Observability:** structured JSON logging for API, generation, and publish events; error tracking (Sentry or equivalent).
- **Job durability:** all generation, transcription, publishing, scheduling, and retry work is backed by persistent job records that survive restarts.

## 11. Platform and Architecture (summary)

- **Web app:** Next.js (App Router) on Vercel; responsive Paper Style design.
- **Backend API:** Python FastAPI on a DigitalOcean Droplet (systemd + Nginx reverse proxy); background tasks + APScheduler for generation, publishing, scheduling.
- **Database:** Supabase Postgres for all application data (users, subscriptions, clients, campaigns, roadmaps, articles + revisions, jobs, platform connections, delivery tokens).
- **File storage:** Supabase Storage (uploaded brand content, generated and uploaded images) with CDN URLs.
- **Providers:** configurable LLM (Gemini default, Anthropic supported), image (Replicate FLUX.1 [pro] / Google Nano Banana Pro), transcription (OpenAI Whisper), email (Resend).
- **Billing:** Stripe (Checkout + Customer Portal + webhooks).
- **Auth:** email/password + Google OAuth.
- Full architecture rationale and data model are in `addendum.md`.

## 12. Aesthetic and Tone

PersonnaPress's own voice follows the Paper Style aesthetic: minimal, direct, confident. Calm authority, specific and actionable error messages, no SaaS enthusiasm, no exclamation marks, no emoji, no em-dashes or double-dashes.

## 13. Open Questions

1. **SEO keyword input depth:** the Brain Dump now accepts focus + supporting keywords. Confirm whether further inferred-target tuning is needed (affects FR-13).
2. **Image style control:** how much visual direction should users get beyond regenerate + prompt override + upload?
3. **GDPR technical compliance:** policy/ToS disclosures are the current scope; data-export and right-to-deletion endpoints and cookie consent remain deferred. `[BLOCKER: Legal review of Privacy Policy and ToS, including delivery API and Meta processors.]`
4. **Provider data policies:** confirm paid-tier no-training terms for each active provider (LLM, image, transcription).
5. **Roadmap success metric target (SM-7).**
6. **Meta GA timing:** dependent on Meta Business App review.
7. **Supabase plan tier:** confirm Pro ($25/mo) for PITR and connection limits at current scale.

## 14. Assumptions Index (open)

| ID | Section | Assumption |
|---|---|---|
| A-1 | §2.2 | Content generation tuned for English only |
| A-2 | §4.1 FR-2 | 7-day session duration |
| A-3 | §4.3 | ~300-word threshold for low-confidence voice flag |
| A-4 | §4.4 FR-40 | 10 MB audio cap; hourly transcription rate limit |
| A-5 | §8 | Pricing $29 / $49 / $149; 14-day no-card trial on Growth |
| A-6 | §8 | Monthly-only billing; hard limits, no overage |
| A-7 | §9.1 | Env-var key management sufficient pre-scale |
| A-8 | §9.1 | Paid provider tiers do not train on submitted data (verify per provider) |
| A-9 | §10 | 99.5% uptime target; single-Droplet API with no failover |
| A-10 | §10 | Supabase Pro plan for PITR and higher limits |
| A-11 | §6 | Meta GA gate: audit passed + <1% Phase-1 failure over 30 days + 100+ paying users |
| A-12 | §7 | SM-7 roadmap-adoption target TBD |

---

*Change history: v2.0 (2026-08-17) re-baselined this PRD from the pre-launch v1 plan (Epics 1 to 7) to the shipped product state (through Epic 23). Capabilities previously deferred or excluded and now live: voice-to-text Brain Dump (Epic 9), Meta/Instagram/Facebook/Threads publishing (Epic 21), email lifecycle (Epic 19), content revision history and headless delivery (Epic 12), configurable second LLM provider and alternate image provider (Epic 3 additions). New capability areas added: Deep Brand Voice Profile (Epic 16), Content Roadmap / Plan My Week (Epic 20), Headless Blog Delivery (Epic 12), marketing/positioning pages (Epics 8, 13, 18, 23). Pricing revised (Epic 8.9). See git history and `epics.md` for story-level detail.*
