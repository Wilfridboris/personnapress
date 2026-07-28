---
baseline_commit: 28d8759
---

# Story 5.7: LinkedIn Company Page Posting Target

Status: ready-for-dev

## Story

As an authenticated user who has connected LinkedIn,
I want to choose whether PersonnaPress posts to my personal LinkedIn profile or to a company page I admin,
So that I can publish campaigns on behalf of a business brand rather than my personal account.

## Background and Context

The current LinkedIn integration (Story 5.2 / 5.3) posts exclusively to the connected user's personal
profile using `urn:li:person:{sub}` as the author URN with the `w_member_social` scope.

LinkedIn's company page posting requires two additional OAuth scopes — `r_organization_admin`
(to list pages the user admins) and `w_organization_social` (to post as an org) — both of which are
gated behind LinkedIn's Marketing Developer Platform (MDP) product approval. This approval process
involves a formal review and is NOT instant.

**Two-layer architecture:**
- **Layer 1 (personal, live today):** No change. Personal profile posting continues working as-is.
- **Layer 2 (company pages, gated):** Build the full technical stack now but gate it behind the
  `LINKEDIN_ORG_POSTING_ENABLED` / `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED` feature flags.
  When the flags are `false`, the UI shows the Company Page option locked with a clear explanation.
  When LinkedIn grants MDP approval, flip both env vars to `true` and the feature goes live
  with zero code changes.

## Acceptance Criteria

### AC 1: Feature flag controls UI availability

**Given** `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED` is `false` (default),
**When** a user views a connected LinkedIn card,
**Then** the "Company Page" option in the target picker is rendered but visually disabled (grayed out,
`cursor-not-allowed`) with a `Lock` icon and tooltip text:
"Company page posting requires LinkedIn Marketing Developer Platform approval. Currently only personal profile posting is available."
No org-listing API calls are made.

**Given** `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED` is `true`,
**When** a user views the connected LinkedIn card,
**Then** the Company Page option is fully interactive and selectable.

### AC 2: Connected card shows posting target

**Given** a LinkedIn connection exists with target `"personal"` (or no `target` key, i.e., legacy connections),
**When** the Platform Connections page renders the LinkedIn card,
**Then** a "Posting as: Personal Account" line appears directly below the account identifier (display name),
alongside a "Change" text link styled identically to the existing "Disconnect" link
(`text-xs text-[#555555] hover:text-[#111111] underline underline-offset-2 transition-colors`).

**Given** a LinkedIn connection exists with target `"organization"`,
**When** the card renders,
**Then** "Posting as: {org_name}" appears in place of "Personal Account" with the same "Change" link.

### AC 3: Target picker — gated state

**Given** the user clicks "Change" on a connected LinkedIn card while `LINKEDIN_ORG_POSTING_ENABLED` is `false`,
**When** the target picker opens,
**Then** an inline panel expands below the card header (separated by `border-t border-[#E5E5E5] mt-4 pt-4`),
showing:

- Section label: "Posting destination" (`text-xs font-medium text-[#111111]`)
- Option 1: `User` icon + "Personal Account" sub-label "Your LinkedIn profile" — selectable, selected by default
- Option 2: `Building2` icon + "Company Page" sub-label "Requires LinkedIn Marketing Developer Platform approval"
  — visually disabled (`opacity-50 cursor-not-allowed`), `Lock` icon (size-3.5) at the right edge,
  tooltip on hover (via `title` attribute): "Company page posting requires LinkedIn Marketing Developer Platform approval. Currently only personal profile posting is available."
- A "Cancel" text link at the top-right of the section

Since only one option is selectable in gated mode, clicking "Personal Account" (or "Cancel") closes
the picker without an API call. No "Save" button is shown in this state.

### AC 4: Target picker — enabled state

**Given** `LINKEDIN_ORG_POSTING_ENABLED` is `true` and the user clicks "Change",
**When** the target picker opens,
**Then** both options are interactive. Selecting "Company Page" triggers
`GET /api/v1/clients/{client_id}/connections/linkedin/organizations` and shows a list below the
Company Page option row. Each org row displays: `Building2` icon (size-4) + org name
(`text-sm font-medium text-[#111111]`) + follower count (`text-xs text-[#555555]`, formatted as
`{n.toLocaleString()} followers`). The selected org has `ring-1 ring-[#111111]` highlight.

