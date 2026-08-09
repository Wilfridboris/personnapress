---
depends_on: 3-22-strip-blog-compliance-report-trailer
---

# Story 3.23: Blog Target Length Selector

Status: ready-for-dev

## Story

As a PersonnaPress user creating a blog campaign,
I want to choose a target word count tier before generating,
so that the output matches the depth and format I need for each piece of content.

## Context & Motivation

The blog generation prompt (`_BLOG_PROMPT` in `generation_prompts.py`) hardcodes
`- Target 900-1,500 words` in its REQUIREMENTS block. Users writing short news
updates need 300-500 words; users targeting competitive SEO topics need
1,500-2,500 words. Neither fits today's fixed range.

This story adds a three-tier length selector to the Brain Dump form and threads
the chosen tier through to the Gemini/Anthropic prompt. Quick Read (300-500 words)
additionally suppresses the TL;DR and FAQ sections -- both are disproportionately
large relative to the body at that length and degrade output quality.

Standard (600-1,000 words) is the default and preserves all current behavior for
existing users.

---

## Files Touched

| File | Change |
|---|---|
| `backend/app/db/repositories/models.py` | ADD column `target_word_count` to `Campaign` |
| `backend/alembic/versions/<new>.py` | ADD migration |
| `backend/app/schemas/campaign.py` | ADD field to `CampaignCreate` + `CampaignResponse` |
| `backend/app/integrations/generation_prompts.py` | Parameterise word count + add Quick Read override block |
| `backend/app/integrations/gemini.py` | ADD `target_word_count` param to `generate_blog` |
| `backend/app/integrations/anthropic_client.py` | ADD `target_word_count` param to `generate_blog` |
| `backend/app/services/generation.py` | Pass `campaign.target_word_count` to `generate_blog` |
| `frontend/components/campaigns/LengthSelector.tsx` | NEW component |
| `frontend/app/(app)/campaigns/new/page.tsx` | Wire `LengthSelector`, autosave, API call |
| `frontend/lib/api.ts` | ADD `target_word_count` to campaign create payload type |

---

## Acceptance Criteria

### AC 1 -- DB column on `Campaign`

**Given** `backend/app/db/repositories/models.py` `class Campaign`,
**When** the story is implemented,
**Then** a new column exists:

```python
target_word_count: Optional[str] = Field(
    default=None,
    sa_column=Column(Text, nullable=True),
)
```

Placed after `skip_image` (line ~188). No enum constraint -- the valid values
("300-500", "600-1000", "1500-2500") are enforced by the Pydantic schema, not
the DB. `null` in DB is treated as "600-1000" (Standard) at generation time.

---

### AC 2 -- Alembic migration

**Given** the project uses Alembic with timestamp-prefixed filenames,
**When** the developer runs `cd backend && alembic revision --autogenerate -m "add_target_word_count_to_campaigns"`,
**Then** the generated migration contains:

```python
op.add_column(
    "campaigns",
    sa.Column("target_word_count", sa.Text(), nullable=True),
)
```

And `downgrade` reverses it with `op.drop_column("campaigns", "target_word_count")`.

**Critical:** Never hand-write the revision ID. Use the Alembic CLI so the
timestamp prefix and unique hex ID are auto-generated (see `project-context.md`
-- a hand-written duplicate revision ID once blocked all deployments).

---

### AC 3 -- Schema: `CampaignCreate` and `CampaignResponse`

**Given** `backend/app/schemas/campaign.py`,
**When** the story is implemented,
**Then**:

`CampaignCreate` gains:
```python
target_word_count: Optional[Literal["300-500", "600-1000", "1500-2500"]] = None
```
Added after `skip_image`.

`CampaignResponse` gains:
```python
target_word_count: Optional[str] = None
```
Added after `skip_image`.

No validator needed -- `Pydantic` `Literal` rejects invalid values automatically.
`None` is valid (treated as Standard at generation time).

---

### AC 4 -- `_BLOG_PROMPT`: parameterise word count

**Given** `backend/app/integrations/generation_prompts.py` line 194:
```
- Target 900-1,500 words
```
**When** the story is implemented,
**Then** that line is replaced with:
```
- Target {word_count_range}
```

And a new `{length_override_section}` placeholder is added immediately after the
closing REQUIREMENTS block (after the BANNED WORDS block, before the final
"Output ONLY the HTML" line):

```
{length_override_section}
```

This placeholder receives content only for Quick Read (see AC 5). For Standard
and In-Depth it receives an empty string.

---

### AC 5 -- `_BLOG_PROMPT`: Quick Read override block

