---
name: PersonnaPress
status: final
created: 2026-06-14
updated: 2026-06-14
sources:
  - _bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md
  - design.prd.md
  - _bmad-output/planning-artifacts/architecture.md
---

# PersonnaPress — Experience Spine

## Foundation

Desktop-first responsive web on Next.js App Router. Raw Tailwind CSS — no component library baseline. `DESIGN.md` is the visual identity reference; this spine owns behavior, states, and interactions only. Desktop breakpoint is 1024px+; tablet 768–1023px; mobile <768px.

Single-user, multi-client workspace. Each user manages one or more Clients (brand identities); all content is generated and published within the context of one active Client at a time. No team collaboration in v1.

Form-factor note: the product is a desktop tool first. Mobile is supported for light use (reviewing Campaigns, approving scheduled posts) but the Brain Dump and Approval Gate flows are designed for a keyboard + screen experience. Mobile users who approve are served; mobile users who write are accommodated, not optimized for.

## Information Architecture

| Surface | Path | Reached from | Purpose |
|---|---|---|---|
| Dashboard | `/dashboard` | Login / sidebar "Dashboard" | Campaign list for active Client; Brain Dump entry point |
| Brain Dump | `/dashboard/new` | Dashboard "New Campaign" CTA | Focused text input that creates a Campaign and triggers generation |
| Approval Gate | `/campaigns/[id]` | Dashboard campaign row | Review, edit, approve/reject, schedule, publish a Campaign |
| Client Management | `/clients` | Sidebar "Clients" | List all Clients; create, edit, delete |
| Client Detail | `/clients/[id]` | Client list row | Brand Voice Profile, Platform Connections for one Client |
| Brand Voice Setup | `/clients/[id]/voice` | Client Detail; onboarding step 2 | Review/edit extracted profile or run the manual questionnaire |
| Platform Connections | `/clients/[id]/connections` | Client Detail | Connect/disconnect WordPress, Webflow, X, LinkedIn |
| Content Calendar | `/calendar` | Sidebar "Calendar" | Read-only month-view of published and scheduled Campaigns |
| Account | `/account` | Sidebar bottom avatar link | Profile, subscription plan, billing via Stripe portal |
| Onboarding | `/onboarding` | First login redirect | 3-step flow: Create Client → Brand Ingestion → First Brain Dump |

Sidebar is the persistent navigation shell. Client switcher occupies the sidebar header. Active Client context persists across Dashboard, Approval Gate, and Calendar surfaces. Client Management and Account are client-agnostic.

Modal stacks one level maximum. No dialogs opened on top of dialogs. Confirmation dialogs (destructive actions) are the only exception pattern — they overlay the surface that triggered them.

→ Spine wins on conflict with any mockup or imported asset.

## Voice and Tone

Microcopy. Brand voice and aesthetic posture live in `DESIGN.md § Brand & Style`.

The product speaks with calm authority. It treats the user as a competent professional managing a real workflow. No hedging, no cheerleading, no apologies for being a software product.

| Situation | Do | Don't |
|---|---|---|
| Generation complete | "Your draft is ready." | "Your draft is ready! 🎉" |
| Generation in progress | "Drafting your blog post..." | "Hang tight! Magic is happening..." |
| Approval prompt | "Review and approve before publishing." | "Take a look at what we made!" |
| Error state | "WordPress returned 401 — check your Application Password." | "Something went wrong. Please try again." |
| Empty Campaign list | "No campaigns yet. Start with a Brain Dump." | "You haven't created any content yet! Click below to get started!" |
| Empty Calendar | "Nothing scheduled. Approve a campaign to see it here." | "Your calendar is empty — let's change that!" |
| Trial expiry banner | "Your trial has ended. Subscribe to continue publishing." | "Oops! Looks like your trial ran out!" |
| Destructive confirm | "Delete 'TechFounder Blog'? This will remove 12 campaigns and all platform connections." | "Are you sure?" |
| Publish success | "Published to WordPress, X, and LinkedIn." | "Boom! Your content is live! 🚀" |
| Voice score warning | "Voice match: 6/10 — review tone before approving." | "Hmm, this might not sound quite like you." |

Error messages name the platform, the HTTP status code (when applicable), and the resolution path. System-generated, AI-generated, and user-edited content each have distinct visual treatments (monospace for generation output, WYSIWYG for edited content) to preserve clarity about provenance.

## Component Patterns

Behavioral. Visual specs live in `DESIGN.md § Components`.

