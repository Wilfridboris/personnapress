import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { CampaignList } from "@/components/campaigns/CampaignList";

export const metadata: Metadata = {
  title: "Campaigns",
  robots: { index: false },
};

export default function CampaignsPage() {
  return (
    <>
      <header className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink mb-1">Campaigns</h1>
          <p className="text-sm text-graphite font-mono">All your content campaigns in one place.</p>
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
        <CampaignList basePath="/campaigns" />
      </Suspense>
    </>
  );
}
