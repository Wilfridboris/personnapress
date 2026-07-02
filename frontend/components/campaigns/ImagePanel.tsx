"use client";

import { useState } from "react";
import Image from "next/image";
import { Loader2 } from "lucide-react";
import { campaignsApi, APIError } from "@/lib/api";

interface ImagePanelProps {
  campaignId: string;
  imageUrl: string | null;
  imageRegenCount: number;
  jobErrorDetails: string | null;
}

export function ImagePanel({
  campaignId,
  imageUrl,
  imageRegenCount,
  jobErrorDetails,
}: ImagePanelProps) {
  const [currentImageUrl, setCurrentImageUrl] = useState(imageUrl);
  const [currentRegenCount, setCurrentRegenCount] = useState(imageRegenCount);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remainingRegens = Math.max(0, 3 - currentRegenCount);
  const isAtLimit = currentRegenCount >= 3;

  async function handleRegenerate() {
    setIsRegenerating(true);
    setError(null);
    try {
      const result = await campaignsApi.regenerateImage(campaignId);
      setCurrentImageUrl(result.image_url);
      setCurrentRegenCount(result.image_regen_count);
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Regeneration failed. Please try again.";
      setError(message);
    } finally {
      setIsRegenerating(false);
    }
  }

  // No image state — covers failed generation, limit reached, and no-context cases.
  // The regenerate endpoint enforces the subscription limit and will surface a proper
  // error message if the quota is genuinely exhausted.
  if (!currentImageUrl) {
    return (
      <div className="border border-border">
        <div className="px-6 py-4 border-b border-border">
          <h2 className="font-mono text-xs text-graphite uppercase tracking-widest">
            Featured Image
          </h2>
        </div>
        <div className="p-6 space-y-4">
          <p className="font-mono text-sm text-graphite">
            {jobErrorDetails?.includes("Image generation failed")
              ? "Image generation failed — blog and social posts are complete."
              : "No featured image generated."}
          </p>
          <button
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-ink text-paper font-mono text-sm hover:bg-graphite transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRegenerating ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              "Generate image"
            )}
          </button>
          {error && (
            <p className="font-mono text-xs text-danger">{error}</p>
          )}
        </div>
      </div>
    );
  }

  // Image present state
  return (
    <div className="border border-border">
      <div className="px-6 py-4 border-b border-border">
        <h2 className="font-mono text-xs text-graphite uppercase tracking-widest">
          Featured Image
        </h2>
      </div>
      <div className="p-6 space-y-4">
        <div className="relative w-full" style={{ aspectRatio: "1200/630" }}>
          <Image
            src={currentImageUrl}
            alt="Featured image"
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 40vw"
          />
        </div>
        <button
          onClick={handleRegenerate}
          disabled={isAtLimit || isRegenerating}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-transparent border border-ink text-ink font-mono text-sm hover:bg-ink hover:text-paper transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRegenerating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : isAtLimit ? (
            "No regenerations remaining"
          ) : (
            `Regenerate image (${remainingRegens} remaining)`
          )}
        </button>
        {error && (
          <p className="font-mono text-xs text-danger">{error}</p>
        )}
      </div>
    </div>
  );
}
