"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

const TABS = ["Profile & Voice", "Connections"] as const;
type Tab = (typeof TABS)[number];

function tabSlug(tab: Tab): string {
  return tab.toLowerCase().replace(/\s*&\s*/g, "-").replace(/\s+/g, "-");
}

interface Props {
  defaultTab?: Tab;
  profileVoiceContent: React.ReactNode;
  connectionsContent: React.ReactNode;
}

export function ClientDetailTabs({
  profileVoiceContent,
  connectionsContent,
  defaultTab = "Profile & Voice",
}: Props) {
  const [active, setActive] = useState<Tab>(defaultTab);

  return (
    <div>
      <div className="flex border-b border-border mb-8" role="tablist" aria-label="Client settings">
        {TABS.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={active === tab}
            aria-controls={`tabpanel-${tabSlug(tab)}`}
            id={`tab-${tabSlug(tab)}`}
            onClick={() => setActive(tab)}
            className={cn(
              "font-mono text-xs uppercase tracking-widest px-6 py-3 border-b-2 -mb-px transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-inset",
              active === tab
                ? "border-ink text-ink"
                : "border-transparent text-graphite hover:text-ink hover:border-border"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      <div
        id={`tabpanel-${tabSlug("Profile & Voice")}`}
        role="tabpanel"
        aria-labelledby={`tab-${tabSlug("Profile & Voice")}`}
        hidden={active !== "Profile & Voice"}
      >
        {profileVoiceContent}
      </div>
      <div
        id={`tabpanel-${tabSlug("Connections")}`}
        role="tabpanel"
        aria-labelledby={`tab-${tabSlug("Connections")}`}
        hidden={active !== "Connections"}
      >
        {connectionsContent}
      </div>
    </div>
  );
}
