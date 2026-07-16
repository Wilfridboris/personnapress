import type { Metadata } from "next";
import { redirect } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";

export const revalidate = 3600;

const API_BASE = "https://api.personnapress.com";

interface ArticleListItem {
  slug: string;
  title: string;
  excerpt: string;
  featured_image_url: string | null;
  featured_image_alt: string | null;
  author: string;
  tags: string[];
  category: string | null;
  published_at: string;
  updated_at: string;
  reading_time_minutes: number;
}

interface ArticleListResponse {
  data: ArticleListItem[];
  meta: { page: number; page_size: number; total: number };
}

async function fetchArticles(page: number): Promise<ArticleListResponse> {
  const token = process.env.PERSONNAPRESS_DELIVERY_TOKEN;
  if (!token) {
    return { data: [], meta: { page: 1, page_size: 9, total: 0 } };
  }
  try {
    const res = await fetch(
      `${API_BASE}/public/v1/articles?page=${page}&page_size=9`,
      {
        headers: { Authorization: `Bearer ${token}` },
        next: { revalidate: 3600 },
      }
    );
    if (!res.ok) return { data: [], meta: { page: 1, page_size: 9, total: 0 } };
    const data = await res.json();
    if (!Array.isArray(data?.data) || !data?.meta) {
      return { data: [], meta: { page: 1, page_size: 9, total: 0 } };
    }
    return data as ArticleListResponse;
  } catch {
    return { data: [], meta: { page: 1, page_size: 9, total: 0 } };
  }
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(new Date(iso));
  } catch {
    return "";
  }
}

