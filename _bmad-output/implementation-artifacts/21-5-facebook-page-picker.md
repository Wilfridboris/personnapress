---
baseline_commit: 3a6310c
---

# Story 21.5: Facebook Page Picker for Multi-Page Meta Accounts

Status: done

## Story

As a PersonnaPress user with multiple Facebook Pages on my Meta account,
I want to choose which Facebook Page PersonnaPress connects to during the OAuth flow,
so that PersonnaPress publishes to the correct page instead of silently connecting to whichever page the API returns first.

---

## Context & Motivation

The current Meta OAuth callback (`POST /api/v1/clients/{client_id}/connections/meta/callback`)
calls `/me/accounts` to discover the user's Facebook Pages, then unconditionally picks
**the first page** in the response and stores it. Users with one page are unaffected.
Users with multiple pages are silently mis-connected: the wrong page gets linked, they
have no way to know, and there is no recovery path short of disconnecting and reconnecting.

Story 21.5 introduces a two-phase approach:

- **Phase 1 (modify existing callback):** When `/me/accounts` returns more than one page,
  the backend stores a short-lived `meta_pending` platform connection row (encrypted JSON
  with the long-lived token and full pages list), returns HTTP 200 with
  `{status: "page_selection_required", pages: [...]}`, and does NOT save any permanent
  connection. When only one page exists, the existing auto-select path runs unchanged and
  returns HTTP 201 as before.

- **Phase 2 (new endpoint):** `POST /api/v1/clients/{client_id}/connections/meta/select-page`
  receives `{page_id: str}`, loads the `meta_pending` row, runs the full credential-save
  logic on just the chosen page, deletes the pending row, and returns HTTP 201 with
  `{connected_platforms: [...]}`.

The Next.js callback route handles both response shapes. When `page_selection_required`,
it stores the pages list in a client-readable cookie and redirects to the connections
page with `?meta_picker=1`. On mount, `PlatformConnectionsClient.tsx` detects the query
param, reads the cookie, opens a Page Picker Modal, and calls the new `select-page` API
method on confirmation.

**Story 21.5 is independent of Story 21.6.** No dependency in either direction.

**API version: v25.0** (all Meta Graph API calls use v25.0, not v21.0 from the epics file).

---

## Acceptance Criteria

### AC 1: Single-page auto-select is unchanged

**Given** a Meta account with exactly one Facebook Page,
**When** `POST /api/v1/clients/{client_id}/connections/meta/callback` runs,
**Then** the behaviour is identical to today: credentials are saved, HTTP 201 is returned,
`connected_platforms` lists the saved platforms, the Next.js callback redirects to
`?success=meta`, and the "Meta platforms connected." toast appears.

No changes to the single-page path whatsoever.

### AC 2: Multi-page discovery returns page_selection_required

**Given** a Meta account with two or more Facebook Pages (`/me/accounts` returns len >= 2),
**When** `POST /api/v1/clients/{client_id}/connections/meta/callback` runs,
**Then**:

a) The backend does NOT save any `instagram`, `facebook_page`, or `threads` connection.

b) The backend saves a single `platform_connection` row with:
   - `platform = "meta_pending"`
   - `encrypted_credentials` = encrypt_credential of JSON:
     ```json
     {
       "long_lived_token": "<string>",
       "pages": [
         {
           "id": "<page_id>",
           "name": "<page_name>",
           "access_token": "<page_access_token>",
           "instagram_user_id": "<str or null>",
           "instagram_username": "<str or null>"
         }
       ],
       "created_at": "<ISO 8601 UTC string>"
     }
     ```
   - One `meta_pending` row per client (upsert by `(client_id, platform)`).

c) The endpoint returns HTTP 200 (not 201) with body:
   ```json
   {
     "status": "page_selection_required",
     "pages": [
       {
         "id": "<page_id>",
         "name": "<page_name>",
         "has_instagram": true,
         "instagram_username": "@boris_page"
       }
     ]
   }
   ```
   `has_instagram` is `true` when the page has a linked Instagram Business Account.
   `instagram_username` is the IG username (without `@`) when `has_instagram` is true,
   `null` otherwise.

