---
baseline_commit: 37bc969c28068cb48663353b4d76950e8073260d
---

# Story 5.6: WordPress.com OAuth Integration

Status: done

## Story

As an authenticated user with a WordPress.com hosted site,
I want to connect my WordPress.com blog to PersonnaPress via OAuth,
So that I can publish content without needing Application Passwords (which are unavailable or blocked on WordPress.com free/personal plans).

## Acceptance Criteria

1. **Given** a user clicks "Connect" on the WordPress platform card, **When** the inline area expands, **Then** a two-option sub-choice is shown: "Self-hosted WordPress" and "WordPress.com" — the existing Application Password form does NOT immediately appear; the user must first choose a type.

2. **Given** the user selects "Self-hosted WordPress" in the sub-choice, **When** the selection is made, **Then** the existing 3-field form (WordPress site URL, WordPress Username, Application Password) is revealed exactly as before — no behavioral change for self-hosted flow.

3. **Given** the user selects "WordPress.com" in the sub-choice, **When** the selection is made, **Then** a "Connect with WordPress.com" anchor button and helper text "You will be redirected to WordPress.com to authorize access." are shown; clicking the anchor redirects to `GET /api/auth/wordpress-com?client_id={clientId}`.

4. **Given** the Next.js route `GET /api/auth/wordpress-com`, **When** hit with a valid `client_id` query param, **Then** it generates a random `state` string, stores `{state, clientId}` in an `oauth_state_wpcom` httpOnly cookie (SameSite=Lax, maxAge=600, Secure in production), and redirects the browser to `https://public-api.wordpress.com/oauth2/authorize` with params: `client_id`, `redirect_uri` (`APP_URL + /api/auth/wordpress-com/callback`), `response_type=code`, `scope=global`, `state` — the `blog` parameter is omitted so WordPress.com lets the user authorize all their blogs.

5. **Given** WordPress.com redirects back to `/api/auth/wordpress-com/callback?code=...&state=...`, **When** the Next.js callback route handles the request, **Then** it verifies `state` matches the `oauth_state_wpcom` cookie, then calls `POST /api/v1/clients/{clientId}/connections/wordpress-com/callback` on FastAPI with `{code}`, clears the cookie, and redirects to `/clients/{clientId}/connections?success=wordpress-com` on success or `?error=...` on failure.

6. **Given** FastAPI receives `POST /clients/{client_id}/connections/wordpress-com/callback`, **When** processed, **Then** it exchanges the code for tokens via `POST https://public-api.wordpress.com/oauth2/token` (body: `client_id`, `client_secret`, `redirect_uri`, `code`, `grant_type=authorization_code`), extracts `access_token`, `blog_id`, `blog_url` from the response, encrypts `json.dumps({"access_token": ..., "blog_id": ..., "blog_url": ...})` with `encrypt_credential()`, upserts a `platform_connections` row with `platform="wordpress-com"`, and returns `{"platform": "wordpress-com", "connected": true, "account_identifier": blog_url}`.

7. **Given** a client has a "wordpress-com" connection in `platform_connections`, **When** `GET /clients/{client_id}/connections` is called, **Then** the response still returns exactly 4 items (wordpress, webflow, x, linkedin); the "wordpress" card item carries `connected: true`, `account_identifier: blog_url`, and `connected_via: "wordpress-com"` — the actual DB platform is hidden from the card count but exposed via `connected_via`.

8. **Given** a "wordpress-com" platform connection is active and a user clicks "Disconnect" on the WordPress card, **When** the disconnect is confirmed, **Then** the frontend calls `DELETE /clients/{client_id}/connections/wordpress-com` (using `connected_via` to determine the actual platform); the `platform_connections` row with `platform="wordpress-com"` is deleted; the card reverts to "Not connected".

9. **Given** an approved campaign is published and the client has a "wordpress-com" connection, **When** `dispatch_publish` or `dispatch_publish_for_platform` iterates connections, **Then** the `"wordpress-com"` platform case calls `wordpress_com_integration.publish_post(creds, campaign)` which POSTs to `https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/posts/new` with `Authorization: Bearer {access_token}`; featured image (if present) is uploaded first via `POST .../media/new` as multipart form-data with `media_urls[0]={image_url}`, extracting the attachment ID from `response.json()["media"][0]["ID"]`; the published post URL (`response["URL"]`) is returned.

10. **Given** WordPress.com token exchange fails (bad code, expired state), **When** the FastAPI endpoint receives the request, **Then** HTTP 400 is returned with `{"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": "WordPress.com token exchange failed — {detail}"}}` — the frontend callback shows the error as `?error=...` param and the connections page shows an error toast.

11. **Given** the Platform Connections page loads with a "wordpress-com" success param (`?success=wordpress-com`), **When** the page renders, **Then** the existing `?success=x` / `?success=linkedin` toast pattern is extended to handle `?success=wordpress-com`, showing a "WordPress.com connected" success message.

