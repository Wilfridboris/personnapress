import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";

export function PublicHeader() {
  return (
    <header className="border-b border-border sticky top-0 bg-paper z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" aria-label="PersonnaPress home">
          <Image
            src="/images/PersonnaPress-logo.png"
            alt="PersonnaPress"
            width={128}
            height={128}
            priority
            className="h-8 w-auto"
          />
        </Link>
        <nav aria-label="Main navigation" className="flex items-center gap-8">
          <a href="/#workflow" className="text-sm text-graphite hover:text-ink transition-colors">How it works</a>
          <a href="/#platforms" className="text-sm text-graphite hover:text-ink transition-colors">Platforms</a>
          <a href="/#pricing" className="text-sm text-graphite hover:text-ink transition-colors">Pricing</a>
          <a href="/#faq" className="text-sm text-graphite hover:text-ink transition-colors">FAQ</a>
          <Link href="/blog" className="text-sm text-graphite hover:text-ink transition-colors">Blog</Link>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-ink text-paper text-sm font-medium px-5 py-2 hover:bg-graphite transition-colors"
          >
            Start Free Trial
            <ArrowRight className="size-3.5" aria-hidden="true" />
          </Link>
        </nav>
      </div>
    </header>
  );
}
