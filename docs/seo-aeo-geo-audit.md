# PersonnaPress SEO / AEO / GEO Audit — Public Marketing Pages

**Date:** 2026-09-18
**Scope:** Public marketing pages only (home, pricing, about, brand-voice-generator, headless-blog-api, github-publisher, blog list). Authenticated app and headless-blog API internals excluded.
**Deliverable:** Review and recommendations only. No code changes were made.

## Verdict

The technical foundation is genuinely strong, well ahead of most seed-stage SaaS. Structured data, metadata, sitemap, semantic HTML, and AI-crawler access are already in place and correct. The on-site technical work is roughly 80% done, and it is not where the remaining gains are.

The real gaps are three: one latent technical risk (canonical host), a content-depth gap (comparison, use-case, and definitional pages), and a thin off-site entity footprint. AEO and GEO are won mostly by content and off-page presence, not by more schema, so that is where the effort should go.

### Scorecard

| Discipline | Score | One-line |
|---|---|---|
| Technical SEO | 8/10 | Excellent structure; docked for a www vs non-www canonical risk |
| On-page SEO | 7/10 | Solid, but title tags and content coverage leave demand on the table |
| Structured data | 9/10 | Best-in-class for this stage |
| AEO (answer engines) | 6/10 | Great schema and FAQs; missing definitional and comparison content |
| GEO (generative engines) | 5/10 | AI crawlers allowed (good), but weak entity graph, no llms.txt, likely minimal off-site citations |

---

## Product context used to ground this audit

- **Product:** PersonnaPress, an autonomous content engine built to eliminate "AI slop."
- **USP:** "Your Ideas, Published and Ranked, In Your Voice, Not AI's."
- **ICP:** SaaS founders, business coaches, marketing agencies (North America).
- **Core pains sold against:** time scarcity, generic AI voice, no SEO structure, siloed blog-to-social workflows.

---

## P0 — Fix first (correctness risk) — RESOLVED 2026-09-18

### 1. Canonical host was inconsistent in code (www vs non-www)

Fallbacks disagreed across files: `app/layout.tsx` and most feature pages used `https://www.personnapress.com` (**www**), while `app/robots.ts`, `app/sitemap.ts`, `pricing`, and `.env.example` used `https://personnapress.com` (**non-www**). If `NEXT_PUBLIC_APP_URL` were ever missing or inconsistent between environments, canonical tags, sitemap, OG URLs, and the robots sitemap line would point at two different hosts, splitting link equity and risking duplicate-content canonicalization.

**Production truth (verified via HTTP headers):**

- `personnapress.com` (apex) returns `308 Permanent Redirect` -> `https://www.personnapress.com/`
- `www.personnapress.com` returns `200 OK`

So **www is the live canonical host**, and it is what Google has indexed and what the directory listings link to.

**Fix applied:** every base-URL fallback in the codebase was aligned to `https://www.personnapress.com` (12 source files: `layout.tsx`, `page.tsx`, `github-publisher/page.tsx`, `headless-blog-api/page.tsx`, `headless-blog-api/docs/page.tsx`, `brand-voice-generator/page.tsx`, `about/page.tsx`, `blog/page.tsx`, `blog/[slug]/page.tsx`, `pricing/page.tsx`, `robots.ts`, `sitemap.ts`), plus `.env.example` and `.env.local.example`. The `api.personnapress.com` and `cdn.personnapress.com` subdomains were intentionally left unchanged.

**Remaining operational step (cannot be done from code):** confirm `NEXT_PUBLIC_APP_URL=https://www.personnapress.com` is set in Vercel production. The apex->www 308 redirect is already in place.

> Alternative direction: if you would rather make the bare apex (`personnapress.com`) the canonical host (cleaner URLs), the fix is the opposite: flip the Vercel redirect to www->apex, set the env var to the apex, and revert the code fallbacks. This is not recommended right now because it would force re-indexing of already-ranked www URLs.

---

## P1 — High impact

### 2. Title tags are brand-first; make them keyword-first

The brand has near-zero search volume today, so leading titles with "PersonnaPress | Official Site" spends the most valuable SEO real estate on a term nobody searches yet.

**Applied 2026-09-18** (rendered titles, keyword-first, brand last, no em-dash, no double-branding):

| Page | Rendered title before | Rendered title after |
|---|---|---|
| Home | `PersonnaPress \| Official Site - AI Content Platform` | `AI Blog Writer That Sounds Like You \| PersonnaPress` |
| Pricing | `PersonnaPress Pricing — AI Content Automation Plans \| PersonnaPress` | `AI Content Automation Pricing & Plans \| PersonnaPress` |
| Blog list | `Blog \| PersonnaPress` | `AI Content Marketing & Brand Voice Strategy \| PersonnaPress` |

