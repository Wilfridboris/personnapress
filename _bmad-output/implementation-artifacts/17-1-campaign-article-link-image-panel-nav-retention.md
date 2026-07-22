# Story 17.1: Campaign Article Link, ImagePanel Parity & Nav Retention

---
baseline_commit: 78e7032b2e2105113907c9892dc266b93621dc21
---

Status: done

## Story

As a PersonnaPress user,
I want to see a clear link to the live article editor from the campaign page when headless-published, have the same image-edit capabilities in the campaign view as in the article editor, and stay on my current app section when switching client profiles,
So that my post-publish editing workflow is coherent and navigation feels intelligent rather than disruptive.

## Context

Three independent UX fixes bundled because they are all small, frontend-heavy, and share no risk of regression with each other.

**Fix 1 — Campaign → Article link (headless publish indicator)**
When a campaign has been published to the headless blog, `campaign.article_id` is populated. The campaign page currently renders `campaign.blog_html` forever — even after the user has edited the live article via the Blog Editor. There is no link from the campaign view to the article. Users get confused about where to edit the content.

The correct model: campaign HTML is the generation snapshot (read-only after headless publish); the `Article` record is the live, editable version. The fix is a banner that signals this and links to `/articles/[article_id]`.

**Fix 2 — ImagePanel parity: alt text + Replace upload**
`ImagePanel` (campaigns) lacks two editing capabilities that `ArticleEditor` has had since story 13-2:
- Editable `image_alt` input (saves on blur)
- "Replace image" button with file picker (uploads via `imagesApi.upload`, then saves URL)

The backend `PATCH /campaigns/{id}` blocks non-`pending_approval` campaigns (`campaigns.py:237`) and `_PATCHABLE_FIELDS` only covers `blog_html`, `x_post`, `linkedin_post`. A new dedicated endpoint `PATCH /campaigns/{id}/image` is required — unrestricted by campaign status, image fields only.

**Fix 3 — ClientSwitcher nav retention**
`ClientSwitcher.selectClient` hardcodes `router.push("/dashboard")`. Switching client while on `/articles` or `/calendar` should stay on that path. Switching from a detail page (e.g., `/articles/[id]`) should navigate to the parent list (`/articles`), not `/dashboard`.

## Acceptance Criteria

### AC1 — Headless article banner on campaign page

**Given** I am on `/campaigns/[id]` and `campaign.article_id` is non-null,
**When** the page renders,
**Then** a banner appears above the Blog Post panel with:
- Text: "Live in headless blog. Content edits go here."
- A link "Edit article →" pointing to `/articles/[campaign.article_id]`
- The blog HTML panel below renders read-only (no `BlogEditor`, only `BlogHtmlRenderer`) regardless of campaign status.

**Given** `campaign.article_id` is null,
**When** the page renders,
**Then** no banner is shown and the existing editable/read-only logic for the blog panel is unchanged.

### AC2 — ImagePanel alt text input

**Given** I am on `/campaigns/[id]` and the featured image exists,
**When** I edit the "Image alt text" input and blur out of it,
**Then** the new alt text is saved via `PATCH /campaigns/{id}/image` with `{ image_alt: <value> }` and a success toast is shown.

**Given** I clear the alt text field and blur,
**Then** `image_alt` is saved as empty string (or null) — no toast on no-op if value unchanged.

### AC3 — ImagePanel Replace image

**Given** I am on `/campaigns/[id]` with any campaign status,
**When** I click "Replace image" and select a PNG/JPEG/WebP file,
**Then**:
1. An upload spinner appears on the Replace button.
2. The file is uploaded via `imagesApi.upload(clientId, file)`.
3. The returned URL is saved via `PATCH /campaigns/{id}/image` with `{ image_url: <url> }`.
4. The image panel updates to show the new image without a page reload.
5. A success toast "Featured image updated." is shown.

**Given** upload fails,
**Then** an error toast is shown and the previous image remains.

### AC4 — Backend: `PATCH /campaigns/{id}/image` endpoint

**Given** any authenticated request to `PATCH /campaigns/{campaign_id}/image` with `{ image_url?: str, image_alt?: str }`,
**When** the campaign belongs to the caller's client,
**Then**:
- The endpoint updates `campaign.image_url` and/or `campaign.image_alt` unconditionally (no status check — image edits are always allowed).
- Returns `{ image_url: str | null, image_alt: str | null }` (200).
- Returns 404 if campaign not found or not owned by caller.
- Requires authentication (same session cookie pattern as all other campaign endpoints).