**Given** the `length_override_section` placeholder added in AC 4,
**When** `target_word_count == "300-500"`,
**Then** the placeholder is filled with:

```
QUICK READ MODE (300-500 words):
- Strict word limit: 300-500 words total including all headings and HTML.
- OMIT the <div class="tldr"> block entirely. Do not output it.
- OMIT the <h2>Frequently Asked Questions</h2> and <dl class="faq"> block entirely.
- Write 1-2 H2 body sections only (not 3-4).
- The BLUF intro paragraph and conclusion are still required.
- Every sentence must earn its place. Cut anything that does not give the reader
  a new fact or a specific action.
```

For Standard and In-Depth, `length_override_section` is an empty string `""`.

---

### AC 6 -- `generate_blog` in both integrations accepts `target_word_count`

**Given** `backend/app/integrations/gemini.py` and
`backend/app/integrations/anthropic_client.py`,
**When** the story is implemented,
**Then** both `generate_blog` functions gain a new keyword argument:
```python
target_word_count: str | None = None,
```
Added after `secondary_keywords`.

Inside the function body, before the `_BLOG_PROMPT.format(...)` call, add:

```python
_WORD_COUNT_MAP = {
    "300-500": "300-500 words",
    "600-1000": "600-1,000 words",
    "1500-2500": "1,500-2,500 words",
}
word_count_range = _WORD_COUNT_MAP.get(target_word_count or "", "900-1,500 words")

if target_word_count == "300-500":
    length_override_section = (
        "QUICK READ MODE (300-500 words):\n"
        "- Strict word limit: 300-500 words total including all headings and HTML.\n"
        "- OMIT the <div class=\"tldr\"> block entirely. Do not output it.\n"
        "- OMIT the <h2>Frequently Asked Questions</h2> and <dl class=\"faq\"> block entirely.\n"
        "- Write 1-2 H2 body sections only (not 3-4).\n"
        "- The BLUF intro paragraph and conclusion are still required.\n"
        "- Every sentence must earn its place. Cut anything that does not give the reader\n"
        "  a new fact or a specific action."
    )
else:
    length_override_section = ""
```

Then add both to the `.format(...)` call:
```python
prompt = _BLOG_PROMPT.format(
    ...existing args...,
    word_count_range=word_count_range,
    length_override_section=length_override_section,
)
```

`_WORD_COUNT_MAP` is a local constant defined inside the function, not at module
level, to avoid polluting the module namespace.

---

### AC 7 -- `generation.py` passes `target_word_count`

**Given** `backend/app/services/generation.py` Step 2 (Blog generation),
**When** the story is implemented,
**Then** the `_llm_with_retry` call for `generate_blog` gains one more keyword arg:

```python
blog_html: str = await _llm_with_retry(
    _llm.generate_blog,
    campaign.brain_dump,
    brand_voice_profile,
    _BLOG_THINKING_TOKENS,
    campaign.target_keyword,
    campaign.target_audience,
    campaign.secondary_keywords,
    target_word_count=campaign.target_word_count,   # <-- new
)
```

No other changes to `generation.py`.

---

### AC 8 -- `LengthSelector` component

**Given** `frontend/components/campaigns/LengthSelector.tsx` does not exist,
**When** the story is implemented,
**Then** it is created with the following exact implementation:

```tsx
"use client";

import { cn } from "@/lib/utils";

export type TargetLength = "300-500" | "600-1000" | "1500-2500";

interface LengthOption {
  value: TargetLength;
  label: string;
  range: string;
  description: string;
}

const OPTIONS: LengthOption[] = [
  {
    value: "300-500",
    label: "Quick Read",
    range: "300-500 words",
    description: "Short update or news",
  },
  {
    value: "600-1000",
    label: "Standard",
    range: "600-1,000 words",
    description: "Guide or blog article",
  },
  {
    value: "1500-2500",
    label: "In-Depth",
    range: "1,500-2,500 words",
    description: "Comprehensive or competitive",
  },
];

interface LengthSelectorProps {
  value: TargetLength;
  onChange: (v: TargetLength) => void;
}

export function LengthSelector({ value, onChange }: LengthSelectorProps) {
  return (
    <fieldset className="mb-6">
      <legend className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
        Target length
      </legend>
      <div className="grid grid-cols-3 border border-ink/10">
        {OPTIONS.map((opt, i) => (
          <label
            key={opt.value}
            className={cn(
              "relative flex flex-col gap-0.5 px-3 py-3 cursor-pointer",
              "transition-shadow duration-100",
              i < OPTIONS.length - 1 && "border-r border-ink/10",
              value === opt.value
                ? "bg-[#FFF1B8] border border-ink shadow-[4px_4px_0_#111111] z-10"
                : "bg-white hover:shadow-[4px_4px_0_#111111] hover:z-10"
            )}
          >
            <input
              type="radio"
              name="target_length"
              value={opt.value}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              className="sr-only"
            />
            <span className="font-mono text-sm font-medium text-ink">
              {opt.label}
            </span>
            <span className="font-mono text-xs text-graphite">
              {opt.range}
            </span>
            <span className="font-mono text-xs text-graphite/60 leading-snug mt-0.5">
              {opt.description}
            </span>
          </label>
        ))}
      </div>
      {value === "300-500" && (
        <p
          role="status"
          aria-live="polite"
          className="mt-2 font-mono text-xs text-graphite border-l-2 border-ink/30 pl-3"
        >
          TL;DR and FAQ sections are omitted at this length.
        </p>
      )}
    </fieldset>
  );
}
```

