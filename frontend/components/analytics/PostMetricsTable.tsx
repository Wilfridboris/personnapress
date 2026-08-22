"use client";

import { useState } from "react";
import { ExternalLink, Heart, MessageCircle, Repeat2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { Skeleton } from "@/components/ui/Skeleton";
import { PlatformUnavailableState } from "./PlatformUnavailableState";
import type { PostMetricItem, SeriesPoint } from "@/hooks/usePostMetrics";
import { fmt } from "@/lib/formatters";

type PlatformFilter = "all" | "facebook_page" | "instagram" | "threads";

const PLATFORM_NOUNS: Record<string, { comments: string; shares: string }> = {
  facebook_page: { comments: "Comments", shares: "Shares" },
  instagram:     { comments: "Comments", shares: "Shares" },
  threads:       { comments: "Replies",  shares: "Reposts" },
};

function fmtComponent(n: number | null | undefined): string {
  return n == null ? "—" : fmt(n);
}

interface EngagementBreakdownProps {
  platform: string;
  likes: number | null;
  comments: number | null;
  shares: number | null;
}

function EngagementBreakdown({ platform, likes, comments, shares }: EngagementBreakdownProps) {
  const nouns = PLATFORM_NOUNS[platform] ?? { comments: "Comments", shares: "Shares" };
  return (
    <div className="flex items-center gap-3 mt-1 font-mono text-xs text-graphite">
      <span className="inline-flex items-center gap-1">
        <Heart className="size-3" aria-hidden="true" />
        <span aria-label={`${fmtComponent(likes)} likes`}>{fmtComponent(likes)}</span>
      </span>
      <span className="inline-flex items-center gap-1">
        <MessageCircle className="size-3" aria-hidden="true" />
        <span aria-label={`${fmtComponent(comments)} ${nouns.comments.toLowerCase()}`}>{fmtComponent(comments)}</span>
      </span>
      <span className="inline-flex items-center gap-1">
        <Repeat2 className="size-3" aria-hidden="true" />
        <span aria-label={`${fmtComponent(shares)} ${nouns.shares.toLowerCase()}`}>{fmtComponent(shares)}</span>
      </span>
    </div>
  );
}

const FILTER_OPTIONS: { value: PlatformFilter; label: string; platform?: string }[] = [
  { value: "all", label: "All" },
  { value: "facebook_page", label: "Facebook", platform: "facebook_page" },
  { value: "instagram", label: "Instagram", platform: "instagram" },
  { value: "threads", label: "Threads", platform: "threads" },
];

function trendLabel(series: SeriesPoint[]): string {
  if (series.length < 2) return "stable";
  const values = series.map((p) => p.engagements ?? 0).filter((v) => v > 0);
  if (values.length < 2) return "stable";
  const first = values[0];
  const last = values[values.length - 1];
  if (last > first * 1.05) return "up";
  if (last < first * 0.95) return "down";
  return "stable";
}

interface SparklineProps {
  series: SeriesPoint[];
  label: string;
}

function Sparkline({ series, label }: SparklineProps) {
  const values = series.map((p) => p.engagements ?? 0);
  if (values.length < 2) {
    return (
      <span className="inline-flex items-center justify-center text-xs font-mono text-graphite" title={label}>
        <span aria-hidden="true">-</span>
        <span className="sr-only">{label}</span>
      </span>
    );
  }

  const max = Math.max(...values, 1);
  const W = 48;
  const H = 20;
  const step = W / (values.length - 1);

  const points = values
    .map((v, i) => `${i * step},${H - (v / max) * H}`)
    .join(" ");

  const trend = trendLabel(series);

  return (
    <span className="inline-flex flex-col items-center gap-0.5" title={label}>
      <svg
        width={W}
        height={H}
        aria-hidden="true"
        className="overflow-visible"
      >
        <polyline
          points={points}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          className={cn(
            trend === "up" && "text-success",
            trend === "down" && "text-danger",
            trend === "stable" && "text-graphite"
          )}
        />
      </svg>
      <span className="sr-only">{label}</span>
    </span>
  );
}

interface Props {
  items: PostMetricItem[] | undefined;
  isLoading: boolean;
}

export function PostMetricsTable({ items, isLoading }: Props) {
  const [filter, setFilter] = useState<PlatformFilter>("all");

  const displayed = (items ?? []).filter(
    (item) => filter === "all" || item.platform === filter
  );

  return (
    <section aria-label="Post performance metrics">
      {/* Platform filter chips */}
      <div
        role="group"
        aria-label="Filter by platform"
        className="flex flex-wrap gap-2 mb-6"
      >
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            aria-pressed={filter === opt.value}
            onClick={() => setFilter(opt.value)}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono border transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1",
              filter === opt.value
                ? "bg-ink text-paper border-ink"
                : "bg-white text-ink border-border hover:border-ink"
            )}
          >
            {opt.platform && (
              <PlatformIcon
                platform={opt.platform}
                className="size-3"
                color={filter === opt.value ? "mono" : "brand"}
              />
            )}
            {opt.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-2" aria-label="Loading post metrics">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : displayed.length === 0 ? (
        <div className="py-12 text-center font-mono text-sm text-graphite border border-dashed border-border">
          No posts match this filter.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="border-b border-border bg-paper">
                <th
                  scope="col"
                  className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-graphite"
                >
                  Post
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-left font-mono text-xs uppercase tracking-widest text-graphite"
                >
                  Platform
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-right font-mono text-xs uppercase tracking-widest text-graphite"
                >
                  Impressions
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-right font-mono text-xs uppercase tracking-widest text-graphite"
                >
                  Engagements
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-center font-mono text-xs uppercase tracking-widest text-graphite"
                >
                  Trend
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-center font-mono text-xs uppercase tracking-widest text-graphite"
                >
                  Link
                </th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((item) => {
                const isUnavailable =
                  item.unavailable_reason !== null &&
                  item.latest_impressions === null &&
                  item.latest_engagements === null;
                const trend = trendLabel(item.series);

                return (
                  <tr
                    key={item.published_post_id}
                    className="border-b border-border last:border-0 hover:bg-paper transition-colors"
                  >
                    <td className="px-4 py-3 max-w-[220px]">
                      <p className="font-medium text-ink truncate leading-tight">
                        {item.campaign_title}
                      </p>
                      {item.campaign_excerpt && (
                        <p className="text-xs text-graphite truncate font-mono mt-0.5">
                          {item.campaign_excerpt}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5">
                        <PlatformIcon
                          platform={item.platform}
                          className="size-4"
                          color="brand"
                        />
                        <span className="sr-only">{item.platform}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-ink">
                      {isUnavailable ? (
                        <span aria-label="Not available">N/A</span>
                      ) : (
                        fmt(item.latest_impressions)
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-ink">
                      {isUnavailable ? (
                        <PlatformUnavailableState reason={item.unavailable_reason} />
                      ) : (
                        <div className="flex flex-col items-end">
                          <span>{fmt(item.latest_engagements)}</span>
                          <EngagementBreakdown
                            platform={item.platform}
                            likes={item.latest_likes}
                            comments={item.latest_comments}
                            shares={item.latest_shares}
                          />
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {isUnavailable ? (
                        <span className="text-xs font-mono text-graphite" aria-hidden="true">
                          —
                        </span>
                      ) : (
                        <Sparkline
                          series={item.series}
                          label={`Engagement trend: ${trend}, current ${fmt(item.latest_engagements)}`}
                        />
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.permalink ? (
                        <a
                          href={item.permalink}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Open ${item.campaign_title} on ${item.platform}`}
                          className="inline-flex items-center justify-center text-ink hover:text-graphite transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
                        >
                          <ExternalLink className="size-4" aria-hidden="true" />
                        </a>
                      ) : (
                        <span className="text-xs font-mono text-graphite" aria-hidden="true">
                          —
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
