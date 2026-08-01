"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { BlogEditor } from "@/components/campaigns/BlogEditor";
import { BlogHtmlRenderer } from "@/components/ui/BlogHtmlRenderer";
import { ImagePanel } from "@/components/campaigns/ImagePanel";
import { SocialPostEditors } from "@/components/campaigns/SocialPostEditors";
import { VoiceFidelityBadge } from "@/components/campaigns/VoiceFidelityBadge";
import { useRouter } from "next/navigation";
import { ApprovalPanel } from "./approval-panel";
import { RetryPanel } from "@/components/publishing/RetryPanel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BookOpen, ArrowRight, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { useClientStore } from "@/lib/stores/useClientStore";
import { publishingApi } from "@/lib/api";
import type { Campaign, CampaignStatus } from "@/lib/types";
import type { BlogEditorHandle } from "@/components/campaigns/BlogEditor";
import type { SocialPostEditorsHandle } from "@/components/campaigns/SocialPostEditors";

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending_approval: { label: "Pending Review", className: "bg-highlight text-ink border-highlight" },
  approved: { label: "APPROVED", className: "bg-success/10 text-success border-success/20" },
  published: { label: "PUBLISHED", className: "bg-success/10 text-success border-success/20" },
  rejected: { label: "Rejected", className: "bg-danger/10 text-danger border-danger/20" },
  failed: { label: "Generation Failed", className: "bg-danger/10 text-danger border-danger/20" },
};

interface ApprovalGateClientProps {
  campaign: Campaign;
  jobErrorDetails?: string | null;
  jobIsActive?: boolean;
}

function parseErrorDetails(raw: string | null | undefined): Record<string, string> | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Record<string, string>;
  } catch {
    return null;
  }
}

function getCampaignTitle(campaign: Campaign): string {
  if (campaign.blog_html) return "Campaign";
  if (campaign.roadmap_id || campaign.campaign_type === "social_only") {
    if (campaign.x_post) return "X Post";
    if (campaign.linkedin_post) return "LinkedIn Post";
    return "Social Post";
  }
  return "Generating...";
}

