import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { ArrowLeft } from "lucide-react";
import { BlogHtmlRenderer } from "@/components/ui/BlogHtmlRenderer";
import { BlogEditor } from "@/components/campaigns/BlogEditor";
import { ApprovalPanel } from "./approval-panel";
import { GenerationGate } from "./GenerationGate";
import { ImagePanel } from "@/components/campaigns/ImagePanel";
import { VoiceFidelityBadge } from "@/components/campaigns/VoiceFidelityBadge";
import { SocialPostEditors } from "@/components/campaigns/SocialPostEditors";
import type { Campaign, Job } from "@/lib/types";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ job_id?: string | string[] }>;
};

async function authHeaders(): Promise<HeadersInit> {
  const store = await cookies();
  const session = store.get("session");
  return session ? { Cookie: `session=${session.value}` } : {};
}

async function getCampaign(id: string): Promise<Campaign | null> {
  try {
    const res = await fetch(`${BACKEND}/api/v1/campaigns/${id}`, {
      cache: "no-store",
      headers: await authHeaders(),
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function getJob(id: string): Promise<Job | null> {
  try {
    const res = await fetch(`${BACKEND}/api/v1/jobs/${id}`, {
      cache: "no-store",
      headers: await authHeaders(),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const campaign = await getCampaign(id);
  return {
    title: campaign?.blog_html ? "Campaign Review" : "Generating...",
    robots: { index: false },
  };
}

const CAMPAIGN_TERMINAL_STATUSES = new Set(["complete", "completed", "failed", "published", "rejected", "pending_approval", "approved"]);

const STATUS_CONFIG: Record<
  string,
  { label: string; className: string }
> = {
  pending_approval: {
    label: "Pending Review",
    className: "bg-highlight text-ink border-highlight",
  },
  approved: {
    label: "Approved",
    className: "bg-success/10 text-success border-success/20",
  },
  published: {
    label: "Published",
    className: "bg-success/10 text-success border-success/20",
  },
  rejected: {
    label: "Rejected",
    className: "bg-danger/10 text-danger border-danger/20",
  },
  failed: {
    label: "Generation Failed",
    className: "bg-danger/10 text-danger border-danger/20",
  },
};

export default async function CampaignDetailPage({ params, searchParams }: Props) {
  const { id } = await params;
  const rawJobId = (await searchParams).job_id;
  const jobId = Array.isArray(rawJobId) ? (rawJobId[0] ?? null) : (rawJobId ?? null);
  const campaign = await getCampaign(id);

  if (!campaign) notFound();

  // Fetch job to get error_details for ImagePanel empty-state determination
  const job = jobId ? await getJob(jobId) : null;
  const jobErrorDetails = job?.error_details ?? null;

  const statusConfig =
    STATUS_CONFIG[campaign.status] ?? {
      label: campaign.status,
      className: "bg-border text-graphite",
    };

  const isPending = campaign.status === "pending_approval";
  const isPublished = campaign.status === "published";
  const isFailed = campaign.status === "failed";

  const rawBlogHtml = campaign.blog_html ?? null;

  // AC #8: if job_id is present but campaign is already in a terminal state, don't show overlay
  const effectiveJobId =
    jobId && !CAMPAIGN_TERMINAL_STATUSES.has(campaign.status) ? jobId : null;

  return (
    <>
      {/* Generation overlay — shown only while job is active (AC #9, #8) */}
      <GenerationGate campaign={campaign} jobId={effectiveJobId} />

      <section aria-label="Campaign Review - PersonnaPress">
        {/* Back */}
        <Link
          href="/campaigns"
          className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors font-mono mb-10"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to Campaigns
        </Link>

        {/* Header */}
        <header className="mb-8">
          <div className="flex items-start justify-between gap-4 mb-3">
            <h1 className="font-display text-3xl font-bold text-ink text-balance leading-tight">
              {campaign.blog_html ? "Campaign" : "Generating..."}
            </h1>
            <span
              className={`text-xs font-mono border px-3 py-1 shrink-0 mt-1 ${statusConfig.className}`}
            >
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
          {/* Voice Fidelity Badge — advisory only, shown when voice_score fails thresholds */}
          {campaign.voice_score && (
            <div className="mt-3">
              <VoiceFidelityBadge voiceScore={campaign.voice_score} />
            </div>
          )}
        </header>

        {/* Approval panel - shown for pending campaigns */}
        {isPending && (
          <ApprovalPanel campaignId={campaign.id} />
        )}

        {isPublished && (
          <div className="border border-success/30 bg-success/5 p-4 mb-8 font-mono text-sm text-success">
            This campaign has been published.
          </div>
        )}

        {isFailed && (
          <div className="border border-danger/30 bg-danger/5 p-4 mb-8 font-mono text-sm text-danger">
            Content generation failed. Delete this campaign and try again.
          </div>
        )}

        {/* Content grid — pb-24 ensures sticky footer doesn't overlap content on mobile */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 pb-24">
          {/* Blog post - main column */}
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

          {/* Sidebar: image → X post → LinkedIn post */}
          <aside className="lg:col-span-2 space-y-8">
            {/* Featured image */}
            <ImagePanel
              campaignId={campaign.id}
              imageUrl={campaign.image_url}
              imageRegenCount={campaign.image_regen_count}
              jobErrorDetails={jobErrorDetails}
            />

            {/* Social Posts — editable for pending_approval, read-only otherwise */}
            <div className="border border-border">
              <div className="p-6">
                <SocialPostEditors
                  campaignId={campaign.id}
                  initialXPost={campaign.x_post ?? null}
                  initialLinkedInPost={campaign.linkedin_post ?? null}
                  readOnly={!isPending}
                />
              </div>
            </div>
          </aside>
        </div>

        {/* Sticky footer — stub for Story 4.4 wiring; shown only for pending_approval */}
        {isPending && (
          <div className="fixed bottom-0 left-0 md:left-14 lg:left-[240px] right-0 z-10 bg-paper border-t border-border px-6 py-4 flex items-center justify-end gap-3">
            {/* data-story="4.4-wiring" — Story 4.4 dev agent wires these buttons */}
            <button
              type="button"
              aria-label="Reject campaign"
              className="inline-flex items-center rounded-none px-5 py-2.5 border border-ink text-ink text-sm font-medium hover:bg-ink hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              data-story="4.4-wiring"
            >
              Reject
            </button>
            <button
              type="button"
              aria-label="Approve campaign"
              className="inline-flex items-center rounded-none px-5 py-2.5 bg-ink text-white text-sm font-medium border border-transparent shadow-[4px_4px_0px_#111111] hover:bg-white hover:text-ink hover:border-ink transition-all focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              data-story="4.4-wiring"
            >
              Approve
            </button>
          </div>
        )}
      </section>
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
