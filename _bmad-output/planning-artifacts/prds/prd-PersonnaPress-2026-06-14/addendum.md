# Addendum — PersonnaPress PRD

*Companion to `prd.md`. Contains depth that belongs in downstream documents (architecture, UX, solution design) or that earned a place but doesn't fit the PRD's main narrative.*

## A. Competitive Landscape (June 2026)

### Market Gap

No tool currently combines deep personal voice learning + SEO-structured content + intelligent cross-platform adaptation + native multi-platform publishing at a solopreneur-friendly price. Most competitors have pivoted upmarket (Jasper → enterprise agents, Copy.ai → GTM AI, Writesonic → AI search visibility). Narrato — the closest unified workspace competitor — is shutting down June 15, 2026 (acquired by Typeface), creating an immediate opening.

### Direct Competitor Positioning

| Competitor | Segment | Entry Price | Brand Voice | Publishing | SEO | PersonnaPress Advantage |
|---|---|---|---|---|---|---|
| Jasper | Enterprise marketing | $59/seat/mo | 2 voices (Pro) | None | Limited | Deeper voice learning, native publishing, lower price |
| Copy.ai | GTM/Sales AI | $24/mo (chat) | Yes (shallow) | None | None | Content-focused vs. sales-focused |
| Writesonic | AI Search Visibility | $79/mo | 1 voice (Starter) | WordPress only | Strong | Multi-platform publishing, voice fidelity |
| Lately | Social repurposing | $14–$199/mo | Yes (strong) | Social only | None | Blog generation + social, SEO structure |
| Buffer | Social scheduling | $5/channel/mo | None | 11+ channels | None | AI generation + voice learning |
| ContentShake (Semrush) | SEO content | ~$60/mo add-on | None | None | Strong | Standalone, voice learning, publishing |

### Pricing Benchmarks

- Solopreneur comfort zone: $29–$79/mo
- Acceptable if replaces 2–3 tools: $99–$149/mo
- Churn risk: Above $150/mo without clear ROI
- PersonnaPress pricing ($29/$79/$199) positions at the lower end of the writing-tool market while delivering more value (generation + publishing) than any single competitor.

### Common User Complaints (across all competitors)

1. "Sounds like AI" — brand voice features are shallow mimicry, not genuine personal voice
2. Writing tools don't publish; scheduling tools can't write
3. No intelligent cross-platform adaptation (same text everywhere)
4. Pricing bloat — users cobble together 3+ tools ($200+/mo combined)
5. Enterprise features gate useful capabilities behind high-tier plans

## B. Architecture Decision Rationale (for downstream architecture doc)

### Why Decoupled Backend

Next.js serverless functions timeout after 10–60 seconds. LLM agent chains (Gemini 2.5 Flash with thinking budgets) and Replicate image generation routinely exceed this. FastAPI's native `BackgroundTasks` handle long-running operations and return 202 Accepted immediately. This is the foundational constraint driving the split architecture.

### Why Supabase Postgres (replaces SQLite)

Managed Postgres via Supabase provides: concurrent read/write support, connection pooling (PgBouncer), point-in-time recovery (PITR on Pro plan), no single-Droplet data dependency, and a clear path to horizontal scaling. The $6 DO Droplet now hosts only FastAPI + Nginx (compute layer), while all persistent data lives in Supabase. Cost: Supabase free tier for launch validation, Pro ($25/mo) for production PITR and higher connection/storage limits.

Trade-offs vs. SQLite: introduces a network hop for every DB query (latency), requires connection string management, and adds a service dependency. Acceptable given the reliability and scaling gains.

### Why Supabase Storage (replaces Nginx static files)

Supabase Storage provides CDN-backed file hosting with access control policies, eliminating the risk of disk failure = data loss on the Droplet. Generated FLUX images and uploaded brand content files are stored here. Nginx's role is reduced to reverse proxy only.

### Persistent Job Records

