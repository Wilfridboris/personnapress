"use client";

import { ClientSwitcher } from "./ClientSwitcher";
import { NavItem } from "./NavItem";
import { NAV_ITEMS, ACCOUNT_NAV_ITEM } from "./nav-items";

export function Sidebar() {
  return (
    <aside
      aria-label="Sidebar"
      className="hidden md:flex flex-col h-screen fixed left-0 top-0 z-40 w-14 lg:w-60 bg-[#F9F9F6] border-r border-[#E5E5E5]"
    >
      <ClientSwitcher />
      <nav
        aria-label="Main navigation"
        className="flex-1 overflow-y-auto py-2"
      >
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.href} {...item} />
        ))}
      </nav>
      <div className="border-t border-[#E5E5E5] shrink-0">
        <NavItem {...ACCOUNT_NAV_ITEM} />
      </div>
    </aside>
  );
}
