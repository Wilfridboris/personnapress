---
depends_on: 3-23-blog-target-length-selector
---

# Story 3.24: Blog Article Template Selector

Status: ready-for-dev

## Story

As a PersonnaPress user creating a blog campaign,
I want to choose an article structure template before generating,
so that the output matches the format that best fits my content goal.

## Context & Motivation

Story 3-23 added length selection. This story adds structural template selection.
The current generation prompt hardcodes a single MANDATORY STRUCTURE (H2-body + FAQ
+ Conclusion). This works well for evergreen articles but produces the wrong shape
for how-to guides (users expect numbered steps), listicles (users expect numbered
lists), and opinion pieces (users expect an argument arc, not FAQ).

Four templates are supported:

| Template | Replaces standard structure with |
|---|---|
| Standard (default) | No change -- existing MANDATORY STRUCTURE |
| How-To Guide | TL;DR + prerequisites + numbered steps + mistakes + FAQ + wrap-up |
| Listicle | Hook paragraph + `<ol>` numbered items with `<h3>` titles + recap |
| Thought Leadership | Bold opener + argument + evidence + counter + rebuttal + CTA |

**Fidelity check note:** Listicle articles produce `seo_h2_count: 0` and
`seo_faq_present: false` because the primary structure is `<ol><li><h3>`, not
`<h2>` sections, and there is no FAQ. Thought Leadership produces
`seo_faq_present: false`. These are correct, accurate values for their formats
and do not affect the voice badge (which only gates on tone/cadence/jargon).
The fidelity check does not need modification.

**Tiptap editor note:** The WYSIWYG editor already supports `<ol>`, `<ul>`,
`<h3>`, `<strong>`, `<em>` via starter-kit. Listicle and How-To Guide output
will render and be editable correctly without editor changes.

---

## Files Touched

| File | Change |
|---|---|
| `backend/app/db/repositories/models.py` | ADD `article_template` column to `Campaign` |
| `backend/alembic/versions/<new>.py` | ADD migration |
| `backend/app/schemas/campaign.py` | ADD `article_template` to `CampaignCreate` + `CampaignResponse` |
| `backend/app/integrations/generation_prompts.py` | ADD `{template_structure_override}` placeholder + `_build_template_structure()` helper |
| `backend/app/integrations/gemini.py` | ADD `article_template` param to `generate_blog` |
| `backend/app/integrations/anthropic_client.py` | ADD `article_template` param to `generate_blog` |
| `backend/app/services/generation.py` | Pass `campaign.article_template` to `generate_blog` |
| `frontend/components/campaigns/TemplateSelector.tsx` | NEW component |
| `frontend/app/(app)/campaigns/new/page.tsx` | Wire `TemplateSelector`, autosave, API call |
| `frontend/lib/api.ts` | ADD `article_template` to campaign create payload type |

---

## Acceptance Criteria

### AC 1 -- DB column on `Campaign`

**Given** `backend/app/db/repositories/models.py` `class Campaign`,
**When** the story is implemented,
**Then** a new column exists immediately after `target_word_count` (added by 3-23):

```python
article_template: Optional[str] = Field(
    default=None,
    sa_column=Column(Text, nullable=True),
)
```

Valid values: `"standard"`, `"how-to"`, `"listicle"`, `"thought-leadership"`.
`null` in DB is treated as `"standard"` at generation time. No DB-level enum
constraint -- validation is in the Pydantic schema.

---

### AC 2 -- Alembic migration

**Given** the project uses Alembic with timestamp-prefixed filenames,
**When** the developer runs:
```
cd backend && alembic revision --autogenerate -m "add_article_template_to_campaigns"
```
**Then** the generated migration contains:

```python
op.add_column(
    "campaigns",
    sa.Column("article_template", sa.Text(), nullable=True),
)
```

And `downgrade` reverses it with `op.drop_column("campaigns", "article_template")`.

**Critical:** Never hand-write the revision ID. Always use the CLI
(see `project-context.md` -- a hand-written duplicate revision ID once blocked
all deployments).

---

### AC 3 -- Schema: `CampaignCreate` and `CampaignResponse`

