---
baseline_commit: f0f063d3135dff9ceef58f7c0b0b1fe96e92a565
---

# Story 2.4: Brand Voice Ingestion — Website Scraping & Content Upload

Status: done

## Story

As an authenticated user,
I want the system to scrape my website and accept uploaded content files to gather writing samples,
So that PersonnaPress has enough of my writing to accurately learn my voice.

## Acceptance Criteria

1. **Given** a client with a website URL has an ingestion job queued, **When** the BackgroundTask executes in `workers/ingest.py`, **Then** `services/ingestion.py` uses httpx to fetch the website; BeautifulSoup is used to extract clean text from blog posts, about pages, and long-form pages; navigation menus, footers, sidebars, cookie banners, and ad containers are stripped; at least the 10 most recent blog posts are extracted, or all posts if fewer than 10 exist.

2. **Given** the website scraping completes successfully, **When** the extracted text is ready, **Then** it is passed in-memory to the voice extraction function (Story 2.5) within the same BackgroundTask — it is not stored as a separate database record.

3. **Given** the website URL is unreachable, returns a non-200 response, or scraping times out after 60 seconds, **When** the failure occurs, **Then** the `jobs` record is updated to `status='failed'` with descriptive `error_details`; `clients.brand_voice_profile` remains null; the client UI shows: "Couldn't extract content from [url]. Complete the voice questionnaire to set up your profile." with a primary CTA to the voice questionnaire.

4. **Given** a user navigates to the Client detail page and clicks "Upload content files," **When** they select up to 10 files (.txt, .md, or .docx, each no larger than 5 MB), **Then** each file is uploaded to Supabase Storage at path `brand-content/{client_id}/{filename}`; upload progress is shown per file; upon completion the file list is displayed with file names and sizes.

5. **Given** a user attempts to upload a file larger than 5 MB or in an unsupported format, **When** the file is selected, **Then** the frontend validates the file before initiating upload and shows an inline error: "File must be under 5 MB." or "Only .txt, .md, and .docx files are supported." — the upload is not initiated.

6. **Given** uploaded files exist for a client alongside scraped content, **When** the ingestion BackgroundTask processes voice extraction, **Then** text is extracted from each file (.txt/.md read directly; .docx parsed via python-docx), and the extracted file text is appended to scraped website text before being passed to Gemini for voice extraction.

7. **Given** the ingestion job is `in_progress`, **When** the client detail page or onboarding step 2 is viewed, **Then** a status message is shown in JetBrains Mono: "Scraping [domain]..." while fetching, then "Extracting voice profile..." during Gemini analysis; React Query polls `GET /api/v1/jobs/{job_id}` with `refetchInterval: 2000` until the job reaches a terminal state.

8. **Given** the number of uploaded files would exceed 10 per client, **When** the user tries to add a file, **Then** the frontend shows an inline error: "You've reached the 10-file limit for this client." and the upload is not initiated.

## Tasks / Subtasks

