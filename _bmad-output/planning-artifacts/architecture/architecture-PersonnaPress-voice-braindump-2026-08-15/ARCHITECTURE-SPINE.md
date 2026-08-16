---
name: 'Voice-to-text Brain Dump (Phase 2)'
type: architecture-spine
purpose: build-substrate
altitude: epic
paradigm: stateless-io-proxy
scope: 'Audio capture in browser → transcription via external API → transcript text rejoins existing Brain Dump → Campaign pipeline at the textarea boundary'
status: final
created: '2026-08-15'
updated: '2026-08-15'
binds: ['voice-braindump-capture', 'voice-transcription-api-integration']
sources: ['_bmad-output/planning-artifacts/architecture.md']
companions: []
---

# Architecture Spine — Voice-to-text Brain Dump (Phase 2)

## Design Paradigm

**Stateless I/O Proxy.** The voice pipeline is a pure adapter: audio in → text out. It joins the existing pipeline exactly where a typed Brain Dump would — at the textarea. No new state machine, no new job type, no schema migration. The Droplet never does speech inference; it proxies the audio bytes to an external transcription API and returns the text.

```
Browser
  └─ MediaRecorder (WebM/Opus or MP4)
       └─ POST /api/v1/voice/transcribe  (multipart)
            ← 202 {job_id}
       └─ GET /api/v1/jobs/{job_id}  [polls every 2s — existing pattern]
            ← {status: "complete", result: {transcript: "..."}}
       └─ BrainDumpInput textarea  ← rejoins existing flow
            └─ POST /api/v1/campaigns  (unchanged)

BackgroundTask (inside Droplet):
  └─ httpx → Groq POST /v1/listen  (audio bytes, ~0.1–0.3× real-time)
       └─ transcript text
            └─ UPDATE jobs SET status='complete', result='{"transcript": "..."}' WHERE id=...
```

## Inherited Invariants

| Inherited | From parent | Binds here |
| --- | --- | --- |
| Naming conventions (snake_case columns, PascalCase components, `use` hooks) | architecture.md | All new files |
| Router delegates, service orchestrates, integration calls external API | architecture.md | `routers/voice.py`, `services/voice.py`, `integrations/openai_audio.py` |
| Auth: JWT cookie on all protected routes (`get_current_user` dependency) | architecture.md | `POST /api/v1/voice/transcribe` |
| Rate limiting via slowapi | architecture.md | Voice endpoint adds its own limit on top |
| Error shape `{"error": {"code": "...", "message": "...", "detail": {}}}` | architecture.md | 413, 415, 503 responses |
| Supabase Storage: backend-only; frontend consumes public CDN URLs only | architecture.md | Audio bypasses Storage entirely (AD-V3) |

Note: The parent job-durability rule ("create a job record before every BackgroundTask dispatch") does **not** apply here because no BackgroundTask is dispatched (see AD-V2). This is an explicit, narrow exemption — not a precedent for other features.

## Invariants & Rules

### AD-V1 — Transcription is external-only; zero STT compute on Droplet

- **Binds:** `integrations/groq_audio.py`, `services/voice.py`
- **Prevents:** One builder loading Whisper locally (CPU-bound on 1 vCPU: even `faster-whisper tiny` runs at 2–5× real-time, meaning a 10-min brain dump takes 20–50 min and blocks all concurrent requests). Also prevents Google Cloud STT for long recordings — its async batch endpoint requires audio in GCS, violating AD-V3.
- **Rule:** All speech-to-text inference MUST be delegated to the Groq API via `httpx`; no STT model may be installed or loaded on the Droplet. Endpoint: `POST https://api.groq.com/openai/v1/audio/transcriptions`, model `whisper-large-v3-turbo`. Auth: `Authorization: Bearer {GROQ_API_KEY}`. Accepts `audio/webm` and `audio/mp4` natively. Free tier: ~7,200 audio-seconds/day.

### AD-V2 — Transcription uses BackgroundTask + job record; endpoint returns 202

