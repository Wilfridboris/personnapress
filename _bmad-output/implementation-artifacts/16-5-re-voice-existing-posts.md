---
baseline_commit: 42ed019a11a827808a4ba5d7c682eb54348f6326
---

# Story 16.5: Re-voice Existing Posts

Status: done

## Story

As a PersonnaPress user,
I want to refresh any of my approved or published blog posts using my current Brand Voice Profile,
so that older posts written with a weaker voice profile benefit from the richer extraction.

## Acceptance Criteria

### AC 1 -- Backend revoice endpoint

1. **Given** `POST /api/v1/campaigns/{id}/revoice` is added to `backend/app/routers/campaigns.py`, **When** called by the authenticated owner of the campaign, **Then**:
   - The campaign is fetched and ownership verified against the session user
   - The campaign's `brain_dump` is retrieved
   - The client's current `brand_voice_profile` (including `voice_brief` if present) is retrieved
   - A new Campaign record is created with `status="pending_approval"`, the same `client_id`, and the original `brain_dump`
   - A generation job is dispatched (same path as the normal Brain Dump -> Campaign flow from Story 3.3) using the current BVP
   - Returns `{"new_campaign_id": str, "job_id": str}` with HTTP 202
   - The original campaign is NOT modified in any way

2. **Given** the revoice endpoint, **When** the campaign `status` is not `"approved"` or `"published"`, **Then** it returns HTTP 422 with error code `REVOICE_INVALID_STATUS` and message "Only approved or published campaigns can be re-voiced."

3. **Given** the revoice endpoint, **When** the campaign has no `brain_dump` stored (null or empty), **Then** it returns HTTP 422 with error code `REVOICE_NO_BRAIN_DUMP` and message "This campaign has no brain dump to re-generate from."

4. **Given** the revoice endpoint, **When** the client has no `brand_voice_profile`, **Then** the generation proceeds using the default voice (same behavior as a brand-new campaign with no BVP).

---

### AC 2 -- Re-voice action on campaign cards

5. **Given** the Campaign list page (`/campaigns`) and the `CampaignList.tsx` component, **When** a campaign has `status === "approved"` or `status === "published"`, **Then** a "Re-voice" button appears on the campaign card as a secondary action alongside the existing "View" link:
   - Button: Lucide `RefreshCw` icon (14px) + "Re-voice" text label
   - Style: `border border-[#E5E5E5] bg-transparent text-sm text-[#555555] min-h-[44px] px-3 py-2`
   - Hover: `hover:border-[#111111] hover:text-[#111111]`
   - `focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1`
   - The button is NOT shown for campaigns with any other status

6. **Given** a campaign card with status `"pending_approval"`, `"rejected"`, or `"failed"`, **When** rendered, **Then** no "Re-voice" button appears.

---

### AC 3 -- Confirmation modal

7. **Given** the user clicks "Re-voice" on a campaign card, **When** clicked, **Then** a confirmation modal opens:
   - Background: `#F9F9F6` (Paper)
   - Border: `1px solid #111111` (Ink), `rounded-none`, no box-shadow
   - Heading: Playfair Display, "Create a re-voiced draft?" (`font-['Playfair_Display'] text-xl font-bold text-[#111111]`)
   - Campaign title shown below heading in `text-sm font-medium text-[#111111]`, truncated
   - Body: "This creates a new draft using your current voice profile. Your original post is not changed. The new draft goes through the approval gate before publishing."
   - Primary button: "Create new draft" (Ink fill, White text, 4px hard shadow)
   - Secondary button: "Cancel"
   - On open: focus moves to the Cancel button (`autoFocus` on Cancel or `useEffect` focus ref)
   - Escape key closes the modal (when not loading)
   - Modal is role="dialog" with aria-modal="true" and aria-labelledby pointing to the heading

---

### AC 4 -- Loading state and navigation

8. **Given** the user clicks "Create new draft" in the modal, **When** the POST request is in flight, **Then**:
   - The "Create new draft" button shows Lucide `Loader2` icon spinning (`animate-spin`) + "Creating..." text
   - Both buttons are disabled
   - The modal does not close

9. **Given** the POST succeeds, **When** `new_campaign_id` is received, **Then**:
   - The modal closes
   - The user is navigated to `/campaigns/{new_campaign_id}` (the approval gate for the new draft)
   - The campaign list page does NOT need to refresh (the new campaign is not visible there yet)

10. **Given** the POST fails (non-2xx response), **When** the error arrives, **Then**:
    - The loading state clears
    - An error message appears below the buttons: the `error.message` from the response's `error.message` field, or "Failed to create re-voiced draft. Try again." as fallback
    - The user can retry or cancel

---

### AC 5 -- Design system compliance

