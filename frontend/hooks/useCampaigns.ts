"use client";

import { useQuery } from "@tanstack/react-query";
import { campaignsApi } from "@/lib/api";

export interface UseCampaignsParams {
  clientId: string | null;
  status?: string;
  page?: number;
  perPage?: number;
}

export function useCampaigns({ clientId, status, page = 1, perPage = 20 }: UseCampaignsParams) {
  return useQuery({
    queryKey: ["campaigns", clientId, { status, page, perPage }],
    queryFn: () =>
      campaignsApi.listPaginated({
        client_id: clientId ?? undefined,
        status,
        page,
        per_page: perPage,
      }),
    enabled: !!clientId,
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });
}
