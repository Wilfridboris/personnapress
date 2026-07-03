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
    // Go to danger level first
    fireEvent.change(textarea, { target: { value: "a".repeat(267) } });
    // Then drop below danger threshold
    fireEvent.change(textarea, { target: { value: "a".repeat(266) } });
    const counter = screen.getByText("266 / 280");
    expect(counter.className).not.toContain("text-danger");
    expect(counter.className).toContain("text-graphite");
  });

  it("LinkedIn counter turns danger at >= 1235", () => {
    renderEditors({ initialLinkedInPost: "" });
    const textarea = screen.getByLabelText("LinkedIn post content");
    const longText = "a".repeat(1235);
    fireEvent.change(textarea, { target: { value: longText } });
    const counter = screen.getByText("1235 / 1300");
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

  it("Save calls campaignsApi.patch with correct payload", async () => {
    vi.mocked(campaignsApi.patch).mockResolvedValue({} as never);

    renderEditors({ initialXPost: "original", initialLinkedInPost: "orig-li" });
    const xTextarea = screen.getByLabelText("X post content");
    fireEvent.change(xTextarea, { target: { value: "updated x" } });

    fireEvent.click(screen.getByRole("button", { name: /save social posts/i }));

    await waitFor(() => {
      expect(campaignsApi.patch).toHaveBeenCalledWith("camp-1", {
        x_post: "updated x",
        linkedin_post: "orig-li",
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
    expect(screen.queryByText(/\/ 1300/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save/i })).not.toBeInTheDocument();
  });

  it("getCurrentValues ref returns current textarea values", () => {
    const ref = createRef<SocialPostEditorsHandle>();
    render(
      <SocialPostEditors
        campaignId="camp-1"
        initialXPost="init-x"
        initialLinkedInPost="init-li"
        ref={ref}
      />
    );
    const xTextarea = screen.getByLabelText("X post content");
    fireEvent.change(xTextarea, { target: { value: "new-x" } });
    expect(ref.current?.getCurrentValues()).toEqual({
      x_post: "new-x",
      linkedin_post: "init-li",
    });
  });
});
