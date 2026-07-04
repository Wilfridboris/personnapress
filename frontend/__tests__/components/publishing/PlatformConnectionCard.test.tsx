import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PlatformConnectionCard, PlatformConnectionCardSkeleton } from "@/components/publishing/PlatformConnectionCard";
import type { PlatformConnectionStatus } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  publishingApi: {
    createConnection: vi.fn(),
    deleteConnection: vi.fn(),
    getWebflowCollections: vi.fn(),
  },
}));

const { publishingApi } = await import("@/lib/api");

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function renderCard(connection: PlatformConnectionStatus) {
  return render(
    <PlatformConnectionCard clientId="client-123" connection={connection} />,
    { wrapper }
  );
}

const notConnected: PlatformConnectionStatus = { platform: "wordpress", connected: false };
const connected: PlatformConnectionStatus = {
  platform: "wordpress",
  connected: true,
  account_identifier: "https://mysite.com",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PlatformConnectionCardSkeleton", () => {
  it("renders skeleton placeholder", () => {
    const { container } = render(<PlatformConnectionCardSkeleton />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });
});

describe("PlatformConnectionCard — not connected", () => {
  it("shows Not connected status", () => {
    renderCard(notConnected);
    expect(screen.getByText("Not connected")).toBeInTheDocument();
  });

  it("Connect button has descriptive aria-label", () => {
    renderCard(notConnected);
    expect(screen.getByRole("button", { name: "Connect WordPress" })).toBeInTheDocument();
  });

  it("clicking Connect shows type picker (not form directly)", () => {
    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    expect(screen.getByText("Where is your WordPress site hosted?")).toBeInTheDocument();
    expect(screen.queryByLabelText("WordPress site URL")).not.toBeInTheDocument();
  });

  it("Cancel closes the type picker", () => {
    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText("Where is your WordPress site hosted?")).not.toBeInTheDocument();
  });

  it("submitting form calls publishingApi.createConnection via self-hosted flow", async () => {
    vi.mocked(publishingApi.createConnection).mockResolvedValue({
      platform: "wordpress",
      connected: true,
      account_identifier: "https://mysite.com",
    });

    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    fireEvent.click(screen.getByRole("button", { name: "Self-hosted WordPress — your own server or managed host" }));

    fireEvent.change(screen.getByLabelText("WordPress site URL"), {
      target: { value: "https://mysite.com" },
    });
    fireEvent.change(screen.getByLabelText("WordPress Username"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Application Password"), {
      target: { value: "pass pass pass" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Connect" }));

    await waitFor(() => {
      expect(publishingApi.createConnection).toHaveBeenCalledWith(
        "client-123",
        expect.objectContaining({ platform: "wordpress", site_url: "https://mysite.com" })
      );
    });
  });

  it("WordPress 400 error shows inline error message and keeps form open", async () => {
    vi.mocked(publishingApi.createConnection).mockRejectedValue(
      new Error("WordPress returned 401 — check your Application Password.")
    );

    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    fireEvent.click(screen.getByRole("button", { name: "Self-hosted WordPress — your own server or managed host" }));
    fireEvent.change(screen.getByLabelText("WordPress site URL"), {
      target: { value: "https://mysite.com" },
    });
    fireEvent.change(screen.getByLabelText("WordPress Username"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Application Password"), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Connect" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("WordPress site URL")).toBeInTheDocument();
  });
});

describe("PlatformConnectionCard — connected", () => {
  it("shows Connected status with identifier", () => {
    renderCard(connected);
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByText("https://mysite.com")).toBeInTheDocument();
  });

  it("Disconnect button has descriptive aria-label", () => {
    renderCard(connected);
    expect(screen.getByRole("button", { name: "Disconnect WordPress" })).toBeInTheDocument();
  });

  it("clicking Disconnect opens confirmation dialog with role=dialog", () => {
    renderCard(connected);
    fireEvent.click(screen.getByRole("button", { name: "Disconnect WordPress" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("confirm Disconnect calls publishingApi.deleteConnection", async () => {
    vi.mocked(publishingApi.deleteConnection).mockResolvedValue(undefined);

    renderCard(connected);
    // First click opens the dialog (card's Disconnect button)
    fireEvent.click(screen.getByText("Disconnect"));
    // Confirm inside dialog
    const dialog = screen.getByRole("dialog");
    fireEvent.click(dialog.querySelector("button[aria-label='Disconnect WordPress']")!);

    await waitFor(() => {
      expect(publishingApi.deleteConnection).toHaveBeenCalledWith("client-123", "wordpress");
    });
  });
});

describe("PlatformConnectionCard — accessibility", () => {
  it("all inputs have visible labels after selecting self-hosted", () => {
    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    fireEvent.click(screen.getByRole("button", { name: "Self-hosted WordPress — your own server or managed host" }));
    expect(screen.getByLabelText("WordPress site URL")).toBeInTheDocument();
    expect(screen.getByLabelText("WordPress Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Application Password")).toBeInTheDocument();
  });

  it("disconnect dialog has role=dialog", () => {
    renderCard(connected);
    fireEvent.click(screen.getByRole("button", { name: "Disconnect WordPress" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
  });
});

describe("PlatformConnectionCard — OAuth platforms", () => {
  it("X platform renders Connect X as anchor link with correct href", () => {
    renderCard({ platform: "x", connected: false });
    const link = screen.getByRole("link", { name: "Connect X (Twitter)" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/api/auth/x?client_id=client-123");
  });

  it("LinkedIn platform renders Connect LinkedIn as anchor link with correct href", () => {
    renderCard({ platform: "linkedin", connected: false });
    const link = screen.getByRole("link", { name: "Connect LinkedIn" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/api/auth/linkedin?client_id=client-123");
  });
});

describe("PlatformConnectionCard — WordPress.com sub-choice", () => {
  it("test_wordpress_connect_shows_type_picker — clicking Connect shows type picker, not form", () => {
    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    expect(screen.getByRole("button", { name: "Self-hosted WordPress — your own server or managed host" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "WordPress.com — free or paid site hosted by Automattic" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Application Password")).not.toBeInTheDocument();
  });

  it("test_wordpress_selfhosted_selection_reveals_form — Self-hosted click shows 3-field form", () => {
    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    fireEvent.click(screen.getByRole("button", { name: "Self-hosted WordPress — your own server or managed host" }));
    expect(screen.getByLabelText("WordPress site URL")).toBeInTheDocument();
    expect(screen.getByLabelText("WordPress Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Application Password")).toBeInTheDocument();
  });

  it("test_wordpress_com_selection_reveals_oauth_button — WordPress.com click shows OAuth link", () => {
    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    fireEvent.click(screen.getByRole("button", { name: "WordPress.com — free or paid site hosted by Automattic" }));
    const link = screen.getByRole("link", { name: "Connect with WordPress.com via OAuth" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/api/auth/wordpress-com?client_id=client-123");
    expect(screen.getByText("You will be redirected to WordPress.com to authorize access.")).toBeInTheDocument();
  });

  it("test_wordpress_back_navigation — Back button from self-hosted returns to type picker", () => {
    renderCard(notConnected);
    fireEvent.click(screen.getByRole("button", { name: "Connect WordPress" }));
    fireEvent.click(screen.getByRole("button", { name: "Self-hosted WordPress — your own server or managed host" }));
    fireEvent.click(screen.getByRole("button", { name: "Back to WordPress hosting type selection" }));
    expect(screen.getByText("Where is your WordPress site hosted?")).toBeInTheDocument();
    expect(screen.queryByLabelText("WordPress site URL")).not.toBeInTheDocument();
  });

  it("test_wordpress_com_disconnect_uses_correct_platform — connected_via=wordpress-com calls deleteConnection with wordpress-com", async () => {
    vi.mocked(publishingApi.deleteConnection).mockResolvedValue(undefined);

    const wpcomConnected: PlatformConnectionStatus = {
      platform: "wordpress",
      connected: true,
      account_identifier: "https://mysite.wordpress.com",
      connected_via: "wordpress-com",
    };
    renderCard(wpcomConnected);
    fireEvent.click(screen.getByRole("button", { name: "Disconnect WordPress" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.click(dialog.querySelector("button[aria-label='Disconnect WordPress']")!);

    await waitFor(() => {
      expect(publishingApi.deleteConnection).toHaveBeenCalledWith("client-123", "wordpress-com");
    });
  });
});
