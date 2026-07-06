"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

interface FaqItem {
  question: string;
  answer: string;
}

export function FaqAccordion({ items }: { items: FaqItem[] }) {
  const [open, setOpen] = useState<string | null>(null);

  return (
    <div className="divide-y divide-border border border-border">
      {items.map(({ question, answer }, i) => {
        const panelId = `faq-panel-${i}`;
        const isOpen = open === question;
        return (
          <div key={question}>
            <button
              onClick={() => setOpen(isOpen ? null : question)}
              className="w-full flex items-center justify-between px-8 py-6 text-left hover:bg-highlight transition-colors group"
              aria-expanded={isOpen}
              aria-controls={panelId}
            >
              <span className="font-display text-lg font-bold text-ink text-balance pr-4">
                {question}
              </span>
              <ChevronDown
                className={`size-5 text-graphite shrink-0 transition-transform ${
                  isOpen ? "rotate-180" : ""
                }`}
                aria-hidden="true"
              />
            </button>
            {isOpen && (
              <div id={panelId} className="px-8 pb-6">
                <p className="text-graphite leading-relaxed text-pretty">
                  {answer}
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
