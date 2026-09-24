---
title: 'Fix link type (nofollow/dofollow) toggle not persisting when editing an existing link'
type: 'bugfix'
created: '2026-09-23'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '187a56aeb961070349252fac653f6e7f296e5033'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** In the blog editor, changing an existing link's type from Nofollow to Dofollow (or vice versa) does not persist — the link keeps its old `rel`. Most visible on articles published via the token/headless write API, whose links arrive with no `rel` and are displayed as "Nofollow", so the user's attempt to flip them to Dofollow appears to do nothing.

**Approach:** In `handleLinkConfirm`, extend the selection across the whole link mark (`extendMarkRange("link")`) before calling `setLink`. TipTap's `setLink` is `setMark` with no range extension, so on a collapsed cursor (the normal way to edit an existing link) it only sets stored marks and never rewrites the surrounding link's attributes. `unsetLink`/`toggleLink` already extend empty mark ranges internally; only `setLink` is missing it. No backend change is needed — both sanitizers already preserve `rel`.

## Boundaries & Constraints

**Always:** Fix must make link-type edits persist for both a collapsed cursor inside a link and a full text selection. Keep the existing `setLink` attribute payload (rel + target coupling) unchanged. Frontend-only change.

**Ask First:** Changing the display-default semantics at `BlogEditor.tsx:274` (a link with no `rel` is currently shown as "Nofollow", though semantically no-`rel` is dofollow). Leaving it as-is is acceptable for this fix; flipping the default is a separate product decision.

**Never:** Do not touch either backend sanitizer (`html_sanitize.py`, `campaigns.py`) — they already preserve `rel` correctly and are not the cause. Do not add a `rel` or `target` default to the Link extension's `HTMLAttributes`. Do not switch the dialog from `setLink` to `toggleLink`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Edit existing link, collapsed cursor | Cursor inside a link with `rel="nofollow noopener noreferrer"`; user picks Dofollow, Update | Whole link's `rel` becomes `noopener noreferrer`; reopening dialog shows Dofollow; persists after save + reload | N/A |
| Edit token-API link (no rel), collapsed cursor | Cursor inside `<a href>` (no rel); user picks Dofollow, Update | Link gets `rel="noopener noreferrer"`; reopening shows Dofollow | N/A |
| Insert link on new text selection | Text selected, no existing link; user sets URL + type | Link created over the selection with correct `rel`/`target` (unchanged from today) | Invalid URL → confirm disabled |
| Flip Dofollow → Nofollow, collapsed cursor | Cursor in `rel="noopener noreferrer"` link; user picks Nofollow, Update | `rel` becomes `nofollow noopener noreferrer`, `target="_blank"` added | N/A |

</frozen-after-approval>

## Code Map

