"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

const TABS = ["Profile", "Voice", "Connections"] as const;
type Tab = (typeof TABS)[number];

interface Props {
  defaultTab?: Tab;
  profileContent: React.ReactNode;
  voiceContent: React.ReactNode;
  connectionsContent: React.ReactNode;
}

export function ClientDetailTabs({
  profileContent,
  voiceContent,
  connectionsContent,
  defaultTab = "Profile",
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
            aria-controls={`tabpanel-${tab.toLowerCase()}`}
            id={`tab-${tab.toLowerCase()}`}
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
        id="tabpanel-profile"
        role="tabpanel"
        aria-labelledby="tab-profile"
        hidden={active !== "Profile"}
      >
        {profileContent}
      </div>
      <div
        id="tabpanel-voice"
        role="tabpanel"
        aria-labelledby="tab-voice"
        hidden={active !== "Voice"}
      >
        {voiceContent}
      </div>
      <div
        id="tabpanel-connections"
        role="tabpanel"
        aria-labelledby="tab-connections"
        hidden={active !== "Connections"}
      >
        {connectionsContent}
      </div>
    </div>
  );
}