**Given** `backend/app/schemas/campaign.py`,
**When** the story is implemented,
**Then**:

`CampaignCreate` gains (after `target_word_count`):
```python
article_template: Optional[Literal["standard", "how-to", "listicle", "thought-leadership"]] = None
```

`CampaignResponse` gains (after `target_word_count`):
```python
article_template: Optional[str] = None
```

---

### AC 4 -- `_build_template_structure()` helper in `generation_prompts.py`

**Given** `backend/app/integrations/generation_prompts.py`,
**When** the story is implemented,
**Then** a new private function `_build_template_structure` exists after the
existing `_build_seo_section` function:

```python
def _build_template_structure(
    article_template: str | None,
    meta_voice_note: str,
) -> str:
    """Return a template_structure_override string for non-standard templates.

    Returns empty string for "standard" or None (existing MANDATORY STRUCTURE applies).
    For all other templates, returns a block that explicitly replaces the
    MANDATORY STRUCTURE.
    """
    tmpl = (article_template or "standard").lower()
    if tmpl == "standard":
        return ""

    if tmpl == "how-to":
        return (
            "TEMPLATE: HOW-TO GUIDE\n"
            "Disregard the MANDATORY STRUCTURE above. Use this structure instead:\n"
            "<h1>[Action-first title starting with \"How to\" or a direct instruction verb]</h1>\n"
            f"<!-- meta: [One sentence, max 150 chars, ends with action phrase{meta_voice_note}] -->\n"
            "<!-- excerpt: [One engaging editorial hook, max 240 chars, conversational -- open with a provocative question, a surprising fact, or an intriguing observation; NOT a summary] -->\n"
            "<div class=\"tldr\"><p><strong>TL;DR:</strong> [Complete this guide and you will [specific outcome]. [What you need in one sentence].]</p></div>\n"
            "<p>[BLUF intro: who this is for and what outcome they will achieve. State it in the first sentence.]</p>\n"
            "<h2>What You Will Need</h2>\n"
            "<ul>\n"
            "  <li>[Tool or prerequisite 1]</li>\n"
            "  <li>[Tool or prerequisite 2]</li>\n"
            "</ul>\n"
            "<h2>Step 1: [First action as a verb phrase]</h2>\n"
            "<p>[Explain the step. If the brain dump contains a specific example or outcome for this step, lead with it.]</p>\n"
            "<h2>Step 2: [Second action]</h2>\n"
            "<p>...</p>\n"
            "[Continue for 3-5 total steps. Each step is one H2. Do not use H3 inside steps.]\n"
            "<h2>Common Mistakes to Avoid</h2>\n"
            "<p>[1-3 specific mistakes drawn from the brain dump. Not generic advice.]</p>\n"
            "<h2>Frequently Asked Questions</h2>\n"
            "<dl class=\"faq\">\n"
            "  <dt>[Question 1]</dt><dd><strong>[Direct answer.]</strong> [1-2 sentences.]</dd>\n"
            "  <dt>[Question 2]</dt><dd><strong>[Direct answer.]</strong> [1-2 sentences.]</dd>\n"
            "  <dt>[Question 3]</dt><dd><strong>[Direct answer.]</strong> [1-2 sentences.]</dd>\n"
            "</dl>\n"
            "<h2>[Wrap-up heading: \"What to Try Next\", \"Your Next Step\", or similar]</h2>\n"
            "<p>[Single clear action. Forward momentum. No recap.]</p>"
        )

    if tmpl == "listicle":
        return (
            "TEMPLATE: LISTICLE\n"
            "Disregard the MANDATORY STRUCTURE above. Use this structure instead:\n"
            "<h1>[[Number] [Things/Ways/Reasons/Mistakes] [verb phrase] -- specific and direct]</h1>\n"
            f"<!-- meta: [One sentence, max 150 chars, ends with action phrase{meta_voice_note}] -->\n"
            "<!-- excerpt: [One engaging editorial hook, max 240 chars, conversational] -->\n"
            "<p>[Hook paragraph: the problem this list solves, why it matters, who should read it. "
            "2-3 sentences. This replaces the TL;DR -- state the payoff upfront. "
            "Do NOT include a <div class=\"tldr\"> block.]</p>\n"
            "<ol>\n"
            "  <li>\n"
            "    <h3>[Item title: specific and direct, 4-8 words]</h3>\n"
            "    <p>[80-120 word explanation. Lead with one specific example, number, or outcome. Avoid generic advice.]</p>\n"
            "  </li>\n"
            "  <li>\n"
            "    <h3>[Item title]</h3>\n"
            "    <p>...</p>\n"
            "  </li>\n"
            "  [Continue for the number of items named in the H1. Each item is one <li>. "
            "Do NOT use <h2> sections. Do NOT add a FAQ section.]\n"
            "</ol>\n"
            "<p>[Recap paragraph: the single most important takeaway across all items. "
            "End with a call to action or an honest opinion. 2-3 sentences.]</p>"
        )

    if tmpl == "thought-leadership":
        return (
            "TEMPLATE: THOUGHT LEADERSHIP\n"
            "Disregard the MANDATORY STRUCTURE above. Use this structure instead:\n"
            "<h1>[Bold contrarian claim or clear opinion as title -- not a question, not a how-to]</h1>\n"
            f"<!-- meta: [One sentence, max 150 chars, ends with action phrase{meta_voice_note}] -->\n"
            "<!-- excerpt: [Open with the author's position in one sharp sentence. Max 240 chars.] -->\n"
            "<p>[Opening paragraph: state your position in the first sentence without hedging. "
            "If the brain dump contains an AUTHORED PASSAGE with a first-person opinion, use it here verbatim. "
            "Do NOT include a <div class=\"tldr\"> block -- this paragraph IS the TL;DR.]</p>\n"
            "<h2>[Your core argument: name the thing most people get wrong or misunderstand]</h2>\n"
            "<p>[Make the case. Use specific numbers, named examples, or personal experience from the brain dump. "
            "State the argument as the author's direct view, not universal fact.]</p>\n"
            "<h2>[Your evidence: the specific experience, test, or data point]</h2>\n"
            "<p>[Concrete and specific. First-person where the brain dump supports it.]</p>\n"
            "<h2>[The counter-argument: steelman the opposing view honestly]</h2>\n"
            "<p>[Acknowledge what is true in the opposite position. Then explain why your view still holds.]</p>\n"
            "<h2>[Your rebuttal or the nuance that resolves the tension]</h2>\n"
            "<p>...</p>\n"
            "<h2>[Call to action: one specific thing the reader should do, think, or stop doing]</h2>\n"
            "<p>[Closing with forward momentum. No recap. End with your honest opinion. "
            "Do NOT add a FAQ section.]</p>"
        )

    return ""
```

