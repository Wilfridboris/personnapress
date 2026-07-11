---
baseline_commit: 32d2c1e
---

# Story 11.6: GitHub Connection Reuse & Connections Nav Item

Status: done

## Story

As an authenticated PersonnaPress user with multiple clients,
I want connecting GitHub to a new client to reuse my existing GitHub App installation automatically,
so that I don't get sent to a useless GitHub settings page when connecting a second client.

## Acceptance Criteria

1. **Given** a user clicks "Connect GitHub" on any client's connections page, **When** the user already has a GitHub connection on another client, **Then** the app detects the existing installation, creates the connection directly, and shows "Connected" without redirecting to GitHub — no GitHub OAuth flow is triggered.

2. **Given** the existing GitHub installation is reused, **When** the connection is created, **Then** the user is immediately taken to repo selection (the same flow as after a fresh installation). The repo selection step is still per-client — each client picks its own repository.

3. **Given** a user has no prior GitHub connection on any client, **When** they click "Connect GitHub", **Then** the existing GitHub OAuth redirect flow runs as before (no change to the first-time connect experience).

4. **Given** the "Connect GitHub" button is clicked, **When** the reuse check is in progress, **Then** the button shows "Connecting…" and is disabled; a connection error is shown inline below the card if the reuse attempt fails.

5. **Given** the left sidebar navigation, **When** it renders for an authenticated user with an active client, **Then** a "Connections" item appears in the nav list (between "Clients" and "Calendar"), using the `Plug` Lucide icon, linking to `/clients/{activeClientId}/connections`.

6. **Given** the left sidebar navigation, **When** no active client is set (e.g. first login before client creation), **Then** the "Connections" nav item is hidden rather than linking to a broken URL.

7. **Given** the GitHub publish endpoint receives `author` and `categories` fields in the request body, **When** the background job is dispatched, **Then** both values are passed through to `publish_github_job` and forwarded to `generate_github_post_file` — completing the router-layer wiring that Story 11.5 added at the service layer.

## Tasks / Subtasks

### Task 1: Backend — user-level GitHub installation lookup endpoint (AC: 1, 2, 3)

- [x] 1.1 In `backend/app/routers/publishing.py`, add a new route **before** the `connect_github` POST handler:
  ```python
  @router.get("/connections/github/installation-id")
  async def get_existing_github_installation_id(
      current_user: dict = Depends(get_current_user),
      db: AsyncSession = Depends(get_session),
  ) -> dict:
  ```
  Query `PlatformConnection` joined to `Client` where `Client.user_id == user_id` and `platform == "github_pages"` (LIMIT 1). Decrypt the credential JSON and return `{"installation_id": cred.get("installation_id")}`. Return `{"installation_id": None}` on any exception or if no row found.

  Required imports to add at the top of `publishing.py`:
  ```python
  from app.db.repositories.models import Client, PlatformConnection
  ```

- [x] 1.2 Fix `GitHubPublishRequest` in `publishing.py` to pass `author` and `categories` through to the job worker (missed in Story 11.5 router layer):
  ```python
  class GitHubPublishRequest(BaseModel):
      mode: str
      author: str | None = None
      categories: list[str] | None = None
  ```
  And update the background task dispatch call:
  ```python
  background_tasks.add_task(publish_github_job, job.id, campaign_id, body.mode, body.author, body.categories)
  ```
  Note: `publish_github_job` in `backend/app/workers/publish.py` already accepts `author` and `categories` parameters — only the router layer is missing this wiring.

### Task 2: Frontend — GitHub connection reuse logic (AC: 1, 2, 3, 4)

- [x] 2.1 In `frontend/lib/api.ts`, add two methods to `publishingApi`:
  ```typescript
  getExistingGithubInstallationId: () =>
    apiFetch<{ installation_id: string | null }>("/connections/github/installation-id"),
  connectGithubDirect: (clientId: string, installationId: string) =>
    apiFetch<{ platform: string; connected: boolean }>(
      `/clients/${clientId}/connections/github`,
      { method: "POST", body: JSON.stringify({ installation_id: installationId }) }
    ),
  ```

