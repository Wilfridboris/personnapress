import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ImagePanel } from "@/components/campaigns/ImagePanel";

const mockAddToast = vi.fn();

vi.mock("@/lib/stores/useUIStore", () => ({
  useUIStore: (selector: (s: { addToast: typeof mockAddToast }) => unknown) =>
    selector({ addToast: mockAddToast }),
}));

vi.mock("@/lib/api", () => ({
  campaignsApi: { regenerateImage: vi.fn(), patchImage: vi.fn() },
  imagesApi: { upload: vi.fn() },
  APIError: class APIError extends Error {},
}));

vi.mock("next/image", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}));

function renderPanel(jobErrorDetails: string | null) {
  return render(
    <ImagePanel
      campaignId="campaign-123"
      clientId="client-456"
      imageUrl={null}
      imageRegenCount={0}
      jobErrorDetails={jobErrorDetails}
      isGenerating={false}
    />,
  );
}

describe("ImagePanel -- no-image states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows limit reached message and upgrade link when error_details contains image generation skipped", () => {
    renderPanel(
      "Image generation skipped: you have reached your plan limit for image generations this billing cycle.",
    );

    expect(
      screen.getByText("Image limit reached for this billing cycle."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Upgrade your plan" })).toHaveAttribute(
      "href",
      "/account#choose-plan",
    );
  });

  it("shows generation failed message when error_details contains Image generation failed", () => {
    renderPanel("Image generation failed: some internal error");

    expect(
      screen.getByText("Image generation failed. Blog and social posts are complete."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Upgrade your plan" })).not.toBeInTheDocument();
  });

  it("shows no featured image yet when error_details is null", () => {
    renderPanel(null);

    expect(screen.getByText("No featured image yet.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Upgrade your plan" })).not.toBeInTheDocument();
  });
});
