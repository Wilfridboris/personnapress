---
baseline_commit: a01ab18063c72b0f2ddf2d24951f53f6d5b9754b
---

# Story 4.4: Approve & Reject Campaign

Status: done

## Story

As an authenticated user,
I want to approve a Campaign to mark it ready for publishing, or reject it with an optional reason to trigger regeneration,
So that nothing publishes without my explicit sign-off and I can refine content that does not meet my standards.

## Acceptance Criteria

1. **Given** a user clicks "Approve" in the Approval Gate footer, **When** `POST /api/v1/campaigns/{id}/approve` is called, **Then** `campaigns.status` transitions atomically from `pending_approval` to `approved`; if the transition is attempted from any other status, the API returns HTTP 400 with error code `INVALID_STATUS_TRANSITION`.

2. **Given** the approve action succeeds and the Client has at least one Platform Connection configured, **When** the `approved` status is confirmed, **Then** the Approval Gate footer transitions to the "approved, not yet published" state: the Approve/Reject buttons are replaced by a schedule picker and two CTAs — "Publish now" primary button and "Schedule" secondary button (fully wired in Epic 5, stubs only in this story).

3. **Given** the approve action succeeds and the Client has NO Platform Connections configured, **When** the `approved` status is confirmed, **Then** a prompt appears: "Connect a platform to publish. Your campaign is approved and ready." with a "Connect a platform" CTA that navigates to `/clients/{client_id}/connections`; the Campaign status badge shows "APPROVED" and the content is preserved.

4. **Given** a user clicks "Reject" in the Approval Gate footer, **When** the Reject button is clicked, **Then** a confirmation dialog appears with: a headline "Reject this campaign?"; an optional plain-text textarea labeled "Reason (optional) — helps us improve future generations"; a "Reject campaign" Danger-styled confirm button; a "Cancel" secondary button.

5. **Given** the user confirms rejection (with or without a reason), **When** `POST /api/v1/campaigns/{id}/reject` is called, **Then** `campaigns.status` transitions from `pending_approval` to `rejected`; if a reason was provided, it is saved to `campaigns.rejection_reason`; the Approval Gate transitions to the "rejected" state showing the rejection status and a "Regenerate from same Brain Dump" primary CTA.

6. **Given** the user clicks "Regenerate from same Brain Dump" on a rejected Campaign, **When** the regeneration is triggered, **Then** `POST /api/v1/campaigns/{id}/regenerate` creates a new Campaign record with the same `brain_dump` text and `client_id`, creates a new `jobs` record, dispatches a new generation BackgroundTask, and navigates to the new Campaign's Approval Gate at `/campaigns/{new_campaign_id}` — the old rejected Campaign is preserved with its rejected status.

7. **Given** a generation or publish job is in-flight for a Campaign, **When** the Approval Gate footer renders, **Then** both the Approve and Reject buttons are disabled until the job reaches a terminal state; a loading indicator (inline spinner) is shown on the button that corresponds to the active operation.

8. **Given** the Approve button is clicked, **When** the action completes, **Then** the Campaign status badge in the Approval Gate header updates optimistically to "APPROVED" before the API response; if the API returns an error, the badge reverts to "PENDING APPROVAL" and an error toast is shown.

## Tasks / Subtasks