### AC5 — ClientSwitcher stays on current section

**Given** I am on `/articles` and switch client,
**Then** I remain on `/articles` (data reloads for the new client via TanStack Query).

**Given** I am on `/calendar` and switch client,
**Then** I remain on `/calendar`.

**Given** I am on `/campaigns` and switch client,
**Then** I remain on `/campaigns`.

**Given** I am on `/articles/[id]` (detail page) and switch client,
**Then** I navigate to `/articles` (parent list, not dashboard).

**Given** I am on `/campaigns/[id]` and switch client,
**Then** I navigate to `/campaigns`.

**Given** I am on `/clients/[id]/connections` or any other path not in the safe list,
**Then** I navigate to `/dashboard`.

**Safe bases (stay on):** `/dashboard`, `/articles`, `/campaigns`, `/calendar`, `/connections`
**Everything else:** navigate to `/${first-segment}` if it is a safe base, otherwise `/dashboard`.

## Dev Notes

### Fix 1 — Files to change

**`frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`**

1. Add `BookOpen, ArrowRight` to the lucide-react import.
2. After the `rawBlogHtml` declaration and before the blog panel `<div className="border border-border">`, insert the banner:

```tsx
{campaign.article_id && (
  <div className="flex items-center justify-between gap-3 border border-[#111111] bg-[#FFF1B8] px-4 py-3">
    <div className="flex items-center gap-2 min-w-0">
      <BookOpen className="size-4 shrink-0 text-[#111111]" aria-hidden="true" />
      <p className="font-mono text-xs text-[#111111] truncate">
        Live in headless blog. Content edits go here.
      </p>
    </div>
    <Link
      href={`/articles/${campaign.article_id}`}
      className={cn(
        "shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-[#111111]",
        "bg-[#111111] text-white hover:bg-white hover:text-[#111111] transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
      )}
    >
      Edit article
      <ArrowRight className="size-3" aria-hidden="true" />
    </Link>
  </div>
)}
```

3. **Read-only rule:** when `campaign.article_id` is non-null, the blog panel must be read-only — replace the existing `isPending ? <BlogEditor ...> : <BlogHtmlRenderer ...>` with:

```tsx
{rawBlogHtml ? (
  (isPending && !campaign.article_id) ? (
    <BlogEditor
      ref={blogEditorRef}
      initialHtml={rawBlogHtml}
      campaignId={campaign.id}
      clientId={campaign.client_id}
      readOnly={false}
    />
  ) : (
    <BlogHtmlRenderer
      html={rawBlogHtml}
      className="p-6 prose prose-sm max-w-none font-sans text-ink prose-headings:font-display prose-headings:text-ink prose-a:text-ink prose-a:underline"
    />
  )
) : (
  <div className="p-6"><GeneratingPlaceholder lines={8} /></div>
)}
```