---

### AC 5 -- `{template_structure_override}` placeholder in `_BLOG_PROMPT`

**Given** `_BLOG_PROMPT` in `generation_prompts.py` (already modified by story
3-23 to include `{length_override_section}`),
**When** the story is implemented,
**Then** a new placeholder `{template_structure_override}` is inserted immediately
before `{length_override_section}`:

```
...BANNED WORDS block...

{template_structure_override}

{length_override_section}

Output ONLY the HTML above. Do NOT append...
```

For Standard or null, `template_structure_override = ""` (empty string) and the
existing MANDATORY STRUCTURE block continues to apply.

For non-Standard templates, the block says "Disregard the MANDATORY STRUCTURE
above. Use this structure instead: [template HTML]" -- overriding the hardcoded
structure cleanly via a terminal instruction.

---

### AC 6 -- `generate_blog` in both integrations accepts `article_template`

**Given** `backend/app/integrations/gemini.py` and
`backend/app/integrations/anthropic_client.py`,
**When** the story is implemented,
**Then** both `generate_blog` functions gain:

```python
article_template: str | None = None,
```
Added after `target_word_count` (from 3-23).

Inside the function, after the existing `meta_voice_note` call and before
`_BLOG_PROMPT.format(...)`, add:

```python
template_structure_override = _build_template_structure(article_template, meta_voice_note)
```

