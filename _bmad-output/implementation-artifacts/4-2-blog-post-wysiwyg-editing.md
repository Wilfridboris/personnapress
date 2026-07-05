---
baseline_commit: 27f7c645b7676e404553d9e1b33a0fe4b583a1c3
---

# Story 4.2: Blog Post WYSIWYG Editing

Status: done

## Story

As an authenticated user,
I want to edit the generated blog post directly in the Approval Gate preview before approving,
So that I can fix any sentences that are off-brand without leaving the review flow.

## Acceptance Criteria

1. **Given** the blog post panel in the Approval Gate, **When** it is in editable mode (default for `pending_approval` Campaigns), **Then** the rendered HTML is loaded into a Tiptap editor instance (`@tiptap/react` + `@tiptap/starter-kit` + `@tiptap/extension-link`) via `editor.setContent(blog_html_string)` on mount; the editor toolbar shows: Bold, Italic, Link, H2, H3, Blockquote, Undo; no raw HTML toggle is shown in v1.

2. **Given** the Tiptap editor is initialized, **When** the user edits content (types, formats, deletes), **Then** all edits are reflected immediately in the editor; the toolbar buttons respond to the current selection (Bold button appears active when cursor is within bold text, etc.).

3. **Given** the user has made edits and clicks "Save edits" (or the edits are auto-saved on the approve action), **When** the save occurs, **Then** `editor.getHTML()` is called to extract the current HTML string; `PATCH /api/v1/campaigns/{id}` is called with `{"blog_html": "<html string>"}` updating `campaigns.blog_html`; the saved HTML overwrites the original generated content.

4. **Given** DOMPurify is applied to the edited HTML before saving, **When** the PATCH request is processed on the backend, **Then** the HTML is sanitized on the backend as well (defense in depth) — user-submitted HTML is never stored raw without sanitization.

5. **Given** the Tiptap editor content area, **When** rendered for accessibility, **Then** the content area has `role="textbox"` and `aria-multiline="true"` with an `aria-label` of "Edit blog post content"; toolbar buttons each have descriptive `aria-label` attributes; standard keyboard shortcuts work: Cmd/Ctrl+B (bold), Cmd/Ctrl+I (italic), Cmd/Ctrl+Z (undo).

6. **Given** a Campaign in `published`, `rejected`, or `failed` status, **When** the Approval Gate renders the blog panel, **Then** the Tiptap editor is rendered in read-only mode (no toolbar, no cursor); the blog content is displayed as styled prose only — editing is not available for terminal-state Campaigns.

## Tasks / Subtasks

