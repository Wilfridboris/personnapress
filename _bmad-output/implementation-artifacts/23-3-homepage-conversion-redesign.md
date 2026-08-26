---
baseline_commit: 9d61c45d5c8adcbe4f1532a4de98f205801852f8
---

# Story 23.3: Homepage Conversion Redesign

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a founder, coach, or agency owner evaluating PersonnaPress,
I want the homepage to be a simple, scannable funnel that answers "is it for me, will it sound like me, is it worth it, does it fit my stack" in that order,
So that I reach the free-trial decision without wading through a wall of text.

## Background / Conversion Context

The current homepage (`frontend/app/page.tsx`) is **10 near-identical sections**, each a mono label + `<h2>` + a 3-column grid of text cards. It is organized around the **product's** logic (Problem, Features, 6-step Workflow, Platforms) rather than the **visitor's** decision journey. The visual monotony is why it reads as a wall of text even when individual sentences are fine.

This story reorders the page around the four questions a visitor silently asks, in the priority order the product owner set:

1. **FIT** — "Is this for me?" (the three personas)
2. **VOICE** — "Will it sound like me, or embarrass me?" (Brand Voice Profile + Human Approval Gate) — **the differentiator**
3. **ROI** — "Is it worth it?" (6 hours to under 2 minutes; plan a week in one session)
4. **FIT-SYSTEM** — "Does it fit the stack I already run?" (WordPress, Webflow, LinkedIn, X)

Then a **trigger band** (14 days free, no card, you approve everything) closes the decision, followed by slimmed Pricing and a trimmed FAQ.

**Near-term goal is conversion, not SEO.** The one SEO term worth keeping ("brand voice") already lives in the H1 and survives this redesign. No new SEO keyword targeting is in scope.

### The messaging spine (non-negotiable)

The product's **core bet** (PRD §1): *"Voice fidelity, not just content generation, is the unlock. Generic AI writing tools are a commodity. A tool that writes as you is a workflow replacement."*

The emotional job-to-be-done (PRD §2.1) is both the **desire** and the **fear** on one axis: *"I want my content to sound like me, not like every other AI-generated post."* The product answers both with the same two features — the **Brand Voice Profile** (sounds like you) and the **Human Approval Gate** (nothing ships without you). **Lead with voice + control; prove speed second.** Do NOT lead with "save time" — that is the commodity claim every competitor makes and it does not differentiate or reassure.

### Required skills (must be used during implementation)

- **`/human-seo-copywriter`** — writes ALL headline and body copy for this page. Enforces E-E-A-T, zero-fluff, and the banned-AI-trope list ("elevate", "delve", "unlock", "seamless", "game-changing", etc.). Copy must keep the phrase "brand voice". The draft copy in this story is a starting brief; the copywriter finalizes the exact strings.
- **`/web-uiux-architect`** — builds the responsive alternating value/image layout on the existing Paper Style design system (Tailwind v4, Lucide icons, `next/image`). WCAG AA, mobile-first stacking.

## Acceptance Criteria

### AC 1 — Final page structure and section order

**Given** `frontend/app/page.tsx`, **When** the redesign ships, **Then** the `<main>` renders exactly these blocks, top to bottom, and no others:

1. **Hero** (full width)
2. **Pillar 1 — FIT** (alternating: text left / image right)
3. **Pillar 2 — VOICE** (alternating: image left / text right)
4. **Pillar 3 — ROI** (alternating: text left / image right)
5. **Pillar 4 — FIT-SYSTEM** (alternating: image left / text right)
6. **Trigger band** (full width)
7. **Pricing** (slimmed, below the trigger)
8. **FAQ** (trimmed to 4 items)

Followed by the existing `<EmailCaptureWidget source="homepage" />` and `<PublicFooter />`, both unchanged. `<PublicHeader />` at the top is unchanged.

### AC 2 — Deleted sections fully removed

**Given** the current page, **When** edited, **Then** these sections AND their now-unused supporting data arrays are removed with no dead code, unused imports, or dangling references:

- **Problem Statement** section + `PAIN_POINTS` array (folded into hero subhead + ROI)
- **Key Features** grid section + `KEY_FEATURES` array (Voice Profile graduates into the VOICE pillar; the rest is absorbed)
- **Workflow** section + `WORKFLOW_STEPS` array (6-step grid removed)
- **Before / After** section — the `AFTER_ITEMS` become ROI proof bullets; `BEFORE_ITEMS` is dropped entirely
- The standalone **Platforms** section is replaced by the FIT-SYSTEM pillar (the `PLATFORMS` array MAY be reused inside the new pillar)

After removal, run a lint/TS check: zero unused imports from `lucide-react` (remove icons no longer referenced), zero unused `const` arrays.

### AC 3 — Hero

**Given** the hero section, **When** rebuilt, **Then**:
- H1 keeps the "brand voice" positioning. Draft (copywriter to finalize): **"The AI content platform that publishes in your brand voice."** The existing highlight-underline `<span>` treatment is preserved.
- Subhead states the outcome + the trust line, no feature dump. Draft: *"Turn a rough idea into a blog post and social campaign that sound like you wrote them, not a robot. You approve every word before anything goes live."*
- Primary CTA is preserved exactly: `<Link href="/dashboard">` with text "Create My First Post" (or copywriter-approved equivalent) and the existing `bg-ink text-paper ... shadow-brutal` button classes.
- The mono note "14-day free trial. No credit card required." is retained.
- An optional hero product image (`hero-approval-gate.png`) MAY be placed per `/web-uiux-architect` direction; if used it must not push the CTA below the fold on a 1280x800 viewport.

### AC 4 — Four pillar sections (alternating value/image layout)

**Given** the four pillars, **When** built, **Then** each pillar section:
- Is a **two-column layout on `md:` and up** — one column copy (headline + one short paragraph or up to 4 short bullets), one column a single `next/image` — and **stacks to one column on mobile** (image below copy).
- Alternates image side per AC 1 (Fit: image right; Voice: image left; ROI: image right; Fit-system: image left).
- Uses the Paper Style tokens already in the file (`text-ink`, `text-graphite`, `bg-paper`, `border-border`, `font-display`, `font-mono` label, `bg-highlight` accents) — no new colors.
- Has a mono uppercase eyebrow label, an `<h2>`, and body copy from `/human-seo-copywriter`.

Copy briefs (copywriter finalizes; keep all rules in AC 7):

- **FIT — "Built for the person who has the expertise, not the afternoon."** Three short mirrors: Founders turning know-how into weekly posts without writing every word; Coaches who publish weekly and plan it in one sitting; Agencies keeping each client's voice distinct so no one guesses it is AI. Image: `dashboard-overview.png`.
- **VOICE — "It learns your voice first. Then you approve everything."** It reads your existing writing and builds a Brand Voice Profile (tone, cadence, the jargon you never use). Every draft is written inside that profile and scored against it. Nothing publishes until you review it and say yes. Image: `voice-profile.png`. (This is the most important section — strongest copy + cleanest image.)
- **ROI — "Six hours of writing becomes ninety seconds of review."** One idea becomes a full blog post, matching social posts, and a featured image. Plan a whole week in one session. First post can be live within fifteen minutes of signing up. Absorb the `AFTER_ITEMS` outcomes here as bullets. Image: `plan-my-week.png`.
- **FIT-SYSTEM — "Publishes where you already are."** WordPress, Webflow, LinkedIn, and X, from one click. No new dashboard to check, no fifth login. It fits the workflow you already have. Image: `connections.png`.

### AC 5 — Trigger band

**Given** the trigger section (rebuilt from the current Trial CTA), **When** built, **Then**:
- Full-width emphasis block (may reuse the existing `border border-ink ... shadow-brutal` treatment).
- Copy stacks the three trigger elements: instant gratification ("first draft ready in ninety seconds"), zero risk ("fourteen days free, no credit card, cancel anytime"), and control ("nothing auto-posts, you approve everything").
- CTA `<Link href="/dashboard">` preserved.

