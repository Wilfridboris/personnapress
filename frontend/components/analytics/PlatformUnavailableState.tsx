"use client";

import { useState, useRef, useEffect, useId, useCallback } from "react";
import { Info } from "lucide-react";

type UnavailabilityReason =
  | "page_under_100_likes"
  | "permission_missing"
  | "no_snapshot"
  | string
  | null;

interface Props {
  reason: UnavailabilityReason;
}

const REASON_COPY: Record<string, string> = {
  page_under_100_likes:
    "Facebook only provides post insights for Pages with 100+ likes. Analytics will appear here once this Page reaches that threshold.",
  permission_missing:
    "Analytics permissions have not been granted for this platform. Reconnect the platform and enable insights permissions to start tracking.",
};

const GENERIC_COPY = "Analytics not available for this platform.";

function getTooltipCopy(reason: UnavailabilityReason): string | null {
  if (!reason) return null;
  return REASON_COPY[reason] ?? null;
}

export function PlatformUnavailableState({ reason }: Props) {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const wrapperRef = useRef<HTMLSpanElement>(null);
  const tooltipCopy = getTooltipCopy(reason);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    function onMouseDown(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        close();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onMouseDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, [open, close]);

  return (
    <span className="relative inline-flex items-center gap-1.5 text-xs text-graphite font-mono">
      <span aria-label="Analytics not available">{GENERIC_COPY}</span>
      {tooltipCopy && (
        <span ref={wrapperRef} className="relative">
          <button
            ref={buttonRef}
            type="button"
            aria-label="Why is analytics unavailable?"
            aria-expanded={open}
            aria-controls={tooltipId}
            onClick={() => setOpen((v) => !v)}
            className="inline-flex items-center justify-center w-4 h-4 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
          >
            <Info className="size-3.5 text-graphite" aria-hidden="true" />
          </button>
          {open && (
            <span
              id={tooltipId}
              role="tooltip"
              className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-ink text-paper text-xs font-mono p-2 shadow-brutal-sm"
            >
              {tooltipCopy}
              <span className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-ink" />
            </span>
          )}
        </span>
      )}
    </span>
  );
}
