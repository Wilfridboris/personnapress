---
baseline_commit: 39821153de4d7d70a2b3b18cb43b8f9642bdfc8f
---

# Story 5.2: Platform Connection Setup — X (Twitter) & LinkedIn OAuth

Status: done

## Story

As an authenticated user,
I want to connect my Client to X and LinkedIn via OAuth authorization flows,
So that PersonnaPress can post on my behalf using secure, revocable OAuth tokens.

## Acceptance Criteria

1. **Given** a user clicks "Connect" on the X (Twitter) connection card, **When** the "Connect X" button is clicked, **Then** Next.js generates a random `state` value (32-byte hex), stores it in a short-lived httpOnly cookie (`oauth_state`, SameSite=Lax, 10-minute expiry, Path=/), and redirects the browser to the Twitter OAuth 2.0 PKCE authorization URL with `client_id`, `redirect_uri`, `scope=tweet.read tweet.write users.read offline.access`, `state`, `code_challenge`, `code_challenge_method=S256`, and `response_type=code` parameters.

2. **Given** the user authorizes the X app and is returned to the OAuth callback, **When** the callback URL `GET /api/auth/x/callback?code=...&state=...` is hit, **Then** Next.js verifies the returned `state` matches the httpOnly `oauth_state` cookie (CSRF protection); if valid, calls FastAPI `POST /api/v1/clients/{client_id}/connections/x/callback` with the authorization code and `client_id`; FastAPI exchanges the code for tokens via Twitter OAuth 2.0 PKCE token endpoint; the access token and refresh token are JSON-serialized, encrypted with AES-256-GCM, and stored in `platform_connections`; the callback page navigates back to `/clients/{client_id}/connections` and the X card updates to "Connected — @{twitter_handle}."

3. **Given** the `state` parameter in the callback does not match the `oauth_state` cookie, **When** the callback is received, **Then** the OAuth flow is aborted, the `oauth_state` cookie is cleared, and the user is redirected to `/clients/{client_id}/connections` with an error toast: "Authorization failed — the request was tampered with. Please try connecting again."

4. **Given** a user clicks "Connect" on the LinkedIn connection card, **When** the "Connect LinkedIn" button is clicked, **Then** the user is redirected to LinkedIn's OAuth 2.0 authorization URL with `scope=w_member_social`, `redirect_uri`, `response_type=code`, `state`, and `client_id`; the same `oauth_state` CSRF protection pattern (httpOnly cookie, SameSite=Lax, 10-minute expiry) is used as for X.

5. **Given** the user authorizes LinkedIn and is returned to the callback, **When** `GET /api/auth/linkedin/callback?code=...&state=...` is hit and state validates, **Then** Next.js calls FastAPI `POST /api/v1/clients/{client_id}/connections/linkedin/callback`; FastAPI calls LinkedIn's token endpoint to obtain an access token; FastAPI calls `GET https://api.linkedin.com/v2/userinfo` to retrieve the user's name; the access token is encrypted and stored in `platform_connections` with `platform='linkedin'`; the LinkedIn card updates to "Connected — {LinkedIn display name}."

6. **Given** any OAuth connection attempt fails on the provider side (user denies, token exchange error), **When** the callback receives an `error` parameter or the exchange fails, **Then** the user is redirected to `/clients/{client_id}/connections` with a toast error: "[Platform] authorization failed — [error_description]. Please try connecting again." — the connection card remains "Not connected."

7. **Given** the OAuth callback page closes or navigates away, **When** the Platform Connections page shows, **Then** the connection cards reflect the updated state without a manual page refresh — the page refetches connection status on focus (React Query `refetchOnWindowFocus: true`).

8. **Given** the Platform Connections page, **When** X or LinkedIn "Connect" button is clicked, **Then** the button shows "Connecting..." state and the OAuth redirect happens; the card updates to "Connecting..." optimistically until the callback completes and the React Query cache is refreshed.

## Tasks / Subtasks

