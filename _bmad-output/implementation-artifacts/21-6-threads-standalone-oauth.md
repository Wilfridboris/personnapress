---
baseline_commit: 3a6310c
---

# Story 21.6: Threads Standalone OAuth Connection

Status: done

## Story

As a PersonnaPress user who wants to post on Threads,
I want to connect my Threads account through its own dedicated OAuth flow,
so that PersonnaPress can publish to Threads even if I have not connected a Facebook or Instagram account.

## Context & Motivation

Threads publishing is **completely broken today.** Story 21.1 wired up Threads connection by piggybacking on the Meta (Facebook/Instagram) OAuth flow: after the Facebook token exchange, the backend calls `discover_threads_user_id` which hits `GET /v25.0/{instagram_user_id}?fields=threads_user_id` on the Facebook Graph API and stores the **Facebook long-lived user token** as the Threads `user_access_token`. When the publisher later calls `graph.threads.com` with this Facebook token it receives a 401 because Facebook tokens are rejected by the Threads API.

Threads runs on a **completely separate OAuth system** from Facebook/Instagram:
- Authorization endpoint: `https://threads.net/oauth/authorize`
- Token exchange: `POST https://graph.threads.net/oauth/access_token`
- Long-lived token upgrade: `GET https://graph.threads.net/access_token?grant_type=th_exchange_token`
- User info: `GET https://graph.threads.net/v1.0/me?fields=id,username`
- Threads-specific app credentials: `THREADS_APP_ID` / `THREADS_APP_SECRET` (registered separately from the Meta Business App at developers.facebook.com under "Threads settings")

This story replaces the broken Step f piggyback with a proper standalone Threads OAuth flow. No changes to Instagram or Facebook Page connection code are needed; only the Threads-specific Step f block is removed from the meta callback.

The `threads` value already exists in the `platform_enum` Postgres type (added in Story 21.1). No migration is needed.

---

## Acceptance Criteria

### AC 1: Backend `threads_auth.py` module

**Given** a new file `backend/app/integrations/threads_auth.py` is created,
**When** it is imported,
**Then** it exposes exactly three async functions with these signatures:

```python
async def exchange_code_for_short_lived_token(code: str, redirect_uri: str) -> str:
    """Exchange Threads OAuth code for a short-lived token (valid ~1 hour)."""

async def exchange_short_lived_for_long_lived_token(short_lived_token: str) -> str:
    """Exchange short-lived Threads token for a 60-day long-lived token."""

async def get_threads_user(long_lived_token: str) -> dict:
    """Fetch Threads user info. Returns dict with 'id' and 'username' keys."""
```

Implementation details:
- All three functions use `httpx.AsyncClient(timeout=10.0)` (matching `meta.py` pattern)
- `exchange_code_for_short_lived_token`: `POST https://graph.threads.net/oauth/access_token` with form fields `client_id`, `client_secret`, `grant_type=authorization_code`, `redirect_uri`, `code`; on non-200 raise `PlatformError("threads", status_code, message)`; return `resp.json()["access_token"]`
- `exchange_short_lived_for_long_lived_token`: `GET https://graph.threads.net/access_token` with params `grant_type=th_exchange_token`, `client_id`, `client_secret`, `access_token={short_lived_token}`; on non-200 raise `PlatformError("threads", status_code, message)`; return `resp.json()["access_token"]`
- `get_threads_user`: `GET https://graph.threads.net/v1.0/me` with params `fields=id,username`, `access_token={long_lived_token}`; on non-200 raise `PlatformError("threads", status_code, message)`; return `resp.json()` (caller accesses `.get("id")` and `.get("username")`)
- Import `settings` from `app.core.config` to access `THREADS_APP_ID` and `THREADS_APP_SECRET`
- Import `PlatformError` from `app.core.exceptions`
- No logging module needed unless a function warrants a warning (keep it minimal like `meta.py`)

### AC 2: New settings in `backend/app/core/config.py`

**Given** `backend/app/core/config.py` `Settings` class,
**When** the story is complete,
**Then** the following two fields are added, grouped after `META_APP_SECRET` with a comment:

