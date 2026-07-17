---
baseline_commit: 42ed019a11a827808a4ba5d7c682eb54348f6326
---

# Story 16.1: Computed Stylometric Metrics Pre-processing

Status: done

## Story

As a PersonnaPress system,
I want to compute five measurable writing style metrics from raw text using Python libraries before Gemini extraction,
so that the BVP contains objective, reproducible values that complement qualitative LLM analysis.

## Acceptance Criteria

### AC 1 -- New dependencies

1. **Given** `textstat` and `spacy` (with `en_core_web_sm` model) are added to `backend/requirements.txt`, **When** the backend starts, **Then** `import textstat` and `spacy.load("en_core_web_sm")` both succeed without error; the spaCy model download is documented in the deploy runbook comment at the top of `deploy.sh` (one line: `# python -m spacy download en_core_web_sm`).

---

### AC 2 -- `compute_stylometric_fields` function

2. **Given** raw text is passed to `compute_stylometric_fields(text: str) -> dict` in `backend/app/services/stylometry.py`, **When** the function runs, **Then** it returns a dict with exactly these 5 keys computed without any external API call:

   - `sentence_length_avg` (int): mean words per sentence, rounded to nearest int; computed via spaCy sentence segmentation
   - `sentence_rhythm` (str): `"uniform"` if sentence-length standard deviation < 4, else `"varied"`
   - `paragraph_density` (str): `"airy"` if mean sentences per paragraph <= 2, `"moderate"` if 3-4, `"dense"` if >= 5; paragraphs are split on double newlines (`\n\n`)
   - `contraction_frequency` (str): `"never"` if 0 contractions found, `"occasional"` if contraction rate (contractions / total tokens) < 0.05, `"frequent"` if >= 0.05; contractions detected as tokens containing apostrophes (e.g. `don't`, `we'll`, `I'm`)
   - `list_preference` (str): `"rarely"` if < 5% of paragraphs start with a list marker (`- `, `* `, or `1.` / digit-dot pattern), `"sometimes"` if 5-20%, `"often"` if > 20%

3. **Given** text with fewer than 300 words, **When** `compute_stylometric_fields` runs, **Then** it returns the 5 computed fields based on available text PLUS a `low_confidence: True` key; it never raises an exception and never blocks the extraction pipeline.

---

### AC 3 -- Integration into ingestion pipeline

4. **Given** the ingestion pipeline in `backend/app/services/ingestion.py`, **When** website content (FR-8) or uploaded file content (FR-9) is collected and combined into `combined_text`, **Then** `compute_stylometric_fields(combined_text)` is called BEFORE the Gemini `extract_brand_voice` call; its returned dict is merged into the BVP dict using `bvp.update(computed_fields)` so the 5 computed keys are stored alongside the Gemini-extracted fields.

5. **Given** the FR-11 refresh pipeline (voice profile refresh), **When** re-extraction is triggered, **Then** `compute_stylometric_fields` runs on the new combined text and the returned 5 fields overwrite only those 5 keys in the existing BVP; no other BVP keys are touched during the computed-fields update step.

---

### AC 4 -- Unit tests

6. **Given** `backend/tests/test_stylometry.py`, **When** the test suite runs, **Then** it covers:
   - Normal text (300+ words): all 5 fields returned, `low_confidence` key absent
   - Short text (< 300 words): all 5 fields returned plus `low_confidence: True`
   - Text with no contractions: `contraction_frequency == "never"`
   - Text where > 20% paragraphs are bullet lists: `list_preference == "often"`
   - Text with highly uniform sentence lengths (stddev < 4): `sentence_rhythm == "uniform"`
   - Text with varied sentence lengths (stddev >= 4): `sentence_rhythm == "varied"`

---

## Tasks / Subtasks

### Task 1 -- Add dependencies (AC 1)

- [x] 1.1 Add `textstat` and `spacy` to `backend/requirements.txt`
- [x] 1.2 Add `# python -m spacy download en_core_web_sm` as a comment near the top of `deploy.sh` (deploy runbook section); do not add it as an executable step
- [x] 1.3 Verify `import textstat` and `spacy.load("en_core_web_sm")` work in the backend virtual environment

---

### Task 2 -- Create `services/stylometry.py` (AC 2, 3)

