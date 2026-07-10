import type { Metadata } from "next";
import Link from "next/link";
import { TerminalDemo } from "@/components/marketing/TerminalDemo";

export const dynamic = "force-static";

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: "AI Blog Writer for GitHub Pages | PersonnaPress",
    description:
      "Publish AI-written blog posts to Jekyll, Astro, Hugo, or Eleventy repos. PersonnaPress detects your framework and commits posts correctly, no config needed.",
    openGraph: {
      title: "AI Blog Writer for GitHub Pages | PersonnaPress",
      description:
        "Publish AI-written blog posts to Jekyll, Astro, Hugo, or Eleventy repos. PersonnaPress detects your framework and commits posts correctly, no config needed.",
      type: "website",
    },
    alternates: {
      canonical: "https://personnapress.com/github-publisher",
    },
    twitter: {
      card: "summary_large_image",
      title: "AI Blog Writer for GitHub Pages | PersonnaPress",
      description:
        "PersonnaPress detects your GitHub Pages framework and commits AI-written posts in the right format. Jekyll, Astro, Hugo, Next.js, Eleventy, no config required.",
    },
  };
}

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "PersonnaPress",
  description:
    "AI-powered blog writing and GitHub Pages publishing tool. Detects your static site framework and commits posts in the correct format via Pull Request or direct commit.",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Web",
  url: "https://personnapress.com",
  offers: [
    {
      "@type": "Offer",
      name: "Starter",
      price: "29",
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        billingDuration: "P1M",
      },
    },
    {
      "@type": "Offer",
      name: "Growth",
      price: "79",
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        billingDuration: "P1M",
      },
    },
    {
      "@type": "Offer",
      name: "Agency",
      price: "199",
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        billingDuration: "P1M",
      },
    },
  ],
  featureList: [
    "AI blog content generation",
    "GitHub Pages framework auto-detection",
    "Jekyll, Astro, Next.js, Hugo, Eleventy support",
    "PR-first publishing workflow",
    "Voice-matched writing",
  ],
};

const FRAMEWORKS = [
  {
    name: "Jekyll",
    signals: "_config.yml · _posts/",
    publishPath: "_posts/YYYY-MM-DD-slug.md",
  },
  {
    name: "Astro",
    signals: "astro.config.* · src/content/",
    publishPath: "src/content/blog/",
  },
  {
    name: "Next.js",
    signals: "next.config.* · posts/",
    publishPath: "posts/{slug}.md",
  },
  {
    name: "Hugo",
    signals: "hugo.toml · content/",
    publishPath: "content/posts/",
  },
  {
    name: "Eleventy",
    signals: ".eleventy.js",
    publishPath: "src/posts/",
  },
  {
    name: "Docusaurus",
    signals: "docusaurus.config.* · blog/",
    publishPath: "blog/YYYY-MM-DD-slug.md",
  },
  {
    name: "MkDocs",
    signals: "mkdocs.yml · docs/",
    publishPath: "docs/blog/posts/",
  },
  {
    name: "Plain static",
    signals: "index.html",
    publishPath: "docs/{slug}.html",
  },
];

const COMPARISON_ROWS = [
  {
    feature: "AI content generation",
    personnapress: true,
    pagesCms: false,
    decapCms: false,
  },
  {
    feature: "Auto framework detection",
    personnapress: true,
    pagesCms: false,
    decapCms: false,
  },
  {
    feature: "PR-first publish",
    personnapress: true,
    pagesCms: true,
    decapCms: true,
  },
  {
    feature: "Voice-matched writing",
    personnapress: true,
    pagesCms: false,
    decapCms: false,
  },
  {
    feature: "No config file required",
    personnapress: true,
    pagesCms: false,
    decapCms: false,
  },
];

function Check() {
  return (
    <span className="text-success font-bold" aria-label="Yes">
      &#10003;
    </span>
  );
}

function Cross() {
  return (
    <span className="text-danger font-bold" aria-label="No">
      &#10007;
    </span>
  );
}

