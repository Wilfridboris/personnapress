---
title: PersonnaPress
created: 2026-06-14
updated: 2026-06-14
status: final
---

# PRD: PersonnaPress

## 0. Document Purpose

This PRD defines the v1 commercial launch of PersonnaPress — an AI content automation platform that learns a user's writing voice and publishes SEO-structured blog posts and social campaigns across multiple platforms. It is written for the product owner, designer, and engineering team. Features are grouped with globally-numbered functional requirements (FR-N) nested under each feature section. Assumptions made during fast-path drafting are tagged inline as `[ASSUMPTION]` and indexed in §14. This PRD builds on four existing inputs: `full.prd.md` (concept brief), `design.prd.md` (Paper Style design system), `architecture.prd.md` (split-architecture spec), and `research.md` (tech stack audit) — all located at the project root.

## 1. Vision

Content-driven founders, coaches, and agency owners in North America know that consistent publishing drives growth — but writing takes 3–6 hours per article, and AI tools produce generic output that sounds nothing like them. The result: sporadic publishing, off-brand content, or expensive ghostwriters.

PersonnaPress solves this by learning the user's exact writing style from their existing content, then turning rough ideas ("Brain Dumps") into SEO-ranked blog posts and matching social campaigns — all in their authentic voice. Nothing publishes without human approval. The system handles the entire pipeline from idea to live post across WordPress, Webflow, X, and LinkedIn.

The product's core bet is that voice fidelity — not just content generation — is the unlock. Generic AI writing tools are a commodity. A tool that writes *as you* and publishes *for you* across platforms is a workflow replacement, not just a writing assistant.

## 2. Target User

### 2.1 Jobs To Be Done

- **Functional:** "I need to publish a blog post and matching social posts every week without spending half a day writing."
- **Functional:** "I need my content to rank on Google, not just exist."
- **Emotional:** "I want my content to sound like me — not like every other AI-generated post."
- **Social:** "I want my audience to see me as a consistent, authentic thought leader."
- **Contextual:** "I have 20 minutes between meetings — I want to dump my idea and have a draft waiting for me later."
- **Functional (Agency):** "I manage content for multiple clients and need each client's voice maintained separately."
- **Emotional (Agency):** "I need my clients to not realize I'm using AI — each client's content must sound distinctly like them, not like a template."

### 2.2 Non-Users (v1)

- **Enterprise marketing teams** with existing content management systems, approval chains, and compliance workflows. PersonnaPress v1 has no RBAC, no approval chains beyond single-user approve/reject, and no SSO.
- **Users who need to publish to Meta/Instagram/Threads.** These platforms are deferred to Phase 2.
- **Users who want a full CMS.** PersonnaPress generates and publishes content — it does not manage an existing content library, handle comments, or provide analytics dashboards.
- **Non-English content creators.** `[ASSUMPTION: v1 supports English-language content only. Multi-language generation is Phase 3+.]`

### 2.3 Key User Journeys

- **UJ-1. Sarah onboards and publishes her first blog post.**
  - **Persona + context:** Sarah is a SaaS founder who blogs monthly but wants to go weekly. She just signed up.
  - **Entry state:** Authenticated, first login, no clients or brand profiles configured.
  - **Path:** (1) System prompts her to create her first client profile — she enters her company name and website URL. (2) PersonnaPress scrapes her site and extracts a Brand Voice Profile; she reviews the tone descriptors and banned-jargon list, edits one entry, confirms. (3) She's prompted to enter her first Brain Dump — she pastes three bullet points about a product update. (4) System generates a blog draft (HTML preview) and social posts (X + LinkedIn). She reads the blog, tweaks one paragraph inline, and approves. (5) System prompts her to connect WordPress — she enters her site URL and Application Password. (6) She hits Publish. Blog goes live on WordPress, social posts go live on X and LinkedIn.
  - **Climax:** Sarah sees her blog post live on her WordPress site, written in her voice, with a generated featured image — 12 minutes after she pasted three bullet points.
  - **Resolution:** Campaign status shows "Published" with links to all live posts. She's back on the dashboard with an empty Brain Dump input ready for next time.
  - **Edge case:** If Sarah has no existing website content, Brand Ingestion falls back to a manual voice questionnaire (tone sliders, sample text input, example URLs from writers she admires). `[ASSUMPTION: Fallback questionnaire is the mechanism for users with no scrapable content.]`

- **UJ-2. Marcus runs his weekly content routine.**
  - **Persona + context:** Marcus is a business coach who publishes weekly. Brand Voice Profile and platform connections are already configured.
  - **Entry state:** Authenticated, returning user, dashboard view.
  - **Path:** (1) Marcus clicks "New Campaign," types a Brain Dump about a coaching framework he discussed with a client. (2) System generates blog + social drafts in under 90 seconds. (3) He reviews the blog preview, sees one sentence that's off-brand, edits it. Approves. (4) He sets a scheduled publish time for Thursday 8 AM. (5) On Thursday at 8 AM, the system publishes to all connected platforms.
  - **Climax:** Marcus checks his phone Thursday morning and sees LinkedIn engagement on a post he wrote in 5 minutes on Monday.
  - **Resolution:** Campaign status is "Published." Dashboard shows the next empty slot.

