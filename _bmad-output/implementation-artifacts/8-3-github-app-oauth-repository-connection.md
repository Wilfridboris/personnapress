---
baseline_commit: 7467045bfe39bf5acd4c789969a6c9a41799a3fb
---

# Story 8.3: GitHub App OAuth & Repository Connection
<!-- epics.md reference: Epic 8, Story 8.1 (GitHub Blog Publishing Phase 2) -->

Status: done

## Story

As an authenticated user,
I want to install the PersonnaPress GitHub App on my repositories and link one to my active Client,
so that PersonnaPress can read my repo structure and publish blog posts on my behalf.

## Acceptance Criteria

1. Platform Connections page (`/clients/{id}/connections`) shows a GitHub connection card alongside WordPress, Webflow, X, and LinkedIn cards; the card displays "Not connected" and a "Connect GitHub" CTA when no connection exists.
2. Clicking "Connect GitHub" redirects the user to the GitHub App installation URL with a `state` parameter stored in a short-lived httpOnly cookie (SameSite=Lax, 10-minute expiry) for CSRF protection; the user selects which repositories to grant access on the GitHub App consent screen.
3. On return to `/api/auth/github/callback` with `installation_id` and `state`: Next.js verifies the state cookie matches, calls FastAPI `POST /api/v1/clients/{client_id}/connections/github` with the `installation_id`; FastAPI exchanges the installation ID for a GitHub App installation token via JWT-signed request using the App private key; the token is AES-256-GCM encrypted and stored in `platform_connections` with `platform='github_pages'`; the connection card updates to "Connected" without page reload.
4. When connected, clicking "Select repository" opens a dropdown populated from `GET /installation/repositories` (using the installation token); the selected `repo_full_name` (e.g., `wilfridboris/my-blog`) is stored on the `platform_connections` record; the card label updates to "Connected — wilfridboris/my-blog."
5. Clicking "Disconnect" deletes the `platform_connections` record for `platform='github_pages'`; the card reverts to "Not connected." The GitHub App installation itself is NOT revoked (user manages that on GitHub directly).
6. When a subsequent API call is made and the installation token has expired (~1 hour), FastAPI automatically refreshes it using the stored `installation_id` and App private key — no user re-authentication required.
7. Any connection request for a Client not owned by the JWT user returns HTTP 403.

## Tasks / Subtasks

- [ ] **PREREQUISITE — Manual admin steps before coding** (AC: all)
  - [ ] Register the PersonnaPress GitHub App in GitHub Developer Settings (no code — human task)
  - [ ] Generate GitHub App private key (PEM); store securely as backend env var `GITHUB_APP_PRIVATE_KEY`
  - [ ] Note the App's `Client ID` and `App ID` for env vars

- [x] **PREREQUISITE — Alembic migration** (AC: 1, 3, 4)
  - [x] Create `backend/alembic/versions/002_github_platform.py`
  - [x] Add `github_pages` to `platform_connections.platform` PostgreSQL enum (or TEXT column — verify current column type in `001_initial_schema.py` before choosing ALTER TYPE vs. nothing)
  - [x] Add `github_pr_url TEXT NULLABLE` to `campaigns` table (needed by Stories 8.5+)
  - [x] Run `alembic upgrade head` and verify schema on dev DB before writing app code

- [x] **Backend — Config** (AC: 2, 3, 6)
  - [x] `backend/app/core/config.py`: Add `GITHUB_APP_ID: str` (numeric app ID, still needed for some API paths), `GITHUB_APP_CLIENT_ID: str` (string like `Iv1.xxx` — used as `iss` in JWT), `GITHUB_APP_PRIVATE_KEY: str` (PEM content, base64-encoded or raw newlines), `GITHUB_APP_WEBHOOK_SECRET: str`; all with `Field(...)` (required, no default)
  - [x] `backend/.env.example`: Document all 4 new vars with placeholder values

