import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";

export const dynamic = "force-static";

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: { absolute: "Headless Blog API Reference | PersonnaPress" },
    description:
      "Complete API reference for the PersonnaPress headless blog delivery API. Delivery token auth, all endpoints, parameters, error codes, and code examples.",
    alternates: {
      canonical: `${APP_URL}/headless-blog-api/docs`,
    },
    openGraph: {
      title: "Headless Blog API Reference | PersonnaPress",
      description:
        "Complete API reference for the PersonnaPress headless blog delivery API. Delivery token auth, all endpoints, parameters, error codes, and code examples.",
      type: "website",
      url: `${APP_URL}/headless-blog-api/docs`,
      images: [
        {
          url: "/images/PersonnaPress-opengraph.png",
          width: 1200,
          height: 630,
          alt: "PersonnaPress Headless Blog API Reference",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "Headless Blog API Reference | PersonnaPress",
      description:
        "Complete API reference for the PersonnaPress headless blog delivery API. Delivery token auth, all endpoints, parameters, error codes, and code examples.",
    },
  };
}

const jsonLdBreadcrumb = {
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    { "@type": "ListItem", position: 1, name: "PersonnaPress", item: APP_URL },
    {
      "@type": "ListItem",
      position: 2,
      name: "Headless Blog API",
      item: `${APP_URL}/headless-blog-api`,
    },
    {
      "@type": "ListItem",
      position: 3,
      name: "API Reference",
      item: `${APP_URL}/headless-blog-api/docs`,
    },
  ],
};

const jsonLdTechArticle = {
  "@context": "https://schema.org",
  "@type": "TechArticle",
  name: "Headless Blog API Reference",
  description:
    "Complete reference for the PersonnaPress headless blog delivery API. All endpoints, parameters, error codes, and code examples.",
  url: `${APP_URL}/headless-blog-api/docs`,
  author: { "@type": "Organization", name: "PersonnaPress" },
};

const TOC_SECTIONS = [
  { id: "quickstart", label: "Quickstart" },
  { id: "authentication", label: "Authentication" },
  { id: "list-articles", label: "List Articles" },
  { id: "get-article", label: "Get Article" },
  { id: "list-tags", label: "List Tags" },
  { id: "errors", label: "Error Reference" },
  { id: "caching", label: "Caching" },
  { id: "examples", label: "Code Examples" },
];

const AUTH_TERMINAL = `Authorization: Bearer ppd_abc123def456ghi789jkl012mno345pqr678stu`;

const LIST_ARTICLES_RESPONSE = `{
  "data": [
    {
      "slug": "how-to-price-consulting-services",
      "title": "How to Price Consulting Services Without Guessing",
      "excerpt": "Most consultants underprice because they anchor to hourly rates.",
      "featured_image_url": "https://cdn.personnapress.com/images/how-to-price-consulting.jpg",
      "featured_image_alt": "Chart showing value-based pricing vs hourly rates",
      "author": "Alex Morgan",
      "tags": ["consulting", "pricing"],
      "category": "Business",
      "published_at": "2026-07-14T09:00:00+00:00",
      "updated_at": "2026-07-14T10:23:00+00:00",
      "reading_time_minutes": 7
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 42
  }
}`;

const GET_ARTICLE_RESPONSE = `{
  "slug": "how-to-price-consulting-services",
  "title": "How to Price Consulting Services Without Guessing",
  "excerpt": "Most consultants underprice because they anchor to hourly rates.",
  "featured_image_url": "https://cdn.personnapress.com/images/how-to-price-consulting.jpg",
  "featured_image_alt": "Chart showing value-based pricing vs hourly rates",
  "author": "Alex Morgan",
  "tags": ["consulting", "pricing"],
  "category": "Business",
  "published_at": "2026-07-14T09:00:00+00:00",
  "updated_at": "2026-07-14T10:23:00+00:00",
  "reading_time_minutes": 7,
  "html": "<h2>The problem with hourly pricing</h2><p>When you charge by the hour...</p>",
  "seo": {
    "reading_time_minutes": 7,
    "json_ld": {
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "How to Price Consulting Services Without Guessing",
      "datePublished": "2026-07-14T09:00:00+00:00",
      "author": { "@type": "Person", "name": "Alex Morgan" }
    },
    "meta_description": "Learn how to price consulting services based on value, not hours.",
    "og": {
      "title": "How to Price Consulting Services Without Guessing",
      "description": "Learn how to price consulting services based on value.",
      "image": "https://cdn.personnapress.com/images/how-to-price-consulting.jpg"
    }
  }
}`;

