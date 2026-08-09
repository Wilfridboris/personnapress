---
baseline_commit: df1a6a9
---

# Story: Fix Sidebar Client Nav UX

Status: done

---

## Story

As a PersonnaPress user on the Growth (or any) plan with one or more existing clients,
I want the sidebar to let me create additional clients and navigate to my active client in one click,
so that I can manage multiple clients without hunting for a hidden route.

---

## Context & Motivation

### Root Cause (three separate bugs, one story)

**Bug 1 — No "New Client" entry in the ClientSwitcher dropdown when clients exist.**
`ClientSwitcher.tsx` shows a "Create client" link only when `clients.length === 0`. Once the user
has at least one client, the dropdown becomes a pure switcher with no creation path. The Growth plan
allows up to 5 clients, so a user with 1–4 clients has no visible way to add more from the sidebar.
The only fallback path (`ClientList.tsx`) is dead code — it is never rendered by any page.

**Bug 2 — "Clients" nav link causes a double navigation hop.**
Both `Sidebar` and `MobileDrawer` use `href="/clients"` from the static `NAV_ITEMS` array. That
route renders `ClientsRedirectClient`, which immediately fires `router.replace(/clients/${activeClientId})`.
The result is two URL changes instead of one. Both components already have `activeClientId` from
`useClientStore`, so the redirect is unnecessary.

**Bug 3 — "Back to clients" on the client detail page is a no-op loop.**
`/clients/[id]/page.tsx` renders an arrow link `href="/clients"` which routes back through the
same redirect and returns the user to the page they were already on.

### Additional Issues Found During Audit

- `ClientList.tsx` is dead code (never imported anywhere). It should be deleted.
- `CreateClientForm.tsx`'s `UpgradePrompt` component uses the Stripe portal for upgrades.
  Every other upgrade CTA in the app (`UpgradePromptModal`, `TrialBanner`, `TrialNudgeToast`)
  uses `href="/account#choose-plan"` (the in-app plan picker). This must be made consistent.
- `useClientStore` receives `plan_at_limit`, `plan_tier`, and `client_limit` from the API
  response on every app load (via `AppShell`), but those fields are discarded. They need to be
  stored so `ClientSwitcher` can show the correct footer without an extra API call.

---

## Acceptance Criteria

### AC 1: ClientSwitcher shows "New client" footer when user has clients and is not at plan limit

**Given** the user has one or more clients AND `planAtLimit` is false,
**When** they open the ClientSwitcher dropdown,
**Then** below the client list (separated by `border-t border-[#E5E5E5]`) a "New client" row
appears. Clicking it navigates to `/clients/new` and closes the dropdown.

The row must match the existing Paper Style design:
- `Plus` icon from `lucide-react` (`w-4 h-4`, `aria-hidden="true"`)
- Label: "New client"
- Same hover treatment as client rows: `hover:bg-[#FFF1B8] hover:text-[#111111] transition-colors`
- Full-width link, `py-2 px-3`, `text-[0.9375rem]`
- Rendered as a `<Link>` (not a `<button>`) — navigates, does not submit

### AC 2: ClientSwitcher shows at-limit footer when user has reached their plan cap

**Given** `planAtLimit` is true (e.g. 5/5 clients on Growth),
**When** they open the ClientSwitcher dropdown,
**Then** below the client list the footer shows:
`"X/Y clients · "` followed by an `"Upgrade plan"` link that navigates to `/account#choose-plan`.

- `X` = `clients.length`, `Y` = `clientLimit` from the store
- Footer text: `text-xs text-[#555555]`, the link: `text-[#111111] underline hover:no-underline`
- No "New client" option is shown when at limit

### AC 3: Empty-state "Create client" link is preserved unchanged

**Given** the user has zero clients (first onboarding),
**When** they open the ClientSwitcher dropdown,
**Then** the existing "No clients yet. Create client" message is shown exactly as before (no change).

### AC 4: `useClientStore` stores plan quota data

