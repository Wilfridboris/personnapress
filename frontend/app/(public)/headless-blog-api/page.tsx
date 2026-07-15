import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Sparkles, Database, Braces, Check, X } from "lucide-react";
import { FaqAccordion } from "@/app/_components/FaqAccordion";

export const dynamic = "force-static";

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com").replace(/\/$/, "");

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: "Headless Blog API for Your Website | PersonnaPress",
    description:
      "Store blog content in PersonnaPress and fetch it on your own site through one API. A Contentful alternative built for blogs, with SEO data included.",
    alternates: {
      canonical: `${APP_URL}/headless-blog-api`,
    },
    openGraph: {
      title: "Headless Blog API for Your Website | PersonnaPress",
      description:
        "Store blog content in PersonnaPress and fetch it on your own site through one API. A Contentful alternative built for blogs, with SEO data included.",
      type: "website",
      url: `${APP_URL}/headless-blog-api`,
      images: [
        {
          url: "/images/PersonnaPress-opengraph.png",
          width: 1200,
          height: 630,
          alt: "PersonnaPress headless blog API: fetch blog content via one GET request",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "Headless Blog API for Your Website | PersonnaPress",
      description:
        "Store blog content in PersonnaPress and fetch it on your own site through one API. A Contentful alternative built for blogs, with SEO data included.",
    },
  };
}

const jsonLdSoftwareApp = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "PersonnaPress",
  description:
    "Headless blog API that writes, stores, and versions your articles. Fetch content via one GET request. SEO structured data included in every response.",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: APP_URL,
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
    "Headless blog content API",
    "SEO structured data in every article response",
    "AI blog post generation in your brand voice",
    "Revision history for every article",
    "Publish to WordPress, X, LinkedIn, and GitHub",
    "JSON-LD, OpenGraph, and meta description per article",
  ],
};

const FAQ_ITEMS = [
  {
    question: "What is a headless blog API?",
    answer:
      "A headless blog API stores your content on a server and delivers it to any website or app via HTTP. Your site requests articles with a GET call and renders them using your own design. There is no CMS dashboard to embed, no plugin to install, and no theme to configure. PersonnaPress is a headless blog API that also writes the content for you, stores every revision, and includes SEO structured data in every response.",
  },
  {
    question: "How is PersonnaPress different from Contentful?",
    answer:
      "Contentful is a general-purpose headless CMS designed for any type of content: pages, products, media, and more. PersonnaPress is built specifically for blog content. It writes articles in your brand voice using AI, versions every edit, and includes ready-to-use JSON-LD structured data and OpenGraph tags in every API response. You do not need a developer to write or manage content, and you do not need to build your own SEO layer on top of the API.",
  },
  {
    question: "Do I need a CMS to use the PersonnaPress headless blog API?",
    answer:
      "No. PersonnaPress replaces the CMS for blog content entirely. You write a brain dump, PersonnaPress generates and stores the article. Your website fetches it with one GET request. There is no CMS to host, configure, or maintain. If you already use a CMS for other content types, PersonnaPress handles only the blog layer and does not interfere with the rest of your stack.",
  },
  {
    question: "How do I fetch articles on my website?",
    answer:
      "To list your published articles, send a GET request to https://api.personnapress.com/public/v1/articles. Each item in the response includes title, excerpt, featured image URL, author, tags, category, and timestamps. To render a full article with HTML content and SEO data, call https://api.personnapress.com/public/v1/articles/{slug} using the slug from the list. That response adds an html field and a complete seo object. Include your delivery token in the Authorization header as Bearer ppd_your_token.",
  },
  {
    question: "Can I edit articles after publishing?",
    answer:
      "Yes. The PersonnaPress approval gate includes a full WYSIWYG editor. Every save creates a numbered revision so you can compare and restore any previous version. Edits are reflected in the API response immediately after saving. If you use revalidation in your frontend (for example next: { revalidate: 60 } in a Next.js fetch), the updated content appears on your site within your chosen interval.",
  },
  {
    question: "What fields does the article API response include?",
    answer:
      "Each article detail response includes: slug, title, excerpt, HTML content, featured_image_url, author, tags, category, published_at, updated_at, reading_time_minutes, and a seo object. The seo object always contains a json_ld block (Schema.org Article type) and reading_time_minutes. The og block (with title, description, and image) and meta_description string are included when the article has those fields populated. You can pass these directly to your page metadata without writing any SEO logic yourself.",
  },
  {
    question: "Is the PersonnaPress headless blog API a Contentful alternative?",
    answer:
      "For blog content specifically, yes. PersonnaPress covers the full cycle: AI writes the article in your voice, stores it with revision history, and delivers it via a clean read API with SEO data built in. Contentful requires you to write the content yourself, build a separate SEO layer, and configure webhooks for publishing to social platforms. PersonnaPress handles all of this as a single integrated system.",
  },
];

