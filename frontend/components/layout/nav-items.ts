import { LayoutDashboard, Users, Calendar, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItemConfig {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItemConfig[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/clients",   label: "Clients",   icon: Users },
  { href: "/calendar",  label: "Calendar",  icon: Calendar },
];

export const ACCOUNT_NAV_ITEM: NavItemConfig = {
  href: "/account",
  label: "Account",
  icon: Settings,
};
