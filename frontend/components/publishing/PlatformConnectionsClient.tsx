"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { publishingApi, clientsApi } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "./PlatformConnectionCard";

interface Props {
  clientId: string;
}

const ALL_PLATFORMS = ["wordpress", "webflow", "x", "linkedin"] as const;

export function PlatformConnectionsClient({ clientId }: Props) {
  const addToast = useUIStore((s) => s.addToast);
  const handledRef = useRef(false);

  // ── Diagnostic: log mount/unmount + intercept fetch to trace RSC re-fetch triggers ──
  useEffect(() => {
    console.log("[connections] CLIENT MOUNTED", performance.now().toFixed(0) + "ms");
    return () => {
      console.log("[connections] CLIENT UNMOUNTED", performance.now().toFixed(0) + "ms");
    };
  }, []);

  useEffect(() => {
    const origFetch = window.fetch;
    window.fetch = function (input, init) {
      const url = input?.toString() ?? "";
      if (url.includes("/connections") && !url.includes(":8000")) {
        console.trace("[connections] RSC fetch →", url);
      }
      return origFetch.call(this, input, init);
    };
    return () => {
      window.fetch = origFetch;
    };
  }, []);

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
        </div>
      )}
    </>
  );
}
