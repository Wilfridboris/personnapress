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
  setImage: vi.fn().mockReturnThis(),
  deleteSelection: vi.fn().mockReturnThis(),
  updateAttributes: vi.fn().mockReturnThis(),
  insertContent: vi.fn().mockReturnThis(),
  run: vi.fn(),
};

const mockEditor = {
  chain: vi.fn(() => mockChain),
  isActive: vi.fn(() => false),
  can: vi.fn(() => ({ undo: () => true })),
  getHTML: vi.fn(() => "<p>edited content</p>"),
  getAttributes: vi.fn(() => ({})),
  isEmpty: false,
  destroy: vi.fn(),
  state: { selection: { from: 0 }, doc: { nodeAt: vi.fn(() => null) } },
};

vi.mock("@tiptap/react", () => ({
  useEditor: vi.fn((opts?: { onUpdate?: (args: { editor: typeof mockEditor }) => void }) => {
    if (opts?.onUpdate) {
      (mockEditor as unknown as Record<string, unknown>)._triggerUpdate = () =>
        opts.onUpdate?.({ editor: mockEditor });
    }
    return mockEditor;
  }),
  useEditorState: vi.fn(({ selector }: { editor: unknown; selector: (ctx: { editor: typeof mockEditor }) => unknown }) =>
    selector({ editor: mockEditor }),
  ),
  EditorContent: ({ editor }: { editor: unknown }) =>
    editor ? <div data-testid="editor-content">editor</div> : null,
}));

vi.mock("@tiptap/starter-kit", () => ({
  default: { configure: vi.fn(() => ({})) },
}));
vi.mock("@tiptap/extension-link", () => ({
  default: { configure: vi.fn(() => ({})) },
}));
vi.mock("@tiptap/extension-image", () => ({
  default: { configure: vi.fn(() => ({})) },
}));
vi.mock("dompurify", () => ({
  default: { sanitize: vi.fn((html: string) => html) },
}));
vi.mock("@/components/ui/Modal", () => ({
  Modal: ({ isOpen, children }: { isOpen: boolean; children: React.ReactNode }) =>
    isOpen ? <div data-testid="modal">{children}</div> : null,
}));

