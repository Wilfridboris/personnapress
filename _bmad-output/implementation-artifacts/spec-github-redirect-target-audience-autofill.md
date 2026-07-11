---
title: 'Fix GitHub redirect + target audience autofill'
type: 'bugfix'
created: '2026-07-11'
status: 'done'
baseline_commit: '32d2c1e2236e7179077f1ec8016400e6c7e15192'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Two bugs block the platform connections + campaign creation flows. (1) Clicking "Connect GitHub" drops the user on `github.com/settings/installations/{id}` because the GitHub App has no Setup URL configured — the redirect back to our callback never fires. (2) The "Target audience" field on New Campaign stays blank after voice ingestion because the backend's `/clients` list endpoint strips `brand_voice_profile` from its response, so the client store never carries the data the autofill reads.

**Approach:** Bug A is a GitHub App settings change — configure the "Setup URL" (Post Installation URL) in the GitHub App settings on github.com to `{APP_URL}/api/auth/github/callback`, and update the env comment to call this out clearly. Bug B is a two-line backend fix — add `brand_voice_profile` to the `ClientListItem` Pydantic schema and pass the field when building list responses.

## Boundaries & Constraints

**Always:**
- Backend change must not alter the `ClientListItem` JSON shape for fields that already exist (status, name, id, etc.)
- `brand_voice_profile` can be null (not yet extracted) — the serialisation must allow that
- Do not fetch a separate client detail endpoint from the New Campaign page; fix it in the list response

**Ask First:** Any change that requires touching the Vercel env dashboard or GitHub App settings beyond the Setup URL field

**Never:**
- Do not add `brand_voice_profile` to the response only for the active client — all `ClientListItem` entries must carry it for consistency with client-switching logic
- Do not remove `brand_voice_profile_status` — it is used by the sidebar status indicators

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Client has BVP with target_audience | GET /clients returns list; active client has `brand_voice_profile.target_audience = "indie founders"` | New Campaign page pre-fills Target audience field with "indie founders" | N/A |
| Client BVP has null target_audience | `brand_voice_profile.target_audience = null` | Field stays blank (no autofill); no JS error | N/A |
| Client has no BVP yet | `brand_voice_profile = null` | `brand_voice_profile` is null in list response; autofill skips silently | N/A |
| Client switches mid-session | User switches active client; new client has different target_audience | Field updates to new client's audience (existing `switchingClient` logic in effect) | N/A |
| GitHub: Setup URL not configured | User clicks "Connect GitHub" | Redirects to GitHub settings page instead of app (Bug A — config-only fix) | Requires github.com/settings/apps/{slug}/edit → Setup URL field |

</frozen-after-approval>

## Code Map

- `backend/app/schemas/client.py:107-114` -- `ClientListItem` Pydantic schema — missing `brand_voice_profile` field
- `backend/app/routers/clients.py:70-76` -- `list_clients` builds `ClientListItem` objects — does not pass `brand_voice_profile`
- `frontend/app/(app)/campaigns/new/page.tsx:47-57` -- autofill useEffect reads `activeClient?.brand_voice_profile?.target_audience`
- `frontend/lib/types.ts:46-53` -- `ClientListItem` TS type already has optional `brand_voice_profile` field — no change needed
- `frontend/lib/stores/useClientStore.ts` -- stores `ClientListItem[]`; will carry BVP once backend sends it
- `frontend/app/api/auth/github/route.ts` -- builds install URL with `GITHUB_APP_SLUG`; no code change needed
- `frontend/.env.example` -- update comment to call out the Setup URL field name precisely

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/schemas/client.py` -- Add `brand_voice_profile: Optional[dict] = None` to `ClientListItem` -- the list endpoint must return BVP data so the store carries it for autofill
- [x] `backend/app/routers/clients.py` -- Pass `brand_voice_profile=client.brand_voice_profile` in the `ClientListItem(...)` constructor inside `list_clients` -- wires the newly added field to the actual ORM value
- [x] `frontend/.env.example` -- Update the GitHub comment: rename "Callback URL" to "Setup URL" and add the field path `GitHub App settings → General → Post installation → Setup URL` -- prevents future misconfiguration
- [ ] **[Config — outside code]** `github.com/settings/apps/personnapress/edit` → "Post installation" section → set "Setup URL" to `https://personnapress.com/api/auth/github/callback` and check "Redirect on update" -- this is the only fix for Bug A; no code change makes this work without it

**Acceptance Criteria:**
- Given a client with a completed voice profile that includes `target_audience`, when the user navigates to New Campaign, then the Target audience field is pre-filled with that value
- Given a client with `target_audience: null` in BVP, when the user navigates to New Campaign, then the Target audience field is blank and no console error appears
- Given `brand_voice_profile = null` (no ingestion run), when GET /clients is called, then the response contains `"brand_voice_profile": null` for that client
- Given the GitHub App Setup URL is configured, when the user clicks "Connect GitHub" and completes the GitHub installation flow, then they are redirected back to `/clients/{id}/connections` (not to GitHub settings)

## Spec Change Log

## Verification

**Commands:**
- `cd backend && python -m pytest tests/ -k "client" -x` -- expected: all client-related tests pass
- `cd backend && python -m pytest tests/ -x` -- expected: full test suite green

**Manual checks (if no CLI):**
- After backend change: call GET /api/v1/clients and confirm each item has `brand_voice_profile` key (null or object, never absent)
- After backend change: load New Campaign page for a client with a ready voice profile; confirm Target audience field shows the extracted audience string
