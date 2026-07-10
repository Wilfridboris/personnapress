---
title: 'Landing page copy: replace rough ideas/notes with your notes'
type: 'chore'
created: '2026-07-10'
status: 'done'
route: 'one-shot'
---

# Landing page copy: replace rough ideas/notes with your notes

## Intent

**Problem:** The landing page used "rough ideas" (metadata) and "rough notes" (hero body) to describe the user's input, while the H1 said "Your Ideas." — three inconsistent nouns for the same concept.

**Approach:** Unify all hero-section and SEO metadata copy to "your notes" / "Your Notes." so the marketing message is coherent before any crawler or visitor reads it.

## Suggested Review Order

- [`frontend/app/page.tsx:26`](../../frontend/app/page.tsx) — meta description ("turns your notes into SEO-ranked blog posts…")
- [`frontend/app/page.tsx:43`](../../frontend/app/page.tsx) — OG description ("Turn your notes into ranked blog posts…")
- [`frontend/app/page.tsx:408`](../../frontend/app/page.tsx) — H1 ("Your Notes.")
- [`frontend/app/page.tsx:422`](../../frontend/app/page.tsx) — hero body ("turns your notes into ranked articles…")
