---
title: 'Fix blog template and quick-read prompt injection conflicts'
type: 'bugfix'
created: '2026-08-27'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: 'd52c5f012ea626ec524ae1f990a5a3d387347d74'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** When a non-standard article template (Listicle, Thought Leadership) is combined with Quick Read (300-500 words), the generated blog ignores the template and produces a standard-looking article. Two compounding causes: (1) the Quick Read `length_override_section` instructs the LLM to "write 1-2 H2 body sections" which conflicts with Listicle's `<ol>/<li>/<h3>` structure; (2) post-processing code blindly injects a `<div class="tldr">` even when the selected template explicitly omits it. Supporting keyword injection was also audited and confirmed working end-to-end -- no code fix needed there.

**Approach:** Make `length_override_section` template-aware so structural directives are stripped when a non-standard template is active (keeping only the word count + writing-quality line). Gate the TL;DR post-processing injection so it is skipped for Listicle, Thought-Leadership, and Quick Read mode. Apply identically to both LLM provider modules.

## Boundaries & Constraints

**Always:** Both `gemini.py` and `anthropic_client.py` must receive the same fix. The existing TL;DR injection fallback must be preserved for standard template + non-quick-read combinations where the LLM accidentally omits it. No DB schema, router, or frontend changes. No new LLM calls.

**Ask First:** Nothing.

**Never:** Do not alter `_build_template_structure` internals. Do not remove the TL;DR injection guard entirely.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output |
|----------|--------------|-----------------|
| Listicle + any length | `article_template="listicle"` | No `<div class="tldr">` injected by post-processing; listicle `<ol>` structure intact |
| Thought-Leadership + any length | `article_template="thought-leadership"` | No TL;DR injected by post-processing |
| Quick Read + Listicle | `target_word_count="300-500"`, `article_template="listicle"` | `length_override_section` has word-limit line only; no "1-2 H2 sections" or TL;DR/FAQ omission directives |
| Quick Read + How-To | `target_word_count="300-500"`, `article_template="how-to"` | Word-limit only in override; no structural conflict |
| Quick Read + Standard | `target_word_count="300-500"`, `article_template="standard"` or None | Full QUICK READ MODE block unchanged; TL;DR injection skipped (300-500 still guards it) |
| Standard, non-quick-read, LLM omits TL;DR | `article_template="standard"`, `target_word_count` != "300-500" | TL;DR injection fires (existing fallback preserved) |

</frozen-after-approval>

## Code Map

- `backend/app/integrations/gemini.py:281-293` -- `length_override_section` construction block (gated on `target_word_count == "300-500"`)
- `backend/app/integrations/gemini.py:319-337` -- TL;DR post-processing injection block (no template-awareness today)
- `backend/app/integrations/anthropic_client.py:126-138` -- identical `length_override_section` construction
- `backend/app/integrations/anthropic_client.py:163-183` -- identical TL;DR post-processing injection block
- `backend/app/integrations/generation_prompts.py:551-646` -- `_build_template_structure`; Listicle at :596, Thought-Leadership at :622 both say "Do NOT include a `<div class=\"tldr\">` block"
- `backend/app/integrations/generation_prompts.py:521-548` -- `_build_seo_section` builds "SUPPORTING KEYWORDS" block from `secondary_keywords` -- confirmed injected correctly, no change needed
- `backend/tests/test_generation_prompts.py:307-374` -- existing word-count + template tests; extend for new guard logic

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/integrations/gemini.py` -- In the `length_override_section` block: when `article_template` is set and not `"standard"`, replace the full QUICK READ MODE block with a word-count-only variant: `"QUICK READ MODE (300–500 words):\n- Strict word limit: 300–500 words total including all headings and HTML.\n- Every sentence must earn its place. Cut anything that does not give the reader a new fact or a specific action."` (omit structural lines about H2 count, TL;DR, FAQ). In the TL;DR injection block: wrap it in `if article_template not in ("listicle", "thought-leadership") and target_word_count != "300-500":` -- `article_template` and `target_word_count` are already local variables in scope.
- [x] `backend/app/integrations/anthropic_client.py` -- Apply the identical two-part fix to its `length_override_section` block and TL;DR injection block.
- [x] `backend/tests/test_generation_prompts.py` -- Add: (a) `test_quick_read_listicle_no_h2_directive` -- asserts "H2 body sections" not in `length_override_section` when template is listicle; (b) `test_quick_read_standard_full_block` -- asserts full QUICK READ MODE block present when template is standard; (c) `test_tldr_injection_skipped_for_listicle` -- shows that a simulated listicle result (no tldr block) would satisfy the guard condition.

**Acceptance Criteria:**
- Given `article_template="listicle"` and any `target_word_count`, when post-processing runs on LLM output lacking `<div class="tldr">`, then no TL;DR is injected.
- Given `target_word_count="300-500"` and `article_template="listicle"`, when the prompt is assembled, then `length_override_section` contains the word-limit line and does NOT contain "Write 1-2 H2 body sections".
- Given `target_word_count="300-500"` and `article_template=None` (standard), when the prompt is assembled, then the full QUICK READ MODE block is present and unchanged.
- Given `target_word_count="600-1000"` and `article_template="standard"`, when LLM output omits TL;DR, then post-processing injects the fallback TL;DR (existing behaviour preserved).

## Verification

**Commands:**
- `cd backend && python -m pytest tests/test_generation_prompts.py -v` -- expected: all tests pass including new cases

## Design Notes

The `length_override_section` Quick Read structural directives ("Write 1-2 H2 body sections", "OMIT the TL;DR", "OMIT the FAQ") are meaningless for non-standard templates because those templates have already replaced the MANDATORY STRUCTURE entirely. Sending contradictory structural signals causes the LLM to revert to the default (standard) shape. The word-count constraint and writing-quality rules are template-agnostic and should always be included.

## Suggested Review Order

**Shared prompt logic (entry point)**

- Single source of truth for QUICK READ MODE prompt text; branches on template type
  [`generation_prompts.py:551`](../../backend/app/integrations/generation_prompts.py#L551)

**Gemini provider**

- Provider now delegates to the shared helper; 2-line replacement of 20-line inline block
  [`gemini.py:283`](../../backend/app/integrations/gemini.py#L283)

- TL;DR injection guard made case-insensitive; skips listicle + thought-leadership + quick-read
  [`gemini.py:318`](../../backend/app/integrations/gemini.py#L318)

**Anthropic provider (mirrors Gemini exactly)**

- Same delegation to shared helper
  [`anthropic_client.py:128`](../../backend/app/integrations/anthropic_client.py#L128)

- Same case-insensitive injection guard
  [`anthropic_client.py:163`](../../backend/app/integrations/anthropic_client.py#L163)

**Tests**

- New word-count tests call `build_quick_read_override` directly from production code (not a replica)
  [`test_generation_prompts.py:376`](../../backend/tests/test_generation_prompts.py#L376)

- TL;DR injection guard tests; `_should_inject_tldr` updated to match case-insensitive guard
  [`test_generation_prompts.py:416`](../../backend/tests/test_generation_prompts.py#L416)
