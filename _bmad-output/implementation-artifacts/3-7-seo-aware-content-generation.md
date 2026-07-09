---
baseline_commit: 350c4ae
---

# Story 3.7: SEO-Aware Content Generation

Status: done

## Story

As a PersonnaPress user,
I want the blog posts generated from my Brain Dump to be structured, direct, and SEO-ready — not generic AI filler — so that the content I publish can rank and drives real traffic rather than getting demoted by Google's Helpful Content algorithms.

## Context & Motivation

A production audit of generated blog posts identified 7 structural SEO flaws, all traceable to a single root cause: the `_BLOG_PROMPT` template in `backend/app/integrations/gemini.py` provides no constraints against fluffy intros, no mandatory structure, and no banned-phrase enforcement. The `check_fidelity()` call only checks voice tone/cadence — it never validates SEO quality.

This story fixes the generation pipeline with two phases:

**Phase 1 (Prompt-only, zero migration):** Rewrite `_BLOG_PROMPT` to enforce BLUF intro, mandatory H2/H3 hierarchy, FAQ schema section, banned-phrase blacklist, and TL;DR block. Extend `check_fidelity()` to also output SEO quality signals stored in the existing `voice_score` JSONB field.

**Phase 2 (Schema + UI):** Add optional `target_keyword` and `target_audience` nullable columns to the `campaigns` table. Flow them into the generation prompt so the AI knows what keyword to target and who it is writing for — the two inputs that alone fix Search Intent Conflation (flaw #1) and Keyword Optimization (flaw #5).

Both phases together address all 7 SEO flaws while staying within the existing service architecture, cost envelope, and MVP scope.

## Acceptance Criteria

### Phase 1: Prompt & Fidelity Upgrade

1. **Given** `generate_blog()` in `gemini.py` is called, **When** the blog prompt is sent to Gemini, **Then** the prompt MUST include ALL of these mandatory structural requirements:
   - First paragraph uses BLUF (Bottom Line Up Front): states the core takeaway immediately with a specific fact or number
   - A `<div class="tldr">` block with 2-3 bold sentences appears immediately after the H1, directly answering the reader's primary question
   - 3 to 4 H2 sections, each with at least one H3 subsection
   - An FAQ section at the end with exactly 3 Q&A pairs formatted as `<dt>` / `<dd>` inside a `<dl class="faq">`
   - A conclusion H2 section that leads with the actionable takeaway (not a restatement of the intro)
   - A `<!-- meta: ... -->` HTML comment immediately after the H1 containing the meta description (already present but must be retained)

2. **Given** the blog prompt is built in `generate_blog()`, **When** the BVP or the Brain Dump uses broad or unclear framing, **Then** the prompt includes a banned-phrase blacklist that Gemini MUST NOT start any paragraph or sentence with. The exact list to include in the prompt:
   ```
   BANNED OPENERS (never start a paragraph or sentence with these):
   - "In today's fast-paced world"
   - "In today's digital landscape"
   - "As we all know"
   - "It's no secret that"
   - "The [industry] landscape is evolving"
   - "Standing out requires more than"
   - "Now more than ever"
   ```
   Also ban these words anywhere in the output: `delve`, `moreover`, `testament`, `comprehensive`, `furthermore`, `tapestry`, `paradigm`, `bespoke`, `unlock`, `supercharge`, `navigate` (as a metaphor).

3. **Given** the blog prompt is sent, **When** the output HTML is returned by Gemini, **Then** `generate_blog()` runs a post-processing validation pass:
   - Verify an H1 is present; if absent, log a warning and return the raw HTML (do not fail)
   - Verify at least 2 H2 tags are present; if fewer, log a warning (do not fail — fidelity check will flag it)
   - Verify the TL;DR block (`<div class="tldr">`) is present; if absent, inject a placeholder: `<div class="tldr"><p><strong>TL;DR:</strong> [Summary pending review]</p></div>` directly after the H1

4. **Given** `check_fidelity()` is called after blog generation, **When** the fidelity prompt is sent to Gemini, **Then** the response JSON MUST include three new SEO quality fields in addition to the existing voice fields:
   ```json
   {
     "tone_score": 8,
     "cadence_score": 7,
     "jargon_violations": 0,
     "seo_bluf_present": true,
     "seo_h2_count": 3,
     "seo_faq_present": true,
     "seo_fluff_detected": false
   }
   ```
   - `seo_bluf_present`: true if the first paragraph states a specific fact, stat, or direct answer; false if it opens with a general statement
   - `seo_h2_count`: integer count of H2 tags in the blog HTML
   - `seo_faq_present`: true if a FAQ section (at minimum 3 Q&A pairs) is present
   - `seo_fluff_detected`: true if any banned opener phrase is found in the content

5. **Given** `check_fidelity()` returns the extended JSON, **When** the response is parsed, **Then** the existing validation MUST be extended to:
   - Accept and validate all 7 keys (3 existing + 4 new SEO fields)
   - Validate boolean types for the 3 boolean fields; raise `ValueError` on non-boolean
   - Validate integer type for `seo_h2_count`; raise `ValueError` on non-integer
   - Store the complete 7-key object in `campaign.voice_score` (the JSONB column already supports this — no migration needed)
   - The BVP-None bypass (`return {"tone_score": 10, ...}`) MUST also include the 4 new SEO keys with neutral values: `seo_bluf_present: True, seo_h2_count: 3, seo_faq_present: True, seo_fluff_detected: False`

6. **Given** `check_fidelity()` runs with the existing 256 thinking token budget, **When** the extended check runs, **Then** the thinking budget remains 256 tokens (no increase) — the 4 new SEO fields are deterministic checks the model can do cheaply; do NOT increase `_FIDELITY_THINKING_TOKENS`.

### Phase 2: Keyword + Audience Fields

7. **Given** the `campaigns` table in Supabase Postgres, **When** the Alembic migration for this story runs, **Then** two nullable `TEXT` columns are added:
   - `target_keyword TEXT NULL DEFAULT NULL`
   - `target_audience TEXT NULL DEFAULT NULL`
   No existing rows are affected. No backfill. Migration is safe to run on a live database.

8. **Given** the `Campaign` SQLModel in `backend/app/db/repositories/models.py`, **When** this story is implemented, **Then** the model includes:
   ```python
   target_keyword: Optional[str] = None
   target_audience: Optional[str] = None
   ```
   Both nullable, no default. These are plain `Text` columns (no JSONB, no Enum).

9. **Given** `backend/app/schemas/campaign.py` contains `CampaignCreate`, **When** a campaign is created via `POST /api/v1/campaigns`, **Then** `CampaignCreate` accepts two new optional fields:
   ```python
   target_keyword: Optional[str] = Field(default=None, max_length=200)
   target_audience: Optional[str] = Field(default=None, max_length=500)
   ```
   Both optional. If omitted or null, the generation falls back to the existing behavior (no keyword-specific targeting). The existing `campaigns.create_campaign()` repository function MUST be updated to accept and persist these two new fields.

10. **Given** `target_keyword` is provided and non-empty in the Campaign record, **When** `generate_blog()` builds the prompt via `_build_seo_section()`, **Then** the prompt includes:
    ```
    SEO TARGET:
    - Primary keyword: {target_keyword}
    - Include this exact phrase or a close variant in: the H1 title, the first 100 words, at least one H2 heading, and the conclusion paragraph.
    - Write to rank for this specific search query — assume the reader typed this exact phrase into Google.
    ```
    **Given** `target_keyword` is null or empty, **When** `_build_seo_section()` runs, **Then** the prompt includes a Search Intent Focus block instead:
    ```
    SEARCH INTENT FOCUS (no keyword provided):
    Extract the single most specific, actionable angle from the Brain Dump. Pick ONE target reader type — not "developers AND marketers", not "apps AND SaaS". Choose one. Write exclusively for that angle. State your choice in the H1 and commit to it through every section. If the brain dump is broad, pick the most specific, technical angle.
    ```
    This ensures Search Intent Conflation (Flaw #1 from the SEO audit) is prevented whether or not the user provides a keyword. The no-keyword path forces the model to self-select one focused angle rather than covering all angles from the brain dump simultaneously.

11. **Given** `target_audience` is provided and non-empty in the Campaign record, **When** `generate_blog()` builds the prompt, **Then** the prompt includes:
    ```
    TARGET AUDIENCE:
    - {target_audience}
    - Write exclusively for this audience. If they would not recognize a reference or tool, explain it briefly or omit it.
    ```
    If null or empty, this section is omitted.

12. **Given** the `/campaigns/new` page in the frontend, **When** the page renders, **Then** two new optional input fields appear below the Brain Dump textarea and above the submit button:
    - A text input labeled `"Target keyword (optional)"` with placeholder `"e.g. how to scale a subscription mobile app"` — max 200 chars, `font-mono text-sm`, bottom-border-only Paper Style input
    - A text input labeled `"Target audience (optional)"` with placeholder `"e.g. indie app developers, solo founders building iOS apps"` — max 500 chars, same style
    Both inputs are optional and do NOT affect the disabled state of the submit button. Both are cleared on successful submit.

13. **Given** the frontend form is submitted with keyword and/or audience filled in, **When** `campaignsApi.create()` is called, **Then** the API call includes `target_keyword` and `target_audience` as nullable string fields in the request body. The TypeScript type for `CampaignCreate` in `frontend/lib/api.ts` or `frontend/lib/types.ts` MUST be updated to include these optional fields.

### Phase 2b: BVP-Derived Audience (Auto-Populate from Scraping)

14. **Given** the `_BVP_PROMPT_TEMPLATE` in `gemini.py` that already runs during brand voice ingestion with 1024 thinking tokens, **When** `extract_brand_voice()` is called, **Then** the prompt instructs Gemini to also return a `target_audience` field in the JSON response:
    ```json
    {
      "tone": [...],
      "cadence": {...},
      "banned_jargon": [...],
      "target_audience": "one sentence describing who this brand writes for, based on the scraped content"
    }
    ```
    The field is a plain string, max ~200 chars. If the scraped content does not make the audience clear, Gemini returns `null` for this field. `extract_brand_voice()` validation MUST accept `target_audience` as optional (`str | None`) — its absence or null value MUST NOT raise a `ValueError`. Clients with existing BVP JSON that lack this key continue to work unchanged.

15. **Given** the `/campaigns/new` page loads or the active client changes in `useClientStore`, **When** `activeClient.brand_voice_profile?.target_audience` is a non-empty string, **Then** the `targetAudience` input is pre-populated with that value. If the user has already typed something in the field, their input is NOT overwritten (only pre-populate when the field is currently empty or when the active client switches). This is UI state only — no API call is made until the form is submitted.

### Regression Protection

16. **Given** all changes in this story, **When** `target_keyword` and `target_audience` are both null/omitted (legacy behavior), **Then** the complete generation pipeline behaves identically to before this story — same retry logic, same error handling, same job status transitions, same voice score structure (extended but backward compatible). No existing tests should break.

17. **Given** the extended `check_fidelity()` response schema, **When** the `VoiceFidelityBadge` component in `frontend/components/campaigns/VoiceFidelityBadge.tsx` renders the voice score, **Then** it MUST NOT crash if the new SEO keys are present in `voice_score`. If the component uses TypeScript types for `VoiceScore`, update the type to include the 4 new optional SEO fields as `optional` (not required) so existing campaigns without them still render correctly.

## Tasks / Subtasks

### Phase 1: Prompt + Fidelity Upgrade

- [x] Task 1: Rewrite `_BLOG_PROMPT` in `backend/app/integrations/gemini.py` (AC: #1, #2, #10, #11)
  - [x] 1.1 Replace the current `_BLOG_PROMPT` string with the new template (see Dev Notes section for full template)
  - [x] 1.2 Add `target_keyword` and `target_audience` parameters to `generate_blog()` signature (both `Optional[str] = None`); inject the SEO TARGET and TARGET AUDIENCE sections into the prompt only when non-empty
  - [x] 1.3 Add the banned-phrase blacklist to the prompt's REQUIREMENTS section (AC #2)

- [x] Task 2: Post-processing validation in `generate_blog()` (AC: #3)
  - [x] 2.1 After `_md_to_html(_strip_fences(response.text.strip()))`, run the 3-check validation pass
  - [x] 2.2 TL;DR block injection: if `<div class="tldr">` not in result, find the closing `</h1>` tag and inject `<div class="tldr"><p><strong>TL;DR:</strong> [Summary pending review]</p></div>` immediately after it
  - [x] 2.3 Log warnings for missing H1 or fewer than 2 H2s (use `logger.warning`, do not raise)

- [x] Task 3: Extend `_FIDELITY_PROMPT` and `check_fidelity()` (AC: #4, #5, #6)
  - [x] 3.1 Update `_FIDELITY_PROMPT` to request the 4 new SEO fields in the JSON response (see Dev Notes for full template)
  - [x] 3.2 Extend `check_fidelity()` validation to accept and type-check all 7 keys
  - [x] 3.3 Update the BVP-None bypass return value to include the 4 new SEO fields with neutral values
  - [x] 3.4 Confirm thinking tokens remain at 256 (no change to `_FIDELITY_THINKING_TOKENS`)

### Phase 2: Schema + Migration + UI

- [x] Task 4: Alembic migration for new columns (AC: #7)
  - [x] 4.1 Generate migration: `alembic revision --autogenerate -m "add_target_keyword_audience_to_campaigns"` from `backend/`
  - [x] 4.2 Verify the migration adds `target_keyword TEXT NULL` and `target_audience TEXT NULL` to the `campaigns` table with no backfill and no NOT NULL constraints
  - [x] 4.3 Run `alembic upgrade head` locally and verify it applies cleanly

- [x] Task 5: Update `Campaign` model and `campaigns` repository (AC: #8, #9)
  - [x] 5.1 Add `target_keyword: Optional[str] = None` and `target_audience: Optional[str] = None` to `Campaign` in `backend/app/db/repositories/models.py`
  - [x] 5.2 Update `create_campaign()` in `backend/app/db/repositories/campaigns.py` to accept and persist `target_keyword` and `target_audience`

- [x] Task 6: Update API schema (AC: #9)
  - [x] 6.1 Add `target_keyword: Optional[str] = Field(default=None, max_length=200)` and `target_audience: Optional[str] = Field(default=None, max_length=500)` to `CampaignCreate` in `backend/app/schemas/campaign.py`

- [x] Task 7: Wire keyword + audience through the generation pipeline (AC: #10, #11)
  - [x] 7.1 In `services/generation.py`, after loading `campaign` from DB, extract `campaign.target_keyword` and `campaign.target_audience`
  - [x] 7.2 Pass both to `gemini.generate_blog()` call via `_gemini_with_retry`

- [x] Task 8: Extend `extract_brand_voice()` to extract `target_audience` from scraped content (AC: #14)
  - [x] 8.1 Update `_BVP_PROMPT_TEMPLATE` in `gemini.py` to include `"target_audience": "<string or null>"` in the output JSON schema and a one-line instruction: `"target_audience: A single sentence describing who this brand writes for, inferred from the content. Return null if unclear."`
  - [x] 8.2 Update `extract_brand_voice()` validation: after the 3 required field checks (`tone`, `cadence`, `banned_jargon`), add a soft check for `target_audience` — if present, validate it is `str | None`; if absent from the response entirely, set `data["target_audience"] = None` and continue (no error); the 3 existing required-field `ValueError` checks are unchanged
  - [x] 8.3 Verify `services/ingestion.py` stores the full BVP JSON (including the new `target_audience` field) in `client.brand_voice_profile` — no change needed since the entire JSON is stored as-is; confirm this is the case by reading `services/ingestion.py`

- [x] Task 9: Frontend — Brain Dump UI additions (AC: #12, #13, #15)
  - [x] 9.1 Add `targetKeyword` and `targetAudience` state to `NewCampaignPage` (both `string`, init `""`)
  - [x] 9.2 Add a `useEffect` that watches `activeClientId` (from `useClientStore`): when the active client changes, if `targetAudience` is currently `""`, set it to `activeClient.brand_voice_profile?.target_audience ?? ""`; if the user has already typed something, do not overwrite
  - [x] 9.3 Render two optional Paper Style bottom-border-only text inputs below the Brain Dump textarea and above the submit button (use same `border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink` style as the textarea; `bg-transparent`, `font-mono text-sm`)
  - [x] 9.4 Add labels using the same `font-mono text-xs text-graphite uppercase tracking-widest` pattern used for other labels on this page
  - [x] 9.5 Pass `target_keyword` and `target_audience` to `campaignsApi.create()` — send `null` when the string is empty (`trimmed length === 0`)
  - [x] 9.6 Update TypeScript `CampaignCreate` type to include `target_keyword?: string | null` and `target_audience?: string | null`
  - [x] 9.7 Clear both fields on successful submit (reset state to `""`)

- [x] Task 10: Update `VoiceFidelityBadge` TypeScript type (AC: #17)
  - [x] 10.1 In `frontend/lib/types.ts`, update `VoiceScore` to add the 4 new optional SEO fields:
    ```typescript
    export interface VoiceScore {
      tone_score: number;
      cadence_score: number;
      jargon_violations: number;
      seo_bluf_present?: boolean;
      seo_h2_count?: number;
      seo_faq_present?: boolean;
      seo_fluff_detected?: boolean;
    }
    ```
  - [x] 10.2 Verify `VoiceFidelityBadge.tsx` renders without crash when the 4 new fields are present or absent; no UI changes required to the badge itself (display of SEO signals is deferred)

### Tests

- [x] Task 11: Backend tests (AC: #1, #2, #3, #4, #5, #14, #16)
  - [x] 11.1 Update `backend/tests/test_gemini_generation.py` to verify the new `_BLOG_PROMPT` includes the TL;DR requirement, banned-phrase list, FAQ requirement, and BLUF instruction
  - [x] 11.2 Update `generate_blog()` unit tests to verify: TL;DR injection fires when missing from Gemini output; warning is logged when H2 count < 2; warnings are logged but not raised as errors
  - [x] 11.3 Update `check_fidelity()` unit tests to verify: the 7-key response is accepted and validated; boolean type check on SEO fields raises `ValueError` on wrong type; BVP-None bypass includes the 4 new SEO fields
  - [x] 11.4 Update `extract_brand_voice()` unit tests to verify: `target_audience` present in response is accepted; `target_audience` missing from response is silently set to `None`; the 3 existing required-field `ValueError` checks still pass unchanged
  - [x] 11.5 Update generation pipeline integration tests to verify `target_keyword` and `target_audience` flow from campaign to `generate_blog()` call
  - [x] 11.6 Add a regression test: when `target_keyword=None` and `target_audience=None`, the blog prompt does NOT include the "SEO TARGET:" or "TARGET AUDIENCE:" sections

## Dev Notes

### Root Cause Analysis

The problem is in `gemini.py:_BLOG_PROMPT`. The current prompt:
```
REQUIREMENTS:
- Target 800-1,500 words
- Use H2 and H3 for structure; only one H1 (the title)
- Match the tone: {tone_list}
- Match the cadence: avg sentence length {avg_sentence_length} words
- Never use these jargon terms: {banned_jargon_list}
- Output ONLY valid HTML tags — NEVER use markdown syntax...
```

Problems:
- "Use H2 and H3 for structure" is too vague — Gemini generates them but in ad-hoc order
- No BLUF requirement — Gemini defaults to context-setting intros ("The landscape is evolving...")
- No FAQ section requirement
- No TL;DR block
- No banned opener phrases
- No keyword or audience context — Gemini reads a broad brain dump and covers all angles simultaneously (Search Intent Conflation)
- No "pick one angle" instruction — even with no keyword, Gemini must be told to commit to a single audience and intent

### New `_BLOG_PROMPT` Template

Replace the entire `_BLOG_PROMPT` constant with:

```python
_BLOG_PROMPT = """You are a direct, expert blog writer. Write a blog post that sounds like a human expert, not an AI assistant.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP (author's raw idea — extract the core argument from this):
{brain_dump}

{seo_target_section}
{audience_section}

MANDATORY STRUCTURE (HTML only, no markdown — follow this EXACTLY):
<h1>[Keyword-first title, specific and direct]</h1>
<!-- meta: [One sentence meta description, max 150 chars, ends with action phrase] -->
<div class="tldr"><p><strong>TL;DR:</strong> [2-3 bold sentences that directly answer the post's core question. Specific. No filler.]</p></div>
<p>[BLUF intro paragraph: Start with a specific fact, number, or bold claim. Never start with "In today's..." or similar openers. State the core takeaway in the first sentence.]</p>
<h2>[First main topic — actionable heading]</h2>
<h3>[Sub-topic]</h3>
<p>...</p>
<h2>[Second main topic]</h2>
<h3>[Sub-topic]</h3>
<p>...</p>
<h2>[Third main topic]</h2>
<h3>[Sub-topic]</h3>
<p>...</p>
<h2>Frequently Asked Questions</h2>
<dl class="faq">
  <dt>[Question 1 related to the post topic]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
  <dt>[Question 2]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
  <dt>[Question 3]</dt>
  <dd><strong>[Direct one-sentence answer.]</strong> [1-2 sentence explanation.]</dd>
</dl>
<h2>Key Takeaways</h2>
<p>[Conclusion paragraph that leads with the single most important action the reader should take. Do not restate the intro.]</p>

REQUIREMENTS:
- Target 900-1,500 words
- Use H2 and H3 for structure; only one H1 (the title)
- Match the tone: {tone_list}
- Match the cadence: avg sentence length {avg_sentence_length} words
- Never use these jargon terms: {banned_jargon_list}
- Output ONLY valid HTML tags — NEVER use markdown syntax like **bold**, *italic*, ##, ###
- Bold text must use <strong>, italics must use <em>

BANNED OPENERS — never start any paragraph or sentence with these phrases:
- "In today's fast-paced world"
- "In today's digital landscape"
- "As we all know"
- "It's no secret that"
- "The [anything] landscape is evolving"
- "Standing out requires more than"
- "Now more than ever"

BANNED WORDS — do not use anywhere: delve, moreover, testament, comprehensive, furthermore, tapestry, paradigm, bespoke, unlock, supercharge, navigate (as metaphor)

Every sentence must earn its place. If a sentence does not give the reader new information or a specific action, cut it.
"""
```

The `seo_target_section` and `audience_section` are generated by `_build_seo_section(target_keyword, target_audience)`:

```python
def _build_seo_section(target_keyword: str | None, target_audience: str | None) -> tuple[str, str]:
    if target_keyword:
        seo_section = f"""SEO TARGET:
- Primary keyword: {target_keyword}
- Include this exact phrase or a close variant in: the H1 title, the first 100 words, at least one H2 heading, and the conclusion paragraph.
- Write to rank for this specific search query — assume the reader typed this exact phrase into Google."""
    else:
        # No keyword provided: force intent focus to prevent Search Intent Conflation.
        # Without this, Gemini reads a broad brain dump and tries to cover every angle simultaneously.
        seo_section = """SEARCH INTENT FOCUS (no keyword provided):
Extract the single most specific, actionable angle from the Brain Dump. Pick ONE target reader type — not "developers AND marketers", not "apps AND SaaS". Choose one. Write exclusively for that angle. State your choice in the H1 and commit to it through every section. If the brain dump is broad, pick the most specific, technical angle."""

    audience_section = ""
    if target_audience:
        audience_section = f"""TARGET AUDIENCE:
- {target_audience}
- Write exclusively for this audience. Do not broaden the scope. If a reference or tool would be unfamiliar to this audience, explain it in one clause or omit it."""

    return seo_section, audience_section
```

### New `_FIDELITY_PROMPT` Template

```python
_FIDELITY_PROMPT = """Evaluate the following blog post against the Brand Voice Profile AND for SEO quality.

BRAND VOICE PROFILE:
{bvp_json}

BLOG HTML:
{blog_html}

Return ONLY a valid JSON object (no markdown):
{{
  "tone_score": <integer 0-10>,
  "cadence_score": <integer 0-10>,
  "jargon_violations": <integer count of banned BVP terms found>,
  "seo_bluf_present": <boolean: true if the first <p> tag starts with a specific fact, stat, or direct claim — NOT a general statement like "The landscape is..."; false otherwise>,
  "seo_h2_count": <integer: count of <h2> tags in the blog HTML>,
  "seo_faq_present": <boolean: true if a FAQ section with at least 3 Q&A pairs (as <dl> or similar) is present>,
  "seo_fluff_detected": <boolean: true if any banned opener phrase like "In today's fast-paced world", "As we all know", "It's no secret that" appears anywhere in the content>
}}
"""
```

BVP-None bypass must return:
```python
return {
    "tone_score": 10,
    "cadence_score": 10,
    "jargon_violations": 0,
    "seo_bluf_present": True,
    "seo_h2_count": 3,
    "seo_faq_present": True,
    "seo_fluff_detected": False,
}
```

### `check_fidelity()` Extended Validation

Add after the existing 3-key validation:

```python
seo_bool_keys = ("seo_bluf_present", "seo_faq_present", "seo_fluff_detected")
for key in seo_bool_keys:
    if key not in data:
        raise ValueError(f"check_fidelity: missing key '{key}' in Gemini response")
    if not isinstance(data[key], bool):
        raise ValueError(
            f"check_fidelity: '{key}' must be bool, got {type(data[key]).__name__}"
        )
if "seo_h2_count" not in data:
    raise ValueError("check_fidelity: missing key 'seo_h2_count' in Gemini response")
if not isinstance(data["seo_h2_count"], int):
    raise ValueError(
        f"check_fidelity: 'seo_h2_count' must be int, got {type(data['seo_h2_count']).__name__}"
    )
```

### `generate_blog()` Signature Change

```python
async def generate_blog(
    brain_dump: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = 512,
    target_keyword: str | None = None,
    target_audience: str | None = None,
) -> str:
```

The two new params are keyword-only with defaults of `None` so all existing call sites continue to work (AC #14 regression protection).

### `services/generation.py` Change

In `run_generation_pipeline()`, the Step 2 call becomes:

```python
blog_html: str = await _gemini_with_retry(
    gemini.generate_blog,
    campaign.brain_dump,
    brand_voice_profile,
    _BLOG_THINKING_TOKENS,
    campaign.target_keyword,
    campaign.target_audience,
)
```

No other changes to the pipeline are required.

### Alembic Migration Pattern

Follow the pattern established by previous migrations in `backend/alembic/versions/`. The migration should be:

```python
def upgrade() -> None:
    op.add_column("campaigns", sa.Column("target_keyword", sa.Text(), nullable=True))
    op.add_column("campaigns", sa.Column("target_audience", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("campaigns", "target_audience")
    op.drop_column("campaigns", "target_keyword")
```

Run migration: from `backend/` directory, `alembic upgrade head`.

### Frontend Input Styling

The two new optional fields must match the Paper Style input convention established in UX-DR4:

```tsx
<div className="space-y-1 mb-2">
  <label className="font-mono text-xs text-graphite uppercase tracking-widest">
    Target keyword <span className="normal-case">(optional)</span>
  </label>
  <input
    type="text"
    value={targetKeyword}
    onChange={(e) => setTargetKeyword(e.target.value)}
    maxLength={200}
    placeholder="e.g. how to scale a subscription mobile app"
    className="w-full bg-transparent font-mono text-sm text-ink border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink py-2 focus:outline-none transition-all placeholder:text-graphite/40"
  />
</div>
```

Same pattern for Target Audience with `maxLength={500}`.

### Cost Impact (NFR-9)

- Blog generation: thinking tokens unchanged at 512
- Fidelity check: thinking tokens unchanged at 256
- Social generation: unchanged at 0
- No new Gemini calls added
- Total `_ESTIMATED_TOTAL_TOKENS` in `services/generation.py` remains 768

The extended prompt is longer in tokens but Gemini input tokens are cheap; the thinking budget is what drives cost, and both stay fixed.

### VoiceFidelityBadge — No Display Change Required

The `VoiceFidelityBadge.tsx` component currently reads `voice_score.tone_score`, `cadence_score`, and `jargon_violations`. The 4 new SEO fields are stored in the JSONB but NOT displayed in the badge in this story. Just update the TypeScript type to include them as optional so the component does not crash on TypeScript strict mode checks. A future story can surface the SEO signals in the badge UI.

### BVP Prompt Extension for `target_audience`

Add one field to `_BVP_PROMPT_TEMPLATE`:

```python
_BVP_PROMPT_TEMPLATE = """Analyze the following text and extract a Brand Voice Profile.

Return ONLY a valid JSON object with this exact schema:
{{
  "tone": ["list", "of", "style", "descriptors"],
  "cadence": {{
    "avg_sentence_length": <integer>,
    "variation_pattern": "<string>",
    "paragraph_structure": "<string>"
  }},
  "banned_jargon": ["words", "or", "phrases", "to", "avoid"],
  "target_audience": "<one sentence describing who this brand writes for, inferred from the content, or null if unclear>"
}}

No markdown code blocks, no explanation. Raw JSON only.

TEXT TO ANALYZE:
{text}"""
```

And extend `extract_brand_voice()` after the 3 existing validation checks:
```python
# Soft check: target_audience is optional
if "target_audience" not in data:
    data["target_audience"] = None
elif data["target_audience"] is not None and not isinstance(data["target_audience"], str):
    data["target_audience"] = None  # coerce invalid type to None silently
```

### File Structure

**Modified files:**
```
backend/app/integrations/gemini.py          ← Rewrite _BLOG_PROMPT, extend _FIDELITY_PROMPT, update _BVP_PROMPT_TEMPLATE; update generate_blog(), check_fidelity(), extract_brand_voice()
backend/app/services/generation.py          ← Pass target_keyword + target_audience to generate_blog()
backend/app/db/repositories/models.py       ← Add target_keyword, target_audience to Campaign
backend/app/db/repositories/campaigns.py    ← Update create_campaign() to accept + persist new fields
backend/app/schemas/campaign.py             ← Add optional fields to CampaignCreate
frontend/app/(app)/campaigns/new/page.tsx   ← Add keyword + audience input fields, BVP pre-population useEffect
frontend/lib/types.ts                       ← Extend VoiceScore interface
backend/tests/test_gemini_generation.py     ← Update tests for new prompt, fidelity, and BVP extraction
backend/tests/test_generation_service.py    ← Update tests for new pipeline args
```

**New files:**
```
backend/alembic/versions/{hash}_add_target_keyword_audience_to_campaigns.py
```

### Service Boundary Reminder (AR-19)

The call chain must remain:
```
router (campaigns.py)
  └── BackgroundTask → workers/generate.py
        └── services/generation.py      ← ONLY location that calls gemini.py
              └── integrations/gemini.py
```

`target_keyword` and `target_audience` are loaded from the `Campaign` ORM object inside `services/generation.py` and passed to `gemini.generate_blog()`. They are NOT passed through from the router layer to the worker to the service — the service reads them directly from the DB record it already loads (Step 1 of the pipeline).

### What Was Explicitly Excluded from This Story

The following brainstormed solutions were assessed and deferred to keep this story MVP-scoped:

- **Author profile + story library (Solution D):** Requires a new DB table, new UI flows, and library management UX. Too complex for MVP. Deferred.
- **Web research integration (Solution F):** Requires web search API calls per generation. Significant cost and latency impact. Deferred.
- **Auto-linking engine (Solution E):** Requires a URL database for tool names and internal link detection. Deferred.
- **SEO gate blocking publish (Solution J):** Adds friction before publishing. Deferred. A future story can add the SEO score display in the Approval Gate using the `seo_*` fields now stored in `voice_score`.
- **Multimedia placeholders (Solution H):** Useful but secondary. The new prompt's structure (H2 per section) naturally provides visual break points where image insertion is obvious. Deferred.
- **CLAUDE Code skill (Solution L):** A separate developer tool concern, not an app feature. Deferred.

## References

- `backend/app/integrations/gemini.py` — current `_BLOG_PROMPT`, `_FIDELITY_PROMPT`, `_BVP_PROMPT_TEMPLATE`, `generate_blog()`, `check_fidelity()`, `extract_brand_voice()` implementations (read before modifying)
- `backend/app/services/ingestion.py` — confirm how BVP JSON is stored to `client.brand_voice_profile` (read before Task 8.3)
- `backend/app/services/generation.py` — `run_generation_pipeline()` Step 2 and Step 3 (read before modifying)
- `backend/app/db/repositories/models.py` — `Campaign` SQLModel class (read before adding columns)
- `backend/app/schemas/campaign.py` — `CampaignCreate` schema (read before modifying)
- `frontend/app/(app)/campaigns/new/page.tsx` — Brain Dump page (read before modifying)
- `frontend/lib/types.ts` — `VoiceScore` TypeScript interface (read before modifying)
- Story 3.3 dev notes — `_gemini_with_retry` pattern, service boundary enforcement, retry logic
- AR-19: Service boundaries — generation.py is ONLY caller of gemini.py
- NFR-9: Cost controls — thinking token budgets must not increase
- UX-DR4: Input components — bottom-border-only Paper Style pattern for new form fields
- Previous audit findings: 7 SEO flaws from production blog post review (context in this story's motivation section)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- `_BLOG_PROMPT` fully rewritten with mandatory BLUF structure, TL;DR block, FAQ section, H2/H3 hierarchy, banned-opener list, and banned-word list.
- `_build_seo_section()` helper generates SEO TARGET block (keyword path) or SEARCH INTENT FOCUS block (no-keyword path) and optional TARGET AUDIENCE section.
- Post-processing in `generate_blog()`: warns on missing H1/H2, injects TL;DR placeholder after `</h1>` if absent.
- `_FIDELITY_PROMPT` extended to 7-key JSON; `check_fidelity()` validates 3 bool fields and 1 int field with `ValueError` on wrong type. BVP-None bypass returns all 7 keys.
- Alembic migration `e4582603a04a` adds `target_keyword TEXT NULL` and `target_audience TEXT NULL` to `campaigns` table; applied cleanly.
- `Campaign` SQLModel, `create_campaign()` repo, `CampaignCreate` schema, campaigns router, and `run_generation_pipeline()` all updated to carry the two new fields end-to-end.
- `extract_brand_voice()` extended: `_BVP_PROMPT_TEMPLATE` now requests `target_audience`; soft-check coerces absent/invalid values to `None`.
- `/campaigns/new` page: added `targetKeyword`/`targetAudience` state, Paper Style inputs, BVP auto-populate `useEffect`, null-when-empty submit logic, and clear-on-success.
- `VoiceScore` TypeScript interface extended with 4 optional SEO fields; `CampaignCreate` type added to types.ts and imported in api.ts.
- Backend test suite: 31 gemini unit tests (all new/rewritten) + 8 generation service tests all pass. Full suite: 33 failures, all pre-existing before this story.
- Root-cause fixed in `conftest.py`: added google.genai stubs + eager pre-import of `app.integrations.gemini` and `app.services.generation` to prevent `tests/routers/test_campaigns.py`'s `sys.modules.setdefault` stubs from polluting later tests.

### File List

- `backend/app/integrations/gemini.py`
- `backend/app/services/generation.py`
- `backend/app/db/repositories/models.py`
- `backend/app/db/repositories/campaigns.py`
- `backend/app/schemas/campaign.py`
- `backend/app/routers/campaigns.py`
- `backend/alembic/versions/e4582603a04a_add_target_keyword_audience_to_campaigns.py`
- `backend/tests/test_gemini_generation.py`
- `backend/tests/test_generation_service.py`
- `backend/tests/conftest.py`
- `frontend/app/(app)/campaigns/new/page.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Review Findings

- [x] [Review][Patch] useEffect two bugs: (a) async race — `clients` loads after `activeClientId` fires the effect with `activeClient=null`, BVP never pre-fills on initial load; (b) client switch doesn't update audience when `targetAudience !== ""`, violating AC15 "or when the active client switches" clause [`frontend/app/(app)/campaigns/new/page.tsx:28-38`]
- [x] [Review][Patch] TL;DR not injected when H1 is also absent — `if h1_close != -1` guard silently skips injection; untested path [`backend/app/integrations/gemini.py:282-287`]
- [x] [Review][Patch] Case-sensitive H1 detection mismatch — `result.lower()` for H1 presence check vs `result.find("</h1>")` (case-sensitive) for injection position; Gemini output with `</H1>` triggers wrong TL;DR position [`backend/app/integrations/gemini.py:274,280`]
- [x] [Review][Patch] `seo_h2_count` bool validation gap — `isinstance(True, int)` is `True` in Python; JSON `true` from Gemini passes the int check and stores `True` as H2 count [`backend/app/integrations/gemini.py:346-349`]
- [x] [Review][Patch] Regression test asserts vacuously true condition — `test_generate_blog_no_keyword_no_audience_no_seo_or_audience_sections` checks `"SEO TARGET:" not in prompt` but SEARCH INTENT FOCUS is always injected when keyword=None; test should assert SEARCH INTENT FOCUS presence [`backend/tests/test_gemini_generation.py:214`]
- [x] [Review][Patch] Whitespace-only strings pass Pydantic validation — `"   "` passes `Optional[str]` + `max_length`; add strip validator for defense-in-depth against non-frontend callers [`backend/app/schemas/campaign.py:30-31`]
- [x] [Review][Defer] `tone_score`/`cadence_score`/`jargon_violations` accept floats — only `seo_h2_count` enforces strict `int` — deferred, pre-existing behavior not introduced by this story
- [x] [Review][Defer] `_FIDELITY_PROMPT` asks Gemini to count `<h2>` tags — LLMs are unreliable HTML parsers — deferred, pre-existing design decision; deterministic counting is a broader refactor
