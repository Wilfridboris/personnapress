---
title: 'P2.5 Persona / use-case landing pages (SaaS founders, coaches, agencies)'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '59af5d67329ffb4194faec4a48225e69a50a1ef9'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** PersonnaPress has no persona/use-case landing pages for its three ICP segments (SaaS founders, coaches, agencies). This leaves long-tail, high-intent SEO demand uncaptured and gives answer engines (ChatGPT, Perplexity, Google AI Overviews) no persona-specific, quotable answers to cite. Keyword research confirms winnable LOW-competition demand: "content marketing for saas" (590/mo), "content marketing for startups" (210/mo), "white label content creation/blog writing" (tool-intent), and a thinner coach cluster best served answer-first.

**Approach:** Ship a three-page persona cluster reusing the P1.4 comparison pattern: one shared Server Component `PersonaPage` driven by a `personas.data.ts` data file, consumed by three thin static routes. Each page is keyword-targeted, answer-first (40-60 word direct answer in the hero for AEO extraction), and carries SoftwareApplication + FAQPage + BreadcrumbList JSON-LD. Wire all three into the sitemap and the public footer so they are crawlable, not orphaned.

## Boundaries & Constraints

**Always:**
- Server Components only (no `"use client"` in routes); `export const dynamic = "force-static"`.
- Base URL fallback exactly `(process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "")` (www canonical, per P0).
- H1 and title follow the house `[Feature] + [Action] + [Platform]` naming rule and embed the page's primary keyword; brand supplied by title template, no double-branding.
- No em-dash and no double-dash (`--`) in any copy; restructure sentences naturally (single hyphens in compounds like "white-label" are fine).
- Reuse Paper Style tokens (`ink`, `graphite`, `paper`, `border`, `highlight`, `highlighter`, `font-display`, `font-mono`), `FaqAccordion`, lucide-react icons. No new design primitives, no hardcoded hex.
- CTA links to `/dashboard` with the standard "14-day free trial. No credit card required." microcopy.
- Escape JSON-LD with `.replace(/</g, "\\u003c")` as existing pages do.

**Ask First:**
- Changing the three approved slugs `/ai-blog-writer-for-saas-founders`, `/ai-content-for-coaches`, `/white-label-content-for-agencies` (keyword-rich set chosen 2026-09-18; changing after launch needs 301s).
- Adding links from the home page or other existing pages beyond the footer.

**Never:**
- Do not touch the P2.6 glossary, P2.7 llms.txt/crawler, or P2.8 breadcrumb-everywhere work (deferred).
- Do not modify `ComparisonPage.tsx` / `comparisons.data.ts` (copy the pattern, do not couple to it).
- No backend, DB, or API changes. No fabricated stats or testimonials in copy.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Crawler / AI bot fetches a persona route | GET `/ai-blog-writer-for-saas-founders` | 200, statically rendered, single H1, answer-first intro, and three JSON-LD blocks (SoftwareApplication, FAQPage, BreadcrumbList) in source | N/A |
| Canonical resolution | `NEXT_PUBLIC_APP_URL` set in prod | `alternates.canonical`, `og:url`, and sitemap entries all use that value with no trailing slash | Falls back to `https://www.personnapress.com` when env unset |
| Sitemap request | GET `/sitemap.xml` | Includes all three persona URLs at priority 0.8, `changeFrequency: "monthly"` | N/A |
| Footer render on any marketing page | Any public page | New "Use cases" group lists the three persona links | N/A |

</frozen-after-approval>

## Code Map

- `frontend/components/marketing/ComparisonPage.tsx` — READ-ONLY reference pattern: `<main className="-mt-8 -mx-4">`, hero (`section max-w-6xl mx-auto px-6 pt-12 md:pt-24`), `ICON_MAP` (RefreshCw/FileText/Share2/Search), CTA to `/dashboard`. Mirror its structure; do not import from it.
- `frontend/components/marketing/comparisons.data.ts` — READ-ONLY reference for data-file shape (`FaqItem`, `Differentiator { iconName, title, description }`, `metadata { title, description, canonicalPath }`, `relatedLinks`).
- `frontend/app/(public)/jasper-alternatives/page.tsx` — READ-ONLY thin-route template: `dynamic = "force-static"`, `APP_URL` const, `generateMetadata()` with `title: { absolute }`, `alternates.canonical`, `openGraph`, `twitter`; JSON-LD scripts before the component.
- `frontend/app/(public)/best-ai-blog-writers/page.tsx` — READ-ONLY reference for a richer bespoke section layout and its 3 JSON-LD blocks.
- `frontend/app/_components/FaqAccordion.tsx` — REUSE: `export function FaqAccordion({ items }: { items: {question,answer}[] })` (client component; safe to render inside RSC).
- `frontend/app/sitemap.ts` — EDIT: `BASE_URL` const at top; append three entries in the marketing block.
- `frontend/components/marketing/PublicFooter.tsx` — EDIT: add a "Use cases" nav group with three `<Link>`s (mirror the "Resources" group markup).
- `frontend/app/layout.tsx` — READ-ONLY: title template `%s | PersonnaPress`, `metadataBase`.
- `frontend/package.json` — scripts: `build`, `lint`, `test` (vitest).

