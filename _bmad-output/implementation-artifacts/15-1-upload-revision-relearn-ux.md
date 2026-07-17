---
baseline_commit: 684f26b
---

# Story 15.1: Upload Filename, Revision History Collapse & File Upload Relearn Trigger

Status: done

## Story

As a PersonnaPress user,
I want uploaded image filenames to stay recognisable, the revision history panel to stay compact, and my brand voice to automatically retrain when I add new content files,
so that my workflow is smoother and the UI does not become unwieldy over time.

## Acceptance Criteria

### AC 1 — Image upload: preserve original filename

1. **Given** a user uploads an image (PNG/JPG/JPEG/WEBP) via `POST /api/v1/clients/{client_id}/images`, **When** the object is stored in Supabase, **Then** the object path is `{client_id}/{uuid4}_{slugified_name}.{ext}` (e.g. `abc.../3147453d_personnapress-ai-dashboard.jpg`); the UUID prefix guarantees uniqueness; the slugified name is lowercase, spaces replaced with hyphens, only `[a-z0-9\-]` retained, truncated to 80 chars before extension.

2. **Given** the slug helper, **When** the original filename contains characters outside `[a-z0-9\-_.]` (e.g. spaces, uppercase, accents, parentheses), **Then** they are stripped or transliterated so the resulting path is a valid URL segment with no encoding needed.

3. **Given** the response from the upload endpoint, **When** the client receives the public URL, **Then** the URL contains the slugified filename and the UUID prefix — visually identifiable yet unique.

---

### AC 2 — Revision history: show 5 most recent, expand to see all

4. **Given** the History card in the `/blog/[id]` article editor right sidebar, **When** there are 5 or fewer revisions, **Then** all revisions are shown exactly as today (no change in behaviour).

5. **Given** there are more than 5 revisions, **When** the History card renders, **Then** only the 5 most recent revisions (highest revision numbers) are shown; below the list a link reads "Show all X revisions" (where X is the total count); the card height is bounded and does not grow further.

6. **Given** the user clicks "Show all X revisions", **When** the panel expands, **Then** the remaining revisions appear in a scrollable container (`max-h-[260px] overflow-y-auto`) directly below the initial 5, separated by a 1px `#E5E5E5` divider; the toggle text changes to "Show less"; all revision row interactions (Preview, Restore, Current badge) work identically in the expanded section.

7. **Given** the panel is expanded, **When** the user clicks "Show less", **Then** only the 5 most recent revisions are shown again and the overflow container collapses.

8. **Given** the toggle link, **Then** it is styled `text-[12px] text-[#555555] hover:text-[#111111] transition-colors underline underline-offset-2` with `focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1` — Paper Style, no emojis, Lucide icons only.

---

### AC 3 — Content file upload: auto-trigger AI relearn

9. **Given** a user uploads one or more content files in `FileUploadPanel`, **When** all uploads in the batch complete successfully (at least one file succeeded with no network error), **Then** `POST /api/v1/clients/{client_id}/ingest` is called automatically — no user action required.

10. **Given** the ingest call is in-flight, **When** it is pending, **Then** an inline status banner appears below the upload area with a `Loader2` spinner and the text "Relearning voice from new content…"; the banner uses `border border-[#111111] p-3` Paper Style, no modal, no blocking UI.

11. **Given** the ingest call succeeds (HTTP 202), **When** the job is accepted, **Then** the banner transitions to a success state: `Check` icon + "Voice profile updated." in `text-[#2E4F2E]`; the banner auto-dismisses after 3 seconds via `setTimeout`.

12. **Given** the ingest call fails (network error or non-2xx), **When** the error occurs, **Then** the banner shows `AlertTriangle` icon + a short error message + a "Retry" button (`text-[12px] font-medium underline`); clicking Retry re-fires `clientsApi.ingest(clientId)`.

13. **Given** the banner transitions from success to idle (auto-dismiss), **Then** Framer Motion `AnimatePresence` is used for the exit animation (`opacity: 0, y: -6`, duration 0.18s); this is the ONLY justified use of Framer Motion in this component — CSS cannot animate unmounting.

14. **Given** the upload batch contains only errored files (all uploads failed), **When** the batch finishes, **Then** the ingest trigger is NOT called (no point relearning from files that did not land in storage).

---

## Tasks / Subtasks

### Task 1 — Backend: slugify image filename (AC 1–3)

