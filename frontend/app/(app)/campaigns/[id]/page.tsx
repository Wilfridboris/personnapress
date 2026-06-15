import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { BlogHtmlRenderer } from "@/components/ui/BlogHtmlRenderer";
import { ApprovalPanel } from "./approval-panel";
import type { Campaign } from "@/lib/types";

type Props = { params: Promise<{ id: string }> };

async function getCampaign(id: string): Promise<Campaign | null> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/campaigns/${id}`,
      { cache: "no-store" }
    );
    if (res.status === 404) return null;
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

export default async function CampaignDetailPage({ params }: Props) {
  const { id } = await params;
  const campaign = await getCampaign(id);

  if (!campaign) notFound();

  const statusConfig =
    STATUS_CONFIG[campaign.status] ?? {
      label: campaign.status,
      className: "bg-border text-graphite",
    };

  const isPending = campaign.status === "pending_approval";
  const isPublished = campaign.status === "published";
  const isFailed = campaign.status === "failed";

  const rawBlogHtml = campaign.blog_html ?? null;

  return (
    <div className="p-8 max-w-4xl mx-auto">
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

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Blog post - main column */}
        <section className="lg:col-span-2 space-y-6">
          <div className="border border-border">
            <div className="px-6 py-4 border-b border-border">
              <h2 className="font-mono text-xs text-graphite uppercase tracking-wider">
                Blog Post (HTML)
              </h2>
            </div>
            {rawBlogHtml ? (
              <BlogHtmlRenderer
                html={rawBlogHtml}
                className="p-6 prose prose-sm max-w-none font-sans text-ink"
              />
            ) : (
              <div className="p-6">
                <GeneratingPlaceholder lines={8} />
              </div>
            )}
          </div>
        </section>

        {/* Sidebar: social + image */}
        <aside className="space-y-6">
          {/* Featured image */}
          {campaign.image_url && (
            <div className="border border-border">
              <div className="px-4 py-3 border-b border-border">
                <h2 className="font-mono text-xs text-graphite uppercase tracking-wider">
                  Featured Image
                </h2>
              </div>
              <div className="p-4">
                <Image
                  src={campaign.image_url}
                  alt="Featured image"
                  width={600}
                  height={400}
                  className="w-full object-cover"
                />
              </div>
            </div>
          )}

          {/* X Post */}
          <div className="border border-border">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="font-mono text-xs text-graphite uppercase tracking-wider">
                X (Twitter)
              </h2>
            </div>
            <div className="p-4">
              {campaign.x_post ? (
                <p className="font-mono text-sm text-ink leading-relaxed whitespace-pre-wrap">
                  {campaign.x_post}
                </p>
              ) : (
                <GeneratingPlaceholder lines={4} />
              )}
            </div>
          </div>

          {/* LinkedIn Post */}
          <div className="border border-border">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="font-mono text-xs text-graphite uppercase tracking-wider">
                LinkedIn
              </h2>
            </div>
            <div className="p-4">
              {campaign.linkedin_post ? (
                <p className="font-mono text-sm text-ink leading-relaxed whitespace-pre-wrap">
                  {campaign.linkedin_post}
                </p>
              ) : (
                <GeneratingPlaceholder lines={6} />
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
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