## Tasks & Acceptance

**Execution:**
- [x] `frontend/components/marketing/personas.data.ts` — CREATE: `export interface PersonaPageData { slug; persona; primaryKeyword; metadata{title,description,canonicalPath}; h1; heroAnswer; pains: {title,description}[]; solutions: {iconName,title,description}[]; faqItems: {question,answer}[]; relatedLinks: {href,label}[] }`; `export const PERSONAS: Record<"saas"|"coaches"|"agencies", PersonaPageData>` with real keyword-targeted copy per Design Notes; `export function buildPersonaJsonLd(data, appUrl)` returning `{ softwareApp, faq, breadcrumb }`. Rationale: single source of content keeps routes thin and consistent.
- [x] `frontend/components/marketing/PersonaPage.tsx` — CREATE: `export function PersonaPage({ data }: { data: PersonaPageData })` Server Component; sections: hero (H1 = `data.h1`, answer-first `data.heroAnswer`, CTA to `/dashboard`), Pains (`data.pains`), How PersonnaPress helps (`data.solutions` via local `ICON_MAP`), FAQ (`<FaqAccordion items={data.faqItems} />`), CTA banner, related-links row (`data.relatedLinks`). Reuse Paper Style tokens and semantic `main/section/article/h1/h2`. Rationale: one component renders all three pages.
- [x] `frontend/app/(public)/ai-blog-writer-for-saas-founders/page.tsx` — CREATE thin route consuming `PERSONAS.saas`; `generateMetadata()` + three JSON-LD scripts from `buildPersonaJsonLd`. Primary keyword: "content marketing for saas" / "ai blog writer for saas founders".
- [x] `frontend/app/(public)/ai-content-for-coaches/page.tsx` — CREATE thin route consuming `PERSONAS.coaches`. Primary keyword: "content marketing for coaches" (answer-first, AEO-led).
- [x] `frontend/app/(public)/white-label-content-for-agencies/page.tsx` — CREATE thin route consuming `PERSONAS.agencies`. Primary keyword: "white label content creation" / "white label blog writing" (tool intent, not the broad head term).
- [x] `frontend/app/sitemap.ts` — EDIT: append the three routes (priority 0.8, `changeFrequency: "monthly"`).
- [x] `frontend/components/marketing/PublicFooter.tsx` — EDIT: add "Use cases" nav group linking the three routes.

**Acceptance Criteria:**
- Given a crawler fetches any of the three routes, when the page renders, then the source contains exactly one `<h1>` matching the `[Feature]+[Action]+[Platform]` rule with the primary keyword, an answer-first intro of 40-60 words, and valid SoftwareApplication, FAQPage, and BreadcrumbList JSON-LD.
- Given `NEXT_PUBLIC_APP_URL` is set, when metadata and sitemap render, then canonical, `og:url`, and sitemap URLs all use it (www, no trailing slash); when unset, they fall back to `https://www.personnapress.com`.
- Given the sitemap is requested, when it renders, then all three persona URLs appear at priority 0.8.
- Given any public marketing page renders, when the footer shows, then a "Use cases" group links all three persona pages.
- Given the copy is reviewed, when scanned for `—` and `--`, then none are present.

## Design Notes

**Per-persona keyword + H1 targeting (from DataForSEO, US/English, all LOW competition):**

- SaaS founders (`/ai-blog-writer-for-saas-founders`) — primary "content marketing for saas" (590), secondary "content marketing for startups" (210), "saas content writing" (90). Proposed H1: "AI Blog Writer for SaaS Founders That Ranks in Your Voice." Angle: ship product content without hiring; brand voice holds in long-form; blog-to-social in one loop.
- Coaches (`/ai-content-for-coaches`) — primary "content marketing for coaches" (20); thin volume, so lead answer-first for AEO. Proposed H1: "AI Content Marketing for Coaches, in Your Own Voice." Angle: sound like you, not generic AI; consistent presence without ghostwriters.
- Agencies (`/white-label-content-for-agencies`) — primary "white label content creation" (30) / "white label blog writing" (20); intentionally avoid the mixed-intent head term "content marketing for agencies" (3,600 but mostly hire-an-agency intent) as the primary target. Proposed H1: "White-Label AI Blog Writing for Agencies, in Every Client's Voice." Angle: per-client brand voice at scale, publish under client accounts.

