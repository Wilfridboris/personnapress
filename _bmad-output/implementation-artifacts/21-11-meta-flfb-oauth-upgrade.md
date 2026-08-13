---
baseline_commit: e0f9f23
---

# Story 21.11: Meta FLfB OAuth Upgrade

Status: done

---

## Story

As a PersonnaPress user connecting Meta platforms,
I want the OAuth flow to use Facebook Login for Business (config_id) instead of scope-based Standard Login,
so that I can select my Business Portfolio pages and Instagram accounts -- not just pages tied to my personal account -- during the Meta connect flow.

As a PersonnaPress user who encounters a Meta connection error,
I want to see a safe, user-friendly error message,
so that partial OAuth credentials are never exposed in the browser URL bar, error toasts, or server logs.

---

## Context & Motivation

### The Business Portfolio gap

The current Meta OAuth in `frontend/app/api/auth/meta/route.ts` uses:
```
scope=instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,pages_manage_posts
```
This is Standard Facebook Login. The subsequent `/me/accounts` call only returns Facebook Pages where the authenticated **personal** user is a direct admin. Pages owned by a Business Portfolio where the user has delegated access -- but is not a direct page admin -- are invisible. This is the root cause of "I can't see my Business Portfolio pages."

**Facebook Login for Business (FLfB)** with a User access token replaces `scope` with a `config_id` that points to a pre-configured permission set. During the OAuth dialog, Meta shows a **business asset picker**: the user selects their Business Portfolio, then chooses which Pages and Instagram accounts to grant. The resulting `/me/accounts` call returns exactly those selected pages -- including Business Portfolio pages.

**`override_default_response_type` is NOT used.** That flag is only required for System User Access Tokens (SUAT/BISU). For User access tokens -- which is what PersonnaPress uses -- the existing `response_type=code` flow is correct and unchanged.

### Security leak

Meta returns raw error messages that echo back incorrect credential values:
```
"Invalid client_secret: a45473be1dc8d4fefb282343fa"
```
`_platform_error_msg` in `publishing.py` passes this string directly into the HTTP 400 response. The frontend callback at `callback/route.ts:80` then puts `err.detail.error.message` verbatim into the `?error=` URL query parameter. The result: the partial secret is visible in the browser address bar and stored in browser history.

Two fixes: (1) sanitize `_platform_error_msg` to never forward raw Meta API error strings; (2) the frontend callback maps on the error `code` field, not `message`.

### Graph API version

`meta.py` uses `META_API_VERSION = "v25.0"`. Meta released v26.0 on July 29, 2026. Update to v26.0.

### What is NOT changing

- `discover_accounts` -- still calls `/me/accounts`, still returns exactly what the user granted
- Token exchange logic -- same code → short-lived → long-lived flow, same endpoints
- Threads OAuth -- completely separate app (`graph.threads.net`), separate route (`/api/auth/threads`), untouched
- Database schema -- no migrations needed
- `META_PUBLISHING_ENABLED` gate and beta unlock logic -- untouched
- Publishing functions (`publish_instagram_feed_post`, `publish_facebook_page_post`, `publish_threads_post`) -- untouched

---

## External Prerequisite (Boris does this before devving the story)

The story code cannot be tested without a FLfB Configuration ID from the Meta App Dashboard.