11. **Given** the Re-voice button and confirmation modal, **When** assessed against the Paper Style design system, **Then**:
    - All surfaces: `rounded-none`
    - Backdrop overlay: `rgba(17,17,17,0.35)` (semi-transparent Ink, no blur)
    - No emojis; Lucide icons only (`RefreshCw`, `Loader2`)
    - All interactive elements: `min-h-[44px]`
    - Focus rings: `focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1`
    - Transitions: `transition-colors duration-150` (no Framer Motion)
    - No em-dash in any visible text

---

## Tasks / Subtasks

### Task 1 -- Backend: add revoice endpoint (AC 1, 2, 3, 4)

- [x] 1.1 In `backend/app/routers/campaigns.py`, add:
  ```python
  @router.post("/{campaign_id}/revoice", status_code=202)
  async def revoice_campaign(
      campaign_id: uuid.UUID,
      session: AsyncSession = Depends(get_session),
      current_user: User = Depends(get_current_user),
  ):
  ```

- [x] 1.2 Fetch campaign and verify ownership: use the existing `get_campaign` repository pattern; return 404 if not found, 403 if wrong user.

- [x] 1.3 Status guard:
  ```python
  if campaign.status not in ("approved", "published"):
      raise HTTPException(422, detail={"error": {"code": "REVOICE_INVALID_STATUS", "message": "Only approved or published campaigns can be re-voiced."}})
  ```

- [x] 1.4 Brain dump guard:
  ```python
  if not campaign.brain_dump:
      raise HTTPException(422, detail={"error": {"code": "REVOICE_NO_BRAIN_DUMP", "message": "This campaign has no brain dump to re-generate from."}})
  ```

- [x] 1.5 Create new Campaign record:
  ```python
  new_campaign = Campaign(
      client_id=campaign.client_id,
      brain_dump=campaign.brain_dump,
      status="pending_approval",
  )
  session.add(new_campaign)
  await session.flush()  # get new_campaign.id
  ```

- [x] 1.6 Create job record and dispatch generation (reuse the existing generation dispatch pattern from the Brain Dump endpoint in Story 3.1/3.3):
  ```python
  job = Job(campaign_id=new_campaign.id, job_type="generation", status="pending")
  session.add(job)
  await session.commit()
  background_tasks.add_task(generation_worker, job_id=job.id, campaign_id=new_campaign.id)
  ```

- [x] 1.7 Return `{"new_campaign_id": str(new_campaign.id), "job_id": str(job.id)}`

- [x] 1.8 The generation worker already fetches `client.brand_voice_profile` at runtime -- no special handling needed. The new campaign has the same `client_id`, so it picks up the current BVP automatically including `voice_brief` if Story 16.2 has run.

---

### Task 2 -- Add `BackgroundTasks` parameter

- [x] 2.1 The revoice endpoint needs `background_tasks: BackgroundTasks` as a FastAPI dependency. Check the Brain Dump creation endpoint (Story 3.1) for the exact parameter pattern already in use.

---

### Task 3 -- Frontend: `RevoiceButton` component (AC 5, 6, 7, 8, 9, 10)

- [x] 3.1 Create `frontend/components/campaigns/RevoiceButton.tsx` as a `"use client"` component. The complete reference implementation from the UX design session is below -- use it as the authoritative source.

  **Component structure:**
  - `RevoiceConfirmModal`: the dialog (role="dialog", aria-modal, aria-labelledby)
  - `RevoiceButton`: the trigger button that manages modal state, API call, and navigation

- [x] 3.2 Implement `RevoiceConfirmModal`:
  ```tsx
  function RevoiceConfirmModal({ campaignTitle, onConfirm, onCancel, loading }) {
    const cancelRef = useRef<HTMLButtonElement>(null);

    useEffect(() => { cancelRef.current?.focus(); }, []);
    useEffect(() => {
      const handler = (e: KeyboardEvent) => {
        if (e.key === "Escape" && !loading) onCancel();
      };
      document.addEventListener("keydown", handler);
      return () => document.removeEventListener("keydown", handler);
    }, [loading, onCancel]);
    // ...
  }
  ```

- [x] 3.3 Modal backdrop: `fixed inset-0 z-50 flex items-center justify-center p-4` with `style={{ backgroundColor: "rgba(17,17,17,0.35)" }}`; no blur.

- [x] 3.4 Modal container: `w-full max-w-md bg-[#F9F9F6] border border-[#111111] p-8`; no shadow; `rounded-none`.

