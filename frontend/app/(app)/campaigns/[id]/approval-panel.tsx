"use client";

import { useState, useRef, useCallback, useEffect, RefObject } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GitBranch, Loader2, CheckCircle2, XCircle, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { campaignsApi, clientsApi, jobsApi, publishingApi, fetchAPI, APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/utils";
import type { Campaign, CampaignStatus } from "@/lib/types";
import type { BlogEditorHandle } from "@/components/campaigns/BlogEditor";
import type { SocialPostEditorsHandle } from "@/components/campaigns/SocialPostEditors";

const GITHUB_SUPPORTED_FRAMEWORKS = ["jekyll", "plain_static", "astro", "nextjs", "hugo", "eleventy"];

function platformLabel(platform: string): string {
  const MAP: Record<string, string> = {
    wordpress: "WordPress",
    "wordpress-com": "WordPress.com",
    webflow: "Webflow",
    x: "X",
    linkedin: "LinkedIn",
    github_pages: "GitHub Pages",
  };
  return MAP[platform] ?? platform;
}

type GitHubResult =
  | { type: "pr"; prUrl: string; title: string }
  | { type: "commit"; commitSha: string; repoName: string };

function slugFromTitle(title: string): string {
  return title.toLowerCase().replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").slice(0, 60).replace(/-$/, "") || "untitled";
}

function buildTargetFilePath(framework: string, publishPath: string, title: string): string {
  const slug = slugFromTitle(title);
  const today = new Date().toISOString().slice(0, 10);
  if (framework === "jekyll") return `_posts/${today}-${slug}.md`;
  if (framework === "plain_static") {
    const base = publishPath?.replace(/\/$/, "");
    return base ? `${base}/${slug}.html` : `${slug}.html`;
  }
  if (framework === "astro") return `src/content/blog/${slug}.md`;
  if (framework === "hugo") return `content/posts/${slug}.md`;
  if (framework === "eleventy") return `src/posts/${slug}.md`;
  if (framework === "nextjs") {
    const base = publishPath?.replace(/\/$/, "");
    return base ? `${base}/${slug}.md` : `posts/${slug}.md`;
  }
  return `${slug}.md`;
}

function extractMetaDescription(blogHtml: string | null): string {
  if (!blogHtml) return "";
  const match = blogHtml.match(/<!--\s*meta:\s*(.+?)\s*-->/i);
  return match ? match[1].trim() : "";
}

function buildFrontMatterPreview(
  framework: string,
  title: string,
  description: string,
  tags: string[],
  author?: string,
  categories?: string[],
): string {
  // Jekyll canonical date: "YYYY-MM-DD HH:MM:SS +0000"
  const nowIso = new Date().toISOString();
  const jekyllDate = nowIso.replace("T", " ").replace(/\.\d{3}Z$/, " +0000");
  const isoDate = nowIso.replace(/\.\d{3}Z$/, "Z"); // all other frameworks

  const safe = title.replace(/"/g, '\\"');
  const safeDesc = description.replace(/\r?\n/g, " ").replace(/"/g, '\\"');
  const tagsYaml = tags.length > 0
    ? `[${tags.map((t) => `"${t.replace(/\r?\n/g, " ").replace(/"/g, '\\"')}"`).join(", ")}]`
    : "";

  if (framework === "jekyll") {
    const catsLine = categories && categories.length > 0
      ? `\ncategories: [${categories.map((c) => c.replace(/"/g, '\\"')).join(", ")}]`
      : "";
    const tagsLine = tagsYaml ? `\ntags: ${tagsYaml}` : "";
    const authorLine = author ? `\nauthor: "${author.replace(/"/g, '\\"')}"` : "";
    return `---\nlayout: post\ntitle: "${safe}"\ndate: ${jekyllDate}\ndescription: "${safeDesc}"${catsLine}${tagsLine}${authorLine}\n---`;
  }
  if (framework === "astro") {
    const tagsLine = tagsYaml ? `\ntags: ${tagsYaml}` : "";
    return `---\ntitle: "${safe}"\ndescription: "${safeDesc}"\npubDate: "${isoDate}"\nheroImage: ""${tagsLine}\n---`;
  }
  if (framework === "hugo") {
    const catsLine = categories && categories.length > 0
      ? `\ncategories: [${categories.map((c) => c.replace(/"/g, '\\"')).join(", ")}]`
      : "";
    const tagsLine = tagsYaml ? `\ntags: ${tagsYaml}` : "";
    const authorLine = author ? `\nauthor: "${author.replace(/"/g, '\\"')}"` : "";
    return `---\ntitle: "${safe}"\ndate: ${isoDate}\ndescription: "${safeDesc}"\ndraft: false${tagsLine}${catsLine}${authorLine}\n---`;
  }
  const tagsLine = tagsYaml ? `\ntags: ${tagsYaml}` : "";
  return `---\ntitle: "${safe}"\ndate: ${isoDate}\ndescription: "${safeDesc}"${tagsLine}\n---`;
}

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
  const [showSchedulePicker, setShowSchedulePicker] = useState(false);
  const [scheduledAt, setScheduledAt] = useState<string>("");
  const [isScheduling, setIsScheduling] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [showRepublishControls, setShowRepublishControls] = useState(false);
  const [publishedPlatforms, setPublishedPlatforms] = useState<string[]>([]);

  // GitHub pre-publish panel state
  const [showGitHubPanel, setShowGitHubPanel] = useState(false);
  const [publishMode, setPublishMode] = useState<"pr" | "commit">("pr");
  const [showFrontMatter, setShowFrontMatter] = useState(false);
  const [activeGitHubJobId, setActiveGitHubJobId] = useState<string | null>(null);
  const [isGitHubPublishing, setIsGitHubPublishing] = useState(false);
  const [githubResult, setGithubResult] = useState<GitHubResult | null>(null);
  const [repoName, setRepoName] = useState<string | null>(null);
  const [directCommitDefault, setDirectCommitDefault] = useState(false);
  const [detectedFramework, setDetectedFramework] = useState<string>("");
  const [publishPath, setPublishPath] = useState<string>("");

  // Author & Categories optional frontmatter inputs (Jekyll / Hugo only)
  const [authorOverride, setAuthorOverride] = useState<string>("");
  const [categoriesInput, setCategoriesInput] = useState<string>("");
  const authorAutofilledRef = useRef(false);

  // Fetch client to pre-fill author
  const { data: clientData } = useQuery({
    queryKey: ["client", campaign.client_id],
    queryFn: () => clientsApi.get(campaign.client_id),
    staleTime: 60_000,
  });

  // One-time autofill from client name once loaded
  useEffect(() => {
    if (clientData?.name && !authorAutofilledRef.current) {
      setAuthorOverride(clientData.name);
      authorAutofilledRef.current = true;
    }
  }, [clientData?.name]);

  // Derived: parse comma-separated categories
  const parsedCategories = categoriesInput
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const rejectBtnRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const effectiveStatus = campaign.status;

  // Extract H1 title from blog HTML for previews
  const blogTitle = (() => {
    if (!campaign.blog_html) return "Untitled";
    if (typeof document === "undefined") return "Untitled";
    const tmp = document.createElement("div");
    tmp.innerHTML = campaign.blog_html;
    return tmp.querySelector("h1")?.textContent?.trim() || "Untitled";
  })();

  useEffect(() => {
    if (effectiveStatus === "approved" && clientHasPlatforms === null) {
      fetchAPI<{ items: Array<{ platform: string; connected: boolean; account_identifier?: string; github_detection?: { detected_framework: string; publish_path?: string } | null; direct_commit_default?: boolean }> }>(`/clients/${campaign.client_id}/connections`)
        .then((connections) => {
          const items = connections?.items ?? [];
          setClientHasPlatforms(items.length > 0);
          const ghConn = items.find((c) => c.platform === "github_pages" && c.connected);
          const framework = ghConn?.github_detection?.detected_framework ?? "";
          const ready = !!ghConn?.account_identifier && GITHUB_SUPPORTED_FRAMEWORKS.includes(framework);
          setGithubPublishReady(ready);
          if (ghConn) {
            setRepoName(ghConn.account_identifier ?? null);
            setDetectedFramework(framework);
            setPublishPath(ghConn.github_detection?.publish_path ?? "");
            const defaultCommit = ghConn.direct_commit_default ?? false;
            setDirectCommitDefault(defaultCommit);
            if (defaultCommit) setPublishMode("commit");
          }
        })
        .catch(() => {
          setClientHasPlatforms(false);
          setGithubPublishReady(false);
        });
    }
  }, [effectiveStatus, campaign.client_id, clientHasPlatforms]);

  useEffect(() => {
    if (effectiveStatus === "published" && clientHasPlatforms === null) {
      fetchAPI<{ items: Array<{ platform: string; connected: boolean; account_identifier?: string; github_detection?: { detected_framework: string; publish_path?: string } | null; direct_commit_default?: boolean }> }>(`/clients/${campaign.client_id}/connections`)
        .then((connections) => {
          const items = connections?.items ?? [];
          // Read actual published platforms from the job results.
          // Falls back to connected-platform list for campaigns published before this fix
          // (when error_details was null on success).
          const jobDetails = (() => {
            try { const p = JSON.parse(campaign.publish_job?.error_details ?? "{}"); return (p && typeof p === "object" && !Array.isArray(p)) ? p : {}; } catch { return {}; }
          })();
          const actualPublished = (Object.entries(jobDetails) as [string, string][])
            .filter(([, v]) => v === "success" || v === "already_published")
            .map(([p]) => platformLabel(p));
          setPublishedPlatforms(actualPublished.length > 0 ? actualPublished : items.filter((c) => c.connected).map((c) => platformLabel(c.platform)));
          setClientHasPlatforms(items.length > 0);
          const ghConn = items.find((c) => c.platform === "github_pages" && c.connected);
          const framework = ghConn?.github_detection?.detected_framework ?? "";
          const ready = !!ghConn?.account_identifier && GITHUB_SUPPORTED_FRAMEWORKS.includes(framework);
          setGithubPublishReady(ready);
          if (ghConn) {
            setRepoName(ghConn.account_identifier ?? null);
            setDetectedFramework(framework);
            setPublishPath(ghConn.github_detection?.publish_path ?? "");
            const defaultCommit = ghConn.direct_commit_default ?? false;
            setDirectCommitDefault(defaultCommit);
            if (defaultCommit) setPublishMode("commit");
          }
        })
        .catch(() => {
          setClientHasPlatforms(false);
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

  const handleConfirmGitHubPublish = useCallback(async () => {
    setIsGitHubPublishing(true);
    try {
      const { job_id } = await publishingApi.publishGitHub(campaign.id, {
        mode: publishMode,
        author: authorOverride.trim() || undefined,
        categories: parsedCategories.length > 0 ? parsedCategories : undefined,
      });
      setActiveGitHubJobId(job_id);
    } catch (err) {
      if (err instanceof APIError && err.code === "TRIAL_EXPIRED") {
        showUpgradePrompt(err.message);
      } else {
        addToast(err instanceof APIError ? err.message : "GitHub publish failed.", "error");
      }
      setIsGitHubPublishing(false);
    }
  }, [campaign.id, publishMode, addToast, showUpgradePrompt]);

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

  // Poll regular publish job every 2s while in-flight
  useEffect(() => {
    if (!activeJobId) return;
    const interval = setInterval(async () => {
      try {
        const job = await jobsApi.get(activeJobId);
        if (job.status === "complete") {
          clearInterval(interval);
          setIsPublishing(false);
          setActiveJobId(null);
          setClientHasPlatforms(null);
          const jobResults = (() => { try { return JSON.parse(job.error_details ?? "{}"); } catch { return {}; } })();
          const allAlready = Object.values(jobResults).length > 0 && (Object.values(jobResults) as string[]).every((v) => v === "already_published");
          addToast(allAlready ? "Already published to all connected platforms." : "Published successfully.", "success");
          router.refresh();
        } else if (job.status === "failed") {
          clearInterval(interval);
          setIsPublishing(false);
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

  // Poll GitHub publish job every 2s while in-flight
  useEffect(() => {
    if (!activeGitHubJobId) return;
    const interval = setInterval(async () => {
      try {
        const job = await jobsApi.get(activeGitHubJobId);
        if (job.status === "complete") {
          clearInterval(interval);
          setActiveGitHubJobId(null);
          setIsGitHubPublishing(false);
          setShowGitHubPanel(false);
          try {
            const details = job.error_details ? JSON.parse(job.error_details) : {};
            if (publishMode === "pr" && details.pr_url) {
              setGithubResult({ type: "pr", prUrl: details.pr_url, title: details.title ?? "" });
            } else if (publishMode === "commit" && details.commit_sha) {
              setGithubResult({ type: "commit", commitSha: details.commit_sha, repoName: details.repo_full_name ?? repoName ?? "" });
            }
          } catch {
            // parse error — just refresh
          }
          router.refresh();
        } else if (job.status === "failed") {
          clearInterval(interval);
          setActiveGitHubJobId(null);
          setIsGitHubPublishing(false);
          const details = (() => { try { return JSON.parse(job.error_details ?? "{}"); } catch { return {}; } })();
          addToast(details.message ?? "GitHub publish failed.", "error");
        }
      } catch {
        // polling errors are transient — keep polling
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [activeGitHubJobId, publishMode, repoName, router, addToast]);

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

    const targetFilePath = buildTargetFilePath(detectedFramework, publishPath, blogTitle);
    const metaDescription = extractMetaDescription(campaign.blog_html);
    const frontMatterTags = campaign.voice_score?.tags ?? [];
    const frontMatterPreview = buildFrontMatterPreview(
      detectedFramework,
      blogTitle,
      metaDescription,
      frontMatterTags,
      authorOverride.trim() || undefined,
      parsedCategories.length > 0 ? parsedCategories : undefined,
    );
    const hasPrOpen = !!campaign.github_pr_url && !githubResult;
    const prDisplayUrl = githubResult?.type === "pr" ? githubResult.prUrl : campaign.github_pr_url ?? "";

    return (
      <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border">
        {/* Main action row */}
        <div className="px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <p className="font-mono text-xs text-graphite uppercase tracking-wider">
              Campaign approved
            </p>
            {hasPrOpen && <StatusBadge status="pr_open" />}
          </div>
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
            <div className="flex items-center gap-3 flex-wrap">
              {githubPublishReady && (
                <button
                  type="button"
                  onClick={() => setShowGitHubPanel((v) => !v)}
                  disabled={isPublishing || isGitHubPublishing}
                  className={cn(
                    "inline-flex items-center gap-2 px-5 py-2.5 border border-ink text-ink text-sm font-medium",
                    "hover:bg-ink hover:text-white transition-colors",
                    "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                  )}
                >
                  <GitBranch className="size-4" aria-hidden="true" />
                  Publish to GitHub
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowSchedulePicker((v) => !v)}
                className="inline-flex items-center px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none"
              >
                Schedule
              </button>
              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  onClick={handlePublishNow}
                  disabled={isPublishing || isGitHubPublishing}
                  className={cn(
                    "inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm font-medium border border-transparent",
                    "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all",
                    "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                  )}
                >
                  {isPublishing ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
                  {isPublishing ? "Publishing..." : "Publish now"}
                </button>
                <p className="font-mono text-xs text-graphite">Publishes to all connected platforms</p>
              </div>
            </div>
          )}
        </div>

        {/* Schedule picker */}
        {showSchedulePicker && (
          <div className="px-6 pt-0 pb-4 border-t border-border space-y-3">
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

        {/* GitHub pre-publish confirmation panel */}
        {showGitHubPanel && !githubResult && (
          <div className="border-t border-[#E5E5E5] bg-[#F9F9F6] px-6 py-6 space-y-4">
            {/* Target info */}
            <div className="space-y-1">
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">Publishing to</p>
              <p className="text-sm font-medium text-ink">{repoName ?? "GitHub"}</p>
            </div>
            <div className="space-y-1">
              <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">File</p>
              <p
                className="font-mono text-[13px] text-ink"
                role="region"
                aria-label="Publish target file path"
              >
                {targetFilePath}
              </p>
            </div>

            {/* Author & Categories — Jekyll and Hugo only */}
            {(detectedFramework === "jekyll" || detectedFramework === "hugo") && (
              <div className="grid grid-cols-2 gap-x-6 gap-y-4">

                {/* Author */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="gh-fm-author"
                    className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
                  >
                    Author
                    <span className="ml-1 normal-case font-normal text-[#999999]">optional</span>
                  </label>
                  <input
                    id="gh-fm-author"
                    type="text"
                    value={authorOverride}
                    onChange={(e) => setAuthorOverride(e.target.value)}
                    placeholder="e.g. Jane Smith"
                    aria-label="Post author written to frontmatter author field"
                    className={cn(
                      "w-full bg-transparent px-0 py-1.5",
                      "border-0 border-b border-[#E5E5E5] text-sm text-[#111111]",
                      "placeholder:text-[#BBBBBB]",
                      "outline-none focus:border-b-2 focus:border-[#111111]",
                      "transition-[border-color,border-width] duration-150",
                    )}
                  />
                </div>

                {/* Categories */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="gh-fm-categories"
                    className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
                  >
                    Categories
                    <span className="ml-1 normal-case font-normal text-[#999999]">optional</span>
                  </label>
                  <input
                    id="gh-fm-categories"
                    type="text"
                    value={categoriesInput}
                    onChange={(e) => setCategoriesInput(e.target.value)}
                    placeholder="guides, facebook"
                    aria-label="Post categories for frontmatter, comma-separated slugs"
                    className={cn(
                      "w-full bg-transparent px-0 py-1.5",
                      "border-0 border-b border-[#E5E5E5] text-sm text-[#111111]",
                      "placeholder:text-[#BBBBBB]",
                      "outline-none focus:border-b-2 focus:border-[#111111]",
                      "transition-[border-color,border-width] duration-150",
                    )}
                  />
                  <p className="text-[11px] text-[#999999]">Comma-separated slugs</p>
                </div>

              </div>
            )}

            {/* Front matter toggle */}
            <div>
              <button
                type="button"
                aria-expanded={showFrontMatter}
                onClick={() => setShowFrontMatter((v) => !v)}
                className="text-sm text-graphite hover:text-ink underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                {showFrontMatter ? "Hide front matter" : "Show front matter"}
              </button>
              {showFrontMatter && (
                <pre
                  role="region"
                  aria-label="Publish target file path"
                  className="mt-2 font-mono text-[12px] bg-[#F9F9F6] border border-[#E5E5E5] p-3 overflow-x-auto text-ink"
                >
                  {frontMatterPreview}
                </pre>
              )}
            </div>

            {/* Mode selector */}
            <div
              role="radiogroup"
              aria-label="Publish mode"
              className="flex gap-3"
            >
              {(["pr", "commit"] as const).map((mode) => {
                const isSelected = publishMode === mode;
                return (
                  <button
                    key={mode}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => setPublishMode(mode)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPublishMode(mode); } }}
                    className={cn(
                      "flex-1 text-left p-3 border transition-all focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                      isSelected
                        ? "bg-[#FFF1B8] border-[#111111] shadow-[4px_4px_0px_#111111]"
                        : "bg-white border-[#E5E5E5]"
                    )}
                  >
                    <p className="text-sm font-medium text-ink">
                      {mode === "pr" ? "Open Pull Request" : "Commit directly"}
                    </p>
                    <p className="text-[12px] text-graphite mt-0.5">
                      {mode === "pr"
                        ? "Creates a PR for review before going live"
                        : "Commits straight to the default branch"}
                    </p>
                  </button>
                );
              })}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={handleConfirmGitHubPublish}
                disabled={isGitHubPublishing}
                className={cn(
                  "inline-flex items-center gap-2 px-5 py-2.5 bg-[#111111] text-white text-sm font-medium",
                  "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-[#111111] hover:border hover:border-[#111111] transition-all",
                  "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 rounded-none",
                  "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                )}
              >
                {isGitHubPublishing && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
                {isGitHubPublishing ? "Publishing..." : "Confirm and publish"}
              </button>
              <button
                type="button"
                onClick={() => setShowGitHubPanel(false)}
                className="text-sm text-[#555555] hover:text-[#111111] underline focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* PR result state */}
        {(githubResult?.type === "pr" || hasPrOpen) && prDisplayUrl && (
          <div className="border-t border-[#E5E5E5] px-6 py-3">
            <p className="text-sm text-ink">
              PR opened{" — "}
              <a
                href={prDisplayUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-ink underline hover:text-graphite"
              >
                {githubResult?.type === "pr"
                  ? (githubResult.title.length > 45 ? githubResult.title.slice(0, 45) + "…" : githubResult.title)
                  : "View PR"}
              </a>
            </p>
          </div>
        )}

        {/* Commit result state */}
        {githubResult?.type === "commit" && (
          <div className="border-t border-[#E5E5E5] px-6 py-3">
            <p className="text-sm text-ink">
              {"Published to "}
              {githubResult.repoName}
              {" "}
              <a
                href={`https://github.com/${githubResult.repoName}/commit/${githubResult.commitSha}`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-xs text-ink underline hover:text-graphite"
              >
                {githubResult.commitSha.slice(0, 7)}
              </a>
            </p>
          </div>
        )}
      </div>
    );
  }

  // Published state
  if (effectiveStatus === "published") {
    const publishedLine = publishedPlatforms.length > 0
      ? `Published to ${publishedPlatforms.join(", ")}`
      : "Published";

    const targetFilePath = buildTargetFilePath(detectedFramework, publishPath, blogTitle);
    const metaDescription = extractMetaDescription(campaign.blog_html);
    const frontMatterTags = campaign.voice_score?.tags ?? [];
    const frontMatterPreview = buildFrontMatterPreview(
      detectedFramework,
      blogTitle,
      metaDescription,
      frontMatterTags,
      authorOverride.trim() || undefined,
      parsedCategories.length > 0 ? parsedCategories : undefined,
    );

    return (
      <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border">
        <div className="px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
          <p className="text-sm text-graphite">
            <span className="font-medium text-ink">{publishedLine}</span>
            {" — "}
            <span>
              {new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(
                new Date(campaign.updated_at),
              )}
            </span>
          </p>
          <button
            type="button"
            onClick={() => setShowRepublishControls((v) => !v)}
            className="font-mono text-xs text-graphite underline underline-offset-2 hover:text-ink transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
          >
            {showRepublishControls ? "Hide publish options" : "Publish to more platforms"}
          </button>
        </div>

        {showRepublishControls && (
          <div className="px-6 pb-4 pt-0 border-t border-border">
            <p className="font-mono text-xs text-graphite uppercase tracking-wider mb-3 pt-3">
              Publish to additional platforms
            </p>
            <div className="flex items-center gap-3 flex-wrap">
              {githubPublishReady && (
                <button
                  type="button"
                  onClick={() => { setGithubResult(null); setShowGitHubPanel((v) => !v); }}
                  className="inline-flex items-center gap-2 px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none"
                >
                  <GitBranch className="size-4" aria-hidden="true" />
                  Publish to GitHub
                </button>
              )}
              <button
                type="button"
                onClick={() => { setScheduledAt(""); setShowSchedulePicker((v) => !v); }}
                className="inline-flex items-center px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-none"
              >
                Schedule
              </button>
              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  onClick={handlePublishNow}
                  disabled={isPublishing || isGitHubPublishing}
                  className={cn(
                    "inline-flex items-center gap-2 px-5 py-2.5 bg-ink text-paper text-sm font-medium border border-transparent",
                    "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all",
                    "focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                    "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                  )}
                >
                  {isPublishing ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : null}
                  {isPublishing ? "Publishing..." : "Publish now"}
                </button>
                <p className="font-mono text-xs text-graphite">Publishes to platforms not yet reached</p>
              </div>
            </div>

            {showGitHubPanel && !githubResult && (
              <div className="mt-4 border-t border-[#E5E5E5] bg-[#F9F9F6] px-0 py-6 space-y-4">
                <div className="space-y-1">
                  <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">Publishing to</p>
                  <p className="text-sm font-medium text-ink">{repoName ?? "GitHub"}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]">File</p>
                  <p className="font-mono text-[13px] text-ink" role="region" aria-label="Publish target file path">
                    {targetFilePath}
                  </p>
                </div>

                {/* Author & Categories — Jekyll and Hugo only */}
                {(detectedFramework === "jekyll" || detectedFramework === "hugo") && (
                  <div className="grid grid-cols-2 gap-x-6 gap-y-4">

                    {/* Author */}
                    <div className="space-y-1.5">
                      <label
                        htmlFor="gh-fm-author-republish"
                        className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
                      >
                        Author
                        <span className="ml-1 normal-case font-normal text-[#999999]">optional</span>
                      </label>
                      <input
                        id="gh-fm-author-republish"
                        type="text"
                        value={authorOverride}
                        onChange={(e) => setAuthorOverride(e.target.value)}
                        placeholder="e.g. Jane Smith"
                        aria-label="Post author written to frontmatter author field"
                        className={cn(
                          "w-full bg-transparent px-0 py-1.5",
                          "border-0 border-b border-[#E5E5E5] text-sm text-[#111111]",
                          "placeholder:text-[#BBBBBB]",
                          "outline-none focus:border-b-2 focus:border-[#111111]",
                          "transition-[border-color,border-width] duration-150",
                        )}
                      />
                    </div>

                    {/* Categories */}
                    <div className="space-y-1.5">
                      <label
                        htmlFor="gh-fm-categories-republish"
                        className="text-[11px] font-medium uppercase tracking-[0.06em] text-[#555555]"
                      >
                        Categories
                        <span className="ml-1 normal-case font-normal text-[#999999]">optional</span>
                      </label>
                      <input
                        id="gh-fm-categories-republish"
                        type="text"
                        value={categoriesInput}
                        onChange={(e) => setCategoriesInput(e.target.value)}
                        placeholder="guides, facebook"
                        aria-label="Post categories for frontmatter, comma-separated slugs"
                        className={cn(
                          "w-full bg-transparent px-0 py-1.5",
                          "border-0 border-b border-[#E5E5E5] text-sm text-[#111111]",
                          "placeholder:text-[#BBBBBB]",
                          "outline-none focus:border-b-2 focus:border-[#111111]",
                          "transition-[border-color,border-width] duration-150",
                        )}
                      />
                      <p className="text-[11px] text-[#999999]">Comma-separated slugs</p>
                    </div>

                  </div>
                )}

                <button
                  type="button"
                  aria-expanded={showFrontMatter}
                  onClick={() => setShowFrontMatter((v) => !v)}
                  className="text-sm text-graphite hover:text-ink underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                >
                  {showFrontMatter ? "Hide front matter" : "Show front matter"}
                </button>
                {showFrontMatter && (
                  <pre className="mt-2 font-mono text-[12px] bg-[#F9F9F6] border border-[#E5E5E5] p-3 overflow-x-auto text-ink">
                    {frontMatterPreview}
                  </pre>
                )}
                <div role="radiogroup" aria-label="Publish mode" className="flex gap-3">
                  {(["pr", "commit"] as const).map((mode) => {
                    const isSelected = publishMode === mode;
                    return (
                      <button
                        key={mode}
                        type="button"
                        role="radio"
                        aria-checked={isSelected}
                        onClick={() => setPublishMode(mode)}
                        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPublishMode(mode); } }}
                        className={cn(
                          "flex-1 text-left p-3 border transition-all focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                          isSelected ? "bg-[#FFF1B8] border-[#111111] shadow-[4px_4px_0px_#111111]" : "bg-white border-[#E5E5E5]"
                        )}
                      >
                        <p className="text-sm font-medium text-ink">
                          {mode === "pr" ? "Open Pull Request" : "Commit directly"}
                        </p>
                        <p className="text-[12px] text-graphite mt-0.5">
                          {mode === "pr" ? "Creates a PR for review before going live" : "Commits straight to the default branch"}
                        </p>
                      </button>
                    );
                  })}
                </div>
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={handleConfirmGitHubPublish}
                    disabled={isGitHubPublishing}
                    className={cn(
                      "inline-flex items-center gap-2 px-5 py-2.5 bg-[#111111] text-white text-sm font-medium",
                      "shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-[#111111] hover:border hover:border-[#111111] transition-all",
                      "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 rounded-none",
                      "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                    )}
                  >
                    {isGitHubPublishing && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
                    {isGitHubPublishing ? "Publishing..." : "Confirm and publish"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowGitHubPanel(false)}
                    className="text-sm text-[#555555] hover:text-[#111111] underline focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {showSchedulePicker && (
              <div className="mt-4 pt-3 border-t border-border space-y-3">
                <div>
                  <label
                    htmlFor="schedule-datetime-republish"
                    className="block text-xs font-medium uppercase tracking-[0.06em] text-graphite mb-1"
                  >
                    Schedule date &amp; time
                  </label>
                  <input
                    id="schedule-datetime-republish"
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
