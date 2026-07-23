---
title: 'Fix nofollow links to open in a new tab'
type: 'bugfix'
created: '2026-07-23'
status: 'done'
route: 'one-shot'
---

# Fix nofollow links to open in a new tab

## Intent

**Problem:** Clicking a "nofollow" link inserted via the blog editor link dialog navigates the current tab — `target="_blank"` was never set, and was actively stripped by DOMPurify (frontend) and both backend HTML sanitizers.

**Approach:** Add `target="_blank"` to `setLink()` when `nofollow` is selected; allow `target` through DOMPurify and both backend sanitizers; restrict accepted values to `_blank` only in the backend attribute filters.

## Suggested Review Order

**Entry point — link dialog writes target**

- `handleLinkConfirm` now passes `target: "_blank"` when nofollow is selected.
  [`BlogEditor.tsx:264`](../../frontend/components/campaigns/BlogEditor.tsx#L264)

**Frontend sanitizer — DOMPurify allows target**

- `target` added to ALLOWED_ATTR and removed from FORBID_ATTR; applies wherever `_DOMPURIFY_CONFIG` is reused (save, render, article-editor).
  [`BlogEditor.tsx:33`](../../frontend/components/campaigns/BlogEditor.tsx#L33)

**Backend sanitizers — campaigns and articles**

- nh3 attribute filter now allows `target="_blank"` only on `<a>` tags; any other value is stripped.
  [`campaigns.py:32`](../../backend/app/routers/campaigns.py#L32)

- BeautifulSoup post-pass restricts `target` to `_blank`; other values removed before href-scheme check.
  [`articles.py:85`](../../backend/app/routers/articles.py#L85)
