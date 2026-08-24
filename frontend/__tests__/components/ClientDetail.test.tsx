import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ClientDetail } from "@/components/clients/ClientDetail";
import type { ClientResponse } from "@/lib/types";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock next/link — renders a plain anchor
vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: unknown; className?: string }) => (
    <a href={href} className={className}>{children as never}</a>
  ),
}));

// Mock APIs
vi.mock("@/lib/api", () => ({
  jobsApi: {},
  clientsApi: {
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    ingest: vi.fn(),
  },
}));

// Mock useClientStore — ClientDetail accesses via .getState() only
const mockStoreState = {
  clients: [] as { id: string }[],
  addClient: vi.fn(),
  updateClient: vi.fn(),
  updateClientName: vi.fn(),
  removeClient: vi.fn(),
  setActiveClientId: vi.fn(),
};

vi.mock("@/lib/stores/useClientStore", () => ({
  useClientStore: Object.assign(vi.fn(), {
    getState: vi.fn(() => mockStoreState),
  }),
}));

// Mock useJobStatus — configurable per test; defaults to no active job
const mockUseJobStatus = vi.hoisted(() => vi.fn().mockReturnValue({ job: null }));

vi.mock("@/hooks/useJobStatus", () => ({
  useJobStatus: (...args: unknown[]) => mockUseJobStatus(...args),
  isJobTerminal: () => false,
}));

// Mock TanStack Query
vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

// Mock child components not under test
vi.mock("@/components/clients/FileUploadPanel", () => ({
  FileUploadPanel: () => null,
}));
vi.mock("@/components/clients/LowConfidenceBanner", () => ({
  LowConfidenceBanner: () => null,
}));
vi.mock("@/components/clients/ClientDetailTabs", () => ({
  // Render profileVoiceContent so that the brand voice section is visible
  ClientDetailTabs: ({ profileVoiceContent }: { profileVoiceContent: unknown }) => (
    <div>{profileVoiceContent as never}</div>
  ),
}));
vi.mock("@/components/publishing/PlatformConnectionsClient", () => ({
  PlatformConnectionsClient: () => null,
}));

import { clientsApi } from "@/lib/api";

function makeClient(overrides: Partial<ClientResponse> = {}): ClientResponse {
  return {
    id: "client-abc",
    name: "Acme Inc",
    website_url: "https://acme.com",
    brand_voice_profile: { summary: "test voice", low_confidence: false } as never,
    job_id: null,
    campaign_count: 2,
    ...overrides,
  };
}

describe("ClientDetail – Refresh voice profile button", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStoreState.clients = [];
    mockUseJobStatus.mockReturnValue({ job: null });
  });

  it("shows the refresh button when a voice profile exists and no active job", () => {
    render(<ClientDetail client={makeClient()} />);
    expect(screen.getByRole("button", { name: /refresh voice profile/i })).toBeInTheDocument();
  });

  it("does not show the refresh button when client.job_id is set (ingestion active)", () => {
    render(<ClientDetail client={makeClient({ job_id: "job-123" })} />);
    expect(screen.queryByRole("button", { name: /refresh voice profile/i })).not.toBeInTheDocument();
  });

  it("does not show the refresh button when no voice profile exists", () => {
    render(<ClientDetail client={makeClient({ brand_voice_profile: null })} />);
    expect(screen.queryByRole("button", { name: /refresh voice profile/i })).not.toBeInTheDocument();
  });

  it("opens the confirmation modal when the refresh button is clicked", () => {
    render(<ClientDetail client={makeClient()} />);
    fireEvent.click(screen.getByRole("button", { name: /refresh voice profile/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Re-analyze voice profile?")).toBeInTheDocument();
  });

  it("calls clientsApi.ingest and closes the modal on confirm", async () => {
    vi.mocked(clientsApi.ingest).mockResolvedValue({ job_id: "new-job-789" });

    render(<ClientDetail client={makeClient()} />);
    fireEvent.click(screen.getByRole("button", { name: /refresh voice profile/i }));
    fireEvent.click(screen.getByRole("button", { name: /^re-analyze$/i }));

    await waitFor(() => {
      expect(clientsApi.ingest).toHaveBeenCalledWith("client-abc");
    });

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("does not show the refresh button when the polled job has failed (AC#5)", () => {
    mockUseJobStatus.mockReturnValue({ job: { status: "failed" } });
    render(<ClientDetail client={makeClient({ job_id: "job-123" })} />);
    expect(screen.queryByRole("button", { name: /refresh voice profile/i })).not.toBeInTheDocument();
  });

  it("shows an error alert and keeps the modal open when clientsApi.ingest rejects", async () => {
    vi.mocked(clientsApi.ingest).mockRejectedValue(new Error("Network failure"));

    render(<ClientDetail client={makeClient()} />);
    fireEvent.click(screen.getByRole("button", { name: /refresh voice profile/i }));
    fireEvent.click(screen.getByRole("button", { name: /^re-analyze$/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Network failure");
    });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
