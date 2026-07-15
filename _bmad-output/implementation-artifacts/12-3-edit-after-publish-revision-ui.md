---
baseline_commit: 89ae16358dc7a4316d6fd71ab2b01b0d52e31ee3
---

# Story 12.3: Edit After Publish, Revision UI & Blog Section

Status: done

## Story

As a PersonnaPress user,
I want to edit my live articles, browse their revision history, and restore any version,
so that my published blog stays current without regenerating campaigns.

## Acceptance Criteria

1. **Given** the left sidebar navigation, **When** it renders for an authenticated user with an active client, **Then** a "Blog" item appears (Lucide `Newspaper` icon) between "Campaigns" and "Connections", linking to `/blog`; like the Connections item (Story 11.6), it is hidden or disabled when no active client is set.

2. **Given** the `/blog` page, **When** it loads, **Then** it lists the active client's articles (title, slug, status badge `published`/`hidden`, published date, last updated) fetched via TanStack Query in a client component (server component does auth/session only, per the RSC loop rule), with an empty state explaining that publishing a campaign creates articles.

3. **Given** the `/blog/[id]` editor page, **When** it loads an article, **Then** the existing Tiptap `BlogEditor` renders the article HTML in editable mode (read-only restriction does not apply to articles), alongside editable fields: title, slug, excerpt, meta description, tags, category, author, and a hide/unhide toggle.

4. **Given** the user edits the slug, **When** they attempt to save, **Then** a confirmation dialog warns that existing links to the old slug will break (customer sites fetch by slug) and requires explicit confirmation before saving.

5. **Given** the user clicks Save with content changes, **When** PATCH `/api/v1/articles/{id}` succeeds, **Then** the article is updated, a new revision is created (per Story 12.1 AC 4), the editor shows a success toast, and subsequent public API reads reflect the new content (new ETag).

6. **Given** the revision history panel on `/blog/[id]`, **When** it renders, **Then** it lists revisions newest first (revision number, date, source badge initial/edit/restore), each with a preview action (rendered sanitized HTML in a modal) and a Restore action; restoring revision N creates a new highest revision with source `restore` whose content equals revision N (history is never rewritten), updates the article, and refreshes the editor.

7. **Given** the approval panel of an approved or published campaign, **When** publish destinations are shown, **Then** "Headless Blog" appears as a destination requiring no platform connection; selecting it calls POST `/api/v1/campaigns/{id}/publish-headless`, which creates or updates the campaign's article (reusing the Story 12.1 service function), marks the campaign `published` (guard accepts `approved` or `published`, mirroring Story 11.7 AC 4), and the panel confirms with the article's slug.

8. **Given** all backend article endpoints under `/api/v1/articles`, **When** called, **Then** they require the session cookie (existing `get_current_user`), verify the article's client belongs to the current user, and return the standard nested error shape on failure.

9. **Given** the new UI, **When** assessed against the Paper Style design system, **Then** it uses Ink 1px solid borders, rounded-none surfaces, Playfair Display headings, Inter body, the 4px 4px 0px Ink shadow on primary buttons, Lucide icons only (no emojis), visible `focus-visible` rings, and 44px minimum touch targets.

## Tasks / Subtasks

### Task 1: Backend article endpoints (AC: 5, 6, 8)

