---
baseline_commit: a37f7fd5de5860b55e512fc0fe12c8b0c1991482
---

# Story 23.1: Brand Voice Generator Feature Landing Page

Status: done

## Story

As a marketer or content creator searching for a "brand voice generator",
I want to land on a dedicated PersonnaPress feature page at `/brand-voice-generator` that explains what brand voice extraction is and how PersonnaPress automates it,
So that I understand PersonnaPress's core differentiator and convert to a free trial.

## Background / SEO Context

This page targets the keyword cluster anchored by "brand voice generator" (1,000 sv, KD 31) and "brand voice examples" (2,900 sv, KD 2). blaze.ai currently holds #1 for "brand voice generator" but is a social scheduler — PersonnaPress is brand-voice-first and therefore has higher topical authority. This is the single highest-ROI new page build in the keyword opportunity map. The page must use semantic HTML (`<article>`, `<section>`, `<header>`, `<table>`) and FAQPage JSON-LD for AI answer engine citation (ChatGPT, Perplexity, Google AI Overviews).

## Acceptance Criteria

### AC 1 — File location and rendering mode

**Given** the route `/brand-voice-generator`, **When** built, **Then**:
- Page file is at `frontend/app/(public)/brand-voice-generator/page.tsx`
- Declares `export const dynamic = "force-static"` at module scope (same as `frontend/app/(public)/headless-blog-api/page.tsx`)
- Does NOT import or render `PublicHeader` or `PublicFooter` — the `(public)` group layout (`frontend/app/(public)/layout.tsx`) already provides them
- The page is a React Server Component (no `'use client'` directive)

### AC 2 — Metadata

**Given** metadata, **When** `generateMetadata()` runs (async function, not a const — match the pattern in `frontend/app/(public)/headless-blog-api/page.tsx`), **Then**:
- `title: { absolute: "Brand Voice Generator | PersonnaPress - Extract Your Voice, Keep It Everywhere" }`
- `description`: `"PersonnaPress extracts your brand voice from existing content and applies it to every blog post and social update — automatically. No manual style guide required."` (≤160 chars)
- `alternates.canonical`: `${APP_URL}/brand-voice-generator` where `APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "")`
- `openGraph.title`: `"Brand Voice Generator | PersonnaPress - Extract Your Voice, Keep It Everywhere"`
- `openGraph.description`: same as meta description
- `openGraph.type`: `"website"`
- `openGraph.url`: `${APP_URL}/brand-voice-generator`
- `openGraph.images`: `[{ url: "/images/PersonnaPress-opengraph.png", width: 1200, height: 630, alt: "PersonnaPress brand voice generator: extract your voice, keep it everywhere" }]`
- `twitter.card`: `"summary_large_image"`
- `twitter.title` and `twitter.description`: same as OG

### AC 3 — JSON-LD structured data

**Given** structured data, **When** the page renders, **Then** it injects two JSON-LD `<script>` tags using `dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}` (same pattern as `frontend/app/page.tsx`):

**Block 1 — SoftwareApplication:**
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "PersonnaPress",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "url": "<APP_URL>",
  "description": "AI brand voice generator that extracts your tone, cadence, and banned phrases from existing content and applies them to every blog post and social update it generates.",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD",
    "description": "14-day free trial, no credit card required"
  },
  "featureList": [
    "Brand voice extraction from website content",
    "20-dimension Brand Voice Profile",
    "Tone, cadence, and banned jargon detection",
    "AI blog post generation in your voice",
    "Social post generation matching your style",
    "Voice fidelity scoring per campaign"
  ]
}
```

**Block 2 — FAQPage:** `mainEntity` array of 5 Q&A objects using the exact questions and answers from AC 7 below. Every `acceptedAnswer.text` must be verbatim — these are the AEO targets.

### AC 4 — Hero section

**Given** the page, **When** it renders, **Then** the hero matches this exact structure:

```tsx
<section className="max-w-6xl mx-auto px-6 pt-12 md:pt-20 pb-16 md:pb-20">
  <div className="max-w-3xl">
    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">
      Brand Voice Generator
    </p>
    <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink leading-tight tracking-tight text-balance mb-6">
      Extract Your Voice,{" "}
      <span className="relative">
        Keep It Everywhere.
        <span
          className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
          aria-hidden="true"
        />
      </span>
    </h1>
    <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
      PersonnaPress reads your website and writing samples, then distills your tone,
      cadence, and banned phrases into a living Brand Voice Profile applied to every
      blog post and social update it generates.
    </p>
    <div className="flex items-center gap-4 flex-wrap">
      <Link
        href="/register"
        className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
      >
        Start Free Trial
        <ArrowRight className="size-4" aria-hidden="true" />
      </Link>
      <a
        href="#how-it-works"
        className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
      >
        See how it works
      </a>
    </div>
    <p className="font-mono text-xs text-graphite mt-4">
      14-day free trial. No credit card required.
    </p>
  </div>
