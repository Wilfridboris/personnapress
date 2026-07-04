"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Clock } from "lucide-react";
import clsx from "clsx";
import { useCalendarCampaigns } from "@/hooks/useCalendarCampaigns";
import { usePlatformConnections } from "@/hooks/usePlatformConnections";
import { useClientStore } from "@/lib/stores/useClientStore";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { Skeleton } from "@/components/ui/Skeleton";
import { extractTitle } from "@/lib/utils";
import type { Campaign } from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildMonthGrid(year: number, month: number): Array<Date | null> {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDow = firstDay.getDay();
  const daysInMonth = lastDay.getDate();
  const cells: Array<Date | null> = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

function toDateKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Slices the ISO string directly to avoid local-timezone shift when mapping
// UTC backend timestamps to calendar date keys.
function campaignCalendarDateKey(campaign: Campaign): string | null {
  if (campaign.status === "published") {
    return campaign.updated_at.slice(0, 10);
  }
  if (campaign.status === "approved" && campaign.scheduled_at) {
    return campaign.scheduled_at.slice(0, 10);
  }
  return null;
}

function chunkArray<T>(arr: T[], size: number): T[][] {
  const result: T[][] = [];
  for (let i = 0; i < arr.length; i += size) result.push(arr.slice(i, i + size));
  return result;
}

// ---------------------------------------------------------------------------
// CalendarEntry sub-component
// ---------------------------------------------------------------------------

const DOW_LABELS: Record<string, string> = {
  Sun: "Sunday",
  Mon: "Monday",
  Tue: "Tuesday",
  Wed: "Wednesday",
  Thu: "Thursday",
  Fri: "Friday",
  Sat: "Saturday",
};

function CalendarEntry({
  campaign,
  connectedPlatforms,
  onNavigate,
}: {
  campaign: Campaign;
  connectedPlatforms: string[];
  onNavigate: (id: string) => void;
}) {
  const title = extractTitle(campaign.blog_html);
  const shortTitle = title.length > 24 ? title.slice(0, 24) + "…" : title;

  const timeLabel =
    campaign.status === "approved" && campaign.scheduled_at
      ? new Intl.DateTimeFormat("en-US", {
          hour: "numeric",
          minute: "2-digit",
        }).format(new Date(campaign.scheduled_at))
      : null;

  const ariaLabel = `${shortTitle} — ${
    campaign.status === "published" ? "Published" : `Scheduled ${timeLabel}`
  }`;

  return (
    <button
      type="button"
      onClick={() => onNavigate(campaign.id)}
      draggable={false}
      onDragStart={(e) => e.preventDefault()}
      aria-label={ariaLabel}
      className={clsx(
        "w-full text-left px-1.5 py-0.5 text-[10px] font-body leading-tight",
        "border transition-colors cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ink focus-visible:ring-offset-1",
        campaign.status === "published"
          ? "bg-success/10 border-success/30 text-success hover:bg-success/20"
          : "bg-border border-border text-graphite hover:border-ink hover:text-ink"
      )}
    >
      <span className="block truncate">{shortTitle}</span>
      <div className="flex items-center gap-0.5 mt-0.5">
        {campaign.status === "published" &&
          connectedPlatforms.map((p) => (
            <PlatformIcon key={p} platform={p} className="size-2.5 shrink-0" />
          ))}
        {timeLabel && (
          <>
            <Clock className="size-2.5 shrink-0 text-graphite" aria-hidden="true" />
            <span className="text-graphite">{timeLabel}</span>
          </>
        )}
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// ContentCalendar main component
// ---------------------------------------------------------------------------

export function ContentCalendar() {
  const router = useRouter();
  const activeClientId = useClientStore((s) => s.activeClientId);

  const now = new Date();
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());

  const { data: campaigns, isLoading, isError } = useCalendarCampaigns(activeClientId);
  const { data: connections } = usePlatformConnections(activeClientId);

  const connectedPlatforms = useMemo(
    () =>
      (connections?.items ?? [])
        .filter((p) => p.connected)
        .map((p) => p.platform),
    [connections]
  );

  function prevMonth() {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((y) => y - 1);
    } else {
      setViewMonth((m) => m - 1);
    }
  }

  function nextMonth() {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((y) => y + 1);
    } else {
      setViewMonth((m) => m + 1);
    }
  }

  const monthLabel = new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(new Date(viewYear, viewMonth, 1));

  const grid = buildMonthGrid(viewYear, viewMonth);
  const todayKey = toDateKey(now);
  const weeks = chunkArray(grid, 7);

  const campaignsByDate = useMemo(() => {
    const map = new Map<string, Campaign[]>();
    for (const c of campaigns ?? []) {
      const key = campaignCalendarDateKey(c);
      if (!key) continue;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(c);
    }
    return map;
  }, [campaigns]);

  // True only when campaigns are loaded and at least one falls in the viewed month.
  const hasVisibleCampaigns = useMemo(() => {
    for (const date of grid) {
      if (!date) continue;
      if (campaignsByDate.has(toDateKey(date))) return true;
    }
    return false;
  }, [grid, campaignsByDate]);

  function navigate(id: string) {
    router.push(`/campaigns/${id}`);
  }

  return (
    <div className="select-none">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-display text-2xl font-bold text-ink tracking-tight">
          {monthLabel}
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={prevMonth}
            aria-label="Previous month"
            className="p-2 border border-border hover:border-ink hover:bg-ink hover:text-paper transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
          >
            <ChevronLeft className="size-4" aria-hidden="true" />
          </button>
          <button
            onClick={nextMonth}
            aria-label="Next month"
            className="p-2 border border-border hover:border-ink hover:bg-ink hover:text-paper transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
          >
            <ChevronRight className="size-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Calendar grid, skeleton, or error */}
      {isLoading ? (
        <div className="space-y-2 mt-4">
          <Skeleton className="h-[400px] w-full" />
        </div>
      ) : isError ? (
        <p className="mt-6 text-sm text-graphite font-body text-center">
          Failed to load campaigns. Please refresh to try again.
        </p>
      ) : (
        /*
         * Single role="grid" container owns both the header row and all week
         * rows, satisfying the ARIA grid ownership requirement (row must be
         * a descendant of grid).
         */
        <div
          role="grid"
          aria-label={`Content calendar for ${monthLabel}`}
          className="border-t border-l border-border"
        >
          {/* Day-of-week header — inside the grid for correct ARIA ownership */}
          <div role="row" className="grid grid-cols-7">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
              <div
                key={d}
                role="columnheader"
                className="border-b border-r border-border px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider text-graphite text-center"
              >
                <abbr title={DOW_LABELS[d]}>{d}</abbr>
              </div>
            ))}
          </div>

          {/* One role="row" per week — required by ARIA grid pattern */}
          {weeks.map((week, wi) => (
            <div key={wi} role="row" className="grid grid-cols-7">
              {week.map((date, di) => {
                if (!date) {
                  return (
                    <div
                      key={`empty-${wi}-${di}`}
                      role="gridcell"
                      className="border-b border-r border-border min-h-[80px] bg-border/20"
                    />
                  );
                }
                const key = toDateKey(date);
                const dayCampaigns = campaignsByDate.get(key) ?? [];
                const count = dayCampaigns.length;
                const isToday = key === todayKey;
                const ariaLabel = `${date.toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}, ${count === 0 ? "no campaigns" : `${count} campaign${count > 1 ? "s" : ""}`}`;

                return (
                  <div
                    key={key}
                    role="gridcell"
                    aria-label={ariaLabel}
                    className={clsx(
                      "border-b border-r border-border min-h-[80px] p-1.5 flex flex-col gap-1",
                      isToday && "bg-highlighter/30"
                    )}
                  >
                    <span
                      className={clsx(
                        "text-xs font-mono self-start px-1",
                        isToday ? "bg-ink text-paper font-bold" : "text-graphite"
                      )}
                    >
                      {date.getDate()}
                    </span>
                    {dayCampaigns.map((c) => (
                      <CalendarEntry
                        key={c.id}
                        campaign={c}
                        connectedPlatforms={connectedPlatforms}
                        onNavigate={navigate}
                      />
                    ))}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}

      {/* Empty state — fires only when loaded and no campaigns fall in this month */}
      {!isLoading && !isError && !hasVisibleCampaigns && (
        <p className="mt-6 text-sm text-graphite font-body text-center">
          Nothing scheduled. Approve a campaign to see it here.
        </p>
      )}
    </div>
  );
}