This means: even a `pending_approval` campaign that has an `article_id` (edge case: shouldn't happen, but defensive) shows read-only. Normal pending campaigns without article_id remain editable.

**`frontend/app/(app)/campaigns/[id]/page.tsx`**
No changes needed — `campaign.article_id` is already fetched by the server component via `getCampaign` → `CampaignDetailResponse` (see `campaigns.py:202-213`).

**`frontend/lib/types.ts`**
Verify `Campaign` type has `article_id: string | null`. It should already exist from story 12-3. If missing, add it.

---

### Fix 2 — Files to change

#### Backend

**`backend/app/routers/campaigns.py`**

Add a new schema class above the router (near existing `CampaignPatch`):

```python
class CampaignImagePatch(BaseModel):
    image_url: Optional[str] = None
    image_alt: Optional[str] = None
```

Add a new endpoint after `patch_campaign`:

```python
@router.patch("/{campaign_id}/image")
async def patch_campaign_image(
    campaign_id: uuid.UUID,
    body: CampaignImagePatch,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Update campaign image_url and/or image_alt — unrestricted by campaign status."""
    try:
        user_id = uuid.UUID(current_user["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail=_INVALID_SESSION)

    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    client = await get_client(db, campaign.client_id)
    if not client or client.user_id != user_id:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    if body.image_url is not None:
        campaign.image_url = body.image_url
    if body.image_alt is not None:
        campaign.image_alt = body.image_alt

    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    return {"image_url": campaign.image_url, "image_alt": campaign.image_alt}
```

**No migration needed** — `image_url` and `image_alt` columns already exist on the `Campaign` model.

#### Frontend

**`frontend/lib/api.ts`**

Inside `campaignsApi`, add after `publishHeadless`:

```ts
patchImage: (id: string, body: { image_url?: string; image_alt?: string }) =>
  apiFetch<{ image_url: string | null; image_alt: string | null }>(`/campaigns/${id}/image`, {
    method: "PATCH",
    body: JSON.stringify(body),
  }),
```

**`frontend/components/campaigns/ImagePanel.tsx`**

Full rewrite of the component — add these imports:

```tsx
import { useState, useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import Image from "next/image";
import { campaignsApi, imagesApi, APIError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { useUIStore } from "@/lib/stores/useUIStore";
```

Updated props interface:

```tsx
interface ImagePanelProps {
  campaignId: string;
  clientId: string;         // NEW — required for imagesApi.upload
  imageUrl: string | null;
  imageAlt?: string;
  imageRegenCount: number;
  jobErrorDetails: string | null;
  isGenerating?: boolean;
}
```

New state inside the component:

```tsx
const addToast = useUIStore((s) => s.addToast);
const [altText, setAltText] = useState(imageAlt ?? "");
const [isSavingAlt, setIsSavingAlt] = useState(false);
const [isUploading, setIsUploading] = useState(false);
const fileInputRef = useRef<HTMLInputElement>(null);
const lastSavedAlt = useRef(imageAlt ?? "");
```

Alt save handler (call on blur):

```tsx
async function handleSaveAlt() {
  if (altText === lastSavedAlt.current) return;  // no-op if unchanged
  setIsSavingAlt(true);
  try {
    await campaignsApi.patchImage(campaignId, { image_alt: altText });
    lastSavedAlt.current = altText;
    addToast("Alt text saved.", "success");
  } catch (err) {
    setError(err instanceof APIError ? err.message : "Failed to save alt text.");
  } finally {
    setIsSavingAlt(false);
  }
}
```

Replace handler:

```tsx
async function handleReplaceImage(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0];
  if (!file) return;
  e.target.value = "";
  setIsUploading(true);
  setError(null);
  try {
    const { url } = await imagesApi.upload(clientId, file);
    await campaignsApi.patchImage(campaignId, { image_url: url });
    setCurrentImageUrl(url);
    addToast("Featured image updated.", "success");
  } catch (err) {
    setError(err instanceof APIError ? err.message : "Failed to replace image.");
  } finally {
    setIsUploading(false);
  }
}
```

In the "image present" return block, insert between the image and the existing regen `<Button>`:

```tsx
{/* Hidden file input */}
<input
  ref={fileInputRef}
  type="file"
  accept="image/png,image/jpeg,image/webp"
  className="sr-only"
  aria-hidden="true"
  tabIndex={-1}
  onChange={handleReplaceImage}
/>

{/* Alt text */}
<div className="space-y-1.5">
  <label
    htmlFor={`img-alt-${campaignId}`}
    className="text-[11px] font-medium uppercase tracking-[0.06em] text-graphite"
  >
    Image alt text
  </label>
  <input
    id={`img-alt-${campaignId}`}
    type="text"
    value={altText}
    onChange={(e) => setAltText(e.target.value)}
    onBlur={handleSaveAlt}
    placeholder="Describe what the image shows…"
    maxLength={500}
    disabled={isSavingAlt}
    className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB] disabled:opacity-50"
  />
</div>

{/* Replace image */}
<Button
  variant="secondary"
  onClick={() => fileInputRef.current?.click()}
  disabled={isUploading || isAtLimit || isRegenerating}
  aria-busy={isUploading}
  className="w-full font-mono"
>
  {isUploading ? (
    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
  ) : (
    "Replace image"
  )}
</Button>
```

Then the existing regen `<Button>` stays below Replace.

**`frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`**

Pass `clientId` to `ImagePanel`:

```tsx
<ImagePanel
  campaignId={campaign.id}
  clientId={campaign.client_id}   // ADD THIS
  imageUrl={campaign.image_url}
  imageAlt={campaign.image_alt ?? undefined}
  imageRegenCount={campaign.image_regen_count}
  jobErrorDetails={jobErrorDetails ?? null}
  isGenerating={jobIsActive}
/>
```

---

### Fix 3 — Files to change

**`frontend/components/layout/ClientSwitcher.tsx`**

1. Add `usePathname` to the next/navigation import:
```tsx
import { useRouter, usePathname } from "next/navigation";
```

2. Add the hook inside the component:
```tsx
const pathname = usePathname();
```

3. Replace `selectClient`:
```tsx
const SAFE_BASES = new Set(["/dashboard", "/articles", "/campaigns", "/calendar", "/connections"]);

function selectClient(id: string) {
  setActiveClientId(id);
  setIsOpen(false);
  const base = "/" + (pathname.split("/")[1] ?? "dashboard");
  router.push(SAFE_BASES.has(base) ? base : "/dashboard");
}
```

---

### API Contract

`PATCH /api/v1/campaigns/{campaign_id}/image`

Request body:
```json
{ "image_url": "https://...", "image_alt": "Alt text here" }
```
Both fields optional; at least one should be present (but the endpoint accepts both or either).

Response (200):
```json
{ "image_url": "https://...", "image_alt": "Alt text here" }
```

---

### Type checks

- `Campaign` in `types.ts` must have `article_id: string | null` and `image_alt: string | null`.
- After adding `patchImage` to `campaignsApi`, TypeScript will enforce the return type.

---

### Testing checklist

**Fix 1 — Banner:**
- Campaign with `article_id` → banner visible, link href correct, blog panel read-only
- Campaign without `article_id` → no banner, existing editable/read-only logic unchanged
- Campaign `pending_approval` + no `article_id` → BlogEditor still rendered (regression guard)

**Fix 2 — ImagePanel:**
- Alt text blur with changed value → `PATCH /campaigns/{id}/image` called with `image_alt`
- Alt text blur with unchanged value → no API call
- Replace → file picker opens, upload spinner shown, image updates in UI on success
- Replace failure → error shown, previous image unchanged
- Regen still works (existing tests must pass)
- Backend: `PATCH /campaigns/{id}/image` with valid session + owned campaign → 200
- Backend: unknown campaign or wrong client → 404
- Backend: unauthenticated → 401

**Fix 3 — Nav retention:**
- On `/articles`, switch client → stay `/articles`
- On `/articles/abc-123`, switch client → go to `/articles`
- On `/campaigns/xyz`, switch client → go to `/campaigns`
- On `/clients/abc/connections`, switch client → go to `/dashboard`
- Existing dashboard redirect behavior confirmed for unknown paths

---

### Constraints

- Do NOT modify `_PATCHABLE_FIELDS` in `campaigns.py` — it exists only for the approval-gate patch endpoint and must remain content-only.
- Do NOT change the idempotency logic in `create_or_update_article_from_campaign` — campaign and article are intentionally separate records.
- Do NOT add motion/animation — CSS transitions only (consistent with existing Paper Style).
- No new npm dependencies.
- RSC loop rule: `ApprovalGateClient` is already a client component. No server component data fetching added.

## Tasks/Subtasks

- [x] Fix 1: Headless article banner in ApprovalGateClient
  - [x] Add BookOpen + ArrowRight lucide imports
  - [x] Insert banner when campaign.article_id is non-null
  - [x] Override blog panel to read-only when article_id present
- [x] Fix 2: ImagePanel alt text + Replace image
  - [x] Backend: Add CampaignImagePatch schema + PATCH /campaigns/{id}/image endpoint
  - [x] Frontend: Add campaignsApi.patchImage in api.ts
  - [x] Frontend: Rewrite ImagePanel with alt text input (save on blur) and Replace button
  - [x] Pass clientId from ApprovalGateClient to ImagePanel
- [x] Fix 3: ClientSwitcher nav retention
  - [x] Add usePathname hook
  - [x] Replace hardcoded /dashboard push with pathname-aware logic
- [x] Tests: 6 new backend tests for patch_campaign_image endpoint

## Dev Agent Record

### Completion Notes

All three fixes implemented in a single session without pauses:

**Fix 1** — Added `BookOpen`/`ArrowRight` lucide imports and `Link` to `ApprovalGateClient.tsx`. Banner renders above the Blog Post panel when `campaign.article_id` is non-null (amber `#FFF1B8` background, Paper Style border). Blog panel read-only override: `(isPending && !campaign.article_id)` — only editable when pending approval AND no article_id.

**Fix 2** — Backend: `CampaignImagePatch` Pydantic model + `PATCH /{campaign_id}/image` endpoint with no status restriction. No migration needed (`image_url`/`image_alt` columns already exist). Frontend: `campaignsApi.patchImage` added to `api.ts`. `ImagePanel` fully rewritten: adds `clientId` prop, `altText` state with blur-save (no-op guard via `lastSavedAlt` ref), hidden file `<input>` for Replace, `imagesApi.upload` → `campaignsApi.patchImage` chain. Replace button disabled while uploading/regenerating/at-limit.

**Fix 3** — `SAFE_BASES` Set moved to module level. `usePathname` wired in. `selectClient` derives base segment, stays on safe bases, falls back to `/dashboard` for everything else (detail pages like `/articles/[id]` navigate to parent `/articles`).

**Tests** — 6 new tests in `test_campaigns_router.py` covering: happy path with both fields, alt-only update, status-unrestricted operation, wrong-user 404, not-found 404, unauthenticated 401. All pass; 8 pre-existing failures unchanged.

## File List

- `backend/app/routers/campaigns.py` — added `CampaignImagePatch` model + `patch_campaign_image` endpoint
- `backend/tests/test_campaigns_router.py` — added 6 tests for patch_campaign_image
- `frontend/lib/api.ts` — added `patchImage` to `campaignsApi`
- `frontend/components/campaigns/ImagePanel.tsx` — full rewrite with `clientId`, alt text input, Replace button
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` — headless banner + read-only override + clientId prop to ImagePanel
- `frontend/components/layout/ClientSwitcher.tsx` — pathname-aware client switching

## Change Log

- 2026-07-22: Story 17-1 implemented — headless article banner, ImagePanel alt+replace parity, ClientSwitcher nav retention

### Review Findings

- [x] [Review][Patch] P1 (high) — Upload failure uses `setError` not `addToast` — AC3 explicit violation [frontend/components/campaigns/ImagePanel.tsx:handleReplaceImage]
- [x] [Review][Patch] P2 (medium) — Alt save failure uses `setError` not `addToast` — inconsistent with toast pattern [frontend/components/campaigns/ImagePanel.tsx:handleSaveAlt]
- [x] [Review][Patch] P3 (medium) — `image_url` accepts arbitrary strings, no URL format validation [backend/app/routers/campaigns.py:CampaignImagePatch]
- [x] [Review][Patch] P4 (low) — `image_alt` has no max_length cap in backend model (frontend maxLength=500 is bypassable) [backend/app/routers/campaigns.py:CampaignImagePatch]
- [x] [Review][Patch] P5 (low) — Concurrent `handleSaveAlt` calls not guarded by `isSavingAlt` check at entry [frontend/components/campaigns/ImagePanel.tsx:handleSaveAlt]
- [x] [Review][Patch] P6 (low) — Test assertions compare returned value against mutated mock object instead of input body values [backend/tests/test_campaigns_router.py]
- [x] [Review][Patch] P7 (low) — `patch_campaign_image` returns `-> dict` with no Pydantic response model on decorator [backend/app/routers/campaigns.py:patch_campaign_image]
- [x] [Review][Patch] P8 (low) — Empty PATCH body (both fields None) still commits to DB — spurious round-trip [backend/app/routers/campaigns.py:patch_campaign_image]
- [x] [Review][Patch] P9 (low) — `altText` state and `lastSavedAlt` ref not synced when `imageAlt` prop changes externally [frontend/components/campaigns/ImagePanel.tsx]
- [x] [Review][Defer] D1 — Orphaned CDN file when patchImage PATCH fails after successful upload [frontend/components/campaigns/ImagePanel.tsx] — deferred, pre-existing 2-step upload pattern; requires CDN cleanup infrastructure
- [x] [Review][Defer] D2 — No rate-limiting on PATCH /campaigns/{id}/image [backend/app/routers/campaigns.py] — deferred, pre-existing, affects all endpoints
- [x] [Review][Defer] D3 — No client-side file size/MIME check before upload [frontend/components/campaigns/ImagePanel.tsx] — deferred, pre-existing from story 12-5 upload pattern; server validates
- [x] [Review][Defer] D4 — `db.refresh` on AsyncMock is no-op in tests [backend/tests/test_campaigns_router.py] — deferred, pre-existing test infrastructure limitation
