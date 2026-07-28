"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useClientStore } from "@/lib/stores/useClientStore";
import { roadmapsApi } from "@/lib/api";
import { Skeleton } from "@/components/ui/Skeleton";
import type { RoadmapListItem } from "@/lib/types";

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: { label: "Generating", className: "bg-highlight text-ink border-border" },
  generating: { label: "Generating", className: "bg-highlight text-ink border-border" },
  ready: { label: "Ready to Review", className: "bg-highlight text-ink border-ink" },
  approved: { label: "Scheduled", className: "bg-success/10 text-success border-success/20" },
  failed: { label: "Failed", className: "bg-danger/10 text-danger border-danger/20" },
};

function getStatusConfig(status: string) {
  return STATUS_CONFIG[status] ?? { label: status, className: "bg-border text-graphite border-border" };
}

function getActionHref(item: RoadmapListItem): string {
  if (item.status === "approved") {
    const month = item.week_start_date?.slice(0, 7); // "YYYY-MM"
    return month ? `/calendar?month=${month}` : "/calendar";
  }
  if (item.status === "failed") return "/roadmap/new";
  return `/roadmap/${item.id}/review`;
}

function getActionLabel(item: RoadmapListItem): string {
  if (item.status === "approved") return "View calendar";
  if (item.status === "failed") return "Try again";
  return "Review";
}

function formatWeekLabel(item: RoadmapListItem): string {
  if (!item.week_start_date) {
    return `Week of ${new Date(item.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
  }
  const d = new Date(item.week_start_date + "T00:00:00");
  return `Week of ${d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
}

export function RoadmapListClient() {
  const activeClientId = useClientStore((s) => s.activeClientId);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["roadmaps", activeClientId],
    queryFn: () => roadmapsApi.list(activeClientId ?? undefined),
    staleTime: 30_000,
    enabled: !!activeClientId,
  });

  const items = data?.items ?? [];

  return (
    <div>
      <header className="flex items-center justify-between mb-10">
        <h1 className="font-display text-3xl font-bold text-ink">Roadmap</h1>
        <Link
          href="/roadmap/new"
          className="inline-flex items-center gap-2 bg-ink text-white text-sm font-medium px-5 py-3 shadow-[4px_4px_0px_0px_#111111] hover:shadow-none transition-shadow"
        >
          Plan My Week
        </Link>
      </header>

      {!activeClientId && (
        <p className="font-body text-sm text-graphite">Select a client to view roadmaps.</p>
      )}

      {isError && (
        <p className="font-body text-sm text-danger">Failed to load roadmaps. Please try again.</p>
      )}

      {activeClientId && isLoading && (
        <div className="border border-border divide-y divide-border">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between p-5">
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-2/5" />
                <Skeleton className="h-3 w-1/5" />
              </div>
              <div className="flex items-center gap-4 ml-4">
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-4 w-16" />
              </div>
            </div>
          ))}
        </div>
      )}

      {activeClientId && !isLoading && !isError && items.length === 0 && (
        <div className="border border-dashed border-graphite p-16 text-center">
          <p className="font-body text-sm text-graphite mb-6">No week plans yet.</p>
          <Link
            href="/roadmap/new"
            className="inline-flex items-center gap-2 bg-ink text-white text-sm font-medium px-5 py-3 shadow-[4px_4px_0px_0px_#111111] hover:shadow-none transition-shadow"
          >
            Plan My Week
          </Link>
        </div>
      )}

      {activeClientId && !isLoading && !isError && items.length > 0 && (
        <div className="border border-border divide-y divide-border">
          {items.map((item) => {
            const { label, className } = getStatusConfig(item.status);
            return (
              <div key={item.id} className="flex items-center justify-between p-5 hover:bg-ink/5 transition-colors">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-ink text-sm mb-1">{formatWeekLabel(item)}</p>
                  <p className="font-body text-xs text-graphite">
                    {item.campaign_count} post{item.campaign_count !== 1 ? "s" : ""}
                  </p>
                </div>
                <div className="flex items-center gap-4 ml-4 shrink-0">
                  <span className={`text-xs font-mono border px-2 py-0.5 ${className}`}>{label}</span>
                  <Link
                    href={getActionHref(item)}
                    className="font-body text-xs text-graphite underline hover:text-ink transition-colors"
                  >
                    {getActionLabel(item)}
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
