"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { publishingApi } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "./PlatformConnectionCard";

interface Props {
  clientId: string;
}

const ALL_PLATFORMS = ["wordpress", "webflow", "x", "linkedin"] as const;

export function PlatformConnectionsClient({ clientId }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const addToast = useUIStore((s) => s.addToast);

  useEffect(() => {
    const success = searchParams.get("success");
    const error = searchParams.get("error");
    if (success) {
      addToast(`Connected to ${success === "x" ? "X" : "LinkedIn"}.`, "success");
      router.replace(`/clients/${clientId}/connections`);
    }
    if (error) {
      addToast(decodeURIComponent(error), "error");
      router.replace(`/clients/${clientId}/connections`);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["platform-connections", clientId],
    queryFn: () => publishingApi.listConnections(clientId),
    refetchOnWindowFocus: true,
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
