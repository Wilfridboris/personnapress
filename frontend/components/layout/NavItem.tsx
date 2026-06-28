"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItemProps {
  href: string;
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
  forceLabel?: boolean;
}

export function NavItem({ href, label, icon: Icon, onClick, forceLabel }: NavItemProps) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(href + "/");

  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex items-center gap-3 min-h-[44px] px-3 text-sm transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]",
        active
          ? "bg-[#FFF1B8] border-l-2 border-[#111111] text-[#111111] font-medium pl-[calc(0.75rem-2px)]"
          : "border-l-2 border-transparent text-[#555555] hover:bg-[#FFF1B8] hover:text-[#111111]"
      )}
    >
      <Icon
        className={cn(
          "shrink-0 w-[18px] h-[18px]",
          active
            ? "text-[#111111]"
            : "text-[#555555] group-hover:text-[#111111]"
        )}
        aria-hidden="true"
      />
      <span className={cn("truncate", forceLabel ? "block" : "hidden lg:block")}>
        {label}
      </span>
      {!forceLabel && (
        <span
          role="tooltip"
          className="lg:hidden absolute left-full ml-2 px-2 py-1 bg-[#111111] text-[#F9F9F6] text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none whitespace-nowrap z-50"
        >
          {label}
        </span>
      )}
    </Link>
  );
}
