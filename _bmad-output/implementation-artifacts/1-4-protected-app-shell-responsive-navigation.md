# Story 1.4: Protected App Shell & Responsive Navigation

Status: ready-for-dev

## Story

As an authenticated user,
I want a persistent navigation shell with sidebar and responsive layout that adapts to my device,
So that I can navigate the application from any surface and always know my current context.

## Acceptance Criteria

1. **Given** an authenticated user visits any `(app)/` route, **When** the page renders, **Then** the full app shell is displayed: Paper-background sidebar (240px wide on lg, 1px right border, no shadow); logo and product name in the sidebar header; primary nav links — Dashboard, Clients, Calendar; account link pinned to sidebar bottom; client switcher placeholder in the sidebar header (shows "No clients yet — add one" until Epic 2 populates it); main content area with 720px max-width and correct horizontal padding (32px tablet, 48px desktop).

2. **Given** a viewport at 1024px or wider (lg), **When** the app shell renders, **Then** the full 240px sidebar is visible and persistent; page content renders at 720px max-width within the content pane.

3. **Given** a viewport between 768px and 1023px (md), **When** the app shell renders, **Then** the sidebar collapses to 56px icon-only width showing only nav icons; tooltips appear on icon hover; the content area expands to fill the remaining width.

4. **Given** a viewport below 768px, **When** the app shell renders, **Then** no sidebar is visible; instead a top bar is shown with logo, hamburger menu icon, and active client name; tapping the hamburger opens a slide-in drawer with the full nav links; the drawer can be closed by tapping outside it or pressing Esc.

5. **Given** the app shell is rendering, **When** the initial data fetch is in progress, **Then** skeleton placeholders matching the shape of sidebar nav links (3 rectangular blocks at correct heights) are shown — not a spinner — until the layout is ready.

6. **Given** a screen reader navigates the app shell, **When** the user tabs through the interface, **Then** all nav items are reachable via Tab with visible focus indicators (2px Ink ring); Tab order matches visual DOM reading order; there are no tab traps outside of modal/dialog contexts; the mobile drawer announces as `role="dialog"` with `aria-modal="true"`.

