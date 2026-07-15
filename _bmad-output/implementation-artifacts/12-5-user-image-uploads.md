---
baseline_commit: 10a2eac79c43fafd0f252076440614e28ddeabd5
---

# Story 12.5: User Image Uploads — Inline Article Images & Featured Image Replace

Status: done

## Story

As a PersonnaPress user,
I want to upload my own images into the blog editor and replace the featured image,
so that my articles carry my visuals, not just the AI-generated one.

## Acceptance Criteria

1. **Given** an authenticated user who owns a client, **When** they POST an image (png, jpg, jpeg, or webp, max 5 MB) as multipart to `/api/v1/clients/{client_id}/images`, **Then** the file is validated by extension AND magic bytes, stored in a public `article-images` Supabase bucket at `{client_id}/{uuid}.{ext}`, and the response returns the public URL; oversize, wrong type, unowned client, or missing session return the standard nested error shape.

2. **Given** the Supabase storage integration, **When** the `article-images` bucket is auto-created on first upload, **Then** it is created with `public=true` (the existing `_ensure_bucket` hardcodes `public=False`, which would 404 every public URL), and `_content_type_for_path` returns correct image MIME types for .png/.jpg/.jpeg/.webp.

3. **Given** the three HTML sanitization layers (client DOMPurify in `BlogEditor.tsx`, nh3 in `campaigns.py` blog_html PATCH, BeautifulSoup `_sanitize_html` in `articles.py`), **When** HTML containing images is sanitized, **Then** all three allow `img`, `figure`, `figcaption` with attributes `src`, `alt`, `width`, `height` only; any `img` whose `src` does not start with the app's Supabase public-object URL prefix (article-images or generated-images buckets) is removed entirely; event-handler attributes, `srcset`, and `style` are stripped.

4. **Given** the shared Tiptap `BlogEditor` toolbar, **When** the user clicks the image button (Lucide `ImagePlus`), pastes an image, or drops an image file onto the editor, **Then** the file uploads via the endpoint from AC 1 with a visible in-progress state, a required alt-text prompt is shown before insertion, and the image is inserted at the cursor as `<img src alt>`; multiple images per article are supported; upload failure surfaces an error toast and inserts nothing.

5. **Given** an inline image is selected in the editor, **When** the selection is active, **Then** the toolbar exposes replace (re-upload, same node) and remove actions plus alt-text editing, each with accessible labels; removing an image from the article never deletes the stored object (revision history references it).

