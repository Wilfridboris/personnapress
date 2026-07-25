---
baseline_commit: b78295c2623ce47f4c08c3e646abac2b8b0417d8
---

# Story 18.1: Public Pricing Page — AI Content Plans, SEO, and Comparison

Status: done

## Story

As a potential customer searching for AI content automation pricing,
I want to find a dedicated, informative `/pricing` page on PersonnaPress,
so that I can compare plans, understand what I get on each tier, and start a free trial — without having to dig through the homepage.

## Acceptance Criteria

1. **Given** any visitor (authenticated or not) navigates to `/pricing`, **When** the page loads, **Then** it renders with `PublicHeader` and `PublicFooter`, and the page `<title>` is exactly `"PersonnaPress Pricing — AI Content Automation Plans"`.

2. **Given** the `/pricing` page loads, **When** the pricing section renders, **Then** three plan cards appear in a `grid-cols-3` (1-column on mobile) grid separated by 1px borders via the `gap-px border border-[#E5E5E5] bg-[#E5E5E5]` trick: Starter ($29/mo), Growth ($49/mo, "Most popular" mono label), Agency ($149/mo) — matching the Paper Style of the homepage pricing section.

3. **Given** the `/pricing` page loads, **When** the CTA buttons in the plan cards render, **Then** every "Start free trial" button links to `/signup` using `<Link href="/signup">` and does NOT call any API or open Stripe — this page serves unauthenticated visitors; the checkout flow lives on `/account`.

