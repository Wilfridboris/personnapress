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
  total_likes: 300,
  total_comments: 80,
  total_shares: 40,
  engagement_rate: 0.0375,
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
  latest_likes: 150,
  latest_comments: 30,
  latest_shares: 20,
  engagement_rate: 0.04,
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

    expect(screen.getByText("Engagement Rate")).toBeInTheDocument();
    expect(screen.getByText("3.8%")).toBeInTheDocument();
  });

  it("renders engagement rate card with correct percentage", () => {
    render(<AnalyticsDashboard />, { wrapper: Wrapper });
    expect(screen.getByText("Engagement Rate")).toBeInTheDocument();
    // 0.0375 * 100 = 3.750... -> "3.8%"
    expect(screen.getAllByText("3.8%").length).toBeGreaterThan(0);
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
      latest_likes: null,
      latest_comments: null,
      latest_shares: null,
      engagement_rate: null,
      series: [],
      unavailable_reason: "page_under_100_likes",
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [unavailablePost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(screen.getByText("Analytics not available for this platform.")).toBeInTheDocument();
  });

  it("shows tooltip content for page_under_100_likes unavailability", () => {
    const unavailablePost = {
      ...basePost,
      platform: "facebook_page",
      latest_impressions: null,
      latest_engagements: null,
      latest_likes: null,
      latest_comments: null,
      latest_shares: null,
      engagement_rate: null,
      series: [],
      unavailable_reason: "page_under_100_likes",
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
      latest_likes: null,
      latest_comments: null,
      latest_shares: null,
      engagement_rate: null,
      series: [],
      unavailable_reason: "page_under_100_likes",
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

  // ---------------------------------------------------------------------------
  // Story 24.4 — breakdown line in post table (AC #7, #8, #10, #13)
  // ---------------------------------------------------------------------------

  it("renders engagement breakdown line with correct Instagram labels", () => {
    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    // Instagram post: should show "150 likes", "30 comments", "20 shares"
    expect(screen.getByLabelText("150 likes")).toBeInTheDocument();
    expect(screen.getByLabelText("30 comments")).toBeInTheDocument();
    expect(screen.getByLabelText("20 shares")).toBeInTheDocument();
  });

  it("renders Threads-specific nouns (Replies, Reposts) in breakdown line", () => {
    const threadsPost = {
      ...basePost,
      published_post_id: "pp-threads",
      platform: "threads",
      campaign_title: "Threads Post",
      latest_likes: 10,
      latest_comments: 5,
      latest_shares: 3,
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [threadsPost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(screen.getByLabelText("10 likes")).toBeInTheDocument();
    expect(screen.getByLabelText("5 replies")).toBeInTheDocument();
    expect(screen.getByLabelText("3 reposts")).toBeInTheDocument();
    // No "comments" or "shares" nouns for Threads
    expect(screen.queryByLabelText(/5 comments/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/3 shares/i)).not.toBeInTheDocument();
  });

  it("renders em-dash placeholder for NULL component values", () => {
    const postWithNullComponents = {
      ...basePost,
      latest_likes: null,
      latest_comments: null,
      latest_shares: null,
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [postWithNullComponents] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    // All three should show em-dash for NULL values
    const likesDashes = screen.getAllByLabelText(/— likes/);
    expect(likesDashes.length).toBeGreaterThan(0);
  });

  it("hides breakdown line on unavailable rows (AC #10)", () => {
    // Reset summary to have no breakdown data so summary card doesn't interfere
    mockUseAnalyticsSummary.mockReturnValue({
      data: {
        ...baseSummary,
        total_likes: null,
        total_comments: null,
        total_shares: null,
        engagement_rate: null,
      },
      isLoading: false,
    });

    const unavailablePost = {
      ...basePost,
      platform: "facebook_page",
      latest_impressions: null,
      latest_engagements: null,
      latest_likes: null,
      latest_comments: null,
      latest_shares: null,
      engagement_rate: null,
      series: [],
      unavailable_reason: "page_under_100_likes",
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [unavailablePost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    // The post table section should have no breakdown icons (scoped to the table section)
    const tableSection = screen.getByRole("region", { name: "Post performance metrics" });
    expect(within(tableSection).queryByLabelText(/likes/)).not.toBeInTheDocument();
    expect(within(tableSection).queryByLabelText(/comments/)).not.toBeInTheDocument();
    expect(within(tableSection).queryByLabelText(/shares/)).not.toBeInTheDocument();

    // But the unavailable state IS shown
    expect(screen.getByText("Analytics not available for this platform.")).toBeInTheDocument();
  });

  it("renders Facebook-specific nouns (Comments, Shares) in breakdown line (AC #8, #13)", () => {
    const fbPost = {
      ...basePost,
      published_post_id: "pp-facebook",
      platform: "facebook_page",
      campaign_title: "Facebook Post",
      latest_likes: 25,
      latest_comments: 8,
      latest_shares: 3,
    };

    mockUsePostMetrics.mockReturnValue({
      data: { ...baseMetrics, items: [fbPost] },
      isLoading: false,
    });

    render(<AnalyticsDashboard />, { wrapper: Wrapper });

    expect(screen.getByLabelText("25 likes")).toBeInTheDocument();
    expect(screen.getByLabelText("8 comments")).toBeInTheDocument();
    expect(screen.getByLabelText("3 shares")).toBeInTheDocument();
    // Facebook does NOT use Threads nouns
    expect(screen.queryByLabelText(/8 replies/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/3 reposts/i)).not.toBeInTheDocument();
  });
});
