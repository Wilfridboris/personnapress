"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { clientsApi } from "@/lib/api";
import { useJobStatus } from "@/hooks/useJobStatus";
import { Button } from "@/components/ui/Button";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { Input } from "@/components/ui/Input";
import { TagChip } from "@/components/ui/TagChip";
import { VoiceQuestionnaire } from "@/components/clients/VoiceQuestionnaire";
import { ExpandedProfileReview } from "@/components/clients/ExpandedProfileReview";
import type { BrandVoiceCadence, BrandVoiceProfile, ClientResponse } from "@/lib/types";

interface Props {
  client: ClientResponse;
}

type View = "review" | "in-progress" | "failed" | "questionnaire";

// ── Section label ─────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-sans text-xs uppercase tracking-[0.06em] text-[#111111] mb-3">
      {children}
    </p>
  );
}

// ── Profile Review ────────────────────────────────────────────────────────────
interface ProfileReviewProps {
  bvp: BrandVoiceProfile;
  clientId: string;
  onRefresh?: () => void;
  refreshDisabled?: boolean;
  refreshBtnRef?: React.RefObject<HTMLButtonElement | null>;
}

function ProfileReview({ bvp, clientId, onRefresh, refreshDisabled, refreshBtnRef }: ProfileReviewProps) {
  const [editMode, setEditMode] = useState(false);
  const [tone, setTone] = useState<string[]>(bvp.tone ?? []);
  const [cadence, setCadence] = useState<BrandVoiceCadence>(
    bvp.cadence ?? { avg_sentence_length: 0, variation_pattern: "", paragraph_structure: "" }
  );
  const [bannedJargon, setBannedJargon] = useState<string[]>(bvp.banned_jargon ?? []);

  // Tag add inputs
  const [newTone, setNewTone] = useState("");
  const [newJargon, setNewJargon] = useState("");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  const handleConfirm = async () => {
    setSaving(true);
    setError(null);
    setConfirmed(false);
    try {
      await clientsApi.patch(clientId, {
        brand_voice_profile: { tone, cadence, banned_jargon: bannedJargon },
      });
      setConfirmed(true);
      setEditMode(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  const addToneTag = () => {
    const trimmed = newTone.trim();
    if (trimmed && !tone.includes(trimmed)) {
      setTone((prev) => [...prev, trimmed]);
    }
    setNewTone("");
  };

  const addJargonTag = () => {
    const trimmed = newJargon.trim();
    if (trimmed && !bannedJargon.includes(trimmed)) {
      setBannedJargon((prev) => [...prev, trimmed]);
    }
    setNewJargon("");
  };

  return (
    <div className="max-w-xl">
      {/* TONE */}
      <div className="mb-8">
        <SectionLabel>Tone</SectionLabel>
        <div className="flex flex-wrap">
          {tone.map((tag) => (
            <TagChip
              key={tag}
              label={tag}
              readOnly={!editMode}
              onRemove={() => setTone((prev) => prev.filter((t) => t !== tag))}
            />
          ))}
        </div>
        {editMode && (
          <div className="flex items-center gap-2 mt-2">
            <Input
              value={newTone}
              onChange={(e) => setNewTone(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addToneTag())}
              placeholder="Add descriptor…"
              className="max-w-[220px]"
              aria-label="New tone descriptor"
            />
            <Button variant="secondary" type="button" onClick={addToneTag} className="text-sm px-3 py-1.5">
              Add
            </Button>
          </div>
        )}
      </div>

      {/* CADENCE */}
      <div className="mb-8">
        <SectionLabel>Cadence</SectionLabel>

        <div className="mb-4">
          <label className="block text-xs uppercase tracking-[0.06em] text-[#555555] mb-1">
            Avg. sentence length
          </label>
          {editMode ? (
            <input
              type="number"
              value={cadence.avg_sentence_length}
              onChange={(e) =>
                setCadence((prev) => ({
                  ...prev,
                  avg_sentence_length: Number(e.target.value),
                }))
              }
              className="w-20 bg-transparent border-0 border-b border-ink focus:border-b-2 focus:border-ink focus:outline-none focus:ring-0 text-sm text-ink py-2 transition-[border-width] duration-100"
              aria-label="Average sentence length"
            />
          ) : (
            <p className="text-sm text-[#111111] py-2">{cadence.avg_sentence_length}</p>
          )}
        </div>

        <div className="mb-4">
          <label className="block text-xs uppercase tracking-[0.06em] text-[#555555] mb-1">
            Variation pattern
          </label>
          {editMode ? (
            <textarea
              rows={2}
              value={cadence.variation_pattern}
              onChange={(e) =>
                setCadence((prev) => ({ ...prev, variation_pattern: e.target.value }))
              }
              className="w-full bg-transparent border-0 border-b border-ink focus:border-b-2 focus:border-ink focus:outline-none focus:ring-0 text-sm text-ink py-2 resize-none transition-[border-width] duration-100"
              aria-label="Variation pattern"
            />
          ) : (
            <p className="text-sm text-[#111111] py-2 whitespace-pre-wrap">
              {cadence.variation_pattern || <span className="text-[#555555]">—</span>}
            </p>
          )}
        </div>

        <div>
          <label className="block text-xs uppercase tracking-[0.06em] text-[#555555] mb-1">
            Paragraph structure
          </label>
          {editMode ? (
            <textarea
              rows={2}
              value={cadence.paragraph_structure}
              onChange={(e) =>
                setCadence((prev) => ({ ...prev, paragraph_structure: e.target.value }))
              }
              className="w-full bg-transparent border-0 border-b border-ink focus:border-b-2 focus:border-ink focus:outline-none focus:ring-0 text-sm text-ink py-2 resize-none transition-[border-width] duration-100"
              aria-label="Paragraph structure"
            />
          ) : (
            <p className="text-sm text-[#111111] py-2 whitespace-pre-wrap">
              {cadence.paragraph_structure || <span className="text-[#555555]">—</span>}
            </p>
          )}
        </div>
      </div>

      {/* BANNED JARGON */}
      <div className="mb-8">
        <SectionLabel>Banned jargon</SectionLabel>
        <div className="flex flex-wrap">
          {bannedJargon.map((tag) => (
            <TagChip
              key={tag}
              label={tag}
              readOnly={!editMode}
              onRemove={() => setBannedJargon((prev) => prev.filter((t) => t !== tag))}
            />
          ))}
          {bannedJargon.length === 0 && !editMode && (
            <p className="text-sm text-[#555555]">None specified.</p>
          )}
        </div>
        {editMode && (
          <div className="flex items-center gap-2 mt-2">
            <Input
              value={newJargon}
              onChange={(e) => setNewJargon(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addJargonTag())}
              placeholder="Add jargon to avoid…"
              className="max-w-[220px]"
              aria-label="New banned jargon term"
            />
            <Button variant="secondary" type="button" onClick={addJargonTag} className="text-sm px-3 py-1.5">
              Add
            </Button>
          </div>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-[#8B0000] mb-4">
          {error}
        </p>
      )}

      {confirmed && !editMode && (
        <p className="text-[#2E4F2E] text-sm mb-4">Voice profile confirmed.</p>
      )}

      <div className="flex items-center gap-3">
        {editMode ? (
          <>
            <Button onClick={handleConfirm} disabled={saving} aria-busy={saving} type="button">
              {saving ? "Saving..." : "Confirm profile"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setEditMode(false)}
              disabled={saving}
              type="button"
            >
              Cancel
            </Button>
          </>
        ) : (
          <>
            <Button onClick={handleConfirm} disabled={saving} aria-busy={saving} type="button">
              {saving ? "Saving..." : "Confirm profile"}
            </Button>
            <Button variant="secondary" onClick={() => setEditMode(true)} type="button">
              Edit profile
            </Button>
          </>
        )}
      </div>

      {onRefresh && (
        <div className="mt-6">
          <Button
            ref={refreshBtnRef}
            variant="secondary"
            onClick={onRefresh}
            disabled={refreshDisabled}
            type="button"
          >
            Refresh voice profile
          </Button>
        </div>
      )}
    </div>
  );
}

// ── In-progress state ─────────────────────────────────────────────────────────
function InProgressState() {
  return (
    <p className="font-mono text-sm text-[#555555] animate-pulse">
      Extracting your voice profile...
    </p>
  );
}

// ── Extraction failed state ───────────────────────────────────────────────────
interface ExtractionFailedProps {
  clientId: string;
  onShowQuestionnaire: () => void;
}

function ExtractionFailed({ clientId, onShowQuestionnaire }: ExtractionFailedProps) {
  return (
    <div>
      <p className="text-sm text-[#555555] mb-6">
        Voice profile extraction failed. Complete the questionnaire to set up your profile manually.
      </p>
      <Button onClick={onShowQuestionnaire} type="button">
        Complete questionnaire
      </Button>
    </div>
  );
}

// ── VoiceSetupPage ────────────────────────────────────────────────────────────
export function VoiceSetupPage({ client }: Props) {
  const router = useRouter();

  const initialView = (): View => {
    if (client.brand_voice_profile) return "review";
    if (client.job_id) return "in-progress";
    if (client.ingestion_no_content) return "questionnaire"; // AC5: no content → questionnaire directly
    if (client.ingestion_failed) return "failed";
    return "questionnaire";
  };

  const [view, setView] = useState<View>(initialView);
  const [activeJobId, setActiveJobId] = useState<string | null>(client.job_id ?? null);
  const [showRefreshModal, setShowRefreshModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  // Track BVP in state so the review shows updated values after a completed refresh
  const [bvp, setBvp] = useState(client.brand_voice_profile);
  const refreshBtnRef = useRef<HTMLButtonElement>(null);

  const { job } = useJobStatus(activeJobId);

  // P6: true when activeJobId is set and job is either not yet loaded or in a non-terminal state
  const jobIsActive =
    !!activeJobId && (!job || !["completed", "complete", "failed"].includes(job.status));

  useEffect(() => {
    if (!job) return;
    if (job.status === "completed" || job.status === "complete") {
      setActiveJobId(null); // P1: stop polling before refreshing
      router.refresh();
    } else if (job.status === "failed") {
      // AC#4 / AC#6: check error_details to choose next state
      if (job.error_details === "no_content") {
        setView("questionnaire");
      } else {
        setView("failed");
      }
      setActiveJobId(null);
    }
  }, [job, router]);

  // Sync bvp when client prop changes (after router.refresh() resolves)
  useEffect(() => {
    if (client.brand_voice_profile) {
      setBvp(client.brand_voice_profile);
      setView("review");
    }
  }, [client.brand_voice_profile]);

  const handleJobStarted = (jobId: string) => {
    setActiveJobId(jobId);
    setView("in-progress");
  };

  const handleRefreshConfirm = async () => {
    setRefreshing(true);
    setRefreshError(null);
    setBvp(null); // P7: null BVP immediately so old profile isn't visible during the call
    try {
      const { job_id } = await clientsApi.ingest(client.id);
      setShowRefreshModal(false);
      setActiveJobId(job_id);
      setView("in-progress");
    } catch {
      setBvp(client.brand_voice_profile); // restore if the call failed
      setRefreshError("Failed to start re-analysis. Please try again.");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <>
      {/* Back link */}
      <Link
        href={`/clients/${client.id}`}
        className="inline-flex items-center gap-2 text-sm text-[#555555] hover:text-[#111111] transition-colors mb-10"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to client
      </Link>

      {/* Page header */}
      <header className="mb-10">
        <h1 className="font-serif text-[2.25rem] font-bold tracking-[-0.01em] text-[#111111] mb-1">
          Brand Voice
        </h1>
        <p className="text-sm text-[#555555]">{client.name}</p>
      </header>

      <hr className="border-[#E5E5E5] mb-10" />

      {/* Content area */}
      {view === "review" && bvp && (
        <ExpandedProfileReview
          bvp={bvp}
          clientId={client.id}
          onRefresh={() => setShowRefreshModal(true)}
          refreshDisabled={!!jobIsActive}
          refreshBtnRef={refreshBtnRef}
        />
      )}

      {view === "in-progress" && <InProgressState />}

      {view === "failed" && (
        <ExtractionFailed
          clientId={client.id}
          onShowQuestionnaire={() => setView("questionnaire")}
        />
      )}

      {view === "questionnaire" && (
        <VoiceQuestionnaire clientId={client.id} onJobStarted={handleJobStarted} />
      )}

      {/* Refresh confirmation modal (AC#2, AC#3) */}
      <ConfirmModal
        isOpen={showRefreshModal}
        onClose={() => { setShowRefreshModal(false); setRefreshError(null); }}
        onConfirm={handleRefreshConfirm}
        title="Re-analyze voice profile?"
        description={`This will update ${client.name}'s voice profile with insights from the new content. Existing values are preserved where possible.`}
        confirmLabel="Re-analyze"
        confirmVariant="primary"
        isLoading={refreshing}
        triggerRef={refreshBtnRef}
        error={refreshError}
      />
    </>
  );
}
