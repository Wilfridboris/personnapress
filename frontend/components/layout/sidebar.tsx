"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  FileText,
  Plus,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/campaigns", label: "Campaigns", icon: FileText },
  { href: "/clients", label: "Clients", icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 h-screen border-r border-border bg-paper flex flex-col sticky top-0 shrink-0">
      {/* Logo */}
      <div className="h-16 px-6 flex items-center border-b border-border">
        <Link href="/" className="font-display text-lg font-bold text-ink tracking-tight">
          PersonaPress
        </Link>
      </div>

      {/* Quick action */}
      <div className="p-4 border-b border-border">
        <Link
          href="/campaigns/new"
          className={cn(
            "flex items-center justify-center gap-2 w-full py-2.5 text-sm font-medium",
            "bg-ink text-paper hover:bg-graphite transition-colors"
          )}
        >
          <Plus className="size-4" aria-hidden="true" />
          New Campaign
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5" aria-label="Main navigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-ink text-paper"
                  : "text-graphite hover:text-ink hover:bg-ink/5"
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="p-3 border-t border-border">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors",
            pathname === "/settings"
              ? "bg-ink text-paper"
              : "text-graphite hover:text-ink hover:bg-ink/5"
          )}
        >
          <Settings className="size-4 shrink-0" aria-hidden="true" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
