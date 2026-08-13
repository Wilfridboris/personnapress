---
baseline_commit: 6d732ab
---

# Story 21.10: Meta Beta Gate + Support Page

Status: done

---

## Story

As a PersonnaPress user,
I want Meta platform connections (Instagram, Facebook Page, Threads) to show a meaningful beta gate
when not yet publicly available, and as a beta tester I can self-unlock access instantly,
so that invited testers can connect their Meta accounts while non-testers have a clear path to request access.

As a PersonnaPress user,
I want a Help & Support page accessible from the sidebar and the Account page,
so that I can quickly contact support or request early access without hunting for an email address.

---

## Context & Motivation

Meta publishing (Instagram, Facebook Page, Threads) is fully implemented (Epic 21) but gated behind
`NEXT_PUBLIC_META_PUBLISHING_ENABLED`. When `false`, the current UI shows a hard-disabled button with
a tooltip — no request path, no beta bypass.

Boris is awaiting Meta Business API approval. In the meantime, invited beta testers need access.
The solution is a purely frontend honor-system gate: a localStorage flag unlocks the connect buttons
for users who self-identify as beta testers (invited by Boris directly). No backend changes are needed.

A support page is also needed as a permanent entry point for users who need help, want to report bugs,
or want to request beta access. It lives at `/account/support` and is reachable from both the sidebar
and the Account page.

---

## Acceptance Criteria

### AC 1: MetaPlatformsSection — three distinct states

**Given** `NEXT_PUBLIC_META_PUBLISHING_ENABLED=true`,
**When** the Connections page renders the Meta section,
**Then** the section behaves exactly as today (connect buttons for Facebook/Instagram and Threads).
No visual change. This is the "globally enabled" state.

---

**Given** `NEXT_PUBLIC_META_PUBLISHING_ENABLED=false`,
**And** the user has self-unlocked (localStorage `meta_beta === "1"`) OR already has at least one
Meta platform connected (instagram, facebook_page, or threads),
**When** the Connections page renders the Meta section,
**Then** the section shows the connect buttons (same as globally enabled state) PLUS a small
`"Beta"` pill badge next to the "Meta Platforms" / "Threads" section label.

The badge must be:
- `text-[10px] font-medium uppercase tracking-[0.06em] px-1.5 py-0.5`
- `bg-[#FFF1B8] text-[#111111] border border-[#E5E5E5]`
- Inline, positioned right of the label text (not absolute-positioned)

---

**Given** `NEXT_PUBLIC_META_PUBLISHING_ENABLED=false`,
**And** the user has NOT self-unlocked (no localStorage flag) AND has NO Meta platforms connected,
**When** the Connections page renders the Meta section,
**Then** the section shows the locked state (described in AC 2).

---

### AC 2: Locked state UI — beta gate with two CTAs

The locked state replaces the current hard-disabled button and tooltip. It must render:

**Left column (labels, unchanged from current):**
- Platform icons (Instagram, Facebook Page when not hasFBIG; Threads always)
- Label: "Meta Platforms" or "Threads" (same existing logic)
- Sublabel: "Instagram, Facebook Page, and Threads" or "Connect your Threads account"

**Right column (replaces the disabled button):**

Primary CTA — "I'm a beta tester" button:
```
border border-[#111111] text-[#111111] text-xs font-medium
px-4 min-h-[44px] rounded-none
hover:bg-[#111111] hover:text-white transition-colors
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2
```

Secondary CTA — "Request early access" link:
```
text-xs text-[#555555] underline underline-offset-2 hover:text-[#111111] transition-colors
```
Opens: `mailto:support@personnapress.com?subject=Beta%20Access%20Request%20-%20PersonnaPress`

Below the two CTAs, one line of copy:
```
<p class="text-xs text-[#555555] mt-2">
  Currently in beta. Available to invited testers only.
</p>
```

The old `<div className="relative group">` disabled-button block and its tooltip div must be removed.

---

### AC 3: "I'm a beta tester" unlock behavior

