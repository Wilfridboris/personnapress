import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { ArrowRight, Clock, CheckCircle2, Globe, Users } from "lucide-react";
import { DashboardEmptyState } from "./DashboardEmptyState";
import { NudgeCard } from "./NudgeCard";

export const metadata: Metadata = {
  title: "Dashboard",
  robots: { index: false },
};

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

async function authHeaders(): Promise<HeadersInit> {
  const store = await cookies();
  const session = store.get("session");
  return session ? { Cookie: `session=${session.value}` } : {};
}

async function getRecentCampaigns() {
  try {
    const res = await fetch(`${BACKEND}/api/v1/campaigns`, {
      cache: "no-store",
      headers: await authHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

async function getClients() {
  try {
    const res = await fetch(`${BACKEND}/api/v1/clients`, {
      cache: "no-store",
      headers: await authHeaders(),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.clients ?? data ?? [];
  } catch {
    return [];
  }
}

const STATUS_LABELS: Record<string, string> = {
  pending_approval: "Pending Review",
  approved: "Approved",
  published: "Published",
  rejected: "Rejected",
  failed: "Failed",
};

const STATUS_STYLES: Record<string, string> = {
  pending_approval: "bg-highlight text-ink border-highlight",
  approved: "bg-success/10 text-success border-success/20",
  published: "bg-success/10 text-success border-success/20",
  rejected: "bg-danger/10 text-danger border-danger/20",
  failed: "bg-danger/10 text-danger border-danger/20",
};

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ nudge?: string }>;
}) {
  const [campaigns, clients, params] = await Promise.all([
    getRecentCampaigns(),
    getClients(),
    searchParams,
  ]);
  const showNudge = params.nudge === "true";

  const now = new Date();
  const thisMonth = now.getMonth();
  const thisYear = now.getFullYear();

  const stats = {
    total_campaigns: campaigns.length,
    pending_approval: campaigns.filter((c: { status: string }) => c.status === "pending_approval").length,
    published_this_month: campaigns.filter((c: { status: string; created_at: string }) => {
      if (c.status !== "published") return false;
      const d = new Date(c.created_at);
      return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
    }).length,
    total_clients: clients.length,
  };

  const statCards = [
    { label: "Total Campaigns", value: stats.total_campaigns, icon: Globe },
    { label: "Pending Review", value: stats.pending_approval, icon: Clock },
    { label: "Published This Month", value: stats.published_this_month, icon: CheckCircle2 },
    { label: "Active Clients", value: stats.total_clients, icon: Users },
  ];

  return (
    <>
      <DashboardEmptyState />
      {showNudge && campaigns.length === 0 && <NudgeCard />}

      {/* Header */}
      <header className="mb-10">
        <h1 className="font-display text-3xl font-bold text-ink mb-1">
          Dashboard
        </h1>
        <p className="text-sm text-graphite font-mono">
          Your content pipeline at a glance.
        </p>
      </header>

      {/* Stats */}
      <section aria-label="Statistics" className="grid grid-cols-2 lg:grid-cols-4 gap-px border border-border bg-border mb-10">
        {statCards.map(({ label, value, icon: Icon }) => (
          <div key={label} className="bg-paper p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-mono text-graphite uppercase tracking-wider">
                {label}
              </span>
              <Icon className="size-4 text-graphite" aria-hidden="true" />
            </div>
            <p className="font-display text-4xl font-bold text-ink">{value}</p>
          </div>
        ))}
      </section>

      {/* Recent Campaigns */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-display text-xl font-bold text-ink">
            Recent Campaigns
          </h2>
          <Link
            href="/campaigns"
            className="flex items-center gap-1.5 text-sm text-graphite hover:text-ink transition-colors font-mono"
          >
            View all
            <ArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </div>

        {campaigns.length === 0 ? (
          <div className="border border-border p-12 text-center">
            <p className="text-graphite font-mono text-sm mb-4">
              No campaigns yet. Start with a brain dump.
            </p>
            <Link
              href="/campaigns/new"
              className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-6 py-3 hover:bg-graphite transition-colors"
            >
              Create First Campaign
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        ) : (
          <div className="border border-border divide-y divide-border">
            {campaigns.slice(0, 8).map(
              (campaign: {
                id: string;
                blog_html: string | null;
                status: string;
                client_id: string;
                created_at: string;
              }) => (
                <Link
                  key={campaign.id}
                  href={`/campaigns/${campaign.id}`}
                  className="flex items-center justify-between p-5 hover:bg-ink/3 transition-colors group"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-ink text-sm truncate group-hover:text-ink mb-1">
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
                      })}
                    </span>
                    <ArrowRight
                      className="size-3.5 text-graphite opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-hidden="true"
                    />
                  </div>
                </Link>
              )
            )}
          </div>
        )}
      </section>
    </>
  );
}
