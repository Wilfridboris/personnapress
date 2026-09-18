import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import { FaqAccordion } from "@/app/_components/FaqAccordion";

export const dynamic = "force-static";

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");

export function generateMetadata(): Metadata {
  const title = "Best AI Blog Writers for Publishing to Your Blog and Social | PersonnaPress";
  const description =
    "Compare the best AI blog writers in 2026: PersonnaPress, Writesonic, Jasper, and Copy.ai. Honest ranking by publishing depth, voice fidelity, and price.";
  return {
    title: { absolute: title },
    description,
    alternates: { canonical: `${APP_URL}/best-ai-blog-writers` },
    openGraph: {
      title,
      description,
      type: "website",
      url: `${APP_URL}/best-ai-blog-writers`,
      images: [
        {
          url: "/images/PersonnaPress-opengraph.png",
          width: 1200,
          height: 630,
          alt: "Best AI blog writers comparison 2026",
        },
      ],
    },
    twitter: { card: "summary_large_image", title, description },
  };
}

const FAQ_ITEMS = [
  {
    question: "What is the best AI blog writer in 2026?",
    answer:
      "The best AI blog writer depends on your use case. PersonnaPress is the strongest choice if you need an autonomous loop from idea to published blog post and social content, with voice extracted from your own writing. Writesonic leads on SEO data integrations. Jasper is best for large marketing teams running multiple agent workflows. Copy.ai is the best fit for GTM and revenue teams focused on short-form copy and workflow automation.",
  },
  {
    question: "Do AI blog writers publish directly to my blog?",
    answer:
      "PersonnaPress publishes to GitHub, WordPress, Webflow, and a headless API automatically after you approve. Writesonic publishes to WordPress with one click. Jasper and Copy.ai both stop at content generation, requiring a manual copy-paste step or a third-party integration like Zapier to move content to your blog.",
  },
  {
    question: "Can AI writing tools match my brand voice?",
    answer:
      "All four tools covered here have brand-voice features that extract or learn your tone from samples. The meaningful difference is how well the voice holds in longer pieces. PersonnaPress is built specifically around maintaining voice consistency through 2,000-word posts. The other tools handle brand voice well for short-form copy but show varying degrees of drift in long-form content.",
  },
  {
    question: "How much do AI blog writers cost?",
    answer:
      "Pricing varies widely: PersonnaPress starts at $29 per month with a 14-day free trial and no credit card required. Writesonic starts at $79 per month. Jasper starts at $69 per seat per month with a 7-day trial. Copy.ai starts at $29 per month with no listed free tier or trial. Check each tool's site for current pricing, as plans change frequently.",
  },
  {
    question: "What is the difference between an AI blog writer and a GTM AI platform?",
    answer:
      "An AI blog writer is focused on generating and publishing long-form content for your blog and social channels. PersonnaPress and Writesonic are in this category. A GTM AI platform, like Copy.ai, is designed to automate broader go-to-market workflows: sales outreach, ad copy, email sequences, and CRM tasks. Jasper sits between the two, offering both long-form writing and a suite of marketing agents for teams.",
  },
];

const jsonLdItemList = {
  "@context": "https://schema.org",
  "@type": "ItemList",
  name: "Best AI Blog Writers",
  itemListElement: [
    {
      "@type": "ListItem",
      position: 1,
      item: {
        "@type": "SoftwareApplication",
        name: "PersonnaPress",
        url: APP_URL,
        description:
          "Autonomous idea-to-published loop: writes SEO-structured articles and social posts in your brand voice, then publishes to blog and social channels in one workflow.",
      },
    },
    {
      "@type": "ListItem",
      position: 2,
      item: {
        "@type": "SoftwareApplication",
        name: "Writesonic",
        url: "https://writesonic.com",
        description:
          "AI search and GEO growth engine with deep SEO data integrations (Surfer, Ahrefs, Semrush, GSC) and one-click WordPress publishing.",
      },
    },
    {
      "@type": "ListItem",
      position: 3,
      item: {
        "@type": "SoftwareApplication",
        name: "Jasper",
        url: "https://www.jasper.ai",
        description:
          "Multi-agent AI marketing platform for large teams, with broad content types, mature brand voice management, and GEO/AEO investment.",
      },
    },
    {
      "@type": "ListItem",
      position: 4,
      item: {
        "@type": "SoftwareApplication",
        name: "Copy.ai",
        url: "https://www.copy.ai",
        description:
          "GTM AI Platform for revenue teams focused on short-form copy, sales workflows, and CRM automation.",
      },
    },
  ],
};

