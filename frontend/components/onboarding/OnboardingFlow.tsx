"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { authApi, clientsApi, campaignsApi } from "@/lib/api";
import { useClientStore } from "@/lib/stores/useClientStore";
import { useJobStatus } from "@/hooks/useJobStatus";
import { Button } from "@/components/ui/Button";
import { Input, BrainDumpInput } from "@/components/ui/Input";
import { TagChip } from "@/components/ui/TagChip";
import { VoiceQuestionnaire } from "@/components/clients/VoiceQuestionnaire";
import type { BrandVoiceProfile, BrandVoiceCadence } from "@/lib/types";

type OnboardingStep = 1 | 2 | 3;
type Step2View = "in-progress" | "questionnaire" | "review" | "failed";

const MAX_BRAIN_DUMP = 10_000;
const MIN_BRAIN_DUMP = 20;

// ── Progress indicator ─────────────────────────────────────────────────────────
function ProgressIndicator({ step, total }: { step: number; total: number }) {
  return (
    <p className="text-xs font-medium uppercase tracking-[0.06em] text-[#555555] mb-6">
      {step} of {total}
    </p>
  );
}

// ── Skip link ──────────────────────────────────────────────────────────────────
function SkipLink({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full text-center text-sm text-[#555555] mt-4 hover:text-[#111111] underline underline-offset-2"
    >
      {children}
    </button>
  );
}

// ── Inline BVP Review for Step 2 ──────────────────────────────────────────────
interface InlineProfileReviewProps {
  bvp: BrandVoiceProfile;
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
          placeholder="Add tone descriptor…"
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

      {error && (
        <p role="alert" className="text-sm text-[#8B0000] mb-4">
          {error}
        </p>
      )}

      <Button onClick={handleConfirm} disabled={saving} aria-busy={saving} type="button">
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
  onStep2Complete: () => void;
  onJobStarted: (jobId: string) => void;
}

function Step2Content({ view, jobId, clientId, websiteUrl, onStep2Complete, onJobStarted }: Step2ContentProps) {
  const { job } = useJobStatus(jobId);
  const [currentView, setCurrentView] = useState<Step2View>(view);
  const [bvp, setBvp] = useState<BrandVoiceProfile | null>(null);
  const [statusText, setStatusText] = useState(`Scraping ${websiteUrl}...`);

  useEffect(() => {
    setCurrentView(view);
  }, [view]);

  useEffect(() => {
    if (!job) return;
    if (job.status === "completed" || job.status === "complete") {
      // Fetch updated client to get BVP
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

  if (currentView === "in-progress") {
    return (
      <p className="font-mono text-sm text-[#555555] animate-pulse">
        {statusText}
      </p>
    );
  }

  if (currentView === "questionnaire") {
    return (
      <VoiceQuestionnaire
        clientId={clientId}
        onJobStarted={(jId) => {
          onJobStarted(jId);
          setCurrentView("in-progress");
        }}
      />
    );
  }

  if (currentView === "failed") {
    return (
      <div>
        <p className="text-sm text-[#555555] mb-4">
          Voice profile extraction failed. Complete the questionnaire to set up your profile manually.
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
// Defined outside OnboardingFlow so React doesn't treat it as a new component
// type on every parent re-render (which would remount children and lose focus).
function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white border border-[#E5E5E5] p-8 w-full max-w-lg">
      {children}
    </div>
  );
}

// ── Main OnboardingFlow ────────────────────────────────────────────────────────
export function OnboardingFlow() {
  const router = useRouter();
  const [step, setStep] = useState<OnboardingStep>(1);

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

  // Step 3 state
  const [brainDump, setBrainDump] = useState("");
  const [step3Loading, setStep3Loading] = useState(false);
  const [step3Error, setStep3Error] = useState<string | null>(null);

  // Global complete-onboarding error
  const [completeError, setCompleteError] = useState<string | null>(null);

  const activeClientId = useClientStore((s) => s.activeClientId);

  const nameInputRef = useRef<HTMLInputElement>(null);

  // Focus name input on mount
  useEffect(() => {
    nameInputRef.current?.focus();
  }, []);

  // ── Skip all ──────────────────────────────────────────────────────────────
  const handleSkipAll = useCallback(async () => {
    try {
      setCompleteError(null);
      await authApi.completeOnboarding();
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
      } else {
        setJobId(null);
        setStep2View("questionnaire");
      }
      setStep(2);
    } catch (err: unknown) {
      setStep1Error(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setStep1Loading(false);
    }
  };

  // ── Step 2 skip ────────────────────────────────────────────────────────────
  const handleSkipStep2 = () => {
    setStep(3);
  };

  // ── Step 2 complete ────────────────────────────────────────────────────────
  const handleStep2Complete = () => {
    setStep(3);
  };

  // ── Step 3 submit ──────────────────────────────────────────────────────────
  const handleStep3Submit = async () => {
    setStep3Loading(true);
    setStep3Error(null);

    try {
      // Complete onboarding FIRST so JWT has onboarding_completed=true before navigation
      await authApi.completeOnboarding();

      const clientId = createdClientId ?? activeClientId;
      if (!clientId) {
        setStep3Error("Create a client first. Go back to Step 1.");
        return;
      }

      const { campaign_id, job_id } = await campaignsApi.create({
        client_id: clientId,
        brain_dump: brainDump,
      });

      router.push(`/campaigns/${campaign_id}?job_id=${job_id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      setStep3Error(`Could not start generation: ${message}`);
    } finally {
      setStep3Loading(false);
    }
  };

  // ── Step 3 skip ────────────────────────────────────────────────────────────
  const handleSkipStep3 = async () => {
    setCompleteError(null);
    try {
      await authApi.completeOnboarding();
      router.push("/dashboard?nudge=true");
    } catch {
      setCompleteError("Could not save progress. Please try again.");
    }
  };

  // ── Keyboard handlers ──────────────────────────────────────────────────────
  const handleBrainDumpKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape") {
      e.preventDefault(); // prevents blur/form reset on some browsers
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
        <h1 className="font-['Playfair_Display'] text-[2.25rem] font-bold leading-[1.15] tracking-[-0.01em] text-[#111111] mb-2">
          Who are you writing for?
        </h1>
        <p className="text-[0.9375rem] text-[#555555] leading-[1.6] mb-8">
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
        <ProgressIndicator step={2} total={3} />
        <Card>
          <Step2Content
            view={step2View}
            jobId={jobId}
            clientId={createdClientId}
            websiteUrl={websiteUrl}
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
  // STEP 3
  // ══════════════════════════════════════════════════════════════════════════
  return (
    <div className="w-full max-w-lg">
      <ProgressIndicator step={3} total={3} />

      <h2 className="font-['Playfair_Display'] text-[1.5rem] font-bold leading-[1.2] tracking-[-0.01em] text-[#111111] mb-3 text-center">
        What&apos;s on your mind this week?
      </h2>
      <p className="text-[0.9375rem] text-[#555555] leading-[1.6] mb-6 text-center">
        Paste anything: bullet points, half-formed thoughts, a topic title.
        PersonnaPress will do the rest.
      </p>

      <Card>
        <div className="mb-2">
          <label htmlFor="brain-dump" className="sr-only">
            Brain dump
          </label>
          <BrainDumpInput
            id="brain-dump"
            value={brainDump}
            onChange={(e) => {
              if (e.target.value.length <= MAX_BRAIN_DUMP) {
                setBrainDump(e.target.value);
              }
            }}
            onKeyDown={handleBrainDumpKeyDown}
            placeholder="What are you thinking about this week?"
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

        {createdClientId === null && activeClientId === null && (
          <p className="text-sm text-[#555555] mt-3 text-center">
            Create a client first.
          </p>
        )}

        <Button
          type="button"
          onClick={handleStep3Submit}
          disabled={
            brainDump.length < MIN_BRAIN_DUMP ||
            step3Loading ||
            (createdClientId === null && activeClientId === null)
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
