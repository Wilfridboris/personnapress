"use client";

import { cn } from "@/lib/utils";
import type { CampaignGenerationMode } from "@/lib/types";

type ContentType = "blog_full" | "social_only";

interface ModeOption {
  value: CampaignGenerationMode;
  label: string;
  taglines: Record<ContentType, string>;
}

const MODES: ModeOption[] = [
  {
    value: "generate",
    label: "Generate from my notes",
    taglines: {
      blog_full: "Turn rough notes into a full article and social posts",
      social_only: "Turn rough notes into a post for each platform",
    },
  },
  {
    value: "assist",
    label: "Assist my writing",
    taglines: {
      blog_full: "Keep my writing and only fix grammar and logic",
      social_only: "Keep my wording, just polish and fit each platform",
    },
  },
];

interface GenerationModeSelectorProps {
  value: CampaignGenerationMode;
  onChange: (v: CampaignGenerationMode) => void;
  contentType?: ContentType;
}

export function GenerationModeSelector({ value, onChange, contentType = "blog_full" }: GenerationModeSelectorProps) {
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
              <span className="font-mono text-xs text-graphite">{mode.taglines[contentType]}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
