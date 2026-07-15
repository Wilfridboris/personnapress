import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft } from "lucide-react";

export const revalidate = 3600;
export const dynamicParams = true;

const API_BASE = "https://api.personnapress.com";

interface ArticleSeo {
  reading_time_minutes: number;
  meta_description?: string | null;
  og?: { title?: string; description?: string; image?: string } | null;
  json_ld?: Record<string, unknown> | null;
}

interface ArticleDetail {
  slug: string;
  title: string;
  excerpt: string;
  featured_image_url: string | null;
  author: string;
  tags: string[];
  category: string | null;
  published_at: string;
  updated_at: string;
  reading_time_minutes: number;
  html: string;
  seo: ArticleSeo;
}

async function fetchArticle(slug: string): Promise<ArticleDetail | null> {
  const token = process.env.PERSONNAPRESS_DELIVERY_TOKEN;
  if (!token) return null;
  try {
    const res = await fetch(
      `${API_BASE}/public/v1/articles/${encodeURIComponent(slug)}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        next: { revalidate: 3600 },
      }
    );
    if (!res.ok) return null;
    const data = await res.json();
    if (!data?.slug || !data?.html) return null;
    return data as ArticleDetail;
  } catch {
    return null;
  }
}

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  try {
    const token = process.env.PERSONNAPRESS_DELIVERY_TOKEN;
    if (!token) return [];
    const res = await fetch(`${API_BASE}/public/v1/articles?page_size=50`, {
      headers: { Authorization: `Bearer ${token}` },
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.data ?? []).map((a: { slug: string }) => ({ slug: a.slug }));
  } catch {
    return [];
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = await fetchArticle(slug);
  if (!article) notFound();

  const rawTitle = `${article.title} | PersonnaPress Blog`;
  const title = rawTitle.length > 70 ? rawTitle.slice(0, 67) + "..." : rawTitle;
  const description = article.seo?.meta_description ?? article.excerpt ?? "";
  const ogTitle = article.seo?.og?.title ?? article.title;
  const ogDescription = article.seo?.og?.description ?? article.excerpt ?? "";
  const ogImageUrl = article.seo?.og?.image ?? article.featured_image_url;

  const metadata: Metadata = {
    title,
    description,
    alternates: { canonical: `/blog/${article.slug}` },
    openGraph: {
      title: ogTitle,
      description: ogDescription,
      url: `/blog/${article.slug}`,
      type: "article",
      ...(ogImageUrl
        ? {
            images: [
              {
                url: ogImageUrl,
                width: 1200,
                height: 630,
                alt: ogTitle,
              },
            ],
          }
        : {}),
    },
    twitter: { card: "summary_large_image", title: ogTitle, description: ogDescription },
  };

  return metadata;
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

export default async function BlogDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = await fetchArticle(slug);
  if (!article) notFound();

  return (
    <main className="min-h-screen bg-paper">
      {/* JSON-LD structured data */}
      {article.seo?.json_ld && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(article.seo.json_ld).replace(/</g, "\\u003c") }}
        />
      )}

      {/* Back nav */}
      <div className="max-w-3xl mx-auto px-6 pt-12">
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-sm"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Blog
        </Link>
      </div>

      {/* Article header */}
      <header className="max-w-3xl mx-auto px-6 pt-8 pb-10">
        <p className="font-mono text-xs text-graphite uppercase tracking-widest mb-4">
          {article.category ?? article.tags?.[0] ?? "Article"}
        </p>
        <h1 className="font-display text-4xl md:text-5xl font-bold text-ink text-balance leading-tight">
          {article.title}
        </h1>
        <div className="flex items-center gap-3 font-mono text-xs text-graphite mt-6 flex-wrap">
          <span>{article.author}</span>
          <span aria-hidden="true">&middot;</span>
          <time dateTime={article.published_at}>{formatDate(article.published_at)}</time>
          <span aria-hidden="true">&middot;</span>
          <span>{article.reading_time_minutes} min read</span>
        </div>
      </header>

      {/* Featured image */}
      {article.featured_image_url && (
        <div className="max-w-4xl mx-auto px-6 mb-12">
          <div className="border border-border overflow-hidden relative aspect-video">
            <Image
              src={article.featured_image_url}
              alt={article.title}
              fill
              style={{ objectFit: "cover" }}
              priority
              sizes="(max-width: 1024px) 100vw, 896px"
            />
          </div>
        </div>
      )}

      {/* Article body */}
      <div className="max-w-3xl mx-auto px-6 pb-16">
        {/* HTML sanitized by public API _strip_scripts(); safe to render as-is.
            H1 tags are demoted to H2 to preserve single-H1 invariant. */}
        <div
          className="prose prose-sm md:prose-base max-w-none font-sans text-ink
            prose-headings:font-display prose-headings:text-ink prose-headings:font-bold
            prose-a:text-ink prose-a:underline prose-a:underline-offset-2
            prose-img:border prose-img:border-border prose-img:rounded-none
            prose-blockquote:border-l-ink prose-blockquote:text-graphite
            prose-code:bg-highlight prose-code:text-ink prose-code:px-1 prose-code:rounded-none"
          dangerouslySetInnerHTML={{
            __html: article.html
              .replace(/<h1(\s|>)/gi, "<h2$1")
              .replace(/<\/h1>/gi, "</h2>"),
          }}
        />
      </div>

      {/* Bottom nav */}
      <div className="max-w-3xl mx-auto px-6 pb-24 border-t border-border pt-8 mt-4">
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-sm text-graphite hover:text-ink transition-colors focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 rounded-sm"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to Blog
        </Link>
      </div>
    </main>
  );
}
