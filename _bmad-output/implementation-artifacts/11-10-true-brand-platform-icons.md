---
baseline_commit: c4f13aa747a778043cbce625d8ab9bdb19319e68
---

# Story 11.10: True Brand Platform Icons with Two-Color Mode

Status: done

## Story

As a PersonnaPress user,
I want every platform (Instagram, Facebook, LinkedIn, WordPress, Threads, X, Webflow, GitHub) to show its real brand icon throughout the app,
so that the interface feels alive, trustworthy, and immediately recognizable rather than using generic substitutes.

## Background

The codebase currently has **four separate, all-wrong icon systems** for social platforms:

1. **`PlatformIcon.tsx`** — the central component. Uses `<Camera>` for Instagram, `<BookOpen>` for Facebook, `<Share2>` for X, `<Globe>` for WordPress, `<MessageCircle>` for Threads, `<LayoutGrid>` for Webflow, `<GitBranch>` for GitHub — and **LinkedIn is missing entirely** (falls through to `<Link2>` default).
2. **`approval-panel.tsx` `PLATFORM_ICON_MAP`** (lines 111–121) — its own lookup with equally wrong icons, used in `DestinationChip`.
3. **`PostCard.tsx` `getPlatformInfo()`** (lines 10–23) — its own inline icon logic: `AtSign` for LinkedIn, `Share2` for X.
4. **`RetryPanel.tsx`** — shows platform names with CSS `capitalize` producing "Facebook_page", "Wordpress-com" (broken).

All four must be replaced. The fix is to make `PlatformIcon.tsx` the **single source of truth** and delete the other three ad-hoc systems.

## Acceptance Criteria

1. **Given** `PlatformIcon` is rendered for any supported platform, **When** it renders, **Then** it shows the true brand SVG path (the exact paths provided in Dev Notes) — not any Lucide substitute. Supported platforms: `instagram`, `facebook_page`, `linkedin`, `x`, `wordpress`, `wordpress-com`, `threads`, `webflow`, `github_pages`.

2. **Given** `PlatformIcon` is called with `color="mono"` (the default), **When** it renders, **Then** the SVG uses `fill="currentColor"` so it inherits whatever Tailwind `text-*` class the parent applies.

3. **Given** `PlatformIcon` is called with `color="brand"`, **When** it renders, **Then** the SVG `fill` is set to the official platform brand hex via inline style (see brand hex table in Dev Notes), bypassing `currentColor`.

4. **Given** `PlatformConnectionCard` renders a platform connection, **When** `connection.connected === true`, **Then** `PlatformIcon` is rendered with `color="brand"` at `size-5`. **When** `connection.connected === false`, **Then** `color="mono"` is used.

5. **Given** `DestinationChip` in `approval-panel.tsx`, **When** the chip is selected (`selected=true`), **Then** `PlatformIcon` is rendered with `color="brand"`. **When** unselected, **Then** `color="mono"` with inherited `text-graphite`.

6. **Given** `PostCard.tsx` renders a platform chip, **When** it renders, **Then** it uses `<PlatformIcon platform={...} className="size-3.5 text-graphite shrink-0" />` directly — the `getPlatformInfo()` function no longer returns an `icon` field; icons come from `PlatformIcon`.

7. **Given** `RetryPanel.tsx` lists platforms in a publish failure, **When** it renders a platform row, **Then** the platform name is shown using the same label map as `PlatformConnectionCard` (e.g. `"facebook_page" → "Facebook Page"`, `"wordpress-com" → "WordPress.com"`) — the raw `capitalize` CSS is removed. A `<PlatformIcon>` at `size-3.5` appears left of the platform name.

8. **Given** `MetaPlatformsSection` in `PlatformConnectionsClient.tsx`, **When** it renders the grouped Meta connect/locked block, **Then** three icons appear inline in the section header: Instagram, Facebook, Threads — each `size-4 color="mono"` in `text-graphite`.

9. **Given** `PublicFooter.tsx`, **When** it renders, **Then** a new social follow row appears in the bottom bar with PersonnaPress's own platform links. Icons are `size-5 color="brand"`. Each link has `aria-label="PersonnaPress on [Platform]"`. On hover: `opacity-100 → opacity-70` via `transition-opacity duration-150`. Platforms to include: Facebook (`https://www.facebook.com/personnapress/`). Add X, LinkedIn, Instagram as `href="#"` placeholders until real URLs are known.

