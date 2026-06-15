"use client";

import { useEffect, useRef } from "react";
import { clsx } from "clsx";
import { useUIStore } from "@/lib/stores/useUIStore";

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore();

  return (
    <div
      role="region"
      aria-label="Notifications"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
    >
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          id={toast.id}
          message={toast.message}
          type={toast.type}
          onRemove={removeToast}
        />
      ))}
    </div>
  );
}

interface ToastItemProps {
  id: string;
  message: string;
  type: "success" | "error" | "info";
  onRemove: (id: string) => void;
}

function ToastItem({ id, message, type, onRemove }: ToastItemProps) {
  const onRemoveRef = useRef(onRemove);
  useEffect(() => {
    onRemoveRef.current = onRemove;
  }, [onRemove]);

  useEffect(() => {
    const timer = setTimeout(() => onRemoveRef.current(id), 5000);
    return () => clearTimeout(timer);
  }, [id]);

  return (
    <div
      role="alert"
      className={clsx(
        "flex items-start gap-3 border p-4 shadow-brutal text-sm font-body",
        "animate-fade-in-up",
        type === "success" && "bg-success text-white border-success",
        type === "error" && "bg-danger text-white border-danger",
        type === "info" && "bg-paper text-ink border-ink"
      )}
    >
      <span className="flex-1">{message}</span>
      <button
        onClick={() => onRemoveRef.current(id)}
        className="shrink-0 text-current opacity-70 hover:opacity-100"
        aria-label="Dismiss notification"
      >
        &times;
      </button>
    </div>
  );
}