const LIST_TAGS_RESPONSE = `{
  "tags": [
    { "name": "consulting", "count": 12 },
    { "name": "pricing", "count": 8 },
    { "name": "freelance", "count": 5 }
  ],
  "categories": [
    { "name": "Business", "count": 18 },
    { "name": "Marketing", "count": 9 }
  ]
}`;

const ERROR_RESPONSE = `{
  "detail": {
    "error": {
      "code": "INVALID_DELIVERY_TOKEN",
      "message": "Missing or invalid delivery token."
    }
  }
}`;

const CACHE_HEADERS_TERMINAL = `Cache-Control: public, max-age=60, stale-while-revalidate=300
ETag: W/"a3f9bc12de56f789"`;

const CACHE_NEXTJS_TERMINAL = `const res = await fetch(\`\${API}/articles/\${slug}\`, {
  headers: { Authorization: \`Bearer \${TOKEN}\` },
  next: { revalidate: 60 },  // ISR: re-fetch at most every 60 s
});`;

const CURL_SAMPLE = `# List articles
curl --silent --fail-with-body \\
  "https://api.personnapress.com/public/v1/articles?page_size=20" \\
  -H "Authorization: Bearer ppd_your_token_here"

# Get a single article
curl --silent --fail-with-body \\
  "https://api.personnapress.com/public/v1/articles/how-to-price-consulting-services" \\
  -H "Authorization: Bearer ppd_your_token_here"`;

const PLAIN_FETCH_SAMPLE = `const TOKEN = "ppd_your_token_here";
const API = "https://api.personnapress.com/public/v1";

// List articles (index page)
const listRes = await fetch(\`\${API}/articles?page_size=20\`, {
  headers: { Authorization: \`Bearer \${TOKEN}\` },
});
if (!listRes.ok) throw new Error(\`HTTP \${listRes.status}\`);
const { data, meta } = await listRes.json();

// Get a single article (detail page)
const articleRes = await fetch(
  \`\${API}/articles/how-to-price-consulting-services\`,
  { headers: { Authorization: \`Bearer \${TOKEN}\` } }
);
if (!articleRes.ok) throw new Error(\`HTTP \${articleRes.status}\`);
const article = await articleRes.json();

document.querySelector("h1").textContent = article.title;
document.querySelector("article").innerHTML = article.html;`;

