import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { SubscriptionStatusBadge } from "@/components/ui/SubscriptionStatusBadge";
import type { SubscriptionResponse } from "@/lib/types";
import { AccountClient } from "./AccountClient";

export const metadata: Metadata = {
  title: "Account — PersonnaPress",
};

export default async function AccountPage() {
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;

  if (!session) {
    redirect("/login");
  }

  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/subscriptions/me`,
    {
      headers: { Cookie: `session=${session}` },
      cache: "no-store",
    }
  );

  if (!res.ok) {
    redirect("/login");
  }

  const subscription = (await res.json()) as SubscriptionResponse;

  const renewalDate = new Intl.DateTimeFormat(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date(subscription.billing_cycle_end));

  const tierLabel =
    subscription.plan_tier.charAt(0).toUpperCase() +
    subscription.plan_tier.slice(1);

  const status = subscription.status as "trialing" | "active" | "canceled" | "past_due";

  return (
    <>
      <h1 className="font-display text-3xl text-ink">Account</h1>

      <hr className="border-[#E5E5E5] my-6" />

      <section>
        <p className="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-2">
          Current plan
        </p>
        <div className="flex items-center gap-3">
          <span className="font-body font-medium text-ink">{tierLabel}</span>
          <SubscriptionStatusBadge status={status} />
        </div>
      </section>

      <hr className="border-[#E5E5E5] my-6" />

      <section>
        <p className="font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite mb-3">
          This billing cycle
        </p>
        <div className="space-y-1">
          <p className="font-body text-sm text-graphite">
            Campaigns: {subscription.campaigns_used} / {subscription.plan_limits.campaigns}
          </p>
          <p className="font-body text-sm text-graphite">
            Clients: {subscription.clients_count} / {subscription.plan_limits.clients}
          </p>
          <p className="font-body text-sm text-graphite">
            Image generations: {subscription.image_gen_used} / {subscription.plan_limits.image_gens}
          </p>
        </div>
        <p className="font-body text-sm text-graphite mt-3">
          Renews {renewalDate}
        </p>
      </section>

      <AccountClient />
    </>
  );
}
