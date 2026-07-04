import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function truncate(str: string, length: number): string {
  return str.length > length ? str.slice(0, length) + "..." : str;
}

export function extractTitle(html: string | null): string {
  if (!html) return "(Generating…)";
  const snippet = html.slice(0, 2000);
  const match = snippet.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  if (!match) return "(Untitled)";
  const text = match[1].replace(/<[^>]+>/g, "").trim();
  return text.length > 60 ? text.slice(0, 60) + "…" : text || "(Untitled)";
}
