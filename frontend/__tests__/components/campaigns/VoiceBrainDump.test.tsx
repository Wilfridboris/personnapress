import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VoiceBrainDump } from "@/components/campaigns/VoiceBrainDump";

const mockStartRecording = vi.fn();
const mockStopRecording = vi.fn();

let mockStatus = "idle";
let mockError: string | null = null;
let mockIsSupported = true;

vi.mock("@/hooks/useVoiceTranscription", () => ({
  useVoiceTranscription: () => ({
    status: mockStatus,
    error: mockError,
    isSupported: mockIsSupported,
    startRecording: mockStartRecording,
    stopRecording: mockStopRecording,
  }),
}));

function renderComponent(onTranscript = vi.fn()) {
  return render(<VoiceBrainDump onTranscript={onTranscript} />);
}

describe("VoiceBrainDump", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = "idle";
    mockError = null;
    mockIsSupported = true;
  });

  describe("browser unsupported", () => {
    it("renders fallback text and no mic button when isSupported is false", () => {
      mockIsSupported = false;
      renderComponent();
      expect(
        screen.getByText(
          "Microphone access unavailable. Type your Brain Dump below.",
        ),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /record voice brain dump/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("idle state", () => {
    it("renders Record button with correct aria-label", () => {
      renderComponent();
      const btn = screen.getByRole("button", { name: "Record voice Brain Dump" });
      expect(btn).toBeInTheDocument();
      expect(btn).not.toBeDisabled();
    });

    it("calls startRecording when Record button is clicked", () => {
      mockStartRecording.mockResolvedValue(undefined);
      renderComponent();
      fireEvent.click(screen.getByRole("button", { name: "Record voice Brain Dump" }));
      expect(mockStartRecording).toHaveBeenCalledTimes(1);
    });

    it("renders an empty status span", () => {
      renderComponent();
      const status = screen.getByRole("status");
      expect(status).toBeEmptyDOMElement();
    });
  });

  describe("recording state", () => {
    beforeEach(() => {
      mockStatus = "recording";
    });

    it("renders Stop recording button", () => {
      renderComponent();
      expect(
        screen.getByRole("button", { name: "Stop recording" }),
      ).toBeInTheDocument();
    });

    it("calls stopRecording when Stop recording is clicked", () => {
      renderComponent();
      fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
      expect(mockStopRecording).toHaveBeenCalledTimes(1);
    });

    it("shows Recording... status text", () => {
      renderComponent();
      expect(screen.getByText("Recording...")).toBeInTheDocument();
    });
  });

  describe("uploading state", () => {
    beforeEach(() => {
      mockStatus = "uploading";
    });

    it("renders disabled Uploading button", () => {
      renderComponent();
      const btn = screen.getByRole("button", { name: "Uploading audio, please wait" });
      expect(btn).toBeDisabled();
    });

    it("shows Uploading... status text", () => {
      renderComponent();
      expect(screen.getByText("Uploading...")).toBeInTheDocument();
    });
  });

  describe("transcribing state", () => {
    beforeEach(() => {
      mockStatus = "transcribing";
    });

    it("renders disabled Transcribing button", () => {
      renderComponent();
      const btn = screen.getByRole("button", { name: "Transcribing audio, please wait" });
      expect(btn).toBeDisabled();
    });

    it("shows Transcribing... status text", () => {
      renderComponent();
      expect(screen.getByText("Transcribing...")).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    beforeEach(() => {
      mockStatus = "error";
    });

    it("renders Try again button", () => {
      renderComponent();
      expect(
        screen.getByRole("button", { name: "Try recording again" }),
      ).toBeInTheDocument();
    });

    it("calls startRecording when Try again is clicked", () => {
      mockStartRecording.mockResolvedValue(undefined);
      renderComponent();
      fireEvent.click(screen.getByRole("button", { name: "Try recording again" }));
      expect(mockStartRecording).toHaveBeenCalledTimes(1);
    });

    it("shows custom error message when error is set", () => {
      mockError = "Microphone access denied.";
      renderComponent();
      expect(screen.getByText("Microphone access denied.")).toBeInTheDocument();
    });

    it("shows default error message when error is null", () => {
      mockError = null;
      renderComponent();
      expect(
        screen.getByText("Transcription failed. Try again."),
      ).toBeInTheDocument();
    });
  });

  describe("copy rules", () => {
    it("has no exclamation marks in any rendered text", () => {
      const states: Array<typeof mockStatus> = [
        "idle",
        "recording",
        "uploading",
        "transcribing",
        "complete",
        "error",
      ];
      for (const s of states) {
        mockStatus = s;
        const { container, unmount } = renderComponent();
        expect(container.textContent).not.toMatch(/!/);
        unmount();
      }
    });

    it("has no em-dashes or double-dashes in any rendered text", () => {
      const states: Array<typeof mockStatus> = [
        "idle",
        "recording",
        "uploading",
        "transcribing",
        "complete",
        "error",
      ];
      for (const s of states) {
        mockStatus = s;
        const { container, unmount } = renderComponent();
        expect(container.textContent).not.toMatch(/—|--/);
        unmount();
      }
    });
  });
});
