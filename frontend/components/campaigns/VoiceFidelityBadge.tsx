"use client";

import { useState } from "react";
import { Wand2 } from "lucide-react";
import type { VoiceScore } from "@/lib/types";

interface Props {
  voiceScore: VoiceScore;
}

export function VoiceFidelityBadge({ voiceScore }: Props) {
  const [isExpanded, setIsExpanded] = useState(false);

  const passagesRewritten = voiceScore.authored_passages_preserved === false;

  // Read final scores from flat keys (always hold final values per AC 2)
  const hasFailed =
    voiceScore.tone_score < 7 ||
    voiceScore.cadence_score < 6 ||
    voiceScore.jargon_violations > 0 ||
    passagesRewritten;

  const wasRepaired = voiceScore.repaired === true;
  const repairedAndPassing = wasRepaired && !hasFailed;

  // Voice-tuned: repaired and now passing -- show informational badge, not failure badge
  if (repairedAndPassing) {
    return (
      <div
        title="This draft was automatically adjusted to match your voice profile."
        className="inline-flex items-center gap-2 rounded-none border border-ink/30 px-3 py-1 text-xs font-medium uppercase tracking-widest text-ink"
      >
        <Wand2 aria-hidden="true" className="size-3.5 shrink-0" />
        Voice-tuned
      </div>
    );
  }

  // No issues and not repaired: render nothing
  if (!hasFailed) return null;

  return (
    <div>
      <button
        type="button"
        aria-expanded={isExpanded}
        aria-controls="voice-detail"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="inline-flex items-center rounded-none gap-2 text-xs font-medium uppercase tracking-widest text-danger border border-danger/30 px-3 py-1 hover:bg-danger/5 transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
      >
        VOICE MATCH: {voiceScore.tone_score}/10 - REVIEW TONE
      </button>

      <div
        id="voice-detail"
        role="region"
        aria-label="Voice fidelity detail"
        aria-live="polite"
        hidden={!isExpanded}
        className="mt-2 text-sm font-mono text-danger/80 space-y-1 border-l-2 border-danger/30 pl-3"
      >
        <p>Tone: {voiceScore.tone_score}/10</p>
        <p>Cadence: {voiceScore.cadence_score}/10</p>
        <p>Jargon violations: {voiceScore.jargon_violations}</p>
        {passagesRewritten && (
          <p>Authored passages: rewritten by AI, consider regenerating</p>
        )}
      </div>
    </div>
  );
}
