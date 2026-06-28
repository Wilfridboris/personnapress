"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useUIStore } from "@/lib/stores/useUIStore";
import { Sidebar } from "./sidebar";
import { MobileTopBar } from "./MobileTopBar";
import { MobileDrawer } from "./MobileDrawer";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const closeMobileDrawer = useUIStore((s) => s.closeMobileDrawer);

  useEffect(() => {
    closeMobileDrawer();
  }, [pathname, closeMobileDrawer]);

  return (
    <div className="min-h-screen bg-[#F9F9F6]">
      <Sidebar />
      <MobileTopBar />
      <MobileDrawer />
      <main className="md:ml-14 lg:ml-60 pt-14 lg:pt-0 min-h-screen">
        <div className="max-w-[720px] px-8 lg:px-12 py-8 mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
