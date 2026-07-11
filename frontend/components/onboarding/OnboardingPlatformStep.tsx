"use client";

import { useQuery } from "@tanstack/react-query";
import { publishingApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "@/components/publishing/PlatformConnectionCard";
import { SkipLink } from "./SkipLink";

interface Props {
  clientId: string;
  oauthError?: string | null;
  onContinue: () => void;
  onSkip: () => void;
}

const ONBOARDING_PLATFORMS = ["wordpress", "x", "linkedin", "webflow"] as const;

export function OnboardingPlatformStep({ clientId, oauthError, onContinue, onSkip }: Props) {
  const { data: connections, isLoading, isError } = useQuery({
    queryKey: ["platform-connections", clientId],
    queryFn: () => publishingApi.listConnections(clientId),
    staleTime: 15_000,
  });

  const hasConnection = (connections?.items ?? []).some((c) => c.connected);

  const platformItems = isLoading
    ? null
    : ONBOARDING_PLATFORMS.map((p) => {
        const found = connections?.items?.find((c) => c.platform === p);
        return found ?? { platform: p, connected: false };
      });

  if (isError) {
    return (
      <div>
        <div role="alert" className="border border-danger/30 bg-danger/5 p-4 mb-4">
          <p className="text-sm font-mono text-danger">Could not load platform connections. Please refresh and try again.</p>
        </div>
        <SkipLink onClick={onSkip}>I&apos;ll connect a platform later.</SkipLink>
      </div>
    );
  }

  return (
    <div>
      {oauthError && (
        <div role="alert" className="border border-[#8B0000]/30 bg-[#8B0000]/5 p-4 mb-4">
          <p className="text-sm font-mono text-[#8B0000]">{oauthError}</p>
        </div>
      )}

      <div className="space-y-4">
        {isLoading
          ? ONBOARDING_PLATFORMS.map((p) => <PlatformConnectionCardSkeleton key={p} />)
          : platformItems!.map((connection) => (
              // Event delegation: intercepts OAuth <a> clicks to inject return_to and save clientId
              <div
                key={connection.platform}
                onClick={(e) => {
                  const anchor = (e.target as HTMLElement).closest("a[href^='/api/auth/']");
                  if (!anchor) return;
                  e.preventDefault();
                  try {
                    sessionStorage.setItem("onboarding_client_id", clientId);
                  } catch {
                    // storage unavailable — OAuth return detection won't work; user restarts from step 1
                  }
                  const href = (anchor as HTMLAnchorElement).href;
                  const url = new URL(href);
                  url.searchParams.set("return_to", "onboarding");
                  window.location.href = url.toString();
                }}
              >
                <PlatformConnectionCard clientId={clientId} connection={connection} />
              </div>
            ))}
      </div>

      {hasConnection && (
        <Button type="button" onClick={onContinue} className="w-full justify-center mt-6">
          Continue
        </Button>
      )}

      <SkipLink onClick={onSkip}>I&apos;ll connect a platform later.</SkipLink>
    </div>
  );
}