10. **Given** the landing page "Day-1 Integrations" platform pills section (`app/page.tsx` `PLATFORMS` array), **When** it renders, **Then** each pill is updated to `inline-flex items-center gap-2` and includes a `<PlatformIcon platform={...} className="size-4" color="mono" />` to the left of the text. Platforms: WordPress, Webflow, X (Twitter), LinkedIn. Mono mode is used so the icon automatically flips to `text-paper` on `hover:bg-ink hover:text-paper` — no extra logic needed.

11. **Given** the calendar cell (`ContentCalendar.tsx` line 122), **When** it renders platform icons, **Then** it continues to use `PlatformIcon` at `size-2.5 color="mono"` — no brand color at this size (too small to be meaningful).

12. **Given** all existing usages of `PlatformIcon` across the codebase, **When** no `color` prop is passed, **Then** behavior is identical to today's mono behavior (default is `"mono"`) — no regressions in calendar, campaign list, or connections list.

## Tasks / Subtasks

- [x] Task 1: Rewrite `PlatformIcon.tsx` as single source of truth (AC: 1, 2, 3, 12)
  - [x] Replace the file entirely with the new implementation from Dev Notes
  - [x] Embed all 8 SVG paths inline (no imports, no external files)
  - [x] Add `color?: "mono" | "brand"` prop defaulting to `"mono"`
  - [x] Add `linkedin` case (currently missing, falls to default)
  - [x] Add `wordpress-com` as alias for `wordpress` case
  - [x] Verify `className` still controls size (consumer passes `size-2.5`, `size-3.5`, `size-5`, etc.)

- [x] Task 2: Fix `PlatformConnectionCard.tsx` to use brand color when connected (AC: 4)
  - [x] In `PlatformConnectionCard`, change the `<PlatformIcon>` at line 139 to pass `color={connection.connected ? "brand" : "mono"}`
  - [x] No other changes to this file

- [x] Task 3: Fix `approval-panel.tsx` — delete `PLATFORM_ICON_MAP`, update `DestinationChip` (AC: 5)
  - [x] Delete `PLATFORM_ICON_MAP` constant (lines 111–121) and its `LucideIcon` type alias (line 109)
  - [x] Remove Lucide imports that are no longer needed: `Globe`, `Layout`, `AtSign`, `Share2`, `Camera`, `Users`, `MessageSquare` (keep `GitBranch`, `Database`, `Loader2`, `CheckCircle2`, `XCircle`, `RefreshCw`, `Check`)
  - [x] Add `import { PlatformIcon } from "@/components/ui/PlatformIcon"`
  - [x] In `DestinationChip`: replace `const Icon = PLATFORM_ICON_MAP[platform] ?? Globe` + `<Icon className="size-3.5" .../>` with `<PlatformIcon platform={platform} className="size-3.5" color={selected ? "brand" : "mono"} aria-hidden="true" />`
  - [x] `headless` platform has no brand SVG — `PlatformIcon` will return the `<Link2>` fallback for it; that's acceptable

- [x] Task 4: Fix `PostCard.tsx` — remove icon from `getPlatformInfo()`, use `PlatformIcon` (AC: 6)
  - [x] Remove `icon: React.ElementType` field from the return type of `getPlatformInfo()`
  - [x] Remove `icon: BookOpen`, `icon: AtSign`, `icon: Share2` from the three return objects
  - [x] Remove unused Lucide imports: `AtSign`, `BookOpen`, `Share2` (keep `ExternalLink`, `UploadCloud`)
  - [x] Add `import { PlatformIcon } from "@/components/ui/PlatformIcon"`
  - [x] In `PostCard` JSX, changed to use `platformKey` from `getPlatformInfo()` result
  - [x] Replace icon rendering with `<PlatformIcon platform={platformKey} className="size-3.5 text-graphite shrink-0" color="mono" aria-hidden="true" />`

- [x] Task 5: Fix `RetryPanel.tsx` — fix label bug, add icons (AC: 7)
  - [x] Add the platform label map `PLATFORM_LABELS`
  - [x] Add `import { PlatformIcon } from "@/components/ui/PlatformIcon"`
  - [x] Replace raw `capitalize` platform name with `PLATFORM_LABELS[platform] ?? platform`
  - [x] Wrap icon + platform name in flex row for non-synthetic platforms

