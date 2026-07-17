"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Check, AlertTriangle } from "lucide-react";
import { filesApi, clientsApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import type { FileItem } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RelearningStatus = "idle" | "learning" | "success" | "error";
const FILE_LIMIT = 10;
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
const ALLOWED_EXTENSIONS = /\.(txt|md|docx)$/i;

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface Props {
  clientId: string;
}

interface FileProgress {
  filename: string;
  size: number;
  progress: number; // 0-100
  status: "uploading" | "done" | "error";
  error?: string;
}

export function FileUploadPanel({ clientId }: Props) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [uploading, setUploading] = useState<FileProgress[]>([]);

  const [relearning, setRelearning] = useState<RelearningStatus>("idle");
  const [relearningError, setRelearningError] = useState<string | null>(null);
  const relearningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: fileList, isLoading } = useQuery({
    queryKey: ["files", clientId],
    queryFn: () => filesApi.list(clientId),
    staleTime: 30_000,
  });

  const currentCount = fileList?.count ?? 0;
  const files: FileItem[] = fileList?.files ?? [];

  const uploadWithProgress = useCallback(
    (file: File): Promise<void> => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append("files", file);

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const pct = (e.loaded / e.total) * 100;
            setUploading((prev) =>
              prev.map((p) =>
                p.filename === file.name ? { ...p, progress: pct } : p,
              ),
            );
          }
        };

        xhr.onload = () => {
          if (xhr.status < 400) {
            // The backend returns HTTP 200 even when Supabase storage fails,
            // so parse the body to detect server-side errors.
            try {
              const body = JSON.parse(xhr.responseText) as {
                uploaded: Array<{ filename: string }>;
                errors: Array<{ filename: string; error: string }>;
              };
              const uploadError = body.errors?.find((e) => e.filename === file.name);
              if (uploadError) {
                setUploading((prev) =>
                  prev.map((p) =>
                    p.filename === file.name
                      ? { ...p, status: "error", error: uploadError.error }
                      : p,
                  ),
                );
                reject(new Error(uploadError.error));
                return;
              }
            } catch {
              // Non-JSON response — treat as success based on status code
            }
            setUploading((prev) =>
              prev.map((p) =>
                p.filename === file.name
                  ? { ...p, progress: 100, status: "done" }
                  : p,
              ),
            );
            resolve();
          } else {
            setUploading((prev) =>
              prev.map((p) =>
                p.filename === file.name
                  ? { ...p, status: "error", error: "Upload failed." }
                  : p,
              ),
            );
            reject(new Error(xhr.responseText));
          }
        };

        xhr.onerror = () => {
          setUploading((prev) =>
            prev.map((p) =>
              p.filename === file.name
                ? { ...p, status: "error", error: "Network error." }
                : p,
            ),
          );
          reject(new Error("Network error"));
        };

        xhr.open("POST", `${API_URL}/api/v1/clients/${clientId}/files`);
        xhr.withCredentials = true;
        xhr.send(formData);
      });
    },
    [clientId],
  );

  const triggerRelearn = useCallback(async () => {
    if (relearningTimerRef.current) clearTimeout(relearningTimerRef.current);
    setRelearning("learning");
    setRelearningError(null);
    try {
      await clientsApi.ingest(clientId);
      setRelearning("success");
      relearningTimerRef.current = setTimeout(() => setRelearning("idle"), 3000);
    } catch {
      setRelearning("error");
      setRelearningError("Failed to start relearning. Try again.");
    }
  }, [clientId]);

  useEffect(() => {
    return () => {
      if (relearningTimerRef.current) clearTimeout(relearningTimerRef.current);
    };
  }, []);

  const handleFilesSelected = useCallback(
    async (selectedFiles: FileList | null) => {
      if (!selectedFiles || selectedFiles.length === 0) return;
      setInlineError(null);

      const toUpload: File[] = [];
      const immediateErrors: FileProgress[] = [];
      let slotsFilled = 0;

      for (const file of Array.from(selectedFiles)) {
        // Extension check
        if (!ALLOWED_EXTENSIONS.test(file.name)) {
          immediateErrors.push({
            filename: file.name,
            size: file.size,
            progress: 0,
            status: "error",
            error: "Only .txt, .md, and .docx files are supported.",
          });
          continue;
        }
        // Size check
        if (file.size > MAX_FILE_SIZE) {
          immediateErrors.push({
            filename: file.name,
            size: file.size,
            progress: 0,
            status: "error",
            error: "File must be under 5 MB.",
          });
          continue;
        }
        // Count check
        if (currentCount + slotsFilled >= FILE_LIMIT) {
          immediateErrors.push({
            filename: file.name,
            size: file.size,
            progress: 0,
            status: "error",
            error: "You've reached the 10-file limit for this client.",
          });
          continue;
        }
        toUpload.push(file);
        slotsFilled += 1;
      }

      if (toUpload.length === 0 && immediateErrors.length === 0) return;

      // Initialise progress state: show validation-rejected files as errors immediately,
      // valid files start as uploading
      setUploading([
        ...immediateErrors,
        ...toUpload.map((f) => ({
          filename: f.name,
          size: f.size,
          progress: 0,
          status: "uploading" as const,
        })),
      ]);

      if (toUpload.length > 0) {
        // Upload valid files sequentially; track how many actually landed
        let successCount = 0;
        for (const file of toUpload) {
          try {
            await uploadWithProgress(file);
            successCount += 1;
          } catch {
            // Error already reflected in uploading state
          }
        }

        // Refresh the file list after all uploads finish
        await queryClient.invalidateQueries({ queryKey: ["files", clientId] });

        // Trigger AI voice relearn from newly uploaded files (only if at least one succeeded)
        if (successCount > 0) {
          triggerRelearn();
        }

        // Clear successfully-done entries after a brief pause so user sees 100%.
        // Keep error entries visible until the next selection attempt.
        setTimeout(() => {
          setUploading((prev) => prev.filter((p) => p.status === "error"));
        }, 800);
      }

      // Reset input so the same files can be re-selected if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [currentCount, uploadWithProgress, queryClient, clientId, triggerRelearn],
  );

  return (
    <section aria-labelledby="files-heading">
      {/* Section label — Paper Style: Inter 12px uppercase tracked */}
      <p
        id="files-heading"
        className="text-xs font-sans uppercase tracking-widest text-ink mb-4"
      >
        Content files
      </p>

      {/* File list */}
      {isLoading ? (
        <p className="text-sm text-graphite mb-4">Loading files...</p>
      ) : files.length === 0 && uploading.length === 0 ? (
        <p className="text-sm text-graphite mb-4">No files uploaded yet.</p>
      ) : (
        <ul className="mb-4 divide-y divide-border border border-border">
          {files.map((f) => (
            <li key={f.filename} className="flex items-center justify-between px-4 py-3">
              <span className="text-sm text-ink font-sans">{f.filename}</span>
              <span className="text-sm text-graphite font-sans ml-4 shrink-0">
                {humanSize(f.size)}
              </span>
            </li>
          ))}

          {/* In-flight uploads */}
          {uploading.map((p) => (
            <li key={p.filename} className="px-4 py-3">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm text-ink font-sans">{p.filename}</span>
                <span className="text-sm text-graphite font-sans ml-4 shrink-0">
                  {humanSize(p.size)}
                </span>
              </div>
              {p.status === "error" ? (
                <p className="text-xs text-danger">{p.error}</p>
              ) : (
                <div className="relative w-full h-0.5 bg-border overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 bg-ink transition-all duration-200"
                    style={{ width: `${p.progress}%` }}
                    role="progressbar"
                    aria-valuenow={Math.round(p.progress)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Uploading ${p.filename}`}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Inline validation error */}
      {inlineError && (
        <p role="alert" className="text-sm text-danger mb-3">
          {inlineError}
        </p>
      )}

      {/* AI relearn status banner */}
      <AnimatePresence>
        {relearning !== "idle" && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="mt-3 border border-[#111111] p-3 flex items-center gap-3"
            role="status"
            aria-live="polite"
          >
            {relearning === "learning" && (
              <>
                <Loader2 className="size-4 text-[#555555] animate-spin shrink-0" aria-hidden="true" />
                <p className="text-[13px] text-[#555555] font-sans">Relearning voice from new content…</p>
              </>
            )}
            {relearning === "success" && (
              <>
                <Check className="size-4 text-[#2E4F2E] shrink-0" aria-hidden="true" />
                <p className="text-[13px] text-[#2E4F2E] font-sans">Voice profile updated.</p>
              </>
            )}
            {relearning === "error" && (
              <>
                <AlertTriangle className="size-4 text-[#8B1A1A] shrink-0" aria-hidden="true" />
                <p className="text-[13px] text-[#8B1A1A] font-sans flex-1">{relearningError}</p>
                <button
                  type="button"
                  onClick={triggerRelearn}
                  className="text-[12px] font-medium text-[#111111] underline underline-offset-2 hover:text-[#555555] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1 shrink-0"
                >
                  Retry
                </button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload button */}
      {currentCount < FILE_LIMIT && (
        <>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.md,.docx"
            className="sr-only"
            aria-hidden="true"
            onChange={(e) => handleFilesSelected(e.target.files)}
          />
          <Button
            variant="secondary"
            onClick={() => {
              setInlineError(null);
              fileInputRef.current?.click();
            }}
            disabled={uploading.some((p) => p.status === "uploading")}
          >
            Upload content files
          </Button>
        </>
      )}

      {currentCount >= FILE_LIMIT && (
        <p className="text-sm text-graphite">
          10-file limit reached.
        </p>
      )}
    </section>
  );
}
