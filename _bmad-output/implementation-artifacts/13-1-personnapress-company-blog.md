---
baseline_commit: add2b7762a1bb9e42848b4ac0353c602b51e5643
---

# Story 13.1: PersonnaPress Company Blog (ISR, Headless Delivery)

Status: done

## Story

As a PersonnaPress visitor researching AI content tools,
I want to read the PersonnaPress company blog at `/blog`,
so that I can discover insights on brand voice, content strategy, and AI writing while seeing the product's own headless API in action.

## Acceptance Criteria

1. **Given** the route `/blog`, **When** built, **Then** it lives at `frontend/app/(public)/blog/page.tsx`, inherits `PublicHeader`/`PublicFooter` from the `(public)` layout, uses `export const revalidate = 3600` (ISR — NOT `force-static`), and renders in the Paper Style design system.

2. **Given** the route `/blog/[slug]`, **When** built, **Then** it lives at `frontend/app/(public)/blog/[slug]/page.tsx`, uses `export const revalidate = 3600`, exports `generateStaticParams()` that pre-generates slugs for the first 50 published articles (returns `[]` safely if the env var is absent or the API is unreachable), and `dynamicParams = true` (default) allows new slugs to be rendered on first request.

3. **Given** the list page, **When** rendered, **Then** it displays:
   - A hero with a `font-mono` eyebrow label "THE BLOG", a Playfair H1, and a descriptive Inter subhead.
   - The first article as a featured full-width card: `md:grid-cols-2` (image + content side-by-side), Playfair title, excerpt, mono meta (author · date · reading time), "Read article" link.
   - Remaining articles in a `grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-border border border-border` grid (border trick creates 1px gutters between cards), each `bg-paper group hover:bg-highlight transition-colors`.
   - An empty state ("Nothing published yet.") when the article list is empty.
   - URL-based pagination (`?page=N`) via prev/next Paper-style buttons when `meta.total > meta.page_size`.

4. **Given** the detail page, **When** rendered for a valid published slug, **Then** it displays:
   - A back link "← Blog" (`ArrowLeft` Lucide icon, `text-sm text-graphite hover:text-ink`).
   - Category/tag mono label, Playfair H1 (`text-4xl md:text-5xl text-balance`), meta bar (`author · formatted date · N min read` in `font-mono text-xs text-graphite`).
   - Featured image (if `featured_image_url` is present) in a `border border-border overflow-hidden` wrapper using `next/image` with `priority`.
   - The full article HTML rendered in the Paper-style prose class set: `prose prose-sm md:prose-base max-w-none font-sans text-ink prose-headings:font-display prose-headings:text-ink prose-a:text-ink prose-a:underline prose-img:border prose-img:border-border`. The HTML is sourced from the API, which already strips `<script>` and `<style>` tags; render directly without an additional client-side sanitizer.
   - A "Back to Blog" link at the bottom of the article.

5. **Given** SEO on the list page, **When** `generateMetadata()` runs, **Then** it returns title `"Blog | PersonnaPress"`, meta description `"Insights on AI writing, brand voice, and content strategy from the PersonnaPress team."`, canonical `/blog`, and standard OpenGraph/Twitter fields reusing the existing OG image approach (static image, no `runtime=edge`).

6. **Given** SEO on the detail page, **When** `generateMetadata()` runs for a valid slug, **Then** it returns:
   - `title`: `article.title + " | PersonnaPress Blog"` (trim to ≤70 chars if needed).
   - `description`: `article.seo.meta_description ?? article.excerpt` (fallback order).
   - `canonical`: `/blog/${article.slug}`.
   - `openGraph.title/description`: from `article.seo.og.title` / `article.seo.og.description` (with fallback to `article.title` / `article.excerpt`).
   - `openGraph.images`: `article.seo.og?.image ?? article.featured_image_url` (skip `images` key entirely if both are absent — do NOT pass a null/undefined value to Next.js metadata).
   - `twitter.card`: `"summary_large_image"`.