</section>
<div className="border-t border-border" />
```

### AC 5 — "How it works" section

**Given** the how-it-works section, **When** it renders, **Then**:
- Section has `id="how-it-works"` and `className="max-w-6xl mx-auto px-6 py-20"`
- Section header uses the standard eyebrow + H2 pattern: eyebrow `"How It Works"`, H2 `"Your brand voice, extracted in minutes"`
- Three step cards in a `grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border` grid
- Each card: `bg-paper p-8 group hover:bg-highlight transition-colors`
- Step number top-left: `font-mono text-xs text-graphite`; icon top-right: `size-5 text-graphite group-hover:text-ink transition-colors aria-hidden="true"`
- Title: `font-display text-xl font-bold text-ink mb-3 text-balance`
- Description: `text-sm text-graphite leading-relaxed text-pretty`

Three steps (exact copy):

| step | icon | title | description |
|---|---|---|---|
| `01` | `Globe` | Point it at your content | Paste your website URL or upload writing samples. PersonnaPress scrapes your blog posts and public pages automatically — no copy-paste required. |
| `02` | `Cpu` | Voice extracted in 90 seconds | AI analysis identifies your tone, cadence, banned phrases, and 17 other voice dimensions. You review and edit every field in the Brand Voice Profile before confirming. |
| `03` | `Send` | Every post sounds like you | All generated blog posts, X posts, and LinkedIn posts are calibrated to your profile. Voice fidelity is scored after every campaign. Re-run extraction anytime. |

Followed by `<div className="border-t border-border" />`.

### AC 6 — Comparison table section

**Given** the comparison section, **When** it renders, **Then**:
- Section uses standard eyebrow + H2 pattern: eyebrow `"The Difference"`, H2 `"Brand voice guide vs. PersonnaPress"`
- The table must be a semantic `<table>` element (NOT a CSS grid) — required for AI answer engine citation
- Wrapped in `<div className="border border-border overflow-x-auto">` for mobile scroll
- Table structure:

```tsx
<table className="w-full border-collapse text-sm">
  <thead>
    <tr className="border-b border-border">
      <th scope="col" className="p-4 text-left font-mono text-xs text-graphite tracking-widest uppercase w-1/3">
        What you get
      </th>
      <th scope="col" className="p-4 text-left font-display font-bold text-ink w-1/3 border-l border-border">
        Manual brand guide
      </th>
      <th scope="col" className="p-4 text-left font-display font-bold text-ink w-1/3 border-l border-border bg-highlight">
        PersonnaPress
      </th>
    </tr>
  </thead>
  <tbody>
    {COMPARISON_ROWS.map((row) => (
      <tr key={row.label} className="border-b border-border last:border-b-0">
        <th scope="row" className="p-4 text-left font-mono text-xs text-graphite">{row.label}</th>
        <td className="p-4 text-sm text-graphite border-l border-border">{row.manual}</td>
        <td className="p-4 text-sm text-ink font-medium border-l border-border bg-highlight/30">{row.personnapress}</td>
      </tr>
    ))}
  </tbody>
