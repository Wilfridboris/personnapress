"use client";

import { useEffect, useRef, useState } from "react";
import { Info } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { publishingApi, clientsApi } from "@/lib/api";
import { PlatformIcon } from "@/components/ui/PlatformIcon";
import { useUIStore } from "@/lib/stores/useUIStore";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "./PlatformConnectionCard";
import { DeliveryTokensCard } from "./DeliveryTokensCard";
import { Modal } from "@/components/ui/Modal";

type MetaPageOption = {
  id: string;
  name: string;
  has_instagram: boolean;
  instagram_username: string | null;
};

type MetaPageOptions = {
  clientId: string;
  pages: MetaPageOption[];
};

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
  const queryClient = useQueryClient();
  const [metaBetaUnlocked, setMetaBetaUnlocked] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("meta_beta") === "1";
  });
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerPages, setPickerPages] = useState<MetaPageOption[]>([]);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const [pickerLoading, setPickerLoading] = useState(false);

  useEffect(() => {
    if (handledRef.current) return;
    // Read params imperatively -- avoids creating a reactive useSearchParams subscription
    // that would cause the page to re-subscribe to URL changes and trigger RSC re-renders.
    const params = new URLSearchParams(window.location.search);
    const picker = params.get("meta_picker");
    if (picker === "1") {
      handledRef.current = true;
      const raw = document.cookie
        .split("; ")
        .find((c) => c.startsWith("meta_page_options="))
        ?.split("=")
        .slice(1)
        .join("=");
      if (raw) {
        try {
          const opts = JSON.parse(decodeURIComponent(raw)) as MetaPageOptions;
          if (opts.pages && opts.pages.length > 0) {
            setPickerPages(opts.pages);
            setPickerOpen(true);
            return;
          }
        } catch {
          // fall through to error
        }
      }
      addToast("Meta connection failed. Please try connecting again.", "error");
      return;
    }
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

  async function handlePickerConfirm() {
    if (!selectedPageId) return;
    setPickerLoading(true);
    setPickerError(null);
    try {
      await publishingApi.selectMetaPage(clientId, selectedPageId);
      document.cookie = "meta_page_options=; max-age=0; path=/";
      await queryClient.invalidateQueries({ queryKey: ["platform-connections", clientId] });
      setPickerOpen(false);
      addToast("Meta platforms connected.", "success");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to connect. Please try again.";
      setPickerError(msg);
    } finally {
      setPickerLoading(false);
    }
  }

  function handlePickerCancel() {
    document.cookie = "meta_page_options=; max-age=0; path=/";
    setPickerOpen(false);
    setPickerPages([]);
    setSelectedPageId(null);
    setPickerError(null);
  }

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

  const metaEffectivelyEnabled =
    META_PUBLISHING_ENABLED ||
    metaBetaUnlocked ||
    connectedItems.some((c) => META_PLATFORMS.has(c.platform) && c.connected);

  function handleMetaUnlock() {
    localStorage.setItem("meta_beta", "1");
    setMetaBetaUnlocked(true);
    addToast("Meta platforms unlocked.", "success");
  }

  // Hide MetaPlatformsSection once ALL Meta platforms are connected (individual cards handle them).
  // If some are connected and some aren't, show connected ones as individual cards AND
  // the section for remaining unconnected ones (AC7 requires unconnected always have a connect path).
  const hasAllMetaConnected =
    META_PLATFORMS.size > 0 &&
    [...META_PLATFORMS].every((p) => connectedItems.some((c) => c.platform === p && c.connected));

  const normalItems = connectedItems.filter((c) => !META_PLATFORMS.has(c.platform));

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
              enabled={metaEffectivelyEnabled}
              showBetaBadge={!META_PUBLISHING_ENABLED && metaEffectivelyEnabled}
              onUnlock={handleMetaUnlock}
              connectedItems={connectedItems}
            />
          )}

          <DeliveryTokensCard clientId={clientId} />
        </div>
      )}

      <Modal
        isOpen={pickerOpen}
        onClose={handlePickerCancel}
        title="Select Facebook Page"
        titleId="meta-page-picker-title"
        descriptionId="meta-page-picker-desc"
      >
        <p
          id="meta-page-picker-desc"
          className="text-sm text-[#555555] mb-4"
        >
          Choose which page PersonnaPress should publish to.
        </p>

        <div role="radiogroup" aria-labelledby="meta-page-picker-title">
          {pickerPages.map((page) => (
            <button
              key={page.id}
              role="radio"
              aria-checked={selectedPageId === page.id}
              onClick={() => setSelectedPageId(page.id)}
              className={
                selectedPageId === page.id
                  ? "w-full text-left border border-[#111111] bg-[#FFF1B8] p-3 mb-2 rounded-none"
                  : "w-full text-left border border-[#E5E5E5] p-3 mb-2 rounded-none hover:border-[#999999]"
              }
            >
              <div className="flex items-center gap-1.5">
                <PlatformIcon
                  platform="facebook_page"
                  className="size-4 text-graphite"
                  color="mono"
                  aria-hidden="true"
                />
                <span className="text-sm font-medium text-[#111111]">{page.name}</span>
              </div>
              <div className="flex items-center mt-1">
                {page.has_instagram ? (
                  <>
                    <PlatformIcon
                      platform="instagram"
                      className="size-3 text-graphite"
                      color="mono"
                      aria-hidden="true"
                    />
                    <span className="text-xs text-[#555555] ml-1">
                      Linked Instagram: @{page.instagram_username}
                    </span>
                  </>
                ) : (
                  <span className="text-xs text-[#555555]">
                    No linked Instagram Business Account
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>

        {pickerError && (
          <p className="text-xs text-red-600 mt-2">{pickerError}</p>
        )}

        <div className="flex gap-3 mt-4">
          <button
            onClick={handlePickerCancel}
            className="border border-[#111111] text-[#111111] text-xs font-medium px-4 min-h-[44px] rounded-none hover:bg-[#F5F5F5]"
          >
            Cancel
          </button>
          <button
            onClick={handlePickerConfirm}
            disabled={!selectedPageId || pickerLoading}
            className="bg-[#111111] text-white text-xs font-medium px-4 min-h-[44px] rounded-none disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {pickerLoading ? "Connecting..." : "Confirm"}
          </button>
        </div>
      </Modal>
    </>
  );
}

// ── Meta Platforms Section ────────────────────────────────────────────────────

interface MetaPlatformsSectionProps {
  clientId: string;
  enabled: boolean;
  showBetaBadge: boolean;
  onUnlock: () => void;
  connectedItems: Array<{ platform: string; connected: boolean }>;
}

function MetaPlatformsSection({ clientId, enabled, showBetaBadge, onUnlock, connectedItems }: MetaPlatformsSectionProps) {
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
          <p className="text-xs font-medium uppercase tracking-[0.06em] text-[#111111] flex items-center gap-1.5">
            {hasFBIG ? "Threads" : "Meta Platforms"}
            {showBetaBadge && (
              <span className="text-[10px] font-medium uppercase tracking-[0.06em] px-1.5 py-0.5 bg-[#FFF1B8] text-[#111111] border border-[#E5E5E5]">
                Beta
              </span>
            )}
          </p>
          <p className="text-xs text-[#555555] mt-0.5">
            {hasFBIG ? "Connect your Threads account" : "Instagram, Facebook Page, and Threads"}
          </p>
        </div>

        <div className="shrink-0">
          {enabled ? (
            <div className="flex flex-col gap-2">
              {!hasFBIG && (
                <>
                  <a
                    href={`/api/auth/meta?client_id=${clientId}`}
                    className="inline-flex items-center justify-center px-5 min-h-[44px] border border-[#111111] text-[#111111] text-xs font-medium rounded-none hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
                    aria-label="Connect Facebook and Instagram"
                  >
                    Connect Facebook &amp; Instagram
                  </a>
                  <p className="flex items-start gap-1 mt-2 text-xs text-[#555555]">
                    <Info className="size-3 mt-0.5 shrink-0" aria-hidden="true" />
                    You&apos;ll be asked to select your Business Portfolio and choose which Pages and Instagram accounts to connect.
                  </p>
                </>
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
            <div className="flex flex-col items-end gap-2">
              <button
                type="button"
                onClick={onUnlock}
                className="border border-[#111111] text-[#111111] text-xs font-medium px-4 min-h-[44px] rounded-none hover:bg-[#111111] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
              >
                I&apos;m a beta tester
              </button>
              <a
                href="mailto:support@personnapress.com?subject=Beta%20Access%20Request%20-%20PersonnaPress"
                className="text-xs text-[#555555] underline underline-offset-2 hover:text-[#111111] transition-colors"
              >
                Request early access
              </a>
              <p className="text-xs text-[#555555] mt-2">
                Currently in beta. Available to invited testers only.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