const jsonLdFaq = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ_ITEMS.map(({ question, answer }) => ({
    "@type": "Question",
    name: question,
    acceptedAnswer: {
      "@type": "Answer",
      text: answer,
    },
  })),
};

const HOW_IT_WORKS = [
  {
    step: "01",
    icon: Sparkles,
    title: "Generate",
    description:
      "Drop your notes into PersonnaPress. The AI writes a full SEO blog post in your brand voice, ready for review in under 90 seconds.",
  },
  {
    step: "02",
    icon: Database,
    title: "Store and version",
    description:
      "After you approve, the article is stored with a clean slug, full revision history, and SEO metadata. Every edit creates a numbered revision you can restore.",
  },
  {
    step: "03",
    icon: Braces,
    title: "Fetch via API",
    description:
      "Your site calls GET /public/v1/articles with your delivery token. You receive HTML, metadata, and ready-to-use SEO structured data in one response.",
  },
];

const EXAMPLE_RESPONSE = `{
  "slug": "how-to-price-consulting-services",
  "title": "How to Price Consulting Services Without Guessing",
  "excerpt": "Most consultants underprice because they anchor to hourly rates instead of value delivered.",
  "featured_image_url": "https://cdn.personnapress.com/images/how-to-price-consulting.jpg",
  "author": "Alex Morgan",
  "tags": ["consulting", "pricing", "freelance"],
  "category": "Business",
  "published_at": "2026-07-14T09:00:00+00:00",
  "updated_at": "2026-07-14T10:23:00+00:00",
  "reading_time_minutes": 7,
  "html": "<h2>The problem with hourly pricing</h2><p>When you charge by the hour...</p>",
  "seo": {
    "reading_time_minutes": 7,
    "meta_description": "Learn how to price consulting services based on value, not hours. Three frameworks that help independent consultants earn more without working more.",
    "json_ld": {
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "How to Price Consulting Services Without Guessing",
      "description": "Learn how to price consulting services based on value, not hours.",
      "image": "https://cdn.personnapress.com/images/how-to-price-consulting.jpg",
      "datePublished": "2026-07-14T09:00:00+00:00",
      "dateModified": "2026-07-14T10:23:00+00:00",
      "author": { "@type": "Person", "name": "Alex Morgan" },
      "keywords": "consulting, pricing, freelance"
    },
    "og": {
      "title": "How to Price Consulting Services Without Guessing",
      "description": "Learn how to price consulting services based on value, not hours.",
      "image": "https://cdn.personnapress.com/images/how-to-price-consulting.jpg"
    }
  }
}`;

const FETCH_SAMPLE = `// Plain fetch: works in any JavaScript environment
const res = await fetch(
  "https://api.personnapress.com/public/v1/articles/how-to-price-consulting-services",
  {
    headers: {
      Authorization: "Bearer ppd_your_token_here",
    },
  }
);
if (!res.ok) throw new Error(\`HTTP \${res.status}\`);
const article = await res.json();

document.querySelector("h1").textContent = article.title;
document.querySelector("article").innerHTML = article.html;`;

