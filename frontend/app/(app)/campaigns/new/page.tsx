"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { useClientStore } from "@/lib/stores/useClientStore";
import { campaignsApi, publishingApi, APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";

function platformLabel(platform: string): string {
  const MAP: Record<string, string> = {
    wordpress: "WordPress",
    "wordpress-com": "WordPress.com",
    webflow: "Webflow",
    x: "X",
    linkedin: "LinkedIn",
    github_pages: "GitHub Pages",
  };
  return MAP[platform] ?? platform;
}

const MAX_CHARS = 10000;
const MIN_CHARS = 20;

export default function NewCampaignPage() {
  const router = useRouter();
  const { clients, activeClientId } = useClientStore();
  const showUpgradePrompt = useUIStore((s) => s.showUpgradePrompt);
  const activeClient = clients.find((c) => c.id === activeClientId) ?? null;

  const [brainDump, setBrainDump] = useState("");
  const [targetKeyword, setTargetKeyword] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limitExceeded, setLimitExceeded] = useState<{ message: string; nextTier: string } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Track which clientId we last auto-filled from, so we re-fill on client
  // switch and on async client-list load (when activeClientId is set before
  // clients arrive in the store).
  const lastAutoFilledClientId = useRef<string | null>(null);

  useEffect(() => {
    const bvpAudience = activeClient?.brand_voice_profile?.target_audience ?? "";
    if (!bvpAudience) return;
    // Fill when: (a) field is empty, or (b) switching to a different client
    // whose BVP has an audience (overrides the previous client's auto-fill).
    const switchingClient = activeClientId !== lastAutoFilledClientId.current;
    if (targetAudience === "" || switchingClient) {
      setTargetAudience(bvpAudience);
      lastAutoFilledClientId.current = activeClientId ?? null;
    }
  }, [activeClientId, activeClient]);

  const { data: connectionsData } = useQuery({
    queryKey: ["platform-connections", activeClientId],
    queryFn: () => publishingApi.listConnections(activeClientId!),
    enabled: !!activeClientId,
    staleTime: 2 * 60_000,
  });

  const connectedPlatforms = (connectionsData?.items ?? [])
    .filter((c) => c.connected)
    .map((c) => platformLabel(c.platform));

  const charCount = brainDump.length;
  const hasActiveClient = activeClient !== null;
  const hasBvp = activeClient?.brand_voice_profile_status === "ready";
  const isDisabled = charCount < MIN_CHARS || !hasActiveClient || isSubmitting;

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const val = e.target.value;
    if (val.length <= MAX_CHARS) {
      setBrainDump(val);
    }
    // Auto-expand
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Escape") {
      e.preventDefault();
      return;
    }
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (!isDisabled) handleSubmit();
    }
  }

  async function handleSubmit() {
    if (!activeClient) return;
    setIsSubmitting(true);
    setError(null);
    setLimitExceeded(null);
    try {
      const data = await campaignsApi.create({
        client_id: activeClient.id,
        brain_dump: brainDump.trim(),
        target_keyword: targetKeyword.trim() || null,
        target_audience: targetAudience.trim() || null,
      });
      setBrainDump("");
      setTargetKeyword("");
      setTargetAudience("");
      setIsSubmitting(false);
      router.push(`/campaigns/${data.campaign_id}?job_id=${data.job_id}`);
    } catch (err: unknown) {
      if (err instanceof APIError && err.code === "TRIAL_EXPIRED") {
        showUpgradePrompt(err.message);
      } else if (err instanceof APIError && err.code === "CAMPAIGN_LIMIT_EXCEEDED") {
        setLimitExceeded({ message: err.message, nextTier: "" });
      } else {
        const msg =
          err instanceof Error
            ? err.message
            : "Something went wrong. Please try again.";
        setError(msg);
      }
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Link
        href="/campaigns"
        className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors font-mono mb-10"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to campaigns
      </Link>

      <header className="mb-8">
        <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-1">
          New Campaign
        </p>
        <h1 className="font-display text-3xl font-bold text-ink">Brain Dump</h1>
      </header>

      {hasActiveClient ? (
        <p className="text-xs font-mono text-graphite mb-4">
          Writing for:{" "}
          <span className="text-ink font-medium">{activeClient.name}</span>
        </p>
      ) : null}

      {hasActiveClient && connectedPlatforms.length > 0 && (
        <p className="font-mono text-xs text-graphite mb-6">
          Publishing to:{" "}
          <span className="text-ink">{connectedPlatforms.join(" · ")}</span>
        </p>
      )}

      {hasActiveClient && connectionsData !== undefined && connectedPlatforms.length === 0 && (
        <div className="mb-6 border border-ink/10 bg-paper px-4 py-3">
          <p className="text-sm font-mono text-graphite">
            No platforms connected.{" "}
            <Link
              href={`/clients/${activeClient!.id}/connections`}
              className="underline hover:text-ink"
            >
              Connect a platform
            </Link>
            {" "}to publish after approval.
          </p>
        </div>
      )}

      {!hasActiveClient && (
        <div className="mb-6 border border-danger/20 bg-danger/5 px-4 py-3">
          <p className="text-sm font-mono text-danger">
            Select a client first — use the switcher in the sidebar.
          </p>
          <Link
            href="/clients"
            className="text-xs font-mono text-danger underline mt-1 inline-block"
          >
            Go to Clients
          </Link>
        </div>
      )}

      {hasActiveClient && !hasBvp && (
        <div className="mb-6 border border-ink/10 bg-paper px-4 py-3">
          <p className="text-sm font-mono text-graphite">
            This client has no voice profile yet. Content will be generated
            without brand alignment.{" "}
            <Link
              href={`/clients/${activeClient!.id}/voice`}
              className="underline hover:text-ink"
            >
              Set up a voice profile first.
            </Link>
          </p>
        </div>
      )}

      {limitExceeded && (
        <div className="mb-6 border border-danger/20 bg-danger/5 px-4 py-3 space-y-2">
          <p className="text-sm font-mono text-danger">{limitExceeded.message}</p>
          <Link
            href="/account"
            className="text-xs font-mono text-danger underline inline-block"
          >
            Upgrade your plan
          </Link>
        </div>
      )}

      {error && (
        <div className="mb-6 border border-danger/20 bg-danger/5 px-4 py-3">
          <p className="text-sm font-mono text-danger">{error}</p>
        </div>
      )}

      <div className="space-y-2 mb-4">
        <textarea
          ref={textareaRef}
          value={brainDump}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Paste your raw idea here — voice note transcript, rough bullets, half-finished thoughts. No structure needed."
          className={cn(
            "w-full bg-transparent resize-none font-mono text-sm text-ink leading-[1.7]",
            "border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink",
            "py-3 focus:outline-none transition-all min-h-[200px]",
            "placeholder:text-graphite/40"
          )}
          rows={8}
          aria-label="Brain dump"
        />
        <p
          className={cn(
            "text-xs font-mono",
            charCount > 0 && charCount < MIN_CHARS ? "text-danger" : "text-graphite"
          )}
        >
          {charCount} / {MAX_CHARS.toLocaleString()} characters
        </p>
      </div>

      <div className="space-y-1 mb-2">
        <label className="font-mono text-xs text-graphite uppercase tracking-widest">
          Target keyword <span className="normal-case">(optional)</span>
        </label>
        <input
          type="text"
          value={targetKeyword}
          onChange={(e) => setTargetKeyword(e.target.value)}
          maxLength={200}
          placeholder="e.g. how to scale a subscription mobile app"
          className="w-full bg-transparent font-mono text-sm text-ink border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink py-2 focus:outline-none transition-all placeholder:text-graphite/40"
        />
      </div>

      <div className="space-y-1 mb-6">
        <label className="font-mono text-xs text-graphite uppercase tracking-widest">
          Target audience <span className="normal-case">(optional)</span>
        </label>
        <input
          type="text"
          value={targetAudience}
          onChange={(e) => setTargetAudience(e.target.value)}
          maxLength={500}
          placeholder="e.g. indie app developers, solo founders building iOS apps"
          className="w-full bg-transparent font-mono text-sm text-ink border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink py-2 focus:outline-none transition-all placeholder:text-graphite/40"
        />
      </div>

      <Button
        variant="primary"
        disabled={isDisabled}
        onClick={handleSubmit}
        className="w-full sm:w-auto"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            Starting generation...
          </>
        ) : (
          "Generate campaign"
        )}
      </Button>
      {hasActiveClient && !isSubmitting && (
        <p className="text-xs font-mono text-graphite mt-2">
          Tip: Cmd+Enter submits
        </p>
      )}
    </div>
  );
}
