"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { useCampaigns } from "@/hooks/useCampaigns";
import { usePlatformConnections } from "@/hooks/usePlatformConnections";
import { useClientStore } from "@/lib/stores/useClientStore";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { extractTitle } from "@/lib/utils";
import type { Campaign } from "@/lib/types";

const FILTER_OPTIONS = [
  { value: "", label: "All" },
  { value: "pending_approval", label: "Pending Approval" },
  { value: "approved", label: "Approved" },
  { value: "published", label: "Published" },
  { value: "rejected", label: "Rejected" },
  { value: "failed", label: "Failed" },
];

const DATE_FORMAT = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

function formatDate(dateStr: string): string {
  return DATE_FORMAT.format(new Date(dateStr));
}

export function CampaignList() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeClientId = useClientStore((s) => s.activeClientId);

  const status = searchParams.get("status") ?? "";
  const page = parseInt(searchParams.get("page") ?? "1", 10) || 1;

  const { data, isLoading } = useCampaigns({ clientId: activeClientId, status: status || undefined, page });
  const { data: connectionsData } = usePlatformConnections(activeClientId);

  const connectedPlatforms = (connectionsData?.items ?? [])
    .filter((c) => c.connected)
    .map((c) => c.platform);

  const campaigns = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  function setFilter(newStatus: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (newStatus) params.set("status", newStatus);
    else params.delete("status");
    params.set("page", "1");
    router.push(`/dashboard?${params.toString()}`);
  }

  function goToPage(n: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(n));
    router.push(`/dashboard?${params.toString()}`);
  }

  return (
    <div>
      {/* Filter tabs */}
      <nav role="tablist" className="flex border-b border-border mb-6 overflow-x-auto">
        {FILTER_OPTIONS.map((opt) => {
          const isActive = opt.value === status;
          return (
            <button
              key={opt.value}
              role="tab"
              aria-selected={isActive}
              onClick={() => setFilter(opt.value)}
              className={`px-4 py-2 text-sm font-body whitespace-nowrap transition-colors ${
                isActive
                  ? "border-b-2 border-ink text-ink font-medium -mb-px"
                  : "text-graphite hover:text-ink"
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </nav>

      {/* Loading skeletons */}
      {isLoading && (
        <div className="border border-border divide-y divide-border" aria-label="Loading campaigns">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between p-5">
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/5" />
                <Skeleton className="h-3 w-1/4" />
              </div>
              <div className="flex items-center gap-4 ml-4">
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && campaigns.length === 0 && (
        <div className="border border-border p-16 text-center">
          <h2 className="font-display text-xl font-bold text-ink mb-2">No campaigns yet.</h2>
          <p className="text-sm text-graphite font-body mb-6">
            Start with a Brain Dump and publish your first post.
          </p>
          <Link
            href="/campaigns/new"
            className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-6 py-3 hover:bg-graphite transition-colors shadow-[4px_4px_0px_0px_var(--color-ink)] hover:shadow-none"
          >
            New Campaign
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      )}

      {/* Campaign rows */}
      {!isLoading && campaigns.length > 0 && (
        <div className="border border-border divide-y divide-border">
          {campaigns.map((campaign: Campaign) => {
            const title = extractTitle(campaign.blog_html);
            return (
              <div
                key={campaign.id}
                className="flex items-center justify-between p-5 hover:bg-ink/5 transition-colors cursor-pointer group"
                onClick={() => router.push(`/campaigns/${campaign.id}`)}
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-ink text-sm truncate mb-1">{title}</p>
                  <p className="text-xs text-graphite font-mono">{formatDate(campaign.created_at)}</p>
                </div>
                <div className="flex items-center gap-3 ml-4 shrink-0">
                  <StatusBadge status={campaign.status} />
                  {campaign.status === "published" && (
                    <div className="flex items-center gap-1">
                      {connectedPlatforms.map((p) => (
                        <PlatformIcon key={p} platform={p} className="size-3.5 text-graphite" />
                      ))}
                      <span className="text-xs text-graphite font-mono ml-1">
                        {formatDate(campaign.updated_at)}
                      </span>
                    </div>
                  )}
                  {campaign.status === "failed" && (
                    <Link
                      href={`/campaigns/${campaign.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-xs font-mono text-danger underline underline-offset-2 hover:text-ink transition-colors"
                    >
                      Retry →
                    </Link>
                  )}
                  <ArrowRight className="size-3.5 text-graphite opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden="true" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-border px-5 py-4">
          <button
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1}
            className="text-sm font-mono text-graphite hover:text-ink disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ← Previous
          </button>
          <span className="text-xs font-mono text-graphite">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
            className="text-sm font-mono text-graphite hover:text-ink disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
