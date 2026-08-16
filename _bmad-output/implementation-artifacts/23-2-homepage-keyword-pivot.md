---
baseline_commit: 6ab2559b51d4f1e34139e786e7eeac2b4db0a19c
---

# Story 23.2: Homepage Keyword Pivot

Status: done

## Story

As a potential customer searching for an "AI content platform" or "AI marketing tools",
I want the PersonnaPress homepage to immediately communicate that it is a full AI content platform,
So that the page ranks for platform-category keywords and accurately represents the full product scope.

## Background / SEO Context

The homepage currently targets "AI Blog Writer That Sounds Like You" — a keyword category declining -71% YoY. The highest-volume, low-to-medium competition commercial keywords are "ai powered content creation platform" (6,600 sv, KD 33) and "ai marketing tools" (4,400 sv, KD 19). This story changes only: (1) the metadata and JSON-LD descriptions, (2) the hero H1 and subhead copy, and (3) adds one internal link from the homepage's Voice Profile feature card to the new `/brand-voice-generator` page. Every other section, class, data array, and component stays exactly as-is.

**Scope is intentionally narrow.** No structural changes. No new components. No section rearrangements.

## Acceptance Criteria

### AC 1 — Metadata

**Given** `frontend/app/page.tsx`, **When** the `export const metadata: Metadata` constant is edited, **Then** these exact values are used:

```ts
export const metadata: Metadata = {
  title: {
    absolute: "PersonnaPress | Official Site - The AI Content Platform That Publishes in Your Brand Voice",
  },
  description:
    "PersonnaPress is an AI content platform that extracts your brand voice and turns your ideas into SEO-ranked blog posts and social campaigns — published automatically to WordPress, Webflow, LinkedIn, X, and more.",
  metadataBase: new URL(APP_URL),           // UNCHANGED
  alternates: {
    canonical: APP_URL,                     // UNCHANGED
  },
  openGraph: {
    title: "PersonnaPress | Official Site - The AI Content Platform That Publishes in Your Brand Voice",
    description:
      "Turn raw ideas into on-brand blog posts, social campaigns, and featured images — published to all your platforms in under 90 seconds.",
    url: APP_URL,                           // UNCHANGED
    type: "website",                        // UNCHANGED
    images: [
      {
        url: "/images/PersonnaPress-opengraph.png",   // UNCHANGED
        width: 1200,                                  // UNCHANGED
        height: 630,                                  // UNCHANGED
        alt: "PersonnaPress - The AI Content Platform That Publishes in Your Brand Voice",
      },
    ],
  },
};
```

All other metadata fields are unchanged.

### AC 2 — JSON-LD schema updates

**Given** the three schema constants at the top of `frontend/app/page.tsx`, **When** edited, **Then**:

**`schemaWebsite`** — change only `description`:
```ts
const schemaWebsite = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "PersonnaPress",           // UNCHANGED
  url: APP_URL,                    // UNCHANGED
  description:
    "An AI content platform that extracts your brand voice and generates SEO-ranked blog posts, social campaigns, and featured images in your authentic style. Published to WordPress, Webflow, LinkedIn, and X.",
};
```

**`schemaSoftwareApp`** — change only `description`:
```ts
const schemaSoftwareApp = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "PersonnaPress",                    // UNCHANGED
  applicationCategory: "BusinessApplication", // UNCHANGED
  operatingSystem: "Web",                   // UNCHANGED
  url: APP_URL,                             // UNCHANGED
  description:
    "PersonnaPress is an AI-powered content platform that extracts your brand voice from existing content, then turns raw ideas into SEO-structured blog posts, social campaigns, and featured images — all published to WordPress, Webflow, LinkedIn, and X in your authentic voice. Human approval required before any publish.",
  offers: { ... },        // UNCHANGED — keep existing offers object exactly
  featureList: [ ... ],   // UNCHANGED — keep existing featureList array exactly
};
```

**`schemaOrganization`** — no changes whatsoever.
**`schemaFaq`** — no changes whatsoever.

### AC 3 — Hero H1 copy

