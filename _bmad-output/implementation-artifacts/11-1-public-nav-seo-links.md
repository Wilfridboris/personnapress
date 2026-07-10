---
baseline_commit: 81668d610bb15f49649ab1b4ab6b41517bbd0608
---

# Story 11.1: Public Nav & SEO Links

Status: done

## Story

As a visitor to any PersonnaPress public page,
I want consistent navigation (header + footer) on every public page,
so that I can always find my way around and discover all product features including the GitHub Publisher.

## Acceptance Criteria

1. A `PublicHeader` component is extracted from `app/page.tsx` and renders the same sticky header (logo + nav links + "Start Free Trial" CTA) on every public page.
2. A `PublicFooter` component is extracted from `app/page.tsx` and renders the same footer structure on every public page.
3. `app/(public)/layout.tsx` uses `PublicHeader` and `PublicFooter` so `/privacy` and `/terms` both receive full navigation.
4. The `/github-publisher` page receives `PublicHeader` and `PublicFooter` (either by moving it into the `(public)` group or by updating its root-level layout).
5. The footer nav includes a "GitHub Publisher" link pointing to `/github-publisher`, placed between "Pricing" and "FAQ".
6. The landing page Platforms section adds a contextual anchor link beneath the existing platform chips: "Publishing to GitHub Pages? → See the dedicated integration" linking to `/github-publisher`.
7. The `PublicFooter` renders on the landing page itself (replacing the inline footer) with no visual regression — pixel-identical to the current footer.
8. The `PublicHeader` renders on the landing page itself (replacing the inline header) with no visual regression — sticky, `z-50`, same logo, nav links, and CTA.

## Tasks / Subtasks