- **UJ-3. Jenna manages content for three agency clients.**
  - **Persona + context:** Jenna runs a small marketing agency. She manages content for three clients, each with distinct brand voices and platform connections.
  - **Entry state:** Authenticated, dashboard showing client list.
  - **Path:** (1) Jenna selects Client A from her client list. (2) She enters a Brain Dump based on notes from her client call. (3) System generates drafts using Client A's Brand Voice Profile. (4) She reviews, approves, and publishes to Client A's WordPress and LinkedIn. (5) She switches to Client B and repeats the workflow.
  - **Climax:** Three clients' weekly content published in under 30 minutes total.
  - **Resolution:** Dashboard shows all three clients with "Published" status for this week.

## 3. Glossary

- **Brain Dump** — Raw, unstructured user input (text, bullet points) that serves as the creative brief for a Campaign. One Brain Dump produces one Campaign.
- **Brand Voice Profile** — A structured JSON representation of a Client's writing style, extracted from their existing content. Contains Tone descriptors, Cadence patterns (sentence rhythm and structure), and a Banned Jargon list. Used by the generation engine to match the Client's authentic voice.
- **Campaign** — The atomic unit of content production. One Campaign contains exactly one blog post (HTML), one X post (text), one LinkedIn post (text), and one featured image. A Campaign progresses through a status lifecycle: `pending_approval → approved → published` (or `rejected` / `failed`).
- **Client** — A brand identity with its own Brand Voice Profile and platform connections. A single PersonnaPress account can manage multiple Clients. For solo users, their Client is themselves.
- **Approval Gate** — The mandatory human review step before any Campaign is published. Nothing auto-publishes.
- **Platform Connection** — An authenticated link between a Client and an external publishing platform (WordPress, Webflow, X, LinkedIn). Stores credentials required to publish on the Client's behalf.
- **Brand Ingestion** — The process of analyzing a Client's existing website content and/or uploaded text to extract a Brand Voice Profile.
- **Featured Image** — An AI-generated image (via FLUX.1 [pro] on Replicate) that accompanies the blog post in a Campaign.

## 4. Features

### 4.1 Account Management

**Description:** Users sign up, log in, and manage their account. Authentication is the entry point for all other features. `[ASSUMPTION: Email/password authentication with Google OAuth (via Google Cloud) as an alternative. No SSO or SAML in v1.]`

**Functional Requirements:**

#### FR-1: User Registration

User can create an account with email and password or via Google OAuth (Google Cloud OAuth 2.0 client credentials). Realizes UJ-1.

**Consequences (testable):**
- System creates a user record and sends a verification email on signup.
- User cannot access any features until email is verified. `[ASSUMPTION: Email verification is required before first use.]`
- Google OAuth users skip email verification.

#### FR-2: User Authentication

Registered user can log in via email/password or Google OAuth (via Google Cloud) and receive a session token.

**Consequences (testable):**
- Session persists across browser tabs for 7 days. `[ASSUMPTION: 7-day session duration.]`
- Invalid credentials return a generic error (no credential enumeration).

#### FR-3: Subscription Management

Authenticated user can view their current plan, upgrade, downgrade, or cancel their subscription via Stripe Customer Portal. Realizes monetization model. For trial expiration behavior, see §4.10 FR-28.

**Consequences (testable):**
- User sees their current plan tier, usage (Campaigns created this billing cycle), and renewal date.
- Upgrade takes effect immediately; downgrade takes effect at next billing cycle.
- Cancellation retains access until the end of the current billing period.

### 4.2 Client Management

**Description:** Users create and manage Client profiles — the brand identities that content is generated for. Solo users have one Client (themselves). Agency users manage multiple Clients. Realizes UJ-1, UJ-3.

**Functional Requirements:**

#### FR-4: Create Client

Authenticated user can create a new Client by providing a name and optional website URL.

**Consequences (testable):**
- Client record is created with an empty Brand Voice Profile.
- If a website URL is provided, Brand Ingestion (§4.3) is triggered automatically.
- Client count is enforced per subscription tier. Attempting to exceed the limit returns an error with an upgrade prompt.

#### FR-5: Edit Client

User can update a Client's name, website URL, and Brand Voice Profile.

**Consequences (testable):**
- Changing the website URL triggers a re-run of Brand Ingestion with a confirmation prompt.
- Brand Voice Profile edits (tone descriptors, banned jargon) are saved immediately and applied to all future Campaigns.

#### FR-6: Delete Client

User can delete a Client and all associated Campaigns and Platform Connections.

**Consequences (testable):**
- System shows a destructive-action confirmation with the Client name and Campaign count.
- Deletion cascades to all Campaigns, Platform Connections, and the Brand Voice Profile.

#### FR-7: List and Switch Clients

User can view all their Clients and switch active context between them. Realizes UJ-3.

**Consequences (testable):**
- Dashboard always shows which Client is currently active.
- Switching Clients loads that Client's Campaign history, Brand Voice Profile, and Platform Connections.

### 4.3 Brand Voice Ingestion

**Description:** The system analyzes a Client's existing content to extract a Brand Voice Profile — the structured representation of how they write. This is PersonnaPress's core differentiator: the profile drives voice fidelity in all generated content. Ingestion runs automatically when a Client is created with a website URL, or manually when the user uploads content. Realizes UJ-1.

**Functional Requirements:**

#### FR-8: Website Scraping

System can scrape a provided website URL and extract text content from blog posts, about pages, and other public-facing written content.

