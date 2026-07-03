"use client";

import { useRef, useState } from "react";
import { BlogEditor } from "@/components/campaigns/BlogEditor";
import { BlogHtmlRenderer } from "@/components/ui/BlogHtmlRenderer";
import { ImagePanel } from "@/components/campaigns/ImagePanel";
import { SocialPostEditors } from "@/components/campaigns/SocialPostEditors";
import { VoiceFidelityBadge } from "@/components/campaigns/VoiceFidelityBadge";
import { useRouter } from "next/navigation";
import { ApprovalPanel } from "./approval-panel";
import { RetryPanel } from "@/components/publishing/RetryPanel";
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

export function ApprovalGateClient({ campaign, jobErrorDetails, jobIsActive = false }: ApprovalGateClientProps) {
  const router = useRouter();
  const blogEditorRef = useRef<BlogEditorHandle>(null);
  const socialEditorsRef = useRef<SocialPostEditorsHandle>(null);

  const [displayStatus, setDisplayStatus] = useState<CampaignStatus>(campaign.status);

  const statusConfig = STATUS_CONFIG[displayStatus] ?? { label: displayStatus, className: "bg-border text-graphite" };
  const isPending = displayStatus === "pending_approval" && campaign.status === "pending_approval";
  const rawBlogHtml = campaign.blog_html ?? null;

  return (
    <>
      {/* Header with optimistic status badge */}
      <header className="mb-8">
        <div className="flex items-start justify-between gap-4 mb-3">
          <h1 className="font-display text-3xl font-bold text-ink text-balance leading-tight">
            {campaign.blog_html ? "Campaign" : "Generating..."}
          </h1>
          <span className={`text-xs font-mono border px-3 py-1 shrink-0 mt-1 ${statusConfig.className}`}>
            {statusConfig.label}
          </span>
        </div>
        <p className="text-sm text-graphite font-mono">
          Created{" "}
          {new Date(campaign.created_at).toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
        </p>
        {campaign.voice_score && (
          <div className="mt-3">
            <VoiceFidelityBadge voiceScore={campaign.voice_score} />
          </div>
        )}
      </header>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 pb-24">
        <section className="lg:col-span-3 space-y-6">
          <div className="border border-border">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="font-mono text-xs text-graphite uppercase tracking-wider">
                Blog Post (HTML)
              </h2>
            </div>
            {rawBlogHtml ? (
              isPending ? (
                <BlogEditor
                  ref={blogEditorRef}
                  initialHtml={rawBlogHtml}
                  campaignId={campaign.id}
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

        <aside className="lg:col-span-2 space-y-8">
          <ImagePanel
            campaignId={campaign.id}
            imageUrl={campaign.image_url}
            imageRegenCount={campaign.image_regen_count}
            jobErrorDetails={jobErrorDetails ?? null}
          />
          <div className="border border-border">
            <div className="p-6">
              <SocialPostEditors
                ref={socialEditorsRef}
                campaignId={campaign.id}
                initialXPost={campaign.x_post ?? null}
                initialLinkedInPost={campaign.linkedin_post ?? null}
                readOnly={!isPending}
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
