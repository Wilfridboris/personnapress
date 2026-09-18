---
title: 'llms.txt and explicit AI-crawler coverage'
type: 'feature'
created: '2026-09-18'
status: 'done'
route: 'one-shot'
---

# llms.txt and explicit AI-crawler coverage

## Intent

**Problem:** PersonnaPress had no `/llms.txt` for generative crawlers, `robots.ts` did not explicitly name `Google-Extended` or `OAI-SearchBot`, and the `proxy.ts` allowlist was silently redirecting eight sitemap-listed marketing pages (comparison, persona, brand-voice-generator) plus any new AI-meta file to `/login`, hiding them from every crawler. This implements audit item P2.7 from `docs/seo-aeo-geo-audit.md`.

**Approach:** Add a static `/llms.txt` route handler that curates the main public routes using the existing `BASE_URL` fallback pattern; add explicit `Google-Extended` and `OAI-SearchBot` groups to `robots.ts`; and open the proxy allowlist so `/llms.txt` and the eight blocked marketing pages are publicly crawlable. During review, also closed a robots correctness gap: named bot groups override the wildcard, so each now restates the full private-route `disallow` list (previously AI bots could crawl the gated app), and that list was completed to match the proxy's private routes.

## Suggested Review Order

**AI-crawler content (entry point)**

- New route handler; curated public-route summary in the llms.txt convention, built from `BASE_URL`.
  [`route.ts:8`](../../frontend/app/llms.txt/route.ts#L8)

- Publishing destinations now include Meta (Facebook, Instagram, Threads) per product scope.
  [`route.ts:11`](../../frontend/app/llms.txt/route.ts#L11)

- Optional section points crawlers to the full URL set and legal pages.
  [`route.ts:46`](../../frontend/app/llms.txt/route.ts#L46)

**Crawler directives**

- Shared `disallow` list applied to the wildcard and every named bot so AI crawlers cannot reach the gated app.
  [`robots.ts:38`](../../frontend/app/robots.ts#L38)

- Private routes completed and aligned with the proxy allowlist to stop drift.
  [`robots.ts:7`](../../frontend/app/robots.ts#L7)

**Access control**

- Public allowlist opened for `/llms.txt` and the eight previously login-walled marketing routes; gated app stays protected.
  [`proxy.ts:16`](../../frontend/proxy.ts#L16)
