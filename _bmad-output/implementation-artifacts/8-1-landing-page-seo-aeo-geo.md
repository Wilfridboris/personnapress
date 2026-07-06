---
baseline_commit: d54c281
---

# Story 8.1: Production-Ready Landing Page — SEO / AEO / GEO

Status: done

## Story

As a potential user visiting personapress.io for the first time,
I want to land on a production-quality marketing page that explains what PersonnaPress does, answers my questions, and ranks in search engines and AI answer engines,
so that I can immediately understand the product's value and confidently start a free trial.

## Acceptance Criteria

1. **Given** favicon files are currently in `frontend/public/favicon/`, **When** this story is implemented, **Then** all favicon assets are moved to their correct Next.js App Router locations (see Task 1); the `public/favicon/` folder is deleted; `web-app-manifest-192x192.png` and `web-app-manifest-512x512.png` resolve at `/web-app-manifest-192x192.png` and `/web-app-manifest-512x512.png` (root of `public/`); a browser navigation to `/site.webmanifest` returns valid JSON; no broken icon links appear in browser dev tools.

2. **Given** the OG image exists at `frontend/public/images/PersonnaPress-opengraph.png`, **When** the page head is rendered, **Then** `layout.tsx` metadata includes `openGraph.images` pointing to `https://personapress.io/images/PersonnaPress-opengraph.png` (1200×630); the Twitter card also references the same image; `<meta property="og:image">` appears in rendered HTML.

3. **Given** `site.webmanifest` is moved to `frontend/public/`, **When** the page head is rendered, **Then** `layout.tsx` metadata includes `manifest: '/site.webmanifest'`; `<link rel="manifest">` appears in rendered HTML.

4. **Given** the current landing page has no FAQ, **When** this story is implemented, **Then** `frontend/app/page.tsx` includes a FAQ section with at least 10 question/answer pairs; each item has a visible question heading and answer paragraph; the section has `id="faq"` for anchor linking; the nav includes a "FAQ" link pointing to `#faq`.

5. **Given** the FAQ section content, **When** the page renders, **Then** a `<script type="application/ld+json">` block contains a valid `FAQPage` schema with all FAQ entries matching the rendered FAQ section text; each `mainEntity` item has `@type: "Question"` and a nested `acceptedAnswer` with `@type: "Answer"`.

6. **Given** the product is a SaaS tool, **When** the page renders, **Then** a `<script type="application/ld+json">` block contains a valid `SoftwareApplication` schema with: `name`, `applicationCategory: "BusinessApplication"`, `operatingSystem: "Web"`, `description`, `offers` (14-day free trial, price: 0), and `featureList` with at least 6 specific features.

7. **Given** the brand entity, **When** the page renders, **Then** a `<script type="application/ld+json">` block contains a valid `Organization` schema with `name`, `url`, and `logo` pointing to the absolute OG image URL.

8. **Given** the product targets specific personas, **When** this story is implemented, **Then** the landing page includes a "Who It's For" section with at least 3 distinct personas (founders/executives, solo coaches, content agencies); each persona has a heading and a 1–2 sentence description of the specific value they receive.

9. **Given** the product has a 14-day free trial, **When** this story is implemented, **Then** at least one section on the page explicitly uses the text "14-day free trial" with a CTA button linking to `/dashboard`; the trial is mentioned in the page hero or a dedicated pricing/trial section.

10. **Given** AI answer engines crawl the site, **When** this story is implemented, **Then** `frontend/app/robots.ts` includes explicit `allow: "/"` rules for `ClaudeBot` and `CCBot` in addition to the existing GPTBot, PerplexityBot, Googlebot, and anthropic-ai rules.

11. **Given** the Paper Style design system, **When** all new sections are implemented, **Then** every new element uses only classes from `globals.css` tokens: `bg-paper`, `text-ink`, `text-graphite`, `border-border`, `bg-highlight`, `font-display`, `font-body`, `font-mono`; no arbitrary hex colors or inline styles; icons come only from `lucide-react`; no emojis anywhere.

12. **Given** the logo image at `frontend/public/images/PersonnaPress-logo.png`, **When** the landing page renders, **Then** the `<header>` and `<footer>` use `<Image>` from `next/image` to display the logo instead of the current text-only wordmark; `width` and `height` props are explicitly set; `alt="PersonnaPress"` is set.

---

## Dev Agent Critical Rules

