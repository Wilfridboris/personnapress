"use client";

import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { subscriptionsApi } from "@/lib/api";
import type { PlanTier } from "@/lib/types";

const PLANS = [
  {
    key: "starter" as PlanTier,
    name: "Starter",
    price: "$29",
    tagline: "For individuals getting started with AI content.",
    features: [
      "2 clients",
      "10 campaigns per month",
      "10 image generations per month",
      "All publishing platforms",
      "Content calendar",
      "Scheduled publishing",
      "Headless blog API",
    ],
    popular: false,
  },
  {
    key: "growth" as PlanTier,
    name: "Growth",
    price: "$49",
    tagline: "For businesses that publish weekly.",
    features: [
      "5 clients",
      "30 campaigns per month",
      "30 image generations per month",
      "Everything in Starter",
    ],
    popular: true,
  },
  {
    key: "agency" as PlanTier,
    name: "Agency",
    price: "$149",
    tagline: "For agencies managing multiple client voices.",
    features: [
      "20 clients",
      "Unlimited campaigns",
      "100 image generations per month",
      "Everything in Growth",
      "Priority support",
    ],
    popular: false,
  },
];

interface PlanPickerClientProps {
  currentTier: PlanTier;
}

export function PlanPickerClient({ currentTier }: PlanPickerClientProps) {
  const [loadingPlan, setLoadingPlan] = useState<PlanTier | null>(null);
  const [error, setError] = useState("");

  async function handleSubscribe(plan: PlanTier) {
    setLoadingPlan(plan);
    setError("");
    try {
      const data = await subscriptionsApi.createCheckout(plan);
      window.location.href = data.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setLoadingPlan(null);
    }
  }

  return (
    <section id="choose-plan" aria-labelledby="plan-picker-heading">
      <p
        id="plan-picker-heading"
        className="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-4"
      >
        Choose your plan
      </p>

      {error && (
        <p role="alert" className="font-body text-sm text-danger mb-4">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-[#E5E5E5] bg-[#E5E5E5]">
        {PLANS.map((plan) => {
          const isCurrent = plan.key === currentTier;
          const isLoading = loadingPlan === plan.key;
          const isDisabled = loadingPlan !== null;

          return (
            <article key={plan.key} className="bg-paper p-6 flex flex-col">
              {plan.popular && (
                <p className="font-mono text-[10px] text-graphite tracking-widest uppercase mb-1">
                  Most popular
                </p>
              )}
              {isCurrent && (
                <p className="font-mono text-[10px] text-graphite tracking-widest uppercase mb-1">
                  Current trial
                </p>
              )}

              <h3 className="font-display text-xl font-bold text-ink mb-1">
                {plan.name}
              </h3>
              <p className="font-display text-3xl font-bold text-ink mb-1">
                {plan.price}
                <span className="font-mono text-xs text-graphite">/mo</span>
              </p>
              <p className="font-body text-sm text-graphite mb-4">{plan.tagline}</p>

              <ul
                className="space-y-1.5 mb-6 flex-1"
                aria-label={`${plan.name} plan features`}
              >
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-graphite">
                    <CheckCircle2
                      className="size-4 text-ink mt-0.5 shrink-0"
                      aria-hidden="true"
                    />
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleSubscribe(plan.key)}
                disabled={isDisabled}
                className="inline-flex w-full items-center justify-center bg-ink text-paper font-medium text-sm px-5 py-2.5 hover:bg-graphite transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                {isLoading ? "Processing..." : `Subscribe to ${plan.name}`}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
