---
baseline_commit: 3a6310c
---

# Story 21.7: Meta Social Content Visibility

Status: done

## Story

As a PersonnaPress user with Meta platforms connected,
I want to see which Meta platforms will reuse my X and LinkedIn post content during editing,
and I want the Instagram destination chip to clearly show why it cannot be selected when no image exists,
so that I understand exactly what will be published where before I click Publish.

## Context & Motivation

Epic 21 (Meta Platform Publishing) intentionally reuses the two existing social content fields
for Meta platform publishing:

- `x_post` → **also published to Threads** (both ≤ 500 chars)
- `linkedin_post` → **also used as Instagram caption** (truncated to 2200 chars) **and Facebook Page post**

This content reuse is invisible to the user. The social editors show only "X (TWITTER)" and
"LINKEDIN" section labels. Users with Meta platforms connected have no idea their LinkedIn post
becomes their Instagram caption and Facebook Page message, or that their X post becomes their
Threads post. This causes confusion: "Why didn't Instagram post anything different?"

A second UX gap: the Instagram destination chip is already disabled when `campaign.image_url`
is `null` (social-only mode, skip-image toggle), but the chip has no tooltip explaining why.
Users see a grayed-out chip with no explanation until they scroll down to the note text.

This story adds two pure-frontend UX fixes. **No backend changes. No DB migration. No new API
endpoints.**

---

## Acceptance Criteria

### AC 1: Platform reuse badges in social post editor labels

**Given** a campaign is in `pending_approval` state and the user has Meta platforms connected,
**When** the `SocialPostEditors` component renders,
**Then** each section label row displays a right-aligned inline badge group showing which
connected Meta platforms consume that field:

**X (Twitter) label row** — when Threads is connected:
```
X (TWITTER)                          [threads-icon] Threads
```
Badge: `text-[10px] font-mono text-graphite`, Threads `PlatformIcon` at `size-3` mono color,
space between icon and text `gap-0.5`, row uses `flex items-center justify-between`.

**LinkedIn label row** — when Instagram and/or Facebook Page are connected:
```
LINKEDIN             [ig-icon] Instagram  ·  [fb-icon] Facebook
```
Each platform shown as `[icon] [name]` with `gap-0.5`. Multiple platforms separated by
`·` (`<span aria-hidden="true" className="text-border">·</span>`).
Outer wrapper: `flex items-center gap-1.5`.

**When none of those platforms are connected** (or `metaContext` omitted), no badge renders —
the label row is unchanged from its current appearance.

**Accessibility:** The badge `<span>` carries `aria-label="Also posts to Threads"` (or
`"Also used as Instagram caption"` / `"Also used as Facebook Page post"`) so screen readers
announce the reuse relationship.

---

### AC 2: `metaContext` prop on `SocialPostEditors`

**Given** the `SocialPostEditors` component,
**When** it receives the new optional `metaContext` prop,
**Then** the prop is typed as:

```typescript
interface MetaContext {
  threads?: boolean;
  instagram?: boolean;
  facebook_page?: boolean;
}
```

Added to `SocialPostEditorsProps`. The existing `SocialPostEditorsHandle` interface is
**unchanged** — `getCurrentValues()` still returns `{ x_post: string; linkedin_post: string }`.

---

### AC 3: `ApprovalGateClient` derives and passes `metaContext`

**Given** `ApprovalGateClient.tsx` renders `SocialPostEditors`,
**When** the component mounts,
**Then** it queries `publishingApi.listConnections(campaign.client_id)` using TanStack Query
with `queryKey: ["platform-connections", campaign.client_id]` and `staleTime: 30_000`.

This is the **same query key** that `ApprovalPanel` already fires — the result comes from
cache, not a new network request.

The derived `metaContext`:
```typescript
const connectedItems = connections?.items ?? [];
const metaContext: MetaContext = {
  threads:       connectedItems.some(c => c.platform === "threads"       && c.connected),
  instagram:     connectedItems.some(c => c.platform === "instagram"     && c.connected),
  facebook_page: connectedItems.some(c => c.platform === "facebook_page" && c.connected),
};
```

`metaContext` is passed as a prop to `SocialPostEditors`. When `connections` is still loading
(`undefined`), `metaContext` defaults to all `false` — no badges render during the loading
state (graceful degradation, no flash).