- [x] 1.1 In `backend/app/routers/images.py`, add a `_slugify_filename(name: str) -> str` helper immediately below `_check_magic`:
  ```python
  import re, unicodedata

  def _slugify_filename(name: str) -> str:
      """Lowercase, ASCII-only, spaces to hyphens, max 80 chars."""
      name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
      name = name.lower()
      name = re.sub(r"[^a-z0-9\-_]", "-", name)
      name = re.sub(r"-{2,}", "-", name).strip("-")
      return name[:80] or "image"
  ```

- [x] 1.2 Update line 123 from:
  ```python
  object_path = f"{client_id}/{uuid.uuid4()}{ext}"
  ```
  to:
  ```python
  stem = _slugify_filename(Path(file.filename).stem if file.filename else "image")
  object_path = f"{client_id}/{uuid.uuid4()}_{stem}{ext}"
  ```
  (`Path` is already imported via `from pathlib import Path` — add if missing.)

- [x] 1.3 Verify the Supabase `upload_file` call uses `object_path` unchanged — no other changes needed.

---

### Task 2 — Frontend: revision history collapse (AC 4–8)

- [x] 2.1 In `frontend/app/(app)/blog/[id]/article-editor.tsx`, add state near the top of the component (alongside other `useState` declarations):
  ```typescript
  const HISTORY_VISIBLE = 5;
  const [historyExpanded, setHistoryExpanded] = useState(false);
  ```

- [x] 2.2 Replace the current revision map block (lines ~620–666) with:
  ```tsx
  {/* Visible revisions: always show 5 most recent */}
  <div className="space-y-0">
    {revisions.slice(0, HISTORY_VISIBLE).map((rev) => {
      const isCurrent = rev.revision_number === maxRevNum;
      return <RevisionRow key={rev.revision_number} rev={rev} isCurrent={isCurrent} ... />;
    })}
  </div>

  {/* Expanded overflow: scrollable area for older revisions */}
  {historyExpanded && revisions.length > HISTORY_VISIBLE && (
    <div className="max-h-[260px] overflow-y-auto border-t border-[#E5E5E5] pt-3 space-y-0 mt-1">
      {revisions.slice(HISTORY_VISIBLE).map((rev) => {
        const isCurrent = rev.revision_number === maxRevNum;
        return <RevisionRow key={rev.revision_number} rev={rev} isCurrent={isCurrent} ... />;
      })}
    </div>
  )}

  {/* Toggle link */}
  {revisions.length > HISTORY_VISIBLE && (
    <button
      type="button"
      onClick={() => setHistoryExpanded((v) => !v)}
      className="text-[12px] text-[#555555] hover:text-[#111111] transition-colors underline underline-offset-2 mt-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
    >
      {historyExpanded ? "Show less" : `Show all ${revisions.length} revisions`}
    </button>
  )}
  ```

  Note: The existing inline JSX for each revision row is long. Do NOT extract to a separate `RevisionRow` component unless it already exists — inline the JSX exactly as today in both the visible and expanded sections. The placeholder `<RevisionRow .../>` above is shorthand for the full existing row JSX.

- [x] 2.3 Ensure no Framer Motion is used here — CSS handles the show/hide via conditional rendering. The scrollable `max-h-[260px]` container appears/disappears instantly which is correct for this pattern.

---

### Task 3 — Frontend: relearn trigger in FileUploadPanel (AC 9–14)

- [x] 3.1 In `frontend/components/clients/FileUploadPanel.tsx`, add imports at top:
  ```typescript
  import { useCallback, useRef, useState } from "react";  // already present; add no duplicate
  import { AnimatePresence, motion } from "framer-motion";
  import { Loader2, Check, AlertTriangle } from "lucide-react";
  import { clientsApi } from "@/lib/api";
  ```

- [x] 3.2 Add relearn state after the existing state declarations:
  ```typescript
  type RelearningStatus = "idle" | "learning" | "success" | "error";
  const [relearning, setRelearning] = useState<RelearningStatus>("idle");
  const [relearningError, setRelearningError] = useState<string | null>(null);
  const relearningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  ```

- [x] 3.3 Add `triggerRelearn` callback after the existing `uploadWithProgress` callback:
  ```typescript
  const triggerRelearn = useCallback(async () => {
    if (relearningTimerRef.current) clearTimeout(relearningTimerRef.current);
    setRelearning("learning");
    setRelearningError(null);
    try {
      await clientsApi.ingest(clientId);
      setRelearning("success");
      relearningTimerRef.current = setTimeout(() => setRelearning("idle"), 3000);
    } catch {
      setRelearning("error");
      setRelearningError("Failed to start relearning. Try again.");
    }
  }, [clientId]);
  ```

