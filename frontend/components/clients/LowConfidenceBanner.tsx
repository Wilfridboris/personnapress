"use client";

import { AlertTriangle } from "lucide-react";

interface Props {
  onAddContent: () => void;
}

export function LowConfidenceBanner({ onAddContent }: Props) {
  return (
    <div
      className="flex flex-col gap-3 sm:flex-row sm:items-start border border-[#E5E5E5] border-l-4 border-l-[#F59E0B] bg-[#F9F9F6] px-4 py-3 rounded-none"
      role="status"
    >
      <div className="flex items-start gap-3 flex-1">
        <AlertTriangle size={16} className="text-[#F59E0B] mt-0.5 shrink-0" aria-hidden="true" />
        <p className="text-sm text-[#111111]">
          Your voice profile was built from limited content -- fewer than 300 words were analysed.
          Add more writing samples for a more accurate voice match.
        </p>
      </div>
      <button
        type="button"
        onClick={onAddContent}
        aria-label="Add writing samples to improve voice profile accuracy"
        className="shrink-0 border border-[#111111] bg-transparent px-3 py-2 text-sm text-[#111111] min-h-[44px] transition-colors duration-150 hover:bg-[#111111] hover:text-white focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1 rounded-none"
      >
        Add writing samples
      </button>
    </div>
  );
}
