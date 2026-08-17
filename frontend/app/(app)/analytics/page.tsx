import type { Metadata } from "next";
import { AnalyticsDashboard } from "./AnalyticsDashboard";

export const metadata: Metadata = {
  title: "Analytics",
  robots: { index: false },
};

export default function AnalyticsPage() {
  return (
    <>
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold text-ink mb-1">
          Post Performance Analytics
        </h1>
        <p className="text-sm text-graphite font-mono">
          How your Meta posts are performing across Facebook, Instagram, and Threads.
        </p>
      </header>
      <AnalyticsDashboard />
    </>
  );
}