A "Save" primary button and "Cancel" secondary button appear at the bottom of the section.
Clicking "Save" calls `PATCH /api/v1/clients/{client_id}/connections/linkedin/target` and closes
the picker. The card updates to "Posting as: {org_name}".

### AC 5: Org list loading and empty states

**Given** the org fetch is in flight (feature enabled, Company Page selected),
**When** the list area renders,
**Then** a single-line spinner + "Loading your pages..." text (`text-xs text-[#555555]`) is shown.

**Given** the org fetch returns an empty list,
**When** the list area renders,
**Then** text is shown: "No pages found. You must be an admin of a LinkedIn Page to post to it."

**Given** the org fetch returns a permission error (403 / 401 — token predates scope upgrade),
**When** the list area renders,
**Then** text is shown: "Please reconnect LinkedIn to enable company page access." with a
"Reconnect" link that initiates a fresh LinkedIn OAuth flow via `/api/auth/linkedin?client_id={id}`.

### AC 6: OAuth scope upgrade when feature is enabled

**Given** `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED` is `true`,
**When** the user clicks "Connect LinkedIn" (initiating fresh OAuth),
**Then** `frontend/app/api/auth/linkedin/route.ts` includes
`r_organization_admin w_organization_social` appended to the scope string:
`openid profile w_member_social r_organization_admin w_organization_social`.

**Given** `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED` is `false` (default),
**When** OAuth is initiated,
**Then** scope remains `openid profile w_member_social` — no change from today.

### AC 7: Publishing uses the stored target

**Given** a campaign is published to LinkedIn and the connection has `target = "organization"` with `org_id` set,
**When** `linkedin_integration.create_ugc_post()` is called,
**Then** the `author` field in the UGC Posts request body is `urn:li:organization:{org_id}` instead of
`urn:li:person:{sub}`. The `GET /v2/userinfo` call to fetch the person sub is skipped when posting as an org.

**Given** the connection has `target = "personal"` (or no `target` key — legacy),
**When** `create_ugc_post()` is called,
**Then** behavior is identical to today: fetch sub from `/v2/userinfo` and use `urn:li:person:{sub}`.

### AC 8: No DB migration — backward compatible JSON extension

**Given** the existing `encrypted_credentials` JSON blob for a LinkedIn connection is `{"access_token": "...", "name": "..."}`,
**When** the PATCH target endpoint is called with `target = "organization"`,
**Then** the blob is updated in place: `{"access_token": "...", "name": "...", "target": "organization", "org_id": "123456", "org_name": "Acme Corp"}`.

**Given** a legacy connection with no `target` key,
**When** the publishing service decrypts and reads the blob,
**Then** the absence of `target` is treated as `"personal"`. No migration is required.

### AC 9: Backend feature flag enforcement

**Given** `LINKEDIN_ORG_POSTING_ENABLED` is `false` on the backend,
**When** `GET /api/v1/clients/{id}/connections/linkedin/organizations` is called,
**Then** the endpoint returns HTTP 403 with `{"detail": "LinkedIn company page posting is not yet enabled."}`.

**Given** `LINKEDIN_ORG_POSTING_ENABLED` is `true`,
**When** the endpoint is called with a valid, authenticated session,
**Then** the endpoint fetches org pages from `GET https://api.linkedin.com/v2/organizationAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED` and returns `{"organizations": [{"id": "...", "name": "...", "follower_count": 1240}]}`.

### AC 10: New env vars documented

**Given** the feature ships,
**Then** `backend/.env.example` gains `LINKEDIN_ORG_POSTING_ENABLED=false` with comment:
"Set to true after LinkedIn Marketing Developer Platform approval is granted."
And `frontend/.env.example` gains `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED=false` with the same comment.

## Tasks / Subtasks

