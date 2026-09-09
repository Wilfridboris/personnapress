"use client";

import { useState, useEffect, useId, useMemo, useRef, useCallback } from "react";
import { ChevronDown, ChevronUp, Lightbulb, Link as LinkIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { authApi, clientsApi, campaignsApi } from "@/lib/api";
import { useClientStore } from "@/lib/stores/useClientStore";
import { useJobStatus } from "@/hooks/useJobStatus";
import { Button } from "@/components/ui/Button";
import { Input, BrainDumpInput } from "@/components/ui/Input";
import { TagChip } from "@/components/ui/TagChip";
import { VoiceQuestionnaire } from "@/components/clients/VoiceQuestionnaire";
import { VoiceBrainDump } from "@/components/campaigns/VoiceBrainDump";
import { ProgressIndicator } from "./ProgressIndicator";
import { SkipLink } from "./SkipLink";
import { OnboardingPlatformStep } from "./OnboardingPlatformStep";
import type { ExpandedBrandVoiceProfile, BrandVoiceCadence } from "@/lib/types";

type OnboardingStep = 1 | 2 | 3 | 4;
type Step2View = "in-progress" | "questionnaire" | "review" | "failed";

const MAX_BRAIN_DUMP = 10_000;
const MIN_BRAIN_DUMP = 20;
const DRAFT_STORAGE_KEY = "onboarding_brain_dump_draft";
const DRAFT_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

// ── Voice Proof element (AC: 2) ────────────────────────────────────────────────
interface VoiceProofProps {
  clientId: string;
}

function VoiceProof({ clientId }: VoiceProofProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["voice-preview", clientId],
    queryFn: () => clientsApi.voicePreview(clientId),
    retry: false,
    staleTime: Infinity,
  });

  // AC: 2 — generation failure hides the element without blocking the step
  if (isError) return null;

  return (
    <div
      className="mt-6 border border-[#111111] p-4"
      style={{ boxShadow: "4px 4px 0px 0px var(--color-ink, #111111)" }}
    >
      <p className="font-sans text-[10px] uppercase tracking-[0.1em] text-[#555555] mb-3">
        This is how PersonnaPress will sound as you
      </p>
      {isLoading ? (
        <div className="space-y-2" aria-busy="true" aria-label="Loading voice preview">
          <div className="h-4 bg-[#E5E5E0] rounded-none" style={{ width: "90%", animation: "shimmer 1.5s ease-in-out infinite" }} />
          <div className="h-4 bg-[#E5E5E0] rounded-none" style={{ width: "75%", animation: "shimmer 1.5s ease-in-out infinite" }} />
          <style>{`
            @keyframes shimmer {
              0% { opacity: 1; }
              50% { opacity: 0.5; }
              100% { opacity: 1; }
            }
            @keyframes voiceProofIn {
              from { opacity: 0; transform: translateY(6px); }
              to   { opacity: 1; transform: translateY(0); }
            }
          `}</style>
        </div>
      ) : data?.preview ? (
        <p
          className="text-[0.9375rem] text-[#111111] leading-[1.65] text-pretty motion-reduce:animate-none"
          style={{ animation: "voiceProofIn 0.4s ease-out both" }}
        >
          <style>{`
            @keyframes voiceProofIn {
              from { opacity: 0; transform: translateY(6px); }
              to   { opacity: 1; transform: translateY(0); }
            }
          `}</style>
          {data.preview}
        </p>
      ) : null}
    </div>
  );
}

// ── Inline BVP Review for Step 2 ──────────────────────────────────────────────
interface InlineProfileReviewProps {
  bvp: ExpandedBrandVoiceProfile;
  clientId: string;
  onConfirmed: () => void;
}

