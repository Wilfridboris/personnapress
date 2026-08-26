import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import NewCampaignPage from "@/app/(app)/campaigns/new/page";

const mockCreate = vi.hoisted(() => vi.fn());
const mockPush = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/stores/useClientStore", () => ({
  useClientStore: () => ({
    clients: [{ id: "client-1", name: "Test Client", brand_voice_profile: null, brand_voice_profile_status: null }],
    activeClientId: "client-1",
    isInitialized: true,
  }),
}));

vi.mock("@/lib/stores/useUIStore", () => ({
  useUIStore: (selector: (s: { showUpgradePrompt: () => void }) => unknown) =>
    selector({ showUpgradePrompt: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  campaignsApi: { create: mockCreate },
  publishingApi: { listConnections: vi.fn().mockResolvedValue({ items: [] }) },
  APIError: class APIError extends Error {
    code: string;
    constructor(message: string, code = "UNKNOWN") {
      super(message);
      this.code = code;
    }
  },
}));

vi.mock("@/components/campaigns/VoiceBrainDump", () => ({
  VoiceBrainDump: () => null,
}));

vi.mock("@/components/campaigns/LengthSelector", () => ({
  LengthSelector: () => <div data-testid="length-selector" />,
}));

vi.mock("@/components/campaigns/TemplateSelector", () => ({
  TemplateSelector: () => <div data-testid="template-selector" />,
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("NewCampaignPage — Story 3.29 assist-mode integration", () => {
  beforeEach(() => {
    mockCreate.mockResolvedValue({ campaign_id: "camp-1", job_id: "job-1" });
    mockCreate.mockClear();
    mockPush.mockClear();
  });

  it("switches brain-dump placeholder to finished-draft copy when Assist mode is selected", () => {
    render(<NewCampaignPage />, { wrapper });
    fireEvent.click(screen.getByRole("radio", { name: /assist my writing/i }));
    expect(
      screen.getByPlaceholderText(/paste the post you already wrote/i)
    ).toBeInTheDocument();
  });

  it("sends generation_mode in create payload for social_only campaign (not null)", async () => {
    render(<NewCampaignPage />, { wrapper });
    fireEvent.click(screen.getByRole("radio", { name: /social post only/i }));
    const textarea = document.querySelector("textarea")!;
    fireEvent.change(textarea, { target: { value: "A".repeat(25) } });
    fireEvent.click(screen.getByRole("button", { name: /generate campaign/i }));
    await waitFor(() => expect(mockCreate).toHaveBeenCalled());
    expect(mockCreate.mock.calls[0][0]).toMatchObject({
      campaign_type: "social_only",
      generation_mode: "generate",
    });
  });

  it("does not null generation_mode for social_only (regression guard pre-3.29)", async () => {
    render(<NewCampaignPage />, { wrapper });
    fireEvent.click(screen.getByRole("radio", { name: /social post only/i }));
    const textarea = document.querySelector("textarea")!;
    fireEvent.change(textarea, { target: { value: "B".repeat(25) } });
    fireEvent.click(screen.getByRole("button", { name: /generate campaign/i }));
    await waitFor(() => expect(mockCreate).toHaveBeenCalled());
    expect(mockCreate.mock.calls[0][0].generation_mode).not.toBeNull();
  });

  it("marks blog-only block as aria-hidden when social_only is selected", () => {
    const { container } = render(<NewCampaignPage />, { wrapper });
    fireEvent.click(screen.getByRole("radio", { name: /social post only/i }));
    const hiddenBlock = container.querySelector('.overflow-hidden[aria-hidden="true"]');
    expect(hiddenBlock).not.toBeNull();
  });
});