d) HTTP 200 status code is returned (the existing endpoint declares `status_code=201` --
   the multi-page branch must override this with an explicit `Response(status_code=200, ...)`).

### AC 3: select-page endpoint finalises the connection

**Given** a valid `meta_pending` connection exists for `client_id`,
**When** `POST /api/v1/clients/{client_id}/connections/meta/select-page` is called
with body `{"page_id": "<string>"}`,
**Then**:

a) The `meta_pending` row is loaded and decrypted. If not found, return HTTP 404:
   `{"error": {"code": "NO_PENDING_CONNECTION", "message": "No pending Meta connection found. Please reconnect."}}`.

b) If `created_at` in the decrypted JSON is older than 10 minutes (600 seconds), return
   HTTP 410:
   `{"error": {"code": "PENDING_CONNECTION_EXPIRED", "message": "The Meta connection session has expired. Please reconnect."}}`.

c) The `page_id` is looked up in the stored `pages` list. If not found, return HTTP 400:
   `{"error": {"code": "INVALID_PAGE_SELECTION", "message": "Selected page not found. Please reconnect."}}`.

d) For the selected page, save credentials exactly as the original callback does today
   (steps d, e, f in the original endpoint -- instagram upsert if page has IG account,
   facebook_page upsert always, threads discovery and upsert if instagram was found).
   These use the same `long_lived_token` from the pending row for Threads discovery.

e) The `meta_pending` connection row is deleted after successful save
   (call `delete_connection(db, client_id, "meta_pending")`).

f) Return HTTP 201 with `{"connected_platforms": ["instagram", "facebook_page", "threads"]}` (or whatever subset was saved).

### AC 4: DB migration adds meta_pending to platform_enum

**Given** the existing `platform_enum` in PostgreSQL,
**When** the Alembic migration runs,
**Then** `meta_pending` is added as a valid enum value using `autocommit_block()` with
`ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'meta_pending'`.

The migration is generated via `cd backend && alembic revision -m "add_meta_pending_platform"`
(NEVER hand-write the revision ID per project-context.md). The `Platform` StrEnum in
`backend/app/db/repositories/models.py` gains `meta_pending = "meta_pending"`. Downgrade is a
`pass` comment: "PostgreSQL does not support removing enum values -- downgrade omits enum revert."

### AC 5: Next.js callback handles both response shapes

**Given** the backend returns HTTP 200 with `{status: "page_selection_required", pages: [...]}`,
**When** the Next.js route handler at `frontend/app/api/auth/meta/callback/route.ts` processes it,
**Then**:

a) Reads the pages list from the response.

b) Constructs a `MetaPageOptions` object:
   ```typescript
   { clientId: string; pages: MetaPageOption[] }
   // where MetaPageOption = { id: string; name: string; has_instagram: boolean; instagram_username: string | null }
   ```

c) Sets a cookie named `meta_page_options` on the redirect response:
   - `value`: `JSON.stringify(metaPageOptions)`
   - `httpOnly: false` (client JS must be able to read it)
   - `maxAge: 600`
   - `sameSite: "lax"`
   - `path: "/"`
   - `secure: process.env.NODE_ENV === "production"`

d) Clears the `oauth_state_meta` cookie (existing behaviour).

e) Redirects to `${connectionsUrl}?meta_picker=1`.

**Given** the backend returns HTTP 201 (single page auto-selected),
**When** the Next.js callback processes it,
**Then** behaviour is unchanged: clear `oauth_state_meta` cookie, redirect to `?success=meta`.

**Error handling**: if the backend returns a non-200/201 status, use existing error redirect
pattern (unchanged from today).

### AC 6: Page Picker Modal in PlatformConnectionsClient.tsx

**Given** the connections page loads with `?meta_picker=1` in the URL,
**When** `PlatformConnectionsClient.tsx` mounts,
**Then**:

a) The existing `useEffect` that handles `?success` and `?error` is extended to also handle
   `?meta_picker=1`. When detected:
   - Read the `meta_page_options` cookie value (`document.cookie`).
   - Parse it as `MetaPageOptions`.
   - If parsing succeeds and `pages.length > 0`, open the Page Picker Modal by setting
     `pickerPages` state and `pickerOpen` state to `true`.
   - If parsing fails or pages is empty, show an error toast:
     "Meta connection failed. Please try connecting again." (no picker shown).