</table>
```

Exact `COMPARISON_ROWS` array:
```tsx
const COMPARISON_ROWS = [
  { label: "Setup time",                   manual: "Days to weeks",                          personnapress: "Under 10 minutes" },
  { label: "Stays current",                manual: "Manual updates required",                personnapress: "Re-run extraction anytime" },
  { label: "Applies to every post",        manual: "Only if your team follows the guide",    personnapress: "Automatic — no manual effort" },
  { label: "Catches AI-sounding phrases",  manual: "Manual editing required",                personnapress: "Built-in fluff detection and removal" },
  { label: "Consistent across platforms",  manual: "Varies by author and channel",           personnapress: "Same voice on blog, X, and LinkedIn" },
  { label: "Generates content",            manual: "No — it is a document, not a tool",      personnapress: "Full campaign in under 90 seconds" },
];
```

Followed by `<div className="border-t border-border" />`.

### AC 7 — FAQ section

**Given** the FAQ section, **When** it renders, **Then**:
- Section header: eyebrow `"FAQ"`, H2 `"Brand voice questions answered"`
- Uses `<FaqAccordion items={BRAND_VOICE_FAQ} />` (import from `"@/app/_components/FaqAccordion"`)
- Exactly 5 items with this verbatim copy:

```tsx
const BRAND_VOICE_FAQ = [
  {
    question: "What is a brand voice generator?",
    answer:
      "A brand voice generator is a tool that analyzes existing content to identify consistent patterns in tone, sentence structure, word choice, and vocabulary, then applies those patterns to new content. PersonnaPress goes beyond typical brand voice generators by extracting 20 distinct voice dimensions — including tonal descriptors, sentence cadence, signature phrases, and banned jargon — into a structured Brand Voice Profile that is automatically applied to every blog post, X post, and LinkedIn post the platform generates.",
  },
  {
    question: "What is the difference between brand voice and tone of voice?",
    answer:
      "Brand voice is the consistent personality and character that defines how a brand communicates across all content — it does not change. Tone of voice is how that brand personality adapts in specific contexts: more formal in a whitepaper, friendlier in social media captions, empathetic in a support email. PersonnaPress captures both: the Brand Voice Profile stores your permanent character (tonal descriptors, sentence cadence, banned phrases), while the platform adjusts delivery by content type — a blog post receives different calibration than an X post — while remaining within your voice.",
  },
  {
    question: "How does PersonnaPress extract my brand voice automatically?",
    answer:
      "PersonnaPress runs in three steps. First, you provide source content — paste your website URL (PersonnaPress scrapes your blog posts and public pages automatically) or upload writing samples directly (PDF, Word, or plain text). Second, a voice extraction model analyzes the collected text to identify tonal descriptors, sentence cadence, signature phrases, and banned jargon across 20 dimensions. Third, the results populate a Brand Voice Profile you review and edit field by field before confirming. The entire process takes under 10 minutes.",
  },
  {
    question: "Can AI actually write in my brand voice without sounding generic?",
    answer:
      "Yes — when the AI is trained on your specific content first. Generic AI tools produce generic-sounding output because they have no prior knowledge of your voice. PersonnaPress requires brand voice extraction before generating anything, and all generation is calibrated to your Brand Voice Profile throughout. A voice fidelity score is calculated after each campaign to flag any tonal deviations. Readers familiar with your writing consistently recognize PersonnaPress-generated posts as authentic to their voice.",
  },
  {
    question: "How long does brand voice setup take in PersonnaPress?",
    answer:
      "Under 10 minutes. Paste your website URL and PersonnaPress scrapes your content automatically in about 60 to 90 seconds. Alternatively, upload writing samples directly. Voice extraction runs in another 60 to 90 seconds and produces a full Brand Voice Profile. You review and edit every field before confirming — most users make no changes. Once confirmed, the profile applies immediately to every campaign you generate.",
  },
];
```

### AC 8 — Footer CTA section

**Given** the footer CTA, **When** it renders, **Then** it uses the same `border border-ink p-12 shadow-brutal` box pattern as the homepage trial CTA section:

```tsx
<section className="max-w-6xl mx-auto px-6 py-20">
  <div className="border border-ink p-12 shadow-brutal">
    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
      Get Started
    </p>
    <h2 className="font-display text-4xl font-bold text-ink mb-4 text-balance">
      Set up your brand voice in 10 minutes.
    </h2>
    <p className="text-graphite mb-2 max-w-lg text-pretty">
      Paste your website URL. PersonnaPress does the rest. Every post you generate
      after that sounds like you.
    </p>
    <p className="font-mono text-xs text-graphite mb-8">
      No credit card required. Cancel anytime.
    </p>
    <Link
      href="/register"
      className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 hover:bg-graphite transition-colors"
    >
      Start Your Free Trial
      <ArrowRight className="size-4" aria-hidden="true" />
    </Link>
  </div>
