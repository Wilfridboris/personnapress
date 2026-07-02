"use client";

import { useState } from "react";
import type { VoiceScore } from "@/lib/types";

interface Props {
  voiceScore: VoiceScore;
}

export function VoiceFidelityBadge({ voiceScore }: Props) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasFailed =
    voiceScore.tone_score < 7 ||
    voiceScore.cadence_score < 6 ||
    voiceScore.jargon_violations > 0;

  if (!hasFailed) return null;

  return (
    <div>
      <button
        type="button"
        aria-expanded={isExpanded}
        aria-controls="voice-detail"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="inline-flex items-center rounded-none gap-2 text-xs font-medium uppercase tracking-widest text-danger border border-danger/30 px-3 py-1 hover:bg-danger/5 transition-colors focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2"
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
      </div>
    </div>
  );
}
