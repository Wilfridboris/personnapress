"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
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

  // Limit reached state (no image, no error about failure)
  if (!currentImageUrl && !jobErrorDetails?.includes("Image generation failed")) {
    return (
      <div className="border border-border">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="font-mono text-xs text-graphite uppercase tracking-widest">
            Featured Image
          </h2>
        </div>
        <div className="p-4">
          <p className="font-mono text-sm text-graphite mb-3">
            Image generation limit reached for this billing cycle.
          </p>
          <Link
            href="/account"
            className="font-mono text-sm text-ink underline underline-offset-2 hover:text-graphite transition-colors"
          >
            Upgrade plan →
          </Link>
        </div>
      </div>
    );
  }

  // Failed state (no image, explicit failure error)
  if (!currentImageUrl) {
    return (
      <div className="border border-border">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="font-mono text-xs text-graphite uppercase tracking-widest">
            Featured Image
          </h2>
        </div>
        <div className="p-4">
          <p className="font-mono text-sm text-graphite mb-3">Image generation failed.</p>
          <button
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="inline-flex items-center gap-2 px-4 py-2 bg-ink text-paper font-mono text-sm hover:bg-graphite transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRegenerating ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              "Generate image"
            )}
          </button>
          {error && (
            <p className="mt-2 font-mono text-xs text-danger">{error}</p>
          )}
        </div>
      </div>
    );
  }

  // Image present state
  return (
    <div className="border border-border">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="font-mono text-xs text-graphite uppercase tracking-widest">
          Featured Image
        </h2>
      </div>
      <div className="p-4 space-y-3">
        <div className="relative w-full" style={{ aspectRatio: "1200/630" }}>
          <Image
            src={currentImageUrl}
            alt="Featured image"
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 33vw"
          />
        </div>
        <button
          onClick={handleRegenerate}
          disabled={isAtLimit || isRegenerating}
          className="inline-flex items-center gap-2 px-4 py-2 bg-transparent border border-ink text-ink font-mono text-sm hover:bg-ink hover:text-paper transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
