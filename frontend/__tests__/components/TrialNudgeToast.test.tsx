import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useSubscription", () => ({
  useTrialDaysRemaining: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  subscriptionsApi: {
    createPortal: vi.fn(),
  },
}));

const { useTrialDaysRemaining } = await import("@/hooks/useSubscription");
const { subscriptionsApi } = await import("@/lib/api");

import { TrialNudgeToast } from "@/components/layout/TrialNudgeToast";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
});

describe("TrialNudgeToast", () => {
  it("shows 4-day copy when daysRemaining is 4", () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(4);
    render(<TrialNudgeToast />, { wrapper });

    expect(
      screen.getByText(/4 days left on your trial\. Subscribe to keep publishing\./),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Subscribe" })).toBeInTheDocument();
  });

  it("shows urgent copy when daysRemaining is 1", () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(1);
    render(<TrialNudgeToast />, { wrapper });

    expect(
      screen.getByText(/1 day left on your trial\. Subscribe now to avoid interruption\./),
    ).toBeInTheDocument();
  });

  it("shows expired copy when daysRemaining is 0", () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(0);
    render(<TrialNudgeToast />, { wrapper });

    expect(
      screen.getByText(/Your trial has ended\. Subscribe to keep publishing\./),
    ).toBeInTheDocument();
  });

  it("does not render when daysRemaining is 5", () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(5);
    const { container } = render(<TrialNudgeToast />, { wrapper });

    expect(container.firstChild).toBeNull();
  });

  it("does not render when daysRemaining is null (not trialing)", () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(null);
    const { container } = render(<TrialNudgeToast />, { wrapper });

    expect(container.firstChild).toBeNull();
  });

  it("does not render when trial_nudge_dismissed is set in sessionStorage", () => {
    sessionStorage.setItem("trial_nudge_dismissed", "1");
    vi.mocked(useTrialDaysRemaining).mockReturnValue(4);
    const { container } = render(<TrialNudgeToast />, { wrapper });

    expect(container.firstChild).toBeNull();
  });

  it("dismiss button sets sessionStorage and removes toast", () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(4);
    render(<TrialNudgeToast />, { wrapper });

    const dismissBtn = screen.getByRole("button", { name: "Dismiss trial notification" });
    fireEvent.click(dismissBtn);

    expect(sessionStorage.getItem("trial_nudge_dismissed")).toBe("1");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("subscribe button calls createPortal and navigates", async () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(4);
    vi.mocked(subscriptionsApi.createPortal).mockResolvedValue({
      portal_url: "https://billing.stripe.com/session/test",
    });

    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });

    render(<TrialNudgeToast />, { wrapper });

    const subscribeBtn = screen.getByRole("button", { name: "Subscribe" });
    fireEvent.click(subscribeBtn);

    await waitFor(() => {
      expect(subscriptionsApi.createPortal).toHaveBeenCalledOnce();
    });
    expect(window.location.href).toBe("https://billing.stripe.com/session/test");
  });

  it("shows error message when createPortal fails", async () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(4);
    vi.mocked(subscriptionsApi.createPortal).mockRejectedValue(new Error("Network error"));

    render(<TrialNudgeToast />, { wrapper });

    const subscribeBtn = screen.getByRole("button", { name: "Subscribe" });
    fireEvent.click(subscribeBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Could not open billing portal\. Please try again\./),
      ).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Subscribe" })).not.toBeInTheDocument();
  });

  it("does not navigate when dismissed while portal request is in flight", async () => {
    vi.mocked(useTrialDaysRemaining).mockReturnValue(4);

    let resolvePortal!: (value: { portal_url: string }) => void;
    vi.mocked(subscriptionsApi.createPortal).mockReturnValue(
      new Promise((res) => { resolvePortal = res; }),
    );

    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });

    render(<TrialNudgeToast />, { wrapper });

    fireEvent.click(screen.getByRole("button", { name: "Subscribe" }));
    fireEvent.click(screen.getByRole("button", { name: "Dismiss trial notification" }));

    resolvePortal({ portal_url: "https://billing.stripe.com/session/test" });

    await waitFor(() => expect(subscriptionsApi.createPortal).toHaveBeenCalledOnce());
    expect(window.location.href).toBe("");
  });
});
