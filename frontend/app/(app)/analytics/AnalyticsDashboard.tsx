"use client";

import { useClientStore } from "@/lib/stores/useClientStore";
import { useAnalyticsSummary, usePostMetrics } from "@/hooks/usePostMetrics";
import { MetricsSummaryCards } from "@/components/analytics/MetricsSummaryCards";
import { PostMetricsTable } from "@/components/analytics/PostMetricsTable";

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return "";
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60_000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return "just now";
}

export function AnalyticsDashboard() {
  const activeClientId = useClientStore((s) => s.activeClientId);

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
  } = useAnalyticsSummary(activeClientId);

  const {
    data: postMetrics,
    isLoading: postsLoading,
    isError: postsError,
  } = usePostMetrics(activeClientId);

  const freshness =
    summary?.freshest_captured_at ?? postMetrics?.freshest_captured_at ?? null;

  const isEmpty =
    !summaryLoading &&
    !postsLoading &&
    summary !== undefined &&
    postMetrics !== undefined &&
    (summary.posts_tracked ?? 0) === 0 &&
    (postMetrics.items.length ?? 0) === 0;

  if (!activeClientId) {
    return (
      <div className="py-16 text-center font-mono text-sm text-graphite border border-dashed border-border">
        Select a client using the switcher to view their analytics.
      </div>
    );
  }

  if (summaryError || postsError) {
    return (
      <div className="py-16 text-center font-mono text-sm text-graphite border border-dashed border-border">
        Failed to load analytics data. Please refresh the page to try again.
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="py-16 text-center font-mono text-sm text-graphite border border-dashed border-border">
        No analytics yet. Publish a post to Meta to start tracking.
      </div>
    );
  }

  return (
    <div>
      {freshness && (
        <p className="text-xs font-mono text-graphite mb-6">
          Updated {formatRelativeTime(freshness)}
        </p>
      )}

      <MetricsSummaryCards summary={summary} isLoading={summaryLoading} />

      <PostMetricsTable items={postMetrics?.items} isLoading={postsLoading} />
    </div>
  );
}
