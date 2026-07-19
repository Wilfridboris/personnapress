---
baseline_commit: a702acc023e2c17e006abd29d6f9fd7eea566349
---

# Story 4.5: Blog Editor Link Rel Control

Status: done

## Story

As an authenticated user editing a blog post,
I want to choose whether each link is dofollow or nofollow when inserting or editing links,
so that I can control which outbound links pass SEO ranking authority to external pages.

## Acceptance Criteria

1. **Given** the blog editor toolbar in edit mode, **When** the user clicks the Link2 icon button, **Then** a modal dialog opens with a URL input field and a two-option segmented toggle: "Nofollow" (selected by default) / "Dofollow".

2. **Given** the link modal is open with "Nofollow" selected, **When** the user enters a valid URL and confirms, **Then** `editor.chain().focus().setLink({ href: url.trim(), rel: "nofollow noopener noreferrer" }).run()` is called.

3. **Given** the link modal is open with "Dofollow" selected, **When** the user enters a valid URL and confirms, **Then** `editor.chain().focus().setLink({ href: url.trim(), rel: "noopener noreferrer" }).run()` is called.

4. **Given** the cursor is positioned within an existing link, **When** the user clicks the Link2 toolbar button, **Then** the modal opens pre-populated with the link's current `href` and with the "Nofollow" / "Dofollow" toggle reflecting the existing `rel` value (nofollow selected if `rel` contains "nofollow" or is absent; dofollow selected if `rel` is exactly "noopener noreferrer").

5. **Given** the link modal is open while editing an existing link, **When** the user clicks "Remove link", **Then** `editor.chain().focus().unsetLink().run()` is called and the modal closes.

6. **Given** the link modal is open, **When** the URL field is empty or does not start with `http://`, `https://`, `mailto:`, `/`, `#`, `./`, or `../`, **Then** the confirm button is disabled.

7. **Given** the link modal URL field is focused and contains a valid URL, **When** the user presses Enter, **Then** the link is confirmed (same as clicking the confirm button).

8. **Given** the Link2 toolbar button, **When** the cursor is within a link node, **Then** the button renders with `bg-highlighter` background (active state), matching all other toolbar button active states.

9. **Given** the backend sanitizers, **When** HTML with `rel="nofollow noopener noreferrer"` or `rel="noopener noreferrer"` on `<a>` tags is received, **Then** the `rel` attribute is preserved as-is — no backend changes are needed (already confirmed: both `campaigns.py` and `articles.py` allowlists include `"rel"` for `<a>` tags; `_DOMPURIFY_CONFIG` in BlogEditor.tsx also includes `"rel"` in `ALLOWED_ATTR`).

## Tasks / Subtasks