- [x] 2.2 In `frontend/components/publishing/GitHubConnect.tsx`, replace the static `<a href="/api/auth/github?...">` anchor with a `<button>` that calls an async `handleConnect()` function:
  - Add state: `const [connectError, setConnectError] = useState<string | null>(null);` and `const [connecting, setConnecting] = useState(false);`
  - `handleConnect` checks `getExistingGithubInstallationId()`. If `installation_id` is truthy, calls `connectGithubDirect(clientId, installation_id)` then invalidates `platform-connections` query. Otherwise falls through to `window.location.href = \`/api/auth/github?client_id=${clientId}\``.
  - Button renders: `{connecting ? "Connecting…" : "Connect GitHub"}` with `disabled={connecting}`
  - Show `connectError` inline below the card as `<p className="text-xs text-[#C0392B] mt-2" role="alert">{connectError}</p>` when truthy.

### Task 3: Frontend — Connections nav item in sidebar (AC: 5, 6)

> **Use the /web-uiux-architect skill when designing this change.**

- [x] 3.1 In `frontend/components/layout/sidebar.tsx`:
  - Add `import { useClientStore } from "@/lib/stores/useClientStore";`
  - Add `import { Plug } from "lucide-react";` (verify `Plug` exists in the installed lucide-react version; if not, use `Cable`)
  - Read `activeClientId` from the store: `const { activeClientId } = useClientStore();`
  - Render the connections nav item conditionally between Clients and Calendar:
    ```tsx
    {activeClientId && (
      <NavItem
        href={`/clients/${activeClientId}/connections`}
        label="Connections"
        icon={Plug}
      />
    )}
    ```
  - The item is hidden (`!activeClientId`) rather than disabled to avoid a broken link.

- [x] 3.2 The mobile `MobileDrawer` component (if it uses the same `NAV_ITEMS` array) needs the same dynamic connections item. Check if `MobileDrawer` renders its own nav and apply the same `activeClientId`-conditional pattern.

### Task 4: Backend tests (AC: 1, 2, 3)

- [x] 4.1 In `backend/tests/routers/test_publishing.py`, add tests for `GET /api/v1/connections/github/installation-id`:
  - Returns `{"installation_id": null}` when the user has no GitHub connections on any client.
  - Returns `{"installation_id": "12345"}` when one of the user's clients has a GitHub connection.
  - Returns `{"installation_id": null}` (no crash) when the credential row is corrupt/un-decryptable.
  - Returns 401 when called unauthenticated.

## Dev Notes

### Unstaged baseline changes

The following changes are **already in the working tree** (unstaged) at the time this story was written. Treat them as the authoritative starting point for Tasks 1 and 2 — do NOT rewrite them from scratch, only verify and extend if needed:

- `backend/app/routers/publishing.py`: `GET /connections/github/installation-id` endpoint + `Client`/`PlatformConnection` imports + `author`/`categories` on `GitHubPublishRequest` + pass-through to `publish_github_job`.
- `frontend/components/publishing/GitHubConnect.tsx`: `handleConnect()`, `connectError` state, button swap.
- `frontend/lib/api.ts`: `getExistingGithubInstallationId` and `connectGithubDirect` additions.

Do a `git diff` before starting and verify these are all present. If they are, Tasks 1 and 2 are effectively done — write the tests (Task 4) and implement the nav item (Task 3).

### Key files

| File | Change type | Purpose |
|------|-------------|---------|
| `backend/app/routers/publishing.py` | UPDATE | Add installation lookup endpoint + fix author/categories wiring |
| `backend/tests/routers/test_publishing.py` | UPDATE | Add tests for new endpoint |
| `frontend/lib/api.ts` | UPDATE | Add `getExistingGithubInstallationId`, `connectGithubDirect` |
| `frontend/components/publishing/GitHubConnect.tsx` | UPDATE | Replace static anchor with `handleConnect()` |
| `frontend/components/layout/sidebar.tsx` | UPDATE | Add dynamic Connections nav item |
| `frontend/components/layout/MobileDrawer.tsx` (if exists) | UPDATE | Same dynamic nav item for mobile |

