# Story 12.6: Headless Blog API Developer Docs Page

Status: done

## Story

As a PersonnaPress customer who has signed up and created a delivery token,
I want a dedicated developer reference page at `/headless-blog-api/docs` that documents every endpoint, parameter, and error code,
so that I can complete my blog integration without leaving the PersonnaPress site or guessing at API details.

## Acceptance Criteria

1. **Given** the route `/headless-blog-api/docs`, **When** it is built, **Then** it lives at `frontend/app/(public)/headless-blog-api/docs/page.tsx`, inherits `PublicHeader`/`PublicFooter` from the `(public)` layout, is statically generated (`export const dynamic = "force-static"`), and renders in the Paper Style design system. No client-side data fetching anywhere on the page.

2. **Given** the page metadata, **When** the static page is generated, **Then** `generateMetadata()` sets:
   - `title`: `{ absolute: "Headless Blog API Reference | PersonnaPress" }` (under 60 chars)
   - `description`: under 160 chars, mentions "delivery token", "endpoints", and "code examples"
   - `alternates.canonical`: `/headless-blog-api/docs`
   - Full OpenGraph (type `website`, reuse the existing OG image approach — static file, no `runtime=edge`)
   - Twitter `summary_large_image`
   - Uses the existing `metadataBase` (Story 8-2 patch)

3. **Given** structured data, **When** the page renders, **Then** it embeds two JSON-LD objects via inline `<script type="application/ld+json">` using `JSON.stringify` (never `dangerouslySetInnerHTML` raw string — use the post-8-1-review pattern from the current `frontend/app/page.tsx`):
   - A `BreadcrumbList` with two items: PersonnaPress home → Headless Blog API → API Reference
   - A `TechArticle` (or `WebPage`) schema with `name`, `description`, `url`, and `author` pointing to PersonnaPress

4. **Given** the page header, **When** rendered, **Then** it shows:
   - A breadcrumb: `← Headless Blog API` linking to `/headless-blog-api` (font-mono text-xs text-graphite, using Lucide `ArrowLeft` icon, aria-label="Back to Headless Blog API overview")
   - An `<h1>` in `font-display text-4xl lg:text-5xl font-bold text-ink text-balance`: "API Reference"
   - An Inter subline (text-graphite, text-pretty): "Complete reference for the PersonnaPress headless blog delivery API. All endpoints, parameters, error codes, and copy-paste integration examples."
   - The header is separated from the two-column body by `border-b border-border`
   - No hero, no CTA, no shadow-brutal in the header — this is a reference page

5. **Given** the two-column layout, **When** rendered on desktop (lg+), **Then** a sticky left sidebar TOC (224px wide, `border-r border-border`) contains an `<nav aria-label="On this page">` with anchor links to all 7 content sections. The sidebar uses `sticky top-20` CSS positioning — no JavaScript required. On mobile (< lg) the sidebar is hidden (`hidden lg:block`) and replaced by a horizontal-scroll pill strip (`<nav aria-label="Jump to section">`) above the first section, with the same 7 links styled as `font-mono text-xs border border-border px-3 py-1.5 whitespace-nowrap` pills.

   TOC sections (in order, with `id` values for anchor targets):
   - `#quickstart` — Quickstart
   - `#authentication` — Authentication
   - `#list-articles` — List Articles
   - `#get-article` — Get Article
   - `#list-tags` — List Tags
   - `#errors` — Error Reference
   - `#caching` — Caching
   - `#examples` — Code Examples

6. **Given** the Quickstart section (`id="quickstart"`), **When** rendered, **Then** it shows a 3-column grid (1-col on mobile) of numbered step cards. Each step card uses `border border-border p-6 bg-paper` — no shadow-brutal, no hover animation. Steps:
   - **Step 01 — Get your token**: "In the app, go to your client → Connections tab → Delivery API section. Click Create token, give it a name, and copy the `ppd_...` value. You will only see the full token once." Include a `<Link href="/dashboard">` with text "Open the app" and Lucide `ExternalLink` icon (aria-hidden).
   - **Step 02 — Call the API**: "Send a GET request to `https://api.personnapress.com/public/v1/articles` with `Authorization: Bearer ppd_your_token` in the header. The response is a paginated JSON object."
   - **Step 03 — Render the result**: "Use `article.html` for the post body and pass the `seo` object fields to your page metadata. The `seo.json_ld` block is ready to embed as-is."