const jsonLdFaq = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ_ITEMS.map(({ question, answer }) => ({
    "@type": "Question",
    name: question,
    acceptedAnswer: { "@type": "Answer", text: answer },
  })),
};

const jsonLdBreadcrumb = {
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    { "@type": "ListItem", position: 1, name: "Home", item: APP_URL },
    {
      "@type": "ListItem",
      position: 2,
      name: "Best AI Blog Writers for Publishing to Your Blog and Social",
      item: `${APP_URL}/best-ai-blog-writers`,
    },
  ],
};

const TOOLS = [
  {
    rank: "01",
    name: "PersonnaPress",
    tagline: "Best for: autonomous idea-to-published loop in your own voice",
    description:
      "PersonnaPress extracts your brand voice from your existing content, then turns raw ideas into SEO-structured blog articles and social posts, and publishes to your blog (GitHub, WordPress, Webflow, or headless API) and social channels (X, LinkedIn, Meta) in one workflow after a single approval. Entry price: $29 per month. 14-day free trial, no credit card.",
    strengths: [
      "Full autonomous publish loop: blog and social in one workflow",
      "Voice extracted from your writing, held consistently in long-form",
      "Publish to GitHub, WordPress, Webflow, and headless API",
    ],
    comparisonHref: null,
    url: APP_URL,
  },
  {
    rank: "02",
    name: "Writesonic",
    tagline: "Best for: SEO data integrations and WordPress publishing",
    description:
      "Writesonic is a capable AI writing and SEO platform with native integrations for Surfer, Ahrefs, Semrush, and Google Search Console, plus a GEO module for AI-search visibility. One-click WordPress publishing is included. Social auto-posting is not. Entry price: $79 per month, no permanent free tier. As of September 2026, check current pricing at writesonic.com.",
    strengths: [
      "Deep SEO data integrations: Surfer, Ahrefs, Semrush, GSC",
      "GEO module for tracking AI-search visibility",
      "One-click WordPress publishing",
    ],
    comparisonHref: "/writesonic-alternatives",
    url: "https://writesonic.com",
  },
  {
    rank: "03",
    name: "Jasper",
    tagline: "Best for: large marketing teams running parallel agent workflows",
    description:
      "Jasper is an AI marketing platform built around a suite of agents covering blog posts, ads, emails, and landing pages. It has mature multi-profile brand voice management and early GEO/AEO investment. Publishing stops at a WordPress or HubSpot handoff. Entry price: $69 per seat per month, 7-day trial, no permanent free tier. As of September 2026, check current pricing at jasper.ai.",
    strengths: [
      "Broad suite of marketing agents for large teams",
      "Mature multi-profile brand voice management",
      "Early investment in GEO and AEO content formats",
    ],
    comparisonHref: "/jasper-alternatives",
    url: "https://www.jasper.ai",
  },
  {
    rank: "04",
    name: "Copy.ai",
    tagline: "Best for: GTM workflow automation and short-form copy",
    description:
      "Copy.ai has repositioned as a GTM AI Platform for revenue teams, with strong short-form copy generation and workflow automation connecting to CRM and outreach tools. It does not include native blog publishing or SEO structuring for long-form content. Entry price: $29 per month, no listed free tier or trial. As of September 2026, check current pricing at copy.ai.",
    strengths: [
      "Fast short-form copy for ads, emails, and social posts",
      "GTM workflow automation for sales and revenue teams",
      "Model flexibility for different content tasks",
    ],
    comparisonHref: "/copy-ai-alternatives",
    url: "https://www.copy.ai",
  },
];

