"use client";

import { CampaignGenerationOverlay } from "@/components/campaigns/CampaignGenerationOverlay";
import type { Campaign } from "@/lib/types";

const ACTIVE_STATUSES = new Set(["pending", "in_progress"]);

interface GenerationGateProps {
  campaign: Campaign;
  jobId: string | null;
}

export function GenerationGate({ campaign, jobId }: GenerationGateProps) {
  // Show overlay only when jobId is present and campaign is still generating
  if (!jobId || !ACTIVE_STATUSES.has(campaign.status)) {
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