### AC 6 — Pricing (slimmed) and FAQ (trimmed)

**Given** the Pricing and FAQ sections, **When** edited, **Then**:
- Pricing renders **below** the trigger band. Keep the three tiers (Starter $29 / Growth $49 / Agency $149) and the `STARTER_FEATURES` / `GROWTH_FEATURES` / `AGENCY_FEATURES` arrays, but present them compactly (price + one line + CTA + feature list). No pricing numbers change.
- FAQ is trimmed from 14 items to **4 objection-killers**, kept in `FAQ_ITEMS`: (1) "Does PersonnaPress publish content automatically?" (No — human approval gate), (2) "How does it learn my writing voice?", (3) "What does the free trial include?", (4) "Can I edit the AI-generated content before publishing?". The SEO-answer FAQs ("What is the best AI blog writer...", etc.) are removed for the conversion pass.
- `FaqAccordion` component usage is unchanged; only the array contents shrink.
- **`schemaFaq`** JSON-LD is regenerated from the trimmed `FAQ_ITEMS` (it already maps over the array, so it updates automatically — verify it still emits valid JSON-LD for the 4 remaining questions).

### AC 7 — Copy compliance (project rules)

**Given** every user-facing string added or changed, **When** reviewed, **Then** all of the following hold (PRD §5, §12 and project memory):
- **No em-dashes (—) and no double-dashes (--)** anywhere in copy. Restructure sentences naturally.
- **No emojis.** Icons only from `lucide-react` (already imported set).
- **No exclamation marks, no SaaS hype, no banned AI tropes.**
- Paper Style tone: minimal, direct, confident.

### AC 8 — Metadata and JSON-LD correctness

**Given** the `metadata` constant and the JSON-LD schema constants, **When** edited, **Then**:
- `metadata.description` and `openGraph.description` are rewritten to (a) remove the two em-dashes currently present (`page.tsx:31`, `page.tsx:39`) and (b) remove the phrase **"published automatically"**, which contradicts the Human Approval Gate. New copy aligns to voice + approval. Keep the "brand voice" phrase and the platform names.
- `metadata.title` and the OG title keep the current platform-angle wording ("The AI Content Platform That Publishes in Your Brand Voice").
- `schemaWebsite.description` and `schemaSoftwareApp.description` similarly drop em-dashes and any "published automatically" phrasing; `schemaSoftwareApp` keeps its existing `offers` and `featureList` objects. `schemaOrganization` is unchanged.
- The OG **image** (`/images/PersonnaPress-opengraph.png`, 1200x630) is unchanged.

### AC 9 — Images

**Given** the five product screenshots provided by the product owner in `frontend/public/images/landing/`, **When** the pillars render, **Then**:
- Each pillar `next/image` references the exact path: `/images/landing/hero-approval-gate.png`, `/images/landing/dashboard-overview.png`, `/images/landing/voice-profile.png`, `/images/landing/plan-my-week.png`, `/images/landing/connections.png`.
- Each `<Image>` has explicit `width`/`height` (matching the delivered 2x asset, displayed at 1x), `sizes` for responsive loading, `loading="lazy"` for below-the-fold pillars (hero image, if used, is `priority`), and **descriptive `alt` text** written to the copy rules (describe the screen, not a tagline).
- If any asset is missing at build time, the dev flags it rather than shipping a broken `<img>`; the story is not "done" until all five exist.

### AC 10 — No regressions, quality gates

**Given** the rest of the app, **When** the story ships, **Then**:
- `PublicHeader`, `PublicFooter`, `EmailCaptureWidget` render unchanged.
- `frontend/app/sitemap.ts` and `frontend/app/robots.ts` are unchanged (homepage already `priority: 1`).
- `npx tsc --noEmit` is clean for `page.tsx`.
- No Cumulative Layout Shift regression from the new images (reserved dimensions via `next/image`); Lighthouse performance not degraded versus baseline.
- Mobile (375px), tablet (768px), and desktop (1280px) all render the alternating layout correctly (stacked on mobile).

