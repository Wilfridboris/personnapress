import { clsx } from "clsx";
import type { CampaignStatus } from "@/lib/types";

type BadgeVariant = CampaignStatus | "pr_open";

interface StatusBadgeProps {
  status: BadgeVariant;
  className?: string;
}

const STATUS_CONFIG: Record<BadgeVariant, { label: string; className: string }> = {
  pending_approval: {
    label: "PENDING APPROVAL",
    className: "bg-highlighter border-ink text-ink",
  },
  approved: {
    label: "APPROVED",
    className: "bg-border border-border text-graphite",
  },
  published: {
    label: "PUBLISHED",
    className: "bg-success border-transparent text-white",
  },
  rejected: {
    label: "REJECTED",
    className: "bg-transparent border-border text-graphite line-through",
  },
  failed: {
    label: "FAILED",
    className: "bg-danger border-transparent text-white",
  },
  pr_open: {
    label: "PR OPEN",
    className: "bg-white border-[#E5E5E5] text-graphite",
  },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  if (!config) return null;
  return (
    <span
      className={clsx(
        "inline-flex items-center",
        "border px-2 py-0.5",
        "font-body text-[0.75rem] font-medium",
        "tracking-[0.06em] uppercase",
        "rounded-[2px]",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