The blog-list case was the clearest miss: the H1 is keyword-rich ("AI Content Marketing, Brand Voice & Publishing Strategy") but the title tag Google ranked on just said "Blog." Two extra issues surfaced during the fix: the pricing title was accidentally **double-branded** (a plain-string child title receives the root `%s | PersonnaPress` template, so "PersonnaPress Pricing" rendered with a trailing "| PersonnaPress" as well), and it contained an **em-dash**, which violates house style. Both are resolved by dropping the leading brand and letting the template supply the single trailing brand. OpenGraph and Twitter titles (which do not receive the template) were set to the full brand-suffixed string to match.

Pages left as-is: `github-publisher` and `headless-blog-api` are already keyword-first; `brand-voice-generator` leads with its exact keyword; `about` stays "About Boris Kwayep, Founder of PersonnaPress" (founder-first is correct for E-E-A-T). "Official Site" was dropped from the home title to capture non-brand demand; revisit only if branded-SERP defense becomes a concern as brand search volume grows.

### 3. Enrich the entity graph (biggest GEO lever)

`Organization.sameAs` currently lists only Facebook, yet the About page already exposes the founder's LinkedIn and X. LLMs and Google's Knowledge Graph learn who a brand is by triangulating consistent entity references across the web. A thin `sameAs` gives them almost nothing to anchor on.

Add to the Organization schema:

- `sameAs`: LinkedIn company page, X, Product Hunt, Crunchbase, and G2/Capterra once listed
- `contactPoint` (support email is already public), `foundingDate`, and `address` (Scarborough, Canada, per public directory data)

**Applied 2026-09-18:** `foundingDate: "2026"`, `address` (Scarborough, ON, CA), and `contactPoint` (customer support, `support@personnapress.com`, English) were added to `Organization` in `app/page.tsx`, alongside the six directory `sameAs` entries. Still open: a company-owned LinkedIn/X page and Product Hunt/Crunchbase profiles to extend `sameAs` further.

Consistency matters more than volume: same name, same founder, same one-line description everywhere.

**Directory research (2026-09-18) and `sameAs` status:**

| Directory | Listing found | URL | Action |
|---|---|---|---|
| AlternativeTo | Yes (verified live) | `https://alternativeto.net/software/personnapress/` | Added to `sameAs` |
| SaaSHub | Yes (verified live) | `https://www.saashub.com/personnapress` | Added to `sameAs` |
| G2 | Indexed in search with standard live-product title ("PersonnaPress Reviews 2026: Details, Pricing, & Features"); direct fetch blocked by G2 bot protection (403), so not machine-verified | `https://www.g2.com/products/personnapress/reviews` | Added to `sameAs` (confirm in a browser) |
| Capterra (.ca) | Yes (verified live) | `https://www.capterra.ca/software/1108715/PersonnaPress` | Added to `sameAs` |
| Software Advice | Yes (verified live) | `https://www.softwareadvice.com/product/560892-PersonnaPress/` | Added to `sameAs` |
| GetApp | Yes (verified live) | `https://www.getapp.com/all-software/a/personnapress/` | Added to `sameAs` |

Note: Capterra, Software Advice, and GetApp are all Gartner Digital Markets properties and the profiles are already live (though each shows zero reviews so far). The next step is to seed genuine customer reviews, which is what actually drives ranking and AI citations from these sources.

Six directory listings (AlternativeTo, SaaSHub, Capterra.ca, Software Advice, GetApp, G2) were added to `Organization.sameAs` in `app/page.tsx` alongside the existing Facebook entry. Five were fetched and confirmed live; G2 could not be machine-verified because it blocks bots, but it is indexed in search with a standard live-product title, so it was added on that evidence (worth a manual browser check).

### 4. Build comparison and "alternative" pages (highest content ROI)

The single most valuable content gap, serving SEO, AEO, and GEO simultaneously. When a founder asks Google, ChatGPT, or Perplexity "what is the best AI writer that keeps my brand voice," the pages that get ranked and cited are comparisons and alternatives lists.

The "Contentful alternative" framing on `/headless-blog-api` already does this well. Extend the pattern:

- `PersonnaPress vs Jasper`, `vs Copy.ai`, `vs Writesonic`
- `Best AI blog writers for SaaS founders / coaches / agencies`
- `Jasper alternatives that match your brand voice`

These are bottom-of-funnel, high-intent, and disproportionately cited by answer engines.

---

## P2 — Medium impact

### 5. Persona / use-case landing pages

The ICP is explicitly SaaS founders, coaches, and agencies. Build one page each: `/ai-blog-writer-for-saas-founders`, `/for-coaches`, `/for-agencies`. Captures long-tail intent and gives AI engines persona-specific answers to quote. Keep H1s to the `[Feature] + [Action] + [Platform]` naming rule.

### 6. Definitional / glossary pages for AEO

Answer engines favor clean definitions. Create short answer-first pages: "What is brand voice," "What is a headless blog API," "What is AI content that ranks." Structure each as a 40-60 word direct answer at the top, then depth below. This wins featured snippets and AI Overview citations.

### 7. llms.txt + explicit AI-crawler coverage