- [x] 2.1 Create `backend/app/services/stylometry.py` with the following function signature:

  ```python
  import re
  import statistics
  from typing import Any

  import spacy
  import textstat

  _nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
  _CONTRACTION_RE = re.compile(r"\w+'\w+")
  _LIST_MARKER_RE = re.compile(r"^(\s*[-*]|\s*\d+\.)[\s]", re.MULTILINE)

  def compute_stylometric_fields(text: str) -> dict[str, Any]:
      ...
  ```

- [x] 2.2 Implement sentence_length_avg and sentence_rhythm:
  - Parse with `_nlp(text[:50_000])` (cap at 50k chars to match existing Gemini cap)
  - Collect per-sentence word count using `[len([t for t in s if not t.is_punct and not t.is_space]) for s in doc.sents]`
  - `sentence_length_avg = round(statistics.mean(lengths))` if lengths else 0
  - `sentence_rhythm = "uniform" if statistics.stdev(lengths) < 4 else "varied"` (guard for len < 2: default "varied")

- [x] 2.3 Implement paragraph_density:
  - Split text on `\n\n` to get paragraphs; filter empty strings
  - For each paragraph count sentences using `len(list(_nlp(para).sents))`
  - `avg = mean(sentences_per_para)`; "airy" if avg <= 2, "moderate" if 3-4, "dense" if >= 5

- [x] 2.4 Implement contraction_frequency:
  - Count tokens matching `_CONTRACTION_RE` in the doc
  - Rate = contractions / total non-space tokens; "never" if 0, "occasional" if < 0.05, "frequent" if >= 0.05

- [x] 2.5 Implement list_preference:
  - Count paragraphs (split on `\n\n`) that match `_LIST_MARKER_RE`
  - Pct = list_paragraphs / total_paragraphs; "rarely" if < 0.05, "sometimes" if 0.05-0.20, "often" if > 0.20

- [x] 2.6 Add low_confidence flag: if `word_count < 300` (use `textstat.lexicon_count(text, removepunct=True)`) add `result["low_confidence"] = True`

- [x] 2.7 Return dict with all 5 keys (plus optional low_confidence)

---

### Task 3 -- Wire into ingestion pipeline (AC 4, 5)

- [x] 3.1 In `backend/app/services/ingestion.py`, import `compute_stylometric_fields` from `services/stylometry`

- [x] 3.2 Locate where `combined_text` is assembled (after scrape + file upload merge). Add this block BEFORE the `extract_brand_voice` call:
  ```python
  computed = compute_stylometric_fields(combined_text)
  ```

- [x] 3.3 After `extract_brand_voice` returns `bvp_data`, merge:
  ```python
  bvp_data.update(computed)
  ```

- [x] 3.4 In the FR-11 refresh path (wherever the existing BVP is loaded and updated), apply the same pattern: run `compute_stylometric_fields` on the new text and `existing_bvp.update(computed)` before saving.

---

### Task 4 -- Write tests (AC 6)

- [x] 4.1 Create `backend/tests/test_stylometry.py`
- [x] 4.2 Write fixtures: normal_text (300+ words, varied lengths), short_text (< 300 words), contraction_free_text, heavy_list_text, uniform_text (all sentences ~10 words)
- [x] 4.3 Test all 6 cases listed in AC 6; no mocking needed (function is pure Python, no external calls)

---

## Dev Notes

### Files to create

| File | Action |
|---|---|
| `backend/app/services/stylometry.py` | CREATE |
| `backend/tests/test_stylometry.py` | CREATE |

### Files to modify

| File | Change |
|---|---|
| `backend/requirements.txt` | Add textstat and spacy |
| `backend/app/services/ingestion.py` | Call compute_stylometric_fields before Gemini, merge result |
| `deploy.sh` | Add spaCy model download note as comment only |

### No DB migration required

The BVP is stored as JSONB in `clients.brand_voice_profile`. Adding new keys to the dict requires no schema change.

### Performance note

`spacy.load` is called at module level (`_nlp = spacy.load(...)`) so the model loads once on worker startup, not per request. The `disable=["ner", "lemmatizer"]` flag keeps the model fast for sentence segmentation and tokenization only.

### spaCy model size

`en_core_web_sm` is ~12 MB. It must be downloaded in the deployment environment. The `deploy.sh` comment ensures the next deploy engineer knows to run it once. Do NOT add it to `requirements.txt` (it is installed via `python -m spacy download`, not pip directly).

### Existing ingestion.py reference

The `combined_text` variable and the `extract_brand_voice` call are currently in `backend/app/services/ingestion.py`. Locate the exact lines before making changes; the function structure may have evolved since Story 2.5.

