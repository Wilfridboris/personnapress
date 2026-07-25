---
baseline_commit: e370e0c
---

# Story 8.10: About Page — Founder Story and Trust Signal

Status: done

## Story

As PersonnaPress,
I want an About page that tells Boris's founder story with Person schema markup,
so that visitors who check "who built this?" find a trust-building, rankable page before converting.

## Acceptance Criteria

1. **Route exists**: GET `/about` returns HTTP 200. The page is a static server component in the `(public)` route group and renders with `PublicHeader` and `PublicFooter`.

2. **Metadata**: `<title>` is exactly `About Boris Kwayep — Founder of PersonnaPress`. Meta description is `Boris Kwayep is the founder of PersonnaPress. He built it after watching a brilliant client go silent every week — not from lack of ideas, but from the cost of everything that comes after the idea.` Canonical URL is `https://www.personnapress.com/about`.

3. **Page structure**: The page renders three named sections in order: hero (H1 + lead), "The Origin Story" (H2 + prose + pullquote), "The Core Bet" (H2 + prose). Each section is separated by a `border-t border-border` horizontal rule.

4. **H1**: The page H1 is exactly `Boris Kwayep` in `font-display` (Playfair Display). A monospace label `FOUNDER · PERSONNAPRESS` appears above the H1.

5. **Pullquote**: The sentence "The bottleneck is not the idea. It is everything that comes after the idea." renders in a `bg-highlight` block with a left border `border-l-2 border-ink` inside the Origin Story section.

6. **Person JSON-LD**: The page embeds a `<script type="application/ld+json">` block with `@type: Person`, `name: Boris Kwayep`, `jobTitle: Founder`, `email: support@personnapress.com`, `sameAs: [LinkedIn URL, X URL]`, and `worksFor` pointing to the PersonnaPress Organization.

7. **CTA**: A "Try PersonnaPress Free" link (styled as the standard Paper Style ink button with `shadow-brutal`) links to `/dashboard`. A `font-mono text-xs text-graphite` line below it reads "14-day trial. No credit card required."

8. **Contact line**: Below the CTA, a line reads "Questions?" followed by a `mailto:support@personnapress.com` link.

9. **Social links**: At the bottom of the page content (above the footer), two links render with Lucide icons: one to `https://www.linkedin.com/in/boris-k-1218581a3/` labelled "LinkedIn", one to `https://x.com/BusinessBoris` labelled "@BusinessBoris". Both open in a new tab with `rel="noopener noreferrer"`.

10. **PublicHeader nav**: "About" link is added to the `<nav>` in `PublicHeader.tsx` after the Blog link, before the "Start Free Trial" CTA button. Styled identically to existing nav links (`text-sm text-graphite hover:text-ink transition-colors`).

11. **PublicFooter Company column**: A new "Company" column is added as the first column in the footer nav. It contains a single link: "About" pointing to `/about`. Column header style matches the existing footer column headers (`font-mono text-[10px] uppercase tracking-widest text-graphite/50`).

12. **Homepage Organization schema cross-link**: The `schemaOrganization` object in `frontend/app/page.tsx` gains a `"founder"` property: `{ "@type": "Person", "name": "Boris Kwayep", "url": "https://www.personnapress.com/about" }`.

13. **No em-dashes**: The page contains zero em-dash characters (`—`). All separators use periods, commas, or line breaks.

14. **No emojis**: The page contains zero emoji characters.

15. **Robots**: `robots` metadata allows indexing: `{ index: true, follow: true }`.

## Tasks / Subtasks

- [x] Task 1: Create `frontend/app/(public)/about/page.tsx` (AC: 1–9, 13–15)
  - [x] Add `export const metadata: Metadata` with title, description, canonical, robots, openGraph
  - [x] Define `const schemaPerson` object (see Dev Notes for exact shape)
  - [x] Render `<script type="application/ld+json">` with `JSON.stringify(schemaPerson)`
  - [x] Render Hero section: mono label, thick top border, H1, lead paragraph
  - [x] Render Origin Story section: mono label, H2, two prose paragraphs, pullquote block, one post-quote paragraph
  - [x] Render Core Bet section: mono label, H2, three prose paragraphs
  - [x] Render CTA section: ink button to `/dashboard`, trial note, contact line
  - [x] Render social links row: LinkedIn + X with Lucide icons, `target="_blank" rel="noopener noreferrer"`
  - [x] Audit: confirm zero em-dashes, zero emojis

- [x] Task 2: Update `frontend/components/marketing/PublicHeader.tsx` (AC: 10)
  - [x] Add `<Link href="/about" className="text-sm text-graphite hover:text-ink transition-colors">About</Link>` after the Blog link, before the Start Free Trial `<Link>`

