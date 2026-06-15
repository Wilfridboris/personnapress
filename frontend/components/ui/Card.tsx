import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { HTMLAttributes } from "react";

type CardVariant = "default" | "active";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
}

export function Card({ variant = "default", className, children, ...props }: CardProps) {
  return (
    <div
      className={twMerge(
        clsx(
          "rounded-none transition-shadow duration-150",
          variant === "default" && [
            "bg-white border border-border",
            "hover:shadow-[4px_4px_0px_#111111]",
          ],
          variant === "active" && [
            "bg-highlighter border border-ink",
            "shadow-[4px_4px_0px_#111111]",
          ],
          className
        )
      )}
      {...props}
    >
      {children}
    </div>
  );
}
