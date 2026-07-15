"use client";

import Link from "next/link";
import { EyeOff, Newspaper } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { articlesApi } from "@/lib/api";
import { useClientStore } from "@/lib/stores/useClientStore";
import type { ArticleListItem } from "@/lib/types";

// ── shimmer skeleton ─────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 px-6 py-4 border-b border-[#E5E5E5] animate-pulse">
      <div className="h-4 bg-[#E5E5E5] rounded-none flex-1" />
      <div className="h-4 w-20 bg-[#E5E5E5] rounded-none" />
      <div className="h-4 w-24 bg-[#E5E5E5] rounded-none" />
    </div>
  );
}

// ── status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const isPublished = status === "published";
  return (
    <span
      className={
        isPublished
          ? "inline-flex items-center gap-1 px-2 py-0.5 border border-[#111111] text-[11px] font-medium text-[#2E4F2E] uppercase tracking-[0.06em]"
          : "inline-flex items-center gap-1 px-2 py-0.5 border border-[#E5E5E5] text-[11px] font-medium text-[#555555] uppercase tracking-[0.06em]"
      }
    >
      {!isPublished && <EyeOff className="size-3" aria-hidden="true" />}
      {isPublished ? "Published" : "Hidden"}
    </span>
  );
}

// ── article row ──────────────────────────────────────────────────────────────
function ArticleRow({ article }: { article: ArticleListItem }) {
  const pubDate = new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(
    new Date(article.published_at),
  );
  const updatedDate = new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(
    new Date(article.updated_at),
  );

  return (
    <Link
      href={`/blog/${article.id}`}
      className="flex items-center gap-4 px-6 py-4 border-b border-[#E5E5E5] min-h-[44px] hover:bg-[#FFF1B8]/30 transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 focus-visible:outline-none"
    >
      <span className="flex-1 font-display font-semibold text-[#111111] text-sm leading-snug truncate">
        {article.title}
      </span>
      <span className="font-mono text-[13px] text-[#555555] hidden sm:block truncate max-w-[180px]">
        {article.slug}
      </span>
      <StatusBadge status={article.status} />
      <span className="font-mono text-[12px] text-[#555555] hidden md:block whitespace-nowrap">
        {pubDate}
      </span>
      <span className="font-mono text-[12px] text-[#555555] hidden lg:block whitespace-nowrap">
        Updated {updatedDate}
      </span>
    </Link>
  );
}

// ── empty state ──────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="border border-[#111111] p-10 flex flex-col items-center gap-4 text-center">
      <Newspaper className="size-10 text-[#555555]" aria-hidden="true" />
      <h2 className="font-display text-xl font-bold text-[#111111]">No articles yet</h2>
      <p className="text-sm text-[#555555] max-w-sm">
        Publish a campaign and it appears here as an article you can keep editing.
      </p>
      <Link
        href="/campaigns"
        className="mt-2 text-sm text-[#111111] underline underline-offset-2 hover:text-[#555555] focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 focus-visible:outline-none"
      >
        Go to Campaigns
      </Link>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────
export function BlogList() {
  const { activeClientId, isInitialized } = useClientStore();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["articles", activeClientId],
    queryFn: () => articlesApi.list(activeClientId!),
    enabled: !!activeClientId && isInitialized,
    staleTime: 30_000,
  });

  return (
    <div>
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold text-[#111111] mb-1">Blog</h1>
        <p className="text-sm text-[#555555] font-mono">Your published articles — editable after publishing.</p>
      </header>

      <div className="border border-[#111111]">
        {/* Column headers */}
        <div className="flex items-center gap-4 px-6 py-2 border-b border-[#E5E5E5] bg-[#F9F9F6]">
          <span className="flex-1 text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">Title</span>
          <span className="font-mono text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555] hidden sm:block w-[180px]">Slug</span>
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555] w-[80px]">Status</span>
          <span className="font-mono text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555] hidden md:block w-[100px]">Published</span>
          <span className="font-mono text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555] hidden lg:block w-[120px]">Updated</span>
        </div>

        {/* Loading */}
        {(isLoading || !isInitialized) && (
          <>
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </>
        )}

        {/* Error */}
        {isError && !isLoading && (
          <p className="px-6 py-8 text-sm text-[#8B0000]">
            Failed to load articles. Please refresh.
          </p>
        )}

        {/* No active client */}
        {isInitialized && !activeClientId && (
          <p className="px-6 py-8 text-sm text-[#555555]">
            Select a client to view their blog articles.
          </p>
        )}

        {/* Empty */}
        {isInitialized && activeClientId && !isLoading && !isError && data?.items.length === 0 && (
          <div className="px-6 py-10">
            <EmptyState />
          </div>
        )}

        {/* Articles */}
        {data?.items.map((article) => (
          <ArticleRow key={article.id} article={article} />
        ))}
      </div>
    </div>
  );
}
