---
baseline_commit: 9f94cee
---

# Story 3.19: Brain Dump Personal Voice Preservation

Status: done

## Story

As a PersonnaPress user who writes personal passages, opinions, and final notes in my brain dump,
I want those authored sentences to appear in the generated blog nearly word for word,
so that my content sounds genuinely like me -- not like a polished AI rewrite of my raw ideas.

## Context & Motivation

Users write two very different kinds of content in the brain dump: raw fragments (bullet points,
data, shorthand) that the AI should expand, and authored prose (coherent first-person sentences)
that the AI should preserve. The current `_BLOG_PROMPT` treats both identically -- it instructs
the LLM to "build the blog around the core argument," which primes it to rewrite everything,
including the user's most authentic sentences.

The result: a user writes `"personalization at scale is a myth. I spent 3 weeks building a
system -- it barely moved the needle"` and receives back `"personalized outreach often
underperforms generic messaging at scale, as testing has shown"`. The factual claim survives;
the voice, the bluntness, and the Information Gain delta are destroyed.

This is compounded by two additional issues:
- The Brand Voice Profile is applied to the entire output including the user's own sentences,
  which "professionalises" them against the user's intent.
- There is no mechanism for the user to give the AI direct instructions inside the brain dump
  (e.g. `"Note: keep this sentence verbatim"`).

**Research context (July 2026):** Google's March 2026 core update made Information Gain its
primary ranking signal -- it mathematically scores whether content contains insight that
"cannot be found expressed in identical or near-identical form across thousands of other pages."
Rewriting an authored passage destroys this signal. Passage-level indexing means a distinctive
first-person sentence can independently rank; the sanitised version cannot. The same update
amplified the first E in E-E-A-T (Experience) above all other signals on contested queries.
Pages whose AI expands around genuinely experienced content maintained or improved rankings;
pages that replaced experience with AI generalities were penalised.

**Scope:** All changes live in `generation_prompts.py`, `gemini.py`, `anthropic_client.py`,
`generation.py`, `test_generation_prompts.py`, and a small frontend update to `campaigns/new/page.tsx`.
No DB migration. No new library. No schema change.

---

## Acceptance Criteria

### AC 1 -- Brain dump classification framework in `_BLOG_PROMPT`

1. **Given** the `_BLOG_PROMPT` in `generation_prompts.py`, **When** the prompt is read,
   **Then** the brain dump section instructs the LLM to silently classify every part of the
   brain dump into exactly three types before writing:

   - **AUTHORED PASSAGE** -- 2 or more coherent first-person sentences that read as finished
     prose (not a list, not a fragment, not a label:value pair). Defined as Information Gain
     signals: content that exists nowhere else on the web because only this author lived it.
   - **FRAGMENT/NOTE** -- bullet points, single-line fragments, data lists, label:value pairs,
     shorthand. Raw material for the LLM to expand.
   - **DIRECTIVE** -- any line beginning with `"Note:"`, `"Final note:"`, `"PS:"`, or
     `"Important:"`. Author instructions to the AI; never output as content.

### AC 2 -- Authored passage treatment rules in `_BLOG_PROMPT`

2. **Given** the classification framework, **When** the prompt's TREATMENT RULES section is
   read, **Then** it states:

   - AUTHORED PASSAGES are reproduced with grammar corrections only. Do not rewrite structure,
     improve vocabulary, or apply the Brand Voice Profile to these passages. The author's own
     words ARE the voice here.
   - If an authored passage contains an em-dash, rewrite that sentence naturally without one
     (per the BANNED CHARACTER rule) but change nothing else.
   - Preserve expressions of uncertainty, self-deprecation, conversational asides, and
     "off-script" moments in authored passages exactly as written. These are authenticity
     signals, not errors to fix.
   - AUTHORED PASSAGES must open the section they belong to: placed as the first content after
     the H2 or H3 heading, not buried mid-section. The authored passage is the Information Gain
     delta; surface it first so Google's passage indexing captures it.
   - For sections generated from FRAGMENT/NOTE content: match the directness, sentence length,
     and register of the AUTHORED PASSAGES in this brain dump. Do not default to a generic
     professional blog voice -- the authored passages are the register benchmark.
   - FRAGMENT/NOTE content: expand into full prose using the Brand Voice Profile and SEO structure.
   - DIRECTIVES: follow them silently. Never quote or reference them in the output.

