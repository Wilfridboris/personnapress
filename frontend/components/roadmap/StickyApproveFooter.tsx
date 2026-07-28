"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { roadmapsApi } from "@/lib/api";

interface StickyApproveFooterProps {
  roadmapId: string;
  removedIds: Set<string>;
  nonRemovedCount: number;
  weekStartDate?: string | null;
}

export function StickyApproveFooter({
  roadmapId,
  removedIds,
  nonRemovedCount,
  weekStartDate,
}: StickyApproveFooterProps) {
  const router = useRouter();
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const approvingRef = useRef(false);

  async function handleApprove() {
    if (approvingRef.current) return;
    approvingRef.current = true;
    setIsApproving(true);
    setError(null);
    try {
      await roadmapsApi.approve(roadmapId, [...removedIds]);
      const month = weekStartDate?.slice(0, 7);
      router.push(month ? `/calendar?month=${month}` : "/calendar");
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Approval failed. Please try again."
      );
      approvingRef.current = false;
      setIsApproving(false);
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-[#E5E5E5] md:left-14 lg:left-60">
      <div className="max-w-7xl mx-auto px-8 lg:px-12 py-3 flex items-center justify-between gap-4">
        <p
          className="font-body text-[15px] text-graphite"
          aria-live="polite"
          aria-atomic="true"
        >
          {nonRemovedCount} post{nonRemovedCount === 1 ? "" : "s"} selected
        </p>
        <div className="flex items-center gap-3">
          {error && (
            <p className="font-body text-xs text-danger">{error}</p>
          )}
          <Button
            type="button"
            variant="primary"
            onClick={handleApprove}
            disabled={isApproving || nonRemovedCount === 0}
            className="whitespace-nowrap"
          >
            {isApproving ? "Scheduling..." : "Approve All & Schedule"}
          </Button>
        </div>
      </div>
    </div>
  );
}