- [x] 3.5 In `RevoiceButton`, the fetch call:
  ```tsx
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/campaigns/${campaignId}/revoice`,
    { method: "POST", credentials: "include" }
  );
  ```
  On success: `router.push(`/campaigns/${data.new_campaign_id}`)`.
  On failure: parse `body.error?.message` or fall back to generic message.

---

### Task 4 -- Wire Re-voice button into `CampaignList.tsx`

- [x] 4.1 In `frontend/components/campaigns/CampaignList.tsx`, import `RevoiceButton`.

- [x] 4.2 Locate the campaign card action area (where the "View" link lives). Add `RevoiceButton` conditionally:
  ```tsx
  {(campaign.status === "approved" || campaign.status === "published") && (
    <RevoiceButton
      campaignId={campaign.id}
      campaignTitle={campaign.title ?? "Untitled"}
    />
  )}
  ```

- [x] 4.3 Verify the card layout accommodates two action buttons side by side without breaking on narrow screens. Use `flex flex-wrap gap-2` on the action container.

---

### Task 5 -- Backend tests

- [x] 5.1 In `backend/tests/test_campaigns.py` (or equivalent), add tests:
  - Happy path: approved campaign, valid brain_dump, returns 202 with new_campaign_id and job_id
  - Status guard: pending_approval campaign returns 422 with REVOICE_INVALID_STATUS
  - Brain dump guard: campaign with null brain_dump returns 422 with REVOICE_NO_BRAIN_DUMP
  - Auth guard: unauthenticated request returns 401; wrong user returns 403
  - Original campaign untouched: verify original campaign.status and brain_dump unchanged after revoice

---

## Dev Notes

### Files to create

| File | Action |
|---|---|
| `frontend/components/campaigns/RevoiceButton.tsx` | CREATE |

### Files to modify

| File | Change |
|---|---|
| `backend/app/routers/campaigns.py` | Add `POST /{campaign_id}/revoice` endpoint |
| `frontend/components/campaigns/CampaignList.tsx` | Wire in RevoiceButton for approved/published campaigns |
| `backend/tests/test_campaigns.py` | Add revoice endpoint tests |

### The new campaign reuses the existing generation pipeline

The revoice endpoint creates a new Campaign and dispatches to `generation_worker` -- the exact same worker that handles normal Brain Dump submissions. No new generation logic is needed. The worker already reads the client's current BVP at job execution time, so it automatically uses the updated BVP (including `voice_brief` if Story 16.2 is deployed).

### Original campaign is immutable

A re-voiced draft is always a NEW campaign. The original campaign record is never patched, its status is never changed, and its published content is never overwritten. The new draft goes through the normal approval gate (review, edit, approve, publish) before anything appears on connected platforms.

### UX reference: the complete RevoiceButton implementation

```tsx
"use client";

