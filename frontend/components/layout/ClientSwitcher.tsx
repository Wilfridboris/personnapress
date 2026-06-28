"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface Client {
  id: string;
  name: string;
}

interface ClientSwitcherProps {
  clients?: Client[];
  activeClientId?: string;
}

export function ClientSwitcher({ clients = [], activeClientId }: ClientSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

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
      if (e.key === "Escape") setIsOpen(false);
    }

    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
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
        <span className="hidden lg:block flex-1 text-sm font-medium text-[#111111] truncate text-left">
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
          className="absolute top-full left-0 z-50 min-w-[200px] w-full lg:w-56 bg-[#F9F9F6] border border-[#E5E5E5] shadow-[4px_4px_0px_#111111] py-1"
        >
          {clients.length === 0 ? (
            <div className="px-4 py-3 text-sm font-mono text-[#555555]">
              No clients yet.{" "}
              <Link
                href="/clients/new"
                className="text-[#111111] underline hover:no-underline"
                onClick={() => setIsOpen(false)}
              >
                Add one
              </Link>
            </div>
          ) : (
            clients.map((client) => {
              const isSelected = client.id === activeClientId;
              return (
                <button
                  key={client.id}
                  role="option"
                  aria-selected={isSelected}
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-left hover:bg-[#FFF1B8] transition-colors"
                >
                  <Check
                    className={cn(
                      "w-4 h-4 shrink-0",
                      isSelected ? "opacity-100" : "opacity-0"
                    )}
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