7. **Given** structured data on the detail page, **When** the page renders, **Then** it injects the `article.seo.json_ld` object verbatim via `<script type="application/ld+json">{JSON.stringify(article.seo.json_ld)}</script>` (use the same safe inline-script pattern as the existing landing pages — avoid `dangerouslySetInnerHTML` per the 8-1 review patch; use the current pattern from `frontend/app/page.tsx`).

8. **Given** the `PublicHeader`, **When** the blog ships, **Then** a "Blog" nav link pointing to `/blog` is added between "FAQ" and "Start Free Trial" using the same `text-sm text-graphite hover:text-ink transition-colors` class as existing nav items.

9. **Given** site plumbing, **When** the pages ship, **Then**:
   - `frontend/app/sitemap.ts`: add `/blog` (changeFrequency `weekly`, priority 0.9) and, optionally, the first 50 article slugs at `/blog/{slug}` (changeFrequency `weekly`, priority 0.7). If the fetch fails, omit article URLs gracefully.
   - `frontend/app/robots.ts`: `/blog` is already covered by `allow: "/"` — no change needed.
   - `frontend/components/marketing/PublicFooter.tsx`: add a "Blog" link in the existing product links section (alongside "Headless Blog API" and "GitHub Publisher").

10. **Given** accessibility, **When** assessed, **Then**:
    - Featured image in detail page has descriptive `alt` text (use `article.title` as fallback).
    - Card images have `alt={article.title}`.
    - Pagination buttons have `aria-label="Go to previous page"` / `aria-label="Go to page N"`.
    - Single H1 per page. No heading hierarchy skips.
    - `text-balance` on all headings, `text-pretty` on body paragraphs.
    - All interactive elements have `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`.
    - Card hover animation uses CSS only (`transition-colors`), no Framer Motion (too many simultaneous instances).

11. **Given** the API env var, **When** `PERSONNAPRESS_DELIVERY_TOKEN` is missing at build time (e.g., CI without secrets), **Then** both pages degrade gracefully: list page renders the empty state, detail page returns `notFound()`, and `generateStaticParams` returns `[]`. No uncaught exception or build failure.

## Tasks / Subtasks

### Task 1: Epic 13 registration + env var (AC: 11)

- [ ] 1.1 Add `PERSONNAPRESS_DELIVERY_TOKEN=` to `frontend/.env.local.example` with a comment: `# Delivery token for the PersonnaPress company blog (create one in Settings → API Tokens)`.
- [ ] 1.2 Add Epic 13 to `_bmad-output/planning-artifacts/epics.md` (brief 3-line summary: "Company blog powered by the PersonnaPress headless API; showcases the product by dogfooding it").
- [ ] 1.3 Do NOT add any new backend files. All data comes from the public delivery API.

### Task 2: Blog list page (AC: 1, 3, 5, 10, 11)

- [ ] 2.1 Create `frontend/app/(public)/blog/page.tsx` as a server component.
  - `export const revalidate = 3600;` — do NOT use `force-static`.
  - Accept `searchParams: Promise<{ page?: string }>` (Next.js 16 async searchParams).
  - Parse `page = Math.max(1, parseInt(searchParams.page ?? '1', 10))`.
  - Call `fetchArticles(page)` — a module-level async function that calls `GET https://api.personnapress.com/public/v1/articles?page=${page}&page_size=9` with `Authorization: Bearer ${process.env.PERSONNAPRESS_DELIVERY_TOKEN}` and `next: { revalidate: 3600 }`. On missing env var or non-OK response, return `{ data: [], meta: { page: 1, page_size: 9, total: 0 } }` — never throw.

- [ ] 2.2 Hero section:
  ```
  <section class="max-w-6xl mx-auto px-6 pt-20 pb-12">
    <p class="font-mono text-xs text-graphite uppercase tracking-widest mb-4">The Blog</p>
    <h1 class="font-display text-5xl md:text-6xl font-bold text-ink text-balance leading-tight">
      Ideas on AI, brand voice, and content that sounds like you.
    </h1>
    <p class="mt-6 text-graphite max-w-2xl text-pretty leading-relaxed">
      Practical writing on AI-generated content, brand voice strategy, and publishing — from the team building PersonnaPress.
    </p>
    <div class="border-t border-border mt-12" />
  </section>
  ```

