"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, ChevronUp } from "lucide-react";
import Link from "next/link";
import { useClientStore } from "@/lib/stores/useClientStore";
import { clientsApi, subscriptionsApi, roadmapsApi } from "@/lib/api";
import { usePlatformConnections } from "@/hooks/usePlatformConnections";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const MAX_CHARS = 10_000;
const MIN_CHARS = 20;

interface PlanConfig {
  linkedinOn: boolean;
  linkedinCount: number;
  twitterOn: boolean;
  twitterCount: number;
  blogOn: boolean;
  generateImages: boolean;
}

const DEFAULT_CONFIG: PlanConfig = {
  linkedinOn: false,
  linkedinCount: 3,
  twitterOn: false,
  twitterCount: 5,
  blogOn: true,
  generateImages: true,
};

function Toggle({
  id,
  label,
  checked,
  onChange,
  disabled = false,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex items-center gap-3 select-none",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
      )}
    >
      <button
        type="button"
        id={id}
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => { if (!disabled) onChange(!checked); }}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 items-center border border-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]",
          "disabled:cursor-not-allowed",
          checked ? "bg-[#111111]" : "bg-white"
        )}
      >
        <span
          className={cn(
            "inline-block h-3 w-3 transform transition-transform border border-[#111111]",
            checked ? "translate-x-[18px] bg-white" : "translate-x-1 bg-[#111111]"
          )}
        />
      </button>
      <span className="font-body text-sm text-ink">{label}</span>
    </label>
  );
}

function Spinner({
  value,
  onChange,
  min,
  max,
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        aria-label="Decrease"
        disabled={value <= min}
        onClick={() => onChange(Math.max(min, value - 1))}
        className="w-7 h-7 flex items-center justify-center border border-[#111111] text-ink disabled:opacity-40 hover:bg-[#FFF1B8] transition-colors"
      >
        <span className="font-mono text-sm leading-none">-</span>
      </button>
      <span className="font-mono text-sm text-ink w-4 text-center">{value}</span>
      <button
        type="button"
        aria-label="Increase"
        disabled={value >= max}
        onClick={() => onChange(Math.min(max, value + 1))}
        className="w-7 h-7 flex items-center justify-center border border-[#111111] text-ink disabled:opacity-40 hover:bg-[#FFF1B8] transition-colors"
      >
        <span className="font-mono text-sm leading-none">+</span>
      </button>
    </div>
  );
}