- [x] Task 3: Update `frontend/components/marketing/PublicFooter.tsx` (AC: 11)
  - [x] Add Company column as the first `<div>` child of the footer `<nav>`, containing only the About link
  - [x] Match existing column structure exactly (same `gap-3 min-w-[120px]` classes)

- [x] Task 4: Update `frontend/app/page.tsx` Organization schema (AC: 12)
  - [x] Add `"founder": { "@type": "Person", "name": "Boris Kwayep", "url": \`${APP_URL}/about\` }` to `schemaOrganization`

## Dev Notes

### Architecture compliance

This is a pure frontend story. No backend changes. No new npm packages required.

**RSC rule**: The About page is static content only. No API calls. No `useEffect`. No `useState`. Render as a server component (no `'use client'` directive). This is the correct pattern per `project-context.md` — only session/auth checks belong in server components, but static content like this page is safe and ideal as a server component.

**Route group**: The file must live at `frontend/app/(public)/about/page.tsx`. The `(public)` group layout (`frontend/app/(public)/layout.tsx`) already wraps all children with `PublicHeader`, `<main className="flex-1 px-4 py-8">`, and `PublicFooter`. The page component renders inside that `<main>`, so do NOT add another header or footer.

### Page file — complete implementation

`frontend/app/(public)/about/page.tsx`:

```tsx
import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Linkedin, Twitter } from "lucide-react";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com";

export const metadata: Metadata = {
  title: "About Boris Kwayep — Founder of PersonnaPress",
  description:
    "Boris Kwayep is the founder of PersonnaPress. He built it after watching a brilliant client go silent every week — not from lack of ideas, but from the cost of everything that comes after the idea.",
  robots: { index: true, follow: true },
  alternates: { canonical: `${APP_URL}/about` },
  openGraph: {
    title: "About Boris Kwayep — Founder of PersonnaPress",
    description:
      "Boris Kwayep is the founder of PersonnaPress. He built it after watching a brilliant client go silent every week — not from lack of ideas, but from the cost of everything that comes after the idea.",
    url: `${APP_URL}/about`,
    type: "profile",
    images: [
      {
        url: "/images/PersonnaPress-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PersonnaPress — AI Blog Writer That Sounds Like You",
      },
    ],
  },
};

const schemaPerson = {
  "@context": "https://schema.org",
  "@type": "Person",
  name: "Boris Kwayep",
  jobTitle: "Founder",
  description:
    "Software developer with 7 years of experience building scalable applications. Founder of PersonnaPress, an AI blog writer and content automation platform.",
  worksFor: {
    "@type": "Organization",
    name: "PersonnaPress",
    url: APP_URL,
  },
  url: `${APP_URL}/about`,
  email: "support@personnapress.com",
  sameAs: [
    "https://www.linkedin.com/in/boris-k-1218581a3/",
    "https://x.com/BusinessBoris",
  ],
};

export default function AboutPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaPerson) }}
      />

      <div className="max-w-2xl mx-auto py-8">

        {/* Hero */}
        <header className="mb-12">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">
            Founder · PersonnaPress
          </p>
          <div className="border-t-2 border-ink pt-8">
            <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink leading-tight tracking-tight text-balance mb-6">
              Boris Kwayep
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty max-w-lg">
              Software developer. Seven years building scalable applications.
              Now building AI products around marketing — so businesses can grow
              and make sales without the publishing bottleneck that stops most of them.
            </p>
          </div>
        </header>

        <div className="border-t border-border" />

        {/* Origin Story */}
        <section className="py-12" aria-labelledby="origin-heading">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-8">
            The Origin Story
          </p>
          <h2
            id="origin-heading"
            className="font-display text-3xl font-bold text-ink text-balance mb-8"
          >
            The bottleneck is not the idea.
          </h2>

          <div className="space-y-5 text-base text-graphite leading-relaxed text-pretty">
            <p>
              I was helping a client with his content strategy. Smart guy. Years
              of real experience, strong opinions, genuinely useful things to say.
            </p>
            <p>
              But he never published. Not because he had nothing to write about.
              He had too much. The problem was the gap between having an insight
              and turning it into a polished blog post, formatted for SEO, then
              posted to his WordPress site, LinkedIn, and X. That process cost
              him a week. So he skipped it every time.
            </p>
          </div>

          <blockquote className="my-10 px-6 py-5 bg-highlight border-l-2 border-ink">
            <p className="font-display text-xl text-ink leading-snug text-balance">
              The bottleneck is not the idea. It is everything that comes after
              the idea.
            </p>
          </blockquote>

          <div className="space-y-5 text-base text-graphite leading-relaxed text-pretty">
            <p>
              I kept thinking about that gap. Not the writing itself. The
              formatting, the SEO structure, the four separate logins, the
              scheduling. Every one of those steps is a place where a busy person
              stops. And most of them do.
            </p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* The Core Bet */}
        <section className="py-12" aria-labelledby="core-bet-heading">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-8">
            The Core Bet
          </p>
          <h2
            id="core-bet-heading"
            className="font-display text-3xl font-bold text-ink text-balance mb-8"
          >
            Voice fidelity is the unlock, not automation.
          </h2>

          <div className="space-y-5 text-base text-graphite leading-relaxed text-pretty">
            <p>
              Most AI writing tools solve for speed. They give you something
              fast. But fast and generic still does not publish. It still does
              not rank. And it definitely does not sound like you.
            </p>
            <p>
              PersonnaPress is built on a different bet: when content sounds
              exactly like you, you approve it. When you approve it, it
              publishes. When it publishes consistently, it compounds. The voice
              is not a feature. It is the product.
            </p>
            <p>That is what I am building.</p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* CTA */}
        <section className="py-12">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            Try PersonnaPress Free
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
          <p className="font-mono text-xs text-graphite mt-4">
            14-day trial. No credit card required.
          </p>
          <p className="text-sm text-graphite mt-4">
            Questions?{" "}
            <a
              href="mailto:support@personnapress.com"
              className="underline underline-offset-4 hover:text-ink transition-colors"
            >
              support@personnapress.com
            </a>
          </p>
        </section>

        <div className="border-t border-border" />

        {/* Social links */}
        <div className="pt-8 flex items-center gap-6">
          <a
            href="https://www.linkedin.com/in/boris-k-1218581a3/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors"
          >
            <Linkedin className="size-4" aria-hidden="true" />
            LinkedIn
          </a>
          <a
            href="https://x.com/BusinessBoris"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors"
          >
            <Twitter className="size-4" aria-hidden="true" />
            @BusinessBoris
          </a>
        </div>
      </div>
    </>
  );
}
```

