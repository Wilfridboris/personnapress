"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { useTrialDaysRemaining } from "@/hooks/useSubscription";

export function TrialNudgeToast() {
  const daysRemaining = useTrialDaysRemaining();
  const [dismissed, setDismissed] = useState(
    () =>
      typeof window !== "undefined" &&
      sessionStorage.getItem("trial_nudge_dismissed") === "1",
  );

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
    sessionStorage.setItem("trial_nudge_dismissed", "1");
    setDismissed(true);
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-4 right-4 z-50 flex max-w-sm items-start gap-3 bg-[#111111] px-4 py-3 text-white shadow-md animate-in slide-in-from-right-4 fade-in duration-300"
    >
      <p className="flex-1 text-sm leading-snug">
        {message}{" "}
        <a
          href="/account#choose-plan"
          className="underline text-white text-sm font-medium hover:no-underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white"
        >
          Subscribe
        </a>
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