3. **Given** the RETAIN instruction (first-person experiences, specific numbers, dates, named
   tools, unique outcomes), **When** it is updated, **Then** it now reads: "RETAIN all
   first-person experiences, specific numbers, dates, named tools, and unique outcomes
   **regardless of classification**." The URL embedding rule (anchor tags for http:// https://)
   is unchanged.

### AC 3 -- Passive voice ban in `_BLOG_PROMPT` REQUIREMENTS

4. **Given** the REQUIREMENTS section of `_BLOG_PROMPT`, **When** the passive voice rule is
   added, **Then** it states: "Never use passive voice when active voice is possible. Write
   'I tested this' not 'this was tested', 'the data showed' not 'it was shown by the data'.
   Passive voice is the single most detectable AI writing pattern."

### AC 4 -- Opinion stance instruction in `_BLOG_PROMPT` REQUIREMENTS

5. **Given** the REQUIREMENTS section, **When** the opinion rule is added, **Then** it states:
   "In 1-2 sections, take a clear direct opinion: 'I think X is wrong', 'most advice on this
   is backwards', 'in my view Y is overrated'. State it as the author's personal view, not
   universal fact. Opinion statements are the strongest authenticity signal in written content."

### AC 5 -- Social prompt authored passage handling

6. **Given** `_SOCIAL_PROMPT` in `generation_prompts.py`, **When** the brain dump section is
   read, **Then** after `{brain_dump}` the prompt instructs: if the brain dump contains
   AUTHORED PASSAGES (2+ coherent first-person sentences in finished prose), use their exact
   wording as the LinkedIn post opening hook -- preserve their register and do not
   professionalize. Distil the sharpest claim or opinion from authored passages as the X post
   hook. DIRECTIVES (`"Note:"`, `"Final note:"`, `"PS:"`) are author instructions -- follow
   them silently, never include them in the posts. Preserve personality signals (humor,
   self-deprecation, bluntness) from authored passages exactly.

7. **Given** `_SOCIAL_STANDALONE_PROMPT`, **When** the brain dump section is read, **Then**
   the same authored passage instruction from AC 5.6 is present (LinkedIn hook from authored
   passage, X hook from sharpest claim, DIRECTIVE handling, personality preservation).

### AC 6 -- Fidelity check: `authored_passages_preserved` metric

8. **Given** `_FIDELITY_PROMPT` in `generation_prompts.py`, **When** the JSON schema in the
   prompt is read, **Then** it includes a new field:
   ```
   "authored_passages_preserved": <boolean: true if at least one passage of 2+ coherent
   first-person sentences from the brain dump sample appears in the blog HTML with only minor
   grammar changes; false if all brain dump content has been fully rewritten>
   ```

9. **Given** `_FIDELITY_PROMPT`, **When** the prompt template is read, **Then** it includes a
   `{brain_dump_sample}` placeholder with label: "BRAIN DUMP SAMPLE (first 1500 characters of
   the original brain dump -- used only to verify authored passage preservation)".

10. **Given** `check_fidelity` in `gemini.py` and `anthropic_client.py`, **When** the function
    signature is updated, **Then** it accepts a new parameter `brain_dump: str = ""` (keyword,
    with empty-string default for backwards compatibility) and passes
    `brain_dump_sample=brain_dump[:1500]` to `_FIDELITY_PROMPT.format(...)`.

11. **Given** `run_generation_pipeline` in `generation.py`, **When** it calls `check_fidelity`,
    **Then** it passes `campaign.brain_dump` as the `brain_dump` argument.

12. **Given** `check_fidelity` when `brand_voice_profile is None` (no BVP fallback path),
    **When** the default dict is returned, **Then** `authored_passages_preserved: True` is
    included in the default dict in both `gemini.py` and `anthropic_client.py`.

### AC 7 -- Frontend: prose quality nudge on campaigns/new

