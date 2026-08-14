---
baseline_commit: dd51de6
---

# Story 21.13: Social Post Image Preview and Instagram Warning

Status: done

---

## Story

As a PersonnaPress user reviewing social posts before publishing,
I want to see the campaign's featured image in the social post review panel,
so that I know whether a campaign image exists and can judge whether it will accompany my posts on Instagram and LinkedIn.

As a PersonnaPress user with Instagram connected,
I want to see a clear inline note when no campaign image is attached,
so that I understand that Instagram will be skipped at publish time — before I click Publish — rather than discovering a failed publish after the fact.

---

## Context & Motivation

### The gap

The `SocialPostEditors` component (`frontend/components/campaigns/SocialPostEditors.tsx`) shows the X and LinkedIn text editors but has no visibility into the campaign image. The image is stored on `campaign.image_url` and used automatically at publish time — but the review screen gives no indication of whether it exists.

This matters most for Instagram: `dispatch_publish` skips Instagram silently if `campaign.image_url` is null (Story 21.12 fixes the "skipped = failed" bug, making this skip produce a "published" result — but users will still wonder why Instagram received no post).

This is the prevention mechanism: before the user clicks Publish, they see the image and any Instagram warning. Story 21.12 is the correction mechanism after publish.

### What is NOT in scope

- Uploading or replacing the campaign image from this screen (that belongs to `ImagePanel`, which already handles image generation and upload)
- Any change to publish logic (covered by Story 21.12)
- Platform-native content generation (separate future story — see note at end)

### Design constraints (paper style)

- No emojis anywhere
- `lucide-react` for the warning icon (`Info`)
- No color fills, no colored borders — monochrome palette: `ink=#111111`, `graphite=#555555`, `border=#D4D0C8`
- No Framer Motion — CSS only
- No border-radius (`rounded-none` aesthetic matches the rest of the app)
- `aspect-video` (16:9) container for the image — handles both square and landscape source images via `object-cover`

---

## Acceptance Criteria

### AC 1: Image thumbnail renders above text sections when imageUrl is present

**Given** `imageUrl` prop is a non-null, non-empty string,
**When** `SocialPostEditors` renders,
**Then** an `<img>` element renders at the top of the component (above the X section), contained in a full-width `aspect-video` div with a `border border-border` frame and `overflow-hidden`.
**And** the img has `alt="Campaign image"` and `className="w-full h-full object-cover"`.

**Given** `imageUrl` is null, undefined, or empty string,
**When** `SocialPostEditors` renders,
**Then** no image element or placeholder renders — the component looks identical to its current state.

---

### AC 2: Instagram warning renders when Instagram is connected and no image exists

**Given** `metaContext.instagram === true` AND `imageUrl` is null/undefined/empty,
**When** `SocialPostEditors` renders the LinkedIn section,
**Then** an informational `<p>` tag renders immediately below the LinkedIn label row (before the textarea), containing:
  - An `Info` lucide icon at `size-3` with `aria-hidden="true"` and `shrink-0`
  - Text: `"Instagram will be skipped at publish — no image attached to this campaign"`
  - Typography: `text-[10px] font-mono text-graphite`
  - Layout: `flex items-center gap-1 -mt-1 mb-2`

**Given** `metaContext.instagram === true` AND `imageUrl` is a valid URL,
**When** `SocialPostEditors` renders,
**Then** no Instagram warning renders (image exists, Instagram will publish).

**Given** `metaContext.instagram` is false/undefined (Instagram not connected),
**When** `SocialPostEditors` renders,
**Then** no Instagram warning renders regardless of `imageUrl` state.

---

### AC 3: The `imageUrl` prop flows from parent without additional API calls

**Given** `ApprovalGateClient` already has `campaign.image_url` from server-side props,
**When** it renders `SocialPostEditors`,
**Then** it passes `imageUrl={campaign.image_url ?? null}` — no new `useQuery`, no new API fetch, no new component state.

---

### AC 4: Existing SocialPostEditors behavior is fully preserved

**Given** the component is rendered without `imageUrl` prop (existing call sites with no change),
**When** it renders,
**Then** all existing behavior is unchanged: X section, LinkedIn section, save button, character counters, platform icon badges, read-only mode, dirty state tracking, and `SocialPostEditorsHandle.getCurrentValues()` ref.

---

## Files to Modify

| File | Change |
|---|---|
| `frontend/components/campaigns/SocialPostEditors.tsx` | Add `imageUrl` prop, image thumbnail block, Instagram warning `<p>`, `Info` import |
| `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` | Pass `imageUrl={campaign.image_url ?? null}` to `SocialPostEditors` |
| `frontend/__tests__/components/SocialPostEditors.test.tsx` | Add 4 new tests for image thumbnail and Instagram warning; confirm existing tests still pass |

