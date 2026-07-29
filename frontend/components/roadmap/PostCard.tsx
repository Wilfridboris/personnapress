"use client";

import Image from "next/image";
import Link from "next/link";
import { AtSign, BookOpen, ExternalLink, Share2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type { RoadmapCampaignSummary } from "@/lib/types";

export function getPlatformInfo(campaign: RoadmapCampaignSummary): {
  icon: React.ElementType;
  label: string;
  charLimit: number;
  postText: string | null;
} {
  if (campaign.platform_hint === "blog_full") {
    return { icon: BookOpen, label: "Blog", charLimit: 0, postText: campaign.blog_title };
  }
  if (campaign.platform_hint === "linkedin") {
    return { icon: AtSign, label: "LinkedIn", charLimit: 1300, postText: campaign.linkedin_post };
  }
  return { icon: Share2, label: "X", charLimit: 280, postText: campaign.x_post };
}

function formatScheduledTime(scheduledFor: string | null): string {
  if (!scheduledFor) return "";
  const d = new Date(scheduledFor);
  return d.toLocaleString("en-US", {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

interface PostCardProps {
  campaign: RoadmapCampaignSummary;
  scheduledFor: string | null;
  isRemoved: boolean;
  onRemove: () => void;
  onUndo: () => void;
  onEdit: () => void;
  onUpdate: (updates: Partial<RoadmapCampaignSummary>) => void;
}

export function PostCard({
  campaign,
  scheduledFor,
  isRemoved,
  onRemove,
  onUndo,
  onEdit,
  onUpdate,
}: PostCardProps) {
  const { icon: PlatformIcon, label: platformLabel, postText } = getPlatformInfo(campaign);
  const timeLabel = formatScheduledTime(scheduledFor);

  return (
    <div
      className={cn(
        "bg-white border border-[#E5E5E5] p-3 flex flex-col gap-2",
        "hover:shadow-[4px_4px_0px_#111111] transition-shadow duration-150",
        isRemoved && "opacity-50"
      )}
    >
        {/* Platform chip + status badge — inline row, no absolute positioning */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <PlatformIcon className="w-3.5 h-3.5 text-graphite shrink-0" aria-hidden="true" />
            <span className="font-body text-xs text-graphite uppercase tracking-[0.08em] truncate">
              {platformLabel}
            </span>
          </div>
          {isRemoved ? (
            <span className="font-body text-xs text-graphite uppercase tracking-[0.08em] bg-[#E5E5E5] px-2 py-0.5 shrink-0">
              REMOVED
            </span>
          ) : campaign.status === "published" ? (
            <span className="font-body text-xs uppercase tracking-[0.08em] bg-success-muted text-success px-2 py-0.5 shrink-0">
              PUBLISHED
            </span>
          ) : campaign.status === "failed" ? (
            <span className="font-body text-xs uppercase tracking-[0.08em] bg-danger-muted text-danger px-2 py-0.5 shrink-0">
              FAILED
            </span>
          ) : null}
        </div>

        {/* Scheduled time chip */}
        {timeLabel && (
          <p className="font-body text-xs text-graphite uppercase tracking-[0.08em]">
            {timeLabel}
          </p>
        )}

        {/* Post preview */}
        <p
          className={cn(
            "font-body text-[15px] text-ink line-clamp-2",
            isRemoved && "line-through"
          )}
        >
          {postText ?? "(No content)"}
        </p>

        {/* Image area */}
        <div className="h-[80px] w-full overflow-hidden flex items-center justify-center border border-dashed border-[#E5E5E5]">
          {campaign.image_url ? (
            <Image
              src={campaign.image_url}
              alt=""
              width={240}
              height={135}
              className="w-full h-full object-cover"
              style={{ objectFit: "cover" }}
            />
          ) : (
            <div className="flex flex-col items-center gap-1">
              <UploadCloud className="w-4 h-4 text-graphite" aria-hidden="true" />
              <span className="font-body text-xs text-graphite">Add your own image</span>
            </div>
          )}
        </div>

        {/* Action row */}
        {isRemoved ? (
          <div className="flex gap-2 mt-1">
            <Button
              type="button"
              variant="secondary"
              onClick={onUndo}
              className="text-xs px-3 py-1.5 min-h-[44px]"
              aria-label="Undo removal"
            >
              Undo
            </Button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2 mt-1 items-center">
            <Button
              type="button"
              variant="secondary"
              onClick={onEdit}
              className="text-xs px-3 py-1.5 min-h-[44px]"
              aria-label={campaign.status === "published" ? `View ${platformLabel} post` : `Edit ${platformLabel} post`}
            >
              {campaign.status === "published" ? "View" : "Edit"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={onRemove}
              className="text-xs px-3 py-1.5 min-h-[44px]"
              aria-label={`Remove ${platformLabel} post`}
            >
              Remove
            </Button>
            <Link
              href={`/campaigns/${campaign.id}`}
              className="inline-flex items-center gap-1 font-body text-xs text-graphite hover:text-ink transition-colors underline underline-offset-2 min-h-[44px]"
              aria-label={`Open full campaign page for ${platformLabel} post`}
            >
              <ExternalLink className="w-3 h-3" aria-hidden="true" />
              Campaign
            </Link>
          </div>
        )}
    </div>
  );
}