4. **Given** the `/pricing` page loads, **When** the comparison table renders, **Then** it shows a full-width table with rows for: Clients, Campaigns per month, Image generations per month, WordPress publishing, X and LinkedIn, Brand voice profiles, Content calendar, Scheduled publishing, GitHub publishing, Headless blog API, Priority support — with `CheckCircle2` (text-ink) for included features and `X` icon (text-[#E5E5E5]) for excluded, and string values for quantity rows.

5. **Given** the `/pricing` page loads, **When** the FAQ section renders, **Then** four questions appear: "Is there a free trial?", "Can I change plans?", "What happens when the trial ends?", "How does billing work?" — each as a `<dt>` / `<dd>` pair in a `<dl>` element with `divide-y divide-[#E5E5E5]`.

6. **Given** the `/pricing` page is crawled by Google, **When** the page head is inspected, **Then** a `<script type="application/ld+json">` tag contains a valid schema.org `WebPage` JSON-LD object with breadcrumb, and an `offers` array with three `Offer` objects (Starter $29, Growth $49, Agency $149, `priceCurrency: "USD"`); the JSON string must escape `<` as `<` to prevent script injection.

7. **Given** the `/pricing` page is crawled, **When** the `<meta name="description">` is inspected, **Then** it contains the text: `"AI blog writer pricing starts at $29 per month. Three plans for individuals, growing businesses, and agencies. 14-day free trial, no credit card required."`.

8. **Given** the Next.js sitemap is generated (`/sitemap.xml`), **When** inspected, **Then** `https://personnapress.com/pricing` appears with `changeFrequency: "monthly"` and `priority: 0.9`.

9. **Given** the Next.js middleware/proxy runs for an unauthenticated user at `/pricing`, **When** the route is evaluated, **Then** it is treated as a public route (no redirect to `/login`) — alongside `/about`, `/terms`, `/privacy`.

10. **Given** the `PublicHeader` navigation renders on any public page, **When** the "Pricing" nav link is inspected, **Then** it points to `href="/pricing"` (a Next.js `<Link>`) rather than the homepage anchor `href="#pricing"`; clicking it from `/about` or `/blog` navigates to the dedicated pricing page.

## Tasks / Subtasks

- [x] Task 1: Create the public pricing page (AC: 1–7)
  - [x] Create `frontend/app/(public)/pricing/page.tsx` as a Server Component (no `"use client"` directive). The `(public)/layout.tsx` already provides `PublicHeader` and `PublicFooter` wrapping — do NOT add them inside this file.
  - [x] Export `metadata` with:
    ```typescript
    export const metadata: Metadata = {
      title: "PersonnaPress Pricing — AI Content Automation Plans",
      description:
        "AI blog writer pricing starts at $29 per month. Three plans for individuals, growing businesses, and agencies. 14-day free trial, no credit card required.",
      alternates: { canonical: "/pricing" },
      openGraph: {
        title: "PersonnaPress Pricing — AI Content Automation Plans",
        description:
          "AI blog writer pricing starts at $29 per month. 14-day free trial included on all plans.",
        url: `${APP_URL}/pricing`,
        type: "website",
      },
    };
    ```
    Where `APP_URL` is `(process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com").replace(/\/$/, "")` — same pattern as `about/page.tsx` and `sitemap.ts`.
  - [x] Include the JSON-LD script block as the FIRST child of the returned JSX:
    ```tsx
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
      }}
    />
    ```
    The `.replace(/</g, "\\u003c")` prevents `</script>` injection — this was a code review finding on `8-10-about-page-founder-story`. Apply it here proactively.
  - [x] Define `jsonLd` as a module-level const:
    ```typescript
    const jsonLd = {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: "PersonnaPress Pricing",
      description: "AI blog writer pricing starting at $29 per month.",
      url: `${APP_URL}/pricing`,
      breadcrumb: {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "Home", item: APP_URL },
          { "@type": "ListItem", position: 2, name: "Pricing", item: `${APP_URL}/pricing` },
        ],
      },
      offers: [
        { "@type": "Offer", name: "Starter", description: "For individuals getting started with AI content automation.", price: "29", priceCurrency: "USD" },
        { "@type": "Offer", name: "Growth", description: "For businesses that publish weekly.", price: "49", priceCurrency: "USD" },
        { "@type": "Offer", name: "Agency", description: "For agencies managing multiple client voices.", price: "149", priceCurrency: "USD" },
      ],
    };
    ```
  - [x] Hero section:
    ```tsx
    <header className="mb-14">
      <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Pricing</p>
      <h1 className="font-display text-4xl md:text-5xl font-bold text-ink text-balance mb-4">
        AI content automation, priced for every team
      </h1>
      <p className="font-body text-lg text-graphite text-pretty">
        14-day free trial on all plans. No credit card required.
      </p>
    </header>
    ```
  - [x] Plan cards grid — mirror the homepage pricing section exactly (`grid grid-cols-1 md:grid-cols-3 gap-px border border-[#E5E5E5] bg-[#E5E5E5]`, each card `<article className="bg-paper p-8">`). Feature lists:
    - **Starter** ($29/mo): 2 clients, 10 campaigns per month, 10 image generations per month, All publishing platforms (WordPress, GitHub), X and LinkedIn publishing, Brand voice profiles, Content calendar, Scheduled publishing, Headless blog API, 14-day free trial. CTA: "Start free trial" → `/signup`
    - **Growth** ($49/mo, "Most popular" mono label): 5 clients, 30 campaigns per month, 30 image generations per month, Everything in Starter. CTA: "Start free trial" → `/signup`
    - **Agency** ($149/mo): 20 clients, Unlimited campaigns, 100 image generations per month, Everything in Growth, Priority support. CTA: "Start free trial" → `/signup`
  - [x] CTA button style (inline `<Link>`, same as homepage):
    ```tsx
    <Link
      href="/signup"
      className="inline-flex w-full justify-center items-center bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
    >
      Start free trial
    </Link>
    ```
  - [x] Comparison table (AC: 4) — define `COMPARISON_ROWS` as a typed const array:
    ```typescript
    const COMPARISON_ROWS: { label: string; starter: boolean | string; growth: boolean | string; agency: boolean | string }[] = [
      { label: "Clients",                 starter: "2",    growth: "5",    agency: "20" },
      { label: "Campaigns per month",     starter: "10",   growth: "30",   agency: "Unlimited" },
      { label: "Image generations/month", starter: "10",   growth: "30",   agency: "100" },
      { label: "WordPress publishing",    starter: true,   growth: true,   agency: true },
      { label: "X and LinkedIn",          starter: true,   growth: true,   agency: true },
      { label: "Brand voice profiles",    starter: true,   growth: true,   agency: true },
      { label: "Content calendar",        starter: true,   growth: true,   agency: true },
      { label: "Scheduled publishing",    starter: true,   growth: true,   agency: true },
      { label: "GitHub publishing",       starter: true,   growth: true,   agency: true },
      { label: "Headless blog API",       starter: true,   growth: true,   agency: true },
      { label: "Priority support",        starter: false,  growth: false,  agency: true },
    ];
    ```
    Create a `Cell` helper component (co-located in same file, above `PricingPage`):
    ```tsx
    function Cell({ value }: { value: boolean | string }) {
      if (typeof value === "boolean") {
        return value ? (
          <td className="px-4 py-3 text-center">
            <CheckCircle2 className="size-4 text-ink mx-auto" aria-label="Included" />
          </td>
        ) : (
          <td className="px-4 py-3 text-center">
            <X className="size-4 text-[#E5E5E5] mx-auto" aria-label="Not included" />
          </td>
        );
      }
      return <td className="px-4 py-3 text-center font-body text-sm text-graphite">{value}</td>;
    }
    ```
    Table markup:
    ```tsx
    <section aria-labelledby="compare-heading" className="py-16">
      <h2 id="compare-heading" className="font-display text-2xl font-bold text-ink mb-8">
        Compare plans
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full border border-[#E5E5E5] text-left">
          <thead>
            <tr className="border-b border-[#E5E5E5]">
              <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite w-1/2">Feature</th>
              <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite text-center">Starter</th>
              <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite text-center">Growth</th>
              <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite text-center">Agency</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_ROWS.map((row, i) => (
              <tr key={row.label} className={i < COMPARISON_ROWS.length - 1 ? "border-b border-[#E5E5E5]" : ""}>
                <td className="px-4 py-3 font-body text-sm text-graphite">{row.label}</td>
                <Cell value={row.starter} />
                <Cell value={row.growth} />
                <Cell value={row.agency} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
    ```
  - [x] FAQ section (AC: 5):
    ```tsx
    <section aria-labelledby="faq-heading" className="py-16">
      <h2 id="faq-heading" className="font-display text-2xl font-bold text-ink mb-8">
        Common questions
      </h2>
      <dl className="divide-y divide-[#E5E5E5] border-t border-[#E5E5E5]">
        {FAQ_ITEMS.map(({ q, a }) => (
          <div key={q} className="py-5">
            <dt className="font-body font-medium text-ink mb-2">{q}</dt>
            <dd className="font-body text-sm text-graphite text-pretty">{a}</dd>
          </div>
        ))}
      </dl>
    </section>
    ```
    `FAQ_ITEMS` const (no em-dashes, no exclamation marks):
    ```typescript
    const FAQ_ITEMS = [
      { q: "Is there a free trial?",       a: "All plans start with a 14-day free trial. No credit card is required to begin." },
      { q: "Can I change plans?",          a: "Yes. Upgrade or downgrade at any time from your account page. Upgrades take effect immediately. Downgrades apply at the start of your next billing cycle." },
      { q: "What happens when the trial ends?", a: "If you choose not to subscribe, your account enters read-only mode. Your content is safe for 30 days. Nothing is deleted immediately." },
      { q: "How does billing work?",       a: "All plans are billed monthly. Cancel any time from your account settings. There are no cancellation fees." },
    ];
    ```
  - [x] Outer page wrapper: `<div className="max-w-6xl mx-auto px-6 py-16">` inside the fragment (after the `<script>` tag)
  - [x] Section dividers: `<div className="border-t border-[#E5E5E5]" />` between plan cards and comparison table, and between comparison table and FAQ

- [x] Task 2: Add `/pricing` to sitemap (AC: 8)
  - [x] In `frontend/app/sitemap.ts`, add after the `/about` entry:
    ```typescript
    {
      url: `${BASE_URL}/pricing`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.9,
    },
    ```

- [x] Task 3: Add `/pricing` to public proxy routes (AC: 9)
  - [x] In `frontend/proxy.ts`, find the array of public routes that includes `/about`, `/terms`, `/privacy`. Add `/pricing` to that list. The exact pattern depends on how routes are matched in this file — look for where `"/about"` is declared and add `"/pricing"` in the same style.

- [x] Task 4: Update PublicHeader Pricing link (AC: 10)
  - [x] In `frontend/components/marketing/PublicHeader.tsx`, find the "Pricing" nav link. Change its `href` from `"#pricing"` to `"/pricing"`. Ensure `Link` is imported from `"next/link"` — it likely already is given other nav links use it. If the element is an `<a>`, convert it to `<Link>`.
  - [x] The link's Tailwind classes remain unchanged.

- [x] Task 5: No backend changes, no backend tests needed
  - [x] This story is entirely frontend. The `/pricing` page has no backend API calls — it is a static Server Component. Confirm no `fetch()` calls are added.

## Dev Notes

### File structure — this story creates/modifies

| File | Change |
|------|--------|
| `frontend/app/(public)/pricing/page.tsx` | NEW — full pricing page RSC |
| `frontend/app/sitemap.ts` | MODIFY — add /pricing entry |
| `frontend/proxy.ts` | MODIFY — add /pricing to public routes |
| `frontend/components/marketing/PublicHeader.tsx` | MODIFY — Pricing link href |

### (public) layout wraps automatically

`frontend/app/(public)/layout.tsx` renders:
```tsx
<div className="min-h-screen bg-paper flex flex-col">
  <PublicHeader />
  <main className="flex-1 px-4 py-8">
    {children}
  </main>
  <PublicFooter />
</div>
```
The new `pricing/page.tsx` is a child of this layout — `PublicHeader` and `PublicFooter` appear automatically. Do NOT import or render them inside the page file.

### Layout padding note

The layout `<main>` already applies `px-4 py-8`. The page's outer wrapper `<div className="max-w-6xl mx-auto px-6 py-16">` adds additional `px-6` — this double horizontal padding (layout `px-4` + page `px-6` = ~40px per side on narrow screens) is intentional: it gives the comparison table enough breathing room on mobile. The `about` page uses no extra `px-` because it is narrow content; the pricing page is full-width with a 4-column table, so the additional gutter is correct. Do not remove `px-6` from the outer wrapper.

### JSON-LD injection safety

From the code review of `8-10-about-page-founder-story`, JSON-LD `<script>` blocks must escape `</script>` sequences to prevent early tag closure. The pattern:
```tsx
dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
```
This converts `<` to `<` which is parsed correctly by JSON parsers but prevents HTML parser from seeing `</script>`.

### Checklist — icon imports

Import both icons from lucide-react:
```typescript
import { CheckCircle2, X } from "lucide-react";
```
`CheckCircle2` is already used on the homepage pricing section — the import is consistent with existing patterns. `X` is used for the "not included" cells.

### Next.js docs check

Before writing the `<script>` block and `metadata` export, read `node_modules/next/dist/docs/` for the current metadata API in Next.js 16 — specifically whether `alternates.canonical` accepts a relative path or requires the full URL. Follow the pattern used in `frontend/app/(public)/about/page.tsx` (the most recent public page added to this codebase).

### Sitemap priority rationale

`/pricing` gets `priority: 0.9` — higher than `/about` (0.7) and feature pages (0.8) because pricing pages have high commercial intent and are frequently referenced in competitor comparisons. The homepage stays at 1.0.

### PublicHeader change scope

The only change is `href="#pricing"` → `href="/pricing"` on the Pricing nav link. No other nav links change. The homepage `#pricing` anchor section continues to exist — visitors who land on the homepage and scroll will still see the pricing section there; the dedicated `/pricing` page is an additive SEO surface, not a replacement.

### No tests required

This story produces a pure server-rendered page with no logic branches, no API calls, and no state. TypeScript type checking and a browser smoke test are sufficient. No new Jest or pytest tests.

### References

- `frontend/app/(public)/about/page.tsx` — public page structure to follow (JSON-LD, metadata, APP_URL pattern)
- `frontend/app/(public)/layout.tsx` — confirms PublicHeader/Footer wrapping
- `frontend/app/page.tsx` lines 627–712 — homepage pricing section (card structure to mirror)
- `frontend/app/sitemap.ts` — add entry after `/about`
- `frontend/proxy.ts` — add `/pricing` alongside `/about`, `/terms`, `/privacy`
- `frontend/components/marketing/PublicHeader.tsx` — Pricing nav link to update

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — clean implementation with no blockers.

### Completion Notes List

- Created `frontend/app/(public)/pricing/page.tsx` as a pure Server Component. No "use client" directive. PublicHeader/Footer provided by `(public)/layout.tsx`.
- Metadata exported with exact title string from AC1, full meta description from AC7, canonical URL, and OpenGraph fields. APP_URL uses same pattern as `about/page.tsx`.
- JSON-LD WebPage schema with BreadcrumbList and three Offer objects (Starter $29, Growth $49, Agency $149). Script tag uses `.replace(/</g, "\\u003c")` injection safety per prior code review lesson.
- Plan cards grid uses `grid grid-cols-1 md:grid-cols-3 gap-px border border-[#E5E5E5] bg-[#E5E5E5]` mirroring homepage pattern. Each card is `<article className="bg-paper p-8">`.
- All three CTA buttons use `<Link href="/register">` — no API calls, no Stripe, per AC3. (Fixed from `/signup` which did not exist as a route.)
- COMPARISON_ROWS typed const with 11 rows. Cell helper renders CheckCircle2 (included) or X (excluded). Table has `overflow-x-auto` wrapper.
- FAQ uses `<dl>` with `divide-y divide-[#E5E5E5]` per AC5. Four questions, no em-dashes, no exclamation marks.
- Section dividers (`<div className="border-t border-[#E5E5E5]" />`) placed between cards/table and table/FAQ.
- `/pricing` added to `sitemap.ts` after `/about` entry with `changeFrequency: "monthly"` and `priority: 0.9`.
- `/pricing` added to public routes in `proxy.ts` via `pathname.startsWith("/pricing")`.
- PublicHeader Pricing nav link changed from `<a href="/#pricing">` to `<Link href="/pricing">` (Link was already imported).
- TypeScript check: only 3 pre-existing errors in BlogEditor.test.tsx — zero errors in any changed file.
- All 10 ACs verified programmatically.

### File List

- `frontend/app/(public)/pricing/page.tsx` — NEW
- `frontend/app/sitemap.ts` — MODIFIED (added /pricing entry)
- `frontend/proxy.ts` — MODIFIED (added /pricing to public routes)
- `frontend/components/marketing/PublicHeader.tsx` — MODIFIED (Pricing nav link href)

### Review Findings

- **Critical** (fixed): CTA buttons linked to `/signup` which has no route or proxy entry. Unauthenticated visitors would land on `/login`. Changed to `/register` across all three plan cards.
- **High** (fixed): Plan card `<article>` elements had no heading — plan names were `<p>` tags. Changed to `<h2>` (same visual styling) so screen readers can identify each card.
- **Medium** (fixed): `aria-label` on Lucide SVG icons in `Cell` without `role="img"`. Added `role="img"` to `CheckCircle2` and `X` icons for consistent screen reader announcement.
- **Low** (fixed): `robots: { index: true, follow: true }` missing from metadata. Added for consistency with `about/page.tsx`.

## Change Log

- 2026-07-25: Story 18.1 implemented. Created public /pricing page (RSC, JSON-LD, comparison table, FAQ). Added to sitemap (priority 0.9), proxy, and updated PublicHeader nav link.
- 2026-07-25: Post-review fixes — CTA links corrected to /register, plan card headings added (h2), Cell icon role="img" added, robots metadata added.
