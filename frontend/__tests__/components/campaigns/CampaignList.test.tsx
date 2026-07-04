import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock zustand store
vi.mock("@/lib/stores/useClientStore", () => ({
  useClientStore: (selector: (s: { activeClientId: string | null }) => unknown) =>
    selector({ activeClientId: "client-abc" }),
}));

// Mock hooks
vi.mock("@/hooks/useCampaigns", () => ({
  useCampaigns: vi.fn(),
}));
vi.mock("@/hooks/usePlatformConnections", () => ({
  usePlatformConnections: vi.fn(),
}));

const { useCampaigns } = await import("@/hooks/useCampaigns");
const { usePlatformConnections } = await import("@/hooks/usePlatformConnections");

import { CampaignList } from "@/components/campaigns/CampaignList";

const noConnections = { data: { items: [] }, isLoading: false };

function makeCampaign(overrides: Partial<{
  id: string;
  status: string;
  blog_html: string | null;
  created_at: string;
  updated_at: string;
}> = {}) {
  return {
    id: "camp-1",
    client_id: "client-abc",
    brain_dump: "test",
    blog_html: "<h1>My Campaign Title</h1><p>Body</p>",
    x_post: null,
    linkedin_post: null,
    image_url: null,
    status: "pending_approval",
    voice_score: null,
    rejection_reason: null,
    scheduled_at: null,
    image_regen_count: 0,
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-01T10:00:00Z",
    ...overrides,
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(usePlatformConnections).mockReturnValue(noConnections as ReturnType<typeof usePlatformConnections>);
});

describe("CampaignList", () => {
  it("renders skeleton while loading", () => {
    vi.mocked(useCampaigns).mockReturnValue({ data: undefined, isLoading: true } as ReturnType<typeof useCampaigns>);
    const { container } = render(<CampaignList />, { wrapper });
    expect(container.querySelector('[aria-label="Loading campaigns"]')).toBeTruthy();
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("renders campaign rows with title, status badge, date", () => {
    const campaign = makeCampaign();
    vi.mocked(useCampaigns).mockReturnValue({
      data: { items: [campaign], total: 1 },
      isLoading: false,
    } as ReturnType<typeof useCampaigns>);

    render(<CampaignList />, { wrapper });

    expect(screen.getByText("My Campaign Title")).toBeInTheDocument();
    expect(screen.getByText("PENDING APPROVAL")).toBeInTheDocument();
    expect(screen.getByText("Jun 1, 2026")).toBeInTheDocument();
  });

  it("shows empty state when no campaigns", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    } as ReturnType<typeof useCampaigns>);

    render(<CampaignList />, { wrapper });

    expect(screen.getByText("No campaigns yet.")).toBeInTheDocument();
    expect(screen.getByText(/Start with a Brain Dump/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /New Campaign/i })).toBeInTheDocument();
  });

  it("shows Retry link for failed campaigns", () => {
    const campaign = makeCampaign({ id: "camp-fail", status: "failed" });
    vi.mocked(useCampaigns).mockReturnValue({
      data: { items: [campaign], total: 1 },
      isLoading: false,
    } as ReturnType<typeof useCampaigns>);

    render(<CampaignList />, { wrapper });

    const retryLink = screen.getByRole("link", { name: /Retry/i });
    expect(retryLink).toBeInTheDocument();
    expect(retryLink).toHaveAttribute("href", "/campaigns/camp-fail");
  });

  it("filter tab click updates URL", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    } as ReturnType<typeof useCampaigns>);

    render(<CampaignList />, { wrapper });

    fireEvent.click(screen.getByRole("tab", { name: "Published" }));
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("status=published"));
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("page=1"));
  });

  it("shows pagination controls when more than 20 campaigns", () => {
    const campaigns = Array.from({ length: 20 }, (_, i) =>
      makeCampaign({ id: `camp-${i}`, blog_html: `<h1>Campaign ${i}</h1>` })
    );
    vi.mocked(useCampaigns).mockReturnValue({
      data: { items: campaigns, total: 45 },
      isLoading: false,
    } as ReturnType<typeof useCampaigns>);

    render(<CampaignList />, { wrapper });

    expect(screen.getByText(/Page 1 of 3/)).toBeInTheDocument();
    expect(screen.getByText("← Previous")).toBeDisabled();
    expect(screen.getByText("Next →")).not.toBeDisabled();
  });
});
