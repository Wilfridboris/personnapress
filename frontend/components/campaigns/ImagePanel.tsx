"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { Loader2 } from "lucide-react";
import { campaignsApi, APIError } from "@/lib/api";
import { Button } from "@/components/ui/Button";

interface ImagePanelProps {
  campaignId: string;
  imageUrl: string | null;
  imageRegenCount: number;
  jobErrorDetails: string | null;
  isGenerating?: boolean;
}

export function ImagePanel({
  campaignId,
  imageUrl,
  imageRegenCount,
  jobErrorDetails,
  isGenerating = false,
}: ImagePanelProps) {
  const [currentImageUrl, setCurrentImageUrl] = useState(imageUrl);
  const [currentRegenCount, setCurrentRegenCount] = useState(imageRegenCount);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state when image arrives post-generation (null → value transition only)
  useEffect(() => {
    if (imageUrl && !currentImageUrl) setCurrentImageUrl(imageUrl);
  }, [imageUrl]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // During active generation, show an animated placeholder — the image hasn't
  // been generated yet so actions would be misleading.
  if (isGenerating && !currentImageUrl) {
    return (
      <div className="border border-border">
        <div className="px-6 py-4 border-b border-border">
          <h2 className="font-mono text-xs text-graphite uppercase tracking-widest">
            Featured Image
          </h2>
        </div>
        <div className="p-6">
          <div
            className="w-full animate-pulse bg-border"
            style={{ aspectRatio: "1200/630" }}
          />
        </div>
      </div>
    );
  }

  // No image state — covers failed generation and no-context cases.
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
              ? "Image generation failed. Blog and social posts are complete."
              : "No featured image generated."}
          </p>
          <Button
            variant="primary"
            onClick={handleRegenerate}
            disabled={isRegenerating}
            aria-busy={isRegenerating}
            className="w-full font-mono"
          >
            {isRegenerating ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              "Generate image"
            )}
          </Button>
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
        <Button
          variant="secondary"
          onClick={handleRegenerate}
          disabled={isAtLimit || isRegenerating}
          aria-busy={isRegenerating}
          className="w-full font-mono"
        >
          {isRegenerating ? (
            <Loader2 className="size-4 animate-spin" />
          ) : isAtLimit ? (
            "No regenerations remaining"
          ) : (
            `Regenerate image (${remainingRegens} remaining)`
          )}
        </Button>
        {error && (
          <p className="font-mono text-xs text-danger">{error}</p>
        )}
      </div>
    </div>
  );
}
