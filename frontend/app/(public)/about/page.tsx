import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ExternalLink } from "lucide-react";
import { EmailCaptureWidget } from "@/components/marketing/EmailCaptureWidget";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://www.personnapress.com";

export const metadata: Metadata = {
  title: "About Boris Kwayep, Founder of PersonnaPress",
  description:
    "Boris Kwayep is the founder of PersonnaPress. He built it after watching a brilliant client go silent every week. Not from lack of ideas. From the cost of everything that comes after the idea.",
  robots: { index: true, follow: true },
  alternates: { canonical: `${APP_URL}/about` },
  openGraph: {
    title: "About Boris Kwayep, Founder of PersonnaPress",
    description:
      "Boris Kwayep is the founder of PersonnaPress. He built it after watching a brilliant client go silent every week. Not from lack of ideas. From the cost of everything that comes after the idea.",
    url: `${APP_URL}/about`,
    type: "website",
    images: [
      {
        url: "/images/PersonnaPress-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PersonnaPress. AI Blog Writer That Sounds Like You",
      },
    ],
  },
};

const schemaPerson = {
  "@context": "https://schema.org",
  "@type": "Person",
  name: "Boris Kwayep",
  jobTitle: "Founder",
  description:
    "Software developer with seven years of experience building scalable applications. Founder of PersonnaPress, an AI blog writer and content automation platform.",
  worksFor: {
    "@type": "Organization",
    name: "PersonnaPress",
    url: APP_URL,
  },
  url: `${APP_URL}/about`,
  email: "support@personnapress.com",
  sameAs: [
    "https://www.linkedin.com/in/boris-k-1218581a3/",
    "https://x.com/BusinessBoris",
  ],
};

export default function AboutPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaPerson).replace(/</g, "\\u003c") }}
      />

      <div className="max-w-2xl mx-auto py-8">

        {/* Hero */}
        <header className="mb-12">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">
            Founder · PersonnaPress
          </p>
          <div className="border-t-2 border-ink pt-8">
            <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink leading-tight tracking-tight text-balance mb-6">
              Boris Kwayep
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty max-w-lg">
              Software developer. Seven years building scalable applications.
              Now building AI products around marketing. So businesses can grow
              and make sales without the publishing bottleneck that stops most of them.
            </p>
          </div>
        </header>

        <div className="border-t border-border" />

        {/* Origin Story */}
        <section className="py-12" aria-labelledby="origin-heading">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-8">
            The Origin Story
          </p>
          <h2
            id="origin-heading"
            className="font-display text-3xl font-bold text-ink text-balance mb-8"
          >
            The bottleneck is not the idea.
          </h2>

          <div className="space-y-5 text-base text-graphite leading-relaxed text-pretty">
            <p>
              I was helping a client with his content strategy. Smart guy. Years
              of real experience, strong opinions, genuinely useful things to say.
            </p>
            <p>
              But he never published. Not because he had nothing to write about.
              He had too much. The problem was the gap between having an insight
              and turning it into a polished blog post, formatted for SEO, then
              posted to his WordPress site, LinkedIn, and X. That process cost
              him a week. So he skipped it every time.
            </p>
          </div>

          <blockquote className="my-10 px-6 py-5 bg-highlight border-l-2 border-ink">
            <p className="font-display text-xl text-ink leading-snug text-balance">
              The bottleneck is not the idea. It is everything that comes after
              the idea.
            </p>
            <footer className="sr-only"><cite>Boris Kwayep</cite></footer>
          </blockquote>

          <div className="space-y-5 text-base text-graphite leading-relaxed text-pretty">
            <p>
              I kept thinking about that gap. Not the writing itself. The
              formatting, the SEO structure, the four separate logins, the
              scheduling. Every one of those steps is a place where a busy person
              stops. And most of them do.
            </p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* The Core Bet */}
        <section className="py-12" aria-labelledby="core-bet-heading">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-8">
            The Core Bet
          </p>
          <h2
            id="core-bet-heading"
            className="font-display text-3xl font-bold text-ink text-balance mb-8"
          >
            Voice fidelity is the unlock, not automation.
          </h2>

          <div className="space-y-5 text-base text-graphite leading-relaxed text-pretty">
            <p>
              Most AI writing tools solve for speed. They give you something
              fast. But fast and generic still does not publish. It still does
              not rank. And it definitely does not sound like you.
            </p>
            <p>
              PersonnaPress is built on a different bet: when content sounds
              exactly like you, you approve it. When you approve it, it
              publishes. When it publishes consistently, it compounds. The voice
              is not a feature. It is the product.
            </p>
            <p>That is what I am building.</p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* CTA */}
        <section className="py-12" aria-label="Get started with PersonnaPress">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            Try PersonnaPress Free
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
          <p className="font-mono text-xs text-graphite mt-4">
            14-day trial. No credit card required.
          </p>
          <p className="text-sm text-graphite mt-4">
            Questions?{" "}
            <a
              href="mailto:support@personnapress.com"
              className="underline underline-offset-4 hover:text-ink transition-colors"
            >
              support@personnapress.com
            </a>
          </p>
        </section>

        <div className="border-t border-border" />

        {/* Social links */}
        <div className="pt-8 flex items-center gap-6" aria-label="Boris Kwayep on social media">
          <a
            href="https://www.linkedin.com/in/boris-k-1218581a3/"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Boris Kwayep on LinkedIn"
            className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors"
          >
            <ExternalLink className="size-4" aria-hidden="true" />
            LinkedIn
          </a>
          <a
            href="https://x.com/BusinessBoris"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Boris Kwayep on X"
            className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors"
          >
            <ExternalLink className="size-4" aria-hidden="true" />
            @BusinessBoris
          </a>
        </div>
      </div>

      <EmailCaptureWidget source="about" />
    </>
  );
}
