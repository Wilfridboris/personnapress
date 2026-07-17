---
baseline_commit: 684f26b
---

# Story 15.2: Excerpt vs Meta Description — Distinct Content Quality

Status: done

## Story

As a PersonnaPress user,
I want the article Excerpt and Meta Description to contain genuinely different, purpose-built content,
so that my blog preview hooks readers while my SEO meta tag is optimised for search engines — not two truncated copies of the same paragraph.

## Acceptance Criteria

### AC 1 — Gemini generates three distinct outputs

1. **Given** the blog generation Gemini prompt in `backend/app/integrations/gemini.py`, **When** it is updated, **Then** the MANDATORY STRUCTURE block contains two distinct HTML comments immediately after `<h1>`:
   ```
   <!-- meta: [One sentence meta description, max 150 chars, ends with action phrase] -->
   <!-- excerpt: [One engaging editorial hook, max 240 chars, conversational tone, makes the reader want to keep reading — NOT a summary of the article] -->
   ```
   These are non-optional output fields; both must appear in every generated article.

2. **Given** the two comment instructions, **When** Gemini generates content, **Then**:
   - `<!-- meta: ... -->` — keyword-rich, ends with a call-to-action phrase (e.g. "Learn how to…", "Discover why…"), written for Google's search results snippet.
   - `<!-- excerpt: ... -->` — editorial hook, written for a human browsing an article list; may open with a provocative question, a surprising fact, or an intriguing observation; does NOT restate the title or read like a summary/TL;DR.

3. **Given** the TL;DR block (`<div class="tldr">`), **When** the Gemini prompt is read, **Then** the TL;DR instruction remains unchanged; TL;DR content must NOT bleed into the excerpt or meta comment — each is a separate instruction with a distinct purpose.

---

### AC 2 — Excerpt extracted from dedicated comment

4. **Given** `_extract_excerpt(html: str)` in `backend/app/services/articles.py`, **When** it is updated, **Then** it first searches for `<!-- excerpt: ... -->` using the same regex pattern used for `<!-- meta: ... -->`; if found, returns the normalised text truncated to 300 chars.

5. **Given** the excerpt comment is absent (e.g. older articles generated before this story), **When** `_extract_excerpt` falls back, **Then** it uses the existing first-`<p>`-after-TL;DR logic (unchanged) — backward compatibility preserved.

6. **Given** the regex pattern, **Then** it is: `r'<!--\s*excerpt:\s*(.+?)\s*-->'` with `re.IGNORECASE | re.DOTALL`; `re` is already imported in `articles.py`.

---

### AC 3 — Meta description extracted exclusively from its comment

7. **Given** `_extract_meta_description(blog_html: str)` in `backend/app/services/publishing.py`, **When** the `<!-- meta: ... -->` comment is found, **Then** it is returned truncated to 160 chars (unchanged behaviour).

8. **Given** the `<!-- meta: ... -->` comment is absent (older articles or Gemini omission), **When** the fallback runs, **Then** the function returns `""` (empty string) instead of the first paragraph — the first-paragraph fallback is removed; returning empty string is preferable to silently copying the excerpt's content into the meta description.

9. **Given** `meta_description` is `""` in the article editor, **When** displayed, **Then** the textarea is empty; the user can manually fill it; the character counter still works correctly on an empty field.

---

### AC 4 — Article creation stores both fields correctly

10. **Given** `backend/app/services/articles.py` function that creates articles from campaign blog HTML (lines ~87–121), **When** an article is created or updated from generated HTML, **Then** `excerpt = _extract_excerpt(campaign.blog_html)` and `meta_description = _extract_meta_description(campaign.blog_html)` are both called with the updated functions — no change to call sites, only the function implementations change.

11. **Given** a newly generated article with both comments present, **When** the article is saved, **Then** `article.excerpt` and `article.meta_description` contain meaningfully different text (different sentences, different purposes).

---

### AC 5 — No regressions on existing articles

12. **Given** existing articles in the database whose `excerpt` and `meta_description` were populated by the old logic (both from first paragraph), **When** those articles are opened in the editor, **Then** the stored values are displayed as-is — no migration or overwrite occurs; users can manually update them if desired.

13. **Given** the public delivery API (`GET /public/v1/articles/{slug}`), **When** it returns an article, **Then** `excerpt` and `meta_description` in the response reflect whatever is stored — no API contract change.

---

## Tasks / Subtasks

### Task 1 — Update Gemini blog generation prompt (AC 1–3)