### No frontend changes

This story is entirely backend. The BVP JSON stored in the DB now has 5 more keys; the frontend Story 16.3 handles displaying them.

### Computed fields are write-once from the server

The frontend PATCH body (Story 16.3) explicitly excludes computed fields. The server should also ignore `sentence_length_avg`, `sentence_rhythm`, `paragraph_density`, `contraction_frequency`, `list_preference` if present in a PATCH body (treat as read-only). Add a note to the client PATCH schema validation -- but do NOT block the request on their presence, just discard them silently.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None -- implementation was straightforward; no debug iterations required.

### Completion Notes List

- Created `backend/app/services/stylometry.py` with `compute_stylometric_fields` and `COMPUTED_FIELD_NAMES` constant.
- Module-level `spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])` loads once on worker startup.
- `paragraph_density` runs spaCy sentence segmentation on each paragraph; this is correct but runs the model twice (once on full text for sentence/contraction metrics, once per paragraph). Acceptable given the 50k char cap and the existing performance note in Dev Notes.
- FR-11 refresh uses the same `extract_voice_profile` code path (router nulls BVP then re-dispatches `ingest_worker`), so Task 3.4 is handled automatically by the Task 3.2/3.3 integration.
- Added computed-field stripping in `clients.py` PATCH handler: `brand_voice_profile` values keyed in `COMPUTED_FIELD_NAMES` are silently discarded before the DB write, per Dev Notes read-only constraint.
- 17 unit tests written covering all 6 AC 6 cases plus edge cases (empty string, single sentence).
- No new DB migrations required (JSONB field accommodates new keys).

### File List

- `backend/app/services/stylometry.py` (CREATED)
- `backend/tests/test_stylometry.py` (CREATED)
- `backend/requirements.txt` (MODIFIED — added textstat, spacy)
- `backend/app/services/ingestion.py` (MODIFIED — import + compute before Gemini call + merge)
- `backend/app/routers/clients.py` (MODIFIED — PATCH computed-field stripping)
- `deploy.sh` (MODIFIED — runbook comment for spaCy model download)

### Review Findings

- [x] [Review][Patch] spacy.load() at module level gives opaque traceback if model missing — wrap with OSError→RuntimeError [stylometry.py:14]
- [x] [Review][Patch] filtered_bvp empty dict wipes existing BVP in DB when client sends only computed fields [clients.py:216]
- [x] [Review][Patch] _CONTRACTION_RE.fullmatch never matches spaCy-split tokens (n't, 'm, 'll) — contraction_frequency always returns "never" [stylometry.py:75]
- [x] [Review][Patch] No positive contraction detection test — masks systematic bug above [test_stylometry.py]
- [x] [Review][Patch] compute_stylometric_fields can raise before Gemini retry loop, killing all 3 attempts — wrap in try/except in ingestion.py [ingestion.py:268]
- [x] [Review][Patch] Paragraphs split from full text, not text[:50_000] — paragraph_density/list_preference metrics inconsistent with other metrics [stylometry.py:59]
- [x] [Review][Patch] textstat.lexicon_count uses full text, not text[:50_000] — low_confidence flag inconsistent [stylometry.py:99]
- [x] [Review][Patch] Dead re.MULTILINE flag on _LIST_MARKER_RE — does nothing with .match(), misleading [stylometry.py:16]
- [x] [Review][Patch] COMPUTED_FIELD_NAMES unused import in ingestion.py [ingestion.py:23]
- [x] [Review][Defer] textstat/spacy not version-pinned in requirements.txt — deferred, project-wide policy concern
- [x] [Review][Defer] Per-paragraph _nlp() CPU cost — deferred, mitigated by text[:50_000] fix; background worker context acceptable
- [x] [Review][Defer] bvp.update(computed) could override future Gemini keys — deferred, theoretical; Gemini prompt controlled by us

## Change Log

- 2026-07-17: Story implemented. New `stylometry.py` service with 5-metric computation; integrated into `extract_voice_profile` before Gemini call; computed fields merged into BVP. PATCH endpoint silently strips computed-only keys. 17 unit tests added, all pass.
- 2026-07-17: Code review complete. 9 patches applied (spacy OSError wrap, empty BVP guard, contraction regex fixed to apostrophe-in-token, positive contraction test, stylometry try/except in ingestion, text[:50_000] for paragraphs, text[:50_000] for low_confidence, dead re.MULTILINE removed, unused import removed). Marked done.
