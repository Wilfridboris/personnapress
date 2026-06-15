"use client";

import { useState } from "react";
import { CheckCircle2, XCircle, Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type ActionType = "approve" | "reject" | "publish";
type Status = "idle" | "loading" | "done" | "error";

export function ApprovalPanel({ campaignId }: { campaignId: string }) {
  const [status, setStatus] = useState<Status>("idle");
  const [activeAction, setActiveAction] = useState<ActionType | null>(null);

  async function handleAction(action: ActionType) {
    setActiveAction(action);
    setStatus("loading");

    const endpoint =
      action === "publish"
        ? `/api/v1/campaigns/${campaignId}/publish`
        : `/api/v1/campaigns/${campaignId}/${action}`;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${endpoint}`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error();
      setStatus("done");
      setTimeout(() => window.location.reload(), 800);
    } catch {
      setStatus("error");
      setTimeout(() => {
        setStatus("idle");
        setActiveAction(null);
      }, 3000);
    }
  }

  const isLoading = status === "loading";

  return (
    <div className="border border-ink/20 bg-highlight/30 p-5 mb-8 flex items-center justify-between gap-4 flex-wrap">
      <div>
        <p className="font-mono text-xs text-graphite uppercase tracking-wider mb-1">
          Awaiting your review
        </p>
        <p className="text-sm text-ink font-medium">
          Approve to save for publishing, or reject to discard.
        </p>
      </div>

      <div className="flex items-center gap-3">
        {/* Reject */}
        <button
          onClick={() => handleAction("reject")}
          disabled={isLoading}
          className={cn(
            "inline-flex items-center gap-2 text-sm font-medium px-5 py-2.5 border transition-colors",
            "border-danger/40 text-danger hover:bg-danger hover:text-paper hover:border-danger",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          {isLoading && activeAction === "reject" ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <XCircle className="size-4" aria-hidden="true" />
          )}
          Reject
        </button>

        {/* Approve */}
        <button
          onClick={() => handleAction("approve")}
          disabled={isLoading}
          className={cn(
            "inline-flex items-center gap-2 text-sm font-medium px-5 py-2.5 border transition-colors",
            "border-success/40 text-success hover:bg-success hover:text-paper hover:border-success",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          {isLoading && activeAction === "approve" ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="size-4" aria-hidden="true" />
          )}
          Approve
        </button>

        {/* Publish */}
        <button
          onClick={() => handleAction("publish")}
          disabled={isLoading}
          className={cn(
            "inline-flex items-center gap-2 text-sm font-medium px-5 py-2.5 bg-ink text-paper transition-colors",
            "hover:bg-graphite",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          {isLoading && activeAction === "publish" ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="size-4" aria-hidden="true" />
          )}
          Approve and Publish
        </button>
      </div>

      {status === "error" && (
        <p className="w-full text-xs font-mono text-danger mt-1">
          Action failed. Please try again.
        </p>
      )}
    </div>
  );
}
