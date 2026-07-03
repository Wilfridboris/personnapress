import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RetryPanel } from "@/components/publishing/RetryPanel";
import type { Campaign } from "@/lib/types";

const mockRefresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: mockRefresh }),
}));

const mockRetryPublish = vi.fn();
const mockJobGet = vi.fn();

vi.mock("@/lib/api", () => ({
  campaignsApi: {
    retryPublish: (...args: unknown[]) => mockRetryPublish(...args),
  },
  jobsApi: {
    get: (...args: unknown[]) => mockJobGet(...args),
  },
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
    brain_dump: "test",
    blog_html: "<p>blog</p>",
    x_post: "x post",
    linkedin_post: "linkedin post",
    image_url: null,
    status: "failed",
    voice_score: null,
    rejection_reason: null,
    scheduled_at: null,
    image_regen_count: 0,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

describe("RetryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders platform list with error messages from error_details", () => {
    const errorDetails = {
      wordpress: "WordPress returned 401 — check your Application Password",
      x: "success",
    };
    render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={errorDetails}
        attemptCount={1}
        onRetrySuccess={vi.fn()}
      />
    );

    expect(screen.getByText("wordpress")).toBeInTheDocument();
    expect(screen.getByText("WordPress returned 401 — check your Application Password")).toBeInTheDocument();
    expect(screen.getByText("x")).toBeInTheDocument();
    expect(screen.getByText("Published")).toBeInTheDocument();
  });

  it("shows Retry button for failed platform but not for successful one", () => {
    const errorDetails = { wordpress: "error", x: "success" };
    render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={errorDetails}
        attemptCount={1}
        onRetrySuccess={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: /retry publishing to wordpress/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry publishing to x/i })).not.toBeInTheDocument();
  });

  it("shows Attempt 2 of 3 for attemptCount=2", () => {
    const errorDetails = { wordpress: "some error" };
    render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={errorDetails}
        attemptCount={2}
        onRetrySuccess={vi.fn()}
      />
    );

    expect(screen.getByText("Attempt 2 of 3")).toBeInTheDocument();
  });

  it("shows max retries text and no Retry button when attemptCount=3", () => {
    const errorDetails = { wordpress: "some error" };
    render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={errorDetails}
        attemptCount={3}
        onRetrySuccess={vi.fn()}
      />
    );

    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
    expect(screen.getByText(/maximum retries reached/i)).toBeInTheDocument();
  });

  it("calls retryPublish when Retry button is clicked", async () => {
    mockRetryPublish.mockResolvedValueOnce({ job_id: "job-1" });
    mockJobGet.mockResolvedValue({ status: "complete" });

    const onRetrySuccess = vi.fn();
    const errorDetails = { wordpress: "some error" };
    render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={errorDetails}
        attemptCount={1}
        onRetrySuccess={onRetrySuccess}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /retry publishing to wordpress/i }));

    await waitFor(() => expect(mockRetryPublish).toHaveBeenCalledWith("campaign-123", "wordpress"));
  });

  it("disables retry button during in-flight and shows spinner; other buttons stay enabled", async () => {
    let resolveRetry: (val: { job_id: string }) => void;
    mockRetryPublish.mockImplementationOnce(
      () => new Promise<{ job_id: string }>((resolve) => { resolveRetry = resolve; })
    );

    const errorDetails = { wordpress: "wp error", linkedin: "li error" };
    render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={errorDetails}
        attemptCount={1}
        onRetrySuccess={vi.fn()}
      />
    );

    const wpBtn = screen.getByRole("button", { name: /retry publishing to wordpress/i });
    const liBtn = screen.getByRole("button", { name: /retry publishing to linkedin/i });

    fireEvent.click(wpBtn);

    await waitFor(() => expect(wpBtn).toBeDisabled());
    expect(liBtn).not.toBeDisabled();

    // Resolve so the test can clean up
    mockJobGet.mockResolvedValue({ status: "complete" });
    resolveRetry!({ job_id: "job-1" });
  });

  it("calls onRetrySuccess when retry job completes successfully", async () => {
    mockRetryPublish.mockResolvedValueOnce({ job_id: "job-1" });
    mockJobGet.mockResolvedValue({ status: "complete" });

    const onRetrySuccess = vi.fn();
    const errorDetails = { linkedin: "li error" };
    render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={errorDetails}
        attemptCount={1}
        onRetrySuccess={onRetrySuccess}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /retry publishing to linkedin/i }));

    await waitFor(() => expect(onRetrySuccess).toHaveBeenCalled(), { timeout: 6000 });
  });

  it("returns null when jobErrorDetails is null", () => {
    const { container } = render(
      <RetryPanel
        campaign={makeCampaign()}
        jobId="job-1"
        jobErrorDetails={null}
        attemptCount={0}
        onRetrySuccess={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
