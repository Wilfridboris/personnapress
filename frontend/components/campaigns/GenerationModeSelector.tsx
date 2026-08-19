"use client";

import { cn } from "@/lib/utils";
import type { CampaignGenerationMode } from "@/lib/types";

interface ModeOption {
  value: CampaignGenerationMode;
  label: string;
  tagline: string;
}

const MODES: ModeOption[] = [
  {
    value: "generate",
    label: "Generate from my notes",
    tagline: "Turn rough notes into a full post",
  },
  {
    value: "assist",
    label: "Assist my writing",
    tagline: "Keep my writing and only fix grammar and logic",
  },
];

interface GenerationModeSelectorProps {
  value: CampaignGenerationMode;
  onChange: (v: CampaignGenerationMode) => void;
}

export function GenerationModeSelector({ value, onChange }: GenerationModeSelectorProps) {
  return (
    <fieldset className="mb-6">
      <legend className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
        Generation mode
      </legend>
      <div className="flex flex-col border border-ink/10">
        {MODES.map((mode, i) => (
          <label
            key={mode.value}
            className={cn(
              "flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors duration-100",
              "hover:bg-ink/[0.02]",
              i > 0 && "border-t border-ink/10",
              value === mode.value ? "bg-[#FFF1B8]" : ""
            )}
          >
            <input
              type="radio"
              name="generation_mode"
              value={mode.value}
              checked={value === mode.value}
              onChange={() => onChange(mode.value)}
              className="mt-0.5 accent-ink"
            />
            <span className="flex flex-col gap-0.5">
              <span className="font-mono text-sm text-ink">{mode.label}</span>
              <span className="font-mono text-xs text-graphite">{mode.tagline}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
