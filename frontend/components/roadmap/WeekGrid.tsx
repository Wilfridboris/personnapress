"use client";

import { PostCard } from "./PostCard";
import type { RoadmapCampaignSummary } from "@/lib/types";

const DAY_ABBRS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getWeekDates(weekStartDate: string | null): Date[] {
  const base = weekStartDate ? new Date(weekStartDate + "T00:00:00") : getMondayOfCurrentWeek();
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(base);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function getMondayOfCurrentWeek(): Date {
  const today = new Date();
  const day = today.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(today);
  monday.setDate(today.getDate() + diff);
  return monday;
}

function getDayIndex(scheduledFor: string | null): number {
  if (!scheduledFor) return -1;
  const d = new Date(scheduledFor);
  const day = d.getDay();
  return day === 0 ? 6 : day - 1;
}

interface WeekGridProps {
  campaigns: RoadmapCampaignSummary[];
  weekStartDate: string | null;
  removedIds: Set<string>;
  onRemove: (id: string) => void;
  onUndo: (id: string) => void;
  onUpdateCampaign: (id: string, updates: Partial<RoadmapCampaignSummary>) => void;
}

export function WeekGrid({
  campaigns,
  weekStartDate,
  removedIds,
  onRemove,
  onUndo,
  onUpdateCampaign,
}: WeekGridProps) {
  const weekDates = getWeekDates(weekStartDate);

  const campaignsByDay: RoadmapCampaignSummary[][] = Array.from(
    { length: 7 },
    () => []
  );
  const unscheduled: RoadmapCampaignSummary[] = [];

  for (const campaign of campaigns) {
    const idx = getDayIndex(campaign.scheduled_for);
    if (idx >= 0 && idx < 7) {
      campaignsByDay[idx].push(campaign);
    } else {
      unscheduled.push(campaign);
    }
  }

  // Distribute unscheduled campaigns across days evenly
  let dayIdx = 0;
  for (const campaign of unscheduled) {
    campaignsByDay[dayIdx].push(campaign);
    dayIdx = (dayIdx + 1) % 7;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-7 gap-3">
      {weekDates.map((date, i) => {
        const abbr = DAY_ABBRS[i];
        const dateLabel = date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
        const dayCampaigns = campaignsByDay[i];

        return (
          <div key={i} className="flex flex-col gap-2">
            <p className="font-body text-xs text-graphite uppercase tracking-[0.08em] pb-1 border-b border-[#E5E5E5]">
              {abbr} {dateLabel}
            </p>

            {dayCampaigns.length === 0 ? (
              <div className="border border-dashed border-[#E5E5E5] flex items-center justify-center py-6">
                <p className="font-body text-xs text-graphite">No posts this day</p>
              </div>
            ) : (
              dayCampaigns.map((campaign) => (
                <PostCard
                  key={campaign.id}
                  campaign={campaign}
                  scheduledFor={campaign.scheduled_for}
                  isRemoved={removedIds.has(campaign.id)}
                  onRemove={() => onRemove(campaign.id)}
                  onUndo={() => onUndo(campaign.id)}
                  onUpdate={(updates) => onUpdateCampaign(campaign.id, updates)}
                />
              ))
            )}
          </div>
        );
      })}
    </div>
  );
}
