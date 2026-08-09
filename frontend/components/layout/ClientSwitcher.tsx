"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronDown, Check, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useClientStore } from "@/lib/stores/useClientStore";

// Top-level routes that are safe to stay on as-is when switching clients.
const SAFE_BASES = new Set(["/dashboard", "/articles", "/campaigns", "/calendar", "/clients", "/roadmap"]);
// Routes where a deep path (e.g. /campaigns/[id]) should collapse to the list on switch.
const COLLAPSE_TO_PARENT = new Set(["articles", "campaigns", "roadmap"]);

function getTargetPath(pathname: string, newClientId: string): string {
  const segments = pathname.split("/").filter(Boolean);
  const [first, second, third] = segments;

  if (!first) return "/dashboard";

  // /clients/[id] or /clients/[id]/connections|voice → swap in the new client ID.
  if (first === "clients" && second && second !== "new") {
    return third ? `/clients/${newClientId}/${third}` : `/clients/${newClientId}`;
  }

  // Creation forms are not client-specific — stay on the same path.
  if (second === "new" && !third) return `/${first}/new`;

  // /campaigns/[id] or /articles/[id] → the item belongs to the old client, go to the list.
  if (COLLAPSE_TO_PARENT.has(first) && second) return `/${first}`;

  const base = `/${first}`;
  return SAFE_BASES.has(base) ? base : "/dashboard";
}

export function ClientSwitcher() {
  const router = useRouter();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const clients = useClientStore((s) => s.clients);
  const activeClientId = useClientStore((s) => s.activeClientId);
  const isInitialized = useClientStore((s) => s.isInitialized);
  const planAtLimit = useClientStore((s) => s.planAtLimit);
  const clientLimit = useClientStore((s) => s.clientLimit);
  const setActiveClientId = useClientStore((s) => s.setActiveClientId);

  const activeClient = clients.find((c) => c.id === activeClientId);
  const initial = activeClient ? activeClient.name[0].toUpperCase() : "C";

  useEffect(() => {
    if (!isOpen) return;

    function handleMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function selectClient(id: string) {
    setActiveClientId(id);
    setIsOpen(false);
    router.push(getTargetPath(pathname, id));
  }

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Switch client"
        className={cn(
          "flex items-center w-full h-14 gap-2 border-b border-[#E5E5E5]",
          "hover:bg-[#FFF1B8] transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111]",
          "justify-center lg:justify-start lg:px-4"
        )}
      >
        <span className="w-[18px] h-[18px] bg-[#E5E5E5] flex items-center justify-center text-xs font-bold shrink-0">
          {initial}
        </span>
        <span className="hidden lg:block flex-1 text-sm font-medium text-[#111111] truncate text-left max-w-[160px]">
          {activeClient ? activeClient.name : isInitialized ? "No client" : ""}
        </span>
        <ChevronDown
          className={cn(
            "hidden lg:block shrink-0 size-4 text-[#555555] transition-transform duration-150",
            isOpen && "rotate-180"
          )}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <div
          role="listbox"
          aria-label="Client list"
          className="absolute top-full left-0 z-50 w-60 bg-[#F9F9F6] border border-[#111111] shadow-[4px_4px_0px_#111111] py-1"
        >
          {clients.length === 0 ? (
            <div className="px-3 py-2 text-sm text-[#555555]">
              No clients yet.{" "}
              <Link
                href="/clients/new"
                className="text-[#111111] underline hover:no-underline"
                onClick={() => setIsOpen(false)}
              >
                Create client
              </Link>
            </div>
          ) : (
            <>
              {clients.map((client) => {
                const isActive = client.id === activeClientId;
                return (
                  <button
                    key={client.id}
                    role="option"
                    aria-selected={isActive}
                    type="button"
                    onClick={() => selectClient(client.id)}
                    className={cn(
                      "flex items-center gap-2 w-full py-2 px-3 text-[0.9375rem] text-left transition-colors",
                      isActive
                        ? "bg-[#FFF1B8] text-[#111111] border-l-2 border-[#111111]"
                        : "text-[#555555] hover:bg-[#FFF1B8]"
                    )}
                  >
                    <Check
                      className={cn("size-4 shrink-0", isActive ? "opacity-100" : "opacity-0")}
                      aria-hidden="true"
                    />
                    <span className="truncate">{client.name}</span>
                  </button>
                );
              })}
              {!planAtLimit && (
                <div className="border-t border-border mt-1">
                  <Link
                    href="/clients/new"
                    onClick={() => setIsOpen(false)}
                    className="flex items-center gap-2 w-full py-2 px-3 text-[0.9375rem] text-graphite hover:bg-highlighter hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ink"
                  >
                    <Plus className="size-4 shrink-0" aria-hidden="true" />
                    <span>New client</span>
                  </Link>
                </div>
              )}
              {planAtLimit && (
                <div className="border-t border-border mt-1 px-3 py-2">
                  <p className="text-xs text-graphite">
                    {clients.length}/{clientLimit} clients &middot;{" "}
                    <Link
                      href="/account#choose-plan"
                      onClick={() => setIsOpen(false)}
                      className="text-ink underline hover:no-underline focus-visible:outline-none focus-visible:rounded-sm focus-visible:ring-2 focus-visible:ring-ink"
                    >
                      Upgrade plan
                    </Link>
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
