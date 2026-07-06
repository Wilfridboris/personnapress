"use client";

import { useState } from "react";
import { useSubscriptionStatus } from "@/hooks/useSubscription";
import { subscriptionsApi } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";

export function TrialBanner() {
  const status = useSubscriptionStatus();
  const addToast = useUIStore((s) => s.addToast);
  const [loading, setLoading] = useState(false);

  if (status !== "trial_expired") return null;

  async function handleSubscribe() {
    setLoading(true);
    try {
      const { portal_url } = await subscriptionsApi.createPortal();
      window.location.href = portal_url;
    } catch {
      addToast("Could not open billing portal. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      role="alert"
      aria-label="Trial expired — upgrade required"
      className="w-full bg-[#111111] px-4 py-3 text-white flex items-center justify-center gap-4"
    >
      <p className="text-sm">
        Your trial has ended. Subscribe to continue publishing.
      </p>
      <button
        onClick={handleSubscribe}
        disabled={loading}
        className="shrink-0 border border-white px-4 py-1.5 text-sm font-medium transition-colors hover:bg-white hover:text-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-[#111111] disabled:opacity-60"
      >
        {loading ? "Opening..." : "Subscribe"}
      </button>
    </div>
  );
}
