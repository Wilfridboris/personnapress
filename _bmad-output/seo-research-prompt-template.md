# SEO Keyword Opportunity Research — [APP NAME]

Act as an SEO and marketing expert. Your goal is to produce a complete keyword opportunity map
for [APP NAME] using live DataForSEO API calls. Do not create any stories or code.
Research first, then deliver the map.

---

## App Context

- **Name:** [APP NAME] (exact brand spelling: [e.g. PersonnaPress — double-n])
- **Domain:** [e.g. personnapress.com]
- **One-line description:** [e.g. AI-powered content platform that extracts brand voice and
  publishes blog posts + social content to WordPress, Webflow, LinkedIn, and X]
- **Target audiences:** [e.g. marketing agencies, content teams, solopreneurs]
- **Core differentiators:** [e.g. brand voice extraction, multi-platform publishing,
  featured image generation]
- **Pricing model:** [e.g. SaaS, monthly subscription]
- **Tech stack (if relevant to positioning):** [e.g. AI-generated content via Gemini,
  images via FLUX.1]

---

## Feature Areas / Planned Landing Pages

List every feature or integration that might warrant its own landing page or keyword cluster.
Be exhaustive — the research must cover ALL of these, not just the homepage.

1. [Feature 1 — e.g. Brand Voice Generator]
2. [Feature 2 — e.g. AI Blog Post Generation]
3. [Feature 3 — e.g. WordPress Publishing Integration]
4. [Feature 4 — e.g. Webflow CMS Integration]
5. [Feature 5 — e.g. LinkedIn Post Generator]
6. [Feature 6 — e.g. X / Twitter Post Generator]
7. [Feature 7 — e.g. Featured Image Generation]
8. [Feature 8 — e.g. Content Calendar / Scheduler]
9. [Feature 9 — e.g. GitHub Pages Publishing]
10. [Feature 10 — e.g. Headless Blog API]
11. [Integration/use-case pages — e.g. For Marketing Agencies, For Solopreneurs]
12. [Comparison pages — e.g. vs Jasper, vs blaze.ai, vs Contentful]

---

## Direct Competitors

These are the tools [APP NAME] competes with most directly. Pull their ranked keywords.

1. [competitor1.com]
2. [competitor2.com]
3. [competitor3.com]

---

## Research Instructions

Execute all steps using the DataForSEO MCP tools (`mcp__dataforseo__api_request`).
Run independent calls in parallel where possible.

### Step 1 — Domain Baseline

Check if [APP NAME]'s domain already has Google organic rankings:

- `POST /v3/dataforseo_labs/google/domain_rank_overview/live`
  - target: `[domain.com]`, language: English, location: United States

### Step 2 — Competitor Ranked Keywords

For each competitor, pull their top ranked keywords to understand what's actually
ranking in this market:

- `POST /v3/dataforseo_labs/google/ranked_keywords/live`
  - target: `[competitor.com]`, limit: 40, order_by: `["keyword_data.keyword_info.search_volume,desc"]`

### Step 3 — SERP Competitors for Core Keywords

For 3–5 of the most important seed keywords, check who actually ranks:

- `POST /v3/dataforseo_labs/google/serp_competitors/live`
  - Use the most important commercial keywords for this app's category

### Step 4 — Keyword Ideas per Feature Area

Run one keyword ideas call per feature area from the list above. Use 5–8 specific
seed keywords per call that match how a real user would search for that feature.
Do NOT use generic seeds — be specific to the feature.

- `POST /v3/dataforseo_labs/google/keyword_ideas/live`
  - language: English, location: United States, limit: 50
  - include_serp_info: true, include_keyword_annotations: true

### Step 5 — Brand Mention and Sentiment Check

Check if [APP NAME] has any brand mentions or editorial coverage:

- `POST /v3/content_analysis/search/live`
  - keyword: `"[APP NAME]"`, limit: 10
- `POST /v3/content_analysis/sentiment_analysis/live`
  - keyword: `"[APP NAME]"`

---

## Output Format

Produce a markdown document with these sections:

### 1. Executive Summary

- Domain baseline (zero rankings vs. established)
- The single biggest keyword opportunity found
- The single most important strategic insight

### 2. Market Intelligence

- What competitors actually rank for (table: competitor / keyword / position / SV / KD)
- What that tells us about the market

### 3. Keyword Opportunity Map — by Landing Page

One section per feature area. For each:

- Table: keyword | SV | KD | intent | priority
- Honest assessment: is this a real keyword category with search volume?
- Recommended page title targeting the primary keyword
- If no volume exists: say so and recommend the right distribution channel instead
  (developer communities, marketplaces, AEO/AI citation, etc.)

### 4. Top 15 Keywords to Own

Master table sorted by opportunity score (low KD + meaningful SV + on-target intent):

| # | Keyword | SV | KD | Intent | Target Page | Phase |

### 5. Keywords Explicitly Ruled Out

Table of keyword categories to avoid and why (declining market, too competitive,
wrong audience, no volume).

### 6. Priority Action Plan

Three phases:

- Phase 1: Foundation (SEO infrastructure — metadata, schema, sitemap)
- Phase 2: Highest ROI content (lowest KD, most on-target intent)
- Phase 3: Platform positioning (broader commercial keywords)

For each phase, name the specific story or page to build.

---

## Rules

- Never create stories, code, or implementation artifacts — research and map only.
- If a keyword idea batch returns irrelevant noise (the seeds were too broad),
  note it and run a second batch with more specific seeds.
- If a feature area has zero search volume, say so plainly — do not invent opportunity
  where none exists. Recommend the right non-SEO channel instead.
- Distinguish between traditional SEO opportunity (Google rankings) and AEO opportunity
  (AI answer engine citation via FAQPage schema). Some pages are AEO-first, not SEO-first.
- Flag all declining keyword categories (check yearly trend data from keyword_info).
- KD reference: 0-20 = low resistance, 21-40 = moderate, 41-60 = competitive,
  60+ = established players only.