`useClientStore` gains three new fields and one new setter:
```ts
planAtLimit: boolean        // default false
clientLimit: number         // default 0
planTier: string            // default ""
setPlanInfo: (planAtLimit: boolean, planTier: string, clientLimit: number) => void
```

These fields are NOT persisted to localStorage (keep the existing `partialize` that only
persists `activeClientId`).

### AC 5: `AppShell` populates plan data into store after client list fetch

In `AppShell.tsx`, inside `initClients()`, after `const data = await clientsApi.list()`:
```ts
store.setPlanInfo(data.plan_at_limit, data.plan_tier, data.client_limit);
```
Call this unconditionally before the `try/finally` exits.

### AC 6: "Clients" nav link navigates directly to the active client detail page

In both `Sidebar.tsx` and `MobileDrawer.tsx`, the "Clients" nav item's href must be:
- `activeClientId ? /clients/${activeClientId} : /clients` (fallback to `/clients` when no client selected)

Implement by computing `clientsHref` from `activeClientId` and overriding it in the `NAV_ITEMS.map`:
```tsx
const clientsHref = activeClientId ? `/clients/${activeClientId}` : "/clients";
// In the map:
<NavItem key={item.href} {...item} href={item.href === "/clients" ? clientsHref : item.href} />
```

`NavItem`'s active detection (`pathname.startsWith(href + "/")`) works correctly with the specific
client ID in the href. The nav item will no longer be highlighted when on `/clients/new` — this is
acceptable and a minor improvement (creation form is not a "view clients" context).

`ClientsRedirectClient.tsx` must NOT be changed or deleted — it remains a valid fallback for
bookmarks and direct browser navigation to `/clients`.

### AC 7: "Back to clients" arrow link removed from client detail page

In `frontend/app/(app)/clients/[id]/page.tsx`, remove the entire `<Link>` block:
```tsx
// DELETE this entire block:
<Link
  href="/clients"
  className="inline-flex items-center gap-2 text-sm text-[#555555] hover:text-[#111111] transition-colors mb-10"
>
  <ArrowLeft className="size-4" aria-hidden="true" />
  Back to clients
</Link>
```

Also remove the now-unused `ArrowLeft` import from `lucide-react`.

### AC 8: `CreateClientForm` upgrade prompt uses in-app plan picker

Replace the `UpgradePrompt` component's Stripe portal logic with a simple `<Link>` to
`/account#choose-plan`. The rewritten component:

```tsx
import Link from "next/link";

function UpgradePrompt({ message }: { message: string }) {
  return (
    <div role="alert" className="mb-6 border border-[#E5E5E5] p-4">
      <p className="text-sm text-[#111111] mb-3">{message}</p>
      <Link
        href="/account#choose-plan"
        className="text-sm border border-[#111111] text-[#111111] px-4 py-2 hover:bg-[#111111] hover:text-white transition-colors rounded-none inline-block"
      >
        Upgrade plan
      </Link>
    </div>
  );
}
```

Remove: `useState` for `loading`/`portalError`, the `openPortal` async function, the `fetchAPI`
import if it becomes unused after this change, and the `portalError` error paragraph. The `useState`
import may still be needed by the parent form — check before removing it.

### AC 9: `ClientList.tsx` deleted (dead code)

Delete `frontend/components/clients/ClientList.tsx`. It is not imported or rendered anywhere.
No tests reference it. Confirm with a grep before deleting.

---

## Dev Notes

### Files to Change

| File | Change |
|------|--------|
| `frontend/lib/stores/useClientStore.ts` | AC 4: add `planAtLimit`, `clientLimit`, `planTier`, `setPlanInfo` |
| `frontend/components/layout/AppShell.tsx` | AC 5: call `store.setPlanInfo(...)` in `initClients()` |
| `frontend/components/layout/ClientSwitcher.tsx` | AC 1/2/3: add "New client" / at-limit footer; import `Plus` from lucide-react |
| `frontend/components/layout/sidebar.tsx` | AC 6: compute `clientsHref`, override in map |
| `frontend/components/layout/MobileDrawer.tsx` | AC 6: same `clientsHref` override |
| `frontend/app/(app)/clients/[id]/page.tsx` | AC 7: remove "Back to clients" `<Link>` + `ArrowLeft` import |
| `frontend/components/clients/CreateClientForm.tsx` | AC 8: replace `UpgradePrompt` Stripe portal with `/account#choose-plan` `<Link>` |