const NEXTJS_SAMPLE = `// Next.js App Router: async Server Component
// app/blog/[slug]/page.tsx

import type { Metadata } from "next";

const API = "https://api.personnapress.com/public/v1/articles";
const TOKEN = process.env.PERSONNAPRESS_DELIVERY_TOKEN!;

async function getArticle(slug: string) {
  const res = await fetch(\`\${API}/\${slug}\`, {
    headers: { Authorization: \`Bearer \${TOKEN}\` },
    next: { revalidate: 60 },
  });
  if (!res.ok) return null;
  return res.json();
}

export async function generateMetadata(
  { params }: { params: { slug: string } }
): Promise<Metadata> {
  const article = await getArticle(params.slug);
  if (!article) return {};
  return {
    title: article.title,
    ...(article.seo.meta_description && { description: article.seo.meta_description }),
    ...(article.seo.og && { openGraph: article.seo.og }),
  };
}

export default async function BlogPostPage(
  { params }: { params: { slug: string } }
) {
  const article = await getArticle(params.slug);
  if (!article) return <p>Article not found.</p>;
  return (
    <main>
      <h1>{article.title}</h1>
      <article dangerouslySetInnerHTML={{ __html: article.html }} />
    </main>
  );
}`;

const ASTRO_SAMPLE = `---
// src/pages/blog/[slug].astro

const { slug } = Astro.params;
const res = await fetch(
  \`https://api.personnapress.com/public/v1/articles/\${slug}\`,
  {
    headers: {
      Authorization: \`Bearer \${import.meta.env.PERSONNAPRESS_TOKEN}\`,
    },
  }
);
const article = await res.json();
---

<html lang="en">
  <head>
    <title>{article.title}</title>
    {article.seo.meta_description && <meta name="description" content={article.seo.meta_description} />}
    {article.seo.og?.title && <meta property="og:title" content={article.seo.og.title} />}
    {article.seo.og?.image && <meta property="og:image" content={article.seo.og.image} />}
    <script type="application/ld+json" set:html={JSON.stringify(article.seo.json_ld)} />
  </head>
  <body>
    <h1>{article.title}</h1>
    <article set:html={article.html} />
  </body>
</html>`;

type ComparisonValue = "yes" | "no" | "partial";

interface ComparisonRow {
  feature: string;
  personnapress: ComparisonValue;
  contentful: ComparisonValue;
  dropinblog: ComparisonValue;
}

const COMPARISON_ROWS: ComparisonRow[] = [
  {
    feature: "AI writes the content",
    personnapress: "yes",
    contentful: "no",
    dropinblog: "no",
  },
  {
    feature: "SEO structured data in every response",
    personnapress: "yes",
    contentful: "no",
    dropinblog: "partial",
  },
  {
    feature: "Revision history included",
    personnapress: "yes",
    contentful: "yes",
    dropinblog: "no",
  },
  {
    feature: "Publishes to WordPress, X, LinkedIn, GitHub",
    personnapress: "yes",
    contentful: "no",
    dropinblog: "no",
  },
  {
    feature: "Built specifically for blogs",
    personnapress: "yes",
    contentful: "no",
    dropinblog: "yes",
  },
];

function ComparisonCell({ value }: { value: ComparisonValue }) {
  if (value === "yes") {
    return <Check className="size-4 text-success mx-auto" aria-label="Yes" />;
  }
  if (value === "no") {
    return <X className="size-4 text-danger mx-auto" aria-label="No" />;
  }
  return (
    <span className="font-mono text-xs text-graphite" aria-label="Partial">
      partial
    </span>
  );
}

