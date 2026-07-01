# Story 2.3: Client List & Active Context Switching

Status: done

## Story

As an authenticated user,
I want to view all my clients and switch which client is active in my workspace,
So that I can manage content for multiple brands without confusion about which context I am working in.

## Acceptance Criteria

1. **Given** an authenticated user navigates to `/clients`, **When** the page loads, **Then** all clients owned by the user are displayed as cards showing: client name, website URL (if set), Brand Voice Profile status ("Voice profile ready" / "Profile incomplete" / "Analyzing..."), and the number of campaigns associated with that client.

2. **Given** a user clicks the Client Switcher dropdown in the sidebar header, **When** the dropdown opens, **Then** all client names are listed alphabetically; the currently active client is marked with a checkmark; if no clients exist, the dropdown shows "No clients yet." with a "Create client" link to `/clients/new`.

3. **Given** a user selects a different client from the Client Switcher, **When** the selection is made, **Then** `useClientStore.setActiveClientId` is updated with the new client ID; the user is navigated to `/dashboard` which reloads campaign history, Brand Voice Profile status, and Platform Connection status for the newly active client; the sidebar switcher label updates to the selected client name.

4. **Given** an authenticated user logs in and has at least one client, **When** the app shell initializes, **Then** the most recently active client ID (stored in localStorage) is restored into `useClientStore` as the active client.

5. **Given** a user with no clients lands on `/dashboard`, **When** the page renders, **Then** an empty state is displayed: "No clients yet." as an H2, body text "Create a client to start generating content.", and a "Create your first client" primary CTA — no campaign rows or list skeleton.

6. **Given** a user on the Growth plan (5-client limit) already has 5 clients and views `/clients`, **When** the page renders, **Then** no "New Client" button is shown; instead, a text message reads "You've reached the 5-client limit on your Growth plan." with an "Upgrade to Agency" link.

7. **Given** the `/clients` page, **When** a client card is in its default state, **Then** it uses Paper Style default card (white fill, 1px Border, no shadow, sharp corners); on hover the card shows a hard 4px brutalist shadow (`shadow-[4px_4px_0px_#111111]`); clicking the card navigates to `/clients/{id}`.

8. **Given** the client list, **When** the skeleton loading state is active (data fetch in progress), **Then** skeleton placeholder cards matching the shape of real client cards are shown (name line, URL line, status line, campaign count line) — no spinner; the "New Client" button area shows a skeleton block too.

## Tasks / Subtasks

