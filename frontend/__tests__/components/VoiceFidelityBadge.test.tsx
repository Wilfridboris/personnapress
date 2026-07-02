import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VoiceFidelityBadge } from "@/components/campaigns/VoiceFidelityBadge";
import type { VoiceScore } from "@/lib/types";

const passingScore: VoiceScore = { tone_score: 8, cadence_score: 7, jargon_violations: 0 };
const exactBoundaryScore: VoiceScore = { tone_score: 7, cadence_score: 6, jargon_violations: 0 };
const failingTone: VoiceScore = { tone_score: 6, cadence_score: 7, jargon_violations: 0 };
const failingCadence: VoiceScore = { tone_score: 8, cadence_score: 5, jargon_violations: 0 };
const failingJargon: VoiceScore = { tone_score: 8, cadence_score: 7, jargon_violations: 2 };

describe("VoiceFidelityBadge", () => {
  it("renders null when all scores pass", () => {
    const { container } = render(<VoiceFidelityBadge voiceScore={passingScore} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders badge when tone_score < 7", () => {
    render(<VoiceFidelityBadge voiceScore={failingTone} />);
    expect(screen.getByRole("button", { name: /voice match/i })).toBeInTheDocument();
    expect(screen.getByText(/VOICE MATCH: 6\/10 - REVIEW TONE/i)).toBeInTheDocument();
  });

  it("renders badge when cadence_score < 6", () => {
    render(<VoiceFidelityBadge voiceScore={failingCadence} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("renders badge when jargon_violations > 0", () => {
    render(<VoiceFidelityBadge voiceScore={failingJargon} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("renders null when all scores are at exact passing boundary", () => {
    const { container } = render(<VoiceFidelityBadge voiceScore={exactBoundaryScore} />);
    expect(container.firstChild).toBeNull();
  });

  it("detail panel is hidden by default", () => {
    render(<VoiceFidelityBadge voiceScore={failingTone} />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-expanded", "false");
    // eslint-disable-next-line testing-library/no-node-access
    const panel = document.getElementById("voice-detail");
    expect(panel).toHaveAttribute("hidden");
  });

  it("clicking badge toggles expand/collapse of detail panel", () => {
    render(<VoiceFidelityBadge voiceScore={failingTone} />);
    const button = screen.getByRole("button");

    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("region", { name: /voice fidelity detail/i })).not.toHaveAttribute("hidden");

    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
    // eslint-disable-next-line testing-library/no-node-access
    expect(document.getElementById("voice-detail")).toHaveAttribute("hidden");
  });

  it("detail panel shows all three dimensions when expanded", () => {
    const score: VoiceScore = { tone_score: 5, cadence_score: 4, jargon_violations: 3 };
    render(<VoiceFidelityBadge voiceScore={score} />);

    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByText("Tone: 5/10")).toBeInTheDocument();
    expect(screen.getByText("Cadence: 4/10")).toBeInTheDocument();
    expect(screen.getByText("Jargon violations: 3")).toBeInTheDocument();
  });
});
