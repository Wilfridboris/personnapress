import type { Metadata } from "next";
import Link from "next/link";
import { CheckCircle2, X } from "lucide-react";

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com").replace(/\/$/, "");

export const metadata: Metadata = {
  title: "PersonnaPress Pricing — AI Content Automation Plans",
  description:
    "AI blog writer pricing starts at $29 per month. Three plans for individuals, growing businesses, and agencies. 14-day free trial, no credit card required.",
  robots: { index: true, follow: true },
  alternates: { canonical: `${APP_URL}/pricing` },
  openGraph: {
    title: "PersonnaPress Pricing — AI Content Automation Plans",
    description:
      "AI blog writer pricing starts at $29 per month. 14-day free trial included on all plans.",
    url: `${APP_URL}/pricing`,
    type: "website",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebPage",
  name: "PersonnaPress Pricing",
  description: "AI blog writer pricing starting at $29 per month.",
  url: `${APP_URL}/pricing`,
  breadcrumb: {
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: APP_URL },
      { "@type": "ListItem", position: 2, name: "Pricing", item: `${APP_URL}/pricing` },
    ],
  },
  offers: [
    { "@type": "Offer", name: "Starter", description: "For individuals getting started with AI content automation.", price: "29", priceCurrency: "USD" },
    { "@type": "Offer", name: "Growth", description: "For businesses that publish weekly.", price: "49", priceCurrency: "USD" },
    { "@type": "Offer", name: "Agency", description: "For agencies managing multiple client voices.", price: "149", priceCurrency: "USD" },
  ],
};

const COMPARISON_ROWS: { label: string; starter: boolean | string; growth: boolean | string; agency: boolean | string }[] = [
  { label: "Clients",                   starter: "2",    growth: "5",    agency: "20" },
  { label: "Campaigns per month",       starter: "10",   growth: "30",   agency: "Unlimited" },
  { label: "Image generations/month",   starter: "10",   growth: "30",   agency: "100" },
  { label: "WordPress publishing",      starter: true,   growth: true,   agency: true },
  { label: "X and LinkedIn",            starter: true,   growth: true,   agency: true },
  { label: "Brand voice profiles",      starter: true,   growth: true,   agency: true },
  { label: "Content calendar",          starter: true,   growth: true,   agency: true },
  { label: "Scheduled publishing",      starter: true,   growth: true,   agency: true },
  { label: "GitHub publishing",         starter: true,   growth: true,   agency: true },
  { label: "Headless blog API",         starter: true,   growth: true,   agency: true },
  { label: "Priority support",          starter: false,  growth: false,  agency: true },
];

const FAQ_ITEMS = [
  { q: "Is there a free trial?",            a: "All plans start with a 14-day free trial. No credit card is required to begin." },
  { q: "Can I change plans?",               a: "Yes. Upgrade or downgrade at any time from your account page. Upgrades take effect immediately. Downgrades apply at the start of your next billing cycle." },
  { q: "What happens when the trial ends?", a: "If you choose not to subscribe, your account enters read-only mode. Your content is safe for 30 days. Nothing is deleted immediately." },
  { q: "How does billing work?",            a: "All plans are billed monthly. Cancel any time from your account settings. There are no cancellation fees." },
];

function Cell({ value }: { value: boolean | string }) {
  if (typeof value === "boolean") {
    return value ? (
      <td className="px-4 py-3 text-center">
        <CheckCircle2 className="size-4 text-ink mx-auto" role="img" aria-label="Included" />
      </td>
    ) : (
      <td className="px-4 py-3 text-center">
        <X className="size-4 text-[#E5E5E5] mx-auto" role="img" aria-label="Not included" />
      </td>
    );
  }
  return <td className="px-4 py-3 text-center font-body text-sm text-graphite">{value}</td>;
}