**Given** the hero section in `frontend/app/page.tsx`, **When** the H1 is edited, **Then** replace only the text content of the H1 and its inner `<span>`:

**Before:**
```tsx
<h1 className="font-display text-6xl lg:text-7xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
  The AI Blog Writer{" "}
  <span className="relative">
    That Sounds Like You.
    <span
      className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
      aria-hidden="true"
    />
  </span>
</h1>
```

**After:**
```tsx
<h1 className="font-display text-6xl lg:text-7xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
  The AI Content Platform{" "}
  <span className="relative">
    That Publishes in Your Brand Voice.
    <span
      className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
      aria-hidden="true"
    />
  </span>
</h1>
```

The `className` on the `<h1>` and both `<span>` elements is **unchanged**.

### AC 4 — Hero subhead copy

**Given** the hero subhead paragraph, **When** edited, **Then** replace only the text content:

**Before:**
```tsx
<p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
  Drop in a quick voice memo or brain dump. PersonnaPress learns your
  tone, removes the AI fluff, and turns your notes into published,
  ranked articles in seconds.
</p>
```

**After:**
```tsx
<p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
  PersonnaPress learns your voice from existing content, then turns raw
  ideas into SEO-structured blog posts, social campaigns, and featured
  images — published to all your platforms in under 90 seconds.
</p>
```

The `className` is **unchanged**.

### AC 5 — Internal link from Voice Profile feature card

**Given** the `KEY_FEATURES` array in `frontend/app/page.tsx`, **When** the "Voice Profile" feature card renders (index 0 of `KEY_FEATURES`), **Then** a `<Link>` is added inside the card article, after the description paragraph:

The feature grid currently renders:
```tsx
{KEY_FEATURES.map(({ icon: Icon, title, description }) => (
  <article key={title} className="bg-paper p-8 group hover:bg-highlight transition-colors">
    <Icon className="size-5 text-graphite mb-6 group-hover:text-ink transition-colors" aria-hidden="true" />
    <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">{title}</h3>
    <p className="text-sm text-graphite leading-relaxed text-pretty">{description}</p>
  </article>
))}
```

This map-based render must NOT change. Instead, add an optional `href` field to `KEY_FEATURES` and conditionally render the link:

```tsx
const KEY_FEATURES = [
  {
    icon: Fingerprint,
    title: "Voice Profile",
    description: "...",          // UNCHANGED
    href: "/brand-voice-generator",
  },
  {
    icon: Eraser,
    title: "No AI Fluff",
    description: "...",          // UNCHANGED
  },
  {
    icon: CalendarCheck,
    title: "Schedule and Publish",
    description: "...",          // UNCHANGED
  },
];
```

Updated card render (only the inner JSX changes — the `article` wrapper class stays identical):
```tsx
{KEY_FEATURES.map(({ icon: Icon, title, description, href }) => (
  <article key={title} className="bg-paper p-8 group hover:bg-highlight transition-colors">
    <Icon className="size-5 text-graphite mb-6 group-hover:text-ink transition-colors" aria-hidden="true" />
    <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">{title}</h3>
    <p className="text-sm text-graphite leading-relaxed text-pretty">{description}</p>
    {href && (
      <Link
        href={href}
        className="mt-3 inline-flex items-center gap-1 font-mono text-xs text-ink underline underline-offset-2 hover:text-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
      >
        Learn how brand voice extraction works
        <ArrowRight className="size-3" aria-hidden="true" />
      </Link>
    )}
  </article>
))}
```

`KEY_FEATURES` type definition must be updated to `href?: string` (optional, not required — the other two cards have no link and must not be affected).

### AC 6 — Zero regressions in all other sections