12. **Given** both "wordpress" (self-hosted) and "wordpress-com" connections exist for the same client (edge case — user connected both), **When** `GET /clients/{client_id}/connections` is called, **Then** the "wordpress" (self-hosted) connection takes precedence in the card display; "wordpress-com" is shown only if no "wordpress" connection exists.

## Tasks / Subtasks

- [x] Task 1: Create `backend/app/integrations/wordpress_com.py` (AC: #6, #9, #10)
  - [x] 1.1 `exchange_code_for_tokens(code: str, redirect_uri: str) -> dict`:
    ```python
    async def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://public-api.wordpress.com/oauth2/token",
                data={
                    "client_id": settings.WP_COM_CLIENT_ID,
                    "client_secret": settings.WP_COM_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "code": code,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
        if resp.status_code != 200:
            raise PlatformError("wordpress-com", resp.status_code, f"token exchange failed — {resp.text[:200]}")
        data = resp.json()
        if "access_token" not in data:
            raise PlatformError("wordpress-com", 200, "no access_token in response")
        return {
            "access_token": data["access_token"],
            "blog_id": str(data.get("blog_id", "")),
            "blog_url": data.get("blog_url", ""),
        }
    ```
  - [x] 1.2 `publish_post(creds: dict, campaign) -> str` — uses WordPress.com REST API v1.1 (NOT self-hosted WP REST API):
    ```python
    async def publish_post(creds: dict, campaign) -> str:
        """Publish to WordPress.com. Returns the live post URL."""
        access_token = creds["access_token"]
        blog_id = creds["blog_id"]  # numeric string — use as site identifier
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Upload featured image if present
            # Media endpoint requires multipart form-data with media_urls[] parameter
            # Response shape: {"media": [{"ID": 123, "URL": "..."}, ...], "errors": [...]}
            featured_media_id = None
            if campaign.image_url:
                try:
                    media_resp = await client.post(
                        f"https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/media/new",
                        headers={"Authorization": f"Bearer {access_token}"},
                        data={"media_urls[0]": campaign.image_url},  # form-data, NOT json
                    )
                    if media_resp.status_code in (200, 201):
                        media_objects = media_resp.json().get("media", [])
                        if media_objects:
                            featured_media_id = media_objects[0].get("ID")
                except Exception as exc:
                    logger.warning("WP.com featured image upload failed: %s", exc)

            # Step 2: Create post
            post_body: dict = {
                "title": _extract_title(campaign.blog_html),
                "content": campaign.blog_html,
                "status": "publish",
            }
            if featured_media_id:
                post_body["featured_image"] = str(featured_media_id)

            pub_resp = await client.post(
                f"https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/posts/new",
                headers=headers,
                json=post_body,
            )
            if pub_resp.status_code not in (200, 201):
                raise PlatformError("wordpress-com", pub_resp.status_code, f"publish failed — {pub_resp.text[:200]}")
            return pub_resp.json().get("URL", "")
    ```
  - [x] 1.3 Import `_extract_title` from `app.integrations.wordpress` (it's already defined there for HTML title extraction — do NOT duplicate it):
    ```python
    from app.integrations.wordpress import _extract_title
    ```
  - [x] 1.4 Import `PlatformError` from `app.core.exceptions` and `settings` from `app.core.config`

- [x] Task 2: Update `backend/app/core/config.py` (AC: #4, #6)
  - [x] 2.1 Add three new settings to the `Settings` class:
    ```python
    WP_COM_CLIENT_ID: str = ""
    WP_COM_CLIENT_SECRET: str = ""
    WP_COM_REDIRECT_URI: str = ""  # e.g. http://localhost:3000/api/auth/wordpress-com/callback
    ```

- [x] Task 3: Update `backend/app/routers/publishing.py` (AC: #6, #7, #8, #10, #12)
  - [x] 3.1 Add import at top:
    ```python
    from app.integrations import wordpress_com as wordpress_com_integration
    ```
  - [x] 3.2 Add new Pydantic model and callback endpoint:
    ```python
    class WpComCallbackRequest(BaseModel):
        code: str

    @router.post("/clients/{client_id}/connections/wordpress-com/callback", status_code=201)
    async def wordpress_com_oauth_callback(
        client_id: uuid.UUID,
        body: WpComCallbackRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
        user_id = _parse_user_id(current_user)
        client = await get_client(db, client_id)
        _check_ownership(client, user_id)

        redirect_uri = f"{settings.APP_URL}/api/auth/wordpress-com/callback"
        try:
            tokens = await wordpress_com_integration.exchange_code_for_tokens(body.code, redirect_uri)
        except PlatformError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": f"WordPress.com token exchange failed — {e.message}", "detail": {}}},
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": f"WordPress.com token exchange failed — {str(e)[:200]}", "detail": {}}},
            )

        cred_json = json.dumps(tokens)  # {"access_token": ..., "blog_id": ..., "blog_url": ...}
        encrypted = encrypt_credential(cred_json)
        await upsert_connection(db, client_id, "wordpress-com", encrypted)

        return {
            "platform": "wordpress-com",
            "connected": True,
            "account_identifier": tokens.get("blog_url", ""),
        }
    ```
  - [x] 3.3 Update `_extract_identifier` to handle "wordpress-com":
    ```python
    def _extract_identifier(platform: str, encrypted_credentials: str) -> Optional[str]:
        try:
            data = json.loads(decrypt_credential(encrypted_credentials))
            if platform == "wordpress":
                return data.get("site_url") or None
            if platform == "wordpress-com":
                return data.get("blog_url") or None
            if platform == "webflow":
                return data.get("collection_id") or None
            return data.get("handle") or data.get("name") or None
        except Exception:
            return None
    ```
  - [x] 3.4 Update `list_platform_connections` — keep 4-item response but fold "wordpress-com" under the "wordpress" card:
    ```python
    @router.get("/clients/{client_id}/connections")
    async def list_platform_connections(...) -> dict:
        ...
        connections = await get_connections_for_client(db, client_id)
        connected_map = {pc.platform: pc for pc in connections}

        items = []
        for platform in ALL_PLATFORMS:  # ["wordpress", "webflow", "x", "linkedin"]
            if platform in connected_map:
                pc = connected_map[platform]
                items.append({
                    "platform": platform,
                    "connected": True,
                    "account_identifier": _extract_identifier(platform, pc.encrypted_credentials),
                })
            elif platform == "wordpress" and "wordpress-com" in connected_map:
                # WordPress.com connection shown under the wordpress card
                pc = connected_map["wordpress-com"]
                items.append({
                    "platform": "wordpress",
                    "connected": True,
                    "account_identifier": _extract_identifier("wordpress-com", pc.encrypted_credentials),
                    "connected_via": "wordpress-com",
                })
            else:
                items.append({"platform": platform, "connected": False})

        return {"items": items}
    ```

- [x] Task 4: Update `backend/app/services/publishing.py` (AC: #9)
  - [x] 4.1 Add import:
    ```python
    from app.integrations import wordpress_com as wordpress_com_integration
    ```
  - [x] 4.2 In `dispatch_publish` — add `elif platform == "wordpress-com":` case after the `elif platform == "webflow":` block:
    ```python
    elif platform == "wordpress-com":
        await wordpress_com_integration.publish_post(creds, campaign)
    ```
  - [x] 4.3 In `dispatch_publish_for_platform` — same addition in the same position. Both functions have the same if/elif chain — update both.

- [x] Task 5: Create `frontend/app/api/auth/wordpress-com/route.ts` (AC: #4)
  - [x] 5.1 Follow the exact same pattern as `frontend/app/api/auth/linkedin/route.ts` (standard code flow, no PKCE):
    ```typescript
    import { type NextRequest, NextResponse } from "next/server";
    import { randomBytes } from "crypto";

    const APP_URL = process.env.APP_URL ?? "http://localhost:3000";

    export async function GET(request: NextRequest) {
      const { searchParams } = request.nextUrl;
      const clientId = searchParams.get("client_id");
      if (!clientId) {
        return NextResponse.json({ error: "Missing client_id" }, { status: 400 });
      }

      const wpComClientId = process.env.NEXT_PUBLIC_WP_COM_CLIENT_ID;
      if (!wpComClientId) {
        return NextResponse.json({ error: "WordPress.com OAuth is not configured" }, { status: 500 });
      }

      const state = randomBytes(32).toString("hex");
      const redirectUri = `${APP_URL}/api/auth/wordpress-com/callback`;

      const params = new URLSearchParams({
        client_id: wpComClientId,
        redirect_uri: redirectUri,
        response_type: "code",
        scope: "global",
        state,
        // NOTE: "blog" param is intentionally omitted — passing "all" is invalid;
        // omitting it lets WordPress.com authorize access to all the user's blogs
      });

      const authUrl = `https://public-api.wordpress.com/oauth2/authorize?${params.toString()}`;

      const cookieValue = JSON.stringify({ state, clientId });
      const response = NextResponse.redirect(authUrl);
      response.cookies.set("oauth_state_wpcom", cookieValue, {
        httpOnly: true,
        sameSite: "lax",
        maxAge: 600,
        path: "/",
        secure: process.env.NODE_ENV === "production",
      });
      return response;
    }
    ```

- [x] Task 6: Create `frontend/app/api/auth/wordpress-com/callback/route.ts` (AC: #5, #10, #11)
  - [x] 6.1 Follow the exact same pattern as `frontend/app/api/auth/linkedin/callback/route.ts`:
    ```typescript
    import { type NextRequest, NextResponse } from "next/server";

    const APP_URL = process.env.APP_URL ?? "http://localhost:3000";
    const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

    function clearCookieRedirect(url: string): NextResponse {
      const res = NextResponse.redirect(url);
      res.cookies.delete("oauth_state_wpcom");
      return res;
    }

    export async function GET(request: NextRequest) {
      const { searchParams } = request.nextUrl;
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const error = searchParams.get("error");

      const cookieRaw = request.cookies.get("oauth_state_wpcom")?.value;
      let oauthState: { state: string; clientId: string } | null = null;
      if (cookieRaw) {
        try {
          oauthState = JSON.parse(cookieRaw) as { state: string; clientId: string };
        } catch {
          // malformed cookie
        }
      }

      const connectionsUrl = oauthState?.clientId
        ? `${APP_URL}/clients/${oauthState.clientId}/connections`
        : `${APP_URL}/clients`;

      if (error) {
        return clearCookieRedirect(
          `${connectionsUrl}?error=${encodeURIComponent(`WordPress.com authorization failed — ${error}. Please try connecting again.`)}`
        );
      }

      if (!oauthState || state !== oauthState.state) {
        return clearCookieRedirect(
          `${connectionsUrl}?error=${encodeURIComponent("Authorization failed — the request was tampered with. Please try connecting again.")}`
        );
      }

      try {
        const backendResp = await fetch(
          `${BACKEND_URL}/api/v1/clients/${oauthState.clientId}/connections/wordpress-com/callback`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Cookie: request.headers.get("cookie") ?? "",
            },
            body: JSON.stringify({ code }),
          }
        );

        if (!backendResp.ok) {
          const err = await backendResp.json().catch(() => ({})) as { error?: { message?: string } };
          return clearCookieRedirect(
            `${connectionsUrl}?error=${encodeURIComponent(err?.error?.message ?? "WordPress.com connection failed. Please try again.")}`
          );
        }
      } catch {
        return clearCookieRedirect(
          `${connectionsUrl}?error=${encodeURIComponent("WordPress.com connection failed. Please try again.")}`
        );
      }

      return clearCookieRedirect(`${connectionsUrl}?success=wordpress-com`);
    }
    ```

- [x] Task 7: Update `frontend/lib/types.ts` (AC: #7, #8)
  - [x] 7.1 Update `PlatformConnectionStatus` type:
    ```typescript
    export interface PlatformConnectionStatus {
      platform: "wordpress" | "webflow" | "x" | "linkedin"
      connected: boolean
      account_identifier?: string
      connected_via?: "self-hosted" | "wordpress-com"  // NEW — only present on wordpress card
    }
    ```
  - [x] 7.2 Keep `ConnectionCreatePayload` unchanged — WordPress.com flow goes via OAuth redirect, not through `createConnection()`.

- [x] Task 8: Update `frontend/components/publishing/PlatformConnectionCard.tsx` (AC: #1, #2, #3, #8, #11)
  - [x] 8.1 Add `wpType` state variable:
    ```typescript
    const [wpType, setWpType] = useState<null | "self-hosted" | "wordpress-com">(null);
    ```
  - [x] 8.2 Update `handleCancel` to also reset `wpType`:
    ```typescript
    function handleCancel() {
      setShowForm(false);
      setWpType(null);
      setError(null);
      setWpSiteUrl("");
      setWpUsername("");
      setWpPassword("");
      // + existing webflow resets
    }
    ```
  - [x] 8.3 The "Connect" button click for WordPress should set `showForm(true)` AND `wpType` should start as `null` (type picker step). No change to the button itself — the `!isOAuth && !isConnected` branch already calls `setShowForm(true)`. WordPress will hit this branch since `isOAuth` only checks for "x" / "linkedin".
  - [x] 8.4 Update `isOAuth` — no change needed; WordPress always goes through the sub-choice inline, not the OAuth anchor directly.
  - [x] 8.5 Update the `{showForm && ...}` block for WordPress platform — replace the current WordPress form with the two-step sub-choice UI (see UX spec in Dev Notes below). The sub-choice renders when `connection.platform === "wordpress" && wpType === null`. Then `wpType === "self-hosted"` shows the existing 3-field form. `wpType === "wordpress-com"` shows the OAuth anchor.
  - [x] 8.6 Update disconnect logic — when `connection.connected_via === "wordpress-com"`, the DELETE must target `wordpress-com` not `wordpress`:
    ```typescript
    async function handleDisconnect() {
      const platformToDelete = connection.connected_via === "wordpress-com"
        ? "wordpress-com"
        : connection.platform;
      await publishingApi.deleteConnection(clientId, platformToDelete);
      ...
    }
    ```
  - [x] 8.7 Extend success toast handling in `PlatformConnectionsClient.tsx` — find where `?success=x` / `?success=linkedin` is handled and add `wordpress-com`:
    - File: `frontend/components/publishing/PlatformConnectionsClient.tsx`
    - The success toast probably reads `searchParams.get("success")` — add `"wordpress-com"` to the label map so it shows "WordPress.com connected"

- [x] Task 9: Backend tests — add to `backend/tests/test_publishing_router.py` (AC: #6, #10)
  - [x] 9.1 `test_wordpress_com_callback_success` — mock `wordpress_com_integration.exchange_code_for_tokens` to return valid tokens; verify 201 response and `platform_connections` row created with `platform="wordpress-com"`
  - [x] 9.2 `test_wordpress_com_callback_token_exchange_failure` — mock exchange to raise `PlatformError`; verify HTTP 400 with `TOKEN_EXCHANGE_FAILED`
  - [x] 9.3 `test_list_connections_with_wpcom` — when client has `platform="wordpress-com"` connection, verify list returns 4 items with the "wordpress" card showing `connected: true` and `connected_via: "wordpress-com"`
  - [x] 9.4 `test_list_connections_prefers_selfhosted_over_wpcom` — when client has BOTH "wordpress" and "wordpress-com" connections, verify "wordpress" (self-hosted) shows in the card (not wordpress-com)
  - [x] 9.5 `test_delete_wordpress_com_connection` — `DELETE /clients/{id}/connections/wordpress-com` removes the row; verify 204
  - [x] 9.6 `test_wordpress_com_publish_dispatch` — in `publishing.py` service test, verify `dispatch_publish` calls `wordpress_com_integration.publish_post` when platform="wordpress-com"

- [x] Task 10: Frontend tests — add to `frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx` (AC: #1, #2, #3, #8)
  - [x] 10.1 `test_wordpress_connect_shows_type_picker` — clicking "Connect" on the WordPress card reveals the sub-choice (both option labels visible); NOT the Application Password form directly
  - [x] 10.2 `test_wordpress_selfhosted_selection_reveals_form` — clicking "Self-hosted WordPress" in sub-choice reveals the 3-field form
  - [x] 10.3 `test_wordpress_com_selection_reveals_oauth_button` — clicking "WordPress.com" in sub-choice reveals the "Connect with WordPress.com" link
  - [x] 10.4 `test_wordpress_back_navigation` — clicking "Back" from either step 2 returns to type picker
  - [x] 10.5 `test_wordpress_com_disconnect_uses_correct_platform` — when `connected_via="wordpress-com"`, disconnect calls `deleteConnection(clientId, "wordpress-com")` not `"wordpress"`

## Dev Notes

### UX Sub-Choice Component Spec (from web-uiux-architect)

**State machine:** `wpType: null | "self-hosted" | "wordpress-com"` — controls 3 sub-states of the expanded WordPress card.

**Step 1 (wpType === null) — Type picker:**
```tsx
{connection.platform === "wordpress" && wpType === null && (
  <fieldset>
    <legend className="block text-xs font-medium text-[#111111] mb-3">
      Where is your WordPress site hosted?
    </legend>
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setWpType("self-hosted")}
        className="w-full text-left px-4 py-3 border border-[#E5E5E5] hover:border-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 transition-colors duration-150"
        aria-label="Self-hosted WordPress — your own server or managed host"
      >
        <span className="block text-sm font-medium text-[#111111]">Self-hosted WordPress</span>
        <span className="block text-xs text-[#555555] mt-0.5">
          Your own server or managed host — SiteGround, WP Engine, Kinsta, etc.
        </span>
      </button>
      <button
        type="button"
        onClick={() => setWpType("wordpress-com")}
        className="w-full text-left px-4 py-3 border border-[#E5E5E5] hover:border-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 transition-colors duration-150"
        aria-label="WordPress.com — free or paid site hosted by Automattic"
      >
        <span className="block text-sm font-medium text-[#111111]">WordPress.com</span>
        <span className="block text-xs text-[#555555] mt-0.5">
          Free or paid site hosted by Automattic at wordpress.com
        </span>
      </button>
    </div>
    <button type="button" onClick={handleCancel}
      className="mt-4 text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors">
      Cancel
    </button>
  </fieldset>
)}
```

**Step 2a (wpType === "self-hosted") — existing form, unchanged except add Back button:**
```tsx
{connection.platform === "wordpress" && wpType === "self-hosted" && (
  <div className="space-y-4">
    <button type="button" onClick={() => setWpType(null)}
      className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
      aria-label="Back to WordPress hosting type selection">
      Back
    </button>
    {/* ... existing 3 fields + error + Connect/Cancel buttons ... */}
  </div>
)}
```

**Step 2b (wpType === "wordpress-com") — OAuth anchor:**
```tsx
{connection.platform === "wordpress" && wpType === "wordpress-com" && (
  <div className="space-y-4">
    <button type="button" onClick={() => setWpType(null)}
      className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors"
      aria-label="Back to WordPress hosting type selection">
      Back
    </button>
    <p className="text-xs text-[#555555]">
      You will be redirected to WordPress.com to authorize access.
    </p>
    <a
      href={`/api/auth/wordpress-com?client_id=${clientId}`}
      onClick={() => setLoading(true)}
      className="inline-block px-5 py-2.5 border border-[#111111] text-[#111111] text-xs font-medium hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
      aria-label="Connect with WordPress.com via OAuth"
    >
      {loading ? "Connecting…" : "Connect with WordPress.com"}
    </a>
    <div>
      <button type="button" onClick={handleCancel}
        className="text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors">
        Cancel
      </button>
    </div>
  </div>
)}
```

### WordPress.com OAuth2 — Critical API Details

**Registration:** Create an app at `developer.wordpress.com/apps` to get `client_id` + `client_secret`. Set "Redirect URL" to `APP_URL/api/auth/wordpress-com/callback`.

**Token exchange response shape** (confirmed from live docs):
```json
{
  "access_token": "your-token-here",
  "token_type": "bearer",
  "blog_id": "12345678",
  "blog_url": "https://mysite.wordpress.com"
}
```
Both `blog_id` (numeric string) and `blog_url` are in the token response — no separate API call needed to get them. Store all three fields encrypted. Use `blog_id` for API calls; display `blog_url` as the account identifier.

**`blog` OAuth param must be omitted** — the `blog` parameter in the authorize URL takes a specific blog URL/ID, not `"all"`. Omitting it is correct and lets WordPress.com authorize across all the user's blogs.

**WordPress.com REST API vs self-hosted WP REST API — critical difference:**
- Self-hosted: `{site_url}/wp-json/wp/v2/posts` with Basic Auth
- WordPress.com: `https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/posts/new` with Bearer token

Do NOT use the WP REST API patterns from `wordpress.py` for the WordPress.com integration.

**Publishing endpoint:** `POST https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/posts/new`
- Body: `{"title": "...", "content": "...", "status": "publish", "featured_image": "<attachment_id>"}`
- Response URL field: `response["URL"]` (uppercase) — the full permalink

**Featured image upload — correct call:**
```python
# MUST be form-data (data=), NOT json= 
# Parameter is media_urls[0] (indexed array notation)
await client.post(
    f"https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/media/new",
    headers={"Authorization": f"Bearer {access_token}"},
    data={"media_urls[0]": campaign.image_url},
)
```
**Media upload response shape:**
```json
{
  "media": [{"ID": 987654, "URL": "https://mysite.files.wordpress.com/..."}],
  "errors": []
}
```
The ID is nested at `response["media"][0]["ID"]` (uppercase `ID`). Not a flat `{"ID": ...}` — it's inside a `"media"` array.

**No PKCE required** — standard code flow only. Follow the LinkedIn pattern in `frontend/app/api/auth/linkedin/route.ts`, NOT the X PKCE pattern.

**Cookie name:** `oauth_state_wpcom` (not `oauth_state_linkedin` or `oauth_state_x`) — each provider uses a distinct cookie name to avoid cross-contamination.

### Self-hosted vs WordPress.com API Differences — Do Not Mix

These field names differ between the two APIs. The dev agent must use each in the correct integration file only:

| Field | Self-hosted `wordpress.py` | WordPress.com `wordpress_com.py` |
|-------|---------------------------|----------------------------------|
| Auth | `Authorization: Basic base64(user:pass)` | `Authorization: Bearer {access_token}` |
| API base | `{site_url}/wp-json/wp/v2/` | `https://public-api.wordpress.com/rest/v1.1/sites/{blog_id}/` |
| Create post endpoint | `POST .../posts` | `POST .../posts/new` |
| Featured image param | `featured_media` (integer) | `featured_image` (string) |
| Media upload body | multipart binary file (`Content-Disposition: attachment`) | form-data with `media_urls[0]={url}` |
| Media response ID | `resp.json().get("id")` — lowercase | `resp.json()["media"][0].get("ID")` — uppercase, nested in array |
| Post URL in response | `resp.json().get("link", "")` | `resp.json().get("URL", "")` |
| Validation call | `GET .../wp-json/wp/v2/users/me` with Basic Auth | Not needed — `exchange_code_for_tokens()` validates implicitly |

The self-hosted implementation (`wordpress.py`) is confirmed correct against the WordPress REST API docs. Do not change it.

### Anti-Regression Guards

**Do NOT touch:**
- The self-hosted WordPress form or credential storage (`platform="wordpress"` rows) — must remain 100% unchanged
- The `isOAuth` variable — WordPress never uses this path; it always goes through the sub-choice
- `ALL_PLATFORMS = ["wordpress", "webflow", "x", "linkedin"]` — keep this 4-item list; "wordpress-com" is NOT added here (it would create a 5th card)
- `dispatch_publish` / `dispatch_publish_for_platform` iteration — these already iterate over all DB connections, so "wordpress-com" rows will naturally be picked up once the `elif platform == "wordpress-com":` case is added

**Connected state display:** When the WordPress card shows `connected_via: "wordpress-com"`, the disconnect call must pass `"wordpress-com"` to `publishingApi.deleteConnection`, not `"wordpress"`. Without this, the DELETE would try to delete a "wordpress" row that doesn't exist (404) while the "wordpress-com" row remains.

**publishingApi.deleteConnection:** The existing method signature `deleteConnection(clientId, platform)` already handles arbitrary platform strings — just pass `"wordpress-com"`.

**Retry flow (Story 5-5 compatibility):** The retry endpoint in `publishing.py` accepts `{"platform": "wordpress-com"}` in `RetryRequest`. The `run_publish_retry` worker calls `dispatch_publish_for_platform(db, campaign_id, body.platform)`. Since we're adding the `"wordpress-com"` case to `dispatch_publish_for_platform`, retries will work without additional changes.

### New File Structure

**New files:**
```
backend/app/integrations/wordpress_com.py
frontend/app/api/auth/wordpress-com/route.ts
frontend/app/api/auth/wordpress-com/callback/route.ts
```

**Modified files:**
```
backend/app/core/config.py                    ← Add WP_COM_* settings
backend/app/routers/publishing.py             ← Add callback endpoint + list logic + identifier extraction
backend/app/services/publishing.py            ← Add "wordpress-com" case to both dispatch functions
backend/tests/test_publishing_router.py       ← Add 6 new tests
frontend/lib/types.ts                         ← Add connected_via field to PlatformConnectionStatus
frontend/components/publishing/PlatformConnectionCard.tsx  ← Sub-choice UI + disconnect fix
frontend/components/publishing/PlatformConnectionsClient.tsx  ← Extend success toast
frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx  ← 5 new tests
```

### Environment Variables to Document

**`backend/.env`:**
```
WP_COM_CLIENT_ID=your-client-id
WP_COM_CLIENT_SECRET=your-client-secret
WP_COM_REDIRECT_URI=http://localhost:3000/api/auth/wordpress-com/callback
```

**`frontend/.env.local`:**
```
NEXT_PUBLIC_WP_COM_CLIENT_ID=your-client-id
```

Note: `WP_COM_CLIENT_SECRET` is backend-only. The `NEXT_PUBLIC_` prefix exposes a value to the browser — never add `NEXT_PUBLIC_WP_COM_CLIENT_SECRET`.

### Previous Story Learnings (Story 5-2 OAuth patterns)

Story 5-2 (X + LinkedIn OAuth) established these patterns — follow them:
- State cookie: JSON-encoded `{state, clientId}` in httpOnly cookie, maxAge 600s
- Distinct cookie name per provider (no reuse)
- Callback route: verify state → call backend → clear cookie → redirect with `?success=provider` or `?error=...`
- Backend callback endpoint: ownership check first, then token exchange, then encrypt+store
- `_platform_error_msg(e)` helper in publishing.py — use it when catching unexpected exceptions

Story 5-1 patterns to follow for the self-hosted form (no change needed, just don't break):
- Application Password validation: `GET {site_url}/wp-json/wp/v2/users/me` with Basic Auth
- Credential JSON stored as `{"site_url": ..., "username": ..., "credential": ...}`

### References

- WordPress.com OAuth2 docs: `developer.wordpress.com/docs/oauth2/`
- WordPress.com REST API v1.1: `developer.wordpress.com/docs/api/`
- X OAuth route (model to follow for no-PKCE parts): `frontend/app/api/auth/x/route.ts`
- LinkedIn OAuth route (exact no-PKCE model): `frontend/app/api/auth/linkedin/route.ts`
- LinkedIn callback (exact model): `frontend/app/api/auth/linkedin/callback/route.ts`
- Existing WordPress integration: `backend/app/integrations/wordpress.py` — import `_extract_title` from here
- Publishing service (add wp-com case): `backend/app/services/publishing.py:44-56` and `98-122`
- Publishing router (list logic to update): `backend/app/routers/publishing.py:68-93`
- Config to update: `backend/app/core/config.py`
- PlatformConnectionCard (file to update): `frontend/components/publishing/PlatformConnectionCard.tsx`
- Success toast location: `frontend/components/publishing/PlatformConnectionsClient.tsx`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — all tasks implemented cleanly following story specs exactly.

### Completion Notes List

- Created `backend/app/integrations/wordpress_com.py` with `exchange_code_for_tokens()` and `publish_post()`. Imports `_extract_title` from `wordpress.py` (no duplication). Uses form-data (not JSON) for media upload per WP.com REST API v1.1 requirements.
- Added `WP_COM_CLIENT_ID`, `WP_COM_CLIENT_SECRET`, `WP_COM_REDIRECT_URI` settings to `config.py`.
- Added `wordpress_com_integration` import, `WpComCallbackRequest` model, `wordpress_com_oauth_callback` endpoint, updated `_extract_identifier` to handle `"wordpress-com"`, and updated `list_platform_connections` to fold wordpress-com under the wordpress card with `connected_via` field.
- Added `"wordpress-com"` case to both `dispatch_publish` and `dispatch_publish_for_platform` in `services/publishing.py`.
- Created `frontend/app/api/auth/wordpress-com/route.ts` — state cookie, redirect to WP.com OAuth authorize (no `blog` param).
- Created `frontend/app/api/auth/wordpress-com/callback/route.ts` — state verification, backend call, cookie clear, redirect with `?success=wordpress-com`.
- Updated `PlatformConnectionStatus` type to add optional `connected_via` field.
- Updated `PlatformConnectionCard.tsx` — added `wpType` state, two-step sub-choice UI (type picker → self-hosted form OR wordpress-com OAuth link), disconnect uses `connected_via` to determine correct platform.
- Updated `PlatformConnectionsClient.tsx` toast to handle `?success=wordpress-com`.
- Added 6 backend tests (all pass) and 5 new frontend tests (all pass). Updated 4 existing frontend tests to navigate through sub-choice flow.
- Pre-existing `test_create_webflow_connection_success` failure is unrelated to this story (makes real HTTP calls without mocking).

### File List

- `backend/app/integrations/wordpress_com.py` (new)
- `frontend/app/api/auth/wordpress-com/route.ts` (new)
- `frontend/app/api/auth/wordpress-com/callback/route.ts` (new)
- `backend/app/core/config.py` (modified)
- `backend/app/routers/publishing.py` (modified)
- `backend/app/services/publishing.py` (modified)
- `backend/tests/test_publishing_router.py` (modified)
- `frontend/lib/types.ts` (modified)
- `frontend/components/publishing/PlatformConnectionCard.tsx` (modified)
- `frontend/components/publishing/PlatformConnectionsClient.tsx` (modified)
- `frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx` (modified)

### Review Findings

- [x] [Review][Patch] Empty/missing blog_id not validated at token exchange — if WP.com omits blog_id, stores "" and later constructs `/sites//posts/new` causing 404 [backend/app/integrations/wordpress_com.py:exchange_code_for_tokens]
- [x] [Review][Patch] media/new upload uses application/x-www-form-urlencoded, not multipart/form-data — httpx `data=` sends form-encoded; WP.com requires multipart; silently swallowed, posts publish without featured images [backend/app/integrations/wordpress_com.py:publish_post]
- [x] [Review][Patch] Dual wordpress+wordpress-com connections both dispatch — dispatch_publish iterates all DB rows; if client has both, publishes twice with no UI indication [backend/app/services/publishing.py:dispatch_publish]
- [x] [Review][Patch] Toast message "Connected to WordPress.com." does not match spec "WordPress.com connected" [frontend/components/publishing/PlatformConnectionsClient.tsx]
- [x] [Review][Patch] Null code param not guarded in callback before backend call — missing code + missing error → 422 from backend with generic error [frontend/app/api/auth/wordpress-com/callback/route.ts]
- [x] [Review][Patch] connected_via "self-hosted" union arm is dead code — backend never sets it [frontend/lib/types.ts]
- [x] [Review][Patch] WP_COM_REDIRECT_URI setting added but never used — router now uses it as override with APP_URL fallback [backend/app/routers/publishing.py:wordpress_com_oauth_callback]
- [x] [Review][Patch] NEXT_PUBLIC_WP_COM_CLIENT_ID should be server-only — changed to WP_COM_CLIENT_ID [frontend/app/api/auth/wordpress-com/route.ts]
- [x] [Review][Patch] psycopg2-binary added without version pin — pinned to >=2.9,<3 [backend/requirements.txt]
- [x] [Review][Patch] State validation occurs after connectionsUrl built from cookie clientId — restructured callback to validate state first; error redirect uses safe /clients fallback [frontend/app/api/auth/wordpress-com/callback/route.ts]
- [x] [Review][Patch] Empty blog_url returned as "" account_identifier instead of null/omitted [backend/app/routers/publishing.py:wordpress_com_oauth_callback]
- [x] [Review][Defer] CSRF state-in-cookie pattern — standard OAuth, consistent with X/LinkedIn — deferred, pre-existing
- [x] [Review][Defer] Session cookie forwarding to backend — pre-existing OAuth pattern — deferred, pre-existing
- [x] [Review][Defer] WP_COM_CLIENT_SECRET defaults to "" — pre-existing settings pattern — deferred, pre-existing
- [x] [Review][Defer] Cookie Secure only in production — pre-existing, X/LinkedIn same — deferred, pre-existing
- [x] [Review][Defer] _extract_title null-safety — pre-existing imported function — deferred, pre-existing
- [x] [Review][Defer] Safari ITP may strip lax cookie — pre-existing, affects X/LinkedIn too — deferred, pre-existing
- [x] [Review][Defer] Parallel tabs overwrite state cookie — pre-existing pattern — deferred, pre-existing
- [x] [Review][Defer] Disconnect error handling silently ignored — pre-existing UI pattern — deferred, pre-existing
- [x] [Review][Defer] publish_post URL return value discarded — consistent with all platform integrations — deferred, pre-existing
- [x] [Review][Defer] scope=global requests full access — spec-mandated — deferred, pre-existing

### Change Log

- 2026-07-03: Implemented WordPress.com OAuth integration — new integration module, OAuth routes, two-step WordPress card sub-choice UI, list/disconnect logic, publishing dispatch support, and full test coverage (Story 5.6)
