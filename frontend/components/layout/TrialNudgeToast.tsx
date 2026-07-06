"use client";

import { useState, useRef } from "react";
import { X } from "lucide-react";
import { useTrialDaysRemaining } from "@/hooks/useSubscription";
import { subscriptionsApi } from "@/lib/api";

export function TrialNudgeToast() {
  const daysRemaining = useTrialDaysRemaining();
  const [dismissed, setDismissed] = useState(
    () =>
      typeof window !== "undefined" &&
      sessionStorage.getItem("trial_nudge_dismissed") === "1",
  );
  const [portalLoading, setPortalLoading] = useState(false);
  const [portalError, setPortalError] = useState(false);
  const cancelledRef = useRef(false);

  const shouldShow = daysRemaining !== null && daysRemaining <= 4 && !dismissed;
  if (!shouldShow) return null;

  const isUrgent = daysRemaining <= 1;
  const message =
    daysRemaining === 0
      ? "Your trial has ended. Subscribe to keep publishing."
      : isUrgent
        ? "1 day left on your trial. Subscribe now to avoid interruption."
        : `${daysRemaining} days left on your trial. Subscribe to keep publishing.`;

  function handleDismiss() {
    cancelledRef.current = true;
    sessionStorage.setItem("trial_nudge_dismissed", "1");
    setDismissed(true);
  }

  async function handleSubscribe() {
    setPortalLoading(true);
    setPortalError(false);
    try {
      const { portal_url } = await subscriptionsApi.createPortal();
      if (!cancelledRef.current) {
        window.location.href = portal_url;
      }
    } catch {
      setPortalError(true);
    } finally {
      setPortalLoading(false);
    }
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-4 right-4 z-50 flex max-w-sm items-start gap-3 bg-[#111111] px-4 py-3 text-white shadow-md animate-in slide-in-from-right-4 fade-in duration-300"
    >
      <p className="flex-1 text-sm leading-snug">
        {portalError ? "Could not open billing portal. Please try again." : message}{" "}
        {!portalError && (
          <button
            onClick={handleSubscribe}
            disabled={portalLoading}
            className="font-medium underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white"
          >
            {portalLoading ? "Opening..." : "Subscribe"}
          </button>
        )}
      </p>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss trial notification"
        className="mt-0.5 shrink-0 text-white/70 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white"
      >
        <X className="size-4" aria-hidden="true" />
      </button>
    </div>
  );
}