- **NO emojis** anywhere in JSX, comments, or strings — use lucide-react icons only.
- **Paper Style only** — colors come exclusively from `@theme` tokens in `globals.css`. Do not add new color classes.
- **`next/image` for all images** — never use raw `<img>` tags for project assets.
- **RSC rule** — `page.tsx` is a Server Component (no `"use client"`). Do not add client-side state to `page.tsx`. The FAQ accordion (if interactive) must be a separate Client Component in a sibling file.
- **No em-dashes (—)** — use `&mdash;` or rephrase. This is a hard project constraint.
- **Icon imports** — `import { X, Y } from "lucide-react"` only. Never use emoji as icons.
- **Absolute OG image URLs** — in metadata objects use `https://personapress.io/images/PersonnaPress-opengraph.png`, not a relative path. Relative paths in JSON-LD are fine for `@id` but `logo` and `image` fields should be absolute.

---

## Tasks / Subtasks

### [x] Task 1: Favicon Asset Migration (AC: #1, #3)

Move all files from `frontend/public/favicon/` to their correct locations. Do this with PowerShell `Move-Item` or `Copy-Item` + delete, since git on Windows handles this as delete+add.

```
# Destination mapping:
# frontend/public/favicon/favicon.ico           → frontend/app/favicon.ico
# frontend/public/favicon/apple-touch-icon.png  → frontend/app/apple-icon.png
# frontend/public/favicon/favicon.svg           → frontend/app/icon.svg
# frontend/public/favicon/favicon-96x96.png     → frontend/app/icon.png
# frontend/public/favicon/web-app-manifest-192x192.png → frontend/public/web-app-manifest-192x192.png
# frontend/public/favicon/web-app-manifest-512x512.png → frontend/public/web-app-manifest-512x512.png
# frontend/public/favicon/site.webmanifest      → frontend/public/site.webmanifest
# After all moves: delete frontend/public/favicon/ (the now-empty directory)
```

**Why these locations:**
- `app/favicon.ico` — Next.js App Router auto-serves this at `/favicon.ico` and injects `<link rel="shortcut icon">` with no metadata config needed.
- `app/apple-icon.png` — Next.js App Router auto-serves at `/apple-icon.png` and injects `<link rel="apple-touch-icon">` automatically.
- `app/icon.svg` and `app/icon.png` — Next.js auto-serves as `<link rel="icon">` alternatives.
- `public/web-app-manifest-*.png` — the webmanifest references these as `/web-app-manifest-192x192.png` (root-relative). They must be in `public/` root to resolve correctly.
- `public/site.webmanifest` — served at `/site.webmanifest`; referenced in metadata as `manifest: '/site.webmanifest'`.

**After moving, verify:**
- `frontend/public/favicon/` directory is empty and deleted.
- `frontend/app/favicon.ico` exists.
- `frontend/public/web-app-manifest-192x192.png` exists (not in subfolder).

---

### [x] Task 2: Update `frontend/app/layout.tsx` Metadata (AC: #2, #3)

Modify the `metadata` export in `frontend/app/layout.tsx`:

```typescript
export const metadata: Metadata = {
  metadataBase: new URL("https://personapress.io"),
  title: {
    default: "PersonaPress - Publish in Your Voice, Not AI's",
    template: "%s | PersonaPress",
  },
  description:
    "PersonaPress turns your raw ideas into SEO-ranked blog posts and social campaigns that sound exactly like you. Built for founders, coaches, and agencies.",
  keywords: [
    "AI content writing",
    "blog automation",
    "content marketing automation",
    "social media automation",
    "SEO blog posts",
    "brand voice AI",
    "AI writing tool",
    "content agency tool",
    "WordPress publishing automation",
    "LinkedIn content automation",
  ],
  manifest: "/site.webmanifest",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/icon.png", type: "image/png" },
    ],
    apple: "/apple-icon.png",
    shortcut: "/favicon.ico",
  },
  openGraph: {
    title: "PersonaPress - Publish in Your Voice, Not AI's",
    description:
      "Turn your brain dumps into published, ranked content. Your voice, your style, every time.",
    type: "website",
    locale: "en_US",
    siteName: "PersonaPress",
    images: [
      {
        url: "https://personapress.io/images/PersonnaPress-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PersonaPress — AI content engine that publishes in your voice",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "PersonaPress — Publish in Your Voice, Not AI's",
    description: "AI content that sounds like you, published and ranked.",
    images: ["https://personapress.io/images/PersonnaPress-opengraph.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
};
```

**Note:** `metadataBase` is already set to `https://personapress.io`, so Next.js will prefix relative URLs automatically. However, for `openGraph.images` and `twitter.images`, use the full absolute URL to be safe across all crawlers.

