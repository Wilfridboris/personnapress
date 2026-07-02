"use client";

import { useId, useRef } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel: string;
  confirmVariant?: "primary" | "danger";
  isLoading?: boolean;
  triggerRef?: React.RefObject<HTMLButtonElement | null>;
  error?: string | null;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel,
  confirmVariant = "primary",
  isLoading = false,
  triggerRef,
  error,
}: ConfirmModalProps) {
  const uid = useId();
  const titleId = `confirm-title-${uid}`;
  const descId = `confirm-desc-${uid}`;
  const confirmBtnRef = useRef<HTMLButtonElement>(null);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      titleId={titleId}
      descriptionId={descId}
      triggerRef={triggerRef}
      initialFocusRef={confirmBtnRef}
    >
      <p
        id={descId}
        className="text-sm text-graphite mb-6"
      >
        {description}
      </p>
      {error && (
        <p role="alert" className="text-sm text-[#8B0000] mb-4">
          {error}
        </p>
      )}
      <div className="flex gap-3 justify-end">
        <Button
          ref={confirmBtnRef}
          variant={confirmVariant}
          onClick={onConfirm}
          disabled={isLoading}
          aria-busy={isLoading}
        >
          {isLoading ? "Please wait..." : confirmLabel}
        </Button>
        <Button variant="secondary" onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
      </div>
    </Modal>
  );
}
