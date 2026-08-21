"use client";

import { useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ExternalLink, Loader2, UploadCloud } from "lucide-react";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { Button } from "@/components/ui/Button";
import { roadmapsApi, APIError } from "@/lib/api";
import { useClientStore } from "@/lib/stores/useClientStore";
import { cn } from "@/lib/utils";
import { getAngleLabel } from "@/lib/angles";
import type { RoadmapCampaignSummary } from "@/lib/types";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

export function getPlatformInfo(campaign: RoadmapCampaignSummary): {
  label: string;
  charLimit: number;
  postText: string | null;
  platformKey: string;
} {
  if (campaign.platform_hint === "blog_full") {
    return { label: "Blog", charLimit: 0, postText: campaign.blog_title, platformKey: "wordpress" };
  }
  if (campaign.platform_hint === "linkedin") {
    return { label: "LinkedIn", charLimit: 1300, postText: campaign.linkedin_post, platformKey: "linkedin" };
  }
  return { label: "X", charLimit: 280, postText: campaign.x_post, platformKey: "x" };
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
  const { activeClientId } = useClientStore();
  const [pendingPreview, setPendingPreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { label: platformLabel, postText, platformKey } = getPlatformInfo(campaign);
  const timeLabel = formatScheduledTime(scheduledFor);
  const angleLabel = getAngleLabel(campaign.angle);

  // Transient blob preview overrides persisted image only during upload
  const displayedImage = pendingPreview ?? campaign.image_url;
  const canEditImage = !isRemoved && campaign.status !== "published";

  async function handleImageSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !activeClientId) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      setUploadError("Unsupported file type. Please use PNG, JPEG, or WebP.");
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setUploadError("Image must be under 5 MB.");
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    const localUrl = URL.createObjectURL(file);
    setPendingPreview(localUrl);
    try {
      const { image_url } = await roadmapsApi.uploadCampaignImage(
        campaign.id,
        activeClientId,
        file
      );
      onUpdate({ image_url });
    } catch (err: unknown) {
      setUploadError(err instanceof APIError ? err.message : "Image upload failed.");
    } finally {
      setIsUploading(false);
      setPendingPreview(null);
      URL.revokeObjectURL(localUrl);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

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
            <PlatformIcon platform={platformKey} className="size-3.5 text-graphite shrink-0" color="mono" aria-hidden="true" />
            <span className="font-body text-xs text-graphite uppercase tracking-[0.08em] truncate">
              {platformLabel}
            </span>
            {angleLabel && platformLabel !== "Blog" && (
              <span className="font-body text-xs uppercase tracking-[0.08em] text-graphite border border-[#E5E5E5] px-1.5 py-0.5 shrink-0 whitespace-nowrap">
                {angleLabel}
              </span>
            )}
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
        {canEditImage ? (
          displayedImage ? (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              aria-label="Replace image"
              className={cn(
                "group relative block h-20 w-full overflow-hidden border border-[#E5E5E5]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1",
                "disabled:cursor-wait"
              )}
            >
              {displayedImage.startsWith("blob:") ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={displayedImage}
                  alt=""
                  className="size-full object-cover"
                />
              ) : (
                <Image
                  src={displayedImage}
                  alt=""
                  width={240}
                  height={80}
                  className="size-full object-cover"
                  style={{ objectFit: "cover" }}
                />
              )}
              <span
                className={cn(
                  "absolute inset-0 flex items-center justify-center gap-1.5 bg-ink/60",
                  "opacity-0 transition-opacity duration-150",
                  "group-hover:opacity-100 group-focus-visible:opacity-100",
                  isUploading && "opacity-100"
                )}
              >
                {isUploading ? (
                  <Loader2 className="size-4 animate-spin text-white" aria-hidden="true" />
                ) : (
                  <UploadCloud className="size-4 text-white" aria-hidden="true" />
                )}
                <span className="font-mono text-xs uppercase tracking-[0.08em] text-white">
                  {isUploading ? "Uploading" : "Replace"}
                </span>
              </span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              aria-label="Upload your own image"
              className={cn(
                "group relative flex h-20 w-full items-center justify-center",
                "border border-dashed border-[#E5E5E5] bg-white",
                "transition-colors duration-150 hover:border-ink hover:bg-[#F9F9F6]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1",
                "disabled:cursor-wait disabled:opacity-60"
              )}
            >
              <div className="flex flex-col items-center gap-1">
                <UploadCloud className="size-4 text-graphite transition-colors group-hover:text-ink" aria-hidden="true" />
                <span className="font-body text-xs text-graphite transition-colors group-hover:text-ink">
                  {isUploading ? "Uploading..." : "Add your own image"}
                </span>
              </div>
            </button>
          )
        ) : (
          <div className="h-20 w-full overflow-hidden flex items-center justify-center border border-dashed border-[#E5E5E5]">
            {campaign.image_url ? (
              <Image
                src={campaign.image_url}
                alt=""
                width={240}
                height={80}
                className="size-full object-cover"
                style={{ objectFit: "cover" }}
              />
            ) : (
              <div className="flex flex-col items-center gap-1">
                <UploadCloud className="size-4 text-graphite" aria-hidden="true" />
                <span className="font-body text-xs text-graphite">Add your own image</span>
              </div>
            )}
          </div>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
          onChange={handleImageSelect}
        />

        {/* Upload error */}
        {uploadError && (
          <p className="font-body text-xs text-danger" role="alert">
            {uploadError}
          </p>
        )}

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