```python
    # Threads App (separate credentials from Meta Business App — threads.net developer portal)
    THREADS_APP_ID: str = ""
    THREADS_APP_SECRET: str = ""
```

### AC 3: New backend endpoint `POST /clients/{client_id}/connections/threads/callback`

**Given** `backend/app/routers/publishing.py`,
**When** `POST /api/v1/clients/{client_id}/connections/threads/callback` is called with `{"code": "<auth_code>"}`,
**Then** the handler executes these steps in order:

a) Exchange code for short-lived token:
```python
short_lived_token = await threads_auth.exchange_code_for_short_lived_token(
    body.code,
    f"{settings.APP_URL}/api/auth/threads/callback"
)
```
On failure, raise `HTTPException(400, detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": ..., "detail": {}}})` (same shape as the meta callback error responses).

b) Exchange for long-lived token:
```python
long_lived_token = await threads_auth.exchange_short_lived_for_long_lived_token(short_lived_token)
```
On failure, raise same `HTTPException(400, ...)` shape.

c) Fetch Threads user info:
```python
user_info = await threads_auth.get_threads_user(long_lived_token)
threads_user_id = user_info.get("id", "")
username = user_info.get("username", "")
```
On failure or if `threads_user_id` is empty, raise `HTTPException(422, detail={"error": {"code": "USER_FETCH_FAILED", "message": "Could not retrieve Threads user ID.", "detail": {}}})`.

d) Upsert the `threads` platform connection:
```python
threads_cred = json.dumps({
    "threads_user_id": threads_user_id,
    "username": username,
    "user_access_token": long_lived_token,
    "token_acquired_at": datetime.now(timezone.utc).isoformat(),
})
encrypted = encrypt_credential(threads_cred)
await upsert_connection(db, client_id, "threads", encrypted)
```

e) Return `{"connected_platforms": ["threads"]}` with `status_code=201`.

The endpoint signature must match the existing pattern for `meta_oauth_callback`:
```python
@router.post("/clients/{client_id}/connections/threads/callback", status_code=201)
async def threads_oauth_callback(
    client_id: uuid.UUID,
    body: OAuthCallbackRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
```

`OAuthCallbackRequest` (already defined for the meta callback) has a `code: str` field -- reuse it.

Import `threads_auth` from `app.integrations.threads_auth` at the top of `publishing.py` (alongside the existing `meta_integration` import).

Add `from datetime import datetime, timezone` if not already imported (check -- it may already be present).

### AC 4: Remove Threads piggyback from meta OAuth callback (Step f)

**Given** `backend/app/routers/publishing.py` lines ~456-469 (Step f block),
**When** this story is complete,
**Then** the entire Step f block is deleted:

```python
    # Step f: Attempt Threads user discovery (optional, non-fatal)
    if first_instagram_user_id:
        threads_user_id = await meta_integration.discover_threads_user_id(
            first_instagram_user_id, long_lived_token
        )
        if threads_user_id:
            threads_cred = json.dumps({
                "threads_user_id": threads_user_id,
                "username": first_instagram_username or "",
                "user_access_token": long_lived_token,
            })
            encrypted_threads = encrypt_credential(threads_cred)
            await upsert_connection(db, client_id, "threads", encrypted_threads)
            connected_platforms.append("threads")
```

Also remove the two variables that were only used by Step f:
- `first_instagram_user_id: Optional[str] = None`
- `first_instagram_username: Optional[str] = None`

And the assignments inside the `for page in pages:` loop:
- `first_instagram_user_id = ig_user_id`
- `first_instagram_username = ig_username`

The `Optional` import from `typing` can be removed from `publishing.py` if it is no longer used elsewhere in the file (check before removing).

The `discover_threads_user_id` function in `meta.py` itself should **not** be deleted -- it may be referenced in existing tests. Simply stop calling it from the meta callback.

After removing Step f, the `connected_platforms` list will only contain `"instagram"` and/or `"facebook_page"`. The existing `422` guard when `connected_platforms` is empty remains unchanged.