7. **Given** the Authentication section (`id="authentication"`), **When** rendered, **Then** it explains:
   - All requests require `Authorization: Bearer ppd_<token>` header
   - Token prefix is always `ppd_` (delivery token) — do not use session cookies or API keys from the app
   - Missing, revoked, or malformed tokens return `401 INVALID_DELIVERY_TOKEN`
   - A small `TerminalBlock` shows the header: `Authorization: Bearer ppd_abc123def456...`
   - Rate limit: 120 requests per minute per token (keyed on the token's first 8 characters); exceeding returns `429 RATE_LIMIT_EXCEEDED`

8. **Given** the API Reference sections, **When** rendered, **Then** each of the three endpoints is wrapped in an `EndpointBlock` component (local function component in page.tsx) with this consistent structure:
   - **Header bar** (`border-b border-border px-6 py-4 flex items-baseline gap-3`): method badge (`GET` in `border border-success bg-success-muted text-success font-mono text-xs px-2 py-0.5`) + path in `font-mono text-base text-ink` + short description in `text-sm text-graphite`
   - Optional **QUERY PARAMETERS** sub-section with a `ParamTable` (local component, see AC 9)
   - **RESPONSE** sub-section with a `TerminalBlock` showing a realistic JSON example

   Endpoint 1 (`id="list-articles"`): `GET /public/v1/articles`
   - Query params table: `page` (int, default 1, optional), `page_size` (int, 1–50, default 20, optional), `tag` (string, optional, filters by tag), `category` (string, optional, filters by category)
   - Response JSON example showing `{"data": [{slug, title, excerpt, featured_image_url, featured_image_alt, author, tags, category, published_at, updated_at, reading_time_minutes}], "meta": {"page": 1, "page_size": 20, "total": 42}}`
   - **Note clearly**: "The `html` and `seo` fields are not included in list responses. Fetch `GET /public/v1/articles/{slug}` for the full article."

   Endpoint 2 (`id="get-article"`): `GET /public/v1/articles/{slug}`
   - Path param: `slug` (string, required) — the article's URL slug, obtained from the list response
   - Response JSON example showing ALL fields: `slug, title, excerpt, featured_image_url, featured_image_alt, author, tags, category, published_at, updated_at, reading_time_minutes, html` (truncated `"<h2>...</h2><p>...</p>"`), plus `seo: {reading_time_minutes, json_ld: {...}, meta_description: "...", og: {title, description, image}}`
   - Note: `meta_description` and `og` are conditional (present only when the article has those fields populated)
   - 404 returned for: hidden articles, unknown slugs, or articles belonging to another client — all indistinguishable

   Endpoint 3 (`id="list-tags"`): `GET /public/v1/tags`
   - No query params
   - Response JSON: `{"tags": [{"name": "consulting", "count": 12}, ...], "categories": [{"name": "Business", "count": 8}, ...]}`
   - Note: "Use this endpoint to build tag clouds, category nav, or filtered list pages."

9. **Given** the `ParamTable` component (local function component), **When** rendered, **Then** it uses the same brutalist table style as the comparison table on `/headless-blog-api`:
   - `<table className="w-full border-collapse border border-border">`
   - `<caption className="sr-only">` describing the table
   - `<thead>` with `<tr className="bg-ink">` and `<th scope="col">` cells in `text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink`
   - Columns: Parameter, Type, Default, Description
   - `<tbody>` with `<th scope="row">` for the parameter name cell (font-mono text-sm text-ink px-4 py-3 border border-border)
   - Required params get a `font-mono text-[10px] bg-danger-muted text-danger border border-danger px-1.5 py-0.5 ml-2` badge; optional params get `font-mono text-[10px] text-graphite` label
   - No `rounded-*` anywhere — Paper Style

10. **Given** the Error Reference section (`id="errors"`), **When** rendered, **Then** it shows a single 3-column brutalist table (same style as `ParamTable`):
    - Columns: `Error Code`, `HTTP Status`, `When it fires`
    - Rows:
      - `INVALID_DELIVERY_TOKEN` | `401` | Token missing, malformed, revoked, or does not match any active token
      - `ARTICLE_NOT_FOUND` | `404` | Slug does not exist, article is hidden, or belongs to another client
      - `RATE_LIMIT_EXCEEDED` | `429` | More than 120 requests per minute for this token
      - `INTERNAL_ERROR` | `500` | Unexpected server error — retry with exponential backoff
    - Error response shape shown in a `TerminalBlock`: `{"detail": {"error": {"code": "INVALID_DELIVERY_TOKEN", "message": "Missing or invalid delivery token."}}}`

11. **Given** the Caching section (`id="caching"`), **When** rendered, **Then** it explains:
    - All successful responses include `Cache-Control: public, max-age=60, stale-while-revalidate=300` — CDNs and browsers may cache for 60 s and serve stale for up to 300 s while revalidating
    - All responses include an `ETag` header; send it back as `If-None-Match` to receive `304 Not Modified` and save bandwidth
    - A `TerminalBlock` shows the headers:
      ```
      Cache-Control: public, max-age=60, stale-while-revalidate=300
      ETag: W/"a3f9bc12de56f789"
      ```
    - A second `TerminalBlock` shows the Next.js revalidate integration pattern:
      ```ts
      const res = await fetch(`${API}/articles/${slug}`, {
        headers: { Authorization: `Bearer ${TOKEN}` },
        next: { revalidate: 60 },  // ISR: re-fetch at most every 60 s
      });
      ```
    - Note: "401, 404, and 429 responses are sent with `Cache-Control: no-store` and must not be cached."

12. **Given** the Code Examples section (`id="examples"`), **When** rendered, **Then** it shows 5 stacked labeled blocks (same layout as the integration section on `/headless-blog-api`) — each a `TerminalBlock` with a `font-mono text-xs text-graphite tracking-widest uppercase` label above it:

    - **cURL** — full command for both list and detail endpoints with `-H "Authorization: Bearer ppd_..."`, showing `--fail-with-body` flag
    - **Plain fetch** — list and detail calls; includes `if (!res.ok) throw new Error(...)` guard (AC 5 of Story 12.4 review patch — the original FETCH_SAMPLE was patched to add this)
    - **Next.js App Router** — the full pattern from `/headless-blog-api/page.tsx` NEXTJS_SAMPLE but updated to show the list endpoint for a blog index page AND the detail endpoint with `generateStaticParams` + `generateMetadata`
    - **Astro** — updated version of the existing ASTRO_SAMPLE from `/headless-blog-api/page.tsx`, with `!res.ok` guard added
    - **SvelteKit** — `src/routes/blog/[slug]/+page.server.ts` using `load({ params, fetch })` function with `PERSONNAPRESS_TOKEN` from `import.meta.env`

13. **Given** site-wide plumbing, **When** the page ships, **Then**:
    - `frontend/app/sitemap.ts` gains the `/headless-blog-api/docs` route (`changeFrequency: "monthly"`, `priority: 0.7`, `lastModified: new Date()`)
    - `frontend/app/robots.ts` — no change needed (allow: "/" covers it; verify)
    - `frontend/components/marketing/PublicFooter.tsx` — add an "API Docs" link directly below the existing "Headless Blog API" link in the Product column
    - `frontend/app/(public)/headless-blog-api/page.tsx` — add a small "Full API Reference →" text link at the bottom of the Integration section (before the FAQ), linking to `/headless-blog-api/docs`

14. **Given** copy rules, **When** written, **Then** the page source contains zero instances of:
    - Em-dashes (`—`, `&mdash;`, `&#8212;`) — verified by grep
    - Banned marketing words: "elevate", "delve", "unlock", "seamless", "empower", "revolutionary"
    - Emojis anywhere in the page source

15. **Given** accessibility and performance, **When** assessed, **Then**:
    - Single `<h1>` ("API Reference"); all section headings are `<h2>`; param group labels ("QUERY PARAMETERS", "RESPONSE") are `<p>` with `font-mono text-xs uppercase` styling — not headings (they are presentational labels within an endpoint block, not document outline nodes)
    - Breadcrumb nav: `<nav aria-label="Breadcrumb">` with Lucide `ArrowLeft` icon `aria-hidden="true"` on the back link
    - Sidebar nav: `<nav aria-label="On this page">`; mobile pill strip: `<nav aria-label="Jump to section">`
    - All `TerminalBlock` panels: `tabIndex={0}`, `role="region"`, `aria-label` describing the content, `overflow-x-auto`, `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`
    - All tables: `<caption className="sr-only">` + `<th scope="col">` + `<th scope="row">`
    - No client-side data fetching; `npm run build` must show `/headless-blog-api/docs` as `○ (Static)` in build output
    - No Framer Motion on this page — reference pages have no entrance animations

## Tasks / Subtasks

### Task 1: Page scaffold + metadata (AC: 1, 2)

- [ ] 1.1 Create `frontend/app/(public)/headless-blog-api/docs/page.tsx` as a server component with `export const dynamic = "force-static"`. No `<main>` wrapper — the `(public)` layout provides it. Use the same `-mt-8 -mx-4` trick to break out of the layout's `px-4 py-8` padding so the full-width two-column layout has self-contained horizontal control.
- [ ] 1.2 `generateMetadata()` — title absolute (under 60 chars), description (under 160 chars), canonical `/headless-blog-api/docs`, OG (type `website`, static OG image, no `runtime=edge` — same as Story 8-8 patch), Twitter `summary_large_image`. Uses existing `metadataBase`.

### Task 2: Structured data (AC: 3)

- [ ] 2.1 `BreadcrumbList` JSON-LD: 3 items — `{"@id": APP_URL, "name": "PersonnaPress"}`, `{"@id": "${APP_URL}/headless-blog-api", "name": "Headless Blog API"}`, `{"@id": "${APP_URL}/headless-blog-api/docs", "name": "API Reference"}`.
- [ ] 2.2 `TechArticle` JSON-LD: `name: "Headless Blog API Reference"`, `description`, `url: canonical`, `author: {"@type": "Organization", "name": "PersonnaPress"}`.
- [ ] 2.3 Both embedded via inline `<script type="application/ld+json">` with `JSON.stringify()` — match exact pattern in `frontend/app/page.tsx` (post-8-1-review: no `dangerouslySetInnerHTML` raw HTML string injection).

### Task 3: Page header + two-column layout structure (AC: 4, 5)

- [ ] 3.1 Page header: breadcrumb `<nav aria-label="Breadcrumb">` with `<Link href="/headless-blog-api">` containing Lucide `ArrowLeft size-3 aria-hidden` + "Headless Blog API" text. Below: `<h1>` "API Reference" + subline paragraph.
- [ ] 3.2 Desktop sidebar: `<aside className="hidden lg:block w-56 shrink-0 border-r border-border">` containing `<nav aria-label="On this page" className="sticky top-20 p-6">`. Each TOC link: `<a href="#section-id" className="block font-mono text-xs text-graphite hover:text-ink transition-colors py-1.5 focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2">`.
- [ ] 3.3 Mobile pill strip: `<nav aria-label="Jump to section" className="flex gap-3 overflow-x-auto py-3 mb-8 border-b border-border lg:hidden">` with same 7 anchor links as pills (`font-mono text-xs border border-border px-3 py-1.5 whitespace-nowrap hover:text-ink hover:border-ink transition-colors`).
- [ ] 3.4 Content area: `<div className="flex-1 min-w-0 px-6 lg:px-10 py-10">` with `<div className="max-w-3xl space-y-16">` inside to cap line length for readability.

### Task 4: Local component definitions (AC: 8, 9)

- [ ] 4.1 `TerminalBlock` local function component — reuse the exact terminal panel pattern from `/headless-blog-api/page.tsx` (dark `bg-ink`, decorative dots `aria-hidden`, `<pre>` with `tabIndex`, `role="region"`, `aria-label`, `overflow-x-auto`, `focus-visible:ring-2`). Props: `{ content: string; ariaLabel: string }`.
- [ ] 4.2 `ParamTable` local function component. Props: `{ caption: string; rows: { name: string; type: string; defaultVal: string; description: string; required?: boolean }[] }`. Renders the brutalist 4-column table with `bg-ink` header, `<caption className="sr-only">`, `th scope="col"` headers, `th scope="row"` for name cells. Required badge in `danger-muted`, optional label in graphite.
- [ ] 4.3 `EndpointBlock` local function component. Props: `{ id: string; method: string; path: string; description: string; params?: ParamTableRow[]; paramsCaption?: string; responseJson: string; responseAriaLabel: string; children?: React.ReactNode }`. Renders the outer `border border-border`, header bar with method badge + path + description, optional params section, response section.

### Task 5: Quickstart section (AC: 6)

- [ ] 5.1 Section `id="quickstart"`, `<h2>` "Quickstart", 3-column grid (`grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border`). Each step as a `<div className="bg-paper p-6">` — no hover, no shadow, no animation (reference page).
- [ ] 5.2 Step 01: includes `<Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm underline underline-offset-2 hover:text-graphite transition-colors mt-3">Open the app <ExternalLink className="size-3" aria-hidden="true" /></Link>`
- [ ] 5.3 Steps 02 and 03: inline code snippets use `<code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">` — no border-radius.

### Task 6: Authentication section (AC: 7)

- [ ] 6.1 Section `id="authentication"`, `<h2>` "Authentication".
- [ ] 6.2 Prose paragraphs explaining ppd_ prefix, Bearer format, 401 on failure.
- [ ] 6.3 `TerminalBlock` showing just `Authorization: Bearer ppd_abc123def456ghi789jkl012mno345pqr678stu` (realistic length — ppd_ + 43 chars = 47 chars total after prefix).
- [ ] 6.4 Rate limit note: "The API allows 120 requests per minute per token. Exceeding this returns `429 RATE_LIMIT_EXCEEDED`."

### Task 7: API reference — three endpoint blocks (AC: 8, 9)

- [ ] 7.1 `<section id="list-articles">` with `<h2>` "List Articles". `EndpointBlock` with: method GET, path `/public/v1/articles`, 4-param table (page, page_size, tag, category), response JSON. Explicit note (italic or graphite paragraph): "`html` and `seo` are not included in list responses."
- [ ] 7.2 `<section id="get-article">` with `<h2>` "Get Article". `EndpointBlock` with: method GET, path `/public/v1/articles/{slug}`, no params table (just path param note in prose), full response JSON with all fields including `featured_image_alt` (field that was missing from the marketing page showcase — this is the correct reference). Note the conditional `meta_description` and `og` fields.
- [ ] 7.3 `<section id="list-tags">` with `<h2>` "List Tags". `EndpointBlock` with: method GET, path `/public/v1/tags`, no params, simple response JSON. Use-case note about tag clouds / category nav.

### Task 8: Error reference section (AC: 10)

- [ ] 8.1 Section `id="errors"`, `<h2>` "Error Reference".
- [ ] 8.2 3-column `ParamTable` variant (or dedicated `ErrorTable` local component) — columns: Error Code, HTTP Status, When it fires. 4 rows per AC 10.
- [ ] 8.3 `TerminalBlock` showing error response shape.

### Task 9: Caching section (AC: 11)

- [ ] 9.1 Section `id="caching"`, `<h2>` "Caching".
- [ ] 9.2 Two prose paragraphs: Cache-Control explanation, ETag / If-None-Match explanation.
- [ ] 9.3 `TerminalBlock` with response headers example.
- [ ] 9.4 `TerminalBlock` with Next.js `next: { revalidate: 60 }` pattern (TypeScript).
- [ ] 9.5 Note about `no-store` on error responses.

### Task 10: Code examples section (AC: 12)

- [ ] 10.1 Section `id="examples"`, `<h2>` "Code Examples". Subline: "Copy-paste samples for common environments. The endpoint URL and header format are the same in every language."
- [ ] 10.2 cURL block — shows list endpoint call with `--fail-with-body` and `--silent` flags.
- [ ] 10.3 Plain fetch block — shows list call (index page pattern) AND detail call, both with `if (!res.ok) throw new Error(...)` guard.
- [ ] 10.4 Next.js App Router block — `generateStaticParams` (fetching all slugs from list) + `generateMetadata` (passing `seo.meta_description`, `seo.og`) + default export page component with `next: { revalidate: 60 }`. TypeScript.
- [ ] 10.5 Astro block — updated from marketing page sample; add `if (!res.ok)` guard; add `featured_image_alt` in img alt attribute.
- [ ] 10.6 SvelteKit block — `+page.server.ts` with `load` function, `import.meta.env.PERSONNAPRESS_TOKEN`, null check returning `{ status: 404 }` on failed fetch.

### Task 11: Site plumbing + cross-linking (AC: 13)

- [ ] 11.1 `frontend/app/sitemap.ts`: add `/headless-blog-api/docs` entry (`changeFrequency: "monthly"`, `priority: 0.7`). Keep existing trailing-slash guard pattern.
- [ ] 11.2 `frontend/app/robots.ts`: verify `/headless-blog-api/docs` is allowed by `allow: "/"`. No change needed if so.
- [ ] 11.3 `frontend/components/marketing/PublicFooter.tsx`: add `<Link href="/headless-blog-api/docs">API Docs</Link>` directly after the existing "Headless Blog API" link in the Product column (`font-mono text-xs text-graphite hover:text-ink transition-colors`).
- [ ] 11.4 `frontend/app/(public)/headless-blog-api/page.tsx`: in the Integration section (`aria-label="Integration examples"`), after the 3 code blocks and before the next `<div className="border-t border-border" />`, add a small footer line: `<p className="font-mono text-xs text-graphite mt-6"><Link href="/headless-blog-api/docs" className="underline underline-offset-2 hover:text-ink transition-colors">Full API Reference including all endpoints, error codes, and caching →</Link></p>`

### Task 12: Copy + accessibility pass (AC: 14, 15)

- [ ] 12.1 Grep page source for `—`, `&mdash;`, `&#8212;`: zero hits required.
- [ ] 12.2 Grep for banned words ("elevate", "delve", "unlock", "seamless", "empower", "revolutionary"): zero hits.
- [ ] 12.3 Verify: single `<h1>`, all sections have `<h2>`, param labels are `<p>` not `<h3>`.
- [ ] 12.4 Verify all `TerminalBlock` instances have unique, descriptive `aria-label` values.
- [ ] 12.5 Verify all tables have `<caption className="sr-only">`, `th scope="col"`, `th scope="row"`.
- [ ] 12.6 `npm run build` — `/headless-blog-api/docs` must appear as `○ (Static)`.

## Dev Notes

### Architecture: Page vs Component File Structure

This is a single-file page following the github-publisher and headless-blog-api precedent. All local components (`TerminalBlock`, `ParamTable`, `EndpointBlock`) are defined as function components within `page.tsx`. Do NOT create separate files in `components/` for these — they are page-internal and have no reuse outside this file. Extract to a separate file only if the file exceeds ~800 lines; even then, prefer a co-located `_components.tsx` in the same directory.

### Critical: Layout Interaction

The `(public)` layout renders:
```tsx
<main className="flex-1 px-4 py-8">
  {children}
</main>
```

The page MUST use `-mt-8 -mx-4` on its outermost wrapper to cancel this padding, then apply its own `max-w-7xl mx-auto px-6` for the header, and `flex` (sidebar + content) for the body. This is the established pattern — see `frontend/app/(public)/headless-blog-api/page.tsx` line 356.

The two-column body wrapper:
```tsx
<div className="max-w-7xl mx-auto flex">
  <aside className="hidden lg:block w-56 shrink-0 border-r border-border">...</aside>
  <div className="flex-1 min-w-0 px-6 lg:px-10 py-10">
    <div className="max-w-3xl space-y-16">
      {/* all sections */}
    </div>
  </div>
</div>
```

### Critical: Sticky Sidebar — CSS Only

The TOC sidebar uses `sticky top-20` (Tailwind). This requires the parent (`<aside>`) to NOT have `overflow: hidden` or `overflow: auto`. The `max-w-7xl flex` wrapper must have `overflow: visible` (the default). Do not add any overflow utilities to the flex container.

`top-20` = 80px from viewport top, which clears the fixed `PublicHeader` (verify header height; if PublicHeader is 64px/`h-16`, use `top-16`; if it's not fixed/sticky itself, `top-8` may be enough — check `frontend/components/marketing/PublicHeader.tsx` before setting this value).

### Critical: TerminalBlock — Exact Pattern Reuse

Copy the terminal panel pattern exactly from `frontend/app/(public)/headless-blog-api/page.tsx` lines 456–473 (the API response showcase). Do NOT simplify or restyle. The `rounded-full` dots are intentional Paper Style irony (brutalist frame, rounded decorative elements). The focus ring must be `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`.

### Critical: featured_image_alt Field

The marketing page JSON showcase (`EXAMPLE_RESPONSE` in headless-blog-api/page.tsx) does NOT include `featured_image_alt`. The real API DOES return this field (see `backend/app/routers/public_articles.py:_article_list_item()` line 200 — `"featured_image_alt": article.featured_image_alt`). The developer docs page MUST include it in both the list endpoint and detail endpoint response examples. This is a documentation accuracy fix, not a backend change.

### Critical: No Nested `<main>` Tag

The `(public)` layout provides the `<main>` element. The headless-blog-api page.tsx uses `<main className="-mt-8 -mx-4">` which creates a nested main — that's a semantic error that was inherited from the original implementation. The **docs page must NOT repeat this mistake**. The outermost element returned from the page component should be a `<>` fragment or a `<div>`, not `<main>`.

Example correct structure:
```tsx
export default function HeadlessBlogApiDocsPage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={...} />
      <script type="application/ld+json" dangerouslySetInnerHTML={...} />
      <div className="-mt-8 -mx-4">
        {/* header */}
        {/* two-column layout */}
        {/* CTA strip */}
      </div>
    </>
  );
}
```

Wait — the JSON-LD injection pattern requires clarification. Read the current `frontend/app/page.tsx` to see the exact post-8-1 pattern before implementing. The 8-1 review removed `dangerouslySetInnerHTML` raw string injection. Verify the current pattern used. If it now uses `JSON.stringify` inside `dangerouslySetInnerHTML={{ __html: JSON.stringify(obj) }}`, that IS safe (it serializes a JS object, not a raw string). The banned pattern was concatenating raw user-controlled strings.

### Previous Story Intelligence (12-4)

From Story 12.4 review findings — these patches apply equally to this page:
- `<ol list-none>` needs `role="list"` for VoiceOver/Safari: if any ordered list with `list-style: none` appears on this page, add `role="list"` on the `<ol>` and `role="listitem"` is implied
- FAQ "What fields does the API response include?" answer in the marketing page was patched to clarify conditional `meta_description`/`og` — the docs page must be accurate about the same fields
- NEXTJS_SAMPLE was patched with optional chaining: `article.seo.meta_description && {...}` and `article.seo.og && {...}` — apply this in the Next.js code example here too
- FETCH_SAMPLE was patched to add `if (!res.ok) throw new Error(...)` — all code examples on this page must include this guard

From Story 12.2:
- `featured_image_alt` is a field in `_article_list_item()` — include in all response examples
- Error shape: `{"detail": {"error": {"code": "...", "message": "..."}}}` — the error table must show this wrapping structure
- Rate limit is keyed on the first 8 chars of the token prefix (not the full token) — mention this in the rate limit note if useful

### PublicHeader Height Check

Before setting the sticky `top-X` value on the sidebar, read `frontend/components/marketing/PublicHeader.tsx` to confirm whether it is sticky/fixed and its height. Set `top` to clear the header. If the header is `h-16` (64px) and sticky, use `sticky top-16`; add 8px buffer → `sticky top-20` is safe.

### Sitemap Trailing-Slash Guard

The sitemap uses the trailing-slash guard pattern from Story 9-1 review. When adding `/headless-blog-api/docs`, apply the same guard: `url: \`\${baseUrl}/headless-blog-api/docs\`` (no trailing slash, matches the canonical).

### Copy: Inline Code Style

All inline code references (endpoint paths, field names, header names, error codes) within prose must use:
```tsx
<code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
  {content}
</code>
```
No `rounded-*` — Paper Style. This is different from the `<pre><code>` inside TerminalBlocks.

### No Framer Motion

This is a static reference page. Zero animation. Do not import or use `framer-motion` anywhere. The existing Paper Style has `globals.css` animations (`fade-in-up`, etc.) — do not apply these either. The page should render instantly with no motion.

### Project Structure Notes

- New file: `frontend/app/(public)/headless-blog-api/docs/page.tsx`
- Modified: `frontend/app/sitemap.ts`
- Modified: `frontend/components/marketing/PublicFooter.tsx`
- Modified: `frontend/app/(public)/headless-blog-api/page.tsx` (add cross-link to docs)
- No backend changes in this story

### References

- [Source: backend/app/routers/public_articles.py — `_article_list_item()`, `_build_seo()`, rate limiter, error shapes, endpoint paths]
- [Source: frontend/app/(public)/headless-blog-api/page.tsx — TerminalBlock pattern, comparison table style, layout `-mt-8 -mx-4` trick, JSON-LD injection]
- [Source: _bmad-output/implementation-artifacts/12-4-headless-blog-api-cluster-page.md — review findings (ASTRO_SAMPLE og null guard, FETCH_SAMPLE res.ok guard, ol role=list, ol role=list, NEXTJS_SAMPLE optional chaining)]
- [Source: _bmad-output/implementation-artifacts/12-2-public-delivery-api-tokens.md — complete endpoint spec, error codes, auth dependency]
- [Source: frontend/app/sitemap.ts — trailing-slash guard, existing entries]
- [Source: frontend/components/marketing/PublicFooter.tsx — Product column, existing link pattern]
- [Source: frontend/app/page.tsx — JSON-LD injection pattern (post-8-1-review)]
- [Source: frontend/app/globals.css — design tokens (colors, fonts, shadow-brutal, paper-texture)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

### Review Findings

- [x] [Review][Patch] Meta description 163 chars exceeds 160-char limit (AC 2) [docs/page.tsx:13]
- [x] [Review][Patch] SvelteKit error guard `return { status: 404 }` is not valid SvelteKit — load fn returns data not HTTP status, causing crash in template when article is undefined (AC 12) [docs/page.tsx:305]
- [x] [Review][Patch] NEXTJS_SAMPLE params typed as `{ slug: string }` not `Promise<{ slug: string }>` — deprecated in Next.js 15+ (project is Next.js 16.2.9), produces warnings/errors (AC 12) [docs/page.tsx:224]
- [x] [Review][Defer] www vs no-www fallback URL mismatch between docs/page.tsx (www.personnapress.com) and sitemap.ts (personnapress.com) — deferred, pre-existing pattern across codebase
- [x] [Review][Defer] TerminalBlock focus ring `ring-ink` on `bg-ink` background may be invisible (WCAG) — deferred, pre-existing pattern copied from parent headless-blog-api/page.tsx
- [x] [Review][Defer] Parent page `headless-blog-api/page.tsx` ASTRO_SAMPLE missing `res.ok` guard — deferred, pre-existing code not modified by this story
- [x] [Review][Defer] Sitemap `lastModified: new Date()` marks page modified on every deploy — deferred, pre-existing pattern across all sitemap entries