b) While the modal is open, the user sees a list of pages (see AC 7 for design). Selecting
   a page card sets `selectedPageId` state. The Confirm button is disabled until a page is
   selected.

c) On Confirm:
   1. Call `publishingApi.selectMetaPage(clientId, selectedPageId)`.
   2. On success: delete `meta_page_options` cookie (`document.cookie = "meta_page_options=; max-age=0; path=/"`), call `queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] })`, close the modal, call `addToast("Meta platforms connected.", "success")`.
   3. On error: show error message inside the modal (do NOT close modal). Error message from `err?.detail?.error?.message ?? "Failed to connect. Please try again."`.

d) On Cancel: close the modal, delete `meta_page_options` cookie.

e) The `handledRef.current = true` guard must be set when the picker is opened, just like the
   success/error branches, to prevent double-firing.

### AC 7: Page Picker Modal Paper Style design

**Given** the Page Picker Modal is open,
**When** it renders,
**Then**:

- Uses the existing `Modal` component from `@/components/ui/Modal`.
- `title` prop: `"Select Facebook Page"`
- Below the title, a subtitle paragraph: `"Choose which page PersonnaPress should publish to."`
  (`text-sm text-[#555555] mb-4`)
- Page list: each page rendered as a `<button>` with full-width bordered card style:
  - Default: `w-full text-left border border-[#E5E5E5] p-3 mb-2 rounded-none`
  - Selected: `w-full text-left border border-[#111111] bg-[#FFF1B8] p-3 mb-2 rounded-none`
  - Inside each card:
    - Row 1: `PlatformIcon platform="facebook_page" className="size-4 text-graphite" color="mono"` + page name (`text-sm font-medium text-[#111111] ml-1.5`)
    - Row 2 (conditional on `has_instagram`):
      - If `has_instagram === true`: `PlatformIcon platform="instagram" className="size-3 text-graphite" color="mono"` + `"Linked Instagram: @{instagram_username}"` (`text-xs text-[#555555] ml-1`)
      - If `has_instagram === false`: `"No linked Instagram Business Account"` (`text-xs text-[#555555]`)
- Footer with two buttons (flex row, gap-3, mt-4):
  - Cancel: `border border-[#111111] text-[#111111] text-xs font-medium px-4 min-h-[44px] rounded-none hover:bg-[#F5F5F5]`
  - Confirm: `bg-[#111111] text-white text-xs font-medium px-4 min-h-[44px] rounded-none disabled:opacity-50 disabled:cursor-not-allowed`
  - Confirm is `disabled` until `selectedPageId` is non-null.
- If an API error occurred (AC 6c step 3), show below the page list (above footer):
  `<p className="text-xs text-red-600 mt-2">{errorMessage}</p>`
- No emojis. No em-dashes in any user-visible text. `rounded-none` throughout.

---

## Dev Notes

### File-by-file changes

#### 1. `backend/alembic/versions/<generated_id>_add_meta_pending_platform.py` (NEW)

Generate with: `cd backend && alembic revision -m "add_meta_pending_platform"`

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'meta_pending'"))

def downgrade() -> None:
    # PostgreSQL does not support removing enum values -- downgrade omits enum revert.
    pass
```

#### 2. `backend/app/db/repositories/models.py` (UPDATE)

Add to the `Platform` StrEnum:

```python
meta_pending = "meta_pending"
```

Full Platform enum after change:
```python
class Platform(str, Enum):
    wordpress = "wordpress"
    wordpress_com = "wordpress-com"
    webflow = "webflow"
    x = "x"
    linkedin = "linkedin"
    github_pages = "github_pages"
    instagram = "instagram"
    facebook_page = "facebook_page"
    threads = "threads"
    meta_pending = "meta_pending"
```

#### 3. `backend/app/routers/publishing.py` (UPDATE)

**3a. Modify `meta_oauth_callback` (around line 375)**

The endpoint currently declares `status_code=201`. For the multi-page path we must return 200.
Change the return type and add an explicit `Response` import:

```python
from fastapi.responses import JSONResponse
```

After the `pages = await meta_integration.discover_accounts(long_lived_token)` call, replace
the existing loop + return with:

```python
from datetime import datetime, timezone