**When** the user clicks "I'm a beta tester",
**Then**:
1. `localStorage.setItem("meta_beta", "1")` is called
2. The component local state (`metaBetaUnlocked`) is set to `true`
3. A success toast fires: `addToast("Meta platforms unlocked.", "success")`
4. The section immediately re-renders into the "beta unlocked" state (AC 1 second block)
   showing connect buttons + "Beta" badge — no page reload required

---

### AC 4: Unlock persistence on localStorage clear (connected users)

**Given** a user has at least one Meta platform already connected,
**When** their localStorage is cleared (new browser, incognito, manual clear),
**Then** the section still renders connect buttons for remaining unconnected platforms
because `connectedItems.some(c => META_PLATFORMS.has(c.platform) && c.connected)` evaluates `true`.

The "already connected" check is self-healing — it does not rely on localStorage.

---

### AC 5: `isBetaUnlocked` logic encapsulation

The effective unlock check must be computed as a single derived boolean in `PlatformConnectionsClient`
and passed into `MetaPlatformsSection`. The formula:

```tsx
const [metaBetaUnlocked, setMetaBetaUnlocked] = useState<boolean>(() => {
  if (typeof window === "undefined") return false;
  return localStorage.getItem("meta_beta") === "1";
});

const metaEffectivelyEnabled =
  META_PUBLISHING_ENABLED ||
  metaBetaUnlocked ||
  connectedItems.some((c) => META_PLATFORMS.has(c.platform) && c.connected);
```

`MetaPlatformsSection` receives:
- `enabled: boolean` — the `metaEffectivelyEnabled` value
- `showBetaBadge: boolean` — `!META_PUBLISHING_ENABLED && metaEffectivelyEnabled`
- `onUnlock: () => void` — sets localStorage + updates `metaBetaUnlocked`
- existing `clientId`, `connectedItems` props (unchanged)

`MetaPlatformsSection` interface becomes:
```tsx
interface MetaPlatformsSectionProps {
  clientId: string;
  enabled: boolean;
  showBetaBadge: boolean;
  onUnlock: () => void;
  connectedItems: Array<{ platform: string; connected: boolean }>;
}
```

---

### AC 6: `/account/support` page — static server component

A new route at `frontend/app/(app)/account/support/page.tsx`.

Page metadata:
```tsx
export const metadata: Metadata = {
  title: "Help & Support | PersonnaPress",
  robots: { index: false },
};
```

Page structure (Paper Style RSC, matches `/account/page.tsx` layout):

```
<h1 class="font-display text-3xl text-ink">Help & Support</h1>

<hr class="border-[#E5E5E5] my-6" />

<section>
  <p class="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-2">
    Contact
  </p>
  <a href="mailto:support@personnapress.com"
     class="font-body text-sm text-ink underline underline-offset-2
            hover:text-graphite transition-colors">
    support@personnapress.com
  </a>
  <p class="font-body text-xs text-graphite mt-1">
    We typically respond within 24 hours on business days.
  </p>
</section>

<hr class="border-[#E5E5E5] my-6" />

<section>
  <p class="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-3">
    Quick requests
  </p>
  <p class="font-body text-sm text-graphite mb-4">
    Tap to open a pre-filled email for common requests.
  </p>
  <div class="space-y-2">
    [mailto buttons — see AC 7]
  </div>
</section>
```

---

### AC 7: Support page mailto quick-action buttons

Four `<a>` elements styled as secondary buttons (matching the existing `Button variant="secondary"` style:
`border border-[#E5E5E5] text-[#111111] bg-white hover:bg-[#F9F9F6] transition-colors`).

Each must be `min-h-[44px]` and `w-full` for touch targets.

| Label | mailto subject |
|---|---|
| Request Beta Access | `Beta%20Access%20Request%20-%20PersonnaPress` |
| Report a Bug | `Bug%20Report%20-%20PersonnaPress` |
| Feature Request | `Feature%20Request%20-%20PersonnaPress` |
| Billing Question | `Billing%20Question%20-%20PersonnaPress` |

