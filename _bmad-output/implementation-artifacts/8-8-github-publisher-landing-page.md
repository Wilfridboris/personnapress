---
baseline_commit: 5e298dffd0633af23ec4808946930d6d600375c1
---

# Story 8.8: GitHub Publisher Landing Page
<!-- epics.md reference: Epic 8, Story 8.7 (GitHub Blog Publishing Phase 2) -->

Status: done

## Story

As a developer who hosts their blog on GitHub Pages,
I want to find a dedicated page that clearly explains how PersonnaPress publishes to my specific setup,
so that I can quickly understand if it supports my framework and sign up without friction.

## Acceptance Criteria

1. Page at `/github-publisher` renders as a Next.js App Router SSG page with `export const dynamic = 'force-static'`; a minimal top navigation bar shows the PersonnaPress wordmark in Playfair Display (Ink) on a Paper background, a "Sign in" text link (Inter, Graphite), and a "Start free" compact Primary button; no app shell sidebar present.
2. Hero section: full-bleed Ink (#111111) background; Playfair Display 700 White headline `text-5xl lg:text-7xl text-balance`; Inter 18px White/70 subheadline; single Primary button with inverted styling (White fill, Ink text, 4px 4px 0px White hard shadow, rounded-none) linking to `/register`; JetBrains Mono 13px White/50 framework list below the button.
3. "Terminal demo" section: Paper background; simulated terminal window (Ink background card, rounded-none, 1px Border); on scroll into viewport (Intersection Observer), a CSS `@keyframes` character-reveal animation types the demo text in JetBrains Mono 13px White; `✓` characters in Success green (#2E4F2E); `prefers-reduced-motion` shows completed terminal state immediately with no animation.
4. "Framework support" section: Paper background; Playfair H2 "Works with your setup"; 8-card grid (4 columns desktop, 2 columns mobile); Default Card style (White fill, 1px Border, rounded-none, hover adds 4px 4px 0px Ink hard shadow); framework name (Inter 500 15px Ink), detection signals (JetBrains Mono 12px Graphite), publish path (JetBrains Mono 12px Ink bold).
5. "How it compares" section: Playfair H2 "Not a CMS. A publishing layer."; HTML `<table>` with Ink 1px solid borders throughout (no border-radius); columns: Feature, PersonnaPress, Pages CMS, Decap CMS; rows: AI content generation (✓/✗/✗), Auto framework detection (✓/✗/✗), PR-first publish (✓/✓/✓), Voice-matched writing (✓/✗/✗), No config file required (✓/✗/✗); ✓ in Success (#2E4F2E), ✗ in Danger (#8B0000); header row Ink background, White Inter 11px uppercase tracked labels.
6. CTA section: full-bleed Highlighter (#FFF1B8) background; Playfair H2; Inter 16px Graphite body; Primary button "Start free — no credit card" linking to `/register`; Inter 13px Graphite supporting text.
7. SEO/GEO: `generateMetadata` exports `title` "AI Blog Writer for GitHub Pages — PersonnaPress", `description` (150-160 chars, keyword-first), `openGraph` with `og:title`, `og:description`, `og:image`; `alternates.canonical` = `https://personnapress.com/github-publisher`; JSON-LD `SoftwareApplication` schema with `operatingSystem: "Web"`, `applicationCategory: "DeveloperApplication"`, and `offers` block matching the three pricing tiers ($29/$79/$199/mo).
8. All images have descriptive `alt` text; page is fully keyboard-navigable; all `<section>` elements have `aria-label`; comparison table has `<caption>` and `<th scope>` attributes.

## Tasks / Subtasks

- [x] **Page scaffold — SSG route** (AC: 1, 7)
  - [x] Create `frontend/app/github-publisher/page.tsx` (outside `(auth)/` and `(app)/` route groups — public, no middleware protection)
  - [x] Add `export const dynamic = 'force-static'` at the top of the file
  - [x] Implement `export async function generateMetadata(): Promise<Metadata>` (no dynamic params needed — static page):
    ```typescript
    export async function generateMetadata(): Promise<Metadata> {
      return {
        title: "AI Blog Writer for GitHub Pages — PersonnaPress",
        description:
          "Publish AI-written blog posts to your Jekyll, Astro, Hugo, Next.js, or Eleventy repo. PersonnaPress detects your framework and commits the post in the right format — no config required.",
        openGraph: {
          title: "AI Blog Writer for GitHub Pages — PersonnaPress",
          description:
            "Publish AI-written blog posts to your Jekyll, Astro, Hugo, Next.js, or Eleventy repo. PersonnaPress detects your framework and commits the post in the right format — no config required.",
          type: "website",
          images: [
            {
              url: "/og-github-publisher.png",
              width: 1200,
              height: 630,
              alt: "PersonnaPress GitHub Publisher — AI blog writing for Jekyll, Astro, Hugo, and more",
            },
          ],
        },
        alternates: {
          canonical: "https://personnapress.com/github-publisher",
        },
        twitter: {
          card: "summary_large_image",
          title: "AI Blog Writer for GitHub Pages — PersonnaPress",
          description:
            "PersonnaPress detects your GitHub Pages framework and commits AI-written posts in the right format. Jekyll, Astro, Hugo, Next.js, Eleventy — no config required.",
        },
      };
    }
    ```

- [x] **JSON-LD schema** (AC: 7)
  - [x] In the page Server Component, define the `SoftwareApplication` JSON-LD and inject as `<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />`
  - [ ] Schema shape:
    ```typescript
    const jsonLd = {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: "PersonnaPress",
      description:
        "AI-powered blog writing and GitHub Pages publishing tool. Detects your static site framework and commits posts in the correct format via Pull Request or direct commit.",
      applicationCategory: "DeveloperApplication",
      operatingSystem: "Web",
      url: "https://personnapress.com",
      offers: [
        {
          "@type": "Offer",
          name: "Starter",
          price: "29",
          priceCurrency: "USD",
          priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
        },
        {
          "@type": "Offer",
          name: "Growth",
          price: "79",
          priceCurrency: "USD",
          priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
        },
        {
          "@type": "Offer",
          name: "Agency",
          price: "199",
          priceCurrency: "USD",
          priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
        },
      ],
      featureList: [
        "AI blog content generation",
        "GitHub Pages framework auto-detection",
        "Jekyll, Astro, Next.js, Hugo, Eleventy support",
        "PR-first publishing workflow",
        "Voice-matched writing",
      ],
    };
    ```
  - [x] Place the `<script>` tag as the first child of the page's root element (before visible content) for fastest AI crawler parsing

- [x] **Minimal top navigation** (AC: 1)
  - [x] `<nav aria-label="Site navigation">` with Paper background (#F9F9F6), 1px bottom Border (#E5E5E5)
  - [x] Wordmark: `<a href="/">PersonnaPress</a>` in `font-serif font-bold text-xl text-[#111111]` (Playfair Display via global CSS)
  - [x] "Sign in": `<a href="/login">Sign in</a>` in `text-sm text-[#555555] hover:text-[#111111]`
  - [x] "Start free": `<a href="/register">Start free</a>` using Primary button style compact — `bg-[#111111] text-white text-sm px-4 py-2 shadow-[2px_2px_0px_#111111] hover:bg-white hover:text-[#111111] hover:border hover:border-[#111111] rounded-none`
  - [x] No sidebar; no `AppShell.tsx` — this page has its own minimal layout

- [x] **Hero section** (AC: 2)
  - [x] `<section aria-label="Hero" className="bg-[#111111] px-6 py-24 lg:py-32 text-center">`
  - [x] H1: `<h1 className="font-serif font-bold text-5xl lg:text-7xl text-white text-balance leading-[1.15] tracking-[-0.01em] mb-6">Publish your AI-written blog to GitHub. In the right format, to the right file, every time.</h1>`
  - [x] Subheadline: `<p className="text-[18px] text-white/70 font-sans max-w-[600px] mx-auto mb-8 leading-[1.6]">PersonnaPress detects your Jekyll, Astro, Hugo, or Next.js setup and commits the post where it belongs, no config, no copy-paste.</p>`
  - [x] CTA button: inverted Primary button (White fill, Ink text, white hard shadow) linking to /register
  - [x] Framework list: `<p className="font-mono text-[13px] text-white/50 mt-6">Jekyll · Astro · Next.js · Hugo · Eleventy · Docusaurus · MkDocs</p>`

- [x] **Terminal demo section** (AC: 3)
  - [x] Create `frontend/components/marketing/TerminalDemo.tsx` as a Client Component (`"use client"`) — the only client component on this page (Intersection Observer requires browser API)
  - [x] Uses `useRef` + `useEffect` to set up `IntersectionObserver` on the terminal container; on intersection, adds a CSS class that triggers the `@keyframes` character-reveal animation
  - [x] `prefers-reduced-motion`: in the `useEffect`, check `window.matchMedia('(prefers-reduced-motion: reduce)').matches`; if true, add the "complete" class immediately (shows finished terminal text, no animation)
  - [x] Terminal window structure:
    ```tsx
    <div className="bg-[#111111] border border-[#E5E5E5] rounded-none max-w-[640px] mx-auto">
      {/* Traffic lights — decorative, aria-hidden */}
      <div className="flex gap-2 px-4 py-3 border-b border-[#E5E5E5]" aria-hidden="true">
        <span className="w-[10px] h-[10px] rounded-full bg-[#8B0000]" />
        <span className="w-[10px] h-[10px] rounded-full bg-[#FFF1B8]" />
        <span className="w-[10px] h-[10px] rounded-full bg-[#2E4F2E]" />
      </div>
      {/* Content area */}
      <pre className="font-mono text-[13px] text-white p-6 leading-[1.7]">
        {/* Animated text — see animation notes */}
      </pre>
    </div>
    ```
  - [x] `✓` characters rendered in `text-success` (Success green)
  - [x] Section wrapper: `<section aria-label="Terminal demo" className="bg-paper px-6 py-20">`
  - [x] Section heading above terminal: `<h2 className="font-display font-bold text-3xl text-ink text-center mb-10">See it work</h2>`

- [x] **CSS animation for terminal** (AC: 3)
  - [x] React state-driven character reveal approach used: `setInterval`-style via `setTimeout` chaining, 18ms per character
  - [x] `prefers-reduced-motion` check shows complete text via `setTimeout(..., 0)` — avoids synchronous setState in effect

- [x] **Framework support section** (AC: 4)
  - [x] `<section aria-label="Supported frameworks" className="bg-paper px-6 py-20">`
  - [x] Playfair H2 centered: "Works with your setup"
  - [x] BLUF paragraph for featured snippet targeting
  - [x] Grid: `grid-cols-2 lg:grid-cols-4 gap-4`
  - [x] Each card: `<article>` with White fill, border-border, rounded-none, hover:shadow-brutal
  - [x] Framework name, signals, publish path rendered for all 8 frameworks

- [x] **Comparison table section** (AC: 5)
  - [x] `<section aria-label="Comparison with alternatives">`
  - [x] Playfair H2: "Not a CMS. A publishing layer."
  - [x] Semantic `<table>` with `border-collapse` and Ink borders throughout
  - [x] `<caption className="sr-only">` present
  - [x] `<th scope="col">` for each column header, `<th scope="row">` for feature names
  - [x] Check rendered as `&#10003;` in `text-success` with `aria-label="Yes"`
  - [x] Cross rendered as `&#10007;` in `text-danger` with `aria-label="No"`
  - [x] Table container with `overflow-x-auto` for mobile scroll

- [x] **CTA section** (AC: 6)
  - [x] `<section aria-label="Call to action" className="bg-highlighter px-6 py-24 text-center">`
  - [x] Playfair H2 Ink: "Your next post is one Brain Dump away."
  - [x] Inter 16px Graphite body copy
  - [x] Primary button "Start free, no credit card" linking to /register
  - [x] Supporting text Inter 13px Graphite: "14-day free trial · Supports 8 frameworks · PR-first by default."

- [x] **Sitemap and robots updates** (AC: 7)
  - [x] `frontend/app/sitemap.ts`: Added `/github-publisher` entry with `priority: 0.8`, `changeFrequency: 'monthly'`
  - [x] `frontend/app/robots.ts`: Verified GPTBot and PerplexityBot already allowed — no changes needed

- [x] **OG image** (AC: 7)
  - [x] Created `frontend/app/github-publisher/opengraph-image.tsx` using Next.js `ImageResponse` (static PNG not feasible in dev environment)

- [x] **Accessibility** (AC: 8)
  - [x] All `<section>` elements have `aria-label`
  - [x] Comparison table has `<caption>`, `<th scope="col">`, `<th scope="row">`
  - [x] Check/cross cells have `aria-label="Yes"` / `aria-label="No"`
  - [x] Terminal traffic lights: `aria-hidden="true"`
  - [x] Navigation links have `focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2`

## Dev Notes

### Route Placement — Outside Route Groups

The page must be at `frontend/app/github-publisher/page.tsx` — NOT inside `(app)/` (protected) or `(auth)/` (login pages). The middleware.ts only protects `(app)/` routes, so a file directly under `frontend/app/` is public by default.

Verify `middleware.ts` matcher config does not accidentally catch `/github-publisher`. Current pattern protects routes like `/(app)/*` — the parenthetical route group convention means `github-publisher` (no parens) is not caught.

### Do NOT Fetch Data in This Server Component

Per project-context.md: never put API calls in server components. This page is fully static — all content is hard-coded in the component. `export const dynamic = 'force-static'` makes this explicit. No backend calls needed.

### Font Loading

Playfair Display, Inter, and JetBrains Mono are already loaded via `next/font` in `frontend/app/layout.tsx` and applied as CSS custom properties / Tailwind classes. Do NOT import fonts again in this page — they are inherited from the root layout. Use the existing Tailwind classes: `font-serif` (Playfair), `font-sans` (Inter), `font-mono` (JetBrains Mono).

### Terminal Animation — React State Approach (Preferred)

```tsx
"use client";
import { useRef, useState, useEffect } from "react";

const TERMINAL_TEXT = `$ personnapress detect wilfridboris/my-blog
Scanning repository...
  ✓ Found _config.yml
  ✓ Found _posts/ (14 posts)
  ✓ Detected: Jekyll

Target file: _posts/2026-07-09-how-i-built-this.md
Front matter: title, date, categories, description

Ready to publish via Pull Request.`;

export function TerminalDemo() {
  const ref = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      setVisibleCount(TERMINAL_TEXT.length); // show all immediately
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting && !started) setStarted(true); },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [started]);

  useEffect(() => {
    if (!started || visibleCount >= TERMINAL_TEXT.length) return;
    const id = setTimeout(() => setVisibleCount((n) => n + 1), 18);
    return () => clearTimeout(id);
  }, [started, visibleCount]);

  const visible = TERMINAL_TEXT.slice(0, visibleCount);
  // Render ✓ in Success green
  // Split visible text on ✓ and wrap spans
  ...
}
```

### SEO Structure Priority

The comparison table and framework support grid are the highest-value content for AI crawlers and featured snippets. Structure rules:
1. Use `<table>` for the comparison (not a CSS grid) — Google and AI answer engines extract table data for comparison queries
2. The BLUF paragraph in the framework support section is the featured snippet target for "what frameworks does PersonnaPress support"
3. The JSON-LD `featureList` array reinforces the comparison table claims for AI models

### Meta Description Length Check

The description must be 150-160 characters:
"Publish AI-written blog posts to your Jekyll, Astro, Hugo, Next.js, or Eleventy repo. PersonnaPress detects your framework and commits the post in the right format — no config required."
→ Count: 185 chars — TRIM to: "Publish AI-written blog posts to Jekyll, Astro, Hugo, or Eleventy repos. PersonnaPress detects your framework and commits posts correctly — no config needed." → 157 chars ✓

### Checklist Against nextjs-seo-aeo Skill

- [x] `generateMetadata` returns `title`, `description`, `openGraph`, `alternates.canonical`
- [x] JSON-LD `SoftwareApplication` schema injected via `dangerouslySetInnerHTML`
- [x] Semantic HTML: `<nav>`, `<section aria-label>`, `<article>` for cards, `<table>` for comparison
- [x] BLUF paragraph in framework support section (direct answer for featured snippets)
- [x] `<table>` used for comparison data (not CSS grid)
- [x] `next/font` inherited from root layout (no re-import)
- [x] Sitemap updated with `/github-publisher`
- [x] `robots.ts` GPTBot/PerplexityBot allow verified
- [x] OG image static file provided

### Project Structure Notes

**New files:**
- `frontend/app/github-publisher/page.tsx`
- `frontend/components/marketing/TerminalDemo.tsx`
- `frontend/public/og-github-publisher.png` (static asset — design/create separately)

**Modified files:**
- `frontend/app/sitemap.ts` — add `/github-publisher` entry
- `frontend/app/robots.ts` — verify GPTBot allowed (create if missing)

**No backend changes.** This page has no server-side data dependencies.

### References

- Epics.md: Epic 8, Story 8.7 — pixel-exact design spec for all sections
- nextjs-seo-aeo skill: SEO/GEO checklist, JSON-LD patterns, semantic HTML requirements
- Architecture: `frontend/app/layout.tsx` — root layout font loading (do not re-import fonts)
- Architecture: `frontend/app/api/webhooks/stripe/route.ts` — how Next.js API routes are structured (for robots.ts reference)
- project-context.md: Never put API calls in server components — this page is fully static, so no API calls needed
- UX-DR2: Typography tokens (Playfair = `font-serif`, Inter = `font-sans`, JetBrains Mono = `font-mono`)
- UX-DR3: Button variants (Primary + inverted Primary for dark hero background)
- UX-DR5: Default Card spec (white fill, 1px Border #E5E5E5, hover shadow)
- PRD §8: Pricing tiers ($29 Starter, $79 Growth, $199 Agency) — used in JSON-LD offers block

## Review Findings

- [x] [Review][Patch] `window.matchMedia` called without existence guard [frontend/components/marketing/TerminalDemo.tsx:34]
- [x] [Review][Patch] IntersectionObserver stale closure + not disconnected after trigger [frontend/components/marketing/TerminalDemo.tsx:41-48]
- [x] [Review][Patch] OG image uses `runtime = "edge"` with no font loading [frontend/app/github-publisher/opengraph-image.tsx:3]
- [x] [Review][Patch] Hero CTA button white shadow invisible on dark hover state [frontend/app/github-publisher/page.tsx]
- [x] [Review][Patch] OG image `alt` is marketing tagline, not image description [frontend/app/github-publisher/opengraph-image.tsx:4]
- [x] [Review][Defer] Pricing in JSON-LD hardcoded — will silently go stale on pricing changes; acceptable for MVP [frontend/app/github-publisher/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] Comparison table competitor data unsubstantiated — no audit mechanism; acceptable for MVP content [frontend/app/github-publisher/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] `lastModified: new Date()` at build time stamps all URLs as freshly modified on every deploy [frontend/app/sitemap.ts] — deferred, pre-existing
- [x] [Review][Defer] `style={{ borderRadius: 0 }}` repeated inline on 6+ elements instead of shared Tailwind class [frontend/app/github-publisher/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] "See it work" terminal heading is content-free — low SEO/accessibility value [frontend/components/marketing/TerminalDemo.tsx:64] — deferred, pre-existing
- [x] [Review][Defer] Two consecutive `bg-paper` sections render as one continuous block with no visual separator [frontend/app/github-publisher/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] `dangerouslySetInnerHTML` + `JSON.stringify(jsonLd)` lacks `</script>`-sequence escaping [frontend/app/github-publisher/page.tsx] — deferred, currently static
- [x] [Review][Defer] Terminal animation has no "skip" affordance for users who scroll past before animation completes [frontend/components/marketing/TerminalDemo.tsx] — deferred, out of spec scope
- [x] [Review][Defer] `renderWithCheckmarks` splits on literal ✓ codepoint — brittle if copy-pasted from different editor [frontend/components/marketing/TerminalDemo.tsx:17] — deferred, currently correct

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Implemented fully static SSG landing page at `/github-publisher` with `force-static` export
- Used `font-display` (Playfair Display) consistent with rest of codebase — not `font-serif` which maps to system serif
- All em-dashes replaced with commas per project constraint (no em-dashes anywhere in app)
- TerminalDemo uses React state-driven character reveal via chained `setTimeout` at 18ms/char; `prefers-reduced-motion` shows complete text via `setTimeout(..., 0)` to avoid synchronous setState-in-effect ESLint violation
- All internal navigation uses `<Link>` from `next/link` (ESLint `@next/next/no-html-link-for-pages` compliance)
- `opengraph-image.tsx` generates OG image via Next.js ImageResponse at build time; `generateMetadata` does not duplicate images to avoid URL conflict
- `robots.ts` already had GPTBot/PerplexityBot allowed; no change needed
- Pre-existing TypeScript error in `ClientDetail.tsx` and pre-existing Jest/Vitest config mismatch are unrelated to this story

### File List

- frontend/app/github-publisher/page.tsx (new)
- frontend/app/github-publisher/opengraph-image.tsx (new)
- frontend/components/marketing/TerminalDemo.tsx (new)
- frontend/app/sitemap.ts (modified — added /github-publisher entry)
