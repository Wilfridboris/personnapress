"use client";

import { useQuery } from "@tanstack/react-query";
import { publishingApi } from "@/lib/api";

export function usePlatformConnections(clientId: string | null) {
  return useQuery({
    queryKey: ["platform-connections", clientId],
    queryFn: () => publishingApi.listConnections(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
  });
}
