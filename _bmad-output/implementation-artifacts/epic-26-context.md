# Epic 26 Context: Voice Fidelity v2 and First-Run Value

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

This epic closes the gap between the product promise ("content that sounds like you, not AI") and what the pipeline actually delivers. Code analysis identified four concrete failure modes: (1) character limits defined in four places with inconsistent values and no enforcement at publish time; (2) the BVP captures ~25 fields but injects only half, and micro-style signals like casing habits and comma density are never measured; (3) raw writing samples are discarded after voice extraction, so the model receives abstract style instructions rather than real exemplars; (4) the voice fidelity score is informational only and never triggers a repair; and (5) onboarding has 10 screen transitions and 5 async waits with no step persistence, so a dropout restarts cold. The epic fixes all five.

## Stories

- Story 26.1: Character Limit Single Source of Truth and Enforcement
- Story 26.2: Micro-Style Stylometry and Full BVP Injection
- Story 26.3: Few-Shot Voice Exemplars from Stored Samples
- Story 26.4: Fidelity Repair Loop and Per-Mode Voice Differentiation
- Story 26.5: Onboarding Friction Reduction and Early Voice Proof

## Requirements & Constraints

**Character limits (26.1):** Canonical hard limits are X 280 (weighted, URLs = 23 chars), LinkedIn 3000, Instagram 2200, Facebook 63206, Threads 500. Target ranges for prompts are stricter. A single shared module per layer enforces these: `backend/app/services/platform_limits.py` and `frontend/lib/platformLimits.ts`. Blind string-slice truncation (`[:280]`, `[:2200]`) is forbidden; the only allowed fallback is sentence-boundary truncation after a failed one-shot repair call. Over-limit posts must be blocked at Approval (inline error naming platform and overage) and rejected at publish time before any API call, with `error_details="over_limit"` and a user-visible retry message.

**Stylometry and BVP injection (26.2):** Six new micro-style fields are added to `compute_stylometric_fields()`: `casing_style`, `comma_density`, `exclamation_frequency`, `ellipsis_usage`, `parenthetical_usage`, `sentence_length_stdev`. Seven previously extracted-but-uninjected qualitative fields (`formality_scale`, `humor_style`, `vocabulary_complexity`, `example_style`, `target_audience`, `sentence_rhythm`, `paragraph_density`) must each produce a concrete instruction line in the voice section. Absent fields (legacy BVPs) inject nothing and never raise. `signature_phrases`, `voice_anchor_sentences`, and `anti_pattern_example` must reach social prompts the same way they already reach blog prompts.

**Voice samples (26.3):** Up to 12 representative excerpts (200-600 chars, sentence-boundary trimmed, deduplicated) are stored in a new `voice_samples JSONB` column on `clients`. Ingestion currently discards raw text after extraction — it must store excerpts instead. Questionnaire and transcript sources are preserved across rescans; only `source="scrape"` samples are replaced on rescan.

**Fidelity repair loop (26.4):** Repair triggers when `tone_score < 7 OR cadence_score < 6 OR jargon_violations > 0`. Exactly one repair call per campaign — no recursion. The better-scoring version (initial vs. repaired) is kept. `voice_score` gains `initial`, `final`, and `repaired` fields; `repaired: true` displays a "voice-tuned" badge. Each surface (blog, LinkedIn, X, Instagram/Facebook, Threads) must receive a verifiably different voice section in the built prompt.

**Onboarding (26.5):** A new `onboarding_step INT` nullable column (Alembic migration) enables resume. Step order changes: brain dump moves to Step 3, platform connection becomes Step 4. The OAuth return handler must be updated for the new numbering. Brain dump textarea draft persists to localStorage (cleared on campaign creation). The voice recording option from `VoiceBrainDump.tsx` must be available in the onboarding brain dump step.

**Copy and style constraints (project-wide):** No em-dash, no double-dash in any generated copy or prompts. No emojis anywhere.

## Technical Decisions

**New files and modules:**
- `backend/app/services/platform_limits.py` — single source of truth for all hard limits and prompt target ranges; the X weighted-count function lives here.
- `frontend/lib/platformLimits.ts` — mirrors backend constants; a backend test asserts parity between the two (or via a shared JSON fixture).
- Stylometry additions go in the existing `backend/app/services/stylometry.py`; new fields follow the existing never-raise, 50K-cap pattern.
- `_build_voice_injection()` and `_build_social_universal_rules()` in `generation_prompts.py` are the injection points for all BVP fields.

**Schema migrations (all via `alembic revision --autogenerate` from `backend/`):**
- `clients.voice_samples JSONB` nullable (26.3).
- `users.onboarding_step INT` nullable, default null (26.5).
- `campaigns.voice_score` shape extended to `{tone, cadence, jargon_violations, initial, final, repaired}` — additive, backward-compatible (26.4).

**Repair loop placement:** The repair call runs inside `services/generation.py`, after the fidelity score is received, before the result is stored. It adds no user-visible wait state beyond the existing generation job.

**LLM provider parity:** Any prompt-building change (new injection lines, per-surface voice sections, repair prompt, few-shot samples block) must be reflected identically in both `integrations/gemini.py` and `integrations/anthropic_client.py`. The `_llm` indirection in `generation.py` routes at runtime based on `LLM_PROVIDER`.

**Frontend counter fix (26.1):** `SocialPostEditors.tsx` counter maxima (currently 280/1500/2200/1000/500) are replaced with values from `platformLimits.ts`. The X counter must use the weighted-count function (URLs = 23 chars).

**RSC pattern:** All new or modified server components must follow the project pattern — no API calls in server components; those live in client components via TanStack Query.

**Alembic:** Never hand-write revision IDs. Always use `alembic revision --autogenerate` from `backend/`.

## UX & Interaction Patterns

**Approval Gate over-limit block (26.1):** When any post exceeds its platform hard limit, the Approve button is disabled with an inline message naming the platform(s) and character overage. The corresponding counter enters danger state. This is a hard block, not a warning.

**Voice-proof element in onboarding (26.5):** After voice extraction completes in Step 2 (`InlineProfileReview`), a "voice proof" shows one short paragraph generated live in the user's extracted voice, captioned "This is how PersonnaPress will sound as you." Generation failure hides the element silently — it never blocks the step.

**Scrape-failure explanation (26.5):** When website scraping fails or finds no content, the questionnaire path displays a one-line explanation keyed to the specific `error_details` reason (`no_content` vs. other), rather than the questionnaire appearing unexplained.

**Voice samples tab (26.3):** The voice tab in `ClientDetailTabs` gains a stored-samples section where the user can view and individually delete samples. A rescan button replaces scrape samples only.

**Onboarding step reorder (26.5):** Brain dump is now Step 3, platform connection is Step 4 (framed as "publish what you just made"). Skipping platform connection still completes onboarding.

## Cross-Story Dependencies

- **26.2 before 26.4:** The per-surface voice section differentiation in 26.4 builds on the injection infrastructure expanded in 26.2. Both touch `generation_prompts.py`; implement 26.2 first.
- **26.3 before 26.4:** The repair call in 26.4 passes the voice section and few-shot samples block built by 26.3's injection logic. 26.3's `voice_samples` migration must land before 26.4 runs in any environment.
- **26.1 is independent:** The platform limits module and enforcement changes do not depend on any other 26.x story and can ship separately.
- **26.5 is independent:** The onboarding changes share no schema or service surface with 26.1-26.4 except that the voice proof element (26.5 AC-2) calls the same voice generation path that 26.2 improves; 26.5 works correctly without 26.2 but benefits from it.