7. **Given** the active navigation item, **When** it is rendered, **Then** it displays Highlighter background (#FFF1B8), Ink text (#111111), a 2px left Ink border, and `aria-current="page"`; all inactive items display Graphite (#555555) labels with Highlighter background and Ink text on hover.

8. **Given** all interactive elements in the app shell, **When** measured for touch target size, **Then** each has minimum height and width of 44px (WCAG 2.2 AA).

9. **Given** a logged-in user clicks "Log out" in the Account section, **When** `POST /api/v1/auth/logout` completes, **Then** the httpOnly cookie is cleared and the user is redirected to `/login`.

## Tasks / Subtasks

- [ ] Task 1: Create `useUIStore` additions for mobile drawer state (AC: #4)
  - [ ] 1.1 In `frontend/lib/stores/useUIStore.ts`: add `isMobileDrawerOpen: boolean`, `openMobileDrawer()`, `closeMobileDrawer()` to the Zustand store
  - [ ] 1.2 Confirm store file exists from Story 1.1 scaffold; if not, create it with all fields

- [ ] Task 2: `AppShell` layout root component (AC: #1, #2, #3, #4)
  - [ ] 2.1 Create `frontend/components/layout/AppShell.tsx` — Client Component that composes `Sidebar`, `MobileTopBar`, `MobileDrawer`
  - [ ] 2.2 Apply sidebar margin offsets: `lg:ml-60 md:ml-14` on the `<main>` element
  - [ ] 2.3 Apply mobile top-bar offset: `pt-14 lg:pt-0` on `<main>` for the 56px top bar
  - [ ] 2.4 Content area inner wrapper: `max-w-[720px] px-8 lg:px-12 py-8 mx-auto`
  - [ ] 2.5 On route change (via `usePathname` effect), call `closeMobileDrawer()` so the drawer closes on navigation

- [ ] Task 3: `Sidebar` component — desktop (AC: #1, #2, #3, #7, #8)
  - [ ] 3.1 Create `frontend/components/layout/Sidebar.tsx`
  - [ ] 3.2 Outer `<aside>`: `hidden md:flex flex-col h-screen fixed left-0 top-0 z-40 w-14 lg:w-60 bg-[#F9F9F6] border-r border-[#E5E5E5]`
  - [ ] 3.3 Add `aria-label="Sidebar"` on `<aside>`
  - [ ] 3.4 Compose `<ClientSwitcher />` at the top, primary `<nav>` in the flex-grow middle, `<NavItem href="/account" ... />` pinned to the bottom with `border-t border-[#E5E5E5]`

- [ ] Task 4: `NavItem` component (AC: #6, #7, #8)
  - [ ] 4.1 Create `frontend/components/layout/NavItem.tsx` — Client Component
  - [ ] 4.2 Derive active state from `usePathname()` — `pathname === href || pathname.startsWith(href + '/')`
  - [ ] 4.3 Active classes: `bg-[#FFF1B8] border-l-2 border-[#111111] text-[#111111] font-medium pl-[calc(0.75rem-2px)]`
  - [ ] 4.4 Inactive classes: `border-l-2 border-transparent text-[#555555] hover:bg-[#FFF1B8] hover:text-[#111111]`
  - [ ] 4.5 Base classes: `group relative flex items-center gap-3 min-h-[44px] px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]`
  - [ ] 4.6 Icon: `shrink-0 w-[18px] h-[18px]` — Ink on active, Graphite on inactive, Ink on group-hover
  - [ ] 4.7 Label: `hidden lg:block truncate` — visible only at lg (240px sidebar)
  - [ ] 4.8 Tooltip (md only): `lg:hidden absolute left-full ml-2 px-2 py-1 bg-[#111111] text-[#F9F9F6] text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-150` with `role="tooltip"`
  - [ ] 4.9 Set `aria-current="page"` on active link
  - [ ] 4.10 Accept optional `onClick` prop for drawer usage (closes drawer on nav click)

- [ ] Task 5: `ClientSwitcher` component (AC: #1)
  - [ ] 5.1 Create `frontend/components/layout/ClientSwitcher.tsx` — Client Component
  - [ ] 5.2 Trigger button: `flex items-center w-full h-14 gap-2 border-b border-[#E5E5E5] hover:bg-[#FFF1B8] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]` with `justify-center lg:justify-start lg:px-4`
  - [ ] 5.3 Set `aria-expanded`, `aria-haspopup="listbox"`, `aria-label="Switch client"` on the trigger button
  - [ ] 5.4 Show active client initial as 18×18 box (`bg-[#E5E5E5] flex items-center justify-center text-xs font-bold`) — visible at md and lg
  - [ ] 5.5 Show active client name (`hidden lg:block flex-1 text-sm font-medium text-[#111111] truncate`) + `ChevronDown` icon (rotates 180deg when open) — visible only at lg
  - [ ] 5.6 Dropdown: `absolute top-full left-0 z-50 min-w-[200px] w-full lg:w-56 bg-[#F9F9F6] border border-[#E5E5E5] shadow-[4px_4px_0px_#111111] py-1` with `role="listbox"`
  - [ ] 5.7 Empty state: "No clients yet." with link to `/clients/new`
  - [ ] 5.8 Client list items: `role="option"`, `aria-selected`, `Check` icon (opacity-0 when not selected), `hover:bg-[#FFF1B8]`
  - [ ] 5.9 Close dropdown on: click outside (mousedown), Esc key, option selection
  - [ ] 5.10 For Story 1.4: always shows empty state (no clients yet — Epic 2 populates); props type `clients?: Client[]` defaults to `[]`

- [ ] Task 6: `MobileTopBar` component (AC: #4, #8)
  - [ ] 6.1 Create `frontend/components/layout/MobileTopBar.tsx`
  - [ ] 6.2 `<header>`: `flex lg:hidden items-center h-14 fixed top-0 left-0 right-0 z-40 bg-[#F9F9F6] border-b border-[#E5E5E5] px-4 gap-4`
  - [ ] 6.3 Logo: `font-['Playfair_Display'] font-bold text-[#111111] text-lg shrink-0` — shows "PP" or "PersonnaPress" per viewport
  - [ ] 6.4 Active client name: `flex-1 text-sm text-[#555555] truncate text-center`
  - [ ] 6.5 Hamburger: `flex items-center justify-center w-11 h-11 shrink-0 text-[#111111] hover:bg-[#FFF1B8] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]` — `aria-label="Open navigation"`, calls `openMobileDrawer()`
  - [ ] 6.6 Use `Menu` icon from `lucide-react`

- [ ] Task 7: `MobileDrawer` component (AC: #4, #6, #8)
  - [ ] 7.1 Create `frontend/components/layout/MobileDrawer.tsx`
  - [ ] 7.2 Backdrop: `lg:hidden fixed inset-0 z-40 bg-[#111111]/40 transition-opacity duration-200 motion-reduce:transition-none` — `opacity-100` when open, `opacity-0 pointer-events-none` when closed; `aria-hidden="true"`, click calls `closeMobileDrawer()`
  - [ ] 7.3 Drawer panel: `lg:hidden fixed top-0 left-0 bottom-0 z-50 w-[280px] flex flex-col bg-[#F9F9F6] border-r border-[#E5E5E5] transition-transform duration-200 ease-out motion-reduce:transition-none` — `translate-x-0` when open, `-translate-x-full` when closed
  - [ ] 7.4 Panel attributes: `role="dialog"`, `aria-modal="true"`, `aria-label="Navigation"`, `tabIndex={-1}`
  - [ ] 7.5 Drawer header: `flex items-center justify-between h-14 px-4 border-b border-[#E5E5E5]` — wordmark left, close button right (`X` icon, `w-11 h-11`, `aria-label="Close navigation"`)
  - [ ] 7.6 Below header: `<ClientSwitcher />`, nav items (same `NAV_ITEMS` as sidebar, each with `onClick={closeMobileDrawer}`), account nav item at bottom
  - [ ] 7.7 On Esc key: call `closeMobileDrawer()` (attach listener only when open)
  - [ ] 7.8 Lock body scroll when drawer open: `document.body.style.overflow = 'hidden'`; restore on close

- [ ] Task 8: `SidebarSkeleton` component (AC: #5)
  - [ ] 8.1 Create `frontend/components/layout/SidebarSkeleton.tsx`
  - [ ] 8.2 Three `animate-pulse bg-[#E5E5E5] mx-3` blocks at 44px height — shown while client data loads
  - [ ] 8.3 `aria-hidden="true"` on the skeleton container

- [ ] Task 9: `(app)` route group layout (AC: #1, #2, #3, #4, #5)
  - [ ] 9.1 Create `frontend/app/(app)/layout.tsx` — Server Component
  - [ ] 9.2 Render `<AppShell>{children}</AppShell>`
  - [ ] 9.3 This layout is distinct from `(auth)/layout.tsx` (which has no shell)
  - [ ] 9.4 Confirm middleware.ts (Story 1.3) already gates this route group — no additional auth check needed in layout

- [ ] Task 10: `/dashboard` placeholder page (AC: #1)
  - [ ] 10.1 Create `frontend/app/(app)/dashboard/page.tsx` — placeholder Server Component
  - [ ] 10.2 Minimal content: H1 "Dashboard" in Playfair Display — sufficient to verify shell renders
  - [ ] 10.3 Set `metadata.title = "Dashboard — PersonnaPress"`

- [ ] Task 11: Logout integration (AC: #9)
  - [ ] 11.1 In the Account `NavItem` bottom of sidebar, hook the `logout()` function from `frontend/lib/auth.ts` (created in Story 1.3)
  - [ ] 11.2 The Account link at `/account` navigates normally; the actual logout button will be rendered ON the `/account` page (Story 1.5)
  - [ ] 11.3 For now, ensure the logout function is importable and that calling it from any layout component correctly POSTs and redirects

- [ ] Task 12: Global CSS — reduced-motion safe net (AC: #6)
  - [ ] 12.1 In `frontend/app/globals.css`: add `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; } }`
  - [ ] 12.2 Confirm drawer and backdrop transitions have `motion-reduce:transition-none` Tailwind class as a belt-and-suspenders override

## Dev Notes

### Nav Items Registry

```typescript
// Used in both Sidebar.tsx and MobileDrawer.tsx
import { LayoutDashboard, Users, Calendar, Settings } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/clients',   label: 'Clients',   icon: Users },
  { href: '/calendar',  label: 'Calendar',  icon: Calendar },
]
// Account is rendered separately (pinned bottom / drawer bottom)
```

All icons must be imported from `lucide-react` — the project's installed icon library. No emoji, no custom SVG files unless added to the icon library.

### Sidebar Exact Class Specifications

**Outer `<aside>` (desktop):**
```
hidden md:flex flex-col h-screen fixed left-0 top-0 z-40
w-14 lg:w-60
bg-[#F9F9F6] border-r border-[#E5E5E5]
```

**NavItem active state:**
```
bg-[#FFF1B8] border-l-2 border-[#111111] text-[#111111] font-medium
pl-[calc(0.75rem-2px)]
```
(The `pl-` compensates for the 2px border so icon stays horizontally consistent with inactive items.)

**NavItem inactive state:**
```
border-l-2 border-transparent text-[#555555]
hover:bg-[#FFF1B8] hover:text-[#111111]
```

**NavItem base (always):**
```
group relative flex items-center gap-3 min-h-[44px] px-3 text-sm
transition-colors
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]
```

### Mobile Drawer Transition

The drawer slides in from the left using `translateX`:
- Closed: `-translate-x-full` (off-screen left)
- Open: `translate-x-0`
- Transition: `transition-transform duration-200 ease-out`
- Reduced motion override: `motion-reduce:transition-none`

The backdrop fades with opacity:
- Closed: `opacity-0 pointer-events-none`
- Open: `opacity-100`
- Transition: `transition-opacity duration-200`

Both are driven by `isMobileDrawerOpen` from Zustand — no local state in MobileDrawer.

### ClientSwitcher — v1 Empty State

For Story 1.4, the switcher always renders the empty state since no clients exist yet. The component is wired up and functional — Epic 2 (Story 2.3) passes real `clients` and `activeClientId` into it.

```tsx
// Empty state copy (no exclamation mark)
"No clients yet." with <Link href="/clients/new">Add one</Link>
```

### AppShell Content Area Layout

```
┌──────────────────────────────────────────────────────┐
│ Sidebar (fixed) │         Main (ml-60 / ml-14)       │
│  240px lg        │  ┌────────────────────────────┐   │
│   56px md        │  │ max-w-[720px] mx-auto       │   │
│                  │  │ px-12 (lg) / px-8 (md/sm)   │   │
│                  │  │ py-8                         │   │
│                  │  └────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

Content pane never overflows the viewport width. The `mx-auto` with `max-w-[720px]` centers content within the available pane space.

### Dependency on Story 1.3

- `middleware.ts` must exist and gate `(app)/` routes before this shell is visible
- `frontend/lib/auth.ts` must export `logout()` (created in Story 1.3)
- `useUIStore` may already exist from Story 1.1 — check before creating; add the drawer fields

### Architecture Rules for this Story

- `AppShell` is a Client Component (uses Zustand, `usePathname`)
- `(app)/layout.tsx` is a Server Component — it renders `<AppShell>` which becomes the client boundary
- No business logic in layout components — they compose and nothing else
- All icons from `lucide-react` only; no emoji substitutes
- No `console.log` in components; no `any` TypeScript types

### Next.js Guide Check

Before implementing layout.tsx and AppShell.tsx, read `node_modules/next/dist/docs/` for the current App Router layout nesting rules in Next.js 16. Specifically check how nested layouts in route groups interact with the root layout.

### Project Structure Notes

New files this story creates:
```
frontend/
├── app/
│   ├── (app)/
│   │   ├── layout.tsx                       ← NEW — app shell wrapper
│   │   └── dashboard/
│   │       └── page.tsx                     ← NEW — placeholder
├── components/
│   └── layout/
│       ├── AppShell.tsx                     ← NEW
│       ├── Sidebar.tsx                      ← NEW
│       ├── NavItem.tsx                      ← NEW
│       ├── ClientSwitcher.tsx               ← NEW
│       ├── MobileTopBar.tsx                 ← NEW
│       ├── MobileDrawer.tsx                 ← NEW
│       └── SidebarSkeleton.tsx              ← NEW
```

Updated files:
```
frontend/lib/stores/useUIStore.ts            ← ADD drawer state fields
frontend/app/globals.css                     ← ADD reduced-motion safe net
```

### References

- App shell spec: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]
- Paper Style sidebar, nav item, client switcher component specs: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/DESIGN.md#Components]
- Responsive behavior (lg/md/mobile), drawer UX, tooltip rules: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Responsive Behavior]
- Microcopy rules (no exclamation marks): [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Voice and Tone]
- Touch target 44px WCAG 2.2 AA, `aria-current`, dialog/modal focus trap: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md#Accessibility]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
