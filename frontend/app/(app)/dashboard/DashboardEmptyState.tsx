"use client";

import Link from "next/link";
import { useClientStore } from "@/lib/stores/useClientStore";

export function DashboardEmptyState() {
  const clients = useClientStore((s) => s.clients);
  const isInitialized = useClientStore((s) => s.isInitialized);

  if (!isInitialized || clients.length > 0) return null;

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <h2 className="font-['Playfair_Display'] text-2xl font-bold text-[#111111] mb-3">
        No clients yet.
      </h2>
      <p className="text-[#555555] mb-8">
        Create a client to start generating content.
      </p>
      <Link
        href="/clients/new"
        className="inline-flex items-center bg-[#111111] text-white text-sm font-medium px-6 py-3 hover:bg-[#555555] transition-colors rounded-none"
      >
        Create your first client
      </Link>
    </div>
  );
}