13. **Given** the brain dump textarea on `/campaigns/new`, **When** `charCount >= 150` and no
    first-person prose passage is detected (fewer than 2 sentences matching `\bI\s+[a-z]` in
    the brain dump text), **Then** a quality nudge appears below the character counter:
    - Lucide `Feather` icon (12px, `aria-hidden="true"`)
    - Text: `"Tip: write 2-3 sentences in your own voice -- they will be kept as written."`
    - Style: `text-xs font-mono text-[#555555]`
    - Wrapped in the existing `aria-live="polite"` container

14. **Given** the prose nudge is shown, **When** the user writes 2+ first-person sentences
    (prose passage detected), **Then** the nudge disappears immediately (no delay).

15. **Given** the existing lightbulb tip (shown when `charCount > 0 && charCount < 150`),
    **When** the prose nudge is implemented, **Then** the two nudges are mutually exclusive:
    - `charCount < 150`: lightbulb tip only
    - `charCount >= 150` AND no prose: Feather prose nudge only
    - `charCount >= 150` AND prose detected: no nudge (success state)

16. **Given** the prose detection logic, **When** it runs, **Then** it uses a `useMemo`
    (dependent on `brainDump`) with this exact detection:
    ```ts
    const sentences = brainDump.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 10);
    const firstPersonSentences = sentences.filter(s => /\bI\s+[a-z]/i.test(s));
    return firstPersonSentences.length >= 2;
    ```

### AC 8 -- Frontend: tips panel fifth tip

17. **Given** the collapsible tips panel on `/campaigns/new`, **When** it is open, **Then** a
    new first tip is shown at the top of the list:
    - Text: `"Write the sentences you care most about in full -- they will appear in your article nearly word for word"`
    - Style: `text-[#111111]` (slightly stronger than the existing `text-[#555555]` tips,
      to signal this is the most important behavioral tip)
    - No code example needed (it is a behavioral statement, not a formatting example)
    - Existing 4 tips are unchanged in content and order below it

### AC 9 -- No regressions

18. **Given** all existing brain dump features (character counter, lightbulb tip, link detection
    indicator, Cmd+Enter submit, tips panel, URL anchor embedding, BVP voice injection,
    `_build_voice_injection`, `_build_standalone_voice_injection`, `_build_seo_section`),
    **When** this story is implemented, **Then** all existing behaviour is unaffected.

19. **Given** the `_FIDELITY_PROMPT` format call in `gemini.py`, **When** `brain_dump` is
    empty string (e.g. older callers, tests that do not pass brain_dump), **Then** no
    `KeyError` or formatting error occurs -- `brain_dump_sample` receives `""` and the
    fidelity check still returns a valid JSON object.

---

## Dev Notes

### Files to modify

| File | Change |
|---|---|
| `backend/app/integrations/generation_prompts.py` | `_BLOG_PROMPT` brain dump section rewrite; passive voice + opinion rules in REQUIREMENTS; `_SOCIAL_PROMPT` + `_SOCIAL_STANDALONE_PROMPT` brain dump addition; `_FIDELITY_PROMPT` `brain_dump_sample` placeholder + `authored_passages_preserved` field |
| `backend/app/integrations/gemini.py` | `check_fidelity` signature: add `brain_dump: str = ""`; pass `brain_dump_sample=brain_dump[:1500]` to `_FIDELITY_PROMPT.format()`; add `authored_passages_preserved: True` to BVP-None default dict |
| `backend/app/integrations/anthropic_client.py` | Same `check_fidelity` changes as `gemini.py` |
| `backend/app/services/generation.py` | Pass `brain_dump=campaign.brain_dump` to `check_fidelity` call |
| `frontend/app/(app)/campaigns/new/page.tsx` | Add `hasProsePassage` useMemo; update hint display logic; add `Feather` import; add 5th tip to tips panel |
| `backend/tests/test_generation_prompts.py` | 5 new tests (see below) |

No new files. No Alembic migration. No new npm/pip packages.

---

### `_BLOG_PROMPT` -- exact replacement for the brain dump section

Replace the entire `BRAIN DUMP (...):\n{brain_dump}` block (lines 128-129 in current file)
with the following. Keep everything before it and after it unchanged:

```
BRAIN DUMP:
{brain_dump}

Before writing, silently classify every part of the brain dump above into one of three types:

AUTHORED PASSAGE -- 2 or more coherent first-person sentences that read as finished prose (not
a list, not a fragment, not a label:value pair). These are Information Gain signals: content
that exists nowhere else on the web because only this author lived it. Google's ranking
algorithm scores this uniqueness directly.

FRAGMENT/NOTE -- bullet points, single-line fragments, data lists, label:value pairs (e.g.
"Tools: Apollo, Clay"), shorthand notes. Raw material for you to expand.

DIRECTIVE -- any line beginning with "Note:", "Final note:", "PS:", or "Important:". These are
author instructions to you. Follow them silently. Do not output them as content.

TREATMENT RULES:
- AUTHORED PASSAGES: reproduce in the blog with grammar corrections only. Do not rewrite
  structure, improve vocabulary, or apply the Brand Voice Profile to these passages -- the
  author's own words ARE the voice here. If a passage contains an em-dash, rewrite that
  sentence naturally without one but change nothing else. Preserve expressions of uncertainty,
  self-deprecation, conversational asides, and off-script moments exactly as written -- these
  are authenticity signals, not errors.
- AUTHORED PASSAGES must open the section they belong to: place them as the first content after
  the H2 or H3 heading. The authored passage is the Information Gain delta; surface it first so
  Google's passage indexing can capture it independently.
- For sections you generate from FRAGMENT/NOTE content: match the directness, sentence length,
  and register of the AUTHORED PASSAGES in this brain dump. Do not default to a generic
  professional blog voice -- the authored passages are your register benchmark.
- FRAGMENT/NOTE content: expand into full prose using the Brand Voice Profile and SEO structure.
- DIRECTIVES: follow them silently. Never quote or reference them in the output.

RETAIN all first-person experiences, specific numbers, dates, named tools, and unique outcomes
regardless of classification. These are E-E-A-T signals; do not generalize or anonymize them.
If the brain dump contains any URLs (http:// or https://), embed each as an HTML anchor link
<a href="[URL]" rel="noopener noreferrer" target="_blank">[natural anchor text describing what
the URL points to]</a> at the point in the article where it is most relevant; preserve each URL
exactly as provided. If the brain dump contains no URLs, do not add any anchor tags or links.
```

---

### `_BLOG_PROMPT` -- two new REQUIREMENTS rules

Add these two lines after the existing "Contractions" rule in the REQUIREMENTS section:

```
- Never use passive voice when active voice is possible. Write "I tested this" not "this was
  tested", "the data showed" not "it was shown by the data". Passive voice is the single most
  detectable AI writing pattern.
- In 1-2 sections, take a clear direct opinion: "I think X is wrong", "most advice on this is
  backwards", "in my view Y is overrated". State it as the author's personal view, not
  universal fact. Opinion statements are the strongest authenticity signal in written content.
```

---

### `_SOCIAL_PROMPT` -- addition after `{brain_dump}`

In `_SOCIAL_PROMPT`, replace:
```
BRAIN DUMP:
{brain_dump}

BLOG TITLE:
```

With:
```
BRAIN DUMP:
{brain_dump}

Reading the brain dump: if it contains AUTHORED PASSAGES (2+ coherent first-person sentences in
finished prose), use their exact wording as the LinkedIn post opening hook -- preserve the
register and do not professionalize. Distil the sharpest claim or opinion from any authored
passage as the X post hook. DIRECTIVES (lines beginning "Note:", "Final note:", "PS:") are
author instructions -- follow them silently, never include them in the posts. Preserve
personality signals (humor, self-deprecation, bluntness) from authored passages exactly.

BLOG TITLE:
```

---

### `_SOCIAL_STANDALONE_PROMPT` -- same addition after `{brain_dump}`

In `_SOCIAL_STANDALONE_PROMPT`, replace:
```
BRAIN DUMP:
{brain_dump}

Return ONLY a valid JSON object
```

With:
```
BRAIN DUMP:
{brain_dump}

Reading the brain dump: if it contains AUTHORED PASSAGES (2+ coherent first-person sentences in
finished prose), use their exact wording as the LinkedIn post opening hook -- preserve the
register and do not professionalize. Distil the sharpest claim or opinion from any authored
passage as the X post hook. DIRECTIVES (lines beginning "Note:", "Final note:", "PS:") are
author instructions -- follow them silently, never include them in the posts. Preserve
personality signals (humor, self-deprecation, bluntness) from authored passages exactly.

Return ONLY a valid JSON object
```