### Files to Delete

| File | Reason |
|------|--------|
| `frontend/components/clients/ClientList.tsx` | AC 9: dead code, never imported anywhere |

### Files NOT to Change

- `frontend/components/clients/ClientsRedirectClient.tsx` — keep as fallback for direct `/clients` navigation
- `frontend/app/(app)/clients/page.tsx` — keep as-is (uses `ClientsRedirectClient`)
- `frontend/components/layout/NavItem.tsx` — no changes needed; existing active detection is correct
- Any backend file — all changes are frontend-only
- Any DB migration — no schema changes

### Key Data Flow

```
AppShell.initClients()
  → clientsApi.list()                       // GET /clients
  → returns { clients, plan_at_limit, plan_tier, client_limit }
  → store.setClients(clients)               // existing
  → store.setPlanInfo(...)                  // NEW: store plan quota
  → store.setActiveClientId(...)            // existing

ClientSwitcher
  → reads useClientStore: clients, planAtLimit, clientLimit
  → renders footer based on planAtLimit
```

### Design Reference — ClientSwitcher Footer

The dropdown container already has `py-1`. The footer divider uses `border-t border-[#E5E5E5]` and `mt-1`:

```tsx
// Not at limit — show "New client"
{clients.length > 0 && !planAtLimit && (
  <div className="border-t border-[#E5E5E5] mt-1">
    <Link
      href="/clients/new"
      onClick={() => setIsOpen(false)}
      className="flex items-center gap-2 w-full py-2 px-3 text-[0.9375rem] text-[#555555] hover:bg-[#FFF1B8] hover:text-[#111111] transition-colors"
    >
      <Plus className="w-4 h-4 shrink-0" aria-hidden="true" />
      <span>New client</span>
    </Link>
  </div>
)}

// At limit — show upgrade note
{clients.length > 0 && planAtLimit && (
  <div className="border-t border-[#E5E5E5] mt-1 px-3 py-2">
    <p className="text-xs text-[#555555]">
      {clients.length}/{clientLimit} clients &middot;{" "}
      <Link
        href="/account#choose-plan"
        onClick={() => setIsOpen(false)}
        className="text-[#111111] underline hover:no-underline"
      >
        Upgrade plan
      </Link>
    </p>
  </div>
)}
```

Note: when `clients.length === 0`, the existing empty-state div renders instead and neither footer is shown (AC 3 preserved).

### `useClientStore` Store Shape (after change)

```ts
interface ClientStore {
  clients: ClientListItem[];
  activeClientId: string | null;
  isInitialized: boolean;
  planAtLimit: boolean;       // NEW
  clientLimit: number;        // NEW
  planTier: string;           // NEW
  setClients: (clients: ClientListItem[]) => void;
  setActiveClientId: (id: string) => void;
  setInitialized: () => void;
  setPlanInfo: (planAtLimit: boolean, planTier: string, clientLimit: number) => void;  // NEW
  addClient: (client: ClientListItem) => void;
  updateClient: (id: string, data: Partial<ClientListItem>) => void;
  updateClientName: (id: string, name: string) => void;
  removeClient: (id: string) => void;
}
```

Initial values: `planAtLimit: false`, `clientLimit: 0`, `planTier: ""`.

The `partialize` in `persist` must NOT change — still persists only `activeClientId`. Plan data is
re-fetched fresh on every app load from the server.

### `AppShell` Change Location

In `initClients()` inside the `try` block, immediately after `store.setClients(clients)`:
```ts
store.setPlanInfo(data.plan_at_limit, data.plan_tier, data.client_limit);
```
`data` is the full `ClientListResponse` — `plan_at_limit`, `plan_tier`, and `client_limit` are all
present (see `frontend/lib/types.ts:111-116`).

