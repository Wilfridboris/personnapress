import type { Metadata } from "next";
import { Suspense } from "react";
import { ContentCalendar } from "@/components/calendar/ContentCalendar";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata: Metadata = {
  title: "Content Calendar",
  robots: { index: false },
};

export default function CalendarPage() {
  return (
    <>
      <header className="mb-8">
        <h1 className="font-display text-3xl font-bold text-ink mb-1">
          Content Calendar
        </h1>
        <p className="text-sm text-graphite font-mono">
          Your publishing cadence at a glance.
        </p>
      </header>
      <Suspense fallback={<Skeleton className="h-[500px] w-full" />}>
        <ContentCalendar />
      </Suspense>
    </>
  );
}