- [x] Task 1: Add `LinkDialogState` type, constant, and URL validator to `BlogEditor.tsx` (AC: #1, #6)
  - [x] 1.1 Add module-level `isValidLinkUrl` helper alongside `_DOMPURIFY_CONFIG`:
    ```typescript
    const _SAFE_URL_PREFIXES = ["http://", "https://", "mailto:", "/", "#", "./", "../"];
    function isValidLinkUrl(url: string): boolean {
      const t = url.trim();
      return t.length > 0 && _SAFE_URL_PREFIXES.some((p) => t.startsWith(p));
    }
    ```
  - [x] 1.2 Add inside the component (alongside `ImageDialogState`):
    ```typescript
    interface LinkDialogState {
      open: boolean;
      url: string;
      nofollow: boolean;
    }
    const CLOSED_LINK_DIALOG: LinkDialogState = { open: false, url: "", nofollow: true };
    ```

- [x] Task 2: Add link dialog state and handlers inside `BlogEditor` (AC: #1–#5, #7)
  - [x] 2.1 Add ref and state inside the component body (alongside the image refs and dialog state):
    ```typescript
    const linkUrlInputRef = useRef<HTMLInputElement>(null);
    const [linkDialog, setLinkDialog] = useState<LinkDialogState>(CLOSED_LINK_DIALOG);
    ```
  - [x] 2.2 Add `openLinkDialog` callback — reads current link attributes when cursor is on a link:
    ```typescript
    const openLinkDialog = useCallback(() => {
      if (!editor) return;
      const attrs = editor.getAttributes("link");
      const currentRel = (attrs.rel as string | undefined) ?? "";
      setLinkDialog({
        open: true,
        url: (attrs.href as string | undefined) ?? "",
        nofollow: !currentRel || currentRel.includes("nofollow"),
      });
    }, [editor]);
    ```
  - [x] 2.3 Add `closeLinkDialog` callback:
    ```typescript
    const closeLinkDialog = useCallback(() => {
      setLinkDialog(CLOSED_LINK_DIALOG);
    }, []);
    ```
  - [x] 2.4 Add `handleLinkConfirm` callback:
    ```typescript
    const handleLinkConfirm = useCallback(() => {
      if (!editor || !isValidLinkUrl(linkDialog.url)) return;
      editor.chain().focus().setLink({
        href: linkDialog.url.trim(),
        rel: linkDialog.nofollow ? "nofollow noopener noreferrer" : "noopener noreferrer",
      }).run();
      closeLinkDialog();
    }, [editor, linkDialog, closeLinkDialog]);
    ```

- [x] Task 3: Replace `window.prompt` toolbar link button with modal-triggering button (AC: #1, #4, #8)
  - [x] 3.1 In the toolbar JSX (currently lines 273–289 of `BlogEditor.tsx`), replace the existing link button block:
    ```tsx
    // REMOVE THIS:
    <button
      type="button"
      aria-label="Set link"
      onClick={() => {
        const url = window.prompt("URL:");
        if (url) {
          editor.chain().focus().setLink({ href: url }).run();
        } else {
          editor.chain().focus().unsetLink().run();
        }
      }}
      className={cn(
        "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
        editor.isActive("link") && "bg-highlighter",
      )}
    >
      <Link2 size={16} aria-hidden="true" />
    </button>

    // REPLACE WITH:
    <button
      type="button"
      aria-label="Insert or edit link"
      onClick={openLinkDialog}
      className={cn(
        "p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink",
        editor.isActive("link") && "bg-highlighter",
      )}
    >
      <Link2 size={16} aria-hidden="true" />
    </button>
    ```

- [x] Task 4: Add link modal JSX to the component return (AC: #1–#7)
  - [x] 4.1 Add a second `<Modal>` below the existing image `<Modal>` (before the closing `</div>`):
    ```tsx
    <Modal
      isOpen={linkDialog.open}
      onClose={closeLinkDialog}
      title={editor?.isActive("link") ? "Edit link" : "Insert link"}
      initialFocusRef={linkUrlInputRef}
    >
      <div className="space-y-4">
        {/* URL field */}
        <div className="space-y-1.5">
          <label
            htmlFor="link-url"
            className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
          >
            URL
          </label>
          <input
            ref={linkUrlInputRef}
            id="link-url"
            type="url"
            value={linkDialog.url}
            onChange={(e) => setLinkDialog((d) => ({ ...d, url: e.target.value }))}
            onKeyDown={(e) => {
              if (e.key === "Enter" && isValidLinkUrl(linkDialog.url)) handleLinkConfirm();
            }}
            placeholder="https://example.com"
            className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
          />
        </div>

        {/* Nofollow / Dofollow segmented toggle */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
            Link type
          </span>
          <div className="flex border border-[#E5E5E5]" role="group" aria-label="Link type">
            <button
              type="button"
              aria-pressed={linkDialog.nofollow}
              onClick={() => setLinkDialog((d) => ({ ...d, nofollow: true }))}
              className={cn(
                "flex-1 py-2 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
                linkDialog.nofollow
                  ? "bg-[#111111] text-white"
                  : "text-[#555555] hover:text-[#111111]",
              )}
            >
              Nofollow
            </button>
            <button
              type="button"
              aria-pressed={!linkDialog.nofollow}
              onClick={() => setLinkDialog((d) => ({ ...d, nofollow: false }))}
              className={cn(
                "flex-1 py-2 text-sm font-medium border-l border-[#E5E5E5] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
                !linkDialog.nofollow
                  ? "bg-[#111111] text-white"
                  : "text-[#555555] hover:text-[#111111]",
              )}
            >
              Dofollow
            </button>
          </div>
          <p className="text-[11px] text-[#999999]">
            {linkDialog.nofollow
              ? "Does not pass SEO ranking authority to the linked page."
              : "Passes SEO ranking authority to the linked page."}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          {editor?.isActive("link") && (
            <button
              type="button"
              onClick={() => {
                editor.chain().focus().unsetLink().run();
                closeLinkDialog();
              }}
              className="px-3 py-2 text-sm font-medium text-[#555555] hover:text-[#111111] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 min-h-[44px]"
            >
              Remove link
            </button>
          )}
          <div
            className={cn(
              "flex items-center gap-3",
              !editor?.isActive("link") && "ml-auto",
            )}
          >
            <button
              type="button"
              onClick={closeLinkDialog}
              className="px-4 py-2 text-sm font-medium text-[#555555] hover:text-[#111111] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 min-h-[44px]"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleLinkConfirm}
              disabled={!isValidLinkUrl(linkDialog.url)}
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 bg-[#111111] text-white text-sm font-medium",
                "shadow-[4px_4px_0px_0px_#111111] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all",
                "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
                "disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed min-h-[44px]",
              )}
            >
              {editor?.isActive("link") ? "Update link" : "Insert link"}
            </button>
          </div>
        </div>
      </div>
    </Modal>
    ```

- [x] Task 5: Add tests to `BlogEditor.test.tsx` (AC: #1–#8)
  - [x] 5.1 Add `getAttributes` to `mockEditor` (needed for pre-populate test):
    ```typescript
    const mockEditor = {
      ...existing fields...
      getAttributes: vi.fn(() => ({})),
    };
    ```
  - [x] 5.2 Test: clicking Link2 toolbar button opens the link modal (modal with title "Insert link" appears; no existing link active)
  - [x] 5.3 Test: confirming with a valid URL and Nofollow (default) calls `setLink` with `rel: "nofollow noopener noreferrer"`
  - [x] 5.4 Test: switching to Dofollow and confirming calls `setLink` with `rel: "noopener noreferrer"`
  - [x] 5.5 Test: when `editor.isActive("link")` is true and `getAttributes("link")` returns `{ href: "https://x.com", rel: "nofollow noopener noreferrer" }`, opening the dialog pre-populates URL field and selects Nofollow
  - [x] 5.6 Test: when editing existing link, "Remove link" button is visible; clicking it calls `unsetLink`
  - [x] 5.7 Test: confirm button is disabled when URL is empty or starts with `javascript:`
  - [x] 5.8 Test: confirm button is enabled when URL starts with `https://`

## Dev Notes

### The only file that changes in production code is `BlogEditor.tsx`

This is a **frontend-only change**. No backend modifications. No new packages.

- `frontend/components/campaigns/BlogEditor.tsx` — only file with production code changes
- `frontend/__tests__/components/BlogEditor.test.tsx` — test additions only

### Why no backend changes

Both backend sanitizers already preserve `rel` on `<a>` tags:
- `backend/app/routers/campaigns.py:26` — `_ALLOWED_HTML_ATTRS = {"a": {"href", "title", "rel"}, ...}` with `link_rel=None` (nh3 will not override or strip the rel value we set)
- `backend/app/routers/articles.py:49` — `_ALLOWED_ATTRS = {"a": ["href", "title", "rel"], ...}` (BeautifulSoup preserves it)
- `BlogEditor.tsx:32` — `_DOMPURIFY_CONFIG.ALLOWED_ATTR` already includes `"rel"`

### TipTap v3 `rel` attribute is tracked as a mark attribute

In `@tiptap/extension-link` v3, `rel` is a first-class mark attribute alongside `href` and `target`. This means:
- `editor.getAttributes("link")` returns `{ href, rel, target, class }` for an active link
- `editor.chain().focus().setLink({ href, rel })` correctly stores `rel` on the mark
- `editor.getHTML()` serializes `rel` into the `<a>` tag output
- `editor.commands.unsetLink()` removes the entire mark including `rel`

**DO NOT** try to extend the Link extension with a custom attribute — it is already built in.

### Current link button location in BlogEditor.tsx

The `window.prompt` link button is at lines **273–289** in the toolbar JSX. Replace the entire button block. Do not touch any surrounding buttons.

### StarterKit link configuration — leave unchanged

The current StarterKit link config in `useEditor`:
```typescript
StarterKit.configure({
  horizontalRule: false,
  strike: false,
  link: { openOnClick: false, HTMLAttributes: { class: "underline" } },
}),
```
Do NOT change this. The `HTMLAttributes: { class: "underline" }` sets the CSS class; `rel` is handled per-link via `setLink()`, not as a default HTML attribute. If you set `rel` in `HTMLAttributes` here, it would override the per-link value and break the feature.

### `CLOSED_LINK_DIALOG` placement

Declare `CLOSED_LINK_DIALOG` as a module-level constant (alongside `CLOSED_DIALOG` for images), not inside the component — same pattern as the image dialog:
```typescript
// Module level, alongside CLOSED_DIALOG
const CLOSED_LINK_DIALOG: LinkDialogState = { open: false, url: "", nofollow: true };
```

### `openLinkDialog` must use `useCallback` with `[editor]` dependency

`editor` can be null on the first render tick. The callback guards with `if (!editor) return;`. Dependency is just `[editor]`.

### `handleLinkConfirm` dependency array

```typescript
}, [editor, linkDialog, closeLinkDialog]);
```
`closeLinkDialog` is stable (no deps), `linkDialog` is the full state object (needed for `url` and `nofollow`).

### Modal `initialFocusRef` pattern

The existing image modal uses `initialFocusRef={altInputRef}` to move focus to the first input on open. Do the same with `initialFocusRef={linkUrlInputRef}`. This matches the `Modal` component's `useEffect` focus logic in `components/ui/Modal.tsx:45`.

### "Remove link" button — conditional on active link

The "Remove link" button on the left of the action row only appears when `editor?.isActive("link")` is true. The `ml-auto` on the right button group shifts it to the far right when "Remove link" is absent — matching the Cancel+Confirm right-aligned pattern in the image dialog.

### No `type="url"` validation side-effects

The URL input uses `type="url"` for semantics, but the confirm button's disabled state is driven by the `isValidLinkUrl()` helper, not browser URL validation. Browser validation can reject valid relative paths (`/page`, `#anchor`) that we want to allow — so always rely on `isValidLinkUrl`, not `input.validity.valid`.

### `article-editor.tsx` gets this feature for free

`frontend/app/(app)/blog/[id]/article-editor.tsx` imports `BlogEditor` directly:
```typescript
import { BlogEditor, BlogEditorHandle, _DOMPURIFY_CONFIG } from "@/components/campaigns/BlogEditor";
```
No changes needed there — the link modal will appear in both the campaign editor and the article editor.

### Test mock additions needed

The existing `mockEditor` in `BlogEditor.test.tsx` is missing `getAttributes`. Add it before the new tests:
```typescript
const mockEditor = {
  ...
  getAttributes: vi.fn(() => ({})),  // ADD THIS
};
```
For the "edit existing link" test, configure it to return link attrs:
```typescript
mockEditor.isActive.mockImplementation((type) => type === "link");
mockEditor.getAttributes.mockReturnValue({ href: "https://x.com", rel: "nofollow noopener noreferrer" });
```

### Design System Compliance

- Segmented toggle: two adjacent buttons with outer `border border-[#E5E5E5]`, divider `border-l border-[#E5E5E5]`, selected = `bg-[#111111] text-white`, unselected = `text-[#555555] hover:text-[#111111]`
- Labels: `text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]`
- Inputs: `border-b border-[#E5E5E5] focus:border-[#111111]` (no box border)
- Action buttons: `min-h-[44px]` (44px touch target minimum)
- Confirm button: `shadow-[4px_4px_0px_0px_#111111] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none` (Paper brutal shadow)
- No Framer Motion — Modal already uses `animate-fade-in-up` CSS animation

### References

- Existing BlogEditor (full current source): `frontend/components/campaigns/BlogEditor.tsx`
- Existing BlogEditor tests (mock patterns): `frontend/__tests__/components/BlogEditor.test.tsx`
- Modal component (initialFocusRef, focus trap): `frontend/components/ui/Modal.tsx`
- Backend campaigns sanitizer (rel already allowed): `backend/app/routers/campaigns.py:26`
- Backend articles sanitizer (rel already allowed): `backend/app/routers/articles.py:49`
- Story 4.2 dev notes (TipTap patterns, Link extension, StarterKit config): `_bmad-output/implementation-artifacts/4-2-blog-post-wysiwyg-editing.md`

### Review Findings

- [x] [Review][Patch] Stale `editor?.isActive("link")` in modal JSX — replace 4 occurrences with `editorState?.isLink` [BlogEditor.tsx:533,598,613,634]
- [x] [Review][Patch] `onKeyDown` stale closure URL — use `e.currentTarget.value` instead of `linkDialog.url` [BlogEditor.tsx:551]
- [x] [Review][Patch] Missing test: dofollow pre-population (existing link with `rel="noopener noreferrer"` should set Dofollow aria-pressed) [BlogEditor.test.tsx]
- [x] [Review][Patch] Missing test: Nofollow selected by default when modal opens on new link [BlogEditor.test.tsx]
- [x] [Review][Patch] Missing tests: `mailto:`, `/`, `#` URL prefix validation (AC 6) [BlogEditor.test.tsx]
- [x] [Review][Patch] Missing test: Enter key submits form when URL is valid [BlogEditor.test.tsx]
- [x] [Review][Defer] `can().undo()` in `useEditorState` selector creates temporary transaction on every state update [BlogEditor.tsx:157] — deferred, pre-existing Tiptap pattern
- [x] [Review][Defer] `handleLinkConfirm` useCallback recreated on every URL keystroke (`linkDialog` in deps) [BlogEditor.tsx:264] — deferred, non-issue (not passed to memoized children)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `isValidLinkUrl` helper (module-level) allowing `http://`, `https://`, `mailto:`, `/`, `#`, `./`, `../` prefixes; blocks `javascript:` and empty strings.
- Added `LinkDialogState` interface and `CLOSED_LINK_DIALOG` constant at module level alongside the existing image dialog pattern.
- Added `linkUrlInputRef`, `linkDialog` state, `openLinkDialog`, `closeLinkDialog`, and `handleLinkConfirm` callbacks inside the component.
- Replaced the `window.prompt` link button with `openLinkDialog` handler; button label updated to "Insert or edit link".
- Added full link modal JSX (URL input, Nofollow/Dofollow segmented toggle, Remove link / Cancel / confirm actions) below the existing image modal.
- Added `useEditorState` to the `@tiptap/react` mock (pre-existing omission caught by tests) plus `getAttributes` to `mockEditor`.
- Added 8 new tests covering: modal open, nofollow confirm, dofollow confirm, pre-populate existing link, remove link, disabled on empty URL, disabled on javascript: URL, enabled on valid https URL.
- All 18 BlogEditor tests pass; 16 failures in other test files are pre-existing and unrelated.

### File List

- `frontend/components/campaigns/BlogEditor.tsx`
- `frontend/__tests__/components/BlogEditor.test.tsx`

### Change Log

- 2026-07-18: Implemented story 4.5 — replaced window.prompt link insert with modal dialog featuring Nofollow/Dofollow toggle and URL validation; added 8 tests.