---

### AC 4: Disabled `DestinationChip` gets a native tooltip

**Given** the `DestinationChip` component in `approval-panel.tsx`,
**When** `disabled` is `true` and a `disabledReason` string is provided,
**Then** the `<button>` element receives `title={disabledReason}` (native browser tooltip
on hover) and `aria-label={\`${label} -- ${disabledReason}\`}` for screen reader clarity.

New prop on `DestinationChip`:
```typescript
disabledReason?: string;
```

The `disabled` prop logic on the chip row is **unchanged** — existing conditions remain:
- Instagram: `p === "instagram" && !campaign.image_url`
- Threads: `p === "threads" && !(campaign.x_post || "").trim()`
- Facebook Page: `p === "facebook_page" && !(campaign.linkedin_post || "").trim()`

`disabledReason` values to pass at each call site:
```typescript
p === "instagram"    && !campaign.image_url                         => "Requires a featured image"
p === "threads"      && !(campaign.x_post || "").trim()             => "Requires an X post"
p === "facebook_page"&& !(campaign.linkedin_post || "").trim()      => "Requires a LinkedIn post"
```

**Both** `DestinationChip` call sites in `approval-panel.tsx` (approved state ~line 722 and
published state ~line 1139) must receive the `disabledReason` prop.

---

### AC 5: Existing approval-panel notes remain (no removal)

The existing text notes below the chip row are kept **as-is**:
- "Instagram requires a featured image. Generate or upload one first." (line ~741)
- "Facebook Page requires a LinkedIn post to be generated." (line ~751)
- "Threads requires an X post to be generated." (line ~756)
- "Also posts to Threads" (line ~760, shown when both X + Threads selected)

These notes serve a different role from the AC 4 tooltip — they are always visible when the
condition is active, not just on hover. Do not remove them.

---

### AC 6: Paper Style compliance

**Given** the new badge elements,
**When** they render,
**Then**:
- `rounded-none` on any wrapper element that might default to rounded
- No emojis anywhere
- Only Lucide icons and `PlatformIcon` (which wraps Lucide + custom SVG)
- No Framer Motion — CSS transitions only (`transition-colors duration-150` on the label row
  if hover treatment is needed, but static is fine)
- All new text: `font-mono text-graphite` or lighter — never heavier than the section label

---

## Dev Notes

### Files to modify (frontend only)

| File | Change |
|------|--------|
| `frontend/components/campaigns/SocialPostEditors.tsx` | Add `metaContext` prop + badge render |
| `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` | Add connections query + derive + pass `metaContext` |
| `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` | Add `disabledReason` to `DestinationChip` + pass at both call sites |

No other files change.

---

### SocialPostEditors.tsx — precise change

Current label (X section):
```tsx
<label
  htmlFor="x-post"
  className="block text-xs font-mono uppercase tracking-widest text-graphite mb-2"
>
  X (Twitter)
</label>
```

Replace with:
```tsx
<div className="flex items-center justify-between mb-2">
  <label
    htmlFor="x-post"
    className="text-xs font-mono uppercase tracking-widest text-graphite"
  >
    X (Twitter)
  </label>
  {metaContext?.threads && (
    <span
      className="flex items-center gap-0.5 text-[10px] font-mono text-graphite"
      aria-label="Also posts to Threads"
    >
      <PlatformIcon platform="threads" className="size-3" color="mono" aria-hidden="true" />
      Threads
    </span>
  )}
</div>
```

Current label (LinkedIn section):
```tsx
<label
  htmlFor="linkedin-post"
  className="block text-xs font-mono uppercase tracking-widest text-graphite mb-2"
>
  LinkedIn
</label>
```