- [ ] Task 1: Backend — feature flag + new endpoints (AC: 9, 10)
  - [ ] 1.1 Add `LINKEDIN_ORG_POSTING_ENABLED: bool = False` to `backend/app/core/config.py` Settings class
  - [ ] 1.2 Add `LINKEDIN_ORG_POSTING_ENABLED=false` to `backend/.env.example` with comment
  - [ ] 1.3 Add `GET /clients/{client_id}/connections/linkedin/organizations` to `backend/app/routers/publishing.py`:
    - Guard: return 403 if `not settings.LINKEDIN_ORG_POSTING_ENABLED`
    - Decrypt LinkedIn creds, extract `access_token`
    - Call `GET https://api.linkedin.com/v2/organizationAcls?q=roleAssignee&role=ADMINISTRATOR&state=APPROVED` with `LinkedIn-Version: 202602` header
    - For each org ACL element, fetch org name via `GET /v2/organizations/{orgId}?projection=(localizedName,followersCount)` (or use `organizationAcls` projection to avoid N+1 — see LinkedIn API note below)
    - Return `{"organizations": [{"id": str, "name": str, "follower_count": int}]}`
    - On 401/403 from LinkedIn, return 403 with detail "token_insufficient_scope" so frontend can show reconnect prompt
  - [ ] 1.4 Add `PATCH /clients/{client_id}/connections/linkedin/target` to `backend/app/routers/publishing.py`:
    - Request body: `LinkedInTargetPatchRequest(target: Literal["personal", "organization"], org_id: str | None = None, org_name: str | None = None)`
    - Validate: if `target == "organization"`, both `org_id` and `org_name` must be non-empty
    - Decrypt existing `platform_connections` row for linkedin; parse JSON; set/overwrite `target`, `org_id`, `org_name` keys; re-encrypt; upsert
    - Return `{"target": ..., "org_id": ..., "org_name": ...}` (200)
  - [ ] 1.5 Add `LINKEDIN_ORG_POSTING_ENABLED=false` to `backend/.env.example`

- [ ] Task 2: Backend — publishing dispatch update (AC: 7, 8)
  - [ ] 2.1 Update `backend/app/integrations/linkedin.py`:
    - Refactor `create_ugc_post(access_token, blog_html, linkedin_text)` to accept optional `org_id: str | None = None`
    - When `org_id` is provided: skip `GET /v2/userinfo` call; set `"author": f"urn:li:organization:{org_id}"`
    - When `org_id` is None: retain existing behavior (fetch sub from `/v2/userinfo`, use `urn:li:person:{sub}`)
  - [ ] 2.2 Update `backend/app/services/publishing.py` in the `elif platform == "linkedin":` branch:
    - Extract `target = creds.get("target", "personal")` and `org_id = creds.get("org_id")` from the decrypted blob
    - Pass `org_id=org_id if target == "organization" else None` to `create_ugc_post()`
  - [ ] 2.3 Update `backend/app/services/publishing.py` retry path (lines ~480-490) with same extraction logic

- [ ] Task 3: Frontend — env var + OAuth scope upgrade (AC: 6, 10)
  - [ ] 3.1 Add `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED=false` to `frontend/.env.example` with comment
  - [ ] 3.2 Update `frontend/app/api/auth/linkedin/route.ts`:
    - Read `process.env.NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED`
    - When truthy, append `r_organization_admin w_organization_social` to the scope string
    - When falsy, scope remains `openid profile w_member_social` (no change)

- [ ] Task 4: Frontend — types and API client (AC: 2, 4, 5)
  - [ ] 4.1 Update `frontend/lib/types.ts`:
    - Add optional fields to `PlatformConnectionStatus`:
      ```typescript
      linkedin_target?: "personal" | "organization";
      linkedin_org_name?: string;
      ```
  - [ ] 4.2 Update `frontend/lib/api.ts` in `publishingApi`:
    - Add `getLinkedInOrganizations: (clientId: string) => apiFetch<{ organizations: LinkedInOrg[] }>(...)`
    - Add `updateLinkedInTarget: (clientId: string, payload: LinkedInTargetPayload) => apiFetch<void>(...)`
    - Export new types `LinkedInOrg` (`{ id: string; name: string; follower_count: number }`) and
      `LinkedInTargetPayload` (`{ target: "personal" | "organization"; org_id?: string; org_name?: string }`)
  - [ ] 4.3 Update `GET /api/v1/clients/{client_id}/connections` backend response to include `linkedin_target`
        and `linkedin_org_name` fields derived from the decrypted blob (read-only, safe to surface)