const NEXTJS_SAMPLE = `// app/blog/[slug]/page.tsx
import type { Metadata } from "next";

const API = "https://api.personnapress.com/public/v1";
const TOKEN = process.env.PERSONNAPRESS_DELIVERY_TOKEN!;

async function getArticle(slug: string) {
  const res = await fetch(\`\${API}/articles/\${slug}\`, {
    headers: { Authorization: \`Bearer \${TOKEN}\` },
    next: { revalidate: 60 },
  });
  if (!res.ok) return null;
  return res.json();
}

export async function generateStaticParams() {
  const res = await fetch(\`\${API}/articles?page_size=50\`, {
    headers: { Authorization: \`Bearer \${TOKEN}\` },
    next: { revalidate: 3600 },
  });
  if (!res.ok) return [];
  const { data } = await res.json();
  return data.map(({ slug }: { slug: string }) => ({ slug }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const { slug } = await params;
  const article = await getArticle(slug);
  if (!article) return {};
  return {
    title: article.title,
    ...(article.seo.meta_description && {
      description: article.seo.meta_description,
    }),
    ...(article.seo.og && { openGraph: article.seo.og }),
  };
}

export default async function BlogPostPage(
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const article = await getArticle(slug);
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
if (!res.ok) return Astro.redirect("/404");
const article = await res.json();
---

<html lang="en">
  <head>
    <title>{article.title}</title>
    {article.seo.meta_description && (
      <meta name="description" content={article.seo.meta_description} />
    )}
    {article.seo.og?.title && (
      <meta property="og:title" content={article.seo.og.title} />
    )}
    {article.seo.og?.image && (
      <meta property="og:image" content={article.seo.og.image} />
    )}
    <script
      type="application/ld+json"
      set:html={JSON.stringify(article.seo.json_ld)}
    />
  </head>
  <body>
    <img
      src={article.featured_image_url}
      alt={article.featured_image_alt ?? article.title}
    />
    <h1>{article.title}</h1>
    <article set:html={article.html} />
  </body>
</html>`;

const SVELTEKIT_SAMPLE = `// src/routes/blog/[slug]/+page.server.ts
import type { PageServerLoad } from "./$types";
import { error } from "@sveltejs/kit";

export const load: PageServerLoad = async ({ params, fetch }) => {
  const res = await fetch(
    \`https://api.personnapress.com/public/v1/articles/\${params.slug}\`,
    {
      headers: {
        Authorization: \`Bearer \${import.meta.env.PERSONNAPRESS_TOKEN}\`,
      },
    }
  );
  if (!res.ok) {
    throw error(404, "Article not found");
  }
  const article = await res.json();
  return { article };
};`;

// TerminalBlock: exact pattern from headless-blog-api/page.tsx
function TerminalBlock({ content, ariaLabel }: { content: string; ariaLabel: string }) {
  return (
    <div className="bg-ink border border-border">
      <div className="flex gap-2 px-4 py-3 border-b border-graphite" aria-hidden="true">
        <span className="w-[10px] h-[10px] rounded-full bg-danger inline-block" />
        <span className="w-[10px] h-[10px] rounded-full bg-highlighter inline-block" />
        <span className="w-[10px] h-[10px] rounded-full bg-success inline-block" />
      </div>
      <pre
        tabIndex={0}
        role="region"
        aria-label={ariaLabel}
        className="font-mono text-[13px] text-white p-6 leading-[1.7] overflow-x-auto whitespace-pre focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
      >
        <code>{content}</code>
      </pre>
    </div>
  );
}

interface ParamRow {
  name: string;
  type: string;
  defaultVal: string;
  description: string;
  required?: boolean;
}

