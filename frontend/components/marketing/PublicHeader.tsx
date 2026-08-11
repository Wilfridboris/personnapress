'use client';

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Menu, X } from "lucide-react";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/#workflow", label: "How it works" },
  { href: "/#platforms", label: "Platforms" },
  { href: "/pricing", label: "Pricing" },
  { href: "/#faq", label: "FAQ" },
  { href: "/blog", label: "Blog" },
  { href: "/about", label: "About" },
];

export function PublicHeader() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setIsOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen]);

  useEffect(() => {
    document.body.style.overflow = isOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [isOpen]);

  const close = () => setIsOpen(false);

  return (
    <>
      <header className="border-b border-border sticky top-0 bg-paper z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" aria-label="PersonnaPress home">
            <Image
              src="/images/PersonnaPress-logo.png"
              alt="PersonnaPress"
              width={128}
              height={128}
              priority
              loading="eager"
              className="h-8 w-auto"
            />
          </Link>

          {/* Desktop nav */}
          <nav aria-label="Main navigation" className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map(({ href, label }) => (
              <a
                key={href}
                href={href}
                className="text-sm text-graphite hover:text-ink transition-colors"
              >
                {label}
              </a>
            ))}
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-2 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Start Free Trial
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </nav>

          {/* Mobile hamburger */}
          <button
            type="button"
            onClick={() => setIsOpen((v) => !v)}
            aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={isOpen}
            aria-controls="mobile-nav"
            className="md:hidden flex items-center justify-center size-11 -mr-2 text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
          >
            {isOpen
              ? <X className="size-5" aria-hidden="true" />
              : <Menu className="size-5" aria-hidden="true" />
            }
          </button>
        </div>

        {/* Mobile nav panel */}
        <div
          id="mobile-nav"
          aria-hidden={!isOpen}
          className={[
            "md:hidden border-t border-border bg-paper overflow-hidden",
            "transition-[max-height,opacity] duration-300 ease-in-out",
            isOpen ? "max-h-screen opacity-100" : "max-h-0 opacity-0",
          ].join(" ")}
        >
          <nav
            aria-label="Mobile navigation"
            className="max-w-6xl mx-auto px-6 py-4 flex flex-col"
          >
            {NAV_LINKS.map(({ href, label }) => (
              <a
                key={href}
                href={href}
                onClick={close}
                className="text-sm text-graphite hover:text-ink transition-colors py-3.5 border-b border-border last:border-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                {label}
              </a>
            ))}
            <Link
              href="/dashboard"
              onClick={close}
              className="inline-flex items-center justify-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-3 hover:bg-graphite transition-colors mt-5 mb-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Start Free Trial
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </nav>
        </div>
      </header>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-ink/10 md:hidden"
          onClick={close}
          aria-hidden="true"
        />
      )}
    </>
  );
}
