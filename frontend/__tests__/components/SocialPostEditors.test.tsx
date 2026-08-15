import { describe, it, expect, vi, beforeEach } from "vitest";
import { createRef } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SocialPostEditors, type SocialPostEditorsHandle } from "@/components/campaigns/SocialPostEditors";
import { campaignsApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  campaignsApi: {
    patch: vi.fn(),
  },
  APIError: class APIError extends Error {},
}));

const mockAddToast = vi.fn();
vi.mock("@/lib/stores/useUIStore", () => ({
  useUIStore: (selector: (s: { addToast: typeof mockAddToast }) => unknown) =>
    selector({ addToast: mockAddToast }),
}));

function renderEditors(overrides?: Partial<React.ComponentProps<typeof SocialPostEditors>>) {
  return render(
    <SocialPostEditors
      campaignId="camp-1"
      initialXPost=""
      initialLinkedInPost=""
      readOnly={false}
      {...overrides}
    />
  );
}

describe("SocialPostEditors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders X counter as '0 / 280' on init with empty post", () => {
    renderEditors({ initialXPost: "" });
    expect(screen.getByText("0 / 280")).toBeInTheDocument();
  });

  it("updates X counter as user types", () => {
    renderEditors({ initialXPost: "" });
    const textarea = screen.getByLabelText("X post content");
    fireEvent.change(textarea, { target: { value: "hello" } });
    expect(screen.getByText("5 / 280")).toBeInTheDocument();
  });

  it("X counter turns danger color when length >= 267", () => {
    renderEditors({ initialXPost: "" });
    const textarea = screen.getByLabelText("X post content");
    const longText = "a".repeat(267);
    fireEvent.change(textarea, { target: { value: longText } });
    const counter = screen.getByText("267 / 280");
    expect(counter.className).toContain("text-danger");
  });

  it("X counter returns to graphite when below 267", () => {
    renderEditors({ initialXPost: "" });
    const textarea = screen.getByLabelText("X post content");
    fireEvent.change(textarea, { target: { value: "a".repeat(267) } });
    fireEvent.change(textarea, { target: { value: "a".repeat(266) } });
    const counter = screen.getByText("266 / 280");
    expect(counter.className).not.toContain("text-danger");
    expect(counter.className).toContain("text-graphite");
  });

  it("LinkedIn counter turns danger at >= 1425 (95% of 1500)", () => {
    renderEditors({ initialLinkedInPost: "" });
    const textarea = screen.getByLabelText("LinkedIn post content");
    const longText = "a".repeat(1425);
    fireEvent.change(textarea, { target: { value: longText } });
    const counter = screen.getByText("1425 / 1500");
    expect(counter.className).toContain("text-danger");
  });

  it("Save button is hidden when not dirty", () => {
    renderEditors();
    expect(screen.queryByRole("button", { name: /save social posts/i })).not.toBeInTheDocument();
  });

  it("Save button appears after typing", () => {
    renderEditors();
    const textarea = screen.getByLabelText("X post content");
    fireEvent.change(textarea, { target: { value: "new content" } });
    expect(screen.getByRole("button", { name: /save social posts/i })).toBeInTheDocument();
  });

  it("Save calls campaignsApi.patch with all five fields", async () => {
    vi.mocked(campaignsApi.patch).mockResolvedValue({} as never);

    renderEditors({ initialXPost: "original", initialLinkedInPost: "orig-li" });
    const xTextarea = screen.getByLabelText("X post content");
    fireEvent.change(xTextarea, { target: { value: "updated x" } });

    fireEvent.click(screen.getByRole("button", { name: /save social posts/i }));

    await waitFor(() => {
      expect(campaignsApi.patch).toHaveBeenCalledWith("camp-1", {
        x_post: "updated x",
        linkedin_post: "orig-li",
        instagram_caption: "",
        facebook_post: "",
        threads_post: "",
      });
    });
  });

  it("shows success toast on save success", async () => {
    vi.mocked(campaignsApi.patch).mockResolvedValue({} as never);

    renderEditors();
    fireEvent.change(screen.getByLabelText("X post content"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /save social posts/i }));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith("Social posts saved.", "success");
    });
  });

  it("shows error toast on save failure", async () => {
    vi.mocked(campaignsApi.patch).mockRejectedValue(new Error("Network error"));

    renderEditors();
    fireEvent.change(screen.getByLabelText("X post content"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /save social posts/i }));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith("Failed to save social posts.", "error");
    });
  });

  it("readOnly=true disables textareas and hides counters and save button", () => {
    renderEditors({ readOnly: true, initialXPost: "hello", initialLinkedInPost: "world" });
    const xTextarea = screen.getByLabelText("X post content");
    const liTextarea = screen.getByLabelText("LinkedIn post content");
    expect(xTextarea).toBeDisabled();
    expect(liTextarea).toBeDisabled();
    expect(screen.queryByText(/\/ 280/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/ 1500/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save/i })).not.toBeInTheDocument();
  });

  it("renders campaign image thumbnail when imageUrl is provided", () => {
    renderEditors({ imageUrl: "https://cdn.example.com/img.png" });
    const img = screen.getByRole("img", { name: "Campaign image" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://cdn.example.com/img.png");
  });

  it("does not render image thumbnail when imageUrl is null", () => {
    renderEditors({ imageUrl: null });
    expect(screen.queryByRole("img", { name: "Campaign image" })).not.toBeInTheDocument();
  });

  it("does not render image thumbnail when imageUrl is undefined", () => {
    renderEditors({});
    expect(screen.queryByRole("img", { name: "Campaign image" })).not.toBeInTheDocument();
  });

  it("getCurrentValues ref returns current textarea values for all five fields", () => {
    const ref = createRef<SocialPostEditorsHandle>();
    render(
      <SocialPostEditors
        campaignId="camp-1"
        initialXPost="init-x"
        initialLinkedInPost="init-li"
        initialInstagramCaption="init-ig"
        initialFacebookPost="init-fb"
        initialThreadsPost="init-th"
        ref={ref}
      />
    );
    const xTextarea = screen.getByLabelText("X post content");
    fireEvent.change(xTextarea, { target: { value: "new-x" } });
    expect(ref.current?.getCurrentValues()).toEqual({
      x_post: "new-x",
      linkedin_post: "init-li",
      instagram_caption: "init-ig",
      facebook_post: "init-fb",
      threads_post: "init-th",
    });
  });

  // AC 6: Instagram section visibility driven by connection state

  it("shows Instagram section when instagram connected", () => {
    renderEditors({ metaContext: { instagram: true } });
    expect(screen.getByLabelText("Instagram caption content")).toBeInTheDocument();
  });

  it("hides Instagram section when instagram not connected", () => {
    renderEditors({ metaContext: { instagram: false } });
    expect(screen.queryByLabelText("Instagram caption content")).not.toBeInTheDocument();
  });

  it("hides Instagram section when metaContext is undefined", () => {
    renderEditors({ metaContext: undefined });
    expect(screen.queryByLabelText("Instagram caption content")).not.toBeInTheDocument();
  });

  it("shows Instagram section with empty textarea when caption is null but instagram connected", () => {
    renderEditors({
      metaContext: { instagram: true },
      initialInstagramCaption: null,
      imageUrl: "https://cdn.example.com/img.png",
    });
    const textarea = screen.getByLabelText("Instagram caption content");
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveValue("");
  });

  it("shows Instagram skip warning when instagram connected and no imageUrl", () => {
    renderEditors({ imageUrl: null, metaContext: { instagram: true } });
    expect(screen.getByText(/Instagram will be skipped at publish/i)).toBeInTheDocument();
  });

  it("does not render Instagram warning when imageUrl is provided", () => {
    renderEditors({ imageUrl: "https://cdn.example.com/img.png", metaContext: { instagram: true } });
    expect(screen.queryByText(/Instagram will be skipped at publish/i)).not.toBeInTheDocument();
  });

  it("does not render Instagram warning when instagram is false", () => {
    renderEditors({ imageUrl: null, metaContext: { instagram: false } });
    expect(screen.queryByText(/Instagram will be skipped at publish/i)).not.toBeInTheDocument();
  });

  it("shows Facebook section when facebook_page connected", () => {
    renderEditors({ metaContext: { facebook_page: true } });
    expect(screen.getByLabelText("Facebook post content")).toBeInTheDocument();
  });

  it("hides Facebook section when facebook_page not connected", () => {
    renderEditors({ metaContext: { facebook_page: false } });
    expect(screen.queryByLabelText("Facebook post content")).not.toBeInTheDocument();
  });

  it("shows Threads section when threads connected", () => {
    renderEditors({ metaContext: { threads: true } });
    expect(screen.getByLabelText("Threads post content")).toBeInTheDocument();
  });

  it("hides Threads section when threads not connected", () => {
    renderEditors({ metaContext: { threads: false } });
    expect(screen.queryByLabelText("Threads post content")).not.toBeInTheDocument();
  });

  it("Threads counter turns danger at >= 475 (95% of 500)", () => {
    renderEditors({ metaContext: { threads: true } });
    const textarea = screen.getByLabelText("Threads post content");
    fireEvent.change(textarea, { target: { value: "a".repeat(475) } });
    const counter = screen.getByText("475 / 500");
    expect(counter.className).toContain("text-danger");
  });

  it("LinkedIn section no longer shows Instagram or Facebook badges", () => {
    renderEditors({ metaContext: { instagram: true, facebook_page: true } });
    expect(screen.queryByLabelText("Also used as Instagram caption")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Also used as Facebook Page post")).not.toBeInTheDocument();
  });

  it("X section no longer shows Threads badge", () => {
    renderEditors({ metaContext: { threads: true } });
    // The old badge was a span with aria-label "Also posts to Threads"
    expect(screen.queryByLabelText("Also posts to Threads")).not.toBeInTheDocument();
  });

  it("save includes all five fields after editing instagram caption", async () => {
    vi.mocked(campaignsApi.patch).mockResolvedValue({} as never);

    renderEditors({
      initialXPost: "x-post",
      initialLinkedInPost: "li-post",
      metaContext: { instagram: true },
    });

    const igTextarea = screen.getByLabelText("Instagram caption content");
    fireEvent.change(igTextarea, { target: { value: "ig caption updated" } });
    fireEvent.click(screen.getByRole("button", { name: /save social posts/i }));

    await waitFor(() => {
      expect(campaignsApi.patch).toHaveBeenCalledWith("camp-1", {
        x_post: "x-post",
        linkedin_post: "li-post",
        instagram_caption: "ig caption updated",
        facebook_post: "",
        threads_post: "",
      });
    });
  });
});