export const metadata: Metadata = {
  title: "Blog",
  description:
    "Insights on AI writing, brand voice, and content strategy from Boris Kwayep and the PersonnaPress team.",
  alternates: { canonical: "/blog" },
  openGraph: {
    title: "Blog | PersonnaPress",
    description:
      "Insights on AI writing, brand voice, and content strategy from Boris Kwayep and the PersonnaPress team.",
    url: "/blog",
    type: "website",
    images: [
      {
        url: "/images/PersonnaPress-opengraph.png",
        width: 1200,
        height: 630,
        alt: "PersonnaPress Blog",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Blog | PersonnaPress",
    description:
      "Insights on AI writing, brand voice, and content strategy from Boris Kwayep and the PersonnaPress team.",
  },
};

const APP_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");

const schemaBlog = {
  "@context": "https://schema.org",
  "@type": "Blog",
  name: "PersonnaPress Blog",
  description: "Insights on AI writing, brand voice, and content strategy.",
  url: `${APP_URL}/blog`,
  author: {
    "@type": "Person",
    name: "Boris Kwayep",
    url: APP_URL,
  },
  publisher: {
    "@type": "Organization",
    name: "PersonnaPress",
    url: APP_URL,
  },
};

export default async function BlogListPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const parsed = parseInt(params.page ?? "1", 10);
  const page = Number.isNaN(parsed) ? 1 : Math.max(1, parsed);
  const articles = await fetchArticles(page);
  const pageSize = articles.meta.page_size || 9;
  const totalPages = Math.ceil(articles.meta.total / pageSize);
  if (totalPages > 0 && page > totalPages) redirect(`/blog?page=${totalPages}`);
  const featured = articles.data[0] ?? null;
  const rest = articles.data.slice(1);

  return (
    <main className="min-h-screen bg-paper">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaBlog) }}
      />
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-12">
        <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-4">
          The PersonnaPress Blog
        </p>
        <h1 className="font-display text-5xl md:text-6xl font-bold text-ink text-balance leading-tight">
          AI Content Marketing, Brand Voice &amp; Publishing Strategy.
        </h1>
        <p className="mt-6 text-graphite max-w-2xl text-pretty leading-relaxed">
          Practical writing on AI-generated content, brand voice strategy, and publishing
          from the team building PersonnaPress.
        </p>
        <div className="border-t border-border mt-12" />
      </section>

      <div className="max-w-6xl mx-auto px-6 pb-20">
        {articles.data.length === 0 ? (
          /* Empty state */
          <div className="py-32 text-center">
            <h2 className="font-display text-3xl font-bold text-ink mb-4 text-balance">
              Nothing published yet.
            </h2>
            <p className="text-graphite text-pretty">
              New articles will appear here as soon as they are published.
            </p>
          </div>
        ) : (
          <>
            {/* Featured article */}
            {featured && (
              <article className="border border-border bg-paper mb-px">
                <div className="md:grid md:grid-cols-2">
                  {/* Image side */}
                  <div className="relative overflow-hidden min-h-[240px] bg-highlight">
                    {featured.featured_image_url ? (
                      <Image
                        src={featured.featured_image_url}
                        alt={featured.featured_image_alt || featured.title}
                        fill
                        priority
                        style={{ objectFit: "cover" }}
                        sizes="(max-width: 768px) 100vw, 50vw"
                      />
                    ) : null}
                  </div>

                  {/* Content side */}
                  <div className="p-8 md:p-12 flex flex-col justify-center">
                    <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-4">
                      {featured.category ?? featured.tags?.[0] ?? "General"}
                    </p>
                    <h2 className="font-display text-3xl md:text-4xl font-bold text-ink text-balance leading-snug mb-4">
                      {featured.title}
                    </h2>
                    <p className="text-graphite text-pretty leading-relaxed mb-6 line-clamp-4">
                      {featured.excerpt}
                    </p>
                    <p className="font-mono text-xs text-graphite mb-6">
                      {featured.author || "Boris Kwayep"} &middot; {formatDate(featured.published_at)} &middot;{" "}
                      {featured.reading_time_minutes} min read
                    </p>
                    <Link
                      href={`/blog/${featured.slug}`}
                      className="inline-flex items-center gap-2 text-sm font-medium text-ink border-b border-ink pb-0.5 hover:border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 self-start"
                    >
                      Read article
                      <ArrowRight className="size-4" aria-hidden="true" />
                    </Link>
                  </div>
                </div>
              </article>
            )}

            {/* Article grid */}
            {rest.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-border border border-border mt-px">
                {rest.map((article, index) => (
                  <Link
                    key={article.slug}
                    href={`/blog/${article.slug}`}
                    className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2"
                  >
                    <article
                      className="bg-paper group hover:bg-highlight transition-colors flex flex-col h-full [animation:none] motion-safe:[animation:card-in_0.35s_ease-out_both]"
                      style={{ animationDelay: `${index * 60}ms` }}
                    >
                      {article.featured_image_url && (
                        <div className="relative overflow-hidden aspect-video">
                          <Image
                            src={article.featured_image_url}
                            alt={article.featured_image_alt || article.title}
                            fill
                            style={{ objectFit: "cover" }}
                            sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
                          />
                        </div>
                      )}
                      <div className="p-6 flex flex-col flex-1">
                        <p className="font-mono text-xs text-graphite uppercase tracking-widest">
                          {article.category ?? article.tags?.[0] ?? "General"}
                        </p>
                        <h2 className="font-display text-xl font-bold text-ink text-balance leading-snug mt-2 mb-3">
                          {article.title}
                        </h2>
                        <p className="text-sm text-graphite text-pretty leading-relaxed line-clamp-3 flex-1">
                          {article.excerpt}
                        </p>
                        <p className="font-mono text-xs text-graphite mt-4">
                          {article.author || "Boris Kwayep"} &middot; {formatDate(article.published_at)} &middot;{" "}
                          {article.reading_time_minutes} min read
                        </p>
                        <ArrowRight
                          className="mt-4 self-end size-4 text-graphite group-hover:text-ink transition-colors"
                          aria-hidden="true"
                        />
                      </div>
                    </article>
                  </Link>
                ))}
              </div>
            )}

            {/* Pagination */}
            {articles.meta.total > articles.meta.page_size && (
              <nav
                aria-label="Blog pagination"
                className="flex items-center justify-center gap-2 mt-12 mb-4"
              >
                {page === 1 ? (
                  <span
                    aria-disabled="true"
                    aria-label="Go to previous page"
                    className="border border-border px-4 py-2 text-sm font-medium text-ink opacity-40 pointer-events-none font-mono"
                  >
                    Prev
                  </span>
                ) : (
                  <Link
                    href={`/blog?page=${page - 1}`}
                    aria-label="Go to previous page"
                    className="border border-border px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-paper transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 font-mono"
                  >
                    Prev
                  </Link>
                )}

                {getPaginationRange(page, totalPages).map((p) => (
                  <Link
                    key={p}
                    href={`/blog?page=${p}`}
                    aria-label={`Go to page ${p}`}
                    aria-current={p === page ? "page" : undefined}
                    className={`border px-4 py-2 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 font-mono ${
                      p === page
                        ? "bg-ink text-paper border-ink"
                        : "border-border text-ink hover:bg-ink hover:text-paper"
                    }`}
                  >
                    {p}
                  </Link>
                ))}

                {page === totalPages ? (
                  <span
                    aria-disabled="true"
                    aria-label="Go to next page"
                    className="border border-border px-4 py-2 text-sm font-medium text-ink opacity-40 pointer-events-none font-mono"
                  >
                    Next
                  </span>
                ) : (
                  <Link
                    href={`/blog?page=${page + 1}`}
                    aria-label="Go to next page"
                    className="border border-border px-4 py-2 text-sm font-medium text-ink hover:bg-ink hover:text-paper transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 font-mono"
                  >
                    Next
                  </Link>
                )}
              </nav>
            )}
          </>
        )}
      </div>

      <style>{`
        @keyframes card-in {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </main>
  );
}

function getPaginationRange(current: number, total: number): number[] {
  const delta = 2;
  const start = Math.max(1, current - delta);
  const end = Math.min(total, current + delta);
  const range: number[] = [];
  for (let i = start; i <= end; i++) range.push(i);
  return range;
}