| Component | Use | Behavioral rules |
|---|---|---|
| Campaign row | Dashboard list | Click anywhere opens Approval Gate. Status badge updates optimistically on approve/reject. Hover applies card-active shadow. |
| Brain Dump textarea | Brain Dump page | Auto-expands vertically. Minimum 20 chars enforced with inline counter below: "N / 10,000 characters." Submit disabled below minimum. No submit on Enter — use the Submit button (prevents accidental generation). |
| Typewriter generation display | Brain Dump → Approval Gate transition | Fills the full page content area during generation. Character-by-character reveal in JetBrains Mono. Status line below cycles: "Analyzing your voice profile..." → "Drafting blog post..." → "Checking voice fidelity..." → "Generating featured image..." → "Done." |
| Blog WYSIWYG editor | Approval Gate | Rendered HTML editable via contenteditable or lightweight rich-text editor. Toolbar: Bold, Italic, Link, H2, H3, Blockquote, Undo. No raw HTML toggle in v1. |
| Social post editors | Approval Gate | Plain textarea per platform. Live character counter: X shows "N / 280", LinkedIn shows "N / 1300." Counter turns Danger color at 95% capacity. |
| Featured image panel | Approval Gate | Image rendered at full panel width. "Regenerate" button below with remaining count: "Regenerate image (2 of 3 remaining)." Button disabled at 0 remaining. |
| Voice score badge | Approval Gate header | Shown only when voice fidelity score fails threshold. Danger-color label: "VOICE MATCH: N/10 — REVIEW TONE." Clicking expands inline detail: per-dimension breakdown (tone, cadence, jargon). Does not block Approve. |
| Approve / Reject actions | Approval Gate footer | "Approve" primary button. "Reject" secondary button. Clicking Reject opens a confirmation dialog with optional reason textarea. Both disabled while a publish or generation job is in flight. |
| Schedule picker | Approval Gate | Appears inline below Approve button after approval. Datetime picker. Shows resolved timezone next to the input: "Schedules in America/New_York." Confirm sets the scheduled time; Cancel discards without changing status. |
| Client switcher | Sidebar header | Dropdown showing all Client names. Active client has a check mark. Switching client navigates to Dashboard with the new active context. |
| Platform connection card | Platform Connections | Shows platform name, connection status (connected / not connected), connected account identifier (e.g., "@handle", "site.com"). "Connect" CTA opens OAuth popup or inline credential form. "Disconnect" triggers a confirmation dialog. |
| Webflow Collection selector | Platform Connections / Connection setup | Appears after successful Webflow OAuth. Dropdown populated from Webflow CMS API collections list. If the API call fails, falls back to a text input with a documentation link. [ASSUMPTION] |
| Voice questionnaire | Brand Voice Setup (fallback) | Three-step wizard. Step 1: three tone slider pairs (Formal↔Casual, Professional↔Friendly, Concise↔Elaborate), each 1–5. Step 2: up to 3 sample text paste areas labeled "Paste a piece of writing that sounds like you." Step 3 (optional): up to 3 URL fields labeled "A writer whose style you admire." Submit triggers extraction. [ASSUMPTION] |
| Content Calendar | Calendar surface | Month view, read-only. Published campaigns show with platform icons (WP, Webflow, X, LinkedIn) on the date. Scheduled campaigns show with a clock icon and time. Clicking a date entry navigates to the Approval Gate for that Campaign. No drag-to-reschedule in v1. [ASSUMPTION per PRD A-24] |
| Upgrade banner | Global (post-trial) | Full-width sticky bar, top of viewport. Non-dismissible. Disappears on subscription activation. Shown above sidebar and content — pushes layout down, does not overlay. |
| Retry panel | Approval Gate (failed Campaign) | Shown when Campaign status is `failed`. Lists each platform with its error message and a per-platform "Retry" button. Shows attempt count: "Attempt 1 of 3." |

## State Patterns