- [x] Task 6: Fix `MetaPlatformsSection` — add three Meta icons (AC: 8)
  - [x] In `PlatformConnectionsClient.tsx`, add `import { PlatformIcon } from "@/components/ui/PlatformIcon"`
  - [x] Add icon row above "Meta Platforms" label

- [x] Task 7: Add social follow links to `PublicFooter.tsx` (AC: 9)
  - [x] Add `import { PlatformIcon } from "@/components/ui/PlatformIcon"`
  - [x] Add social links nav between copyright and legal nav
  - [x] Added `flex-wrap` to bottom bar

- [x] Task 8: Update landing page platform pills (AC: 10)
  - [x] Convert `PLATFORMS` from `string[]` to `{label, platform}[]`
  - [x] Add `import { PlatformIcon } from "@/components/ui/PlatformIcon"`
  - [x] Update pill render with `inline-flex items-center gap-2` and `PlatformIcon`

## Dev Notes

### New `PlatformIcon.tsx` — Complete Implementation

The file must be completely replaced. Do NOT incrementally patch it. Here is the full implementation:

```tsx
const BRAND_COLORS: Record<string, string> = {
  instagram:    "#E1306C",
  facebook_page:"#1877F2",
  linkedin:     "#0A66C2",
  wordpress:    "#21759B",
  "wordpress-com":"#21759B",
  threads:      "#101010",
  x:            "#000000",
  webflow:      "#146EF5",
  github_pages: "#181717",
};

interface Props {
  platform: string;
  className?: string;
  color?: "mono" | "brand";
}

export function PlatformIcon({ platform, className = "size-3.5", color = "mono" }: Props) {
  const fill = color === "brand" ? (BRAND_COLORS[platform] ?? "currentColor") : "currentColor";
  const style = color === "brand" ? { fill: BRAND_COLORS[platform] ?? "currentColor" } : undefined;
  const shared = { className, "aria-hidden": true as const, style };

  // Instagram
  if (platform === "instagram") return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {...shared}>
      <path d="M10.202,2.098c-1.49,.07-2.507,.308-3.396,.657-.92,.359-1.7,.84-2.477,1.619-.776,.779-1.254,1.56-1.61,2.481-.345,.891-.578,1.909-.644,3.4-.066,1.49-.08,1.97-.073,5.771s.024,4.278,.096,5.772c.071,1.489,.308,2.506,.657,3.396,.359,.92,.84,1.7,1.619,2.477,.779,.776,1.559,1.253,2.483,1.61,.89,.344,1.909,.579,3.399,.644,1.49,.065,1.97,.08,5.771,.073,3.801-.007,4.279-.024,5.773-.095s2.505-.309,3.395-.657c.92-.36,1.701-.84,2.477-1.62s1.254-1.561,1.609-2.483c.345-.89,.579-1.909,.644-3.398,.065-1.494,.081-1.971,.073-5.773s-.024-4.278-.095-5.771-.308-2.507-.657-3.397c-.36-.92-.84-1.7-1.619-2.477s-1.561-1.254-2.483-1.609c-.891-.345-1.909-.58-3.399-.644s-1.97-.081-5.772-.074-4.278,.024-5.771,.096m.164,25.309c-1.365-.059-2.106-.286-2.6-.476-.654-.252-1.12-.557-1.612-1.044s-.795-.955-1.05-1.608c-.192-.494-.423-1.234-.487-2.599-.069-1.475-.084-1.918-.092-5.656s.006-4.18,.071-5.656c.058-1.364,.286-2.106,.476-2.6,.252-.655,.556-1.12,1.044-1.612s.955-.795,1.608-1.05c.493-.193,1.234-.422,2.598-.487,1.476-.07,1.919-.084,5.656-.092,3.737-.008,4.181,.006,5.658,.071,1.364,.059,2.106,.285,2.599,.476,.654,.252,1.12,.555,1.612,1.044s.795,.954,1.051,1.609c.193,.492,.422,1.232,.486,2.597,.07,1.476,.086,1.919,.093,5.656,.007,3.737-.006,4.181-.071,5.656-.06,1.365-.286,2.106-.476,2.601-.252,.654-.556,1.12-1.045,1.612s-.955,.795-1.608,1.05c-.493,.192-1.234,.422-2.597,.487-1.476,.069-1.919,.084-5.657,.092s-4.18-.007-5.656-.071M21.779,8.517c.002,.928,.755,1.679,1.683,1.677s1.679-.755,1.677-1.683c-.002-.928-.755-1.679-1.683-1.677,0,0,0,0,0,0-.928,.002-1.678,.755-1.677,1.683m-12.967,7.496c.008,3.97,3.232,7.182,7.202,7.174s7.183-3.232,7.176-7.202c-.008-3.97-3.233-7.183-7.203-7.175s-7.182,3.233-7.174,7.203m2.522-.005c-.005-2.577,2.08-4.671,4.658-4.676,2.577-.005,4.671,2.08,4.676,4.658,.005,2.577-2.08,4.671-4.658,4.676-2.577,.005-4.671-2.079-4.676-4.656h0" />
    </svg>
  );

  // Facebook
  if (platform === "facebook_page") return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {...shared}>
      <path d="M16,2c-7.732,0-14,6.268-14,14,0,6.566,4.52,12.075,10.618,13.588v-9.31h-2.887v-4.278h2.887v-1.843c0-4.765,2.156-6.974,6.835-6.974,.887,0,2.417,.174,3.043,.348v3.878c-.33-.035-.904-.052-1.617-.052-2.296,0-3.183,.87-3.183,3.13v1.513h4.573l-.786,4.278h-3.787v9.619c6.932-.837,12.304-6.74,12.304-13.897,0-7.732-6.268-14-14-14Z" />
    </svg>
  );

  // LinkedIn
  if (platform === "linkedin") return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {...shared}>
      <path d="M26.111,3H5.889c-1.595,0-2.889,1.293-2.889,2.889V26.111c0,1.595,1.293,2.889,2.889,2.889H26.111c1.595,0,2.889-1.293,2.889-2.889V5.889c0-1.595-1.293-2.889-2.889-2.889ZM10.861,25.389h-3.877V12.87h3.877v12.519Zm-1.957-14.158c-1.267,0-2.293-1.034-2.293-2.31s1.026-2.31,2.293-2.31,2.292,1.034,2.292,2.31-1.026,2.31-2.292,2.31Zm16.485,14.158h-3.858v-6.571c0-1.802-.685-2.809-2.111-2.809-1.551,0-2.362,1.048-2.362,2.809v6.571h-3.718V12.87h3.718v1.686s1.118-2.069,3.775-2.069,4.556,1.621,4.556,4.975v7.926Z" fillRule="evenodd" />
    </svg>
  );

  // WordPress (also handles wordpress-com)
  if (platform === "wordpress" || platform === "wordpress-com") return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {...shared}>
      <path d="M16,2c7.722,0,14,6.278,14,14s-6.278,14-14,14S2,23.722,2,16,8.278,2,16,2Zm.215,15.098l-3.769,10.985c2.536,.741,5.241,.665,7.732-.215l-.086-.172s-3.877-10.597-3.877-10.597ZM4.509,10.874c-2.769,6.205-.114,13.488,5.998,16.455L4.509,10.874Zm22.551-.915c.199,1.977-.101,3.973-.872,5.805l-3.855,11.114c5.895-3.426,7.987-10.925,4.717-16.908l.011-.011ZM16,3.411c-4.394,0-8.271,2.262-10.522,5.675l.818,.011c1.314,0,3.349-.151,3.349-.151,.678-.043,.754,.948,.086,1.034h-.097c-.205,.032-.754,.086-1.346,.108l4.577,13.645,2.757-8.26-1.96-5.385c-.678-.032-1.314-.108-1.314-.108-.678-.043-.603-1.077,.075-1.034,0,0,.883,.065,1.842,.108l.388,.022,1.077,.022h.183c1.314,0,3.177-.151,3.177-.151,.678-.043,.754,.948,.086,1.034h-.086c-.215,.032-.754,.086-1.357,.108l4.545,13.537,1.26-4.2c.646-1.626,.958-2.983,.958-4.06,0-1.562-.56-2.638-1.034-3.468-.646-1.045-1.238-1.917-1.238-2.951,0-1.163,.872-2.24,2.111-2.24l.162,.011c-2.317-2.13-5.35-3.31-8.497-3.306Z" />
    </svg>
  );

  // Threads
  if (platform === "threads") return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {...shared}>
      <path d="M22.7,14.977c-.121-.058-.243-.113-.367-.167-.216-3.982-2.392-6.262-6.046-6.285-.017,0-.033,0-.05,0-2.185,0-4.003,.933-5.122,2.63l2.009,1.378c.836-1.268,2.147-1.538,3.113-1.538,.011,0,.022,0,.033,0,1.203,.008,2.111,.357,2.698,1.04,.428,.497,.714,1.183,.855,2.049-1.067-.181-2.22-.237-3.453-.166-3.474,.2-5.707,2.226-5.557,5.041,.076,1.428,.788,2.656,2.003,3.459,1.028,.678,2.351,1.01,3.727,.935,1.817-.1,3.242-.793,4.236-2.06,.755-.963,1.233-2.21,1.444-3.781,.866,.523,1.507,1.21,1.862,2.037,.603,1.405,.638,3.714-1.246,5.596-1.651,1.649-3.635,2.363-6.634,2.385-3.326-.025-5.842-1.091-7.478-3.171-1.532-1.947-2.323-4.759-2.353-8.359,.03-3.599,.821-6.412,2.353-8.359,1.636-2.079,4.151-3.146,7.478-3.171,3.35,.025,5.91,1.097,7.608,3.186,.833,1.025,1.461,2.313,1.874,3.815l2.355-.628c-.502-1.849-1.291-3.443-2.365-4.764-2.177-2.679-5.361-4.051-9.464-4.08h-.016c-4.094,.028-7.243,1.406-9.358,4.095-1.882,2.393-2.853,5.722-2.886,9.895v.01s0,.01,0,.01c.033,4.173,1.004,7.503,2.886,9.895,2.115,2.689,5.264,4.067,9.358,4.095h.016c3.64-.025,6.206-.978,8.32-3.09,2.765-2.763,2.682-6.226,1.771-8.352-.654-1.525-1.901-2.763-3.605-3.581Zm-6.285,5.909c-1.522,.086-3.104-.598-3.182-2.061-.058-1.085,.772-2.296,3.276-2.441,.287-.017,.568-.025,.844-.025,.909,0,1.76,.088,2.533,.257-.288,3.602-1.98,4.187-3.471,4.269Z" />
    </svg>
  );

  // X (Twitter)
  if (platform === "x") return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {...shared}>
      <path d="M18.42,14.009L27.891,3h-2.244l-8.224,9.559L10.855,3H3.28l9.932,14.455L3.28,29h2.244l8.684-10.095,6.936,10.095h7.576l-10.301-14.991h0Zm-3.074,3.573l-1.006-1.439L6.333,4.69h3.447l6.462,9.243,1.006,1.439,8.4,12.015h-3.447l-6.854-9.804h0Z" />
    </svg>
  );

  // Webflow
  if (platform === "webflow") return (
    <svg role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" {...shared}>
      <path d="m24 4.515-7.658 14.97H9.149l3.205-6.204h-.144C9.566 16.713 5.621 18.973 0 19.485v-6.118s3.596-.213 5.71-2.435H0V4.515h6.417v5.278l.144-.001 2.622-5.277h4.854v5.244h.144l2.72-5.244H24Z" />
    </svg>
  );

  // GitHub Pages
  if (platform === "github_pages") return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" {...shared}>
      <path d="M16,2.345c7.735,0,14,6.265,14,14-.002,6.015-3.839,11.359-9.537,13.282-.7,.14-.963-.298-.963-.665,0-.473,.018-1.978,.018-3.85,0-1.312-.437-2.152-.945-2.59,3.115-.35,6.388-1.54,6.388-6.912,0-1.54-.543-2.783-1.435-3.762,.14-.35,.63-1.785-.14-3.71,0,0-1.173-.385-3.85,1.435-1.12-.315-2.31-.472-3.5-.472s-2.38,.157-3.5,.472c-2.677-1.802-3.85-1.435-3.85-1.435-.77,1.925-.28,3.36-.14,3.71-.892,.98-1.435,2.24-1.435,3.762,0,5.355,3.255,6.563,6.37,6.913-.403,.35-.77,.963-.893,1.872-.805,.368-2.818,.963-4.077-1.155-.263-.42-1.05-1.452-2.152-1.435-1.173,.018-.472,.665,.017,.927,.595,.332,1.277,1.575,1.435,1.978,.28,.787,1.19,2.293,4.707,1.645,0,1.173,.018,2.275,.018,2.607,0,.368-.263,.787-.963,.665-5.719-1.904-9.576-7.255-9.573-13.283,0-7.735,6.265-14,14-14Z" />
    </svg>
  );

  // Fallback
  import { Link2 } from "lucide-react";
  return <Link2 className={className} aria-hidden="true" />;
}
```