- [ ] 2.3 Featured article card (first item, `articles.data[0]` if present):
  - Outer: `border border-border bg-paper` full-width card, `md:grid md:grid-cols-2` layout.
  - Image side (if `featured_image_url`): `relative overflow-hidden`, `<Image>` with `fill`, `objectFit: "cover"`, `min-h-[240px]`, `alt={article.title}`. If no image, show a `bg-highlight` placeholder panel.
  - Content side: `p-8 md:p-12 flex flex-col justify-center`.
    - Category: `font-mono text-xs text-graphite uppercase tracking-widest mb-4` (use `article.category ?? article.tags?.[0] ?? 'General'`).
    - Title: `font-display text-3xl md:text-4xl font-bold text-ink text-balance leading-snug mb-4`.
    - Excerpt: `text-graphite text-pretty leading-relaxed mb-6 line-clamp-4`.
    - Meta: `font-mono text-xs text-graphite mb-6` — `{article.author} · {formatted date} · {article.reading_time_minutes} min read`.
    - CTA link: `<Link href={/blog/${article.slug}}>Read article <ArrowRight /></Link>` — `inline-flex items-center gap-2 text-sm font-medium text-ink border-b border-ink pb-0.5 hover:border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`.

- [ ] 2.4 Article grid (remaining items, `articles.data.slice(1)`):
  - Container: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-border border border-border mt-px`.
  - Each card `<Link href={/blog/${a.slug}}>` wrapping an `<article>`:
    - `bg-paper group hover:bg-highlight transition-colors flex flex-col h-full`.
    - Image (if `featured_image_url`): `relative overflow-hidden aspect-video` with `<Image fill objectFit="cover" alt={a.title}>`. No image = no placeholder (keep card compact).
    - Content: `p-6 flex flex-col flex-1`.
      - Category mono label.
      - Title: `font-display text-xl font-bold text-ink text-balance leading-snug mt-2 mb-3`.
      - Excerpt: `text-sm text-graphite text-pretty leading-relaxed line-clamp-3 flex-1`.
      - Meta: `font-mono text-xs text-graphite mt-4`.
      - Arrow: `mt-4 self-end` — `<ArrowRight class="size-4 text-graphite group-hover:text-ink transition-colors" aria-hidden="true">`.
    - CSS stagger entrance — use inline style `animationDelay` with a module-level `@keyframes card-in` (or use Tailwind's `animate-in` class if available). Do NOT use Framer Motion.

- [ ] 2.5 Empty state (when `articles.data.length === 0`):
  ```
  <div class="py-32 text-center max-w-6xl mx-auto px-6">
    <h2 class="font-display text-3xl font-bold text-ink mb-4">Nothing published yet.</h2>
    <p class="text-graphite">New articles will appear here as soon as they are published.</p>
  </div>
  ```

- [ ] 2.6 Pagination (when `meta.total > meta.page_size`):
  - Render below the grid: `<nav aria-label="Blog pagination" class="flex items-center justify-center gap-2 mt-12 mb-20">`.
  - Prev button: `<Link href="/blog?page=${page-1}">` — disabled (no href, `aria-disabled="true"`, `opacity-40 pointer-events-none`) when `page === 1`.
  - Page numbers: show up to 5 page numbers centered on current page. Each: `border border-border px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-paper transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`. Current page: `bg-ink text-paper border-ink`.
  - Next button: similarly disabled when on last page.
  - `aria-label="Go to page N"` on each page button; `aria-label="Go to previous page"` / `"Go to next page"` on prev/next.
  - `aria-current="page"` on the active page link.

- [ ] 2.7 `generateMetadata()` for list page (AC 5).

### Task 3: Blog detail page (AC: 2, 4, 6, 7, 10, 11)

- [ ] 3.1 Create `frontend/app/(public)/blog/[slug]/page.tsx` as a server component.
  - `export const revalidate = 3600;`
  - `export const dynamicParams = true;` (explicit, documents intent).
  - `generateStaticParams()`: call `GET /public/v1/articles?page_size=50`, return `data.map(a => ({ slug: a.slug }))`. Wrap entire function in try/catch — on any error return `[]`.
  - `fetchArticle(slug)`: call `GET https://api.personnapress.com/public/v1/articles/${encodeURIComponent(slug)}` with the same auth header and `next: { revalidate: 3600 }`. On 404 or non-OK response, return `null`.
  - In the page component: if `fetchArticle` returns `null`, call `notFound()` (import from `next/navigation`).