---

### `_FIDELITY_PROMPT` -- full updated version

Replace `_FIDELITY_PROMPT` with:

```python
_FIDELITY_PROMPT = """Evaluate the following blog post against the Brand Voice Profile AND for SEO quality.

BRAND VOICE PROFILE:
{bvp_json}

BRAIN DUMP SAMPLE (first 1500 characters of the original brain dump -- used only to verify authored passage preservation):
{brain_dump_sample}

BLOG HTML:
{blog_html}

Return ONLY a valid JSON object (no markdown):
{{
  "tone_score": <integer 0-10>,
  "cadence_score": <integer 0-10>,
  "jargon_violations": <integer count of banned BVP terms found>,
  "seo_bluf_present": <boolean: true if the first <p> tag starts with a specific fact, stat, or direct claim, NOT a general statement like "The landscape is..."; false otherwise>,
  "seo_h2_count": <integer: count of <h2> tags in the blog HTML>,
  "seo_faq_present": <boolean: true if a FAQ section with at least 3 Q&A pairs (as <dl> or similar) is present>,
  "seo_fluff_detected": <boolean: true if any banned opener phrase like "In today's fast-paced world", "As we all know", "It's no secret that" appears anywhere in the content>,
  "authored_passages_preserved": <boolean: true if at least one passage of 2+ coherent first-person sentences from the brain dump sample appears in the blog HTML with only minor grammar changes; false if all brain dump content has been fully rewritten>,
  "tags": [<list of 3-5 concise lowercase SEO tags relevant to this specific post, e.g. ["brand voice", "content marketing", "ai tools"]>]
}}
{expanded_scoring_section}"""
```

---

### `gemini.py` -- `check_fidelity` changes

1. Add `brain_dump: str = ""` parameter:
```python
async def check_fidelity(
    blog_html: str,
    brand_voice_profile: dict | None,
    thinking_tokens: int = _FIDELITY_THINKING_TOKENS,
    brain_dump: str = "",
) -> dict:
```

2. Update BVP-None default dict to include new field:
```python
if brand_voice_profile is None:
    return {
        "tone_score": 10,
        "cadence_score": 10,
        "jargon_violations": 0,
        "seo_bluf_present": True,
        "seo_h2_count": 3,
        "seo_faq_present": True,
        "seo_fluff_detected": False,
        "authored_passages_preserved": True,
        "tags": [],
    }
```

3. Pass `brain_dump_sample` to format call:
```python
prompt = _FIDELITY_PROMPT.format(
    bvp_json=json.dumps(brand_voice_profile),
    blog_html=blog_html,
    brain_dump_sample=brain_dump[:1500],
    expanded_scoring_section=expanded_scoring_section,
)
```

Apply the same three changes to `anthropic_client.py` -- same function, same pattern.

---

### `generation.py` -- pass brain_dump to check_fidelity

```python
voice_score: dict = await _llm_with_retry(
    _llm.check_fidelity,
    blog_html,
    brand_voice_profile,
    _FIDELITY_THINKING_TOKENS,
    campaign.brain_dump,          # new: for authored_passages_preserved metric
)
```

---

### `frontend/app/(app)/campaigns/new/page.tsx` -- full diff

**1. Add `Feather` to Lucide import:**
```ts
import { ArrowLeft, ChevronDown, ChevronUp, Feather, Lightbulb, Link as LinkIcon, Loader2 } from "lucide-react";
```

**2. Add `hasProsePassage` useMemo (place after existing `linkCount` useMemo):**
```ts
const hasProsePassage = useMemo(() => {
  if (!brainDump || brainDump.length < 30) return false;
  const sentences = brainDump.split(/[.!?]+/).map((s) => s.trim()).filter((s) => s.length > 10);
  const firstPersonSentences = sentences.filter((s) => /\bI\s+[a-z]/i.test(s));
  return firstPersonSentences.length >= 2;
}, [brainDump]);
```

**3. Replace the two existing hint `aria-live` divs with the updated version:**

Replace:
```tsx
<div aria-live="polite" aria-atomic="true">
  {charCount > 0 && charCount < 150 && (
    <p className="flex items-center gap-1 text-xs text-[#555555] mt-1">
      <Lightbulb size={12} aria-hidden="true" />
      Tip: include a specific number, personal outcome, or named tool for best results.
    </p>
  )}
</div>
```