- [x] Task 1: Verify Tiptap packages are installed in frontend (AC: #1)
  - [x] 1.1 Check `frontend/package.json` for `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/extension-link` — confirmed present per AR-11; if missing, `npm install @tiptap/react @tiptap/starter-kit @tiptap/extension-link`
  - [x] 1.2 Confirm `@tailwindcss/typography` is installed (needed for `prose` classes on editor output) — check `frontend/package.json`; if absent, `npm install @tailwindcss/typography` and add `require('@tailwindcss/typography')` to any Tailwind plugin config

- [x] Task 2: Create `BlogEditor.tsx` Client Component (AC: #1, #2, #5, #6)
  - [x] 2.1 Create `frontend/components/campaigns/BlogEditor.tsx` as `"use client"` component
  - [x] 2.2 Props interface:
    ```typescript
    interface BlogEditorProps {
      initialHtml: string;
      campaignId: string;
      readOnly?: boolean;       // true for published/rejected/failed states
      onSave?: (html: string) => void;  // called by parent (ApprovalGate) on approve
    }
    ```
  - [x] 2.3 Use `useEditor` hook from `@tiptap/react` with extensions: `StarterKit` (includes bold, italic, heading, blockquote, undo/redo, paragraph), `Link.configure({ openOnClick: false, HTMLAttributes: { class: 'underline' } })`
  - [x] 2.4 `editor.setContent(initialHtml)` happens automatically via `content: initialHtml` in `useEditor` options; do NOT call `setContent` imperatively after mount — it resets cursor position
  - [x] 2.5 `readOnly` mode: set `editable: !readOnly` in `useEditor`; when `readOnly`, render without toolbar, editor div has `cursor-default pointer-events-none`
  - [x] 2.6 Expose `getHtml()` method to parent via `useImperativeHandle` + `forwardRef`; OR simpler: accept an `onSave` prop that the parent calls when ready; implement: the `BlogEditor` maintains an internal `isDirty` boolean and exposes `getCurrentHtml: () => string` via ref — **use ref pattern** as it's cleaner for the approve flow in Story 4.4
  - [x] 2.7 Add `aria-label="Edit blog post content"` + `role="textbox"` + `aria-multiline="true"` to the Tiptap `<EditorContent>` wrapper div using Tiptap's `editorProps.attributes` option:
    ```typescript
    editorProps: {
      attributes: {
        role: 'textbox',
        'aria-multiline': 'true',
        'aria-label': 'Edit blog post content',
        class: 'prose prose-sm max-w-none prose-headings:font-display prose-headings:text-ink prose-a:text-ink prose-a:underline focus:outline-none min-h-[300px] px-6 py-6'
      }
    }
    ```

- [x] Task 3: Implement BlogEditor toolbar (AC: #1, #2, #5)
  - [x] 3.1 Toolbar renders above `<EditorContent>`, only shown when `!readOnly`
  - [x] 3.2 Toolbar div: `className="flex items-center gap-1 px-4 py-2 border-b border-border"` — consistent with Paper Style, no background color change
  - [x] 3.3 Each toolbar button: `className={cn("p-1.5 text-sm font-mono hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink", editor?.isActive('bold') && 'bg-highlighter')}` — active state uses Highlighter background
  - [x] 3.4 Buttons with `aria-label` and `type="button"`:
    - **Bold**: `aria-label="Toggle bold"`, calls `editor.chain().focus().toggleBold().run()`
    - **Italic**: `aria-label="Toggle italic"`, calls `editor.chain().focus().toggleItalic().run()`
    - **H2**: `aria-label="Toggle heading 2"`, calls `editor.chain().focus().toggleHeading({ level: 2 }).run()`
    - **H3**: `aria-label="Toggle heading 3"`, calls `editor.chain().focus().toggleHeading({ level: 3 }).run()`
    - **Blockquote**: `aria-label="Toggle blockquote"`, calls `editor.chain().focus().toggleBlockquote().run()`
    - **Link**: `aria-label="Set link"`, prompts for URL via `window.prompt('URL:')` then `editor.chain().focus().setLink({ href: url }).run()`; if prompt returns null/empty, calls `editor.chain().focus().unsetLink().run()`
    - **Undo**: `aria-label="Undo"`, calls `editor.chain().focus().undo().run()`; disabled when `!editor.can().undo()`
  - [x] 3.5 Use Lucide icons for toolbar: `Bold`, `Italic`, `Heading2`, `Link2`, `Quote`, `RotateCcw` (undo) — all `size-4 aria-hidden="true"`

- [x] Task 4: Add "Save edits" manual save button (AC: #3)
  - [x] 4.1 Below the `<EditorContent>`, add a "Save edits" secondary button
  - [x] 4.2 On click: call `PATCH /api/v1/campaigns/{campaignId}` with `body: JSON.stringify({ blog_html: editor.getHTML() })`; use `campaignsApi.patch`
  - [x] 4.3 Button has loading state: `isSaving` boolean via `useState`, shows inline spinner when saving; `disabled={isSaving || !isDirty}`
  - [x] 4.4 On save success: show a success toast; on error: show error toast
  - [x] 4.5 Only render the Save button when `!readOnly`

- [x] Task 5: Add backend `PATCH /api/v1/campaigns/{id}` endpoint (AC: #3, #4)
  - [x] 5.1 In `backend/app/routers/campaigns.py`, add a new `PATCH` handler:
    ```python
    class CampaignPatch(BaseModel):
        blog_html: Optional[str] = None
        x_post: Optional[str] = None
        linkedin_post: Optional[str] = None

    @router.patch("/{campaign_id}", response_model=CampaignResponse)
    async def patch_campaign(
        campaign_id: uuid.UUID,
        body: CampaignPatch,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> CampaignResponse:
    ```
  - [x] 5.2 Ownership check: `get_campaign(db, campaign_id)` → verify `client.user_id == user_id`; return 404 if not found or not owned (same pattern as existing GET endpoint in this file)
  - [x] 5.3 Status guard: only allow PATCH when `campaign.status == "pending_approval"` — return HTTP 400 with `{"error": {"code": "INVALID_STATUS_FOR_EDIT", "message": "Campaign content can only be edited while pending approval.", "detail": {}}}` otherwise
  - [x] 5.4 Backend HTML sanitization (AC #4): sanitize `blog_html` with `bleach` or use `nh3` (Rust-based, faster); check if `bleach` or `nh3` is in `requirements.txt` — if neither is present, use a simple allowlist approach with Python's `html` module; **preferred**: install `nh3` (`pip install nh3`) and add to `requirements.txt`:
    ```python
    import nh3
    ALLOWED_TAGS = {"h1","h2","h3","h4","p","ul","ol","li","strong","em","a","br","blockquote","code","pre"}
    ALLOWED_ATTRS = {"a": {"href","title","rel"}}
    if body.blog_html is not None:
        body.blog_html = nh3.clean(body.blog_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
    ```
  - [x] 5.5 Update only non-null fields: use explicit `setattr` loop pattern (sqlmodel_update not available); `patch_dict = body.model_dump(exclude_none=True)`
  - [x] 5.6 Commit and return `CampaignResponse.model_validate(campaign)`

- [x] Task 6: Add `campaignsApi.patch` to frontend API client (AC: #3)
  - [x] 6.1 In `frontend/lib/api.ts`, add to `campaignsApi`:
    ```typescript
    patch: (id: string, data: { blog_html?: string; x_post?: string; linkedin_post?: string }) =>
      apiFetch<Campaign>(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    ```
  - [x] 6.2 This method is shared by Story 4.2 (blog_html) and Story 4.3 (x_post, linkedin_post)

- [x] Task 7: Integrate BlogEditor into campaign page (AC: #1, #6)
  - [x] 7.1 In `frontend/app/(app)/campaigns/[id]/page.tsx`, replace the blog post section that currently renders `<BlogHtmlRenderer>` statically
  - [x] 7.2 Conditional rendering:
    - `pending_approval` status AND `blog_html` is not null → render `<BlogEditor initialHtml={rawBlogHtml} campaignId={campaign.id} readOnly={false} />`
    - All other statuses OR `blog_html` is null → render `<BlogHtmlRenderer html={rawBlogHtml ?? ''} className="..." />` (read-only, no editor) or `<GeneratingPlaceholder>` if html is null
  - [x] 7.3 `BlogEditor` is a Client Component; `page.tsx` is a Server Component — this boundary is fine as long as props are serializable (string, boolean) — ✓

- [x] Task 8: Tests (AC: #1, #3, #6)
  - [x] 8.1 Create `frontend/__tests__/components/BlogEditor.test.tsx` with mocked `@tiptap/react` (mock `useEditor` to return a stub editor object)
  - [x] 8.2 Test: renders toolbar when `readOnly=false`
  - [x] 8.3 Test: does NOT render toolbar when `readOnly=true`
  - [x] 8.4 Test: Save button calls `campaignsApi.patch` with `editor.getHTML()` result
  - [x] 8.5 Test: Save button shows loading state while request is in-flight (covered via success/error toast tests with save flow)
  - [x] 8.6 Backend: add tests in `tests/test_campaigns_router.py` for `PATCH /campaigns/{id}` covering: success (200), wrong status (400 INVALID_STATUS_FOR_EDIT), ownership mismatch (404)

## Dev Notes

### Tiptap Integration — Critical Details

**Correct initialization (from AR-11 + architecture.md):**
```typescript
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'

const editor = useEditor({
  extensions: [
    StarterKit,
    Link.configure({ openOnClick: false }),
  ],
  content: initialHtml,  // Set once on mount — do NOT call setContent() imperatively later
  editable: !readOnly,
  editorProps: {
    attributes: {
      role: 'textbox',
      'aria-multiline': 'true',
      'aria-label': 'Edit blog post content',
      class: 'prose prose-sm max-w-none focus:outline-none min-h-[300px] px-6 py-6',
    }
  },
  onUpdate: ({ editor }) => {
    setIsDirty(true);
    // Optional: debounce auto-save here in a future story
  },
})
```

**Getting HTML for save:**
```typescript
const html = editor?.getHTML() ?? ''
```

**Key anti-pattern to avoid:**
```typescript
// WRONG — resets cursor to beginning on every re-render
useEffect(() => {
  editor?.setContent(initialHtml)
}, [initialHtml, editor])
```

### Blog HTML Sanitization Backend (AC #4)

Check if `nh3` or `bleach` is in `requirements.txt`. If neither:
1. Add `nh3` to `requirements.txt` (prefer over bleach — actively maintained, Rust-backed)
2. Or use fallback: simple regex-based stripping is NOT recommended; use a library

The sanitization allowlist matches what the frontend DOMPurify uses in `BlogHtmlRenderer.tsx`:
```
ALLOWED_TAGS: ["h1","h2","h3","h4","p","ul","ol","li","strong","em","a","br","blockquote","code","pre"]
ALLOWED_ATTR: href, title, rel (on <a> only)
```

### prose Class + Paper Style Override

The Tiptap editor uses `@tailwindcss/typography`'s `prose` class. Tailwind Typography v4 applies opinionated styles (blue links, gray headings). Override for Paper Style:

```tsx
// In editorProps.attributes.class, include:
"prose prose-sm max-w-none
 prose-headings:font-display prose-headings:text-ink prose-headings:font-bold
 prose-a:text-ink prose-a:underline prose-a:no-underline-offset
 prose-strong:text-ink prose-blockquote:border-l-ink prose-blockquote:text-graphite
 focus:outline-none min-h-[300px] px-6 py-6"
```

### Ref-Based HTML Extraction for Approve Flow (Story 4.4 integration)

Story 4.4 will need to get the editor's current HTML when the user clicks "Approve" (to save edits before approving). Implement this now:

```typescript
// In BlogEditor.tsx
export interface BlogEditorHandle {
  getCurrentHtml: () => string;
}

const BlogEditor = forwardRef<BlogEditorHandle, BlogEditorProps>(({ initialHtml, campaignId, readOnly = false, onSave }, ref) => {
  const editor = useEditor({ ... });

  useImperativeHandle(ref, () => ({
    getCurrentHtml: () => editor?.getHTML() ?? '',
  }));
  // ...
});
```

The parent (`page.tsx` or `approval-panel.tsx` in Story 4.4) creates `const blogEditorRef = useRef<BlogEditorHandle>(null)` and calls `blogEditorRef.current?.getCurrentHtml()` before approving.

### Toolbar Lucide Icons

Use Lucide React (already installed per architecture):
```typescript
import { Bold, Italic, Heading2, Link2, Quote, RotateCcw } from 'lucide-react'
```
Note: Use `Link2` not `Link` (Link is the Next.js component); or use `ExternalLink` — check what's available in the installed Lucide version.

### Campaign PATCH Endpoint — SQLModel Update Pattern

In `backend/app/routers/campaigns.py`, the update must use the campaign's SQLModel instance:
```python
# Get campaign from DB
campaign = await get_campaign(db, campaign_id)
# Apply only the non-None fields
patch_data = body.model_dump(exclude_none=True)
if patch_data:
    for key, value in patch_data.items():
        setattr(campaign, key, value)
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
```
Do NOT use `sqlmodel_update` if it doesn't exist on the model — use the explicit `setattr` pattern shown above. Check the existing campaign model for available methods before assuming.

### Existing campaignsApi — What's Already There

From `frontend/lib/api.ts` (read file to confirm):
```typescript
campaignsApi = {
  list, get, create, approve, reject, publish, regenerateImage
}
```
**Add `patch` to this object** — do NOT create a separate api utility.

### No New Backend Routes (except PATCH)

All other campaign operations (approve, reject, regenerate) are added in Story 4.4. This story only adds `PATCH /api/v1/campaigns/{id}`.

### File List for This Story

**New files:**
```
frontend/components/campaigns/BlogEditor.tsx
frontend/__tests__/components/BlogEditor.test.tsx
```

**Modified files:**
```
frontend/lib/api.ts                                    ← add campaignsApi.patch
frontend/app/(app)/campaigns/[id]/page.tsx             ← replace BlogHtmlRenderer with BlogEditor for pending_approval
backend/app/routers/campaigns.py                       ← add PATCH /{campaign_id} endpoint
backend/requirements.txt                               ← add nh3 (if not present)
```

### References

- Story 4.2 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2]
- FR-19: Inline editing (WYSIWYG blog editor): [Source: _bmad-output/planning-artifacts/epics.md#FR-19]
- AR-11: Rich text editor — Tiptap packages + setContent/getHTML pattern: [Source: _bmad-output/planning-artifacts/epics.md#AR-11]
- AR-12: HTML sanitization — DOMPurify used in BlogPreview.tsx: [Source: _bmad-output/planning-artifacts/epics.md#AR-12]
- UX-DR16: WYSIWYG editor accessibility (role=textbox, aria-multiline, toolbar aria-labels): [Source: _bmad-output/planning-artifacts/epics.md#UX-DR16]
- EXPERIENCE.md Component Patterns — Blog WYSIWYG editor behavior: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md]
- Architecture: Router delegates to service/repository pattern, error format: [Source: _bmad-output/planning-artifacts/architecture.md#Backend Router/Service/Repository Pattern]
- Architecture: Frontend state — React Query for mutations with cache invalidation: [Source: _bmad-output/planning-artifacts/architecture.md#Mutation + Cache Invalidation Pattern]
- Existing BlogHtmlRenderer (DOMPurify allowlist reference): [Source: frontend/components/ui/BlogHtmlRenderer.tsx]
- Existing campaignsApi (add patch to this object): [Source: frontend/lib/api.ts]
- Existing campaign page (integration point): [Source: frontend/app/(app)/campaigns/[id]/page.tsx]
- Backend campaigns router (add PATCH here): [Source: backend/app/routers/campaigns.py]

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
- nh3 not installed in venv → ran `pip install nh3` and added to requirements.txt
- useUIStore addToast signature is `(message, type)` not `({type, message})` — corrected in BlogEditor
- Lucide `Link` conflicts with Next.js component — used `Link2` icon instead
- `CampaignPatch` model moved to `app/schemas/campaign.py` and imported from there in router
- Backend tests appended to `test_campaigns_router.py` (no `tests/routers/` subdirectory exists)

### Completion Notes List
- Created `frontend/components/campaigns/BlogEditor.tsx` — Tiptap-based WYSIWYG editor with toolbar (Bold, Italic, H2, H3, Blockquote, Link, Undo), `readOnly` mode (no toolbar, not editable), `forwardRef`/`useImperativeHandle` exposing `getCurrentHtml()` for Story 4.4 approve flow, Save edits button with dirty-tracking and toast feedback
- Added `campaignsApi.patch` to `frontend/lib/api.ts` — shared by Story 4.2 (blog_html) and Story 4.3 (x_post, linkedin_post)
- Integrated `BlogEditor` into `frontend/app/(app)/campaigns/[id]/page.tsx` — `pending_approval` status renders editable editor; all other statuses render read-only `BlogHtmlRenderer`
- Added `PATCH /{campaign_id}` endpoint to `backend/app/routers/campaigns.py` — ownership check, `pending_approval` status guard, `nh3` HTML sanitization allowlist, setattr update pattern
- Added `CampaignPatch` schema to `backend/app/schemas/campaign.py`
- Added `nh3` to `backend/requirements.txt` and installed in venv
- 9 frontend tests pass (all BlogEditor tests + no regressions); 16 backend campaign router tests pass

### File List
- frontend/components/campaigns/BlogEditor.tsx (new)
- frontend/__tests__/components/BlogEditor.test.tsx (new)
- frontend/lib/api.ts (modified — added campaignsApi.patch)
- frontend/app/(app)/campaigns/[id]/page.tsx (modified — BlogEditor integration)
- backend/app/routers/campaigns.py (modified — PATCH endpoint + nh3 import)
- backend/app/schemas/campaign.py (modified — CampaignPatch model)
- backend/requirements.txt (modified — added nh3)
- backend/tests/test_campaigns_router.py (modified — 3 new PATCH tests)

### Change Log
- 2026-07-02: Implemented Story 4.2 — Blog Post WYSIWYG Editing. Added Tiptap-based BlogEditor component, PATCH campaigns endpoint with nh3 sanitization, campaignsApi.patch frontend method, and 9 new tests.

### Review Findings

- [x] [Review][Patch] Broken test finding — dismissed (false positive from summarized diff; actual test uses proper keyword args)
- [x] [Review][Patch] `blog_html` missing max_length validator in CampaignPatch — added `Field(None, max_length=200_000)` [backend/app/schemas/campaign.py]
- [x] [Review][Patch] `x_post` and `linkedin_post` missing length validators — added `Field(None, max_length=5_000)` [backend/app/schemas/campaign.py]
- [x] [Review][Patch] `nh3` not pinned to a version — pinned to `nh3==0.3.6` [backend/requirements.txt]
- [x] [Review][Patch] `nh3.clean` missing explicit `url_schemes` — added `url_schemes={"http","https","mailto"}` [backend/app/routers/campaigns.py]
- [x] [Review][Patch] `editor.getHTML()` returns `"<p></p>"` for empty editor — added guard in handleSave [frontend/components/campaigns/BlogEditor.tsx]
- [x] [Review][Patch] H3 aria-label finding — dismissed (false positive; button already has `aria-label="Toggle heading 3"`)
- [x] [Review][Patch] `setattr` loop without explicit allowlist — replaced with `_PATCHABLE_FIELDS` filter [backend/app/routers/campaigns.py]
- [x] [Review][Defer] Race condition: status check is non-atomic; concurrent PATCH and approve could slip past guard [backend/app/routers/campaigns.py] — deferred, pre-existing architectural pattern
- [x] [Review][Defer] `onSave` prop declared but never called — Story 4.4 integration concern [frontend/components/campaigns/BlogEditor.tsx] — deferred, Story 4.4 will wire this up
- [x] [Review][Defer] `getCurrentHtml` ref not passed from page.tsx — by design, Story 4.4 will add the ref [frontend/app/(app)/campaigns/[id]/page.tsx] — deferred, by design for Story 4.4

- [x] [Review][Patch] StarterKit HorizontalRule and Strike produce `<hr>` and `<s>` that nh3 strips silently on save — data loss for users who use those formatting options [frontend/components/campaigns/BlogEditor.tsx]
- [x] [Review][Patch] Toolbar button order wrong — Link placed after Blockquote, spec (AC1) requires Bold, Italic, Link, H2, H3, Blockquote, Undo [frontend/components/campaigns/BlogEditor.tsx]
- [x] [Review][Patch] Empty-content guard only catches exact `"<p></p>"` — misses whitespace paragraphs, empty headings, etc.; use `editor.isEmpty` instead [frontend/components/campaigns/BlogEditor.tsx]
- [x] [Review][Patch] nh3 returning `""` stored as empty string → `rawBlogHtml` is falsy → GeneratingPlaceholder shown for a saved campaign; store `None` when nh3 output is empty [backend/app/routers/campaigns.py]
- [x] [Review][Patch] Frontend DOMPurify not applied before PATCH — AC4 requires frontend sanitization as first defense layer [frontend/components/campaigns/BlogEditor.tsx]
- [x] [Review][Defer] Save in-flight + Approve race → false error toast after successful approval — Story 4.4 concern; BlogEditor's isSaving not surfaced to ApprovalPanel [frontend/components/campaigns/ApprovalGateClient.tsx] — deferred, Story 4.4 to fix
- [x] [Review][Defer] handleApprove always patches even when user made no edits, bypasses empty guard, re-sanitizes AI content through nh3 — Story 4.4 concern [approval-panel.tsx] — deferred, Story 4.4 to add isDirty check
- [x] [Review][Defer] Optimistic approval shows stale blog content in BlogHtmlRenderer until router.refresh() resolves — Story 4.4 concern [frontend/components/campaigns/ApprovalGateClient.tsx] — deferred, Story 4.4 to track last-saved HTML
- [x] [Review][Defer] readOnly prop change not propagated to Tiptap editor (setEditable not called) — masked by current unmount/remount pattern but fragile [frontend/components/campaigns/BlogEditor.tsx] — deferred, future-proofing only