- [ ] 3.2 Back nav:
  ```
  <div class="max-w-3xl mx-auto px-6 pt-12">
    <Link href="/blog" class="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-sm">
      <ArrowLeft class="size-4" aria-hidden="true" /> Blog
    </Link>
  </div>
  ```

- [ ] 3.3 Article header:
  ```
  <header class="max-w-3xl mx-auto px-6 pt-8 pb-10">
    <p class="font-mono text-xs text-graphite uppercase tracking-widest mb-4">
      {article.category ?? article.tags?.[0] ?? 'Article'}
    </p>
    <h1 class="font-display text-4xl md:text-5xl font-bold text-ink text-balance leading-tight">
      {article.title}
    </h1>
    <div class="flex items-center gap-3 font-mono text-xs text-graphite mt-6 flex-wrap">
      <span>{article.author}</span>
      <span aria-hidden="true">·</span>
      <time dateTime={article.published_at}>{formatDate(article.published_at)}</time>
      <span aria-hidden="true">·</span>
      <span>{article.reading_time_minutes} min read</span>
    </div>
  </header>
  ```

- [ ] 3.4 Featured image (if `article.featured_image_url`):
  ```
  <div class="max-w-4xl mx-auto px-6 mb-12">
    <div class="border border-border overflow-hidden relative aspect-video">
      <Image src={article.featured_image_url} alt={article.title} fill style={{ objectFit: 'cover' }} priority />
    </div>
  </div>
  ```
  If no featured image: omit entirely (no placeholder — the typography carries the page on its own).

- [ ] 3.5 Article body:
  ```
  <div class="max-w-3xl mx-auto px-6 pb-16">
    <div
      class="prose prose-sm md:prose-base max-w-none font-sans text-ink
             prose-headings:font-display prose-headings:text-ink prose-headings:font-bold
             prose-a:text-ink prose-a:underline prose-a:underline-offset-2
             prose-img:border prose-img:border-border prose-img:rounded-none
             prose-blockquote:border-l-ink prose-blockquote:text-graphite
             prose-code:bg-highlight prose-code:text-ink prose-code:px-1 prose-code:rounded-none"
      dangerouslySetInnerHTML={{ __html: article.html }}
    />
  </div>
  ```
  The `article.html` is already sanitized by the public API (`_strip_scripts` + regex). Since this is a server component rendering our own content, no additional client sanitizer is needed. Note this explicitly in a code comment for future readers.

- [ ] 3.6 Bottom nav:
  ```
  <div class="max-w-3xl mx-auto px-6 pb-24 border-t border-border pt-8 mt-4">
    <Link href="/blog" class="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors">
      <ArrowLeft class="size-4" aria-hidden="true" /> Back to Blog
    </Link>
  </div>
  ```

- [ ] 3.7 `generateMetadata()` — implement per AC 6. Helper `formatDate(iso: string): string` — use `new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(iso))`. Since the detail page is ISR (not force-static), `new Date()` is safe inside `generateMetadata` (it runs at revalidation time, not per-request).

- [ ] 3.8 JSON-LD — if `article.seo?.json_ld` is present, inject using the safe inline script pattern from `frontend/app/page.tsx` (read that file before implementing to copy the exact approach post the 8-1 review patch that removed `dangerouslySetInnerHTML` for JSON-LD).

### Task 4: Site plumbing (AC: 8, 9)

- [ ] 4.1 `frontend/components/marketing/PublicHeader.tsx`: add `<Link href="/blog" className="text-sm text-graphite hover:text-ink transition-colors">Blog</Link>` between the FAQ anchor and the "Start Free Trial" button.

