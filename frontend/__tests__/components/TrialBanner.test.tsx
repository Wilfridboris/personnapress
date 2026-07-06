import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/hooks/useSubscription", () => ({
  useSubscriptionStatus: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  subscriptionsApi: {
    createPortal: vi.fn(),
  },
}));

const { useSubscriptionStatus } = await import("@/hooks/useSubscription");
const { subscriptionsApi } = await import("@/lib/api");

import { TrialBanner } from "@/components/layout/TrialBanner";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TrialBanner", () => {
  it("renders when status is trial_expired", () => {
    vi.mocked(useSubscriptionStatus).mockReturnValue("trial_expired");
    render(<TrialBanner />, { wrapper });

    expect(
      screen.getByText("Your trial has ended. Subscribe to continue publishing."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Subscribe" })).toBeInTheDocument();
  });

  it("does not render when status is trialing", () => {
    vi.mocked(useSubscriptionStatus).mockReturnValue("trialing");
    const { container } = render(<TrialBanner />, { wrapper });
    expect(container.firstChild).toBeNull();
  });

  it("does not render when status is active", () => {
    vi.mocked(useSubscriptionStatus).mockReturnValue("active");
    const { container } = render(<TrialBanner />, { wrapper });
    expect(container.firstChild).toBeNull();
  });

  it("does not render when status is null", () => {
    vi.mocked(useSubscriptionStatus).mockReturnValue(null);
    const { container } = render(<TrialBanner />, { wrapper });
    expect(container.firstChild).toBeNull();
  });

  it("subscribe button calls createPortal and navigates", async () => {
    vi.mocked(useSubscriptionStatus).mockReturnValue("trial_expired");
    vi.mocked(subscriptionsApi.createPortal).mockResolvedValue({
      portal_url: "https://billing.stripe.com/session/test",
    });

    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });

    render(<TrialBanner />, { wrapper });

    const subscribeBtn = screen.getByRole("button", { name: "Subscribe" });
    fireEvent.click(subscribeBtn);

    await waitFor(() => {
      expect(subscriptionsApi.createPortal).toHaveBeenCalledOnce();
    });
    expect(window.location.href).toBe("https://billing.stripe.com/session/test");
  });

  it("shows 'Opening...' while portal request is in flight", async () => {
    vi.mocked(useSubscriptionStatus).mockReturnValue("trial_expired");

    let resolve!: (v: { portal_url: string }) => void;
    vi.mocked(subscriptionsApi.createPortal).mockReturnValue(
      new Promise((res) => { resolve = res; }),
    );

    render(<TrialBanner />, { wrapper });
    fireEvent.click(screen.getByRole("button", { name: "Subscribe" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Opening..." })).toBeInTheDocument(),
    );

    resolve({ portal_url: "https://billing.stripe.com/session/test" });
  });

  it("has role=alert and aria-label for accessibility", () => {
    vi.mocked(useSubscriptionStatus).mockReturnValue("trial_expired");
    render(<TrialBanner />, { wrapper });

    const banner = screen.getByRole("alert");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveAttribute("aria-label", "Trial expired — upgrade required");
  });
});