All link to `mailto:support@personnapress.com?subject=<encoded-subject>`.

Each button renders the label text left-aligned with a `Mail` icon (`size-4 shrink-0`) from
`lucide-react` on the left, and an `ArrowUpRight` icon (`size-3.5 shrink-0 text-[#555555]`) on
the right:

```tsx
<a
  href="mailto:support@personnapress.com?subject=..."
  className="flex items-center gap-3 w-full px-4 min-h-[44px]
             border border-[#E5E5E5] bg-white text-[#111111] text-sm
             hover:bg-[#F9F9F6] transition-colors
             focus-visible:outline-none focus-visible:ring-2
             focus-visible:ring-[#111111] focus-visible:ring-offset-2"
>
  <Mail className="size-4 shrink-0 text-[#555555]" aria-hidden="true" />
  <span className="flex-1">Request Beta Access</span>
  <ArrowUpRight className="size-3.5 shrink-0 text-[#555555]" aria-hidden="true" />
</a>
```

---

### AC 8: Sidebar — "Help" nav item

In `frontend/components/layout/sidebar.tsx`, the footer `<div>` currently contains only the Account
nav item. Add `HelpCircle` NavItem above it, inside the same bordered footer div:

```tsx
import { HelpCircle } from "lucide-react";

// Footer div:
<div className="border-t border-[#E5E5E5] shrink-0">
  <NavItem href="/account/support" label="Help" icon={HelpCircle} />
  <NavItem {...ACCOUNT_NAV_ITEM} />
</div>
```

The `HelpCircle` import must come from `lucide-react` (already a project dependency).

---

### AC 9: Mobile drawer — "Help" nav item

In `frontend/components/layout/MobileDrawer.tsx`, mirror the same change:

```tsx
import { HelpCircle, Newspaper, Plug, X } from "lucide-react";

// Footer div:
<div className="border-t border-[#E5E5E5] shrink-0">
  <NavItem href="/account/support" label="Help" icon={HelpCircle} onClick={close} forceLabel />
  <NavItem {...ACCOUNT_NAV_ITEM} onClick={close} forceLabel />
</div>
```

---

### AC 10: Account page — support navigation link

In `frontend/app/(app)/account/AccountClient.tsx`, after the Log out `<Button>`, add:

```tsx
<hr className="border-[#E5E5E5] my-6" />

<Link
  href="/account/support"
  className="font-body text-sm text-graphite underline underline-offset-2
             hover:text-ink transition-colors"
>
  Help &amp; Support
</Link>
```

`Link` must be imported from `next/link`.

---

## Files to Create / Modify

| Operation | Path |
|---|---|
| CREATE | `frontend/app/(app)/account/support/page.tsx` |
| MODIFY | `frontend/components/publishing/PlatformConnectionsClient.tsx` |
| MODIFY | `frontend/app/(app)/account/AccountClient.tsx` |
| MODIFY | `frontend/components/layout/sidebar.tsx` |
| MODIFY | `frontend/components/layout/MobileDrawer.tsx` |

No backend changes. No DB migration. No new env vars.

---

## Dev Notes

### No Framer Motion
All state transitions in `MetaPlatformsSection` are CSS `transition-colors` / instant re-renders.
The beta badge appearance on unlock is immediate (no animation needed). Do not reach for
Framer Motion here.

### localStorage SSR Safety
`useState(() => typeof window === "undefined" ? false : localStorage.getItem("meta_beta") === "1")`
is the correct pattern. `PlatformConnectionsClient` is already `'use client'` so there is no
server render, but the lazy initializer guard is still the defensive best practice.

### META_PLATFORMS Set
`META_PLATFORMS` is already defined at the top of `PlatformConnectionsClient.tsx`:
```ts
const META_PLATFORMS = new Set(["instagram", "facebook_page", "threads"]);
```
Use it directly in the `metaEffectivelyEnabled` check — do not redefine it.

