"use client";

import { Loader2, Mic, RotateCcw, Square } from "lucide-react";
import { useVoiceTranscription } from "@/hooks/useVoiceTranscription";

interface VoiceBrainDumpProps {
  onTranscript: (text: string) => void;
}

export function VoiceBrainDump({ onTranscript }: VoiceBrainDumpProps) {
  const { status, error, isSupported, startRecording, stopRecording } =
    useVoiceTranscription({ onTranscript });

  if (!isSupported) {
    return (
      <p className="text-[11px] font-mono text-graphite min-h-[44px] flex items-center">
        Microphone access unavailable. Type your Brain Dump below.
      </p>
    );
  }

  if (status === "recording") {
    return (
      <div className="flex items-center gap-3 min-h-[44px]">
        <button
          type="button"
          onClick={stopRecording}
          aria-label="Stop recording"
          className="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-ink rounded-none bg-ink text-paper hover:bg-transparent hover:text-ink transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
        >
          <Square size={14} aria-hidden="true" />
          <span>Stop recording</span>
        </button>
        <span role="status" aria-live="polite" aria-atomic="true">
          <span
            className="inline-block size-2 rounded-full bg-danger animate-[voice-pulse_1.4s_ease-in-out_infinite] motion-reduce:animate-none"
            aria-hidden="true"
          />
          <span className="text-[11px] font-mono text-graphite ml-1.5">
            Recording...
          </span>
        </span>
      </div>
    );
  }

  if (status === "uploading") {
    return (
      <div className="flex items-center gap-3 min-h-[44px]">
        <button
          type="button"
          disabled
          aria-label="Uploading audio, please wait"
          className="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-border rounded-none bg-transparent text-graphite opacity-60 cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
        >
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          <span>Uploading</span>
        </button>
        <span role="status" aria-live="polite" aria-atomic="true">
          <span className="text-[11px] font-mono text-graphite">
            Uploading...
          </span>
        </span>
      </div>
    );
  }

  if (status === "transcribing") {
    return (
      <div className="flex items-center gap-3 min-h-[44px]">
        <button
          type="button"
          disabled
          aria-label="Transcribing audio, please wait"
          className="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-border rounded-none bg-transparent text-graphite opacity-60 cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
        >
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          <span>Transcribing</span>
        </button>
        <span role="status" aria-live="polite" aria-atomic="true">
          <span className="text-[11px] font-mono text-graphite">
            Transcribing...
          </span>
        </span>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex items-center gap-3 min-h-[44px]">
        <button
          type="button"
          onClick={() => void startRecording()}
          aria-label="Try recording again"
          className="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-ink rounded-none bg-transparent text-ink hover:bg-ink hover:text-paper transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
        >
          <RotateCcw size={14} aria-hidden="true" />
          <span>Try again</span>
        </button>
        <span role="status" aria-live="polite" aria-atomic="true">
          <span className="text-[11px] font-mono text-danger">
            {error ?? "Transcription failed. Try again."}
          </span>
        </span>
      </div>
    );
  }

  // idle / complete
  return (
    <div className="flex items-center gap-3 min-h-[44px]">
      <button
        type="button"
        onClick={() => void startRecording()}
        aria-label="Record voice Brain Dump"
        className="inline-flex items-center gap-2 px-3 h-11 min-w-[44px] border border-ink rounded-none bg-transparent text-[11px] font-mono text-ink uppercase tracking-[0.08em] hover:bg-ink hover:text-paper transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
      >
        <Mic size={14} aria-hidden="true" />
        <span>Record</span>
      </button>
      <span role="status" aria-live="polite" aria-atomic="true" />
    </div>
  );
}