**Answer-first (AEO/GEO) rule:** the hero intro must be a self-contained 40-60 word direct answer to the page's implied question (e.g. "The best AI blog writer for SaaS founders is one that..."), because answer engines preferentially extract and cite clean, standalone definitions. Depth follows below the fold.

**JSON-LD shape:** `softwareApp` = SoftwareApplication (name PersonnaPress, applicationCategory BusinessApplication, offers/free-trial), `faq` = FAQPage from `faqItems`, `breadcrumb` = BreadcrumbList (Home -> page). Match the escaping and injection used in `jasper-alternatives/page.tsx`.

## Verification

**Commands:**
- `cd frontend && npm run lint` — expected: no errors on new/edited files.
- `cd frontend && npm run build` — expected: build succeeds; the three routes prerender as static.

**Manual checks:**
- Visit each route; confirm a single H1 with the primary keyword, a 40-60 word answer-first intro, working `/dashboard` CTA, and no `—`/`--` in copy.
- View source on each route; confirm three JSON-LD blocks and validate with Google Rich Results / Schema.org validator.
- Load `/sitemap.xml`; confirm the three URLs at priority 0.8. Confirm the footer "Use cases" group links all three.

## Suggested Review Order

**Data layer — single source of truth for all copy and JSON-LD**

- Interface: five content arrays + three heading fields drive the whole component
  [`personas.data.ts:17`](../../frontend/components/marketing/personas.data.ts#L17)

- PERSONAS record: real keyword-targeted copy for all three ICP segments
  [`personas.data.ts:34`](../../frontend/components/marketing/personas.data.ts#L34)

- buildPersonaJsonLd: SoftwareApplication + FAQPage + BreadcrumbList from one call
  [`personas.data.ts:291`](../../frontend/components/marketing/personas.data.ts#L291)

**Shared Server Component — one component renders all three pages**

- PersonaPage entry point: no "use client", Paper Style tokens throughout
  [`PersonaPage.tsx:15`](../../frontend/components/marketing/PersonaPage.tsx#L15)

- Hero: H1 from data.h1, answer-first AEO paragraph, CTA to /dashboard
  [`PersonaPage.tsx:24`](../../frontend/components/marketing/PersonaPage.tsx#L24)

- Pains section: data-driven heading (painsHeading) + 3-column grid
  [`PersonaPage.tsx:53`](../../frontend/components/marketing/PersonaPage.tsx#L53)

- Solutions section: ICON_MAP + data-driven heading (solutionsHeading)
  [`PersonaPage.tsx:77`](../../frontend/components/marketing/PersonaPage.tsx#L77)

**Thin static routes — identical pattern, representative example**

- force-static + APP_URL env fallback: canonical baked at build time
  [`ai-blog-writer-for-saas-founders/page.tsx:5`](../../frontend/app/(public)/ai-blog-writer-for-saas-founders/page.tsx#L5)

- generateMetadata: absolute title, canonical, OG, Twitter with images
  [`ai-blog-writer-for-saas-founders/page.tsx:11`](../../frontend/app/(public)/ai-blog-writer-for-saas-founders/page.tsx#L11)

- Three JSON-LD scripts with </script>-safe escaping before PersonaPage
  [`ai-blog-writer-for-saas-founders/page.tsx:38`](../../frontend/app/(public)/ai-blog-writer-for-saas-founders/page.tsx#L38)

- Coaches route (same pattern, different PERSONAS key)
  [`ai-content-for-coaches/page.tsx:1`](../../frontend/app/(public)/ai-content-for-coaches/page.tsx#L1)

- Agencies route (same pattern, different PERSONAS key)
  [`white-label-content-for-agencies/page.tsx:1`](../../frontend/app/(public)/white-label-content-for-agencies/page.tsx#L1)

**Crawlability — sitemap + footer**

- Three persona entries at priority 0.8, changeFrequency monthly
  [`sitemap.ts:89`](../../frontend/app/sitemap.ts#L89)

- "Use cases" nav group added between Resources and Account columns
  [`PublicFooter.tsx:64`](../../frontend/components/marketing/PublicFooter.tsx#L64)