With:
```tsx
<div aria-live="polite" aria-atomic="true">
  {charCount > 0 && charCount < 150 && (
    <p className="flex items-center gap-1 text-xs font-mono text-[#555555] mt-1">
      <Lightbulb size={12} aria-hidden="true" />
      Tip: include a specific number, personal outcome, or named tool for best results.
    </p>
  )}
  {charCount >= 150 && !hasProsePassage && (
    <p className="flex items-center gap-1 text-xs font-mono text-[#555555] mt-1">
      <Feather size={12} aria-hidden="true" />
      Tip: write 2-3 sentences in your own voice -- they will be kept as written.
    </p>
  )}
</div>
```

Note: the existing lightbulb tip was missing `font-mono` -- add it in the same pass (non-visual
change, matches the rest of the UI).

**4. Add 5th tip as the first item in the tips `<ul>`:**

Replace:
```tsx
<ul role="list" className="mt-2 border border-[#E5E5E5] bg-[#F9F9F6] p-3 rounded-none list-none space-y-2 text-sm text-[#555555]">
  <li>Start with a specific number...
```

With:
```tsx
<ul role="list" className="mt-2 border border-[#E5E5E5] bg-[#F9F9F6] p-3 rounded-none list-none space-y-2 text-sm text-[#555555]">
  <li className="text-[#111111]">
    Write the sentences you care most about in full -- they will appear in your article nearly word for word
  </li>
  <li>Start with a specific number...
```

---

### Tests to add in `test_generation_prompts.py`

Add a new class `TestPromptStructure` with 5 tests. Import `_BLOG_PROMPT`, `_FIDELITY_PROMPT`,
`_SOCIAL_PROMPT`, `_SOCIAL_STANDALONE_PROMPT` from `generation_prompts`.

```python
from app.integrations.generation_prompts import (
    _BLOG_PROMPT,
    _FIDELITY_PROMPT,
    _SOCIAL_PROMPT,
    _SOCIAL_STANDALONE_PROMPT,
    _build_standalone_voice_injection,
    _build_voice_injection,
)

class TestPromptStructure:
    def test_blog_prompt_contains_authored_passage_classification(self):
        assert "AUTHORED PASSAGE" in _BLOG_PROMPT
        assert "FRAGMENT/NOTE" in _BLOG_PROMPT
        assert "DIRECTIVE" in _BLOG_PROMPT

    def test_blog_prompt_directive_markers_listed(self):
        # Note: / Final note: / PS: must all be named as directive triggers
        assert '"Note:"' in _BLOG_PROMPT or "Note:" in _BLOG_PROMPT
        assert "Final note:" in _BLOG_PROMPT
        assert "PS:" in _BLOG_PROMPT

    def test_blog_prompt_passive_voice_rule_present(self):
        assert "passive voice" in _BLOG_PROMPT.lower()

    def test_fidelity_prompt_contains_authored_passages_preserved_field(self):
        assert "authored_passages_preserved" in _FIDELITY_PROMPT
        assert "brain_dump_sample" in _FIDELITY_PROMPT

    def test_social_prompts_contain_authored_passage_instruction(self):
        assert "AUTHORED PASSAGE" in _SOCIAL_PROMPT or "authored passage" in _SOCIAL_PROMPT.lower()
        assert "AUTHORED PASSAGE" in _SOCIAL_STANDALONE_PROMPT or "authored passage" in _SOCIAL_STANDALONE_PROMPT.lower()
```

---

### UX Design (web-uiux-architect spec)

**Prose nudge visual spec:**
- Sits in the same `aria-live="polite"` container as the lightbulb tip
- Mutually exclusive with lightbulb tip (never both visible at once)
- `Feather` icon: `size={12}`, `aria-hidden="true"`, no colour override (inherits `text-[#555555]`)
- Text: `text-xs font-mono text-[#555555]` -- identical weight/size to lightbulb tip
- No border, no background, no padding beyond `gap-1` -- same visual weight as existing tip
- No animation (instant show/hide on state change -- CSS transitions on a `<p>` tag in an
  aria-live region can cause screen reader confusion)