Replace with:
```tsx
<div className="flex items-center justify-between mb-2">
  <label
    htmlFor="linkedin-post"
    className="text-xs font-mono uppercase tracking-widest text-graphite"
  >
    LinkedIn
  </label>
  {(metaContext?.instagram || metaContext?.facebook_page) && (
    <span className="flex items-center gap-1.5 text-[10px] font-mono text-graphite">
      {metaContext.instagram && (
        <span
          className="flex items-center gap-0.5"
          aria-label="Also used as Instagram caption"
        >
          <PlatformIcon platform="instagram" className="size-3" color="mono" aria-hidden="true" />
          Instagram
        </span>
      )}
      {metaContext.instagram && metaContext.facebook_page && (
        <span aria-hidden="true" className="text-border">·</span>
      )}
      {metaContext.facebook_page && (
        <span
          className="flex items-center gap-0.5"
          aria-label="Also used as Facebook Page post"
        >
          <PlatformIcon platform="facebook_page" className="size-3" color="mono" aria-hidden="true" />
          Facebook
        </span>
      )}
    </span>
  )}
</div>
```

Add `PlatformIcon` import at the top of `SocialPostEditors.tsx`:
```typescript
import { PlatformIcon } from "@/components/ui/PlatformIcon";
```

---

### ApprovalGateClient.tsx — precise additions

Add to imports:
```typescript
import { useQuery } from "@tanstack/react-query";
import { publishingApi } from "@/lib/api";
```

Add inside `ApprovalGateClient` function body (after existing `useRef` lines):
```typescript
const { data: connections } = useQuery({
  queryKey: ["platform-connections", campaign.client_id],
  queryFn: () => publishingApi.listConnections(campaign.client_id),
  staleTime: 30_000,
});
const connectedItems = connections?.items ?? [];
const metaContext = {
  threads:       connectedItems.some(c => c.platform === "threads"       && c.connected),
  instagram:     connectedItems.some(c => c.platform === "instagram"     && c.connected),
  facebook_page: connectedItems.some(c => c.platform === "facebook_page" && c.connected),
};
```

Update the `SocialPostEditors` call (line ~197):
```tsx
<SocialPostEditors
  ref={socialEditorsRef}
  campaignId={campaign.id}
  initialXPost={campaign.x_post ?? null}
  initialLinkedInPost={campaign.linkedin_post ?? null}
  readOnly={!isPending}
  showXSection={hideBlogSection ? !!campaign.x_post : true}
  showLinkedInSection={hideBlogSection ? !!campaign.linkedin_post : true}
  metaContext={metaContext}
/>
```

---

### approval-panel.tsx — DestinationChip change

Extend props interface:
```typescript
function DestinationChip({
  platform,
  selected,
  onToggle,
  disabled,
  disabledReason,   // NEW
  label: labelOverride,
}: {
  platform: string;
  selected: boolean;
  onToggle: () => void;
  disabled?: boolean;
  disabledReason?: string;  // NEW
  label?: string;
}) {
  const label = labelOverride ?? PLATFORM_LABEL_MAP[platform] ?? platform;
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      aria-pressed={selected}
      title={disabled && disabledReason ? disabledReason : undefined}              // NEW
      aria-label={disabled && disabledReason ? `${label} -- ${disabledReason}` : undefined}  // NEW
      className={cn(
        // ...unchanged...
      )}
    >
```

Call site update (apply to BOTH the approved-state chip row ~line 722
and the published-state chip row ~line 1139 — they are structurally identical):
```tsx
<DestinationChip
  key={p}
  platform={p}
  selected={selectedPlatforms.has(p)}
  onToggle={() => /* unchanged */ }
  disabled={
    isPublishing || isGitHubPublishing ||
    (p === "instagram"     && !campaign.image_url) ||
    (p === "threads"       && !(campaign.x_post || "").trim()) ||
    (p === "facebook_page" && !(campaign.linkedin_post || "").trim())
  }
  disabledReason={
    p === "instagram"     && !campaign.image_url
      ? "Requires a featured image"
      : p === "threads" && !(campaign.x_post || "").trim()
      ? "Requires an X post"
      : p === "facebook_page" && !(campaign.linkedin_post || "").trim()
      ? "Requires a LinkedIn post"
      : undefined
  }
  label={platformLabels[p]}
/>
```

---

### No tests needed

This story has zero business logic changes — it adds display-only props and a badge render.
The connections query is already tested via `ApprovalPanel`. Skip unit tests for this story.

---

## Visual Reference (Paper Style)

