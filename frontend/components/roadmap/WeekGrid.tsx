"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { PostCard, getPlatformInfo } from "./PostCard";
import { PostEditPanel } from "./PostEditPanel";
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
  const [editingCampaign, setEditingCampaign] = useState<RoadmapCampaignSummary | null>(null);

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
    <>
    <div className="overflow-x-auto pb-3 -mx-4 px-4 lg:-mx-0 lg:px-0">
      <div
        className="grid gap-3"
        style={{
          gridTemplateColumns: "repeat(7, minmax(180px, 1fr))",
          minWidth: "1260px",
        }}
      >
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
                  onEdit={() => setEditingCampaign(campaign)}
                  onUpdate={(updates) => onUpdateCampaign(campaign.id, updates)}
                />
              ))
            )}
          </div>
        );
      })}
      </div>
    </div>

    <AnimatePresence>
      {editingCampaign && (
        <motion.div
          key="backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-40 bg-black/20"
          onClick={() => setEditingCampaign(null)}
        />
      )}
      {editingCampaign && (
        <motion.div
          key={`drawer-${editingCampaign.id}`}
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed inset-y-0 right-0 z-50 w-[480px] max-w-full bg-[#F9F9F6] border-l border-[#111111] shadow-[-4px_0px_0px_#111111] overflow-y-auto flex flex-col"
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E5E5]">
            <p className="font-body text-xs text-graphite uppercase tracking-[0.08em]">
              {editingCampaign.status === "published"
                ? `Published ${getPlatformInfo(editingCampaign).label} post`
                : `Editing ${getPlatformInfo(editingCampaign).label} post`}
            </p>
            <button
              type="button"
              aria-label="Close editor"
              onClick={() => setEditingCampaign(null)}
              className="text-graphite hover:text-ink transition-colors"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
          <PostEditPanel
            campaign={editingCampaign}
            charLimit={getPlatformInfo(editingCampaign).charLimit}
            postText={getPlatformInfo(editingCampaign).postText}
            platformLabel={getPlatformInfo(editingCampaign).label}
            readOnly={editingCampaign.status === "published"}
            onClose={() => setEditingCampaign(null)}
            onUpdate={(updates) => {
              onUpdateCampaign(editingCampaign.id, updates);
              setEditingCampaign((prev) => prev ? { ...prev, ...updates } : null);
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
    </>
  );
}