export default function HeadlessBlogApiPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdSoftwareApp) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdFaq) }}
      />

      <main className="-mt-8 -mx-4">

        {/* Hero */}
        <section className="max-w-6xl mx-auto px-6 pt-24 pb-20">
          <div className="max-w-3xl">
            <h1 className="font-display text-6xl lg:text-7xl font-bold text-ink leading-tight tracking-tight text-balance mb-8">
              Your blog, on your website,{" "}
              <span className="relative">
                powered by our API.
                <span
                  className="absolute -bottom-1 left-0 w-full h-0.5 bg-highlight"
                  aria-hidden="true"
                />
              </span>
            </h1>
            <p className="text-xl text-graphite leading-relaxed text-pretty mb-10 max-w-xl">
              PersonnaPress writes, stores, and versions your articles. Your site
              fetches them with one GET request. No CMS to install, no plugin to
              maintain.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
              >
                Start free
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <a
                href="#api-response"
                className="text-sm text-graphite underline underline-offset-4 hover:text-ink transition-colors"
              >
                See the API response
              </a>
            </div>
            <p className="font-mono text-xs text-graphite mt-6">
              14-day free trial. No credit card required.
            </p>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* How it works */}
        <section id="how-it-works" className="max-w-6xl mx-auto px-6 py-20" aria-label="How it works">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              How It Works
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Store once, deliver anywhere
            </h2>
          </header>
          <ol role="list" className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border list-none">
            {HOW_IT_WORKS.map(({ step, icon: Icon, title, description }) => (
              <li
                key={step}
                className="bg-paper p-8 group hover:bg-highlight transition-colors"
              >
                <div className="flex items-start justify-between mb-6">
                  <span className="font-mono text-xs text-graphite uppercase tracking-widest">
                    {step}
                  </span>
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

        {/* API Response Showcase */}
        <section
          id="api-response"
          className="max-w-6xl mx-auto px-6 py-20"
          aria-label="API response example"
        >
          <header className="mb-10">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              The Response
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Everything you need in one call
            </h2>
            <p className="text-graphite max-w-xl mt-4 leading-relaxed text-pretty">
              GET /public/v1/articles/{"{slug}"} returns the article HTML, metadata,
              and a complete SEO object. No extra requests, no server-side SEO
              assembly needed.
            </p>
          </header>
          <div className="bg-ink border border-border">
            <div
              className="flex gap-2 px-4 py-3 border-b border-graphite"
              aria-hidden="true"
            >
              <span className="w-[10px] h-[10px] rounded-full bg-danger inline-block" />
              <span className="w-[10px] h-[10px] rounded-full bg-highlighter inline-block" />
              <span className="w-[10px] h-[10px] rounded-full bg-success inline-block" />
            </div>
            <pre
              tabIndex={0}
              role="region"
              aria-label="Example API response for GET /public/v1/articles/how-to-price-consulting-services"
              className="font-mono text-[13px] text-white p-6 leading-[1.7] overflow-x-auto whitespace-pre focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
            >
              <code>{EXAMPLE_RESPONSE}</code>
            </pre>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Integration docs */}
        <section className="max-w-6xl mx-auto px-6 py-20" aria-label="Integration examples">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Integration
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Add it to your site in one request
            </h2>
            <p className="text-graphite max-w-xl mt-4 leading-relaxed text-pretty">
              Copy-paste examples for the most common setups. The same API works
              from any language or framework.{" "}
              <Link
                href="/github-publisher"
                className="text-ink underline underline-offset-2 hover:text-graphite transition-colors"
              >
                Publishing to a GitHub Pages repo instead?
              </Link>
            </p>
          </header>

          <div className="space-y-8">
            {/* Plain fetch */}
            <div>
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                Plain fetch
              </p>
              <div className="bg-ink border border-border">
                <div
                  className="flex gap-2 px-4 py-3 border-b border-graphite"
                  aria-hidden="true"
                >
                  <span className="w-[10px] h-[10px] rounded-full bg-danger inline-block" />
                  <span className="w-[10px] h-[10px] rounded-full bg-highlighter inline-block" />
                  <span className="w-[10px] h-[10px] rounded-full bg-success inline-block" />
                </div>
                <pre
                  tabIndex={0}
                  role="region"
                  aria-label="Plain fetch code example"
                  className="font-mono text-[13px] text-white p-6 leading-[1.7] overflow-x-auto whitespace-pre focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                >
                  <code>{FETCH_SAMPLE}</code>
                </pre>
              </div>
            </div>

            {/* Next.js */}
            <div>
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                Next.js App Router
              </p>
              <div className="bg-ink border border-border">
                <div
                  className="flex gap-2 px-4 py-3 border-b border-graphite"
                  aria-hidden="true"
                >
                  <span className="w-[10px] h-[10px] rounded-full bg-danger inline-block" />
                  <span className="w-[10px] h-[10px] rounded-full bg-highlighter inline-block" />
                  <span className="w-[10px] h-[10px] rounded-full bg-success inline-block" />
                </div>
                <pre
                  tabIndex={0}
                  role="region"
                  aria-label="Next.js App Router code example"
                  className="font-mono text-[13px] text-white p-6 leading-[1.7] overflow-x-auto whitespace-pre focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                >
                  <code>{NEXTJS_SAMPLE}</code>
                </pre>
              </div>
            </div>

            {/* Astro */}
            <div>
              <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                Astro
              </p>
              <div className="bg-ink border border-border">
                <div
                  className="flex gap-2 px-4 py-3 border-b border-graphite"
                  aria-hidden="true"
                >
                  <span className="w-[10px] h-[10px] rounded-full bg-danger inline-block" />
                  <span className="w-[10px] h-[10px] rounded-full bg-highlighter inline-block" />
                  <span className="w-[10px] h-[10px] rounded-full bg-success inline-block" />
                </div>
                <pre
                  tabIndex={0}
                  role="region"
                  aria-label="Astro code example"
                  className="font-mono text-[13px] text-white p-6 leading-[1.7] overflow-x-auto whitespace-pre focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                >
                  <code>{ASTRO_SAMPLE}</code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* Comparison table */}
        <section className="max-w-6xl mx-auto px-6 py-20" aria-label="Comparison with alternatives">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              Why PersonnaPress
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Built for blogs, not for everything
            </h2>
            <p className="text-graphite max-w-xl mt-4 leading-relaxed text-pretty">
              A Contentful alternative that writes the content for you and ships
              SEO data in every response.
            </p>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse border border-border max-w-2xl">
              <caption className="sr-only">
                PersonnaPress vs Contentful vs DropInBlog feature comparison
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
                    Contentful
                  </th>
                  <th
                    scope="col"
                    className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-6 py-4 border border-ink text-center"
                  >
                    DropInBlog
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
                      <ComparisonCell value={row.personnapress} />
                    </td>
                    <td className="border border-border px-6 py-4 text-center">
                      <ComparisonCell value={row.contentful} />
                    </td>
                    <td className="border border-border px-6 py-4 text-center">
                      <ComparisonCell value={row.dropinblog} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="border-t border-border" />

        {/* FAQ */}
        <section className="max-w-6xl mx-auto px-6 py-20" aria-label="Frequently asked questions">
          <header className="mb-14">
            <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
              FAQ
            </p>
            <h2 className="font-display text-4xl font-bold text-ink text-balance">
              Questions about the headless blog API
            </h2>
          </header>
          <FaqAccordion items={FAQ_ITEMS} />
        </section>

        <div className="border-t border-border" />

        {/* CTA: full-bleed Highlighter */}
        <section
          className="bg-highlighter px-6 py-24 text-center"
          aria-label="Get started"
        >
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-6">
            Get Started
          </p>
          <h2 className="font-display font-bold text-4xl text-ink mb-4 text-balance max-w-xl mx-auto">
            Your blog does not need a CMS.
          </h2>
          <p className="text-graphite max-w-xl mx-auto mb-4 leading-relaxed text-pretty">
            PersonnaPress handles content creation, storage, and delivery.
            Your site calls one endpoint and renders the result.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-ink text-paper font-medium px-8 py-4 shadow-brutal hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
          >
            Start free, no credit card
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
          <p className="font-mono text-xs text-graphite mt-6">
            14-day free trial. One API for content, SEO data, and images.
          </p>
        </section>

      </main>
    </>
  );
}
