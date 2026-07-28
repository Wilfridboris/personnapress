"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { roadmapsApi } from "@/lib/api";
import { TypewriterAnimation } from "@/components/campaigns/TypewriterAnimation";
import { WeekGrid } from "./WeekGrid";
import { StickyApproveFooter } from "./StickyApproveFooter";
import type { RoadmapCampaignSummary } from "@/lib/types";

interface RoadmapReviewClientProps {
  roadmapId: string;
}

function buildMessages(generateImages: boolean, skipBlog: boolean): string[] {
  const msgs = [
    "Analyzing your voice profile...",
    "Drafting LinkedIn posts...",
    "Drafting X posts...",
  ];
  if (!skipBlog) msgs.push("Drafting blog post...");
  if (generateImages) msgs.push("Generating images...");
  msgs.push("Done.");
  return msgs;
}

export function RoadmapReviewClient({ roadmapId }: RoadmapReviewClientProps) {
  const [messageIndex, setMessageIndex] = useState(0);
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set());
  const [localCampaigns, setLocalCampaigns] = useState<RoadmapCampaignSummary[] | null>(null);
  const populatedRef = useRef(false);

  const { data: roadmap } = useQuery({
    queryKey: ["roadmap", roadmapId],
    queryFn: () => roadmapsApi.get(roadmapId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : 2000;
    },
    staleTime: 0,
  });

  // Populate local campaign state once when roadmap first becomes ready
  useEffect(() => {
    if (populatedRef.current || roadmap?.status !== "ready") return;
    populatedRef.current = true;
    setLocalCampaigns(roadmap.campaigns);
  }, [roadmap]);

  const messages = roadmap
    ? buildMessages(roadmap.generate_images, roadmap.skip_blog)
    : ["Analyzing your voice profile..."];

  const campaigns = localCampaigns ?? roadmap?.campaigns ?? [];
  const nonRemovedCount = campaigns.filter((c) => !removedIds.has(c.id)).length;

  function handleRemove(id: string) {
    setRemovedIds((prev) => new Set([...prev, id]));
  }

  function handleUndo(id: string) {
    setRemovedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  function handleUpdateCampaign(id: string, updates: Partial<RoadmapCampaignSummary>) {
    setLocalCampaigns((prev) =>
      (prev ?? []).map((c) => (c.id === id ? { ...c, ...updates } : c))
    );
  }

  if (!roadmap || roadmap.status === "pending" || roadmap.status === "generating") {
    return (
      <div className="max-w-5xl mx-auto">
        <TypewriterAnimation
          statusMessages={messages}
          currentMessageIndex={messageIndex}
          onMessageComplete={() =>
            setMessageIndex((i) => Math.min(i + 1, messages.length - 1))
          }
        />
      </div>
    );
  }

  if (roadmap.status === "failed") {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="border border-danger px-6 py-5">
          <p className="font-body text-sm text-danger font-medium mb-2">
            Generation failed
          </p>
          {roadmap.error_message && (
            <p className="font-body text-sm text-danger mb-4">
              {roadmap.error_message}
            </p>
          )}
          <Link
            href="/roadmap/new"
            className="font-body text-sm text-ink underline hover:text-graphite transition-colors"
          >
            Try again
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="max-w-7xl mx-auto pb-24">
        <header className="mb-6">
          <p className="font-body text-xs text-graphite uppercase tracking-[0.08em] mb-1">
            Week Review
          </p>
          <h1 className="font-display text-3xl font-bold text-ink">
            Review and Approve Your Week
          </h1>
        </header>

        {campaigns.length === 0 ? (
          <div className="border border-[#E5E5E5] px-6 py-10 text-center">
            <p className="font-body text-sm text-graphite">No posts were generated for this roadmap.</p>
            <Link href="/roadmap/new" className="font-body text-sm text-ink underline hover:text-graphite transition-colors mt-2 inline-block">
              Start a new plan
            </Link>
          </div>
        ) : (
          <WeekGrid
            campaigns={campaigns}
            weekStartDate={roadmap.week_start_date}
            removedIds={removedIds}
            onRemove={handleRemove}
            onUndo={handleUndo}
            onUpdateCampaign={handleUpdateCampaign}
          />
        )}
      </div>

      <StickyApproveFooter
        roadmapId={roadmapId}
        removedIds={removedIds}
        nonRemovedCount={nonRemovedCount}
        weekStartDate={roadmap.week_start_date ?? null}
      />
    </>
  );
}