6. **Given** the `/blog/[id]` article editor right rail, **When** an article renders, **Then** a "Featured image" card shows the current image (or an empty state) with a Replace action that uploads via AC 1 and PATCHes `featured_image_url` (field added to `ArticlePatch`, validated to the app's own storage URL prefix); featured image changes do not create revisions (documented v1 exclusion).

7. **Given** GitHub publishing and the public delivery API, **When** blog HTML containing inline images flows through them, **Then** `html_to_markdown` converts `<img>` to `![alt](src)` (regression test) and `/public/v1/articles/{slug}` delivers inline `<img>` tags intact through `_strip_scripts` (regression test).

8. **Given** the new UI, **When** assessed against the Paper Style design system, **Then** it uses 1px Ink borders, rounded-none, Lucide icons only (no emojis), visible `focus-visible` rings, 44px minimum touch targets, CSS-only transitions (no Framer Motion), and required alt text enforced in the upload flow.

9. **Given** the security test suite, **When** it runs, **Then** tests prove: user B cannot upload to user A's client; `<img onerror=...>` and foreign-host `src` are stripped by both server sanitizers; oversize and non-image payloads (including a renamed .exe) are rejected.

## Tasks / Subtasks

### Task 1: Storage integration fixes (AC: 2)

- [x] 1.1 `backend/app/integrations/supabase_storage.py`: extend `_content_type_for_path` with `.png` → `image/png`, `.jpg`/`.jpeg` → `image/jpeg`, `.webp` → `image/webp`.
- [x] 1.2 Add `public: bool = False` parameter to `upload_file`, threaded into the `_ensure_bucket` call on the bucket-not-found retry path. Do NOT change existing callers (brand-content stays private).
- [x] 1.3 Add a small helper `public_object_url(bucket: str, object_path: str) -> str` returning `{SUPABASE_URL}/storage/v1/object/public/{bucket}/{object_path}` (extract the URL-building logic already inlined in `upload_image_from_url` and reuse it there — do not duplicate the string format twice).

### Task 2: Image upload endpoint (AC: 1, 9)

- [x] 2.1 New router `backend/app/routers/images.py` (or extend `files.py` — prefer a new file; files.py is brand-content-specific with its 10-file limit which must NOT apply here): `POST /api/v1/clients/{client_id}/images`. Copy the exact patterns from `backend/app/routers/files.py`: `_get_owned_client` ownership check (reuse it via import if importable without circularity, else copy), nested error constants, `UploadFile = File(...)`.
- [x] 2.2 Validation order: extension in `{".png", ".jpg", ".jpeg", ".webp"}` → read bytes → size ≤ 5 MB → magic-byte sniff (PNG `\x89PNG\r\n\x1a\n`, JPEG `\xff\xd8\xff`, WEBP `RIFF....WEBP`). Reject mismatched extension/magic with the standard nested error shape (e.g. code `INVALID_IMAGE`). No Pillow dependency needed — plain byte-prefix checks.
- [x] 2.3 Store via `upload_file("article-images", f"{client_id}/{uuid4()}{ext}", file_bytes, public=True)`; respond `{"url": public_object_url(...), "path": ...}` with a Pydantic response model. Single file per request (the editor uploads one at a time).
- [x] 2.4 Register router in `backend/app/main.py` (same block as `files.router` / `articles.router`).

### Task 3: Sanitizer stack — all three layers in lockstep (AC: 3, 9)

- [x] 3.1 Define the allowed-src prefixes ONCE per side. Backend: module-level helper `is_allowed_image_src(src: str) -> bool` in a shared location (e.g. `backend/app/core/html_sanitize.py` or inline in each router with a shared constant — prefer one shared module since two routers need it) checking `src.startswith(f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/article-images/")` or the same for `generated-images`. If `SUPABASE_URL` is unset (local dev without storage), reject all img src (fail closed) — document this in a comment.
- [x] 3.2 `backend/app/routers/articles.py`: add `"img", "figure", "figcaption"` to `_ALLOWED_TAGS`; extend `_ALLOWED_ATTRS` with `{"img": ["src", "alt", "width", "height"]}`. In `_sanitize_html`, after attribute stripping, `decompose()` any `img` whose `src` is missing or fails `is_allowed_image_src`.
- [x] 3.3 `backend/app/routers/campaigns.py`: add the same tags to `_ALLOWED_HTML_TAGS`, `{"img": {"src", "alt", "width", "height"}}` to `_ALLOWED_HTML_ATTRS`. nh3 supports an `attribute_filter` callback — use it to return `None` for disallowed `img src` values (which drops the attribute), then post-strip `<img>` without `src` via a BeautifulSoup pass or nh3 config. Verify against installed nh3 version's API before coding; if `attribute_filter` is awkward, a small BeautifulSoup post-pass mirroring 3.2 is acceptable — correctness over cleverness.
- [x] 3.4 `frontend/components/campaigns/BlogEditor.tsx`: extend `_DOMPURIFY_CONFIG` — `ALLOWED_TAGS` += `img`, `figure`, `figcaption`; `ALLOWED_ATTR` += `src`, `alt`, `width`, `height`. Client side does NOT need the src-prefix check (server is authoritative), but the editor only ever inserts own-bucket URLs anyway.
- [x] 3.5 `frontend/app/(app)/blog/[id]/article-editor.tsx` has its own DOMPurify usage for revision preview and pre-PATCH sanitize — find every DOMPurify config in the frontend (`grep -r "ALLOWED_TAGS" frontend/`) and update ALL of them identically. A missed config silently deletes user images on save — this is the single most likely bug in this story.

### Task 4: Tiptap inline images in BlogEditor (AC: 4, 5, 8)

- [x] 4.1 Install `@tiptap/extension-image` matching the installed `@tiptap/*` major version (check `frontend/package.json` first; all Tiptap packages must be on the same version line). Configure `Image.configure({ inline: false, allowBase64: false })` — block-level images, never base64 (base64 would bypass the src allowlist and bloat the DB).
- [x] 4.2 New prop on `BlogEditor`: `clientId: string` (needed for the upload endpoint). Both call sites already have it: approval flow has the campaign's client, article editor has `article.client_id`. Update both call sites in the same commit — a missing prop is a type error, not a runtime surprise.
- [x] 4.3 Toolbar button: Lucide `ImagePlus`, same button classes as existing toolbar buttons (`p-1.5 hover:bg-border transition-colors focus-visible:ring-2 focus-visible:ring-ink`, `bg-highlighter` when an image node is active), `aria-label="Insert image"`. Clicking opens a hidden `<input type="file" accept="image/png,image/jpeg,image/webp">`.
- [x] 4.4 Upload flow: on file pick → open the alt-text dialog (existing `Modal` component from `frontend/components/ui/Modal.tsx` — focus trap/restore/scroll lock already patched per Story 7-2): shows filename, required alt-text input (Inter 13px label "Alt text", helper line "Describes the image for screen readers and search engines."), optional caption input, Confirm ("Insert image", Ink fill primary with the `4px 4px 0px` shadow treatment used elsewhere) disabled while alt is empty or upload pending (`Loader2` CSS spin). On confirm: upload via new `imagesApi.upload(clientId, file)`, then `editor.chain().focus().setImage({ src, alt }).run()`; when a caption was given, insert as `<figure><img/><figcaption>text</figcaption></figure>` (Tiptap: either a small Figure extension or insertContent with the HTML — keep it minimal, no new dependency). On upload error: toast `err.message`, close dialog, insert nothing.
- [x] 4.5 Paste/drop: `editorProps.handlePaste` / `handleDrop` — when the payload contains an image file, prevent default and route into the same alt-dialog flow (never insert data-URLs). Non-image paste/drop must fall through untouched (return false) — do not break text paste.
- [x] 4.6 Selected-image actions: when `editor.isActive("image")`, the toolbar additionally shows: replace (`ImagePlus` with `aria-label="Replace image"` — re-opens the file+alt flow and updates the selected node's attrs), edit alt (`PenLine`, pre-filled dialog), remove (`Trash2`, `aria-label="Remove image"`, deletes the node — no confirm needed, undo covers it). Never call any storage-delete API from the editor (AC 5: objects outlive articles because revisions reference them).
- [x] 4.7 Editor CSS: images render via the existing `prose` classes; add `prose-img:border prose-img:border-border prose-img:my-4` (or equivalent) so images sit flush with Paper Style — sharp corners, no rounded, no shadows.

### Task 5: Featured image replace (AC: 6)

- [x] 5.1 Backend: add `featured_image_url: Optional[str] = Field(None, max_length=1000)` to `ArticlePatch` in `backend/app/schemas/article.py` with an after-validator enforcing `is_allowed_image_src` (import from the shared module of 3.1). In `backend/app/routers/articles.py` PATCH handler: treat `featured_image_url` like `status` — a non-content field routed OUTSIDE `update_article_content` (no revision; Story 12.1 AC 4 lists the content fields and featured_image_url is not one). It must still bump `updated_at` so the public API ETag changes (featured_image_url appears in list responses and `seo.og`).
- [x] 5.2 Frontend `frontend/app/(app)/blog/[id]/article-editor.tsx`: new "Featured image" card in the right rail above Details — current image as `<img>` (aspect-video, `object-cover`, 1px Ink border, rounded-none, meaningful alt) or empty state (Graphite `ImageOff` icon + "No featured image"); a "Replace" secondary button (1px Ink border, hover:bg-ink hover:text-white, min-h 44px) opening file picker → upload → PATCH `{featured_image_url}` via the existing update mutation or a dedicated one; `Loader2` spin while pending; success toast "Featured image updated."
- [x] 5.3 Types/API: `frontend/lib/api.ts` gains `imagesApi.upload(clientId, file)` (multipart POST, returns `{url}`) and `featured_image_url` in the article-update payload type; `frontend/lib/types.ts` already has `featured_image_url` on `Article` — verify, extend the patch type only.

### Task 6: Downstream regression tests (AC: 7)

- [x] 6.1 `backend/tests/` (locate the existing github/publishing service test file): `html_to_markdown('<p>x</p><img src="https://.../a.png" alt="Chart">')` contains `![Chart](https://.../a.png)`; a `<figure><img/><figcaption>Cap</figcaption></figure>` input produces the image markdown and the caption text without crashing (markdownify handles both — the test pins the behavior).
- [x] 6.2 Public API test (extend `backend/tests/` public articles tests): an article whose html contains an allowed `<img>` returns it intact from `GET /public/v1/articles/{slug}` (`_strip_scripts` must not touch it).

### Task 7: Backend tests (AC: 1, 3, 9)

- [x] 7.1 New `backend/tests/routers/test_images.py`: happy-path upload (mock `supabase_storage.upload_file`, assert bucket/path/public args and returned URL), ownership 403/404 (user B on user A's client — mirror test_articles.py ownership tests), 401 no session, oversize rejection, extension rejection, magic-byte rejection (a `.png`-named file with exe bytes `MZ...`).
- [x] 7.2 Extend `backend/tests/routers/test_articles.py`: PATCH html keeps allowed own-bucket `<img>`; strips foreign-src `<img>`; strips `onerror`/`style`/`srcset` attrs; `figure`/`figcaption` survive; PATCH `featured_image_url` with own-bucket URL succeeds WITHOUT creating a revision and bumps `updated_at`; foreign URL → 422.
- [x] 7.3 Extend campaigns PATCH tests similarly for the nh3 layer (allowed img kept, foreign src dropped, onerror stripped).

### Task 8: Verification checklist (AC: 4, 5, 8)

- [ ] 8.1 Manual: insert 3 images in one article via button, paste, and drag-drop; save; reload; all 3 persist (proves every DOMPurify config was updated per 3.5).
- [ ] 8.2 Manual: publish a campaign with an inline image to Headless Blog and view via the public API sample from the 12-4 page patterns.
- [ ] 8.3 Keyboard-only pass: toolbar button reachable, dialog focus-trapped, alt input labelled, all actions have visible focus rings.

### Review Findings

- [x] [Review][Patch] _sanitize_html crashes when block tag (object/iframe/embed) has element children — decomposed nodes remain in find_all list; tag.unwrap() on parentless node raises ValueError → 500 [backend/app/routers/articles.py:61-79]
- [x] [Review][Patch] BlogHtmlRenderer.tsx has its own hardcoded DOMPurify config without img/figure/figcaption — inline images stripped in approval read-only view (Task 3.5 missed this fourth DOMPurify site) [frontend/components/ui/BlogHtmlRenderer.tsx:22-29]
- [x] [Review][Patch] BeautifulSoup articles sanitizer allows javascript: href on <a> tags — no URL scheme validation unlike nh3's url_schemes; public API consumers rendering the html field would be exposed to XSS [backend/app/routers/articles.py:47-48]
- [x] [Review][Patch] is_allowed_image_src path-traversal bypass — URL like .../article-images/../other-bucket/x.png passes startswith check; normalize path before comparison [backend/app/core/html_sanitize.py:22-25]
- [x] [Review][Patch] Dangerous tags (template, svg, math, use, noscript) not in _BLOCK_TAGS — they get unwrap()ed instead of decompose()d, promoting children into parent context [backend/app/routers/articles.py:51]
- [x] [Review][Patch] Insert image button silently acts as Replace when image is selected — handleFilePickerChange re-checks isActive("image") at file-pick time, switching mode without user awareness [frontend/components/campaigns/BlogEditor.tsx:189-196]
- [x] [Review][Patch] nodeAt(selection.from) unreliable for edit-alt — use editor.getAttributes("image").alt instead; nodeAt can return null if cursor at node boundary, clearing existing alt text on confirm [frontend/components/campaigns/BlogEditor.tsx:137]
- [x] [Review][Patch] Multi-image paste/drop silently drops all images after first — add a toast: "Only the first image was inserted; paste one at a time" [frontend/components/campaigns/BlogEditor.tsx:94-119]
- [x] [Review][Patch] 401 no-session test missing for image upload endpoint — spec Task 7.1 listed it explicitly [backend/tests/routers/test_images.py]
- [x] [Review][Patch] srcset-strip test missing for campaigns sanitizer — nh3 strips it but no regression test [backend/tests/test_campaigns_router.py]
- [x] [Review][Defer] No rate-limiting on POST /clients/{client_id}/images [backend/app/routers/images.py:87] — deferred, pre-existing infrastructure gap; all endpoints share same global rate-limiter pattern

## Dev Notes

### Critical constraints

- **One Tiptap editor** (Story 12.3 rule): extend `BlogEditor.tsx`; never fork. The image feature lands in BOTH the campaign approval flow and the article editor automatically because they share the component.
- **Three sanitizers, one allowlist.** Client DOMPurify (`BlogEditor.tsx` + any config in `article-editor.tsx`), nh3 (`campaigns.py:23`), BeautifulSoup (`articles.py:37`). All must accept the exact same tags/attrs or images silently vanish at whichever layer was missed. The server-side src-prefix restriction is the security boundary; DOMPurify is UX-level only.
- **Fail closed on src.** Only `article-images` and `generated-images` public-object URLs pass. No external URLs by design (v1 decision: keeps out tracking pixels and hotlinked content). No base64.
- **Never delete storage objects** when images are removed from articles — revision history snapshots html that references them. No GC in v1.
- **Featured image is not versioned.** `featured_image_url` is not a Story 12.1 AC 4 content field; route it around `update_article_content` like `status`, but ensure `updated_at` bumps (public ETag must change).
- **No new heavyweight deps.** `@tiptap/extension-image` only (match installed Tiptap major). Magic-byte checks are byte-prefix comparisons, not Pillow.
- **RSC loop rule** unchanged: all new data calls go through TanStack Query / fetch in client components.
- **Paper Style:** 1px Ink borders, rounded-none, Lucide only, no emojis, CSS transitions only (no Framer Motion — nothing here needs exit animations), 44px touch targets, `focus-visible:ring-2 focus-visible:ring-ink`.

### Reuse map

| Need | Existing code |
|---|---|
| Multipart upload endpoint pattern (ownership, size/ext checks, error shape) | `backend/app/routers/files.py` |
| Storage upload + public URL | `backend/app/integrations/supabase_storage.py` (`upload_file`, URL format in `upload_image_from_url`) |
| Server sanitizer (articles) | `_sanitize_html` in `backend/app/routers/articles.py:49` |
| Server sanitizer (campaigns) | nh3 config in `backend/app/routers/campaigns.py:23-25,185` |
| Client sanitizer | `_DOMPURIFY_CONFIG` in `frontend/components/campaigns/BlogEditor.tsx:26` |
| Toolbar button styling | existing buttons in `BlogEditor.tsx` toolbar |
| Modal with focus trap | `frontend/components/ui/Modal.tsx` (Story 7-2 patched) |
| Mutation + toast + invalidate patterns | `frontend/app/(app)/blog/[id]/article-editor.tsx` (Story 12.3) |
| html→markdown conversion | `html_to_markdown` in `backend/app/integrations/github.py:31` (markdownify, handles `img` natively) |
| Ownership test patterns | `backend/tests/routers/test_articles.py` |

### Previous story intelligence (12.1–12.4)

- 12.3 added `hideSaveButton` to BlogEditor instead of forking — same spirit here: additive props (`clientId`), no breaking changes to the approval-flow call site.
- 12.3 review history shows the approval panel is regression-prone; this story does NOT touch `approval-panel.tsx` — the image button arrives there via the shared BlogEditor only.
- 12.2 hardened `_strip_scripts` to iframe/object/embed; it deliberately does not touch `img` — do not "improve" it to strip images.
- 12.1 AC 4 defines the revision-triggering content fields; html edits containing images version automatically since html is snapshotted.
- Story 3-4/3-6 own AI featured-image generation via Replicate → `generated-images` bucket; user upload is a parallel path, not a replacement — do not modify `image.py`/`replicate.py`.
- Reviews repeatedly patched: separate `invalidateQueries` from mutation try-blocks (11-6), never manually set `updated_at` where the repo layer handles it (7-3), surface `err.message` from APIError (11-7).

### Project Structure Notes

- Backend: new `backend/app/routers/images.py`, new shared `backend/app/core/html_sanitize.py` (src allowlist helper), edits to `supabase_storage.py`, `articles.py`, `campaigns.py`, `schemas/article.py`, `main.py`.
- Frontend: edits to `BlogEditor.tsx`, `article-editor.tsx`, `lib/api.ts`, `lib/types.ts`. No new pages, no nav changes.
- Tests: new `backend/tests/routers/test_images.py`; extensions to `test_articles.py`, campaigns tests, publishing/github service tests.
- Read `node_modules/next/dist/docs/` guidance before any Next-specific changes (AGENTS.md rule) — though this story adds no new routes or server components.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 12, Story 12.5]
- [Source: _bmad-output/implementation-artifacts/12-3-edit-after-publish-revision-ui.md (BlogEditor extension pattern, sanitizer parity, Paper Style AC)]
- [Source: _bmad-output/implementation-artifacts/12-1-article-model-revision-history.md (revision-triggering fields)]
- [Source: _bmad-output/implementation-artifacts/12-2-public-delivery-api-tokens.md (_strip_scripts, ETag)]
- [Source: backend/app/routers/files.py (upload endpoint pattern)]
- [Source: backend/app/integrations/supabase_storage.py (bucket public=False footgun)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- **`@tiptap/extension-image` peer dep conflict**: Installed with `--legacy-peer-deps`; resolved to 3.27.4 (compatible major version 3).
- **`fetchAPI` multipart issue**: `fetchAPI` injects `Content-Type: application/json`, breaking multipart boundaries. Fixed by using raw `fetch` in `imagesApi.upload`.
- **`test_patch_campaign_returns_200_for_owner` regression**: `_make_campaign` factory missing `github_pr_url = None`; added to fix Pydantic ValidationError on CampaignResponse.
- **`@testing-library/dom` missing**: Frontend tests required `npm install @testing-library/dom --save-dev --legacy-peer-deps` to resolve missing transitive dependency.
- **Task 8 (manual verification)**: Marked as manual-only; cannot be automated in this story. Requires a running Supabase instance with the `article-images` bucket configured.

### Completion Notes List

- Three-layer sanitizer parity enforced via shared `backend/app/core/html_sanitize.py::is_allowed_image_src`; DOMPurify client layer does NOT enforce src prefix (server is authoritative).
- nh3 `attribute_filter` + BeautifulSoup post-pass pattern used in campaigns.py: nh3 strips disallowed src, leaving `<img>` without src, then BeautifulSoup removes those empty-src tags.
- Featured image (`featured_image_url`) routed in PATCH handler OUTSIDE `update_article_content` block — no revision created; `updated_at` bumped manually.
- `_DOMPURIFY_CONFIG` exported from BlogEditor.tsx and imported in article-editor.tsx — single source of truth for all three frontend DOMPurify call sites.
- No storage-delete API called from editor; objects are never GC'd in v1 (revision history snapshots reference them).
- `imagesApi.upload` uses raw `fetch` (not `fetchAPI`) to avoid JSON Content-Type header corrupting multipart form boundary.

### File List

- `backend/app/core/html_sanitize.py` (NEW)
- `backend/app/integrations/supabase_storage.py` (MODIFIED)
- `backend/app/routers/images.py` (NEW)
- `backend/app/routers/articles.py` (MODIFIED)
- `backend/app/routers/campaigns.py` (MODIFIED)
- `backend/app/schemas/article.py` (MODIFIED)
- `backend/app/main.py` (MODIFIED)
- `backend/tests/routers/test_images.py` (NEW)
- `backend/tests/routers/test_articles.py` (MODIFIED)
- `backend/tests/test_campaigns_router.py` (MODIFIED)
- `backend/tests/integrations/test_github.py` (MODIFIED)
- `backend/tests/routers/test_public_articles.py` (MODIFIED)
- `frontend/components/campaigns/BlogEditor.tsx` (MODIFIED)
- `frontend/app/(app)/blog/[id]/article-editor.tsx` (MODIFIED)
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` (MODIFIED)
- `frontend/lib/api.ts` (MODIFIED)
- `frontend/lib/types.ts` (MODIFIED)
- `frontend/package.json` (MODIFIED — added `@tiptap/extension-image@^3.27.4`, `@testing-library/dom`)
- `frontend/__tests__/components/BlogEditor.test.tsx` (MODIFIED)

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-07-14 | 1.0 | Initial implementation: storage fixes, image upload endpoint, three-layer sanitizer stack, Tiptap Image extension, featured image replace UI, downstream regression tests | claude-sonnet-4-6 |