- [ ] Task 5: Frontend — PlatformConnectionCard LinkedIn target picker (AC: 1, 2, 3, 4, 5)
  - [ ] 5.1 In `PlatformConnectionCard.tsx`, add LinkedIn-specific state:
    ```typescript
    const [showTargetPicker, setShowTargetPicker] = useState(false);
    const [pickerTarget, setPickerTarget] = useState<"personal" | "organization">("personal");
    const [orgs, setOrgs] = useState<LinkedInOrg[] | null>(null);
    const [orgsLoading, setOrgsLoading] = useState(false);
    const [orgsError, setOrgsError] = useState<string | null>(null);
    const [selectedOrgId, setSelectedOrgId] = useState<string>("");
    const [savingTarget, setSavingTarget] = useState(false);
    ```
  - [ ] 5.2 When `connection.platform === "linkedin"` and `connection.connected`, render "Posting as" row
        below `account_identifier`:
        ```tsx
        <span className="block text-xs text-[#555555] mt-1">
          Posting as: {connection.linkedin_target === "organization" && connection.linkedin_org_name
            ? connection.linkedin_org_name
            : "Personal Account"}
          {" "}
          <button onClick={() => setShowTargetPicker(true)} className="underline underline-offset-2 hover:text-[#111111] transition-colors">
            Change
          </button>
        </span>
        ```
  - [ ] 5.3 Render `LinkedInTargetPicker` inline section (below the main flex row) when
        `showTargetPicker && connection.platform === "linkedin"`:
    - `border-t border-[#E5E5E5] mt-4 pt-4 space-y-3`
    - Header: `<p className="text-xs font-medium text-[#111111]">Posting destination</p>` + Cancel link top-right
    - Personal Account option button:
      ```
      w-full text-left px-3 py-2.5 border transition-colors
      selected: border-[#111111] ring-1 ring-[#111111]
      unselected: border-[#E5E5E5] hover:border-[#111111]
      focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2
      ```
      Contains: `User` icon (size-4 shrink-0) + div with "Personal Account" (`text-sm font-medium text-[#111111]`) and "Your LinkedIn profile" (`text-xs text-[#555555]`)
    - Company Page option button (same structure, `Building2` icon + `Lock` icon at far right):
      - When `NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED` is falsy: add `opacity-50 cursor-not-allowed pointer-events-none` and `title` tooltip; show `Lock` icon
      - When truthy: fully interactive; clicking triggers org fetch if `orgs === null`
    - Org list (only visible when `pickerTarget === "organization"` and feature enabled):
      - Loading: `Loader2 animate-spin` + "Loading your pages..."
      - Error with "token_insufficient_scope": reconnect link
      - Empty: "No pages found. You must be an admin of a LinkedIn Page to post to it."
      - Org rows: `button w-full text-left px-3 py-2 border border-[#E5E5E5] hover:border-[#111111] transition-colors` with `Building2` + name + follower count; selected: `border-[#111111] ring-1 ring-[#111111]`
    - Save + Cancel buttons (only shown when feature enabled and `pickerTarget === "organization"` or changed):
      ```
      <Button variant="primary" onClick={handleSaveTarget} disabled={savingTarget} className="text-xs px-4 py-2">
        {savingTarget ? "Saving..." : "Save"}
      </Button>
      <Button variant="secondary" onClick={handleCancelPicker} className="text-xs px-4 py-2">Cancel</Button>
      ```
  - [ ] 5.4 Implement `handleSaveTarget`:
    - Calls `publishingApi.updateLinkedInTarget(clientId, { target: pickerTarget, org_id: selectedOrgId, org_name: selectedOrgName })`
    - On success: `queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] })` + close picker
    - On error: set `error` state and show inline `role="alert"` text
  - [ ] 5.5 When `pickerTarget === "organization"` and org list fetch is triggered, call
        `publishingApi.getLinkedInOrganizations(clientId)` and populate `orgs` state

