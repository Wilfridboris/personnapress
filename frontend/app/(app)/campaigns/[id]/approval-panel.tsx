"use client";

import { useState, useRef, useCallback, useEffect, RefObject } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GitBranch, Loader2, CheckCircle2, XCircle, RefreshCw } from "lucide-react";
import { campaignsApi, jobsApi, fetchAPI, APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { Modal } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import type { Campaign, CampaignStatus } from "@/lib/types";
import type { BlogEditorHandle } from "@/components/campaigns/BlogEditor";
import type { SocialPostEditorsHandle } from "@/components/campaigns/SocialPostEditors";

const GITHUB_SUPPORTED_FRAMEWORKS = ["jekyll", "plain_static", "astro", "nextjs", "hugo", "eleventy"];

interface ApprovalPanelProps {
  campaign: Campaign;
  blogEditorRef?: RefObject<BlogEditorHandle | null>;
  socialEditorsRef?: RefObject<SocialPostEditorsHandle | null>;
  onOptimisticStatus?: (status: CampaignStatus) => void;
  jobIsActive?: boolean;
}

export function ApprovalPanel({ campaign, blogEditorRef, socialEditorsRef, onOptimisticStatus, jobIsActive = false }: ApprovalPanelProps) {
  const router = useRouter();
  const addToast = useUIStore((s) => s.addToast);
  const showUpgradePrompt = useUIStore((s) => s.showUpgradePrompt);

  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [clientHasPlatforms, setClientHasPlatforms] = useState<boolean | null>(null);
  const [githubPublishReady, setGithubPublishReady] = useState(false);
  const [isPublishingGitHub, setIsPublishingGitHub] = useState(false);
  const [showSchedulePicker, setShowSchedulePicker] = useState(false);
  const [scheduledAt, setScheduledAt] = useState<string>("");
  const [isScheduling, setIsScheduling] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  const rejectBtnRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const effectiveStatus = campaign.status;

  useEffect(() => {
    if (effectiveStatus === "approved" && clientHasPlatforms === null) {
      fetchAPI<{ items: Array<{ platform: string; connected: boolean; account_identifier?: string; github_detection?: { detected_framework: string } | null }> }>(`/clients/${campaign.client_id}/connections`)
        .then((connections) => {
          const items = connections?.items ?? [];
          setClientHasPlatforms(items.length > 0);
          const ghConn = items.find((c) => c.platform === "github_pages" && c.connected);
          const framework = ghConn?.github_detection?.detected_framework ?? "";
          setGithubPublishReady(
            !!ghConn?.account_identifier &&
            GITHUB_SUPPORTED_FRAMEWORKS.includes(framework)
          );
        })
        .catch(() => {
          setClientHasPlatforms(false);
          setGithubPublishReady(false);
        });
    }
  }, [effectiveStatus, campaign.client_id, clientHasPlatforms]);

  const handleApprove = useCallback(async () => {
    const previousStatus = campaign.status;
    setIsApproving(true);
    onOptimisticStatus?.("approved");

    const blogHtml = blogEditorRef?.current?.getCurrentHtml();
    const socialValues = socialEditorsRef?.current?.getCurrentValues();

    let editsPatched = false;
    try {
      if (blogHtml || socialValues) {
        await campaignsApi.patch(campaign.id, {
          ...(blogHtml ? { blog_html: blogHtml } : {}),
          ...(socialValues ?? {}),
        });
        editsPatched = true;
      }
      const result = await campaignsApi.approve(campaign.id);
      try {
        const connections = await fetchAPI<{ items: unknown[] }>(`/clients/${result.client_id ?? campaign.client_id}/connections`);
        setClientHasPlatforms((connections?.items?.length ?? 0) > 0);
      } catch {
        setClientHasPlatforms(false);
      }
      router.refresh();
    } catch (err) {
      onOptimisticStatus?.(previousStatus);
      if (editsPatched) router.refresh();
      addToast(err instanceof APIError ? err.message : "Approval failed.", "error");
    } finally {
      setIsApproving(false);
    }
  }, [campaign, blogEditorRef, socialEditorsRef, router, addToast, onOptimisticStatus]);

  const handleRejectConfirm = useCallback(async () => {
    const previousStatus = campaign.status;
    setIsRejecting(true);
    setShowRejectDialog(false);
    onOptimisticStatus?.("rejected");
    try {
      await campaignsApi.reject(campaign.id, rejectionReason || undefined);
      setRejectionReason("");
      router.refresh();
    } catch (err) {
      onOptimisticStatus?.(previousStatus);
      addToast(err instanceof APIError ? err.message : "Rejection failed.", "error");
    } finally {
      setIsRejecting(false);
    }
  }, [campaign, rejectionReason, router, addToast, onOptimisticStatus]);

  const handleRegenerate = useCallback(async () => {
    setIsRegenerating(true);
    try {
      const result = await campaignsApi.regenerate(campaign.id);
      router.push(`/campaigns/${result.campaign_id}?job_id=${result.job_id}`);
    } catch (err) {
      if (err instanceof APIError && err.code === "TRIAL_EXPIRED") {
        showUpgradePrompt(err.message);
      } else {
        addToast(err instanceof APIError ? err.message : "Regeneration failed.", "error");
      }
    } finally {
      setIsRegenerating(false);
    }
  }, [campaign.id, router, addToast, showUpgradePrompt]);

  const handlePublishNow = useCallback(async () => {
    setIsPublishing(true);
    try {
      const { job_id } = await campaignsApi.publishNow(campaign.id);
      setActiveJobId(job_id);
    } catch (err) {
      if (err instanceof APIError && err.code === "TRIAL_EXPIRED") {
        showUpgradePrompt(err.message);
      } else {
        addToast(err instanceof APIError ? err.message : "Publish failed.", "error");
      }
      setIsPublishing(false);
    }
  }, [campaign.id, addToast, showUpgradePrompt]);

  const handlePublishGitHub = useCallback(async () => {
    setIsPublishingGitHub(true);
    try {
      const { job_id } = await campaignsApi.publishNow(campaign.id);
      if (!job_id) {
        addToast("Publish started but job tracking unavailable.", "warning");
        setIsPublishingGitHub(false);
        return;
      }
      setActiveJobId(job_id);
    } catch (err) {
      if (err instanceof APIError && err.code === "TRIAL_EXPIRED") {
        showUpgradePrompt(err.message);
      } else {
        addToast(err instanceof APIError ? err.message : "GitHub publish failed.", "error");
      }
      setIsPublishingGitHub(false);
    }
  }, [campaign.id, addToast, showUpgradePrompt]);

  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const isPastTime = Boolean(scheduledAt && new Date(scheduledAt) <= new Date());

  const handleConfirmSchedule = useCallback(async () => {
    setIsScheduling(true);
    try {
      const localDate = new Date(scheduledAt);
      await campaignsApi.schedule(campaign.id, localDate.toISOString());
      router.refresh();
    } catch (err) {
      if (err instanceof APIError && err.code === "TRIAL_EXPIRED") {
        showUpgradePrompt(err.message);
      } else {
        addToast(err instanceof APIError ? err.message : "Scheduling failed.", "error");
      }
    } finally {
      setIsScheduling(false);
    }
  }, [campaign.id, scheduledAt, router, addToast, showUpgradePrompt]);

  const handleCancelSchedule = useCallback(async () => {
    setIsCancelling(true);
    try {
      await campaignsApi.cancelSchedule(campaign.id);
      router.refresh();
    } catch (err) {
      addToast(err instanceof APIError ? err.message : "Could not cancel schedule.", "error");
    } finally {
      setIsCancelling(false);
    }
  }, [campaign.id, router, addToast]);

  // Poll publish job every 2s while in-flight
  useEffect(() => {
    if (!activeJobId) return;
    const interval = setInterval(async () => {
      try {
        const job = await jobsApi.get(activeJobId);
        if (job.status === "complete") {
          clearInterval(interval);
          setIsPublishing(false);
          setIsPublishingGitHub(false);
          setActiveJobId(null);
          router.refresh();
        } else if (job.status === "failed") {
          clearInterval(interval);
          setIsPublishing(false);
          setIsPublishingGitHub(false);
          setActiveJobId(null);
          addToast(
            job.error_details
              ? "Some platforms failed to publish. Check the retry panel."
              : "Publish failed.",
            "error",
          );
          router.refresh();
        }
      } catch {
        // polling errors are transient — keep polling
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [activeJobId, router, addToast]);

  // Post-approved state
  if (effectiveStatus === "approved") {
    const isScheduled = campaign.scheduled_at != null;

    if (isScheduled) {
      return (
        <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
          <p className="text-sm text-graphite">
            <span className="font-medium text-ink">Scheduled</span>
            {" — "}
            <span>
              {new Intl.DateTimeFormat("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
                timeZoneName: "short",
              }).format(new Date(
                campaign.scheduled_at!.endsWith("Z") || campaign.scheduled_at!.includes("+")
                  ? campaign.scheduled_at!
                  : campaign.scheduled_at! + "Z"
              ))}
            </span>
          </p>
          <button
            type="button"
            onClick={handleCancelSchedule}
            disabled={isCancelling}
            className="text-sm text-graphite underline hover:text-ink disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCancelling ? "Cancelling…" : "Cancel schedule"}
          </button>
        </div>
      );
    }

    return (
      <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
        <p className="font-mono text-xs text-graphite uppercase tracking-wider">
          Campaign approved
        </p>
        {clientHasPlatforms === null ? (
          <div className="flex items-center gap-2">
            <div className="h-8 w-24 bg-border animate-pulse" />
            <div className="h-8 w-20 bg-border animate-pulse" />
          </div>
        ) : clientHasPlatforms === false ? (
          <div className="flex items-center gap-4 flex-wrap">
            <p className="text-sm text-ink">Connect a platform to publish. Your campaign is approved and ready.</p>
            <Link
              href={`/clients/${campaign.client_id}/connections`}
              className="inline-flex items-center px-5 py-2.5 bg-ink text-paper text-sm font-medium border border-transparent shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Connect a platform
            </Link>
          </div>
        ) : (
          <div className="w-full">
            <div className="flex items-center justify-end gap-3 flex-wrap">
              {githubPublishReady && (
                <button
                  type="button"
                  onClick={handlePublishGitHub}
                  disabled={isPublishingGitHub || isPublishing}
                  className={cn(
                    "inline-flex items-center gap-2 px-5 py-2.5 border border-ink text-ink text-sm font-medium",
                    "hover:bg-ink hover:text-white transition-colors",
                    "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                  )}
                >
                  {isPublishingGitHub ? (
                    <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <GitBranch className="size-4" aria-hidden="true" />
                  )}
                  {isPublishingGitHub ? "Publishing..." : "Publish to GitHub"}
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowSchedulePicker((v) => !v)}
                className="inline-flex items-center px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none"
              >
                Schedule
              </button>
              <button
                type="button"
                onClick={handlePublishNow}
                disabled={isPublishing || isPublishingGitHub}
                className={cn(
                  "inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm font-medium border border-transparent",
                  "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all",
                  "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                  "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                )}
              >
                {isPublishing ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                ) : null}
                {isPublishing ? "Publishing..." : "Publish now"}
              </button>
            </div>
            {showSchedulePicker && (
              <div className="mt-4 pt-4 border-t border-border space-y-3">
                <div>
                  <label
                    htmlFor="schedule-datetime"
                    className="block text-xs font-medium uppercase tracking-[0.06em] text-graphite mb-1"
                  >
                    Schedule date &amp; time
                  </label>
                  <input
                    id="schedule-datetime"
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                    className="border-b border-ink focus:border-b-2 outline-none bg-transparent py-2 text-sm text-ink w-full"
                  />
                </div>
                <p className="text-xs text-graphite">Schedules in {userTimezone}</p>
                {isPastTime && (
                  <p className="text-xs text-danger" role="alert">
                    Scheduled time must be in the future.
                  </p>
                )}
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={handleConfirmSchedule}
                    disabled={!scheduledAt || isPastTime || isScheduling}
                    className="px-5 py-2.5 bg-ink text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white hover:text-ink hover:border hover:border-ink transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none"
                  >
                    {isScheduling ? (
                      <span className="inline-block size-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
                    ) : (
                      "Confirm schedule"
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowSchedulePicker(false)}
                    className="px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors rounded-none"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // Published state
  if (effectiveStatus === "published") {
    return (
      <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4">
        <p className="text-sm text-graphite">
          <span className="font-medium text-ink">Published</span>
          {" — "}
          <span>
            {new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(
              new Date(campaign.updated_at),
            )}
          </span>
        </p>
      </div>
    );
  }

  // Post-rejected state
  if (effectiveStatus === "rejected") {
    return (
      <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
        <p className="font-mono text-xs text-danger uppercase tracking-wider">
          Campaign rejected{campaign.rejection_reason ? ` — ${campaign.rejection_reason}` : ""}
        </p>
        <button
          type="button"
          onClick={handleRegenerate}
          disabled={isRegenerating}
          className={cn(
            "inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm font-medium border border-transparent",
            "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all",
            "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
            "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          )}
        >
          {isRegenerating ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <RefreshCw className="size-4" aria-hidden="true" />}
          Regenerate from same Brain Dump
        </button>
      </div>
    );
  }

  // Failed state — RetryPanel handles the UI; sticky footer is empty
  if (effectiveStatus === "failed") {
    return null;
  }

  // Pending approval state
  return (
    <>
      <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-end gap-3">
        <button
          ref={rejectBtnRef}
          type="button"
          onClick={() => setShowRejectDialog(true)}
          disabled={isApproving || isRejecting || jobIsActive}
          aria-label="Reject campaign"
          className={cn(
            "inline-flex items-center gap-2 rounded-none px-5 py-2.5 border border-ink text-ink text-sm font-medium",
            "hover:bg-ink hover:text-white transition-colors",
            "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          {isRejecting ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <XCircle className="size-4" aria-hidden="true" />}
          Reject
        </button>
        <button
          type="button"
          onClick={handleApprove}
          disabled={isApproving || isRejecting || jobIsActive}
          aria-label="Approve campaign"
          className={cn(
            "inline-flex items-center gap-2 rounded-none px-5 py-2.5 bg-ink text-white text-sm font-medium border border-transparent",
            "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all",
            "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
            "disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
          )}
        >
          {isApproving ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="size-4" aria-hidden="true" />}
          Approve
        </button>
      </div>

      <Modal
        isOpen={showRejectDialog}
        onClose={() => {
          setShowRejectDialog(false);
          setRejectionReason("");
        }}
        title="Reject this campaign?"
        titleId="reject-dialog-heading"
        triggerRef={rejectBtnRef}
        initialFocusRef={textareaRef}
      >
        <textarea
          ref={textareaRef}
          placeholder="Reason (optional) — helps us improve future generations"
          rows={3}
          className="w-full border-b border-ink focus:border-b-2 focus:outline-none bg-transparent text-sm font-mono text-ink resize-none px-0 py-2 mt-4"
          value={rejectionReason}
          onChange={(e) => setRejectionReason(e.target.value)}
        />
        <div className="flex items-center justify-end gap-3 mt-6">
          <button
            type="button"
            onClick={() => {
              setShowRejectDialog(false);
              setRejectionReason("");
            }}
            className="px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-paper transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleRejectConfirm}
            className="px-5 py-2.5 bg-danger text-white text-sm font-medium hover:bg-danger/90 transition-colors focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2"
          >
            Reject campaign
          </button>
        </div>
      </Modal>
    </>
  );
}