| State | Surface | Treatment |
|---|---|---|
| Initial page load | All | Skeleton placeholders match layout: sidebar links, campaign rows, form fields. No spinner — layout holds shape while data loads. |
| Empty Campaign list | Dashboard | Center of content pane. H2 "No campaigns yet." Body: "Start with a Brain Dump and publish your first post." Primary CTA: "New Campaign." |
| Generating | Brain Dump → Approval Gate | Typewriter animation fills content area. Navigation away is blocked with a confirm dialog: "Generation is in progress. Leaving will not cancel it — your draft will be available on the Dashboard when complete." |
| Generation failed | Dashboard (campaign row) | Campaign row status badge shows Failed (danger red). Row expands to show error message. "Retry" link in the row. |
| Approval Gate: pending | Approval Gate | Full content loaded. Blog preview, social posts, image all visible. Approve / Reject footer always visible (sticky). |
| Approval Gate: approved, not yet published | Approval Gate | Approval section replaced by schedule picker. "Publish now" and "Schedule" CTAs. |
| Approval Gate: published | Approval Gate | Footer replaced by "Published" status summary: date, time, platform links ("View on WordPress →"). Read-only. Content still visible for reference. |
| Approval Gate: rejected | Approval Gate | "Rejected" status shown. "Regenerate from same Brain Dump" primary CTA. Optional: edit Brain Dump before regenerating. |
| Approval Gate: failed | Approval Gate | Retry panel shown (see Component Patterns). |
| Brand ingestion: in progress | Client Detail / Onboarding | Progress indicator: "Scraping [url]..." then "Extracting voice profile..." in monospace label type. |
| Brand ingestion: complete | Brand Voice Setup | Voice Profile fields pre-populated. User reviews; each field is editable. "Confirm profile" primary CTA. |
| Brand ingestion: failed (no scrapable content) | Brand Voice Setup | Error message: "Couldn't extract content from [url]. Complete the voice questionnaire to set up your profile." Primary CTA opens voice questionnaire. |
| Platform connection: OAuth pending | Platform Connections | Popup open indicator. Connection card shows "Connecting..." label. Popup completion updates card to "Connected" without page reload. |
| Platform connection: credential validation fail | Platform Connections | Inline error below form: "[Platform] returned [status] — [actionable message]." Form remains open for correction. |
| Trial expiring: day 10 | All authenticated surfaces | In-app notification (top-right toast, non-blocking): "4 days left on your trial. Subscribe to keep publishing." Dismissible. |
| Trial expiring: day 13 | All authenticated surfaces | Same pattern, more urgent copy: "1 day left. Subscribe now to avoid interruption." |
| Trial expired | All authenticated surfaces | Upgrade banner appears. New Campaign, generation, and publish CTAs disabled. Clicking disabled CTAs shows upgrade prompt. All data still visible. |
| Offline | Global | One-time toast: "You're offline. Changes won't save until you reconnect." |

## Interaction Primitives

**Primary input: keyboard + mouse.** The product does not require power-user keyboard shortcuts (unlike a task tool). The primary keyboard interactions are tab-order navigation, form submission, and WYSIWYG editing.

**Critical keyboard behaviors:**
- `Tab` order matches DOM reading order on every surface. No tab traps outside modals and dialogs.
- In modals/dialogs: `Esc` closes. Tab cycles within the modal only. `Enter` on the confirm button fires the action.
- In Brain Dump: `Cmd/Ctrl + Enter` submits (as an affordance for power users); the primary button is still required for mouse users. `Esc` does not clear the input — it does nothing (prevents accidental loss of long inputs).
- In WYSIWYG editor: standard text editor shortcuts (`Cmd/Ctrl + B`, `Cmd/Ctrl + I`, `Cmd/Ctrl + Z` for undo). Toolbar provides mouse access to the same actions.
- In social post editors: `Tab` moves between X and LinkedIn editors in sequence, then to the next action.

**Banned interaction patterns:**
- Drag-to-reorder in v1.
- Hover-only affordances on `sm` viewports (mobile tap reveals what desktop hover reveals).
- Auto-advance (no automatic navigation after an action unless it is the only sensible next surface — e.g., post-submission of Brain Dump navigates to the generation waiting screen).
- Infinite scroll — all lists are paginated (Dashboard Campaign list: 20 per page).
- Confirmation dialogs for non-destructive actions. Only destructive actions get confirms.

**Touch:** All interactive elements minimum 44px touch target height. Swipe gestures not used in v1.

## Accessibility Floor

