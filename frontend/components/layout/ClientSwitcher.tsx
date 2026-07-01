"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useClientStore } from "@/lib/stores/useClientStore";

export function ClientSwitcher() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const clients = useClientStore((s) => s.clients);
  const activeClientId = useClientStore((s) => s.activeClientId);
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
    router.push("/dashboard");
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
          {activeClient ? activeClient.name : "No client"}
        </span>
        <ChevronDown
          className={cn(
            "hidden lg:block shrink-0 w-4 h-4 text-[#555555] transition-transform duration-150",
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
            clients.map((client) => {
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
                    className={cn("w-4 h-4 shrink-0", isActive ? "opacity-100" : "opacity-0")}
                    aria-hidden="true"
                  />
                  <span className="truncate">{client.name}</span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