```
┌─────────────────────────────────────────────────────────────┐
│  X (TWITTER)                          [◎] Threads           │
│  ─────────────────────────────────────────────────────────  │
│  Your X post here...                                        │
│  ─────────────────────────────────────────────────────────  │
│  142 / 280                                                  │
│                                                             │
│  LINKEDIN                  [◻] Instagram  ·  [f] Facebook   │
│  ─────────────────────────────────────────────────────────  │
│  Your LinkedIn post here...                                 │
│  ─────────────────────────────────────────────────────────  │
│  834 / 1300                                                 │
└─────────────────────────────────────────────────────────────┘

Destination chips (Instagram disabled, no image):
  [✓ X]  [✓ LinkedIn]  [Instagram ← grayed, title="Requires a featured image"]

Note below chips:
  "Instagram requires a featured image. Generate or upload one first."
```

Badges sit flush-right in the label row. Icon + name only — no wrapping box, no background,
no border. Exactly `text-[10px] font-mono text-graphite` so they read as metadata, not as
primary labels. The separator `·` uses `text-border` to fade further.

---

## Tasks / Subtasks

- [x] Task 1: Add `MetaContext` interface + `metaContext` prop to `SocialPostEditors`, replace X and LinkedIn label blocks with `flex justify-between` rows that conditionally render platform reuse badges.
- [x] Task 2: In `ApprovalGateClient`, import `useQuery` + `publishingApi`, add connections query with `queryKey: ["platform-connections", campaign.client_id]` and `staleTime: 30_000`, derive `metaContext`, pass it to `SocialPostEditors`.
- [x] Task 3: Add `disabledReason?: string` prop to `DestinationChip`, wire `title` and `aria-label` attributes, pass `disabledReason` at both call sites (~line 722 and ~line 1139) in `approval-panel.tsx`.

### Review Findings

- [x] [Review][Patch] Badges render in non-pending (readOnly) states — AC 1 scopes to `pending_approval` [ApprovalGateClient.tsx:219]
- [x] [Review][Defer] No `gcTime` on connections query — pre-existing pattern across other queries in file [ApprovalGateClient.tsx:65]
- [x] [Review][Defer] `disabledReason` ternary duplicated across two call sites — deferred, intentional per spec; pre-existing file has symmetric chip rows [approval-panel.tsx:738,1164]
- [x] [Review][Defer] `MetaContext` interface not exported — deferred, pre-existing; spec doesn't require export; TypeScript infers correctly at call site [SocialPostEditors.tsx:15]
- [x] [Review][Defer] `isPublishing`/`isGitHubPublishing` disables chips with no tooltip — deferred, pre-existing behavior not introduced by this story [approval-panel.tsx:737]
- [x] [Review][Defer] Future platforms added to chip list will have no `disabledReason` — deferred, pre-existing extensibility gap [approval-panel.tsx:738]

---

## File List

- `frontend/components/campaigns/SocialPostEditors.tsx`
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`

---

## Dev Agent Record

### Completion Notes

All three frontend-only changes implemented per spec:

1. **SocialPostEditors.tsx**: Added `MetaContext` interface and `metaContext` prop. X label row replaced with `flex items-center justify-between` div; conditionally shows Threads badge when `metaContext.threads`. LinkedIn label row replaced similarly; conditionally shows Instagram and/or Facebook Page badges with `·` separator, each with proper `aria-label`. `PlatformIcon` imported. No logic changes to textarea/save behavior.

2. **ApprovalGateClient.tsx**: Added `useQuery` from TanStack Query and `publishingApi` import. Connections query fires with the same `queryKey: ["platform-connections", campaign.client_id]` used by `ApprovalPanel` — result hits cache, no extra network request. `metaContext` defaults all-false while loading. Passed as prop to `SocialPostEditors`.

3. **approval-panel.tsx**: `DestinationChip` extended with `disabledReason?: string`. Button receives `title={disabled && disabledReason ? disabledReason : undefined}` and `aria-label` override when disabled. Both chip map call sites (approved-state ~line 722 and published-state ~line 1139) updated identically with `disabledReason` ternary. Existing note text below chip rows is untouched (AC 5).

TypeScript check: zero new errors (pre-existing BlogEditor test errors unchanged). ESLint: zero new warnings/errors in the three modified files.

### Change Log

- 2026-08-01: Implemented story 21.7 — Meta Social Content Visibility (pure frontend UX, no backend/DB/API changes).
