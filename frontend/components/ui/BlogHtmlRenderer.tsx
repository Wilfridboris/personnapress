"use client";

import { useEffect, useState } from "react";
import { Skeleton } from "./Skeleton";

interface Props {
  html: string;
  className?: string;
}

export function BlogHtmlRenderer({ html, className }: Props) {
  const [safeHtml, setSafeHtml] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setSafeHtml(null);

    import("dompurify")
      .then(({ default: DOMPurify }) => {
        if (cancelled) return;
        setSafeHtml(
          DOMPurify.sanitize(html, {
            ALLOWED_TAGS: [
              "h1", "h2", "h3", "h4", "p", "ul", "ol", "li",
              "strong", "em", "a", "br", "blockquote", "code", "pre",
            ],
            ALLOWED_ATTR: ["href", "title", "rel"],
            FORBID_ATTR: ["target"],
          })
        );
      })
      .catch(() => {
        if (!cancelled) setSafeHtml("");
      });

    return () => {
      cancelled = true;
    };
  }, [html]);

  if (safeHtml === null) return <Skeleton className={className} />;

  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: safeHtml }}
    />
  );
}
