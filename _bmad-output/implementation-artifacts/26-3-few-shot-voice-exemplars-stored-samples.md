# Story 26.3: Few-Shot Voice Exemplars from Stored Samples

Status: ready-for-dev

## Story

As a writer,
I want the system to keep my actual writing samples and show them to the model as exemplars at generation time,
so that the model imitates real examples of my writing instead of following abstract instructions about it.

## Acceptance Criteria

1. **Given** ingestion currently discards raw text after extraction, **When** ingestion completes (scrape, file upload, or questionnaire samples), **Then** up to 12 representative sample excerpts (200-600 chars each, sentence-boundary trimmed, deduplicated) are stored in a new `voice_samples` JSONB column on `clients` (list of `{text, source, added_at}`), selected to maximize diversity of length and register; a migration is generated via the Alembic CLI.

2. **Given** questionnaire sample texts and voice transcripts already pass through the pipeline, **When** they are processed, **Then** their excerpts are stored with `source="questionnaire"` or `source="transcript"` alongside scraped ones.

3. **Given** blog generation with a BVP present, **When** the prompt is built, **Then** 2-3 stored samples are injected in a clearly delimited WRITING SAMPLES block with the instruction "match the rhythm, punctuation, casing, and register of these samples; do not copy their content", and the fidelity prompt receives the same samples as reference.

4. **Given** social generation (linked and standalone), **When** the prompt is built, **Then** 1-2 short samples are injected per request, preferring shorter excerpts for platform posts.

5. **Given** a client with no stored samples (legacy client, skipped voice setup), **When** generation runs, **Then** the samples block is omitted entirely and behavior is unchanged.

6. **Given** the voice tab in `ClientDetailTabs`, **When** a profile has stored samples, **Then** the user can view them and delete individual samples; a rescan replaces `source="scrape"` samples but preserves questionnaire and transcript samples.

7. **Given** tests, **When** run, **Then** they cover excerpt selection (dedup, length bounds, sentence boundaries), migration up/down, prompt injection for blog and social on both providers, legacy no-samples path, and rescan preservation semantics.

## Tasks / Subtasks

- [ ] Task 1: Schema and migration (AC: 1)
  - [ ] Add `voice_samples` JSONB nullable column to `Client` in `backend/app/db/repositories/models.py`.
  - [ ] Generate the migration with the Alembic CLI (`cd backend && alembic revision --autogenerate -m "add_voice_samples_to_clients"`). NEVER hand-write a revision ID (a hand-written duplicate ID blocked all deployments in July 2026).
- [ ] Task 2: Excerpt selection service (AC: 1, 2)
  - [ ] New `select_voice_samples(texts: list[tuple[str, str]]) -> list[dict]` in `backend/app/services/ingestion.py` (or a small sibling module): input (text, source) pairs; output up to 12 `{text, source, added_at}` dicts.
  - [ ] Selection rules: split on paragraph boundaries, trim each candidate to sentence boundaries within 200-600 chars, drop near-duplicates (normalized-prefix comparison is enough, no embeddings), pick for diversity: mix of short (200-300) and long (400-600) excerpts, cap 12 total, deterministic given the same input.
  - [ ] Wire into `ingest_worker` (scrape + file paths) and the questionnaire worker; transcripts: when a voice transcription result is used for voice setup, store excerpts with `source="transcript"` (only where transcripts already reach ingestion; do not build a new transcript-to-voice pipeline in this story).