- [ ] 4.2 `frontend/app/sitemap.ts`: add `/blog` entry. Optionally fetch article slugs for individual entries:
  ```ts
  // Fetch article slugs for sitemap — graceful fallback on failure
  async function getBlogSlugs(): Promise<string[]> {
    try {
      const token = process.env.PERSONNAPRESS_DELIVERY_TOKEN;
      if (!token) return [];
      const res = await fetch('https://api.personnapress.com/public/v1/articles?page_size=50', {
        headers: { Authorization: `Bearer ${token}` },
        next: { revalidate: 86400 },
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.data.map((a: { slug: string }) => a.slug);
    } catch {
      return [];
    }
  }
  ```
  Make `sitemap()` `async` and include the results. Keep the trailing-slash guard pattern from the 9-1 review patch.

- [ ] 4.3 `frontend/components/marketing/PublicFooter.tsx`: add "Blog" link alongside existing product links (Headless Blog API, GitHub Publisher).

### Task 5: Verification (AC: all)

- [ ] 5.1 Run `npm run build` from `frontend/`. Confirm `/blog` and `/blog/[slug]` (at least one pre-generated slug) appear in build output as ISR pages (not Static `○`), i.e., shown as `◐` or with revalidate annotation.
- [ ] 5.2 With `PERSONNAPRESS_DELIVERY_TOKEN` unset, confirm build succeeds, `/blog` shows empty state, `/blog/some-slug` returns 404.
- [ ] 5.3 Confirm `PublicHeader` "Blog" link renders on all public pages (header is in layout).
- [ ] 5.4 Grep for em-dashes (`—`), banned words (elevate, delve, unlock), and emojis: zero hits in the new files.
- [ ] 5.5 Verify heading hierarchy: H1 on list page (blog title); H1 on detail page (article title). No H2+ before H1. No heading skips.

### Review Findings

- [x] [Review][Patch] JSON-LD XSS: JSON.stringify doesn't escape `</script>` — add `.replace(/</g, '\\u003c')` [`[slug]/page.tsx:135`]
- [x] [Review][Patch] fetchArticles response shape unvalidated — `articles.data[0]` crashes if API returns unexpected shape [`blog/page.tsx:42`]
- [x] [Review][Patch] Featured article image missing `priority` prop — LCP regression [`blog/page.tsx:133`]
- [x] [Review][Patch] NaN page parameter: `Math.max(1, NaN)` = NaN when `?page=abc` [`blog/page.tsx:90`]
- [x] [Review][Patch] Division by zero: `page_size=0` causes `totalPages=Infinity` [`blog/page.tsx:92`]
- [x] [Review][Patch] Out-of-bounds `?page=N` beyond totalPages shows confusing empty state [`blog/page.tsx:92`]
- [x] [Review][Patch] `formatDate` throws RangeError on invalid/null `published_at` [`blog/page.tsx:48`, `[slug]/page.tsx:112`]
- [x] [Review][Patch] `fetchArticle` response shape unvalidated — `article.html` may be undefined [`[slug]/page.tsx:45`]
- [x] [Review][Patch] Detail page `twitter` object omits `title`/`description` [`[slug]/page.tsx:106`]
- [x] [Review][Patch] `generateMetadata` returns stub title instead of `notFound()` when token absent (AC11) [`[slug]/page.tsx:75`]
- [x] [Review][Patch] Bottom "Back to Blog" link missing `rounded-sm` — inconsistent focus ring [`[slug]/page.tsx:200`]
- [x] [Review][Patch] `getBlogSlugs` doesn't filter null/empty slugs — malformed sitemap URLs [`sitemap.ts`]
- [x] [Review][Patch] `.env.local.example` token comment doesn't clarify read-only delivery scope [`.env.local.example`]
- [x] [Review][Patch] `article.excerpt` undefined propagates into OG description [`[slug]/page.tsx:79,81`]
- [x] [Review][Defer] Hardcoded `API_BASE` string across 3 files [`blog/page.tsx`, `[slug]/page.tsx`, `sitemap.ts`] — deferred, pre-existing pattern
- [x] [Review][Defer] Sitemap `lastModified: new Date()` instead of `updated_at` [`sitemap.ts`] — deferred, pre-existing pattern
- [x] [Review][Defer] `updated_at` in TypeScript interfaces but never rendered [`blog/page.tsx`, `[slug]/page.tsx`] — deferred, housekeeping
- [x] [Review][Defer] Revalidate mismatch: pages use 3600, sitemap uses 86400 — deferred, design decision