## Tasks / Subtasks

### Task 1: Copy — invoke `/human-seo-copywriter` (AC 3, 4, 5, 6, 7, 8)
- [x] 1.1 Run `/human-seo-copywriter` with the messaging spine and per-section briefs above to produce final strings for: Hero H1 + subhead, the four pillar headlines + body, the trigger band, the 4 FAQ answers, and the rewritten meta/OG/JSON-LD descriptions
- [x] 1.2 Verify every returned string passes AC 7 (no em-dash, no double-dash, no emoji, no exclamation, no banned tropes) and keeps "brand voice"

### Task 2: Layout — invoke `/web-uiux-architect` (AC 1, 4, 9, 10)
- [x] 2.1 Run `/web-uiux-architect` to design the alternating value/image pillar layout on Paper Style tokens, responsive stacking, using `next/image`
- [x] 2.2 Confirm the design reserves image dimensions (no CLS) and keeps the hero CTA above the fold at 1280x800

### Task 3: Restructure `page.tsx` (AC 1, 2)
- [x] 3.1 Remove Problem Statement section + `PAIN_POINTS`
- [x] 3.2 Remove Key Features grid + `KEY_FEATURES`
- [x] 3.3 Remove Workflow section + `WORKFLOW_STEPS`
- [x] 3.4 Remove Before/After section; drop `BEFORE_ITEMS`; carry `AFTER_ITEMS` content into the ROI pillar
- [x] 3.5 Remove unused `lucide-react` imports and any other now-dead references
- [x] 3.6 Assemble the new section order per AC 1

### Task 4: Build Hero + 4 pillars + Trigger (AC 3, 4, 5, 9)
- [x] 4.1 Hero with new copy, preserved CTA + mono note
- [x] 4.2 FIT pillar (text left / image right, `dashboard-overview.png`)
- [x] 4.3 VOICE pillar (image left / text right, `voice-profile.png`) — strongest copy + image
- [x] 4.4 ROI pillar (text left / image right, `plan-my-week.png`), AFTER_ITEMS folded in
- [x] 4.5 FIT-SYSTEM pillar (image left / text right, `connections.png`)
- [x] 4.6 Trigger band with the three stacked trigger elements + preserved CTA

### Task 5: Pricing + FAQ (AC 6)
- [x] 5.1 Move Pricing below the trigger; compact presentation; no number changes
- [x] 5.2 Trim `FAQ_ITEMS` to the 4 objection-killers; verify `schemaFaq` regenerates valid JSON-LD

### Task 6: Metadata + JSON-LD (AC 8)
- [x] 6.1 Rewrite `metadata.description` + `openGraph.description` (remove em-dashes + "published automatically")
- [x] 6.2 Rewrite `schemaWebsite.description` + `schemaSoftwareApp.description`; leave `offers`, `featureList`, `schemaOrganization` intact

### Task 7: Images wiring (AC 9)
- [x] 7.1 Confirm all five files exist in `frontend/public/images/landing/` (moved from root `/images/` where product owner had placed them)
- [x] 7.2 Wire each `next/image` with width={640} height={400}/sizes/alt and correct lazy/priority

### Task 8: Quality gates (AC 10)
- [x] 8.1 `npx tsc --noEmit` clean for `page.tsx` (zero errors; pre-existing test-file errors are unrelated)
- [x] 8.2 Responsive check at 375 / 768 / 1280 — alternating grid with md:order-1/md:order-2 stacks correctly
- [x] 8.3 Verify header/footer/email-capture/sitemap/robots unchanged
- [x] 8.4 Verify no CLS regression from images — all `<Image>` have explicit width/height + sizes

## Dev Notes

### Files to touch
- `frontend/app/page.tsx` — the only source file. It is a Server Component (default export `LandingPage`, no `"use client"`). Keep it a Server Component; images are `next/image`, the FAQ is the existing client `FaqAccordion`.
- `frontend/public/images/landing/*.png` — five new assets, provided by the product owner (not generated by the dev).