> **Implementation note on the fallback:** The `Link2` import inside the function body is invalid syntax. The actual implementation should have `Link2` imported at the top of the file from `"lucide-react"`, and the fallback `return <Link2 className={className} aria-hidden="true" />` at the bottom. The rest of the file keeps zero Lucide imports for the real platforms.

### Brand Hex Reference (for dev agent)

| Platform key | Brand hex |
|---|---|
| `instagram` | `#E1306C` |
| `facebook_page` | `#1877F2` |
| `linkedin` | `#0A66C2` |
| `wordpress` / `wordpress-com` | `#21759B` |
| `threads` | `#101010` |
| `x` | `#000000` |
| `webflow` | `#146EF5` |
| `github_pages` | `#181717` |

### Color Mode Usage Reference

| Component | State | color prop |
|---|---|---|
| `PlatformConnectionCard` | `connected=true` | `"brand"` |
| `PlatformConnectionCard` | `connected=false` | `"mono"` |
| `DestinationChip` | `selected=true` | `"brand"` |
| `DestinationChip` | `selected=false` | `"mono"` |
| `PublicFooter` social links | always | `"brand"` |
| Landing page platform pills | always | `"mono"` (hover cascade handles color flip) |
| `ContentCalendar` cell | always | `"mono"` (too small for brand color) |
| `CampaignList` published row | always | `"mono"` |
| `PostCard` platform chip | always | `"mono"` |
| `RetryPanel` platform row | always | `"mono"` |
| `MetaPlatformsSection` header icons | always | `"mono"` |

