# Story 12.4: Headless Blog API Cluster Page & Integration Docs

---
baseline_commit: 89ae16358dc7a4316d6fd71ab2b01b0d52e31ee3
---

Status: done

## Story

As a marketing site visitor evaluating headless CMS options,
I want a page that explains PersonnaPress headless blog delivery with real integration code,
so that I understand it as a Contentful alternative for blogs and can integrate in minutes.

## Acceptance Criteria

1. **Given** the route `/headless-blog-api`, **When** it is built, **Then** it lives at `frontend/app/(public)/headless-blog-api/page.tsx`, inherits `PublicHeader`/`PublicFooter` from the (public) layout, is statically generated (force-static with the `CopyrightYear` client-component pattern from Story 11.1), and renders in the Paper Style design system.

2. **Given** the page metadata, **When** the static page is generated, **Then** `generateMetadata()` sets a title targeting "Headless Blog API" (under 60 chars), a meta description under 160 chars mentioning API-powered blog delivery and Contentful alternative, canonical `/headless-blog-api`, and complete OpenGraph/Twitter card fields.

3. **Given** structured data, **When** the page renders, **Then** it embeds JSON-LD for `SoftwareApplication` (consistent with the existing landing pages) and a `FAQPage` with at least 5 questions targeting AEO queries such as "What is a headless blog API?", "How is PersonnaPress different from Contentful?", "Do I need a CMS to use it?", "How do I fetch articles on my website?", "Can I edit articles after publishing?" with answers matching the visible FAQ accordion content.

4. **Given** the page sections, **When** rendered, **Then** they include: a hero stating the store-once/deliver-anywhere positioning; a 3-step "How it works" (generate, store and version, fetch via API); a response-bundle showcase rendering a real `/public/v1/articles/{slug}` JSON example in a code block (including the `seo` object); an integration docs section with copy-paste examples for plain fetch, Next.js App Router, and Astro that work against the real API from Story 12.2; a brutalist comparison table (PersonnaPress vs Contentful vs DropInBlog) in the Story 8.7 table style; and a full-bleed Highlighter CTA section.

5. **Given** site-wide SEO plumbing, **When** the page ships, **Then** `sitemap.ts` gains the `/headless-blog-api` route, `robots.ts` allows it, and the `PublicFooter` product links include it.

6. **Given** the page copy, **When** written, **Then** it follows the human-seo-copywriter constraints: no AI tropes ("elevate", "delve", "unlock"), no em-dashes, E-E-A-T-conscious concrete claims, and technically accurate endpoint names and field names matching the implemented API.

7. **Given** accessibility and performance, **When** assessed, **Then** code blocks are keyboard-scrollable with visible focus, the comparison table uses proper `<th scope>` attributes, animations respect `prefers-reduced-motion`, all images have descriptive alt text, and the page introduces no client-side data fetching.

## Tasks / Subtasks

### Task 1: Page scaffold + metadata (AC: 1, 2)

- [x] 1.1 Create `frontend/app/(public)/headless-blog-api/page.tsx` as a server component with `export const dynamic = "force-static"`. Any date rendering uses the `CopyrightYear` client component (Story 11-1 patch) — the (public) layout footer already handles this; do not add another date source.
- [x] 1.2 Metadata (verify against implemented copy before finalizing):
  - title: `Headless Blog API for Your Website | PersonnaPress` (46 chars)
  - description: `Store blog content in PersonnaPress and fetch it on your own site through one API. A Contentful alternative built for blogs, with SEO data included.` (149 chars)
  - canonical `/headless-blog-api` via `alternates.canonical`; OpenGraph type website + og:image (reuse the existing OG image approach from 8-8, static image, no `runtime=edge`); Twitter `summary_large_image`. Use the existing `metadataBase` (Story 8-2 patch).

### Task 2: Structured data (AC: 3)

- [x] 2.1 JSON-LD via inline `<script type="application/ld+json">` with `JSON.stringify` of typed objects (match the existing landing page implementation exactly — Story 8-1 review REMOVED `dangerouslySetInnerHTML` usage; copy whatever pattern `frontend/app/page.tsx` currently uses).
- [x] 2.2 `SoftwareApplication` node consistent with existing pages (`operatingSystem: "Web"`, `applicationCategory`, `offers` matching PRD §8 pricing: Starter $29, Growth $79, Agency $199).
- [x] 2.3 `FAQPage` node with 5+ Q/As, text identical to the visible accordion (AEO requirement). FAQ accordion follows the 8-1 pattern including the review patches (stable `key`s, `aria-expanded`/`aria-controls`, button elements without nested headings — the 8-1 review flagged h3-in-button).