Then add `template_structure_override=template_structure_override` to the
`.format(...)` call alongside the other kwargs.

`_build_template_structure` is imported from `generation_prompts` alongside the
existing imports.

---

### AC 7 -- `generation.py` passes `campaign.article_template`

**Given** `backend/app/services/generation.py` Step 2,
**When** the story is implemented,
**Then** the `_llm_with_retry` call for `generate_blog` gains:

```python
blog_html: str = await _llm_with_retry(
    _llm.generate_blog,
    campaign.brain_dump,
    brand_voice_profile,
    _BLOG_THINKING_TOKENS,
    campaign.target_keyword,
    campaign.target_audience,
    campaign.secondary_keywords,
    target_word_count=campaign.target_word_count,
    article_template=campaign.article_template,   # <-- new
)
```

No other changes to `generation.py`.

---

### AC 8 -- `TemplateSelector` component

**Given** `frontend/components/campaigns/TemplateSelector.tsx` does not exist,
**When** the story is implemented,
**Then** it is created with the following exact implementation:

```tsx
"use client";

import { cn } from "@/lib/utils";

export type ArticleTemplate = "standard" | "how-to" | "listicle" | "thought-leadership";

interface TemplateOption {
  value: ArticleTemplate;
  label: string;
  tagline: string;
  outline: string[];
}

const TEMPLATES: TemplateOption[] = [
  {
    value: "standard",
    label: "Standard",
    tagline: "Hook, body sections, FAQ, conclusion",
    outline: ["TL;DR", "BLUF intro", "3-4 H2 body sections", "FAQ", "Conclusion"],
  },
  {
    value: "how-to",
    label: "How-To Guide",
    tagline: "Step-by-step instructional",
    outline: ["TL;DR", "What you will need", "Steps 1-5", "Common mistakes", "FAQ", "Wrap-up"],
  },
  {
    value: "listicle",
    label: "Listicle",
    tagline: "Numbered Top-N format",
    outline: ["Hook paragraph", "Numbered items (each ~100 words)", "Recap"],
  },
  {
    value: "thought-leadership",
    label: "Thought Leadership",
    tagline: "Opinion-driven personal take",
    outline: ["Bold opener", "Your argument", "Your evidence", "Counter-argument", "Rebuttal", "Call to action"],
  },
];

interface TemplateSelectorProps {
  value: ArticleTemplate;
  onChange: (v: ArticleTemplate) => void;
}

export function TemplateSelector({ value, onChange }: TemplateSelectorProps) {
  return (
    <fieldset className="mb-6">
      <legend className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
        Article structure
      </legend>
      <div className="grid grid-cols-2 border border-ink/10">
        {TEMPLATES.map((tpl, i) => (
          <label
            key={tpl.value}
            className={cn(
              "group/card relative flex flex-col gap-0.5 px-3 py-3 cursor-pointer",
              "transition-shadow duration-100",
              (i === 0 || i === 1) && "border-b border-ink/10",
              (i === 0 || i === 2) && "border-r border-ink/10",
              value === tpl.value
                ? "bg-[#FFF1B8] border border-ink shadow-[4px_4px_0_#111111] z-10"
                : "bg-white hover:shadow-[4px_4px_0_#111111] hover:z-10"
            )}
          >
            <input
              type="radio"
              name="article_template"
              value={tpl.value}
              checked={value === tpl.value}
              onChange={() => onChange(tpl.value)}
              className="sr-only"
            />
            <span className="font-mono text-sm font-medium text-ink">
              {tpl.label}
            </span>
            <span className="font-mono text-xs text-graphite/70 leading-snug">
              {tpl.tagline}
            </span>

            {/* CSS-only hover preview popover -- no JS state needed */}
            <div
              role="tooltip"
              className={cn(
                "pointer-events-none absolute bottom-full left-0 mb-2 w-52 z-20",
                "border border-ink/10 bg-white shadow-[4px_4px_0_#111111] px-3 py-2",
                "opacity-0 invisible translate-y-1",
                "group-hover/card:opacity-100 group-hover/card:visible group-hover/card:translate-y-0",
                "transition-all duration-150"
              )}
            >
              <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-2">
                Structure
              </p>
              <ol className="space-y-1">
                {tpl.outline.map((item) => (
                  <li
                    key={item}
                    className="font-mono text-xs text-ink flex items-start gap-1.5"
                  >
                    <span className="text-graphite/40 select-none" aria-hidden="true">-</span>
                    {item}
                  </li>
                ))}
              </ol>
            </div>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
```