- [x] 3.4 In the upload handler, after the existing `queryClient.invalidateQueries` call, add:
  ```typescript
  // Trigger AI voice relearn from newly uploaded files (only if at least one upload succeeded)
  const anySucceeded = uploading.some((p) => p.status === "done");
  if (anySucceeded) {
    triggerRelearn();
  }
  ```
  Note: `uploading` state at this point in the handler reflects the current batch. Use a local variable to track success if the closure captures stale state — derive it from XHR results in the loop instead if needed.

- [x] 3.5 In the JSX `return`, place the status banner immediately after the file list section and before the upload button:
  ```tsx
  <AnimatePresence>
    {relearning !== "idle" && (
      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
        className="mt-3 border border-[#111111] p-3 flex items-center gap-3"
        role="status"
        aria-live="polite"
      >
        {relearning === "learning" && (
          <>
            <Loader2 className="size-4 text-[#555555] animate-spin shrink-0" aria-hidden="true" />
            <p className="text-[13px] text-[#555555] font-sans">Relearning voice from new content…</p>
          </>
        )}
        {relearning === "success" && (
          <>
            <Check className="size-4 text-[#2E4F2E] shrink-0" aria-hidden="true" />
            <p className="text-[13px] text-[#2E4F2E] font-sans">Voice profile updated.</p>
          </>
        )}
        {relearning === "error" && (
          <>
            <AlertTriangle className="size-4 text-[#8B1A1A] shrink-0" aria-hidden="true" />
            <p className="text-[13px] text-[#8B1A1A] font-sans flex-1">{relearningError}</p>
            <button
              type="button"
              onClick={triggerRelearn}
              className="text-[12px] font-medium text-[#111111] underline underline-offset-2 hover:text-[#555555] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1 shrink-0"
            >
              Retry
            </button>
          </>
        )}
      </motion.div>
    )}
  </AnimatePresence>
  ```

- [x] 3.6 Clean up the timer on unmount — add a `useEffect` cleanup:
  ```typescript
  useEffect(() => {
    return () => {
      if (relearningTimerRef.current) clearTimeout(relearningTimerRef.current);
    };
  }, []);
  ```

---

## Dev Notes

### Files to touch

| File | Change |
|---|---|
| `backend/app/routers/images.py` | Add `_slugify_filename()`, update `object_path` construction |
| `frontend/app/(app)/blog/[id]/article-editor.tsx` | Add `historyExpanded` state, slice revisions, add toggle button |
| `frontend/components/clients/FileUploadPanel.tsx` | Add relearn state, `triggerRelearn` callback, status banner |

### Key constraints

- **No new backend endpoints** — `clientsApi.ingest(clientId)` maps to the existing `POST /api/v1/clients/{client_id}/ingest` (HTTP 202, already in `frontend/lib/api.ts`).
- **No DB migration** — filename change is storage-path only; existing URLs remain valid.
- **No Framer Motion in article-editor.tsx** — the history collapse uses conditional rendering (no exit animation needed). Framer Motion is ONLY in `FileUploadPanel.tsx` for the dismiss animation.
- **Paper Style strict** — no emojis, only Lucide icons, 1px `border-[#111111]` borders, `focus-visible:ring-2 focus-visible:ring-[#111111]` on all interactive elements, 44px min touch targets.
- **No regressions** — the revision preview modal, restore dialog, and current-revision badge all use existing handlers; do not change their logic.
- **Ingest is idempotent** — calling it while a prior job is still running is safe (backend creates a new job; old job finishes or is superseded).

### Existing patterns to follow

- `sourceBadge(rev.source)` and `relativeDate(rev.created_at)` are already defined in `article-editor.tsx` — reuse them in both the visible and expanded revision sections.
- `clientsApi.ingest` signature: `(id: string) => apiFetch<{ job_id: string }>`. It returns `{ job_id }` on 202; catch block handles any thrown error.
- The `Loader2 animate-spin` pattern is established in the codebase (see existing publish/restore pending states).

### Testing

- Upload an image with spaces and uppercase in the filename (e.g. `My Dashboard Screenshot.jpg`) — verify the stored URL is `{uuid}_my-dashboard-screenshot.jpg`.
- Upload an image with special chars (e.g. `café (1).png`) — verify ASCII-only slugification.
- Create 8 revisions on an article — verify only 5 show, toggle works, scrollable area appears.
- Upload a content file — verify the relearn banner appears, transitions to success, auto-dismisses.
- Simulate network failure on `/ingest` — verify error banner and Retry button.

### Project Structure Notes

