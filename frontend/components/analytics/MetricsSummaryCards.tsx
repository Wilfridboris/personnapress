"use client";

import { ExternalLink } from "lucide-react";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { Skeleton } from "@/components/ui/Skeleton";
import type { ClientSummary } from "@/hooks/usePostMetrics";
import { fmt } from "@/lib/formatters";

interface CardProps {
  label: string;
  children: React.ReactNode;
}

function SummaryCard({ label, children }: CardProps) {
  return (
    <div className="bg-white border border-border shadow-brutal p-5 flex flex-col gap-1 min-w-0">
      <p className="font-mono text-xs uppercase tracking-widest text-graphite">{label}</p>
      <div className="font-display text-2xl font-bold text-ink truncate">{children}</div>
    </div>
  );
}

interface Props {
  summary: ClientSummary | undefined;
  isLoading: boolean;
}

export function MetricsSummaryCards({ summary, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8" aria-label="Loading analytics summary">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  const bestPostLabel = summary?.best_post
    ? summary.best_post.campaign_title
    : "None yet";

  return (
    <div
      className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
      aria-label="Analytics summary"
    >
      <SummaryCard label="Total Impressions">
        {fmt(summary?.total_impressions)}
      </SummaryCard>

      <SummaryCard label="Total Engagements">
        {fmt(summary?.total_engagements)}
      </SummaryCard>

      <SummaryCard label="Posts Tracked">
        {summary?.posts_tracked ?? 0}
      </SummaryCard>

      <SummaryCard label="Best-Performing Post">
        {summary?.best_post ? (
          <span className="flex items-start gap-1.5 min-w-0">
            <PlatformIcon
              platform={summary.best_post.platform}
              className="size-4 shrink-0 mt-0.5"
              color="brand"
            />
            <span className="flex flex-col min-w-0">
              <span className="text-sm font-sans font-medium text-ink truncate leading-tight">
                {bestPostLabel}
              </span>
              <span className="text-xs font-mono text-graphite">
                {fmt(summary.best_post.engagements)} engagements
              </span>
              {summary.best_post.permalink && (
                <a
                  href={summary.best_post.permalink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-mono text-ink underline underline-offset-2 hover:no-underline focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1 mt-0.5"
                  aria-label={`Open ${bestPostLabel} on platform`}
                >
                  View post
                  <ExternalLink className="size-3" aria-hidden="true" />
                </a>
              )}
            </span>
          </span>
        ) : (
          <span className="text-sm font-mono text-graphite">None yet</span>
        )}
      </SummaryCard>
    </div>
  );
}
