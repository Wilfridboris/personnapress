"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { publishingApi, clientsApi } from "@/lib/api";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "./PlatformConnectionCard";
import { DeliveryTokensCard } from "./DeliveryTokensCard";

interface Props {
  clientId: string;
}

const ALL_PLATFORMS = [
  "wordpress",
  "webflow",
  "x",
  "linkedin",
  "github_pages",
  "instagram",
  "facebook_page",
  "threads",
] as const;

const META_PLATFORMS = new Set(["instagram", "facebook_page", "threads"]);

const META_PUBLISHING_ENABLED =
  process.env.NEXT_PUBLIC_META_PUBLISHING_ENABLED === "true";

export function PlatformConnectionsClient({ clientId }: Props) {
  const addToast = useUIStore((s) => s.addToast);
  const handledRef = useRef(false);

  useEffect(() => {
    if (handledRef.current) return;
    // Read params imperatively -- avoids creating a reactive useSearchParams subscription
    // that would cause the page to re-subscribe to URL changes and trigger RSC re-renders.
    const params = new URLSearchParams(window.location.search);
    const success = params.get("success");
    const error = params.get("error");
    if (!success && !error) return;
    handledRef.current = true;
    if (success) {
      const message =
        success === "x" ? "Connected to X." :
        success === "linkedin" ? "Connected to LinkedIn." :
        success === "wordpress-com" ? "WordPress.com connected." :
        success === "github" ? "GitHub connected. Select a repository to publish to." :
        success === "meta" ? "Meta platforms connected." :
        success === "threads" ? "Threads connected." :
        `Connected to ${success}.`;
      addToast(message, "success");
    }
    if (error) {
      addToast(decodeURIComponent(error), "error");
    }
    // Do NOT call replaceState or router.replace here.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: client } = useQuery({
    queryKey: ["client", clientId],
    queryFn: () => clientsApi.get(clientId),
    staleTime: 5 * 60_000,
  });

  const { data: connections, isLoading } = useQuery({
    queryKey: ["platform-connections", clientId],
    queryFn: () => publishingApi.listConnections(clientId),
    staleTime: 30_000,
  });

  const connectedItems = connections?.items ?? [];

  // Show MetaPlatformsSection (connect/locked) only when ALL Meta platforms are connected.
  // If some are connected and some aren't, show individual cards for connected ones AND
  // the section for remaining unconnected ones (AC7 requires unconnected always have a connect path).
  const hasAllMetaConnected =
    META_PLATFORMS.size > 0 &&
    [...META_PLATFORMS].every((p) => connectedItems.some((c) => c.platform === p && c.connected));

  const normalItems = isLoading
    ? ALL_PLATFORMS.filter((p) => !META_PLATFORMS.has(p)).map((p) => ({ platform: p, connected: false }))
    : connectedItems.filter((c) => !META_PLATFORMS.has(c.platform));

  const metaConnectedItems = connectedItems.filter(
    (c) => META_PLATFORMS.has(c.platform) && c.connected
  );

  return (
    <>
      <h1 className="font-serif text-[2.25rem] font-bold tracking-[-0.01em] text-[#111111] mb-1">
        Platform Connections
      </h1>
      <p className="text-[#555555] text-sm mb-8">{client?.name ?? " "}</p>

      {isLoading ? (
        <div className="space-y-4" aria-label="Loading platform connections">
          {ALL_PLATFORMS.filter((p) => !META_PLATFORMS.has(p)).map((p) => (
            <PlatformConnectionCardSkeleton key={p} />
          ))}
          <PlatformConnectionCardSkeleton key="meta-skeleton" />
        </div>
      ) : (
        <div className="space-y-4">
          {normalItems.map((connection) => (
            <PlatformConnectionCard
              key={connection.platform}
              clientId={clientId}
              connection={connection}
            />
          ))}

          {/* Connected Meta platform cards (individual disconnect per platform) */}
          {metaConnectedItems.map((connection) => (
            <PlatformConnectionCard
              key={connection.platform}
              clientId={clientId}
              connection={connection}
            />
          ))}

          {/* Meta connect / locked section -- shown when not all Meta platforms are connected */}
          {!hasAllMetaConnected && (
            <MetaPlatformsSection
              clientId={clientId}
              enabled={META_PUBLISHING_ENABLED}
              connectedItems={connectedItems}
            />
          )}

          <DeliveryTokensCard clientId={clientId} />
        </div>
      )}
    </>
  );
}

// ── Meta Platforms Section ────────────────────────────────────────────────────

interface MetaPlatformsSectionProps {
  clientId: string;
  enabled: boolean;
  connectedItems: Array<{ platform: string; connected: boolean }>;
}

function MetaPlatformsSection({ clientId, enabled, connectedItems }: MetaPlatformsSectionProps) {
  const hasFBIG = connectedItems.some(
    (c) => (c.platform === "instagram" || c.platform === "facebook_page") && c.connected
  );
  const hasThreads = connectedItems.some(
    (c) => c.platform === "threads" && c.connected
  );

  return (
    <div className="bg-white border border-[#E5E5E5] rounded-none p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            {!hasFBIG && (
              <>
                <PlatformIcon platform="instagram" className="size-4 text-graphite" color="mono" aria-hidden="true" />
                <PlatformIcon platform="facebook_page" className="size-4 text-graphite" color="mono" aria-hidden="true" />
              </>
            )}
            <PlatformIcon platform="threads" className="size-4 text-graphite" color="mono" aria-hidden="true" />
          </div>
          <p className="text-xs font-medium uppercase tracking-[0.06em] text-[#111111]">
            {hasFBIG ? "Threads" : "Meta Platforms"}
          </p>
          <p className="text-xs text-[#555555] mt-0.5">
            {hasFBIG ? "Connect your Threads account" : "Instagram, Facebook Page, and Threads"}
          </p>
        </div>

        <div className="shrink-0">
          {enabled ? (
            <div className="flex flex-col gap-2">
              {!hasFBIG && (
                <a
                  href={`/api/auth/meta?client_id=${clientId}`}
                  className="inline-flex items-center justify-center px-5 min-h-[44px] border border-[#111111] text-[#111111] text-xs font-medium rounded-none hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                  aria-label="Connect Facebook and Instagram"
                >
                  Connect Facebook &amp; Instagram
                </a>
              )}
              {!hasThreads && (
                <a
                  href={`/api/auth/threads?client_id=${clientId}`}
                  className="inline-flex items-center justify-center px-5 min-h-[44px] border border-[#111111] text-[#111111] text-xs font-medium rounded-none hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                  aria-label="Connect Threads"
                >
                  Connect Threads
                </a>
              )}
            </div>
          ) : (
            <div className="relative group">
              <button
                disabled
                className="inline-flex items-center gap-1.5 px-5 min-h-[44px] border border-[#E5E5E5] text-[#999999] text-xs font-medium rounded-none opacity-50 cursor-not-allowed"
                aria-label="Connect Meta Platforms (unavailable)"
                aria-disabled="true"
                aria-describedby="meta-locked-tooltip"
              >
                <Lock className="size-3.5" aria-hidden="true" />
                Connect Meta Platforms
              </button>
              <div
                id="meta-locked-tooltip"
                role="tooltip"
                className="absolute right-0 top-full mt-1 w-64 bg-[#111111] text-white text-xs px-3 py-2 rounded-none opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 pointer-events-none transition-opacity z-10"
              >
                Meta Business API approval in progress. Available soon.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