**Consequences (testable):**
- System extracts at least the 10 most recent blog posts (or all posts if fewer than 10). `[ASSUMPTION: 10-post extraction threshold.]`
- Non-content elements (navigation, footers, ads, boilerplate) are stripped.
- Scraping completes within 60 seconds for sites with up to 50 pages. `[ASSUMPTION: 60-second scraping timeout.]`
- If the URL is unreachable or returns no parseable content, the system surfaces an error and offers the manual fallback (FR-10).

#### FR-9: Content Upload

User can upload text files (.txt, .md, .docx) or paste raw text to supplement or replace scraped content.

**Consequences (testable):**
- Uploaded content is appended to scraped content (if any) before voice extraction. Uploaded files are stored in Supabase Storage.
- Maximum upload size is 5 MB per file, 10 files per Client. `[ASSUMPTION: Upload limits.]`

#### FR-10: Voice Profile Extraction

System uses Gemini 2.5 Flash to analyze collected content and produce a Brand Voice Profile containing: Tone (e.g., "authoritative but conversational"), Cadence (sentence rhythm — average sentence length, variation patterns, paragraph structure), and Banned Jargon (overused words and phrases the user avoids).

**Consequences (testable):**
- Profile is stored as structured JSON on the Client record.
- User can review and edit every field of the extracted profile before it's finalized.
- Extraction uses a Gemini thinking budget of 1024 tokens for reasoning depth.
- If no content is available (no URL, no uploads), the system falls back to a manual voice questionnaire: tone sliders, sample text input, and example URLs from writers the user admires. `[ASSUMPTION: Manual voice questionnaire is the fallback mechanism.]`

#### FR-11: Voice Profile Refresh

User can trigger a re-extraction of the Brand Voice Profile at any time using updated website content or new uploads.

**Consequences (testable):**
- Re-extraction overwrites the existing profile after user confirmation.
- Previous profile is not versioned in v1. `[ASSUMPTION: No profile version history in v1.]`

### 4.4 Brain Dump Capture

**Description:** The user inputs their raw idea — unstructured text or bullet points — which becomes the creative brief for content generation. The Brain Dump is the primary input surface and should feel effortless. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-12: Text Brain Dump

User can enter free-form text or bullet points as a Brain Dump for the active Client.

**Consequences (testable):**
- Input field uses monospace typography (per design spec) and auto-expands.
- Minimum input: 20 characters. `[ASSUMPTION: Minimum input length to prevent empty/trivial generations.]`
- Maximum input: 10,000 characters. `[ASSUMPTION: Maximum input length for cost control.]`
- Submitting a Brain Dump creates a new Campaign in `pending_approval` status and triggers content generation (§4.5).

**Notes:** Voice note input (mentioned in `full.prd.md`) is deferred to v2. `[NOTE FOR PM: Voice-to-text Brain Dump is a high-value feature for the "20 minutes between meetings" JTBD — revisit for v2 if adoption data supports it.]`

### 4.5 Content Generation

**Description:** The core generation engine. Takes a Brain Dump and Brand Voice Profile as input and produces a complete Campaign: SEO-structured blog post (HTML), X post, and LinkedIn post — all written in the Client's voice. Uses Gemini 2.5 Flash. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-13: Blog Post Generation

System generates an SEO-structured blog post in HTML from the Brain Dump, conforming to the Client's Brand Voice Profile.

**Consequences (testable):**
- Output includes: title (H1), meta description, structured headings (H2/H3), body paragraphs, and a conclusion.
- Blog post uses semantic HTML suitable for WordPress/Webflow rendering.
- Word count targets 800–1,500 words. `[ASSUMPTION: Blog length target range.]`
- Generation uses a Gemini thinking budget of 512 tokens.
- **Voice fidelity check:** After generation, the system runs a second Gemini call (thinking budget 256) that scores the draft against the Client's Brand Voice Profile on three dimensions: tone alignment (0–10), cadence match (0–10), and banned-jargon violations (count). The draft passes if tone >= 7, cadence >= 6, and jargon violations = 0. This check is advisory in v1 — a failing score surfaces a warning badge ("Voice match: 6/10 — review tone") in the Approval Gate but does not block the user from approving. If SM-3 (approval rate) falls below 70%, re-evaluate whether the check should become blocking. `[ASSUMPTION: Advisory voice check with 7/6/0 thresholds is the v1 mechanism. Re-evaluation trigger tied to SM-3.]`

**Notes:** The voice fidelity check is the product's core differentiator mechanism. Alternatives considered: embedding similarity scoring (requires training data infrastructure), human A/B evaluation (does not scale), no check (relies entirely on prompt quality). The advisory second-call approach was chosen for v1 because it provides signal without blocking workflow, and the scoring thresholds can be tuned per-Client in v2.

#### FR-14: Social Post Generation

System generates platform-specific social posts from the same Brain Dump and Brand Voice Profile.

**Consequences (testable):**
- X post is ≤ 280 characters (text only, no threads in v1). `[ASSUMPTION: Single-tweet, no threads in v1.]`
- LinkedIn post is 500–1,300 characters with line breaks for readability. `[ASSUMPTION: LinkedIn post length range.]`
- Both posts reference or tease the blog content without duplicating it.
- Social post generation uses a Gemini thinking budget of 0 (no chain-of-thought — fast, direct output).

#### FR-15: Generation Status Feedback

System returns a 202 Accepted response immediately and provides real-time status updates during generation. Generation and publish tasks run as FastAPI BackgroundTasks with persistent job records in the database so that in-flight work survives process restarts.

