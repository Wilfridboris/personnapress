"use client";

import { cn } from "@/lib/utils";

export type TargetLength = "300-500" | "600-1000" | "1500-2500";

interface LengthOption {
  value: TargetLength;
  label: string;
  range: string;
  description: string;
}

const OPTIONS: LengthOption[] = [
  {
    value: "300-500",
    label: "Quick Read",
    range: "300-500 words",
    description: "Short update or news",
  },
  {
    value: "600-1000",
    label: "Standard",
    range: "600-1,000 words",
    description: "Guide or blog article",
  },
  {
    value: "1500-2500",
    label: "In-Depth",
    range: "1,500-2,500 words",
    description: "Comprehensive or competitive",
  },
];

interface LengthSelectorProps {
  value: TargetLength;
  onChange: (v: TargetLength) => void;
}

export function LengthSelector({ value, onChange }: LengthSelectorProps) {
  return (
    <fieldset className="mb-6">
      <legend className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
        Target length
      </legend>
      <div className="grid grid-cols-3 border border-ink/10">
        {OPTIONS.map((opt, i) => (
          <label
            key={opt.value}
            className={cn(
              "relative flex flex-col gap-0.5 px-3 py-3 cursor-pointer",
              "transition-shadow duration-100",
              i < OPTIONS.length - 1 && "border-r border-ink/10",
              value === opt.value
                ? "bg-[#FFF1B8] border border-ink shadow-[4px_4px_0_#111111] z-10"
                : "bg-white hover:shadow-[4px_4px_0_#111111] hover:z-10"
            )}
          >
            <input
              type="radio"
              name="target_length"
              value={opt.value}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              className="sr-only"
            />
            <span className="font-mono text-sm font-medium text-ink">
              {opt.label}
            </span>
            <span className="font-mono text-xs text-graphite">
              {opt.range}
            </span>
            <span className="font-mono text-xs text-graphite/60 leading-snug mt-0.5">
              {opt.description}
            </span>
          </label>
        ))}
      </div>
      {value === "300-500" && (
        <p
          role="status"
          aria-live="polite"
          className="mt-2 font-mono text-xs text-graphite border-l-2 border-ink/30 pl-3"
        >
          TL;DR and FAQ sections are omitted at this length.
        </p>
      )}
    </fieldset>
  );
}
