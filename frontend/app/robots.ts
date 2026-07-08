import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/dashboard", "/campaigns", "/clients", "/settings", "/account", "/onboarding"],
      },
      { userAgent: "GPTBot", allow: "/" },
      { userAgent: "PerplexityBot", allow: "/" },
      { userAgent: "Googlebot", allow: "/" },
      { userAgent: "anthropic-ai", allow: "/" },
      { userAgent: "ClaudeBot", allow: "/" },
      { userAgent: "CCBot", allow: "/" },
    ],
    sitemap: `${(process.env.NEXT_PUBLIC_APP_URL ?? "https://personnapress.com").replace(/\/$/, "")}/sitemap.xml`,
  };
}