**Given** every other section of `frontend/app/page.tsx`, **When** the file is edited, **Then** the following are pixel-identical to the pre-story state:
- `WORKFLOW_STEPS` array — unchanged
- `PLATFORMS` array — unchanged
- `PERSONAS` array — unchanged
- `PAIN_POINTS` array — unchanged
- `BEFORE_ITEMS` / `AFTER_ITEMS` arrays — unchanged
- `STARTER_FEATURES` / `GROWTH_FEATURES` / `AGENCY_FEATURES` arrays — unchanged
- `FAQ_ITEMS` array — unchanged
- `schemaOrganization` — unchanged
- `schemaFaq` — unchanged
- All section JSX (Problem Statement, Who It's For, Workflow, Before/After, Platforms, Trial CTA, Pricing, FAQ) — unchanged
- `PublicHeader`, `PublicFooter`, `EmailCaptureWidget` — unchanged
- Primary hero CTA: `<Link href="/dashboard">Create My First Post</Link>` — unchanged (text, href, classes all unchanged)
- Secondary hero anchor: `<a href="#workflow">See how it works</a>` — unchanged
- Hero mono note: "14-day free trial. No credit card required." — unchanged

### AC 7 — Sitemap and robots

**Given** `frontend/app/sitemap.ts` and `frontend/app/robots.ts`, **When** this story ships, **Then** no changes are made to either file. The homepage entry already has `priority: 1`. The robots.ts already allows all bots. No edits needed.

## Tasks / Subtasks

### Task 1: Metadata update (AC 1)
- [x] 1.1 In `frontend/app/page.tsx`, update `metadata.title.absolute` to the new platform-angle title
- [x] 1.2 Update `metadata.description` to the new platform-angle description
- [x] 1.3 Update `metadata.openGraph.title` to match
- [x] 1.4 Update `metadata.openGraph.description` to the shorter variant
- [x] 1.5 Update `metadata.openGraph.images[0].alt`

### Task 2: JSON-LD updates (AC 2)
- [x] 2.1 Update `schemaWebsite.description`
- [x] 2.2 Update `schemaSoftwareApp.description` (only; leave `offers` and `featureList` untouched)
- [x] 2.3 Verify `schemaOrganization` and `schemaFaq` are untouched

### Task 3: Hero copy updates (AC 3, 4)
- [x] 3.1 Update H1 text from "The AI Blog Writer / That Sounds Like You." to "The AI Content Platform / That Publishes in Your Brand Voice." — classes unchanged
- [x] 3.2 Update subhead paragraph copy — class unchanged (em-dash replaced with comma per project rule)
- [x] 3.3 Verify all other hero elements (CTAs, mono note, section classes) are untouched

### Task 4: Internal link in Voice Profile card (AC 5)
- [x] 4.1 Add `href?: string` field to the `KEY_FEATURES` type (inline or explicit)
- [x] 4.2 Add `href: "/brand-voice-generator"` to the Voice Profile entry only
- [x] 4.3 Update the card map render to conditionally render the `<Link>` with exact classes from AC 5
- [x] 4.4 Verify the No AI Fluff and Schedule and Publish cards are visually unchanged

### Task 5: Regression check (AC 6)
- [x] 5.1 Verify all data arrays are unchanged
- [x] 5.2 Verify all section JSX below the hero is unchanged
- [x] 5.3 Verify primary CTA `href="/dashboard"` and text "Create My First Post" are unchanged
- [x] 5.4 Verify no em-dashes introduced in copy (use regular hyphen `-` for the metadata separator, not `—`)

## Dev Notes

### Scope discipline
This story is intentionally narrow. The only file that changes is `frontend/app/page.tsx`. The only changes are: 5 metadata strings, 2 schema description strings, H1 text, subhead text, and one conditional `<Link>` added to the Voice Profile feature card. If you find yourself touching anything else, stop — that is out of scope.

### Em-dash rule
The project bans em-dashes (`—`) in user-facing copy and prompts. However, the metadata description uses `—` as punctuation in a string literal (not in a user-facing UI element). Check project memory: the rule is "no em-dash in generated copy or prompts". Metadata strings are hardcoded, not generated. Still, to be safe, the new `metadata.description` uses `—` in a sentence — this is acceptable as it is a hardcoded string in a metadata constant, matching the pattern in `frontend/app/(public)/headless-blog-api/page.tsx` which also uses `—` in its description. If the code reviewer flags this, replace with a comma or restructure the sentence.

### After this story ships
1. Publish blog post: "Brand Voice Examples: 10 Companies with Instantly Recognizable Voices" via the PersonnaPress app (targets KD 2, 2,900 sv). The blog post should link to `/brand-voice-generator`. This is content authorship, not a dev story.
2. Submit both new/updated pages to Google Search Console for crawl request.

## Dev Agent Record

### Completion Notes

Implementation date: 2026-08-15. Only `frontend/app/page.tsx` was changed.

- **AC 1 (Metadata):** Updated `title.absolute`, `description`, `openGraph.title`, `openGraph.description`, and `openGraph.images[0].alt` to platform-angle copy. Em-dashes in metadata description and OG description retained per story Dev Notes (hardcoded metadata strings, not user-facing UI copy).
- **AC 2 (JSON-LD):** Updated `schemaWebsite.description` and `schemaSoftwareApp.description` only. `offers`, `featureList`, `schemaOrganization`, and `schemaFaq` are untouched.
- **AC 3 (H1):** H1 now reads "The AI Content Platform / That Publishes in Your Brand Voice." All classNames unchanged.
- **AC 4 (Subhead):** Subhead updated. Em-dash from the AC spec replaced with a comma ("images, published to all your platforms in under 90 seconds") — the project rule bans em-dashes in all public page copy (body paragraphs), and subtask 5.4 confirms this.
- **AC 5 (Internal link):** `href?: string` added to `KEY_FEATURES` items via TypeScript inference. Voice Profile entry gets `href: "/brand-voice-generator"`. Card `.map()` destructures `href` and conditionally renders `<Link>` with the exact classes from the AC. No AI Fluff and Schedule and Publish cards are unaffected.
- **AC 6 (Regressions):** All data arrays, section JSX, CTAs, mono note, and footer unchanged. Verified via Python grep checks.
- **AC 7 (Sitemap/robots):** No changes.
- **TS clean:** `npx tsc --noEmit` reports zero errors in `page.tsx`.

### File List

- `frontend/app/page.tsx` — modified (metadata, JSON-LD descriptions, H1, subhead, KEY_FEATURES + card render)

### Change Log

- 2026-08-15: Homepage keyword pivot — metadata, JSON-LD, H1, subhead, Voice Profile internal link (Story 23.2)

### Review Findings

- [x] [Review][Defer] Meta description length ~215 chars exceeds Google's ~155-160 char SERP display limit [frontend/app/page.tsx:31] — deferred, pre-existing SEO tradeoff; Google rewrites descriptions; target keywords benefit from full copy
- [x] [Review][Defer] Page title 90 chars exceeds ~60-char SERP display limit [frontend/app/page.tsx:28] — deferred, spec-mandated (AC 1); intentional keyword length trade-off
- [x] [Review][Defer] OG `og:image:alt` contains brand tagline copy, not an image description [frontend/app/page.tsx:47] — deferred, pre-existing pattern before this story
- [x] [Review][Defer] `schemaWebsite.description` ends with a dangling sentence fragment ("Published to WordPress, Webflow, LinkedIn, and X.") [frontend/app/page.tsx:59] — deferred, minor grammar in JSON-LD; not user-facing
- [x] [Review][Defer] Feature card link text "Learn how brand voice extraction works" is hardcoded for all `href` entries [frontend/app/page.tsx:513] — deferred, only one card has href today; extend type with `linkText?: string` when a second card needs a link
- [x] [Review][Defer] `{href && ...}` guard silently suppresses `href=""` (empty string is falsy) [frontend/app/page.tsx:508] — deferred, theoretical; no current KEY_FEATURES entry has `href: ""`
- [x] [Review][Defer] External URL passed to Next.js `<Link>` would be routed client-side, breaking the link [frontend/app/page.tsx:509] — deferred, theoretical; all current hrefs are internal paths
- [x] [Review][Defer] `key={title}` in KEY_FEATURES map would collide if two entries share a title [frontend/app/page.tsx:499] — deferred, pre-existing pattern unchanged by this story
