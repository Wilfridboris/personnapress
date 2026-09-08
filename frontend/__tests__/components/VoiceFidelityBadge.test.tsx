import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VoiceFidelityBadge } from "@/components/campaigns/VoiceFidelityBadge";
import type { VoiceScore } from "@/lib/types";

// ── Story 26.4 fixtures ───────────────────────────────────────────────────────
const repairedPassingScore: VoiceScore = {
  tone_score: 9,
  cadence_score: 8,
  jargon_violations: 0,
  repaired: true,
  initial: { tone_score: 5, cadence_score: 8, jargon_violations: 0 },
  final: { tone_score: 9, cadence_score: 8, jargon_violations: 0 },
};

const repairedStillFailingScore: VoiceScore = {
  tone_score: 5,
  cadence_score: 4,
  jargon_violations: 0,
  repaired: true,
  initial: { tone_score: 5, cadence_score: 4, jargon_violations: 0 },
  final: { tone_score: 5, cadence_score: 4, jargon_violations: 0 },
};

const legacyFlatOnlyScore: VoiceScore = {
  tone_score: 8,
  cadence_score: 7,
  jargon_violations: 0,
};
// ─────────────────────────────────────────────────────────────────────────────

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

  it("renders badge when authored_passages_preserved is false", () => {
    const score: VoiceScore = { tone_score: 8, cadence_score: 7, jargon_violations: 0, authored_passages_preserved: false };
    render(<VoiceFidelityBadge voiceScore={score} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("shows authored passages message in detail panel when passages were rewritten", () => {
    const score: VoiceScore = { tone_score: 8, cadence_score: 7, jargon_violations: 0, authored_passages_preserved: false };
    render(<VoiceFidelityBadge voiceScore={score} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText(/authored passages: rewritten by ai, consider regenerating/i)).toBeInTheDocument();
  });

  it("renders null when authored_passages_preserved is true and other scores pass", () => {
    const score: VoiceScore = { tone_score: 8, cadence_score: 7, jargon_violations: 0, authored_passages_preserved: true };
    const { container } = render(<VoiceFidelityBadge voiceScore={score} />);
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

// ── Story 26.4: voice-tuned badge variant ─────────────────────────────────────
describe("VoiceFidelityBadge - Story 26.4 repair variants", () => {
  it("shows Voice-tuned badge when repaired is true and final score passes", () => {
    render(<VoiceFidelityBadge voiceScore={repairedPassingScore} />);
    expect(screen.getByText(/voice-tuned/i)).toBeInTheDocument();
  });

  it("Voice-tuned badge is not a button (informational only)", () => {
    render(<VoiceFidelityBadge voiceScore={repairedPassingScore} />);
    // Should be a div, not a button
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("Voice-tuned badge has tooltip text about automatic adjustment", () => {
    render(<VoiceFidelityBadge voiceScore={repairedPassingScore} />);
    const badge = screen.getByText(/voice-tuned/i).closest("[title]");
    expect(badge).toBeTruthy();
    expect(badge?.getAttribute("title")).toMatch(/automatically adjusted/i);
  });

  it("Voice-tuned badge renders Wand2 icon with aria-hidden", () => {
    const { container } = render(<VoiceFidelityBadge voiceScore={repairedPassingScore} />);
    // Lucide Wand2 renders as an svg; it should be aria-hidden
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
  });

  it("shows failing badge when repaired is true but final score still fails", () => {
    render(<VoiceFidelityBadge voiceScore={repairedStillFailingScore} />);
    // Should show the failure button, not the voice-tuned badge
    expect(screen.getByRole("button", { name: /voice match/i })).toBeInTheDocument();
    expect(screen.queryByText(/voice-tuned/i)).toBeNull();
  });

  it("renders null for legacy flat-only passing score (no repaired field)", () => {
    const { container } = render(<VoiceFidelityBadge voiceScore={legacyFlatOnlyScore} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders failure badge for legacy flat-only failing score", () => {
    const failingLegacy: VoiceScore = { tone_score: 5, cadence_score: 7, jargon_violations: 0 };
    render(<VoiceFidelityBadge voiceScore={failingLegacy} />);
    expect(screen.getByRole("button", { name: /voice match/i })).toBeInTheDocument();
  });
});
