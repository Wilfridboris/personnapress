import Link from "next/link";
import Image from "next/image";
import { CopyrightYear } from "./CopyrightYear";

export function PublicFooter() {
  return (
    <footer className="border-t border-border">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <Link href="/" aria-label="PersonnaPress home">
            <Image
              src="/images/PersonnaPress-logo.png"
              alt="PersonnaPress"
              width={128}
              height={128}
              className="h-7 w-auto"
            />
          </Link>
          <nav aria-label="Footer navigation" className="flex flex-wrap gap-6">
            <a href="/#workflow" className="font-mono text-xs text-graphite hover:text-ink transition-colors">How it works</a>
            <a href="/#platforms" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Platforms</a>
            <a href="/#pricing" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Pricing</a>
            <Link href="/blog" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Blog</Link>
            <Link href="/github-publisher" className="font-mono text-xs text-graphite hover:text-ink transition-colors">GitHub Publisher</Link>
            <Link href="/headless-blog-api" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Headless Blog API</Link>
            <a href="/#faq" className="font-mono text-xs text-graphite hover:text-ink transition-colors">FAQ</a>
            <Link href="/dashboard" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Sign up</Link>
            <Link href="/login" className="font-mono text-xs text-graphite hover:text-ink transition-colors">Log in</Link>
          </nav>
        </div>
        <div className="border-t border-border mt-6 pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <p className="font-mono text-xs text-graphite">
            &copy; <CopyrightYear /> PersonnaPress. All rights reserved.
          </p>
          <nav className="flex items-center gap-4" aria-label="Legal">
            <Link href="/terms" className="font-mono text-xs text-graphite hover:text-ink transition-colors">
              Terms of Service
            </Link>
            <span className="font-mono text-xs text-graphite/40" aria-hidden="true">&middot;</span>
            <Link href="/privacy" className="font-mono text-xs text-graphite hover:text-ink transition-colors">
              Privacy Policy
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
