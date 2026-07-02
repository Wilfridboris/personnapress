import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { Plus, ArrowRight, FileText } from "lucide-react";
import type { Campaign } from "@/lib/types";

export const metadata: Metadata = {
  title: "Campaigns",
  robots: { index: false },
};

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

async function getCampaigns(): Promise<Campaign[]> {
  try {
    const store = await cookies();
    const session = store.get("session");
    const res = await fetch(`${BACKEND}/api/v1/campaigns`, {
      cache: "no-store",
      headers: session ? { Cookie: `session=${session.value}` } : {},
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

const STATUS_STYLES: Record<string, string> = {
  pending_approval: "bg-highlight text-ink border-highlight",
  approved: "bg-success/10 text-success border-success/20",
  published: "bg-success/10 text-success border-success/20",
  rejected: "bg-danger/10 text-danger border-danger/20",
  failed: "bg-danger/10 text-danger border-danger/20",
};

const STATUS_LABELS: Record<string, string> = {
  pending_approval: "Pending Review",
  approved: "Approved",
  published: "Published",
  rejected: "Rejected",
  failed: "Failed",
};

export default async function CampaignsPage() {
  const campaigns = await getCampaigns();

  return (
    <>
      <header className="flex items-center justify-between mb-10">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink mb-1">
            Campaigns
          </h1>
          <p className="text-sm text-graphite font-mono">
            {campaigns.length} total campaign{campaigns.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link
          href="/campaigns/new"
          className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-3 hover:bg-graphite transition-colors"
        >
          <Plus className="size-4" aria-hidden="true" />
          New Campaign
        </Link>
      </header>

      {campaigns.length === 0 ? (
        <div className="border border-border p-16 text-center">
          <FileText className="size-8 text-graphite mx-auto mb-4" aria-hidden="true" />
          <p className="text-graphite font-mono text-sm mb-6">
            No campaigns yet. Start your first brain dump.
          </p>
          <Link
            href="/campaigns/new"
            className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-6 py-3 hover:bg-graphite transition-colors"
          >
            <Plus className="size-4" aria-hidden="true" />
            Create First Campaign
          </Link>
        </div>
      ) : (
        <div className="border border-border divide-y divide-border">
          {campaigns.map((campaign) => (
            <Link
              key={campaign.id}
              href={`/campaigns/${campaign.id}`}
              className="flex items-center justify-between p-5 hover:bg-ink/3 transition-colors group"
            >
              <div className="min-w-0 flex-1">
                <p className="font-medium text-ink text-sm truncate mb-1">
                  {campaign.blog_html ? "Campaign Ready" : "Generating..."}
                </p>
                <p className="text-xs text-graphite font-mono">
                  Client #{campaign.client_id.slice(0, 8)}
                </p>
              </div>
              <div className="flex items-center gap-4 ml-4 shrink-0">
                <span
                  className={`text-xs font-mono border px-2 py-0.5 ${STATUS_STYLES[campaign.status] ?? "bg-border text-graphite"}`}
                >
                  {STATUS_LABELS[campaign.status] ?? campaign.status}
                </span>
                <span className="text-xs text-graphite font-mono">
                  {new Date(campaign.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
                <ArrowRight
                  className="size-3.5 text-graphite opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-hidden="true"
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