- `frontend/components/campaigns/BlogEditor.tsx:282-290` -- `handleLinkConfirm`; the fix site. Currently `editor.chain().focus().setLink({...}).run()` with no `extendMarkRange("link")`.
- `frontend/components/campaigns/BlogEditor.tsx:267-276` -- `openLinkDialog`; reads `getAttributes("link").rel`, treats empty/`nofollow`-containing rel as Nofollow (line 274). Explains why no-rel links display as Nofollow. Do not change under this fix (see Ask First).
- `frontend/components/campaigns/BlogEditor.tsx:623-633` -- "Remove link" uses `unsetLink()`, which already extends empty mark ranges; confirms only `setLink` is broken. Read-only reference.
- `node_modules/@tiptap/extension-link/dist/index.js:367-391` -- proof: `setLink` = `chain().setMark(...)` (no extend); `toggleLink`/`unsetLink` pass `extendEmptyMarkRange: true`. Read-only evidence.
- `backend/app/core/html_sanitize.py:40-47,122-137` -- token-API sanitizer; allows `rel`, only appends `noopener/noreferrer` for `target="_blank"`, never forces nofollow. Read-only — confirms backend is not the cause.
- `backend/app/routers/campaigns.py:44-53` -- in-app save sanitizer (nh3, `link_rel=None`, `rel` allowed); preserves rel. Read-only — confirms save path is not the cause.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/components/campaigns/BlogEditor.tsx` -- in `handleLinkConfirm` (line 284), insert `.extendMarkRange("link")` into the chain before `.setLink({...})`, i.e. `editor.chain().focus().extendMarkRange("link").setLink({...}).run()` -- so editing an existing link on a collapsed cursor rewrites the whole link's attributes instead of no-op'ing into stored marks.
- [x] `frontend/__tests__/components/BlogEditor.test.tsx` -- add `extendMarkRange` to the mocked chain and add regression tests covering the matrix rows (edit existing nofollow link → dofollow, edit no-rel token-API link → dofollow, flip dofollow → nofollow), asserting `extendMarkRange("link")` is called before `setLink`. Also fixed two pre-existing stale nofollow assertions (missing `target: "_blank"` from the earlier done target-blank fix) and the mocked `isActive` param typing (removed 3 pre-existing tsc errors) so the suite is green.
- [x] `frontend/__tests__/components/BlogEditorLinkMark.test.ts` -- (added during review to close the verification-gap finding) real, unmocked TipTap `Editor` test that observes the serialized `rel`/`target` in `getHTML()` after a collapsed-cursor rewrite, with a negative control proving the bug reproduces without `extendMarkRange`. Guards against a regression that keeps the command chain but stops persisting the flipped `rel`.

**Acceptance Criteria:**
- Given a token-API-published article open in the editor with a link that has no `rel`, when the user places the cursor inside the link (no text selected), opens the link dialog, selects Dofollow, and clicks Update link, then the link's `rel` becomes `noopener noreferrer` and reopening the dialog shows Dofollow selected.
- Given the same edit, when the user saves and the article is reloaded, then the link remains Dofollow (persisted through the backend and re-read).
- Given a Dofollow link, when the user flips it to Nofollow with a collapsed cursor, then `rel` becomes `nofollow noopener noreferrer` and reopening shows Nofollow.
- Given a fresh text selection with no existing link, when the user inserts a link, then behavior is unchanged from before the fix (link created over the selection with the chosen type).

## Design Notes

Root cause is a TipTap API asymmetry, not a sanitizer bug. `setLink` → `setMark`; on a collapsed selection `setMark` only updates *stored marks* (next-typed-character), leaving the existing link untouched. `extendMarkRange("link")` selects the full contiguous link mark first so `setMark` rewrites it. With a real text selection this is a no-op-safe addition (extends to mark bounds if a link mark is present, otherwise leaves the selection as-is), so link insertion is unaffected.

The token-API path is where users notice it because markdown-rendered links arrive as `<a href>` with no `rel`, and `openLinkDialog` (line 274) renders any no-`rel` link as "Nofollow". After this fix the toggle works regardless of source.

## Verification

**Commands:**
- `cd frontend && npx tsc --noEmit` -- expected: no new type errors.
- `cd frontend && npm run lint` -- expected: clean (no new warnings in `BlogEditor.tsx`).

**Manual checks:**
- Publish an article via the token API (link with no rel), open it in the blog editor, click into the link, open the link dialog, switch to Dofollow, Update, then Save. Reload the campaign and reopen the link dialog: it must show Dofollow, and the stored `blog_html` must contain `rel="noopener noreferrer"` (no `nofollow`).

## Suggested Review Order

**The fix**

- Entry point: `extendMarkRange("link")` prepended to the chain so a collapsed-cursor edit rewrites the whole link mark instead of only setting stored marks.
  [`BlogEditor.tsx:284`](../../frontend/components/campaigns/BlogEditor.tsx#L284)

- Why the symptom is token-API-specific: no-`rel` links are shown as Nofollow, so the flip-to-Dofollow appeared to do nothing. Unchanged; read for context.
  [`BlogEditor.tsx:274`](../../frontend/components/campaigns/BlogEditor.tsx#L274)

**Verification (tests)**

- Real, unmocked editor test — negative control reproduces the bug; the fix drops `nofollow` from serialized HTML. Closes the mock-only verification gap.
  [`BlogEditorLinkMark.test.ts:43`](../../frontend/__tests__/components/BlogEditorLinkMark.test.ts#L43)

- Mock-chain regression: asserts `extendMarkRange("link")` is dispatched before `setLink` when editing an existing link.
  [`BlogEditor.test.tsx:337`](../../frontend/__tests__/components/BlogEditor.test.tsx#L337)

- Mocked chain gains `extendMarkRange`; also fixes two stale nofollow assertions and the `isActive` mock typing.
  [`BlogEditor.test.tsx:12`](../../frontend/__tests__/components/BlogEditor.test.tsx#L12)
