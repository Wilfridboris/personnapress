"use client";

import { useEffect } from "react";
import { X, Newspaper, Plug } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores/useUIStore";
import { useClientStore } from "@/lib/stores/useClientStore";
import { ClientSwitcher } from "./ClientSwitcher";
import { NavItem } from "./NavItem";
import { NAV_ITEMS, ACCOUNT_NAV_ITEM } from "./nav-items";

export function MobileDrawer() {
  const isOpen = useUIStore((s) => s.isMobileDrawerOpen);
  const close = useUIStore((s) => s.closeMobileDrawer);
  const { activeClientId } = useClientStore();
  const calendarIdx = NAV_ITEMS.findIndex((item) => item.label === "Calendar");

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen, close]);

  return (
    <>
      <div
        aria-hidden="true"
        onClick={close}
        className={cn(
          "lg:hidden fixed inset-0 z-40 bg-[#111111]/40 transition-opacity duration-200 motion-reduce:transition-none",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        tabIndex={-1}
        className={cn(
          "lg:hidden fixed top-0 left-0 bottom-0 z-50 w-[280px] flex flex-col",
          "bg-[#F9F9F6] border-r border-[#E5E5E5]",
          "transition-transform duration-200 ease-out motion-reduce:transition-none",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between h-14 px-4 border-b border-[#E5E5E5] shrink-0">
          <span className="font-display font-bold text-[#111111] text-lg">
            PersonnaPress
          </span>
          <button
            type="button"
            onClick={close}
            aria-label="Close navigation"
            className="flex items-center justify-center w-11 h-11 text-[#111111] hover:bg-[#FFF1B8] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <ClientSwitcher />
        <nav aria-label="Navigation" className="flex-1 overflow-y-auto py-2">
          {NAV_ITEMS.slice(0, calendarIdx).map((item) => (
            <NavItem key={item.href} {...item} onClick={close} forceLabel />
          ))}
          {activeClientId && (
            <NavItem
              href="/articles"
              label="Articles"
              icon={Newspaper}
              onClick={close}
              forceLabel
            />
          )}
          {activeClientId && (
            <NavItem
              href={`/clients/${activeClientId}/connections`}
              label="Connections"
              icon={Plug}
              onClick={close}
              forceLabel
            />
          )}
          {NAV_ITEMS.slice(calendarIdx).map((item) => (
            <NavItem key={item.href} {...item} onClick={close} forceLabel />
          ))}
        </nav>
        <div className="border-t border-[#E5E5E5] shrink-0">
          <NavItem {...ACCOUNT_NAV_ITEM} onClick={close} forceLabel />
        </div>
      </div>
    </>
  );
}