- [x] Create `frontend/components/marketing/PublicHeader.tsx` (AC: 1, 8)
  - [x] Extract header JSX from `app/page.tsx` verbatim — logo, nav anchors, "Start Free Trial" Link
  - [x] Keep `"use client"` only if interactive state is needed (it's not — this is static, use RSC)
  - [x] Preserve all existing classes and aria attributes exactly
- [x] Create `frontend/components/marketing/PublicFooter.tsx` (AC: 2, 5, 7)
  - [x] Extract footer JSX from `app/page.tsx` verbatim
  - [x] Add "GitHub Publisher" `<Link href="/github-publisher">` in the nav between "Pricing" and "FAQ"
  - [x] RSC (no client state needed)
- [x] Update `app/(public)/layout.tsx` to use `PublicHeader` + `PublicFooter` (AC: 3)
  - [x] Wrap `children` between header and footer
  - [x] Keep the `<main>` tag wrapping children
- [x] Update `app/page.tsx` to replace inline header/footer with `PublicHeader`/`PublicFooter` (AC: 7, 8)
  - [x] Delete the inline `<header>` block; replace with `<PublicHeader />`
  - [x] Delete the inline `<footer>` block; replace with `<PublicFooter />`
  - [x] Verify the surrounding `<div className="min-h-screen bg-paper">` structure is preserved
- [x] Handle `/github-publisher` page navigation (AC: 4)
  - [x] Check if `app/github-publisher/page.tsx` already has its own header/footer
  - [x] If yes: replace inline header/footer with `PublicHeader`/`PublicFooter`
  - [x] If the page has `export const dynamic = "force-static"`, ensure the components are also statically renderable (RSC with no dynamic data = fine)
- [x] Add GitHub Pages contextual link in Platforms section of landing page (AC: 6)
  - [x] In `app/page.tsx`, locate the `{/* Platforms */}` section (around line 609)
  - [x] Below the `flex flex-wrap gap-4` chip row, add:
    ```tsx
    <p className="text-sm text-graphite mt-4 font-mono">
      Publishing to GitHub Pages?{" "}
      <Link href="/github-publisher" className="text-ink underline underline-offset-2 hover:text-graphite transition-colors">
        See the dedicated integration
      </Link>
    </p>
    ```
  - [x] This replaces or supplements the existing `<p className="text-sm text-graphite mt-6 font-mono">Meta / Instagram / Threads: architected, shipping in Phase 2.</p>` — keep both, put the GitHub link first

### Review Findings

- [x] [Review][Patch] HOW_IT_WORKS step cards use `<article>` — sequential numbered process steps are not independently distributable content; `<ol>/<li>` is semantically correct [frontend/app/github-publisher/page.tsx, HOW_IT_WORKS section]
- [x] [Review][Patch] `new Date().getFullYear()` in PublicFooter baked at build time on force-static pages — `/github-publisher` uses `export const dynamic = "force-static"`, so the copyright year freezes at build year; fix with a `CopyrightYear` client component using `suppressHydrationWarning` [frontend/components/marketing/PublicFooter.tsx:30]
- [x] [Review][Defer] No mobile/responsive navigation in PublicHeader — pre-existing, inline header had the same issue; deferred, pre-existing
- [x] [Review][Defer] Logo intrinsic dimensions `width={128} height={128}` are square for a wide logo — pre-existing, matches spec-prescribed extraction; deferred, pre-existing
- [x] [Review][Defer] `priority` on logo image in PublicHeader applies to all public pages — logo is above fold on all pages (sticky header) so acceptable, minor overhead on inner pages; deferred, pre-existing

## Dev Notes

### PublicHeader component spec (Paper Style)

```tsx
// frontend/components/marketing/PublicHeader.tsx
// RSC — no "use client" needed (no state, no hooks)
import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";

export function PublicHeader() {
  return (
    <header className="border-b border-border sticky top-0 bg-paper z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" aria-label="PersonnaPress home">
          <Image
            src="/images/PersonnaPress-logo.png"
            alt="PersonnaPress"
            width={128}
            height={128}
            priority
            className="h-8 w-auto"
          />
        </Link>
        <nav aria-label="Main navigation" className="flex items-center gap-8">
          <a href="/#workflow" className="text-sm text-graphite hover:text-ink transition-colors">How it works</a>
          <a href="/#platforms" className="text-sm text-graphite hover:text-ink transition-colors">Platforms</a>
          <a href="/#pricing" className="text-sm text-graphite hover:text-ink transition-colors">Pricing</a>
          <a href="/#faq" className="text-sm text-graphite hover:text-ink transition-colors">FAQ</a>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-2 hover:bg-graphite transition-colors"
          >
            Start Free Trial
            <ArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </nav>
      </div>
    </header>
  );
}
```

**Important:** The landing page uses anchor hash links (`#workflow`, `#platforms`, etc.) — these work fine from the landing page itself. From `/privacy` or `/terms`, these will navigate to `/#workflow` etc., which is correct behavior. Use `href="/#workflow"` (with leading slash) so links work from any public page, not just the homepage.

### PublicFooter component spec (Paper Style)

```tsx
// frontend/components/marketing/PublicFooter.tsx
// RSC — no "use client" needed
import Link from "next/link";
import Image from "next/image";

export function PublicFooter() {
  return (
    <footer className="border-t border-border">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <Link href="/" aria-label="PersonnaPress home">
            <Image
              src="/images/PersonnaPress-logo.png"
              alt="PersonnaPress"
              width={128}
              height={128}
              className="h-7 w-auto"
            />
          </Link>
          <nav aria-label="Footer navigation" className="flex flex-wrap gap-6">
            <a href="/#workflow" className="font-mono text-xs text-graphite hover:text-ink transition-colors">How it works</a>
            <a href="/#platforms" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Platforms</a>
            <a href="/#pricing" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Pricing</a>
            <Link href="/github-publisher" className="font-mono text-xs text-graphite hover:text-ink transition-colors">GitHub Publisher</Link>
            <a href="/#faq" className="font-mono text-xs text-graphite hover:text-ink transition-colors">FAQ</a>
            <Link href="/dashboard" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Sign up</Link>
            <Link href="/login" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Log in</Link>
          </nav>
        </div>
        <div className="border-t border-border mt-6 pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <p className="font-mono text-xs text-graphite">
            &copy; {new Date().getFullYear()} PersonnaPress. All rights reserved.
          </p>
          <nav className="flex items-center gap-4" aria-label="Legal">
            <Link href="/terms" className="font-mono text-xs text-graphite hover:text-ink transition-colors">
              Terms of Service
            </Link>
            <span className="font-mono text-xs text-graphite/40" aria-hidden="true">&middot;</span>
            <Link href="/privacy" className="font-mono text-xs text-graphite hover:text-ink transition-colors">
              Privacy Policy
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
```

**Note:** `new Date().getFullYear()` in the footer copyright is fine in an RSC because it runs at request time (or build time for static pages). No "use client" needed.

### Updated (public)/layout.tsx spec

```tsx
// app/(public)/layout.tsx
import { PublicHeader } from "@/components/marketing/PublicHeader";
import { PublicFooter } from "@/components/marketing/PublicFooter";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-paper flex flex-col">
      <PublicHeader />
      <main className="flex-1 px-4 py-8">
        {children}
      </main>
      <PublicFooter />
    </div>
  );
}
```

### /github-publisher layout handling

The `/github-publisher` page is at `app/github-publisher/page.tsx` — it is NOT inside the `(public)` route group so it does NOT get the `(public)/layout.tsx` automatically. It likely has its own inline header/footer JSX. Check the file and replace with `<PublicHeader />` / `<PublicFooter />`.

If the page exports `export const dynamic = "force-static"`, the shared components must also be statically renderable (no cookies/headers). Both `PublicHeader` and `PublicFooter` are pure RSC with no dynamic data, so this is fine.

### Critical: anchor links from non-landing pages

The nav links in the header (`#workflow`, `#platforms`, etc.) are section anchors on the landing page. When rendering from `/privacy`, `/terms`, or `/github-publisher`, they must resolve to the landing page sections. Always use `href="/#workflow"` (with leading `/`) — never bare `href="#workflow"` — in the shared components.

### Architecture compliance

- No API calls in these components — they are pure presentational RSC
- Follow RSC rule from project-context.md: no data fetching in server components
- Use `@/components/marketing/` as the directory (alongside existing `TerminalDemo.tsx`)
- No `"use client"` directive on these components
- Use `next/link` for internal routes, plain `<a>` for hash anchors

### Project Structure Notes

- New files: `frontend/components/marketing/PublicHeader.tsx`, `frontend/components/marketing/PublicFooter.tsx`
- Modified files: `frontend/app/(public)/layout.tsx`, `frontend/app/page.tsx`, `frontend/app/github-publisher/page.tsx`
- The landing page `app/page.tsx` keeps all its data constants, schema LD+JSON, and metadata — only the header and footer JSX blocks are replaced with component calls
- No new dependencies needed (already uses next/link, next/image, lucide-react)

### References

- Current inline header: `frontend/app/page.tsx` lines 357–401
- Current inline footer: `frontend/app/page.tsx` lines 768–802
- Current public layout: `frontend/app/(public)/layout.tsx` (5 lines, empty wrapper)
- Platforms section: `frontend/app/page.tsx` lines 609–633
- GitHub publisher page: `frontend/app/github-publisher/page.tsx`
- Existing marketing component: `frontend/components/marketing/TerminalDemo.tsx`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Created `PublicHeader` RSC with logo Link wrapper, aria-label on nav, and `/#` prefixed hash anchors so links work from any public page
- Created `PublicFooter` RSC with "GitHub Publisher" link between Pricing and FAQ as specified
- Updated `(public)/layout.tsx` to use both components with `flex-col` min-h-screen wrapper
- Replaced 45-line inline `<header>` and 36-line inline `<footer>` in `app/page.tsx` with single component calls; removed now-unused `Image` import
- Replaced inline header/footer in `github-publisher/page.tsx` (which had a different nav — Home/Sign in/Start free); now uses unified shared components; removed unused `Image` import
- Added GitHub Pages contextual link above Meta/Phase 2 note in Platforms section
- Pre-existing TypeScript error in `ClientDetail.tsx` (unrelated to this story) was present before baseline commit

### File List

- `frontend/components/marketing/PublicHeader.tsx` (new)
- `frontend/components/marketing/PublicFooter.tsx` (new)
- `frontend/app/(public)/layout.tsx` (modified)
- `frontend/app/page.tsx` (modified)
- `frontend/app/github-publisher/page.tsx` (modified)

## Change Log

- Extracted PublicHeader and PublicFooter shared RSC components; updated (public)/layout.tsx, landing page, and github-publisher page to use them; added GitHub Pages contextual link in Platforms section (Date: 2026-07-10)