**Steps:**
1. Go to [Meta App Dashboard](https://developers.facebook.com/apps/) and select the Facebook/Instagram app
2. Settings > Basic -- confirm App Type is **Business** (not None)
3. Left sidebar: Add product **Facebook Login for Business**
4. Facebook Login for Business > **Configurations** > **+ Create configuration**
5. Configure:
   - Name: `PersonnaPress Connect`
   - Token type: **User access token**
   - Permissions: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`
6. Click **Create** -- copy the generated **Configuration ID** (a 16-digit number like `1234567890123456`)
7. Put it in `frontend/.env` (local dev) and production env:
   ```
   NEXT_PUBLIC_META_OAUTH_CONFIG_ID=1234567890123456
   ```

---

## Acceptance Criteria

### AC 1: FLfB config_id replaces scope in OAuth initiation

**Given** `NEXT_PUBLIC_META_OAUTH_CONFIG_ID` is set and `NEXT_PUBLIC_META_APP_ID` is set,
**When** the user navigates to `GET /api/auth/meta?client_id={id}`,
**Then** the redirect URL to `https://www.facebook.com/v25.0/dialog/oauth` includes:
- `client_id={NEXT_PUBLIC_META_APP_ID}` (unchanged)
- `redirect_uri={APP_URL}/api/auth/meta/callback` (unchanged)
- `response_type=code` (unchanged)
- `state={randomHex32}` (unchanged)
- `config_id={NEXT_PUBLIC_META_OAUTH_CONFIG_ID}` ← **NEW**
- NO `scope` parameter ← **REMOVED**

**And** `override_default_response_type` is NOT added (not needed for User access token flow).

**Given** `NEXT_PUBLIC_META_OAUTH_CONFIG_ID` is missing or empty,
**When** the user navigates to `GET /api/auth/meta`,
**Then** the route returns `{ error: "Meta OAuth is not configured" }` with status 500 (same pattern as missing `metaAppId`).

---

### AC 3: Backend error sanitization -- no credential leak

**Given** Meta's token exchange API returns an error response that includes credential values (e.g. `"Invalid client_secret: abc123"`),
**When** `exchange_code_for_short_lived_token` or `exchange_short_lived_for_long_lived_token` raises `PlatformError`,
**Then** `_platform_error_msg` returns a safe, non-credential string such as `"Meta authorization failed. Please reconnect your Meta account."` -- never the raw Meta API error message.

**Implementation rule for `_platform_error_msg`:** If the exception is a `PlatformError` and its `.message` contains any of the substrings `client_secret`, `access_token`, `appsecret`, `client_id` (case-insensitive), return the safe fallback string for that platform instead of the raw message. All other exceptions pass through `str(e)` unchanged.

Safe fallback strings by error code:
- `TOKEN_EXCHANGE_FAILED` → `"Meta authorization failed. Please try connecting again."`
- `ACCOUNT_DISCOVERY_FAILED` → `"Could not fetch your Facebook Pages. Ensure your Instagram is linked to a Facebook Page and try again."`

---

### AC 4: Backend OAuth failures are logged

**Given** any of the three Meta OAuth steps fail (short-lived exchange, long-lived exchange, account discovery),
**When** the exception is caught in `meta_oauth_callback`,
**Then** `logger.warning("Meta OAuth step failed: %s", _platform_error_msg(e), exc_info=True)` is called before raising `HTTPException`.

Same requirement applies to `threads_oauth_callback` for its TOKEN_EXCHANGE_FAILED step (the Threads secret bug that prompted this story).

---

### AC 5: Frontend callback -- safe error in URL

**Given** the backend returns a non-OK response from `POST .../connections/meta/callback`,
**When** `frontend/app/api/auth/meta/callback/route.ts` handles the error,
**Then** the `?error=` query parameter appended to the redirect URL contains a **user-friendly string mapped from `err.detail.error.code`**, not the raw `err.detail.error.message`.

**Mapping (implement as a local `const` in the callback route):**
```typescript
const SAFE_META_ERRORS: Record<string, string> = {
  TOKEN_EXCHANGE_FAILED: "Meta authorization failed. Please try connecting again.",
  ACCOUNT_DISCOVERY_FAILED: "Could not fetch your Facebook Pages. Ensure your Instagram is linked to a Facebook Page, then reconnect.",
};
const safeMessage = SAFE_META_ERRORS[err?.detail?.error?.code ?? ""] ?? "Meta connection failed. Please try again.";
```

The `err.detail.error.message` field must NOT appear in the redirect URL under any circumstance.

---

### AC 6: UX explainer callout in MetaPlatformsSection

**Given** `enabled=true` and `!hasFBIG` (Facebook/Instagram not yet connected),
**When** the MetaPlatformsSection renders in `PlatformConnectionsClient.tsx`,
**Then** a one-line info note appears below the "Connect Facebook & Instagram" button:
- `Info` Lucide icon (size-3, `text-[#555555]`, `aria-hidden="true"`)
- Text: `"You'll be asked to select your Business Portfolio and choose which Pages and Instagram accounts to connect."`
- Typography: `text-xs text-[#555555]`
- Layout: `flex items-start gap-1 mt-2` (tight, non-intrusive; sits below the button)
- Paper Style: `rounded-none`, no emojis, no em-dashes, CSS transition only (no Framer Motion)

The note renders **only** when the enabled state shows the connect button, not in the locked/beta-gate state.

---

### AC 7: Env var documentation updated

**Given** the story is complete,
**When** a developer reads the env example files,
**Then**:

`frontend/.env.local.example` gains (near `NEXT_PUBLIC_META_APP_ID`):
```
# Facebook Login for Business Configuration ID
# 1. In Meta App Dashboard, add "Facebook Login for Business" product
# 2. Go to Configurations > + Create configuration (User access token, required permissions)
# 3. Copy the Configuration ID shown after saving
NEXT_PUBLIC_META_OAUTH_CONFIG_ID=your-flfb-config-id
```

`frontend/.env.example` gains (near `NEXT_PUBLIC_META_APP_ID`):
```
# Facebook Login for Business Configuration ID (from Meta App Dashboard > FLfB > Configurations)
NEXT_PUBLIC_META_OAUTH_CONFIG_ID=REPLACE_WITH_FLFB_CONFIG_ID
```

No backend env changes -- `META_APP_ID` and `META_APP_SECRET` already exist in `backend/.env.example`.

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/routers/publishing.py` | Sanitize `_platform_error_msg`; add `logger.warning()` in `meta_oauth_callback` and `threads_oauth_callback` |
| `frontend/app/api/auth/meta/route.ts` | Replace `scope` with `config_id`; add `NEXT_PUBLIC_META_OAUTH_CONFIG_ID` guard; bump dialog URL to v26.0 |
| `frontend/app/api/auth/meta/callback/route.ts` | Map error by `code` not `message` in redirect URL |
| `frontend/components/publishing/PlatformConnectionsClient.tsx` | Add UX explainer note in `MetaPlatformsSection` |
| `frontend/.env.local.example` | Document `NEXT_PUBLIC_META_OAUTH_CONFIG_ID` |
| `frontend/.env.example` | Document `NEXT_PUBLIC_META_OAUTH_CONFIG_ID` |

---

## Dev Notes

### AC 1 -- exact route.ts diff

**Current** (`frontend/app/api/auth/meta/route.ts`):
```typescript
const metaAppId = process.env.NEXT_PUBLIC_META_APP_ID;
if (!metaAppId) {
  return NextResponse.json({ error: "Meta OAuth is not configured" }, { status: 500 });
}
// ...
const authUrl = new URL("https://www.facebook.com/v25.0/dialog/oauth");
authUrl.searchParams.set("client_id", metaAppId);
authUrl.searchParams.set("redirect_uri", `${APP_URL}/api/auth/meta/callback`);
authUrl.searchParams.set("response_type", "code");
authUrl.searchParams.set("state", state);
authUrl.searchParams.set(
  "scope",
  "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,pages_manage_posts"
);
```

**After:**
```typescript
const metaAppId = process.env.NEXT_PUBLIC_META_APP_ID;
const metaConfigId = process.env.NEXT_PUBLIC_META_OAUTH_CONFIG_ID;
if (!metaAppId || !metaConfigId) {
  return NextResponse.json({ error: "Meta OAuth is not configured" }, { status: 500 });
}
// ...
const authUrl = new URL("https://www.facebook.com/v25.0/dialog/oauth");  // version unchanged
authUrl.searchParams.set("client_id", metaAppId);
authUrl.searchParams.set("redirect_uri", `${APP_URL}/api/auth/meta/callback`);
authUrl.searchParams.set("response_type", "code");
authUrl.searchParams.set("state", state);
authUrl.searchParams.set("config_id", metaConfigId);
// scope removed -- FLfB config_id defines permissions
```

Do NOT add `override_default_response_type` -- that is only for System User access tokens, not User access tokens.

### AC 3 -- `_platform_error_msg` sanitization

**Current** (`backend/app/routers/publishing.py:281-284`):
```python
def _platform_error_msg(e: Exception) -> str:
    """Extract a safe, serializable message from a platform exception."""
    msg = getattr(e, "message", None)
    return str(msg) if msg is not None else str(e)
```

**After:**
```python
_CREDENTIAL_SUBSTRINGS = frozenset(["client_secret", "access_token", "appsecret", "client_id"])

_SAFE_PLATFORM_MSGS: dict[str, str] = {
    "meta": "Meta authorization failed. Please try connecting again.",
    "threads": "Threads authorization failed. Please try connecting again.",
}

def _platform_error_msg(e: Exception) -> str:
    """Return a safe, non-credential error message for HTTP responses."""
    msg = getattr(e, "message", None)
    raw = str(msg) if msg is not None else str(e)
    platform = getattr(e, "platform", "")
    if any(sub in raw.lower() for sub in _CREDENTIAL_SUBSTRINGS):
        return _SAFE_PLATFORM_MSGS.get(platform, "Authorization failed. Please try connecting again.")
    return raw
```

### AC 4 -- logger.warning placement

In `meta_oauth_callback`, each of the three `except Exception as e` blocks gains a `logger.warning` before the `raise HTTPException`:

```python
    except Exception as e:
        logger.warning("Meta OAuth token exchange failed: %s", _platform_error_msg(e), exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "TOKEN_EXCHANGE_FAILED", "message": _platform_error_msg(e), "detail": {}}},
        )
