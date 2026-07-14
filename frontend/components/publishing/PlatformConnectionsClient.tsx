"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { publishingApi, clientsApi } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "./PlatformConnectionCard";
import { DeliveryTokensCard } from "./DeliveryTokensCard";

interface Props {
  clientId: string;
}

const ALL_PLATFORMS = ["wordpress", "webflow", "x", "linkedin", "github_pages"] as const;

export function PlatformConnectionsClient({ clientId }: Props) {
  const addToast = useUIStore((s) => s.addToast);
  const handledRef = useRef(false);

  useEffect(() => {
    if (handledRef.current) return;
    // Read params imperatively — avoids creating a reactive useSearchParams subscription
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

  return (
    <>
      <h1 className="font-serif text-[2.25rem] font-bold tracking-[-0.01em] text-[#111111] mb-1">
        Platform Connections
      </h1>
      <p className="text-[#555555] text-sm mb-8">{client?.name ?? " "}</p>

      {isLoading ? (
        <div className="space-y-4" aria-label="Loading platform connections">
          {ALL_PLATFORMS.map((p) => (
            <PlatformConnectionCardSkeleton key={p} />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {(connections?.items ?? ALL_PLATFORMS.map((p) => ({ platform: p, connected: false }))).map(
            (connection) => (
              <PlatformConnectionCard
                key={connection.platform}
                clientId={clientId}
                connection={connection}
              />
            )
          )}
          <DeliveryTokensCard clientId={clientId} />
        </div>
      )}
    </>
  );
}