### AC 5: New Next.js route `frontend/app/api/auth/threads/route.ts`

**Given** this new file,
**When** `GET /api/auth/threads?client_id={clientId}` is called,
**Then**:

a) Read `client_id` from query params; if missing return `NextResponse.json({ error: "Missing client_id" }, { status: 400 })`.

b) Read `NEXT_PUBLIC_THREADS_APP_ID` from `process.env`; if missing return `NextResponse.json({ error: "Threads OAuth is not configured" }, { status: 500 })`.

c) Generate `state = randomBytes(32).toString("hex")` and set `oauth_state_threads` cookie:
```typescript
const cookieValue = JSON.stringify({ state, clientId });
response.cookies.set("oauth_state_threads", cookieValue, {
  httpOnly: true,
  sameSite: "lax",
  maxAge: 600,
  path: "/",
  secure: process.env.NODE_ENV === "production",
});
```

d) Build the authorization URL and redirect:
```typescript
const authUrl = new URL("https://threads.net/oauth/authorize");
authUrl.searchParams.set("client_id", threadsAppId);
authUrl.searchParams.set("redirect_uri", `${APP_URL}/api/auth/threads/callback`);
authUrl.searchParams.set("scope", "threads_basic,threads_content_publish");
authUrl.searchParams.set("response_type", "code");
authUrl.searchParams.set("state", state);
return NextResponse.redirect(authUrl.toString());
```

