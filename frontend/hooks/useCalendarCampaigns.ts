"use client";

import { useQuery } from "@tanstack/react-query";
import { campaignsApi } from "@/lib/api";
import type { Campaign } from "@/lib/types";

export function useCalendarCampaigns(clientId: string | null) {
  return useQuery({
    queryKey: ["calendar-campaigns", clientId],
    queryFn: async (): Promise<Campaign[]> => {
      const res = await campaignsApi.listPaginated({
        client_id: clientId ?? undefined,
        status: "published,approved",
        per_page: 100,
      });
      return res.items;
    },
    enabled: !!clientId,
    staleTime: 30_000,
  });
}
