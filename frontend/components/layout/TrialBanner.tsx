"use client";

import { useSubscriptionStatus } from "@/hooks/useSubscription";

export function TrialBanner() {
  const status = useSubscriptionStatus();

  if (status !== "trial_expired") return null;

  return (
    <div
      role="alert"
      aria-label="Trial expired — upgrade required"
      className="w-full bg-[#111111] px-4 py-3 text-white flex items-center justify-center gap-4"
    >
      <p className="text-sm">
        Your trial has ended. Subscribe to continue publishing.
      </p>
      <a
        href="/account#choose-plan"
        className="shrink-0 border border-white px-4 py-1.5 text-sm font-medium transition-colors hover:bg-white hover:text-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#111111]"
      >
        Subscribe
      </a>
    </div>
  );
}
