"use client";

import { useState } from "react";
import Link from "next/link";
import { fetchAPI } from "@/lib/api";
import { ClientCard } from "./ClientCard";
import type { ClientListItem } from "@/lib/types";

interface ClientListProps {
  clients: ClientListItem[];
  planAtLimit: boolean;
  planTier: string;
  clientLimit: number;
}

export function ClientList({
  clients,
  planAtLimit,
  planTier,
  clientLimit,
}: ClientListProps) {
  const [portalLoading, setPortalLoading] = useState(false);

  async function openStripePortal() {
    setPortalLoading(true);
    try {
      const data = await fetchAPI<{ portal_url: string }>("/subscriptions/portal", {
        method: "POST",
      });
      window.location.href = data.portal_url;
    } catch {
      setPortalLoading(false);
    }
  }

  return (
    <>
      <header className="flex items-center justify-between mb-8">
        <h1 className="font-['Playfair_Display'] text-3xl font-bold text-[#111111]">
          Clients
        </h1>
        {planAtLimit ? (
          <p className="text-[#555555] text-sm">
            You have reached the {clientLimit}-client limit on your{" "}
            {planTier.charAt(0).toUpperCase() + planTier.slice(1)} plan.{" "}
            <button
              type="button"
              onClick={openStripePortal}
              disabled={portalLoading}
              className="text-[#111111] underline hover:no-underline disabled:opacity-50"
            >
              {portalLoading ? "Opening..." : "Upgrade to Agency"}
            </button>
          </p>
        ) : (
          <Link
            href="/clients/new"
            className="inline-flex items-center gap-2 bg-[#111111] text-white text-sm font-medium px-5 py-3 hover:bg-[#555555] transition-colors rounded-none"
          >
            New Client
          </Link>
        )}
      </header>

      {clients.length === 0 ? (
        <div className="border border-[#E5E5E5] p-12 text-center">
          <p className="text-[#555555] mb-4">No clients yet.</p>
          <Link
            href="/clients/new"
            className="inline-flex items-center gap-2 bg-[#111111] text-white text-sm font-medium px-6 py-3 hover:bg-[#555555] transition-colors rounded-none"
          >
            Create your first client
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {clients.map((client) => (
            <ClientCard key={client.id} client={client} />
          ))}
        </div>
      )}
    </>
  );
}
