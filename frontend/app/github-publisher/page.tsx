import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check, X, GitBranch, Scan, FileCode, GitPullRequest } from "lucide-react";
import { TerminalDemo } from "@/components/marketing/TerminalDemo";
import { PublicHeader } from "@/components/marketing/PublicHeader";
import { PublicFooter } from "@/components/marketing/PublicFooter";

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

const HOW_IT_WORKS = [
  {
    step: "01",
    icon: GitBranch,
    title: "Connect your repo",
    description:
      "Install the PersonnaPress GitHub App on your account. Select which repository contains your site. No tokens, no SSH keys, no config files.",
  },
  {
    step: "02",
    icon: Scan,
    title: "Auto-detection",
    description:
      "PersonnaPress scans your repo for framework signals — _config.yml, astro.config.*, hugo.toml — and resolves the correct publish path automatically.",
  },
  {
    step: "03",
    icon: FileCode,
    title: "Write in your voice",
    description:
      "Drop your notes. PersonnaPress generates a full SEO blog post in your brand voice, formatted for your framework with correct front matter.",
  },
  {
    step: "04",
    icon: GitPullRequest,
    title: "PR-first publish",
    description:
      "After you approve the draft, PersonnaPress opens a Pull Request to your repo. Merge it to publish. Direct commit is available for trusted workflows.",
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

export default function GitHubPublisherPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Navigation */}
      <PublicHeader />

      <main>
        {/* Hero — light background, left-aligned, brutalist CTA */}
        <section className="max-w-6xl mx-auto px-6 pt-24 pb-20" aria-label="Hero">
          <div className="max-w-3xl">
            <h1 className="font-display text-6xl lg:text-7xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
              Publish your AI-written blog to GitHub.
              <br />
              <span className="relative">
                In the right format, every time.
                <span
                  className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
                  aria-hidden="true"
                />
              </span>
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
              PersonnaPress detects your Jekyll, Astro, Hugo, or Next.js setup
              and commits the post where it belongs &mdash; no config, no
              copy-paste, no SSH keys.
            </p>
            <div className="flex items-center gap-4">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
              >
                Connect your repo
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <a
                href="#how-it-works"
                className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
              >
                See how it works
              </a>
            </div>
            <p className="font-mono text-xs text-graphite mt-6">
              Jekyll · Astro · Next.js · Hugo · Eleventy · Docusaurus · MkDocs
            </p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Terminal demo */}
        <TerminalDemo />

        <div className="border-t border-border" />

        {/* How it works */}
        <section id="how-it-works" className="max-w-6xl mx-auto px-6 py-20" aria-label="How it works">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              How It Works
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              From notes to merged PR in minutes
            </h2>
          </header>
          <ol className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px border border-border bg-border list-none">
            {HOW_IT_WORKS.map(({ step, icon: Icon, title, description }) => (
              <li
                key={step}
                className="bg-paper p-8 group hover:bg-highlight transition-colors"
              >
                <div className="flex items-start justify-between mb-6">
                  <span className="font-mono text-xs text-graphite">{step}</span>
                  <Icon
                    className="size-5 text-graphite group-hover:text-ink transition-colors"
                    aria-hidden="true"
                  />
                </div>
                <h3 className="font-display text-xl font-bold text-ink mb-3 text-balance">
                  {title}
                </h3>
                <p className="text-sm text-graphite leading-relaxed text-pretty">
                  {description}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <div className="border-t border-border" />

        {/* Framework support */}
        <section aria-label="Supported frameworks" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Framework Support
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Works with your setup
            </h2>
            <p className="text-graphite max-w-xl mt-4 leading-relaxed text-pretty">
              PersonnaPress automatically detects your framework from repo
              signals and writes your post to the correct folder in the correct
              format. No configuration file required.
            </p>
          </header>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px border border-border bg-border">
            {FRAMEWORKS.map((fw) => (
              <article
                key={fw.name}
                className="bg-paper p-8 group hover:bg-highlight transition-colors"
              >
                <h3 className="font-display text-lg font-bold text-ink mb-3">
                  {fw.name}
                </h3>
                <p className="font-mono text-xs text-graphite mb-2">
                  {fw.signals}
                </p>
                <p className="font-mono text-xs font-bold text-ink">
                  {fw.publishPath}
                </p>
              </article>
            ))}
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Comparison */}
        <section aria-label="Comparison with alternatives" className="max-w-6xl mx-auto px-6 py-20">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Why PersonnaPress
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Not a CMS. A publishing layer.
            </h2>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse border border-border max-w-2xl">
              <caption className="sr-only">
                PersonnaPress vs Pages CMS vs Decap CMS feature comparison
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
                    Pages CMS
                  </th>
                  <th
                    scope="col"
                    className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-6 py-4 border border-ink text-center"
                  >
                    Decap CMS
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_ROWS.map((row) => (
                  <tr key={row.feature} className="group hover:bg-highlight transition-colors">
                    <th
                      scope="row"
                      className="font-body text-sm text-ink px-6 py-4 border border-border text-left font-normal"
                    >
                      {row.feature}
                    </th>
                    <td className="border border-border px-6 py-4 text-center">
                      {row.personnapress ? (
                        <Check className="size-4 text-success mx-auto" aria-label="Yes" />
                      ) : (
                        <X className="size-4 text-danger mx-auto" aria-label="No" />
                      )}
                    </td>
                    <td className="border border-border px-6 py-4 text-center">
                      {row.pagesCms ? (
                        <Check className="size-4 text-success mx-auto" aria-label="Yes" />
                      ) : (
                        <X className="size-4 text-danger mx-auto" aria-label="No" />
                      )}
                    </td>
                    <td className="border border-border px-6 py-4 text-center">
                      {row.decapCms ? (
                        <Check className="size-4 text-success mx-auto" aria-label="Yes" />
                      ) : (
                        <X className="size-4 text-danger mx-auto" aria-label="No" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* CTA */}
        <section
          aria-label="Call to action"
          className="bg-highlighter px-6 py-24 text-center"
        >
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">
            Get Started
          </p>
          <h2 className="font-display font-bold text-4xl text-ink mb-4 text-balance">
            Your next post is one Brain Dump away.
          </h2>
          <p className="text-graphite max-w-xl mx-auto mb-10 leading-relaxed text-pretty">
            Paste your raw notes. PersonnaPress writes the post in your voice
            and commits it to your GitHub repo in the right format for your
            framework.
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
          >
            Start free, no credit card
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
          <p className="font-mono text-xs text-graphite mt-6">
            14-day free trial · 8 frameworks supported · PR-first by default
          </p>
        </section>
      </main>

      {/* Footer */}
      <PublicFooter />
    </>
  );
}
