"use client";

import { CampaignGenerationOverlay } from "@/components/campaigns/CampaignGenerationOverlay";
import type { Campaign } from "@/lib/types";

interface GenerationGateProps {
  campaign: Campaign;
  jobId: string | null;
}

export function GenerationGate({ campaign, jobId }: GenerationGateProps) {
  if (!jobId) {
    return null;
  }

  return (
    <CampaignGenerationOverlay
      campaignId={campaign.id}
      jobId={jobId}
      brainDump={campaign.brain_dump}
      clientId={campaign.client_id}
    />
  );
}