- [ ] Task 6: Backend — connections list response enrichment (AC: 2, 4)
  - [ ] 6.1 In `GET /clients/{client_id}/connections`, for any `platform='linkedin'` row:
    - Decrypt creds, extract `target` and `org_name` from the JSON blob safely (try/except, default to personal)
    - Include `linkedin_target` and `linkedin_org_name` in the response item (alongside existing `platform`, `connected`, `account_identifier`)
    - Never include `access_token` or `org_id` in the response — org_id stays server-side only

- [ ] Task 7: Tests (AC: 7, 8, 9)
  - [ ] 7.1 Unit test `linkedin.py::create_ugc_post` with `org_id=None` — verifies `/v2/userinfo` is called, `urn:li:person:X` used
  - [ ] 7.2 Unit test `linkedin.py::create_ugc_post` with `org_id="123456"` — verifies `/v2/userinfo` NOT called, `urn:li:organization:123456` used
  - [ ] 7.3 Test `dispatch_publish` with a cred blob containing `target="organization"` and `org_id="123456"` — verifies `create_ugc_post` called with correct `org_id`
  - [ ] 7.4 Test `dispatch_publish` with legacy blob (no `target` key) — verifies personal-profile path taken
  - [ ] 7.5 Test `PATCH /connections/linkedin/target` — valid org payload stores encrypted blob correctly
  - [ ] 7.6 Test `PATCH /connections/linkedin/target` with `target="organization"` and missing `org_id` — returns 422
  - [ ] 7.7 Test `GET /connections/linkedin/organizations` returns 403 when `LINKEDIN_ORG_POSTING_ENABLED=false`

## Dev Notes

### LinkedIn API: Organization Listing

**Endpoint:**
```
GET https://api.linkedin.com/v2/organizationAcls
    ?q=roleAssignee
    &role=ADMINISTRATOR
    &state=APPROVED
    &projection=(elements*(organization~(localizedName,followersCount),organizationRole,state),paging)
```
Headers: `Authorization: Bearer {access_token}`, `LinkedIn-Version: 202602`

The projection `organization~(localizedName,followersCount)` inlines the org data so you avoid a second
N+1 call per org. The `follower_count` comes from the `followersCount` field. The `id` is extracted from
the `organization` URN: `urn:li:organization:{id}` — parse the trailing number.

If LinkedIn returns `403` or `401`, it usually means the token was issued without `r_organization_admin`.
Return this to the frontend as `detail: "token_insufficient_scope"` so the UI can show the reconnect prompt.

**UGC Posts with org author:**
```json
{
  "author": "urn:li:organization:123456",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": { "text": "..." },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" }
}
```
Note: When author is an organization, the `visibility` field should use `"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"` — same as personal. LinkedIn also accepts `"com.linkedin.ugc.CompanyVisibility"` for org posts but `PUBLIC` works for both.

### Credential JSON Schema (extended)

```json
{
  "access_token": "AQX...",
  "name": "Boris Kwayep",
  "target": "organization",
  "org_id": "123456",
  "org_name": "Acme Corp"
}
```

Old connections: `{"access_token": "...", "name": "..."}` — treated as personal everywhere. No migration script needed.

### File Locations

| File | Change type |
|---|---|
| `backend/app/core/config.py` | UPDATE — add `LINKEDIN_ORG_POSTING_ENABLED: bool = False` |
| `backend/app/integrations/linkedin.py` | UPDATE — `create_ugc_post` org_id param |
| `backend/app/services/publishing.py` | UPDATE — extract target+org_id from creds, pass to integration |
| `backend/app/routers/publishing.py` | UPDATE — 2 new endpoints + connections list enrichment |
| `backend/.env.example` | UPDATE — add flag |
| `frontend/app/api/auth/linkedin/route.ts` | UPDATE — conditional scope upgrade |
| `frontend/lib/types.ts` | UPDATE — `PlatformConnectionStatus` new fields |
| `frontend/lib/api.ts` | UPDATE — new API functions |
| `frontend/components/publishing/PlatformConnectionCard.tsx` | UPDATE — LinkedIn target picker |
| `frontend/.env.example` | UPDATE — add flag |

### Design Patterns to Follow

**Inline expansion:** Mirror the WordPress host-type picker pattern in `PlatformConnectionCard.tsx`
(lines 191-227). Use `border-t border-[#E5E5E5] mt-4 pt-4 space-y-4` for the separator.