# Multi-page path: require user selection
if len(pages) > 1:
    # Build the pending credentials JSON
    pages_for_storage = []
    pages_for_picker = []
    for page in pages:
        page_id = page.get("id", "")
        page_name = page.get("name", "")
        page_access_token = page.get("access_token", "")
        ig_account = page.get("instagram_business_account")
        ig_user_id = ig_account.get("id", "") if ig_account else None
        ig_username = ig_account.get("username", "") if ig_account else None

        pages_for_storage.append({
            "id": page_id,
            "name": page_name,
            "access_token": page_access_token,
            "instagram_user_id": ig_user_id,
            "instagram_username": ig_username,
        })
        pages_for_picker.append({
            "id": page_id,
            "name": page_name,
            "has_instagram": bool(ig_user_id),
            "instagram_username": ig_username,
        })

    pending_cred = json.dumps({
        "long_lived_token": long_lived_token,
        "pages": pages_for_storage,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    encrypted_pending = encrypt_credential(pending_cred)
    await upsert_connection(db, client_id, "meta_pending", encrypted_pending)

    return JSONResponse(
        status_code=200,
        content={
            "status": "page_selection_required",
            "pages": pages_for_picker,
        },
    )

# Single-page path: auto-select (existing logic below, unchanged)
```

Then the existing single-page loop continues unchanged.

**3b. Add the Pydantic model for select-page request**

```python
class MetaSelectPageRequest(BaseModel):
    page_id: str
```

**3c. Add the new select-page endpoint**

```python
@router.post("/clients/{client_id}/connections/meta/select-page", status_code=201)
async def meta_select_page(
    client_id: uuid.UUID,
    body: MetaSelectPageRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    from datetime import datetime, timezone, timedelta

    user_id = _parse_user_id(current_user)
    client = await get_client(db, client_id)
    _check_ownership(client, user_id)

    # Load the meta_pending connection
    connections = await get_connections_for_client(db, client_id)
    pending_conn = next(
        (c for c in connections if c.platform == "meta_pending"), None
    )
    if not pending_conn:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NO_PENDING_CONNECTION", "message": "No pending Meta connection found. Please reconnect.", "detail": {}}},
        )

    try:
        pending_data = json.loads(decrypt_credential(pending_conn.encrypted_credentials))
    except Exception:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_PENDING_DATA", "message": "Pending Meta connection is corrupt. Please reconnect.", "detail": {}}},
        )

    # Check 10-minute expiry
    created_at_str = pending_data.get("created_at", "")
    try:
        created_at = datetime.fromisoformat(created_at_str)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created_at > timedelta(seconds=600):
            raise ValueError("expired")
    except ValueError:
        raise HTTPException(
            status_code=410,
            detail={"error": {"code": "PENDING_CONNECTION_EXPIRED", "message": "The Meta connection session has expired. Please reconnect.", "detail": {}}},
        )

    long_lived_token = pending_data.get("long_lived_token", "")
    pages = pending_data.get("pages", [])

    # Find the selected page
    selected = next((p for p in pages if p.get("id") == body.page_id), None)
    if not selected:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_PAGE_SELECTION", "message": "Selected page not found. Please reconnect.", "detail": {}}},
        )

    page_id = selected["id"]
    page_name = selected["name"]
    page_access_token = selected["access_token"]
    ig_user_id = selected.get("instagram_user_id")
    ig_username = selected.get("instagram_username")

    connected_platforms: list[str] = []

    # Save Instagram connection (if page has linked IG account)
    if ig_user_id:
        ig_cred = json.dumps({
            "instagram_user_id": ig_user_id,
            "username": ig_username or "",
            "page_access_token": page_access_token,
            "facebook_page_id": page_id,
            "facebook_page_name": page_name,
        })
        await upsert_connection(db, client_id, "instagram", encrypt_credential(ig_cred))
        connected_platforms.append("instagram")

    # Save Facebook Page connection
    fb_cred = json.dumps({
        "page_id": page_id,
        "page_name": page_name,
        "page_access_token": page_access_token,
    })
    await upsert_connection(db, client_id, "facebook_page", encrypt_credential(fb_cred))
    connected_platforms.append("facebook_page")

    # Attempt Threads discovery (non-fatal, same as original callback)
    if ig_user_id:
        threads_user_id = await meta_integration.discover_threads_user_id(
            ig_user_id, long_lived_token
        )
        if threads_user_id:
            threads_cred = json.dumps({
                "threads_user_id": threads_user_id,
                "username": ig_username or "",
                "user_access_token": long_lived_token,
            })
            await upsert_connection(db, client_id, "threads", encrypt_credential(threads_cred))
            connected_platforms.append("threads")

    # Delete the pending connection
    await delete_connection(db, client_id, "meta_pending")

    return {"connected_platforms": connected_platforms}