### Task 3: Page sections (AC: 4, 6)

- [x] 3.1 Hero: Playfair Display H1 "Your blog, on your website, powered by our API." (or refined equivalent hitting "headless blog API" in the first 100 words of body copy); Inter subhead: "PersonnaPress writes, stores, and versions your articles. Your site fetches them with one GET request. No CMS to install, no plugin to maintain."; primary CTA "Start free" (Ink fill, 4px 4px 0px Ink shadow, rounded-none) + secondary link "See the API response" anchoring to the showcase section.
- [x] 3.2 How it works, 3 numbered steps in a bento-ish 3-col grid (1-col mobile), each a Paper card with 1px Ink border, rounded-none, Lucide icon (`Sparkles` generate, `DatabaseZap` or `Database` store, `Braces` fetch), Inter 11px uppercase tracked step label, short body. CSS-only entrance (no Framer Motion; respect `prefers-reduced-motion` by gating any `animation` in a `@media (prefers-reduced-motion: no-preference)` block).
- [x] 3.3 Response showcase: dark Ink panel styled like the 8-8 terminal (reuse its component/classes if extractable; decorative dots `aria-hidden="true"`), containing a `<pre><code>` block with a realistic `GET /public/v1/articles/how-to-price-consulting-services` JSON response INCLUDING the `seo` object with `json_ld`, `og`, `meta_description`, and `reading_time_minutes`. Field names must match Story 12.2's implemented response exactly — read `backend/app/routers/public_articles.py` before writing this JSON. `<pre>` gets `tabIndex={0}`, `role="region"`, `aria-label="Example API response"`, `overflow-x-auto`, and `focus-visible:ring-2 focus-visible:ring-ink`.
- [x] 3.4 Integration docs section, H2 "Add it to your site in one request": three sub-blocks (plain fetch, Next.js App Router, Astro), each a code block in the same terminal styling. Static server-rendered code samples (plain `<pre><code>`, no syntax-highlighting dependency unless one already exists in the repo). Samples must be copy-paste runnable against the real API.
- [x] 3.5 Comparison table "Built for blogs, not for everything": Story 8.7 brutalist style (1px Ink borders throughout, no border-radius, Ink header row with White Inter 11px uppercase labels, `<th scope="col">` / `<th scope="row">`). Columns: Feature, PersonnaPress, Contentful, DropInBlog. Rows with checks (Success) and crosses (Danger) as specified. "SEO schema in every response" marked partial for DropInBlog (softened as not fully verifiable).
- [x] 3.6 FAQ accordion (content = JSON-LD Task 2.3), then full-bleed Highlighter (#FFF1B8) CTA section: Playfair H2 "Your blog does not need a CMS.", Inter body line, primary CTA "Start free, no credit card". Below: Inter 13px Graphite "14-day free trial. One API for content, SEO data, and images."
- [x] 3.7 Copy pass: grepped for all banned words (zero hits); no em-dashes anywhere in the page (verified by grep); keyword targets woven naturally throughout.

### Task 4: Site plumbing (AC: 5)

- [x] 4.1 `frontend/app/sitemap.ts`: added `/headless-blog-api` (changeFrequency `monthly`, priority 0.8, lastModified current date), keeping the trailing-slash guard.
- [x] 4.2 `frontend/app/robots.ts`: verified `/headless-blog-api` is allowed by default (not in disallow list; allow: "/" covers it). No change needed.
- [x] 4.3 `frontend/components/marketing/PublicFooter.tsx`: added "Headless Blog API" link alongside GitHub Publisher link.
- [x] 4.4 PublicHeader: GitHub Publisher has no nav item, so no nav item added for headless-blog-api (mirrors existing behavior).

### Task 5: Accessibility + performance pass (AC: 7)

- [x] 5.1 Checklist: code blocks have `tabIndex={0}`, `role="region"`, `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`, and `overflow-x-auto`. Comparison table uses `<th scope="col">` and `<th scope="row">`. Decorative icons have `aria-hidden="true"`. Single H1. Heading hierarchy H1 > H2 (no skips; no H3 on page). `text-balance` on all headings, `text-pretty` on body paragraphs. No client-side data fetching. Only client JS island is the existing FaqAccordion component.
- [x] 5.2 `npm run build` passes. `/headless-blog-api` shown as `○ (Static)` in build output.

### Task 6: Verification (AC: all)

- [x] 6.1 JSON-LD structure verified: both `SoftwareApplication` and `FAQPage` objects pass JSON.parse (valid JSON). SoftwareApplication has operatingSystem, applicationCategory, offers array (Starter/Growth/Agency). FAQPage has 7 Q/A pairs (above minimum 5). Accordion text matches JSON-LD text exactly (same FAQ_ITEMS array used for both).
- [x] 6.2 Endpoint paths cross-checked: `GET /public/v1/articles` and `GET /public/v1/articles/{slug}` match `backend/app/routers/public_articles.py`. Field names in EXAMPLE_RESPONSE match `_article_list_item()` + `_build_seo()` output exactly (slug, title, excerpt, featured_image_url, author, tags, category, published_at, updated_at, reading_time_minutes, html, seo with reading_time_minutes/meta_description/json_ld/og).
- [x] 6.3 Grepped final page source for `—` (em-dash), `&mdash;`, `&#8212;`, and banned words ("elevate", "delve", "unlock", "seamless", "empower"): zero hits.

## Dev Notes

### Critical constraints

- **Do not ship before Story 12.2 is done.** Every code sample and the JSON showcase must reflect the real, implemented API. If 12.2's response shape changed during its review, this page follows the implementation, not the epic text.
- **Static only.** `force-static`; no TanStack Query, no client fetch, no dynamic rendering. The RSC loop rule is moot here because there are no API calls, but any date must use `CopyrightYear` (force-static pages cannot render `new Date()` server-side per Story 11-1 patch).
- **Paper Style, not generic SaaS glassmorphism.** This site is brutalist Paper: 1px Ink borders, rounded-none, Playfair/Inter, Highlighter accents, hard 4px offset shadows. Glassmorphism/backdrop-blur is NOT part of this design system — ignore any generic template instinct and match `frontend/app/page.tsx` and the github-publisher page.
- **Copy rules are hard requirements:** no em-dashes, no AI-trope vocabulary, no emojis; icons only from Lucide (already installed).
- **Honest comparison table.** Only verifiable claims; this page carries legal/brand risk if it misstates Contentful or DropInBlog capabilities.

### Reuse map

| Need | Existing code |
|---|---|
| Page + metadata pattern | `frontend/app/github-publisher/page.tsx` (Story 8-8) and `frontend/app/page.tsx` (8-1/8-2) |
| Public layout, header/footer | `frontend/app/(public)/layout.tsx`, `frontend/components/marketing/PublicHeader.tsx` / `PublicFooter.tsx` |
| JSON-LD injection pattern | landing page implementation (post-8-1-review pattern) |
| Terminal-styled code panel | github-publisher page demo section |
| Comparison table style | Story 8.7 AC (epics.md ~line 1702) + its implementation in github-publisher page |
| FAQ accordion | landing page FAQ (8-1 patched: keys + aria) |
| CopyrightYear | Story 11-1 client component |
| Sitemap/robots | `frontend/app/sitemap.ts`, `frontend/app/robots.ts` (9-1 trailing-slash guard) |

### Previous story intelligence

- 8-1 review patches to respect: no `dangerouslySetInnerHTML` for JSON-LD (use the replacement pattern in the current code), no h3 inside buttons, FAQ needs stable keys + aria wiring, `&mdash;` entities were removed (consistent with the no-em-dash rule).
- 8-8 review patches: `window.matchMedia` existence guard for reduced-motion checks in any client component; IntersectionObserver must disconnect on trigger; OG image must not use `runtime=edge`; alt text describes the image, not the product.
- 8-2 review: `metadataBase` is set globally; pricing wording must match PRD §8 exactly.
- 11-1 review: semantic list markup for step sequences (`ol`/`li`, not divs styled as steps) — apply to the 3-step How it works.

### SEO/AEO targets

- Primary: "headless blog api". Secondary: "contentful alternative for blogs", "blog content api", "api powered blog". Long-tail via FAQ: "what is a headless blog api", "how to add a blog to my website without a cms".
- The FAQ answers should be quotable 2-3 sentence direct answers (AEO: AI engines lift concise, self-contained answers).
- Internal links: hero/CTA to signup, one contextual link to `/github-publisher` ("publish to a GitHub Pages repo instead") and one to the landing page pricing section.

### Project Structure Notes

- Page: `frontend/app/(public)/headless-blog-api/page.tsx` (single file preferred, matching how privacy/terms pages are structured; extract components only if the file exceeds the github-publisher page's organization pattern).
- No backend changes in this story.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 12, Story 12.4]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 8.7 (comparison table + terminal styling + SEO AC patterns)]
- [Source: _bmad-output/implementation-artifacts/12-2-public-delivery-api-tokens.md (response shape source of truth)]
- [Source: _bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md#8 Monetization (pricing for offers JSON-LD)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was clean on first pass.

### Completion Notes List

- Created `frontend/app/(public)/headless-blog-api/page.tsx` as a fully static server component (force-static) inheriting PublicHeader/PublicFooter from the (public) layout.
- generateMetadata() returns title (49 chars), description (149 chars), canonical, OG (website type, static OG image, no runtime=edge), and Twitter summary_large_image.
- Two JSON-LD blocks: SoftwareApplication (BusinessApplication, Web, 3-tier offers array Starter/Growth/Agency) and FAQPage (7 Q/As, text identical to FaqAccordion items).
- Page sections: hero with shadow-brutal CTA and anchor link to API showcase; 3-step how-it-works rendered as `<ol>` with Lucide icons (Sparkles/Database/Braces); terminal-styled API response showcase with tabIndex/role/aria-label/focus-visible ring; integration docs with plain fetch/Next.js App Router/Astro code blocks; brutalist comparison table (PersonnaPress vs Contentful vs DropInBlog) with th scope attributes; FaqAccordion; full-bleed bg-highlighter CTA.
- All API endpoints verified against backend/app/routers/public_articles.py: `GET /public/v1/articles` and `GET /public/v1/articles/{slug}` at api.personnapress.com (public_app mounted at /public in main.py).
- EXAMPLE_RESPONSE JSON field names match _article_list_item() + _build_seo() exactly (slug, title, excerpt, featured_image_url, author, tags, category, published_at, updated_at, reading_time_minutes, html, seo.reading_time_minutes, seo.meta_description, seo.json_ld, seo.og).
- Zero em-dashes in page source (verified by grep). Zero banned copywriting words (verified by grep).
- robots.ts: no change needed; /headless-blog-api covered by allow: "/".
- sitemap.ts: /headless-blog-api added (monthly, 0.8 priority).
- PublicFooter: "Headless Blog API" link added alongside GitHub Publisher.
- PublicHeader: no change (GitHub Publisher has no nav item; mirroring existing behavior).
- Build output confirms /headless-blog-api as ○ (Static).

### File List

- frontend/app/(public)/headless-blog-api/page.tsx (new)
- frontend/app/sitemap.ts (modified)
- frontend/components/marketing/PublicFooter.tsx (modified)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified)
- _bmad-output/implementation-artifacts/12-4-headless-blog-api-cluster-page.md (modified)

