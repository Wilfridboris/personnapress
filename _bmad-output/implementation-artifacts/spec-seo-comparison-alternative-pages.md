---
title: 'SEO Comparison & Alternative Pages Cluster (P1.4)'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'ea8cc1ee6a2465abbc53dfc336bfe4b757ad8943'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** PersonnaPress has no bottom-of-funnel comparison content, so high-intent searches like "jasper alternatives" (140/mo, low competition), "copy.ai alternatives" (110/mo), and "writesonic alternatives" (110/mo) — plus the head term "best ai writing tools/blog writers" (880/mo) — are captured by competitors and cited by answer engines instead of us. This is the audit's highest-ROI content gap (SEO + AEO + GEO at once).

**Approach:** Ship a 4-page hub-and-spoke cluster built from ONE reusable, data-driven comparison-page system: three "[competitor] alternatives" spoke pages (`/jasper-alternatives`, `/copy-ai-alternatives`, `/writesonic-alternatives`) and one hub (`/best-ai-blog-writers`) that ranks the tools and links down to the spokes. Each page is answer-first (AEO), carries a fair comparison table plus an honest "where the competitor wins" section (helpful-content + legal safety), and emits `SoftwareApplication` + `FAQPage` + `BreadcrumbList` JSON-LD. Match the existing brutalist Paper Style exactly; reuse `PublicHeader`/`PublicFooter`, the `/headless-blog-api` comparison table, and `FaqAccordion`.

## Boundaries & Constraints

**Always:**
- Match Paper Style exactly: 1px Ink (`#111`) borders, `rounded-none`, `shadow-brutal` 4px offset, Playfair (`font-display`) headings, Inter (`font-body`), JetBrains Mono (`font-mono`) micro-labels, Paper (`#F9F9F6`) bg, Highlighter (`#FFF1B8`) CTA. Icons from `lucide-react` only. No emojis.
- Copy rules are hard: no em-dashes and no double-dashes (`--`) in any user-facing copy; no AI-trope words ("elevate", "delve", "unlock", "seamless", "empower"); E-E-A-T concrete claims only.
- Differentiate ONLY on the autonomous idea→SEO-structured→auto-publish-to-blog-and-social loop and long-form voice fidelity. All three competitors HAVE a brand-voice feature; never claim "only we do brand voice."
- Comparison tables must be fair: include at least one row each competitor wins. Every competitor factual claim carries a visible "as of September 2026, check current pricing/features" disclaimer and links to the competitor's own page as source.
- Keyword-first H1/title, brand last (`... | PersonnaPress`), following the `[Feature] + [Action] + [Platform]` naming rule.
- Pages are static server components (`force-static`); zero client-side data fetching; the only client island is the existing `FaqAccordion`. Any year renders via the existing `CopyrightYear` pattern (do not call `new Date()` in a force-static page body).
- FAQ accordion visible text must be identical to the `FAQPage` JSON-LD text (both read from the same data entry).
- JSON-LD injected via `<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(obj).replace(/</g, "\\u003c") }} />` (the current live pattern in `pricing`/`about`).

**Ask First:**
- Adding these pages to `PublicHeader` primary nav (spokes likely footer-only, mirroring `headless-blog-api`; hub could be nav-worthy). Default: footer links only unless approved.
- Any competitor dollar figure beyond the verified entry price, or any claim not backed by the competitor's own page.

**Never:**
- State unverified figures: Jasper "Business" dollar amounts or "Creator $39" as current, Copy.ai "Pro $49", Writesonic permanent free tier, or any competitor headless-publishing API beyond Writesonic's WordPress plugin.
- Ship the branded "PersonnaPress vs X" head-to-head pages (deferred — ~0 organic demand; separate Phase 2).
- Glassmorphism, backdrop-blur, Framer Motion for hover/entrance, or any generic SaaS template styling.
- Overclaim PersonnaPress SEO tooling: we generate SEO-structured output but do NOT integrate Ahrefs/Semrush/Surfer — that row is a competitor win where applicable.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Spoke page render | Visit `/jasper-alternatives` | Static HTML: answer-first hero, quotable verdict, fair table, competitor-wins section, differentiators, FAQ, Highlighter CTA; 3 JSON-LD blocks valid | N/A |
| Hub page render | Visit `/best-ai-blog-writers` | Static HTML ranking the tools with `ItemList` JSON-LD + links to all 3 spokes | N/A |
| Comparison data | Component reads a competitor data entry | Renders that entry's rows/verdict/FAQ; FAQ text == FAQPage JSON-LD text | Missing optional field renders nothing, never "undefined" |
| Reduced motion | `prefers-reduced-motion: reduce` | No entrance animation | Animations gated in `@media (prefers-reduced-motion: no-preference)` |
| Keyboard/SR nav | Tab through page | Visible `focus-visible:ring-2 ring-ink`; table `<th scope>`; single H1; decorative icons `aria-hidden` | N/A |

