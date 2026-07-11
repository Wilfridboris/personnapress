# Sprint Change Proposal — GitHub Blog Publishing (v2 / Phase 2)

**Date:** 2026-07-09
**Prepared by:** Boris (with Correct Course workflow)
**Change scope:** Moderate — new Epic 8, additive to v1 MVP
**Handoff:** Product Owner / Developer

---

## 1. Issue Summary

**Trigger:** Post-MVP planning. v1 (Epics 1–7) is complete. The opportunity is to extend PersonnaPress into the developer blogger market by adding GitHub-hosted blog publishing as a first-class Phase 2 feature, alongside a dedicated marketing landing page targeting that audience.

**Context:** The v1 platform already publishes to WordPress, Webflow, X, and LinkedIn. The `platform_connections` table was explicitly architected to support Phase 2 additions. No existing v1 work is affected.

**Core problem statement:** Developers who blog on GitHub Pages (Jekyll, Astro, Next.js, Hugo, Eleventy, Docusaurus, MkDocs, static) have no current tool that combines AI writing + automatic framework detection + repo-aware publishing. Existing Git CMS tools (Pages CMS, Decap, TinaCMS) are editors-first, not AI-generation-first. PersonnaPress can own this gap.

**Evidence:**
- `platform_connections` addendum note: "Required for Phase 2 platform additions."
- No current competitor delivers AI writing + framework detection + GitHub publish in one product.
- Perplexity research confirms clear positioning: "Not a CMS. An AI GitHub publishing layer."

---

## 2. Impact Analysis

### Epic Impact

| Epic | Status | Change |
|------|--------|--------|
| Epic 1 — Foundation & Auth | Complete | No change |
| Epic 2 — Client Management | Complete | No change |
| Epic 3 — Content Generation | Complete | No change |
| Epic 4 — Approval Gate | Complete | No change |
| Epic 5 — Platform Publishing | Complete | Minor: `platform` enum needs `github_pages` value (one Alembic migration, no story changes) |
| Epic 6 — Dashboard & Calendar | Complete | No change |
| Epic 7 — Trial Lifecycle | Complete | No change |
| **Epic 8 — GitHub Blog Publishing** | **New** | **7 new stories (FR-29 through FR-35)** |

### PRD Artifact Changes

| Section | Change |
|---------|--------|
| §2.2 Non-Users | Added: GitHub-hosted blog publishing deferred to Phase 2 (Epic 8) |
| §3 Glossary | Added: GitHub App, Repo Detection, Framework Template |
| §4.11 (new) | Full feature section with FR-29 through FR-35 |

### Architecture Impact

| Component | Change |
|-----------|--------|
| `platform_connections.platform` enum | Add `github_pages` value — one Alembic migration |
| `campaigns` table | Add `github_pr_url` text column nullable — one Alembic migration |
| `integrations/github.py` | New file: GitHub App token refresh, Contents API reads, commit/tree/PR writes |
| `services/repo_detection.py` | New file: framework detection logic (reads only via GitHub API) |
| `services/publishing.py` | Extended: new branch for `platform='github_pages'` |
| `scheduler/scheduler.py` | No change (GitHub PR merge handled via webhook, not scheduler) |
| Next.js `/api/webhooks/github` | New route: validates GitHub App webhook signature, calls FastAPI on PR merge |
| FastAPI `POST /api/v1/webhooks/github` | New endpoint: matches PR URL to Campaign, transitions status to `published` |
| `backend/.env.example` | New vars: `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_CLIENT_ID`, `GITHUB_APP_WEBHOOK_SECRET` |
| Next.js `/github-publisher` | New SSG marketing page |

### UX Impact

| Surface | Change |
|---------|--------|
| Platform Connections page | New GitHub connection card (follows UX-DR20 pattern) |
| Connection card states | Scanning → Detected / Ambiguous / Unknown detection states |
| Approval Gate footer | New "Publish to GitHub" Secondary button |
| Approval Gate | New pre-publish confirmation panel (inline, Paper Style) |
| Approval Gate | New "PR OPEN" StatusBadge variant |
| `/github-publisher` | New SSG landing page: Ink hero, terminal demo, framework grid, comparison table, Highlighter CTA |

---

## 3. Recommended Approach

**Selected:** Option 1 — Direct Adjustment (purely additive)

**Rationale:**
- Zero risk to v1: no existing stories, services, or DB tables are modified
- The `platform_connections` and `jobs` tables are already designed for exactly this extension
- The publishing service boundary (`services/publishing.py`) is the correct integration point per AR-19
- The GitHub App installation token pattern is self-refreshing (no scheduler job needed)
- The landing page is a static SSG page with no backend dependency — can be built and deployed independently

**Effort estimate:** Medium (3–4 development sprints)
**Risk level:** Low (isolated new capability, PR-first default prevents live site corruption)

---

## 4. Epic 8 Story Summary

| Story | Title | FRs | Effort |
|-------|-------|-----|--------|
| 8.1 | GitHub App OAuth & Repository Connection | FR-29 | Medium |
| 8.2 | Repo Framework Detection Engine | FR-30 | Medium |
| 8.3 | Publish Pipeline — Jekyll & Plain Static | FR-31 | Low |
| 8.4 | Publish Pipeline — Astro, Next.js, Hugo, Eleventy | FR-32 | Medium |
| 8.5 | Publish Pipeline — Docusaurus & MkDocs | FR-33 | Low |
| 8.6 | PR-First Workflow, Preview UI & Direct Commit Option | FR-34 | Medium |
| 8.7 | GitHub Publisher Landing Page | FR-35 | Medium |

**Suggested sequencing:**
1. Stories 8.1 → 8.2 → 8.3 (auth + detection + first publish — MVP subset, shippable as v2.0)
2. Stories 8.4 → 8.5 (extended framework coverage — v2.1)
3. Story 8.6 (PR workflow polish — v2.1 or v2.2)
4. Story 8.7 (landing page — can run in parallel with 8.1/8.2, ship with v2.0)

**Required prerequisite (outside Epic 8 stories):**
- Register a PersonnaPress GitHub App in GitHub Developer Settings
- Generate and securely store the GitHub App private key (PEM) as a Droplet env var
- One Alembic migration: add `github_pages` to `platform` enum + add `github_pr_url` column to `campaigns`

---

## 5. Implementation Handoff

**Scope classification:** Moderate

**Handoff to:** Developer agent (stories are self-contained and ready for implementation)

**Developer responsibilities:**
1. Run the prerequisite Alembic migration before starting Story 8.1
2. Register the GitHub App (manual step in GitHub Developer Settings)
3. Implement Stories 8.1–8.7 in sequencing order above
4. Wire the `/api/webhooks/github` Next.js route alongside the existing Stripe webhook route

**Success criteria for v2.0 ship:**
- User can connect a GitHub repo, see "Detected: Jekyll" (or equivalent), and publish a post as a PR
- PR merge triggers `campaigns.status → published` via webhook
- `/github-publisher` landing page is live and indexed
- All existing v1 platform publishing (WordPress, Webflow, X, LinkedIn) is unaffected

---

## 6. Files Modified

| File | Change type |
|------|-------------|
| `_bmad-output/planning-artifacts/prds/prd-PersonnaPress-2026-06-14/prd.md` | Updated: §2.2, §3, new §4.11 |
| `_bmad-output/planning-artifacts/epics.md` | Updated: Epic 8 header + Stories 8.1–8.7 |
| `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-09.md` | New: this document |