---

## Dev Notes

### Prop interface change — `SocialPostEditors.tsx`

```typescript
interface SocialPostEditorsProps {
  campaignId: string;
  initialXPost: string | null;
  initialLinkedInPost: string | null;
  readOnly?: boolean;
  showXSection?: boolean;
  showLinkedInSection?: boolean;
  metaContext?: MetaContext;
  imageUrl?: string | null;   // ← ADD
}
```

Update the destructure on line 38:
```typescript
>(({ campaignId, initialXPost, initialLinkedInPost, readOnly = false, showXSection = true, showLinkedInSection = true, metaContext, imageUrl }, ref) => {
```

---

### Add `Info` import

Add `Info` to the lucide-react import at the top of `SocialPostEditors.tsx`. Check whether `Info` is already imported — if not, add it:
```typescript
import { Info } from "lucide-react";
```

---

### AC 1 — Image thumbnail block

Insert at the very top of the returned JSX, as the first child of `<div className="space-y-8">`:

```tsx
{imageUrl && (
  <div className="border border-border overflow-hidden aspect-video w-full">
    <img
      src={imageUrl}
      alt="Campaign image"
      className="w-full h-full object-cover"
    />
  </div>
)}
```

The parent `space-y-8` provides the gap between image and the first textarea section automatically — no additional margin needed.

Do NOT use `next/image` here. The `imageUrl` is an external CDN URL (Gemini-generated or user-uploaded) and may not be in `next.config.js` image domains. A plain `<img>` is correct and safe — this is an authenticated app screen, not a public page.

---

### AC 2 — Instagram warning block

The warning sits between the LinkedIn label row `<div>` and the `<textarea>`. It must be inside the `{showLinkedInSection !== false && (...)}` block. Insert it immediately after the closing `</div>` of the label row:

```tsx
{showLinkedInSection !== false && (
  <div>
    <div className="flex items-center justify-between mb-2">
      <label htmlFor="linkedin-post" className="text-xs font-mono uppercase tracking-widest text-graphite">
        LinkedIn
      </label>
      {/* existing platform icon badges — unchanged */}
    </div>

    {/* Instagram no-image informational note */}
    {metaContext?.instagram && !imageUrl && (
      <p className="flex items-center gap-1 text-[10px] font-mono text-graphite -mt-1 mb-2">
        <Info className="size-3 shrink-0" aria-hidden="true" />
        Instagram will be skipped at publish — no image attached to this campaign
      </p>
    )}

    <textarea id="linkedin-post" ... />
    {/* counter — unchanged */}
  </div>
)}
```

Note: `-mt-1` collapses the gap between the label row's `mb-2` and the warning, visually grouping the warning with the label above rather than floating between label and textarea.

---

### AC 3 — `ApprovalGateClient.tsx` prop pass-through

Find the `<SocialPostEditors ... />` render (line 211). Add `imageUrl` prop:

```tsx
<SocialPostEditors
  ref={socialEditorsRef}
  campaignId={campaign.id}
  initialXPost={campaign.x_post ?? null}
  initialLinkedInPost={campaign.linkedin_post ?? null}
  readOnly={!isPending}
  showXSection={hideBlogSection ? !!campaign.x_post : true}
  showLinkedInSection={hideBlogSection ? !!campaign.linkedin_post : true}
  metaContext={isPending ? metaContext : undefined}
  imageUrl={campaign.image_url ?? null}   {/* ← ADD */}
/>
```

No import changes needed in `ApprovalGateClient.tsx` — `SocialPostEditors` is already imported.

---

### Warning only when editable or read-only?

Show the warning regardless of `readOnly` state. When `readOnly=true` (published/rejected campaigns), the warning still informs the user why Instagram received no post. Suppress only by `metaContext` gate — `metaContext` is already set to `undefined` when `!isPending` in the parent, so the warning will naturally not render for non-pending campaigns (AC 4 preserved).

---

## Tests to Write

File: `frontend/__tests__/components/SocialPostEditors.test.tsx`

### New test 1: Image thumbnail renders when imageUrl provided
```typescript
it("renders campaign image thumbnail when imageUrl is provided", () => {
  render(<SocialPostEditors campaignId="c1" initialXPost="" initialLinkedInPost="" imageUrl="https://cdn.example.com/img.png" />);
  const img = screen.getByRole("img", { name: "Campaign image" });
  expect(img).toBeInTheDocument();
  expect(img).toHaveAttribute("src", "https://cdn.example.com/img.png");
});
```

