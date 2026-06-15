"use client";

import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import {
  FormEvent,
  forwardRef,
  InputHTMLAttributes,
  TextareaHTMLAttributes,
  useRef,
  useEffect,
  useImperativeHandle,
} from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  variant?: "standard";
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ variant = "standard", className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={twMerge(
          clsx(
            "w-full bg-transparent",
            "border-0 border-b border-ink",
            "focus:border-b-2 focus:border-ink",
            "focus:outline-none focus:ring-0",
            "placeholder:text-graphite",
            "text-sm text-ink py-2",
            "transition-[border-width] duration-100",
            className
          )
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";

type BrainDumpProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onInput"> & {
  onInput?: (e: FormEvent<HTMLTextAreaElement>) => void;
};

export const BrainDumpInput = forwardRef<HTMLTextAreaElement, BrainDumpProps>(
  ({ className, onInput, ...props }, ref) => {
    const internalRef = useRef<HTMLTextAreaElement>(null);
    useImperativeHandle(ref, () => internalRef.current!, []);

    const handleInput = (e: FormEvent<HTMLTextAreaElement>) => {
      const el = e.currentTarget;
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
      onInput?.(e);
    };

    // Resize on mount
    useEffect(() => {
      const el = internalRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }, []);

    // Resize when controlled value changes
    const controlledValue = props.value ?? props.defaultValue;
    useEffect(() => {
      const el = internalRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }, [controlledValue]);

    return (
      <textarea
        ref={internalRef}
        onInput={handleInput}
        className={twMerge(
          clsx(
            "w-full bg-transparent",
            "border-0 border-b border-border",
            "focus:border-b-2 focus:border-border",
            "focus:outline-none focus:ring-0",
            "placeholder:text-graphite",
            "text-sm text-ink py-2",
            "font-mono",
            "min-h-[120px] resize-none overflow-hidden",
            className
          )
        )}
        {...props}
      />
    );
  }
);

BrainDumpInput.displayName = "BrainDumpInput";