- [x] 1.1 New `backend/app/routers/articles.py`, all with `get_current_user`, all verifying article -> client -> user ownership (join through clients.user_id; 404 `ARTICLE_NOT_FOUND` when not owned, matching existing ownership conventions):
  - `GET /api/v1/articles?client_id=` -> paginated list (status filter optional: `published`, `hidden`, omitted = all)
  - `GET /api/v1/articles/{id}` -> full article
  - `PATCH /api/v1/articles/{id}` -> body: any of title, html, excerpt, meta_description, tags, category, author, slug, status. Content fields route through `update_article_content(source="edit")` (revision on real change only); `status` through `set_article_status` (no revision); `slug` validated (regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`, max 60) + uniqueness per client -> 409 `SLUG_TAKEN` on conflict.
  - `GET /api/v1/articles/{id}/revisions` -> list (number, source, created_at; NOT full html — keep list light)
  - `GET /api/v1/articles/{id}/revisions/{n}` -> full revision content (for preview)
  - `POST /api/v1/articles/{id}/revisions/{n}/restore` -> applies revision N's content via `update_article_content(source="restore")`; returns updated article. Restoring identical content to current is a no-op (no revision) per Story 12.1 AC 4 — return the article unchanged with 200.
- [x] 1.2 HTML sanitization server-side on PATCH: sanitize incoming `html` with the same allowlist the frontend DOMPurify uses (h1-h4, p, ul/ol/li, strong, em, a, br, blockquote, code, pre; no script/style/iframe, no event attributes). Use `bleach` if already a dependency, else a BeautifulSoup strip pass. Never trust client sanitization alone — this HTML is served to third-party sites by the public API.
- [x] 1.3 Register router in `backend/app/main.py`. Pydantic schemas in `backend/app/schemas/article.py` (mirror `backend/app/schemas/campaign.py` style, including the Pydantic strip validator pattern from Story 3-7 for slug/title).

### Task 2: publish-headless endpoint (AC: 7)

- [x] 2.1 In `backend/app/routers/publishing.py`: `POST /api/v1/campaigns/{campaign_id}/publish-headless`. Guard: `campaign.status not in ("approved", "published")` -> 400 `INVALID_STATUS_TRANSITION` (exact pattern from Story 11-7 AC 4, publishing.py ~line 845). Ownership check as existing campaign endpoints.
- [x] 2.2 Calls `create_or_update_article_from_campaign` (Story 12.1 service) synchronously (no job needed — it is a local DB write, not an external API call), sets `campaign.status = "published"` if it was `approved`, commits, returns `{article_id, slug, status}`. If the article already existed, still 200 with the existing slug (idempotent).
- [x] 2.3 Trial enforcement: apply the same trial/subscription guard as `publish_campaign_now` (TRIAL_EXPIRED check) — headless publish is still a publish.

### Task 3: Blog nav item (AC: 1)

- [x] 3.1 Add "Blog" to the sidebar NAV_ITEMS (the Story 11-6 review patch used a `findIndex` insertion — same file/pattern; locate NAV_ITEMS in the app shell component under `frontend/app/(app)/` or `frontend/components/`). Lucide `Newspaper` icon, href `/blog`, positioned between Campaigns and Connections. Same no-active-client behavior as Connections (Story 11.6 AC 6).

### Task 4: /blog list page (AC: 2, 9)

- [x] 4.1 `frontend/app/(app)/blog/page.tsx`: server component does session cookie check ONLY and passes clientId (copy the exact pattern from `connections/page.tsx`, commits d880dc6/0d1b5c9 — this is the RSC loop mitigation, non-negotiable).
- [x] 4.2 `frontend/app/(app)/blog/blog-list.tsx` (`'use client'`): TanStack Query on `articlesApi.list(clientId)`. Table/list rows: Playfair title, Inter 13px slug in Graphite, status badge (published: Success #2E4F2E text on 1px Ink border chip; hidden: Graphite text + `EyeOff` icon chip), published date, updated date. Row click -> `/blog/{id}`. Rows are `<a>`/`<Link>` with min-height 44px, `hover:bg-highlighter/30 transition-colors duration-200`, `focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2`.
- [x] 4.3 Empty state: Paper card, 1px Ink border, `Newspaper` icon (Lucide, `aria-hidden="true"`), Playfair "No articles yet", Inter body "Publish a campaign and it appears here as an article you can keep editing." plus a secondary link to /campaigns. Loading state: shimmer skeleton rows (CSS `@keyframes`, no Framer Motion).

### Task 5: /blog/[id] editor page (AC: 3, 4, 5, 9)

- [x] 5.1 `frontend/app/(app)/blog/[id]/page.tsx` (server: session only) + `article-editor.tsx` (`'use client'`, TanStack Query for article + revisions).
- [x] 5.2 Layout: two-column on `lg:` (editor main column, right rail 320px for metadata + revisions), stacked on mobile. Main column: title input (Inter 24px semibold, borderless with bottom 1px Ink border on focus), then `BlogEditor` (frontend/components/campaigns/BlogEditor.tsx) mounted with `readOnly={false}` — check its current published-status read-only logic; it keys off campaign status, so pass an explicit editable prop rather than a fake status. If BlogEditor hardcodes campaign coupling, extract/wrap rather than fork: keep one Tiptap editor component.
- [x] 5.3 Right rail "Details" card (1px Ink border, rounded-none, p-4, space-y-4): slug input (monospace, lowercase enforced), excerpt textarea (2 rows), meta description textarea with 160-char counter (reuse the character-counter pattern from Story 11-8), tags input (comma-separated -> chips with 1px Ink border), category input, author input, and visibility toggle: a labeled switch row "Visible in delivery API" using `Eye`/`EyeOff` Lucide icons, immediate PATCH on toggle (status only, no revision), optimistic update via TanStack `useMutation` + rollback on error.
- [x] 5.4 Save flow: single primary "Save changes" button (Ink fill, White Inter text, `shadow-[4px_4px_0px_0px_var(--ink)]`, rounded-none, `active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all duration-150`), disabled while pristine or mutation pending (`Loader2` spin while pending). On slug change: Radix AlertDialog (existing modal patterns; focus trap + restore + scroll lock per Story 7-2 review learnings) with title "Change the article slug?", body explaining customer sites fetching `/{old-slug}` will 404, confirm button "Change slug" in Danger (#8B0000) treatment, cancel default. Dialog only when slug differs from loaded value.
- [x] 5.5 Editor content sanitized with the existing DOMPurify config before PATCH (same as BlogEditor's approve flow, via `getCurrentHtml()` ref). Success toast "Article updated." / error toast surfaces `err.message` (APIError parsing already fixed in Story 11-7).

### Task 6: Revision history panel (AC: 6, 9)

- [x] 6.1 Right rail "History" card below Details: list revisions newest first. Each row (min-height 44px): `History` Lucide icon, "Rev {n}" Inter 13px semibold, relative date, source badge (initial: Graphite outline chip; edit: Ink outline chip; restore: Highlighter background chip, Ink text) and two icon buttons with `aria-label`s: preview (`Eye`) and restore (`RotateCcw`). Current (highest) revision row shows "Current" instead of restore.
- [x] 6.2 Preview: Radix Dialog, max-w-3xl, article-styled prose rendering of the revision's sanitized HTML (DOMPurify before `dangerouslySetInnerHTML` — never render revision HTML unsanitized), revision metadata header, and a "Restore this version" primary button inside the dialog.
- [x] 6.3 Restore: confirm inline (button swaps to "Confirm restore?" for 3s, Danger text) OR reuse AlertDialog — pick AlertDialog for consistency with 5.4. On success: invalidate article + revisions queries, editor re-initializes with restored content, toast "Restored to revision {n}. Saved as revision {m}." Wrap `invalidateQueries` separately from the mutation try-block (Story 11-6 review patch pattern).

### Task 7: Approval panel destination (AC: 7)

- [x] 7.1 In `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`: add "Headless Blog" to the publish destinations UI as a card that never shows "not connected" (it needs no platform_connection). Copy: "Headless Blog. Stores this post in your PersonnaPress blog and serves it through your delivery API." with a `Database` or `Braces` Lucide icon (pick one already imported elsewhere if possible; else `Database`).
- [x] 7.2 Publish action: `campaignsApi.publishHeadless(id)` (add to `frontend/lib/api.ts`), on success show the returned slug with a link to `/blog/{article_id}` ("View in Blog"). Handle `TRIAL_EXPIRED` and `INVALID_STATUS_TRANSITION` via existing `err.code` toast patterns. Beware approval-panel state-machine regressions: 11-2/11-7/11-9 reviews patched republish state resets (`githubResult`, `scheduledAt`, `setClientHasPlatforms(null)`) — read the current state handling in approval-panel.tsx fully before adding the new destination, and reset any new state on republish-open the same way.

### Task 8: Tests (AC: all)

- [x] 8.1 Backend `backend/tests/routers/test_articles.py`: ownership (user B gets 404 on user A's article), PATCH creates revision on content change / no revision on status-only, slug conflict 409, slug format validation, restore creates new revision + is idempotent on identical content, sanitization strips `<script>` from PATCHed html.
- [x] 8.2 publish-headless tests in `backend/tests/routers/test_publishing.py`: 202/200 from `approved` and `published`, 400 from `pending_approval`/`rejected`/`failed`, idempotent second call, TRIAL_EXPIRED guard.
- [x] 8.3 Frontend: no frontend test suite covering components exists under `frontend/__tests__/`; manual verification checklist recorded in Dev Agent Record below.

## Dev Notes

### Critical constraints

- **RSC loop rule (project-context.md):** server components do session/auth ONLY; all data via TanStack Query in client components. The connections page is the reference implementation.
- **One Tiptap editor.** Extend/wrap `BlogEditor.tsx`; do not fork a second editor component. Its DOMPurify allowlist is the canonical client-side sanitizer.
- **History is append-only.** No revision row is ever mutated or deleted. Restore = new revision.
- **Articles diverge from campaigns by design.** Editing an article never touches `campaign.blog_html`, and re-publishing a campaign to external platforms still uses campaign content (existing behavior). Publishing again does not overwrite article edits (Story 12.1 idempotency).
- **Paper Style tokens:** Ink, Paper, Graphite, Highlighter #FFF1B8, Success #2E4F2E, Danger #8B0000; Playfair Display headings, Inter body; 1px solid Ink borders; rounded-none; 4px 4px 0px Ink button shadow. No emojis anywhere; Lucide icons only. Prefer CSS transitions over Framer Motion for all hover/toggle/skeleton states (FM only if an exit animation is truly needed — the dialogs already handle their own transitions via Radix).

### Reuse map

| Need | Existing code |
|---|---|
| WYSIWYG editor + sanitize | `frontend/components/campaigns/BlogEditor.tsx` (Tiptap, DOMPurify, `getCurrentHtml()` ref) |
| Server-component session pattern | `frontend/app/(app)/clients/[id]/connections/page.tsx` (commits d880dc6, 0d1b5c9) |
| Nav insertion | NAV_ITEMS + findIndex pattern from Story 11-6 |
| Char counter | Story 11-8 social counter implementation |
| Modal focus trap/restore/scroll lock | Story 7-2 patched modal patterns |
| Error toasts + APIError codes | `frontend/lib/api.ts` (Story 11-7 fix), existing `err.code` checks in approval-panel.tsx |
| Status guard + endpoint shape | `publish_campaign_now` in `backend/app/routers/publishing.py` |
| Article service + repos | Story 12.1 (`backend/app/services/articles.py`, `backend/app/db/repositories/articles.py`) |

### Previous story intelligence

- Stories 12.1/12.2 are direct dependencies — read both File Lists first. The PATCH endpoint must produce a new ETag on the public API automatically (it does, via `updated_at` — just do not forget to bump `updated_at` on status toggles too, since hidden/unhidden changes list responses; note Story 12.1 says status changes skip revisions, not skip `updated_at`).
- Approval panel is the most review-patched file in the codebase (11-2, 11-7, 11-8, 11-9). Read its full state machine before touching it; every new async action needs: pending state, error surface, and state reset on panel re-open.
- Story 7-3 review: never mutate `updated_at` manually where a default/factory handles it — check how existing repos bump it and stay consistent.

### Project Structure Notes

- Backend: new `backend/app/routers/articles.py`, `backend/app/schemas/article.py`; publish-headless lives in existing `backend/app/routers/publishing.py`.
- Frontend: `frontend/app/(app)/blog/page.tsx`, `blog-list.tsx`, `blog/[id]/page.tsx`, `blog/[id]/article-editor.tsx`; shared bits in `frontend/components/` only if reused across pages.
- API client: extend `frontend/lib/api.ts` with `articlesApi` group + `campaignsApi.publishHeadless`; types in `frontend/lib/types.ts`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 12, Story 12.3]
- [Source: _bmad-output/project-context.md#RSC Re-render Loop rule]
- [Source: _bmad-output/implementation-artifacts/12-1-article-model-revision-history.md]
- [Source: _bmad-output/implementation-artifacts/12-2-public-delivery-api-tokens.md]
- [Source: _bmad-output/implementation-artifacts/11-7-republish-error-clarity-re-publish-support.md (status guard + APIError)]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4.6 (github-copilot/claude-sonnet-4.6)

### Debug Log References

None — all tasks implemented cleanly without debugging sessions.

### Completion Notes List

- `BlogEditor.tsx` extended with `hideSaveButton?: boolean` prop rather than forking a second Tiptap editor; guards the internal save button with `{!readOnly && !hideSaveButton && ...}`.
- Server-side HTML sanitization uses BeautifulSoup allowlist (bleach not installed); client-side via async DOMPurify import in article-editor.tsx.
- Blog nav item inserted between Campaigns and Connections in both `sidebar.tsx` and `MobileDrawer.tsx` using `findIndex` insertion consistent with Story 11-6.
- `POST /publish-headless` returns `{article_id, slug, status}` synchronously (no background job — local DB write only).
- Headless Blog button placed between GitHub and Schedule in both the approved-state and published/republish sections of approval-panel; `isHeadlessPublishing` disables all three publish buttons while in flight.
- `PATCH /articles/{id}` separates content fields (→ `update_article_content`, creates revision on change) from status (→ `set_article_status`, no revision).
- 8.3 frontend test suite: no component test suite found under `frontend/__tests__/`; slug-change dialog and revision restore invalidation verified manually.

### File List

**Backend**
- `backend/app/schemas/article.py` — Pydantic schemas: ArticlePatch, ArticleListItem, ArticleListResponse, ArticleResponse, RevisionListItem, RevisionListResponse, RevisionDetail, PublishHeadlessResponse
- `backend/app/routers/articles.py` — articles REST router (GET list, GET detail, PATCH, GET revisions list, GET revision detail, POST restore); BeautifulSoup HTML sanitization
- `backend/app/routers/publishing.py` — added `POST /campaigns/{id}/publish-headless`
- `backend/app/main.py` — registers `articles.router`
- `backend/tests/routers/test_articles.py` — 28 tests: sanitize helper, ownership, PATCH content/status/slug/validation/sanitization, revisions, restore
- `backend/tests/routers/test_publishing.py` — 9 headless tests appended: approved/published 200, invalid statuses 400, TRIAL_EXPIRED, NO_CONTENT, 404s

**Frontend**
- `frontend/lib/types.ts` — Article, ArticleRevision types added
- `frontend/lib/api.ts` — `articlesApi` (list, get, update, listRevisions, getRevision, restoreRevision) + `campaignsApi.publishHeadless` added
- `frontend/components/layout/sidebar.tsx` — Blog nav item (Newspaper icon, /blog, before Connections)
- `frontend/components/layout/MobileDrawer.tsx` — Blog nav item (mobile)
- `frontend/components/campaigns/BlogEditor.tsx` — `hideSaveButton?: boolean` prop added
- `frontend/app/(app)/blog/page.tsx` — server component (auth/session only)
- `frontend/app/(app)/blog/blog-list.tsx` — client component (article list, empty state, skeleton loading)
- `frontend/app/(app)/blog/[id]/page.tsx` — server component (auth/session only)
- `frontend/app/(app)/blog/[id]/article-editor.tsx` — client component (full editor + details rail + revision history panel)
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` — Headless Blog publish button in both approved and republish sections
