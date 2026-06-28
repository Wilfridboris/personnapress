"use client";

import { Menu } from "lucide-react";
import { useUIStore } from "@/lib/stores/useUIStore";

export function MobileTopBar() {
  const openMobileDrawer = useUIStore((s) => s.openMobileDrawer);

  return (
    <header className="flex lg:hidden items-center h-14 fixed top-0 left-0 right-0 z-40 bg-[#F9F9F6] border-b border-[#E5E5E5] px-4 gap-4">
      <span className="font-display font-bold text-[#111111] text-lg shrink-0">
        PP
      </span>
      <span className="flex-1 text-sm text-[#555555] truncate text-center" />
      <button
        type="button"
        onClick={openMobileDrawer}
        aria-label="Open navigation"
        className="flex items-center justify-center w-11 h-11 shrink-0 text-[#111111] hover:bg-[#FFF1B8] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]"
      >
        <Menu className="w-5 h-5" aria-hidden="true" />
      </button>
    </header>
  );
}
