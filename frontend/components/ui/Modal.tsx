"use client";

import { useEffect, useRef, ReactNode, RefObject } from "react";
import { clsx } from "clsx";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  titleId?: string;
  descriptionId?: string;
  triggerRef?: RefObject<HTMLElement | null>;
  children: ReactNode;
  className?: string;
}

const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

export function Modal({
  isOpen,
  onClose,
  title,
  titleId = "modal-title",
  descriptionId,
  triggerRef,
  children,
  className,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  const prevIsOpenRef = useRef(false);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return;

    const el = panelRef.current;
    if (!el) return;

    el.querySelectorAll<HTMLElement>(FOCUSABLE)[0]?.focus();

    const trap = (e: KeyboardEvent) => {
      const focusable = el.querySelectorAll<HTMLElement>(FOCUSABLE);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (!first) return;

      if (e.key === "Tab") {
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
      if (e.key === "Escape") {
        onCloseRef.current();
      }
    };

    document.addEventListener("keydown", trap);
    return () => document.removeEventListener("keydown", trap);
  }, [isOpen]);

  // Return focus to trigger only when closing (not on initial mount)
  useEffect(() => {
    if (prevIsOpenRef.current && !isOpen && triggerRef?.current) {
      triggerRef.current.focus();
    }
    prevIsOpenRef.current = isOpen;
  }, [isOpen, triggerRef]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-ink/40"
        onClick={() => onCloseRef.current()}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={clsx(
          "relative z-10 bg-paper border border-ink shadow-brutal",
          "w-full max-w-lg mx-4 p-6",
          "animate-fade-in-up",
          className
        )}
      >
        <div className="flex items-start justify-between mb-4 gap-4">
          <h2 id={titleId} className="font-heading text-xl font-bold text-ink">
            {title}
          </h2>
          <button
            onClick={() => onCloseRef.current()}
            className="shrink-0 text-graphite hover:text-ink transition-colors"
            aria-label="Close dialog"
          >
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
