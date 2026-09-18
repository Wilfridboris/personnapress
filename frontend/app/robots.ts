import type { MetadataRoute } from "next";

const BASE_URL = (process.env.NEXT_PUBLIC_APP_URL ?? "https://www.personnapress.com").replace(/\/$/, "");

// Authenticated app areas that no crawler should index. Kept in step with the
// private routes gated by proxy.ts (everything not in its public allowlist).
const DISALLOW = [
  "/account",
  "/analytics",
  "/articles",
  "/calendar",
  "/campaigns",
  "/clients",
  "/dashboard",
  "/onboarding",
  "/roadmap",
  "/settings",
];

// Search and AI crawlers get their own explicit User-agent groups so intent is
// documented for AEO/GEO. A named group overrides the wildcard rule, so each must
// restate DISALLOW or it would inherit no blocks and could crawl the gated app.
const EXPLICIT_BOTS = [
  "GPTBot",
  "OAI-SearchBot",
  "PerplexityBot",
  "Googlebot",
  "Google-Extended",
  "anthropic-ai",
  "ClaudeBot",
  "CCBot",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: DISALLOW },
      ...EXPLICIT_BOTS.map((userAgent) => ({ userAgent, allow: "/", disallow: DISALLOW })),
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
