"use client";

import { useState } from "react";
import { campaignsApi, jobsApi, APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import type { Campaign } from "@/lib/types";

interface RetryPanelProps {
  campaign: Campaign;
  jobId: string;
  jobErrorDetails: Record<string, string> | null;
  attemptCount: number;
  onRetrySuccess: () => void;
}

const MAX_RETRIES = 3;

export function RetryPanel({
  campaign,
  jobId,
  jobErrorDetails,
  attemptCount,
  onRetrySuccess,
}: RetryPanelProps) {
  const addToast = useUIStore((s) => s.addToast);
  const [isRetrying, setIsRetrying] = useState<Record<string, boolean>>({});

  if (!jobErrorDetails) return null;

  const platforms = Object.entries(jobErrorDetails).map(([platform, result]) => ({
    platform,
    error: result,
    isSuccess: result === "success",
  }));

  async function handleRetry(platform: string) {
    setIsRetrying((prev) => ({ ...prev, [platform]: true }));
    try {
      const { job_id } = await campaignsApi.retryPublish(campaign.id, platform);
      // Poll until terminal state
      await new Promise<void>((resolve, reject) => {
        const interval = setInterval(async () => {
          try {
            const job = await jobsApi.get(job_id);
            if (job.status === "complete" || job.status === "failed") {
              clearInterval(interval);
              resolve();
            }
          } catch (err) {
            clearInterval(interval);
            reject(err);
          }
        }, 2000);
      });
      onRetrySuccess();
    } catch (err) {
      addToast(err instanceof APIError ? err.message : "Retry failed.", "error");
    } finally {
      setIsRetrying((prev) => ({ ...prev, [platform]: false }));
    }
  }

  return (
    <div className="border border-border p-4 space-y-3 mt-8">
      <h2 className="text-sm font-medium uppercase tracking-[0.06em] text-ink">
        Publishing failed
      </h2>
      {platforms.map(({ platform, error, isSuccess }) => (
        <div
          key={platform}
          className="flex items-center justify-between py-2 border-b border-border last:border-0"
        >
          <div>
            <p className="text-sm font-medium text-ink capitalize">{platform}</p>
            {isSuccess ? (
              <p className="text-xs text-[#2E4F2E]">Published</p>
            ) : (
              <p className="text-xs text-[#8B0000]">{error}</p>
            )}
          </div>
          {!isSuccess && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-graphite">
                Attempt {attemptCount} of {MAX_RETRIES}
              </span>
              {attemptCount >= MAX_RETRIES ? (
                <span className="text-xs text-graphite">
                  Maximum retries reached — reconnect {platform} and try again.
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => handleRetry(platform)}
                  disabled={isRetrying[platform]}
                  aria-label={`Retry publishing to ${platform}`}
                  className="px-3 py-1.5 border border-ink text-ink text-xs font-medium hover:bg-ink hover:text-white transition-colors rounded-none disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                >
                  {isRetrying[platform] ? (
                    <span
                      className="inline-block size-3 border-2 border-ink border-t-transparent rounded-full animate-spin"
                      aria-hidden="true"
                    />
                  ) : (
                    "Retry"
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
