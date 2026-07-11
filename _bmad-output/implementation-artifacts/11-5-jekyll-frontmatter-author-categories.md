---
baseline_commit: 44b5700
---

# Story 11.5: Jekyll Frontmatter Corrections & Author/Categories Inputs

Status: done

## Story

As a user publishing a blog post to a Jekyll site via GitHub,
I want the generated frontmatter to use the correct Jekyll date format, separate voice tags into a `tags:` field, and optionally set `author:` and `categories:` from the confirmation panel,
so that the published post integrates cleanly with my Jekyll site without corrupted URLs or malformed dates.

## Acceptance Criteria

1. **Given** `detected_framework === "jekyll"`, **When** a post is published, **Then** the `date:` field uses Jekyll's canonical format `YYYY-MM-DD HH:MM:SS +0000` (e.g. `2026-07-10 09:00:00 +0000`), not ISO 8601 (`2026-07-10T09:00:00Z`).

2. **Given** the campaign has `voice_score.tags`, **When** publishing to Jekyll, **Then** those tags are written to the `tags:` frontmatter field (not `categories:`); the `categories:` field is omitted unless the user explicitly provides it.

3. **Given** the GitHub confirmation panel is open for a Jekyll repo, **When** it renders, **Then** two optional input fields appear between the "File" path block and the "Show front matter" toggle: **Author** (text input, pre-filled from the client name, editable) and **Categories** (text input, placeholder `"guides, facebook"`, empty by default).

4. **Given** the user edits the Author or Categories inputs, **When** they open "Show front matter", **Then** the `<pre>` preview reflects their current values in real time — `author: {value}` and `categories: [{slugs}]` — without any save action.

5. **Given** the user clears the Author field (empty string), **When** the post is published, **Then** no `author:` line is written to the frontmatter.

6. **Given** the user leaves Categories empty, **When** the post is published, **Then** no `categories:` line is written to the frontmatter.

7. **Given** the user has entered `"guides, facebook"` in Categories, **When** the post is published, **Then** the frontmatter contains `categories: [guides, facebook]` (split on comma, trimmed, empty items dropped).

8. **Given** `detected_framework === "hugo"`, **When** the GitHub confirmation panel renders, **Then** the same Author and Categories inputs appear; Categories maps to Hugo's `categories` taxonomy and is written alongside the existing `tags` field.

9. **Given** `detected_framework !== "jekyll"` and `!== "hugo"` (Astro, Next.js, Eleventy, plain\_static), **When** the GitHub confirmation panel renders, **Then** the Author and Categories inputs do NOT appear.

10. **Given** any value in Author or Categories contains a double-quote character, **When** the frontmatter is generated, **Then** the quote is YAML-escaped (`\"`) so the resulting file is valid YAML.

11. **Given** the "Show front matter" preview in the frontend, **When** `framework === "jekyll"`, **Then** the preview date format also uses `YYYY-MM-DD HH:MM:SS +0000` (matching the backend output exactly).

## Tasks / Subtasks

### Task 1: Backend — fix `generate_github_post_file` signature and Jekyll block (AC: 1, 2, 5, 6, 7, 10)

- [x] 1.1 Add `author: str | None = None` and `categories: list[str] | None = None` parameters to `generate_github_post_file` in `backend/app/services/publishing.py`.

- [x] 1.2 Replace the Jekyll date string:
  ```python
  # Remove this line:
  publish_datetime: str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
  # Add per-framework:
  jekyll_date: str = now_utc.strftime("%Y-%m-%d %H:%M:%S +0000")
  ```
  Keep `publish_datetime` (ISO 8601) for Astro, Hugo, Next.js, and Eleventy — they are correct.