### Architecture constraints

- Server components should only do session/auth checks. All data fetching in client components via TanStack Query (see `project-context.md`).
- `Sidebar` is already `"use client"` — `useClientStore` can be called directly.
- No emojis anywhere. Icons must come from `lucide-react` only (check installed version for `Plug`; fallback is `Cable`).
- The `NavItem` component already handles `href`, `label`, `icon` props — no changes needed to that component.

### Lucide icon check

Before using `Plug` in the sidebar, verify it exists:
```bash
grep -r "\"plug\"" node_modules/lucide-react/dist/lucide-react.js | head -1
```
If absent, use `Cable` instead (both represent "connection").

### Why the author/categories router wiring was missing

Story 11.5 added `author`/`categories` to `generate_github_post_file` (service layer) and `publish_github_job` (worker layer). The router (`GitHubPublishRequest` Pydantic model and `background_tasks.add_task` call) was not updated in that commit. The `author` field already works in `approval-panel.tsx` at the frontend but the values were silently dropped at the router boundary. Task 1.2 closes that gap.

## Dev Agent Record

### Implementation Plan

- Tasks 1 and 2 were pre-implemented in the working tree (unstaged). Verified via `git diff` — all changes confirmed present.
- Added missing `from sqlalchemy import select` import to `publishing.py` (required by the new `get_existing_github_installation_id` endpoint).
- Task 3: Both `Sidebar` and `MobileDrawer` use `NAV_ITEMS.map()`. Split the render into `slice(0,2)` + conditional Connections item + `slice(2)` to inject between Clients and Calendar. `Plug` icon confirmed present in installed lucide-react.
- Task 4: Added 4 tests for the new endpoint. Fixed pre-existing regression in `_make_campaign` (`github_pr_url = None` needed after Story 11.5 added PR guard in the publish route).

### Completion Notes

All 7 ACs satisfied. 10 backend tests pass (4 new, 6 pre-existing). Frontend changes are compile-time safe (TypeScript types respected). 48 other test failures confirmed pre-existing on baseline — no regressions introduced.

## File List

- `backend/app/routers/publishing.py` — added `select` import; GET endpoint + author/categories wiring were pre-staged
- `backend/tests/routers/test_publishing.py` — added 4 tests for installation-id endpoint; fixed `_make_campaign` mock
- `frontend/lib/api.ts` — `getExistingGithubInstallationId` + `connectGithubDirect` (pre-staged)
- `frontend/components/publishing/GitHubConnect.tsx` — `handleConnect()` + button swap (pre-staged)
- `frontend/components/layout/sidebar.tsx` — dynamic Connections nav item
- `frontend/components/layout/MobileDrawer.tsx` — dynamic Connections nav item (mobile)

## Review Findings

- [x] [Review][Patch] invalidateQueries inside same try block as connectGithubDirect — cache error shows false "GitHub connection failed" [frontend/components/publishing/GitHubConnect.tsx]
- [x] [Review][Patch] Bare except in credential decrypt swallows all errors with no log [backend/app/routers/publishing.py:423]
- [x] [Review][Patch] author empty-string passes None check; normalize with field_validator [backend/app/routers/publishing.py:GitHubPublishRequest]
- [x] [Review][Patch] NAV_ITEMS.slice(0,2) hardcodes Calendar position; use findIndex [frontend/components/layout/sidebar.tsx, MobileDrawer.tsx]

## Change Log

- 2026-07-11: Implemented Story 11.6 — GitHub connection reuse, Connections nav item, author/categories router wiring, backend tests for installation-id endpoint
- 2026-07-11: Code review complete — 4 patches applied (invalidateQueries try-block separation, bare-except logging, author empty-string normalization, NAV_ITEMS findIndex); marked done
