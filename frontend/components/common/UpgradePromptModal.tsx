"use client";

import { useEffect, useRef, useState } from "react";
import { useUIStore } from "@/lib/stores/useUIStore";
import { subscriptionsApi } from "@/lib/api";

export function UpgradePromptModal() {
  const message = useUIStore((s) => s.upgradePromptMessage);
  const hide = useUIStore((s) => s.hideUpgradePrompt);
  const addToast = useUIStore((s) => s.addToast);
  const [loading, setLoading] = useState(false);
  const subscribeRef = useRef<HTMLButtonElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!message) return;

    const previousFocus = document.activeElement as HTMLElement | null;
    subscribeRef.current?.focus();

    // Scroll lock
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        hide();
        return;
      }
      if (e.key === "Tab" && innerRef.current) {
        const focusable = Array.from(
          innerRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          )
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prevOverflow;
      previousFocus?.focus();
    };
  }, [message, hide]);

  if (!message) return null;

  async function handleSubscribe() {
    setLoading(true);
    try {
      const { portal_url } = await subscriptionsApi.createPortal();
      window.location.href = portal_url;
    } catch {
      addToast("Could not open billing portal. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upgrade-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={hide}
    >
      <div
        ref={innerRef}
        className="bg-[#F9F9F6] border border-[#E5E5E5] p-8 max-w-sm w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="upgrade-modal-title"
          className="font-serif text-xl text-[#111111] mb-3"
        >
          Subscription required
        </h2>
        <p className="text-sm text-[#555555] mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            ref={subscribeRef}
            onClick={handleSubscribe}
            disabled={loading}
            className="flex-1 bg-[#111111] text-white px-4 py-2.5 text-sm font-medium hover:bg-white hover:text-[#111111] border border-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 disabled:opacity-60"
          >
            {loading ? "Opening..." : "Subscribe"}
          </button>
          <button
            onClick={hide}
            className="px-4 py-2.5 text-sm border border-[#E5E5E5] text-[#555555] hover:border-[#111111] hover:text-[#111111] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
