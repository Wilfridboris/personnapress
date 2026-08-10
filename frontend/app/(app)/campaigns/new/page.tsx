"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ChevronDown, ChevronUp, Feather, FileText, Lightbulb, Link as LinkIcon, Loader2 } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { useClientStore } from "@/lib/stores/useClientStore";
import { campaignsApi, publishingApi, APIError } from "@/lib/api";
import { useUIStore } from "@/lib/stores/useUIStore";
import { LengthSelector, type TargetLength } from "@/components/campaigns/LengthSelector";

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
const MAX_TEXTAREA_HEIGHT = 480;

const DRAFT_KEY = (clientId: string) =>
  `personnapress:brain-dump-draft:${clientId}`;

const DRAFT_TTL_MS = 7 * 24 * 60 * 60 * 1000;

interface BrainDumpDraft {
  brainDump: string;
  targetKeyword: string;
  supportingKeywords: string;
  targetAudience: string;
  targetLength: TargetLength;
  savedAt: string;
}

function formatDraftAge(savedAt: string): string {
  const diffMs = Date.now() - new Date(savedAt).getTime();
  if (isNaN(diffMs) || diffMs < 0) return "just now";
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? "" : "s"} ago`;
  if (diffHr < 24) return `${diffHr} hour${diffHr === 1 ? "" : "s"} ago`;
  if (diffDay === 1) return "yesterday";
  return `${diffDay} days ago`;
}

function resizeTextarea(ta: HTMLTextAreaElement, maxH: number) {
  if (ta.scrollHeight >= maxH && parseFloat(ta.style.height || "0") >= maxH) {
    ta.style.overflowY = "auto";
    return;
  }
  const scrollY = window.scrollY;
  ta.style.height = "auto";
  const newH = Math.min(ta.scrollHeight, maxH);
  ta.style.height = `${newH}px`;
  ta.style.overflowY = ta.scrollHeight > maxH ? "auto" : "hidden";
  window.scrollTo({ top: scrollY, behavior: "instant" });
}

export default function NewCampaignPage() {
  const router = useRouter();
  const { clients, activeClientId, isInitialized } = useClientStore();
  const showUpgradePrompt = useUIStore((s) => s.showUpgradePrompt);
  const activeClient = clients.find((c) => c.id === activeClientId) ?? null;

  const [campaignType, setCampaignType] = useState<"blog_full" | "social_only">("blog_full");
  const [targetLength, setTargetLength] = useState<TargetLength>("600-1000");
  const [generateImage, setGenerateImage] = useState(true);
  const [brainDump, setBrainDump] = useState("");
  const [targetKeyword, setTargetKeyword] = useState("");
  const [supportingKeywords, setSupportingKeywords] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [tipsOpen, setTipsOpen] = useState(false);
  const tipsToggleId = useId();
  const tipsPanelId = useId();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limitExceeded, setLimitExceeded] = useState<{ message: string; nextTier: string } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Track which clientId we last auto-filled from, so we re-fill on client
  // switch and on async client-list load (when activeClientId is set before
  // clients arrive in the store).
  const lastAutoFilledClientId = useRef<string | null>(null);
  const [draftBanner, setDraftBanner] = useState<BrainDumpDraft | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const userHasTypedRef = useRef(false);

  useEffect(() => {
    setGenerateImage(true);
  }, [campaignType]);

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

  // Debounced autosave to localStorage (AC 1)
  useEffect(() => {
    if (!activeClientId || !userHasTypedRef.current) return;
    const anyContent = brainDump || targetKeyword || supportingKeywords || targetAudience;
    if (!anyContent) return;

    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      const draft: BrainDumpDraft = {
        brainDump,
        targetKeyword,
        supportingKeywords,
        targetAudience,
        targetLength,
        savedAt: new Date().toISOString(),
      };
      try {
        localStorage.setItem(DRAFT_KEY(activeClientId), JSON.stringify(draft));
      } catch {
        // localStorage quota exceeded -- silently ignore
      }
    }, 500);

    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [brainDump, targetKeyword, supportingKeywords, targetAudience, targetLength, activeClientId]);

  // Load draft from localStorage on mount / client change (AC 2, AC 3)
  useEffect(() => {
    userHasTypedRef.current = false;
    if (!activeClientId) return;
    setDraftBanner(null);
    try {
      const raw = localStorage.getItem(DRAFT_KEY(activeClientId));
      if (!raw) return;
      const draft: BrainDumpDraft = JSON.parse(raw);
      if (!draft || typeof draft.savedAt !== "string" || !draft.savedAt) {
        localStorage.removeItem(DRAFT_KEY(activeClientId));
        return;
      }
      if (Date.now() - new Date(draft.savedAt).getTime() > DRAFT_TTL_MS) {
        localStorage.removeItem(DRAFT_KEY(activeClientId));
        return;
      }
      setDraftBanner({
        brainDump: typeof draft.brainDump === "string" ? draft.brainDump : "",
        targetKeyword: typeof draft.targetKeyword === "string" ? draft.targetKeyword : "",
        supportingKeywords: typeof draft.supportingKeywords === "string" ? draft.supportingKeywords : "",
        targetAudience: typeof draft.targetAudience === "string" ? draft.targetAudience : "",
        savedAt: draft.savedAt,
      });
    } catch {
      // Malformed JSON or localStorage unavailable -- silently ignore
    }
  }, [activeClientId]);

  // Auto-dismiss banner when user starts typing (AC 3, criterion 9)
  useEffect(() => {
    if (!draftBanner || !userHasTypedRef.current) return;
    const anyContent = brainDump || targetKeyword || supportingKeywords || targetAudience;
    if (anyContent) setDraftBanner(null);
  }, [brainDump, targetKeyword, supportingKeywords, targetAudience]);

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
  const linkCount = useMemo(
    () => (brainDump.match(/https?:\/\/[^\s]+/g) ?? []).length,
    [brainDump]
  );
  const hasProsePassage = useMemo(() => {
    if (!brainDump || brainDump.length < 30) return false;
    const sentences = brainDump.split(/[.!?]+/).map((s) => s.trim()).filter((s) => s.length > 10);
    const firstPersonSentences = sentences.filter((s) => /\bI\s+[a-z]/i.test(s));
    return firstPersonSentences.length >= 2;
  }, [brainDump]);
  const hasActiveClient = activeClient !== null;
  const hasBvp = activeClient?.brand_voice_profile_status === "ready";
  const isDisabled = charCount < MIN_CHARS || !hasActiveClient || isSubmitting;

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    resizeTextarea(ta, MAX_TEXTAREA_HEIGHT);
  }, [brainDump]);

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    userHasTypedRef.current = true;
    setBrainDump(e.target.value.slice(0, MAX_CHARS));
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

  function handleRestoreDraft() {
    if (!draftBanner) return;
    setBrainDump(draftBanner.brainDump);
    setTargetKeyword(draftBanner.targetKeyword);
    setSupportingKeywords(draftBanner.supportingKeywords);
    setTargetAudience(draftBanner.targetAudience);
    setTargetLength(
      ["300-500", "600-1000", "1500-2500"].includes(draftBanner.targetLength)
        ? (draftBanner.targetLength as TargetLength)
        : "600-1000"
    );
    setDraftBanner(null);
  }

  function handleDiscardDraft() {
    setDraftBanner(null);
    if (!activeClientId) return;
    localStorage.removeItem(DRAFT_KEY(activeClientId));
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
        target_keyword: campaignType === "blog_full" ? (targetKeyword.trim() || null) : null,
        secondary_keywords: campaignType === "blog_full" ? (supportingKeywords.trim() || null) : null,
        target_audience: targetAudience.trim() || null,
        campaign_type: campaignType,
        skip_image: campaignType === "social_only" ? true : !generateImage,
        target_word_count: campaignType === "blog_full" ? targetLength : null,
      });
      setBrainDump("");
      setTargetKeyword("");
      setSupportingKeywords("");
      setTargetAudience("");
      setIsSubmitting(false);
      if (activeClientId) localStorage.removeItem(DRAFT_KEY(activeClientId));
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

      {draftBanner && (
        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-3 border border-ink/10 bg-[#F9F9F6] rounded-none px-4 py-3 mb-6 animate-[slideDown_150ms_ease-out]"
        >
          <FileText size={12} aria-hidden="true" className="shrink-0 text-graphite" />
          <p className="text-xs font-mono text-graphite flex-1">
            Unsaved draft from {formatDraftAge(draftBanner.savedAt)}.
          </p>
          <button
            type="button"
            onClick={handleRestoreDraft}
            className="text-xs font-mono text-ink underline underline-offset-2 min-h-[44px] px-2 hover:text-graphite transition-colors duration-100"
          >
            Restore
          </button>
          <button
            type="button"
            onClick={handleDiscardDraft}
            className="text-xs font-mono text-graphite/60 underline underline-offset-2 min-h-[44px] px-2 hover:text-graphite transition-colors duration-100"
          >
            Discard
          </button>
        </div>
      )}

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

      {isInitialized && !hasActiveClient && (
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

      <fieldset className="mb-6">
        <legend className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
          Content type
        </legend>
        <div className="flex flex-col border border-ink/10">
          <label
            className={cn(
              "flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors duration-100",
              "hover:bg-ink/[0.02]",
              campaignType === "blog_full" ? "bg-ink/[0.03]" : ""
            )}
          >
            <input
              type="radio"
              name="campaign_type"
              value="blog_full"
              checked={campaignType === "blog_full"}
              onChange={() => setCampaignType("blog_full")}
              className="mt-0.5 accent-ink"
              aria-describedby="ct-blog-desc"
            />
            <span className="flex flex-col gap-0.5">
              <span className="font-mono text-sm text-ink">Blog + Social</span>
              <span id="ct-blog-desc" className="font-mono text-xs text-graphite">
                Blog post, X and LinkedIn posts, featured image
              </span>
            </span>
          </label>
          <div className="border-t border-ink/10" />
          <label
            className={cn(
              "flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors duration-100",
              "hover:bg-ink/[0.02]",
              campaignType === "social_only" ? "bg-ink/[0.03]" : ""
            )}
          >
            <input
              type="radio"
              name="campaign_type"
              value="social_only"
              checked={campaignType === "social_only"}
              onChange={() => setCampaignType("social_only")}
              className="mt-0.5 accent-ink"
              aria-describedby="ct-social-desc"
            />
            <span className="flex flex-col gap-0.5">
              <span className="font-mono text-sm text-ink">Social post only</span>
              <span id="ct-social-desc" className="font-mono text-xs text-graphite">
                X and LinkedIn posts only, no blog or featured image
              </span>
            </span>
          </label>
        </div>
        {campaignType === "social_only" && (
          <p
            role="status"
            aria-live="polite"
            className="mt-2 font-mono text-xs text-graphite border-l-2 border-ink/30 pl-3"
          >
            Shorter generation time. You can publish directly to X and LinkedIn after approval.
          </p>
        )}
      </fieldset>

      <div className="space-y-2 mb-4">
        <textarea
          ref={textareaRef}
          value={brainDump}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`e.g. "I ran a 90-day test comparing 3 LinkedIn posting strategies, daily tips vs. 3x storytelling vs. 2x case studies. Case studies drove 4x more DMs. Most people post daily tips because it feels safe. Here's what I found and why I switched..."`}
          className={cn(
            "w-full bg-transparent resize-none font-mono text-sm text-ink leading-[1.7]",
            "border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink",
            "py-3 focus:outline-none transition-[border-width] duration-100 min-h-[200px]",
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
        <div aria-live="polite" aria-atomic="true">
          {charCount > 0 && charCount < 150 && (
            <p className="flex items-center gap-1 text-xs font-mono text-[#555555] mt-1">
              <Lightbulb size={12} aria-hidden="true" />
              Tip: include a specific number, personal outcome, or named tool for best results.
            </p>
          )}
          {charCount >= 150 && !hasProsePassage && (
            <p className="flex items-center gap-1 text-xs font-mono text-[#555555] mt-1">
              <Feather size={12} aria-hidden="true" />
              Tip: write 2-3 sentences in your own voice, they will be kept as written.
            </p>
          )}
        </div>
        <div aria-live="polite" aria-atomic="true">
          {linkCount > 0 && (
            <p className="flex items-center gap-1 text-xs font-mono text-sky-600 mt-1">
              <LinkIcon size={12} aria-hidden="true" />
              {linkCount === 1 ? "1 link detected" : `${linkCount} links detected`} -- will be cited in your article
            </p>
          )}
        </div>
        <div className="mt-2">
          <button
            id={tipsToggleId}
            type="button"
            onClick={() => setTipsOpen(!tipsOpen)}
            aria-expanded={tipsOpen}
            aria-controls={tipsPanelId}
            className="flex items-center gap-1 text-xs text-[#555555] min-h-[44px] px-2 py-0 hover:text-[#111111] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
          >
            {tipsOpen
              ? <ChevronUp size={12} aria-hidden="true" />
              : <ChevronDown size={12} aria-hidden="true" />}
            {tipsOpen ? "Hide tips" : "Tips for better results"}
          </button>
          <div
            id={tipsPanelId}
            role="region"
            aria-labelledby={tipsToggleId}
            className={`grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none ${
              tipsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            }`}
          >
            <div className="overflow-hidden">
              <ul role="list" className="mt-2 border border-[#E5E5E5] bg-[#F9F9F6] p-3 rounded-none list-none space-y-2 text-sm text-[#555555]">
                <li className="text-[#111111]">
                  Write the sentences you care most about in full, they will appear in your article nearly word for word
                </li>
                <li>Start with a specific number, date, or outcome:{" "}
                  <code className="font-mono text-xs bg-[#F0F0ED] px-1">
                    I increased conversion 28% in 6 weeks
                  </code>
                </li>
                <li>Mention tools or platforms by name:{" "}
                  <code className="font-mono text-xs bg-[#F0F0ED] px-1">
                    We switched from Mailchimp to ConvertKit
                  </code>
                </li>
                <li>Use first-person:{" "}
                  <code className="font-mono text-xs bg-[#F0F0ED] px-1">I found</code>,{" "}
                  <code className="font-mono text-xs bg-[#F0F0ED] px-1">I tested</code>,{" "}
                  <code className="font-mono text-xs bg-[#F0F0ED] px-1">my client saw</code>
                </li>
                <li>Describe the before/after or the problem you solved</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className={`grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none ${
        campaignType === "blog_full" ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
      }`}>
        <div className="overflow-hidden" aria-hidden={campaignType === "social_only" || undefined}>
          {/* NEW -- length selector first */}
          <LengthSelector value={targetLength} onChange={setTargetLength} />

          <div className="space-y-1 mb-2">
            <label className="font-mono text-xs text-graphite uppercase tracking-widest">
              Focus keyword <span className="normal-case">(optional)</span>
            </label>
            <input
              type="text"
              value={targetKeyword}
              onChange={(e) => { userHasTypedRef.current = true; setTargetKeyword(e.target.value); }}
              maxLength={200}
              placeholder="e.g. how to scale a subscription mobile app"
              className="w-full bg-transparent font-mono text-sm text-ink border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink py-2 focus:outline-none transition-all placeholder:text-graphite/40"
              tabIndex={campaignType === "social_only" ? -1 : undefined}
            />
          </div>

          <div className="space-y-1 mb-2">
            <label className="font-mono text-xs text-graphite/70 uppercase tracking-widest">
              Supporting keywords <span className="normal-case">(optional)</span>
            </label>
            <input
              type="text"
              value={supportingKeywords}
              onChange={(e) => { userHasTypedRef.current = true; setSupportingKeywords(e.target.value); }}
              maxLength={500}
              placeholder="e.g. SaaS growth, bootstrapped startup, MRR expansion"
              className="w-full bg-transparent font-mono text-sm text-ink border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink py-2 focus:outline-none transition-all placeholder:text-graphite/40"
              tabIndex={campaignType === "social_only" ? -1 : undefined}
            />
            <p className="font-mono text-xs text-graphite/50 normal-case tracking-normal">
              Comma-separated. Each mentioned once naturally within the first 500 words.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-1 mb-6">
        <label className="font-mono text-xs text-graphite uppercase tracking-widest">
          Target audience <span className="normal-case">(optional)</span>
        </label>
        <input
          type="text"
          value={targetAudience}
          onChange={(e) => { userHasTypedRef.current = true; setTargetAudience(e.target.value); }}
          maxLength={500}
          placeholder="e.g. indie app developers, solo founders building iOS apps"
          className="w-full bg-transparent font-mono text-sm text-ink border-0 border-b border-ink/20 focus:border-b-2 focus:border-ink py-2 focus:outline-none transition-all placeholder:text-graphite/40"
        />
      </div>

      {campaignType === "blog_full" && (
        <div className="mb-6">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={generateImage}
              onChange={(e) => setGenerateImage(e.target.checked)}
              className="mt-0.5 accent-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
              aria-describedby={generateImage ? undefined : "image-skip-hint"}
            />
            <span className="flex flex-col gap-0.5">
              <span className="font-mono text-xs text-graphite uppercase tracking-widest">
                AI featured image
              </span>
              {!generateImage && (
                <span
                  id="image-skip-hint"
                  role="status"
                  aria-live="polite"
                  className="font-mono text-xs text-graphite"
                >
                  Upload your own image from the approval page.
                </span>
              )}
            </span>
          </label>
        </div>
      )}

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
