import Link from "next/link";
import { ArrowRight, RefreshCw, FileText, Share2, Search } from "lucide-react";
import { FaqAccordion } from "@/app/_components/FaqAccordion";
import type { PersonaPageData } from "./personas.data";

type LucideIcon = React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;

const ICON_MAP: Record<string, LucideIcon> = {
  RefreshCw,
  FileText,
  Share2,
  Search,
};

export function PersonaPage({ data }: { data: PersonaPageData }) {
  return (
    <main className="-mt-8 -mx-4">
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-12 md:pt-24 pb-16 md:pb-20">
        <div className="max-w-3xl">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
            {data.persona}
          </p>
          <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
            {data.h1}
          </h1>
          <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
            {data.heroAnswer}
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
            >
              Try PersonnaPress free
              <ArrowRight className="size-4" aria-hidden={true} />
            </Link>
            <a
              href="#how-it-helps"
              className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
            >
              See how it helps
            </a>
          </div>
          <p className="font-mono text-xs text-graphite mt-6">
            14-day free trial. No credit card required.
          </p>
        </div>
      </section>

      <div className="border-t border-border" />

      {/* Pains */}
      <section className="max-w-6xl mx-auto px-6 py-20" aria-label="Common challenges">
        <header className="mb-14">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">The Problem</p>
          <h2 className="font-display text-4xl font-bold text-ink text-balance">
            {data.painsHeading}
          </h2>
        </header>
        <ul role="list" className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border list-none">
          {data.pains.map(({ title, description }, i) => (
            <li key={title} className="bg-paper p-8">
              <span className="font-mono text-xs text-graphite uppercase tracking-widest mb-6 block">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">{title}</h3>
              <p className="text-sm text-graphite leading-relaxed text-pretty">{description}</p>
            </li>
          ))}
        </ul>
      </section>

      <div className="border-t border-border" />

      {/* Solutions */}
      <section
        id="how-it-helps"
        className="max-w-6xl mx-auto px-6 py-20"
        aria-label="How PersonnaPress helps"
      >
        <header className="mb-14">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">How PersonnaPress Helps</p>
          <h2 className="font-display text-4xl font-bold text-ink text-balance">
            {data.solutionsHeading}
          </h2>
        </header>
        <ol role="list" className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border list-none">
          {data.solutions.map(({ iconName, title, description }, i) => {
            const Icon: LucideIcon = ICON_MAP[iconName] ?? ArrowRight;
            return (
              <li key={title} className="bg-paper p-8 group hover:bg-highlight transition-colors">
                <div className="flex items-start justify-between mb-6">
                  <span className="font-mono text-xs text-graphite uppercase tracking-widest">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <Icon className="size-5 text-graphite group-hover:text-ink transition-colors" aria-hidden={true} />
                </div>
                <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">{title}</h3>
                <p className="text-sm text-graphite leading-relaxed text-pretty">{description}</p>
              </li>
            );
          })}
        </ol>
      </section>

      <div className="border-t border-border" />

      {/* FAQ */}
      <section className="max-w-6xl mx-auto px-6 py-20" aria-label="Frequently asked questions">
        <header className="mb-14">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">FAQ</p>
          <h2 className="font-display text-4xl font-bold text-ink text-balance">
            Questions about PersonnaPress for {data.persona}
          </h2>
        </header>
        <FaqAccordion items={data.faqItems} />
      </section>

      <div className="border-t border-border" />

      {/* Related links */}
      <section className="max-w-6xl mx-auto px-6 py-12" aria-label="Related pages">
        <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Also See</p>
        <div className="flex flex-wrap gap-4">
          {data.relatedLinks.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="font-mono text-xs text-graphite underline underline-offset-2 hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
            >
              {label}
            </Link>
          ))}
        </div>
      </section>

      <div className="border-t border-border" />

      {/* CTA banner */}
      <section className="bg-highlighter px-6 py-24 text-center" aria-label="Get started with PersonnaPress">
        <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">Get Started</p>
        <h2 className="font-display font-bold text-4xl text-ink mb-4 text-balance max-w-xl mx-auto">
          Your idea to published post, in your voice.
        </h2>
        <p className="text-graphite max-w-xl mx-auto mb-8 leading-relaxed text-pretty">
          PersonnaPress writes the article and social posts in your brand voice, then publishes to your blog and
          channels. One loop, one approval.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
        >
          Start free, no credit card
          <ArrowRight className="size-4" aria-hidden={true} />
        </Link>
        <p className="font-mono text-xs text-graphite mt-6">14-day free trial. Starter from $29 / month.</p>
      </section>
    </main>
  );
}
