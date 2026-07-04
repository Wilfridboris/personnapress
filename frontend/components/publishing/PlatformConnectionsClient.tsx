"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { publishingApi } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "./PlatformConnectionCard";

interface Props {
  clientId: string;
}

const ALL_PLATFORMS = ["wordpress", "webflow", "x", "linkedin"] as const;

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
        `Connected to ${success}.`;
      addToast(message, "success");
    }
    if (error) {
      addToast(decodeURIComponent(error), "error");
    }
    // Do NOT call replaceState or router.replace here.
    // window.history.replaceState is intercepted by the Next.js router and, when
    // there is no cached RSC for the target URL, triggers completeHardNavigation
    // (mpaNavigation: true) which causes location.replace() → hard reload → loop.
    // The params staying in the URL is acceptable: the toast runs once (handledRef),
    // and a manual refresh just re-shows the confirmation, which is fine UX.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["platform-connections", clientId],
    queryFn: () => publishingApi.listConnections(clientId),
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="space-y-4" aria-label="Loading platform connections">
        {ALL_PLATFORMS.map((p) => (
          <PlatformConnectionCardSkeleton key={p} />
        ))}
      </div>
    );
  }

  const items = data?.items ?? ALL_PLATFORMS.map((p) => ({ platform: p, connected: false }));

  return (
    <div className="space-y-4">
      {items.map((connection) => (
        <PlatformConnectionCard
          key={connection.platform}
          clientId={clientId}
          connection={connection}
        />
      ))}
    </div>
  );
}