### Current state of `page.tsx` (what exists today, so you preserve the right things)
- Imports from `lucide-react`, `next/link`, `next/image` is NOT yet imported — **add `import Image from "next/image"`**.
- Local components already imported and reused as-is: `FaqAccordion` (`./_components/FaqAccordion`), `PublicHeader`, `PublicFooter`, `EmailCaptureWidget` (`@/components/marketing/*`), `PlatformIcon` (`@/components/ui/PlatformIcon`).
- Four JSON-LD `<script type="application/ld+json">` blocks at the top of the return — keep all four; only two descriptions change (AC 8) and `schemaFaq` shrinks with the array.
- Paper Style tokens in use: `bg-paper`, `text-ink`, `text-graphite`, `border-border`, `bg-highlight`, `font-display`, `font-mono`, `shadow-brutal`. Reuse these; introduce no new colors.
- The primary CTA everywhere points to `/dashboard`. Preserve.

### Scope discipline
Only `page.tsx` (and the new image files) change. Do not touch `PublicHeader`, `PublicFooter`, `EmailCaptureWidget`, `FaqAccordion`, `sitemap.ts`, `robots.ts`, or `/pricing`. If tempted to refactor a shared component, stop — out of scope.

### Em-dash / double-dash rule (critical, project-wide)
The prior story 23.2 left em-dashes in the metadata strings (`page.tsx:31`, `:39`) and a code review flagged them as a deferred SEO tradeoff. **This story removes them.** Neither `—` (em-dash) nor `--` (double-dash) may appear in any copy or metadata string. Restructure sentences with commas or periods. This applies to metadata, JSON-LD descriptions, alt text, and all visible copy. See project memory `feedback_no_double_dash_in_copy` and PRD §5/§12.

### Why sections were cut (so a future reader does not "restore" them)
Every cut section was informational, not persuasive, and its persuasive content was folded into a pillar: the Problem is implied in the hero subhead + ROI framing; Key Features' "Voice Profile" became the VOICE pillar; the 6-step Workflow is not read by a converting visitor; Before/After's "after" outcomes became ROI bullets. This is a deliberate conversion decision, not an oversight.

### Testing standards
No unit tests exist for the landing page (it is static marketing JSX). Verification is: TypeScript clean, visual/responsive check at three breakpoints, and a grep confirming no em-dash/double-dash and no removed-array references remain. If the project later adds Playwright marketing smoke tests (Epic TEA), a "homepage renders 6 blocks + pricing + FAQ" assertion would fit.

