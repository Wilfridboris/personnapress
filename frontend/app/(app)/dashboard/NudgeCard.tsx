"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export function NudgeCard() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard", { scroll: false });
  }, [router]);

  return (
    <div className="bg-white border border-[#E5E5E5] p-6 mb-8 flex items-center justify-between">
      <p className="text-sm text-[#111111] font-sans">Complete your first campaign.</p>
      <Link
        href="/campaigns/new"
        className="inline-flex items-center gap-2 bg-transparent text-[#111111] border border-[#111111] text-sm font-medium px-4 py-2 hover:bg-[#111111] hover:text-white transition-colors"
      >
        New Campaign
        <ArrowRight className="size-4" aria-hidden="true" />
      </Link>
    </div>
  );
}
