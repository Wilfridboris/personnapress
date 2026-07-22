"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { Loader2 } from "lucide-react";
import { campaignsApi, imagesApi, APIError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { useUIStore } from "@/lib/stores/useUIStore";

interface ImagePanelProps {
  campaignId: string;
  clientId: string;
  imageUrl: string | null;
  imageAlt?: string;
  imageRegenCount: number;
  jobErrorDetails: string | null;
  isGenerating?: boolean;
}

export function ImagePanel({
  campaignId,
  clientId,
  imageUrl,
  imageAlt,
  imageRegenCount,
  jobErrorDetails,
  isGenerating = false,
}: ImagePanelProps) {
  const addToast = useUIStore((s) => s.addToast);
  const [currentImageUrl, setCurrentImageUrl] = useState(imageUrl);
  const [currentImageAlt, setCurrentImageAlt] = useState(imageAlt);
  const [currentRegenCount, setCurrentRegenCount] = useState(imageRegenCount);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSavingAlt, setIsSavingAlt] = useState(false);
  const [altText, setAltText] = useState(imageAlt ?? "");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lastSavedAlt = useRef(imageAlt ?? "");

  // Sync state when image arrives post-generation (null → value transition only)
  useEffect(() => {
    if (imageUrl && !currentImageUrl) setCurrentImageUrl(imageUrl);
  }, [imageUrl]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync alt text when prop changes externally (e.g. parent re-fetches campaign)
  useEffect(() => {
    setAltText(imageAlt ?? "");
    lastSavedAlt.current = imageAlt ?? "";
  }, [imageAlt]); // eslint-disable-line react-hooks/exhaustive-deps

  const remainingRegens = Math.max(0, 3 - currentRegenCount);
  const isAtLimit = currentRegenCount >= 3;

  async function handleRegenerate() {
    setIsRegenerating(true);
    setError(null);
    try {
      const result = await campaignsApi.regenerateImage(campaignId);
      setCurrentImageUrl(result.image_url);
      setCurrentImageAlt(result.image_alt);
      setAltText(result.image_alt ?? "");
      lastSavedAlt.current = result.image_alt ?? "";
      setCurrentRegenCount(result.image_regen_count);
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : "Regeneration failed. Please try again.";
      setError(message);
    } finally {
      setIsRegenerating(false);
    }
  }

  async function handleSaveAlt() {
    if (altText === lastSavedAlt.current || isSavingAlt) return;
    setIsSavingAlt(true);
    try {
      await campaignsApi.patchImage(campaignId, { image_alt: altText });
      lastSavedAlt.current = altText;
      addToast("Alt text saved.", "success");
    } catch (err) {
      addToast(err instanceof APIError ? err.message : "Failed to save alt text.", "error");
    } finally {
      setIsSavingAlt(false);
    }
  }

  async function handleReplaceImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setIsUploading(true);
    setError(null);
    try {
      const { url } = await imagesApi.upload(clientId, file);
      await campaignsApi.patchImage(campaignId, { image_url: url });
      setCurrentImageUrl(url);
      addToast("Featured image updated.", "success");
    } catch (err) {
      addToast(err instanceof APIError ? err.message : "Failed to replace image.", "error");
    } finally {
      setIsUploading(false);
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
            alt={currentImageAlt ?? "Featured article image"}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 40vw"
          />
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={handleReplaceImage}
        />

        {/* Alt text */}
        <div className="space-y-1.5">
          <label
            htmlFor={`img-alt-${campaignId}`}
            className="text-[11px] font-medium uppercase tracking-[0.06em] text-graphite"
          >
            Image alt text
          </label>
          <input
            id={`img-alt-${campaignId}`}
            type="text"
            value={altText}
            onChange={(e) => setAltText(e.target.value)}
            onBlur={handleSaveAlt}
            placeholder="Describe what the image shows…"
            maxLength={500}
            disabled={isSavingAlt}
            className="w-full text-sm text-[#111111] bg-transparent border-b border-[#E5E5E5] focus:border-[#111111] focus:outline-none py-1.5 transition-[border-color] duration-150 placeholder:text-[#BBBBBB] disabled:opacity-50"
          />
        </div>

        {/* Replace image */}
        <Button
          variant="secondary"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading || isAtLimit || isRegenerating}
          aria-busy={isUploading}
          className="w-full font-mono"
        >
          {isUploading ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            "Replace image"
          )}
        </Button>

        {/* Regen */}
        <Button
          variant="secondary"
          onClick={handleRegenerate}
          disabled={isAtLimit || isRegenerating || isUploading}
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