- [ ] Task 3: Prompt injection (AC: 3, 4, 5)
  - [ ] New `_build_samples_block(samples, max_count, prefer_short)` in `generation_prompts.py`: delimited block `WRITING SAMPLES (match the rhythm, punctuation, casing, and register of these samples; do not copy their content):` with numbered samples in quotes; sanitize embedded newlines to spaces and escape double quotes (same guards as 16-6).
  - [ ] Blog prompt: inject 2-3 samples. Fidelity prompt (`_FIDELITY_PROMPT`): pass the same samples so scoring judges against real examples.
  - [ ] Social prompts (linked + standalone): inject 1-2 samples, `prefer_short=True`.
  - [ ] No samples: block omitted entirely, zero behavioral change (assert in tests).
  - [ ] Assist mode: NO samples injection (assist bypasses voice by design).
  - [ ] Plumb `voice_samples` from campaign generation call sites (`services/generation.py` fetches the client; pass samples alongside `brand_voice_profile` through both providers' function signatures).
- [ ] Task 4: Voice tab samples UI (AC: 6)
  - [ ] In the `ClientDetailTabs` voice tab, add a "Writing samples" section listing stored samples: source label (Website, Questionnaire, Voice note), excerpt text (clamped to 3 lines with expand), delete button per row.
  - [ ] Delete: `DELETE /clients/{id}/voice-samples/{index}` or a PATCH updating the array; follow the existing clients router auth/ownership pattern; optimistic update via TanStack Query with invalidation.
  - [ ] Empty state: single quiet line "No writing samples stored yet. Rescan your website or add questionnaire samples to collect some." (no em-dashes, no exclamation marks).
- [ ] Task 5: Rescan semantics (AC: 6)
  - [ ] In `ingest_worker`: on successful rescan, replace only `source="scrape"` entries; preserve questionnaire and transcript entries. On FAILED rescan, preserve ALL existing samples (mirror the fix-rescan-preserve-profile-on-failure rule: write only on success).
- [ ] Task 6: Tests (AC: 7)
  - [ ] Selection: length bounds, sentence-boundary trim, dedup, determinism, 12-cap, diversity mix.
  - [ ] Migration: upgrade/downgrade heads clean.
  - [ ] Injection: blog 2-3 samples, social 1-2 short, omitted when empty, sanitization of quotes/newlines, both provider test files, fidelity prompt receives samples, assist mode has none.
  - [ ] Rescan: scrape-only replacement, failure preserves all.
  - [ ] Frontend: samples render with source labels, delete flow, empty state.

## Dev Notes

### Why this story exists (evidence, 2026-09-05 code analysis)

- `scrape_website()` (`ingestion.py:133-211`) fetches up to 10 posts and `extract_file_text()` (214-237) processes uploads, but the combined text is used ONLY for extraction and then discarded. Nothing raw survives to generation time.
- Voice transcripts are stored via the transcription job but never referenced by `generation.py` or any prompt.
- `signature_phrases` and `voice_anchor_sentences` are injected as instructions ("use these phrases"), not exemplars. Few-shot imitation of real samples is the strongest known lever for "sounds like me" and it is entirely absent.

### Constraints and guardrails

- Alembic CLI only for the migration; timestamped filename comes from `alembic.ini` file_template. Downgrade must drop the column.
- Prompt-size discipline: 3 samples at 600 chars is ~1800 chars added to the blog prompt; acceptable. Do NOT inject all 12.
- Sanitize sample text in the prompt block (newlines to spaces, escape double quotes); samples are user-controlled content entering a prompt.
- No em-dashes or double-dashes in UI copy or the injected instruction line.
- Provider parity: both `gemini.py` and `anthropic_client.py` signatures change; tests in both test files.
- Ordering with 26.2: independent; both touch `generation_prompts.py` but different builders. If 26.2 is not yet merged, do not block on it.
- Story 26.4 will add a repair loop that re-uses the fidelity prompt; keeping samples in `_FIDELITY_PROMPT` via a parameter (not a global) makes that reuse clean.

### Existing behavior that must not break

- fix-rescan-preserve-profile-on-failure semantics: failed ingest must not destroy prior state. Samples follow the same rule: write only on success.
- 16-2 enrichment merge on refresh applies to BVP fields; `voice_samples` is managed separately by this story's replace/preserve rule, not the BVP merge.
- Legacy clients with `voice_samples=NULL` generate exactly as today (AC 5); the JSONB column is nullable, no backfill.
- `ingest_worker` continues to never fail the whole job because of sample selection; wrap selection in try/except like stylometry is wrapped (16-1 review patch pattern).

### UI/UX design guidance (web-uiux-architect, adapted to Paper Style)

- Paper Style: `rounded-none`, ink borders, paper background, hard offset shadows for cards; no glassmorphism, no dark mode variants (project has none).
- Sample rows: source label as a small uppercase tag (existing tag idiom in the voice tab), excerpt in regular text with `line-clamp-3` and an expand toggle; expand is a real button with `aria-expanded` and `focus-visible:ring-2` (16-7 and 15-1 reviews both patched missing aria-expanded; do not repeat).
- Delete button: Lucide `Trash2` icon-only with `aria-label="Delete this writing sample"` and minimum 44x44px touch target via padding; confirm destructive action inline (small "Delete? Yes / No" swap), not a modal, since a sample is low-stakes.
- Motion: CSS only (`transition-colors duration-300`); no Framer Motion for row hover/expand.
- No emojis anywhere.

### Source tree components to touch

- `backend/app/db/repositories/models.py` (UPDATE: Client.voice_samples)
- `backend/alembic/versions/` (NEW via CLI)
- `backend/app/services/ingestion.py` (UPDATE: selection + wiring), questionnaire worker (UPDATE)
- `backend/app/workers/ingest.py` (UPDATE: rescan replace/preserve, failure preservation)
- `backend/app/integrations/generation_prompts.py` (UPDATE: samples block, fidelity prompt param)
- `backend/app/integrations/gemini.py`, `backend/app/integrations/anthropic_client.py` (UPDATE: signatures + passthrough)
- `backend/app/services/generation.py` (UPDATE: fetch + pass samples)
- `backend/app/routers/clients.py` (UPDATE: delete-sample endpoint)
- `frontend/components/clients/ClientDetailTabs.tsx` (UPDATE: samples section), `frontend/lib/api.ts` (UPDATE)
- Tests: `backend/tests/test_ingestion*` or new `test_voice_samples.py`, both provider test files, frontend voice tab tests

### Testing standards summary

- Backend: pytest with mocked provider clients; selection tests are pure. Assert provider mock called WITH samples present in prompt text.
- Frontend: vitest + testing-library; TanStack Query test wrapper per existing voice tab tests.

### Project Structure Notes

- Server components never fetch this data directly: voice tab data flows through TanStack Query in client components (RSC loop rule in project-context.md).
- Delivery/consumption split: sample selection is a service; prompt formatting stays in `generation_prompts.py`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 26, Story 26.3]
- [Source: backend/app/services/ingestion.py:133-211, 214-237 (scrape and file text, discarded today)]
- [Source: backend/app/integrations/generation_prompts.py:316-339 (_FIDELITY_PROMPT)]
- [Source: _bmad-output/implementation-artifacts/fix-rescan-preserve-profile-on-failure.md (write-only-on-success rule)]
- [Source: _bmad-output/project-context.md (Alembic CLI rule, no em-dash rule, RSC data-fetching rule)]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