- [x] 1.3 Rewrite the Jekyll frontmatter block entirely:
  ```python
  if detected_framework == "jekyll":
      body_md = github_integration.html_to_markdown(blog_html)
      description = _extract_meta_description(blog_html)
      title_yaml = title.replace("\\", "\\\\").replace('"', '\\"')
      description_yaml = description.replace("\\", "\\\\").replace('"', '\\"')

      fm_lines = [
          "---",
          "layout: post",
          f'title: "{title_yaml}"',
          f"date: {jekyll_date}",
          f'description: "{description_yaml}"',
      ]
      # User-provided categories (separate from voice tags)
      if categories:
          cats = [c.replace("\\", "\\\\").replace('"', '\\"') for c in categories if c.strip()]
          if cats:
              fm_lines.append(f"categories: [{', '.join(cats)}]")
      # Voice score tags → tags: field (not categories:)
      if campaign.voice_score and campaign.voice_score.get("tags"):
          voice_tags = campaign.voice_score["tags"]
          if isinstance(voice_tags, list) and voice_tags:
              tags_yaml = ", ".join(
                  f'"{t.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34))}"'
                  for t in voice_tags
              )
              fm_lines.append(f"tags: [{tags_yaml}]")
      # Optional author
      if author:
          author_yaml = author.replace("\\", "\\\\").replace('"', '\\"')
          fm_lines.append(f'author: "{author_yaml}"')
      fm_lines.append("---")
      front_matter = "\n".join(fm_lines) + "\n\n"
      file_content = front_matter + body_md
      file_path = f"_posts/{today}-{slug}.md"
      commit_message = f"Add blog post: {title}"
  ```

- [x] 1.4 Add Hugo `categories` support inside the Hugo YAML and TOML branches — after the existing `tags` block, add:
  ```python
  if categories:
      cats = [c.replace("\\", "\\\\").replace('"', '\\"') for c in categories if c.strip()]
      if cats:
          fm_lines.append(f"categories: [{', '.join(cats)}]")   # YAML
          # or for TOML: fm_lines.append(f'categories = [{", ".join(f\'"{c}"\' for c in cats)}]')
  ```

### Task 2: Backend — extend `GitHubPublishRequest` and wire through worker (AC: 1-10)

- [x] 2.1 In `backend/app/routers/publishing.py`, extend `GitHubPublishRequest`:
  ```python
  class GitHubPublishRequest(BaseModel):
      mode: str
      author: str | None = None
      categories: list[str] | None = None

      @field_validator("mode")
      @classmethod
      def validate_mode(cls, v: str) -> str:
          if v not in ("pr", "commit"):
              raise ValueError("mode must be 'pr' or 'commit'")
          return v
  ```

- [x] 2.2 In the router endpoint, pass the new fields to the background task:
  ```python
  background_tasks.add_task(
      publish_github_job, job.id, campaign_id, body.mode,
      body.author, body.categories
  )
  ```

- [x] 2.3 In `backend/app/workers/publish.py`, update `publish_github_job` signature:
  ```python
  async def publish_github_job(
      job_id: UUID,
      campaign_id: UUID,
      mode: str,
      author: str | None = None,
      categories: list[str] | None = None,
  ) -> None:
  ```

- [x] 2.4 Pass through to `generate_github_post_file`:
  ```python
  file_path, file_content, commit_message, title = await generate_github_post_file(
      campaign, cred, db, author=author, categories=categories
  )
  ```

### Task 3: Frontend — update `buildFrontMatterPreview` (AC: 4, 11)

**Use `/web-uiux-architect` skill for this task.**

