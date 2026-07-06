"use client";

import { useQuery } from "@tanstack/react-query";
import { subscriptionsApi } from "@/lib/api";
import type { SubscriptionInfo } from "@/lib/types";

export function useSubscription() {
  return useQuery<SubscriptionInfo>({
    queryKey: ["subscription"],
    queryFn: () => subscriptionsApi.getMe(),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useSubscriptionStatus(): string | null {
  const { data } = useSubscription();
  return data?.status ?? null;
}

export function useTrialDaysRemaining(): number | null {
  const { data } = useSubscription();
  if (!data || data.status !== "trialing") return null;
  const now = Date.now();
  const end = new Date(data.billing_cycle_end).getTime();
  const diffMs = end - now;
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
}