</frozen-after-approval>

## Code Map

- `frontend/app/(public)/headless-blog-api/page.tsx:340-460` -- REFERENCE for hero, `<ol role="list">` steps, brutalist comparison table (Ink header, `<th scope="col/row">`, `Check`/`X` cells with `aria-label`), full-bleed Highlighter CTA, and JSON-LD block placement. Copy these patterns.
- `frontend/app/(public)/pricing/page.tsx:84-86` -- exact JSON-LD injection with `.replace(/</g, "\\u003c")` escaping. Use this variant.
- `frontend/app/(public)/layout.tsx` -- provides `PublicHeader`/`PublicFooter`; new routes under `(public)` inherit it automatically.
- `frontend/app/_components/FaqAccordion.tsx` (imported as `@/app/_components/FaqAccordion`) -- reuse; client island with aria wiring; feed it the same array used for FAQ JSON-LD.
- `frontend/components/marketing/PublicFooter.tsx` -- add cluster links (Product or Resources column) alongside "Headless Blog API".
- `frontend/app/sitemap.ts` -- add 4 routes before the `...blogSlugs` spread; keep trailing-slash guard; `BASE_URL` fallback `https://www.personnapress.com`.
- `frontend/app/robots.ts` -- verify the 4 routes are covered by `allow: "/"` (no change expected; confirm not under a disallow prefix).
- `frontend/app/page.tsx:200-235` -- Organization/offers JSON-LD + PersonnaPress pricing (Starter $29, Growth $79, Agency $199) source of truth for `SoftwareApplication.offers`.
- Constant per file: `const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "")`.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/components/marketing/comparisons.data.ts` -- create typed data module. Export a `ComparisonPageData` type and a `COMPARISONS` record keyed `jasper` | `copy-ai` | `writesonic`, each with: slug, competitorName, metadata (title/description/canonical path), heroAnswer (40-60 words), verdict (2-3 sentences), pricingNote (entry price + "as of September 2026, check current pricing" + source URL), comparisonRows (feature/personnapress/competitor with at least one competitor-win row), competitorStrengths (2-3 honest items), differentiators (3 items with Lucide icon name), faqItems (5+ Q/A), relatedLinks. Seed factual content from Design Notes.
- [x] `frontend/components/marketing/ComparisonPage.tsx` -- create shared server component taking `ComparisonPageData`. Renders hero (answer-first), quotable verdict card, brutalist comparison table, "Where {competitor} is the better choice" section, differentiators `<ol role="list">`, `FaqAccordion`, full-bleed Highlighter CTA. No client fetching; single H1; a11y per matrix.
- [x] `frontend/app/(public)/jasper-alternatives/page.tsx` -- thin route: `export const dynamic = "force-static"`, `generateMetadata()`, 3 JSON-LD blocks (`SoftwareApplication` + `FAQPage` from data + `BreadcrumbList`), render `<ComparisonPage data={COMPARISONS["jasper"]} />`.
- [x] `frontend/app/(public)/copy-ai-alternatives/page.tsx` -- same pattern, `copy-ai` entry.
- [x] `frontend/app/(public)/writesonic-alternatives/page.tsx` -- same pattern, `writesonic` entry.
- [x] `frontend/app/(public)/best-ai-blog-writers/page.tsx` -- hub page: keyword-first H1 ("Best AI Blog Writers"), answer-first intro, a ranked list/table of the tools (fair, PersonnaPress + the 3 competitors + short honest take each), `ItemList` + `FAQPage` + `BreadcrumbList` JSON-LD, internal links to all 3 spokes, Highlighter CTA. Reuse table/CTA styling.
- [x] `frontend/app/sitemap.ts` -- add the 4 routes (changeFrequency `monthly`, priority 0.8 spokes / 0.9 hub).
- [x] `frontend/components/marketing/PublicFooter.tsx` -- add 4 cluster links.
- [x] `frontend/app/robots.ts` -- confirm coverage (change only if needed).

**Acceptance Criteria:**
- Given any spoke route, when built, then `next build` lists it as `○ (Static)` and it renders hero + verdict + table + competitor-wins + differentiators + FAQ + CTA in Paper Style.
- Given the JSON-LD, when parsed, then each page has valid `SoftwareApplication` (offers Starter $29/Growth $79/Agency $199), `FAQPage` (5+ Q/A, text identical to visible accordion), and `BreadcrumbList` (Home › page); the hub also has a valid `ItemList`.
- Given the comparison tables, when reviewed, then every competitor claim is backed by that competitor's own page, carries the dated disclaimer, and each table has at least one competitor-win row; no unverified figure from the Never list appears.
- Given the hub, when rendered, then it links to all three spoke pages and each spoke links back to the hub (hub-and-spoke internal linking).
- Given copy, when grepped for `—`, `--`, `&mdash;`, and banned words, then zero hits.
- Given a11y, when audited, then single H1 per page, `<th scope>` on tables, `focus-visible:ring-2 ring-ink` on interactive elements, decorative icons `aria-hidden`, animations gated behind `prefers-reduced-motion`, no client-side data fetching.

## Design Notes

Verified competitor facts (September 2026; each page cites the competitor's own URL + dated disclaimer). All three HAVE a brand-voice feature — differentiate on the autonomous publish-and-distribute loop and long-form voice fidelity, not on brand-voice existence.

- **Jasper** (jasper.ai): entry Pro $69/mo/seat, no permanent free tier (7-day trial), 2 brand voices on Pro; positioned as an AI-agent marketing platform. Publishing stops at copy/paste handoff (WordPress/HubSpot integrations, no true one-click); deep SEO needs the paid Surfer add-on. Fair wins: mature multi-profile brand voice, breadth of marketing agents, early GEO/AEO investment.
- **Copy.ai** (copy.ai): entry Chat $29/mo, no free tier/trial, steep jump to Growth $1,000/mo; repositioned as a "GTM AI Platform." No native publishing (Zapier glue only); weak/no rank-oriented SEO (no SERP/keyword/scoring/integrations). Fair wins: fast short-form copy, GTM workflow automation, model flexibility.
- **Writesonic** (writesonic.com): entry Starter $79/mo; positioned as an AI-search/GEO growth engine; strong SEO (Surfer/Ahrefs/Semrush/GSC + GEO module) and one-click WordPress publish. Honest contrasts: documented long-form voice drift, WordPress-only publish with no native social auto-posting. Fair wins (mark as competitor wins in its table): SEO data integrations, GEO visibility tracking, all-in-one breadth. This page must NOT claim PersonnaPress beats Writesonic on SEO-tool integrations.

PersonnaPress differentiators (true vs all three): (1) autonomous idea → SEO-structured article + social posts → published, in your voice; (2) voice extracted from your existing content, held in long-form; (3) publish-and-distribute to blog (GitHub / WordPress / Webflow / headless API) AND social (X, LinkedIn, Meta) in one workflow. Entry price $29 (Starter), 14-day free trial, no credit card.

Answer-first hero example (jasper, ~50 words, for the quotable block):
> "The best Jasper alternative depends on your goal. Jasper is built for marketing teams running many agents. If you are a founder who wants one tool to write in your voice, structure content for SEO, and publish to your blog and socials automatically, PersonnaPress covers that whole loop end to end."

Table row set (per competitor; use Check/X, and `partial` in mono where honest): brand voice from your samples (parity: both yes); consistent long-form voice; auto-publish to your blog/CMS; auto-publish to social; SEO structure built into output; third-party SEO data integrations (competitor-win row where true, e.g. Writesonic yes / PersonnaPress no); autonomous idea→published loop; entry price; free to start.

Layout order (spoke): hero + dual CTA → `THE SHORT ANSWER` verdict card → comparison table (`overflow-x-auto`, `<caption className="sr-only">`) → "Where {competitor} is the better choice" → "Why founders switch" 3-col `<ol role="list">` → FAQ → Highlighter CTA.

## Verification

**Commands:**
- `cd frontend && npm run build` -- expected: succeeds; the 4 new routes appear as `○ (Static)`.
- `cd frontend && npx tsc --noEmit` -- expected: no type errors (data module + component typed).
- grep the 5 new page files + data module for `—`, `--`, `&mdash;`, "elevate", "delve", "unlock", "seamless", "empower" -- expected: zero hits.

**Manual checks:**
- Paste each page's 3 JSON-LD blocks into a validator (or `JSON.parse`) -- valid; FAQ JSON-LD text matches the visible accordion verbatim.
- Confirm each comparison claim traces to the linked competitor page and the dated disclaimer is visible; at least one competitor-win row present per table.
- Hub links to all 3 spokes and each spoke links back to the hub.

## Suggested Review Order

**Data & Design Intent**

- Entry point: all factual claims, table rows, FAQ, and pricing live here; read first.
  [`comparisons.data.ts:1`](../../frontend/components/marketing/comparisons.data.ts#L1)

- `ComparisonPageData` type governs every field ComparisonPage and route pages accept.
  [`comparisons.data.ts:23`](../../frontend/components/marketing/comparisons.data.ts#L23)

- `COMPARISONS` record: 3 entries seeded with verified competitor facts from Design Notes.
  [`comparisons.data.ts:37`](../../frontend/components/marketing/comparisons.data.ts#L37)

**Shared Component**

- Server component: 8-section layout; H1 from `title.split(" | ")[0]` avoids duplication.
  [`ComparisonPage.tsx:26`](../../frontend/components/marketing/ComparisonPage.tsx#L26)

- Comparison table: `overflow-x-auto`, `caption` sr-only, `th scope`, competitor-win badge.
  [`ComparisonPage.tsx:77`](../../frontend/components/marketing/ComparisonPage.tsx#L77)

- Differentiators `ol[role="list"]`: `ICON_MAP` string lookup; `ArrowRight` fallback for unknowns.
  [`ComparisonPage.tsx:188`](../../frontend/components/marketing/ComparisonPage.tsx#L188)

**JSON-LD and Metadata (representative spoke)**

- `SoftwareApplication` with 3 offers ($29/$79/$199) — values from `page.tsx:200-235` source of truth.
  [`jasper-alternatives/page.tsx:37`](../../frontend/app/(public)/jasper-alternatives/page.tsx#L37)

- `FAQPage` built from `data.faqItems.map` — the exact same array `FaqAccordion` receives.
  [`jasper-alternatives/page.tsx:71`](../../frontend/app/(public)/jasper-alternatives/page.tsx#L71)

- `BreadcrumbList`; all 3 script tags use `<` escaping to prevent XSS.
  [`jasper-alternatives/page.tsx:81`](../../frontend/app/(public)/jasper-alternatives/page.tsx#L81)

**Hub Page**

- `ItemList` JSON-LD: 4 `SoftwareApplication` items via the `item` property (Schema.org correct).
  [`best-ai-blog-writers/page.tsx:64`](../../frontend/app/(public)/best-ai-blog-writers/page.tsx#L64)

- `TOOLS` array drives the ranked list rendering and spoke-page cross-links.
  [`best-ai-blog-writers/page.tsx:128`](../../frontend/app/(public)/best-ai-blog-writers/page.tsx#L128)

- Deep Dives 3-col grid: hub-to-spoke internal links completing the hub-and-spoke structure.
  [`best-ai-blog-writers/page.tsx:316`](../../frontend/app/(public)/best-ai-blog-writers/page.tsx#L316)

**Wiring**

- 4 new routes added; hub priority 0.9, spokes 0.8, `changeFrequency` monthly.
  [`sitemap.ts:64`](../../frontend/app/sitemap.ts#L64)

- 4 cluster links added to the Resources column alongside existing headless-blog-api link.
  [`PublicFooter.tsx:57`](../../frontend/components/marketing/PublicFooter.tsx#L57)
