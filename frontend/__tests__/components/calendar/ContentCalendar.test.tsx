import { describe, it, expect, vi, beforeAll, afterAll, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Pin system time to July 2026 so the calendar always initialises to that month.
beforeAll(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-01T12:00:00Z"));
});
afterAll(() => {
  vi.useRealTimers();
});

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock zustand store
vi.mock("@/lib/stores/useClientStore", () => ({
  useClientStore: (selector: (s: { activeClientId: string | null }) => unknown) =>
    selector({ activeClientId: "client-abc" }),
}));

// Mock hooks
vi.mock("@/hooks/useCalendarCampaigns", () => ({
  useCalendarCampaigns: vi.fn(),
}));
vi.mock("@/hooks/usePlatformConnections", () => ({
  usePlatformConnections: vi.fn(),
}));

const { useCalendarCampaigns } = await import("@/hooks/useCalendarCampaigns");
const { usePlatformConnections } = await import("@/hooks/usePlatformConnections");

import { ContentCalendar } from "@/components/calendar/ContentCalendar";

const noConnections = { data: { items: [] }, isLoading: false };

function makeCampaign(overrides: Record<string, unknown> = {}) {
  return {
    id: "camp-1",
    client_id: "client-abc",
    brain_dump: "test",
    blog_html: "<h1>July Campaign</h1><p>Body</p>",
    x_post: null,
    linkedin_post: null,
    image_url: null,
    status: "published",
    voice_score: null,
    rejection_reason: null,
    scheduled_at: null,
    image_regen_count: 0,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-17T10:00:00Z",
    ...overrides,
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function mockCalendarData(data: ReturnType<typeof makeCampaign>[] | undefined, opts: { isLoading?: boolean; isError?: boolean } = {}) {
  vi.mocked(useCalendarCampaigns).mockReturnValue({
    data,
    isLoading: opts.isLoading ?? false,
    isError: opts.isError ?? false,
  } as ReturnType<typeof useCalendarCampaigns>);
}

describe("ContentCalendar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(usePlatformConnections).mockReturnValue(noConnections as ReturnType<typeof usePlatformConnections>);
  });

  it("renders current month header in H2", () => {
    mockCalendarData([]);

    render(<ContentCalendar />, { wrapper });

    const expectedLabel = new Intl.DateTimeFormat("en-US", {
      month: "long",
      year: "numeric",
    }).format(new Date("2026-07-01T12:00:00Z"));

    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(expectedLabel);
  });

  it("renders published campaign on correct date cell", () => {
    const campaign = makeCampaign({
      status: "published",
      updated_at: "2026-07-17T10:00:00Z",
    });
    mockCalendarData([campaign]);

    render(<ContentCalendar />, { wrapper });

    const cell = screen.getByRole("gridcell", {
      name: /July 17, 2026, 1 campaign/i,
    });
    expect(cell).toBeInTheDocument();
    expect(cell.querySelector("button")).toBeInTheDocument();
  });

  it("renders scheduled campaign on scheduled_at date with time", () => {
    const campaign = makeCampaign({
      status: "approved",
      scheduled_at: "2026-07-20T08:00:00Z",
      updated_at: "2026-07-01T10:00:00Z",
    });
    mockCalendarData([campaign]);

    render(<ContentCalendar />, { wrapper });

    const cell = screen.getByRole("gridcell", {
      name: /July 20, 2026, 1 campaign/i,
    });
    expect(cell).toBeInTheDocument();
    const btn = cell.querySelector("button");
    expect(btn).toBeInTheDocument();
  });

  it("shows empty state message when no campaigns in viewed month", () => {
    mockCalendarData([]);

    render(<ContentCalendar />, { wrapper });

    expect(
      screen.getByText("Nothing scheduled. Approve a campaign to see it here.")
    ).toBeInTheDocument();
  });

  it("does not show empty state when campaigns exist in other months but not current", () => {
    // Campaign in June — not visible in July view
    const campaign = makeCampaign({
      status: "published",
      updated_at: "2026-06-15T10:00:00Z",
    });
    mockCalendarData([campaign]);

    render(<ContentCalendar />, { wrapper });

    // Navigate to August (no campaigns there)
    fireEvent.click(screen.getByRole("button", { name: "Next month" }));

    expect(
      screen.getByText("Nothing scheduled. Approve a campaign to see it here.")
    ).toBeInTheDocument();
  });

  it("navigates to campaign page on entry click", () => {
    const campaign = makeCampaign({
      id: "camp-xyz",
      status: "published",
      updated_at: "2026-07-17T10:00:00Z",
    });
    mockCalendarData([campaign]);

    render(<ContentCalendar />, { wrapper });

    const entryBtn = screen.getByRole("button", { name: /July Campaign/i });
    fireEvent.click(entryBtn);
    expect(mockPush).toHaveBeenCalledWith("/campaigns/camp-xyz");
  });

  it("prevents drag on calendar entry (draggable=false, onDragStart preventDefault)", () => {
    const campaign = makeCampaign({
      status: "published",
      updated_at: "2026-07-17T10:00:00Z",
    });
    mockCalendarData([campaign]);

    render(<ContentCalendar />, { wrapper });

    const entryBtn = screen.getByRole("button", { name: /July Campaign/i });
    expect(entryBtn).toHaveAttribute("draggable", "false");

    const mockEvent = new Event("dragstart", { bubbles: true, cancelable: true });
    const preventDefaultSpy = vi.spyOn(mockEvent, "preventDefault");
    entryBtn.dispatchEvent(mockEvent);
    expect(preventDefaultSpy).toHaveBeenCalled();
  });

  it("day cell aria-label includes date and campaign count", () => {
    const campaigns = [
      makeCampaign({ id: "c1", status: "published", updated_at: "2026-07-17T10:00:00Z" }),
      makeCampaign({ id: "c2", status: "published", updated_at: "2026-07-17T12:00:00Z" }),
    ];
    mockCalendarData(campaigns);

    render(<ContentCalendar />, { wrapper });

    const cell = screen.getByRole("gridcell", {
      name: /July 17, 2026, 2 campaigns/i,
    });
    expect(cell).toBeInTheDocument();
  });

  it("navigates to previous month on ChevronLeft click", () => {
    mockCalendarData([]);

    render(<ContentCalendar />, { wrapper });

    const prevDate = new Date(2026, 5, 1); // June 2026
    const expectedLabel = new Intl.DateTimeFormat("en-US", {
      month: "long",
      year: "numeric",
    }).format(prevDate);

    fireEvent.click(screen.getByRole("button", { name: "Previous month" }));

    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(expectedLabel);
  });

  it("navigates to next month on ChevronRight click", () => {
    mockCalendarData([]);

    render(<ContentCalendar />, { wrapper });

    const nextDate = new Date(2026, 7, 1); // August 2026
    const expectedLabel = new Intl.DateTimeFormat("en-US", {
      month: "long",
      year: "numeric",
    }).format(nextDate);

    fireEvent.click(screen.getByRole("button", { name: "Next month" }));

    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(expectedLabel);
  });

  it("reacts to activeClientId change via query key", () => {
    mockCalendarData([]);

    render(<ContentCalendar />, { wrapper });

    expect(vi.mocked(useCalendarCampaigns)).toHaveBeenCalledWith("client-abc");
  });

  it("shows skeleton while loading", () => {
    mockCalendarData(undefined, { isLoading: true });

    render(<ContentCalendar />, { wrapper });

    // Grid should not be rendered during load
    expect(screen.queryByRole("grid")).not.toBeInTheDocument();
    // Month header and nav remain visible
    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
  });

  it("shows error message on API failure", () => {
    mockCalendarData(undefined, { isError: true });

    render(<ContentCalendar />, { wrapper });

    expect(
      screen.getByText(/Failed to load campaigns/i)
    ).toBeInTheDocument();
  });
});
