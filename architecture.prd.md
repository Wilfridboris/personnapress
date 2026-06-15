# System Architecture: PersonaPress

## 1. Infrastructure Overview
* **Frontend UI:** Next.js (App Router), deployed on **Vercel**.
* **Backend API & Agent Engine:** **Python (FastAPI)**, deployed on a **DigitalOcean $6 Droplet** (1vCPU, 1GB RAM).
  * *Why decoupled?* Next.js serverless functions time out after 10-60 seconds. LLM agent chains and Replicate image generation take longer. FastAPI's native `BackgroundTasks` handle these long-running tasks perfectly while immediately returning a 202 response to the frontend.
* **Database:** SQLite (enabled with WAL mode) hosted locally on the Droplet SSD.
* **Process Manager:** Uvicorn managed via `systemd` (keeps the FastAPI app and APScheduler running persistently).
* **Web Server / Media Hosting:** Nginx (Reverse proxies API requests to Uvicorn and serves Flux images statically for $0 hosting).

## 2. AI & Third-Party Integrations
* **LLM Core:** Google Gemini 2.5 Flash (`gemini-2.5-flash`) via `google-genai` Python SDK (v2.x).
  * Thinking budget tuned per task: 0 (social posts), 512 (blog drafts), 1024 (brand voice extraction).
  * API key via `GEMINI_API_KEY` env var. Model overridable via `GEMINI_MODEL`.
* **Image Generation:** Replicate API (`black-forest-labs/flux-dev`).
* **Direct Post APIs:** WP REST API, Webflow CMS API v2, Twitter API v2 (Tweepy), LinkedIn UGC Posts API (version 202602).

## 3. Database Schema (SQLite)
```sql
PRAGMA journal_mode=WAL;

CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    website_url TEXT DEFAULT '',
    brand_voice_json TEXT,
    wp_credentials TEXT,
    webflow_token TEXT,
    x_oauth_keys TEXT,
    li_oauth_keys TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    raw_brain_dump TEXT NOT NULL,
    blog_title TEXT,
    blog_html TEXT,
    social_x_text TEXT,
    social_li_text TEXT,
    media_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending_approval',
    -- status values: pending_approval | approved | published | rejected | failed
    scheduled_time DATETIME,
    published_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);