"use client";

import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { jobsApi } from "@/lib/api";
import type { Job } from "@/lib/types";

export type VoiceStatus =
  | "idle"
  | "recording"
  | "uploading"
  | "transcribing"
  | "complete"
  | "error";

const TERMINAL = new Set(["complete", "failed"]);
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UseVoiceTranscriptionOptions {
  onTranscript: (text: string) => void;
}

export interface UseVoiceTranscriptionReturn {
  status: VoiceStatus;
  error: string | null;
  isSupported: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  analyserNodeRef: React.RefObject<AnalyserNode | null>;
}

export function useVoiceTranscription({
  onTranscript,
}: UseVoiceTranscriptionOptions): UseVoiceTranscriptionReturn {
  const [isSupported, setIsSupported] = useState(false);
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const completeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);
  const analyserNodeRef = useRef<AnalyserNode | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    setIsSupported(
      typeof MediaRecorder !== "undefined" &&
        !!navigator.mediaDevices?.getUserMedia,
    );
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const { data: voiceJob } = useQuery<Job | null>({
    queryKey: ["voice-job", jobId],
    queryFn: async () => (jobId ? jobsApi.get(jobId) : null),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const d = q.state.data;
      if (!d || TERMINAL.has(d.status)) return false;
      return 2000;
    },
    staleTime: 0,
  });

  useEffect(() => {
    if (!voiceJob || status !== "transcribing") return;

    if (voiceJob.status === "complete") {
      const transcript =
        (voiceJob.result as { transcript?: string } | null)?.transcript ?? "";
      if (transcript) {
        onTranscript(transcript);
        setStatus("complete");
        completeTimerRef.current = setTimeout(() => {
          completeTimerRef.current = null;
          setStatus("idle");
          setJobId(null);
        }, 1200);
      } else {
        setError("No speech detected. Try again.");
        setStatus("error");
        setJobId(null);
      }
    } else if (voiceJob.status === "failed") {
      setError(voiceJob.error_details ?? "Transcription failed. Try again.");
      setStatus("error");
      setJobId(null);
    }
  }, [voiceJob, status, onTranscript]);

  async function startRecording(): Promise<void> {
    if (completeTimerRef.current) {
      clearTimeout(completeTimerRef.current);
      completeTimerRef.current = null;
      setJobId(null);
    }
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new AudioContext();
      if (audioCtx.state === "suspended") await audioCtx.resume();
      audioCtxRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      analyserNodeRef.current = analyser;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/mp4";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        streamRef.current?.getTracks().forEach((t) => t.stop());
        analyserNodeRef.current?.disconnect();
        analyserNodeRef.current = null;
        void audioCtxRef.current?.close();
        audioCtxRef.current = null;
        streamRef.current = null;

        if (!isMountedRef.current) return;
        setStatus("uploading");

        try {
          const formData = new FormData();
          formData.append("file", blob, "audio");
          const res = await fetch(`${API_URL}/api/v1/voice/transcribe`, {
            method: "POST",
            body: formData,
            credentials: "include",
          });

          if (!isMountedRef.current) return;

          if (res.status === 202) {
            const data = (await res.json()) as { job_id: string };
            setJobId(data.job_id);
            setStatus("transcribing");
          } else {
            let errorMsg = "Transcription service unavailable.";
            try {
              const errData = (await res.json()) as Record<string, unknown>;
              const detail = errData?.detail as
                | Record<string, unknown>
                | undefined;
              const nestedError = detail?.error as
                | { message?: string }
                | undefined;
              const errShape = (nestedError ??
                errData?.error) as { message?: string } | undefined;
              if (res.status === 413) {
                errorMsg = "Audio file too large. Max 10 MB.";
              } else if (typeof errShape?.message === "string") {
                errorMsg = errShape.message;
              }
            } catch {
              // couldn't parse error body
            }
            setError(errorMsg);
            setStatus("error");
          }
        } catch {
          if (!isMountedRef.current) return;
          setError("Transcription service unavailable.");
          setStatus("error");
        }
      };

      recorder.start(100);
      setStatus("recording");
    } catch (err: unknown) {
      analyserNodeRef.current?.disconnect();
      analyserNodeRef.current = null;
      void audioCtxRef.current?.close();
      audioCtxRef.current = null;
      const name = err instanceof Error ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setError("Microphone access denied.");
      } else {
        setError("Transcription service unavailable.");
      }
      setStatus("error");
    }
  }

  function stopRecording(): void {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
    }
  }

  return { status, error, isSupported, startRecording, stopRecording, analyserNodeRef };
}