---

### [x] Task 3: Update `frontend/app/robots.ts` (AC: #10)

```typescript
import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/dashboard", "/campaigns", "/clients", "/settings", "/account", "/onboarding"],
      },
      { userAgent: "GPTBot", allow: "/" },
      { userAgent: "PerplexityBot", allow: "/" },
      { userAgent: "Googlebot", allow: "/" },
      { userAgent: "anthropic-ai", allow: "/" },
      { userAgent: "ClaudeBot", allow: "/" },
      { userAgent: "CCBot", allow: "/" },
    ],
    sitemap: "https://personapress.io/sitemap.xml",
  };
}
```

---

### [x] Task 4: Update `frontend/app/sitemap.ts` (minor)

```typescript
import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://personapress.io",
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
```

---

### [x] Task 5: Rewrite `frontend/app/page.tsx` — Complete Landing Page (AC: #4–#12)

This is the primary task. The page is a Server Component (no `"use client"`). Any interactive accordion for the FAQ must be extracted to a `frontend/app/_components/FaqAccordion.tsx` Client Component file.

#### 5.1 — JSON-LD Schema Definitions

Define three JSON-LD objects at the top of the file (after imports):

**WebSite schema** (already exists, enhance with `potentialAction`):
```typescript
const schemaWebsite = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "PersonaPress",
  url: "https://personapress.io",
  description:
    "An autonomous content engine that turns brain dumps into SEO-ranked blog posts and social campaigns in your authentic voice.",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: "https://personapress.io/?q={search_term_string}",
    },
    "query-input": "required name=search_term_string",
  },
};
```

**SoftwareApplication schema**:
```typescript
const schemaSoftwareApp = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "PersonaPress",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: "https://personapress.io",
  description:
    "PersonaPress learns your writing voice from existing content, then turns raw brain dumps into SEO-structured blog posts, social campaigns, and featured images — published across WordPress, Webflow, X, and LinkedIn.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: "14-day free trial, no credit card required",
  },
  featureList: [
    "Brand voice extraction from existing content",
    "AI blog post generation (SEO-structured HTML)",
    "X (Twitter) and LinkedIn social post generation",
    "AI featured image generation via FLUX.1",
    "Human approval gate before any publish",
    "WordPress and Webflow publishing",
    "Scheduled publishing",
    "Multi-client agency management",
  ],
};
```

**Organization schema**:
```typescript
const schemaOrganization = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "PersonaPress",
  url: "https://personapress.io",
  logo: "https://personapress.io/images/PersonnaPress-logo.png",
  description:
    "PersonaPress is an AI content automation platform that learns your brand voice and publishes SEO-structured content across multiple platforms.",
};
```

**FAQPage schema** — define after the FAQ_ITEMS data array (Task 5.3 below):
```typescript
const schemaFaq = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ_ITEMS.map(({ question, answer }) => ({
    "@type": "Question",
    name: question,
    acceptedAnswer: {
      "@type": "Answer",
      text: answer,
    },
  })),
};
```

Inject all four schemas in the JSX using `<script type="application/ld+json">` blocks. Do not merge them into a single object; keep them as separate `<script>` tags for clarity.

#### 5.2 — Page Data Constants

```typescript
const WORKFLOW_STEPS = [
  // Keep existing 6 steps unchanged
];

const PLATFORMS = ["WordPress", "Webflow", "X (Twitter)", "LinkedIn"];

const PERSONAS = [
  {
    role: "Founders & Executives",
    description:
      "Turn domain expertise into consistent content without writing every word yourself. Set your voice once; the engine handles every post.",
  },
  {
    role: "Solo Coaches",
    description:
      "Publish in your distinctive voice across platforms without hiring a content team. Your audience gets you, not a generic AI.",
  },
  {
    role: "Content Agencies",
    description:
      "Manage multiple client voices from one dashboard. Each client gets a separate Brand Voice Profile; campaigns never cross-contaminate.",
  },
];

const FEATURES = [
  {
    heading: "Brand Voice Ingestion",
    body: "Paste a website URL or upload writing samples. PersonaPress extracts your tone, cadence, and banned jargon into a living profile that improves with every campaign.",
  },
  {
    heading: "Brain Dump to Campaign",
    body: "Drop a raw thought or bullet list. In under 90 seconds you get a full SEO blog post (800-1,500 words), an X post, a LinkedIn post, and a featured image.",
  },
  {
    heading: "Human Approval Gate",
    body: "Every draft lands in your inbox for review. Edit in a WYSIWYG editor, approve, reject, or regenerate. Nothing ships without your sign-off.",
  },
  {
    heading: "One-Click Publishing",
    body: "Publish to WordPress, Webflow, X, and LinkedIn simultaneously. Schedule posts to go live at peak engagement times without logging into four separate platforms.",
  },
];
```