function InlineProfileReview({ bvp, clientId, onConfirmed }: InlineProfileReviewProps) {
  const [tone, setTone] = useState<string[]>(bvp.tone ?? []);
  const [cadence, setCadence] = useState<BrandVoiceCadence>(
    bvp.cadence ?? { avg_sentence_length: 0, variation_pattern: "", paragraph_structure: "" }
  );
  const [bannedJargon, setBannedJargon] = useState<string[]>(bvp.banned_jargon ?? []);
  const [newTone, setNewTone] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setSaving(true);
    setError(null);
    try {
      await clientsApi.patch(clientId, {
        brand_voice_profile: { tone, cadence, banned_jargon: bannedJargon },
      });
      onConfirmed();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  const addTone = () => {
    const t = newTone.trim();
    if (t && !tone.includes(t)) setTone((p) => [...p, t]);
    setNewTone("");
  };

  return (
    <div>
      <p className="font-sans text-xs uppercase tracking-[0.06em] text-[#111111] mb-3">Tone</p>
      <div className="flex flex-wrap mb-3">
        {tone.map((tag) => (
          <TagChip
            key={tag}
            label={tag}
            onRemove={() => setTone((p) => p.filter((t) => t !== tag))}
          />
        ))}
      </div>
      <div className="flex items-center gap-2 mb-6">
        <Input
          value={newTone}
          onChange={(e) => setNewTone(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addTone())}
          placeholder="Add tone descriptor..."
          className="max-w-[200px]"
          aria-label="New tone descriptor"
        />
        <Button variant="secondary" type="button" onClick={addTone} className="text-sm px-3 py-1.5">
          Add
        </Button>
      </div>

      <p className="font-sans text-xs uppercase tracking-[0.06em] text-[#111111] mb-2">Cadence</p>
      <p className="text-sm text-[#111111] mb-6">
        Avg. sentence length: {cadence.avg_sentence_length} words
        {cadence.variation_pattern ? `. ${cadence.variation_pattern}` : ""}
      </p>

      {bannedJargon.length > 0 && (
        <>
          <p className="font-sans text-xs uppercase tracking-[0.06em] text-[#111111] mb-2">Banned jargon</p>
          <div className="flex flex-wrap mb-6">
            {bannedJargon.map((tag) => (
              <TagChip
                key={tag}
                label={tag}
                onRemove={() => setBannedJargon((p) => p.filter((t) => t !== tag))}
              />
            ))}
          </div>
        </>
      )}

      {/* Voice proof element (AC: 2) */}
      <VoiceProof clientId={clientId} />

      {error && (
        <p role="alert" className="text-sm text-[#8B0000] mb-4 mt-4">
          {error}
        </p>
      )}

      <Button onClick={handleConfirm} disabled={saving} aria-busy={saving} type="button" className="mt-4">
        {saving ? "Saving..." : "Confirm profile"}
      </Button>
    </div>
  );
}

// ── Step 2 content ─────────────────────────────────────────────────────────────
interface Step2ContentProps {
  view: Step2View;
  jobId: string | null;
  clientId: string;
  websiteUrl: string;
  errorDetails: string | null;
  onStep2Complete: () => void;
  onJobStarted: (jobId: string) => void;
}

function Step2Content({ view, jobId, clientId, websiteUrl, errorDetails, onStep2Complete, onJobStarted }: Step2ContentProps) {
  const { job } = useJobStatus(jobId);
  const [currentView, setCurrentView] = useState<Step2View>(view);
  const [bvp, setBvp] = useState<ExpandedBrandVoiceProfile | null>(null);
  const [statusText, setStatusText] = useState(`Scraping ${websiteUrl}...`);

  useEffect(() => {
    setCurrentView(view);
  }, [view]);

  useEffect(() => {
    if (!job) return;
    if (job.status === "completed" || job.status === "complete") {
      clientsApi.get(clientId).then((client) => {
        if (client.brand_voice_profile) {
          setBvp(client.brand_voice_profile);
          setCurrentView("review");
        } else {
          setCurrentView("questionnaire");
        }
      }).catch(() => setCurrentView("questionnaire"));
    } else if (job.status === "in_progress") {
      setStatusText("Extracting voice profile...");
    } else if (job.status === "failed") {
      if (job.error_details === "no_content") {
        setCurrentView("questionnaire");
      } else {
        setCurrentView("failed");
      }
    }
  }, [job, clientId]);

  // AC: 3 — Scrape failure explanation copy (quiet single line above questionnaire)
  const scrapeExplanation = useMemo(() => {
    if (currentView !== "questionnaire") return null;
    const reason = errorDetails ?? job?.error_details ?? "";
    if (!reason) return null;
    if (reason === "no_content") {
      return "We could not read enough text from your site, so we will ask a few quick questions instead.";
    }
    return "We could not finish analyzing your site, so we will ask a few quick questions instead.";
  }, [currentView, errorDetails, job?.error_details]);

  if (currentView === "in-progress") {
    return (
      <p className="font-mono text-sm text-[#555555] animate-pulse">
        {statusText}
      </p>
    );
  }

  if (currentView === "questionnaire") {
    return (
      <div>
        {scrapeExplanation && (
          <p className="text-sm text-[#555555] mb-4 text-pretty">
            {scrapeExplanation}
          </p>
        )}
        <VoiceQuestionnaire
          clientId={clientId}
          onJobStarted={(jId) => {
            onJobStarted(jId);
            setCurrentView("in-progress");
          }}
        />
      </div>
    );
  }

  if (currentView === "failed") {
    return (
      <div>
        <p className="text-sm text-[#555555] mb-4 text-pretty">
          We could not finish analyzing your site, so we will ask a few quick questions instead.
        </p>
        <Button type="button" onClick={() => setCurrentView("questionnaire")}>
          Complete questionnaire
        </Button>
      </div>
    );
  }

  if (currentView === "review" && bvp) {
    return (
      <InlineProfileReview
        bvp={bvp}
        clientId={clientId}
        onConfirmed={onStep2Complete}
      />
    );
  }

  return null;
}

// ── Card wrapper ───────────────────────────────────────────────────────────────
// Defined outside OnboardingFlow so React does not treat it as a new component
// type on every parent re-render (which would remount children and lose focus).
function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white border border-[#E5E5E5] p-8 w-full max-w-lg">
      {children}
    </div>
  );
}

