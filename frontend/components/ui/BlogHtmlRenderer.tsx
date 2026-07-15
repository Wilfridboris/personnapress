"use client";

import { useEffect, useState } from "react";
import { _DOMPURIFY_CONFIG } from "@/components/campaigns/BlogEditor";
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
        setSafeHtml(DOMPurify.sanitize(html, _DOMPURIFY_CONFIG));
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