### Review Findings

- [x] [Review][Patch] ASTRO_SAMPLE TypeError: `article.seo.og.title` and `.og.image` crash when `seo.og` is absent (conditional in `_build_seo()`) [frontend/app/(public)/headless-blog-api/page.tsx:278-281]
- [x] [Review][Patch] FAQ "How do I fetch articles?" answer points to list endpoint but claims it returns `html` and `seo` — these fields only exist on the detail endpoint `/articles/{slug}` [frontend/app/(public)/headless-blog-api/page.tsx:112]
- [x] [Review][Patch] FETCH_SAMPLE missing `res.ok` check before `res.json()` — silently parses error body on 401/429 [frontend/app/(public)/headless-blog-api/page.tsx:202-214]
- [x] [Review][Patch] `<ol list-none>` missing `role="list"` — VoiceOver/Safari strips ordered-list semantics from `list-style: none` elements [frontend/app/(public)/headless-blog-api/page.tsx:411]
- [x] [Review][Patch] FAQ "What fields does the API response include?" presents `meta_description` and `og` as always-present; they are conditional in `_build_seo()` [frontend/app/(public)/headless-blog-api/page.tsx:122]
- [x] [Review][Patch] NEXTJS_SAMPLE: `article.seo.meta_description` and `article.seo.og` passed without optional chaining to Next.js metadata [frontend/app/(public)/headless-blog-api/page.tsx:236-240]

## Change Log

- 2026-07-14: Story 12.4 implemented — headless blog API cluster page created with metadata, JSON-LD (SoftwareApplication + FAQPage), hero, how-it-works, API response showcase, integration docs (fetch/Next.js/Astro), comparison table, FAQ accordion, and CTA. Sitemap and PublicFooter updated. Build verified static.