import { useRef, useEffect, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";

function RevoiceConfirmModal({ campaignTitle, onConfirm, onCancel, loading }) {
  const cancelRef = useRef(null);
  useEffect(() => { cancelRef.current?.focus(); }, []);
  useEffect(() => {
    const h = (e) => { if (e.key === "Escape" && !loading) onCancel(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [loading, onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         style={{ backgroundColor: "rgba(17,17,17,0.35)" }}>
      <div role="dialog" aria-modal="true" aria-labelledby="revoice-title"
           className="w-full max-w-md bg-[#F9F9F6] border border-[#111111] p-8">
        <p id="revoice-title"
           className="font-['Playfair_Display'] text-xl font-bold text-[#111111] mb-1">
          Create a re-voiced draft?
        </p>
        <p className="text-sm font-medium text-[#111111] mb-3 truncate">{campaignTitle}</p>
        <p className="text-sm text-[#555555] leading-relaxed mb-6">
          This creates a new draft using your current voice profile. Your original post is not
          changed. The new draft goes through the approval gate before publishing.
        </p>
        <div className="flex gap-3">
          <Button variant="primary" onClick={onConfirm} disabled={loading}>
            {loading
              ? <><Loader2 className="size-3.5 animate-spin" aria-hidden="true" />Creating...</>
              : "Create new draft"}
          </Button>
          <Button ref={cancelRef} variant="secondary" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

export function RevoiceButton({ campaignId, campaignTitle }) {
  const router = useRouter();
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/campaigns/${campaignId}/revoice`,
        { method: "POST", credentials: "include" }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.error?.message ?? "Failed to create re-voiced draft.");
      }
      const { new_campaign_id } = await res.json();
      setShowModal(false);
      router.push(`/campaigns/${new_campaign_id}`);
    } catch (err) {
      setError(err.message ?? "Something went wrong.");
      setLoading(false);
    }
  };

  return (
    <>
      <button type="button" onClick={() => setShowModal(true)}
              aria-label={`Re-voice: ${campaignTitle}`}
              className="inline-flex items-center gap-1.5 px-3 py-2 min-h-[44px] border border-[#E5E5E5] bg-transparent text-sm text-[#555555] transition-colors duration-150 hover:border-[#111111] hover:text-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1">
        <RefreshCw className="size-3.5" aria-hidden="true" />
        Re-voice
      </button>
      {error && <p className="text-xs text-[#8B0000] mt-1">{error}</p>}
      {showModal && (
        <RevoiceConfirmModal
          campaignTitle={campaignTitle}
          onConfirm={handleConfirm}
          onCancel={() => !loading && setShowModal(false)}
          loading={loading}
        />
      )}
    </>
  );
}
```

### No em-dash in visible text

All user-facing strings in this story (modal body, button labels, error messages) use plain dashes or no dashes. The modal body copy uses a period instead of a dash between sentences.

### Error shape matches project convention

Backend errors use the nested shape: `{"error": {"code": "SCREAMING_SNAKE_CASE", "message": "..."}}` (AR-17). The frontend reads `body.error?.message`.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None - implementation completed without issues.

### Completion Notes List

- Added `RevoiceResponse` Pydantic model and `POST /{campaign_id}/revoice` endpoint to `campaigns.py`. Reuses `create_campaign` + `create_job` + `run_generation` pattern from the existing regenerate endpoint. Returns 404 (campaign not found), 403 (wrong user), 422 (bad status or no brain_dump), 202 (success).
- Created `RevoiceButton.tsx` as a full "use client" component with `RevoiceConfirmModal` sub-component. Focus moves to Cancel on open, Escape closes when not loading, error displayed below buttons. TypeScript-typed throughout.
- Wired `RevoiceButton` into `CampaignList.tsx` with conditional rendering for approved/published status. Action container updated to `flex flex-wrap gap-2` with `e.stopPropagation()` to prevent row navigation when interacting with the button.
- Added 9 new tests in `test_campaigns_router.py` covering: approved/published happy paths, original unchanged, invalid status (pending_approval + rejected), null brain_dump, empty brain_dump, unauthenticated (401), wrong user (403). All 9 pass; no regressions introduced.

### File List

- `backend/app/routers/campaigns.py` (modified)
- `frontend/components/campaigns/RevoiceButton.tsx` (created)
- `frontend/components/campaigns/CampaignList.tsx` (modified)
- `backend/tests/test_campaigns_router.py` (modified)
- `_bmad-output/implementation-artifacts/16-5-re-voice-existing-posts.md` (modified)

### Review Findings

- [x] [Review][Patch] `setLoading(false)` never called on success path -- modal reopens in disabled/spinner state [frontend/components/campaigns/RevoiceButton.tsx:109]
- [x] [Review][Patch] No focus trap in `RevoiceConfirmModal` -- Tab escapes into background page [frontend/components/campaigns/RevoiceButton.tsx:24]
- [x] [Review][Patch] `headingId` hardcoded `"revoice-title"` -- duplicate DOM ids when two modals open simultaneously [frontend/components/campaigns/RevoiceButton.tsx:18]
- [x] [Review][Patch] Whitespace-only brain_dump bypasses `not campaign.brain_dump` guard [backend/app/routers/campaigns.py:404]
- [x] [Review][Patch] Catch fallback says `"Something went wrong."` instead of spec-mandated `"Failed to create re-voiced draft. Try again."` [frontend/components/campaigns/RevoiceButton.tsx:112]
- [x] [Review][Patch] `test_revoice_campaign_original_unchanged` tests a tautology -- never asserts `create_campaign` received the original brain_dump [backend/tests/test_campaigns_router.py:752]
- [x] [Review][Patch] Modal container missing explicit `rounded-none` (AC 5 design system compliance) [frontend/components/campaigns/RevoiceButton.tsx:41]
- [x] [Review][Patch] No test for `"failed"` campaign status [backend/tests/test_campaigns_router.py]
- [x] [Review][Defer] No rate limiting on revoice endpoint -- pre-existing, applies to all endpoints
- [x] [Review][Defer] No DB rollback on create_campaign/create_job/commit failure -- pre-existing pattern across all endpoints
- [x] [Review][Defer] Raw `<button>` for trigger vs project `<Button>` component -- spec-prescribed design decision
- [x] [Review][Defer] `extractTitle(campaign.blog_html)` called per-render without memoization -- pre-existing rendering pattern
- [x] [Review][Defer] `NEXT_PUBLIC_API_URL` undefined edge case -- pre-existing across all fetch calls
- [x] [Review][Defer] Modal unmount during active request -- theoretical, list does not refresh during revoice

## Change Log

- 2026-07-17: Story 16.5 implemented -- revoice backend endpoint, RevoiceButton component, CampaignList wiring, 9 backend tests. (claude-sonnet-4-6)
- 2026-07-17: Code review complete -- 8 patches applied (setLoading on success, focus trap + Tab key handler, useId for headingId, whitespace brain_dump guard, fallback error text, original_unchanged assertion strengthened, rounded-none on modal, failed-status + whitespace tests added), 6 deferred, 8 dismissed. (claude-sonnet-4-6)