**Consequences (testable):**
- Frontend shows a typewriter-effect loading state (per design spec) during generation.
- A job record is created in Supabase Postgres when generation starts, tracking task type, status, timestamps, and error details. The frontend polls this record for progress.
- If generation fails (Gemini API error, timeout), the job record and Campaign status are set to `failed` with an error message, and the user is prompted to retry.
- If the backend process restarts mid-generation, the job record persists and can be retried automatically or by the user.
- Total generation time for blog + social posts is under 90 seconds for typical inputs. `[ASSUMPTION: 90-second generation target.]`

### 4.6 Image Generation

**Description:** Each Campaign includes a custom AI-generated featured image produced by FLUX.1 [pro] via the Replicate API. The image accompanies the blog post when published. Realizes UJ-1.

**Functional Requirements:**

#### FR-16: Featured Image Generation

System generates a featured image based on the blog post title and content summary.

**Consequences (testable):**
- Image is generated as a 1200x630 PNG (Open Graph dimensions). `[ASSUMPTION: OG image dimensions as default.]`
- Image is uploaded to Supabase Storage and served via its CDN-backed public URL.
- Image generation prompt is derived from the blog title + a style directive aligned with the Client's brand.
- If image generation fails, the Campaign still proceeds — the user is notified and can retry image generation independently.

#### FR-17: Image Preview and Regeneration

User can preview the generated image and request a new generation with an optional prompt override.

**Consequences (testable):**
- User sees the image alongside the blog preview in the Approval Gate.
- "Regenerate" button triggers a new FLUX.1 [pro] call. Previous image is replaced in Supabase Storage.
- Maximum 3 regenerations per Campaign. `[ASSUMPTION: Regeneration cap for cost control.]`

### 4.7 Approval Gate

**Description:** The mandatory human review step. No Campaign publishes without explicit user approval. This is a product principle, not just a feature — it protects brand integrity and builds user trust. Realizes UJ-1, UJ-2.

**Functional Requirements:**

#### FR-18: Campaign Review

User can view a full preview of all Campaign content: blog post (rendered HTML), X post, LinkedIn post, and featured image.

**Consequences (testable):**
- Blog preview renders the HTML as it would appear on the target CMS.
- Social posts display with platform-appropriate formatting (character count for X, line breaks for LinkedIn).
- Featured image displays at full resolution.

#### FR-19: Inline Editing

User can edit any generated content directly in the preview before approving.

**Consequences (testable):**
- Blog post is editable as rich text (WYSIWYG). `[ASSUMPTION: Rich text editor for blog edits, not raw HTML.]`
- Social posts are editable as plain text with live character count.
- Edits are saved to the Campaign record, overwriting the generated content.

#### FR-20: Approve Campaign

User can approve a Campaign, which marks it as ready for immediate or scheduled publishing.

**Consequences (testable):**
- Campaign status transitions from `pending_approval` to `approved`.
- If no Platform Connections exist for the active Client, the system prompts the user to connect at least one platform before publishing.

#### FR-21: Reject Campaign

User can reject a Campaign with an optional reason, which returns it to draft state for regeneration.

**Consequences (testable):**
- Campaign status transitions to `rejected`.
- User can trigger regeneration from the same Brain Dump (generates new content, resets to `pending_approval`).
- Rejection reason is stored on the Campaign record for analytics. `[ASSUMPTION: Rejection reason stored for future product improvement.]`

### 4.8 Publishing

**Description:** The system publishes approved Campaigns to connected platforms via their native APIs. Supports immediate and scheduled publishing. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-22: Platform Connection Setup

User can connect a Client to external publishing platforms by providing API credentials.

**Consequences (testable):**
- WordPress: User provides site URL + Application Password. System validates by making a test API call.
- Webflow: User provides API Bearer Token + target Collection ID. System validates access.
- X (Twitter): OAuth 2.0 with PKCE flow — user authorizes via Twitter's OAuth screen.
- LinkedIn: OAuth 2.0 flow — user authorizes via LinkedIn's OAuth screen with `w_member_social` scope.
- Credentials are encrypted at rest using AES-256-GCM before storage. `[ASSUMPTION: AES-256-GCM encryption for credential storage.]`
- Connection validation fails gracefully with a specific error message (e.g., "WordPress returned 401 — check your Application Password").

#### FR-23: Immediate Publishing

User can publish an approved Campaign immediately to all connected platforms.

**Consequences (testable):**
- Blog post is published to WordPress using a draft-first pattern: POST to WP REST API v2 with `status: "draft"`, upload featured image as featured media, then PATCH to `status: "publish"` only after both succeed. If the publish step fails, the draft is cleaned up. This prevents partial/broken posts from going live.
- Blog post is published to Webflow via CMS API v2 create + separate publish endpoint.
- X post is published via Twitter API v2 (OAuth 2.0 PKCE).
- LinkedIn post is published via UGC Posts API (`/v2/ugcPosts`, version header `202602`).
- Each platform publish is independent — failure on one does not block others.
- Campaign status transitions to `published` only when all connected platforms succeed. Partial failures set status to `failed` with per-platform error details. **Note:** v1 does not distinguish between full failure and partial failure — both show as `failed`. If 3 of 4 platforms succeed, those posts are already live; the `failed` status reflects the incomplete set. A `partially_published` status is a v2 consideration.

#### FR-24: Scheduled Publishing

User can set a future date/time for an approved Campaign to publish automatically. Uses the persistent job pattern (FR-15).

