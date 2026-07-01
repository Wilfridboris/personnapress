# Story 2.5: Voice Profile Extraction, Review & Manual Questionnaire

Status: ready

## Story

As an authenticated user,
I want the system to analyze my collected content and produce an editable Brand Voice Profile — or guide me through a questionnaire if no content is available — so that all generated content sounds authentically like me.

## Acceptance Criteria

1. **Given** collected content (scraped website text and/or uploaded file text) is available in the ingestion BackgroundTask, **When** voice extraction runs, **Then** `integrations/gemini.py` is called with the full collected text and a 1024 thinking token budget; Gemini 2.5 Flash returns a structured Brand Voice Profile containing: `tone` (array of descriptor strings), `cadence` (object: avg_sentence_length int, variation_pattern string, paragraph_structure string), `banned_jargon` (array of strings). **And** `clients.brand_voice_profile` is updated with the returned JSON; the `jobs` record is set to `status='complete'`.

2. **Given** voice extraction completes successfully, **When** the Client Voice Setup page at `/clients/{id}/voice` is loaded, **Then** the extracted profile fields are pre-populated for user review: tone descriptors displayed as editable tags (add/remove); banned jargon listed as editable tags (add/remove); cadence fields shown with their values and editable text inputs; a "Confirm profile" primary CTA is present.

3. **Given** a user edits fields in the Brand Voice Profile review and clicks "Confirm profile," **When** the save action runs, **Then** `PATCH /api/v1/clients/{client_id}` updates `clients.brand_voice_profile` with the edited JSON; a success message shows: "Voice profile confirmed." — no exclamation mark.

4. **Given** the Gemini voice extraction call fails or returns a 5xx/429 error after 3 consecutive retries, **When** the failure is confirmed, **Then** the `jobs` record is set to `status='failed'` with `error_details` populated; the error is logged to Sentry; the client UI shows: "Voice profile extraction failed. Complete the questionnaire to set up your profile manually." with a primary CTA to the voice questionnaire.

5. **Given** no website content is available (no URL provided, scraping failed, or no files uploaded), **When** the user accesses the Brand Voice Setup page, **Then** the voice questionnaire (FR-10 fallback) is shown instead of an extraction result — the UI transitions directly to the questionnaire flow without showing an error.

6. **Given** a client with no voice profile and the user submits the voice questionnaire (three steps: tone sliders, sample text pastes, optional reference URLs), **When** the questionnaire is submitted, **Then** a `jobs` record is created before dispatch; a BackgroundTask calls Gemini 2.5 Flash with a 1024 thinking token budget passing slider values (converted to tone descriptors), sample texts (if provided), and reference writer URLs (if provided); the UI shows "Extracting your voice profile..." in JetBrains Mono label type.

7. **Given** the questionnaire wizard, **When** it is rendered, **Then** Step 1 shows three paired tone slider pairs (Formal↔Casual 1–5, Professional↔Friendly 1–5, Concise↔Elaborate 1–5); Step 2 shows up to 3 textarea fields labeled "Paste a piece of writing that sounds like you." (all optional); Step 3 (optional) shows up to 3 URL input fields labeled "A writer whose style you admire." with a "Skip this step" secondary link; each step shows a progress indicator ("Step 1 of 3"), "Back" (except Step 1), and "Next" buttons; the final step has "Submit questionnaire" as the primary CTA. **And** each slider pair has an accessible aria-label identifying both ends of the scale and the current numeric value is announced to screen readers.

8. **Given** a user is on the Voice Setup page with an existing (confirmed) voice profile, **When** the page loads, **Then** the profile is displayed in read-only "confirmed" mode with field values shown; an "Edit profile" Secondary Button switches to editable mode; a "Refresh voice profile" Secondary Button is also available (Story 2.6 scope).

## Tasks / Subtasks

