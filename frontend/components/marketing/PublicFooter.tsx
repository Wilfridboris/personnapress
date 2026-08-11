import Link from "next/link";
import Image from "next/image";
import { CopyrightYear } from "./CopyrightYear";
import { PlatformIcon } from "@/components/ui/PlatformIcon";

export function PublicFooter() {
  return (
    <footer className="border-t border-border">
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex flex-col md:flex-row gap-10 md:gap-16">

          {/* Logo */}
          <div className="shrink-0">
            <Link href="/" aria-label="PersonnaPress home">
              <Image
                src="/images/PersonnaPress-logo.png"
                alt="PersonnaPress"
                width={128}
                height={128}
                className="h-7 w-auto"
              />
            </Link>
          </div>

          {/* Nav columns — 2-up grid on mobile, flex-wrap from sm */}
          <nav
            aria-label="Footer navigation"
            className="grid grid-cols-2 gap-8 sm:flex sm:flex-wrap sm:gap-10 md:gap-16 flex-1"
          >

            {/* Company */}
            <div className="flex flex-col gap-3">
              <p className="font-mono text-[10px] uppercase tracking-widest text-graphite/50">Company</p>
              <Link href="/about" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">About</Link>
            </div>

            {/* Product */}
            <div className="flex flex-col gap-3">
              <p className="font-mono text-[10px] uppercase tracking-widest text-graphite/50">Product</p>
              <a href="/#workflow" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">How it works</a>
              <a href="/#platforms" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Platforms</a>
              <a href="/#pricing" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Pricing</a>
              <Link href="/github-publisher" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">GitHub Publisher</Link>
              <Link href="/headless-blog-api" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Headless Blog API</Link>
              <Link href="/headless-blog-api/docs" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">API Docs</Link>
              <a href="/#faq" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">FAQ</a>
            </div>

            {/* Resources */}
            <div className="flex flex-col gap-3">
              <p className="font-mono text-[10px] uppercase tracking-widest text-graphite/50">Resources</p>
              <Link href="/blog" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Blog</Link>
              <Link
                href="/blog/how-to-use-ai-to-write-blog-posts"
                className="font-mono text-xs text-graphite hover:text-ink transition-colors leading-snug focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
              >
                How to use AI to write blog posts
              </Link>
            </div>

            {/* Account */}
            <div className="flex flex-col gap-3">
              <p className="font-mono text-[10px] uppercase tracking-widest text-graphite/50">Account</p>
              <Link href="/dashboard" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Sign up</Link>
              <Link href="/login" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Log in</Link>
            </div>

          </nav>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-border mt-8 pt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
          <p className="font-mono text-xs text-graphite">
            &copy; <CopyrightYear /> PersonnaPress. All rights reserved.
          </p>
          <div className="flex flex-row items-center justify-between sm:contents gap-4">
            <nav aria-label="PersonnaPress social links" className="flex items-center gap-4">
              <a
                href="https://www.facebook.com/personnapress/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="PersonnaPress on Facebook"
                className="text-graphite hover:opacity-70 transition-opacity duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
              >
                <PlatformIcon platform="facebook_page" className="size-5" color="brand" aria-hidden="true" />
              </a>
            </nav>
            <nav className="flex items-center gap-4" aria-label="Legal">
              <Link href="/terms" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Terms of Service</Link>
              <span className="font-mono text-xs text-graphite/40" aria-hidden="true">&middot;</span>
              <Link href="/privacy" className="font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1">Privacy Policy</Link>
            </nav>
          </div>
        </div>
      </div>
    </footer>
  );
}