#### 5.3 — FAQ Data

```typescript
const FAQ_ITEMS = [
  {
    question: "What is PersonaPress and how does it work?",
    answer:
      "PersonaPress is an AI content engine that learns your exact writing voice, then turns raw ideas into SEO-structured blog posts and social campaigns. You paste a website URL or upload past writing samples, PersonaPress extracts your tone and style into a Brand Voice Profile, and then any time you submit a brain dump it generates a complete campaign in under 90 seconds.",
  },
  {
    question: "How does PersonaPress learn my writing voice?",
    answer:
      "PersonaPress scrapes your website for blog posts and public content, then runs it through a voice extraction model (Gemini 2.5 Flash) that identifies your tone, sentence cadence, and words you never use (banned jargon). The resulting Brand Voice Profile is stored on your account and applied to every campaign. You can review and edit every field before finalizing.",
  },
  {
    question: "What publishing platforms does PersonaPress support?",
    answer:
      "PersonaPress currently supports WordPress (self-hosted and WordPress.com), Webflow, X (Twitter), and LinkedIn. Meta / Instagram / Threads are architected and will ship in Phase 2. Each platform integration is independent; a failure on one platform does not block publishing to the others.",
  },
  {
    question: "How long does content generation take?",
    answer:
      "A typical campaign (blog post + X post + LinkedIn post + featured image) generates in under 90 seconds. The 95th-percentile upper bound is 120 seconds. You see real-time progress via a typewriter animation while the pipeline runs.",
  },
  {
    question: "Does PersonaPress publish content automatically?",
    answer:
      "No. Every draft goes through a human approval gate before anything is published. You review the full campaign, edit it in a WYSIWYG editor if needed, then explicitly approve or reject. Only after your approval can you trigger immediate or scheduled publishing.",
  },
  {
    question: "What is a Brain Dump?",
    answer:
      "A Brain Dump is a free-form text input where you write your raw idea, voice note transcript, or bullet list. It can be between 20 and 10,000 characters. No structure is required. PersonaPress takes that rough input and transforms it into a polished, on-brand campaign.",
  },
  {
    question: "How is PersonaPress different from ChatGPT or other AI writing tools?",
    answer:
      "Generic AI tools produce generic-sounding content because they have no knowledge of your voice. PersonaPress is trained on your specific content before generating anything. It also automates the full pipeline from idea to live post, including featured image generation and multi-platform publishing, which no general-purpose AI tool does.",
  },
  {
    question: "Can I edit the AI-generated content before publishing?",
    answer:
      "Yes. The approval gate includes a full WYSIWYG editor for the blog post and plain-text editors with live character counters for X and LinkedIn posts. You can edit as much or as little as you want before approving.",
  },
  {
    question: "What does the free trial include?",
    answer:
      "The 14-day free trial includes full access to all features: brand voice ingestion, campaign generation, image generation, and publishing to all connected platforms. No credit card is required to start. After 14 days you can subscribe to continue or your account enters a read-only state for 30 days.",
  },
  {
    question: "Is PersonaPress suitable for agencies managing multiple clients?",
    answer:
      "Yes. PersonaPress has first-class multi-client support. Each client has a separate Brand Voice Profile, campaign history, and platform connections. You switch between clients from the dashboard. Campaigns never cross-contaminate between clients.",
  },
  {
    question: "Can I publish to WordPress.com (not just self-hosted WordPress)?",
    answer:
      "Yes. PersonaPress supports both self-hosted WordPress (via Application Password) and WordPress.com (via OAuth 2.0). The WordPress.com OAuth flow handles authentication without requiring you to generate an application password.",
  },
  {
    question: "How are featured images generated?",
    answer:
      "Featured images are generated using FLUX.1 [pro] via the Replicate API. The image is based on your blog post title and content summary, sized at 1200x630 pixels (standard OG/social dimensions), and stored in Supabase Storage. You can request up to 3 regenerations per campaign with an optional prompt override.",
  },
];
```

#### 5.4 — Page Structure (JSX)

The full page structure must follow this section order. Each section should have the Paper Style layout pattern: `max-w-6xl mx-auto px-6 py-20` container, section `<header>` with a mono overline + display heading.