export default function PricingPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
        }}
      />

      <div className="max-w-6xl mx-auto px-6 py-16">
        {/* Hero */}
        <header className="mb-14">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Pricing</p>
          <h1 className="font-display text-4xl md:text-5xl font-bold text-ink text-balance mb-4">
            AI content automation, priced for every team
          </h1>
          <p className="font-body text-lg text-graphite text-pretty">
            14-day free trial on all plans. No credit card required.
          </p>
        </header>

        {/* Plan cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-[#E5E5E5] bg-[#E5E5E5]">
          {/* Starter */}
          <article className="bg-paper p-8">
            <h2 className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Starter</h2>
            <p className="font-display text-4xl font-bold text-ink mb-1">$29<span className="text-base font-body font-normal text-graphite">/mo</span></p>
            <p className="font-body text-sm text-graphite mb-8">For individuals getting started with AI content automation.</p>
            <ul className="space-y-2 mb-8">
              {["2 clients", "10 campaigns per month", "10 image generations per month", "All publishing platforms (WordPress, GitHub)", "X and LinkedIn publishing", "Brand voice profiles", "Content calendar", "Scheduled publishing", "Headless blog API", "14-day free trial"].map((feat) => (
                <li key={feat} className="flex items-start gap-2 font-body text-sm text-graphite">
                  <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                  {feat}
                </li>
              ))}
            </ul>
            <Link
              href="/register"
              className="inline-flex w-full justify-center items-center bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Start free trial
            </Link>
          </article>

          {/* Growth */}
          <article className="bg-paper p-8">
            <h2 className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Growth <span className="text-ink normal-case">Most popular</span></h2>
            <p className="font-display text-4xl font-bold text-ink mb-1">$49<span className="text-base font-body font-normal text-graphite">/mo</span></p>
            <p className="font-body text-sm text-graphite mb-8">For businesses that publish weekly.</p>
            <ul className="space-y-2 mb-8">
              {["5 clients", "30 campaigns per month", "30 image generations per month", "Everything in Starter"].map((feat) => (
                <li key={feat} className="flex items-start gap-2 font-body text-sm text-graphite">
                  <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                  {feat}
                </li>
              ))}
            </ul>
            <Link
              href="/register"
              className="inline-flex w-full justify-center items-center bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Start free trial
            </Link>
          </article>

          {/* Agency */}
          <article className="bg-paper p-8">
            <h2 className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Agency</h2>
            <p className="font-display text-4xl font-bold text-ink mb-1">$149<span className="text-base font-body font-normal text-graphite">/mo</span></p>
            <p className="font-body text-sm text-graphite mb-8">For agencies managing multiple client voices.</p>
            <ul className="space-y-2 mb-8">
              {["20 clients", "Unlimited campaigns", "100 image generations per month", "Everything in Growth", "Priority support"].map((feat) => (
                <li key={feat} className="flex items-start gap-2 font-body text-sm text-graphite">
                  <CheckCircle2 className="size-4 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                  {feat}
                </li>
              ))}
            </ul>
            <Link
              href="/register"
              className="inline-flex w-full justify-center items-center bg-ink text-paper font-medium px-6 py-3 hover:bg-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              Start free trial
            </Link>
          </article>
        </div>

        <div className="border-t border-[#E5E5E5]" />

        {/* Comparison table */}
        <section aria-labelledby="compare-heading" className="py-16">
          <h2 id="compare-heading" className="font-display text-2xl font-bold text-ink mb-8">
            Compare plans
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full border border-[#E5E5E5] text-left">
              <thead>
                <tr className="border-b border-[#E5E5E5]">
                  <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite w-1/2">Feature</th>
                  <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite text-center">Starter</th>
                  <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite text-center">Growth</th>
                  <th className="px-4 py-3 font-body text-xs font-medium uppercase tracking-[0.08em] text-graphite text-center">Agency</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_ROWS.map((row, i) => (
                  <tr key={row.label} className={i < COMPARISON_ROWS.length - 1 ? "border-b border-[#E5E5E5]" : ""}>
                    <td className="px-4 py-3 font-body text-sm text-graphite">{row.label}</td>
                    <Cell value={row.starter} />
                    <Cell value={row.growth} />
                    <Cell value={row.agency} />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="border-t border-[#E5E5E5]" />

        {/* FAQ */}
        <section aria-labelledby="faq-heading" className="py-16">
          <h2 id="faq-heading" className="font-display text-2xl font-bold text-ink mb-8">
            Common questions
          </h2>
          <dl className="divide-y divide-[#E5E5E5] border-t border-[#E5E5E5]">
            {FAQ_ITEMS.map(({ q, a }) => (
              <div key={q} className="py-5">
                <dt className="font-body font-medium text-ink mb-2">{q}</dt>
                <dd className="font-body text-sm text-graphite text-pretty">{a}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </>
  );
}