Behavioral. Visual contrast is defined in `DESIGN.md § Colors` (Paper/Ink at #F9F9F6/#111111 passes WCAG AA at all type sizes; Highlighter/Ink badge passes AA for large text at badge scale; Danger/White and Success/White pass AA).

- **WCAG 2.2 AA** across all surfaces.
- **Page announcements:** Screen reader announces surface on navigation: "Dashboard — PersonnaPress", "Approval Gate — [Campaign title]", "Calendar — Month view."
- **Status badges:** Never rely on color alone. Badge text ("PENDING APPROVAL", "PUBLISHED") is always present alongside color.
- **Typewriter animation:** Provides `aria-live="polite"` region for the status message line. The character-reveal animation itself is `aria-hidden`; only status messages are announced.
- **Forms:** All inputs have visible labels (not placeholder-only). Error messages are associated via `aria-describedby`.
- **Modals:** `role="dialog"` with `aria-labelledby` pointing to the dialog heading. Focus moves to the dialog on open; returns to the trigger on close.
- **Images:** Featured images in Approval Gate have descriptive `alt` text generated from the blog title: "AI-generated featured image for: [title]."
- **WYSIWYG editor:** Toolbar buttons have accessible labels. Content area has `role="textbox" aria-multiline="true"` with an `aria-label` describing its purpose.
- **Calendar:** Each calendar day cell has `aria-label` including the date and campaign count: "June 17, 2026, 2 campaigns scheduled."
- **Reduced motion:** Typewriter animation wraps in `prefers-reduced-motion` check. When reduced motion is preferred, generation feedback uses a simple "Generating..." text with a pulsing opacity only.

## Responsive & Platform

| Breakpoint | Behavior |
|---|---|
| `≥ lg` (1024px+) | Full left sidebar (240px). Dashboard shows Campaign list with sidebar visible. Approval Gate: two-panel layout — blog preview left, social posts + image right. |
| `md` (768–1023px) | Sidebar collapses to icon-only (56px). Content area expands. Approval Gate: single column, blog first, then social, then image. |
| `< md` (< 768px) | Sidebar becomes slide-in drawer triggered by hamburger in top bar. Top bar: Logo, hamburger, client name. Approval Gate: single column stack. Brain Dump is full-screen. |

The Approval Gate on `lg` uses a specific two-panel layout: left panel (blog WYSIWYG, ~60% width) / right panel (social posts, image, voice score, action footer). This layout is not present at `md` or below.

Minimum supported browser: current major version minus 2 (Chrome, Safari, Firefox, Edge). No IE.

## Onboarding Flow

_Triggered on first login. Replaced by Dashboard on completion. User cannot navigate away from onboarding until it is complete or explicitly skipped (skip link available at Step 1)._

### Step 1: Create Your First Client

- Surface: Centered card on Paper background. No sidebar.
- H1 (Playfair): "Who are you writing for?"
- Body: "A Client is the brand voice you're building. Start with yours."
- Form fields: Client name (required), Website URL (optional but recommended).
- Primary CTA: "Create client and analyze voice"
- Skip link (below CTA): "Skip for now — I'll set this up later" → enters main app with a default client named after the user's email prefix.
- On submit with URL: navigates to Step 2 with ingestion running.
- On submit without URL: navigates to Step 2 with voice questionnaire shown (not ingestion).

### Step 2: Your Brand Voice

- Surface: Same centered layout. Progress indicator: "2 of 3".
- If ingestion ran (URL provided): shows "Analyzing [url]..." typewriter then auto-reveals the extracted Brand Voice Profile fields for review. User edits any field, then "Confirm my voice profile."
- If no URL: shows the voice questionnaire (see Component Patterns). On submit, shows "Extracting your voice profile..." typewriter then confirms.
- Skip link: "Skip — I'll refine this later" → proceeds to Step 3 with an incomplete profile flagged.

### Step 3: Your First Brain Dump

- Surface: Full-width Brain Dump input. Progress indicator: "3 of 3."
- H2 (Playfair): "What's on your mind this week?"
- Subtext: "Paste anything — bullet points, half-formed thoughts, a topic title. PersonnaPress will do the rest."
- Brain Dump textarea (full width, min 200px height).
- Primary CTA: "Generate my first campaign"
- Skip link: "I'll write my first draft later" → enters Dashboard with a "Complete your first campaign" nudge card.

## Key Flows

### Flow 1 — Sarah onboards and publishes her first blog post

_Sarah is a SaaS founder who wants to publish weekly. She just signed up via Google OAuth. No existing content. First login._

1. Sarah lands on Onboarding Step 1. She types her company name "TechFounder" and pastes her website URL.
2. She hits "Create client and analyze voice." Step 2 loads with typewriter: "Scraping techfounder.io... Analyzing 8 blog posts... Extracting voice profile..."
3. Voice profile appears. Three tone descriptors read: "authoritative, conversational, direct." One jargon entry: "synergy." She deletes it and replaces with "leverage" (also dislikes). Clicks "Confirm my voice profile."
4. Step 3 loads. Sarah types three bullet points about a recent product update. Clicks "Generate my first campaign."
5. Typewriter fills the screen. "Drafting your blog post... Checking voice fidelity... Generating featured image..." — 65 seconds.
6. **Climax:** Approval Gate loads. Blog preview fills the left panel — 1,150 words in her voice. Featured image: abstract blue. Right panel: her X teaser (274 chars) and LinkedIn post (820 chars). Voice score badge shows "VOICE MATCH: 8/10." She reads the first three paragraphs, edits one sentence in the WYSIWYG. She clicks "Approve."
7. Schedule picker appears. She clicks "Publish now." Platform Connections panel appears (she has none yet): "Connect a platform to publish." She clicks "Connect WordPress," enters her site URL and Application Password. System validates: "Connected — techfounder.io."
8. She clicks "Publish now." Publishing progress: "Publishing to WordPress..." → "Done. Published to WordPress." She sees the live URL: "View on WordPress →".
9. **Resolution:** Approval Gate footer shows "Published — June 14, 2026, 4:07 PM." Dashboard loads with her first Campaign row: "Published" status, green badge. Brain Dump input is ready and waiting.

Failure at generation: Gemini returns an error after 3 retries → Campaign status set to `failed`. Dashboard shows error row. "Retry generation" link retries from the same Brain Dump.

Failure at publish (WordPress 401): Retry panel appears in Approval Gate. "WordPress returned 401 — check your Application Password." She re-enters the password. Retry succeeds.

---

### Flow 2 — Marcus runs his weekly content routine

_Marcus is a business coach. Brand Voice Profile confirmed, WordPress and LinkedIn connected. Returning user, Tuesday morning._

1. Marcus logs in. Dashboard shows three previous Campaigns: all "Published." Client switcher shows "Marcus Coaching" active.
2. He clicks "New Campaign." Brain Dump page loads. He types four sentences about a coaching framework he developed. 180 characters. Counter reads "180 / 10,000." He clicks "Generate campaign."
3. Typewriter. 58 seconds. Approval Gate loads. Voice score: 9/10 (no badge — above threshold).
4. He reads the blog on the left panel. Everything sounds right. He doesn't edit. He clicks "Approve."
5. Schedule picker: he selects Thursday, 8:00 AM. "Schedules in America/New_York." Clicks "Schedule."
6. **Climax:** Approval Gate footer shows "Scheduled — Thursday, June 18, 2026, 8:00 AM." Dashboard updates: Campaign row shows "Approved" status badge and "Scheduled for Jun 18, 8:00 AM." Marcus closes the tab. Thursday morning his phone shows LinkedIn engagement on a post he finished in 6 minutes on Tuesday.

Failure at scheduled publish: APScheduler fires at 8:00 AM. LinkedIn returns a token expiration error. Campaign status set to `failed`. In-app notification (next login): "Scheduled publish failed — Thursday post to LinkedIn. Reconnect LinkedIn and retry." Retry panel in Approval Gate.

---

### Flow 3 — Jenna manages three agency clients

_Jenna runs a marketing agency. Three clients: "TechFounder," "WellnessHub," "AutoShop Pro." All brand profiles confirmed, all platforms connected._

1. Jenna logs in. Dashboard shows "TechFounder" active (her last used client). Campaign list shows 4 Published campaigns this month.
2. She clicks the client switcher in the sidebar header. Dropdown shows all three clients. She selects "WellnessHub."
3. Dashboard reloads with WellnessHub context. Campaign list is empty for this week. She clicks "New Campaign."
4. Brain Dump: she pastes notes from her client call about a seasonal wellness topic.
5. Generation runs. Approval Gate loads. Voice score: 7/10 — above threshold, no warning.
6. She reads and approves. Publishes immediately to WellnessHub's WordPress and LinkedIn.
7. **Climax:** Three clients' weekly content done. She switches to "AutoShop Pro" and repeats. Calendar surface now shows all three clients' published posts on today's date — three platform icon clusters on June 14. Jenna sees the full week at a glance.

Edge case — client limit reached: Jenna tries to add a fourth client. Form submission returns: "You've reached your 3-client limit on the Growth plan. Upgrade to Agency for up to 20 clients." Upgrade CTA opens Stripe Customer Portal.

---

## Monetization UX

Trial state is communicated without anxiety until Day 10. After Day 10, in-app nudges are proportional: a toast notification (not a modal takeover). Only on expiry does the banner become non-dismissible and CTAs become gated.

Upgrade prompts are triggered at the moment of limit contact — not preemptively. A user who has never hit their Campaign limit never sees a "you're close to your limit" message. The friction appears exactly when and only when it's relevant.

The Stripe Customer Portal handles all subscription management. PersonnaPress does not build its own billing UI. Account surface contains: current plan name, current period usage (Campaigns used / limit, Clients, Images), renewal date, and a "Manage subscription" link that opens the Stripe portal.