export default function BestAiBlogWritersPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdItemList).replace(/</g, "\\u003c") }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdFaq).replace(/</g, "\\u003c") }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdBreadcrumb).replace(/</g, "\\u003c") }}
      />

      <main className="-mt-8 -mx-4">
        {/* Hero */}
        <section className="max-w-6xl mx-auto px-6 pt-12 md:pt-24 pb-16 md:pb-20">
          <div className="max-w-3xl">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Comparison</p>
            <h1 className="font-display text-5xl lg:text-6xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
              Best AI Blog Writers for Publishing to Your Blog and Social
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
              Four AI writing tools, ranked by how far they take you: from idea to published blog post and social
              content, in your own voice. Each has a different strength and a different ceiling. Here is an honest
              breakdown.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
              >
                Try PersonnaPress free
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <a
                href="#tools"
                className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
              >
                See the rankings
              </a>
            </div>
            <p className="font-mono text-xs text-graphite mt-6">
              14-day free trial. No credit card required.
            </p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Ranked tools */}
        <section
          id="tools"
          className="max-w-6xl mx-auto px-6 py-20"
          aria-label="Ranked AI blog writers"
        >
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">The Rankings</p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Four tools, four different strengths
            </h2>
            <p className="text-graphite max-w-xl mt-4 leading-relaxed text-pretty">
              Ranked by autonomous publishing depth. All claims as of September 2026, check each tool's site for
              current pricing and features.
            </p>
          </header>

          <ol role="list" className="space-y-px border border-border bg-border list-none">
            {TOOLS.map(({ rank, name, tagline, description, strengths, comparisonHref, url }) => (
              <li key={name} className="bg-paper p-8 md:p-10">
                <div className="flex items-start gap-6 md:gap-10">
                  <span className="font-mono text-3xl font-bold text-graphite/30 shrink-0 leading-none mt-1">
                    {rank}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-baseline gap-3 mb-2">
                      <h3 className="font-display text-2xl font-bold text-ink">{name}</h3>
                      <span className="font-mono text-xs text-graphite tracking-wide">{tagline}</span>
                    </div>
                    <p className="font-body text-sm text-graphite leading-relaxed text-pretty mb-6 max-w-2xl">
                      {description}
                    </p>
                    <ul className="space-y-2 mb-6">
                      {strengths.map((s) => (
                        <li key={s} className="flex items-start gap-3">
                          <Check className="size-3.5 text-ink mt-0.5 shrink-0" aria-hidden="true" />
                          <span className="font-body text-xs text-graphite leading-relaxed">{s}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="flex flex-wrap gap-4">
                      {comparisonHref ? (
                        <Link
                          href={comparisonHref}
                          className="font-mono text-xs text-graphite underline underline-offset-2 hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
                        >
                          PersonnaPress vs {name} in depth
                        </Link>
                      ) : (
                        <Link
                          href="/dashboard"
                          className="font-mono text-xs text-graphite underline underline-offset-2 hover:text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
                        >
                          Start free trial
                        </Link>
                      )}
                      {url !== APP_URL && (
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-xs text-graphite/60 underline underline-offset-2 hover:text-graphite transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-1"
                        >
                          {name} site
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <div className="border-t border-border" />

        {/* Spoke links */}
        <section className="max-w-6xl mx-auto px-6 py-16" aria-label="Deep-dive comparisons">
          <header className="mb-10">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">Deep Dives</p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Side-by-side comparisons
            </h2>
            <p className="text-graphite max-w-xl mt-4 leading-relaxed text-pretty">
              Each page below compares PersonnaPress directly against one competitor: honest table, fair assessment
              of where the competitor wins, and a full FAQ.
            </p>
          </header>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border">
            {[
              {
                href: "/jasper-alternatives",
                title: "Jasper Alternatives",
                desc: "For founders who want an autonomous loop vs. a multi-agent marketing platform.",
              },
              {
                href: "/copy-ai-alternatives",
                title: "Copy.ai Alternatives",
                desc: "For blog-focused publishing vs. GTM workflow automation.",
              },
              {
                href: "/writesonic-alternatives",
                title: "Writesonic Alternatives",
                desc: "For blog and social publishing vs. deep SEO data integrations.",
              },
            ].map(({ href, title, desc }) => (
              <Link
                key={href}
                href={href}
                className="bg-paper p-8 group hover:bg-highlight transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-inset"
              >
                <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-3">Compare</p>
                <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance group-hover:underline underline-offset-2">
                  {title}
                </h3>
                <p className="text-sm text-graphite leading-relaxed text-pretty">{desc}</p>
                <span className="inline-flex items-center gap-1 font-mono text-xs text-ink mt-4">
                  Read comparison
                  <ArrowRight className="size-3" aria-hidden="true" />
                </span>
              </Link>
            ))}
          </div>
        </section>

        <div className="border-t border-border" />

        {/* FAQ */}
        <section className="max-w-6xl mx-auto px-6 py-20" aria-label="Frequently asked questions">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">FAQ</p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Questions about AI blog writers
            </h2>
          </header>
          <FaqAccordion items={FAQ_ITEMS} />
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
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
          <p className="font-mono text-xs text-graphite mt-6">14-day free trial. Starter from $29 / month.</p>
        </section>
      </main>
    </>
  );
}