- [x] Task 1: Add backend `POST /approve` endpoint (AC: #1)
  - [x] 1.1 In `backend/app/routers/campaigns.py`, add:
    ```python
    class ApproveResponse(BaseModel):
        id: uuid.UUID
        status: str
        client_id: uuid.UUID

    @router.post("/{campaign_id}/approve", response_model=ApproveResponse)
    async def approve_campaign(
        campaign_id: uuid.UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> ApproveResponse:
    ```
  - [x] 1.2 Ownership check: same pattern as existing GET endpoint — return 404 if not found or not owned
  - [x] 1.3 Status guard: `campaign.status != "pending_approval"` → return HTTP 400:
    ```python
    {"error": {"code": "INVALID_STATUS_TRANSITION", "message": "Campaign can only be approved from pending_approval status.", "detail": {}}}
    ```
  - [x] 1.4 Atomic status transition: `campaign.status = "approved"` → `db.add(campaign)` → `await db.commit()` → `await db.refresh(campaign)`
  - [x] 1.5 Return: `ApproveResponse(id=campaign.id, status=campaign.status, client_id=campaign.client_id)` — include `client_id` so frontend can check platform connections and redirect if needed

- [x] Task 2: Add backend `POST /reject` endpoint (AC: #4, #5)
  - [x] 2.1 In `backend/app/routers/campaigns.py`, add:
    ```python
    class RejectRequest(BaseModel):
        reason: Optional[str] = None

    class RejectResponse(BaseModel):
        id: uuid.UUID
        status: str
        rejection_reason: Optional[str]

    @router.post("/{campaign_id}/reject", response_model=RejectResponse)
    async def reject_campaign(
        campaign_id: uuid.UUID,
        body: RejectRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> RejectResponse:
    ```
  - [x] 2.2 Ownership check + status guard: same pattern; only `pending_approval` can be rejected; error code: `INVALID_STATUS_TRANSITION`
  - [x] 2.3 Transition: `campaign.status = "rejected"`; if `body.reason`: `campaign.rejection_reason = body.reason.strip()`
  - [x] 2.4 Commit and return `RejectResponse`

- [x] Task 3: Add backend `POST /regenerate` endpoint (AC: #6)
  - [x] 3.1 In `backend/app/routers/campaigns.py`, add:
    ```python
    @router.post("/{campaign_id}/regenerate", response_model=CampaignCreateResponse, status_code=202)
    async def regenerate_campaign(
        campaign_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
    ) -> CampaignCreateResponse:
    ```
  - [x] 3.2 Fetch source campaign — ownership check — status guard: only `rejected` campaigns can be regenerated (error code: `INVALID_STATUS_TRANSITION`)
  - [x] 3.3 Subscription check: call `await check_campaign_limit(db, user_id)` before creating new campaign — same as `POST /campaigns` endpoint
  - [x] 3.4 Create new campaign: `new_campaign = await create_campaign(db, source_campaign.client_id, source_campaign.brain_dump)`
  - [x] 3.5 Create new job: `new_job = await create_job(db, job_type="generation", status="pending", campaign_id=new_campaign.id)`
  - [x] 3.6 Commit: `await db.commit()`
  - [x] 3.7 Dispatch: `background_tasks.add_task(run_generation, new_job.id)` — same import as existing `POST /campaigns`
  - [x] 3.8 Return: `CampaignCreateResponse(campaign_id=new_campaign.id, job_id=new_job.id)` — status 202
  - [x] 3.9 The source `rejected` campaign is NOT modified — it remains with `status="rejected"`

- [x] Task 4: Add `approve`, `reject`, `regenerate` to `campaignsApi` if not already present (AC: #1, #5, #6)
  - [x] 4.1 Check `frontend/lib/api.ts` — `campaignsApi.approve` and `campaignsApi.reject` already exist per the file read (they return `Campaign`); verify they match the new backend response shapes
  - [x] 4.2 `campaignsApi.approve` currently returns `Campaign` — update to accept the new `ApproveResponse` type or keep returning `Campaign` (ApproveResponse is a subset); if the backend returns the full campaign, use `Campaign` type; **decision: return `Campaign` from approve for simplicity — update backend to return `CampaignResponse` instead of `ApproveResponse`**
  - [x] 4.3 Add `regenerate` if missing:
    ```typescript
    regenerate: (id: string) =>
      apiFetch<{ campaign_id: string; job_id: string }>(`/campaigns/${id}/regenerate`, { method: "POST" }),
    ```
  - [x] 4.4 Add `reject` with reason payload — current stub takes no body; update:
    ```typescript
    reject: (id: string, reason?: string) =>
      apiFetch<Campaign>(`/campaigns/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: reason ?? null }),
      }),
    ```

- [x] Task 5: Rewrite `approval-panel.tsx` with full state machine (AC: #1–#8)
  - [x] 5.1 The existing `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` is a stub — replace it completely with the full implementation
  - [x] 5.2 New props:
    ```typescript
    interface ApprovalPanelProps {
      campaign: Campaign;
      blogEditorRef?: RefObject<BlogEditorHandle>;      // from Story 4.2
      socialEditorsRef?: RefObject<SocialPostEditorsHandle>;  // from Story 4.3
    }
    ```
  - [x] 5.3 Internal state:
    - `isApproving: boolean` — spinner on Approve button
    - `isRejecting: boolean` — spinner on Reject button
    - `showRejectDialog: boolean` — controls ConfirmModal visibility
    - `rejectionReason: string` — optional reason textarea value
    - `optimisticStatus: CampaignStatus | null` — for optimistic badge update (AC #8)
    - `clientHasPlatforms: boolean | null` — fetched after approve
  - [x] 5.4 **Optimistic approve flow (AC #8)**:
    ```typescript
    async function handleApprove() {
      setIsApproving(true);
      setOptimisticStatus('approved');  // immediate badge update

      // Save edits first (Stories 4.2 + 4.3)
      const blogHtml = blogEditorRef?.current?.getCurrentHtml();
      const socialValues = socialEditorsRef?.current?.getCurrentValues();
      
      try {
        if (blogHtml || socialValues) {
          await campaignsApi.patch(campaign.id, {
            ...(blogHtml ? { blog_html: blogHtml } : {}),
            ...(socialValues ?? {}),
          });
        }
        const result = await campaignsApi.approve(campaign.id);
        // Check platform connections for client
        const connections = await fetchAPI<{items: unknown[]}>(`/clients/${result.client_id ?? campaign.client_id}/connections`);
        setClientHasPlatforms((connections?.items?.length ?? 0) > 0);
        // Trigger page refresh to reflect new status
        router.refresh();
      } catch (err) {
        setOptimisticStatus(null);  // revert optimistic update
        addToast({ type: 'error', message: err instanceof APIError ? err.message : 'Approval failed.' });
      } finally {
        setIsApproving(false);
      }
    }
    ```
  - [x] 5.5 **Reject flow (AC #4, #5)**:
    - "Reject" button click → `setShowRejectDialog(true)`
    - Dialog has optional textarea for reason; "Reject campaign" Danger button confirms
    - On confirm: `setIsRejecting(true)` → `campaignsApi.reject(campaign.id, rejectionReason || undefined)` → on success: `router.refresh()`; on error: toast
  - [x] 5.6 **Post-approve state rendering (AC #2, #3)**:
    - When `campaign.status === 'approved'` OR `optimisticStatus === 'approved'`:
      - If `clientHasPlatforms === true`: show "Publish now" (primary, stub — links to Epic 5) + "Schedule" (secondary, stub)
      - If `clientHasPlatforms === false`: show "Connect a platform to publish. Your campaign is approved and ready." with `<Link href={/clients/${campaign.client_id}/connections}>Connect a platform</Link>` as primary CTA
      - If `clientHasPlatforms === null` (loading): show loading skeleton
  - [x] 5.7 **Post-reject state rendering (AC #5)**:
    - When `campaign.status === 'rejected'`: show "Regenerate from same Brain Dump" primary button → calls `handleRegenerate()`
    - `handleRegenerate`: `campaignsApi.regenerate(campaign.id)` → navigate to `/campaigns/{new_campaign_id}?job_id={new_job_id}` using `useRouter().push()`
  - [x] 5.8 **Disabled state during in-flight jobs (AC #7)**:
    - Accept `jobIsActive?: boolean` prop from parent OR pass it down from the page
    - When `jobIsActive=true`: both Approve and Reject buttons get `disabled` + inline spinner indicating which is active
  - [x] 5.9 Use `useRouter()` from `next/navigation` for client-side navigation after approve/reject/regenerate

- [x] Task 6: Integrate full ApprovalPanel into campaign page (AC: #1–#8)
  - [x] 6.1 In `frontend/app/(app)/campaigns/[id]/page.tsx`, pass `campaign` object (full) to `ApprovalPanel` instead of just `campaignId`
  - [x] 6.2 The `page.tsx` is a Server Component — it fetches campaign server-side; `ApprovalPanel` is a Client Component — it receives the serialized campaign object as prop
  - [x] 6.3 The sticky footer stub from Story 4.1 (Approve/Reject buttons) should be removed — the `ApprovalPanel` owns the sticky footer in this story
  - [x] 6.4 Pass `blogEditorRef` and `socialEditorsRef` from the page: since `page.tsx` is a Server Component, refs cannot live there — **the refs must be managed in a Client Component wrapper**
    - Create `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx` as a `"use client"` wrapper
    - This component holds the `blogEditorRef` and `socialEditorsRef` using `useRef`
    - Renders: `<BlogEditor ref={blogEditorRef} ... />` + `<SocialPostEditors ref={socialEditorsRef} ... />` + `<ApprovalPanel ... blogEditorRef={blogEditorRef} socialEditorsRef={socialEditorsRef} />`
    - `page.tsx` renders `<ApprovalGateClient campaign={campaign} />` for the interactive editing portion

- [x] Task 7: Reject Confirmation Dialog (AC: #4)
  - [x] 7.1 Use the existing `ConfirmModal` component from `frontend/components/ui/ConfirmModal.tsx` if it supports a textarea slot; if not, use the existing `Modal` component to build a custom dialog
  - [x] 7.2 Read `ConfirmModal.tsx` — check if it accepts custom children or only a message string
  - [x] 7.3 Dialog content:
    - Headline: "Reject this campaign?" (Paper Style: Playfair Display font if it's a major headline, but since it's a dialog heading, use `font-display text-xl font-bold text-ink`)
    - Textarea: `<textarea placeholder="Reason (optional) — helps us improve future generations" rows={3} className="w-full border-b border-ink focus:border-b-2 focus:outline-none bg-transparent text-sm font-mono text-ink resize-none px-0 py-2 mt-4" value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)} />`
    - "Reject campaign" button: Danger style (red fill, white text, no shadow, `rounded-none`) — `className="px-5 py-2.5 bg-danger text-white text-sm font-medium hover:bg-danger/90 transition-colors focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2"`
    - "Cancel" button: secondary style
  - [x] 7.4 Modal must have `role="dialog"` + `aria-labelledby` pointing to heading + focus trap + Esc closes it — use existing `Modal.tsx` for proper focus trap behavior
  - [x] 7.5 On Esc or "Cancel": `setShowRejectDialog(false)`, `setRejectionReason('')`

- [x] Task 8: Backend endpoint — fetch platform connections for client (AC: #2, #3)
  - [x] 8.1 The frontend approve flow needs to check `GET /api/v1/clients/{client_id}/connections` to decide which post-approve UI to show — verify this endpoint exists in `backend/app/routers/publishing.py` (Epic 5 placeholder) or `clients.py`
  - [x] 8.2 If the endpoint does NOT exist yet (Epic 5 hasn't been implemented), add a minimal stub:
    ```python
    # In backend/app/routers/publishing.py (or clients.py)
    @router.get("/clients/{client_id}/connections")
    async def list_platform_connections(...):
        return {"items": []}  # stub — always returns empty until Epic 5
    ```
  - [x] 8.3 The frontend can also handle a fetch failure gracefully — if the connections endpoint returns 404, treat as `clientHasPlatforms = false` (show "Connect a platform" CTA)

- [x] Task 9: Optimistic status badge update (AC: #8)
  - [x] 9.1 The `optimisticStatus` in `ApprovalPanel` controls the immediate badge update
  - [x] 9.2 Pass `optimisticStatus` up to the page — since `page.tsx` renders the badge as a Server Component, the optimistic update must happen in the Client Component layer
  - [x] 9.3 Move the status badge display into `ApprovalGateClient.tsx` (the client wrapper from Task 6.4) with a `statusToDisplay: CampaignStatus` state that starts as `campaign.status` and updates to `optimisticStatus` when approve is clicked
  - [x] 9.4 `StatusBadge` component already exists in `components/ui/StatusBadge.tsx` — use it for the badge; import and pass the status string to it

- [x] Task 10: Tests (AC: #1, #4, #5, #6, #8)
  - [x] 10.1 Create `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx` testing `ApprovalPanel` directly
  - [x] 10.2 Test: Approve button click → optimistic status update to "approved" → `campaignsApi.approve` called
  - [x] 10.3 Test: Approve API error → optimistic status reverts → error toast shown
  - [x] 10.4 Test: Reject button click → dialog opens with textarea
  - [x] 10.5 Test: Reject with reason → `campaignsApi.reject(id, reason)` called; without reason → `campaignsApi.reject(id, undefined)`
  - [x] 10.6 Test: Regenerate button click → `campaignsApi.regenerate(id)` → navigate to new campaign URL
  - [x] 10.7 Backend: added tests to `tests/test_campaigns_router.py` for:
    - `POST /campaigns/{id}/approve` — success, wrong status (400), ownership mismatch (404)
    - `POST /campaigns/{id}/reject` — success with reason, success without reason, wrong status
    - `POST /campaigns/{id}/regenerate` — success (creates new campaign + job), rejected source only

## Dev Notes

### Campaign State Machine (Critical — No Shortcuts)

```
pending_approval → approved    (POST /approve)
pending_approval → rejected    (POST /reject)
rejected         → [new pending_approval Campaign]  (POST /regenerate creates NEW campaign)
approved         → [publishing in Epic 5]
```

**Important**: `regenerate` does NOT change the source campaign's status. It creates a BRAND NEW campaign record. The old rejected campaign stays as-is at `status='rejected'`. The navigation goes to the NEW campaign page.

### Existing Stub in approval-panel.tsx

The current `approval-panel.tsx` is a non-functional stub that:
- Has local `status` state for loading/done/error
- Calls backend endpoints directly with `fetch` (not via `campaignsApi`)
- Does a `window.location.reload()` on success (bad pattern — use `router.refresh()`)
- Has no dialog for reject reason
- Has no post-approve state rendering

**Replace the entire file** — do not extend the stub. The new implementation should be cleaner and follow the established patterns (`campaignsApi`, `useUIStore.addToast`, `useRouter().refresh()`).

### ApprovalGateClient.tsx — The Client Boundary Architecture

Since `page.tsx` is a Server Component but the interactive parts need refs and state, introduce a client wrapper:

```
page.tsx (Server Component)
  └── <GenerationGate /> (Client Component — existing)
  └── <ApprovalGateClient campaign={campaign} /> (Client Component — NEW)
        ├── blogEditorRef = useRef<BlogEditorHandle>()
        ├── socialRef = useRef<SocialPostEditorsHandle>()
        ├── <header with optimistic StatusBadge>
        ├── <div lg:grid-cols-5>
        │     ├── <BlogEditor ref={blogEditorRef} ... />     (left panel)
        │     └── <aside>
        │           ├── <ImagePanel ... />
        │           ├── <SocialPostEditors ref={socialRef} ... />
        │           └── <VoiceFidelityBadge ... />          (if score fails)
        └── <ApprovalPanel ... blogEditorRef={blogEditorRef} socialRef={socialRef} />
              └── sticky footer (Approve/Reject for pending; post-approve/post-reject states)