Design notes (Paper Style compliance):
- `rounded-none` throughout -- no border radius anywhere.
- 2x2 grid: top row has `border-b`; left column has `border-r`.
- Active: Highlighter fill + 1px Ink border + `shadow-[4px_4px_0_#111111]` + `z-10`.
- Hover: hard shadow only, no fill change. `z-10` prevents shadow clipping.
- Tooltip: `pointer-events-none` so hovering the tooltip does not break `group-hover`.
  Opens upward (`bottom-full mb-2`) so it never overlaps the textarea below.
  CSS-only -- no Framer Motion, no JS state (CSS can handle it).
- `sr-only` radio input: keyboard users navigate with arrow keys; entire `<label>`
  is the hit target.
- No emojis anywhere (project constraint).

---

### AC 9 -- `NewCampaignPage` wires `TemplateSelector`

**Given** `frontend/app/(app)/campaigns/new/page.tsx`,
**When** the story is implemented,
**Then**:

**Import:**
```tsx
import { TemplateSelector, type ArticleTemplate } from "@/components/campaigns/TemplateSelector";
```

**State:**
```tsx
const [articleTemplate, setArticleTemplate] = useState<ArticleTemplate>("standard");
```

**Placement in JSX:** Inside the `blog_full` collapse `<div>`, insert
`<TemplateSelector>` immediately after `<LengthSelector>` (added in 3-23) and
before the Focus keyword input:

```tsx
<div className={`grid transition-[grid-template-rows] ...`}>
  <div className="overflow-hidden" aria-hidden={...}>
    <LengthSelector value={targetLength} onChange={setTargetLength} />
    <TemplateSelector value={articleTemplate} onChange={setArticleTemplate} />

    {/* existing keyword inputs below, unchanged */}
    <div className="space-y-1 mb-2">
      <label ...>Focus keyword ...
```

---

### AC 10 -- Draft autosave includes `articleTemplate`

**Given** the `BrainDumpDraft` interface in `page.tsx`,
**When** the story is implemented,
**Then**:

`BrainDumpDraft` gains:
```ts
articleTemplate: ArticleTemplate;
```

The autosave draft object gains:
```ts
articleTemplate,
```

The restore handler gains:
```ts
const validTemplates: ArticleTemplate[] = ["standard", "how-to", "listicle", "thought-leadership"];
setArticleTemplate(
  validTemplates.includes(draftBanner.articleTemplate)
    ? draftBanner.articleTemplate
    : "standard"
);
```

---

### AC 11 -- `handleSubmit` passes `article_template`

**Given** the `handleSubmit` function in `page.tsx`,
**When** the story is implemented,
**Then** `campaignsApi.create(...)` gains:

```ts
article_template: campaignType === "blog_full" ? articleTemplate : null,
```

Social-only campaigns send `null` (the field is unused for social pipelines).

---

### AC 12 -- `lib/api.ts` campaign create type

**Given** the TypeScript campaign create payload type in `frontend/lib/api.ts`,
**When** the story is implemented,
**Then** the type gains:
```ts
article_template?: "standard" | "how-to" | "listicle" | "thought-leadership" | null;
```

---

### AC 13 -- Regeneration preserves `article_template`

**Given** `backend/app/db/repositories/campaigns.py` `create_campaign()` and
`backend/app/routers/campaigns.py` `regenerate_campaign`,
**When** the story is implemented,
**Then**:

`create_campaign()` gains a new optional parameter after `target_word_count`
(added by story 3-23):
```python
article_template: Optional[str] = None,
```
And passes it to the `Campaign(...)` constructor:
```python
campaign = Campaign(
    ...existing fields...,
    article_template=article_template,
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
    target_word_count=campaign.target_word_count,
    article_template=campaign.article_template,     # <-- new
)
```