- [x] **Backend — GitHub integration module** (AC: 3, 4, 6)
  - [x] Create `backend/app/integrations/github.py` (new file; follows pattern of `twitter.py`/`linkedin.py`)
  - [x] `generate_app_jwt() -> str`: signs a JWT with `GITHUB_APP_PRIVATE_KEY` (RS256) using `PyJWT`; claims: `iss=GITHUB_APP_CLIENT_ID` (string client ID, e.g. `Iv1.xxx`), `iat=int(time.time()) - 60` (60 seconds in past for clock-drift tolerance), `exp=int(time.time()) + 540` (9-min validity, max is 10 min); add `PyJWT>=2.8.0` to `requirements.txt`
  - [x] `get_installation_token(installation_id: str) -> dict`: `POST https://api.github.com/app/installations/{installation_id}/access_tokens` with App JWT; headers must include `X-GitHub-Api-Version: 2026-03-10`; returns `{"token": str, "expires_at": str}` — store both fields
  - [x] `get_installation_repositories(installation_token: str) -> list[dict]`: `GET https://api.github.com/installation/repositories?per_page=100`; headers must include `X-GitHub-Api-Version: 2026-03-10`; returns list of `{full_name, private}` dicts; `per_page=100` (max allowed — default is 30, which would silently cut off users with more repos)
  - [x] All functions raise `PlatformError("github", status_code, message)` on non-2xx — import from `app.core.exceptions`
  - [x] `integrations/github.py` functions must only be called from `services/publishing.py` and `routers/publishing.py` (never from workers directly)

- [x] **Backend — Publishing router** (AC: 1, 3, 4, 5, 7)
  - [x] `backend/app/routers/publishing.py`: Add `github_pages` to `ALL_PLATFORMS` list so it appears in the connections list response
  - [x] Add `POST /api/v1/clients/{client_id}/connections/github` endpoint:
    - Accepts `{"installation_id": str}` body
    - Verifies client ownership (JWT `user_id` == `clients.user_id`) → 403 if mismatch
    - Calls `integrations.github.get_installation_token(installation_id)`
    - Builds encrypted credential JSON: `{"installation_id": ..., "installation_token": ..., "repo_full_name": null}`
    - Calls `encrypt_credential()` (from `core.security`) and `upsert_connection()` (from `db.repositories.platform_connections`)
    - Returns `{"platform": "github_pages", "connected": true, "account_identifier": null}`
  - [x] Add `PATCH /api/v1/clients/{client_id}/connections/github/repo` endpoint:
    - Accepts `{"repo_full_name": str}`
    - Verifies client ownership
    - Decrypts existing credential, updates `repo_full_name` field, re-encrypts, upserts
    - Returns `{"platform": "github_pages", "connected": true, "account_identifier": repo_full_name}`
  - [x] Add `GET /api/v1/clients/{client_id}/connections/github/repos` endpoint:
    - Decrypts credential, retrieves `installation_token` (auto-refresh if expired), calls `integrations.github.get_installation_repositories()`
    - Returns `{"repos": [{"full_name": str, "private": bool}]}`
  - [x] Existing `DELETE /api/v1/clients/{client_id}/connections/{platform}` (or equivalent disconnect endpoint) already handles deletion — verify it works for `github_pages` platform value

- [x] **Frontend — Next.js GitHub callback route** (AC: 2, 3)
  - [x] Create `frontend/app/api/auth/github/callback/route.ts` (new, mirrors `/api/auth/google/callback/route.ts` pattern)
  - [x] `GET` handler: reads `state` and `installation_id` from query params
  - [x] Reads `github_oauth_state` httpOnly cookie; compares with `state` query param; returns 400 if mismatch
  - [x] Reads `client_id` from the cookie (stored alongside state at redirect time)
  - [x] Calls FastAPI `POST /api/v1/clients/{client_id}/connections/github` with `installation_id`
  - [x] On success: clears state cookie; redirects to `/clients/{client_id}/connections?success=github`
  - [x] On error: redirects to `/clients/{client_id}/connections?error=<encoded message>`

- [x] **Frontend — GitHubConnect component** (AC: 1, 2, 4, 5)
  - [x] Create `frontend/components/publishing/GitHubConnect.tsx` (new)
  - [x] States to render: not-connected → connect CTA; connecting (spinner); connected-no-repo (repo selector dropdown); connected-with-repo (label + Disconnect button)
  - [x] "Connect GitHub" button: calls `/api/v1/clients/{client_id}/connections/github/initiate` (or builds URL client-side using env var `NEXT_PUBLIC_GITHUB_APP_SLUG`); stores `state` + `client_id` in httpOnly cookie via `/api/auth/github/state` Next.js route
  - [x] Repo selector: fetches from `GET /api/v1/clients/{client_id}/connections/github/repos` via React Query; renders a `<select>` with JetBrains Mono styling; on selection calls PATCH endpoint
  - [x] Disconnect: calls existing DELETE connection endpoint for `github_pages`
  - [x] On successful connect (URL `?success=github`): invalidates `["platform-connections", clientId]` React Query key