export default function GitHubPublisherPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Minimal top navigation */}
      <nav
        aria-label="Site navigation"
        className="bg-paper border-b border-border"
      >
        <div className="max-w-[1200px] mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="font-display font-bold text-xl text-ink hover:text-graphite transition-colors"
          >
            PersonnaPress
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm text-graphite hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="bg-ink text-white text-sm px-4 py-2 shadow-brutal-sm hover:bg-white hover:text-ink border border-ink transition-colors focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
              style={{ borderRadius: 0 }}
            >
              Start free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero section */}
      <section
        aria-label="Hero"
        className="bg-ink px-6 py-24 lg:py-32 text-center"
      >
        <h1 className="font-display font-bold text-5xl lg:text-7xl text-white text-balance leading-[1.15] tracking-[-0.01em] mb-6 max-w-[900px] mx-auto">
          Publish your AI-written blog to GitHub. In the right format, to the
          right file, every time.
        </h1>
        <p className="text-[18px] text-white/70 font-sans max-w-[600px] mx-auto mb-8 leading-[1.6]">
          PersonnaPress detects your Jekyll, Astro, Hugo, or Next.js setup and
          commits the post where it belongs, no config, no copy-paste.
        </p>
        <Link
          href="/register"
          className="inline-block bg-white text-ink font-sans font-medium px-6 py-3 border border-white shadow-[4px_4px_0px_white] hover:bg-ink hover:text-white hover:shadow-none transition-colors focus-visible:outline-2 focus-visible:outline-white focus-visible:outline-offset-2"
          style={{ borderRadius: 0 }}
        >
          Connect your repo
        </Link>
        <p className="font-mono text-[13px] text-white/50 mt-6">
          Jekyll · Astro · Next.js · Hugo · Eleventy · Docusaurus · MkDocs
        </p>
      </section>

      {/* Terminal demo section */}
      <TerminalDemo />

      {/* Framework support section */}
      <section
        aria-label="Supported frameworks"
        className="bg-paper px-6 py-20"
      >
        <h2 className="font-display font-bold text-4xl text-ink text-center mb-4">
          Works with your setup
        </h2>
        <p className="text-center text-graphite max-w-[520px] mx-auto mb-12 leading-[1.6]">
          PersonnaPress automatically detects Jekyll, Astro, Next.js, Hugo,
          Eleventy, Docusaurus, MkDocs, or plain static sites and writes your
          post to the correct folder in the correct format.
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 max-w-[960px] mx-auto">
          {FRAMEWORKS.map((fw) => (
            <article
              key={fw.name}
              className="bg-white border border-border p-5 hover:shadow-brutal transition-shadow"
              style={{ borderRadius: 0 }}
            >
              <h3 className="font-sans font-medium text-[15px] text-ink mb-2">
                {fw.name}
              </h3>
              <p className="font-mono text-[12px] text-graphite">
                {fw.signals}
              </p>
              <p className="font-mono text-[12px] font-bold text-ink mt-1">
                {fw.publishPath}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Comparison table section */}
      <section
        aria-label="Comparison with alternatives"
        className="bg-paper px-6 py-20"
      >
        <h2 className="font-display font-bold text-4xl text-ink text-center mb-4">
          Not a CMS. A publishing layer.
        </h2>
        <div className="overflow-x-auto max-w-[720px] mx-auto mt-10">
          <table className="w-full border-collapse">
            <caption className="sr-only">
              PersonnaPress vs Pages CMS vs Decap CMS feature comparison
            </caption>
            <thead>
              <tr className="bg-ink">
                <th
                  scope="col"
                  className="text-white font-sans text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
                >
                  Feature
                </th>
                <th
                  scope="col"
                  className="text-white font-sans text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-center"
                >
                  PersonnaPress
                </th>
                <th
                  scope="col"
                  className="text-white font-sans text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-center"
                >
                  Pages CMS
                </th>
                <th
                  scope="col"
                  className="text-white font-sans text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-center"
                >
                  Decap CMS
                </th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_ROWS.map((row) => (
                <tr key={row.feature}>
                  <th
                    scope="row"
                    className="font-sans text-sm text-ink px-4 py-3 border border-ink text-left font-normal"
                  >
                    {row.feature}
                  </th>
                  <td className="border border-ink px-4 py-3 text-center">
                    {row.personnapress ? <Check /> : <Cross />}
                  </td>
                  <td className="border border-ink px-4 py-3 text-center">
                    {row.pagesCms ? <Check /> : <Cross />}
                  </td>
                  <td className="border border-ink px-4 py-3 text-center">
                    {row.decapCms ? <Check /> : <Cross />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* CTA section */}
      <section
        aria-label="Call to action"
        className="bg-highlighter px-6 py-24 text-center"
      >
        <h2 className="font-display font-bold text-4xl text-ink mb-4">
          Your next post is one Brain Dump away.
        </h2>
        <p className="text-[16px] text-graphite max-w-[520px] mx-auto mb-8 leading-[1.6]">
          Paste your raw notes. PersonnaPress writes the post in your voice and
          commits it to your GitHub repo in the right format for your framework.
        </p>
        <Link
          href="/register"
          className="inline-block bg-ink text-white font-sans font-medium px-6 py-3 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
          style={{ borderRadius: 0 }}
        >
          Start free, no credit card
        </Link>
        <p className="text-[13px] text-graphite mt-4 font-sans">
          14-day free trial · Supports 8 frameworks · PR-first by default.
        </p>
      </section>
    </>
  );
}