Full file structure (mirror of `frontend/app/api/auth/meta/route.ts`):
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

  const threadsAppId = process.env.NEXT_PUBLIC_THREADS_APP_ID;
  if (!threadsAppId) {
    return NextResponse.json({ error: "Threads OAuth is not configured" }, { status: 500 });
  }

  const state = randomBytes(32).toString("hex");
  const cookieValue = JSON.stringify({ state, clientId });

  const authUrl = new URL("https://threads.net/oauth/authorize");
  authUrl.searchParams.set("client_id", threadsAppId);
  authUrl.searchParams.set("redirect_uri", `${APP_URL}/api/auth/threads/callback`);
  authUrl.searchParams.set("scope", "threads_basic,threads_content_publish");
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("state", state);

  const response = NextResponse.redirect(authUrl.toString());
  response.cookies.set("oauth_state_threads", cookieValue, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
```

### AC 6: New Next.js callback `frontend/app/api/auth/threads/callback/route.ts`

**Given** this new file,
**When** `GET /api/auth/threads/callback?code=...&state=...` is called,
**Then**:

a) Read `code`, `state`, `error`, `error_description` from query params.

b) Read `oauth_state_threads` cookie and parse as `{ state: string; clientId: string }`.

c) Derive `connectionsUrl` using the same pattern as `meta/callback/route.ts`:
```typescript
const connectionsUrl = oauthState?.clientId
  ? `${APP_URL}/clients/${oauthState.clientId}/connections`
  : `${APP_URL}/clients`;
```

d) On provider error (`error` param present), call `clearCookieRedirect` and redirect to `${connectionsUrl}?error=...`.

e) On CSRF failure (`!oauthState || state !== oauthState.state`), call `clearCookieRedirect` and redirect to `${connectionsUrl}?error=...`.

f) On success, `POST` to `${BACKEND_URL}/api/v1/clients/${oauthState.clientId}/connections/threads/callback` with `{ code }` and forwarded session cookie (same as the meta callback's fetch pattern).

g) On backend error, redirect to `${connectionsUrl}?error=...`.

h) On success, redirect to `${connectionsUrl}?success=threads`.

i) `clearCookieRedirect` deletes `oauth_state_threads` cookie in all redirect paths.

Full file structure (mirror of `frontend/app/api/auth/meta/callback/route.ts`):
```typescript
import { type NextRequest, NextResponse } from "next/server";

const APP_URL = process.env.APP_URL ?? "http://localhost:3000";
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function clearCookieRedirect(url: string): NextResponse {
  const res = NextResponse.redirect(url);
  res.cookies.delete("oauth_state_threads");
  return res;
}

type ThreadsOAuthState = { state: string; clientId: string };

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  const cookieRaw = request.cookies.get("oauth_state_threads")?.value;
  let oauthState: ThreadsOAuthState | null = null;
  if (cookieRaw) {
    try {
      oauthState = JSON.parse(cookieRaw) as ThreadsOAuthState;
    } catch {
      // malformed cookie -- treat as missing
    }
  }

  const connectionsUrl = oauthState?.clientId
    ? `${APP_URL}/clients/${oauthState.clientId}/connections`
    : `${APP_URL}/clients`;

  if (error) {
    return clearCookieRedirect(
      `${connectionsUrl}?error=${encodeURIComponent(`Threads authorization failed: ${errorDescription ?? error}. Please try connecting again.`)}`
    );
  }

  if (!oauthState || state !== oauthState.state) {
    return clearCookieRedirect(
      `${connectionsUrl}?error=${encodeURIComponent("Authorization failed: the request was tampered with. Please try connecting again.")}`
    );
  }

  const successUrl = `${connectionsUrl}?success=threads`;
  const errorBase = connectionsUrl;

  try {
    const backendResp = await fetch(
      `${BACKEND_URL}/api/v1/clients/${oauthState.clientId}/connections/threads/callback`,
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
      const err = await backendResp.json().catch(() => ({})) as { detail?: { error?: { message?: string } } };
      return clearCookieRedirect(
        `${errorBase}?error=${encodeURIComponent(err?.detail?.error?.message ?? "Threads connection failed. Please try again.")}`
      );
    }
  } catch {
    return clearCookieRedirect(
      `${errorBase}?error=${encodeURIComponent("Threads connection failed. Please try again.")}`
    );
  }

  return clearCookieRedirect(successUrl);
}
```

### AC 7: Environment variable additions

**Given** the project's `.env.example` and `.env.local.example` files,
**When** the story is complete,
**Then**:

`frontend/.env.local.example` -- add below the existing `NEXT_PUBLIC_META_APP_ID` line:
```
# Threads App (separate from Meta Business App — register at developers.facebook.com under Threads settings)
# Redirect URI: https://personnapress.com/api/auth/threads/callback
NEXT_PUBLIC_THREADS_APP_ID=your-threads-app-id
```

`backend/.env.example` -- add below the existing `META_APP_SECRET` line:
```
# Threads App (separate credentials from Meta Business App)
# Register at: https://developers.facebook.com/apps/ (under Threads settings)
# Redirect URI: https://personnapress.com/api/auth/threads/callback
THREADS_APP_ID=your-threads-app-id
THREADS_APP_SECRET=your-threads-app-secret
```

### AC 8: UI changes in `PlatformConnectionsClient.tsx` -- split connect buttons

**Given** `frontend/components/publishing/PlatformConnectionsClient.tsx`,
**When** the `MetaPlatformsSection` is rendered while not all Meta platforms are connected,
**Then** the section logic is updated to show the correct connect button(s) based on connection state:

**Logic:** Inside `MetaPlatformsSection`, derive:
```tsx
const hasFBIG = connectedItems.some(
  (c) => (c.platform === "instagram" || c.platform === "facebook_page") && c.connected
);
const hasThreads = connectedItems.some(
  (c) => c.platform === "threads" && c.connected
);
```

**Scenario A -- nothing connected:** Show both "Connect Facebook & Instagram" button AND "Connect Threads" button.

**Scenario B -- Instagram/Facebook connected, Threads not:** `hasFBIG` is `true`, `hasThreads` is `false`. Show only "Connect Threads" button (omit "Connect Facebook & Instagram").

**Scenario C -- all three connected:** `MetaPlatformsSection` not rendered at all (existing `!hasAllMetaConnected` guard handles this).

Pass `connectedItems` as a prop to `MetaPlatformsSection`:
```tsx
interface MetaPlatformsSectionProps {
  clientId: string;
  enabled: boolean;
  connectedItems: Array<{ platform: string; connected: boolean }>;
}
```

Update the call site to pass `connectedItems`:
```tsx
{!hasAllMetaConnected && (
  <MetaPlatformsSection
    clientId={clientId}
    enabled={META_PUBLISHING_ENABLED}
    connectedItems={connectedItems}
  />
)}
```

**"Connect Facebook & Instagram" button** (shown when `!hasFBIG && enabled`):
```tsx
<a
  href={`/api/auth/meta?client_id=${clientId}`}
  className="inline-flex items-center justify-center px-5 min-h-[44px] border border-[#111111] text-[#111111] text-xs font-medium rounded-none hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
  aria-label="Connect Facebook and Instagram"
