"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Eye, EyeOff, History, ImageOff, Loader2, RotateCcw } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { articlesApi, imagesApi } from "@/lib/api";
import { APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { Modal } from "@/components/ui/Modal";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { BlogEditor, BlogEditorHandle, _DOMPURIFY_CONFIG } from "@/components/campaigns/BlogEditor";
import { cn } from "@/lib/utils";
import type { Article, RevisionListItem, RevisionDetail } from "@/lib/types";

const META_MAX = 160;

interface ArticleEditorProps {
  articleId: string;
}

// ── helpers ──────────────────────────────────────────────────────────────────

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function sourceBadge(source: string) {
  const cls = {
    initial: "bg-transparent border border-[#E5E5E5] text-[#555555]",
    edit: "bg-transparent border border-[#111111] text-[#111111]",
    restore: "bg-[#FFF1B8] border border-[#111111] text-[#111111]",
  }[source] ?? "bg-transparent border border-[#E5E5E5] text-[#555555]";
  return (
    <span className={cn("px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.06em]", cls)}>
      {source}
    </span>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function ArticleEditor({ articleId }: ArticleEditorProps) {
  const addToast = useUIStore((s) => s.addToast);
  const qc = useQueryClient();

  // ── fetch article ──────────────────────────────────────────────────────────
  const { data: article, isLoading, isError } = useQuery<Article>({
    queryKey: ["article", articleId],
    queryFn: () => articlesApi.get(articleId),
    staleTime: 30_000,
  });

  // ── fetch revisions ────────────────────────────────────────────────────────
  const { data: revisionsData } = useQuery({
    queryKey: ["article-revisions", articleId],
    queryFn: () => articlesApi.listRevisions(articleId),
    staleTime: 30_000,
    enabled: !!article,
  });

  const revisions = revisionsData?.items ?? [];
  const maxRevNum = revisions.length > 0 ? revisions[0].revision_number : 0;

  // ── local form state ──────────────────────────────────────────────────────
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [metaDescription, setMetaDescription] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [category, setCategory] = useState("");
  const [author, setAuthor] = useState("");

  // Track loaded slug to detect changes
  const loadedSlug = useRef<string>("");

  // ── editor ref ─────────────────────────────────────────────────────────────
  const editorRef = useRef<BlogEditorHandle>(null);

  // ── initialise form from article ──────────────────────────────────────────
  useEffect(() => {
    if (!article) return;
    setTitle(article.title ?? "");
    setSlug(article.slug ?? "");
    loadedSlug.current = article.slug ?? "";
    setExcerpt(article.excerpt ?? "");
    setMetaDescription(article.meta_description ?? "");
    setTagsInput(Array.isArray(article.tags) ? article.tags.join(", ") : "");
    setCategory(article.category ?? "");
    setAuthor(article.author ?? "");
  }, [article]);

  // ── featured image ─────────────────────────────────────────────────────────
  const [isUploadingFeatured, setIsUploadingFeatured] = useState(false);
  const featuredFileRef = useRef<HTMLInputElement>(null);

  const handleFeaturedImageChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !article) return;
    e.target.value = "";
    setIsUploadingFeatured(true);
    try {
      const { url } = await imagesApi.upload(article.client_id, file);
      await articlesApi.patch(articleId, { featured_image_url: url });
      qc.setQueryData(["article", articleId], (prev: Article | undefined) =>
        prev ? { ...prev, featured_image_url: url } : prev
      );
      addToast("Featured image updated.", "success");
    } catch (err) {
      addToast(err instanceof APIError ? err.message : "Failed to update featured image.", "error");
    } finally {
      setIsUploadingFeatured(false);
    }
  }, [article, articleId, qc, addToast]);

  // ── slug-change dialog ─────────────────────────────────────────────────────
  const [showSlugDialog, setShowSlugDialog] = useState(false);
  const [pendingPatch, setPendingPatch] = useState<Record<string, unknown> | null>(null);
  const saveBtnRef = useRef<HTMLButtonElement>(null);

  // ── save mutation ──────────────────────────────────────────────────────────
  const saveMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      articlesApi.patch(articleId, data as Parameters<typeof articlesApi.patch>[1]),
    onSuccess: (updated) => {
      qc.setQueryData(["article", articleId], updated);
      loadedSlug.current = updated.slug;
      setSlug(updated.slug);
      addToast("Article updated.", "success");
      try {
        qc.invalidateQueries({ queryKey: ["article-revisions", articleId] });
      } catch {
        // invalidate errors are non-fatal
      }
      try {
        qc.invalidateQueries({ queryKey: ["articles"] });
      } catch {
        // invalidate errors are non-fatal
      }
    },
    onError: (err) => {
      addToast(err instanceof APIError ? err.message : "Failed to save article.", "error");
    },
  });

  // ── build patch and handle slug-change gate ────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!article) return;

    const html = editorRef.current?.getCurrentHtml() ?? "";
    // DOMPurify sanitization before sending (mirrors BlogEditor's approve flow)
    let sanitizedHtml = html;
    if (html) {
      try {
        const { default: DOMPurify } = await import("dompurify");
        sanitizedHtml = DOMPurify.sanitize(html, _DOMPURIFY_CONFIG);
      } catch {
        // DOMPurify not available on server; server will re-sanitize anyway
        sanitizedHtml = html;
      }
    }

    const tags = tagsInput
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const patch: Record<string, unknown> = {
      title: title.trim() || undefined,
      html: sanitizedHtml || undefined,
      excerpt: excerpt.trim() || undefined,
      meta_description: metaDescription.trim() || undefined,
      tags: tags.length > 0 ? tags : undefined,
      category: category.trim() || undefined,
      author: author.trim() || undefined,
      slug: slug.trim() || undefined,
    };

    // If slug changed, show confirmation dialog
    if (slug.trim() && slug.trim() !== loadedSlug.current) {
      setPendingPatch(patch);
      setShowSlugDialog(true);
      return;
    }

    saveMutation.mutate(patch);
  }, [article, title, slug, excerpt, metaDescription, tagsInput, category, author, saveMutation]);

  // ── visibility toggle ──────────────────────────────────────────────────────
  const toggleMutation = useMutation({
    mutationFn: (newStatus: string) => articlesApi.patch(articleId, { status: newStatus }),
    onMutate: async (newStatus) => {
      // Optimistic update
      await qc.cancelQueries({ queryKey: ["article", articleId] });
      const prev = qc.getQueryData<Article>(["article", articleId]);
      if (prev) {
        qc.setQueryData(["article", articleId], { ...prev, status: newStatus as Article["status"] });
      }
      return { prev };
    },
    onError: (_err, _newStatus, ctx) => {
      if (ctx?.prev) qc.setQueryData(["article", articleId], ctx.prev);
      addToast("Failed to update visibility.", "error");
    },
    onSuccess: (updated) => {
      qc.setQueryData(["article", articleId], updated);
      try {
        qc.invalidateQueries({ queryKey: ["articles"] });
      } catch {
        // non-fatal
      }
    },
  });

  // ── revision preview ───────────────────────────────────────────────────────
  const [previewRevNum, setPreviewRevNum] = useState<number | null>(null);
  const [previewData, setPreviewData] = useState<RevisionDetail | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [showRestoreDialog, setShowRestoreDialog] = useState(false);
  const [restoreRevNum, setRestoreRevNum] = useState<number | null>(null);

  const openPreview = useCallback(async (revNum: number) => {
    setPreviewRevNum(revNum);
    setIsLoadingPreview(true);
    try {
      const data = await articlesApi.getRevision(articleId, revNum);
      // Sanitize revision HTML client-side before rendering (belt-and-suspenders)
      let safeHtml = data.html;
      try {
        const { default: DOMPurify } = await import("dompurify");
        safeHtml = DOMPurify.sanitize(data.html, _DOMPURIFY_CONFIG);
      } catch {
        // DOMPurify unavailable (SSR) — server-sanitized content is still safe
      }
      setPreviewData({ ...data, html: safeHtml });
    } catch {
      addToast("Failed to load revision preview.", "error");
      setPreviewRevNum(null);
    } finally {
      setIsLoadingPreview(false);
    }
  }, [articleId, addToast]);

  // ── restore mutation ───────────────────────────────────────────────────────
  const restoreMutation = useMutation({
    mutationFn: (revNum: number) => articlesApi.restoreRevision(articleId, revNum),
    onSuccess: (updated, revNum) => {
      qc.setQueryData(["article", articleId], updated);
      loadedSlug.current = updated.slug;
      setTitle(updated.title ?? "");
      setSlug(updated.slug ?? "");
      setExcerpt(updated.excerpt ?? "");
      setMetaDescription(updated.meta_description ?? "");
      setTagsInput(Array.isArray(updated.tags) ? updated.tags.join(", ") : "");
      setCategory(updated.category ?? "");
      setAuthor(updated.author ?? "");
      try {
        qc.invalidateQueries({ queryKey: ["article-revisions", articleId] });
      } catch {
        // non-fatal
      }
      try {
        qc.invalidateQueries({ queryKey: ["articles"] });
      } catch {
        // non-fatal
      }
      // Determine new highest revision
      const newRevisions = qc.getQueryData<{ items: RevisionListItem[] }>(["article-revisions", articleId]);
      const newMax = newRevisions?.items?.[0]?.revision_number ?? revNum;
      addToast(`Restored to revision ${revNum}. Saved as revision ${newMax}.`, "success");
      setPreviewRevNum(null);
      setPreviewData(null);
      setRestoreRevNum(null);
    },
    onError: (err) => {
      addToast(err instanceof APIError ? err.message : "Restore failed.", "error");
    },
  });

  // ── derived state ──────────────────────────────────────────────────────────
  const currentStatus = qc.getQueryData<Article>(["article", articleId])?.status ?? article?.status;
  const isVisible = currentStatus === "published";
  const isSaving = saveMutation.isPending;

  // ── loading / error states ────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 bg-[#E5E5E5] animate-pulse" />
        <div className="h-4 w-48 bg-[#E5E5E5] animate-pulse" />
        <div className="h-64 bg-[#E5E5E5] animate-pulse" />
      </div>
    );
  }

  if (isError || !article) {
    return (
      <div className="space-y-4">
        <Link href="/blog" className="inline-flex items-center gap-2 text-sm text-[#555555] hover:text-[#111111]">
          <ArrowLeft className="size-4" aria-hidden="true" /> Back to Blog
        </Link>
        <p className="text-sm text-[#8B0000]">Failed to load article. Please go back and try again.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-sm text-[#555555] hover:text-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 focus-visible:outline-none"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Blog
        </Link>
      </div>

      {/* Two-column layout */}
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main column */}
        <div className="flex-1 min-w-0">
          {/* Title input */}
          <div className="mb-4">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              aria-label="Article title"
              placeholder="Article title"
              className="w-full text-2xl font-semibold text-[#111111] bg-transparent border-0 border-b border-transparent focus:border-b focus:border-[#111111] focus:outline-none py-2 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
            />
          </div>

          {/* Blog editor */}
          <div className="border border-[#111111]">
            <BlogEditor
              ref={editorRef}
              initialHtml={article.html}
              campaignId=""
              clientId={article.client_id}
              readOnly={false}
              hideSaveButton={true}
            />
          </div>

          {/* Save button */}
          <div className="mt-4 flex items-center gap-3">
            <button
              ref={saveBtnRef}
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className={cn(
                "inline-flex items-center gap-2 px-5 py-2.5 bg-[#111111] text-white text-sm font-medium border border-transparent",
                "shadow-[4px_4px_0px_0px_var(--ink,#111111)]",
                "active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all duration-150",
                "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
                "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
              )}
            >
              {isSaving && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
              {isSaving ? "Saving..." : "Save changes"}
            </button>
          </div>
        </div>

        {/* Right rail */}
        <div className="lg:w-80 shrink-0 space-y-4">
          {/* Featured image card */}
          <div className="border border-[#111111] p-4 space-y-3">
            <h2 className="font-display text-sm font-bold text-[#111111] uppercase tracking-[0.06em]">
              Featured image
            </h2>
            {/* Hidden file input */}
            <input
              ref={featuredFileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              aria-hidden="true"
              tabIndex={-1}
              onChange={handleFeaturedImageChange}
            />
            {article.featured_image_url ? (
              <img
                src={article.featured_image_url}
                alt="Current featured image"
                className="w-full aspect-video object-cover border border-[#111111]"
              />
            ) : (
              <div className="w-full aspect-video border border-[#E5E5E5] flex flex-col items-center justify-center gap-2">
                <ImageOff className="size-6 text-[#BBBBBB]" aria-hidden="true" />
                <span className="text-[11px] text-[#BBBBBB]">No featured image</span>
              </div>
            )}
            <button
              type="button"
              onClick={() => featuredFileRef.current?.click()}
              disabled={isUploadingFeatured}
              className={cn(
                "w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium",
                "border border-[#111111] hover:bg-[#111111] hover:text-white transition-colors",
                "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
                "disabled:opacity-40 disabled:cursor-not-allowed min-h-[44px]",
              )}
            >
              {isUploadingFeatured && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
              {isUploadingFeatured ? "Uploading..." : "Replace"}
            </button>
          </div>

          {/* Details card */}
          <div className="border border-[#111111] p-4 space-y-4">
            <h2 className="font-display text-sm font-bold text-[#111111] uppercase tracking-[0.06em]">
              Details
            </h2>

            {/* Slug */}
            <div className="space-y-1.5">
              <label htmlFor="article-slug" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                Slug
              </label>
              <input
                id="article-slug"
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value.toLowerCase())}
                placeholder="article-slug"
                className="w-full font-mono text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
              />
            </div>

            {/* Excerpt */}
            <div className="space-y-1.5">
              <label htmlFor="article-excerpt" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                Excerpt
              </label>
              <textarea
                id="article-excerpt"
                rows={2}
                value={excerpt}
                onChange={(e) => setExcerpt(e.target.value)}
                placeholder="Short summary…"
                className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 resize-none transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
              />
            </div>

            {/* Meta description with char counter */}
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between">
                <label htmlFor="article-meta" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                  Meta description
                </label>
                <span
                  id="article-meta-counter"
                  className={cn(
                    "font-mono text-[11px]",
                    metaDescription.length > META_MAX ? "text-[#8B0000]" : "text-[#555555]",
                  )}
                  aria-live="polite"
                >
                  {metaDescription.length} / {META_MAX}
                </span>
              </div>
              <textarea
                id="article-meta"
                rows={2}
                value={metaDescription}
                onChange={(e) => setMetaDescription(e.target.value)}
                aria-describedby="article-meta-counter"
                placeholder="SEO meta description…"
                className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 resize-none transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
              />
            </div>

            {/* Tags */}
            <div className="space-y-1.5">
              <label htmlFor="article-tags" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                Tags
                <span className="ml-1 normal-case font-normal text-[#999999]">comma-separated</span>
              </label>
              <input
                id="article-tags"
                type="text"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="seo, marketing, tips"
                className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
              />
              {tagsInput && (
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {tagsInput.split(",").map((t) => t.trim()).filter(Boolean).map((tag) => (
                    <span key={tag} className="px-2 py-0.5 border border-[#111111] text-[11px] font-medium text-[#111111]">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Category */}
            <div className="space-y-1.5">
              <label htmlFor="article-category" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                Category
              </label>
              <input
                id="article-category"
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="e.g. Marketing"
                className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
              />
            </div>

            {/* Author */}
            <div className="space-y-1.5">
              <label htmlFor="article-author" className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">
                Author
              </label>
              <input
                id="article-author"
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="e.g. Jane Smith"
                className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB]"
              />
            </div>

            {/* Visibility toggle */}
            <div className="flex items-center justify-between pt-1 min-h-[44px]">
              <div className="flex items-center gap-2">
                {isVisible
                  ? <Eye className="size-4 text-[#111111]" aria-hidden="true" />
                  : <EyeOff className="size-4 text-[#555555]" aria-hidden="true" />}
                <span className="text-sm text-[#111111]">Visible in delivery API</span>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={isVisible}
                onClick={() => toggleMutation.mutate(isVisible ? "hidden" : "published")}
                disabled={toggleMutation.isPending}
                aria-label={isVisible ? "Hide from delivery API" : "Show in delivery API"}
                className={cn(
                  "relative inline-flex h-5 w-9 items-center border border-[#111111] transition-colors duration-200",
                  "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 focus-visible:outline-none",
                  isVisible ? "bg-[#111111]" : "bg-transparent",
                  toggleMutation.isPending && "opacity-50 cursor-not-allowed",
                )}
              >
                <span
                  className={cn(
                    "inline-block h-3 w-3 border border-[#111111] transition-transform duration-200",
                    isVisible ? "translate-x-5 bg-white" : "translate-x-1 bg-[#111111]",
                  )}
                />
              </button>
            </div>
          </div>

          {/* History card */}
          <div className="border border-[#111111] p-4 space-y-3">
            <div className="flex items-center gap-2">
              <History className="size-4 text-[#111111]" aria-hidden="true" />
              <h2 className="font-display text-sm font-bold text-[#111111] uppercase tracking-[0.06em]">
                History
              </h2>
            </div>

            {revisions.length === 0 && (
              <p className="text-[13px] text-[#555555]">No revisions yet.</p>
            )}

            {revisions.map((rev) => {
              const isCurrent = rev.revision_number === maxRevNum;
              return (
                <div
                  key={rev.revision_number}
                  className="flex items-center gap-2 min-h-[44px]"
                >
                  <History className="size-3.5 text-[#555555] shrink-0" aria-hidden="true" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[13px] font-semibold text-[#111111]">
                        Rev {rev.revision_number}
                      </span>
                      {sourceBadge(rev.source)}
                    </div>
                    <p className="font-mono text-[11px] text-[#555555]">
                      {relativeDate(rev.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      aria-label={`Preview revision ${rev.revision_number}`}
                      onClick={() => openPreview(rev.revision_number)}
                      className="p-1.5 text-[#555555] hover:text-[#111111] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 focus-visible:outline-none"
                    >
                      <Eye className="size-4" aria-hidden="true" />
                    </button>
                    {isCurrent ? (
                      <span className="text-[11px] font-medium text-[#2E4F2E] px-1.5 py-0.5 border border-[#2E4F2E]">
                        Current
                      </span>
                    ) : (
                      <button
                        type="button"
                        aria-label={`Restore revision ${rev.revision_number}`}
                        onClick={() => { setRestoreRevNum(rev.revision_number); setShowRestoreDialog(true); }}
                        disabled={restoreMutation.isPending}
                        className="p-1.5 text-[#555555] hover:text-[#111111] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 focus-visible:outline-none disabled:opacity-40"
                      >
                        <RotateCcw className="size-4" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Slug change confirmation dialog */}
      <ConfirmModal
        isOpen={showSlugDialog}
        onClose={() => { setShowSlugDialog(false); setPendingPatch(null); }}
        onConfirm={() => {
          setShowSlugDialog(false);
          if (pendingPatch) saveMutation.mutate(pendingPatch);
          setPendingPatch(null);
        }}
        title="Change the article slug?"
        description={`Existing links to "/${loadedSlug.current}" will break — customer sites fetching by the old slug will receive a 404. Are you sure you want to change it?`}
        confirmLabel="Change slug"
        confirmVariant="danger"
        triggerRef={saveBtnRef}
      />

      {/* Revision preview modal */}
      <Modal
        isOpen={previewRevNum !== null}
        onClose={() => { setPreviewRevNum(null); setPreviewData(null); }}
        title={previewData ? `Revision ${previewData.revision_number} — ${previewData.source}` : "Loading revision…"}
        className="max-w-3xl"
      >
        {isLoadingPreview && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="size-6 animate-spin text-[#555555]" aria-hidden="true" />
          </div>
        )}
        {previewData && !isLoadingPreview && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 pb-3 border-b border-[#E5E5E5]">
              {sourceBadge(previewData.source)}
              <span className="font-mono text-[11px] text-[#555555]">
                {new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(
                  new Date(previewData.created_at),
                )}
              </span>
            </div>
            <h3 className="font-display text-lg font-bold text-[#111111]">{previewData.title}</h3>
            {/* Sanitized preview */}
            <div
              className="prose prose-sm max-w-none prose-headings:font-display prose-headings:text-ink prose-a:text-ink border border-[#E5E5E5] p-4 max-h-[400px] overflow-y-auto"
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{ __html: previewData.html }}
            />
            {previewRevNum !== null && previewRevNum !== maxRevNum && (
              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowRestoreDialog(true);
                    setRestoreRevNum(previewRevNum);
                    setPreviewRevNum(null);
                    setPreviewData(null);
                  }}
                  className={cn(
                    "inline-flex items-center gap-2 px-5 py-2.5 bg-[#111111] text-white text-sm font-medium",
                    "shadow-[4px_4px_0px_0px_#111111] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all",
                    "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
                  )}
                >
                  Restore this version
                </button>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Restore confirmation dialog */}
      <ConfirmModal
        isOpen={showRestoreDialog}
        onClose={() => { setShowRestoreDialog(false); setRestoreRevNum(null); }}
        onConfirm={() => {
          if (restoreRevNum !== null) restoreMutation.mutate(restoreRevNum);
          setShowRestoreDialog(false);
        }}
        title="Restore this revision?"
        description={`This will create a new revision with the content from revision ${restoreRevNum}. The current version will be preserved in history.`}
        confirmLabel="Restore"
        confirmVariant="primary"
        isLoading={restoreMutation.isPending}
      />
    </div>
  );
}