**Note on em-dash in metadata description**: The `metadata.description` above contains an em-dash (`—`). This violates the project constraint. Replace with: `...He built it after watching a brilliant client go silent every week. Not from lack of ideas. From the cost of everything that comes after the idea.`

**Note on lead paragraph em-dash**: The lead paragraph contains `— so businesses`. Replace `—` with a period and new sentence: `...Now building AI products around marketing. So businesses can grow and make sales without the publishing bottleneck that stops most of them.`

Apply these two fixes when implementing. The implementation guide above is otherwise complete and copy-pasteable.

### PublicHeader change — exact diff

File: `frontend/components/marketing/PublicHeader.tsx`

Current (lines 24-27):
```tsx
          <a href="/#faq" className="text-sm text-graphite hover:text-ink transition-colors">FAQ</a>
          <Link href="/blog" className="text-sm text-graphite hover:text-ink transition-colors">Blog</Link>
          <Link
            href="/dashboard"
```

Replace with:
```tsx
          <a href="/#faq" className="text-sm text-graphite hover:text-ink transition-colors">FAQ</a>
          <Link href="/blog" className="text-sm text-graphite hover:text-ink transition-colors">Blog</Link>
          <Link href="/about" className="text-sm text-graphite hover:text-ink transition-colors">About</Link>
          <Link
            href="/dashboard"
```

### PublicFooter change — exact diff

File: `frontend/components/marketing/PublicFooter.tsx`

Current: the footer `<nav>` contains three columns: Product, Resources, Account.

Add "Company" as the first column. Insert before the Product `<div>`:

```tsx
            {/* Company */}
            <div className="flex flex-col gap-3 min-w-[120px]">
              <p className="font-mono text-[10px] uppercase tracking-widest text-graphite/50">Company</p>
              <Link href="/about" className="font-mono text-xs text-graphite hover:text-ink transition-colors">About</Link>
            </div>
```

### Homepage Organization schema change — exact diff

File: `frontend/app/page.tsx`

Current `schemaOrganization` (approximately lines 88-96):
```ts
const schemaOrganization = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "PersonnaPress",
  url: APP_URL,
  logo: `${APP_URL}/images/PersonnaPress-opengraph.png`,
  description: "...",
};
```

Add `founder` property after `description`:
```ts
const schemaOrganization = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "PersonnaPress",
  url: APP_URL,
  logo: `${APP_URL}/images/PersonnaPress-opengraph.png`,
  description:
    "PersonnaPress is an AI content automation platform that learns your brand voice and publishes SEO-structured content across multiple platforms.",
  founder: {
    "@type": "Person",
    name: "Boris Kwayep",
    url: `${APP_URL}/about`,
  },
};
```

### Design tokens (reference)

All classes used are already defined in `globals.css` or Tailwind v4 theme:

| Token | Value |
|---|---|
| `bg-paper` | #F9F9F6 |
| `text-ink` | #111111 |
| `text-graphite` | #555555 |
| `border-border` | #E5E5E5 |
| `bg-highlight` | #FFF1B8 |
| `font-display` | Playfair Display (via `--font-display`) |
| `font-mono` | JetBrains Mono (via `--font-mono`) |
| `shadow-brutal` | `box-shadow: 4px 4px 0px 0px var(--color-ink)` (defined in globals.css) |

No new CSS required.

### Icon availability check

Before implementing, confirm `Linkedin` and `Twitter` are exported from the installed lucide-react version:

```bash
node -e "const { Linkedin, Twitter } = require('lucide-react'); console.log(!!Linkedin, !!Twitter);"
```

If `Twitter` is not available (renamed to `X` in newer versions), substitute with `ExternalLink` or whichever X-equivalent icon is available. Do NOT add a new icon library.

### Files being modified

| File | Action |
|---|---|
| `frontend/app/(public)/about/page.tsx` | CREATE — new static server component |
| `frontend/components/marketing/PublicHeader.tsx` | UPDATE — add About nav link |
| `frontend/components/marketing/PublicFooter.tsx` | UPDATE — add Company column |
| `frontend/app/page.tsx` | UPDATE — add `founder` property to `schemaOrganization` |

### No tests required

This story is four static markup changes. No logic branches, no async calls, no state. No new tests needed. Verify by running the dev server and navigating to `/about`.

### Regression check

After implementation, verify:
- `/about` renders with PublicHeader and PublicFooter (no duplicate headers)
- PublicHeader nav on every public page now shows "About" between Blog and the CTA
- Footer on every public page shows the Company column as the leftmost column
- Homepage `<script type="application/ld+json">` for Organization now contains `founder`
- No em-dash characters appear anywhere on the About page (including metadata)
- The pullquote has a yellow `bg-highlight` background and a 2px ink left border

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Created `frontend/app/(public)/about/page.tsx` as a static server component with metadata, Person JSON-LD schema, hero/origin/core-bet/CTA/social-links sections.
- `Twitter` and `Linkedin` icons are not in the installed lucide-react version; used `X` (available) for the X link and `ExternalLink` for the LinkedIn link per Dev Notes fallback instruction.
- Em-dashes in metadata `title` fields are required by AC2 (exact title string). Visible page body JSX contains zero em-dashes. OG alt text em-dash removed.
- Added About nav link to `PublicHeader.tsx` after Blog, before Start Free Trial CTA.
- Added Company column as first footer nav column in `PublicFooter.tsx` with About link.
- Added `founder` property to `schemaOrganization` in `frontend/app/page.tsx`.
- No new dependencies. No tests required (static markup only per Dev Notes).

### File List

- `frontend/app/(public)/about/page.tsx` — CREATED
- `frontend/components/marketing/PublicHeader.tsx` — UPDATED
- `frontend/components/marketing/PublicFooter.tsx` — UPDATED
- `frontend/app/page.tsx` — UPDATED

### Review Findings

- [x] [Review][Patch] Em-dash in metadata.title and openGraph.title — replaced `—` with `,` [frontend/app/(public)/about/page.tsx:8,14]
- [x] [Review][Patch] JSON-LD dangerouslySetInnerHTML missing </script> escape — added .replace(/</g, "\\u003c") [frontend/app/(public)/about/page.tsx:55]
- [x] [Review][Patch] APP_URL ?? "" doesn't guard empty string — changed ?? to || [frontend/app/(public)/about/page.tsx:5]
- [x] [Review][Patch] openGraph.type "profile" missing required OG profile properties — changed to "website" [frontend/app/(public)/about/page.tsx:18]
- [x] [Review][Patch] X (close icon) used for X social link — replaced with ExternalLink, removed unused X import [frontend/app/(public)/about/page.tsx:3,199]
- [x] [Review][Patch] Social links section no accessible label — added aria-label to container div and individual links [frontend/app/(public)/about/page.tsx:181,186,196]
- [x] [Review][Patch] CTA section no accessible label — added aria-label to section element [frontend/app/(public)/about/page.tsx:156]
- [x] [Review][Patch] "7 years" in schema vs "Seven years" in body — aligned schema to "seven years" [frontend/app/(public)/about/page.tsx:36]
- [x] [Review][Patch] blockquote no accessible attribution — added sr-only footer with cite [frontend/app/(public)/about/page.tsx:110]

## Change Log

- (2026-07-24) Story created ready-for-dev. About page with Boris Kwayep founder story, Person JSON-LD schema, nav updates to PublicHeader and PublicFooter, Organization schema founder cross-link on homepage.
- (2026-07-24) Implemented all 4 tasks. Static About page created with Person JSON-LD, hero/origin/core-bet/CTA/social sections. PublicHeader About nav link added. PublicFooter Company column added. Homepage Organization schema gained founder property. Marked review.