function ParamTable({ caption, rows }: { caption: string; rows: ParamRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse border border-border">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="bg-ink">
            <th
              scope="col"
              className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
            >
              Parameter
            </th>
            <th
              scope="col"
              className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
            >
              Type
            </th>
            <th
              scope="col"
              className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
            >
              Default
            </th>
            <th
              scope="col"
              className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
            >
              Description
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name}>
              <th
                scope="row"
                className="font-mono text-sm text-ink px-4 py-3 border border-border text-left font-normal"
              >
                {row.name}
                {row.required ? (
                  <span className="font-mono text-[10px] bg-danger-muted text-danger border border-danger px-1.5 py-0.5 ml-2">
                    required
                  </span>
                ) : (
                  <span className="font-mono text-[10px] text-graphite ml-2">optional</span>
                )}
              </th>
              <td className="font-mono text-sm text-graphite px-4 py-3 border border-border">
                {row.type}
              </td>
              <td className="font-mono text-sm text-graphite px-4 py-3 border border-border">
                {row.defaultVal}
              </td>
              <td className="text-sm text-ink px-4 py-3 border border-border">
                {row.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface ErrorRow {
  code: string;
  status: string;
  when: string;
}

function ErrorTable({ rows }: { rows: ErrorRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse border border-border">
        <caption className="sr-only">
          API error codes, HTTP status codes, and conditions that trigger them
        </caption>
        <thead>
          <tr className="bg-ink">
            <th
              scope="col"
              className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
            >
              Error Code
            </th>
            <th
              scope="col"
              className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
            >
              HTTP Status
            </th>
            <th
              scope="col"
              className="text-paper font-mono text-[11px] uppercase tracking-[0.06em] px-4 py-3 border border-ink text-left"
            >
              When it fires
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.code}>
              <th
                scope="row"
                className="font-mono text-sm text-ink px-4 py-3 border border-border text-left font-normal"
              >
                {row.code}
              </th>
              <td className="font-mono text-sm text-graphite px-4 py-3 border border-border">
                {row.status}
              </td>
              <td className="text-sm text-ink px-4 py-3 border border-border">{row.when}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface EndpointBlockProps {
  method: string;
  path: string;
  description: string;
  params?: ParamRow[];
  paramsCaption?: string;
  responseJson: string;
  responseAriaLabel: string;
  children?: React.ReactNode;
}

function EndpointBlock({
  method,
  path,
  description,
  params,
  paramsCaption,
  responseJson,
  responseAriaLabel,
  children,
}: EndpointBlockProps) {
  return (
    <div className="border border-border">
      <div className="border-b border-border px-6 py-4 flex items-baseline gap-3 flex-wrap">
        <span className="border border-success bg-success-muted text-success font-mono text-xs px-2 py-0.5">
          {method}
        </span>
        <code className="font-mono text-base text-ink">{path}</code>
        <span className="text-sm text-graphite">{description}</span>
      </div>
      {children && (
        <div className="px-6 py-4 border-b border-border text-sm text-ink leading-relaxed">
          {children}
        </div>
      )}
      {params && params.length > 0 && (
        <div className="px-6 py-4 border-b border-border">
          <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-3">
            Query Parameters
          </p>
          <ParamTable
            caption={paramsCaption ?? `Parameters for ${method} ${path}`}
            rows={params}
          />
        </div>
      )}
      <div className="px-6 py-4">
        <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-3">Response</p>
        <TerminalBlock content={responseJson} ariaLabel={responseAriaLabel} />
      </div>
    </div>
  );
}

const LIST_ARTICLES_PARAMS: ParamRow[] = [
  {
    name: "page",
    type: "int",
    defaultVal: "1",
    description: "Page number for pagination.",
    required: false,
  },
  {
    name: "page_size",
    type: "int",
    defaultVal: "20",
    description: "Items per page. Minimum 1, maximum 50.",
    required: false,
  },
  {
    name: "tag",
    type: "string",
    defaultVal: "-",
    description: "Filter articles by tag slug. Returns only articles with this tag.",
    required: false,
  },
  {
    name: "category",
    type: "string",
    defaultVal: "-",
    description: "Filter articles by category name. Case-insensitive.",
    required: false,
  },
];

const ERROR_ROWS: ErrorRow[] = [
  {
    code: "INVALID_DELIVERY_TOKEN",
    status: "401",
    when: "Token missing, malformed, revoked, or does not match any active token.",
  },
  {
    code: "ARTICLE_NOT_FOUND",
    status: "404",
    when: "Slug does not exist, article is hidden, or belongs to another client.",
  },
  {
    code: "RATE_LIMIT_EXCEEDED",
    status: "429",
    when: "More than 120 requests per minute for this token.",
  },
  {
    code: "INTERNAL_ERROR",
    status: "500",
    when: "Unexpected server error. Retry with exponential backoff.",
  },
];

export default function HeadlessBlogApiDocsPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdBreadcrumb) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdTechArticle) }}
      />

      <div className="-mt-8 -mx-4">
        {/* Page header */}
        <div className="max-w-7xl mx-auto px-6 py-10 border-b border-border">
          <nav aria-label="Breadcrumb" className="mb-4">
            <Link
              href="/headless-blog-api"
              aria-label="Back to Headless Blog API overview"
              className="inline-flex items-center gap-1.5 font-mono text-xs text-graphite hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
            >
              <ArrowLeft className="size-3" aria-hidden="true" />
              Headless Blog API
            </Link>
          </nav>
          <h1 className="font-display text-4xl lg:text-5xl font-bold text-ink text-balance mb-4">
            API Reference
          </h1>
          <p className="text-graphite text-pretty max-w-2xl">
            Complete reference for the PersonnaPress headless blog delivery API. All endpoints,
            parameters, error codes, and copy-paste integration examples.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="max-w-7xl mx-auto flex">
          {/* Desktop sidebar */}
          <aside className="hidden lg:block w-56 shrink-0 border-r border-border">
            <nav aria-label="On this page" className="sticky top-20 p-6">
              <p className="font-mono text-[10px] uppercase tracking-widest text-graphite/50 mb-3">
                On this page
              </p>
              <ul className="space-y-0.5">
                {TOC_SECTIONS.map((section) => (
                  <li key={section.id}>
                    <a
                      href={`#${section.id}`}
                      className="block font-mono text-xs text-graphite hover:text-ink transition-colors py-1.5 focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
                    >
                      {section.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>

          {/* Content area */}
          <div className="flex-1 min-w-0 px-6 lg:px-10 py-10">
            {/* Mobile pill strip */}
            <nav
              aria-label="Jump to section"
              className="flex gap-3 overflow-x-auto py-3 mb-8 border-b border-border lg:hidden"
            >
              {TOC_SECTIONS.map((section) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  className="font-mono text-xs border border-border px-3 py-1.5 whitespace-nowrap hover:text-ink hover:border-ink transition-colors focus-visible:outline-2 focus-visible:outline-ink focus-visible:outline-offset-2"
                >
                  {section.label}
                </a>
              ))}
            </nav>

            <div className="max-w-3xl space-y-16">
              {/* Quickstart */}
              <section id="quickstart">
                <h2 className="font-display text-2xl font-bold text-ink mb-6">Quickstart</h2>
                <ol
                  role="list"
                  className="grid grid-cols-1 md:grid-cols-3 gap-px border border-border bg-border list-none"
                >
                  <li className="bg-paper p-6">
                    <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
                      Step 01
                    </p>
                    <p className="font-display text-base font-bold text-ink mb-2">Get your token</p>
                    <p className="text-sm text-graphite leading-relaxed text-pretty">
                      In the app, go to your client, then the Connections tab, then the Delivery API
                      section. Click Create token, give it a name, and copy the{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        ppd_...
                      </code>{" "}
                      value. You will only see the full token once.
                    </p>
                    <Link
                      href="/dashboard"
                      className="inline-flex items-center gap-1.5 text-sm underline underline-offset-2 hover:text-graphite transition-colors mt-3"
                    >
                      Open the app{" "}
                      <ExternalLink className="size-3" aria-hidden="true" />
                    </Link>
                  </li>
                  <li className="bg-paper p-6">
                    <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
                      Step 02
                    </p>
                    <p className="font-display text-base font-bold text-ink mb-2">Call the API</p>
                    <p className="text-sm text-graphite leading-relaxed text-pretty">
                      Send a GET request to{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        https://api.personnapress.com/public/v1/articles
                      </code>{" "}
                      with{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        Authorization: Bearer ppd_your_token
                      </code>{" "}
                      in the header. The response is a paginated JSON object.
                    </p>
                  </li>
                  <li className="bg-paper p-6">
                    <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-3">
                      Step 03
                    </p>
                    <p className="font-display text-base font-bold text-ink mb-2">
                      Render the result
                    </p>
                    <p className="text-sm text-graphite leading-relaxed text-pretty">
                      Use{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        article.html
                      </code>{" "}
                      for the post body and pass the{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        seo
                      </code>{" "}
                      object fields to your page metadata. The{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        seo.json_ld
                      </code>{" "}
                      block is ready to embed as-is.
                    </p>
                  </li>
                </ol>
              </section>

              {/* Authentication */}
              <section id="authentication">
                <h2 className="font-display text-2xl font-bold text-ink mb-6">Authentication</h2>
                <div className="space-y-4 text-sm text-ink leading-relaxed">
                  <p>
                    All requests require an{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      Authorization
                    </code>{" "}
                    header in the format{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      Bearer ppd_&lt;token&gt;
                    </code>
                    . Delivery tokens always start with the prefix{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      ppd_
                    </code>
                    . Do not use session cookies or API keys from the app dashboard.
                  </p>
                  <p>
                    A missing, revoked, or malformed token returns{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      401 INVALID_DELIVERY_TOKEN
                    </code>
                    .
                  </p>
                </div>
                <div className="mt-4">
                  <TerminalBlock
                    content={AUTH_TERMINAL}
                    ariaLabel="Authorization header format for the PersonnaPress delivery API"
                  />
                </div>
                <p className="text-sm text-graphite mt-4">
                  The API allows 120 requests per minute per token. Exceeding this returns{" "}
                  <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                    429 RATE_LIMIT_EXCEEDED
                  </code>
                  .
                </p>
              </section>

              {/* List Articles */}
              <section id="list-articles">
                <h2 className="font-display text-2xl font-bold text-ink mb-6">List Articles</h2>
                <EndpointBlock
                  method="GET"
                  path="/public/v1/articles"
                  description="Returns a paginated list of published articles."
                  params={LIST_ARTICLES_PARAMS}
                  paramsCaption="Query parameters for GET /public/v1/articles"
                  responseJson={LIST_ARTICLES_RESPONSE}
                  responseAriaLabel="Example response for GET /public/v1/articles showing paginated article list"
                >
                  <p className="text-sm text-graphite italic">
                    Note: the{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      html
                    </code>{" "}
                    and{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      seo
                    </code>{" "}
                    fields are not included in list responses. Fetch{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      GET /public/v1/articles/{"{slug}"}
                    </code>{" "}
                    for the full article.
                  </p>
                </EndpointBlock>
              </section>

              {/* Get Article */}
              <section id="get-article">
                <h2 className="font-display text-2xl font-bold text-ink mb-6">Get Article</h2>
                <EndpointBlock
                  method="GET"
                  path="/public/v1/articles/{slug}"
                  description="Returns a single article with full HTML content and SEO data."
                  responseJson={GET_ARTICLE_RESPONSE}
                  responseAriaLabel="Example response for GET /public/v1/articles/slug showing all article fields"
                >
                  <div className="space-y-2">
                    <p>
                      <strong>Path parameter:</strong>{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        slug
                      </code>{" "}
                      (string, required) - the article&apos;s URL slug, obtained from the list
                      response.
                    </p>
                    <p className="text-graphite">
                      The{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        meta_description
                      </code>{" "}
                      and{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        og
                      </code>{" "}
                      fields inside{" "}
                      <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                        seo
                      </code>{" "}
                      are conditional: present only when the article has those fields populated. A
                      404 is returned for hidden articles, unknown slugs, or articles belonging to
                      another client - all cases are indistinguishable by design.
                    </p>
                  </div>
                </EndpointBlock>
              </section>

              {/* List Tags */}
              <section id="list-tags">
                <h2 className="font-display text-2xl font-bold text-ink mb-6">List Tags</h2>
                <EndpointBlock
                  method="GET"
                  path="/public/v1/tags"
                  description="Returns all tags and categories with article counts."
                  responseJson={LIST_TAGS_RESPONSE}
                  responseAriaLabel="Example response for GET /public/v1/tags showing tags and categories with counts"
                >
                  <p className="text-sm text-graphite">
                    Use this endpoint to build tag clouds, category navigation, or filtered list
                    pages on your site.
                  </p>
                </EndpointBlock>
              </section>

              {/* Error Reference */}
              <section id="errors">
                <h2 className="font-display text-2xl font-bold text-ink mb-6">Error Reference</h2>
                <ErrorTable rows={ERROR_ROWS} />
                <div className="mt-6">
                  <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-3">
                    Error response shape
                  </p>
                  <TerminalBlock
                    content={ERROR_RESPONSE}
                    ariaLabel="Error response JSON shape for the PersonnaPress delivery API"
                  />
                </div>
              </section>

              {/* Caching */}
              <section id="caching">
                <h2 className="font-display text-2xl font-bold text-ink mb-6">Caching</h2>
                <div className="space-y-4 text-sm text-ink leading-relaxed mb-6">
                  <p>
                    All successful responses include{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      Cache-Control: public, max-age=60, stale-while-revalidate=300
                    </code>
                    . CDNs and browsers may cache the response for 60 seconds and continue serving
                    it stale for up to 300 seconds while revalidating in the background.
                  </p>
                  <p>
                    All responses also include an{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      ETag
                    </code>{" "}
                    header. Send it back as{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      If-None-Match
                    </code>{" "}
                    on subsequent requests to receive{" "}
                    <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                      304 Not Modified
                    </code>{" "}
                    and save bandwidth.
                  </p>
                </div>
                <div className="space-y-6">
                  <div>
                    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-3">
                      Response headers
                    </p>
                    <TerminalBlock
                      content={CACHE_HEADERS_TERMINAL}
                      ariaLabel="Cache-Control and ETag response headers from the PersonnaPress delivery API"
                    />
                  </div>
                  <div>
                    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-3">
                      Next.js revalidation pattern
                    </p>
                    <TerminalBlock
                      content={CACHE_NEXTJS_TERMINAL}
                      ariaLabel="Next.js fetch call with next.revalidate for ISR integration"
                    />
                  </div>
                </div>
                <p className="text-sm text-graphite mt-4">
                  Note: 401, 404, and 429 responses are sent with{" "}
                  <code className="font-mono text-sm bg-border text-ink px-1.5 py-0.5">
                    Cache-Control: no-store
                  </code>{" "}
                  and must not be cached.
                </p>
              </section>

              {/* Code Examples */}
              <section id="examples">
                <h2 className="font-display text-2xl font-bold text-ink mb-2">Code Examples</h2>
                <p className="text-sm text-graphite mb-8 text-pretty">
                  Copy-paste samples for common environments. The endpoint URL and header format are
                  the same in every language.
                </p>
                <div className="space-y-8">
                  <div>
                    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                      cURL
                    </p>
                    <TerminalBlock
                      content={CURL_SAMPLE}
                      ariaLabel="cURL code examples for list and detail endpoints"
                    />
                  </div>
                  <div>
                    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                      Plain fetch
                    </p>
                    <TerminalBlock
                      content={PLAIN_FETCH_SAMPLE}
                      ariaLabel="Plain JavaScript fetch examples for list and detail endpoints"
                    />
                  </div>
                  <div>
                    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                      Next.js App Router
                    </p>
                    <TerminalBlock
                      content={NEXTJS_SAMPLE}
                      ariaLabel="Next.js App Router integration with generateStaticParams, generateMetadata, and ISR"
                    />
                  </div>
                  <div>
                    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                      Astro
                    </p>
                    <TerminalBlock
                      content={ASTRO_SAMPLE}
                      ariaLabel="Astro integration example for rendering blog posts from the PersonnaPress API"
                    />
                  </div>
                  <div>
                    <p className="font-mono text-xs text-graphite tracking-widest uppercase mb-4">
                      SvelteKit
                    </p>
                    <TerminalBlock
                      content={SVELTEKIT_SAMPLE}
                      ariaLabel="SvelteKit page.server.ts load function for fetching articles from the PersonnaPress API"
                    />
                  </div>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