**Option buttons:** Identical pattern to the WP self-hosted / WordPress.com choice buttons:
```
w-full text-left px-4 py-3 border border-[#E5E5E5] hover:border-[#111111]
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2
transition-colors duration-150
```
Selected state: add `border-[#111111] ring-1 ring-[#111111]`.

**No modals.** The whole picker lives inline in the card — consistent with the established card pattern.

**No emojis anywhere.** Icons only from Lucide React: `User`, `Building2`, `Lock`, `Loader2`, `ExternalLink`.

**Feature flag in frontend:** Read from `process.env.NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED`. This is a
`NEXT_PUBLIC_` var so it is baked in at build time. Treat any truthy string as enabled:
```typescript
const orgPostingEnabled = process.env.NEXT_PUBLIC_LINKEDIN_ORG_POSTING_ENABLED === "true";
```

**"Posting as" on same line as account_identifier:** The existing connected state renders:
```
<span className="text-xs font-medium uppercase tracking-[0.06em] text-[#2E4F2E]">Connected</span>
<span className="block text-xs text-[#555555] mt-0.5">{account_identifier}</span>
```
Add a third `<span>` below the second one — same container, `block` span. Keep this LinkedIn-only
(check `connection.platform === "linkedin" && connection.connected`).

### Onboarding Flow

The onboarding step 4 connects LinkedIn via the same OAuth path (`/api/auth/linkedin?return_to=onboarding`).
After connecting, the user lands on `/onboarding?success=linkedin`. The target defaults to "personal"
silently — no target picker is shown in the onboarding flow. Company page selection is a post-onboarding
action via the Connections page only.

### Edge Cases

1. **Token predates scope upgrade (most common after flag flip):** Org fetch returns 403/401 from LinkedIn.
   Show reconnect prompt (AC 5). User clicks reconnect → full OAuth flow with new scopes. After
   reconnect, org posting available.

2. **User switches from org back to personal:** PATCH with `target="personal"`, `org_id=null`,
   `org_name=null`. Backend sets `target="personal"` and removes `org_id`/`org_name` from blob.

3. **Org name change after selection:** Org name is stored at connection time. If the company renames
   itself, the stored name becomes stale. v1: acceptable; user can re-select the org to refresh the name.

4. **Publish when org_id stored but feature later disabled:** The backend publishing path reads `org_id`
   from creds directly — it does NOT check `LINKEDIN_ORG_POSTING_ENABLED` at publish time. If a user
   had selected an org before the flag was turned off (unusual scenario), the publish still uses the
   stored org_id. This is acceptable; the flag only gates UI + the org-listing API.

5. **Disconnect clears everything:** Disconnecting LinkedIn deletes the entire `platform_connections` row
   including the org target. Re-connecting starts fresh as personal. No change needed to disconnect flow.

## Project Context Reference

- No em-dashes in any user-facing copy (use ":" or "-" instead)
- Icons from Lucide React only — `User`, `Building2`, `Lock`, `Loader2`, `ChevronDown`, `ExternalLink`
- Paper Style design: `bg-white`, `border-[#111111]` / `border-[#E5E5E5]`, `rounded-none`, `text-[#111111]`, `text-[#555555]`, `text-[#2E4F2E]` for connected status
- No emojis anywhere
- Brand name: PersonnaPress (double-n)
- All data fetching in client components via TanStack Query (not in server components) to avoid RSC loop in Turbopack dev mode
- `queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] })` after any mutation to refresh the card
- New Alembic migrations are NOT needed here (no schema change — JSON blob extension only)
- For backend endpoints, follow the auth guard pattern used in existing `publishing.py` routes: `user: User = Depends(get_current_user)`, client ownership check via `get_client_or_404(db, client_id, user.id)`

## Story Completion Status

- [ ] All acceptance criteria implemented
- [ ] All tasks completed
- [ ] Tests passing
- [ ] No em-dashes in any added copy
- [ ] `LINKEDIN_ORG_POSTING_ENABLED=false` is the default (feature is off until approval)
- [ ] Legacy connections (no `target` key) continue working as personal
- [ ] Code review complete