### Files to Modify

| File | Change type |
|---|---|
| `frontend/components/ui/PlatformIcon.tsx` | COMPLETE REWRITE |
| `frontend/components/publishing/PlatformConnectionCard.tsx` | UPDATE line 139 — add `color` prop |
| `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` | UPDATE — delete `PLATFORM_ICON_MAP`, update `DestinationChip` |
| `frontend/components/roadmap/PostCard.tsx` | UPDATE — remove icon from `getPlatformInfo()`, use `PlatformIcon` |
| `frontend/components/publishing/RetryPanel.tsx` | UPDATE — fix label bug, add icons |
| `frontend/components/publishing/PlatformConnectionsClient.tsx` | UPDATE — `MetaPlatformsSection` icons |
| `frontend/components/marketing/PublicFooter.tsx` | UPDATE — add social follow row |
| `frontend/app/page.tsx` | UPDATE — `PLATFORMS` array + pill render |

### No New Dependencies

Zero new npm packages. All SVGs are inline. No image files added to `/public`. No `react-icons`, no `simple-icons`.

### PostCard `platform_hint` Mapping Note

`RoadmapCampaignSummary.platform_hint` values: `"blog_full"`, `"linkedin"`, or absent (defaults to X).
- `"blog_full"` → use `"wordpress"` as platform key (blog icon)
- `"linkedin"` → `"linkedin"`
- anything else / null → `"x"`

