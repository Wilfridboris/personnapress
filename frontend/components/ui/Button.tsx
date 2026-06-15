"use client";

import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const variants: Record<Variant, string> = {
  primary: [
    "bg-ink text-white border border-transparent",
    "shadow-[4px_4px_0px_#111111]",
    "hover:bg-white hover:text-ink hover:border-ink hover:shadow-none",
    "disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none",
  ].join(" "),
  secondary: [
    "bg-transparent text-ink border border-ink",
    "hover:bg-ink hover:text-white",
    "disabled:opacity-40 disabled:cursor-not-allowed",
  ].join(" "),
  danger: [
    "bg-danger text-white",
    "hover:opacity-85",
    "disabled:opacity-40 disabled:cursor-not-allowed",
  ].join(" "),
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", className, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={twMerge(
          clsx(
            "inline-flex items-center justify-center gap-2",
            "rounded-none px-[1.25rem] py-[0.625rem]",
            "text-sm font-medium",
            "transition-all duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
            variants[variant],
            className
          )
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
