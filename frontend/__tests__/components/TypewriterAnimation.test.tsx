import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { TypewriterAnimation } from "@/components/campaigns/TypewriterAnimation";

const MESSAGES = ["Hello world!", "Drafting blog post...", "Done."];

describe("TypewriterAnimation", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Default: prefers-reduced-motion = false
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders the aria-live status region with the current message", () => {
    render(
      <TypewriterAnimation
        statusMessages={MESSAGES}
        currentMessageIndex={0}
              />
    );
    const liveRegion = screen.getByRole("status");
    expect(liveRegion).toHaveTextContent(MESSAGES[0]);
  });

  it("updates aria-live region when message index changes", () => {
    const { rerender } = render(
      <TypewriterAnimation
        statusMessages={MESSAGES}
        currentMessageIndex={0}
              />
    );
    expect(screen.getByRole("status")).toHaveTextContent(MESSAGES[0]);

    rerender(
      <TypewriterAnimation
        statusMessages={MESSAGES}
        currentMessageIndex={1}
              />
    );
    expect(screen.getByRole("status")).toHaveTextContent(MESSAGES[1]);
  });

  it("shows characters appearing over time (typewriter effect)", async () => {
    render(
      <TypewriterAnimation
        statusMessages={MESSAGES}
        currentMessageIndex={0}
              />
    );

    // Initially empty display
    const liveRegion = screen.getByRole("status");
    expect(liveRegion).toHaveTextContent(MESSAGES[0]); // aria-live always shows full msg

    // After 35ms x chars, some chars should appear in the visual span
    await act(async () => {
      vi.advanceTimersByTime(35 * 5); // 5 characters revealed
    });
    // The animated span (aria-hidden) should have some content
    const animatedSpans = document.querySelectorAll('[aria-hidden="true"]');
    // At least one char should be visible
    expect(animatedSpans.length).toBeGreaterThan(0);
  });

  it("shows static label when prefers-reduced-motion is enabled", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true, // reduced motion ON
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    render(
      <TypewriterAnimation
        statusMessages={MESSAGES}
        currentMessageIndex={0}
              />
    );

    // Should show static "Generating..." text, not the character reveal
    expect(screen.getByText("Generating...")).toBeInTheDocument();
    // The aria-hidden animated span should NOT be present
    expect(document.querySelector('[aria-hidden="true"]')).toBeNull();
  });

  it("aria-live region is present (screen-reader announcements)", () => {
    render(
      <TypewriterAnimation
        statusMessages={MESSAGES}
        currentMessageIndex={2}
              />
    );
    const liveRegion = screen.getByRole("status");
    expect(liveRegion).toHaveAttribute("aria-live", "polite");
    expect(liveRegion).toHaveTextContent(MESSAGES[2]);
  });
});