**Consequences (testable):**
- User selects date and time via a datetime picker. `[ASSUMPTION: Timezone is set at account level, not per-campaign.]`
- Scheduled Campaigns show in the dashboard with their scheduled time and are visible on the content calendar.
- A persistent job record is written to Supabase Postgres with the Campaign ID, scheduled time, and status. APScheduler reads from this table on startup to recover pending jobs.
- APScheduler triggers publishing at the scheduled time via the FastAPI BackgroundTasks worker pattern.
- If scheduled publishing fails, the job record captures the failure detail, Campaign status is set to `failed`, and the user is notified. `[ASSUMPTION: Notification is in-app only, no email notifications in v1.]`

#### FR-25: Publishing Retry

User can retry a failed publish on specific platforms without regenerating content. Uses the persistent job pattern (FR-15).

**Consequences (testable):**
- Failed platforms are listed with their error messages.
- Retry attempts the publish again for only the failed platforms. Each retry creates or updates the persistent job record with attempt count and failure details.
- Maximum 3 retry attempts per platform per Campaign. `[ASSUMPTION: Retry cap.]`
- If the backend restarts between retries, the job record persists and the user can trigger the next retry on return.

### 4.9 Dashboard

**Description:** The primary interface after login. Shows Campaign status across all Clients, provides the Brain Dump entry point, and surfaces the content calendar. `[ASSUMPTION: Dashboard exists as the primary navigation surface — not explicitly defined in inputs but required by all user journeys.]`

**Functional Requirements:**

#### FR-26: Campaign List

User sees a list of all Campaigns for the active Client, ordered by creation date (newest first).

**Consequences (testable):**
- Each Campaign shows: title, status badge (`pending_approval` / `approved` / `published` / `rejected` / `failed`), creation date, and publish date (if published).
- List is filterable by status.
- Clicking a Campaign opens the Approval Gate view (FR-18).

#### FR-27: Content Calendar

User sees a calendar view of published and scheduled Campaigns. The calendar is included in v1 because agency users (UJ-3) managing multiple Clients need to spot scheduling conflicts and gaps across a week/month — the list view (FR-26) doesn't surface temporal distribution. Realizes UJ-3.

**Consequences (testable):**
- Calendar shows month view by default.
- Published Campaigns show with linked platform icons.
- Scheduled Campaigns show with a clock icon and scheduled time.
- `[ASSUMPTION: Calendar is read-only in v1 — no drag-and-drop rescheduling.]`

### 4.10 Trial and Conversion

**Description:** Users start on a free trial (see §8 for plan details and duration). The system must handle trial expiration cleanly to protect the conversion funnel and avoid data-loss anxiety.

**Functional Requirements:**

#### FR-28: Trial Expiration

When a user's 14-day trial expires without subscribing, the system transitions them to a restricted state.

**Consequences (testable):**
- On trial expiration, the user can log in and view existing Campaigns, Clients, and Brand Voice Profiles, but cannot create new Campaigns, generate content, or publish.
- A persistent upgrade banner appears on every page: "Your trial has ended. Subscribe to continue publishing."
- All existing data (Clients, Campaigns, Brand Voice Profiles, Platform Connections) is preserved for 30 days after trial expiration. `[ASSUMPTION: 30-day data retention after trial expiration.]`
- After 30 days of inactivity post-trial, the account and all associated data are scheduled for deletion with a 7-day warning email. `[ASSUMPTION: 30+7 day retention-then-deletion policy.]`
- Upgrade prompts appear at day 10 (4 days remaining) and day 13 (1 day remaining) as in-app notifications. `[ASSUMPTION: In-app nudge timing.]`

## 5. Non-Goals (Explicit)

- **PersonnaPress is not a local/on-device tool.** The original concept brief described a "local/cloud-hybrid LLM agent." v1 is fully cloud-based: Gemini 2.5 Flash via Google's API, FLUX.1 [pro] via Replicate, Supabase for data. Local inference is not planned for any version — the complexity and hardware requirements conflict with the target user's profile (founders and coaches, not ML engineers). If privacy-sensitive users demand local processing, re-evaluate as a v3+ consideration.
- **PersonnaPress is not a CMS.** It generates and publishes content to external platforms. It does not manage existing content libraries, handle comments, or provide website hosting.
- **PersonnaPress is not an analytics platform.** v1 does not track post performance, engagement metrics, or SEO rankings. `[NOTE FOR PM: Analytics integration is a high-value v2 feature — users will ask for it immediately.]`
- **PersonnaPress does not auto-publish.** Every Campaign requires explicit human approval. This is a product principle, not a limitation.
- **PersonnaPress does not support team collaboration in v1.** No multi-user accounts, no role-based permissions, no approval chains. Single-user accounts only.
- **PersonnaPress does not generate long-form content** (whitepapers, ebooks, email sequences). One Brain Dump = one blog post + social posts.
- **PersonnaPress does not manage social media accounts** beyond posting. No comment management, no DM handling, no follower analytics.
- **No voice-to-text input in v1.** Brain Dumps are text-only.
- **No Meta/Instagram/Threads publishing in v1.** Deferred to Phase 2 (see §6.2).

## 6. MVP Scope

### 6.1 In Scope

