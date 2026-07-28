import type { Metadata } from "next";
import { Suspense } from "react";
import { CampaignList } from "@/components/campaigns/CampaignList";

export const metadata: Metadata = {
  title: "Campaigns",
  robots: { index: false },
};

export default function CampaignsPage() {
  return (
    <>
      <header className="flex items-center justify-between mb-10">
        <h1 className="font-display text-3xl font-bold text-ink">Campaigns</h1>
      </header>
      <Suspense fallback={null}>
        <CampaignList basePath="/campaigns" />
      </Suspense>
    </>
  );
}
