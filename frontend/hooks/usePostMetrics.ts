"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAPI } from "@/lib/api";

export interface SeriesPoint {
  captured_at: string;
  impressions: number | null;
  engagements: number | null;
}

export interface BestPost {
  published_post_id: string;
  platform: string;
  campaign_title: string;
  engagements: number | null;
  permalink: string | null;
}

export interface ClientSummary {
  client_id: string;
  total_impressions: number | null;
  total_engagements: number | null;
  posts_tracked: number;
  best_post: BestPost | null;
  freshest_captured_at: string | null;
}

export interface PostMetricItem {
  published_post_id: string;
  platform: string;
  campaign_title: string;
  campaign_excerpt: string | null;
  latest_impressions: number | null;
  latest_engagements: number | null;
  permalink: string | null;
  captured_at: string | null;
  series: SeriesPoint[];
  unavailable_reason: string | null;
}

export interface ClientPostMetrics {
  client_id: string;
  items: PostMetricItem[];
  freshest_captured_at: string | null;
}

export function useAnalyticsSummary(clientId: string | null) {
  return useQuery<ClientSummary>({
    queryKey: ["analytics", clientId, "summary"],
    queryFn: () => fetchAPI<ClientSummary>(`/analytics/clients/${clientId}/summary`),
    enabled: !!clientId,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function usePostMetrics(clientId: string | null) {
  return useQuery<ClientPostMetrics>({
    queryKey: ["analytics", clientId, "posts"],
    queryFn: () => fetchAPI<ClientPostMetrics>(`/analytics/clients/${clientId}/posts`),
    enabled: !!clientId,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}