- [ ] Task 1: Backend — `services/ingestion.py` — `extract_voice_profile()` (AC: #1, #4)
  - [ ] 1.1 Add `async def extract_voice_profile(combined_text: str, client_id: uuid.UUID, session) -> dict` to `backend/app/services/ingestion.py`
  - [ ] 1.2 Call `integrations/gemini.py → extract_brand_voice(text, thinking_tokens=1024)` — implement retry logic: up to 3 consecutive attempts on 5xx or 429 response (exponential backoff: 1s, 2s, 4s between retries)
  - [ ] 1.3 On 3 consecutive failures: raise `VoiceExtractionError`; the worker catches this and sets `jobs.status='failed'`; log to Sentry
  - [ ] 1.4 On success: update `clients.brand_voice_profile` with the returned JSON via `db/repositories/clients.py → update_client(session, client_id, brand_voice_profile=bvp_json)`
  - [ ] 1.5 Define `class VoiceExtractionError(Exception): pass` in `services/ingestion.py`

- [ ] Task 2: Backend — `integrations/gemini.py` — `extract_brand_voice()` (AC: #1, #4)
  - [ ] 2.1 Create `backend/app/integrations/gemini.py` if it does not exist
  - [ ] 2.2 Add `async def extract_brand_voice(text: str, thinking_tokens: int = 1024) -> dict`:
    - Use `google.generativeai` SDK: `genai.GenerativeModel("gemini-2.5-flash")`
    - Prompt instructs the model to analyze the text and return ONLY a JSON object with this schema:
      ```json
      {
        "tone": ["descriptor1", "descriptor2"],
        "cadence": {
          "avg_sentence_length": 18,
          "variation_pattern": "short punchy sentences, occasional long complex structures",
          "paragraph_structure": "3-5 sentences, opens with a claim"
        },
        "banned_jargon": ["leverage", "synergy", "circle back"]
      }
      ```
    - Set `generation_config={"thinking_budget": thinking_tokens}` per Gemini 2.5 Flash API
    - Parse the JSON response; validate it has `tone` (list), `cadence` (dict), `banned_jargon` (list)
    - If JSON parsing fails, raise `ValueError("Gemini returned invalid JSON")`
  - [ ] 2.3 `integrations/gemini.py` is called ONLY from `services/ingestion.py` and `services/generation.py` — never directly from routers or workers (AR-19)

- [ ] Task 3: Backend — questionnaire submission API (AC: #6)
  - [ ] 3.1 Add `POST /api/v1/clients/{client_id}/questionnaire` to `backend/app/routers/clients.py`; require auth; verify ownership
  - [ ] 3.2 Define `QuestionnaireRequest` schema in `backend/app/schemas/client.py`:
    ```python
    class QuestionnaireRequest(BaseModel):
        tone_sliders: dict  # {"formal_casual": 3, "professional_friendly": 4, "concise_elaborate": 2}
        sample_texts: List[str]  # 0–3 items
        reference_urls: List[str]  # 0–3 items (optional)
    ```
  - [ ] 3.3 Create `jobs` record (`job_type='questionnaire'` or `'ingestion'`, `status='pending'`) before dispatching BackgroundTask
  - [ ] 3.4 Dispatch `BackgroundTask(questionnaire_worker, job_id=job.id, client_id=client_id, questionnaire_data=request)`
  - [ ] 3.5 Return `{job_id}` immediately with HTTP 202

- [ ] Task 4: Backend — questionnaire worker (AC: #6)
  - [ ] 4.1 Add `async def questionnaire_worker(job_id, client_id, data: QuestionnaireRequest)` to `backend/app/workers/ingest.py`
  - [ ] 4.2 Convert slider values to tone descriptors:
    - formal_casual 1–2 → "formal", 3 → "balanced", 4–5 → "casual"
    - professional_friendly 1–2 → "professional", 4–5 → "conversational"
    - concise_elaborate 1–2 → "concise", 4–5 → "detailed"
  - [ ] 4.3 Build combined text: join sample_texts with "\n\n---\n\n"; append reference URL notes if provided
  - [ ] 4.4 Build prompt for Gemini with slider-derived tone descriptors as context + sample texts; call `extract_voice_profile()` with 1024 thinking tokens
  - [ ] 4.5 On success: `clients.brand_voice_profile` updated; `jobs.status='complete'`
  - [ ] 4.6 On failure (after 3 retries): `jobs.status='failed'`; log to Sentry

- [ ] Task 5: Frontend — `/clients/{id}/voice` page (AC: #2, #3, #4, #5, #8)
  - [ ] 5.1 Create `frontend/app/(app)/clients/[id]/voice/page.tsx` — Server Component with metadata; fetch `GET /api/v1/clients/{id}` for current BVP and active job status
  - [ ] 5.2 Create `frontend/components/clients/VoiceSetupPage.tsx` — `'use client'` for all interactive state
  - [ ] 5.3 Page routing logic:
    - If `brand_voice_profile` exists (non-null): show **Profile Review** (confirmed or edit mode, AC #8)
    - If active ingestion job (pending/in_progress): show **In-Progress State** (JetBrains Mono status)
    - If failed ingestion job: show **Extraction Failed** error + questionnaire CTA
    - If no BVP, no active job, no failed job: show **Questionnaire** directly (AC #5)

- [ ] Task 6: Frontend — Profile Review UI (AC: #2, #3, #8)
  - [ ] 6.1 Layout: Playfair Display H1 "Brand Voice" (or H2 within Client context); Paper background
  - [ ] 6.2 **Tone descriptors** section ("TONE" — Inter 12px uppercase label):
    - Display as editable tag chips: `<span className="inline-flex items-center gap-1 bg-[#E5E5E5] px-2 py-0.5 text-sm text-[#111111] rounded-none mr-2 mb-2">`
    - Each tag has an `×` remove button (`<button aria-label="Remove tone: {tag}">`)
    - Below tags: text input to add new descriptors + "Add" button (Secondary style); on submit append to tone array
  - [ ] 6.3 **Cadence** section ("CADENCE" — Inter 12px uppercase label):
    - `avg_sentence_length`: editable `<input type="number">` (Paper Style standard input)
    - `variation_pattern`: editable `<textarea>` (2 rows, standard bottom-border)
    - `paragraph_structure`: editable `<textarea>` (2 rows)
  - [ ] 6.4 **Banned Jargon** section ("BANNED JARGON" — Inter 12px uppercase label):
    - Same editable tag chip pattern as tone descriptors
    - Each tag removable; add-new input below
  - [ ] 6.5 "Confirm profile" Primary Button: calls `PATCH /api/v1/clients/{id}` with `{brand_voice_profile: editedBVP}`; on success shows `<p className="text-[#2E4F2E] text-sm mt-2">Voice profile confirmed.</p>`
  - [ ] 6.6 "Edit profile" Secondary Button (shown in confirmed state): switches tags/inputs from read-only display to editable mode

- [ ] Task 7: Frontend — Voice Questionnaire wizard (AC: #5, #6, #7)
  - [ ] 7.1 Create `frontend/components/clients/VoiceQuestionnaire.tsx` — `'use client'`; multi-step wizard with `currentStep: 1 | 2 | 3` state
  - [ ] 7.2 Progress indicator: `<p className="font-['Inter'] text-xs uppercase tracking-[0.06em] text-[#555555]">Step {step} of 3</p>` — top of wizard
  - [ ] 7.3 **Step 1 — Tone Sliders:**
    - Three slider pairs, each with label showing both ends and current numeric value
    - Slider: `<input type="range" min="1" max="5" step="1">` with `className="w-full accent-[#111111]"`
    - Labels: "Formal" (left) / "Casual" (right), current value announced via `aria-valuenow` and `aria-valuetext`
    - Each slider: `aria-label="Formal to Casual tone — currently {value}"`
  - [ ] 7.4 **Step 2 — Sample Texts:**
    - Three `<textarea>` fields (Brain Dump style: JetBrains Mono, bottom-border-only, min-height 100px)
    - Label: "Paste a piece of writing that sounds like you." (optional)
    - All three are optional; user can leave blank
  - [ ] 7.5 **Step 3 — Reference Writers (optional):**
    - Three Paper Style standard `<input type="url">` fields
    - Label: "A writer whose style you admire." per field
    - "Skip this step" Secondary Button below all three — advances to submit without setting reference URLs
  - [ ] 7.6 Navigation buttons:
    - "Back" Secondary Button (not shown on Step 1): `setCurrentStep(step - 1)`
    - "Next" Primary Button (Steps 1–2): `setCurrentStep(step + 1)`
    - "Submit questionnaire" Primary Button (Step 3): calls `POST /api/v1/clients/{id}/questionnaire`
  - [ ] 7.7 On submit: show in-progress state "Extracting your voice profile..." (JetBrains Mono, Graphite); poll `useJobStatus(jobId)` until complete
  - [ ] 7.8 On job `complete`: refresh page to show Profile Review with extracted BVP pre-populated

- [ ] Task 8: Backend — update `PATCH /api/v1/clients/{id}` to accept BVP (AC: #3)
  - [ ] 8.1 Extend `ClientUpdate` schema to include `brand_voice_profile: Optional[dict] = None`
  - [ ] 8.2 In `update_client()` repository: if `brand_voice_profile` is provided, update `clients.brand_voice_profile`
  - [ ] 8.3 No re-ingestion triggered by this PATCH — BVP update is a direct overwrite of the JSON field

## Dev Notes

### Gemini API Configuration

```python
# backend/app/integrations/gemini.py
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

async def extract_brand_voice(text: str, thinking_tokens: int = 1024) -> dict:
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"thinking_budget": thinking_tokens}
    )
    response = await model.generate_content_async(
        f"""Analyze the following text and extract a Brand Voice Profile.

Return ONLY a valid JSON object with this exact schema:
{{
  "tone": ["list", "of", "style", "descriptors"],
  "cadence": {{
    "avg_sentence_length": <integer>,
    "variation_pattern": "<string>",
    "paragraph_structure": "<string>"
  }},
  "banned_jargon": ["words", "or", "phrases", "to", "avoid"]
}}

No markdown code blocks, no explanation. Raw JSON only.

TEXT TO ANALYZE:
{text[:50000]}"""
    )
    import json
    return json.loads(response.text.strip())
```

### Retry Pattern for Gemini Calls

```python
# backend/app/services/ingestion.py
import asyncio

async def extract_voice_profile(combined_text, client_id, session):
    last_error = None
    for attempt in range(3):
        try:
            bvp = await gemini.extract_brand_voice(combined_text, thinking_tokens=1024)
            await update_client(session, client_id, brand_voice_profile=bvp)
            return bvp
        except Exception as e:
            last_error = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s
    sentry_sdk.capture_exception(last_error)
    raise VoiceExtractionError(str(last_error))
```

### Questionnaire Slider → Tone Descriptor Mapping

```python
SLIDER_TONE_MAP = {
    "formal_casual": {1: "formal", 2: "somewhat formal", 3: "balanced", 4: "conversational", 5: "casual"},
    "professional_friendly": {1: "professional", 2: "business-like", 3: "approachable", 4: "friendly", 5: "warm"},
    "concise_elaborate": {1: "concise", 2: "direct", 3: "balanced", 4: "detailed", 5: "thorough"},
}
```

### Voice Profile Review — Paper Style Layout

```
BRAND VOICE                              ← Inter 12px uppercase tracked

TONE                                     ← Inter 12px uppercase tracked section label

  [authoritative ×] [direct ×] [+ Add]

CADENCE

  Avg. sentence length                   ← Inter 12px uppercase tracked
  [18]                                   ← number input, bottom-border-only

  Variation pattern
  [Short punchy sentences mixed with...] ← textarea, bottom-border-only

  Paragraph structure
  [3-5 sentences, opens with a claim]

BANNED JARGON

  [leverage ×] [synergy ×] [+ Add]

[        Confirm profile        ]        ← Primary Button (Ink, 4px shadow)

[ Refresh voice profile ]               ← Secondary Button (see Story 2.6)
```

### Questionnaire — Paper Style Layout

```
Step 1 of 3                             ← Inter 12px uppercase tracked, Graphite

TONE STYLE                             ← Inter 12px uppercase tracked label

Formal ─────────────────────── Casual
       1   2   [3]  4   5
       ↑ current value

Professional ──────────────── Friendly
       1   2   3   [4]  5

Concise ──────────────────── Elaborate
      [2]  3   4   5

[          Next          ]              ← Primary Button
```

### Tag Chip Component

```tsx
// frontend/components/ui/TagChip.tsx
interface TagChipProps {
  label: string
  onRemove: () => void
}

export function TagChip({ label, onRemove }: TagChipProps) {
  return (
    <span className="inline-flex items-center gap-1 bg-[#E5E5E5] px-2 py-0.5 text-sm text-[#111111] mr-2 mb-2 rounded-none">
      {label}
      <button
        onClick={onRemove}
        aria-label={`Remove: ${label}`}
        className="text-[#555555] hover:text-[#111111] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#111111]"
      >
        ×
      </button>
    </span>
  )
}
```

### Architecture Rules

- `integrations/gemini.py` is called only from `services/ingestion.py` (voice extraction) and `services/generation.py` (blog/social generation). No other call sites (AR-19)
- The questionnaire path and the scraping path both eventually call `extract_voice_profile()` — they converge at the same Gemini call with different input text
- Voice profile is stored as raw JSON in `clients.brand_voice_profile`; no schema enforcement at the DB level — validation happens at the service layer

### New Files This Story

```
backend/app/integrations/gemini.py             ← NEW (or expanded) — extract_brand_voice()
frontend/app/(app)/clients/[id]/voice/page.tsx ← NEW
frontend/components/clients/VoiceSetupPage.tsx ← NEW
frontend/components/clients/VoiceQuestionnaire.tsx ← NEW
frontend/components/ui/TagChip.tsx             ← NEW
```

Updated files:
```
backend/app/services/ingestion.py     ← ADD extract_voice_profile()
backend/app/workers/ingest.py         ← ADD questionnaire_worker()
backend/app/routers/clients.py        ← ADD POST /questionnaire
backend/app/schemas/client.py        ← ADD QuestionnaireRequest, extend ClientUpdate
frontend/components/clients/VoiceSetupPage.tsx ← full implementation
```

### References

- Story spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5]
- FR-10 (Voice Profile Extraction, Gemini 1024t, manual questionnaire fallback): [Source: _bmad-output/planning-artifacts/epics.md#Functional Requirements]
- AR-19 (gemini.py called only from generation.py / ingestion.py): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- NFR-9 (Gemini thinking budget: 1024 for ingestion, 3 retry cap): [Source: _bmad-output/planning-artifacts/epics.md#Non-Functional Requirements]
- UX-DR12 (Voice Questionnaire 3-step wizard spec — sliders, samples, URLs): [Source: _bmad-output/planning-artifacts/epics.md#UX Design Requirements]
- Slider accessible label pattern: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR16]
- Paper Style tags, inputs, buttons: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Components]
- Microcopy — "Voice profile confirmed." (no exclamation mark): [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]