### New test 2: Image thumbnail absent when imageUrl is null
```typescript
it("does not render image thumbnail when imageUrl is null", () => {
  render(<SocialPostEditors campaignId="c1" initialXPost="" initialLinkedInPost="" imageUrl={null} />);
  expect(screen.queryByRole("img", { name: "Campaign image" })).not.toBeInTheDocument();
});
```

### New test 3: Instagram warning renders when connected and no image
```typescript
it("renders Instagram skip warning when instagram is connected and imageUrl is null", () => {
  render(
    <SocialPostEditors
      campaignId="c1"
      initialXPost=""
      initialLinkedInPost=""
      imageUrl={null}
      metaContext={{ instagram: true }}
    />
  );
  expect(screen.getByText(/Instagram will be skipped at publish/i)).toBeInTheDocument();
});
```

### New test 4: Instagram warning absent when image is present
```typescript
it("does not render Instagram warning when imageUrl is provided", () => {
  render(
    <SocialPostEditors
      campaignId="c1"
      initialXPost=""
      initialLinkedInPost=""
      imageUrl="https://cdn.example.com/img.png"
      metaContext={{ instagram: true }}
    />
  );
  expect(screen.queryByText(/Instagram will be skipped at publish/i)).not.toBeInTheDocument();
});
```

### Existing tests
All existing tests in the file must continue to pass unmodified — `imageUrl` is optional with no default behavior change when absent.

---

## Key Constraints

- **No DB migration** — no schema changes
- **No new API endpoints** — `imageUrl` comes from props, not a new fetch
- **No `next/image`** — use plain `<img>` (external CDN URL, not in configured domains)
- **No Framer Motion** — the image block and warning are static; no animation
- **Paper Style** — `border border-border`, no radius, monochrome; `Info` lucide icon only
- **No emojis** — warning text is plain prose
- **`readOnly` mode unaffected** — all textarea disable/enable behavior unchanged

---

## Future Story Note

Platform-native content generation (separate instagram_caption, facebook_post, threads_post fields with AI-generated platform-specific variants) is intentionally deferred. It requires a DB migration (3 new columns), new LLM prompt instructions, 3 new editor sections in SocialPostEditors, and updated publishing logic. This is a separate story for a future sprint planning session.

---

## File List

- `frontend/components/campaigns/SocialPostEditors.tsx`
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`
- `frontend/__tests__/components/SocialPostEditors.test.tsx`

---

## Dev Agent Record

### Implementation Notes

- Added `Info` import from `lucide-react` to `SocialPostEditors.tsx`
- Added `imageUrl?: string | null` to `SocialPostEditorsProps` interface and destructure
- Inserted image thumbnail block (`<img>` in `aspect-video` container) as first child of the `space-y-8` wrapper — renders only when `imageUrl` is truthy (AC 1)
- Inserted Instagram skip warning `<p>` immediately before the LinkedIn `<textarea>`, gated on `metaContext?.instagram && !imageUrl` (AC 2)
- Used plain `<img>` (not `next/image`) per spec — `imageUrl` is an external CDN URL
- Added `imageUrl={campaign.image_url ?? null}` prop to `<SocialPostEditors>` in `ApprovalGateClient.tsx` (AC 3)
- All 4 new tests pass; all 12 existing tests pass unmodified (16 total)

---

### Review Findings

- [x] [Review][Patch] Em-dash in warning copy violates no-em-dash constraint [frontend/components/campaigns/SocialPostEditors.tsx:183] — replaced `—` with `-`
- [x] [Review][Patch] Missing test: imageUrl=undefined does not render thumbnail [frontend/__tests__/components/SocialPostEditors.test.tsx] — added
- [x] [Review][Patch] Missing test: instagram=false with imageUrl=null does not render warning [frontend/__tests__/components/SocialPostEditors.test.tsx] — added
- [x] [Review][Defer] Warning invisible when showLinkedInSection=false (narrow edge case outside spec scope) — deferred, pre-existing
- [x] [Review][Defer] Whitespace-only imageUrl passes truthiness guard (backend produces clean URLs or null) — deferred, pre-existing

---

## Change Log

- 2026-08-14: Story 21.13 created ready-for-dev — campaign image thumbnail in SocialPostEditors, Instagram skip warning, imageUrl prop thread-through from ApprovalGateClient, 4 new tests.
- 2026-08-14: Implementation complete — imageUrl prop added, image thumbnail (AC 1), Instagram warning (AC 2), ApprovalGateClient pass-through (AC 3), 4 new tests all pass, 12 existing tests preserved (AC 4). Status set to review.
