"use client";

import { useRouter } from "next/navigation";
import type { ClientListItem } from "@/lib/types";

interface ClientCardProps {
  client: ClientListItem;
}

const BVP_LABELS: Record<string, string> = {
  ready: "VOICE PROFILE READY",
  analyzing: "ANALYZING...",
  incomplete: "PROFILE INCOMPLETE",
};

const BVP_CLASSES: Record<string, string> = {
  ready: "text-[#2E4F2E]",
  analyzing: "text-[#555555] font-mono animate-pulse",
  incomplete: "text-[#555555]",
};

export function ClientCard({ client }: ClientCardProps) {
  const router = useRouter();

  function handleClick() {
    router.push(`/clients/${client.id}`);
  }

  return (
    <article
      className="bg-white border border-[#E5E5E5] p-6 cursor-pointer transition-shadow hover:shadow-[4px_4px_0px_#111111] rounded-none"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`Open ${client.name}`}
    >
      <p className="font-medium text-[#111111] text-base mb-1">{client.name}</p>
      {client.website_url && (
        <p className="text-sm text-[#555555] mb-1">{client.website_url}</p>
      )}
      <p
        className={`text-xs uppercase tracking-wider mb-1 ${BVP_CLASSES[client.brand_voice_profile_status] ?? "text-[#555555]"}`}
      >
        {BVP_LABELS[client.brand_voice_profile_status] ?? "PROFILE INCOMPLETE"}
      </p>
      <p className="text-sm text-[#555555]">
        {client.campaign_count} campaign{client.campaign_count !== 1 ? "s" : ""}
      </p>
    </article>
  );
}