- `_slugify_filename` goes in `images.py` not in a shared utils module — it is image-upload-specific.
- `HISTORY_VISIBLE = 5` constant goes at component level in `article-editor.tsx`, not exported.
- No new components or files needed for this story.

### References

- `backend/app/routers/images.py:87–134` — full upload endpoint
- `frontend/app/(app)/blog/[id]/article-editor.tsx:607–667` — current history card JSX
- `frontend/components/clients/FileUploadPanel.tsx:1–216` — full upload panel
- `frontend/lib/api.ts` — `clientsApi.ingest` already defined

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1: Added `_slugify_filename()` helper (unicodedata NFKD + ASCII-only, lowercase, hyphens, 80-char limit) to `images.py`. Updated `object_path` construction to `{client_id}/{uuid4}_{slug}{ext}`. Added `re`, `unicodedata`, and `pathlib.Path` imports.
- Task 2: Added `HISTORY_VISIBLE = 5` constant and `historyExpanded` state to `article-editor.tsx`. Replaced the flat `revisions.map()` block with a split render: first 5 revisions always visible (in a `space-y-0` div), older revisions in a scrollable `max-h-[260px] overflow-y-auto` container gated by `historyExpanded`, and a toggle button styled to Paper Style spec. Full inline JSX reused in both sections (no separate component extracted).
- Task 3: Added `AnimatePresence`/`motion`, `Loader2`, `Check`, `AlertTriangle` imports and `clientsApi` to `FileUploadPanel.tsx`. Added `RelearningStatus` type, `relearning`/`relearningError` state, `relearningTimerRef`, `triggerRelearn` callback (POST to `/ingest`, success auto-dismisses after 3s), `useEffect` timer cleanup, and `successCount` tracking in upload loop. Status banner rendered via `AnimatePresence` with opacity/y-6 exit animation (0.18s). Retry button re-fires `triggerRelearn`.

### File List

- `backend/app/routers/images.py`
- `frontend/app/(app)/blog/[id]/article-editor.tsx`
- `frontend/components/clients/FileUploadPanel.tsx`

### Review Findings

- [x] [Review][Patch] Slugify regex allows underscores — violates AC 1.1 `[a-z0-9\-]`-only spec; change `[^a-z0-9\-_]` → `[^a-z0-9\-]` [backend/app/routers/images.py:63]
- [x] [Review][Patch] Toggle button lacks `aria-expanded` — no ARIA state exposed to assistive technology [frontend/app/(app)/blog/[id]/article-editor.tsx:729]
- [x] [Review][Patch] `historyExpanded` not reset on `articleId` change — add `useEffect` to reset on prop change [frontend/app/(app)/blog/[id]/article-editor.tsx]
- [x] [Review][Patch] `HISTORY_VISIBLE` constant declared inside component body — move to module scope [frontend/app/(app)/blog/[id]/article-editor.tsx:129]
- [x] [Review][Patch] `type RelearningStatus` declared inside component body — move to module scope [frontend/components/clients/FileUploadPanel.tsx:40]
- [x] [Review][Patch] `space-y-0` is a no-op Tailwind class on both revision containers — remove [frontend/app/(app)/blog/[id]/article-editor.tsx:625,677]
- [x] [Review][Defer] No concurrency guard in `triggerRelearn` [frontend/components/clients/FileUploadPanel.tsx:135] — deferred, backend ingest is idempotent per dev notes
- [x] [Review][Defer] Stale `historyExpanded` if revisions drop back ≤5 then grow above 5 [frontend/app/(app)/blog/[id]/article-editor.tsx] — deferred, revisions only grow in this app; not reachable in practice
- [x] [Review][Defer] `clientId` in-flight ingest race on prop change [frontend/components/clients/FileUploadPanel.tsx] — deferred, would need AbortController; unmount cleanup handles timer
- [x] [Review][Defer] Relearn error state doesn't auto-clear before next upload batch [frontend/components/clients/FileUploadPanel.tsx] — deferred, clears at start of next triggerRelearn; minimal UX impact

## Change Log

- 2026-07-16: Story implemented — image upload slugified filenames (AC 1-3), revision history collapse to 5 with expand/collapse toggle (AC 4-8), FileUploadPanel auto-relearn trigger with inline status banner and Framer Motion dismiss (AC 9-14). Status → review.
- 2026-07-16: Code review complete — 6 patches applied (slugify regex, aria-expanded, historyExpanded reset, HISTORY_VISIBLE scope, RelearningStatus scope, space-y-0 removal); 4 deferred; 7 dismissed. Status → done.