```tsx
<div className="min-h-screen bg-paper">
  {/* JSON-LD scripts — 4 separate blocks */}
  <script type="application/ld+json">{JSON.stringify(schemaWebsite)}</script>
  <script type="application/ld+json">{JSON.stringify(schemaSoftwareApp)}</script>
  <script type="application/ld+json">{JSON.stringify(schemaOrganization)}</script>
  <script type="application/ld+json">{JSON.stringify(schemaFaq)}</script>

  {/* Navigation — sticky, border-bottom */}
  <header> ... </header>

  <main>
    {/* 1. Hero — existing, add "14-day free trial" sub-note below CTA buttons */}
    <section> ... </section>
    <div className="border-t border-border" />

    {/* 2. Problem Statement — NEW */}
    <section id="problem"> ... </section>
    <div className="border-t border-border" />

    {/* 3. Who It's For — NEW */}
    <section id="for-who"> ... </section>
    <div className="border-t border-border" />

    {/* 4. Workflow — existing 6-step grid */}
    <section id="workflow"> ... </section>
    <div className="border-t border-border" />

    {/* 5. Features Deep-Dive — NEW */}
    <section id="features"> ... </section>
    <div className="border-t border-border" />

    {/* 6. Platforms — existing */}
    <section id="platforms"> ... </section>
    <div className="border-t border-border" />

    {/* 7. Trial CTA — enhance existing CTA with trial language */}
    <section id="trial"> ... </section>
    <div className="border-t border-border" />

    {/* 8. FAQ — NEW */}
    <section id="faq"> ... </section>
  </main>

  {/* Footer — enhanced with nav links */}
  <footer> ... </footer>
</div>
```

#### 5.5 — Navigation Update

Add `#faq` link to the nav:
```tsx
<nav className="flex items-center gap-8">
  <a href="#workflow" ...>How it works</a>
  <a href="#platforms" ...>Platforms</a>
  <a href="#faq" ...>FAQ</a>
  <Link href="/dashboard" ...>Start Free Trial ...</Link>
</nav>
```

Change CTA button text from "Open App" to "Start Free Trial".

#### 5.6 — Hero Update

Below the existing CTA button group, add a trust line:
```tsx
<p className="font-mono text-xs text-graphite mt-4">
  14-day free trial. No credit card required.
</p>
```

#### 5.7 — Problem Statement Section (NEW)

Mono overline: "The Problem"
H2: "AI tools write content that sounds like every other AI"

Three pain-point cards (1x3 grid, border layout like workflow cards):
- "6 hours per post" — writing takes too long even with generic AI
- "Sounds like everyone else" — no brand voice = no differentiation
- "4 platforms, 4 logins" — publishing friction kills consistency

Use the same `grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border` pattern as the workflow cards.

#### 5.8 — Who It's For Section (NEW)

Mono overline: "Built For"
H2: "Content that sounds like you, at scale"

Three persona cards using `PERSONAS` array. Each card:
```tsx
<article key={role} className="bg-paper p-8 border-b border-border last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
  <h3 className="font-display text-xl font-bold text-ink mb-3">{role}</h3>
  <p className="text-sm text-graphite leading-relaxed">{description}</p>
</article>
```

#### 5.9 — Features Section (NEW)

Mono overline: "Features"
H2: "Everything from idea to live post"

Two-column grid (`grid-cols-1 md:grid-cols-2`) of feature cards using `FEATURES` array. Each card has a bold heading and description. Use the border-grid pattern.

#### 5.10 — Trial CTA Section (REPLACE existing CTA)

```tsx
<section className="max-w-6xl mx-auto px-6 py-20">
  <div className="border border-ink p-12 shadow-brutal">
    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
      Get Started
    </p>
    <h2 className="font-display text-4xl font-bold text-ink mb-4 text-balance">
      14 days free. Your voice, ranked and published.
    </h2>
    <p className="text-graphite mb-2 max-w-lg text-pretty">
      Set up your brand voice profile in under 10 minutes. Your first campaign draft is ready in 90 seconds.
    </p>
    <p className="font-mono text-xs text-graphite mb-8">
      No credit card required. Cancel anytime.
    </p>
    <Link
      href="/dashboard"
      className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 hover:bg-graphite transition-colors"
    >
      Start Your Free Trial
      <ArrowRight className="size-4" aria-hidden="true" />
    </Link>
  </div>
</section>
```

#### 5.11 — FAQ Section (NEW)

Create a Client Component `frontend/app/_components/FaqAccordion.tsx` for interactive open/close:

```tsx
"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

interface FaqItem {
  question: string;
  answer: string;
}

export function FaqAccordion({ items }: { items: FaqItem[] }) {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <div className="divide-y divide-border border border-border">
      {items.map(({ question, answer }, i) => (
        <div key={i}>
          <button
            onClick={() => setOpen(open === i ? null : i)}
            className="w-full flex items-center justify-between px-8 py-6 text-left hover:bg-highlight transition-colors group"
            aria-expanded={open === i}
          >
            <h3 className="font-display text-lg font-bold text-ink text-balance pr-4">
              {question}
            </h3>
            <ChevronDown
              className={`size-5 text-graphite shrink-0 transition-transform ${
                open === i ? "rotate-180" : ""
              }`}
              aria-hidden="true"
            />
          </button>
          {open === i && (
            <div className="px-8 pb-6">
              <p className="text-graphite leading-relaxed text-pretty">
                {answer}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

In `page.tsx`, import and render this component:

```tsx
import { FaqAccordion } from "./_components/FaqAccordion";

// In JSX:
<section id="faq" className="max-w-6xl mx-auto px-6 py-20">
  <header className="mb-14">
    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
      FAQ
    </p>
    <h2 className="font-display text-4xl font-bold text-ink text-balance">
      Frequently asked questions
    </h2>
  </header>
  <FaqAccordion items={FAQ_ITEMS} />
</section>
```

#### 5.12 — Header and Footer Logo

Replace text wordmarks with `<Image>`:

```tsx
import Image from "next/image";

// In <header>:
<Image
  src="/images/PersonnaPress-logo.png"
  alt="PersonnaPress"
  width={160}
  height={32}
  priority
/>

// In <footer>:
<Image
  src="/images/PersonnaPress-logo.png"
  alt="PersonnaPress"
  width={140}
  height={28}
/>
```

Measure the actual pixel dimensions of the PNG file and set `width` / `height` accordingly. Do not guess dimensions; check the file.

#### 5.13 — Enhanced Footer

```tsx
<footer className="border-t border-border">
  <div className="max-w-6xl mx-auto px-6 py-8">
    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
      <Image src="/images/PersonnaPress-logo.png" alt="PersonnaPress" width={140} height={28} />
      <nav className="flex flex-wrap gap-6">
        <a href="#workflow" className="font-mono text-xs text-graphite hover:text-ink transition-colors">How it works</a>
        <a href="#platforms" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Platforms</a>
        <a href="#faq" className="font-mono text-xs text-graphite hover:text-ink transition-colors">FAQ</a>
        <Link href="/dashboard" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Sign up</Link>
        <Link href="/login" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Log in</Link>
      </nav>
    </div>
    <div className="border-t border-border mt-6 pt-6">
      <p className="font-mono text-xs text-graphite">
        &copy; {new Date().getFullYear()} PersonnaPress. All rights reserved.
      </p>
    </div>
  </div>