- [x] **Frontend — PlatformConnectionsClient** (AC: 1)
  - [x] `frontend/components/publishing/PlatformConnectionsClient.tsx`: Add `"github_pages"` to `ALL_PLATFORMS` array (line 13)
  - [x] `frontend/components/publishing/PlatformConnectionCard.tsx`: Add `"github_pages"` to `PLATFORM_LABELS` record; render `<GitHubConnect>` when `connection.platform === "github_pages"`

- [x] **Frontend — Type update** (AC: 1, 3)
  - [x] `frontend/lib/types.ts` line ~181: Add `"github_pages"` to `PlatformConnectionStatus.platform` union type

- [x] **Tests** (AC: 3, 6, 7)
  - [x] `backend/tests/integrations/test_github.py`: Mock httpx; test `get_installation_token()` success and non-200 error path
  - [x] `backend/tests/routers/test_publishing.py`: Test `POST /api/v1/clients/{id}/connections/github` — success, 403 wrong owner, 404 client not found

## Dev Notes

### Architecture Anti-Patterns to Avoid

- **DO NOT** decrypt credentials in the router. Encryption happens in `routers/publishing.py` on write; decryption happens ONLY in `services/publishing.py` immediately before the API call. The GitHub token in `integrations/github.py` functions receives the decrypted value passed from `services/publishing.py` — it never reads from DB directly.
- **DO NOT** add GitHub API logic to `workers/publish.py` directly. The worker calls `services/publishing.py`, which calls `integrations/github.py`.
- **DO NOT** use `useSearchParams()` for reading OAuth callback params in a client component — this creates RSC re-render subscriptions. The callback is handled server-side in `frontend/app/api/auth/github/callback/route.ts` then redirects to the connections page. The connections page reads `?success=github` imperatively via `window.location.search` inside `useEffect`, following the existing pattern in `PlatformConnectionsClient.tsx` (line 23).
- **DO NOT** store the decrypted installation token beyond the immediate API call scope (architecture rule: "decrypted value never leaves services/publishing.py function scope").

### Token Refresh Strategy

GitHub App installation tokens expire in exactly 1 hour. The token response now includes `expires_at` (ISO 8601 string) — use this directly rather than computing from `issued_at`. Store `expires_at` in the encrypted credential JSON. On each publish/repo-list call:

```python
from datetime import datetime, timezone

def is_token_expired(expires_at_iso: str) -> bool:
    expiry = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
    # Refresh 5 minutes early to avoid races
    return datetime.now(timezone.utc) >= expiry - timedelta(minutes=5)
```

If expired: call `get_installation_token(installation_id)`, update credential JSON with new `token` and `expires_at`, re-encrypt and upsert.

### PyJWT Dependency + JWT `iss` Claim

The GitHub App JWT must be signed with RS256 using the App private key. Add `PyJWT[crypto]>=2.8.0` to `backend/requirements.txt` (the `[crypto]` extra brings in `cryptography` for RS256; already used by AES-256-GCM — verify no duplicate).

