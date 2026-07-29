"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/Button";
import { campaignsApi, roadmapsApi, APIError } from "@/lib/api";
import { useClientStore } from "@/lib/stores/useClientStore";
import { cn } from "@/lib/utils";
import type { RoadmapCampaignSummary } from "@/lib/types";

const MAX_FILE_BYTES = 5 * 1024 * 1024;

interface PostEditPanelProps {
  campaign: RoadmapCampaignSummary;
  charLimit: number;
  postText: string | null;
  platformLabel: string;
  readOnly?: boolean;
  onClose: () => void;
  onUpdate: (updates: Partial<RoadmapCampaignSummary>) => void;
}

export function PostEditPanel({
  campaign,
  charLimit,
  postText,
  platformLabel,
  readOnly = false,
  onClose,
  onUpdate,
}: PostEditPanelProps) {
  const { activeClientId } = useClientStore();

  // State is initialized from props on mount (parent uses AnimatePresence to remount on each open)
  const [text, setText] = useState(postText ?? "");
  const [imagePreview, setImagePreview] = useState<string | null>(campaign.image_url);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, [text]);

  const charCount = text.length;
  const atCapacity = charLimit > 0 && charCount >= charLimit * 0.95;

  function getPostFieldKey(): "x_post" | "linkedin_post" | "blog_title" {
    if (campaign.platform_hint === "linkedin") return "linkedin_post";
    if (campaign.platform_hint === "blog_full") return "blog_title";
    return "x_post";
  }

  async function handleSave() {
    const postFieldKey = getPostFieldKey();
    if (campaign.platform_hint === "blog_full") {
      onUpdate({ blog_title: text });
      onClose();
      return;
    }
    setIsSaving(true);
    setSaveError(null);
    const patchData =
      postFieldKey === "linkedin_post"
        ? { linkedin_post: text }
        : { x_post: text };
    try {
      onUpdate({ [postFieldKey]: text });
      await campaignsApi.patch(campaign.id, patchData);
      onClose();
    } catch (err: unknown) {
      onUpdate({ [postFieldKey]: postText });
      setSaveError(
        err instanceof Error ? err.message : "Save failed. Please try again."
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !activeClientId) return;
    if (file.size > MAX_FILE_BYTES) {
      setSaveError("Image must be under 5 MB.");
      return;
    }
    setIsUploading(true);
    setSaveError(null);
    const localUrl = URL.createObjectURL(file);
    setImagePreview(localUrl);
    try {
      const { image_url } = await roadmapsApi.uploadCampaignImage(
        campaign.id,
        activeClientId,
        file
      );
      setImagePreview(image_url);
      onUpdate({ image_url });
    } catch (err: unknown) {
      setImagePreview(campaign.image_url);
      setSaveError(
        err instanceof APIError ? err.message : "Image upload failed."
      );
    } finally {
      setIsUploading(false);
      URL.revokeObjectURL(localUrl);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div
      className="px-6 py-6 flex flex-col gap-5"
      role="region"
      aria-label={`${readOnly ? "View" : "Edit"} ${platformLabel} post`}
    >
      {/* Published note — shown for all platforms in read-only mode */}
      {readOnly && (
        <p className="font-body text-xs text-graphite">This post has already been published.</p>
      )}

      {/* Text area — not shown for blog (only title exists in summary) */}
      {campaign.platform_hint !== "blog_full" && (
        <div>
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) =>
              setText(
                charLimit > 0 ? e.target.value.slice(0, charLimit) : e.target.value
              )
            }
            disabled={readOnly}
            className={cn(
              "w-full bg-transparent resize-none font-mono text-sm text-ink leading-[1.7]",
              "border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink",
              "py-2 focus:outline-none transition-all",
              readOnly && "opacity-50 cursor-default"
            )}
            rows={4}
            aria-label={`${platformLabel} post content`}
          />
          {charLimit > 0 && (
            <p
              className={cn(
                "font-body text-xs mt-1",
                atCapacity ? "text-danger" : "text-graphite"
              )}
            >
              {charCount} / {charLimit}
            </p>
          )}
        </div>
      )}

      {/* Image section — hidden in read-only mode */}
      {!readOnly && (
        <div>
          {imagePreview ? (
            <div className="flex flex-col gap-2">
              {imagePreview.startsWith("blob:") ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={imagePreview}
                  alt=""
                  width={240}
                  className="w-full max-w-[240px] h-auto object-cover"
                  style={{ objectFit: "cover" }}
                />
              ) : (
                <Image
                  src={imagePreview}
                  alt=""
                  width={240}
                  height={135}
                  className="w-full max-w-[240px] h-auto object-cover"
                  style={{ objectFit: "cover" }}
                />
              )}
              <Button
                type="button"
                variant="secondary"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="text-xs self-start"
                aria-label="Replace image"
              >
                {isUploading ? "Uploading..." : "Replace image"}
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="text-xs"
              aria-label="Upload your own image"
            >
              {isUploading ? "Uploading..." : "Upload your own image"}
            </Button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={handleFileSelect}
          />
        </div>
      )}

      {saveError && (
        <p className="font-body text-xs text-danger">{saveError}</p>
      )}

      {/* Footer */}
      <div className="flex gap-2">
        {readOnly ? (
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            className="text-xs"
          >
            Close
          </Button>
        ) : (
          <>
            <Button
              type="button"
              variant="primary"
              onClick={handleSave}
              disabled={isSaving || isUploading}
              className="text-xs"
            >
              {isSaving ? "Saving..." : "Save changes"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isSaving || isUploading}
              className="text-xs"
            >
              Cancel
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