The original architecture used in-process APScheduler — if the process died, scheduled jobs were lost. The updated design persists all job records (generation tasks, publish tasks, scheduled publishes, retry state) in Supabase Postgres. APScheduler is configured with a SQLAlchemy-backed job store pointing at Supabase Postgres, so it recovers all pending jobs on restart. FastAPI BackgroundTasks remain the execution mechanism; the DB is the durability layer.

### Gemini 2.5 Flash Thinking Budget Strategy

| Task | Budget | Rationale |
|---|---|---|
| Social posts | 0 | Short, direct output — no reasoning needed |
| Blog drafts | 512 | Needs structure and voice adherence |
| Brand voice extraction | 1024 | Analytical task requiring deep reasoning |

### Infrastructure Scaling Path

| Stage | Compute | Database | Storage | Concurrency |
|---|---|---|---|---|
| Launch | $6 DO Droplet (1 vCPU / 1 GB) | Supabase Free/Pro | Supabase Storage | ~50 concurrent gen requests |
| Growth | $12 DO Droplet (2 vCPU / 2 GB) | Supabase Pro | Supabase Storage | ~100 concurrent gen requests |
| Scale | Container orchestration (DO App Platform / Fly.io) | Supabase Pro / dedicated Postgres | Supabase Storage | 100+ concurrent gen requests |

## C. Data Model Notes (for downstream architecture doc)

### Campaign Status State Machine

```
pending_approval → approved → published
                 → rejected → (regenerate) → pending_approval
                 → failed → (retry) → published
```

### Credential Storage Approach

All third-party credentials stored as AES-256-GCM encrypted TEXT in Supabase Postgres. Encryption key from environment variable on the FastAPI Droplet — the key never touches Supabase. v1 limitation: no key rotation mechanism, no HSM/KMS. Upgrade path: AWS KMS or HashiCorp Vault when moving to managed compute infrastructure.

### Entities for v1 Schema

The original architecture spec had 2 tables (`clients`, `campaigns`). The updated Supabase Postgres schema requires:

- `users` — account records, linked to Stripe customer IDs and Google OAuth subject IDs
- `subscriptions` — Stripe subscription state, plan tier, billing cycle, usage counters
- `clients` — brand identities owned by a user, with Brand Voice Profile JSON
- `platform_connections` — normalized table (one row per client-platform pair) replacing the inlined credential columns on `clients`. Required for Phase 2 platform additions.
- `campaigns` — content production records with status state machine
- `jobs` — persistent job records for generation, publishing, scheduling, and retry tracking. Columns: id, campaign_id, job_type, status, scheduled_at, started_at, completed_at, attempt_count, error_details, created_at.
- `generation_logs` — per-user API cost tracking (Gemini token usage, Replicate image count) for internal monitoring

## D. Design System Reference

Full design spec in `design.prd.md` at project root. Key tokens for downstream reference:

- **Aesthetic:** "Paper Style" — brutalist, academic, Notion-esque, ink & paper
- **Palette:** Paper (#F9F9F6), Ink (#111111), Graphite (#555555), Highlighter (#FFF1B8), Danger (#8B0000), Success (#2E4F2E)
- **Typography:** Playfair Display (headings), Inter (body), JetBrains Mono (brain dump input/code)
- **Components:** Sharp corners, flat/brutalist shadows, bottom-border inputs, monospace input fields, typewriter loading animation
- **Gaps for UX to resolve:** Responsive breakpoints, accessibility/WCAG compliance, spacing system, navigation structure, iconography, component states beyond hover, modal/toast patterns

## E. FLUX.1 [pro] Licensing Note

FLUX.1 [pro] is commercially licensed via Black Forest Labs / Replicate API. Unlike FLUX.1 [dev] (non-commercial), [pro] permits commercial use of generated images by end users. PersonnaPress Terms of Service must:
1. Disclose that featured images are AI-generated by FLUX.1 [pro]
2. Confirm user's right to use generated images commercially
3. Note that images are subject to FLUX.1 [pro] output license terms
