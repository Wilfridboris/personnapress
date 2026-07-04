import { Suspense } from "react";
import type { Metadata } from "next";
import { CampaignList } from "@/components/campaigns/CampaignList";

export const metadata: Metadata = {
  title: "Dashboard",
  robots: { index: false },
};

export default async function DashboardPage() {
  return (
    <>
      <header className="mb-10">
        <h1 className="font-display text-3xl font-bold text-ink mb-1">Dashboard</h1>
        <p className="text-sm text-graphite font-mono">Your content pipeline at a glance.</p>
      </header>
      <Suspense fallback={null}>
        <CampaignList />
      </Suspense>
    </>
  );
}
