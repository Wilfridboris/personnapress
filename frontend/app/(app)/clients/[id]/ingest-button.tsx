"use client";

import { useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function IngestButton({ clientId }: { clientId: number }) {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle"
  );

  async function handleIngest() {
    setStatus("loading");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/clients/${clientId}/ingest`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error();
      setStatus("done");
      setTimeout(() => {
        window.location.reload();
      }, 1200);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }

  return (
    <button
      onClick={handleIngest}
      disabled={status === "loading"}
      className={cn(
        "inline-flex items-center gap-2 text-sm font-medium px-5 py-2.5 border transition-colors",
        status === "error"
          ? "border-danger text-danger"
          : status === "done"
          ? "border-success text-success"
          : "border-ink text-ink hover:bg-ink hover:text-paper",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
    >
      {status === "loading" ? (
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      ) : (
        <RefreshCw className="size-4" aria-hidden="true" />
      )}
      {status === "loading"
        ? "Ingesting..."
        : status === "done"
        ? "Done!"
        : status === "error"
        ? "Failed. Retry?"
        : "Run Brand Ingestion"}
    </button>
  );
}