- **Binds:** `POST /api/v1/voice/transcribe`, `workers/transcribe.py`, `jobs` table
- **Prevents:** Long recordings (up to ~15 min; Groq LPU processes audio at ~10–30s regardless of length) tying up a client HTTP connection unnecessarily — and prevents deviation from the parent job-durability pattern; also prevents deviation from the parent job-durability pattern
- **Rule:** `POST /api/v1/voice/transcribe` MUST create a `jobs` row (type `transcription`) and dispatch a `BackgroundTask` before returning `202 {job_id}`. The BackgroundTask streams audio to Groq via `await httpx.post(...)`, writes the transcript to `jobs.result` (`{"transcript": "..."}`) on success or `jobs.error_details` on failure, and sets `jobs.status` to the terminal state. Frontend polls `GET /api/v1/jobs/{job_id}` (existing pattern). DB migration required: one `result JSONB` nullable column added to the `jobs` table — the only schema change in this epic.

### AD-V3 — Audio bytes are never persisted

- **Binds:** Entire audio pipeline (router → service → integration)
- **Prevents:** Audio files accumulating in Supabase Storage or on Droplet disk (privacy risk, storage cost, no retention policy needed for input audio)
- **Rule:** `UploadFile` bytes travel in-process from the FastAPI multipart parser to the Groq API call and are discarded immediately after. They MUST NOT be written to disk, Supabase Storage, or any database column. Groq's own transient handling of audio as part of service delivery is not a violation of this rule.

### AD-V4 — Transcript rejoins the pipeline at the Brain Dump textarea boundary

- **Binds:** Frontend (`VoiceBrainDump.tsx`), backend response contract, data model
- **Prevents:** Voice path creating a new `Campaign` field (e.g., `brain_dump_audio_transcript`), a new job type, or a schema migration
- **Rule:** When `GET /api/v1/jobs/{job_id}` returns `status: "complete"`, the frontend reads `result.transcript` (string) and populates the existing `BrainDumpInput` textarea. The user may edit. Campaign creation proceeds via the unchanged `POST /api/v1/campaigns`. No new campaign field, no new job type beyond `"transcription"`. The only DB change is the `result JSONB` column on `jobs` (see AD-V2).

### AD-V5 — Browser capture via MediaRecorder; Web Speech API is banned

