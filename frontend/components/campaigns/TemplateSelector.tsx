"use client";

import { cn } from "@/lib/utils";

export type ArticleTemplate = "standard" | "how-to" | "listicle" | "thought-leadership";

interface TemplateOption {
  value: ArticleTemplate;
  label: string;
  tagline: string;
  outline: string[];
}

const TEMPLATES: TemplateOption[] = [
  {
    value: "standard",
    label: "Standard",
    tagline: "Hook, body sections, FAQ, conclusion",
    outline: ["TL;DR", "BLUF intro", "3-4 H2 body sections", "FAQ", "Conclusion"],
  },
  {
    value: "how-to",
    label: "How-To Guide",
    tagline: "Step-by-step instructional",
    outline: ["TL;DR", "What you will need", "Steps 1-5", "Common mistakes", "FAQ", "Wrap-up"],
  },
  {
    value: "listicle",
    label: "Listicle",
    tagline: "Numbered Top-N format",
    outline: ["Hook paragraph", "Numbered items (each ~100 words)", "Recap"],
  },
  {
    value: "thought-leadership",
    label: "Thought Leadership",
    tagline: "Opinion-driven personal take",
    outline: ["Bold opener", "Your argument", "Your evidence", "Counter-argument", "Rebuttal", "Call to action"],
  },
];

interface TemplateSelectorProps {
  value: ArticleTemplate;
  onChange: (v: ArticleTemplate) => void;
}

export function TemplateSelector({ value, onChange }: TemplateSelectorProps) {
  return (
    <fieldset className="mb-6">
      <legend className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
        Article structure
      </legend>
      <div className="grid grid-cols-2 border border-ink/10">
        {TEMPLATES.map((tpl, i) => (
          <label
            key={tpl.value}
            className={cn(
              "group/card relative flex flex-col gap-0.5 px-3 py-3 cursor-pointer",
              "transition-shadow duration-100",
              (i === 0 || i === 1) && "border-b border-ink/10",
              (i === 0 || i === 2) && "border-r border-ink/10",
              value === tpl.value
                ? "bg-[#FFF1B8] border border-ink shadow-[4px_4px_0_#111111] z-10"
                : "bg-white hover:shadow-[4px_4px_0_#111111] hover:z-10"
            )}
          >
            <input
              type="radio"
              name="article_template"
              value={tpl.value}
              checked={value === tpl.value}
              onChange={() => onChange(tpl.value)}
              className="sr-only"
            />
            <span className="font-mono text-sm font-medium text-ink">
              {tpl.label}
            </span>
            <span className="font-mono text-xs text-graphite/70 leading-snug">
              {tpl.tagline}
            </span>

            {/* CSS-only hover preview popover -- no JS state needed */}
            <div
              role="tooltip"
              className={cn(
                "pointer-events-none absolute bottom-full left-0 mb-2 w-52 z-20",
                "border border-ink/10 bg-white shadow-[4px_4px_0_#111111] px-3 py-2",
                "opacity-0 invisible translate-y-1",
                "group-hover/card:opacity-100 group-hover/card:visible group-hover/card:translate-y-0",
                "group-focus-within/card:opacity-100 group-focus-within/card:visible group-focus-within/card:translate-y-0",
                "transition-all duration-150"
              )}
            >
              <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-2">
                Structure
              </p>
              <ol className="space-y-1">
                {tpl.outline.map((item) => (
                  <li
                    key={item}
                    className="font-mono text-xs text-ink flex items-start gap-1.5"
                  >
                    <span className="text-graphite/40 select-none" aria-hidden="true">-</span>
                    {item}
                  </li>
                ))}
              </ol>
            </div>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
