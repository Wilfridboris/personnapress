"use client";

interface TagChipProps {
  label: string;
  onRemove?: () => void;
  readOnly?: boolean;
}

export function TagChip({ label, onRemove, readOnly = false }: TagChipProps) {
  return (
    <span className="inline-flex items-center gap-1 bg-[#E5E5E5] px-2 py-0.5 text-sm text-[#111111] mr-2 mb-2 rounded-none">
      {label}
      {!readOnly && onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove: ${label}`}
          className="text-[#555555] hover:text-[#111111] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#111111] leading-none"
        >
          ×
        </button>
      )}
    </span>
  );
}