- **Binds:** `VoiceBrainDump.tsx`
- **Prevents:** A builder using the Web Speech API (Chrome-only, routes audio to Google's servers without explicit user disclosure, produces no downloadable blob, incompatible with the server-side transcription pipeline)
- **Rule:** Audio capture MUST use the `MediaRecorder` browser API. The emitted Blob MUST be sent as a multipart upload with its native MIME type: `audio/webm;codecs=opus` (Chrome/Firefox/Edge) or `audio/mp4` (Safari). The transcription provider MUST accept both natively — no server-side audio conversion.

### AD-V6 — Hard size cap and dedicated rate limit at FastAPI layer

- **Binds:** `POST /api/v1/voice/transcribe`
- **Prevents:** RAM exhaustion (10 concurrent × 10 MB = 100 MB — well within budget) and runaway transcription API costs
- **Rule:** Reject any upload with `Content-Length > 10 485 760` (10 MB) with HTTP 413 before reading the body. Enforce a separate slowapi limit of **5 transcription requests / hour / user** (keyed on `user_id` from JWT), in addition to the inherited global 10 req/min/user limit. **[ASSUMPTION: 5/hour — revisit post-launch based on usage data]**

## Consistency Conventions

| Concern | Convention |
| --- | --- |
| New route file | `backend/app/routers/voice.py` — prefix `/api/v1/voice` |
| New integration file | `backend/app/integrations/groq_audio.py` — single function `async def transcribe(content: bytes, mime_type: str) -> str` |
| New service file | `backend/app/services/voice.py` — validates size/type, creates job record, dispatches BackgroundTask |
| New worker file | `backend/app/workers/transcribe.py` — BackgroundTask: call integration, write result to `jobs.result`, update status |
| New frontend component | `frontend/components/campaigns/VoiceBrainDump.tsx` — MediaRecorder capture, progress indicator, upload, calls transcript callback |
| Error codes | `AUDIO_TOO_LARGE` (413), `AUDIO_FORMAT_UNSUPPORTED` (415), `TRANSCRIPTION_FAILED` (503), `TRANSCRIPTION_RATE_LIMITED` (429) |
| New env var | `GROQ_API_KEY` on Droplet only; add to `.env.example` |
| Allowed MIME types | `audio/webm`, `audio/webm;codecs=opus`, `audio/mp4`, `audio/mpeg`, `audio/wav` — validated in `services/voice.py` before sending to API |

## Stack

| Name | Version |
| --- | --- |
| Groq API endpoint | `https://api.groq.com/openai/v1/audio/transcriptions`, model `whisper-large-v3-turbo` |
| httpx (already in requirements) | existing |
| MediaRecorder (browser built-in) | Web API — no npm package |
| python-multipart (already in requirements) | existing |

No new backend packages needed — Groq REST API called directly via httpx. Groq SDK (`groq_audio-sdk`) is optional convenience only.

## Structural Seed

```
backend/
  app/
    routers/
      voice.py              ← POST /api/v1/voice/transcribe (size check, rate limit, create job, dispatch)
    services/
      voice.py              ← validate mime type, create job record, call BackgroundTask
    workers/
      transcribe.py         ← BackgroundTask: httpx → Groq, write jobs.result, set status
    integrations/
      groq_audio.py           ← async def transcribe(content: bytes, mime_type: str) -> str
    core/
      config.py             ← add GROQ_API_KEY: str field [ADOPTED — already pattern]
    models/
      job.py                ← add result: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
  alembic/versions/
    YYYYMMDD_HHMM_xxxx_add_result_to_jobs.py   ← ALTER TABLE jobs ADD COLUMN result JSONB

frontend/
  components/
    campaigns/
      VoiceBrainDump.tsx    ← mic button, MediaRecorder, upload, poll job, transcript callback
      BrainDumpInput.tsx    ← gains optional `onVoiceTranscript` prop; renders VoiceBrainDump
  hooks/
    useVoiceTranscription.ts  ← wraps upload + useJobStatus polling; returns {transcript, status}
```

### Concurrency model on 1 vCPU / 1 GB

```
1 vCPU / 1 GB RAM — 2 uvicorn async workers
├─ Worker A (async event loop)
│    ├─ req-1: POST /voice/transcribe → create job → dispatch BackgroundTask → return 202 (fast)
│    ├─ BackgroundTask-1: await httpx → Groq  (~1–3 min I/O wait, non-blocking)
│    ├─ BackgroundTask-2: await httpx → Groq  (co-operative, no CPU stall)
│    └─ req-N: poll /jobs/{id} ...                (instant DB read)
└─ Worker B (async event loop)
     └─ other routes (generation polling, publish, etc.)

RAM profile:
  - Upload phase: 10 MB audio buffer held briefly during multipart parse → Groq send
  - BackgroundTask phase: audio bytes released once httpx send completes; only job record in RAM
  - Peak: N concurrent uploads × 10 MB (upload phase only, seconds)
  - Budget: ~700 MB free after OS + FastAPI baseline
  - 5/hr/user rate limit → natural concurrency ceiling

Bottleneck: Groq API throughput and cost — not the Droplet
```

## Capability → Architecture Map

| Capability | Lives in | Governed by |
| --- | --- | --- |
| Audio capture (browser) | `VoiceBrainDump.tsx` | AD-V5 |
| Audio upload + job creation | `POST /api/v1/voice/transcribe` | AD-V2, AD-V6 |
| Transcription | `integrations/groq_audio.py` | AD-V1 |
| Transcript result storage | `jobs.result JSONB` (new column) | AD-V2 |
| Transcript polling | `GET /api/v1/jobs/{id}` (existing) | parent architecture |
| Audio persistence (none) | — | AD-V3 |
| Transcript handoff to Brain Dump | `BrainDumpInput.tsx` prop | AD-V4 |
| Campaign creation (unchanged) | `POST /api/v1/campaigns` | parent architecture |

## Deferred

- **Streaming transcription (real-time interim results):** Groq Live (WebSocket) would give users a real-time transcript as they speak — better UX for very long recordings. Requires a WebSocket relay in FastAPI and significant frontend changes. Defer until user research confirms it's wanted over the current record-then-upload UX.
- **Audio stored for replay / audit trail:** Not needed for v1 voice brain dump; revisit if enterprise compliance is a requirement.
- **Transcription language selection:** `[ASSUMPTION: English-only, consistent with PRD v1 constraint]`; add `language` param to `integrations/openai_audio.py` when multi-language is activated.
- **Alternative providers (AssemblyAI, Google Cloud STT for clips under 60s):** Provider is encapsulated in `integrations/groq_audio.py`; swapping requires changing only that file and the env var. Defer.
- **Per-user transcription cost tracking:** No `generation_logs` row for voice (it's an input assist, not a content generation event); revisit if costs become material.