- User registration and authentication (email/password + Google OAuth via Google Cloud)
- Subscription billing and plan enforcement via Stripe
- Client CRUD (multi-client support)
- Brand Voice Ingestion (website scraping + file upload to Supabase Storage + manual fallback)
- Text-based Brain Dump capture
- Blog post generation (SEO-structured HTML) via Gemini 2.5 Flash
- Social post generation (X + LinkedIn) via Gemini 2.5 Flash
- Featured image generation via FLUX.1 [pro] on Replicate, stored in Supabase Storage
- Inline content editing in approval view
- Approve/reject workflow
- Publishing to WordPress, Webflow, X, LinkedIn
- Scheduled publishing via APScheduler with persistent job records in Supabase Postgres
- Persistent job records for generation, publishing, and retry operations (survive backend restarts)
- Campaign dashboard with status tracking
- Content calendar (read-only)
- Credential encryption at rest (AES-256-GCM)
- Supabase Postgres for all application data
- Supabase Storage for all file uploads and generated assets

### 6.2 Out of Scope for MVP

- **Meta/Instagram/Threads publishing** — Deferred to Phase 2. Trigger conditions: (1) Meta's screencast audit process is completed and API access is approved, (2) Phase 1 platform publish failure rate is below 1% sustained over 30 days, (3) at least 100 active paying users on Phase 1 platforms. `[ASSUMPTION: These three conditions define the Phase 2 gate.]`
- **Voice-to-text Brain Dump** — Deferred to v2. Requires speech-to-text integration and adds input parsing complexity. `[NOTE FOR PM: High-value for the "between meetings" JTBD. Revisit if early user interviews surface demand.]`
- **Post analytics and performance tracking** — Deferred to v2. Requires platform API read access and dashboard investment.
- **Team/multi-user accounts** — Deferred to v2. Requires RBAC, invite flows, and approval chains.
- **Content revision history** — v1 stores only the final approved version. No diff or version rollback.
- **Email notifications** — v1 uses in-app notifications only.
- **Dark mode** — Not in v1 design spec.
- **Mobile-native apps** — v1 is responsive web only.
- **Multi-language content generation** — v1 is English only.
- **Thread generation for X** — v1 generates single tweets only.
- **Custom image style training** — v1 uses prompt-based image generation without fine-tuned models.

## 7. Success Metrics

**Primary**

- **SM-1: Time to First Publish** — Median time from account creation to first published Campaign is under 15 minutes. Validates FR-1, FR-4, FR-8, FR-10, FR-12, FR-13, FR-22, FR-23. `[ASSUMPTION: 15-minute target for onboarding-to-publish.]`
- **SM-2: Weekly Active Publishers** — 40% of paying users publish at least one Campaign per week by Month 3 post-launch. Validates FR-12, FR-13, FR-14, FR-23. `[ASSUMPTION: 40% WAP target.]`
- **SM-3: Voice Fidelity Approval Rate** — 80% of generated Campaigns are approved on first review (not rejected for voice/quality issues). Validates FR-10, FR-13, FR-14.

**Secondary**

- **SM-4: Multi-Platform Adoption** — 60% of active users connect 2+ publishing platforms. Validates FR-22.
- **SM-5: Agency Adoption** — 15% of paying users manage 2+ Clients. Validates FR-4, FR-7.
- **SM-6: Publish Success Rate** — 99% of approved Campaigns publish successfully to all connected platforms. Validates FR-23, FR-24.

**Counter-metrics (do not optimize)**

- **SM-C1: Generation Speed at Expense of Quality** — Average generation time should not be optimized below 30 seconds if it degrades voice fidelity or SEO structure. Counterbalances SM-1.
- **SM-C2: Approval Rate via Lowered Standards** — Approval rate (SM-3) should not rise because the system generates bland, safe content. Monitor rejection reasons for "too generic" as a signal. Counterbalances SM-3.

## 8. Monetization

`[ASSUMPTION: Three-tier subscription model. Pricing benchmarked against Jasper ($49/mo starter), Copy.ai ($49/mo), and Lately ($49/mo). PersonnaPress undercuts on entry to capture the solopreneur segment and prices up for agency value.]`

| Plan | Monthly Price | Clients | Campaigns/Month | Image Generations | Platform Connections |
|---|---|---|---|---|---|
| **Starter** | $29/mo | 1 | 10 | 10 | All 4 |
| **Growth** | $79/mo | 5 | 30 | 30 | All 4 |
| **Agency** | $199/mo | 20 | Unlimited | 100 | All 4 |

- **Trial:** 14-day free trial on the Growth plan (no credit card required). `[ASSUMPTION: No-card trial for lower friction.]`
- **Billing:** Monthly billing only in v1. Annual billing (with discount) in v2. `[ASSUMPTION: Monthly-only billing in v1.]`
- **Overage:** When a user hits their Campaign or image generation limit, further generations are blocked with an upgrade prompt. No pay-per-use overage in v1. `[ASSUMPTION: Hard limits, no overage billing.]`

## 9. Constraints and Guardrails

### 9.1 Privacy and Data Ownership

