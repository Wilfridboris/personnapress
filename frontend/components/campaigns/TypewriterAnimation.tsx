"use client";

import { useState, useEffect } from "react";

interface TypewriterAnimationProps {
  statusMessages: string[];
  currentMessageIndex: number;
  onMessageComplete?: () => void;
}

export function TypewriterAnimation({
  statusMessages,
  currentMessageIndex,
  onMessageComplete,
}: TypewriterAnimationProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [charIndex, setCharIndex] = useState(0);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  const message = statusMessages[currentMessageIndex] ?? "";

  // Detect prefers-reduced-motion on client only (avoids SSR mismatch)
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Reset character state when message changes
  useEffect(() => {
    setDisplayedText("");
    setCharIndex(0);
  }, [currentMessageIndex]);

  // Character-by-character reveal
  useEffect(() => {
    if (prefersReducedMotion) return;
    if (charIndex >= message.length) {
      // Fully revealed — hold 800ms then notify parent
      if (message.length > 0 && onMessageComplete) {
        const holdTimer = setTimeout(onMessageComplete, 800);
        return () => clearTimeout(holdTimer);
      }
      return;
    }
    const timer = setTimeout(() => {
      setDisplayedText(message.slice(0, charIndex + 1));
      setCharIndex((c) => c + 1);
    }, 35);
    return () => clearTimeout(timer);
  }, [charIndex, message, prefersReducedMotion, onMessageComplete]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] bg-paper px-8 py-12">
      {prefersReducedMotion ? (
        <p className="font-mono text-sm text-graphite animate-pulse">Generating...</p>
      ) : (
        <p
          aria-hidden="true"
          className="font-mono text-sm text-graphite leading-[1.7] whitespace-pre"
        >
          {displayedText}
          <span className="animate-pulse">▌</span>
        </p>
      )}

      {/* Screen-reader status line — announces each new message */}
      <p
        role="status"
        aria-live="polite"
        className="sr-only"
      >
        {message}
      </p>
    </div>
  );
}
