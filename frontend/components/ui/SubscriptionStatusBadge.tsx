import { clsx } from "clsx";

type SubscriptionStatus = "trialing" | "active" | "canceled" | "past_due";

interface SubscriptionStatusBadgeProps {
  status: SubscriptionStatus;
  className?: string;
}

const STATUS_CONFIG: Record<SubscriptionStatus, { label: string; className: string }> = {
  trialing:  { label: "TRIALING",  className: "bg-highlighter text-ink" },
  active:    { label: "ACTIVE",    className: "bg-success/10 text-success" },
  canceled:  { label: "CANCELED",  className: "bg-danger/10 text-danger" },
  past_due:  { label: "PAST DUE", className: "bg-danger/10 text-danger" },
};

export function SubscriptionStatusBadge({ status, className }: SubscriptionStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  if (!config) return null;
  return (
    <span
      className={clsx(
        "inline-flex items-center",
        "px-2 py-0.5",
        "font-body text-xs font-medium",
        "uppercase tracking-wide",
        "rounded-[2px]",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