Design notes:
- `sr-only` on the radio input -- the entire `<label>` is the interactive target.
- Active state: Highlighter fill + 1px Ink border + `shadow-[4px_4px_0_#111111]`
  matching the Card Active spec (UX-DR5). `z-10` prevents adjacent border overlap.
- Hover state: same hard shadow, no fill change. Matching Button Primary hover pattern.
- `rounded-none` everywhere -- Paper Style mandates no border radius.
- The Quick Read notice uses `role="status"` + `aria-live="polite"` and the same
  left-border hint pattern as the `social_only` note already in the form.

---

### AC 9 -- `NewCampaignPage` wires `LengthSelector`

**Given** `frontend/app/(app)/campaigns/new/page.tsx`,
**When** the story is implemented,
**Then**:

**Import:**
```tsx
import { LengthSelector, type TargetLength } from "@/components/campaigns/LengthSelector";
```

**State** (alongside existing `campaignType` state):
```tsx
const [targetLength, setTargetLength] = useState<TargetLength>("600-1000");
```

**Placement in JSX:** Inside the same `grid-rows` collapse `<div>` that wraps
the keyword fields (the one controlled by `campaignType === "blog_full"`), insert
`<LengthSelector>` as the first child, before the Focus keyword input:

```tsx
<div className={`grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none ${
  campaignType === "blog_full" ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
}`}>
  <div className="overflow-hidden" aria-hidden={campaignType === "social_only" || undefined}>
    {/* NEW -- length selector first */}
    <LengthSelector value={targetLength} onChange={setTargetLength} />

    {/* existing keyword inputs below, unchanged */}
    <div className="space-y-1 mb-2">
      <label ...>Focus keyword ...
```

No other structural changes to the form.

---

### AC 10 -- Draft autosave includes `targetLength`

**Given** the `BrainDumpDraft` interface in `page.tsx` and the autosave
`useEffect`,
**When** the story is implemented,
**Then**:

`BrainDumpDraft` gains:
```ts
targetLength: TargetLength;
```

The autosave draft object gains:
```ts
targetLength,
```

The restore handler (`handleRestoreDraft`) gains:
```ts
setTargetLength(
  ["300-500", "600-1000", "1500-2500"].includes(draftBanner.targetLength)
    ? (draftBanner.targetLength as TargetLength)
    : "600-1000"
);
```

The guard on restore validates the value is a known tier and falls back to
Standard, so stale drafts written before this story was shipped don't crash.

---

### AC 11 -- `handleSubmit` passes `target_word_count`

**Given** the `handleSubmit` function in `page.tsx`,
**When** the story is implemented,
**Then** the `campaignsApi.create(...)` call gains:

```ts
target_word_count: campaignType === "blog_full" ? targetLength : null,
```

Added alongside `campaign_type` and `skip_image`. Social-only campaigns always
send `null` so the backend treats them as Standard (though the value is unused
for social-only pipelines).

---

### AC 12 -- `lib/api.ts` campaign create type

**Given** the TypeScript campaign create payload type in `frontend/lib/api.ts`,
**When** the story is implemented,
**Then** the create payload interface/type gains:
```ts
target_word_count?: "300-500" | "600-1000" | "1500-2500" | null;
```

The field is optional in the type signature (existing call sites that don't pass
it remain valid) but `page.tsx` always passes it explicitly.

---

### AC 13 -- Regeneration preserves `target_word_count`

**Given** `backend/app/db/repositories/campaigns.py` `create_campaign()` and
`backend/app/routers/campaigns.py` `regenerate_campaign`,
**When** the story is implemented,
**Then**:

`create_campaign()` gains a new optional parameter after `skip_image`:
```python
target_word_count: Optional[str] = None,
```
And passes it to the `Campaign(...)` constructor:
```python
campaign = Campaign(
    ...existing fields...,
    target_word_count=target_word_count,
)
```

`regenerate_campaign` router passes it through from the original campaign:
```python
new_campaign = await create_campaign(
    db,
    campaign.client_id,
    campaign.brain_dump,
    target_keyword=campaign.target_keyword,
    target_audience=campaign.target_audience,
    secondary_keywords=campaign.secondary_keywords,
    campaign_type=campaign.campaign_type,
    skip_image=campaign.skip_image,
    target_word_count=campaign.target_word_count,   # <-- new
)
```

Also update the existing `campaigns.py` router `POST /` (campaign create) to pass
`target_word_count=body.target_word_count` into `create_campaign()` if it is not
already doing so via a direct `Campaign(...)` construction -- check the actual
create endpoint implementation and match the pattern.

---

## Dev Notes

**`_BLOG_PROMPT` is a module-level string constant, not a function.** The
`{word_count_range}` and `{length_override_section}` placeholders are filled at
call time by `.format(...)` inside `generate_blog()` in each integration file.
Both integrations (`gemini.py` and `anthropic_client.py`) must receive the
identical change -- missing one means the Anthropic provider ignores the
length selection.

**Quick Read suppresses TL;DR + FAQ via a terminal QUICK READ MODE block**, not
by editing the MANDATORY STRUCTURE template. This approach keeps the prompt
backwards-compatible and avoids touching the hardcoded structure block that
governs Standard/In-Depth output.

**The fidelity check (`check_fidelity`) does NOT need modification.** When Quick
Read omits FAQ, `seo_faq_present` will correctly be `false` in the stored
`voice_score`. This is accurate, not a bug -- the fidelity badge only gates on
`tone_score`, `cadence_score`, and `jargon_violations`, not on FAQ presence.

**`target_word_count=None` from the DB** (existing campaigns, or campaigns
submitted without the field) maps to `"900-1,500 words"` via the fallback in the
`_WORD_COUNT_MAP.get(target_word_count or "", "900-1,500 words")` call. This
preserves the historical behavior for all existing campaigns.

**Do not add `target_word_count` to the roadmap campaign creation path** (Epic
20 `roadmap.py` service) -- roadmap-generated campaigns use a separate pipeline
that is out of scope here.

---

## Tests

Add to the existing backend test suite for generation prompts and the campaign
create endpoint:

1. `test_word_count_standard_default` -- `generate_blog(..., target_word_count=None)` prompt
   contains "900-1,500 words" and no QUICK READ MODE block.
2. `test_word_count_quick_read` -- `generate_blog(..., target_word_count="300-500")` prompt
   contains "300-500 words" and the QUICK READ MODE block (checking for "OMIT the <div
   class=\"tldr\">" string).
3. `test_word_count_in_depth` -- `generate_blog(..., target_word_count="1500-2500")` prompt
   contains "1,500-2,500 words" and no QUICK READ MODE block.
4. `test_campaign_create_with_target_word_count` -- POST `/api/v1/campaigns/` with
   `target_word_count="300-500"` returns 202 and the campaign DB record has
   `target_word_count="300-500"`.
5. `test_campaign_create_invalid_target_word_count` -- POST with
   `target_word_count="999-9999"` returns 422.

Apply the same 5 prompt tests to `anthropic_client.py` if integration tests for
that provider already exist.

---

## Checklist

- [ ] `target_word_count` column added to `Campaign` model
- [ ] Alembic migration generated via CLI (not hand-written)
- [ ] `CampaignCreate` and `CampaignResponse` updated
- [ ] `_BLOG_PROMPT` `{word_count_range}` + `{length_override_section}` placeholders added
- [ ] `gemini.py` `generate_blog` accepts and applies `target_word_count`
- [ ] `anthropic_client.py` `generate_blog` accepts and applies `target_word_count`
- [ ] `generation.py` passes `campaign.target_word_count` to `generate_blog`
- [ ] `LengthSelector.tsx` created exactly as specified
- [ ] `NewCampaignPage` wires state, placement, autosave, and submit payload
- [ ] `lib/api.ts` type updated
- [ ] 5 backend tests passing
- [ ] `social_only` campaigns send `target_word_count: null`
- [ ] Existing campaigns (null DB value) still generate 900-1,500 word articles
- [ ] `create_campaign()` repository accepts `target_word_count` param
- [ ] `regenerate_campaign` router passes `campaign.target_word_count` to `create_campaign()`