### Sidebar `clientsHref` Pattern

Both `Sidebar.tsx` and `MobileDrawer.tsx` already read `activeClientId` from `useClientStore`. Add:
```tsx
const clientsHref = activeClientId ? `/clients/${activeClientId}` : "/clients";
```
Then in the `NAV_ITEMS.slice(...).map(...)` calls, pass the override:
```tsx
<NavItem key={item.href} {...item} href={item.href === "/clients" ? clientsHref : item.href} />
```
`MobileDrawer` also passes `onClick={close}` and `forceLabel` — keep those unchanged, only
override `href`.

### No Tests Required

This is a pure frontend UX fix with no business logic changes. No backend files changed, no new
API contracts introduced. Manual verification in the browser is sufficient.

---

## File List

- `frontend/lib/stores/useClientStore.ts`
- `frontend/components/layout/AppShell.tsx`
- `frontend/components/layout/ClientSwitcher.tsx`
- `frontend/components/layout/sidebar.tsx`
- `frontend/components/layout/MobileDrawer.tsx`
- `frontend/app/(app)/clients/[id]/page.tsx`
- `frontend/components/clients/CreateClientForm.tsx`
- ~~`frontend/components/clients/ClientList.tsx`~~ *(deleted)*

---

## Review Findings

- [x] [Review][Defer] ARIA listbox contract: `<Link>` inside `role="listbox"` without `role="option"` [frontend/components/layout/ClientSwitcher.tsx:122,158,172] — deferred, pre-existing (empty-state "Create client" Link also lacks role)
- [x] [Review][Defer] `calendarIdx === -1` sentinel: findIndex returns -1 if "Calendar" label absent, making slice(-1) return only last element [frontend/components/layout/sidebar.tsx:10, frontend/components/layout/MobileDrawer.tsx:16] — deferred, pre-existing; Calendar always present in NAV_ITEMS
- [x] [Review][Defer] `planTier` stored in useClientStore but no component reads it [frontend/lib/stores/useClientStore.ts:11] — deferred, spec-mandated (AC 4); intentional dead state for future use
- [x] [Review][Defer] AppShell silently discards all initClients() errors; planAtLimit/clientLimit stay at defaults with no retry or console warning [frontend/components/layout/AppShell.tsx:54] — deferred, pre-existing design decision

## Dev Agent Record

### Completion Notes

- AC 4: Added `planAtLimit`, `clientLimit`, `planTier` fields and `setPlanInfo` setter to `useClientStore`. Not persisted (partialize unchanged).
- AC 5: `AppShell.initClients()` now calls `store.setPlanInfo(data.plan_at_limit, data.plan_tier, data.client_limit)` after `setClients`.
- AC 1/2/3: `ClientSwitcher` reads `planAtLimit` and `clientLimit` from store. When clients exist and not at limit, shows "New client" footer with `Plus` icon. When at limit, shows `X/Y clients · Upgrade plan` footer. Empty-state unchanged.
- AC 6: Both `Sidebar` and `MobileDrawer` compute `clientsHref = activeClientId ? /clients/${activeClientId} : "/clients"` and override the `/clients` nav item href in both NAV_ITEMS map calls.
- AC 7: Removed entire "Back to clients" `<Link>` block and `ArrowLeft`/`Link` imports from `clients/[id]/page.tsx`.
- AC 8: Replaced `UpgradePrompt` Stripe portal logic with simple `<Link href="/account#choose-plan">`. Removed `useState` for `loading`/`portalError` and `openPortal` function.
- AC 9: Deleted `frontend/components/clients/ClientList.tsx` (confirmed not imported anywhere).

---

## Change Log

- 2026-08-08: Implemented all 9 ACs — sidebar UX fixes, plan quota store, ClientSwitcher footer, dead code removal (Story: fix-sidebar-client-nav-ux)