The `getPlatformInfo()` function still returns `label` and `charLimit` and `postText` — only the `icon` field is removed.

### `approval-panel.tsx` Lucide Imports After Change

**Remove:** `Globe`, `Layout`, `AtSign`, `Share2`, `Camera`, `Users`, `MessageSquare`
**Keep:** `GitBranch`, `Database`, `Loader2`, `CheckCircle2`, `XCircle`, `RefreshCw`, `Check`

The `headless` platform destination chip will render `PlatformIcon platform="headless"` which falls through to `<Link2>` — acceptable, as headless is not a social platform.

### Project Rules Reminder

- No em-dashes in any user-facing copy (this story adds no copy, but follow the rule)
- No emojis anywhere
- No Turbopack RSC API calls — this story is all client components, no risk
- `rounded-none` everywhere (no rounded corners — the footer social links have no visible border so this is moot)
- Brand name is **PersonnaPress** (double-n), never PersonaPress

### Paper Style Design System Constraints

- `shadow-brutal = shadow-[4px_4px_0px_#111111]` — not used in this story
- ink = `#111111`, graphite = `#555555`, paper = `#FAFAF7`
- No Framer Motion — these are static SVG swaps, CSS `transition-opacity` covers the footer hover
- Focus rings: `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`

### Review Findings