- Add `/llms.txt` (and optionally `/llms-full.txt`): a plain-text summary of what PersonnaPress is, canonical page descriptions, and links. Low cost, emerging convention, a clean signal to generative crawlers.
- `robots.ts` already allows GPTBot, PerplexityBot, ClaudeBot, CCBot, and anthropic-ai. Since AI visibility is a goal, explicitly add `Google-Extended` (Gemini and AI Overviews grounding) and `OAI-SearchBot` (ChatGPT Search, distinct from GPTBot, which is training). The wildcard already permits them, but being explicit documents intent and prevents an accidental future block.

### 8. BreadcrumbList everywhere, not just pricing

Only `/pricing` has breadcrumb schema. Add it to every deep page. It earns breadcrumb SERP display and gives answer engines page-hierarchy context.

---

## P3 — Polish

- **Per-page OG images.** Every page shares one static OG image. Generate per-page images via `next/og` `ImageResponse` for better social and AI-surface click-through.
- **Font payload.** Three Google families load (Playfair, Inter, JetBrains Mono). `next/font` self-hosts them (good), but confirm every weight is actually used above the fold; each adds Core Web Vitals cost.
- **FAQ schema reality check.** Keep the FAQ schema (it still helps AEO extraction), but note Google no longer shows FAQ rich results for non-authoritative sites, so do not expect SERP stars from it.

---

## Off-page (where AEO/GEO are actually won)

On-site work is nearly maxed out. Generative engines cite brands that appear in third-party authoritative sources. To move GEO:

- Listings on G2, Capterra, Product Hunt, and AlternativeTo
- Inclusion in "best AI writing tools" listicles (outreach or guest contributions)
- Quotable original assets: publish one real stat or benchmark ("6-hour article cut to 90 seconds of review" is a strong claim, prove it with data), because LLMs preferentially cite content containing statistics and clear claims.

No amount of schema substitutes for existing off-site presence.

---

## Measurement baseline (capture before and after)

1. **Google Search Console** and **Bing Webmaster Tools**: verify the canonical host on both. Bing matters more than usual because it grounds ChatGPT and Copilot.
2. **PageSpeed Insights** on `/` and `/pricing` for real Core Web Vitals (not measurable from source).
3. **GEO baseline:** manually prompt ChatGPT, Perplexity, Gemini, and Google AI Overviews with "AI blog writer that matches my brand voice" and record whether PersonnaPress appears. Re-run monthly to track citation share.

---

## Suggested sequence

1. Fix canonical host (P0) and title tags (P1.2) this week.
2. Enrich entity schema (P1.3) and ship 2-3 comparison pages (P1.4).
3. Add llms.txt + crawler coverage (P2.7), then persona and definitional pages (P2.5, P2.6).
4. Run off-page listings in parallel throughout.

---

## Appendix — current-state inventory (as audited)

**Framework:** Next.js 16.2.9, App Router. Marketing pages are Server Components; most are static (SSG) or ISR-cached.

**Metadata:** Root layout defines `metadataBase`, title template `%s | PersonnaPress`, default description, Open Graph, Twitter card, and `robots: index/follow`. Per-page metadata and canonical `alternates.canonical` present on home, pricing, about, blog, brand-voice-generator, and headless-blog-api.

**Structured data (JSON-LD):** Comprehensive.
- Home: WebSite, SoftwareApplication, Organization, FAQPage
- Pricing: WebPage + BreadcrumbList + Offers
- About: Person
- Blog list: Blog
- Brand Voice Generator: SoftwareApplication + FAQPage
- Headless Blog API: SoftwareApplication + FAQPage
- GitHub Publisher: SoftwareApplication

**Technical foundation:**
- `app/sitemap.ts` covers all marketing routes plus dynamic blog slugs with priorities and change frequencies.
- `app/robots.ts` allows public pages, disallows authenticated routes (`/dashboard`, `/campaigns`, `/clients`, `/settings`, `/account`, `/onboarding`), and explicitly allows GPTBot, PerplexityBot, Googlebot, anthropic-ai, ClaudeBot, CCBot.
- Static `public/site.webmanifest` present (no dynamic `manifest.ts`).
- No `llms.txt` or `ai.txt`.
- Base URL via `NEXT_PUBLIC_APP_URL`, with inconsistent www vs non-www fallbacks (see P0).

**Semantic HTML:** Home page has a single H1, proper H2/H3 hierarchy, and `main`/`section`/`article` elements. Pricing page has a single H1 and a semantic comparison table with `scope` attributes.

**Performance:** `next/image` with `priority`/lazy and responsive `sizes`; `next/font` with `display: swap` across three families; marketing pages are Server Components with minimal client hydration (public header only).

**Marketing H1s (keyword targeting):**
- Home: "The AI Content Platform That Publishes in Your Brand Voice."
- Pricing: "AI content automation, priced for every team"
- About: "Boris Kwayep"
- Blog list: "AI Content Marketing, Brand Voice & Publishing Strategy."
- Brand Voice Generator: "Extract Your Voice, Keep It Everywhere."
- Headless Blog API: "The AI Headless Blog API for Custom Web Apps."

**Internal linking:** Public header and four-section footer interconnect all marketing pages, with in-page anchors (`#workflow`, `#platforms`, `#faq`, `#pricing`).