- `mt-1` top margin (same as lightbulb tip)

**Fifth tips panel item visual spec:**
- List item uses `text-[#111111]` (ink) rather than the panel's default `text-[#555555]` (graphite)
- No icon, no `<code>` block -- it is a behavioral statement, not a formatting example
- No separator between it and the next item -- same `space-y-2` spacing as the other items
- Placed FIRST in the list: users scan top-to-bottom; the preservation guarantee is the most
  important behavioral signal and should be seen before the formatting tips

**Detection threshold rationale:**
- `brainDump.length < 30` guard prevents running the regex on trivially short input
- `sentence.length > 10` filter excludes sentence fragments from the split (e.g. trailing spaces
  after a period)
- `/\bI\s+[a-z]/i` matches "I [lowercase verb]" -- catches "I found", "I tested", "I spent"
  while avoiding "I" as part of a proper noun or acronym at the start of a sentence boundary
- Threshold of 2 first-person sentences mirrors the AUTHORED PASSAGE definition in the prompt

---

## Out of Scope

- `authored_passages_preserved` surfaced in the Approval Gate UI (voice score display) -- the
  metric is internal quality data for this story; surfacing it is a separate story
- Backend Python detection of authored passages (all classification is prompt-level only)
- Onboarding Step 3 brain dump tips panel (excluded -- one-time flow, lower priority)
- Regeneration stability guarantee (re-running generation always re-reads the brain dump;
  authored passages are preserved by the prompt, not by caching)
- Updating existing campaigns (prompt changes apply to new generation jobs only)
- Dark mode variants for the prose nudge (the page has no dark mode)

---

## Dev Agent Record

### Completion Notes

Implemented all 9 ACs across 6 files with no new dependencies, no DB migration, and no schema changes.

- AC 1-4 (`_BLOG_PROMPT`): Replaced the BRAIN DUMP inline label with a full 3-type classification framework (AUTHORED PASSAGE / FRAGMENT/NOTE / DIRECTIVE) plus TREATMENT RULES block. Added passive voice ban and opinion stance rules in REQUIREMENTS. RETAIN instruction now explicitly says "regardless of classification."
- AC 5 (`_SOCIAL_PROMPT`): Added authored passage reading instruction between `{brain_dump}` and `BLOG TITLE:`.
- AC 5 (`_SOCIAL_STANDALONE_PROMPT`): Added same authored passage instruction between `{brain_dump}` and `Return ONLY`.
- AC 6 (`_FIDELITY_PROMPT`): Added `{brain_dump_sample}` placeholder and `authored_passages_preserved` field to JSON schema.
- AC 6 (`gemini.py` + `anthropic_client.py`): Added `brain_dump: str = ""` parameter to `check_fidelity`; added `authored_passages_preserved: True` to BVP-None default dict; passed `brain_dump_sample=brain_dump[:1500]` to format call.
- AC 6 (`generation.py`): Passed `campaign.brain_dump` as 4th positional arg to `_llm.check_fidelity`.
- AC 7-8 (`campaigns/new/page.tsx`): Added `Feather` import; added `hasProsePassage` useMemo; updated aria-live div to be mutually exclusive (lightbulb < 150, Feather >= 150 + no prose, nothing when prose detected); added `font-mono` to lightbulb tip; added 5th tip as first list item in `text-[#111111]`.
- AC 9: All existing tests pass; 5 new `TestPromptStructure` tests added and passing. 49 generation tests pass. Pre-existing failures (spacy missing, unrelated routers) are unchanged.

---

## File List

- `backend/app/integrations/generation_prompts.py`
- `backend/app/integrations/gemini.py`
- `backend/app/integrations/anthropic_client.py`
- `backend/app/services/generation.py`
- `frontend/app/(app)/campaigns/new/page.tsx`
- `backend/tests/test_generation_prompts.py`

---

## Change Log

- 2026-07-30: Implemented Story 3.19 -- brain dump classification framework, authored passage treatment rules, passive voice ban, opinion stance rule, social prompt authored passage instructions, fidelity prompt brain_dump_sample + authored_passages_preserved field, check_fidelity signature update in both LLM providers, generation.py pipeline update, frontend prose nudge + 5th tips panel item. 5 new tests added.