- [x] 1.1 In `backend/app/integrations/gemini.py`, find the MANDATORY STRUCTURE block (currently around line 104). Replace:
  ```
  <!-- meta: [One sentence meta description, max 150 chars, ends with action phrase] -->
  ```
  with:
  ```
  <!-- meta: [One sentence meta description, max 150 chars, ends with action phrase] -->
  <!-- excerpt: [One engaging editorial hook, max 240 chars, conversational, makes the reader want to keep reading -- NOT a summary or restatement of the title] -->
  ```
  Place the `<!-- excerpt: ... -->` line immediately after `<!-- meta: ... -->` and before `<div class="tldr">`.

  **Critical formatting constraint:** The prompt already bans em-dashes (`—`). The excerpt instruction uses `--` (double hyphen) not `—` — maintain this.

- [x] 1.2 Verify the prompt change does not break the existing `_check_for_tldr` post-processing guard (lines ~291–303 in gemini.py) — that guard only checks for the TL;DR div, not for the HTML comments, so no change needed there.

---

### Task 2 — Update `_extract_excerpt()` to use dedicated comment (AC 4–6)

- [x] 2.1 In `backend/app/services/articles.py`, add `import re` at the top if not already present.

- [x] 2.2 Replace the current `_extract_excerpt` implementation:
  ```python
  def _extract_excerpt(html: str) -> str:
      """Extract the dedicated <!-- excerpt: ... --> comment.

      Falls back to the first <p> after TL;DR strip for articles generated
      before this story shipped.
      """
      match = re.search(r"<!--\s*excerpt:\s*(.+?)\s*-->", html, re.IGNORECASE | re.DOTALL)
      if match:
          return " ".join(match.group(1).split())[:300]
      # Legacy fallback: first paragraph after stripping TL;DR
      soup = BeautifulSoup(html, "html.parser")
      tldr = soup.find("div", class_="tldr")
      if tldr:
          tldr.decompose()
      first_p = soup.find("p")
      return first_p.get_text(separator=" ", strip=True)[:300] if first_p else ""
  ```

- [x] 2.3 The import of `_extract_meta_description` at the top of `articles.py` (line 12) remains — do not remove it.

---

### Task 3 — Update `_extract_meta_description()` to remove first-paragraph fallback (AC 7–9)

- [x] 3.1 In `backend/app/services/publishing.py`, update `_extract_meta_description`:
  ```python
  def _extract_meta_description(blog_html: str) -> str:
      """Extract the <!-- meta: ... --> comment.

      Returns empty string if the comment is absent rather than falling back
      to the first paragraph -- the fallback previously caused meta description
      and excerpt to share identical content.
      """
      match = re.search(r"<!--\s*meta:\s*(.+?)\s*-->", blog_html, re.IGNORECASE | re.DOTALL)
      if match:
          return " ".join(match.group(1).split())[:160]
      return ""
  ```
  Remove the BeautifulSoup fallback block entirely (the `soup = BeautifulSoup(...)` lines that follow the regex check in the current implementation).

- [x] 3.2 Verify `re` and `BeautifulSoup` imports at the top of `publishing.py` — if `BeautifulSoup` is no longer used in the function and no other function in the file uses it, remove the import to keep the file clean. Check carefully before removing.

---

### Task 4 — Verify no call-site changes needed (AC 10–11)

- [x] 4.1 Confirm `backend/app/services/articles.py` lines ~87–121 call `_extract_excerpt` and `_extract_meta_description` — no changes needed at call sites since function signatures are unchanged.

- [x] 4.2 Grep for any other callers of `_extract_excerpt` or `_extract_meta_description` across the codebase — update if any additional callers exist.

---

## Dev Notes

### Files to touch

| File | Change |
|---|---|
| `backend/app/integrations/gemini.py` | Add `<!-- excerpt: ... -->` line to MANDATORY STRUCTURE prompt |
| `backend/app/services/articles.py` | Replace `_extract_excerpt()` to use regex comment first |
| `backend/app/services/publishing.py` | Remove first-paragraph fallback from `_extract_meta_description()` |

### No frontend changes

Both `excerpt` and `meta_description` are stored strings displayed in textarea fields in `article-editor.tsx`. Their display, editing, and save logic is unchanged. Character limits enforced by existing frontend (`META_MAX = 160`) and backend schemas (`max_length=500` for meta, `max_length=1000` for excerpt in `ArticlePatch`) remain in place.

### Why remove the fallback from meta description

The first-paragraph fallback in `_extract_meta_description` was a safety net for when Gemini omitted the `<!-- meta: ... -->` comment. With the updated prompt making both comments non-optional, the fallback will almost never fire — but when it does, it silently produces a meta description identical to the excerpt. An empty meta description is more honest: it surfaces in the editor and prompts the user to fill it, rather than quietly duplicating content that harms SEO (duplicate meta/snippet text across pages).

