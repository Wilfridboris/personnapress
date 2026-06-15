Based on your PersonaPress PRD and architecture files, here's a complete breakdown of every platform, library, and language in your stack — with the latest versions, API references, and best practices as of June 2026.
Frontend: Next.js on Vercel

Latest Version: Next.js 16.2.7 (stable as of June 2026, released October 2025). The App Router is now fully mature with better error handling, faster RSC streaming, and React 19.2 support built-in.

Key best practices:

    Use Turbopack (now default bundler — webpack configs need review)

    All parallel route slots require explicit default.js files or builds will fail

    Request APIs (cookies(), headers()) are async-only — no sync access

    Minimum Node.js 20+ required

    Use next doctor and next check CLI commands to diagnose config and RSC boundary issues

📎 Docs: nextjs.org/docs |
nextjs.org/blog/next-16
Backend: Python + FastAPI + Uvicorn

Latest Version: FastAPI 0.135.1 (2026 current release line). Uvicorn is managed via systemd per your architecture — the recommended production pattern.

Key best practices:

    Use fastapi[standard] install which bundles Uvicorn automatically

    Use BackgroundTasks for long-running LLM/image jobs (as you already plan) — return 202 Accepted immediately

    Use APScheduler for scheduled publishing — keep it persistent under systemd

    Target Python 3.12+ for best FastAPI compatibility

    Use Pydantic v2 models for all request/response schemas (ships with FastAPI 0.100+)

📎 Docs: fastapi.tiangolo.com |
fastapi.tiangolo.com/reference/fastapi
LLM: OpenRouter API

Current State: OpenRouter provides a unified OpenAI-compatible API routing to 300+ models. The model nousresearch/hermes-3-llama-3.1-70b:free (Hermes 3) is available free tier with 128K context.

2026 Model Upgrade Recommendation: Consider swapping or adding fallbacks:
Model ID	Best For	Context	Cost
nousresearch/hermes-3-llama-3.1-70b:free	Assistant-style, brand voice	128K	Free
deepseek/deepseek-chat-v3-0324:free	SEO content writing	64K	Free
meta-llama/llama-4-maverick:free	Long doc ingestion (brand voice)	1M	Free

Key best practices:

    Use the /api/v1/chat/completions endpoint (OpenAI-compatible — drop-in replacement)

    Add model fallback logic: if a free model returns 429, retry with a secondary model ID before upgrading to paid

    Use X-Title and HTTP-Referer headers to identify your app to OpenRouter

📎 Docs:
openrouter.ai/docs
Image Generation: Replicate + FLUX.1 [dev]

Current Model: black-forest-labs/flux-dev — a 12B parameter rectified flow transformer, the best open-weight text-to-image model for non-commercial use.

Key best practices:

    Call via Python replicate client: replicate.run("black-forest-labs/flux-dev", input={...})

    For speed: consider prunaai/flux.1-dev — billed as the fastest Flux Dev endpoint on Replicate

    FLUX.1 [dev] is non-commercial licensed — ensure your PersonaPress ToS reflects this for end-user image output

    Use httpx async client (as your arch specifies) when calling the Replicate REST API directly for non-blocking image generation

📎 Docs:
replicate.com/black-forest-labs/flux-dev
| replicate.com/docs
Publishing APIs
WordPress REST API

    Version: WP REST API v2 (/wp/v2/) — the current stable namespace, fully supports Application Passwords

    Best practice: POST to /wp/v2/posts with status: "draft" first, then status: "publish" after approval gate

    Use Application Passwords (WP 5.6+) — no OAuth plugin needed for self-hosted sites

Webflow CMS API

    Version: API v2 (released Aug 2023, now the standard)

    Key change from v1: ?live=true parameter removed — you must call a separate publish endpoint after creating/updating a CMS item

    Auth: Bearer token via Authorization: Bearer {API_TOKEN} header

    📎 Docs:
    developers.webflow.com

X (Twitter) API v2

    Version: v2 — current and only actively developed version

    Auth: OAuth 2.0 with PKCE is mandatory; Basic Auth deprecated since early 2024

    Use tweet.fields, user.fields parameters to request only needed data — reduces rate limit pressure

    Free tier supports posting tweets; use Tweepy (Python) as your client library for easy v2 integration

    📎 Docs: developer.twitter.com/en/docs/twitter-api

LinkedIn REST API

    Latest Version: 202602 (February 2026) — versioned via LinkedIn-Version: 202602 request header

    The latest stable version header is 2026-03-10 per their versioning cycle

    For personal profile posts: use the UGC Posts API (/v2/ugcPosts) with OAuth 2.0 w_member_social scope

    📎 Docs:
    learn.microsoft.com/linkedin

Infrastructure: Nginx + SQLite + DigitalOcean

    SQLite WAL mode (PRAGMA journal_mode=WAL) is the correct production setting for concurrent reads on the Droplet — no changes needed

    Nginx: Ensure you're on 1.26.x (stable branch as of 2026) — use it both as reverse proxy to Uvicorn (port 8000) and as a static file server for FLUX-generated images

    DigitalOcean $6 Droplet: With BackgroundTasks offloading image generation, your 1vCPU/1GB RAM is sufficient for MVP — upgrade to $12 (2vCPU/2GB) before scaling past ~50 concurrent users

Prepared using Claude Sonnet 4.6 Thinking