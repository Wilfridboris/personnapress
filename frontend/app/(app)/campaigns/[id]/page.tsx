import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { ArrowLeft } from "lucide-react";
import { ApprovalGateClient } from "./ApprovalGateClient";
import { GenerationGate } from "./GenerationGate";
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

export default async function CampaignDetailPage({ params, searchParams }: Props) {
  const { id } = await params;
  const rawJobId = (await searchParams).job_id;
  const jobId = Array.isArray(rawJobId) ? (rawJobId[0] ?? null) : (rawJobId ?? null);
  const campaign = await getCampaign(id);

  if (!campaign) notFound();

  const job = jobId ? await getJob(jobId) : null;
  const jobErrorDetails = job?.error_details ?? null;

  const isFailed = campaign.status === "failed";
  const isPublished = campaign.status === "published";

  // Show overlay only while content hasn't been generated yet (blog_html is the canonical signal)
  const effectiveJobId = jobId && !campaign.blog_html ? jobId : null;

  return (
    <>
      {/* Generation overlay — shown only while job is active */}
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

        {/* Interactive approval gate — client component owns header, content grid, and sticky footer */}
        <ApprovalGateClient campaign={campaign} jobErrorDetails={jobErrorDetails} jobIsActive={!!effectiveJobId} />
      </section>
    </>
  );
}
