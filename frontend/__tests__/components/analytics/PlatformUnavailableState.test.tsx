import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PlatformUnavailableState } from "@/components/analytics/PlatformUnavailableState";

function openTooltip() {
  fireEvent.click(screen.getByRole("button", { name: /why is analytics unavailable/i }));
}

describe("PlatformUnavailableState — member reasons (Story 25.2)", () => {
  it("shows member_metrics_disabled copy and NO reconnect link", () => {
    render(<PlatformUnavailableState reason="member_metrics_disabled" />);
    openTooltip();
    expect(screen.getByText(/not enabled yet/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /reconnect linkedin/i })
    ).not.toBeInTheDocument();
  });

  it("shows member_scope_missing copy WITH a reconnect link to /connections", () => {
    render(<PlatformUnavailableState reason="member_scope_missing" />);
    openTooltip();
    expect(screen.getByText(/need an updated permission/i)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /reconnect linkedin/i });
    expect(link).toHaveAttribute("href", "/connections");
  });

  it("shows consent_revoked copy WITH a reconnect link", () => {
    render(<PlatformUnavailableState reason="consent_revoked" />);
    openTooltip();
    expect(screen.getByText(/access was revoked/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /reconnect linkedin/i })
    ).toHaveAttribute("href", "/connections");
  });

  it("token_expired (org or member) surfaces a reconnect link", () => {
    render(<PlatformUnavailableState reason="token_expired" />);
    openTooltip();
    expect(
      screen.getByRole("link", { name: /reconnect linkedin/i })
    ).toBeInTheDocument();
  });

  it("no_data_yet does not surface a reconnect link", () => {
    render(<PlatformUnavailableState reason="no_data_yet" />);
    openTooltip();
    expect(screen.getByText(/not yet available/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /reconnect linkedin/i })
    ).not.toBeInTheDocument();
  });

  it("toggles the tooltip via the info button (aria-expanded)", () => {
    render(<PlatformUnavailableState reason="member_scope_missing" />);
    const btn = screen.getByRole("button", { name: /why is analytics unavailable/i });
    expect(btn).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-expanded", "true");
  });

  it("renders nothing extra when reason has no copy", () => {
    render(<PlatformUnavailableState reason={null} />);
    // Generic label always present; no info button when there is no reason copy
    expect(screen.getByText(/analytics not available/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /why is analytics unavailable/i })
    ).not.toBeInTheDocument();
  });
});