- [x] Task 1: Backend — Full `workers/ingest.py` implementation (AC: #1, #2, #3, #6)
  - [x] 1.1 Update the stub in `workers/ingest.py` (Story 2.1) to the full implementation:
    - Set `jobs.status='in_progress'`, `jobs.started_at=now()`
    - Fetch the `Client` record (get `website_url`, `id`)
    - Fetch any uploaded files for this client from Supabase Storage (`brand-content/{client_id}/`)
    - Call `services/ingestion.py → scrape_website(url)` if `website_url` is set
    - Call `services/ingestion.py → extract_file_text(file_bytes, filename)` for each uploaded file
    - Concatenate all text; pass combined text to `services/ingestion.py → extract_voice_profile(combined_text, client_id)` (Story 2.5)
    - On success: `jobs.status='complete'`, `jobs.completed_at=now()`
    - On any unhandled exception: `jobs.status='failed'`, `jobs.error_details=str(e)`; log to Sentry
  - [x] 1.2 Wrap the scraping step in a `try/except`; on scraping failure, do NOT abort the job — continue with uploaded-file text only if files exist; if no text at all, set `jobs.status='failed'` with `error_details`

- [x] Task 2: Backend — `services/ingestion.py` — website scraping (AC: #1, #2, #3)
  - [x] 2.1 Create `backend/app/services/ingestion.py`
  - [x] 2.2 Implement `async def scrape_website(url: str) -> str`:
    - Use `httpx.AsyncClient(timeout=60.0)` to fetch the website root URL
    - On non-200 response or timeout (`httpx.TimeoutException`, `httpx.ConnectError`): raise `ScrapingError(f"Could not reach {url}: HTTP {status}")`
    - Use BeautifulSoup4 (`html.parser`) to parse the page; find all `<a>` tags linking to blog/post/article paths (heuristic: URLs containing `/blog/`, `/post/`, `/article/`, `/news/`, path segments that look like slugs)
    - Fetch up to 10 blog post URLs (sorted by recency heuristic — last-modified meta or URL date patterns); extract clean text per page
  - [x] 2.3 Implement `def extract_clean_text(html_content: str) -> str`:
    - Parse with BeautifulSoup4; remove: `<nav>`, `<footer>`, `<header>`, `<aside>`, elements with class patterns matching `menu`, `cookie`, `banner`, `ad`, `sidebar`, `social`; extract text from `<article>`, `<main>`, `<p>`, `<h1>`–`<h3>` elements; join with newlines; strip excess whitespace
    - Return clean text string
  - [x] 2.4 Scraping function returns combined clean text from all extracted pages as a single string; limit total text to 50,000 characters before passing to Gemini (cost control)
  - [x] 2.5 Define `class ScrapingError(Exception): pass` in `services/ingestion.py` for clean exception handling in the worker

- [x] Task 3: Backend — `services/ingestion.py` — file text extraction (AC: #6)
  - [x] 3.1 Implement `def extract_file_text(file_bytes: bytes, filename: str) -> str`:
    - `.txt` files: decode as UTF-8 (with error replacement), return text
    - `.md` files: decode as UTF-8, return raw text (Markdown syntax acceptable for Gemini analysis)
    - `.docx` files: use `python-docx` (`from docx import Document; import io; doc = Document(io.BytesIO(file_bytes))`); join paragraph text with newlines; return string
    - Unknown extension: return empty string (file was validated on upload, so this is a safety fallback)
  - [x] 3.2 Add `python-docx` to `backend/requirements.txt`

- [x] Task 4: Backend — file upload API via Supabase Storage (AC: #4, #5, #8)
  - [x] 4.1 Create `backend/app/routers/files.py`; add `POST /api/v1/clients/{client_id}/files`; require auth; register in `main.py`
  - [x] 4.2 Accept `multipart/form-data` with `files: List[UploadFile] = File(...)`; use `python-multipart` (already in requirements)
  - [x] 4.3 Validate each file server-side: extension must be `.txt`, `.md`, or `.docx`; size must be ≤ 5,242,880 bytes (5 MB); count check: query existing files from Supabase Storage at `brand-content/{client_id}/` — if count + new files > 10, return HTTP 400 `FILE_LIMIT_REACHED`
  - [x] 4.4 Upload each valid file to Supabase Storage: used `httpx` to call Supabase Storage REST API directly (via `supabase_storage.py`)
  - [x] 4.5 Create `backend/app/integrations/supabase_storage.py` with `upload_file(bucket, path, bytes)` and `list_files(bucket, prefix)` and `download_file(bucket, path) -> bytes` functions — called only from services, not directly from routers
  - [x] 4.6 Return `FileUploadResponse`: list of `{filename, size, path}` for successfully uploaded files; partial success is acceptable (upload as many as possible, report failures per file)
  - [x] 4.7 Add `DELETE /api/v1/clients/{client_id}/files/{filename}` for future file management (stub only in v1 — return 204 after deleting from Supabase Storage)

- [x] Task 5: Backend — file listing API (AC: #4)
  - [x] 5.1 Add `GET /api/v1/clients/{client_id}/files` to `backend/app/routers/files.py`; require auth; verify client ownership
  - [x] 5.2 Call `supabase_storage.list_files("brand-content", f"{client_id}/")` → return list of `{filename, size}` objects
  - [x] 5.3 Return `FileListResponse`: `{"files": [{"filename": "...", "size": N}], "count": N, "limit": 10}`

- [x] Task 6: Backend — integrate file download into ingest worker (AC: #6)
  - [x] 6.1 In `workers/ingest.py`: before scraping, call `supabase_storage.list_files("brand-content", f"{client_id}/")` to get the list of uploaded files
  - [x] 6.2 For each file: call `supabase_storage.download_file("brand-content", f"{client_id}/{filename}")` → get bytes → call `extract_file_text(bytes, filename)`
  - [x] 6.3 Concatenate all file texts; append to scraped website text; the combined string goes to `extract_voice_profile()` (Story 2.5 — called from the worker after all text is assembled)

- [x] Task 7: Frontend — file upload UI on Client detail page (AC: #4, #5, #8)
  - [x] 7.1 Create `frontend/components/clients/FileUploadPanel.tsx` — `'use client'`; placed in the Client detail page below the BVP section
  - [x] 7.2 File input: hidden `<input type="file" multiple accept=".txt,.md,.docx" ref={fileInputRef} />`; trigger via a "Upload content files" Secondary Button
  - [x] 7.3 Client-side validation (before any API call):
    - Extension check: reject files where `!filename.match(/\.(txt|md|docx)$/i)` — show inline error "Only .txt, .md, and .docx files are supported."
    - Size check: reject if `file.size > 5 * 1024 * 1024` — show inline error "File must be under 5 MB."
    - Count check: if current file count + selected files > 10 — show "You've reached the 10-file limit for this client."
  - [x] 7.4 Upload progress per file: use `XMLHttpRequest` (not `fetch`) for progress tracking; show animated progress bar per file using animated `<div>` with `bg-ink` fill (h-0.5)
  - [x] 7.5 After successful upload: refresh the file list via `useQuery` invalidation; show file list with `filename` and human-readable size ("2.3 MB")
  - [x] 7.6 Call `POST /api/v1/clients/{id}/files` with `FormData` containing the validated files

- [x] Task 8: Frontend — ingestion in-progress status polling (AC: #7)
  - [x] 8.1 Create `frontend/hooks/useJobStatus.ts` — custom React Query hook: `useQuery({ queryKey: ['job', jobId], queryFn: () => fetchAPI('/jobs/' + jobId), refetchInterval: (data) => data?.status === 'pending' || data?.status === 'in_progress' ? 2000 : false })`
  - [x] 8.2 In `ClientDetail.tsx`: if active ingestion job exists, use `useJobStatus(jobId)` to poll; while `pending` or `in_progress`, show status message in JetBrains Mono:
    - Job `in_progress`: "Scraping [domain]..." → after a short delay "Extracting voice profile..." (cycle via `setInterval` between these messages locally; the actual backend phase is opaque at the polling level)
    - Job `complete`: invalidate `["client", clientId]` query to reload BVP data
    - Job `failed`: show error state "Couldn't extract content from [url]. Complete the voice questionnaire to set up your profile." + "Complete questionnaire" Primary Button → `/clients/{id}/voice`
  - [x] 8.3 `GET /api/v1/jobs/{job_id}` already existed from Story 2.1 in `backend/app/routers/jobs.py` — verified it satisfies AC requirements (auth, ownership check, correct response fields)

- [x] Task 9: Backend — `GET /api/v1/jobs/{job_id}` endpoint (AC: #7)
  - [x] 9.1 `backend/app/routers/jobs.py` already exists with `GET /api/v1/jobs/{job_id}`; require auth
  - [x] 9.2 Fetch job; verify ownership via `job.client_id → client.user_id == current_user["user_id"]`; return HTTP 403 on mismatch
  - [x] 9.3 Return `JobResponse`: `id`, `status`, `job_type`, `error_details`, `started_at`, `completed_at`
  - [x] 9.4 `jobs` router already registered in `main.py` under `/api/v1/jobs`

## Dev Notes

### Scraping Strategy

BeautifulSoup heuristics for blog post discovery:
1. Fetch the root URL and find all `<a>` tags where `href` contains path segments like `/blog/`, `/post/`, `/article/`, `/news/`, or matches patterns like `/YYYY/MM/slug`
2. Filter to unique, same-domain URLs only
3. Sort by recency heuristic: date in URL path (regex `\d{4}/\d{2}`) or publication date meta tag (`<meta property="article:published_time">`)
4. Fetch up to 10 most recent posts with `asyncio.gather` (concurrent fetches, max 5 concurrent)
5. If the site has no discoverable blog structure (e.g., a single-page app): fall back to extracting all long-form text from the root page

**60-second timeout:** Applied at the `httpx.AsyncClient(timeout=60.0)` level. The total scraping budget (root + 10 posts) should complete within this window; individual page timeouts are 10s each.

### File Upload Progress via XMLHttpRequest

```typescript
// frontend/components/clients/FileUploadPanel.tsx
const uploadWithProgress = (file: File, clientId: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('files', file)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        setProgress(prev => ({ ...prev, [file.name]: (e.loaded / e.total) * 100 }))
      }
    }
    xhr.onload = () => xhr.status < 400 ? resolve() : reject(xhr.responseText)
    xhr.onerror = () => reject('Network error')
    xhr.open('POST', `/api/v1/clients/${clientId}/files`)
    xhr.withCredentials = true  // send httpOnly session cookie
    xhr.send(formData)
  })
}
```

### File Upload UI — Paper Style

```
CONTENT FILES                          ← Inter 12px uppercase tracked label

No files uploaded yet.                 ← Inter Graphite, shown when list is empty

[ Upload content files ]               ← Secondary Button

────────────────────────────────────

sample-post.docx            23 KB      ← Inter 15px Ink filename, Graphite size
[████████████████████] 100%            ← progress bar (h-0.5, border-none, bg-[#111111])

brand-guidelines.txt        8 KB
```

### Ingestion Status Display — Paper Style

```
BRAND VOICE                            ← Inter 12px uppercase tracked label

Scraping example.com...                ← JetBrains Mono, Graphite, pulsing opacity
                                          className="font-mono text-sm text-[#555555]
                                          animate-pulse"

(changes to:)

Extracting voice profile...            ← Same styling, cycled via local interval
```

### Supabase Storage Path Convention

```
Bucket: brand-content
Path:   {client_id}/{original_filename}

Examples:
  550e8400-e29b-41d4-a716-446655440000/my-blog-post.docx
  550e8400-e29b-41d4-a716-446655440000/brand-guidelines.txt
```

Storage bucket must be set to private (no public URL) — files are only read server-side by the ingest worker.

### Text Concatenation Order

```python
# workers/ingest.py — text assembly
scraped_text = await scrape_website(client.website_url) if client.website_url else ""
file_texts = []
for filename in file_list:
    file_bytes = await supabase_storage.download_file("brand-content", f"{client.id}/{filename}")
    file_texts.append(extract_file_text(file_bytes, filename))

combined_text = "\n\n---\n\n".join(filter(None, [scraped_text] + file_texts))
combined_text = combined_text[:50_000]  # Cost control: cap at 50k chars before Gemini
```

### python-docx Note

`python-docx` requires its own import name: `from docx import Document` (not `import docx`). The package name in requirements.txt is `python-docx`, import name is `docx`.

### New Files This Story

```
backend/app/
├── services/ingestion.py        ← NEW — scrape_website(), extract_clean_text(), extract_file_text()
├── routers/files.py             ← NEW — POST /files, GET /files, DELETE /files/{filename}
├── routers/jobs.py              ← NEW — GET /jobs/{job_id}
└── integrations/supabase_storage.py ← NEW — upload_file(), list_files(), download_file()

frontend/
├── components/clients/FileUploadPanel.tsx ← NEW
└── hooks/useJobStatus.ts                  ← NEW
```

Updated files:
```
backend/app/workers/ingest.py     ← FULL implementation (was stub from Story 2.1)
backend/app/main.py               ← REGISTER files, jobs routers
backend/requirements.txt         ← ADD python-docx, supabase (or httpx for Storage REST)
frontend/components/clients/ClientDetail.tsx ← ADD file upload panel, ingestion polling
```

### References

- Story spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4]
- FR-8 (Website scraping, 60s timeout, 10 posts), FR-9 (file upload, .txt/.md/.docx, 5MB/10 file limits): [Source: _bmad-output/planning-artifacts/epics.md#Functional Requirements]
- AR-19 (service boundaries — ingestion.py is the only scraping service): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- NFR-7 (job durability): [Source: _bmad-output/planning-artifacts/architecture.md]
- Supabase Storage integration pattern: [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- JetBrains Mono for status messages: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Typography]
- Typewriter / monospace status styling: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#State Patterns]

## Dev Agent Record

### Implementation Notes

- Supabase Storage accessed via `httpx` calling the REST API directly (no `supabase-py` client needed — `httpx` already a dependency). `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` added to `config.py` settings.
- `extract_voice_profile()` stub in `services/ingestion.py` returns empty dict; full Gemini implementation deferred to Story 2.5. Ingest worker handles empty dict result gracefully by setting `brand_voice_profile = None`.
- Ingest worker uses a separate `AsyncSessionLocal()` context for the error-marking path (`_mark_failed`) to guarantee the error is persisted even if the main session is in a bad state.
- `jobs.py` router already existed from Story 2.1 with full ownership verification — Task 9 verified and confirmed complete.
- `ClientDetail.tsx` now uses `useJobStatus` (React Query v5) instead of the hand-rolled `setInterval`/`fetch` polling. Callbacks handled via `useEffect` watching query data (React Query v5 dropped `onSuccess`/`onError` callbacks from `useQuery`).
- `useIngestionMessage` custom hook cycles the "Scraping..." / "Extracting voice profile..." display strings on a 5-second interval while `isIngesting` is true.
- Progress bar implemented as animated `<div>` fill rather than `<progress>` element (better styling control with Tailwind, consistent with Paper Style).

### Debug Log

No blocking issues encountered.

## File List

**New files:**
- `backend/app/services/ingestion.py`
- `backend/app/integrations/supabase_storage.py`
- `backend/app/routers/files.py`
- `frontend/components/clients/FileUploadPanel.tsx`
- `frontend/hooks/useJobStatus.ts`
- `backend/tests/test_ingestion_service.py`
- `backend/tests/test_files_router.py`
- `backend/tests/test_ingest_worker.py`
- `backend/tests/test_jobs_router.py`

**Modified files:**
- `backend/app/workers/ingest.py` (full implementation replacing stub)
- `backend/app/main.py` (added `files` router import and registration)
- `backend/app/core/config.py` (added `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`)
- `backend/requirements.txt` (added `python-docx`)
- `frontend/components/clients/ClientDetail.tsx` (FileUploadPanel + useJobStatus + cycling status messages)
- `frontend/lib/api.ts` (added `filesApi`)
- `frontend/lib/types.ts` (added `FileItem`, `FileUploadedItem`, `FileUploadError`, `FileUploadResponse`, `FileListResponse`)
- `_bmad-output/implementation-artifacts/2-4-brand-voice-ingestion-scraping-upload.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Senior Developer Review (AI)

**Date:** 2026-07-01
**Reviewer:** wilfridboris (AI-assisted)
**Outcome:** Approved with fixes applied

### Findings Fixed

**HIGH — `_is_blog_url` over-broad fallback removed** (`backend/app/services/ingestion.py`):
The function had a third branch `len(segments) >= 2 and not any(...)` that matched virtually any multi-level URL path (e.g., `/about/team`, `/services/web`, `/contact/form`) as a "blog URL". This wasted the 10-post scraping budget on non-writing-sample pages. Fixed: removed the fallback; now only explicit `/blog/`, `/post/`, `/article/`, `/news/`, `/journal/` path patterns AND URL date patterns (`/YYYY/MM/`) qualify as blog pages.

**HIGH (Security) — Campaign-level jobs had no ownership check** (`backend/app/routers/jobs.py`):
When `job.client_id` was `None` (campaign-level job), the endpoint skipped ownership verification entirely — any authenticated user could poll another user's campaign job. Fixed: added `elif job.campaign_id` branch that follows the `Campaign → Client → user_id` chain to verify ownership. Added 3 new tests covering owner access, non-owner 404, and orphaned-job pass-through.

**MEDIUM — Scraping timeout was 10s, spec requires 60s** (`backend/app/services/ingestion.py`):
`httpx.Timeout(10.0, connect=10.0)` set a 10-second read timeout per page; AC #3 specifies 60 seconds. Fixed: changed to `httpx.Timeout(60.0, connect=10.0)` — 60s read timeout per page, 10s connect timeout, matching both the spec's intent and AC #3 ("scraping times out after 60 seconds").

**MEDIUM — `test_jobs_router.py` missing from File List** (story metadata):
File was created and referenced in test summary but not listed in the story's Dev Agent Record File List. Fixed: added to File List.

**LOW — Frontend validation returned early on first invalid file in batch** (`frontend/components/clients/FileUploadPanel.tsx`):
When a user selected multiple files and the first was invalid (wrong extension or too large), the entire batch was rejected silently. Valid files were never uploaded. Fixed: replaced early `return` with `continue` — each file is validated independently, invalid files are immediately shown as error entries in the upload progress list with the spec-required error messages, and valid files proceed to upload. `inlineError` state is now only used for global count-limit messages.

### Tests

58 backend tests: 58 passed, 0 failed, 0 skipped (docx test now runs — `python-docx` installed in test env).

## Change Log

- 2026-07-01: Implemented Story 2.4 — Brand Voice Ingestion via website scraping and file upload. Full ingest worker pipeline, Supabase Storage integration, file upload/list/delete API, and frontend FileUploadPanel with per-file progress bars and React Query polling for ingestion status.
- 2026-07-01: Code review fixes — tightened `_is_blog_url` heuristic, added campaign-job ownership check to jobs router, corrected scraping timeout to 60s, added missing test file to File List, improved frontend per-file validation error handling.