export function ApprovalGateClient({ campaign, jobErrorDetails, jobIsActive = false }: ApprovalGateClientProps) {
  const router = useRouter();
  const blogEditorRef = useRef<BlogEditorHandle>(null);
  const socialEditorsRef = useRef<SocialPostEditorsHandle>(null);

  const storeClient = useClientStore((s) => s.clients.find((c) => c.id === campaign.client_id));
  const isLowConfidence = storeClient?.brand_voice_profile?.low_confidence === true;
  const clientName = storeClient?.name ?? campaign.client_name ?? "this client";

  const { data: connections } = useQuery({
    queryKey: ["platform-connections", campaign.client_id],
    queryFn: () => publishingApi.listConnections(campaign.client_id),
    staleTime: 30_000,
  });
  const connectedItems = connections?.items ?? [];
  const metaContext = {
    threads:       connectedItems.some(c => c.platform === "threads"       && c.connected),
    instagram:     connectedItems.some(c => c.platform === "instagram"     && c.connected),
    facebook_page: connectedItems.some(c => c.platform === "facebook_page" && c.connected),
  };

  const [displayStatus, setDisplayStatus] = useState<CampaignStatus>(campaign.status);

  // Sync to server ground truth for terminal states so router.refresh() propagates
  // without requiring a full page reload (e.g. failed publish, successful retry).
  useEffect(() => {
    if (campaign.status === "failed" || campaign.status === "published") {
      setDisplayStatus(campaign.status);
    }
  }, [campaign.status]);

  const statusConfig = STATUS_CONFIG[displayStatus] ?? { label: displayStatus, className: "bg-border text-graphite" };
  const isPending = displayStatus === "pending_approval" && campaign.status === "pending_approval";
  const rawBlogHtml = campaign.blog_html ?? null;
  const isRoadmapSocialPost = !!campaign.roadmap_id && campaign.blog_html === null;
  const isSocialOnly = campaign.campaign_type === "social_only";
  const hideBlogSection = isRoadmapSocialPost || isSocialOnly;

  return (
    <>
      {/* Header with optimistic status badge */}
      <header className="mb-8">
        <div className="flex items-start justify-between gap-4 mb-3">
          <h1 className="font-display text-3xl font-bold text-ink text-balance leading-tight">
            {getCampaignTitle(campaign)}
          </h1>
          <div className="flex items-center gap-2 shrink-0 mt-1">
            {displayStatus === "approved" && campaign.github_pr_url && (
              <StatusBadge status="pr_open" />
            )}
            <span className={`text-xs font-mono border px-3 py-1 ${statusConfig.className}`}>
              {statusConfig.label}
            </span>
          </div>
        </div>
        <p className="text-sm text-graphite font-mono">
          Created{" "}
          {new Date(campaign.created_at).toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
        </p>
        {!isSocialOnly && (campaign.voice_score || isLowConfidence) && (
          <div className="mt-3">
            {campaign.voice_score && (
              <VoiceFidelityBadge voiceScore={campaign.voice_score} />
            )}
            {isLowConfidence && (
              <Link
                href={`/clients/${campaign.client_id}/voice`}
                aria-label={`View voice profile for ${clientName} -- accuracy may vary due to limited samples`}
                className="flex items-center gap-1 text-xs text-[#555555] hover:text-[#111111] transition-colors duration-150 mt-1 focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
              >
                <Info size={12} aria-hidden="true" />
                Voice profile built from limited samples -- accuracy may vary.
              </Link>
            )}
          </div>
        )}
      </header>

      {/* Content grid */}
      <div className={
        hideBlogSection
          ? "grid grid-cols-1 lg:grid-cols-2 gap-8 pb-24"
          : "grid grid-cols-1 lg:grid-cols-5 gap-8 pb-24"
      }>
        {!hideBlogSection && (
          <section className="lg:col-span-3 space-y-6">
            {campaign.article_id && (
              <div className="flex items-center justify-between gap-3 border border-[#111111] bg-[#FFF1B8] px-4 py-3">
                <div className="flex items-center gap-2 min-w-0">
                  <BookOpen className="size-4 shrink-0 text-[#111111]" aria-hidden="true" />
                  <p className="font-mono text-xs text-[#111111] truncate">
                    Live in headless blog. Content edits go here.
                  </p>
                </div>
                <Link
                  href={`/articles/${campaign.article_id}`}
                  className={cn(
                    "shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-[#111111]",
                    "bg-[#111111] text-white hover:bg-white hover:text-[#111111] transition-colors duration-150",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
                  )}
                >
                  Edit article
                  <ArrowRight className="size-3" aria-hidden="true" />
                </Link>
              </div>
            )}
            <div className="border border-border">
              <div className="px-6 py-4 border-b border-border">
                <h2 className="font-mono text-xs text-graphite uppercase tracking-wider">
                  Blog Post (HTML)
                </h2>
              </div>
              {rawBlogHtml ? (
                (isPending && !campaign.article_id) ? (
                  <BlogEditor
                    ref={blogEditorRef}
                    initialHtml={rawBlogHtml}
                    campaignId={campaign.id}
                    clientId={campaign.client_id}
                    readOnly={false}
                  />
                ) : (
                  <BlogHtmlRenderer
                    html={rawBlogHtml}
                    className="p-6 prose prose-sm max-w-none font-sans text-ink prose-headings:font-display prose-headings:text-ink prose-a:text-ink prose-a:underline"
                  />
                )
              ) : (
                <div className="p-6">
                  <GeneratingPlaceholder lines={8} />
                </div>
              )}
            </div>
          </section>
        )}

        <aside className={hideBlogSection ? "space-y-8" : "lg:col-span-2 space-y-8"}>
          {!isSocialOnly && (
            <ImagePanel
              campaignId={campaign.id}
              clientId={campaign.client_id}
              imageUrl={campaign.image_url}
              imageAlt={campaign.image_alt ?? undefined}
              imageRegenCount={campaign.image_regen_count}
              jobErrorDetails={jobErrorDetails ?? null}
              isGenerating={jobIsActive}
            />
          )}
          <div className="border border-border">
            <div className="p-6">
              <SocialPostEditors
                ref={socialEditorsRef}
                campaignId={campaign.id}
                initialXPost={campaign.x_post ?? null}
                initialLinkedInPost={campaign.linkedin_post ?? null}
                readOnly={!isPending}
                showXSection={hideBlogSection ? !!campaign.x_post : true}
                showLinkedInSection={hideBlogSection ? !!campaign.linkedin_post : true}
                metaContext={isPending ? metaContext : undefined}
              />
            </div>
          </div>
        </aside>
      </div>

      {displayStatus === "failed" && campaign.publish_job && (
        <RetryPanel
          campaign={campaign}
          jobId={campaign.publish_job.id}
          jobErrorDetails={parseErrorDetails(campaign.publish_job.error_details)}
          attemptCount={campaign.publish_job.attempt_count}
          onRetrySuccess={() => router.refresh()}
        />
      )}

      <ApprovalPanel
        campaign={{ ...campaign, status: displayStatus }}
        blogEditorRef={blogEditorRef}
        socialEditorsRef={socialEditorsRef}
        onOptimisticStatus={setDisplayStatus}
        jobIsActive={jobIsActive}
      />
    </>
  );
}

function GeneratingPlaceholder({ lines }: { lines: number }) {
  return (
    <div className="space-y-2 animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="relative overflow-hidden h-3 bg-border rounded-none"
          style={{ width: `${60 + (i % 3) * 15}%` }}
        >
          <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-paper/60 to-transparent animate-[shimmer_2s_infinite]" />
        </div>
      ))}
    </div>
  );
}
