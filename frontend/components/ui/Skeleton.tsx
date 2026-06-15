import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={twMerge(
        clsx(
          "relative overflow-hidden",
          "bg-border rounded-none",
          "animate-pulse",
          className
        )
      )}
      aria-hidden="true"
    />
  );
}