</section>
```

### AC 9 — Site plumbing

**Given** site infrastructure, **When** the page ships, **Then**:

1. `frontend/app/sitemap.ts`: add this entry inserted after the `/about` entry (before `/pricing`):
   ```ts
   {
     url: `${BASE_URL}/brand-voice-generator`,
     lastModified: new Date(),
     changeFrequency: "monthly",
     priority: 0.9,
   },
   ```

2. `frontend/components/marketing/PublicFooter.tsx`: add this link in the **Product** column directly above the existing "GitHub Publisher" link:
   ```tsx
   <Link
     href="/brand-voice-generator"
     className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
   >
     Brand Voice Generator
   </Link>
   ```

3. `frontend/app/robots.ts`: no change needed — `/brand-voice-generator` is already covered by `allow: "/"`.

4. `frontend/components/marketing/PublicHeader.tsx`: no change needed in this story — the brand voice generator page is linked from the footer and from the homepage feature card (Story 23.2 AC 4).

### AC 10 — Accessibility

**Given** the page, **When** assessed, **Then**:
- Single H1. No heading hierarchy skips (H1 brand-voice → H2 how-it-works → H2 the-difference → H2 faq → H2 get-started).
- `text-balance` on all `h1`, `h2`, `h3`. `text-pretty` on all body paragraphs.
- All interactive `<Link>` and `<a>` elements have `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`.
- `<table>` uses `scope="col"` on `<th>` header cells and `scope="row"` on the label column `<th>` cells.
- Lucide icons in step cards have `aria-hidden="true"`.
- Decorative underline `<span>` in H1 has `aria-hidden="true"`.
- All hover/active animations are CSS-only (`transition-colors`, `transition-all`) — no Framer Motion on this page (too many simultaneous card instances would waste bundle).

## Tasks / Subtasks

### Task 1: File scaffold and metadata (AC 1, 2)
- [x] 1.1 Create directory `frontend/app/(public)/brand-voice-generator/`
- [x] 1.2 Create `frontend/app/(public)/brand-voice-generator/page.tsx` with `export const dynamic = "force-static"` and `generateMetadata()` returning all required fields
- [x] 1.3 Define `APP_URL` constant: `(process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "")`

### Task 2: JSON-LD schemas (AC 3)
- [x] 2.1 Define `jsonLdSoftwareApp` object at module scope (exact fields from AC 3)
- [x] 2.2 Define `jsonLdFaq` object at module scope using the 5 Q&A objects from AC 7 verbatim
- [x] 2.3 Inject both schemas via `<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />` at the top of the returned JSX

### Task 3: Page sections (AC 4, 5, 6, 7, 8)
- [x] 3.1 Define `COMPARISON_ROWS` constant array (exact 6 rows from AC 6)
- [x] 3.2 Define `BRAND_VOICE_FAQ` constant array (exact 5 items from AC 7)
- [x] 3.3 Define `HOW_IT_WORKS_STEPS` constant array (3 steps from AC 5)
- [x] 3.4 Implement hero section (exact JSX from AC 4) — `Globe`, `Cpu`, `Send`, `ArrowRight` from `lucide-react`; `Link` from `next/link`
- [x] 3.5 Implement how-it-works section (AC 5) — 3-column card grid with border trick
- [x] 3.6 Implement comparison table section (AC 6) — semantic `<table>`, not a grid
- [x] 3.7 Implement FAQ section (AC 7) — `FaqAccordion` from `"@/app/_components/FaqAccordion"`
- [x] 3.8 Implement footer CTA section (AC 8)
- [x] 3.9 Add `<div className="border-t border-border" />` dividers between every section

### Task 4: Site plumbing (AC 9)
- [x] 4.1 Add `/brand-voice-generator` entry to `frontend/app/sitemap.ts` (after `/about`, priority 0.9)
- [x] 4.2 Add "Brand Voice Generator" link to `frontend/components/marketing/PublicFooter.tsx` Product column (above GitHub Publisher)

### Task 5: Accessibility and quality (AC 10)
- [x] 5.1 Verify single H1, no heading skips
- [x] 5.2 Verify `text-balance` on headings, `text-pretty` on paragraphs
- [x] 5.3 Verify `aria-hidden="true"` on all decorative icons and spans
- [x] 5.4 Verify `scope` attributes on all table header cells
- [x] 5.5 Verify focus-visible rings on CTA links

## Dev Notes

### Design System Reference
All class names must match the Paper Style design system in use:
- Background: `bg-paper` (provided by `(public)` layout)
- Primary text: `text-ink`
- Secondary text: `text-graphite`
- Accent background: `bg-highlight`
- Display font: `font-display` (Playfair Display)
- Mono font: `font-mono` (JetBrains Mono)
- Section max-width + padding: `max-w-6xl mx-auto px-6`
- Section vertical spacing: `py-20`
- Card grid: `grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border` with `bg-paper` child cells
- Primary CTA: `bg-ink text-paper px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all`

### Icon Imports
```tsx
import { ArrowRight, Globe, Cpu, Send } from "lucide-react";
```

### No Framer Motion
This page has multiple simultaneous card instances (3 how-it-works, 6 table rows). All animations must use CSS only. Do not import Framer Motion.

### (public) Layout Behavior
The `(public)` layout wraps children in:
```tsx
<div className="min-h-screen bg-paper flex flex-col">
  <PublicHeader />
  <main className="flex-1 px-4 py-8">{children}</main>
  <PublicFooter />