Also verify the campaign create router endpoint (`POST /`) passes
`article_template=body.article_template` into `create_campaign()`.

---

## Dev Notes

**Composability with story 3-23:** The `{template_structure_override}` placeholder
is inserted before `{length_override_section}` in `_BLOG_PROMPT`. Both apply
independently. A Quick Read Listicle sends both: the Listicle structure override
replaces the MANDATORY STRUCTURE, and the Quick Read block applies a word count
limit. The Quick Read block's instruction to "omit TL;DR" is redundant for
Listicle (it already has none) and harmless.

**Standard template (null or "standard") changes nothing.** `_build_template_structure`
returns `""` for Standard, leaving `{template_structure_override}` as an empty
string. The existing MANDATORY STRUCTURE block in the prompt continues to govern
the output. No existing behavior changes.

**Tiptap WYSIWYG editor requires no changes.** The editor already handles `<ol>`,
`<ul>`, `<h3>` via starter-kit. Listicle and How-To Guide HTML renders and
edits correctly.

**Fidelity check requires no changes.** Listicle returns `seo_h2_count: 0` and
`seo_faq_present: false` because these accurately reflect the listicle structure.
Thought Leadership returns `seo_faq_present: false` for the same reason. Neither
triggers the voice badge (which only reads `tone_score`, `cadence_score`, and
`jargon_violations`). The values stored in `voice_score` JSONB are correct.

**`_build_template_structure` must import `meta_voice_note` as a parameter**, not
re-derive it inside the function. This is because `meta_voice_note` is derived
from the BVP inside `generate_blog()` and would require passing the BVP into the
helper -- passing the already-computed string is simpler and correct.

**Do not add `article_template` to the roadmap campaign creation path** (Epic 20
`roadmap.py` service) -- roadmap-generated campaigns are out of scope here.

---

## Tests

1. `test_template_standard_no_override` -- `_build_template_structure("standard", "")` returns `""`.
2. `test_template_none_no_override` -- `_build_template_structure(None, "")` returns `""`.
3. `test_template_how_to_structure` -- `_build_template_structure("how-to", "")` contains
   "HOW-TO GUIDE", "What You Will Need", "Step 1:", "Frequently Asked Questions".
4. `test_template_listicle_structure` -- `_build_template_structure("listicle", "")` contains
   "LISTICLE", "<ol>", "<h3>", "Do NOT add a FAQ section".
5. `test_template_thought_leadership_structure` -- `_build_template_structure("thought-leadership", "")`
   contains "THOUGHT LEADERSHIP", "counter-argument", "Do NOT add a FAQ section".
6. `test_campaign_create_with_article_template` -- POST `/api/v1/campaigns/` with
   `article_template="how-to"` returns 202 and DB record has `article_template="how-to"`.
7. `test_campaign_create_invalid_article_template` -- POST with `article_template="newsletter"`
   returns 422.

---

## Checklist

- [ ] `article_template` column added to `Campaign` model
- [ ] Alembic migration generated via CLI (not hand-written)
- [ ] `CampaignCreate` and `CampaignResponse` updated
- [ ] `_build_template_structure()` helper added to `generation_prompts.py`
- [ ] `{template_structure_override}` placeholder added before `{length_override_section}` in `_BLOG_PROMPT`
- [ ] `gemini.py` `generate_blog` accepts and applies `article_template`
- [ ] `anthropic_client.py` `generate_blog` accepts and applies `article_template`
- [ ] `generation.py` passes `campaign.article_template` to `generate_blog`
- [ ] `TemplateSelector.tsx` created exactly as specified
- [ ] `NewCampaignPage` wires state, placement (after `LengthSelector`), autosave, submit payload
- [ ] `lib/api.ts` type updated
- [ ] 7 backend tests passing
- [ ] Standard/null template produces zero prompt changes (existing behavior preserved)
- [ ] Social-only campaigns send `article_template: null`
- [ ] `create_campaign()` repository accepts `article_template` param
- [ ] `regenerate_campaign` router passes `campaign.article_template` to `create_campaign()`
