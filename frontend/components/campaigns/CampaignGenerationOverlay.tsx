"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useJobStatus } from "@/hooks/useJobStatus";
import { campaignsApi } from "@/lib/api";
import { TypewriterAnimation } from "./TypewriterAnimation";
import { Button } from "@/components/ui/Button";

const BLOG_FULL_MESSAGES = [
  "Analyzing your voice profile...",
  "Drafting blog post...",
  "Checking voice fidelity...",
  "Generating featured image...",
  "Done.",
];

const SOCIAL_ONLY_MESSAGES = [
  "Analyzing your voice profile...",
  "Generating your social posts...",
  "Done.",
];

interface CampaignGenerationOverlayProps {
  campaignId: string;
  jobId: string;
  brainDump: string;
  clientId: string;
  campaignType?: "blog_full" | "social_only";
  skipImage?: boolean;
}

export function CampaignGenerationOverlay({
  campaignId,
  jobId,
  brainDump,
  clientId,
  campaignType,
  skipImage,
}: CampaignGenerationOverlayProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { job, isPolling } = useJobStatus(jobId);

  const STATUS_MESSAGES = campaignType === "social_only" ? SOCIAL_ONLY_MESSAGES : BLOG_FULL_MESSAGES;
  const IN_PROGRESS_START_INDEX = 1;
  const IN_PROGRESS_END_INDEX = campaignType === "social_only" ? 1 : 3;
  const COMPLETE_INDEX = STATUS_MESSAGES.length - 1;

  const [messageIndex, setMessageIndex] = useState(0);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  // Map job status to message index
  // pending -> 0; in_progress -> cycle through steps; complete -> last index
  useEffect(() => {
    if (!job) return;
    if (job.status === "pending") {
      setMessageIndex(0);
    } else if (job.status === "complete" || job.status === "completed") {
      setMessageIndex(COMPLETE_INDEX);
    }
    // in_progress cycling is handled by the 15s timer below
  }, [job?.status, COMPLETE_INDEX]);

  // Cycle through in_progress messages every 15s
  useEffect(() => {
    if (job?.status !== "in_progress") return;
    setMessageIndex((idx) => Math.max(idx, IN_PROGRESS_START_INDEX));
    const timer = setInterval(() => {
      setMessageIndex((idx) => (idx >= IN_PROGRESS_END_INDEX ? idx : idx + 1));
    }, 15_000);
    return () => clearInterval(timer);
  }, [job?.status, IN_PROGRESS_START_INDEX, IN_PROGRESS_END_INDEX]);

  // On job complete, navigate to clean URL
  useEffect(() => {
    if (job?.status === "complete" || job?.status === "completed") {
      queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
      const timer = setTimeout(() => {
        router.replace(`/campaigns/${campaignId}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [job?.status, campaignId, queryClient, router]);

  // Task 4.6: Browser tab close / reload guard while polling is active
  useEffect(() => {
    if (!isPolling) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isPolling]);

  const handleRetry = useCallback(async () => {
    setIsRetrying(true);
    setRetryError(null);
    try {
      const result = await campaignsApi.create({ client_id: clientId, brain_dump: brainDump, campaign_type: campaignType, skip_image: skipImage });
      router.push(`/campaigns/${result.campaign_id}?job_id=${result.job_id}`);
    } catch {
      setRetryError("Failed to retry generation. Please try again.");
      setIsRetrying(false);
    }
  }, [clientId, brainDump, campaignType, skipImage, router]);

  const handleMessageComplete = useCallback(() => {
    if (job?.status === "pending") {
      setMessageIndex((idx) => Math.min(idx + 1, IN_PROGRESS_END_INDEX));
    }
  }, [job?.status, IN_PROGRESS_END_INDEX]);

  // Task 4.5: Failed state
  if (job?.status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] bg-paper px-8 py-12">
        <div className="border border-danger/30 bg-danger/5 p-6 max-w-md w-full">
          <p className="font-sans text-sm font-medium text-ink mb-2">Generation failed.</p>
          <p className="font-sans text-sm text-graphite mb-6">
            {job.error_details ?? "Generation service temporarily unavailable."}
          </p>
          {retryError && (
            <p role="alert" className="text-sm text-danger mb-4">
              {retryError}
            </p>
          )}
          <Button variant="primary" onClick={handleRetry} disabled={isRetrying} aria-busy={isRetrying}>
            {isRetrying ? "Retrying..." : "Retry generation"}
          </Button>
        </div>
      </div>
    );
  }

  // Task 4.6: In-app leave confirmation banner (pragmatic approach from Dev Notes)
  return (
    <>
      {isPolling && (
        <div className="bg-highlight/10 border border-highlight/30 px-4 py-3 mb-6 font-mono text-xs text-graphite">
          Generation is in progress. Leaving will not cancel it. Your draft will be available on the Dashboard when complete.
        </div>
      )}
      <TypewriterAnimation
        statusMessages={STATUS_MESSAGES}
        currentMessageIndex={messageIndex}
        onMessageComplete={handleMessageComplete}
      />

    </>
  );
}