>
  Connect Facebook &amp; Instagram
</a>
```

**"Connect Threads" button** (shown when `!hasThreads && enabled`):
```tsx
<a
  href={`/api/auth/threads?client_id=${clientId}`}
  className="inline-flex items-center justify-center px-5 min-h-[44px] border border-[#111111] text-[#111111] text-xs font-medium rounded-none hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
  aria-label="Connect Threads"
>
  Connect Threads
</a>
```

When both buttons are shown (Scenario A), wrap them in a `flex flex-col gap-2` or `flex gap-2` container. Keep Paper Style (`rounded-none`, `border border-[#111111]`, `text-xs font-medium`).

The locked/disabled button when `!enabled` should remain as a single "Connect Meta Platforms" button (or split into two locked buttons -- either is acceptable, but a single locked button is simpler).

**Update the section title** when `hasFBIG` is true: change label from "Meta Platforms" to "Threads" since the FB/IG platforms are already shown as individual connected cards.

### AC 9: Success toast for Threads in `PlatformConnectionsClient.tsx`

**Given** the `useEffect` success toast handler in `PlatformConnectionsClient.tsx`,
**When** the URL contains `?success=threads`,
**Then** the toast shows `"Threads connected."` (period, no em-dash, no emoji).

Add to the existing message switch block:
```tsx
success === "threads" ? "Threads connected." :
```
Place it alongside the existing `success === "meta"` entry.

### AC 10: Paper Style compliance

**When** any Threads OAuth UI renders (buttons, error states, locked state),
**Then**:
- All surfaces use `rounded-none`
- No emojis anywhere
- Only Lucide icons or `PlatformIcon` -- no external SVGs, no inline SVGs
- No em-dashes (`--` or `—`) in any user-visible text
- Minimum touch target `min-h-[44px]` on all interactive elements
- Error and success patterns match the existing `PlatformConnectionCard.tsx` pattern

---

## Dev Notes

### File Map

| Action | File |
|--------|------|
| CREATE | `backend/app/integrations/threads_auth.py` |
| UPDATE | `backend/app/core/config.py` |
| UPDATE | `backend/app/routers/publishing.py` |
| CREATE | `frontend/app/api/auth/threads/route.ts` |
| CREATE | `frontend/app/api/auth/threads/callback/route.ts` |
| UPDATE | `frontend/components/publishing/PlatformConnectionsClient.tsx` |
| UPDATE | `frontend/.env.local.example` |
| UPDATE | `backend/.env.example` |

### No DB Migration Needed

The `threads` value was added to `platform_enum` in Story 21.1 via Alembic migration. The `platform_connections` table already supports Threads rows. The new credential JSON shape adds `token_acquired_at` (ISO string) vs the old shape from Story 21.1, but since no Threads rows will have valid tokens yet (they are all broken due to the wrong token type), this is a clean slate.

### Threads API Host vs Facebook Graph API Host

**Critical distinction:**
- Meta (Facebook/Instagram): `https://graph.facebook.com/v25.0/...`
- Threads: `https://graph.threads.net/...` (note: `threads.net`, not `facebook.com`)
- Threads token exchange uses `https://graph.threads.net/oauth/access_token` (not `graph.facebook.com`)
- Threads user info uses `https://graph.threads.net/v1.0/me` with `fields=id,username`
- Threads long-lived upgrade uses `https://graph.threads.net/access_token` with `grant_type=th_exchange_token`

The `publish_threads_post` function in `meta.py` already uses `THREADS_GRAPH_BASE = "https://graph.threads.com/v1.0"` -- note the slight difference (`threads.com` for publishing, `threads.net` for auth). The Threads docs as of 2025 show `graph.threads.net` for OAuth and `graph.threads.com` for content publishing. Use `graph.threads.net` for the three new auth functions.

### Existing Publishing Code Is Not Changed

The existing `publish_threads_post` in `meta.py` (used by Story 21.4) remains unchanged. Its credential shape (`threads_user_id`, `user_access_token`) is preserved. The new `threads_auth.py` stores the same field names plus `token_acquired_at`. The publisher (`dispatch_publish`) already reads `creds["threads_user_id"]` and `creds["user_access_token"]` -- these will now be real Threads tokens rather than broken Facebook tokens.

### OAuthCallbackRequest Already Exists

`OAuthCallbackRequest` is defined in `publishing.py` (used by the meta callback). Reuse it -- no new Pydantic model needed:
```python
class OAuthCallbackRequest(BaseModel):
    code: str
```

### Removing Step f -- What to Keep

The `discover_threads_user_id` function in `meta.py` should be left in place (do not delete it). It is likely referenced in `test_meta_integration.py` and removing it would break tests. The meta callback simply stops calling it.

After the Step f removal, also check whether `Optional` from `typing` is still used in `publishing.py`. Look for `Optional[str]` or `Optional[...]` in other parts of the file (e.g., `Optional[str] = None` parameters). If `Optional` is used elsewhere, keep the import. If it was only used for `first_instagram_user_id` and `first_instagram_username`, remove it.

### Threads Token Lifetime

The Threads long-lived token is valid for 60 days (same as Facebook). The `token_acquired_at` field stored in credentials can be used in a future story to implement refresh warnings. This story stores it but does not act on it.

### `datetime` import in `publishing.py`

The endpoint needs `datetime.now(timezone.utc)`. Check whether `from datetime import datetime, timezone` is already in `publishing.py`. If it is not present, add it. Do not use `datetime.utcnow()` (deprecated); use `datetime.now(timezone.utc)`.

### Error Shape Consistency

All error HTTPExceptions in the meta/threads callbacks use this nested shape:
```python
{"error": {"code": "...", "message": "...", "detail": {}}}
```
The frontend callback reads `err?.detail?.error?.message`. Use this exact shape in the threads callback too.

### Frontend Cookie Pattern

Cookie name: `oauth_state_threads` (not `oauth_state_meta`). Each platform has its own cookie namespace to prevent cross-platform state confusion.

### `NEXT_PUBLIC_THREADS_APP_ID` is server-side only in the callback

In `frontend/app/api/auth/threads/route.ts`, `NEXT_PUBLIC_THREADS_APP_ID` is read server-side inside a Route Handler. Despite the `NEXT_PUBLIC_` prefix (which makes it available client-side too), reading it in a Route Handler with `process.env.NEXT_PUBLIC_THREADS_APP_ID` works correctly because Route Handlers are server-side code. This matches how `NEXT_PUBLIC_META_APP_ID` is used in `meta/route.ts`.

### `META_PUBLISHING_ENABLED` Feature Flag Applies to Threads Too

The existing `META_PUBLISHING_ENABLED` flag (`process.env.NEXT_PUBLIC_META_PUBLISHING_ENABLED === "true"`) gates whether the connect buttons are enabled. The "Connect Threads" button should also be gated behind this same flag -- if `!enabled`, show a single locked state. A separate `THREADS_PUBLISHING_ENABLED` flag is not needed.

### `hasAllMetaConnected` Logic -- No Change Needed

The existing logic:
```tsx
const hasAllMetaConnected =
  META_PLATFORMS.size > 0 &&
  [...META_PLATFORMS].every((p) => connectedItems.some((c) => c.platform === p && c.connected));
```
`META_PLATFORMS = new Set(["instagram", "facebook_page", "threads"])` includes `threads`. This means `hasAllMetaConnected` is only `true` when all three are connected. The `MetaPlatformsSection` still hides when all three are connected. No change to this logic.

### UI Layout for Two Buttons

When both "Connect Facebook & Instagram" and "Connect Threads" buttons appear (Scenario A), a clean layout:
```tsx
<div className="flex flex-col gap-2">
  {!hasFBIG && enabled && (
    <a href={`/api/auth/meta?client_id=${clientId}`} ...>Connect Facebook & Instagram</a>
  )}
  {!hasThreads && enabled && (
    <a href={`/api/auth/threads?client_id=${clientId}`} ...>Connect Threads</a>
  )}
</div>
```

### Dynamic Section Label

When `hasFBIG` (Instagram/Facebook already connected), change the label and description:
```tsx
<p className="text-xs font-medium uppercase tracking-[0.06em] text-[#111111]">
  {hasFBIG ? "Threads" : "Meta Platforms"}
</p>
<p className="text-xs text-[#555555] mt-0.5">
  {hasFBIG ? "Connect your Threads account" : "Instagram, Facebook Page, and Threads"}
</p>
```

And in the icon row, when `hasFBIG`, show only the Threads icon:
```tsx
<div className="flex items-center gap-1.5 mb-1">
  {!hasFBIG && (
    <>
      <PlatformIcon platform="instagram" className="size-4 text-graphite" color="mono" aria-hidden="true" />
      <PlatformIcon platform="facebook_page" className="size-4 text-graphite" color="mono" aria-hidden="true" />
    </>
  )}
  <PlatformIcon platform="threads" className="size-4 text-graphite" color="mono" aria-hidden="true" />
</div>
```

---

## Tasks / Subtasks

- [x] Create `backend/app/integrations/threads_auth.py` (AC 1)
  - [x] `exchange_code_for_short_lived_token` -- POST to graph.threads.net/oauth/access_token
  - [x] `exchange_short_lived_for_long_lived_token` -- GET graph.threads.net/access_token with th_exchange_token
  - [x] `get_threads_user` -- GET graph.threads.net/v1.0/me?fields=id,username
- [x] Update `backend/app/core/config.py` -- add `THREADS_APP_ID` and `THREADS_APP_SECRET` (AC 2)
- [x] Update `backend/app/routers/publishing.py` (AC 3, AC 4)
  - [x] Import `threads_auth` from `app.integrations.threads_auth`
  - [x] Add `datetime`/`timezone` import if missing
  - [x] Add `threads_oauth_callback` endpoint with 5-step flow
  - [x] Remove Step f block (Threads piggyback discovery)
  - [x] Remove `first_instagram_user_id` and `first_instagram_username` variables
  - [x] Check and clean up `Optional` import if no longer used
- [x] Create `frontend/app/api/auth/threads/route.ts` (AC 5)
- [x] Create `frontend/app/api/auth/threads/callback/route.ts` (AC 6)
- [x] Update `frontend/.env.local.example` -- add `NEXT_PUBLIC_THREADS_APP_ID` (AC 7)
- [x] Update `backend/.env.example` -- add `THREADS_APP_ID` and `THREADS_APP_SECRET` (AC 7)
- [x] Update `frontend/components/publishing/PlatformConnectionsClient.tsx` (AC 8, AC 9)
  - [x] Add `connectedItems` prop to `MetaPlatformsSection`
  - [x] Derive `hasFBIG` and `hasThreads` inside `MetaPlatformsSection`
  - [x] Conditional "Connect Facebook & Instagram" button (shown when `!hasFBIG`)
  - [x] Conditional "Connect Threads" button (href `/api/auth/threads`)
  - [x] Dynamic label/description/icon row based on `hasFBIG`
  - [x] Pass `connectedItems` to `MetaPlatformsSection` call site
  - [x] Add `success === "threads"` toast handler

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Created `threads_auth.py` with three async functions using `httpx.AsyncClient(timeout=10.0)` and `graph.threads.net` host for OAuth (separate from `graph.threads.com` used by publisher).
- Added `THREADS_APP_ID` / `THREADS_APP_SECRET` to `Settings` in `config.py` after `META_APP_SECRET`.
- Added `threads_oauth_callback` POST endpoint in `publishing.py` (5-step flow: short-lived → long-lived token → user info → upsert with `token_acquired_at`).
- Removed Step f piggyback block from `meta_oauth_callback`; replaced `not first_instagram_user_id` guard with `"instagram" not in connected_platforms`; removed `first_instagram_user_id` and `first_instagram_username` variables. `Optional` import retained (still used elsewhere in file).
- Created frontend route handlers: `threads/route.ts` (initiates OAuth with `oauth_state_threads` cookie) and `threads/callback/route.ts` (handles callback, posts to backend, redirects with `?success=threads`).
- Updated `MetaPlatformsSection` with `connectedItems` prop; derives `hasFBIG` / `hasThreads` to show split buttons (Scenario A: both buttons; Scenario B: only Threads button). Dynamic label/icon row based on `hasFBIG`.
- Added `success === "threads" ? "Threads connected." :` to toast switch.
- Updated 2 existing tests that validated old Step f behavior; added 8 new tests (5 for `threads_auth.py`, 3 for `threads_oauth_callback`). All 46 tests in `test_meta_integration.py` pass.

### File List

- backend/app/integrations/threads_auth.py (CREATED)
- backend/app/core/config.py (MODIFIED)
- backend/app/routers/publishing.py (MODIFIED)
- frontend/app/api/auth/threads/route.ts (CREATED)
- frontend/app/api/auth/threads/callback/route.ts (CREATED)
- frontend/components/publishing/PlatformConnectionsClient.tsx (MODIFIED)
- frontend/.env.local.example (MODIFIED)
- backend/.env.example (MODIFIED)
- backend/tests/test_meta_integration.py (MODIFIED)

### Review Findings

- [x] [Review][Patch] `access_token` KeyError on success response [backend/app/integrations/threads_auth.py:33,54] — fixed: use `.get()` + explicit PlatformError instead of bare key access
- [x] [Review][Patch] `code` null forwarded to backend in callback [frontend/app/api/auth/threads/callback/route.ts:50] — fixed: early return if `!code` before CSRF check
- [x] [Review][Patch] httpx patched globally in tests instead of module-scoped [backend/tests/test_meta_integration.py] — fixed: `patch("app.integrations.threads_auth.httpx.AsyncClient")`
- [x] [Review][Defer] APP_URL trailing slash risk in redirect_uri — same pre-existing pattern as meta OAuth [backend/app/routers/publishing.py, frontend/app/api/auth/threads/route.ts] — deferred, pre-existing
- [x] [Review][Defer] clientId not UUID-validated in route.ts — node URL resolution prevents open redirect, backend FastAPI UUID type guards exploitation [frontend/app/api/auth/threads/route.ts] — deferred, pre-existing
- [x] [Review][Defer] No rate limiting on threads callback endpoint — pre-existing pattern across all OAuth endpoints [backend/app/routers/publishing.py] — deferred, pre-existing
- [x] [Review][Defer] THREADS_APP_ID/SECRET no startup validation for empty strings — same as META_APP_ID/META_APP_SECRET pattern [backend/app/core/config.py] — deferred, pre-existing
- [x] [Review][Defer] Backend error message reflected to redirect URL — same as meta callback pattern [frontend/app/api/auth/threads/callback/route.ts] — deferred, pre-existing
- [x] [Review][Defer] DB failure after token exchange leaves valid token unstored — user re-auths, gets new token, resolves itself [backend/app/routers/publishing.py] — deferred, acceptable
- [x] [Review][Defer] Stale Threads credentials from old meta piggyback remain in DB — operational migration concern, no code fix needed [backend/app/routers/publishing.py] — deferred, operational
- [x] [Review][Defer] Cookie cleared on network failure to backend — safe behavior, matches meta callback pattern [frontend/app/api/auth/threads/callback/route.ts] — deferred, pre-existing