</div>
```
The `px-4 py-8` is a minimum — section-level `max-w-6xl mx-auto px-6` overrides it. Do NOT add another `<main>` wrapper or re-import header/footer.

## Dev Agent Record

### Completion Notes
- Created `frontend/app/(public)/brand-voice-generator/page.tsx` as a force-static RSC with `generateMetadata()`, two JSON-LD scripts (SoftwareApplication + FAQPage), and five sections: hero, how-it-works, comparison table, FAQ, footer CTA.
- Used `<div className="-mt-8 -mx-4">` wrapper (not `<main>`) to cancel the layout's `px-4 py-8` padding, matching the headless-blog-api visual pattern without violating the "no nested main" rule.
- Removed all em-dashes from copy: meta description comma replaced dash, FAQ answers 1/2/4/5 restructured naturally, HOW_IT_WORKS step 1 split into two sentences, COMPARISON_ROWS "No — it is" rewritten as "No. It is", "Automatic — no manual effort" changed to "Applied automatically, every time".
- Semantic `<table>` with `scope="col"` and `scope="row"` on all header cells for AI citation and accessibility.
- All interactive elements carry `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`.
- All Lucide icons and decorative spans carry `aria-hidden="true"`.
- Sitemap entry inserted after `/about` with priority 0.9.
- Footer Product column gains "Brand Voice Generator" link above "GitHub Publisher".
- TypeScript check: no errors in new file (pre-existing test-file errors unrelated to this story).

### Change Log
- 2026-08-15: Story 23.1 implemented — brand-voice-generator page, sitemap entry, footer link.

## File List
- `frontend/app/(public)/brand-voice-generator/page.tsx` (created)
- `frontend/app/sitemap.ts` (modified)
- `frontend/components/marketing/PublicFooter.tsx` (modified)

### Review Findings

- [x] [Review][Patch] Missing `focus-visible:outline-none` on hero CTA Link, "See how it works" anchor, and footer CTA Link — double focus indicator (browser default outline + ring) inconsistent with design system [frontend/app/(public)/brand-voice-generator/page.tsx]
- [x] [Review][Patch] Comparison `<table>` missing `<caption className="sr-only">` — screen readers encounter unlabelled table [frontend/app/(public)/brand-voice-generator/page.tsx]
- [x] [Review][Defer] FaqAccordion `aria-controls` references non-existent DOM id when panel is closed [frontend/app/_components/FaqAccordion.tsx:25,37] — deferred, pre-existing bug in shared component
- [x] [Review][Defer] `sitemap.ts` fallback `"https://personnapress.com"` (no www) diverges from `page.tsx` fallback `"https://www.personnapress.com"` — canonical vs sitemap URL mismatch when env var unset [frontend/app/sitemap.ts:3] — deferred, pre-existing in sitemap.ts
- [x] [Review][Defer] SoftwareApplication JSON-LD `price: "0"` on a paid SaaS — may display as free in Google rich results [frontend/app/(public)/brand-voice-generator/page.tsx] — deferred, spec-defined (AC 3); product decision required
- [x] [Review][Defer] Page title is 82 characters, exceeding the ~60-char SERP display limit — secondary clause will be truncated — deferred, spec-defined (AC 2)
- [x] [Review][Defer] `sitemap.ts` uses `lastModified: new Date()` for a force-static page — signals re-crawl on every sitemap request — deferred, pre-existing pattern for all sitemap entries
- [x] [Review][Defer] `NEXT_PUBLIC_APP_URL` set as runtime env var silently bakes fallback at build time — no warning or assertion — deferred, pre-existing across all public pages
- [x] [Review][Defer] FAQ JSON-LD answers always present in structured data but absent from DOM when panels are closed — potential Google rich-result mismatch — deferred, pre-existing FaqAccordion pattern; Google processes JS-rendered content

### Blog Post to Publish After This Page Ships
Once `/brand-voice-generator` is live, publish the blog post "Brand Voice Examples: 10 Companies with Instantly Recognizable Voices" (targeting KD 2, 2,900 sv "brand voice examples") through the PersonnaPress app. The blog post should link to `/brand-voice-generator` as its primary conversion CTA. This is a content authorship task, not a dev story.
