const BASE_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");

export const dynamic = "force-static";

// Plain-text summary of PersonnaPress for generative AI crawlers, following the
// llms.txt convention (https://llmstxt.org/). Curates the main public routes; the
// full URL set (including blog posts) lives in sitemap.xml, linked below.
function buildLlmsTxt(): string {
  return `# PersonnaPress

> PersonnaPress is an autonomous content engine that learns your brand voice and turns raw ideas into SEO-ranked blog posts and social campaigns that sound like you, not generic AI. You approve everything before it publishes to WordPress, Webflow, GitHub Pages, LinkedIn, X, Facebook, Instagram, and Threads.

PersonnaPress is built for SaaS founders, business coaches, and marketing agencies who need consistent, on-brand publishing without writing everything themselves. It extracts your voice from existing content, structures every article for SEO, and runs the full idea-to-published loop after a single review.

## Core pages

- [Home](${BASE_URL}): AI blog writer that learns your brand voice and turns ideas into SEO-ranked blog posts and social campaigns.
- [Pricing](${BASE_URL}/pricing): Plans from $29 per month for individuals, growing businesses, and agencies. 14-day free trial, no credit card required.
- [About the founder](${BASE_URL}/about): Boris Kwayep, founder of PersonnaPress, and why he built it.
- [Blog](${BASE_URL}/blog): Insights on AI writing, brand voice, and content strategy.

## Product

- [Brand Voice Generator](${BASE_URL}/brand-voice-generator): Extracts your brand voice from existing content and applies it to every blog post and social update automatically.
- [GitHub Pages publisher](${BASE_URL}/github-publisher): Auto-publishes AI-written posts to Jekyll, Astro, Hugo, Next.js, or Eleventy repos with no config.
- [Headless Blog API](${BASE_URL}/headless-blog-api): Store blog content in PersonnaPress and fetch it on your own site through one API. A Contentful alternative built for blogs, with SEO data included.
- [Headless Blog API reference](${BASE_URL}/headless-blog-api/docs): Delivery token auth, all endpoints, parameters, error codes, and code examples.

## Comparisons and alternatives

- [Best AI blog writers](${BASE_URL}/best-ai-blog-writers): Honest 2026 ranking of PersonnaPress, Writesonic, Jasper, and Copy.ai by publishing depth, voice fidelity, and price.
- [Jasper alternatives](${BASE_URL}/jasper-alternatives): PersonnaPress vs Jasper on voice fidelity, autonomous publishing, and price.
- [Copy.ai alternatives](${BASE_URL}/copy-ai-alternatives): PersonnaPress vs Copy.ai on blog publishing, voice fidelity, and price.
- [Writesonic alternatives](${BASE_URL}/writesonic-alternatives): PersonnaPress vs Writesonic on voice fidelity, social publishing, and price.

## By role

- [AI blog writer for SaaS founders](${BASE_URL}/ai-blog-writer-for-saas-founders): Learns your voice, writes SEO-structured articles, and publishes to your blog and social channels automatically.
- [AI content for coaches](${BASE_URL}/ai-content-for-coaches): Generates articles and social posts in your coaching voice so you stay visible without ghostwriters.
- [White-label content for agencies](${BASE_URL}/white-label-content-for-agencies): One workspace per client, each with its own brand voice, publishing to the client's channels.

## Contact

- Support email: support@personnapress.com

## Optional

- [Sitemap](${BASE_URL}/sitemap.xml): Full list of public URLs, including individual blog posts.
- [Privacy Policy](${BASE_URL}/privacy): How PersonnaPress handles your data.
- [Terms of Service](${BASE_URL}/terms): Terms for using PersonnaPress.
`;
}

export function GET(): Response {
  return new Response(buildLlmsTxt(), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
