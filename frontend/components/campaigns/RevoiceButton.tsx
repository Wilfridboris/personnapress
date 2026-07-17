"use client";

import { useRef, useEffect, useId, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

interface RevoiceConfirmModalProps {
  campaignTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
  error: string | null;
}

function RevoiceConfirmModal({ campaignTitle, onConfirm, onCancel, loading, error }: RevoiceConfirmModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const headingId = useId();

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) {
        onCancel();
        return;
      }
      if (e.key === "Tab") {
        const el = panelRef.current;
        if (!el) return;
        const focusable = el.querySelectorAll<HTMLElement>(FOCUSABLE);
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first) return;
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last?.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first?.focus();
          }
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [loading, onCancel]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(17,17,17,0.35)" }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        className="w-full max-w-md rounded-none bg-[#F9F9F6] border border-[#111111] p-8"
      >
        <p
          id={headingId}
          className="font-['Playfair_Display'] text-xl font-bold text-[#111111] mb-1"
        >
          Create a re-voiced draft?
        </p>
        <p className="text-sm font-medium text-[#111111] mb-3 truncate">{campaignTitle}</p>
        <p className="text-sm text-[#555555] leading-relaxed mb-6">
          This creates a new draft using your current voice profile. Your original post is not
          changed. The new draft goes through the approval gate before publishing.
        </p>
        <div className="flex gap-3">
          <Button variant="primary" onClick={onConfirm} disabled={loading} className="min-h-[44px]">
            {loading ? (
              <>
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                Creating...
              </>
            ) : (
              "Create new draft"
            )}
          </Button>
          <Button
            ref={cancelRef}
            variant="secondary"
            onClick={onCancel}
            disabled={loading}
            className="min-h-[44px]"
          >
            Cancel
          </Button>
        </div>
        {error && (
          <p className="text-xs text-[#8B0000] mt-3" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

interface RevoiceButtonProps {
  campaignId: string;
  campaignTitle: string;
}

export function RevoiceButton({ campaignId, campaignTitle }: RevoiceButtonProps) {
  const router = useRouter();
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/campaigns/${campaignId}/revoice`,
        { method: "POST", credentials: "include" },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.error?.message ?? "Failed to create re-voiced draft. Try again.");
      }
      const { new_campaign_id } = await res.json();
      setLoading(false);
      setShowModal(false);
      router.push(`/campaigns/${new_campaign_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create re-voiced draft. Try again.");
      setLoading(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => { setError(null); setShowModal(true); }}
        aria-label={`Re-voice: ${campaignTitle}`}
        className="inline-flex items-center gap-1.5 px-3 py-2 min-h-[44px] border border-[#E5E5E5] bg-transparent text-sm text-[#555555] transition-colors duration-150 hover:border-[#111111] hover:text-[#111111] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1"
      >
        <RefreshCw className="size-3.5" aria-hidden="true" />
        Re-voice
      </button>
      {showModal && (
        <RevoiceConfirmModal
          campaignTitle={campaignTitle}
          onConfirm={handleConfirm}
          onCancel={() => { if (!loading) setShowModal(false); }}
          loading={loading}
          error={error}
        />
      )}
    </>
  );
}