- [x] [Review][Patch] Mono-mode SVGs missing fill="currentColor" — icons render black instead of inheriting text-* color [frontend/components/ui/PlatformIcon.tsx:24] — fixed: added `fill: "currentColor"` to shared spread; brand inline style overrides it
- [x] [Review][Patch] Footer placeholder href="#" links had target="_blank" — remove from X/LinkedIn/Instagram [frontend/components/marketing/PublicFooter.tsx:75-89] — fixed: removed target="_blank" and rel from placeholder links
- [x] [Review][Patch] RetryPanel retry button aria-label used raw platform key [frontend/components/publishing/RetryPanel.tsx:116] — fixed: use PLATFORM_LABELS lookup
- [x] [Review][Patch] .env.example angle-bracket placeholder for META_APP_ID [frontend/.env.example:46] — fixed: replaced with REPLACE_WITH_META_APP_ID
- [x] [Review][Patch] .env.example missing trailing newline [frontend/.env.example] — fixed
- [x] [Review][Patch] Redundant opacity-100 class on all 4 footer social links [frontend/components/marketing/PublicFooter.tsx:72-89] — fixed: removed
- [x] [Review][Defer] PLATFORM_LABELS duplicated across 3 files — pre-existing pattern, needs shared constants module
- [x] [Review][Defer] Webflow SVG uses viewBox="0 0 24 24" while all others use 32x32 — cosmetic optical weight difference, sourceconstraint (SimpleIcons format)
- [x] [Review][Defer] SYNTHETIC_KEYS exhaustiveness in RetryPanel — future synthetic keys may fall into icon branch incorrectly
- [x] [Review][Defer] rounded-full on spinner in RetryPanel — pre-existing, intentional for circular spinner

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Rewrote `PlatformIcon.tsx` as the single source of truth with all 8 brand SVG paths inline, `color="mono"|"brand"` prop, and `Link2` fallback. LinkedIn (previously missing) and `wordpress-com` alias both added.
- `PlatformConnectionCard`: brand color shown when `connected=true`, mono when disconnected.
- `approval-panel.tsx`: removed `PLATFORM_ICON_MAP`, `LucideIcon` alias, and 7 dead Lucide imports. `DestinationChip` now uses `PlatformIcon` with `color={selected ? "brand" : "mono"}`.
- `PostCard.tsx`: removed `icon` field from `getPlatformInfo()` return type; added `platformKey` field. Removed 3 dead Lucide imports. Uses `PlatformIcon` with `platformKey`.
- `RetryPanel.tsx`: added `PLATFORM_LABELS` map, `PlatformIcon` import. Platform name no longer uses raw CSS `capitalize`; shows proper label. Non-synthetic platforms now show icon in flex row.
- `PlatformConnectionsClient.tsx`: added `PlatformIcon` import. `MetaPlatformsSection` now shows Instagram, Facebook, Threads icons above section label.
- `PublicFooter.tsx`: added social follow links nav (Facebook brand URL, X/LinkedIn/Instagram as `#` placeholders). Bottom bar uses `flex-wrap`. Icons at `size-5 color="brand"`.
- `app/page.tsx`: `PLATFORMS` converted to `{label, platform}[]`. Pills now `inline-flex items-center gap-2` with `PlatformIcon` at `size-4 color="mono"` for auto hover color flip.

### File List

- `frontend/components/ui/PlatformIcon.tsx` — complete rewrite
- `frontend/components/publishing/PlatformConnectionCard.tsx` — added `color` prop to PlatformIcon
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` — removed PLATFORM_ICON_MAP + dead imports, updated DestinationChip
- `frontend/components/roadmap/PostCard.tsx` — removed icon from getPlatformInfo, added platformKey, uses PlatformIcon
- `frontend/components/publishing/RetryPanel.tsx` — added PLATFORM_LABELS, PlatformIcon, fixed label display
- `frontend/components/publishing/PlatformConnectionsClient.tsx` — added PlatformIcon, MetaPlatformsSection icons
- `frontend/components/marketing/PublicFooter.tsx` — added social follow links nav
- `frontend/app/page.tsx` — PLATFORMS array + pill render updated
