import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock next/navigation (required by some layout imports)
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/analytics",
}));

// Mock zustand client store
const mockClientId = "client-abc";
vi.mock("@/lib/stores/useClientStore", () => ({
  useClientStore: (selector: (s: { activeClientId: string | null }) => unknown) =>
    selector({ activeClientId: mockClientId }),
}));

// Mock the hooks
vi.mock("@/hooks/usePostMetrics", () => ({
  useAnalyticsSummary: vi.fn(),
  usePostMetrics: vi.fn(),
}));

import { useAnalyticsSummary, usePostMetrics } from "@/hooks/usePostMetrics";
import { AnalyticsDashboard } from "@/app/(app)/analytics/AnalyticsDashboard";

const mockUseAnalyticsSummary = useAnalyticsSummary as ReturnType<typeof vi.fn>;
const mockUsePostMetrics = usePostMetrics as ReturnType<typeof vi.fn>;

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

const baseSummary = {
  client_id: mockClientId,
  total_impressions: 12_000,
  total_engagements: 450,
  posts_tracked: 3,
  best_post: null,
  freshest_captured_at: new Date(Date.now() - 3_600_000).toISOString(), // 1h ago
};

const basePost = {
  published_post_id: "pp-1",
  platform: "instagram",
  campaign_title: "Test Campaign",
  campaign_excerpt: null,
  latest_impressions: 5_000,
  latest_engagements: 200,
  permalink: "https://instagram.com/p/abc",
  captured_at: new Date().toISOString(),
  series: [
    { captured_at: new Date(Date.now() - 86_400_000).toISOString(), impressions: 4_500, engagements: 180 },
    { captured_at: new Date().toISOString(), impressions: 5_000, engagements: 200 },
  ],
  unavailable_reason: null,
};

const baseMetrics = {
  client_id: mockClientId,
  items: [basePost],
  freshest_captured_at: basePost.captured_at,
};

describe("AnalyticsDashboard", () => {
  beforeEach(() => {
    mockUseAnalyticsSummary.mockReturnValue({ data: baseSummary, isLoading: false });
    mockUsePostMetrics.mockReturnValue({ data: baseMetrics, isLoading: false });
  });

  it("renders summary cards with correct values", () => {
    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(screen.getByText("Total Impressions")).toBeInTheDocument();
    expect(screen.getByText("12K")).toBeInTheDocument();

    expect(screen.getByText("Total Engagements")).toBeInTheDocument();
    expect(screen.getByText("450")).toBeInTheDocument();

    expect(screen.getByText("Posts Tracked")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders per-post table rows", () => {
    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(screen.getByText("Test Campaign")).toBeInTheDocument();
    expect(screen.getByText("5K")).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
  });

  it("renders freshness indicator", () => {
    render(<AnalyticsDashboard />, { wrapper: Wrapper });
    expect(screen.getByText(/Updated.*ago/)).toBeInTheDocument();
  });

  it("shows loading skeletons while data is loading", () => {
    mockUseAnalyticsSummary.mockReturnValue({ data: undefined, isLoading: true });
    mockUsePostMetrics.mockReturnValue({ data: undefined, isLoading: true });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(screen.getByLabelText("Loading analytics summary")).toBeInTheDocument();
    expect(screen.getByLabelText("Loading post metrics")).toBeInTheDocument();
  });

  it("shows empty state when no posts tracked", () => {
    mockUseAnalyticsSummary.mockReturnValue({
      data: { ...baseSummary, posts_tracked: 0 },
      isLoading: false,
    });
    mockUsePostMetrics.mockReturnValue({
      data: { client_id: mockClientId, items: [], freshest_captured_at: null },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(
      screen.getByText(/No analytics yet.*Publish a post/i)
    ).toBeInTheDocument();
  });

  it("shows unavailable state for platform with no metrics", () => {
    const unavailablePost = {
      ...basePost,
      platform: "facebook_page",
      latest_impressions: null,
      latest_engagements: null,
      series: [],
      unavailable_reason: "facebook_under_100_likes",
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [unavailablePost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(screen.getByText("Analytics not available for this platform.")).toBeInTheDocument();
  });

  it("shows tooltip content for facebook_under_100_likes unavailability", () => {
    const unavailablePost = {
      ...basePost,
      platform: "facebook_page",
      latest_impressions: null,
      latest_engagements: null,
      series: [],
      unavailable_reason: "facebook_under_100_likes",
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [unavailablePost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    const infoButton = screen.getByRole("button", { name: /why is analytics unavailable/i });
    fireEvent.click(infoButton);

    expect(screen.getByRole("tooltip")).toHaveTextContent(/100\+ likes/i);
  });

  it("tooltip is keyboard-dismissible via Escape", () => {
    const unavailablePost = {
      ...basePost,
      platform: "facebook_page",
      latest_impressions: null,
      latest_engagements: null,
      series: [],
      unavailable_reason: "facebook_under_100_likes",
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [unavailablePost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    const infoButton = screen.getByRole("button", { name: /why is analytics unavailable/i });
    fireEvent.click(infoButton);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("platform filter chips filter by platform", () => {
    const facebookPost = {
      ...basePost,
      published_post_id: "pp-2",
      platform: "facebook_page",
      campaign_title: "Facebook Campaign",
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [basePost, facebookPost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    // Both visible initially
    expect(screen.getByText("Test Campaign")).toBeInTheDocument();
    expect(screen.getByText("Facebook Campaign")).toBeInTheDocument();

    // Click Facebook filter
    fireEvent.click(screen.getByRole("button", { name: /Facebook/i }));

    expect(screen.queryByText("Test Campaign")).not.toBeInTheDocument();
    expect(screen.getByText("Facebook Campaign")).toBeInTheDocument();
  });

  it("table has proper <th scope> headers for accessibility", () => {
    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    const headers = screen.getAllByRole("columnheader");
    headers.forEach((th) => {
      expect(th).toHaveAttribute("scope", "col");
    });
  });

  it("platform icons are aria-hidden", () => {
    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    // Filter chip icons and table icons should be aria-hidden
    const svgIcons = document.querySelectorAll('svg[aria-hidden="true"]');
    expect(svgIcons.length).toBeGreaterThan(0);
  });
});
