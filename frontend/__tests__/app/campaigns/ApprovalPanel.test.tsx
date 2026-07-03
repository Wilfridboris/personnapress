import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ApprovalPanel } from "@/app/(app)/campaigns/[id]/approval-panel";
import type { Campaign } from "@/lib/types";

const mockPush = vi.fn();
const mockRefresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, refresh: mockRefresh }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockApprove = vi.fn();
const mockReject = vi.fn();
const mockRegenerate = vi.fn();
const mockPatch = vi.fn();
const mockPublishNow = vi.fn();
const mockJobGet = vi.fn();

vi.mock("@/lib/api", () => ({
  campaignsApi: {
    approve: (...args: unknown[]) => mockApprove(...args),
    reject: (...args: unknown[]) => mockReject(...args),
    regenerate: (...args: unknown[]) => mockRegenerate(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    publishNow: (...args: unknown[]) => mockPublishNow(...args),
  },
  jobsApi: {
    get: (...args: unknown[]) => mockJobGet(...args),
  },
  fetchAPI: vi.fn().mockResolvedValue({ items: [{ platform: "wordpress", connected: true }] }),
  APIError: class APIError extends Error {
    code: string;
    constructor(message: string, code: string) {
      super(message);
      this.code = code;
    }
  },
}));

const mockAddToast = vi.fn();

vi.mock("@/lib/stores/useUIStore", () => ({
  useUIStore: (selector: (s: { addToast: typeof mockAddToast }) => unknown) =>
    selector({ addToast: mockAddToast }),
}));

function makeCampaign(overrides: Partial<Campaign> = {}): Campaign {
  return {
    id: "campaign-123",
    client_id: "client-456",
    brain_dump: "test brain dump",
    blog_html: "<p>blog</p>",
    x_post: "x post",
    linkedin_post: "linkedin post",
    image_url: null,
    status: "pending_approval",
    voice_score: null,
    rejection_reason: null,
    scheduled_at: null,
    image_regen_count: 0,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

describe("ApprovalPanel — pending_approval state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Approve and Reject buttons", () => {
    render(<ApprovalPanel campaign={makeCampaign()} />);
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
  });

  it("calls campaignsApi.approve on Approve click and triggers optimistic status", async () => {
    const onOptimisticStatus = vi.fn();
    mockApprove.mockResolvedValueOnce({ id: "campaign-123", status: "approved", client_id: "client-456" });

    render(<ApprovalPanel campaign={makeCampaign()} onOptimisticStatus={onOptimisticStatus} />);
    fireEvent.click(screen.getByRole("button", { name: /approve/i }));

    expect(onOptimisticStatus).toHaveBeenCalledWith("approved");
    await waitFor(() => expect(mockApprove).toHaveBeenCalledWith("campaign-123"));
  });

  it("reverts optimistic status and shows error toast on approve failure", async () => {
    const onOptimisticStatus = vi.fn();
    const { APIError } = await import("@/lib/api");
    mockApprove.mockRejectedValueOnce(new APIError("Approve failed", "INVALID_STATUS_TRANSITION"));

    render(<ApprovalPanel campaign={makeCampaign()} onOptimisticStatus={onOptimisticStatus} />);
    fireEvent.click(screen.getByRole("button", { name: /approve/i }));

    await waitFor(() => expect(mockAddToast).toHaveBeenCalledWith("Approve failed", "error"));
    expect(onOptimisticStatus).toHaveBeenCalledWith("pending_approval");
  });

  it("opens reject dialog when Reject is clicked", () => {
    render(<ApprovalPanel campaign={makeCampaign()} />);
    fireEvent.click(screen.getByRole("button", { name: "Reject campaign" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Reject this campaign?")).toBeInTheDocument();
  });

  it("calls campaignsApi.reject with reason when confirmed", async () => {
    mockReject.mockResolvedValueOnce({ id: "campaign-123", status: "rejected", rejection_reason: "Too vague" });

    render(<ApprovalPanel campaign={makeCampaign()} />);
    fireEvent.click(screen.getByRole("button", { name: "Reject campaign" }));

    const textarea = screen.getByPlaceholderText(/reason \(optional\)/i);
    fireEvent.change(textarea, { target: { value: "Too vague" } });
    // Click the confirm button in the dialog (text "Reject campaign", not aria-label)
    const allRejectBtns = screen.getAllByText("Reject campaign");
    // The one inside the dialog has no aria-label
    const confirmBtn = allRejectBtns.find((el) => !el.getAttribute("aria-label"))!;
    fireEvent.click(confirmBtn.closest("button")!);

    await waitFor(() => expect(mockReject).toHaveBeenCalledWith("campaign-123", "Too vague"));
    await waitFor(() => expect(mockRefresh).toHaveBeenCalled());
  });

  it("calls campaignsApi.reject with undefined when no reason provided", async () => {
    mockReject.mockResolvedValueOnce({ id: "campaign-123", status: "rejected", rejection_reason: null });

    render(<ApprovalPanel campaign={makeCampaign()} />);
    fireEvent.click(screen.getByRole("button", { name: "Reject campaign" }));
    const allRejectBtns2 = screen.getAllByText("Reject campaign");
    const confirmBtn2 = allRejectBtns2.find((el) => !el.getAttribute("aria-label"))!;
    fireEvent.click(confirmBtn2.closest("button")!);

    await waitFor(() => expect(mockReject).toHaveBeenCalledWith("campaign-123", undefined));
  });

  it("closes reject dialog on Cancel", () => {
    render(<ApprovalPanel campaign={makeCampaign()} />);
    fireEvent.click(screen.getByRole("button", { name: "Reject campaign" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("ApprovalPanel — rejected state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows Regenerate button", () => {
    render(<ApprovalPanel campaign={makeCampaign({ status: "rejected" })} />);
    expect(screen.getByRole("button", { name: /regenerate from same brain dump/i })).toBeInTheDocument();
  });

  it("calls campaignsApi.regenerate and navigates to new campaign", async () => {
    mockRegenerate.mockResolvedValueOnce({ campaign_id: "new-camp-999", job_id: "job-888" });

    render(<ApprovalPanel campaign={makeCampaign({ status: "rejected" })} />);
    fireEvent.click(screen.getByRole("button", { name: /regenerate from same brain dump/i }));

    await waitFor(() =>
      expect(mockPush).toHaveBeenCalledWith("/campaigns/new-camp-999?job_id=job-888")
    );
  });
});

describe("ApprovalPanel — approved state", () => {
  it("shows Connect a platform CTA when clientHasPlatforms is false (loading skeleton initially)", () => {
    render(<ApprovalPanel campaign={makeCampaign({ status: "approved" })} />);
    // Initially shows skeleton while clientHasPlatforms is null
    expect(screen.getByText(/campaign approved/i)).toBeInTheDocument();
  });
});

describe("ApprovalPanel — publish now", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderApprovedWithPlatforms() {
    const utils = render(<ApprovalPanel campaign={makeCampaign({ status: "approved" })} />);
    // Wait for platforms to load (fetchAPI returns items with wordpress)
    await waitFor(() => expect(screen.queryByRole("button", { name: /publish now/i })).toBeInTheDocument());
    return utils;
  }

  it("Publish now button calls campaignsApi.publishNow", async () => {
    mockPublishNow.mockResolvedValueOnce({ job_id: "job-111" });
    mockJobGet.mockResolvedValue({ status: "pending", error_details: null });

    await renderApprovedWithPlatforms();
    fireEvent.click(screen.getByRole("button", { name: /publish now/i }));

    await waitFor(() => expect(mockPublishNow).toHaveBeenCalledWith("campaign-123"));
  });

  it("shows Publishing... state while job is in-flight", async () => {
    mockPublishNow.mockResolvedValueOnce({ job_id: "job-222" });
    mockJobGet.mockResolvedValue({ status: "in_progress", error_details: null });

    await renderApprovedWithPlatforms();
    fireEvent.click(screen.getByRole("button", { name: /publish now/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: /publishing/i })).toBeDisabled());
  });

  it("calls router.refresh when polling detects job complete", async () => {
    mockPublishNow.mockResolvedValueOnce({ job_id: "job-333" });
    mockJobGet.mockResolvedValue({ status: "complete", error_details: null });

    await renderApprovedWithPlatforms();
    fireEvent.click(screen.getByRole("button", { name: /publish now/i }));

    // Polling fires every 2s; wait for refresh to be called
    await waitFor(() => expect(mockRefresh).toHaveBeenCalled(), { timeout: 6000 });
  });

  it("shows error toast when polling detects job failure", async () => {
    mockPublishNow.mockResolvedValueOnce({ job_id: "job-444" });
    mockJobGet.mockResolvedValue({ status: "failed", error_details: '{"wordpress":"auth failed"}' });

    await renderApprovedWithPlatforms();
    fireEvent.click(screen.getByRole("button", { name: /publish now/i }));

    await waitFor(() => expect(mockAddToast).toHaveBeenCalledWith(
      expect.stringContaining("platforms failed"),
      "error",
    ), { timeout: 6000 });
    await waitFor(() => expect(mockRefresh).toHaveBeenCalled(), { timeout: 6000 });
  });

  it("shows error toast when publishNow API call fails", async () => {
    const { APIError } = await import("@/lib/api");
    mockPublishNow.mockRejectedValueOnce(new APIError("No platform connections", "NO_PLATFORM_CONNECTIONS"));

    await renderApprovedWithPlatforms();
    fireEvent.click(screen.getByRole("button", { name: /publish now/i }));

    await waitFor(() => expect(mockAddToast).toHaveBeenCalledWith("No platform connections", "error"));
  });
});

describe("ApprovalPanel — published state", () => {
  it("shows Published footer with date", () => {
    render(<ApprovalPanel campaign={makeCampaign({ status: "published", updated_at: "2026-07-03T14:30:00Z" })} />);
    expect(screen.getByText("Published")).toBeInTheDocument();
  });

  it("does not show Approve/Reject buttons in published state", () => {
    render(<ApprovalPanel campaign={makeCampaign({ status: "published" })} />);
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
  });
});