```

Same pattern for `ACCOUNT_DISCOVERY_FAILED`. In `threads_oauth_callback`, add the same `logger.warning` to the `TOKEN_EXCHANGE_FAILED` and `USER_FETCH_FAILED` blocks.

### AC 5 -- callback/route.ts error handling

**Current** (`frontend/app/api/auth/meta/callback/route.ts:77-81`):
```typescript
if (!backendResp.ok) {
  const err = await backendResp.json().catch(() => ({})) as { detail?: { error?: { message?: string } } };
  return clearCookieRedirect(
    `${errorBase}?error=${encodeURIComponent(err?.detail?.error?.message ?? "Meta connection failed. Please try again.")}`
  );
}
```

**After:**
```typescript
if (!backendResp.ok) {
  const err = await backendResp.json().catch(() => ({})) as { detail?: { error?: { code?: string } } };
  const SAFE_META_ERRORS: Record<string, string> = {
    TOKEN_EXCHANGE_FAILED: "Meta authorization failed. Please try connecting again.",
    ACCOUNT_DISCOVERY_FAILED: "Could not fetch your Facebook Pages. Ensure your Instagram is linked to a Facebook Page, then reconnect.",
  };
  const safeMessage = SAFE_META_ERRORS[err?.detail?.error?.code ?? ""] ?? "Meta connection failed. Please try again.";
  return clearCookieRedirect(
    `${errorBase}?error=${encodeURIComponent(safeMessage)}`
  );
}
```

### AC 6 -- UX explainer placement in MetaPlatformsSection

The note sits immediately after (below) the "Connect Facebook & Instagram" `<a>` tag, still inside the `!hasFBIG` block:

```tsx
{!hasFBIG && (
  <>
    <a
      href={`/api/auth/meta?client_id=${clientId}`}
      className="inline-flex items-center justify-center px-5 min-h-[44px] border border-[#111111] ..."
      aria-label="Connect Facebook and Instagram"
    >
      Connect Facebook &amp; Instagram
    </a>
    <p className="flex items-start gap-1 mt-2 text-xs text-[#555555]">
      <Info className="size-3 mt-0.5 shrink-0" aria-hidden="true" />
      You&apos;ll be asked to select your Business Portfolio and choose which Pages and Instagram accounts to connect.
    </p>
  </>
)}
```

Import `Info` from `lucide-react` at the top of the file -- check if `Info` is already imported before adding it.

---

## Key Constraints (do not violate)

- **No `override_default_response_type`** -- not needed, not wanted, do not add
- **`scope` param fully removed** -- do not leave it alongside `config_id`
- **Threads OAuth files untouched** -- `threads_auth.py`, `/api/auth/threads/route.ts`, `threads_oauth_callback` in publishing.py are out of scope (except adding `logger.warning` to threads_oauth_callback per AC 4)
- **`discover_accounts` unchanged** -- the `/me/accounts` call stays exactly as-is
- **Token exchange unchanged** -- the short-lived → long-lived exchange in `meta.py` stays exactly as-is
- **Paper Style** -- `rounded-none`, Lucide icons only, no emojis, no em-dashes in any user-facing string
- **No Framer Motion** -- the info note is static; CSS `transition-colors` is the only animation needed anywhere in this story
- **No new DB migrations** -- this story touches no database schema

---

## Tests to Write

### Backend

1. `test__platform_error_msg_sanitizes_client_secret` -- given a `PlatformError("meta", 400, "Invalid client_secret: abc123")`, assert `_platform_error_msg(e)` returns the safe string and NOT the raw message
2. `test__platform_error_msg_sanitizes_access_token` -- same for a message containing `access_token`
3. `test__platform_error_msg_passes_through_safe_message` -- given a `PlatformError("meta", 429, "Rate limit exceeded")`, assert the message passes through unchanged
4. `test_meta_oauth_callback_token_exchange_failure_logs_warning` -- mock `exchange_code_for_short_lived_token` to raise `PlatformError`, assert `logger.warning` is called and the response `message` does not contain `client_secret`

### Frontend

No new test files required -- the callback route change is a straightforward mapping; rely on manual QA.

---

## Sources

- [Facebook Login for Business](https://developers.facebook.com/documentation/facebook-login/facebook-login-for-business) -- config_id replaces scope; override_default_response_type for SUAT only
- [Introducing Graph API v26.0](https://developers.facebook.com/blog/post/2026/07/29/introducing-graph-api-v26-and-marketing-api-v26/) -- current stable version (released July 29, 2026)
- [Manually Build a Login Flow](https://developers.facebook.com/documentation/facebook-login/guides/advanced/manual-flow) -- manual redirect with config_id as optional parameter

---

## File List

- `backend/app/routers/publishing.py`
- `frontend/app/api/auth/meta/route.ts`
- `frontend/app/api/auth/meta/callback/route.ts`
- `frontend/components/publishing/PlatformConnectionsClient.tsx`
- `frontend/.env.local.example`
- `frontend/.env.example`
- `backend/tests/test_meta_integration.py`

---

## Dev Agent Record

### Implementation Notes

- AC 1: Replaced `scope` param with `config_id={NEXT_PUBLIC_META_OAUTH_CONFIG_ID}` in `route.ts`. Added guard: returns 500 if either `metaAppId` or `metaConfigId` is missing. OAuth dialog URL version kept at `v25.0` (unchanged per AC 1 and dev notes).
- AC 3: Replaced `_platform_error_msg` with a sanitized version using `_CREDENTIAL_SUBSTRINGS` frozenset; returns platform-specific safe fallback when credential substrings detected in error message.
- AC 4: Added `logger.warning(...)` with `exc_info=True` before each `raise HTTPException` in `meta_oauth_callback` (all 3 steps) and `threads_oauth_callback` (steps a, b, c).
- AC 5: Frontend callback now maps error by `code` field using `SAFE_META_ERRORS` dict; `err.detail.error.message` never appears in redirect URL.
- AC 6: Added `Info` import from `lucide-react`; UX explainer `<p>` placed immediately after the "Connect Facebook & Instagram" `<a>` inside the `!hasFBIG` conditional.
- AC 7: Added `NEXT_PUBLIC_META_OAUTH_CONFIG_ID` to both `.env.local.example` and `.env.example` with full setup comments.
- Backend tests: 4 new tests added to `test_meta_integration.py` -- all pass (70 total, no regressions).

---

### Review Findings

- [x] [Review][Patch] PlatformError.__init__ baked raw message into str(e) -- exc_info=True logged credentials to server [backend/app/core/exceptions.py] -- fixed: super().__init__ no longer includes {message}
- [x] [Review][Patch] _platform_error_msg used per-platform fallback; ACCOUNT_DISCOVERY_FAILED got TOKEN_EXCHANGE_FAILED safe message [backend/app/routers/publishing.py] -- fixed: per-error-code _SAFE_ERROR_MSGS dict; callers pass error_code
- [x] [Review][Patch] Frontend ACCOUNT_DISCOVERY_FAILED text said "then reconnect." -- spec says "and try again." [frontend/app/api/auth/meta/callback/route.ts] -- fixed
- [x] [Review][Patch] Warning assertion did not verify logged message was sanitized [backend/tests/test_meta_integration.py] -- fixed: added call_args credential assertions

---

## Change Log

- 2026-08-13: Story 21.11 implemented -- FLfB config_id OAuth upgrade, credential error sanitization, logger.warning in OAuth callbacks, safe frontend error mapping, UX Business Portfolio explainer, env var docs. 4 backend tests added.
- 2026-08-13: Code review complete -- 4 patches applied (PlatformError.__init__ credential leak via exc_info, _platform_error_msg per-error-code fallbacks, ACCOUNT_DISCOVERY_FAILED wording, warning assertion), 9 dismissed.