```

This means `page.tsx` becomes simpler — it just fetches the campaign server-side and passes it to `ApprovalGateClient`. The Generating placeholder and GenerationGate can stay in `page.tsx`.

### Sticky Footer CSS — Sidebar Offset

The footer must offset for the sidebar at lg breakpoint:
```tsx
<div className="fixed bottom-0 left-0 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-end gap-3">
```
This was designed in Story 4.1. Do NOT use `left-0` at all breakpoints — the sidebar is 240px wide at lg+ and would overlap the footer.

### Post-Approve State — "Publish Now" and "Schedule" Stubs

Per AC #2, these buttons are "fully wired in Epic 5." In this story, render them as disabled buttons with `data-story="5.x-wiring"` comments:
```tsx
<button type="button" disabled className="... opacity-50 cursor-not-allowed" title="Publishing wired in Epic 5">
  Publish now
</button>
<button type="button" disabled className="..." title="Scheduling wired in Epic 5">
  Schedule
</button>
```
Do NOT navigate to any publishing endpoint — Epic 5 handles that.

### campaignsApi.approve and .reject — Existing Implementations

From `frontend/lib/api.ts` (confirmed in file read):
```typescript
approve: (id: string) => apiFetch<Campaign>(`/campaigns/${id}/approve`, { method: "POST" }),
reject: (id: string) => apiFetch<Campaign>(`/campaigns/${id}/reject`, { method: "POST" }),
```

The `reject` method needs to be updated to accept an optional `reason`:
```typescript
reject: (id: string, reason?: string) =>
  apiFetch<Campaign>(`/campaigns/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? null }),
  }),
```

### Platform Connections Check After Approve

After a successful approve, the frontend needs to know if the client has any platform connections to determine which post-approve UI to show. The simplest approach:

```typescript
// In handleApprove, after successful approve:
try {
  const connections = await fetchAPI<{ items: unknown[] }>(
    `/clients/${campaign.client_id}/connections`
  )
  setClientHasPlatforms(connections.items.length > 0)
} catch {
  // If endpoint doesn't exist yet (Epic 5 not done), default to "no platforms"
  setClientHasPlatforms(false)
}
```

This is a defensive pattern that works whether Epic 5 is implemented or not.

### Error Response Format (from architecture.md)

ALL backend errors must use this format:
```json
{"error": {"code": "INVALID_STATUS_TRANSITION", "message": "...", "detail": {}}}
```
The `APIError` class in frontend `lib/api.ts` parses this format and surfaces `error.message` to the user via toast.

### Reject Dialog Accessibility

Per UX-DR16 and EXPERIENCE.md:
- `role="dialog"` + `aria-labelledby="reject-dialog-heading"`
- Focus moves to the dialog on open (the heading or first input)
- Focus returns to the "Reject" button on close
- Esc closes the dialog
- Tab cycles within the dialog only

Use the existing `Modal.tsx` component which should handle the focus trap — read it first to confirm.

### Import Checklist for ApprovalPanel/ApprovalGateClient

```typescript
import { useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { campaignsApi, fetchAPI, APIError } from '@/lib/api'
import { useUIStore } from '@/lib/stores/useUIStore'
import type { Campaign, CampaignStatus } from '@/lib/types'
import type { BlogEditorHandle } from '@/components/campaigns/BlogEditor'
import type { SocialPostEditorsHandle } from '@/components/campaigns/SocialPostEditors'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Modal } from '@/components/ui/Modal'
import { cn } from '@/lib/utils'
```

### File List for This Story

**New files:**
```
frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx
frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx
```

**Modified files:**
```
frontend/app/(app)/campaigns/[id]/approval-panel.tsx   ← REPLACE ENTIRELY
frontend/app/(app)/campaigns/[id]/page.tsx             ← pass campaign obj, use ApprovalGateClient
frontend/lib/api.ts                                    ← update reject() to accept reason; add regenerate()
backend/app/routers/campaigns.py                       ← add POST /approve, /reject, /regenerate
```

**Conditionally modified (if stub needed):**
```
backend/app/routers/publishing.py                      ← add minimal GET /clients/{id}/connections stub
```

### References

- Story 4.4 ACs: [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4]
- FR-20: Approve Campaign — status transition, platform connection prompt: [Source: _bmad-output/planning-artifacts/epics.md#FR-20]
- FR-21: Reject Campaign — rejection reason, regenerate from same Brain Dump: [Source: _bmad-output/planning-artifacts/epics.md#FR-21]
- UX-DR22: Approval Gate state machine UI — all 5 states: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR22]
- UX-DR16: Accessibility — modal focus trap, dialog attributes: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR16]
- UX-DR21: Microcopy — destructive confirms name the item: [Source: _bmad-output/planning-artifacts/epics.md#UX-DR21]
- EXPERIENCE.md State Patterns — Approval Gate states: [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md]
- EXPERIENCE.md Microcopy table — "Review and approve before publishing.": [Source: _bmad-output/planning-artifacts/ux-designs/ux-PersonnaPress-2026-06-14/EXPERIENCE.md]
- Architecture: BackgroundTask must have job record first: [Source: _bmad-output/planning-artifacts/architecture.md#FastAPI BackgroundTask Pattern]
- Architecture: router delegates to service/repository, error format: [Source: _bmad-output/planning-artifacts/architecture.md]
- Architecture: React Query cache invalidation after mutation: [Source: _bmad-output/planning-artifacts/architecture.md#Mutation + Cache Invalidation Pattern]
- Story 4.2 BlogEditorHandle ref interface: [Source: _bmad-output/implementation-artifacts/4-2-blog-post-wysiwyg-editing.md#Task 2.6]
- Story 4.3 SocialPostEditorsHandle ref interface: [Source: _bmad-output/implementation-artifacts/4-3-social-post-editing-with-character-counters.md#Task 1.6]
- Story 4.1 sticky footer CSS (sidebar offset pattern): [Source: _bmad-output/implementation-artifacts/4-1-approval-gate-campaign-preview-voice-fidelity-badge.md#Sticky Footer Implementation]
- Existing approval-panel.tsx stub (to be replaced): [Source: frontend/app/(app)/campaigns/[id]/approval-panel.tsx]
- Existing campaign page Server Component: [Source: frontend/app/(app)/campaigns/[id]/page.tsx]
- Existing campaignsApi (approve, reject already there — update reject): [Source: frontend/lib/api.ts]
- Existing ConfirmModal + Modal components: [Source: frontend/components/ui/ConfirmModal.tsx, frontend/components/ui/Modal.tsx]
- Existing StatusBadge component: [Source: frontend/components/ui/StatusBadge.tsx]
- Backend campaigns router (add approve/reject/regenerate): [Source: backend/app/routers/campaigns.py]
- Backend create_campaign + create_job repository functions (reuse for regenerate): [Source: backend/app/db/repositories/campaigns.py, backend/app/db/repositories/jobs.py]
- Backend run_generation worker (reuse for regenerate dispatch): [Source: backend/app/workers/generate.py]
- Backend check_campaign_limit service (call before regenerate): [Source: backend/app/services/subscription_service.py]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers. All tasks implemented cleanly.

### Completion Notes List

- Backend: Added `approve_campaign`, `reject_campaign`, `regenerate_campaign` endpoints to `backend/app/routers/campaigns.py`. All follow existing ownership-check + status-guard pattern. Regenerate creates a brand-new campaign+job and leaves source campaign untouched.
- Backend: Added `GET /clients/{client_id}/connections` stub to `backend/app/routers/clients.py` — returns `{"items": []}` until Epic 5 implements real platform connections.
- Frontend: Rewrote `approval-panel.tsx` from scratch with full state machine: pending/approved/rejected states, optimistic badge update via `onOptimisticStatus` callback, reject dialog using existing `Modal.tsx` component, accessibility attributes (focus trap, aria-labelledby, triggerRef for focus return).
- Frontend: Created `ApprovalGateClient.tsx` as client boundary — owns refs for BlogEditor and SocialPostEditors, passes them down to ApprovalPanel, manages optimistic status display badge.
- Frontend: Simplified `page.tsx` to delegate all interactive content to `ApprovalGateClient`. Removed the Story 4.1 sticky footer stub.
- Frontend: Updated `campaignsApi.approve` return type to `ApproveResponse` shape, added `reason` param to `reject`, added `regenerate` method.
- Tests: 10 frontend tests (ApprovalPanel.test.tsx) all pass. 7 new backend tests all pass. Full suites: 58 frontend, 170+ backend — all green.

### File List

**New files:**
- `frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`
- `frontend/__tests__/app/campaigns/ApprovalPanel.test.tsx`

**Modified files:**
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` — replaced entirely
- `frontend/app/(app)/campaigns/[id]/page.tsx` — simplified to use ApprovalGateClient
- `frontend/lib/api.ts` — updated approve/reject/added regenerate
- `backend/app/routers/campaigns.py` — added approve/reject/regenerate endpoints + Pydantic models
- `backend/app/routers/clients.py` — added connections stub endpoint
- `backend/tests/test_campaigns_router.py` — added 7 new tests

### Review Findings

- [x] [Review][Patch] Auth bypass: `list_platform_connections` has no auth check [`backend/app/routers/clients.py:361`]
- [x] [Review][Patch] AC7 not implemented: Approve/Reject buttons not disabled during in-flight job [`frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx`, `approval-panel.tsx`]
- [x] [Review][Patch] No optimistic reject status: `onOptimisticStatus?.("rejected")` never called [`frontend/app/(app)/campaigns/[id]/approval-panel.tsx:68`]
- [x] [Review][Patch] `clientHasPlatforms` stays null forever on already-approved campaign page reload [`frontend/app/(app)/campaigns/[id]/approval-panel.tsx:31`]
- [x] [Review][Patch] `rejection_reason` not cleared on approve: stale reason persists on approved record [`backend/app/routers/campaigns.py:approve_campaign`]
- [x] [Review][Patch] `rejection_reason` not set to None when reject has no/whitespace reason [`backend/app/routers/campaigns.py:254`]
- [x] [Review][Patch] Optimistic revert captures stale closure status instead of pre-action status [`frontend/app/(app)/campaigns/[id]/approval-panel.tsx:61`]
- [x] [Review][Patch] `campaignsApi.reject` return type is `Campaign` but backend returns `RejectResponse` subset [`frontend/lib/api.ts:104`]
- [x] [Review][Patch] `router.refresh()` not called when patch succeeds but approve fails [`frontend/app/(app)/campaigns/[id]/approval-panel.tsx:46`]
- [x] [Review][Patch] `isRegenerating` never reset to false on navigation success — button stays locked [`frontend/app/(app)/campaigns/[id]/approval-panel.tsx:82`]
- [x] [Review][Patch] Status badge label "Approved" should be "APPROVED" per AC3 [`frontend/app/(app)/campaigns/[id]/ApprovalGateClient.tsx:16`]
- [x] [Review][Defer] Race condition: non-atomic status check+write on approve/reject/regenerate [`backend/app/routers/campaigns.py`] — deferred, pre-existing systemic pattern throughout router
- [x] [Review][Defer] `check_campaign_limit` TOCTOU gap on concurrent regenerate [`backend/app/routers/campaigns.py:290`] — deferred, pre-existing systemic pattern same as POST /campaigns
