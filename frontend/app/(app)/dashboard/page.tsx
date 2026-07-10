import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { CampaignList } from "@/components/campaigns/CampaignList";

export const metadata: Metadata = {
  title: "Dashboard",
  robots: { index: false },
};

export default async function DashboardPage() {
  return (
    <>
      <header className="mb-10 flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink mb-1">Dashboard</h1>
          <p className="text-sm text-graphite font-mono">Your content pipeline at a glance.</p>
        </div>
        <Link
          href="/campaigns/new"
          className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-2.5 shadow-brutal hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all shrink-0 focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
        >
          <ArrowRight className="size-3.5" aria-hidden="true" />
          New Campaign
        </Link>
      </header>
      <Suspense fallback={null}>
        <CampaignList />
      </Suspense>
    </>
  );
}