// ── Draft persistence helpers (AC: 5, story 3-18 pattern) ─────────────────────
function readDraft(): { text: string; savedAt: number } | null {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { text: string; savedAt: number };
    if (typeof parsed.text !== "string" || typeof parsed.savedAt !== "number") return null;
    if (isNaN(parsed.savedAt)) return null;
    if (Date.now() - parsed.savedAt > DRAFT_MAX_AGE_MS) {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function saveDraft(text: string) {
  try {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify({ text, savedAt: Date.now() }));
  } catch {
    // storage unavailable -- fail silently
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    // noop
  }
}

// ── Main OnboardingFlow ────────────────────────────────────────────────────────
interface OnboardingFlowProps {
  /** Saved step from the session JWT, forwarded by the server component via x-onboarding-step header. */
  initialStep?: number | null;
}

export function OnboardingFlow({ initialStep }: OnboardingFlowProps = {}) {
  const router = useRouter();
  // Clamp initialStep to valid range 1-4; fall back to 1 if absent or out of range.
  const clampedInitial = initialStep != null && initialStep >= 1 && initialStep <= 4
    ? (initialStep as OnboardingStep)
    : 1;
  const [step, setStep] = useState<OnboardingStep>(clampedInitial);

  // Step 1 state
  const [clientName, setClientName] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [step1Loading, setStep1Loading] = useState(false);
  const [step1Error, setStep1Error] = useState<string | null>(null);

  // Step 2 state
  const [createdClientId, setCreatedClientId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [step2View, setStep2View] = useState<Step2View>("questionnaire");
  const [step2ErrorDetails, setStep2ErrorDetails] = useState<string | null>(null);

  // Step 3 state (brain dump -- new position after reorder)
  const [brainDump, setBrainDump] = useState("");
  const [showRestoreBanner, setShowRestoreBanner] = useState(false);
  const [draftSaveTimeout, setDraftSaveTimeout] = useState<ReturnType<typeof setTimeout> | null>(null);
  const userHasTypedRef = useRef(false);
  const brainDumpTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const linkCount = useMemo(
    () => (brainDump.match(/https?:\/\/[^\s]+/g) ?? []).length,
    [brainDump]
  );
  const [tipsOpen, setTipsOpen] = useState(false);
  const tipsToggleId = useId();
  const tipsPanelId = useId();
  const [step3Loading, setStep3Loading] = useState(false);
  const [step3Error, setStep3Error] = useState<string | null>(null);

  // Step 4 state (platform connection -- new position after reorder)
  const [oauthReturnError, setOauthReturnError] = useState<string | null>(null);
  const [campaignIdForNav, setCampaignIdForNav] = useState<string | null>(null);
  const [campaignJobIdForNav, setCampaignJobIdForNav] = useState<string | null>(null);

  // Global complete-onboarding error
  const [completeError, setCompleteError] = useState<string | null>(null);

  const activeClientId = useClientStore((s) => s.activeClientId);

  const nameInputRef = useRef<HTMLInputElement>(null);

  // TanStack Query: load clients list (RSC rule -- all data fetching in client components via TanStack Query)
  // Hydrates createdClientId on resume so step 2+ can continue with an existing client.
  const { isSuccess: clientsQuerySuccess, data: clientsQueryData } = useQuery({
    queryKey: ["clients-onboarding"],
    queryFn: async () => {
      const result = await clientsApi.list();
      // Resume: if we have no createdClientId yet but there are clients, hydrate from most recent
      if (result.clients.length > 0 && !createdClientId) {
        // Sort by created_at descending to reliably pick the newest client
        const sorted = [...result.clients].sort(
          (a, b) => new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime()
        );
        setCreatedClientId(sorted[0].id);
      }
      return result;
    },
    staleTime: 60_000,
    // Only run on mount (don't re-run if user is mid-onboarding and createdClientId is set)
    enabled: !createdClientId,
  });

  // Guard: if the clients query settled with an empty list while we're mid-onboarding,
  // fall back to Step 1 so the user isn't stuck on a blank screen (AC 1 resume edge case).
  useEffect(() => {
    if (
      clientsQuerySuccess &&
      clientsQueryData?.clients.length === 0 &&
      !createdClientId &&
      step >= 2
    ) {
      setStep(1);
    }
  }, [clientsQuerySuccess, clientsQueryData, createdClientId, step]);

  // Focus name input on mount
  useEffect(() => {
    nameInputRef.current?.focus();
  }, []);

  // OAuth return detection -- runs once on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthSuccess = params.get("success");
    const oauthError = params.get("error");
    if (!oauthSuccess && !oauthError) return; // not an OAuth redirect
    const savedClientId = sessionStorage.getItem("onboarding_client_id");
    if (!savedClientId) return; // not from our OAuth flow

    // Restore campaign context for final redirect (AC: 6)
    const savedCampaignId = sessionStorage.getItem("onboarding_campaign_id");
    const savedCampaignJobId = sessionStorage.getItem("onboarding_job_id");

    // Clean up
    sessionStorage.removeItem("onboarding_client_id");
    sessionStorage.removeItem("onboarding_campaign_id");
    sessionStorage.removeItem("onboarding_job_id");
    window.history.replaceState({}, "", "/onboarding");

    setCreatedClientId(savedClientId);
    setStep2View("questionnaire"); // safe default
    if (savedCampaignId) setCampaignIdForNav(savedCampaignId);
    if (savedCampaignJobId) setCampaignJobIdForNav(savedCampaignJobId);

    // Prefer error over success when both are present (degenerate OAuth response)
    if (oauthError) {
      setOauthReturnError(oauthError);
      setStep(4); // back to platform step (Step 4 after reorder) with error
    } else {
      setOauthReturnError(null);
      setStep(4); // connected -- still on Step 4; completeOnboarding fires on exit
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Guard: if step >= 3 (brain dump or platform) but no client yet, fall back to step 1.
  // A client is required before any content-creation step.
  useEffect(() => {
    if (step >= 3 && !createdClientId && !activeClientId) {
      setStep(1);
    }
  }, [step, createdClientId, activeClientId]);

  // Draft restore check when step 3 (brain dump) first renders
  useEffect(() => {
    if (step !== 3) return;
    if (userHasTypedRef.current) return; // user already typed, don't clobber
    const draft = readDraft();
    if (draft && draft.text && !brainDump) {
      setShowRestoreBanner(true);
    }
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Step persistence fire-and-forget ──────────────────────────────────────
  const persistStep = useCallback((s: number) => {
    authApi.patchOnboardingStep(s).catch(() => {
      // fire-and-forget: failure never blocks UI
    });
  }, []);

  // ── Skip all ──────────────────────────────────────────────────────────────
  const handleSkipAll = useCallback(async () => {
    try {
      setCompleteError(null);
      await authApi.completeOnboarding();
      clearDraft();
      router.push("/dashboard");
    } catch {
      setCompleteError("Could not save progress. Please try again.");
    }
  }, [router]);

  // ── Step 1 submit ──────────────────────────────────────────────────────────
  const handleStep1Submit = async () => {
    if (!clientName.trim()) {
      setNameError("Client name is required.");
      nameInputRef.current?.focus();
      return;
    }
    setNameError(null);
    setStep1Loading(true);
    setStep1Error(null);
    try {
      const client = await clientsApi.create({
        name: clientName.trim(),
        website_url: websiteUrl.trim() || undefined,
      });
      setCreatedClientId(client.id);

      if (websiteUrl.trim() && client.job_id) {
        setJobId(client.job_id);
        setStep2View("in-progress");
        setStep2ErrorDetails(null);
      } else {
        setJobId(null);
        setStep2View("questionnaire");
        setStep2ErrorDetails(null);
      }
      persistStep(1);
      setStep(2);
    } catch (err: unknown) {
      setStep1Error(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setStep1Loading(false);
    }
  };

  // ── Step 2 skip ────────────────────────────────────────────────────────────
  const handleSkipStep2 = () => {
    persistStep(2);
    setStep(3);
  };

  // ── Step 2 complete ────────────────────────────────────────────────────────
  const handleStep2Complete = () => {
    persistStep(2);
    setStep(3);
  };

  // ── Brain dump change with debounced draft save (AC: 5) ───────────────────
  const handleBrainDumpChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length > MAX_BRAIN_DUMP) return;
    userHasTypedRef.current = true;
    setBrainDump(value);
    setShowRestoreBanner(false); // hide banner once user starts typing

    if (draftSaveTimeout) clearTimeout(draftSaveTimeout);
    const t = setTimeout(() => saveDraft(value), 600);
    setDraftSaveTimeout(t);
  };

  // ── Restore draft ─────────────────────────────────────────────────────────
  const handleRestoreDraft = () => {
    const draft = readDraft();
    if (draft) {
      setBrainDump(draft.text);
      userHasTypedRef.current = true;
    }
    setShowRestoreBanner(false);
  };

  // ── Voice recording transcript appended at cursor (AC: 4) ─────────────────
  const handleVoiceTranscript = useCallback((transcript: string) => {
    if (!transcript.trim()) return; // 20-7 empty-transcript guard
    setBrainDump((prev) => {
      const ta = brainDumpTextareaRef.current;
      if (ta) {
        const start = ta.selectionStart ?? prev.length;
        const separator = prev && !prev.endsWith(" ") && !prev.endsWith("\n") ? " " : "";
        return (prev.slice(0, start) + separator + transcript + prev.slice(start)).slice(0, MAX_BRAIN_DUMP);
      }
      const separator = prev && !prev.endsWith(" ") && !prev.endsWith("\n") ? " " : "";
      return (prev + separator + transcript).slice(0, MAX_BRAIN_DUMP);
    });
    userHasTypedRef.current = true;
    setShowRestoreBanner(false);
  }, []);

  // ── Step 3 submit (brain dump -- campaign creation fires here) ────────────
  // NOTE: completeOnboarding does NOT fire here (user still has Step 4 to complete)
  const handleStep3Submit = async () => {
    setStep3Loading(true);
    setStep3Error(null);

    const clientId = createdClientId ?? activeClientId;
    if (!clientId) {
      setStep3Error("Create a client first. Go back to Step 1.");
      setStep3Loading(false);
      return;
    }

    try {
      const { campaign_id, job_id } = await campaignsApi.create({
        client_id: clientId,
        brain_dump: brainDump,
      });
      // Store for the final redirect from Step 4
      setCampaignIdForNav(campaign_id);
      setCampaignJobIdForNav(job_id);
      // Persist in sessionStorage so OAuth return can recover campaign context
      try {
        sessionStorage.setItem("onboarding_campaign_id", campaign_id);
        sessionStorage.setItem("onboarding_job_id", job_id);
      } catch {
        // storage unavailable -- redirect will fall back to /dashboard
      }
      clearDraft(); // AC 5: clear draft on successful campaign creation
      persistStep(3);
      setStep(4);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      setStep3Error(`Could not start generation: ${message}`);
    } finally {
      setStep3Loading(false);
    }
  };

  // ── Step 3 skip (brain dump) ───────────────────────────────────────────────
  // Skip from brain dump still calls completeOnboarding (user opts out of generation entirely)
  const handleSkipStep3 = async () => {
    setCompleteError(null);
    try {
      await authApi.completeOnboarding();
      clearDraft();
      router.push("/dashboard?nudge=true");
    } catch {
      setCompleteError("Could not save progress. Please try again.");
    }
  };

  // ── Step 4 (platform) -- every exit path calls completeOnboarding ──────────
  // Invariant: a user can NEVER be stuck with onboarding_completed=false and no path forward.
  const completeAndNavigate = useCallback(async () => {
    setCompleteError(null);
    try {
      await authApi.completeOnboarding();
      clearDraft();
      try {
        sessionStorage.removeItem("onboarding_campaign_id");
        sessionStorage.removeItem("onboarding_job_id");
      } catch {
        // noop
      }
      if (campaignIdForNav && campaignJobIdForNav) {
        router.push(`/campaigns/${campaignIdForNav}?job_id=${campaignJobIdForNav}`);
      } else {
        router.push("/dashboard");
      }
    } catch {
      setCompleteError("Could not save progress. Please try again.");
    }
  }, [router, campaignIdForNav, campaignJobIdForNav]);

  const handleStep4Continue = useCallback(() => {
    completeAndNavigate();
  }, [completeAndNavigate]);

  const handleSkipStep4 = useCallback(() => {
    completeAndNavigate();
  }, [completeAndNavigate]);

  // ── Keyboard handlers ──────────────────────────────────────────────────────
  const handleBrainDumpKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (brainDump.length >= MIN_BRAIN_DUMP) handleStep3Submit();
    }
  };

  // ══════════════════════════════════════════════════════════════════════════
  // STEP 1
  // ══════════════════════════════════════════════════════════════════════════
  if (step === 1) {
    return (
      <div className="w-full max-w-lg">
        <h1 className="font-['Playfair_Display'] text-[2.25rem] font-bold leading-[1.15] tracking-[-0.01em] text-[#111111] mb-2 text-balance">
          Who are you writing for?
        </h1>
        <p className="text-[0.9375rem] text-[#555555] leading-[1.6] mb-8 text-pretty">
          A Client is the brand voice you&apos;re building. Start with yours.
        </p>

        <Card>
          <div className="mb-6">
            <label
              htmlFor="client-name"
              className="block text-xs uppercase tracking-[0.06em] text-[#555555] mb-1"
            >
              Client name
            </label>
            <Input
              id="client-name"
              ref={nameInputRef}
              value={clientName}
              onChange={(e) => {
                setClientName(e.target.value);
                if (nameError) setNameError(null);
              }}
              placeholder="Your brand or company name"
              required
              aria-required="true"
              aria-describedby={nameError ? "client-name-error" : undefined}
            />
            {nameError && (
              <p id="client-name-error" role="alert" className="text-sm text-[#8B0000] mt-1">
                {nameError}
              </p>
            )}
          </div>

          <div className="mb-8">
            <label
              htmlFor="website-url"
              className="block text-xs uppercase tracking-[0.06em] text-[#555555] mb-1"
            >
              Website URL
            </label>
            <p className="text-xs text-[#555555] mb-1">
              Recommended: automatic voice setup
            </p>
            <Input
              id="website-url"
              type="url"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://yoursite.com"
            />
          </div>

          {step1Error && (
            <p role="alert" className="text-sm text-[#8B0000] mb-4">
              {step1Error}
            </p>
          )}

          <Button
            type="button"
            onClick={handleStep1Submit}
            disabled={step1Loading}
            aria-busy={step1Loading}
            className="w-full justify-center"
          >
            {step1Loading ? "Creating..." : "Create client and analyze voice"}
          </Button>

          {completeError && (
            <p role="alert" className="text-sm text-[#8B0000] mt-2 text-center">
              {completeError}
            </p>
          )}
          <SkipLink onClick={handleSkipAll}>
            Skip for now
          </SkipLink>
        </Card>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // STEP 2
  // ══════════════════════════════════════════════════════════════════════════
  if (step === 2 && !createdClientId) return null;

  if (step === 2 && createdClientId) {
    return (
      <div className="w-full max-w-lg">
        <ProgressIndicator step={2} />
        <Card>
          <Step2Content
            view={step2View}
            jobId={jobId}
            clientId={createdClientId}
            websiteUrl={websiteUrl}
            errorDetails={step2ErrorDetails}
            onStep2Complete={handleStep2Complete}
            onJobStarted={(jId) => setJobId(jId)}
          />
        </Card>
        <SkipLink onClick={handleSkipStep2}>
          Skip
        </SkipLink>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // STEP 3 -- Brain dump (reordered: was Step 4)
  // ══════════════════════════════════════════════════════════════════════════
  if (step === 3) {
    const clientId = createdClientId ?? activeClientId;
    return (
      <div className="w-full max-w-lg">
        <ProgressIndicator step={3} />

        <h2 className="font-['Playfair_Display'] text-[1.5rem] font-bold leading-[1.2] tracking-[-0.01em] text-[#111111] mb-3 text-center text-balance">
          What&apos;s on your mind this week?
        </h2>
        <p className="text-[0.9375rem] text-[#555555] leading-[1.6] mb-6 text-center text-pretty">
          Paste anything: bullet points, half-formed thoughts, a topic title.
          PersonnaPress will do the rest.
        </p>

        <Card>
          {/* Restore draft banner (AC: 5, 3-18 pattern) */}
          {showRestoreBanner && (
            <div className="flex items-center justify-between gap-2 border border-[#E5E5E5] bg-[#F9F9F6] p-3 mb-4">
              <p className="text-sm text-[#555555]">
                You have a saved draft. Restore it?
              </p>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={handleRestoreDraft}
                  className="text-sm text-[#111111] underline hover:no-underline focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
                >
                  Restore
                </button>
                <button
                  type="button"
                  onClick={() => setShowRestoreBanner(false)}
                  aria-label="Dismiss draft restore banner"
                  className="text-sm text-[#555555] hover:text-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Voice recorder (AC: 4 -- VoiceBrainDump reused from campaigns, identical behavior) */}
          <div className="mb-3">
            <VoiceBrainDump onTranscript={handleVoiceTranscript} />
          </div>

          <div className="mb-2">
            <label htmlFor="brain-dump" className="sr-only">
              Brain dump
            </label>
            <BrainDumpInput
              id="brain-dump"
              ref={brainDumpTextareaRef}
              value={brainDump}
              onChange={handleBrainDumpChange}
              onKeyDown={handleBrainDumpKeyDown}
              placeholder={`e.g. "I ran a 90-day test comparing 3 LinkedIn posting strategies, daily tips vs. 3x storytelling vs. 2x case studies. Case studies drove 4x more DMs. Most people post daily tips because it feels safe. Here's what I found and why I switched..."`}
              className="min-h-[200px] border-b border-[#E5E5E5] focus:border-b-2 focus:border-[#111111]"
              aria-describedby="brain-dump-count"
              maxLength={MAX_BRAIN_DUMP}
            />
            <p
              id="brain-dump-count"
              className="text-xs text-[#555555] font-mono text-right mt-1"
            >
              {brainDump.length} / {MAX_BRAIN_DUMP.toLocaleString()} characters
            </p>
            <div aria-live="polite" aria-atomic="true">
              {brainDump.length > 0 && brainDump.length < 150 && (
                <p className="flex items-center gap-1 text-xs text-[#555555] mt-1">
                  <Lightbulb size={12} aria-hidden="true" />
                  Tip: include a specific number, personal outcome, or named tool for best results.
                </p>
              )}
            </div>
            <div aria-live="polite" aria-atomic="true">
              {linkCount > 0 && (
                <p className="flex items-center gap-1 text-xs font-mono text-sky-600 mt-1">
                  <LinkIcon size={12} aria-hidden="true" />
                  {linkCount === 1 ? "1 link detected" : `${linkCount} links detected`}, will be cited in your article
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

          {step3Error && (
            <div
              role="alert"
              className="border border-danger/30 bg-danger/5 p-4 mt-4"
            >
              <p className="text-sm font-mono text-danger">{step3Error}</p>
              <button
                type="button"
                className="text-sm font-mono text-danger underline hover:no-underline mt-1"
                onClick={() => setStep3Error(null)}
              >
                Try again
              </button>
            </div>
          )}

          {!clientId && (
            <p className="text-sm text-[#555555] mt-3 text-center">
              Create a client first.
            </p>
          )}

          {completeError && (
            <p role="alert" className="text-sm text-[#8B0000] mt-2 text-center">
              {completeError}
            </p>
          )}

          <Button
            type="button"
            onClick={handleStep3Submit}
            disabled={
              brainDump.length < MIN_BRAIN_DUMP ||
              step3Loading ||
              !clientId
            }
            aria-busy={step3Loading}
            className="w-full justify-center mt-4"
          >
            {step3Loading ? "Generating..." : "Generate my first campaign"}
          </Button>
          <SkipLink onClick={handleSkipStep3}>
            I&apos;ll write my first draft later.
          </SkipLink>
        </Card>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  // STEP 4 -- Platform connection (reordered: was Step 3)
  //           Framed as "Publish what you just made"
  // ══════════════════════════════════════════════════════════════════════════
  if (step === 4 && !createdClientId && !activeClientId) return null; // brief flash until guard effect fires

  if (step === 4 && (createdClientId || activeClientId)) {
    const clientId = (createdClientId ?? activeClientId)!;
    const hasCampaign = !!(campaignIdForNav && campaignJobIdForNav);

    return (
      <div className="w-full max-w-lg">
        <ProgressIndicator step={4} />
        <h2 className="font-['Playfair_Display'] text-[1.5rem] font-bold leading-[1.2] tracking-[-0.01em] text-[#111111] mb-3 text-center text-balance">
          Publish what you just made
        </h2>
        <p className="text-[0.9375rem] text-[#555555] leading-[1.6] mb-6 text-center text-pretty">
          {hasCampaign
            ? "Your first campaign is generating. Connect a platform to publish it in one click."
            : "Connect a platform so you're ready to publish your first campaign in one click."}
        </p>

        {completeError && (
          <p role="alert" className="text-sm text-[#8B0000] mb-4 text-center">
            {completeError}
          </p>
        )}

        <OnboardingPlatformStep
          clientId={clientId}
          oauthError={oauthReturnError}
          onContinue={handleStep4Continue}
          onSkip={handleSkipStep4}
          campaignId={campaignIdForNav}
          campaignJobId={campaignJobIdForNav}
        />
      </div>
    );
  }

  return null;
}