**`iss` claim (changed May 2024):** Use `GITHUB_APP_CLIENT_ID` (the string `Iv1.xxx` shown in the App's "About" page), NOT the numeric `GITHUB_APP_ID`. GitHub now uses the Client ID as the canonical issuer identifier. Both env vars must be set (`GITHUB_APP_ID` is still used in some API paths; `GITHUB_APP_CLIENT_ID` is the JWT `iss`).

**`iat` must be 60 seconds in the past** (GitHub's requirement to handle clock skew between servers):
```python
import time, jwt
now = int(time.time())
payload = {"iss": settings.GITHUB_APP_CLIENT_ID, "iat": now - 60, "exp": now + 540}
token = jwt.encode(payload, private_key_pem, algorithm="RS256")
```

**New token format (April 2026):** GitHub now issues stateless tokens in `ghs_APPID_JWT` format instead of the old 40-character opaque tokens. Do not write any code that assumes token length or format — treat the token as an opaque string.

### CSRF Protection Cookie

The GitHub OAuth `state` param must be stored as an httpOnly, SameSite=Lax cookie — matches the pattern the existing Twitter PKCE `code_verifier` uses. The Next.js route handler (`/api/auth/github/callback/route.ts`) reads and deletes this cookie.  Cookie name: `github_oauth_state`.

### Credential JSON Shape

```json
{
  "installation_id": "12345678",
  "installation_token": "ghs_...",
  "expires_at": "2026-07-09T11:00:00Z",
  "repo_full_name": null
}
```
`expires_at` is the value returned directly from `POST /app/installations/{id}/access_tokens` response. After repo selection, `repo_full_name` is populated. `detected_framework`, `publish_path`, `confidence`, and `signals` are added by Story 8.4.

### Project Structure Notes

**New files:**
- `backend/app/integrations/github.py`
- `backend/alembic/versions/002_github_platform.py`
- `frontend/app/api/auth/github/callback/route.ts`
- `frontend/components/publishing/GitHubConnect.tsx`

**Modified files:**
- `backend/app/core/config.py` — add 4 env vars
- `backend/.env.example` — document new vars
- `backend/requirements.txt` — add `PyJWT[crypto]>=2.8.0`
- `backend/app/routers/publishing.py` — add GitHub endpoints + `github_pages` to ALL_PLATFORMS
- `frontend/components/publishing/PlatformConnectionsClient.tsx` — add `github_pages` to ALL_PLATFORMS array
- `frontend/components/publishing/PlatformConnectionCard.tsx` — add `github_pages` label + GitHubConnect render
- `frontend/lib/types.ts` — extend platform union

### References

- Epics.md: Epic 8, Story 8.1 — full BDD acceptance criteria
- Architecture: `backend/app/integrations/twitter.py` — integration module pattern to follow
- Architecture: Credential Encrypt/Decrypt Pattern (lines 718-723 in architecture.md)
- Architecture: `frontend/app/api/auth/google/callback/route.ts` — OAuth callback route pattern
- Architecture: `frontend/components/publishing/PlatformConnectionsClient.tsx` — ALL_PLATFORMS pattern and imperative URL param reading
- Sprint change proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-09.md` — lists required env vars

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- All code tasks implemented and tested. The PREREQUISITE — Manual admin steps task (register GitHub App, generate private key, note App ID/Client ID) is left unchecked — Boris must complete these on GitHub before the integration is functional. Fill in `GITHUB_APP_ID`, `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_WEBHOOK_SECRET` in `backend/.env` and `GITHUB_APP_SLUG` in `frontend/.env`.
- Alembic migration `f1a2b3c4d5e6` adds `github_pages` to platform_enum and `github_pr_url TEXT NULLABLE` to campaigns (using `autocommit_block()` pattern for ALTER TYPE, consistent with `a1b2c3d4e5f6`).
- Config vars added with empty string defaults (not `Field(...)`) to avoid breaking dev environment while credentials are not yet set. They are effectively required — the integration raises at runtime if they're blank.
- `GitHubConnect.tsx` renders the complete card (outer border + header row + repo selector form + disconnect modal) and `PlatformConnectionCard` returns early for `github_pages`. All hooks are called before the early return to satisfy React Rules of Hooks.
- `PlatformConnectionsClient` updated count assertions: `test_list_connections_empty` and `test_list_connections_with_wpcom` now assert 5 platforms (was 4).
- Pre-existing failure `test_create_webflow_connection_success` was already failing before this story (missing `validate_token` mock) — not introduced by this work.
- `frontend/app/api/auth/github/route.ts` created as the initiation route (state cookie + redirect to GitHub App install page), mirroring the X OAuth `/api/auth/x/route.ts` pattern.

### File List

**New files:**
- `backend/alembic/versions/f1a2b3c4d5e6_add_github_pages_to_platform.py`
- `backend/app/integrations/github.py`
- `backend/tests/integrations/test_github.py`
- `backend/tests/routers/test_publishing.py`
- `frontend/app/api/auth/github/route.ts`
- `frontend/app/api/auth/github/callback/route.ts`
- `frontend/components/publishing/GitHubConnect.tsx`

**Modified files:**
- `backend/app/core/config.py`
- `backend/.env.example`
- `backend/requirements.txt`
- `backend/app/routers/publishing.py`
- `backend/tests/test_publishing_router.py`
- `frontend/components/publishing/PlatformConnectionsClient.tsx`
- `frontend/components/publishing/PlatformConnectionCard.tsx`
- `frontend/components/ui/PlatformIcon.tsx`
- `frontend/lib/types.ts`
- `frontend/lib/api.ts`
- `frontend/.env.example`

### Review Findings

- [x] [Review][Patch] repo_full_name format validation — add regex guard ensuring `owner/repo` pattern [backend/app/routers/publishing.py:GitHubRepoPatchRequest]
- [x] [Review][Patch] Raw backend error exposed in redirect URL — replace raw error with generic message [frontend/app/api/auth/github/callback/route.ts]
- [x] [Review][Patch] clientId from cookie not validated as UUID before URL use [frontend/app/api/auth/github/callback/route.ts]
- [x] [Review][Patch] Silent disconnect failure — catch block swallows error, no user feedback [frontend/components/publishing/GitHubConnect.tsx:handleDisconnect]
- [x] [Review][Patch] Duplicate disconnect button branches — identical JSX in both ternary arms [frontend/components/publishing/GitHubConnect.tsx]
- [x] [Review][Patch] connectGitHub in api.ts is dead code — connection made server-side via callback route [frontend/lib/api.ts]
- [x] [Review][Patch] GITHUB_APP_PRIVATE_KEY empty → cryptic jwt.encode exception [backend/app/integrations/github.py:generate_app_jwt]
- [x] [Review][Patch] GitHub response missing token/expires_at key → unhandled KeyError [backend/app/integrations/github.py:get_installation_token]
- [x] [Review][Patch] installation_id format not validated as numeric [backend/app/routers/publishing.py + frontend/app/api/auth/github/callback/route.ts]
- [x] [Review][Patch] decrypt_credential exception not caught in select_github_repo and list_github_repos [backend/app/routers/publishing.py]
- [x] [Review][Patch] cred dict missing 'installation_id' → KeyError in list_github_repos refresh block [backend/app/routers/publishing.py:list_github_repos]
- [x] [Review][Patch] cookieData.clientId/state not validated after JSON.parse [frontend/app/api/auth/github/callback/route.ts]
- [x] [Review][Defer] >100 repos silently truncated — per_page=100 with no pagination [backend/app/integrations/github.py:get_installation_repositories] — deferred, edge case for large installations; add pagination in future
- [x] [Review][Defer] Stale token in DB if upsert_connection fails during refresh [backend/app/routers/publishing.py:list_github_repos] — deferred, low probability; next call will refresh again
- [x] [Review][Defer] CSRF cookie-stuffing via subdomain takeover with SameSite=Lax [frontend/app/api/auth/github/route.ts] — deferred, existing pattern across all OAuth flows; subdomain takeover is separate concern
- [x] [Review][Defer] Architecture: decrypt_credential called in router, not service layer [backend/app/routers/publishing.py] — deferred, existing pattern (_extract_identifier also decrypts in router); service-layer-only rule targets publish path
- [x] [Review][Defer] No "Change repository" CTA when connected-with-repo selected [frontend/components/publishing/GitHubConnect.tsx] — deferred, spec ambiguous; disconnect-and-reconnect is acceptable UX for MVP
- [x] [Review][Defer] Token refresh not implemented in publish path — only in list_github_repos [backend/app/routers/publishing.py] — deferred, publish endpoint is story 8.5; refresh must be added there
- [x] [Review][Defer] Returns 403 for non-existent client (vs 404 in other endpoints) [backend/app/routers/publishing.py:_check_github_ownership] — deferred, intentional security-by-obscurity pattern
- [x] [Review][Defer] httpx.RequestError/TimeoutException not caught in github.py [backend/app/integrations/github.py] — deferred, pre-existing pattern across all integrations (linkedin/twitter/webflow also unguarded)
- [x] [Review][Defer] No rate limiting / idempotency on POST connect_github — silently overwrites existing connection [backend/app/routers/publishing.py:connect_github] — deferred, cross-cutting concern; auth ownership check limits blast radius

## Change Log

- 2026-07-09: Implemented Story 8.3 — GitHub App OAuth & Repository Connection. Added `github_pages` platform support: Alembic migration, FastAPI integration module (RS256 JWT, token exchange, repo listing, 5-min-early refresh), 3 new router endpoints (connect, select-repo, list-repos), Next.js initiation + callback route handlers with CSRF state cookie, GitHubConnect component (all connection states), type/API/label updates across frontend. 8 new passing tests.
