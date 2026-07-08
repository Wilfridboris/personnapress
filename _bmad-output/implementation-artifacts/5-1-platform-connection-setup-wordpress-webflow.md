---
baseline_commit: b14d5693c6a141a135d01cb60d71f9f160ecce0b
---

# Story 5.1: Platform Connection Setup — WordPress & Webflow

Status: review

## Story

As an authenticated user,
I want to connect my Client to WordPress and Webflow by providing my API credentials,
So that PersonnaPress can publish blog posts directly to my CMS on my behalf.

## Acceptance Criteria

1. **Given** a user navigates to `/clients/{id}/connections`, **When** the Platform Connections page loads, **Then** four platform connection cards are displayed — WordPress, Webflow, X, LinkedIn — each showing the platform name, connection status ("Connected" / "Not connected"), and connected account identifier (site URL or CMS name if connected); "Connect" CTA is shown on disconnected platforms.

2. **Given** a user clicks "Connect" on the WordPress card, **When** the connection form opens, **Then** an inline form appears below the card with two fields: "WordPress site URL" (standard Input component, e.g., https://mysite.com) and "Application Password" (password input, masked); a "Connect" primary button and "Cancel" secondary button are present; the form renders inside the card with no page navigation.

3. **Given** the user submits a WordPress site URL and Application Password, **When** `POST /api/v1/clients/{client_id}/connections` is called with `{"platform": "wordpress", "site_url": "...", "credential": "..."}`, **Then** FastAPI validates credentials by calling `{site_url}/wp-json/wp/v2/users/me` with Basic Auth (Application Password); if HTTP 200, encrypts with `encrypt_credential()` (`core/security.py`) and writes a `platform_connections` row; returns `{"id": "...", "platform": "wordpress", "account_identifier": "{site_url}", "connected": true}`; card updates to "Connected — {site_url}" without page reload.

4. **Given** the WordPress credentials fail validation (HTTP 401 from WordPress), **When** the test call returns 401, **Then** FastAPI returns HTTP 400 with `{"error": {"code": "CREDENTIAL_VALIDATION_FAILED", "message": "WordPress returned 401 — check your Application Password."}}` — the inline form stays open for correction; no `platform_connections` record is created.

5. **Given** a user clicks "Connect" on the Webflow card, **When** the connection form opens, **Then** fields are shown for "Webflow API Bearer Token" (text input) and a "CMS Collection" selector; the selector shows "Loading collections..." state; upon entering a token and clicking "Validate token" (secondary button), `GET /api/v1/clients/{client_id}/webflow/collections?token={token}` is called — the endpoint proxies a request to the Webflow CMS API v2 (`GET https://api.webflow.com/v2/sites/{site_id}/collections`) and returns a list of collection names + IDs to populate the dropdown.

6. **Given** the Webflow token validation fails or the collections API returns an error, **When** the dropdown population fails, **Then** the dropdown is replaced by a plain text input labeled "Webflow Collection ID" with the microcopy: "Find your Collection ID in Webflow → CMS → [Collection] → Settings"; the user can enter the ID manually; the form remains open.

7. **Given** valid Webflow token and collection are submitted, **When** `POST /api/v1/clients/{client_id}/connections` is called with `{"platform": "webflow", "token": "...", "collection_id": "..."}`, **Then** both values are JSON-serialized, encrypted as one credential blob with `encrypt_credential()`, stored in `platform_connections`; the card shows "Connected — {collection_id}" without page reload.

8. **Given** a user clicks "Disconnect" on any connected platform card, **When** the disconnect action is triggered, **Then** a confirmation dialog appears: "Disconnect [Platform]? Future campaigns will not publish to this platform." with a "Disconnect" Danger button and "Cancel"; on confirm, `DELETE /api/v1/clients/{client_id}/connections/{platform}` deletes the `platform_connections` row; the card reverts to "Not connected" without page reload.

9. **Given** the Platform Connections page loads, **When** the initial data fetch is in progress, **Then** skeleton placeholder cards (4 × card-shaped rectangles at correct heights) are shown — no spinner — until data loads.

10. **Given** a screen reader navigates the Platform Connections page, **When** the user tabs through the interface, **Then** all inputs have visible labels (not placeholder-only); "Connect" and "Disconnect" buttons have descriptive aria-labels ("Connect WordPress", "Disconnect WordPress"); connection status is announced via `aria-live` region on card update; the confirmation dialog has `role="dialog"` with `aria-labelledby` pointing to its heading, focus trap, and Esc-to-close behavior.

## Tasks / Subtasks

- [x] Task 1: Create `backend/app/db/repositories/platform_connections.py` (AC: #3, #7, #8)
  - [x] 1.1 Add repository functions:
    ```python
    async def get_connections_for_client(db: AsyncSession, client_id: uuid.UUID) -> list[PlatformConnection]
    async def get_connection(db: AsyncSession, client_id: uuid.UUID, platform: str) -> PlatformConnection | None
    async def upsert_connection(db: AsyncSession, client_id: uuid.UUID, platform: str, encrypted_credentials: str) -> PlatformConnection
    async def delete_connection(db: AsyncSession, client_id: uuid.UUID, platform: str) -> bool
    ```
  - [x] 1.2 `upsert_connection`: check if a row exists for `(client_id, platform)`; if yes `UPDATE encrypted_credentials + updated_at`; if no `INSERT` new row — use SQLAlchemy `select` + `db.add()`
  - [x] 1.3 `delete_connection`: `DELETE WHERE client_id={} AND platform={}` — return `True` if deleted, `False` if not found

- [x] Task 2: Implement `backend/app/routers/publishing.py` — platform connection endpoints (AC: #1, #3, #4, #5, #6, #7, #8)
  - [x] 2.1 Replace the empty stub with full implementation. Keep prefix `/publishing` unless overridden — but note: architecture maps these routes as `/clients/{id}/connections`, so set `prefix=""` (no prefix on this router) since `API_PREFIX` is already applied in `main.py`; use individual route paths like `"/clients/{client_id}/connections"`
  - [x] 2.2 Add `GET /clients/{client_id}/connections` — replace the stub in `clients.py` with the real implementation here; remove stub from `clients.py` (important: this stub exists at `backend/app/routers/clients.py` and returns `{"items": []}` — delete it to avoid duplicate route):
    ```python
    @router.get("/clients/{client_id}/connections")
    async def list_platform_connections(
        client_id: uuid.UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
    ```
    - Ownership check: load client, verify `client.user_id == user_id`
    - Return `{"items": [{"platform": pc.platform, "connected": True, "account_identifier": extract_identifier(pc)}]}` for each connection + fill in `{"platform": p, "connected": False}` for each platform NOT in DB
    - Helper `extract_identifier(pc)`: for wordpress, decrypt and extract `site_url` from JSON; for webflow, decrypt and extract `collection_id`; for x/linkedin, decrypt and extract `handle` or `name` field
  - [x] 2.3 Add `POST /clients/{client_id}/connections`:
    ```python
    class ConnectionCreate(BaseModel):
        platform: str  # "wordpress" | "webflow"
        # WordPress fields
        site_url: Optional[str] = None
        credential: Optional[str] = None  # Application Password
        # Webflow fields
        token: Optional[str] = None
        collection_id: Optional[str] = None

    @router.post("/clients/{client_id}/connections", status_code=201)
    async def create_platform_connection(
        client_id: uuid.UUID,
        body: ConnectionCreate,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
    ```
    - Ownership check
    - For `platform="wordpress"`: call `integrations/wordpress.py:validate_credentials(site_url, credential)` — makes `GET {site_url}/wp-json/wp/v2/users/me` with Basic Auth; raise HTTP 400 on failure
    - For `platform="webflow"`: validate token + collection_id are present; no API call here (validation was done via separate endpoint in Task 2.4)
    - Credential serialization: `json.dumps({"site_url": site_url, "credential": credential})` for wordpress; `json.dumps({"token": token, "collection_id": collection_id})` for webflow
    - Call `encrypt_credential(json_string)` from `core/security.py`
    - Call `upsert_connection(db, client_id, platform, encrypted_creds)`
    - Return `{"platform": platform, "connected": True, "account_identifier": ...}`
  - [x] 2.4 Add `GET /clients/{client_id}/webflow/collections?token={token}`:
    ```python
    @router.get("/clients/{client_id}/webflow/collections")
    async def get_webflow_collections(
        client_id: uuid.UUID,
        token: str,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
    ```
    - Ownership check on client
    - Call `integrations/webflow.py:fetch_collections(token)` which calls `GET https://api.webflow.com/v2/sites` then `GET https://api.webflow.com/v2/sites/{site_id}/collections` with `Authorization: Bearer {token}`
    - Return `{"collections": [{"id": "...", "name": "..."}]}` or raise HTTP 400 if Webflow API fails
  - [x] 2.5 Add `DELETE /clients/{client_id}/connections/{platform}`:
    ```python
    @router.delete("/clients/{client_id}/connections/{platform}", status_code=204)
    async def delete_platform_connection(
        client_id: uuid.UUID,
        platform: str,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> None:
    ```
    - Ownership check
    - Call `delete_connection(db, client_id, platform)` — if `False`, raise HTTP 404
    - Return 204 No Content

- [x] Task 3: Create `backend/app/integrations/wordpress.py` (AC: #3, #4)
  - [x] 3.1 Create file with:
    ```python
    import base64
    import httpx
    from app.core.exceptions import PlatformError

    async def validate_credentials(site_url: str, application_password: str) -> str:
        """Validate WordPress credentials. Returns the site display URL on success."""
        credentials = base64.b64encode(f"username:{application_password}".encode()).decode()
        # Note: we use 'admin' as username placeholder — WordPress Application Passwords
        # are tied to specific users; the actual username doesn't matter for validation.
        # The test call uses the app password which encodes the user context.
        url = f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Basic {credentials}"})
        if resp.status_code == 401:
            raise PlatformError("wordpress", 401, "check your Application Password")
        if resp.status_code != 200:
            raise PlatformError("wordpress", resp.status_code, "connection test failed")
        return site_url
    ```
  - [x] 3.2 Note: The `application_password` for WordPress is the raw Application Password from the WP dashboard — it's used in Basic Auth as `username:application_password` (base64 encoded). The actual WP username is embedded in the app password itself; we use a placeholder username since WP validates via the password token. For a more correct implementation, prompt the user for their WP username too — but the AC only requires URL + Application Password, so proceed with placeholder pattern and note it in dev notes.
  - [x] 3.3 Add `PlatformError` to `backend/app/core/exceptions.py` if not present:
    ```python
    class PlatformError(Exception):
        def __init__(self, platform: str, status_code: int, message: str):
            self.platform = platform
            self.status_code = status_code
            self.message = message
            super().__init__(f"{platform} returned {status_code} — {message}")
    ```
  - [x] 3.4 In the router, catch `PlatformError` and convert to HTTP 400 with standard error format

- [x] Task 4: Create `backend/app/integrations/webflow.py` (partial — collections only for this story; full publish in Story 5.3) (AC: #5, #6)
  - [x] 4.1 Create file with:
    ```python
    import httpx
    from app.core.exceptions import PlatformError

    async def fetch_collections(token: str) -> list[dict]:
        """Fetch Webflow CMS collections for the authenticated user's sites."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First get sites
            sites_resp = await client.get(
                "https://api.webflow.com/v2/sites",
                headers={"Authorization": f"Bearer {token}", "accept": "application/json"}
            )
            if sites_resp.status_code != 200:
                raise PlatformError("webflow", sites_resp.status_code, "token validation failed")
            sites = sites_resp.json().get("sites", [])
            if not sites:
                raise PlatformError("webflow", 200, "no Webflow sites found for this token")
            # Use first site
            site_id = sites[0]["id"]
            cols_resp = await client.get(
                f"https://api.webflow.com/v2/sites/{site_id}/collections",
                headers={"Authorization": f"Bearer {token}", "accept": "application/json"}
            )
            if cols_resp.status_code != 200:
                raise PlatformError("webflow", cols_resp.status_code, "collections fetch failed")
            return [{"id": c["id"], "name": c["displayName"]} for c in cols_resp.json().get("collections", [])]
    ```

- [x] Task 5: Create `frontend/app/(app)/clients/[id]/connections/page.tsx` (AC: #1, #9, #10)
  - [x] 5.1 This is a new page that must be created at `frontend/app/(app)/clients/[id]/connections/page.tsx`
  - [x] 5.2 Page is a Server Component that fetches the client name (for heading) then renders `PlatformConnectionsClient` client component:
    ```tsx
    // page.tsx (Server Component)
    import { PlatformConnectionsClient } from '@/components/publishing/PlatformConnectionsClient'
    import { clientsApi } from '@/lib/api'
    import { notFound } from 'next/navigation'

    export default async function PlatformConnectionsPage({
      params,
    }: {
      params: Promise<{ id: string }>
    }) {
      const { id } = await params
      const client = await clientsApi.get(id).catch(() => null)
      if (!client) notFound()
      return (
        <div className="max-w-[720px] mx-auto px-8 py-10">
          <h1 className="font-display text-4xl font-bold text-ink mb-2">Platform Connections</h1>
          <p className="text-graphite text-sm mb-8">{client.name}</p>
          <PlatformConnectionsClient clientId={id} />
        </div>
      )
    }
    ```
  - [x] 5.3 Create `frontend/components/publishing/PlatformConnectionsClient.tsx` as a `"use client"` component — owns all connection state, inline forms, and modal interactions
  - [x] 5.4 Use React Query to fetch connections: `useQuery({ queryKey: ["platform-connections", clientId], queryFn: () => publishingApi.listConnections(clientId) })`
  - [x] 5.5 Skeleton state: render 4 × `<PlatformConnectionCardSkeleton />` while `isLoading` is true (match card height ~100px, use CSS shimmer animation via `animate-pulse bg-border` blocks)
  - [x] 5.6 For each of 4 platforms in order (wordpress, webflow, x, linkedin): render `<PlatformConnectionCard>` component

- [x] Task 6: Create `frontend/components/publishing/PlatformConnectionCard.tsx` (AC: #1, #2, #5, #8, #10)
  - [x] 6.1 Paper Style card spec: `bg-white border border-border rounded-none p-5` (default), connected state adds `border-ink`
  - [x] 6.2 Card layout: platform name (uppercase tracked Inter label), connection status badge, account identifier (if connected), Connect/Disconnect CTA
  - [x] 6.3 Platform icons: use Lucide `Globe` for WordPress, `LayoutGrid` for Webflow (no official icons — use these as placeholders); annotate with platform name label
  - [x] 6.4 Connected state: show green `"Connected"` label (Success color `text-[#2E4F2E]`) + account identifier in Graphite text
  - [x] 6.5 Inline form pattern — when "Connect" is clicked, expand an inline form below the card summary row (do NOT open a modal):
    ```tsx
    {showForm && (
      <div className="mt-4 pt-4 border-t border-border space-y-4">
        {/* WordPress fields or Webflow fields */}
      </div>
    )}
    ```
  - [x] 6.6 WordPress form:
    - Label "WordPress site URL" + `<input type="url" />` (standard Input: `border-b border-ink focus:border-b-2 outline-none bg-transparent py-2`)
    - Label "Application Password" + `<input type="password" />` (same styles)
    - Buttons: "Connect" (primary) + "Cancel" (secondary)
    - On submit: call `publishingApi.createConnection(clientId, { platform: "wordpress", site_url, credential })`
  - [x] 6.7 Webflow form:
    - Label "Webflow API Bearer Token" + text input
    - "Validate token" secondary button → calls `publishingApi.getWebflowCollections(clientId, token)` → populates collection dropdown
    - Collection select dropdown (standard `<select>` styled with bottom-border only)
    - Fallback: if collections fetch fails, show text input for "Webflow Collection ID" with microcopy link
    - "Connect" primary + "Cancel" secondary
  - [x] 6.8 Disconnect confirmation: use existing `Modal.tsx` for the confirm dialog with Danger button
  - [x] 6.9 On successful connect/disconnect: call `queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] })` to refresh

- [x] Task 7: Add `publishingApi` methods to `frontend/lib/api.ts` (AC: #1, #3, #5, #7, #8)
  - [x] 7.1 Add `publishingApi` object:
    ```typescript
    export const publishingApi = {
      listConnections: (clientId: string) =>
        apiFetch<{ items: PlatformConnectionStatus[] }>(`/clients/${clientId}/connections`),
      createConnection: (clientId: string, data: ConnectionCreatePayload) =>
        apiFetch<PlatformConnectionStatus>(`/clients/${clientId}/connections`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
      deleteConnection: (clientId: string, platform: string) =>
        apiFetch<void>(`/clients/${clientId}/connections/${platform}`, { method: "DELETE" }),
      getWebflowCollections: (clientId: string, token: string) =>
        apiFetch<{ collections: { id: string; name: string }[] }>(
          `/clients/${clientId}/webflow/collections?token=${encodeURIComponent(token)}`
        ),
    }
    ```
  - [x] 7.2 Add TypeScript types to `frontend/lib/types.ts`:
    ```typescript
    export interface PlatformConnectionStatus {
      platform: "wordpress" | "webflow" | "x" | "linkedin"
      connected: boolean
      account_identifier?: string
    }

    export interface ConnectionCreatePayload {
      platform: string
      // WordPress
      site_url?: string
      credential?: string
      // Webflow
      token?: string
      collection_id?: string
      // X/LinkedIn (Story 5.2)
      access_token?: string
      refresh_token?: string
      handle?: string
    }
    ```
  - [x] 7.3 Remove or update the existing `campaignsApi` connection check in `approval-panel.tsx` (Story 4.4 added a direct `fetchAPI` call to `/clients/${campaign.client_id}/connections`) — this will now work correctly since the real endpoint exists

- [x] Task 8: Add navigation link to Platform Connections from Client Detail page (AC: #1)
  - [x] 8.1 In `frontend/app/(app)/clients/[id]/page.tsx`, add a "Platform Connections" link/card that navigates to `/clients/{id}/connections`
  - [x] 8.2 Style as a secondary nav link or Card component per Paper Style
  - [x] 8.3 This ensures users can discover the connections page from the Client Detail

- [x] Task 9: Backend tests (AC: #3, #4, #7, #8)
  - [x] 9.1 Create `backend/tests/routers/test_publishing.py`:
    - `test_list_connections_empty` — returns 4 platforms, all not connected
    - `test_list_connections_with_wordpress` — shows connected WordPress with identifier
    - `test_create_wordpress_connection_success` — mocks `validate_credentials`, stores encrypted row
    - `test_create_wordpress_connection_401` — mocks WordPress returning 401, returns HTTP 400
    - `test_create_webflow_connection_success` — stores encrypted Webflow credentials
    - `test_get_webflow_collections` — mocks Webflow API, returns collection list
    - `test_delete_connection` — deletes row, returns 204
    - `test_delete_connection_not_found` — returns 404
    - `test_ownership_check` — other user's client returns 404 on all endpoints
  - [x] 9.2 Use `pytest-asyncio` + `AsyncClient` fixtures from `tests/conftest.py`
  - [x] 9.3 Mock `httpx.AsyncClient` calls to WordPress and Webflow APIs to avoid external calls in tests

- [x] Task 10: Frontend tests (AC: #1, #2, #8, #10)
  - [x] 10.1 Create `frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx`
  - [x] 10.2 Test: renders 4 cards in loading skeleton state
  - [x] 10.3 Test: "Connect" click opens inline WordPress form
  - [x] 10.4 Test: submit WordPress form → calls `publishingApi.createConnection`; on success shows "Connected"
  - [x] 10.5 Test: WordPress 400 error → inline error message shown; form stays open
  - [x] 10.6 Test: "Disconnect" click → confirmation modal opens; confirm → calls `publishingApi.deleteConnection`
  - [x] 10.7 Test: accessibility — all inputs have visible labels; Disconnect dialog has role="dialog"

## Dev Notes

### Paper Style — Platform Connection Cards

Per UX-DR20 and DESIGN.md:
- Default card: `bg-white border border-[#E5E5E5] rounded-none` — no shadow
- Connected state: `border-[#111111]` border upgrade (ink border signals active state)
- No hover shadow on these cards (they are status displays, not clickable rows)
- Connect/Disconnect buttons: "Connect" = Secondary button (`border border-ink px-5 py-2.5 text-sm`); "Disconnect" = Danger button inside confirmation dialog only
- All status text uses Inter label style: `text-xs font-medium uppercase tracking-[0.06em]`
- "Connected" label color: `text-[#2E4F2E]` (Success green) — text only, no badge
- "Not connected" label color: `text-[#555555]` (Graphite)

Per EXPERIENCE.md Component Patterns:
> "Platform connection card — Shows platform name, connection status (connected / not connected), connected account identifier (e.g., '@handle', 'site.com'). 'Connect' CTA opens OAuth popup or inline credential form. 'Disconnect' triggers a confirmation dialog."

For WordPress and Webflow in this story: inline credential form (no popup). X and LinkedIn use OAuth popup (Story 5.2).

### Credential Encryption Architecture

From `architecture.md` Credential Encrypt/Decrypt Pattern:
- Encrypt: ONLY in the router (`publishing.py`) before calling repository — call `encrypt_credential(json.dumps(payload))` from `core/security.py`
- Decrypt: ONLY in `services/publishing.py` immediately before API call (Story 5.3)
- Never pass decrypted credentials across function boundaries
- Never log credential values at any level

`encrypt_credential()` and `decrypt_credential()` already exist in `backend/app/core/security.py` (confirmed via file read — uses AESGCM with `CREDENTIAL_ENCRYPTION_KEY` env var).

### WordPress Application Password Format

The WordPress Application Password from WP dashboard looks like: `xxxx xxxx xxxx xxxx xxxx xxxx` (24 chars with spaces). When used in Basic Auth, it's sent as-is (the spaces are part of the format). The basic auth encoding is: `base64("anyusername:xxxx xxxx xxxx xxxx xxxx xxxx")`.

In practice, WordPress validates the Application Password against the user it was created for — the username in Basic Auth must match. Since we don't prompt for username in the AC, use a simple validation approach: call `GET /wp-json/wp/v2/posts?per_page=1` instead (which requires auth) or use the `Application Password` in a way that allows us to discover the username. Simplest: require username + app password, but AC says only "Application Password" — proceed with a note that the WordPress username will need to be stored too for actual publish calls. For the validation test, use a call that doesn't require knowing the username upfront.

**Decision: store both `username` and `application_password` in the WordPress credential JSON. Add a "WordPress Username" field to the connection form, labeled clearly.** This is required for the `POST /wp-json/wp/v2/posts` calls in Story 5.3. Add it as a third form field; AC says "URL + Application Password" but without username, publishing cannot work.

### Existing Connections Stub — Remove from clients.py

`backend/app/routers/clients.py` currently has a stub `GET /clients/{client_id}/connections` at approximately line 361. This stub returns `{"items": []}`. In this story, the real implementation goes into `publishing.py` router. **Delete the stub from `clients.py` to avoid a duplicate route registration conflict.**

### Publishing Router Prefix

The `publishing.py` router is imported in `main.py` with `prefix=API_PREFIX` (which is `/api/v1`). The router itself currently has `prefix="/publishing"`. This needs to change to `prefix=""` (empty) since the connection routes are under `/clients/{id}/connections` not `/publishing/clients/{id}/connections`. Update `router = APIRouter(prefix="", tags=["publishing"])`.

### React Query Key Pattern (from architecture.md)

```typescript
// Platform connections for a client
["platform-connections", clientId]

// Invalidate after connect/disconnect:
queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] })
```

### Platform Connection Card Accessibility

Per UX-DR16 and EXPERIENCE.md:
- aria-live region on card status updates: wrap the "Connected" / "Not connected" label in `<span aria-live="polite">` so screen readers announce state changes
- Inline forms: each input has `<label htmlFor="...">` with visible text
- "Connect WordPress" button should have descriptive text or aria-label
- Confirmation dialog: `role="dialog"` + `aria-labelledby="disconnect-dialog-heading"` + focus trap + Esc closes (use existing `Modal.tsx`)

### X and LinkedIn Cards — Read-Only Placeholders in This Story

The connections page shows all 4 platform cards. For X and LinkedIn in Story 5.1:
- Show the card with "Connect" button
- Clicking "Connect" for X or LinkedIn shows the message: "OAuth connection setup coming soon." or better: renders an inert button that links to `/clients/{id}/connections#x` (no action) — OR mark X/LinkedIn "Connect" buttons as disabled with tooltip "Connect X via OAuth — fully implemented in Story 5.2"
- **Best approach**: render a placeholder `<button disabled>` for X and LinkedIn with a `title="OAuth setup available in next update"` — this prevents 404 errors if clicked and keeps the UI honest

### Project Structure Notes

**New files:**
```
frontend/app/(app)/clients/[id]/connections/page.tsx
frontend/components/publishing/PlatformConnectionsClient.tsx
frontend/components/publishing/PlatformConnectionCard.tsx
backend/app/db/repositories/platform_connections.py
backend/app/integrations/wordpress.py
backend/app/integrations/webflow.py   (partial — collections only)
backend/tests/routers/test_publishing.py
frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx
```

**Modified files:**
```
backend/app/routers/publishing.py          ← Full implementation (replace stub)
backend/app/routers/clients.py             ← Remove GET /clients/{id}/connections stub
backend/app/core/exceptions.py             ← Add PlatformError class
frontend/lib/api.ts                        ← Add publishingApi
frontend/lib/types.ts                      ← Add PlatformConnectionStatus, ConnectionCreatePayload
frontend/app/(app)/clients/[id]/page.tsx   ← Add Platform Connections navigation link
```

### References

- Story 5.1 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1]
- FR-22: Platform connection setup — AES-256-GCM, credential validation: [Source: _bmad-output/planning-artifacts/epics.md#FR-22]
- UX-DR20: Platform Connection management UI: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR20]
- UX-DR21: Microcopy — error messages name platform + HTTP status + resolution: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR21]
- UX-DR16: Accessibility — modal focus trap, aria-live: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR16]
- Architecture: Credential encrypt/decrypt pattern: [Source: _bmad-output/planning-artifacts/architecture.md#Credential Encrypt/Decrypt Pattern]
- Architecture: Publishing router maps to `/clients/{id}/connections`: [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- Architecture: `platform_connections` repository: [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- EXPERIENCE.md: Platform connection card behavior: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Component Patterns]
- DESIGN.md: Card components, button variants: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Components]
- Architecture: Anti-patterns — business logic in routers, direct DB queries: [Source: _bmad-output/planning-artifacts/architecture.md#Enforcement Guidelines]
- Existing connections stub to remove: [Source: backend/app/routers/clients.py]
- Existing `encrypt_credential()` / `decrypt_credential()`: [Source: backend/app/core/security.py:82-95]
- Webflow CMS API v2: [Source: _bmad-output/planning-artifacts/epics.md#FR-22, Story 5.1 AC #5]
- Story 4.4 connections check stub added to clients.py: [Source: _bmad-output/implementation-artifacts/4-4-approve-reject-campaign.md#Task 8]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Implemented full platform connection CRUD: GET list (4 platforms always returned), POST create with credential validation, GET webflow/collections proxy, DELETE disconnect.
- WordPress form extended with a "WordPress Username" field (required for publish in Story 5.3) beyond the AC's minimum — Dev Notes explicitly calls this out.
- X and LinkedIn cards render as disabled placeholder buttons (per Dev Notes guidance).
- Removed clients.py stub to avoid duplicate route registration.
- `PlatformError` exception class created in `backend/app/core/exceptions.py`.
- Used `Share2` for X icon and `Link2` for LinkedIn (Lucide version lacks `Twitter`/`Linkedin` icons).
- 9 backend tests pass (100%); 15 frontend tests pass (100%); pre-existing test failures are unrelated to this story.

### File List

**New files:**
- `backend/app/core/exceptions.py`
- `backend/app/db/repositories/platform_connections.py`
- `backend/app/integrations/wordpress.py`
- `backend/app/integrations/webflow.py`
- `backend/tests/test_publishing_router.py`
- `frontend/app/(app)/clients/[id]/connections/page.tsx`
- `frontend/components/publishing/PlatformConnectionsClient.tsx`
- `frontend/components/publishing/PlatformConnectionCard.tsx`
- `frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx`

**Modified files:**
- `backend/app/routers/publishing.py`
- `backend/app/routers/clients.py` (removed connections stub)
- `frontend/lib/api.ts` (added publishingApi)
- `frontend/lib/types.ts` (added PlatformConnectionStatus, ConnectionCreatePayload)
- `frontend/components/clients/ClientDetail.tsx` (added Platform Connections section)

### Change Log

- 2026-07-02: Implemented Story 5.1 — Platform Connection Setup (WordPress & Webflow). Created repository, integrations, full publishing router, platform connections page and card components, publishingApi, TypeScript types, navigation link, backend tests (9), frontend tests (15).