```

**Important**: `delete_connection` already exists -- confirm its signature. It takes
`(db, client_id, platform)` where platform is a string. Check `publishing.py` line ~215
where it is imported and used with `DELETE /connections/{platform}`. Use the same call.

#### 4. `frontend/app/api/auth/meta/callback/route.ts` (UPDATE)

Add types at the top:

```typescript
type MetaPageOption = {
  id: string;
  name: string;
  has_instagram: boolean;
  instagram_username: string | null;
};

type MetaPageOptions = {
  clientId: string;
  pages: MetaPageOption[];
};
```

Replace the successful backend response handling section. Currently the code does:

```typescript
// ...backendResp.ok check...
// then falls through to:
return clearCookieRedirect(successUrl);
```

After verifying `backendResp.ok`, read the response body to distinguish 200 vs 201:

```typescript
const respData = await backendResp.json().catch(() => ({})) as {
  status?: string;
  pages?: MetaPageOption[];
  connected_platforms?: string[];
};

if (respData.status === "page_selection_required" && respData.pages?.length) {
  const metaPageOptions: MetaPageOptions = {
    clientId: oauthState.clientId,
    pages: respData.pages,
  };
  const res = NextResponse.redirect(`${connectionsUrl}?meta_picker=1`);
  res.cookies.delete("oauth_state_meta");
  res.cookies.set("meta_page_options", JSON.stringify(metaPageOptions), {
    httpOnly: false,        // client JS must read it
    sameSite: "lax",
    maxAge: 600,
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return res;
}

// 201 single-page auto-select path (unchanged)
return clearCookieRedirect(successUrl);
```

The `clearCookieRedirect` helper already deletes `oauth_state_meta`. In the picker path we
handle cookie deletion manually (both deleting `oauth_state_meta` and setting `meta_page_options`).

#### 5. `frontend/lib/api.ts` (UPDATE)

Add to `publishingApi` object:

```typescript
selectMetaPage: (clientId: string, pageId: string) =>
  apiFetch<{ connected_platforms: string[] }>(
    `/clients/${clientId}/connections/meta/select-page`,
    {
      method: "POST",
      body: JSON.stringify({ page_id: pageId }),
    }
  ),
```

#### 6. `frontend/components/publishing/PlatformConnectionsClient.tsx` (UPDATE)

**6a. Add imports**

```typescript
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Modal } from "@/components/ui/Modal";
```

`useRef` and `useEffect` already imported. `PlatformIcon` already imported. `addToast` and
`publishingApi` already imported.

**6b. Add state and queryClient in component body**

```typescript
const queryClient = useQueryClient();
const [pickerOpen, setPickerOpen] = useState(false);
const [pickerPages, setPickerPages] = useState<MetaPageOption[]>([]);
const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
const [pickerError, setPickerError] = useState<string | null>(null);
const [pickerLoading, setPickerLoading] = useState(false);
```

**6c. Extend the existing useEffect**

The existing `useEffect` reads `params.get("success")` and `params.get("error")`. Extend it:

```typescript
const picker = params.get("meta_picker");
if (picker === "1") {
  handledRef.current = true;
  // Read meta_page_options cookie
  const raw = document.cookie
    .split("; ")
    .find((c) => c.startsWith("meta_page_options="))
    ?.split("=")
    .slice(1)
    .join("=");
  if (raw) {
    try {
      const opts = JSON.parse(decodeURIComponent(raw)) as MetaPageOptions;
      if (opts.pages && opts.pages.length > 0) {
        setPickerPages(opts.pages);
        setPickerOpen(true);
        return;
      }
    } catch {
      // fall through to error
    }
  }
  addToast("Meta connection failed. Please try connecting again.", "error");
  return;
}
```

Place this block before the `success`/`error` check. Note: the existing `if (!success && !error) return;` guard must be adjusted to also not return early when `meta_picker=1` is present.

**6d. Add confirm handler**

```typescript
async function handlePickerConfirm() {
  if (!selectedPageId) return;
  setPickerLoading(true);
  setPickerError(null);
  try {
    await publishingApi.selectMetaPage(clientId, selectedPageId);
    // Delete cookie
    document.cookie = "meta_page_options=; max-age=0; path=/";
    await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
    setPickerOpen(false);
    addToast("Meta platforms connected.", "success");
  } catch (err: unknown) {
    const msg =
      (err as { detail?: { error?: { message?: string } } })?.detail?.error?.message ??
      "Failed to connect. Please try again.";
    setPickerError(msg);
  } finally {
    setPickerLoading(false);
  }
}
```

**6e. Add cancel handler**

```typescript
function handlePickerCancel() {
  document.cookie = "meta_page_options=; max-age=0; path=/";
  setPickerOpen(false);
  setPickerPages([]);
  setSelectedPageId(null);
  setPickerError(null);
}
```

**6f. Add types at module level (above component)**

```typescript
type MetaPageOption = {
  id: string;
  name: string;
  has_instagram: boolean;
  instagram_username: string | null;
};

type MetaPageOptions = {
  clientId: string;
  pages: MetaPageOption[];
};
```

**6g. Add Modal JSX** (render at the bottom of the component return, after `<DeliveryTokensCard>`):

```tsx
<Modal
  isOpen={pickerOpen}
  onClose={handlePickerCancel}
  title="Select Facebook Page"
  titleId="meta-page-picker-title"
  descriptionId="meta-page-picker-desc"
>
  <p
    id="meta-page-picker-desc"
    className="text-sm text-[#555555] mb-4"
  >
    Choose which page PersonnaPress should publish to.
  </p>

  <div role="radiogroup" aria-labelledby="meta-page-picker-title">
    {pickerPages.map((page) => (
      <button
        key={page.id}
        role="radio"
        aria-checked={selectedPageId === page.id}
        onClick={() => setSelectedPageId(page.id)}
        className={
          selectedPageId === page.id
            ? "w-full text-left border border-[#111111] bg-[#FFF1B8] p-3 mb-2 rounded-none"
            : "w-full text-left border border-[#E5E5E5] p-3 mb-2 rounded-none hover:border-[#999999]"
        }
      >
        <div className="flex items-center gap-1.5">
          <PlatformIcon
            platform="facebook_page"
            className="size-4 text-graphite"
            color="mono"
            aria-hidden="true"
          />
          <span className="text-sm font-medium text-[#111111]">{page.name}</span>
        </div>
        <div className="flex items-center gap-1 mt-1">
          {page.has_instagram ? (
            <>
              <PlatformIcon
                platform="instagram"
                className="size-3 text-graphite"
                color="mono"
                aria-hidden="true"
              />
              <span className="text-xs text-[#555555]">
                Linked Instagram: @{page.instagram_username}
              </span>
            </>
          ) : (
            <span className="text-xs text-[#555555]">
              No linked Instagram Business Account
            </span>
          )}
        </div>
      </button>
    ))}
  </div>

  {pickerError && (
    <p className="text-xs text-red-600 mt-2">{pickerError}</p>
  )}

  <div className="flex gap-3 mt-4">
    <button
      onClick={handlePickerCancel}
      className="border border-[#111111] text-[#111111] text-xs font-medium px-4 min-h-[44px] rounded-none hover:bg-[#F5F5F5]"
    >
      Cancel
    </button>
    <button
      onClick={handlePickerConfirm}
      disabled={!selectedPageId || pickerLoading}
      className="bg-[#111111] text-white text-xs font-medium px-4 min-h-[44px] rounded-none disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {pickerLoading ? "Connecting..." : "Confirm"}
    </button>
  </div>
</Modal>
```

---

### Credential JSON shapes (exact)

**`meta_pending` encrypted_credentials (stored in platform_connection row):**
```json
{
  "long_lived_token": "<60-day user access token string>",
  "pages": [
    {
      "id": "<facebook_page_id>",
      "name": "<facebook_page_name>",
      "access_token": "<page_access_token>",
      "instagram_user_id": "<ig_user_id or null>",
      "instagram_username": "<ig_username or null>"
    }
  ],
  "created_at": "2026-08-01T14:30:00.123456+00:00"
}
```

**`instagram` encrypted_credentials (unchanged from Story 21.1):**
```json
{
  "instagram_user_id": "<ig_user_id>",
  "username": "<ig_username>",
  "page_access_token": "<page_access_token>",
  "facebook_page_id": "<facebook_page_id>",
  "facebook_page_name": "<facebook_page_name>"
}
```

**`facebook_page` encrypted_credentials (unchanged from Story 21.1):**
```json
{
  "page_id": "<facebook_page_id>",
  "page_name": "<facebook_page_name>",
  "page_access_token": "<page_access_token>"
}
```

**`threads` encrypted_credentials (unchanged from Story 21.1):**
```json
{
  "threads_user_id": "<threads_user_id>",
  "username": "<ig_username>",
  "user_access_token": "<long_lived_user_token>"
}
```

---

### Architecture and patterns to follow

- **API version**: v25.0 (not v21.0 from epics file -- v21.0 deprecated, all existing meta.py already uses v25.0).
- **encrypt_credential / decrypt_credential**: imported from `app.core.security`, used exactly as in the existing callback.
- **upsert_connection / delete_connection**: imported from `app.db.repositories.platform_connections`. Both already used in the same file.
- **get_connections_for_client**: already imported and used in `publishing.py` for list connections endpoint. Use it to find the `meta_pending` row.
- **_parse_user_id / _check_ownership**: private helpers already in `publishing.py`. Call them at the top of the new endpoint identically to the existing `meta_oauth_callback`.
- **Error response format**: all error raises in `publishing.py` use `{"error": {"code": "...", "message": "...", "detail": {}}}`. Match this exactly.
- **RSC loop rule**: PlatformConnectionsClient.tsx is already a `"use client"` component using TanStack Query. No server component changes needed. Continue this pattern.
- **No em-dashes**: use commas, colons, or short phrases instead of `--` or `—` in all user-visible text.
- **Modal component**: use `@/components/ui/Modal` exactly as defined. It handles focus trap, Escape key, and backdrop click.
- **TanStack query invalidation**: `queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] })` -- matches the existing query key pattern used throughout.

---

### What NOT to do

- Do NOT add a new DB table. Use the existing `platform_connections` table with `platform="meta_pending"`.
- Do NOT use `threads_basic` or `threads_content_publish` scopes in the OAuth URL -- those were removed in a prior commit (3a6310c, the baseline). The `route.ts` at `frontend/app/api/auth/meta/route.ts` already has the correct scope without Threads scopes.
- Do NOT hand-write an Alembic revision ID. Use `alembic revision -m "..."` CLI.
- Do NOT put the picker pages list in an httpOnly cookie. The cookie must be readable by client JavaScript (`httpOnly: false`).
- Do NOT use emojis anywhere in UI text or code comments.
- Do NOT add `rounded-sm` or any other border radius. Paper Style uses `rounded-none` everywhere.
- Do NOT use `useSearchParams()` hook from Next.js in `PlatformConnectionsClient.tsx` -- this causes RSC subscription re-renders. The existing pattern reads `window.location.search` imperatively inside `useEffect` and this story follows the same pattern.

---

## Tests Required

### Backend (pytest)

1. `test_meta_callback_single_page_unchanged` -- mock discover_accounts returning 1 page; assert upsert called, HTTP 201, `connected_platforms` in response.
2. `test_meta_callback_multi_page_stores_pending` -- mock discover_accounts returning 2+ pages; assert upsert called with platform="meta_pending"; assert no instagram/facebook_page upsert; assert HTTP 200, `status="page_selection_required"`, `pages` array in response with `has_instagram` bool.
3. `test_meta_callback_multi_page_has_instagram_false` -- mock page with no instagram_business_account; assert `has_instagram=false` in picker response and `instagram_username=null`.
4. `test_meta_select_page_success` -- mock pending row with 2 pages; call select-page with valid page_id; assert instagram+facebook_page+threads upserted, meta_pending deleted, HTTP 201.
5. `test_meta_select_page_no_pending_returns_404` -- no meta_pending row; assert HTTP 404 with `NO_PENDING_CONNECTION`.
6. `test_meta_select_page_expired_returns_410` -- pending row with `created_at` > 10 minutes ago; assert HTTP 410 with `PENDING_CONNECTION_EXPIRED`.
7. `test_meta_select_page_invalid_page_id_returns_400` -- page_id not in stored pages list; assert HTTP 400 with `INVALID_PAGE_SELECTION`.
8. `test_meta_select_page_no_instagram_page` -- selected page has `instagram_user_id=null`; assert only facebook_page upserted (no instagram, no threads), meta_pending deleted.

---

## Dev Agent Record

### Completion Notes

Implementation of Story 21.5 complete. Two-phase approach implemented as specified:

**Phase 1 (modified `meta_oauth_callback`):** When `/me/accounts` returns 2+ pages, the backend now stores a `meta_pending` platform_connection row (encrypted JSON with long-lived token + full pages list), and returns HTTP 200 with `{status: "page_selection_required", pages: [...]}`. Single-page path is unchanged (HTTP 201 + auto-select).

**Phase 2 (new `meta_select_page` endpoint):** `POST /api/v1/clients/{client_id}/connections/meta/select-page` loads the pending row, validates expiry (10 min), looks up the chosen page, saves instagram/facebook_page/threads credentials (same logic as original callback), deletes the pending row, returns HTTP 201 with `{connected_platforms: [...]}`.

**Frontend:** Next.js callback route.ts detects HTTP 200 `page_selection_required` response, sets `meta_page_options` cookie (httpOnly: false, maxAge: 600), redirects to `?meta_picker=1`. PlatformConnectionsClient.tsx useEffect reads the cookie on mount, opens the Page Picker Modal (Paper Style design per AC 7). Confirm calls `selectMetaPage` API, invalidates connections query.

**Migration:** Generated via CLI (`alembic revision -m "add_meta_pending_platform"`), adds `meta_pending` to `platform_enum` using `autocommit_block()`.

Fixed a regression introduced during `MetaSelectPageRequest` insertion that accidentally split `OAuthCallbackRequest` and removed its `code_verifier` field. Corrected before final test run.

All 8 required tests pass (64 total in test_meta_integration.py). No regressions (56 pre-existing failures unchanged).

---

## File List

- `backend/alembic/versions/20260801_1103_b89b98f2591f_add_meta_pending_platform.py` (new)
- `backend/app/db/repositories/models.py` (modified)
- `backend/app/routers/publishing.py` (modified)
- `backend/tests/test_meta_integration.py` (modified)
- `frontend/app/api/auth/meta/callback/route.ts` (modified)
- `frontend/lib/api.ts` (modified)
- `frontend/components/publishing/PlatformConnectionsClient.tsx` (modified)

---

## Change Log

- 2026-08-01: Implemented Story 21.5 -- Facebook Page Picker for multi-page Meta accounts. Added meta_pending platform enum value (migration + models.py), two-phase OAuth flow in publishing.py (multi-page branch + select-page endpoint), Next.js callback route.ts handling for both response shapes, selectMetaPage API method, Page Picker Modal in PlatformConnectionsClient.tsx with Paper Style design.
- 2026-08-01: Code review patches applied: timedelta moved to top-level import in publishing.py, meta_oauth_callback response_model=None added (correct return type for dict/JSONResponse union), error extraction in handlePickerConfirm corrected to err instanceof Error.
- 2026-08-01: Second code review pass (3-layer: Blind Hunter + Edge Case Hunter + Acceptance Auditor). 1 patch applied, 14 findings dismissed as false positives or already handled.

---

### Review Findings

- [x] [Review][Patch] Instagram row 2 uses gap-1 on wrapper div instead of ml-1 on text span [frontend/components/publishing/PlatformConnectionsClient.tsx:253] — AC 7 specifies ml-1 on the span; fixed.

---

Status: done
