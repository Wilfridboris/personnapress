---
title: 'Fix excerpt and meta-description lost during blog approval'
type: 'bugfix'
created: '2026-07-19'
baseline_commit: '86efb5aabff95a1879d93cc8edce88d05e4bda91'
status: 'done'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** After generating a blog, the article's `excerpt` shows TL;DR content and `meta_description` is empty. The root cause: the approval flow unconditionally calls `blogEditorRef.current.getCurrentHtml()` (TipTap), which silently drops HTML comments and unwraps `<div class="tldr">` into plain paragraphs, then PATCHes this degraded HTML to `campaign.blog_html` in the DB — even when the user made zero edits — destroying the `<!-- excerpt: ... -->` and `<!-- meta: ... -->` comments before `create_or_update_article_from_campaign` can extract them.

**Approach:** (1) Expose `isDirty` from `BlogEditorHandle` so the approval panel knows whether actual changes were made. (2) Skip the `blog_html` patch in the approval flow when the editor is clean. (3) Harden the excerpt fallback to skip TL;DR paragraphs that lost their `div.tldr` wrapper via TipTap serialization.

## Boundaries & Constraints

**Always:**
- Blog HTML is only PATCHed to the DB during approval when the user has actually edited it (`isDirty === true` at the time of approval click; explicit Save resets dirty to false, so a save-then-approve sequence correctly sends no extra patch — the saved version is already in the DB).
- `BlogEditorHandle` stays backward-compatible: `getCurrentHtml()` signature unchanged; `isDirty` is additive.
- No schema changes, no new DB columns, no new API endpoints.

**Ask First:** None anticipated.

**Never:**
- Do not attempt to make TipTap preserve HTML comments or `<div>` nodes — that requires a custom extension and opens scope beyond this fix.
- Do not change how the explicit "Save edits" button works.
- Do not add migration logic for existing articles.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Approve with no edits | `isDirty = false`, DB has comments | `blog_html` NOT included in approval PATCH; article gets correct excerpt + meta | N/A |
| Approve after editing (no explicit save) | `isDirty = true` | `blog_html` included (TipTap output); excerpt/meta fall back gracefully | N/A |
| Approve after Save then no edits | `isDirty = false` (reset by save) | `blog_html` NOT re-patched; DB already has the saved version | N/A |
| Fallback excerpt — TL;DR as plain `<p>` | HTML: `<p>TL;DR: ...</p><p>Actual intro</p>` | Skip TL;DR paragraph; return "Actual intro" | Return `""` if no usable `<p>` found |
| Fallback excerpt — TL;DR in original `<div>` | HTML has `<div class="tldr">` | Remove div, return first `<p>` (existing behaviour, unchanged) | N/A |

</frozen-after-approval>

## Code Map

- `frontend/components/campaigns/BlogEditor.tsx:14-16,147-149` -- `BlogEditorHandle` interface + `useImperativeHandle`; add `isDirty: boolean`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx:338-350` -- `handleApprove`; reads `blogEditorRef.current.isDirty` before deciding to include `blog_html`
- `backend/app/services/articles.py:20-38` -- `_extract_excerpt`; fallback must skip `<p>` nodes whose text starts with `TL;DR:`

## Tasks & Acceptance

**Execution:**
- [x] `frontend/components/campaigns/BlogEditor.tsx` -- Add `isDirty: boolean` to `BlogEditorHandle` interface; expose it from `useImperativeHandle` alongside `getCurrentHtml` -- so the approval panel can conditionally include blog_html
- [x] `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` -- In `handleApprove`, read `blogEditorRef.current?.isDirty`; set `blogHtml = isDirtyBlog ? blogEditorRef.current.getCurrentHtml() : undefined`; the existing spread `...(blogHtml ? { blog_html: blogHtml } : {})` will correctly exclude it when undefined
- [x] `backend/app/services/articles.py` -- In `_extract_excerpt` fallback (after `tldr.decompose()`), add a loop that decomposes any remaining `<p>` whose stripped text starts with `"TL;DR:"` before calling `soup.find("p")`

**Acceptance Criteria:**
- Given a freshly generated campaign in `pending_approval` status, when the user clicks Approve without editing, then `campaign.blog_html` in the DB retains the original Gemini-generated HTML (with comments), and the created article's `excerpt` and `meta_description` contain content extracted from the `<!-- excerpt: ... -->` and `<!-- meta: ... -->` comments respectively.
- Given a campaign where the user made and saved blog edits before approving, when the article is created, then `excerpt` is non-empty and does not start with "TL;DR:".
- Given `_extract_excerpt` called with HTML where `<div class="tldr">` was converted to `<p>TL;DR: ...</p>` by TipTap, when the fallback runs, then the returned text is taken from the first non-TL;DR paragraph.
- Given the existing `BlogEditorHandle` consumers (e.g. other uses of `getCurrentHtml`), when the interface is updated, then no TypeScript errors are introduced.

## Spec Change Log

## Design Notes

The `isDirty` flag is already tracked inside `BlogEditor`; it starts `false`, flips `true` on any editor `onUpdate`, and resets to `false` after an explicit save. Exposing it via the handle requires zero new state — only the `useImperativeHandle` return value changes.

The approval-panel change:
```typescript
const isDirtyBlog = blogEditorRef?.current?.isDirty ?? false;
const blogHtml = isDirtyBlog ? blogEditorRef?.current?.getCurrentHtml() : undefined;
```

The TL;DR paragraph skip in the Python fallback:
```python
for p in list(soup.find_all("p")):
    if p.get_text(strip=True).startswith("TL;DR:"):
        p.decompose()
```
Place this after the `tldr.decompose()` block, before `soup.find("p")`.

## Suggested Review Order

**Dirty-state guard — preserving Gemini HTML through approval**

- Entry point: `isDirty` read here determines whether `blog_html` is patched at all.
  [`approval-panel.tsx:341`](../../frontend/app/(app)/campaigns/[id]/approval-panel.tsx#L341)

- Interface contract: `isDirty: boolean` added to `BlogEditorHandle` — additive, backward-compatible.
  [`BlogEditor.tsx:16`](../../frontend/components/campaigns/BlogEditor.tsx#L16)

- Wiring: existing internal `isDirty` state surfaced via `useImperativeHandle` — zero new state.
  [`BlogEditor.tsx:150`](../../frontend/components/campaigns/BlogEditor.tsx#L150)

**Excerpt fallback hardening — TL;DR paragraph skip**

- Fallback loop: decomposes any `<p>` whose text starts "tl;dr:" (case-insensitive) before grabbing first paragraph.
  [`articles.py:37`](../../backend/app/services/articles.py#L37)

## Verification

**Commands:**
- `cd frontend && npx tsc --noEmit` -- expected: 0 errors
- `cd frontend && npx vitest run --reporter=verbose 2>&1 | tail -20` -- expected: all tests pass
- `cd backend && python -m pytest tests/services/test_articles.py -v` -- expected: all pass

**Manual checks (if no CLI):**
- Generate a new campaign, approve without editing → open the created article in the editor and confirm excerpt ≠ TL;DR content and meta_description ≠ empty.