</footer>
```

---

## File Summary

| File | Action | Notes |
|---|---|---|
| `frontend/public/favicon/favicon.ico` | MOVE → `frontend/app/favicon.ico` | Auto-served by Next.js |
| `frontend/public/favicon/apple-touch-icon.png` | MOVE → `frontend/app/apple-icon.png` | Auto-served by Next.js |
| `frontend/public/favicon/favicon.svg` | MOVE → `frontend/app/icon.svg` | Auto-served by Next.js |
| `frontend/public/favicon/favicon-96x96.png` | MOVE → `frontend/app/icon.png` | Auto-served by Next.js |
| `frontend/public/favicon/web-app-manifest-192x192.png` | MOVE → `frontend/public/web-app-manifest-192x192.png` | Fixes broken webmanifest links |
| `frontend/public/favicon/web-app-manifest-512x512.png` | MOVE → `frontend/public/web-app-manifest-512x512.png` | Fixes broken webmanifest links |
| `frontend/public/favicon/site.webmanifest` | MOVE → `frontend/public/site.webmanifest` | Served at `/site.webmanifest` |
| `frontend/public/favicon/` | DELETE | Empty after all moves |
| `frontend/public/images/` | KEEP | Logo and OG image referenced from here |
| `frontend/app/layout.tsx` | UPDATE | Add OG image, icons, manifest to metadata |
| `frontend/app/page.tsx` | MAJOR UPDATE | New sections, FAQ, 4 JSON-LD schemas |
| `frontend/app/_components/FaqAccordion.tsx` | NEW | Client Component for interactive FAQ |
| `frontend/app/robots.ts` | UPDATE | Add ClaudeBot, CCBot |
| `frontend/app/sitemap.ts` | UPDATE | Change frequency to weekly |

---

## Architecture & Guardrails

**Stack:**
- Next.js 16 App Router (Vercel), TypeScript
- Tailwind CSS v4 via `@import "tailwindcss"` in `globals.css` — class generation is automatic, no `tailwind.config.js`
- `lucide-react` for all icons
- `next/image` for all raster images

**Paper Style tokens** (from `globals.css @theme`):
- `bg-paper` (#F9F9F6), `text-ink` (#111111), `text-graphite` (#555555)
- `border-border` (#E5E5E5), `bg-highlight` (#FFF1B8)
- `font-display` (Playfair Display), `font-body` (Inter), `font-mono` (JetBrains Mono)
- `shadow-brutal` — existing utility class used in existing landing page CTAs

**Do NOT:**
- Add `"use client"` to `page.tsx` (keep it a Server Component)
- Use `<img>` tags — use `<Image>` from `next/image`
- Add any arbitrary Tailwind colors outside the `@theme` tokens
- Use emoji anywhere
- Add `console.log` or debug code
- Import icons from anywhere except `lucide-react`
- Use em-dashes (--) in JSX text content

**`next/image` for the logo — check dimensions first:**
```bash
# Check PNG dimensions before hardcoding width/height:
# Right-click PersonnaPress-logo.png → Properties → Details tab (Windows)
# Or use: python3 -c "from PIL import Image; img=Image.open('frontend/public/images/PersonnaPress-logo.png'); print(img.size)"
```

**SEO / AEO / GEO checklist before marking done:**
- [x] All 4 `<script type="application/ld+json">` blocks render in page source
- [x] `<meta name="description">` present
- [x] `<meta property="og:image">` present with absolute URL
- [x] `<link rel="manifest">` present
- [x] `<link rel="icon">` and `<link rel="apple-touch-icon">` present (auto by Next.js after Task 1)
- [x] FAQ section visible on page with all 12 items
- [x] "14-day free trial" text appears at least once on page
- [x] Logo image renders in header and footer (no broken image)
- [x] No emojis visible anywhere on page

---

## Dev Notes

- The current `page.tsx` exports `metadata` with a `canonical` that uses a single `alternates.canonical` key. The layout already has `metadataBase`. Removing the page-level `canonical` is fine since layout-level `metadataBase` handles it; or keep the `alternates` if you want explicit per-page canonical control.
- The `FaqAccordion` must be in `frontend/app/_components/` (note the underscore prefix which prevents Next.js from treating it as a route segment).
- `new Date().getFullYear()` in the footer copyright is a valid server-side call in a Server Component; no hydration issues.
- The `site.webmanifest` references `PersonnaPress` (double n) as the `name` and `short_name` — keep that consistent with the logo file name. The domain `personapress.io` (single n) is separate from the brand name.
- When checking the logo image dimensions on Windows with PowerShell: `Add-Type -AssemblyName System.Drawing; $img = [System.Drawing.Image]::FromFile('.\frontend\public\images\PersonnaPress-logo.png'); Write-Output "$($img.Width)x$($img.Height)"; $img.Dispose()`

---

## Dev Agent Record

### Implementation Notes

- Logo PNG is 128x128px (verified via PowerShell System.Drawing). Used `className="h-8 w-auto"` in header and `className="h-7 w-auto"` in footer to control display size while keeping intrinsic dimensions accurate per `next/image` requirements.
- `page.tsx` remains a pure Server Component (no `"use client"`). Interactive FAQ accordion extracted to `frontend/app/_components/FaqAccordion.tsx` as a Client Component per RSC rule.
- 4 separate JSON-LD `<script>` blocks injected: WebSite (with potentialAction), SoftwareApplication, Organization, FAQPage.
- Persona role strings use `dangerouslySetInnerHTML` only for HTML entity `&amp;` in "Founders &amp; Executives" — this is safe since the data is a static constant, not user input.
- Pre-existing TypeScript errors in `components/campaigns/BlogEditor.tsx` and test files are unrelated to story 8-1; they existed in the codebase before this story began and are not in any file modified here.
- No em-dashes used anywhere. No emojis used anywhere. All icons from `lucide-react` only.

### Completion Notes

All 12 ACs satisfied and all 5 tasks completed:
- Task 1: 7 favicon files moved to correct Next.js App Router locations; `frontend/public/favicon/` directory deleted
- Task 2: `layout.tsx` metadata updated with OG images (absolute URL), Twitter card image, icons, manifest, expanded keywords, googleBot robots config
- Task 3: `robots.ts` updated with `ClaudeBot` and `CCBot` rules plus `/account` and `/onboarding` to disallow list
- Task 4: `sitemap.ts` updated to `changeFrequency: "weekly"`
- Task 5: `page.tsx` fully rewritten with 4 JSON-LD schemas, Problem section, Who It's For section, Features section, enhanced Trial CTA with "14-day free trial" language, FAQ section (12 items), logo images in header/footer, FAQ nav link, "Start Free Trial" CTA text; `FaqAccordion.tsx` created as Client Component

---

## File List

- `frontend/app/favicon.ico` (moved from `frontend/public/favicon/favicon.ico`)
- `frontend/app/apple-icon.png` (moved from `frontend/public/favicon/apple-touch-icon.png`)
- `frontend/app/icon.svg` (moved from `frontend/public/favicon/favicon.svg`)
- `frontend/app/icon.png` (moved from `frontend/public/favicon/favicon-96x96.png`)
- `frontend/public/web-app-manifest-192x192.png` (moved from `frontend/public/favicon/`)
- `frontend/public/web-app-manifest-512x512.png` (moved from `frontend/public/favicon/`)
- `frontend/public/site.webmanifest` (moved from `frontend/public/favicon/`)
- `frontend/public/favicon/` (DELETED)
- `frontend/app/layout.tsx` (modified)
- `frontend/app/page.tsx` (modified)
- `frontend/app/_components/FaqAccordion.tsx` (new)
- `frontend/app/robots.ts` (modified)
- `frontend/app/sitemap.ts` (modified)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)

---

### Review Findings

- [x] [Review][Patch] `<h3>` inside `<button>` in FaqAccordion — invalid HTML per spec, breaks screen readers [`frontend/app/_components/FaqAccordion.tsx:23`] — fixed: replaced `<h3>` with `<span>` styled as heading
- [x] [Review][Patch] `&mdash;` HTML entity in `schemaSoftwareApp.description` — literal in JSON-LD output, garbles structured data [`frontend/app/page.tsx:61`] — fixed: rephrased to remove dash
- [x] [Review][Patch] `&mdash;` in twitter.title and OG image alt in layout.tsx — renders as literal text in meta tags [`frontend/app/layout.tsx:66,72`] — fixed: replaced with hyphen
- [x] [Review][Patch] AC7 violation: Organization schema logo points to logo.png instead of OG image URL [`frontend/app/page.tsx:85`] — fixed: changed to `PersonnaPress-opengraph.png`
- [x] [Review][Patch] `dangerouslySetInnerHTML` for PERSONAS role strings — unnecessary for static `&` character [`frontend/app/page.tsx:419`] — fixed: plain string + `{role}` rendering
- [x] [Review][Patch] SearchAction potentialAction in schemaWebsite references non-existent search endpoint [`frontend/app/page.tsx:43-50`] — fixed: removed potentialAction block
- [x] [Review][Patch] FAQ accordion `key={i}` — array index key, use question string [`frontend/app/_components/FaqAccordion.tsx:17`] — fixed: key by question, state by question
- [x] [Review][Patch] aria-controls missing on accordion button — incomplete ARIA pattern [`frontend/app/_components/FaqAccordion.tsx:21`] — fixed: added panelId + aria-controls
- [x] [Review][Patch] site.webmanifest all icons `purpose: "maskable"` only — missing `any` variants [`frontend/public/site.webmanifest`] — fixed: added `any` purpose entries for both sizes
- [x] [Review][Defer] `new Date().getFullYear()` in footer evaluates at build time in static RSC [`frontend/app/page.tsx`] — deferred, pre-existing landing page pattern

## Change Log

- 2026-07-06: Implemented story 8-1 — Production-Ready Landing Page with SEO/AEO/GEO. Migrated all favicon assets to Next.js App Router locations, updated layout.tsx metadata with OG/Twitter images and manifest, updated robots.ts with AI bot rules, updated sitemap.ts to weekly frequency, rewrote page.tsx with 4 JSON-LD schemas and 4 new sections (Problem, Who It's For, Features, FAQ with 12 items), created FaqAccordion.tsx Client Component.
- 2026-07-06: Code review — applied 9 patches: h3-in-button fix, &mdash; entity fixes in JSON-LD and metadata, AC7 Organization logo URL correction, dangerouslySetInnerHTML removal, SearchAction removed, FAQ accordion key+aria fixes, webmanifest any-purpose icons added.