### Backward compatibility

- `_extract_excerpt` fallback (first `<p>` after TL;DR) is KEPT for older articles — their stored `excerpt` values are not touched.
- `_extract_meta_description` returning `""` on fallback: for NEW article creations only. Existing stored `meta_description` values in the DB are not changed.
- No DB migration required.

### TL;DR is already correctly handled

Both extraction functions already strip `<div class="tldr">` via BeautifulSoup `.decompose()` before parsing. The user concern about TL;DR appearing in these fields is a content-quality issue (the old first-paragraph extraction produced TL;DR-style BLUF prose), not a parsing bug. The dedicated `<!-- excerpt: ... -->` comment resolves this by giving Gemini a separate, explicitly different instruction for the excerpt.

### Gemini prompt — no em-dash constraint

The project bans em-dashes (`—`) from all Gemini prompts. The excerpt instruction uses `--` (double hyphen) as a separator. Verify the final prompt text contains no `—` characters.

### Testing

- Generate a new article after the prompt change — inspect the raw HTML in the DB or logs and confirm both `<!-- meta: ... -->` and `<!-- excerpt: ... -->` comments are present.
- Confirm `article.excerpt` and `article.meta_description` in the DB contain different sentences.
- Open an older article (generated before this story) — confirm its excerpt still shows the stored first-paragraph value (fallback path).
- Confirm `article.meta_description` is `""` for any article whose HTML lacks the meta comment (test by temporarily removing the comment from a test HTML string).
- Confirm the article editor textarea for meta description shows the empty state correctly when `meta_description` is `""`.

### Project Structure Notes

- All three files are pure Python service/integration files — no new modules needed.
- `re` module is stdlib; no new dependencies.
- If `BeautifulSoup` import is removed from `publishing.py`, run the test suite to confirm no hidden usage remains.

### References

- `backend/app/integrations/gemini.py:104–124` — MANDATORY STRUCTURE prompt block
- `backend/app/services/articles.py:12–30, 87–121` — excerpt extraction and article creation
- `backend/app/services/publishing.py:31–44` — meta description extraction
- Gemini no-em-dash constraint: commits `ad345ff`, `69faae8`, `aa3afcc`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `<!-- excerpt: ... -->` line to Gemini MANDATORY STRUCTURE prompt immediately after `<!-- meta: ... -->` and before `<div class="tldr">`. Used `--` (double hyphen) per no-em-dash constraint.
- Confirmed TL;DR post-processing guard in `gemini.py` only checks for `<div class="tldr">` — no change needed.
- Added `import re` to `articles.py` and replaced `_extract_excerpt` with regex-first implementation; legacy first-`<p>` fallback preserved for older articles.
- Removed BeautifulSoup first-paragraph fallback from `_extract_meta_description` in `publishing.py`; function now returns `""` when comment is absent. `BeautifulSoup` import retained (used elsewhere in file at lines 89, 142, etc.).
- Updated `test_extract_meta_description_falls_back_to_first_paragraph` → `test_extract_meta_description_returns_empty_when_comment_absent` to match new behaviour.
- Added 5 new tests for `_extract_excerpt` in `test_articles.py` covering: comment present, legacy fallback, case-insensitivity, whitespace stripping, empty HTML. All 50 tests pass.

### File List

- `backend/app/integrations/gemini.py`
- `backend/app/services/articles.py`
- `backend/app/services/publishing.py`
- `backend/tests/services/test_articles.py`
- `backend/tests/services/test_publishing.py`

### Review Findings

- [x] [Review][Patch] Whitespace-only excerpt comment returns empty string instead of falling back to paragraph [backend/app/services/articles.py:27-28]
- [x] [Review][Patch] HTML tags not stripped from regex-extracted excerpt (inconsistent with legacy get_text() fallback) [backend/app/services/articles.py:26-28]
- [x] [Review][Patch] AC 1.2 — Excerpt prompt missing concrete opening-style examples (provocative question, surprising fact, intriguing observation) [backend/app/integrations/gemini.py:107]
- [x] [Review][Patch] No test for excerpt truncation at >300 chars boundary [backend/tests/services/test_articles.py]
- [x] [Review][Patch] AC 11 — No combined test verifying excerpt and meta description contain different text when both comments present [backend/tests/services/test_articles.py]
- [x] [Review][Defer] AC 1.2 — Meta prompt missing concrete CTA examples ("Learn how to…", "Discover why…") [backend/app/integrations/gemini.py:106] — deferred, pre-existing (meta line unchanged by this story)
