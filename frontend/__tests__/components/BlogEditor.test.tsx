import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BlogEditor } from "@/components/campaigns/BlogEditor";

// Mock @tiptap/react
const mockChain = {
  focus: vi.fn().mockReturnThis(),
  toggleBold: vi.fn().mockReturnThis(),
  toggleItalic: vi.fn().mockReturnThis(),
  toggleHeading: vi.fn().mockReturnThis(),
  toggleBlockquote: vi.fn().mockReturnThis(),
  setLink: vi.fn().mockReturnThis(),
  unsetLink: vi.fn().mockReturnThis(),
  undo: vi.fn().mockReturnThis(),
  run: vi.fn(),
};

const mockEditor = {
  chain: vi.fn(() => mockChain),
  isActive: vi.fn(() => false),
  can: vi.fn(() => ({ undo: () => true })),
  getHTML: vi.fn(() => "<p>edited content</p>"),
  isEmpty: false,
  destroy: vi.fn(),
};

vi.mock("@tiptap/react", () => ({
  useEditor: vi.fn((opts?: { onUpdate?: (args: { editor: typeof mockEditor }) => void }) => {
    // Call onUpdate to simulate dirty state in tests that need it
    if (opts?.onUpdate) {
      // Store for manual trigger
      (mockEditor as unknown as Record<string, unknown>)._triggerUpdate = () =>
        opts.onUpdate?.({ editor: mockEditor });
    }
    return mockEditor;
  }),
  EditorContent: ({ editor }: { editor: unknown }) =>
    editor ? <div data-testid="editor-content">editor</div> : null,
}));

vi.mock("@tiptap/starter-kit", () => ({
  default: { configure: vi.fn(() => ({})) },
}));
vi.mock("@tiptap/extension-link", () => ({
  default: { configure: vi.fn(() => ({})) },
}));
vi.mock("dompurify", () => ({
  default: { sanitize: vi.fn((html: string) => html) },
}));

// Mock campaignsApi
vi.mock("@/lib/api", () => ({
  campaignsApi: {
    patch: vi.fn(),
  },
}));

// Mock useUIStore
const mockAddToast = vi.fn();
vi.mock("@/lib/stores/useUIStore", () => ({
  useUIStore: (selector: (s: { addToast: typeof mockAddToast }) => unknown) =>
    selector({ addToast: mockAddToast }),
}));

describe("BlogEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders toolbar when readOnly=false", () => {
    render(
      <BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={false} />,
    );
    expect(screen.getByRole("toolbar", { name: /text formatting/i })).toBeInTheDocument();
  });

  it("does NOT render toolbar when readOnly=true", () => {
    render(
      <BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={true} />,
    );
    expect(screen.queryByRole("toolbar")).not.toBeInTheDocument();
  });

  it("renders editor content area", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" />);
    expect(screen.getByTestId("editor-content")).toBeInTheDocument();
  });

  it("renders Save button when readOnly=false", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={false} />);
    expect(screen.getByRole("button", { name: /save edits/i })).toBeInTheDocument();
  });

  it("does NOT render Save button when readOnly=true", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={true} />);
    expect(screen.queryByRole("button", { name: /save edits/i })).not.toBeInTheDocument();
  });

  it("Save button is disabled when not dirty", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={false} />);
    const saveBtn = screen.getByRole("button", { name: /save edits/i });
    expect(saveBtn).toBeDisabled();
  });

  it("Save button calls campaignsApi.patch with editor.getHTML() result", async () => {
    const { campaignsApi } = await import("@/lib/api");
    const patchMock = vi.mocked(campaignsApi.patch).mockResolvedValue({} as never);

    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={false} />);

    // Simulate editor becoming dirty by triggering onUpdate
    const { useEditor } = await import("@tiptap/react");
    const opts = vi.mocked(useEditor).mock.calls[0]?.[0];
    opts?.onUpdate?.({ editor: mockEditor as never });

    const saveBtn = screen.getByRole("button", { name: /save edits/i });

    await waitFor(() => expect(saveBtn).not.toBeDisabled());
    fireEvent.click(saveBtn);

    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith("camp-1", { blog_html: "<p>edited content</p>" }),
    );
  });

  it("shows success toast after successful save", async () => {
    const { campaignsApi } = await import("@/lib/api");
    vi.mocked(campaignsApi.patch).mockResolvedValue({} as never);

    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={false} />);

    const { useEditor } = await import("@tiptap/react");
    const opts = vi.mocked(useEditor).mock.calls[0]?.[0];
    opts?.onUpdate?.({ editor: mockEditor as never });

    const saveBtn = screen.getByRole("button", { name: /save edits/i });
    await waitFor(() => expect(saveBtn).not.toBeDisabled());
    fireEvent.click(saveBtn);

    await waitFor(() =>
      expect(mockAddToast).toHaveBeenCalledWith("Blog post saved.", "success"),
    );
  });

  it("shows error toast on save failure", async () => {
    const { campaignsApi } = await import("@/lib/api");
    vi.mocked(campaignsApi.patch).mockRejectedValue(new Error("Network error"));

    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" readOnly={false} />);

    const { useEditor } = await import("@tiptap/react");
    const opts = vi.mocked(useEditor).mock.calls[0]?.[0];
    opts?.onUpdate?.({ editor: mockEditor as never });

    const saveBtn = screen.getByRole("button", { name: /save edits/i });
    await waitFor(() => expect(saveBtn).not.toBeDisabled());
    fireEvent.click(saveBtn);

    await waitFor(() =>
      expect(mockAddToast).toHaveBeenCalledWith("Network error", "error"),
    );
  });
});