## Dev Notes

### Why ISR, not `force-static`

`force-static` builds the page once at deploy time and never updates — new articles would require a full redeploy. `revalidate = 3600` (ISR) serves the cached static page from CDN edge (fast TTFB, good LCP/Core Web Vitals) and regenerates in the background every hour. This is the right balance for a blog.

### RSC re-render loop and the data cache

The `project-context.md` RSC loop warning applies to `cache: 'no-store'` fetches inside server components. The blog pages use `next: { revalidate: 3600 }`, which stores the API response in Next.js's persistent Data Cache. Even if Turbopack re-renders the RSC in dev mode, the cached response is returned immediately — no flood of requests to `api.personnapress.com`. This is a safe pattern.

In dev mode the Data Cache behaviour differs from production; you may see a fresh API call on first load but not on subsequent re-renders. This is expected.

### API surface used

```
GET https://api.personnapress.com/public/v1/articles
  ?page=N&page_size=9[&tag=...][&category=...]
  Authorization: Bearer ppd_...
  → { data: ArticleListItem[], meta: { page, page_size, total } }

GET https://api.personnapress.com/public/v1/articles/{slug}
  Authorization: Bearer ppd_...
  → ArticleDetail (all list fields + html + seo)
```

Field reference (from `backend/app/routers/public_articles.py` `_article_list_item` + `_build_seo`):

```ts
// List item
{ slug, title, excerpt, featured_image_url, author, tags, category,
  published_at, updated_at, reading_time_minutes }

// Detail (all of the above plus):
{ html,
  seo: {
    reading_time_minutes,
    meta_description?,   // nullable — use article.excerpt as fallback
    og?: { title, description, image },  // entire og key may be absent
    json_ld: { ... }    // ready-to-embed Article schema.org object
  }
}
```

`seo.og` is conditionally absent — **always use optional chaining** (`article.seo?.og?.title`). Do NOT assume it's present. Same for `seo.meta_description`. The 12-4 review patches caught this exact bug.

### Delivery token setup (manual step before deploy)

The dev agent cannot create a delivery token — Boris must do this manually:
1. Log into PersonnaPress, switch to the client that holds the company blog articles.
2. Go to Settings → API Tokens → Create token → name it "Company Blog".
3. Copy the `ppd_...` token and add it to Vercel env vars as `PERSONNAPRESS_DELIVERY_TOKEN`.
4. Add the same to `.env.local` for local development.

This is a one-time step. The token is production-grade (rate-limited at 120 req/min, scoped to one client).

### CSS stagger animation for cards

Do NOT use Framer Motion for the article grid cards — too many simultaneous instances. Use CSS only:

```css
/* In the component file as a <style> tag, or via Tailwind arbitrary animation */
@keyframes card-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

Apply via inline style per card:
```tsx
style={{
  animation: 'card-in 0.35s ease-out both',
  animationDelay: `${index * 60}ms`,
}}
```

Wrap in `@media (prefers-reduced-motion: no-preference)` — use a CSS class to gate it:
```tsx
className="[animation:none] motion-safe:[animation:card-in_0.35s_ease-out_both]"
```
Then apply the delay inline. This respects `prefers-reduced-motion`.

### Paper Style design system constraints

- No glassmorphism, no `backdrop-blur`, no `rounded-*` (use `rounded-none` explicitly if a reset is needed).
- Colors: `bg-paper` (off-white), `text-ink` (near-black), `text-graphite` (mid-grey), `bg-highlight` (pale yellow), `border-border` (light grey).
- Typography: `font-display` = Playfair Display (headings), `font-sans` = Inter (body), `font-mono` = JetBrains Mono (labels/code).
- Box shadows: 4px offset hard shadow (`shadow-brutal`) for CTAs only.
- No Framer Motion on list/grid items. CSS transitions only.
- No emojis, no AI-trope copy ("elevate", "delve", "unlock", "seamless", "empower").

### JSON-LD safe injection pattern

Read `frontend/app/page.tsx` to find the current post-8-1-review JSON-LD injection pattern before implementing. The 8-1 review removed `dangerouslySetInnerHTML` for JSON-LD — copy whatever pattern is currently in use there.

### `dangerouslySetInnerHTML` for article body

The article HTML comes from PersonnaPress's own API, which runs `_strip_scripts()` (strips `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<noscript>` via regex). Since this is a server component rendering our own content from our own API:
- Additional sanitization (e.g., `sanitize-html`) is not required.
- Leave a code comment: `{/* HTML sanitized by public API _strip_scripts(); safe to render as-is */}`.
- If a future story moves this to a client component, DOMPurify must be added at that point.

### Sitemap `async` conversion

`sitemap()` must become `async function sitemap()` to `await getBlogSlugs()`. Check that no other return path was missed after the conversion — TypeScript will enforce the return type `Promise<MetadataRoute.Sitemap>`.

### Reuse map

| Need | Existing code |
|---|---|
| Public layout, header, footer | `frontend/app/(public)/layout.tsx`, `PublicHeader.tsx`, `PublicFooter.tsx` |
| OG image approach | `frontend/app/page.tsx` (8-2 pattern — static image, no runtime=edge) |
| JSON-LD injection | `frontend/app/page.tsx` (post-8-1-review safe pattern) |
| `metadataBase` | Already set globally (8-2 patch) — do not re-set in these pages |
| Prose styles | `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` line 104 |
| `next/image` with `fill` | Multiple existing pages |
| Sitemap trailing-slash guard | `frontend/app/sitemap.ts` (9-1 pattern) |

## Story Context

### Epic 13

This is the first story in a new Epic 13: **PersonnaPress Company Blog**. The epic showcases the product by using its own headless delivery API to power the company blog — dogfooding at the public URL level. No backend changes in this story or epic.

Note: After creating the story file, add Epic 13 to `_bmad-output/planning-artifacts/epics.md` with a 2-3 line summary and this story as the only current story. Update `sprint-status.yaml` as below.

### Previous story intelligence

- **12-4 review patches to respect:**
  - `seo.og` can be absent — always use optional chaining (`?.`).
  - `seo.meta_description` can be absent — always provide a fallback.
  - Use optional chaining on `seo.meta_description` and `seo.og` in `generateMetadata()`.
  - `ol`/`ul` with `list-style: none` need `role="list"` for VoiceOver/Safari.
- **8-2 patch:** `metadataBase` is already set globally — do not set it again.
- **8-1 patch:** No `dangerouslySetInnerHTML` for JSON-LD; no `<h3>` inside `<button>`; FAQ needs stable keys (not applicable here but good to remember).
- **11-1 patch:** `CopyrightYear` client component is for `force-static` pages that cannot call `new Date()` server-side. Since this page uses `revalidate = 3600` (ISR), dates can be computed normally in the server component.
- **9-1 trailing-slash guard in sitemap** — preserve when modifying `sitemap.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 12 (delivery API and cluster page patterns)]
- [Source: _bmad-output/implementation-artifacts/12-2-public-delivery-api-tokens.md (API response shape)]
- [Source: _bmad-output/implementation-artifacts/12-4-headless-blog-api-cluster-page.md (review patches, API field names)]
- [Source: backend/app/routers/public_articles.py (_article_list_item + _build_seo field names)]
- [Source: frontend/app/(public)/headless-blog-api/page.tsx (Paper Style patterns, nav, API URL)]
- [Source: frontend/components/marketing/PublicHeader.tsx (nav link pattern)]
- [Source: frontend/app/sitemap.ts (sitemap pattern + trailing-slash guard)]
- [Source: frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx:104 (prose class set)]