- [x] Task 1: Backend — `GET /api/v1/clients` endpoint (AC: #1, #6)
  - [x] 1.1 Add `GET /api/v1/clients` to `backend/app/routers/clients.py`; require auth
  - [x] 1.2 In `backend/app/db/repositories/clients.py`, add `get_clients_by_user(session, user_id)`: query all `clients` where `user_id = user_id`, join or subquery `campaigns` count per client; order alphabetically by `name`
  - [x] 1.3 Define `ClientListItem` schema in `backend/app/schemas/client.py`: `id`, `name`, `website_url`, `brand_voice_profile_status` (derived: `"ready"` if BVP non-null, `"analyzing"` if active ingestion job exists, `"incomplete"` otherwise), `campaign_count: int`
  - [x] 1.4 Include `plan_at_limit: bool` in the list response metadata to tell the frontend whether to show the "New Client" button or the limit message
  - [x] 1.5 Return `ClientListResponse`: `{"clients": [...], "plan_at_limit": bool, "plan_tier": str, "client_limit": int}`

- [x] Task 2: Backend — BVP status derivation (AC: #1)
  - [x] 2.1 For each client in the list, check if there is an active `jobs` record with `job_type='ingestion'` and `status IN ('pending', 'in_progress')`; if yes → `"analyzing"`
  - [x] 2.2 If `client.brand_voice_profile` is not null → `"ready"`; else if no active job → `"incomplete"`
  - [x] 2.3 Implement as a database query (LEFT JOIN on `jobs`) to avoid N+1 queries — fetch all clients and their latest ingestion job status in a single query

- [x] Task 3: Frontend — `/clients` page (AC: #1, #6, #7, #8)
  - [x] 3.1 Create `frontend/app/(app)/clients/page.tsx` — Server Component with metadata `title: "Clients — PersonnaPress"`; fetch `GET /api/v1/clients` server-side with session cookie
  - [x] 3.2 Create `frontend/components/clients/ClientList.tsx` — `'use client'` for interactive card navigation and store updates
  - [x] 3.3 Page layout: Playfair Display H1 "Clients", `max-w-[720px]`, right-aligned "New Client" Primary Button in the page header row — `flex items-center justify-between`
  - [x] 3.4 If `plan_at_limit`: hide "New Client" button; show `<p className="text-[#555555] text-sm">You've reached the {clientLimit}-client limit on your {planTier} plan. <a href="#" onClick={openStripePortal}>Upgrade to Agency</a></p>`
  - [x] 3.5 Client card component `frontend/components/clients/ClientCard.tsx`:
    - Outer: `<article className="bg-white border border-[#E5E5E5] p-6 cursor-pointer transition-shadow hover:shadow-[4px_4px_0px_#111111] rounded-none">`
    - Client name: Inter medium, Ink (#111111), 1rem
    - Website URL (if set): Inter, Graphite (#555555), 14px
    - BVP status badge line: Inter 12px uppercase tracked label — "VOICE PROFILE READY" (Success green, no badge, just colored label), "ANALYZING..." (Graphite JetBrains Mono), "PROFILE INCOMPLETE" (Graphite)
    - Campaign count: Inter, Graphite, "N campaigns"
    - Click handler: `router.push('/clients/' + client.id)`
  - [x] 3.6 Skeleton loading: create `frontend/components/clients/ClientCardSkeleton.tsx` — matching card shape with shimmer `<div className="animate-pulse bg-[#E5E5E5] rounded-none h-4 w-3/4 mb-2" />` blocks; show 3 skeleton cards while data is fetching

- [x] Task 4: Frontend — Client Switcher dropdown in sidebar (AC: #2, #3, #4)
  - [x] 4.1 Locate the sidebar client switcher area in `frontend/components/layout/Sidebar.tsx` (established in Story 1.4); upgrade the placeholder to a functional dropdown
  - [x] 4.2 Create `frontend/components/clients/ClientSwitcher.tsx` — `'use client'`, reads `useClientStore.clients` and `useClientStore.activeClientId`
  - [x] 4.3 Dropdown trigger: shows active client name (truncated to 160px max-width with CSS `text-overflow: ellipsis`) + chevron-down icon (Lucide `ChevronDown`, `size-4`, Graphite); 56px height, full sidebar width; Paper background, 1px bottom Border
  - [x] 4.4 Dropdown panel: positioned absolutely below the trigger, `w-60`, Paper background, 1px Ink border, `z-50`; client list sorted alphabetically; each item shows client name + checkmark (Lucide `Check`, `size-4`) if active
  - [x] 4.5 On client selection: call `useClientStore.setActiveClientId(id)`; persist to localStorage (`localStorage.setItem('activeClientId', id)`); close dropdown; navigate to `/dashboard` via `router.push('/dashboard')`
  - [x] 4.6 Empty state: if `clients.length === 0`, show "No clients yet." + "Create client" link to `/clients/new` inside dropdown
  - [x] 4.7 Close dropdown on: clicking outside (attach `mousedown` listener on `document`), Esc key, item selection
  - [x] 4.8 Accessibility: dropdown trigger has `aria-haspopup="listbox"`, `aria-expanded={isOpen}`; panel has `role="listbox"`; each client item has `role="option"`, `aria-selected={isActive}`; Esc closes and returns focus to trigger

- [x] Task 5: Frontend — Active client persistence on app shell init (AC: #4)
  - [x] 5.1 In the app shell layout `frontend/app/(app)/layout.tsx` (established in Story 1.4): on mount (`useEffect`), read `localStorage.getItem('activeClientId')`; if present and the client exists in the fetched clients list, call `useClientStore.setActiveClientId(id)`
  - [x] 5.2 Fetch the client list once on app shell init (`GET /api/v1/clients`) and populate `useClientStore.clients` — this drives both the sidebar switcher and the `/clients` page (the page re-fetches independently server-side for freshness)
  - [x] 5.3 If no localStorage value or stored ID not found in current list: set first client alphabetically as active

- [x] Task 6: Frontend — Dashboard empty state for no-client users (AC: #5)
  - [x] 6.1 In `frontend/app/(app)/dashboard/page.tsx` (established in Story 1.4): check `useClientStore.clients.length === 0`
  - [x] 6.2 Render empty state: `<h2 className="font-['Playfair_Display'] text-2xl font-bold text-[#111111] text-center">No clients yet.</h2>`, body text "Create a client to start generating content." (Inter, Graphite, centered), "Create your first client" Primary Button linking to `/clients/new`
  - [x] 6.3 Empty state is centered in the content area — the only context where centered text is used per Paper Style (empty states and onboarding screens)

- [x] Task 7: Zustand store — `useClientStore` full implementation (AC: #3, #4)
  - [x] 7.1 Create or update `frontend/lib/stores/useClientStore.ts` with full state shape:
    ```typescript
    interface ClientStore {
      clients: ClientListItem[]
      activeClientId: string | null
      setClients: (clients: ClientListItem[]) => void
      setActiveClientId: (id: string) => void
      addClient: (client: ClientListItem) => void
      updateClientName: (id: string, name: string) => void
      removeClient: (id: string) => void
    }
    ```
  - [x] 7.2 `setActiveClientId` automatically persists to `localStorage` and updates the sidebar switcher label via reactive state
  - [x] 7.3 Initialize store with `clients: []`, `activeClientId: null` — populated by the app shell init (Task 5)

## Dev Notes

### Client List Page — Paper Style Layout

```
Clients                    [ New Client ]   ← Playfair H1 + Primary Button (right-aligned)
                                            ← "flex items-center justify-between mb-8"

─────────────────────────────────────────

┌─────────────────────────────────────────┐
│ Acme Corp                               │ ← Inter medium, Ink
│ acmecorp.com                            │ ← Inter 14px, Graphite
│ VOICE PROFILE READY                     │ ← Inter 12px uppercase, Success (#2E4F2E)
│ 7 campaigns                             │ ← Inter 14px, Graphite
│                        →                │ ← hover: shadow-[4px_4px_0px_#111111]
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ TechStartup Inc.                        │
│ techstartup.io                          │
│ ANALYZING...                            │ ← JetBrains Mono, Graphite, pulsing opacity
│ 3 campaigns                             │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Personal Blog                           │
│ (no URL set)                            │
│ PROFILE INCOMPLETE                      │ ← Inter 12px uppercase, Graphite
│ 0 campaigns                             │
└─────────────────────────────────────────┘
```

### Client Switcher Dropdown — Paper Style Layout

```
┌──────────────────────────────────────┐  ← sidebar, 240px wide
│ Acme Corp              ▼             │  ← 56px height, chevron right-aligned
├──────────────────────────────────────┤  ← 1px Ink border
│ ✓ Acme Corp                          │  ← active: Highlighter bg, 2px left Ink border
│   TechStartup Inc.                   │  ← hover: Highlighter bg
│   Personal Blog                      │
└──────────────────────────────────────┘

Panel: bg-[#F9F9F6], border border-[#111111], z-50, absolute
Items: py-2 px-3, text-[0.9375rem], text-[#555555]
Active item: bg-[#FFF1B8], text-[#111111], border-l-2 border-[#111111]
```

### Dashboard Empty State — Paper Style

```
(centered in content area, no sidebar content except nav)

        No clients yet.
(Playfair Display H2, centered, Ink)

  Create a client to start generating content.
  (Inter 15px, Graphite, centered)

        [ Create your first client ]
             Primary Button
```

### N+1 Query Prevention

The backend `GET /api/v1/clients` must fetch clients AND their ingestion job status AND campaign counts in a single query — not per-client. Use SQLAlchemy with a subquery or LEFT JOIN:

```python
# backend/app/db/repositories/clients.py
from sqlmodel import select, func
from sqlalchemy import case

async def get_clients_by_user(session, user_id):
    # One query: clients + campaign count + latest ingestion job status
    stmt = (
        select(
            Client,
            func.count(Campaign.id).label("campaign_count"),
            func.max(case(
                (Job.status.in_(["pending", "in_progress"]), 1), else_=0
            )).label("has_active_ingestion")
        )
        .outerjoin(Campaign, Campaign.client_id == Client.id)
        .outerjoin(Job, (Job.client_id == Client.id) & (Job.job_type == "ingestion"))
        .where(Client.user_id == user_id)
        .group_by(Client.id)
        .order_by(Client.name)
    )
    results = await session.exec(stmt)
    return results.all()
```

### localStorage Persistence

```typescript
// frontend/lib/stores/useClientStore.ts
const setActiveClientId = (id: string) => {
  set({ activeClientId: id })
  if (typeof window !== 'undefined') {
    localStorage.setItem('activeClientId', id)
  }
}
```

On app shell init, read from localStorage before any API call completes so the sidebar shows the correct client immediately without flash.

### Architecture Rules

- `/clients` page uses server-side fetch for initial HTML (SEO + no loading flash for returning users)
- `useClientStore` is initialized from the server-fetched list passed as props to the app shell Client Component
- `GET /api/v1/clients` returns `plan_at_limit` so the frontend never has to re-compute tier limits

### New Files This Story

```
frontend/app/(app)/clients/page.tsx          ← NEW
frontend/components/clients/ClientList.tsx   ← NEW
frontend/components/clients/ClientCard.tsx   ← NEW
frontend/components/clients/ClientCardSkeleton.tsx ← NEW
frontend/components/clients/ClientSwitcher.tsx ← NEW
```

Updated files:
```
backend/app/routers/clients.py              ← ADD GET /clients
backend/app/db/repositories/clients.py     ← ADD get_clients_by_user()
backend/app/schemas/client.py             ← ADD ClientListItem, ClientListResponse
frontend/app/(app)/layout.tsx             ← ADD client list init + localStorage restore
frontend/app/(app)/dashboard/page.tsx     ← ADD empty state for no-client users
frontend/components/layout/Sidebar.tsx   ← REPLACE placeholder with ClientSwitcher
frontend/lib/stores/useClientStore.ts     ← FULL implementation (was partial in Story 2.1)
frontend/lib/types.ts                     ← ADD ClientListItem, ClientListResponse
```

### References

- Story spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]
- FR-7 (List and switch Clients): [Source: _bmad-output/planning-artifacts/epics.md#Functional Requirements]
- AR-10 (Zustand for useClientStore): [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements]
- UX-DR7 (Client Switcher dropdown spec, 56px height, checkmark): [Source: _bmad-output/planning-artifacts/epics.md#UX Design Requirements]
- UX-DR19 (Client Switcher behavior — optimistic label, navigate to Dashboard): [Source: _bmad-output/planning-artifacts/epics.md#UX Design Requirements]
- UX-DR17 (skeleton loading, not spinner): [Source: _bmad-output/planning-artifacts/epics.md#UX Design Requirements]
- Paper Style card hover shadow: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Cards]
- WCAG focus and touch targets: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR16]