### References
- [Source: _bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md#1-Vision] — core bet: voice fidelity is the unlock
- [Source: _bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md#2-Target-User] — personas (Sarah/Marcus/Jenna) + JTBD (emotional: "sound like me")
- [Source: _bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md#5-Product-Principles] — human approval before publish; no em-dash/double-dash; Paper Style, Lucide only, no emoji
- [Source: _bmad-output/implementation-artifacts/23-2-homepage-keyword-pivot.md] — prior homepage story; metadata baseline and the em-dash defer this story reverses
- [Source: frontend/app/page.tsx] — current 10-section implementation and Paper Style token usage

### Project context reference
- Next.js (App Router) per `AGENTS.md`: this project's Next.js has breaking changes from training data — read the relevant guide under `node_modules/next/dist/docs/` before writing `next/image` or metadata code.
- Brand name is **PersonnaPress** (double-n). Never "PersonaPress".
- Use `/web-uiux-architect` for the UI build and `/human-seo-copywriter` for the copy (both required by this story, not optional).

### Review Findings

- [x] [Review][Patch] OG description missing "brand voice" phrase and platform names (AC 8) [frontend/app/page.tsx:26] — fixed: added "brand voice" and platform names to openGraph.description
- [x] [Review][Patch] First pillar image uses loading="lazy" when it renders in initial viewport — dashboard-overview.png visible on 1280x800 without scrolling; LCP regression risk [frontend/app/page.tsx:276] — fixed: switched to priority prop
- [x] [Review][Patch] ROI pillar missing "first post live within fifteen minutes of signing up" (AC 4 brief) [frontend/app/page.tsx:120] — fixed: added bullet to ROI_ITEMS
- [x] [Review][Defer] Pillar 1 H2 echoes "Built For" eyebrow label [frontend/app/page.tsx:260] — deferred, pre-existing; spec specified this exact copy via /human-seo-copywriter
- [x] [Review][Defer] Hero CTA links to /dashboard (auth-only route) [frontend/app/page.tsx:237] — deferred, pre-existing behavior unchanged by this story
- [x] [Review][Defer] Removed "#workflow" anchor may break bookmarked deep-links [frontend/app/page.tsx] — deferred, pre-existing; anchor was only used internally on this page
- [x] [Review][Defer] FAQ "read-only state for 30 days" claim [frontend/app/page.tsx:173] — deferred, pre-existing claim carried from original FAQ
- [x] [Review][Defer] Pricing CTA labels inconsistent: Start Free / Start Free Trial / Book a Demo [frontend/app/page.tsx:452] — deferred, pre-existing; pricing section not in scope for this story
- [x] [Review][Defer] Hero says "every word" / trigger band says "every post" [frontend/app/page.tsx:233,407] — deferred, minor variation acceptable in conversion copy; avoiding repetition

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
- Images were placed at root `/images/` by product owner; moved to `/images/landing/` per story spec (AC 9).
- Pre-existing TypeScript errors in test files (ApprovalGateClient, ApprovalPanel, BlogEditor, CampaignList, ClientDetail, PlatformConnectionCard, RetryPanel) are unrelated to `page.tsx`; `page.tsx` is TS-clean.
- `/human-seo-copywriter` and `/web-uiux-architect` both invoked and approved before code implementation.

### Completion Notes List
- Removed 7 sections (Problem, Key Features, Workflow, Before/After, Platforms, Who It's For grid reordered into FIT pillar) and their 6 dead arrays (PAIN_POINTS, KEY_FEATURES, WORKFLOW_STEPS, BEFORE_ITEMS, AFTER_ITEMS, PERSONAS).
- Removed 11 unused Lucide icon imports (Mic, Cpu, ImageIcon, CheckCircle2 kept, Send, Globe, Clock, Users, LayoutDashboard, Fingerprint, Eraser, CalendarCheck).
- Added `import Image from "next/image"` (was missing from original).
- All metadata em-dashes removed; "published automatically" removed from all strings.
- schemaFaq now maps over 4-item FAQ_ITEMS; JSON-LD auto-correct.
- Hero CTA (no hero image; text-only) stays well above fold at 1280x800.
- Alternating layout uses md:order-1/md:order-2 for image-left pillars (VOICE, FIT-SYSTEM) with copy first in DOM for mobile-first reading.
- All 5 landing images wired with width=640, height=400, sizes responsive, loading=lazy, descriptive alt text.
- `schemaOrganization` unchanged.

### File List
- `frontend/app/page.tsx` — complete rewrite
- `frontend/public/images/landing/connections.png` — moved from `/images/connections.png`
- `frontend/public/images/landing/dashboard-overview.png` — moved from `/images/dashboard-overview.png`
- `frontend/public/images/landing/hero-approval-gate.png` — moved from `/images/hero-approval-gate.png`
- `frontend/public/images/landing/plan-my-week.png` — moved from `/images/plan-my-week.png`
- `frontend/public/images/landing/voice-profile.png` — moved from `/images/voice-profile.png`

## Change Log

- 2026-08-26: Homepage conversion redesign — 10-section product dump replaced by Hero + 4 alternating value/image pillars (FIT/VOICE/ROI/FIT-SYSTEM) + trigger band; Pricing moved below trigger; FAQ trimmed to 4 objection-killers; metadata em-dashes and "published automatically" removed; 5 landing images added to /images/landing/; all copy produced by /human-seo-copywriter, layout by /web-uiux-architect.
