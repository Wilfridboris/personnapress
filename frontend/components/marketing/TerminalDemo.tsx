"use client";

import { useRef, useState, useEffect, Fragment } from "react";

const TERMINAL_TEXT = `$ personnapress detect wilfridboris/my-blog
Scanning repository...
  ✓ Found _config.yml
  ✓ Found _posts/ (14 posts)
  ✓ Detected: Jekyll

Target file: _posts/2026-07-09-how-i-built-this.md
Front matter: title, date, categories, description

Ready to publish via Pull Request.`;

function renderWithCheckmarks(text: string) {
  const parts = text.split("✓");
  return parts.map((part, i) => (
    <Fragment key={i}>
      {part}
      {i < parts.length - 1 && (
        <span className="text-success font-bold">{"✓"}</span>
      )}
    </Fragment>
  ));
}

export function TerminalDemo() {
  const ref = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const prefersReduced =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
        : false;
    if (prefersReduced) {
      const id = setTimeout(() => setVisibleCount(TERMINAL_TEXT.length), 0);
      return () => clearTimeout(id);
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [started]);

  useEffect(() => {
    if (!started || visibleCount >= TERMINAL_TEXT.length) return;
    const id = setTimeout(() => setVisibleCount((n) => n + 1), 18);
    return () => clearTimeout(id);
  }, [started, visibleCount]);

  const visible = TERMINAL_TEXT.slice(0, visibleCount);

  return (
    <section
      aria-label="Terminal demo"
      className="bg-paper px-6 py-20"
    >
      <h2 className="font-display font-bold text-3xl text-ink text-center mb-10">
        See it work
      </h2>
      <div ref={ref} className="max-w-[640px] mx-auto">
        <div
          className="bg-ink border border-border"
          style={{ borderRadius: 0 }}
        >
          {/* Traffic lights — decorative */}
          <div
            className="flex gap-2 px-4 py-3 border-b border-border"
            aria-hidden="true"
          >
            <span
              className="w-[10px] h-[10px] rounded-full bg-danger"
              style={{ display: "inline-block" }}
            />
            <span
              className="w-[10px] h-[10px] rounded-full bg-highlighter"
              style={{ display: "inline-block" }}
            />
            <span
              className="w-[10px] h-[10px] rounded-full bg-success"
              style={{ display: "inline-block" }}
            />
          </div>
          {/* Content area */}
          <pre
            className="font-mono text-[13px] text-white p-6 leading-[1.7] whitespace-pre-wrap break-words"
            aria-label="Terminal output showing PersonnaPress detecting a Jekyll blog repository"
          >
            {renderWithCheckmarks(visible)}
            {visibleCount < TERMINAL_TEXT.length && (
              <span className="text-white animate-[cursor-blink_1s_step-end_infinite]">
                |
              </span>
            )}
          </pre>
        </div>
      </div>
    </section>
  );
}
