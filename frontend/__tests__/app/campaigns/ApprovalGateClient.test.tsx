import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApprovalGateClient } from "@/app/(app)/campaigns/[id]/ApprovalGateClient";
import type { Campaign } from "@/lib/types";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockAddToast = vi.fn();

vi.mock("@/lib/stores/useUIStore", () => ({
  useUIStore: (selector: (s: { addToast: typeof mockAddToast }) => unknown) =>
    selector({ addToast: mockAddToast }),
}));

vi.mock("@/lib/stores/useClientStore", () => ({
  useClientStore: () => undefined,
}));

vi.mock("@/lib/api", () => ({
  campaignsApi: { regenerateImage: vi.fn(), patchImage: vi.fn() },
  imagesApi: { upload: vi.fn() },
  publishingApi: { listConnections: vi.fn().mockResolvedValue({ items: [] }) },
  APIError: class APIError extends Error {},
}));

vi.mock("next/image", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}));

vi.mock("@/components/campaigns/BlogEditor", () => ({
  BlogEditor: vi.fn(() => null),
}));

vi.mock("@/components/campaigns/SocialPostEditors", () => ({
  SocialPostEditors: vi.fn(() => null),
}));

vi.mock("@/app/(app)/campaigns/[id]/approval-panel", () => ({
  ApprovalPanel: vi.fn(() => null),
}));

function makeCampaign(overrides: Partial<Campaign> = {}): Campaign {
  return {
    id: "campaign-123",
    client_id: "client-456",
    brain_dump: "test brain dump",
    blog_html: null,
    x_post: "x post content",
    linkedin_post: null,
    image_url: null,
    image_alt: null,
    status: "pending_approval",
    voice_score: null,
    rejection_reason: null,
    scheduled_at: null,
    image_regen_count: 0,
    campaign_type: "blog_full",
    skip_image: false,
    github_pr_url: null,
    roadmap_id: null,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

describe("getCampaignTitle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns Social Campaign for social_only campaign type", () => {
    const campaign = makeCampaign({ campaign_type: "social_only" });
    render(<ApprovalGateClient campaign={campaign} />, { wrapper });

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Social Campaign");
  });

  it("returns Social Campaign for roadmap campaign with no blog_html", () => {
    const campaign = makeCampaign({ roadmap_id: "roadmap-abc", blog_html: null });
    render(<ApprovalGateClient campaign={campaign} />, { wrapper });

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Social Campaign");
  });

  it("returns Campaign when blog_html is present", () => {
    const campaign = makeCampaign({ blog_html: "<p>some content</p>" });
    render(<ApprovalGateClient campaign={campaign} />, { wrapper });

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Campaign");
  });
});

describe("Edit toggle button", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows Edit button for approved campaign", () => {
    render(
      <ApprovalGateClient campaign={makeCampaign({ status: "approved" })} />,
      { wrapper },
    );
    expect(screen.getByRole("button", { name: /^edit$/i })).toBeInTheDocument();
  });

  it("does not show Edit button for pending_approval campaign", () => {
    render(
      <ApprovalGateClient campaign={makeCampaign({ status: "pending_approval" })} />,
      { wrapper },
    );
    expect(screen.queryByRole("button", { name: /^edit$/i })).not.toBeInTheDocument();
  });

  it("does not show Edit button for published campaign", () => {
    render(
      <ApprovalGateClient campaign={makeCampaign({ status: "published" })} />,
      { wrapper },
    );
    expect(screen.queryByRole("button", { name: /^edit$/i })).not.toBeInTheDocument();
  });
});