- [x] Task 1: Add X and LinkedIn OAuth env vars to `backend/app/core/config.py` (AC: #1, #4)
  - [x] 1.1 Add to `Settings` class in `backend/app/core/config.py`:
    ```python
    X_CLIENT_ID: str = ""
    X_CLIENT_SECRET: str = ""
    X_REDIRECT_URI: str = ""   # e.g. https://app.personnapress.com/api/auth/x/callback
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = ""  # e.g. https://app.personnapress.com/api/auth/linkedin/callback
    ```
  - [x] 1.2 Add corresponding entries to `backend/.env.example` with descriptive comments
  - [x] 1.3 Add to `frontend/.env.example`:
    ```
    NEXT_PUBLIC_X_CLIENT_ID=        # Twitter/X OAuth 2.0 app Client ID
    X_CLIENT_SECRET=                # Twitter/X app Client Secret (server-side only)
    NEXT_PUBLIC_LINKEDIN_CLIENT_ID= # LinkedIn app Client ID
    LINKEDIN_CLIENT_SECRET=         # LinkedIn app Client Secret (server-side only)
    APP_URL=                        # e.g. https://app.personnapress.com
    ```
  - [x] 1.4 Note: `NEXT_PUBLIC_*` env vars are readable client-side; the redirect construction can reference these. Client secrets are NEVER `NEXT_PUBLIC_*` — they stay server-only and are only used in Next.js API route handlers or FastAPI.

- [x] Task 2: Create Next.js API route for X OAuth initiation (AC: #1)
  - [x] 2.1 Create `frontend/app/api/auth/x/route.ts` — GET handler that initiates X OAuth PKCE:
    ```typescript
    import { NextRequest, NextResponse } from 'next/server'
    import { randomBytes, createHash } from 'crypto'

    export async function GET(request: NextRequest) {
      const { searchParams } = new URL(request.url)
      const clientId = searchParams.get('client_id')
      if (!clientId) return NextResponse.json({ error: 'Missing client_id' }, { status: 400 })

      // Generate PKCE code verifier and challenge
      const codeVerifier = randomBytes(32).toString('base64url')
      const codeChallenge = createHash('sha256')
        .update(codeVerifier)
        .digest('base64url')

      // Generate CSRF state
      const state = randomBytes(32).toString('hex')

      // Store state + code_verifier + client_id in httpOnly cookie
      const cookieValue = JSON.stringify({ state, codeVerifier, clientId })
      const response = NextResponse.redirect(buildXAuthUrl(codeChallenge, state))
      response.cookies.set('oauth_state', cookieValue, {
        httpOnly: true,
        sameSite: 'lax',
        maxAge: 600, // 10 minutes
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      })
      return response
    }

    function buildXAuthUrl(codeChallenge: string, state: string): string {
      const params = new URLSearchParams({
        response_type: 'code',
        client_id: process.env.NEXT_PUBLIC_X_CLIENT_ID!,
        redirect_uri: `${process.env.APP_URL}/api/auth/x/callback`,
        scope: 'tweet.read tweet.write users.read offline.access',
        state,
        code_challenge: codeChallenge,
        code_challenge_method: 'S256',
      })
      return `https://twitter.com/i/oauth2/authorize?${params.toString()}`
    }
    ```

- [x] Task 3: Create Next.js API route for X OAuth callback (AC: #2, #3, #6)
  - [x] 3.1 Create `frontend/app/api/auth/x/callback/route.ts`:
    ```typescript
    import { NextRequest, NextResponse } from 'next/server'

    export async function GET(request: NextRequest) {
      const { searchParams } = new URL(request.url)
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const error = searchParams.get('error')
      const errorDescription = searchParams.get('error_description')

      // Read oauth_state cookie
      const cookieRaw = request.cookies.get('oauth_state')?.value
      const oauthState = cookieRaw ? JSON.parse(cookieRaw) : null

      // Clear oauth_state cookie immediately
      const clearCookieResponse = (url: string) => {
        const res = NextResponse.redirect(url)
        res.cookies.delete('oauth_state')
        return res
      }

      const connectionsUrl = oauthState?.clientId
        ? `${process.env.APP_URL}/clients/${oauthState.clientId}/connections`
        : `${process.env.APP_URL}/clients`

      // Provider error
      if (error) {
        return clearCookieResponse(
          `${connectionsUrl}?error=${encodeURIComponent(`X authorization failed — ${errorDescription ?? error}. Please try connecting again.`)}`
        )
      }

      // CSRF check
      if (!oauthState || state !== oauthState.state) {
        return clearCookieResponse(
          `${connectionsUrl}?error=${encodeURIComponent('Authorization failed — the request was tampered with. Please try connecting again.')}`
        )
      }

      // Exchange code for tokens via FastAPI
      const apiUrl = process.env.BACKEND_URL ?? 'http://localhost:8000'
      const backendResp = await fetch(
        `${apiUrl}/api/v1/clients/${oauthState.clientId}/connections/x/callback`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Cookie: request.headers.get('cookie') ?? '' },
          body: JSON.stringify({ code, code_verifier: oauthState.codeVerifier }),
        }
      )

      if (!backendResp.ok) {
        const err = await backendResp.json().catch(() => ({}))
        return clearCookieResponse(
          `${connectionsUrl}?error=${encodeURIComponent(err?.error?.message ?? 'X connection failed. Please try again.')}`
        )
      }

      return clearCookieResponse(`${connectionsUrl}?success=x`)
    }
    ```

- [x] Task 4: Create Next.js API route for LinkedIn OAuth initiation (AC: #4)
  - [x] 4.1 Create `frontend/app/api/auth/linkedin/route.ts` — GET handler analogous to X, but without PKCE (LinkedIn uses standard OAuth 2.0 code flow):
    ```typescript
    export async function GET(request: NextRequest) {
      const { searchParams } = new URL(request.url)
      const clientId = searchParams.get('client_id')
      const state = randomBytes(32).toString('hex')
      const cookieValue = JSON.stringify({ state, clientId })
      const authUrl = new URL('https://www.linkedin.com/oauth/v2/authorization')
      authUrl.searchParams.set('response_type', 'code')
      authUrl.searchParams.set('client_id', process.env.NEXT_PUBLIC_LINKEDIN_CLIENT_ID!)
      authUrl.searchParams.set('redirect_uri', `${process.env.APP_URL}/api/auth/linkedin/callback`)
      authUrl.searchParams.set('scope', 'w_member_social')
      authUrl.searchParams.set('state', state)
      const response = NextResponse.redirect(authUrl.toString())
      response.cookies.set('oauth_state', cookieValue, { httpOnly: true, sameSite: 'lax', maxAge: 600, path: '/', secure: process.env.NODE_ENV === 'production' })
      return response
    }
    ```

- [x] Task 5: Create Next.js API route for LinkedIn OAuth callback (AC: #5, #6)
  - [x] 5.1 Create `frontend/app/api/auth/linkedin/callback/route.ts` — analogous to X callback but calls `POST /api/v1/clients/{client_id}/connections/linkedin/callback` with just `{ code }` (no PKCE verifier needed)
  - [x] 5.2 Same state CSRF check pattern, cookie clear pattern, error redirect pattern as X callback

- [x] Task 6: Add FastAPI endpoints for X and LinkedIn OAuth token exchange (AC: #2, #5)
  - [x] 6.1 In `backend/app/routers/publishing.py`, add:
    ```python
    class OAuthCallbackRequest(BaseModel):
        code: str
        code_verifier: Optional[str] = None  # X PKCE only
        client_id_param: uuid.UUID  # renamed to avoid conflict with path param

    @router.post("/clients/{client_id}/connections/x/callback", status_code=201)
    async def x_oauth_callback(
        client_id: uuid.UUID,
        body: OAuthCallbackRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> dict:
    ```
    - Ownership check
    - Call `integrations/twitter.py:exchange_code_for_tokens(code, body.code_verifier, redirect_uri)`
    - Get handle via `integrations/twitter.py:get_user_handle(access_token)`
    - Serialize: `json.dumps({"access_token": ..., "refresh_token": ..., "handle": handle})`
    - Encrypt and upsert into `platform_connections`
    - Return `{"platform": "x", "connected": True, "account_identifier": f"@{handle}"}`
  - [x] 6.2 Add LinkedIn callback endpoint analogously:
    ```python
    @router.post("/clients/{client_id}/connections/linkedin/callback", status_code=201)
    ```
    - Exchange code via `integrations/linkedin.py:exchange_code_for_token(code, redirect_uri)`
    - Get name via `integrations/linkedin.py:get_user_name(access_token)`
    - Serialize, encrypt, upsert, return

- [x] Task 7: Create `backend/app/integrations/twitter.py` (partial — OAuth exchange + user handle; publish in Story 5.3) (AC: #2)
  - [x] 7.1 Create with:
    ```python
    import httpx
    from app.core.config import settings
    from app.core.exceptions import PlatformError

    async def exchange_code_for_tokens(
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict:
        """Exchange PKCE code for access + refresh tokens."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": settings.X_CLIENT_ID,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
                auth=(settings.X_CLIENT_ID, settings.X_CLIENT_SECRET),
            )
        if resp.status_code != 200:
            raise PlatformError("X", resp.status_code, resp.json().get("error_description", "token exchange failed"))
        return resp.json()  # {"access_token": ..., "refresh_token": ..., "token_type": "bearer"}

    async def get_user_handle(access_token: str) -> str:
        """Fetch the authenticated user's Twitter handle."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            return "unknown"
        return resp.json().get("data", {}).get("username", "unknown")
    ```

- [x] Task 8: Create `backend/app/integrations/linkedin.py` (partial — OAuth exchange + user name; publish in Story 5.3) (AC: #5)
  - [x] 8.1 Create with:
    ```python
    import httpx
    from app.core.config import settings
    from app.core.exceptions import PlatformError

    async def exchange_code_for_token(code: str, redirect_uri: str) -> str:
        """Exchange OAuth code for access token."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if resp.status_code != 200:
            raise PlatformError("LinkedIn", resp.status_code, "token exchange failed")
        return resp.json()["access_token"]

    async def get_user_name(access_token: str) -> str:
        """Fetch the authenticated LinkedIn user's display name."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            return "unknown"
        return resp.json().get("name", "unknown")
    ```

- [x] Task 9: Wire X and LinkedIn "Connect" buttons in `PlatformConnectionCard.tsx` (AC: #1, #4, #8)
  - [x] 9.1 For `platform === "x"`: "Connect X" button navigates to `/api/auth/x?client_id={clientId}` (full page navigation — not a fetch — to allow the redirect chain)
    ```tsx
    <a href={`/api/auth/x?client_id=${clientId}`}
       className="inline-block px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2">
      Connect X
    </a>
    ```
    Style as Secondary Button (border ink, hover inverts) — note: `<a>` not `<button>` since it navigates away
  - [x] 9.2 For `platform === "linkedin"`: same pattern with `/api/auth/linkedin?client_id={clientId}`
  - [x] 9.3 Success handling: when the connections page loads after callback (`?success=x` or `?success=linkedin`), read the URL param and show a toast: "Connected to X." or "Connected to LinkedIn."; then strip the param from the URL with `router.replace`
  - [x] 9.4 Error handling: when the connections page loads after callback with `?error=...`, show the decoded error as a toast; then strip the URL param

- [x] Task 10: Handle success/error query params on connections page (AC: #7, #8)
  - [x] 10.1 In `PlatformConnectionsClient.tsx`, read `useSearchParams()` for `success` and `error` params on mount:
    ```typescript
    useEffect(() => {
      const success = searchParams.get('success')
      const error = searchParams.get('error')
      if (success) {
        addToast({ type: 'success', message: `Connected to ${success === 'x' ? 'X' : 'LinkedIn'}.` })
        router.replace(`/clients/${clientId}/connections`)
      }
      if (error) {
        addToast({ type: 'error', message: decodeURIComponent(error) })
        router.replace(`/clients/${clientId}/connections`)
      }
    }, [])
    ```
  - [x] 10.2 React Query `refetchOnWindowFocus: true` is the default — the connections query will refetch automatically when the window regains focus after the OAuth popup returns. Confirm this in the `useQuery` call.

- [x] Task 11: Backend tests (AC: #2, #3, #5, #6)
  - [x] 11.1 In `backend/tests/routers/test_publishing.py`:
    - `test_x_oauth_callback_success` — mocks `twitter.exchange_code_for_tokens` + `get_user_handle`, verifies encrypted row stored
    - `test_x_oauth_callback_token_exchange_failure` — platform error → 400
    - `test_linkedin_oauth_callback_success` — mocks `linkedin.exchange_code_for_token` + `get_user_name`, verifies row stored
    - `test_linkedin_oauth_callback_failure` — 400 on exchange error

- [x] Task 12: Frontend tests (AC: #1, #2, #3, #4, #6, #8)
  - [x] 12.1 In `frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx`, extend for OAuth platforms:
    - Test: X "Connect X" renders as `<a>` with correct href
    - Test: LinkedIn "Connect LinkedIn" renders as `<a>` with correct href
  - [x] 12.2 Test Next.js API routes: `frontend/__tests__/app/api/auth/x.test.ts`
    - State cookie is set on GET `/api/auth/x`
    - CSRF mismatch → redirect with error message
    - Missing `oauth_state` cookie → redirect with error message

## Dev Notes

### Twitter OAuth 2.0 PKCE Flow — Key Details

Per AR-13 and FR-22:
- `oauth_state` cookie: `httpOnly=True`, `SameSite=Lax`, 10-minute expiry — this is the existing pattern from Google OAuth (AR-8)
- PKCE: code verifier = 32 random bytes, base64url encoded; code challenge = SHA256 of verifier, base64url encoded
- Scopes: `tweet.read tweet.write users.read offline.access` — `offline.access` gets a refresh token for long-lived posting
- The `code_verifier` must be stored alongside `state` in the cookie and sent to FastAPI for the token exchange

**Critical**: Store `{ state, codeVerifier, clientId }` as JSON in the `oauth_state` cookie — not just the state string. This is different from the Google OAuth flow which only needs state (AR-8).

### LinkedIn OAuth 2.0 — No PKCE Required

LinkedIn uses standard OAuth 2.0 authorization code flow (no PKCE). The `oauth_state` cookie only needs `{ state, clientId }`. LinkedIn's API version header `202602` is required for UGC Posts API in Story 5.3 — not needed for token exchange here.

### Next.js API Route Cookie Forwarding to FastAPI

The Next.js callback route calls FastAPI with `Cookie: request.headers.get('cookie')` forwarded. This passes the user's session JWT cookie to FastAPI so `get_current_user` works. This is the same pattern used by the Google OAuth callback route (`frontend/app/api/auth/google/callback/route.ts`).

**Read the existing Google OAuth callback route** to confirm the pattern before implementing — it's the canonical reference: `frontend/app/api/auth/google/callback/route.ts`.

### Connection Card — X and LinkedIn Enabled in This Story

Story 5.1 left X and LinkedIn cards with disabled "Connect" buttons. In Story 5.2, these are activated:
- Replace the `<button disabled>` placeholders with the `<a href="/api/auth/x?...">` links
- The `PlatformConnectionCard` component receives a `platform` prop and `clientId` — it renders the appropriate form based on platform type:
  - `"wordpress"` → inline credential form (5.1)
  - `"webflow"` → inline token + collection form (5.1)
  - `"x"` → `<a>` link to OAuth initiation route (5.2)
  - `"linkedin"` → `<a>` link to OAuth initiation route (5.2)

### Paper Style — OAuth Connect Buttons

Per DESIGN.md Secondary button spec:
```
background: transparent
border: 1px solid ink (#111111)
hover: background ink, foreground white
padding: 0.625rem 1.25rem
rounded-none
```

Since we use `<a>` for OAuth (browser navigation), style it as:
```tsx
className="inline-block px-5 py-2.5 border border-ink text-ink text-sm font-medium
           rounded-none hover:bg-ink hover:text-white transition-colors
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
```

### BACKEND_URL Environment Variable for Next.js Server-Side Calls

The Next.js callback routes call FastAPI server-side. In production, FastAPI is on the DO Droplet. Add `BACKEND_URL` to `frontend/.env.example`:
```
BACKEND_URL=https://api.personnapress.com  # FastAPI backend URL (server-side only, never NEXT_PUBLIC_)
```
In development, this defaults to `http://localhost:8000`.

### Twitter Redirect URI Registration

The Twitter/X Developer Portal requires the exact `redirect_uri` to be whitelisted. Add a note in `.env.example`:
```
# Register https://app.personnapress.com/api/auth/x/callback in Twitter Dev Portal → App → Auth settings
```

### Project Structure Notes

**New files:**
```
frontend/app/api/auth/x/route.ts
frontend/app/api/auth/x/callback/route.ts
frontend/app/api/auth/linkedin/route.ts
frontend/app/api/auth/linkedin/callback/route.ts
backend/app/integrations/twitter.py      (partial — OAuth only; publish in 5.3)
backend/app/integrations/linkedin.py     (partial — OAuth only; publish in 5.3)
frontend/__tests__/app/api/auth/x.test.ts
```

**Modified files:**
```
backend/app/routers/publishing.py        ← Add x/callback + linkedin/callback endpoints
backend/app/core/config.py               ← Add X_CLIENT_ID, X_CLIENT_SECRET, etc.
backend/.env.example                     ← Add new OAuth vars
frontend/.env.example                    ← Add NEXT_PUBLIC_X_CLIENT_ID, NEXT_PUBLIC_LINKEDIN_CLIENT_ID, BACKEND_URL
frontend/components/publishing/PlatformConnectionCard.tsx  ← Wire X/LinkedIn buttons
frontend/components/publishing/PlatformConnectionsClient.tsx ← Handle success/error params
frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx ← Extend for OAuth
```

### References

- Story 5.2 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2]
- FR-22: X OAuth 2.0 PKCE, LinkedIn OAuth `w_member_social`, AES-256-GCM: [Source: _bmad-output/planning-artifacts/epics.md#FR-22]
- AR-13: X OAuth PKCE state in httpOnly cookie: [Source: _bmad-output/planning-artifacts/epics.md#AR-13]
- AR-8: Google OAuth flow pattern (Next.js callback route): [Source: _bmad-output/planning-artifacts/epics.md#AR-8]
- UX-DR20: Platform connection card — OAuth popup pattern: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR20]
- UX-DR21: Error microcopy — "[Platform] authorization failed — [error]. Please try connecting again.": [Source: _bmad-output/planning-artifacts/epics.md#UX-DR21]
- Architecture: OAuth callbacks handled by Next.js routes only: [Source: _bmad-output/planning-artifacts/architecture.md#API Boundaries]
- Architecture: credentials encrypt at write, decrypt only at publish: [Source: _bmad-output/planning-artifacts/architecture.md#Credential Encrypt/Decrypt Pattern]
- Existing Google OAuth callback route (canonical pattern): [Source: frontend/app/api/auth/google/callback/route.ts]
- Twitter OAuth 2.0 PKCE: POST https://api.twitter.com/2/oauth2/token: [Source: _bmad-output/planning-artifacts/epics.md#FR-23]
- LinkedIn UGC Posts API `202602` version header: [Source: _bmad-output/planning-artifacts/epics.md#FR-23]
- Story 5.1 PlatformConnectionCard — placeholder disabled buttons for X/LinkedIn: [Source: _bmad-output/implementation-artifacts/5-1-platform-connection-setup-wordpress-webflow.md#Task 6.7]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Implemented full X (Twitter) OAuth 2.0 PKCE flow via Next.js API routes (`/api/auth/x` initiation, `/api/auth/x/callback`)
- Implemented full LinkedIn OAuth 2.0 flow via Next.js API routes (`/api/auth/linkedin` initiation, `/api/auth/linkedin/callback`)
- Created FastAPI endpoints `POST /api/v1/clients/{client_id}/connections/x/callback` and `POST /api/v1/clients/{client_id}/connections/linkedin/callback` with ownership checks, token exchange, credential encryption, and upsert
- Created `backend/app/integrations/twitter.py` (PKCE token exchange + user handle fetch) and `backend/app/integrations/linkedin.py` (token exchange + userinfo fetch) — publish functions to be added in Story 5.3
- CSRF protection: `oauth_state` cookie stores `{ state, codeVerifier, clientId }` as JSON (X) or `{ state, clientId }` (LinkedIn); verified before calling FastAPI
- Replaced disabled OAuth buttons in `PlatformConnectionCard.tsx` with Paper-style `<a>` links navigating to the respective initiation routes
- Added `refetchOnWindowFocus: true` to connections query; success/error params handled in `PlatformConnectionsClient.tsx` with toast notifications and URL cleanup
- Added `settings` import to `publishing.py` (required for redirect URI construction)
- 78 frontend tests all pass; 12 backend publishing tests pass (1 pre-existing webflow test failure unrelated to this story)

### File List

- `backend/app/core/config.py` — added X and LinkedIn OAuth env vars
- `backend/.env.example` — added X and LinkedIn OAuth comments and vars
- `frontend/.env.example` — added NEXT_PUBLIC_X_CLIENT_ID, X_CLIENT_SECRET, NEXT_PUBLIC_LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET
- `frontend/app/api/auth/x/route.ts` — new: X OAuth PKCE initiation handler
- `frontend/app/api/auth/x/callback/route.ts` — new: X OAuth callback handler with CSRF check
- `frontend/app/api/auth/linkedin/route.ts` — new: LinkedIn OAuth initiation handler
- `frontend/app/api/auth/linkedin/callback/route.ts` — new: LinkedIn OAuth callback handler with CSRF check
- `backend/app/integrations/twitter.py` — new: X token exchange + get_user_handle
- `backend/app/integrations/linkedin.py` — new: LinkedIn token exchange + get_user_name
- `backend/app/routers/publishing.py` — added settings import, linkedin/twitter integration imports, OAuthCallbackRequest model, x_oauth_callback and linkedin_oauth_callback endpoints
- `frontend/components/publishing/PlatformConnectionCard.tsx` — replaced disabled OAuth buttons with active `<a>` links
- `frontend/components/publishing/PlatformConnectionsClient.tsx` — added success/error query param handling and refetchOnWindowFocus
- `backend/tests/test_publishing_router.py` — added 4 new tests: x_oauth_callback_success, x_oauth_callback_token_exchange_failure, linkedin_oauth_callback_success, linkedin_oauth_callback_failure
- `frontend/__tests__/components/publishing/PlatformConnectionCard.test.tsx` — updated OAuth platform tests: disabled buttons → active anchor links
- `frontend/__tests__/app/api/auth/x.test.ts` — new: 5 tests for X OAuth initiation and callback CSRF checks

### Review Findings

- [x] [Review][Patch] Shared `oauth_state` cookie name — X and LinkedIn overwrite each other's state [frontend/app/api/auth/x/route.ts, frontend/app/api/auth/linkedin/route.ts]
- [x] [Review][Patch] Uncaught JSON.parse on malformed cookie throws 500 instead of safe redirect [frontend/app/api/auth/x/callback/route.ts, frontend/app/api/auth/linkedin/callback/route.ts]
- [x] [Review][Patch] Env var non-null assertion `!` — undefined becomes literal "undefined" in OAuth URL [frontend/app/api/auth/x/route.ts, frontend/app/api/auth/linkedin/route.ts]
- [x] [Review][Patch] Empty `access_token` not validated before storing — bad credential stored silently [backend/app/routers/publishing.py]
- [x] [Review][Patch] AC #8: No "Connecting..." optimistic state on OAuth anchor link [frontend/components/publishing/PlatformConnectionCard.tsx]
- [x] [Review][Patch] LinkedIn `resp.json()["access_token"]` raises KeyError on malformed 200 response [backend/app/integrations/linkedin.py]
- [x] [Review][Patch] LinkedIn error detail discarded — hardcoded "token exchange failed" hides provider errors [backend/app/integrations/linkedin.py]
- [x] [Review][Patch] Exception `.message` attribute assumption — non-string `.message` causes 500 instead of 400 [backend/app/routers/publishing.py]
- [x] [Review][Patch] `code_verifier` silently replaced with empty string — should reject missing verifier for X endpoint [backend/app/routers/publishing.py]
- [x] [Review][Patch] `NEXT_PUBLIC_APP_URL` leaks APP_URL into client bundle — use server-only `APP_URL` [frontend/app/api/auth/x/route.ts, frontend/app/api/auth/linkedin/route.ts]
- [x] [Review][Patch] `ConnectionCreatePayload` exposes OAuth token fields that should never be sent client→server [frontend/lib/types.ts]
- [x] [Review][Patch] APP_URL consistency — frontend/backend must match exactly for redirect_uri; add paired note in .env.example [frontend/.env.example, backend/.env.example]
- [x] [Review][Defer] `get_user_handle` returns "unknown" silently on failure — acceptable degradation, connection still stored [backend/app/integrations/twitter.py] — deferred, pre-existing pattern
- [x] [Review][Defer] `useEffect` empty deps in PlatformConnectionsClient — intentional, acknowledged with eslint suppression [frontend/components/publishing/PlatformConnectionsClient.tsx] — deferred, intentional design
- [x] [Review][Defer] Cookie forwarding passes all cookies to backend — documented project pattern for session forwarding [frontend/app/api/auth/x/callback/route.ts] — deferred, pre-existing
- [x] [Review][Defer] `connectionsUrl` computed from cookie before state validation — same-origin redirect only, no external open redirect risk [frontend/app/api/auth/x/callback/route.ts] — deferred, low risk
- [x] [Review][Defer] `refresh_token` stored with no refresh logic — X tokens expire in 2 hours; refresh flow is future story work [backend/app/routers/publishing.py] — deferred, future story

## Change Log

- 2026-07-03: Implemented Story 5.2 — X (Twitter) and LinkedIn OAuth connection flows. Added Next.js API routes for both initiation and callback, FastAPI token-exchange endpoints, twitter.py/linkedin.py integration modules, activated OAuth "Connect" buttons in PlatformConnectionCard, and wired success/error toast notifications in PlatformConnectionsClient. Added 9 new tests (4 backend, 5 frontend); all pass.
