import Link from "next/link";
import { ArrowRight, Check, X, RefreshCw, FileText, Share2, Search } from "lucide-react";
import { FaqAccordion } from "@/app/_components/FaqAccordion";
import type { ComparisonPageData, ComparisonValue } from "./comparisons.data";

type LucideIcon = React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;

const ICON_MAP: Record<string, LucideIcon> = {
  RefreshCw,
  FileText,
  Share2,
  Search,
};

function ComparisonCell({ value }: { value: ComparisonValue }) {
  if (value === "yes") return <Check className="size-4 text-success mx-auto" aria-label="Yes" />;
  if (value === "no") return <X className="size-4 text-danger mx-auto" aria-label="No" />;
  return (
    <span className="font-mono text-xs text-graphite" aria-label="Partial support">
      partial
    </span>
  );
}

export function ComparisonPage({ data }: { data: ComparisonPageData }) {
  return (
    <main className="-mt-8 -mx-4">
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-12 md:pt-24 pb-16 md:pb-20">
        <div className="max-w-3xl">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
            {data.competitorName} Alternatives
          </p>
          <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
            {data.metadata.title.split(" | ")[0]}
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
              href="#comparison"
              className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
            >
              See the comparison
            </a>
          </div>
          <p className="font-mono text-xs text-graphite mt-6">
            14-day free trial. No credit card required.
          </p>
        </div>
      </section>

      <div className="border-t border-border" />

      {/* Verdict */}
      <section className="max-w-6xl mx-auto px-6 py-16" aria-label="Short answer">
        <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">The Short Answer</p>
        <blockquote className="border-l-4 border-ink pl-8 py-2 max-w-3xl">
          <p className="font-display text-2xl font-bold text-ink text-balance leading-snug">
            {data.verdict}
          </p>
        </blockquote>
      </section>

      <div className="border-t border-border" />

      {/* Comparison table */}
      <section
        id="comparison"
        className="max-w-6xl mx-auto px-6 py-20"
        aria-label={`PersonnaPress vs ${data.competitorName} comparison`}
      >
        <header className="mb-14">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Feature Comparison</p>
          <h2 className="font-display text-4xl font-bold text-ink text-balance">
            PersonnaPress vs {data.competitorName}
          </h2>
          <p className="text-graphite max-w-xl mt-4 leading-relaxed text-pretty">{data.pricingNote}</p>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border border-border max-w-2xl">
            <caption className="sr-only">
              PersonnaPress vs {data.competitorName} feature comparison
            </caption>
            <thead>
              <tr className="bg-ink">
                <th
                  scope="col"
                  className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-6 py-4 border border-ink text-left"
                >
                  Feature
                </th>
                <th
                  scope="col"
                  className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-6 py-4 border border-ink text-center"
                >
                  PersonnaPress
                </th>
                <th
                  scope="col"
                  className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-6 py-4 border border-ink text-center"
                >
                  {data.competitorName}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.comparisonRows.map((row) => (
                <tr key={row.feature} className="group hover:bg-highlight transition-colors">
                  <th
                    scope="row"
                    className="font-body text-sm text-ink px-6 py-4 border border-border text-left font-normal"
                  >
                    {row.feature}
                    {row.competitorWin && (
                      <span className="ml-2 font-mono text-[10px] text-graphite/60 tracking-widest uppercase">
                        competitor advantage
                      </span>
                    )}
                  </th>
                  <td className="border border-border px-6 py-4 text-center">
                    <ComparisonCell value={row.personnapress} />
                  </td>
                  <td className="border border-border px-6 py-4 text-center">
                    <ComparisonCell value={row.competitor} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="border-t border-border" />

      {/* Where competitor wins */}
      <section
        className="max-w-6xl mx-auto px-6 py-20"
        aria-label={`Where ${data.competitorName} is the better choice`}
      >
        <header className="mb-10">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Fair Assessment</p>
          <h2 className="font-display text-4xl font-bold text-ink text-balance">
            Where {data.competitorName} is the better choice
          </h2>
        </header>
        <ul className="space-y-4 max-w-2xl">
          {data.competitorStrengths.map((strength) => (
            <li key={strength} className="flex items-start gap-4 border border-border p-6">
              <Check className="size-4 text-ink mt-0.5 shrink-0" aria-hidden={true} />
              <p className="font-body text-sm text-graphite leading-relaxed">{strength}</p>
            </li>
          ))}
        </ul>
        <p className="font-mono text-xs text-graphite mt-8 max-w-2xl">
          Source:{" "}
          <a
            href={data.competitorUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink"
          >
            {data.competitorUrl.replace("https://", "")}
          </a>
          . As of September 2026, check current features at their site.
        </p>
      </section>

      <div className="border-t border-border" />

      {/* Why founders switch */}
      <section className="max-w-6xl mx-auto px-6 py-20" aria-label="Why founders switch to PersonnaPress">
        <header className="mb-14">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Why Founders Switch</p>
          <h2 className="font-display text-4xl font-bold text-ink text-balance">
            The PersonnaPress difference
          </h2>
        </header>
        <ol role="list" className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border list-none">
          {data.differentiators.map(({ iconName, title, description }, i) => {
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
            Questions about PersonnaPress vs {data.competitorName}
          </h2>
        </header>
        <FaqAccordion items={data.faqItems} />
      </section>

      <div className="border-t border-border" />

      {/* Related links */}
      <section className="max-w-6xl mx-auto px-6 py-12" aria-label="Related comparisons">
        <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Also Compare</p>
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

      {/* Highlighter CTA */}
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