- [x] 3.1 Update `buildFrontMatterPreview` signature and body in `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`:
  ```tsx
  function buildFrontMatterPreview(
    framework: string,
    title: string,
    description: string,
    tags: string[],
    author?: string,
    categories?: string[],
  ): string {
    // Jekyll canonical date: "YYYY-MM-DD HH:MM:SS +0000"
    const nowIso  = new Date().toISOString();
    const jekyllDate = nowIso.replace("T", " ").replace(/\.\d{3}Z$/, " +0000");
    const isoDate    = nowIso.replace(/\.\d{3}Z$/, "Z");  // all other frameworks

    const safe     = title.replace(/"/g, '\\"');
    const safeDesc = description.replace(/\r?\n/g, " ").replace(/"/g, '\\"');
    const tagsYaml = tags.length > 0
      ? `[${tags.map((t) => `"${t.replace(/\r?\n/g, " ").replace(/"/g, '\\"')}"`).join(", ")}]`
      : "";

    if (framework === "jekyll") {
      const catsLine   = categories && categories.length > 0
        ? `\ncategories: [${categories.map((c) => c.replace(/"/g, '\\"')).join(", ")}]`
        : "";
      const tagsLine   = tagsYaml ? `\ntags: ${tagsYaml}` : "";
      const authorLine = author ? `\nauthor: "${author.replace(/"/g, '\\"')}"` : "";
      return `---\nlayout: post\ntitle: "${safe}"\ndate: ${jekyllDate}\ndescription: "${safeDesc}"${catsLine}${tagsLine}${authorLine}\n---`;
    }
    if (framework === "astro") {
      const tagsLine = tagsYaml ? `\ntags: ${tagsYaml}` : "";
      return `---\ntitle: "${safe}"\ndescription: "${safeDesc}"\npubDate: "${isoDate}"\nheroImage: ""${tagsLine}\n---`;
    }
    if (framework === "hugo") {
      const catsLine = categories && categories.length > 0
        ? `\ncategories: [${categories.map((c) => c.replace(/"/g, '\\"')).join(", ")}]`
        : "";
      const tagsLine = tagsYaml ? `\ntags: ${tagsYaml}` : "";
      return `---\ntitle: "${safe}"\ndate: ${isoDate}\ndescription: "${safeDesc}"\ndraft: false${catsLine}${tagsLine}\n---`;
    }
    const tagsLine = tagsYaml ? `\ntags: ${tagsYaml}` : "";
    return `---\ntitle: "${safe}"\ndate: ${isoDate}\ndescription: "${safeDesc}"${tagsLine}\n---`;
  }
  ```

- [x] 3.2 Update the `frontMatterPreview` call site (search for `buildFrontMatterPreview(` in the file):
  ```tsx
  const frontMatterPreview = buildFrontMatterPreview(
    detectedFramework,
    blogTitle,
    campaign.voice_score?.meta_description ?? "",
    frontMatterTags,
    authorOverride.trim() || undefined,
    parsedCategories.length > 0 ? parsedCategories : undefined,
  );
  ```

### Task 4: Frontend — state, client fetch, and input UI (AC: 3, 4, 5, 6, 7, 9)

**Use `/web-uiux-architect` skill for this task.**

- [x] 4.1 Add `clientsApi` to the existing imports in `approval-panel.tsx` (it's already exported from `@/lib/api`).

- [x] 4.2 Add `useQuery` (already imported via TanStack Query) to fetch client name:
  ```tsx
  const { data: clientData } = useQuery({
    queryKey: ["client", campaign.client_id],
    queryFn: () => clientsApi.get(campaign.client_id),
    staleTime: 60_000,
  });
  ```

- [x] 4.3 Add state for the two fields:
  ```tsx
  const [authorOverride, setAuthorOverride]     = useState<string>("");
  const [categoriesInput, setCategoriesInput]   = useState<string>("");
  const authorAutofilledRef                     = useRef(false);

  // One-time autofill from client name once loaded
  useEffect(() => {
    if (clientData?.name && !authorAutofilledRef.current) {
      setAuthorOverride(clientData.name);
      authorAutofilledRef.current = true;
    }
  }, [clientData?.name]);

  // Derived: parse comma-separated categories
  const parsedCategories = categoriesInput
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  ```

- [x] 4.4 Add the two input fields inside the GitHub panel (`{showGitHubPanel && !githubResult && (...)}`), placed **between** the File path block and the "Show front matter" toggle:
  ```tsx
  {/* Author & Categories — Jekyll and Hugo only */}
  {(detectedFramework === "jekyll" || detectedFramework === "hugo") && (
    <div className="grid grid-cols-2 gap-x-6 gap-y-4">

      {/* Author */}
      <div className="space-y-1.5">
        <label
          htmlFor="gh-fm-author"
          className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
        >
          Author
          <span className="ml-1 normal-case font-normal text-[#999999]">optional</span>
        </label>
        <input
          id="gh-fm-author"
          type="text"
          value={authorOverride}
          onChange={(e) => setAuthorOverride(e.target.value)}
          placeholder="e.g. Jane Smith"
          aria-label="Post author written to frontmatter author field"
          className={cn(
            "w-full bg-transparent px-0 py-1.5",
            "border-0 border-b border-[#E5E5E5] text-sm text-[#111111]",
            "placeholder:text-[#BBBBBB]",
            "outline-none focus:border-b-2 focus:border-[#111111]",
            "transition-[border-color,border-width] duration-150",
          )}
        />
      </div>

      {/* Categories */}
      <div className="space-y-1.5">
        <label
          htmlFor="gh-fm-categories"
          className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
        >
          Categories
          <span className="ml-1 normal-case font-normal text-[#999999]">optional</span>
        </label>
        <input
          id="gh-fm-categories"
          type="text"
          value={categoriesInput}
          onChange={(e) => setCategoriesInput(e.target.value)}
          placeholder="guides, facebook"
          aria-label="Post categories for frontmatter, comma-separated slugs"
          className={cn(
            "w-full bg-transparent px-0 py-1.5",
            "border-0 border-b border-[#E5E5E5] text-sm text-[#111111]",
            "placeholder:text-[#BBBBBB]",
            "outline-none focus:border-b-2 focus:border-[#111111]",
            "transition-[border-color,border-width] duration-150",
          )}
        />
        <p className="text-[11px] text-[#999999]">Comma-separated slugs</p>
      </div>

    </div>
  )}
  ```

### Task 5: Frontend — update API call and type (AC: 7, 10)

- [x] 5.1 In `handleConfirmGitHubPublish`, pass the new fields:
  ```tsx
  const { job_id } = await publishingApi.publishGitHub(campaign.id, {
    mode: publishMode,
    author:     authorOverride.trim() || undefined,
    categories: parsedCategories.length > 0 ? parsedCategories : undefined,
  });
  ```

- [x] 5.2 Update `publishGitHub` type in `frontend/lib/api.ts`:
  ```ts
  publishGitHub: (
    campaignId: string,
    body: { mode: "pr" | "commit"; author?: string; categories?: string[] }
  ) => ...
  ```

### Task 6: Tests (AC: 1, 2, 7, 10)

- [x] 6.1 In `backend/tests/services/test_publishing.py`, add/update Jekyll tests:
  - Assert `date:` uses format `YYYY-MM-DD HH:MM:SS +0000` (not `T` separator, not `Z` suffix)
  - Assert voice score tags appear under `tags:` not `categories:`
  - Assert `categories:` is absent when no user categories provided
  - Assert `author:` is absent when `author=None`
  - Assert `author: "Jane Smith"` appears when `author="Jane Smith"`
  - Assert `categories: [guides, facebook]` when `categories=["guides", "facebook"]`
  - Assert double-quote in author or category is YAML-escaped

## Dev Notes

### Critical: what changed and why

The Jekyll block in `generate_github_post_file` had three bugs confirmed against Jekyll's official spec:

1. **Date format**: ISO 8601 (`T` separator, `Z` suffix) is non-canonical for Jekyll. Jekyll's own docs specify `YYYY-MM-DD HH:MM:SS +/-TTTT`. Liquid date filters and some Jekyll plugins fail on the ISO form with GitHub Pages's pinned Jekyll version. Fix: `now_utc.strftime("%Y-%m-%d %H:%M:%S +0000")`.

2. **Tags in wrong field**: `voice_score.tags` (SEO keyword phrases like `"facebook business page"`) was being written to `categories:`. Jekyll's default permalink templates include `/:categories/`, so multi-word phrases produce URL-encoded paths. These phrases belong in `tags:`. The epics spec (epics.md line 1529) said `categories: [{tags from voice profile}]` — that spec is now superseded by this story.

3. **No `tags:` field**: The `tags:` field was never written for Jekyll (only `categories:`). Now voice tags go there.

The `author:` and `categories:` fields are new optional user inputs, not previously specified.

### File locations (verified)

| File | Role |
|---|---|
| `backend/app/services/publishing.py` | `generate_github_post_file()` — all framework frontmatter logic |
| `backend/app/routers/publishing.py` | `GitHubPublishRequest` model + endpoint |
| `backend/app/workers/publish.py` | `publish_github_job()` background worker |
| `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` | GitHub panel UI, `buildFrontMatterPreview`, `handleConfirmGitHubPublish` |
| `frontend/lib/api.ts` | `publishingApi.publishGitHub` type |
| `backend/tests/services/test_publishing.py` | Service-level publish tests |

### Backend: no new DB import needed

The author pre-fill is handled entirely on the frontend via `useQuery` + `clientsApi.get()`. The backend `generate_github_post_file` simply receives `author` as a plain string (or `None`) — no extra DB lookup required.

### Frontend: client name fetch pattern

- Use `useQuery({ queryKey: ["client", campaign.client_id], queryFn: () => clientsApi.get(campaign.client_id), staleTime: 60_000 })` — `clientsApi.get` already exists in `lib/api.ts`
- Autofill via a one-time `useEffect` + `useRef(false)` guard so user edits are not overwritten
- `ClientResponse` (from `lib/types.ts`) has `name: string` — that's the pre-fill value

### Frontend: live preview wiring

`frontMatterPreview` is a derived value (not state). Because `authorOverride` and `parsedCategories` are in state, any change to either input causes a re-render, which recomputes `frontMatterPreview`, which the `<pre>` block renders. No `useEffect` needed for the preview.

### Hugo categories field order

In the Hugo YAML branch, insert `categories` **after** `tags` (not before). In the Hugo TOML branch, the same. This mirrors the conventional Hugo frontmatter field ordering seen in popular themes (PaperMod, Congo, Ananke).

### Inputs: reset behavior

When the user clicks Cancel (`setShowGitHubPanel(false)`), the inputs **retain** their values. On panel re-open the user sees what they last typed. This is intentional (less surprising than a reset). If the client name changes between renders, the autofill does NOT overwrite existing user edits because of the `authorAutofilledRef` guard.

### Tests: date assertion

When asserting the date format in tests, avoid snapshot matching the exact timestamp (it will be wrong in CI). Instead assert:
```python
assert "date: " in front_matter
date_line = next(l for l in front_matter.splitlines() if l.startswith("date: "))
import re
assert re.match(r"date: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \+0000", date_line), date_line
```

### YAML injection: existing escaping is sufficient

The `replace('"', '\\"')` pattern already in place for title/description is applied to `author` and each `categories` entry. This prevents YAML injection via double-quotes. No additional sanitization is needed for these optional fields (they are user-controlled, not AI-generated).

### Project Structure Notes

- No new files created — all changes are in existing files.
- The `categories` field on `GitHubPublishRequest` is optional (`list[str] | None = None`) so the endpoint remains backward-compatible with existing clients that don't send it.
- `author` is a flat string in frontmatter (not an object) — consistent with Jekyll/Hugo conventions; differs from next-blog-starter's `author: { name, picture }` pattern but that framework is not in scope here.

### References

- Jekyll official frontmatter spec: https://jekyllrb.com/docs/front-matter/ (date format, tags vs categories)
- Hugo frontmatter taxonomies: https://gohugo.io/content-management/front-matter/
- Current Jekyll block: `backend/app/services/publishing.py` lines 84–110
- Current Hugo block: `backend/app/services/publishing.py` lines 256–320
- `GitHubPublishRequest`: `backend/app/routers/publishing.py` lines 673–681
- Worker call site: `backend/app/workers/publish.py` line 47
- `buildFrontMatterPreview`: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` lines 62–84
- GitHub panel UI: `frontend/app/(app)/campaigns/[id]/approval-panel.tsx` lines 553–652
- `publishGitHub` type: `frontend/lib/api.ts` line 194
- `clientsApi.get`: `frontend/lib/api.ts` line 55
- `ClientResponse.name`: `frontend/lib/types.ts` line 33
- Previous story learnings: `_bmad-output/implementation-artifacts/11-3-github-frontmatter-description-tags.md` (YAML injection pattern, tag coercion guard)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Rewrote Jekyll frontmatter block in `generate_github_post_file`: Jekyll date now uses `strftime("%Y-%m-%d %H:%M:%S +0000")`, voice tags moved from `categories:` to `tags:`, new `author` and `categories` params added (both default to None for backward compatibility).
- Hugo YAML and TOML branches both support the new optional `categories` param, inserted after the existing `tags` block.
- `GitHubPublishRequest` extended with `author: str | None` and `categories: list[str] | None`; router passes them to `publish_github_job`; worker passes them through to `generate_github_post_file`.
- `buildFrontMatterPreview` updated: Jekyll branch uses the `T`→space / `Z`→` +0000` date transform; both Jekyll and Hugo branches accept optional `author` and `categories` args; Jekyll no longer puts voice tags in `categories:`.
- `useQuery` + `clientsApi.get` added to `approval-panel.tsx` to pre-fill Author from client name; `useRef` guard prevents overwriting user edits on re-render.
- Author and Categories inputs rendered in both the primary and republish GitHub panels (Jekyll and Hugo only); panels for other frameworks show no new inputs.
- `publishGitHub` API type extended with `author?: string; categories?: string[]`.
- Fixed existing test `test_publish_github_jekyll_calls_create_file_commit_with_front_matter` to assert `tags:` not `categories:` for voice tags.
- Added 8 new tests covering: date format regex, voice tags→tags field, no author when None, author written correctly, no categories when None, categories list, double-quote YAML escape in author, double-quote YAML escape in category.
- All 30 service tests pass; 0 TypeScript errors introduced.

### File List

- `backend/app/services/publishing.py`
- `backend/app/routers/publishing.py`
- `backend/app/workers/publish.py`
- `frontend/app/(app)/campaigns/[id]/approval-panel.tsx`
- `frontend/lib/api.ts`
- `backend/tests/services/test_publishing.py`

## Change Log

- 2026-07-10: Story 11.5 implemented — Jekyll frontmatter date fix, voice tags→`tags:` field, author/categories optional inputs for Jekyll/Hugo GitHub panel (claude-sonnet-4-6)

### Review Findings

- [x] [Review][Patch] P1 (HIGH): Newline `\n`/`\r` not stripped from `author`/`categories` — YAML injection risk [backend/app/services/publishing.py:~100-117, ~311-334]
- [x] [Review][Patch] P2 (MEDIUM): `author` field missing from Hugo TOML and YAML blocks — UI shows Author input for Hugo but backend never wrote it [backend/app/services/publishing.py:~315, ~334]
- [x] [Review][Patch] P3 (LOW): CSS typo `focus:border[#111111]` (missing `-`) in republish categories input — dismissed, false positive (file correct)
- [x] [Review][Patch] P4 (LOW): Dead `_common_jekyll_patches()` helper defined but never used [backend/tests/services/test_publishing.py:~704]
- [x] [Review][Patch] P5 (LOW): Whitespace-only `author` passes `if author:` truthiness check [backend/app/services/publishing.py:~115]
- [x] [Review][Patch] P6 (LOW): `jekyll_date` computed unconditionally outside Jekyll block [backend/app/services/publishing.py:~85]
- [x] [Review][Defer] D1 (LOW): Preview date computed at render time vs job execution time — pre-existing architectural choice, pre-existing [frontend/app/(app)/campaigns/[id]/approval-panel.tsx:~72]
- [x] [Review][Defer] D2 (MEDIUM): Unquoted category items in YAML flow sequences — intentional design per spec AC7 example (`categories: [guides, facebook]`), pre-existing