- **Content ownership:** Users own all generated content. PersonnaPress retains no rights to republish, sublicense, or use generated content for any purpose other than delivering the service. Terms of Service must state this explicitly.
- **Credential storage:** All third-party platform credentials (WordPress Application Passwords, Webflow tokens, X OAuth tokens, LinkedIn OAuth tokens) are encrypted at rest using AES-256-GCM. Encryption keys are managed via environment variables on the backend server, not stored in the database. `[ASSUMPTION: Encryption key management via environment variables is sufficient for v1. HSM or KMS-based key management is a Phase 2 security upgrade.]`
- **Brain Dump data:** Raw Brain Dump text is stored in the database for the lifetime of the Campaign. Users can delete Campaigns (and their Brain Dumps) at any time.
- **Gemini API data:** Content sent to Google Gemini 2.5 Flash for generation is subject to Google's API data usage policy. PersonnaPress must disclose this in its Privacy Policy. `[ASSUMPTION: Google's paid API tier does not use submitted data for model training — verify before launch.]`
- **FLUX.1 [pro] data:** Image generation prompts sent to Replicate are subject to Replicate's data usage policy. Disclose in Privacy Policy.

### 9.2 Cost Controls and Rate Limiting

- **Per-user generation caps:** Enforced at the subscription tier level (see §8). Prevents runaway API spend.
- **Gemini token budgets:** Thinking budget is tuned per task type — 0 for social posts, 512 for blog drafts, 1024 for voice extraction. These caps bound per-request cost.
- **FLUX.1 [pro] image caps:** Image generations are capped per plan tier per billing cycle. Regeneration attempts are capped at 3 per Campaign (FR-17).
- **Backend rate limiting:** The FastAPI backend enforces request rate limits per user session to prevent abuse. `[ASSUMPTION: Rate limit of 10 requests per minute per user.]`
- **External API rate-limit mitigation:** Scheduled publishing can batch-fire API calls when multiple Campaigns are scheduled at the same time. The backend must stagger outbound API calls with per-platform delays (e.g., 2-second intervals between X posts, 5-second intervals between LinkedIn posts) to avoid hitting platform rate walls. X API calls use `tweet.fields` selective parameters to reduce rate-limit pressure. `[ASSUMPTION: Staggered outbound publishing with 2–5 second intervals.]`
- **LLM provider resilience:** Gemini 2.5 Flash is a single-provider dependency. If the Gemini API returns 5xx errors or rate-limits (429) for more than 3 consecutive attempts, the system sets the Campaign to `failed` with a "Generation service temporarily unavailable — retry in a few minutes" message rather than silently retrying indefinitely. `[NOTE FOR PM: Evaluate adding a fallback model provider (e.g., Claude, GPT-4o) if Gemini availability becomes a recurring issue post-launch. Single-provider simplicity is acceptable for v1 launch scale.]`
- **Cost monitoring:** `[ASSUMPTION: The system logs per-user API costs (Gemini + Replicate) for internal monitoring but does not expose cost data to users in v1.]`

### 9.3 Licensing

- **FLUX.1 [pro]:** Commercial license obtained via Black Forest Labs / Replicate API. Terms permit commercial use of generated images by end users. PersonnaPress Terms of Service must reflect that generated images are produced by FLUX.1 [pro] and are subject to its output license.

## 10. Cross-Cutting NFRs

- **Performance:** Content generation (blog + social + image) completes within 120 seconds for 95th percentile requests. Frontend is interactive within 2 seconds on a 4G connection.
- **Availability:** `[ASSUMPTION: 99.5% uptime target. Supabase provides managed Postgres with built-in availability. The FastAPI Droplet remains a single point of failure for the API layer — no failover in v1.]`
- **Security:** All API traffic over HTTPS (TLS 1.3). Frontend-to-backend communication authenticated via session tokens. No plaintext credentials stored anywhere. Specific mitigations: parameterized queries for all database access (SQL injection), output encoding for user-submitted content rendered in HTML previews (XSS), CSRF protection via origin checking on state-changing requests, credential encryption at rest (AES-256-GCM), OAuth token scoping to minimum required permissions per platform.
- **Scalability:** Supabase Postgres removes the database bottleneck. The FastAPI Droplet ($6 DO, 1 vCPU / 1 GB) remains the compute ceiling for concurrent generation/publish tasks. Upgrade path: $12 Droplet (2 vCPU / 2 GB) before ~50 concurrent generation requests. Beyond that, container orchestration or managed compute is required. Supabase Storage handles media scaling independently.
- **Data integrity:** Supabase Postgres with point-in-time recovery (PITR) on Pro plan. Supabase Storage provides durable, CDN-backed file hosting. `[ASSUMPTION: Supabase Pro plan ($25/mo) is used for PITR and higher limits.]`
- **Observability:** Structured JSON logging for all API requests, generation events, and publish events. Error tracking via Sentry or equivalent. `[ASSUMPTION: Observability stack is added for launch — not in architecture doc.]`
- **Job durability:** All generation, publishing, and scheduling tasks are backed by persistent job records in Supabase Postgres. Process restarts do not lose in-flight or scheduled work.

## 11. Platform

- **Web application:** Next.js (App Router) on Vercel. Responsive design — desktop-first with mobile breakpoints.
- **Design system:** "Paper Style" — brutalist, academic, Notion-esque aesthetic. Full spec in `design.prd.md`.
- **Backend API:** Python FastAPI on DigitalOcean Droplet ($6/mo), managed via systemd + Nginx reverse proxy. Handles generation, publishing, and scheduling via BackgroundTasks + APScheduler.
- **Database:** Supabase Postgres for all application data (users, clients, campaigns, job records, platform connections).
- **File storage:** Supabase Storage for uploaded brand content and generated assets (FLUX images). CDN-backed public URLs.
- **Billing:** Stripe for subscription management, payment processing, and Customer Portal.
- **Authentication:** Email/password + Google OAuth via Google Cloud (OAuth 2.0 client credentials).
- **No native mobile apps in v1.** Responsive web serves mobile users.

## 12. Aesthetic and Tone

PersonnaPress's own voice (in UI copy, onboarding, error messages, marketing) follows the "Paper Style" design aesthetic: minimal, direct, confident. No exclamation marks in UI copy. No "Hey there!" informality. Think Notion's product voice crossed with a literary magazine editor.

- **Tone:** Calm authority. "Your draft is ready" not "Your draft is ready!"
- **Error messages:** Specific and actionable. "WordPress returned 401 — check your Application Password" not "Something went wrong."
- **Anti-references:** No SaaS enthusiasm. No "supercharge your content." No gradient-heavy, emoji-laden, or gamified interfaces.

## 13. Open Questions

1. **Voice questionnaire design:** What specific questions/sliders comprise the manual voice fallback (FR-10) when no content is available for scraping? Needs UX design. `[BLOCKER: UX]`
2. **SEO keyword input:** Should the Brain Dump accept optional target keywords, or should the system infer SEO targets from the topic? Affects FR-13.
3. **Image style control:** How much control does the user have over the featured image style? Just regenerate, or can they specify visual direction?
4. **Webflow Collection mapping:** How does the user specify which Webflow Collection to publish to? Needs UX for Collection ID selection. `[BLOCKER: UX]`
5. **GDPR compliance scope:** PersonnaPress targets North America but may serve EU users. GDPR compliance in v1 is scoped to Privacy Policy and Terms of Service disclosures (data usage, third-party processors, retention periods). Technical compliance (data export API, right-to-deletion endpoint, cookie consent mechanism) is deferred to v1.1 — these are engineering tasks that should not block initial launch. `[BLOCKER: Legal — Privacy Policy and ToS must be reviewed before launch.]`
6. **Google Gemini data policy verification:** Confirm that the paid API tier does not use submitted content for model training.
7. **Onboarding email sequence:** Does the product need drip emails post-signup, or is the in-app onboarding flow sufficient?
8. **Supabase plan tier:** Confirm Supabase Pro ($25/mo) is required for PITR and connection pooling, or whether the free tier is sufficient for launch scale.

## 14. Assumptions Index

| ID | Section | Assumption |
|---|---|---|
| A-1 | §2.2 | v1 supports English-language content only |
| A-2 | §4.1 FR-1 | Email/password + Google OAuth (via Google Cloud) authentication; no SSO/SAML |
| A-3 | §4.1 FR-1 | Email verification required before first use |
| A-4 | §4.1 FR-2 | 7-day session duration |
| A-5 | §4.3 FR-8 | 10-post extraction threshold for website scraping |
| A-6 | §4.3 FR-8 | 60-second scraping timeout |
| A-7 | §4.3 FR-9 | Upload limits: 5 MB per file, 10 files per Client |
| A-8 | §4.3 FR-10 | Manual voice questionnaire is the fallback for no-content users |
| A-9 | §4.3 FR-11 | No profile version history in v1 |
| A-10 | §4.4 FR-12 | Minimum input 20 characters, maximum 10,000 characters |
| A-11 | §4.5 FR-13 | Blog word count target: 800–1,500 words |
| A-12 | §4.5 FR-13 | Advisory voice check with 7/6/0 thresholds; re-evaluation trigger tied to SM-3 |
| A-13 | §4.5 FR-14 | Single tweet only, no threads in v1 |
| A-14 | §4.5 FR-14 | LinkedIn post length: 500–1,300 characters |
| A-15 | §4.5 FR-15 | 90-second generation time target |
| A-16 | §4.6 FR-16 | OG image dimensions (1200x630) as default |
| A-17 | §4.6 FR-17 | 3-regeneration cap per Campaign for cost control |
| A-18 | §4.7 FR-19 | Rich text (WYSIWYG) editor for blog edits |
| A-19 | §4.7 FR-21 | Rejection reason stored for analytics |
| A-20 | §4.8 FR-22 | AES-256-GCM encryption for credential storage |
| A-21 | §4.8 FR-24 | Timezone set at account level |
| A-22 | §4.8 FR-24 | In-app notifications only, no email in v1 |
| A-23 | §4.8 FR-25 | 3 retry attempts per platform per Campaign |
| A-24 | §4.9 FR-27 | Calendar is read-only in v1 |
| A-25 | §4.9 | Dashboard exists as primary navigation surface |
| A-26 | §6.2 | Phase 2 trigger: Meta audit passed + <1% failure rate + 100 active users |
| A-27 | §7 | 15-minute Time to First Publish target |
| A-28 | §7 | 40% Weekly Active Publishers target |
| A-29 | §8 | Three-tier pricing: $29/$79/$199 |
| A-30 | §8 | 14-day free trial, no credit card required |
| A-31 | §8 | Monthly billing only in v1 |
| A-32 | §8 | Hard limits, no overage billing |
| A-33 | §9.1 | Env var key management sufficient for v1 |
| A-34 | §9.1 | Google paid API does not train on submitted data |
| A-35 | §9.2 | 10 requests/minute/user rate limit |
| A-36 | §9.2 | Per-user API cost logging for internal use |
| A-37 | §9.2 | Staggered outbound publishing with 2–5 second intervals |
| A-38 | §10 | 99.5% uptime target |
| A-39 | §10 | Supabase Pro plan ($25/mo) used for PITR and higher limits |
| A-40 | §10 | Observability stack (logging + error tracking) added for launch |
| A-41 | §4.10 FR-28 | 30-day data retention after trial expiration |
| A-42 | §4.10 FR-28 | 30+7 day retention-then-deletion policy |
| A-43 | §4.10 FR-28 | In-app upgrade nudges at day 10 and day 13 |