### useUIStore toast
The existing toast system is `useUIStore((s) => s.addToast)`. Call
`addToast("Meta platforms unlocked.", "success")` inside `onUnlock` in `PlatformConnectionsClient`
after setting the localStorage flag and updating state.

### Support page is a Server Component
`/account/support/page.tsx` has no interactivity. It must NOT have `"use client"`. All mailto links
are plain `<a>` elements. Import `Mail` and `ArrowUpRight` from `lucide-react` directly — both are
safe to use in RSCs.

### No em-dashes anywhere
Use ` - ` (space-hyphen-space) in mailto subject strings and all copy. Never `—` or `&mdash;`.

### NavItem active state
`NavItem` marks itself active when `pathname === href || pathname.startsWith(href + "/")`.
`href="/account/support"` will be active on the support page AND will keep `/account` active too
(since it `startsWith("/account")`). This is acceptable — both Help and Account in the sidebar will
highlight when on the support page. If this creates a visual double-active concern, note it in dev
notes but do not over-engineer a fix.

### Existing locked state removal
The current locked state in `MetaPlatformsSection` is:
```tsx
<div className="relative group">
  <button disabled ...>
    <Lock ... /> Connect Meta Platforms
  </button>
  <div id="meta-locked-tooltip" role="tooltip" ...>
    Meta Business API approval in progress. Available soon.
  </div>
</div>
```
This entire block must be replaced by AC 2. The `Lock` import may become unused — remove it if so.

---

## Out of Scope

- Backend beta-tester list or `is_beta_tester` field — not needed for this story
- Any gate on the publishing/approval panel — if Meta platforms are connected, publishing proceeds
  as normal regardless of `META_PUBLISHING_ENABLED`
- Settings page changes — the `/settings` placeholder is left untouched
- Any form-based support submission — mailto only, no API
- Response time guarantees or SLA — the "24 hours" copy is informational only

---

## Dev Agent Record

### Implementation Plan

Implemented all 10 ACs in a single pass with no backend changes:
- Added `metaBetaUnlocked` lazy-initialized state and `metaEffectivelyEnabled` derived bool to `PlatformConnectionsClient`
- `handleMetaUnlock` sets localStorage, flips state, fires success toast
- `MetaPlatformsSection` interface extended with `showBetaBadge`, `onUnlock` props
- Locked state replaced entirely: "I'm a beta tester" button + "Request early access" mailto link + copy line
- Beta pill badge rendered inline when `showBetaBadge=true`
- Old `<div className="relative group">` disabled-button+tooltip block removed; `Lock` import removed
- Created `/account/support/page.tsx` as a static RSC (no `"use client"`) with 4 mailto quick-action buttons using `Mail` + `ArrowUpRight` icons
- `HelpCircle` NavItem added above `ACCOUNT_NAV_ITEM` in both `sidebar.tsx` and `MobileDrawer.tsx`
- `Link` from `next/link` added to `AccountClient.tsx` with support link after Log out button

### Completion Notes

- TypeScript: 0 new errors (3 pre-existing errors in `BlogEditor.test.tsx` unrelated to this story)
- ESLint: 0 warnings across all 5 modified/created files
- Next.js build: clean — `/account/support` appears as `○` (static prerender) as expected

---

## File List

- `frontend/app/(app)/account/support/page.tsx` (CREATED)
- `frontend/components/publishing/PlatformConnectionsClient.tsx` (MODIFIED)
- `frontend/app/(app)/account/AccountClient.tsx` (MODIFIED)
- `frontend/components/layout/sidebar.tsx` (MODIFIED)
- `frontend/components/layout/MobileDrawer.tsx` (MODIFIED)

---

## Change Log

- 2026-08-13: Story 21.10 implemented — Meta beta gate (honor-system localStorage unlock, Beta pill badge, locked state with two CTAs) + `/account/support` page + Help nav item in sidebar/MobileDrawer + support link in AccountClient
