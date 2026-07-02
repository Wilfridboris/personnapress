import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useJobStatus } from "@/hooks/useJobStatus";
import { jobsApi } from "@/lib/api";
import type { Job } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  jobsApi: {
    get: vi.fn(),
  },
}));

function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    campaign_id: "campaign-1",
    client_id: null,
    job_type: "generate_campaign",
    status: "pending",
    scheduled_at: null,
    started_at: null,
    completed_at: null,
    attempt_count: 0,
    error_details: null,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useJobStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns isPolling=true when status is pending", async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob({ status: "pending" }));
    const { result } = renderHook(() => useJobStatus("job-1"), { wrapper });
    await waitFor(() => expect(result.current.job).not.toBeNull());
    expect(result.current.isPolling).toBe(true);
  });

  it("returns isPolling=true when status is in_progress", async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob({ status: "in_progress" }));
    const { result } = renderHook(() => useJobStatus("job-1"), { wrapper });
    await waitFor(() => expect(result.current.job).not.toBeNull());
    expect(result.current.isPolling).toBe(true);
  });

  it("returns isPolling=false when status is complete", async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob({ status: "complete" }));
    const { result } = renderHook(() => useJobStatus("job-1"), { wrapper });
    await waitFor(() => expect(result.current.job).not.toBeNull());
    expect(result.current.isPolling).toBe(false);
  });

  it("returns isPolling=false when status is failed", async () => {
    vi.mocked(jobsApi.get).mockResolvedValue(makeJob({ status: "failed" }));
    const { result } = renderHook(() => useJobStatus("job-1"), { wrapper });
    await waitFor(() => expect(result.current.job).not.toBeNull());
    expect(result.current.isPolling).toBe(false);
  });

  it("does not fetch when jobId is null", () => {
    const { result } = renderHook(() => useJobStatus(null), { wrapper });
    expect(result.current.job).toBeNull();
    expect(jobsApi.get).not.toHaveBeenCalled();
  });

  it("does not fetch when jobId is empty string", () => {
    const { result } = renderHook(() => useJobStatus(""), { wrapper });
    expect(result.current.job).toBeNull();
    expect(jobsApi.get).not.toHaveBeenCalled();
  });

  it("returns error when API fails", async () => {
    vi.mocked(jobsApi.get).mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useJobStatus("job-1"), { wrapper });
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toBeInstanceOf(Error);
  });
});