export function PlanMyWeekClient() {
  const router = useRouter();
  const { activeClientId } = useClientStore();

  const [panelOpen, setPanelOpen] = useState(true);
  const [settingsSaved, setSettingsSaved] = useState(false);
  const [config, setConfig] = useState<PlanConfig>(DEFAULT_CONFIG);
  const configPopulated = useRef(false);

  const [brainDump, setBrainDump] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: subscription } = useQuery({
    queryKey: ["subscription-me"],
    queryFn: () => subscriptionsApi.getMe(),
    staleTime: 60_000,
  });

  const { data: clientData } = useQuery({
    queryKey: ["client", activeClientId],
    queryFn: () => clientsApi.get(activeClientId!),
    enabled: !!activeClientId,
    staleTime: 5 * 60_000,
  });

  const { data: connectionsData } = usePlatformConnections(activeClientId);
  const connectedPlatforms = new Set(
    (connectionsData?.items ?? [])
      .filter((c) => c.connected)
      .map((c) => c.platform)
  );
  const hasLinkedIn = connectionsData ? connectedPlatforms.has("linkedin") : true;
  const hasTwitter = connectionsData ? connectedPlatforms.has("x") : true;

  useEffect(() => {
    if (!connectionsData) return;
    const connected = new Set(
      connectionsData.items.filter((c) => c.connected).map((c) => c.platform)
    );
    setConfig((prev) => ({
      ...prev,
      linkedinOn: prev.linkedinOn && connected.has("linkedin"),
      twitterOn: prev.twitterOn && connected.has("x"),
    }));
  }, [connectionsData]);

  useEffect(() => {
    configPopulated.current = false;
  }, [activeClientId]);

  useEffect(() => {
    if (configPopulated.current || !clientData?.roadmap_config) return;
    const cfg = clientData.roadmap_config;
    configPopulated.current = true;
    setConfig({
      linkedinOn: (cfg.linkedin_count ?? 0) > 0,
      linkedinCount: (cfg.linkedin_count ?? 0) > 0 ? cfg.linkedin_count : 3,
      twitterOn: (cfg.twitter_count ?? 0) > 0,
      twitterCount: (cfg.twitter_count ?? 0) > 0 ? cfg.twitter_count : 5,
      blogOn: cfg.blog_enabled ?? true,
      generateImages: cfg.images_enabled ?? true,
    });
  }, [clientData]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, [brainDump]);

  const imageQuota = subscription
    ? subscription.plan_limits.image_gens - subscription.image_gen_used
    : null;

  const totalPosts =
    (config.linkedinOn ? config.linkedinCount : 0) +
    (config.twitterOn ? config.twitterCount : 0) +
    (config.blogOn ? 1 : 0);

  const imageQuotaLocked = imageQuota !== null && imageQuota <= 0;
  const roadmapsUsed = subscription?.roadmaps_used ?? 0;
  const roadmapsLimit = subscription?.plan_limits.roadmaps ?? Infinity;
  const roadmapLimitHit = roadmapsUsed >= roadmapsLimit;

  const charCount = brainDump.length;
  const isDisabled =
    charCount < MIN_CHARS ||
    !activeClientId ||
    isSubmitting ||
    roadmapLimitHit ||
    totalPosts === 0;

  function updateConfig(patch: Partial<PlanConfig>) {
    setConfig((prev) => ({ ...prev, ...patch }));
  }

  async function handleSubmit() {
    if (!activeClientId || isDisabled) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const { roadmap_id } = await roadmapsApi.create({
        brain_dump: brainDump,
        client_id: activeClientId,
        linkedin_count: config.linkedinOn ? config.linkedinCount : 0,
        twitter_count: config.twitterOn ? config.twitterCount : 0,
        blog_enabled: config.blogOn,
        generate_images: config.generateImages && !imageQuotaLocked,
      });
      router.push(`/roadmap/${roadmap_id}/review`);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Something went wrong. Please try again."
      );
      setIsSubmitting(false);
    }
  }

  function handlePanelSave() {
    setSettingsSaved(true);
    setPanelOpen(false);
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Link
        href="/roadmap"
        className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors font-mono mb-10"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to Roadmap
      </Link>
      <header className="mb-8">
        <p className="font-body text-xs text-graphite uppercase tracking-[0.08em] mb-1">
          Week Planning
        </p>
        <h1 className="font-display text-3xl font-bold text-ink">
          Plan My Week with Content
        </h1>
      </header>

      {roadmapLimitHit && (
        <div className="mb-6 border border-danger px-4 py-3">
          <p className="font-body text-sm text-danger">
            You have reached your roadmap limit for this billing cycle.{" "}
            <Link href="/pricing" className="underline">
              Upgrade your plan
            </Link>
          </p>
        </div>
      )}

      {/* Settings panel */}
      <div className="mb-6 bg-white border border-[#E5E5E5]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5E5E5]">
          <p className="font-body text-xs text-graphite uppercase tracking-[0.08em]">
            This week&apos;s plan
          </p>
          <div className="flex items-center gap-3">
            {settingsSaved && !panelOpen && (
              <button
                type="button"
                onClick={() => setPanelOpen(true)}
                className="font-body text-xs text-graphite underline hover:text-ink transition-colors"
              >
                Change plan
              </button>
            )}
            <button
              type="button"
              aria-label={panelOpen ? "Collapse settings" : "Expand settings"}
              onClick={() => setPanelOpen((v) => !v)}
              className="text-graphite hover:text-ink transition-colors"
            >
              {panelOpen ? (
                <ChevronUp className="w-4 h-4" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {panelOpen && (
          <div className="px-4 py-4 space-y-4">
            {/* LinkedIn */}
            <div className="space-y-1">
              <div className="flex items-center gap-4">
                <Toggle
                  id="linkedin-toggle"
                  label="LinkedIn"
                  checked={config.linkedinOn}
                  onChange={(v) => updateConfig({ linkedinOn: v })}
                  disabled={!hasLinkedIn}
                />
                {config.linkedinOn && hasLinkedIn && (
                  <Spinner
                    value={config.linkedinCount}
                    onChange={(v) => updateConfig({ linkedinCount: v })}
                    min={1}
                    max={7}
                  />
                )}
              </div>
              {!hasLinkedIn && activeClientId && connectionsData && (
                <p className="font-body text-xs text-graphite">
                  Not connected.{" "}
                  <Link href={`/clients/${activeClientId}/connections`} className="underline hover:text-ink">
                    Connect LinkedIn
                  </Link>
                </p>
              )}
            </div>

            {/* X/Twitter */}
            <div className="space-y-1">
              <div className="flex items-center gap-4">
                <Toggle
                  id="twitter-toggle"
                  label="X / Twitter"
                  checked={config.twitterOn}
                  onChange={(v) => updateConfig({ twitterOn: v })}
                  disabled={!hasTwitter}
                />
                {config.twitterOn && hasTwitter && (
                  <Spinner
                    value={config.twitterCount}
                    onChange={(v) => updateConfig({ twitterCount: v })}
                    min={1}
                    max={14}
                  />
                )}
              </div>
              {!hasTwitter && activeClientId && connectionsData && (
                <p className="font-body text-xs text-graphite">
                  Not connected.{" "}
                  <Link href={`/clients/${activeClientId}/connections`} className="underline hover:text-ink">
                    Connect X
                  </Link>
                </p>
              )}
            </div>

            {/* Blog */}
            <Toggle
              id="blog-toggle"
              label="Blog post"
              checked={config.blogOn}
              onChange={(v) => updateConfig({ blogOn: v })}
            />

            {/* Image generation */}
            <div className="pt-1 border-t border-[#E5E5E5]">
              <div className="flex items-center gap-4 mt-3">
                <Toggle
                  id="images-toggle"
                  label="Generate images"
                  checked={imageQuotaLocked ? false : config.generateImages}
                  onChange={(v) => updateConfig({ generateImages: v })}
                  disabled={imageQuotaLocked}
                />
                {imageQuotaLocked && (
                  <span className="font-body text-xs text-graphite">(quota reached)</span>
                )}
              </div>
              {!imageQuotaLocked && config.generateImages && imageQuota !== null && (
                <>
                  <p className="font-body text-xs text-graphite mt-2">
                    You have {imageQuota} image generation{imageQuota === 1 ? "" : "s"} remaining this month.
                  </p>
                  {imageQuota < totalPosts && (
                    <div className="mt-2 bg-[#FFF1B8] border border-[#111111] px-3 py-2">
                      <p className="font-body text-xs text-ink">
                        The first {imageQuota} post{imageQuota === 1 ? "" : "s"} will include a generated image.
                      </p>
                    </div>
                  )}
                </>
              )}
              {imageQuotaLocked && (
                <p className="font-body text-xs text-graphite mt-2">
                  No image generations remaining this cycle.{" "}
                  <Link href="/pricing" className="underline hover:text-ink">
                    Upgrade
                  </Link>
                </p>
              )}
            </div>

            <div className="pt-2">
              <Button
                type="button"
                variant="secondary"
                onClick={handlePanelSave}
                className="text-xs"
              >
                Save settings
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Brain dump */}
      <div className="mb-6">
        <label
          htmlFor="brain-dump"
          className="block font-body text-xs text-graphite uppercase tracking-[0.08em] mb-2"
        >
          What&apos;s on your mind this week?
        </label>
        <textarea
          id="brain-dump"
          ref={textareaRef}
          value={brainDump}
          onChange={(e) => setBrainDump(e.target.value.slice(0, MAX_CHARS))}
          placeholder="Paste your raw ideas here -- voice note transcript, rough bullets, half-finished thoughts. No structure needed."
          className={cn(
            "w-full bg-transparent resize-none font-mono text-sm text-ink leading-[1.7]",
            "border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink",
            "py-3 focus:outline-none transition-all",
            "placeholder:text-graphite/40"
          )}
          style={{ minHeight: "160px" }}
          rows={6}
          aria-label="What's on your mind this week?"
        />
        <p className="font-body text-xs text-graphite mt-1">
          {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
        </p>
      </div>

      {error && (
        <div className="mb-4 border border-danger/20 bg-danger/5 px-4 py-3">
          <p className="font-body text-sm text-danger">{error}</p>
        </div>
      )}

      <Button
        type="button"
        variant="primary"
        disabled={isDisabled}
        aria-disabled={isDisabled}
        onClick={handleSubmit}
        className="w-full sm:w-auto"
      >
        {isSubmitting ? "Planning your week..." : "Plan My Week"}
      </Button>
    </div>
  );
}