// Mock campaignsApi and imagesApi
vi.mock("@/lib/api", () => ({
  campaignsApi: {
    patch: vi.fn(),
  },
  imagesApi: {
    upload: vi.fn(),
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
      <BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />,
    );
    expect(screen.getByRole("toolbar", { name: /text formatting/i })).toBeInTheDocument();
  });

  it("does NOT render toolbar when readOnly=true", () => {
    render(
      <BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={true} />,
    );
    expect(screen.queryByRole("toolbar")).not.toBeInTheDocument();
  });

  it("renders editor content area", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" />);
    expect(screen.getByTestId("editor-content")).toBeInTheDocument();
  });

  it("renders Save button when readOnly=false", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    expect(screen.getByRole("button", { name: /save edits/i })).toBeInTheDocument();
  });

  it("does NOT render Save button when readOnly=true", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={true} />);
    expect(screen.queryByRole("button", { name: /save edits/i })).not.toBeInTheDocument();
  });

  it("Save button is disabled when not dirty", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    const saveBtn = screen.getByRole("button", { name: /save edits/i });
    expect(saveBtn).toBeDisabled();
  });

  it("Save button calls campaignsApi.patch with editor.getHTML() result", async () => {
    const { campaignsApi } = await import("@/lib/api");
    const patchMock = vi.mocked(campaignsApi.patch).mockResolvedValue({} as never);

    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);

    // Simulate editor becoming dirty by triggering onUpdate
    const { useEditor } = await import("@tiptap/react");
    const opts = vi.mocked(useEditor).mock.calls[0]?.[0];
    opts?.onUpdate?.({ editor: mockEditor } as unknown as Parameters<NonNullable<typeof opts.onUpdate>>[0]);

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

    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);

    const { useEditor } = await import("@tiptap/react");
    const opts = vi.mocked(useEditor).mock.calls[0]?.[0];
    opts?.onUpdate?.({ editor: mockEditor } as unknown as Parameters<NonNullable<typeof opts.onUpdate>>[0]);

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

    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);

    const { useEditor } = await import("@tiptap/react");
    const opts = vi.mocked(useEditor).mock.calls[0]?.[0];
    opts?.onUpdate?.({ editor: mockEditor } as unknown as Parameters<NonNullable<typeof opts.onUpdate>>[0]);

    const saveBtn = screen.getByRole("button", { name: /save edits/i });
    await waitFor(() => expect(saveBtn).not.toBeDisabled());
    fireEvent.click(saveBtn);

    await waitFor(() =>
      expect(mockAddToast).toHaveBeenCalledWith("Network error", "error"),
    );
  });

  it("renders Insert image toolbar button", () => {
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    expect(screen.getByRole("button", { name: /insert image/i })).toBeInTheDocument();
  });

  // ── Link dialog tests ──────────────────────────────────────────────────────

  it("clicking Link2 toolbar button opens the link modal with Nofollow selected by default", () => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    expect(screen.getByTestId("modal")).toBeInTheDocument();
    expect(screen.getByText("Insert link")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^nofollow$/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /^dofollow$/i })).toHaveAttribute("aria-pressed", "false");
  });

  it("confirming with valid URL and Nofollow (default) calls setLink with nofollow rel", () => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    fireEvent.change(screen.getByPlaceholderText("https://example.com"), {
      target: { value: "https://example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /insert link/i }));
    expect(mockChain.setLink).toHaveBeenCalledWith({
      href: "https://example.com",
      rel: "nofollow noopener noreferrer",
    });
    expect(mockChain.run).toHaveBeenCalled();
  });

  it("switching to Dofollow and confirming calls setLink with noopener rel only", () => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    fireEvent.change(screen.getByPlaceholderText("https://example.com"), {
      target: { value: "https://example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^dofollow$/i }));
    fireEvent.click(screen.getByRole("button", { name: /insert link/i }));
    expect(mockChain.setLink).toHaveBeenCalledWith({
      href: "https://example.com",
      rel: "noopener noreferrer",
    });
    expect(mockChain.run).toHaveBeenCalled();
  });

  it("pre-populates URL and selects Nofollow when editing an existing nofollow link", () => {
    mockEditor.isActive.mockImplementation((type: string) => type === "link");
    mockEditor.getAttributes.mockReturnValue({ href: "https://x.com", rel: "nofollow noopener noreferrer" });
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    const urlInput = screen.getByPlaceholderText("https://example.com") as HTMLInputElement;
    expect(urlInput.value).toBe("https://x.com");
    const nofollowBtn = screen.getByRole("button", { name: /^nofollow$/i });
    expect(nofollowBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("shows Remove link button when editing existing link; clicking it calls unsetLink", () => {
    mockEditor.isActive.mockImplementation((type: string) => type === "link");
    mockEditor.getAttributes.mockReturnValue({ href: "https://x.com", rel: "nofollow noopener noreferrer" });
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    const removeBtn = screen.getByRole("button", { name: /remove link/i });
    expect(removeBtn).toBeInTheDocument();
    fireEvent.click(removeBtn);
    expect(mockChain.unsetLink).toHaveBeenCalled();
    expect(mockChain.run).toHaveBeenCalled();
  });

  it("confirm button is disabled when URL is empty", () => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    const confirmBtn = screen.getByRole("button", { name: /insert link/i });
    expect(confirmBtn).toBeDisabled();
  });

  it("confirm button is disabled when URL starts with javascript:", () => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    fireEvent.change(screen.getByPlaceholderText("https://example.com"), {
      target: { value: "javascript:alert(1)" },
    });
    expect(screen.getByRole("button", { name: /insert link/i })).toBeDisabled();
  });

  it("confirm button is enabled when URL starts with https://", () => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    fireEvent.change(screen.getByPlaceholderText("https://example.com"), {
      target: { value: "https://valid.com" },
    });
    expect(screen.getByRole("button", { name: /insert link/i })).not.toBeDisabled();
  });

  it("pre-populates URL and selects Dofollow when editing an existing dofollow link", () => {
    mockEditor.isActive.mockImplementation((type: string) => type === "link");
    mockEditor.getAttributes.mockReturnValue({ href: "https://y.com", rel: "noopener noreferrer" });
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    const urlInput = screen.getByPlaceholderText("https://example.com") as HTMLInputElement;
    expect(urlInput.value).toBe("https://y.com");
    expect(screen.getByRole("button", { name: /^dofollow$/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /^nofollow$/i })).toHaveAttribute("aria-pressed", "false");
  });

  it.each([
    ["mailto:user@example.com"],
    ["/relative-path"],
    ["#anchor"],
  ])("confirm button is enabled for valid prefix: %s", (url) => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    fireEvent.change(screen.getByPlaceholderText("https://example.com"), { target: { value: url } });
    expect(screen.getByRole("button", { name: /insert link/i })).not.toBeDisabled();
  });

  it("pressing Enter with a valid URL submits the link", () => {
    mockEditor.isActive.mockReturnValue(false);
    mockEditor.getAttributes.mockReturnValue({});
    render(<BlogEditor initialHtml="<p>Hello</p>" campaignId="camp-1" clientId="client-1" readOnly={false} />);
    fireEvent.click(screen.getByRole("button", { name: /insert or edit link/i }));
    const urlInput = screen.getByPlaceholderText("https://example.com");
    fireEvent.change(urlInput, { target: { value: "https://enter-test.com" } });
    fireEvent.keyDown(urlInput, { key: "Enter" });
    expect(mockChain.setLink).toHaveBeenCalledWith({
      href: "https://enter-test.com",
      rel: "nofollow noopener noreferrer",
    });
    expect(mockChain.run).toHaveBeenCalled();
  });
});
